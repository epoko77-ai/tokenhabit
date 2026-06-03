#!/usr/bin/env python3
"""
tokenhabit — habit_scan.py  v1.1

목적: ~/.claude/projects/*/*.jsonl 직접 파싱 → 습관 진단 리포트.
범위: 전체 25패턴 중 JSONL에서 정량 자동감지 가능한 일부(현재 8패턴:
  H1-01, H1-03, H2-01, H2-02, H4-03, H5-04, H8-01, H8-02)만 자동 진단한다.
  나머지 패턴(프롬프트 명료성·CLAUDE.md 설정·MCP 구성 등)은 JSONL만으로 판정할 수
  없으므로 references/habit_catalog.md 카탈로그로 자가점검한다.
측정(집계)은 ccusage에 위임하고, 우리는 raw 메시지 단위 패턴 감지 + 카탈로그 ID 매핑이 차별점.

사용법:
  python3 habit_scan.py                    # 최근 7일 전체 프로젝트
  python3 habit_scan.py --days 14          # 최근 14일
  python3 habit_scan.py --project /path    # 특정 프로젝트 디렉토리
  python3 habit_scan.py --session file.jsonl  # 단일 세션 파일
  python3 habit_scan.py --json             # JSON 출력 (CI/파이핑용)

LLM 호출 0회. 표준 라이브러리만.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# ─── 상수 (모두 여기서 조정) ────────────────────────────────────────────────────

CLAUDE_PROJECTS_DIR = Path.home() / ".claude" / "projects"

# 토큰 추정 계수 (근사치임을 명시)
# 영문: ~4자/token, 한글: 가중 ~2자/token.
# 이 값은 정밀 측정이 아닌 경향 파악용.
CHARS_PER_TOKEN_EN = 4.0

# 패턴 감지 임계치
LARGE_TOOL_RESULT_CHARS = 8_000     # 이 이상이면 stdout 홍수(H2-02/H8-02) 신호
VERBOSE_OUTPUT_RATIO = 0.5          # output/input > 이 비율이면 H5-04 신호
SESSION_MAX_MINUTES = 35            # 이 분 초과면 H1-01/H1-03 신호
SESSION_MAX_TOKENS = 50_000         # 이 토큰 초과면 H1-03 신호

# 카탈로그 패턴 정보 (ID, 이름, 즉시 fix 요약)
CATALOG = {
    "H2-01": {
        "name": "파일 리드 재탕",
        "fix": '같은 파일 재읽기 대신 "아까 읽은 X에서..." 컨텍스트 참조 유도. PreToolUse hook으로 차단.',
        "token_est_per_hit": 2_000,  # 200줄 파일 1회 재독 추정
    },
    "H2-02": {
        "name": "로그 전체 덤프 / stdout 홍수",
        "fix": "grep -A5 'FAIL|ERROR'로 필터 후 실행. PreToolUse hook 설정.",
        "token_est_per_hit": 5_000,
    },
    "H8-02": {
        "name": "stdout 홍수 (Bash 결과 대형)",
        "fix": "Bash 명령에 | head -50 또는 | grep 필터 추가. 파일 저장 후 경로만 전달.",
        "token_est_per_hit": 5_000,
    },
    "H5-04": {
        "name": "장황 출력 유도",
        "fix": '"2줄로만" "코드·예시 없이" 등 출력 제한 명시. CLAUDE.md에 기본값 설정.',
        "token_est_per_hit": 800,
    },
    "H4-03": {
        "name": "캐시 킬 스위치 (캐시 히트율 급락)",
        "fix": "세션 내 모델·effort 전환 최소화. 전환 필요 시 새 세션 오픈.",
        "token_est_per_hit": 21_000,
    },
    "H1-01": {
        "name": "주제 드래그 / 장시간 세션",
        "fix": "35분·50K 토큰 기준으로 /compact 또는 /clear + 새 세션 전환.",
        "token_est_per_hit": 10_000,
    },
    "H1-03": {
        "name": "compaction 버스 막차 (누적 토큰 과다)",
        "fix": "50K 토큰 전에 수동 /compact [포커스 지시] 실행.",
        "token_est_per_hit": 15_000,
    },
    "H8-01": {
        "name": "메인 스레드 탐색 (한 턴 Read 다수)",
        "fix": '서브에이전트로 탐색 위임: "src/auth/ 에서 OAuth 함수 찾아서 이름·위치만 요약."',
        "token_est_per_hit": 5_000,
    },
}


# ─── JSONL 파싱 ─────────────────────────────────────────────────────────────────

def iter_messages(jsonl_path: Path):
    """JSONL 1줄 1객체 파싱. 실패 라인은 skip."""
    try:
        with open(jsonl_path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    parsed = json.loads(line)
                except json.JSONDecodeError:
                    continue  # 파싱 실패 skip
                # 최상위가 dict가 아닌 유효 JSON(예: [1,2,3], "str", 42)도 skip
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
    """조건에 맞는 .jsonl 파일 목록 반환."""
    if session_file:
        return [session_file] if session_file.exists() else []

    base = project_dir if project_dir else CLAUDE_PROJECTS_DIR
    if not base.exists():
        return []

    cutoff_ts = datetime.now(tz=timezone.utc) - timedelta(days=days)
    result: list[Path] = []

    # 재귀 탐색 (subagents/ 포함)
    for p in base.rglob("*.jsonl"):
        try:
            mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
            if mtime >= cutoff_ts:
                result.append(p)
        except OSError:
            pass

    return sorted(result)


# ─── 패턴 감지 ──────────────────────────────────────────────────────────────────

def _est_tokens(text: str) -> int:
    """문자열 → 토큰 수 근사 추정. 한글 포함 시 가중. 정밀 측정이 아님."""
    korean_count = sum(1 for ch in text if "가" <= ch <= "힣")
    non_korean = len(text) - korean_count
    return int(non_korean / CHARS_PER_TOKEN_EN + korean_count / 2.0)


def analyze_session(jsonl_path: Path) -> dict[str, Any]:
    """단일 세션 파일을 분석해 패턴 카운트와 토큰 집계 반환."""
    seen_ids: set[str] = set()

    # usage 집계 (dedup by message.id)
    total_input = 0
    total_output = 0
    total_cache_read = 0
    total_cache_creation = 0

    # 패턴 카운트
    read_file_paths: list[str] = []          # H2-01 탐지용
    large_tool_results: int = 0              # H2-02/H8-02
    large_tool_result_tokens: int = 0
    verbose_output_hits: int = 0             # H5-04
    cache_drops: int = 0                     # H4-03
    # H8-01: "한 assistant 메시지(턴) 내 동시 Read 개수" 최대치 (휴리스틱·근사).
    # tool_result/턴 경계에서 자연히 리셋되도록 메시지 단위로 카운트한다.
    max_reads_in_one_turn: int = 0

    # 타임스탬프 (세션 wall-time 추정)
    timestamps: list[datetime] = []

    prev_cache_ratio: float | None = None

    messages = list(iter_messages(jsonl_path))

    for obj in messages:
        # iter_messages가 dict만 yield하지만 이중 방어 (크래시 0 보장)
        if not isinstance(obj, dict):
            continue
        msg = obj.get("message", {})
        if not isinstance(msg, dict):
            continue

        # 타임스탬프
        ts_raw = obj.get("timestamp") or obj.get("ts") or obj.get("created_at")
        if ts_raw:
            try:
                ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
                timestamps.append(ts)
            except (ValueError, AttributeError):
                pass

        # usage 집계 (dedup)
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

            # H5-04: output/input 비율
            if inp > 200 and out > 0:
                ratio = out / max(inp, 1)
                if ratio > VERBOSE_OUTPUT_RATIO:
                    verbose_output_hits += 1

            # H4-03: cache_read 비율 급락
            total_tokens_this = inp + out + cr + cc
            if total_tokens_this > 0:
                cache_ratio = cr / total_tokens_this
                if prev_cache_ratio is not None and prev_cache_ratio > 0.3 and cache_ratio < 0.05:
                    cache_drops += 1
                if cr > 0 or cc > 0:
                    prev_cache_ratio = cache_ratio

        # content 분석 (tool_use / tool_result)
        role = msg.get("role", "")
        content = msg.get("content", [])
        # content가 리스트가 아니면(문자열 등) 블록 분석 대상 없음 → 빈 리스트로 폴백
        if not isinstance(content, list):
            content = []

        # H8-01: 이 메시지(턴) 안의 Read 개수만 센다. 다음 턴/tool_result에서
        # 자동으로 0부터 다시 시작하므로 분산된 정상 단일 Read는 오탐되지 않는다.
        reads_this_turn: int = 0

        for block in content:
            if not isinstance(block, dict):
                continue
            btype = block.get("type", "")

            # tool_use: Read 도구 탐지 (H2-01, H8-01)
            if btype == "tool_use":
                tool_name = block.get("name", "")
                if tool_name == "Read":
                    fp = block.get("input", {}).get("file_path", "")
                    if fp:
                        read_file_paths.append(str(fp))
                    reads_this_turn += 1
                    max_reads_in_one_turn = max(max_reads_in_one_turn, reads_this_turn)

            # tool_result: 대형 출력 탐지 (H2-02/H8-02)
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

    # H2-01: 동일 파일 경로 중복
    from collections import Counter
    path_counts = Counter(read_file_paths)
    repeated_reads = sum(cnt - 1 for cnt in path_counts.values() if cnt > 1)
    repeated_read_files = {p: cnt for p, cnt in path_counts.items() if cnt > 1}

    # H1-01/H1-03: 세션 시간 및 누적 토큰
    session_minutes = 0.0
    if len(timestamps) >= 2:
        session_minutes = (max(timestamps) - min(timestamps)).total_seconds() / 60.0
    total_tokens_all = total_input + total_output + total_cache_read + total_cache_creation

    long_session = (
        session_minutes > SESSION_MAX_MINUTES
        or total_tokens_all > SESSION_MAX_TOKENS
    )

    return {
        "file": str(jsonl_path),
        "total_input": total_input,
        "total_output": total_output,
        "total_cache_read": total_cache_read,
        "total_cache_creation": total_cache_creation,
        "total_tokens": total_tokens_all,
        "session_minutes": round(session_minutes, 1),
        # 패턴별 카운트
        "H2-01_repeated_reads": repeated_reads,
        "H2-01_repeated_files": repeated_read_files,
        "H2-02_large_tool_results": large_tool_results,
        "H2-02_large_tool_result_tokens": large_tool_result_tokens,
        "H5-04_verbose_output_hits": verbose_output_hits,
        "H4-03_cache_drops": cache_drops,
        "H1-01_long_session": 1 if long_session else 0,
        "H1-03_token_overrun": 1 if total_tokens_all > SESSION_MAX_TOKENS else 0,
        "H8-01_max_reads_in_one_turn": max_reads_in_one_turn,
    }


# ─── 집계 & 리포트 ───────────────────────────────────────────────────────────────

def aggregate(results: list[dict]) -> dict[str, Any]:
    """여러 세션 결과를 패턴별로 집계."""
    agg: dict[str, int] = defaultdict(int)
    total_tokens = 0
    total_input = 0
    total_output = 0
    total_cache_read = 0

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
        # H8-01: 한 턴에 Read >= 4개 몰아 읽은 세션 수 (근사)
        if r["H8-01_max_reads_in_one_turn"] >= 4:
            agg["H8-01"] += 1

    return {
        "pattern_counts": dict(agg),
        "total_tokens": total_tokens,
        "total_input": total_input,
        "total_output": total_output,
        "total_cache_read": total_cache_read,
        "session_count": len(results),
    }


def try_ccusage(days: int) -> str | None:
    """npx ccusage 호출 시도. 없거나 실패하면 None 반환 (graceful skip).

    실제 ccusage CLI 서브커맨드는 `daily`(report 아님). `ccusage daily`.
    """
    try:
        result = subprocess.run(
            ["npx", "--yes", "ccusage@latest", "daily"],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0 and result.stdout.strip():
            # 테이블 출력 중 앞부분만
            lines = result.stdout.strip().splitlines()
            return "\n".join(lines[:12])
    except Exception:
        pass
    return None


def print_report(agg: dict, days: int, file_count: int):
    """사람이 읽기 좋은 형식으로 출력."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"\n{'='*60}")
    print(f"tokenhabit 습관 진단 리포트  ({now_str})")
    print(f"기간: 최근 {days}일  |  세션 파일: {file_count}개  |  분석 세션: {agg['session_count']}개")
    print(f"{'='*60}")

    total_tok = agg["total_tokens"]
    total_in = agg["total_input"]
    total_out = agg["total_output"]
    total_cr = agg["total_cache_read"]
    cache_pct = (total_cr / max(total_tok, 1)) * 100

    print(f"\n[총계]  누적 토큰: {total_tok:,}  |  input: {total_in:,}  |  output: {total_out:,}")
    print(f"        캐시 히트: {total_cr:,} ({cache_pct:.1f}%)")

    # ccusage 보강 시도
    ccusage_out = try_ccusage(days)
    if ccusage_out:
        print(f"\n[ccusage 보강]\n{ccusage_out}")
    else:
        print("\n[ccusage] 미설치 또는 실패 — 총 비용 집계 생략 (npx ccusage@latest 로 별도 확인)")

    # 패턴별 집계 (카운트 내림차순)
    counts = agg["pattern_counts"]
    detected = {k: v for k, v in counts.items() if not k.endswith("_tokens") and v > 0}
    if not detected:
        print("\n감지된 습관 패턴 없음. 잘 하고 있습니다!")
        return

    sorted_patterns = sorted(detected.items(), key=lambda x: x[1], reverse=True)

    print(f"\n[감지된 습관 패턴] — 카탈로그 ID 기준")
    print(f"{'─'*60}")

    total_waste_est = 0
    for pattern_id, count in sorted_patterns:
        info = CATALOG.get(pattern_id)
        if not info:
            continue
        waste = info["token_est_per_hit"] * count
        total_waste_est += waste

        # H2-02는 추정 토큰이 직접 계산된 값 사용
        if pattern_id == "H2-02":
            raw_waste = counts.get("H2-02_tokens", 0)
            if raw_waste > 0:
                waste = raw_waste

        print(f"\n  [{pattern_id}] {info['name']}  ×{count}회")
        print(f"  추정 낭비: ~{waste:,} 토큰")
        print(f"  즉시 fix: {info['fix']}")

    print(f"\n{'─'*60}")
    print(f"  총 추정 낭비: ~{total_waste_est:,} 토큰")
    print(f"\n  * 수치는 경향 파악용 근사치입니다.")
    print(f"  * H8-01(메인스레드 탐색)은 한 턴에 Read ≥4개 몰아 읽은 세션 수 (근사).")
    print(f"{'='*60}\n")


