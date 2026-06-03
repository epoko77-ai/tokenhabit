# 능동(Active) 상호작용 토큰 낭비 패턴 — R2 리서치

> 담당: R2 패턴 리서처 (능동 상호작용 계열)
> 기준: Claude Code 공식 문서 (code.claude.com/docs) 기반 검증
> 작성일: 2026-06-03
> 총 패턴: 13개

---

## 카테고리 구성

- **A. 프롬프트 명료성** (A1~A4): 요청 방식 자체의 낭비
- **B. 재작업 루프** (B1~B3): "다시 해줘" 패턴의 낭비
- **C. 영속화 미활용** (C1~C3): 반복 입력 습관의 낭비
- **D. 컨텍스트 오염** (D1~D3): 메인 대화 흐름 오염의 낭비

---

## A. 프롬프트 명료성 계열

---

### A1. 안개 프롬프트 (모호한 요청 → 명료화 왕복)

**패턴 ID**: A1 | **이름**: 안개 프롬프트

**무의식 시나리오**
```
"이 코드 좀 개선해줘"
"로그인 버그 고쳐줘"
```

**왜 토큰이 새는가**
Claude는 무엇을 개선할지, 어느 파일인지, 어떤 버그인지 모르기 때문에 (1) 명료화 질문을 하거나, (2) 넓은 범위를 탐색하며 수십 개 파일을 읽은 뒤 광범위한 분석을 출력한다. 사용자가 "아 그게 아니라..."로 정정하면 왕복이 발생한다. 공식 문서("Vague prompts generate expensive sessions — Claude reads numerous files and generates sprawling analyses before producing useful output")가 직접 경고.

**자각 신호(tell)**
- Claude가 "어떤 파일을 보면 될까요?" 또는 "조금 더 구체적으로..." 등 되묻는다
- Claude의 첫 응답이 2~3개 파일에 걸친 장문 분석이다
- 응답 후 "아 그게 아니라"를 타이핑하게 된다

**고치는 습관(fix)**

Before:
```
"성능 개선해줘"
```

After (공식 문서 권장 패턴):
```
"src/api/search.ts의 쿼리 함수 성능이 느려. 
N+1 문제가 의심됨. 해당 함수만 확인하고, 
수정 후 기존 테스트 통과 여부 검증해줘."
```

- 파일 경로를 `@` 참조로 직접 지정 (`@src/api/search.ts`)
- 증상·위치·완료 기준을 한 번에 명시
- 검증 조건(테스트 통과)까지 포함하면 왕복 0회

**절감 추정**: 왕복 1~3회 제거 → 프롬프트당 500~2,000 토큰 절감 (정량). 광범위 파일 탐색 차단으로 도구 호출 비용 추가 절감.

---

### A2. 무제한 탐색 (범위 없는 분석 요청)

**패턴 ID**: A2 | **이름**: 무제한 탐색

**무의식 시나리오**
```
"이 코드베이스 분석해줘"
"우리 인증 시스템 어떻게 돼 있어?"
```

**왜 토큰이 새는가**
범위 미지정 탐색은 Claude가 수십~수백 개 파일을 순차 Read한다. 파일 1개 읽기당 수백 토큰 소모, 파일 내용이 컨텍스트에 누적된다. 공식 문서: "The infinite exploration — you ask Claude to 'investigate' something without scoping it. Claude reads hundreds of files, filling the context."

**자각 신호(tell)**
- Claude가 "파일 구조를 먼저 파악하겠습니다"라며 ls/find를 수차례 실행
- 응답에 "src/X.ts, src/Y.ts, src/Z.ts를 확인했습니다..."가 10개 이상 나열
- 응답 자체가 장문 요약 보고서

**고치는 습관(fix)**

Before:
```
"인증 시스템 분석해줘"
```

After:
```
"@src/auth/ 디렉토리의 session.ts와 tokenRefresh.ts만 읽고, 
토큰 갱신 플로우를 3줄로 요약해줘."
```

