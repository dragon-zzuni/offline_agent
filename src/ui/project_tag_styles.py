#!/usr/bin/env python3
"""프로젝트 태그 스타일링 및 레이아웃 시스템"""

from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class TagSize(Enum):
    """태그 크기 옵션"""
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"

class TagStyle(Enum):
    """태그 스타일 옵션"""
    ROUNDED = "rounded"
    PILL = "pill"
    SQUARE = "square"
    MINIMAL = "minimal"

@dataclass
class TagDimensions:
    """태그 크기 정보"""
    height: int
    padding_horizontal: int
    padding_vertical: int
    font_size: int
    border_radius: int
    margin: int

@dataclass
class TagColorScheme:
    """태그 색상 스키마"""
    background: str
    text: str
    border: str
    hover_background: str
    hover_text: str
    active_background: str
    active_border: str

class ProjectTagStyleManager:
    """프로젝트 태그 스타일 관리자"""
    
    # 크기별 치수 정의
    SIZE_DIMENSIONS = {
        TagSize.SMALL: TagDimensions(
            height=20,
            padding_horizontal=8,
            padding_vertical=2,
            font_size=9,
            border_radius=10,
            margin=2
        ),
        TagSize.MEDIUM: TagDimensions(
            height=24,
            padding_horizontal=12,
            padding_vertical=4,
            font_size=10,
            border_radius=12,
            margin=3
        ),
        TagSize.LARGE: TagDimensions(
            height=28,
            padding_horizontal=16,
            padding_vertical=6,
            font_size=11,
            border_radius=14,
            margin=4
        )
    }
    
    def __init__(self):
        self.current_size = TagSize.MEDIUM
        self.current_style = TagStyle.ROUNDED
        self.animation_enabled = True
        self.shadow_enabled = True
    
    def generate_tag_stylesheet(
        self, 
        background_color: str,
        text_color: str = None,
        size: TagSize = None,
        style: TagStyle = None,
        is_active: bool = False,
        is_clickable: bool = True
    ) -> str:
        """태그 스타일시트 생성"""
        
        size = size or self.current_size
        style = style or self.current_style
        
        # 크기 정보 가져오기
        dimensions = self.SIZE_DIMENSIONS[size]
        
        # 색상 스키마 생성
        color_scheme = self._create_color_scheme(background_color, text_color, is_active)
        
        # 스타일별 속성 생성
        style_properties = self._get_style_properties(style, dimensions)
        
        # 기본 스타일
        base_style = f"""
        QLabel {{
            background-color: {color_scheme.background};
            color: {color_scheme.text};
            border: 1px solid {color_scheme.border};
            border-radius: {style_properties['border_radius']}px;
            padding: {dimensions.padding_vertical}px {dimensions.padding_horizontal}px;
            margin: {dimensions.margin}px;
            font-size: {dimensions.font_size}px;
            font-weight: 500;
            min-height: {dimensions.height}px;
            max-height: {dimensions.height}px;
            {style_properties['additional_properties']}
        }}
        """
        
        # 호버 효과 (클릭 가능한 경우만)
        if is_clickable:
            hover_style = f"""
            QLabel:hover {{
                background-color: {color_scheme.hover_background};
                color: {color_scheme.hover_text};
                {self._get_hover_effects()}
            }}
            """
            base_style += hover_style
        
        # 활성 상태 스타일
        if is_active:
            active_style = f"""
            QLabel {{
                background-color: {color_scheme.active_background} !important;
                border: 2px solid {color_scheme.active_border} !important;
                font-weight: 600;
            }}
            """
            base_style += active_style
        
        return base_style
    
    def _create_color_scheme(self, background_color: str, text_color: str = None, is_active: bool = False) -> TagColorScheme:
        """색상 스키마 생성"""
        
        # 텍스트 색상 자동 결정
        if text_color is None:
            text_color = self._get_contrast_color(background_color)
        
        # 호버 색상 생성
        hover_bg = self._adjust_color_brightness(background_color, 0.1)
        hover_text = text_color
        
        # 활성 상태 색상
        active_bg = self._adjust_color_brightness(background_color, -0.1)
        active_border = self._adjust_color_brightness(background_color, -0.2)
        
        # 테두리 색상
        border_color = self._adjust_color_brightness(background_color, -0.1) if not is_active else active_border
        
        return TagColorScheme(
            background=background_color,
            text=text_color,
            border=border_color,
            hover_background=hover_bg,
            hover_text=hover_text,
            active_background=active_bg,
            active_border=active_border
        )
    
    def _get_style_properties(self, style: TagStyle, dimensions: TagDimensions) -> Dict[str, str]:
        """스타일별 속성 반환"""
        
        properties = {
            'border_radius': dimensions.border_radius,
            'additional_properties': ''
        }
        
        if style == TagStyle.PILL:
            # 완전히 둥근 모양
            properties['border_radius'] = dimensions.height // 2
            
        elif style == TagStyle.SQUARE:
            # 사각형 모양
            properties['border_radius'] = 2
            
        elif style == TagStyle.MINIMAL:
            # 미니멀 스타일
            properties['border_radius'] = 4
            properties['additional_properties'] = """
                border: none;
                background-color: transparent;
                text-decoration: underline;
            """
            
        # 그림자 효과 추가
        if self.shadow_enabled and style != TagStyle.MINIMAL:
            properties['additional_properties'] += """
                /* 그림자는 CSS에서 지원하지 않으므로 QGraphicsDropShadowEffect 사용 필요 */
            """
        
        return properties
    
    def _get_hover_effects(self) -> str:
        """호버 효과 스타일 반환"""
        effects = []
        
        if self.animation_enabled:
            effects.append("/* 애니메이션 효과는 QPropertyAnimation으로 구현 */")
        
        # 기본 호버 효과
        effects.append("border-width: 2px;")
        
        return '\n'.join(effects)
    
    def _get_contrast_color(self, bg_color: str) -> str:
        """배경색에 대한 대비 텍스트 색상 반환"""
        # HEX 색상에서 RGB 추출
        if bg_color.startswith('#'):
            bg_color = bg_color[1:]
        
        try:
            r = int(bg_color[0:2], 16)
            g = int(bg_color[2:4], 16)
            b = int(bg_color[4:6], 16)
            
            # 밝기 계산 (0.299*R + 0.587*G + 0.114*B)
            brightness = (r * 299 + g * 587 + b * 114) / 1000
            
            # 밝기에 따라 텍스트 색상 결정
            return "#ffffff" if brightness < 128 else "#000000"
        except (ValueError, IndexError):
            return "#ffffff"  # 기본값
    
    def _adjust_color_brightness(self, color: str, factor: float) -> str:
        """색상 밝기 조정"""
        if color.startswith('#'):
            color = color[1:]
        
        try:
            r = int(color[0:2], 16)
            g = int(color[2:4], 16)
            b = int(color[4:6], 16)
            
            if factor > 0:
                # 밝게 만들기
                r = min(255, int(r + (255 - r) * factor))
                g = min(255, int(g + (255 - g) * factor))
                b = min(255, int(b + (255 - b) * factor))
            else:
                # 어둡게 만들기
                factor = abs(factor)
                r = max(0, int(r * (1 - factor)))
                g = max(0, int(g * (1 - factor)))
                b = max(0, int(b * (1 - factor)))
            
            return f"#{r:02x}{g:02x}{b:02x}"
        except (ValueError, IndexError):
            return color
    
    def create_filter_button_style(self, background_color: str, is_active: bool = False) -> str:
        """필터 버튼용 스타일 생성"""
        return self.generate_tag_stylesheet(
            background_color=background_color,
            size=TagSize.MEDIUM,
            style=TagStyle.ROUNDED,
            is_active=is_active,
            is_clickable=True
        )
    
    def create_display_tag_style(self, background_color: str) -> str:
        """표시용 태그 스타일 생성 (클릭 불가)"""
        return self.generate_tag_stylesheet(
            background_color=background_color,
            size=TagSize.SMALL,
            style=TagStyle.PILL,
            is_active=False,
            is_clickable=False
        )
    
    def set_global_settings(
        self, 
        size: TagSize = None,
        style: TagStyle = None,
        animation_enabled: bool = None,
        shadow_enabled: bool = None
    ):
        """전역 설정 변경"""
        if size is not None:
            self.current_size = size
        if style is not None:
            self.current_style = style
        if animation_enabled is not None:
            self.animation_enabled = animation_enabled
        if shadow_enabled is not None:
            self.shadow_enabled = shadow_enabled
        
        logger.info(f"태그 스타일 설정 변경: size={self.current_size}, style={self.current_style}")

