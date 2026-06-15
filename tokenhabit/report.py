"""Human-readable report rendering: color, Token Waste Score, i18n, fixes."""

from __future__ import annotations

from datetime import datetime
import os
import sys

from .catalog import info as catalog_info

# ─── ANSI color (auto-disabled when not a TTY or NO_COLOR is set) ──────────────

_USE_COLOR = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None

# Frequency signals: shown in the list, but NOT summed into the Waste Score —
# subagents and web tools are legitimate, so their raw counts would overstate waste.
SIGNAL_PATTERNS = {"H2-04", "H8-03"}


def _c(code: str, text: str) -> str:
    if not _USE_COLOR:
        return text
    return f"\033[{code}m{text}\033[0m"


def set_color(enabled: bool) -> None:
    global _USE_COLOR
    _USE_COLOR = enabled


def bold(t: str) -> str:
    return _c("1", t)


def dim(t: str) -> str:
    return _c("2", t)


def red(t: str) -> str:
    return _c("31", t)


def yellow(t: str) -> str:
    return _c("33", t)


def green(t: str) -> str:
    return _c("32", t)


def cyan(t: str) -> str:
    return _c("36", t)


# ─── i18n strings ─────────────────────────────────────────────────────────────

STR = {
    "en": {
        "title": "tokenhabit — habit scan",
        "period": "Window: last {days}d  |  session files: {files}  |  analyzed: {sessions}",
        "totals": "[Totals]  tokens: {tok:,}  |  input: {inp:,}  |  output: {out:,}",
        "cache": "          cache hits: {cr:,} ({pct:.1f}%)",
        "score": "Token Waste Score",
        "score_line": "{grade}  —  ~{pct:.0f}% of your tokens were likely wasted ({waste:,} tok)",
        "clean": "No wasteful habits detected. Nice — you're driving clean.",
        "detected": "[Detected habits]  (by catalog ID, most frequent first)",
        "waste_per": "  est. waste: ~{waste:,} tokens",
        "signal_per": "  frequency signal — not scored ({count} calls; check context)",
        "fix": "  fix: ",
        "total_waste": "  Total estimated waste: ~{waste:,} tokens",
        "share": "Share: I was wasting ~{pct:.0f}% of my Claude Code tokens. Top leak: {top}. — tokenhabit",
        "notes": [
            "  * Numbers are trend-spotting approximations, not exact billing.",
            "  * H8-01 = sessions with >=4 Reads piled into a single turn (heuristic).",
            "  * H8-03 = sessions spawning >=6 subagents; H2-04 = WebFetch/WebSearch calls.",
            "    Both are frequency signals — subagents and web tools are legit; check context.",
            "  * Want the full 28-pattern coaching? Use the tokenhabit skill in Claude Code.",
        ],
        "no_files": "No .jsonl files to analyze (window: {days}d, path: {path})",
    },
    "ko": {
        "title": "tokenhabit — 습관 진단 리포트",
        "period": "기간: 최근 {days}일  |  세션 파일: {files}개  |  분석 세션: {sessions}개",
        "totals": "[총계]  누적 토큰: {tok:,}  |  input: {inp:,}  |  output: {out:,}",
        "cache": "        캐시 히트: {cr:,} ({pct:.1f}%)",
        "score": "토큰 낭비 점수",
        "score_line": "{grade}  —  토큰의 약 {pct:.0f}%가 습관적으로 낭비됨 ({waste:,} tok)",
        "clean": "감지된 낭비 습관 없음. 잘 하고 있습니다!",
        "detected": "[감지된 습관 패턴]  (카탈로그 ID, 빈도 내림차순)",
        "waste_per": "  추정 낭비: ~{waste:,} 토큰",
        "signal_per": "  빈도 신호 — 점수 미반영 ({count}회; 맥락으로 판단)",
        "fix": "  즉시 fix: ",
        "total_waste": "  총 추정 낭비: ~{waste:,} 토큰",
        "share": "공유: 내 Claude Code 토큰의 약 {pct:.0f}%를 낭비하고 있었다. 1위 누수: {top}. — tokenhabit",
        "notes": [
            "  * 수치는 경향 파악용 근사치이며 정확한 과금이 아닙니다.",
            "  * H8-01 = 한 턴에 Read 4개 이상 몰아 읽은 세션 수 (근사).",
            "  * H8-03 = 서브에이전트 6개 이상 띄운 세션 수; H2-04 = WebFetch/WebSearch 호출 수.",
            "    둘 다 빈도 신호일 뿐 — 서브에이전트·웹툴은 정당한 도구이니 맥락으로 판단하세요.",
            "  * 전체 28패턴 코칭이 필요하면 Claude Code의 tokenhabit 스킬을 사용하세요.",
        ],
        "no_files": "분석할 .jsonl 파일 없음 (기간: {days}일, 경로: {path})",
    },
}


