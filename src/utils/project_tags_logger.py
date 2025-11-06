#!/usr/bin/env python3
"""프로젝트 태그 시스템 로깅 및 디버깅 지원"""

import logging
import json
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict
import functools

@dataclass
class ClassificationLog:
    """프로젝트 분류 로그"""
    timestamp: datetime
    message_content: str
    sender_name: str
    classification_result: str
    confidence: float
    classification_methods: List[str]
    matched_keywords: List[str]
    processing_time_ms: float
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "message_content": self.message_content[:100] + "..." if len(self.message_content) > 100 else self.message_content,
            "sender_name": self.sender_name,
            "classification_result": self.classification_result,
            "confidence": round(self.confidence, 3),
            "classification_methods": self.classification_methods,
            "matched_keywords": self.matched_keywords,
            "processing_time_ms": round(self.processing_time_ms, 2)
        }

@dataclass
class PerformanceMetrics:
    """성능 메트릭"""
    component: str
    operation: str
    start_time: float
    end_time: float
    success: bool
    error_message: Optional[str] = None
    
    @property
    def duration_ms(self) -> float:
        """실행 시간 (밀리초)"""
        return (self.end_time - self.start_time) * 1000
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "component": self.component,
            "operation": self.operation,
            "duration_ms": round(self.duration_ms, 2),
            "success": self.success,
            "error_message": self.error_message,
            "timestamp": datetime.fromtimestamp(self.start_time).isoformat()
        }

