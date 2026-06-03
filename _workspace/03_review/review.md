# tokenhabit SKILL.md — Q1 감사 리뷰

> 감사 일시: 2026-06-03  
> 감사자: Q1 (리뷰어 에이전트)  
> 대상 파일: `skill/SKILL.md`, `skill/references/habit_catalog.md`, `skill/references/session_coach_checklist.md`  
> 직교 대조: `tokensave/SKILL.md`

---

## 감사 결과 요약

| 종합 판정 | BLOCKER | MAJOR | MINOR |
|-----------|---------|-------|-------|
| **수정후PASS** | 2 | 4 | 5 |

---

## 축 1 — 기술 정확성

### [축1][BLOCKER] habit_catalog.md:H4-01 — thinking 토큰 재과금 설명이 틀림

**위치:** `references/habit_catalog.md` H4-01 "추론의 망령", 157줄 전후

**문제:**  
"이전 턴의 thinking 블록이 컨텍스트에 보존되어 다음 턴 input 토큰으로 재과금된다. output 토큰으로 최초 과금 + 캐시 input으로 재과금되는 이중 비용 구조."

공식 Anthropic 문서에 따르면, thinking 토큰은 생성 시점에 output 토큰으로 1회만 과금되며 후속 턴에서 재과금되지 않는다. 단, thinking 블록이 캐시에서 읽힐 때 캐시 input 토큰으로 카운트되는 것은 사실이나, "재과금(re-billed)"이라는 표현은 과장이다. Opus 4.5+/Sonnet 4.6+ 이전 모델에서는 이전 턴의 thinking 블록이 컨텍스트에서 **제거**되어 오히려 절감이 발생한다. Opus 4.5+/Sonnet 4.6+에서는 thinking 블록이 유지되지만 캐시 hit 시 캐시 input 요금(base × 0.1)이 적용될 뿐이다.

또한 "Sonnet 4.6과 Opus 4.5+ 모델에서"라는 범위 지정이 SKILL.md 본문(H4-01)에는 누락되어 모델 무관하게 재과금이 발생하는 것처럼 서술되어 있다.

**수정지시:**  
- H4-01의 "왜 새는가" 섹션을 다음으로 교체:  
  "Opus 4.5+/Sonnet 4.6+ 모델에서 이전 턴의 thinking 블록이 컨텍스트에 보존된다. 최초 output 토큰으로 1회 과금되며 후속 턴에서는 재과금되지 않는다. 단 캐시에서 읽힐 때 캐시 input 요금(base × 0.1)이 발생한다. 컨텍스트가 커질수록 이 누적은 무시할 수 없는 비용이 된다."  
- "이중 비용 구조" 표현 삭제.  
- 절감 추정치 "30~60%" 도 재검토 필요(과장 가능성).

---

### [축1][BLOCKER] habit_catalog.md:H1-03 — 자동 compaction 임계치를 "83.5% / ≈167K"로 단정

**위치:** `references/habit_catalog.md` H1-03 "compaction 버스 막차 타기", 41줄

**문제:**  
"자동 compaction은 약 83.5% 임계점(200K 윈도우 기준 ≈167K 토큰)에서 발동한다(정확 수치 검증 필요)."

괄호 안에 "검증 필요"를 달았음에도 수치를 확정 표기했다. 공식 Anthropic 문서는 자동 compaction 임계치를 구체적인 퍼센트로 공개하지 않으며, 모델/버전에 따라 다를 수 있다고만 명시한다. 이 수치의 출처가 불명확하고 SKILL.md 본문(H1-03 자각신호 "컨텍스트 사용률 50% 초과") 및 SKILL.md 퀵카드(50~60%)와도 숫자가 일치하지 않아 내적 일관성도 깨진다.

**수정지시:**  
- "약 83.5% 임계점(200K 윈도우 기준 ≈167K 토큰)에서 발동한다" → "컨텍스트 상한에 접근하면 발동한다(정확 임계치는 미공개)"로 교체.  
- SKILL.md 퀵카드·본문과 "50~60%에 수동 compact" 일관성은 유지.

---

### [축1][MAJOR] SKILL.md:H4-02, session_coach_checklist.md — `Option+O`(fast mode) 설명 미검증

**위치:** `references/habit_catalog.md` H4-02, `references/session_coach_checklist.md` 패턴별 즉시 fix 표

