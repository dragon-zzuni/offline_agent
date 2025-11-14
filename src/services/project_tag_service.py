# -*- coding: utf-8 -*-
"""
프로젝트 태그 서비스

메시지와 TODO에서 프로젝트 정보를 자동으로 추출하고 태그를 생성하는 서비스입니다.
"""
import re
import logging
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from utils.project_fullname_mapper import generate_project_code

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
    
    def __init__(self, vdos_connector=None, cache_db_path: str = None):
        self.vdos_connector = vdos_connector
        self.project_tags = {}
        self.person_project_mapping = {}  # 사람별 프로젝트 매핑
        self.project_periods = {}  # 프로젝트별 기간 정보
        self.vdos_db_path = None  # VDOS 데이터베이스 경로
        self.tag_cache = None  # 초기화 후 설정
        self._custom_cache_path = cache_db_path  # 사용자 지정 경로 저장
        
        # VDOS 프로젝트 로드 (vdos_db_path 설정됨)
        self._load_projects_from_vdos()
        
        # 프로젝트 태그 영구 캐시 초기화 (VDOS DB와 같은 위치)
        self._init_cache()
    
    def _init_cache(self):
        """프로젝트 태그 캐시 초기화 (VDOS DB와 같은 위치)"""
        from pathlib import Path
        
        # 사용자 지정 경로가 있으면 사용
        if self._custom_cache_path:
            cache_path = self._custom_cache_path
        # VDOS DB 경로가 있으면 같은 디렉토리에 캐시 생성
        elif self.vdos_db_path:
            vdos_dir = Path(self.vdos_db_path).parent
            cache_path = str(vdos_dir / "project_tags_cache.db")
        else:
            logger.warning("⚠️ 프로젝트 태그 캐시 비활성화 (VDOS DB 경로 없음)")
            return
        
        try:
            from services.project_tag_cache_service import ProjectTagCacheService
            self.tag_cache = ProjectTagCacheService(cache_path)
            logger.info(f"✅ 프로젝트 태그 캐시 활성화: {cache_path}")
        except Exception as e:
            logger.error(f"❌ 프로젝트 태그 캐시 초기화 실패: {e}")
            self.tag_cache = None
    
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
        
        # VDOS 데이터베이스 경로 찾기
        # 작업 디렉토리 기준으로 절대 경로 사용 (상대 경로 문제 방지)
        import os
        workspace_root = Path(os.getcwd())
        
        possible_paths = [
            # 작업 디렉토리 기준 (가장 안전)
            workspace_root / "virtualoffice" / "src" / "virtualoffice" / "vdos.db",
            # 현재 파일 기준 (폴백)
            Path(__file__).resolve().parents[3] / "virtualoffice" / "src" / "virtualoffice" / "vdos.db",
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
            # 프로젝트 정보 조회 (기간 정보 포함)
            cur.execute("""
                SELECT id, project_name, project_summary, duration_weeks, start_week
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
            
            # 프로젝트 태그 생성 (기간 정보 포함)
            self.project_periods = {}  # 프로젝트별 기간 정보 저장
            for project_id, project_name, project_summary, duration_weeks, start_week in projects:
                project_code = self._extract_project_code_from_name(project_name)
                
                self.project_tags[project_code] = ProjectTag(
                    code=project_code,
                    name=project_name,
                    color=self._get_project_color(project_code),
                    description=project_summary or ""
                )
                
                # 기간 정보 저장
                if duration_weeks and start_week:
                    self.project_periods[project_code] = {
                        'start_week': start_week,
                        'end_week': start_week + duration_weeks - 1,
                        'duration_weeks': duration_weeks
                    }
            
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
            
            # "미분류" 태그는 항상 추가 (프로젝트 특정 불가 시 사용)
            if "미분류" not in self.project_tags:
                self.project_tags["미분류"] = ProjectTag(
                    code="미분류",
                    name="미분류",
                    color="#9CA3AF",  # 회색
                    description="프로젝트를 특정할 수 없는 TODO"
                )
                logger.info("✅ '미분류' 태그 추가 완료")
            
            # VDOS 프로젝트만 사용 (기본 프로젝트 추가 비활성화)
            # self._ensure_all_projects_loaded()
            
        finally:
            conn.close()
    
    def _extract_project_code_from_name(self, project_name: str) -> str:
        """프로젝트 이름에서 실제 프로젝트 코드 추출 (동적 생성)"""
        return generate_project_code(project_name)
    
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
        
        # "미분류" 태그는 항상 추가 (프로젝트 특정 불가 시 사용)
        self.project_tags["미분류"] = ProjectTag(
            code="미분류",
            name="미분류",
            color="#9CA3AF",  # 회색
            description="프로젝트를 특정할 수 없는 TODO"
        )
        
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
    
    def extract_project_from_message(self, message: Dict, use_cache: bool = True) -> Optional[str]:
        """메시지에서 프로젝트 코드 추출 (캐시 우선, LLM 기반 지능 분류)
        
        분석 우선순위:
        1. 캐시 조회 (이미 분석된 TODO)
        2. 명시적 프로젝트명 (대괄호 패턴 등)
        3. LLM 기반 내용 분석 (메시지 내용 우선)
        4. 고급 분석 (프로젝트 기간, 설명, 발신자 종합)
        5. 발신자 정보 참고 (폴백, 여러 프로젝트 가능하므로 참고용)
        
        Args:
            message: 메시지 데이터
            use_cache: 캐시 사용 여부
            
        Returns:
            프로젝트 코드 (예: "WELL", "WI", "CC") 또는 None
        """
        try:
            todo_id = message.get('id')
            
            # 0. 캐시 조회 (가장 우선)
            if use_cache and todo_id and hasattr(self, 'tag_cache') and self.tag_cache:
                cached = self.tag_cache.get_cached_tag(todo_id)
                if cached:
                    reason = cached.get('classification_reason', '')
                    if reason:
                        logger.debug(f"[프로젝트 태그] 캐시 히트: {todo_id} → {cached['project_tag']} ({reason})")
                    else:
                        logger.debug(f"[프로젝트 태그] 캐시 히트: {todo_id} → {cached['project_tag']}")
                    return cached['project_tag']
            
            # 1. 명시적 프로젝트명 확인 (대괄호 패턴 등 명확한 경우만)
            explicit_project = self._extract_explicit_project(message)
            if explicit_project:
                reason = f"명시적 패턴 매칭"
                
                # 명시적 패턴이 발견되면 LLM으로 검증
                llm_result = self._extract_project_by_llm(message)
                if llm_result:
                    llm_project, llm_reason = llm_result
                    if llm_project and llm_project != 'UNKNOWN':
                        logger.info(f"[프로젝트 태그] LLM 검증: {llm_project} ({llm_reason})")
                        result = llm_project
                        reason = llm_reason
                    else:
                        logger.info(f"[프로젝트 태그] 명시적 프로젝트 사용: {explicit_project}")
                        result = explicit_project
                else:
                    logger.info(f"[프로젝트 태그] 명시적 프로젝트 사용: {explicit_project}")
                    result = explicit_project
                
                # 캐시 저장
                if todo_id and hasattr(self, 'tag_cache') and self.tag_cache:
                    self.tag_cache.save_tag(todo_id, result, 'explicit', 'pattern_match', reason)
                return result
            
            # 2. LLM 기반 지능 분류 (메시지 내용 우선 분석)
            llm_result = self._extract_project_by_llm(message)
            if llm_result:
                llm_project, llm_reason = llm_result
                if llm_project and llm_project != 'UNKNOWN':
                    logger.info(f"[프로젝트 태그] LLM 분석: {llm_project} ({llm_reason})")
                    
                    # 캐시 저장
                    if todo_id and hasattr(self, 'tag_cache') and self.tag_cache:
                        self.tag_cache.save_tag(todo_id, llm_project, 'llm', 'content_analysis', llm_reason)
                    return llm_project
            
            # 3. 고급 분석 (프로젝트 기간, 설명, 발신자 종합)
            advanced_result = self._extract_project_by_advanced_analysis(message)
            if advanced_result:
                project_code, reason = advanced_result
                logger.info(f"[프로젝트 태그] 고급 분석: {project_code} ({reason})")
                
                # 캐시 저장
                if todo_id and hasattr(self, 'tag_cache') and self.tag_cache:
                    self.tag_cache.save_tag(todo_id, project_code, 'advanced', 'advanced_analysis', reason)
                return project_code
            
            # 4. 발신자 정보 참고 (폴백 - 여러 프로젝트 가능하므로 참고용)
            sender_project = self._extract_project_by_sender(message)
            if sender_project:
                reason = "발신자 기본 프로젝트"
                logger.info(f"[프로젝트 태그] 발신자 폴백: {sender_project} ({reason})")
                
                # 캐시 저장
                if todo_id and hasattr(self, 'tag_cache') and self.tag_cache:
                    self.tag_cache.save_tag(todo_id, sender_project, 'sender', 'sender_fallback', reason)
                return sender_project
            
            # 5. 최종 폴백: "미분류" 태그 부여 (프로젝트를 전혀 식별할 수 없는 경우)
            logger.info("[프로젝트 태그] 최종 폴백: 미분류")
            if todo_id and hasattr(self, 'tag_cache') and self.tag_cache:
                self.tag_cache.save_tag(todo_id, "미분류", 'fallback', 'unclassified', "프로젝트 특정 불가")
            return "미분류"
            
        except Exception as e:
            logger.error(f"프로젝트 추출 오류: {e}")
            return None
    
    def _extract_explicit_project(self, message: Dict) -> Optional[str]:
        """메시지에서 명시적으로 언급된 프로젝트명 추출 (동적 매칭)"""
        content = message.get("content", "")
        subject = message.get("subject", "")
        text = f"{subject} {content}".lower()
        
        # 매칭 결과를 점수와 함께 저장
        matches = []
        
        # 현재 로드된 모든 프로젝트에 대해 패턴 매칭
        for project_code, project_tag in self.project_tags.items():
            project_name_lower = project_tag.name.lower()
            
            # 패턴별 우선순위 점수 (높을수록 우선)
            patterns_with_scores = [
                (f"[{project_name_lower}]", 100),  # 대괄호 포함 (가장 명시적)
                (project_name_lower, 90),  # 전체 이름
                (project_name_lower.replace(" ", ""), 80),  # 공백 제거
            ]
            
            # 특별 키워드 추가 (중간 우선순위)
            special_keywords = self._get_project_keywords(project_code, project_tag.name)
            for keyword in special_keywords:
                if keyword:
                    patterns_with_scores.append((keyword, 70))
            
            # 프로젝트 코드 (낮은 우선순위)
            patterns_with_scores.append((project_code.lower(), 50))
            
            # 숫자 버전 패턴 추가 (낮은 우선순위)
            if any(char.isdigit() for char in project_name_lower):
                first_word = project_name_lower.split()[0]
                patterns_with_scores.append((first_word, 40))
            
            # 패턴 매칭 및 점수 계산
            for pattern, score in patterns_with_scores:
                if pattern and pattern in text:
                    # 패턴 길이도 고려 (더 긴 패턴이 더 구체적)
                    final_score = score + len(pattern)
                    matches.append((project_code, pattern, final_score))
                    break  # 첫 번째 매칭만 사용
        
        # 가장 높은 점수의 매칭 반환
        if matches:
            matches.sort(key=lambda x: x[2], reverse=True)  # 점수 내림차순 정렬
            best_match = matches[0]
            project_code, pattern, score = best_match
            logger.info(f"[프로젝트 태그] 명시적 패턴 매칭: '{pattern}' → {project_code} (점수: {score})")
            return project_code
        
        return None
    
    def _get_project_keywords(self, project_code: str, project_name: str) -> List[str]:
        """프로젝트별 동적 키워드 생성 (VDOS DB 기반)"""
        keywords = []
        project_name_lower = project_name.lower()
        
        # 프로젝트 이름에서 자동으로 키워드 추출
        import re
        
        # 영어 단어들 추출
        english_words = re.findall(r'[A-Za-z]+', project_name)
        for word in english_words:
            if len(word) > 2:  # 3글자 이상만
                keywords.append(word.lower())
        
        # 한글 단어들 추출
        korean_words = re.findall(r'[가-힣]+', project_name)
        for word in korean_words:
            if len(word) > 1:  # 2글자 이상만
                keywords.append(word.lower())
        
        # 복합 키워드 생성
        if len(english_words) >= 2:
            # 첫 두 단어 조합
            keywords.append(f"{english_words[0].lower()} {english_words[1].lower()}")
            keywords.append(f"{english_words[0].lower()}{english_words[1].lower()}")
        
        # 대괄호 패턴 추가
        for keyword in keywords[:]:  # 복사본으로 순회
            keywords.append(f"[{keyword}")
            
        return keywords
    
    def _extract_project_by_sender(self, message: Dict) -> Optional[str]:
        """발신자 정보로 프로젝트 추출 (스마트 폴백)
        
        여러 프로젝트에 참여하는 발신자의 경우:
        1. 메시지 시간대와 프로젝트 기간 비교
        2. 메시지 내용과 프로젝트 키워드 매칭
        3. 최근 활동 프로젝트 우선
        """
        sender_email = message.get("sender_email", "") or message.get("sender", "")
        sender_name = message.get("sender_name", "")
        
        # 발신자의 프로젝트 목록 가져오기
        projects = []
        if sender_email and sender_email in self.person_project_mapping:
            projects = self.person_project_mapping[sender_email]
        elif sender_name and sender_name in self.person_project_mapping:
            projects = self.person_project_mapping[sender_name]
        
        if not projects:
            return None
        
        # 프로젝트가 1개면 바로 반환
        if len(projects) == 1:
            return projects[0]
        
        # 여러 프로젝트인 경우 스마트 선택
        return self._smart_project_selection(message, projects, sender_email or sender_name)
    
    def _smart_project_selection(self, message: Dict, projects: List[str], sender_id: str) -> Optional[str]:
        """여러 프로젝트 중 가장 적합한 프로젝트 선택
        
        점수 기반 선택:
        - 시간대 일치: +50점
        - 키워드 매칭: +30점 (키워드당 +10점)
        - 최근 활동: +20점
        """
        from datetime import datetime
        
        project_scores = {}
        
        # 메시지 시간 추출
        message_time = None
        timestamp = message.get("timestamp") or message.get("created_at")
        if timestamp:
            try:
                if isinstance(timestamp, str):
                    message_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                elif isinstance(timestamp, datetime):
                    message_time = timestamp
            except:
                pass
        
        # 메시지 내용
        content = message.get("content", "")
        subject = message.get("subject", "")
        full_text = f"{subject} {content}".lower()
        
        for project_code in projects:
            score = 0
            
            # 1. 시간대 일치 확인 (프로젝트 기간 내인지)
            if message_time and project_code in self.project_periods:
                period = self.project_periods[project_code]
                start_date = period.get("start_date")
                end_date = period.get("end_date")
                
                if start_date and end_date:
                    try:
                        start = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                        end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                        
                        if start <= message_time <= end:
                            score += 50
                            logger.debug(f"[스마트폴백] {project_code}: 시간대 일치 (+50)")
                    except:
                        pass
            
            # 2. 키워드 매칭 (프로젝트 이름, 설명에서 키워드 추출)
            if project_code in self.project_tags:
                project_tag = self.project_tags[project_code]
                project_name = project_tag.name.lower()
                project_desc = project_tag.description.lower()
                
                # 프로젝트 이름이 메시지에 포함되어 있으면
                if project_name and project_name in full_text:
                    score += 30
                    logger.debug(f"[스마트폴백] {project_code}: 프로젝트명 매칭 (+30)")
                
                # 프로젝트 코드가 메시지에 포함되어 있으면
                if project_code.lower() in full_text:
                    score += 20
                    logger.debug(f"[스마트폴백] {project_code}: 코드 매칭 (+20)")
                
                # 설명에서 키워드 추출하여 매칭
                if project_desc:
                    keywords = self._extract_keywords_from_description(project_desc)
                    matched_keywords = sum(1 for kw in keywords if kw in full_text)
                    if matched_keywords > 0:
                        keyword_score = min(matched_keywords * 10, 30)
                        score += keyword_score
                        logger.debug(f"[스마트폴백] {project_code}: 키워드 {matched_keywords}개 매칭 (+{keyword_score})")
            
            # 3. 최근 활동 프로젝트 우선 (프로젝트 종료일이 가까운 순)
            if project_code in self.project_periods:
                period = self.project_periods[project_code]
                end_date = period.get("end_date")
                
                if end_date and message_time:
                    try:
                        end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                        days_diff = abs((end - message_time).days)
                        
                        # 종료일이 가까울수록 높은 점수 (최대 20점)
                        if days_diff < 30:
                            recency_score = max(20 - days_diff // 2, 0)
                            score += recency_score
                            logger.debug(f"[스마트폴백] {project_code}: 최근 활동 (+{recency_score})")
                    except:
                        pass
            
            project_scores[project_code] = score
        
        # 점수가 가장 높은 프로젝트 선택
        if project_scores:
            best_project = max(project_scores.items(), key=lambda x: x[1])
            project_code, score = best_project
            
            logger.info(f"[스마트폴백] {sender_id}: {project_code} 선택 (점수: {score})")
            logger.debug(f"[스마트폴백] 전체 점수: {project_scores}")
            
            # 점수가 0보다 크면 반환 (어느 정도 근거가 있는 경우)
            if score > 0:
                return project_code
            
            # 점수가 모두 0이면 첫 번째 프로젝트 반환 (기본 폴백)
            logger.info(f"[스마트폴백] 점수 없음 → 첫 번째 프로젝트 반환: {projects[0]}")
            return projects[0]
        
        return None
    
    def _extract_keywords_from_description(self, description: str) -> List[str]:
        """프로젝트 설명에서 키워드 추출"""
        # 간단한 키워드 추출 (3글자 이상 단어)
        import re
        words = re.findall(r'\b\w{3,}\b', description.lower())
        
        # 불용어 제거
        stopwords = {'the', 'and', 'for', 'with', 'this', 'that', 'from', 'have', 'will', 'are', 'was', 'were'}
        keywords = [w for w in words if w not in stopwords]
        
        return keywords[:10]  # 최대 10개
    
    def _extract_project_by_advanced_analysis(self, message: Dict) -> Optional[Tuple[str, str]]:
        """고급 분석: 채팅 메시지 처리 + 프로젝트 기간, 설명, 발신자 종합 분석
        
        UNKNOWN이 나올 경우:
        1. 채팅 메시지인지 확인 (source_message가 비어있는 경우)
        2. VDOS DB에서 실제 채팅 내용 가져오기
        3. 프로젝트 기간과 설명을 활용하여 유추
        
        Returns:
            (프로젝트 코드, 분류 근거) 튜플 또는 None
        """
        try:
            content = message.get("content", "")
            subject = message.get("subject", "")
            sender = message.get("sender", "")
            sender_email = message.get("sender_email", "")
            message_date = message.get("timestamp", "")
            todo_content = message.get("todo_content", "")  # TODO 내용 (있는 경우)
            
            # 채팅 메시지 감지: content와 subject가 모두 비어있고 sender가 이메일 형식이 아님
            is_chat_message = (not content and not subject and sender and '@' not in sender)
            
            if is_chat_message:
                logger.info(f"[프로젝트 태그] 채팅 메시지 감지: {sender}")
                
                # 채팅 전용 매칭 로직 사용
                if self.vdos_db_path:
                    chat_result = self._match_project_from_chat(sender, message_date, todo_content)
                    if chat_result:
                        return chat_result
                    else:
                        logger.debug(f"[프로젝트 태그] 채팅 매칭 실패, 기본 분석으로 폴백")
                
                # 폴백: VDOS DB에서 채팅 내용 가져오기
                content = self._fetch_chat_content_from_vdos(sender, message_date)
                if content:
                    logger.debug(f"[프로젝트 태그] 채팅 내용 조회 성공: {content[:100]}...")
            
            text = f"{subject} {content} {todo_content}".lower()
            
            # 1. 발신자가 참여한 프로젝트 목록 가져오기
            sender_projects = []
            if sender_email and sender_email in self.person_project_mapping:
                sender_projects = self.person_project_mapping[sender_email]
            elif sender and sender in self.person_project_mapping:
                sender_projects = self.person_project_mapping[sender]
            
            if not sender_projects:
                return None
            
            # 2. 각 프로젝트별 점수 계산
            project_scores = {}
            
            for project_code in sender_projects:
                score = 0
                reasons = []
                
                project_tag = self.project_tags.get(project_code)
                if not project_tag:
                    continue
                
                # 2.1 프로젝트 설명과의 유사도
                if project_tag.description:
                    desc_lower = project_tag.description.lower()
                    # 설명에서 주요 키워드 추출
                    desc_keywords = set(re.findall(r'[가-힣a-z]{2,}', desc_lower))
                    text_keywords = set(re.findall(r'[가-힣a-z]{2,}', text))
                    
                    # 공통 키워드 개수
                    common_keywords = desc_keywords & text_keywords
                    if common_keywords:
                        keyword_score = len(common_keywords) * 10
                        score += keyword_score
                        reasons.append(f"키워드 {len(common_keywords)}개 일치")
                
                # 2.2 프로젝트 이름 부분 매칭
                project_name_lower = project_tag.name.lower()
                project_words = re.findall(r'[가-힣a-z]+', project_name_lower)
                for word in project_words:
                    if len(word) > 2 and word in text:
                        score += 20
                        reasons.append(f"프로젝트명 '{word}' 포함")
                        break
                
                # 2.3 프로젝트 기간 정보 활용 (메시지 날짜가 있는 경우)
                if message_date and project_code in self.project_periods:
                    period = self.project_periods[project_code]
                    score += 5
                    reasons.append(f"기간: {period['start_week']}~{period['end_week']}주차")
                
                if score > 0:
                    project_scores[project_code] = (score, ", ".join(reasons))
            
            # 3. 가장 높은 점수의 프로젝트 반환
            if project_scores:
                best_project = max(project_scores.items(), key=lambda x: x[1][0])
                project_code, (score, reason) = best_project
                
                if score >= 10:  # 최소 점수 임계값
                    return (project_code, f"고급분석: {reason}")
            
            return None
            
        except Exception as e:
            logger.error(f"고급 분석 오류: {e}")
            return None
    
    def _match_project_from_chat(self, sender: str, message_date: str = None, 
                                 todo_content: str = None) -> Optional[Tuple[str, str]]:
        """채팅 메시지 전용 프로젝트 매칭
        
        Args:
            sender: 발신자 (채팅 핸들)
            message_date: 메시지 날짜
            todo_content: TODO 내용 (있는 경우)
            
        Returns:
            (프로젝트 코드, 분류 근거) 튜플 또는 None
        """
        try:
            from services.chat_project_matcher import ChatProjectMatcher
            
            matcher = ChatProjectMatcher(
                vdos_db_path=self.vdos_db_path,
                project_tags=self.project_tags,
                person_project_mapping=self.person_project_mapping,
                project_periods=self.project_periods
            )
            
            return matcher.match_project_from_chat(sender, message_date, todo_content)
            
        except Exception as e:
            logger.error(f"채팅 프로젝트 매칭 오류: {e}")
            return None
    
    def _fetch_chat_content_from_vdos(self, sender: str, message_date: str = None) -> Optional[str]:
        """VDOS DB에서 채팅 메시지 내용 가져오기
        
        Args:
            sender: 발신자 (채팅 핸들 또는 이메일)
            message_date: 메시지 날짜 (선택)
            
        Returns:
            채팅 메시지 내용 또는 None
        """
        try:
            if not self.vdos_db_path:
                return None
            
            import sqlite3
            conn = sqlite3.connect(self.vdos_db_path)
            cur = conn.cursor()
            
            # 최근 메시지 조회 (발신자 기준)
            if message_date:
                # 날짜 기준으로 가장 가까운 메시지
                cur.execute('''
                    SELECT body
                    FROM chat_messages
                    WHERE sender = ?
                    ORDER BY ABS(julianday(sent_at) - julianday(?))
                    LIMIT 1
                ''', (sender, message_date))
            else:
                # 가장 최근 메시지
                cur.execute('''
                    SELECT body
                    FROM chat_messages
                    WHERE sender = ?
                    ORDER BY id DESC
                    LIMIT 1
                ''', (sender,))
            
            result = cur.fetchone()
            conn.close()
            
            if result:
                return result[0]
            
            return None
            
        except Exception as e:
            logger.error(f"채팅 내용 조회 오류: {e}")
            return None
    
    def _extract_project_by_llm(self, message: Dict) -> Optional[Tuple[str, str]]:
        """LLM을 사용하여 메시지 내용으로 프로젝트 분류
        
        Returns:
            (프로젝트 코드, 분류 근거) 튜플 또는 None
        """
        try:
            # 메시지 내용 준비
            content = message.get("content", "")
            subject = message.get("subject", "")
            sender = message.get("sender", "")
            
            if not content and not subject:
                return None
            
            # 기존 LLM 서비스 사용 (Top3Service와 동일한 방식)
            result = self._call_existing_llm_service(message)
            
            if result:
                project_code, reason = result
                if project_code and project_code.strip().upper() in self.project_tags:
                    return (project_code.strip().upper(), reason)
            
            return None
            
        except Exception as e:
            logger.error(f"LLM 프로젝트 분류 오류: {e}")
            return None
    
    def _recover_chat_message_content(self, message: Dict) -> Optional[Dict]:
        """채팅 메시지 내용 복구
        
        source_message에 내용이 없는 경우 VDOS DB에서 실제 채팅 내용을 가져옴
        
        Returns:
            복구된 메시지 딕셔너리 또는 None
        """
        try:
            # 발신자가 채팅 핸들인지 확인 (이메일 형식이 아님)
            sender = message.get('sender', '') or message.get('sender_email', '')
            if not sender or '@' in sender:
                return None  # 이메일이면 채팅이 아님
            
            # 내용이 비어있는지 확인
            content = message.get('content', '') or message.get('body', '')
            subject = message.get('subject', '')
            
            if content or subject:
                return None  # 이미 내용이 있음
            
            # VDOS DB가 없으면 복구 불가
            if not self.vdos_db_path:
                return None
            
            import sqlite3
            conn = sqlite3.connect(self.vdos_db_path)
            cur = conn.cursor()
            
            # 채팅 핸들로 최근 메시지 검색 (프로젝트 언급이 있는 메시지 우선)
            cur.execute('''
                SELECT cm.id, cm.sender, cm.body, cm.sent_at, cr.name as room_name, cm.room_id
                FROM chat_messages cm
                JOIN chat_rooms cr ON cm.room_id = cr.id
                WHERE cm.sender = ?
                ORDER BY cm.id DESC
                LIMIT 20
            ''', (sender,))
            
            recent_messages = cur.fetchall()
            
            if not recent_messages:
                conn.close()
                return None
            
            # 프로젝트 언급이 있는 메시지 우선 선택
            selected_message = None
            for msg_id, msg_sender, msg_body, msg_sent_at, room_name, room_id in recent_messages:
                # 프로젝트 키워드 확인
                if any(keyword in msg_body for keyword in ['Project', 'LUMINA', 'VERTEX', 'NOVA', 'SYNAPSE', 'OMEGA', '프로젝트']):
                    selected_message = (msg_id, msg_sender, msg_body, msg_sent_at, room_name, room_id)
                    logger.info(f"[프로젝트 태그] 프로젝트 언급 채팅 발견: {msg_body[:50]}...")
                    break
            
            # 프로젝트 언급이 없으면 가장 최근 메시지 사용
            if not selected_message:
                selected_message = recent_messages[0]
                logger.info(f"[프로젝트 태그] 최근 채팅 사용: {selected_message[2][:50]}...")
            
            msg_id, msg_sender, msg_body, msg_sent_at, room_name, room_id = selected_message
            
            # 채팅방 멤버 확인 (프로젝트 유추에 활용)
            cur.execute('''
                SELECT handle
                FROM chat_members
                WHERE room_id = ?
            ''', (room_id,))
            room_members = [row[0] for row in cur.fetchall()]
            
            conn.close()
            
            # 복구된 메시지 반환
            return {
                'id': message.get('id'),
                'sender': msg_sender,
                'sender_email': msg_sender,
                'subject': f"채팅: {room_name}",
                'content': msg_body,
                'body': msg_body,
                'timestamp': msg_sent_at,
                'source_type': 'chat',
                'room_members': room_members  # 채팅방 멤버 정보 추가
            }
            
        except Exception as e:
            logger.error(f"채팅 메시지 복구 오류: {e}")
            return None
    
    def _extract_project_by_advanced_analysis(self, message: Dict) -> Optional[Tuple[str, str]]:
        """고급 분석: 프로젝트 기간, 설명, 발신자 종합 분석
        
        UNKNOWN이 나올 경우 프로젝트 기간과 설명을 활용하여 유추
        
        Returns:
            (프로젝트 코드, 분류 근거) 튜플 또는 None
        """
        try:
            content = message.get("content", "")
            subject = message.get("subject", "")
            sender = message.get("sender", "")
            sender_email = message.get("sender_email", "")
            message_date = message.get("timestamp", "")
            
            text = f"{subject} {content}".lower()
            
            # 1. 발신자가 참여한 프로젝트 목록 가져오기
            sender_projects = []
            if sender_email and sender_email in self.person_project_mapping:
                sender_projects = self.person_project_mapping[sender_email]
            elif sender and sender in self.person_project_mapping:
                sender_projects = self.person_project_mapping[sender]
            
            if not sender_projects:
                return None
            
            # 2. 각 프로젝트별 점수 계산
            project_scores = {}
            
            for project_code in sender_projects:
                score = 0
                reasons = []
                
                project_tag = self.project_tags.get(project_code)
                if not project_tag:
                    continue
                
                # 2.1 프로젝트 설명과의 유사도
                if project_tag.description:
                    desc_lower = project_tag.description.lower()
                    # 설명에서 주요 키워드 추출
                    desc_keywords = set(re.findall(r'[가-힣a-z]{2,}', desc_lower))
                    text_keywords = set(re.findall(r'[가-힣a-z]{2,}', text))
                    
                    # 공통 키워드 개수
                    common_keywords = desc_keywords & text_keywords
                    if common_keywords:
                        keyword_score = len(common_keywords) * 10
                        score += keyword_score
                        reasons.append(f"키워드 {len(common_keywords)}개 일치")
                
                # 2.2 프로젝트 이름 부분 매칭
                project_name_lower = project_tag.name.lower()
                project_words = re.findall(r'[가-힣a-z]+', project_name_lower)
                for word in project_words:
                    if len(word) > 2 and word in text:
                        score += 20
                        reasons.append(f"프로젝트명 '{word}' 포함")
                        break
                
                # 2.3 프로젝트 기간 정보 활용 (메시지 날짜가 있는 경우)
                if message_date and project_code in self.project_periods:
                    period = self.project_periods[project_code]
                    # TODO: 메시지 날짜를 주차로 변환하여 프로젝트 기간과 비교
                    # 현재는 기간 정보가 있다는 것만으로 약간의 가산점
                    score += 5
                    reasons.append(f"기간: {period['start_week']}~{period['end_week']}주차")
                
                if score > 0:
                    project_scores[project_code] = (score, ", ".join(reasons))
            
            # 3. 가장 높은 점수의 프로젝트 반환
            if project_scores:
                best_project = max(project_scores.items(), key=lambda x: x[1][0])
                project_code, (score, reason) = best_project
                
                if score >= 10:  # 최소 점수 임계값
                    return (project_code, f"고급분석: {reason}")
            
            return None
            
        except Exception as e:
            logger.error(f"고급 분석 오류: {e}")
            return None
    
    def _call_existing_llm_service(self, message: Dict) -> Optional[Tuple[str, str]]:
        """VDOS DB 정보를 활용한 LLM 기반 프로젝트 분류
        
        Returns:
            (프로젝트 코드, 분류 근거) 튜플 또는 None
        """
        try:
            # VDOS DB에서 프로젝트 및 사람 정보 가져오기
            project_context = self._build_project_context()
            
            # 메시지 내용 준비
            content = message.get("content", "")
            subject = message.get("subject", "")
            sender = message.get("sender", "")
            
            logger.debug(f"[프로젝트 태그] LLM 분석 시작:")
            logger.debug(f"  - 제목: {subject}")
            logger.debug(f"  - 내용: {content[:100]}")
            logger.debug(f"  - 발신자: {sender}")
            logger.debug(f"  - 프로젝트 수: {len(self.project_tags)}")
            
            # LLM 프롬프트 구성 (VDOS DB 정보 포함)
            system_prompt = f"""당신은 업무 메시지를 분석하여 관련 프로젝트를 분류하는 전문가입니다.

다음은 현재 진행 중인 프로젝트들과 관련 정보입니다:

{project_context}

메시지 내용을 분석하여 가장 관련성이 높은 프로젝트 코드를 선택하세요.

규칙:
1. **메시지 제목이나 내용에 프로젝트명이 명시**되어 있으면 해당 프로젝트를 우선 선택
2. **발신자가 특정 프로젝트에만 참여**하고 있다면 해당 프로젝트 선택
3. **메시지 내용의 키워드와 프로젝트 설명을 매칭**하여 판단
4. **발신자가 여러 프로젝트에 참여하는 경우**:
   - 메시지 내용의 키워드 (예: "디자인", "개발", "데이터", "캠페인" 등)를 분석
   - 프로젝트 설명과 가장 관련성이 높은 프로젝트 선택
   - 업무 유형 (디자인, 개발, 마케팅 등)을 고려하여 추론
5. **시간대나 문맥을 고려**하여 프로젝트 유추
6. **정말 판단할 수 없는 경우에만** 'UNKNOWN' 반환 (최후의 수단)

응답 형식: "프로젝트코드|분류근거" (예: "PV|디자인 작업 언급" 또는 "UNKNOWN|프로젝트 특정 불가")
분류근거는 10단어 이내로 간단히 작성하세요."""

            user_prompt = f"""다음 메시지를 분석하여 관련 프로젝트를 분류해주세요:

발신자: {sender}
제목: {subject}
내용: {content[:1000]}

"프로젝트코드|분류근거" 형식으로 반환하세요."""

            # LLM API 호출
            response = self._call_llm_api(system_prompt, user_prompt)
            
            if response and response.strip():
                # 응답 파싱: "프로젝트코드|분류근거" 또는 "프로젝트코드 (분류근거)"
                response_clean = response.strip().strip('"')  # 따옴표 제거
                
                # | 구분자가 있으면 사용
                if '|' in response_clean:
                    parts = response_clean.split('|', 1)
                    project_code = parts[0].strip().upper()
                    reason = parts[1].strip() if len(parts) > 1 else "LLM 내용 분석"
                # ( 구분자가 있으면 사용 (예: "PV (김세린 참여 프로젝트)")
                elif '(' in response_clean:
                    parts = response_clean.split('(', 1)
                    project_code = parts[0].strip().upper()
                    reason = parts[1].strip().rstrip(')') if len(parts) > 1 else "LLM 내용 분석"
                # 공백으로 구분 (예: "PV 디자인작업")
                else:
                    parts = response_clean.split(None, 1)
                    project_code = parts[0].strip().upper()
                    reason = parts[1].strip() if len(parts) > 1 else "LLM 내용 분석"
                
                logger.info(f"[프로젝트 태그] LLM 분류: {project_code} ({reason})")
                return (project_code, reason)
                
            return None
            
        except Exception as e:
            logger.error(f"LLM 프로젝트 분류 오류: {e}")
            return None
    
    def _build_project_context(self) -> str:
        """VDOS DB 정보를 활용한 프로젝트 컨텍스트 구축"""
        context_lines = []
        
        for code, tag in self.project_tags.items():
            context_lines.append(f"## {code}: {tag.name}")
            context_lines.append(f"설명: {tag.description}")
            
            # 프로젝트 참여자 정보 추가
            participants = []
            for person, projects in self.person_project_mapping.items():
                if code in projects:
                    participants.append(person)
            
            if participants:
                context_lines.append(f"참여자: {', '.join(participants[:5])}")  # 최대 5명만
                if len(participants) > 5:
                    context_lines.append(f"(총 {len(participants)}명)")
            
            context_lines.append("")  # 빈 줄
        
        return "\n".join(context_lines)
    
    def _call_llm_api(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        """LLM API 호출 (환경 설정 기반)"""
        try:
            import os
            import requests
            import json
            from dotenv import load_dotenv
            
            # VDOS .env 파일 로드
            vdos_env_path = os.path.join(os.path.dirname(__file__), '../../../virtualoffice/.env')
            if os.path.exists(vdos_env_path):
                load_dotenv(vdos_env_path)
            
            # 환경 변수에서 설정 읽기
            use_openrouter = os.getenv('VDOS_USE_OPENROUTER', 'false').lower() == 'true'
            
            if use_openrouter:
                # OpenRouter 사용
                api_key = os.getenv('OPENROUTER_API_KEY')
                if not api_key:
                    logger.warning("OpenRouter API 키가 설정되지 않음")
                    return None
                
                url = "https://openrouter.ai/api/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "model": "openai/gpt-4o",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "max_tokens": 50,
                    "temperature": 0.1
                }
                
            else:
                # Azure OpenAI 사용
                api_key = os.getenv('AZURE_OPENAI_API_KEY')
                endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
                
                if not api_key or not endpoint:
                    # OpenAI 폴백
                    return self._call_openai_api(system_prompt, user_prompt)
                
                url = f"{endpoint}/openai/deployments/gpt-4o/chat/completions?api-version=2024-02-15-preview"
                headers = {
                    "api-key": api_key,
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "max_tokens": 50,
                    "temperature": 0.1
                }
            
            # API 호출
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            content = result['choices'][0]['message']['content'].strip()
            
            return content
            
        except Exception as e:
            logger.error(f"LLM API 호출 오류: {e}")
            return None
    
    def _call_openai_api(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        """OpenAI API 폴백 호출"""
        try:
            import os
            import requests
            from dotenv import load_dotenv
            
            # VDOS .env 파일 로드
            vdos_env_path = os.path.join(os.path.dirname(__file__), '../../../virtualoffice/.env')
            if os.path.exists(vdos_env_path):
                load_dotenv(vdos_env_path)
            
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                logger.warning("OpenAI API 키가 설정되지 않음")
                return None
            
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "gpt-4o",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "max_tokens": 50,
                "temperature": 0.1
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            content = result['choices'][0]['message']['content'].strip()
            
            return content
            
        except Exception as e:
            logger.error(f"OpenAI API 폴백 호출 오류: {e}")
            return None
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
        project_code = generate_project_code(project_name)
        
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
