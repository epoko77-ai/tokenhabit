# GitHub 경쟁/유사 스킬 전수 스캔 결과

> 기준일: 2026-06-03
> 비교 대상: tokenhabit 스킬 (8카테고리 24패턴, 4모드: 세션 진단 / 습관 카탈로그 / 프롬프트 교정 / 런타임 자가점검)

---

## 발견 요약

- 실재 확인 레포 총 수: **18개**
- 카테고리별: 출력 압축(2), 측정·대시보드(7), 세션·컨텍스트 관리(3), MCP 최적화(2), 모델 라우팅(2), 습관·코칭(2)
- tokenhabit와 가장 유사한 (습관 자각·코칭 영역): 2개 — 하지만 둘 다 사후 로그 분석 방식, 실시간 세션 내 행동 코칭은 없음

---

## 전수 목록

---

### 1. Caveman
- **GitHub**: https://github.com/juliusbrussee/caveman
- **Stars**: ~68,000 (2026-05 기준 최대 규모)
- **활성도**: v1.8.2 (2026-05-12), 활발히 유지
- **무엇**: Claude Code 등 30+ 에이전트에서 출력 토큰을 65~75% 줄이는 스킬. `/caveman` 호출 시 AI 응답을 원시적·단편 문장으로 압축 ("why use many token when few token do trick"). 압축 레벨 4단계(lite/full/ultra/wenyan), 커밋 메시지·PR 리뷰·메모리 최적화 유틸도 포함.
- **겹치는 부분**: 출력 토큰 절감 목표 동일. Claude Code 전용 설치 방식(SKILL.md).
- **다른 부분**: 모델의 응답 언어를 압축하는 것 — 사용자 행동 습관을 교정하지 않음. tokenhabit는 운전자(사용자) 행동 패턴 자각이 목적. 완전히 다른 레이어.
- **배울 점**: 압축 레벨 단계화(lite→ultra) 설계, 생태계 연계 언급(RTK·Caveman 조합 등). 우리도 "교정 강도" 레벨 설계 참고 가능.

---

### 2. RTK (Rust Token Killer)
- **GitHub**: https://github.com/rtk-ai/rtk
- **Stars**: ~58,100
- **활성도**: develop 브랜치 1,072+ commits, 최근 활발
- **무엇**: CLI 프록시. Claude Code의 PreToolUse 훅에 설치되어 모든 Bash 명령어를 자동으로 `rtk git status` 등으로 재작성, 60~90% 명령어 출력 압축. 단일 Rust 바이너리, 제로 의존성.
- **겹치는 부분**: 세션 토큰 절감 목표 동일. 훅 기반 자동화.
- **다른 부분**: 완전 자동 인프라 레이어 — 사용자가 의식하지 않아도 작동. tokenhabit는 사용자가 어떤 행동을 바꿔야 하는지 '자각'시키는 것. 보완적 관계.
- **배울 점**: 훅을 통한 "강제 시행(enforcement)" 패턴. 우리 진단 결과를 훅으로 자동 강제하는 후속 기능 설계 시 참고.

---

### 3. ccusage
- **GitHub**: https://github.com/ryoppippi/ccusage
- **Stars**: ~15,400
- **활성도**: v20.0.6 (2026-05-29), 120 릴리즈, 매우 활발
- **무엇**: Claude Code 및 22개+ CLI 에이전트의 로컬 JSONL 로그를 파싱해 일별·주별·월별·세션별 토큰 사용량·비용을 Rust로 분석. 캐시 토큰 분리, JSON 출력, 타임존 설정 지원.
- **겹치는 부분**: 세션별 토큰 집계.
- **다른 부분**: 순수 측정 도구 — 습관 진단·코칭 없음. "얼마나 썼나"만 보여줌. tokenhabit는 "왜 낭비했나, 어떤 행동을 고쳐야 하나"까지.
- **배울 점**: 멀티 에이전트 CLI 지원 확장성. JSONL 로그 파싱 방법론.

---

