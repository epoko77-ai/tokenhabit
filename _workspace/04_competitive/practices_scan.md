# tokenhabit 베스트프랙티스 스캔 보고서

> 작성일: 2026-06-03  
> 목적: tokenhabit 스킬 보완을 위한 외부 지식 발굴  
> 조사 범위: Anthropic 공식 문서, context rot 연구, 측정 도구, hook 사례

---

## 섹션 1 — Anthropic 공식 Best Practices 대조

### 출처
- **공식 문서** (신뢰도: 최고, 2026-06 최신): https://code.claude.com/docs/en/best-practices
- **공식 비용 관리** (신뢰도: 최고): https://code.claude.com/docs/en/costs
- **공식 hooks 레퍼런스** (신뢰도: 최고): https://code.claude.com/docs/en/hooks

### 핵심 발견 1: 공식 문서가 명시한 "실패 패턴 5개" 중 tokenhabit 미반영 항목

공식 best-practices 페이지는 "common failure patterns" 섹션에서 5개 실패 유형을 나열한다. tokenhabit의 24패턴과 대조 결과:

| 공식 실패 패턴 | tokenhabit 반영 여부 | 비고 |
|---|---|---|
| Kitchen sink session (무관 작업 혼재) | H1-04 반영 | 동일 개념 |
| Correcting over and over (실패 루프) | H1-02 반영 | 동일 |
| Over-specified CLAUDE.md | H3-01 반영 | 동일 |
| Trust-then-verify gap (검증 누락) | H6-02로 부분 반영 | **공식은 더 강조**: "Always provide verification" — 구현 시 검증 기준을 미리 포함하는 습관 |
| **Infinite exploration (범위 없는 탐색)** | H5-02 반영 | 공식이 추가한 fix: "scope narrowly or use subagents" → tokenhabit에 이미 있음 |

**보완 포인트:** 공식은 "교정을 2회 이상 한 뒤 `/clear` 후 더 나은 프롬프트로 재시작"을 단호하게 권고한다. tokenhabit의 H1-02 "2회 실패 시 `/compact` 제안"과 방향이 같지만, 공식은 `/compact`보다 **`/clear` + 재작성**을 더 강조함. H1-02 고치는습관에 "2회 실패 → `/clear` 후 새 프롬프트"를 `/compact`와 병렬로 추가 권장.

### 핵심 발견 2: 공식 문서에 있지만 tokenhabit 미포함인 패턴

**A. `.claudeignore` 파일 활용**
- **출처**: https://code.claude.com/docs/en/costs (비용 절감 섹션), 커뮤니티 검증
- **내용**: `.gitignore`와 동일 문법으로 `node_modules/`, `dist/`, `.next/`, `*.lock` 등을 Claude 자동 탐색에서 제외. `.next/` 하나만 추가해도 Next.js 프로젝트 컨텍스트 30~40% 절감.
- **중요 한계(2026-03-16 현재)**: 명시적으로 Read 요청하면 bypass 가능 — 자동 탐색 필터이지 완전 차단이 아님.
- **tokenhabit 반영 방안**: 새 패턴 **H9-01 `.claudeignore` 미설정** 으로 추가. H2-01(파일 재탕)의 사전 예방책으로 묶는다. 카테고리 H9 "프로젝트 설정 미비"를 신설하거나 H3-01(과비대 CLAUDE.md) 고치는습관에 합산.

**B. Plan Mode(Shift+Tab)의 토큰 절감 관점**
- **출처**: 공식 best-practices, claudefa.st/blog
- **내용**: Plan mode에서 Claude는 파일을 읽되 수정하지 않으므로, 탐색-계획 단계에서 output 토큰이 대폭 줄어든다. 공식 권고: "For small, clear tasks skip plan. For multi-file changes use plan mode first."
- **tokenhabit 현황**: H5-02 "무제한 탐색 요청"의 fix에 서브에이전트만 언급, plan mode 미언급.
- **반영 방안**: H5-02 고치는습관에 "plan mode(Shift+Tab)로 탐색-계획 분리, 파일 읽기는 plan mode에서 격리" 추가.

