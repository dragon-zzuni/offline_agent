#!/usr/bin/env python3
"""
프로젝트 분류기

메시지 내용과 발신자 정보를 기반으로 해당 메시지가 어떤 프로젝트와 
관련이 있는지 분류하는 시스템입니다.
"""

import logging
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from utils.vdos_db_connector import VDOSDBConnector, get_vdos_connector, ProjectInfo

logger = logging.getLogger(__name__)

@dataclass
class ProjectClassification:
    """프로젝트 분류 결과"""
    project_id: Optional[int]
    project_name: Optional[str]
    confidence: float  # 0.0 ~ 1.0
    keyword_score: float  # 키워드 매칭 점수
    sender_score: float  # 발신자 매칭 점수
    matched_keywords: List[str]  # 매칭된 키워드들
    matched_senders: List[str]  # 매칭된 발신자들
    is_classified: bool  # 분류 성공 여부 (임계값 이상)
    
    @property
    def tag(self) -> str:
        """태그 문자열 반환"""
        if self.is_classified and self.project_name:
            return self.project_name
        return "미분류"

class ProjectClassifier:
    """프로젝트 분류기 클래스"""
    
    def __init__(self, 
                 db_connector: Optional[VDOSDBConnector] = None,
                 confidence_threshold: float = 0.4,
                 keyword_weight: float = 0.6,
                 sender_weight: float = 0.4):
        """
        프로젝트 분류기 초기화
        
        Args:
            db_connector: VDOS DB 커넥터 (None이면 기본 인스턴스 사용)
            confidence_threshold: 분류 신뢰도 임계값 (기본 0.4)
            keyword_weight: 키워드 매칭 가중치 (기본 0.6)
            sender_weight: 발신자 매칭 가중치 (기본 0.4)
        """
        self.db_connector = db_connector or get_vdos_connector()
        self.confidence_threshold = confidence_threshold
        self.keyword_weight = keyword_weight
        self.sender_weight = sender_weight
        
        # 캐시된 매핑 데이터
        self._projects: Optional[Dict[int, ProjectInfo]] = None
        self._keyword_mapping: Optional[Dict[str, List[int]]] = None
        self._participant_mapping: Optional[Dict[str, List[int]]] = None
        
        logger.info(f"ProjectClassifier 초기화 (임계값: {confidence_threshold}, 키워드 가중치: {keyword_weight})")
    
    def _load_mappings(self):
        """매핑 데이터 로드 (캐시 사용)"""
        if self._projects is None:
            self._projects = self.db_connector.get_projects()
            self._keyword_mapping = self.db_connector.get_project_keywords_mapping()
            self._participant_mapping = self.db_connector.get_participant_project_mapping()
            
            logger.info(f"프로젝트 매핑 로드: {len(self._projects)}개 프로젝트, "
                       f"{len(self._keyword_mapping)}개 키워드, "
                       f"{len(self._participant_mapping)}개 참여자")
    
    def classify_message(self, 
                        message_content: str, 
                        sender: str, 
                        subject: Optional[str] = None) -> ProjectClassification:
        """
        메시지를 프로젝트별로 분류
        
        Args:
            message_content: 메시지 내용
            sender: 발신자 (이름, 이메일, 핸들 등)
            subject: 제목 (이메일의 경우)
            
        Returns:
            ProjectClassification 객체
        """
        self._load_mappings()
        
        # 전체 텍스트 (내용 + 제목)
        full_text = message_content
        if subject:
            full_text = f"{subject} {message_content}"
        
        # 1. 키워드 기반 분류
        keyword_scores = self._classify_by_keywords(full_text)
        
        # 2. 발신자 기반 분류
        sender_scores = self._classify_by_sender(sender)
        
        # 3. 점수 통합 및 최종 분류
        return self._combine_scores(keyword_scores, sender_scores, full_text, sender)
    
    def _classify_by_keywords(self, text: str) -> Dict[int, Tuple[float, List[str]]]:
        """
        키워드 기반 분류
        
        Args:
            text: 분석할 텍스트
            
        Returns:
            프로젝트 ID별 (점수, 매칭된 키워드 목록) 딕셔너리
        """
        text_lower = text.lower()
        project_scores = {}
        
        for keyword, project_ids in self._keyword_mapping.items():
            # 키워드 매칭 확인
            match_score = self._calculate_keyword_match_score(keyword, text_lower)
            
            if match_score > 0:
                for project_id in project_ids:
                    if project_id not in project_scores:
                        project_scores[project_id] = [0.0, []]
                    
                    # 점수 누적 (중복 키워드는 가중치 감소)
                    current_score, matched_keywords = project_scores[project_id]
                    new_score = current_score + match_score * (0.8 ** len(matched_keywords))
                    
                    project_scores[project_id] = [new_score, matched_keywords + [keyword]]
        
        # 점수 정규화 (0.0 ~ 1.0)
        if project_scores:
            max_score = max(score for score, _ in project_scores.values())
            if max_score > 0:
                for project_id in project_scores:
                    score, keywords = project_scores[project_id]
                    project_scores[project_id] = (score / max_score, keywords)
        
        return project_scores
    
    def _calculate_keyword_match_score(self, keyword: str, text: str) -> float:
        """
        키워드 매칭 점수 계산
        
        Args:
            keyword: 검색할 키워드
            text: 대상 텍스트 (소문자)
            
        Returns:
            매칭 점수 (0.0 ~ 1.0)
        """
        if not keyword or not text:
            return 0.0
        
        keyword_lower = keyword.lower()
        
        # 1. 완전 일치 (가장 높은 점수)
        if keyword_lower in text:
            # 단어 경계 확인
            if re.search(rf'\b{re.escape(keyword_lower)}\b', text):
                return 1.0  # 완전한 단어 일치
            else:
                return 0.8  # 부분 문자열 일치
        
        # 2. 부분 매칭 (키워드가 긴 경우)
        if len(keyword_lower) >= 4:
            # 키워드의 일부가 텍스트에 포함되는지 확인
            words = keyword_lower.split()
            if len(words) > 1:
                matched_words = sum(1 for word in words if word in text)
                if matched_words > 0:
                    return 0.6 * (matched_words / len(words))
        
        # 3. 유사도 기반 매칭 (간단한 편집 거리)
        if len(keyword_lower) >= 3:
            similarity = self._calculate_similarity(keyword_lower, text)
            if similarity > 0.7:
                return 0.4 * similarity
        
        return 0.0
    
    def _calculate_similarity(self, keyword: str, text: str) -> float:
        """간단한 문자열 유사도 계산"""
        # 키워드가 텍스트의 어떤 부분과 가장 유사한지 확인
        keyword_len = len(keyword)
        max_similarity = 0.0
        
        # 텍스트를 키워드 길이만큼 슬라이딩 윈도우로 검사
        for i in range(len(text) - keyword_len + 1):
            substring = text[i:i + keyword_len]
            
            # 공통 문자 수 계산
            common_chars = sum(1 for a, b in zip(keyword, substring) if a == b)
            similarity = common_chars / keyword_len
            
            max_similarity = max(max_similarity, similarity)
        
        return max_similarity
    
    def _classify_by_sender(self, sender: str) -> Dict[int, Tuple[float, List[str]]]:
        """
        발신자 기반 분류
        
        Args:
            sender: 발신자 정보
            
        Returns:
            프로젝트 ID별 (점수, 매칭된 발신자 목록) 딕셔너리
        """
        project_scores = {}
        sender_lower = sender.lower()
        
        # 발신자 정보에서 가능한 키들 추출
        sender_keys = self._extract_sender_keys(sender)
        
        for sender_key in sender_keys:
            if sender_key in self._participant_mapping:
                project_ids = self._participant_mapping[sender_key]
                
                for project_id in project_ids:
                    if project_id not in project_scores:
                        project_scores[project_id] = [0.0, []]
                    
                    # 매칭 정확도에 따른 점수 부여
                    match_score = self._calculate_sender_match_score(sender_key, sender_lower)
                    
                    current_score, matched_senders = project_scores[project_id]
                    new_score = current_score + match_score
                    
                    project_scores[project_id] = [new_score, matched_senders + [sender_key]]
        
        # 점수 정규화
        if project_scores:
            max_score = max(score for score, _ in project_scores.values())
            if max_score > 0:
                for project_id in project_scores:
                    score, senders = project_scores[project_id]
                    project_scores[project_id] = (min(score / max_score, 1.0), senders)
        
        return project_scores
    
    def _extract_sender_keys(self, sender: str) -> List[str]:
        """발신자 정보에서 가능한 키들 추출"""
        keys = []
        sender_lower = sender.lower()
        
        # 1. 원본 발신자
        keys.append(sender_lower)
        
        # 2. 이메일 주소인 경우 @ 앞부분
        if '@' in sender:
            email_prefix = sender.split('@')[0].lower()
            keys.append(email_prefix)
        
        # 3. 공백으로 분리된 이름들
        words = sender.split()
        for word in words:
            if len(word) >= 2:
                keys.append(word.lower())
        
        # 4. 특수문자 제거
        clean_sender = re.sub(r'[^\w가-힣]', '', sender_lower)
        if clean_sender and clean_sender != sender_lower:
            keys.append(clean_sender)
        
        # 5. 한국 이름 패턴 (성 제외)
        if len(sender) >= 3 and not '@' in sender:
            # 한글 이름으로 보이는 경우
            if re.match(r'^[가-힣]+$', sender):
                keys.append(sender[1:])  # 성 제외한 이름
        
        return list(set(keys))  # 중복 제거
    
    def _calculate_sender_match_score(self, sender_key: str, sender_original: str) -> float:
        """발신자 매칭 점수 계산"""
        if sender_key == sender_original:
            return 1.0  # 완전 일치
        elif sender_key in sender_original:
            return 0.8  # 부분 일치
        elif any(part in sender_original for part in sender_key.split()):
            return 0.6  # 단어 일치
        else:
            return 0.4  # 기본 점수
    
    def _combine_scores(self, 
                       keyword_scores: Dict[int, Tuple[float, List[str]]], 
                       sender_scores: Dict[int, Tuple[float, List[str]]],
                       original_text: str,
                       original_sender: str) -> ProjectClassification:
        """
        키워드와 발신자 점수를 통합하여 최종 분류 결과 생성
        
        Args:
            keyword_scores: 키워드 기반 점수
            sender_scores: 발신자 기반 점수
            original_text: 원본 텍스트
            original_sender: 원본 발신자
            
        Returns:
            ProjectClassification 객체
        """
        # 모든 프로젝트 ID 수집
        all_project_ids = set(keyword_scores.keys()) | set(sender_scores.keys())
        
        if not all_project_ids:
            # 매칭되는 프로젝트가 없음
            return ProjectClassification(
                project_id=None,
                project_name=None,
                confidence=0.0,
                keyword_score=0.0,
                sender_score=0.0,
                matched_keywords=[],
                matched_senders=[],
                is_classified=False
            )
        
        # 각 프로젝트별 최종 점수 계산
        final_scores = {}
        
        for project_id in all_project_ids:
            keyword_score, matched_keywords = keyword_scores.get(project_id, (0.0, []))
            sender_score, matched_senders = sender_scores.get(project_id, (0.0, []))
            
            # 가중 평균 계산
            final_score = (keyword_score * self.keyword_weight + 
                          sender_score * self.sender_weight)
            
            final_scores[project_id] = {
                'score': final_score,
                'keyword_score': keyword_score,
                'sender_score': sender_score,
                'matched_keywords': matched_keywords,
                'matched_senders': matched_senders
            }
        
        # 최고 점수 프로젝트 선택
        best_project_id = max(final_scores.keys(), key=lambda pid: final_scores[pid]['score'])
        best_result = final_scores[best_project_id]
        
        # 프로젝트 정보 조회
        project_name = None
        if best_project_id in self._projects:
            project_name = self._projects[best_project_id].name
        
        # 분류 성공 여부 판단
        is_classified = best_result['score'] >= self.confidence_threshold
        
        return ProjectClassification(
            project_id=best_project_id if is_classified else None,
            project_name=project_name if is_classified else None,
            confidence=best_result['score'],
            keyword_score=best_result['keyword_score'],
            sender_score=best_result['sender_score'],
            matched_keywords=best_result['matched_keywords'],
            matched_senders=best_result['matched_senders'],
            is_classified=is_classified
        )
    
    def classify_batch(self, messages: List[Dict]) -> List[ProjectClassification]:
        """
        여러 메시지를 일괄 분류
        
        Args:
            messages: 메시지 목록 (각 메시지는 content, sender, subject 키를 가져야 함)
            
        Returns:
            ProjectClassification 객체 목록
        """
        results = []
        
        for message in messages:
            content = message.get('content', message.get('body', ''))
            sender = message.get('sender', '')
            subject = message.get('subject', '')
            
            result = self.classify_message(content, sender, subject)
            results.append(result)
        
        return results
    
    def get_classification_stats(self, classifications: List[ProjectClassification]) -> Dict:
        """분류 결과 통계 생성"""
        total = len(classifications)
        classified = sum(1 for c in classifications if c.is_classified)
        unclassified = total - classified
        
        # 프로젝트별 분류 수
        project_counts = {}
        for c in classifications:
            if c.is_classified and c.project_name:
                project_counts[c.project_name] = project_counts.get(c.project_name, 0) + 1
        
        # 평균 신뢰도
        avg_confidence = sum(c.confidence for c in classifications) / total if total > 0 else 0.0
        
        return {
            'total_messages': total,
            'classified': classified,
            'unclassified': unclassified,
            'classification_rate': classified / total if total > 0 else 0.0,
            'average_confidence': avg_confidence,
            'project_distribution': project_counts
        }
    
    def clear_cache(self):
        """캐시 초기화"""
        self._projects = None
        self._keyword_mapping = None
        self._participant_mapping = None
        logger.info("ProjectClassifier 캐시 초기화됨")

# 전역 인스턴스 (싱글톤 패턴)
_project_classifier: Optional[ProjectClassifier] = None

def get_project_classifier(**kwargs) -> ProjectClassifier:
    """프로젝트 분류기 싱글톤 인스턴스 반환"""
    global _project_classifier
    
    if _project_classifier is None:
        _project_classifier = ProjectClassifier(**kwargs)
    
    return _project_classifier