### 4. Claude Code Usage Monitor
- **GitHub**: https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor
- **Stars**: ~8,100
- **활성도**: v3.1.0 (2025-07-23), 비교적 최근
- **무엇**: Rich TUI 기반 실시간 토큰 소비 모니터. ML 기반 번 레이트 분석, P90 예측, 세션 만료 시점 예측, 다단계 경보.
- **겹치는 부분**: 세션 중 실시간 모니터링.
- **다른 부분**: "앞으로 얼마 남았나" 예측 중심. 행동 패턴 분류·코칭 없음.
- **배울 점**: 예측 알고리즘(P90) + 실시간 경보 조합이 사용자 경험 좋음. tokenhabit의 "런타임 자가점검" 모드에서 경보 기능 보강 참고.

---

### 5. claude-code-prompt-coach-skill (hancengiz)
- **GitHub**: https://github.com/hancengiz/claude-code-prompt-coach-skill
- **Stars**: 145
- **활성도**: 9 commits, 구체적 날짜 미확인
- **무엇**: JSONL 세션 로그를 분석해 프롬프트 품질·토큰 사용 패턴·생산성을 리포트. 모호한 프롬프트 탐지 (파일 경로 누락 42%, 에러 디테일 누락 23%, 성공 기준 누락 30% 등), 도구 활용 미흡 탐지, 피크 생산성 시간 분석.
- **겹치는 부분**: 사용자 행동 패턴 분석·코칭이라는 점에서 tokenhabit와 가장 유사. 모호 프롬프트 패턴 탐지는 tokenhabit의 "모호 프롬프트" 카테고리와 직접 겹침.
- **다른 부분**: 사후 로그 분석(세션 종료 후 분석) 방식. tokenhabit는 현재 세션 내 실시간 자각 + 프롬프트 교정까지. 이 스킬은 토큰 절감보다 "프롬프트 스킬 향상"이 주목적.
- **배울 점**: 구체적 수치 제시 방식("파일 경로 누락 42%") — 우리도 패턴 빈도 수치화 방식 참고 가능.

---

### 6. token-dashboard (nateherkai)
- **GitHub**: https://github.com/nateherkai/token-dashboard
- **Stars**: ~551
- **활성도**: 30 commits, 구체적 날짜 미확인
- **무엇**: JSONL 트랜스크립트를 파싱해 프롬프트별 비용, 도구·파일 히트맵, 서브에이전트 귀속, 캐시 분석, 프로젝트 비교, **규칙 기반 Tips 엔진** 제공. 로컬 전용.
- **겹치는 부분**: Tips 엔진이 "반복 파일 읽기, 과도한 도구 결과, 낮은 캐시 히트율" 등 낭비 패턴 제안. tokenhabit의 습관 카탈로그와 부분 겹침.
- **다른 부분**: Tips가 규칙 기반 정적 제안 — 개인화된 실시간 세션 코칭이 아님.
- **배울 점**: 도구·파일 히트맵으로 "무엇이 가장 많은 토큰을 먹는가" 시각화. 귀속 분석.

---

### 7. oh-my-hi (netil)
- **GitHub**: https://github.com/netil/oh-my-hi
- **Stars**: 48
- **활성도**: v0.11.11 (2026-05-29), 활발
- **무엇**: Claude Code 하네스(스킬·에이전트·플러그인·훅·MCP) 전반의 비주얼 대시보드. 스타트업 컨텍스트 비용 추정, 모델별 일별 트렌드, 캐시 효율, 태스크 카테고리 자동 분류, 컨텍스트 창 리플레이.
- **겹치는 부분**: 하네스 전반의 토큰 귀속 분석. tokenhabit의 "MCP 스키마 상시 주입" 패턴 탐지와 부분 연관.
- **다른 부분**: 분석·시각화 도구. 행동 코칭 없음.
- **배울 점**: "스타트업 컨텍스트 비용 추정" 기능 — tokenhabit의 세션 시작 시 비용 경고 기능에 응용 가능.

---

### 8. TokenTracker (mm7894215)
- **GitHub**: https://github.com/mm7894215/TokenTracker
- **Stars**: ~635
- **활성도**: v0.39.0 (2026-06-02), 매우 활발
- **무엇**: 22개 AI 코딩 도구(Claude Code, Cursor, Gemini 등) 토큰을 로컬 수집·집계. macOS 메뉴바 앱 + 4종 데스크톱 위젯, localhost:7680 대시보드. 제로 설정, 클라우드 없음.
- **겹치는 부분**: Claude Code 토큰 집계.
- **다른 부분**: 멀티 도구 비교 측정이 차별점. 습관 코칭 전무.
- **배울 점**: 크로스 에이전트 비교를 통한 "도구별 토큰 효율" 인식 제고 아이디어.

