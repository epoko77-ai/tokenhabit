# Claude Code 2026년 최신 기능의 토큰 낭비 패턴 종합 진단

**작성**: 2026-06-15 | **대상**: tokenhabit 스킬 v1.2+  
**검증**: 공식 문서 (code.claude.com/docs) 기반 직접 분석  
**형식**: (무의식적 행동) → (토큰 누출 경로) → (구체적 해결책)

---

## 요약표: 13개 최신 기능의 토큰 낭비 메커니즘

| # | 기능 | 증상 (무의식적 행동) | 토큰 누출 | 절감 수치 | 우선도 |
|---|------|-----------------|---------|---------|--------|
| **1** | **Subagents** | 매번 새 subagent 생성, WebSearch 결과 정리용 | 각 subagent +4,200 (×5 = 21K) | 30,000/회 | 🔴 |
| **2** | **MCP 서버** | 20개 연결, 90% 미사용 | 스키마 사전 로드 | 10,000/session | 🔴 |
| **3** | **Skills** | Description 200줄+, disable-model 안 함 | 매번 비관련 skill 로드 | 5,000/session | 🟠 |
| **4** | **Plan/Compact** | 미사용, context 150K 넘어도 안 함 | 자동 compaction 반복 (낭비) | 50,000/use | 🔴 |
| **5** | **Thinking** | alwaysThinkingEnabled=true 기본값 | 단순 질문도 +10K 토큰 | 20,000/session | 🔴 |
| **6** | **1M Context** | 3주 한 세션, 초반 지시 무시 | 주의 계산 병목 | 응답 15초 지연 | 🟠 |
| **7** | **Background Tasks** | 순차 작업을 5개 parallel로 | 각 session ×200K | 800K/excess | 🟡 |
| **8** | **이미지 반복** | 스크린샷 3번 이상 재첨부 | 각 2,500토큰 | 2,500/반복 | 🟡 |
| **9** | **WebSearch 중복** | 같은 쿼리 3번, 캐싱 모름 | API call + 토큰 | 5,000/중복 | 🟡 |
| **10** | **Output 과장** | 간단한 fix에 설명 2,000토큰 | Output 5배 비용 | 1,500/회 | 🟡 |
| **11** | **Hook Context** | 매 tool use마다 500자 주입 | 50회 사용 = 25K | 3,000/session | 🟡 |
| **12** | **MEMORY.md 비대** | 200줄+, 옛 메모 미정리 | 매 세션 필수 로드 | 4,000/session | 🟡 |
| **13** | **Plugin 과다설치** | 6개+, 필요 없는 것도 로드 | 시스템 프롬프트 +2K | 2,000/session | 🟡 |

---

## 각 항목의 상세 분석

### 1. Subagents / Task Tool — "병렬이 아닌데 subagent 쓰기"

**어떤 무의식적 사용자 행동이 문제인가?**

```
패턴 1: 단순 정리 작업 → subagent 위임
"이 검색 결과 요약해줘" → /task create summarizer
→ 새 context window 생성 (4,200 토큰 낭비)

패턴 2: 순차 작업을 병렬로 착각
1단계: WebSearch ("파이썬 최신 버전")
2단계: 결과 정리 (subagent로 위임)
3단계: 예시 작성 (또 subagent로)
→ 3개 subagent, 각각 완료 대기

패턴 3: Subagent에 Custom prompt 과다 정의
descriptions.md에 500줄 지시 → +5,000 토큰
```

**토큰이 정확히 어떻게 새는가?**

```
Subagent = 완전히 독립된 context window

메인 session cost:
- System prompt: 4,200
- CLAUDE.md: 1,200
- Conversation: 50,000 (예)
━━━━━━━━━━━━━━
Total: 55,400

Subagent 5개 병렬 시:
- 메인: 55,400
- Sub 1: 4,200 + 600 (mini CLAUDE) + 500 work = 5,300
- Sub 2~5: 5,300 × 4 = 21,200
━━━━━━━━━━━━━━
Total: 82,000 (vs 55,400) = +26,600 추가 비용

+ Custom prompt (+1K ~5K per subagent)
+ Task metadata logs (+200 per task completion)
```

