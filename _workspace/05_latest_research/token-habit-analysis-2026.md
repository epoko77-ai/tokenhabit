# Claude Code 2026년 최신 기능의 토큰 낭비 패턴 & 해결책

> 2026-06-15 분석 기준. 공식 문서 검증 (code.claude.com/docs).
> 사용자의 무의식적 행동이 → 토큰 누출 경로 → 구체적 해결책

---

## 1. Subagents / Task Tool — 과다 생성 & 잘못된 위임

### 어떤 무의식적 행동이 문제인가?

**증상:**
- "이 연구를 subagent로 해줘" → 매번 새 subagent 생성
- WebSearch/WebFetch 결과를 "정리해줘" → 불필요하게 subagent 위임
- 병렬 작업 아니면서 `Task tool`로 5개 이상 동시 위임
- Subagent에 주 세션의 컨텍스트 전부 복제해서 전달

### 토큰이 어떻게 새는가?

**각 subagent = 완전히 독립된 context window:**
- 메인 세션 시스템 프롬프트: ~4,200 토큰 ✓ (이미 부담)
- **Subagent 시스템 프롬프트**: 추가 ~4,200 토큰
- **Custom system prompt 지정하면**: +1,000~5,000 토큰 (subagent마다)
- Subagent가 CLAUDE.md 전체 로드: 메인의 메모리 중복
- Task tool 각각이 "작업 시작/완료" 로그: 매번 ~200 토큰 누적

**예시 비용:**
- 5개 subagent 병렬 위임 = 기본 4,200 × 5 = **21,000 토큰 추가**
- Custom prompt + CLAUDE.md 중복 = +8,000 토큰
- 총: 한 턴에 **30,000 토큰** 낭비 (실제 작업은 각각 1,000~3,000)

### 구체적으로 어떻게 고칠 것인가?

**원칙:**
```
WebSearch/WebFetch 결과 정리 → subagent X
파일 로딩·변환·재포장 → subagent X  
긴 output 요약 → subagent X
실제로 병렬 비의존 작업 → subagent O
```

**해결책:**

1. **진짜 병렬만 subagent 위임**
   ```
   ✓ "한국 맥락 리서치" + "차트 설계" (동시, 비의존)
   ✓ 서로 다른 도메인 전문가 팀 (각각 자신의 domain knowledge)
   
   ✗ "첫 번째 검색 후 정리" (순차 → subagent 낭비)
   ✗ 단순 WebFetch 결과 요약 (메인에서 1라인)
   ```

2. **Subagent 설명 3줄 이내로 유지**
   - "한국 맥락 리서치 전담" vs "한국 정책, 산업, 사용자 사례, SNS 여론..."
   - 설명이 길수록 Claude가 subagent 유도 설명도 커짐 → 토큰 낭비

3. **Custom system prompt 지정하지 말 것**
   - 기본 subagent prompt로 충분 (이미 최적화)
   - 특수 지시는 `/task` 첫 메시지에 인라인

4. **Subagent 결과 길이 제한**
   - `summarize in 3-5 bullet points`를 subagent 지시에 명시
   - 상세 결과 필요 시 → 파일 생성 요청, 메인에서 필요할 때만 Read

**명령:**
```bash
# Subagent 최소 구성으로 실행
/task run-korean-research "한국 맥락 리서치. 답변은 5줄 이내."

# 기존 subagent 풀 확인
/agents  # 불필요한 subagent 제거
```

**효과:** ~30,000 토큰/회 절감 (불필요한 subagent 당 4,200 토큰)

---

## 2. MCP 서버 — 상시 연결 스키마가 컨텍스트 점유

### 어떤 무의식적 행동이 문제인가?

**증상:**
- 20개 이상의 MCP 서버 설정해놓고 대부분 사용 안 함
- Tools schema가 context에 "상시 로드된다"고 착각
- MCP 서버 추가할 때마다 설정만 하고 언제 쓸지 안 생각
- Google Drive, Gmail, Sheets 모두 연결했는데 1개만 씀

### 토큰이 어떻게 새는가?

**MCP 도구 로드 메커니즘:**

1. **기본 (Deferred)** = 똑똑함
   ```
   - Session 시작: 도구 이름만 로드 (~120 토큰 목록)
   - 실제 사용 시: 해당 스키마만 on-demand로 로드 (필요한 것만)
   - env: ENABLE_TOOL_SEARCH=auto (기본값)
   ```

2. **실제 문제 케이스** = 낭비
   ```
   ✗ ENABLE_TOOL_SEARCH=false → 모든 스키마 사전 로드
   ✗ 20개 MCP 서버가 400개 도구 = 20,000~50,000 토큰 스키마 점유
   ✗ Hook에서 MCP tool 호출 → 매 호출마다 스키마 재로드
   ```

3. **연결은 되는데 사용 안 하는 서버의 비용**
   ```
   - Vercel MCP (프로젝트 아닐 때)
   - Google Workspace (Drive/Sheets 하나만 쓰는데 Calendar/Tasks도 로드)
   - Computer Use (가끔만 필요한데 항상 대기 상태)
   ```

