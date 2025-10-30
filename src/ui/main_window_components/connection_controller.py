# -*- coding: utf-8 -*-
"""
VirtualOffice 연결 및 시뮬레이션 제어 컨트롤러

`SmartAssistantGUI`에서 분리된 연결 관련 책임을 담당합니다.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, List

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication, QMessageBox

from src.integrations.polling_worker import PollingWorker
from src.integrations.simulation_monitor import SimulationMonitor
from src.integrations.virtualoffice_client import VirtualOfficeClient

if TYPE_CHECKING:  # pragma: no cover - 순환 참조 방지용 힌트
    from src.integrations.models import PersonaInfo
    from src.ui.main_window import SmartAssistantGUI

logger = logging.getLogger(__name__)


class VirtualOfficeConnectionController:
    """VirtualOffice 연결과 관련된 상호작용을 담당."""

    def __init__(self, ui: "SmartAssistantGUI") -> None:
        self.ui = ui

    # ------------------------------------------------------------------
    # 공개 API
    # ------------------------------------------------------------------
    def connect_virtualoffice(self) -> None:
        """VirtualOffice 서버에 연결하고 초기 준비를 수행."""
        ui = self.ui
        try:
            self._prepare_connection()
            ui.vo_client = self._create_vo_client()
            personas = self._fetch_personas()
            sim_status = self._setup_simulation_monitoring()
            self._setup_polling_worker()
            self._finalize_connection(personas, sim_status)
        except Exception as exc:
            self._handle_connection_error(exc)
        finally:
            ui.connect_collect_button.setEnabled(True)

    def update_sim_status_display(self, sim_status: Any) -> None:
        """시뮬레이션 상태 표시에 대한 외부 업데이트."""
        self._update_sim_status_display(sim_status)

    def setup_personas(self, personas: List["PersonaInfo"]) -> None:
        """페르소나 드롭다운 초기화."""
        self._setup_personas(personas)

    def show_connection_success_dialog(
        self, personas: List["PersonaInfo"], sim_status: Any
    ) -> None:
        """연결 성공 다이얼로그 직접 요청 시 사용."""
        self._show_connection_success_dialog(personas, sim_status)

    # ------------------------------------------------------------------
    # 내부 구현
    # ------------------------------------------------------------------
    def _prepare_connection(self) -> None:
        ui = self.ui
        ui.connect_collect_button.setEnabled(False)
        ui.vo_panel.update_connection_status("🔄 연결 중...", "waiting")
        QApplication.processEvents()

    def _create_vo_client(self) -> VirtualOfficeClient:
        ui = self.ui
        server_urls = ui.vo_panel.get_server_urls()
        if not all(server_urls.values()):
            raise ValueError("모든 서버 URL을 입력해주세요.")

        vo_client = VirtualOfficeClient(
            server_urls["email"],
            server_urls["chat"],
            server_urls["sim"],
        )

        logger.info("VirtualOffice 서버 연결 테스트 중...")
        connection_status = vo_client.test_connection()
        if not all(connection_status.values()):
            failed_servers = [k for k, v in connection_status.items() if not v]
            raise ConnectionError(f"일부 서버 연결 실패: {', '.join(failed_servers)}")

        logger.info("✅ 모든 서버 연결 성공")
        return vo_client

    def _fetch_personas(self) -> List["PersonaInfo"]:
        ui = self.ui
        logger.info("페르소나 목록 조회 중...")
        personas = ui.vo_client.get_personas() if ui.vo_client else []

        if not personas:
            raise ValueError("페르소나 목록이 비어있습니다.")

        logger.info("✅ %d개 페르소나 조회 완료", len(personas))
        self._setup_personas(personas)
        return personas

    def _setup_simulation_monitoring(self):
        ui = self.ui
        if not ui.vo_client:
            raise RuntimeError("VirtualOffice 클라이언트가 설정되지 않았습니다.")

        sim_status = ui.vo_client.get_simulation_status()
        self._update_sim_status_display(sim_status)

        logger.info("SimulationMonitor 시작 중...")
        ui.sim_monitor = SimulationMonitor(ui.vo_client)
        ui.sim_monitor.status_updated.connect(ui.on_sim_status_updated)
        ui.sim_monitor.tick_advanced.connect(ui.on_tick_advanced)
        ui.sim_monitor.start_monitoring()
        logger.info("✅ SimulationMonitor 시작됨")
        return sim_status

    def _setup_polling_worker(self) -> None:
        ui = self.ui
        if ui.data_source_type != "virtualoffice" or not ui.selected_persona:
            return

        logger.info("PollingWorker 시작 중...")
        data_source = ui.assistant.data_source_manager.current_source
        if not data_source:
            logger.warning("데이터 소스가 없어 PollingWorker를 시작할 수 없습니다.")
            return

        ui.polling_worker = PollingWorker(data_source, polling_interval=30)
        ui.polling_worker.new_data_received.connect(ui.on_new_data_received)
        ui.polling_worker.error_occurred.connect(ui.on_polling_error)
        ui.polling_worker.start()
        logger.info("✅ PollingWorker 시작됨 (폴링 간격: 30초)")

    def _finalize_connection(self, personas, sim_status) -> None:
        ui = self.ui
        self._update_connection_ui(personas)
        ui._save_vo_config()
        self._show_connection_success_dialog(personas, sim_status)

        logger.info("🚀 연결 성공 - 1초 후 자동 분석 시작")
        QTimer.singleShot(1000, ui._auto_start_analysis)

    def _update_connection_ui(self, personas) -> None:
        ui = self.ui
        success_text = f"✅ 연결 성공 ({len(personas)}개 페르소나)"
        success_style = """
            QLabel {
                color: #059669; background-color: #D1FAE5; padding: 6px;
                border-radius: 4px; font-size: 11px; font-weight: 600;
            }
        """

        if hasattr(ui, "vo_connection_status_label"):
            ui.vo_connection_status_label.setText(success_text)
            ui.vo_connection_status_label.setStyleSheet(success_style)

        if hasattr(ui, "tick_history_btn"):
            ui.tick_history_btn.setEnabled(True)

        logger.info("✅ 연결 상태 레이블 업데이트: %d개 페르소나", len(personas))

    def _show_connection_success_dialog(self, personas, sim_status) -> None:
        ui = self.ui
        QMessageBox.information(
            ui,
            "연결 성공",
            (
                "VirtualOffice 서버에 성공적으로 연결되었습니다.\n\n"
                f"페르소나: {len(personas)}개\n"
                f"현재 틱: {getattr(sim_status, 'current_tick', '?')}\n"
                f"시뮬레이션 시간: {getattr(sim_status, 'sim_time', '?')}"
            ),
        )

    def _handle_connection_error(self, error: Exception) -> None:
        ui = self.ui
        logger.error("❌ VirtualOffice 연결 실패: %s", error, exc_info=True)
        ui.vo_panel.update_connection_status(f"❌ 연결 실패: {str(error)}", "disconnected")
        QMessageBox.critical(
            ui,
            "연결 오류",
            "VirtualOffice 서버 연결에 실패했습니다.\n\n오류: {0}".format(str(error)),
        )

    def _setup_personas(self, personas) -> None:
        ui = self.ui
        ui.persona_combo.clear()
        ui.persona_combo.setEnabled(True)

        for persona in personas:
            display_name = f"{persona.name} ({persona.role})"
            ui.persona_combo.addItem(display_name, persona)

        pm_index = -1
        for i in range(ui.persona_combo.count()):
            persona = ui.persona_combo.itemData(i)
            if persona and (
                "pm" in persona.name.lower() or "pm" in persona.role.lower()
            ):
                pm_index = i
                break

        if pm_index >= 0:
            ui.persona_combo.setCurrentIndex(pm_index)
            logger.info("✅ PM 페르소나 자동 선택: %s", ui.persona_combo.currentText())
        else:
            ui.persona_combo.setCurrentIndex(0)
            logger.info(
                "⚠️ PM 페르소나를 찾을 수 없어 첫 번째 페르소나 선택: %s",
                ui.persona_combo.currentText(),
            )

    def _update_sim_status_display(self, sim_status: Any) -> None:
        ui = self.ui
        status_text = (
            f"Tick: {getattr(sim_status, 'current_tick', '?')}\n"
            f"시간: {getattr(sim_status, 'sim_time', '?')}\n"
            f"상태: {'실행 중' if getattr(sim_status, 'is_running', False) else '정지'}\n"
            f"자동 틱: {'활성화' if getattr(sim_status, 'auto_tick', False) else '비활성화'}"
        )
        ui.sim_status_display.setText(status_text)

        if getattr(sim_status, "is_running", False):
            ui.sim_status_display.setStyleSheet(
                """
                QLabel {
                    color: #059669;
                    background-color: #D1FAE5;
                    padding: 8px;
                    border-radius: 4px;
                    border: 1px solid #10B981;
                    font-size: 11px;
                }
            """
            )
        else:
            ui.sim_status_display.setStyleSheet(
                """
                QLabel {
                    color: #DC2626;
                    background-color: #FEE2E2;
                    padding: 8px;
                    border-radius: 4px;
                    border: 1px solid #EF4444;
                    font-size: 11px;
                }
            """
            )
