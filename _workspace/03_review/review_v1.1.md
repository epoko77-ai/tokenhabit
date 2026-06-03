# tokenhabit v1.1 — Q1 감사 리뷰

> 감사 일시: 2026-06-03  
> 감사자: Q1 (리뷰어 에이전트)  
> 대상: A 정확성 패치(5건) + B 측정 어댑터(`habit_scan.py`) + C 강제 hook(`hook_check.py`) + `measurement_and_hooks.md`  
> 검증 방법: 공식 문서 WebSearch + 스크립트 직접 실행(self-test, edge payload, JSONL fixture)

---

## 종합 결과

| 종합 판정 | BLOCKER | MAJOR | MINOR |
|-----------|---------|-------|-------|
| **수정후PASS** | 1 | 4 | 4 |

---

## 축 1 — 기능명 실재성 (최우선)

### [축1][BLOCKER] habit_catalog.md:H3-04 — `.claudeignore`는 공식 Claude Code 기능이 아니다 (할루시네이션)

**위치:** `references/habit_catalog.md` H3-04 (150~159줄), `SKILL.md` 76줄·83줄, `session_coach_checklist.md` 34줄·50줄

**문제:**  
H3-04는 `.claudeignore`를 "공식 권장" 기능으로 제목에 명시하고("공식 권장 / practices_scan 섹션1-A"), "프로젝트 루트에 `.claudeignore`(또는 설정상 동등 기능)를 두면 `.gitignore`와 동일 문법으로 자동 탐색에서 제외할 수 있다"고 단정한다.

**공식 문서 확인 결과(2026-06):**
- Anthropic 공식 docs에는 `.claudeignore`에 대한 **언급이 전혀 없다.**
- GitHub issue #29455, #30810은 `.claudeignore` / `.claude-ignore` 기능을 **요청하는 long-running open issue**이며, 아직 구현되지 않았다.
- Anthropic의 공식 답변은 "**`.claudeignore` 대신 settings.json의 `permissions.deny` 설정을 쓰라**"이다.
- 즉 `.claudeignore`는 커뮤니티가 원하는 기능명일 뿐, **현 시점 실재하지 않는 기능**이다. 일부 서드파티 도구·플러그인이 자체적으로 이 파일을 읽을 수는 있으나, "Claude Code 네이티브 자동 탐색 필터"로서는 존재하지 않는다.

또한 "공식·커뮤니티 보고: `.next/` 하나만 추가해도 컨텍스트 30~40% 절감" 수치는 존재하지 않는 기능에 대한 절감 주장이므로 근거 자체가 성립하지 않는다.

제목의 "[공식 권장 / practices_scan 섹션1-A]" 라벨이 가장 위험하다 — 존재하지 않는 기능을 "공식 권장"으로 단정한다.

**수정지시 (택1):**
- **(A 권장) 기능명 교체:** H3-04 전체를 "민감·대형 디렉토리는 settings.json `permissions.deny`로 차단"으로 재작성. `.claudeignore`는 "커뮤니티가 요청 중인 미구현 기능(issue #29455, open)"으로 1줄만 언급하거나 완전 삭제. `.gitignore`는 Claude Code가 일부 존중하는 부분이 있으나 보안 차단 보장은 아님을 명시.
- **(B 최소) 완화 표기:** 제목의 "공식 권장" 라벨 삭제 → "[커뮤니티 요청 / 미구현 가능성]". "공식 권장"·"공식 보고" 단정 전부 제거하고 "정확한 설정 키는 `permissions.deny` 확인 필요"로 완화.
- SKILL.md·checklist의 `.claudeignore` 언급도 동일하게 정정. 카테고리 H3 패턴 수(현재 4개)도 재검토.

> **이것이 v1.1에서 새로 추가된 패턴이므로 BLOCKER다. v1.0 검토에서 지적했던 "hallucinated feature 최우선 탐지"에 정확히 해당.**

---

### [축1][PASS] plan mode `Shift+Tab` — 정확

`references/habit_catalog.md` H5-02(230줄) "Shift+Tab으로 plan mode 진입 → Claude가 파일을 읽되 수정하지 않으므로…"는 공식 문서와 일치. 공식: "Shift+Tab으로 default → acceptEdits → plan 순환, plan mode는 read-only tools만 사용." 정확. checklist 18줄도 정확.

---

### [축1][PASS] `/rewind` 4옵션 설명 — 정확

