"""JSONL parsing + habit pattern detection.

Parses ~/.claude/projects/*/*.jsonl directly. No LLM calls, standard library only.
Detects the subset of habit patterns that are quantitatively measurable from logs
(currently 10: H1-01, H1-03, H2-01, H2-02, H2-04, H4-03, H5-04, H8-01, H8-02, H8-03).
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
import json

CLAUDE_PROJECTS_DIR = Path.home() / ".claude" / "projects"

# Token estimation coefficient (approximation, for trend-spotting only).
# English: ~4 chars/token; Korean: weighted ~2 chars/token.
CHARS_PER_TOKEN_EN = 4.0

# Detection thresholds
LARGE_TOOL_RESULT_CHARS = 8_000  # above this = stdout flood (H2-02/H8-02)
VERBOSE_OUTPUT_RATIO = 0.5       # output/input above this = verbose (H5-04)
SESSION_MAX_MINUTES = 35         # above this = long session (H1-01/H1-03)
SESSION_MAX_TOKENS = 50_000      # above this = token overrun (H1-03)
READS_PER_TURN_FLAG = 4          # >= this many Reads in one turn = main-thread sweep (H8-01)
TASKS_PER_SESSION_FLAG = 6       # >= this many Task spawns in one session = subagent overuse (H8-03)


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
) -> list[Path]:
    """Return matching .jsonl files (recursive, includes subagents/)."""
    if session_file:
        return [session_file] if session_file.exists() else []

    base = project_dir if project_dir else CLAUDE_PROJECTS_DIR
    if not base.exists():
        return []

    cutoff_ts = datetime.now(tz=timezone.utc) - timedelta(days=days)
    result: list[Path] = []
    for p in base.rglob("*.jsonl"):
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


def analyze_session(jsonl_path: Path) -> dict[str, Any]:
    """Analyze a single session file -> pattern counts + token totals."""
    seen_ids: set[str] = set()

    total_input = total_output = total_cache_read = total_cache_creation = 0

    read_file_paths: list[str] = []
    large_tool_results = 0
    large_tool_result_tokens = 0
    verbose_output_hits = 0
    cache_drops = 0
    max_reads_in_one_turn = 0
    task_calls = 0       # H8-03: subagent (Task) spawns
    web_calls = 0        # H2-04: WebFetch / WebSearch calls
    timestamps: list[datetime] = []
    prev_cache_ratio: float | None = None

    for obj in iter_messages(jsonl_path):
        msg = obj.get("message", {})
        if not isinstance(msg, dict):
            continue

        ts_raw = obj.get("timestamp") or obj.get("ts") or obj.get("created_at")
        if ts_raw:
            try:
                timestamps.append(datetime.fromisoformat(ts_raw.replace("Z", "+00:00")))
            except (ValueError, AttributeError):
                pass

        mid = msg.get("id")
        usage = msg.get("usage", {})
        if usage and mid and mid not in seen_ids:
            seen_ids.add(mid)
            inp = usage.get("input_tokens", 0) or 0
            out = usage.get("output_tokens", 0) or 0
            cr = usage.get("cache_read_input_tokens", 0) or 0
            cc = usage.get("cache_creation_input_tokens", 0) or 0
            total_input += inp
            total_output += out
            total_cache_read += cr
            total_cache_creation += cc

            if inp > 200 and out > 0 and out / max(inp, 1) > VERBOSE_OUTPUT_RATIO:
                verbose_output_hits += 1

            total_tokens_this = inp + out + cr + cc
            if total_tokens_this > 0:
                cache_ratio = cr / total_tokens_this
                if prev_cache_ratio is not None and prev_cache_ratio > 0.3 and cache_ratio < 0.05:
                    cache_drops += 1
                if cr > 0 or cc > 0:
                    prev_cache_ratio = cache_ratio

        content = msg.get("content", [])
        if not isinstance(content, list):
            content = []

        reads_this_turn = 0
        for block in content:
            if not isinstance(block, dict):
                continue
            btype = block.get("type", "")
            if btype == "tool_use":
                tool_name = block.get("name", "")
                if tool_name == "Read":
                    fp = block.get("input", {}).get("file_path", "")
                    if fp:
                        read_file_paths.append(str(fp))
                    reads_this_turn += 1
                    max_reads_in_one_turn = max(max_reads_in_one_turn, reads_this_turn)
                elif tool_name == "Task":
                    task_calls += 1
                elif tool_name in ("WebFetch", "WebSearch"):
                    web_calls += 1
            elif btype == "tool_result":
                rc = block.get("content", "")
                rc_len = 0
                if isinstance(rc, str):
                    rc_len = len(rc)
                elif isinstance(rc, list):
                    for item in rc:
                        if isinstance(item, dict) and item.get("type") == "text":
                            rc_len += len(item.get("text", ""))
                if rc_len > LARGE_TOOL_RESULT_CHARS:
                    large_tool_results += 1
                    large_tool_result_tokens += _est_tokens(
                        rc if isinstance(rc, str) else str(rc)[:rc_len]
                    )

    path_counts = Counter(read_file_paths)
    repeated_reads = sum(cnt - 1 for cnt in path_counts.values() if cnt > 1)
    repeated_read_files = {p: cnt for p, cnt in path_counts.items() if cnt > 1}

    session_minutes = 0.0
    if len(timestamps) >= 2:
        session_minutes = (max(timestamps) - min(timestamps)).total_seconds() / 60.0
    total_tokens_all = total_input + total_output + total_cache_read + total_cache_creation
    long_session = session_minutes > SESSION_MAX_MINUTES or total_tokens_all > SESSION_MAX_TOKENS

    return {
        "file": str(jsonl_path),
        "total_input": total_input,
        "total_output": total_output,
        "total_cache_read": total_cache_read,
        "total_cache_creation": total_cache_creation,
        "total_tokens": total_tokens_all,
        "session_minutes": round(session_minutes, 1),
        "H2-01_repeated_reads": repeated_reads,
        "H2-01_repeated_files": repeated_read_files,
        "H2-02_large_tool_results": large_tool_results,
        "H2-02_large_tool_result_tokens": large_tool_result_tokens,
        "H5-04_verbose_output_hits": verbose_output_hits,
        "H4-03_cache_drops": cache_drops,
        "H1-01_long_session": 1 if long_session else 0,
        "H1-03_token_overrun": 1 if total_tokens_all > SESSION_MAX_TOKENS else 0,
        "H8-01_max_reads_in_one_turn": max_reads_in_one_turn,
        "H8-03_task_calls": task_calls,
        "H2-04_web_calls": web_calls,
    }


def aggregate(results: list[dict]) -> dict[str, Any]:
    """Aggregate per-session results by pattern."""
    agg: dict[str, int] = defaultdict(int)
    total_tokens = total_input = total_output = total_cache_read = 0

    for r in results:
        total_tokens += r["total_tokens"]
        total_input += r["total_input"]
        total_output += r["total_output"]
        total_cache_read += r["total_cache_read"]
        agg["H2-01"] += r["H2-01_repeated_reads"]
        agg["H2-02"] += r["H2-02_large_tool_results"]
        agg["H2-02_tokens"] += r["H2-02_large_tool_result_tokens"]
        agg["H5-04"] += r["H5-04_verbose_output_hits"]
        agg["H4-03"] += r["H4-03_cache_drops"]
        agg["H1-01"] += r["H1-01_long_session"]
        agg["H1-03"] += r["H1-03_token_overrun"]
        agg["H2-04"] += r["H2-04_web_calls"]
        if r["H8-01_max_reads_in_one_turn"] >= READS_PER_TURN_FLAG:
            agg["H8-01"] += 1
        if r["H8-03_task_calls"] >= TASKS_PER_SESSION_FLAG:
            agg["H8-03"] += 1

    return {
        "pattern_counts": dict(agg),
        "total_tokens": total_tokens,
        "total_input": total_input,
        "total_output": total_output,
        "total_cache_read": total_cache_read,
        "session_count": len(results),
    }
