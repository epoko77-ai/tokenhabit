#!/usr/bin/env python3
"""tokenhabit 진단 본체 — 과거 Claude Code 세션 로그를 LLM 0회로 사후 스캔한다.

    python3 habit_scan.py                 # 최근 7일 전체 세션 (한국어)
    python3 habit_scan.py --days 30
    python3 habit_scan.py --current       # 현재(가장 최근) 세션 1개만
    python3 habit_scan.py --lang en
    python3 habit_scan.py --json          # 기계 판독용
    python3 habit_scan.py --ccusage       # npx ccusage 병합 (네트워크 사용, opt-in)

~/.claude/projects/**/*.jsonl 을 직접 파싱한다. LLM 호출 0회, 표준 라이브러리만,
기본 완전 오프라인(--ccusage 를 켤 때만 네트워크).

── 이 파일은 로직을 갖고 있지 않다 ────────────────────────────────────────────
탐지·집계·리포트 로직의 단일 진실 원천(SSOT)은 레포 루트의 `tokenhabit/` 패키지다.
여기 `_vendor/tokenhabit/` 는 그 패키지를 그대로 복사한 것이며,
`python3 skill/scripts/sync_vendor.py` 로 재생성한다. 로직을 고칠 일이 생기면
`tokenhabit/` 를 고치고 sync 를 돌려라 — 이 파일이나 _vendor 를 직접 편집하면
CLI 와 스킬의 숫자가 갈라진다(그게 바로 이 스킬이 잡으려는 종류의 낭비다).
"""

from __future__ import annotations

from pathlib import Path
import sys

_VENDOR = Path(__file__).resolve().parent / "_vendor"
if _VENDOR.is_dir():
    sys.path.insert(0, str(_VENDOR))

try:
    from tokenhabit.cli import main
except ImportError as exc:  # pragma: no cover - defensive
    print(
        f"tokenhabit 모듈을 찾을 수 없습니다: {exc}\n"
        f"기대 경로: {_VENDOR}/tokenhabit/\n"
        "복구: 레포 루트에서 `python3 skill/scripts/sync_vendor.py` 실행.",
        file=sys.stderr,
    )
    raise SystemExit(2)


def _with_ko_default(argv: list[str]) -> list[str]:
    """스킬 경로에서는 한국어가 기본. 사용자가 --lang 을 주면 그대로 존중."""
    if any(a == "--lang" or a.startswith("--lang=") for a in argv):
        return argv
    return [*argv, "--lang", "ko"]


if __name__ == "__main__":
    raise SystemExit(main(_with_ko_default(sys.argv[1:])))
