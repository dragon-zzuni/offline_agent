#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
프로젝트 태그 영구 캐시 서비스
TODO ID별 프로젝트 태그를 별도 DB에 저장하여 재분석 방지
"""

import sqlite3
import logging
import os
from typing import Optional, Dict
from datetime import datetime

logger = logging.getLogger(__name__)


class ProjectTagCacheService:
    """프로젝트 태그 영구 캐시 관리"""
    
    def __init__(self, db_path: str):
        """
        Args:
            db_path: 캐시 DB 파일 경로 (예: project_tags_cache.db)
        """
        self.db_path = db_path
        self._init_database()
        logger.info(f"✅ 프로젝트 태그 캐시 초기화: {db_path}")
    
    def _init_database(self):
        """캐시 데이터베이스 초기화"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 프로젝트 태그 캐시 테이블 생성
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS project_tag_cache (
                    todo_id TEXT PRIMARY KEY,
                    project_tag TEXT NOT NULL,
                    confidence TEXT,
                    analysis_method TEXT,
                    classification_reason TEXT,
                    project_full_name TEXT,
                    evidence TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            self._ensure_columns(cursor)
            self._backfill_project_full_names(cursor)
            self._sync_evidence_column(cursor)
            
            # 인덱스 생성
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_project_tag 
                ON project_tag_cache(project_tag)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_updated_at 
                ON project_tag_cache(updated_at)
            """)
            
            conn.commit()
            conn.close()
            
            logger.info("✅ 프로젝트 태그 캐시 테이블 초기화 완료")
            
        except Exception as e:
            logger.error(f"❌ 캐시 DB 초기화 실패: {e}")
    
    def _ensure_columns(self, cursor: sqlite3.Cursor) -> None:
        """기존 DB에 누락된 컬럼이 있으면 추가"""
        cursor.execute("PRAGMA table_info(project_tag_cache)")
        existing = {row[1] for row in cursor.fetchall()}
        for column, definition in (
            ("classification_reason", "TEXT"),
            ("project_full_name", "TEXT"),
            ("evidence", "TEXT"),
        ):
            if column not in existing:
                cursor.execute(f"ALTER TABLE project_tag_cache ADD COLUMN {column} {definition}")

    def _backfill_project_full_names(self, cursor: sqlite3.Cursor) -> None:
        """기존 레코드에 프로젝트 풀네임을 채운다."""
        try:
            cursor.execute("""
                SELECT todo_id, project_tag
                  FROM project_tag_cache
                 WHERE (project_full_name IS NULL OR project_full_name = '')
                   AND project_tag IS NOT NULL
            """)
            rows = cursor.fetchall()
            if not rows:
                return

            try:
                from src.utils.project_fullname_mapper import get_project_fullname
            except Exception:  # pragma: no cover - mapper 사용 불가 시 건너뜀
                return

            for todo_id, project_code in rows:
                full_name = get_project_fullname(project_code)
                if full_name:
                    cursor.execute(
                        "UPDATE project_tag_cache SET project_full_name = ? WHERE todo_id = ?",
                        (full_name, todo_id),
                    )
        except Exception as exc:  # pragma: no cover - 백필 실패는 치명적이지 않음
            logger.debug("프로젝트 풀네임 백필 실패: %s", exc)

    def _sync_evidence_column(self, cursor: sqlite3.Cursor) -> None:
        """evidence 컬럼이 비어 있는 경우 classification_reason으로 채운다."""
        try:
            cursor.execute("""
                UPDATE project_tag_cache
                   SET evidence = classification_reason
                 WHERE (evidence IS NULL OR TRIM(evidence) = '')
            """)
        except Exception as exc:  # pragma: no cover
            logger.debug("evidence 컬럼 동기화 실패: %s", exc)

    def _resolve_project_full_name(self, project_code: Optional[str]) -> Optional[str]:
        """프로젝트 코드 기준으로 풀네임을 찾는다."""
        if not project_code:
            return None
        try:
            from src.utils.project_fullname_mapper import get_project_fullname

            return get_project_fullname(project_code)
        except Exception:
            return None

    def get_cached_tag(self, todo_id: str) -> Optional[Dict[str, str]]:
        """
        캐시에서 프로젝트 태그 조회
        
        Args:
            todo_id: TODO ID
            
        Returns:
            캐시된 태그 정보 또는 None
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT project_tag, confidence, analysis_method,
                       classification_reason, project_full_name, evidence,
                       created_at, updated_at
                FROM project_tag_cache
                WHERE todo_id = ?
            """, (todo_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    'project_tag': result[0],
                    'confidence': result[1],
                    'analysis_method': result[2],
                    'classification_reason': result[3],
                    'project_full_name': result[4],
                    'evidence': result[5],
                    'created_at': result[6],
                    'updated_at': result[7]
                }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ 캐시 조회 실패 ({todo_id}): {e}")
            return None
    
    def save_tag(self, todo_id: str, project_tag: str, 
                 confidence: str = None, analysis_method: str = None,
                 classification_reason: str = None,
                 project_full_name: Optional[str] = None,
                 evidence: Optional[str] = None):
        """
        프로젝트 태그를 캐시에 저장
        
        Args:
            todo_id: TODO ID
            project_tag: 프로젝트 태그
            confidence: 신뢰도 (explicit, llm, sender, unknown)
            analysis_method: 분석 방법
            classification_reason: 분류 근거 (짧은 설명)
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            now = datetime.now().isoformat()
            resolved_full_name = project_full_name or self._resolve_project_full_name(project_tag)
            evidence_text = evidence if evidence is not None else classification_reason
            
            cursor.execute("""
                INSERT OR REPLACE INTO project_tag_cache 
                (todo_id, project_tag, confidence, analysis_method,
                 classification_reason, project_full_name, evidence,
                 created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 
                    COALESCE((SELECT created_at FROM project_tag_cache WHERE todo_id = ?), ?),
                    ?)
            """, (
                todo_id,
                project_tag,
                confidence,
                analysis_method,
                classification_reason,
                resolved_full_name,
                evidence_text,
                todo_id,
                now,
                now,
            ))
            
            conn.commit()
            conn.close()
            
            # 로그에 분류 근거 포함
            if classification_reason:
                logger.info(f"✅ 캐시 저장: {todo_id} → {project_tag} ({classification_reason})")
            else:
                logger.debug(f"✅ 캐시 저장: {todo_id} → {project_tag}")
            
        except Exception as e:
            logger.error(f"❌ 캐시 저장 실패 ({todo_id}): {e}")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """캐시 통계 조회"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 전체 캐시 개수
            cursor.execute("SELECT COUNT(*) FROM project_tag_cache")
            total = cursor.fetchone()[0]
            
            # 프로젝트별 개수
            cursor.execute("""
                SELECT project_tag, COUNT(*) 
                FROM project_tag_cache 
                GROUP BY project_tag
            """)
            by_project = dict(cursor.fetchall())
            
            conn.close()
            
            return {
                'total': total,
                'by_project': by_project
            }
            
        except Exception as e:
            logger.error(f"❌ 캐시 통계 조회 실패: {e}")
            return {'total': 0, 'by_project': {}}
    
    def clear_cache(self, older_than_days: int = None):
        """
        캐시 정리
        
        Args:
            older_than_days: 지정된 일수보다 오래된 캐시만 삭제 (None이면 전체 삭제)
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if older_than_days:
                from datetime import timedelta
                cutoff_date = (datetime.now() - timedelta(days=older_than_days)).isoformat()
                cursor.execute("""
                    DELETE FROM project_tag_cache 
                    WHERE updated_at < ?
                """, (cutoff_date,))
                deleted = cursor.rowcount
                logger.info(f"🗑️ {older_than_days}일 이상 된 캐시 {deleted}개 삭제")
            else:
                cursor.execute("DELETE FROM project_tag_cache")
                deleted = cursor.rowcount
                logger.info(f"🗑️ 전체 캐시 {deleted}개 삭제")
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ 캐시 정리 실패: {e}")
