# TODO 표시 문제 긴급 수정

## 🐛 발견된 문제

### 1. 분석 TODO가 GUI에 표시 안되는 문제
- **증상**: 즉시 TODO는 나오지만, 백그라운드 분석 완료 후 분석 TODO가 GUI에 표시되지 않음
- **원인**: 백그라운드 분석 완료 후 `populate_from_items()` 호출이 누락됨

### 2. TODO 상세 다이얼로그 중복 표시 문제
- **증상**: 같은 내용이 두 번 나옴 (원본 메시지 섹션 + 요약 및 액션 섹션)
- **원인**: 원본 메시지가 이미 표시되는데, 요약 및 액션 섹션에 또 같은 내용이 표시됨

## 🔧 수정 방법

### 문제 1: 분석 TODO 표시 안되는 문제

**파일**: `offline_agent/src/ui/main_window_components/analysis_cache_controller.py`

백그라운드 분석 완료 후 TODO를 GUI에 표시하는 로직이 누락되어 있습니다.

```python
# _handle_background_analysis_result 메서드에서
# TODO 업데이트 부분 추가 필요

if todos:
    # DB에 저장
    ui.todo_panel.populate_from_items(todos)
    logger.info("✅ 백그라운드 분석 TODO 업데이트: %d개", len(todos))
```

### 문제 2: TODO 상세 다이얼로그 중복 표시

**파일**: `offline_agent/src/ui/todo_panel.py` 또는 TODO 상세 다이얼로그 관련 파일

원본 메시지 섹션과 요약 및 액션 섹션이 중복되어 표시되고 있습니다.
- 원본 메시지는 상단에만 표시
- 요약 및 액션 섹션은 LLM 생성 버튼을 눌렀을 때만 표시되어야 함

## 📋 수정 필요 사항

1. 백그라운드 분석 완료 시 `populate_from_items()` 호출 추가
2. TODO 상세 다이얼로그에서 중복 표시 제거
3. 즉시 TODO는 분석 TODO가 나오면 자동으로 교체되어야 함

## 🔍 확인 필요

- 로그에서 "✅ 백그라운드 분석 완료" 메시지 확인
- 로그에서 "populate_from_items" 호출 여부 확인
- TODO 패널 refresh 호출 여부 확인
