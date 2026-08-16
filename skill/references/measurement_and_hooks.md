# tokenhabit — 측정·Hook 레퍼런스 (v1.3)

> **포지셔닝 한 줄**: 측정(집계·비용)은 ccusage에 위임하고, tokenhabit은 그 raw 메시지를 습관 진단으로 번역하는 것이 차별점이다. ccusage는 "얼마 썼냐"를 알려주고, habit_scan은 "왜 낭비했냐·어떤 습관이 문제냐"를 카탈로그 ID(H2-01 등)로 매핑해준다. 단, habit_scan이 JSONL에서 정량 자동감지하는 것은 31패턴 중 일부(현재 11패턴)뿐이며, 나머지는 카탈로그 자가점검 영역이다. 특히 H9(지불 습관)는 토큰 로그에 흔적이 남지 않아 원리적으로 자동감지가 불가능하다. 두 도구는 보완 관계이며 경쟁하지 않는다.

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

| 신호 | 감지 방법 | 카탈로그 ID | 낭비 계산 |
|---|---|---|---|
| 동일 파일 반복 Read | `Read` 의 `(file_path, offset, limit)` 중복 카운트 | H2-01 | 추정 (상수 2,000/회) |
| 대형 tool_result (≥8,000자), Bash 출처 | `tool_use_id` → 툴 이름 역추적 | H8-02 | **환산** (문자→토큰) |
| 대형 tool_result (≥8,000자), Bash 외 | 위와 동일, Bash 아닌 것 | H2-02 | **환산** (문자→토큰) |
| 한 턴 output_tokens > 2,000 | `message.usage.output_tokens` | H5-04 | 추정 (상수 800/회) |
| `message.model` 실제 변경 (5분 TTL 내) | 직전 메시지 모델과 비교 | H4-03 | **실측** (전환 직후 `cache_creation` 카운터) |
| 세션 assistant 메시지 ≥10건이 100% 최상위 티어 | `message.model` 분포 | H4-04 | 신호 (미합산) |
| 한 턴 컨텍스트(`input+cache_read+cache_creation`) > 50K | 메시지별 최대값 | H1-03 | **실측** (usage 카운터 초과분) |
| 세션 >35분 **그리고** 최대 컨텍스트 >50K | wall-time + 위 컨텍스트 | H1-01 | 신호 (미합산) |
| 한 턴 내 Read ≥4개 | `message.id` 로 묶은 Read 개수 | H8-01 | 추정 (상수 5,000/회) |
| 세션당 서브에이전트 스폰 ≥6 | `Agent`(현행) 또는 `Task`(구버전) | H8-03 | 신호 (미합산) |
| WebFetch/WebSearch 호출 수 | tool_use 이름 | H2-04 | 신호 (미합산) |

**증거 등급 — 낭비 수치는 셋 중 하나이며 절대 뭉뚱그리지 않는다:**

| 등급 | 뜻 | 해당 패턴 |
|---|---|---|
| **실측(observed)** | 로그의 토큰 카운터 그대로 | H4-03, H1-03 |
| **환산(estimated)** | 실제 내용이지만 문자 수를 토큰으로 환산 (영문 4자/한글 2자) | H2-02, H8-02 |
| **추정(heuristic)** | 시나리오 상수 × 횟수 | H2-01, H5-04, H8-01 |
| 신호(signal) | 세지만 점수 미합산 | H1-01, H2-04, H4-04, H8-03 |

> ⚠️ v1.3.0은 H2-02·H8-02를 "실측"으로 표기했으나 실제로는 문자 환산이었다. 남의 출처 없는 수치를 지적하면서 자기 헤드라인 숫자의 근거를 잘못 말한 것이다. v1.3.1에서 등급을 셋으로 분리했다.

**측정 규약 — 이 4가지를 어기면 숫자가 거짓말을 한다:**

