# VirtualOffice 설정 관리

이 문서는 offline_agent의 VirtualOffice 연동 설정을 관리하는 방법을 설명합니다.

## 설정 파일

설정은 다음 경로에 JSON 파일로 저장됩니다:

```
data/multi_project_8week_ko/virtualoffice_config.json
```

### 설정 파일 형식

```json
{
  "email_url": "http://127.0.0.1:8000",
  "chat_url": "http://127.0.0.1:8001",
  "sim_url": "http://127.0.0.1:8015",
  "polling_interval": 5,
  "selected_persona": "pm.1@multiproject.dev"
}
```

## 자동 저장 및 로드

### 자동 저장

VirtualOffice 연결에 성공하면 설정이 자동으로 저장됩니다:

1. GUI에서 "🔌 연결 테스트" 버튼 클릭
2. 연결 성공 시 현재 URL 설정이 자동으로 파일에 저장됨
3. 선택된 페르소나 정보도 함께 저장됨

### 자동 로드

애플리케이션 시작 시 설정 파일이 자동으로 로드됩니다:

1. `run_gui.py` 실행
2. 설정 파일이 있으면 자동으로 로드
3. URL 입력 필드에 저장된 값이 자동으로 채워짐
4. 다음 연결 시 저장된 URL 사용 가능

## 환경 변수 지원

환경 변수를 사용하여 설정을 덮어쓸 수 있습니다. 환경 변수는 설정 파일보다 우선순위가 높습니다.

### 지원되는 환경 변수

```bash
# Windows (cmd)
set VDOS_EMAIL_URL=http://127.0.0.1:8000
set VDOS_CHAT_URL=http://127.0.0.1:8001
set VDOS_SIM_URL=http://127.0.0.1:8015

# Windows (PowerShell)
$env:VDOS_EMAIL_URL="http://127.0.0.1:8000"
$env:VDOS_CHAT_URL="http://127.0.0.1:8001"
$env:VDOS_SIM_URL="http://127.0.0.1:8015"

# Linux/Mac
export VDOS_EMAIL_URL=http://127.0.0.1:8000
export VDOS_CHAT_URL=http://127.0.0.1:8001
export VDOS_SIM_URL=http://127.0.0.1:8015
```

### 우선순위

설정 적용 우선순위는 다음과 같습니다:

1. **환경 변수** (최우선)
2. **설정 파일** (`virtualoffice_config.json`)
3. **기본값** (http://127.0.0.1:8000, 8001, 8015)

## 사용 예시

### 예시 1: 기본 사용

```bash
# 1. 애플리케이션 실행
python run_gui.py

# 2. VirtualOffice 연동 패널에서 URL 입력
#    - Email Server: http://127.0.0.1:8000
#    - Chat Server: http://127.0.0.1:8001
#    - Sim Manager: http://127.0.0.1:8015

# 3. "🔌 연결 테스트" 버튼 클릭

# 4. 연결 성공 시 설정이 자동으로 저장됨

# 5. 다음 실행 시 저장된 URL이 자동으로 로드됨
```

### 예시 2: 환경 변수 사용

```bash
# 1. 환경 변수 설정
set VDOS_EMAIL_URL=http://192.168.1.100:8000
set VDOS_CHAT_URL=http://192.168.1.100:8001
set VDOS_SIM_URL=http://192.168.1.100:8015

# 2. 애플리케이션 실행
python run_gui.py

# 3. 환경 변수의 URL이 자동으로 적용됨
```

### 예시 3: 설정 파일 직접 편집

```bash
# 1. 설정 파일 열기
notepad data\multi_project_8week_ko\virtualoffice_config.json

# 2. URL 수정
{
  "email_url": "http://localhost:9000",
  "chat_url": "http://localhost:9001",
  "sim_url": "http://localhost:9015",
  "polling_interval": 10,
  "selected_persona": "pm.1@multiproject.dev"
}

# 3. 저장 후 애플리케이션 재시작
python run_gui.py
```

## 설정 초기화

설정을 초기화하려면 설정 파일을 삭제하면 됩니다:

```bash
# Windows
del data\multi_project_8week_ko\virtualoffice_config.json

# Linux/Mac
rm data/multi_project_8week_ko/virtualoffice_config.json
```

다음 실행 시 기본값이 사용됩니다.

## 문제 해결

### 설정 파일이 로드되지 않음

**증상**: 저장된 URL이 UI에 표시되지 않음

**해결 방법**:
1. 설정 파일 경로 확인: `data/multi_project_8week_ko/virtualoffice_config.json`
2. 파일 권한 확인 (읽기 권한 필요)
3. JSON 형식 검증 (유효한 JSON인지 확인)
4. 로그 확인: `LOG_LEVEL=DEBUG python run_gui.py`

### 설정이 저장되지 않음

**증상**: 연결 성공 후에도 다음 실행 시 URL이 비어있음

**해결 방법**:
1. 디렉토리 권한 확인 (쓰기 권한 필요)
2. 디스크 공간 확인
3. 로그 확인: "VirtualOffice 설정 저장 완료" 메시지 확인

### 환경 변수가 적용되지 않음

**증상**: 환경 변수를 설정했지만 기본값이 사용됨

**해결 방법**:
1. 환경 변수 이름 확인 (대소문자 구분)
2. 환경 변수가 올바르게 설정되었는지 확인:
   ```bash
   # Windows
   echo %VDOS_EMAIL_URL%
   
   # Linux/Mac
   echo $VDOS_EMAIL_URL
   ```
3. 애플리케이션 재시작

## 관련 문서

- [VirtualOffice 연동 테스트 가이드](VIRTUALOFFICE_TESTING.md)
- [실시간 기능 테스트 가이드](REALTIME_TESTING.md)
- [GUI 실시간 통합 문서](GUI_REALTIME_INTEGRATION.md)

## API 참조

### VirtualOfficeConfig

```python
from src.integrations.models import VirtualOfficeConfig

# 설정 객체 생성
config = VirtualOfficeConfig(
    email_url="http://127.0.0.1:8000",
    chat_url="http://127.0.0.1:8001",
    sim_url="http://127.0.0.1:8015",
    polling_interval=5,
    selected_persona="pm.1@multiproject.dev"
)

# 파일에 저장
config.save_to_file(Path("data/virtualoffice_config.json"))

# 파일에서 로드
config = VirtualOfficeConfig.load_from_file(Path("data/virtualoffice_config.json"))

# 딕셔너리로 변환
config_dict = config.to_dict()

# 딕셔너리에서 생성
config = VirtualOfficeConfig.from_dict(config_dict)
```

### SmartAssistantGUI

```python
# 설정 로드 (자동 호출됨)
self._load_vo_config()

# 설정 저장 (연결 성공 시 자동 호출됨)
self._save_vo_config()
```
