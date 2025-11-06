# -*- coding: utf-8 -*-
"""
JSON Data Source
로컬 JSON 파일 기반 데이터 소스
"""
import json
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

from data_sources.manager import DataSource

logger = logging.getLogger(__name__)


def _to_aware_iso(ts: str | None) -> str:
    """문자열 타임스탬프를 UTC aware ISO8601로 표준화."""
    if not ts:
        return datetime.now(timezone.utc).isoformat()
    s = ts.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)  # tz 포함/미포함 모두 허용
    except Exception:
        # YYYY-MM-DD HH:MM:SS 같은 포맷 처리
        try:
            dt = datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
        except Exception:
            return datetime.now(timezone.utc).isoformat()

    if dt.tzinfo is None:
        # naive면 UTC로 간주
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        # 타임존 있으면 UTC로 변환
        dt = dt.astimezone(timezone.utc)
    return dt.isoformat()


def _sort_key(msg: dict) -> datetime:
    """날짜 키를 UTC aware datetime으로 반환(정렬용)."""
    try:
        return datetime.fromisoformat(msg["date"])
    except Exception:
        try:
            return datetime.fromisoformat(_to_aware_iso(msg.get("date")))
        except Exception:
            return datetime.min.replace(tzinfo=timezone.utc)


class JSONDataSource(DataSource):
    """JSON 파일 기반 데이터 소스"""
    
    def __init__(self, dataset_root: Path | str):
        """
        Args:
            dataset_root: 데이터셋 루트 디렉토리 경로
        """
        self.dataset_root = Path(dataset_root)
        self.personas: List[Dict[str, Any]] = []
        self.persona_by_email: Dict[str, Dict[str, Any]] = {}
        self.persona_by_handle: Dict[str, Dict[str, Any]] = {}
        
        # 초기화 시 페르소나 로드
        self._load_personas()
        
        logger.info(f"JSONDataSource 초기화: {self.dataset_root}")
    
    def _load_json(self, filename: str) -> Any:
        """JSON 파일 로드"""
        path = self.dataset_root / filename
        if not path.exists():
            raise FileNotFoundError(f"데이터 파일을 찾을 수 없습니다: {path}")
        with path.open("r", encoding="utf-8") as fp:
            return json.load(fp)
    
    def _load_personas(self) -> None:
        """페르소나 정보 로드"""
        try:
            personas_payload = self._load_json("team_personas.json")
        except FileNotFoundError as exc:
            logger.warning(f"페르소나 파일 없음: {exc}")
            personas_payload = []
        except json.JSONDecodeError as exc:
            logger.error(f"페르소나 JSON 파싱 실패: {exc}")
            personas_payload = []
        
        if isinstance(personas_payload, list):
            self.personas = personas_payload
        else:
            self.personas = []
        
        self.persona_by_email = {
            (p.get("email_address") or "").lower(): p
            for p in self.personas
            if p.get("email_address")
        }
        self.persona_by_handle = {
            (p.get("chat_handle") or "").lower(): p
            for p in self.personas
            if p.get("chat_handle")
        }
        
        # PM 페르소나를 user_profile로 설정
        self.user_profile = next(
            (p for p in self.personas if (p.get("chat_handle") or "").lower() == "pm"),
            None,
        )
        
        logger.info(f"페르소나 로드 완료: {len(self.personas)}명")
    
    def _build_chat_messages(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """채팅 메시지 빌드 (SmartAssistant._build_chat_messages와 동일)"""
        rooms = payload.get("rooms", {}) if isinstance(payload, dict) else {}
        messages: List[Dict[str, Any]] = []
        
        for room_slug, entries in rooms.items():
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                
                sender_handle = (entry.get("sender") or "").strip()
                persona = self.persona_by_handle.get(sender_handle.lower())
                sender_name = persona.get("name") if persona else sender_handle
                iso_date = _to_aware_iso(entry.get("sent_at"))
                
                msg = {
                    "msg_id": f"chat_{room_slug}_{entry.get('id')}",
                    "sender": sender_name or sender_handle or "Unknown",
                    "sender_handle": sender_handle or None,
                    "sender_email": (persona or {}).get("email_address"),
                    "subject": "",
                    "body": entry.get("body") or "",
                    "content": entry.get("body") or "",
                    "date": iso_date,
                    "type": "messenger",
                    "platform": room_slug or "chat",
                    "room_slug": room_slug,
                    "is_read": True,
                    "metadata": {
                        "chat_id": entry.get("id"),
                        "raw_sender": sender_handle,
                        "persona": persona,
                        "room_slug": room_slug,
                    },
                }
                messages.append(msg)
        
        messages.sort(key=_sort_key)
        return messages
    
    def _build_email_messages(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """이메일 메시지 빌드 (SmartAssistant._build_email_messages와 동일)"""
        mailboxes = payload.get("mailboxes", {}) if isinstance(payload, dict) else {}
        messages: List[Dict[str, Any]] = []
        
        for mailbox, entries in mailboxes.items():
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                
                sender_email = (entry.get("sender") or "").strip()
                persona = self.persona_by_email.get(sender_email.lower())
                sender_display = persona.get("name") if persona else sender_email or "Unknown"
                iso_date = _to_aware_iso(entry.get("sent_at"))
                body = entry.get("body") or ""
                
                msg = {
                    "msg_id": f"email_{entry.get('id')}_{sender_email or mailbox}",
                    "sender": sender_display,
                    "sender_email": sender_email or None,
                    "sender_handle": (persona or {}).get("chat_handle"),
                    "subject": entry.get("subject") or "",
                    "body": body,
                    "content": body,
                    "date": iso_date,
                    "type": "email",
                    "platform": "email",
                    "mailbox": mailbox,
                    "recipients": entry.get("to") or [],
                    "cc": entry.get("cc") or [],
                    "bcc": entry.get("bcc") or [],
                    "thread_id": entry.get("thread_id"),
                    "is_read": True,
                    "metadata": {
                        "mailbox": mailbox,
                        "email_id": entry.get("id"),
                        "persona": persona,
                    },
                }
                messages.append(msg)
        
        messages.sort(key=_sort_key)
        return messages
    
    async def collect_messages(self, options: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        JSON 파일에서 메시지 수집
        
        Args:
            options: 수집 옵션 (현재 미사용)
            
        Returns:
            메시지 리스트
        """
        logger.info(f"JSON 파일에서 메시지 수집: {self.dataset_root}")
        
        # 채팅 메시지 로드
        try:
            chat_payload = self._load_json("chat_communications.json")
        except FileNotFoundError as exc:
            logger.warning(f"채팅 파일 없음: {exc}")
            chat_payload = {}
        except json.JSONDecodeError as exc:
            logger.error(f"채팅 JSON 파싱 실패: {exc}")
            chat_payload = {}
        
        chat_messages = self._build_chat_messages(chat_payload)
        
        # 이메일 메시지 로드
        try:
            email_payload = self._load_json("email_communications.json")
        except FileNotFoundError as exc:
            logger.warning(f"이메일 파일 없음: {exc}")
            email_payload = {}
        except json.JSONDecodeError as exc:
            logger.error(f"이메일 JSON 파싱 실패: {exc}")
            email_payload = {}
        
        email_messages = self._build_email_messages(email_payload)
        
        # 통합 및 정렬
        all_messages = chat_messages + email_messages
        all_messages.sort(key=_sort_key)
        
        logger.info(f"메시지 수집 완료: 채팅 {len(chat_messages)}개, 이메일 {len(email_messages)}개")
        return all_messages
    
    def get_personas(self) -> List[Dict[str, Any]]:
        """페르소나 목록 반환"""
        return self.personas
    
    def get_source_type(self) -> str:
        """소스 타입 반환"""
        return "json"
