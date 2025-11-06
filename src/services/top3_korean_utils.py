# -*- coding: utf-8 -*-
"""
Top3 서비스 한국어 이름 처리 유틸리티
"""
from typing import List

# 한국어 이름 처리 상수
_KOREAN_NAME_SUFFIXES = ("선생님", "팀장", "부장", "님", "씨")
_KOREAN_PARTICLES = (
    "께서", "에서", "에게", "으로", "로", "와", "과", "은", "는", "이", "가",
    "을", "를", "도", "만", "부터", "까지", "에게서", "밖에", "로서", "로써",
    "이라서", "라서", "이라도", "라도", "이며", "이며도"
)


def normalize_korean_name(token: str) -> str:
    """
    한국어 이름 정규화 (존댓말, 조사 제거)
    
    Args:
        token: 정규화할 이름
        
    Returns:
        str: 정규화된 이름
    """
    base = token.strip()
    
    # 존댓말 제거
    for suffix in _KOREAN_NAME_SUFFIXES:
        if base.endswith(suffix) and len(base) > len(suffix):
            base = base[:-len(suffix)]
            break
    
    # 조사 제거 (반복)
    changed = True
    while changed and len(base) > 2:
        changed = False
        for suffix in _KOREAN_PARTICLES:
            if base.endswith(suffix) and len(base) > len(suffix):
                base = base[:-len(suffix)]
                changed = True
                break
    
    return base.strip()


def generate_korean_name_variations(name: str) -> List[str]:
    """
    한국어 이름의 변형들을 생성
    
    Args:
        name: 원본 이름
        
    Returns:
        List[str]: 이름 변형 리스트
    """
    variations = []
    base = normalize_korean_name(name)
    
    if base != name:
        variations.append(base)
    
    # 존댓말 변형
    for suffix in _KOREAN_NAME_SUFFIXES:
        variation = base + suffix
        if variation != name:
            variations.append(variation)
    
    return variations
