# LLM API 사용 가이드

## 개요

Smart Assistant는 여러 LLM 공급자를 지원하며, 각 공급자의 API 특성에 맞게 최적화된 파라미터를 사용합니다.

## 지원되는 LLM 공급자

### 1. Azure OpenAI

Microsoft Azure의 OpenAI 서비스를 사용합니다.

#### 환경 변수 설정
```bash
AZURE_OPENAI_KEY=your_api_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_DEPLOYMENT=your_deployment_name
AZURE_OPENAI_API_VERSION=2024-08-01-preview  # 권장
LLM_PROVIDER=azure
```

#### API 파라미터
- **max_completion_tokens**: 생성할 최대 토큰 수 (기본값: 500)
- **temperature**: deployment 설정에서 관리 (API 호출 시 생략)
- **model**: deployment에서 지정 (API 호출 시 생략)

#### 주의사항
- API 버전은 `2024-08-01-preview` 이상을 권장합니다
- `max_tokens` 대신 `max_completion_tokens`를 사용해야 합니다
- `temperature`는 deployment 레벨에서 설정하므로 API 호출 시 생략합니다
- deployment 이름은 Azure Portal에서 확인할 수 있습니다

#### 예시 코드
```python
# Azure OpenAI API 호출
payload = {
    "messages": [
        {"role": "system", "content": "당신은 업무 요약 전문가입니다."},
        {"role": "user", "content": "다음 메시지를 요약해주세요: ..."}
    ],
    "max_completion_tokens": 500
}
```

### 2. OpenAI

OpenAI의 공식 API를 직접 사용합니다.

#### 환경 변수 설정
```bash
OPENAI_API_KEY=your_api_key
LLM_PROVIDER=openai
```

#### API 파라미터
- **model**: 사용할 모델 (기본값: gpt-4)
- **max_tokens**: 생성할 최대 토큰 수 (기본값: 500)
- **temperature**: 생성 다양성 (기본값: 0.7)

#### 예시 코드
```python
# OpenAI API 호출
payload = {
    "model": "gpt-4",
    "messages": [
        {"role": "system", "content": "당신은 업무 요약 전문가입니다."},
        {"role": "user", "content": "다음 메시지를 요약해주세요: ..."}
    ],
    "max_tokens": 500,
    "temperature": 0.7
}
```

### 3. OpenRouter

여러 LLM 모델을 통합 제공하는 OpenRouter 서비스를 사용합니다.

#### 환경 변수 설정
```bash
OPENROUTER_API_KEY=your_api_key
LLM_PROVIDER=openrouter
```

#### API 파라미터
- **model**: 사용할 모델 (예: openrouter/auto)
- **max_tokens**: 생성할 최대 토큰 수 (기본값: 500)
- **temperature**: 생성 다양성 (기본값: 0.7)

#### 예시 코드
```python
# OpenRouter API 호출
payload = {
    "model": "openrouter/auto",
    "messages": [
        {"role": "system", "content": "당신은 업무 요약 전문가입니다."},
        {"role": "user", "content": "다음 메시지를 요약해주세요: ..."}
    ],
    "max_tokens": 500,
    "temperature": 0.7
}
```

## 공급자별 비교

| 특성 | Azure OpenAI | OpenAI | OpenRouter |
|------|-------------|--------|------------|
| 토큰 제한 파라미터 | max_completion_tokens | max_tokens | max_tokens |
| temperature 설정 | deployment 레벨 | API 호출 시 | API 호출 시 |
| 모델 지정 | deployment 레벨 | API 호출 시 | API 호출 시 |
| API 버전 | 필수 (URL 파라미터) | 불필요 | 불필요 |
| 인증 방식 | api-key 헤더 | Bearer 토큰 | Bearer 토큰 |

## 사용 위치

### TODO 상세 다이얼로그
- **요약 생성**: 원본 메시지를 3-5개 불릿 포인트로 요약
- **회신 초안 작성**: 정중하고 명확한 회신 자동 생성

### 메시지 분석 파이프라인
- **메시지 요약**: 개별 메시지 핵심 내용 추출
- **대화 요약**: 여러 메시지의 전체 흐름 파악
- **우선순위 분석**: 메시지의 긴급도 및 중요도 판단
- **액션 추출**: 실행 가능한 TODO 항목 생성

## 에러 처리

### 일반적인 오류

#### 1. 400 Bad Request
```
원인: 잘못된 API 파라미터
해결: 공급자별 파라미터 규격 확인
- Azure: max_completion_tokens 사용
- OpenAI/OpenRouter: max_tokens 사용
```

#### 2. 401 Unauthorized
```
원인: API 키가 잘못되었거나 만료됨
해결: .env 파일의 API 키 확인
```

#### 3. 429 Too Many Requests
```
원인: API 호출 한도 초과
해결: 요청 빈도 조절 또는 플랜 업그레이드
```

#### 4. 500 Internal Server Error
```
원인: LLM 서비스 내부 오류
해결: 잠시 후 재시도
```

### 에러 로깅

모든 API 호출 오류는 로그에 기록됩니다:

```python
logger.error(f"[TodoDetail][LLM] API 호출 실패: {e}")
```

로그 파일 위치: `logs/` 디렉토리 (향후 구현 예정)

## 성능 최적화

### 토큰 사용량 최적화
- 요약 생성: 최대 500 토큰
- 회신 초안: 최대 500 토큰
- 프롬프트 최적화로 불필요한 토큰 사용 최소화

### 동시 요청 제한
- 배치 처리 시 동시 요청 수 제한 (기본값: 5)
- 과도한 API 호출 방지

### 캐싱
- 동일한 메시지에 대한 중복 요청 방지
- 요약 결과를 메모리에 캐싱

## 비용 관리

### Azure OpenAI
- deployment 레벨에서 토큰 제한 설정 가능
- 월별 사용량 모니터링 권장

### OpenAI
- 사용량 대시보드에서 실시간 모니터링
- 월별 한도 설정 권장

### OpenRouter
- 크레딧 기반 과금
- 모델별 가격 차이 확인

## 문제 해결

### Azure OpenAI 연결 실패
1. endpoint URL 확인 (https://your-resource.openai.azure.com)
2. deployment 이름 확인
3. API 버전 확인 (2024-08-01-preview 권장)
4. API 키 유효성 확인

### OpenAI 연결 실패
1. API 키 유효성 확인
2. 네트워크 연결 확인
3. 방화벽 설정 확인

### OpenRouter 연결 실패
1. API 키 유효성 확인
2. 크레딧 잔액 확인
3. 모델 가용성 확인

## 참고 자료

- [Azure OpenAI 공식 문서](https://learn.microsoft.com/azure/ai-services/openai/)
- [OpenAI API 문서](https://platform.openai.com/docs/api-reference)
- [OpenRouter 문서](https://openrouter.ai/docs)

## 관련 파일

- `ui/todo_panel.py`: TODO 상세 다이얼로그 LLM 호출
- `nlp/summarize.py`: 메시지 요약 LLM 호출
- `config/settings.py`: LLM 설정 관리
