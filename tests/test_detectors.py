#!/usr/bin/env python3
"""Detector regression tests — synthetic JSONL sessions, no network, no LLM.

Every test here encodes a bug that shipped once and must not ship again.
Run: python3 tests/test_detectors.py
"""

from __future__ import annotations

from pathlib import Path
import json
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tokenhabit.scan import (  # noqa: E402
    CONTEXT_MAX_TOKENS,
    READS_PER_TURN_FLAG,
    aggregate,
    analyze_session,
)

FAILURES: list[str] = []


def check(name: str, actual, expected) -> None:
    if actual == expected:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name}: expected {expected!r}, got {actual!r}")
        FAILURES.append(name)


def check_gt(name: str, actual, floor) -> None:
    if actual > floor:
        print(f"  ok   {name} ({actual!r} > {floor!r})")
    else:
        print(f"  FAIL {name}: expected > {floor!r}, got {actual!r}")
        FAILURES.append(name)


def assistant(mid, *, model="claude-opus-5", usage=None, content=None, ts=None, sidechain=False):
    obj = {
        "type": "assistant",
        "timestamp": ts or "2026-08-12T10:00:00.000Z",
        "message": {
            "id": mid,
            "role": "assistant",
            "model": model,
            "content": content or [],
        },
    }
    if usage:
        obj["message"]["usage"] = usage
    if sidechain:
        obj["isSidechain"] = True
    return obj


def user_result(tool_use_id, text, ts=None, sidechain=False):
    obj = {
        "type": "user",
        "timestamp": ts or "2026-08-12T10:00:00.000Z",
        "message": {
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": tool_use_id, "content": text}
            ],
        },
    }
    if sidechain:
        obj["isSidechain"] = True
    return obj


def tool_use(tid, name, inp=None):
    return {"type": "tool_use", "id": tid, "name": name, "input": inp or {}}


def usage(inp=0, out=0, cr=0, cc=0):
    return {
        "input_tokens": inp,
        "output_tokens": out,
        "cache_read_input_tokens": cr,
        "cache_creation_input_tokens": cc,
    }


def write_session(lines) -> Path:
    fh = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8")
    for obj in lines:
        fh.write(json.dumps(obj, ensure_ascii=False) + "\n")
    fh.close()
    return Path(fh.name)


# ─── B1: subagent spawns are logged as "Agent", not "Task" ────────────────────
def test_subagent_tool_name():
    print("B1 subagent spawn detection (Agent + legacy Task)")
    lines = [assistant(f"m{i}", content=[tool_use(f"t{i}", "Agent")]) for i in range(5)]
    lines.append(assistant("m9", content=[tool_use("t9", "Task")]))
    r = analyze_session(write_session(lines))
    check("Agent and Task both counted", r["H8-03_subagent_calls"], 6)

    # TaskCreate/TaskUpdate are todo tools and must never count as spawns.
    lines2 = [assistant("m0", content=[tool_use("t0", "TaskCreate"), tool_use("t1", "TaskUpdate")])]
    r2 = analyze_session(write_session(lines2))
    check("todo tools not counted as subagents", r2["H8-03_subagent_calls"], 0)


# ─── B2: a turn is a message id, spread over several JSONL lines ──────────────
def test_reads_per_turn_spans_lines():
    print("B2 parallel Reads share one message id across lines")
    mid = "msg_parallel"
    lines = [
        assistant(mid, content=[tool_use(f"r{i}", "Read", {"file_path": f"/a/f{i}.ts"})])
        for i in range(5)
    ]
    r = analyze_session(write_session(lines))
    check_gt("5 parallel Reads counted as one turn", r["H8-01_max_reads_in_one_turn"],
             READS_PER_TURN_FLAG - 1)

    agg = aggregate([r])
    check("H8-01 flagged at session level", agg["pattern_counts"].get("H8-01", 0), 1)


# ─── B3: context ceiling compares against per-turn context, not throughput ────
def test_context_uses_per_turn_not_cumulative():
    print("B3 context ceiling uses per-turn size, not session throughput")
    # Many small turns whose cumulative cache_read is enormous, but no single turn
    # ever holds a big context. This must NOT flag.
    lines = [
        assistant(f"m{i}", usage=usage(inp=100, out=100, cr=9_000))
        for i in range(200)
    ]
    r = analyze_session(write_session(lines))
    check_gt("throughput is large", r["total_tokens"], 1_000_000)
    check("no overrun flagged on small turns", r["H1-03_context_overrun"], 0)
    check("no overrun tokens", r["H1-03_context_overrun_tokens"], 0)

    # One genuinely heavy turn must flag, and report the measured excess.
    heavy = [assistant("m0", usage=usage(inp=1_000, out=100, cr=CONTEXT_MAX_TOKENS + 19_000))]
    r2 = analyze_session(write_session(heavy))
    check("overrun flagged on heavy turn", r2["H1-03_context_overrun"], 1)
    check("overrun tokens are measured excess", r2["H1-03_context_overrun_tokens"], 20_000)


