#!/usr/bin/env python3
"""Generate synthetic ~/.claude-style JSONL logs that trigger tokenhabit patterns.

Used only to record the README demo GIF without exposing real usage data.
Output: ./demo-logs/<proj>/<session>.jsonl
"""
from __future__ import annotations
import json
from pathlib import Path

OUT = Path("demo-logs/demo-project")
OUT.mkdir(parents=True, exist_ok=True)


def rec(mid, role, ts, usage=None, content=None):
    m = {"id": mid, "role": role}
    if usage is not None:
        m["usage"] = usage
    if content is not None:
        m["content"] = content
    return json.dumps({"timestamp": ts, "message": m}, ensure_ascii=False)


def usage(inp, out, cr=0, cc=0):
    return {"input_tokens": inp, "output_tokens": out,
            "cache_read_input_tokens": cr, "cache_creation_input_tokens": cc}


BIG_LOG = "FAIL test_auth.py::test_login expected 200 got 500\n" * 400  # ~stdout flood


def write(name, lines):
    (OUT / name).write_text("\n".join(lines) + "\n", encoding="utf-8")


# Session 1 — file re-reads (H2-01) + log dump (H2-02) + token overrun (H1-03/H1-01)
s1 = []
for i in range(9):
    s1.append(rec(f"s1-{i}", "assistant", f"2026-06-10T10:{i*4:02d}:00Z",
                  usage=usage(9000, 6500, 3000, 1200),
                  content=[{"type": "tool_use", "name": "Read",
                            "input": {"file_path": "src/auth/session.ts"}}]))
s1.append(rec("s1-log", "user", "2026-06-10T10:40:00Z",
              content=[{"type": "tool_result", "content": BIG_LOG}]))
write("session-1.jsonl", s1)

# Session 2 — cache-kill (H4-03) + verbose output (H5-04) + long session (H1-01)
s2 = []
s2.append(rec("s2-0", "assistant", "2026-06-11T14:00:00Z", usage=usage(8000, 1000, 20000, 2000)))
s2.append(rec("s2-1", "assistant", "2026-06-11T14:20:00Z", usage=usage(22000, 1000, 200, 0)))  # cache drop
for i in range(6):
    s2.append(rec(f"s2-v{i}", "assistant", f"2026-06-11T14:{30+i*5:02d}:00Z",
                  usage=usage(1200, 4800, 500, 0)))  # output/input > 0.5 → verbose
write("session-2.jsonl", s2)

# Session 3 — web fetch (H2-04, signal) + subagent overuse (H8-03, signal) + main-thread reads (H8-01)
s3 = []
for i in range(8):
    s3.append(rec(f"s3-w{i}", "assistant", f"2026-06-12T09:{i*3:02d}:00Z",
                  usage=usage(3000, 1500, 1000, 200),
                  content=[{"type": "tool_use", "name": "WebFetch", "input": {"url": f"https://example.com/{i}"}}]))
for i in range(7):
    s3.append(rec(f"s3-t{i}", "assistant", "2026-06-12T09:30:00Z",
                  content=[{"type": "tool_use", "name": "Task", "input": {"prompt": "explore"}}]))
s3.append(rec("s3-reads", "assistant", "2026-06-12T09:35:00Z",
              content=[{"type": "tool_use", "name": "Read", "input": {"file_path": f"src/m{i}.ts"}} for i in range(5)]))
write("session-3.jsonl", s3)

print(f"wrote {len(list(OUT.glob('*.jsonl')))} synthetic sessions to {OUT}")
