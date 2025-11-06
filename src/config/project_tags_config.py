#!/usr/bin/env python3
"""프로젝트 태그 시스템 설정 관리"""

import json
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

@dataclass
class ProjectTagsConfig:
    """프로젝트 태그 시스템 설정"""
    
    # 분류 관련 설정
    classification_confidence_threshold: float = 0.4
    keyword_matching_weight: float = 0.6
    sender_matching_weight: float = 0.4
    
    # UI 관련 설정
    tag_size: str = "medium"  # small, medium, large
    tag_style: str = "rounded"  # rounded, pill, square, minimal
    show_project_counts: bool = True
    max_tags_per_row: int = 6
    
    # 색상 관련 설정
    use_extended_color_palette: bool = False
    auto_generate_colors: bool = True
    color_generation_mode: str = "hash"  # hash, random, manual
    
    # 성능 관련 설정
    enable_project_caching: bool = True
    cache_expiry_minutes: int = 30
    max_cached_projects: int = 50
    
    # VDOS DB 연동 설정
    vdos_db_path: str = "virtualoffice/src/virtualoffice/vdos.db"
    auto_refresh_projects: bool = True
    refresh_interval_minutes: int = 60
    
    # 디버그 설정
    enable_debug_logging: bool = False
    log_classification_results: bool = False
    show_confidence_scores: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProjectTagsConfig':
        """딕셔너리에서 생성"""
        # 알려진 필드만 사용하여 인스턴스 생성
        known_fields = {
            field.name for field in cls.__dataclass_fields__.values()
        }
        
        filtered_data = {
            key: value for key, value in data.items()
            if key in known_fields
        }
        
        return cls(**filtered_data)
    
    def validate(self) -> bool:
        """설정 값 유효성 검사"""
        try:
            # 신뢰도 임계값 검사
            if not 0.0 <= self.classification_confidence_threshold <= 1.0:
                logger.error("classification_confidence_threshold는 0.0~1.0 사이여야 합니다")
                return False
            
            # 가중치 검사
            total_weight = self.keyword_matching_weight + self.sender_matching_weight
            if abs(total_weight - 1.0) > 0.01:  # 부동소수점 오차 허용
                logger.error("keyword_matching_weight + sender_matching_weight = 1.0이어야 합니다")
                return False
            
            # 태그 크기 검사
            if self.tag_size not in ["small", "medium", "large"]:
                logger.error("tag_size는 small, medium, large 중 하나여야 합니다")
                return False
            
            # 태그 스타일 검사
            if self.tag_style not in ["rounded", "pill", "square", "minimal"]:
                logger.error("tag_style은 rounded, pill, square, minimal 중 하나여야 합니다")
                return False
            
            # 색상 생성 모드 검사
            if self.color_generation_mode not in ["hash", "random", "manual"]:
                logger.error("color_generation_mode는 hash, random, manual 중 하나여야 합니다")
                return False
            
            # 양수 값 검사
            positive_fields = [
                "max_tags_per_row", "cache_expiry_minutes", "max_cached_projects",
                "refresh_interval_minutes"
            ]
            
            for field in positive_fields:
                value = getattr(self, field)
                if value <= 0:
                    logger.error(f"{field}는 양수여야 합니다")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"설정 유효성 검사 중 오류: {e}")
            return False

