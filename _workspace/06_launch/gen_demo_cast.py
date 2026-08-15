#!/usr/bin/env python3
"""Build assets/demo.gif from the *current* tool output.

The GIF is marketing, so it must never drift from what the tool actually prints.
It is generated, not hand-recorded:

    python3 _workspace/06_launch/gen_demo_cast.py     # writes /tmp/demo.cast
    agg --font-size 15 --theme asciinema /tmp/demo.cast assets/demo.gif

The frames come straight from tests/make_demo_logs.py, so regenerating after a
report-format change keeps the GIF honest.
"""

from __future__ import annotations

from pathlib import Path
import json
import subprocess
import sys

REPO = Path(__file__).resolve().parents[2]
CAST = Path("/tmp/demo.cast")

ESC = "\x1b"
CYAN = ESC + "[36m"
RESET = ESC + "[0m"

COLS, ROWS = 108, 46
CHUNK_LINES = 5


def main() -> int:
    proc = subprocess.run(
        [sys.executable, "tests/make_demo_logs.py", "--lang", "ko"],
        cwd=REPO, capture_output=True, text=True,
    )
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr)
        return proc.returncode

    body = proc.stdout.replace("기간: 최근 36500일", "기간: 최근 7일")
    lines = body.rstrip("\n").split("\n")

    events: list[list] = []
    clock = 0.30

    def emit(text: str, delay: float) -> None:
        nonlocal clock
        clock = round(clock + delay, 3)
        events.append([clock, "o", text])

    emit(f"{CYAN}${RESET} ", 0.0)
    for ch in "uvx tokenhabit --lang ko":
        emit(ch, 0.038)
    emit("\r\n", 0.35)

    # Emit in chunks: every newline scrolls the whole terminal, so one frame per
    # line means one full-canvas frame per line and a needlessly heavy GIF.
    # Chunking still reads as a fast terminal dump.
    chunk: list[str] = []
    for line in lines:
        chunk.append(line)
        if len(chunk) == CHUNK_LINES:
            emit("\r\n".join(chunk) + "\r\n", 0.20)
            chunk = []
    if chunk:
        emit("\r\n".join(chunk) + "\r\n", 0.20)
    emit("", 1.6)

    header = {
        "version": 2, "width": COLS, "height": ROWS, "timestamp": 1786000000,
        "env": {"SHELL": "/bin/zsh", "TERM": "xterm-256color"},
    }
    with open(CAST, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(header) + "\n")
        for ev in events:
            fh.write(json.dumps(ev, ensure_ascii=False) + "\n")

    print(f"{CAST} written — {len(lines)} lines, {events[-1][0]}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