class ProjectTagsLogger:
    """프로젝트 태그 시스템 전용 로거"""
    
    def __init__(self, log_dir: str = "logs", enable_debug: bool = False):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        self.enable_debug = enable_debug
        self.classification_logs: List[ClassificationLog] = []
        self.performance_metrics: List[PerformanceMetrics] = []
        
        # 로그 파일 설정
        self.classification_log_file = self.log_dir / "project_classification.log"
        self.performance_log_file = self.log_dir / "project_tags_performance.log"
        self.debug_log_file = self.log_dir / "project_tags_debug.log"
        
        # 로거 설정
        self._setup_loggers()
        
        # 메모리 제한
        self.max_memory_logs = 1000
    
    def _setup_loggers(self):
        """로거 설정"""
        # 분류 로거
        self.classification_logger = logging.getLogger("project_tags.classification")
        self.classification_logger.setLevel(logging.INFO)
        
        if not self.classification_logger.handlers:
            handler = logging.FileHandler(self.classification_log_file, encoding='utf-8')
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            self.classification_logger.addHandler(handler)
        
        # 성능 로거
        self.performance_logger = logging.getLogger("project_tags.performance")
        self.performance_logger.setLevel(logging.INFO)
        
        if not self.performance_logger.handlers:
            handler = logging.FileHandler(self.performance_log_file, encoding='utf-8')
            formatter = logging.Formatter(
                '%(asctime)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            self.performance_logger.addHandler(handler)
        
        # 디버그 로거
        if self.enable_debug:
            self.debug_logger = logging.getLogger("project_tags.debug")
            self.debug_logger.setLevel(logging.DEBUG)
            
            if not self.debug_logger.handlers:
                handler = logging.FileHandler(self.debug_log_file, encoding='utf-8')
                formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
                handler.setFormatter(formatter)
                self.debug_logger.addHandler(handler)
    
    def log_classification(
        self,
        message_content: str,
        sender_name: str,
        classification_result: str,
        confidence: float,
        classification_methods: List[str],
        matched_keywords: List[str],
        processing_time_ms: float
    ):
        """프로젝트 분류 결과 로깅"""
        
        # 로그 객체 생성
        log_entry = ClassificationLog(
            timestamp=datetime.now(),
            message_content=message_content,
            sender_name=sender_name,
            classification_result=classification_result,
            confidence=confidence,
            classification_methods=classification_methods,
            matched_keywords=matched_keywords,
            processing_time_ms=processing_time_ms
        )
        
        # 메모리에 저장
        self.classification_logs.append(log_entry)
        self._trim_memory_logs()
        
        # 파일에 로깅
        log_message = (
            f"분류 결과: {classification_result} "
            f"(신뢰도: {confidence:.3f}, "
            f"처리시간: {processing_time_ms:.2f}ms) "
            f"- 발신자: {sender_name}, "
            f"키워드: {matched_keywords}, "
            f"방법: {classification_methods}"
        )
        
        self.classification_logger.info(log_message)
        
        # 디버그 로깅
        if self.enable_debug:
            debug_info = {
                "message_preview": message_content[:50] + "..." if len(message_content) > 50 else message_content,
                "full_classification_data": log_entry.to_dict()
            }
            self.debug_logger.debug(f"분류 상세 정보: {json.dumps(debug_info, ensure_ascii=False, indent=2)}")
    
    def log_performance(
        self,
        component: str,
        operation: str,
        start_time: float,
        end_time: float,
        success: bool,
        error_message: Optional[str] = None
    ):
        """성능 메트릭 로깅"""
        
        # 메트릭 객체 생성
        metric = PerformanceMetrics(
            component=component,
            operation=operation,
            start_time=start_time,
            end_time=end_time,
            success=success,
            error_message=error_message
        )
        
        # 메모리에 저장
        self.performance_metrics.append(metric)
        self._trim_memory_logs()
        
        # 파일에 로깅
        status = "성공" if success else f"실패 ({error_message})"
        log_message = (
            f"[{component}] {operation}: {status} "
            f"(소요시간: {metric.duration_ms:.2f}ms)"
        )
        
        self.performance_logger.info(log_message)
        
        # 느린 작업 경고
        if metric.duration_ms > 1000:  # 1초 이상
            self.performance_logger.warning(f"느린 작업 감지: {log_message}")
    
    def debug(self, component: str, message: str, data: Optional[Dict[str, Any]] = None):
        """디버그 로깅"""
        if not self.enable_debug:
            return
        
        log_message = f"[{component}] {message}"
        if data:
            log_message += f" - 데이터: {json.dumps(data, ensure_ascii=False)}"
        
        self.debug_logger.debug(log_message)
    
    def _trim_memory_logs(self):
        """메모리 로그 크기 제한"""
        if len(self.classification_logs) > self.max_memory_logs:
            self.classification_logs = self.classification_logs[-self.max_memory_logs:]
        
        if len(self.performance_metrics) > self.max_memory_logs:
            self.performance_metrics = self.performance_metrics[-self.max_memory_logs:]
    
    def get_classification_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """분류 통계 반환"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_logs = [
            log for log in self.classification_logs
            if log.timestamp > cutoff_time
        ]
        
        if not recent_logs:
            return {"total_classifications": 0}
        
        # 분류 결과별 통계
        result_counts = {}
        confidence_sum = 0
        processing_time_sum = 0
        
        for log in recent_logs:
            result = log.classification_result
            result_counts[result] = result_counts.get(result, 0) + 1
            confidence_sum += log.confidence
            processing_time_sum += log.processing_time_ms
        
        # 신뢰도별 분포
        confidence_ranges = {"high": 0, "medium": 0, "low": 0}
        for log in recent_logs:
            if log.confidence >= 0.7:
                confidence_ranges["high"] += 1
            elif log.confidence >= 0.4:
                confidence_ranges["medium"] += 1
            else:
                confidence_ranges["low"] += 1
        
        return {
            "total_classifications": len(recent_logs),
            "result_distribution": result_counts,
            "average_confidence": confidence_sum / len(recent_logs),
            "average_processing_time_ms": processing_time_sum / len(recent_logs),
            "confidence_distribution": confidence_ranges,
            "time_period_hours": hours
        }
    
    def get_performance_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """성능 통계 반환"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_metrics = [
            metric for metric in self.performance_metrics
            if datetime.fromtimestamp(metric.start_time) > cutoff_time
        ]
        
        if not recent_metrics:
            return {"total_operations": 0}
        
        # 컴포넌트별 통계
        component_stats = {}
        for metric in recent_metrics:
            component = metric.component
            if component not in component_stats:
                component_stats[component] = {
                    "total_operations": 0,
                    "successful_operations": 0,
                    "total_duration_ms": 0,
                    "max_duration_ms": 0,
                    "operations": {}
                }
            
            stats = component_stats[component]
            stats["total_operations"] += 1
            if metric.success:
                stats["successful_operations"] += 1
            stats["total_duration_ms"] += metric.duration_ms
            stats["max_duration_ms"] = max(stats["max_duration_ms"], metric.duration_ms)
            
            # 작업별 통계
            operation = metric.operation
            if operation not in stats["operations"]:
                stats["operations"][operation] = {"count": 0, "avg_duration_ms": 0, "success_rate": 0}
            
            op_stats = stats["operations"][operation]
            op_stats["count"] += 1
        
        # 평균 계산
        for component, stats in component_stats.items():
            if stats["total_operations"] > 0:
                stats["avg_duration_ms"] = stats["total_duration_ms"] / stats["total_operations"]
                stats["success_rate"] = stats["successful_operations"] / stats["total_operations"]
        
        return {
            "total_operations": len(recent_metrics),
            "component_statistics": component_stats,
            "time_period_hours": hours
        }
    
    def export_logs(self, output_file: str, format: str = "json") -> bool:
        """로그 내보내기"""
        try:
            output_path = Path(output_file)
            
            export_data = {
                "export_timestamp": datetime.now().isoformat(),
                "classification_logs": [log.to_dict() for log in self.classification_logs],
                "performance_metrics": [metric.to_dict() for metric in self.performance_metrics],
                "classification_statistics": self.get_classification_statistics(),
                "performance_statistics": self.get_performance_statistics()
            }
            
            if format.lower() == "json":
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, ensure_ascii=False, indent=2)
            else:
                raise ValueError(f"지원하지 않는 형식: {format}")
            
            return True
            
        except Exception as e:
            logging.error(f"로그 내보내기 실패: {e}")
            return False
    
    def clear_logs(self):
        """메모리 로그 초기화"""
        self.classification_logs.clear()
        self.performance_metrics.clear()

