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


from typing import Dict, List, Optional
from pathlib import Path

from datetime import datetime, timezone, timedelta
from collections import Counter
import math, uuid, json, sqlite3
import requests

# 로거 초기화
logger = logging.getLogger(__name__)

from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtWidgets import QApplication, QStyleFactory


import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def _make_http_session():
    """HTTP 세션 생성 (재시도 로직 포함)
    
    네트워크 오류 시 자동으로 재시도하는 HTTP 세션을 생성합니다.
    
    재시도 설정:
    - 최대 3회 재시도
    - 백오프 팩터: 0.6초
    - 재시도 대상 상태 코드: 502, 503, 504
    - 허용 메서드: GET, POST
    
    Returns:
        requests.Session: 재시도 로직이 적용된 HTTP 세션
    """
    retry = Retry(
        total=3, connect=3, read=3,
        backoff_factor=0.6,
        status_forcelist=(502, 503, 504),
        allowed_methods=("GET", "POST"),
        raise_on_status=False,
    )
    s = requests.Session()
    adapter = HTTPAdapter(max_retries=retry)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s


TODO_DB_PATH = os.path.join("data", "multi_project_8week_ko", "todos_cache.db")  # v1.2.0: 데이터셋 변경

KMA_CITY_GRID = {
    "서울": (60, 127),
    "Seoul": (60, 127),
    "부산": (98, 76),
    "Busan": (98, 76),
    "대구": (89, 90),
    "Daegu": (89, 90),
    "인천": (55, 124),
    "Incheon": (55, 124),
    "광주": (58, 74),
    "Gwangju": (58, 74),
    "대전": (67, 100),
    "Daejeon": (67, 100),
}

KMA_CITY_ALIAS = {
    "서울": "Seoul",
    "부산": "Busan",
    "대구": "Daegu",
    "인천": "Incheon",
    "광주": "Gwangju",
    "대전": "Daejeon",
}

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

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextEdit, QTabWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QGroupBox, QLineEdit, QProgressBar, QStatusBar,
    QFrame, QMessageBox, QStyleFactory, QListWidget, QListWidgetItem,
    QDialog, QDialogButtonBox, QScrollArea, QSizePolicy)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QObject, QEvent
from PyQt6.QtGui import QFont, QPalette, QColor
from pathlib import Path
import asyncio, json, os, sys


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


# 한 번만 실행(어디든 붙여서 호출)
def recompute_top3_in_db(db_path="data/mobile_4week_ko/todos_cache.db"):
    import sqlite3, json
    from datetime import datetime, timezone
    def score(r):
        p=(r.get("priority") or "low").lower()
        wp={"high":3,"medium":2,"low":1}.get(p,1)
        now=datetime.now(timezone.utc)
        dl=r.get("deadline_ts") or r.get("deadline")
        try:
            dl=dl and (datetime.fromisoformat(dl.replace("Z","+00:00")) if "Z" in dl else datetime.fromisoformat(dl))
        except: dl=None
        wd=1.0
        if dl:
            if dl.tzinfo is None: dl=dl.replace(tzinfo=timezone.utc)
            h=max(0,(dl-now).total_seconds()/3600)
            wd=1+24/(24+h)
        ev=r.get("evidence") or "[]"
        try: n=len(ev if isinstance(ev,list) else json.loads(ev))
        except: n=0
        we=1+min(0.5,0.1*n)
        return wp*wd*we
    conn=sqlite3.connect(db_path); conn.row_factory=sqlite3.Row
    cur=conn.cursor(); cur.execute("SELECT * FROM todos WHERE status!='done'")
    rows=[dict(x) for x in cur.fetchall()]
    if not rows: conn.close(); return
    for r in rows: r["_s"]=score(r)
    rows.sort(key=lambda x:(x["_s"], x.get("created_at","")), reverse=True)
    top=[r["id"] for r in rows[:3] if r.get("id")]
    cur.execute("UPDATE todos SET is_top3=0")
    if top: cur.execute(f"UPDATE todos SET is_top3=1 WHERE id IN ({','.join('?'*len(top))})", top)
    conn.commit(); conn.close()



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


def _score_for_top3(t: dict) -> float:
    # 우선순위 가중치
    p = (t.get("priority") or "low").lower()
    w_priority = {"high": 3.0, "medium": 2.0, "low": 1.0}.get(p, 1.0)

    # 데드라인 임박 가중치(없으면 약하게)
    now = datetime.now(timezone.utc)
    deadline = t.get("deadline_ts") or t.get("deadline")
    if deadline:
        try:
            dl = datetime.fromisoformat(deadline.replace("Z","+00:00"))
        except Exception:
            try:
                dl = datetime.fromisoformat(deadline)
            except Exception:
                dl = None
    else:
        dl = None
    if dl:
        hours_left = max(0.0, (dl - now).total_seconds() / 3600.0)
        w_deadline = 1.0 + (24.0 / (24.0 + hours_left))  # 0~24h 임박할수록 ~2.0
    else:
        w_deadline = 1.0

    # 액션/근거가 많은 것도 약간 가산
    reasons = t.get("evidence")
    if not isinstance(reasons, list):
        try: reasons = json.loads(reasons or "[]")
        except: reasons = []
    w_evidence = 1.0 + min(0.5, 0.1 * len(reasons))     # 최대 +0.5

    return w_priority * w_deadline * w_evidence

def _pick_top3(items: list[dict]) -> set[str]:
    # status가 done/snoozed가 아닌 것만 후보
    cand = [x for x in items if (x.get("status") or "pending") not in ("done",)]
    # 점수 계산
    for x in cand:
        x["_top3_score"] = _score_for_top3(x)
    # 점수 > created_at 최신 순으로 정렬
    def _created_iso(x):
        return x.get("created_at") or datetime.now().isoformat()
    cand.sort(key=lambda x: (x["_top3_score"], _created_iso(x)), reverse=True)
    top = cand[:3]
    return {x.get("id") or "" for x in top if x.get("id")}

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
        }, **(t or {})}

        # ID 없으면 자동 생성
        if not t.get("id"):
            t["id"] = uuid.uuid4().hex

        # evidence가 list면 문자열로, dict면 그대로 list→문자열 변환
        if not isinstance(t.get("evidence"), str):
            t["evidence"] = json.dumps(t.get("evidence") or [], ensure_ascii=False)

        prepared.append(t)

    # 1) 이번 배치에서 Top-3 자동 선정 (이미 is_top3가 True면 존중)
    auto_top_ids = _pick_top3([x for x in prepared if not x.get("is_top3")])

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
         draft_subject, draft_body, evidence, deadline_confidence)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        ))

    conn.commit()
    conn.close()

