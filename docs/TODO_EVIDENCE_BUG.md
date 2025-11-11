# TODO Evidence 버그 분석

## 문제 상황

임보연의 TODO 리스트에 "안녕하세요, 팀 여러분! 작업 중입니다" 같은 단순한 내용의 TODO가 생성되고 있습니다.

DB를 확인한 결과, **모든 TODO의 evidence 필드가 빈 배열 `[]`**로 저장되어 있습니다.

```sql
SELECT id, title, evidence FROM todos WHERE persona_name = '임보연' LIMIT 5;

결과:
- task_328610e3d35e: evidence = []
- task_bd55dec902ed: evidence = []
- task_63ef82d6316c: evidence = []
- task_e98bea79f47c: evidence = []
- task_3378d11d2752: evidence = []
```

---

## 원인 분석

### 1. Evidence 생성 코드 (main.py:812)

```python
# ❷ Evidence chips / deadline confidence (result 컨텍스트 기반)
reasons = (pr.get("reasons") or [])[:3]
todo_item["evidence"] = json.dumps(reasons, ensure_ascii=False)
```

- `pr`은 `result.get("priority")`의 결과
- `pr.get("reasons")`를 시도하지만...

### 2. PriorityScore.to_dict() (priority_ranker.py:30-44)

```python
def to_dict(self) -> Dict:
    """딕셔너리로 변환"""
    return {
        "overall_score": self.overall_score,
        "priority_level": self.priority_level,
        "urgency_score": self.urgency_score,
        "importance_score": self.importance_score,
        "deadline_score": self.deadline_score,
        "sender_score": self.sender_score,
        "keyword_score": self.keyword_score,
        "reasoning": self.reasoning,  # ← "reasoning"이지 "reasons"가 아님!
        "suggested_action": self.suggested_action,
        "estimated_time": self.estimated_time
    }
```

**버그**: 필드명 불일치!
- 생성 코드: `pr.get("reasons")`
- 실제 필드: `"reasoning"`

### 3. 결과

```python
pr.get("reasons")  # → None
(pr.get("reasons") or [])  # → []
reasons = [][:3]  # → []
todo_item["evidence"] = json.dumps([])  # → "[]"
```

**모든 TODO의 evidence가 빈 배열이 됩니다!**

---

## Evidence의 역할

Evidence는 TODO 생성 근거를 보여주는 중요한 정보입니다:

### 원래 의도

```python
# priority_ranker.py:240-260
def _generate_reasoning(self, scores: Dict, content: str, sender: str) -> List[str]:
    """추론 과정 생성"""
    reasoning = []
    
    if scores["urgency"] > 0.6:
        reasoning.append("긴급 키워드가 포함되어 높은 긴급도를 보임")
    
    if scores["sender"] > 0.7:
        reasoning.append("중요한 발신자로부터 온 메시지")
    
    if scores["keywords"] > 0.5:
        reasoning.append("중요 키워드가 다수 포함됨")
    
    if scores["deadline"] > 0.5:
        reasoning.append("명시적인 데드라인이 있음")
    
    if scores["importance"] > 0.5:
        reasoning.append("업무상 중요한 내용 포함")
    
    if not reasoning:
        reasoning.append("일반적인 메시지")
    
    return reasoning
```

### 예상 결과

```json
{
    "evidence": [
        "긴급 키워드가 포함되어 높은 긴급도를 보임",
        "중요한 발신자로부터 온 메시지",
        "중요 키워드가 다수 포함됨"
    ]
}
```

### 실제 결과

```json
{
    "evidence": []
}
```

---

## LLM 분석과의 관계

### 오해

"임보연 TODO에 LLM 분석을 안 하는 거야?"

### 실제

**LLM 분석은 하고 있습니다!**

1. **1단계: 키워드 기반 우선순위 분류** (priority_ranker)
   - 모든 메시지에 대해 수행
   - 점수 계산 및 reasoning 생성
   - **하지만 evidence에 저장 안 됨 (버그)**

2. **2단계: LLM 상세 분석** (summarizer)
   - 상위 70개 메시지만 수행
   - 메시지 요약, 액션 추출
   - **이 결과는 evidence와 무관**

### Evidence의 실제 용도

Evidence는 **키워드 기반 우선순위 분류의 근거**를 보여주는 것입니다:

```python
# main.py:850-856
evidence_count = 0
try:
    evidence_count = len(json.loads(t.get("evidence") or "[]"))
except Exception:
    pass
evidence_bonus = min(0.6, 0.2 * evidence_count)
score = base + urgency + evidence_bonus
```

- evidence가 많을수록 우선순위 점수가 높아짐
- 최대 0.6점 보너스 (3개 이상일 때)

---

## 단순한 TODO가 생성되는 이유

### 예시: "안녕하세요, 팀 여러분! 작업 중입니다"

이런 메시지가 TODO로 생성되는 이유:

1. **키워드 매칭**
   - "작업"이라는 키워드가 포함됨
   - `medium_priority_keywords`에 "작업"이 있을 가능성

2. **액션 추출**
   - action_extractor가 "작업 중"을 액션으로 인식
   - 실제로는 상태 보고일 뿐

3. **LLM 판단 부재**
   - 상위 70개에 포함되지 않으면 LLM 분석 없음
   - 키워드만으로 TODO 생성

### 해결 방법

1. **버그 수정**: `pr.get("reasons")` → `pr.get("reasoning")`
2. **키워드 정제**: 불필요한 키워드 제거
3. **LLM 범위 확대**: 상위 70개 → 100개 (비용 고려)
4. **액션 추출 개선**: 상태 보고와 액션 요청 구분

---

## 수정 방안

### 1. 즉시 수정 (버그 픽스)

**파일**: `offline_agent/main.py:812`

```python
# 수정 전
reasons = (pr.get("reasons") or [])[:3]

# 수정 후
reasons = (pr.get("reasoning") or [])[:3]
```

### 2. 검증

수정 후 TODO 생성 시 evidence 확인:

```sql
SELECT id, title, evidence FROM todos WHERE persona_name = '임보연' LIMIT 5;

기대 결과:
- task_xxx: evidence = ["긴급 키워드가 포함되어 높은 긴급도를 보임", "중요 키워드가 다수 포함됨"]
- task_yyy: evidence = ["일반적인 메시지"]
```

### 3. 추가 개선 (선택)

**파일**: `offline_agent/src/nlp/priority_ranker.py:30-44`

필드명 통일을 위해 `reasons`로 변경:

```python
def to_dict(self) -> Dict:
    return {
        ...
        "reasons": self.reasoning,  # reasoning → reasons로 변경
        ...
    }
```

또는 main.py에서 `reasoning`으로 통일:

```python
reasons = (pr.get("reasoning") or [])[:3]
```

---

## 결론

1. **버그 확인**: evidence가 빈 배열인 이유는 필드명 불일치
2. **LLM 분석**: 실제로는 수행되고 있음 (상위 70개)
3. **단순 TODO**: 키워드 기반 필터링의 한계
4. **해결**: 필드명 수정 + 키워드 정제 + LLM 범위 확대

**우선순위**: 버그 수정 (1줄 변경)으로 즉시 개선 가능!
