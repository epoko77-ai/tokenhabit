# 조직 구성 진단기 (tokenhabit-org) 설계 스펙 v0.1

3개 독립 설계 통합: **config-recon**(Fable 5, 설정 표면 실사) · **rule-designer**(Fable 5, 룰셋 설계) ·
**codex gpt-5.6-sol/ultra**(아키텍처 + 적대적 검증). 공식 문서 직접 확인분 포함.

---

## 0. 판정: 조건부 GO — 단, 범위를 좁혀서

codex 판정을 그대로 채택한다.

> 지금 당장 공개용 "멀티툴 조직 토큰 절감 린터"를 만드는 것은 **NO-GO**.
> 먼저 **Claude Code 전용 컨설팅 감사 도구**로 좁혀 검증할 가치는 있다.

**정적 분석이 증명할 수 있는 것은 셋뿐이다:**
1. 어떤 설정이 **실제로 로드되는가**
2. 무엇이 **shadowed·무시·잘림·상시 노출**되는가
3. 그 **크기와 적용 범위**가 얼마인가

**증명할 수 없는 것:** "그 내용이 불필요하다", "MCP가 낭비다", "N토큰 절약된다".
이 선을 지키지 않으면 *"CLAUDE.md 줄이세요"를 과학처럼 포장하는 도구*가 된다.

---

## 1. 만들 가치가 있는 룰 vs 없는 룰

### 가치 있음 — 사람이 수작업으로 재현하기 어려운 것

- managed 설정 때문에 팀 설정이 **실제로는 무시됨**
- 잘못된 위치·확장자·schema로 hook/rule이 **로드되지 않음**
- `@import` 포함 **실제 expanded instruction graph**가 예상보다 큼
- 조건부여야 할 규칙이 실제로는 **unconditional** (`.claude/rules/`에 `paths` 누락)
- MCP tool search가 provider/model/env 때문에 비활성화되어 **schema가 upfront load**
- 같은 이름의 skill/plugin/MCP **충돌**로 의도와 다른 항목 활성화
- 설정을 바꿨는데 **엔드포인트에 적용되지 않음**

### 가치 낮음 — 맥락 없는 inventory, 블로그 조언 수준

- "CLAUDE.md 200줄 초과" (단독으로는)
- "MCP 10개 초과" / "skill 20개 초과"
- "`permissions.deny` 없음"
- "최고 모델이 기본값"

> ⚠️ 특히 **"서버 수 × schema 토큰" 계산은 기본 환경에서 틀리다** — MCP는 기본 deferred다.

### 포지션

> "조직 토큰 절감 린터"가 아니라
> **"AI coding setup의 실제 적용 상태와 개입 후보를 재현하는 configuration audit engine"**

그리고 이것은 **제품 해자가 아니다.** 컨설팅을 반복 가능하게 만들고 개입 데이터셋을 쌓는 **장비**다.

---

## 2. 실측 근거 — 이 머신 (config-recon)

세션 시작 시 고정 로드 **약 37~48K 토큰**. 지배 요인은 CLAUDE.md가 아니다.

| 항목 | 추정 토큰 | 비중 |
|---|---|---|
| 커스텀 에이전트 117개 description | 13~19K | ~40% |
| 개인 스킬 44개 description | 10~14K | ~30% |
| 플러그인 스킬·커맨드 description | 6~8K | ~17% |
| `~/CLAUDE.md` | 2.0~2.7K | ~6% |
| MCP 툴 이름 + server instructions | 2~4K | ~8% |

**description 총량이 80%.** "조직 구성이 곧 고정비"의 실증이며, 200K 컨텍스트의 ~20%를 시작 전에 소모한다.

즉시 고칠 수 있는 실사 발견: **Vercel 플러그인 이중 설치**(`vercel@official` + `vercel-plugin@vercel`),
깨진 커맨드 심링크 2개, `~/.codex/config.toml`의 `model_reasoning_effort = "ultra"` 전역 고정,
`permissions.deny`에 `node_modules` 차단 부재.

### 상시 vs 조건부 (공식 문서 확정)

