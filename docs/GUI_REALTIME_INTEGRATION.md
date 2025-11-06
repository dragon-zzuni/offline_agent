# GUI 실시간 기능 통합 문서

## 개요

이 문서는 offline_agent GUI에 VirtualOffice 실시간 기능을 통합한 내용을 설명합니다.

## 구현된 기능

### 1. PollingWorker 통합

**목적**: 백그라운드에서 주기적으로 VirtualOffice API를 폴링하여 새로운 메일과 메시지를 수집합니다.

**구현 위치**: `offline_agent/src/ui/main_window.py`

**주요 기능**:
- VirtualOffice 연결 성공 시 자동으로 PollingWorker 시작
- 5초 간격으로 새 데이터 폴링 (시뮬레이션 일시정지 시 10초로 증가)
- 새 데이터 수신 시 `on_new_data_received` 시그널 발생
- 오류 발생 시 `on_polling_error` 시그널 발생

**사용 방법**:
```python
# VirtualOffice 연결 후 자동으로 시작됨
# 수동으로 시작하려면:
if self.vo_client and self.selected_persona:
    data_source = self.assistant.data_source_manager.current_source
    self.polling_worker = PollingWorker(data_source)
    self.polling_worker.new_data_received.connect(self.on_new_data_received)
    self.polling_worker.error_occurred.connect(self.on_polling_error)
    self.polling_worker.start()
```

### 2. SimulationMonitor 통합

**목적**: VirtualOffice 시뮬레이션의 상태를 실시간으로 모니터링합니다.

**구현 위치**: `offline_agent/src/ui/main_window.py`

**주요 기능**:
- 2초 간격으로 시뮬레이션 상태 폴링
- 틱 진행 감지 및 알림
- 시뮬레이션 실행 상태 추적 (running/paused/stopped)
- UI에 시뮬레이션 상태 표시

**사용 방법**:
```python
# VirtualOffice 연결 후 자동으로 시작됨
# 수동으로 시작하려면:
self.sim_monitor = SimulationMonitor(self.vo_client)
self.sim_monitor.status_updated.connect(self.on_sim_status_updated)
self.sim_monitor.tick_advanced.connect(self.on_tick_advanced)
self.sim_monitor.start_monitoring()
```

### 3. 새 데이터 수신 핸들러

**메서드**: `on_new_data_received(data: dict)`

**기능**:
- 새로운 메일과 메시지를 기존 데이터에 추가
- 메시지 요약 패널 업데이트
- 이메일 패널 업데이트
- 상태바에 알림 표시

**데이터 형식**:
```python
{
    "emails": [
        {
            "msg_id": "email_123",
            "sender": "이준호",
            "subject": "프로젝트 업데이트",
            ...
        }
    ],
    "messages": [
        {
            "msg_id": "chat_456",
            "sender": "김민준",
            "body": "회의 시간 변경",
            ...
        }
    ],
    "timestamp": "2025-10-21T15:30:00"
}
```

### 4. 시뮬레이션 상태 업데이트 핸들러

**메서드**: `on_sim_status_updated(status: dict)`

**기능**:
- 시뮬레이션 상태 레이블 업데이트
- 실행 상태에 따라 색상 변경 (실행 중: 녹색, 정지: 빨간색)
- 폴링 간격 자동 조정

**상태 형식**:
```python
{
    "current_tick": 1234,
    "sim_time": "2025-10-21T09:30:00",
    "is_running": True,
    "auto_tick": True
}
```

### 5. 틱 진행 알림 핸들러

**메서드**: `on_tick_advanced(tick: int)`

**기능**:
- 상태바에 틱 진행 메시지 표시 (3초 동안)
- 해당 틱에서 수집된 메시지 수 표시 (선택적)

**예시**:
```
⏰ Tick 1234 진행됨 (5개 새 메시지)
```

## 데이터 소스 전환

### JSON 파일 모드

- PollingWorker 자동 중지
- 로컬 JSON 파일에서 데이터 로드
- 기존 오프라인 분석 기능 사용

### VirtualOffice 실시간 모드

- PollingWorker 자동 시작
- VirtualOffice API에서 실시간 데이터 수집
- SimulationMonitor로 시뮬레이션 상태 추적

## 페르소나 변경

