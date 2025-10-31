# -*- coding: utf-8 -*-
"""
Top3 TODO 선정 및 규칙 관리 서비스 (Refactored - LLM 통합)

LLM 기반 선정을 우선 사용하고, 실패 시 점수 기반으로 폴백합니다.
"""
import os
import json
import logging
from copy import deepcopy
from typing import Dict, List, Optional, Tuple, Set

from .llm_client import LLMClient
from .top3_llm_selector import Top3LLMSelector
from .top3_score_calculator import Top3ScoreCalculator
from .top3_cache_manager import Top3CacheManager

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
    "keyword": {},
}


class Top3ServiceRefactored:
    """Top3 TODO 선정 및 규칙 관리 서비스 (LLM 통합)
    
    기존 Top3Service를 대체할 리팩토링 버전입니다.
    """
    
    def __init__(
        self,
        config_path: Optional[str] = None,
        people_data: Optional[List[Dict]] = None,
        vdos_connector=None,
        cache_service=None
    ):
        """
        Args:
            config_path: 규칙 저장 경로
            people_data: 사람 정보 리스트
            vdos_connector: VDOSConnector 인스턴스
            cache_service: PersonaTodoCacheService 인스턴스
        """
        # 설정 경로
        if config_path is None:
            if vdos_connector and hasattr(vdos_connector, 'is_available') and vdos_connector.is_available:
                vdos_dir = os.path.dirname(vdos_connector.vdos_db_path)
                config_path = os.path.join(vdos_dir, "top3_config.json")
            else:
                config_path = os.path.join("data", "top3_config.json")
        
        self.config_path = config_path
        self._vdos_connector = vdos_connector
        self._cache_service = cache_service
        
        # 규칙 초기화
        self._rules = deepcopy(TOP3_RULE_DEFAULT)
        self._entity_rules = deepcopy(ENTITY_RULES_DEFAULT)
        self._last_instruction = ""
        
        # 이메일 → 이름 매핑
        self._email_to_name = {}
        self._load_people_mapping(people_data)
        
        # LLM 관련 초기화
        self.llm_client = LLMClient()
        self.cache_manager = Top3CacheManager(default_ttl=300.0)
        self.llm_selector = Top3LLMSelector(self.llm_client, self.cache_manager)
        self.score_calculator = Top3ScoreCalculator(self._rules, self._entity_rules)
        
        # LLM 실패 추적
        self._llm_failure_count = 0
        self._llm_disabled = False
        
        # 저장된 규칙 로드
        self._load_rules()
        
        logger.info(
            f"[Top3Service] 초기화 완료 "
            f"(이메일 매핑: {len(self._email_to_name)}개, "
            f"LLM 사용 가능: {self.llm_client.is_available()})"
        )
    
    def _load_people_mapping(self, people_data: Optional[List[Dict]]) -> None:
        """사람 정보에서 이메일 → 이름 매핑 구축"""
        if people_data is None:
            if self._vdos_connector and hasattr(self._vdos_connector, 'is_available') and self._vdos_connector.is_available:
                people_data = self._vdos_connector.get_people()
                logger.info(f"[Top3Service] VDOS에서 people 데이터 로드: {len(people_data)}명")
            else:
                people_data = self._load_people_from_file()
        
        if people_data:
            for person in people_data:
                email = person.get("email_address", "")
                name = person.get("name", "")
                if email and name:
                    self._email_to_name[email.lower()] = name
    
    def _load_people_from_file(self) -> List[Dict]:
        """파일에서 people 데이터 로드"""
        try:
            data_dir = os.path.dirname(self.config_path)
            if not os.path.isabs(data_dir):
                data_dir = os.path.abspath(data_dir)
            
            if not os.path.exists(data_dir):
                return []
            
            people_files = [f for f in os.listdir(data_dir) if f.startswith("people_") and f.endswith(".json")]
            if not people_files:
                return []
            
            people_file = sorted(people_files)[-1]
            people_path = os.path.join(data_dir, people_file)
            
            with open(people_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("people", [])
        except Exception as e:
            logger.error(f"[Top3Service] people 데이터 로드 실패: {e}")
            return []
    
    def pick_top3(self, items: List[Dict]) -> Set[str]:
        """Top3 선정 (LLM 우선, 폴백은 점수 기반)
        
        Args:
            items: TODO 항목 리스트
            
        Returns:
            선정된 TODO ID 집합
        """
        if not items:
            logger.warning("[Top3Service] TODO 리스트가 비어있습니다")
            return set()
        
        # LLM 비활성화 상태면 점수 기반 사용
        if self._llm_disabled:
            logger.info("[Top3Service] LLM 비활성화 상태, 점수 기반 사용")
            return self._pick_with_score(items)
        
        # 자연어 규칙이 있으면 LLM 사용 시도
        if self._last_instruction and self._last_instruction.strip():
            try:
                logger.info(f"[Top3Service] LLM 선정 시도 (규칙: {self._last_instruction[:50]}...)")
                
                top3_ids = self.llm_selector.select_top3(
                    items,
                    self._last_instruction,
                    self._entity_rules
                )
                
                if top3_ids:
                    # 성공 시 실패 카운터 리셋
                    self._llm_failure_count = 0
                    logger.info(f"[Top3Service] LLM 선정 성공: {len(top3_ids)}개")
                    return top3_ids
                else:
                    # 빈 결과
                    self._llm_failure_count += 1
                    logger.warning(
                        f"[Top3Service] LLM 선정 실패 (빈 결과) "
                        f"({self._llm_failure_count}/3)"
                    )
                    
            except Exception as e:
                self._llm_failure_count += 1
                logger.error(
                    f"[Top3Service] LLM 선정 중 예외 발생 "
                    f"({self._llm_failure_count}/3): {e}"
                )
            
            # 3회 연속 실패 시 LLM 비활성화
            if self._llm_failure_count >= 3:
                self._llm_disabled = True
                logger.error(
                    "[Top3Service] LLM 3회 연속 실패, "
                    "점수 기반 모드로 전환합니다"
                )
        
        # 폴백: 점수 기반 선정
        logger.info("[Top3Service] 점수 기반 선정 사용")
        return self._pick_with_score(items)
    
    def _pick_with_score(self, items: List[Dict]) -> Set[str]:
        """점수 기반 Top3 선정"""
        # ScoreCalculator 규칙 업데이트
        self.score_calculator.rules = self._rules
        self.score_calculator.entity_rules = self._entity_rules
        
        return self.score_calculator.select_top3(items)
    
    def apply_natural_language_rules(
        self,
        text: str,
        reset: bool = False
    ) -> Tuple[str, str]:
        """자연어 규칙 적용 및 즉시 Top3 재선정
        
        Args:
            text: 자연어 규칙
            reset: 초기화 여부
            
        Returns:
            (결과 메시지, 규칙 설명)
        """
        if reset:
            # 초기화
            self._last_instruction = ""
            self._rules = deepcopy(TOP3_RULE_DEFAULT)
            self._entity_rules = deepcopy(ENTITY_RULES_DEFAULT)
            self._llm_failure_count = 0
            self._llm_disabled = False
            self.cache_manager.invalidate()
            self._save_rules()
            
            logger.info("[Top3Service] 규칙 초기화 완료")
            return "규칙이 초기화되었습니다", self.describe_rules()
        
        # 규칙 저장
        self._last_instruction = text.strip()
        self._save_rules()
        
        logger.info(f"[Top3Service] 자연어 규칙 저장: {self._last_instruction[:100]}")
        
        # 캐시에서 TODO 조회
        if self._cache_service:
            todos = self._cache_service.get_cached_todos()
            
            if todos:
                logger.info(f"[Top3Service] 캐시에서 TODO {len(todos)}개 조회")
                
                # LLM으로 즉시 Top3 선정
                try:
                    top3_ids = self.llm_selector.select_top3(
                        todos,
                        self._last_instruction,
                        self._entity_rules
                    )
                    
                    if top3_ids:
                        return (
                            f"규칙 적용 완료: {len(top3_ids)}개 선정",
                            self.describe_rules()
                        )
                    else:
                        return (
                            "규칙이 저장되었으나 선정된 TODO가 없습니다",
                            self.describe_rules()
                        )
                except Exception as e:
                    logger.error(f"[Top3Service] LLM 선정 실패: {e}")
                    return (
                        f"규칙이 저장되었으나 LLM 선정 실패: {e}",
                        self.describe_rules()
                    )
            else:
                return (
                    "규칙이 저장되었습니다. 백그라운드 분석을 실행하세요.",
                    self.describe_rules()
                )
        else:
            return (
                "규칙이 저장되었습니다",
                self.describe_rules()
            )
    
    def describe_rules(self) -> str:
        """현재 규칙 설명"""
        lines = []
        
        if self._last_instruction:
            lines.append(f"**자연어 규칙**: {self._last_instruction}")
        
        if self._entity_rules.get("requester"):
            requesters = ", ".join(self._entity_rules["requester"].keys())
            lines.append(f"**요청자 규칙**: {requesters}")
        
        if self._entity_rules.get("type"):
            types = ", ".join(self._entity_rules["type"].keys())
            lines.append(f"**유형 규칙**: {types}")
        
        if self._entity_rules.get("keyword"):
            keywords = ", ".join(self._entity_rules["keyword"].keys())
            lines.append(f"**키워드 규칙**: {keywords}")
        
        if not lines:
            lines.append("규칙이 설정되지 않았습니다 (기본 점수 기반)")
        
        # LLM 상태
        if self._llm_disabled:
            lines.append("⚠️ LLM 비활성화 (점수 기반 모드)")
        elif self.llm_client.is_available():
            providers = self.llm_client.get_available_providers()
            lines.append(f"✅ LLM 사용 가능 ({', '.join(providers)})")
        else:
            lines.append("❌ LLM 사용 불가 (API 키 확인 필요)")
        
        return "\n".join(lines)
    
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
        for key, value in new_rules.items():
            if key in TOP3_RULE_DEFAULT and isinstance(value, (int, float)):
                self._rules[key] = float(value)
        
        self._save_rules()
    
    def update_entity_rules(
        self,
        entity_rules: Dict[str, Dict[str, float]],
        reset: bool = False
    ) -> None:
        """엔티티 규칙 업데이트"""
        if reset:
            self._entity_rules = deepcopy(ENTITY_RULES_DEFAULT)
        
        for entity_type, rules in entity_rules.items():
            if entity_type not in self._entity_rules:
                self._entity_rules[entity_type] = {}
            
            self._entity_rules[entity_type].update(rules)
        
        self._save_rules()
    
    def reset_llm_failures(self) -> None:
        """LLM 실패 카운터 리셋 (수동 재활성화)"""
        self._llm_failure_count = 0
        self._llm_disabled = False
        logger.info("[Top3Service] LLM 실패 카운터 리셋")
    
    def get_cache_stats(self) -> Dict:
        """캐시 통계 반환"""
        return self.cache_manager.get_stats()
    
    def _save_rules(self) -> None:
        """규칙을 파일에 저장"""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            data = {
                "weights": self._rules,
                "entities": self._entity_rules,
                "instruction": self._last_instruction
            }
            
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"[Top3Service] 규칙 저장: {self.config_path}")
        except Exception as e:
            logger.error(f"[Top3Service] 규칙 저장 실패: {e}")
    
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
            
            if isinstance(weights, dict):
                self._rules.update(weights)
            
            if isinstance(entities, dict):
                for entity_type, rules in entities.items():
                    if entity_type not in self._entity_rules:
                        self._entity_rules[entity_type] = {}
                    self._entity_rules[entity_type].update(rules)
            
            if isinstance(instruction, str):
                self._last_instruction = instruction
            
            logger.info(f"[Top3Service] 규칙 로드: {self.config_path}")
        except Exception as e:
            logger.warning(f"[Top3Service] 규칙 로드 실패: {e}")