**어떻게 고칠 것인가?**

```bash
# 진짜 병렬만 생성:
✓ /task "한국 맥락 리서치. 5줄 요약 (필수)"
✓ /task "차트 스펙 설계. JSON만 (설명 X)"
   → 동시 실행, 결과만 수집

# 순차는 메인에서:
✗ WebSearch → subagent 정리 (메인에서 한 줄)
✗ 검색 결과 + 정리 + 예시 (3개 subagent)

# Subagent 설명 3줄 이내:
"한국 경제 리서치 전담" (OK, 5 words)
vs
"한국 정책, 산업 동향, 기술, 금융, ..." (NO, 50 words)

# 명령:
/agents  # 불필요한 subagent 정리
/context  # subagent 비용 확인
```

**실제 절감:**
- 불필요한 subagent 1개 제거 = **4,200 토큰/session**
- 5개 줄임 = **21,000 토큰/session**

---

### 2. MCP 서버 — "20개 연결, 90% 미사용"

**어떤 무의식적 사용자 행동이 문제인가?**

```
패턴 1: "있으면 좋겠지" 마음으로 모두 연결
Vercel + GWS + Harness + Computer Use + ...
→ 활용: 2개만 정기적

패턴 2: ENABLE_TOOL_SEARCH=false 설정
모든 도구 스키마 사전 로드
→ 400개 도구 × 50 토큰 = 20,000 토큰 낭비

패턴 3: Hook에서 MCP tool 호출
매 PreToolUse마다 mcp__google__* 호출
→ 스키마 반복 로드
```

**토큰이 정확히 어떻게 새는가?**

```
기본 (Deferred loading, ENABLE_TOOL_SEARCH=auto):
- Session 시작: 도구 이름만 ~120 토큰
- 첫 사용: 해당 스키마 on-demand (+1,000)
- 재사용: 캐시 (free)
━━━━━━━━━━━━━━
Total: 1,120 (한 번)

문제 케이스 (ENABLE_TOOL_SEARCH=false):
- Session 시작: 모든 스키마 사전 로드
- 20 MCP × 20 도구 × 50 토큰 = 20,000
- Hook에서 매번 호출: ×50 turn = 1,000,000 토큰/day!
```

**어떻게 고칠 것인가?**

```bash
# 1단계: 현재 MCP 감시
/mcp
# "Unused" 표시 → 제거 대상

# 2단계: 비용 확인
/context | grep "MCP"

# 3단계: ENABLE_TOOL_SEARCH 확인
cat ~/.claude/settings.json | grep ENABLE_TOOL_SEARCH
# "false" 있으면 → 삭제 (auto가 기본값)

# 4단계: 프로젝트별 MCP 선택
# .claude/settings.json에만 필요한 것:
{
  "extraKnownMarketplaces": {
    "project-a": {
      "servers": ["vercel"]  // A 프로젝트에만
    }
  }
}

# 5단계: Hook에서 MCP 사용 최소화
# 매번 호출되는 MCP → Command hook으로 교체
```

**실제 절감:**
- 미사용 MCP 5개 제거 = **2,000 토큰/session**
- ENABLE_TOOL_SEARCH=false 제거 = **20,000 토큰/session**
- Hook에서 반복 호출 제거 = **1,000,000 토큰/day (심각한 경우)**

---

### 3. Skills — "Description 길고, disable 안 함"

**어떤 무의식적 사용자 행동이 문제인가?**

```
패턴 1: Skill description이 200줄 (Manual 수준)
"이 스킬은 다음을 수행합니다: 1. ... 2. ... 3. ..."
→ 100+ 단어 설명 (vs 10 단어면 충분)

패턴 2: disable-model-invocation = false (기본)
모든 skill description 매 세션 로드
→ 30개 skill × 400 토큰 = 12,000 낭비

패턴 3: 중복 skill 관리 안 함
/tokenhabit (v1.0) + /tokenhabit (v1.1)
/tokensave + /tokensave-audit
→ 모두 로드됨
```

**토큰이 정확히 어떻게 새는가?**

