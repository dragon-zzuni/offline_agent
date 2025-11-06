#!/usr/bin/env python3
"""프로젝트 태그 시스템 에러 처리 및 폴백 메커니즘"""

import logging
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass
from enum import Enum
import traceback
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class ErrorSeverity(Enum):
    """에러 심각도"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class ProjectTagsError:
    """프로젝트 태그 시스템 에러 정보"""
    error_type: str
    message: str
    severity: ErrorSeverity
    timestamp: datetime
    component: str
    details: Optional[Dict[str, Any]] = None
    traceback_info: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "error_type": self.error_type,
            "message": self.message,
            "severity": self.severity.value,
            "timestamp": self.timestamp.isoformat(),
            "component": self.component,
            "details": self.details,
            "traceback_info": self.traceback_info
        }

class ProjectTagsErrorHandler:
    """프로젝트 태그 시스템 에러 처리기"""
    
    def __init__(self):
        self.error_history: List[ProjectTagsError] = []
        self.max_history_size = 100
        self.fallback_handlers: Dict[str, Callable] = {}
        self.error_counts: Dict[str, int] = {}
        self.last_error_time: Dict[str, datetime] = {}
        
        # 기본 폴백 핸들러 등록
        self._register_default_fallbacks()
    
    def _register_default_fallbacks(self):
        """기본 폴백 핸들러 등록"""
        self.fallback_handlers.update({
            "vdos_db_connection": self._fallback_vdos_db_connection,
            "project_classification": self._fallback_project_classification,
            "color_generation": self._fallback_color_generation,
            "tag_rendering": self._fallback_tag_rendering,
            "config_loading": self._fallback_config_loading
        })
    
    def handle_error(
        self,
        error_type: str,
        message: str,
        severity: ErrorSeverity,
        component: str,
        exception: Optional[Exception] = None,
        details: Optional[Dict[str, Any]] = None,
        enable_fallback: bool = True
    ) -> Any:
        """에러 처리 및 폴백 실행"""
        
        # 에러 정보 생성
        error_info = ProjectTagsError(
            error_type=error_type,
            message=message,
            severity=severity,
            timestamp=datetime.now(),
            component=component,
            details=details,
            traceback_info=traceback.format_exc() if exception else None
        )
        
        # 에러 기록
        self._record_error(error_info)
        
        # 로깅
        self._log_error(error_info, exception)
        
        # 폴백 실행
        if enable_fallback and error_type in self.fallback_handlers:
            try:
                return self.fallback_handlers[error_type](error_info, details)
            except Exception as fallback_error:
                logger.error(f"폴백 핸들러 실행 실패 ({error_type}): {fallback_error}")
        
        return None
    
    def _record_error(self, error_info: ProjectTagsError):
        """에러 기록"""
        # 에러 히스토리 관리
        self.error_history.append(error_info)
        if len(self.error_history) > self.max_history_size:
            self.error_history.pop(0)
        
        # 에러 카운트 업데이트
        error_key = f"{error_info.component}:{error_info.error_type}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        self.last_error_time[error_key] = error_info.timestamp
    
    def _log_error(self, error_info: ProjectTagsError, exception: Optional[Exception]):
        """에러 로깅"""
        log_message = f"[{error_info.component}] {error_info.error_type}: {error_info.message}"
        
        if error_info.severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message, exc_info=exception)
        elif error_info.severity == ErrorSeverity.HIGH:
            logger.error(log_message, exc_info=exception)
        elif error_info.severity == ErrorSeverity.MEDIUM:
            logger.warning(log_message)
        else:
            logger.info(log_message)
    
    # 폴백 핸들러들
    
    def _fallback_vdos_db_connection(self, error_info: ProjectTagsError, details: Optional[Dict]) -> Dict:
        """VDOS DB 연결 실패 시 폴백"""
        logger.info("VDOS DB 연결 실패, 기본 프로젝트 목록 사용")
        
        # 기본 프로젝트 목록 반환
        default_projects = {
            1: {
                "name": "일반 프로젝트",
                "description": "분류되지 않은 일반적인 작업",
                "participants": [],
                "keywords": ["일반", "기본"]
            },
            2: {
                "name": "긴급 작업",
                "description": "긴급하게 처리해야 하는 작업",
                "participants": [],
                "keywords": ["긴급", "urgent", "즉시"]
            },
            3: {
                "name": "개발 작업",
                "description": "소프트웨어 개발 관련 작업",
                "participants": [],
                "keywords": ["개발", "코딩", "프로그래밍", "버그"]
            }
        }
        
        return default_projects
    
    def _fallback_project_classification(self, error_info: ProjectTagsError, details: Optional[Dict]) -> str:
        """프로젝트 분류 실패 시 폴백"""
        logger.info("프로젝트 분류 실패, '미분류'로 처리")
        return "미분류"
    
    def _fallback_color_generation(self, error_info: ProjectTagsError, details: Optional[Dict]) -> str:
        """색상 생성 실패 시 폴백"""
        logger.info("색상 생성 실패, 기본 색상 사용")
        
        # 기본 색상 목록
        default_colors = [
            "#6b7280",  # 회색 (기본)
            "#3b82f6",  # 파란색
            "#10b981",  # 초록색
            "#f59e0b",  # 주황색
            "#ef4444"   # 빨간색
        ]
        
        # 프로젝트명 해시 기반 색상 선택
        project_name = details.get("project_name", "default") if details else "default"
        color_index = hash(project_name) % len(default_colors)
        
        return default_colors[color_index]
    
    def _fallback_tag_rendering(self, error_info: ProjectTagsError, details: Optional[Dict]) -> str:
        """태그 렌더링 실패 시 폴백"""
        logger.info("태그 렌더링 실패, 텍스트만 표시")
        
        project_name = details.get("project_name", "미분류") if details else "미분류"
        return f"[{project_name}]"
    
    def _fallback_config_loading(self, error_info: ProjectTagsError, details: Optional[Dict]) -> Dict:
        """설정 로딩 실패 시 폴백"""
        logger.info("설정 로딩 실패, 기본 설정 사용")
        
        from config.project_tags_config import ProjectTagsConfig
        return ProjectTagsConfig().to_dict()
    
    # 에러 분석 및 리포팅
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """에러 통계 반환"""
        if not self.error_history:
            return {"total_errors": 0}
        
        # 심각도별 통계
        severity_counts = {}
        for error in self.error_history:
            severity = error.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        # 컴포넌트별 통계
        component_counts = {}
        for error in self.error_history:
            component = error.component
            component_counts[component] = component_counts.get(component, 0) + 1
        
        # 최근 에러들
        recent_errors = [
            error.to_dict() for error in self.error_history[-10:]
        ]
        
        return {
            "total_errors": len(self.error_history),
            "severity_distribution": severity_counts,
            "component_distribution": component_counts,
            "recent_errors": recent_errors,
            "error_counts": dict(self.error_counts),
            "last_error_times": {
                key: time.isoformat() for key, time in self.last_error_time.items()
            }
        }
    
    def is_component_healthy(self, component: str, time_window_minutes: int = 60) -> bool:
        """컴포넌트 건강 상태 확인"""
        cutoff_time = datetime.now() - timedelta(minutes=time_window_minutes)
        
        recent_errors = [
            error for error in self.error_history
            if error.component == component and error.timestamp > cutoff_time
        ]
        
        # 최근 시간 내 심각한 에러가 있는지 확인
        critical_errors = [
            error for error in recent_errors
            if error.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]
        ]
        
        return len(critical_errors) == 0
    
    def get_health_report(self) -> Dict[str, Any]:
        """전체 시스템 건강 상태 리포트"""
        components = ["vdos_db", "project_classifier", "color_generator", "tag_renderer", "config_manager"]
        
        health_status = {}
        for component in components:
            health_status[component] = {
                "healthy": self.is_component_healthy(component),
                "error_count_1h": len([
                    error for error in self.error_history
                    if error.component == component and 
                       error.timestamp > datetime.now() - timedelta(hours=1)
                ]),
                "last_error": None
            }
            
            # 마지막 에러 시간
            component_errors = [
                error for error in self.error_history
                if error.component == component
            ]
            if component_errors:
                health_status[component]["last_error"] = component_errors[-1].timestamp.isoformat()
        
        # 전체 건강 상태
        overall_healthy = all(status["healthy"] for status in health_status.values())
        
        return {
            "overall_healthy": overall_healthy,
            "components": health_status,
            "total_errors_24h": len([
                error for error in self.error_history
                if error.timestamp > datetime.now() - timedelta(hours=24)
            ]),
            "report_timestamp": datetime.now().isoformat()
        }
    
    def clear_error_history(self):
        """에러 히스토리 초기화"""
        self.error_history.clear()
        self.error_counts.clear()
        self.last_error_time.clear()
        logger.info("에러 히스토리가 초기화되었습니다")
    
    def register_fallback_handler(self, error_type: str, handler: Callable):
        """사용자 정의 폴백 핸들러 등록"""
        self.fallback_handlers[error_type] = handler
        logger.info(f"폴백 핸들러 등록: {error_type}")

# 전역 에러 핸들러 인스턴스
_error_handler: Optional[ProjectTagsErrorHandler] = None

def get_error_handler() -> ProjectTagsErrorHandler:
    """전역 에러 핸들러 반환"""
    global _error_handler
    if _error_handler is None:
        _error_handler = ProjectTagsErrorHandler()
    return _error_handler

def handle_project_tags_error(
    error_type: str,
    message: str,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    component: str = "unknown",
    exception: Optional[Exception] = None,
    details: Optional[Dict[str, Any]] = None,
    enable_fallback: bool = True
) -> Any:
    """편의 함수: 프로젝트 태그 에러 처리"""
    return get_error_handler().handle_error(
        error_type=error_type,
        message=message,
        severity=severity,
        component=component,
        exception=exception,
        details=details,
        enable_fallback=enable_fallback
    )

# 데코레이터
def with_error_handling(
    error_type: str,
    component: str,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    fallback_value: Any = None
):
    """에러 처리 데코레이터"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                handle_project_tags_error(
                    error_type=error_type,
                    message=f"함수 {func.__name__} 실행 중 에러: {str(e)}",
                    severity=severity,
                    component=component,
                    exception=e
                )
                return fallback_value
        return wrapper
    return decorator