- 추가 고급 기법: `"subagent를 써서 인증 시스템 탐색해줘"` — 서브에이전트가 별도 컨텍스트 창에서 탐색하고 요약만 메인으로 반환 (공식: "Use subagents for investigation. They explore in a separate context, keeping your main conversation clean")
- 탐색 범위를 디렉토리 1~2개 + 파일 1~3개로 명시 제한

**절감 추정**: 서브에이전트 사용 시 메인 컨텍스트에서 파일 읽기 비용 100% 차단. 범위 지정만으로도 읽는 파일 수 80% 감소 (정성).

---

### A3. 분할 요구 결핍 (한 번에 명세 안 줌 → 다회 왕복)

**패턴 ID**: A3 | **이름**: 분할 요구 결핍

**무의식 시나리오**
```
[1회] "로그인 페이지 만들어줘"
[2회] "아 소셜 로그인도 넣어야 해"
[3회] "폼 검증도 추가해줘"
[4회] "에러 메시지 스타일도 맞춰줘"
```

**왜 토큰이 새는가**
각 후속 요청마다 이전 대화 전체(점점 늘어나는 컨텍스트)를 재처리하며 응답한다. 4회 왕복 시 1회차 대비 컨텍스트 누적량이 3~5배. 또한 각 왕복마다 Claude가 이미 생성한 코드를 다시 읽고 이해하는 비용이 발생한다.

**자각 신호(tell)**
- 하나의 기능 구현에 동일 세션 내 4회 이상 추가 요청
- "아 그리고..." "하나만 더..." 패턴이 반복
- 대화 히스토리가 계속 길어지는데 여전히 같은 파일을 수정 중

**고치는 습관(fix)**

Before: 위 시나리오처럼 4번 나눠 요청

After (공식 권장 인터뷰 패턴 활용):
```
"로그인 페이지를 만들기 전에 
AskUserQuestion 도구로 나를 인터뷰해줘. 
필요한 기능, UI, 검증 로직, 소셜 로그인, 
에러 처리 등을 다 물어보고 SPEC.md를 써줘."
```
또는 직접 일괄 명세:
```
"로그인 페이지 구현. 요구사항:
1. 이메일/비밀번호 폼 (검증 포함)
2. Google OAuth 소셜 로그인
3. 에러 메시지: design-system의 ErrorMessage 컴포넌트 사용
4. @src/auth/existing-pattern.ts 패턴 따를 것
완료 후 테스트 실행해줘."
```

**절감 추정**: 4회 왕복 → 1회 단축 시 컨텍스트 누적 70~80% 감소 (정량적 추정). SPEC.md를 새 세션에서 소비하면 히스토리 오염 0.

---

### A4. 장황 출력 유도 (원하는 것보다 많은 응답 요청)

**패턴 ID**: A4 | **이름**: 장황 출력 유도

**무의식 시나리오**
```
"이 함수 설명해줘" → Claude가 배경·맥락·예시·주의사항까지 500줄 출력
"이거 왜 이렇게 돼 있어?" → 히스토리 분석 + 대안 설명 포함 장문
```
→ 사용자는 첫 2~3줄만 실제로 읽음

**왜 토큰이 새는가**
Claude의 기본 출력은 verbose하다. 요청이 "설명해줘"처럼 열려 있으면 Claude는 배경·원리·예시·경고·대안을 모두 포함한다. 출력 토큰은 입력 토큰보다 비싸며, 이 출력이 다시 다음 턴의 컨텍스트로 누적된다. 공식 문서: "Requesting unnecessary explanations — you can suppress this with directives. The difference can represent 40-60% of token usage."

**자각 신호(tell)**
- 응답이 스크롤을 내려야 할 만큼 길지만 첫 단락만 읽고 넘어감
- "요약만 해줘"를 요청 후에 하게 됨 (이미 생성된 후)
- 응답에 "참고로...", "추가적으로...", "한편..." 단락이 3개 이상

**고치는 습관(fix)**