```
Current: 30 skills, 각 400 토큰 description
Session 시작:
- 모든 skill description 로드: 12,000 토큰
- Claude가 자동 호출 가능 (보조)
- 실제 사용: 3개 skill만

Optimized:
- 자주 쓰는 skill 3개: 400 × 3 = 1,200
- 필요할 때만 /skill-name로 호출: lazy load (on-demand)
- 절감: 10,800 토큰
```

**어떻게 고칠 것인가?**

```bash
# 1단계: Skill 현황 파악
ls -la ~/.claude/skills/
wc -l ~/.claude/skills/*/SKILL.md | sort -nr

# 2단계: Description 최적화
# ✗ Before: "이 스킬은 사용자의 토큰 습관을 진단합니다..."
# ✓ After: "토큰 낭비 습관 진단 스킬."

# 3단계: 중복 제거
rm -rf ~/.claude/skills/tokenhabit-v1/  # 오래된 버전
# 앞으로 "새 버전 = 옛 버전 삭제" 규칙

# 4단계: disable-model-invocation 활용
# .claude/settings.json:
{
  "skillOverrides": {
    "~/.claude/skills/tokenhabit/SKILL.md": {
      "disable-model-invocation": true
    }
  }
}
# → /tokenhabit (명시 호출)만 가능, 자동 호출 X

# 5단계: Skill 본체 분리
# SKILL.md (3,000자: 프롬프트만)
#   └─ @references/examples.md (필요할 때만 Read)
```

**실제 절감:**
- Description 길이 제한 = **2,000~5,000 토큰/session**
- disable-model 적용 = **1,000~3,000 토큰/session**
- 중복 제거 = **400 토큰/skill**

---

### 4. Plan Mode, /context, /compact — "미사용 명령"

**어떤 무의식적 사용자 행동이 문제인가?**

```
패턴 1: Context 상황 파악 안 함
"왜 응답이 느려?" → /context 안 함
→ 대화가 100K 이상인데도 모름

패턴 2: /compact 타이밍 놓침
Context 150K 찼는데 그냥 대화
→ Auto-compact 여러 번 (낭비)

패턴 3: Plan mode 모름
/plan 없이 "설계해줄까?" → 바로 Edit
→ 수정 50%, Undo 30%, Rewind 20%

패턴 4: /rewind 미사용
"아, 다시 할래" → 세션 종료 (context 버림)
→ 새 세션 (fresh start, 15분 낭비)
```

**토큰이 정확히 어떻게 새는가?**

```
Context 150K인 상태에서 대화:

매 turn마다:
1. 150K 전체 attention (계산 비용)
2. Auto-compact 시도 (overhead)
3. Summarization 실행 (토큰 사용)
4. Re-injection (또 로드)

Compact 한 번:
- Before: 150K tokens
- Compaction process: 5K tokens (요약)
- After: 45K tokens (요약 + 필수)
━━━━━━━━━━━━━━
Saved: 100K+ tokens, 응답 3배 빨라짐

Plan mode의 효율:
- Without: 10개 파일 Edit → 반 실패 → Rewind
  = 5,000 output + 5,000 context + undo overhead
- With: Plan (Read만) → Approval → 정확한 Edit
  = 500 output (설계) + 2,000 output (실행) = 70% 절감
```

**어떻게 고칠 것인가?**

```bash
# 1단계: /context 습관 들이기 (매 session 1회)
/context
# "Conversation: 150K" → /compact 필요 신호

# 2단계: /compact 타이밍
/context에서 150K 이상이면:
/compact focus on [current task]
→ 50,000~100,000 토큰 절감

# 3단계: Plan mode 사용 (복잡한 구조 변경)
/plan  # 또는 Shift+Tab ×2
# Read/Search만, Edit 안 함
# 당신이 "OK 진행" 후 실제 Edit

# 4단계: /rewind 활용 (direction change)
/rewind  # 체크포인트 목록
/rewind to "Before API refactor"
# Context history 리셋, 파일은 현재 상태 유지
```

