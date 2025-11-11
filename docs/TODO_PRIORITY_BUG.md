# TODO 우선순위 버그 분석

## 문제 요약

**"임보연님, 안녕하세요, 임보연입니다! 확인했습니다."** 같은 단순 인사/확인 메시지가 **HIGH 우선순위**로 잘못 분류되고 있습니다.

## 심각도

- **HIGH 우선순위 77개 중 68개(88.3%)가 단순 메시지**
- 실제 중요한 TODO가 묻힐 위험
- 사용자 신뢰도 하락

---

## 실제 사례

### 사례 1
```
제목: 문서검토
설명: 임보연님, 안녕하세요, 임보연입니다! 확인했습니다.
발신자: jiwon_design
유형: review
우선순위: high ⚠️
Evidence: ["일반적인 메시지"]
```

### 사례 2
```
제목: 문서검토
설명: 임보연님, 안녕하세요, 임보연입니다 확인했습니다.
발신자: lee_jd
유형: review
우선순위: high ⚠️
Evidence: ["일반적인 메시지"]
```

### 통계
```
임보연 TODO 우선순위 분포:
- HIGH: 77개
  └─ 단순 메시지: 68개 (88.3%) ⚠️
  └─ 실제 중요: 9개 (11.7%)
- MEDIUM: 140개
- LOW: 57개
```

---

## 원인 분석

### 원인 1: 우선순위 재보정 로직 (main.py:820-880)

**코드**:
```python
# ❹-1 우선순위 재보정(편중 완화)
if todo_items:
    scored_items: List[tuple[float, Dict]] = []
    for t in todo_items:
        base = priority_value.get(t.get("priority", "low"), 1)
        
        # 마감일 긴급도
        if deadline_dt == datetime.max:
            urgency = 0.0
        else:
            hours_left = (deadline_dt - now_utc).total_seconds() / 3600.0
            if hours_left <= 24:
                urgency = 1.5
            elif hours_left <= 72:
                urgency = 1.0
            elif hours_left <= 168:
                urgency = 0.5
            else:
                urgency = 0.0
        
        # Evidence 보너스
        evidence_count = len(json.loads(t.get("evidence") or "[]"))
        evidence_bonus = min(0.6, 0.2 * evidence_count)
        
        score = base + urgency + evidence_bonus
        scored_items.append((score, t))
    
    scored_items.sort(key=lambda x: x[0], reverse=True)
    
    # 상위 30%를 HIGH로 재분류
    high_cut = max(1, round(total * 0.3))
    low_cut = total - max(1, round(total * 0.2))
    
    for idx, (_, item) in enumerate(scored_items):
        if idx < high_cut:
            item["priority"] = "high"  # ← 문제: 무조건 HIGH 부여
        elif idx >= low_cut:
            item["priority"] = "low"
        else:
            item["priority"] = "medium"
```

**문제점**:
1. 원래 LOW 우선순위였던 TODO도
2. 상위 30%에 들어가면
3. **무조건 HIGH로 재분류**됨
4. 원래 우선순위를 완전히 무시

**예시**:
```
원래 우선순위:
- TODO A: LOW (0.16점) - "확인했습니다"
- TODO B: LOW (0.18점) - "안녕하세요"
- TODO C: MEDIUM (0.45점) - "검토 부탁드립니다"

재보정 후:
- TODO C: HIGH (상위 30%) ✅
- TODO B: HIGH (상위 30%) ❌ 잘못됨
- TODO A: MEDIUM
```

### 원인 2: 액션 추출기가 단순 메시지를 "review"로 인식

**코드**: `action_extractor.py`

```python
# "확인했습니다"를 "review" 액션으로 인식
{
    "action_type": "review",  # 문서검토
    "title": "문서검토",
    "description": "임보연님, 안녕하세요, 임보연입니다! 확인했습니다."
}
```

**문제점**:
- "확인했습니다" = 단순 확인 메시지
- 하지만 "review" 유형으로 분류
- "review"는 중요한 액션으로 간주됨

### 원인 3: Evidence가 의미 없음

**Evidence**: `["일반적인 메시지"]`

**문제점**:
- 모든 점수가 낮아서 "일반적인 메시지"로 분류됨
- 하지만 evidence_count = 1이므로 0.2점 보너스
- 이 보너스로 인해 상위 30%에 진입

---

## 해결 방법

### 1. 즉시 수정: 우선순위 재보정 로직 개선

**파일**: `offline_agent/main.py:820-880`

```python
# 수정 전
for idx, (_, item) in enumerate(scored_items):
    if idx < high_cut:
        item["priority"] = "high"  # 무조건 HIGH

# 수정 후
for idx, (score, item) in enumerate(scored_items):
    # 원래 우선순위 저장
    original_priority = item.get("priority", "low")
    
    if idx < high_cut:
        # 원래 LOW였던 것은 MEDIUM까지만
        if original_priority == "low" and score < 2.0:
            item["priority"] = "medium"  # LOW → MEDIUM
        else:
            item["priority"] = "high"  # MEDIUM/HIGH → HIGH
    elif idx >= low_cut:
        # 원래 HIGH였던 것은 MEDIUM까지만
        if original_priority == "high":
            item["priority"] = "medium"  # HIGH → MEDIUM
        else:
            item["priority"] = "low"
    else:
        item["priority"] = "medium"
```