Before:
```
"이 함수 설명해줘"
```

After:
```
"이 함수 목적을 2줄로만. 코드·예시 없이."
```

CLAUDE.md에 영속 지시 추가 (한 번만 설정):
```markdown
# 출력 기본값
- 코드 설명: 3줄 이하. 추가 요청 시에만 확장.
- 분석 보고: 핵심 포인트 불릿 3개 이하.
- 불필요한 서론·배경 생략.
```

또는 `/btw` 활용: 간단한 궁금증은 `/btw 이 함수 뭐 하는 거야?` — 답변이 컨텍스트에 추가되지 않음 (dismissible overlay, 공식 확인).

**절감 추정**: 응답 토큰 40~60% 감소 (MindStudio 자료 기반). CLAUDE.md 설정 1회로 모든 세션에 영속 적용.

---

## B. 재작업 루프 계열

---

### B1. 전체 재생성 요청 (부분 수정이면 될 걸 처음부터)

**패턴 ID**: B1 | **이름**: 전체 재생성 요청

**무의식 시나리오**
```
"이거 다시 짜줘 — 변수명을 더 명확하게"
"처음부터 다시 해줘, 에러 처리 빠진 것 같아"
```

**왜 토큰이 새는가**
Claude는 기존 코드를 다시 읽고 전체를 재출력한다. 200줄 파일이면 200줄 재생성. 실제 변경은 10줄인데도. 재출력된 코드가 다시 컨텍스트에 쌓인다. 공식 문서: "Re-requesting reformatted content means Claude regenerates content it already produced, doubling the token cost."

**자각 신호(tell)**
- 응답이 전체 파일·함수를 코드블록으로 다시 출력
- 변경점이 실제로는 5% 미만인데 100% 재출력
- 직전 응답과 새 응답을 diff해보면 수정 부분이 극히 적음

**고치는 습관(fix)**

Before:
```
"이 코드 다시 써줘, 에러 처리 추가해서"
```

After:
```
"위 코드에서 API 호출 부분(35~42줄)에만 
try/catch 추가해줘. 나머지는 그대로."
```

또는 공식 Edit 도구 활용 유도:
```
"@src/api.ts 파일의 fetchUser 함수에만 
에러 처리 추가. 파일 전체 재출력 하지 마."
```

코드 리뷰/디버깅 시: "diff만 보여줘" 또는 "변경된 줄만 알려줘" 명시.

**절감 추정**: 100줄 파일 기준 90% 출력 토큰 절감. 파일 재독 비용 제거.

---

### B2. 반복 검증 요청 (정말 맞아? 다시 확인해)

**패턴 ID**: B2 | **이름**: 반복 검증 요청

**무의식 시나리오**
```
[Claude 구현 후]
"정말 맞아?"
"한번 더 확인해줘"
"혹시 엣지케이스 빠진 거 없어?"
```

**왜 토큰이 새는가**
Claude는 각 검증 요청마다 자신이 작성한 코드를 다시 읽고 분석한다. 3회 반복이면 동일 코드를 3번 추가 처리. 더 심각한 문제: Claude는 자신이 구현한 코드를 검증할 때 확증 편향이 있어 검증 효과도 낮다. 공식 문서: "The reviewer running in a fresh subagent context sees only the diff and the criteria you give it, not the reasoning that produced the change — so it evaluates the result on its own terms."

**자각 신호(tell)**
- "정말?", "확실해?", "다시 봐줘" 패턴이 구현 후 연속 발생
- Claude가 "네, 맞습니다" → "아 잠깐, 이 부분..." 패턴을 반복
- 같은 세션 내에서 동일 코드에 대한 검증이 3회 이상

**고치는 습관(fix)**

Before: 구현 후 "정말 맞아?" 반복

After 방법 1 — 구현 요청 시 검증 조건을 미리 포함:
```
"fetchUser 구현 후 기존 테스트 실행하고 
결과 보여줘. 테스트 통과 시 완료."
```