| 표면 | 판정 |
|---|---|
| CLAUDE.md | **항상·전체** ("loaded in full regardless of length"). user message로 주입. HTML 블록 주석은 스트립(토큰 0) |
| `@import` | **항상·전체**, 최대 **4 hops**. "분할해도 컨텍스트는 안 준다" |
| `.claude/rules/` | **`paths` 프론트매터가 없으면 launch에 무조건 로드** — rules로 옮긴다고 자동 절약이 아니다 |
| Skill | **description만 상시**(스킬당 **1,536자 캡**), 본문은 온디맨드. 로드 후 세션 끝까지 상주 |
| Agent | **description 상시**(Agent 툴 목록으로 주입, 실물 확인), 본문은 스폰 시 |
| MCP schema | **기본 deferred**. 툴 이름 + server instructions(각 2KB 캡)만 상시. 예외: `alwaysLoad`, tool search 비활성, 비-first-party `ANTHROPIC_BASE_URL`, Azure Foundry |
| Plugin | 컴포넌트별. 스킬·에이전트 desc·MCP 툴 이름 상시 |
| Output style | 상시(system prompt 일부, 세션 시작 시 고정) |
| Hook | **상시 0**. 이벤트 시에만 출력 주입 |
| MEMORY.md | 첫 **200줄/25KB**만 상시 |
| 시스템 프롬프트·내장 툴 baseline | **공식 수치 없음** → `/context` 실측 필요 |

---

## 3. 아키텍처

```
명시적 입력 (repo roots + user-scope opt-in + admin export + client version)
        ↓
Tool/Surface/Version Adapter  (discover → parse → resolve → optional runtime probe)
        ↓
Resolution Graph  (source, precedence, merge rule, activation condition, provenance)
        ↓
Canonical Facts + Capability Manifest
        ├── Static rules
        └── Config fingerprint ↔ normalized session events
        ↓
Rule Results + Scan Health  →  JSON / CLI / Markdown / SARIF / Executive report
```

### 원칙

**공통 병합 엔진을 만들지 않는다.** 공통화할 것은 **결과 스키마**이고, 발견·병합·활성화 의미는
**어댑터가 책임**진다. Effective configuration은 단일 객체가 아니라 함수다:

```
tool × client version × surface × project root/CWD × trust
     × CLI/env override × provider/model × managed/cloud policy × target path
```

**Instruction file은 "winner" 하나로 축약하면 안 된다.** ordered chunks + activation predicate를
가진 graph로 보존한다. 충돌한 자연어 지시 중 무엇을 모델이 따를지는 정적 분석으로 확정 불가.

### 상태 모델

- **Source discovery**: `observed` / `not_present` / `declared_but_unreadable` / `not_observable` / `unsupported_version`
- **Rule 결과**: `pass` / `finding` / `not_applicable` / `inconclusive` / `error` / `suppressed`
- **Scan 전체**: `complete` / `partial` / `failed`
  → **`partial` 스캔은 findings가 0이어도 "clean"을 출력하면 안 된다**

### Finding 구조 (rule이 직접 emit — aggregate 배선 금지)

```
rule_id, rule_version
tool/surface/supported_versions
status, subject, activation_scope
measurement(value, unit, provenance)
inference(claim, confidence)
impact(estimate?, method?, interval?)
threshold(value?, basis, source, verified_at)
coverage, remediation, exception conditions
```

> 현재 tokenhabit처럼 `detector return key → aggregate mapping → catalog → report`를 각각 수정하는
> 구조가 **H8-02 배선 누락**을 만들었다. 같은 구조를 반복하지 않는다.

### 증거 4축 (기존 3등급으로는 부족)

| 축 | 값 |
|---|---|
| 값의 출처 | `config_observed` / `runtime_observed` / `converted` / `modeled` |
| 실제 적용 여부 | `effective` / `possible` / `unknown` |
| 결론의 확신 | `confirmed` / `correlated` / `theoretical` |
| 절감 근거 | `none` / `exposure_estimate` / `observed_delta` / `causal_estimate` |

---

## 4. 룰 카탈로그 (rule-designer 초안, codex 판정 반영)

ID 체계: `ORG-<CAT>-NNN` (불변, 번호 재사용 금지) + slug 병기.
카테고리: `CTX`(컨텍스트 파일)·`MCP`·`SKL`·`PRM`·`HOK`·`MDL`.
**severity(영향)와 confidence(확신도)를 분리**한다.

