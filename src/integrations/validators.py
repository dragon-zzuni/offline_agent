# -*- coding: utf-8 -*-
"""
Data Validators
VirtualOffice API 응답 데이터 검증
"""

import logging
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """데이터 검증 오류"""
    pass


def validate_email_response(
    emails: List[Dict[str, Any]],
    strict: bool = False
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """이메일 응답 데이터 검증
    
    Args:
        emails: 이메일 데이터 리스트
        strict: 엄격 모드 (True면 필수 필드 누락 시 예외 발생)
    
    Returns:
        Tuple[List[Dict[str, Any]], List[str]]: (유효한 이메일 리스트, 오류 메시지 리스트)
    
    Raises:
        ValidationError: strict=True이고 필수 필드 누락 시
    
    Example:
        >>> emails = [{"id": 1, "sender": "test@example.com", ...}]
        >>> valid_emails, errors = validate_email_response(emails)
    """
    if not isinstance(emails, list):
        error_msg = f"이메일 응답이 리스트가 아닙니다: {type(emails)}"
        logger.error(error_msg)
        if strict:
            raise ValidationError(error_msg)
        return [], [error_msg]
    
    valid_emails = []
    errors = []
    
    # 필수 필드
    required_fields = ["id", "sender", "subject", "body", "sent_at"]
    
    for idx, email in enumerate(emails):
        if not isinstance(email, dict):
            error_msg = f"이메일 #{idx}가 딕셔너리가 아닙니다: {type(email)}"
            logger.warning(error_msg)
            errors.append(error_msg)
            continue
        
        # 필수 필드 확인
        missing_fields = [f for f in required_fields if f not in email]
        
        if missing_fields:
            error_msg = (
                f"이메일 ID {email.get('id', 'unknown')}에 "
                f"필수 필드 누락: {missing_fields}"
            )
            logger.warning(error_msg)
            errors.append(error_msg)
            
            if strict:
                raise ValidationError(error_msg)
            
            # 엄격 모드가 아니면 건너뛰기
            continue
        
        # 필드 타입 검증
        if not isinstance(email.get("id"), int):
            error_msg = f"이메일 ID가 정수가 아닙니다: {email.get('id')}"
            logger.warning(error_msg)
            errors.append(error_msg)
            if strict:
                raise ValidationError(error_msg)
            continue
        
        if not isinstance(email.get("sender"), str):
            error_msg = f"발신자가 문자열이 아닙니다: {email.get('sender')}"
            logger.warning(error_msg)
            errors.append(error_msg)
            if strict:
                raise ValidationError(error_msg)
            continue
        
        # 유효한 이메일 추가
        valid_emails.append(email)
    
    if errors:
        logger.info(
            f"이메일 검증 완료: {len(valid_emails)}개 유효, "
            f"{len(errors)}개 오류"
        )
    
    return valid_emails, errors


def validate_message_response(
    messages: List[Dict[str, Any]],
    strict: bool = False
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """메시지 응답 데이터 검증
    
    Args:
        messages: 메시지 데이터 리스트
        strict: 엄격 모드 (True면 필수 필드 누락 시 예외 발생)
    
    Returns:
        Tuple[List[Dict[str, Any]], List[str]]: (유효한 메시지 리스트, 오류 메시지 리스트)
    
    Raises:
        ValidationError: strict=True이고 필수 필드 누락 시
    
    Example:
        >>> messages = [{"id": 1, "sender": "pm", "body": "Hello", ...}]
        >>> valid_messages, errors = validate_message_response(messages)
    """
    if not isinstance(messages, list):
        error_msg = f"메시지 응답이 리스트가 아닙니다: {type(messages)}"
        logger.error(error_msg)
        if strict:
            raise ValidationError(error_msg)
        return [], [error_msg]
    
    valid_messages = []
    errors = []
    
    # 필수 필드
    required_fields = ["id", "room_slug", "sender", "body", "sent_at"]
    
    for idx, message in enumerate(messages):
        if not isinstance(message, dict):
            error_msg = f"메시지 #{idx}가 딕셔너리가 아닙니다: {type(message)}"
            logger.warning(error_msg)
            errors.append(error_msg)
            continue
        
        # 필수 필드 확인
        missing_fields = [f for f in required_fields if f not in message]
        
        if missing_fields:
            error_msg = (
                f"메시지 ID {message.get('id', 'unknown')}에 "
                f"필수 필드 누락: {missing_fields}"
            )
            logger.warning(error_msg)
            errors.append(error_msg)
            
            if strict:
                raise ValidationError(error_msg)
            
            # 엄격 모드가 아니면 건너뛰기
            continue
        
        # 필드 타입 검증
        if not isinstance(message.get("id"), int):
            error_msg = f"메시지 ID가 정수가 아닙니다: {message.get('id')}"
            logger.warning(error_msg)
            errors.append(error_msg)
            if strict:
                raise ValidationError(error_msg)
            continue
        
        if not isinstance(message.get("sender"), str):
            error_msg = f"발신자가 문자열이 아닙니다: {message.get('sender')}"
            logger.warning(error_msg)
            errors.append(error_msg)
            if strict:
                raise ValidationError(error_msg)
            continue
        
        # 유효한 메시지 추가
        valid_messages.append(message)
    
    if errors:
        logger.info(
            f"메시지 검증 완료: {len(valid_messages)}개 유효, "
            f"{len(errors)}개 오류"
        )
    
    return valid_messages, errors


def validate_simulation_status(
    status: Dict[str, Any],
    strict: bool = False
) -> Tuple[bool, Optional[str]]:
    """시뮬레이션 상태 데이터 검증
    
    Args:
        status: 시뮬레이션 상태 딕셔너리
        strict: 엄격 모드
    
    Returns:
        Tuple[bool, Optional[str]]: (유효 여부, 오류 메시지)
    
    Example:
        >>> status = {"current_tick": 100, "sim_time": "2025-01-15T10:00:00Z", ...}
        >>> is_valid, error = validate_simulation_status(status)
    """
    if not isinstance(status, dict):
        error_msg = f"시뮬레이션 상태가 딕셔너리가 아닙니다: {type(status)}"
        logger.error(error_msg)
        return False, error_msg
    
    # 필수 필드
    required_fields = ["current_tick", "sim_time", "is_running", "auto_tick"]
    
    missing_fields = [f for f in required_fields if f not in status]
    
    if missing_fields:
        error_msg = f"시뮬레이션 상태에 필수 필드 누락: {missing_fields}"
        logger.error(error_msg)
        return False, error_msg
    
    # 필드 타입 검증
    if not isinstance(status.get("current_tick"), int):
        error_msg = f"current_tick이 정수가 아닙니다: {status.get('current_tick')}"
        logger.error(error_msg)
        return False, error_msg
    
    if not isinstance(status.get("sim_time"), str):
        error_msg = f"sim_time이 문자열이 아닙니다: {status.get('sim_time')}"
        logger.error(error_msg)
        return False, error_msg
    
    if not isinstance(status.get("is_running"), bool):
        error_msg = f"is_running이 불리언이 아닙니다: {status.get('is_running')}"
        logger.error(error_msg)
        return False, error_msg
    
    if not isinstance(status.get("auto_tick"), bool):
        error_msg = f"auto_tick이 불리언이 아닙니다: {status.get('auto_tick')}"
        logger.error(error_msg)
        return False, error_msg
    
    return True, None


def validate_persona_list(
    personas: List[Dict[str, Any]],
    strict: bool = False
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """페르소나 리스트 검증
    
    Args:
        personas: 페르소나 데이터 리스트
        strict: 엄격 모드
    
    Returns:
        Tuple[List[Dict[str, Any]], List[str]]: (유효한 페르소나 리스트, 오류 메시지 리스트)
    
    Example:
        >>> personas = [{"id": 1, "name": "이민주", "email_address": "pm@example.com", ...}]
        >>> valid_personas, errors = validate_persona_list(personas)
    """
    if not isinstance(personas, list):
        error_msg = f"페르소나 응답이 리스트가 아닙니다: {type(personas)}"
        logger.error(error_msg)
        if strict:
            raise ValidationError(error_msg)
        return [], [error_msg]
    
    valid_personas = []
    errors = []
    
    # 필수 필드
    required_fields = ["id", "name", "email_address", "chat_handle"]
    
    for idx, persona in enumerate(personas):
        if not isinstance(persona, dict):
            error_msg = f"페르소나 #{idx}가 딕셔너리가 아닙니다: {type(persona)}"
            logger.warning(error_msg)
            errors.append(error_msg)
            continue
        
        # 필수 필드 확인
        missing_fields = [f for f in required_fields if f not in persona]
        
        if missing_fields:
            error_msg = (
                f"페르소나 ID {persona.get('id', 'unknown')}에 "
                f"필수 필드 누락: {missing_fields}"
            )
            logger.warning(error_msg)
            errors.append(error_msg)
            
            if strict:
                raise ValidationError(error_msg)
            
            continue
        
        # 유효한 페르소나 추가
        valid_personas.append(persona)
    
    if errors:
        logger.info(
            f"페르소나 검증 완료: {len(valid_personas)}개 유효, "
            f"{len(errors)}개 오류"
        )
    
    return valid_personas, errors
