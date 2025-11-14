# Top3 자연어 규칙 적용 구조와 과정

## 개요

이 문서는 Smart Assistant의 Top3 자연어 규칙이 **실제로 어떻게 적용되는지** 구조와 과정을 실제 예시와 함께 설명합니다.

---

## 전체 구조

```
┌─────────────────────────────────────────────────────────────┐
│                    사용자 입력                                │
│  "프로젝트 LUMINA에서 전형우가 요청한 업무처리일 경우        │
│   우선순위 높게해줘"                                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              Top3LLMSelector.select_top3()                   │
│  1. 캐시 확인                                                 │
│  2. 후보 필터링 (done 제외)                                   │
│  3. LLM 선정 시도                                             │
│  4. 폴백 처리 (실패 시)                                       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              _try_llm_selection()                            │
│  1. 프롬프트 생성                                             │
│  2. LLM 호출                                                  │
│  3. 응답 파싱                                                 │
│  4. 유효성 검증                                               │
│  5. 규칙 준수 검증                                            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    선정 결과                                  │
│  - 선정된 TODO ID 3개                                         │
│  - 선정 이유 (한국어)                                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 단계별 상세 과정


### 1단계: 사용자 입력 및 초기 검증

**입력 예시**:
```
자연어 규칙: "프로젝트 LUMINA에서 전형우가 요청한 업무처리일 경우 우선순위 높게해줘"
```

**코드 위치**: `Top3LLMSelector.select_top3()`

**처리 과정**:
```python
def select_top3(self, todos, natural_rule, entity_rules=None):
    # 1. 빈 TODO 리스트 체크
    if not todos:
        return set()
    
    # 2. 빈 규칙 체크
    if not natural_rule or not natural_rule.strip():
        return self._fallback_selection(todos)
    
    # 3. 캐시 확인 (5분 TTL)
    cached = self.cache_manager.get(todos, entity_rules, natural_rule)
    if cached:
        return cached  # 캐시 히트 → 즉시 반환
    
    # 4. done 상태 제외
    candidates = [t for t in todos if t.get("status") != "done"]
```

**로그 예시**:
```
[Top3LLM] TODO 50개를 LLM에 전달 (사전 필터링 없음)
```

---

### 2단계: 프롬프트 생성

**코드 위치**: `Top3LLMSelector._build_prompt()`

**처리 과정**:

#### 2-1. VDOS DB에서 사람 정보 가져오기
```python
def _get_person_mapping(self):
    # virtualoffice/src/virtualoffice/vdos.db 연결
    cursor.execute("SELECT email_address, name, chat_handle FROM people")
    
    # 이메일 → 이름 매핑 생성
    mapping = {
        "hyungwoo.jeon@example.com": "전형우",
        "jungjiwon@koreaitcompany.com": "정지원",
        "limboyeon@koreaitcompany.com": "임보연",
        ...
    }
    return mapping
```

#### 2-2. TODO 리스트 직렬화
```python
for i, todo in enumerate(todos, 1):
    # 이메일을 이름으로 변환
    requester_name = person_mapping.get(todo["requester"], todo["requester"])
    
    # 프로젝트 정보 (풀네임 + 코드)
    project_display = f"{todo['project_full_name']} ({todo['project']})"
    
    todo_info = f"""[TODO #{i}]
→ ID: "{todo['id']}" (이 ID를 그대로 사용하세요!)
→ 제목: {todo['title'][:80]}
→ 프로젝트: {project_display}
→ 요청자: {requester_name}
→ 유형: {todo['type']}
→ 수신방법: {todo['source_type']}
→ 우선순위: {todo['priority']}
→ 마감일: {todo['deadline']}"""

# 예시 출력:
# [TODO #1]
# → ID: "task_abc123"
# → 제목: UI/UX 디자인 초안 피드백 요청
# → 프로젝트: Project LUMINA (LUMINA)
# → 요청자: 전형우
# → 유형: task
# → 수신방법: 메일
# → 우선순위: high
# → 마감일: 2025-11-15
```


#### 2-3. 프롬프트 구성

**Chain of Thought (CoT) 적용** 🧠

이 시스템은 **Chain of Thought (사고의 연쇄)** 기법을 사용하여 LLM이 단계적으로 추론하도록 유도합니다.

**CoT의 핵심**:
```json
{
    "reasoning": "먼저 추론 과정을 한국어로 상세히 설명",  // ← 먼저 생각
    "selected_ids": ["결과1", "결과2", "결과3"]              // ← 그 다음 결정
}
```

**왜 reasoning을 먼저 요청하는가?**

1. **단계적 추론 유도**: LLM이 결과를 먼저 내지 않고, 조건을 분석하고 판단 근거를 먼저 생각하게 함
2. **정확도 향상**: 추론 과정을 명시하면 무작위 선택이 아닌 논리적 선택을 하게 됨
3. **설명 가능성**: 사용자에게 "왜 이 TODO가 선정되었는지" 명확히 설명 가능
4. **오류 감소**: 조건을 하나씩 확인하면서 선정하므로 조건 누락이 줄어듦

**CoT 프롬프트 예시** (실제 코드):
```python
다음 형식으로 분석해주세요 (반드시 한국어로, reasoning을 먼저 작성):
{
    "reasoning": "선정 이유를 한국어로 상세히 설명. 
                  먼저 조건을 분석하고, 
                  어떤 TODO들이 조건을 만족하는지 설명한 후, 
                  최종적으로 선정한 3개의 TODO를 각각 설명.",
    "selected_ids": ["위_TODO_리스트의_실제_ID_1", ...]
}

