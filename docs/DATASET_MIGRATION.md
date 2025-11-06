# 데이터셋 마이그레이션 가이드

## 변경 사항 요약

### 데이터셋 변경
- **기존**: `data/mobile_4week_ko` (4주 데이터)
- **신규**: `data/multi_project_8week_ko` (8주 데이터)

### PM 정보 변경
- **기존**: 
  - 이름: (미지정)
  - 이메일: pm.1@quickchat.dev
  - 채팅 핸들: pm

- **신규**: 
  - 이름: 이민주
  - 이메일: pm.1@multiproject.dev
  - 채팅 핸들: pm
  - 역할: 프로젝트 매니저

## 수정된 파일

### 1. main.py
**변경 위치**: Line 21
```python
# 기존
DEFAULT_DATASET_ROOT = project_root / "data" / "mobile_4week_ko"

# 변경
DEFAULT_DATASET_ROOT = project_root / "data" / "multi_project_8week_ko"
```

**변경 위치**: Line 426
```python
# 기존
logger.info("📥 메시지 수집 시작 (mobile_4week_ko)")

# 변경
logger.info("📥 메시지 수집 시작 (multi_project_8week_ko - 이민주 PM)")
```

**변경 위치**: Line 433-434
```python
# 기존
pm_email = (self.user_profile or {}).get("email_address", "pm.1@quickchat.dev").lower()

# 변경
pm_email = (self.user_profile or {}).get("email_address", "pm.1@multiproject.dev").lower()
```

### 2. ui/main_window.py
**변경 위치**: Line 43
```python
# 기존
TODO_DB_PATH = os.path.join("data", "mobile_4week_ko", "todos_cache.db")

# 변경
TODO_DB_PATH = os.path.join("data", "multi_project_8week_ko", "todos_cache.db")
```

### 3. ui/todo_panel.py
**변경 위치**: Line 21
```python
# 기존
TODO_DB_PATH = os.path.join("data", "mobile_4week_ko", "todos_cache.db")

# 변경
TODO_DB_PATH = os.path.join("data", "multi_project_8week_ko", "todos_cache.db")
```

## 필터링 로직

### PM 수신 메시지 필터링
이민주 PM이 **수신한** 메시지만 표시됩니다.

#### 이메일 필터링
```python
# 이메일의 to, cc, bcc 필드에 pm.1@multiproject.dev가 포함된 경우만 표시
recipients = msg.get("recipients", []) or []
cc = msg.get("cc", []) or []
bcc = msg.get("bcc", []) or []
all_recipients = [r.lower() for r in (recipients + cc + bcc)]
return "pm.1@multiproject.dev" in all_recipients
```

#### 메신저 필터링
```python
# DM 룸에서 PM handle("pm")이 포함된 경우만 표시
# 예: dm:pm:designer (O), dm:designer:dev (X)
room_slug = msg.get("room_slug", "").lower()
if room_slug.startswith("dm:"):
    room_parts = room_slug.split(":")
    return "pm" in room_parts

# 그룹 채팅은 모두 포함
return True
```

## 데이터 구조

### team_personas.json
```json
{
  "name": "이민주",
  "role": "프로젝트 매니저",
  "email_address": "pm.1@multiproject.dev",
  "chat_handle": "pm",
  "is_department_head": true,
  "skills": [
    "Agile",
    "Scrum",
    "프로젝트 관리",
    "이해관계자 커뮤니케이션",
    "문제 해결"
  ]
}
```

### 팀 구성원
1. **이민주** - 프로젝트 매니저 (PM)
2. **김민준** - 모바일/웹 UI/UX 디자이너
3. **이준호** - 풀스택 개발자
4. **이정현** - 데보옵스 엔지니어

## 테스트 방법

### 1. 데이터 확인
```bash
# 새 데이터셋 파일 확인
ls data/multi_project_8week_ko/

# 예상 파일:
# - team_personas.json
# - chat_communications.json
# - email_communications.json
# - final_state.json
```

### 2. 애플리케이션 실행
```bash
python run_gui.py
```

### 3. 메시지 수집
1. "메시지 수집 시작" 버튼 클릭
2. 로그 확인:
   ```
   📥 메시지 수집 시작 (multi_project_8week_ko - 이민주 PM)
   👤 PM 필터링: email=pm.1@multiproject.dev, handle=pm
   👤 PM 수신 메시지 필터링 완료: chat X→Y, email A→B
   ```

### 4. 결과 확인
- **TODO 탭**: 이민주 PM이 수신한 메시지에서 생성된 TODO만 표시
- **메시지 탭**: 이민주 PM이 수신한 메신저 메시지만 표시
- **메일 탭**: 이민주 PM이 수신한 이메일만 표시

## 주의사항

### 1. PM이 보낸 메시지는 제외
- 이민주 PM이 **보낸** 메시지는 필터링에서 제외됩니다
- PM이 **수신한** 메시지만 TODO로 변환됩니다

### 2. 그룹 채팅
- 그룹 채팅은 현재 모두 포함됩니다
- 향후 개선 예정

### 3. 데이터베이스 위치
- TODO 데이터베이스: `data/multi_project_8week_ko/todos_cache.db`
- 기존 데이터베이스는 자동으로 마이그레이션되지 않습니다
- 새로운 데이터베이스가 자동으로 생성됩니다

## 롤백 방법

기존 데이터셋으로 돌아가려면:

### 1. main.py
```python
DEFAULT_DATASET_ROOT = project_root / "data" / "mobile_4week_ko"
```

### 2. ui/main_window.py
```python
TODO_DB_PATH = os.path.join("data", "mobile_4week_ko", "todos_cache.db")
```

### 3. ui/todo_panel.py
```python
TODO_DB_PATH = os.path.join("data", "mobile_4week_ko", "todos_cache.db")
```

### 4. main.py (PM 이메일)
```python
pm_email = (self.user_profile or {}).get("email_address", "pm.1@quickchat.dev").lower()
```

## 문제 해결

### 메시지가 수집되지 않는 경우
1. 데이터 파일 확인:
   ```bash
   ls data/multi_project_8week_ko/*.json
   ```

2. PM 정보 확인:
   ```bash
   cat data/multi_project_8week_ko/team_personas.json | grep -A 5 "이민주"
   ```

3. 로그 확인:
   ```bash
   tail -f logs/smart_assistant.log
   ```

### TODO가 생성되지 않는 경우
1. PM 수신 메시지 필터링 로그 확인
2. 메시지 수가 0이 아닌지 확인
3. 시간 범위 설정 확인 (기본: 최근 30일)

## 참고 문서
- [SUMMARIZER_FLOW.md](SUMMARIZER_FLOW.md) - 메시지 요약 흐름
- [MESSAGE_GROUPING.md](MESSAGE_GROUPING.md) - 메시지 그룹화
- [TODO_DETAIL_IMPROVEMENTS.md](TODO_DETAIL_IMPROVEMENTS.md) - TODO 상세 기능
