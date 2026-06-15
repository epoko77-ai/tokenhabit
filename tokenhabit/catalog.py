"""Pattern catalog (i18n).

Each entry holds a per-hit token estimate (trend-only approximation) plus a
localized name and a copy-pasteable fix. These IDs map back to the 28-pattern
habit catalog in the Claude Code skill; only the subset that is quantitatively
auto-detectable from JSONL logs lives here.
"""

from __future__ import annotations

CATALOG: dict[str, dict] = {
    "H2-01": {
        "token_est_per_hit": 2_000,
        "en": {
            "name": "Re-reading the same file",
            "fix": 'Reference what you already read ("from the X you read earlier...") '
            "instead of re-Reading. Block it with a PreToolUse hook.",
        },
        "ko": {
            "name": "파일 리드 재탕",
            "fix": '같은 파일 재읽기 대신 "아까 읽은 X에서..." 컨텍스트 참조 유도. PreToolUse hook으로 차단.',
        },
    },
    "H2-02": {
        "token_est_per_hit": 5_000,
        "en": {
            "name": "Dumping full logs / stdout flood",
            "fix": "Filter before running: pipe through grep -A5 'FAIL|ERROR' or | head -50. "
            "Save to a file and pass the path.",
        },
        "ko": {
            "name": "로그 전체 덤프 / stdout 홍수",
            "fix": "grep -A5 'FAIL|ERROR'로 필터 후 실행. PreToolUse hook 설정.",
        },
    },
    "H8-02": {
        "token_est_per_hit": 5_000,
        "en": {
            "name": "stdout flood (large Bash output)",
            "fix": "Add | head -50 or a grep filter to Bash commands. "
            "Save output to a file and pass the path.",
        },
        "ko": {
            "name": "stdout 홍수 (Bash 결과 대형)",
            "fix": "Bash 명령에 | head -50 또는 | grep 필터 추가. 파일 저장 후 경로만 전달.",
        },
    },
    "H2-04": {
        "token_est_per_hit": 2_000,
        "en": {
            "name": "Stranded web results (WebFetch/WebSearch)",
            "fix": "Delegate research to a subagent so only the summary returns. "
            "Don't re-fetch the same page; narrow your queries.",
        },
        "ko": {
            "name": "웹 결과 방치 (WebFetch/WebSearch)",
            "fix": "리서치는 서브에이전트로 위임해 요약만 반환받기. 같은 페이지 재페치 금지, 쿼리는 좁게.",
        },
    },
    "H8-03": {
        "token_est_per_hit": 8_000,
        "en": {
            "name": "Subagent overuse (many Task spawns)",
            "fix": "Delegate only exploration / large independent / parallelizable work. "
            "Do simple edits and known-context queries on the main thread.",
        },
        "ko": {
            "name": "서브에이전트 남발 (Task 다수 생성)",
            "fix": "탐색·대형 독립·병렬 작업만 위임. 단순 편집·이미 아는 정보는 메인에서 직접.",
        },
    },
    "H5-04": {
        "token_est_per_hit": 800,
        "en": {
            "name": "Inviting verbose output",
            "fix": 'Cap the output: "in 2 lines", "no code or examples". '
            "Set response defaults in CLAUDE.md.",
        },
        "ko": {
            "name": "장황 출력 유도",
            "fix": '"2줄로만" "코드·예시 없이" 등 출력 제한 명시. CLAUDE.md에 기본값 설정.',
        },
    },
    "H4-03": {
        "token_est_per_hit": 21_000,
        "en": {
            "name": "Cache-kill switch (cache hit-rate crash)",
            "fix": "Avoid switching model/effort mid-session. Open a new session when you must switch.",
        },
        "ko": {
            "name": "캐시 킬 스위치 (캐시 히트율 급락)",
            "fix": "세션 내 모델·effort 전환 최소화. 전환 필요 시 새 세션 오픈.",
        },
    },
    "H1-01": {
        "token_est_per_hit": 10_000,
        "en": {
            "name": "Topic drift / marathon session",
            "fix": "At ~35 min / ~50K tokens, /compact or /clear and start a fresh session.",
        },
        "ko": {
            "name": "주제 드래그 / 장시간 세션",
            "fix": "35분·50K 토큰 기준으로 /compact 또는 /clear + 새 세션 전환.",
        },
    },
    "H1-03": {
        "token_est_per_hit": 15_000,
        "en": {
            "name": "Compaction overrun (token pile-up)",
            "fix": "Run /compact [focus] manually before you hit ~50K tokens.",
        },
        "ko": {
            "name": "compaction 버스 막차 (누적 토큰 과다)",
            "fix": "50K 토큰 전에 수동 /compact [포커스 지시] 실행.",
        },
    },
    "H8-01": {
        "token_est_per_hit": 5_000,
        "en": {
            "name": "Main-thread exploration (many Reads in one turn)",
            "fix": 'Delegate exploration to a subagent: '
            '"search src/auth/ and return only function names + locations."',
        },
        "ko": {
            "name": "메인 스레드 탐색 (한 턴 Read 다수)",
            "fix": '서브에이전트로 탐색 위임: "src/auth/ 에서 OAuth 함수 찾아서 이름·위치만 요약."',
        },
    },
}


def info(pattern_id: str, lang: str) -> dict | None:
    entry = CATALOG.get(pattern_id)
    if not entry:
        return None
    loc = entry.get(lang) or entry.get("en")
    return {"name": loc["name"], "fix": loc["fix"], "token_est_per_hit": entry["token_est_per_hit"]}
