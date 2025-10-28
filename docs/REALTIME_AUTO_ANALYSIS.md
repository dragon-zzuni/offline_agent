# 실시간 자동 분석 시스템

## 개요

VirtualOffice 연동 시 자동으로 메시지를 수집하고 분석하여 TODO를 생성하는 시스템입니다.

## 주요 기능

### 1. 연결 테스트 후 자동 분석

**위치**: 좌측 패널 > 제어 섹션 > "🔌 실시간 연결 테스트" 버튼

**동작 흐름**:
1. 사용자가 "실시간 연결 테스트" 버튼 클릭
2. VirtualOffice 서버 연결 및 페르소나 조회
3. 연결 성공 후 **1초 뒤 자동으로 메시지 수집 및 분석 시작**
4. TODO 패널에 결과 자동 표시

**코드 위치**: `offline_agent/src/ui/main_window.py`
```python
def connect_virtualoffice(self):
    # ... 연결 로직 ...
    
    # 연결 성공 후 1초 뒤 자동으로 분석 시작
    QTimer.singleShot(1000, self._auto_start_analysis)

def _auto_start_analysis(self):
    """연결 성공 후 자동으로 분석 시작"""
    if self.data_source_type == "virtualoffice" and self.selected_persona:
        self.start_collection()
```

### 2. 새 메시지 수신 시 자동 재분석

**트리거 조건**:
- 시뮬레이션 틱 진행 시
- 새 이메일/메시지 수신 시
- TODO 리스트 변경 시

**동작 흐름**:
1. PollingWorker가 새 메시지 감지 (30초 간격)
2. `on_new_data_received()` 핸들러 호출
3. UI 업데이트 (메시지 패널, 이메일 패널 등)
4. **2초 후 자동으로 전체 메시지 재분석**
5. TODO 패널 자동 새로고침

**코드 위치**: `offline_agent/src/ui/main_window.py`
```python
def on_new_data_received(self, data: dict):
    # ... UI 업데이트 ...
    
    # 새 메시지에 대한 자동 재분석 트리거 (2초 후)
    if total_new > 0:
        self._process_new_messages_async(all_messages)

def _process_new_messages_async(self, new_messages: list):
    # 2초 후 자동 재분석
    QTimer.singleShot(2000, self._trigger_reanalysis)

def _trigger_reanalysis(self):
    """전체 메시지 재분석 트리거"""
    # 기존 메시지로 분석만 다시 실행 (수집 건너뛰기)
    collect_options = {
        "skip_collection": True,  # 수집 건너뛰기
        "force_reload": False,
    }
    self.worker_thread = WorkerThread(self.assistant, dataset_config, collect_options)
    # ...
```

### 3. 분석 완료 후 TODO 패널 자동 새로고침

**동작 흐름**:
1. 분석 완료 시 `_handle_reanalysis_result()` 호출
2. TODO 데이터를 `todo_panel.populate_from_items()` 전달
3. Top3 규칙 자동 적용
4. UI 자동 업데이트

**코드 위치**: `offline_agent/src/ui/main_window.py`
```python
def _handle_reanalysis_result(self, result):
    """재분석 결과 처리"""
    if result.get("success"):
        # TODO 업데이트
        todo_list = result.get("todo_list") or {}
        items = todo_list.get("items", [])
        
        if items and hasattr(self, "todo_panel"):
            self.todo_panel.populate_from_items(items)  # 자동 새로고침
            logger.info(f"✅ TODO 업데이트 완료: {len(items)}개")
```

## UI 변경 사항

### 제거된 기능

1. **"데이터 다시 읽기" 버튼 제거**
   - 위치: 좌측 패널 > 데이터 소스 섹션
   - 이유: 실시간 자동 분석으로 불필요

2. **VirtualOffice 패널의 "연결 테스트" 버튼 제거**
   - 위치: VirtualOffice 연동 패널
   - 이유: 제어 섹션으로 통합

### 추가된 기능

