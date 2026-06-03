#!/usr/bin/env python3
"""
tokenhabit — hook_check.py  v1.1  (MODE4 런타임 강제 hook)

Claude Code hook으로 등록해 MODE4 행동 룰을 실시간 경고.
경고는 stderr에만, exit 0 고정 — 절대 블로킹하지 않음.

지원 이벤트:
  UserPromptSubmit  — 모호 프롬프트(H5-01/H5-02) · 첫 메시지 긴 설명(H7-01) 감지
  PreToolUse(Bash)  — 대형 출력 위험 명령(H2-02/H8-02) 감지
  PreToolUse(Read)  — 이미 읽은 파일 재요청(H2-01) 감지

Usage:
  # Claude Code가 stdin으로 hook payload JSON을 전달
  python3 hook_check.py userprompt
  python3 hook_check.py pretooluse
  python3 hook_check.py --self-test

settings.json 등록 예제:
  {
    "hooks": {
      "UserPromptSubmit": [
        {"hooks": [{"type": "command",
          "command": "python3 /path/to/skill/scripts/hook_check.py userprompt"}]}
      ],
      "PreToolUse": [
        {"matcher": "Bash",
          "hooks": [{"type": "command",
            "command": "python3 /path/to/skill/scripts/hook_check.py pretooluse"}]},
        {"matcher": "Read",
          "hooks": [{"type": "command",
            "command": "python3 /path/to/skill/scripts/hook_check.py pretooluse"}]}
      ]
    }
  }

표준 라이브러리만. LLM 호출 0회.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path

# ─── 상수 ────────────────────────────────────────────────────────────────────────

# UserPromptSubmit: 모호 프롬프트 감지 (H5-01/H5-02)
VAGUE_PROMPT_MAX_LEN = 25               # 이 글자 수 이하이면 매우 짧은 프롬프트
VAGUE_PROMPT_PATTERNS = [
    r"^(고쳐줘|수정해줘|분석해줘|확인해줘|개선해줘|리팩토링해줘|설명해줘|만들어줘|작성해줘|검토해줘)[\.\s!?]*$",
    r"^(fix|analyze|check|improve|refactor|explain|create|write|review)\s*\.?\s*$",
]

# UserPromptSubmit: 첫 메시지 긴 설명 감지 (H7-01)
FIRST_MSG_LONG_THRESHOLD = 500          # 첫 메시지가 이 글자 이상이면 CLAUDE.md 영속화 권고

# PreToolUse Bash: 대형 출력 위험 명령 패턴 (H2-02/H8-02)
# 필터 없이 대량 출력 가능성이 있는 명령들
RISKY_BASH_PATTERNS = [
    r"\bnpm\s+(test|run\s+build|install)\b",
    r"\bpytest\b",
    r"\bgo\s+test\b",
    r"\bcargo\s+(test|build)\b",
    r"\bnext\s+build\b",
    r"\bcat\s+\S+\.(log|txt|json)\b",
    r"\bjournalctl\b",
    r"\bdocker\s+logs\b",
]
# 필터가 이미 붙어 있으면 경고 면제 (| grep, | head, | tail, > 파일, 2>/dev/null 등)
FILTER_PATTERNS = [
    r"\|\s*(grep|head|tail|awk|sed|wc|cut|sort|uniq)",
    r"\d+>\s*\S+",     # 리디렉션
    r">\s*\S+\.log",
    r"2>/dev/null",
]

# 임시 파일 기반 세션 상태. 세션 ID는 환경변수, 없으면 pid 폴백.
def _session_key() -> str:
    session_id = os.environ.get("CLAUDE_SESSION_ID") or f"pid{os.getppid()}"
    return re.sub(r"[^a-zA-Z0-9_-]", "_", session_id)[:40]


# H2-01: Read 재읽기 추적 파일
def _session_reads_path() -> Path:
    return Path(tempfile.gettempdir()) / f"tokenhabit_{_session_key()}_reads"


# H7-01: "첫 사용자 프롬프트 이미 봤음" 마커 — Read 추적과 반드시 분리해야
# Read가 먼저 일어나도 H7-01이 정상 발동한다.
def _session_seen_prompt_path() -> Path:
    return Path(tempfile.gettempdir()) / f"tokenhabit_{_session_key()}_seen_prompt"


def _load_session_reads() -> set[str]:
    p = _session_reads_path()
    if not p.exists():
        return set()
    try:
        return set(p.read_text(encoding="utf-8").splitlines())
    except OSError:
        return set()


def _save_session_reads(paths: set[str]) -> None:
    p = _session_reads_path()
    try:
        p.write_text("\n".join(sorted(paths)), encoding="utf-8")
    except OSError:
        pass  # 쓰기 실패해도 무시


# ─── 이벤트별 경고 생성 ─────────────────────────────────────────────────────────

def warn(msg: str) -> None:
    """stderr에 경고 한 줄 출력."""
    print(msg, file=sys.stderr)


def _extract_message_content(payload: dict) -> str:
    """message.content 폴백 추출. 리스트면 text 블록을 join."""
    mc = payload.get("message", {})
    if not isinstance(mc, dict):
        return ""
    content = mc.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
            elif isinstance(block, str):
                parts.append(block)
        return " ".join(parts)
    return ""


def check_userprompt(payload: dict) -> None:
    """UserPromptSubmit hook 처리."""
    prompt = str(
        payload.get("prompt")
        or payload.get("user_prompt")
        or _extract_message_content(payload)
        or ""
    ).strip()

    if not prompt:
        return

    prompt_len = len(prompt)

    # (a) 매우 짧고 모호한 프롬프트 → H5-01/H5-02
    is_vague = False
    if prompt_len <= VAGUE_PROMPT_MAX_LEN:
        for pat in VAGUE_PROMPT_PATTERNS:
            if re.match(pat, prompt, re.IGNORECASE):
                is_vague = True
                break
        # 패턴 미일치여도 너무 짧고 경로·파일명이 없으면 모호로 판단
        if not is_vague and prompt_len < 15:
            is_vague = True

    if is_vague:
        warn(
            f"[tokenhabit H5-01/H5-02] 모호한 프롬프트 감지: '{prompt[:40]}'\n"
            "  → 파일 경로(@src/foo.py), 증상, 완료 기준을 명시하면 탐색 토큰 절감."
        )

    # (b) 세션 첫 사용자 프롬프트가 긴 프로젝트 설명 → H7-01
    # 첫 프롬프트 여부는 전용 마커 파일로 판단 (Read 추적과 분리 — M4 수정).
    seen_marker = _session_seen_prompt_path()
    is_first_prompt = not seen_marker.exists()
    # 이 프롬프트를 봤다고 마커 기록 (다음 프롬프트는 첫 프롬프트 아님)
    try:
        seen_marker.write_text("1", encoding="utf-8")
    except OSError:
        pass
    if is_first_prompt and prompt_len >= FIRST_MSG_LONG_THRESHOLD:
        warn(
            f"[tokenhabit H7-01] 첫 메시지 길이 {prompt_len:,}자 — 프로젝트 설명이 매 세션 반복되고 있을 수 있음.\n"
            "  → /init 후 CLAUDE.md에 영속화하면 세션당 재타이핑 제거."
        )


def check_pretooluse(payload: dict) -> None:
    """PreToolUse hook 처리 — Bash / Read 모두 이 함수로 처리."""
    tool_name = str(
        payload.get("tool_name")
        or payload.get("tool", {}).get("name")
        or ""
    ).strip()

    tool_input = payload.get("tool_input") or payload.get("input") or {}
    if not isinstance(tool_input, dict):
        tool_input = {}

    # ── Bash: 대형 출력 위험 탐지 (H2-02/H8-02) ──────────────────────────────
    if tool_name == "Bash":
        command = str(tool_input.get("command", "")).strip()
        if not command:
            return

        # 위험 패턴 일치?
        risky = any(re.search(pat, command, re.IGNORECASE) for pat in RISKY_BASH_PATTERNS)
        if not risky:
            return

        # 이미 필터가 붙어 있으면 면제
        has_filter = any(re.search(pat, command, re.IGNORECASE) for pat in FILTER_PATTERNS)
        if has_filter:
            return

        # 짧은 명령(단순 echo 등) 면제
        if len(command) < 8:
            return

        warn(
            f"[tokenhabit H2-02/H8-02] 대형 stdout 위험 명령: `{command[:80]}`\n"
            "  → | grep -A5 'ERROR\\|FAIL' 또는 > /tmp/out.log 필터 추가 권고. 차단 아님."
        )

    # ── Read: 재읽기 탐지 (H2-01) ─────────────────────────────────────────────
    elif tool_name == "Read":
        file_path = str(tool_input.get("file_path", "")).strip()
        if not file_path:
            return

        already_read = _load_session_reads()
        if file_path in already_read:
            warn(
                f"[tokenhabit H2-01] 이미 읽은 파일 재요청: {file_path}\n"
                "  → '아까 읽은 파일에서 X 부분...' 컨텍스트 참조로 재읽기 생략 권고. 차단 아님."
            )
        else:
            already_read.add(file_path)
            _save_session_reads(already_read)


# ─── self-test ───────────────────────────────────────────────────────────────────

SAMPLE_USERPROMPT_VAGUE = {"prompt": "고쳐줘"}
# 임계(500자) 초과하도록 충분히 길게 — H7-01 실제 발동 검증용
SAMPLE_USERPROMPT_LONG = {"prompt": "안녕하세요. 이 프로젝트는 Next.js 15와 TypeScript를 사용하는 SaaS 플랫폼입니다. " * 12}
SAMPLE_PRETOOLUSE_BASH = {
    "tool_name": "Bash",
    "tool_input": {"command": "npm test"}
}
SAMPLE_PRETOOLUSE_BASH_OK = {
    "tool_name": "Bash",
    "tool_input": {"command": "npm test | grep -A5 FAIL"}
}
SAMPLE_PRETOOLUSE_READ = {
    "tool_name": "Read",
    "tool_input": {"file_path": "/some/file.ts"}
}


def self_test() -> int:
    warn("=== [tokenhabit hook_check self-test] ===\n")

    warn("-- Test 1: 모호한 프롬프트 (H5-01) --")
    check_userprompt(SAMPLE_USERPROMPT_VAGUE)

    warn("\n-- Test 2: 첫 메시지 긴 설명 (H7-01) --")
    # 전용 마커 파일 제거 → '첫 프롬프트' 상태로. (Read 추적과 분리되어 있음)
    seen = _session_seen_prompt_path()
    if seen.exists():
        seen.unlink()
    check_userprompt(SAMPLE_USERPROMPT_LONG)
    warn(f"  (위 H7-01 경고 떠야 정상. 샘플 길이 {len(SAMPLE_USERPROMPT_LONG['prompt'])}자)")

    warn("\n-- Test 2b: Read가 먼저 일어나도 H7-01 발동 확인 (M4 회귀) --")
    # Read 추적 파일을 먼저 생성한 뒤에도 H7-01이 발동해야 한다.
    if seen.exists():
        seen.unlink()
    rp = _session_reads_path()
    if rp.exists():
        rp.unlink()
    check_pretooluse({"tool_name": "Read", "tool_input": {"file_path": "/early/read.ts"}})
    check_userprompt(SAMPLE_USERPROMPT_LONG)
    warn("  (위 H7-01 경고 떠야 정상 — Read 선행에도 침묵하지 않음)")

    warn("\n-- Test 3: Bash 대형 출력 위험 (H2-02) --")
    check_pretooluse(SAMPLE_PRETOOLUSE_BASH)

    warn("\n-- Test 4: Bash 필터 있음 → 경고 없어야 함 --")
    check_pretooluse(SAMPLE_PRETOOLUSE_BASH_OK)
    warn("  (경고 없으면 정상)")

    warn("\n-- Test 5: Read 첫 번째 요청 → 경고 없어야 함 --")
    # 세션 reads 초기화
    if rp.exists():
        rp.unlink()
    check_pretooluse(SAMPLE_PRETOOLUSE_READ)
    warn("  (경고 없으면 정상)")

    warn("\n-- Test 6: Read 동일 파일 재요청 (H2-01) → 경고 있어야 함 --")
    check_pretooluse(SAMPLE_PRETOOLUSE_READ)

    warn("\n=== self-test 완료. exit 0 ===")
    return 0


# ─── main ────────────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(
        description="tokenhabit hook_check — MODE4 런타임 경고. stderr만, exit 0 고정."
    )
    ap.add_argument(
        "mode",
        choices=["userprompt", "pretooluse", "self-test"],
        help="훅 이벤트 종류 또는 self-test",
    )
    args = ap.parse_args()

    if args.mode == "self-test":
        return self_test()

    # stdin에서 JSON payload 읽기 (실패 시 빈 dict로 폴백)
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except Exception:
        payload = {}

    try:
        if args.mode == "userprompt":
            check_userprompt(payload)
        elif args.mode == "pretooluse":
            check_pretooluse(payload)
    except Exception:
        # 어떤 입력에도 크래시 없이 종료
        pass

    return 0  # 항상 exit 0


if __name__ == "__main__":
    raise SystemExit(main())