class ProjectTagLayoutManager:
    """프로젝트 태그 레이아웃 관리자"""
    
    def __init__(self):
        self.max_tags_per_row = 6
        self.tag_spacing = 4
        self.row_spacing = 8
        self.container_padding = 8
    
    def calculate_layout_dimensions(self, tag_count: int, container_width: int) -> Dict[str, int]:
        """레이아웃 치수 계산"""
        
        # 태그 크기 추정 (평균 태그 너비)
        avg_tag_width = 80  # 평균 태그 너비 (픽셀)
        
        # 한 행에 들어갈 수 있는 태그 수 계산
        available_width = container_width - (self.container_padding * 2)
        tags_per_row = min(
            self.max_tags_per_row,
            max(1, available_width // (avg_tag_width + self.tag_spacing))
        )
        
        # 필요한 행 수 계산
        rows_needed = (tag_count + tags_per_row - 1) // tags_per_row
        
        # 전체 높이 계산
        tag_height = 24  # 기본 태그 높이
        total_height = (
            (rows_needed * tag_height) + 
            ((rows_needed - 1) * self.row_spacing) + 
            (self.container_padding * 2)
        )
        
        return {
            'tags_per_row': tags_per_row,
            'rows_needed': rows_needed,
            'total_height': total_height,
            'available_width': available_width
        }
    
    def create_container_stylesheet(self, background_color: str = "#f8f9fa") -> str:
        """컨테이너 스타일시트 생성"""
        return f"""
        QWidget {{
            background-color: {background_color};
            border: 1px solid #e9ecef;
            border-radius: 8px;
            padding: {self.container_padding}px;
        }}
        """
    
    def create_layout_config(self) -> Dict[str, int]:
        """레이아웃 설정 반환"""
        return {
            'spacing': self.tag_spacing,
            'margins': self.container_padding,
            'max_tags_per_row': self.max_tags_per_row
        }
    
    def set_layout_settings(
        self,
        max_tags_per_row: int = None,
        tag_spacing: int = None,
        row_spacing: int = None,
        container_padding: int = None
    ):
        """레이아웃 설정 변경"""
        if max_tags_per_row is not None:
            self.max_tags_per_row = max_tags_per_row
        if tag_spacing is not None:
            self.tag_spacing = tag_spacing
        if row_spacing is not None:
            self.row_spacing = row_spacing
        if container_padding is not None:
            self.container_padding = container_padding

class ResponsiveTagLayout:
    """반응형 태그 레이아웃"""
    
    def __init__(self):
        self.breakpoints = {
            'small': 400,
            'medium': 600,
            'large': 800
        }
        
        self.layout_configs = {
            'small': {'max_tags_per_row': 3, 'tag_size': TagSize.SMALL},
            'medium': {'max_tags_per_row': 5, 'tag_size': TagSize.MEDIUM},
            'large': {'max_tags_per_row': 8, 'tag_size': TagSize.MEDIUM}
        }
    
    def get_layout_for_width(self, width: int) -> Dict:
        """너비에 따른 레이아웃 설정 반환"""
        if width <= self.breakpoints['small']:
            return self.layout_configs['small']
        elif width <= self.breakpoints['medium']:
            return self.layout_configs['medium']
        else:
            return self.layout_configs['large']
    
    def should_update_layout(self, old_width: int, new_width: int) -> bool:
        """레이아웃 업데이트 필요 여부 확인"""
        old_config = self.get_layout_for_width(old_width)
        new_config = self.get_layout_for_width(new_width)
        return old_config != new_config

# 전역 스타일 관리자 인스턴스
tag_style_manager = ProjectTagStyleManager()
tag_layout_manager = ProjectTagLayoutManager()
responsive_layout = ResponsiveTagLayout()

def get_tag_style(background_color: str, **kwargs) -> str:
    """편의 함수: 태그 스타일 생성"""
    return tag_style_manager.generate_tag_stylesheet(background_color, **kwargs)

def get_filter_button_style(background_color: str, is_active: bool = False) -> str:
    """편의 함수: 필터 버튼 스타일 생성"""
    return tag_style_manager.create_filter_button_style(background_color, is_active)

def get_display_tag_style(background_color: str) -> str:
    """편의 함수: 표시용 태그 스타일 생성"""
    return tag_style_manager.create_display_tag_style(background_color)

if __name__ == "__main__":
    """테스트 코드"""
    
    print("=" * 60)
    print("프로젝트 태그 스타일링 시스템 테스트")
    print("=" * 60)
    
    # 스타일 관리자 테스트
    style_manager = ProjectTagStyleManager()
    
    test_colors = [
        "#2563eb",  # 파란색
        "#16a34a",  # 초록색
        "#ea580c",  # 주황색
        "#9333ea"   # 보라색
    ]
    
    print("생성된 스타일시트 예시:")
    print("-" * 40)
    
    for i, color in enumerate(test_colors):
        print(f"\n{i+1}. 색상: {color}")
        
        # 기본 스타일
        basic_style = style_manager.generate_tag_stylesheet(color)
        print("기본 스타일 (일부):")
        print(basic_style.split('\n')[1:4])  # 첫 몇 줄만 출력
        
        # 활성 상태 스타일
        active_style = style_manager.generate_tag_stylesheet(color, is_active=True)
        print("활성 상태 스타일 생성됨")
    
    # 레이아웃 관리자 테스트
    print("\n" + "=" * 40)
    print("레이아웃 관리자 테스트")
    print("=" * 40)
    
    layout_manager = ProjectTagLayoutManager()
    
    test_scenarios = [
        (5, 400),   # 5개 태그, 400px 너비
        (10, 600),  # 10개 태그, 600px 너비
        (15, 800)   # 15개 태그, 800px 너비
    ]
    
    for tag_count, width in test_scenarios:
        dimensions = layout_manager.calculate_layout_dimensions(tag_count, width)
        print(f"\n태그 {tag_count}개, 너비 {width}px:")
        print(f"  행당 태그 수: {dimensions['tags_per_row']}")
        print(f"  필요한 행 수: {dimensions['rows_needed']}")
        print(f"  전체 높이: {dimensions['total_height']}px")
    
    # 반응형 레이아웃 테스트
    print("\n" + "=" * 40)
    print("반응형 레이아웃 테스트")
    print("=" * 40)
    
    responsive = ResponsiveTagLayout()
    
    test_widths = [350, 500, 750, 900]
    
    for width in test_widths:
        config = responsive.get_layout_for_width(width)
        print(f"너비 {width}px: {config}")
    
    print("\n✅ 모든 테스트 완료")