# ─── main ────────────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(
        description="tokenhabit habit_scan — JSONL 파싱 기반 습관 진단 (25패턴 중 자동감지 가능한 8패턴)"
    )
    ap.add_argument("--days", type=int, default=7, metavar="N",
                    help="최근 N일 분석 (기본 7)")
    ap.add_argument("--project", type=Path, metavar="PATH",
                    help="특정 프로젝트 디렉토리")
    ap.add_argument("--session", type=Path, metavar="FILE",
                    help="단일 .jsonl 세션 파일")
    ap.add_argument("--json", action="store_true",
                    help="JSON 형식으로 출력")
    args = ap.parse_args()

    files = collect_jsonl_files(
        project_dir=args.project,
        session_file=args.session,
        days=args.days,
    )

    if not files:
        msg = f"분석할 .jsonl 파일 없음 (기간: {args.days}일, 경로: {CLAUDE_PROJECTS_DIR})"
        if args.json:
            print(json.dumps({"error": msg}))
        else:
            print(msg, file=sys.stderr)
        return 1

    results = [analyze_session(f) for f in files]
    agg = aggregate(results)

    if args.json:
        out = {
            "meta": {
                "days": args.days,
                "file_count": len(files),
                "session_count": agg["session_count"],
                "generated_at": datetime.now().isoformat(),
            },
            "totals": {
                "total_tokens": agg["total_tokens"],
                "total_input": agg["total_input"],
                "total_output": agg["total_output"],
                "total_cache_read": agg["total_cache_read"],
            },
            "pattern_counts": {
                k: v for k, v in agg["pattern_counts"].items()
                if not k.endswith("_tokens") and v > 0
            },
            "sessions": results,
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print_report(agg, args.days, len(files))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