class WorkerThread(QThread):
    """백그라운드 작업 스레드"""
    progress_updated = pyqtSignal(int)
    status_updated = pyqtSignal(str)
    result_ready = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, assistant, dataset_config, collect_options):
        super().__init__()
        self.assistant = assistant
        self.dataset_config = dataset_config or {}
        self.collect_options = collect_options or {}
        self.collect_options.setdefault("force_reload", True)
        self._should_stop = False
    
    def run(self):
        try:
            # 비동기 작업을 동기적으로 실행
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            self.status_updated.emit("시스템 초기화 중...")
            loop.run_until_complete(self.assistant.initialize(self.dataset_config))
            
            self.status_updated.emit("메시지 수집 중...")
            self.progress_updated.emit(20)
            
            messages = loop.run_until_complete(
                self.assistant.collect_messages(**self.collect_options)
            )
            
            if not messages:
                self.error_occurred.emit("수집된 메시지가 없습니다.")
                return
            
            self.status_updated.emit("AI 분석 중...")
            self.progress_updated.emit(50)
            
            analysis_results = loop.run_until_complete(self.assistant.analyze_messages())
            
            self.status_updated.emit("TODO 리스트 생성 중...")
            self.progress_updated.emit(80)
            todo_list = loop.run_until_complete(self.assistant.generate_todo_list(analysis_results))

            self.progress_updated.emit(100)
            self.status_updated.emit("완료")
            
            result = {
                "success": True,
                "todo_list": todo_list,
                "analysis_results": analysis_results,
                "messages": messages,
                "analysis_report_text": getattr(self.assistant, "analysis_report_text", "")  # ✅ 추가
            }
            
            self.result_ready.emit(result)


            
        except Exception as e:
            self.error_occurred.emit(f"오류 발생: {str(e)}")
        finally:
            loop.close()
    
    def stop(self):
        self._should_stop = True


