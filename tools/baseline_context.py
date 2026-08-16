#!/usr/bin/env python3
"""Baseline measurer — what a session actually loads before you type anything.

Why this exists
---------------
The org-configuration work started from a static estimate: read the config files,
convert characters to tokens, and call the sum "fixed cost". That estimate was
wrong by 5-7x on one category (skills estimated at 10-14K, actually 2K), which is
exactly the failure this project keeps having to correct.

`/context` reports the real numbers, per category and per item, and it runs in
headless print mode. So the baseline is measured, not modelled:

    python3 tools/baseline_context.py                  # run a session and parse
    python3 tools/baseline_context.py --from FILE      # parse an existing capture
    python3 tools/baseline_context.py --json           # machine-readable

Evidence grade of everything here is `runtime_observed` — Claude Code's own
accounting, not our character conversion. The one caveat is in the output: the
numbers are what loaded *for this cwd, model, and configuration*, so a baseline
is only comparable to another baseline taken the same way.

Running with no `--from` starts a real Claude Code session, which costs tokens.
Use the cheapest model available and keep the prompt to the slash command.
"""

from __future__ import annotations

from pathlib import Path
import argparse
import json
import re
import shutil
import subprocess
import sys

PROBE_DIR = Path(__file__).resolve().parent / "_probe"

# "48.2k", "3.2k", "147", "< 20", "~290"
_NUM = re.compile(r"^\s*(?:[<~]\s*)?([\d.]+)\s*([km]?)\s*$", re.I)


def parse_tokens(cell: str) -> int | None:
    """'3.2k' -> 3200, '< 20' -> 20, '147' -> 147. Unparseable -> None."""
    m = _NUM.match(cell.strip())
    if not m:
        return None
    value, unit = float(m.group(1)), m.group(2).lower()
    if unit == "k":
        value *= 1_000
    elif unit == "m":
        value *= 1_000_000
    return int(round(value))


def _rows(lines: list[str], start: int) -> list[list[str]]:
    """Read a markdown table starting at or after `start`, skipping the header."""
    out: list[list[str]] = []
    seen_header = False
    for line in lines[start:]:
        s = line.strip()
        if not s.startswith("|"):
            if out or seen_header:
                break
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if set("".join(cells)) <= set("-: "):
            seen_header = True
            continue
        if not seen_header:
            continue
        out.append(cells)
    return out


def parse_context(text: str) -> dict:
    lines = text.splitlines()
    result: dict = {
        "evidence": "runtime_observed",
        "source": "claude -p /context",
        "model": None,
        "total_tokens": None,
        "window_tokens": None,
        "categories": {},
        "items": {},
        "unparsed_sections": [],
    }

    for line in lines[:12]:
        if line.startswith("**Model:**"):
            result["model"] = line.split("**Model:**", 1)[1].strip()
        m = re.search(r"\*\*Tokens:\*\*\s*([\d.]+[km]?)\s*/\s*([\d.]+[km]?)", line, re.I)
        if m:
            result["total_tokens"] = parse_tokens(m.group(1))
            result["window_tokens"] = parse_tokens(m.group(2))

    # (key, name_col, source_col, tok_col)
    sections = {
        "Estimated usage by category": ("categories", 0, None, 1),
        "MCP Tools": ("mcp_tools", 0, 1, 2),
        "Custom Agents": ("custom_agents", 0, 1, 2),
        "Memory Files": ("memory_files", 1, 0, 2),
        "Skills": ("skills", 0, 1, 2),
    }

    for i, line in enumerate(lines):
        if not line.startswith("### "):
            continue
        title = line[4:].strip()
        if title not in sections:
            result["unparsed_sections"].append(title)
            continue
        key, name_col, src_col, tok_col = sections[title]
        rows = _rows(lines, i + 1)
        if key == "categories":
            for r in rows:
                if len(r) > tok_col:
                    tok = parse_tokens(r[tok_col])
                    if tok is not None:
                        result["categories"][r[name_col]] = tok
        else:
            entries = []
            for r in rows:
                if len(r) <= tok_col:
                    continue
                tok = parse_tokens(r[tok_col])
                entries.append({
                    "name": r[name_col],
                    "source": r[src_col] if src_col is not None and len(r) > src_col else None,
                    "tokens": tok,
                    # "< 20" and "~290" are bounds, not counts. Summing them
                    # overshoots the category total, so mark them.
                    "is_bound": bool(re.match(r"^\s*[<~]", r[tok_col])),
                })
            result["items"][key] = entries
    return result


def load_hook_capture() -> list[dict]:
    """InstructionsLoaded records, if the probe hook is registered."""
    path = PROBE_DIR / "instructions_loaded.jsonl"
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("hook_event_name") == "InstructionsLoaded" and rec.get("file_path"):
            out.append({
                "file_path": rec["file_path"],
                "memory_type": rec.get("memory_type"),
                "load_reason": rec.get("load_reason"),
            })
    # de-duplicate, keep order
    seen, uniq = set(), []
    for r in out:
        k = (r["file_path"], r["load_reason"])
        if k not in seen:
            seen.add(k)
            uniq.append(r)
    return uniq


