# Smart Assistant v1.2.0 릴리스 노트

**릴리스 날짜**: 2025-10-20

## 🎯 주요 변경사항

### 데이터셋 마이그레이션 📁

v1.2.0에서는 기본 데이터셋을 `mobile_4week_ko`에서 `multi_project_8week_ko`로 변경했습니다. 더 풍부한 데이터와 긴 기간의 메시지를 분석할 수 있습니다.

## ✨ 새로운 데이터셋

### multi_project_8week_ko
- **기간**: 8주 데이터 (기존 4주에서 2배 증가)
- **팀 구성**: PM, 디자이너, 개발자, DevOps (4명)
- **PM 정보**:
  - 이름: 이민주
  - 이메일: pm.1@multiproject.dev
  - 역할: 프로젝트 매니저
- **프로젝트**: 멀티 프로젝트 환경
- **메시지 수**: 더 많은 이메일 및 메신저 대화

### 레거시 데이터셋 (mobile_4week_ko)
- **상태**: 지원 종료
- **사용 가능**: 수동으로 경로 변경 시 사용 가능
- **권장**: 새 데이터셋으로 마이그레이션

## 📝 변경된 파일

### 코드 변경
- `main.py`: `DEFAULT_DATASET_ROOT` 경로 변경
  ```python
  # 기존
  DEFAULT_DATASET_ROOT = project_root / "data" / "mobile_4week_ko"
  
  # 변경
  DEFAULT_DATASET_ROOT = project_root / "data" / "multi_project_8week_ko"
  ```

- `ui/main_window.py`: `TODO_DB_PATH` 경로 변경
  ```python
  TODO_DB_PATH = os.path.join("data", "multi_project_8week_ko", "todos_cache.db")
  ```

- `.env`: `MESSENGER_DB_PATH` 경로 변경
  ```bash
  MESSENGER_DB_PATH=data/multi_project_8week_ko/todos_cache.db
  ```

### 문서 업데이트
- `README.md`: 데이터셋 정보 업데이트
- `CHANGELOG.md`: v1.2.0 변경사항 추가
- `docs/DEVELOPMENT.md`: 프로젝트 구조 업데이트
- `docs/DATASET_MIGRATION.md`: 마이그레이션 가이드 (기존)

## 🔄 업그레이드 방법

### 자동 마이그레이션 (권장)
```bash
# 저장소 업데이트
git pull origin main

# 애플리케이션 실행 (자동으로 새 데이터셋 사용)
python run_gui.py
```

### 수동 마이그레이션
기존 TODO 데이터를 유지하려면:

1. **기존 TODO 백업**:
   ```bash
   cp data/mobile_4week_ko/todos_cache.db data/mobile_4week_ko/todos_cache.db.backup
   ```

2. **새 데이터셋 확인**:
   ```bash
   ls data/multi_project_8week_ko/
   ```

3. **애플리케이션 실행**:
   ```bash
   python run_gui.py
   ```

### 레거시 데이터셋 계속 사용
기존 데이터셋을 계속 사용하려면 `main.py`를 수정:

```python
# main.py
DEFAULT_DATASET_ROOT = project_root / "data" / "mobile_4week_ko"
```

**주의**: 레거시 데이터셋은 향후 버전에서 지원이 중단될 수 있습니다.

## 📊 데이터셋 비교

| 항목 | mobile_4week_ko | multi_project_8week_ko |
|------|----------------|------------------------|
| **기간** | 4주 | 8주 |
| **팀 구성** | 모바일 앱 팀 | 멀티 프로젝트 팀 |
| **PM 이메일** | pm@mobile.dev | pm.1@multiproject.dev |
| **메시지 수** | 적음 | 많음 |
| **프로젝트 복잡도** | 단일 프로젝트 | 멀티 프로젝트 |
| **지원 상태** | 종료 | 활성 |

## 🎬 사용 시나리오