| ID | slug | 로그 | 기본 상태 |
|---|---|---|---|
| ORG-CTX-001 | claudemd-bloat | 보강 | advisory (공식 200줄 권고) |
| ORG-CTX-002 | import-chain | 불요 | CTX-001 합산. 깊이 4 hops |
| ORG-CTX-003 | scope-duplication | 불요 | warn |
| ORG-CTX-004 | multi-tool-drift | 불요 | **Claude Code는 AGENTS.md를 읽지 않음**(공식 확인) — `@AGENTS.md` 임포트·symlink만 |
| ORG-CTX-005 | dead-references | 불요 | 사실 판정, 1건부터 finding |
| ORG-CTX-006 | unconditional-rules | 불요 | **신규** — `.claude/rules/`에 `paths` 없어 상시 로드 |
| ORG-MCP-001 | server-count | 보강 | **임계값 없음.** 이름 목록 토큰만 보고 |
| ORG-MCP-002 | no-observed-use | **필수** | 로그 교차. 표본 미달 시 inconclusive |
| ORG-MCP-003 | upfront-exposure | 불요 | deferred 예외 탐지(alwaysLoad·게이트웨이·Foundry) |
| ORG-SKL-001 | catalog-overhead | 불요 | **description 총 토큰**. 개수 아님 |
| ORG-SKL-002 | no-observed-use | 준필수 | `~/.claude.json`의 `skillUsage`로 준정적 판정 가능 |
| ORG-SKL-003 | verbose-description | 불요 | 1,536자 캡 대비 + 설치본 내 p90 상대 비교 |
| ORG-SKL-004 | duplicate-install | 불요 | **신규** — 같은 기능 플러그인 이중 설치(이 머신 vercel 실례) |
| ORG-PRM-001 | huge-dir-unblocked | 보강 | 로그에서 실제 탐색 관측 시에만 승격 |
| ORG-HOK-001 | no-output-filter | 준필수 | **부재 자체는 낭비가 아니다.** 로그에 H8-02 히트가 있을 때만 finding |
| ORG-MDL-001 | top-tier-default | 보강 | info. fail 없음 |

### 임계값 정책 (가장 중요한 판정)

| 근거 | 처리 |
|---|---|
| schema·실제 동작 한계 | **deterministic finding 가능** (예: Codex AGENTS 32KiB 잘림, 스킬 desc 1,536자 truncation) |
| 공식 권고 | `advisory` (예: CLAUDE.md 200줄 — **공식 확인 완료**) |
| 조직 정책 | `policy finding` |
| 조직 내 경험적 분포 | **outlier signal만.** 나쁘다는 뜻 아님 |
| intervention 데이터로 검증 | 특정 tool/version/use case에 한해 calibrated rule |
| **아무 근거 없음** | **default off experimental 또는 metric만 출력** |

**MCP·skill에 "몇 개부터 과다"는 없다.** 개수 대신 연속값으로 보여준다:
unconditional metadata bytes / 실제 activation 횟수 / covered session 중 사용 비율 /
startup failure·reconnect 빈도 / upfront schema bytes / 중복 여부 / 최대 contributor 순위.

> 상대 비교도 만능이 아니다. 조직 전체가 잘못 구성됐으면 median도 나쁘다.
> 같은 `tool × version × provider/model × use case` 안에서 **우선순위 신호로만** 쓴다.

---

## 5. 오탐 통제

### 억제 3계층
1. **인라인** (마크다운만): `<!-- tokenhabit-org-ignore: ORG-CTX-001 reason="..." -->`
2. **설정** `.tokenhabit-org.yaml`: 룰별 임계 오버라이드·off·경로 스코프. **`reason` 필수**, `expires` 선택
3. **baseline 스냅샷**: 이후 신규 finding만. 컨설팅의 before 측정본과 겸용

**억제된 finding은 사라지지 않고 `suppressed` 섹션에 남는다.** 억제율 높은 룰은 임계 재조정 후보로 자동 표시.

> ⚠️ codex 경고: **instruction 파일 안에 suppression 주석을 넣는 관례는 차용하지 말 것.**

### inconclusive 사유 코드
`logs_unavailable` / `insufficient_sessions` / `parse_error`(**pass로 넘기지 않음**) /
`option_schema_unverified` / `tool_version_unknown` / `adapter_missing`(침묵 아닌 보고)

