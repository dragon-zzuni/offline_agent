# -*- coding: utf-8 -*-
"""
Top3 TODO 선정 및 규칙 관리 서비스

TODO 항목의 우선순위를 계산하고 Top3를 자동으로 선정합니다.
자연어 규칙 해석 및 LLM 기반 규칙 파싱을 지원합니다.
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
    """Top3 TODO 선정 및 규칙 관리 서비스"""
    
    def __init__(self, config_path: Optional[str] = None, people_data: Optional[List[Dict]] = None, vdos_connector=None):
        """
        Args:
            config_path: 규칙 저장 경로 (선택사항)
            people_data: 사람 정보 리스트 (이메일→이름 매핑용)
            vdos_connector: VDOSConnector 인스턴스 (실시간 people 데이터용)
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
        self._vdos_connector = vdos_connector
        
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
        
        # 저장된 규칙 로드
        self._load_rules()
    
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
    
    def calculate_score(self, todo: Dict) -> float:
        """TODO 항목의 점수 계산"""
        # 우선순위 가중치
        priority = (todo.get("priority") or "low").lower()
        w_priority = self._rules.get(f"priority_{priority}", self._rules["priority_low"])
        
        # 데드라인 임박 가중치
        now = datetime.now(timezone.utc)
        deadline = todo.get("deadline_ts") or todo.get("deadline")
        
        if deadline:
            try:
                dl = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
            except Exception:
                try:
                    dl = datetime.fromisoformat(deadline)
                except Exception:
                    dl = None
        else:
            dl = None
        
        if dl:
            if dl.tzinfo is None:
                dl = dl.replace(tzinfo=timezone.utc)
            hours_left = max(0.0, (dl - now).total_seconds() / 3600.0)
            emphasis = self._rules.get("deadline_emphasis", 24.0)
            base = self._rules.get("deadline_base", 1.0)
            w_deadline = base + (emphasis / (emphasis + hours_left))
        else:
            w_deadline = 1.0
        
        # 근거 가중치
        evidence = todo.get("evidence")
        if not isinstance(evidence, list):
            try:
                evidence = json.loads(evidence or "[]")
            except Exception:
                evidence = []
        
        per_item = self._rules.get("evidence_per_item", 0.1)
        max_bonus = self._rules.get("evidence_max_bonus", 0.5)
        w_evidence = 1.0 + min(max_bonus, per_item * len(evidence))
        
        # 엔티티 규칙 적용 (자연어 규칙)
        rule_multiplier = 1.0
        priority_bonus = 0.0
        
        # 요청자 보너스 (더 강력하게 적용)
        requester = (todo.get("requester") or "").lower()
        if requester:
            for match, bonus in self._entity_rules.get("requester", {}).items():
                if match and match in requester:
                    priority_bonus += bonus
                    rule_multiplier += bonus * 0.25
            
            # 임호규 특별 매칭 (이메일 주소 포함)
            hongyu_patterns = ["임호규", "hongyu", "imhokyu", "lim", "ho", "gyu"]
            if any(pattern in requester for pattern in hongyu_patterns):
                for pattern in hongyu_patterns:
                    if pattern in self._entity_rules.get("requester", {}):
                        bonus = self._entity_rules["requester"][pattern]
                        priority_bonus += bonus
                        rule_multiplier += bonus * 0.25
                        break
        
        # 키워드 보너스 (제목, 설명, 타입에서 검색)
        text_fields = " ".join([
            todo.get("title", ""),
            todo.get("description", ""),
            todo.get("type", ""),
        ]).lower()
        
        for match, bonus in self._entity_rules.get("keyword", {}).items():
            if match and match in text_fields:
                priority_bonus += bonus * 0.5
                rule_multiplier += bonus * 0.25
        
        # 타입 보너스
        todo_type = (todo.get("type") or "").lower()
        for match, bonus in self._entity_rules.get("type", {}).items():
            if match and match in todo_type:
                priority_bonus += bonus * 0.5
                rule_multiplier += bonus * 0.25
        
        # rule_multiplier 범위 제한
        rule_multiplier = max(0.5, min(rule_multiplier, 6.0))
        
        # priority_term 계산 (엔티티 보너스 적용)
        if priority_bonus > 0:
            priority_floor = max(self._rules.get("priority_high", 3.0) + priority_bonus, 3.5)
        else:
            priority_floor = 0.0
        
        priority_term = max(0.1, w_priority + priority_bonus, priority_floor)
        
        # 수신 타입 페널티 (CC/BCC)
        recipient_type = (todo.get("recipient_type") or "to").lower()
        cc_penalty = 1.0
        if recipient_type == "cc":
            cc_penalty = self._rules.get("recipient_type_cc_penalty", 0.7)
        elif recipient_type == "bcc":
            cc_penalty = self._rules.get("recipient_type_cc_penalty", 0.7) * 0.9
        
        # 최종 점수 (엔티티 규칙이 강력하게 적용됨)
        score = (priority_term * rule_multiplier) * w_deadline * w_evidence * cc_penalty
        return score
    
    def _normalize_name(self, name: str) -> str:
        """이름 정규화 (공백, 대소문자, 특수문자 제거, 이메일 주소 처리)
        
        Args:
            name: 정규화할 이름
            
        Returns:
            정규화된 이름 (소문자, 공백/특수문자 제거)
        """
        if not name:
            return ""
        
        # 소문자 변환
        normalized = name.lower().strip()
        
        # 이메일 주소에서 이름 부분만 추출
        if "@" in normalized:
            normalized = normalized.split("@")[0]
        
        # 공백 제거
        normalized = normalized.replace(" ", "").replace("\t", "")
        
        # 특수문자 제거 (한글, 영문, 숫자만 유지)
        normalized = re.sub(r"[^a-z0-9가-힣]", "", normalized)
        
        return normalized
    
    def _match_requester(self, requester: str, rules: Dict[str, float]) -> bool:
        """요청자가 규칙에 매칭되는지 확인 (완전 일치 및 부분 일치, 이메일→이름 변환)
        
        Args:
            requester: TODO의 요청자 (이메일 또는 이름)
            rules: 요청자 규칙 딕셔너리 {이름: 보너스}
            
        Returns:
            매칭 여부
        """
        if not requester or not rules:
            return False
        
        # 이메일 주소인 경우 이름으로 변환
        requester_name = requester
        if "@" in requester:
            requester_name = self._email_to_name.get(requester.lower(), requester)
            logger.debug(f"[Top3Service] 이메일→이름 변환: {requester} → {requester_name}")
        
        # 정규화
        normalized_requester = self._normalize_name(requester_name)
        
        for rule_name in rules.keys():
            normalized_rule = self._normalize_name(rule_name)
            
            # 완전 일치
            if normalized_requester == normalized_rule:
                logger.debug(f"[Top3Service] ✓ 완전 일치: requester={requester_name}, rule={rule_name}")
                return True
            
            # 부분 일치 (한국어 이름은 엄격하게)
            # 규칙이 요청자에 포함되는 경우만 허용 (역방향 제외)
            # 예: 규칙="김철수", 요청자="김철수님" → OK
            # 예: 규칙="김철수님", 요청자="김철수" → NO (너무 느슨함)
            if normalized_rule and len(normalized_rule) >= 2:
                if normalized_rule in normalized_requester and len(normalized_requester) - len(normalized_rule) <= 2:
                    # 길이 차이가 2 이하일 때만 부분 일치 허용 (호칭 정도만)
                    logger.debug(f"[Top3Service] ✓ 부분 일치 (규칙→요청자): requester={requester_name}, rule={rule_name}")
                    return True
        
        logger.debug(f"[Top3Service] ✗ 매칭 실패: requester={requester_name} (원본={requester})")
        return False
    
    def _filter_by_rules(self, candidates: List[Dict]) -> List[Dict]:
        """규칙에 매칭되는 TODO 필터링
        
        Args:
            candidates: 후보 TODO 리스트
            
        Returns:
            규칙에 매칭되는 TODO 리스트
        """
        requester_rules = self._entity_rules.get("requester", {})
        
        if not requester_rules:
            logger.debug("[Top3Service] 요청자 규칙 없음, 필터링 스킵")
            return []
        
        logger.info(f"[Top3Service] 규칙 적용 시작: {len(requester_rules)}개 요청자 규칙, {len(candidates)}개 후보 TODO")
        logger.debug(f"[Top3Service] 규칙 목록: {list(requester_rules.keys())}")
        
        matched = []
        unmatched_requesters = set()
        
        for item in candidates:
            requester = item.get("requester", "")
            if not requester:
                continue
            
            # 규칙과 매칭 확인
            if self._match_requester(requester, requester_rules):
                matched.append(item)
                logger.debug(f"[Top3Service] 규칙 매칭 성공: TODO={item.get('title', '')[:30]}, 요청자={requester}")
            else:
                unmatched_requesters.add(requester)
        
        if unmatched_requesters:
            logger.debug(f"[Top3Service] 규칙 미매칭 요청자: {list(unmatched_requesters)[:5]}")
        
        logger.info(f"[Top3Service] 규칙 매칭 완료: {len(matched)}개 TODO 매칭, {len(unmatched_requesters)}개 요청자 미매칭")
        return matched
    
    def pick_top3(self, items: List[Dict]) -> Set[str]:
        """Top3 TODO 선정 (규칙 강제 적용)
        
        자연어 규칙이 있으면 무조건 규칙에 맞는 TODO만 Top3에 표시
        규칙이 없으면 일반 점수 기반 선정
        """
        # 1. status가 done이 아닌 것만 후보
        candidates = [x for x in items if (x.get("status") or "pending") not in ("done",)]
        
        # 2. 자연어 규칙 확인
        has_natural_rules = bool(self._entity_rules.get("requester") or 
                                 self._entity_rules.get("keyword") or 
                                 self._entity_rules.get("type"))
        
        if has_natural_rules:
            # 자연어 규칙이 있으면 무조건 규칙 매칭 TODO만 선정
            logger.info(f"[Top3Service] 🔒 강제 모드: 자연어 규칙에 맞는 TODO만 Top3 선정")
            
            # 규칙 매칭 TODO 필터링
            rule_matched = self._filter_by_rules(candidates)
            
            if not rule_matched:
                logger.warning(f"[Top3Service] ⚠️ 규칙에 맞는 TODO가 없음 (전체 {len(candidates)}개 중)")
                return set()
            
            # 규칙 매칭 TODO를 점수순으로 정렬
            for item in rule_matched:
                item["_top3_score"] = self.calculate_score(item)
            
            def _created_iso(x):
                return x.get("created_at") or datetime.now().isoformat()
            
            rule_matched.sort(key=lambda x: (x["_top3_score"], _created_iso(x)), reverse=True)
            
            # 규칙 매칭 TODO에서 최대 3개 선정 (3개 미만이어도 채우지 않음)
            top3_ids = set()
            for item in rule_matched[:3]:
                if item.get("id"):
                    top3_ids.add(item["id"])
            
            logger.info(f"[Top3Service] ✅ 강제 모드 완료: 규칙 매칭 {len(rule_matched)}개 중 {len(top3_ids)}개 선정")
            return top3_ids
        
        else:
            # 자연어 규칙이 없으면 일반 점수 기반 선정
            logger.info(f"[Top3Service] 📊 일반 모드: 점수 기반 Top3 선정")
            
            # 모든 후보의 점수 계산
            for item in candidates:
                item["_top3_score"] = self.calculate_score(item)
            
            def _created_iso(x):
                return x.get("created_at") or datetime.now().isoformat()
            
            candidates.sort(key=lambda x: (x["_top3_score"], _created_iso(x)), reverse=True)
            
            # 상위 3개 선정
            top3_ids = set()
            for item in candidates[:3]:
                if item.get("id"):
                    top3_ids.add(item["id"])
            
            logger.info(f"[Top3Service] ✅ 일반 모드 완료: {len(candidates)}개 중 {len(top3_ids)}개 선정")
            return top3_ids
    
    def describe_rules(self) -> str:
        """현재 규칙을 텍스트로 설명"""
        rules = self.get_rules()
        entity_rules = self.get_entity_rules()
        
        # 자연어 규칙 확인
        has_natural_rules = bool(entity_rules.get("requester") or 
                                 entity_rules.get("keyword") or 
                                 entity_rules.get("type"))
        
        parts = []
        
        if has_natural_rules:
            parts.append("🔒 강제 모드: 자연어 규칙에 맞는 TODO만 Top3 표시")
            
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
            logger.info("[Top3Service] rules reset by user input")
            return "규칙을 기본값으로 초기화했습니다.", self.describe_rules()
        
        # 휴리스틱 파싱 먼저 시도 (더 안정적)
        logger.info(f"[Top3Service] 자연어 규칙 파싱 시작: '{cleaned_text[:50]}...'")
        parsed, heuristic_note = self._heuristic_parse_rules(cleaned_text)
        
        if parsed:
            logger.info(f"[Top3Service] 휴리스틱 파싱 성공: {heuristic_note}")
            llm_message = heuristic_note
        else:
            # 휴리스틱 실패 시 LLM 파싱
            logger.warning(f"[Top3Service] 휴리스틱 파싱 실패, LLM 파싱으로 전환")
            parsed, llm_message = self._try_llm_parse_rules(cleaned_text)
            
            if parsed:
                logger.info(f"[Top3Service] LLM 파싱 성공: {llm_message}")
            else:
                logger.warning(f"[Top3Service] LLM 파싱도 실패: {llm_message}")
        
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
