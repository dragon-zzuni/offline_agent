# VirtualOffice 실시간 기능 테스트 가이드

이 문서는 Phase 2의 실시간 기능들을 테스트하는 방법을 설명합니다.

## 테스트 대상

1. **SimulationMonitor**: 시뮬레이션 상태 실시간 모니터링
2. **PollingWorker**: 백그라운드 데이터 수집
3. **증분 수집**: `since_id`를 사용한 새 데이터만 조회
4. **오류 처리**: 네트워크 오류 시 재시도 로직
5. **통합 동작**: 두 컴포넌트의 동시 작동

## 사전 준비

### 1. VirtualOffice 서버 시작

```bash
cd virtualoffice
briefcase dev
```

또는 수동으로 3개 서버 실행:

```bash
# 터미널 1
uvicorn virtualoffice.servers.email:app --port 8000 --reload

# 터미널 2
uvicorn virtualoffice.servers.chat:app --port 8001 --reload

# 터미널 3
uvicorn virtualoffice.sim_manager:create_app --port 8015 --reload
```

### 2. 시뮬레이션 시작

VirtualOffice GUI에서:
1. 시나리오 선택 (예: `multi_project_8week_ko`)
2. **Start** 버튼 클릭
3. 시뮬레이션이 실행 중인지 확인 (틱이 증가하는지 확인)

### 3. 서버 연결 확인

```bash
python offline_agent/test_virtualoffice_connection.py
```

모든 서버가 연결되고 페르소나가 조회되는지 확인합니다.

## 테스트 실행

### 전체 실시간 기능 테스트

```bash
pytest offline_agent/test/test_realtime_integration.py -v -s
```

### 개별 테스트 실행

#### 1. SimulationMonitor 기본 동작

```bash
pytest offline_agent/test/test_realtime_integration.py::TestRealtimeIntegration::test_01_simulation_monitor_basic -v -s
```

**예상 결과**:
- 2초마다 시뮬레이션 상태 업데이트 수신
- 틱이 진행되면 `tick_advanced` 시그널 발생
- 10초 동안 최소 3-5회 상태 업데이트

**확인 사항**:
```
상태 업데이트: Tick 1234, Running: True
틱 진행: 1235
상태 업데이트: Tick 1235, Running: True
...
```

#### 2. PollingWorker 기본 동작

```bash
pytest offline_agent/test/test_realtime_integration.py::TestRealtimeIntegration::test_02_polling_worker_basic -v -s
```

**예상 결과**:
- 5초마다 새 메일/메시지 조회
- 새 데이터가 있으면 `new_data_received` 시그널 발생
- 15초 동안 2-3회 폴링

**확인 사항**:
```
새 데이터 수신: 이메일 2개, 메시지 5개
새 데이터 수신: 이메일 1개, 메시지 3개
...
```

#### 3. 증분 수집

```bash
pytest offline_agent/test/test_realtime_integration.py::TestRealtimeIntegration::test_03_polling_worker_incremental -v -s
```

**예상 결과**:
- `last_email_id`와 `last_message_id`가 증가
- 새 데이터만 수집됨 (중복 없음)
- ID가 순차적으로 증가

**확인 사항**:
```
초기 last_email_id: 100
최종 last_email_id: 105
✓ last_email_id 증가: 100 -> 105
```

#### 4. 오류 처리 및 재시도

```bash
pytest offline_agent/test/test_realtime_integration.py::TestRealtimeIntegration::test_04_error_handling -v -s
```

**예상 결과**:
- 잘못된 서버 URL로 연결 시도
- 오류 발생 및 `error_occurred` 시그널 발생
- 자동 재시도 (최소 2회)

**확인 사항**:
```
예상된 오류 발생: HTTPConnectionPool...
예상된 오류 발생: HTTPConnectionPool...
✓ 오류 처리 및 재시도 확인됨 (3회 재시도)
```

#### 5. 통합 모니터링

```bash
pytest offline_agent/test/test_realtime_integration.py::TestRealtimeIntegration::test_05_combined_monitoring -v -s
```

**예상 결과**:
- SimulationMonitor와 PollingWorker가 동시에 작동
- 상태 업데이트와 데이터 수집이 독립적으로 진행
- 두 컴포넌트 간 간섭 없음

**확인 사항**:
```
[Monitor] Tick 1234
[Worker] 새 데이터: 이메일 1개, 메시지 2개
[Monitor] 틱 진행: 1235
[Monitor] Tick 1235
[Worker] 새 데이터: 이메일 0개, 메시지 1개
...
```

#### 6. 폴링 간격 조정

```bash
pytest offline_agent/test/test_realtime_integration.py::TestRealtimeIntegration::test_06_polling_interval_adjustment -v -s
```

**예상 결과**:
- 폴링 간격을 3초 → 10초로 변경
- 간격이 길어지면 이벤트 수 감소
- 동적 간격 조정 확인

**확인 사항**:
```
첫 번째 단계 (3초 간격): 3개
두 번째 단계 (10초 간격): 1개
이벤트 비율: 3.00
✓ 폴링 간격 조정 확인됨
```

## GUI 통합 테스트