def run_context(model: str) -> str:
    if not shutil.which("claude"):
        raise SystemExit("claude CLI를 찾을 수 없습니다. --from 으로 캡처 파일을 넘기세요.")
    proc = subprocess.run(
        ["claude", "-p", "/context", "--model", model],
        capture_output=True, text=True, stdin=subprocess.DEVNULL,
    )
    if proc.returncode != 0 or "Context Usage" not in proc.stdout:
        sys.stderr.write(proc.stderr[-2000:])
        raise SystemExit(f"/context 캡처 실패 (exit {proc.returncode})")
    return proc.stdout


def render(data: dict, hook_records: list[dict]) -> None:
    total = data["total_tokens"] or 0
    window = data["window_tokens"] or 0
    print()
    print("═" * 62)
    print("세션 시작 고정비 — 실측 (claude -p /context)")
    print("═" * 62)
    print(f"모델: {data['model']}")
    if window:
        print(f"입력 전 사용: {total:,} / {window:,} 토큰  ({total / window * 100:.1f}%)")
    print()

    cats = data["categories"]
    if cats:
        # Deferred rows are shown by /context but are not part of the loaded total.
        loaded = {k: v for k, v in cats.items()
                  if "deferred" not in k.lower() and k.lower() != "free space"}
        deferred = {k: v for k, v in cats.items() if "deferred" in k.lower()}
        print("[로드된 것]")
        for k, v in sorted(loaded.items(), key=lambda kv: -kv[1]):
            share = f"{v / total * 100:5.1f}%" if total else "    —"
            print(f"  {k:28} {v:>8,}  {share}")
        if deferred:
            print()
            print("[지연 로드 — 지금은 안 실림, 호출 시 실림]")
            for k, v in sorted(deferred.items(), key=lambda kv: -kv[1]):
                print(f"  {k:28} {v:>8,}")

    for key, label in (("custom_agents", "커스텀 에이전트"),
                       ("skills", "스킬"),
                       ("memory_files", "메모리 파일"),
                       ("mcp_tools", "MCP 툴 (지연)")):
        entries = [e for e in data["items"].get(key, []) if e["tokens"]]
        if not entries:
            continue
        entries.sort(key=lambda e: -e["tokens"])
        subtotal = sum(e["tokens"] for e in entries)
        bounds = sum(1 for e in entries if e.get("is_bound"))
        note = f" (그중 {bounds}개는 상한 표기라 합계는 과대)" if bounds else ""
        print()
        print(f"[{label}]  {len(entries)}개 · 항목합 {subtotal:,} 토큰{note} · 상위 5")
        for e in entries[:5]:
            src = f" ({e['source']})" if e.get("source") else ""
            print(f"  {e['tokens']:>7,}  {e['name']}{src}")

    if hook_records:
        print()
        print("[InstructionsLoaded 훅 — 실제로 로드된 지시 파일]")
        for r in hook_records:
            print(f"  {r['memory_type'] or '?':10} {r['load_reason'] or '?':16} {r['file_path']}")

    print()
    print("─" * 62)
    print("  * 이 수치는 Claude Code 자신의 회계다(runtime_observed).")
    print("    우리가 문자 수로 환산한 추정이 아니다.")
    print("  * 단 이 cwd·모델·구성에서 로드된 값이다. 베이스라인끼리 비교하려면")
    print("    같은 방식으로 측정한 것과만 비교하라.")
    print("  * 범주 합계가 항목합보다 작을 수 있다 — `< 20`·`~290` 같은 상한 표기를")
    print("    더하면 부풀기 때문. 총량은 범주 값을, 순위는 항목 값을 보라.")
    if data["unparsed_sections"]:
        print(f"  * 해석하지 못한 섹션: {', '.join(data['unparsed_sections'])}")
        print("    (포맷이 바뀌었을 수 있다 — 파서 점검 필요)")
    print("═" * 62)
    print()


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="세션 시작 고정비를 /context 로 실측한다.")
    ap.add_argument("--from", dest="src", type=Path, help="이미 캡처한 /context 출력 파일")
    ap.add_argument("--model", default="claude-haiku-4-5", help="측정용 모델 (기본: 가장 싼 것)")
    ap.add_argument("--json", action="store_true", help="기계 판독 출력")
    ap.add_argument("--save", type=Path, help="원본 캡처를 저장할 경로")
    args = ap.parse_args(argv)

    text = args.src.read_text(encoding="utf-8") if args.src else run_context(args.model)
    if args.save:
        args.save.parent.mkdir(parents=True, exist_ok=True)
        args.save.write_text(text, encoding="utf-8")

    data = parse_context(text)
    hooks = load_hook_capture()

    if args.json:
        data["instructions_loaded"] = hooks
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        render(data, hooks)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