### 구체적으로 어떻게 고칠 것인가?

**1단계: MCP 서버 감시**
```bash
/mcp
# 각 서버별 활성 상태 + 스키마 크기 확인
# "미사용 서버" 표시된 것은 즉시 제거
```

**2단계: 실제 비용 측정**
```bash
/context
# MCP tools 섹션의 토큰 사용량 확인
# 20,000+ 토큰이면 과다 → 정리 필요
```

**3단계: 프로젝트별 MCP 선택**
```json
{
  "extraKnownMarketplaces": {
    "project-a": {
      "servers": ["vercel", "github"]  // A 프로젝트에만
    },
    "project-b": {
      "servers": ["gws"]  // B 프로젝트에만
    }
  }
}
```

**4단계: ENABLE_TOOL_SEARCH 명시**
```json
{
  "env": {
    "ENABLE_TOOL_SEARCH": "auto"  // 기본값, 명시하지 않으면 OK
  }
}
// NEVER "false" (모든 스키마 로드 = 낭비)
```

**5단계: Hook에서 MCP 호출 최소화**
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "mcp__.*",  // ✗ 매번 호출되는 MCP
        "type": "mcp_tool"
      }
    ]
  }
}
// → 더 나음: Command hook (shell 스크립트)로 캐시, MCP는 필요할 때만
```

**효과:**
- 미사용 MCP 5개 제거 = **5,000~10,000 토큰/세션 절감**
- Deferred loading 확인 = **10,000+ 토큰 낭비 방지**

---

## 3. Skills — Description 과다 로드 & 본체 중복 로드

### 어떤 무의식적 행동이 문제인가?

**증상:**
- 30개 이상의 skill을 ~/.claude/skills/ 에 보유 중
- Skill description이 200줄짜리 상세 매뉴얼
- 같은 기능의 skill이 여러 개 (tokensave v1, tokensave v2, ...)
- `disable-model-invocation: false` (모든 skill description 항상 로드)
- Skill 본체 SKILL.md가 10,000자 이상

### 토큰이 어떻게 새는가?

**1. Skill Description 로드**
```
- Session 시작 시 활성 skills의 description만 로드
- 각 skill description (기본) ≈ 300~500 토큰
- 30개 skill × 400 토큰 = 12,000 토큰 항상 점유
- 그 중 90%는 이번 세션에서 안 씀
```

**2. disable-model-invocation 설정 오류**
```json
{
  "disable-model-invocation": false  // ✗ description은 항상 노출
}

↓

각 세션마다:
- 설정된 모든 skill description 로드
- Claude가 자동으로 관련 skill 호출 → 본체 로드
- 사용하지 않은 skill도 로드됨 (혹시 모르니까)
```

**3. 중복 & 오래된 skill**
```
예: 
- /tokenhabit (v1.0) ← 옛 버전, 안 씀
- /tokenhabit (v1.1) ← 현재 버전
- /tokensave ← 관련
- /tokensave-audit ← 또 관련
- /context-manager ← 비슷한 기능

→ 모두 description 로드 = 2,000+ 토큰 낭비
```

**4. Skill 본체의 과도한 크기**
```
SKILL.md 구조:
- 프롬프트/지시: 2,000자 (필요)
- 참고 자료: 8,000자 (필요할 때만)
- 예시 20개: 5,000자 (클라우드에 저장)

