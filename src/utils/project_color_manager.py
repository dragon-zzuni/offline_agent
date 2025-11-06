#!/usr/bin/env python3
"""
프로젝트 색상 관리자

프로젝트별로 일관된 색상을 제공하는 전역 관리자입니다.
"""

import hashlib
from typing import Dict, Tuple

class ProjectColorManager:
    """프로젝트 색상 관리자"""
    
    # 12색 팔레트 (프로젝트별 고유 색상)
    COLOR_PALETTE = [
        ("#8B5CF6", "#FFFFFF"),  # Purple
        ("#3B82F6", "#FFFFFF"),  # Blue  
        ("#10B981", "#FFFFFF"),  # Green
        ("#F59E0B", "#FFFFFF"),  # Amber
        ("#EF4444", "#FFFFFF"),  # Red
        ("#8B5A2B", "#FFFFFF"),  # Brown
        ("#EC4899", "#FFFFFF"),  # Pink
        ("#06B6D4", "#FFFFFF"),  # Cyan
        ("#84CC16", "#FFFFFF"),  # Lime
        ("#F97316", "#FFFFFF"),  # Orange
        ("#6366F1", "#FFFFFF"),  # Indigo
        ("#14B8A6", "#FFFFFF"),  # Teal
    ]
    
    def __init__(self):
        self._color_cache: Dict[str, Tuple[str, str]] = {}
    
    def get_project_colors(self, project_name: str) -> Tuple[str, str]:
        """
        프로젝트 이름에 대한 일관된 색상 반환
        
        Args:
            project_name: 프로젝트 이름
            
        Returns:
            (배경색, 텍스트색) 튜플
        """
        # 캐시에서 확인
        if project_name in self._color_cache:
            return self._color_cache[project_name]
        
        # 프로젝트명을 정규화 (대소문자 무시, 공백 제거)
        normalized_name = project_name.lower().replace(" ", "").replace("-", "").replace("_", "")
        
        # 해시 기반 색상 생성
        hash_value = hashlib.md5(normalized_name.encode('utf-8')).hexdigest()
        color_index = int(hash_value[:2], 16) % len(self.COLOR_PALETTE)
        
        colors = self.COLOR_PALETTE[color_index]
        
        # 캐시에 저장
        self._color_cache[project_name] = colors
        
        return colors
    
    def get_project_short_name(self, project_name: str) -> str:
        """
        프로젝트 축약명 생성
        
        Args:
            project_name: 프로젝트 전체 이름
            
        Returns:
            축약명 (2-4글자)
        """
        if not project_name:
            return "?"
        
        # 특별한 프로젝트명 처리
        special_names = {
            "Care Connect 2.0 리디자인": "CARE",
            "HealthCore API 리팩토링": "HEAL", 
            "WellLink 브랜드 런칭 캠페인": "WC",
            "WellLink Insight Dashboard": "WD",
            "CareBridge Integration (CPO 주관)": "CARE",
            "미분류": "기타"
        }
        
        if project_name in special_names:
            return special_names[project_name]
        
        # 일반적인 축약명 생성
        words = project_name.split()
        if len(words) >= 2:
            # 첫 두 단어의 첫 글자
            return ''.join(word[0].upper() for word in words[:2] if word)
        elif len(words) == 1:
            # 단일 단어의 첫 3글자
            return words[0][:3].upper()
        else:
            return project_name[:3].upper()
    
    def clear_cache(self):
        """색상 캐시 초기화"""
        self._color_cache.clear()

# 전역 인스턴스
_color_manager: ProjectColorManager = None

def get_project_color_manager() -> ProjectColorManager:
    """프로젝트 색상 관리자 싱글톤 인스턴스 반환"""
    global _color_manager
    
    if _color_manager is None:
        _color_manager = ProjectColorManager()
    
    return _color_manager

def get_project_colors(project_name: str) -> Tuple[str, str]:
    """프로젝트 색상 가져오기 (편의 함수)"""
    return get_project_color_manager().get_project_colors(project_name)

def get_project_short_name(project_name: str) -> str:
    """프로젝트 축약명 가져오기 (편의 함수)"""
    return get_project_color_manager().get_project_short_name(project_name)