**문제:**  
"`Option+O`(fast mode)로 빠른 응답 요청"이라고 명시하나, 공식 문서에서 fast mode 단축키는 확인되었지만 그것이 `Option+O`인지는 공식 keybindings 페이지에서 명시적으로 확인되지 않았다. `Option+T`(thinking 비활성화)는 공식 문서에서 확인됨. `Option+O`는 독립 fast mode 단축키로 추정되나 현재 단정 표현은 미검증이다.

**수정지시:**  
- `Option+O`에 "(공식 문서에서 키바인딩 확인 권장)" 주석 추가 또는 `/effort low`·fast mode 명시로 대체.  
- 또는 공식 keybindings 페이지(`code.claude.com/docs/en/keybindings`)를 직접 확인 후 확정.

---

### [축1][MAJOR] SKILL.md:H5-04 — `/btw`가 히스토리에 추가되지 않는다는 설명은 조건부 정확

**위치:** `references/habit_catalog.md` H5-04, `references/session_coach_checklist.md` H8-01

**문제:**  
"`/btw` 활용 — 답변이 컨텍스트에 추가되지 않음(공식 확인)"이라고 단정하고 있다.  
실제로 `/btw`는 2026-03-10(v2.1.72) 공식 도입된 기능이며, 답변이 주 대화 히스토리에 추가되지 않는 것은 사실이다. 그러나 GitHub issue #33159(2026-03-11)에서 도입 직후 "Unknown skill: btw"로 작동하지 않는 버그가 보고됐고, issue #45460 등 후속 버그들도 존재한다. 또한 `/btw`는 **tool 접근 불가** 제한이 있으나 SKILL.md에 이 중요한 제한이 전혀 언급되지 않는다. H8-01에서 "이미 컨텍스트에 있는 정보 질문은 `/btw` 사용"이라는 권고는 이 제한 때문에 올바른 용례이지만, H5-04에서의 맥락은 불완전하다.

**수정지시:**  
- H5-04와 H8-01에 `/btw` 제한 사항 추가: "단, `/btw`는 파일 읽기·Bash 등 tool 접근 불가. 컨텍스트에 이미 있는 정보에만 활용 가능."  
- "(공식 확인)" 대신 명확한 버전 표기: "(Claude Code v2.1.72+ 공식 기능)"

---

### [축1][MAJOR] SKILL.md:퀵카드 — `/rename` → `/resume`으로 이전 세션 보존 설명 불완전

**위치:** `skill/SKILL.md` 퀵카드 #1, 20줄

**문제:**  
"`/rename` → `/resume`으로 이전 세션 보존 가능"이라고 설명하나, `/resume`은 슬래시 커맨드이자 CLI 플래그(`claude --resume <name>`)로도 사용 가능하다는 것이 공식 문서에 확인된 사실이다. 퀵카드에서는 이 두 사용법이 혼재되어 설명이 부정확해 보인다. 또한 `/rename`이 세션 내부 명령어이고, 재개 시 `/resume <name>` 또는 `claude --resume <name>` 두 방법이 있다는 점을 명확히 해야 사용자가 올바르게 쓸 수 있다.

**수정지시:**  
- 퀵카드 #1 fix 설명을 "작업 전환마다 `/clear`. `/rename <이름>`으로 세션 이름 지정 → 이후 `/resume <이름>` 또는 `claude --resume <이름>`으로 복귀 가능"으로 수정.

---

### [축1][MINOR] SKILL.md:MODE 4 룰 #3 — `/rewind` 표기와 Esc+Esc 설명

**위치:** `skill/SKILL.md` MODE 4, 134줄

**문제:**  
"2회 실패 후 `/compact` 또는 `/rewind` 제안"에서 `/rewind`는 공식적으로 "Esc+Esc 또는 /rewind" 모두로 열 수 있는 메뉴이며, habit_catalog.md H1-02에서 "Esc+Esc(`/rewind`)"로 표기한 것과 일관성 있어 MINOR이지만, 공식 문서에서 `/rewind`는 단순 roll-back이 아닌 "대화만/코드만/둘다/요약" 4개 옵션을 제공하는 메뉴임을 명시하지 않는다.

**수정지시:**  
- H1-02와 MODE 4 룰 #3에 `/rewind` 설명을 "대화·코드·둘다·요약 4가지 복원 옵션"이라는 한 줄 주석 추가.

---

### [축1][MINOR] SKILL.md:SKILL.md 본문 vs habit_catalog.md 패턴 수 불일치

**위치:** `skill/SKILL.md` 70줄 ("8카테고리 24패턴"), 참고 자료 148줄 ("8카테고리 27패턴")

