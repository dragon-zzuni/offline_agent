# 페르소나 변경 시 TODO 리스트 문제 해결

## 🔍 발견된 문제

**문제**: 페르소나 변경 시 TODO 리스트가 해당 페르소나가 수신한 메시지들로 바뀌지 않고 이전 페르소나의 TODO가 그대로 남아있음

**원인**: 
- TODO 데이터베이스가 전역적으로 공유됨
- 페르소나 변경 시 TODO 데이터베이스 초기화 없음
- 새 페르소나의 메시지로 TODO 재생성 로직 부재

## 🔧 적용된 수정사항

### 1. 페르소나 변경 시 TODO 초기화 추가

**`_collect_and_cache_data()` 메서드 수정**:
```python
# 페르소나 변경 시 TODO 데이터베이스 초기화
self._clear_todos_for_persona_change()
```

**`_load_from_cache()` 메서드 수정**:
```python
# 페르소나 변경 시 TODO 데이터베이스 초기화
self._clear_todos_for_persona_change()

# 캐시된 TODO 데이터 복원
cached_todos = cached_data.get('todos', [])
if cached_todos:
    # 캐시된 TODO를 데이터베이스에 저장
    self._restore_todos_from_cache(cached_todos)
else:
    # 캐시된 TODO가 없으면 메시지로부터 새로 생성
    self._trigger_background_analysis(messages)
```

### 2. TODO 초기화 메서드 추가

**`_clear_todos_for_persona_change()` 메서드**:
```python
def _clear_todos_for_persona_change(self) -> None:
    """페르소나 변경 시 TODO 데이터베이스 초기화"""
    try:
        if hasattr(self, 'todo_panel') and self.todo_panel:
            # TODO 데이터베이스 초기화
            cur = self.todo_panel.conn.cursor()
            cur.execute("DELETE FROM todos")
            self.todo_panel.conn.commit()
            
            # TODO 패널 UI 초기화
            self.todo_panel.todo_list.clear()
            
            logger.info("🗑️ 페르소나 변경으로 TODO 데이터베이스 초기화 완료")
```

### 3. 캐시된 TODO 복원 메서드 추가

**`_restore_todos_from_cache()` 메서드**:
```python
def _restore_todos_from_cache(self, cached_todos: List[Dict]) -> None:
    """캐시된 TODO를 데이터베이스에 복원"""
    try:
        if not cached_todos:
            return
        
        # TODO 데이터베이스에 저장
        from src.ui.main_window import _save_todos_to_db
        _save_todos_to_db(cached_todos, self.todo_panel.db_path)
        
        logger.info(f"💾 캐시된 TODO 복원 완료: {len(cached_todos)}개")
```

### 4. 분석 후 캐시 업데이트 개선

**`_quick_analysis()` 메서드 수정**:
```python
# TODO 패널 업데이트
if todos and hasattr(self, 'todo_panel'):
    self.todo_panel.populate_from_items(todos)
    logger.info(f"✅ 빠른 분석 완료: {len(todos)}개 TODO 생성")
    
    # 캐시에 TODO 업데이트
    self._update_cache_with_analysis_results(todos, [])
```

## 🎯 개선된 동작 방식

### 페르소나 변경 시나리오

#### 첫 번째 선택 (새 데이터 로드)
```
1. 페르소나 선택 (예: 이정두)
2. 🗑️ TODO 데이터베이스 초기화
3. 📡 새 메시지 수집 (이정두의 메시지)
4. 🔄 메시지 분석 및 TODO 생성
5. 💾 캐시에 저장 (메시지 + TODO)
6. 📋 TODO 패널 업데이트
```

#### 재선택 (캐시 사용)
```
1. 페르소나 재선택 (예: 이정두)
2. 🗑️ TODO 데이터베이스 초기화
3. 📂 캐시에서 데이터 로드
4. 💾 캐시된 TODO 복원
5. 📋 TODO 패널 업데이트
```

#### 다른 페르소나 선택
```
1. 페르소나 변경 (예: 임보연)
2. 🗑️ TODO 데이터베이스 초기화
3. 📡 새 메시지 수집 (임보연의 메시지)
4. 🔄 메시지 분석 및 TODO 생성
5. 💾 캐시에 저장
6. 📋 TODO 패널 업데이트
```

## 📊 예상 로그 패턴

### 페르소나 변경 시 나타날 로그:
```
2025-10-29 XX:XX:XX - src.ui.main_window - INFO - 🗑️ 페르소나 변경으로 TODO 데이터베이스 초기화 완료
2025-10-29 XX:XX:XX - src.ui.main_window - INFO - 📨 메시지 수집 완료: X개
2025-10-29 XX:XX:XX - src.ui.main_window - INFO - ✅ 빠른 분석 완료: X개 TODO 생성
2025-10-29 XX:XX:XX - src.ui.todo_panel - INFO - [프로젝트 태그] 활성 프로젝트 업데이트: {...}
```

### 캐시 사용 시 나타날 로그:
```
2025-10-29 XX:XX:XX - src.ui.main_window - INFO - 🗑️ 페르소나 변경으로 TODO 데이터베이스 초기화 완료
2025-10-29 XX:XX:XX - src.ui.main_window - INFO - 📂 캐시 로드 시작: persona_key=...
2025-10-29 XX:XX:XX - src.ui.main_window - INFO - 💾 캐시된 TODO 복원 완료: X개
2025-10-29 XX:XX:XX - src.ui.main_window - INFO - ✅ TODO 패널 새로고침 완료
```

## ✅ 해결된 문제

1. **페르소나별 TODO 분리**: 각 페르소나마다 독립적인 TODO 리스트
2. **캐시 일관성**: 캐시된 TODO와 실제 TODO 동기화
3. **UI 반응성**: 페르소나 변경 시 즉시 TODO 리스트 업데이트
4. **프로젝트 태그 유지**: 페르소나 변경 후에도 프로젝트 태그 정상 표시

## 🧪 테스트 방법

GUI에서 다음 시나리오를 테스트:

1. **이정두 선택** → TODO 리스트 확인 (이정두 관련 TODO만 표시)
2. **임보연 선택** → TODO 리스트 확인 (임보연 관련 TODO만 표시)
3. **이정두 재선택** → TODO 리스트 확인 (캐시된 이정두 TODO 복원)
4. **김용준 선택** → TODO 리스트 확인 (김용준 관련 TODO만 표시)

각 변경 시 로그에서 위의 패턴이 나타나는지 확인하세요.

## 🎉 기대 효과

- **정확한 TODO 분리**: 각 페르소나가 수신한 메시지에서만 TODO 생성
- **향상된 사용자 경험**: 페르소나 변경 시 명확한 TODO 리스트 변화
- **효율적인 캐싱**: 페르소나별 TODO 캐싱으로 성능 향상
- **일관된 프로젝트 태그**: 페르소나 변경 후에도 프로젝트 태그 정상 작동