class StatusIndicator(QLabel):
    """상태 표시기"""
    def __init__(self, text="오프라인"):
        super().__init__(text)
        self.setFixedSize(100, 30)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                border: 2px solid #ccc;
                border-radius: 15px;
                background-color: #f0f0f0;
                color: #666;
                font-weight: bold;
            }
        """)
        self.current_status = "offline"
    
    def set_status(self, status):
        self.current_status = status
        if status == "online":
            self.setText("온라인")
            self.setStyleSheet("""
                QLabel {
                    border: 2px solid #4CAF50;
                    border-radius: 15px;
                    background-color: #E8F5E8;
                    color: #2E7D32;
                    font-weight: bold;
                }
            """)
        else:
            self.setText("오프라인")
            self.setStyleSheet("""
                QLabel {
                    border: 2px solid #ccc;
                    border-radius: 15px;
                    background-color: #f0f0f0;
                    color: #666;
                    font-weight: bold;
                }
            """)


class EmojiLabel(QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        f = self.font()
        f.setFamily("Segoe UI Emoji")  # 이모지 전용 폰트
        self.setFont(f)


class SmartAssistantGUI(QMainWindow):
    """Smart Assistant 메인 GUI"""
    
    def __init__(self):
        super().__init__()
        self.assistant = SmartAssistant()
        self.worker_thread = None
        self.current_status = "offline"
        self.dataset_config = {
            "dataset_root": str(DEFAULT_DATASET_ROOT),
            "force_reload": False,
        }
        self.collect_options = {
            "email_limit": None,
            "messenger_limit": None,
            "overall_limit": None,
            "force_reload": True,
        }
        self.analysis_results: List[Dict] = []
        self.collected_messages: List[Dict] = []
        self.kma_api_key = os.environ.get("KMA_API_KEY")
        self.init_ui()
        self.setup_timers()
        self.initialize_online_state()
        # SmartAssistantGUI.__init__() 안
        self.http = _make_http_session()

    
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
        """좌측 패널 생성 (스크롤 가능)"""
        from PyQt6.QtWidgets import QScrollArea
        from PyQt6.QtCore import Qt
        
        # 스크롤 영역 생성
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        # 폭 계산은 패널 구성 후 sizeHint 기준으로 설정하여 잘림 방지
        scroll_area.setFrameStyle(QFrame.Shape.NoFrame)
        # 수평 스크롤은 필요 시 표시(안전망)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # 실제 컨텐츠 패널
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(13, 13, 13, 13)  # 마진 축소 (기본 11 → 8)
        layout.setSpacing(10)  # 간격 축소
        
        # 제목
        title = QLabel("OFFLINE-AGENT")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))  # 16 → 14로 축소
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #2c3e50; margin: 8px;")  # margin도 축소
        layout.addWidget(title)
        
        # 상태 표시기
        status_group = QGroupBox("연결 상태")
        status_layout = QVBoxLayout(status_group)
        
        self.status_indicator = StatusIndicator()
        status_layout.addWidget(self.status_indicator)
        
        # 상태 토글 버튼
        self.status_button = QPushButton("오프라인 → 온라인")
        self.status_button.clicked.connect(self.toggle_status)
        self.status_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        status_layout.addWidget(self.status_button)
        
        layout.addWidget(status_group)
        
        # 데이터셋 정보
        dataset_group = QGroupBox("데이터 소스")
        dataset_layout = QVBoxLayout(dataset_group)
        dataset_layout.addWidget(QLabel("사용 중인 데이터 폴더:"))
        self.dataset_path_label = QLabel(str(Path(self.dataset_config["dataset_root"]).resolve()))
        self.dataset_path_label.setWordWrap(True)
        self.dataset_path_label.setStyleSheet("color: #1f2937; font-weight: 600;")
        dataset_layout.addWidget(self.dataset_path_label)

        self.reload_dataset_button = QPushButton("데이터 다시 읽기")
        self.reload_dataset_button.setStyleSheet("""
            QPushButton {
                background-color: #6366f1;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4f46e5;
            }
        """)
        self.reload_dataset_button.clicked.connect(self.mark_dataset_reload_needed)
        dataset_layout.addWidget(self.reload_dataset_button)

        layout.addWidget(dataset_group)
        
        # 제어 버튼
        control_group = QGroupBox("제어")
        control_layout = QVBoxLayout(control_group)
        
        # 시작 버튼
        self.start_button = QPushButton("🔄 메시지 수집")
        self.start_button.clicked.connect(self.start_collection)
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        control_layout.addWidget(self.start_button)
        
        # 중지 버튼
        self.stop_button = QPushButton("⏹️ 중지")
        self.stop_button.clicked.connect(self.stop_collection)
        self.stop_button.setEnabled(False)
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        control_layout.addWidget(self.stop_button)
        
        # 오프라인 정리 버튼
        self.cleanup_button = QPushButton("🧹 정리")
        self.cleanup_button.clicked.connect(self.offline_cleanup)
        self.cleanup_button.setStyleSheet("""
            QPushButton {
                background-color: #f39c12;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #e67e22;
            }
        """)
        control_layout.addWidget(self.cleanup_button)
        
        layout.addWidget(control_group)
        
        # 진행률 표시
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # 상태 메시지
        self.status_message = QLabel("준비됨")
        self.status_message.setStyleSheet("color: #666; font-size: 10px; padding: 4px;")
        self.status_message.setWordWrap(True)  # 텍스트 줄바꿈 활성화
        layout.addWidget(self.status_message)

        # ✅ 시간 범위 선택기 추가
        time_range_group = QGroupBox("⏰ 시간 범위 선택")
        time_range_layout = QVBoxLayout(time_range_group)
        self.time_range_selector = TimeRangeSelector()
        self.time_range_selector.time_range_changed.connect(self._on_time_range_changed)
        time_range_layout.addWidget(self.time_range_selector)
        layout.addWidget(time_range_group)
        
        # 데이터셋의 시간 범위를 자동으로 설정
        self._initialize_data_time_range()
        
        # 날씨 위젯
        weather_group = QGroupBox("오늘/내일 날씨")
        weather_layout = QVBoxLayout(weather_group)
        self.weather_input = QLineEdit()
        self.weather_input.setPlaceholderText("도시 또는 지역 (예: 서울, Seoul)")
        self.weather_input.setText("서울")
        self.weather_button = QPushButton("날씨 업데이트")
        self.weather_button.clicked.connect(lambda: self.fetch_weather())
        self.weather_button.setStyleSheet("padding:6px 10px; font-weight:600;")
        self.daily_summary_button = QPushButton("일일 요약")
        self.daily_summary_button.setStyleSheet("padding:6px 10px; font-weight:600;")
        self.daily_summary_button.clicked.connect(self.show_daily_summary)
        self.weekly_summary_button = QPushButton("주간 요약")
        self.weekly_summary_button.setStyleSheet("padding:6px 10px; font-weight:600;")
        self.weekly_summary_button.clicked.connect(self.show_weekly_summary)
        self.weather_status_label = QLabel("위치를 입력하고 업데이트를 눌러주세요.")
        self.weather_status_label.setWordWrap(True)
        self.weather_status_label.setStyleSheet("color:#1F2937; background:#F5F3FF; padding:6px; border-radius:6px;")
        self.weather_tip_label = QLabel("날씨 팁을 준비 중입니다.")
        self.weather_tip_label.setWordWrap(True)
        self.weather_tip_label.setStyleSheet("color:#4C1D95; background:#F5F3FF; padding:6px; border-radius:6px; font-size:12px;")
        weather_layout.addWidget(self.weather_input)
        weather_layout.addWidget(self.weather_button)
        weather_layout.addWidget(self.weather_status_label)
        weather_layout.addWidget(self.weather_tip_label)
        layout.addWidget(weather_group)

        summary_group = QGroupBox("요약 빠른 보기")
        summary_layout = QHBoxLayout(summary_group)
        summary_layout.addWidget(self.daily_summary_button)
        summary_layout.addWidget(self.weekly_summary_button)
        layout.addWidget(summary_group)
        # 날씨 API 자동 호출 비활성화 - 네트워크 오류 시 앱 종료 방지
        # 사용자가 수동으로 "날씨 업데이트" 버튼을 클릭하여 날씨 정보를 가져올 수 있습니다
        # QTimer.singleShot(100, lambda: self.fetch_weather("서울"))
        
        layout.addStretch()
        
        # 스크롤 영역에 패널 설정 및 추천 폭 산출
        scroll_area.setWidget(panel)
        try:
            panel.adjustSize()
            width_hint = panel.sizeHint().width()
            cushion = 48  # 여백 및 스크롤바 폭 대비
            fixed_w = max(320, width_hint + cushion)
            scroll_area.setFixedWidth(fixed_w)
        except Exception:
            scroll_area.setFixedWidth(340)
        
        return scroll_area
    
    def mark_dataset_reload_needed(self):
        """데이터셋을 다시 읽도록 표시"""
        self.dataset_config["force_reload"] = True
        self.collect_options["force_reload"] = True
        if hasattr(self, "dataset_path_label"):
            self.dataset_path_label.setText(str(Path(self.dataset_config["dataset_root"]).resolve()))
        if hasattr(self, "status_message"):
            self.status_message.setText("데이터를 다시 읽도록 준비되었습니다. '메시지 수집 시작'을 눌러주세요.")

    # ✅ utils/datetime_utils.py의 parse_iso_datetime 사용으로 대체됨
    # def _parse_iso_datetime(self, value: Optional[str]) -> Optional[datetime]:
    #     if not value:
    #         return None
    #     value = value.strip()
    #     if not value:
    #         return None
    #     try:
    #         return datetime.fromisoformat(value.replace("Z", "+00:00"))
    #     except Exception:
    #         try:
    #             return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    #         except Exception:
    #             return None

    def _show_summary_popup(self, title: str, text: str) -> None:
        """요약 다이얼로그 표시 (개선된 UI)"""
        
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setMinimumSize(600, 500)
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 헤더
        header = QWidget()
        header.setStyleSheet(f"""
            QWidget {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {Colors.PRIMARY}, stop:1 {Colors.PRIMARY_DARK});
                padding: {Spacing.MD}px;
            }}
        """)
        header_layout = QVBoxLayout(header)
        
        title_label = QLabel(title)
        title_label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_XXL, QFont.Weight.Bold))
        title_label.setStyleSheet("color: white;")
        header_layout.addWidget(title_label)
        
        layout.addWidget(header)
        
        # 스크롤 영역
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #F9FAFB;
            }
        """)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # 내용 컨테이너
        content_widget = QWidget()
        content_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(Spacing.MD, Spacing.MD, Spacing.MD, Spacing.MD)
        content_layout.setSpacing(Spacing.SM)
        
        # 텍스트를 파싱하여 섹션별로 표시
        lines = (text.strip() or "표시할 요약이 없습니다.").split('\n')
        current_section = None
        section_widget = None
        section_layout = None
        content_labels: List[QLabel] = []
        
        for line in lines:
            line = line.strip()
            if not line or line == '=' * 40:
                continue
            
            # 섹션 제목 감지
            if line.endswith(':') or '요약' in line or 'TOP' in line or '발신자' in line or '액션' in line:
                # 새 섹션 시작
                if section_widget:
                    content_layout.addWidget(section_widget)
                
                section_widget = QWidget()
                section_widget.setStyleSheet(f"""
                    QWidget {{
                        background-color: white;
                        border-radius: {BorderRadius.BASE}px;
                        border: 1px solid {Colors.BORDER_LIGHT};
                    }}
                """)
                section_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
                section_layout = QVBoxLayout(section_widget)
                section_layout.setContentsMargins(Spacing.MD, Spacing.SM, Spacing.MD, Spacing.SM)
                section_layout.setSpacing(Spacing.XS)
                
                # 섹션 제목
                section_title = QLabel(line)
                section_title.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_BASE, QFont.Weight.Bold))
                section_title.setStyleSheet(f"color: {Colors.PRIMARY}; padding-bottom: 4px;")
                section_layout.addWidget(section_title)
                current_section = line
            else:
                # 섹션 내용
                if not section_widget:
                    # 첫 번째 라인 (날짜 등)
                    section_widget = QWidget()
                    section_widget.setStyleSheet(f"""
                        QWidget {{
                            background-color: white;
                            border-radius: {BorderRadius.BASE}px;
                            border: 1px solid {Colors.BORDER_LIGHT};
                        }}
                    """)
                    section_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
                    section_layout = QVBoxLayout(section_widget)
                    section_layout.setContentsMargins(Spacing.MD, Spacing.SM, Spacing.MD, Spacing.SM)
                    section_layout.setSpacing(Spacing.XS)
                
                content_label = QLabel(line)
                content_label.setFont(QFont(Fonts.FAMILY, Fonts.SIZE_SM))
                content_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; padding: 2px 0;")
                content_label.setWordWrap(True)
                content_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
                content_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
                section_layout.addWidget(content_label)
                content_labels.append(content_label)
        
        # 마지막 섹션 추가
        if section_widget:
            content_layout.addWidget(section_widget)
        
        content_layout.addStretch()
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)
        
        class _WrapHelper(QObject):
            def __init__(self, labels, padding):
                super().__init__()
                self.labels = labels
                self.padding = padding
            
            def eventFilter(self, obj, event):
                if event.type() in (QEvent.Type.Resize, QEvent.Type.Show):
                    available = max(obj.width() - self.padding * 2, 200)
                    for lbl in self.labels:
                        lbl.setMaximumWidth(available)
                return False
        
        wrap_helper = _WrapHelper(content_labels, Spacing.MD)
        scroll.viewport().installEventFilter(wrap_helper)
        dialog._wrap_helper = wrap_helper  # keep reference
        
        # 하단 버튼
        button_container = QWidget()
        button_container.setStyleSheet(f"background-color: {Colors.BG_SECONDARY}; padding: {Spacing.SM}px;")
        button_layout = QHBoxLayout(button_container)
        button_layout.addStretch()
        
        close_button = QPushButton("닫기")
        close_button.setMinimumWidth(100)
        close_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.PRIMARY};
                color: white;
                border: none;
                border-radius: {BorderRadius.BASE}px;
                padding: {Spacing.SM}px {Spacing.MD}px;
                font-size: {FontSizes.BASE};
                font-weight: {FontWeights.SEMIBOLD};
            }}
            QPushButton:hover {{
                background-color: {Colors.PRIMARY_DARK};
            }}
        """)
        close_button.clicked.connect(dialog.accept)
        button_layout.addWidget(close_button)
        
        layout.addWidget(button_container)
        
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
        self.todo_panel.set_top3_callback(self._on_top3_updated)
        todo_layout.addWidget(self.todo_panel)
        self.tab_widget.addTab(self.todo_tab, "📋 TODO 리스트")

        # ✅ 메시지/이메일/분석 탭
        self.message_tab = self.create_message_tab(); self.tab_widget.addTab(self.message_tab, "📨 메시지")
        self.email_tab = self.create_email_tab(); self.tab_widget.addTab(self.email_tab, "📧 이메일")
        self.analysis_tab = self.create_analysis_tab(); self.tab_widget.addTab(self.analysis_tab, "📊 분석 결과")

        layout.addWidget(self.tab_widget)
        return panel
    
    # def create_todo_tab(self):
 
    #     tab = QWidget()
    #     layout = QVBoxLayout(tab)

    #     self.todo_list = QListWidget()
    #     self.todo_list.setStyleSheet("""
    #         QListWidget {
    #             border: 1px solid #ddd;
    #             border-radius: 5px;
    #             background-color: #f8f9fa;
    #         }
    #         QListWidget::item {
    #             padding: 5px;
    #             border-bottom: 1px solid #eee;
    #         }
    #         QListWidget::item:selected {
    #             background-color: #e3f2fd;
    #         }
    #     """)
    #     layout.addWidget(self.todo_list)
        
    #     return tab
    def create_todo_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

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
            text = f"{prefix} [{timestamp}] {sender}\n{snippet}"
            item = QListWidgetItem(text)
            if mtype == "email":
                item.setBackground(QColor("#EEF2FF"))
            else:
                item.setBackground(QColor("#ECFDF5"))
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

    def _fetch_weather_from_kma(self, location: str) -> bool:
        grid = None
        resolved_name = location
        for name, coords in KMA_CITY_GRID.items():
            if name.lower() == location.lower():
                grid = coords
                resolved_name = name
                break
        if not grid:
            return False

        nx, ny = grid
        kst = datetime.now(timezone.utc) + timedelta(hours=9)
        base_date = kst.date()
        base_times = ["2300", "2000", "1700", "1400", "1100", "0800", "0500", "0200"]
        current_hm = kst.strftime("%H%M")
        base_time = None
        for bt in base_times:
            if current_hm >= bt:
                base_time = bt
                break
        if base_time is None:
            base_time = "2300"
            base_date = (kst - timedelta(days=1)).date()

        base_date_str = base_date.strftime("%Y%m%d")
        service_url = os.environ.get(
            "KMA_API_URL",
            "https://apihub.kma.go.kr/api/typ02/openapi/VilageFcstInfoService_2.0/getVilageFcst",
        )
        params = {
            "serviceKey": self.kma_api_key,
            "pageNo": 1,
            "numOfRows": 500,
            "dataType": "JSON",
            "base_date": base_date_str,
            "base_time": base_time,
            "nx": nx,
            "ny": ny,
        }
                # KMA
        resp = self.http.get(service_url, params=params, timeout=(3.05, 20))

        # geocoding
        geo_resp = self.http.get("https://geocoding-api.open-meteo.com/v1/search",
                                params={...}, timeout=(3.05, 20))

        # forecast
        forecast_resp = self.http.get("https://api.open-meteo.com/v1/forecast",
                                    params={...}, timeout=(3.05, 20))

        resp = requests.get(service_url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        items = (
            (((data.get("response") or {}).get("body") or {}).get("items") or {}).get("item")
            or []
        )
        if not items:
            return False

        def find_value(category: str, target_date: str, preferred_times: list[str]):
            for t in preferred_times:
                for item in items:
                    if item.get("category") == category and item.get("fcstDate") == target_date and item.get("fcstTime") == t:
                        return item.get("fcstValue")
            return None

        current_hour = int(kst.strftime("%H"))
        preferred_today = [f"{current_hour:02d}00"]
        for offset in range(1, 4):
            preferred_today.append(f"{(current_hour + offset) % 24:02d}00")
        today_date_str = kst.strftime("%Y%m%d")

        temp_today = find_value("TMP", today_date_str, preferred_today)
        sky_today = find_value("SKY", today_date_str, preferred_today)
        pty_today = find_value("PTY", today_date_str, preferred_today)

        tomorrow_date_str = (kst + timedelta(days=1)).strftime("%Y%m%d")
        preferred_morning = ["0600", "0900", "1200"]
        temp_tomorrow = find_value("TMP", tomorrow_date_str, preferred_morning)
        sky_tomorrow = find_value("SKY", tomorrow_date_str, preferred_morning)
        pty_tomorrow = find_value("PTY", tomorrow_date_str, preferred_morning)

        if temp_today is None and temp_tomorrow is None:
            return False

        def fmt_temp(value):
            if value is None:
                return "--°C"
            try:
                return f"{float(value):.1f}°C"
            except Exception:
                return f"{value}°C"

        today_desc = self._describe_kma_weather(sky_today, pty_today)
        tomorrow_desc = self._describe_kma_weather(sky_tomorrow, pty_tomorrow)

        self.weather_status_label.setText(
            f"{resolved_name}\n현재 {fmt_temp(temp_today)} · {today_desc}\n"
            f"내일 오전 {fmt_temp(temp_tomorrow)} · {tomorrow_desc}"
        )
        self.weather_tip_label.setText(self._weather_tip(temp_tomorrow, pty_code=pty_tomorrow))
        return True

    def fetch_weather(self, preset_location: Optional[str] = None):
        if not hasattr(self, "weather_input"):
            return
        location = (preset_location or self.weather_input.text()).strip()
        if preset_location:
            self.weather_input.setText(location)
        if not location:
            QMessageBox.warning(self, "입력 오류", "지역을 입력해주세요.")
            return
        self.weather_status_label.setText("날씨 정보를 불러오는 중입니다...")
        if self.kma_api_key:
            try:
                if self._fetch_weather_from_kma(location):
                    return
            except Exception as exc:
                print(f"[weather] KMA fetch error: {exc}")
        try:
            results = []
            candidates = [location]
            alias = KMA_CITY_ALIAS.get(location)
            if alias and alias not in candidates:
                candidates.append(alias)
            for candidate in candidates:
                for lang in ("ko", "en"):
                    geo_resp = requests.get(
                        "https://geocoding-api.open-meteo.com/v1/search",
                        params={"name": candidate, "count": 1, "language": lang, "format": "json"},
                        timeout=10,
                    )
                    geo_resp.raise_for_status()
                    geo_json = geo_resp.json()
                    results = geo_json.get("results") or []
                    if results:
                        break
                if results:
                    break
            if not results:
                self.weather_status_label.setText("해당 위치를 찾을 수 없습니다. 영어/한국어 표기로 다시 시도해 주세요.")
                self.weather_tip_label.setText("날씨 팁을 불러오지 못했습니다. 기본적으로 우산과 마스크를 준비해 주세요.")
                return
            top = results[0]
            lat = top.get("latitude")
            lon = top.get("longitude")
            resolved_name = ", ".join(filter(None, [top.get("name"), top.get("country")]))

            forecast_resp = requests.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "hourly": "temperature_2m,weathercode",
                    "current_weather": True,
                    "forecast_days": 2,
                    "timezone": "auto",
                },
                timeout=10,
            )
            forecast_resp.raise_for_status()
            forecast_json = forecast_resp.json()
            current = forecast_json.get("current_weather") or {}
            hourly = forecast_json.get("hourly") or {}

            current_temp = current.get("temperature")
            current_temp_text = f"{current_temp}°C" if current_temp is not None else "--°C"
            current_desc = self._weather_description(current.get("weathercode"))

            tomorrow_temp, tomorrow_code = self._extract_tomorrow_morning(hourly)
            tomorrow_temp_text = f"{tomorrow_temp}°C" if tomorrow_temp is not None else "--°C"
            tomorrow_desc = self._weather_description(tomorrow_code)

            self.weather_status_label.setText(
                f"{resolved_name}\n현재 {current_temp_text} · {current_desc}\n"
                f"내일 오전 {tomorrow_temp_text} · {tomorrow_desc}"
            )
            self.weather_tip_label.setText(self._weather_tip(tomorrow_temp, weather_code=tomorrow_code))
        except requests.RequestException as exc:
            self.weather_status_label.setText("날씨 정보를 가져오지 못했습니다.")
            self.weather_tip_label.setText("날씨 팁을 불러오지 못했습니다. 기본적으로 우산과 마스크를 준비해 주세요.")
            logger.warning(f"날씨 API 요청 오류: {exc}")
        except Exception as exc:
            self.weather_status_label.setText("날씨 정보를 처리하는 중 오류가 발생했습니다.")
            self.weather_tip_label.setText("날씨 팁을 불러오지 못했습니다. 기본적으로 우산과 마스크를 준비해 주세요.")
            logger.error(f"날씨 정보 처리 오류: {exc}")

    def _describe_kma_weather(self, sky: Optional[str], pty: Optional[str]) -> str:
        try:
            pty_val = int(pty) if pty is not None else 0
        except Exception:
            pty_val = 0
        if pty_val == 1:
            return "비"
        if pty_val == 2:
            return "비/눈"
        if pty_val == 3:
            return "눈"
        if pty_val == 5:
            return "빗방울"
        if pty_val == 6:
            return "빗방울/눈날림"
        if pty_val == 7:
            return "눈날림"
        try:
            sky_val = int(sky) if sky is not None else 0
        except Exception:
            sky_val = 0
        sky_map = {
            1: "맑음",
            3: "구름 많음",
            4: "흐림",
        }
        return sky_map.get(sky_val, "상세 정보 없음")

    def _weather_tip(self, morning_temp: Optional[float], pty_code: Optional[str] = None, weather_code: Optional[int] = None) -> str:
        tips: List[str] = []
        rain_expected = False
        if pty_code is not None:
            try:
                p_val = int(pty_code)
                if p_val in {1, 2, 3, 5, 6, 7}:
                    rain_expected = True
            except Exception:
                pass
        elif weather_code is not None:
            rain_expected = weather_code in {51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82}
        if rain_expected:
            tips.append("비 예보가 있으니 우산을 챙기세요.")
        temp_tip_added = False
        if morning_temp is not None:
            try:
                temp = float(morning_temp)
                if temp <= 0:
                    tips.append("아침 기온이 영하권이라 두꺼운 외투와 장갑을 준비하세요.")
                    temp_tip_added = True
                elif temp <= 5:
                    tips.append("쌀쌀하니 코트나 패딩을 추천합니다.")
                    temp_tip_added = True
                elif temp >= 25:
                    tips.append("무더울 수 있으니 가볍고 통풍이 잘 되는 복장을 입으세요.")
                    temp_tip_added = True
            except Exception:
                pass
        if not temp_tip_added:
            tips.append("기온 변화에 대비해 겉옷을 하나 챙기면 좋습니다.")
        tips.append("미세먼지 정보가 없으나 기본적으로 마스크 착용을 권장합니다.")
        return " ".join(tips)

    def _extract_tomorrow_morning(self, hourly: dict) -> tuple[Optional[float], Optional[int]]:
        try:
            times = hourly.get("time", [])
            temps = hourly.get("temperature_2m", [])
            codes = hourly.get("weathercode", [])
            target_date = (datetime.now() + timedelta(days=1)).date()
            candidate = None
            for t_str, temp, code in zip(times, temps, codes):
                dt = datetime.fromisoformat(t_str.replace("Z", "+00:00"))
                if dt.date() == target_date and 6 <= dt.hour <= 10:
                    candidate = (temp, code)
                    break
            if not candidate and temps:
                candidate = (temps[0], codes[0] if codes else None)
            return candidate or (None, None)
        except Exception:
            return (None, None)

    def _weather_description(self, code: Optional[int]) -> str:
        mapping = {
            0: "맑음",
            1: "대체로 맑음",
            2: "부분적으로 흐림",
            3: "흐림",
            45: "안개",
            48: "서리 안개",
            51: "실비",
            53: "약한 이슬비",
            55: "강한 이슬비",
            61: "약한 비",
            63: "보통 비",
            65: "강한 비",
            71: "가벼운 눈",
            73: "보통 눈",
            75: "강한 눈",
            80: "약한 소나기",
            81: "보통 소나기",
            82: "강한 소나기",
            95: "천둥번개",
            96: "우박 가능",
            99: "강한 폭우/우박",
        }
        return mapping.get(code, "상세 정보 없음")

    
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
        if not hasattr(self, "status_indicator"):
            return
        if self.current_status == "online":
            self.status_indicator.set_status("online")
            self.status_button.setText("온라인 → 오프라인")
            self.status_button.setStyleSheet("""
                QPushButton {
                    background-color: #e74c3c;
                    color: white;
                    border: none;
                    padding: 8px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #c0392b;
                }
                QPushButton:disabled {
                    background-color: #bdc3c7;
                }
            """)
        else:
            self.status_indicator.set_status("offline")
            self.status_button.setText("오프라인 → 온라인")
            self.status_button.setStyleSheet("""
                QPushButton {
                    background-color: #3498db;
                    color: white;
                    border: none;
                    padding: 8px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #2980b9;
                }
                QPushButton:disabled {
                    background-color: #bdc3c7;
                }
            """)

    def initialize_online_state(self):
        self.current_status = "online"
        self._apply_status_style()
        if hasattr(self, "refresh_timer"):
            self.refresh_timer.start()
        if hasattr(self, "status_message"):
            self.status_message.setText("온라인 모드입니다. '메시지 수집 시작'을 눌러 모바일 데이터셋을 분석하세요.")
        if hasattr(self, "status_bar"):
            self.status_bar.showMessage("온라인 모드 - 오프라인 데이터셋 기반 분석 준비 완료")

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
        """데이터셋의 시간 범위를 자동으로 설정
        
        데이터셋 파일을 읽어서 가장 오래된 메시지와 가장 최근 메시지의 시간을 찾아
        TimeRangeSelector에 설정합니다.
        """
        try:
            import json
            from pathlib import Path
            
            # 데이터셋 경로
            dataset_path = Path("data/multi_project_8week_ko")
            logger.info(f"📂 데이터셋 경로: {dataset_path.absolute()}")
            
            dates = []
            
            # 채팅 메시지 파일 읽기
            chat_file = dataset_path / "chat_communications.json"
            logger.info(f"채팅 파일 확인: {chat_file.absolute()} (존재: {chat_file.exists()})")
            
            if chat_file.exists():
                with open(chat_file, 'r', encoding='utf-8') as f:
                    chat_data = json.load(f)
                    rooms = chat_data.get("rooms", [])
                    logger.info(f"채팅 방 수: {len(rooms)} (type: {type(rooms).__name__})")
                    
                    if isinstance(rooms, dict):
                        room_iter = rooms.values()
                    elif isinstance(rooms, list):
                        room_iter = rooms
                    else:
                        logger.warning(f"지원되지 않는 rooms 타입: {type(rooms)}")
                        room_iter = []
                    
                    for room in room_iter:
                        if isinstance(room, dict) and "entries" in room:
                            entries = room.get("entries", [])
                        elif isinstance(room, list):
                            entries = room
                        else:
                            logger.debug(f"알 수 없는 채팅 룸 구조: {room}")
                            continue
                        
                        for entry in entries:
                            if not isinstance(entry, dict):
                                logger.debug(f"채팅 엔트리 구조 오류: {entry}")
                                continue
                            
                            sent_at = entry.get("sent_at")
                            if sent_at:
                                try:
                                    dt = datetime.fromisoformat(sent_at.replace("Z", "+00:00"))
                                    if dt.tzinfo is None:
                                        dt = dt.replace(tzinfo=timezone.utc)
                                    else:
                                        dt = dt.astimezone(timezone.utc)
                                    dates.append(dt)
                                except Exception as e:
                                    logger.debug(f"채팅 날짜 파싱 오류: {sent_at} - {e}")
                    
                    logger.info(f"채팅에서 수집된 날짜 수: {len(dates)}")
            
            # 이메일 파일 읽기
            email_file = dataset_path / "email_communications.json"
            logger.info(f"이메일 파일 확인: {email_file.absolute()} (존재: {email_file.exists()})")
            
            if email_file.exists():
                email_dates_before = len(dates)
                with open(email_file, 'r', encoding='utf-8') as f:
                    email_data = json.load(f)
                    mailboxes = email_data.get("mailboxes", [])
                    logger.info(f"메일박스 수: {len(mailboxes)} (type: {type(mailboxes).__name__})")
                    
                    if isinstance(mailboxes, dict):
                        mailbox_iter = mailboxes.values()
                    elif isinstance(mailboxes, list):
                        mailbox_iter = mailboxes
                    else:
                        logger.warning(f"지원되지 않는 mailboxes 타입: {type(mailboxes)}")
                        mailbox_iter = []
                    
                    for mailbox in mailbox_iter:
                        if isinstance(mailbox, dict) and "entries" in mailbox:
                            entries = mailbox.get("entries", [])
                        elif isinstance(mailbox, list):
                            entries = mailbox
                        else:
                            logger.debug(f"알 수 없는 메일박스 구조: {mailbox}")
                            continue
                        
                        for entry in entries:
                            if not isinstance(entry, dict):
                                logger.debug(f"이메일 엔트리 구조 오류: {entry}")
                                continue
                            
                            sent_at = entry.get("sent_at")
                            if sent_at:
                                try:
                                    dt = datetime.fromisoformat(sent_at.replace("Z", "+00:00"))
                                    if dt.tzinfo is None:
                                        dt = dt.replace(tzinfo=timezone.utc)
                                    else:
                                        dt = dt.astimezone(timezone.utc)
                                    dates.append(dt)
                                except Exception as e:
                                    logger.debug(f"이메일 날짜 파싱 오류: {sent_at} - {e}")
                    
                    logger.info(f"이메일에서 수집된 날짜 수: {len(dates) - email_dates_before}")
            
            logger.info(f"총 수집된 날짜 수: {len(dates)}")
            
            if dates:
                data_start = min(dates)
                data_end = max(dates)
                self.time_range_selector.set_data_range(data_start, data_end)
                logger.info(f"📅 데이터 시간 범위 자동 설정: {data_start.strftime('%Y-%m-%d %H:%M')} ~ {data_end.strftime('%Y-%m-%d %H:%M')}")
            else:
                logger.warning("⚠️ 데이터셋에서 시간 정보를 찾을 수 없습니다")
                
        except Exception as e:
            logger.error(f"❌ 데이터 시간 범위 초기화 오류: {e}", exc_info=True)
    
    def _on_time_range_changed(self, start: datetime, end: datetime):
        """시간 범위 변경 핸들러
        
        TimeRangeSelector에서 시간 범위가 변경되면 호출됩니다.
        변경된 시간 범위를 collect_options에 저장하고 상태 메시지를 업데이트합니다.
        
        Args:
            start: 시작 시간 (UTC aware datetime)
            end: 종료 시간 (UTC aware datetime)
        """
        # 시간 범위를 collect_options에 저장
        self.collect_options["time_range"] = {
            "start": start,
            "end": end
        }
        
        # 상태 메시지 업데이트
        start_str = start.strftime('%Y-%m-%d %H:%M')
        end_str = end.strftime('%Y-%m-%d %H:%M')
        self.status_message.setText(
            f"시간 범위 설정: {start_str} ~ {end_str}\n"
            "'메시지 수집 시작'을 눌러 분석하세요."
        )
    
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
        if self.worker_thread and self.worker_thread.isRunning():
            return

        dataset_config = dict(self.dataset_config)
        collect_options = dict(self.collect_options)
        # 항상 최신 JSON을 반영하도록 강제 리로드
        collect_options["force_reload"] = True
        dataset_config["force_reload"] = dataset_config.get("force_reload", False) or True

        # UI 상태 변경
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # 워커 스레드 시작
        self.worker_thread = WorkerThread(self.assistant, dataset_config, collect_options)
        self.worker_thread.progress_updated.connect(self.progress_bar.setValue)
        self.worker_thread.status_updated.connect(self.status_message.setText)
        self.worker_thread.result_ready.connect(self.handle_result)
        self.worker_thread.error_occurred.connect(self.handle_error)
        self.worker_thread.start()

        # 다음 실행은 필요 시 다시 표시
        self.dataset_config["force_reload"] = False
        self.collect_options["force_reload"] = False
    
    def stop_collection(self):
        """수집 중지"""
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.stop()
            self.worker_thread.wait(3000)
        
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.status_message.setText("수집 중지됨")
    
    def handle_result(self, result):
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.status_message.setText("수집 완료")

        if result.get("success"):
            todo_list = result.get("todo_list") or {}
            items = todo_list.get("items", [])
            if items:
                if hasattr(self, "todo_panel"):
                    self.todo_panel.populate_from_items(items)
                    self.todo_panel.show_top3_dialog()
                try:
                    _save_todos_to_db(items, db_path=TODO_DB_PATH)
                except Exception as e:
                    if hasattr(self, "status_message"):
                        self.status_message.setText(f"DB 저장 경고: {e}")
            else:
                if hasattr(self, "status_message"):
                    self.status_message.setText("이번 수집에서 새로운 TODO가 없어 이전 목록을 유지합니다.")
            messages = result.get("messages", [])
            self.collected_messages = list(messages)
            
            # ✅ 데이터 시간 범위 계산 및 TimeRangeSelector에 설정
            if messages and hasattr(self, "time_range_selector"):
                dates = []
                for msg in messages:
                    date_str = msg.get("date")
                    if date_str:
                        try:
                            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                            dates.append(dt)
                        except:
                            pass
                
                if dates:
                    data_start = min(dates)
                    data_end = max(dates)
                    self.time_range_selector.set_data_range(data_start, data_end)
                    logger.info(f"데이터 시간 범위 설정: {data_start.strftime('%Y-%m-%d')} ~ {data_end.strftime('%Y-%m-%d')}")
            
            # ✅ 메시지 요약 업데이트 (MessageSummaryPanel 사용)
            self._update_message_summaries("day")  # 기본값: 일별 요약
            
            # 기존 메시지 테이블 업데이트 (호환성 유지)
            if hasattr(self, "message_table"):
                self.update_message_table(messages)
            if hasattr(self, "message_summary_label"):
                self._update_message_summary(messages)
            
            self.update_timeline(messages)

            analysis_results = result.get("analysis_results") or []
            self.analysis_results = analysis_results
            
            # ✅ AnalysisResultPanel 업데이트
            if hasattr(self, "analysis_result_panel"):
                self.analysis_result_panel.update_analysis(analysis_results, messages)
            
            # ✅ EmailPanel 업데이트 (TODO에 없는 이메일만 표시)
            if hasattr(self, "email_panel"):
                self.email_panel.update_emails(messages, items)

            total = len(items)
            self.status_bar.showMessage(f"수집 완료: {total}개 TODO 생성")
            self.auto_save_results(result)
        else:
            QMessageBox.critical(self, "오류", "수집 중 오류가 발생했습니다.")

    def _on_top3_updated(self, top3: list[dict]) -> None:
        if not hasattr(self, "todo_panel"):
            return
    
    def handle_error(self, error_message):
        """오류 처리"""
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.status_message.setText("오류 발생")
        
        QMessageBox.critical(self, "오류", error_message)
    
    # def update_todo_list(self, todo_items):
    #     """TODO 리스트 업데이트"""
    #     self.todo_list.clear()
        
    #     for item in todo_items[:30]:  # 상위 20개만 표시
    #         todo_widget = TodoItemWidget(item)
    #         list_item = QListWidgetItem()
    #         list_item.setSizeHint(todo_widget.sizeHint())
            
    #         self.todo_list.addItem(list_item)
    #         self.todo_list.setItemWidget(list_item, todo_widget)
    # ✅ 이전 버전 호환성을 위해 유지 (현재는 AnalysisResultPanel 사용)
    # def update_analysis_tab(self, analysis_report_text: Optional[str], analysis_results: Optional[list]):
    #     """
    #     분석결과 탭에 최종 텍스트를 채운다.
    #     - 우선적으로 main.py에서 만들어둔 self.analysis_report_text(=analysis_report_text)를 사용
    #     - 없으면 기존 방식으로 top 10 간단 요약을 만들어서 출력(폴백)
    #     """
    #     pass  # AnalysisResultPanel로 대체됨

    
    def auto_refresh(self):
        """자동 새로고침 (온라인 모드)"""
        if self.current_status == "online" and not self.worker_thread:
            self.start_collection()
    
    def offline_cleanup(self):
        """오프라인 정리"""
        from .offline_cleaner import OfflineCleanupDialog
        
        dialog = OfflineCleanupDialog(self)
        dialog.exec()
    
    def auto_save_results(self, result):
        """결과 자동 저장"""
        try:
            filename = f"gui_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"자동 저장 오류: {e}")
    
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
    
    def closeEvent(self, event):
        """창 닫기 이벤트"""
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.stop()
            self.worker_thread.wait(3000)
        
        event.accept()

