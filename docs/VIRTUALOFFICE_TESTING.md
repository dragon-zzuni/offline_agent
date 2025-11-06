# VirtualOffice 연동 테스트 가이드

이 문서는 offline_agent와 virtualoffice 간의 연동을 테스트하는 방법을 설명합니다.

## 사전 준비

### 1. VirtualOffice 서버 시작

VirtualOffice 서버를 시작하는 방법은 두 가지가 있습니다:

#### 방법 A: GUI 사용 (권장)

```bash
cd virtualoffice
briefcase dev
```

GUI가 실행되면:
1. 시뮬레이션 시나리오 선택 (예: `multi_project_8week_ko`)
2. "Start Simulation" 버튼 클릭
3. 서버가 자동으로 시작됨 (포트 8000, 8001, 8015)

#### 방법 B: 수동 실행

3개의 터미널을 열고 각각 실행:

```bash
# 터미널 1: Email Server
cd virtualoffice
uvicorn virtualoffice.servers.email:app --port 8000 --reload

# 터미널 2: Chat Server
cd virtualoffice
uvicorn virtualoffice.servers.chat:app --port 8001 --reload

# 터미널 3: Simulation Manager
cd virtualoffice
uvicorn virtualoffice.sim_manager:create_app --port 8015 --reload
```

### 2. 서버 확인

브라우저에서 다음 URL을 열어 서버가 실행 중인지 확인:

- Email Server: http://127.0.0.1:8000/docs
- Chat Server: http://127.0.0.1:8001/docs
- Simulation Manager: http://127.0.0.1:8015/docs

## 테스트 방법

### 1. 빠른 연결 테스트 (권장)

가장 간단한 방법으로 연결을 테스트합니다:

```bash
python offline_agent/test_virtualoffice_connection.py
```

이 스크립트는 다음을 테스트합니다:
- ✓ 서버 연결 상태
- ✓ 페르소나 목록 조회
- ✓ 시뮬레이션 상태 조회
- ✓ 이메일/메시지 수집
- ✓ DataSource 통합

**예상 출력:**

```
============================================================
  VirtualOffice 연결 테스트
============================================================

============================================================
  1. 서버 연결 테스트
============================================================
Email Server: ✓ 연결됨
Chat Server:  ✓ 연결됨
Sim Manager:  ✓ 연결됨

✓ 모든 서버 연결 성공!

============================================================
  2. 페르소나 조회
============================================================
총 4명의 페르소나 발견

1. 이민주
   - Role: 프로젝트 매니저
   - Email: pm.1@multiproject.dev
   - Chat Handle: pm

...

✓ PM 페르소나 발견: 이민주

============================================================
  3. 시뮬레이션 상태
============================================================
현재 틱: 1920
시뮬레이션 시간: 2025-11-26T06:29:27.073636Z
실행 상태: 🟢 실행 중
자동 틱: 활성화

...
```

### 2. 전체 통합 테스트 (pytest)

더 상세한 테스트를 실행하려면:

```bash
pytest offline_agent/test/test_integration_full.py -v -s
```

이 테스트는 다음을 검증합니다:
- 서버 연결
- 페르소나 조회 및 검증
- 시뮬레이션 상태 조회
- 이메일 수집 및 필드 검증
- 메시지 수집 및 필드 검증
- DataSource 통합
- 페르소나 전환
- 증분 수집 (since_id 파라미터)
- DataSourceManager 통합

**예상 출력:**

```
test_integration_full.py::TestVirtualOfficeIntegration::test_01_connection PASSED
test_integration_full.py::TestVirtualOfficeIntegration::test_02_get_personas PASSED
test_integration_full.py::TestVirtualOfficeIntegration::test_03_get_simulation_status PASSED
test_integration_full.py::TestVirtualOfficeIntegration::test_04_collect_emails PASSED
test_integration_full.py::TestVirtualOfficeIntegration::test_05_collect_messages PASSED
test_integration_full.py::TestVirtualOfficeIntegration::test_06_data_source_integration PASSED
test_integration_full.py::TestVirtualOfficeIntegration::test_07_persona_switching PASSED
test_integration_full.py::TestVirtualOfficeIntegration::test_08_incremental_collection PASSED
test_integration_full.py::TestVirtualOfficeIntegration::test_09_data_source_manager PASSED
```

### 3. GUI 테스트

실제 사용자 경험을 테스트하려면:

```bash
python offline_agent/run_gui.py
```

GUI에서:

1. **VirtualOffice 연동 패널 찾기**
   - 좌측 패널에 "🌐 VirtualOffice 연동" 섹션이 있어야 함

2. **연결 설정**
   - Email Server URL: `http://127.0.0.1:8000`
   - Chat Server URL: `http://127.0.0.1:8001`
   - Sim Manager URL: `http://127.0.0.1:8015`
   - "연결" 버튼 클릭

