#!/usr/bin/env python3
"""
VDOS 데이터베이스 연동 시스템

VDOS의 SQLite 데이터베이스에서 프로젝트 및 페르소나 정보를 추출하여
프로젝트 태그 시스템에서 사용할 수 있는 형태로 변환합니다.
"""

import sqlite3
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import re

logger = logging.getLogger(__name__)

@dataclass
class ProjectInfo:
    """프로젝트 정보 데이터 클래스"""
    id: int
    name: str
    summary: str
    participants: List[Dict[str, str]]  # [{"name": "이름", "role": "역할", "email": "이메일"}]
    keywords: List[str]  # 프로젝트명에서 추출한 키워드
    
    def get_short_name(self) -> str:
        """프로젝트 축약명 생성"""
        # 영문 대문자와 한글 첫 글자 추출
        words = re.findall(r'[A-Z][a-z]*|[가-힣]+', self.name)
        if len(words) >= 2:
            return ''.join(word[0].upper() if word[0].isalpha() else word[0] for word in words[:3])
        elif len(words) == 1:
            return words[0][:3].upper()
        else:
            return self.name[:3]

@dataclass
class PersonaInfo:
    """페르소나 정보 데이터 클래스"""
    id: int
    name: str
    email: str
    chat_handle: str
    role: str
    projects: List[int]  # 참여 프로젝트 ID 목록

