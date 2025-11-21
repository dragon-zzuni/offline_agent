# -*- coding: utf-8 -*-
"""
Top3 TODO 선정 및 규칙 관리 서비스 (오케스트레이터)

TODO 항목의 우선순위를 계산하고 Top3를 자동으로 선정합니다.
자연어 규칙 해석 및 LLM 기반 Top3 선정을 지원합니다.

이 클래스는 다음 컴포넌트들을 조율합니다:
- Top3LLMSelector: LLM 기반 Top3 선정
- Top3ScoreCalculator: 점수 기반 Top3 선정 (폴백)
- Top3CacheManager: 선정 결과 캐싱
"""
import os
import json
import logging
import re
from copy import deepcopy
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Set

logger = logging.getLogger(__name__)

# Top-3 규칙 기본값
TOP3_RULE_DEFAULT = {
    "priority_high": 3.0,
    "priority_medium": 2.0,
    "priority_low": 1.0,
    "deadline_emphasis": 24.0,
    "deadline_base": 1.0,
    "evidence_per_item": 0.1,
    "evidence_max_bonus": 0.5,
    "recipient_type_cc_penalty": 0.7,
}

# 엔티티 규칙 기본값
ENTITY_RULES_DEFAULT = {
    "requester": {},
    "type": {},
}


