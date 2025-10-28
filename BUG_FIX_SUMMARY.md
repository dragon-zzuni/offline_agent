# 버그 수정 요약

## 수정 일자
2025-10-28

## 해결된 문제

### 오류: `unsupported operand type(s) for /: 'NoneType' and 'str'`

**원인**:
- `dataset_root = None` (VirtualOffice 전용 모드)
- `_load_json()` 메서드에서 `self.dataset_root / filename` 연산 시도
- `Path(None) / "something"` 연산은 불가능

**해결**:
1. `_load_json()` 메서드에 None 체크 추가
2. `_ensure_dataset()` 메서드에서 VirtualOffice 모드 감지 시 건너뛰기

## 파일 변경 사항

### offline_agent/main.py

**수정 1: _load_json 메서드**
```python
# Before
def _load_json(self, filename: str) -> Any:
    path = self.dataset_root / filename  # ❌ dataset_root가 None이면 오류
    if not path.exists():
        ...

# After
def _load_json(self, filename: str) -> Any:
    # dataset_root가 None이면 FileNotFoundError 발생
    if self.dataset_root is None:
        raise FileNotFoundError(f"데이터 파일을 찾을 수 없습니다: {filename} (dataset_root가 설정되지 않음)")
    
    path = self.dataset_root / filename
    if not path.exists():
        ...
```

**수정 2: _ensure_dataset 메서드**
```python
# Before
def _ensure_dataset(self, force_reload: bool = False) -> None:
    if self._dataset_loaded and not force_reload:
        return
    self._load_dataset()  # ❌ VirtualOffice 모드에서도 실행됨

# After
def _ensure_dataset(self, force_reload: bool = False) -> None:
    # VirtualOffice 모드일 때는 데이터셋 로드 건너뛰기
    if self.dataset_root is None:
        logger.debug("VirtualOffice 모드: 데이터셋 로드 건너뛰기")
        return
    
    if self._dataset_loaded and not force_reload:
        return
    self._load_dataset()
```

## 동작 방식

### VirtualOffice 모드 (dataset_root = None)
```
1. SmartAssistant 초기화
2. dataset_root = None 설정
3. initialize() 호출
4. _ensure_dataset() 호출
5. ✅ dataset_root가 None이므로 건너뛰기
6. ✅ 오류 없이 초기화 완료
```

### JSON 모드 (dataset_root = Path)
```
1. SmartAssistant 초기화
2. dataset_root = Path("data/...") 설정
3. initialize() 호출
4. _ensure_dataset() 호출
5. _load_dataset() 실행
6. _load_json() 호출
7. ✅ Path 연산 정상 실행
```

## 테스트 결과

```bash
python offline_agent/test_app_startup.py
```

```
================================================================================
모듈 Import 테스트
================================================================================
✓ main 모듈 import...
✓ SmartAssistant import 성공
✓ MainWindow import...
✓ SmartAssistantGUI import 성공
✓ VirtualOfficeManager import...
✓ VirtualOfficeManager import 성공

✅ 모든 모듈 import 성공!

================================================================================
SmartAssistant 초기화 테스트
================================================================================
SmartAssistant 인스턴스 생성 중...
✓ SmartAssistant 인스턴스 생성 성공
  - dataset_root: None
  - data_source_manager: <DataSourceManager>

✅ SmartAssistant 초기화 성공!

================================================================================
✅ 모든 테스트 통과!
================================================================================
```

## 남은 작업

### TODO 리스트 및 분석 결과 탭 데이터 로드 문제

**현재 상태**:
- ✅ 메시지 수집 성공 (903개)
- ✅ 이메일/메시지 탭 업데이트 성공
- ❌ TODO 생성 실패 (0개)
- ❌ 분석 결과 없음

**원인**:
- 분석 파이프라인이 실행되지 않음
- `WorkerThread`가 `skip_collection=True`로 실행되지만 분석이 완료되지 않음

**해결 방법**:
1. `WorkerThread.run()` 메서드 확인
2. `analyze_messages()` 호출 확인
3. `generate_todo_list()` 호출 확인
4. 오류 로그 확인

## 다음 단계

1. ✅ 오류 수정 (`NoneType` 연산)
2. ⏳ TODO 생성 파이프라인 수정
3. ⏳ 분석 결과 업데이트 수정
4. ⏳ 추가 모듈화

## 결론

`NoneType` 오류를 수정했습니다:
- ✅ `_load_json()` 메서드에 None 체크 추가
- ✅ `_ensure_dataset()` 메서드에서 VirtualOffice 모드 감지
- ✅ 테스트 통과

앱을 재시작하고 오류 다이얼로그가 사라졌는지 확인하세요!
