#!/usr/bin/env python3
"""InstructionsLoaded probe — record the hook's real payload, don't guess it.

The official docs say this event fires when a CLAUDE.md or `.claude/rules/*.md`
file is loaded, and list the common fields plus `load_reason`. They do not
document whether the payload names the file that loaded. That single unknown
decides whether a baseline measurer can report observed loads or only estimates,
so we observe it instead of assuming.

Register it in `.claude/settings.local.json` (local, not committed):

    {"hooks": {"InstructionsLoaded": [{"hooks": [
      {"type": "command", "command": "python3 /abs/path/tools/probe_instructions_loaded.py"}
    ]}]}}

Then start any session in this repo and read the capture:

    python3 tools/probe_instructions_loaded.py --show

Writes newline-delimited JSON to tools/_probe/instructions_loaded.jsonl.
Never blocks: reads stdin, appends, exits 0 whatever happens.
"""

from __future__ import annotations

from pathlib import Path
import json
import sys

CAPTURE = Path(__file__).resolve().parent / "_probe" / "instructions_loaded.jsonl"


def show() -> int:
    if not CAPTURE.exists():
        print(f"아직 캡처 없음: {CAPTURE}")
        print("훅을 등록한 뒤 이 레포에서 새 세션을 한 번 시작하세요.")
        return 1

    records = []
    for line in CAPTURE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                pass

    print(f"캡처 {len(records)}건 — {CAPTURE}\n")
    keys: dict[str, int] = {}
    for r in records:
        for k in r:
            keys[k] = keys.get(k, 0) + 1
    print("관측된 최상위 필드 (등장 횟수):")
    for k, n in sorted(keys.items(), key=lambda kv: -kv[1]):
        print(f"  {k:24} {n}")

    print("\n첫 레코드 전문:")
    if records:
        print(json.dumps(records[0], ensure_ascii=False, indent=2)[:4000])
    return 0


def main(argv: list[str]) -> int:
    if "--show" in argv:
        return show()

    raw = ""
    try:
        raw = sys.stdin.read()
    except Exception:  # noqa: BLE001 - a probe must never break the session
        pass

    try:
        CAPTURE.parent.mkdir(parents=True, exist_ok=True)
        payload: object
        try:
            payload = json.loads(raw) if raw.strip() else {"_empty_stdin": True}
        except json.JSONDecodeError:
            payload = {"_unparsed_stdin": raw[:8000]}
        with open(CAPTURE, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:  # noqa: BLE001
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