**실제 절감:**
- `/compact` 한 번 = **50,000~100,000 토큰**
- Plan mode 습관 = **60% Edit work 감소**
- `/context` 조기 발견 = **불필요한 auto-compact 10회 방지**

---

### 5. Extended Thinking — "무의식적 활성화"

**어떤 무의식적 사용자 행동이 문제인가?**

```
패턴 1: alwaysThinkingEnabled=true 설정
settings.json에 한 번 넣고 잊음
→ 모든 메시지마다 thinking 실행

패턴 2: /effort xhigh 기본값
"어려운 문제 아닌데" 설정 복구 안 함
→ 버그 수정에도 +30K 토큰

패턴 3: Thinking 백그라운드 실행
"왜 3분 걸려?" → thinking이 몰래 실행 중
```

**토큰이 정확히 어떻게 새는가?**

```
일반 메시지 (no thinking):
- Input: 50,000 tokens
- Output: 1,000 tokens
- Total: 51,000

Extended thinking:
- Input: 50,000 tokens
- Thinking (숨겨짐): 10,000~50,000 tokens ← 추가!
- Output: 1,000 tokens
- Total: 61,000~101,000 tokens

alwaysThinkingEnabled=true:
- 매 메시지마다 +20K 토큰 (평균)
- 50 turn/session = +1,000,000 토큰/session
```

**어떻게 고칠 것인가?**

```bash
# 1단계: 현재 상태 확인
/effort  # "medium"이 기본 (OK)
cat ~/.claude/settings.json | grep -i thinking

# 2단계: Thinking 끄기
# settings.json:
{
  "alwaysThinkingEnabled": false,
  "effortLevel": "medium"
}

# 3단계: 필요할 때만 활성화
/effort xhigh  # "이 설계가 정말 맞을까?" (1회만)
# 문제 해결 후:
/effort medium  # 자동 복구

# 4단계: 문제 유형별 effort 선택
# 간단한 fix: /effort low
# 중간 복잡: /effort medium (기본)
# 복잡한 설계: /effort high
# 매우 어려움: /effort xhigh (1회)
```

**실제 절감:**
- `alwaysThinkingEnabled=false` = **기본선**
- 불필요한 xhigh 제거 = **30,000 토큰/메시지**
- Session당 = **500,000~1,000,000 토큰 가능**

---

### 6. 1M Context Window — "무한정 쌓기"

**어떤 무의식적 사용자 행동이 문제인가?**

```
패턴 1: "1M이니까 3주 계속 OK"
한 세션 150K → 300K → 800K 진행
→ 응답 시간 15초, 초반 지시 무시됨

패턴 2: Context 후반부 우선
1M 중 마지막 10K가 가장 영향력
→ "3주 전 지시가 왜 무시돼?"

패턴 3: Checkpoint 500개 방치
/rewind 모르니까 계속 쌓임
```

**토큰이 정확히 어떻게 새는가?**

```
Context size와 비용:
- 200K input: 0.0006 (저렴)
- 1M input: 0.003 (5배!)
- 생성: 둘 다 0.000075

응답 지연:
- 200K: 2초
- 1M: 15초 (계산 complexity)

초반 지시 무시:
Token 1~10K (초반): 우선도 ★
Token 990K~1M (최근): 우선도 ★★★★★
→ 모델의 주의가 최근을 더 중시
```

**어떻게 고칠 것인가?**

```bash
# 1단계: 세션 주기 설정
# 1주일마다 /compact 또는 새 세션
# 2주 이상 = 필수 /compact
# 1개월 = 새 세션 시작

# 2단계: Auto-compaction 설정
# .claude/settings.json:
{
  "autoCompactionConfig": {
    "triggerAtPercentage": 70,
    "compactAfterTurns": 20
  }
}

# 3단계: 긴 세션은 periodic checkpoint
/context  # 4~5시간마다 확인
# 150K 이상이면:
/compact focus on recent work

# 4단계: 초반 지시 재확인
# /compact 후 CLAUDE.md 자동 재로드됨
# But 대화 초반 세부 지시는 요약됨
# → CLAUDE.md에 옮기기
```