1. **"🔌 실시간 연결 테스트" 버튼**
   - 위치: 좌측 패널 > 제어 섹션 (최상단)
   - 기능: 연결 + 자동 분석 시작

## 기술 세부사항

### WorkerThread 개선

**skip_collection 옵션 추가**:
```python
# offline_agent/src/ui/widgets/worker_thread.py
def run(self):
    skip_collection = self.collect_options.get("skip_collection", False)
    
    if skip_collection:
        # 기존 메시지 사용 (수집 건너뛰기)
        messages = getattr(self.assistant, 'collected_messages', [])
    else:
        # 새로 메시지 수집
        messages = loop.run_until_complete(
            self.assistant.collect_messages(**self.collect_options)
        )
```

### 자동화 타이밍

- **연결 후 분석**: 1초 대기 (UI 안정화)
- **새 메시지 재분석**: 2초 대기 (UI 업데이트 완료 후)
- **폴링 간격**: 30초 (PollingWorker)

## 사용자 워크플로우

### 기본 사용 시나리오

1. **초기 설정**
   ```
   1. VirtualOffice 서버 URL 입력 (Email, Chat, Sim Manager)
   2. "🔌 실시간 연결 테스트" 버튼 클릭
   3. 페르소나 자동 선택 (PM 우선)
   4. 1초 후 자동으로 메시지 수집 및 분석 시작
   5. TODO 패널에 결과 자동 표시
   ```

2. **실시간 업데이트**
   ```
   1. 시뮬레이션 진행 (틱 증가)
   2. 새 메시지 자동 감지 (30초마다)
   3. 2초 후 자동 재분석
   4. TODO 패널 자동 새로고침
   ```

3. **수동 분석 (필요 시)**
   ```
   1. "🔄 메시지 수집" 버튼 클릭
   2. 전체 메시지 재수집 및 분석
   ```

## 로그 메시지

### 정상 동작
```
[INFO] 🚀 연결 성공 - 1초 후 자동 분석 시작
[INFO] 🚀 자동 분석 시작
[INFO] 📬 새 데이터 수신: 메일 5개, 메시지 12개
[INFO] 🔄 새 메시지 17개 수신 - 2초 후 자동 재분석 시작
[INFO] 🔄 전체 메시지 재분석 시작
[INFO] ✅ TODO 업데이트 완료: 23개
```

### 오류 처리
```
[WARNING] ⚠️ VirtualOffice 모드가 아니거나 페르소나가 선택되지 않음
[ERROR] ❌ 재분석 트리거 오류: ...
```

## 성능 최적화

1. **비동기 처리**: 분석 작업을 백그라운드 스레드에서 실행
2. **점진적 UI 업데이트**: 대량 데이터 처리 시 프로그레스 바 표시
3. **캐시 시스템**: 페르소나별 데이터 캐싱 (5분 유효)
4. **스마트 폴링**: 시뮬레이션 실행 중에만 실시간 폴링

## 문제 해결

### TODO가 자동으로 업데이트되지 않음

**원인**: PollingWorker가 시작되지 않음

**해결**:
1. VirtualOffice 모드로 전환 확인
2. 페르소나 선택 확인
3. 연결 테스트 다시 실행

### 분석이 너무 자주 실행됨

**원인**: 폴링 간격이 너무 짧음

**해결**:
```python
# offline_agent/src/ui/main_window.py
self.polling_worker = PollingWorker(data_source, polling_interval=60)  # 30초 → 60초
```

### 메모리 사용량 증가

**원인**: 캐시 데이터 누적

**해결**:
- 캐시는 5분 후 자동 무효화
- 페르소나 변경 시 캐시 자동 정리
- 필요 시 앱 재시작

## 향후 개선 사항

1. **선택적 자동 분석**: 사용자가 자동 분석 on/off 설정 가능
2. **분석 간격 조정**: 폴링 간격을 UI에서 설정 가능
3. **배치 분석**: 여러 메시지를 모아서 한 번에 분석
4. **알림 시스템**: 중요한 TODO 생성 시 데스크톱 알림