→ 매번 skill 호출 시 15,000 토큰 로드
→ 참고자료는 on-demand로 로드 가능
```

### 구체적으로 어떻게 고칠 것인가?

**1단계: Skill 인벤토리**
```bash
ls -la ~/.claude/skills/
# 각 SKILL.md의 행수 확인
wc -l ~/.claude/skills/*/SKILL.md | sort -nr
```

**2단계: Description 길이 제한**
```markdown
# ✗ 현재 상태
---
description: |
  이 스킬은 토큰 습관을 진단합니다.
  여러 메트릭을 수집합니다.
  패턴을 분석합니다.
  결과를 시각화합니다.
  (200줄의 상세 설명)
---

# ✓ 개선안
---
description: |
  사용자의 토큰 낭비 습관을 진단하는 코칭 스킬.
  프롬프트 길이, 도구 사용 패턴, context 관리를 측정한다.
---
```

**3단계: disable-model-invocation 활용**
```json
{
  "skillOverrides": {
    "~/.claude/skills/tokenhabit/SKILL.md": {
      "disable-model-invocation": true
      // Claude가 자동으로 호출 안 함
      // 사용자가 /tokenhabit으로 명시 호출만
    }
  }
}
```

**4단계: 중복 skill 정리**
```bash
# 버전 관리: v1 제거, v1.1만 유지
rm -rf ~/.claude/skills/tokenhabit-v1/

# 비슷한 기능: tokensave + tokensave-audit 통합
# 앞으로 새로운 버전만 추가할 때 기존 버전 삭제 규칙
```

**5단계: Skill 본체 분리**
```
SKILL.md (현재: 15,000자)
  ↓
SKILL.md (프롬프트만: 3,000자)
  └─ @references/examples.md (예시)
  └─ @references/faq.md (자주묻는질문)
  
→ 기본 로드: 3,000 토큰
→ 필요 시 examples.md Read: +1,000 토큰 (선택)
```

**6단계: settings.json에서 확인**
```bash
/context
# Loaded skills 섹션의 토큰 합계 확인
# 8,000 토큰 이상 = 과다
```

**효과:**
- Description 길이 제한 = **2,000~5,000 토큰/세션 절감**
- disable-model-invocation 적용 = **1,000~3,000 토큰/세션 절감**
- 중복 skill 제거 = **400~800 토큰/skill**

---

## 4. Plan Mode, /context, /compact, /rewind 명령

### 어떤 무의식적 행동이 문제인가?

**증상:**
- Context 가득 찼는데 그냥 계속 대화 (auto-compact 걸릴 때까지 대기)
- `/context` 명령을 안 함 (상황 파악 없이)
- `/compact` 해봤는데 "내 지시가 사라졌다" → 다시 설명
- `/rewind`를 모르고 매번 세션 새로 시작
- Plan mode를 `Shift+Tab`으로 들어갔다가 나옴 (구조 모름)

### 각 명령이 토큰을 어떻게 절감하는가?

**1. `/context` — 상황 진단**
```bash
# 현재 context 구성 확인
/context

# 출력:
# System prompt: 4,200 tokens
# CLAUDE.md: 1,200 tokens
# Auto memory: 680 tokens
# Conversation: 89,200 tokens  ← 여기가 80%!
# Tools: 2,100 tokens
# Total: 97,380 / 200,000
```

**효과:**
- "context가 문제다" 확인 → `/compact` 타이밍 결정
- 낭비 요인 식별 (예: "Tool output이 15,000 토큰" → 지워도 됨)

**2. `/compact` — Context 요약 정리**
```bash
# 기본 compaction (자동 요약)
/compact

# 포커스와 함께 (중요한 것만 유지)
/compact focus on the authentication flow

# 절감 효과:
# Before: 150,000 tokens (대화 history 가득)
# After: 45,000 tokens (요약 + 필수만)
```

**⚠️ 주의:**
```
/compact 이후:
- CLAUDE.md는 다시 로드됨 (손실 없음)
- 대화 초반의 세부 지시는 요약됨 (CLAUDE.md에 옮길 것)
- 파일 경로/git 상태 등 환경정보는 유지
```

**효과:**
- 한 번의 `/compact` = **50,000~100,000 토큰 절감**
- 이후 대화 효율 증가 (새 명령 반응 빨라짐)

**3. `/rewind` — 체크포인트로 돌아가기**
```bash
# 최근 체크포인트 목록
/rewind

# 특정 체크포인트로
/rewind to "Before refactoring API"

# 효과:
# - 잘못된 경로 버림 (파일 변경 사항 제외)
# - Context history만 지워짐 (conversation 리셋)
# - 새 접근 시도 가능 (fresh context)
```

**Use case:**
```
❌ 현재: "아, 잘못됐어. 다시 처음부터"
   → 세션 종료 후 new session (context 낭비)

✓ 개선: /rewind to [checkpoint]
   → 체크포인트 이후 history 제거
   → 파일은 현재 상태 유지
   → 새로운 접근 시도
```

**4. Plan Mode — 코드 편집 없이 설계**
```bash
# Shift+Tab 두 번 (또는 /plan)
/plan

# 이 모드에서:
# - Read/Search: OK (파일 읽기, 탐색)
# - Edit/Write: X (파일 수정 안 함)
# - 계획 검토 후 approval 필요 (user에게 control)
```

**토큰 효율:**
```
❌ Without plan mode:
"API 수정해" → Claude가 10개 파일 수정 → 반을 되돌림

✓ With plan mode:
1. /plan 진입
2. Claude가 구조 분석 → 계획 제시 (Read만 사용)
3. 당신의 feedback
4. 계획 승인 후 실제 Edit (낭비 없음)
```

**효과:**
- 수정 work 60% 감소 (체계적 설계)
- 불필요한 Edit/Undo cycle 제거

### 구체적으로 언제 써야 할까?

```markdown
| 상황 | 명령 | 효과 |
|------|------|------|
| 대화 150K 이상 | `/compact focus on X` | -50K~100K 토큰 |
| 아, 다시 해야겠다 | `/rewind to [point]` | Context reset |
| "이게 맞을까?" | `/plan` (Shift+Tab×2) | 설계 검증 후 coding |
| 어디서 토큰 쓰지? | `/context` | 낭비 요인 식별 |
| 파일 많고 복잡 | `/compact focus on api/` | 범위 좁혀서 저장 |
```

**효과:**
- `/context` 습관 = **토큰 낭비 요인 조기 발견**
- `/compact` 적절 타이밍 = **50,000~100,000 토큰/세션 절감**
- `/plan` 습관 = **불필요한 Edit/Rewind cycle 60% 감소**

---

## 5. Extended Thinking / Reasoning Effort — 추가 토큰 소비

### 어떤 무의식적 행동이 문제인가?

**증상:**
- 어려운 문제 아닌데 `/effort xhigh` 설정
- 매번 thinking을 켜놓고 사용 (기본값 true가 됨)
- "왜 응답이 느려?" → thinking이 3분간 실행 중
- Complex 문제인데 low 설정해서 답변이 엉망

### 토큰이 어떻게 새는가?

**Thinking 토큰 구조:**
```
일반 응답 (no thinking):
- Prompt: 50,000 tokens
- Output: 1,000 tokens
- Total: 51,000

Extended thinking 켜짐:
- Prompt: 50,000 tokens
- Thinking (숨겨짐): 10,000~50,000 tokens ← 추가!
- Output: 1,000 tokens
- Total: 61,000~101,000 tokens
```

**무의식적 낭비 패턴:**
```
1. alwaysThinkingEnabled: true (settings.json)
   → 모든 메시지마다 thinking 시작
   → 단순 질문도 5,000+ 토큰 추가

2. /effort xhigh로 설정
   → 매번 deep reasoning (~30,000 토큰 추가)
   → 버그 수정 같은 간단 작업도

3. 이전에 thinking 설정 후 잊음
   → "왜 응답이 5분 걸려?"
   → thinking이 백그라운드에서 실행 중
```

### 구체적으로 어떻게 고칠 것인가?

**1단계: 현재 상태 확인**
```bash
/effort  # 현재 effort level 확인
cat ~/.claude/settings.json | grep -i thinking
```

**2단계: Thinking 끄기**
```json
// ✗ 낭비 설정
{
  "alwaysThinkingEnabled": true,
  "effortLevel": "xhigh"
}

// ✓ 기본 설정 (권장)
{
  "alwaysThinkingEnabled": false,
  "effortLevel": "medium"
}
```

**3단계: 문제 유형별 effort 선택**
```bash
# 간단한 문제 (수정, 추가)
/effort low

# 중간 복잡도 (구조 이해, 리팩토링)
/effort medium

# 복잡한 설계 (아키텍처, 알고리즘)
/effort high

# 매우 어려운 문제 + 깊은 생각 필요 (1회만!)
/effort xhigh
```

**4단계: 필요할 때만 thinking 활성화**
```bash
# "이 설계가 맞을까?" 한 번만
/effort xhigh

# 문제 해결 후 자동 복구
/effort medium  # 기본으로 돌아감
```

**효과:**
- `alwaysThinkingEnabled: false` + `medium` = **기본선**
- 불필요한 xhigh = **각 메시지 +30,000 토큰 낭비**
- 올바른 effort 선택 = **세션당 50,000~100,000 토큰 절감 가능**

---

## 6. 1M Context Window — 무한정 쌓기의 위험성

### 어떤 무의식적 행동이 문제인가?

**증상:**
- "context가 1M까지 되니까 계속 대화해도 괜찮겠지?"
- 한 세션을 3주 계속함 (checkpoint가 500개)
- "왜 응답이 점점 느려져?"
- 초반 지시가 점점 무시됨 (context 후반부 우선)

### 토큰이 어떻게 새는가?

**1. Context window의 실제 비용**
```
200K context window:
- 읽기: 200K 입력 × $0.003/1M = $0.0006 (저렴)
- 생성: 5K 출력 × $0.015/1M = $0.000075

1M context window (Opus 4.8):
- 읽기: 1M 입력 × $0.003/1M = $0.003 (5배 비쌈!)
- 생성: 5K 출력 × $0.015/1M = $0.000075
```

**2. 반응 지연의 원인**
```
- 200K: 즉시 응답 (~2초)
- 500K: 더 느림 (~5초)
- 1M+: 매우 느림 (~15초+)

이유: Context의 모든 token을 모델이 "주의(attention)"해야 함
     → 1M token = 5배 많은 계산
```

**3. 초반 지시 무시 현상**
```
가정: 1M context 95% 찼을 때 새 메시지

메시지 구성:
- 초반 지시 (위치: token 1~10K): 우선도 ★
- 최근 대화 (위치: token 950K~1M): 우선도 ★★★★★

→ 모델이 최근 context를 더 중요하게 여김
→ "어? 3주 전에 했던 지시가 왜 무시돼?"
```

### 구체적으로 어떻게 고칠 것인가?

**원칙:**
```
"Context window를 키웠다 ≠ 무한정 사용해도 된다"
```

**1단계: 세션 주기 설정**
```
당신의 습관:
- 3주 한 세션 → ❌ 너무 김
  
권장:
- 1주일마다 /compact 또는 새 세션
- 2주 이상 = 필수 /compact
- 1개월 = 새 세션 시작
```

**2단계: Auto-compaction 활용**
```json
{
  "autoCompactionConfig": {
    "triggerAtPercentage": 70,  // 70% 찼을 때 자동 시작
    "preserveConversationLength": 5000,  // 최근 5K 토큰은 유지
    "compactAfterTurns": 20  // 또는 20턴마다
  }
}
```

**3단계: Large context의 올바른 사용**
```
✓ 1M context는 "크고 복잡한 프로젝트를 한 세션에서 깊이 있게"
  예: 100K LOC 리팩토링 (1주 집중)

✗ 1M context를 "아무거나 계속 쌓는" 용도
  예: 3주간 여러 작업 섞음
```

**4단계: 긴 세션은 periodic checkpoint**
```bash
# 매 4~5시간마다
/context check

# 150K 이상이면
/compact focus on recent work

# 깃 커밋 타이밍에 checkpoint 생성
git commit -m "..."
```

**효과:**
- 정기적 /compact = **반응 속도 2~3배 향상**
- 초반 지시 재확인 = **명령 누락 0%로**
- 세션당 실제 비용 감소 = **일주일 단위로 초기화**

---

## 7. Background Tasks / 백그라운드 실행 — 과다 생성

### 어떤 무의식적 행동이 문제인가?

**증상:**
- 한 세션에서 `/background` 5개 이상 분기
- `claude agents` 실행하니 "Working" 25개 (뭐 하는지 모름)
- 백그라운드 작업이 자꾸 "needs input" → 방치 → 타임아웃
- 병렬 작업인데 실제로는 순차 실행됨

### 토큰이 어떻게 새는가?

**각 background session = 새로운 context window:**
```
메인 세션: 200K context
├─ Background task 1: 200K context (독립)
├─ Background task 2: 200K context (독립)
└─ Background task 3: 200K context (독립)

총 메모리: 800K context 동시 소비
```

**효율 문제:**
```
예: "API 문서화" + "테스트 작성" + "성능 최적화" (진짜 병렬)
→ 3개 background task (정당)

예: "한국어 번역" → "review" → "edit" (순차 작업!)
→ 3개 background task (낭비! 순차로 해야 함)
```

### 구체적으로 어떻게 고칠 것인가?

**1단계: Background vs Main 판단**
```
Background 생성 조건 (모두 만족):
□ 메인 세션과 비의존적 (먼저 끝날 필요 X)
□ 실제로 병렬 실행 가능 (시간이 겹침)
□ 결과가 필요 후 merge (완전히 독립 아님)

예:
✓ "대문서 번역" + "차트 설계" → 동시 (진정 병렬)
✗ "번역" → "리뷰" → "편집" → 순차 (background X)
```

**2단계: Background task 제한**
```bash
# 메인 작업에 집중
# Background는 진정 병렬인 것만 (일반적으로 2~3개 최대)

/agents  # 현재 background 상태 확인
# "Working" 5개 이상 = 과다, 정리 필요
```

**3단계: 백그라운드 모니터링**
```bash
# "Needs input"이 있으면 즉시 처리
# 또는 timeout 방지: timeout 10m 설정

/agents  # 실시간 확인
```

**효과:**
- 불필요한 background 3개 제거 = **600K context 절감 (동시)**
- 순차 작업 → 메인 세션 진행 = **더 빨리 완료**

---

## 8. 이미지 / 스크린샷 반복 첨부 — 누적 비용

### 어떤 무의식적 행동이 문제인가?

**증상:**
- 스크린샷 같은 이미지를 매번 명시적으로 첨부
- PNG/JPG 해상도 높은 그대로 (1920×1080, 2MB)
- "이전 스크린샷이 있는데?" 다시 붙임
- 매 turn마다 화면 갈린 거 첨부 (5개 이상)

### 토큰이 어떻게 새는가?

**이미지 토큰 비용:**
```
이미지 토큰 = (높이 × 너비) / 750 + 85

예:
- 1920×1080 PNG: (1920 × 1080) / 750 + 85 ≈ 2,500 토큰
- 800×600 PNG: (800 × 600) / 750 + 85 ≈ 750 토큰
- 실시간 스크린샷 1개: ~2,500 토큰
```

**누적 낭비:**
```
Turn 1: 스크린샷 A (2,500)
Turn 2: 스크린샷 B + A 다시 (2,500 + 2,500)
Turn 3: 스크린샷 C + B + A 또 (2,500 + 2,500 + 2,500)

→ 15,000 토큰 낭비 (같은 이미지 반복 로드)
```

### 구체적으로 어떻게 고칠 것인가?

**1단계: 첫 첨부 후 참조**
```
❌ 현재:
1. "스크린샷 해줘" → [스크린샷 A 붙임]
2. "이건 왜 그래?" → [스크린샷 A 또 붙임]

✓ 개선:
1. "스크린샷 해줘" → [스크린샷 A 붙임]
   Claude: "OK, A의 상태 파악"
2. "이건 왜 그래?" → "위 스크린샷에서"
   (재첨부 X, 참조만)
```

**2단계: 해상도 최적화**
```bash
# 고해상도 스크린샷
# 1920×1080 (2,500 토큰) → 1024×768 (1,000 토큰)

# macOS/Linux
screencapture -x out.png  # 현재 스크린
convert out.png -resize 1024x768 small.png  # 크기 줄임

# 또는 내장 도구 사용 (낮은 해상도 선택)
```

**3단계: Context에서 제거**
```bash
# 더 이상 필요 없는 스크린샷 (5 turn 이상 전)
/context  # 이미지 토큰 확인
# 오래된 이미지는 reference만, 다시 붙이지 말 것
```

**효과:**
- 스크린샷 1개 재첨부 금지 = **2,500 토큰/turn 절감**
- 해상도 최적화 = **1,500 토큰/스크린샷 절감**

---

## 9. WebSearch / WebFetch 남발 — 캐싱과 중복

### 어떤 무의식적 행동이 문제인가?

**증상:**
- 같은 URL을 3번 이상 fetch (캐싱을 모름)
- "결과를 더 자세히" → 같은 URL fetch 또 (결과는 캐시됨)
- WebSearch로 매번 새 검색 (같은 쿼리, 매번 API call)
- Fetch 결과를 전부 context에 로드 (100KB 페이지)

### 토큰이 어떻게 새는가?

**WebFetch 캐싱:**
```
기본 설정: 15분 자동 캐시 (in-memory)

같은 URL을 2번:
1차: /fetch google.com → API call (유료)
2차: /fetch google.com → 캐시에서 (free!)

하지만 사용자가 모르면:
1차: API call + 토큰 로드
2차: "왜 같은 내용?" → 또 fetch (캐시 안 됨, 새 API call)
```

**WebSearch 중복:**
```
"Claude 최신 버전" → WebSearch

Turn 1: 검색, 결과 로드
Turn 2: 같은 정보로 답변
Turn 3: "더 자세히" → WebSearch 또 (필요 없음!)
```

**결과 크기 낭비:**
```
WIRED 기사 fetch (50KB)
→ Claude에 전부 로드: 10,000+ 토큰
→ 실제 필요: 500 토큰 (intro 문단)
```

### 구체적으로 어떻게 고칠 것인가?

**1단계: WebFetch 캐싱 확인**
```bash
# 15분 자동 캐시는 기본값
# 명시 설정하려면
env CLAUDE_FETCH_CACHE_TTL=900  # 초 단위

# "같은 URL fetch 필요" → /cache clear로 강제 갱신
```

**2단계: WebSearch 결과 재사용**
```
❌ 현재:
"Claude 최신 버전이 뭐야?" → WebSearch
"얼마에 팔아?" → WebSearch 또 (첫 검색 결과에 있음!)

✓ 개선:
"Claude 최신 버전이 뭐야?" → WebSearch
"얼마에 팔아?" → "위 검색 결과에서..."
   (이미 context에 있음)
```

**3단계: WebFetch 결과 요약 요청**
```
❌ 현재:
/fetch wired.com/article
→ 50KB 페이지 전부 로드 (10,000 토큰)

✓ 개선:
/fetch wired.com/article
"intro 문단과 주요 포인트만 정리해줘"
→ 자동으로 요약 (2,000 토큰)
```

**4단계: 수동 제어**
```bash
# 이전 검색 결과로 충분하다면
# "위에서 본 것처럼"만 언급

# 정말 새로운 정보 필요할 때만
/search "2026년 최신 Claude 가격" (명시적)
```

**효과:**
- WebSearch 중복 제거 = **3,000~5,000 토큰/session 절감**
- WebFetch 요약 요청 = **5,000+ 토큰/fetch 절감**

---

## 10. Output Styles / 응답 길이 설정 — 과장된 설정

### 어떤 무의식적 행동이 문제인가?

**증상:**
- 기본값 그대로 사용 (Claude가 자동 결정)
- "자세히 설명해줘" → 10페이지 응답 (필요 30줄)
- 간단한 버그 수정인데 "설명까지" → 2,000 토큰 output
- 모든 turn마다 "간단하게" 안 함 (반복 지시)

### 토큰이 어떻게 새는가?

**Output 토큰 비용:**
```
Output token = 생성 토큰 × 가격

Claude 3.5 Sonnet:
- 입력: $3/1M
- 출력: $15/1M (5배!)

즉, 출력 1,000 토큰 = 입력 5,000 토큰 가격
```

**과장된 응답:**
```
간단한 fix:
- 최소 응답: "라인 52에서 로직 바꿈" (10 토큰)
- 현재 응답: "라인 52에서... 이유는... 대안은... 테스트..." (500 토큰)
→ 50배 비용!
```

### 구체적으로 어떻게 고칠 것인가?

**1단계: 상황별 지시 설정**
```
❌ 기본 ("자세하게" 기본값이면)
❌ 매번 "간단하게" 반복

✓ 상황별:
"이 버그만 고쳐줘 (설명 없이)" → 코드만
"새 API 설계 → 설명과 함께"
"스크린샷 확인" → 짧은 피드백만
```

**2단계: Prompt에서 output 길이 명시**
```markdown
# ✗ 현재
"이 코드 버그 고쳐줘"
← Claude가 자동으로 설명까지 추가

# ✓ 개선
"이 코드 버그 고쳐줘. 코드만 제시 (설명 X)"
← 응답 200 토큰 (vs 500)
```

**3단계: Output style 프리셋**
```json
{
  "outputPresets": {
    "minimal": "Answer in 1-2 sentences, no explanation",
    "normal": "Normal explanation with context",
    "detailed": "Comprehensive explanation with alternatives"
  }
}
```

**사용:**
```bash
# 간단한 답변 모드
/style minimal

# 자세한 설명 필요할 때만
/style detailed
```

**효과:**
- 불필요한 설명 제거 = **50~80% output 토큰 절감**
- 세션당 평균 = **10,000~20,000 토큰 절감**

---

## 11. Hooks가 매 호출마다 주입하는 컨텍스트

### 어떤 무의식적 행동이 문제인가?

**증상:**
- Hook에서 additionalContext로 매번 긴 설명 주입
- Pre/Post hook에서 모두 context 추가 (중복)
- Hook 파일이 없는데 설정은 있음 (비활성화 안 함)
- 매 tool use마다 "이건 생성 파일입니다" 주입

### 토큰이 어떻게 새는가?

**Hook context 주입:**
```
// settings.json
hooks:
  PreToolUse:
    additionalContext: |
      주의: 이 파일은 생성되었습니다.
      변경하면 안 됩니다.
      (500자 설명)

매 tool use마다 → 500 토큰 추가
하루 50번 tool use → 25,000 토큰 낭비
```

**여러 hook의 누적:**
```
UserPromptSubmit hook: +200 토큰
PreToolUse hook: +500 토큰
PostToolUse hook: +300 토큰

→ 매 turn마다 1,000 토큰 overhead
```

### 구체적으로 어떻게 고칠 것인가?

**1단계: Hook 감사**
```bash
/hooks  # 설정된 hook 목록

# 비활성 hook 제거
cat ~/.claude/settings.json | jq '.hooks' | less
```

**2단계: additionalContext 최소화**
```json
// ✗ 낭비
{
  "hooks": {
    "PostToolUse": [
      {
        "additionalContext": "주의: 이 파일은 생성됨. 직접 수정하지 말 것. \n코드 생성 중일 때 사용자의 변경사항은 덮어씌워질 수 있습니다..."
      }
    ]
  }
}

// ✓ 개선
{
  "hooks": {
    "PostToolUse": [
      {
        "if": "Write",
        "additionalContext": "이 파일은 생성됨. 수정 주의."
      }
    ]
  }
}
```

**3단계: Hook 특정 도구에만 적용**
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",  // 모든 tool이 아니라 Bash만
        "hooks": [
          {
            "type": "command",
            "command": "/path/to/check.sh"
          }
        ]
      }
    ]
  }
}
```

**4단계: Async hook 활용**
```json
{
  "hooks": {
    "PostToolUse": [
      {
        "type": "command",
        "async": true,  // 백그라운드 실행
        "asyncRewake": false  // context 주입 안 함
      }
    ]
  }
}
```

**효과:**
- 과다 additionalContext 제거 = **1,000~5,000 토큰/turn 절감**
- 비활성 hook 정리 = **200~500 토큰/turn 절감**

---

## 12. MEMORY.md 비대화 & 쓸모없는 메모 축적

### 어떤 무의식적 행동이 문제인가?

**증상:**
- MEMORY.md가 200줄 초과 (기본 200줄 로드됨)
- "이건 이전에 했던 거" → 메모에 남음
- 3개월 된 메모가 아직 있음 (지금은 쓸모없음)
- Auto memory를 안 정리해본 적 없음

### 토큰이 어떻게 새는가?

**Auto Memory 로드:**
```
MEMORY.md 첫 200줄 또는 25KB까지 매 세션마다 로드

현재 상태:
- 유용한 메모: 50줄 (필요)
- 옛날 메모: 100줄 (안 쓰임)
- 중복: 30줄 (다른 곳에 있음)

→ 200줄 전부 로드: 3,000~5,000 토큰 (매 세션!)
→ 실제 필요: 1,000 토큰
→ 낭비: 2,000~4,000 토큰/세션
```

### 구체적으로 어떻게 고칠 것인가?

**1단계: MEMORY.md 감시**
```bash
/memory  # auto memory 파일 목록

wc -l ~/.claude/projects/*/memory/MEMORY.md
# 200줄 이상이면 정리 필요
```

**2단계: MEMORY.md 구조 정렬**
```markdown
# MEMORY.md (현재: 250줄)

