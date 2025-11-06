# -*- coding: utf-8 -*-
"""
VirtualOffice Data Source
VirtualOffice API 기반 데이터 소스
"""
import asyncio
import logging
import os
import time
import sqlite3
from bisect import bisect_right
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple

from data_sources.manager import DataSource
from integrations.virtualoffice_client import VirtualOfficeClient
from integrations.converters import (
    convert_email_to_internal_format,
    convert_message_to_internal_format,
    build_persona_maps
)
from utils.vdos_connector import VDOSConnector

logger = logging.getLogger(__name__)


class VirtualOfficeDataSource(DataSource):
    """VirtualOffice API 기반 데이터 소스"""
    
    # 메모리 관리 설정
    MAX_MESSAGES = 10000  # 최대 메시지 수
    CLEANUP_THRESHOLD = 11000  # 정리 시작 임계값
    
    def __init__(self, client: VirtualOfficeClient, selected_persona: Dict[str, Any]):
        """
        Args:
            client: VirtualOfficeClient 인스턴스
            selected_persona: 선택된 페르소나 정보
        """
        self.client = client
        self.selected_persona = selected_persona
        self.last_email_id = 0
        self.last_message_id = 0
        
        # 페르소나 정보 캐싱
        self.personas: List[Dict[str, Any]] = []
        self.persona_by_email: Dict[str, Dict[str, Any]] = {}
        self.persona_by_handle: Dict[str, Dict[str, Any]] = {}
        
        # 메시지 캐시 (메모리 관리용)
        self.cached_messages: List[Dict[str, Any]] = []

        # 시뮬레이션 시간 매핑
        self._tick_datetimes: List[datetime] = []
        self._tick_values: List[int] = []
        self._sim_base_dt: Optional[datetime] = None
        try:
            self._sim_hours_per_day = max(1, int(os.getenv("VDOS_HOURS_PER_DAY", "8")))
        except ValueError:
            self._sim_hours_per_day = 8
        self._vdos_connector: Optional[VDOSConnector] = None
        
        # 시뮬레이션 상태 캐시
        self._cached_sim_status: Optional[Dict[str, Any]] = None
        self._sim_status_cache_time: float = 0
        self._sim_status_cache_ttl: float = 2.0  # 2초 TTL
        
        # 초기화 시 페르소나 로드
        self._load_personas()
        self._initialize_simulation_clock()
        
        logger.info(
            f"VirtualOfficeDataSource 초기화: "
            f"페르소나={selected_persona.get('name', 'Unknown')}"
        )
    
    def _load_personas(self) -> None:
        """페르소나 정보 로드 및 캐싱"""
        try:
            self.personas = self.client.get_personas()
            self.persona_by_email, self.persona_by_handle = build_persona_maps(self.personas)
            logger.info(f"페르소나 로드 완료: {len(self.personas)}명")
        except Exception as e:
            logger.error(f"페르소나 로드 실패: {e}")
            self.personas = []
            self.persona_by_email = {}
            self.persona_by_handle = {}

    def _initialize_simulation_clock(self) -> None:
        """시뮬레이션 tick → datetime 매핑 초기화"""
        try:
            if not self._vdos_connector:
                self._vdos_connector = VDOSConnector()
            if not self._vdos_connector or not self._vdos_connector.is_available:
                logger.warning("VDOS DB를 사용할 수 없어 시뮬레이션 시간 매핑을 건너뜁니다.")
                return

            db_path = self._vdos_connector.vdos_db_path
            with sqlite3.connect(f"file:{db_path}?immutable=1", uri=True) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT tick, created_at FROM tick_log ORDER BY tick ASC")
                rows = cursor.fetchall()

            if not rows:
                logger.warning("tick_log 데이터가 없어 시뮬레이션 시간 매핑을 구성할 수 없습니다.")
                return

            tick_datetimes: List[datetime] = []
            tick_values: List[int] = []
            for row in rows:
                created_at = row["created_at"]
                tick = int(row["tick"])
                try:
                    dt = self._parse_db_datetime(created_at)
                except Exception:
                    continue
                tick_datetimes.append(dt)
                tick_values.append(tick)

            if not tick_datetimes:
                logger.warning("tick_log의 datetime 파싱에 실패했습니다.")
                return

            self._tick_datetimes = tick_datetimes
            self._tick_values = tick_values
            self._sim_base_dt = tick_datetimes[0]
            logger.info(
                "시뮬레이션 시계 초기화 완료: base=%s, ticks=%d",
                self._sim_base_dt.isoformat(),
                tick_values[-1],
            )
        except Exception as e:
            logger.warning(f"시뮬레이션 시간 매핑 초기화 실패: {e}", exc_info=True)

    @staticmethod
    def _parse_db_datetime(value: str) -> datetime:
        """SQLite timestamp를 UTC aware datetime으로 변환"""
        if not value:
            raise ValueError("빈 datetime 문자열입니다.")
        normalized = value.replace("Z", "+00:00")
        if "T" not in normalized and "+" not in normalized[10:]:
            return datetime.fromisoformat(normalized).replace(tzinfo=timezone.utc)
        return datetime.fromisoformat(normalized).astimezone(timezone.utc)

    def _safe_parse_iso_datetime(self, value: Optional[str]) -> Optional[datetime]:
        """메시지 날짜 문자열을 UTC aware datetime으로 변환"""
        if not value:
            return None
        try:
            normalized = value.replace("Z", "+00:00")
            if "T" not in normalized and "+" not in normalized[10:]:
                return datetime.fromisoformat(normalized).replace(tzinfo=timezone.utc)
            return datetime.fromisoformat(normalized).astimezone(timezone.utc)
        except Exception:
            return None

    def _infer_tick_for_datetime(self, dt: datetime) -> Optional[int]:
        """실제 발생 시각으로부터 시뮬레이션 tick 추정"""
        if not self._tick_datetimes or not self._tick_values:
            return None
        idx = bisect_right(self._tick_datetimes, dt)
        if idx <= 0:
            return self._tick_values[0]
        if idx >= len(self._tick_values):
            return self._tick_values[-1]
        return self._tick_values[idx - 1]

    def _compute_sim_datetime_from_tick(self, tick: int) -> Optional[Tuple[datetime, int, int]]:
        """tick을 시뮬레이션 datetime으로 변환"""
        if not self._sim_base_dt:
            return None
        tick = max(1, tick)
        day_ticks = max(1, self._sim_hours_per_day * 60)
        tick_index = tick - 1
        day_index = tick_index // day_ticks
        tick_of_day = tick_index % day_ticks
        minutes_24h = int((tick_of_day / day_ticks) * 1440)
        sim_dt = self._sim_base_dt + timedelta(days=day_index, minutes=minutes_24h)
        return sim_dt, day_index, minutes_24h

    def _annotate_simulation_timestamps(self, messages: List[Dict[str, Any]]) -> None:
        """메시지에 시뮬레이션 시간 관련 메타데이터를 주입"""
        if not messages or not self._sim_base_dt or not self._tick_datetimes:
            return

        for msg in messages:
            metadata = msg.get("metadata") or {}
            source_date = (
                metadata.get("original_date")
                or msg.get("date")
                or msg.get("timestamp")
                or msg.get("datetime")
            )
            msg_dt = self._safe_parse_iso_datetime(source_date)
            if not msg_dt:
                continue

            if msg_dt <= self._tick_datetimes[0]:
                tick = self._tick_values[0]
            elif msg_dt >= self._tick_datetimes[-1]:
                tick = self._tick_values[-1]
            else:
                tick = self._infer_tick_for_datetime(msg_dt)
            if not tick:
                continue

            result = self._compute_sim_datetime_from_tick(tick)
            if not result:
                continue

            sim_dt, day_index, minutes_24h = result
            hours = minutes_24h // 60
            minutes = minutes_24h % 60

            if source_date and "original_date" not in metadata:
                metadata["original_date"] = source_date

            metadata["sim_tick"] = tick
            metadata["sim_day_index"] = day_index + 1
            metadata["sim_time"] = f"Day {day_index + 1} {hours:02d}:{minutes:02d}"
            msg["metadata"] = metadata

            msg["simulated_datetime"] = sim_dt.isoformat()
            msg["sim_day_index"] = day_index + 1
            msg["sim_week_index"] = day_index // 7 + 1
            msg["sim_month_index"] = day_index // 30 + 1
            msg["date"] = sim_dt.isoformat()
    
    async def collect_messages(self, options: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        VirtualOffice API에서 메시지 수집
        
        Args:
            options: 수집 옵션
                - incremental: True면 증분 수집, False면 전체 수집 (기본값: False)
                - parallel: True면 병렬 수집, False면 순차 수집 (기본값: True)
                - time_range: 시간 범위 필터링 {"start": datetime, "end": datetime}
            
        Returns:
            메시지 리스트
        """
        options = options or {}
        incremental = options.get("incremental", False)
        parallel = options.get("parallel", True)
        time_range = options.get("time_range")
        
        # 선택된 페르소나의 메일박스와 핸들
        mailbox = self.selected_persona.get("email_address")
        handle = (self.selected_persona.get("chat_handle") or "").strip()
        
        if not mailbox or not handle:
            logger.error("선택된 페르소나에 email_address 또는 chat_handle이 없습니다")
            return []
        
        # 핸들을 소문자로 변환 (VDOS 데이터베이스 대소문자 불일치 해결)
        normalized_handle = handle.lower()
        
        logger.info(
            f"메시지 수집 시작 (증분={incremental}, 병렬={parallel}): "
            f"mailbox={mailbox}, handle={normalized_handle}"
        )
        
        # 증분 수집 시 since_id 사용
        since_email_id = self.last_email_id if incremental else None
        since_message_id = self.last_message_id if incremental else None
        
        # API 호출 (병렬 또는 순차)
        try:
            if parallel:
                raw_emails, raw_messages = await self._collect_parallel(
                    mailbox, normalized_handle, since_email_id, since_message_id
                )
            else:
                raw_emails = self.client.get_emails(mailbox, since_id=since_email_id)
                raw_messages = self.client.get_messages(
                    normalized_handle, since_id=since_message_id
                )
        except Exception as e:
            logger.error(f"API 호출 실패: {e}")
            return []
        
        # 데이터 변환 (성능 측정)
        start_time = time.time()
        emails = [
            convert_email_to_internal_format(e, self.persona_by_email, mailbox)
            for e in raw_emails
        ]
        email_time = time.time() - start_time
        
        start_time = time.time()
        messages = [
            convert_message_to_internal_format(
                m,
                self.persona_by_handle,
                selected_persona_handle=handle
            )
            for m in raw_messages
        ]
        message_time = time.time() - start_time
        
        logger.info(
            f"⏱️ 변환 시간: 이메일 {email_time:.2f}초 ({len(raw_emails)}개), "
            f"메시지 {message_time:.2f}초 ({len(raw_messages)}개)"
        )
        
        # last_id 업데이트
        if raw_emails:
            self.last_email_id = max(e["id"] for e in raw_emails)
        if raw_messages:
            self.last_message_id = max(m["id"] for m in raw_messages)
        
        # 통합 및 정렬
        all_messages = emails + messages
        
        # msg_id 기준 중복 제거 (TO/CC 중복 수신 처리) - 성능 측정
        start_time = time.time()
        seen_msg_ids = set()
        unique_messages = []
        for msg in all_messages:
            msg_id = msg.get("msg_id")
            if msg_id and msg_id not in seen_msg_ids:
                seen_msg_ids.add(msg_id)
                unique_messages.append(msg)
            elif not msg_id:
                # msg_id가 없는 경우는 그대로 추가
                unique_messages.append(msg)
        
        dedup_time = time.time() - start_time
        
        if len(all_messages) != len(unique_messages):
            logger.info(
                f"🔍 중복 메시지 제거: {len(all_messages)}개 → {len(unique_messages)}개 "
                f"({len(all_messages) - len(unique_messages)}개 중복) - {dedup_time:.2f}초"
            )
        
        all_messages = unique_messages

        # 시뮬레이션 시간 메타데이터 주입
        self._annotate_simulation_timestamps(all_messages)
        
        # 정렬 - 성능 측정
        start_time = time.time()
        all_messages.sort(key=lambda m: m["date"])
        sort_time = time.time() - start_time
        logger.info(f"⏱️ 정렬 시간: {sort_time:.2f}초 ({len(all_messages)}개)")
        
        # 시간 범위 필터링 적용 (옵션)
        if time_range:
            all_messages = self._apply_time_filter(all_messages, time_range)
            logger.info(f"⏰ 시간 필터링 적용: {time_range['start']} ~ {time_range['end']}")
        
        logger.info(
            f"메시지 수집 완료: 이메일 {len(emails)}개, 채팅 {len(messages)}개 "
            f"(last_email_id={self.last_email_id}, last_message_id={self.last_message_id})"
        )
        
        return all_messages
    
    async def _collect_parallel(
        self, 
        mailbox: str, 
        handle: str, 
        since_email_id: Optional[int], 
        since_message_id: Optional[int]
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        병렬로 이메일과 메시지 수집
        
        Args:
            mailbox: 메일박스 주소
            handle: 채팅 핸들
            since_email_id: 마지막 이메일 ID
            since_message_id: 마지막 메시지 ID
        
        Returns:
            (이메일 리스트, 메시지 리스트) 튜플
        """
        # 비동기 태스크 생성
        email_task = asyncio.to_thread(
            self.client.get_emails, mailbox, since_id=since_email_id
        )
        message_task = asyncio.to_thread(
            self.client.get_messages, handle, since_id=since_message_id
        )
        
        # 병렬 실행
        raw_emails, raw_messages = await asyncio.gather(
            email_task, message_task, return_exceptions=False
        )
        
        return raw_emails, raw_messages
    
    async def collect_new_data_batch(self) -> Dict[str, Any]:
        """
        병렬로 새 데이터 수집 (증분 수집 전용)
        
        이 메서드는 PollingWorker에서 사용하기 위한 최적화된 배치 수집 메서드입니다.
        이메일과 메시지를 병렬로 조회하여 성능을 향상시킵니다.
        
        Returns:
            Dict[str, Any]: 수집 결과
                - emails: 새 이메일 리스트 (내부 포맷)
                - messages: 새 채팅 메시지 리스트 (내부 포맷)
                - raw_emails: 원본 이메일 리스트
                - raw_messages: 원본 메시지 리스트
                - success: 성공 여부
                - error: 오류 메시지 (실패 시)
        
        Example:
            >>> result = await data_source.collect_new_data_batch()
            >>> if result["success"]:
            >>>     print(f"새 이메일: {len(result['emails'])}개")
        """
        mailbox = self.selected_persona.get("email_address")
        handle = (self.selected_persona.get("chat_handle") or "").strip()
        
        if not mailbox or not handle:
            return {
                "emails": [],
                "messages": [],
                "raw_emails": [],
                "raw_messages": [],
                "success": False,
                "error": "선택된 페르소나에 email_address 또는 chat_handle이 없습니다"
            }
        
        try:
            # 병렬 수집
            raw_emails, raw_messages = await self._collect_parallel(
                mailbox, handle.lower(), self.last_email_id, self.last_message_id
            )
            
            # 데이터 변환
            emails = [
                convert_email_to_internal_format(e, self.persona_by_email, mailbox)
                for e in raw_emails
            ]
            messages = [
                convert_message_to_internal_format(
                    m,
                    self.persona_by_handle,
                    selected_persona_handle=handle
                )
                for m in raw_messages
            ]
            
            # msg_id 기준 중복 제거 (TO/CC 중복 수신 처리)
            seen_msg_ids = set()
            unique_emails = []
            for email in emails:
                msg_id = email.get("msg_id")
                if msg_id and msg_id not in seen_msg_ids:
                    seen_msg_ids.add(msg_id)
                    unique_emails.append(email)
                elif not msg_id:
                    unique_emails.append(email)
            
            if len(emails) != len(unique_emails):
                logger.info(
                    f"🔍 중복 이메일 제거: {len(emails)}개 → {len(unique_emails)}개 "
                    f"({len(emails) - len(unique_emails)}개 중복)"
                )
            
            emails = unique_emails
            
            # last_id 업데이트
            if raw_emails:
                self.last_email_id = max(e["id"] for e in raw_emails)
            if raw_messages:
                self.last_message_id = max(m["id"] for m in raw_messages)

            self._annotate_simulation_timestamps(emails)
            self._annotate_simulation_timestamps(messages)
            
            return {
                "emails": emails,
                "messages": messages,
                "raw_emails": raw_emails,
                "raw_messages": raw_messages,
                "success": True,
                "error": None
            }
            
        except Exception as e:
            logger.error(f"배치 수집 실패: {e}")
            return {
                "emails": [],
                "messages": [],
                "raw_emails": [],
                "raw_messages": [],
                "success": False,
                "error": str(e)
            }
    
    def get_personas(self) -> List[Dict[str, Any]]:
        """페르소나 목록 반환"""
        return self.personas
    
    def get_source_type(self) -> str:
        """소스 타입 반환"""
        return "virtualoffice"
    
    def set_selected_persona(self, persona: Dict[str, Any]) -> None:
        """
        선택된 페르소나 변경
        
        Args:
            persona: 새로운 페르소나 정보
        """
        self.selected_persona = persona
        # 증분 수집 ID 리셋 (새 페르소나로 전환 시 처음부터 수집)
        self.last_email_id = 0
        self.last_message_id = 0
        logger.info(f"페르소나 변경: {persona.get('name', 'Unknown')}")
    
    def get_selected_persona(self) -> Dict[str, Any]:
        """현재 선택된 페르소나 반환"""
        return self.selected_persona
    
    def reset_incremental_ids(self) -> None:
        """증분 수집 ID 리셋 (전체 재수집 시 사용)"""
        self.last_email_id = 0
        self.last_message_id = 0
        logger.info("증분 수집 ID 리셋")
    
    def cleanup_old_messages(self, max_count: Optional[int] = None) -> int:
        """
        오래된 메시지 정리
        
        메모리 사용량을 관리하기 위해 오래된 메시지를 삭제합니다.
        날짜 기준으로 정렬하여 최신 메시지만 유지합니다.
        
        Args:
            max_count: 유지할 최대 메시지 수 (기본값: MAX_MESSAGES)
        
        Returns:
            int: 삭제된 메시지 수
        
        Example:
            >>> deleted = data_source.cleanup_old_messages(5000)
            >>> print(f"{deleted}개 메시지 삭제됨")
        """
        max_count = max_count or self.MAX_MESSAGES
        
        if len(self.cached_messages) <= max_count:
            return 0
        
        # 날짜 기준 정렬 (최신순)
        self.cached_messages.sort(key=lambda m: m.get("date", ""), reverse=True)
        
        # 오래된 메시지 삭제
        deleted_count = len(self.cached_messages) - max_count
        self.cached_messages = self.cached_messages[:max_count]
        
        logger.info(
            f"메시지 정리 완료: {deleted_count}개 삭제, "
            f"{len(self.cached_messages)}개 유지"
        )
        
        return deleted_count
    
    def add_messages_to_cache(self, messages: List[Dict[str, Any]]) -> None:
        """
        메시지를 캐시에 추가하고 필요시 자동 정리
        
        Args:
            messages: 추가할 메시지 리스트
        """
        self.cached_messages.extend(messages)
        
        # 임계값 초과 시 자동 정리
        if len(self.cached_messages) > self.CLEANUP_THRESHOLD:
            logger.warning(
                f"메시지 캐시 임계값 초과: {len(self.cached_messages)}개 "
                f"(임계값: {self.CLEANUP_THRESHOLD})"
            )
            self.cleanup_old_messages()
    
    def get_cached_messages(self) -> List[Dict[str, Any]]:
        """
        캐시된 메시지 반환
        
        Returns:
            List[Dict[str, Any]]: 캐시된 메시지 리스트
        """
        return self.cached_messages.copy()
    
    def clear_cache(self) -> None:
        """
        메시지 캐시 완전 삭제
        
        Example:
            >>> data_source.clear_cache()
        """
        count = len(self.cached_messages)
        self.cached_messages.clear()
        logger.info(f"메시지 캐시 삭제: {count}개")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        캐시 통계 정보 반환
        
        Returns:
            Dict[str, Any]: 캐시 통계
                - total_messages: 총 메시지 수
                - max_messages: 최대 메시지 수
                - cleanup_threshold: 정리 임계값
                - usage_percent: 사용률 (%)
                - needs_cleanup: 정리 필요 여부
        
        Example:
            >>> stats = data_source.get_cache_stats()
            >>> print(f"사용률: {stats['usage_percent']:.1f}%")
        """
        total = len(self.cached_messages)
        usage_percent = (total / self.MAX_MESSAGES) * 100 if self.MAX_MESSAGES > 0 else 0
        
        return {
            "total_messages": total,
            "max_messages": self.MAX_MESSAGES,
            "cleanup_threshold": self.CLEANUP_THRESHOLD,
            "usage_percent": usage_percent,
            "needs_cleanup": total > self.CLEANUP_THRESHOLD
        }
    
    def get_simulation_status_cached(self, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """
        시뮬레이션 상태 조회 (캐싱 적용)
        
        TTL(Time To Live) 기반 캐싱을 사용하여 불필요한 API 호출을 줄입니다.
        기본 TTL은 2초입니다.
        
        Args:
            force_refresh: True면 캐시 무시하고 강제 갱신
        
        Returns:
            Optional[Dict[str, Any]]: 시뮬레이션 상태 또는 None (오류 시)
        
        Example:
            >>> status = data_source.get_simulation_status_cached()
            >>> if status:
            >>>     print(f"현재 틱: {status['current_tick']}")
        """
        current_time = time.time()
        
        # 캐시 유효성 확인
        if not force_refresh and self._cached_sim_status:
            cache_age = current_time - self._sim_status_cache_time
            if cache_age < self._sim_status_cache_ttl:
                logger.debug(f"시뮬레이션 상태 캐시 사용 (age: {cache_age:.2f}초)")
                return self._cached_sim_status
        
        # 캐시 만료 또는 강제 갱신
        try:
            status = self.client.get_simulation_status()
            self._cached_sim_status = status.to_dict() if hasattr(status, 'to_dict') else status
            self._sim_status_cache_time = current_time
            logger.debug("시뮬레이션 상태 캐시 갱신")
            return self._cached_sim_status
        except Exception as e:
            logger.error(f"시뮬레이션 상태 조회 실패: {e}")
            # 오류 시 기존 캐시 반환 (있으면)
            return self._cached_sim_status
    
    def invalidate_sim_status_cache(self) -> None:
        """
        시뮬레이션 상태 캐시 무효화
        
        Example:
            >>> data_source.invalidate_sim_status_cache()
        """
        self._cached_sim_status = None
        self._sim_status_cache_time = 0
        logger.debug("시뮬레이션 상태 캐시 무효화")
    
    def set_sim_status_cache_ttl(self, ttl: float) -> None:
        """
        시뮬레이션 상태 캐시 TTL 설정
        
        Args:
            ttl: TTL (초)
        
        Example:
            >>> data_source.set_sim_status_cache_ttl(5.0)  # 5초로 변경
        """
        if ttl <= 0:
            logger.warning(f"잘못된 TTL: {ttl}초. 변경하지 않습니다.")
            return
        
        old_ttl = self._sim_status_cache_ttl
        self._sim_status_cache_ttl = ttl
        logger.info(f"시뮬레이션 상태 캐시 TTL 변경: {old_ttl}초 → {ttl}초")
    
    def refresh_persona_cache(self) -> bool:
        """
        페르소나 캐시 강제 갱신
        
        Returns:
            bool: 성공 여부
        
        Example:
            >>> if data_source.refresh_persona_cache():
            >>>     print("페르소나 캐시 갱신 성공")
        """
        try:
            self._load_personas()
            return True
        except Exception as e:
            logger.error(f"페르소나 캐시 갱신 실패: {e}")
            return False
    def _apply_time_filter(self, messages: List[Dict[str, Any]], time_range: Dict[str, Any]) -> List[Dict[str, Any]]:
        """메시지 리스트에 시간 범위 필터링 적용
        
        Args:
            messages: 필터링할 메시지 리스트
            time_range: 시간 범위 {"start": datetime, "end": datetime}
            
        Returns:
            필터링된 메시지 리스트
        """
        try:
            start_time = time_range.get("start")
            end_time = time_range.get("end")
            
            if not start_time or not end_time:
                logger.warning("시간 범위가 불완전합니다")
                return messages
            
            # UTC로 변환
            if start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=timezone.utc)
            else:
                start_time = start_time.astimezone(timezone.utc)
                
            if end_time.tzinfo is None:
                end_time = end_time.replace(tzinfo=timezone.utc)
            else:
                end_time = end_time.astimezone(timezone.utc)
            
            filtered_messages = []
            
            for message in messages:
                message_time = self._parse_message_time(message)
                if message_time and start_time <= message_time <= end_time:
                    filtered_messages.append(message)
            
            original_count = len(messages)
            filtered_count = len(filtered_messages)
            
            logger.info(f"⏰ 시간 필터링 결과: {original_count}개 → {filtered_count}개")
            
            return filtered_messages
            
        except Exception as e:
            logger.error(f"시간 필터링 오류: {e}")
            return messages  # 오류 시 원본 반환
    
    def _parse_message_time(self, message: Dict[str, Any]) -> Optional[datetime]:
        """메시지에서 시간 정보 파싱
        
        Args:
            message: 메시지 딕셔너리
            
        Returns:
            파싱된 datetime (UTC) 또는 None
        """
        try:
            try:
                import dateutil.parser
            except ImportError:
                logger.warning("python-dateutil 패키지가 설치되지 않음. 기본 datetime 파싱만 사용")
                dateutil = None
            
            # 다양한 시간 필드 시도
            time_fields = ['date', 'timestamp', 'sent_at', 'created_at']
            
            for field in time_fields:
                if field in message and message[field]:
                    time_value = message[field]
                    
                    if isinstance(time_value, datetime):
                        # 이미 datetime 객체
                        if time_value.tzinfo is None:
                            return time_value.replace(tzinfo=timezone.utc)
                        return time_value.astimezone(timezone.utc)
                    
                    elif isinstance(time_value, str):
                        # 문자열 파싱
                        try:
                            if dateutil:
                                dt = dateutil.parser.parse(time_value)
                            else:
                                # 기본 ISO 형식만 지원
                                dt = datetime.fromisoformat(time_value.replace('Z', '+00:00'))
                            
                            if dt.tzinfo is None:
                                dt = dt.replace(tzinfo=timezone.utc)
                            return dt.astimezone(timezone.utc)
                        except Exception:
                            continue
                    
                    elif isinstance(time_value, (int, float)):
                        # 타임스탬프
                        return datetime.fromtimestamp(time_value, tz=timezone.utc)
            
            return None
            
        except Exception as e:
            logger.debug(f"메시지 시간 파싱 오류: {e}")
            return None
