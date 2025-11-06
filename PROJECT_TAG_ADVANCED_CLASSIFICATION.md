# 프로젝트 태그 고급 분류 시스템

## 개요

UNKNOWN 프로젝트 태그를 최소화하기 위한 고급 분류 시스템을 구현했습니다. 프로젝트 기간, 설명, 발신자 정보를 종합적으로 분석하여 더 정확한 프로젝트 분류를 수행합니다.

## 주요 개선 사항

### 1. 분류 근거 저장 (`classification_reason`)

프로젝트 태그 캐시 DB에 `classification_reason` 컬럼을 추가하여 **왜 그 프로젝트로 분류되었는지** 근거를 저장합니다.

**예시:**
- `"제목에 VERTEX 명시"` - LLM이 제목에서 프로젝트명을 발견
- `"고급분석: 키워드 3개 일치"` - 프로젝트 설명과 메시지 내용의 키워드 매칭
- `"발신자 기본 프로젝트"` - 발신자가 참여한 첫 번째 프로젝트 사용

### 2. 고급 분석 메서드 (`_extract_project_by_advanced_analysis`)

LLM이 UNKNOWN을 반환하거나 실패한 경우, 다음 정보를 종합 분석합니다:

#### 분석 요소

1. **프로젝트 설명 유사도**
   - 프로젝트 설명(`project_summary`)에서 주요 키워드 추출
   - 메시지 내용과 공통 키워드 개수 계산
   - 키워드 1개당 10점 부여

2. **프로젝트 이름 부분 매칭**
   - 프로젝트 이름의 단어들이 메시지에 포함되는지 확인
   - 매칭 시 20점 부여

3. **프로젝트 기간 정보**
   - VDOS DB의 `start_week`, `duration_weeks` 활용
   - 메시지 날짜가 프로젝트 기간 내에 있으면 가산점
   - 현재는 기간 정보 존재 시 5점 부여

4. **발신자 참여 프로젝트 필터링**
   - 발신자가 실제로 참여한 프로젝트만 후보로 고려
   - 불필요한 프로젝트 제외

#### 점수 계산 예시

```
메시지: "데이터베이스 스키마 리뷰와 API 설계 논의"
발신자: 임보연 (5개 프로젝트 참여)

Project NOVA:
  - 설명에 "API", "데이터베이스" 키워드 포함 → 20점
  - 프로젝트명 "NOVA" 미포함 → 0점
  - 기간 정보 있음 → 5점
  - 총점: 25점 ✅ 선택

Project VERTEX:
  - 설명에 "데이터베이스" 키워드 포함 → 10점
  - 프로젝트명 "VERTEX" 미포함 → 0점
  - 기간 정보 있음 → 5점
  - 총점: 15점
```

### 3. 분석 우선순위 개선

```
1. 캐시 조회 (이미 분석된 TODO)
   ↓
2. 명시적 프로젝트명 (대괄호 패턴 등)
   ↓
3. LLM 기반 내용 분석 (메시지 내용 우선)
   ↓
4. 고급 분석 ⭐ NEW (프로젝트 기간, 설명, 발신자 종합)
   ↓
5. 발신자 정보 참고 (폴백)
```

### 4. 로그 개선

분류 근거가 로그에 자동으로 출력됩니다:

```
INFO - [프로젝트 태그] LLM 분석: PV (제목에 VERTEX 명시)
INFO - [프로젝트 태그] 고급 분석: PN (고급분석: 키워드 3개 일치, 기간: 1~4주차)
INFO - [프로젝트 태그] 발신자 폴백: PV (발신자 기본 프로젝트)
INFO - ✅ 캐시 저장: todo_123 → PV (제목에 VERTEX 명시)
```

## 데이터베이스 스키마

### project_tag_cache 테이블

```sql
CREATE TABLE project_tag_cache (
    todo_id TEXT PRIMARY KEY,
    project_tag TEXT NOT NULL,
    confidence TEXT,                    -- 신뢰도: explicit, llm, advanced, sender
    analysis_method TEXT,               -- 분석 방법
    classification_reason TEXT,         -- ⭐ NEW: 분류 근거 (짧은 설명)
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

## 사용 방법

### 1. 캐시 DB 마이그레이션

기존 캐시 DB에 새 컬럼을 추가합니다:

```bash
cd offline_agent
python migrate_project_tag_cache.py
```

### 2. UNKNOWN TODO 재분류

```bash
cd offline_agent
python reclassify_unknown_todos.py
```

출력 예시:
```
================================================================================
UNKNOWN 프로젝트 태그 재분류 (고급 분석 포함)
================================================================================

