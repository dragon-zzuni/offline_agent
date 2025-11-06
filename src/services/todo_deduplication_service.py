"""
TODO 중복 제거 서비스

한 메시지에서 여러 유형의 TODO가 생성되는 것을 방지하고,
기존 중복 TODO를 정리합니다.
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class TodoDeduplicationService:
    """TODO 중복 제거 서비스"""
    
    # 유형 우선순위 (높을수록 중요)
    TYPE_PRIORITY = {
        "deadline": 6,
        "meeting": 5,
        "task": 4,
        "review": 3,
        "documentation": 2,
        "issue": 1,
    }
    
    def __init__(self):
        """초기화"""
        # 메모리 캐시: source_message → todo_id 매핑
        self._source_message_cache: Dict[str, str] = {}
        
        # 통계
        self._stats = {
            "checked": 0,
            "duplicates_prevented": 0,
            "duplicates_removed": 0,
            "todos_kept": 0,
        }
        
        logger.info("TodoDeduplicationService 초기화 완료")
    
    def should_create_todo(
        self, 
        source_message: str, 
        todo_type: str,
        repository=None
    ) -> Tuple[bool, Optional[str]]:
        """
        TODO 생성 여부 결정
        
        Args:
            source_message: 원본 메시지 ID
            todo_type: TODO 유형
            repository: TODO 저장소 (DB 조회용)
            
        Returns:
            (생성 여부, 기존 TODO ID)
        """
        self._stats["checked"] += 1
        
        # 1. 메모리 캐시 확인
        if source_message in self._source_message_cache:
            existing_todo_id = self._source_message_cache[source_message]
            logger.debug(
                f"중복 감지 (캐시): source_message={source_message}, "
                f"existing_todo={existing_todo_id}"
            )
            self._stats["duplicates_prevented"] += 1
            return False, existing_todo_id
        
        # 2. DB 조회 (캐시 미스 시)
        if repository:
            existing_todo = repository.find_by_source_message(source_message)
            if existing_todo:
                # 캐시에 추가
                self._source_message_cache[source_message] = existing_todo["id"]
                logger.debug(
                    f"중복 감지 (DB): source_message={source_message}, "
                    f"existing_todo={existing_todo['id']}"
                )
                self._stats["duplicates_prevented"] += 1
                return False, existing_todo["id"]
        
        # 3. 중복 없음 - 생성 가능
        return True, None
    
    def select_best_type(self, todos: List[Dict]) -> Dict:
        """
        같은 메시지의 여러 TODO 중 최선 선택
        
        Args:
            todos: 같은 source_message를 가진 TODO 리스트
            
        Returns:
            선택된 TODO
        """
        if not todos:
            raise ValueError("TODO 리스트가 비어있습니다")
        
        if len(todos) == 1:
            return todos[0]
        
        # 우선순위로 정렬 (높은 것부터)
        sorted_todos = sorted(
            todos,
            key=lambda t: (
                self.TYPE_PRIORITY.get(t.get("type", "task"), 0),
                t.get("created_at", "")  # 같은 우선순위면 최신 것
            ),
            reverse=True
        )
        
        best_todo = sorted_todos[0]
        logger.debug(
            f"최선 TODO 선택: type={best_todo.get('type')}, "
            f"id={best_todo.get('id')}, "
            f"후보 {len(todos)}개 중"
        )
        
        return best_todo
    
    def cleanup_duplicates(self, repository) -> Dict[str, int]:
        """
        DB에서 중복 TODO 제거
        
        Args:
            repository: TODO 저장소
            
        Returns:
            통계 정보 (removed, kept)
        """
        logger.info("중복 TODO 정리 시작...")
        
        # 1. 같은 source_message를 가진 TODO 그룹 조회
        duplicate_groups = repository.find_duplicate_groups()
        
        if not duplicate_groups:
            logger.info("중복 TODO 없음")
            return {"removed": 0, "kept": 0}
        
        removed_count = 0
        kept_count = 0
        
        # 2. 각 그룹에서 최선 TODO 선택 및 나머지 삭제
        for source_message, todos in duplicate_groups.items():
            if len(todos) <= 1:
                continue
            
            # 최선 TODO 선택
            best_todo = self.select_best_type(todos)
            
            # 나머지 삭제
            for todo in todos:
                if todo["id"] != best_todo["id"]:
                    logger.info(
                        f"중복 TODO 삭제: id={todo['id']}, "
                        f"type={todo.get('type')}, "
                        f"title={todo.get('title', '')[:50]}"
                    )
                    repository.delete_todo(todo["id"])
                    removed_count += 1
                else:
                    kept_count += 1
            
            # 캐시 업데이트
            self._source_message_cache[source_message] = best_todo["id"]
        
        self._stats["duplicates_removed"] = removed_count
        self._stats["todos_kept"] = kept_count
        
        logger.info(
            f"중복 TODO 정리 완료: "
            f"제거={removed_count}, 유지={kept_count}"
        )
        
        return {
            "removed": removed_count,
            "kept": kept_count
        }
    
    def register_todo(self, source_message: str, todo_id: str):
        """
        TODO 생성 후 캐시에 등록
        
        Args:
            source_message: 원본 메시지 ID
            todo_id: 생성된 TODO ID
        """
        self._source_message_cache[source_message] = todo_id
        logger.debug(f"TODO 캐시 등록: {source_message} → {todo_id}")
    
    def get_deduplication_stats(self) -> Dict[str, int]:
        """
        중복 제거 통계 반환
        
        Returns:
            통계 정보
        """
        return self._stats.copy()
    
    def clear_cache(self):
        """캐시 초기화"""
        self._source_message_cache.clear()
        logger.debug("중복 제거 캐시 초기화")