### 수동 GUI 테스트

1. **GUI 실행**:
   ```bash
   python offline_agent/run_gui.py
   ```

2. **VirtualOffice 연동**:
   - 좌측 패널에서 "VirtualOffice 연동" 섹션 찾기
   - URL 입력 (기본값 사용)
   - "연결" 버튼 클릭

3. **페르소나 선택**:
   - 드롭다운에서 PM 페르소나 선택
   - 자동으로 PM이 선택되는지 확인

4. **시뮬레이션 상태 확인**:
   - 현재 틱, 시뮬레이션 시간, 실행 상태 표시 확인
   - 2초마다 업데이트되는지 확인

5. **실시간 데이터 수집**:
   - 5초마다 새 메일/메시지 수집 확인
   - 새 데이터 도착 시 UI 업데이트 확인
   - 메시지 목록에 새 항목 추가 확인

6. **틱 진행 알림**:
   - 틱이 진행될 때 상태바 메시지 확인
   - "Tick X 진행됨" 메시지 표시 확인

### GUI 테스트 체크리스트

- [ ] VirtualOffice 연결 성공
- [ ] 페르소나 목록 로드됨
- [ ] PM 페르소나 자동 선택됨
- [ ] 시뮬레이션 상태 실시간 업데이트
- [ ] 새 메일/메시지 자동 수집
- [ ] 메시지 목록 UI 업데이트
- [ ] 틱 진행 알림 표시
- [ ] 오류 발생 시 알림 표시
- [ ] 연결 해제 시 폴링 중지

## 문제 해결

### 테스트가 스킵되는 경우

**증상**: `pytest.skip: VirtualOffice 서버가 실행 중이지 않습니다`

**해결**:
1. VirtualOffice 서버 시작 확인
2. 포트 8000, 8001, 8015가 사용 중인지 확인
3. 방화벽 설정 확인

### 새 데이터가 수집되지 않는 경우

**증상**: `⚠ 새 데이터가 없습니다`

**원인**:
- 시뮬레이션이 일시정지됨
- 시뮬레이션 속도가 느림
- 새 커뮤니케이션이 생성되지 않음

**해결**:
1. VirtualOffice GUI에서 시뮬레이션 실행 상태 확인
2. Auto Tick 활성화 확인
3. 더 긴 시간 대기 (30초 이상)

### 틱이 진행되지 않는 경우

**증상**: `⚠ 틱 진행이 감지되지 않았습니다`

**원인**:
- 시뮬레이션이 정지됨
- Auto Tick이 비활성화됨
- 시뮬레이션이 완료됨

**해결**:
1. VirtualOffice GUI에서 "Start" 버튼 클릭
2. Auto Tick 체크박스 활성화
3. 새 시뮬레이션 시작

### 오류가 계속 발생하는 경우

**증상**: 연속적인 연결 오류

**원인**:
- 서버가 다운됨
- 네트워크 문제
- 포트 충돌

**해결**:
1. 서버 로그 확인
2. 서버 재시작
3. 포트 변경 시도

## 성능 기준

### 예상 성능

- **SimulationMonitor 폴링**: 2초 간격, ±0.5초 오차
- **PollingWorker 폴링**: 5초 간격, ±1초 오차
- **메모리 사용량**: < 100MB 증가
- **CPU 사용량**: < 5% (유휴 시)

### 성능 측정

```python
import psutil
import time

# 메모리 사용량 측정
process = psutil.Process()
initial_memory = process.memory_info().rss / 1024 / 1024  # MB

# 테스트 실행...

final_memory = process.memory_info().rss / 1024 / 1024
print(f"메모리 증가: {final_memory - initial_memory:.2f} MB")
```

## 추가 테스트

### 장시간 안정성 테스트

```bash
# 1시간 동안 실행
pytest offline_agent/test/test_realtime_integration.py::TestRealtimeIntegration::test_05_combined_monitoring -v -s --timeout=3600
```

### 부하 테스트

```python
# 여러 페르소나 동시 모니터링
for persona in personas:
    worker = PollingWorker(VirtualOfficeDataSource(client, persona.email_address))
    worker.start()
```

## 참고 자료

- [VirtualOffice API 문서](../virtualoffice/docs/api/)
- [PollingWorker 구현](../offline_agent/src/integrations/polling_worker.py)
- [SimulationMonitor 구현](../offline_agent/src/integrations/simulation_monitor.py)
- [GUI 통합 문서](./GUI_REALTIME_INTEGRATION.md)

## 요약

실시간 기능 테스트는 다음을 검증합니다:

1. ✅ **시뮬레이션 모니터링**: 2초마다 상태 조회, 틱 진행 감지
2. ✅ **백그라운드 데이터 수집**: 5초마다 새 메일/메시지 조회
3. ✅ **증분 수집**: `since_id` 사용, 중복 방지
4. ✅ **오류 처리**: 자동 재시도, 사용자 알림
5. ✅ **통합 동작**: 두 컴포넌트 독립적 작동
6. ✅ **폴링 간격 조정**: 동적 간격 변경

모든 테스트가 통과하면 Phase 2 실시간 기능이 정상적으로 작동하는 것입니다.
