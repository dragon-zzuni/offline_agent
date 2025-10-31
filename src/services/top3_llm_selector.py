# -*- coding: utf-8 -*-
"""
LLM 기반 Top3 선정 모듈

자연어 규칙을 LLM에 전달하여 가장 적합한 TODO 3개를 선정합니다.
"""
import json
import logging
from typing import Dict, List, Set, Optional, Tuple
from datetime import datetime

from .llm_client import LLMClient
from .top3_cache_manager import Top3CacheManager

logger = logging.getLogger(__name__)


class Top3LLMSelector:
    """LLM 기반 Top3 선정기
    
    자연어 규칙과 TODO 리스트를 LLM에 전달하여 최적의 3개를 선정합니다.
    """
    
    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        cache_manager: Optional[Top3CacheManager] = None,
        email_to_name: Optional[Dict[str, str]] = None
    ):
        """
        Args:
            llm_client: LLM 클라이언트 (None이면 자동 생성)
            cache_manager: 캐시 관리자 (None이면 자동 생성)
            email_to_name: 이메일-이름 매핑 (호환성을 위해 유지, 사용하지 않음)
        """
        self.llm_client = llm_client or LLMClient()
        self.cache_manager = cache_manager or Top3CacheManager()
        self.email_to_name = email_to_name or {}
    
    def select_top3(
        self,
        todos: List[Dict],
        natural_rule: str,
        entity_rules: Optional[Dict[str, Dict[str, float]]] = None
    ) -> Set[str]:
        """LLM으로 Top3 선정 (폴백 메커니즘 포함)
        
        Args:
            todos: TODO 리스트
            natural_rule: 자연어 규칙
            entity_rules: 엔티티 규칙 (캐시 키 생성용)
            
        Returns:
            선정된 TODO ID 집합
        """
        if not todos:
            logger.warning("[Top3LLM] TODO 리스트가 비어있습니다")
            return set()
        
        if not natural_rule or not natural_rule.strip():
            logger.warning("[Top3LLM] 자연어 규칙이 비어있습니다")
            return self._fallback_selection(todos)
        
        # 캐시 확인
        cached = self.cache_manager.get(todos, entity_rules, natural_rule)
        if cached:
            logger.info(f"[Top3LLM] 캐시 히트: {len(cached)}개 반환")
            return cached
        
        # done 상태 제외
        candidates = [t for t in todos if (t.get("status") or "pending") not in ("done",)]
        
        if not candidates:
            logger.warning("[Top3LLM] 후보 TODO가 없습니다 (모두 완료 상태)")
            return set()
        
        # LLM 사용 가능 여부 확인
        if not self.llm_client.is_available():
            logger.warning("[Top3LLM] LLM 클라이언트를 사용할 수 없습니다 → 폴백 모드")
            return self._fallback_selection(candidates)
        
        # 50개 이상이면 사전 필터링
        if len(candidates) > 50:
            logger.info(f"[Top3LLM] TODO {len(candidates)}개 → 사전 필터링 적용")
            candidates = self._prefilter_todos(candidates, natural_rule)
            logger.info(f"[Top3LLM] 사전 필터링 후: {len(candidates)}개")
        
        # LLM 시도
        try:
            result = self._try_llm_selection(candidates, natural_rule, entity_rules, todos)
            if result:
                return result
        except Exception as e:
            logger.error(f"[Top3LLM] LLM 선정 실패: {e}")
        
        # LLM 실패 시 폴백
        logger.warning("[Top3LLM] LLM 선정 실패 → 폴백 모드")
        return self._fallback_selection(candidates)
    
    def _try_llm_selection(
        self, 
        candidates: List[Dict], 
        natural_rule: str, 
        entity_rules: Optional[Dict], 
        original_todos: List[Dict]
    ) -> Optional[Set[str]]:
        """LLM 선정 시도
        
        Returns:
            성공 시 선정된 ID 집합, 실패 시 None
        """
        # LLM 프롬프트 생성
        prompt = self._build_prompt(candidates, natural_rule)
        
        # 디버그 로깅
        logger.debug(f"[Top3LLM] 프롬프트 생성 완료 (길이: {len(prompt)}자)")
        logger.debug(f"[Top3LLM] 자연어 규칙: {natural_rule}")
        
        # LLM 호출
        logger.info(f"[Top3LLM] LLM 호출 시작 (후보: {len(candidates)}개)")
        
        response = self.llm_client.generate(
            messages=[
                {"role": "system", "content": self._get_system_prompt()},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,  # 더 일관된 결과를 위해 낮춤
            max_tokens=1000
        )
        
        if response.error:
            logger.error(f"[Top3LLM] LLM 호출 실패: {response.error}")
            return None
        
        # 응답 로깅 (INFO)
        logger.info(
            f"[Top3LLM] LLM 응답 수신: {response.response_time:.2f}초, "
            f"토큰={response.tokens_used or 'N/A'}, "
            f"길이={len(response.content)}자"
        )
        
        # 응답 내용 로깅 (DEBUG)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"[Top3LLM] 응답 내용:\n{response.content}")
        
        # 응답 파싱
        top3_ids, reasoning = self._parse_response(response.content)
        
        if not top3_ids:
            logger.warning("[Top3LLM] 선정된 TODO가 없습니다 (파싱 결과 빈 집합)")
            logger.warning(f"[Top3LLM] LLM 응답 내용: {response.content[:500]}")
            return None
        
        logger.info(f"[Top3LLM] 파싱 결과: {len(top3_ids)}개 ID 추출")
        
        # 유효성 검증
        valid_ids = self._validate_ids(top3_ids, candidates)
        
        if not valid_ids:
            logger.warning("[Top3LLM] 유효한 TODO ID가 없습니다 (검증 실패)")
            return None
        
        # 캐시 저장
        self.cache_manager.set(original_todos, valid_ids, entity_rules, natural_rule)
        
        # 선정 결과 로깅 (INFO)
        logger.info(f"[Top3LLM] ✅ 선정 완료: {len(valid_ids)}개")
        logger.info(f"[Top3LLM] 선정 이유: {reasoning}")
        
        # 선정된 TODO 상세 로깅 (DEBUG)
        if logger.isEnabledFor(logging.DEBUG):
            for todo_id in valid_ids:
                todo = next((t for t in candidates if t.get("id") == todo_id), None)
                if todo:
                    logger.debug(
                        f"[Top3LLM] 선정: {todo_id} - "
                        f"{todo.get('title', '')[:50]} "
                        f"(프로젝트: {todo.get('project', 'N/A')}, "
                        f"요청자: {todo.get('requester', 'N/A')})"
                    )
        
        return valid_ids
    
    def _fallback_selection(self, todos: List[Dict]) -> Set[str]:
        """폴백 선정 (점수 기반)
        
        LLM이 실패했을 때 사용하는 간단한 점수 기반 선정
        """
        logger.info(f"[Top3LLM] 폴백 모드: 점수 기반 선정 (후보: {len(todos)}개)")
        
        if not todos:
            return set()
        
        # 점수 계산
        scored = []
        now = datetime.now()
        
        for todo in todos:
            score = 0.0
            
            # 우선순위 점수
            priority = (todo.get("priority") or "medium").lower()
            if priority == "high":
                score += 3.0
            elif priority == "medium":
                score += 2.0
            else:
                score += 1.0
            
            # 마감일 임박도
            deadline = todo.get("deadline")
            if deadline:
                try:
                    if isinstance(deadline, str):
                        dl = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
                        hours_left = (dl - now).total_seconds() / 3600.0
                        
                        if hours_left < 24:
                            score += 2.0
                        elif hours_left < 72:
                            score += 1.0
                except Exception:
                    pass
            
            # 수신 타입 (TO가 우선)
            recipient_type = (todo.get("recipient_type") or "to").lower()
            if recipient_type == "to":
                score += 0.5
            
            scored.append((score, todo))
        
        # 점수순 정렬 후 상위 3개
        scored.sort(key=lambda x: x[0], reverse=True)
        top3 = [todo for _, todo in scored[:3]]
        
        result = {todo.get("id") for todo in top3 if todo.get("id")}
        
        logger.info(f"[Top3LLM] 폴백 선정 완료: {len(result)}개")
        
        return result
    
    def _build_prompt(self, todos: List[Dict], natural_rule: str) -> str:
        """LLM 프롬프트 생성 (기존 summarizer와 동일한 형식)"""
        # VDOS DB에서 사람 정보 가져오기
        person_mapping = self._get_person_mapping()
        
        # TODO 리스트를 간결한 형태로 직렬화
        todo_list = []
        for i, todo in enumerate(todos, 1):
            requester = todo.get("requester", "")
            # 이메일을 이름으로 변환
            requester_name = person_mapping.get(requester, requester)
            
            todo_info = f"""ID: {todo.get("id", "")}
제목: {(todo.get("title") or "")[:100]}
프로젝트: {todo.get("project", "")}
**요청자(이 TODO를 생성한 사람)**: {requester_name}
우선순위: {todo.get("priority", "medium")}
마감일: {todo.get("deadline", "")}
유형: {todo.get("type", "")}
수신타입: {todo.get("recipient_type", "to")}
설명: {(todo.get("description") or "")[:150]}"""
            todo_list.append(f"{i}. {todo_info}")
        
        todos_text = "\n\n".join(todo_list)
        
        # 사람 매핑 정보도 프롬프트에 추가
        person_info = "\n".join([f"- {email}: {name}" for email, name in person_mapping.items()])
        person_section = f"\n\n사람 매핑 (이메일 → 이름):\n{person_info}" if person_info else ""
        
        prompt = f"""다음 TODO 리스트에서 사용자의 자연어 규칙에 가장 잘 맞는 상위 3개를 선정하여 JSON 형식으로 답변해주세요. 
반드시 소문자 json이라는 단어를 포함한 json 문자열로만 응답하세요.

사용자 규칙: {natural_rule}

프로젝트 태그 매핑:
- CC: Care Connect 2.0 리디자인 (케어 커넥트, 환자 연결 플랫폼)
- HA: HealthCore API 리팩토링 (헬스코어, 헬스 코어)
- WELL: WellLink 브랜드 런칭 캠페인 (웰링크, 웰 링크)
- WI: WellLink Insight Dashboard (웰링크 인사이트)
- CI: CareBridge Integration (케어브릿지, 케어 브릿지)
{person_section}

TODO 리스트 ({len(todos)}개):
{todos_text}

선정 기준:
1. 사용자 규칙의 모든 조건을 정확히 만족하는 TODO 우선
2. 프로젝트명은 부분 일치 허용 (예: "Care" → CC, "케어" → CC, "HealthCore" → HA)
3. **중요**: "요청자"는 TODO를 생성한 사람입니다. 설명에 언급된 사람이 아닙니다.
   - 예: "요청자: 전형우, 설명: 황다연과 회의" → 요청자는 전형우입니다 (황다연 아님)
4. 마감일, 우선순위, 유형 등 모든 조건 종합 고려
5. 정확히 3개를 선정 (조건에 맞는 TODO가 3개 미만이면 조건 완화)

다음 형식으로 분석해주세요:
{{
    "selected_ids": ["선정된_TODO_ID_1", "선정된_TODO_ID_2", "선정된_TODO_ID_3"],
    "reasoning": "선정 이유를 간략히 설명"
}}"""
        return prompt
    
    def _get_person_mapping(self) -> Dict[str, str]:
        """VDOS DB에서 이메일 → 이름 매핑 가져오기"""
        try:
            import sqlite3
            import os
            
            # VDOS DB 경로
            vdos_db_path = os.path.join(
                os.path.dirname(__file__),
                "../../../virtualoffice/src/virtualoffice/vdos.db"
            )
            
            if not os.path.exists(vdos_db_path):
                logger.warning(f"[Top3LLM] VDOS DB를 찾을 수 없습니다: {vdos_db_path}")
                return {}
            
            conn = sqlite3.connect(vdos_db_path)
            cursor = conn.cursor()
            
            # 이메일과 이름 가져오기
            cursor.execute("SELECT email_address, name, chat_handle FROM people")
            rows = cursor.fetchall()
            
            mapping = {}
            for email, name, handle in rows:
                if email:
                    mapping[email] = name
                if handle:
                    mapping[handle] = name
            
            conn.close()
            
            logger.debug(f"[Top3LLM] 사람 매핑 로드: {len(mapping)}명")
            return mapping
            
        except Exception as e:
            logger.error(f"[Top3LLM] 사람 매핑 로드 오류: {e}")
            return {}
    
    def _get_system_prompt(self) -> str:
        """시스템 프롬프트 (기존 summarizer와 동일한 형식)"""
        return """당신은 업무용 TODO 우선순위 분석 전문가입니다. 
사용자의 자연어 규칙을 정확히 이해하고, 주어진 TODO 리스트에서 규칙에 가장 잘 맞는 상위 3개를 선정합니다.
프로젝트 태그, 요청자, 마감일, 우선순위, 키워드 등 모든 조건을 종합적으로 고려하여 분석하세요."""
    
    def _parse_response(self, response: str) -> Tuple[Set[str], str]:
        """LLM 응답 파싱
        
        Returns:
            (선정된 TODO ID 집합, 선정 이유)
        """
        try:
            # JSON 추출 (마크다운 코드 블록 제거)
            response = response.strip()
            if response.startswith("```"):
                # ```json ... ``` 형태 처리
                lines = response.split("\n")
                response = "\n".join(lines[1:-1])
            
            data = json.loads(response)
            selected_ids = data.get("selected_ids", [])
            reasoning = data.get("reasoning", "")
            
            if not isinstance(selected_ids, list):
                logger.error(f"[Top3LLM] selected_ids가 리스트가 아닙니다: {type(selected_ids)}")
                return set(), ""
            
            return set(selected_ids), reasoning
            
        except json.JSONDecodeError as e:
            logger.error(f"[Top3LLM] JSON 파싱 실패: {e}")
            logger.debug(f"[Top3LLM] 응답 내용: {response[:500]}")
            return set(), ""
        except Exception as e:
            logger.error(f"[Top3LLM] 응답 파싱 중 예외: {e}")
            return set(), ""
    
    def _validate_ids(self, ids: Set[str], todos: List[Dict]) -> Set[str]:
        """TODO ID 유효성 검증
        
        Args:
            ids: LLM이 선정한 ID 집합
            todos: 실제 TODO 리스트
            
        Returns:
            유효한 ID 집합
        """
        valid_todo_ids = {t.get("id") for t in todos if t.get("id")}
        valid_ids = ids & valid_todo_ids
        
        invalid_ids = ids - valid_ids
        if invalid_ids:
            logger.warning(f"[Top3LLM] 유효하지 않은 ID: {invalid_ids}")
        
        return valid_ids
    
    def _prefilter_todos(self, todos: List[Dict], natural_rule: str = "") -> List[Dict]:
        """50개 이상일 때 사전 필터링
        
        자연어 규칙에 언급된 조건(요청자, 프로젝트)을 우선 고려하여 필터링합니다.
        
        Args:
            todos: TODO 리스트
            natural_rule: 자연어 규칙 (키워드 추출용)
            
        Returns:
            필터링된 TODO 리스트 (최대 50개)
        """
        # 자연어 규칙에서 키워드 추출
        rule_keywords = self._extract_rule_keywords(natural_rule)
        
        scored = []
        now = datetime.now()
        
        for todo in todos:
            score = 0.0
            
            # 자연어 규칙 매칭 보너스 (최우선)
            if rule_keywords:
                # 요청자 매칭
                requester = (todo.get("requester") or "").lower()
                for keyword in rule_keywords.get("requesters", []):
                    if keyword in requester:
                        score += 10.0  # 큰 보너스
                        break
                
                # 프로젝트 매칭
                project = (todo.get("project") or "").lower()
                for keyword in rule_keywords.get("projects", []):
                    if keyword in project:
                        score += 10.0  # 큰 보너스
                        break
            
            # 우선순위 점수
            priority = (todo.get("priority") or "medium").lower()
            if priority == "high":
                score += 3.0
            elif priority == "medium":
                score += 2.0
            else:
                score += 1.0
            
            # 마감일 임박도
            deadline = todo.get("deadline")
            if deadline:
                try:
                    # ISO 형식 파싱
                    if isinstance(deadline, str):
                        dl = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
                        hours_left = (dl - now).total_seconds() / 3600.0
                        
                        if hours_left < 24:
                            score += 2.0
                        elif hours_left < 72:
                            score += 1.0
                except Exception:
                    pass
            
            # 수신 타입 (TO가 우선)
            recipient_type = (todo.get("recipient_type") or "to").lower()
            if recipient_type == "to":
                score += 0.5
            
            scored.append((score, todo))
        
        # 점수순 정렬
        scored.sort(key=lambda x: x[0], reverse=True)
        
        # 상위 50개 반환
        return [todo for _, todo in scored[:50]]
    
    def _extract_rule_keywords(self, natural_rule: str) -> Dict[str, List[str]]:
        """자연어 규칙에서 키워드 추출
        
        Args:
            natural_rule: 자연어 규칙
            
        Returns:
            {"requesters": [...], "projects": [...]}
        """
        if not natural_rule:
            return {}
        
        rule_lower = natural_rule.lower()
        keywords = {"requesters": [], "projects": []}
        
        # 프로젝트 코드 추출
        project_codes = ["cc", "ha", "well", "wi", "ci"]
        for code in project_codes:
            if code in rule_lower:
                keywords["projects"].append(code)
        
        # 사람 이름 추출 (VDOS DB에서)
        person_mapping = self._get_person_mapping()
        for email, name in person_mapping.items():
            name_lower = name.lower()
            if name_lower in rule_lower:
                # 이메일과 이름 모두 추가
                keywords["requesters"].append(email.lower())
                keywords["requesters"].append(name_lower)
        
        return keywords