class ProjectTagsConfigManager:
    """프로젝트 태그 설정 관리자"""
    
    DEFAULT_CONFIG_PATH = "config/project_tags_config.json"
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = Path(config_path or self.DEFAULT_CONFIG_PATH)
        self._config: Optional[ProjectTagsConfig] = None
        self._ensure_config_dir()
    
    def _ensure_config_dir(self):
        """설정 디렉토리 생성"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
    
    def load_config(self) -> ProjectTagsConfig:
        """설정 로드"""
        if self._config is not None:
            return self._config
        
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                config = ProjectTagsConfig.from_dict(data)
                
                # 유효성 검사
                if config.validate():
                    self._config = config
                    logger.info(f"프로젝트 태그 설정 로드 완료: {self.config_path}")
                else:
                    logger.warning("설정 파일이 유효하지 않아 기본 설정을 사용합니다")
                    self._config = ProjectTagsConfig()
            else:
                logger.info("설정 파일이 없어 기본 설정을 생성합니다")
                self._config = ProjectTagsConfig()
                self.save_config()
        
        except Exception as e:
            logger.error(f"설정 로드 실패, 기본 설정 사용: {e}")
            self._config = ProjectTagsConfig()
        
        return self._config
    
    def save_config(self, config: Optional[ProjectTagsConfig] = None) -> bool:
        """설정 저장"""
        try:
            config_to_save = config or self._config
            if config_to_save is None:
                logger.error("저장할 설정이 없습니다")
                return False
            
            # 유효성 검사
            if not config_to_save.validate():
                logger.error("유효하지 않은 설정은 저장할 수 없습니다")
                return False
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config_to_save.to_dict(), f, indent=2, ensure_ascii=False)
            
            self._config = config_to_save
            logger.info(f"프로젝트 태그 설정 저장 완료: {self.config_path}")
            return True
            
        except Exception as e:
            logger.error(f"설정 저장 실패: {e}")
            return False
    
    def update_config(self, **kwargs) -> bool:
        """설정 업데이트"""
        try:
            current_config = self.load_config()
            
            # 새 설정으로 업데이트
            config_dict = current_config.to_dict()
            config_dict.update(kwargs)
            
            new_config = ProjectTagsConfig.from_dict(config_dict)
            
            return self.save_config(new_config)
            
        except Exception as e:
            logger.error(f"설정 업데이트 실패: {e}")
            return False
    
    def reset_to_default(self) -> bool:
        """기본 설정으로 초기화"""
        try:
            default_config = ProjectTagsConfig()
            return self.save_config(default_config)
        except Exception as e:
            logger.error(f"기본 설정 초기화 실패: {e}")
            return False
    
    def get_config(self) -> ProjectTagsConfig:
        """현재 설정 반환"""
        return self.load_config()
    
    def backup_config(self, backup_path: Optional[str] = None) -> bool:
        """설정 백업"""
        try:
            if not self.config_path.exists():
                logger.warning("백업할 설정 파일이 없습니다")
                return False
            
            if backup_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = f"{self.config_path}.backup_{timestamp}"
            
            backup_path = Path(backup_path)
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            
            import shutil
            shutil.copy2(self.config_path, backup_path)
            
            logger.info(f"설정 백업 완료: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"설정 백업 실패: {e}")
            return False
    
    def restore_config(self, backup_path: str) -> bool:
        """설정 복원"""
        try:
            backup_path = Path(backup_path)
            if not backup_path.exists():
                logger.error(f"백업 파일이 없습니다: {backup_path}")
                return False
            
            # 백업 파일 유효성 검사
            with open(backup_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            config = ProjectTagsConfig.from_dict(data)
            if not config.validate():
                logger.error("백업 파일의 설정이 유효하지 않습니다")
                return False
            
            # 현재 설정 백업
            self.backup_config()
            
            # 백업에서 복원
            import shutil
            shutil.copy2(backup_path, self.config_path)
            
            # 캐시 무효화
            self._config = None
            
            logger.info(f"설정 복원 완료: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"설정 복원 실패: {e}")
            return False

# 전역 설정 관리자 인스턴스
_config_manager: Optional[ProjectTagsConfigManager] = None

def get_config_manager() -> ProjectTagsConfigManager:
    """전역 설정 관리자 반환"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ProjectTagsConfigManager()
    return _config_manager

def get_project_tags_config() -> ProjectTagsConfig:
    """현재 프로젝트 태그 설정 반환"""
    return get_config_manager().get_config()

def update_project_tags_config(**kwargs) -> bool:
    """프로젝트 태그 설정 업데이트"""
    return get_config_manager().update_config(**kwargs)

if __name__ == "__main__":
    """테스트 코드"""
    
    print("=" * 60)
    print("프로젝트 태그 설정 관리 테스트")
    print("=" * 60)
    
    # 설정 관리자 테스트
    config_manager = ProjectTagsConfigManager("test_config.json")
    
    # 기본 설정 로드
    config = config_manager.load_config()
    print(f"기본 설정 로드:")
    print(f"  분류 신뢰도 임계값: {config.classification_confidence_threshold}")
    print(f"  태그 크기: {config.tag_size}")
    print(f"  색상 팔레트 확장: {config.use_extended_color_palette}")
    
    # 설정 업데이트 테스트
    print(f"\n설정 업데이트 테스트:")
    success = config_manager.update_config(
        classification_confidence_threshold=0.5,
        tag_size="large",
        enable_debug_logging=True
    )
    print(f"  업데이트 성공: {success}")
    
    # 업데이트된 설정 확인
    updated_config = config_manager.get_config()
    print(f"  업데이트된 신뢰도 임계값: {updated_config.classification_confidence_threshold}")
    print(f"  업데이트된 태그 크기: {updated_config.tag_size}")
    print(f"  디버그 로깅: {updated_config.enable_debug_logging}")
    
    # 유효성 검사 테스트
    print(f"\n유효성 검사 테스트:")
    
    # 잘못된 설정
    invalid_config = ProjectTagsConfig(
        classification_confidence_threshold=1.5,  # 범위 초과
        keyword_matching_weight=0.7,
        sender_matching_weight=0.4  # 합계가 1.0이 아님
    )
    
    print(f"  잘못된 설정 유효성 검사: {invalid_config.validate()}")
    
    # 올바른 설정
    valid_config = ProjectTagsConfig(
        classification_confidence_threshold=0.6,
        keyword_matching_weight=0.7,
        sender_matching_weight=0.3
    )
    
    print(f"  올바른 설정 유효성 검사: {valid_config.validate()}")
    
    # 백업 및 복원 테스트
    print(f"\n백업 및 복원 테스트:")
    backup_success = config_manager.backup_config("test_backup.json")
    print(f"  백업 성공: {backup_success}")
    
    # 설정 파일 정리
    import os
    try:
        os.remove("test_config.json")
        os.remove("test_backup.json")
        print("  테스트 파일 정리 완료")
    except:
        pass
    
    print("\n✅ 모든 테스트 완료")