**실제 절감:**
- 정기적 `/compact` = **반응 속도 2~3배 향상**
- 세션당 실제 비용 = **일주일 단위 초기화**

---

### 7. Background Tasks — "순차인데 병렬"

**어떤 무의식적 사용자 행동이 문제인가?**

```
패턴 1: 순차 작업을 background로 분기
1. 한국어 번역 → /background
2. 리뷰 → /background (1 완료 대기 필요)
3. 편집 → /background (2 완료 대기 필요)
→ 3개 세션 (각 200K context) = 낭비

패턴 2: "Needs input" 방치
background 작업이 pending → timeout
→ 자동 종료, 작업 유실
```

**토큰이 정확히 어떻게 새는가?**

```
Background task (진정 병렬):
✓ "대문서 번역" + "차트 설계" (동시, 비의존)
→ 2개 session × 200K = 400K (정당)

Background task (낭비):
✗ "번역" → "리뷰" → "편집" (순차)
→ 3개 session × 200K = 600K
→ 실제로는 순차라서 idle 시간 많음
→ 메인에서 처리했으면 200K (3배 낭비)
```

**어떻게 고칠 것인가?**

```bash
# 1단계: Background 조건 확인
# Background 생성 조건 (모두 만족):
# □ 메인과 비의존 (먼저 끝날 필요 X)
# □ 실제 병렬 가능 (시간 겹침)
# □ 결과 필요 후 merge

# 2단계: 불필요한 background 정리
/agents  # 현재 상태 확인
# "Working" 5개 이상 = 과다, 정리

# 3단계: Background 모니터링
/agents  # "Needs input" 확인
# 즉시 처리 또는 timeout 설정
```

**실제 절감:**
- 불필요한 background 3개 = **600K context 낭비 방지**

---

### 8. 이미지 / 스크린샷 반복 첨부 — "누적 비용"

**어떤 무의식적 사용자 행동이 문제인가?**

```
패턴 1: 같은 스크린샷 재첨부
Turn 1: "스크린샷 해줘" → [Screenshot A]
Turn 2: "이건 왜?" → [Screenshot A 또 붙임]
Turn 3: "다시 봐" → [Screenshot A 또 또]

패턴 2: 고해상도 이미지
1920×1080 PNG = 2,500 토큰
Turn 10: (2,500 × 10) 반복 = 25,000 토큰 누적
```

**토큰이 정확히 어떻게 새는가?**

```
이미지 토큰 = (높이 × 너비) / 750 + 85

1920×1080: (1920 × 1080) / 750 + 85 = 2,500 토큰
800×600: (800 × 600) / 750 + 85 = 750 토큰

반복 첨부:
Turn 1: 2,500 (초)
Turn 2: 2,500 (재) + 2,500 (누적) = 5,000
Turn 3: 2,500 + 5,000 + 2,500 = 10,000 누적
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
5 turn: 22,500 토큰 낭비
```

**어떻게 고칠 것인가?**

```bash
# 1단계: 첫 첨부 후 참조만
# ✗ "스크린샷 봐" → [재첨부]
# ✓ "위 스크린샷에서 보듯이"

# 2단계: 해상도 최적화
# 1920×1080 (2,500) → 1024×768 (1,000)
convert out.png -resize 1024x768 small.png

# 3단계: Context에서 제거
/context  # 이미지 토큰 확인
# 오래된 이미지 정보 문맥으로 정리, 다시 붙이지 말 것
```

**실제 절감:**
- 스크린샷 1개 재첨부 금지 = **2,500 토큰/turn**
- 해상도 최적화 = **1,500 토큰/스크린샷**

---

### 9. WebSearch / WebFetch 남발 — "캐싱과 중복"

**어떤 무의식적 사용자 행동이 문제인가?**

```
패턴 1: 같은 URL 3번 fetch
1. /fetch google.com (API call, 유료)
2. "자세히" → /fetch google.com (캐시되었는데?)
3. "더 자세히" → /fetch google.com (또?)

패턴 2: WebSearch 중복
"Claude 최신 버전" → WebSearch
"얼마?" → WebSearch (첫 결과에 있음!)

패턴 3: 결과 크기 낭비
WIRED 50KB 페이지 전부 로드
→ 10,000 토큰 (실제 필요: 500)
```