class Chip(QLabel):
    def __init__(self, text, bg="#E5E7EB", fg="#111827"):
        super().__init__(text)
        self.setProperty("chip", True)
        self.setStyleSheet(f"""
            QLabel[chip="true"] {{
                background: {bg};
                color: {fg};
                padding: 2px 8px;
                border-radius: 999px;
                font-weight: 600;
            }}
        """)

# def main():
#     """메인 함수"""
#     app = QApplication(sys.argv)
#     app.setApplicationName("Smart Assistant")
#     app.setApplicationVersion("1.0")
    
#     window = SmartAssistantGUI()
#     window.show()
    
#     sys.exit(app.exec())

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("OFFLINE Agent")
    app.setApplicationVersion("1.0")

    # 1) OS 일관 테마
    app.setStyle(QStyleFactory.create("Fusion"))

    # 2) 전역 기본 글꼴(한글)
    #  - 윈도우: 맑은 고딕이 가장 안정적
    #  - Noto Sans KR 폰트를 동봉했다면 addApplicationFont로 등록 후 이름만 바꾸면 됩니다.
    base_korean_font = QFont("Malgun Gothic", 10)
    app.setFont(base_korean_font)

    # 3) 전역 팔레트(살짝 명도 올린 중립 톤)
    from PyQt6.QtGui import QPalette, QColor
    pal = app.palette()
    pal.setColor(QPalette.ColorRole.Window, QColor("#FAFAFA"))
    pal.setColor(QPalette.ColorRole.Base,   QColor("#FFFFFF"))
    pal.setColor(QPalette.ColorRole.Text,   QColor("#222222"))
    pal.setColor(QPalette.ColorRole.Button, QColor("#FFFFFF"))
    # 탭/라벨 등의 텍스트 컬러를 명확히 지정 (화이트 텍스트 문제 방지)
    pal.setColor(QPalette.ColorRole.WindowText, QColor("#111827"))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor("#111827"))
    app.setPalette(pal)

    # 4) 전역 스타일시트(여백/모서리/폰트크기 통일)
    app.setStyleSheet("""
        * { font-size: 12px; }
        /* PoC: 모든 일반 텍스트를 검정으로 강제하여 가독성 확보 */
        QWidget { color: #000000; }
        QLabel { color: #000000; }
        QLineEdit, QTextEdit, QPlainTextEdit { color: #000000; }
        QListWidget, QListView, QTreeView, QTableWidget, QTableView { color: #000000; }
        QTabBar::tab { color: #000000; }
        QHeaderView::section { color: #000000; }
        QGroupBox { font-weight: 600; border: 1px solid #E5E7EB; border-radius: 8px; margin-top: 8px; }
        QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; color:#111827; }
        QLabel[role="title"] { font-size: 18px; font-weight: 800; color:#1F2937; }
        QPushButton {
            border: 0; border-radius: 8px; padding: 10px 12px; font-weight: 700;
        }
        QTableWidget, QListWidget {
            border: 1px solid #E5E7EB; border-radius: 8px; background: #FFFFFF;
        }
        QHeaderView::section {
            background: #F3F4F6; border: 0; padding: 8px; font-weight: 600;
        }
    """)

    window = SmartAssistantGUI()
    window.show()
    sys.exit(app.exec())



if __name__ == "__main__":
    main()