**문제:**  
SKILL.md 본문에서 MODE 2 설명은 "24패턴"이라고 하지만, habit_catalog.md 제목은 "27패턴"이고, 참고 자료 섹션도 "8카테고리 27패턴"이라고 쓴다. 실제 habit_catalog.md를 세면 24패턴(H1~H8, 각 4+3+3+3+4+2+3+2=24)이다. SKILL.md 본문이 "R1 14개 + R2 13개 원본에서 3쌍의 완전 중복 제거 후 통합"으로 24가 됐다고 설명했으면서 참고 자료와 habit_catalog.md 제목을 27로 남긴 것은 일관성 오류다.

**수정지시:**  
- habit_catalog.md 제목을 "8카테고리 24패턴"으로 수정.  
- SKILL.md 참고 자료 섹션의 "8카테고리 27패턴"을 "8카테고리 24패턴"으로 수정.

---

## 축 2 — tokensave 직교성

### [축2][MAJOR] SKILL.md:H3-02 — MCP 비활성화에 `/mcp` 커맨드 언급이 tokensave 레이어와 경계 모호

**위치:** `skill/SKILL.md` 직접 참조 없으나 `references/habit_catalog.md` H3-02, 131줄

**문제:**  
"`/mcp` 명령으로 현재 연결 서버 확인 후 미사용 서버 비활성화"라는 구체적인 MCP 서버 관리 지시는 tokensave의 "항상 켜진 컨텍스트 오버헤드(C4)" 범주와 완전히 동일한 레이어다. tokensave는 SKILL.md 비대화와 MCP 스키마 고정 오버헤드를 C4 카테고리로 다룬다. tokenhabit의 H3-02는 사용자 **습관**("혹시 필요할지 몰라서 켜놓는다") 차원이므로 레이어는 다르지만, fix 내용이 "MCP 서버 설정 변경"으로 가면 tokensave 영역으로 침범한다.

**수정지시:**  
- H3-02 "고치는습관" 섹션을 습관 자각에 집중시키고, 구체적인 MCP 설정 방법은 "→ 설계 레벨 가이드는 `tokensave` 참조"로 넘긴다.  
- 예시: "세션 시작 전 이 작업에 필요한 MCP 서버만 켜는 습관을 들인다. 어떤 서버를 끌지 설계 기준 → tokensave 참조."

---

### [축2][MINOR] SKILL.md:H4-03 — 캐시 무효화 설명이 tokensave C5와 내용 중복

**위치:** `references/habit_catalog.md` H4-03 "캐시 킬 스위치"

**문제:**  
"모델 전환 또는 thinking 파라미터 변경은 캐시 브레이크포인트를 무효화해…"는 캐싱 설계 레이어(tokensave C5)와 겹친다. 단, tokensave는 "캐시를 어떻게 설계할 것인가"를 다루고 tokenhabit는 "사용자가 무심코 캐시를 깨는 습관"을 다루므로 렌즈는 다르다. 완전 재탕은 아니지만 경계가 흐릿하다.

**수정지시:**  
- H4-03 "왜 새는가" 마지막에 "캐시 설계 원칙 → tokensave 참조" 1줄 추가로 경계를 명시.

---

## 축 3 — 트리거 충돌

### [축3][MAJOR] description 트리거 — "컨텍스트가 너무 커졌어" 충돌

**위치:** `skill/SKILL.md` frontmatter description 3줄

**문제:**  
tokenhabit description의 트리거 문구 중 "컨텍스트가 너무 커졌어"는 tokensave description의 "context bloat" 트리거와 동일 의미다. 사용자가 "컨텍스트가 너무 커졌어"를 입력하면 두 스킬 중 어느 것이 우선 발동할지 모델이 자의적으로 결정하게 된다.

겹치는 트리거 전체 목록:
- "컨텍스트가 너무 커졌어" ↔ tokensave "context bloat"
- "compact 언제 써야 해" — tokensave는 명시적 트리거는 아니나 "토큰 절감" 범주에 포함될 가능성

**수정지시:**  
- "컨텍스트가 너무 커졌어"를 "이 세션 컨텍스트가 너무 커졌어, /compact 언제 해야 해"처럼 사용자 행동·세션 차원임을 명확히 하는 문구로 교체.  
- 또는 해당 트리거를 제거하고 "세션이 너무 길어진 것 같아"로 통합.  
- description 앞부분에 "설계·모델 티어·캐싱 → tokensave / 운전자 대화 습관 → tokenhabit" 구분 문장 1줄 추가.

---

