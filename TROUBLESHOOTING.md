# 문제 해결 가이드 (Troubleshooting)

이 문서는 Smart Assistant (offline_agent) 사용 중 발생할 수 있는 일반적인 문제와 해결 방법을 설명합니다.

## 목차

- [일반 문제](#일반-문제)
- [VirtualOffice 연동 문제](#virtualoffice-연동-문제)
- [데이터 수집 문제](#데이터-수집-문제)
- [GUI 문제](#gui-문제)
- [성능 문제](#성능-문제)

---

## 일반 문제

### 애플리케이션이 시작되지 않음

**증상**: `python run_gui.py` 실행 시 오류 발생

**원인**:
- Python 버전 불일치 (3.10+ 필요)
- 필수 패키지 미설치
- 환경 변수 설정 오류

**해결 방법**:

```bash
# 1. Python 버전 확인
python --version  # 3.10 이상이어야 함

# 2. 의존성 재설치
pip install -r requirements.txt

# 3. 환경 변수 확인
# .env 파일이 있는지 확인
# LLM_PROVIDER, OPENAI_API_KEY 등 필수 변수 설정
```

### 한글이 깨져서 표시됨

**증상**: GUI에서 한글이 □□□ 또는 ??? 로 표시됨

**원인**:
- Windows 인코딩 설정 문제
- 한글 폰트 미설치

**해결 방법**:

```bash
# 환경 변수 설정 (Windows)
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

# 또는 run_gui.bat 사용 (자동 설정됨)
run_gui.bat
```

---

## VirtualOffice 연동 문제

### 서버 연결 실패

**증상**: "일부 서버 연결 실패" 오류 메시지

**원인**:
- VirtualOffice 서버가 실행되지 않음
- 잘못된 URL 입력
- 방화벽 차단

**해결 방법**:

```bash
# 1. VirtualOffice 서버 시작 확인
cd virtualoffice
briefcase dev

# 2. 서버 상태 확인 (브라우저에서)
http://127.0.0.1:8000/docs  # Email Server
http://127.0.0.1:8001/docs  # Chat Server
http://127.0.0.1:8015/docs  # Simulation Manager

# 3. 포트 사용 확인
netstat -ano | findstr :8000
netstat -ano | findstr :8001
netstat -ano | findstr :8015

# 4. 방화벽 예외 추가 (필요시)
# Windows Defender 방화벽 설정에서 Python 허용
```

### 페르소나 목록이 비어있음

**증상**: "페르소나 목록이 비어있습니다" 오류

**원인**:
- 시뮬레이션이 초기화되지 않음
- 데이터베이스 파일 손상

**해결 방법**:

```bash
# 1. VirtualOffice GUI에서 시나리오 선택
# 2. "Initialize" 버튼 클릭
# 3. 데이터베이스 확인
# virtualoffice/vdos.db 파일이 있는지 확인

# 4. 데이터베이스 재생성 (필요시)
# vdos.db 파일 삭제 후 시뮬레이션 재초기화
```

### 새 데이터가 수집되지 않음

**증상**: PollingWorker가 실행 중이지만 새 데이터가 없음

**원인**:
- 시뮬레이션이 일시정지됨
- 시뮬레이션 속도가 느림
- 새 커뮤니케이션이 생성되지 않음

**해결 방법**:

```bash
# 1. 시뮬레이션 상태 확인
# GUI에서 "실행 중" 상태인지 확인

# 2. Auto Tick 활성화
# VirtualOffice GUI에서 Auto Tick 체크박스 활성화

# 3. 시뮬레이션 진행 대기
# 30초 이상 기다린 후 다시 확인

# 4. 로그 확인
set LOG_LEVEL=DEBUG
python run_gui.py
# "새 데이터 수집" 로그 메시지 확인
```

### 틱이 진행되지 않음

**증상**: SimulationMonitor가 틱 진행을 감지하지 못함

**원인**:
- 시뮬레이션이 정지됨
- Auto Tick이 비활성화됨
- 시뮬레이션이 완료됨

**해결 방법**:

```bash
# 1. VirtualOffice GUI에서 "Start" 버튼 클릭
# 2. Auto Tick 체크박스 활성화
# 3. 시뮬레이션 상태 확인
#    - 현재 틱이 증가하는지 확인
#    - "실행 중" 상태인지 확인

# 4. 새 시뮬레이션 시작 (필요시)
# VirtualOffice GUI에서 시나리오 재선택 및 Initialize
```

### 설정 파일이 로드되지 않음

**증상**: 저장된 URL이 UI에 표시되지 않음

**원인**:
- 설정 파일 경로 오류
- 파일 권한 문제
- JSON 형식 오류

**해결 방법**:

```bash
# 1. 설정 파일 경로 확인
# data/multi_project_8week_ko/virtualoffice_config.json

# 2. 파일 권한 확인 (읽기 권한 필요)
# 파일 속성에서 읽기 전용 해제

# 3. JSON 형식 검증
# 온라인 JSON 검증 도구 사용
# https://jsonlint.com/

# 4. 로그 확인
set LOG_LEVEL=DEBUG
python run_gui.py
# "VirtualOffice 설정 파일 로드" 로그 확인
```

### 환경 변수가 적용되지 않음

**증상**: 환경 변수를 설정했지만 기본값이 사용됨

**원인**:
- 환경 변수 이름 오류 (대소문자 구분)
- 환경 변수가 올바르게 설정되지 않음
- 애플리케이션 재시작 필요

**해결 방법**:

```bash
# 1. 환경 변수 이름 확인
# VDOS_EMAIL_URL (대문자)
# VDOS_CHAT_URL
# VDOS_SIM_URL

# 2. 환경 변수 설정 확인 (Windows)
echo %VDOS_EMAIL_URL%

# 3. 환경 변수 설정 (Windows cmd)
set VDOS_EMAIL_URL=http://127.0.0.1:8000
set VDOS_CHAT_URL=http://127.0.0.1:8001
set VDOS_SIM_URL=http://127.0.0.1:8015

# 4. 애플리케이션 재시작
python run_gui.py
```

---

## 데이터 수집 문제

### "수집할 메시지가 없습니다" 오류

**증상**: 메시지 수집 시 오류 발생

**원인**:
- 시간 범위 필터가 너무 좁음
- 데이터셋에 메시지가 없음
- PM 필터링으로 모든 메시지가 제외됨

**해결 방법**:

```bash
# 1. 시간 범위 확장
# "전체 기간" 버튼 클릭

# 2. 데이터셋 확인
# data/multi_project_8week_ko/ 폴더에
# chat_communications.json, email_communications.json 파일 확인

# 3. PM 페르소나 확인
# team_personas.json에서 PM 페르소나 정보 확인
# chat_handle: "pm"
# email_address: "pm.1@multiproject.dev"
```

### 메시지 수집이 느림

**증상**: 메시지 수집에 시간이 오래 걸림

**원인**:
- 대량의 메시지 처리
- LLM API 호출 지연
- 네트워크 속도 문제

**해결 방법**:

```bash
# 1. 메시지 수 제한
# collect_options에서 email_limit, messenger_limit 설정

# 2. LLM 타임아웃 조정
# .env 파일에서 타임아웃 설정

# 3. 네트워크 확인
# 인터넷 연결 상태 확인
# VPN 사용 시 비활성화 시도
```

### LLM 기반 Top3 선정 문제 ✨ NEW (v1.4.0)

**증상**: 자연어 규칙을 입력했지만 Top3가 선정되지 않음

**원인**:
- LLM API 키 미설정 또는 잘못된 설정
- LLM 서비스 장애 또는 네트워크 문제
- 연속 3회 실패로 LLM 자동 비활성화
- 규칙에 맞는 TODO가 없음

**해결 방법**:

```bash
# 1. API 키 확인
# .env 파일에서 다음 중 하나 설정 확인:
# OPENAI_API_KEY=sk-...
# AZURE_OPENAI_KEY=...
# OPENROUTER_API_KEY=sk-or-...

# 2. LLM 제공자 설정 확인
# LLM_PROVIDER=openai  # 또는 azure, openrouter

# 3. 로그 확인
set LOG_LEVEL=DEBUG
python run_gui.py
# [Top3Service] 로그 메시지 확인

# 4. LLM 수동 재활성화
# GUI에서 "LLM 모드 활성화" 버튼 클릭 (있는 경우)
```

**로그 예시 (정상):**
```
[Top3Service] 🤖 LLM 모드: 자연어 규칙 기반 Top3 선정 시도
[Top3Service] ✅ LLM 선정 성공: 3개 선정
```

**로그 예시 (오류):**
```
[Top3Service] ❌ LLM 선정 실패 (1/3): API key not found
[Top3Service] 📊 폴백: 점수 기반 선정으로 전환
```

**증상**: "규칙에 맞는 TODO가 없음" 메시지 표시

**원인**:
- 입력한 규칙이 현재 TODO와 매칭되지 않음
- 요청자 이름이 정확하지 않음
- 프로젝트 태그가 존재하지 않음

**해결 방법**:

```bash
# 1. 규칙 확인
# 실제 TODO의 요청자 이름과 일치하는지 확인
# 예: "유준영" vs "yujunyoung@example.com"

# 2. 프로젝트 태그 확인
# TODO에 실제로 할당된 프로젝트 태그 확인

# 3. 더 넓은 규칙 사용
# "유준영 최우선" → "유준영 또는 김세린 우선"
# "CARE 프로젝트만" → "CARE 또는 HEAL 프로젝트 우선"
```

**증상**: LLM 응답이 너무 느림 (30초 이상)

**원인**:
- LLM 서비스 과부하
- 네트워크 지연
- 타임아웃 설정이 너무 김

**해결 방법**:

```bash
# 1. 타임아웃 조정
# .env 파일에 추가:
TOP3_LLM_TIMEOUT=15  # 기본값 30초 → 15초로 단축

# 2. 다른 LLM 제공자 시도
# OpenAI → Azure OpenAI 또는 OpenRouter로 전환

# 3. 점수 기반 모드 사용
# 자연어 규칙을 제거하고 기존 점수 기반 시스템 사용
```

---

## GUI 문제

### GUI가 응답하지 않음 (멈춤)

**증상**: 버튼 클릭 시 GUI가 멈춤

**원인**:
- 장시간 작업이 메인 스레드에서 실행됨
- 워커 스레드 오류

**해결 방법**:

```bash
# 1. 작업 완료 대기
# 프로그레스 바가 표시되면 완료될 때까지 대기

# 2. 애플리케이션 재시작
# Ctrl+C 또는 작업 관리자에서 종료 후 재시작

# 3. 로그 확인
set LOG_LEVEL=DEBUG
python run_gui.py
# 오류 메시지 확인
```

### TODO 리스트가 표시되지 않음

**증상**: 분석 완료 후 TODO 탭이 비어있음

**원인**:
- 액션 추출 실패
- 데이터베이스 오류
- 필터링으로 모든 TODO 제외됨

**해결 방법**:

```bash
# 1. 분석 결과 탭 확인
# 메시지가 분석되었는지 확인

# 2. 데이터베이스 확인
# data/multi_project_8week_ko/todos_cache.db 파일 확인

# 3. 데이터베이스 재생성 (필요시)
# todos_cache.db 파일 삭제 후 재분석

# 4. 로그 확인
# "TODO 리스트 생성" 로그 메시지 확인
```

---

## 성능 문제

### 메모리 사용량이 계속 증가함

**증상**: 장시간 실행 시 메모리 사용량 증가

**원인**:
- 대량의 메시지가 메모리에 누적됨
- 캐시 정리가 작동하지 않음

**해결 방법**:

```bash
# 1. 애플리케이션 재시작
# 주기적으로 재시작하여 메모리 정리

# 2. 시간 범위 필터 사용
# 필요한 기간의 메시지만 로드

# 3. 메시지 수 제한
# collect_options에서 overall_limit 설정

# 4. 자동 정리 확인
# VirtualOfficeDataSource.cleanup_old_messages() 호출 확인
```

### CPU 사용률이 높음

**증상**: CPU 사용률이 지속적으로 높음

**원인**:
- 폴링 간격이 너무 짧음
- 백그라운드 작업이 과도함

**해결 방법**:

```bash
# 1. 폴링 간격 조정
# PollingWorker.set_polling_interval(10)  # 10초로 증가

# 2. 불필요한 워커 중지
# PollingWorker.stop()
# SimulationMonitor.stop_monitoring()

# 3. 시뮬레이션 일시정지
# VirtualOffice GUI에서 Pause 버튼 클릭
```

---

## 로그 확인 방법

상세한 로그를 확인하려면 DEBUG 레벨로 실행하세요:

```bash
# Windows (cmd)
set LOG_LEVEL=DEBUG
python run_gui.py

# Windows (PowerShell)
$env:LOG_LEVEL="DEBUG"
python run_gui.py

# Linux/Mac
export LOG_LEVEL=DEBUG
python run_gui.py
```

로그 메시지 예시:

```
2025-10-21 15:30:00 - INFO - VirtualOffice 서버 연결 테스트 중...
2025-10-21 15:30:01 - INFO - ✅ 모든 서버 연결 성공
2025-10-21 15:30:02 - INFO - 페르소나 목록 조회 중...
2025-10-21 15:30:03 - INFO - ✅ 4개 페르소나 조회 완료
2025-10-21 15:30:04 - INFO - SimulationMonitor 시작 중...
2025-10-21 15:30:05 - INFO - ✅ SimulationMonitor 시작됨
```

---

## 추가 도움말

### 관련 문서

- [VirtualOffice 연동 테스트 가이드](docs/VIRTUALOFFICE_TESTING.md)
- [실시간 기능 테스트 가이드](docs/REALTIME_TESTING.md)
- [VirtualOffice 설정 관리](docs/VIRTUALOFFICE_CONFIG.md)
- [GUI 실시간 통합 문서](docs/GUI_REALTIME_INTEGRATION.md)

### 이슈 보고

문제가 해결되지 않으면 다음 정보와 함께 이슈를 보고해주세요:

1. **환경 정보**:
   - OS 버전 (Windows 10/11, Linux, Mac)
   - Python 버전 (`python --version`)
   - 패키지 버전 (`pip list`)

2. **재현 단계**:
   - 문제가 발생한 정확한 단계
   - 입력한 명령어 또는 클릭한 버튼

3. **로그**:
   - DEBUG 레벨 로그 (`LOG_LEVEL=DEBUG`)
   - 오류 메시지 전체 내용

4. **스크린샷**:
   - 오류 화면 캡처
   - 설정 화면 캡처

### 커뮤니티 지원

- GitHub Issues: 버그 보고 및 기능 요청
- GitHub Discussions: 질문 및 토론
- README.md: 기본 사용법 및 예시