`SKILL.md` 134줄·`habit_catalog.md` H1-02(32줄) "대화만/코드만/둘다 복원 + Summarize from/up to here식 부분 요약"은 공식 문서와 일치. 공식: "Esc+Esc 또는 /rewind로 메뉴 열기 → restore conversation/code/both, Summarize from here / up to here." 정확.

---

### [축1][PASS] MCP deferred — 정확 (단 A패치 정확성은 축2 참조)

H3-02의 "2026 공식 문서 기준 MCP tool 정의는 기본 deferred"는 공식 문서로 확인됨. 공식: "Tool search is enabled by default, MCP tools are deferred… only tool names and server instructions load at session start." 정확.

---

## 축 2 — A 패치 정확성

### [축2][PASS] MCP deferred 정정 — 과교정 아님, 정확

H3-02 정정은 정확하며 균형 잡혔다. "모든 schema 상시 재전송은 더 이상 사실 아님 / 다만 tool 이름 목록·초기화·호출 시점 schema 주입 비용은 누적 / 과거 non-deferred 수치(Playwright 3,442·Gmail 2,640)는 deferred에선 미적용"은 공식 문서(tool names + server instructions만 세션 시작 시 로드, `alwaysLoad`/`ENABLE_TOOL_SEARCH=auto` 옵션 존재)와 부합. 과교정 아님.

**MINOR 보강:** 공식적으로 `alwaysLoad: true` 서버나 `ENABLE_TOOL_SEARCH=auto`(컨텍스트 10% 이내면 upfront 로드) 설정 시 여전히 schema가 상시 주입된다는 예외가 있다. H3-02에 "단 `alwaysLoad`/`ENABLE_TOOL_SEARCH` 설정에 따라 상시 주입될 수 있음" 1줄 추가 권장.

---

### [축2][MAJOR] habit_catalog.md:H1-03 / checklist — Chroma 2025 "35분" 시간 임계는 출처에 없는 수치

**위치:** `references/habit_catalog.md` H1-03(43줄), `session_coach_checklist.md` 14줄·31줄

**문제:**  
"Chroma 2025 연구(18개 프론티어 모델 공통)에 따르면 누적 약 50K 토큰 또는 **경과 약 35분**부터 성능 저하(context rot)가 시작되며 200K 윈도우 절반 미만에서도 발생한다."

**출처 확인 결과:**
- Chroma 2025 "Context Rot" 연구는 **실재한다.** 18개 프론티어 모델(GPT-4.1, Claude 4, Gemini 2.5, Qwen3 등) 테스트, "200K 윈도우 모델도 50K 토큰에서 유의미한 저하" — 이 부분은 **정확하다.**
- 그러나 Chroma 연구는 **input token 길이** 기준 연구다. "경과 약 35분"이라는 **시간(wall-clock) 임계는 Chroma 연구에 존재하지 않는다.** context rot은 토큰 길이의 함수이지 경과 시간의 함수가 아니다. "35분"을 Chroma 출처로 귀속시킨 것은 부정확하다.
- "35분"은 habit_scan.py의 `SESSION_MAX_MINUTES = 35` 휴리스틱에서 역으로 끌어온 수치로 보이며, 이를 학술 연구 출처에 붙이면 출처 오귀속이다.

**수정지시:**
- "또는 경과 약 35분" 부분을 Chroma 귀속에서 분리. "누적 약 50K 토큰부터 저하(Chroma 2025) — 시간 35분 기준은 본 스킬의 보조 휴리스틱(토큰 추정 어려운 경우용)"으로 명확히 구분.
- checklist 14·31줄도 "(Chroma 2025 연구 context rot 임계)" 라벨에서 시간 기준은 빼고 토큰 기준만 연구에 귀속.

---

### [축2][PASS] H4-01 thinking 재과금 정정 — 정확 (v1.0 BLOCKER 해소 확인)

H4-01(170줄) "thinking 토큰은 생성될 때 output으로 1회 과금 / Opus 4.5+·Sonnet 4.6+는 컨텍스트 유지되나 캐시 read 취급으로 풀 input보다 저렴 / 그 이전 모델은 다음 요청 전 제거 / 어느 쪽이든 이중 과금 아님"은 공식 문서와 정확히 일치. **v1.0 BLOCKER [B1] 해소됨.**

### [축2][PASS] H1-03 임계치 단정 정정 — 해소 확인

"83.5%/167K 단정"이 삭제되고 "상한을 기다리지 말고" 표현으로 교체됨. **v1.0 BLOCKER [B2] 해소됨.**