↓

## 유효한 항목만 (60줄)

# 최근 패턴 (Build commands)
- `npm run dev` always, not `npm start`
- tests take 3min (expected)

# 최근 실수
- Async/await 체크 잊으면 에러

# 최근 발견 (설계)
- API v2 미마이그레이션 (큰 파일들)
```

**3단계: Topic files로 이동**
```
MEMORY.md (50줄): 핵심만
├─ debugging.md: "이전에 막혔던 것" 상세
├─ patterns.md: 코드 패턴 모음
└─ api-notes.md: API 설계 노트

→ MEMORY.md만 로드 (매 세션)
→ 필요할 때만 topic file read
```

**4단계: 월간 정리**
```bash
# 매월 1일
/memory
# 3개월 이상 된 항목 삭제
# 중복된 항목 통합
```

**효과:**
- MEMORY.md 최적화 = **2,000~4,000 토큰/세션 절감**

---

## 13. 기타 최신 기능 중 토큰을 새게 하는 것

### Worktree 과다 사용
```
Git worktree는 각각 독립 디렉토리.
Git이 각 worktree마다 CLAUDE.md 로드.
10개 worktree = 10배 CLAUDE.md 로드?

No: Auto memory는 repo 전체 공유
Yes: CLAUDE.md는 각 worktree마다 로드 가능

