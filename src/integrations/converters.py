# -*- coding: utf-8 -*-
"""
VirtualOffice API 응답을 offline_agent 내부 포맷으로 변환하는 함수들
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone


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


def convert_email_to_internal_format(
    email: Dict[str, Any],
    persona_map: Dict[str, Dict[str, Any]],
    selected_persona_email: Optional[str] = None
) -> Dict[str, Any]:
    """Email API 응답을 offline_agent 내부 포맷으로 변환
    
    Args:
        email: virtualoffice API 응답 (simulation_output과 동일 형식)
            {
                "id": 1079,
                "sender": "dev.1@multiproject.dev",
                "to": ["pm.1@multiproject.dev"],
                "cc": ["devops.1@multiproject.dev"],
                "bcc": [],
                "subject": "업데이트: 이준호",
                "body": "오늘 작업 결과 | ...",
                "thread_id": null,
                "sent_at": "2025-11-26T06:29:27.073636Z"
            }
        persona_map: {email_address -> persona_info}
        selected_persona_email: 선택된 페르소나의 이메일 주소 (recipient_type 판별용)
    
    Returns:
        offline_agent 내부 포맷 (main.py의 _build_email_messages와 동일)
        {
            "msg_id": "email_1079",
            "sender": "이준호",  # persona의 name
            "sender_email": "dev.1@multiproject.dev",
            "sender_handle": "dev",  # persona의 chat_handle
            "subject": "업데이트: 이준호",
            "body": "오늘 작업 결과 | ...",
            "content": "오늘 작업 결과 | ...",
            "date": "2025-11-26T06:29:27.073636Z",
            "type": "email",
            "platform": "email",
            "mailbox": "pm.1@multiproject.dev",  # 선택된 페르소나의 메일박스
            "recipients": ["pm.1@multiproject.dev"],
            "cc": ["devops.1@multiproject.dev"],
            "bcc": [],
            "thread_id": null,
            "recipient_type": "to",  # PM이 to/cc/bcc 중 어디에 있는지
            "is_read": False,
            "metadata": {
                "mailbox": "pm.1@multiproject.dev",
                "email_id": 1079,
                "persona": {...}  # sender의 persona 정보
            }
        }
    """
    sender_email = (email.get("sender") or "").strip()
    sender_persona = persona_map.get(sender_email.lower(), {})
    sender_name = sender_persona.get("name", sender_email)
    
    # recipient_type 판별 (선택된 페르소나가 to/cc/bcc 중 어디에 있는지)
    recipient_type = "to"  # 기본값
    if selected_persona_email:
        selected_email_lower = selected_persona_email.lower()
        to_list = [r.lower() for r in (email.get("to") or [])]
        cc_list = [r.lower() for r in (email.get("cc") or [])]
        bcc_list = [r.lower() for r in (email.get("bcc") or [])]
        
        if selected_email_lower in to_list:
            recipient_type = "to"
        elif selected_email_lower in cc_list:
            recipient_type = "cc"
        elif selected_email_lower in bcc_list:
            recipient_type = "bcc"
    
    # ISO 날짜 표준화
    iso_date = _to_aware_iso(email.get("sent_at"))
    
    # 내부 포맷으로 변환
    return {
        "msg_id": f"email_{email.get('id')}",
        "sender": sender_name,
        "sender_email": sender_email or None,
        "sender_handle": sender_persona.get("chat_handle"),
        "subject": email.get("subject") or "",
        "body": email.get("body") or "",
        "content": email.get("body") or "",
        "date": iso_date,
        "type": "email",
        "platform": "email",
        "mailbox": selected_persona_email or sender_email,
        "recipients": email.get("to") or [],
        "cc": email.get("cc") or [],
        "bcc": email.get("bcc") or [],
        "thread_id": email.get("thread_id"),
        "recipient_type": recipient_type,
        "is_read": False,
        "metadata": {
            "mailbox": selected_persona_email or sender_email,
            "email_id": email.get("id"),
            "persona": sender_persona,
        }
    }


def convert_message_to_internal_format(
    message: Dict[str, Any],
    persona_map: Dict[str, Dict[str, Any]],
    selected_persona_handle: Optional[str] = None
) -> Dict[str, Any]:
    """Chat API 응답을 offline_agent 내부 포맷으로 변환
    
    Args:
        message: virtualoffice API 응답 (simulation_output과 동일 형식)
            {
                "id": 26,
                "room_slug": "dm:designer:dev",
                "sender": "designer",
                "body": "이준호님, 09:00 - 09:15 진행 중입니다.",
                "sent_at": "2025-10-20T22:02:27.073636Z"
            }
        persona_map: {chat_handle -> persona_info}
        selected_persona_handle: 선택된 페르소나의 chat_handle (필터링용)
    
    Returns:
        offline_agent 내부 포맷 (main.py의 _build_chat_messages와 동일)
        {
            "msg_id": "chat_dm:designer:dev_26",
            "sender": "김민준",  # persona의 name
            "sender_handle": "designer",
            "sender_email": "designer.1@multiproject.dev",  # persona의 email_address
            "subject": "",
            "body": "이준호님, 09:00 - 09:15 진행 중입니다.",
            "content": "이준호님, 09:00 - 09:15 진행 중입니다.",
            "date": "2025-10-20T22:02:27.073636Z",
            "type": "messenger",
            "platform": "dm:designer:dev",  # room_slug
            "room_slug": "dm:designer:dev",
            "recipient_type": "to",
            "is_read": False,
            "metadata": {
                "chat_id": 26,
                "raw_sender": "designer",
                "persona": {...},  # sender의 persona 정보
                "room_slug": "dm:designer:dev"
            }
        }
    """
    sender_handle = (message.get("sender") or "").strip()
    sender_persona = persona_map.get(sender_handle.lower(), {})
    sender_name = sender_persona.get("name", sender_handle)
    
    room_slug = message.get("room_slug") or ""
    
    # ISO 날짜 표준화
    iso_date = _to_aware_iso(message.get("sent_at"))
    
    # 내부 포맷으로 변환
    return {
        "msg_id": f"chat_{room_slug}_{message.get('id')}",
        "sender": sender_name or sender_handle or "Unknown",
        "sender_handle": sender_handle or None,
        "sender_email": sender_persona.get("email_address"),
        "subject": "",
        "body": message.get("body") or "",
        "content": message.get("body") or "",
        "date": iso_date,
        "type": "messenger",
        "platform": room_slug or "chat",
        "room_slug": room_slug,
        "recipient_type": "to",
        "is_read": False,
        "metadata": {
            "chat_id": message.get("id"),
            "raw_sender": sender_handle,
            "persona": sender_persona,
            "room_slug": room_slug,
        }
    }


def build_persona_maps(personas: List[Dict[str, Any]]) -> tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """페르소나 목록에서 email_address와 chat_handle 매핑 딕셔너리 생성
    
    Args:
        personas: 페르소나 목록
            [
                {
                    "id": 1,
                    "name": "이민주",
                    "email_address": "pm.1@multiproject.dev",
                    "chat_handle": "pm",
                    ...
                },
                ...
            ]
    
    Returns:
        (persona_by_email, persona_by_handle) 튜플
        - persona_by_email: {email_address -> persona_info}
        - persona_by_handle: {chat_handle -> persona_info}
    """
    persona_by_email = {}
    persona_by_handle = {}
    
    for persona in personas:
        if not isinstance(persona, dict):
            continue
        
        # email_address 매핑
        email_address = persona.get("email_address")
        if email_address:
            persona_by_email[email_address.lower()] = persona
        
        # chat_handle 매핑
        chat_handle = persona.get("chat_handle")
        if chat_handle:
            persona_by_handle[chat_handle.lower()] = persona
    
    return persona_by_email, persona_by_handle