3. **연결 성공 확인**
   - "VirtualOffice 연결 성공!" 메시지 표시
   - 페르소나 드롭다운에 페르소나 목록 표시
   - 시뮬레이션 상태 레이블 업데이트

4. **페르소나 선택**
   - 드롭다운에서 페르소나 선택 (기본: PM)
   - 선택 시 자동으로 데이터 소스 전환

5. **데이터 수집 확인**
   - "메시지 수집" 버튼 클릭
   - 수집된 메시지가 표시되는지 확인
   - 이메일/채팅 탭에서 데이터 확인

6. **시뮬레이션 상태 모니터링**
   - 시뮬레이션 상태 레이블이 2초마다 업데이트되는지 확인
   - 틱 번호가 증가하는지 확인

## 테스트 시나리오

### 시나리오 1: 기본 연동

1. VirtualOffice 서버 시작
2. `test_virtualoffice_connection.py` 실행
3. 모든 테스트 통과 확인

### 시나리오 2: 페르소나 전환

1. GUI 실행
2. VirtualOffice 연결
3. PM 페르소나로 데이터 수집
4. 다른 페르소나로 전환
5. 데이터가 다르게 표시되는지 확인

### 시나리오 3: 실시간 수집

1. GUI 실행
2. VirtualOffice 연결
3. 시뮬레이션이 실행 중인지 확인
4. 5초마다 새 데이터가 수집되는지 확인
5. 새 메시지에 "NEW" 배지가 표시되는지 확인

### 시나리오 4: 데이터 소스 전환

1. GUI 실행
2. 기본 JSON 파일로 데이터 수집
3. VirtualOffice로 전환
4. 데이터가 API에서 수집되는지 확인
5. 다시 JSON 파일로 전환
6. 데이터가 파일에서 로드되는지 확인

## 문제 해결

### 서버 연결 실패

**증상:**
```
✗ 연결 실패: HTTPConnectionPool(host='127.0.0.1', port=8000): Max retries exceeded
```

**해결 방법:**
1. VirtualOffice 서버가 실행 중인지 확인
2. 포트가 이미 사용 중인지 확인: `netstat -ano | findstr :8000`
3. 방화벽 설정 확인

### 페르소나가 없음

**증상:**
```
조회된 페르소나 수: 0
```

**해결 방법:**
1. 시뮬레이션이 초기화되었는지 확인
2. GUI에서 시나리오를 선택하고 "Initialize" 버튼 클릭
3. 데이터베이스 파일 확인: `virtualoffice/vdos.db`

### 데이터가 없음

**증상:**
```
수집된 메일 수: 0
수집된 메시지 수: 0
```

**해결 방법:**
1. 시뮬레이션이 시작되었는지 확인
2. GUI에서 "Start Simulation" 버튼 클릭
3. 몇 초 기다린 후 다시 시도
4. 시뮬레이션 상태 확인: `is_running: true`

### 증분 수집 실패

**증상:**
```
새 이메일 ID가 마지막 ID보다 작습니다
```

**해결 방법:**
1. 데이터베이스가 초기화되었는지 확인
2. `since_id` 파라미터가 올바른지 확인
3. 서버 로그 확인

## 성능 테스트

### 대량 데이터 수집

```python
# 1000개 이상의 메시지 수집 시간 측정
import time

start = time.time()
messages = data_source.collect_messages()
elapsed = time.time() - start

print(f"수집 시간: {elapsed:.2f}초")
print(f"메시지 수: {len(messages)}개")
print(f"초당 메시지: {len(messages) / elapsed:.2f}개/초")
```

**목표:**
- 1000개 메시지 수집: < 5초
- 메모리 사용량: < 500MB

### 폴링 성능

```python
# 폴링 간격 정확도 측정
import time

intervals = []
last_time = time.time()

for _ in range(10):
    time.sleep(5)  # 5초 폴링
    current_time = time.time()
    interval = current_time - last_time
    intervals.append(interval)
    last_time = current_time

avg_interval = sum(intervals) / len(intervals)
print(f"평균 폴링 간격: {avg_interval:.2f}초")
print(f"목표: 5.0초 ± 0.5초")
```

## 다음 단계

Phase 1 테스트가 완료되면:

1. **Phase 2: 실시간 기능**
   - PollingWorker 구현
   - SimulationMonitor 구현
   - 새 데이터 알림

2. **Phase 3: UI 개선**
   - NEW 배지 표시
   - 틱 히스토리
   - 시뮬레이션 상태 패널

3. **Phase 4: 고급 기능**
   - 오류 처리 강화
   - 성능 최적화
   - 설정 저장/로드

## 참고 자료

- [VirtualOffice API 문서](http://127.0.0.1:8015/docs)
- [Design Document](.kiro/specs/virtualoffice-integration/design.md)
- [Requirements Document](.kiro/specs/virtualoffice-integration/requirements.md)
- [Tasks Document](.kiro/specs/virtualoffice-integration/tasks.md)
