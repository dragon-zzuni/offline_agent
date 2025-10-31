# -*- coding: utf-8 -*-
"""
Top3 캐시 관리 모듈

LLM 호출 결과를 캐싱하여 성능을 개선합니다.
"""
import time
import hashlib
import logging
from typing import Optional, Dict, Any, Set
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """캐시 항목"""
    key: str
    value: Set[str]  # TODO ID 집합
    created_at: float
    ttl: float
    
    def is_expired(self) -> bool:
        """만료 여부 확인"""
        return time.time() - self.created_at > self.ttl


class Top3CacheManager:
    """Top3 선정 결과 캐시 관리자
    
    LLM 호출 결과를 메모리에 캐싱하여 동일한 조건에서 재호출을 방지합니다.
    """
    
    def __init__(self, default_ttl: float = 300.0, ttl_seconds: Optional[float] = None):
        """
        Args:
            default_ttl: 기본 TTL (초, 기본값: 5분)
            ttl_seconds: TTL (초, 호환성용 - default_ttl과 동일)
        """
        # 호환성을 위해 ttl_seconds 파라미터도 지원
        if ttl_seconds is not None:
            self.default_ttl = ttl_seconds
        else:
            self.default_ttl = default_ttl
        self._cache: Dict[str, CacheEntry] = {}
        self._hit_count = 0
        self._miss_count = 0
    
    def _generate_cache_key(
        self,
        todos: list,
        rules: Optional[Dict[str, Any]] = None,
        instruction: Optional[str] = None
    ) -> str:
        """캐시 키 생성
        
        TODO 목록, 규칙, 지시사항을 조합하여 고유 키를 생성합니다.
        
        Args:
            todos: TODO 항목 리스트
            rules: 엔티티 규칙
            instruction: 자연어 지시사항
            
        Returns:
            캐시 키 (해시 문자열)
        """
        # TODO ID 목록 (정렬하여 순서 무관하게)
        todo_ids = sorted([t.get("id", "") for t in todos if t.get("id")])
        
        # 규칙 문자열화
        rules_str = ""
        if rules:
            # 요청자 규칙만 사용 (가장 중요)
            requester_rules = rules.get("requester", {})
            if requester_rules:
                rules_str = ",".join(sorted(f"{k}:{v}" for k, v in requester_rules.items()))
        
        # 지시사항
        instruction_str = instruction or ""
        
        # 조합하여 해시 생성
        combined = f"{','.join(todo_ids)}|{rules_str}|{instruction_str}"
        cache_key = hashlib.md5(combined.encode()).hexdigest()
        
        logger.debug(f"[Top3Cache] 캐시 키 생성: {cache_key[:16]}... (TODO {len(todo_ids)}개)")
        
        return cache_key
    
    def get(
        self,
        todos: list,
        rules: Optional[Dict[str, Any]] = None,
        instruction: Optional[str] = None
    ) -> Optional[Set[str]]:
        """캐시에서 조회
        
        Args:
            todos: TODO 항목 리스트
            rules: 엔티티 규칙
            instruction: 자연어 지시사항
            
        Returns:
            캐시된 TODO ID 집합 또는 None
        """
        cache_key = self._generate_cache_key(todos, rules, instruction)
        
        # 만료된 항목 정리
        self._cleanup_expired()
        
        entry = self._cache.get(cache_key)
        
        if entry and not entry.is_expired():
            self._hit_count += 1
            logger.info(f"[Top3Cache] 캐시 히트: {cache_key[:16]}... (TTL 남음: {entry.ttl - (time.time() - entry.created_at):.0f}초)")
            return entry.value
        
        self._miss_count += 1
        logger.debug(f"[Top3Cache] 캐시 미스: {cache_key[:16]}...")
        return None
    
    def set(
        self,
        todos: list,
        result: Set[str],
        rules: Optional[Dict[str, Any]] = None,
        instruction: Optional[str] = None,
        ttl: Optional[float] = None
    ) -> None:
        """캐시에 저장
        
        Args:
            todos: TODO 항목 리스트
            result: 선정된 TODO ID 집합
            rules: 엔티티 규칙
            instruction: 자연어 지시사항
            ttl: TTL (초, None이면 기본값 사용)
        """
        cache_key = self._generate_cache_key(todos, rules, instruction)
        ttl = ttl or self.default_ttl
        
        entry = CacheEntry(
            key=cache_key,
            value=result,
            created_at=time.time(),
            ttl=ttl
        )
        
        self._cache[cache_key] = entry
        logger.info(f"[Top3Cache] 캐시 저장: {cache_key[:16]}... (TTL: {ttl:.0f}초, 결과: {len(result)}개)")
    
    def invalidate(
        self,
        todos: Optional[list] = None,
        rules: Optional[Dict[str, Any]] = None,
        instruction: Optional[str] = None
    ) -> None:
        """캐시 무효화
        
        Args:
            todos: TODO 항목 리스트 (None이면 전체 무효화)
            rules: 엔티티 규칙
            instruction: 자연어 지시사항
        """
        if todos is None:
            # 전체 무효화
            count = len(self._cache)
            self._cache.clear()
            logger.info(f"[Top3Cache] 전체 캐시 무효화: {count}개 항목 삭제")
        else:
            # 특정 키 무효화
            cache_key = self._generate_cache_key(todos, rules, instruction)
            if cache_key in self._cache:
                del self._cache[cache_key]
                logger.info(f"[Top3Cache] 캐시 무효화: {cache_key[:16]}...")
    
    def _cleanup_expired(self) -> None:
        """만료된 캐시 항목 정리"""
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.is_expired()
        ]
        
        for key in expired_keys:
            del self._cache[key]
        
        if expired_keys:
            logger.debug(f"[Top3Cache] 만료된 캐시 정리: {len(expired_keys)}개 항목 삭제")
    
    def get_stats(self) -> Dict[str, Any]:
        """캐시 통계 반환"""
        total_requests = self._hit_count + self._miss_count
        hit_rate = (self._hit_count / total_requests * 100) if total_requests > 0 else 0.0
        
        return {
            "cache_size": len(self._cache),
            "hit_count": self._hit_count,
            "miss_count": self._miss_count,
            "total_requests": total_requests,
            "hit_rate": hit_rate,
        }
    
    def clear_stats(self) -> None:
        """통계 초기화"""
        self._hit_count = 0
        self._miss_count = 0
        logger.debug("[Top3Cache] 통계 초기화")
