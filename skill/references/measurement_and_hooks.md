# tokenhabit — 측정·Hook 레퍼런스 (v1.1)

> **포지셔닝 한 줄**: 측정(집계·비용)은 ccusage에 위임하고, tokenhabit은 그 raw 메시지를 습관 진단으로 번역하는 것이 차별점이다. ccusage는 "얼마 썼냐"를 알려주고, habit_scan은 "왜 낭비했냐·어떤 습관이 문제냐"를 카탈로그 ID(H2-01 등)로 매핑해준다. 단, habit_scan이 JSONL에서 정량 자동감지하는 것은 25패턴 중 일부(현재 8패턴)뿐이며, 나머지는 카탈로그 자가점검 영역이다. 두 도구는 보완 관계이며 경쟁하지 않는다.

---

## 1. habit_scan.py — 습관 진단 어댑터

### 위치
```
skill/scripts/habit_scan.py
```

### 사용법

```bash
# 최근 7일 전체 프로젝트 분석 (기본)
python3 skill/scripts/habit_scan.py

# 최근 14일
python3 skill/scripts/habit_scan.py --days 14

# 특정 프로젝트 디렉토리만
python3 skill/scripts/habit_scan.py --project ~/.claude/projects/-Users-myname-myproject

# 단일 세션 파일
python3 skill/scripts/habit_scan.py --session ~/.claude/projects/*/session.jsonl

# CI/파이핑용 JSON 출력
python3 skill/scripts/habit_scan.py --json | jq .pattern_counts
```

### 감지 패턴 및 카탈로그 매핑

| 신호 | 감지 방법 | 카탈로그 ID |
|---|---|---|
| 동일 파일 반복 Read | tool_use.name=="Read" + file_path 중복 카운트 | H2-01 |
| 대형 tool_result (≥8,000자) | tool_result content 길이 | H2-02 / H8-02 |
| output/input > 0.5 (장황 응답) | message.usage 비율 | H5-04 |
| cache_read 비율 급락 (>30%→<5%) | 연속 메시지 캐시 히트율 비교 | H4-03 |
| 세션 >35분 또는 누적 >50K 토큰 | wall-time + usage 집계 | H1-01 / H1-03 |
| 한 턴(메시지) 내 Read ≥4개 (근사) | 메시지 단위 Read 개수 | H8-01 |

> **주의**: 병렬 tool call은 동일 `message.id`를 공유하므로 usage 집계 시 ID 기준 dedup 적용.
> 토큰 추정(대형 tool_result 등)은 영문 ~4자/token, 한글 ~2자/token 근사치 — 경향 파악용.

### 출력 해석 예시

```
============================================================
tokenhabit 습관 진단 리포트  (2026-06-03 14:22)
기간: 최근 7일  |  세션 파일: 42개  |  분석 세션: 42개
============================================================

[총계]  누적 토큰: 1,234,567  |  input: 890,000  |  output: 123,000
        캐시 히트: 221,567 (17.9%)

[감지된 습관 패턴] — 카탈로그 ID 기준
──────────────────────────────────────────────────────────

  [H2-02] 로그 전체 덤프 / stdout 홍수  ×12회
  추정 낭비: ~60,000 토큰
  즉시 fix: grep -A5 'FAIL|ERROR'로 필터 후 실행. PreToolUse hook 설정.

  [H2-01] 파일 리드 재탕  ×8회
  추정 낭비: ~16,000 토큰
  즉시 fix: 같은 파일 재읽기 대신 컨텍스트 참조. hook으로 차단.

  [H1-03] compaction 버스 막차  ×3회
  추정 낭비: ~45,000 토큰
  즉시 fix: 50K 토큰 전에 수동 /compact 실행.
```

