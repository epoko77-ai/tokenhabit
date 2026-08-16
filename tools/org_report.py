#!/usr/bin/env python3
"""Executive report — a decision document, not a scoreboard.

The spec is explicit about what an org-facing report must not be: no A-F grade,
no finding count as a headline, no savings figure. An engineering leader cannot
act on "you scored D". They can act on "this change affects these repos, takes
this long, carries this risk, and here is how to undo it".

So every finding renders with the four things a decision needs — scope, effort,
risk, rollback — and the report states its own coverage so a reader knows what
the audit did not see.

    python3 tools/org_report.py --snapshot before.json --audit audit.json \\
        --out report.md
    python3 tools/org_report.py --snapshot before.json --audit audit.json \\
        --before before.json --after after.json --out report.md
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import argparse
import json
import sys

# Remediation metadata per rule. Effort and risk are judgements, and are labelled
# as such in the report rather than dressed up as measurements.
REMEDIATION = {
    "ORG-USE-001": {
        "action": "30일 창에서 호출 0회인 항목을 비활성화 (삭제 아님)",
        "scope": "머신 전역 — 해당 사용자의 모든 세션",
        "effort": "낮음 — 디렉토리 이동 또는 프로젝트 스코프로 강등",
        "risk": "**중간.** 호출 0회는 쓸모없음이 아니다. 분기 1회 쓰는 것이거나 "
                "창 밖에서 쓰였을 수 있다. 소유자 확인 없이 지우면 업무가 막힌다.",
        "rollback": "디렉토리를 되돌리면 다음 세션부터 복구. 데이터 손실 없음",
        "owner": "각 항목 소유자 (개인 스코프면 본인)",
    },
    "ORG-DUP-001": {
        "action": "중복 제공 플러그인 중 하나를 비활성화",
        "scope": "머신 전역",
        "effort": "낮음 — `/plugin` 에서 하나 해제",
        "risk": "**낮음.** 같은 기능이 두 벌이라 하나를 꺼도 기능이 유지된다. "
                "단 두 벌의 버전이 다를 수 있으니 어느 쪽을 남길지는 확인할 것.",
        "rollback": "다시 활성화하면 즉시 복구",
        "owner": "플랫폼팀 또는 설치한 사람",
    },
    "ORG-REF-001": {
        "action": "깨진 심링크 삭제 또는 대상 경로 수정",
        "scope": "해당 파일만",
        "effort": "낮음 — 파일 정리",
        "risk": "**낮음.** 이미 동작하지 않는 참조다.",
        "rollback": "삭제 전 목록을 남겨두면 재생성 가능",
        "owner": "설정 소유자",
    },
}

RULE_BASIS = {
    "ORG-USE-001": "비용=`/context` 실측 · 사용=세션 로그 실측. 임계값 없음(호출 0회는 사실 판정)",
    "ORG-DUP-001": "`/context` 항목 목록 실측. 임계값 없음(동일 이름 존재는 사실 판정)",
    "ORG-REF-001": "파일시스템 실측. 임계값 없음(링크 대상 부재는 사실 판정)",
}


def fmt(n) -> str:
    return f"{n:,}" if isinstance(n, int) else str(n)


def headline_findings(findings: list[dict]) -> list[dict]:
    """Rank by tokens carried, not by count. A count headline rewards noisy rules."""
    scored = []
    for f in findings:
        if f.get("status") != "finding":
            continue
        weight = f.get("tokens_never_invoked") or f.get("redundant_tokens") or 0
        scored.append((weight, f))
    scored.sort(key=lambda x: -x[0])
    return [f for _, f in scored]


def describe(f: dict) -> tuple[str, str]:
    rid = f["rule_id"]
    if rid == "ORG-USE-001":
        return (
            f"{f['subject']} — 로드 {f['loaded']}개 중 {f['never_invoked']}개가 호출 0회",
            f"매 세션 **{fmt(f['tokens_never_invoked'])} 토큰**이 실리고, 최근 "
            f"{f['window_days']}일 {f['sessions_analyzed']}개 세션에서 한 번도 호출되지 "
            f"않았습니다 (이 그룹 비용의 {f['share'] * 100:.0f}%).",
        )
    if rid == "ORG-DUP-001":
        return (
            f"{f['subject']} — 같은 것이 두 번 설치됨 ({f['duplicate_names']}건)",
            f"중복분 **{fmt(f['redundant_tokens'])} 토큰**이 매 세션 실립니다. "
            "네임스페이스 접두사가 달라 목록에서는 중복으로 보이지 않습니다.",
        )
    if rid == "ORG-REF-001":
        return (
            f"설정 디렉토리 — 대상이 없는 참조 {f['broken']}건",
            "가리키는 파일이 존재하지 않습니다. 토큰 비용은 없지만 설정이 "
            "의도대로 동작하지 않는다는 신호입니다.",
        )
    return (rid, "")


def render(snapshot: dict, audit: dict, before: dict | None, after: dict | None) -> str:
    ctx = snapshot.get("context", {})
    findings = audit.get("findings", [])
    ranked = headline_findings(findings)
    inconclusive = [f for f in findings if f.get("status") == "inconclusive"]
    passed = [f for f in findings if f.get("status") == "pass"]

    total = ctx.get("total_tokens") or 0
    window = ctx.get("window_tokens") or 0
    L: list[str] = []
    A = L.append

    A("# AI 코딩 설정 감사 보고서")
    A("")
    A(f"생성: {datetime.now(timezone.utc).strftime('%Y-%m-%d')} · "
      f"측정 모델 `{ctx.get('model')}`")
    A("")

    # ── 1. 감사 범위와 커버리지 ────────────────────────────────────────────────
    A("## 1. 감사 범위")
    A("")
    A("| 항목 | 값 |")
    A("|---|---|")
    A(f"| 대상 도구 | Claude Code |")
    A(f"| 측정 방식 | `/context` 실측 + 세션 로그 교차 |")
    A(f"| 세션 시작 고정비 | **{fmt(total)} / {fmt(window)} 토큰** "
      f"({total / window * 100:.0f}%)" if window else "| 세션 시작 고정비 | — |")
    sess = next((f.get("sessions_analyzed") for f in findings if f.get("sessions_analyzed")), None)
    days = next((f.get("window_days") for f in findings if f.get("window_days")), None)
    if sess:
        A(f"| 사용 여부 관측 창 | 최근 {days}일 · 세션 {sess}개 |")
    A(f"| 적용 룰 | {len({f['rule_id'] for f in findings})}종 |")
    A("")
    unparsed = ctx.get("unparsed_sections") or []
    if unparsed or inconclusive:
        A("**커버리지 한계 — 이 감사가 보지 못한 것**")
        A("")
        for u in unparsed:
            A(f"- `/context` 의 `{u}` 섹션을 해석하지 못했습니다. 포맷 변경 가능성.")
        for f in inconclusive:
            A(f"- `{f['rule_id']}` / {f['subject']}: 판정보류 (`{f.get('reason')}`) — "
              f"{f.get('detail', '')}")
        A("")
    else:
        A("커버리지 결손 없음. 모든 룰이 판정에 도달했습니다.")
        A("")

    # ── 2. 확인된 시스템 이슈 ─────────────────────────────────────────────────
    A("## 2. 확인된 시스템 이슈")
    A("")
    if not ranked:
        A("확인된 이슈 없음.")
        A("")
    for i, f in enumerate(ranked[:3], 1):
        title, body = describe(f)
        rem = REMEDIATION.get(f["rule_id"], {})
        A(f"### {i}. {title}")
        A("")
        A(body)
        A("")
        A("| | |")
        A("|---|---|")
        A(f"| 조치 | {rem.get('action', '—')} |")
        A(f"| 적용 범위 | {rem.get('scope', '—')} |")
        A(f"| 작업량 (판단) | {rem.get('effort', '—')} |")
        A(f"| 위험 (판단) | {rem.get('risk', '—')} |")
        A(f"| 되돌리기 | {rem.get('rollback', '—')} |")
        A(f"| 담당 | {rem.get('owner', '—')} |")
        A(f"| 근거 | {RULE_BASIS.get(f['rule_id'], '—')} |")
        A("")
        if f["rule_id"] == "ORG-USE-001" and f.get("top_unused"):
            A("<details><summary>비용 상위 미호출 항목</summary>")
            A("")
            A("| 토큰 | 항목 |")
            A("|---|---|")
            for e in f["top_unused"][:10]:
                A(f"| {fmt(e['tokens'])} | `{e['name']}` |")
            A("")
            A("</details>")
            A("")

    if len(ranked) > 3:
        A(f"그 외 {len(ranked) - 3}건은 기술 부록 참조.")
        A("")

    # ── 3. 변경 전후 ──────────────────────────────────────────────────────────
    if before and after:
        bc, ac = before.get("context", {}), after.get("context", {})
        bt, at = bc.get("total_tokens") or 0, ac.get("total_tokens") or 0
        A("## 3. 변경 전후 config footprint")
        A("")
        A("| | before | after | 변화 |")
        A("|---|---|---|---|")
        A(f"| 세션 시작 고정비 | {fmt(bt)} | {fmt(at)} | {at - bt:+,} |")
        for k in sorted(set(bc.get("categories", {})) | set(ac.get("categories", {}))):
            if k.lower() == "free space":
                continue
            b, a = bc["categories"].get(k, 0), ac["categories"].get(k, 0)
            if b != a:
                A(f"| {k} | {fmt(b)} | {fmt(a)} | {a - b:+,} |")
        A("")
        same_model = bc.get("model") == ac.get("model")
        A(f"**귀속 등급: {'descriptive' if same_model else '비교 불가'}**")
        A("")
        if not same_model:
            A("> ⚠️ 두 측정의 모델이 다릅니다. 토큰 회계 자체가 달라 이 표를 "
              "개입 효과로 읽으면 안 됩니다.")
        else:
            A("> 이 표는 **설정이 이만큼 바뀌었다**까지만 말합니다. "
              "비용 절감액이 아니고(프리픽스는 2번째 턴부터 캐시 읽기 0.1x로 서빙됩니다), "
              "인과도 아니며(같은 기간 다른 변경이 있었을 수 있습니다), "
              "품질 지표 없이 개선이라 부를 수 없습니다.")
        A("")
        A("**필요한 품질 guardrail** — 아래 중 최소 하나를 함께 관측하지 않으면 "
          "이 변화를 개선으로 보고하지 마십시오: 작업 완료율 · 재작업 빈도 · "
          "CI 실패율 · 동일 유형 작업의 wall-clock · 한도 차단 횟수.")
        A("")

    # ── 4. 다음 30일 ──────────────────────────────────────────────────────────
    A("## 4. 다음 30일 실행")
    A("")
    A("1. **소유자 확인** — 호출 0회 항목 목록을 소유자에게 회람. "
      "지우지 말고 \"쓰는가\"만 물을 것. 이 단계 없이 삭제하면 업무가 막힙니다.")
    A("2. **명백한 사고부터** — 중복 설치와 깨진 참조는 소유자 확인 없이 바로 정리 가능.")
    A("3. **기준선 재측정** — 개입 2~4주 후 같은 방식으로 다시 측정. "
      "모델·작업 디렉토리를 동일하게 유지해야 비교가 성립합니다.")
    A("4. **guardrail 동시 관측** — 위 지표 중 하나를 개입 전부터 기록.")
    A("")

    # ── 5. 기술 부록 ──────────────────────────────────────────────────────────
    A("## 5. 기술 부록")
    A("")
    A("### 적용 룰과 근거")
    A("")
    A("| 룰 | 판정 | 근거 |")
    A("|---|---|---|")
    for f in findings:
        A(f"| `{f['rule_id']}` / {f['subject']} | {f['status']} | "
          f"{RULE_BASIS.get(f['rule_id'], '—')} |")
    A("")
    if passed:
        names = ", ".join(f"`{f['rule_id']}`/{f['subject']}" for f in passed)
        A(f"이상 없음으로 판정된 룰: {names}")
        A("")

    A("### 이 감사가 하지 않는 것")
    A("")
    A("- **개수 임계 판정.** \"스킬 몇 개부터 과다\"에 방어 가능한 답이 없어 "
      "그런 룰은 만들지 않았습니다. 모든 판정은 사실 판정(호출 0회, 중복 존재, "
      "대상 부재)이며 임의 임계값이 없습니다.")
    A("- **절감액 추정.** 여기 토큰은 세션 시작 시 실리는 양이지 과금액이 아닙니다.")
    A("- **개인 평가.** 이 보고서의 단위는 설정 항목이며 사람이 아닙니다. "
      "개인별 집계·순위는 산출하지 않습니다.")
    A("")
    A("### 오탐 조건")
    A("")
    A("- `ORG-USE-001`: 관측 창(기본 30일)보다 드물게 쓰는 항목, 창 시작 이후 "
      "추가된 항목, 다른 머신에서 쓰는 항목은 호출 0회로 보입니다.")
    A("- `ORG-DUP-001`: 두 벌의 버전이 의도적으로 다를 수 있습니다(안정판/개발판).")
    A("- 표본이 20세션 미만이면 `ORG-USE-001` 은 판정보류로 빠집니다.")
    A("")
    return "\n".join(L) + "\n"


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="컨설팅용 조직 리포트를 렌더링한다.")
    ap.add_argument("--snapshot", type=Path, required=True)
    ap.add_argument("--audit", type=Path, required=True)
    ap.add_argument("--before", type=Path)
    ap.add_argument("--after", type=Path)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args(argv)

    md = render(
        json.loads(args.snapshot.read_text(encoding="utf-8")),
        json.loads(args.audit.read_text(encoding="utf-8")),
        json.loads(args.before.read_text(encoding="utf-8")) if args.before else None,
        json.loads(args.after.read_text(encoding="utf-8")) if args.after else None,
    )
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(md, encoding="utf-8")
        print(f"리포트 저장: {args.out}  ({len(md):,} bytes)", file=sys.stderr)
    else:
        sys.stdout.write(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
