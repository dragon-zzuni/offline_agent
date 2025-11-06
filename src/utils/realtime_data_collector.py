#!/usr/bin/env python3
"""
실시간 데이터 수집기

VDOS에서 실시간으로 메시지와 이메일을 수집하여 분석합니다.
"""

import logging
import requests
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
import json

logger = logging.getLogger(__name__)

class RealtimeDataCollector:
    """실시간 데이터 수집기 (캐시 시스템 포함)"""
    
    def __init__(self, 
                 email_server_url: str = "http://127.0.0.1:8000",
                 chat_server_url: str = "http://127.0.0.1:8001",
                 sim_manager_url: str = "http://127.0.0.1:8015"):
        """
        실시간 데이터 수집기 초기화
        
        Args:
            email_server_url: 이메일 서버 URL
            chat_server_url: 채팅 서버 URL  
            sim_manager_url: 시뮬레이션 매니저 URL
        """
        self.email_server_url = email_server_url
        self.chat_server_url = chat_server_url
        self.sim_manager_url = sim_manager_url
        
        # 🚀 캐시 시스템 추가
        self._message_cache = {}  # 전체 메시지 캐시
        self._persona_cache = {}  # 페르소나별 필터링된 메시지 캐시
        self._cache_timestamp = None  # 캐시 생성 시간
        self._last_tick = None  # 마지막 틱 정보
        
    def get_current_tick_info(self) -> Optional[Dict]:
        """현재 틱 정보 조회"""
        try:
            response = requests.get(f"{self.sim_manager_url}/status", timeout=5)
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"틱 정보 조회 실패: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"틱 정보 조회 오류: {e}")
            return None
    
    def get_simulation_time_range(self) -> Optional[Tuple[datetime, datetime]]:
        """시뮬레이션 전체 시간 범위 조회"""
        try:
            # 1. VDOS 데이터베이스에서 시간 범위 조회
            vdos_range = self._get_vdos_db_time_range()
            if vdos_range:
                return vdos_range
            
            # 2. 시뮬레이션 상태에서 시작/종료 시간 정보 가져오기
            status = self.get_current_tick_info()
            if status:
                # 시뮬레이션 시작 시간과 현재 시간 반환
                start_time = datetime.fromisoformat(status.get('simulation_start', '2025-10-22T15:00:00'))
                current_time = datetime.fromisoformat(status.get('current_time', datetime.now().isoformat()))
                return (start_time, current_time)
            
            # 3. 기본값: 데이터 파일에서 추출
            return self._get_data_file_time_range()
            
        except Exception as e:
            logger.error(f"시뮬레이션 시간 범위 조회 오류: {e}")
            return self._get_data_file_time_range()
    
    def _get_vdos_db_time_range(self) -> Optional[Tuple[datetime, datetime]]:
        """VDOS 데이터베이스에서 시간 범위 추출"""
        try:
            import sqlite3
            import os
            
            # VDOS 데이터베이스 경로 (프로젝트 루트에서 상대 경로)
            vdos_db_path = os.path.join("virtualoffice", "src", "virtualoffice", "vdos.db")
            
            if not os.path.exists(vdos_db_path):
                logger.warning(f"VDOS 데이터베이스를 찾을 수 없음: {vdos_db_path}")
                return None
            
            conn = sqlite3.connect(vdos_db_path)
            
            # 채팅 메시지와 이메일에서 시간 범위 조회
            times = []
            
            # 채팅 메시지 시간 범위
            try:
                cursor = conn.execute("SELECT MIN(sent_at), MAX(sent_at) FROM chat_messages")
                chat_range = cursor.fetchone()
                if chat_range[0] and chat_range[1]:
                    times.extend([chat_range[0], chat_range[1]])
            except sqlite3.Error:
                pass
            
            # 이메일 시간 범위
            try:
                cursor = conn.execute("SELECT MIN(sent_at), MAX(sent_at) FROM emails")
                email_range = cursor.fetchone()
                if email_range[0] and email_range[1]:
                    times.extend([email_range[0], email_range[1]])
            except sqlite3.Error:
                pass
            
            conn.close()
            
            if times:
                # 시간 문자열을 datetime으로 변환
                datetime_objects = []
                for time_str in times:
                    try:
                        dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                        datetime_objects.append(dt.replace(tzinfo=None))
                    except:
                        pass
                
                if datetime_objects:
                    min_time = min(datetime_objects)
                    max_time = max(datetime_objects)
                    logger.info(f"VDOS DB 시간 범위: {min_time} ~ {max_time}")
                    return (min_time, max_time)
            
            return None
            
        except Exception as e:
            logger.error(f"VDOS DB 시간 범위 추출 오류: {e}")
            return None
    
    def _get_data_file_time_range(self) -> Optional[Tuple[datetime, datetime]]:
        """데이터 파일에서 시간 범위 추출"""
        try:
            import os
            
            # 채팅 메시지 파일에서 시간 범위 추출
            chat_file = os.path.join("data", "multi_project_8week_ko", "chat_messages_202510230931.json")
            if os.path.exists(chat_file):
                with open(chat_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                chat_messages = data.get('chat_messages', [])
                if chat_messages:
                    times = [msg.get('sent_at') for msg in chat_messages if msg.get('sent_at')]
                    if times:
                        min_time = min(times)
                        max_time = max(times)
                        
                        min_dt = datetime.fromisoformat(min_time.replace('Z', '+00:00'))
                        max_dt = datetime.fromisoformat(max_time.replace('Z', '+00:00'))
                        
                        return (min_dt.replace(tzinfo=None), max_dt.replace(tzinfo=None))
            
            return None
            
        except Exception as e:
            logger.error(f"데이터 파일 시간 범위 추출 오류: {e}")
            return None
    
    def collect_messages(self, start_time: datetime, end_time: datetime, persona_filter: Optional[Dict] = None) -> List[Dict]:
        """메시지 수집 (페르소나 필터링 지원)"""
        try:
            result = self.collect_messages_in_range(start_time, end_time)
            
            if not result.get("success", False):
                return []
            
            # 모든 메시지 통합
            all_messages = []
            
            # 채팅 메시지 변환
            for msg in result.get("chat_messages", []):
                all_messages.append({
                    "type": "chat",
                    "content": msg.get("body", msg.get("content", "")),
                    "sender": msg.get("sender", ""),
                    "timestamp": msg.get("sent_at", msg.get("timestamp", "")),
                    "room_id": msg.get("room_id", ""),
                    "id": msg.get("id", "")
                })
            
            # 이메일 메시지 변환
            for msg in result.get("email_messages", []):
                all_messages.append({
                    "type": "email",
                    "content": msg.get("body", msg.get("content", "")),
                    "sender": msg.get("sender", ""),
                    "recipient": msg.get("recipient", ""),
                    "subject": msg.get("subject", ""),
                    "timestamp": msg.get("sent_at", msg.get("timestamp", "")),
                    "id": msg.get("id", "")
                })
            
            # 페르소나 필터링 적용
            if persona_filter:
                filtered_messages = self._apply_persona_filter(all_messages, persona_filter)
                logger.info(f"페르소나 필터링: {len(all_messages)}개 → {len(filtered_messages)}개")
                return filtered_messages
            
            return all_messages
            
        except Exception as e:
            logger.error(f"메시지 수집 오류: {e}")
            return []
    
    def _apply_persona_filter(self, messages: List[Dict], persona_filter: Dict) -> List[Dict]:
        """페르소나 필터 적용 (발신자 기준으로 수정)"""
        try:
            filtered_messages = []
            
            filter_email = persona_filter.get('email', '').lower().strip()
            filter_chat_handle = persona_filter.get('chat_handle', '').lower().strip()
            filter_name = persona_filter.get('name', '').lower().strip()
            
            logger.info(f"📧 페르소나 필터 적용 시작 (발신자 기준)")
            logger.info(f"   - 이메일: '{filter_email}'")
            logger.info(f"   - 채팅 핸들: '{filter_chat_handle}'")
            logger.info(f"   - 이름: '{filter_name}'")
            
            match_count = 0
            
            for i, message in enumerate(messages):
                sender = message.get('sender', '').lower().strip()
                sender_email = message.get('sender_email', '').lower().strip()
                sender_handle = message.get('sender_handle', '').lower().strip()
                content = message.get('content', message.get('body', ''))[:50]  # 로깅용 내용 일부
                
                # 발신자 기준으로 매칭 (해당 페르소나가 보낸 메시지)
                is_match = False
                match_reason = []
                
                # 이메일 주소로 발신자 매칭
                if filter_email:
                    if filter_email == sender_email:
                        is_match = True
                        match_reason.append(f"이메일 발신자 정확 매칭")
                    elif filter_email in sender_email:
                        is_match = True
                        match_reason.append(f"이메일 발신자 부분 매칭")
                
                # 채팅 핸들로 발신자 매칭
                if filter_chat_handle:
                    if filter_chat_handle == sender_handle:
                        is_match = True
                        match_reason.append(f"채팅 핸들 발신자 정확 매칭")
                    elif filter_chat_handle in sender_handle:
                        is_match = True
                        match_reason.append(f"채팅 핸들 발신자 부분 매칭")
                    # sender 필드에서도 확인
                    elif filter_chat_handle == sender:
                        is_match = True
                        match_reason.append(f"채팅 핸들 sender 정확 매칭")
                    elif filter_chat_handle in sender:
                        is_match = True
                        match_reason.append(f"채팅 핸들 sender 부분 매칭")
                
                # 이름으로 발신자 매칭
                if filter_name and len(filter_name) > 1:
                    if filter_name == sender:
                        is_match = True
                        match_reason.append(f"이름 발신자 정확 매칭")
                    elif filter_name in sender:
                        is_match = True
                        match_reason.append(f"이름 발신자 부분 매칭")
                
                if is_match:
                    filtered_messages.append(message)
                    match_count += 1
                    
                    # 처음 5개 매칭 결과만 로깅
                    if match_count <= 5:
                        logger.debug(f"   ✅ 매칭 #{match_count}: {sender} ({', '.join(match_reason)})")
                        logger.debug(f"      내용: {content}...")
            
            # 매칭률 계산 (division by zero 방지)
            if len(messages) > 0:
                match_rate = len(filtered_messages) / len(messages) * 100
                logger.info(f"📊 페르소나 필터링 완료: {len(messages)}개 → {len(filtered_messages)}개 (매칭률: {match_rate:.1f}%)")
            else:
                logger.info(f"📊 페르소나 필터링 완료: {len(messages)}개 → {len(filtered_messages)}개 (메시지 없음)")
            
            return filtered_messages
            
        except Exception as e:
            logger.error(f"페르소나 필터링 오류: {e}")
            return messages
    
    def collect_messages_in_range(self, start_time: datetime, end_time: datetime) -> Dict:
        """지정된 시간 범위의 메시지 수집"""
        try:
            # 1. VDOS 데이터베이스에서 수집 시도
            chat_messages, email_messages = self._collect_from_vdos_db(start_time, end_time)
            
            # 2. VDOS DB에서 데이터가 없으면 실시간 서버 시도
            if not chat_messages and not email_messages:
                chat_messages = self._collect_chat_messages(start_time, end_time)
                email_messages = self._collect_email_messages(start_time, end_time)
            
            # 결과 통합
            result = {
                "success": True,
                "time_range": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat()
                },
                "chat_messages": chat_messages,
                "email_messages": email_messages,
                "total_messages": len(chat_messages) + len(email_messages)
            }
            
            logger.info(f"메시지 수집 완료: 채팅 {len(chat_messages)}개, 이메일 {len(email_messages)}개")
            return result
            
        except Exception as e:
            logger.error(f"메시지 수집 오류: {e}")
            return {
                "success": False,
                "error": str(e),
                "chat_messages": [],
                "email_messages": [],
                "total_messages": 0
            }
    
    def _collect_from_vdos_db(self, start_time: datetime, end_time: datetime) -> Tuple[List[Dict], List[Dict]]:
        """VDOS 데이터베이스에서 메시지 수집"""
        try:
            import sqlite3
            from pathlib import Path
            
            # VDOS 데이터베이스 경로 찾기
            current_dir = Path.cwd()
            possible_paths = [
                current_dir / "virtualoffice" / "src" / "virtualoffice" / "vdos.db",
                current_dir / ".." / "virtualoffice" / "src" / "virtualoffice" / "vdos.db",
                current_dir / ".." / ".." / "virtualoffice" / "src" / "virtualoffice" / "vdos.db",
                Path("virtualoffice/src/virtualoffice/vdos.db"),
                Path("../virtualoffice/src/virtualoffice/vdos.db"),
                Path("../../virtualoffice/src/virtualoffice/vdos.db")
            ]
            
            vdos_db_path = None
            for path in possible_paths:
                if path.exists():
                    vdos_db_path = path.resolve()
                    break
            
            if not vdos_db_path:
                logger.warning("VDOS 데이터베이스를 찾을 수 없음")
                return [], []
            
            conn = sqlite3.connect(str(vdos_db_path))
            conn.row_factory = sqlite3.Row  # 딕셔너리 형태로 결과 반환
            
            chat_messages = []
            email_messages = []
            
            # 채팅 메시지 수집
            try:
                chat_query = """
                SELECT id, room_id, sender, body, sent_at 
                FROM chat_messages 
                WHERE datetime(sent_at) BETWEEN ? AND ?
                ORDER BY sent_at
                """
                
                cursor = conn.execute(chat_query, (start_time.isoformat(), end_time.isoformat()))
                for row in cursor:
                    chat_messages.append({
                        "id": row["id"],
                        "room_id": row["room_id"],
                        "sender": row["sender"],
                        "body": row["body"],
                        "sent_at": row["sent_at"]
                    })
                
                logger.info(f"VDOS DB에서 채팅 메시지 {len(chat_messages)}개 수집")
                
            except sqlite3.Error as e:
                logger.warning(f"채팅 메시지 수집 실패: {e}")
            
            # 이메일 메시지 수집
            try:
                # recipients 컬럼이 없으므로 기본 컬럼만 조회
                email_query = """
                SELECT id, sender, subject, body, sent_at
                FROM emails 
                WHERE datetime(sent_at) BETWEEN ? AND ?
                ORDER BY sent_at
                """
                
                cursor = conn.execute(email_query, (start_time.isoformat(), end_time.isoformat()))
                for row in cursor:
                    email_messages.append({
                        "id": row["id"],
                        "sender": row["sender"],
                        "recipients": [],  # 빈 리스트로 설정
                        "subject": row["subject"],
                        "body": row["body"],
                        "sent_at": row["sent_at"]
                    })
                
                logger.info(f"VDOS DB에서 이메일 메시지 {len(email_messages)}개 수집")
                
            except sqlite3.Error as e:
                logger.warning(f"이메일 메시지 수집 실패: {e}")
            
            conn.close()
            return chat_messages, email_messages
            
        except Exception as e:
            logger.error(f"VDOS DB 수집 오류: {e}")
            return [], []
    
    def _collect_chat_messages(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """채팅 메시지 수집"""
        try:
            # 시간대 정보 제거 (naive datetime으로 통일)
            start_naive = start_time.replace(tzinfo=None) if start_time.tzinfo else start_time
            end_naive = end_time.replace(tzinfo=None) if end_time.tzinfo else end_time
            
            # 실시간 서버에서 메시지 조회 시도
            try:
                response = requests.get(f"{self.chat_server_url}/messages", timeout=5)
                if response.status_code == 200:
                    messages = response.json()
                    # 시간 범위 필터링
                    filtered = []
                    for msg in messages:
                        msg_time_str = msg.get('sent_at', '')
                        if msg_time_str:
                            msg_time = datetime.fromisoformat(msg_time_str.replace('Z', '+00:00'))
                            msg_naive = msg_time.replace(tzinfo=None)
                            if start_naive <= msg_naive <= end_naive:
                                filtered.append(msg)
                    return filtered
            except:
                pass
            
            # 실시간 서버 연결 실패 시 로컬 파일 사용
            return self._load_chat_messages_from_file(start_naive, end_naive)
            
        except Exception as e:
            logger.error(f"채팅 메시지 수집 오류: {e}")
            return []
    
    def _collect_email_messages(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """이메일 메시지 수집"""
        try:
            # 시간대 정보 제거 (naive datetime으로 통일)
            start_naive = start_time.replace(tzinfo=None) if start_time.tzinfo else start_time
            end_naive = end_time.replace(tzinfo=None) if end_time.tzinfo else end_time
            
            # 실시간 서버에서 이메일 조회 시도
            try:
                response = requests.get(f"{self.email_server_url}/emails", timeout=5)
                if response.status_code == 200:
                    emails = response.json()
                    # 시간 범위 필터링
                    filtered = []
                    for email in emails:
                        email_time_str = email.get('sent_at', '')
                        if email_time_str:
                            email_time = datetime.fromisoformat(email_time_str.replace('Z', '+00:00'))
                            email_naive = email_time.replace(tzinfo=None)
                            if start_naive <= email_naive <= end_naive:
                                filtered.append(email)
                    return filtered
            except:
                pass
            
            # 실시간 서버 연결 실패 시 로컬 파일 사용
            return self._load_email_messages_from_file(start_naive, end_naive)
            
        except Exception as e:
            logger.error(f"이메일 메시지 수집 오류: {e}")
            return []
    
    def _load_chat_messages_from_file(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """파일에서 채팅 메시지 로드"""
        try:
            import os
            
            chat_file = os.path.join("data", "multi_project_8week_ko", "chat_messages_202510230931.json")
            if not os.path.exists(chat_file):
                return []
            
            with open(chat_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            chat_messages = data.get('chat_messages', [])
            filtered = []
            
            for msg in chat_messages:
                msg_time_str = msg.get('sent_at', '')
                if msg_time_str:
                    msg_time = datetime.fromisoformat(msg_time_str.replace('Z', '+00:00'))
                    msg_naive = msg_time.replace(tzinfo=None)
                    if start_time <= msg_naive <= end_time:
                        filtered.append(msg)
            
            return filtered
            
        except Exception as e:
            logger.error(f"채팅 메시지 파일 로드 오류: {e}")
            return []
    
    def _load_email_messages_from_file(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """파일에서 이메일 메시지 로드"""
        try:
            import os
            
            email_file = os.path.join("data", "multi_project_8week_ko", "emails_20251023093 2.json")
            if not os.path.exists(email_file):
                return []
            
            with open(email_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            emails = data.get('emails', [])
            filtered = []
            
            for email in emails:
                email_time_str = email.get('sent_at', '')
                if email_time_str:
                    email_time = datetime.fromisoformat(email_time_str.replace('Z', '+00:00'))
                    email_naive = email_time.replace(tzinfo=None)
                    if start_time <= email_naive <= end_time:
                        filtered.append(email)
            
            return filtered
            
        except Exception as e:
            logger.error(f"이메일 메시지 파일 로드 오류: {e}")
            return []
    
    def is_realtime_available(self) -> bool:
        """실시간 서버 연결 가능 여부 확인"""
        try:
            # 시뮬레이션 매니저 상태 확인
            response = requests.get(f"{self.sim_manager_url}/status", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    # 🚀 캐시 시스템 메서드들
    def _should_refresh_cache(self) -> bool:
        """캐시를 새로고침해야 하는지 확인"""
        try:
            # 캐시가 없으면 새로고침 필요
            if not self._message_cache or self._cache_timestamp is None:
                return True
            
            # 틱이 변경되었으면 새로고침 필요
            current_tick_info = self.get_current_tick_info()
            if current_tick_info:
                current_tick = current_tick_info.get('current_tick')
                if current_tick != self._last_tick:
                    logger.info(f"🔄 틱 변경 감지: {self._last_tick} → {current_tick}, 캐시 새로고침")
                    return True
            
            # 캐시가 5분 이상 오래되었으면 새로고침
            from datetime import timedelta
            if datetime.now() - self._cache_timestamp > timedelta(minutes=5):
                logger.info(f"⏰ 캐시 만료 (5분 경과), 새로고침")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"캐시 새로고침 확인 오류: {e}")
            return True
    
    def _update_cache(self, start_time: datetime, end_time: datetime):
        """캐시 업데이트"""
        try:
            logger.info(f"💾 전체 메시지 캐시 업데이트 시작")
            
            # 전체 메시지 수집
            result = self.collect_messages_in_range(start_time, end_time)
            
            if result.get('success'):
                # 전체 메시지 캐시 저장
                all_messages = result.get('chat_messages', []) + result.get('email_messages', [])
                self._message_cache = {
                    'messages': all_messages,
                    'start_time': start_time,
                    'end_time': end_time,
                    'total_count': len(all_messages)
                }
                
                # 페르소나별 캐시 초기화 (새로 필터링해야 함)
                self._persona_cache = {}
                
                # 캐시 메타데이터 업데이트
                self._cache_timestamp = datetime.now()
                
                # 현재 틱 정보 저장
                tick_info = self.get_current_tick_info()
                if tick_info:
                    self._last_tick = tick_info.get('current_tick')
                
                logger.info(f"✅ 캐시 업데이트 완료: {len(all_messages)}개 메시지")
            else:
                logger.error(f"❌ 캐시 업데이트 실패: {result.get('error')}")
                
        except Exception as e:
            logger.error(f"캐시 업데이트 오류: {e}")
    
    def _get_cached_persona_messages(self, persona_filter: Dict) -> Optional[List[Dict]]:
        """캐시된 페르소나별 메시지 반환"""
        try:
            # 페르소나 식별자 생성
            persona_key = f"{persona_filter.get('email', '')}_{persona_filter.get('chat_handle', '')}_{persona_filter.get('name', '')}"
            
            # 캐시에서 찾기
            if persona_key in self._persona_cache:
                cached_data = self._persona_cache[persona_key]
                logger.info(f"🎯 페르소나 캐시 히트: {persona_key} ({len(cached_data)}개 메시지)")
                return cached_data
            
            return None
            
        except Exception as e:
            logger.error(f"페르소나 캐시 조회 오류: {e}")
            return None
    
    def _cache_persona_messages(self, persona_filter: Dict, filtered_messages: List[Dict]):
        """페르소나별 필터링된 메시지 캐시"""
        try:
            # 페르소나 식별자 생성
            persona_key = f"{persona_filter.get('email', '')}_{persona_filter.get('chat_handle', '')}_{persona_filter.get('name', '')}"
            
            # 캐시에 저장
            self._persona_cache[persona_key] = filtered_messages
            logger.info(f"💾 페르소나 캐시 저장: {persona_key} ({len(filtered_messages)}개 메시지)")
            
        except Exception as e:
            logger.error(f"페르소나 캐시 저장 오류: {e}")
    
    def collect_messages_with_cache(self, start_time: datetime, end_time: datetime, persona_filter: Optional[Dict] = None) -> Dict:
        """캐시를 활용한 메시지 수집 (개선된 버전)"""
        try:
            # 1. 캐시 새로고침 필요 여부 확인
            if self._should_refresh_cache():
                self._update_cache(start_time, end_time)
            
            # 2. 페르소나 필터가 없으면 전체 캐시 반환
            if not persona_filter:
                if self._message_cache:
                    messages = self._message_cache['messages']
                    logger.info(f"📦 전체 캐시 반환: {len(messages)}개 메시지")
                    return {
                        "success": True,
                        "messages": messages,
                        "total_count": len(messages),
                        "from_cache": True
                    }
            
            # 3. 페르소나별 캐시 확인
            cached_persona_messages = self._get_cached_persona_messages(persona_filter)
            if cached_persona_messages is not None:
                return {
                    "success": True,
                    "messages": cached_persona_messages,
                    "total_count": len(cached_persona_messages),
                    "from_cache": True,
                    "persona_filter": persona_filter
                }
            
            # 4. 캐시에서 페르소나 필터링 수행
            if self._message_cache:
                all_messages = self._message_cache['messages']
                filtered_messages = self._apply_persona_filter(all_messages, persona_filter)
                
                # 결과를 캐시에 저장
                self._cache_persona_messages(persona_filter, filtered_messages)
                
                logger.info(f"🔍 페르소나 필터링 완료: {len(all_messages)}개 → {len(filtered_messages)}개")
                return {
                    "success": True,
                    "messages": filtered_messages,
                    "total_count": len(filtered_messages),
                    "from_cache": True,
                    "persona_filter": persona_filter
                }
            
            # 5. 캐시가 없으면 일반 수집
            logger.warning("⚠️ 캐시 없음, 일반 수집 수행")
            return self.collect_messages_in_range(start_time, end_time)
            
        except Exception as e:
            logger.error(f"캐시 기반 메시지 수집 오류: {e}")
            return {
                "success": False,
                "error": str(e),
                "messages": [],
                "total_count": 0
            }

# 전역 인스턴스
_realtime_collector: Optional[RealtimeDataCollector] = None

def get_realtime_collector() -> RealtimeDataCollector:
    """실시간 데이터 수집기 싱글톤 인스턴스 반환"""
    global _realtime_collector
    
    if _realtime_collector is None:
        _realtime_collector = RealtimeDataCollector()
    
    return _realtime_collector