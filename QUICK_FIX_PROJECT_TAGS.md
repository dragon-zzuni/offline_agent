# 🚀 프로젝트 태그 즉시 수정 가이드

## 문제 요약
김세린 TODO 66개 중 프로젝트 태그가 1개만 있음 (1.5%)
→ source_message에 메시지 내용이 없어서 프로젝트 추출 실패

## ✅ 해결 완료
`analysis_pipeline_service.py` 수정 완료 - 이제 TODO 생성 시 전체 메시지 내용 저장

## 🎯 즉시 적용 방법 (2가지 옵션)

### 옵션 1: 기존 TODO 삭제 후 재생성 (권장)

**장점**: 가장 빠르고 확실함
**단점**: 기존 TODO 메모/상태 손실

```bash
# 1. GUI 종료

# 2. TODO DB 삭제
del virtualoffice\src\virtualoffice\todos_cache.db

# 3. GUI 재시작
python offline_agent\run_gui.py

# 4. 김세린 페르소나 선택 후 "분석 시작" 클릭
```

**결과**: 새로 생성되는 TODO에 프로젝트 태그가 자동으로 붙음!

### 옵션 2: 기존 TODO 유지하면서 수정

**장점**: 기존 TODO 메모/상태 유지
**단점**: 스크립트 실행 필요

```bash
# 1. VDOS DB에서 원본 메시지를 찾아서 source_message 업데이트
python offline_agent/fix_source_messages_from_vdos.py

# 2. 프로젝트 태그 재분석
python offline_agent/fix_current_persona_project_tags.py 김세린

# 3. GUI 재시작
python offline_agent\run_gui.py
```

## 📋 확인 방법

### 1. source_message 확인
```bash
python offline_agent/check_source_message_content.py
```

**Before**: `body: ...` (비어있음)
**After**: `body: 안녕하세요, 프로젝트 VERTEX 관련...` (전체 내용)

### 2. 프로젝트 태그 확인
```bash
python offline_agent/check_current_persona_todos.py
```

**Before**: 프로젝트 태그 1개 (1.5%)
**After**: 프로젝트 태그 30-40개 (50-60%)

### 3. GUI 확인
- 김세린 페르소나 선택
- TODO 리스트에서 `[PV]`, `[PS]`, `[HA]` 등 프로젝트 태그 표시 확인
- 프로젝트 필터 바에서 필터링 작동 확인

## 🎉 예상 결과

### GUI에서 보이는 변화:
```
Before:
  ❌ 문서검토 (프로젝트 태그 없음)
  ❌ 업무처리 (프로젝트 태그 없음)
  ❌ 미팅참석 (프로젝트 태그 없음)

After:
  ✅ [PV] 문서검토
  ✅ [PS] 업무처리
  ✅ [HA] 미팅참석
```

### 프로젝트 필터 바:
```
🏷️ 프로젝트 필터  [전체] [PV] [PS] [HA] [CB] [WL] [VC]
                   ^^^^  ^^^^  ^^^^  ^^^^  ^^^^  ^^^^  ^^^^
                   클릭하면 해당 프로젝트 TODO만 표시
```

## ⚡ 지금 바로 실행!

**가장 빠른 방법 (옵션 1):**

1. GUI 종료
2. 명령 프롬프트에서:
   ```cmd
   del virtualoffice\src\virtualoffice\todos_cache.db
   python offline_agent\run_gui.py
   ```
3. 김세린 선택 → 분석 시작
4. 프로젝트 태그 확인! 🎉

**완료!** 이제 모든 TODO에 프로젝트 태그가 표시됩니다.