**C. `/rewind`의 4가지 복원 옵션 명시 부족**
- **출처**: 공식 best-practices + checkpointing 문서
- **내용**: `/rewind` (또는 Esc+Esc)는 단순 롤백이 아닌 4개 옵션 제공: (1) 대화만 복원, (2) 코드만 복원, (3) 둘다 복원, (4) 선택 지점에서 요약. 특히 "Summarize from here" / "Summarize up to here" 두 방향 요약이 partial compaction을 가능케 함.
- **tokenhabit 현황**: Q1 리뷰에서도 지적(MINOR). H1-02와 MODE 4 룰 #3에 4가지 옵션 미언급.
- **반영 방안**: H1-02 고치는습관 + MODE 4 룰 #3에 "Esc+Esc(/rewind) → 4가지 옵션 중 'Summarize from here' 선택 시 실패 이전까지만 압축" 명시.

**D. CLAUDE.md 자식 디렉토리 자동 로드 메커니즘**
- **출처**: 공식 best-practices (CLAUDE.md 섹션)
- **내용**: 자식 디렉토리에도 CLAUDE.md를 배치 가능하며 Claude가 해당 디렉토리의 파일을 읽을 때 온디맨드로 자동 로드. 즉, 모노레포에서 `apps/web/CLAUDE.md`는 web 작업 시에만 로드되어 상시 오버헤드 0.
- **tokenhabit 현황**: H3-01에 "CLAUDE.md 하나에 몽땅 넣는다"는 문제를 다루나, 자식 디렉토리 분산 배치를 해결책으로 언급하지 않음.
- **반영 방안**: H3-01 고치는습관에 "모노레포·멀티프로젝트는 자식 디렉토리 CLAUDE.md로 분산 — 미사용 도메인 지식 자동 격리" 추가.

**E. MCP tool schema 지연 로드(deferred by default) — 최신 변경**
- **출처**: 공식 costs 문서 (2026년 업데이트)
- **내용**: "MCP tool definitions are deferred by default, so only tool names enter context until Claude uses a specific tool." — 이전 tokenhabit H3-02에서 "Playwright ≈3,442 토큰"이라고 한 수치가 deferred 모드에서는 더 이상 적용되지 않을 수 있음.
- **반영 방안**: H3-02의 실측치 주석에 "(v2.x+ deferred mode에서는 tool 실제 호출 시점에만 schema 주입 — 상시 오버헤드 감소)" 추가. 절감 추정치 재검토 필요.

---

## 섹션 2 — Context Rot / Context Engineering 담론

### 출처
- **Chroma 연구** (신뢰도: 높음, 2025): https://www.trychroma.com/research/context-rot
- **Morph LLM 정리** (신뢰도: 높음): https://www.morphllm.com/context-rot
- **Redis 블로그** (신뢰도: 중간): https://redis.io/blog/context-rot/
- **Anthropic 공식 Engineering 블로그** (신뢰도: 최고): https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents

### 핵심 발견 3: Context Rot — 정량 임계치

Chroma의 2025 실험(18개 프론티어 모델 대상):
- **50K 토큰 이상부터 유의미한 성능 저하** 시작 — 200K 윈도우라도 50K에서 이미 rot.
- **Lost-in-the-middle 효과**: 중간 위치 정보 30%+ 정확도 하락.
- **35분 세션 임계**: 코딩 작업 35분 후 에이전트 성공률 급락. 일반적으로 80K~150K 토큰 누적 시점.
- **실패 루프 복리**: 작업 시간이 2배 늘면 실패율 4배 증가.

**tokenhabit 반영 방안:**
- H1-03 "compaction 버스 막차 타기"의 자각신호에 정량 기준 추가: "세션 50K 토큰 이상 또는 35분 이상 → 성능 저하 임계. `/context`에서 50% 미만이라도 compact 고려."
- H1-02 "실패 컨텍스트 적체"의 왜 새는가에 "lost-in-the-middle: 실패 시도가 컨텍스트 중간에 쌓이면 Claude가 더 이전의 성공 패턴을 놓침" 추가.

### 핵심 발견 4: Context Engineering 공식 원칙

Anthropic Engineering 블로그 ("Effective context engineering for AI agents"):
- 핵심 원칙: **"Smallest possible set of high-signal tokens"** — 압축보다 예방. 탐색 흔적 버리기, compact diff, 서브에이전트 격리.
- Anthropic 내부 다중에이전트 시스템이 단일 에이전트 대비 **90.2% 성능 향상** — 컨텍스트 격리가 품질에 직결.