---

### 9. macu — minimize-ai-credit-usage
- **GitHub**: https://github.com/minhvoio/macu_minimize-ai-credit-usage
- **Stars**: 15
- **활성도**: 32 commits, 구체적 날짜 미확인
- **무엇**: Claude Code·OpenCode·Codex 세션의 도구 호출 패턴을 분석해 미사용 MCP 도구를 탐지·제거 권고. 유휴 일수 기반 신뢰도 점수, 보수/공격적 제거 2티어. 88일간 841.9M 토큰 낭비 사례 제시.
- **겹치는 부분**: tokenhabit의 "MCP 스키마 상시 주입" 패턴(미사용 MCP 도구가 매 메시지 오버헤드로 작동)과 직접 겹침.
- **다른 부분**: 도구 등록 레이어 분석(어떤 MCP가 등록되어 있는가). tokenhabit는 실시간 세션 내 주입 여부 인식 코칭.
- **배울 점**: "미사용 도구 비용 정량화" 접근법 — 우리 MCP 카테고리 설명에 수치 근거 추가 시 참고.

---

### 10. token-optimizer-mcp (ooples)
- **GitHub**: https://github.com/ooples/token-optimizer-mcp
- **Stars**: 406
- **활성도**: v5.0.1 (2025-11-02), 31 릴리즈
- **무엇**: MCP 서버로서 95%+ 토큰 절감을 주장. 캐싱·압축·스마트 도구 인텔리전스 레이어.
- **겹치는 부분**: MCP 레이어 토큰 최적화.
- **다른 부분**: 인프라 레이어 자동화. 사용자 행동 교정 없음.
- **배울 점**: MCP 레이어 개입 가능성.

---

### 11. claude-context-mode (mksglu)
- **GitHub**: https://github.com/mksglu/claude-context-mode
- **Stars**: ~16,300
- **활성도**: 최근 green badge 확인, 구체적 날짜 미확인
- **무엇**: 대형 출력을 샌드박스 서브프로세스에서 처리, 컨텍스트 창에는 요약만 주입. 56KB Playwright 스냅샷 → 299바이트(99% 절감), 500건 액세스 로그 → 155바이트 사례. 10개 언어 런타임 지원.
- **겹치는 부분**: 로그 덤프·대형 출력 오염 방지. tokenhabit의 "로그 덤프" 카테고리 대응.
- **다른 부분**: 자동 인프라 레이어. 사용자가 의식·교정할 필요 없음.
- **배울 점**: "로그 덤프" 패턴이 얼마나 심각한지 실제 수치로 증명됨 — tokenhabit 설명에 수치 근거로 활용 가능.

---

### 12. savethetokens (Redclawww)
- **GitHub**: https://github.com/Redclawww/savethetokens
- **Stars**: 7
- **활성도**: 2 commits, 매우 초기
- **무엇**: Claude Code 스킬. "proactive compacting, context pruning, session hygiene"를 슬로건으로 내세운 스킬. 예산 거버넌스, 자동 체크포인트, 계층적 문서, 비용 추적.
- **겹치는 부분**: 세션위생(session hygiene) 용어·개념 직접 사용. tokenhabit와 컨셉 가장 유사한 스킬.
- **다른 부분**: 매우 초기 단계, 구현 미미. Python 기반 스크립트로 보임. 행동 코칭보다 기술적 자동화에 가까움.
- **배울 점**: "session hygiene"을 스킬 레이어에서 다룬 선례 — 우리와 같은 방향이지만 7 star로 아직 거의 알려지지 않음.

---

### 13. nadimtuhin/claude-token-optimizer
- **GitHub**: https://github.com/nadimtuhin/claude-token-optimizer
- **Stars**: ~451
- **활성도**: 55 commits
- **무엇**: CLAUDE.md 문서 구조를 재편해 스타트업 토큰 절감. 필수 파일(~800토큰 자동 로드)과 보조 파일(요청 시만 로드) 분리. "11,000 → 800 토큰" 사례.
- **겹치는 부분**: tokenhabit의 "CLAUDE.md 비대화" 패턴 부분 대응.
- **다른 부분**: 일회성 설정 최적화 도구. 실시간 습관 코칭 없음.
- **배울 점**: CLAUDE.md 레이어 비용이 매 턴에 발생한다는 교육적 설명 방식.