After 방법 2 — 서브에이전트 코드 리뷰:
```
"서브에이전트로 방금 작성한 코드의 
엣지케이스를 검토해줘. 
정확성에 영향 있는 것만 보고해."
```

또는 `/code-review` 슬래시 커맨드 사용 (공식 번들 skill — 현재 diff를 신선한 서브에이전트로 검토).

**절감 추정**: 반복 검증 3회 → 1회(자동화된 검증)로 대체. 검증 품질도 향상. 왕복 2회 × 코드 재독 비용 제거.

---

### B3. 교정 누적 루프 (같은 문제를 계속 수정)

**패턴 ID**: B3 | **이름**: 교정 누적 루프

**무의식 시나리오**
```
[1회 수정] "이거 타입 에러 고쳐줘" → 고침
[2회 수정] "아직도 에러 나" → 다시 고침
[3회 수정] "여전히 안 돼" → 다시 고침
```
(컨텍스트에 실패한 시도들이 누적)

**왜 토큰이 새는가**
실패한 접근법들이 대화 히스토리에 쌓이면서 Claude가 이전 실패를 회피하느라 추가 추론을 하고, 새로운 시도도 오염된 컨텍스트의 영향을 받는다. 공식 문서: "If you've corrected Claude more than twice on the same issue in one session, the context is cluttered with failed approaches. Run `/clear` and start fresh with a more specific prompt that incorporates what you learned."

**자각 신호(tell)**
- 동일 파일/기능에 대해 "아직 안 돼", "여전히 에러"가 2회 이상
- Claude가 이전에 실패한 접근법을 또 시도함
- 대화에 "아까 이렇게 했는데", "다시 원래대로" 패턴

**고치는 습관(fix)**

2회 교정 후 자동 반응:
1. `Esc+Esc` 또는 `/rewind`로 실패 전 체크포인트 복원
2. `/clear`로 컨텍스트 리셋
3. 실패에서 배운 정보를 포함해 더 구체적인 프롬프트로 재시작:

```
"TypeScript strict 모드에서 UserDTO의 
optional 필드 처리 시 타입 에러. 
기존 패턴은 @src/types/BaseDTO.ts 참조. 
undefined 처리 방식을 동일하게 적용해줘."
```

CLAUDE.md에 추가 가능:
```markdown
# 디버깅 규칙
- 같은 문제 2회 실패 시 /clear 후 재시작
```

**절감 추정**: 누적 실패 컨텍스트 제거로 신선한 시작. 3회 실패 루프 대비 전체 토큰 60% 절감 추정.

---

## C. 영속화 미활용 계열

---

### C1. 맥락 재타이핑 (매 세션 같은 지시 반복)

**패턴 ID**: C1 | **이름**: 맥락 재타이핑

**무의식 시나리오**
```
[매일 세션 시작 시]
"이 프로젝트는 Next.js 15, TypeScript strict,
Tailwind CSS를 쓰고, 컴포넌트는 
src/components에, 스타일은 globals.css에..."
```

**왜 토큰이 새는가**
CLAUDE.md는 모든 세션 시작 시 자동 로드된다. 이를 활용하지 않고 매번 동일 맥락을 타이핑하면: (1) 사용자의 타이핑 시간 낭비, (2) 이 반복 입력이 컨텍스트 앞부분을 차지해 실제 작업 공간 감소, (3) 세션마다 손으로 타이핑하면 일관성도 낮아짐. 공식: "CLAUDE.md is a special file that Claude reads at the start of every conversation. Include Bash commands, code style, and workflow rules. This gives Claude persistent context it can't infer from code alone."

**자각 신호(tell)**
- 세션 첫 번째 메시지가 항상 프로젝트 설명으로 시작
- "아까도 말했지만...", "이전에 얘기한 것처럼..." 표현
- 동일 스택·규칙 설명을 3회 이상 반복

**고치는 습관(fix)**

