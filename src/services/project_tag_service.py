# -*- coding: utf-8 -*-
"""
프로젝트 태그 서비스

메시지와 TODO에서 프로젝트 정보를 자동으로 추출하고 태그를 생성하는 서비스입니다.
"""
import re
import logging
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ProjectTag:
    """프로젝트 태그 정보"""
    code: str  # 프로젝트 약어 (예: "CARE", "HEAL", "WC", "WD")
    name: str  # 프로젝트 전체 이름
    color: str  # 태그 색상 (hex)
    description: str = ""  # 프로젝트 설명


class ProjectTagService:
    """프로젝트 태그 서비스"""
    
    def __init__(self, vdos_connector=None):
        self.vdos_connector = vdos_connector
        self.project_tags = {}
        self.person_project_mapping = {}  # 사람별 프로젝트 매핑
        self.vdos_db_path = None  # VDOS 데이터베이스 경로
        self._load_projects_from_vdos()
    
    def _load_projects_from_vdos(self):
        """VDOS 데이터베이스에서 프로젝트 정보 로드"""
        try:
            # VDOS 데이터베이스 직접 접근
            self._load_projects_from_vdos_db()
            
        except Exception as e:
            logger.error(f"❌ VDOS 프로젝트 로드 실패: {e}")
            self._load_default_projects()
    
    def _load_projects_from_vdos_db(self):
        """VDOS 데이터베이스 파일에서 직접 프로젝트 정보 로드"""
        import sqlite3
        import os
        from pathlib import Path
        
        # VDOS 데이터베이스 경로 찾기 (더 많은 경로 시도)
        current_dir = Path(__file__).parent
        possible_paths = [
            # 현재 프로젝트 기준
            current_dir / "../../../virtualoffice/src/virtualoffice/vdos.db",
            current_dir / "../../virtualoffice/src/virtualoffice/vdos.db", 
            current_dir / "../virtualoffice/src/virtualoffice/vdos.db",
            current_dir / "../virtualoffice/vdos.db",
            # 절대 경로 시도
            Path("../virtualoffice/src/virtualoffice/vdos.db"),
            Path("../../virtualoffice/src/virtualoffice/vdos.db"),
            Path("../virtualoffice/vdos.db"),
            # 환경 변수나 설정에서 가져오기
        ]
        
        # VDOS 연결자가 있으면 경로 가져오기
        if hasattr(self, 'vdos_connector') and self.vdos_connector:
            try:
                vdos_path = self.vdos_connector.get_vdos_db_path()
                if vdos_path:
                    possible_paths.insert(0, Path(vdos_path))
            except Exception as e:
                logger.debug(f"VDOS 연결자에서 경로 가져오기 실패: {e}")
        
        vdos_db_path = None
        for path in possible_paths:
            try:
                if path.exists():
                    vdos_db_path = str(path.resolve())
                    break
            except Exception:
                continue
        
        if not vdos_db_path:
            logger.warning("VDOS 데이터베이스를 찾을 수 없어 기본 프로젝트 태그 사용")
            self._load_default_projects()
            return
        
        logger.info(f"VDOS 데이터베이스 발견: {vdos_db_path}")
        self.vdos_db_path = vdos_db_path
        
        conn = sqlite3.connect(vdos_db_path)
        cur = conn.cursor()
        
        try:
            # 프로젝트 정보 조회
            cur.execute("""
                SELECT id, project_name, project_summary 
                FROM project_plans 
                ORDER BY id
            """)
            projects = cur.fetchall()
            
            # 프로젝트-사람 매핑 조회 (올바른 컬럼명 사용)
            cur.execute("""
                SELECT pp.id, pp.project_name, p.name, p.email_address, pa.project_id as role
                FROM project_plans pp
                JOIN project_assignments pa ON pp.id = pa.project_id
                JOIN people p ON pa.person_id = p.id
                ORDER BY pp.id, p.name
            """)
            assignments = cur.fetchall()
            
            # 프로젝트 태그 생성
            for project_id, project_name, project_summary in projects:
                project_code = self._extract_project_code_from_name(project_name)
                
                self.project_tags[project_code] = ProjectTag(
                    code=project_code,
                    name=project_name,
                    color=self._get_project_color(project_code),
                    description=project_summary or ""
                )
            
            # 사람별 프로젝트 매핑 생성
            for project_id, project_name, person_name, email, role in assignments:
                project_code = self._extract_project_code_from_name(project_name)
                
                # 이메일로 매핑
                if email and email not in self.person_project_mapping:
                    self.person_project_mapping[email] = []
                if email:
                    self.person_project_mapping[email].append(project_code)
                
                # 이름으로도 매핑
                if person_name and person_name not in self.person_project_mapping:
                    self.person_project_mapping[person_name] = []
                if person_name:
                    self.person_project_mapping[person_name].append(project_code)
            
            logger.info(f"✅ VDOS에서 {len(self.project_tags)}개 프로젝트 로드 완료")
            logger.info(f"✅ {len(self.person_project_mapping)}개 사람-프로젝트 매핑 생성")
            
            # VDOS 프로젝트만 사용 (기본 프로젝트 추가 비활성화)
            # self._ensure_all_projects_loaded()
            
        finally:
            conn.close()
    
    def _extract_project_code_from_name(self, project_name: str) -> str:
        """프로젝트 이름에서 실제 프로젝트 코드 추출 (동적 생성)"""
        # 기본 약어 생성 로직 사용 (하드코딩 제거)
        return self._generate_project_code(project_name)
    
    def _generate_project_code(self, project_name: str) -> str:
        """프로젝트 이름에서 약어 생성"""
        # 영어 단어들 추출
        import re
        english_words = re.findall(r'[A-Za-z]+', project_name)
        
        if len(english_words) >= 2:
            # 첫 두 단어의 첫 글자
            return ''.join(word[0].upper() for word in english_words[:2])
        elif len(english_words) == 1:
            # 한 단어면 첫 4글자
            return english_words[0][:4].upper()
        else:
            # 영어가 없으면 한글에서 추출
            korean_words = re.findall(r'[가-힣]+', project_name)
            if korean_words:
                # 첫 번째 한글 단어의 첫 2글자
                return korean_words[0][:2].upper()
            else:
                # 그것도 없으면 숫자 기반
                return f"P{hash(project_name) % 1000:03d}"
    
    def _get_project_color(self, project_code: str) -> str:
        """프로젝트 코드에 따른 색상 반환 (동적 생성)"""
        # 색상 팔레트 (순환 사용)
        color_palette = [
            "#3B82F6",  # 파란색
            "#EF4444",  # 빨간색
            "#10B981",  # 녹색
            "#F59E0B",  # 주황색
            "#8B5CF6",  # 보라색
            "#EC4899",  # 핑크색
            "#06B6D4",  # 청록색
            "#F97316",  # 진한 주황색
            "#14B8A6",  # 틸색
            "#A855F7",  # 진한 보라색
        ]
        
        # 프로젝트 코드의 해시값으로 색상 선택 (일관성 유지)
        color_index = hash(project_code) % len(color_palette)
        return color_palette[color_index]
    
    def _load_default_projects(self):
        """기본 프로젝트 태그 로드 (VDOS 연결 실패 시)
        
        VDOS DB를 찾을 수 없을 때만 사용되는 최소한의 폴백입니다.
        실제 프로젝트는 VDOS DB에서 동적으로 로드됩니다.
        """
        self.project_tags = {}
        logger.warning("⚠️ VDOS DB를 찾을 수 없어 빈 프로젝트 목록으로 시작합니다.")
        logger.info("프로젝트는 TODO 분석 시 동적으로 생성됩니다.")
    
    def _ensure_all_projects_loaded(self):
        """VDOS에서 로드되지 않은 프로젝트들을 기본 프로젝트로 추가
        
        이 메서드는 더 이상 사용되지 않습니다.
        모든 프로젝트는 VDOS DB에서 동적으로 로드됩니다.
        """
        # 하드코딩된 프로젝트 추가 비활성화
        logger.debug("_ensure_all_projects_loaded() 호출됨 (비활성화됨)")
        return 0
    
    def extract_project_from_message(self, message: Dict) -> Optional[str]:
        """메시지에서 프로젝트 코드 추출 (LLM 기반 지능 분류)
        
        Args:
            message: 메시지 데이터
            
        Returns:
            프로젝트 코드 (예: "CARE", "BRIDGE") 또는 None
        """
        try:
            # 1. 명시적 프로젝트명 확인
            explicit_project = self._extract_explicit_project(message)
            if explicit_project:
                logger.info(f"[프로젝트 태그] 명시적 프로젝트 발견: {explicit_project}")
                return explicit_project
            
            # 2. 발신자 기반 프로젝트 매핑 확인
            sender_project = self._extract_project_by_sender(message)
            if sender_project:
                logger.info(f"[프로젝트 태그] 발신자 기반 프로젝트: {sender_project}")
                return sender_project
            
            # 3. LLM 기반 지능 분류
            llm_project = self._extract_project_by_llm(message)
            if llm_project:
                logger.info(f"[프로젝트 태그] LLM 분류 결과: {llm_project}")
                return llm_project
            
            logger.debug("[프로젝트 태그] 프로젝트를 식별할 수 없음")
            return None
            
        except Exception as e:
            logger.error(f"프로젝트 추출 오류: {e}")
            return None
    
    def _extract_explicit_project(self, message: Dict) -> Optional[str]:
        """메시지에서 명시적으로 언급된 프로젝트명 추출 (동적 매칭)"""
        content = message.get("content", "")
        subject = message.get("subject", "")
        text = f"{subject} {content}".lower()
        
        # 현재 로드된 모든 프로젝트에 대해 패턴 매칭
        for project_code, project_tag in self.project_tags.items():
            # 프로젝트 이름의 다양한 변형 생성
            project_name_lower = project_tag.name.lower()
            
            # 기본 패턴들
            patterns = [
                project_name_lower,  # 전체 이름
                project_code.lower(),  # 코드
                f"[{project_name_lower}]",  # 대괄호 포함
                project_name_lower.replace(" ", ""),  # 공백 제거
            ]
            
            # 숫자 버전 패턴 추가 (예: "Project 2.0", "Project 2")
            if any(char.isdigit() for char in project_name_lower):
                patterns.append(project_name_lower.split()[0])  # 첫 단어만
            
            # 패턴 매칭
            for pattern in patterns:
                if pattern and pattern in text:
                    logger.info(f"[프로젝트 태그] 명시적 패턴 매칭: '{pattern}' → {project_code}")
                    return project_code
        
        return None
    
    def _extract_project_by_sender(self, message: Dict) -> Optional[str]:
        """발신자 정보로 프로젝트 추출"""
        sender_email = message.get("sender_email", "") or message.get("sender", "")
        sender_name = message.get("sender_name", "")
        
        # 이메일로 프로젝트 찾기
        if sender_email and sender_email in self.person_project_mapping:
            projects = self.person_project_mapping[sender_email]
            if projects:
                return projects[0]  # 첫 번째 프로젝트 반환
        
        # 이름으로 프로젝트 찾기
        if sender_name and sender_name in self.person_project_mapping:
            projects = self.person_project_mapping[sender_name]
            if projects:
                return projects[0]
        
        return None
    
    def _extract_project_by_llm(self, message: Dict) -> Optional[str]:
        """LLM을 사용하여 메시지 내용으로 프로젝트 분류"""
        try:
            # 메시지 내용 준비
            content = message.get("content", "")
            subject = message.get("subject", "")
            sender = message.get("sender", "")
            
            if not content and not subject:
                return None
            
            # 기존 LLM 서비스 사용 (Top3Service와 동일한 방식)
            response_text = self._call_existing_llm_service(message)
            
            if response_text and response_text.strip().upper() in self.project_tags:
                return response_text.strip().upper()
            
            return None
            
        except Exception as e:
            logger.error(f"LLM 프로젝트 분류 오류: {e}")
            return None
    
    def _call_existing_llm_service(self, message: Dict) -> Optional[str]:
        """기존 LLM 서비스를 사용하여 프로젝트 분류"""
        try:
            # Top3Service와 동일한 LLM 호출 방식 사용
            from src.services.top3_service import Top3Service
            
            # 프로젝트 정보 준비
            project_info = []
            for code, tag in self.project_tags.items():
                project_info.append(f"- {code}: {tag.name} ({tag.description})")
            
            projects_text = "\n".join(project_info)
            
            # 메시지 내용 준비
            content = message.get("content", "")
            subject = message.get("subject", "")
            sender = message.get("sender", "")
            
            # LLM 프롬프트 구성
            system_prompt = f"""당신은 업무 메시지를 분석하여 관련 프로젝트를 분류하는 전문가입니다.

다음 프로젝트들 중에서 메시지 내용과 가장 관련있는 프로젝트를 선택하세요:

{projects_text}

응답은 반드시 프로젝트 코드만 반환하세요 (예: CARE, BRIDGE, HEAL 등).
관련 프로젝트가 명확하지 않으면 'UNKNOWN'을 반환하세요."""

            user_prompt = f"""다음 메시지를 분석하여 관련 프로젝트를 분류해주세요:

발신자: {sender}
제목: {subject}
내용: {content[:1000]}

프로젝트 코드만 반환하세요."""

            # Top3Service의 LLM 호출 방식 사용
            if hasattr(self, 'vdos_connector') and self.vdos_connector:
                try:
                    # VDOS 연결을 통한 LLM 호출
                    response = self.vdos_connector.call_llm_api(
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        max_tokens=50,
                        temperature=0.1
                    )
                    
                    if response and response.strip():
                        return response.strip().upper()
                        
                except Exception as e:
                    logger.debug(f"VDOS LLM 호출 실패, 폴백 시도: {e}")
            
            # 폴백: 직접 LLM API 호출
            return self._call_llm_api_fallback(system_prompt, user_prompt)
            
        except Exception as e:
            logger.error(f"기존 LLM 서비스 호출 오류: {e}")
            return None
    
    def _call_llm_api_fallback(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        """LLM API 폴백 호출 (기존 설정 사용)"""
        try:
            # 기존 LLM 설정 파일 시도
            try:
                from config.llm_config import LLM_CONFIG
                import requests
                import json
                
                provider = LLM_CONFIG.get("provider", "azure").lower()
                
                # API 설정
                if provider == "azure":
                    url = f"{LLM_CONFIG['azure']['endpoint']}/openai/deployments/{LLM_CONFIG['azure']['deployment']}/chat/completions?api-version={LLM_CONFIG['azure']['api_version']}"
                    headers = {
                        "Content-Type": "application/json",
                        "api-key": LLM_CONFIG['azure']['api_key']
                    }
                elif provider == "openai":
                    url = "https://api.openai.com/v1/chat/completions"
                    headers = {
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {LLM_CONFIG['openai']['api_key']}"
                    }
                else:
                    logger.debug(f"지원하지 않는 LLM 제공자: {provider}")
                    return None
                
                # 요청 페이로드
                payload = {
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "max_tokens": 50,
                    "temperature": 0.1
                }
                
                if provider == "openai":
                    payload["model"] = LLM_CONFIG['openai'].get('model', 'gpt-4')
                
                # API 호출
                response = requests.post(url, headers=headers, json=payload, timeout=30)
                response.raise_for_status()
                
                result = response.json()
                content = result['choices'][0]['message']['content'].strip()
                
                logger.debug(f"[프로젝트 태그] LLM 폴백 응답: {content}")
                return content
                
            except ImportError:
                logger.debug("LLM 설정 파일이 없어 프로젝트 분류 건너뜀")
                return None
            
        except Exception as e:
            logger.debug(f"LLM API 폴백 호출 오류: {e}")
            return None
    
    def get_available_projects(self) -> Dict[str, ProjectTag]:
        """사용 가능한 프로젝트 태그 반환"""
        return self.project_tags.copy()
    
    def get_project_color(self, project_code: str) -> str:
        """프로젝트 코드의 색상 반환"""
        if project_code in self.project_tags:
            return self.project_tags[project_code].color
        return "#6B7280"  # 기본 회색
    
    def get_project_tag(self, project_code: str) -> Optional[ProjectTag]:
        """프로젝트 코드로 ProjectTag 객체 반환"""
        return self.project_tags.get(project_code)
    
    def add_project_dynamically(self, project_name: str, project_description: str = "") -> str:
        """동적으로 새 프로젝트 추가
        
        Args:
            project_name: 프로젝트 이름
            project_description: 프로젝트 설명
            
        Returns:
            생성된 프로젝트 코드
        """
        project_code = self._generate_project_code(project_name)
        
        # 이미 존재하는 코드면 숫자 추가
        original_code = project_code
        counter = 1
        while project_code in self.project_tags:
            project_code = f"{original_code}{counter}"
            counter += 1
        
        # 새 프로젝트 태그 생성
        color = self._get_project_color(project_code)
        self.project_tags[project_code] = ProjectTag(
            code=project_code,
            name=project_name,
            color=color,
            description=project_description
        )
        
        logger.info(f"✅ 새 프로젝트 동적 추가: {project_code} ({project_name})")
        return project_code
    
    def reload_projects_from_vdos(self):
        """VDOS DB에서 프로젝트 재로드
        
        데이터베이스가 업데이트된 후 호출하여 프로젝트 목록을 갱신합니다.
        """
        logger.info("🔄 VDOS DB에서 프로젝트 재로드 중...")
        self.project_tags.clear()
        self.person_project_mapping.clear()
        self._load_projects_from_vdos()
        logger.info(f"✅ 프로젝트 재로드 완료: {len(self.project_tags)}개")