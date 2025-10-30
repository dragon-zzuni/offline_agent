# 페르소나 캐시 문제 분석

## 🔍 문제 상황
1. **첫 번째 페르소나 (이정두)**: 데이터 수집 → TODO 생성 ✅ 정상 작동
2. **두 번째 페르소나 (임보연)**: 데이터 수집 → TODO 생성 ❌ UI에 표시 안됨
3. **다시 첫 번째 페르소나 (이정두)**: 캐시 사용 → TODO 복원 ❌ UI에 표시 안됨

## 📊 현재 로직 흐름

### 페르소나 변경 시 (`on_persona_changed`)
```
1. 첫 번째 로드인지 확인
   - 첫 로드: _collect_and_cache_data() 호출
   - 재로드: _load_from_cache() 호출 (캐시 유효 시)
```

### 데이터 수집 (`_collect_and_cache_data`)
```
1. _clear_todos_for_persona_change() - TODO DB 초기화
2. 메시지 수집
3. 캐시에 저장 (todos는 빈 배열)
4. UI 업데이트
5. 백그라운드 분석 트리거 (별도 스레드)
```

### 캐시 로드 (`_load_from_cache`)
```
1. _clear_todos_for_persona_change() - TODO DB 초기화
2. 캐시에서 메시지 복원
3. 캐시에서 TODO 복원
   - _restore_todos_from_cache() 호출
   - _save_todos_to_db() 호출
4. todo_panel.refresh_todo_list() 호출
```

## 🐛 발견된 문제들

### 1. TODO 복원 로직 문제
**위치**: `_restore_todos_from_cache()`
**문제**: 
- `_save_todos_to_db()`만 호출하고 `populate_from_items()`를 호출하지 않음
- DB에는 저장되지만 UI에 표시되지 않음

### 2. 백그라운드 분석 결과 캐시 업데이트 타이밍
**위치**: `_update_cache_with_analysis_results()`
**문제**:
- 백그라운드 분석이 완료되어도 캐시가 업데이트되지 않을 수 있음
- 다음 페르소나 변경 시 빈 TODO 배열이 캐시에 남아있음

### 3. 페르소나 변경 시 TODO 초기화 타이밍
**문제**:
- 캐시 로드 시에도 TODO를 초기화하는데, 이게 복원 전에 실행됨
- 복원 로직이 제대로 작동하지 않으면 빈 상태로 남음

## 🔧 해결 방안

### 1. TODO 복원 로직 개선
```python
def _restore_todos_from_cache(self, cached_todos: List[Dict]) -> None:
    """캐시된 TODO를 데이터베이스와 UI에 복원"""
    if not cached_todos:
        return
    
    # 1. DB에 저장
    _save_todos_to_db(cached_todos, self.todo_panel.db_path)
    
    # 2. UI에 표시 (populate_from_items 사용)
    self.todo_panel.populate_from_items(cached_todos)
    
    logger.info(f"✅ TODO 복원 완료: {len(cached_todos)}개")
```

### 2. 백그라운드 분석 완료 시 캐시 업데이트 보장
```python
def _handle_background_analysis_result(self, result):
    # ... 기존 로직 ...
    
    # 캐시 업데이트
    if todos:
        self._update_cache_with_analysis_results(todos, analysis_results)
```

### 3. 캐시 로드 시 TODO 초기화 제거
```python
def _load_from_cache(self, persona_key: str) -> None:
    # _clear_todos_for_persona_change() 제거
    # 대신 populate_from_items()가 자동으로 기존 TODO를 대체함
```

## 📝 수정 계획

1. `_restore_todos_from_cache()` 수정
   - `populate_from_items()` 호출 추가
   
2. `_load_from_cache()` 수정
   - TODO 초기화 로직 제거 또는 조건부 실행
   
3. `_handle_background_analysis_result()` 확인
   - 캐시 업데이트가 제대로 되는지 확인

4. 테스트 시나리오
   - 이정두 → 임보연 → 이정두 순서로 페르소나 변경
   - 각 단계에서 TODO가 제대로 표시되는지 확인
