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
        self._current_persona_filter: Optional[str] = None
        self._current_persona_email: Optional[str] = None
        self._current_persona_handle: Optional[str] = None
        self._show_reasoning_popup_flag: bool = False  # 선정이유 팝업 표시 플래그

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

    def save_items(self, rows: Iterable[dict], incremental: bool = True) -> dict:
        """TODO 아이템 저장
        
        Args:
            rows: TODO 딕셔너리 리스트
            incremental: True면 증분 업데이트, False면 전체 교체
            
        Returns:
            dict: 업데이트 통계 (incremental=True인 경우)
        """
        if incremental:
            stats = self.repository.upsert_todos(rows)
            logger.info(f"📊 TODO 증분 업데이트: 추가 {stats['added']}개, 수정 {stats['updated']}개, 유지 {stats['unchanged']}개")
            return stats
        else:
            self.repository.save_all(rows)
            logger.info(f"📊 TODO 전체 교체: {len(list(rows))}개")
            return {}

    def load_active_items(self, persona_name: Optional[str] = None) -> List[dict]:
        """활성 TODO 로드 (페르소나 필터링 옵션)
        
        Args:
            persona_name: 특정 페르소나의 TODO만 로드 (None이면 현재 필터 사용)
        """
        filter_persona = persona_name or self._current_persona_filter
        filter_email = self._current_persona_email
        filter_handle = self._current_persona_handle
        
        return self.repository.fetch_active(
            persona_name=filter_persona,
            persona_email=filter_email,
            persona_handle=filter_handle
        )

    # ------------------------------------------------------------------ #
    # 저장소 위임 (뷰에서 직접 접근하지 않도록 래핑)
    # ------------------------------------------------------------------ #
    def cleanup_old_rows(self, days: int) -> None:
        self.repository.cleanup_old_rows(days)

    def delete_all(self) -> None:
        self.repository.delete_all()

    def release_snoozed(self) -> None:
        self.repository.release_snoozed()

    def mark_done(self, todo_id: str, now_iso: str) -> bool:
        return self.repository.mark_done(todo_id, now_iso)

    def snooze_until(self, todo_id: str, until_iso: str, updated_iso: str) -> None:
        self.repository.snooze_until(todo_id, until_iso, updated_iso)

    # ------------------------------------------------------------------ #
    # Top-3 계산
    # ------------------------------------------------------------------ #
    def calculate_top3(self, rows: List[dict], show_reasoning: bool = False) -> Set[str]:
        """Top-3 선정 및 점수 계산.
        
        Args:
            rows: TODO 리스트
            show_reasoning: True면 선정이유 팝업 표시 (기본값: False)
        """
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
            
            # Top3 선정 이유 팝업 표시 (플래그가 True일 때만)
            if show_reasoning:
                reasoning = self.top3_service.get_last_reasoning()
                if reasoning and top_ids:
                    self._show_reasoning_popup(reasoning, len(top_ids))
            
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

        # 1. 배치로 캐시된 프로젝트 태그 로드 (성능 최적화)
        cached_projects = self._load_cached_project_tags_batch(todos)
        cache_hits = 0
        
        # 2. 캐시된 태그를 TODO에 적용
        uncached_todos = []
        for todo in todos:
            todo_id = todo.get("id")
            if not todo_id:
                continue
                
            # DB 캐시에서 프로젝트 태그 확인
            if todo_id in cached_projects:
                todo["project"] = cached_projects[todo_id]
                cache_hits += 1
            else:
                # 메모리에 이미 있는 프로젝트 태그 확인
                current_project = todo.get("project")
                if current_project:
                    # 메모리에 있는 태그를 DB에 저장
                    self.repository.set_project(todo_id, current_project)
                else:
                    # LLM 분석이 필요한 TODO
                    uncached_todos.append((todo, len(uncached_todos)))
        
        if cache_hits > 0:
            logger.info(f"✅ 프로젝트 태그 캐시 히트: {cache_hits}개")
        
        # 3. 캐시되지 않은 TODO만 LLM 분석 (성능 최적화)
        if uncached_todos:
            logger.info(f"🔍 프로젝트 태그 LLM 분석 필요: {len(uncached_todos)}개")
            self._analyze_uncached_project_tags(uncached_todos)
        else:
            logger.info("✅ 모든 TODO 프로젝트 태그 캐시됨 - LLM 분석 불필요")
    
    def _load_cached_project_tags_batch(self, todos: List[dict]) -> Dict[str, str]:
        """배치로 캐시된 프로젝트 태그 로드 (성능 최적화)"""
        if not todos or not self.repository:
            return {}
        
        try:
            todo_ids = [todo.get("id") for todo in todos if todo.get("id")]
            if not todo_ids:
                return {}
            
            # 배치로 DB에서 프로젝트 태그 조회
            cached_projects = {}
            for todo_id in todo_ids:
                project = self.repository.get_project(todo_id)
                if project and project.strip():
                    cached_projects[todo_id] = project.strip()
            
            logger.debug(f"[프로젝트 태그] 배치 캐시 로드: {len(cached_projects)}/{len(todo_ids)}개")
            return cached_projects
            
        except Exception as e:
            logger.error(f"프로젝트 태그 배치 캐시 로드 오류: {e}")
            return {}
    
    def _analyze_uncached_project_tags(self, uncached_todos: List[Tuple[dict, int]]) -> None:
        """캐시되지 않은 TODO들을 비동기로 분석"""
        if not uncached_todos:
            return
        
        # 비동기 프로젝트 태그 서비스 사용
        try:
            from src.services.async_project_tag_service import get_async_project_tag_service
            
            async_service = get_async_project_tag_service(self.project_service, self.repository)
            if async_service:
                # 콜백 함수 정의 (UI 업데이트용)
                def on_project_analyzed(todo_id: str, project: str):
                    logger.debug(f"[AsyncProjectTag] UI 업데이트: {todo_id} → {project}")
                    # TODO: UI 업데이트 시그널 발생 (필요시)
                
                # 비동기 분석 큐에 추가
                todos_for_analysis = [todo for todo, idx in uncached_todos]
                async_service.queue_multiple_todos(todos_for_analysis, on_project_analyzed)
                
                logger.info(f"🚀 {len(uncached_todos)}개 TODO 비동기 프로젝트 태그 분석 시작")
                return
        
        except Exception as e:
            logger.warning(f"비동기 프로젝트 태그 서비스 사용 실패, 동기 분석으로 폴백: {e}")
        
        # 폴백: 동기 분석
        self._analyze_uncached_project_tags_sync(uncached_todos)
    
    def _analyze_uncached_project_tags_sync(self, uncached_todos: List[Tuple[dict, int]]) -> None:
        """캐시되지 않은 TODO들을 동기적으로 분석 (폴백)"""
        available_projects = (
            list(self.project_service.project_tags.keys())
            if getattr(self.project_service, "project_tags", None)
            else ["CC", "HA", "WELL", "WI", "CI"]
        )

        updated = 0
        for todo, idx in uncached_todos:
            todo_id = todo.get("id")
            if not todo_id:
                continue

            # LLM으로 프로젝트 추출
            project = self._extract_project(todo, idx, available_projects)
            if project:
                todo["project"] = project
                # DB에 캐시 저장
                if self.repository:
                    self.repository.set_project(todo_id, project)
                updated += 1
                logger.debug(f"[프로젝트 태그] {todo_id}: {project} (동기 분석)")

        if updated:
            logger.info(f"✅ {updated}개 TODO 프로젝트 태그 동기 분석 및 캐시 저장 완료")

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
    
    def set_persona_filter(self, persona_name: Optional[str] = None, persona_email: Optional[str] = None, persona_handle: Optional[str] = None) -> None:
        """페르소나 필터 설정
        
        Args:
            persona_name: 페르소나 이름 (한글 이름)
            persona_email: 페르소나 이메일
            persona_handle: 페르소나 채팅 핸들
        """
        self._current_persona_filter = persona_name
        self._current_persona_email = persona_email
        self._current_persona_handle = persona_handle
        
        filter_info = []
        if persona_name:
            filter_info.append(f"이름={persona_name}")
        if persona_email:
            filter_info.append(f"이메일={persona_email}")
        if persona_handle:
            filter_info.append(f"핸들={persona_handle}")
        
        logger.info(f"👤 페르소나 필터 설정: {', '.join(filter_info) if filter_info else '전체'}")
    
    def match_persona(self, todo: dict) -> bool:
        """TODO가 현재 페르소나 필터와 일치하는지 확인"""
        if not self._current_persona_filter:
            return True
        return todo.get("persona_name") == self._current_persona_filter

    def _show_reasoning_popup(self, reasoning: str, count: int):
        """Top3 선정 이유 팝업 표시
        
        Args:
            reasoning: 선정 이유 (한국어)
            count: 선정된 TODO 개수
        """
        try:
            from PyQt6.QtWidgets import QMessageBox
            
            msg_box = QMessageBox()
            msg_box.setWindowTitle("✅ Top3 선정 완료")
            msg_box.setIcon(QMessageBox.Icon.Information)
            msg_box.setText(f"<b>{count}개의 TODO가 Top3로 선정되었습니다</b>")
            msg_box.setInformativeText(f"<p style='margin-top:10px;'><b>선정 이유:</b><br>{reasoning}</p>")
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: white;
                }
                QLabel {
                    font-size: 13px;
                    color: #333;
                }
            """)
            msg_box.exec()
        except Exception as e:
            logger.error(f"[TodoController] 팝업 표시 오류: {e}")