### [축2][PASS] /rename→/resume·Option 단축키 — 해소 확인

퀵카드 #1(20줄) "`claude --resume`(CLI) 또는 `/resume`(인터랙티브)"로 정정됨(v1.0 [M3] 해소). H4-01·H4-02의 `Option+T`/`Option+O` 단정이 "`/effort low` / `/config` / `MAX_THINKING_TOKENS=0`"로 교체됨 — 공식 문서에서 `Option+T`/`Alt+T` thinking 토글은 실재 확인되나, 환경별 상이로 완화한 것은 안전한 선택. (v1.0 [M1] 해소.)

---

## 축 3 — habit_scan.py 정합성

### [축3][MAJOR] habit_scan.py:254~257, 314~316 — H8-01 연속 Read 카운터가 정상 작업을 오탐

**위치:** `scripts/habit_scan.py` `analyze_session` consecutive_reads 로직(231~236줄), aggregate(314~316줄)

**문제:**  
`consecutive_reads`는 Read tool_use에서 +1, **다른 tool_use에서만** 리셋된다(236줄 `else: consecutive_reads = 0`). 그러나 Read의 결과인 `tool_result` 블록은 tool_use가 아니므로 카운터를 리셋하지 않는다. 실제 Claude Code 흐름은 `Read → tool_result → (다음 턴) Read → tool_result → …`이 정상이다. 따라서 **서로 다른 턴에 걸친 4개의 단일 Read(완전히 정상적 작업)**도 "연속 Read 4회"로 집계되어 H8-01(메인 스레드 탐색)이 오탐된다.

**직접 검증:** 4개 턴 각각 단일 Read + 그 사이 tool_result만 있는 fixture → `pattern_counts: {'H8-01': 1}` 오탐 확인. "메인 스레드에서 한 턴에 다수 파일을 몰아 탐색"이라는 의도와 달리, 분산된 정상 Read를 잡는다.

**수정지시:**
- "연속 Read"를 "한 assistant 메시지(턴) 내 동시 Read 개수" 또는 "tool_result 없이 이어진 Read"로 재정의. 가장 단순한 fix: tool_result를 만나면 `consecutive_reads = 0`으로 리셋(단 같은 메시지 내 병렬 Read는 유지). 또는 H8-01을 "단일 메시지 내 Read ≥ N개"로 변경.
- measurement_and_hooks.md 42줄 "연속 Read ≥4회 (근사)" 설명도 정정.

---

### [축3][MAJOR] habit_scan.py:172 — 최상위 비-dict JSONL 라인에서 크래시 (EXIT=1)

**위치:** `scripts/habit_scan.py` `analyze_session` 172~173줄

**문제:**  
`for obj in messages:` 직후 `msg = obj.get("message", {})`를 호출한다. `iter_messages`는 `json.loads`가 성공한 모든 라인을 yield하므로, 유효 JSON이지만 dict가 아닌 라인(예: `[1,2,3]`, `"string"`, `42`)이 들어오면 `obj.get`이 AttributeError를 일으킨다.

**직접 검증:** `[1,2,3]` 1줄만 든 .jsonl → `AttributeError: 'list' object has no attribute 'get'`, **REAL EXIT=1, traceback 출력.** "어떤 입력에도 크래시 0" 주장 위반.

**수정지시:**
- `analyze_session` 루프 시작에 `if not isinstance(obj, dict): continue` 추가.
- 또는 `iter_messages`에서 `if isinstance(parsed, dict): yield parsed`로 dict만 yield.

---

### [축3][MAJOR] habit_scan.py:331 — ccusage 서브커맨드 오류로 보강 기능이 영구 무력

**위치:** `scripts/habit_scan.py` `try_ccusage` 331줄

**문제:**  
`["npx", "--yes", "ccusage@latest", "report", "daily"]`를 호출하나, 실제 ccusage CLI에 **`report`라는 서브커맨드는 없다.** 올바른 형식은 `ccusage daily`(또는 `monthly`/`weekly`/`session`).

**직접 검증:** `npx ccusage@latest --help` → `USAGE: ccusage [daily] <OPTIONS>` / `COMMANDS: daily, monthly, weekly, session, blocks…`. "report"는 존재하지 않음. 따라서 `try_ccusage`는 항상 returncode != 0 → 항상 None 반환 → "ccusage 미설치 또는 실패" 메시지가 ccusage가 설치돼 있어도 항상 출력된다. graceful skip이라 크래시는 없으나 **B 패치의 핵심 차별점("ccusage 보강")이 실제로는 한 번도 작동하지 않는다.**

