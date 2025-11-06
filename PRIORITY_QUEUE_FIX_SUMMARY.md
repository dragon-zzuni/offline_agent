# 프로젝트 태그 우선순위 큐 수정 완료

## ✅ 수정 완료 사항

### 1. AttributeError 수정
**파일**: `offline_agent/src/ui/main_window_components/connection_controller.py`

```python
# Before (오류)
ui.analysis_cache_controller.start_quick_analysis(force=True)

# After (수정)
ui.analysis_controller.start_quick_analysis(force=True)
```

**효과**: 실시간 연결 시 AttributeError 해결

### 2. 우선순위 큐 구현
**파일**: `offline_agent/src/services/async_project_tag_service.py`

**변경사항**:
- `Queue` → `PriorityQueue`로 변경
- `priority` 파라미터 추가 (True=우선, False=일반)
- 우선순위 0 (높음) vs 1 (낮음)으로 구분

```python
# Before
self.task_queue = Queue()

# After  
self.task_queue = PriorityQueue()  # 우선순위 큐
self._task_counter = 0  # 순서 보장용

# 큐에 추가 시
priority_value = 0 if priority else 1  # 0=우선, 1=일반
self.task_queue.put((priority_value, self._task_counter, task))
```

**효과**: 
- 현재 페르소나의 TODO가 먼저 분석됨
- 페르소나 교체 시에도 새 페르소나의 TODO 우선 처리

## 📋 사용 방법

### TODO 패널에서 우선 분석 요청

```python
# 현재 페르소나의 TODO를 우선 큐에 추가
current_persona_name = self._get_current_persona_name()

for todo in todos:
    is_priority = todo.get('persona_name') == current_persona_name
    
    async_service.queue_todo_for_analysis(
        todo_id=todo['id'],
        todo_data=todo,
        callback=self._on_project_tag_updated,
        priority=is_priority  # 현재 페르소나면 우선 처리
    )
```

## 🎯 예상 동작

### Before (우선순위 없음)
```
큐: [TODO1(이정두), TODO2(김세린), TODO3(이정두), TODO4(김세린), ...]
처리 순서: 1 → 2 → 3 → 4 → ...
결과: 김세린 페르소나 선택 시에도 이정두 TODO가 먼저 분석됨
```

### After (우선순위 큐)
```
현재 페르소나: 김세린
큐: [(0, TODO2(김세린)), (0, TODO4(김세린)), (1, TODO1(이정두)), (1, TODO3(이정두)), ...]
처리 순서: 2 → 4 → 1 → 3 → ...
결과: 김세린 TODO가 먼저 분석되어 GUI에 즉시 표시됨!
```

## 🚀 다음 단계

TODO 패널이나 Controller에서 현재 페르소나의 TODO를 우선 큐에 추가하도록 수정 필요:

```python
# todo_panel.py 또는 controller.py에 추가
def queue_todos_with_priority(self, todos):
    """현재 페르소나의 TODO를 우선 분석"""
    current_persona = self._get_current_persona_name()
    
    # 현재 페르소나 TODO 먼저
    priority_todos = [t for t in todos if t.get('persona_name') == current_persona]
    other_todos = [t for t in todos if t.get('persona_name') != current_persona]
    
    for todo in priority_todos:
        self.async_service.queue_todo_for_analysis(
            todo['id'], todo, priority=True
        )
    
    for todo in other_todos:
        self.async_service.queue_todo_for_analysis(
            todo['id'], todo, priority=False
        )
```

## ✅ 테스트 방법

1. GUI 재시작
2. 실시간 연결 클릭
3. 김세린 페르소나 선택
4. 로그 확인:
   ```
   [AsyncProjectTag] todo_xxx: 분석 큐에 추가 (우선, 큐 크기: 10)
   [AsyncProjectTag] todo_yyy: 분석 큐에 추가 (일반, 큐 크기: 20)
   ```
5. TODO 리스트에서 김세린 TODO의 프로젝트 태그가 먼저 표시되는지 확인

## 🎉 기대 효과

- 실시간 연결 시 AttributeError 해결
- 현재 페르소나의 TODO 프로젝트 태그가 즉시 표시
- 페르소나 교체 시에도 새 페르소나 TODO 우선 분석
- 사용자 경험 대폭 개선!