`/init` 실행 → 생성된 CLAUDE.md에 반복 입력하던 내용 추가:
```markdown
# 프로젝트 스택
- Next.js 15, TypeScript strict, Tailwind CSS
- 컴포넌트: src/components/ (단일 책임 원칙)
- 스타일: Tailwind 클래스 우선, globals.css 최소화

# 코드 스타일
- ES modules (import/export), CommonJS 금지
- 함수 컴포넌트, hooks 전용

# 워크플로우
- 수정 후 항상 타입체크 실행
- 테스트: 개별 테스트 우선, 전체 suite 지양
```

반복 작업 패턴은 skill(.claude/skills/)로 추가 영속화 가능.

**절감 추정**: 세션당 맥락 재타이핑 100~300 토큰 × 일 3~5 세션 = 주당 1,500~7,500 토큰 완전 제거 (정량적으로 계산 가능한 낭비).

---

### C2. 커스텀 명령 미활용 (반복 작업을 매번 장문으로)

**패턴 ID**: C2 | **이름**: 커스텀 명령 미활용

**무의식 시나리오**
```
[매번 PR 만들 때]
"변경사항 확인하고, 테스트 실행하고,
린트 통과 확인하고, 커밋 메시지 컨벤션
확인해서 PR 만들어줘. 우리 컨벤션은..."
[위를 매번 타이핑]
```

**왜 토큰이 새는가**
반복 워크플로우를 매번 장문으로 타이핑하면 (1) 입력 토큰 낭비, (2) 지시가 매번 조금씩 달라 일관성 저하, (3) 빠진 단계가 생겨 재요청 발생. 공식 Skill 기능을 쓰면 `/create-pr`처럼 단 하나의 명령으로 모든 단계를 실행 가능.

**자각 신호(tell)**
- 같은 작업 절차를 세션마다 장문으로 타이핑
- "우리 컨벤션은 이렇게..." 설명을 매번 붙임
- 단계 하나를 빠뜨려 "아 그리고 린트도..." 추가 요청

**고치는 습관(fix)**

`.claude/skills/create-pr/SKILL.md` 생성:
```markdown
---
name: create-pr
description: 변경사항 검증 후 PR 생성
disable-model-invocation: true
---
1. git diff로 변경사항 확인
2. npm test 실행 — 실패 시 중단 후 보고
3. npm run lint 실행 — 실패 시 중단
4. 커밋 메시지: feat/fix/docs/refactor: 설명 (50자 이하)
5. gh pr create로 PR 생성 (본문: What/Why/Test)
```

이후 매번: `/create-pr` 한 줄로 완료.

`/init`으로 시작, 반복 패턴 발견 시 즉시 skill로 추출하는 습관.

**절감 추정**: 반복 워크플로우 장문(100~300 토큰) → 1줄 명령어. 일관성 향상으로 재요청 방지.

---

### C3. 출력 휘발 (결과를 파일로 안 받아 매 턴 재노출)

**패턴 ID**: C3 | **이름**: 출력 휘발

**무의식 시나리오**
```
"이 코드베이스 구조 분석해줘" → Claude가 장문 분석 출력
[다음 턴] "아까 분석한 내용 기반으로 리팩토링 계획 세워줘"
→ Claude가 이전 분석을 다시 참조하며 컨텍스트에 재노출
```

또는:
```
"스펙 작성해줘" → 출력 확인 후 그냥 넘어감
[다음 세션] "저번에 만든 스펙 기반으로..."
→ 스펙이 없어서 다시 만들어야 함
```

**왜 토큰이 새는가**
분석·계획·스펙 등 중간 산출물을 파일로 저장하지 않으면: (1) 같은 세션 내 재참조 시 컨텍스트에 이미 있는 내용을 다시 생성하는 낭비, (2) 새 세션에서 다시 생성해야 함. 공식 문서가 SPEC.md 패턴을 명시적으로 권장: "Once the spec is complete, start a fresh session to execute it. The new session has clean context focused entirely on implementation."