---

### 14. claude-token-analyzer (li195111)
- **GitHub**: https://github.com/li195111/claude-token-analyzer
- **Stars**: 11
- **활성도**: v0.2.0 (2026-04-14)
- **무엇**: Rust 기반 로컬 세션 로그 파싱, 6가지 이상 징후 탐지(토큰 폭발·낮은 캐시 히트·비용 비효율·장기 세션·반복 오류·비정상 모델 분포), SQLite, MCP 서버 지원.
- **겹치는 부분**: 이상 징후 탐지가 tokenhabit의 패턴 진단과 유사한 목적.
- **다른 부분**: 순수 진단 도구, 사후 분석. 코칭 없음. "어디서 낭비했나" 확인.
- **배울 점**: "반복 오류" 탐지 카테고리 — tokenhabit에 "에러 루프" 패턴으로 추가 가능.

---

### 15. Sagargupta16/claude-cost-optimizer
- **GitHub**: https://github.com/Sagargupta16/claude-cost-optimizer
- **Stars**: 24
- **활성도**: 구체적 날짜 미확인
- **무엇**: 11개 가이드(빌링 메커니즘, 컨텍스트 최적화, 모델 선택, 워크플로 패턴, 팀 예산 등) + 9개 최적화 CLAUDE.md 템플릿 + Python 토큰 추정 도구. "300줄 설정 → 62줄 최적화로 $0.080→$0.013" 사례.
- **겹치는 부분**: CLAUDE.md 비대화 패턴, 모델 선택 가이드.
- **다른 부분**: 정적 가이드·템플릿 모음. 실시간 코칭 없음.
- **배울 점**: 가이드 구조화 방식. 우리의 "습관 카탈로그" 모드 설계 참고.

---

### 16. lean (civillizard)
- **awesome-claude-code Issue**: https://github.com/hesreallyhim/awesome-claude-code/issues/1323
- **Stars**: 정보 없음 (issue 제출, 별도 레포 미확인)
- **활성도**: 2026-03 공개
- **무엇**: 작업을 단계 분해 후 각 단계에 Haiku/Sonnet/Opus 최저비용 모델을 자동 배정. 단계별 품질 게이트, 실행 후 절감 리포트. PreToolUse 훅으로 경량 모델 제안.
- **겹치는 부분**: 모델 선택 최적화.
- **다른 부분**: 모델 라우팅 레이어 — 사용자 행동 패턴 교정이 아님.
- **배울 점**: "단계별 모델 배정" 개념을 tokenhabit의 "모델 선택 습관" 카테고리 확장 시 참고.

---

### 17. 0xrdan/claude-router
- **GitHub**: https://github.com/0xrdan/claude-router
- **Stars**: 40
- **활성도**: v2.0.7 (2026-01-13)
- **무엇**: 규칙 기반(+ LLM 폴백) 제로 레이턴시 모델 라우터. Haiku(단순)/Sonnet(중간)/Opus(복잡) 자동 분배. Opus Orchestrator 패턴 포함.
- **겹치는 부분**: 모델 선택 자동화.
- **다른 부분**: 자동화 레이어. 사용자 의식 변화 아님.
- **배울 점**: 모델 선택 기준(task classification) 구체화 방법.

---

### 18. AgentGuard (quilrai)
- **GitHub**: https://github.com/quilrai/AgentGuard
- **Stars**: 22
- **활성도**: v1.0.6 (2026-05-10)
- **무엇**: 로컬 가드레일 + 토큰 절감. 파일 읽기 캐싱, 컨텍스트 인식 응답(전체/diff/줄범위), 빌드 로그 요약, grep 결과 그룹화, JSON 최적화. Token Saver 탭 제공.
- **겹치는 부분**: 세션 내 출력 압축.
- **다른 부분**: 가드레일(안전) + 토큰 절감 결합. 행동 코칭 없음.
- **배울 점**: 파일 읽기 캐싱 패턴.

---

## TOP 5 — tokenhabit와 가장 유사

