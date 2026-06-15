# tokenhabit — 런치 포스트 초안

> 발견성용. 복붙해서 올린 뒤, 첫 댓글에 데모/링크 보강. 톤: 자랑 아닌 "내 로그를 까보니" 1인칭.

---

## A. Hacker News — Show HN

**Title (80자 제한, 클릭 유도형):**
```
Show HN: tokenhabit – scan your Claude Code logs for token-wasting habits
```

**Body:**
```
I use Claude Code a lot, and ccusage told me *how much* I was spending —
but never *why*. So I scanned my own ~/.claude/projects/*.jsonl logs and
found the patterns that quietly burn tokens: re-reading the same file,
dumping full build logs into context, dragging three topics through one
session without /clear, switching models mid-session (cache miss), etc.

tokenhabit parses those logs locally and gives you a "Token Waste Score"
plus ranked habits, each with a copy-paste fix. No LLM calls, no
dependencies, runs offline — it only reads your own logs and sends nothing.

    uvx tokenhabit          # or: pip install tokenhabit

It auto-detects 10 of a 28-pattern habit catalog (the rest are config/prompt
habits you can't judge from logs alone — those live in a companion Claude
Code skill). Frequency-only signals like "subagent overuse" are shown but
deliberately kept out of the score so it doesn't overstate waste.

On my own logs it flagged ~14% of billable tokens as habitually wasted,
dominated by compaction overrun and topic drift.

Repo: https://github.com/epoko77-ai/tokenhabit
PyPI: https://pypi.org/project/tokenhabit/

Curious what habit dominates other people's logs — would love feedback on
the detection heuristics.
```

**첫 댓글(작성자 보강용):** 점수 계산 방식(분모 = billable = input+output+cache_creation, cache_read 제외)과 "추정치이지 청구서가 아니다" 한 줄 + 데모 출력 캡처.

---

## B. Reddit — r/ClaudeAI (또는 r/ClaudeCode)

**Title:**
```
I scanned my Claude Code logs — turns out I was habitually wasting ~14% of my tokens. Made a tool to find the leaks.
```

**Body (마크다운):**
```
ccusage shows you *how much* you spent. I wanted to know *which habits* spent
it — so I wrote a small CLI that reads your local `~/.claude/projects/*.jsonl`
logs and diagnoses the token-wasting patterns.

**What it found in my own logs:**
- **Compaction overrun** — letting context pile past ~50K before /compact
- **Topic drift** — three unrelated tasks in one session, no /clear
- **Cache-kill** — switching model/effort mid-session (full re-bill of the prefix)
- **Re-reading the same file**, **dumping full logs into context**, …

Each detected habit comes with a **copy-paste fix**, and there's a shareable
**Token Waste Score** (A–F).

**Try it (no install):**

    uvx tokenhabit
    uvx tokenhabit --lang ko   # 한국어 리포트도 됩니다

- No LLM calls, no dependencies, fully offline — it only reads your own logs.
- Auto-detects 10 patterns; a companion Claude Code *skill* covers the full
  28-pattern catalog (prompt clarity, CLAUDE.md hygiene, MCP setup, …).
- Honest by design: "subagent overuse" / "web fetch" are shown as frequency
  signals but kept *out* of the score, since they're often legitimate.

Repo: https://github.com/epoko77-ai/tokenhabit

What's the #1 habit it flags for you? Genuinely curious how the distribution
looks across heavier users.
```

---

## C. 한국어 커뮤니티 (GeekNews / 디스코드 / 클로드 한국 채널)

**제목:**
```
내 Claude Code 로그를 까봤더니 토큰의 ~14%를 습관적으로 낭비하고 있었다 (오픈소스 CLI)
```

**본문:**
```
ccusage가 "얼마 썼나"를 알려준다면, 저는 "어떤 습관이 그걸 썼나"가 궁금했습니다.
그래서 로컬 ~/.claude/projects/*.jsonl 로그를 파싱해 토큰 낭비 습관을 진단하는
작은 CLI를 만들었습니다.

  uvx tokenhabit --lang ko

- LLM 호출 0회, 의존성 0개, 완전 오프라인 (내 로그만 읽고 아무것도 전송 안 함)
- 토큰 낭비 점수(A~F) + 습관별 순위 + 복붙 가능한 즉시 fix
- 로그에서 자동 감지 10개 + 전체 28패턴 카탈로그는 Claude Code 스킬로 제공
- 정직성: 서브에이전트·웹툴 호출은 정상 사용이 많아 '빈도 신호'로만 표시하고
  점수에는 합산하지 않음 (낭비 과장 방지)

제 로그에선 compaction 적체와 주제 드래그가 1·2위였습니다.

GitHub: https://github.com/epoko77-ai/tokenhabit
PyPI: https://pypi.org/project/tokenhabit/
```

---

## 올리기 전 체크리스트
- [ ] README 최상단에 데모 GIF/asciinema (이게 있으면 전환율이 크게 오름)
- [ ] GitHub Release v1.2.0 태그 (릴리스 페이지가 있으면 신뢰도↑)
- [ ] HN은 화요일~목요일 오전(미 동부) 트래픽이 높음
- [ ] 첫 댓글에 "점수는 추정치" 디스클레이머 + ccusage와의 보완 관계 명시
- [ ] 비판 대응 준비: "휴리스틱이 거칠다" → 맞음, 트렌드용. PR 환영 톤 유지
