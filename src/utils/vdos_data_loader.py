#!/usr/bin/env python3
"""
VDOS 데이터 로더 - 페르소나 파일에서 프로젝트 정보 추출
"""
import json
import os
import logging
from typing import Dict, List, Set, Optional, Tuple
from pathlib import Path
from datetime import datetime
import re
from collections import defaultdict, Counter

logger = logging.getLogger(__name__)

class VDOSDataLoader:
    """VDOS 페르소나 파일에서 프로젝트 정보를 추출하는 클래스"""
    
    def __init__(self, data_dir: str = "offline_agent/data/multi_project_8week_ko"):
        """
        Args:
            data_dir: VDOS 데이터가 있는 디렉토리 경로
        """
        self.data_dir = Path(data_dir)
        self.personas_data: Dict = {}
        self.projects: Dict[str, Dict] = {}
        self.persona_project_mapping: Dict[str, List[str]] = {}
        self.project_keywords: Dict[str, Set[str]] = {}
        self.last_loaded: Optional[datetime] = None
        
        # 프로젝트 관련 키워드 패턴
        self.project_keywords_patterns = [
            r'앱\s*개발', r'모바일\s*앱', r'애플리케이션',
            r'백엔드', r'인프라', r'시스템',
            r'AI\s*서비스', r'데이터\s*파이프라인', r'ETL',
            r'테스트\s*자동화', r'QA', r'품질\s*관리',
            r'UI/UX', r'디자인', r'프로토타입',
            r'데브옵스', r'AWS', r'Docker', r'Kubernetes'
        ]
    
    def find_persona_files(self) -> List[Path]:
        """VDOS 페르소나 파일들을 찾아 반환"""
        persona_files = []
        
        # vdos-personas로 시작하는 JSON 파일들 찾기
        for file_path in self.data_dir.glob("vdos-personas*.json"):
            if file_path.is_file():
                persona_files.append(file_path)
        
        # 최신 파일 순으로 정렬
        persona_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        logger.info(f"발견된 페르소나 파일: {len(persona_files)}개")
        for file_path in persona_files:
            logger.debug(f"  - {file_path.name}")
        
        return persona_files  
  
    def load_personas_data(self, file_path: Optional[Path] = None) -> bool:
        """
        페르소나 데이터를 로드합니다
        
        Args:
            file_path: 특정 파일 경로 (None이면 최신 파일 사용)
            
        Returns:
            로드 성공 여부
        """
        try:
            if file_path is None:
                persona_files = self.find_persona_files()
                if not persona_files:
                    logger.error("페르소나 파일을 찾을 수 없습니다")
                    return False
                file_path = persona_files[0]  # 최신 파일 사용
            
            logger.info(f"페르소나 데이터 로드 중: {file_path.name}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if 'personas' not in data:
                logger.error("페르소나 데이터 형식이 올바르지 않습니다")
                return False
            
            self.personas_data = data
            self.last_loaded = datetime.now()
            
            logger.info(f"페르소나 {len(data['personas'])}개 로드 완료")
            return True
            
        except Exception as e:
            logger.error(f"페르소나 데이터 로드 실패: {e}")
            return False
    
    def extract_projects(self) -> Dict[str, Dict]:
        """페르소나 데이터에서 프로젝트 정보를 추출합니다"""
        if not self.personas_data:
            logger.warning("페르소나 데이터가 로드되지 않았습니다")
            return {}
        
        projects = {}
        team_members = defaultdict(list)
        
        # 팀별로 페르소나 그룹화
        for persona in self.personas_data.get('personas', []):
            team_name = persona.get('team_name', '').strip()
            if team_name:
                team_members[team_name].append(persona)
        
        # 각 팀을 프로젝트로 변환
        for team_name, members in team_members.items():
            project_info = self._create_project_from_team(team_name, members)
            projects[team_name] = project_info
        
        self.projects = projects
        logger.info(f"추출된 프로젝트: {len(projects)}개")
        
        return projects 
   
    def _create_project_from_team(self, team_name: str, members: List[Dict]) -> Dict:
        """팀 정보에서 프로젝트 정보를 생성합니다"""
        
        # 팀장 찾기
        team_lead = None
        for member in members:
            if member.get('is_department_head', False):
                team_lead = member
                break
        
        # 스킬 집계
        all_skills = []
        for member in members:
            all_skills.extend(member.get('skills', []))
        skill_counts = Counter(all_skills)
        
        # 목표 집계
        all_objectives = []
        for member in members:
            all_objectives.extend(member.get('objectives', []))
        
        # 프로젝트 설명 생성
        description_parts = []
        if team_lead:
            description_parts.append(f"{team_lead['name']}이 이끄는 {team_name}")
        else:
            description_parts.append(team_name)
        
        # 주요 스킬 추가
        top_skills = [skill for skill, count in skill_counts.most_common(5)]
        if top_skills:
            description_parts.append(f"주요 기술: {', '.join(top_skills)}")
        
        # 주요 목표 추가
        if all_objectives:
            unique_objectives = list(set(all_objectives))[:3]
            description_parts.append(f"목표: {', '.join(unique_objectives)}")
        
        project_info = {
            'name': team_name,
            'description': '. '.join(description_parts),
            'team_lead': team_lead['name'] if team_lead else None,
            'team_lead_email': team_lead['email_address'] if team_lead else None,
            'members': [
                {
                    'name': member['name'],
                    'role': member['role'],
                    'email': member['email_address'],
                    'chat_handle': member['chat_handle']
                }
                for member in members
            ],
            'skills': list(skill_counts.keys()),
            'objectives': list(set(all_objectives)),
            'member_count': len(members)
        }
        
        return project_info
    
    def extract_project_keywords(self) -> Dict[str, Set[str]]:
        """각 프로젝트별 키워드를 추출합니다"""
        if not self.projects:
            logger.warning("프로젝트 정보가 없습니다")
            return {}
        
        project_keywords = {}
        
        for project_name, project_info in self.projects.items():
            keywords = set()
            
            # 프로젝트명에서 키워드 추출
            keywords.update(self._extract_keywords_from_text(project_name))
            
            # 설명에서 키워드 추출
            keywords.update(self._extract_keywords_from_text(project_info['description']))
            
            # 스킬에서 키워드 추출
            for skill in project_info.get('skills', []):
                keywords.update(self._extract_keywords_from_text(skill))
            
            # 목표에서 키워드 추출
            for objective in project_info.get('objectives', []):
                keywords.update(self._extract_keywords_from_text(objective))
            
            project_keywords[project_name] = keywords
        
        self.project_keywords = project_keywords
        logger.info(f"프로젝트별 키워드 추출 완료")
        
        return project_keywords 
   
    def _extract_keywords_from_text(self, text: str) -> Set[str]:
        """텍스트에서 키워드를 추출합니다"""
        if not text:
            return set()
        
        keywords = set()
        text_lower = text.lower()
        
        # 패턴 기반 키워드 추출
        for pattern in self.project_keywords_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # 공백 정규화
                normalized = re.sub(r'\s+', ' ', match.strip())
                if normalized:
                    keywords.add(normalized)
        
        # 단어 분할 및 필터링
        words = re.findall(r'\b\w+\b', text)
        for word in words:
            word = word.strip()
            if len(word) >= 2:  # 2글자 이상
                # 기술 용어나 중요한 단어 추가
                if any(tech in word.lower() for tech in [
                    'api', 'ui', 'ux', 'aws', 'sql', 'etl', 'qa', 'ai',
                    'docker', 'kubernetes', 'python', 'javascript', 'react'
                ]):
                    keywords.add(word)
                # 한글 단어 (2글자 이상)
                elif re.match(r'^[가-힣]{2,}$', word):
                    keywords.add(word)
        
        return keywords
    
    def create_persona_project_mapping(self) -> Dict[str, List[str]]:
        """페르소나별 담당 프로젝트 매핑을 생성합니다"""
        if not self.personas_data or not self.projects:
            logger.warning("페르소나 데이터나 프로젝트 정보가 없습니다")
            return {}
        
        mapping = {}
        
        for persona in self.personas_data.get('personas', []):
            persona_name = persona.get('name', '')
            persona_email = persona.get('email_address', '')
            team_name = persona.get('team_name', '')
            
            # 해당 페르소나가 속한 프로젝트들 찾기
            projects = []
            
            # 직접 팀 매핑
            if team_name and team_name in self.projects:
                projects.append(team_name)
            
            # 이메일 기반 매핑 (추가 검증)
            for project_name, project_info in self.projects.items():
                for member in project_info.get('members', []):
                    if member.get('email') == persona_email:
                        if project_name not in projects:
                            projects.append(project_name)
            
            if projects:
                mapping[persona_name] = projects
                mapping[persona_email] = projects  # 이메일로도 매핑
        
        self.persona_project_mapping = mapping
        logger.info(f"페르소나-프로젝트 매핑 생성 완료: {len(mapping)}개")
        
        return mapping
    
    def get_project_info(self, project_name: str) -> Optional[Dict]:
        """특정 프로젝트 정보를 반환합니다"""
        return self.projects.get(project_name)
    
    def get_persona_projects(self, persona_identifier: str) -> List[str]:
        """페르소나가 담당하는 프로젝트 목록을 반환합니다"""
        return self.persona_project_mapping.get(persona_identifier, [])
    
    def get_project_keywords(self, project_name: str) -> Set[str]:
        """특정 프로젝트의 키워드를 반환합니다"""
        return self.project_keywords.get(project_name, set())
    
    def reload_if_changed(self) -> bool:
        """파일이 변경되었으면 다시 로드합니다"""
        persona_files = self.find_persona_files()
        if not persona_files:
            return False
        
        latest_file = persona_files[0]
        latest_mtime = datetime.fromtimestamp(latest_file.stat().st_mtime)
        
        if self.last_loaded is None or latest_mtime > self.last_loaded:
            logger.info("페르소나 파일이 변경되어 다시 로드합니다")
            return self.load_and_extract_all(latest_file)
        
        return True    

    def load_and_extract_all(self, file_path: Optional[Path] = None) -> bool:
        """모든 데이터를 로드하고 추출합니다"""
        try:
            # 1. 페르소나 데이터 로드
            if not self.load_personas_data(file_path):
                return False
            
            # 2. 프로젝트 정보 추출
            self.extract_projects()
            
            # 3. 프로젝트 키워드 추출
            self.extract_project_keywords()
            
            # 4. 페르소나-프로젝트 매핑 생성
            self.create_persona_project_mapping()
            
            logger.info("VDOS 데이터 로드 및 추출 완료")
            return True
            
        except Exception as e:
            logger.error(f"데이터 로드 및 추출 실패: {e}")
            return False
    
    def get_summary(self) -> Dict:
        """로드된 데이터의 요약 정보를 반환합니다"""
        return {
            'personas_count': len(self.personas_data.get('personas', [])),
            'projects_count': len(self.projects),
            'total_keywords': sum(len(keywords) for keywords in self.project_keywords.values()),
            'mappings_count': len(self.persona_project_mapping),
            'last_loaded': self.last_loaded.isoformat() if self.last_loaded else None,
            'projects': list(self.projects.keys()),
            'sample_keywords': {
                project: list(keywords)[:5] 
                for project, keywords in self.project_keywords.items()
            }
        }


# 편의 함수들
def load_vdos_data(data_dir: str = "offline_agent/data/multi_project_8week_ko") -> VDOSDataLoader:
    """VDOS 데이터를 로드하고 VDOSDataLoader 인스턴스를 반환합니다"""
    loader = VDOSDataLoader(data_dir)
    loader.load_and_extract_all()
    return loader


def get_project_for_persona(persona_identifier: str, 
                          data_dir: str = "offline_agent/data/multi_project_8week_ko") -> List[str]:
    """특정 페르소나의 담당 프로젝트를 반환합니다"""
    loader = load_vdos_data(data_dir)
    return loader.get_persona_projects(persona_identifier)


if __name__ == "__main__":
    # 테스트 실행
    logging.basicConfig(level=logging.INFO)
    
    loader = VDOSDataLoader()
    if loader.load_and_extract_all():
        summary = loader.get_summary()
        print("=== VDOS 데이터 로더 테스트 ===")
        print(f"페르소나 수: {summary['personas_count']}")
        print(f"프로젝트 수: {summary['projects_count']}")
        print(f"총 키워드 수: {summary['total_keywords']}")
        print(f"매핑 수: {summary['mappings_count']}")
        print(f"\n프로젝트 목록:")
        for project in summary['projects']:
            print(f"  - {project}")
        print(f"\n샘플 키워드:")
        for project, keywords in summary['sample_keywords'].items():
            print(f"  {project}: {', '.join(keywords)}")
    else:
        print("데이터 로드 실패")