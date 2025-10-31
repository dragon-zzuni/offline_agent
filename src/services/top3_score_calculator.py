# -*- coding: utf-8 -*-
"""
Top3 점수 계산 모듈

TODO 항목의 우선순위 점수를 계산하고 상위 3개를 선정합니다.
"""
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Set, Optional

logger = logging.getLogger(__name__)


class Top3ScoreCalculator:
    """점수 기반 Top3 선정기
    
    우선순위, 데드라인, 근거, 엔티티 규칙을 종합하여 점수를 계산합니다.
    """
    
    def __init__(
        self, 
        rules: Dict[str, float], 
        entity_rules: Dict[str, Dict[str, float]],
        email_to_name: Optional[Dict[str, str]] = None
    ):
        """
        Args:
            rules: 가중치 규칙 딕셔너리
            entity_rules: 엔티티 규칙 딕셔너리
            email_to_name: 이메일 → 이름 매핑 (호환성용, 사용하지 않음)
        """
        self.rules = rules
        self.entity_rules = entity_rules
        # email_to_name은 호환성을 위해 받지만 사용하지 않음
    
    def calculate_score(self, todo: Dict) -> float:
        """TODO 항목의 점수 계산
        
        Args:
            todo: TODO 항목 딕셔너리
            
        Returns:
            계산된 점수
        """
        # 우선순위 가중치
        priority = (todo.get("priority") or "low").lower()
        w_priority = self.rules.get(f"priority_{priority}", self.rules.get("priority_low", 1.0))
        
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
            emphasis = self.rules.get("deadline_emphasis", 24.0)
            base = self.rules.get("deadline_base", 1.0)
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
        
        per_item = self.rules.get("evidence_per_item", 0.1)
        max_bonus = self.rules.get("evidence_max_bonus", 0.5)
        w_evidence = 1.0 + min(max_bonus, per_item * len(evidence))
        
        # 엔티티 규칙 적용 (자연어 규칙)
        rule_multiplier = 1.0
        priority_bonus = 0.0
        
        # 요청자 보너스 (더 강력하게 적용)
        requester = (todo.get("requester") or "").lower()
        if requester:
            for match, bonus in self.entity_rules.get("requester", {}).items():
                if match and match in requester:
                    priority_bonus += bonus
                    rule_multiplier += bonus * 0.25
            
            # 임호규 특별 매칭 (이메일 주소 포함)
            hongyu_patterns = ["임호규", "hongyu", "imhokyu", "lim", "ho", "gyu"]
            if any(pattern in requester for pattern in hongyu_patterns):
                for pattern in hongyu_patterns:
                    if pattern in self.entity_rules.get("requester", {}):
                        bonus = self.entity_rules["requester"][pattern]
                        priority_bonus += bonus
                        rule_multiplier += bonus * 0.25
                        break
        
        # 키워드 보너스 (제목, 설명, 타입에서 검색)
        text_fields = " ".join([
            todo.get("title", ""),
            todo.get("description", ""),
            todo.get("type", ""),
        ]).lower()
        
        for match, bonus in self.entity_rules.get("keyword", {}).items():
            if match and match in text_fields:
                priority_bonus += bonus * 0.5
                rule_multiplier += bonus * 0.25
        
        # 타입 보너스
        todo_type = (todo.get("type") or "").lower()
        for match, bonus in self.entity_rules.get("type", {}).items():
            if match and match in todo_type:
                priority_bonus += bonus * 0.5
                rule_multiplier += bonus * 0.25
        
        # rule_multiplier 범위 제한
        rule_multiplier = max(0.5, min(rule_multiplier, 6.0))
        
        # priority_term 계산 (엔티티 보너스 적용)
        if priority_bonus > 0:
            priority_floor = max(self.rules.get("priority_high", 3.0) + priority_bonus, 3.5)
        else:
            priority_floor = 0.0
        
        priority_term = max(0.1, w_priority + priority_bonus, priority_floor)
        
        # 수신 타입 페널티 (CC/BCC)
        recipient_type = (todo.get("recipient_type") or "to").lower()
        cc_penalty = 1.0
        if recipient_type == "cc":
            cc_penalty = self.rules.get("recipient_type_cc_penalty", 0.7)
        elif recipient_type == "bcc":
            cc_penalty = self.rules.get("recipient_type_cc_penalty", 0.7) * 0.9
        
        # 최종 점수 (엔티티 규칙이 강력하게 적용됨)
        score = (priority_term * rule_multiplier) * w_deadline * w_evidence * cc_penalty
        return score
    
    def update_rules(self, rules: Dict[str, float]) -> None:
        """규칙 업데이트 (호환성 메서드)
        
        Args:
            rules: 새로운 규칙 딕셔너리
        """
        self.rules = rules
        logger.debug("[Top3ScoreCalculator] 규칙 업데이트 완료")
    
    def update_entity_rules(self, entity_rules: Dict[str, Dict[str, float]]) -> None:
        """엔티티 규칙 업데이트 (호환성 메서드)
        
        Args:
            entity_rules: 새로운 엔티티 규칙 딕셔너리
        """
        self.entity_rules = entity_rules
        logger.debug("[Top3ScoreCalculator] 엔티티 규칙 업데이트 완료")
    
    def select_top3_with_rules(
        self, 
        candidates: List[Dict] = None,
        items: List[Dict] = None, 
        entity_rules: Dict[str, Dict[str, float]] = None
    ) -> Set[str]:
        """규칙 기반 Top3 선정 (호환성 메서드)
        
        Args:
            candidates: TODO 항목 리스트 (호환성용)
            items: TODO 항목 리스트 (대체용)
            entity_rules: 엔티티 규칙
            
        Returns:
            선정된 TODO ID 집합
        """
        # candidates 또는 items 중 하나 사용
        todo_items = candidates or items or []
        
        if not todo_items:
            logger.warning("[Top3ScoreCalculator] 규칙 기반 선정: TODO 항목이 없습니다")
            return set()
        
        # 엔티티 규칙 임시 업데이트
        original_rules = self.entity_rules
        if entity_rules:
            self.entity_rules = entity_rules
        
        try:
            result = self.select_top3(todo_items)
            logger.info(f"[Top3ScoreCalculator] 규칙 기반 선정 완료: {len(result)}개")
            return result
        finally:
            # 원래 규칙 복원
            self.entity_rules = original_rules
    
    def select_top3(self, items: List[Dict]) -> Set[str]:
        """점수 기반 Top3 선정
        
        Args:
            items: TODO 항목 리스트
            
        Returns:
            선정된 TODO ID 집합
        """
        # 1. status가 done이 아닌 것만 후보
        candidates = [x for x in items if (x.get("status") or "pending") not in ("done",)]
        
        if not candidates:
            logger.info("[Top3ScoreCalculator] 후보 TODO가 없습니다")
            return set()
        
        # 2. 모든 후보의 점수 계산
        for item in candidates:
            item["_top3_score"] = self.calculate_score(item)
        
        def _created_iso(x):
            return x.get("created_at") or datetime.now().isoformat()
        
        # 3. 점수순으로 정렬
        candidates.sort(key=lambda x: (x["_top3_score"], _created_iso(x)), reverse=True)
        
        # 4. 상위 3개 선정
        top3_ids = set()
        for item in candidates[:3]:
            if item.get("id"):
                top3_ids.add(item["id"])
        
        logger.info(
            f"[Top3ScoreCalculator] 점수 기반 선정 완료: "
            f"{len(candidates)}개 중 {len(top3_ids)}개 선정"
        )
        
        # 디버그: 상위 5개 점수 로깅
        if logger.isEnabledFor(logging.DEBUG):
            for i, item in enumerate(candidates[:5], 1):
                logger.debug(
                    f"  {i}. {item.get('title', '')[:30]} "
                    f"(점수: {item['_top3_score']:.2f}, "
                    f"우선순위: {item.get('priority', 'low')})"
                )
        
        return top3_ids