if __name__ == "__main__":
    """테스트 코드"""
    
    print("=" * 60)
    print("프로젝트 태그 에러 처리 시스템 테스트")
    print("=" * 60)
    
    # 에러 핸들러 테스트
    error_handler = ProjectTagsErrorHandler()
    
    # 다양한 에러 시뮬레이션
    test_errors = [
        {
            "error_type": "vdos_db_connection",
            "message": "VDOS 데이터베이스 연결 실패",
            "severity": ErrorSeverity.HIGH,
            "component": "vdos_db"
        },
        {
            "error_type": "project_classification",
            "message": "프로젝트 분류 실패",
            "severity": ErrorSeverity.MEDIUM,
            "component": "project_classifier"
        },
        {
            "error_type": "color_generation",
            "message": "색상 생성 실패",
            "severity": ErrorSeverity.LOW,
            "component": "color_generator"
        }
    ]
    
    print("에러 처리 테스트:")
    for i, error_info in enumerate(test_errors, 1):
        print(f"\n{i}. {error_info['error_type']} 에러 처리")
        
        result = error_handler.handle_error(**error_info)
        print(f"   폴백 결과: {type(result).__name__}")
        
        if error_info["error_type"] == "vdos_db_connection":
            print(f"   기본 프로젝트 수: {len(result) if result else 0}")
    
    # 에러 통계 확인
    print(f"\n에러 통계:")
    stats = error_handler.get_error_statistics()
    print(f"  총 에러 수: {stats['total_errors']}")
    print(f"  심각도별 분포: {stats['severity_distribution']}")
    print(f"  컴포넌트별 분포: {stats['component_distribution']}")
    
    # 건강 상태 리포트
    print(f"\n건강 상태 리포트:")
    health_report = error_handler.get_health_report()
    print(f"  전체 건강 상태: {'✅ 양호' if health_report['overall_healthy'] else '❌ 문제 있음'}")
    
    for component, status in health_report['components'].items():
        health_icon = "✅" if status['healthy'] else "❌"
        print(f"  {component}: {health_icon} (1시간 내 에러: {status['error_count_1h']}개)")
    
    # 데코레이터 테스트
    print(f"\n데코레이터 테스트:")
    
    @with_error_handling("test_function", "test_component", fallback_value="폴백 값")
    def test_function_with_error():
        raise ValueError("테스트 에러")
    
    result = test_function_with_error()
    print(f"  데코레이터 폴백 결과: {result}")
    
    print("\n✅ 모든 테스트 완료")