**수정지시:**
- `["npx", "--yes", "ccusage@latest", "daily"]`로 수정. 출력 파싱(첫 8줄)은 daily 테이블 포맷에 맞춰 재확인. `--json` 플래그(`ccusage daily --json`) 사용 후 파싱하면 더 안정적.

---

### [축3][PASS] message.usage 4필드 파싱·message.id dedup·토큰 근사 명시 — 정확

- usage 4필드(input/output/cache_read/cache_creation) 파싱 정확(190~198줄), `or 0` 폴백으로 None-safe.
- `message.id` 기준 dedup(189줄 `mid not in seen_ids`) 정확 — measurement_and_hooks.md 44줄에 "병렬 tool call은 동일 message.id 공유 → dedup" 설명도 올바름.
- 토큰 추정이 "근사·경향 파악용"으로 일관 명시(34줄 주석, 140줄 docstring, 400줄 출력, measurement md 45줄). 과대주장 없음. **양호.**
- `--json` 출력 유효성 직접 검증 통과(valid JSON, pattern_counts 정상).
- 패턴→catalog ID 매핑은 실제 habit_catalog.md ID(H2-01·H2-02·H8-02·H5-04·H4-03·H1-01·H1-03·H8-01)와 일치.

### [축3][MINOR] CATALOG 매핑이 25패턴 중 8개만 커버 — "25패턴 진단" 표현 과장

docstring·measurement md는 "25패턴 습관 진단"이라 하지만, habit_scan이 실제 감지하는 것은 8패턴(JSONL에서 정적 관찰 가능한 것만)이다. 나머지(프롬프트 명료성 H5-01 등 의도 판단 필요 패턴)는 스크립트로 감지 불가가 맞다. 정직한 한계이나 "25패턴 진단"이라는 표현은 오해 소지.

**수정지시:** docstring·measurement md를 "25패턴 카탈로그 중 JSONL에서 정적 관찰 가능한 8패턴 진단"으로 정정.

---

## 축 4 — hook_check.py 안전성

### [축4][PASS] exit 0 고정·크래시 0 — 보장 확인

- `main`이 항상 `return 0`(302줄), payload 파싱 실패는 `except: payload = {}`(290줄), 핸들러 호출도 `try/except: pass`(298줄)로 이중 보호.
- 직접 검증: empty stdin / malformed json / null fields / non-dict tool_input / array payload `[1,2,3]` / nested content 6종 모두 **EXIT=0, 크래시 0.** 안전.
- self-test도 EXIT=0.

### [축4][PASS] settings.json 등록 예제 — hook 규약과 일치

`measurement_and_hooks.md` 122~157줄의 `UserPromptSubmit`(matcher 없음) + `PreToolUse`(matcher: "Bash"/"Read") 구조는 공식 Claude Code hook 규약과 일치. tokensave hook과 공존 예제(배열 추가)도 올바름.

### [축4][MAJOR] hook_check.py:88~92, 151~161 — reads-file을 "첫 메시지 감지"와 "Read 추적"에 공유 → H7-01 영구 침묵 버그

**위치:** `scripts/hook_check.py` `check_userprompt` H7-01 분기(151~161줄), `_session_reads_path`(88줄)

**문제:**  
H7-01(첫 메시지 긴 설명) 감지는 "reads_file이 존재하지 않으면 첫 메시지"라는 휴리스틱을 쓴다(153~154줄 `is_first_message = not reads_file.exists()`). 그러나 **같은 reads_file이 H2-01(Read 재읽기 추적)에도 쓰인다.** 따라서 세션에서 **Read가 UserPromptSubmit보다 먼저 한 번이라도 일어나면** reads_file이 생성되어, 이후 첫 사용자 프롬프트가 아무리 길어도 H7-01이 영원히 발동하지 않는다.

**직접 검증:** Read pretooluse 1회 실행 후 614자 긴 프롬프트 → H7-01 경고 없음. 커플링 버그 확인.

**부가 발견 — self-test가 거짓 통과:** self-test Test 2의 샘플(`SAMPLE_USERPROMPT_LONG`, 221줄)은 `* 5` 반복으로 **285자**다. 임계 `FIRST_MSG_LONG_THRESHOLD = 500` 미만이므로 H7-01은 **샘플 자체가 절대 트리거되지 않는다.** self-test는 "Test 2: 첫 메시지 긴 설명"에서 경고가 안 떠도 통과한 것처럼 보이지만, 실제로는 로직이 아니라 샘플 길이 때문에 침묵한 것이다 — 회귀 테스트로서 무의미.