**tokenhabit 반영 방안:**
- SKILL.md MODE 4 HABIT GUARD에 "고신호 토큰만 남기기" 원칙 추가. 현재 7개 룰에 "탐색 결과는 요약만, 원본 파일 내용은 메인 컨텍스트에 남기지 않는다" 강화.

---

## 섹션 3 — 프롬프트 효율 / 토큰 다이어트 — 24패턴 빠진 것

### 출처
- MindStudio 블로그 시리즈 (신뢰도: 중간): https://www.mindstudio.ai/blog/claude-code-token-management-hacks
- Build To Launch (신뢰도: 중간): https://buildtolaunch.substack.com/p/claude-code-token-optimization
- Analytics Vidhya (신뢰도: 중간): https://www.analyticsvidhya.com/blog/2026/05/tips-for-claude-code-token-saving/

### 핵심 발견 5: Code Intelligence Plugin — 파일 탐색 대체

- **내용**: typed language(TypeScript, Python 등)에 code intelligence plugin 설치 시, Claude가 grep+파일읽기 대신 "go to definition" 한 번으로 심볼 위치를 파악. 다중 후보 파일 읽기 제거.
- **tokenhabit 현황**: H5-02(무제한 탐색 요청)의 fix는 "서브에이전트"와 "plan mode"이나, code intelligence plugin은 미언급.
- **반영 방안**: H5-02 또는 H8-01 고치는습관에 "(TypeScript 등 typed 언어: code intelligence plugin 설치 → grep+파일읽기 → go-to-definition 대체)" 추가. 상세는 `tokensave` 설계 레이어이므로 힌트만.

### 핵심 발견 6: Skills로 CLAUDE.md 오프로드 (공식 강조)

- **출처**: 공식 costs 문서
- **핵심 문장**: "Skills load on-demand only when invoked, so moving specialized instructions into skills keeps your base context smaller."
- **tokenhabit 현황**: H3-01에 "Skill로 분리"를 언급하나, skill이 "온디맨드 로드 시 이름/설명만 ≈200 토큰"이라는 정확한 메커니즘은 있음. 그러나 "PR 리뷰, DB 마이그레이션 같은 워크플로우별 지시를 CLAUDE.md에 넣는 습관" 명시 부족.
- **반영 방안**: H7-02 "커스텀 명령 미활용"에 "반복 워크플로우 지시를 CLAUDE.md에 쓰는 것 = 상시 오버헤드" + "Skill로 이동 → 이름만 상주(≈100 토큰), 호출 시에만 전체 로드" 명시 강화.

### 핵심 발견 7: 에이전트 팀 비용 — 7배 승수

- **출처**: 공식 costs 문서
- **내용**: "Agent teams use approximately 7x more tokens than standard sessions when teammates run in plan mode." 각 teammate가 별도 컨텍스트 창 운영.
- **tokenhabit 현황**: H8-01 "메인 스레드 탐색"에서 서브에이전트 격리 비용을 "탐색 35K~50K vs 요약 3K 반환 → 90%+ 절감"으로 계산하나, 에이전트 팀 자체의 7배 비용 경고가 없음.
- **반영 방안**: H8-01 또는 별도 패턴으로 "에이전트 팀 과용" 추가. "서브에이전트는 탐색 격리에 효과적이지만 팀 전체 운영 시 7배 승수 — 팀은 소규모, 작업 집중, 완료 즉시 해산."

---

## 섹션 4 — 측정·정량화: JSONL 구조와 토큰 노출 방식

### 출처
- 공식 Agent SDK 비용 추적 문서 (신뢰도: 최고): https://code.claude.com/docs/en/agent-sdk/cost-tracking
- GitHub Issue #33978 (신뢰도: 높음): https://github.com/anthropics/claude-code/issues/33978
- ccusage (커뮤니티 검증): https://github.com/phuryn/claude-usage
- Shipyard 블로그 (신뢰도: 중간): https://shipyard.build/blog/claude-code-track-usage/
- ljw1004/claude-log (커뮤니티): https://github.com/ljw1004/claude-log

### JSONL 파일 위치 및 구조 (확정)