class VDOSDBConnector:
    """VDOS 데이터베이스 연동 클래스"""
    
    def __init__(self, db_path: str = None):
        """
        VDOSDBConnector 초기화
        
        Args:
            db_path: VDOS 데이터베이스 파일 경로
        """
        self._projects_cache: Optional[Dict[int, ProjectInfo]] = None
        self._personas_cache: Optional[Dict[int, PersonaInfo]] = None
        
        # 에러 처리: 여러 경로에서 VDOS DB 찾기
        if db_path:
            possible_paths = [Path(db_path)]
        else:
            # 현재 작업 디렉토리 기준으로 여러 경로 시도
            current_dir = Path.cwd()
            possible_paths = [
                current_dir / "virtualoffice" / "src" / "virtualoffice" / "vdossnapshot.db",
                current_dir / "virtualoffice" / "src" / "virtualoffice" / "vdos.db",
                current_dir / ".." / "virtualoffice" / "src" / "virtualoffice" / "vdossnapshot.db",
                current_dir / ".." / "virtualoffice" / "src" / "virtualoffice" / "vdos.db",
                current_dir / ".." / ".." / "virtualoffice" / "src" / "virtualoffice" / "vdossnapshot.db",
                current_dir / ".." / ".." / "virtualoffice" / "src" / "virtualoffice" / "vdos.db",
                Path("virtualoffice/src/virtualoffice/vdossnapshot.db"),
                Path("virtualoffice/src/virtualoffice/vdos.db"),
                Path("../virtualoffice/src/virtualoffice/vdossnapshot.db"),
                Path("../virtualoffice/src/virtualoffice/vdos.db"),
                Path("../../virtualoffice/src/virtualoffice/vdossnapshot.db"),
                Path("../../virtualoffice/src/virtualoffice/vdos.db"),
                Path("virtualoffice/vdossnapshot.db"),
                Path("virtualoffice/vdos.db")
            ]
        
        db_found = False
        for path in possible_paths:
            if path.exists():
                self.db_path = path.resolve()  # 절대 경로로 변환
                db_found = True
                logger.info(f"VDOS DB 발견: {self.db_path}")
                break
        
        if not db_found:
            # 경고만 출력하고 계속 진행 (오프라인 모드)
            logger.warning(f"VDOS 데이터베이스 파일을 찾을 수 없습니다. 오프라인 모드로 동작합니다.")
            self.db_path = None
        
        logger.info(f"VDOS DB 연결 초기화: {self.db_path}")
    
    def _get_connection(self) -> sqlite3.Connection:
        """데이터베이스 연결 생성"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as e:
            from utils.project_tags_error_handler import VDOSConnectionError
            raise VDOSConnectionError(f"VDOS DB 연결 실패: {e}")
    
    def get_projects(self, force_reload: bool = False) -> Dict[int, ProjectInfo]:
        """
        모든 프로젝트 정보 조회
        
        Args:
            force_reload: 캐시 무시하고 강제 재로드
            
        Returns:
            프로젝트 ID를 키로 하는 ProjectInfo 딕셔너리
        """
        if self._projects_cache is not None and not force_reload:
            return self._projects_cache
        
        logger.info("VDOS DB에서 프로젝트 정보 로드 중...")
        
        projects = {}
        
        try:
            with self._get_connection() as conn:
                # 프로젝트 기본 정보 조회
                cursor = conn.execute("""
                    SELECT id, project_name, project_summary
                    FROM project_plans
                    ORDER BY id
                """)
                
                for row in cursor:
                    project_id = row['id']
                    project_name = row['project_name'] or f"프로젝트 {project_id}"
                    project_summary = row['project_summary'] or ""
                    
                    # 프로젝트 참여자 조회
                    participants = self._get_project_participants(conn, project_id)
                    
                    # 키워드 추출
                    keywords = self._extract_keywords_from_name(project_name)
                    
                    projects[project_id] = ProjectInfo(
                        id=project_id,
                        name=project_name,
                        summary=project_summary,
                        participants=participants,
                        keywords=keywords
                    )
                
                logger.info(f"프로젝트 {len(projects)}개 로드 완료")
                self._projects_cache = projects
                
        except Exception as e:
            logger.error(f"프로젝트 정보 로드 실패: {e}")
            raise
        
        return projects
    
    def _get_project_participants(self, conn: sqlite3.Connection, project_id: int) -> List[Dict[str, str]]:
        """특정 프로젝트의 참여자 목록 조회"""
        cursor = conn.execute("""
            SELECT p.name, p.email_address, p.chat_handle, p.role
            FROM project_assignments pa
            JOIN people p ON pa.person_id = p.id
            WHERE pa.project_id = ?
            ORDER BY p.name
        """, (project_id,))
        
        participants = []
        for row in cursor:
            participants.append({
                "name": row['name'],
                "email": row['email_address'],
                "chat_handle": row['chat_handle'],
                "role": row['role']
            })
        
        return participants
    
    def _extract_keywords_from_name(self, project_name: str) -> List[str]:
        """
        프로젝트명에서 키워드 추출 (개선된 버전)
        
        Args:
            project_name: 프로젝트명
            
        Returns:
            추출된 키워드 목록
        """
        keywords = []
        
        # 1. 프로젝트명 전체를 키워드로 추가
        keywords.append(project_name.lower())
        
        # 2. 영문 단어, 한글 단어, 숫자 등을 추출
        words = re.findall(r'[A-Za-z]+|[가-힣]+|[0-9]+\.?[0-9]*', project_name)
        
        for word in words:
            # 의미있는 단어만 키워드로 사용 (2글자 이상)
            if len(word) >= 2:
                keywords.append(word.lower())
        
        # 3. 특수 패턴 처리
        # "2.0", "v1.0" 등의 버전 정보
        version_patterns = re.findall(r'v?\d+\.\d+', project_name.lower())
        keywords.extend(version_patterns)
        
        # 4. 브랜드명/제품명 추출 (대문자로 시작하는 연속된 단어)
        brand_patterns = re.findall(r'[A-Z][a-z]+(?:[A-Z][a-z]+)*', project_name)
        for brand in brand_patterns:
            if len(brand) >= 3:
                keywords.append(brand.lower())
        
        # 5. 한글 복합어 분리 (간단한 휴리스틱)
        korean_words = re.findall(r'[가-힣]+', project_name)
        for korean_word in korean_words:
            if len(korean_word) >= 4:  # 4글자 이상인 경우 분리 시도
                # 일반적인 접미사 분리
                suffixes = ['시스템', '플랫폼', '서비스', '솔루션', '프로젝트', '캠페인', '런칭']
                for suffix in suffixes:
                    if korean_word.endswith(suffix) and len(korean_word) > len(suffix):
                        base_word = korean_word[:-len(suffix)]
                        if len(base_word) >= 2:
                            keywords.append(base_word)
                            keywords.append(suffix)
        
        # 6. 영문 약어 생성 (첫 글자들)
        english_words = re.findall(r'[A-Za-z]+', project_name)
        if len(english_words) >= 2:
            acronym = ''.join(word[0].upper() for word in english_words if len(word) >= 2)
            if len(acronym) >= 2:
                keywords.append(acronym.lower())
        
        return list(set(keywords))  # 중복 제거
    
    def get_personas(self, force_reload: bool = False) -> Dict[int, PersonaInfo]:
        """
        모든 페르소나 정보 조회
        
        Args:
            force_reload: 캐시 무시하고 강제 재로드
            
        Returns:
            페르소나 ID를 키로 하는 PersonaInfo 딕셔너리
        """
        if self._personas_cache is not None and not force_reload:
            return self._personas_cache
        
        logger.info("VDOS DB에서 페르소나 정보 로드 중...")
        
        personas = {}
        
        try:
            with self._get_connection() as conn:
                # 페르소나 기본 정보 조회
                cursor = conn.execute("""
                    SELECT id, name, email_address, chat_handle, role
                    FROM people
                    ORDER BY id
                """)
                
                for row in cursor:
                    person_id = row['id']
                    
                    # 참여 프로젝트 조회
                    project_cursor = conn.execute("""
                        SELECT project_id
                        FROM project_assignments
                        WHERE person_id = ?
                    """, (person_id,))
                    
                    projects = [p_row['project_id'] for p_row in project_cursor]
                    
                    personas[person_id] = PersonaInfo(
                        id=person_id,
                        name=row['name'],
                        email=row['email_address'],
                        chat_handle=row['chat_handle'],
                        role=row['role'],
                        projects=projects
                    )
                
                logger.info(f"페르소나 {len(personas)}개 로드 완료")
                self._personas_cache = personas
                
        except Exception as e:
            logger.error(f"페르소나 정보 로드 실패: {e}")
            raise
        
        return personas
    
    def get_project_by_name(self, project_name: str) -> Optional[ProjectInfo]:
        """프로젝트명으로 프로젝트 정보 조회"""
        projects = self.get_projects()
        
        for project in projects.values():
            if project.name.lower() == project_name.lower():
                return project
        
        return None
    
    def get_projects_by_participant(self, participant_name: str) -> List[ProjectInfo]:
        """참여자명으로 프로젝트 목록 조회"""
        projects = self.get_projects()
        result = []
        
        for project in projects.values():
            for participant in project.participants:
                if participant_name.lower() in participant["name"].lower():
                    result.append(project)
                    break
        
        return result
    
    def get_project_keywords_mapping(self) -> Dict[str, List[int]]:
        """
        키워드별 프로젝트 ID 매핑 생성
        
        Returns:
            키워드를 키로 하고 해당 키워드를 포함하는 프로젝트 ID 목록을 값으로 하는 딕셔너리
        """
        projects = self.get_projects()
        keyword_mapping = {}
        
        for project_id, project in projects.items():
            for keyword in project.keywords:
                if keyword not in keyword_mapping:
                    keyword_mapping[keyword] = []
                keyword_mapping[keyword].append(project_id)
        
        return keyword_mapping
    
    def get_participant_project_mapping(self) -> Dict[str, List[int]]:
        """
        참여자별 프로젝트 ID 매핑 생성 (이름 변형 포함)
        
        Returns:
            참여자명을 키로 하고 참여 프로젝트 ID 목록을 값으로 하는 딕셔너리
        """
        projects = self.get_projects()
        participant_mapping = {}
        
        for project_id, project in projects.items():
            for participant in project.participants:
                name = participant["name"]
                email = participant["email"]
                chat_handle = participant["chat_handle"]
                
                # 1. 전체 이름
                if name not in participant_mapping:
                    participant_mapping[name] = []
                participant_mapping[name].append(project_id)
                
                # 2. 이메일 주소 (@ 앞부분)
                if email and '@' in email:
                    email_prefix = email.split('@')[0]
                    if email_prefix not in participant_mapping:
                        participant_mapping[email_prefix] = []
                    participant_mapping[email_prefix].append(project_id)
                
                # 3. 채팅 핸들 (@ 제거)
                if chat_handle:
                    clean_handle = chat_handle.lstrip('@')
                    if clean_handle not in participant_mapping:
                        participant_mapping[clean_handle] = []
                    participant_mapping[clean_handle].append(project_id)
                
                # 4. 이름 변형 (성+이름, 이름만)
                if len(name) >= 3:  # 한국 이름 가정 (3글자 이상)
                    # 성 제외한 이름 (예: "김철수" → "철수")
                    first_name = name[1:]
                    if first_name not in participant_mapping:
                        participant_mapping[first_name] = []
                    participant_mapping[first_name].append(project_id)
        
        # 중복 제거
        for key in participant_mapping:
            participant_mapping[key] = list(set(participant_mapping[key]))
        
        return participant_mapping
    
    def get_team_project_mapping(self) -> Dict[str, List[int]]:
        """
        팀명 기반 프로젝트 그룹핑
        
        Returns:
            팀명을 키로 하고 관련 프로젝트 ID 목록을 값으로 하는 딕셔너리
        """
        projects = self.get_projects()
        team_mapping = {}
        
        # 역할 기반 팀 분류
        role_teams = {
            'development': ['개발자', 'developer', '풀스택', 'fullstack', '백엔드', 'backend', '프론트엔드', 'frontend', '테크리드', 'techlead'],
            'design': ['디자이너', 'designer', 'ui', 'ux', '브랜드'],
            'marketing': ['마케팅', 'marketing', '마케터', 'marketer', '콘텐츠', 'content'],
            'qa': ['qa', 'qe', '테스트', 'test', '품질'],
            'devops': ['데브옵스', 'devops', '인프라', 'infrastructure'],
            'data': ['데이터', 'data', '분석', 'analytics'],
            'management': ['매니저', 'manager', 'pm', 'cpo', 'cto', '팀장', '리드']
        }
        
        for project_id, project in projects.items():
            project_teams = set()
            
            # 참여자 역할 기반 팀 분류
            for participant in project.participants:
                role = participant["role"].lower()
                
                for team_name, keywords in role_teams.items():
                    if any(keyword in role for keyword in keywords):
                        project_teams.add(team_name)
            
            # 프로젝트명에서 팀 추출
            project_name_lower = project.name.lower()
            for team_name, keywords in role_teams.items():
                if any(keyword in project_name_lower for keyword in keywords):
                    project_teams.add(team_name)
            
            # 팀별 프로젝트 매핑에 추가
            for team in project_teams:
                if team not in team_mapping:
                    team_mapping[team] = []
                team_mapping[team].append(project_id)
        
        return team_mapping
    
    def clear_cache(self):
        """캐시 초기화"""
        self._projects_cache = None
        self._personas_cache = None
        logger.info("VDOS DB 캐시 초기화됨")
    
    def get_database_stats(self) -> Dict[str, int]:
        """데이터베이스 통계 정보 조회"""
        try:
            with self._get_connection() as conn:
                stats = {}
                
                # 프로젝트 수
                cursor = conn.execute("SELECT COUNT(*) as count FROM project_plans")
                stats['projects'] = cursor.fetchone()['count']
                
                # 페르소나 수
                cursor = conn.execute("SELECT COUNT(*) as count FROM people")
                stats['personas'] = cursor.fetchone()['count']
                
                # 프로젝트 할당 수
                cursor = conn.execute("SELECT COUNT(*) as count FROM project_assignments")
                stats['assignments'] = cursor.fetchone()['count']
                
                return stats
                
        except Exception as e:
            logger.error(f"데이터베이스 통계 조회 실패: {e}")
            return {}

# 전역 인스턴스 (싱글톤 패턴)
_vdos_connector: Optional[VDOSDBConnector] = None

def get_vdos_connector(db_path: str = "virtualoffice/src/virtualoffice/vdos.db") -> VDOSDBConnector:
    """VDOS DB 커넥터 싱글톤 인스턴스 반환"""
    global _vdos_connector
    
    if _vdos_connector is None:
        _vdos_connector = VDOSDBConnector(db_path)
    
    return _vdos_connector
