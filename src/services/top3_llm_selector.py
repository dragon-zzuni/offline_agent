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
        self.last_reasoning = ""  # 마지막 선정 이유 (한국어)
    
    def select_top3(
        self,
        todos: List[Dict],
        natural_rule: str,
        entity_rules: Optional[Dict[str, Dict[str, float]]] = None
    ) -> Tuple[Set[str], str]:
        """LLM으로 Top3 선정 (폴백 메커니즘 포함)
        
        Args:
            todos: TODO 리스트
            natural_rule: 자연어 규칙
            entity_rules: 엔티티 규칙 (캐시 키 생성용)
            
        Returns:
            (선정된 TODO ID 집합, 선정 이유)
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
        
        # 사전 필터링 제거: LLM이 모든 TODO를 직접 분석하도록 함
        # (자연어 규칙의 모든 조건을 정확히 적용하기 위해)
        logger.info(f"[Top3LLM] TODO {len(candidates)}개를 LLM에 전달 (사전 필터링 없음)")
        
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
        
        # 응답 내용 로깅 (항상 표시 - 디버깅용)
        logger.info(f"[Top3LLM] LLM 응답 내용:\n{response.content}")
        
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
        
        # 규칙 준수 검증 및 설명 개선
        reasoning = self._validate_and_explain_selection(
            valid_ids, candidates, natural_rule, reasoning
        )
        
        # 캐시 저장
        self.cache_manager.set(original_todos, valid_ids, entity_rules, natural_rule)
        
        # 선정 이유 저장 (한국어)
        self.last_reasoning = reasoning
        
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
            
            # 프로젝트 정보 (풀네임 우선, 없으면 코드)
            project_code = todo.get("project", "")
            project_fullname = todo.get("project_full_name", "")
            project_display = f"{project_fullname} ({project_code})" if project_fullname else project_code
            
            # ID를 더 명확하게 강조
            todo_id = todo.get("id", "")
            todo_type = todo.get("type", "")
            
            # 수신 방법 (메일/메시지)
            source_type = todo.get("source_type", "")
            source_display = ""
            if source_type == "email":
                source_display = "메일"
            elif source_type == "messenger":
                source_display = "메시지"
            else:
                source_display = source_type or "알 수 없음"
            
            todo_info = f"""[TODO #{i}]
→ ID: "{todo_id}" (이 ID를 그대로 사용하세요!)
→ 제목: {(todo.get("title") or "")[:80]}
→ 프로젝트: {project_display}
→ 요청자: {requester_name}
→ 유형: {todo_type}
→ 수신방법: {source_display}
→ 우선순위: {todo.get("priority", "medium")}
→ 마감일: {todo.get("deadline", "")}"""
            todo_list.append(todo_info)
        
        todos_text = "\n\n".join(todo_list)
        
        # 사람 매핑 정보도 프롬프트에 추가
        person_info = "\n".join([f"- {email}: {name}" for email, name in person_mapping.items()])
        person_section = f"\n\n사람 매핑 (이메일 → 이름):\n{person_info}" if person_info else ""
        
        prompt = f"""다음 TODO 리스트에서 사용자의 자연어 규칙에 가장 잘 맞는 상위 3개를 선정하여 JSON 형식으로 답변해주세요. 
반드시 소문자 json이라는 단어를 포함한 json 문자열로만 응답하세요.

**중요**: 모든 응답은 반드시 한국어로 작성하세요!

사용자 규칙: {natural_rule}
{person_section}

TODO 리스트 ({len(todos)}개):
{todos_text}

선정 기준 (반드시 순서대로 적용):
1. **프로젝트 조건을 최우선으로 정확히 만족**: 
   - 각 TODO의 "프로젝트" 필드를 확인하세요 (예: "Project LUMINA (PL)" 형태로 표시됨)
   - 사용자가 프로젝트 이름을 언급하면 (한글/영문/약어 모두 가능):
     * "LUMINA", "루미나", "PL" → "Project LUMINA (PL)" 또는 약어 "PL"이 포함된 TODO 선택
     * "CareBridge", "케어브릿지", "CI" → "CareBridge Integration (CI)" 또는 약어 "CI"가 포함된 TODO 선택
     * "Care Connect", "케어커넥트", "CC" → "Care Connect 2.0 (CC)" 또는 약어 "CC"가 포함된 TODO 선택
   - **중요**: 프로젝트 필드에 풀네임과 약어가 함께 표시되므로, 사용자가 어떤 형태로 입력해도 매칭되어야 합니다!
   - 프로젝트 조건이 맞지 않으면 절대 선택하지 마세요!

2. **요청자 조건을 정확히 만족**: 
   - "요청자(이 TODO를 생성한 사람)" 필드를 확인하세요
   - 사용자가 "전형우"라고 하면 요청자가 "전형우" 또는 "hyungwoo.jeon@example.com"인 TODO만 선택
   - 설명에 언급된 사람이 아니라 "요청자" 필드를 확인하세요!

3. **유형 조건을 절대적으로 만족 (매우 중요!)**: 
   - "유형" 필드를 확인하세요
   - 사용자가 "업무처리"라고 하면 **반드시** 유형이 "task"인 TODO**만** 선택
   - "문서검토"면 **반드시** 유형이 "review"인 TODO**만** 선택
   - "미팅"이면 **반드시** 유형이 "meeting"인 TODO**만** 선택
   - "마감작업"이면 **반드시** 유형이 "deadline"인 TODO**만** 선택
   - **절대로 다른 유형을 섞어서 선정하지 마세요!**
   - 예: "업무처리"를 요청했는데 "마감작업"이나 "미팅"을 선정하면 안 됩니다!

4. **수신방법 조건을 정확히 만족**:
   - "수신방법" 필드를 확인하세요
   - 사용자가 "메시지로 수신"이라고 하면 **반드시** 수신방법이 "메시지"인 TODO**만** 선택
   - "메일로 수신"이라고 하면 **반드시** 수신방법이 "메일"인 TODO**만** 선택
   - 수신방법 조건이 있으면 **절대로 다른 수신방법을 섞지 마세요!**

5. **위 1, 2, 3, 4 조건을 모두 만족하는 TODO 중에서** 마감일, 우선순위 등을 고려하여 3개 선정

6. **반드시 정확히 3개를 선정해야 합니다**:
   - 조건을 완벽히 만족하는 TODO가 3개 이상이면 → 그 중 3개 선정
   - 조건을 완벽히 만족하는 TODO가 3개 미만이면:
     a) 먼저 완벽히 만족하는 TODO를 모두 선정
     b) 부족한 개수만큼 조건을 **통일성 있게** 완화하여 추가 선정:
        - **유형 조건은 절대 완화하지 마세요** (가장 중요!)
        - **수신방법 조건은 절대 완화하지 마세요** (두 번째로 중요!)
        - **통일성 원칙**: 같은 방식으로 조건을 완화하세요
          * 예: 요청자만 다른 TODO 2개를 추가한다면, 둘 다 같은 프로젝트여야 함
          * 예: 프로젝트만 다른 TODO 2개를 추가한다면, 둘 다 같은 요청자여야 함
        - 완화 우선순위:
          1. 요청자 조건 완화 (같은 프로젝트 + 같은 유형 + 같은 수신방법)
          2. 프로젝트 조건 완화 (같은 요청자 + 같은 유형 + 같은 수신방법)
     c) reasoning에 어떤 조건을 완화했는지 명확히 설명
   - 예시 1: "PN 프로젝트의 전형우가 요청한 업무처리 TODO 1개를 선정하고, PN 프로젝트의 다른 요청자(임호규)가 요청한 업무처리 TODO 2개를 추가로 선정했습니다. (요청자 조건만 완화, 프로젝트와 유형은 통일)"
   - 예시 2: "완벽히 일치하는 TODO가 없어서, 전형우가 요청한 업무처리 TODO 3개를 선정했습니다. (프로젝트 조건 완화, 요청자와 유형은 통일)"

