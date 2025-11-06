# -*- coding: utf-8 -*-
"""
시간 필터링 서비스

메시지, 이메일, TODO 등을 시간 범위에 따라 필터링하는 서비스입니다.
"""
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple, Any

logger = logging.getLogger(__name__)


class TimeFilterService:
    """시간 범위 기반 데이터 필터링 서비스"""
    
    def __init__(self):
        """TimeFilterService 초기화"""
        self.current_range: Optional[Tuple[datetime, datetime]] = None
        self.is_enabled = False
        logger.info("TimeFilterService 초기화 완료")
    
    def set_time_range(self, start: datetime, end: datetime) -> None:
        """시간 범위 설정
        
        Args:
            start: 시작 시간 (UTC aware datetime)
            end: 종료 시간 (UTC aware datetime)
        """
        self.current_range = (start, end)
        self.is_enabled = True
        
        start_str = start.strftime('%Y-%m-%d %H:%M:%S UTC')
        end_str = end.strftime('%Y-%m-%d %H:%M:%S UTC')
        logger.info(f"⏰ 시간 범위 설정: {start_str} ~ {end_str}")
    
    def clear_time_range(self) -> None:
        """시간 범위 필터링 해제"""
        self.current_range = None
        self.is_enabled = False
        logger.info("⏰ 시간 범위 필터링 해제")
    
    def filter_messages(self, messages: List[Dict]) -> List[Dict]:
        """메시지 리스트를 시간 범위로 필터링
        
        Args:
            messages: 필터링할 메시지 리스트
            
        Returns:
            필터링된 메시지 리스트
        """
        if not self.is_enabled or not self.current_range:
            return messages
        
        start_time, end_time = self.current_range
        filtered_messages = []
        
        for message in messages:
            message_time = self._extract_message_time(message)
            if message_time and self._is_in_range(message_time, start_time, end_time):
                filtered_messages.append(message)
        
        logger.info(f"📧 메시지 필터링: {len(messages)}개 → {len(filtered_messages)}개")
        
        # 디버깅: 처음 몇 개 메시지 샘플 확인
        if len(messages) > 0 and len(filtered_messages) == 0:
            logger.warning("⚠️ 모든 메시지가 필터링됨. 샘플 메시지 확인:")
            for i, msg in enumerate(messages[:3]):  # 처음 3개만 확인
                msg_time = self._extract_message_time(msg)
                logger.warning(f"샘플 {i+1}: msg_id={msg.get('msg_id')}, time={msg_time}, type={msg.get('type')}")
                if msg_time:
                    logger.warning(f"  시간 범위: {start_time} <= {msg_time} <= {end_time} = {start_time <= msg_time <= end_time}")
        return filtered_messages
    
    def filter_todos(self, todos: List[Dict]) -> List[Dict]:
        """TODO 리스트를 시간 범위로 필터링
        
        Args:
            todos: 필터링할 TODO 리스트
            
        Returns:
            필터링된 TODO 리스트
        """
        if not self.is_enabled or not self.current_range:
            return todos
        
        start_time, end_time = self.current_range
        filtered_todos = []
        
        for todo in todos:
            todo_time = self._extract_todo_time(todo)
            if todo_time and self._is_in_range(todo_time, start_time, end_time):
                filtered_todos.append(todo)
        
        logger.info(f"📋 TODO 필터링: {len(todos)}개 → {len(filtered_todos)}개")
        return filtered_todos
    
    def get_collection_params(self) -> Dict[str, Any]:
        """데이터 수집용 시간 범위 파라미터 반환
        
        VirtualOffice API 호출 시 사용할 시간 범위 파라미터를 반환합니다.
        
        Returns:
            시간 범위 파라미터 딕셔너리
        """
        if not self.is_enabled or not self.current_range:
            return {}
        
        start_time, end_time = self.current_range
        
        # ISO 8601 형식으로 변환 (API에서 사용)
        params = {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "time_filter_enabled": True
        }
        
        logger.debug(f"📡 수집 파라미터: {params}")
        return params
    
    def _extract_message_time(self, message: Dict) -> Optional[datetime]:
        """메시지에서 시간 정보 추출
        
        Args:
            message: 메시지 딕셔너리
            
        Returns:
            메시지 시간 (UTC aware datetime) 또는 None
        """
        try:
            # 다양한 시간 필드 시도
            time_fields = ['timestamp', 'sent_at', 'created_at', 'date', 'time']
            
            # 디버깅: 메시지 구조 로그
            msg_id = message.get('msg_id', 'unknown')
            msg_type = message.get('type', 'unknown')
            
            for field in time_fields:
                if field in message and message[field]:
                    time_value = message[field]
                    logger.debug(f"🔍 메시지 {msg_id} ({msg_type}): {field}={time_value} (type: {type(time_value)})")
                    parsed_time = self._parse_datetime(time_value)
                    if parsed_time:
                        logger.debug(f"✅ 파싱 성공: {parsed_time}")
                        return parsed_time
                    else:
                        logger.debug(f"❌ 파싱 실패: {time_value}")
            
            # 이메일의 경우 'sent_at' 필드 확인
            if message.get('type') == 'email' and 'sent_at' in message:
                time_value = message['sent_at']
                logger.debug(f"🔍 이메일 {msg_id}: sent_at={time_value}")
                return self._parse_datetime(time_value)
            
            # 채팅 메시지의 경우 'timestamp' 필드 확인
            if message.get('type') == 'chat' and 'timestamp' in message:
                time_value = message['timestamp']
                logger.debug(f"🔍 채팅 {msg_id}: timestamp={time_value}")
                return self._parse_datetime(time_value)
            
            # 사용 가능한 필드들 로그
            available_fields = list(message.keys())
            logger.debug(f"⚠️ 메시지 {msg_id} ({msg_type}) 시간 정보 없음. 사용 가능한 필드: {available_fields}")
            return None
            
        except Exception as e:
            logger.warning(f"메시지 시간 추출 오류: {e}")
            return None
    
    def _extract_todo_time(self, todo: Dict) -> Optional[datetime]:
        """TODO에서 시간 정보 추출
        
        Args:
            todo: TODO 딕셔너리
            
        Returns:
            TODO 생성 시간 (UTC aware datetime) 또는 None
        """
        try:
            # TODO 생성 시간 또는 관련 메시지 시간 사용
            time_fields = ['created_at', 'timestamp', 'due_date', 'source_timestamp']
            
            for field in time_fields:
                if field in todo and todo[field]:
                    return self._parse_datetime(todo[field])
            
            logger.debug(f"⚠️ TODO 시간 정보 없음: {todo.get('id', 'unknown')}")
            return None
            
        except Exception as e:
            logger.warning(f"TODO 시간 추출 오류: {e}")
            return None
    
    def _parse_datetime(self, time_value: Any) -> Optional[datetime]:
        """다양한 형식의 시간 값을 datetime으로 파싱
        
        Args:
            time_value: 시간 값 (문자열, datetime, 타임스탬프 등)
            
        Returns:
            파싱된 datetime (UTC aware) 또는 None
        """
        try:
            if isinstance(time_value, datetime):
                # 이미 datetime 객체인 경우
                if time_value.tzinfo is None:
                    # naive datetime을 UTC로 간주
                    return time_value.replace(tzinfo=timezone.utc)
                return time_value.astimezone(timezone.utc)
            
            elif isinstance(time_value, (int, float)):
                # 타임스탬프인 경우
                return datetime.fromtimestamp(time_value, tz=timezone.utc)
            
            elif isinstance(time_value, str):
                # 문자열인 경우 ISO 8601 형식으로 파싱 시도
                try:
                    # ISO 8601 형식 (예: "2024-10-28T10:30:00Z")
                    if 'T' in time_value:
                        if time_value.endswith('Z'):
                            time_value = time_value[:-1] + '+00:00'
                        dt = datetime.fromisoformat(time_value)
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        return dt.astimezone(timezone.utc)
                    
                    # 다른 형식들 시도
                    formats = [
                        '%Y-%m-%d %H:%M:%S',
                        '%Y-%m-%d %H:%M:%S.%f',
                        '%Y-%m-%d',
                        '%Y/%m/%d %H:%M:%S',
                        '%d/%m/%Y %H:%M:%S'
                    ]
                    
                    for fmt in formats:
                        try:
                            dt = datetime.strptime(time_value, fmt)
                            return dt.replace(tzinfo=timezone.utc)
                        except ValueError:
                            continue
                    
                except ValueError:
                    pass
            
            logger.debug(f"시간 파싱 실패: {time_value} (type: {type(time_value)})")
            return None
            
        except Exception as e:
            logger.debug(f"시간 파싱 오류: {e}")
            return None
    
    def _is_in_range(self, target_time: datetime, start_time: datetime, end_time: datetime) -> bool:
        """시간이 범위 내에 있는지 확인
        
        Args:
            target_time: 확인할 시간
            start_time: 시작 시간
            end_time: 종료 시간
            
        Returns:
            범위 내에 있으면 True, 그렇지 않으면 False
        """
        try:
            # 모든 시간을 UTC로 변환
            if target_time.tzinfo is None:
                target_time = target_time.replace(tzinfo=timezone.utc)
            else:
                target_time = target_time.astimezone(timezone.utc)
            
            if start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=timezone.utc)
            else:
                start_time = start_time.astimezone(timezone.utc)
            
            if end_time.tzinfo is None:
                end_time = end_time.replace(tzinfo=timezone.utc)
            else:
                end_time = end_time.astimezone(timezone.utc)
            
            return start_time <= target_time <= end_time
            
        except Exception as e:
            logger.warning(f"시간 범위 확인 오류: {e}")
            return True  # 오류 시 포함시킴
    
    def get_status(self) -> Dict[str, Any]:
        """현재 필터링 상태 반환
        
        Returns:
            상태 정보 딕셔너리
        """
        if not self.is_enabled or not self.current_range:
            return {
                "enabled": False,
                "range": None,
                "description": "시간 필터링 비활성화"
            }
        
        start_time, end_time = self.current_range
        return {
            "enabled": True,
            "range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            },
            "description": f"{start_time.strftime('%Y-%m-%d %H:%M')} ~ {end_time.strftime('%Y-%m-%d %H:%M')}"
        }