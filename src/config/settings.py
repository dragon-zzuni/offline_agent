# -*- coding: utf-8 -*-
"""
Smart Assistant 설정 파일
"""
import os
import json
from pathlib import Path
from dotenv import load_dotenv



# 프로젝트 루트 디렉토리 (offline_agent/)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env", override=True)
# 데이터베이스 경로
DATABASE_PATH = PROJECT_ROOT / "data" / "assistant.db"
FAISS_INDEX_PATH = PROJECT_ROOT / "data" / "faiss_index"

# 로그 경로
LOG_PATH = PROJECT_ROOT / "logs"


# LLM 설정 및 로컬 저장소 경로
CONFIG_STORE_PATH = PROJECT_ROOT / "config" / "settings_rules.json"
CONFIG_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
if not CONFIG_STORE_PATH.exists():
    with open(CONFIG_STORE_PATH, "w", encoding="utf-8") as fh:
        json.dump(
            {"top3_rules": {"weights": None, "entities": None}},
            fh,
            ensure_ascii=False,
            indent=2,
        )


LLM_CONFIG = {
    # ✅ 공급자 선택: openai | openrouter
    "provider": os.getenv("LLM_PROVIDER", "azure"),

    # OpenAI 쓸 때만 사용
    "openai_api_key": os.getenv("OPENAI_API_KEY"),

    # ✅ OpenRouter 설정
    "openrouter_api_key": os.getenv("OPENROUTER_API_KEY"),
    "openrouter_base_url": "https://openrouter.ai/api/v1",

    # ✅ Azure OpenAI 설정
    "azure_api_key": os.getenv("AZURE_OPENAI_KEY"),
    "azure_endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
    "azure_deployment": os.getenv("AZURE_OPENAI_DEPLOYMENT"),
    "azure_api_version": os.getenv("AZURE_OPENAI_API_VERSION"),

    # ✅ OpenRouter 모델명 예시
    #   - 자동 라우팅: "openrouter/auto"
    #   - 특정 모델: "anthropic/claude-3.5-sonnet" | "openai/gpt-4o-mini" 등
    "model": os.getenv("LLM_MODEL", "openrouter/auto"),

    "embedding_model": "text-embedding-3-small",   # (지금 프로젝트에선 안 씀)
    # Azure GPT-5는 추론 토큰 소모량이 커서 넉넉한 출력 토큰 한도를 사용합니다.
    "max_tokens": 2048,
    "temperature": 0.2,
}

# UI 설정
UI_CONFIG = {
    "window_width": 1200,
    "window_height": 800,
    "refresh_interval": 5000,  # 5초
    "max_todo_items": 20
}

# 우선순위 규칙
PRIORITY_RULES = {
    "high_priority_keywords": [
        "긴급", "urgent", "asap", "즉시", "오늘까지", "deadline",
        "미팅", "회의", "프레젠테이션", "발표"
    ],
    "high_priority_senders": [
        "boss@company.com", "manager@company.com", "hr@company.com"
    ],
    "medium_priority_keywords": [
        "요청", "request", "검토", "review", "확인", "check"
    ]
}

# 템플릿 설정
EMAIL_TEMPLATES = {
    "reply_acknowledgment": """
안녕하세요 {sender_name}님,

메일을 확인했습니다. {action_required}에 대해 검토 후 답변드리겠습니다.

감사합니다.
{user_name}
    """,
    "meeting_request": """
안녕하세요 {sender_name}님,

미팅 요청을 확인했습니다. 
제안해주신 시간: {proposed_time}
장소: {location}

확인 후 일정을 조율해드리겠습니다.

감사합니다.
{user_name}
    """,
    "task_delegation": """
안녕하세요 {sender_name}님,

업무 위임 요청을 확인했습니다.
업무 내용: {task_description}
기한: {deadline}

검토 후 진행 계획을 공유드리겠습니다.

감사합니다.
{user_name}
    """
}

# 로깅 설정
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default"
        }
    },
    "root": {
        "level": "INFO",
        "handlers": ["console"]
    }
}