페르소나를 변경하면:
1. 데이터 소스가 새 페르소나로 업데이트됨
2. PollingWorker가 재시작됨 (실행 중인 경우)
3. 새 페르소나의 메일박스와 DM만 수집됨

## 리소스 정리

애플리케이션 종료 시 자동으로:
- PollingWorker 중지 (최대 3초 대기)
- SimulationMonitor 중지
- 모든 스레드 정리

## 오류 처리

### 폴링 오류

- 네트워크 오류 시 자동 재시도 (exponential backoff)
- 연속 실패 시 대기 시간 증가
- 상태바에 오류 메시지 표시 (10초 동안)

### 연결 오류

- 연결 실패 시 사용자에게 알림
- 재연결 옵션 제공
- 로그에 상세 오류 정보 기록

## 성능 최적화

### 폴링 간격 조정

- 시뮬레이션 실행 중: 5초
- 시뮬레이션 일시정지: 10초
- 사용자 정의 간격 설정 가능

### 메모리 관리

- 최대 10,000개 메시지 유지
- 오래된 데이터 자동 정리
- 증분 수집으로 중복 방지

## 테스트

테스트 스크립트: `offline_agent/test_gui_integration.py`

실행 방법:
```bash
cd offline_agent
python test_gui_integration.py
```

테스트 항목:
1. Import 테스트 - 모든 모듈이 올바르게 import되는지 확인
2. GUI 속성 테스트 - 필수 속성과 메서드가 존재하는지 확인
3. 시그널 연결 테스트 - UI 위젯이 올바르게 생성되었는지 확인

## 사용 예시

### 1. VirtualOffice 연결

1. 좌측 패널에서 "VirtualOffice 실시간" 라디오 버튼 선택
2. Email/Chat/Sim Manager URL 입력
3. "🔌 연결 테스트" 버튼 클릭
4. 페르소나 선택 (PM 자동 선택됨)
5. 자동으로 PollingWorker와 SimulationMonitor 시작

### 2. 실시간 데이터 수집

- 연결 후 자동으로 5초마다 새 데이터 수집
- 새 데이터 도착 시 상태바에 알림 표시
- 메시지 요약 패널과 이메일 패널 자동 업데이트

### 3. 시뮬레이션 모니터링

- 시뮬레이션 상태 패널에서 현재 틱, 시간, 실행 상태 확인
- 틱 진행 시 상태바에 알림 표시
- 실행 상태에 따라 색상 변경

## 문제 해결

### PollingWorker가 시작되지 않음

**원인**: VirtualOffice 연결이 완료되지 않았거나 페르소나가 선택되지 않음

**해결**:
1. VirtualOffice 서버가 실행 중인지 확인
2. "🔌 연결 테스트" 버튼을 다시 클릭
3. 페르소나가 선택되었는지 확인

### 새 데이터가 수집되지 않음

**원인**: 시뮬레이션이 일시정지되었거나 새 데이터가 없음

**해결**:
1. 시뮬레이션 상태 확인 (실행 중인지)
2. VirtualOffice에서 시뮬레이션 진행
3. 로그에서 폴링 오류 확인

### 메모리 사용량이 계속 증가함

**원인**: 대량의 메시지가 수집되어 메모리에 누적됨

**해결**:
1. 애플리케이션 재시작
2. 시간 범위 필터 적용하여 표시되는 메시지 수 제한
3. 데이터 소스를 JSON 파일로 전환

## 향후 개선 사항

1. **WebSocket 지원**: 폴링 대신 실시간 푸시 알림
2. **배치 처리**: 여러 API 호출을 병렬로 실행
3. **캐싱**: 페르소나 정보 등 정적 데이터 캐싱
4. **UI 개선**: 새 데이터 시각적 알림 (배지, 애니메이션)
5. **틱 히스토리**: 최근 틱별 활동 요약 표시

## 관련 문서

- [VirtualOffice 연동 설계](../../.kiro/specs/virtualoffice-integration/design.md)
- [VirtualOffice 연동 요구사항](../../.kiro/specs/virtualoffice-integration/requirements.md)
- [PollingWorker 구현](../src/integrations/polling_worker.py)
- [SimulationMonitor 구현](../src/integrations/simulation_monitor.py)
