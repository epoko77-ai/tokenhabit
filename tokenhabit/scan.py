"""JSONL parsing + habit pattern detection.

Parses ~/.claude/projects/**/*.jsonl directly. No LLM calls, standard library only.
Detects the subset of habit patterns that are quantitatively measurable from logs
(currently 11: H1-01, H1-03, H2-01, H2-02, H2-04, H4-03, H4-04, H5-04, H8-01,
H8-02, H8-03).

Measurement notes (why the numbers here are defensible):
  * Turn boundaries come from `message.id`, NOT from JSONL lines. Claude Code
    writes parallel tool calls of one assistant turn as separate lines that
    share a message id, so per-line counting can never see a multi-Read turn.
  * Context size uses `input + cache_read + cache_creation` of a single message
    (= what the model actually had in front of it that turn). Session-cumulative
    totals are throughput, not context, and must never be compared to a
    context-window threshold.
  * Subagent transcripts (`isSidechain`) are excluded by default: this tool
    coaches the driver's habits, not what an agent did on its own.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
import json
import os

CLAUDE_PROJECTS_DIR = Path.home() / ".claude" / "projects"

# Token estimation coefficient (approximation, for trend-spotting only).
# English: ~4 chars/token; Korean: weighted ~2 chars/token.
CHARS_PER_TOKEN_EN = 4.0

# ─── Detection thresholds ─────────────────────────────────────────────────────
LARGE_TOOL_RESULT_CHARS = 8_000   # above this = stdout flood (H2-02 / H8-02)
VERBOSE_OUTPUT_TOKENS = 2_000     # assistant output tokens in one turn (H5-04)
SESSION_MAX_MINUTES = 35          # above this = long session (H1-01)
CONTEXT_MAX_TOKENS = 50_000       # per-turn context size ceiling (H1-01 / H1-03)
READS_PER_TURN_FLAG = 4           # >= this many Reads in one turn = main-thread sweep (H8-01)
TASKS_PER_SESSION_FLAG = 6        # >= this many subagent spawns in one session (H8-03)
# Prompt-cache TTL differs by how you authenticate (official docs):
#   Claude subscription (Pro/Max) -> 1 hour, requested automatically
#   API key / Bedrock / Vertex / Foundry -> 5 minutes
#   Subscription drawing on usage credits -> drops back to 5 minutes
#   Subagents -> 5 minutes even on a subscription
# The log does not record the auth method, so we cannot know which applied. We
# default to the subscription value because Claude Code's common case is a
# subscription, and because over-charging a habit is worse than missing one:
# a longer window means fewer gaps get counted as "the cache was still warm".
CACHE_TTL_SECONDS = 3600          # override with TOKENHABIT_CACHE_TTL

_ttl_override = os.environ.get("TOKENHABIT_CACHE_TTL")
if _ttl_override and _ttl_override.isdigit():
    CACHE_TTL_SECONDS = int(_ttl_override)

# H4-04: model ids containing these markers are top-tier (most expensive) models.
TOP_TIER_MARKERS = ("opus", "fable")
# Synthetic / non-model entries that must never count as a model switch.
NON_MODEL_VALUES = ("<synthetic>", "synthetic", "")

# Tool names that spawn a subagent. "Task" is the legacy name; current Claude Code
# logs record subagent spawns as "Agent". Both are accepted so old logs still scan.
SUBAGENT_TOOL_NAMES = ("Task", "Agent")


def iter_messages(jsonl_path: Path):
    """Yield one dict per JSONL line. Malformed lines are skipped."""
    try:
        with open(jsonl_path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    parsed = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(parsed, dict):
                    yield parsed
    except OSError:
        pass


def collect_jsonl_files(
    *,
    project_dir: Path | None = None,
    session_file: Path | None = None,
    days: int = 7,
    include_subagents: bool = False,
) -> list[Path]:
    """Return matching .jsonl files (recursive).

    Subagent transcript directories are skipped unless include_subagents is set.
    """
    if session_file:
        return [session_file] if session_file.exists() else []

    base = project_dir if project_dir else CLAUDE_PROJECTS_DIR
    if not base.exists():
        return []

    cutoff_ts = datetime.now(tz=timezone.utc) - timedelta(days=days)
    result: list[Path] = []
    for p in base.rglob("*.jsonl"):
        if not include_subagents and "subagents" in p.parts:
            continue
        try:
            mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
            if mtime >= cutoff_ts:
                result.append(p)
        except OSError:
            pass
    return sorted(result)


def _est_tokens(text: str) -> int:
    """Approximate token count. Korean characters are weighted. Not a precise measure."""
    korean_count = sum(1 for ch in text if "가" <= ch <= "힣")
    non_korean = len(text) - korean_count
    return int(non_korean / CHARS_PER_TOKEN_EN + korean_count / 2.0)


def _is_top_tier(model: str) -> bool:
    m = (model or "").lower()
    return any(marker in m for marker in TOP_TIER_MARKERS)


def _real_model(model: Any) -> str | None:
    """Return a usable model id, or None for synthetic/absent entries."""
    if not isinstance(model, str):
        return None
    if model.strip().lower() in NON_MODEL_VALUES:
        return None
    return model


def analyze_session(jsonl_path: Path, *, include_subagents: bool = False) -> dict[str, Any]:
    """Analyze a single session file -> pattern counts + token totals."""
    seen_ids: set[str] = set()

    total_input = total_output = total_cache_read = total_cache_creation = 0

    read_keys: list[tuple[str, Any, Any]] = []   # (path, offset, limit) — chunked reads are not re-reads
    reads_per_turn: defaultdict[str, int] = defaultdict(int)
    tool_use_names: dict[str, str] = {}          # tool_use_id -> tool name, to attribute results

    bash_flood_hits = bash_flood_tokens = 0      # H8-02
    other_flood_hits = other_flood_tokens = 0    # H2-02
    verbose_output_hits = 0                      # H5-04
    cache_kills = 0                              # H4-03 (real model switches only)
    cache_kill_tokens = 0                        # measured cache_creation burned by the switch
    subagent_calls = 0                           # H8-03
    web_calls = 0                                # H2-04
    max_context = 0                              # peak per-turn context size
    model_counts: Counter[str] = Counter()       # H4-04

    timestamps: list[datetime] = []
    prev_model: str | None = None
    prev_ts: datetime | None = None
    line_no = 0

    for obj in iter_messages(jsonl_path):
        if not include_subagents and obj.get("isSidechain"):
            continue

        msg = obj.get("message", {})
        if not isinstance(msg, dict):
            continue

        this_ts: datetime | None = None
        ts_raw = obj.get("timestamp") or obj.get("ts") or obj.get("created_at")
        if ts_raw:
            try:
                this_ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
                timestamps.append(this_ts)
            except (ValueError, AttributeError):
                pass

        line_no += 1
        mid = msg.get("id") or f"__line_{line_no}"
        usage = msg.get("usage", {})
        model = _real_model(msg.get("model"))

        if usage and mid not in seen_ids:
            seen_ids.add(mid)
            inp = usage.get("input_tokens", 0) or 0
            out = usage.get("output_tokens", 0) or 0
            cr = usage.get("cache_read_input_tokens", 0) or 0
            cc = usage.get("cache_creation_input_tokens", 0) or 0
            total_input += inp
            total_output += out
            total_cache_read += cr
            total_cache_creation += cc

            # Context actually in front of the model this turn (excludes generated output).
            context_this_turn = inp + cr + cc
            max_context = max(max_context, context_this_turn)

            # H5-04: verbose output is about how much the model *wrote*, in absolute
            # terms. Ratios against input are meaningless once caching is on, because
            # `input_tokens` then only holds the uncached delta.
            if out > VERBOSE_OUTPUT_TOKENS:
                verbose_output_hits += 1

            if model:
                model_counts[model] += 1
                # H4-03: only a genuine model switch counts. A cache-ratio crash also
                # happens on session resume, auto-compact, and plain TTL expiry, so the
                # old heuristic charged the user for things that are not a habit.
                gap_ok = True
                if prev_ts is not None and this_ts is not None:
                    gap_ok = (this_ts - prev_ts).total_seconds() < CACHE_TTL_SECONDS
                if prev_model is not None and model != prev_model and gap_ok:
                    cache_kills += 1
                    cache_kill_tokens += cc  # measured: the re-warm this switch forced
                prev_model = model
                if this_ts is not None:
                    prev_ts = this_ts

        content = msg.get("content", [])
        if not isinstance(content, list):
            content = []

        for block in content:
            if not isinstance(block, dict):
                continue
            btype = block.get("type", "")
            if btype == "tool_use":
                tool_name = block.get("name", "")
                tu_id = block.get("id", "")
                if tu_id:
                    tool_use_names[tu_id] = tool_name
                if tool_name == "Read":
                    inp_block = block.get("input", {})
                    if not isinstance(inp_block, dict):
                        inp_block = {}
                    fp = inp_block.get("file_path", "")
                    if fp:
                        # Chunked reads of one big file (different offset/limit) are a
                        # correct pattern, not a re-read. Key on the actual byte range.
                        read_keys.append(
                            (str(fp), inp_block.get("offset"), inp_block.get("limit"))
                        )
                    # Turn = message id. Parallel tool calls share it across lines.
                    reads_per_turn[mid] += 1
                elif tool_name in SUBAGENT_TOOL_NAMES:
                    subagent_calls += 1
                elif tool_name in ("WebFetch", "WebSearch"):
                    web_calls += 1
            elif btype == "tool_result":
                rc = block.get("content", "")
                rc_len = 0
                text = ""
                if isinstance(rc, str):
                    text = rc
                    rc_len = len(rc)
                elif isinstance(rc, list):
                    parts = [
                        item.get("text", "")
                        for item in rc
                        if isinstance(item, dict) and item.get("type") == "text"
                    ]
                    text = "".join(parts)
                    rc_len = len(text)
                if rc_len > LARGE_TOOL_RESULT_CHARS:
                    origin = tool_use_names.get(block.get("tool_use_id", ""), "")
                    est = _est_tokens(text)
                    if origin == "Bash":
                        bash_flood_hits += 1
                        bash_flood_tokens += est
                    else:
                        other_flood_hits += 1
                        other_flood_tokens += est

    key_counts = Counter(read_keys)
    repeated_reads = sum(cnt - 1 for cnt in key_counts.values() if cnt > 1)
    repeated_read_files = {k[0]: cnt for k, cnt in key_counts.items() if cnt > 1}

    session_minutes = 0.0
    if len(timestamps) >= 2:
        session_minutes = (max(timestamps) - min(timestamps)).total_seconds() / 60.0

    total_tokens_all = total_input + total_output + total_cache_read + total_cache_creation
    context_overrun = max(0, max_context - CONTEXT_MAX_TOKENS)

    # H1-01 needs BOTH duration and a heavy context — a long session that stayed
    # small is not topic drift, and a big context reached in 3 minutes is H1-03.
    long_session = session_minutes > SESSION_MAX_MINUTES and max_context > CONTEXT_MAX_TOKENS

    real_models = sum(model_counts.values())
    top_tier_msgs = sum(n for m, n in model_counts.items() if _is_top_tier(m))
    top_tier_only = 1 if real_models >= 10 and top_tier_msgs == real_models else 0

    max_reads_in_one_turn = max(reads_per_turn.values(), default=0)

    return {
        "file": str(jsonl_path),
        "total_input": total_input,
        "total_output": total_output,
        "total_cache_read": total_cache_read,
        "total_cache_creation": total_cache_creation,
        "total_tokens": total_tokens_all,
        "session_minutes": round(session_minutes, 1),
        "max_context": max_context,
        "models": dict(model_counts),
        "H2-01_repeated_reads": repeated_reads,
        "H2-01_repeated_files": repeated_read_files,
        "H2-02_large_tool_results": other_flood_hits,
        "H2-02_large_tool_result_tokens": other_flood_tokens,
        "H8-02_bash_floods": bash_flood_hits,
        "H8-02_bash_flood_tokens": bash_flood_tokens,
        "H5-04_verbose_output_hits": verbose_output_hits,
        "H4-03_cache_kills": cache_kills,
        "H4-03_cache_kill_tokens": cache_kill_tokens,
        "H4-04_top_tier_only": top_tier_only,
        "H1-01_long_session": 1 if long_session else 0,
        "H1-03_context_overrun": 1 if context_overrun > 0 else 0,
        "H1-03_context_overrun_tokens": context_overrun,
        "H8-01_max_reads_in_one_turn": max_reads_in_one_turn,
        "H8-03_subagent_calls": subagent_calls,
        "H2-04_web_calls": web_calls,
    }


def aggregate(results: list[dict]) -> dict[str, Any]:
    """Aggregate per-session results by pattern."""
    agg: dict[str, int] = defaultdict(int)
    total_tokens = total_input = total_output = total_cache_read = 0
    models: Counter[str] = Counter()

    for r in results:
        total_tokens += r["total_tokens"]
        total_input += r["total_input"]
        total_output += r["total_output"]
        total_cache_read += r["total_cache_read"]
        models.update(r.get("models", {}))

        agg["H2-01"] += r["H2-01_repeated_reads"]
        agg["H2-02"] += r["H2-02_large_tool_results"]
        agg["H2-02_tokens"] += r["H2-02_large_tool_result_tokens"]
        agg["H8-02"] += r["H8-02_bash_floods"]
        agg["H8-02_tokens"] += r["H8-02_bash_flood_tokens"]
        agg["H5-04"] += r["H5-04_verbose_output_hits"]
        agg["H4-03"] += r["H4-03_cache_kills"]
        agg["H4-03_tokens"] += r["H4-03_cache_kill_tokens"]
        agg["H4-04"] += r["H4-04_top_tier_only"]
        agg["H1-01"] += r["H1-01_long_session"]
        agg["H1-03"] += r["H1-03_context_overrun"]
        agg["H1-03_tokens"] += r["H1-03_context_overrun_tokens"]
        agg["H2-04"] += r["H2-04_web_calls"]
        if r["H8-01_max_reads_in_one_turn"] >= READS_PER_TURN_FLAG:
            agg["H8-01"] += 1
        if r["H8-03_subagent_calls"] >= TASKS_PER_SESSION_FLAG:
            agg["H8-03"] += 1

    return {
        "pattern_counts": dict(agg),
        "total_tokens": total_tokens,
        "total_input": total_input,
        "total_output": total_output,
        "total_cache_read": total_cache_read,
        "session_count": len(results),
        "models": dict(models),
    }
