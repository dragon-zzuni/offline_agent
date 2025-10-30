# -*- coding: utf-8 -*-
"""
Smart Assistant 메인 GUI 윈도우
"""
import sys
import os
import asyncio
import json
import logging
import sqlite3
import time

from typing import Dict, List, Optional, Any
from pathlib import Path

from datetime import datetime, timezone, timedelta
from collections import Counter
import uuid, json, sqlite3

# 로거 초기화
logger = logging.getLogger(__name__)

# 서비스 import
from ..services.time_filter_service import TimeFilterService
from ..services.vdos_integration_service import VDOSIntegrationService
from ..services.data_collection_service import DataCollectionService

# TODO DB는 VDOS DB와 같은 위치에 저장 (동적으로 설정됨)
TODO_DB_PATH = None  # 초기화 시 설정됨

# Windows 한글 출력 설정
if sys.platform == "win32":
    import io
    try:
        if hasattr(sys.stdout, 'buffer') and not sys.stdout.closed:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        if hasattr(sys.stderr, 'buffer') and not sys.stderr.closed:
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    except (AttributeError, ValueError, OSError):
        pass
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['PYTHONUTF8'] = '1'

# Qt CSS 경고 억제 (box-shadow 등 지원하지 않는 속성)
os.environ['QT_LOGGING_RULES'] = '*.debug=false;qt.qpa.*=false'

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextEdit, QTabWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QGroupBox, QLineEdit, QProgressBar, QStatusBar,
    QFrame, QMessageBox, QStyleFactory, QListWidget, QListWidgetItem,
    QDialog, QDialogButtonBox, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QObject, QEvent
from PyQt6.QtGui import QFont, QPalette, QColor, QFontDatabase

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from main import SmartAssistant, DEFAULT_DATASET_ROOT
from .todo_panel import TodoPanel   # ✅ TodoPanel 사용
from .time_range_selector import TimeRangeSelector  # ✅ TimeRangeSelector 추가
from .message_summary_panel import MessageSummaryPanel  # ✅ MessageSummaryPanel 추가
from .message_detail_dialog import MessageDetailDialog  # ✅ MessageDetailDialog 추가
from .email_panel import EmailPanel  # ✅ EmailPanel 추가
from .analysis_result_panel import AnalysisResultPanel  # ✅ AnalysisResultPanel 추가
from .styles import Colors, Fonts, FontSizes, FontWeights, Spacing, BorderRadius
from utils.datetime_utils import parse_iso_datetime  # ✅ 날짜 파싱 유틸리티
from .main_window_components import (
    VirtualOfficeConnectionController,
    DataRefreshController,
    AnalysisCacheController,
)

# 분리된 패널 import
from .panels import LeftControlPanel, VirtualOfficePanel

# 분리된 다이얼로그 import
from .dialogs.summary_dialog import SummaryDialog

# 분리된 위젯 및 헬퍼 import
from .widgets import WorkerThread

# 서비스 import
from src.services import WeatherService

# VirtualOffice 연동 관련 import
from src.integrations.virtualoffice_client import VirtualOfficeClient
from src.integrations.models import PersonaInfo, VirtualOfficeConfig
from src.integrations.polling_worker import PollingWorker
from src.integrations.simulation_monitor import SimulationMonitor

# 시각적 알림 관련 import
from src.ui.visual_notification import NotificationManager, VisualNotification
from src.ui.tick_history_dialog import TickHistoryDialog

