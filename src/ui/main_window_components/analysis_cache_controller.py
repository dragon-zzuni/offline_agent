# -*- coding: utf-8 -*-
"""분석 및 캐시 관리 컨트롤러"""
from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import QApplication, QLabel

from src.integrations.polling_worker import PollingWorker
from src.ui.widgets import WorkerThread

if TYPE_CHECKING:  # pragma: no cover
    from src.ui.main_window import SmartAssistantGUI

logger = logging.getLogger(__name__)

DEFAULT_EMAIL_LIMIT = None  # 제한 없음
DEFAULT_MESSENGER_LIMIT = None  # 제한 없음
DEFAULT_OVERALL_LIMIT = None  # 제한 없음

class AnalysisCacheController:
    """메시지 분석 및 캐시 관리를 담당하는 컨트롤러."""

    def __init__(self, ui: "SmartAssistantGUI") -> None:
        self.ui = ui
        self._collect_in_progress: bool = False
        self._active_collection_persona: Optional[str] = None
        self._pending_persona_key: Optional[str] = None
        self._last_analysis_incremental: bool = False

    # ------------------------------------------------------------------
    # 공개 API
    # ------------------------------------------------------------------
    def start_quick_analysis(self, force: bool = False) -> None:
        """선택된 페르소나에 대해 빠른 분석을 시작한다.

        Args:
            force: True일 경우 캐시를 무시하고 데이터를 새로 수집한다.
        """
        ui = self.ui
        try:
            persona = getattr(ui, "selected_persona", None)
            if not persona:
                logger.warning("⚠️ 선택된 페르소나가 없어 빠른 분석을 건너뜀")
                return

            persona_key = getattr(ui, "_current_persona_id", None)
            if not persona_key:
                email = getattr(persona, "email_address", "") or ""
                handle = getattr(persona, "chat_handle", "") or ""
                if email or handle:
                    persona_key = f"{email}_{handle}".strip("_")
                else:
                    persona_key = getattr(persona, "id", "") or persona.name

            if not persona_key:
                logger.warning("⚠️ 페르소나 키를 결정할 수 없어 빠른 분석을 중단")
                return

            if self._collect_in_progress:
                logger.info("⏳ 메시지 수집이 진행 중이라 빠른 분석 요청을 대기 상태로 전환")
                return

            existing_messages = getattr(ui, "collected_messages", []) or []
            if existing_messages and not force:
                logger.info(
                    "📂 기존 메시지 %d개로 빠른 분석 실행 (persona=%s)",
                    len(existing_messages),
                    persona_key,
                )
                self._trigger_background_analysis(existing_messages)
                return

            if not force and self._should_use_cache(persona_key):
                logger.info("📂 캐시된 데이터로 빠른 분석 시작: %s", persona_key)
                self._load_from_cache(persona_key)
                messages = getattr(ui, "collected_messages", []) or []
                if messages:
                    self._trigger_background_analysis(messages)
                else:
                    logger.info("ℹ️ 캐시된 메시지가 없어 새로 수집합니다.")
                    self._collect_and_cache_data(persona_key)
                return

            # 데이터 소스 준비 (VirtualOffice 모드)
            if (
                getattr(ui, "data_source_type", None) == "virtualoffice"
                and hasattr(ui, "assistant")
                and hasattr(ui.assistant, "set_virtualoffice_source")
                and getattr(ui, "vo_client", None)
            ):
                ui.assistant.set_virtualoffice_source(ui.vo_client, persona)

            logger.info("🚀 빠른 분석을 위해 메시지를 새로 수집합니다. force=%s", force)
            self._collect_and_cache_data(persona_key)
        except Exception as exc:  # pragma: no cover
            logger.error("❌ 빠른 분석 실행 오류: %s", exc, exc_info=True)
            if hasattr(ui, "status_message"):
                ui.status_message.setText(f"빠른 분석 오류: {exc}")

    # ------------------------------------------------------------------
    # 백그라운드 분석
    # ------------------------------------------------------------------
    def _process_new_messages_async(
        self,
        new_messages: List[Dict[str, Any]],
        incremental: bool = False,
    ) -> None:
        """새 메시지를 비동기로 분석한다."""
        ui = self.ui
        try:
            if not new_messages:
                return

            worker = getattr(ui, "worker_thread", None)
            if worker and worker.isRunning():
                logger.info("🧵 백그라운드 워커가 이미 실행 중이어서 새 요청을 건너뜀")
                return

            logger.info("🔄 새 메시지 분석 시작: %d개", len(new_messages))

            if hasattr(ui, "assistant") and ui.assistant:
                dataset_config = dict(ui.dataset_config) if hasattr(ui, "dataset_config") else {}
                collect_options = {
                    "email_limit": None,
                    "messenger_limit": None,
                    "overall_limit": None,
                    "force_reload": False,
                }

                ui.worker_thread = WorkerThread(ui.assistant, dataset_config, collect_options)
                ui.worker_thread.result_ready.connect(self._handle_background_analysis_result)
                ui.worker_thread.error_occurred.connect(self._handle_background_analysis_error)
                self._last_analysis_incremental = incremental
                ui.worker_thread.start()

                logger.info("✅ 백그라운드 분석 워커 스레드 시작됨")
            else:
                logger.warning("⚠️ Assistant가 없어 분석을 건너뜀")
        except Exception as exc:  # pragma: no cover
            logger.error("❌ 새 메시지 분석 준비 오류: %s", exc, exc_info=True)

    def _handle_background_analysis_result(self, result: Dict[str, Any]) -> None:
        """백그라운드 분석 결과를 처리한다."""
        ui = self.ui
        try:
            if result.get("success"):
                todo_list = result.get("todo_list") or []
                todos: List[Dict[str, Any]] = []

                logger.info("🔍 TODO 리스트 타입: %s", type(todo_list))

                if getattr(ui, "collected_messages", None):
                    email_count = len([m for m in ui.collected_messages if m.get("type") == "email"])
                    message_count = len([m for m in ui.collected_messages if m.get("type") == "messenger"])
                    other_count = len([m for m in ui.collected_messages if m.get("type") not in ["email", "messenger"]])
                    logger.info(
                        "🔍 수집된 메시지 분석: 이메일 %d개, 메신저 %d개, 기타 %d개",
                        email_count,
                        message_count,
                        other_count,
                    )

                # todo_list가 이미 리스트면 그대로 사용, dict면 추출
                if isinstance(todo_list, list):
                    todos = todo_list
                    logger.info("🔍 TODO 리스트 직접 사용: %d개", len(todos))
                elif isinstance(todo_list, dict):
                    # main.py의 generate_todo_list가 반환하는 형식: {"summary": {...}, "items": [...]}
                    if "items" in todo_list:
                        todos = todo_list["items"]
                        logger.info("🔍 TODO 리스트 'items' 키에서 추출: %d개", len(todos))
                    else:
                        # 레거시 형식 지원: 재귀적으로 TODO 아이템 찾기
                        def extract_todos_recursive(data: Any, depth: int = 0) -> List[Dict[str, Any]]:
                            if depth > 3:
                                return []

                            extracted: List[Dict[str, Any]] = []

                            if isinstance(data, dict):
                                if any(key in data for key in ["title", "description", "priority", "deadline"]):
                                    if "id" not in data:
                                        data["id"] = uuid.uuid4().hex
                                    extracted.append(data)
                                else:
                                    for value in data.values():
                                        extracted.extend(extract_todos_recursive(value, depth + 1))
                            elif isinstance(data, list):
                                for item in data:
                                    extracted.extend(extract_todos_recursive(item, depth + 1))

                            return extracted

                        todos = extract_todos_recursive(todo_list)
                        logger.info("🔍 추출된 TODO 개수 (재귀): %d", len(todos))
                else:
                    logger.warning("⚠️ 예상치 못한 TODO 리스트 타입: %s", type(todo_list))
                    todos = []

                incremental_mode = getattr(self, "_last_analysis_incremental", False)

                if todos and hasattr(ui, "todo_panel"):
                    # 자연어 규칙이 있으면 선정이유 팝업 표시
                    show_reasoning = False
                    if hasattr(ui.todo_panel, "top3_service") and ui.todo_panel.top3_service:
                        has_rules = bool(
                            ui.todo_panel.top3_service.get_last_instruction() or
                            ui.todo_panel.top3_service.get_entity_rules().get("requester") or
                            ui.todo_panel.top3_service.get_entity_rules().get("keyword") or
                            ui.todo_panel.top3_service.get_entity_rules().get("type")
                        )
                        show_reasoning = has_rules
                    
                    logger.info(f"[AnalysisCacheController] populate_from_items 호출: incremental={incremental_mode}, todos={len(todos)}개")
                    ui.todo_panel.populate_from_items(todos, incremental=incremental_mode, show_reasoning=show_reasoning)
                    logger.info("✅ 백그라운드 분석 완료: %d개 TODO 생성", len(todos))
                    
                    # 증분 모드일 때만 TODO 생성 알림 표시
                    if incremental_mode and len(todos) > 0:
                        self._show_todo_creation_notification(len(todos))
                    
                    self._update_cache_with_analysis_results(
                        todos,
                        [],
                        incremental=incremental_mode,
                    )
                else:
                    logger.info("ℹ️ 백그라운드 분석 완료: 생성된 TODO 없음")

                analysis_results = result.get("analysis_results", [])
                if analysis_results:
                    ui.analysis_results = analysis_results
                    if hasattr(ui, "analysis_result_panel"):
                        ui.analysis_result_panel.update_analysis(
                            analysis_results,
                            ui.collected_messages,
                        )
                    logger.info("✅ 분석 결과 업데이트: %d개", len(analysis_results))

                if todos:
                    self._update_cache_with_analysis_results(
                        todos,
                        analysis_results,
                        incremental=incremental_mode,
                    )

                self._last_analysis_incremental = False
            else:
                error_msg = result.get("error", "알 수 없는 오류")
                logger.error("❌ 백그라운드 분석 실패: %s", error_msg)
                self._last_analysis_incremental = False
        except Exception as exc:  # pragma: no cover
            logger.error("❌ 백그라운드 분석 결과 처리 오류: %s", exc, exc_info=True)

    def _handle_background_analysis_error(self, error_msg: str) -> None:
        ui = self.ui
        logger.error("❌ 백그라운드 분석 오류: %s", error_msg)
        if hasattr(ui, "status_message"):
            ui.status_message.setText(f"백그라운드 분석 오류: {error_msg}")

    def _trigger_reanalysis(self) -> None:
        """전체 메시지 재분석을 트리거한다."""
        ui = self.ui
        try:
            logger.info("🔄 전체 메시지 재분석 시작")
            ui.status_message.setText("새 메시지 분석 중...")

            if getattr(ui, "collected_messages", None):
                dataset_config = dict(ui.dataset_config)
                collect_options = {
                    "email_limit": None,
                    "messenger_limit": None,
                    "overall_limit": None,
                    "force_reload": False,
                }

                ui.connect_collect_button.setEnabled(False)
                ui.progress_bar.setVisible(True)
                ui.progress_bar.setValue(0)

                ui.worker_thread = WorkerThread(ui.assistant, dataset_config, collect_options)
                ui.worker_thread.progress_updated.connect(ui.progress_bar.setValue)
                ui.worker_thread.status_updated.connect(ui.status_message.setText)
                ui.worker_thread.result_ready.connect(self._handle_reanalysis_result)
                if hasattr(ui, "data_controller"):
                    ui.worker_thread.error_occurred.connect(ui.data_controller.handle_error)
                else:
                    ui.worker_thread.error_occurred.connect(self._handle_background_analysis_error)
                ui.worker_thread.start()
            else:
                logger.warning("⚠️ 분석할 메시지가 없음")
                ui.status_message.setText("분석할 메시지가 없습니다")
        except Exception as exc:  # pragma: no cover
            logger.error("❌ 재분석 트리거 오류: %s", exc, exc_info=True)
            ui.status_message.setText(f"재분석 오류: {exc}")

    def _handle_reanalysis_result(self, result: Dict[str, Any]) -> None:
        ui = self.ui
        try:
            ui.connect_collect_button.setEnabled(True)
            ui.progress_bar.setVisible(False)

            if result.get("success"):
                todo_list = result.get("todo_list") or {}
                items = todo_list.get("items", [])
                logger.info(
                    "[MainWindow] TODO 업데이트 체크: items=%d, has_todo_panel=%s",
                    len(items) if items else 0,
                    hasattr(ui, "todo_panel"),
                )
                if items and hasattr(ui, "todo_panel"):
                    # 🔥 재분석도 증분 모드로 처리하여 기존 unread 상태 유지
                    logger.info("🔄 재분석 결과를 증분 모드로 적용 (unread 상태 유지)")
                    ui.todo_panel.populate_from_items(items, incremental=True)
                    logger.info("✅ TODO 업데이트 완료: %d개", len(items))
                else:
                    logger.warning(
                        "[MainWindow] TODO 업데이트 건너뜀: items=%d, has_panel=%s",
                        len(items) if items else 0,
                        hasattr(ui, "todo_panel"),
                    )

                analysis_results = result.get("analysis_results") or []
                if analysis_results:
                    ui.analysis_results = analysis_results
                    if hasattr(ui, "analysis_result_panel"):
                        ui.analysis_result_panel.update_analysis(
                            ui.analysis_results,
                            ui.collected_messages,
                        )
                    logger.info("✅ 분석 결과 업데이트 완료: %d개", len(analysis_results))

                self._save_to_cache(items, ui.collected_messages, analysis_results)
                self._update_cache_with_analysis_results(items, analysis_results)
                if hasattr(ui, "message_summary_panel"):
                    ui._update_message_summaries("day")

                ui.status_message.setText(f"✅ 재분석 완료: TODO {len(items)}개")
                ui.statusBar().showMessage(
                    f"✅ 재분석 완료: TODO {len(items)}개, 분석 {len(analysis_results)}개",
                    3000,
                )
            else:
                logger.error("❌ 재분석 실패")
                ui.status_message.setText("재분석 실패")
        except Exception as exc:  # pragma: no cover
            logger.error("❌ 재분석 결과 처리 오류: %s", exc, exc_info=True)
            ui.status_message.setText(f"재분석 결과 처리 오류: {exc}")

    # ------------------------------------------------------------------
    # 캐시 키 및 저장
    # ------------------------------------------------------------------
    def _build_cache_key(self):
        from src.services.persona_todo_cache_service import CacheKey

        ui = self.ui
        return CacheKey(
            persona_id=ui._current_persona_id or "",
            time_range_start=None,
            time_range_end=None,
            data_version=ui._current_data_version,
        )

    def _display_cached_result(self, cached_result) -> None:
        ui = self.ui
        try:
            logger.info("📂 캐시된 결과 표시 중 (생성 시간: %s)", cached_result.created_at)

            # 1. 메시지 복원 (먼저 복원하여 다른 패널에서 사용 가능하도록)
            if cached_result.messages:
                ui.collected_messages = cached_result.messages
                if hasattr(ui.assistant, "collected_messages"):
                    ui.assistant.collected_messages = cached_result.messages
                logger.info("📨 메시지 복원: %d개", len(cached_result.messages))
                # 메시지 요약 캐시는 클리어하지 않음 (페르소나별로 캐시되므로)
                # 대신 페르소나가 변경되었으므로 새로운 캐시 키로 생성됨

            # 2. TODO 복원 (DB에 저장 및 UI 표시)
            if cached_result.todo_list and hasattr(ui, "todo_panel"):
                logger.info("📋 TODO 복원: %d개", len(cached_result.todo_list))
                # incremental=False로 호출하여 전체 교체 (DB에 저장됨)
                # populate_from_items는 DB에 저장하고 UI도 업데이트함
                ui.todo_panel.populate_from_items(cached_result.todo_list, incremental=False)
                logger.info("✅ TODO DB 저장 및 UI 표시 완료")
                
                # 페르소나 필터가 적용된 TODO만 표시되도록 리프레시 (populate_from_items 후 자동으로 필터링됨)
                # populate_from_items 내부에서 _rebuild_from_rows가 호출되므로 별도 refresh 불필요
                # 하지만 페르소나 필터가 변경되었을 수 있으므로 한 번 더 확인
                current_persona = None
                if hasattr(ui, 'selected_persona') and ui.selected_persona:
                    current_persona = ui.selected_persona.name
                logger.info(f"📋 캐시 복원된 TODO 개수: {len(cached_result.todo_list)}, 현재 페르소나: {current_persona}")

            # 3. 분석 결과 복원
            analysis_data = getattr(cached_result, "analysis_data", None)
            if analysis_data:
                ui.analysis_results = analysis_data
                logger.info("📊 분석 결과 복원: %d개", len(analysis_data))
            elif hasattr(cached_result, 'analysis_summary') and cached_result.analysis_summary:
                ui.analysis_results = cached_result.analysis_summary.get('results', [])
                logger.info("📊 분석 결과 복원(하위 호환): %d개", len(ui.analysis_results) if ui.analysis_results else 0)

            # 4. UI 패널 업데이트 (메시지 요약, 이메일, 분석 결과)
            # 메시지 요약 패널 업데이트 (collected_messages가 설정된 후)
            if cached_result.messages and hasattr(ui, "message_summary_panel"):
                logger.info(f"📝 메시지 요약 패널 업데이트 시작 (메시지 {len(cached_result.messages)}개)")
                # collected_messages가 설정되었는지 확인
                if hasattr(ui, "collected_messages") and ui.collected_messages:
                    ui._update_message_summaries("day")
                    logger.info("📝 메시지 요약 패널 업데이트 완료")
                else:
                    logger.warning("⚠️ collected_messages가 설정되지 않아 메시지 요약 패널 업데이트 건너뜀")
            
            # 이메일 패널 업데이트
            if cached_result.messages and hasattr(ui, "email_panel"):
                email_messages = [m for m in cached_result.messages if m.get("type") == "email"]
                # TODO 아이템 가져오기 (필터링된 TODO)
                todo_items = []
                if hasattr(ui, "todo_panel") and hasattr(ui.todo_panel, "controller"):
                    try:
                        todo_items = ui.todo_panel.controller.load_active_items()
                    except Exception as e:
                        logger.warning(f"TODO 아이템 가져오기 실패: {e}")
                ui.email_panel.update_emails(email_messages, todo_items)
                logger.info("📧 이메일 패널 업데이트 완료: %d개", len(email_messages))
            
            # 분석 결과 패널 업데이트
            if hasattr(ui, "analysis_result_panel"):
                # analysis_results가 설정되었는지 확인
                analysis_results = getattr(ui, "analysis_results", None) or []
                if analysis_results:
                    ui.analysis_result_panel.update_analysis(analysis_results, cached_result.messages or [])
                    logger.info(f"📊 분석 결과 패널 업데이트 완료: {len(analysis_results)}개")
                else:
                    logger.warning("⚠️ analysis_results가 없어 분석 결과 패널을 빈 상태로 표시")
                    ui.analysis_result_panel.update_analysis([], cached_result.messages or [])
            
            # 타임라인 업데이트
            if cached_result.messages and hasattr(ui, "timeline_list"):
                ui._update_timeline_with_badges()
                logger.info("⏰ 타임라인 업데이트 완료")

            todo_count = len(cached_result.todo_list) if cached_result.todo_list else 0
            msg_count = len(cached_result.messages) if cached_result.messages else 0
            ui.statusBar().showMessage(
                "✅ 캐시에서 로드 완료: TODO {0}개, 메시지 {1}개 (생성: {2})".format(
                    todo_count,
                    msg_count,
                    cached_result.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                ),
                5000,
            )
            logger.info("✅ 캐시 복원 완료: TODO %d개, 메시지 %d개", todo_count, msg_count)
        except Exception as exc:  # pragma: no cover
            logger.error("❌ 캐시된 결과 표시 오류: %s", exc, exc_info=True)

    def _save_to_cache(
        self,
        todo_list: List[Dict[str, Any]],
        messages: List[Dict[str, Any]],
        analysis_results: List[Dict[str, Any]],
    ) -> None:
        ui = self.ui
        try:
            if not ui._current_persona_id:
                logger.debug("페르소나 ID가 없어 캐시 저장 건너뜀")
                return

            from src.services.persona_todo_cache_service import CachedAnalysisResult

            cache_key = self._build_cache_key()
            analysis_summary = {
                "total_messages": len(messages),
                "email_count": sum(1 for m in messages if m.get("type") == "email" or m.get("platform") == "email"),
                "chat_count": sum(1 for m in messages if m.get("type") == "messenger" or m.get("platform") == "messenger"),
                "todo_count": len(todo_list),
                "high_priority_count": sum(1 for t in todo_list if t.get("priority") == "high"),
                "medium_priority_count": sum(1 for t in todo_list if t.get("priority") == "medium"),
                "low_priority_count": sum(1 for t in todo_list if t.get("priority") == "low"),
            }

            cached_result = CachedAnalysisResult(
                cache_key=cache_key.to_hash(),
                persona_id=ui._current_persona_id,
                todo_list=todo_list,
                messages=messages,
                analysis_summary=analysis_summary,
                analysis_data=list(analysis_results or []),
                created_at=datetime.now(),
                last_accessed_at=datetime.now(),
            )

            ui._cache_service.put(cache_key, cached_result)
            logger.info("💾 캐시 저장 완료: TODO %d개, 메시지 %d개", len(todo_list), len(messages))
        except Exception as exc:  # pragma: no cover
            logger.error("❌ 캐시 저장 오류: %s", exc, exc_info=True)
    
    def _show_todo_creation_notification(self, todo_count: int):
        """TODO 생성 완료 알림 표시
        
        Args:
            todo_count: 생성된 TODO 개수
        """
        try:
            from PyQt6.QtWidgets import QMessageBox
            from PyQt6.QtCore import QTimer
            
            ui = self.ui
            
            # 메시지 구성
            title = "✅ TODO 생성 완료"
            message = f"""
<div style='font-size: 14px;'>
<p><b>새로운 TODO가 생성되었습니다!</b></p>
<br>
<table style='width: 100%;'>
<tr>
    <td style='padding: 5px;'>📋 생성된 TODO:</td>
    <td style='padding: 5px; text-align: right;'><b style='color: #4CAF50; font-size: 16px;'>{todo_count}개</b></td>
</tr>
</table>
<br>
<p style='color: #666; font-size: 12px;'>
※ TODO 리스트에서 확인하세요
</p>
</div>
"""
            
            # 팝업 생성
            msg_box = QMessageBox(ui)
            msg_box.setWindowTitle(title)
            msg_box.setText(message)
            msg_box.setIcon(QMessageBox.Icon.Information)
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            
            # 스타일 적용
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: white;
                }
                QLabel {
                    color: #333;
                    min-width: 300px;
                }
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                    padding: 8px 20px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
            """)
            
            # 3초 후 자동 닫기
            QTimer.singleShot(3000, msg_box.close)
            
            # 비모달로 표시 (백그라운드 작업 방해하지 않음)
            msg_box.show()
            
            logger.info(f"✅ TODO 생성 알림 표시: {todo_count}개")
            
        except Exception as e:
            logger.error(f"TODO 생성 알림 표시 오류: {e}")

    def _should_use_cache(self, persona_key: str) -> bool:
        ui = self.ui
        try:
            if persona_key not in ui._persona_cache:
                logger.info("📂 캐시 없음: %s", persona_key)
                return False

            cached_data = ui._persona_cache[persona_key]
            if not cached_data.get("messages"):
                logger.info("📂 캐시된 메시지 없음: %s", persona_key)
                return False
            if not cached_data.get("todos"):
                logger.info("📂 TODO 없음: %s", persona_key)
                return False

            logger.info(
                "✅ 캐시 사용 가능: %s (메시지: %d개, TODO: %d개)",
                persona_key,
                len(cached_data["messages"]),
                len(cached_data["todos"]),
            )
            return True
        except Exception as exc:  # pragma: no cover
            logger.error("❌ 캐시 확인 오류: %s", exc)
            return False

    def _trigger_immediate_polling(self) -> None:
        ui = self.ui
        try:
            if not getattr(ui, "_initial_collection_completed", False):
                logger.info("⏳ 초기 전체 수집이 끝나지 않아 즉시 폴링을 건너뜀")
                return
            worker = getattr(ui, "polling_worker", None)
            if worker and worker.isRunning() and hasattr(worker, "trigger_immediate_poll"):
                worker.trigger_immediate_poll()
                logger.info("✅ 즉시 폴링 트리거")
            elif worker and worker.isRunning():
                logger.warning("⚠️ PollingWorker가 즉시 폴링을 지원하지 않음")
        except Exception as exc:  # pragma: no cover
            logger.error("즉시 폴링 트리거 오류: %s", exc)

    def _get_simulation_status(self) -> tuple[int, bool]:
        ui = self.ui
        try:
            if getattr(ui, "sim_monitor", None):
                status = ui.sim_monitor.get_status()
                return status.current_tick, status.is_running
            if ui.vo_client:
                status = ui.vo_client.get_simulation_status()
                return status.current_tick, status.is_running
            return 0, False
        except Exception as exc:  # pragma: no cover
            logger.debug("시뮬레이션 상태 조회 실패: %s", exc)
            return 0, False

    def _load_from_cache(self, persona_key: str) -> None:
        ui = self.ui
        try:
            logger.info("📂 캐시 로드 시작: persona_key=%s", persona_key)
            logger.info("📊 현재 캐시 키 목록: %s", list(ui._persona_cache.keys()))

            cached_data = ui._persona_cache.get(persona_key, {})
            if not cached_data:
                logger.warning("⚠️ 캐시에 데이터가 없음: %s", persona_key)
                logger.warning("⚠️ 사용 가능한 캐시 키: %s", list(ui._persona_cache.keys()))
                return

            messages = cached_data.get("messages", [])
            if messages:
                ui.collected_messages = messages
                if hasattr(ui.assistant, "collected_messages"):
                    ui.assistant.collected_messages = messages
                if hasattr(ui, "_register_known_messages"):
                    ui._register_known_messages(messages)
                logger.info("📨 캐시에서 메시지 복원: %d개", len(messages))

            cached_todos = cached_data.get("todos", [])
            if cached_todos:
                logger.info("📋 캐시된 TODO 발견: %d개", len(cached_todos))
                self._clear_todos_for_persona_change()
                self._restore_todos_from_cache(cached_todos)
            else:
                logger.info("📋 캐시된 TODO가 없어 새로 분석 시작")
                self._clear_todos_for_persona_change()
                self._trigger_background_analysis(messages)

            analysis_results = cached_data.get("analysis_results", [])
            if analysis_results:
                ui.analysis_results = analysis_results
                if hasattr(ui, "analysis_result_panel"):
                    ui.analysis_result_panel.update_analysis(
                        ui.analysis_results,
                        messages,
                    )
                logger.info("📊 캐시에서 분석 결과 복원: %d개", len(analysis_results))

            self._update_ui_from_cache_only(messages)
            logger.info(
                "✅ 캐시에서 데이터 로드 완료: 메시지 %d개, TODO %d개, 분석 %d개",
                len(messages),
                len(cached_todos),
                len(analysis_results),
            )
        except Exception as exc:  # pragma: no cover
            logger.error("❌ 캐시 로드 오류: %s", exc, exc_info=True)

    def _collect_and_cache_data(self, persona_key: str) -> None:
        ui = self.ui
        if self._collect_in_progress:
            if persona_key == self._active_collection_persona:
                logger.info("⏳ 이미 동일 페르소나(%s)에 대한 수집이 진행 중입니다.", persona_key)
            else:
                self._pending_persona_key = persona_key
                logger.info(
                    "⏳ 다른 페르소나 수집이 진행 중이라 %s 요청을 대기열에 추가했습니다.",
                    persona_key,
                )
            return
 
        self._collect_in_progress = True
        self._active_collection_persona = persona_key
        start_ts = time.time()

        try:
            logger.info("📥 데이터 수집 시작: persona_key=%s", persona_key)
            self._clear_todos_for_persona_change()

            data_source = ui.assistant.data_source_manager.current_source
            if not data_source:
                logger.warning("⚠️ 데이터 소스가 없음")
                return

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                collect_options: Dict[str, Any] = {"incremental": False, "parallel": True}
                if getattr(ui, "data_source_type", None) == "virtualoffice":
                    email_limit = getattr(ui, "quick_collect_email_limit", DEFAULT_EMAIL_LIMIT)
                    messenger_limit = getattr(ui, "quick_collect_messenger_limit", DEFAULT_MESSENGER_LIMIT)
                    overall_limit = getattr(ui, "quick_collect_overall_limit", DEFAULT_OVERALL_LIMIT)
                    collect_options.update(
                        {
                            "email_limit": email_limit,
                            "messenger_limit": messenger_limit,
                            "overall_limit": overall_limit,
                        }
                    )
                    logger.info(
                        "📉 빠른 분석 수집 제한: email<=%s, messenger<=%s, total<=%s",
                        email_limit,
                        messenger_limit,
                        overall_limit,
                    )
                if ui.time_filter_service.is_enabled:
                    time_params = ui.time_filter_service.get_collection_params()
                    if time_params.get("time_filter_enabled"):
                        collect_options["time_range"] = {
                            "start": ui.time_filter_service.current_range[0],
                            "end": ui.time_filter_service.current_range[1],
                        }
                        logger.info("⏰ 시간 범위로 데이터 수집: %s", collect_options["time_range"])

                messages = loop.run_until_complete(
                    data_source.collect_messages(collect_options)
                )
                logger.info("📨 메시지 수집 완료: %d개", len(messages))

                is_active_persona = persona_key == getattr(ui, "_current_persona_id", None)
                persona_info = ui.selected_persona.__dict__ if ui.selected_persona else {}
                cache_data = {
                    "messages": messages,
                    "timestamp": time.time(),
                    "persona": persona_info,
                    "todos": [],
                    "analysis_results": [],
                }
                ui._persona_cache[persona_key] = cache_data
                ui._cache_valid_until[persona_key] = time.time() + 300

                logger.info(
                    "💾 임시 캐시 저장 완료: persona_key=%s, 메시지=%d개",
                    persona_key,
                    len(messages),
                )
                logger.info("📊 현재 캐시 키 목록: %s", list(ui._persona_cache.keys()))

                if is_active_persona:
                    ui.collected_messages = messages
                    if hasattr(ui.assistant, "collected_messages"):
                        ui.assistant.collected_messages = messages
                    if hasattr(ui, "_register_known_messages"):
                        ui._register_known_messages(messages)
                    if hasattr(ui, "_message_summary_cache"):
                        ui._message_summary_cache.clear()
                    self._update_ui_with_new_data(messages)
                else:
                    logger.info(
                        "🔁 수집 완료했지만 페르소나가 이미 변경되어 UI 갱신을 생략합니다 (요청=%s, 현재=%s)",
                        persona_key,
                        getattr(ui, "_current_persona_id", None),
                    )

                current_tick, is_running = self._get_simulation_status()
                if current_tick > 0 or ui._last_simulation_tick is None:
                    ui._last_simulation_tick = current_tick
                ui._simulation_running = is_running

                logger.info(
                    "✅ 데이터 수집 및 캐시 저장 완료: %d개 메시지 (%.2f초)",
                    len(messages),
                    time.time() - start_ts,
                )
                if hasattr(ui, "_initial_collection_completed") and not ui._initial_collection_completed:
                    ui._initial_collection_completed = True
                    logger.debug("🎯 첫 전체 수집 완료 플래그 설정")
            finally:
                loop.close()
        except Exception as exc:  # pragma: no cover
            logger.error("❌ 데이터 수집 및 캐시 저장 오류: %s", exc, exc_info=True)
        finally:
            self._collect_in_progress = False
            self._active_collection_persona = None
            next_persona = None
            if self._pending_persona_key and self._pending_persona_key != persona_key:
                next_persona = self._pending_persona_key
                self._pending_persona_key = None
            else:
                self._pending_persona_key = None
            if next_persona:
                logger.info("▶️ 대기중이던 페르소나 수집을 재시작합니다: %s", next_persona)
                self._collect_and_cache_data(next_persona)

    def _update_cache_with_analysis_results(
        self,
        todos: List[Dict[str, Any]],
        analysis_results: List[Dict[str, Any]],
        incremental: bool = False,
    ) -> None:
        ui = self.ui
        try:
            persona_key = ui._current_persona_id
            if persona_key in ui._persona_cache:
                cache_data = ui._persona_cache[persona_key]
                existing_todos = cache_data.get("todos", [])
                existing_analysis = cache_data.get("analysis_results", [])

                merged_todos = (
                    self._merge_todo_lists(existing_todos, todos)
                    if incremental
                    else list(todos or [])
                )
                merged_analysis = (
                    self._merge_analysis_results(existing_analysis, analysis_results)
                    if incremental
                    else list(analysis_results or [])
                )

                cache_data["todos"] = merged_todos
                cache_data["analysis_results"] = merged_analysis
                ui._persona_cache[persona_key] = cache_data
                ui._cache_valid_until[persona_key] = time.time() + 300
                logger.info("💾 구 캐시 데이터 업데이트 완료: persona_key=%s", persona_key)
            else:
                merged_todos = list(todos or [])
                merged_analysis = list(analysis_results or [])

            from src.services.persona_todo_cache_service import CachedAnalysisResult

            cache_key = self._build_cache_key()
            cached_result = CachedAnalysisResult(
                cache_key=cache_key.to_hash(),
                persona_id=ui._current_persona_id or "",
                todo_list=merged_todos,
                messages=ui.collected_messages,
                analysis_summary={
                    "todo_count": len(merged_todos),
                    "analysis_count": len(merged_analysis),
                },
                analysis_data=merged_analysis,
                created_at=datetime.now(),
                last_accessed_at=datetime.now(),
            )
            ui._cache_service.put(cache_key, cached_result)
            logger.info(
                "💾 신 캐시 데이터 업데이트 완료: TODO %d개, 분석 %d개",
                len(merged_todos),
                len(merged_analysis),
            )
        except Exception as exc:  # pragma: no cover
            logger.error("❌ 캐시 업데이트 오류: %s", exc, exc_info=True)

    def _update_polling_worker_persona(self, persona) -> None:
        ui = self.ui
        try:
            worker = getattr(ui, "polling_worker", None)
            if worker and worker.isRunning():
                logger.info("PollingWorker 페르소나 업데이트 시작")
                if hasattr(worker, "set_persona"):
                    worker.set_persona(persona)
                    logger.info("✅ PollingWorker 페르소나 업데이트: %s", persona)
                elif hasattr(worker, "data_source") and hasattr(worker.data_source, "set_selected_persona"):
                    persona_dict = persona.__dict__ if hasattr(persona, "__dict__") else persona
                    worker.data_source.set_selected_persona(persona_dict)
                    logger.info("✅ PollingWorker 데이터 소스 페르소나 업데이트")
                else:
                    logger.warning("⚠️ PollingWorker 데이터 소스가 페르소나 업데이트를 지원하지 않음 → 재시작")
                    self._restart_polling_worker()
            else:
                logger.info("PollingWorker가 실행되지 않음 → 시작")
                self._start_polling_worker()
        except Exception as exc:  # pragma: no cover
            logger.error("PollingWorker 페르소나 업데이트 오류: %s", exc)

    def _restart_polling_worker(self) -> None:
        ui = self.ui
        try:
            worker = getattr(ui, "polling_worker", None)
            if worker and worker.isRunning():
                logger.info("PollingWorker 재시작 중...")
                worker.stop()
                worker.wait(2000)
            self._start_polling_worker()
        except Exception as exc:  # pragma: no cover
            logger.error("PollingWorker 재시작 오류: %s", exc)

    def _start_polling_worker(self) -> None:
        ui = self.ui
        try:
            data_source = ui.assistant.data_source_manager.current_source
            if data_source:
                current_tick, is_running = self._get_simulation_status()
                polling_interval = 30 if is_running else 60
                ui.polling_worker = PollingWorker(data_source, polling_interval=polling_interval)
                ui.polling_worker.new_data_received.connect(ui.on_new_data_received)
                ui.polling_worker.error_occurred.connect(ui.on_polling_error)
                ui.polling_worker.start()
                logger.info("✅ PollingWorker 시작됨 (폴링 간격: %d초)", polling_interval)
        except Exception as exc:  # pragma: no cover
            logger.error("PollingWorker 시작 오류: %s", exc)

    def _update_ui_from_cache(self, cached_data: Dict[str, Any]) -> None:
        try:
            messages = cached_data.get("messages", [])
            self._update_ui_with_new_data(messages)
            logger.debug("UI 캐시 업데이트 완료")
        except Exception as exc:  # pragma: no cover
            logger.error("UI 캐시 업데이트 오류: %s", exc)

    def _update_ui_from_cache_only(self, messages: List[Dict[str, Any]]) -> None:
        ui = self.ui
        try:
            logger.info("🔄 UI 업데이트 시작: %d개 메시지", len(messages))

            if hasattr(ui, "email_panel"):
                email_messages = [m for m in messages if m.get("type") == "email"]
                ui.email_panel.update_emails(email_messages)
                logger.debug("이메일 패널 업데이트: %d개", len(email_messages))

            if hasattr(ui, "message_summary_panel"):
                ui._update_message_summaries("day")
                logger.debug("메시지 요약 패널 업데이트")

            if hasattr(ui, "timeline_list"):
                self._update_timeline_with_badges()
                logger.debug("타임라인 업데이트")

            if hasattr(ui, "analysis_result_panel") and hasattr(ui, "analysis_results"):
                ui.analysis_result_panel.update_analysis(ui.analysis_results, messages)
                logger.debug("분석 결과 패널 업데이트")

            logger.info("✅ UI 업데이트 완료")
        except Exception as exc:  # pragma: no cover
            logger.error("UI 업데이트 오류: %s", exc)

    def _update_ui_with_new_data(self, messages: List[Dict[str, Any]]) -> None:
        ui = self.ui
        try:
            logger.info("🔄 UI 업데이트 시작: %d개 메시지", len(messages))
            try:
                ui._update_time_range_selector_data_range(messages)
            except Exception as exc:  # pragma: no cover
                logger.debug("TimeRangeSelector 데이터 범위 설정 오류: %s", exc)

            if hasattr(ui, "email_panel"):
                email_messages = [m for m in messages if m.get("type") == "email"]
                ui.email_panel.update_emails(email_messages)
                logger.debug("이메일 패널 업데이트: %d개", len(email_messages))

            if hasattr(ui, "message_summary_panel"):
                ui._update_message_summaries("day")
                logger.debug("메시지 요약 패널 업데이트")

            if hasattr(ui, "timeline_list"):
                self._update_timeline_with_badges()
                logger.debug("타임라인 업데이트")

            if hasattr(ui, "analysis_result_panel") and hasattr(ui, "analysis_results"):
                ui.analysis_result_panel.update_analysis(ui.analysis_results, messages)
                logger.debug("분석 결과 패널 업데이트")

            if messages:
                self._trigger_background_analysis(messages)

            logger.info("✅ UI 업데이트 완료")
        except Exception as exc:  # pragma: no cover
            logger.error("UI 업데이트 오류: %s", exc)

    def _trigger_background_analysis(self, messages: List[Dict[str, Any]]) -> None:
        try:
            logger.info("⚡ 즉시 분석 시작: %d개 메시지", len(messages))
            self._quick_analysis(messages)
            if messages:
                ui = self.ui
                worker = getattr(ui, "worker_thread", None)
                if worker and worker.isRunning():
                    logger.info("🧵 기존 백그라운드 워커가 실행 중이라 새 작업을 생략")
                else:
                    logger.info("🧵 빠른 분석 이후 백그라운드 워커 스레드 즉시 시작")
                    self._process_new_messages_async(list(messages))
        except Exception as exc:  # pragma: no cover
            logger.error("백그라운드 분석 트리거 오류: %s", exc)

    def _quick_analysis(self, messages: List[Dict[str, Any]]) -> None:
        ui = self.ui
        try:
            todos: List[Dict[str, Any]] = []
            analysis_count = min(len(messages), 200)
            logger.info("📋 %d개 메시지 분석 시작", analysis_count)

            for i, msg in enumerate(messages[-analysis_count:]):
                content = msg.get("content", "") or msg.get("body", "") or msg.get("subject", "")
                subject = msg.get("subject", "")
                sender = msg.get("sender", "")

                if not content and not subject:
                    continue

                keywords = [
                    "회의",
                    "미팅",
                    "검토",
                    "확인",
                    "완료",
                    "제출",
                    "보고",
                    "테스트",
                    "피드백",
                    "논의",
                    "진행",
                    "상황",
                    "점검",
                    "요청",
                    "승인",
                    "수정",
                    "업데이트",
                    "개발",
                    "디자인",
                ]

                priority = "Low"
                if any(word in content.lower() for word in ["urgent", "긴급", "즉시", "오늘"]):
                    priority = "High"
                elif any(word in content.lower() for word in ["중요", "필수", "반드시"]):
                    priority = "Medium"

                should_create_todo = False
                matched_keyword: Optional[str] = None

                for keyword in keywords:
                    if keyword in content or keyword in subject:
                        should_create_todo = True
                        matched_keyword = keyword
                        break

                if msg.get("type") == "email" and not should_create_todo:
                    should_create_todo = True
                    matched_keyword = "이메일"
                elif msg.get("type") == "messenger" and not should_create_todo and content:
                    should_create_todo = True
                    matched_keyword = "메신저"

                if should_create_todo:
                    title = f"{matched_keyword}: {subject[:60]}" if subject else f"{matched_keyword}: {content[:60]}"
                    todo = {
                        "id": f"quick_{msg.get('msg_id', uuid.uuid4().hex)}_{i}",
                        "title": title,
                        "description": content[:300] if content else subject[:300],
                        "priority": priority,
                        "status": "pending",
                        "created_at": datetime.now().isoformat(),
                        "source_message": json.dumps(msg, ensure_ascii=False) if isinstance(msg, dict) else str(msg),
                        "requester": sender,
                        "type": msg.get("type", "message"),
                        "quick_analysis": True,
                    }
                    todos.append(todo)

            if todos and hasattr(ui, "todo_panel"):
                # 빠른 분석은 전체 교체 모드로 동작 (incremental=False)
                # 이때 생성된 모든 TODO는 viewed로 처리됨
                ui.todo_panel.populate_from_items(todos, incremental=False, show_reasoning=False)
                logger.info("✅ 빠른 분석 완료: %d개 TODO 생성", len(todos))
                self._update_cache_with_analysis_results(todos, [])
            else:
                logger.info("ℹ️ 분석 완료: 생성된 TODO 없음 (분석한 메시지: %d개)", analysis_count)
        except Exception as exc:  # pragma: no cover
            logger.error("빠른 분석 오류: %s", exc, exc_info=True)

    def _invalidate_all_cache(self) -> None:
        ui = self.ui
        try:
            ui._persona_cache.clear()
            ui._cache_valid_until.clear()
            if hasattr(ui, "_initial_collection_completed"):
                ui._initial_collection_completed = False
            if hasattr(ui, "_message_summary_cache"):
                ui._message_summary_cache.clear()
            logger.info("🗑️ 모든 캐시 무효화됨 (첫 로드 플래그 보존)")
        except Exception as exc:  # pragma: no cover
            logger.error("캐시 무효화 오류: %s", exc)

    def _force_update_project_tags(self) -> None:
        ui = self.ui
        try:
            if not hasattr(ui, "todo_panel") or not ui.todo_panel:
                return

            repo = getattr(ui.todo_panel, "repository", None)
            todos = repo.fetch_active() if repo else []
            if todos:
                ui.todo_panel.update_project_tags(todos)
                logger.info("🏷️ 프로젝트 태그 강제 업데이트 완료: %d개 TODO", len(todos))
        except Exception as exc:  # pragma: no cover
            logger.error("프로젝트 태그 강제 업데이트 오류: %s", exc)

    def _clear_todos_for_persona_change(self) -> None:
        """페르소나 변경 시 TODO UI 갱신 (DB는 유지, 필터링만 적용)"""
        ui = self.ui
        try:
            if hasattr(ui, "todo_panel") and ui.todo_panel:
                # DB는 삭제하지 않고, UI만 갱신 (필터링은 controller에서 자동 적용)
                ui.todo_panel.refresh_todo_list(preserve_existing_on_empty=False)
                logger.info("🔄 페르소나 변경으로 TODO 리스트 갱신 완료")
        except Exception as exc:  # pragma: no cover
            logger.error("TODO 갱신 오류: %s", exc)

    def _merge_todo_lists(
        self,
        existing: List[Dict[str, Any]],
        new_items: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """기존 TODO 리스트에 새 항목을 병합한다."""
        if not existing:
            return [dict(item) for item in new_items or []]

        merged = [dict(item) for item in existing]
        index_by_id: Dict[str, int] = {
            item.get("id"): idx for idx, item in enumerate(merged) if item.get("id")
        }

        for item in new_items or []:
            item_copy = dict(item)
            todo_id = item_copy.get("id")
            if not todo_id:
                todo_id = item_copy["id"] = uuid.uuid4().hex

            if todo_id in index_by_id:
                idx = index_by_id[todo_id]
                merged[idx] = {**merged[idx], **item_copy}
            else:
                index_by_id[todo_id] = len(merged)
                merged.append(item_copy)

        return merged

    def _merge_analysis_results(
        self,
        existing: List[Dict[str, Any]],
        new_items: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        if not existing:
            return [dict(item) for item in new_items or []]

        merged = [dict(item) for item in existing]
        index_by_key: Dict[str, int] = {}
        for idx, item in enumerate(merged):
            key = self._analysis_result_key(item)
            if key:
                index_by_key[key] = idx

        for item in new_items or []:
            item_copy = dict(item)
            key = self._analysis_result_key(item_copy)
            if key and key in index_by_key:
                idx = index_by_key[key]
                merged[idx] = {**merged[idx], **item_copy}
            else:
                merged.append(item_copy)
                if key:
                    index_by_key[key] = len(merged) - 1

        return merged

    @staticmethod
    def _analysis_result_key(item: Dict[str, Any]) -> Optional[str]:
        return item.get("id") or item.get("title")

    def _restore_todos_from_cache(self, cached_todos: List[Dict[str, Any]]) -> None:
        ui = self.ui
        try:
            if not hasattr(ui, "todo_panel") or not ui.todo_panel:
                return
            if not cached_todos:
                logger.info("ℹ️ 복원할 캐시된 TODO가 없음")
                return

            logger.info("🔄 TODO 복원 시작: %d개", len(cached_todos))
            ui.todo_panel.populate_from_items(cached_todos)
            logger.info("🖥️ TODO UI 표시 완료: %d개", len(cached_todos))

            self._force_update_project_tags()
            logger.info("✅ 캐시된 TODO 복원 완료: %d개", len(cached_todos))
        except Exception as exc:  # pragma: no cover
            logger.error("❌ 캐시된 TODO 복원 오류: %s", exc, exc_info=True)

    def _show_visual_notification(self) -> None:
        ui = self.ui
        try:
            targets = []
            if hasattr(ui, "message_summary_panel"):
                targets.append(ui.message_summary_panel)
            if hasattr(ui, "email_panel"):
                targets.append(ui.email_panel)
            for widget in targets:
                ui.notification_manager.register_widget(widget, "visual")
                ui.notification_manager.show_notification(widget, duration_ms=250)
        except Exception as exc:  # pragma: no cover
            logger.error("시각적 알림 표시 오류: %s", exc)

    def _show_progress_bar(self, message: str = "처리 중...") -> None:
        ui = self.ui
        try:
            from PyQt6.QtWidgets import QProgressBar

            if ui._progress_bar and ui._progress_bar.isVisible():
                return

            if not ui._progress_bar:
                ui._progress_bar = QProgressBar()
                ui._progress_bar.setRange(0, 100)
                ui._progress_bar.setTextVisible(True)
                ui._progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
                ui._progress_bar.setStyleSheet(
                    """
                    QProgressBar {
                        border: 2px solid #3498db;
                        border-radius: 5px;
                        text-align: center;
                        background-color: #ecf0f1;
                        height: 25px;
                    }
                    QProgressBar::chunk {
                        background-color: #3498db;
                        border-radius: 3px;
                    }
                    """
                )

            if not ui._progress_label:
                ui._progress_label = QLabel()
                ui._progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                ui._progress_label.setStyleSheet(
                    """
                    QLabel {
                        color: #2c3e50;
                        font-weight: bold;
                        padding: 5px;
                    }
                    """
                )

            ui._progress_label.setText(message)
            ui.statusBar().addWidget(ui._progress_label, 1)
            ui.statusBar().addWidget(ui._progress_bar, 2)
            ui._progress_bar.setValue(0)
            QApplication.processEvents()
            logger.debug("프로그레스 바 표시: %s", message)
        except Exception as exc:  # pragma: no cover
            logger.error("프로그레스 바 표시 오류: %s", exc)

    def _update_progress_bar(self, value: int) -> None:
        ui = self.ui
        try:
            if ui._progress_bar and ui._progress_bar.isVisible():
                ui._progress_bar.setValue(value)
                QApplication.processEvents()
                logger.debug("프로그레스 바 업데이트: %d%%", value)
        except Exception as exc:  # pragma: no cover
            logger.error("프로그레스 바 업데이트 오류: %s", exc)

    def _hide_progress_bar(self) -> None:
        ui = self.ui
        try:
            if ui._progress_bar and ui._progress_bar.isVisible():
                ui.statusBar().removeWidget(ui._progress_bar)
                ui._progress_bar.setVisible(False)
            if ui._progress_label and ui._progress_label.isVisible():
                ui.statusBar().removeWidget(ui._progress_label)
                ui._progress_label.setVisible(False)
            QApplication.processEvents()
            logger.debug("프로그레스 바 숨김")
        except Exception as exc:  # pragma: no cover
            logger.error("프로그레스 바 숨김 오류: %s", exc)

    def _update_timeline_with_badges(self) -> None:
        ui = self.ui
        try:
            if not hasattr(ui, "timeline_list"):
                return
            ui.update_timeline(ui.collected_messages)
            QTimer.singleShot(3000, ui._clear_new_message_ids)
        except Exception as exc:  # pragma: no cover
            logger.error("타임라인 업데이트 오류: %s", exc)