**자각 신호(tell)**
- Claude의 분석/계획 결과가 대화창에만 있고 파일 없음
- "아까 말한 대로", "방금 분석한 것처럼"으로 이전 출력 재참조
- 새 세션에서 "저번에..." → 결과물 없어서 재작업

**고치는 습관(fix)**

Before: 분석 결과를 그냥 읽고 다음 메시지로 넘어감

After:
```
"인증 시스템 분석해서 ANALYSIS.md로 저장해줘."
"리팩토링 계획을 PLAN.md에 써줘."
"스펙 완성되면 SPEC.md 저장하고, 
새 세션에서 이걸 기반으로 구현할게."
```

규칙화: 모든 중간 산출물(분석·계획·스펙·결정)은 파일로 저장. 새 세션은 파일을 `@` 참조로 소비.

**절감 추정**: 중간 산출물 재생성 방지. 세션 간 산출물 공유로 동일 작업 반복 제거.

---

## D. 컨텍스트 오염 계열

---

### D1. 메인 스레드 탐색 (서브에이전트가 나은 조사를 메인에서)

**패턴 ID**: D1 | **이름**: 메인 스레드 탐색

**무의식 시나리오**
```
[구현 중인 메인 세션에서]
"아 잠깐, 기존 코드에서 OAuth 처리를 
어떻게 했는지 찾아봐줘"
→ Claude가 메인 컨텍스트에서 20개 파일 탐색
```

**왜 토큰이 새는가**
메인 세션에서 파일 탐색을 하면 탐색한 모든 파일 내용이 메인 컨텍스트에 쌓인다. 탐색 목적이 달성된 후에도 그 파일들은 컨텍스트에 남아 이후 모든 턴의 처리 비용을 높인다. 서브에이전트는 별도 컨텍스트 창에서 실행되어 요약만 메인으로 반환. 공식: "Subagents run in separate context windows and report back summaries — without cluttering your main conversation."

**자각 신호(tell)**
- 메인 세션에서 "파일 구조 파악하겠습니다"가 구현 중간에 등장
- 컨텍스트 사용률 표시가 탐색 후 급증
- 탐색용 파일 내용이 이후 응답에도 계속 재참조됨

**고치는 습관(fix)**

Before:
```
"OAuth 기존 구현 찾아봐줘" (메인 세션에서)
```

After:
```
"서브에이전트로 src/auth/ 디렉토리에서 
OAuth 관련 유틸 함수 찾아서 
함수명·위치만 요약해줘."
```

또는 간단한 확인은 `/btw` 사용 (공식 기능, 컨텍스트에 추가 안 됨):
```
/btw 아까 읽은 auth 코드에서 토큰 갱신 함수 이름이 뭐였어?
```
(이미 컨텍스트에 있는 정보 질문 시 — `/btw`는 도구 없이 기존 컨텍스트만 참조)

**절감 추정**: 탐색 파일들이 메인 컨텍스트에서 제거. 서브에이전트 사용 시 탐색 비용이 별도 컨텍스트로 격리.

---

### D2. 주방 싱크 세션 (무관한 작업을 한 세션에 혼재)

**패턴 ID**: D2 | **이름**: 주방 싱크 세션

**무의식 시나리오**
```
[세션 시작] "로그인 버그 고쳐줘"
[중간] "아 참, 새 기능 아이디어 있어, 들어봐줘"
[이후] "방금 말한 기능 설계해줘"
[계속] "다시 로그인 버그로 돌아가서..."
```

**왜 토큰이 새는가**
무관한 작업들이 한 세션에 섞이면 (1) 작업 A의 파일들이 작업 B를 처리할 때도 컨텍스트 공간을 점유, (2) Claude가 무관한 히스토리를 참조하며 혼선 발생, (3) 컨텍스트가 임계에 근접할 때 auto-compact 시 중요 정보 손실 위험. 공식: "The kitchen sink session — context is full of irrelevant information. Fix: `/clear` between unrelated tasks."

**자각 신호(tell)**
- 한 세션에서 토픽이 2회 이상 전환
- "다시 처음 얘기로 돌아가서..."
- `/context` 보면 여러 작업의 파일들이 혼재

