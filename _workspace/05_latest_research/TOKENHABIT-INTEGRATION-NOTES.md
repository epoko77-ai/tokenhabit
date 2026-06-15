# tokenhabit v1.2 통합: 2026년 최신 기능 낭비 패턴

## 이번 분석으로 새로 발견된 항목 (기존 tokensave와 직교)

### tokensave (설계자 렌즈)
- 모델 오배분 (Opus 99%)
- 멀티에이전트 구성 최적화
- 프롬프트 캐싱

### tokenhabit (운전자 렌즈) ← **새로운 영역**
- 사용자의 **무의식적 행동**이 토큰을 새게 하는 방식
- 각 행동 → 토큰 누출 메커니즘 → 구체적 해결책

---

## tokenhabit v1.2에 통합할 13개 신규 패턴

| # | 기능 | 진단 포인트 | 해결 명령 |
|---|------|---------|---------|
| 1 | Subagents | `/agents` 출력에서 "필요 없는 거" | `/agents` + 제거 |
| 2 | MCP 서버 | `/mcp` + "Unused" 표시 | 미사용 제거 |
| 3 | Skills | 30개 이상, description 길다 | `/memory` + 최적화 |
| 4 | Plan/Compact | `/context` 미실행 습관 | `/context` → `/compact` flow |
| 5 | Thinking | `alwaysThinkingEnabled=true` | settings에서 false로 |
| 6 | 1M Context | 3주 한 세션, 초반 지시 무시 | 주간 `/compact` |
| 7 | Background | `Working` 5개+, 순차 작업 | `/agents` 정리 |
| 8 | 이미지 | 같은 스크린샷 3회+ | 첫 첨부 후 참조만 |
| 9 | WebSearch | 같은 쿼리 반복, 캐시 모름 | 결과 재사용 습관 |
| 10 | Output | 간단한 작업에 설명 2,000토큰 | `/style minimal` |
| 11 | Hooks | 매 호출 500자 context | additionalContext 최소화 |
| 12 | MEMORY.md | 250줄+, 3개월 옛 메모 | 월간 정리, 50줄 유지 |
| 13 | Plugins | 6개+, 필요 없는 것 로드 | enabledPlugins 선택 |

---

## 측정 어댑터 (habit_scan.py 확장)

```python
# 신규 진단 함수
def check_subagent_waste():
    # /agents 출력 파싱 → background session 수
    return count > 3  # 3개 초과 = 과다

def check_mcp_bloat():
    # /mcp 출력 또는 settings.json
    return unused_servers >= 5

def check_skill_context():
    # ~/.claude/skills/ 스캔
    # description 평균 길이, 개수
    return (count > 30) or (avg_desc_length > 200)

def check_context_size():
    # current session context window
    # /context의 token sum
    return tokens > 150000

def check_thinking_enabled():
    # settings.json
    # env.CLAUDE_CODE_EXPERIMENTAL_THINKING
    return thinking_always_on

def check_session_age():
    # session 생성 시간 → 1주일 이상?
    return age_days > 7

def check_background_tasks():
    # /agents 또는 process tracking
    return working_count > 5

def check_image_reuse():
    # transcript에서 같은 image 반복 도수
    # [image] 태그 중복 검출
    return duplicates > 2

def check_websearch_dup():
    # transcript의 search_web calls 중복도
    return same_query_ratio > 0.3

def check_output_verbosity():
    # 최근 10개 메시지의 평균 output length
    return avg_output_tokens > 800

def check_hook_context():
    # settings.json hooks → additionalContext 길이
    return sum_context_chars > 2000

def check_memory_size():
    # ~/.claude/projects/*/memory/MEMORY.md 라인 수
    return lines > 200

def check_plugin_count():
    # settings.json enabledPlugins
    return enabled_count > 5
```

---

## 진단 등급 (habit_catalog.md 확장)

### S1 — Critical (즉시 수정, 50% 영향)
- alwaysThinkingEnabled=true
- Subagent 5개+
- Context 500K+ (응답 30초 이상)

### S2 — High (주간 수정, 30% 영향)
- Plan/Compact 미사용 (context 150K)
- MCP 10개+ 미사용
- 1개월 한 세션

### S3 — Medium (월간 검토, 10% 영향)
- Skills 30개+
- Background task 5개+
- MEMORY.md 250줄+

### S4 — Minor (습관 개선, 5% 영향)
- 이미지 반복
- WebSearch 중복
- Output 과장
- Hooks context
- Plugins 6개+

---

## 모니터링 후킹 (hook_check.py 확장)

```python
# UserPromptSubmit hook에서
def diagnose_latest_habits():
    """
    사용자가 새 메시지 보낼 때마다
    가장 최근의 13개 패턴 스캔
    """
    checks = [
        check_subagent_waste(),
        check_mcp_bloat(),
        check_skill_context(),
        check_context_size(),
        check_thinking_enabled(),
        # ... 13개 모두
    ]
    
    critical = [c for c in checks if c.severity in ['S1']]
    
    if critical:
        # 시스템 메시지로 알림
        # "Subagent 5개는 과다입니다" 등
        return {
            "systemMessage": format_findings(critical),
            "continue": True
        }
```

---

## 교육 자료 (session_coach_checklist.md 확장)

```markdown
# 세션 체크리스트 (사용자 매뉴얼)

## 세션 시작 (5분)
- [ ] `/effort medium` 확인
- [ ] `/agents` → 불필요 background 제거
- [ ] `/mcp` → 미사용 서버 확인

## 세션 중 (매 1시간마다)
- [ ] `/context` 실행 → "150K 이상?" 확인
- [ ] Thinking 켜졌나? (settings 재확인)
- [ ] WebSearch 중복 있나? (transcript 훑기)

## 세션 종료 (5분)
- [ ] Context 150K 이상? → `/compact` 실행
- [ ] 1주일 이상? → 새 세션 고려
- [ ] MEMORY.md 정리 필요? → `/memory` 확인

## 주간 정리 (30분)
- [ ] MEMORY.md 200줄 유지
- [ ] Skill 중복 제거
- [ ] Hook additionalContext 점검
- [ ] Plugin enabledPlugins 검토
```

---

## 다음 단계

1. **tokenhabit v1.2 릴리스** (이번 주)
   - 13개 패턴 추가
   - habit_scan.py 확장
   - hook_check.py 업데이트

2. **사용자 피드백** (2주)
   - 어떤 패턴이 가장 자주 감지되는가?
   - 진단 정확도?

3. **tokensave + tokenhabit 통합** (3주)
   - 설계자 렌즈 (tokensave) + 운전자 렌즈 (tokenhabit) 결합
   - 단일 "token health" dashboard

---

**이 분석 자료 위치:**
- 상세 분석: `/Users/epoko77_m5/token-save-2/token-habit-analysis-2026.md` (1,240줄)
- 종합 진단: `/Users/epoko77_m5/token-save-2/RESEARCH-2026-LATEST-TOKEN-WASTE-PATTERNS.md` (824줄)
- 통합 노트: 이 파일

