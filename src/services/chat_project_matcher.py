#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
채팅 메시지 기반 프로젝트 매칭 서비스

채팅 메시지에서 프로젝트를 추론하기 위해 VDOS DB의 다양한 정보를 활용합니다:
- 채팅방 멤버 정보
- 발신자/수신자 프로젝트 참여 정보
- 메시지 시간대와 프로젝트 기간
- 메시지 내용 키워드 분석
"""

import sqlite3
import logging
import re
from typing import Dict, List, Optional, Tuple, Set
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class ChatProjectMatcher:
    """채팅 메시지 기반 프로젝트 매칭"""
    
    def __init__(self, vdos_db_path: str, project_tags: Dict, person_project_mapping: Dict, project_periods: Dict):
        """
        Args:
            vdos_db_path: VDOS 데이터베이스 경로
            project_tags: 프로젝트 태그 딕셔너리
            person_project_mapping: 사람-프로젝트 매핑
            project_periods: 프로젝트 기간 정보
        """
        self.vdos_db_path = vdos_db_path
        self.project_tags = project_tags
        self.person_project_mapping = person_project_mapping
        self.project_periods = project_periods
    
    def match_project_from_chat(self, sender: str, message_date: str = None, 
                                todo_content: str = None) -> Optional[Tuple[str, str]]:
        """채팅 메시지에서 프로젝트 매칭
        
        Args:
            sender: 발신자 (채팅 핸들)
            message_date: 메시지 날짜
            todo_content: TODO 내용 (있는 경우)
            
        Returns:
            (프로젝트 코드, 분류 근거) 튜플 또는 None
        """
        try:
            # 1. VDOS DB에서 채팅 메시지 정보 가져오기
            chat_info = self._fetch_chat_info(sender, message_date)
            if not chat_info:
                logger.debug(f"[채팅 매칭] 채팅 정보를 찾을 수 없음: {sender}")
                return None
            
            # 2. 채팅방 멤버 기반 프로젝트 추론
            room_members = chat_info.get('room_members', [])
            message_body = chat_info.get('body', '')
            
            # 3. 점수 기반 프로젝트 매칭
            project_scores = self._calculate_project_scores(
                sender=sender,
                room_members=room_members,
                message_body=message_body,
                message_date=message_date,
                todo_content=todo_content
            )
            
            # 4. 가장 높은 점수의 프로젝트 반환
            if project_scores:
                best_project = max(project_scores.items(), key=lambda x: x[1][0])
                project_code, (score, reasons) = best_project
                
                if score >= 10:  # 최소 점수 임계값
                    reason_text = ", ".join(reasons)
                    logger.info(f"[채팅 매칭] {sender} → {project_code} (점수: {score}, {reason_text})")
                    return (project_code, f"채팅분석: {reason_text}")
            
            return None
            
        except Exception as e:
            logger.error(f"채팅 프로젝트 매칭 오류: {e}")
            return None
    
    def _fetch_chat_info(self, sender: str, message_date: str = None) -> Optional[Dict]:
        """VDOS DB에서 채팅 정보 가져오기"""
        try:
            conn = sqlite3.connect(self.vdos_db_path)
            cur = conn.cursor()
            
            # 발신자의 최근 메시지 조회 (날짜 기준 또는 최신)
            if message_date:
                # 날짜 기준으로 가장 가까운 메시지
                cur.execute('''
                    SELECT cm.id, cm.sender, cm.body, cm.sent_at, cm.room_id,
                           cr.name as room_name, cr.is_dm
                    FROM chat_messages cm
                    JOIN chat_rooms cr ON cm.room_id = cr.id
                    WHERE cm.sender = ?
                    ORDER BY ABS(julianday(cm.sent_at) - julianday(?))
                    LIMIT 1
                ''', (sender, message_date))
            else:
                # 가장 최근 메시지
                cur.execute('''
                    SELECT cm.id, cm.sender, cm.body, cm.sent_at, cm.room_id,
                           cr.name as room_name, cr.is_dm
                    FROM chat_messages cm
                    JOIN chat_rooms cr ON cm.room_id = cr.id
                    WHERE cm.sender = ?
                    ORDER BY cm.id DESC
                    LIMIT 1
                ''', (sender,))
            
            result = cur.fetchone()
            
            if not result:
                conn.close()
                return None
            
            msg_id, msg_sender, msg_body, msg_sent_at, room_id, room_name, is_dm = result
            
            # 채팅방 멤버 조회
            cur.execute('''
                SELECT handle
                FROM chat_members
                WHERE room_id = ?
            ''', (room_id,))
            room_members = [row[0] for row in cur.fetchall()]
            
            conn.close()
            
            return {
                'id': msg_id,
                'sender': msg_sender,
                'body': msg_body,
                'sent_at': msg_sent_at,
                'room_id': room_id,
                'room_name': room_name,
                'is_dm': bool(is_dm),
                'room_members': room_members
            }
            
        except Exception as e:
            logger.error(f"채팅 정보 조회 오류: {e}")
            return None
    
    def _calculate_project_scores(self, sender: str, room_members: List[str], 
                                  message_body: str, message_date: str = None,
                                  todo_content: str = None) -> Dict[str, Tuple[int, List[str]]]:
        """프로젝트별 점수 계산
        
        Returns:
            {프로젝트코드: (점수, [근거들])} 딕셔너리
        """
        project_scores = {}
        
        # 모든 참여자 (발신자 + 채팅방 멤버)
        all_participants = set([sender] + room_members)
        
        # 각 참여자의 프로젝트 목록 수집
        participant_projects = {}
        for participant in all_participants:
            # 이메일 형식으로 변환 시도 (people 테이블 조회)
            participant_email = self._get_email_from_handle(participant)
            
            projects = []
            if participant_email and participant_email in self.person_project_mapping:
                projects = self.person_project_mapping[participant_email]
            elif participant in self.person_project_mapping:
                projects = self.person_project_mapping[participant]
            
            if projects:
                participant_projects[participant] = projects
        
        # 공통 프로젝트 찾기
        if participant_projects:
            # 모든 참여자가 공통으로 참여하는 프로젝트
            common_projects = set(participant_projects[list(participant_projects.keys())[0]])
            for projects in participant_projects.values():
                common_projects &= set(projects)
            
            # 공통 프로젝트에 높은 점수
            for project_code in common_projects:
                if project_code not in project_scores:
                    project_scores[project_code] = (0, [])
                
                score, reasons = project_scores[project_code]
                score += 50
                reasons.append(f"채팅방 멤버 {len(all_participants)}명 공통 프로젝트")
                project_scores[project_code] = (score, reasons)
            
            # 일부 참여자가 참여하는 프로젝트 (낮은 점수)
            all_projects = set()
            for projects in participant_projects.values():
                all_projects.update(projects)
            
            for project_code in all_projects - common_projects:
                if project_code not in project_scores:
                    project_scores[project_code] = (0, [])
                
                # 참여자 수 계산
                participant_count = sum(1 for p in participant_projects.values() if project_code in p)
                score, reasons = project_scores[project_code]
                score += participant_count * 10
                reasons.append(f"{participant_count}명 참여")
                project_scores[project_code] = (score, reasons)
        
        # 메시지 내용 키워드 분석
        combined_text = f"{message_body} {todo_content or ''}".lower()
        
        for project_code, project_tag in self.project_tags.items():
            if project_code not in project_scores:
                project_scores[project_code] = (0, [])
            
            score, reasons = project_scores[project_code]
            
            # 프로젝트명 매칭
            project_name_lower = project_tag.name.lower()
            if project_name_lower in combined_text:
                score += 30
                reasons.append(f"프로젝트명 '{project_tag.name}' 언급")
            
            # 프로젝트 설명 키워드 매칭
            if project_tag.description:
                desc_keywords = set(re.findall(r'[가-힣a-z]{3,}', project_tag.description.lower()))
                text_keywords = set(re.findall(r'[가-힣a-z]{3,}', combined_text))
                common_keywords = desc_keywords & text_keywords
                
                if common_keywords:
                    keyword_score = len(common_keywords) * 5
                    score += keyword_score
                    reasons.append(f"키워드 {len(common_keywords)}개 일치")
            
            # 프로젝트 코드 매칭
            if project_code.lower() in combined_text:
                score += 20
                reasons.append(f"프로젝트 코드 '{project_code}' 언급")
            
            project_scores[project_code] = (score, reasons)
        
        # 프로젝트 기간 정보 활용 (메시지 날짜가 있는 경우)
        if message_date:
            for project_code in list(project_scores.keys()):
                if project_code in self.project_periods:
                    score, reasons = project_scores[project_code]
                    period = self.project_periods[project_code]
                    
                    # TODO: 메시지 날짜를 주차로 변환하여 프로젝트 기간과 비교
                    # 현재는 기간 정보가 있다는 것만으로 약간의 가산점
                    score += 5
                    reasons.append(f"프로젝트 기간 {period['start_week']}~{period['end_week']}주차")
                    project_scores[project_code] = (score, reasons)
        
        # 점수가 0인 프로젝트 제거
        return {k: v for k, v in project_scores.items() if v[0] > 0}
    
    def _get_email_from_handle(self, handle: str) -> Optional[str]:
        """채팅 핸들에서 이메일 주소 조회"""
        try:
            conn = sqlite3.connect(self.vdos_db_path)
            cur = conn.cursor()
            
            # people 테이블에서 이메일 조회
            # 핸들이 이메일 앞부분과 매칭되는 경우 찾기
            cur.execute('''
                SELECT email_address
                FROM people
                WHERE email_address LIKE ? || '%'
                LIMIT 1
            ''', (handle.replace('@', ''),))
            
            result = cur.fetchone()
            conn.close()
            
            if result:
                return result[0]
            
            return None
            
        except Exception as e:
            logger.debug(f"이메일 조회 오류 ({handle}): {e}")
            return None
