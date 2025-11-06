# VDOS DB 통합 마이그레이션

## 개요
모든 데이터 소스를 `virtualoffice/src/virtualoffice/vdos.db`로 통합하여 단일 데이터베이스 사용

## 변경 사항

### 1. People 데이터
**이전:** `data/multi_project_8week_ko/people_*.json`
**이후:** `vdos.db` → `people` 테이블

- VDOSConnector를 통해 실시간 로드
- 이메일 → 이름 매핑 자동 구축
- Top3Service에서 자동 활용

### 2. TODO 저장소
**이전:** `data/multi_project_8week_ko/todos_cache.db`
**이후:** `virtualoffice/src/virtualoffice/todos_cache.db`

- VDOS DB와 같은 디렉토리에 저장
- 동적 경로 설정 (VDOS 연결 상태에 따라)
- 폴백: `data/todos_cache.db`

### 3. Top3 설정 파일
**이전:** `data/multi_project_8week_ko/top3_config.json`
**이후:** `virtualoffice/src/virtualoffice/top3_config.json`

- VDOS DB와 같은 디렉토리에 저장
- 규칙이 people 데이터와 동기화됨

### 4. 메시지 데이터
**이전:** `data/multi_project_8week_ko/*.json` (정적 파일)
**이후:** VirtualOffice API (실시간)

- `vdos.db` → `emails`, `chat_messages` 테이블
- VirtualOfficeClient를 통해 실시간 조회
- 증분 업데이트 지원

## 장점

### 1. 단일 데이터 소스
- 모든 데이터가 `vdos.db`에 집중
- 데이터 일관성 보장
- 동기화 문제 해소

### 2. 실시간 업데이트
- VirtualOffice 시뮬레이션과 실시간 연동
- 새로운 메시지/TODO 즉시 반영
- 폴링을 통한 자동 갱신

### 3. 확장성
- 새로운 페르소나 추가 시 자동 인식
- 프로젝트 추가/변경 자동 반영
- 설정 파일 관리 간소화

## 마이그레이션 가이드

### 기존 데이터 백업
```bash
# 기존 JSON 파일 백업 (선택사항)
cp -r data/multi_project_8week_ko data/backup_$(date +%Y%m%d)
```

### 새 시스템 사용
1. VirtualOffice 시뮬레이션 실행
2. offline_agent 실행
3. 페르소나 선택 (예: 이정두)
4. 자동으로 `vdos.db` 연결 및 데이터 로드

### 폴백 모드
VDOS 연결 실패 시:
- TODO DB: `data/todos_cache.db`
- Top3 설정: `data/top3_config.json`
- People 데이터: JSON 파일 로드 시도

## 파일 구조

```
virtualoffice/src/virtualoffice/
├── vdos.db                    # 메인 데이터베이스
├── todos_cache.db             # TODO 캐시 (새 위치)
└── top3_config.json           # Top3 규칙 (새 위치)

offline_agent/
├── data/
│   ├── todos_cache.db         # 폴백용
│   └── top3_config.json       # 폴백용
└── src/
    └── utils/
        └── vdos_connector.py  # VDOS 연동 모듈
```

## 주의사항

1. **VirtualOffice 필수**: VDOS DB가 없으면 폴백 모드로 작동
2. **경로 변경**: 기존 설정 파일은 자동으로 새 위치로 복사되지 않음
3. **데이터 초기화**: 새 위치의 TODO DB는 비어있음 (실시간 생성)

## 테스트

```bash
# VDOS 연결 테스트
python offline_agent/test_vdos_schema.py

# People 데이터 로드 테스트
python offline_agent/test_matching_debug.py

# Top3 규칙 테스트
python offline_agent/test_serin_matching.py
```

## 롤백

기존 시스템으로 돌아가려면:
1. `main_window.py`에서 `TODO_DB_PATH` 하드코딩
2. `Top3Service.__init__`에서 `config_path` 하드코딩
3. VDOSConnector 사용 제거