7. **매우 중요**: 
   - selected_ids에는 반드시 위 TODO 리스트의 "ID:" 필드에 있는 **정확한 ID**만 사용하세요
   - 예: TODO #5의 ID가 "abc123"이면 → "abc123"을 그대로 사용
   - 절대로 "task_103" 같은 존재하지 않는 ID를 만들지 마세요!
   - ID를 복사할 때 따옴표나 공백을 제거하세요

다음 형식으로 분석해주세요 (반드시 한국어로, reasoning을 먼저 작성):
{{
    "reasoning": "선정 이유를 한국어로 상세히 설명. 먼저 조건을 분석하고, 어떤 TODO들이 조건을 만족하는지 설명한 후, 최종적으로 선정한 3개의 TODO를 각각 설명. (예: 전형우가 요청한 CareBridge 프로젝트의 업무처리 TODO를 찾았습니다. TODO #5, #12, #18이 모두 프로젝트, 요청자, 유형 조건을 완벽히 만족하므로 이 3개를 선정합니다.)",
    "selected_ids": ["위_TODO_리스트의_실제_ID_1", "위_TODO_리스트의_실제_ID_2", "위_TODO_리스트의_실제_ID_3"]
}}

**중요**: reasoning에서 선정할 TODO의 번호(#)를 먼저 언급한 후, selected_ids에 해당 TODO의 실제 ID를 정확히 복사하세요!

**예시**:
만약 TODO #1(ID: "a1b2c3"), TODO #5(ID: "d4e5f6"), TODO #10(ID: "g7h8i9")을 선정한다면:
{{
    "reasoning": "전형우가 요청한 CareBridge 프로젝트의 업무처리 TODO를 찾았습니다. TODO #1, #5, #10이 모두 조건을 만족하므로 이 3개를 선정합니다.",
    "selected_ids": ["a1b2c3", "d4e5f6", "g7h8i9"]
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
프로젝트 태그, 요청자, 마감일, 우선순위, 키워드 등 모든 조건을 종합적으로 고려하여 분석하세요.

**중요**: 
- 모든 응답은 반드시 한국어로 작성하세요.
- 선정 이유(reasoning)도 반드시 한국어로 작성하세요."""
    
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
            
            # reasoning이 먼저 오도록 변경했지만 순서는 상관없음
            selected_ids = data.get("selected_ids", [])
            reasoning = data.get("reasoning", "")
            
            if not isinstance(selected_ids, list):
                logger.error(f"[Top3LLM] selected_ids가 리스트가 아닙니다: {type(selected_ids)}")
                return set(), reasoning
            
            if len(selected_ids) != 3:
                logger.warning(f"[Top3LLM] selected_ids 개수가 3개가 아닙니다: {len(selected_ids)}개")
            
            logger.info(f"[Top3LLM] 파싱된 ID: {selected_ids}")
            
            return set(selected_ids), reasoning
            
        except json.JSONDecodeError as e:
            logger.error(f"[Top3LLM] JSON 파싱 실패: {e}")
            logger.error(f"[Top3LLM] 응답 내용: {response[:500]}")
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
    
    def _validate_and_explain_selection(
        self,
        selected_ids: Set[str],
        todos: List[Dict],
        natural_rule: str,
        original_reasoning: str
    ) -> str:
        """선정 결과 검증 및 설명 개선
        
        Args:
            selected_ids: 선정된 TODO ID 집합
            todos: 전체 TODO 리스트
            natural_rule: 자연어 규칙
            original_reasoning: LLM이 생성한 원본 설명
            
        Returns:
            개선된 설명
        """
        try:
            # 선정된 TODO 가져오기
            selected_todos = [t for t in todos if t.get("id") in selected_ids]
            
            if not selected_todos:
                return original_reasoning
            
            # 규칙에서 조건 추출
            rule_lower = natural_rule.lower()
            
            # 프로젝트 조건 추출
            expected_project = None
            for todo in todos:
                project = todo.get("project", "")
                project_fullname = todo.get("project_full_name", "")
                if project and (project.lower() in rule_lower or (project_fullname and project_fullname.lower() in rule_lower)):
                    expected_project = project
                    break
            
            # 요청자 조건 추출
            expected_requester = None
            person_mapping = self._get_person_mapping()
            for email, name in person_mapping.items():
                if name and name in natural_rule:
                    expected_requester = name
                    break
            
            # 유형 조건 추출
            type_mapping = {
                "업무처리": "task",
                "문서검토": "review",
                "미팅": "meeting",
                "마감작업": "deadline"
            }
            expected_type = None
            for korean, english in type_mapping.items():
                if korean in natural_rule:
                    expected_type = english
                    break
            
            # 선정된 TODO 분석
            violations = []
            perfect_matches = []
            partial_matches = []
            
            for todo in selected_todos:
                todo_id = todo.get("id", "")
                project = todo.get("project", "")
                requester = todo.get("requester", "")
                requester_name = person_mapping.get(requester, requester)
                todo_type = todo.get("type", "")
                
                issues = []
                
                # 프로젝트 검증
                if expected_project and project != expected_project:
                    issues.append(f"프로젝트 불일치 (기대: {expected_project}, 실제: {project})")
                
                # 요청자 검증
                if expected_requester and requester_name != expected_requester:
                    issues.append(f"요청자 불일치 (기대: {expected_requester}, 실제: {requester_name})")
                
                # 유형 검증
                if expected_type and todo_type != expected_type:
                    issues.append(f"유형 불일치 (기대: {expected_type}, 실제: {todo_type})")
                
                if issues:
                    violations.append({
                        "id": todo_id,
                        "issues": issues,
                        "todo": todo
                    })
                    partial_matches.append(todo)
                else:
                    perfect_matches.append(todo)
            
            # 설명 개선
            if violations:
                # 규칙 위반이 있는 경우 명확한 설명 추가
                explanation_parts = [original_reasoning, "\n\n⚠️ 선정 결과 분석:"]
                
                if perfect_matches:
                    explanation_parts.append(f"\n✅ 완벽히 일치: {len(perfect_matches)}개")
                    for todo in perfect_matches:
                        explanation_parts.append(
                            f"  - {todo.get('id')}: "
                            f"프로젝트={todo.get('project')}, "
                            f"요청자={person_mapping.get(todo.get('requester'), todo.get('requester'))}, "
                            f"유형={todo.get('type')}"
                        )
                
                if partial_matches:
                    explanation_parts.append(f"\n⚠️ 부분 일치: {len(partial_matches)}개")
                    for violation in violations:
                        todo = violation["todo"]
                        explanation_parts.append(
                            f"  - {violation['id']}: "
                            f"프로젝트={todo.get('project')}, "
                            f"요청자={person_mapping.get(todo.get('requester'), todo.get('requester'))}, "
                            f"유형={todo.get('type')}"
                        )
                        for issue in violation["issues"]:
                            explanation_parts.append(f"    → {issue}")
                
                # 완화된 조건 설명
                if len(perfect_matches) < 3:
                    explanation_parts.append(
                        f"\n📝 조건 완화: 규칙을 완벽히 만족하는 TODO가 {len(perfect_matches)}개뿐이어서, "
                        f"부분적으로 일치하는 TODO {len(partial_matches)}개를 추가로 선정했습니다."
                    )
                
                return "".join(explanation_parts)
            
            # 모두 완벽히 일치하는 경우
            return original_reasoning
            
        except Exception as e:
            logger.error(f"[Top3LLM] 선정 결과 검증 오류: {e}")
            return original_reasoning