### 2. 액션 추출 개선: 단순 확인 메시지 필터링

**파일**: `offline_agent/src/nlp/action_extractor.py`

```python
def extract_actions(self, message: Dict) -> List[Dict]:
    """액션 추출"""
    content = message.get("body", "") or message.get("content", "")
    
    # 단순 인사/확인 메시지 필터링
    simple_patterns = [
        r"^.*안녕하세요.*확인했습니다\.?$",
        r"^.*안녕하세요.*작업 중입니다\.?$",
        r"^.*확인했습니다\.?$",
        r"^.*알겠습니다\.?$",
        r"^.*네,?\s*감사합니다\.?$"
    ]
    
    content_clean = content.strip()
    if len(content_clean) < 50:  # 짧은 메시지
        for pattern in simple_patterns:
            if re.match(pattern, content_clean, re.IGNORECASE):
                logger.debug(f"단순 메시지 필터링: {content_clean[:50]}")
                return []  # 액션 없음
    
    # 기존 액션 추출 로직
    ...
```

### 3. Evidence 기반 필터링

**파일**: `offline_agent/main.py:750-820`

```python
for action in result.get("actions", []):
    # ... TODO 생성 ...
    
    # Evidence 검증
    reasons = (pr.get("reasoning") or [])[:3]
    
    # "일반적인 메시지"만 있고 내용이 짧으면 제외
    if (len(reasons) == 1 and 
        "일반적인 메시지" in reasons and 
        len(action.get("description", "")) < 50):
        logger.debug(f"단순 메시지 TODO 제외: {action.get('title')}")
        continue  # TODO 생성 안 함
    
    todo_item["evidence"] = json.dumps(reasons, ensure_ascii=False)
    todo_items.append(todo_item)
```

### 4. 우선순위 점수 임계값 조정

**파일**: `offline_agent/src/nlp/priority_ranker.py:230-240`

```python
def _determine_priority_level(self, overall_score: float) -> str:
    """우선순위 레벨 결정"""
    # 수정 전
    if overall_score >= 0.7:
        return "high"
    elif overall_score >= 0.4:
        return "medium"
    else:
        return "low"
    
    # 수정 후 (임계값 상향)
    if overall_score >= 0.8:  # 0.7 → 0.8
        return "high"
    elif overall_score >= 0.5:  # 0.4 → 0.5
        return "medium"
    else:
        return "low"
```

---

## 테스트 케이스

### 테스트 1: 단순 확인 메시지
```
입력: "임보연님, 안녕하세요, 임보연입니다! 확인했습니다."

기대 결과:
- TODO 생성 안 됨 ✅
- 또는 LOW 우선순위 ✅

실제 결과 (수정 전):
- TODO 생성됨 ❌
- HIGH 우선순위 ❌
```

### 테스트 2: 실제 검토 요청
```
입력: "프로젝트 문서 검토 부탁드립니다. 내일까지 피드백 주시면 감사하겠습니다."

기대 결과:
- TODO 생성됨 ✅
- HIGH 우선순위 ✅

실제 결과:
- TODO 생성됨 ✅
- HIGH 우선순위 ✅
```

### 테스트 3: 중간 복잡도 메시지
```
입력: "안녕하세요, 회의 일정 조정이 필요합니다."

기대 결과:
- TODO 생성됨 ✅
- MEDIUM 우선순위 ✅

실제 결과 (수정 전):
- TODO 생성됨 ✅
- HIGH 우선순위 (상위 30%) ❌
```

---

## 우선순위

1. **P0 (Critical)**: 우선순위 재보정 로직 수정
2. **P1 (High)**: 단순 메시지 필터링
3. **P2 (Medium)**: Evidence 기반 필터링
4. **P3 (Low)**: 임계값 조정

---

## 예상 효과

### 수정 전
```
HIGH: 77개
- 단순 메시지: 68개 (88.3%) ❌
- 실제 중요: 9개 (11.7%)
```

### 수정 후
```
HIGH: 15개
- 단순 메시지: 0개 (0%) ✅
- 실제 중요: 15개 (100%) ✅

MEDIUM: 150개
- 단순 메시지: 10개 (6.7%)
- 중간 중요도: 140개 (93.3%)

LOW: 109개
- 단순 메시지: 58개 (53.2%)
- 낮은 중요도: 51개 (46.8%)
```

---

## 다음 단계

1. ✅ 문제 분석 완료
2. ⏳ 코드 수정
3. ⏳ 테스트
4. ⏳ 배포
5. ⏳ 모니터링

---

## 관련 파일

- `offline_agent/main.py:820-880` - 우선순위 재보정 로직
- `offline_agent/src/nlp/action_extractor.py` - 액션 추출
- `offline_agent/src/nlp/priority_ranker.py` - 우선순위 점수 계산
- `offline_agent/check_specific_todo.py` - 분석 스크립트
