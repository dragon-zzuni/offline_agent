# -*- coding: utf-8 -*-
"""
TODO 데이터베이스 마이그레이션 서비스

TODO 테이블 구조 변경 및 데이터 마이그레이션을 처리합니다.
"""
import sqlite3
import logging
from typing import Dict, List, Optional
from pathlib import Path

from .project_tag_service import ProjectTagService

logger = logging.getLogger(__name__)


class TodoMigrationService:
    """TODO 데이터베이스 마이그레이션 서비스"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.project_service = ProjectTagService()
    
    def migrate_database(self) -> bool:
        """데이터베이스 마이그레이션 실행"""
        try:
            # 데이터베이스 연결
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 1. project 컬럼 추가 (이미 있으면 무시)
            self._add_project_column(cursor)
            
            # 2. 기존 TODO 데이터에 프로젝트 정보 추가
            self._update_existing_todos_with_projects(cursor)
            
            conn.commit()
            conn.close()
            
            logger.info("✅ TODO 데이터베이스 마이그레이션 완료")
            return True
            
        except Exception as e:
            logger.error(f"❌ TODO 데이터베이스 마이그레이션 실패: {e}")
            return False
    
    def _add_project_column(self, cursor: sqlite3.Cursor):
        """project 컬럼 추가"""
        try:
            # 컬럼이 이미 있는지 확인
            cursor.execute("PRAGMA table_info(todos)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'project' not in columns:
                cursor.execute("ALTER TABLE todos ADD COLUMN project TEXT")
                logger.info("✅ todos 테이블에 project 컬럼 추가")
            else:
                logger.info("ℹ️ todos 테이블에 project 컬럼이 이미 존재")
                
        except Exception as e:
            logger.error(f"❌ project 컬럼 추가 실패: {e}")
    
    def _update_existing_todos_with_projects(self, cursor: sqlite3.Cursor):
        """기존 TODO 데이터에 프로젝트 정보 추가"""
        try:
            # project가 NULL인 TODO들 조회
            cursor.execute("""
                SELECT id, title, description, source_message 
                FROM todos 
                WHERE project IS NULL OR project = ''
            """)
            
            todos_to_update = cursor.fetchall()
            updated_count = 0
            
            for todo_id, title, description, source_message in todos_to_update:
                # 프로젝트 추출 시도
                project_code = self._extract_project_from_todo_data(
                    title, description, source_message
                )
                
                if project_code:
                    cursor.execute(
                        "UPDATE todos SET project = ? WHERE id = ?",
                        (project_code, todo_id)
                    )
                    updated_count += 1
            
            if updated_count > 0:
                logger.info(f"✅ {updated_count}개 TODO에 프로젝트 정보 추가")
            else:
                logger.info("ℹ️ 프로젝트 정보를 추가할 TODO가 없음")
                
        except Exception as e:
            logger.error(f"❌ 기존 TODO 프로젝트 정보 업데이트 실패: {e}")
    
    def _extract_project_from_todo_data(
        self, 
        title: Optional[str], 
        description: Optional[str], 
        source_message: Optional[str]
    ) -> Optional[str]:
        """TODO 데이터에서 프로젝트 코드 추출"""
        try:
            # source_message가 JSON 문자열인 경우 파싱
            message_data = {}
            if source_message:
                try:
                    import json
                    message_data = json.loads(source_message)
                except:
                    # JSON이 아닌 경우 텍스트로 처리
                    message_data = {"content": source_message}
            
            # 제목과 설명을 메시지 데이터에 추가
            if title:
                message_data["subject"] = title
            if description:
                if "content" in message_data:
                    message_data["content"] += f" {description}"
                else:
                    message_data["content"] = description
            
            # 프로젝트 추출
            return self.project_service.extract_project_from_message(message_data)
            
        except Exception as e:
            logger.debug(f"프로젝트 추출 실패 (TODO ID: {title}): {e}")
            return None
    
    def get_project_statistics(self) -> Dict[str, int]:
        """프로젝트별 TODO 통계 반환"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT project, COUNT(*) as count
                FROM todos 
                WHERE project IS NOT NULL AND project != ''
                GROUP BY project
                ORDER BY count DESC
            """)
            
            stats = {}
            for project, count in cursor.fetchall():
                stats[project] = count
            
            conn.close()
            return stats
            
        except Exception as e:
            logger.error(f"프로젝트 통계 조회 실패: {e}")
            return {}


def migrate_todo_database(db_path: str) -> bool:
    """TODO 데이터베이스 마이그레이션 실행"""
    migration_service = TodoMigrationService(db_path)
    return migration_service.migrate_database()


def get_project_statistics(db_path: str) -> Dict[str, int]:
    """프로젝트별 TODO 통계 반환"""
    migration_service = TodoMigrationService(db_path)
    return migration_service.get_project_statistics()