# -*- coding: utf-8 -*-
"""
데이터 수집 및 재분석 컨트롤러

메인 윈도우에서 분리한 메시지 수집/분석 관련 책임을 관리합니다.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional, TYPE_CHECKING

from PyQt6.QtWidgets import QMessageBox

from src.ui.widgets import WorkerThread

logger = logging.getLogger(__name__)

if TYPE_CHECKING:  # pragma: no cover
    from src.ui.main_window import SmartAssistantGUI


class DataRefreshController:
    """SmartAssistant 데이터 수집 및 갱신 담당 컨트롤러."""

    def __init__(self, ui: "SmartAssistantGUI") -> None:
        self.ui = ui

    # ------------------------------------------------------------------
    # 데이터 수집 관련
    # ------------------------------------------------------------------
    def start_collection(self) -> None:
        """메시지/분석 수집을 시작한다."""
        ui = self.ui
        if ui.worker_thread and ui.worker_thread.isRunning():
            return

        dataset_config = dict(ui.dataset_config)
        collect_options = dict(ui.collect_options)
        collect_options["force_reload"] = True
        dataset_config["force_reload"] = dataset_config.get("force_reload", False) or True

        ui.connect_collect_button.setEnabled(False)
        ui.progress_bar.setVisible(True)
        ui.progress_bar.setValue(0)

        ui.worker_thread = WorkerThread(ui.assistant, dataset_config, collect_options)
        ui.worker_thread.progress_updated.connect(ui.progress_bar.setValue)
        ui.worker_thread.status_updated.connect(ui.status_message.setText)
        ui.worker_thread.result_ready.connect(self.handle_result)
        ui.worker_thread.error_occurred.connect(self.handle_error)
        ui.worker_thread.start()

        ui.dataset_config["force_reload"] = False
        ui.collect_options["force_reload"] = False

    def stop_collection(self) -> None:
        """진행 중인 수집을 중단한다."""
        ui = self.ui
        if ui.worker_thread and ui.worker_thread.isRunning():
            ui.worker_thread.stop()
            ui.worker_thread.wait(3000)

        ui.connect_collect_button.setEnabled(True)
        ui.progress_bar.setVisible(False)
        ui.status_message.setText("수집 중지됨")

    # ------------------------------------------------------------------
    # 결과 처리 및 오류 대응
    # ------------------------------------------------------------------
    def handle_result(self, result: Dict[str, Any]) -> None:
        """워커 스레드에서 반환한 결과를 UI에 반영한다."""
        ui = self.ui
        ui.connect_collect_button.setEnabled(True)
        ui.progress_bar.setVisible(False)
        ui.status_message.setText("수집 완료")

        if not result.get("success"):
            QMessageBox.critical(ui, "오류", "수집 중 오류가 발생했습니다.")
            return

        todo_list = result.get("todo_list") or {}
        items = todo_list.get("items", [])
        if items:
            if hasattr(ui, "todo_panel"):
                ui.todo_panel.populate_from_items(items)
        else:
            if hasattr(ui, "status_message"):
                ui.status_message.setText("이번 수집에서 새로운 TODO가 없어 이전 목록을 유지합니다.")

        messages = result.get("messages", [])
        ui.collected_messages = list(messages)
        if hasattr(ui, "_register_known_messages"):
            ui._register_known_messages(messages)

        self._update_time_range(messages)
        ui._update_message_summaries("day")

        if hasattr(ui, "message_table"):
            ui.update_message_table(messages)
        if hasattr(ui, "message_summary_label"):
            ui._update_message_summary(messages)
        ui.update_timeline(messages)

        analysis_results = result.get("analysis_results") or []
        ui.analysis_results = analysis_results

        if hasattr(ui, "analysis_result_panel"):
            ui.analysis_result_panel.update_analysis(analysis_results, messages)

        if hasattr(ui, "email_panel"):
            ui.email_panel.update_emails(messages, items)

        ui._save_to_cache(items, messages, analysis_results)

        total = len(items)
        ui.status_bar.showMessage(f"수집 완료: {total}개 TODO 생성")
        self.auto_save_results(result)

    def handle_error(self, error_message: str) -> None:
        """스레드 오류를 사용자에게 알린다."""
        ui = self.ui
        ui.connect_collect_button.setEnabled(True)
        ui.progress_bar.setVisible(False)
        ui.status_message.setText("오류 발생")
        QMessageBox.critical(ui, "오류", error_message)

    # ------------------------------------------------------------------
    # 보조 동작
    # ------------------------------------------------------------------
    def auto_refresh(self) -> None:
        """온라인 모드일 때 자동 수집을 수행한다."""
        ui = self.ui
        if ui.current_status == "online" and not ui.worker_thread:
            self.start_collection()

    def auto_save_results(self, result: Dict[str, Any]) -> None:
        """간단한 JSON 백업을 남긴다."""
        try:
            filename = f"gui_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, "w", encoding="utf-8") as fp:
                json.dump(result, fp, ensure_ascii=False, indent=2)
        except Exception as exc:  # pragma: no cover
            logger.warning("자동 저장 실패: %s", exc)

    # ------------------------------------------------------------------
    # 내부 유틸
    # ------------------------------------------------------------------
    def _update_time_range(self, messages: list[Dict[str, Any]]) -> None:
        """수집한 메시지의 시간 범위를 UI에 반영.

        시뮬레이션 시간이 있으면 이를 우선 사용하고,
        없으면 기존 date 필드를 사용한다.
        """
        ui = self.ui
        if not messages or not hasattr(ui, "time_range_selector"):
            return

        dates: list[datetime] = []
        for msg in messages:
            # 시뮬레이션 시간이 있으면 우선 사용
            raw_value: Optional[str] = (
                msg.get("simulated_datetime")
                or (msg.get("metadata") or {}).get("simulated_datetime")
                or msg.get("date")
            )
            if not raw_value:
                continue
            try:
                dt = datetime.fromisoformat(str(raw_value).replace("Z", "+00:00"))
            except Exception:
                continue
            dates.append(dt)

        if not dates:
            return

        data_start = min(dates)
        data_end = max(dates)
        ui.time_range_selector.set_data_range(data_start, data_end)
        logger.info(
            "데이터 시간 범위 설정(시뮬레이션 기준): %s ~ %s",
            data_start.strftime("%Y-%m-%d %H:%M"),
            data_end.strftime("%Y-%m-%d %H:%M"),
        )