def _init_todo_schema(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.execute("""
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
        deadline_confidence TEXT
    )
    """)
    conn.commit()

# ✅ utils/datetime_utils.py의 parse_iso_datetime 사용으로 대체됨
# def _parse_iso_dt(s: str | None):
#     if not s:
#         return None
#     try:
#         return datetime.fromisoformat(s.replace("Z", "+00:00"))
#     except Exception:
#         try:
#             return datetime.fromisoformat(s)
#         except Exception:
#             return None



def _save_todos_to_db(items: list[dict], db_path=TODO_DB_PATH):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    _init_todo_schema(conn)
    cur = conn.cursor()
    cur.execute("DELETE FROM todos")
    conn.commit()

    # 0) 기본 필드/ID 보정(미리)
    now_iso = datetime.now().isoformat()
    prepared: list[dict] = []
    for t in items:
        t = {**{
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
        }, **(t or {})}

        # ID 없으면 자동 생성
        if not t.get("id"):
            t["id"] = uuid.uuid4().hex

        # evidence가 list면 문자열로, dict면 그대로 list→문자열 변환
        if not isinstance(t.get("evidence"), str):
            t["evidence"] = json.dumps(t.get("evidence") or [], ensure_ascii=False)

        prepared.append(t)

    # 1) 이번 배치에서 Top-3 자동 선정 (이미 is_top3가 True면 존중)
    # 주의: MainWindow의 top3_service를 사용 (이미 VDOS 연동됨)
    # 전역 변수로 접근 (MainWindow 인스턴스가 있을 때만)
    auto_top_ids = set()
    try:
        # MainWindow의 top3_service 사용 시도
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            for widget in app.topLevelWidgets():
                if hasattr(widget, 'top3_service'):
                    auto_top_ids = widget.top3_service.pick_top3([x for x in prepared if not x.get("is_top3")])
                    break
        
        # MainWindow를 찾지 못한 경우 폴백
        if not auto_top_ids:
            from src.services import Top3Service
            from src.utils.vdos_connector import VDOSConnector
            vdos_conn = VDOSConnector()
            top3_service = Top3Service(vdos_connector=vdos_conn)
            auto_top_ids = top3_service.pick_top3([x for x in prepared if not x.get("is_top3")])
    except Exception as e:
        logger.warning(f"Top3 자동 선정 실패: {e}")
        auto_top_ids = set()

    # 2) INSERT/REPLACE
    for t in prepared:
        # source_message가 dict면 직렬화
        if isinstance(t.get("source_message"), dict):
            t["source_message"] = json.dumps(t["source_message"], ensure_ascii=False)

        is_top3_val = (
            1 if t.get("is_top3") in (1, "1", True, "true", "TRUE")
            else (1 if t["id"] in auto_top_ids else 0)
        )

        cur.execute("""
        INSERT OR REPLACE INTO todos
        (id, title, description, priority, deadline, deadline_ts, requester, type, status,
         source_message, created_at, updated_at, snooze_until, is_top3,
         draft_subject, draft_body, evidence, deadline_confidence, recipient_type, source_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            t["id"],
            t["title"],
            t["description"],
            t["priority"],
            t["deadline"],
            t["deadline_ts"],
            t["requester"],
            t["type"],
            t["status"],
            t["source_message"],
            t["created_at"],
            t["updated_at"],
            t["snooze_until"],
            is_top3_val,
            t["draft_subject"],
            t["draft_body"],
            t["evidence"],
            t["deadline_confidence"],
            t.get("recipient_type", "to"),
            t.get("source_type", "메시지"),
        ))

    conn.commit()
    conn.close()

class SmartAssistantGUI(QMainWindow):
    """Smart Assistant 메인 GUI"""
    
    def __init__(self):
        super().__init__()
        self._init_basic_attributes()
        self._init_services()
        self._init_virtualoffice_attributes()
        self._init_cache_system()
        self._init_ui_components()
        self._finalize_initialization()
    
    def _init_basic_attributes(self):
        """기본 속성 초기화"""
        self.assistant = SmartAssistant()
        self.worker_thread = None
        self.current_status = "offline"
        self.dataset_config = {"dataset_root": None, "force_reload": False}
        self.collect_options = {
            "email_limit": None, "messenger_limit": None, 
            "overall_limit": None, "force_reload": True
        }
        self.analysis_results: List[Dict] = []
        self.collected_messages: List[Dict] = []
    
    def _init_services(self):
        """서비스 초기화"""
        # 날씨 서비스
        kma_api_key = os.environ.get("KMA_API_KEY")
        self.weather_service = WeatherService(kma_api_key=kma_api_key)
        
        # VDOS 통합 서비스
        self.vdos_service = VDOSIntegrationService()
        
        # TODO DB 경로 설정
        global TODO_DB_PATH
        TODO_DB_PATH = self.vdos_service.get_todo_db_path()
        logger.info(f"[MainWindow] TODO DB 경로: {TODO_DB_PATH}")
        
        # Top3 서비스
        from src.services import Top3Service
        self.top3_service = Top3Service(vdos_connector=self.vdos_service.vdos_connector)
        
        # 시간 필터링 및 데이터 수집 서비스
        self.time_filter_service = TimeFilterService()
        self.data_collection_service = DataCollectionService(
            self.assistant, self.time_filter_service
        )
    
    def _init_virtualoffice_attributes(self):
        """VirtualOffice 관련 속성 초기화"""
        self.vo_client: Optional[VirtualOfficeClient] = None
        self.selected_persona: Optional[PersonaInfo] = None
        self.data_source_type: str = "virtualoffice"
        self.polling_worker: Optional[PollingWorker] = None
        self.sim_monitor: Optional[SimulationMonitor] = None
        self.vo_config: Optional[VirtualOfficeConfig] = None
        self.vo_config_path = self.vdos_service.get_vo_config_path()
        self.connection_controller = VirtualOfficeConnectionController(self)
        self.data_controller = DataRefreshController(self)
        self.analysis_controller = AnalysisCacheController(self)
    
    def _init_cache_system(self):
        """캐시 시스템 초기화"""
        # 기존 캐시 (레거시 호환성 유지)
        self._persona_cache: Dict[str, Dict] = {}
        self._last_simulation_tick: Optional[int] = None
        self._simulation_running: bool = False
        self._cache_valid_until: Dict[str, float] = {}
        self._persona_first_load: Dict[str, bool] = {}  # 페르소나별 첫 로드 추적
        
        # 새로운 캐시 서비스
        from src.services.persona_todo_cache_service import PersonaTodoCacheService
        self._cache_service = PersonaTodoCacheService(max_cache_size=10)
        
        # 캐시 관련 상태 변수
        self._current_persona_id: Optional[str] = None
        self._current_data_version: str = "0"  # 틱 번호 또는 타임스탬프
        
        logger.info("✅ 캐시 시스템 초기화 완료")
    
    def _init_ui_components(self):
        """UI 컴포넌트 초기화"""
        self.notification_manager = NotificationManager()
        self.new_message_ids = set()
        self._progress_bar = None
        self._progress_label = None
    
    def _finalize_initialization(self):
        """초기화 완료"""
        self.init_ui()
        self.setup_timers()
        self.initialize_online_state()
        self._load_vo_config()
        QTimer.singleShot(1000, self._update_connection_status)

    
    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("OFFLINE AGENT v2.0")
        self.setGeometry(100, 100, 1400, 900)
        
        # 중앙 위젯 설정
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 메인 레이아웃
        main_layout = QHBoxLayout(central_widget)
        
        # 좌측 패널 (설정 및 제어) - 고정 너비
        left_panel = self.create_left_panel()
        main_layout.addWidget(left_panel, 0)  # stretch factor 0 = 고정 크기
        
        # 우측 패널 (결과 표시) - 나머지 공간 모두 사용
        right_panel = self.create_right_panel()
        main_layout.addWidget(right_panel, 1)  # stretch factor 1 = 확장 가능
        
        # 메뉴바 설정
        self.create_menu_bar()
        
        # 상태바 설정
        self.create_status_bar()
    
    def create_left_panel(self):
        """좌측 패널 생성 (리팩토링: 컴포넌트 분리)"""
        # 스크롤 영역 생성
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # 메인 컨테이너
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # 제어 패널 생성 및 시그널 연결
        self.left_control_panel = LeftControlPanel()
        self._connect_control_panel_signals()
        layout.addWidget(self.left_control_panel)
        
        # VirtualOffice 패널 생성 및 시그널 연결
        self.vo_panel = VirtualOfficePanel()
        self._connect_vo_panel_signals()
        layout.addWidget(self.vo_panel)
        
        # 하단 여백
        layout.addStretch()
        
        # 스크롤 영역에 컨테이너 설정
        scroll_area.setWidget(container)
        
        # 고정 폭 설정
        try:
            container.adjustSize()
            width_hint = container.sizeHint().width()
            cushion = 48  # 여백 및 스크롤바 폭 대비
            fixed_w = max(320, width_hint + cushion)
            scroll_area.setFixedWidth(fixed_w)
        except Exception:
            scroll_area.setFixedWidth(380)
        
        return scroll_area
    
    def _connect_control_panel_signals(self):
        """제어 패널 시그널 연결"""
        self.left_control_panel.status_toggled.connect(self.toggle_status)
# 제거됨: 버튼 통합으로 인해 불필요
        self.left_control_panel.time_range_changed.connect(self._on_time_range_changed)
        self.left_control_panel.weather_update_requested.connect(self.fetch_weather)
        self.left_control_panel.daily_summary_requested.connect(self.show_daily_summary)
        self.left_control_panel.weekly_summary_requested.connect(self.show_weekly_summary)
        self.left_control_panel.connect_vo_requested.connect(
            self.connection_controller.connect_virtualoffice
        )
        
        # 기존 위젯 참조 유지 (하위 호환성)
        self.status_indicator = self.left_control_panel.status_indicator
        self.status_button = self.left_control_panel.status_button
        self.connect_collect_button = self.left_control_panel.connect_collect_button
# 제거됨: 버튼 통합으로 인해 불필요
# 제거됨: cleanup_button 삭제됨
        self.progress_bar = self.left_control_panel.progress_bar
        self.status_message = self.left_control_panel.status_message
        self.time_range_selector = self.left_control_panel.time_range_selector
        self.weather_input = self.left_control_panel.weather_input
        self.weather_button = self.left_control_panel.weather_button
        self.weather_status_label = self.left_control_panel.weather_status_label
        self.weather_tip_label = self.left_control_panel.weather_tip_label
        self.daily_summary_button = self.left_control_panel.daily_summary_button
        self.weekly_summary_button = self.left_control_panel.weekly_summary_button
    
    def _connect_vo_panel_signals(self):
        """VirtualOffice 패널 시그널 연결"""
# 중복 제거: left_control_panel에서 이미 연결됨
        self.vo_panel.persona_changed.connect(self.on_persona_changed)
        self.vo_panel.tick_history_requested.connect(self.show_tick_history)
        
        # 기존 위젯 참조 유지 (하위 호환성)
        self.persona_combo = self.vo_panel.persona_combo
        self.vo_connection_status_label = self.vo_panel.connection_status_label
        self.vo_email_url = self.vo_panel.email_url_input
        self.vo_chat_url = self.vo_panel.chat_url_input
        self.vo_sim_url = self.vo_panel.sim_url_input
        self.sim_running_status = self.vo_panel.sim_running_status
        self.sim_progress_bar = self.vo_panel.sim_progress_bar
        self.sim_status_display = self.vo_panel.sim_status_display
        self.tick_history_btn = self.vo_panel.tick_history_btn
    
    def _show_summary_popup(self, title: str, text: str) -> None:
        """요약 다이얼로그 표시"""
        dialog = SummaryDialog(title, text, self)
        dialog.exec()

    def show_daily_summary(self):
        messages = self.collected_messages or list(getattr(self.assistant, "collected_messages", []))
        if not messages:
            QMessageBox.information(self, "일일 요약", "최근 수집된 메시지가 없습니다.")
            return
        parsed = []
        for msg in messages:
            dt = parse_iso_datetime(msg.get("date"))
            if dt:
                parsed.append((dt, msg))
        if not parsed:
            QMessageBox.information(self, "일일 요약", "메시지에 날짜 정보가 없어 요약할 수 없습니다.")
            return
        parsed.sort(key=lambda x: x[0])
        target_date = parsed[-1][0].date()
        day_msgs = [msg for dt, msg in parsed if dt.date() == target_date]
        if not day_msgs:
            QMessageBox.information(self, "일일 요약", "해당 날짜의 메시지를 찾지 못했습니다.")
            return

        email_cnt = sum(1 for m in day_msgs if (m.get("type") or "").lower() == "email")
        messenger_cnt = len(day_msgs) - email_cnt

        analysis_lookup: Dict[str, Dict] = {}
        for res in self.analysis_results or []:
            msg_obj = res.get("message") or {}
            mid = msg_obj.get("msg_id")
            if mid:
                analysis_lookup[mid] = res
        day_results = [analysis_lookup.get(m.get("msg_id")) for m in day_msgs if analysis_lookup.get(m.get("msg_id"))]

        priority_counts = Counter()
        summary_lines: List[str] = []
        action_titles: List[str] = []
        total_actions = 0
        for res in day_results:
            if not res:
                continue
            pr = res.get("priority") or {}
            level = (pr.get("priority_level") or pr.get("priority") or "low").lower()
            priority_counts[level] += 1
            actions = res.get("actions") or []
            total_actions += len(actions)
            for act in actions:
                if isinstance(act, dict):
                    title = act.get("title") or act.get("description") or act.get("task") or ""
                else:
                    title = str(act)
                title = title.strip()
                if title:
                    action_titles.append(title)
            sum_obj = res.get("summary")
            if isinstance(sum_obj, dict):
                summary_text = sum_obj.get("summary") or ""
            elif sum_obj is not None:
                summary_text = getattr(sum_obj, "summary", "") or ""
            else:
                summary_text = ""
            summary_text = summary_text.strip()
            if summary_text:
                summary_lines.append(summary_text)

        sender_counts = Counter((m.get("sender") or "알 수 없음") for m in day_msgs)
        lines = [
            f"{target_date:%Y-%m-%d} 일일 요약",
            "=" * 40,
            f"총 메시지 {len(day_msgs)}건 (이메일 {email_cnt} · 메신저 {messenger_cnt})",
            f"우선순위: High {priority_counts.get('high',0)} · Medium {priority_counts.get('medium',0)} · Low {priority_counts.get('low',0)}",
        ]
        if sender_counts:
            lines.append("")
            lines.append("주요 발신자 TOP3:")
            for sender, cnt in sender_counts.most_common(3):
                lines.append(f"- {sender}: {cnt}건")
        if summary_lines:
            lines.append("")
            lines.append("핵심 요약:")
            for sentence in summary_lines[:3]:
                lines.append(f"- {sentence}")
        if total_actions:
            lines.append("")
            lines.append(f"추출된 액션 {total_actions}건")
            for title in action_titles[:3]:
                lines.append(f"  · {title}")

        self._show_summary_popup("일일 요약", "\n".join(lines))

    def show_weekly_summary(self):
        messages = self.collected_messages or list(getattr(self.assistant, "collected_messages", []))
        if not messages:
            QMessageBox.information(self, "주간 요약", "최근 수집된 메시지가 없습니다.")
            return
        parsed = []
        for msg in messages:
            dt = parse_iso_datetime(msg.get("date"))
            if dt:
                parsed.append((dt, msg))
        if not parsed:
            QMessageBox.information(self, "주간 요약", "메시지에 날짜 정보가 없어 요약할 수 없습니다.")
            return
        parsed.sort(key=lambda x: x[0])
        end_date = parsed[-1][0].date()
        start_date = end_date - timedelta(days=6)
        week_msgs = [msg for dt, msg in parsed if start_date <= dt.date() <= end_date]
        if not week_msgs:
            QMessageBox.information(self, "주간 요약", "주간에 해당하는 메시지를 찾지 못했습니다.")
            return

        email_cnt = sum(1 for m in week_msgs if (m.get("type") or "").lower() == "email")
        messenger_cnt = len(week_msgs) - email_cnt

        analysis_lookup: Dict[str, Dict] = {}
        for res in self.analysis_results or []:
            msg_obj = res.get("message") or {}
            mid = msg_obj.get("msg_id")
            if mid:
                analysis_lookup[mid] = res
        week_results = [analysis_lookup.get(m.get("msg_id")) for m in week_msgs if analysis_lookup.get(m.get("msg_id"))]

        priority_counts = Counter()
        summary_lines: List[str] = []
        action_titles: List[str] = []
        total_actions = 0
        for res in week_results:
            if not res:
                continue
            pr = res.get("priority") or {}
            level = (pr.get("priority_level") or pr.get("priority") or "low").lower()
            priority_counts[level] += 1
            actions = res.get("actions") or []
            total_actions += len(actions)
            for act in actions:
                if isinstance(act, dict):
                    title = act.get("title") or act.get("description") or act.get("task") or ""
                else:
                    title = str(act)
                title = title.strip()
                if title:
                    action_titles.append(title)
            sum_obj = res.get("summary")
            if isinstance(sum_obj, dict):
                summary_text = sum_obj.get("summary") or ""
            elif sum_obj is not None:
                summary_text = getattr(sum_obj, "summary", "") or ""
            else:
                summary_text = ""
            summary_text = summary_text.strip()
            if summary_text:
                summary_lines.append(summary_text)

        sender_counts = Counter((m.get("sender") or "알 수 없음") for m in week_msgs)
        day_counts = Counter(dt.date() for dt, _ in parsed if start_date <= dt.date() <= end_date)
        busiest_day, busiest_count = (None, 0)
        if day_counts:
            busiest_day, busiest_count = max(day_counts.items(), key=lambda itm: itm[1])

        lines = [
            f"{start_date:%Y-%m-%d} ~ {end_date:%Y-%m-%d} 주간 요약",
            "=" * 40,
            f"총 메시지 {len(week_msgs)}건 (이메일 {email_cnt} · 메신저 {messenger_cnt})",
            f"우선순위: High {priority_counts.get('high',0)} · Medium {priority_counts.get('medium',0)} · Low {priority_counts.get('low',0)}",
        ]
        if day_counts:
            day_line = ", ".join(f"{day.strftime('%m-%d')}: {cnt}건" for day, cnt in sorted(day_counts.items()))
            lines.append(f"일별 메시지: {day_line}")
        if busiest_day:
            lines.append(f"가장 바쁜 날: {busiest_day.strftime('%Y-%m-%d')} ({busiest_count}건)")
        if sender_counts:
            lines.append("")
            lines.append("주요 발신자 TOP5:")
            for sender, cnt in sender_counts.most_common(5):
                lines.append(f"- {sender}: {cnt}건")
        if summary_lines:
            lines.append("")
            lines.append("핵심 요약:")
            for sentence in summary_lines[:5]:
                lines.append(f"- {sentence}")
        if total_actions:
            lines.append("")
            lines.append(f"추출된 액션 {total_actions}건")
            for title in action_titles[:5]:
                lines.append(f"  · {title}")

        self._show_summary_popup("주간 요약", "\n".join(lines))

    def create_right_panel(self):
        panel = QWidget(); layout = QVBoxLayout(panel)
        self.tab_widget = QTabWidget()

        # ✅ TODO 탭: TodoPanel 그대로 붙이기
        self.todo_tab = QWidget()
        todo_layout = QVBoxLayout(self.todo_tab)
        self.todo_panel = TodoPanel(db_path=TODO_DB_PATH, parent=self)
        # Top3 서비스 전달 (VDOS 연동됨)
        if hasattr(self.todo_panel, "set_top3_service_instance"):
            self.todo_panel.set_top3_service_instance(self.top3_service)
        else:
            self.todo_panel.top3_service = self.top3_service
        self.todo_panel.set_top3_callback(self._on_top3_updated)
        todo_layout.addWidget(self.todo_panel)
        self.tab_widget.addTab(self.todo_tab, "📋 TODO 리스트")

        # ✅ 메시지/이메일/분석 탭
        self.message_tab = self.create_message_tab(); self.tab_widget.addTab(self.message_tab, "📨 메시지")
        self.email_tab = self.create_email_tab(); self.tab_widget.addTab(self.email_tab, "📧 이메일")
        self.analysis_tab = self.create_analysis_tab(); self.tab_widget.addTab(self.analysis_tab, "📊 분석 결과")

        layout.addWidget(self.tab_widget)
        return panel
    
    def create_todo_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 프로젝트 태그 바 추가
        try:
            from .widgets.project_tag_widget import ProjectTagBar
            self.project_tag_bar = ProjectTagBar()
            self.project_tag_bar.tag_clicked.connect(self._on_project_filter_changed)
            layout.addWidget(self.project_tag_bar)
        except ImportError as e:
            logger.warning(f"프로젝트 태그 위젯 로드 실패: {e}")

        self.todo_list = QListWidget()
        self.todo_list.setUniformItemSizes(True)      # 행 높이 균일
        self.todo_list.setSpacing(6)
        self.todo_list.setStyleSheet("""
            QListWidget::item { padding: 0px; margin: 4px; }
            QListWidget { background: #F8FAFC; }
        """)
        layout.addWidget(self.todo_list)
        return tab

    def create_timeline_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self.timeline_list = QListWidget()
        self.timeline_list.setSpacing(6)
        self.timeline_list.setAlternatingRowColors(True)
        self.timeline_list.setStyleSheet("QListWidget { background: #F9FAFB; }")
        layout.addWidget(self.timeline_list)
        return tab

    def update_message_table(self, messages):
        self.message_table.setRowCount(len(messages))
        self.message_table.verticalHeader().setDefaultSectionSize(36)  # 고정 행 높이
        self.message_table.setWordWrap(False)

        for i, msg in enumerate(messages):
            def item(text):  # 엘라이드용
                it = QTableWidgetItem(text or "")
                it.setToolTip(text or "")
                return it

            self.message_table.setItem(i, 0, item(msg.get("platform", "")))
            self.message_table.setItem(i, 1, item(msg.get("sender", "")))

            content = msg.get("subject") or (msg.get("content", "")[:120])
            self.message_table.setItem(i, 2, item(content))

            date_str = msg.get("date", "")
            if date_str:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    date_str = dt.strftime("%m-%d %H:%M")
                except:
                    pass
            self.message_table.setItem(i, 3, item(date_str))

    def _update_message_summary(self, messages: list[dict]) -> None:
        if not hasattr(self, "message_summary_label"):
            return
        total = len(messages)
        if total == 0:
            self.message_summary_label.setText("메시지를 수집하면 요약이 표시됩니다.")
            return
        email_cnt = sum(1 for m in messages if (m.get("type") or "").lower() == "email")
        messenger_cnt = total - email_cnt
        times = []
        for m in messages:
            value = m.get("date")
            if not value:
                continue
            try:
                times.append(datetime.fromisoformat(value.replace("Z", "+00:00")))
            except Exception:
                continue
        if times:
            start = min(times).strftime("%m/%d %H:%M")
            end = max(times).strftime("%m/%d %H:%M")
            window = f"{start} → {end}"
        else:
            window = "시간 정보 없음"
        self.message_summary_label.setText(
            f"총 {total}건 · 이메일 {email_cnt}건 · 메신저 {messenger_cnt}건 · 기간 {window}"
        )

    def update_timeline(self, messages: list[dict]) -> None:
        if not hasattr(self, "timeline_list"):
            return
        self.timeline_list.clear()

        def parse_dt(value: str | None):
            if not value:
                return None
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except Exception:
                return None

        entries = []
        for msg in messages:
            dt = parse_dt(msg.get("date"))
            entries.append((dt or datetime.min, msg))
        entries.sort(key=lambda x: x[0], reverse=True)

        for dt, msg in entries:
            timestamp = dt.strftime("%m/%d %H:%M") if dt != datetime.min else "시간 미상"
            mtype = (msg.get("type") or msg.get("platform") or "").lower()
            prefix = "📧" if mtype == "email" else "💬"
            sender = msg.get("sender") or "(발신자 없음)"
            snippet = msg.get("subject") or msg.get("content", "")
            if len(snippet) > 80:
                snippet = snippet[:80] + "..."
            
            # 새 메시지인지 확인
            msg_id = msg.get("msg_id")
            is_new = msg_id in self.new_message_ids if hasattr(self, 'new_message_ids') else False
            
            # NEW 배지 추가
            if is_new:
                text = f"{prefix} [{timestamp}] {sender} [NEW]\n{snippet}"
            else:
                text = f"{prefix} [{timestamp}] {sender}\n{snippet}"
            
            item = QListWidgetItem(text)
            if mtype == "email":
                item.setBackground(QColor("#EEF2FF"))
            else:
                item.setBackground(QColor("#ECFDF5"))
            
            # 새 메시지는 더 밝은 배경색으로 표시
            if is_new:
                if mtype == "email":
                    item.setBackground(QColor("#DBEAFE"))  # 더 밝은 파란색
                else:
                    item.setBackground(QColor("#D1FAE5"))  # 더 밝은 초록색
            
            self.timeline_list.addItem(item)

    def _update_analysis_summary(self, todo_list: dict, analysis_results: list[dict] | None) -> None:
        if not hasattr(self, "analysis_summary_label"):
            return
        summary = (todo_list or {}).get("summary", {})
        total = summary.get("total")
        if total is None and todo_list:
            total = len(todo_list.get("items", []))
        if not total:
            self.analysis_summary_label.setText("TODO 생성 결과가 여기에 요약됩니다.")
            return
        high = summary.get("high", 0)
        medium = summary.get("medium", 0)
        low = summary.get("low", 0)
        actions = sum(len(r.get("actions", [])) for r in (analysis_results or []))
        self.analysis_summary_label.setText(
            f"TODO {total}건 · High {high} · Medium {medium} · Low {low} · 추출된 액션 {actions}건"
        )

    def fetch_weather(self, preset_location: Optional[str] = None):
        """날씨 정보 조회"""
        if not hasattr(self, "weather_input"):
            return
        
        location = (preset_location or self.weather_input.text()).strip()
        if preset_location:
            self.weather_input.setText(location)
        
        if not location:
            QMessageBox.warning(self, "입력 오류", "지역을 입력해주세요.")
            return
        
        self.weather_status_label.setText("날씨 정보를 불러오는 중입니다...")
        
        # WeatherService를 사용하여 날씨 정보 조회
        result = self.weather_service.fetch_weather(location)
        
        # 결과 표시
        self.weather_status_label.setText(result.get("status", "날씨 정보를 가져오지 못했습니다."))
        self.weather_tip_label.setText(result.get("tip", "날씨 팁을 불러오지 못했습니다."))
    
    def create_message_tab(self):
        """메시지 탭 생성 - MessageSummaryPanel 사용"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # ✅ MessageSummaryPanel 사용
        self.message_summary_panel = MessageSummaryPanel()
        self.message_summary_panel.summary_unit_changed.connect(self._on_summary_unit_changed)
        self.message_summary_panel.summary_card_clicked.connect(self._on_summary_card_clicked)
        layout.addWidget(self.message_summary_panel)
        
        return tab
    
    def create_email_tab(self):
        """이메일 탭 생성 - EmailPanel 사용"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # ✅ EmailPanel 사용
        self.email_panel = EmailPanel()
        layout.addWidget(self.email_panel)
        
        return tab
    
    def create_analysis_tab(self):
        """분석 결과 탭 생성 - AnalysisResultPanel 사용"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # ✅ AnalysisResultPanel 사용
        self.analysis_result_panel = AnalysisResultPanel()
        layout.addWidget(self.analysis_result_panel)
        
        return tab

    def _apply_status_style(self):
        """상태 스타일 적용 (LeftControlPanel에 위임)"""
        if hasattr(self, "left_control_panel"):
            self.left_control_panel.set_status(self.current_status)

    def initialize_online_state(self):
        self.current_status = "online"
        self._apply_status_style()
        if hasattr(self, "refresh_timer"):
            self.refresh_timer.start()
        if hasattr(self, "status_message"):
            self.status_message.setText("VirtualOffice 연결 대기 중 - '실시간 연결 테스트' 버튼을 눌러주세요")
        if hasattr(self, "status_bar"):
            self.status_bar.showMessage("VirtualOffice 연결 대기 중")

    def create_menu_bar(self):
        """메뉴바 생성"""
        menubar = self.menuBar()
        
        # 파일 메뉴
        file_menu = menubar.addMenu("파일")
        
        save_action = file_menu.addAction("결과 저장")
        save_action.triggered.connect(self.save_results)
        
        load_action = file_menu.addAction("결과 불러오기")
        load_action.triggered.connect(self.load_results)
        
        file_menu.addSeparator()
        
        exit_action = file_menu.addAction("종료")
        exit_action.triggered.connect(self.close)
        
        # 도움말 메뉴
        help_menu = menubar.addMenu("도움말")
        
        about_action = help_menu.addAction("정보")
        about_action.triggered.connect(self.show_about)
    
    def create_status_bar(self):
        """상태바 생성"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Smart Assistant 준비됨")
    
    def setup_timers(self):
        """타이머 설정"""
        # 자동 새로고침 타이머 (온라인 모드에서만)
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.auto_refresh)
        self.refresh_timer.setInterval(300000)  # 5분마다
    
    def toggle_status(self):
        """상태 토글"""
        if self.current_status == "offline":
            self.current_status = "online"
            self._apply_status_style()
            if hasattr(self, "refresh_timer"):
                self.refresh_timer.start()
            if hasattr(self, "status_bar"):
                self.status_bar.showMessage("온라인 모드 - 자동 분석 대기")
            if not self.worker_thread or not self.worker_thread.isRunning():
                self.status_message.setText("온라인 전환 감지: 데이터를 자동으로 분석합니다.")
                self.start_collection()
        else:
            self.current_status = "offline"
            self._apply_status_style()
            if hasattr(self, "refresh_timer"):
                self.refresh_timer.stop()
            if hasattr(self, "status_bar"):
                self.status_bar.showMessage("오프라인 모드")
            self.status_message.setText("오프라인 모드입니다. 필요 시 다시 온라인으로 전환하세요.")
    
    def _initialize_data_time_range(self):
        """데이터 시간 범위 초기화 (VirtualOffice 전용)
        
        VirtualOffice를 사용하는 경우 시간 범위는 실시간으로 결정되므로
        기본 범위만 설정합니다.
        """
        try:
            # 기본 시간 범위: 최근 7일
            now = datetime.now(timezone.utc)
            data_start = now - timedelta(days=7)
            data_end = now
            
            self.time_range_selector.set_data_range(data_start, data_end)
            logger.info(f"📅 기본 시간 범위 설정: 최근 7일")
                
        except Exception as e:
            logger.error(f"❌ 데이터 시간 범위 초기화 오류: {e}", exc_info=True)
    
    def _on_time_range_changed(self, start: datetime, end: datetime):
        """시간 범위 변경 핸들러
        
        TimeRangeSelector에서 시간 범위가 변경되면 호출됩니다.
        변경된 시간 범위를 TimeFilterService에 설정하고 즉시 필터링을 적용합니다.
        
        Args:
            start: 시작 시간 (UTC aware datetime)
            end: 종료 시간 (UTC aware datetime)
        """
        try:
            # TimeFilterService에 시간 범위 설정
            self.time_filter_service.set_time_range(start, end)
            
            # collect_options에도 저장 (하위 호환성)
            self.collect_options["time_range"] = {
                "start": start,
                "end": end
            }
            
            # 현재 페르소나의 캐시 무효화
            if self._current_persona_id:
                invalidated_count = self._cache_service.invalidate(self._current_persona_id)
                logger.info(f"🗑️ 시간 범위 변경으로 캐시 무효화: {invalidated_count}개")
            
            # 상태 메시지 업데이트
            start_str = start.strftime('%Y-%m-%d %H:%M')
            end_str = end.strftime('%Y-%m-%d %H:%M')
            self.status_message.setText(f"⏰ 시간 범위: {start_str} ~ {end_str}")
            
            # 즉시 새 데이터 수집 시작 (시간 범위 적용) - 재분석 자동 실행
            if self.vo_client and self.selected_persona:
                logger.info(f"🚀 시간 범위 변경으로 인한 자동 재분석 시작")
                self._start_data_collection_with_time_filter()
            else:
                logger.info(f"⏰ 시간 범위 설정됨: {start_str} ~ {end_str} (연결 후 적용)")
                
        except Exception as e:
            logger.error(f"❌ 시간 범위 변경 오류: {e}", exc_info=True)
            self.status_message.setText(f"시간 범위 설정 오류: {e}")
    
    def _apply_time_filtering(self):
        """현재 데이터에 시간 필터링 적용"""
        try:
            if not self.time_filter_service.is_enabled:
                logger.debug("시간 필터링이 비활성화됨")
                return
            
            logger.info("🔄 시간 필터링 적용 중...")
            
            # 메시지 필터링
            original_count = len(self.collected_messages)
            filtered_messages = self.time_filter_service.filter_messages(self.collected_messages)
            
            # 필터링된 메시지로 UI 업데이트
            if len(filtered_messages) != original_count:
                logger.info(f"📧 메시지 필터링: {original_count}개 → {len(filtered_messages)}개")
                
                # 분석 결과도 필터링
                if hasattr(self, 'analysis_results'):
                    filtered_analysis = self.time_filter_service.filter_messages(self.analysis_results)
                    self.analysis_results = filtered_analysis
                
                # UI 업데이트
                self._update_ui_with_filtered_data(filtered_messages)
                
                # TODO 재생성 (필터링된 메시지 기반)
                self._regenerate_todos_from_filtered_messages(filtered_messages)
            else:
                logger.info("📧 필터링 결과: 변경 없음")
                
        except Exception as e:
            logger.error(f"❌ 시간 필터링 적용 오류: {e}", exc_info=True)
    
    def _update_ui_with_filtered_data(self, filtered_messages: List[Dict]):
        """필터링된 데이터로 UI 업데이트
        
        Args:
            filtered_messages: 필터링된 메시지 리스트
        """
        try:
            # 이메일 패널 업데이트
            if hasattr(self, 'email_panel'):
                email_messages = [m for m in filtered_messages if m.get("type") == "email"]
                self.email_panel.update_emails(email_messages)
            
            # 메시지 요약 패널 업데이트
            if hasattr(self, 'message_summary_panel'):
                self._update_message_summaries("day")
            
            # 분석 결과 패널 업데이트
            if hasattr(self, 'analysis_result_panel') and hasattr(self, 'analysis_results'):
                self.analysis_result_panel.update_analysis(
                    self.analysis_results, 
                    filtered_messages
                )
            
            logger.info("✅ 필터링된 데이터로 UI 업데이트 완료")
            
        except Exception as e:
            logger.error(f"❌ 필터링된 데이터 UI 업데이트 오류: {e}")
    
    def _regenerate_todos_from_filtered_messages(self, filtered_messages: List[Dict]):
        """필터링된 메시지에서 TODO 재생성
        
        Args:
            filtered_messages: 필터링된 메시지 리스트
        """
        try:
            if not filtered_messages:
                # 메시지가 없으면 TODO도 비움
                if hasattr(self, 'todo_panel'):
                    self.todo_panel.populate_from_items([])
                logger.info("📋 필터링 결과: TODO 없음")
                return
            
            logger.info(f"🔄 필터링된 메시지로 TODO 재생성: {len(filtered_messages)}개 메시지")
            
            # 백그라운드에서 TODO 재생성
            self._trigger_background_analysis(filtered_messages)
            
        except Exception as e:
            logger.error(f"❌ TODO 재생성 오류: {e}")
    
    def _on_summary_unit_changed(self, unit: str):
        """요약 단위 변경 핸들러
        
        MessageSummaryPanel에서 요약 단위가 변경되면 호출됩니다.
        메시지를 새로운 단위로 그룹화하고 요약을 업데이트합니다.
        
        Args:
            unit: 요약 단위 ("daily", "weekly", "monthly")
        """
        if not self.collected_messages:
            self.status_message.setText("메시지를 먼저 수집해주세요.")
            return
        
        # 단위 변환: "daily" → "day", "weekly" → "week", "monthly" → "month"
        unit_map = {"daily": "day", "weekly": "week", "monthly": "month"}
        converted_unit = unit_map.get(unit, "day")
        
        # 로그 출력
        unit_name_kr = {"day": "일별", "week": "주별", "month": "월별"}.get(converted_unit, converted_unit)
        logger.info(f"📊 요약 단위 변경: {unit_name_kr}")
        self.status_message.setText(f"{unit_name_kr} 요약으로 전환 중...")
        
        # 메시지 그룹화 및 요약 업데이트
        self._update_message_summaries(converted_unit)
        
        self.status_message.setText(f"{unit_name_kr} 요약 표시 완료")
    
    def _on_summary_card_clicked(self, summary: Dict):
        """요약 카드 클릭 핸들러
        
        MessageSummaryPanel에서 요약 카드가 클릭되면 호출됩니다.
        클릭된 그룹의 원본 메시지를 조회하여 MessageDetailDialog를 표시합니다.
        
        Args:
            summary: 클릭된 요약 그룹 데이터
        """
        try:
            # message_ids 추출
            message_ids = summary.get("message_ids", [])
            
            logger.info(f"요약 카드 클릭: message_ids 수 = {len(message_ids)}, 전체 메시지 수 = {len(self.collected_messages)}")
            
            if not message_ids:
                logger.warning("요약 그룹에 message_ids가 없습니다")
                logger.debug(f"summary 내용: {summary}")
                QMessageBox.warning(
                    self,
                    "메시지 없음",
                    "이 그룹에 메시지가 없습니다."
                )
                return
            
            # 원본 메시지 조회
            messages = []
            for msg in self.collected_messages:
                # 다양한 ID 필드 시도 (msg_id가 주요 필드)
                msg_id = msg.get("msg_id") or msg.get("id") or msg.get("message_id") or msg.get("_id")
                if msg_id and str(msg_id) in message_ids:
                    messages.append(msg)
            
            logger.info(f"조회된 메시지 수: {len(messages)}/{len(message_ids)}")
            
            if not messages:
                logger.warning(f"message_ids에 해당하는 메시지를 찾을 수 없습니다")
                logger.debug(f"찾으려는 message_ids (처음 3개): {message_ids[:3]}")
                
                # 디버깅: 실제 메시지의 ID 필드 확인
                if self.collected_messages:
                    sample_msg = self.collected_messages[0]
                    logger.debug(f"샘플 메시지 ID 필드: msg_id={sample_msg.get('msg_id')}, id={sample_msg.get('id')}, message_id={sample_msg.get('message_id')}")
                
                QMessageBox.warning(
                    self,
                    "메시지 조회 실패",
                    "메시지를 불러올 수 없습니다. 다시 시도해주세요."
                )
                return
            
            # 기간 라벨 생성
            period_start = summary.get("period_start")
            period_end = summary.get("period_end")
            unit = summary.get("unit", "daily")
            
            if isinstance(period_start, str):
                try:
                    period_start_dt = datetime.fromisoformat(period_start.replace("Z", "+00:00"))
                except Exception:
                    period_start_dt = None
            else:
                period_start_dt = period_start
            
            if period_start_dt:
                if unit == "daily":
                    period_label = period_start_dt.strftime("%Y년 %m월 %d일")
                elif unit == "weekly":
                    if isinstance(period_end, str):
                        try:
                            period_end_dt = datetime.fromisoformat(period_end.replace("Z", "+00:00"))
                            actual_end = period_end_dt - timedelta(days=1)
                            period_label = f"{period_start_dt.strftime('%Y년 %m/%d')} ~ {actual_end.strftime('%m/%d')}"
                        except Exception:
                            period_label = period_start_dt.strftime("%Y년 %W주차")
                    else:
                        period_label = period_start_dt.strftime("%Y년 %W주차")
                elif unit == "monthly":
                    period_label = period_start_dt.strftime("%Y년 %m월")
                else:
                    period_label = period_start_dt.strftime("%Y-%m-%d")
            else:
                period_label = "메시지 상세"
            
            # summary에 period_label 추가
            summary_with_label = summary.copy()
            summary_with_label["period_label"] = period_label
            
            # 통계 정보 추가
            stats_summary = summary.get("statistics_summary", "")
            if not stats_summary:
                total = summary.get("total_messages", len(messages))
                email_count = summary.get("email_count", 0)
                messenger_count = summary.get("messenger_count", 0)
                stats_summary = f"총 {total}건 | 이메일 {email_count}건, 메신저 {messenger_count}건"
            summary_with_label["statistics_summary"] = stats_summary
            
            # MessageDetailDialog 생성 및 표시
            dialog = MessageDetailDialog(summary_with_label, messages, self)
            dialog.exec()
            
        except Exception as e:
            logger.error(f"요약 카드 클릭 처리 오류: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "오류",
                f"메시지를 표시하는 중 오류가 발생했습니다:\n{str(e)}"
            )
    
    def _update_message_summaries(self, unit: str = "day"):
        """메시지 그룹화 및 요약 생성
        
        수집된 메시지를 지정된 단위로 그룹화하고 각 그룹별 요약을 생성합니다.
        생성된 요약은 MessageSummaryPanel에 표시됩니다.
        
        Args:
            unit: 그룹화 단위 ("day", "week", "month")
                - "day": 일별 그룹화
                - "week": 주별 그룹화 (월요일 시작)
                - "month": 월별 그룹화
        """
        if not self.collected_messages:
            return
        
        from nlp.message_grouping import group_by_day, group_by_week, group_by_month
        from nlp.grouped_summary import GroupedSummary
        
        # 단위에 따라 메시지 그룹화
        if unit == "day":
            groups = group_by_day(self.collected_messages)
        elif unit == "week":
            groups = group_by_week(self.collected_messages)
        elif unit == "month":
            groups = group_by_month(self.collected_messages)
        else:
            # 기본값: 일별 그룹화
            groups = group_by_day(self.collected_messages)
        
        # 그룹별 요약 생성
        summaries = []
        for period, messages in groups.items():
            # 간단한 요약 생성
            brief_summary = self._generate_brief_summary(messages)
            key_points = self._extract_key_points(messages)
            
            # 발신자별 우선순위 계산
            sender_priority_map = {}
            for msg in messages:
                sender = msg.get("sender", "Unknown")
                # 분석 결과에서 우선순위 찾기
                priority = "low"
                for result in self.analysis_results:
                    if result.get("message", {}).get("msg_id") == msg.get("msg_id"):
                        priority = result.get("priority", {}).get("priority_level", "low")
                        break
                
                # 최고 우선순위 유지
                if sender not in sender_priority_map:
                    sender_priority_map[sender] = priority
                else:
                    priority_order = {"high": 3, "medium": 2, "low": 1}
                    if priority_order.get(priority, 0) > priority_order.get(sender_priority_map[sender], 0):
                        sender_priority_map[sender] = priority
            
            # 그룹화 단위 결정
            unit_name = "daily" if unit == "day" else ("weekly" if unit == "week" else "monthly")
            
            # 기간 시작/종료 계산 (그룹 키 기반)
            from nlp.message_grouping import get_group_date_range
            period_start, period_end = get_group_date_range(period, unit_name)
            
            if not period_start:
                continue
            
            # GroupedSummary.from_messages 사용
            summary = GroupedSummary.from_messages(
                messages=messages,
                period_start=period_start,
                period_end=period_end,
                unit=unit_name,
                summary_text=brief_summary,
                key_points=key_points
            )
            
            # sender_priority_map을 summary 딕셔너리에 추가
            summary_dict = summary.to_dict()
            summary_dict["sender_priority_map"] = sender_priority_map
            summary_dict["brief_summary"] = brief_summary  # brief_summary도 추가
            
            summaries.append(summary_dict)
        
        # MessageSummaryPanel에 표시
        if hasattr(self, "message_summary_panel"):
            self.message_summary_panel.display_summaries(summaries)
    
    def _generate_brief_summary(self, messages: list) -> str:
        """간결한 요약 생성 (1-2줄)"""
        if not messages:
            return "메시지 없음"
        
        total = len(messages)
        email_count = sum(1 for m in messages if m.get("type") == "email")
        messenger_count = total - email_count
        
        # 주요 발신자
        senders = [m.get("sender", "Unknown") for m in messages]
        sender_counts = Counter(senders)
        top_sender = sender_counts.most_common(1)[0] if sender_counts else ("Unknown", 0)
        
        return f"총 {total}건 (이메일 {email_count}, 메신저 {messenger_count}) | 주요 발신자: {top_sender[0]} ({top_sender[1]}건)"
    
    def _extract_key_points(self, messages: List[Dict]) -> List[str]:
        """주요 포인트 추출 (최대 3개)
        
        메시지에서 핵심 포인트를 추출합니다.
        제목이 있으면 제목을 우선 사용하고, 없으면 본문의 첫 문장을 사용합니다.
        
        Args:
            messages: 메시지 리스트
            
        Returns:
            주요 포인트 문자열 리스트 (최대 3개)
            
        Examples:
            >>> points = self._extract_key_points(messages)
            >>> print(points[0])
            "Kim Jihoon: 오늘 오전 2일차 작업 진행 상황 점검..."
        """
        points = []
        
        # 최대 3개 메시지에서 포인트 추출
        for msg in messages[:3]:
            # 제목 우선, 없으면 본문 첫 문장
            subject = msg.get("subject", "")
            content = msg.get("content", "") or msg.get("body", "")
            sender = msg.get("sender", "Unknown")
            
            if subject:
                # 제목이 있으면 제목 사용
                point = f"{sender}: {subject[:80]}"
            elif content:
                # 첫 문장 추출 (마침표 기준)
                first_sentence = content.split(".")[0].strip()
                if len(first_sentence) > 10:  # 너무 짧은 문장 제외
                    point = f"{sender}: {first_sentence[:80]}"
                else:
                    point = f"{sender}: {content[:80]}"
            else:
                # 제목도 본문도 없으면 건너뛰기
                continue
            
            points.append(point)
        
        return points
    
    def start_collection(self):
        """메시지 수집 시작"""
        self.data_controller.start_collection()
    
    def stop_collection(self):
        """수집 중지"""
        self.data_controller.stop_collection()
    
    def handle_result(self, result):
        self.data_controller.handle_result(result)

    def _on_top3_updated(self, top3: list[dict]) -> None:
        if not hasattr(self, "todo_panel"):
            return
    
    def handle_error(self, error_message):
        """오류 처리"""
        self.data_controller.handle_error(error_message)
    
    def auto_refresh(self):
        """자동 새로고침 (온라인 모드)"""
        self.data_controller.auto_refresh()
    
    def offline_cleanup(self):
        """오프라인 정리"""
        from .offline_cleaner import OfflineCleanupDialog
        
        dialog = OfflineCleanupDialog(self)
        dialog.exec()
    
    def auto_save_results(self, result):
        """결과 자동 저장"""
        self.data_controller.auto_save_results(result)
    
    def save_results(self):
        """결과 저장"""
        QMessageBox.information(self, "저장", "결과 저장 기능은 향후 구현될 예정입니다.")
    
    def load_results(self):
        """결과 불러오기"""
        QMessageBox.information(self, "불러오기", "결과 불러오기 기능은 향후 구현될 예정입니다.")
    
    def show_about(self):
        """정보 표시"""
        QMessageBox.about(self, "Smart Assistant 정보",
                         "Smart Assistant v1.0\n\n"
                         "AI 기반 스마트 어시스턴트\n"
                         "이메일과 메신저 메시지를 분석하여\n"
                         "TODO 리스트를 자동 생성합니다.\n\n"
                         "개발: Smart Assistant Team")
    

    def connect_virtualoffice(self):
        """VirtualOffice 연결 트리거 (컨트롤러 위임)."""
        self.connection_controller.connect_virtualoffice()

    def _setup_personas(self, personas: list):
        """레거시 호환용 래퍼 (컨트롤러 위임)."""
        self.connection_controller.setup_personas(personas)

    def _update_sim_status_display(self, sim_status):
        """시뮬레이션 상태 표시 업데이트 (컨트롤러 위임)."""
        self.connection_controller.update_sim_status_display(sim_status)
    
    def on_persona_changed(self, index: int):
        """페르소나 변경 이벤트 핸들러 (개선된 캐시 로직)"""
        if index < 0:
            return
        
        persona = self.persona_combo.itemData(index)
        if not persona or not self.vo_client:
            return
        
        try:
            self.selected_persona = persona
            persona_key = f"{persona.email_address}_{persona.chat_handle}"
            logger.info(f"페르소나 변경: {persona.name} ({persona.email_address})")
            
            # 현재 페르소나 ID 업데이트
            self._current_persona_id = persona.email_address or persona.chat_handle
            
            # 데이터 소스 업데이트 (VirtualOffice 모드인 경우에만)
            if self.data_source_type == "virtualoffice":
                # 새로운 캐시 서비스 사용
                cache_key = self._build_cache_key()
                cached_result = self._cache_service.get(cache_key)
                
                if cached_result:
                    # 캐시 히트: 즉시 결과 표시
                    logger.info(f"✅ 캐시 히트: {persona.name} - 즉시 표시")
                    self.status_message.setText(f"캐시에서 로드 중: {persona.name}...")
                    self._display_cached_result(cached_result)
                    self.status_message.setText(f"페르소나 변경됨 (캐시): {persona.name}")
                    
                    # ✅ 캐시 히트 시: 폴링 워커만 업데이트 (즉시 폴링 안 함)
                    self._update_polling_worker_persona(persona)
                    logger.info(f"⏰ 캐시 히트 - 정기 폴링만 활성화 (즉시 폴링 생략)")
                    
                    # ✅ 다음 정기 폴링 결과는 재분석 건너뛰기
                    self._skip_reanalysis_after_cache_hit = True
                    logger.info(f"🚫 다음 정기 폴링 결과는 재분석 건너뜀")
                    
                else:
                    # 캐시 미스: 분석 파이프라인 실행
                    logger.info(f"❌ 캐시 미스: {persona.name} - 데이터 수집 시작")
                    self.status_message.setText(f"데이터 분석 중: {persona.name}...")
                    
                    # ✅ 캐시 미스 시: 재분석 플래그 리셋
                    self._skip_reanalysis_after_cache_hit = False
                    
                    # 데이터 소스 업데이트
                    self.assistant.set_virtualoffice_source(self.vo_client, persona)
                    
                    # ✅ 캐시 미스 시: 폴링 워커 업데이트 및 즉시 폴링 트리거
                    self._update_polling_worker_persona(persona)
                    self._trigger_immediate_polling()
                    logger.info(f"🔄 캐시 미스 - 즉시 폴링 트리거")
                    
                    # 새 데이터 수집 및 분석 (캐시 저장은 분석 완료 후)
                    self._collect_and_cache_data(persona_key)
                    
                    self.status_message.setText(f"페르소나 변경됨: {persona.name}")
                    logger.info(f"✅ 데이터 분석 완료: {persona.name}")
        
        except Exception as e:
            logger.error(f"❌ 페르소나 변경 오류: {e}", exc_info=True)
            QMessageBox.warning(self, "오류", f"페르소나 변경 중 오류가 발생했습니다.\n\n{str(e)}")
    
    # on_data_source_changed 메서드 제거 (VirtualOffice 전용으로 변경)
    
    def on_new_data_received(self, data: dict):
        """새 데이터 수신 핸들러 (점진적 UI 업데이트)"""
        try:
            emails, messages, all_messages, timestamp = self._extract_new_data(data)
            total_new = len(emails) + len(messages)
            
            if total_new == 0:
                return
            
            logger.info(f"📬 새 데이터 수신: 메일 {len(emails)}개, 메시지 {len(messages)}개")
            
            # 시간 필터링 적용
            emails, messages, all_messages, total_new = self._apply_time_filtering_to_new_data(
                emails, messages, all_messages
            )
            
            if total_new == 0:
                return
            
            # 데이터 처리 및 UI 업데이트
            show_progress = total_new > 50
            self._process_new_data(emails, messages, all_messages, show_progress)
            self._update_ui_for_new_data(emails, messages, show_progress)
            self._finalize_new_data_processing(all_messages, total_new, timestamp)
            
        except Exception as e:
            logger.error(f"❌ 새 데이터 처리 오류: {e}", exc_info=True)
    
    def _extract_new_data(self, data: dict):
        """새 데이터 추출"""
        emails = data.get("emails", [])
        messages = data.get("messages", [])
        all_messages = data.get("all_messages", emails + messages)
        timestamp = data.get("timestamp", "")
        return emails, messages, all_messages, timestamp
    
    def _apply_time_filtering_to_new_data(self, emails, messages, all_messages):
        """새 데이터에 시간 필터링 적용"""
        if self.time_filter_service.is_enabled:
            original_count = len(all_messages)
            all_messages = self.time_filter_service.filter_messages(all_messages)
            emails = [m for m in all_messages if m.get("type") == "email"]
            messages = [m for m in all_messages if m.get("type") == "messenger"]
            
            filtered_count = len(all_messages)
            if filtered_count != original_count:
                logger.info(f"⏰ 새 데이터 시간 필터링: {original_count}개 → {filtered_count}개")
                total_new = len(emails) + len(messages)
                
                if total_new == 0:
                    logger.info("⏰ 시간 필터링 후 새 데이터 없음")
                    
        return emails, messages, all_messages, len(emails) + len(messages)
    
    def _process_new_data(self, emails, messages, all_messages, show_progress):
        """새 데이터 처리"""
        if show_progress:
            self._show_progress_bar(f"새 데이터 처리 중... ({len(all_messages)}개)")
        
        # SimulationMonitor에 데이터 기록
        if hasattr(self, 'sim_monitor') and self.sim_monitor is not None:
            self.sim_monitor.record_new_data(
                email_count=len(emails), message_count=len(messages)
            )
        
        # 새 메시지 ID 추적
        for msg in all_messages:
            msg_id = msg.get("msg_id")
            if msg_id:
                self.new_message_ids.add(msg_id)
        
        if show_progress:
            self._update_progress_bar(30)
        
        # 기존 데이터에 추가
        if hasattr(self.assistant, 'collected_messages'):
            self.assistant.collected_messages.extend(emails)
            self.assistant.collected_messages.extend(messages)
            self.collected_messages = self.assistant.collected_messages
        
        if show_progress:
            self._update_progress_bar(50)
    
    def _update_ui_for_new_data(self, emails, messages, show_progress):
        """새 데이터를 위한 UI 업데이트"""
        self._show_visual_notification()
        
        # 메시지 요약 패널 업데이트
        if hasattr(self, 'message_summary_panel'):
            self.notification_manager.register_widget(self.message_summary_panel, "visual")
            self.notification_manager.show_notification(self.message_summary_panel, duration_ms=500)
        
        if show_progress:
            self._update_progress_bar(70)
        
        # 이메일 패널 업데이트
        if hasattr(self, 'email_panel'):
            email_messages = [m for m in self.collected_messages if m.get("type") == "email"]
            self.email_panel.update_emails(email_messages)
            
            self.notification_manager.register_widget(self.email_panel, "visual")
            self.notification_manager.show_notification(self.email_panel, duration_ms=500)
        
        if show_progress:
            self._update_progress_bar(90)
        
        # 타임라인 업데이트
        if hasattr(self, 'timeline_list'):
            self._update_timeline_with_badges()
        
        if show_progress:
            self._update_progress_bar(100)
            self._hide_progress_bar()
    
    def _finalize_new_data_processing(self, all_messages, total_new, timestamp):
        """새 데이터 처리 완료"""
        if total_new > 0:
            # ✅ 캐시 히트 후에는 재분석 건너뛰기
            skip_reanalysis = getattr(self, '_skip_reanalysis_after_cache_hit', False)
            
            if skip_reanalysis:
                logger.info(f"⏭️ 캐시 히트 후 정기 폴링 - 재분석 건너뜀 ({total_new}개 메시지)")
                # 플래그 리셋 (다음 정기 폴링부터는 재분석 허용)
                self._skip_reanalysis_after_cache_hit = False
            else:
                logger.info(f"🔄 새 메시지 {total_new}개 수신 - 2초 후 자동 재분석 시작")
                self._process_new_messages_async(all_messages)
        
        # 상태바에 알림 표시
        emails_count = len([m for m in all_messages if m.get("type") == "email"])
        messages_count = len([m for m in all_messages if m.get("type") == "messenger"])
        self.statusBar().showMessage(
            f"📬 새 데이터 도착: 메일 {emails_count}개, 메시지 {messages_count}개 ({timestamp})",
            5000
        )
        
        logger.info(f"✅ UI 업데이트 완료 (총 {len(self.collected_messages)}개 메시지)")
    
    def _auto_start_analysis(self):
        """연결 성공 후 자동으로 분석 시작"""
        try:
            logger.info("🚀 자동 분석 시작")
            self.status_message.setText("자동 분석 시작 중...")
            
            # VirtualOffice 모드인 경우에만 자동 분석
            if self.data_source_type == "virtualoffice" and self.selected_persona:
                # 메시지 수집 시작 (자동)
                self.start_collection()
            else:
                logger.warning("⚠️ VirtualOffice 모드가 아니거나 페르소나가 선택되지 않음")
                self.status_message.setText("VirtualOffice 모드로 전환하고 페르소나를 선택하세요")
        except Exception as e:
            logger.error(f"❌ 자동 분석 시작 오류: {e}", exc_info=True)
            self.status_message.setText(f"자동 분석 오류: {e}")
    
    def _process_new_messages_async(self, new_messages: list) -> None:
        """새 메시지에 대한 분석 및 TODO 생성 (백그라운드 처리)"""
        self.analysis_controller._process_new_messages_async(new_messages)
    
    def _handle_background_analysis_result(self, result):
        """백그라운드 분석 결과 처리"""
        self.analysis_controller._handle_background_analysis_result(result)
    
    def _handle_background_analysis_error(self, error_msg):
        """백그라운드 분석 오류 처리"""
        self.analysis_controller._handle_background_analysis_error(error_msg)
    
    def _trigger_reanalysis(self):
        """전체 메시지 재분석 트리거"""
        self.analysis_controller._trigger_reanalysis()
    
    def _handle_reanalysis_result(self, result):
        """재분석 결과 처리"""
        self.analysis_controller._handle_reanalysis_result(result)
    
    def _build_cache_key(self) -> 'CacheKey':
        """현재 상태로 캐시 키 생성
        
        시간 범위는 캐시 키에 포함하지 않습니다.
        시간 범위 필터링은 캐시된 데이터에서 UI 레벨에서 처리됩니다.
        
        Returns:
            CacheKey: 생성된 캐시 키
        """
        return self.analysis_controller._build_cache_key()
    
    def _display_cached_result(self, cached_result: 'CachedAnalysisResult') -> None:
        """캐시된 분석 결과를 UI에 표시
        
        Args:
            cached_result: 캐시된 분석 결과
        """
        self.analysis_controller._display_cached_result(cached_result)
    
    def _save_to_cache(
        self,
        todo_list: List[Dict[str, Any]],
        messages: List[Dict[str, Any]],
        analysis_results: List[Dict[str, Any]]
    ) -> None:
        """분석 결과를 캐시에 저장"""
        self.analysis_controller._save_to_cache(todo_list, messages, analysis_results)
    
    def _should_use_cache(self, persona_key: str) -> bool:
        """캐시 사용 여부 결정
        
        Args:
            persona_key: 페르소나 식별 키
            
        Returns:
            bool: 캐시 사용 가능 여부
        """
        return self.analysis_controller._should_use_cache(persona_key)
    
    def _trigger_immediate_polling(self) -> None:
        """페르소나 변경 시 즉시 폴링 트리거"""
        self.analysis_controller._trigger_immediate_polling()
    
    def _get_simulation_status(self) -> tuple[int, bool]:
        """시뮬레이션 상태 조회
        
        Returns:
            tuple: (current_tick, is_running)
        """
        return self.analysis_controller._get_simulation_status()
    
    def _load_from_cache(self, persona_key: str) -> None:
        """캐시에서 데이터 로드
        
        Args:
            persona_key: 페르소나 식별 키
        """
        self.analysis_controller._load_from_cache(persona_key)
    
    def _collect_and_cache_data(self, persona_key: str) -> None:
        """데이터 수집 및 캐시 저장
        
        Args:
            persona_key: 페르소나 식별 키
        """
        self.analysis_controller._collect_and_cache_data(persona_key)
    
    def _update_cache_with_analysis_results(self, todos: List[Dict], analysis_results: List[Dict]) -> None:
        """백그라운드 분석 결과로 캐시 업데이트"""
        self.analysis_controller._update_cache_with_analysis_results(todos, analysis_results)
    
    def _update_polling_worker_persona(self, persona) -> None:
        """PollingWorker의 페르소나만 업데이트 (재시작 없이)
        
        Args:
            persona: 새 페르소나 정보
        """
        self.analysis_controller._update_polling_worker_persona(persona)
    
    def _restart_polling_worker(self) -> None:
        """PollingWorker 재시작"""
        self.analysis_controller._restart_polling_worker()
    
    def _start_polling_worker(self) -> None:
        """PollingWorker 시작"""
        self.analysis_controller._start_polling_worker()
    
    def _update_ui_from_cache(self, cached_data: Dict) -> None:
        """캐시 데이터로 UI 업데이트
        
        Args:
            cached_data: 캐시된 데이터
        """
        self.analysis_controller._update_ui_from_cache(cached_data)
    
    def _update_ui_from_cache_only(self, messages: List[Dict]) -> None:
        """캐시에서 로드한 데이터로 UI만 업데이트 (백그라운드 분석 없음)
        
        Args:
            messages: 메시지 리스트
        """
        self.analysis_controller._update_ui_from_cache_only(messages)
    
    def _update_ui_with_new_data(self, messages: List[Dict]) -> None:
        """새 데이터로 모든 UI 패널 업데이트
        
        Args:
            messages: 메시지 리스트
        """
        self.analysis_controller._update_ui_with_new_data(messages)

    def _trigger_background_analysis(self, messages: List[Dict]) -> None:
        """백그라운드에서 분석 실행 (TODO 생성)
        
        Args:
            messages: 분석할 메시지 리스트
        """
        self.analysis_controller._trigger_background_analysis(messages)

    def _quick_analysis(self, messages: List[Dict]) -> None:
        """빠른 분석 (개선된 TODO 생성)
        
        Args:
            messages: 분석할 메시지 리스트
        """
        self.analysis_controller._quick_analysis(messages)

    def _invalidate_all_cache(self) -> None:
        """모든 캐시 무효화"""
        self.analysis_controller._invalidate_all_cache()
    
    def _force_update_project_tags(self) -> None:
        """프로젝트 태그 바 강제 업데이트"""
        self.analysis_controller._force_update_project_tags()
    
    def _clear_todos_for_persona_change(self) -> None:
        """페르소나 변경 시 TODO 데이터베이스 초기화"""
        self.analysis_controller._clear_todos_for_persona_change()
    
    def _restore_todos_from_cache(self, cached_todos: List[Dict]) -> None:
        """캐시된 TODO를 데이터베이스와 UI에 복원"""
        self.analysis_controller._restore_todos_from_cache(cached_todos)
    
    def _show_visual_notification(self):
        """시각적 알림 효과 표시
        
        중앙 위젯에 플래시 효과를 표시합니다.
        """
        self.analysis_controller._show_visual_notification()

    def _show_progress_bar(self, message: str = "처리 중..."):
        """프로그레스 바 표시 (UI 반응성 개선)
        
        장시간 작업 시 프로그레스 바를 표시하여 사용자에게 진행 상황을 알립니다.
        
        Args:
            message: 표시할 메시지
        
        Example:
            >>> self._show_progress_bar("데이터 수집 중...")
        """
        self.analysis_controller._show_progress_bar(message)
    
    def _update_progress_bar(self, value: int):
        """프로그레스 바 업데이트
        
        Args:
            value: 진행률 (0-100)
        
        Example:
            >>> self._update_progress_bar(50)
        """
        self.analysis_controller._update_progress_bar(value)
    
    def _hide_progress_bar(self):
        """프로그레스 바 숨기기
        
        Example:
            >>> self._hide_progress_bar()
        """
        self.analysis_controller._hide_progress_bar()
    
    def _update_timeline_with_badges(self):
        """타임라인 업데이트 (NEW 배지 포함)
        
        타임라인 목록을 업데이트하고 새 메시지에 NEW 배지를 표시합니다.
        """
        self.analysis_controller._update_timeline_with_badges()
    

    def on_polling_error(self, error_msg: str):
        """폴링 오류 핸들러
        
        Args:
            error_msg: 오류 메시지
        """
        logger.error(f"❌ 폴링 오류: {error_msg}")
        self.statusBar().showMessage(f"⚠️ 데이터 수집 오류: {error_msg}", 10000)
    
    def on_sim_status_updated(self, status):
        """시뮬레이션 상태 업데이트 핸들러
        
        Args:
            status: SimulationStatus 객체 또는 딕셔너리
        """
        try:
            # SimulationStatus 객체인지 딕셔너리인지 확인
            if hasattr(status, 'current_tick'):
                # SimulationStatus 객체인 경우
                current_tick = status.current_tick
                is_running = status.is_running
                auto_tick = status.auto_tick
                sim_time = status.sim_time
            else:
                # 딕셔너리인 경우 (하위 호환성)
                current_tick = status['current_tick']
                is_running = status['is_running']
                auto_tick = status['auto_tick']
                sim_time = status['sim_time']
            
            # 실행 상태 표시 업데이트 (아이콘 + 텍스트)
            if hasattr(self, 'sim_running_status'):
                if is_running:
                    self.sim_running_status.setText("🟢 실행 중")
                    self.sim_running_status.setStyleSheet("""
                        QLabel {
                            color: #059669;
                            background-color: #D1FAE5;
                            padding: 6px 10px;
                            border-radius: 4px;
                            font-weight: 600;
                            font-size: 12px;
                            border: 1px solid #10B981;
                        }
                    """)
                else:
                    self.sim_running_status.setText("🔴 정지됨")
                    self.sim_running_status.setStyleSheet("""
                        QLabel {
                            color: #DC2626;
                            background-color: #FEE2E2;
                            padding: 6px 10px;
                            border-radius: 4px;
                            font-weight: 600;
                            font-size: 12px;
                            border: 1px solid #EF4444;
                        }
                    """)
            
            # 진행률 바 업데이트
            if hasattr(self, 'sim_progress_bar'):
                # 진행률 바의 최대값을 동적으로 조정 (현재 틱의 1.2배)
                if current_tick > self.sim_progress_bar.maximum():
                    self.sim_progress_bar.setMaximum(int(current_tick * 1.2))
                
                self.sim_progress_bar.setValue(current_tick)
                self.sim_progress_bar.setFormat(f"Tick: {current_tick:,}")
                
                # 실행 상태에 따라 진행률 바 색상 변경
                if is_running:
                    self.sim_progress_bar.setStyleSheet("""
                        QProgressBar {
                            border: 1px solid #10B981;
                            border-radius: 4px;
                            background-color: #F3F4F6;
                            text-align: center;
                            height: 20px;
                            font-size: 11px;
                            font-weight: 600;
                            color: #065F46;
                        }
                        QProgressBar::chunk {
                            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #10B981, stop:1 #059669);
                            border-radius: 3px;
                        }
                    """)
                else:
                    self.sim_progress_bar.setStyleSheet("""
                        QProgressBar {
                            border: 1px solid #D1D5DB;
                            border-radius: 4px;
                            background-color: #F3F4F6;
                            text-align: center;
                            height: 20px;
                            font-size: 11px;
                            font-weight: 600;
                            color: #6B7280;
                        }
                        QProgressBar::chunk {
                            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #9CA3AF, stop:1 #6B7280);
                            border-radius: 3px;
                        }
                    """)
            
            # 상세 정보 표시 업데이트
            auto_tick_icon = "✅" if auto_tick else "⏸️"
            status_text = (
                f"🕐 Tick: {current_tick:,}\n"
                f"📅 시간: {sim_time}\n"
                f"{auto_tick_icon} 자동 틱: {'활성화' if auto_tick else '비활성화'}"
            )
            
            if hasattr(self, 'sim_status_display'):
                self.sim_status_display.setText(status_text)
                
                # 실행 상태에 따라 배경 색상 변경
                if is_running:
                    self.sim_status_display.setStyleSheet("""
                        QLabel {
                            color: #065F46;
                            background-color: #ECFDF5;
                            padding: 8px;
                            border-radius: 4px;
                            border: 1px solid #A7F3D0;
                            font-size: 11px;
                            font-family: 'Consolas', 'Monaco', monospace;
                        }
                    """)
                else:
                    self.sim_status_display.setStyleSheet("""
                        QLabel {
                            color: #374151;
                            background-color: #F9FAFB;
                            padding: 8px;
                            border-radius: 4px;
                            border: 1px solid #E5E7EB;
                            font-size: 11px;
                            font-family: 'Consolas', 'Monaco', monospace;
                        }
                    """)
            
            # 캐시 관리 (틱 변경 시 캐시 무효화)
            # 유효한 틱 변경만 감지 (0은 오류 상태이므로 무시)
            if (self._last_simulation_tick is not None and 
                current_tick > 0 and 
                current_tick != self._last_simulation_tick):
                logger.info(f"🔄 틱 변경 감지 ({self._last_simulation_tick} → {current_tick}) - 캐시 무효화")
                self._invalidate_all_cache()
            
            # 시뮬레이션 상태 업데이트 (유효한 틱 값이 있을 때만)
            if current_tick > 0 or self._last_simulation_tick is None:
                self._last_simulation_tick = current_tick
            self._simulation_running = is_running
            
            # 폴링 간격 조정 (시뮬레이션이 일시정지되면 폴링 간격 증가)
            if self.polling_worker:
                if is_running:
                    self.polling_worker.set_polling_interval(30)  # 30초
                else:
                    self.polling_worker.set_polling_interval(60)  # 1분
            
            logger.debug(f"시뮬레이션 상태 업데이트: Tick {current_tick}, 실행={is_running}")
            
        except Exception as e:
            logger.error(f"❌ 시뮬레이션 상태 업데이트 오류: {e}", exc_info=True)
    
    def on_tick_advanced(self, tick: int):
        """틱 진행 알림 핸들러
        
        Args:
            tick: 새로운 틱 번호
        """
        try:
            logger.info(f"⏰ Tick {tick} 진행됨")
            
            # 데이터 버전 업데이트
            self._current_data_version = str(tick)
            
            # 모든 캐시 무효화 (새 데이터 추가됨)
            invalidated_count = self._cache_service.invalidate_all()
            logger.info(f"🗑️ 틱 진행으로 전체 캐시 무효화: {invalidated_count}개")
            
            # 상태바에 틱 진행 메시지 표시
            self.statusBar().showMessage(f"⏰ Tick {tick} 진행됨", 3000)
            
            # 현재 페르소나가 선택되어 있으면 자동 재분석
            if self.selected_persona and self._current_persona_id:
                logger.info(f"🔄 현재 페르소나 자동 재분석 시작: {self.selected_persona.name}")
                # 재분석은 폴링 워커가 자동으로 수행하므로 여기서는 로그만 남김
                # 필요시 명시적으로 재분석을 트리거할 수 있음
            
            # 선택적: 틱별 활동 요약 표시
            # 최근 수집된 데이터 개수를 표시할 수 있습니다
            if hasattr(self, 'collected_messages'):
                recent_count = len([
                    msg for msg in self.collected_messages
                    if msg.get('metadata', {}).get('tick') == tick
                ])
                
                if recent_count > 0:
                    logger.info(f"  └─ Tick {tick}에서 {recent_count}개 메시지 수집됨")
                    self.statusBar().showMessage(
                        f"⏰ Tick {tick} 진행됨 ({recent_count}개 새 메시지)",
                        3000
                    )
            
        except Exception as e:
            logger.error(f"❌ 틱 진행 알림 오류: {e}", exc_info=True)
    
    def show_tick_history(self):
        """틱 히스토리 다이얼로그 표시"""
        try:
            if not hasattr(self, 'sim_monitor') or self.sim_monitor is None:
                QMessageBox.warning(
                    self,
                    "경고",
                    "VirtualOffice에 연결되지 않았습니다.\n먼저 연결을 수행해주세요."
                )
                return
            
            # 틱 히스토리 조회
            history = self.sim_monitor.get_tick_history(limit=100)
            
            if not history:
                QMessageBox.information(
                    self,
                    "틱 히스토리",
                    "아직 기록된 틱 히스토리가 없습니다.\n시뮬레이션이 진행되면 히스토리가 쌓입니다."
                )
                return
            
            # 다이얼로그 생성 및 표시
            dialog = TickHistoryDialog(self)
            
            # 새로고침 버튼 동작 연결
            def refresh():
                updated_history = self.sim_monitor.get_tick_history(limit=100)
                dialog.set_history(updated_history)
            
            dialog.refresh_requested = refresh
            
            # 히스토리 설정
            dialog.set_history(history)
            
            # 다이얼로그 표시
            dialog.exec()
            
            logger.info(f"틱 히스토리 다이얼로그 표시: {len(history)}개 항목")
            
        except Exception as e:
            logger.error(f"❌ 틱 히스토리 표시 오류: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "오류",
                f"틱 히스토리를 표시하는 중 오류가 발생했습니다:\n{e}"
            )
    
    def closeEvent(self, event):
        """창 닫기 이벤트"""
        # WorkerThread 정리
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.stop()
            self.worker_thread.wait(3000)
        
        # PollingWorker 정리
        if self.polling_worker and self.polling_worker.isRunning():
            logger.info("PollingWorker 중지 중...")
            self.polling_worker.stop()
            self.polling_worker.wait(3000)
            logger.info("✅ PollingWorker 중지됨")
        
        # SimulationMonitor 정리
        if self.sim_monitor:
            logger.info("SimulationMonitor 중지 중...")
            self.sim_monitor.stop_monitoring()
            logger.info("✅ SimulationMonitor 중지됨")
        
        event.accept()
    
    def _update_connection_status(self):
        """연결 상태 레이블 업데이트 (두 레이블 모두)"""
        try:
            if hasattr(self, 'vo_client') and self.vo_client:
                # 연결되어 있으면 상태 업데이트
                persona_count = self.persona_combo.count() if hasattr(self, 'persona_combo') else 0
                if persona_count > 0:
                    text = f"✅ 연결 성공 ({persona_count}개 페르소나)"
                    style = """
                        QLabel {
                            color: #059669;
                            background-color: #D1FAE5;
                            padding: 6px;
                            border-radius: 4px;
                            font-size: 11px;
                            font-weight: 600;
                        }
                    """
                    logger.info(f"✅ 연결 상태 레이블 업데이트: {persona_count}개 페르소나")
                else:
                    # 연결은 되었지만 페르소나가 없는 경우
                    text = "⚠️ 연결됨 (페르소나 없음)"
                    style = """
                        QLabel {
                            color: #D97706;
                            background-color: #FEF3C7;
                            padding: 6px;
                            border-radius: 4px;
                            font-size: 11px;
                            font-weight: 600;
                        }
                    """
                    logger.warning("⚠️ 연결 상태 레이블 업데이트: 페르소나 없음")
                
                # 연결 상태 레이블 업데이트
                if hasattr(self, 'vo_connection_status_label'):
                    self.vo_connection_status_label.setText(text)
                    self.vo_connection_status_label.setStyleSheet(style)
            else:
                # 연결되지 않은 경우
                text = "❌ 연결되지 않음"
                style = """
                    QLabel {
                        color: #DC2626;
                        background-color: #FEE2E2;
                        padding: 6px;
                        border-radius: 4px;
                        font-size: 11px;
                        font-weight: 600;
                    }
                """
                
                # 연결 상태 레이블 업데이트
                if hasattr(self, 'vo_connection_status_label'):
                    self.vo_connection_status_label.setText(text)
                    self.vo_connection_status_label.setStyleSheet(style)
        except Exception as e:
            logger.error(f"연결 상태 업데이트 오류: {e}")
    
    def _load_vo_config(self):
        """VirtualOffice 설정 파일 로드
        
        저장된 설정 파일이 있으면 로드하여 UI에 반영합니다.
        환경 변수가 설정되어 있으면 환경 변수가 우선합니다.
        """
        try:
            # 환경 변수 확인 (우선순위 높음)
            email_url_env = os.environ.get("VDOS_EMAIL_URL")
            chat_url_env = os.environ.get("VDOS_CHAT_URL")
            sim_url_env = os.environ.get("VDOS_SIM_URL")
            
            # 설정 파일 로드 시도
            if self.vo_config_path.exists():
                logger.info(f"VirtualOffice 설정 파일 로드 중: {self.vo_config_path}")
                self.vo_config = VirtualOfficeConfig.load_from_file(self.vo_config_path)
                logger.info("✅ VirtualOffice 설정 파일 로드 완료")
                
                # 환경 변수로 덮어쓰기
                if email_url_env:
                    self.vo_config.email_url = email_url_env
                    logger.info("환경 변수 VDOS_EMAIL_URL 적용")
                if chat_url_env:
                    self.vo_config.chat_url = chat_url_env
                    logger.info("환경 변수 VDOS_CHAT_URL 적용")
                if sim_url_env:
                    self.vo_config.sim_url = sim_url_env
                    logger.info("환경 변수 VDOS_SIM_URL 적용")
                
                # UI에 반영
                if hasattr(self, 'vo_email_url'):
                    self.vo_email_url.setText(self.vo_config.email_url)
                if hasattr(self, 'vo_chat_url'):
                    self.vo_chat_url.setText(self.vo_config.chat_url)
                if hasattr(self, 'vo_sim_url'):
                    self.vo_sim_url.setText(self.vo_config.sim_url)
                
                logger.info(f"설정 적용: email={self.vo_config.email_url}, chat={self.vo_config.chat_url}, sim={self.vo_config.sim_url}")
                
                # 설정이 로드되면 상태 레이블 업데이트 (아직 연결되지 않음)
                config_loaded_text = "⚙️ 설정 로드됨 (연결 대기 중)"
                config_loaded_style = """
                    QLabel {
                        color: #2563EB;
                        background-color: #DBEAFE;
                        padding: 6px;
                        border-radius: 4px;
                        font-size: 11px;
                        font-weight: 600;
                    }
                """
                
                # 연결 상태 레이블 업데이트
                if hasattr(self, 'vo_connection_status_label'):
                    self.vo_connection_status_label.setText(config_loaded_text)
                    self.vo_connection_status_label.setStyleSheet(config_loaded_style)
            else:
                logger.info("VirtualOffice 설정 파일이 없습니다. 기본값 사용")
                # 환경 변수만 적용
                if email_url_env or chat_url_env or sim_url_env:
                    self.vo_config = VirtualOfficeConfig(
                        email_url=email_url_env or "http://127.0.0.1:8000",
                        chat_url=chat_url_env or "http://127.0.0.1:8001",
                        sim_url=sim_url_env or "http://127.0.0.1:8015"
                    )
                    if hasattr(self, 'vo_email_url'):
                        self.vo_email_url.setText(self.vo_config.email_url)
                    if hasattr(self, 'vo_chat_url'):
                        self.vo_chat_url.setText(self.vo_config.chat_url)
                    if hasattr(self, 'vo_sim_url'):
                        self.vo_sim_url.setText(self.vo_config.sim_url)
                    logger.info("환경 변수로 설정 적용")
        
        except Exception as e:
            logger.warning(f"VirtualOffice 설정 로드 실패: {e}")
            self.vo_config = None
    
    def _save_vo_config(self):
        """VirtualOffice 설정 파일 저장
        
        현재 UI의 설정을 파일에 저장합니다.
        """
        try:
            # 현재 UI 값으로 설정 객체 생성
            email_url = self.vo_email_url.text().strip()
            chat_url = self.vo_chat_url.text().strip()
            sim_url = self.vo_sim_url.text().strip()
            
            if not email_url or not chat_url or not sim_url:
                logger.warning("설정 저장 실패: URL이 비어있습니다")
                return
            
            # 선택된 페르소나 정보
            selected_persona_email = None
            if self.selected_persona:
                selected_persona_email = self.selected_persona.email_address
            
            # 설정 객체 생성
            self.vo_config = VirtualOfficeConfig(
                email_url=email_url,
                chat_url=chat_url,
                sim_url=sim_url,
                polling_interval=30,  # 30초
                selected_persona=selected_persona_email
            )
            
            # 파일에 저장
            self.vo_config.save_to_file(self.vo_config_path)
            logger.info(f"✅ VirtualOffice 설정 저장 완료: {self.vo_config_path}")
            
        except Exception as e:
            logger.error(f"VirtualOffice 설정 저장 실패: {e}")
    
    def _on_project_filter_changed(self, project_code: str):
        """프로젝트 필터 변경 핸들러"""
        try:
            if hasattr(self, 'todo_panel'):
                self.todo_panel.filter_by_project(project_code if project_code else None)
        except Exception as e:
            logger.error(f"프로젝트 필터 변경 오류: {e}")
    
    def _update_time_range_selector_data_range(self, messages: List[Dict]) -> None:
        """TimeRangeSelector에 실제 데이터 범위 설정
        
        Args:
            messages: 메시지 리스트
        """
        try:
            if not messages:
                logger.debug("메시지가 없어 데이터 범위를 설정할 수 없음")
                return
            
            # 메시지에서 시간 정보 추출
            message_times = []
            
            for message in messages:
                # 다양한 시간 필드 확인
                time_str = (
                    message.get('date') or 
                    message.get('timestamp') or 
                    message.get('sent_at') or
                    message.get('created_at') or
                    message.get('time')
                )
                
                if time_str:
                    try:
                        # 시간 파싱 시도
                        if isinstance(time_str, str):
                            # ISO 형식 시도
                            if 'T' in time_str:
                                message_time = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                            else:
                                # 다른 형식들 시도
                                for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d']:
                                    try:
                                        message_time = datetime.strptime(time_str, fmt)
                                        break
                                    except ValueError:
                                        continue
                                else:
                                    continue
                        elif isinstance(time_str, datetime):
                            message_time = time_str
                        else:
                            continue
                            
                        message_times.append(message_time)
                        
                    except Exception as parse_error:
                        logger.debug(f"시간 파싱 실패: {time_str} - {parse_error}")
                        continue
            
            if not message_times:
                logger.debug("메시지에서 유효한 시간 정보를 찾을 수 없음")
                return
            
            # 최소/최대 시간 계산
            min_time = min(message_times)
            max_time = max(message_times)
            
            # TimeRangeSelector에 데이터 범위 설정
            if hasattr(self, 'left_control_panel') and hasattr(self.left_control_panel, 'time_range_selector'):
                self.left_control_panel.time_range_selector.set_data_range(min_time, max_time)
                
                min_str = min_time.strftime('%Y-%m-%d %H:%M')
                max_str = max_time.strftime('%Y-%m-%d %H:%M')
                logger.info(f"📅 데이터 범위 설정: {min_str} ~ {max_str}")
            else:
                logger.debug("TimeRangeSelector를 찾을 수 없음")
            
        except Exception as e:
            logger.error(f"데이터 범위 설정 오류: {e}", exc_info=True)
    
    def _start_data_collection_with_time_filter(self):
        """시간 필터링을 적용한 데이터 수집 시작"""
        try:
            if not self.vo_client or not self.selected_persona:
                logger.warning("VirtualOffice 연결 또는 페르소나가 설정되지 않음")
                return
            
            logger.info("🔄 시간 필터링 적용된 데이터 수집 시작")
            
            # 기존 워커 스레드가 실행 중이면 중지
            if hasattr(self, 'worker_thread') and self.worker_thread and self.worker_thread.isRunning():
                logger.info("기존 워커 스레드 중지 중...")
                self.worker_thread.quit()
                self.worker_thread.wait(2000)
            
            # 새로운 워커 스레드로 데이터 수집 시작
            from .widgets.worker_thread import WorkerThread
            
            dataset_config = dict(self.dataset_config)
            collect_options = {
                "email_limit": None,
                "messenger_limit": None,
                "overall_limit": None,
                "force_reload": True,
            }
            
            self.worker_thread = WorkerThread(self.assistant, dataset_config, collect_options)
            self.worker_thread.progress_updated.connect(self.progress_bar.setValue)
            self.worker_thread.status_updated.connect(self.status_message.setText)
            self.worker_thread.result_ready.connect(self._handle_reanalysis_result)
            self.worker_thread.error_occurred.connect(self.data_controller.handle_error)
            
            # UI 상태 업데이트
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            self.status_message.setText("시간 범위 적용된 데이터 수집 중...")
            
            self.worker_thread.start()
            
        except Exception as e:
            logger.error(f"시간 필터링 데이터 수집 시작 오류: {e}", exc_info=True)
            self.status_message.setText(f"데이터 수집 시작 오류: {e}")


def main():
    """메인 함수"""
    app = QApplication(sys.argv)
    
    # 한글 폰트 설정
    font = QFont("맑은 고딕", 9)
    app.setFont(font)
    
    window = SmartAssistantGUI()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
