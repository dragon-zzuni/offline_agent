# -*- coding: utf-8 -*-
"""
LLM 클라이언트 통합 모듈

OpenAI, Azure OpenAI, OpenRouter를 지원하는 통합 LLM 클라이언트
"""
import os
import logging
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# 로깅 레벨 확인을 위한 상수
DEBUG = logging.DEBUG


@dataclass
class LLMResponse:
    """LLM 응답 데이터 클래스"""
    content: str
    model: str
    provider: str
    tokens_used: Optional[int] = None
    response_time: Optional[float] = None
    error: Optional[str] = None


class LLMClient:
    """통합 LLM 클라이언트
    
    환경 변수를 통해 제공자를 자동 선택하고 API 호출을 수행합니다.
    
    환경 변수:
        LLM_PROVIDER: "openai" | "azure" | "openrouter" | "auto" (기본값)
        OPENAI_API_KEY: OpenAI API 키
        AZURE_OPENAI_KEY: Azure OpenAI API 키
        AZURE_OPENAI_ENDPOINT: Azure OpenAI 엔드포인트
        AZURE_OPENAI_DEPLOYMENT: Azure OpenAI 배포 이름
        AZURE_OPENAI_API_VERSION: Azure OpenAI API 버전
        OPENROUTER_API_KEY: OpenRouter API 키
    """
    
    def __init__(
        self,
        provider: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 2
    ):
        """
        Args:
            provider: LLM 제공자 ("openai" | "azure" | "openrouter" | "auto")
            timeout: API 호출 타임아웃 (초)
            max_retries: 최대 재시도 횟수
        """
        self.provider = provider or os.getenv("LLM_PROVIDER", "auto")
        self.timeout = timeout
        self.max_retries = max_retries
        
        # 제공자별 설정 (기존 시스템과 호환)
        self._openai_key = os.getenv("OPENAI_API_KEY")
        self._azure_key = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("AZURE_OPENAI_KEY")
        self._azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self._azure_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
        self._azure_api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
        self._openrouter_key = os.getenv("OPENROUTER_API_KEY")
        
        # 사용 가능한 제공자 확인
        self._available_providers = self._check_available_providers()
        
        if not self._available_providers:
            logger.warning("사용 가능한 LLM 제공자가 없습니다. API 키를 확인하세요.")
    
    def is_available(self) -> bool:
        """LLM 클라이언트 사용 가능 여부 확인
        
        Returns:
            사용 가능하면 True, 아니면 False
        """
        return len(self._available_providers) > 0
    
    def _check_available_providers(self) -> List[str]:
        """사용 가능한 제공자 목록 반환"""
        available = []
        
        if self._openai_key:
            available.append("openai")
        
        if self._azure_key and self._azure_endpoint:
            available.append("azure")
        
        if self._openrouter_key:
            available.append("openrouter")
        
        return available
    
    def _select_provider(self) -> str:
        """실제 사용할 제공자 선택"""
        if self.provider != "auto":
            if self.provider in self._available_providers:
                return self.provider
            else:
                logger.warning(f"지정된 제공자 '{self.provider}'를 사용할 수 없습니다. 자동 선택합니다.")
        
        # 우선순위: OpenAI > Azure > OpenRouter
        if "openai" in self._available_providers:
            return "openai"
        elif "azure" in self._available_providers:
            return "azure"
        elif "openrouter" in self._available_providers:
            return "openrouter"
        else:
            raise RuntimeError("사용 가능한 LLM 제공자가 없습니다")
    
    def generate(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-4o-mini",
        temperature: float = 0.3,
        max_tokens: Optional[int] = None
    ) -> LLMResponse:
        """LLM 텍스트 생성
        
        Args:
            messages: 메시지 리스트 [{"role": "user", "content": "..."}]
            model: 모델 이름
            temperature: 온도 (0.0 ~ 1.0)
            max_tokens: 최대 토큰 수
            
        Returns:
            LLMResponse 객체
        """
        provider = self._select_provider()
        start_time = time.time()
        
        # 요청 로깅 (DEBUG)
        logger.debug(f"[LLMClient] 호출 시작: provider={provider}, model={model}, temp={temperature}")
        if logger.isEnabledFor(logging.DEBUG):
            for i, msg in enumerate(messages):
                role = msg.get("role", "")
                content = msg.get("content", "")
                logger.debug(f"[LLMClient] 메시지[{i}] role={role}, length={len(content)}")
                if len(content) < 500:
                    logger.debug(f"[LLMClient] 메시지[{i}] content={content}")
        
        try:
            if provider == "openai":
                response = self._call_openai(messages, model, temperature, max_tokens)
            elif provider == "azure":
                response = self._call_azure(messages, model, temperature, max_tokens)
            elif provider == "openrouter":
                response = self._call_openrouter(messages, model, temperature, max_tokens)
            else:
                raise RuntimeError(f"지원하지 않는 제공자: {provider}")
            
            response.response_time = time.time() - start_time
            
            # 응답 로깅 (INFO/DEBUG)
            logger.info(
                f"[LLMClient] 호출 성공: {response.response_time:.2f}초, "
                f"토큰={response.tokens_used or 'N/A'}"
            )
            
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"[LLMClient] 응답 길이: {len(response.content)}자")
                if len(response.content) < 1000:
                    logger.debug(f"[LLMClient] 응답 내용: {response.content}")
                else:
                    logger.debug(f"[LLMClient] 응답 내용 (앞 500자): {response.content[:500]}")
            
            # 느린 응답 경고
            if response.response_time > 10.0:
                logger.warning(
                    f"[LLMClient] 느린 응답: {response.response_time:.1f}초 "
                    f"(제공자: {provider}, 모델: {model})"
                )
            
            return response
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"[LLMClient] 호출 실패 ({elapsed:.2f}초): {e}")
            logger.debug(f"[LLMClient] 제공자: {provider}, 모델: {model}")
            import traceback
            logger.debug(traceback.format_exc())
            
            return LLMResponse(
                content="",
                model=model,
                provider=provider,
                response_time=elapsed,
                error=str(e)
            )
    
    def _call_openai(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: Optional[int]
    ) -> LLMResponse:
        """OpenAI API 호출"""
        try:
            import openai
        except ImportError:
            raise RuntimeError("openai 패키지가 설치되지 않았습니다")
        
        client = openai.OpenAI(
            api_key=self._openai_key,
            timeout=self.timeout,
            max_retries=self.max_retries
        )
        
        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
        
        response = client.chat.completions.create(**kwargs)
        
        return LLMResponse(
            content=response.choices[0].message.content,
            model=model,
            provider="openai",
            tokens_used=response.usage.total_tokens if response.usage else None
        )
    
    def _call_azure(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: Optional[int]
    ) -> LLMResponse:
        """Azure OpenAI API 호출"""
        try:
            import openai
        except ImportError:
            raise RuntimeError("openai 패키지가 설치되지 않았습니다")
        
        client = openai.AzureOpenAI(
            api_key=self._azure_key,
            azure_endpoint=self._azure_endpoint,
            api_version=self._azure_api_version,
            timeout=self.timeout,
            max_retries=self.max_retries
        )
        
        # Azure는 deployment name 사용
        deployment = self._azure_deployment
        
        kwargs = {
            "model": deployment,
            "messages": messages,
            "temperature": temperature,
        }
        
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
        
        response = client.chat.completions.create(**kwargs)
        
        return LLMResponse(
            content=response.choices[0].message.content,
            model=deployment,
            provider="azure",
            tokens_used=response.usage.total_tokens if response.usage else None
        )
    
    def _call_openrouter(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float,
        max_tokens: Optional[int]
    ) -> LLMResponse:
        """OpenRouter API 호출"""
        try:
            import requests
        except ImportError:
            raise RuntimeError("requests 패키지가 설치되지 않았습니다")
        
        # OpenRouter는 모델명 앞에 제공자 추가 필요
        if "/" not in model:
            model = f"openai/{model}"
        
        headers = {
            "Authorization": f"Bearer {self._openrouter_key}",
            "HTTP-Referer": "https://github.com/your-repo",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
        
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=self.timeout
        )
        
        response.raise_for_status()
        data = response.json()
        
        return LLMResponse(
            content=data["choices"][0]["message"]["content"],
            model=model,
            provider="openrouter",
            tokens_used=data.get("usage", {}).get("total_tokens")
        )
    
    def is_available(self) -> bool:
        """LLM 클라이언트 사용 가능 여부"""
        return len(self._available_providers) > 0
    
    def get_available_providers(self) -> List[str]:
        """사용 가능한 제공자 목록"""
        return self._available_providers.copy()