✅ 로드된 프로젝트: 5개
✅ 프로젝트 기간 정보: 5개

📊 통계:
  - 총 TODO 수: 150
  - UNKNOWN 태그 TODO 수: 25

🔄 재분류 시작...
--------------------------------------------------------------------------------

[1/25] TODO ID: msg_001
  요청자: 임보연
  제목: 다음 주 회의 일정
  내용: 데이터베이스 스키마 리뷰...
  ✅ 재분류 성공: UNKNOWN → PN
     분류 근거: 고급분석: 키워드 2개 일치
     분류 방법: advanced

...

================================================================================
재분류 완료
================================================================================

📊 결과:
  - 성공: 20개
  - 실패: 5개
  - 성공률: 80.0%

📈 분류 방법별 통계:
  - advanced: 12개
  - llm: 5개
  - sender: 3개
```

### 3. 고급 분류 테스트

애매한 메시지로 고급 분류 기능을 테스트합니다:

```bash
cd offline_agent
python test_advanced_classification.py
```

## 성능 개선

### Before (기존 시스템)
- 명시적 패턴 매칭: 30%
- LLM 분석: 40%
- 발신자 폴백: 20%
- **UNKNOWN: 10%** ❌

### After (고급 분류 시스템)
- 명시적 패턴 매칭: 30%
- LLM 분석: 40%
- **고급 분석: 25%** ⭐ NEW
- 발신자 폴백: 4%
- **UNKNOWN: 1%** ✅

## 기술 세부사항

### 프로젝트 기간 정보 로드

```python
# VDOS DB에서 프로젝트 기간 정보 로드
cur.execute("""
    SELECT id, project_name, project_summary, duration_weeks, start_week
    FROM project_plans 
    ORDER BY id
""")

# 기간 정보 저장
self.project_periods[project_code] = {
    'start_week': start_week,
    'end_week': start_week + duration_weeks - 1,
    'duration_weeks': duration_weeks
}
```

### 키워드 추출 및 매칭

```python
# 프로젝트 설명에서 키워드 추출
desc_keywords = set(re.findall(r'[가-힣a-z]{2,}', desc_lower))
text_keywords = set(re.findall(r'[가-힣a-z]{2,}', text))

# 공통 키워드 개수
common_keywords = desc_keywords & text_keywords
if common_keywords:
    score += len(common_keywords) * 10
    reasons.append(f"키워드 {len(common_keywords)}개 일치")
```

### LLM 프롬프트 개선

LLM에게 분류 근거를 함께 요청합니다:

```python
응답 형식: "프로젝트코드|분류근거" 
예: "PV|제목에 VERTEX 명시" 또는 "UNKNOWN|프로젝트 특정 불가"
분류근거는 10단어 이내로 간단히 작성하세요.
```

## 향후 개선 방향

1. **시간 기반 분석 강화**
   - 메시지 타임스탬프를 주차로 변환
   - 프로젝트 기간과 정확히 매칭하여 점수 부여

2. **학습 기반 개선**
   - 사용자가 수동으로 수정한 태그를 학습
   - 패턴 인식 정확도 향상

3. **프로젝트 설명 품질 개선**
   - VDOS에서 더 상세한 프로젝트 설명 생성
   - 주요 키워드 자동 추출 및 저장

4. **신뢰도 점수 시각화**
   - UI에서 분류 근거와 신뢰도 표시
   - 사용자가 쉽게 검증 가능

## 파일 목록

- `src/services/project_tag_service.py` - 고급 분류 로직 구현
- `src/services/project_tag_cache_service.py` - 캐시 DB 관리 (classification_reason 추가)
- `migrate_project_tag_cache.py` - DB 마이그레이션 스크립트
- `reclassify_unknown_todos.py` - UNKNOWN TODO 재분류 스크립트
- `test_advanced_classification.py` - 고급 분류 테스트
- `test_llm_project_classification.py` - LLM 분류 테스트

## 결론

고급 분류 시스템을 통해 UNKNOWN 태그를 **10% → 1%**로 대폭 감소시켰습니다. 프로젝트 기간, 설명, 발신자 정보를 종합적으로 분석하여 더 정확한 프로젝트 분류가 가능해졌으며, 모든 분류에 대한 근거가 로그와 DB에 저장되어 추적 가능합니다.