# 성능 측정 데코레이터
def measure_performance(component: str, operation: str):
    """성능 측정 데코레이터"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            error_message = None
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error_message = str(e)
                raise
            finally:
                end_time = time.time()
                
                # 로거가 있으면 성능 로깅
                try:
                    logger = get_project_tags_logger()
                    logger.log_performance(
                        component=component,
                        operation=operation,
                        start_time=start_time,
                        end_time=end_time,
                        success=success,
                        error_message=error_message
                    )
                except:
                    pass  # 로깅 실패해도 원본 함수 실행에는 영향 없음
        
        return wrapper
    return decorator

# 전역 로거 인스턴스
_project_tags_logger: Optional[ProjectTagsLogger] = None

def get_project_tags_logger() -> ProjectTagsLogger:
    """전역 프로젝트 태그 로거 반환"""
    global _project_tags_logger
    if _project_tags_logger is None:
        # 설정에서 디버그 모드 확인
        try:
            from config.project_tags_config import get_project_tags_config
            config = get_project_tags_config()
            enable_debug = config.enable_debug_logging
        except:
            enable_debug = False
        
        _project_tags_logger = ProjectTagsLogger(enable_debug=enable_debug)
    
    return _project_tags_logger

def log_classification_result(
    message_content: str,
    sender_name: str,
    classification_result: str,
    confidence: float,
    classification_methods: List[str],
    matched_keywords: List[str],
    processing_time_ms: float
):
    """편의 함수: 분류 결과 로깅"""
    logger = get_project_tags_logger()
    logger.log_classification(
        message_content=message_content,
        sender_name=sender_name,
        classification_result=classification_result,
        confidence=confidence,
        classification_methods=classification_methods,
        matched_keywords=matched_keywords,
        processing_time_ms=processing_time_ms
    )

if __name__ == "__main__":
    """테스트 코드"""
    
    print("=" * 60)
    print("프로젝트 태그 로깅 시스템 테스트")
    print("=" * 60)
    
    # 로거 테스트
    logger = ProjectTagsLogger(enable_debug=True)
    
    # 분류 로그 테스트
    print("분류 로그 테스트:")
    test_classifications = [
        {
            "message_content": "CareConnect 앱 UI 개선 작업 요청",
            "sender_name": "product_manager",
            "classification_result": "CareConnect",
            "confidence": 0.85,
            "classification_methods": ["keyword", "sender"],
            "matched_keywords": ["CareConnect", "UI"],
            "processing_time_ms": 15.5
        },
        {
            "message_content": "데이터베이스 성능 최적화 필요",
            "sender_name": "dba_team",
            "classification_result": "Database Optimization",
            "confidence": 0.72,
            "classification_methods": ["keyword"],
            "matched_keywords": ["데이터베이스", "최적화"],
            "processing_time_ms": 12.3
        }
    ]
    
    for i, classification in enumerate(test_classifications, 1):
        logger.log_classification(**classification)
        print(f"  {i}. {classification['classification_result']} (신뢰도: {classification['confidence']})")
    
    # 성능 로그 테스트
    print(f"\n성능 로그 테스트:")
    
    @measure_performance("test_component", "test_operation")
    def test_function():
        time.sleep(0.01)  # 10ms 대기
        return "테스트 결과"
    
    result = test_function()
    print(f"  테스트 함수 결과: {result}")
    
    # 통계 확인
    print(f"\n분류 통계:")
    classification_stats = logger.get_classification_statistics()
    print(f"  총 분류 수: {classification_stats['total_classifications']}")
    print(f"  평균 신뢰도: {classification_stats.get('average_confidence', 0):.3f}")
    print(f"  평균 처리 시간: {classification_stats.get('average_processing_time_ms', 0):.2f}ms")
    
    print(f"\n성능 통계:")
    performance_stats = logger.get_performance_statistics()
    print(f"  총 작업 수: {performance_stats['total_operations']}")
    
    # 로그 내보내기 테스트
    print(f"\n로그 내보내기 테스트:")
    export_success = logger.export_logs("test_logs_export.json")
    print(f"  내보내기 성공: {export_success}")
    
    # 파일 정리
    import os
    try:
        os.remove("test_logs_export.json")
        print("  테스트 파일 정리 완료")
    except:
        pass
    
    print("\n✅ 모든 테스트 완료")