→ worktree 많으면 .claude/CLAUDE.md 통합 권장
```

### Task tool 오버헤드
```
Task tool = subagent가 아닌 동시 작업 추적
각 task = 상태 메타 ~100 토큰

50개 동시 task = 5,000 토큰 overhead

→ 5개 이상 task는 정리 후 진행 권장
```

### Chrome 연결 (claude.ai/code에서)
```
Browser instance = context overhead
스크린샷 캡처 매번 2,000+ 토큰

→ 필요할 때만 활성화
→ 매번 스크린샷 첨부 X
```

### 플러그인 다중 설치
```
Vercel plugin + GWS plugin + Harness plugin
→ 각 plugin의 시스템 프롬프트 추가

총 plugin 시스템 프롬프트: 2,000+ 토큰

→ 프로젝트별로 필요한 것만 활성화
enabledPlugins 설정으로 선택적 로드
```

---

## 정리: 토큰 낭비 우선순위 & 어디서부터 시작할까?

### 영향도 × 실행 난이도

| 우선 | 기능 | 절감 | 난이도 | 추천 |
|------|------|------|--------|------|
| **1순위** | Subagent 과다 | 30,000 | ⭐ | 지금 바로 |
| **2순위** | Extended Thinking 무의식 활성화 | 20,000 | ⭐ | 지금 바로 |
| **1.5순위** | 불필요한 MCP 서버 | 10,000 | ⭐ | 지금 바로 |
| **3순위** | Plan mode 미사용 | 50,000 | ⭐⭐ | 이번주 |
| **4순위** | /compact 습관 부족 | 50,000 | ⭐⭐ | 이번주 |
| **5순위** | Skill description 과다 | 5,000 | ⭐⭐ | 다음주 |
| **6순위** | MEMORY.md 비대화 | 4,000 | ⭐ | 지금 바로 |
| **7순위** | Hook context 낭비 | 3,000 | ⭐⭐ | 다음주 |
| **8순위** | 이미지 반복 첨부 | 2,500 | ⭐ | 습관 개선 |
| **9순위** | WebSearch 중복 | 3,000 | ⭐ | 습관 개선 |

### 실행 로드맵

**오늘 (1시간)**
```bash
1. /effort → medium 확인 (기본값)
2. /agents → 비자산 subagent 정리 (3개 이상이면 stop)
3. /mcp → 미사용 서버 확인 (5개 이상이면 제거)
4. /memory → MEMORY.md 200줄 초과 확인 (정리)
```

**이번주 (2시간)**
```bash
1. /plan 명령 학습 (Shift+Tab ×2)
2. /compact 실행 (context 150K 넘으면)
3. /context 습관 들이기 (매 세션 1회)
4. 자신의 토큰 습관 진단 (`/manpower` skill 활용)
```

**다음주 (3시간)**
```bash
1. settings.json에서 skill description 최적화
2. Hook 감사 (불필요한 것 제거)
3. CLAUDE.md 200줄 유지 규칙 설정
4. Background task 정책 수립 (병렬 조건 명시)
```

---

## 참고: 공식 문서

- **Context window 시뮬레이터**: https://code.claude.com/docs/en/context-window.md
- **Subagents**: https://code.claude.com/docs/en/subagents.md
- **MCP 서버**: https://code.claude.com/docs/en/mcp-servers.md
- **Skills**: https://code.claude.com/docs/en/skills.md
- **Commands 전체**: https://code.claude.com/docs/en/commands.md
- **Hooks 레퍼런스**: https://code.claude.com/docs/en/hooks.md
- **Memory**: https://code.claude.com/docs/en/memory.md
- **How Claude Code Works**: https://code.claude.com/docs/en/how-claude-code-works.md

---

**버전**: tokenhabit 진단용 기초 자료 (2026-06-15)
**다음 업데이트**: Claude Code v2.2 릴리스 후 재검증

