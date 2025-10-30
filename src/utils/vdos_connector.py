# -*- coding: utf-8 -*-
"""
VDOS 데이터베이스 연동 모듈
VirtualOffice의 VDOS 데이터베이스에서 데이터를 가져와서 TODO 분석에 활용
"""
import os
import sqlite3
import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class VDOSConnector:
    """VDOS 데이터베이스 연동 클래스"""
    
    def __init__(self, vdos_db_path: Optional[str] = None):
        """
        VDOS 연동 초기화
        
        Args:
            vdos_db_path: VDOS 데이터베이스 경로 (None이면 자동 탐지)
        """
        self.vdos_db_path = vdos_db_path or self._find_vdos_db()
        self.is_available = self._check_availability()
        
        if self.is_available:
            logger.info(f"[VDOS] 데이터베이스 연결 성공: {self.vdos_db_path}")
        else:
            logger.warning(f"[VDOS] 데이터베이스 연결 실패: {self.vdos_db_path}")
    
    def _find_vdos_db(self) -> str:
        """VDOS 데이터베이스 자동 탐지"""
        # 가능한 경로들
        possible_paths = [
            "virtualoffice/src/virtualoffice/vdos.db",
            "../virtualoffice/src/virtualoffice/vdos.db",
            "../../virtualoffice/src/virtualoffice/vdos.db",
            os.path.expanduser("~/virtualoffice/src/virtualoffice/vdos.db"),
        ]
        
        # 현재 파일 기준으로 상대 경로 계산
        current_dir = Path(__file__).parent
        project_root = current_dir.parent.parent.parent  # offline_agent/src/utils -> project_root
        vdos_path = project_root / "virtualoffice" / "src" / "virtualoffice" / "vdos.db"
        possible_paths.insert(0, str(vdos_path))
        
        for path in possible_paths:
            if os.path.exists(path):
                return os.path.abspath(path)
        
        # 기본값 반환
        return str(vdos_path)
    
    def _check_availability(self) -> bool:
        """VDOS 데이터베이스 사용 가능 여부 확인"""
        if not os.path.exists(self.vdos_db_path):
            return False
        
        try:
            with sqlite3.connect(self.vdos_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='people'")
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"[VDOS] 데이터베이스 확인 실패: {e}")
            return False
    
    def get_people(self) -> List[Dict[str, Any]]:
        """VDOS에서 사람 정보 가져오기"""
        if not self.is_available:
            return []
        
        try:
            with sqlite3.connect(self.vdos_db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("""
                SELECT id, name, role, email_address, chat_handle, team_name, 
                       skills, personality, is_department_head
                FROM people
                ORDER BY name
                """)
                
                people = []
                for row in cursor.fetchall():
                    person = dict(row)
                    # JSON 필드 파싱
                    for field in ['skills', 'personality']:
                        try:
                            person[field] = json.loads(person[field] or '[]')
                        except:
                            person[field] = []
                    people.append(person)
                
                logger.info(f"[VDOS] 사람 정보 {len(people)}개 로드")
                return people
                
        except Exception as e:
            logger.error(f"[VDOS] 사람 정보 로드 실패: {e}")
            return []
    
    def get_recent_emails(self, limit: int = 100) -> List[Dict[str, Any]]:
        """VDOS에서 최근 이메일 가져오기"""
        if not self.is_available:
            return []
        
        try:
            with sqlite3.connect(self.vdos_db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("""
                SELECT e.id, e.sender, e.subject, e.body, e.thread_id, e.sent_at,
                       GROUP_CONCAT(er.address) as recipients,
                       GROUP_CONCAT(er.kind) as recipient_types
                FROM emails e
                LEFT JOIN email_recipients er ON e.id = er.email_id
                GROUP BY e.id
                ORDER BY e.sent_at DESC
                LIMIT ?
                """, (limit,))
                
                emails = []
                for row in cursor.fetchall():
                    email = dict(row)
                    # 수신자 정보 파싱
                    if email['recipients']:
                        recipients = email['recipients'].split(',')
                        recipient_types = (email['recipient_types'] or '').split(',')
                        email['recipients_list'] = [
                            {'email': r, 'type': recipient_types[i] if i < len(recipient_types) else 'to'}
                            for i, r in enumerate(recipients)
                        ]
                    else:
                        email['recipients_list'] = []
                    
                    emails.append(email)
                
                logger.info(f"[VDOS] 이메일 {len(emails)}개 로드")
                return emails
                
        except Exception as e:
            logger.error(f"[VDOS] 이메일 로드 실패: {e}")
            return []
    
    def get_recent_chat_messages(self, limit: int = 100) -> List[Dict[str, Any]]:
        """VDOS에서 최근 채팅 메시지 가져오기"""
        if not self.is_available:
            return []
        
        try:
            with sqlite3.connect(self.vdos_db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("""
                SELECT cm.id, cm.room_id, cm.sender, cm.body, cm.sent_at,
                       cr.name as room_name
                FROM chat_messages cm
                LEFT JOIN chat_rooms cr ON cm.room_id = cr.id
                ORDER BY cm.sent_at DESC
                LIMIT ?
                """, (limit,))
                
                messages = []
                for row in cursor.fetchall():
                    messages.append(dict(row))
                
                logger.info(f"[VDOS] 채팅 메시지 {len(messages)}개 로드")
                return messages
                
        except Exception as e:
            logger.error(f"[VDOS] 채팅 메시지 로드 실패: {e}")
            return []
    
    def find_person_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """이름으로 사람 찾기 (다양한 변형 지원)"""
        if not self.is_available:
            return None
        
        people = self.get_people()
        name_lower = name.lower()
        
        # 정확한 매칭 우선
        for person in people:
            if person['name'].lower() == name_lower:
                return person
            if person['email_address'].lower() == name_lower:
                return person
            if person['chat_handle'].lower() == name_lower:
                return person
        
        # 부분 매칭
        for person in people:
            if name_lower in person['name'].lower():
                return person
            if name_lower in person['email_address'].lower():
                return person
            if name_lower in person['chat_handle'].lower():
                return person
        
        return None
    
    def get_person_variations(self, person_name: str) -> List[str]:
        """사람 이름의 다양한 변형 반환"""
        person = self.find_person_by_name(person_name)
        if not person:
            return [person_name]
        
        variations = [
            person['name'],
            person['email_address'],
            person['chat_handle'],
        ]
        
        # 이메일에서 사용자명 추출
        email = person['email_address']
        if '@' in email:
            username = email.split('@')[0]
            variations.append(username)
            
            # 점이나 언더스코어로 분리된 이름 추가
            if '.' in username:
                variations.extend(username.split('.'))
            if '_' in username:
                variations.extend(username.split('_'))
        
        # 중복 제거 및 빈 문자열 제거
        variations = list(set(v.strip() for v in variations if v and v.strip()))
        
        logger.debug(f"[VDOS] {person_name} 변형: {variations}")
        return variations
    
    def get_department_heads(self) -> List[Dict[str, Any]]:
        """부서장 목록 가져오기"""
        if not self.is_available:
            return []
        
        people = self.get_people()
        return [p for p in people if p.get('is_department_head')]
    
    def get_team_members(self, team_name: str) -> List[Dict[str, Any]]:
        """팀 멤버 목록 가져오기"""
        if not self.is_available:
            return []
        
        people = self.get_people()
        return [p for p in people if p.get('team_name') == team_name]


# 전역 인스턴스
_vdos_connector = None

def get_vdos_connector() -> VDOSConnector:
    """VDOS 연결자 싱글톤 인스턴스 반환"""
    global _vdos_connector
    if _vdos_connector is None:
        _vdos_connector = VDOSConnector()
    return _vdos_connector

def is_vdos_available() -> bool:
    """VDOS 데이터베이스 사용 가능 여부 확인"""
    return get_vdos_connector().is_available