# -*- coding: utf-8 -*-
"""
Todo 저장소 모듈

TodoPanel과 같은 UI 계층이 직접 sqlite3에 접근하지 않도록 캡슐화합니다.
"""
from __future__ import annotations

import json
import logging
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator, Iterable, List, Optional

# offline_agent/src 기준에서 virtualoffice/todos_cache.db로 맞춤
OFFLINE_AGENT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB_PATH = (
    OFFLINE_AGENT_ROOT.parent / "virtualoffice" / "src" / "virtualoffice" / "todos_cache.db"
)
VDOS_DB_PATH = (
    OFFLINE_AGENT_ROOT.parent / "virtualoffice" / "src" / "virtualoffice" / "vdos.db"
)

logger = logging.getLogger(__name__)


class TodoRepository:
    """SQLite 기반 TODO 저장소."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = Path(db_path or DEFAULT_DB_PATH)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._init_db()
        self._backfill_missing_source_dates()

    # ------------------------------------------------------------------ #
    # 내부 유틸
    # ------------------------------------------------------------------ #
    def _init_db(self) -> None:
        cur = self._conn.cursor()
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
        self._ensure_column(cur, "recipient_type", "TEXT DEFAULT 'to'")
        self._ensure_column(cur, "source_type", "TEXT DEFAULT '메시지'")
        self._ensure_column(cur, "persona_name", "TEXT")
        self._ensure_column(cur, "project_tag", "TEXT DEFAULT '미분류'")
        self._ensure_column(cur, "project_full_name", "TEXT")
        self._conn.commit()

    def _ensure_column(self, cur: sqlite3.Cursor, name: str, definition: str) -> None:
        try:
            cur.execute(f"ALTER TABLE todos ADD COLUMN {name} {definition}")
        except sqlite3.OperationalError:
            # 이미 존재하는 경우는 무시
            pass

    def _backfill_missing_source_dates(self) -> None:
        """source_message에 date가 없는 레거시 TODO를 VDOS DB 기반으로 보정."""
        if not VDOS_DB_PATH.exists():
            return

        cur = self._conn.cursor()
        cur.execute(
            """
            SELECT id, source_message
              FROM todos
             WHERE source_message IS NOT NULL
               AND source_message != ''
               AND source_message NOT LIKE '%"date":%'
            """
        )
        rows = cur.fetchall()
        if not rows:
            return

        try:
            vdos_conn = sqlite3.connect(str(VDOS_DB_PATH))
            vdos_conn.row_factory = sqlite3.Row
        except sqlite3.Error as exc:  # pragma: no cover - 로컬 환경 문제
            logger.warning("VDOS DB 연결 실패로 수신 시간 보정을 건너뜁니다: %s", exc)
            return

        updated = 0
        with self._transaction() as todo_cur:
            for row in rows:
                todo_id = row["id"]
                raw_src = row["source_message"]
                try:
                    src = json.loads(raw_src)
                except Exception:
                    continue

                timestamp = self._lookup_original_timestamp(src, vdos_conn)
                if not timestamp:
                    continue

                metadata = src.get("metadata") or {}
                metadata.setdefault("original_date", timestamp)
                src["metadata"] = metadata
                if "date" not in src:
                    src["date"] = timestamp

                new_payload = json.dumps(src, ensure_ascii=False)
                todo_cur.execute(
                    "UPDATE todos SET source_message = ? WHERE id = ?",
                    (new_payload, todo_id),
                )
                updated += 1

        vdos_conn.close()
        if updated:
            logger.info("🔄 source_message 누락 수신 시간 %d건 보정 완료", updated)

    def _lookup_original_timestamp(
        self, source_msg: dict, vdos_conn: sqlite3.Connection
    ) -> Optional[str]:
        """VDOS DB에서 원본 메시지의 sent_at을 조회."""
        if not source_msg:
            return None

        metadata = source_msg.get("metadata") or {}
        msg_id = source_msg.get("id") or ""
        platform = (source_msg.get("platform") or "").lower()

        # 이메일: email_id 우선, 없으면 msg_id에서 추출
        if platform == "email" or msg_id.startswith("email_"):
            email_id = metadata.get("email_id")
            if not email_id and msg_id:
                match = re.search(r"email_(\d+)", msg_id)
                if match:
                    email_id = int(match.group(1))
            if not email_id:
                return None
            cur = vdos_conn.execute("SELECT sent_at FROM emails WHERE id = ?", (email_id,))
            row = cur.fetchone()
            if row and row["sent_at"]:
                return self._to_utc_iso(row["sent_at"])
            return None

        # 채팅: chat_id 우선, 없으면 msg_id 마지막 숫자 사용
        chat_id = metadata.get("chat_id")
        if not chat_id and msg_id:
            match = re.search(r"_(\d+)$", msg_id)
            if match:
                chat_id = int(match.group(1))
        if not chat_id:
            return None

        cur = vdos_conn.execute("SELECT sent_at FROM chat_messages WHERE id = ?", (chat_id,))
        row = cur.fetchone()
        if row and row["sent_at"]:
            return self._to_utc_iso(row["sent_at"])
        return None

    @staticmethod
    def _to_utc_iso(value: str) -> Optional[str]:
        """sent_at 문자열을 UTC ISO-8601 형식으로 변환."""
        if not value:
            return None

        normalized = value.strip().replace(" ", "T")
        if normalized.endswith("Z"):
            normalized = normalized[:-1] + "+00:00"

        try:
            dt = datetime.fromisoformat(normalized)
        except ValueError:
            return normalized

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt.isoformat()

    @contextmanager
    def _transaction(self) -> Generator[sqlite3.Cursor, None, None]:
        cur = self._conn.cursor()
        cur.execute("BEGIN IMMEDIATE")
        try:
            yield cur
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise

    # ------------------------------------------------------------------ #
    # 공개 API
    # ------------------------------------------------------------------ #
    def cleanup_old_rows(self, days: int) -> None:
        with self._transaction() as cur:
            cur.execute(
                """
                DELETE FROM todos
                WHERE created_at IS NOT NULL
                  AND created_at <> ''
                  AND datetime(replace(substr(created_at,1,19),'T',' '))
                        < datetime('now', ? , 'localtime')
                """,
                (f"-{days} days",),
            )

    def release_snoozed(self) -> None:
        now = datetime.now().isoformat()
        with self._transaction() as cur:
            cur.execute(
                """
                UPDATE todos
                   SET status='pending', updated_at=?
                 WHERE status='snoozed'
                   AND snooze_until IS NOT NULL
                   AND snooze_until <= ?
                """,
                (now, now),
            )

    def delete_all(self) -> None:
        with self._transaction() as cur:
            cur.execute("DELETE FROM todos")

    def save_all(self, rows: Iterable[dict]) -> None:
        rows = list(rows)
        with self._transaction() as cur:
            cur.execute("DELETE FROM todos")
            for row in rows:
                source_msg = row.get("source_message", {})
                if isinstance(source_msg, dict):
                    source_msg_str = json.dumps(source_msg, ensure_ascii=False)
                else:
                    source_msg_str = source_msg or "{}"

                # 프로젝트 풀네임 가져오기
                from src.utils.project_fullname_mapper import get_project_fullname
                project_code = row.get("project", "")
                project_fullname = get_project_fullname(project_code) if project_code else None
                
                cur.execute(
                    """
                    INSERT OR REPLACE INTO todos (
                        id, title, description, priority, deadline, deadline_ts,
                        requester, type, status, source_message, created_at, updated_at,
                        snooze_until, is_top3, draft_subject, draft_body, evidence,
                        deadline_confidence, recipient_type, source_type, project_tag, persona_name, project_full_name
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row.get("id"),
                        row.get("title", ""),
                        row.get("description", ""),
                        row.get("priority", "low"),
                        row.get("deadline"),
                        row.get("deadline_ts"),
                        row.get("requester", ""),
                        row.get("type", ""),
                        row.get("status", "pending"),
                        source_msg_str,
                        row.get("created_at"),
                        row.get("updated_at"),
                        row.get("snooze_until"),
                        row.get("is_top3", 0),
                        row.get("draft_subject", ""),
                        row.get("draft_body", ""),
                        row.get("evidence", "[]"),
                        row.get("deadline_confidence", "mid"),
                        row.get("recipient_type", "to"),
                        row.get("source_type", "메시지"),
                        row.get("project"),
                        row.get("persona_name"),
                        project_fullname,
                    ),
                )

    def upsert_todos(self, rows: Iterable[dict]) -> dict:
        """TODO를 증분 업데이트 (기존 TODO 유지, 새로운 TODO만 추가/업데이트)
        
        Args:
            rows: TODO 딕셔너리 리스트
            
        Returns:
            dict: 업데이트 통계 {'added': int, 'updated': int, 'unchanged': int}
        """
        rows = list(rows)
        stats = {'added': 0, 'updated': 0, 'unchanged': 0}
        
        with self._transaction() as cur:
            # 기존 TODO ID 목록 조회
            cur.execute("SELECT id, updated_at FROM todos")
            existing_todos = {row[0]: row[1] for row in cur.fetchall()}
            
            for row in rows:
                todo_id = row.get("id")
                updated_at = row.get("updated_at")
                
                source_msg = row.get("source_message", {})
                if isinstance(source_msg, dict):
                    source_msg_str = json.dumps(source_msg, ensure_ascii=False)
                else:
                    source_msg_str = source_msg or "{}"
                
                # 새로운 TODO인지 확인
                if todo_id not in existing_todos:
                    # 프로젝트 풀네임 가져오기
                    from src.utils.project_fullname_mapper import get_project_fullname
                    project_code = row.get("project", "")
                    project_fullname = get_project_fullname(project_code) if project_code else None
                    
                    # 새로운 TODO 추가
                    cur.execute(
                        """
                        INSERT INTO todos (
                            id, title, description, priority, deadline, deadline_ts,
                            requester, type, status, source_message, created_at, updated_at,
                            snooze_until, is_top3, draft_subject, draft_body, evidence,
                            deadline_confidence, recipient_type, source_type, project_tag, persona_name, project_full_name
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            todo_id,
                            row.get("title", ""),
                            row.get("description", ""),
                            row.get("priority", "low"),
                            row.get("deadline"),
                            row.get("deadline_ts"),
                            row.get("requester", ""),
                            row.get("type", ""),
                            row.get("status", "pending"),
                            source_msg_str,
                            row.get("created_at"),
                            updated_at,
                            row.get("snooze_until"),
                            row.get("is_top3", 0),
                            row.get("draft_subject", ""),
                            row.get("draft_body", ""),
                            row.get("evidence", "[]"),
                            row.get("deadline_confidence", "mid"),
                            row.get("recipient_type", "to"),
                            row.get("source_type", "메시지"),
                            row.get("project"),
                            row.get("persona_name"),
                            project_fullname,
                        ),
                    )
                    stats['added'] += 1
                elif existing_todos[todo_id] != updated_at:
                    # 프로젝트 풀네임 가져오기
                    from src.utils.project_fullname_mapper import get_project_fullname
                    project_code = row.get("project", "")
                    project_fullname = get_project_fullname(project_code) if project_code else None
                    
                    # 업데이트된 TODO 수정
                    cur.execute(
                        """
                        UPDATE todos SET
                            title=?, description=?, priority=?, deadline=?, deadline_ts=?,
                            requester=?, type=?, status=?, source_message=?, updated_at=?,
                            snooze_until=?, is_top3=?, draft_subject=?, draft_body=?, evidence=?,
                            deadline_confidence=?, recipient_type=?, source_type=?, project_tag=?, persona_name=?, project_full_name=?
                        WHERE id=?
                        """,
                        (
                            row.get("title", ""),
                            row.get("description", ""),
                            row.get("priority", "low"),
                            row.get("deadline"),
                            row.get("deadline_ts"),
                            row.get("requester", ""),
                            row.get("type", ""),
                            row.get("status", "pending"),
                            source_msg_str,
                            updated_at,
                            row.get("snooze_until"),
                            row.get("is_top3", 0),
                            row.get("draft_subject", ""),
                            row.get("draft_body", ""),
                            row.get("evidence", "[]"),
                            row.get("deadline_confidence", "mid"),
                            row.get("recipient_type", "to"),
                            row.get("source_type", "메시지"),
                            row.get("project"),
                            row.get("persona_name"),
                            project_fullname,
                            todo_id,
                        ),
                    )
                    stats['updated'] += 1
                else:
                    # 변경 없음
                    stats['unchanged'] += 1
        
        return stats

    def fetch_active(self, persona_name: Optional[str] = None, persona_email: Optional[str] = None, persona_handle: Optional[str] = None) -> List[dict]:
        """활성 TODO 조회 (페르소나 필터링 옵션)
        
        Args:
            persona_name: 페르소나 이름 (한글 이름) - DB의 persona_name 컬럼과 비교
            persona_email: 페르소나 이메일 (현재는 사용하지 않음, 향후 확장용)
            persona_handle: 페르소나 채팅 핸들 (현재는 사용하지 않음, 향후 확장용)
            
        Note:
            페르소나가 **수신한** TODO만 반환합니다 (requester가 페르소나가 아닌 TODO).
            즉, 다른 사람이 페르소나에게 요청한 TODO만 표시됩니다.
            
            중요: DB의 persona_name 컬럼에는 한글 이름만 저장되어 있으므로,
            persona_name만 비교합니다.
        """
        cur = self._conn.cursor()
        
        # persona_name 필터만 사용 (DB 컬럼에 한글 이름만 저장됨)
        if persona_name:
            params = []
            
            # 1. persona_name 조건 (페르소나가 받은 TODO)
            persona_clause = "persona_name=?"
            params.append(persona_name)
            
            # 2. requester 제외 조건 (자기가 보낸 것 제외)
            # 페르소나의 이름, 이메일, 핸들 중 하나라도 requester와 일치하면 제외
            requester_params = []
            if persona_name:
                requester_params.append(persona_name)
            if persona_email:
                requester_params.append(persona_email)
            if persona_handle:
                requester_params.append(persona_handle)
            
            # NOT IN 절로 변경 (더 명확하고 안전)
            if requester_params:
                requester_placeholders = ",".join(["?"] * len(requester_params))
                requester_clause = f"requester NOT IN ({requester_placeholders})"
                params.extend(requester_params)
                
                # 최종 쿼리: (페르소나가 받은 TODO) AND (자기가 보낸 것 아님)
                query = f"SELECT * FROM todos WHERE status!='done' AND {persona_clause} AND {requester_clause} ORDER BY created_at DESC"
            else:
                # requester 필터 없으면 persona_name만 필터링
                query = f"SELECT * FROM todos WHERE status!='done' AND {persona_clause} ORDER BY created_at DESC"
            
            cur.execute(query, tuple(params))
            logger.debug(f"🔍 페르소나 필터링 TODO 조회: persona_name={persona_name}, 결과={cur.rowcount}개")
        else:
            # 필터 없으면 전체 조회
            cur.execute("SELECT * FROM todos WHERE status!='done' ORDER BY created_at DESC")
        
        return [dict(row) for row in cur.fetchall()]

    def update_top3_flags(self, updates: Iterable[tuple[int, str]]) -> None:
        updates = list(updates)
        if not updates:
            return
        with self._transaction() as cur:
            cur.executemany("UPDATE todos SET is_top3=? WHERE id=?", updates)

    def mark_done(self, todo_id: str, now_iso: str) -> bool:
        with self._transaction() as cur:
            cur.execute(
                "UPDATE todos SET status='done', updated_at=? WHERE id=?",
                (now_iso, todo_id),
            )
            return cur.rowcount > 0

    def snooze_until(self, todo_id: str, until_iso: str, updated_iso: str) -> None:
        with self._transaction() as cur:
            cur.execute(
                "UPDATE todos SET status='snoozed', snooze_until=?, updated_at=? WHERE id=?",
                (until_iso, updated_iso, todo_id),
            )

    def get_project(self, todo_id: str) -> Optional[str]:
        cur = self._conn.cursor()
        cur.execute("SELECT project_tag FROM todos WHERE id = ?", (todo_id,))
        row = cur.fetchone()
        return row[0] if row and row[0] else None

    def set_project(self, todo_id: str, project: Optional[str]) -> None:
        from src.utils.project_fullname_mapper import get_project_fullname
        project_fullname = get_project_fullname(project) if project else None
        with self._transaction() as cur:
            cur.execute(
                "UPDATE todos SET project_tag = ?, project_full_name = ? WHERE id = ?", 
                (project, project_fullname, todo_id)
            )

    def available_projects(self) -> List[str]:
        cur = self._conn.cursor()
        cur.execute(
            "SELECT DISTINCT project_tag FROM todos WHERE project_tag IS NOT NULL AND project_tag <> ''"
        )
        return [row[0] for row in cur.fetchall()]
    
    # ------------------------------------------------------------------ #
    # 중복 제거 관련 메서드
    # ------------------------------------------------------------------ #
    def find_by_source_message(self, source_message: str) -> Optional[dict]:
        """source_message로 TODO 조회
        
        Args:
            source_message: 원본 메시지 ID
            
        Returns:
            TODO 딕셔너리 또는 None
        """
        cur = self._conn.cursor()
        cur.execute(
            "SELECT * FROM todos WHERE source_message = ? LIMIT 1",
            (source_message,)
        )
        row = cur.fetchone()
        return dict(row) if row else None
    
    def find_duplicate_groups(self) -> dict:
        """같은 source_message를 가진 TODO 그룹 조회
        
        Returns:
            {source_message: [todo1, todo2, ...]} 형태의 딕셔너리
        """
        cur = self._conn.cursor()
        cur.execute(
            """
            SELECT source_message, COUNT(*) as cnt
            FROM todos
            WHERE source_message IS NOT NULL AND source_message != ''
            GROUP BY source_message
            HAVING cnt > 1
            """
        )
        
        duplicate_sources = [row[0] for row in cur.fetchall()]
        
        groups = {}
        for source_message in duplicate_sources:
            cur.execute(
                "SELECT * FROM todos WHERE source_message = ?",
                (source_message,)
            )
            groups[source_message] = [dict(row) for row in cur.fetchall()]
        
        return groups
    
    def delete_todo(self, todo_id: str) -> bool:
        """TODO 삭제
        
        Args:
            todo_id: TODO ID
            
        Returns:
            삭제 성공 여부
        """
        with self._transaction() as cur:
            cur.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
            return cur.rowcount > 0
    
    def create_indexes(self):
        """중복 제거를 위한 인덱스 생성"""
        with self._transaction() as cur:
            # source_message 인덱스
            try:
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_source_message ON todos(source_message)"
                )
            except sqlite3.OperationalError:
                pass
            
            # requester 인덱스
            try:
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_requester ON todos(requester)"
                )
            except sqlite3.OperationalError:
                pass
    
    def migrate_requester_field(self, persona_mapping: dict) -> dict:
        """requester 필드를 발신자 이메일에서 페르소나 이름으로 마이그레이션
        
        Args:
            persona_mapping: {email: persona_name} 매핑
                예: {"manager@test.com": "이정두", "dev@test.com": "김개발"}
        
        Returns:
            {"updated": int, "skipped": int, "errors": int}
        """
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info("🔄 requester 필드 마이그레이션 시작...")
        
        stats = {"updated": 0, "skipped": 0, "errors": 0}
        
        with self._transaction() as cur:
            # 모든 TODO 조회
            cur.execute("SELECT id, requester FROM todos")
            todos = cur.fetchall()
            
            logger.info(f"   총 {len(todos)}개 TODO 확인 중...")
            
            for todo in todos:
                todo_id = todo["id"]
                current_requester = todo["requester"]
                
                if not current_requester:
                    stats["skipped"] += 1
                    continue
                
                # 이미 페르소나 이름인지 확인 (이메일 형식이 아니면 스킵)
                if "@" not in current_requester:
                    stats["skipped"] += 1
                    continue
                
                # 매핑에서 페르소나 이름 찾기
                persona_name = persona_mapping.get(current_requester)
                
                if persona_name:
                    try:
                        cur.execute(
                            "UPDATE todos SET requester = ? WHERE id = ?",
                            (persona_name, todo_id)
                        )
                        stats["updated"] += 1
                        logger.debug(f"   업데이트: {current_requester} → {persona_name}")
                    except Exception as e:
                        logger.error(f"   업데이트 실패 (id={todo_id}): {e}")
                        stats["errors"] += 1
                else:
                    # 매핑에 없는 이메일
                    stats["skipped"] += 1
                    logger.debug(f"   스킵: {current_requester} (매핑 없음)")
        
        logger.info(
            f"✅ requester 필드 마이그레이션 완료: "
            f"업데이트={stats['updated']}, 스킵={stats['skipped']}, 오류={stats['errors']}"
        )
        
        return stats
    
    def get_persona_mapping_from_data(self, messages: List[dict]) -> dict:
        """메시지 데이터에서 페르소나 매핑 생성
        
        Args:
            messages: 메시지 리스트 (sender, persona_name 포함)
        
        Returns:
            {email: persona_name} 매핑
        """
        mapping = {}
        
        for msg in messages:
            sender = msg.get("sender")
            persona_name = msg.get("persona_name")
            
            if sender and persona_name and "@" in sender:
                mapping[sender] = persona_name
        
        return mapping

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass

    # context manager support -------------------------------------------------
    def __enter__(self) -> "TodoRepository":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
