"""
페르소나별 TODO 캐시 관리 서비스

페르소나 전환 시 분석 결과를 캐싱하여 빠른 응답을 제공합니다.
LRU 정책으로 최대 10개의 캐시를 유지하며, 캐시 통계를 수집합니다.
"""

import logging
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
from collections import OrderedDict

logger = logging.getLogger(__name__)


@dataclass
class CacheKey:
    """캐시 키 생성을 위한 데이터 클래스"""
    persona_id: str  # mailbox 또는 handle
    time_range_start: Optional[str]  # ISO format
    time_range_end: Optional[str]    # ISO format
    data_version: str  # 데이터 버전 (틱 번호 또는 타임스탬프)
    
    def to_hash(self) -> str:
        """캐시 키를 해시로 변환"""
        key_str = f"{self.persona_id}|{self.time_range_start}|{self.time_range_end}|{self.data_version}"
        return hashlib.sha256(key_str.encode()).hexdigest()[:16]
    
    def __str__(self) -> str:
        return f"CacheKey({self.persona_id}, {self.time_range_start}~{self.time_range_end}, v{self.data_version})"


@dataclass
class CachedAnalysisResult:
    """캐시된 분석 결과"""
    cache_key: str
    persona_id: str
    todo_list: List[Dict[str, Any]]
    messages: List[Dict[str, Any]]
    analysis_summary: Dict[str, Any]
    created_at: datetime
    last_accessed_at: datetime = field(default_factory=datetime.now)
    analysis_data: List[Dict[str, Any]] = field(default_factory=list)
    
    def update_access_time(self) -> None:
        """마지막 접근 시간 업데이트"""
        self.last_accessed_at = datetime.now()


class PersonaTodoCacheService:
    """페르소나별 TODO 캐시 관리 서비스
    
    LRU(Least Recently Used) 정책으로 최대 max_cache_size개의 캐시를 유지합니다.
    캐시 히트/미스 통계를 수집하고 로깅합니다.
    """
    
    def __init__(self, max_cache_size: int = 10):
        """
        Args:
            max_cache_size: 최대 캐시 개수 (기본값: 10)
        """
        self._cache: OrderedDict[str, CachedAnalysisResult] = OrderedDict()
        self._max_cache_size = max_cache_size
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "invalidations": 0
        }
        logger.info(f"PersonaTodoCacheService 초기화 (max_size={max_cache_size})")
    
    def get(self, cache_key: CacheKey) -> Optional[CachedAnalysisResult]:
        """캐시에서 분석 결과 조회
        
        Args:
            cache_key: 조회할 캐시 키
            
        Returns:
            캐시된 분석 결과 또는 None (캐시 미스)
        """
        key_hash = cache_key.to_hash()
        
        if key_hash in self._cache:
            # 캐시 히트
            result = self._cache[key_hash]
            result.update_access_time()
            
            # LRU 순서 업데이트 (가장 최근 사용으로 이동)
            self._cache.move_to_end(key_hash)
            
            self._stats["hits"] += 1
            logger.info(f"✅ 캐시 히트: {cache_key} (히트율: {self.get_hit_rate():.1%})")
            logger.debug(f"캐시 생성 시간: {result.created_at}, 마지막 접근: {result.last_accessed_at}")
            
            return result
        else:
            # 캐시 미스
            self._stats["misses"] += 1
            logger.info(f"❌ 캐시 미스: {cache_key} (히트율: {self.get_hit_rate():.1%})")
            return None
    
    def put(self, cache_key: CacheKey, result: CachedAnalysisResult) -> None:
        """분석 결과를 캐시에 저장
        
        Args:
            cache_key: 캐시 키
            result: 저장할 분석 결과
        """
        key_hash = cache_key.to_hash()
        
        # 캐시 크기 확인 및 LRU 제거
        if len(self._cache) >= self._max_cache_size and key_hash not in self._cache:
            self._evict_lru()
        
        # 캐시에 저장
        self._cache[key_hash] = result
        self._cache.move_to_end(key_hash)  # 가장 최근 사용으로 이동
        
        logger.info(f"💾 캐시 저장: {cache_key} (현재 캐시 수: {len(self._cache)}/{self._max_cache_size})")
        logger.debug(f"TODO 개수: {len(result.todo_list)}, 메시지 개수: {len(result.messages)}")
    
    def invalidate(self, persona_id: Optional[str] = None) -> int:
        """캐시 무효화
        
        Args:
            persona_id: 특정 페르소나의 캐시만 무효화 (None이면 전체 무효화)
            
        Returns:
            무효화된 캐시 개수
        """
        if persona_id is None:
            return self.invalidate_all()
        
        # 특정 페르소나의 캐시만 제거
        keys_to_remove = [
            key for key, cached_result in self._cache.items()
            if cached_result.persona_id == persona_id
        ]
        
        for key in keys_to_remove:
            del self._cache[key]
        
        count = len(keys_to_remove)
        if count > 0:
            self._stats["invalidations"] += count
            logger.info(f"🗑️ 캐시 무효화: persona_id={persona_id}, 제거된 캐시 수={count}")
        
        return count
    
    def invalidate_all(self) -> int:
        """모든 캐시 무효화
        
        Returns:
            무효화된 캐시 개수
        """
        count = len(self._cache)
        self._cache.clear()
        
        if count > 0:
            self._stats["invalidations"] += count
            logger.info(f"🗑️ 전체 캐시 무효화: 제거된 캐시 수={count}")
        
        return count
    
    def get_stats(self) -> Dict[str, Any]:
        """캐시 통계 반환
        
        Returns:
            캐시 통계 딕셔너리
        """
        total_requests = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total_requests if total_requests > 0 else 0.0
        
        return {
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "evictions": self._stats["evictions"],
            "invalidations": self._stats["invalidations"],
            "hit_rate": hit_rate,
            "current_cache_size": len(self._cache),
            "max_cache_size": self._max_cache_size
        }
    
    def get_hit_rate(self) -> float:
        """캐시 히트율 계산
        
        Returns:
            히트율 (0.0 ~ 1.0)
        """
        total_requests = self._stats["hits"] + self._stats["misses"]
        return self._stats["hits"] / total_requests if total_requests > 0 else 0.0
    
    def log_stats(self) -> None:
        """캐시 통계를 로그에 출력 (DEBUG 레벨)"""
        stats = self.get_stats()
        logger.debug(
            f"📊 캐시 통계: "
            f"히트={stats['hits']}, 미스={stats['misses']}, "
            f"히트율={stats['hit_rate']:.1%}, "
            f"제거={stats['evictions']}, 무효화={stats['invalidations']}, "
            f"현재 크기={stats['current_cache_size']}/{stats['max_cache_size']}"
        )
    
    def _evict_lru(self) -> None:
        """LRU 정책으로 가장 오래된 캐시 제거"""
        if not self._cache:
            return
        
        # OrderedDict의 첫 번째 항목이 가장 오래된 항목
        oldest_key, oldest_result = self._cache.popitem(last=False)
        
        self._stats["evictions"] += 1
        logger.debug(
            f"🔄 LRU 제거: persona_id={oldest_result.persona_id}, "
            f"생성 시간={oldest_result.created_at}, "
            f"마지막 접근={oldest_result.last_accessed_at}"
        )
    
    def clear(self) -> None:
        """모든 캐시 및 통계 초기화"""
        self._cache.clear()
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "invalidations": 0
        }
        logger.info("🧹 캐시 및 통계 초기화 완료")