class Top3Service:
    """Top3 TODO 선정 및 규칙 관리 서비스 (오케스트레이터)"""
    
    def __init__(
        self, 
        config_path: Optional[str] = None, 
        people_data: Optional[List[Dict]] = None, 
        vdos_connector=None,
        persona_cache_service=None
    ):
        """
        Args:
            config_path: 규칙 저장 경로 (선택사항)
            people_data: 사람 정보 리스트 (이메일→이름 매핑용)
            vdos_connector: VDOSConnector 인스턴스 (실시간 people 데이터용)
            persona_cache_service: PersonaTodoCacheService 인스턴스 (TODO 캐시용)
        """
        # VDOS DB 위치에 설정 파일 저장
        if config_path is None:
            if vdos_connector and vdos_connector.is_available:
                # vdos.db와 같은 디렉토리에 저장
                vdos_dir = os.path.dirname(vdos_connector.vdos_db_path)
                config_path = os.path.join(vdos_dir, "top3_config.json")
            else:
                # 폴백: 기본 경로
                config_path = os.path.join("data", "top3_config.json")
        
        self.config_path = config_path
        self._rules = deepcopy(TOP3_RULE_DEFAULT)
        self._entity_rules = deepcopy(ENTITY_RULES_DEFAULT)
        self._last_instruction = ""
        self._last_reasoning = ""  # 마지막 선정 이유 (한국어)
        self._vdos_connector = vdos_connector
        self._persona_cache_service = persona_cache_service
        
        # 이메일 → 이름 매핑 구축
        self._email_to_name = {}
        
        # people_data 로드 우선순위: 1) 파라미터, 2) VDOS, 3) JSON 파일
        if people_data is None:
            if vdos_connector and vdos_connector.is_available:
                people_data = vdos_connector.get_people()
                logger.info(f"[Top3Service] VDOS에서 people 데이터 로드: {len(people_data)}명")
            else:
                people_data = self._load_people_data()
        
        if people_data:
            for person in people_data:
                email = person.get("email_address", "")
                name = person.get("name", "")
                if email and name:
                    self._email_to_name[email.lower()] = name
                    logger.debug(f"[Top3Service] 이메일 매핑: {email} → {name}")
        
        logger.info(f"[Top3Service] 초기화 완료: {len(self._email_to_name)}개 이메일 매핑")
        
        # 컴포넌트 초기화 (lazy loading)
        self._llm_selector = None
        self._score_calculator = None
        self._cache_manager = None
        self._llm_enabled = True  # LLM 사용 여부
        self._llm_failure_count = 0  # 연속 실패 횟수
        self._max_llm_failures = 3  # 최대 연속 실패 횟수
        
        # 저장된 규칙 로드
        self._load_rules()
    
    def _get_llm_selector(self):
        """LLM Selector lazy initialization"""
        if self._llm_selector is None:
            from .top3_llm_selector import Top3LLMSelector
            from .llm_client import LLMClient
            
            llm_client = LLMClient()
            cache_manager = self._get_cache_manager()
            
            self._llm_selector = Top3LLMSelector(
                llm_client=llm_client,
                cache_manager=cache_manager,
                email_to_name=self._email_to_name
            )
            logger.debug("[Top3Service] LLM Selector 초기화 완료")
        
        return self._llm_selector
    
    def _get_score_calculator(self):
        """Score Calculator lazy initialization"""
        if self._score_calculator is None:
            from .top3_score_calculator import Top3ScoreCalculator
            
            self._score_calculator = Top3ScoreCalculator(
                rules=self._rules,
                entity_rules=self._entity_rules,
                email_to_name=self._email_to_name
            )
            logger.debug("[Top3Service] Score Calculator 초기화 완료")
        
        return self._score_calculator
    
    def _get_cache_manager(self):
        """Cache Manager lazy initialization"""
        if self._cache_manager is None:
            from .top3_cache_manager import Top3CacheManager
            
            self._cache_manager = Top3CacheManager(ttl_seconds=300)  # 5분 TTL
            logger.debug("[Top3Service] Cache Manager 초기화 완료")
        
        return self._cache_manager
    
    def _load_people_data(self) -> List[Dict]:
        """people 데이터 자동 로드"""
        try:
            # people 파일 찾기 (절대 경로 및 상대 경로 모두 시도)
            data_dir = os.path.dirname(self.config_path)
            
            # 절대 경로가 아니면 현재 디렉토리 기준으로 변환
            if not os.path.isabs(data_dir):
                data_dir = os.path.abspath(data_dir)
            
            logger.debug(f"[Top3Service] people 데이터 검색 경로: {data_dir}")
            
            if not os.path.exists(data_dir):
                logger.warning(f"[Top3Service] 데이터 디렉토리가 존재하지 않습니다: {data_dir}")
                return []
            
            people_files = [f for f in os.listdir(data_dir) if f.startswith("people_") and f.endswith(".json")]
            
            if not people_files:
                logger.warning(f"[Top3Service] people 데이터 파일을 찾을 수 없습니다 (경로: {data_dir})")
                return []
            
            # 가장 최신 파일 사용
            people_file = sorted(people_files)[-1]
            people_path = os.path.join(data_dir, people_file)
            
            logger.debug(f"[Top3Service] people 파일 로드 시도: {people_path}")
            
            with open(people_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                people_list = data.get("people", [])
                logger.info(f"[Top3Service] people 데이터 로드 성공: {people_file} ({len(people_list)}명)")
                return people_list
        except Exception as e:
            logger.error(f"[Top3Service] people 데이터 로드 실패: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return []
    
    def get_rules(self) -> Dict[str, float]:
        """현재 규칙 반환"""
        return dict(self._rules)
    
    def get_entity_rules(self) -> Dict[str, Dict[str, float]]:
        """현재 엔티티 규칙 반환"""
        return {k: dict(v) for k, v in self._entity_rules.items()}
    
    def get_last_instruction(self) -> str:
        """마지막 자연어 지시사항 반환"""
        return self._last_instruction
    
    def set_rules(self, new_rules: Dict[str, float]) -> None:
        """규칙 설정"""
        for key, default in TOP3_RULE_DEFAULT.items():
            value = new_rules.get(key)
            if value is None:
                continue
            
            # 유효성 검사
            if not isinstance(value, (int, float)):
                continue
            
            # 범위 제한
            if key.startswith("priority_"):
                if value < 0:
                    value = 0.0
                if value > 10:
                    value = 10.0
            elif key == "deadline_emphasis":
                if value < 0:
                    value = 0.0
                if value > 100:
                    value = 100.0
            elif key == "deadline_base":
                if value < 0:
                    value = 0.0
                if value > 10:
                    value = 10.0
            elif key == "evidence_per_item":
                if value < 0:
                    value = 0.0
                if value > 1:
                    value = 1.0
            elif key == "evidence_max_bonus":
                if value < 0:
                    value = 0.0
            elif key == "recipient_type_cc_penalty":
                if value < 0:
                    value = 0.0
                if value > 1:
                    value = 1.0
            
            self._rules[key] = value
        
        # ScoreCalculator 업데이트
        if self._score_calculator is not None:
            self._score_calculator.update_rules(self._rules)
    
    def update_entity_rules(self, new_rules: Optional[Dict[str, Dict[str, float]]], reset: bool = False) -> None:
        """엔티티 규칙 업데이트"""
        if reset:
            for cat in ENTITY_RULES_DEFAULT:
                self._entity_rules[cat].clear()
        
        if not new_rules:
            return
        
        for category, mapping in new_rules.items():
            if category not in self._entity_rules:
                continue
            
            dest = self._entity_rules[category]
            for key, value in (mapping or {}).items():
                if value is None:
                    dest.pop(key, None)
                    continue
                
                if not isinstance(value, (int, float)):
                    continue
                
                # 범위 제한
                if value < -10:
                    value = -10.0
                if value > 10:
                    value = 10.0
                
                dest[key] = value
                
                # 한국어 이름 변형 처리
                if category == "requester":
                    from .top3_korean_utils import normalize_korean_name, generate_korean_name_variations
                    
                    normalized = normalize_korean_name(key)
                    if normalized != key:
                        dest[normalized] = max(dest.get(normalized, 0.0), value)
                    
                    variations = generate_korean_name_variations(key)
                    for variation in variations:
                        if variation not in dest:
                            dest[variation] = value
                        else:
                            dest[variation] = max(dest.get(variation, 0.0), value)
        
        # ScoreCalculator 업데이트
        if self._score_calculator is not None:
            self._score_calculator.update_entity_rules(self._entity_rules)
    
    def calculate_score(self, todo: Dict) -> float:
        """TODO 항목의 점수 계산 (ScoreCalculator로 위임)"""
        score_calculator = self._get_score_calculator()
        return score_calculator.calculate_score(todo)
    

    
    def pick_top3(self, items: List[Dict], use_llm: bool = True, simulation_time: Optional[datetime] = None) -> Set[str]:
        """Top3 TODO 선정 (LLM 또는 점수 기반)
        
        Args:
            items: TODO 항목 리스트
            use_llm: LLM 사용 여부 (기본값: True)
            simulation_time: 시뮬레이션 시간 (None이면 현재 시간 사용)
        
        Returns:
            Set[str]: Top3 TODO ID 집합
        
        선정 방식:
        1. 중복 제거 (같은 source_message는 1개만)
        2. 자연어 규칙이 있고 LLM이 활성화되어 있으면 LLM 선정 시도
        3. LLM 실패 시 점수 기반 선정으로 폴백
        4. 자연어 규칙이 없으면 점수 기반 선정
        """
        # 1. status가 done이 아닌 것만 후보
        candidates = [x for x in items if (x.get("status") or "pending") not in ("done",)]
        
        if not candidates:
            logger.info("[Top3Service] 후보 TODO가 없습니다")
            return set()
        
        # 2. 중복 제거는 TodoPanel에서 이미 처리됨 (제목 포함한 identity 기반)
        # 여기서 추가 중복 제거를 하면 같은 메시지에서 나온 서로 다른 TODO들이 제거됨
        # candidates = self._deduplicate_by_source(candidates)
        
        logger.info(f"[Top3Service] 📊 Top3 후보: {len(candidates)}개 TODO")
        
        # 2. 자연어 규칙 확인 (entity_rules 또는 last_instruction이 있으면 자연어 규칙 있음)
        has_natural_rules = bool(
            self._last_instruction or  # 자연어 텍스트가 있으면 규칙 있음
            self._entity_rules.get("requester") or 
            self._entity_rules.get("keyword") or 
            self._entity_rules.get("type")
        )
        
        # 3. LLM 선정 시도 (조건: 자연어 규칙 있음 + LLM 활성화 + use_llm=True)
        if has_natural_rules and self._llm_enabled and use_llm:
            logger.info(f"[Top3Service] 🤖 LLM 모드: 자연어 규칙 기반 Top3 선정 시도")
            
            try:
                llm_selector = self._get_llm_selector()
                
                # LLM 선정 실행
                top3_ids = llm_selector.select_top3(
                    todos=candidates,
                    natural_rule=self._last_instruction,
                    entity_rules=self._entity_rules,
                    simulation_time=simulation_time
                )
                
                if top3_ids:
                    # LLM 선정 성공
                    self._llm_failure_count = 0  # 실패 카운터 리셋
                    # 선정 이유 저장
                    self._last_reasoning = llm_selector.last_reasoning
                    logger.info(f"[Top3Service] ✅ LLM 선정 성공: {len(top3_ids)}개 선정")
                    return top3_ids
                else:
                    # LLM이 빈 결과 반환 (규칙에 맞는 TODO 없음)
                    logger.warning(f"[Top3Service] ⚠️ LLM이 빈 결과 반환 (규칙에 맞는 TODO 없음)")
                    return set()
            
            except Exception as e:
                # LLM 선정 실패 - 폴백으로 전환
                self._llm_failure_count += 1
                logger.error(f"[Top3Service] ❌ LLM 선정 실패 ({self._llm_failure_count}/{self._max_llm_failures}): {e}")
                
                # 연속 실패 시 LLM 비활성화
                if self._llm_failure_count >= self._max_llm_failures:
                    self._llm_enabled = False
                    logger.warning(
                        f"[Top3Service] 🚫 LLM 연속 {self._max_llm_failures}회 실패 - "
                        f"점수 기반 선정으로 자동 전환됩니다"
                    )
                
                # 점수 기반 선정으로 폴백
                logger.info("[Top3Service] 📊 폴백: 점수 기반 선정으로 전환")
        
        # 4. 점수 기반 선정 (폴백 또는 기본 모드)
        if has_natural_rules:
            # 자연어 규칙이 있으면 규칙 매칭 TODO만 선정
            logger.info(f"[Top3Service] 🔒 강제 모드: 자연어 규칙에 맞는 TODO만 선정")
            
            score_calculator = self._get_score_calculator()
            top3_ids = score_calculator.select_top3_with_rules(
                candidates=candidates,
                entity_rules=self._entity_rules
            )
            
            if not top3_ids:
                logger.warning(f"[Top3Service] ⚠️ 규칙에 맞는 TODO가 없음 (전체 {len(candidates)}개 중)")
            else:
                logger.info(f"[Top3Service] ✅ 강제 모드 완료: {len(top3_ids)}개 선정")
            
            return top3_ids
        else:
            # 자연어 규칙이 없으면 일반 점수 기반 선정
            logger.info(f"[Top3Service] 📊 일반 모드: 점수 기반 Top3 선정")
            
            score_calculator = self._get_score_calculator()
            top3_ids = score_calculator.select_top3(candidates)
            
            logger.info(f"[Top3Service] ✅ 일반 모드 완료: {len(candidates)}개 중 {len(top3_ids)}개 선정")
            return top3_ids
    
    def enable_llm(self) -> None:
        """LLM 선정 활성화"""
        self._llm_enabled = True
        self._llm_failure_count = 0
        logger.info("[Top3Service] LLM 선정 활성화")
    
    def disable_llm(self) -> None:
        """LLM 선정 비활성화"""
        self._llm_enabled = False
        logger.info("[Top3Service] LLM 선정 비활성화")
    
    def is_llm_enabled(self) -> bool:
        """LLM 선정 활성화 여부 확인"""
        return self._llm_enabled
    
    def describe_rules(self) -> str:
        """현재 규칙을 텍스트로 설명"""
        rules = self.get_rules()
        entity_rules = self.get_entity_rules()
        
        # 자연어 규칙 확인
        has_natural_rules = bool(entity_rules.get("requester") or 
                                 entity_rules.get("keyword") or 
                                 entity_rules.get("type"))
        
        parts = []
        
        # LLM 상태 표시
        if has_natural_rules:
            if self._llm_enabled:
                parts.append("🤖 LLM 모드: 자연어 규칙 기반 지능형 선정")
            else:
                parts.append("🔒 강제 모드: 자연어 규칙에 맞는 TODO만 Top3 표시 (LLM 비활성화)")
            
            if entity_rules.get("requester"):
                requester_list = ", ".join(list(entity_rules["requester"].keys())[:5])
                if len(entity_rules["requester"]) > 5:
                    requester_list += f" 외 {len(entity_rules['requester']) - 5}명"
                parts.append(f"  • 요청자: {requester_list}")
            
            if entity_rules.get("keyword"):
                keyword_list = ", ".join(list(entity_rules["keyword"].keys())[:5])
                if len(entity_rules["keyword"]) > 5:
                    keyword_list += f" 외 {len(entity_rules['keyword']) - 5}개"
                parts.append(f"  • 키워드: {keyword_list}")
            
            if entity_rules.get("type"):
                type_list = ", ".join(list(entity_rules["type"].keys())[:5])
                if len(entity_rules["type"]) > 5:
                    type_list += f" 외 {len(entity_rules['type']) - 5}개"
                parts.append(f"  • 타입: {type_list}")
        else:
            parts.append("📊 일반 모드: 점수 기반 Top3 선정")
        
        parts.extend([
            f"우선순위 가중치 H/M/L: {rules.get('priority_high',0):.2f}/{rules.get('priority_medium',0):.2f}/{rules.get('priority_low',0):.2f}",
            f"데드라인 강조: {rules.get('deadline_emphasis',0):.1f}시간",
            f"근거당 가중치: {rules.get('evidence_per_item',0):.2f} (최대 {rules.get('evidence_max_bonus',0):.2f})",
            f"CC/BCC 페널티: {rules.get('recipient_type_cc_penalty',0):.2f}",
        ])
        
        return "\n".join(parts)
    
    def apply_natural_language_rules(self, text: str, reset: bool = False) -> Tuple[str, str]:
        """
        자연어 지시사항을 규칙으로 변환
        
        Args:
            text: 자연어 지시사항
            reset: 규칙 초기화 여부
            
        Returns:
            Tuple[str, str]: (결과 메시지, 현재 규칙 설명)
        """
        cleaned_text = text.strip()
        
        if reset or not cleaned_text:
            self._last_instruction = "" if reset else cleaned_text
            self.set_rules(TOP3_RULE_DEFAULT)
            self.update_entity_rules({}, reset=True)
            self._save_rules()
            
            # 초기화 시 캐시 삭제
            if self._llm_selector:
                self._llm_selector.cache_manager.clear()
                logger.info("[Top3Service] 규칙 초기화로 인한 캐시 삭제")
            
            logger.info("[Top3Service] rules reset by user input")
            return "규칙을 기본값으로 초기화했습니다.", self.describe_rules()
        
        # LLM 파싱 먼저 시도 (더 정확함)
        logger.info(f"[Top3Service] 자연어 규칙 파싱 시작: '{cleaned_text[:50]}...'")
        parsed, llm_message = self._try_llm_parse_rules(cleaned_text)
        
        if parsed:
            logger.info(f"[Top3Service] LLM 파싱 성공: {llm_message}")
        else:
            # LLM 실패 시 휴리스틱 파싱으로 폴백
            logger.warning(f"[Top3Service] LLM 파싱 실패, 휴리스틱 파싱으로 폴백")
            parsed, heuristic_note = self._heuristic_parse_rules(cleaned_text)
            
            if parsed:
                logger.info(f"[Top3Service] 휴리스틱 파싱 성공: {heuristic_note}")
                llm_message = heuristic_note
            else:
                logger.warning(f"[Top3Service] 휴리스틱 파싱도 실패")
        
        if not parsed:
            msg = "규칙을 해석하지 못했습니다. 더 명확하게 입력해주세요."
            if llm_message:
                msg += f" (상세: {llm_message})"
            logger.warning(f"[Top3Service] 규칙 파싱 최종 실패: {msg}")
            return msg, self.describe_rules()
        
        # 규칙 적용
        if parsed.get("reset"):
            self._last_instruction = ""
            self.set_rules(TOP3_RULE_DEFAULT)
            self.update_entity_rules({}, reset=True)
            self._save_rules()
            return "규칙을 기본값으로 초기화했습니다.", self.describe_rules()
        
        # 가중치 업데이트
        weights = parsed.get("weights")
        if weights:
            self.set_rules(weights)
        
        # 엔티티 규칙 업데이트
        entities = parsed.get("entities")
        if entities:
            self.update_entity_rules(entities, reset=False)
        
        self._last_instruction = cleaned_text
        self._save_rules()
        
        # 규칙 변경 시 캐시 삭제 (새로운 규칙으로 재선정하기 위해)
        if self._llm_selector:
            self._llm_selector.cache_manager.clear()
            logger.info("[Top3Service] 규칙 변경으로 인한 캐시 삭제")
        
        result_msg = "규칙을 업데이트했습니다."
        if llm_message:
            result_msg += f" ({llm_message})"
        
        return result_msg, self.describe_rules()
    
    def _try_llm_parse_rules(self, text: str) -> Tuple[Optional[Dict], str]:
        """LLM을 사용하여 자연어 규칙 파싱"""
        # LLM 설정 확인
        provider = os.environ.get("LLM_PROVIDER", "openai").lower()
        
        if provider == "openai":
            api_key = os.environ.get("OPENAI_API_KEY")
            url = "https://api.openai.com/v1/chat/completions"
            model = "gpt-4o-mini"
        elif provider == "azure":
            api_key = os.environ.get("AZURE_OPENAI_KEY")
            endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
            deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
            api_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
            url = f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"
            model = deployment
        elif provider == "openrouter":
            api_key = os.environ.get("OPENROUTER_API_KEY")
            url = "https://openrouter.ai/api/v1/chat/completions"
            model = "openai/gpt-4o-mini"
        else:
            return None, f"지원하지 않는 LLM 제공자: {provider}"
        
        if not api_key:
            return None, "LLM API 키가 설정되지 않았습니다"
        
        # 프롬프트 생성
        system_prompt = """당신은 TODO 우선순위 규칙을 해석하는 전문가입니다.
사용자의 자연어 지시사항을 JSON 형식의 규칙으로 변환하세요.

**중요: 반드시 유효한 JSON 형식으로만 응답하세요. 설명이나 추가 텍스트 없이 JSON만 출력하세요.**

**우선순위 키워드에 따른 보너스 점수 가이드**
- "최우선", "무조건", "항상", "반드시", "가장 먼저", "제일": requester 보너스 8.0~10.0 (매우 높게!)
- "우선", "중요", "먼저": requester 보너스 4.0~6.0
- "보통", "일반": requester 보너스 2.0~3.0
- "낮음", "나중에": requester 보너스 0.5~1.5

**응답 형식:**
{
  "reset": false,
  "weights": {
    "priority_high": 3.0,
    "priority_medium": 2.0,
    "priority_low": 1.0,
    "deadline_emphasis": 24.0
  },
  "entities": {
    "requester": {"김철수": 8.0, "이영희": 4.0},
    "keyword": {"긴급": 3.0, "버그": 2.5},
    "type": {"버그수정": 3.0, "기능개발": 2.0},
    "time_range": {"오늘": 5.0, "이번주": 3.0}
  },
  "filters": {
    "created_after": "2025-10-20",
    "created_before": "2025-10-28",
    "status": ["pending", "in_progress"]
  }
}

**규칙:**
- reset: true면 모든 규칙 초기화 (사용자가 명시적으로 "초기화", "리셋", "reset" 등을 요청한 경우에만!)
- weights: 우선순위 가중치 (0~10)
  - priority_high/medium/low: 우선순위별 기본 가중치
  - deadline_emphasis: 데드라인 강조 (시간 단위)
- entities: 엔티티별 보너스 점수 (0~10)
  - requester: 요청자 이름 (최우선은 8.0 이상!)
  - keyword: 제목/내용의 키워드
  - type: TODO 유형
  - time_range: 시간 범위 ("오늘", "이번주", "이번달" 등)
- filters: 필터 조건 (선택사항)
  - created_after/before: 생성 날짜 범위
  - status: 상태 필터

**중요: reset은 사용자가 명시적으로 초기화를 요청한 경우에만 true로 설정하세요!**
**일반적인 규칙 추가 요청에는 reset을 포함하지 마세요!**

**예시:**
입력: "유준영 최우선"
출력: {"entities": {"requester": {"유준영": 9.0}}}

입력: "요청자가 전형우일 경우 우선순위 높게"
출력: {"entities": {"requester": {"전형우": 5.0}}}

입력: "버그 보고서는 긴급하게"
출력: {"entities": {"keyword": {"버그": 4.0, "보고서": 3.0}, "type": {"버그": 4.0}}}

입력: "오늘 생성된 TODO 우선"
출력: {"entities": {"time_range": {"오늘": 5.0}}, "filters": {"created_after": "2025-10-28"}}

입력: "이번주 데드라인 강조"
출력: {"weights": {"deadline_emphasis": 48.0}, "entities": {"time_range": {"이번주": 4.0}}}

입력: "김철수 우선, 버그 관련 중요"
출력: {"entities": {"requester": {"김철수": 5.0}, "keyword": {"버그": 3.5}}}

입력: "초기화"
출력: {"reset": true}
"""
        
        try:
            import requests
            
            headers = {"Authorization": f"Bearer {api_key}"}
            if provider == "openrouter":
                headers["HTTP-Referer"] = "https://github.com/your-repo"
            
            # Azure는 JSON 형식을 명시적으로 요청해야 함
            user_message = text
            if provider == "azure":
                user_message = f"{text}\n\n반드시 유효한 JSON 형식으로만 응답하세요."
            
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                "temperature": 0.3,
            }
            
            if provider in ("openai", "openrouter"):
                payload["response_format"] = {"type": "json_object"}
            
            logger.info("[Top3Service][LLM] provider=%s URL=%s text=%s", provider, url[:100], text[:200])
            logger.debug("[Top3Service][LLM] payload=%s", json.dumps(payload, ensure_ascii=False)[:500])
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code != 200:
                error_detail = response.text[:500]
                logger.error("[Top3Service][LLM] HTTP %d: %s", response.status_code, error_detail)
            
            response.raise_for_status()
            resp_json = response.json()
            
            logger.debug("[Top3Service][LLM] response=%s", json.dumps(resp_json, ensure_ascii=False)[:500])
            
            choices = resp_json.get("choices") or []
            if not choices:
                logger.error("[Top3Service][LLM] 응답에 choices가 없음: %s", json.dumps(resp_json, ensure_ascii=False)[:500])
                return None, "LLM 응답이 비어있습니다"
            
            content = choices[0].get("message", {}).get("content", "")
            logger.debug("[Top3Service][LLM] content=%s", content[:500])
            
            if not content or not content.strip():
                logger.error("[Top3Service][LLM] 응답 내용이 비어있음")
                return None, "LLM 응답 내용이 비어있습니다"
            
            # JSON 파싱 시도
            try:
                parsed = json.loads(content)
                logger.info("[Top3Service] LLM 파싱 성공: %s", json.dumps(parsed, ensure_ascii=False)[:200])
                return parsed, "LLM 파싱 성공"
            except json.JSONDecodeError as json_err:
                logger.error("[Top3Service][LLM] JSON 파싱 실패: %s, content=%s", json_err, content[:200])
                # JSON이 아닌 경우 텍스트에서 추출 시도
                return None, f"JSON 파싱 실패: {json_err}"
            
        except requests.RequestException as exc:
            logger.warning("[Top3Service][LLM] request error: %s", exc)
            return None, f"LLM 요청 실패: {exc}"
        except Exception as exc:
            logger.warning("[Top3Service][LLM] processing error: %s", exc)
            import traceback
            logger.debug(traceback.format_exc())
            return None, f"LLM 처리 오류: {exc}"
    
    def _heuristic_parse_rules(self, text: str) -> Tuple[Optional[Dict], str]:
        """휴리스틱 방식으로 자연어 규칙 파싱"""
        lower = text.lower()
        
        logger.debug(f"[Top3Service] 휴리스틱 파싱 시작: '{text}'")
        
        # 초기화 키워드
        if any(word in lower for word in ["초기화", "리셋", "reset", "기본값"]):
            logger.debug("[Top3Service] 초기화 키워드 감지")
            return {"reset": True}, "휴리스틱으로 초기화 명령을 감지했습니다."
        
        # 복합 조건 감지 (LLM으로 넘김)
        complex_keywords = ["이고", "이며", "그리고", "and", "참조", "cc", "bcc", "직접", "to"]
        if any(keyword in lower for keyword in complex_keywords):
            logger.debug(f"[Top3Service] 복합 조건 감지 - LLM 파싱으로 전환")
            return None, "복합 조건이 감지되어 LLM 파싱이 필요합니다"
        
        result = {"weights": {}, "entities": {"requester": {}, "type": {}}}
        
        # 우선순위 키워드 (확장)
        priority_weights = {}
        high_priority_words = ["high", "높", "긴급", "중요", "최우선", "급함", "시급", "제일", "높게", "높은"]
        
        if any(word in lower for word in high_priority_words):
            current_high = priority_weights.get("priority_high", TOP3_RULE_DEFAULT["priority_high"])
            priority_weights["priority_high"] = max(current_high, TOP3_RULE_DEFAULT["priority_high"] + 2.0)
            logger.debug(f"[Top3Service] 높은 우선순위 키워드 감지: priority_high={priority_weights['priority_high']:.2f}")
        
        if any(word in lower for word in ["medium", "중간", "보통"]):
            priority_weights["priority_medium"] = max(
                priority_weights.get("priority_medium", TOP3_RULE_DEFAULT["priority_medium"]),
                TOP3_RULE_DEFAULT["priority_medium"] + 0.5
            )
            logger.debug(f"[Top3Service] 중간 우선순위 키워드 감지: priority_medium={priority_weights['priority_medium']:.2f}")
        
        if any(word in lower for word in ["low", "낮", "덜 중요", "낮게", "최하위"]):
            priority_weights["priority_low"] = max(0.2, TOP3_RULE_DEFAULT["priority_low"] - 2.0)
            logger.debug(f"[Top3Service] 낮은 우선순위 키워드 감지: priority_low={priority_weights['priority_low']:.2f}")
        
        if priority_weights:
            result["weights"].update(priority_weights)
        
        # 요청자 키워드 (우선순위에 따라 다른 보너스)
        # 최우선 키워드 체크
        is_top_priority = any(word in lower for word in ["최우선", "무조건", "항상", "반드시", "가장 먼저", "최고", "제일"])
        is_high_priority = any(word in lower for word in ["우선", "중요", "먼저", "높게", "높은"])
        
        # 보너스 점수 결정 (조정)
        if is_top_priority:
            name_bonus = 8.0  # 최우선: 매우 높은 보너스 (7.0 → 8.0)
        elif is_high_priority:
            name_bonus = 4.0  # 우선: 높은 보너스 (3.5 → 4.0)
        else:
            name_bonus = 2.0  # 기본 보너스
        
        logger.debug(f"[Top3Service] 요청자 보너스 점수: {name_bonus:.1f} (최우선={is_top_priority}, 우선={is_high_priority})")
        
        # 요청자 이름 추출 (개선된 패턴)
        # 패턴 1: "XXX이/가 요청자" 형태
        requester_pattern1 = r"([가-힣]{2,6})(?:이|가)\s*요청자"
        # 패턴 2: "요청자가 XXX일 경우" 형태 (가장 일반적)
        requester_pattern2 = r"요청자(?:가|는|이)?\s*([가-힣]{2,6})(?:일|이)?\s*(?:경우|때|면)"
        # 패턴 3: 일반 한글 이름 + 호칭
        requester_pattern3 = r"([가-힣]{2,6})\s*(?:님|씨|선생님|팀장|부장)"
        # 패턴 4: "XXX 요청" 형태
        requester_pattern4 = r"([가-힣]{2,6})\s*요청"
        
        matches = set()
        matches.update(re.findall(requester_pattern1, text))
        matches.update(re.findall(requester_pattern2, text))
        matches.update(re.findall(requester_pattern3, text))
        matches.update(re.findall(requester_pattern4, text))
        
        logger.debug(f"[Top3Service] 패턴 매칭 결과: {matches}")
        
        # 불용어 제거 (일반적인 단어 제외) - 확장
        stopwords = {
            "요청자", "우선순위", "최우선", "경우", "우선", "중요", "먼저", "높게", "높은", "제일",
            "요청", "순위", "규칙", "설정", "변경", "수정", "추가", "삭제", "초기화", "리셋"
        }
        matches = {name for name in matches if name not in stopwords and len(name) >= 2}
        
        # "XXX일", "XXX이" 형태 제거 (예: "정지원일" → "정지원", "김세린이" → "김세린")
        cleaned_matches = set()
        for name in matches:
            cleaned_name = name
            # "일" 제거
            if name.endswith("일") and len(name) > 2:
                cleaned_name = name[:-1]
                logger.debug(f"[Top3Service] 이름 정리 (일): {name} → {cleaned_name}")
            # "이" 제거 (조사)
            elif name.endswith("이") and len(name) > 2:
                cleaned_name = name[:-1]
                logger.debug(f"[Top3Service] 이름 정리 (이): {name} → {cleaned_name}")
            
            if len(cleaned_name) >= 2:
                cleaned_matches.add(cleaned_name)
        
        matches = cleaned_matches
        
        logger.debug(f"[Top3Service] 추출된 이름 후보: {matches}")
        
        for name in matches:
            result["entities"]["requester"][name] = name_bonus
            logger.debug(f"[Top3Service] 요청자 규칙 추가: {name} → 보너스 {name_bonus:.1f}")
            
            # 한국어 이름 정규화
            from .top3_korean_utils import normalize_korean_name
            normalized = normalize_korean_name(name)
            if normalized != name:
                result["entities"]["requester"][normalized] = name_bonus
                logger.debug(f"[Top3Service] 정규화된 이름 추가: {normalized} → 보너스 {name_bonus:.1f}")
        
        # 유형(type) 키워드 추출
        # 패턴: "XXX 유형", "XXX 타입", "XXX 관련", "XXX TODO"
        type_pattern1 = r"([가-힣a-zA-Z]{2,10})\s*(?:유형|타입|관련|TODO)"
        # 패턴: "유형이 XXX", "타입이 XXX"
        type_pattern2 = r"(?:유형|타입)(?:이|가)?\s*([가-힣a-zA-Z]{2,10})"
        
        type_matches = set()
        type_matches.update(re.findall(type_pattern1, text))
        type_matches.update(re.findall(type_pattern2, text))
        
        # 불용어 제거
        type_stopwords = {"유형", "타입", "관련", "TODO", "경우", "우선", "중요", "먼저", "높게"}
        type_matches = {t for t in type_matches if t not in type_stopwords and len(t) >= 2}
        
        logger.debug(f"[Top3Service] 추출된 유형 후보: {type_matches}")
        
        for type_name in type_matches:
            result["entities"]["type"][type_name] = name_bonus
            logger.debug(f"[Top3Service] 유형 규칙 추가: {type_name} → 보너스 {name_bonus:.1f}")
        
        # 결과 확인
        if not result["weights"] and not result["entities"]["requester"] and not result["entities"]["type"]:
            return None, "규칙을 해석할 수 없습니다"
        
        note = "휴리스틱으로 규칙을 해석했습니다."
        if result["entities"]["requester"]:
            note += f" (요청자: {', '.join(result['entities']['requester'].keys())})"
        if result["entities"]["type"]:
            note += f" (유형: {', '.join(result['entities']['type'].keys())})"
        
        return result, note
    
    def _save_rules(self) -> None:
        """규칙을 파일에 저장"""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            data = {
                "weights": self.get_rules(),
                "entities": self.get_entity_rules(),
                "instruction": self._last_instruction
            }
            
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info("[Top3Service] rules saved to %s", self.config_path)
        except Exception as exc:
            logger.error("[Top3Service] failed to save rules: %s", exc)
    
    def _load_rules(self) -> None:
        """파일에서 규칙 로드"""
        try:
            if not os.path.exists(self.config_path):
                return
            
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            weights = data.get("weights")
            entities = data.get("entities")
            instruction = data.get("instruction")
            
            if isinstance(weights, dict) and weights:
                self.set_rules(weights)
            
            if isinstance(entities, dict):
                self.update_entity_rules(entities, reset=True)
            
            if isinstance(instruction, str):
                self._last_instruction = instruction
            
            logger.info("[Top3Service] rules loaded from %s", self.config_path)
        except Exception as exc:
            logger.warning("[Top3Service] failed to load rules: %s", exc)

    def get_last_reasoning(self) -> str:
        """마지막 Top3 선정 이유 가져오기 (한국어)
        
        Returns:
            선정 이유 문자열 (없으면 빈 문자열)
        """
        return self._last_reasoning
    
    def _deduplicate_by_source(self, todos: List[Dict]) -> List[Dict]:
        """같은 source_message를 가진 TODO 중복 제거
        
        같은 메시지에서 여러 유형의 TODO가 생성된 경우,
        우선순위가 가장 높은 유형 1개만 선택합니다.
        
        Args:
            todos: TODO 리스트
        
        Returns:
            중복 제거된 TODO 리스트
        """
        # 유형 우선순위 (TodoDeduplicationService와 동일)
        TYPE_PRIORITY = {
            "deadline": 6,
            "meeting": 5,
            "task": 4,
            "review": 3,
            "documentation": 2,
            "issue": 1,
        }
        
        # source_message별로 그룹화
        source_groups = {}
        for todo in todos:
            source_msg = todo.get("source_message")
            
            if not source_msg:
                # source_message가 없으면 개별 TODO로 처리
                unique_key = f"no_source_{todo.get('id', '')}"
                source_groups[unique_key] = [todo]
            else:
                # source_message가 dict인 경우 ID를 키로 사용
                if isinstance(source_msg, dict):
                    source_key = source_msg.get("id") or source_msg.get("message_id") or str(source_msg)
                else:
                    source_key = str(source_msg)
                
                if source_key not in source_groups:
                    source_groups[source_key] = []
                source_groups[source_key].append(todo)
        
        # 각 그룹에서 최선 TODO 선택
        deduplicated = []
        removed_count = 0
        
        for source_msg, group in source_groups.items():
            if len(group) == 1:
                # 중복 없음
                deduplicated.append(group[0])
            else:
                # 중복 있음 - 우선순위로 정렬
                sorted_group = sorted(
                    group,
                    key=lambda t: (
                        TYPE_PRIORITY.get(t.get("type", "task"), 0),
                        t.get("created_at", "")
                    ),
                    reverse=True
                )
                
                best_todo = sorted_group[0]
                deduplicated.append(best_todo)
                removed_count += len(group) - 1
                
                logger.debug(
                    f"[Top3Service] 중복 제거: source={source_msg}, "
                    f"{len(group)}개 중 {best_todo.get('type')} 선택"
                )
        
        if removed_count > 0:
            logger.info(
                f"[Top3Service] 🗑️ Top3 후보 중복 제거: "
                f"{len(todos)}개 → {len(deduplicated)}개 ({removed_count}개 제거)"
            )
        
        return deduplicated