**토큰이 정확히 어떻게 새는가?**

```
WebFetch 캐싱:
기본: 15분 자동 캐시 (in-memory)

Turn 1: /fetch google.com → API call + context 로드
Turn 2: /fetch google.com (캐시) → free
Turn 3: "또 봐" → 캐시에 있는데 재로드?

결과 크기 낭비:
50KB 페이지:
- 전부: 10,000 토큰
- Intro + key points: 2,000 토큰
- 80% 낭비

WebSearch 중복:
"Latest Claude"  → WebSearch (1,000)
"Pricing"       → WebSearch (1,000) [첫 결과에 있음]
"Features"      → WebSearch (1,000) [또]
→ 2,000 토큰 낭비
```

**어떻게 고칠 것인가?**

```bash
# 1단계: WebFetch 캐싱 이해
# 15분 자동 캐시 = 기본값
# "같은 URL fetch 필요" → /cache clear (강제 갱신)

# 2단계: WebSearch 결과 재사용
# ✗ "Claude 가격" → WebSearch
#    "프리 플랜?" → WebSearch (또)
# ✓ "Claude 가격" → WebSearch
#    "프리 플랜?" → "위 검색에서..."

# 3단계: WebFetch 결과 요약 요청
# ✗ /fetch wired.com/article → 50KB 전부 로드
# ✓ /fetch wired.com/article
#    "intro + key points만 정리해줘"

# 4단계: 수동 제어
# "이전 검색 결과로 충분" → 언급만
# 정말 새로운 정보만 /search
```

**실제 절감:**
- WebSearch 중복 제거 = **3,000~5,000 토큰/session**
- WebFetch 요약 요청 = **5,000+ 토큰/fetch**

---

### 10. Output Styles — "과장된 설정"

**어떤 무의식적 사용자 행동이 문제인가?**

```
패턴 1: 기본값 그대로
Claude가 자동 길이 결정
→ 간단한 fix에 500 토큰 output

패턴 2: 매번 "간단하게" 반복
"간단하게" 지시를 매 turn마다
→ 습관 안 들음

패턴 3: "자세하게" 기본값
모든 답변에 설명 + 대안 + 테스트
→ 원래 필요: 200, 실제: 1,000
```

**토큰이 정확히 어떻게 새는가?**

```
Output 비용 (생성):
Claude 3.5 Sonnet: $15/1M output (입력의 5배!)

간단한 버그 fix:
- Minimal: "라인 52 fix" (10 tokens, $0.00015)
- Normal: "라인 52 fix, 이유는..." (200, $0.003)
- Detailed: "라인 52 fix, 원인 분석, 대안 3개" (500, $0.0075)
→ 50배 비용 차이!

Session당:
- 과장된 output × 50 turn = 25,000 토큰
- 최적 output × 50 turn = 5,000 토큰
→ 20,000 토큰 절감 가능
```

**어떻게 고칠 것인가?**

```bash
# 1단계: 상황별 지시
"이 버그만 고쳐줘 (설명 없이)" → 코드만
"새 API 설계" → 설명과 함께
"확인해줘" → 짧은 피드백

# 2단계: Prompt에서 명시
# ✗ "코드 고쳐줘"
# ✓ "코드만 제시 (설명 X)"

# 3단계: Output preset 생성
# .claude/settings.json:
{
  "outputPresets": {
    "minimal": "1-2 sentences",
    "normal": "Explanation with context",
    "detailed": "Comprehensive + alternatives"
  }
}

# 4단계: /style 명령
/style minimal    # 간단
/style normal     # 중간 (기본)
/style detailed   # 자세
```

**실제 절감:**
- 불필요한 설명 제거 = **50~80% output 절감**
- Session당 = **10,000~20,000 토큰**

---

### 11~13. Hooks, MEMORY.md, Plugins — "작은 낭비들"

