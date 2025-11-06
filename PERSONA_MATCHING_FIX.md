# 페르소나 매칭 문제 해결

## 문제 상황
- 백그라운드 분석: 206개 TODO 생성
- TodoPanel 표시: 33개만 표시
- 원인: 페르소나 필터링 시 이메일/이름/핸들 불일치

## 원인 분석

**DB 저장 상태:**
```
전체 TODO: 206개
- 페르소나 없음: 173개
- 이정두: 33개
- leejungdu@example.com: 0개
```

**필터링 문제:**
1. TODO 저장 시: `persona_name = "이정두"` (한글 이름)
2. 필터링 시도: `persona_name = "leejungdu@example.com"` (이메일)
3. 결과: 매칭 실패 → 0개

**실제 표시되는 33개:**
- 페르소나 필터가 제대로 설정되지 않아 일부 TODO만 표시됨

## 해결 방법

### 1. TodoRepository.fetch_active() 수정
이메일, 이름, 채팅 핸들 모두로 매칭하도록 변경:

```python
def fetch_active(
    self, 
    persona_name: Optional[str] = None,
    persona_email: Optional[str] = None,
    persona_handle: Optional[str] = None
) -> List[dict]:
    """활성 TODO 조회 (페르소나 필터링 옵션)
    
    Note:
        이메일, 이름, 채팅 핸들 중 하나라도 매칭되면 해당 TODO를 반환합니다.
    """
    # 이메일, 이름, 채팅 핸들 중 하나라도 매칭되는 TODO 조회
    conditions = []
    if persona_name:
        conditions.append("persona_name=?")
    if persona_email:
        conditions.append("persona_name=?")
    if persona_handle:
        conditions.append("persona_name=?")
    
    # OR 조건으로 연결
    where_clause = " OR ".join(conditions)
    query = f"SELECT * FROM todos WHERE status!='done' AND ({where_clause}) ORDER BY created_at DESC"
```

### 2. TodoPanelController 수정
페르소나 정보를 모두 저장하고 전달:

```python
def __init__(self, ...):
    self._current_persona_filter: Optional[str] = None
    self._current_persona_email: Optional[str] = None
    self._current_persona_handle: Optional[str] = None

def set_persona_filter(
    self,
    persona_name: Optional[str] = None,
    persona_email: Optional[str] = None,
    persona_handle: Optional[str] = None
) -> None:
    """페르소나 필터 설정 (이메일, 이름, 핸들 모두 지원)"""
    self._current_persona_filter = persona_name
    self._current_persona_email = persona_email
    self._current_persona_handle = persona_handle
```

### 3. TodoPanel 수정
페르소나 정보를 모두 가져와서 전달:

```python
def refresh_todo_list(self, show_reasoning: bool = False) -> None:
    # 현재 페르소나 정보 가져오기
    persona_name = self._get_current_persona_name()
    persona_email = self._get_current_persona_email()
    persona_handle = self._get_current_persona_handle()
    
    # 페르소나 필터 설정
    self.controller.set_persona_filter(
        persona_name=persona_name,
        persona_email=persona_email,
        persona_handle=persona_handle
    )
```

### 4. 헬퍼 메서드 추가
```python
def _get_current_persona_handle(self) -> Optional[str]:
    """현재 선택된 페르소나의 채팅 핸들 가져오기"""
    parent_window = self.parent()
    while parent_window and not hasattr(parent_window, 'selected_persona'):
        parent_window = parent_window.parent()
    
    if parent_window and hasattr(parent_window, 'selected_persona') and parent_window.selected_persona:
        return parent_window.selected_persona.chat_handle
    return None
```

## 수정된 파일
- `offline_agent/src/ui/todo/repository.py`
  - `fetch_active()` 메서드: 이메일/이름/핸들 모두 매칭
  
- `offline_agent/src/ui/todo/controller.py`
  - 페르소나 이메일, 핸들 속성 추가
  - `set_persona_filter()` 메서드: 3가지 정보 모두 저장
  - `load_active_items()` 메서드: 3가지 정보 모두 전달

- `offline_agent/src/ui/todo_panel.py`
  - `refresh_todo_list()` 메서드: 페르소나 정보 수집 및 전달
  - `_get_current_persona_handle()` 메서드 추가

## 테스트 방법
1. 앱 재시작
2. VirtualOffice 연결 및 페르소나 선택
3. TODO 리스트 확인
4. 로그에서 페르소나 필터 설정 확인:
   ```
   👤 페르소나 필터 설정: 이름=이정두, 이메일=leejungdu@example.com, 핸들=lee_jd
   ```
5. 206개 TODO 중 해당 페르소나의 TODO가 모두 표시되는지 확인

## 기대 효과
- ✅ 이메일로 저장된 TODO도 매칭
- ✅ 한글 이름으로 저장된 TODO도 매칭
- ✅ 채팅 핸들로 저장된 TODO도 매칭
- ✅ 206개 TODO 중 해당 페르소나의 모든 TODO 표시