### [축3][MINOR] description 트리거 — "왜 이렇게 토큰을 많이 써" 경계 모호

**위치:** `skill/SKILL.md` frontmatter description

**문제:**  
"왜 이렇게 토큰을 많이 써"는 하네스 감사 맥락(tokensave)으로도 해석될 수 있다. 사용자가 에이전트 팀을 운영하다 이 문구를 쓴다면 tokensave가 더 적절한 스킬이다. 그러나 개인 대화 세션 맥락에서는 tokenhabit이 맞다.

**수정지시:**  
- 트리거를 "대화 중 왜 이렇게 토큰을 많이 써"로 맥락을 강화하거나, description에 "(하네스/에이전트 토큰 낭비 → tokensave)"라는 구분 힌트를 추가.

---

## 축 4 — Actionable·자기일관성

### [축4][MINOR] SKILL.md 본문 분량 — 토큰 절감 스킬 치고 참조 구조 최적화 여지

**위치:** `skill/SKILL.md` 전체

**문제:**  
SKILL.md 본문은 약 153줄로, 200줄 권고 미만이다. 구조는 퀵카드 + 4모드 + 참조링크로 잘 분리되어 있어 자기 원칙(200줄 미만, references 분리)을 준수한다. 단, MODE 2 HABIT CATALOG의 요약 테이블(8행)은 유지되어 있고 상세는 habit_catalog.md로 위임한 구조가 올바르다.  
문제는 MODE 4(HABIT GUARD)의 7개 룰 테이블이 MODE 1 SESSION COACH와 중복되는 항목(로그 덤프 필터, 서브에이전트 위임, /compact 제안)이 있어 실질적으로 같은 내용이 두 번 나온다.

**수정지시:**  
- MODE 4 룰 테이블에서 MODE 1과 완전히 동일한 항목(로그 필터, 서브에이전트, compact)은 "MODE 1 SESSION COACH와 동일 — 런타임 자가점검용"이라는 1줄로 압축하고 나머지만 유지.

---

### [축4][MINOR] session_coach_checklist.md — 자각신호 9개와 SKILL.md MODE 1 진단 3단계가 구조적으로 일부 중복

**위치:** `skill/references/session_coach_checklist.md`

**문제:**  
SKILL.md MODE 1의 진단 절차(세션 위생 점검 3항, 반복 입력 점검 3항, 프롬프트 습관 점검 3항)와 session_coach_checklist.md의 9대 신호 표가 거의 1:1 매핑된다. 분리 자체는 올바른 구조이나 SKILL.md에 이미 충분히 서술한 내용을 checklist에서 다시 서술해 두 파일을 동시에 유지해야 하는 부담이 발생한다.

**수정지시:**  
- MINOR 수준이므로 즉각 수정 불필요. 향후 v1.1에서 SKILL.md MODE 1을 checklist 파일 참조로 완전히 위임하는 방식으로 통합 권장.

---

## 전체 종합

| 판정 | 사유 |
|------|------|
| **수정후PASS** | BLOCKER 2건(H4-01 thinking 재과금 오설명, H1-03 임계치 단정)은 기술적으로 틀린 내용이므로 반드시 수정. MAJOR 4건 수정 완료 후 재검토 불필요. 핵심 구조(4모드 + references 분리 + 직교 선언)는 올바르다. |

### BLOCKER 목록 (2건)

1. **[B1] H4-01 thinking 토큰 이중 과금 오설명** — `habit_catalog.md` H4-01 "왜 새는가"  
   → thinking 블록은 생성 시 1회 output 과금. "재과금" 표현과 모델 범위 미명시 수정 필요.

2. **[B2] H1-03 자동 compaction 임계치 83.5%/167K 미검증 단정** — `habit_catalog.md` H1-03  
   → 공식 미공개 수치. "컨텍스트 상한 접근 시 발동(임계치 미공개)"으로 교체.

### MAJOR 목록 (4건)

1. **[M1] H4-02/checklist — `Option+O` fast mode 단축키 미검증** — 공식 문서에서 확정 미완료.  
2. **[M2] H5-04/H8-01 — `/btw` tool 접근 불가 제한 미언급** — 중요 제한 사항 누락.  
3. **[M3] 퀵카드 #1 — `/rename`→`/resume` 사용법 부정확** — CLI 플래그 vs 슬래시 커맨드 혼용.  
4. **[M4] description 트리거 — "컨텍스트가 너무 커졌어" ↔ tokensave "context bloat" 충돌** — 발동 스킬 모호성.
