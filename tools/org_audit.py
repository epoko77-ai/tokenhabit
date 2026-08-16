#!/usr/bin/env python3
"""Org configuration audit — only rules that survive the "is this obvious?" test.

The design spec set a kill criterion: if the top findings are just "over 200
lines", "too many MCP servers", "too many skills", stop building and ship a
checklist instead, because a threshold nobody can justify is not a finding.

So this file deliberately does NOT implement inventory rules. There is no
defensible answer to "how many skills is too many". What it implements are the
three classes that passed the test on real data — each one measured on both
sides, with no arbitrary number in the middle:

  ORG-USE-001  loaded but never invoked   cost from /context, use from session logs
  ORG-DUP-001  the same thing installed twice
  ORG-REF-001  references that point at nothing

Run:

    python3 tools/org_audit.py --snapshot before.json
    python3 tools/org_audit.py --snapshot before.json --days 30 --json
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
import argparse
import json
import os
import sys

CLAUDE_DIR = Path.home() / ".claude"

# Below this many sessions, "never invoked" is not evidence of anything.
MIN_SESSIONS = 20


# ─── usage from session logs ──────────────────────────────────────────────────

def scan_usage(days: int) -> tuple[Counter, Counter, int]:
    """Which agent types and skills were actually invoked, across all projects."""
    agents: Counter[str] = Counter()
    skills: Counter[str] = Counter()
    sessions = 0
    base = CLAUDE_DIR / "projects"
    if not base.exists():
        return agents, skills, sessions
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    for path in base.rglob("*.jsonl"):
        if "subagents" in path.parts:
            continue
        try:
            if datetime.fromtimestamp(path.stat().st_mtime, timezone.utc) < cutoff:
                continue
        except OSError:
            continue
        sessions += 1
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    # cheap prefilter — these lines are the overwhelming majority
                    if '"Agent"' not in line and '"Skill"' not in line:
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    msg = obj.get("message")
                    if not isinstance(msg, dict):
                        continue
                    for block in msg.get("content") or []:
                        if not isinstance(block, dict) or block.get("type") != "tool_use":
                            continue
                        inp = block.get("input") or {}
                        if not isinstance(inp, dict):
                            continue
                        if block.get("name") == "Agent" and inp.get("subagent_type"):
                            agents[inp["subagent_type"]] += 1
                        elif block.get("name") == "Skill" and inp.get("skill"):
                            skills[inp["skill"]] += 1
        except OSError:
            continue
    return agents, skills, sessions


# ─── rules ────────────────────────────────────────────────────────────────────

def rule_never_invoked(items: list[dict], used: Counter, *, group: str,
                       sessions: int, days: int) -> dict:
    """ORG-USE-001 — loaded into every session, invoked in none of them."""
    if sessions < MIN_SESSIONS:
        return {
            "rule_id": "ORG-USE-001", "subject": group, "status": "inconclusive",
            "reason": "insufficient_sessions",
            "detail": f"{days}일 창에서 세션 {sessions}개 < 최소 표본 {MIN_SESSIONS}개. "
                      "증거의 부재를 부재의 증거로 바꿀 수 없다.",
        }

    # A skill can be invoked as "name" or "namespace:name"; match on both.
    used_keys = set(used)
    used_tails = {k.split(":")[-1] for k in used_keys}

    unused, used_items = [], []
    for e in items:
        name = e["name"]
        hit = name in used_keys or name.split(":")[-1] in used_tails
        (used_items if hit else unused).append(e)

    total = sum((e.get("tokens") or 0) for e in items)
    wasted = sum((e.get("tokens") or 0) for e in unused)
    return {
        "rule_id": "ORG-USE-001",
        "subject": group,
        "status": "finding" if unused else "pass",
        "evidence": {"cost": "runtime_observed", "usage": "runtime_observed"},
        "window_days": days,
        "sessions_analyzed": sessions,
        "loaded": len(items),
        "invoked": len(used_items),
        "never_invoked": len(unused),
        "tokens_total": total,
        "tokens_never_invoked": wasted,
        "share": round(wasted / total, 3) if total else 0.0,
        "top_unused": sorted(
            ({"name": e["name"], "tokens": e.get("tokens") or 0} for e in unused),
            key=lambda x: -x["tokens"])[:10],
    }


def rule_duplicate_install(items: list[dict], *, group: str) -> dict:
    """ORG-DUP-001 — the same capability provided twice under different namespaces."""
    by_tail: defaultdict[str, list[dict]] = defaultdict(list)
    for e in items:
        by_tail[e["name"].split(":")[-1]].append(e)
    dupes = {k: v for k, v in by_tail.items() if len(v) > 1}
    redundant = sum(sum((e.get("tokens") or 0) for e in v[1:]) for v in dupes.values())
    return {
        "rule_id": "ORG-DUP-001",
        "subject": group,
        "status": "finding" if dupes else "pass",
        "evidence": {"cost": "runtime_observed"},
        "duplicate_names": len(dupes),
        "redundant_tokens": redundant,
        "examples": [{"name": k, "provided_by": [e["name"] for e in v]}
                     for k, v in list(dupes.items())[:5]],
    }


def rule_dead_references() -> dict:
    """ORG-REF-001 — symlinks and imports that point at nothing."""
    broken = []
    for sub in ("commands", "skills", "agents", "rules"):
        d = CLAUDE_DIR / sub
        if not d.exists():
            continue
        for p in d.rglob("*"):
            if p.is_symlink() and not p.exists():
                broken.append({"path": str(p), "target": os.readlink(p)})
    return {
        "rule_id": "ORG-REF-001",
        "subject": "claude_dir",
        "status": "finding" if broken else "pass",
        "evidence": {"existence": "config_observed"},
        "broken": len(broken),
        "items": broken[:10],
    }


# ─── report ───────────────────────────────────────────────────────────────────

def render(findings: list[dict]) -> None:
    print()
    print("═" * 72)
    print("조직 구성 감사 — 자명하지 않은 것만")
    print("═" * 72)

    for f in findings:
        rid, subj, status = f["rule_id"], f["subject"], f["status"]
        head = f"[{rid}] {subj}"
        if status == "inconclusive":
            print(f"\n{head}  판정보류 ({f['reason']})")
            print(f"  {f['detail']}")
            continue
        if status == "pass":
            print(f"\n{head}  이상 없음")
            continue

        if rid == "ORG-USE-001":
            print(f"\n{head}  로드됐지만 호출된 적 없음")
            print(f"  최근 {f['window_days']}일 · 세션 {f['sessions_analyzed']}개 분석")
            print(f"  로드 {f['loaded']}개 중 호출 {f['invoked']}개 · "
                  f"미호출 {f['never_invoked']}개")
            print(f"  미호출분 {f['tokens_never_invoked']:,} 토큰 "
                  f"(이 그룹 {f['tokens_total']:,} 중 {f['share'] * 100:.0f}%) — 매 세션 반복")
            if f["top_unused"]:
                print("  비용 상위 미호출:")
                for e in f["top_unused"][:5]:
                    print(f"    {e['tokens']:>6,}  {e['name']}")
        elif rid == "ORG-DUP-001":
            print(f"\n{head}  같은 것이 두 번 설치됨")
            print(f"  중복 {f['duplicate_names']}건 · 중복분 {f['redundant_tokens']:,} 토큰")
            for e in f["examples"][:3]:
                print(f"    {e['name']}: {' / '.join(e['provided_by'])}")
        elif rid == "ORG-REF-001":
            print(f"\n{head}  가리키는 대상이 없는 참조")
            print(f"  깨진 링크 {f['broken']}건")
            for e in f["items"][:5]:
                print(f"    {Path(e['path']).name}  →  {e['target']}")

    print()
    print("─" * 72)
    print("  이 감사가 하지 않는 것:")
    print("    * 개수 임계 판정. \"스킬 몇 개부터 과다\"에는 방어 가능한 답이 없어")
    print("      그런 룰은 아예 만들지 않았다.")
    print("    * 절감액 추정. 여기 토큰은 '세션 시작 시 실리는 양'이지 과금액이 아니다.")
    print("      프리픽스는 2번째 턴부터 캐시 읽기(0.1x)로 서빙된다.")
    print("  '호출된 적 없음'은 '쓸모없음'이 아니다. 분기 1회 쓰는 것일 수도 있고,")
    print("  창 밖에서 쓰였을 수도 있다. 지우기 전에 소유자에게 확인하라.")
    print("═" * 72)
    print()


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="조직 구성 감사 (자명하지 않은 룰만).")
    ap.add_argument("--snapshot", type=Path, required=True,
                    help="baseline_context.py --snapshot 산출물")
    ap.add_argument("--days", type=int, default=30, help="사용 여부를 볼 창 (기본 30일)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    snap = json.loads(args.snapshot.read_text(encoding="utf-8"))
    items = snap.get("context", {}).get("items", {})
    agents_used, skills_used, sessions = scan_usage(args.days)

    findings = [
        rule_never_invoked(items.get("custom_agents", []), agents_used,
                           group="custom_agents", sessions=sessions, days=args.days),
        rule_never_invoked(items.get("skills", []), skills_used,
                           group="skills", sessions=sessions, days=args.days),
        rule_duplicate_install(items.get("skills", []), group="skills"),
        rule_duplicate_install(items.get("custom_agents", []), group="custom_agents"),
        rule_dead_references(),
    ]

    if args.json:
        print(json.dumps({"schema": "tokenhabit-org-audit/1", "findings": findings},
                         ensure_ascii=False, indent=2))
    else:
        render(findings)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
