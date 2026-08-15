"""Pattern catalog (i18n).

Each entry holds a per-hit token estimate (trend-only approximation) plus a
localized name and a copy-pasteable fix. These IDs map back to the 31-pattern
habit catalog in the Claude Code skill; only the subset that is quantitatively
auto-detectable from JSONL logs lives here.

`evidence` says where a waste number came from. Never blur these:

  "observed"  — a token counter the log actually recorded (usage fields).
  "estimated" — derived from real content, but converted, not counted
                (character->token conversion of a tool result).
  "heuristic" — a scenario constant multiplied by a hit count.

Patterns listed in report.SIGNAL_PATTERNS are counted but never scored.
"""

from __future__ import annotations

CATALOG: dict[str, dict] = {
    "H2-01": {
        "token_est_per_hit": 2_000,
        "evidence": "heuristic",
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
        "evidence": "estimated",
        "en": {
            "name": "Oversized tool results pulled into context",
            "fix": "Narrow the request before you make it: read a line range, grep first, "
            "or save the payload to a file and pass the path.",
        },
        "ko": {
            "name": "대형 툴 결과 컨텍스트 적재",
            "fix": "요청 전에 범위를 좁혀라 — 줄 범위 지정, grep 선행, 또는 파일로 저장 후 경로만 전달.",
        },
    },
    "H8-02": {
        "token_est_per_hit": 5_000,
        "evidence": "estimated",
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
        "evidence": "heuristic",
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
        "evidence": "heuristic",
        "en": {
            "name": "Subagent overuse (many spawns in one session)",
            "fix": "Delegate only exploration / large independent / parallelizable work. "
            "Do simple edits and known-context queries on the main thread.",
        },
        "ko": {
            "name": "서브에이전트 남발 (한 세션 다수 생성)",
            "fix": "탐색·대형 독립·병렬 작업만 위임. 단순 편집·이미 아는 정보는 메인에서 직접.",
        },
    },
    "H5-04": {
        "token_est_per_hit": 800,
        "evidence": "heuristic",
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
        "evidence": "observed",
        "en": {
            "name": "Cache-kill switch (model swapped mid-session)",
            "fix": "Switching model mid-session voids the prompt cache — the whole prefix is "
            "re-written at 1.25x instead of being read at 0.1x. Pick the tier first, "
            "or open a new session to switch.",
        },
        "ko": {
            "name": "캐시 킬 스위치 (세션 중 모델 전환)",
            "fix": "세션 중 모델 전환은 프롬프트 캐시를 무효화한다 — 프리픽스 전체가 0.1x 읽기 대신 "
            "1.25x 쓰기로 재작성된다. 티어를 먼저 정하거나, 전환은 새 세션에서.",
        },
    },
    "H4-04": {
        "token_est_per_hit": 0,
        "evidence": "heuristic",
        "en": {
            "name": "Top-tier-only driving (never switched models)",
            "fix": "Official list prices differ 5x (Opus 5 vs Haiku 4.5) to 10x "
            "(Fable 5 vs Haiku 4.5). Route by task: /model for lighter tiers on "
            "mechanical edits; lint, format and rename need no model at all.",
        },
        "ko": {
            "name": "최상위 모델 고정 주행 (티어 전환 0회)",
            "fix": "공식 정가 기준 Opus 5 대 Haiku 4.5는 5배, Fable 5 대 Haiku 4.5는 10배 차이다. "
            "작업별로 라우팅하라 — 기계적 편집은 /model로 낮은 티어, 린트·포맷·리네임은 "
            "애초에 모델이 필요 없다.",
        },
    },
    "H1-01": {
        "token_est_per_hit": 0,
        "evidence": "heuristic",
        "en": {
            "name": "Topic drift (long session carrying a heavy context)",
            "fix": "When the task changes, /clear. Name the session with /rename first "
            "if you plan to come back via claude --resume.",
        },
        "ko": {
            "name": "주제 드래그 (무거운 컨텍스트를 끌고 가는 장시간 세션)",
            "fix": "작업이 바뀌면 /clear. 돌아올 세션은 /rename으로 이름을 붙여두고 "
            "claude --resume으로 복귀.",
        },
    },
    "H1-03": {
        "token_est_per_hit": 15_000,
        "evidence": "observed",
        "en": {
            "name": "Context overrun (peak turn context past the ceiling)",
            "fix": "Run /compact [focus] before the context passes ~50K. "
            "Every later turn re-sends whatever you let pile up.",
        },
        "ko": {
            "name": "컨텍스트 과적재 (한 턴 최대 컨텍스트가 상한 초과)",
            "fix": "컨텍스트가 ~50K를 넘기 전에 /compact [포커스 지시] 실행. "
            "쌓아둔 만큼이 이후 모든 턴에 다시 실린다.",
        },
    },
    "H8-01": {
        "token_est_per_hit": 5_000,
        "evidence": "heuristic",
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
    return {
        "name": loc["name"],
        "fix": loc["fix"],
        "token_est_per_hit": entry["token_est_per_hit"],
        "evidence": entry.get("evidence", "heuristic"),
    }