```
~/.claude/projects/<project-hash>/<session-id>.jsonl
```

- 각 줄 = 하나의 메시지 (user 또는 assistant)
- 서브에이전트 로그는 `subagents/` 하위 디렉토리 — ccusage는 최상위만 파싱(서브에이전트 별도 집계 필요)

**per-message usage 필드:**
```json
{
  "message": {
    "id": "msg_XXXX",
    "usage": {
      "input_tokens": 12345,
      "output_tokens": 678,
      "cache_creation_input_tokens": 9000,
      "cache_read_input_tokens": 3000
    }
  }
}
```

**주의사항:**
- 병렬 tool call 시 동일 `message.id`를 공유하는 여러 assistant message가 생성됨 → 중복 카운트 금지 (ID 기준 deduplicate)
- `total_cost_usd`는 클라이언트 추정치(bundled price table) — 공식 청구와 다를 수 있음
- 실제 청구는 https://platform.claude.com/usage 에서 확인

**추가 메타 필드:**
- `~/.claude/.credentials.json`: 구독 플랜, rate limit tier
- `~/.claude.json`: 추가 사용 상태
- 메시지별 `model` 필드: 어느 모델이 해당 턴을 처리했는지

### 기존 토큰 추적 도구 (자동 진단 스크립트 설계 참고)

| 도구 | 특징 | 상태 |
|---|---|---|
| **ccusage** (npm) | 일별/주별/세션별 리포트, Pro/Max 구독자 quota 추적 | 활성 |
| **ccost** (Rust) | 프로젝트·모델·서브에이전트 breakdown, HTML/CSV 출력 | 활성 |
| **Token Dashboard** | JSONL 파싱 → 7개 뷰(tool/file heatmap, cache analytics, 프로젝트 비교) | 활성 |
| **claude-usage (phuryn)** | 로컬 대시보드, 실시간 바 | 활성 |

### `/usage` 명령 (인터랙티브) — 현재 세션

```
/usage  →  Session block: 세션 총 비용, API 시간, 코드 변경량
           구독자 추가: 24h/7d 전환(d/w키), skill·subagent·MCP별 비율
```

**중요:** Max/Pro 구독자에게는 세션 비용 수치가 과금 기준이 아님(플랫 요금). quota 사용률이 실질 지표.

### `/context` 명령 — 컨텍스트 구성 분석

```
/context  →  system prompt / tools / memory files / skills / conversation history 별 토큰 비율
```

자동 진단 스크립트가 파악할 핵심 비율:
- Memory files > 3% → H3-01/H3-03 패턴 신호
- System tools > 10% → H3-02 패턴 신호
- Conversation history > 60% → H1-01/H1-02/H1-03 패턴 신호

### 자동 진단 스크립트 설계 힌트

tokenhabit "자동 진단 스크립트"를 만든다면:

**데이터 소스 1: JSONL 파싱**
```bash
# 오늘 세션들의 패턴 분석
ls ~/.claude/projects/*/*.jsonl | xargs grep -l "$(date +%Y-%m-%d)"
# 각 파일에서 usage 추출
cat session.jsonl | jq -r 'select(.message.usage) | [.message.id, .message.usage.input_tokens, .message.usage.output_tokens, .message.usage.cache_read_input_tokens] | @csv'
```

**데이터 소스 2: ccusage CLI**
```bash
npx ccusage@latest report daily  # 일별 집계
npx ccusage@latest report session --filter project=myapp
```

**감지 가능한 패턴 신호 (스크립트 자동화 가능):**
- 동일 파일명 반복 Read → H2-01 (JSONL에서 tool_name="Read", tool_input.file_path 중복 카운트)
- output/input 비율 급등 → H5-04 장황 출력 (output_tokens/input_tokens > 0.5)
- cache_read 비율 급락 → H4-03 캐시 킬 (캐시 히트율 갑자기 하락)
- 세션 30분 이상 & 전환 없음 → H1-01 주제 드래그 (타임스탬프 분석)
- 메시지 수 급증 & 유사 tool call 반복 → H6-02 반복 검증

