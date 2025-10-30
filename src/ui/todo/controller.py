# -*- coding: utf-8 -*-
"""
Todo 패널 전용 컨트롤러

데이터 로딩/저장, Top-3 계산, 프로젝트 태그 업데이트 등
비-UI 로직을 캡슐화합니다.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Iterable, List, Optional, Sequence, Set, Tuple, Dict

from src.services import Top3Service

from .repository import TodoRepository

logger = logging.getLogger(__name__)


class TodoPanelController:
    """TodoPanel의 비즈니스 로직을 담당."""

    def __init__(
        self,
        repository: TodoRepository,
        top3_service: Optional[Top3Service] = None,
        project_service: Optional[object] = None,
    ) -> None:
        self.repository = repository
        self.top3_service = top3_service
        self.project_service = project_service
        self._current_project_filter: Optional[str] = None

    # ------------------------------------------------------------------ #
    # 서비스 인스턴스 업데이트
    # ------------------------------------------------------------------ #
    def set_top3_service(self, service: Optional[Top3Service]) -> None:
        self.top3_service = service

    def set_project_service(self, service: Optional[object]) -> None:
        self.project_service = service

    # ------------------------------------------------------------------ #
    # 데이터 준비 / 저장 / 로드
    # ------------------------------------------------------------------ #
    def prepare_items(self, items: Sequence[dict]) -> List[dict]:
        """외부에서 전달 받은 TODO 원본 데이터를 정규화."""
        now_iso = datetime.now().isoformat()
        prepared: List[dict] = []
        for raw in items or []:
            base = {
                "id": None,
                "title": "",
                "description": "",
                "priority": "low",
                "deadline": None,
                "deadline_ts": None,
                "requester": "",
                "type": "",
                "status": "pending",
                "source_message": {},
                "created_at": now_iso,
                "updated_at": now_iso,
                "snooze_until": None,
                "is_top3": 0,
                "draft_subject": "",
                "draft_body": "",
                "evidence": "[]",
                "deadline_confidence": "mid",
                "recipient_type": "to",
                "source_type": "메시지",
            }
            todo = {**base, **(raw or {})}

            if not todo.get("id"):
                import uuid

                todo["id"] = uuid.uuid4().hex

            if not todo.get("created_at"):
                todo["created_at"] = now_iso
            if not todo.get("updated_at"):
                todo["updated_at"] = now_iso

            ev_val = todo.get("evidence")
            if isinstance(ev_val, list):
                todo["evidence"] = json.dumps(ev_val, ensure_ascii=False)
            elif ev_val is None:
                todo["evidence"] = "[]"

            todo["status"] = (todo.get("status") or "pending").lower()
            prepared.append(todo)
        return prepared

    def save_items(self, rows: Iterable[dict]) -> None:
        self.repository.save_all(rows)

    def load_active_items(self) -> List[dict]:
        return self.repository.fetch_active()

    # ------------------------------------------------------------------ #
    # Top-3 계산
    # ------------------------------------------------------------------ #
    def calculate_top3(self, rows: List[dict]) -> Set[str]:
        """Top-3 선정 및 점수 계산."""
        if not self.top3_service:
            for row in rows:
                row["_top3_score"] = 0.0
            return set()

        try:
            top_ids = set(self.top3_service.pick_top3(rows))
            updates: List[Tuple[int, str]] = []
            for row in rows:
                row_id = row.get("id")
                if not row_id:
                    continue
                mark = 1 if row_id in top_ids else 0
                if row.get("is_top3") != mark:
                    updates.append((mark, row_id))
                row["is_top3"] = mark
                try:
                    row["_top3_score"] = self.top3_service.calculate_score(row)
                except Exception:
                    row["_top3_score"] = 0.0

            if updates:
                self.repository.update_top3_flags(updates)
            return top_ids
        except Exception as exc:
            logger.error("Top-3 계산 오류: %s", exc, exc_info=True)
            for row in rows:
                row["_top3_score"] = 0.0
            return set()

    # ------------------------------------------------------------------ #
    # 프로젝트 태그
    # ------------------------------------------------------------------ #
    def update_project_tags(self, todos: List[dict]) -> None:
        if not self.project_service:
            logger.warning("[프로젝트 태그] 프로젝트 서비스가 없습니다")
            return

        available_projects = (
            list(self.project_service.project_tags.keys())
            if getattr(self.project_service, "project_tags", None)
            else ["CARE", "HA", "WD", "BRIDGE", "LINK"]
        )

        updated = 0
        for idx, todo in enumerate(todos):
            todo_id = todo.get("id")
            if not todo_id:
                continue

            db_project = self.repository.get_project(todo_id)
            if db_project:
                todo["project"] = db_project
                continue

            current_project = todo.get("project")
            if current_project:
                self.repository.set_project(todo_id, current_project)
                updated += 1
                continue

            project = self._extract_project(todo, idx, available_projects)
            if project:
                todo["project"] = project
                self.repository.set_project(todo_id, project)
                updated += 1

        if updated:
            logger.info("✅ %d개 TODO에 프로젝트 태그 추가", updated)

    def _extract_project(self, todo: dict, index: int, available: List[str]) -> Optional[str]:
        project = None
        source_message = todo.get("source_message", "")
        if source_message:
            try:
                message_data = (
                    json.loads(source_message)
                    if isinstance(source_message, str) and source_message.startswith("{")
                    else {"content": source_message, "subject": todo.get("title", "")}
                )
                enhanced_message = {
                    "content": f"{todo.get('title', '')} {message_data.get('content', '')} {message_data.get('subject', '')}",
                    "subject": message_data.get("subject", todo.get("title", "")),
                    "sender": message_data.get("sender", ""),
                }
                project = self.project_service.extract_project_from_message(enhanced_message)
                if project:
                    logger.info("[프로젝트 태그] LLM 분석 결과 %s 할당", project)
            except Exception as exc:
                logger.debug("프로젝트 추출 실패: %s", exc)

        if project:
            return project

        title = todo.get("title", "")
        description = todo.get("description", "")
        text = f"{title} {description}".lower()
        if "care connect" in text:
            return "CARE"
        if "healthcore" in text or "health core" in text:
            return "HA"
        if "carebridge" in text or "care bridge" in text:
            return "BRIDGE"
        if "welllink" in text and ("브랜드" in text or "런칭" in text):
            return "LINK"
        if "insight dashboard" in text or "kpi 대시보드" in text:
            return "WD"

        if available:
            project = available[index % len(available)]
            logger.warning("[프로젝트 태그] 최후 수단 순환 할당 %s", project)
            return project
        return None

    # ------------------------------------------------------------------ #
    # 필터링
    # ------------------------------------------------------------------ #
    def set_project_filter(self, project_code: Optional[str]) -> None:
        self._current_project_filter = project_code

    def match_project(self, todo: dict) -> bool:
        if not self._current_project_filter:
            return True
        return (todo.get("project") or "").upper() == self._current_project_filter.upper()