1. **턴 = `message.id`, 줄이 아니다.** Claude Code는 한 assistant 턴의 병렬 tool call을 *같은 message.id를 공유하는 별개의 JSONL 줄*로 쓴다. 줄 단위로 Read를 세면 한 줄에 1개씩만 보이므로 "한 턴에 4개 이상"은 영원히 참이 되지 않는다.
2. **컨텍스트 ≠ 스루풋.** 컨텍스트 크기는 *한 메시지*의 `input + cache_read + cache_creation` 이다. 세션 누적 총계는 처리량이지 컨텍스트가 아니며, 캐시 히트가 90%를 넘는 환경에서 누적 총계를 50K 임계와 비교하면 모든 세션이 무조건 플래그된다.
3. **서브에이전트 스폰 툴 이름은 `Agent`다.** `Task`는 구버전 이름이라 하위호환으로만 받고, `TaskCreate`/`TaskUpdate`는 할 일 관리 툴이므로 스폰으로 세면 안 된다.
4. **캐시 히트율 급락 ≠ 모델 전환.** 세션 재개·auto-compact·5분 TTL 만료로도 급락한다. 로그에 `message.model`이 있으므로 전환은 직접 관찰하고, `<synthetic>` 항목과 TTL 경과 구간은 제외한다.

> **주의**: 병렬 tool call은 동일 `message.id`를 공유하므로 usage 집계 시 ID 기준 dedup 적용.
> 토큰 추정(대형 tool_result 등)은 영문 ~4자/token, 한글 ~2자/token 근사치 — 경향 파악용.
> `isSidechain` 이 붙은 서브에이전트 트랜스크립트는 기본 제외(`--include-subagents` 로 포함).

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
  └─ 한계: 31패턴 중 자동감지 가능한 11패턴만 정량 진단(나머지는 카탈로그 자가점검), 비용 정밀 집계는 ccusage에 위임

tokenhabit hook_check.py
  └─ 역할: 실시간 경고 — 나쁜 습관 발생 시점에 즉시 알림
  └─ 원칙: exit 0 / stderr만 / 블로킹 없음