**데이터 소스 3: statusline JSON (실시간 모니터링)**
```json
{
  "total_input_tokens": 45000,
  "total_output_tokens": 8000,
  "context_window_size": 200000,
  "used_percentage": 26.5,
  "current_usage": {
    "input_tokens": 1200,
    "output_tokens": 340,
    "cache_creation_input_tokens": 800,
    "cache_read_input_tokens": 9000
  }
}
```
→ `used_percentage` 50% 초과 시 compact 알림 트리거 가능.

---

## 섹션 5 — Hook으로 토큰 절감 강제: 실제 사례

### 출처
- 공식 Hooks 레퍼런스 (신뢰도: 최고): https://code.claude.com/docs/en/hooks
- 공식 costs 문서 PreToolUse 예시 (신뢰도: 최고)
- ClaudeLog 훅 가이드 (신뢰도: 높음): https://claudelog.com/mechanics/hooks/

### 핵심 발견 8: 공식 예시 — PreToolUse 테스트 출력 필터

공식 costs 문서에 명시된 예시 (tokenhabit H2-02/H8-02와 직결):

**settings.json:**
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "~/.claude/hooks/filter-test-output.sh"
          }
        ]
      }
    ]
  }
}
```

**filter-test-output.sh:**
```bash
#!/bin/bash
input=$(cat)
cmd=$(echo "$input" | jq -r '.tool_input.command')

if [[ "$cmd" =~ ^(npm test|pytest|go test) ]]; then
  filtered_cmd="$cmd 2>&1 | grep -A 5 -E '(FAIL|ERROR|error:)' | head -100"
  echo "{\"hookSpecificOutput\":{\"hookEventName\":\"PreToolUse\",\"permissionDecision\":\"allow\",\"updatedInput\":{\"command\":\"$filtered_cmd\"}}}"
else
  echo "{}"
