#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
비동기 프로젝트 태그 분석 서비스

새로운 TODO가 들어올 때 백그라운드에서 프로젝트 태그를 분석하고 DB에 저장합니다.
"""
import asyncio
import logging
import threading
import sqlite3
from typing import List, Dict, Optional, Callable
from queue import Queue, PriorityQueue
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ProjectTagTask:
    """프로젝트 태그 분석 작업"""
    todo_id: str
    todo_data: Dict
    callback: Optional[Callable[[str, str], None]] = None  # (todo_id, project) -> None
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


class AsyncProjectTagService:
    """비동기 프로젝트 태그 분석 서비스"""
    
    def __init__(self, project_service, repository):
        self.project_service = project_service
        self.repository = repository
        self.task_queue = PriorityQueue()  # 우선순위 큐로 변경
        self.is_running = False
        self.worker_thread = None
        self.stats = {
            "processed": 0,
            "cached": 0,
            "analyzed": 0,
            "errors": 0
        }
        self._task_counter = 0  # 같은 우선순위 내에서 순서 보장
        
        # VDOS DB와 같은 경로의 todos_cache.db 사용
        self.db_path = self._get_vdos_todos_db_path()
        logger.info(f"[AsyncProjectTag] DB 경로: {self.db_path}")
        if self.db_path:
            self._ensure_todo_table(self.db_path)
        
        # 프로젝트 태그 영구 캐시 서비스 초기화
        self.cache_service = None
        self._init_cache_service()
    
    def _get_vdos_todos_db_path(self) -> str:
        """VDOS DB와 같은 경로의 todos_cache.db 경로 반환"""
        try:
            # VDOS DB 경로 찾기
            from pathlib import Path
            import os
            
            # 여러 가능한 경로 시도
            possible_vdos_paths = [
                "../virtualoffice/src/virtualoffice/vdos.db",
                "../../virtualoffice/src/virtualoffice/vdos.db",
                "../../../virtualoffice/src/virtualoffice/vdos.db"
            ]
            
            for vdos_path in possible_vdos_paths:
                if os.path.exists(vdos_path):
                    # vdos.db와 같은 디렉토리의 todos_cache.db 경로
                    vdos_dir = os.path.dirname(os.path.abspath(vdos_path))
                    todos_db_path = os.path.join(vdos_dir, "todos_cache.db")
                    logger.info(f"[AsyncProjectTag] VDOS 디렉토리 발견: {vdos_dir}")
                    return todos_db_path
            
            # 폴백: repository에서 경로 가져오기
            if hasattr(self.repository, 'db_path'):
                return self.repository.db_path
            
            # 최종 폴백: 기본 경로
            return "../virtualoffice/src/virtualoffice/todos_cache.db"
            
        except Exception as e:
            logger.error(f"VDOS todos DB 경로 찾기 오류: {e}")
            return "../virtualoffice/src/virtualoffice/todos_cache.db"
    
    def _init_cache_service(self):
        """프로젝트 태그 영구 캐시 서비스 초기화"""
        try:
            from pathlib import Path
            import os
            
            # VDOS 디렉토리에 project_tags_cache.db 생성
            possible_vdos_paths = [
                "../virtualoffice/src/virtualoffice/vdos.db",
                "../../virtualoffice/src/virtualoffice/vdos.db",
                "../../../virtualoffice/src/virtualoffice/vdos.db"
            ]
            
            cache_db_path = None
            for vdos_path in possible_vdos_paths:
                if os.path.exists(vdos_path):
                    vdos_dir = os.path.dirname(os.path.abspath(vdos_path))
                    cache_db_path = os.path.join(vdos_dir, "project_tags_cache.db")
                    break
            
            if not cache_db_path:
                # 폴백: 현재 디렉토리
                cache_db_path = "project_tags_cache.db"
            
            from .project_tag_cache_service import ProjectTagCacheService
            self.cache_service = ProjectTagCacheService(cache_db_path)
            logger.info(f"✅ 프로젝트 태그 캐시 서비스 초기화: {cache_db_path}")
            
        except Exception as e:
            logger.error(f"❌ 프로젝트 태그 캐시 서비스 초기화 실패: {e}")
            self.cache_service = None
        
    def start(self):
        """백그라운드 워커 시작"""
        if self.is_running:
            return
            
        self.is_running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        logger.info("🚀 비동기 프로젝트 태그 서비스 시작")
    
    def stop(self):
        """백그라운드 워커 중지"""
        self.is_running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5.0)
        logger.info("⏹️ 비동기 프로젝트 태그 서비스 중지")
    
    def queue_todo_for_analysis(self, todo_id: str, todo_data: Dict, callback: Optional[Callable] = None, priority: bool = False):
        """TODO를 프로젝트 태그 분석 큐에 추가
        
        Args:
            todo_id: TODO ID
            todo_data: TODO 데이터
            callback: 완료 콜백
            priority: True면 큐의 앞에 추가 (현재 페르소나 우선)
        """
        if not self.is_running:
            self.start()
        
        # 이미 프로젝트 태그가 있으면 스킵
        if todo_data.get("project"):
            logger.debug(f"[AsyncProjectTag] {todo_id}: 이미 프로젝트 태그 존재 - 스킵")
            return
        
        # 원본 메시지 ID를 캐시 키로 사용
        source_message = todo_data.get("source_message")
        if source_message:
            # source_message가 딕셔너리면 id 추출, 문자열이면 그대로 사용
            if isinstance(source_message, dict):
                cache_key = source_message.get("id", todo_id)
            elif isinstance(source_message, str):
                # JSON 문자열이면 파싱 시도
                try:
                    import json
                    msg_dict = json.loads(source_message)
                    cache_key = msg_dict.get("id", todo_id)
                except:
                    cache_key = source_message
            else:
                cache_key = todo_id
        else:
            cache_key = todo_id
        
        # 영구 캐시에서 먼저 확인
        if self.cache_service:
            cached = self.cache_service.get_cached_tag(cache_key)
            if cached and cached.get('project_tag'):
                cached_project = cached['project_tag']
                logger.info(f"[AsyncProjectTag] {todo_id}: 영구 캐시 히트 - {cached_project} (키: {cache_key})")
                todo_data["project"] = cached_project
                self.stats["cached"] += 1
                if callback:
                    callback(todo_id, cached_project)
                return
        
        # DB에서 캐시된 프로젝트 태그 확인
        cached_project = self._get_cached_project(todo_id)
        if cached_project:
            logger.debug(f"[AsyncProjectTag] {todo_id}: DB 캐시 히트 - {cached_project}")
            todo_data["project"] = cached_project
            self.stats["cached"] += 1
            if callback:
                callback(todo_id, cached_project)
            return
        
        # 분석 큐에 추가 (우선순위: 0=높음, 1=낮음)
        task = ProjectTagTask(todo_id, todo_data, callback)
        priority_value = 0 if priority else 1
        self._task_counter += 1
        # (우선순위, 카운터, 태스크) 튜플로 저장
        self.task_queue.put((priority_value, self._task_counter, task))
        priority_label = "우선" if priority else "일반"
        logger.debug(f"[AsyncProjectTag] {todo_id}: 분석 큐에 추가 ({priority_label}, 큐 크기: {self.task_queue.qsize()})")
    
    def queue_multiple_todos(self, todos: List[Dict], callback: Optional[Callable] = None):
        """여러 TODO를 배치로 큐에 추가"""
        for todo in todos:
            todo_id = todo.get("id")
            if todo_id:
                self.queue_todo_for_analysis(todo_id, todo, callback)
    
    def _get_cached_project(self, todo_id: str) -> Optional[str]:
        """DB에서 캐시된 프로젝트 태그 조회 (스레드 안전)"""
        try:
            # 1. 영구 캐시에서 먼저 확인
            if self.cache_service:
                cached = self.cache_service.get_cached_tag(todo_id)
                if cached and cached.get('project_tag'):
                    logger.debug(f"[AsyncProjectTag] {todo_id}: 영구 캐시 히트 - {cached['project_tag']}")
                    return cached['project_tag']
            
            # 2. todos_cache.db에서 확인 (컬럼명: project_tag)
            if hasattr(self.repository, 'db_path'):
                import sqlite3
                conn = sqlite3.connect(self.repository.db_path)
                cur = conn.cursor()
                
                cur.execute("SELECT project_tag FROM todos WHERE id = ? AND project_tag IS NOT NULL AND project_tag != ''", (todo_id,))
                result = cur.fetchone()
                conn.close()
                
                if result and result[0]:
                    project = result[0].strip()
                    # 영구 캐시에도 저장
                    if self.cache_service and project:
                        self.cache_service.save_tag(todo_id, project, confidence='db_cache')
                    return project
            else:
                # 폴백: 기존 repository 사용 (메인 스레드에서만)
                if self.repository:
                    project = self.repository.get_project(todo_id)
                    if project and project.strip():
                        project = project.strip()
                        # 영구 캐시에도 저장
                        if self.cache_service:
                            self.cache_service.save_tag(todo_id, project, confidence='db_cache')
                        return project
                    
        except Exception as e:
            logger.debug(f"캐시된 프로젝트 태그 조회 오류: {e}")
        return None
    
    def _worker_loop(self):
        """백그라운드 워커 루프"""
        logger.info("🔄 프로젝트 태그 분석 워커 시작")
        
        while self.is_running:
            try:
                # 큐에서 작업 가져오기 (타임아웃 1초)
                try:
                    priority, counter, task = self.task_queue.get(timeout=1.0)
                except:
                    continue  # 타임아웃 시 계속 루프
                
                # 프로젝트 태그 분석
                self._process_task(task)
                self.task_queue.task_done()
                
            except Exception as e:
                logger.error(f"프로젝트 태그 워커 오류: {e}")
                self.stats["errors"] += 1
        
        logger.info("⏹️ 프로젝트 태그 분석 워커 종료")
    
    def _process_task(self, task: ProjectTagTask):
        """프로젝트 태그 분석 작업 처리"""
        try:
            todo_id = task.todo_id
            todo_data = task.todo_data
            
            logger.debug(f"[AsyncProjectTag] {todo_id}: 프로젝트 태그 분석 시작")
            
            # 프로젝트 태그 추출
            project = self._extract_project_tag(todo_data)
            
            if project:
                # TODO 데이터에 프로젝트 태그 설정
                todo_data["project"] = project
                
                # DB에 캐시 저장 (스레드 안전성을 위해 직접 DB 연결)
                self._save_project_to_db_thread_safe(todo_id, project)
                
                logger.info(f"[AsyncProjectTag] ✅ {todo_id}: {project}")
                self.stats["analyzed"] += 1
                
                # 영구 캐시에 저장 (원본 메시지 ID를 키로 사용)
                if self.cache_service:
                    source_message = todo_data.get("source_message")
                    if source_message:
                        if isinstance(source_message, dict):
                            cache_key = source_message.get("id", todo_id)
                        elif isinstance(source_message, str):
                            try:
                                import json
                                msg_dict = json.loads(source_message)
                                cache_key = msg_dict.get("id", todo_id)
                            except:
                                cache_key = source_message
                        else:
                            cache_key = todo_id
                    else:
                        cache_key = todo_id
                    
                    self.cache_service.save_tag(cache_key, project, confidence='llm', analysis_method='async')
                    logger.debug(f"[AsyncProjectTag] 영구 캐시 저장: {cache_key} → {project}")
                
                # 콜백 호출
                if task.callback:
                    task.callback(todo_id, project)
            else:
                logger.debug(f"[AsyncProjectTag] {todo_id}: 프로젝트 태그 추출 실패")
            
            self.stats["processed"] += 1
            
        except Exception as e:
            logger.error(f"프로젝트 태그 분석 오류 ({task.todo_id}): {e}")
            self.stats["errors"] += 1
    
    def _save_project_to_db_thread_safe(self, todo_id: str, project: str):
        """스레드 안전한 방식으로 프로젝트 태그를 DB에 저장 (todos_cache.db + 캐시 DB)"""
        from datetime import datetime
        import os
        
        # 1. todos_cache.db에 저장
        try:
            conn = sqlite3.connect(self.db_path)
            self._ensure_todo_table(self.db_path, connection=conn)
            cur = conn.cursor()
            
            # 프로젝트 태그 업데이트 (컬럼명: project_tag)
            cur.execute(
                "UPDATE todos SET project_tag = ?, updated_at = datetime('now') WHERE id = ?",
                (project, todo_id)
            )
            conn.commit()
            conn.close()
            
            logger.debug(f"[AsyncProjectTag] todos_cache.db 저장 완료: {todo_id} → {project}")
        except Exception as e:
            logger.error(f"[AsyncProjectTag] todos_cache.db 저장 오류 ({todo_id}): {e}")
        
        # 2. 프로젝트 태그 캐시 DB에도 저장
        try:
            if hasattr(self.project_service, 'tag_cache') and self.project_service.tag_cache:
                cache_db_path = self.project_service.tag_cache.db_path
                
                # 디렉토리 존재 확인 및 생성
                cache_dir = os.path.dirname(cache_db_path)
                if cache_dir and not os.path.exists(cache_dir):
                    os.makedirs(cache_dir, exist_ok=True)
                    logger.info(f"[AsyncProjectTag] 캐시 디렉토리 생성: {cache_dir}")
                
                # 캐시 DB 연결 및 저장
                conn = sqlite3.connect(cache_db_path)
                cur = conn.cursor()
                
                # 테이블 존재 확인 (처음 생성 시)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS project_tag_cache (
                        todo_id TEXT PRIMARY KEY,
                        project_tag TEXT NOT NULL,
                        confidence TEXT,
                        analysis_method TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                """)
                
                now = datetime.now().isoformat()
                cur.execute("""
                    INSERT OR REPLACE INTO project_tag_cache 
                    (todo_id, project_tag, confidence, analysis_method, created_at, updated_at)
                    VALUES (?, ?, ?, ?, 
                        COALESCE((SELECT created_at FROM project_tag_cache WHERE todo_id = ?), ?),
                        ?)
                """, (todo_id, project, 'llm', 'async_analysis', todo_id, now, now))
                
                conn.commit()
                conn.close()
                
                logger.debug(f"[AsyncProjectTag] 캐시 DB 저장 완료: {todo_id} → {project}")
        except Exception as e:
            logger.error(f"[AsyncProjectTag] 캐시 DB 저장 오류 ({todo_id}): {e}")
    
    def _extract_project_tag(self, todo_data: Dict) -> Optional[str]:
        """TODO 데이터에서 프로젝트 태그 추출"""
        try:
            # TODO 데이터에서 직접 정보 추출
            title = todo_data.get("title", "")
            description = todo_data.get("description", "")
            requester = todo_data.get("requester", "")
            
            # 소스 메시지도 참고 (있으면)
            source_message = todo_data.get("source_message", "")
            sender = ""
            subject = title
            
            if source_message:
                import json
                try:
                    if source_message.startswith("{"):
                        msg_data = json.loads(source_message)
                        sender = msg_data.get("sender", requester)
                        subject = msg_data.get("subject", title)
                except:
                    pass
            
            # 제목과 설명을 합쳐서 더 많은 컨텍스트 제공
            full_content = f"{title}\n\n{description}" if description else title
            
            # 메시지 데이터 구성
            message = {
                "content": full_content,
                "subject": subject,
                "sender": sender or requester,
            }
            
            logger.debug(f"[AsyncProjectTag] 분석할 메시지: 제목={subject}, 발신자={sender or requester}")
            
            # 프로젝트 서비스로 추출
            if self.project_service:
                return self.project_service.extract_project_from_message(message, use_cache=False)
            
            return None
            
        except Exception as e:
            logger.debug(f"프로젝트 태그 추출 오류: {e}")
            return None
    
    def get_stats(self) -> Dict:
        """통계 정보 반환"""
        return {
            **self.stats,
            "queue_size": self.task_queue.qsize(),
            "is_running": self.is_running
        }
    
    def clear_queue(self):
        """큐 비우기"""
        while not self.task_queue.empty():
            try:
                self.task_queue.get_nowait()
                self.task_queue.task_done()
            except:
                break
        logger.info("🧹 프로젝트 태그 분석 큐 비움")

    def _ensure_todo_table(self, db_path: str, connection: Optional[sqlite3.Connection] = None) -> None:
        """필요 시 todos 테이블 생성 (다른 스레드에서도 사용)."""
        conn_provided = connection is not None
        conn = connection or sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS todos (
                id TEXT PRIMARY KEY,
                title TEXT,
                description TEXT,
                priority TEXT,
                deadline TEXT,
                deadline_ts TEXT,
                requester TEXT,
                type TEXT,
                status TEXT DEFAULT 'pending',
                source_message TEXT,
                created_at TEXT,
                updated_at TEXT,
                snooze_until TEXT,
                is_top3 INTEGER DEFAULT 0,
                draft_subject TEXT,
                draft_body TEXT,
                evidence TEXT,
                project_tag TEXT DEFAULT '미분류',
                deadline_confidence TEXT,
                recipient_type TEXT DEFAULT 'to',
                source_type TEXT DEFAULT '메시지',
                persona_name TEXT,
                project_full_name TEXT
            )
            """
        )
        conn.commit()
        if not conn_provided:
            conn.close()


# 전역 인스턴스 (싱글톤 패턴)
_async_project_tag_service = None


def get_async_project_tag_service(project_service=None, repository=None):
    """비동기 프로젝트 태그 서비스 싱글톤 인스턴스 반환"""
    global _async_project_tag_service
    
    if _async_project_tag_service is None and project_service and repository:
        _async_project_tag_service = AsyncProjectTagService(project_service, repository)
    
    return _async_project_tag_service