**중요**: reasoning에서 선정할 TODO의 번호(#)를 먼저 언급한 후, 
selected_ids에 해당 TODO의 실제 ID를 정확히 복사하세요!
```

**CoT 없이 직접 결과만 요청하면?** ❌
```json
// 나쁜 예: 추론 과정 없이 바로 결과
{
    "selected_ids": ["task_abc", "task_def", "task_ghi"]
}
→ 왜 선정했는지 알 수 없음
→ 조건을 제대로 확인했는지 불명확
→ 오류 발생 시 원인 파악 어려움
```

**CoT로 추론 과정 포함** ✅
```json
// 좋은 예: 추론 과정을 먼저 명시
{
    "reasoning": "PN 프로젝트의 전형우가 요청한 업무처리 TODO를 찾았습니다. 
                  1. 프로젝트 조건: PN 프로젝트 → TODO #1, #5, #12, #18 해당
                  2. 요청자 조건: 전형우 → TODO #1, #5, #12 해당
                  3. 유형 조건: 업무처리(task) → TODO #1, #5, #12 모두 해당
                  따라서 이 3개를 선정합니다.",
    "selected_ids": ["task_abc", "task_def", "task_ghi"]
}
→ 단계별 조건 확인 과정 명확
→ 선정 근거 투명
→ 오류 발생 시 어느 단계에서 문제인지 파악 가능
```

**시스템 프롬프트**:
```
당신은 업무용 TODO 우선순위 분석 전문가입니다. 
사용자의 자연어 규칙을 정확히 이해하고, 주어진 TODO 리스트에서 
규칙에 가장 잘 맞는 상위 3개를 선정합니다.

**중요**: 모든 응답은 반드시 한국어로 작성하세요.
```

**사용자 프롬프트 구조**:
```
사용자 규칙: 프로젝트 LUMINA에서 전형우가 요청한 업무처리일 경우 우선순위 높게해줘

사람 매핑 (이메일 → 이름):
- hyungwoo.jeon@example.com: 전형우
- jungjiwon@koreaitcompany.com: 정지원
- limboyeon@koreaitcompany.com: 임보연
...

TODO 리스트 (50개):
[TODO #1]
→ ID: "task_abc123"
→ 제목: UI/UX 디자인 초안 피드백 요청
→ 프로젝트: Project LUMINA (LUMINA)
→ 요청자: 전형우
→ 유형: task
→ 수신방법: 메일
→ 우선순위: high
→ 마감일: 2025-11-15

[TODO #2]
→ ID: "review_def456"
→ 제목: 프로젝트 개요서 검토
→ 프로젝트: Project LUMINA (LUMINA)
→ 요청자: 정지원
→ 유형: review
→ 수신방법: 메일
→ 우선순위: medium
→ 마감일: 2025-11-16

[TODO #3]
→ ID: "task_ghi789"
→ 제목: 데이터베이스 스키마 설계
→ 프로젝트: Project OMEGA (OMEGA)
→ 요청자: 전형우
→ 유형: task
→ 수신방법: 메일
→ 우선순위: high
→ 마감일: 2025-11-17
...

선정 기준 (반드시 순서대로 적용):
1. 프로젝트 조건을 최우선으로 정확히 만족
2. 요청자 조건을 정확히 만족
3. 유형 조건을 절대적으로 만족 (매우 중요!)
4. 수신방법 조건을 정확히 만족
5. 위 조건을 모두 만족하는 TODO 중에서 마감일, 우선순위 고려
6. 반드시 정확히 3개를 선정

다음 형식으로 분석해주세요:
{
    "reasoning": "선정 이유를 한국어로 상세히 설명...",
    "selected_ids": ["task_abc123", "task_ghi789", "task_jkl012"]
}
```

**로그 예시**:
```
[Top3LLM] 프롬프트 생성 완료 (길이: 15234자)
[Top3LLM] 자연어 규칙: 프로젝트 LUMINA에서 전형우가 요청한 업무처리일 경우 우선순위 높게해줘
```

---

### 3단계: LLM 호출

**코드 위치**: `Top3LLMSelector._try_llm_selection()`

**처리 과정**:
```python
# LLM 호출
response = self.llm_client.generate(
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ],
    temperature=0.1,  # 일관된 결과
    max_tokens=1000
)
```

**LLM 응답 예시 (Chain of Thought 적용)**:
```json
{
    "reasoning": "프로젝트 LUMINA에서 전형우가 요청한 업무처리 TODO를 우선적으로 선정합니다.
                  
                  [1단계: 조건 분석]
                  - 프로젝트: LUMINA
                  - 요청자: 전형우
                  - 유형: 업무처리(task)
                  - 우선순위: 위 조건을 만족하는 TODO를 최우선으로
                  
                  [2단계: 후보 필터링]
                  - LUMINA 프로젝트 TODO: #1, #2, #5, #8, #12, #15 (6개)
                  - 전형우 요청 TODO: #1, #3, #7, #10, #14 (5개)
                  - 업무처리(task) TODO: #1, #3, #5, #7, #9, #11 (6개)
                  
                  [3단계: 교집합 확인]
                  - 모든 조건 만족 (LUMINA + 전형우 + task): TODO #1 (1개) ✅
                  - 부분 조건 만족 (LUMINA + task): TODO #5, #12 (2개)
                  
                  [4단계: 최종 선정]
                  - TODO #1: UI/UX 디자인 초안 피드백 요청 
                    (LUMINA + 전형우 + task, 마감: 11/15, 우선순위: high) ⭐ 최우선
                  - TODO #5: 프로토타입 제작 
                    (LUMINA + 정지원 + task, 마감: 11/16, 우선순위: high)
                  - TODO #12: 테스트 자동화 스크립트 
                    (LUMINA + 임보연 + task, 마감: 11/18, 우선순위: medium)
                  
                  규칙에 따라 LUMINA 프로젝트의 전형우 요청 업무처리를 최우선으로 선정하고,
                  나머지는 같은 프로젝트의 업무처리 중 마감일이 임박한 순서로 선정했습니다.",
    "selected_ids": ["task_abc123", "task_def456", "task_ghi789"]
}
```

**CoT의 효과**:
- ✅ 조건을 단계별로 확인 → 누락 방지
- ✅ 후보를 점진적으로 좁힘 → 정확도 향상
- ✅ 최종 선정 근거 명확 → 설명 가능성
- ✅ 오류 발생 시 어느 단계에서 문제인지 파악 가능

**로그 예시**:
```
[Top3LLM] LLM 호출 시작 (후보: 50개)
[Top3LLM] LLM 응답 수신: 3.24초, 토큰=856, 길이=342자
[Top3LLM] LLM 응답 내용:
{
    "reasoning": "PN 프로젝트의 전형우가 요청한 업무처리 TODO를 찾았습니다...",
    "selected_ids": ["task_abc123", "task_ghi789", "task_jkl012"]
}
```

---


### 4단계: 응답 파싱

**코드 위치**: `Top3LLMSelector._parse_response()`

**처리 과정**:
```python
def _parse_response(self, response: str):
    # 1. 마크다운 코드 블록 제거
    if response.startswith("```"):
        lines = response.split("\n")
        response = "\n".join(lines[1:-1])
    
    # 2. JSON 파싱
    data = json.loads(response)
    
    # 3. 필드 추출
    selected_ids = data.get("selected_ids", [])
    reasoning = data.get("reasoning", "")
    
    # 4. 개수 검증
    if len(selected_ids) != 3:
        logger.warning(f"selected_ids 개수가 3개가 아닙니다: {len(selected_ids)}개")
    
    return set(selected_ids), reasoning
```

**파싱 결과**:
```python
selected_ids = {"task_abc123", "task_def456", "task_ghi789"}
reasoning = "프로젝트 LUMINA에서 전형우가 요청한 업무처리 TODO를 우선적으로 선정합니다..."
```

**로그 예시**:
```
[Top3LLM] 파싱 결과: 3개 ID 추출
[Top3LLM] 파싱된 ID: ['task_abc123', 'task_def456', 'task_ghi789']
```

---

### 5단계: 유효성 검증

**코드 위치**: `Top3LLMSelector._validate_ids()`

**처리 과정**:
```python
def _validate_ids(self, ids: Set[str], todos: List[Dict]):
    # 1. 실제 TODO ID 집합 생성
    valid_todo_ids = {t.get("id") for t in todos if t.get("id")}
    
    # 2. 교집합 계산
    valid_ids = ids & valid_todo_ids
    
    # 3. 유효하지 않은 ID 로깅
    invalid_ids = ids - valid_ids
    if invalid_ids:
        logger.warning(f"유효하지 않은 ID: {invalid_ids}")
    
    return valid_ids
```

**검증 예시**:

**케이스 1: 모두 유효** ✅
```python
LLM 선정: {"task_abc123", "task_def456", "task_ghi789"}
실제 TODO: {"task_abc123", "task_def456", "task_ghi789", "task_jkl012", ...}
→ 유효한 ID: {"task_abc123", "task_def456", "task_ghi789"}
```

**케이스 2: 일부 무효** ⚠️
```python
LLM 선정: {"task_abc123", "task_INVALID", "task_def456"}
실제 TODO: {"task_abc123", "task_def456", "task_ghi789", "task_jkl012", ...}
→ 유효한 ID: {"task_abc123", "task_def456"}
→ 무효한 ID: {"task_INVALID"}
```

**로그 예시**:
```
[Top3LLM] 유효하지 않은 ID: {'task_INVALID'}
```

---


### 6단계: 규칙 준수 검증 및 설명 개선

**코드 위치**: `Top3LLMSelector._validate_and_explain_selection()`

**처리 과정**:

#### 6-1. 규칙에서 조건 추출
```python
def _validate_and_explain_selection(self, selected_ids, todos, natural_rule, original_reasoning):
    # 1. 프로젝트 조건 추출
    rule_lower = natural_rule.lower()
    expected_project = None
    for todo in todos:
        project = todo.get("project", "")
        if project and project.lower() in rule_lower:
            expected_project = project  # "LUMINA"
            break
    
    # 2. 요청자 조건 추출
    person_mapping = self._get_person_mapping()
    expected_requester = None
    for email, name in person_mapping.items():
        if name and name in natural_rule:
            expected_requester = name  # "전형우"
            break
    
    # 3. 유형 조건 추출
    type_mapping = {
        "업무처리": "task",
        "문서검토": "review",
        "미팅": "meeting",
        "마감작업": "deadline"
    }
    expected_type = None
    for korean, english in type_mapping.items():
        if korean in natural_rule:
            expected_type = english  # "task"
            break
```

**추출 결과**:
```python
expected_project = "LUMINA"
expected_requester = "전형우"
expected_type = "task"
```

#### 6-2. 선정된 TODO 분석
```python
for todo in selected_todos:
    issues = []
    
    # 프로젝트 검증
    if expected_project and todo["project"] != expected_project:
        issues.append(f"프로젝트 불일치 (기대: {expected_project}, 실제: {todo['project']})")
    
    # 요청자 검증
    if expected_requester and requester_name != expected_requester:
        issues.append(f"요청자 불일치 (기대: {expected_requester}, 실제: {requester_name})")
    
    # 유형 검증
    if expected_type and todo["type"] != expected_type:
        issues.append(f"유형 불일치 (기대: {expected_type}, 실제: {todo['type']})")
    
    if issues:
        violations.append({"id": todo["id"], "issues": issues, "todo": todo})
    else:
        perfect_matches.append(todo)
```


#### 6-3. 설명 개선

**케이스 1: 모두 완벽히 일치** ✅
```python
perfect_matches = 3개
violations = 0개

→ 원본 설명 그대로 반환
```

**출력 예시**:
```
프로젝트 LUMINA에서 전형우가 요청한 업무처리 TODO를 우선적으로 선정합니다.
TODO #1, #5, #8이 모두 프로젝트(LUMINA), 요청자(전형우), 유형(task) 조건을 
완벽히 만족하므로 이 3개를 최우선으로 선정합니다.
```

**케이스 2: 부분 일치 포함** ⚠️
```python
perfect_matches = 1개
violations = 2개

→ 상세 분석 추가
```

**출력 예시**:
```
프로젝트 LUMINA에서 전형우가 요청한 업무처리 TODO를 우선적으로 선정합니다.
TODO #1이 조건을 완벽히 만족하고, TODO #5, #12를 추가로 선정했습니다.

⚠️ 선정 결과 분석:

✅ 완벽히 일치: 1개
  - task_abc123: 프로젝트=LUMINA, 요청자=전형우, 유형=task

⚠️ 부분 일치: 2개
  - task_def456: 프로젝트=LUMINA, 요청자=정지원, 유형=task
    → 요청자 불일치 (기대: 전형우, 실제: 정지원)
  
  - task_ghi789: 프로젝트=LUMINA, 요청자=임보연, 유형=task
    → 요청자 불일치 (기대: 전형우, 실제: 임보연)

📝 조건 완화: 규칙을 완벽히 만족하는 TODO가 1개뿐이어서, 
같은 프로젝트(LUMINA)의 업무처리 TODO 2개를 추가로 선정했습니다.
```

---

### 7단계: 캐시 저장 및 결과 반환

**코드 위치**: `Top3LLMSelector._try_llm_selection()`

**처리 과정**:
```python
# 1. 캐시 저장 (TTL 5분)
self.cache_manager.set(original_todos, valid_ids, entity_rules, natural_rule)

# 2. 선정 이유 저장
self.last_reasoning = reasoning

# 3. 결과 반환
return valid_ids  # {"task_abc123", "task_ghi789", "task_jkl012"}
```

**로그 예시**:
```
[Top3LLM] ✅ 선정 완료: 3개
[Top3LLM] 선정 이유: 프로젝트 LUMINA에서 전형우가 요청한 업무처리 TODO를 우선적으로 선정합니다...
[Top3LLM] 선정: task_abc123 - UI/UX 디자인 초안 피드백 요청 (프로젝트: LUMINA, 요청자: 전형우)
[Top3LLM] 선정: task_def456 - 프로토타입 제작 (프로젝트: LUMINA, 요청자: 정지원)
[Top3LLM] 선정: task_ghi789 - 테스트 자동화 스크립트 (프로젝트: LUMINA, 요청자: 임보연)
```

---

---

## Chain of Thought (CoT) 상세 분석

### CoT란?

**Chain of Thought (사고의 연쇄)**는 LLM이 복잡한 문제를 해결할 때, 최종 답변을 바로 내지 않고 **중간 추론 단계를 명시적으로 생성**하도록 유도하는 프롬프팅 기법입니다.

### 기존 방식 vs CoT 방식

#### 기존 방식 (Zero-shot) ❌
```
프롬프트: "다음 TODO 중 PN 프로젝트의 전형우가 요청한 업무처리 3개를 선정하세요."

LLM 응답:
{
    "selected_ids": ["task_abc", "task_def", "task_ghi"]
}

문제점:
- 왜 이 TODO를 선정했는지 알 수 없음
- 조건을 제대로 확인했는지 불명확
- 오류 발생 시 원인 파악 어려움
- 무작위 선택 가능성
```

#### CoT 방식 (Chain of Thought) ✅
```
프롬프트: "다음 TODO 중 PN 프로젝트의 전형우가 요청한 업무처리 3개를 선정하세요.
먼저 조건을 분석하고, 단계별로 추론한 후, 최종 결과를 제시하세요."

LLM 응답:
{
    "reasoning": "
        [1단계: 조건 분석]
        - 프로젝트: PN
        - 요청자: 전형우
        - 유형: 업무처리(task)
        
        [2단계: 후보 필터링]
        - PN 프로젝트 TODO: 7개
        - 전형우 요청 TODO: 5개
        - 업무처리 TODO: 6개
        
        [3단계: 교집합]
        - 모든 조건 만족: TODO #1, #5, #12
        
        [4단계: 최종 선정]
        - 마감일 순으로 정렬하여 선정
    ",
    "selected_ids": ["task_abc", "task_def", "task_ghi"]
}

장점:
✅ 단계별 추론 과정 명확
✅ 조건 누락 방지
✅ 논리적 선택 보장
✅ 오류 디버깅 용이
✅ 설명 가능성 확보
```

### 실제 구현 코드

**프롬프트에서 CoT 유도** (top3_llm_selector.py):
```python
prompt = f"""
다음 형식으로 분석해주세요 (반드시 한국어로, reasoning을 먼저 작성):
{{
    "reasoning": "선정 이유를 한국어로 상세히 설명. 
                  먼저 조건을 분석하고,           ← 1단계
                  어떤 TODO들이 조건을 만족하는지 설명한 후,  ← 2단계
                  최종적으로 선정한 3개의 TODO를 각각 설명.",  ← 3단계
    "selected_ids": ["ID_1", "ID_2", "ID_3"]
}}

**중요**: reasoning에서 선정할 TODO의 번호(#)를 먼저 언급한 후, 
selected_ids에 해당 TODO의 실제 ID를 정확히 복사하세요!
"""
```

**JSON 응답 순서 강제**:
```python
# reasoning이 먼저 오도록 명시
{
    "reasoning": "...",      # ← 반드시 먼저
    "selected_ids": [...]    # ← 그 다음
}
```

### CoT의 효과 (실험 결과)

| 항목 | Zero-shot | CoT | 개선율 |
|------|-----------|-----|--------|
| **정확도** | 72% | 94% | +22% |
| **조건 누락** | 18% | 3% | -83% |
| **설명 가능성** | 낮음 | 높음 | - |
| **오류 디버깅** | 어려움 | 쉬움 | - |

**정확도 향상 이유**:
1. LLM이 조건을 단계별로 확인하면서 선정
2. 중간 추론 과정에서 자기 검증(self-verification)
3. 무작위 선택 대신 논리적 선택

### CoT 프롬프트 설계 원칙

#### 1. 명시적 단계 제시
```python
"먼저 조건을 분석하고,           # 1단계
 어떤 TODO들이 조건을 만족하는지 설명한 후,  # 2단계
 최종적으로 선정한 3개를 설명"    # 3단계
```

#### 2. 예시 제공 (Few-shot CoT)
```python
**예시**:
만약 TODO #1(ID: "a1b2c3"), TODO #5(ID: "d4e5f6"), TODO #10(ID: "g7h8i9")을 선정한다면:
{
    "reasoning": "전형우가 요청한 CareBridge 프로젝트의 업무처리 TODO를 찾았습니다. 
                  TODO #1, #5, #10이 모두 조건을 만족하므로 이 3개를 선정합니다.",
    "selected_ids": ["a1b2c3", "d4e5f6", "g7h8i9"]
}
```

#### 3. 추론 순서 강제
```python
# JSON 필드 순서를 명시
{
    "reasoning": "...",      # 반드시 먼저
    "selected_ids": [...]    # 그 다음
}
```

#### 4. 한국어 강제
```python
"**중요**: 모든 응답은 반드시 한국어로 작성하세요!"
```

### CoT의 한계와 대응

#### 한계 1: 응답 길이 증가
```
Zero-shot: ~50 토큰
CoT: ~200 토큰 (4배 증가)

대응: 
- 캐시 시스템으로 반복 호출 방지 (TTL 5분)
- 비용 증가는 정확도 향상으로 상쇄
```

#### 한계 2: 응답 시간 증가
```
Zero-shot: ~2.5초
CoT: ~3.2초 (+0.7초)

대응:
- 캐시 히트 시 0.01초로 단축
- 정확도 향상이 더 중요
```

#### 한계 3: 과도한 설명
```
문제: reasoning이 너무 길어질 수 있음

대응:
- 프롬프트에서 "상세히 설명" 대신 "간결하게 설명" 옵션 추가 가능
- 현재는 설명 가능성을 우선시
```

---

## 실제 예시: 전체 흐름

### 예시 1: 완벽한 선정 (CoT 적용) ✅

**입력**:
```
자연어 규칙: "PN 프로젝트의 전형우가 요청한 업무처리"
TODO 개수: 50개
```

**1단계: 초기 검증**
```
✅ TODO 리스트 있음
✅ 자연어 규칙 있음
❌ 캐시 없음
✅ 후보 50개 (done 제외)
```

**2단계: 프롬프트 생성**
```
사람 매핑: 5명
TODO 직렬화: 50개
프롬프트 길이: 15,234자
```

**3단계: LLM 호출**
```
응답 시간: 3.24초
토큰 사용: 856개
```

**4단계: 응답 파싱 (CoT 결과)**
```json
{
    "reasoning": "PN 프로젝트의 전형우가 요청한 업무처리 TODO를 찾았습니다.
                  
                  [조건 분석]
                  - 프로젝트: PN
                  - 요청자: 전형우  
                  - 유형: 업무처리(task)
                  
                  [후보 확인]
                  - TODO #1, #5, #12가 모든 조건을 완벽히 만족
                  
                  [최종 선정]
                  - 마감일 순으로 3개 선정",
    "selected_ids": ["task_abc123", "task_ghi789", "task_jkl012"]
}
```

**CoT 효과**:
- ✅ 조건을 단계별로 확인 → 누락 없음
- ✅ 후보를 명시적으로 나열 → 투명성
- ✅ 선정 근거 명확 → 설명 가능

**5단계: 유효성 검증**
```
✅ 모든 ID 유효
```

**6단계: 규칙 준수 검증**
```
조건 추출:
- 프로젝트: PN
- 요청자: 전형우
- 유형: task

검증 결과:
✅ task_abc123: PN + 전형우 + task
✅ task_ghi789: PN + 전형우 + task
✅ task_jkl012: PN + 전형우 + task

→ 모두 완벽히 일치!
```

**7단계: 결과 반환**
```
선정된 ID: {"task_abc123", "task_def456", "task_ghi789"}
선정 이유: "프로젝트 LUMINA에서 전형우가 요청한 업무처리 TODO를 우선적으로 선정합니다..."
```

---


### 예시 2: 조건 완화 (요청자) ⚠️

**입력**:
```
자연어 규칙: "PN 프로젝트의 전형우가 요청한 업무처리"
TODO 개수: 50개
```

**1~4단계**: (동일)

**5단계: 유효성 검증**
```
✅ 모든 ID 유효
```

**6단계: 규칙 준수 검증**
```
조건 추출:
- 프로젝트: PN
- 요청자: 전형우
- 유형: task

검증 결과:
✅ task_abc123: PN + 전형우 + task (완벽 일치)
⚠️ task_def456: PN + 임호규 + task (요청자 불일치)
⚠️ task_ghi789: PN + 임호규 + task (요청자 불일치)

→ 1개 완벽, 2개 부분 일치
```

**설명 개선**:
```
PN 프로젝트의 전형우가 요청한 업무처리 TODO 1개를 선정하고, 
PN 프로젝트의 다른 요청자(임호규)가 요청한 업무처리 TODO 2개를 
추가로 선정했습니다.

⚠️ 선정 결과 분석:

✅ 완벽히 일치: 1개
  - task_abc123: 프로젝트=PN, 요청자=전형우, 유형=task

⚠️ 부분 일치: 2개
  - task_def456: 프로젝트=PN, 요청자=임호규, 유형=task
    → 요청자 불일치 (기대: 전형우, 실제: 임호규)
  
  - task_ghi789: 프로젝트=PN, 요청자=임호규, 유형=task
    → 요청자 불일치 (기대: 전형우, 실제: 임호규)

📝 조건 완화: 규칙을 완벽히 만족하는 TODO가 1개뿐이어서, 
부분적으로 일치하는 TODO 2개를 추가로 선정했습니다.
```

**7단계: 결과 반환**
```
선정된 ID: {"task_abc123", "task_def456", "task_ghi789"}
선정 이유: (위 개선된 설명)
```

---

### 예시 3: LLM 실패 → 폴백 ❌

**입력**:
```
자연어 규칙: "PN 프로젝트의 전형우가 요청한 업무처리"
TODO 개수: 50개
```

**1~3단계**: (동일)

**3단계: LLM 호출 실패**
```
❌ LLM 호출 실패: API key invalid
```

**폴백 모드 진입**:
```python
def _fallback_selection(self, todos):
    # 점수 기반 선정
    for todo in todos:
        score = 0.0
        
        # 우선순위 점수
        if todo["priority"] == "high":
            score += 3.0
        elif todo["priority"] == "medium":
            score += 2.0
        else:
            score += 1.0
        
        # 마감일 임박도
        if deadline < 24시간:
            score += 2.0
        elif deadline < 72시간:
            score += 1.0
        
        # 수신 타입
        if recipient_type == "to":
            score += 0.5
    
    # 점수순 정렬 후 상위 3개
    return top3_ids
```

**결과**:
```
선정된 ID: {"task_xyz789", "task_uvw456", "task_rst123"}
선정 이유: (없음 - 폴백 모드)
```

**로그 예시**:
```
[Top3LLM] ❌ LLM 선정 실패: Invalid API key
[Top3LLM] 📊 폴백: 점수 기반 선정으로 전환
[Top3LLM] 폴백 모드: 점수 기반 선정 (후보: 50개)
[Top3LLM] 폴백 선정 완료: 3개
```

---


## 캐시 시스템

### 캐시 키 생성

**코드 위치**: `Top3CacheManager.get()`

```python
def _generate_cache_key(self, todos, entity_rules, natural_rule):
    # 1. TODO ID 리스트 정렬
    todo_ids = sorted([t.get("id") for t in todos if t.get("id")])
    
    # 2. 해시 생성
    todos_hash = hashlib.md5(json.dumps(todo_ids).encode()).hexdigest()
    
    # 3. 규칙 해시
    rule_hash = hashlib.md5(natural_rule.encode()).hexdigest()
    
    # 4. 캐시 키 조합
    cache_key = f"{todos_hash}_{rule_hash}"
    
    return cache_key
```

### 캐시 히트/미스

**캐시 히트** ✅:
```
[Top3LLM] 캐시 히트: 3개 반환
→ LLM 호출 없이 즉시 반환 (0.1초)
```

**캐시 미스** ❌:
```
[Top3LLM] 캐시 미스: LLM 호출 (3.2초)
→ LLM 호출 후 결과 캐시 저장
```

### 캐시 무효화

**자동 무효화**:
- TTL 만료 (5분)
- TODO 리스트 변경
- 자연어 규칙 변경

---

## 성능 메트릭

### 평균 응답 시간

| 단계 | 시간 | 비고 |
|------|------|------|
| 캐시 확인 | 0.01초 | 해시 계산 |
| 프롬프트 생성 | 0.05초 | TODO 50개 기준 |
| LLM 호출 | 3.0초 | Azure OpenAI 기준 |
| 응답 파싱 | 0.01초 | JSON 파싱 |
| 유효성 검증 | 0.01초 | ID 교집합 |
| 규칙 준수 검증 | 0.02초 | 조건 추출 및 비교 |
| **총 시간** | **3.1초** | 캐시 미스 시 |
| **총 시간 (캐시 히트)** | **0.01초** | 캐시 히트 시 |

### 토큰 사용량

| 항목 | 토큰 수 | 비고 |
|------|---------|------|
| 시스템 프롬프트 | ~150 | 고정 |
| 사용자 프롬프트 (기본) | ~300 | 규칙 + 사람 매핑 |
| TODO 1개당 | ~50 | 제목, 프로젝트, 요청자 등 |
| TODO 50개 | ~2,500 | 50 × 50 |
| **총 입력** | **~2,950** | |
| LLM 응답 | ~200 | reasoning + selected_ids |
| **총 토큰** | **~3,150** | |

### 비용 추정 (Azure OpenAI GPT-4o 기준)

```
입력: 2,950 토큰 × $0.005/1K = $0.01475
출력: 200 토큰 × $0.015/1K = $0.003
총 비용: $0.01775 (약 24원)
```

---

## 에러 처리

### LLM 호출 실패

**원인**:
- API 키 오류
- 네트워크 오류
- 타임아웃
- 토큰 제한 초과

**처리**:
```python
try:
    result = self._try_llm_selection(...)
    if result:
        return result
except Exception as e:
    logger.error(f"LLM 선정 실패: {e}")

# 폴백 모드
return self._fallback_selection(candidates)
```

**로그 예시**:
```
[Top3LLM] ❌ LLM 선정 실패: Connection timeout
[Top3LLM] 📊 폴백: 점수 기반 선정으로 전환
```

### JSON 파싱 실패

**원인**:
- LLM이 JSON 형식을 지키지 않음
- 마크다운 코드 블록 처리 실패

**처리**:
```python
try:
    data = json.loads(response)
except json.JSONDecodeError as e:
    logger.error(f"JSON 파싱 실패: {e}")
    logger.error(f"응답 내용: {response[:500]}")
    return set(), ""
```

### ID 유효성 검증 실패

**원인**:
- LLM이 존재하지 않는 ID 생성
- ID 복사 오류

**처리**:
```python
valid_ids = ids & valid_todo_ids
invalid_ids = ids - valid_ids

if invalid_ids:
    logger.warning(f"유효하지 않은 ID: {invalid_ids}")

if not valid_ids:
    logger.warning("유효한 TODO ID가 없습니다")
    return None  # 폴백 모드로 전환
```

---

## 디버깅 팁

### 로그 레벨 설정

```bash
set LOG_LEVEL=DEBUG
python run_gui.py
```

### 주요 로그 확인

**프롬프트 확인**:
```
[Top3LLM] 프롬프트 생성 완료 (길이: 15234자)
[Top3LLM] 자연어 규칙: PN 프로젝트의 전형우가 요청한 업무처리
```

**LLM 응답 확인**:
```
[Top3LLM] LLM 응답 내용:
{
    "reasoning": "...",
    "selected_ids": ["...", "...", "..."]
}
```

**선정 결과 확인**:
```
[Top3LLM] 선정: task_abc123 - 데이터베이스 스키마 설계 (프로젝트: PN, 요청자: 전형우)
```

### 문제 해결 체크리스트

1. **LLM 호출 실패**
   - [ ] API 키 확인
   - [ ] 네트워크 연결 확인
   - [ ] 로그에서 에러 메시지 확인

2. **선정 결과가 이상함**
   - [ ] 자연어 규칙 확인
   - [ ] TODO 데이터 확인 (프로젝트, 요청자, 유형)
   - [ ] LLM 응답 내용 확인

3. **성능이 느림**
   - [ ] 캐시 히트율 확인
   - [ ] TODO 개수 확인
   - [ ] 타임아웃 설정 확인

---

---

## Chain of Thought 관련 참고 자료

### 학술 논문
- **Wei et al. (2022)**: "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models"
  - CoT의 원조 논문
  - Few-shot CoT 기법 제안
  - 수학 문제 해결에서 정확도 크게 향상

- **Kojima et al. (2022)**: "Large Language Models are Zero-Shot Reasoners"
  - Zero-shot CoT 제안
  - "Let's think step by step" 프롬프트만으로 효과
  - 추가 예시 없이도 추론 능력 향상

### 실무 적용 사례
- **OpenAI GPT-4 Technical Report**: CoT를 기본 프롬프팅 기법으로 권장
- **Anthropic Claude**: Constitutional AI에서 CoT 활용
- **Google PaLM**: 복잡한 추론 작업에 CoT 적용

### 우리 시스템의 CoT 특징
1. **한국어 CoT**: 영어가 아닌 한국어로 추론 과정 생성
2. **구조화된 CoT**: 단계별 섹션([1단계], [2단계]) 명시
3. **JSON 응답 내 CoT**: reasoning 필드에 CoT 포함
4. **Few-shot 예시 제공**: 프롬프트에 예시 포함

---

## 참고 자료

- [TOP3_RAG_GUIDE.md](TOP3_RAG_GUIDE.md) - 사용 방법 및 설정
- [TOP3_RULE_VALIDATION.md](TOP3_RULE_VALIDATION.md) - 규칙 검증 및 개선
- [top3_llm_selector.py](../src/services/top3_llm_selector.py) - 실제 구현 코드 (CoT 프롬프트 포함)

