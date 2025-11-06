# 페르소나 캐시 문제 수정 요약

## 🔍 문제 상황
- **첫 번째 페르소나 (이정두)**: 데이터 수집 → TODO 생성 ✅
- **두 번째 페르소나 (임보연)**: 데이터 수집 → TODO 생성 ❌ UI에 표시 안됨
- **다시 첫 번째 페르소나 (이정두)**: 캐시 사용 → TODO 복원 ❌ UI에 표시 안됨

## 🐛 근본 원인
1. `_restore_todos_from_cache()` 함수에서 DB에만 저장하고 UI 업데이트 누락
2. `_load_from_cache()` 함수에서 TODO 초기화 타이밍 문제

## 🔧 수정 내용

### 1. `_restore_todos_from_cache()` 개선
**파일**: `offline_agent/src/ui/main_window.py`

**변경 전**:
```python
def _restore_todos_from_cache(self, cached_todos: List[Dict]) -> None:
    # DB에만 저장
    _save_todos_to_db(cached_todos, self.todo_panel.db_path)
    logger.info(f"💾 캐시된 TODO 복원 완료: {len(cached_todos)}개")
```

**변경 후**:
```python
def _restore_todos_from_cache(self, cached_todos: List[Dict]) -> None:
    # 1. DB에 저장
    _save_todos_to_db(cached_todos, self.todo_panel.db_path)
    
    # 2. UI에 표시 (populate_from_items 사용)
    self.todo_panel.populate_from_items(cached_todos)
    
    # 3. 프로젝트 태그 강제 업데이트
    self._force_update_project_tags()
    
    logger.info(f"✅ 캐시된 TODO 복원 완료: {len(cached_todos)}개")
```

### 2. `_load_from_cache()` 개선
**파일**: `offline_agent/src/ui/main_window.py`

**변경 전**:
```python
def _load_from_cache(self, persona_key: str) -> None:
    # 항상 TODO 초기화
    self._clear_todos_for_persona_change()
    
    # 메시지 복원
    # TODO 복원
    # ...
```

**변경 후**:
```python
def _load_from_cache(self, persona_key: str) -> None:
    # 메시지 복원
    
    # 캐시된 TODO가 있는 경우에만 초기화 후 복원
    cached_todos = cached_data.get('todos', [])
    if cached_todos:
        self._clear_todos_for_persona_change()
        self._restore_todos_from_cache(cached_todos)
    else:
        # 캐시된 TODO가 없으면 초기화 후 새로 분석
        self._clear_todos_for_persona_change()
        self._trigger_background_analysis(messages)
```

## ✅ 수정 효과

### 페르소나 변경 시나리오
1. **이정두 선택 (첫 로드)**
   - 데이터 수집 → 메시지 10개
   - 백그라운드 분석 → TODO 5개 생성
   - 캐시 저장 → TODO 5개 저장
   - ✅ UI에 TODO 5개 표시

2. **임보연 선택 (첫 로드)**
   - 데이터 수집 → 메시지 15개
   - 백그라운드 분석 → TODO 7개 생성
   - 캐시 저장 → TODO 7개 저장
   - ✅ UI에 TODO 7개 표시

3. **이정두 선택 (재로드)**
   - 캐시 로드 → 메시지 10개, TODO 5개
   - TODO DB 초기화
   - TODO 복원 (DB + UI)
   - ✅ UI에 TODO 5개 표시

4. **김용준 선택 (첫 로드)**
   - 데이터 수집 → 메시지 12개
   - 백그라운드 분석 → TODO 6개 생성
   - 캐시 저장 → TODO 6개 저장
   - ✅ UI에 TODO 6개 표시

5. **임보연 선택 (재로드)**
   - 캐시 로드 → 메시지 15개, TODO 7개
   - TODO DB 초기화
   - TODO 복원 (DB + UI)
   - ✅ UI에 TODO 7개 표시

## 📊 캐시 상태 관리

### 캐시 구조
```python
persona_cache = {
    "leejungdu@example.com_lee_jd": {
        "messages": [...],  # 메시지 리스트
        "todos": [...],     # TODO 리스트 (백그라운드 분석 후 업데이트)
        "analysis_results": [...],  # 분석 결과
        "timestamp": 1234567890  # 타임스탬프
    },
    "limboyeon@koreaitcompany.com_limboyeon": {
        ...
    }
}
```

### 캐시 업데이트 타이밍
1. **데이터 수집 시**: 메시지만 저장, TODO는 빈 배열
2. **백그라운드 분석 완료 시**: TODO와 분석 결과 업데이트
3. **페르소나 재선택 시**: 캐시에서 모든 데이터 복원

## 🧪 테스트 결과
- ✅ 첫 로드 시 TODO 생성 및 표시
- ✅ 재로드 시 캐시에서 TODO 복원 및 표시
- ✅ 페르소나 변경 시 이전 TODO 캐시 유지
- ✅ 프로젝트 태그 자동 업데이트

## 📝 추가 개선 사항
1. 로그 메시지 개선으로 디버깅 용이성 향상
2. 에러 처리 강화 (try-except with exc_info=True)
3. 캐시 복원 과정의 각 단계별 로그 추가

## 🎯 결론
페르소나 변경 시 TODO가 제대로 표시되지 않던 문제가 완전히 해결되었습니다. 
이제 각 페르소나의 TODO가 캐시에 저장되고, 페르소나 재선택 시 정확히 복원됩니다.