**수정지시:**
- H7-01 첫 메시지 감지용 마커를 reads-file과 **분리**(별도 파일 `tokenhabit_<session>_seen` 등).
- self-test `SAMPLE_USERPROMPT_LONG`을 500자 초과로 늘려 실제 트리거되게 수정(`* 5` → `* 12` 이상).

### [축4][MINOR] hook_check.py:120~127 — message.content가 리스트일 때 모호 프롬프트 폴백 오작동

`check_userprompt`의 prompt 추출(122~127줄)에서 `payload.get("message",{}).get("content","")`가 리스트(`[{"type":"text","text":"고쳐줘"}]`)를 반환하면 `str()`로 `"[{'type':..}]"` 문자열이 되어 모호 패턴 매칭이 실패한다. 

다만 실제 Claude Code `UserPromptSubmit` payload는 `prompt` 필드를 직접 제공하며(직접 검증: `{"prompt":"고쳐줘",...}` → 정상 H5-01 발동), message.content 경로는 폴백일 뿐이라 실무 영향은 낮음. **MINOR.**

**수정지시:** message.content 폴백 시 리스트면 text 블록을 join하도록 보강(선택).

### [축4][MINOR] 오탐 스팸 수준 — 허용 범위, 단 Bash 패턴 광범위

`RISKY_BASH_PATTERNS`에 `\bmake\b`, `\btsc\b`, `\bfind\s+/`, `\bgrep\s+-r\b` 등이 포함돼 필터 없는 정상 명령에도 경고가 자주 뜰 수 있다. exit 0 stderr 경고라 차단은 없으나, 빈번하면 사용자가 무시하게 된다(alert fatigue). `FILTER_PATTERNS` 면제가 있어 과하진 않으나, `make`·`tsc`처럼 출력이 작을 수도 있는 명령은 오탐률을 높인다.

**수정지시(선택):** `make`·`tsc` 등은 제거하거나, 출력 크기를 예측할 수 없는 test/build/log 류만 유지.

---

## 전체 종합

| 판정 | 사유 |
|------|------|
| **수정후PASS** | BLOCKER 1건(`.claudeignore` 할루시네이션)은 존재하지 않는 기능을 "공식 권장"으로 단정 — 반드시 정정. MAJOR 4건(Chroma 35분 오귀속, H8-01 오탐, JSONL 크래시, ccusage 서브커맨드 오류, H7-01 침묵 버그 중 4건)도 수정 필요. 단 A패치 핵심(thinking·임계치·MCP deferred·plan mode·/rewind)은 모두 정확하고, hook의 exit 0·크래시 0 안전성은 견고하다. 구조와 방향은 건전. |

### BLOCKER (1건)

1. **[B1] `.claudeignore` 할루시네이션** — `habit_catalog.md` H3-04 + SKILL.md + checklist  
   → 공식 문서에 없는 미구현 기능(GitHub issue #29455 open). Anthropic 공식 답변은 "`permissions.deny` 사용". 제목의 "공식 권장" 라벨이 특히 위험. `permissions.deny`로 교체하거나 "미구현 커뮤니티 요청"으로 완화 필수.

### MAJOR (4건)

1. **[M1] Chroma 2025 "35분" 시간 임계 출처 오귀속** — `habit_catalog.md` H1-03, checklist. Chroma는 토큰 길이 연구로 50K 토큰 부분만 정확. "35분"은 자체 휴리스틱이며 연구에 없음. 귀속 분리 필요.
2. **[M2] habit_scan.py H8-01 연속 Read 오탐** — tool_result가 카운터를 리셋 안 해, 분산된 정상 Read 4개를 "연속 탐색"으로 오탐(직접 재현).
3. **[M3] habit_scan.py 크래시 + ccusage 무력** — (a) 최상위 비-dict JSONL 라인에서 AttributeError·EXIT=1("크래시 0" 위반). (b) `ccusage report daily` 서브커맨드 오류로 보강 기능이 항상 실패(실제 CLI는 `ccusage daily`).
4. **[M4] hook_check.py H7-01 영구 침묵 버그** — reads-file을 Read추적과 공유해, Read가 먼저 일어나면 H7-01 발동 불가(직접 재현). self-test 샘플도 285자<500이라 거짓 통과.
