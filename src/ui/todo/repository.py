# -*- coding: utf-8 -*-
"""
Todo 저장소 모듈

TodoPanel과 같은 UI 계층이 직접 sqlite3에 접근하지 않도록 캡슐화합니다.
"""
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Generator, Iterable, List, Optional

DEFAULT_DB_PATH = os.path.join("data", "multi_project_8week_ko", "todos_cache.db")


class TodoRepository:
    """SQLite 기반 TODO 저장소."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = Path(db_path or DEFAULT_DB_PATH)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._init_db()

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
                project TEXT,
                deadline_confidence TEXT,
                recipient_type TEXT DEFAULT 'to',
                source_type TEXT DEFAULT '메시지'
            )
            """
        )
        self._ensure_column(cur, "recipient_type", "TEXT DEFAULT 'to'")
        self._ensure_column(cur, "source_type", "TEXT DEFAULT '메시지'")
        self._conn.commit()

    def _ensure_column(self, cur: sqlite3.Cursor, name: str, definition: str) -> None:
        try:
            cur.execute(f"ALTER TABLE todos ADD COLUMN {name} {definition}")
        except sqlite3.OperationalError:
            # 이미 존재하는 경우는 무시
            pass

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

                cur.execute(
                    """
                    INSERT OR REPLACE INTO todos (
                        id, title, description, priority, deadline, deadline_ts,
                        requester, type, status, source_message, created_at, updated_at,
                        snooze_until, is_top3, draft_subject, draft_body, evidence,
                        deadline_confidence, recipient_type, source_type, project
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    ),
                )

    def fetch_active(self) -> List[dict]:
        cur = self._conn.cursor()
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
        cur.execute("SELECT project FROM todos WHERE id = ?", (todo_id,))
        row = cur.fetchone()
        return row[0] if row and row[0] else None

    def set_project(self, todo_id: str, project: Optional[str]) -> None:
        with self._transaction() as cur:
            cur.execute("UPDATE todos SET project = ? WHERE id = ?", (project, todo_id))

    def available_projects(self) -> List[str]:
        cur = self._conn.cursor()
        cur.execute(
            "SELECT DISTINCT project FROM todos WHERE project IS NOT NULL AND project <> ''"
        )
        return [row[0] for row in cur.fetchall()]

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