### 구조적 방지책
- rule registry metadata 누락은 **default 보정하지 말고 startup failure**
- 각 rule에 `finding` / `pass` / `not_applicable` / `error` **픽스처 필수**
- **known-positive 픽스처에서 한 번도 발화하지 않는 rule은 CI 실패**
- unknown key와 parse coverage 비율을 **항상 출력** (드리프트 카나리아)
- README 예시·Markdown·executive 표를 **canonical fixture에서 생성**
- **instruction 삭제는 autofix 금지** — proposed diff + owner 승인 + rollback

> **정적 오탐은 개인 습관 알림보다 피해가 크다.** 조직 설정 수정은 blast radius가 전 직원이고,
> 한 번의 오탐으로 비용뿐 아니라 품질·보안 지침까지 중앙에서 제거될 수 있다.

---

## 6. 절감 주장 사다리 — 이 순서를 넘지 않는다

1. **정적 사실** — "expanded unconditional instructions가 28.4KiB → 13.2KiB로 감소했다"
2. **노출 환산** — "prompt content 약 3.2K~4.8K 토큰이 줄 것으로 추정" (`estimated`, **비용 아님**)
3. **관측 연관** — "비교 가능한 세션에서 work unit당 input이 11% 낮게 관측" (association)
4. **인과 절감** — 통제된 rollout + 품질 non-inferiority 통과 시에만 "평균 효과 X, 구간 Y~Z"

### 금지
- 줄 수 → 토큰 직접 변환
- 제거된 모든 내용을 waste로 간주
- content tokens × 전체 turn ← **우리가 H3-01에서 저질렀던 실수**
- server/skill count × 상수
- 구독 사용량을 임의의 달러로 환산
- 품질·완료율 없이 토큰 감소를 효율 향상으로 표현

실제 비용 산식:
```
Δcost = Σturn [ Δuncached_input × input_price + Δcache_write × 1.25x
              + Δcache_read × 0.1x + Δoutput × output_price ]
```

---

## 7. 컨설팅 산출물