### 시나리오 1: 신규 사용자
```bash
# 저장소 클론
git clone <repository-url>
cd smart_assistant

# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정
cp .env.example .env
# .env 파일 편집하여 API 키 설정

# 애플리케이션 실행 (자동으로 새 데이터셋 사용)
python run_gui.py
```

### 시나리오 2: 기존 사용자 (자동 마이그레이션)
```bash
# 저장소 업데이트
git pull origin main

# 애플리케이션 실행
python run_gui.py

# 새 데이터셋으로 메시지 수집
# GUI에서 "메시지 수집 시작" 버튼 클릭
```

### 시나리오 3: 기존 TODO 유지
```bash
# 기존 TODO 백업
cp data/mobile_4week_ko/todos_cache.db backup/

# 새 데이터셋으로 전환
# (자동으로 새 todos_cache.db 생성됨)

# 필요시 기존 TODO를 수동으로 복사
# (권장하지 않음: 데이터 불일치 가능)
```

## 🐛 버그 수정

이번 릴리스에는 버그 수정이 포함되지 않았습니다. 데이터셋 마이그레이션에 집중했습니다.

## 📊 성능 개선

- **더 많은 데이터**: 8주 데이터로 더 정확한 분석 가능
- **멀티 프로젝트**: 복잡한 프로젝트 환경 시뮬레이션
- **향상된 TODO 생성**: 더 많은 메시지에서 더 정확한 TODO 추출

## 🔮 향후 계획

### v1.2.1 (예정)
- [ ] 데이터셋 선택 UI 추가
- [ ] 여러 데이터셋 동시 지원
- [ ] 데이터셋 통계 대시보드

### v1.3.0 (예정)
- [ ] 커스텀 데이터셋 가져오기
- [ ] 데이터셋 병합 기능
- [ ] 데이터셋 내보내기 (JSON, CSV)

## ⚠️ 주의사항

### 호환성
- **Python 버전**: 3.7 이상 (변경 없음)
- **의존성**: 변경 없음
- **API**: 변경 없음

### 데이터 손실 방지
- 기존 TODO 데이터는 `mobile_4week_ko/todos_cache.db`에 그대로 유지됩니다
- 새 TODO는 `multi_project_8week_ko/todos_cache.db`에 저장됩니다
- 두 데이터베이스는 독립적으로 관리됩니다

### 성능
- 8주 데이터로 인해 초기 로딩 시간이 약간 증가할 수 있습니다
- 메모리 사용량은 거의 동일합니다
- 분석 시간은 메시지 수에 비례하여 증가합니다

## 💡 팁

### 빠른 테스트
```bash
# 새 데이터셋으로 빠르게 테스트
python run_gui.py

# 메시지 수집 시작
# 시간 범위: 최근 7일 선택 (빠른 테스트)
```

### 전체 데이터 분석
```bash
# 전체 8주 데이터 분석
# 시간 범위: 전체 기간 선택
# 예상 시간: 5-10분 (LLM API 속도에 따라)
```

### 데이터셋 전환
```python
# main.py에서 경로 변경
DEFAULT_DATASET_ROOT = project_root / "data" / "mobile_4week_ko"  # 레거시
DEFAULT_DATASET_ROOT = project_root / "data" / "multi_project_8week_ko"  # 현재
```

## 🙏 감사의 말

이번 릴리스는 더 풍부한 데이터와 긴 기간의 분석을 제공하여 사용자 경험을 크게 개선합니다. 앞으로도 더 나은 기능을 제공하기 위해 노력하겠습니다.

## 📞 지원

- 이슈 리포팅: GitHub Issues
- 문서: [README.md](README.md)
- 마이그레이션 가이드: [DATASET_MIGRATION.md](docs/DATASET_MIGRATION.md)
- 개발 가이드: [DEVELOPMENT.md](docs/DEVELOPMENT.md)

---

**전체 변경사항**: [v1.1.9...v1.2.0](https://github.com/yourusername/smart_assistant/compare/v1.1.9...v1.2.0)