fi
```

→ **tokenhabit 현황**: H2-02와 H8-02 "고치는습관"에 "PreToolUse 훅으로 grep 필터링" 언급은 있으나, 실제 설정 코드가 없음. "공식 docs filter-test-output.sh 예시"로만 언급.  
→ **반영 방안**: SKILL.md 또는 references에 위 코드를 실제 예시로 포함. 사용자가 복붙 가능한 수준으로.

### 핵심 발견 9: Hook 5가지 타입 — tokenhabit 미활용 타입

현재 tokenhabit은 PreToolUse command 훅만 언급. 공식 docs의 5가지 타입:
1. command (shell script) — 현재 언급
2. http (POST endpoint) — 미언급
3. mcp_tool — 미언급
4. **prompt (LLM 평가)** — **토큰 절감 역설: 훅 자체가 LLM 호출 → 남용 시 역효과**
5. **agent (서브에이전트 검증)** — 미언급

**반영 방안**: H2-02/H8-02의 "고치는습관"에 "(prompt/agent 타입 훅은 훅 자체가 LLM 호출 → 토큰 절감 목적에 역설. command 타입 shell 스크립트를 우선 사용)" 주의사항 추가.

### 핵심 발견 10: PostToolUse 출력 자동 10,000자 캡

공식 hooks 문서:
> "Hook output is capped at 10,000 characters automatically."

즉, PostToolUse로 Claude에게 반환되는 tool result도 10K자 상한이 있다. 이를 적극 활용하면 stdout 홍수(H8-02) 방지에 PostToolUse도 사용 가능.

**반영 방안**: H8-02 고치는습관에 "PostToolUse 훅으로 tool result 후처리 — 출력 10K자 자동 캡 + 추가 grep 필터로 에러만 추출" 추가.

---

## 섹션 6 — tokenhabit 현재 설명 vs 공식 문서 사실 검증

| tokenhabit 현재 설명 | 공식 문서 확인 | 판정 |
|---|---|---|
| "CLAUDE.md 200줄 미만 권고" | 공식 best-practices: "Keep it concise... under 200 lines" 명시 | 정확 |
| "MCP 상시 연결 시 고정 오버헤드" | 공식 costs: "deferred by default" — tool 실제 호출 시에만 schema 주입 | **부분 구식** — 수정 필요 |
| "자동 compaction 임계치 83.5%" | 공식: "approaching context limits" — 구체적 % 미공개 | 부정확 (Q1 리뷰 BLOCKER) |
| "H4-01 thinking 이중 과금" | 공식: output 1회 과금, 캐시 read 시 0.1x | 부정확 (Q1 리뷰 BLOCKER) |
| "PreToolUse 훅으로 로그 필터" | 공식 docs에 정확히 이 예시 있음 | 정확 (코드 추가 권장) |
| "/btw 답변이 컨텍스트에 추가 안 됨" | 공식 best-practices: "answer appears in a dismissible overlay and never enters conversation history" | 정확 (tool 제한 명시 필요) |
| "세션 50K 이상 성능 저하" | Chroma 연구 (공식 아님) | 외부 연구 결과, 공식 언급 없음 |
| "`claude --resume <name>`" | 공식: "claude --resume to choose from a list" + "/resume" 슬래시 커맨드 별도 존재 | 정확 (두 방법 모두 공식 확인) |

---

## 요약 테이블 — 보완 우선순위

| 우선순위 | 보완 항목 | 유형 | 연관 패턴 |
|---|---|---|---|
| P1 | MCP deferred load 반영 — H3-02 수치 업데이트 | 기술 수정 | H3-02 |
| P1 | `.claudeignore` 패턴 신설 또는 H3-01에 합산 | 신규 패턴 | 신규 H9-01 |
| P2 | Context rot 정량 임계(50K/35min) → H1-03 자각신호 추가 | 정량 강화 | H1-03 |
| P2 | Plan mode(Shift+Tab) → H5-02 fix에 추가 | fix 보강 | H5-02 |
| P2 | `/rewind` 4가지 옵션 → H1-02, MODE 4 룰 #3 명시 | 정확성 | H1-02 |
| P3 | Hook 실제 코드(filter-test-output.sh) 포함 | 실용성 | H2-02, H8-02 |
| P3 | 에이전트 팀 7배 토큰 경고 패턴 추가 | 신규 패턴 | 신규 H8-03 |
| P3 | CLAUDE.md 자식 디렉토리 분산 배치 → H3-01 fix 보강 | fix 보강 | H3-01 |

---

## 자동 진단 스크립트 — 데이터 소스 결론

**주 데이터 소스 (권장 순):**

1. **JSONL 파일** (`~/.claude/projects/*/*.jsonl`)
   - 필드: `message.id`, `message.usage.{input_tokens, output_tokens, cache_creation_input_tokens, cache_read_input_tokens}`, `message.model`, 타임스탬프
   - 파싱: `jq` or Python으로 충분. 100MB+ 파일은 seek-to-end 파싱 권장.
   - 주의: 병렬 tool call = 동일 ID → deduplicate 필수. 서브에이전트는 `subagents/` 하위 별도.

2. **ccusage** (오픈소스, npm)
   - `npx ccusage@latest report daily` — 즉시 사용 가능, JSONL 직접 파싱
   - 세션·프로젝트·모델별 breakdown 지원

3. **statusline JSON** (실시간)
   - `used_percentage`, `cache_read_input_tokens` → 실시간 compact 트리거 조건

4. **`/usage` + `/context`** (인터랙티브 세션 중)
   - `/context`: memory files/tools/conversation 비율 → 패턴 신호 즉시 파악
   - `/usage` `d`/`w` 키: 24h/7d 세션 기록

**측정 불가 영역:**
- 서브에이전트 내부 세션 토큰은 메인 JSONL에 미포함 → `subagents/` 하위 별도 파싱 필요
- 구독 플랜(Pro/Max)에서는 `/usage`의 세션 비용이 과금 기준 아님 — quota 사용률(`used_percentage`)이 실질 지표

---

*참고 URL 전체 목록:*
- 공식 Best Practices: https://code.claude.com/docs/en/best-practices
- 공식 비용 관리: https://code.claude.com/docs/en/costs  
- 공식 Hooks 레퍼런스: https://code.claude.com/docs/en/hooks
- Chroma Context Rot 연구: https://www.trychroma.com/research/context-rot
- Morph LLM Context Rot: https://www.morphllm.com/context-rot
- Anthropic Engineering 블로그: https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- ccusage GitHub: https://github.com/phuryn/claude-usage
- GitHub Issue JSONL 구조: https://github.com/anthropics/claude-code/issues/33978
- Shipyard 트래킹 가이드: https://shipyard.build/blog/claude-code-track-usage/
- Claude Code Agent SDK Cost Tracking: https://code.claude.com/docs/en/agent-sdk/cost-tracking