### Executive 1-page (finding 수·A~F 등급이 아니라 의사결정 문서)
감사 범위(tool/version/surface/repo/기간/**coverage**) · confirmed system issue 상위 3개 ·
각 변경의 적용 범위·owner·작업량·위험·rollback · 변경 전후 config footprint ·
outcome 변화와 **품질 guardrail** · attribution 등급 · 다음 30일 action

### 기술 부록
effective config + source provenance · shadowed/unknown/not-observable source ·
rule ID/version과 **공식 근거 확인일** · suppression과 만료일 · proposed diff + validation command ·
false-positive 조건 · **scan health와 누락률**

### Before/after — 교란 통제
워크숍·코칭·설정 변경을 동시에 하면 측정되는 것은 **전체 engagement package의 효과**다.
설정 변경만의 효과라고 말하면 안 된다.

가장 현실적인 강한 설계는 팀·레포 단위 **randomized staggered rollout**(stepped-wedge).
모든 팀이 최종 적용받되 시작 시점만 무작위화 → 아직 적용 전인 팀이 동시 비교군.
운영상 순차 배포와도 맞는다.

무작위화가 어려우면: 유사 비교군 · intervention 전 추세 공개 · 교란 변수 기록(version·sprint·
release·incident·headcount·task mix) · absolute/relative + 불확실성 구간 · config 실제 적용률 ·
완료율·재작업·CI·wall-clock 중 **최소 하나의 guardrail**.

> 단일군 2주 pre/post는 **"변경 후 낮게 관측됐다"까지만** 허용.

### 개인 식별 방지
raw log·config 원문은 **엔드포인트에 유지** · 중앙 export는 고정된 `team-day` 집계와 config hash만 ·
prompt/output·raw path·user handle·지속적 hashed user ID 제외 · **리더보드·개인 drill-down 금지** ·
작은 cohort는 병합 또는 `insufficient data` · **합계에서 역산 가능한 complementary cell도 억제**

> ⚠️ **Hashing만으로는 익명화되지 않는다.** 기본 10명 이상 권고는 제품 정책이지 익명성 보장이 아니다.
> 또한 `~/.claude`·`~/.codex`·개인 plugin·개인 로그까지 중앙 수집하면 **다시 직원 모니터링**이다.
> 개인 scope는 엔드포인트에서만 분석하고 중앙에는 익명 집계만.

---

## 8. 실행 순서 (codex 권고)

1. **현재 신뢰성 계약부터 닫기** — ✅ 1.3.1·1.3.2에서 완료
   (문서 drift 정정, 증거 등급 4종, 캐시 TTL 인증별 처리, H4-03 사실 오류 3건, 절감 산식 정정)
   남은 것: evidence metadata를 JSON 출력에 포함, docs/report를 fixture에서 생성
2. **Claude Code만 지원하는 내부 MVP** — parse/load 오류, import missing/cycle/depth,
   effective expanded footprint, 공식 200-line advisory, shadowed/merged 설정,
   실제 upfront MCP exposure, skill/plugin collision
3. **로그 교차 rule 추가** — connected-but-no-observed-use, 실제 대형 output + mitigation 부재,
   generated directory 실제 탐색, model/effort × outcome
4. **유료 engagement에서 intervention data 수집**
5. **그 후 Codex adapter** — Cursor는 admin export·effective-state 경로 확보 전까지 inventory/partial만

### 중단 기준
> 몇 차례 실제 감사 후에도 상위 finding이 **"200줄 초과", "MCP 많음", "skill 많음"뿐이라면 제품화 중단.**
> 그 경우 configuration checklist와 컨설턴트용 worksheet가 더 정직하고 더 싸다.

반대로 **non-obvious effective-state 오류를 높은 precision으로 반복 발견**하고, 수정 후
**cost/time per verified outcome이 품질 저하 없이 개선**된다면 만들 가치가 있다.
그때의 자산은 린터가 아니라 **검증된 개입 데이터**다.

---

## 9. 미해결 가정 (해소 전까지 해당 룰은 inconclusive 전용)

| # | 가정 | 상태 |
|---|---|---|
| 1 | Claude Code의 AGENTS.md 로드 | ✅ **해소** — 읽지 않음. `@import`·symlink만 |
| 2 | `@import` 깊이 상한 | ✅ **해소** — 4 hops |
| 3 | CLAUDE.md 200줄 공식 권고 | ✅ **해소** — 공식 문서 확인, advisory 승격 가능 |
| 4 | MCP always-load 키 | ✅ **해소** — 서버 단위 `alwaysLoad`, 툴은 `_meta`의 `anthropic/alwaysLoad` |
| 5 | 에이전트 description 상시 로드 | ✅ **해소** — 실물 확인 |
| 6 | `alwaysThinkingEnabled` 키 실존 | ❌ 미확인 |
| 7 | 스킬 호출의 로그 표현 이중성(`/skill` vs 자동 트리거) | ❌ 미확인 — 실로그 픽스처 필요 |
| 8 | `~/.claude.json` mcpServers 구조의 버전 안정성 | ❌ 미확인 |
| 9 | Codex·Cursor 설정 경로·로드 의미론 | ❌ 미확인 (2단계 이후) |
| 10 | 에이전트 개수 세는 기준 | ❌ 불일치 — config-recon 117, rule-designer 121. 플러그인 제공분 포함 여부 확정 필요 |

## 10. 새로 발견한 활용 수단

- **`InstructionsLoaded` 훅** — 어떤 지시 파일이 언제 왜 로드됐는지 로그로 남긴다.
  **정적 추정(estimated)을 런타임 관측(runtime_observed)으로 승격**시키는 결정적 수단.
  베이스라인 측정 절차에 반드시 포함할 것.
- **`/context`** — 세션 시작 고정비 실측. 시스템 프롬프트 baseline은 공식 수치가 없어 이것으로만 확인 가능.
- **`~/.claude.json`의 `skillUsage`** — 스킬 발화율을 로그 전수 스캔 없이 준정적 판정.
- **`.claude/rules/` + `paths` 프론트매터** — CLAUDE.md 다이어트의 **공식 해법**. 단 `paths` 없으면 상시 로드.
- **`claudeMdExcludes`** — 모노레포에서 타 팀 CLAUDE.md 제외.
- **HTML 블록 주석** — 컨텍스트 주입 전 스트립되므로 유지보수 메모를 토큰 0으로 남길 수 있다.
- **`/doctor`** — Anthropic이 이미 CLAUDE.md trim을 제안한다. **ORG-CTX-001의 상당 부분이 이미 1st-party 기능**임을 인정하고, 우리는 조직 전체 고정비 총량으로 무게중심을 옮긴다.
