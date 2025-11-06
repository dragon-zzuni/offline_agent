# 프로젝트 태그 문제 해결 요약

## 🎯 발견한 문제

### 1. source_message에 메시지 내용이 없음
- **문제**: TODO의 `source_message` 필드에 메시지 ID만 저장되고 실제 내용이 없음
- **영향**: 프로젝트 태그 추출 시 원본 메시지 내용을 참조할 수 없어서 프로젝트를 추출할 수 없음
- **해결**: `analysis_pipeline_service.py`에서 TODO 생성 시 전체 메시지 객체를 JSON으로 저장하도록 수정

### 2. 김세린 TODO의 프로젝트 태그 비율이 매우 낮음
- **현황**: 66개 TODO 중 프로젝트 태그가 있는 것은 1개 (1.5%)
- **원인**: source_message에 내용이 없어서 프로젝트 추출 실패
- **캐시**: 프로젝트 태그 캐시에는 459개가 저장되어 있지만 TODO에 적용되지 않음

### 3. 비동기 프로젝트 태그 서비스가 작동하지 않음
- **문제**: `AsyncProjectTagService`가 초기화되지만 실제로 사용되지 않음
- **원인**: TODO 패널에서 프로젝트 태그 분석을 요청하는 로직이 없음

### 4. 현재 페르소나의 TODO 우선 처리 없음
- **문제**: 모든 TODO를 순차적으로 처리하여 현재 보고 있는 페르소나의 TODO가 늦게 분석됨
- **영향**: GUI에서 프로젝트 태그가 늦게 나타남

## ✅ 적용한 수정

### 1. source_message에 전체 메시지 저장
**파일**: `offline_agent/src/services/analysis_pipeline_service.py`

```python
# Before
todo_item = {
    ...
    "source_message": action_source_id,  # 메시지 ID만
    ...
}

# After
import json
source_message_full = json.dumps(message, ensure_ascii=False) if message else action_source_id

todo_item = {
    ...
    "source_message": source_message_full,  # 전체 메시지 JSON
    ...
}
```

**효과**: 
- 프로젝트 태그 추출 시 원본 메시지의 제목, 본문, 발신자 정보를 모두 사용 가능
- 프로젝트 키워드 매칭 정확도 향상

## 📋 다음 단계 (추가 작업 필요)

### 1. 기존 TODO 재분석
기존에 생성된 TODO는 source_message에 ID만 있으므로 재분석 필요:

```bash
# 방법 1: 모든 TODO 삭제 후 재생성
python offline_agent/cleanup_duplicate_todos.py

# 방법 2: VDOS DB에서 원본 메시지를 찾아서 source_message 업데이트
# (스크립트 작성 필요)
```

### 2. 비동기 프로젝트 태그 서비스 통합
TODO 패널에서 프로젝트 태그 분석을 요청하도록 수정:

```python
# todo_panel.py에 추가
def _init_async_project_tag_service(self, project_service):
    """비동기 프로젝트 태그 서비스 초기화"""
    from src.services.async_project_tag_service import AsyncProjectTagService
    
    self.async_project_service = AsyncProjectTagService(
        project_service=project_service,
        repository=self._repo
    )
    self.async_project_service.start()

def queue_new_todos_for_async_analysis(self, todos: List[Dict]):
    """새 TODO를 프로젝트 태그 분석 큐에 추가 (현재 페르소나 우선)"""
    if not hasattr(self, 'async_project_service'):
        return
    
    # 현재 페르소나의 TODO를 먼저 큐에 추가
    persona_name = self._get_current_persona_name()
    current_persona_todos = [t for t in todos if t.get('persona_name') == persona_name]
    other_todos = [t for t in todos if t.get('persona_name') != persona_name]
    
    # 우선순위: 현재 페르소나 → 다른 페르소나
    for todo in current_persona_todos + other_todos:
        self.async_project_service.queue_todo_for_analysis(
            todo_id=todo.get('id'),
            todo_data=todo,
            callback=self._on_project_tag_updated
        )

def _on_project_tag_updated(self, todo_id: str, project: str):
    """프로젝트 태그 업데이트 콜백"""
    logger.info(f"[TodoPanel] 프로젝트 태그 업데이트: {todo_id} → {project}")
    # UI 업데이트 (해당 TODO 위젯만)
    self._update_todo_widget_project_tag(todo_id, project)
```

### 3. GUI 실시간 업데이트
프로젝트 태그가 분석되면 즉시 UI에 반영:

```python
def _update_todo_widget_project_tag(self, todo_id: str, project: str):
    """특정 TODO 위젯의 프로젝트 태그만 업데이트"""
    for i in range(self.todo_list.count()):
        item = self.todo_list.item(i)
        widget = self.todo_list.itemWidget(item)
        if widget and hasattr(widget, 'todo'):
            if widget.todo.get('id') == todo_id:
                widget.todo['project'] = project
                # 프로젝트 태그 라벨 추가/업데이트
                self._add_project_tag_to_widget(widget, project)
                break
```

## 🔍 테스트 방법

### 1. 새 TODO 생성 테스트
```bash
# GUI 재시작 후 새로운 분석 실행
# source_message에 전체 메시지가 저장되는지 확인
python offline_agent/check_source_message_content.py
```

### 2. 프로젝트 태그 추출 테스트
```bash
# 새로 생성된 TODO의 프로젝트 태그 확인
python offline_agent/check_current_persona_todos.py
```

### 3. GUI 확인
- 김세린 페르소나 선택
- TODO 리스트에서 프로젝트 태그가 표시되는지 확인
- 프로젝트 필터 바에서 필터링이 작동하는지 확인

## 📊 예상 결과

### Before
- 김세린 TODO 66개 중 프로젝트 태그 1개 (1.5%)
- source_message에 내용 없음
- 프로젝트 태그가 GUI에 거의 표시되지 않음

### After
- 김세린 TODO 66개 중 프로젝트 태그 30-40개 (50-60%)
- source_message에 전체 메시지 JSON 저장
- 프로젝트 태그가 GUI에 즉시 표시
- 현재 페르소나의 TODO가 우선 분석됨

## 🚀 즉시 적용 가능한 임시 해결책

기존 TODO를 모두 삭제하고 재생성:

```bash
# 1. GUI 종료
# 2. TODO DB 삭제
rm virtualoffice/src/virtualoffice/todos_cache.db

# 3. GUI 재시작
python offline_agent/run_gui.py

# 4. 분석 실행
# - 페르소나 선택
# - "분석 시작" 버튼 클릭
# - 새로운 TODO가 생성되면서 source_message에 전체 내용 저장됨
```

이 방법으로 즉시 프로젝트 태그가 제대로 표시될 것입니다!
