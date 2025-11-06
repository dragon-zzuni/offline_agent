#!/usr/bin/env python3
"""프로젝트 태그 색상 및 축약명 자동 생성 시스템"""

import hashlib
import re
from typing import Dict, List, Tuple, Set
from dataclasses import dataclass
import colorsys
import logging

logger = logging.getLogger(__name__)

@dataclass
class ColorInfo:
    """색상 정보 클래스"""
    hex_color: str
    rgb: Tuple[int, int, int]
    hsl: Tuple[float, float, float]
    contrast_text: str  # 텍스트 색상 (흰색 또는 검은색)
    brightness: float   # 밝기 값 (0-255)

class ColorPalette:
    """색상 팔레트 관리 클래스"""
    
    # 기본 12색 팔레트 (Material Design 기반)
    PRIMARY_COLORS = [
        "#1976d2",  # Blue
        "#388e3c",  # Green  
        "#f57c00",  # Orange
        "#7b1fa2",  # Purple
        "#fbc02d",  # Yellow
        "#d32f2f",  # Red
        "#512da8",  # Deep Purple
        "#00796b",  # Teal
        "#f57f17",  # Lime
        "#c2185b",  # Pink
        "#303f9f",  # Indigo
        "#0097a7"   # Cyan
    ]
    
    # 확장 색상 팔레트 (24색)
    EXTENDED_COLORS = [
        "#1976d2", "#1565c0", "#0d47a1",  # Blue 계열
        "#388e3c", "#2e7d32", "#1b5e20",  # Green 계열
        "#f57c00", "#ef6c00", "#e65100",  # Orange 계열
        "#7b1fa2", "#6a1b9a", "#4a148c",  # Purple 계열
        "#fbc02d", "#f9a825", "#f57f17",  # Yellow 계열
        "#d32f2f", "#c62828", "#b71c1c",  # Red 계열
        "#512da8", "#4527a0", "#311b92",  # Deep Purple 계열
        "#00796b", "#00695c", "#004d40"   # Teal 계열
    ]
    
    def __init__(self, use_extended: bool = False):
        self.colors = self.EXTENDED_COLORS if use_extended else self.PRIMARY_COLORS
        self.color_info_cache: Dict[str, ColorInfo] = {}
        self._build_color_info_cache()
    
    def _build_color_info_cache(self):
        """색상 정보 캐시 구축"""
        for color in self.colors:
            self.color_info_cache[color] = self._create_color_info(color)
    
    def _create_color_info(self, hex_color: str) -> ColorInfo:
        """색상 정보 객체 생성"""
        # RGB 변환
        rgb = self._hex_to_rgb(hex_color)
        
        # HSL 변환
        hsl = self._rgb_to_hsl(rgb)
        
        # 밝기 계산
        brightness = self._calculate_brightness(rgb)
        
        # 대비 텍스트 색상 결정
        contrast_text = "#ffffff" if brightness < 128 else "#000000"
        
        return ColorInfo(
            hex_color=hex_color,
            rgb=rgb,
            hsl=hsl,
            contrast_text=contrast_text,
            brightness=brightness
        )
    
    def _hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        """HEX 색상을 RGB로 변환"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def _rgb_to_hsl(self, rgb: Tuple[int, int, int]) -> Tuple[float, float, float]:
        """RGB를 HSL로 변환"""
        r, g, b = [x / 255.0 for x in rgb]
        return colorsys.rgb_to_hls(r, g, b)
    
    def _calculate_brightness(self, rgb: Tuple[int, int, int]) -> float:
        """RGB 밝기 계산 (0-255)"""
        r, g, b = rgb
        return (r * 299 + g * 587 + b * 114) / 1000
    
    def get_color_info(self, hex_color: str) -> ColorInfo:
        """색상 정보 반환"""
        if hex_color in self.color_info_cache:
            return self.color_info_cache[hex_color]
        return self._create_color_info(hex_color)
    
    def get_colors_by_brightness(self, min_brightness: float = 0, max_brightness: float = 255) -> List[str]:
        """밝기 범위에 따른 색상 목록 반환"""
        return [
            color for color, info in self.color_info_cache.items()
            if min_brightness <= info.brightness <= max_brightness
        ]
    
    def get_contrasting_colors(self, count: int = 12) -> List[str]:
        """대비가 좋은 색상들 선택"""
        # HSL의 H(색조) 값을 기준으로 균등하게 분산된 색상 선택
        sorted_colors = sorted(
            self.color_info_cache.items(),
            key=lambda x: x[1].hsl[0]  # 색조 기준 정렬
        )
        
        if len(sorted_colors) <= count:
            return [color for color, _ in sorted_colors]
        
        # 균등 간격으로 색상 선택
        step = len(sorted_colors) // count
        return [sorted_colors[i * step][0] for i in range(count)]

class ProjectNameProcessor:
    """프로젝트명 처리 및 축약명 생성 클래스"""
    
    # 한국어 불용어
    KOREAN_STOPWORDS = {
        '프로젝트', '시스템', '개발', '구축', '운영', '관리', '서비스', 
        '플랫폼', '솔루션', '어플리케이션', '앱', '웹', '모바일', '데이터',
        '및', '과', '를', '을', '의', '에', '는', '은', '이', '가'
    }
    
    # 영어 불용어
    ENGLISH_STOPWORDS = {
        'project', 'system', 'development', 'dev', 'application', 'app',
        'platform', 'service', 'solution', 'web', 'mobile', 'data',
        'and', 'or', 'the', 'a', 'an', 'of', 'in', 'on', 'at', 'to'
    }
    
    def __init__(self):
        self.stopwords = self.KOREAN_STOPWORDS | self.ENGLISH_STOPWORDS
    
    def generate_abbreviation(self, project_name: str, max_length: int = 6) -> str:
        """프로젝트명에서 축약명 생성"""
        if not project_name or project_name.strip() == "":
            return "PROJ"
        
        project_name = project_name.strip()
        
        # 특수 케이스 처리
        if project_name == "미분류":
            return "미분류"
        
        # 1단계: 단어 추출
        words = self._extract_words(project_name)
        
        # 2단계: 불용어 제거
        meaningful_words = self._remove_stopwords(words)
        
        # 3단계: 축약명 생성 전략 적용
        abbreviation = self._apply_abbreviation_strategy(meaningful_words, project_name)
        
        # 4단계: 길이 조정
        return self._adjust_length(abbreviation, max_length)
    
    def _extract_words(self, text: str) -> List[str]:
        """텍스트에서 단어 추출"""
        # 영어, 한글, 숫자를 포함한 단어 추출
        words = re.findall(r'[a-zA-Z가-힣0-9]+', text)
        return [word for word in words if len(word) > 0]
    
    def _remove_stopwords(self, words: List[str]) -> List[str]:
        """불용어 제거"""
        return [word for word in words if word.lower() not in self.stopwords]
    
    def _apply_abbreviation_strategy(self, words: List[str], original: str) -> str:
        """축약명 생성 전략 적용"""
        if not words:
            # 단어가 없으면 원본에서 첫 글자들 추출
            return self._extract_initials_from_text(original)
        
        # 전략 1: 각 단어의 첫 글자 조합 (최대 3개 단어)
        if len(words) <= 3:
            initials = []
            for word in words:
                if word.isdigit():
                    initials.append(word)  # 숫자는 그대로
                elif self._is_korean(word):
                    initials.append(word[0])  # 한글 첫 글자
                else:
                    initials.append(word[0].upper())  # 영어 첫 글자 대문자
            return ''.join(initials)
        
        # 전략 2: 중요한 단어 선택 (길이, 위치 기반)
        important_words = self._select_important_words(words, 3)
        return self._apply_abbreviation_strategy(important_words, original)
    
    def _extract_initials_from_text(self, text: str) -> str:
        """텍스트에서 첫 글자들 추출"""
        # 공백, 특수문자로 구분된 부분의 첫 글자 추출
        parts = re.split(r'[\s\-_\.]+', text)
        initials = []
        
        for part in parts[:3]:  # 최대 3개 부분
            if part and len(part) > 0:
                if self._is_korean(part):
                    initials.append(part[0])
                else:
                    initials.append(part[0].upper())
        
        return ''.join(initials) if initials else text[:3].upper()
    
    def _select_important_words(self, words: List[str], max_count: int) -> List[str]:
        """중요한 단어 선택"""
        # 점수 기반 단어 선택
        word_scores = []
        
        for i, word in enumerate(words):
            score = 0
            
            # 위치 점수 (앞쪽 단어가 더 중요)
            score += (len(words) - i) * 2
            
            # 길이 점수 (적당한 길이가 좋음)
            if 2 <= len(word) <= 8:
                score += 3
            elif len(word) > 8:
                score += 1
            
            # 숫자 포함 시 보너스
            if any(c.isdigit() for c in word):
                score += 2
            
            # 대문자 포함 시 보너스 (영어)
            if any(c.isupper() for c in word):
                score += 1
            
            word_scores.append((word, score))
        
        # 점수 순으로 정렬하여 상위 단어 선택
        word_scores.sort(key=lambda x: x[1], reverse=True)
        return [word for word, _ in word_scores[:max_count]]
    
    def _is_korean(self, text: str) -> bool:
        """한글 포함 여부 확인"""
        return any('가' <= char <= '힣' for char in text)
    
    def _adjust_length(self, abbreviation: str, max_length: int) -> str:
        """축약명 길이 조정"""
        if len(abbreviation) <= max_length:
            return abbreviation
        
        # 길이가 초과하면 자르기
        if self._is_korean(abbreviation):
            # 한글은 2글자씩 의미 단위
            return abbreviation[:max_length]
        else:
            # 영어는 자음 우선 유지
            vowels = 'aeiouAEIOU'
            consonants = ''.join([c for c in abbreviation if c not in vowels])
            
            if len(consonants) <= max_length:
                return consonants
            else:
                return abbreviation[:max_length]

class SmartColorGenerator:
    """스마트 색상 생성기"""
    
    def __init__(self, use_extended_palette: bool = False):
        self.palette = ColorPalette(use_extended_palette)
        self.name_processor = ProjectNameProcessor()
        
        # 사용된 색상 추적
        self.used_colors: Set[str] = set()
        self.project_color_map: Dict[str, str] = {}
        
        # 색상 충돌 방지를 위한 설정
        self.max_same_brightness_colors = 2  # 같은 밝기 범위에서 최대 색상 수
        self.brightness_ranges = [
            (0, 85),      # 어두운 색상
            (85, 170),    # 중간 색상  
            (170, 255)    # 밝은 색상
        ]
    
    def generate_project_color(self, project_name: str, avoid_similar: bool = True) -> str:
        """프로젝트명 기반 색상 생성"""
        # 이미 할당된 색상이 있으면 반환
        if project_name in self.project_color_map:
            return self.project_color_map[project_name]
        
        # 프로젝트명 해시 기반 초기 색상 선택
        hash_value = int(hashlib.md5(project_name.encode('utf-8')).hexdigest(), 16)
        color_index = hash_value % len(self.palette.colors)
        
        selected_color = self.palette.colors[color_index]
        
        # 색상 충돌 방지
        if avoid_similar and selected_color in self.used_colors:
            selected_color = self._find_alternative_color(selected_color)
        
        # 색상 등록
        self.used_colors.add(selected_color)
        self.project_color_map[project_name] = selected_color
        
        logger.debug(f"프로젝트 '{project_name}'에 색상 '{selected_color}' 할당")
        
        return selected_color
    
    def _find_alternative_color(self, preferred_color: str) -> str:
        """대안 색상 찾기"""
        preferred_info = self.palette.get_color_info(preferred_color)
        
        # 같은 밝기 범위에서 사용되지 않은 색상 찾기
        brightness_range = self._get_brightness_range(preferred_info.brightness)
        candidate_colors = self.palette.get_colors_by_brightness(*brightness_range)
        
        # 사용되지 않은 색상 중에서 선택
        unused_colors = [color for color in candidate_colors if color not in self.used_colors]
        
        if unused_colors:
            return unused_colors[0]
        
        # 모든 색상이 사용되었으면 전체 팔레트에서 가장 적게 사용된 색상 선택
        return self._get_least_used_color()
    
    def _get_brightness_range(self, brightness: float) -> Tuple[float, float]:
        """밝기 값에 해당하는 범위 반환"""
        for min_b, max_b in self.brightness_ranges:
            if min_b <= brightness <= max_b:
                return (min_b, max_b)
        return (0, 255)  # 기본값
    
    def _get_least_used_color(self) -> str:
        """가장 적게 사용된 색상 반환"""
        # 현재는 단순히 첫 번째 색상 반환
        # 향후 사용 빈도 추적 기능 추가 가능
        return self.palette.colors[0]
    
    def generate_project_abbreviation(self, project_name: str, max_length: int = 6) -> str:
        """프로젝트 축약명 생성"""
        return self.name_processor.generate_abbreviation(project_name, max_length)
    
    def get_color_info(self, color: str) -> ColorInfo:
        """색상 정보 반환"""
        return self.palette.get_color_info(color)
    
    def reset_color_assignments(self):
        """색상 할당 초기화"""
        self.used_colors.clear()
        self.project_color_map.clear()
        logger.info("색상 할당이 초기화되었습니다")
    
    def get_color_statistics(self) -> Dict:
        """색상 사용 통계 반환"""
        return {
            "total_projects": len(self.project_color_map),
            "used_colors": len(self.used_colors),
            "available_colors": len(self.palette.colors) - len(self.used_colors),
            "color_utilization": len(self.used_colors) / len(self.palette.colors) * 100
        }

if __name__ == "__main__":
    """테스트 코드"""
    
    # 색상 생성기 테스트
    generator = SmartColorGenerator()
    
    test_projects = [
        "CareConnect 2.0 리디자인 프로젝트",
        "모바일 앱 개발",
        "데이터베이스 최적화 시스템",
        "사용자 인터페이스 개선",
        "보안 강화 프로젝트",
        "AI 챗봇 개발",
        "웹 플랫폼 구축",
        "API 서버 개발",
        "미분류"
    ]
    
    print("=" * 60)
    print("프로젝트 태그 색상 및 축약명 생성 테스트")
    print("=" * 60)
    
    for project in test_projects:
        color = generator.generate_project_color(project)
        abbreviation = generator.generate_project_abbreviation(project)
        color_info = generator.get_color_info(color)
        
        print(f"프로젝트: {project}")
        print(f"  축약명: {abbreviation}")
        print(f"  색상: {color}")
        print(f"  텍스트 색상: {color_info.contrast_text}")
        print(f"  밝기: {color_info.brightness:.1f}")
        print()
    
    # 통계 출력
    stats = generator.get_color_statistics()
    print("색상 사용 통계:")
    for key, value in stats.items():
        print(f"  {key}: {value}")