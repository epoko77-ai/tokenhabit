#!/usr/bin/env python3
"""Generate a synthetic ~/.claude/projects tree and print a real tokenhabit report.

The README demo output must be reproducible and internally consistent — a hand-typed
sample once shipped with cache hits larger than total tokens, which is impossible.
Regenerate with:

    python3 tests/make_demo_logs.py            # prints the English report
    python3 tests/make_demo_logs.py --lang ko  # Korean
"""

from __future__ import annotations

from pathlib import Path
import json
import shutil
import subprocess
import sys
import tempfile

REPO = Path(__file__).resolve().parents[1]

# Deterministic pseudo-randomness: no Date/random, just a fixed LCG.
_state = 20260812


def rnd(n: int) -> int:
    global _state
    _state = (_state * 1103515245 + 12345) % (2**31)
    return _state % n


def ts(minute: int) -> str:
    h, m = 9 + minute // 60, minute % 60
    return f"2026-06-15T{h:02d}:{m:02d}:00.000Z"


def build_session(path: Path, *, turns: int, model: str, seed_shift: int) -> None:
    lines: list[dict] = []
    cache = 4_000
    for t in range(turns):
        mid = f"msg_{seed_shift}_{t}"
        cache = min(cache + 1_800 + rnd(2_400), 120_000)
        out = 200 + rnd(2_600)
        content: list[dict] = []

        # Some turns sweep the repo with parallel Reads (H8-01) — separate lines,
        # shared message id, exactly like real Claude Code logs.
        if t % 9 == 4:
            for i in range(5):
                lines.append({
                    "type": "assistant", "timestamp": ts(t * 2),
                    "message": {"id": mid, "role": "assistant", "model": model,
                                "content": [{"type": "tool_use", "id": f"r{seed_shift}{t}{i}",
                                             "name": "Read",
                                             "input": {"file_path": f"/src/mod{i}.ts"}}]},
                })

        # Re-reading the same file (H2-01)
        if t % 11 == 3:
            content.append({"type": "tool_use", "id": f"rr{seed_shift}{t}", "name": "Read",
                            "input": {"file_path": "/src/auth.ts"}})

        # Unfiltered build output (H8-02)
        if t % 13 == 6:
            content.append({"type": "tool_use", "id": f"b{seed_shift}{t}", "name": "Bash",
                            "input": {"command": "npm test"}})

        lines.append({
            "type": "assistant", "timestamp": ts(t * 2),
            "message": {"id": mid, "role": "assistant", "model": model,
                        "content": content,
                        "usage": {"input_tokens": 120 + rnd(400),
                                  "output_tokens": out,
                                  "cache_read_input_tokens": cache,
                                  "cache_creation_input_tokens": 900 + rnd(1_500)}},
        })

        if t % 13 == 6:
            lines.append({
                "type": "user", "timestamp": ts(t * 2 + 1),
                "message": {"role": "user", "content": [
                    {"type": "tool_result", "tool_use_id": f"b{seed_shift}{t}",
                     "content": "FAIL src/x.test.ts\n" + ("stack frame line\n" * 1_400)}]},
            })

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for obj in lines:
            fh.write(json.dumps(obj) + "\n")


def main(argv: list[str]) -> int:
    lang = "ko" if "--lang" in argv and "ko" in argv else "en"
    tmp = Path(tempfile.mkdtemp(prefix="tokenhabit_demo_"))
    try:
        projects = tmp / "projects"
        for s in range(6):
            model = "claude-opus-5" if s % 3 else "claude-sonnet-5"
            build_session(projects / f"proj-{s % 2}" / f"session-{s}.jsonl",
                          turns=40 + s * 9, model=model, seed_shift=s)

        proc = subprocess.run(
            [sys.executable, "-m", "tokenhabit.cli",
             "--project", str(projects), "--days", "36500",
             "--lang", lang, "--no-color"],
            cwd=REPO, capture_output=True, text=True,
        )
        sys.stdout.write(proc.stdout)
        sys.stderr.write(proc.stderr)
        return proc.returncode
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