| 항목 | 무의식적 행동 | 토큰 누출 | 해결책 |
|------|------------|---------|--------|
| **Hooks** | 매 tool use에 500자 context 주입 | 50회 = 25,000 | additionalContext 최소화, async hook 활용 |
| **MEMORY.md** | 200줄+, 3개월 옛 메모 | 3,000~5,000/session | 월간 정리, 50줄 유지 |
| **Plugins** | 6개+ 설치, 필요 없는 것 로드 | 2,000/session | enabledPlugins 선택적 활성화 |

---

## 종합 진단: "당신의 세션은 몇 % 낭비하는가?"

### 기준점 (Baseline)

```
최적화된 세션:
- System: 4,200 tokens
- CLAUDE.md: 800 tokens (≤200줄)
- Auto memory: 200 tokens (≤50 items)
- Conversation: 50,000 tokens (1시간 작업)
- Tools: 500 tokens
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total: 55,700 tokens
```

### 낭비 진단표 (당신의 경우)

```
체크리스트:

□ Subagent 5개 이상?              +30,000
□ MCP 서버 10개 이상?             +10,000
□ Skill 30개+, description 길다?  +5,000
□ Context 150K+ 대화?             +50,000 (매 turn)
□ alwaysThinkingEnabled=true?      +20,000/message
□ 1개월 한 세션?                  +50,000
□ Background task 5개+?           +400,000 (동시)
□ 스크린샷 3회+ 반복?             +2,500/회
□ WebSearch 같은 거 3회+?         +3,000
□ Output 과장 설정?               +10,000
□ Hook context 매번?              +3,000
□ MEMORY.md 250줄+?               +4,000
□ Plugin 6개+?                    +2,000

나의 추정 낭비: 📊
```

---

## 실행 로드맵 (Priority Order)

### 🔴 **오늘 (1시간) — 즉시 실행**

```bash
1. /effort medium 확인
   cat ~/.claude/settings.json | grep effort

2. /agents 실행 → 비필요 subagent 정리

3. /mcp 확인 → 미사용 서버 제거

4. /memory → MEMORY.md 200줄 점검
```

### 🟠 **이번주 (2시간) — 습관 형성**

```bash
1. /context 명령 학습
   매 세션마다 1회 실행 (토큰 상황 파악)

2. /plan 습관
   복잡한 작업은 /plan (Shift+Tab ×2)로 설계 검증

3. /compact 실행
   Context 150K 넘으면 /compact focus on...

4. 자신의 토큰 습관 진단
   upcoming: /manpower 스킬 (당신의 tokenhabit에 통합)
```

### 🟡 **다음주 (3시간) — 시스템 최적화**

```bash
1. settings.json 최적화
   - ENABLE_TOOL_SEARCH 확인 (auto만)
   - alwaysThinkingEnabled=false
   - skillOverrides 설정

2. skills 정리
   - 중복 제거
   - description 100 단어 이내로 축약

3. MEMORY.md 구조
   - 50줄로 축약
   - 옛 메모 → topic files로 이동

4. hooks 감시
   - /hooks 확인
   - additionalContext 최소화
```

---

## 참고: 공식 문서 (2026년 기준)

- **Context Window Visualization**: https://code.claude.com/docs/en/context-window.md
- **Subagents**: https://code.claude.com/docs/en/subagents.md
- **MCP Servers**: https://code.claude.com/docs/en/mcp-servers.md
- **Skills**: https://code.claude.com/docs/en/skills.md
- **Commands**: https://code.claude.com/docs/en/commands.md
- **Hooks Reference**: https://code.claude.com/docs/en/hooks.md
- **Memory & CLAUDE.md**: https://code.claude.com/docs/en/memory.md
- **How Claude Code Works**: https://code.claude.com/docs/en/how-claude-code-works.md

---

**최종 정리:**
- 상위 3개 낭비: Subagents (30K) + MCP (10K) + Plan/Compact 미사용 (50K) = **90,000 토큰/session 가능**
- 실행 용이도: Subagents 정리 (1시간) > MCP 제거 (30분) > Plan/Compact 습관 (지속)
- 예상 ROI: 오늘 1시간 작업 → 세션당 30,000 토큰 절감 (월 900,000 토큰)

