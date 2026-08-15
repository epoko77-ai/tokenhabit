#!/usr/bin/env python3
"""`tokenhabit/` 패키지를 `skill/scripts/_vendor/tokenhabit/` 로 복사한다.

SSOT 는 레포 루트의 `tokenhabit/` 패키지 하나뿐이다. 스킬은 pip 설치 없이도
돌아가야 하므로 사본을 함께 배포하지만, 그 사본은 항상 이 스크립트로 재생성한다.

    python3 skill/scripts/sync_vendor.py          # 동기화
    python3 skill/scripts/sync_vendor.py --check  # 차이만 보고(비동기면 exit 1) — CI 용
"""

from __future__ import annotations

from pathlib import Path
import shutil
import sys

MODULES = ("__init__.py", "catalog.py", "scan.py", "report.py", "cli.py")

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE = REPO_ROOT / "tokenhabit"
VENDOR = REPO_ROOT / "skill" / "scripts" / "_vendor" / "tokenhabit"


def main(argv: list[str]) -> int:
    check_only = "--check" in argv

    if not SOURCE.is_dir():
        print(f"소스 패키지를 찾을 수 없습니다: {SOURCE}", file=sys.stderr)
        return 2

    VENDOR.mkdir(parents=True, exist_ok=True)
    drifted: list[str] = []

    for name in MODULES:
        src = SOURCE / name
        dst = VENDOR / name
        if not src.is_file():
            print(f"소스 모듈 누락: {src}", file=sys.stderr)
            return 2
        same = dst.is_file() and dst.read_bytes() == src.read_bytes()
        if same:
            continue
        drifted.append(name)
        if not check_only:
            shutil.copy2(src, dst)

    if check_only:
        if drifted:
            print("vendor 사본이 tokenhabit/ 와 다릅니다: " + ", ".join(drifted), file=sys.stderr)
            print("복구: python3 skill/scripts/sync_vendor.py", file=sys.stderr)
            return 1
        print("vendor 사본이 최신입니다.")
        return 0

    if drifted:
        print("동기화 완료: " + ", ".join(drifted))
    else:
        print("변경 없음 — 이미 최신입니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