- **×N회**: 해당 패턴이 N번 감지됨 (중복 파일 재읽기 횟수, 대형 출력 횟수 등).
- **추정 낭비**: 패턴 기본 추정치 × 횟수 (카탈로그 값 기반, 정밀 측정이 아님).
- **즉시 fix**: 카탈로그 `habit_catalog.md`의 고치는습관 요약.

### ccusage 보강

habit_scan은 `npx ccusage@latest daily`를 시도해 총 비용·일별 트렌드를 리포트 상단에 보강한다. ccusage가 미설치이거나 실패하면 graceful skip(에러 없이 계속).

---

## 2. hook_check.py — 런타임 강제 hook

### 위치
```
skill/scripts/hook_check.py
```

### 동작 원칙

- **stderr만, exit 0 고정** — 작업을 절대 차단하지 않음.
- Claude Code가 stdin으로 JSON payload를 전달.
- 경고 패턴: `[tokenhabit HX-XX] 설명\n  → 즉시 fix 한 줄`

### 감지하는 이벤트

| 이벤트 | 조건 | 패턴 ID |
|---|---|---|
| UserPromptSubmit | 프롬프트 ≤25자 + 모호 패턴 (고쳐줘, fix 등) | H5-01/H5-02 |
| UserPromptSubmit | 첫 메시지 길이 ≥500자 (프로젝트 설명 반복 의심) | H7-01 |
| PreToolUse Bash | 필터 없는 npm test/pytest/cat *.log 등 | H2-02/H8-02 |
| PreToolUse Read | 이미 읽은 파일 재요청 (임시파일 기반 세션 추적) | H2-01 |

> Read 재읽기 추적은 `/tmp/tokenhabit_<session>_reads` 임시파일에 경로를 기록하는 베스트에포트 방식.  
> `CLAUDE_SESSION_ID` 환경변수가 있으면 이를 세션 키로 사용, 없으면 ppid 폴백.

### self-test

```bash
python3 skill/scripts/hook_check.py self-test
# → stderr에 6가지 테스트 케이스 출력, exit 0
```

---

## 3. settings.json 등록 방법

아래 JSON을 `~/.claude/settings.json`(글로벌) 또는 프로젝트 `.claude/settings.json`에 추가.

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 /Users/YOURNAME/token-save-2/skill/scripts/hook_check.py userprompt"
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python3 /Users/YOURNAME/token-save-2/skill/scripts/hook_check.py pretooluse"
          }
        ]
      },
      {
        "matcher": "Read",
        "hooks": [
          {
            "type": "command",
            "command": "python3 /Users/YOURNAME/token-save-2/skill/scripts/hook_check.py pretooluse"
          }
        ]
      }
    ]
  }
}
```

> `YOURNAME`을 실제 경로로 교체. 절대 경로 사용 권장.

### 기존 hooks 섹션이 있는 경우

tokensave `hook_check.py`와 공존 가능. 같은 이벤트에 여러 hook 등록 시 배열에 추가:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {"type": "command", "command": "python3 /path/tokensave/scripts/hook_check.py userprompt"},
          {"type": "command", "command": "python3 /path/tokenhabit/skill/scripts/hook_check.py userprompt"}
        ]
      }
    ]
  }
}
```

---

## 4. 측정 분업 요약

```
ccusage (npx ccusage@latest)
  └─ 역할: 총 토큰·비용·일별·세션별 집계 ("얼마 썼냐")
  └─ 한계: 메시지 단위 도구 패턴 미분석

tokenhabit habit_scan.py
  └─ 역할: 메시지 단위 tool_use/tool_result 패턴 → 카탈로그 ID 매핑 ("왜 낭비했냐")
  └─ 한계: 25패턴 중 자동감지 가능한 8패턴만 정량 진단(나머지는 카탈로그 자가점검), 비용 정밀 집계는 ccusage에 위임

tokenhabit hook_check.py
  └─ 역할: 실시간 경고 — 나쁜 습관 발생 시점에 즉시 알림
  └─ 원칙: exit 0 / stderr만 / 블로킹 없음
```