**고치는 습관(fix)**

- 작업 전환 시 `/clear` 실행 → 컨텍스트 완전 리셋
- 또는 `claude --resume`으로 작업별 세션 분리 유지
- `/rename`으로 세션 이름 지정 (`oauth-bug`, `new-feature-spec`) → 나중에 `/resume`으로 복귀 가능
- CLAUDE.md에 규칙 추가: 새로운 독립 작업은 항상 새 세션

**절감 추정**: 무관 컨텍스트 제거로 각 작업당 처리 토큰 20~40% 절감. Claude 응답 품질도 향상 (무관 히스토리 없으므로).

---

### D3. 과한 Thinking 유도 (사소한 작업에 장문 추론 유발)

**패턴 ID**: D3 | **이름**: 과한 Thinking 유도

**무의식 시나리오**
```
"변수명 바꾸는 게 맞을까? 
아키텍처 관점에서 깊이 분석해줘"
"이 함수 이름이 맞는지 철학적으로 생각해봐"
"가장 완벽한 방법을 모든 측면에서 검토해줘"
```

**왜 토큰이 새는가**
"깊이 분석", "모든 측면", "완벽한" 같은 표현은 Claude에게 extended thinking 또는 장문 추론 응답을 유도한다. 변수명 변경처럼 단순한 작업에 500~1000 토큰의 추론을 소모하는 비대칭이 발생한다. 반대로 단순 작업에는 `Option+T`(macOS) / `Alt+T`(Windows)로 extended thinking을 명시적으로 비활성화 가능 (공식 확인).

**자각 신호(tell)**
- 응답 앞에 장문의 "생각해보면...", "여러 관점에서..." 도입부
- 단순 결정에 대한 응답이 스크롤 3회 이상 필요
- "최선의 방법", "완벽한 솔루션" 표현 사용 후 과한 응답

**고치는 습관(fix)**

Before:
```
"가장 완벽한 변수명을 아키텍처 관점에서 분석해줘"
```

After:
```
"userCount vs userTotal — 둘 중 더 명확한 걸 골라줘. 
이유 1줄만."
```

규칙: 작업 복잡도 분류
- 단순 결정(이름·포맷·스타일): 1줄 응답 요청, Thinking 비활성화
- 복잡 설계(아키텍처·알고리즘): plan mode + Thinking 활성화 허용

공식 fast mode(`Option+O`)도 활용 가능 — 빠른 응답이 필요한 단순 작업에.

**절감 추정**: 단순 작업의 추론 비용 70~90% 감소. 작업 복잡도에 비례한 토큰 사용으로 전환.

---

## 임팩트 요약 (Top 3)

| 순위 | 패턴 | 왜 임팩트가 큰가 | 절감 크기 |
|------|------|-----------------|----------|
| 1 | **C1. 맥락 재타이핑** | 매 세션마다 발생, CLAUDE.md 한 번 설정으로 영구 해결 | 정량적 · 즉시 |
| 2 | **A2. 무제한 탐색** | 파일 탐색 시 수십~수백 파일 읽기 → 컨텍스트 폭증 | 최대 규모 단일 이벤트 |
| 3 | **A4. 장황 출력 유도** | 응답 토큰 40~60% 차지, 누적 시 전체 세션 비용 직결 | 빈도 높음 · 누적 효과 큼 |

---

## 참고 — 검증 출처

- [Claude Code Best Practices](https://code.claude.com/docs/en/best-practices) (공식)
- [Claude Code Interactive Mode — /btw](https://code.claude.com/docs/en/interactive-mode) (공식)
- [Claude Code Context Management](https://claudefa.st/blog/guide/mechanics/context-management)
- [MindStudio: Token Management Hacks](https://www.mindstudio.ai/blog/claude-code-token-management-hacks)
- [MindStudio: Token Usage Techniques](https://www.mindstudio.ai/blog/how-to-manage-claude-code-token-usage)
