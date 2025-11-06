# 기여 가이드

Smart Assistant 프로젝트에 기여해 주셔서 감사합니다! 이 문서는 프로젝트에 기여하는 방법을 안내합니다.

## 개발 환경 설정

### 1. 저장소 클론
```bash
git clone <repository-url>
cd smart_assistant
```

### 2. 가상 환경 생성 및 활성화
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

### 3. 의존성 설치
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # 개발 도구 (있는 경우)
```

### 4. 환경 변수 설정
`.env` 파일을 생성하고 필요한 API 키를 설정하세요.

## 코딩 스타일

### Python 코드
- **PEP 8** 스타일 가이드를 따릅니다.
- **타입 힌트**를 적극 활용합니다.
- **Docstring**은 Google 스타일을 사용합니다.
- 변수명과 함수명은 영어로 작성합니다.
- 주석은 한국어로 작성합니다.

### 코드 포맷팅
```bash
# Black으로 자동 포맷팅
black .

# Flake8으로 린팅
flake8 .
```

### Docstring 예시
```python
def calculate_score(priority: str, deadline: Optional[datetime]) -> float:
    """TODO 항목의 점수를 계산합니다.
    
    우선순위와 데드라인을 기반으로 점수를 계산합니다.
    
    Args:
        priority: 우선순위 레벨 ("high", "medium", "low")
        deadline: 마감 기한 (없으면 None)
        
    Returns:
        계산된 점수 (float)
        
    Raises:
        ValueError: 잘못된 우선순위 값이 입력된 경우
    """
    pass
```

## 커밋 메시지

### 커밋 메시지 형식
```
<타입>: <제목>

<본문>

<푸터>
```

### 타입
- `feat`: 새로운 기능 추가
- `fix`: 버그 수정
- `docs`: 문서 변경
- `style`: 코드 포맷팅, 세미콜론 누락 등
- `refactor`: 코드 리팩토링
- `test`: 테스트 코드 추가/수정
- `chore`: 빌드 프로세스, 도구 설정 등

### 예시
```
feat: 날씨 정보 기능 추가

- 기상청 API 연동
- Open-Meteo API 폴백 지원
- 날씨 기반 업무 팁 생성

Closes #123
```

## 브랜치 전략

- `main`: 안정 버전
- `develop`: 개발 버전
- `feature/<기능명>`: 새로운 기능 개발
- `fix/<버그명>`: 버그 수정
- `docs/<문서명>`: 문서 작업

## Pull Request 프로세스

1. **이슈 생성**: 작업할 내용에 대한 이슈를 먼저 생성합니다.
2. **브랜치 생성**: `feature/` 또는 `fix/` 브랜치를 생성합니다.
3. **코드 작성**: 코딩 스타일을 준수하며 작업합니다.
4. **테스트**: 변경사항이 기존 기능을 깨뜨리지 않는지 확인합니다.
5. **커밋**: 의미 있는 단위로 커밋합니다.
6. **PR 생성**: 상세한 설명과 함께 Pull Request를 생성합니다.
7. **리뷰**: 코드 리뷰를 받고 피드백을 반영합니다.
8. **병합**: 승인 후 `develop` 브랜치에 병합합니다.

## 테스트

### 단위 테스트 실행
```bash
pytest
```

### 특정 테스트 실행
```bash
pytest tests/test_main_window.py
```

### 커버리지 확인
```bash
pytest --cov=. --cov-report=html
```

## 문서화

- 새로운 기능을 추가할 때는 README.md를 업데이트합니다.
- API 변경사항은 CHANGELOG.md에 기록합니다.
- 복잡한 기능은 별도의 문서를 작성합니다.

## 이슈 리포팅

버그를 발견하거나 기능 제안이 있으면 이슈를 생성해 주세요.

### 버그 리포트 템플릿
```markdown
## 버그 설명
간단한 버그 설명

## 재현 방법
1. '...'로 이동
2. '...'를 클릭
3. '...'까지 스크롤
4. 오류 확인

## 예상 동작
예상했던 동작 설명

## 실제 동작
실제로 발생한 동작 설명

## 환경
- OS: [예: Windows 11]
- Python 버전: [예: 3.10.0]
- 애플리케이션 버전: [예: 1.0.0]

## 추가 정보
스크린샷, 로그 등
```

## 질문 및 지원

- 질문이 있으면 이슈를 생성하거나 토론 게시판을 이용해 주세요.
- 긴급한 보안 이슈는 비공개로 보고해 주세요.

## 라이선스

기여하신 코드는 프로젝트의 MIT 라이선스를 따릅니다.
