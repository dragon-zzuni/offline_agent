# TODO 리스트 지속성 문제 해결

## 문제 상황
백그라운드 분석 중 TODO 리스트가 사라지는 문제:
1. 앱 시작 → DB에서 TODO 로드 → 화면에 표시
2. 백그라운드 분석 시작 → TODO 리스트 **사라짐** (빈 상태)
3. 백그라운드 분석 완료 → 새 TODO 표시

## 원인 분석
`refresh_todo_list()` 메서드에서:
- DB에서 TODO를 로드할 때 결과가 없으면
- 즉시 `_rebuild_from_rows([])`를 호출하여 빈 리스트 표시
- 백그라운드 분석 중에는 DB가 비어있거나 업데이트 중이므로
- 기존 TODO가 모두 사라짐

## 해결 방법

### refresh_todo_list() 수정
기존 TODO가 있으면 유지하도록 변경:

```python
def refresh_todo_list(self, show_reasoning: bool = False) -> None:
    rows = self.controller.load_active_items()
    logger.info(f"[TodoPanel] DB에서 {len(rows)}개 TODO 로드")

    if not rows:
        # 기존 TODO가 있으면 유지 (백그라운드 분석 중)
        if self._all_rows:
            logger.info("[TodoPanel] TODO 없음 - 기존 TODO 유지 (백그라운드 분석 중)")
            return  # 기존 화면 유지
        else:
            logger.warning("[TodoPanel] TODO 없음 - 빈 리스트 표시")
            self._rebuild_from_rows([])
            return

    self.update_project_tags(rows)
    self._rebuild_from_rows(rows, show_reasoning=show_reasoning)
```

### 동작 방식
1. **DB에서 TODO 로드 실패 시:**
   - `self._all_rows`가 있는지 확인
   - 있으면: 기존 TODO 유지 (return으로 조기 종료)
   - 없으면: 빈 리스트 표시

2. **백그라운드 분석 중:**
   - DB가 비어있어도 기존 TODO가 화면에 계속 표시됨
   - 사용자는 TODO를 계속 볼 수 있음

3. **백그라운드 분석 완료:**
   - 새 TODO가 DB에 저장됨
   - `refresh_todo_list()` 호출 시 새 TODO 로드
   - 화면이 새 TODO로 업데이트됨

## 수정된 파일
- `offline_agent/src/ui/todo_panel.py`
  - `refresh_todo_list()` 메서드: 기존 TODO 유지 로직 추가

## 테스트 방법
1. 앱 시작
2. VirtualOffice 연결 및 페르소나 선택
3. TODO 리스트 확인 (DB에서 로드된 TODO 표시)
4. 백그라운드 분석 시작
5. **TODO 리스트가 계속 표시되는지 확인** (사라지지 않음)
6. 백그라운드 분석 완료
7. 새 TODO로 업데이트되는지 확인

## 기대 효과
- ✅ 백그라운드 분석 중에도 TODO 리스트 유지
- ✅ 사용자 경험 개선 (빈 화면 없음)
- ✅ 부드러운 전환 (기존 TODO → 새 TODO)
- ✅ 초기 로드 시에는 정상적으로 빈 리스트 표시