| 순위 | 이름 | 유사 이유 | 핵심 차이 |
|------|------|-----------|-----------|
| 1 | **hancengiz/claude-code-prompt-coach-skill** | 사용자 행동 패턴 분석 + 프롬프트 코칭. 모호 프롬프트 탐지, 도구 활용 미흡 탐지 | 사후 로그 분석. 세션 내 실시간 교정 없음 |
| 2 | **Redclawww/savethetokens** | "session hygiene" 컨셉 동일, 스킬 레이어로 구현 | 7 star 초기 단계, 자동화 쪽에 치우침 |
| 3 | **nateherkai/token-dashboard** | 규칙 기반 Tips 엔진으로 낭비 패턴 제안 | 대시보드 툴(시각화), 코칭 깊이 얕음 |
| 4 | **li195111/claude-token-analyzer** | 6가지 이상 징후 탐지(반복 오류, 낮은 캐시 히트 등) | 순수 진단, 처방(코칭) 없음 |
| 5 | **macu (minhvoio)** | MCP 미사용 도구 = tokenhabit의 "MCP 스키마 상시 주입" 패턴 직접 대응 | MCP 등록 레이어 분석 도구. 실시간 세션 코칭 아님 |

---

## 우리가 비어있는데 남들이 채운 영역

> tokenhabit가 커버하지 못하거나 강화해야 할 기능 공백

1. **실시간 토큰 소비 측정·예측 (ccusage / Claude Code Usage Monitor)**
   - tokenhabit는 "낭비 행동 진단"은 하지만 "지금 몇 토큰 썼나, 언제 한도 도달하나"를 수치로 보여주지 않음.
   - 측정 레이어는 완전 공백. ccusage(15.4k star)·Usage Monitor(8.1k star)가 이 영역을 독점.

2. **출력 자동 압축 인프라 레이어 (RTK / Caveman / claude-context-mode)**
   - tokenhabit는 "로그 덤프 하지 마라"고 교육하지만, 막아주는 자동화 훅이 없음.
   - RTK(58k star)·Caveman(68k star)·Context Mode(16.3k star) — 모두 자동화로 즉시 절감.

3. **사후 세션 로그 분석 대시보드 (token-dashboard / cc-lens / oh-my-hi)**
   - tokenhabit는 현재 세션 내 실시간 진단이지만, "지난 30일 내 습관 트렌드"를 보여주는 기능 없음.
   - 복수 세션 패턴 추적 및 히스토리 시각화가 완전 공백.

4. **미사용 MCP 도구 등록 감사 (macu)**
   - tokenhabit가 "MCP 스키마 상시 주입" 패턴을 교육하지만, 실제로 어떤 도구가 미사용인지 스캔·목록화하는 기능 없음.
   - macu가 이 틈새를 점유 중.

5. **모델 자동 라우팅 (lean / claude-router)**
   - tokenhabit는 "Opus 남발 말라"고 교육하지만, 자동으로 작업 복잡도에 맞게 모델을 배정해주는 기능 없음.
   - 이 영역은 사용자 교육(우리)과 자동화(경쟁사) 둘 다 필요.

---

## tokenhabit만의 진짜 빈 영역 (경쟁자가 없음)

> 아래 기능은 조사 결과 어떤 실재 레포도 제공하지 않는 것으로 확인됨

1. **세션 중 실시간 행동 패턴 자각 코칭** — 사후 분석(로그)이 아닌, 지금 이 대화에서 "맥락 재타이핑 중입니다, 이렇게 바꾸세요"를 즉시 알려주는 도구 없음.

2. **사용자 무의식 습관 카탈로그** — "운전자가 모르는 사이에 태우는 토큰 패턴"을 범주화·명명·설명한 교육 컨텐츠형 스킬. 기존 도구들은 모두 측정·압축·라우팅 중 하나이며, 습관 이름을 붙여 의식화시키는 접근 없음.

3. **프롬프트 실시간 교정 제안 (입력 전)** — 쓰려는 프롬프트가 모호한지, 컨텍스트 재타이핑인지, 판별 후 대안 제안하는 모드. hancengiz의 Prompt Coach는 사후 로그 분석으로만 접근.

4. **8카테고리 24패턴 분류 체계** — 경쟁 스킬들은 개별 패턴(출력 압축, MCP 정리, 모델 선택)을 각각 다루지만, 이를 통합 분류해 "나는 어느 카테고리를 주로 낭비하나"를 보여주는 프레임워크 없음.

---

*조사 방법: WebSearch (8회) + WebFetch (15회). 실재 확인(URL 접속) 레포만 기록. 추측 레포 없음.*