def _grade(waste_ratio: float) -> tuple[str, callable]:
    """Map waste ratio -> letter grade + color fn."""
    pct = waste_ratio * 100
    if pct < 5:
        return "A", green
    if pct < 12:
        return "B", green
    if pct < 20:
        return "C", yellow
    if pct < 30:
        return "D", yellow
    return "F", red


def render(agg: dict, days: int, file_count: int, lang: str, ccusage_out: str | None) -> None:
    s = STR.get(lang, STR["en"])
    bar = "═" * 64

    print()
    print(cyan(bar))
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(bold(f"{s['title']}") + dim(f"   {now}"))
    print(s["period"].format(days=days, files=file_count, sessions=agg["session_count"]))
    print(cyan(bar))

    total_tok = agg["total_tokens"]
    total_cr = agg["total_cache_read"]
    cache_pct = (total_cr / max(total_tok, 1)) * 100
    print()
    print(s["totals"].format(tok=total_tok, inp=agg["total_input"], out=agg["total_output"]))
    print(s["cache"].format(cr=total_cr, pct=cache_pct))

    if ccusage_out:
        print()
        print(dim(f"[ccusage]\n{ccusage_out}"))

    # Per-pattern waste
    counts = agg["pattern_counts"]
    detected = {k: v for k, v in counts.items() if not k.endswith("_tokens") and v > 0}
    sorted_patterns = sorted(detected.items(), key=lambda x: x[1], reverse=True)

    total_waste = 0
    pattern_lines: list[tuple[str, int, int, str, bool]] = []  # (id, count, waste, fix, is_signal)
    top_name = ""
    for pid, count in sorted_patterns:
        ci = catalog_info(pid, lang)
        if not ci:
            continue
        is_signal = pid in SIGNAL_PATTERNS
        waste = ci["token_est_per_hit"] * count
        if pid == "H2-02":
            raw = counts.get("H2-02_tokens", 0)
            if raw > 0:
                waste = raw
        if not is_signal:
            total_waste += waste
            if not top_name:  # headline reflects the dominant *scored* waste
                top_name = ci["name"]
        pattern_lines.append((pid, count, waste, ci["fix"], is_signal))

    # Token Waste Score (the shareable headline).
    # Denominator = "billable work" tokens (input + output + cache creation),
    # excluding cache reads — those are cheap and so voluminous they would
    # otherwise dilute every score down to ~1%.
    billable_base = max(total_tok - total_cr, 1)
    waste_ratio = total_waste / billable_base
    grade, gcolor = _grade(waste_ratio)
    print()
    print(bold(f"  {s['score']}: ") + gcolor(bold(
        s["score_line"].format(grade=grade, pct=waste_ratio * 100, waste=total_waste)
    )))

    if not sorted_patterns:
        print()
        print(green(f"  {s['clean']}"))
        print(cyan(bar))
        print()
        return

    print()
    print(bold(s["detected"]))
    print(dim("─" * 64))
    for pid, count, waste, fix, is_signal in pattern_lines:
        ci = catalog_info(pid, lang)
        print()
        print(yellow(f"  [{pid}] ") + bold(ci["name"]) + dim(f"  ×{count}"))
        if is_signal:
            print(dim(s["signal_per"].format(count=count)))
        else:
            print(s["waste_per"].format(waste=waste))
        print(dim(s["fix"]) + fix)

    print()
    print(dim("─" * 64))
    print(bold(s["total_waste"].format(waste=total_waste)))
    print()
    print(cyan("  " + s["share"].format(pct=waste_ratio * 100, top=top_name)))
    print()
    for note in s["notes"]:
        print(dim(note))
    print(cyan(bar))
    print()