```

---

## 5. 공식 수치 표 (인용 SSOT)

> **왜 이 표가 있는가.** 토큰 절감 조언은 SNS에서 출처 없는 수치와 함께 유통된다("최상위 모델 쓰면 30배", "배치로 70~90% 절감", "AI 코딩 비용의 90%는 낭비" 등). 방향은 대체로 맞지만 **숫자는 대개 근거가 없고, 일부는 공식 수치와 정면으로 배치된다.** 이 스킬은 절감을 주장할 때 아래 공식 수치만 인용한다. 여기 없는 배수·달러 값을 쓰고 싶어지면, 먼저 1차 출처를 찾아 이 표에 추가하라.

### 프롬프트 캐싱 (Anthropic 공식)

| 항목 | 공식 값 |
|---|---|
| 캐시 읽기 | 기본 입력가의 **0.1x** |
| 캐시 쓰기 | **1.25x** (5분 TTL) / **2x** (1시간 TTL) |
| TTL — API 키·Bedrock·Vertex·Foundry | **5분** (기본) |
| TTL — Claude 구독(Pro/Max) | **1시간**, 자동 요청. usage credit 사용 시 5분으로 하락 |
| TTL — 서브에이전트 | **5분** (구독이어도) |
| 무효화 계층 | `tools` → `system` → `messages` (상위가 바뀌면 그 아래 전부 무효) |
| 캐시를 죽이는 것 | 모델 전환 · effort 변경(캐시 키의 일부) · fast mode 켜기 · MCP 연결/해제(**프리픽스 로드일 때만**) · 플러그인 토글(**MCP 제공 시만**) · 툴 전체 deny · `/compact` · Claude Code 업그레이드 |
| 캐시를 **죽이지 않는** 것 | CLAUDE.md 세션 중 편집(적용도 안 됨) · output style 변경 · permission mode 전환 · **스킬·커맨드 호출**(user message로 append) · `/recap` · `/rewind` · 서브에이전트 스폰 |
| 최소 캐시 가능 토큰 | 모델별 **512~4,096** |
| 캐시 브레이크포인트 | 최대 **4개** |

→ 캐시가 살아 있을 때와 죽었을 때의 차이는 **0.1x 대 (1.0x + 1.25x)**, 즉 캐시됐어야 할 구간 기준 **최대 12.5배**다. H4-03의 근거.

### 모델 티어 정가 (Anthropic 공식, per MTok, 2026-08 기준)

| 모델 | 입력 | 출력 |
|---|---|---|
| Claude Fable 5 | $10 | $50 |
| Claude Opus 5 | $5 | $25 |
| Claude Sonnet 5 | $3 ($2 인트로) | $15 ($10 인트로) |
| Claude Haiku 4.5 | $1 | $5 |

→ 실제 티어 격차는 **Opus 5 : Haiku 4.5 = 5배**, **Fable 5 : Haiku 4.5 = 10배**다. H4-04의 근거.
→ SNS에 도는 "30배", "1/6 가격" 은 **어떤 공식 비율과도 일치하지 않는다.** 인용 금지.

### 배치 처리

| 항목 | 공식 값 |
|---|---|
| Anthropic Message Batches API | 비용 **50%** 절감 |
| OpenAI Batch API | 비용 **50%** 절감 |

→ "배치 한 번으로 70~90% 절감"은 **공식 할인율의 과장**이다. 다만 Anthropic 문서는 배치 할인이 캐싱 배수와 **중첩된다**고 명시하므로, 공유 프리픽스 구간에 한해 배치 50% × 캐시 읽기 0.1x 조합은 성립한다 — 인용할 때 이 조건을 함께 밝힐 것.

### 인용하지 말아야 할 것

2026년 상반기 X(트위터)에서 "Andrej Karpathy: *90% of your AI coding bill is paying for context you didn't need to send*" 인용과 함께 대량 유포된 10개 항목 리스트가 있다. 확인 결과:

- **1차 출처가 확인되지 않는다.** 카파시의 X 계정·개인 사이트·블로그·팟캐스트 어디에서도 원문을 찾지 못했고, 이 문장을 인용하는 모든 경로가 한 게시물과 그 재가공으로 수렴한다. 2차 블로그들도 출처 URL·날짜 없이 "recently outlined"라고만 적는다. 같은 계정이 서로 다른 내용에 `"Andrej Karpathy: 90% of ..."` + `"10 things senior engineers stopped..."` 형식을 반복 사용한 정황도 있다.
  > 다만 정확한 판정은 **"출처 부재 + 오귀속 정황 강함"**이지 **"허위 확정"이 아니다.** 카파시 본인의 공개 부인이나 커뮤니티 노트는 확인하지 못했다. 남의 발언을 근거 없이 허위로 단정하는 것 역시 이 절이 경계하는 바로 그 실수다.
- **메커니즘은 대체로 타당하나 수치는 대부분 근거가 없다.** 항목별 판정은 위 공식 표로 대체 가능하며, 특히 "배치 70~90%"는 공식 50%와 배치된다. ("30배"는 **현행 라인업 기준으로는** 불가능하지만, 구세대 조합(Opus 3 $15 대 Haiku 3 $0.25)에서는 산술적으로 가능했다 — 즉 낡은 가격표를 현재형으로 옮긴 수치일 수 있다.)
- 카파시의 **검증되는** 관련 발언은 따로 있다 — 2025-06-25 X: *"context engineering is the delicate art and science of filling the context window with just the right information for the next step."* 컨텍스트 관리의 중요성을 인용해야 한다면 이쪽을 쓰라.

### 주의 — 카파시를 이 스킬의 우군으로 인용하지 말 것

검증된 그의 최근 입장은 **비용 절약이 아니라 토큰 스루풋 극대화**다 (No Priors 팟캐스트, 2026-03-20):

> "now it's not about flops. it's about tokens. So what is your token throughput and what token throughput do you command?"
> "**I feel nervous when I have subscription left over.** That just means I haven't maximized my token throughput."
> "if you don't feel very bounded by your ability to spend on tokens, then you are the bottleneck"

즉 그 바이럴 인용은 **그의 실제 프레이밍과 방향이 어긋난다.** 그리고 이 관점은 우리 스킬에 대한 정당한 반론이기도 하다 — 새겨들을 것:

- **낭비를 줄이는 것과 적게 쓰는 것은 다르다.** 이 스킬의 목표는 지출을 깎는 게 아니라 **같은 결과를 더 싸게 얻어 남는 예산을 실제 작업에 쓰는 것**이다. 진단 결과를 "그러니 덜 쓰세요"로 번역하지 마라.
- **H9-01(구독 중복)과의 관계.** 카파시가 말한 "남는 구독"은 *쓰고 있는 플랜의 미소진 한도*를 뜻하고, H9-01이 겨냥하는 것은 *아예 로그인도 안 하는 플랜*이다. 전자는 더 쓰라는 신호이고 후자는 해지 대상이다 — 사용자에게 설명할 때 이 둘을 섞지 마라.

**원칙: 방향이 맞는 조언이라도 출처 없는 수치를 붙이면 조언 전체의 신뢰도가 함께 죽는다. 그리고 우리 편처럼 보이는 인용일수록 원문을 먼저 확인하라.**
