# tools/ — 조직 구성 진단 도구 (개발 중)

`tokenhabit` CLI가 **개인 세션 로그**를 사후 스캔한다면, 여기 있는 것들은
**세션이 시작되기 전에 이미 실린 것**을 다룬다. 컨설팅 엔게이지먼트의 베이스라인 측정용이다.

설계 배경은 `_workspace/08_strategy/ORG_LINTER_SPEC.md`.

---

## baseline_context.py — 세션 시작 고정비 실측

```bash
python3 tools/baseline_context.py                      # 지금 측정
python3 tools/baseline_context.py --from CAPTURE.md    # 저장된 캡처 파싱
python3 tools/baseline_context.py --json               # 기계 판독
python3 tools/baseline_context.py --snapshot before.json
python3 tools/baseline_context.py --diff before.json after.json
```

`claude -p /context`를 실행해 Claude Code **자신의 회계**를 읽는다.
증거 등급은 `runtime_observed` — 우리가 문자 수를 토큰으로 환산한 추정이 아니다.

### 왜 추정을 버렸나

이 도구가 생긴 이유가 그대로 경고다. 조직 구성 진단은 원래 *"설정 파일을 읽고
문자 수를 토큰으로 환산해 고정비를 추정한다"* 로 설계돼 있었다. 실측해보니
**한 범주에서 5~7배 틀렸다.**

| 항목 | 정적 추정 | 실측 |
|---|---|---|
| 커스텀 에이전트 | 13~19K | **20.8K** |
| 스킬 | 10~14K | **2K** |
| 메모리 파일 | 2.0~2.7K | **3.3K** |

총량은 맞았지만 내역이 틀렸다. 추정만 믿었으면 **"스킬을 정리하세요"** 라고
처방했을 텐데, 실제로 손봐야 할 곳은 에이전트다.

### 출력이 지키는 것

- **지연 로드를 분리 표기.** `MCP tools (deferred)`는 지금 안 실린다. 고정비로 세면 안 된다.
- **`< 20`·`~290` 상한 표기를 구분.** 그냥 더하면 항목합이 범주 실측을 넘는다
  (스킬 항목합 3,630 vs 범주 2,000).
- **해석 못 한 섹션을 항상 보고.** `/context` 포맷이 바뀌면 조용히 0을 내지 않는다.
- **비교 조건 불일치 경고.** 모델·cwd·컨텍스트 창이 다르면 diff를 개입 효과로 읽지 말라고 막는다.

### diff가 말하지 않는 것

베이스라인 비교는 **세션 시작 시 로드되는 컨텍스트가 얼마나 변했는지**까지만 말한다.

- **비용 절감액이 아니다.** 프리픽스는 2번째 턴부터 캐시 읽기(0.1x)로 서빙된다.
  토큰 감소분에 턴 수를 곱하면 컨텍스트 처리량과 과금을 혼동하는 것이다
  (v1.3.2에서 정정한 실수).
- **인과가 아니다.** 같은 기간에 다른 변경이 있었을 수 있다.
- **개선이 아니다.** 컨텍스트를 줄여 결과 품질이 나빠졌을 수 있다.
  guardrail 지표 없이 개선이라 부르지 않는다.

---

## probe_instructions_loaded.py — 훅 페이로드 관측

`InstructionsLoaded` 훅이 실제로 무엇을 주는지 **추측하지 않고 관측**하기 위한 프로브.

```bash
# .claude/settings.local.json 에 등록 (로컬, 커밋 안 됨)
{"hooks": {"InstructionsLoaded": [{"hooks": [
  {"type": "command", "command": "python3 /abs/path/tools/probe_instructions_loaded.py"}
]}]}}

python3 tools/probe_instructions_loaded.py --show
```

### 관측 결과

공식 문서는 공통 필드와 `load_reason`만 적고, **어떤 파일이 로드됐는지 담기는지는
명시하지 않는다.** 실측 결과 담긴다:

```json
{"file_path": "/Users/…/CLAUDE.md",
 "memory_type": "Project",        // 문서에 없는 필드
 "load_reason": "session_start"}
```

**한계도 같이 확인됐다.** 이 훅은 `CLAUDE.md`와 `.claude/rules/*.md`만 커버한다.
고정비의 대부분인 **에이전트·스킬 description은 잡지 않는다.** 그래서 지시 파일
축은 이 훅으로, 나머지는 `/context`로 본다.

프로브는 세션을 **절대 막지 않는다** — 무슨 일이 있어도 exit 0.
캡처 파일은 세션 경로·머신 고유값을 담으므로 `tools/_probe/`는 gitignore 대상이다.

---

## export_team.py — content-free 팀 export

```bash
python3 tools/export_team.py --snapshot before.json --scan-json scan.json --out export.json
python3 tools/export_team.py --audit --snapshot before.json     # 무엇이 나가고 안 나가는지
```

### 구조적 보장 — 지우지 않고 짓는다

이 도구는 스냅샷에서 민감 필드를 **지우지 않습니다.** 빈 문서에서 시작해
**허용목록에 있는 것만 복사**합니다. 지우는 방식은 새 버전이 추가한 필드를
빠뜨릴 수 있지만, 허용목록은 그럴 수 없습니다.

`--audit` 이 필드별로 무엇이 나가고 무엇이 안 나가는지 출력하므로,
고객 보안팀이 코드를 읽지 않고도 검토할 수 있습니다.

### 나가지 않는 것

| 항목 | 이유 |
|---|---|
| `cwd` | 사용자명 + 레포 정체 |
| 파일 절대경로 | 사용자명 + 디렉토리 구조 |
| 항목 이름(에이전트·스킬) | **내부 프로젝트명이 드러남** — 이 머신 실제 예: `policyblind-…`, `wikibrain-…` |
| 메모리 파일 이름 | 경로 그 자체. **`--name-mode raw` 에서도 절대 노출 안 함** |
| MCP 서버명 | 벤더 관계가 드러남 |
| session_id · transcript_path | 개인 특정 |
| 프롬프트·출력·툴 인자 | 애초에 읽지 않음 |

### 가명화

조직 salt로 HMAC. 같은 salt에서 **가명이 안정적**이라 두 시점을 대조할 수 있고,
salt가 다르면 **조직 간 대조는 불가능**합니다. salt 원문은 export에 안 들어가고
지문(fingerprint)만 실려서 "같은 salt인지"만 확인됩니다.

> ⚠️ salt를 잃으면 과거 export와 대조할 수 없습니다. 커밋하지 말고 따로 보관하세요.
> 그리고 **hashing만으로는 익명화가 아닙니다** — 코호트가 작으면 역추적됩니다.

### k-익명성

기본 하한 5명. 미달이면 `sufficient: false`와 사유가 실리고 경고가 뜹니다.
상위 조직에 합산하거나 `insufficient data` 로 보고해야 합니다.

### 회귀 테스트

`tests/test_export_leaks.py` 가 합성 스냅샷에 사용자명·절대경로·내부
프로젝트명·벤더명·session_id를 심어두고 **하나라도 export에 살아남으면 실패**합니다.
CI에서 매 push마다 돕니다. 실제로 이 테스트가 `--name-mode raw` 의 경로 누출을
잡아냈습니다.

---

## 측정 시 주의

- `--from` 없이 실행하면 **실제 Claude Code 세션이 뜬다.** 토큰을 쓴다.
  기본 모델이 가장 싼 것으로 잡혀 있고 프롬프트는 슬래시 커맨드 하나뿐이다.
- 베이스라인은 **같은 방식으로 측정한 것과만** 비교한다. 모델이 다르면 토큰 회계가 다르다.
- 컨설팅에서는 before를 **개입 전에** 찍어야 한다. 나중에 재현할 수 없다.