# ─── H1: cache-kill means a real model switch, not a cache-ratio dip ──────────
def test_cache_kill_needs_real_model_switch():
    print("H1 cache-kill counts real model switches only")
    # Cache ratio crashes hard, but the model never changes -> not a habit.
    lines = [
        assistant("m0", usage=usage(inp=100, cr=90_000)),
        assistant("m1", usage=usage(inp=50_000, cr=0, cc=50_000)),
    ]
    r = analyze_session(write_session(lines))
    check("no switch -> no cache kill", r["H4-03_cache_kills"], 0)

    # Synthetic entries must not look like a switch either.
    lines_syn = [
        assistant("m0", model="claude-opus-5", usage=usage(inp=100, cr=9_000)),
        assistant("m1", model="<synthetic>", usage=usage(inp=100)),
        assistant("m2", model="claude-opus-5", usage=usage(inp=100, cr=9_000)),
    ]
    r_syn = analyze_session(write_session(lines_syn))
    check("synthetic model ignored", r_syn["H4-03_cache_kills"], 0)

    # A real switch inside the cache TTL counts, and charges the measured re-warm.
    lines2 = [
        assistant("m0", model="claude-opus-5", usage=usage(inp=100, cr=40_000),
                  ts="2026-08-12T10:00:00.000Z"),
        assistant("m1", model="claude-haiku-4-5", usage=usage(inp=100, cc=40_000),
                  ts="2026-08-12T10:01:00.000Z"),
    ]
    r2 = analyze_session(write_session(lines2))
    check("real switch counted", r2["H4-03_cache_kills"], 1)
    check("re-warm is measured", r2["H4-03_cache_kill_tokens"], 40_000)

    # A switch after the 5-min TTL would have expired anyway -> not charged.
    lines3 = [
        assistant("m0", model="claude-opus-5", usage=usage(inp=100, cr=40_000),
                  ts="2026-08-12T10:00:00.000Z"),
        assistant("m1", model="claude-haiku-4-5", usage=usage(inp=100, cc=40_000),
                  ts="2026-08-12T10:30:00.000Z"),
    ]
    r3 = analyze_session(write_session(lines3))
    check("switch past cache TTL not charged", r3["H4-03_cache_kills"], 0)


# ─── H5: subagent transcripts are not the driver's habits ─────────────────────
def test_sidechain_excluded():
    print("H5 subagent (isSidechain) lines excluded by default")
    lines = [
        assistant("m0", usage=usage(inp=100, out=100)),
        assistant("s0", usage=usage(inp=100, out=100), sidechain=True,
                  content=[tool_use("x0", "Agent")]),
    ]
    r = analyze_session(write_session(lines))
    check("sidechain spawn not counted", r["H8-03_subagent_calls"], 0)
    check("sidechain tokens not counted", r["total_tokens"], 200)

    r_inc = analyze_session(write_session(lines), include_subagents=True)
    check("opt-in includes sidechain", r_inc["H8-03_subagent_calls"], 1)


# ─── M5: chunked reads of one file are not re-reads ───────────────────────────
def test_chunked_reads_not_rereads():
    print("M5 offset/limit chunked reads are not re-reads")
    lines = [
        assistant("m0", content=[tool_use("r0", "Read",
                  {"file_path": "/big.ts", "offset": 1, "limit": 500})]),
        assistant("m1", content=[tool_use("r1", "Read",
                  {"file_path": "/big.ts", "offset": 501, "limit": 500})]),
    ]
    r = analyze_session(write_session(lines))
    check("chunked reads not flagged", r["H2-01_repeated_reads"], 0)

    same = [
        assistant("m0", content=[tool_use("r0", "Read", {"file_path": "/same.ts"})]),
        assistant("m1", content=[tool_use("r1", "Read", {"file_path": "/same.ts"})]),
    ]
    r2 = analyze_session(write_session(same))
    check("true re-read flagged", r2["H2-01_repeated_reads"], 1)


# ─── H8-02 was aggregated nowhere; Bash floods must be attributable ───────────
def test_bash_flood_attribution():
    print("H8-02 Bash output attributed apart from other tool results")
    big = "x" * 20_000
    lines = [
        assistant("m0", content=[tool_use("b0", "Bash", {"command": "npm test"})]),
        user_result("b0", big),
        assistant("m1", content=[tool_use("w0", "WebFetch", {"url": "https://e.com"})]),
        user_result("w0", big),
    ]
    r = analyze_session(write_session(lines))
    check("bash flood counted", r["H8-02_bash_floods"], 1)
    check("non-bash flood counted separately", r["H2-02_large_tool_results"], 1)
    check_gt("bash flood tokens measured", r["H8-02_bash_flood_tokens"], 1_000)

    agg = aggregate([r])
    check("H8-02 reaches aggregate", agg["pattern_counts"].get("H8-02", 0), 1)


# ─── H4-04: top-tier-only driving ─────────────────────────────────────────────
def test_top_tier_only():
    print("H4-04 top-tier-only driving")
    top = [assistant(f"m{i}", model="claude-opus-5", usage=usage(inp=10)) for i in range(12)]
    check("all-opus session flagged", analyze_session(write_session(top))["H4-04_top_tier_only"], 1)

    mixed = [assistant(f"m{i}", model="claude-opus-5", usage=usage(inp=10)) for i in range(11)]
    mixed.append(assistant("mx", model="claude-haiku-4-5", usage=usage(inp=10)))
    check("mixed-tier session not flagged",
          analyze_session(write_session(mixed))["H4-04_top_tier_only"], 0)

    short = [assistant(f"m{i}", model="claude-opus-5", usage=usage(inp=10)) for i in range(3)]
    check("tiny session not flagged (too little evidence)",
          analyze_session(write_session(short))["H4-04_top_tier_only"], 0)


def main() -> int:
    for fn in (
        test_subagent_tool_name,
        test_reads_per_turn_spans_lines,
        test_context_uses_per_turn_not_cumulative,
        test_cache_kill_needs_real_model_switch,
        test_sidechain_excluded,
        test_chunked_reads_not_rereads,
        test_bash_flood_attribution,
        test_top_tier_only,
    ):
        fn()
    print()
    if FAILURES:
        print(f"FAILED ({len(FAILURES)}): {', '.join(FAILURES)}")
        return 1
    print("all detector tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
