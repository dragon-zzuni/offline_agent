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


class AnalysisCacheController:
    """메시지 분석 및 캐시 관리를 담당하는 컨트롤러."""

    def __init__(self, ui: "SmartAssistantGUI") -> None:
        self.ui = ui

    # ------------------------------------------------------------------
    # 백그라운드 분석
    # ------------------------------------------------------------------
    def _process_new_messages_async(self, new_messages: List[Dict[str, Any]]) -> None:
        """새 메시지를 비동기로 분석한다."""
        ui = self.ui
        try:
            if not new_messages:
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
                logger.info("🔍 추출된 TODO 개수: %d", len(todos))

                if todos and hasattr(ui, "todo_panel"):
                    ui.todo_panel.populate_from_items(todos)
                    logger.info("✅ 백그라운드 분석 완료: %d개 TODO 생성", len(todos))
                    self._update_cache_with_analysis_results(todos, [])
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
            else:
                error_msg = result.get("error", "알 수 없는 오류")
                logger.error("❌ 백그라운드 분석 실패: %s", error_msg)
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
                    ui.todo_panel.populate_from_items(items)
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

            if cached_result.todo_list and hasattr(ui, "todo_panel"):
                logger.info("📋 TODO 업데이트: %d개", len(cached_result.todo_list))
                ui.todo_panel.populate_from_items(cached_result.todo_list)

            if cached_result.messages:
                ui.collected_messages = cached_result.messages
                if hasattr(ui.assistant, "collected_messages"):
                    ui.assistant.collected_messages = cached_result.messages
                logger.info("📨 메시지 복원: %d개", len(cached_result.messages))

            if cached_result.analysis_summary and hasattr(ui, "analysis_result_panel"):
                logger.info("📊 분석 결과 표시")

            todo_count = len(cached_result.todo_list)
            msg_count = len(cached_result.messages)
            ui.statusBar().showMessage(
                "✅ 캐시에서 로드 완료: TODO {0}개, 메시지 {1}개 (생성: {2})".format(
                    todo_count,
                    msg_count,
                    cached_result.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                ),
                5000,
            )
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
                created_at=datetime.now(),
                last_accessed_at=datetime.now(),
            )

            ui._cache_service.put(cache_key, cached_result)
            logger.info("💾 캐시 저장 완료: TODO %d개, 메시지 %d개", len(todo_list), len(messages))
        except Exception as exc:  # pragma: no cover
            logger.error("❌ 캐시 저장 오류: %s", exc, exc_info=True)

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
                collect_options: Dict[str, Any] = {"incremental": False}
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

                ui.collected_messages = messages
                if hasattr(ui.assistant, "collected_messages"):
                    ui.assistant.collected_messages = messages

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

                self._update_ui_with_new_data(messages)

                current_tick, is_running = self._get_simulation_status()
                if current_tick > 0 or ui._last_simulation_tick is None:
                    ui._last_simulation_tick = current_tick
                ui._simulation_running = is_running

                logger.info("✅ 데이터 수집 및 캐시 저장 완료: %d개 메시지", len(messages))
            finally:
                loop.close()
        except Exception as exc:  # pragma: no cover
            logger.error("❌ 데이터 수집 및 캐시 저장 오류: %s", exc, exc_info=True)

    def _update_cache_with_analysis_results(
        self,
        todos: List[Dict[str, Any]],
        analysis_results: List[Dict[str, Any]],
    ) -> None:
        ui = self.ui
        try:
            persona_key = ui._current_persona_id
            if persona_key in ui._persona_cache:
                cache_data = ui._persona_cache[persona_key]
                cache_data["todos"] = todos
                cache_data["analysis_results"] = analysis_results
                ui._persona_cache[persona_key] = cache_data
                ui._cache_valid_until[persona_key] = time.time() + 300
                logger.info("💾 구 캐시 데이터 업데이트 완료: persona_key=%s", persona_key)

            from src.services.persona_todo_cache_service import CachedAnalysisResult

            cache_key = self._build_cache_key()
            cached_result = CachedAnalysisResult(
                cache_key=cache_key.to_hash(),
                persona_id=ui._current_persona_id or "",
                todo_list=todos,
                messages=ui.collected_messages,
                analysis_summary={
                    "todo_count": len(todos),
                    "analysis_count": len(analysis_results),
                },
                created_at=datetime.now(),
                last_accessed_at=datetime.now(),
            )
            ui._cache_service.put(cache_key, cached_result)
            logger.info(
                "💾 신 캐시 데이터 업데이트 완료: TODO %d개, 분석 %d개",
                len(todos),
                len(analysis_results),
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
        except Exception as exc:  # pragma: no cover
            logger.error("백그라운드 분석 트리거 오류: %s", exc)

    def _quick_analysis(self, messages: List[Dict[str, Any]]) -> None:
        ui = self.ui
        try:
            todos: List[Dict[str, Any]] = []
            analysis_count = min(len(messages), 50)
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
                ui.todo_panel.populate_from_items(todos)
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
        ui = self.ui
        try:
            if hasattr(ui, "todo_panel") and ui.todo_panel:
                ui.todo_panel.clear_all_todos_silent()
                ui.todo_panel.todo_list.clear()
                logger.info("🗑️ 페르소나 변경으로 TODO 데이터베이스 초기화 완료")
        except Exception as exc:  # pragma: no cover
            logger.error("TODO 초기화 오류: %s", exc)

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
            central_widget = ui.centralWidget()
            if central_widget:
                ui.notification_manager.register_widget(central_widget, "flash")
                ui.notification_manager.show_notification(central_widget, interval_ms=250)
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
