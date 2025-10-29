# ui/todo_panel.py
from __future__ import annotations

import os, sys, uuid, json, sqlite3, subprocess, re, logging, requests
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Callable, Optional, Tuple

from copy import deepcopy

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QMessageBox, QHBoxLayout, QTextEdit, QPushButton, QDialog, QDialogButtonBox,
    QLineEdit, QComboBox, QFormLayout, QDoubleSpinBox, QCheckBox
)
from PyQt6.QtCore import QTimer, pyqtSignal, Qt

from config.settings import LLM_CONFIG, CONFIG_STORE_PATH

# 분리된 헬퍼 및 위젯 import
from .todo_helpers import (
    _parse_iso_dt, _created_ts, _normalize_korean_name,
    _create_recipient_type_badge, _create_source_type_badge,
    _deadline_badge, _evidence_count, _source_message_dict,
    _is_unread, _priority_sort_key
)
from .widgets import End2EndCard
from .dialogs import Top3RuleDialog, Top3NaturalRuleDialog

# Top3 서비스 import
from src.services import Top3Service, TOP3_RULE_DEFAULT

# VDOS 연동 import (선택적)
try:
    from utils.vdos_connector import get_vdos_connector, is_vdos_available
    VDOS_AVAILABLE = True
except ImportError:
    VDOS_AVAILABLE = False
    logger.warning("[VDOS] VDOS 연동 모듈을 찾을 수 없습니다. VDOS 기능이 비활성화됩니다.")

logger = logging.getLogger(__name__)

# TODO_DB_PATH는 MainWindow에서 동적으로 설정됨 (VDOS DB와 같은 위치)
# 폴백 경로만 정의
TODO_DB_PATH_FALLBACK = os.path.join("data", "multi_project_8week_ko", "todos_cache.db")

def _create_recipient_type_badge(recipient_type: str) -> Optional[QLabel]:
    """수신 타입 배지 생성 헬퍼 함수
    
    Args:
        recipient_type: 수신 타입 ("to", "cc", "bcc")
        
    Returns:
        QLabel 배지 위젯 또는 None (직접 수신인 경우)
    """
    recipient_type = (recipient_type or "to").lower()
    
    if recipient_type == "cc":
        badge = QLabel("참조(CC)")
        badge.setStyleSheet(
            "color:#92400E; background:#FEF3C7; "
            "padding:2px 6px; border-radius:8px; font-weight:600;"
        )
        return badge
    elif recipient_type == "bcc":
        badge = QLabel("숨은참조(BCC)")
        badge.setStyleSheet(
            "color:#92400E; background:#FEF3C7; "
            "padding:2px 6px; border-radius:8px; font-weight:600;"
        )
        return badge
    
    return None  # 직접 수신(TO)인 경우 배지 없음

def _create_source_type_badge(source_type: str) -> QLabel:
    """소스 타입 배지 생성 헬퍼 함수
    
    Args:
        source_type: 소스 타입 ("메일", "메시지")
        
    Returns:
        QLabel 배지 위젯
    """
    source_type = (source_type or "메시지").strip()
    
    if source_type == "메일":
        badge = QLabel("📧 메일")
        badge.setStyleSheet(
            "color:#1E40AF; background:#DBEAFE; "
            "padding:2px 6px; border-radius:8px; font-weight:600; font-size:10px;"
        )
    else:  # 메시지 또는 기타
        badge = QLabel("💬 메시지")
        badge.setStyleSheet(
            "color:#065F46; background:#D1FAE5; "
            "padding:2px 6px; border-radius:8px; font-weight:600; font-size:10px;"
        )
    
    return badge

def _normalize_korean_name(token: str) -> str:
    base = token.strip()
    for suffix in _KOREAN_NAME_SUFFIXES:
        if base.endswith(suffix) and len(base) > len(suffix):
            base = base[:-len(suffix)]
            break
    changed = True
    while changed and len(base) > 2:
        changed = False
        for suffix in _KOREAN_PARTICLES:
            if base.endswith(suffix) and len(base) > len(suffix):
                base = base[:-len(suffix)]
                changed = True
                break
    return base.strip()

# ─────────────────────────────────────────────────────────────────────────────
# Top3 관련 전역 함수들은 Top3Service로 이동되었습니다
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# 0) DB 헬퍼들과 공용 유틸
# ─────────────────────────────────────────────────────────────────────────────

def get_conn(db_path: str) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(conn: sqlite3.Connection) -> None:
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
        deadline_confidence TEXT,
        recipient_type TEXT DEFAULT 'to',
        source_type TEXT DEFAULT '메시지'
    )
    """)
    
    # 기존 테이블에 컬럼 추가 (마이그레이션)
    try:
        cur.execute("ALTER TABLE todos ADD COLUMN recipient_type TEXT DEFAULT 'to'")
        conn.commit()
    except sqlite3.OperationalError:
        # 컬럼이 이미 존재하면 무시
        pass
    
    try:
        cur.execute("ALTER TABLE todos ADD COLUMN source_type TEXT DEFAULT '메시지'")
        conn.commit()
    except sqlite3.OperationalError:
        # 컬럼이 이미 존재하면 무시
        pass
    
    conn.commit()

def check_snoozes_and_deadlines(conn: sqlite3.Connection) -> None:
    """스누즈 만료시 pending으로 복귀."""
    now = datetime.now().isoformat()
    cur = conn.cursor()
    cur.execute("""
        UPDATE todos
           SET status='pending', updated_at=?
         WHERE status='snoozed'
           AND snooze_until IS NOT NULL
           AND snooze_until <= ?
    """, (now, now))
    conn.commit()

def _open_path_cross_platform(path: str) -> None:
    try:
        if sys.platform.startswith("win"):
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception as e:
        print(f"[open] failed: {e}")

# ✅ utils/datetime_utils.py의 parse_iso_datetime 사용으로 대체됨
# def _parse_iso_dt(value: str | None) -> datetime | None:
#     if not value:
#         return None
#     try:
#         return datetime.fromisoformat(value.replace("Z", "+00:00"))
#     except Exception:
#         try:
#             return datetime.fromisoformat(value)
#         except Exception:
#             return None

# utils 함수 import
from utils.datetime_utils import parse_iso_datetime as _parse_iso_dt

def _created_ts(todo: dict) -> float:
    dt = _parse_iso_dt(todo.get("created_at"))
    if not dt:
        return 0.0
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()

def _is_truthy(v) -> bool:
    return v in (1, "1", True, "true", "TRUE", "True")

# _score_for_top3와 _pick_top3 함수는 Top3Service로 이동되었습니다

def _priority_sort_key(todo: dict):
    order = {"high": 0, "medium": 1, "low": 2}
    idx = order.get((todo.get("priority") or "").lower(), 3)
    return (idx, -_created_ts(todo))

def _deadline_badge(todo: dict) -> Optional[tuple[str, str, str]]:
    deadline = todo.get("deadline_ts") or todo.get("deadline")
    dt = _parse_iso_dt(deadline)
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    diff_hours = (dt - now).total_seconds() / 3600.0
    if diff_hours < 0:
        return ("마감 지남", "#991B1B", "#FEE2E2")
    if diff_hours < 1:
        return ("1시간 이내", "#1F2937", "#FEF3C7")
    if diff_hours < 24:
        return (f"{int(diff_hours)}시간 남음", "#1D4ED8", "#DBEAFE")
    days = int(diff_hours // 24)
    return (f"D-{days}", "#1D4ED8", "#DBEAFE")

def _evidence_count(todo: dict) -> int:
    evidence = todo.get("evidence")
    if isinstance(evidence, list):
        return len(evidence)
    try:
        return len(json.loads(evidence or "[]"))
    except Exception:
        return 0
def _source_message_dict(todo: dict) -> dict:
    src = todo.get("source_message")
    if not src:
        return {}
    if isinstance(src, str):
        try:
            src = json.loads(src)
        except Exception:
            return {}
    if isinstance(src, dict):
        return src
    return {}

def _is_unread(todo: dict) -> bool:
    # 이미 확인한 TODO는 읽음 처리
    if todo.get("_viewed"):
        return False
    
    # 생성된 지 5분 이상 지난 TODO는 자동으로 읽음 처리
    created_at = todo.get("created_at")
    if created_at:
        try:
            from utils.datetime_utils import parse_iso_datetime
            from datetime import datetime, timezone, timedelta
            
            created_dt = parse_iso_datetime(created_at)
            if created_dt:
                now = datetime.now(timezone.utc)
                # 5분 이상 지난 TODO는 읽음 처리
                if (now - created_dt).total_seconds() > 300:  # 5분 = 300초
                    return False
        except Exception:
            pass
    
    # 소스 메시지 확인
    src = _source_message_dict(todo)
    if not src:
        # 소스 메시지가 없으면 기본적으로 읽음 처리
        return False
    
    # 소스 메시지의 is_read 상태 확인 (기본값: True = 읽음)
    return not src.get("is_read", True)

# ─────────────────────────────────────────────────────────────────────────────
# 1) End2EndCard: Top-3 전용 카드
# ─────────────────────────────────────────────────────────────────────────────
class End2EndCard(QWidget):
    send_clicked = pyqtSignal(dict)
    hold_clicked = pyqtSignal(dict)
    snooze_clicked = pyqtSignal(dict)

    def __init__(self, todo: dict, parent=None, unread: bool = False):
        super().__init__(parent)
        self.todo = todo
        root = QVBoxLayout(self)

        title = QLabel(f"🔴 {todo.get('title','(제목없음)')}")
        title.setStyleSheet("font-weight: 700;")
        root.addWidget(title)

        chips = QHBoxLayout()
        try:
            reasons = json.loads(todo.get("evidence", "[]"))[:3] if todo.get("evidence") else []
        except Exception:
            reasons = []
        for chip in reasons:
            lbl = QLabel(f"〔{chip}〕")
            lbl.setStyleSheet("color:#374151; background:#F3F4F6; padding:2px 6px; border-radius:8px;")
            chips.addWidget(lbl)
        dl_badge = _deadline_badge(todo)
        if dl_badge:
            text, fg, bg = dl_badge
            dlabel = QLabel(f"〔{text}〕")
            dlabel.setStyleSheet(f"color:{fg}; background:{bg}; padding:2px 6px; border-radius:8px;")
            chips.addWidget(dlabel)
        ev_count = _evidence_count(todo)
        if ev_count:
            elabel = QLabel(f"〔근거:{ev_count}〕")
            elabel.setStyleSheet("color:#0F172A; background:#E2E8F0; padding:2px 6px; border-radius:8px;")
            chips.addWidget(elabel)
        chips.addStretch(1)
        root.addLayout(chips)

        self.subject = QTextEdit(todo.get("draft_subject", ""))
        self.subject.setFixedHeight(32)
        self.body = QTextEdit(todo.get("draft_body", ""))
        self.body.setFixedHeight(120)
        root.addWidget(self.subject)
        root.addWidget(self.body)

        if unread:
            title.setText("🟢 " + (todo.get('title','(제목없음)')))
            self.setStyleSheet("""
                QWidget { border: 1px solid #FB923C; border-radius: 10px; background: #FFF7ED; }
                QWidget:hover { border-color: #F97316; background: #FFE7D3; }
            """)
        else:
            self.setStyleSheet("""
                QWidget { border: 1px solid #E5E7EB; border-radius: 10px; background: #FFFFFF; }
                QWidget:hover { border-color: #60A5FA; background: #F8FAFC; }
            """)

        btns = QHBoxLayout()
        b_send = QPushButton("보내기")
        b_hold = QPushButton("캘린더 홀드(15분)")
        b_snooz = QPushButton("스누즈")
        for b in (b_send, b_hold, b_snooz):
            b.setStyleSheet("padding:6px 10px; border-radius:6px; font-weight:600;")
        btns.addWidget(b_send)
        btns.addWidget(b_hold)
        btns.addWidget(b_snooz)
        root.addLayout(btns)

        b_send.clicked.connect(lambda: self.send_clicked.emit(self._payload()))
        b_hold.clicked.connect(lambda: self.hold_clicked.emit(self._payload()))
        b_snooz.clicked.connect(lambda: self.snooze_clicked.emit(self._payload()))

    def _payload(self) -> dict:
        payload = dict(self.todo)
        payload["draft_subject"] = self.subject.toPlainText().strip()
        payload["draft_body"] = self.body.toPlainText().strip()
        return payload

# ─────────────────────────────────────────────────────────────────────────────
# 2) Top3RuleDialog: 가중치 조정
# ─────────────────────────────────────────────────────────────────────────────

class BasicTodoItem(QWidget):
    mark_done_clicked = pyqtSignal(dict)

    PRIORITY = {
        "high": ("High", "#FEE2E2", "#991B1B"),
        "medium": ("Medium", "#FEF3C7", "#92400E"),
        "low": ("Low", "#DCFCE7", "#166534"),
    }

    def __init__(self, todo: dict, parent=None, unread: bool = False, closable: bool = True):
        super().__init__(parent)
        self.todo = todo
        self._unread = False
        self._unread_style = "QWidget{border:1px solid #FB923C; border-radius:10px; background:#FFF7ED;} QWidget:hover{border-color:#F97316; background:#FFE7D3;}"
        self._read_style = "QWidget{border:1px solid #D1D5DB; border-radius:10px; background:#E5E7EB;} QWidget:hover{border-color:#9CA3AF; background:#D1D5DB;}"

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 8, 12, 8)

        top = QHBoxLayout()
        top.setSpacing(8)
        title = QLabel(todo.get("title", ""))
        title.setStyleSheet("font-weight:700;")
        top.addWidget(title, 1)

        priority_key = (todo.get("priority") or "low").lower()
        txt, bg, fg = self.PRIORITY.get(priority_key, self.PRIORITY["low"])
        chip = QLabel(txt)
        chip.setStyleSheet(f"background:{bg}; color:{fg}; padding:2px 8px; border-radius:999px; font-weight:600;")
        top.addWidget(chip, 0)

        self.new_badge = QLabel("미확인")
        self.new_badge.setStyleSheet("background:#FDE68A; color:#92400E; padding:2px 8px; border-radius:999px; font-weight:700;")
        self.new_badge.hide()
        top.addWidget(self.new_badge, 0)

        status = QLabel((todo.get("status") or "pending").capitalize())
        status.setStyleSheet("background:#E0E7FF; color:#3730A3; padding:2px 8px; border-radius:999px; font-weight:600;")
        top.addWidget(status, 0)
        
        # 수신 타입 배지 추가 (상단에는 중요한 정보만)
        recipient_badge = _create_recipient_type_badge(todo.get("recipient_type"))
        if recipient_badge:
            top.addWidget(recipient_badge, 0)

        self.close_button = QPushButton("✕")
        self.close_button.setObjectName("closeButton")
        self.close_button.setFixedSize(22, 22)
        self.close_button.setStyleSheet(
            """
            QPushButton {
                border: 1px solid #E5E7EB;
                border-radius: 11px;
                padding: 0;
                background: #F9FAFB;
                color: #6B7280;
                font-weight: 900;
            }
            QPushButton:hover {
                background: #FEE2E2;
                color: #B91C1C;
            }
            QPushButton:pressed {
                background: #FCA5A5;
            }
            """
        )
        self.close_button.clicked.connect(self._emit_mark_done)
        top.addWidget(self.close_button, 0)
        root.addLayout(top)
        
        # 간단한 요약 추가 (회색 박스)
        description = todo.get("description", "")
        if description:
            summary = self._create_brief_summary(description)
            if summary:
                summary_label = QLabel(summary)
                summary_label.setStyleSheet("""
                    color:#6B7280; 
                    background:#F9FAFB; 
                    padding:6px 10px; 
                    border-radius:6px;
                    border:1px solid #E5E7EB;
                """)
                summary_label.setWordWrap(True)
                summary_label.setMaximumHeight(50)
                root.addWidget(summary_label)

        meta = QHBoxLayout()
        meta.setSpacing(12)
        req = QLabel(f"요청자 · {todo.get('requester','')}")
        typ = QLabel(f"유형 · {todo.get('type','')}")
        for widget in (req, typ):
            widget.setStyleSheet("color:#374151; background:#F3F4F6; padding:2px 6px; border-radius:8px;")
            meta.addWidget(widget, 0)
        
        # 소스 타입 표시 (메일/메시지)
        source_badge = _create_source_type_badge(todo.get("source_type"))
        meta.addWidget(source_badge, 0)
        
        # 수신 타입 표시 (참조/직접 수신)
        recipient_badge = _create_recipient_type_badge(todo.get("recipient_type"))
        if recipient_badge:
            meta.addWidget(recipient_badge, 0)
        
        # 수신 시간 표시
        if todo.get("created_at"):
            from utils.datetime_utils import parse_iso_datetime
            created_dt = parse_iso_datetime(todo.get("created_at"))
            if created_dt:
                # 한국 시간으로 변환하여 표시
                from datetime import timezone, timedelta
                kst = timezone(timedelta(hours=9))
                created_kst = created_dt.astimezone(kst)
                created_str = created_kst.strftime("%m/%d %H:%M")
                created_lbl = QLabel(f"수신 · {created_str}")
                created_lbl.setStyleSheet("color:#059669; background:#D1FAE5; padding:2px 6px; border-radius:8px;")
                meta.addWidget(created_lbl, 0)
        
        # 마감 시간 표시
        if todo.get("deadline"):
            deadline_lbl = QLabel(f"마감 · {todo.get('deadline')}")
            deadline_lbl.setStyleSheet("color:#9F1239; background:#FFE4E6; padding:2px 6px; border-radius:8px;")
            meta.addWidget(deadline_lbl, 0)
        if _is_truthy(todo.get("is_top3")):
            badge = QLabel("Top-3")
            badge.setStyleSheet("color:#991B1B; background:#FDE68A; padding:2px 8px; border-radius:999px; font-weight:700;")
            meta.addWidget(badge, 0)
        meta.addStretch(1)
        root.addLayout(meta)

        chips_row = QHBoxLayout()
        chips_row.setSpacing(6)
        deadline_badge = _deadline_badge(todo)
        if deadline_badge:
            text, fg, bg = deadline_badge
            dl = QLabel(text)
            dl.setStyleSheet(f"color:{fg}; background:{bg}; padding:2px 8px; border-radius:999px; font-weight:600;")
            chips_row.addWidget(dl, 0)
        evidence_cnt = _evidence_count(todo)
        if evidence_cnt:
            ev = QLabel(f"근거 {evidence_cnt}개")
            ev.setStyleSheet("color:#0F172A; background:#E2E8F0; padding:2px 8px; border-radius:999px; font-weight:600;")
            chips_row.addWidget(ev, 0)
        if chips_row.count():
            chips_row.addStretch(1)
            root.addLayout(chips_row)

        self.set_unread(unread)
    
    def _create_brief_summary(self, description: str) -> str:
        """설명을 간단하게 요약 (첫 줄만 표시)"""
        if not description:
            return ""
        
        # 줄바꿈 제거 및 공백 정리
        cleaned = " ".join(description.split())
        
        # 첫 문장만 추출
        sentences = cleaned.replace("。", ".").split(".")
        first_sentence = sentences[0].strip() if sentences else cleaned
        
        # 최대 100자로 제한 (첫 줄이 이미 보이므로 간단하게)
        if len(first_sentence) > 100:
            return first_sentence[:97] + "..."
        
        return first_sentence

    def set_unread(self, unread: bool) -> None:
        self._unread = unread
        if unread:
            self.new_badge.show()
            self.setStyleSheet(self._unread_style)
            
            # 10초 후 자동으로 읽음 처리 (알람 효과 자동 해제)
            if not hasattr(self, '_auto_read_timer'):
                from PyQt6.QtCore import QTimer
                self._auto_read_timer = QTimer()
                self._auto_read_timer.setSingleShot(True)
                self._auto_read_timer.timeout.connect(lambda: self.set_unread(False))
            
            self._auto_read_timer.start(10000)  # 10초
        else:
            self.new_badge.hide()
            self.setStyleSheet(self._read_style)
            
            # 타이머 정리
            if hasattr(self, '_auto_read_timer'):
                self._auto_read_timer.stop()
            
            try:
                if isinstance(self.todo, dict):
                    self.todo["_viewed"] = True
            except Exception:
                pass

    def _emit_mark_done(self) -> None:
        self.mark_done_clicked.emit(self.todo)
# 4) TodoPanel 본체
# ─────────────────────────────────────────────────────────────────────────────
class TodoPanel(QWidget):
    def __init__(self, db_path=None, parent=None, top3_callback: Optional[Callable[[List[dict]], None]] = None):
        super().__init__(parent)

        # db_path가 None이면 폴백 경로 사용
        if db_path is None:
            db_path = TODO_DB_PATH_FALLBACK
            logger.warning(f"[TodoPanel] db_path가 None, 폴백 경로 사용: {db_path}")
        
        logger.info(f"[TodoPanel] DB 경로: {db_path}")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = get_conn(db_path)
        init_db(self.conn)

        # Top3 서비스는 MainWindow에서 전달받음 (나중에 설정됨)
        self.top3_service = None

        # 애플리케이션 시작 시 오래된 TODO만 정리 (14일 이상)
        logger.info("애플리케이션 시작: 오래된 TODO 데이터 정리")
        self._cleanup_old_rows(days=14)
        
        # 기존 TODO 유지 (삭제하지 않음)
        # 사용자가 원하면 수동으로 "모두 삭제" 버튼 사용 가능
        self._top3_cache: List[dict] = []
        self._all_rows: List[dict] = []
        self._top3_all: List[dict] = []
        self._rest_all: List[dict] = []
        self._current_top3: List[dict] = []
        self._viewed_ids: set[str] = set()
        self._item_widgets: Dict[str, Tuple[QListWidgetItem | None, BasicTodoItem | None]] = {}
        self._top3_updated_cb: Optional[Callable[[List[dict]], None]] = top3_callback

        self.setup_ui()
        # refresh_todo_list() 호출 제거 - 초기화 상태 유지
        self._refresh_rule_tooltip()

        self.snooze_timer = QTimer(self)
        self.snooze_timer.setInterval(60 * 1000)
        self.snooze_timer.timeout.connect(self.on_snooze_timer)
        self.snooze_timer.start()

    def _cleanup_old_rows(self, days: int = 14) -> None:
        try:
            cur = self.conn.cursor()
            cur.execute(f"""
                DELETE FROM todos
                WHERE created_at IS NOT NULL
                  AND created_at <> ''
                  AND datetime(replace(substr(created_at,1,19),'T',' '))
                        < datetime('now', '-{days} days', 'localtime')
            """)
            self.conn.commit()
        except Exception as e:
            print(f"[TodoPanel] auto-cleanup error: {e}")

    def clear_all_todos(self) -> None:
        """모든 TODO 삭제 (UI 새로고침 포함)"""
        cur = self.conn.cursor()
        cur.execute("DELETE FROM todos")
        self.conn.commit()
        self.refresh_todo_list()
    
    def clear_all_todos_silent(self) -> None:
        """모든 TODO 삭제 (UI 새로고침 없음, 초기화용)"""
        try:
            cur = self.conn.cursor()
            cur.execute("DELETE FROM todos")
            self.conn.commit()
            logger.info("기존 TODO 데이터 삭제 완료")
        except Exception as e:
            logger.error(f"TODO 데이터 삭제 실패: {e}")

    def setup_ui(self) -> None:
        root = QVBoxLayout(self)

        top_header = QHBoxLayout()
        self.top3_label = QLabel("🔺 Top-3 (즉시 처리)")
        self.top3_rule_btn = QPushButton("Top-3 기준 설정")
        self.top3_rule_btn.clicked.connect(self.open_top3_rule_dialog)
        self.top3_nl_btn = QPushButton("자연어 규칙")
        self.top3_nl_btn.clicked.connect(self.open_top3_nl_dialog)

        top_header.addWidget(self.top3_label)
        top_header.addWidget(self.top3_rule_btn)
        top_header.addWidget(self.top3_nl_btn)
        top_header.addStretch(1)


        filter_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("검색: 제목, 요청자, 메모...")
        self.priority_filter = QComboBox()
        self.priority_filter.addItem("우선순위 전체", "all")
        self.priority_filter.addItem("High", "high")
        self.priority_filter.addItem("Medium", "medium")
        self.priority_filter.addItem("Low", "low")
        filter_row.addWidget(self.search_input, 2)
        filter_row.addWidget(self.priority_filter, 1)

        self.todo_label = QLabel("📋 TODO 리스트 (High → Low)")
        self.todo_list = QListWidget()
        self.todo_list.setSpacing(8)
        self.todo_list.itemClicked.connect(self._on_item_clicked)

        root.addLayout(top_header)
        root.addLayout(filter_row)
        root.addSpacing(6)
        root.addWidget(self.todo_label)
        root.addWidget(self.todo_list)

        self.todo_label.setVisible(False)

        self.search_input.textChanged.connect(self._re_render)
        self.priority_filter.currentIndexChanged.connect(self._re_render)

    def open_top3_rule_dialog(self) -> None:
        if not self.top3_service:
            QMessageBox.warning(self, "오류", "Top3 서비스가 초기화되지 않았습니다.")
            return
        dialog = Top3RuleDialog(self.top3_service.get_rules(), self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.top3_service.set_rules(dialog.rules())
            self.top3_service._save_rules()
            # DB에서 다시 로드하여 Top3 재계산
            self.refresh_todo_list()
            self._refresh_rule_tooltip()
            QMessageBox.information(self, "Top-3 기준", self.top3_service.describe_rules())

    def open_top3_nl_dialog(self) -> None:
        if not self.top3_service:
            QMessageBox.warning(self, "오류", "Top3 서비스가 초기화되지 않았습니다.")
            return
        dialog = Top3NaturalRuleDialog(
            self, 
            seed_text=self.top3_service.get_last_instruction(), 
            summary_text=self.top3_service.describe_rules()
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            text = dialog.rule_text()
            message, summary = self.top3_service.apply_natural_language_rules(text, reset=dialog.should_reset())
            # DB에서 다시 로드하여 Top3 재계산
            self.refresh_todo_list()
            self._refresh_rule_tooltip()
            QMessageBox.information(self, "Top-3 자연어 규칙", f"{message}\n\n{summary}")

    def _refresh_rule_tooltip(self) -> None:
        if not self.top3_service:
            return
        summary = self.top3_service.describe_rules()
        last_instruction = self.top3_service.get_last_instruction()
        if last_instruction:
            summary += f"\n\n최근 자연어 규칙: {last_instruction}"
        if hasattr(self, "top3_label") and self.top3_label:
            self.top3_label.setToolTip(summary)
        if hasattr(self, "top3_rule_btn") and self.top3_rule_btn:
            self.top3_rule_btn.setToolTip(summary)
        if hasattr(self, "top3_nl_btn") and self.top3_nl_btn:
            self.top3_nl_btn.setToolTip(summary + "\n\n자연어 규칙을 입력하여 특정 요청자/키워드에 추가 가중치를 부여합니다.")

    def on_snooze_timer(self) -> None:
        check_snoozes_and_deadlines(self.conn)
        self.refresh_todo_list()

    def populate_from_items(self, items: List[dict]) -> None:
        items = items or []
        now_iso = datetime.now().isoformat()

        if not items:
            self._rebuild_from_rows([])
            return

        new_rows: List[dict] = []
        for raw in items:
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
                "recipient_type": "to",  # 기본값: 직접 수신
            }
            todo = {**base, **(raw or {})}

            if not todo.get("id"):
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
            new_rows.append(todo)

        # DB에 저장 (중요!)
        logger.info(f"[TodoPanel] {len(new_rows)}개 TODO를 DB에 저장")
        self._save_to_db(new_rows)
        
        self._rebuild_from_rows(new_rows)
    
    def _save_to_db(self, rows: List[dict]) -> None:
        """TODO를 DB에 저장"""
        try:
            logger.info(f"[TodoPanel] {len(rows)}개 TODO를 DB에 저장 (중복 ID 확인 중...)")
            
            # ID 중복 확인 (디버깅용)
            id_counts = {}
            for row in rows:
                todo_id = row.get("id")
                if todo_id:
                    id_counts[todo_id] = id_counts.get(todo_id, 0) + 1
            
            duplicates = {k: v for k, v in id_counts.items() if v > 1}
            if duplicates:
                logger.warning(f"[TodoPanel] ⚠️ 중복 ID 발견: {len(duplicates)}개 ID가 중복됨")
                logger.warning(f"[TodoPanel] 중복 ID 샘플: {list(duplicates.items())[:5]}")
            
            # 트랜잭션 시작
            cur = self.conn.cursor()
            cur.execute("BEGIN TRANSACTION")
            
            try:
                # 기존 TODO 삭제
                cur.execute("DELETE FROM todos")
                
                # 새 TODO 삽입 (INSERT OR REPLACE 사용)
                inserted_count = 0
                for row in rows:
                    # source_message를 JSON 문자열로 변환
                    source_msg = row.get("source_message", {})
                    if isinstance(source_msg, dict):
                        source_msg_str = json.dumps(source_msg, ensure_ascii=False)
                    else:
                        source_msg_str = source_msg or "{}"
                    
                    cur.execute("""
                        INSERT OR REPLACE INTO todos (
                            id, title, description, priority, deadline, deadline_ts,
                            requester, type, status, source_message, created_at, updated_at,
                            snooze_until, is_top3, draft_subject, draft_body, evidence,
                            deadline_confidence, recipient_type, source_type
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
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
                        row.get("source_type", "메시지")
                    ))
                    inserted_count += 1
                
                # 커밋
                self.conn.commit()
                
                # 실제 저장된 개수 확인
                cur.execute("SELECT COUNT(*) FROM todos")
                actual_count = cur.fetchone()[0]
                logger.info(f"[TodoPanel] ✅ TODO DB 저장 완료: {inserted_count}개 삽입 → {actual_count}개 저장됨")
                
            except Exception as e:
                # 롤백
                self.conn.rollback()
                logger.error(f"[TodoPanel] ❌ TODO DB 저장 실패 (롤백됨): {e}", exc_info=True)
                raise
                
        except Exception as e:
            logger.error(f"[TodoPanel] ❌ TODO DB 저장 실패: {e}", exc_info=True)

    def refresh_todo_list(self) -> None:
        logger.info(f"[TodoPanel] refresh_todo_list 시작")
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM todos WHERE status!='done' ORDER BY created_at DESC")
        rows = [dict(r) for r in cur.fetchall()]
        logger.info(f"[TodoPanel] DB에서 {len(rows)}개 TODO 로드")

        if not rows:
            logger.warning("[TodoPanel] TODO가 없음")
            if self._all_rows:
                # DB가 비어도 기존 메모리 상태를 유지
                self._set_render_lists(self._all_rows, self._top3_all or [], self._rest_all or [])
                return
            self._rebuild_from_rows([])
            return
        
        if not self.top3_service:
            logger.warning("[TodoPanel] Top3Service가 없음")
            self._rebuild_from_rows(rows)
            return

        logger.info(f"[TodoPanel] Top3 재계산 시작")
        top_ids = self.top3_service.pick_top3(rows)
        logger.info(f"[TodoPanel] Top3 선정: {len(top_ids)}개")
        updates = []
        for row in rows:
            mark = 1 if row.get("id") in top_ids else 0
            if _is_truthy(row.get("is_top3")) != bool(mark):
                updates.append((mark, row.get("id")))
            row["is_top3"] = mark

        if updates:
            upd = self.conn.cursor()
            upd.executemany("UPDATE todos SET is_top3=? WHERE id=?", updates)
            self.conn.commit()

        self._rebuild_from_rows(rows)

    def set_top3_callback(self, callback: Optional[Callable[[List[dict]], None]]) -> None:
        self._top3_updated_cb = callback

    def _update_top3_header(self, top3: List[dict]) -> None:
        if not top3:
            self.top3_label.setText("🔺 Top-3 (즉시 처리)")

            self._current_top3 = []
            return

        self.top3_label.setText(f"🔺 Top-3 (즉시 처리) · {len(top3)}")

        self._current_top3 = top3

    def _set_render_lists(self, all_rows: List[dict], top3_items: List[dict], rest_items: List[dict]) -> None:
        self._all_rows = list(all_rows)
        limited_top3 = list(top3_items[:3])
        self._top3_all = limited_top3
        self._rest_all = list(rest_items)

        new_ids = {row.get("id") for row in self._all_rows if row.get("id")}
        self._viewed_ids.intersection_update(new_ids)

        if self._top3_updated_cb:
            self._top3_updated_cb(limited_top3)

        self._re_render()

    def _rebuild_from_rows(self, rows: List[dict]) -> None:
        if not rows:
            self._set_render_lists([], [], [])
            return

        cloned_rows: List[dict] = []
        for row in rows:
            cloned = dict(row)
            cloned["status"] = (cloned.get("status") or "pending").lower()
            cloned_rows.append(cloned)

        if self.top3_service:
            top_ids = self.top3_service.pick_top3(cloned_rows)
        else:
            top_ids = set()
            
        for row in cloned_rows:
            row_id = row.get("id")
            row["is_top3"] = 1 if row_id and row_id in top_ids else 0

        # Top3 점수로 정렬
        for row in cloned_rows:
            if self.top3_service:
                row["_top3_score"] = self.top3_service.calculate_score(row)
            else:
                row["_top3_score"] = 0.0
        
        top3_items = sorted(
            [row for row in cloned_rows if row.get("id") in top_ids],
            key=lambda t: (t.get("_top3_score", 0), _created_ts(t)),
            reverse=True,
        )
        rest_items = sorted(
            [row for row in cloned_rows if row.get("id") not in top_ids],
            key=_priority_sort_key,
        )

        self._set_render_lists(cloned_rows, top3_items, rest_items)

    def _re_render(self) -> None:
        if not self._all_rows:
            self.todo_list.clear()
            self.todo_label.setVisible(False)
            self._item_widgets.clear()
            self._top3_cache = []
            self._update_top3_header([])
            self.todo_list.addItem("등록된 TODO가 없습니다.")
            return

        self._update_top3_header(self._top3_all)

        self._top3_cache = []
        for todo in self._top3_all:
            cloned = dict(todo)
            todo_id = cloned.get("id")
            if todo_id and todo_id in self._viewed_ids:
                cloned["_viewed"] = True
            self._top3_cache.append(cloned)

        filtered_top3 = [todo for todo in self._top3_all if self._match_filters(todo)]
        filtered_rest = [todo for todo in self._rest_all if self._match_filters(todo)]

        if not filtered_top3 and not filtered_rest:
            self.todo_list.clear()
            self.todo_label.setVisible(False)
            self._item_widgets.clear()
            self.todo_list.addItem("검색 조건에 맞는 TODO가 없습니다.")
            return

        self._render_rest(filtered_top3, filtered_rest)

    def _render_rest(self, top3_preview: List[dict], rest: List[dict]) -> None:
        self.todo_list.clear()
        sections: List[tuple[str, str, List[dict]]] = []
        self._item_widgets.clear()

        if top3_preview:
            sections.append(("top3", "🔺 Top-3 미리보기", list(top3_preview)))

        buckets = {"high": [], "medium": [], "low": []}
        for todo in rest:
            key = (todo.get("priority") or "low").lower()
            if key not in buckets:
                key = "low"
            buckets[key].append(todo)

        sections.extend([
            ("high", "🔥 High Priority", buckets["high"]),
            ("medium", "⚖️ Medium Priority", buckets["medium"]),
            ("low", "🧊 Low Priority", buckets["low"]),
        ])

        any_items = False
        for key, label, bucket in sections:
            if not bucket:
                continue
            any_items = True
            header = QLabel(label)
            header.setStyleSheet("padding:6px 10px; font-weight:700; color:#1F2937; background:#E5E7EB; border-radius:6px;")
            header_item = QListWidgetItem()
            header_item.setFlags(Qt.ItemFlag.NoItemFlags)
            header_item.setSizeHint(header.sizeHint())
            self.todo_list.addItem(header_item)
            self.todo_list.setItemWidget(header_item, header)

            for todo in bucket:
                todo_id = todo.get("id")
                already_viewed = todo.get("_viewed") or (todo_id in self._viewed_ids if todo_id else False)
                if already_viewed:
                    todo["_viewed"] = True
                unread = _is_unread(todo) and not already_viewed
                widget = BasicTodoItem(todo, parent=self, unread=unread)
                widget.mark_done_clicked.connect(self._on_mark_done_clicked)
                item = QListWidgetItem()
                item.setSizeHint(widget.sizeHint())
                item.setData(Qt.ItemDataRole.UserRole, todo)
                self.todo_list.addItem(item)
                self.todo_list.setItemWidget(item, widget)
                if todo_id:
                    self._item_widgets[todo_id] = (item, widget)

        if not any_items:
            self.todo_label.setVisible(False)
            self.todo_list.addItem("추가로 처리할 TODO가 없습니다.")
        else:
            self.todo_label.setVisible(True)

    def _match_filters(self, todo: dict) -> bool:
        search = self.search_input.text().strip().lower()
        priority = self.priority_filter.currentData()
        if priority is None:
            priority = "all"
        todo_priority = (todo.get("priority") or "low").lower()
        if priority != "all" and todo_priority != priority:
            return False
        if not search:
            return True
        haystack = " ".join([
            todo.get("title", ""),
            todo.get("description", ""),
            todo.get("requester", ""),
            todo.get("type", ""),
        ]).lower()
        return search in haystack

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        if not item:
            return
        data = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(data, dict):
            return
        todo = data
        todo_id = todo.get("id")
        if todo_id:
            self._mark_item_viewed(todo_id)
        else:
            widget = self.todo_list.itemWidget(item)
            if widget and hasattr(widget, "set_unread"):
                widget.set_unread(False)
        self._show_detail_dialog(todo)

    def _mark_item_viewed(self, todo_id: Optional[str]) -> None:
        if not todo_id:
            return
        self._viewed_ids.add(todo_id)
        stored = self._item_widgets.get(todo_id)
        if stored:
            item, widget = stored
            if widget and hasattr(widget, "set_unread"):
                widget.set_unread(False)
            if item is not None:
                data = item.data(Qt.ItemDataRole.UserRole)
                if isinstance(data, dict):
                    new_data = dict(data)
                    new_data["_viewed"] = True
                    item.setData(Qt.ItemDataRole.UserRole, new_data)
            return

        for idx in range(self.todo_list.count()):
            item = self.todo_list.item(idx)
            if not item:
                continue
            data = item.data(Qt.ItemDataRole.UserRole)
            if not isinstance(data, dict):
                continue
            if data.get("id") == todo_id:
                new_data = dict(data)
                new_data["_viewed"] = True
                item.setData(Qt.ItemDataRole.UserRole, new_data)
                widget = self.todo_list.itemWidget(item)
                if widget and hasattr(widget, "set_unread"):
                    widget.set_unread(False)
                break

    def _show_detail_dialog(self, todo: dict) -> None:
        dlg = TodoDetailDialog(todo, self)
        dlg.exec()

    def show_top3_dialog(self) -> None:
        if not self._top3_cache:
            QMessageBox.information(self, "Top-3", "즉시 처리해야 할 항목이 없습니다.")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("Top-3 즉시 처리 카드")
        layout = QVBoxLayout(dlg)
        for todo in self._top3_cache:
            todo_id = todo.get("id")
            already_viewed = todo.get("_viewed") or (todo_id in self._viewed_ids if todo_id else False)
            unread = _is_unread(todo) and not already_viewed
            card = End2EndCard(todo, parent=dlg, unread=unread)
            card.send_clicked.connect(self.on_send_clicked)
            card.hold_clicked.connect(self.on_hold_clicked)
            card.snooze_clicked.connect(self.on_snooze_clicked)
            layout.addWidget(card)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, parent=dlg)
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)
        dlg.exec()

    def _on_mark_done_clicked(self, todo: dict) -> None:
        if not todo:
            return
        todo_id = todo.get("id")
        if not todo_id:
            QMessageBox.warning(self, "완료 처리", "ID가 없는 TODO는 삭제할 수 없습니다.")
            return
        self._item_widgets.pop(todo_id, None)
        self._viewed_ids.discard(todo_id)
        self._mark_done(todo_id)

    def on_send_clicked(self, payload: Dict) -> None:
        title = (payload.get("title") or "todo").replace(os.sep, " ")
        subject = payload.get("draft_subject") or f"[확인 요청] {title}"
        body = payload.get("draft_body") or "안녕하세요,\n\n확인 부탁드립니다.\n\n감사합니다."

        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        os.makedirs(desktop, exist_ok=True)
        path = os.path.join(desktop, f"draft_{uuid.uuid4().hex}.txt")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(subject + "\n\n" + body)
            _open_path_cross_platform(path)
            self._mark_done(payload.get("id"))
        except Exception as e:
            QMessageBox.critical(self, "초안 저장 실패", str(e))

    def on_hold_clicked(self, payload: Dict) -> None:
        deadline = payload.get("deadline_ts") or payload.get("deadline")
        now = datetime.now()
        if deadline:
            try:
                start = datetime.fromisoformat(deadline.replace("Z", "+00:00")) if "Z" in deadline else datetime.fromisoformat(deadline)
                start = start - timedelta(minutes=60)
            except Exception:
                start = now + timedelta(hours=1)
        else:
            start = now + timedelta(hours=1)
        end = start + timedelta(minutes=15)

        ics = (
            "BEGIN:VCALENDAR\nVERSION:2.0\nBEGIN:VEVENT\n"
            f"DTSTART:{start.strftime('%Y%m%dT%H%M%S')}\n"
            f"DTEND:{end.strftime('%Y%m%dT%H%M%S')}\n"
            f"SUMMARY:[HOLD] {payload.get('title','작업')}\n"
            f"DESCRIPTION:{payload.get('draft_subject') or ''}\n"
            "END:VEVENT\nEND:VCALENDAR\n"
        )
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        os.makedirs(desktop, exist_ok=True)
        path = os.path.join(desktop, f"hold_{uuid.uuid4().hex}.ics")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(ics)
            _open_path_cross_platform(path)
        except Exception as e:
            QMessageBox.critical(self, "캘린더 홀드 실패", str(e))

    def on_snooze_clicked(self, payload: Dict) -> None:
        until = datetime.now() + timedelta(hours=2)
        try:
            cur = self.conn.cursor()
            cur.execute(
                "UPDATE todos SET status='snoozed', snooze_until=?, updated_at=? WHERE id=?",
                (until.isoformat(), datetime.now().isoformat(), payload.get("id")),
            )
            self.conn.commit()
            self.refresh_todo_list()
        except Exception as e:
            QMessageBox.critical(self, "스누즈 실패", str(e))

    def _mark_done(self, todo_id) -> None:
        if not todo_id:
            return
        now_iso = datetime.now().isoformat()
        db_updated = False
        try:
            cur = self.conn.cursor()
            cur.execute(
                "UPDATE todos SET status='done', updated_at=? WHERE id=?",
                (now_iso, todo_id),
            )
            db_updated = cur.rowcount > 0
            self.conn.commit()
        except Exception as e:
            QMessageBox.critical(self, "완료 처리 실패", str(e))
            return

        self._viewed_ids.discard(todo_id)
        self._item_widgets.pop(todo_id, None)

        if self._all_rows:
            remaining = [row for row in self._all_rows if row.get("id") != todo_id]
            if len(remaining) != len(self._all_rows):
                self._rebuild_from_rows(remaining)
                return

        if db_updated:
            self.refresh_todo_list()

class TodoDetailDialog(QDialog):
    """TODO 상세 다이얼로그 - 상하 분할 레이아웃"""
    
    def __init__(self, todo: dict, parent=None):
        super().__init__(parent)
        self.todo = todo
        self.setWindowTitle(todo.get("title") or "TODO 상세")
        self.setMinimumSize(600, 700)

        main_layout = QVBoxLayout(self)
        
        # 상단: 원본 메시지 영역
        upper_group = QLabel("📄 원본 메시지")
        upper_group.setStyleSheet("font-weight:700; font-size:14px; color:#1F2937; padding:8px; background:#F3F4F6; border-radius:6px;")
        main_layout.addWidget(upper_group)
        
        # 원본 메시지 정보
        info_layout = QVBoxLayout()
        
        def add_info(label: str, value: str | None):
            lbl = QLabel(f"{label}: {value or '-'}")
            lbl.setStyleSheet("font-weight:600; color:#374151; padding:4px;")
            info_layout.addWidget(lbl)
        
        add_info("우선순위", (todo.get("priority") or "").capitalize())
        add_info("요청자", todo.get("requester"))
        add_info("유형", todo.get("type"))
        
        # 수신 타입 표시
        recipient_type = (todo.get("recipient_type") or "to").lower()
        if recipient_type == "cc":
            add_info("수신 타입", "참조(CC)")
        elif recipient_type == "bcc":
            add_info("수신 타입", "숨은참조(BCC)")
        else:
            add_info("수신 타입", "직접 수신(TO)")
        
        add_info("마감", todo.get("deadline") or todo.get("deadline_ts"))
        
        main_layout.addLayout(info_layout)
        
        # 원본 메시지 내용
        src = _source_message_dict(todo)
        if src:
            src_info_layout = QVBoxLayout()
            add_info_src = lambda label, value: src_info_layout.addWidget(
                QLabel(f"{label}: {value or '-'}").setStyleSheet("color:#6B7280; padding:2px;") or QLabel(f"{label}: {value or '-'}")
            )
            
            sender_lbl = QLabel(f"발신자: {src.get('sender') or '-'}")
            sender_lbl.setStyleSheet("color:#6B7280; padding:2px;")
            src_info_layout.addWidget(sender_lbl)
            
            if src.get("subject"):
                subject_lbl = QLabel(f"제목: {src.get('subject')}")
                subject_lbl.setStyleSheet("color:#6B7280; padding:2px;")
                src_info_layout.addWidget(subject_lbl)
            
            if src.get("platform"):
                platform_lbl = QLabel(f"플랫폼: {src.get('platform')}")
                platform_lbl.setStyleSheet("color:#6B7280; padding:2px;")
                src_info_layout.addWidget(platform_lbl)
            
            main_layout.addLayout(src_info_layout)
            
            content = src.get("content") or src.get("body")
            if content:
                self.original_message = QTextEdit()
                self.original_message.setReadOnly(True)
                self.original_message.setPlainText(content)
                self.original_message.setStyleSheet("background:#FFFFFF; border:1px solid #E5E7EB; border-radius:6px; padding:8px;")
                self.original_message.setMinimumHeight(200)
                main_layout.addWidget(self.original_message)
        
        # 구분선
        separator = QLabel()
        separator.setStyleSheet("background:#D1D5DB; min-height:2px; max-height:2px;")
        main_layout.addWidget(separator)
        
        # 하단: 요약 및 액션 영역
        lower_group = QLabel("📝 요약 및 액션")
        lower_group.setStyleSheet("font-weight:700; font-size:14px; color:#1F2937; padding:8px; background:#F3F4F6; border-radius:6px;")
        main_layout.addWidget(lower_group)
        
        # 요약 표시 영역
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setPlaceholderText("요약이 생성되지 않았습니다. '요약 생성' 버튼을 클릭하세요.")
        self.summary_text.setStyleSheet("background:#F9FAFB; border:1px solid #E5E7EB; border-radius:6px; padding:8px;")
        self.summary_text.setMinimumHeight(120)
        
        # 기존 요약이 있으면 표시
        existing_summary = self._get_existing_summary()
        if existing_summary:
            self.summary_text.setPlainText(existing_summary)
        
        main_layout.addWidget(self.summary_text)
        
        # 액션 버튼들
        action_layout = QHBoxLayout()
        
        self.generate_summary_btn = QPushButton("📋 요약 생성")
        self.generate_summary_btn.setStyleSheet("""
            QPushButton {
                background:#3B82F6; color:white; padding:8px 16px; 
                border-radius:6px; font-weight:600;
            }
            QPushButton:hover {
                background:#2563EB;
            }
            QPushButton:disabled {
                background:#9CA3AF; color:#E5E7EB;
            }
        """)
        self.generate_summary_btn.clicked.connect(self._generate_summary)
        action_layout.addWidget(self.generate_summary_btn)
        
        self.generate_reply_btn = QPushButton("✉️ 회신 초안 작성")
        self.generate_reply_btn.setStyleSheet("""
            QPushButton {
                background:#10B981; color:white; padding:8px 16px; 
                border-radius:6px; font-weight:600;
            }
            QPushButton:hover {
                background:#059669;
            }
            QPushButton:disabled {
                background:#9CA3AF; color:#E5E7EB;
            }
        """)
        self.generate_reply_btn.clicked.connect(self._generate_reply)
        action_layout.addWidget(self.generate_reply_btn)
        
        main_layout.addLayout(action_layout)
        
        # 회신 초안 표시 영역 (처음에는 숨김)
        self.reply_text = QTextEdit()
        self.reply_text.setPlaceholderText("회신 초안이 여기에 생성됩니다...")
        self.reply_text.setStyleSheet("background:#FFFFFF; border:1px solid #E5E7EB; border-radius:6px; padding:8px;")
        self.reply_text.setMinimumHeight(150)
        self.reply_text.setVisible(False)
        main_layout.addWidget(self.reply_text)
        
        # 닫기 버튼
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, parent=self)
        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)
    
    def _get_existing_summary(self) -> str:
        """기존 요약 가져오기"""
        desc = self.todo.get("description", "")
        if desc and len(desc) > 10:
            # 간단한 요약 생성 (첫 3문장)
            sentences = desc.replace("。", ".").split(".")
            summary_sentences = [s.strip() for s in sentences[:3] if s.strip()]
            if summary_sentences:
                return "\n".join(f"• {s}" for s in summary_sentences)
        return ""
    
    def _generate_summary(self):
        """LLM을 사용하여 요약 생성"""
        self.generate_summary_btn.setEnabled(False)
        self.generate_summary_btn.setText("⏳ 생성 중...")
        self.summary_text.setPlainText("요약을 생성하는 중입니다...")
        
        # 원본 메시지 내용 가져오기
        src = _source_message_dict(self.todo)
        content = ""
        if src:
            content = src.get("content") or src.get("body") or ""
        
        if not content:
            content = self.todo.get("description", "")
        
        if not content:
            self.summary_text.setPlainText("요약할 내용이 없습니다.")
            self.generate_summary_btn.setEnabled(True)
            self.generate_summary_btn.setText("📋 요약 생성")
            return
        
        try:
            # LLM 호출
            summary = self._call_llm_for_summary(content)
            self.summary_text.setPlainText(summary)
        except Exception as e:
            logger.error(f"요약 생성 실패: {e}")
            self.summary_text.setPlainText(f"요약 생성 중 오류가 발생했습니다:\n{str(e)}")
        finally:
            self.generate_summary_btn.setEnabled(True)
            self.generate_summary_btn.setText("📋 요약 생성")
    
    def _generate_reply(self):
        """LLM을 사용하여 회신 초안 생성"""
        self.generate_reply_btn.setEnabled(False)
        self.generate_reply_btn.setText("⏳ 생성 중...")
        self.reply_text.setVisible(True)
        self.reply_text.setPlainText("회신 초안을 생성하는 중입니다...")
        
        # 원본 메시지 내용 가져오기
        src = _source_message_dict(self.todo)
        content = ""
        sender = ""
        if src:
            content = src.get("content") or src.get("body") or ""
            sender = src.get("sender", "")
        
        if not content:
            content = self.todo.get("description", "")
        
        if not content:
            self.reply_text.setPlainText("회신할 내용이 없습니다.")
            self.generate_reply_btn.setEnabled(True)
            self.generate_reply_btn.setText("✉️ 회신 초안 작성")
            return
        
        try:
            # LLM 호출
            reply = self._call_llm_for_reply(content, sender)
            self.reply_text.setPlainText(reply)
        except Exception as e:
            logger.error(f"회신 초안 생성 실패: {e}")
            self.reply_text.setPlainText(f"회신 초안 생성 중 오류가 발생했습니다:\n{str(e)}")
        finally:
            self.generate_reply_btn.setEnabled(True)
            self.generate_reply_btn.setText("✉️ 회신 초안 작성")
    
    def _call_llm_for_summary(self, content: str) -> str:
        """LLM을 호출하여 요약 생성
        
        원본 메시지를 3-5개의 불릿 포인트로 간결하게 요약합니다.
        
        Args:
            content: 요약할 메시지 내용 (최대 2000자)
            
        Returns:
            생성된 요약 텍스트
            
        Raises:
            ValueError: LLM 설정이 완료되지 않은 경우
            requests.RequestException: API 호출 실패 시
        """
        provider = (LLM_CONFIG.get("provider") or "azure").lower()
        
        system_prompt = "당신은 업무 메시지를 간결하게 요약하는 전문가입니다. 핵심 내용만 3-5개의 불릿 포인트로 요약하세요."
        user_prompt = f"다음 메시지를 간결하게 요약해주세요:\n\n{content[:2000]}"
        
        response_text = self._call_llm(system_prompt, user_prompt, provider)
        return response_text
    
    def _call_llm_for_reply(self, content: str, sender: str) -> str:
        """LLM을 호출하여 회신 초안 생성
        
        원본 메시지를 분석하여 정중하고 명확한 회신 초안을 작성합니다.
        
        Args:
            content: 원본 메시지 내용 (최대 2000자)
            sender: 발신자 이름
            
        Returns:
            생성된 회신 초안 텍스트
            
        Raises:
            ValueError: LLM 설정이 완료되지 않은 경우
            requests.RequestException: API 호출 실패 시
        """
        provider = (LLM_CONFIG.get("provider") or "azure").lower()
        
        system_prompt = "당신은 업무 이메일 회신을 작성하는 전문가입니다. 정중하고 명확한 회신을 작성하세요."
        user_prompt = f"다음 메시지에 대한 회신 초안을 작성해주세요:\n\n발신자: {sender}\n\n내용:\n{content[:2000]}"
        
        response_text = self._call_llm(system_prompt, user_prompt, provider)
        return response_text
    
    def _call_llm(self, system_prompt: str, user_prompt: str, provider: str) -> str:
        """LLM API 호출 (공통)
        
        공급자별로 최적화된 파라미터를 사용하여 LLM API를 호출합니다.
        
        Args:
            system_prompt: 시스템 프롬프트
            user_prompt: 사용자 프롬프트
            provider: LLM 공급자 ("azure", "openai", "openrouter")
            
        Returns:
            LLM 응답 텍스트
            
        Raises:
            ValueError: 설정이 완료되지 않았거나 지원되지 않는 공급자인 경우
            requests.HTTPError: API 호출 실패 시
            
        Note:
            Azure OpenAI는 max_completion_tokens를 사용하고 temperature는 deployment 설정을 따릅니다.
            OpenAI와 OpenRouter는 max_tokens와 temperature를 명시적으로 설정합니다.
        """
        model = LLM_CONFIG.get("model") or "gpt-4"
        headers: Dict[str, str] = {}
        url: Optional[str] = None
        payload_model: Optional[str] = model
        
        # 공급자별 API 설정
        if provider == "azure":
            api_key = LLM_CONFIG.get("azure_api_key") or os.getenv("AZURE_OPENAI_KEY")
            endpoint = (LLM_CONFIG.get("azure_endpoint") or os.getenv("AZURE_OPENAI_ENDPOINT") or "").rstrip("/")
            deployment = LLM_CONFIG.get("azure_deployment") or os.getenv("AZURE_OPENAI_DEPLOYMENT")
            # 안정적인 API 버전 사용 (2024-08-01-preview 권장)
            api_version = LLM_CONFIG.get("azure_api_version") or os.getenv("AZURE_OPENAI_API_VERSION") or "2024-08-01-preview"
            
            if not api_key or not endpoint or not deployment:
                raise ValueError("Azure OpenAI 설정이 완료되지 않았습니다. (api_key, endpoint, deployment 필요)")
            
            url = f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"
            headers = {"api-key": api_key, "Content-Type": "application/json"}
            payload_model = None  # Azure는 deployment에서 모델 지정
        
        elif provider == "openai":
            api_key = LLM_CONFIG.get("openai_api_key") or os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OpenAI API 키가 설정되지 않았습니다.")
            
            url = "https://api.openai.com/v1/chat/completions"
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        
        elif provider == "openrouter":
            api_key = LLM_CONFIG.get("openrouter_api_key") or os.getenv("OPENROUTER_API_KEY")
            if not api_key:
                raise ValueError("OpenRouter API 키가 설정되지 않았습니다.")
            
            base_url = LLM_CONFIG.get("openrouter_base_url") or "https://openrouter.ai/api/v1"
            url = f"{base_url}/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
        else:
            raise ValueError(f"지원되지 않는 LLM 공급자: {provider}")
        
        # 기본 페이로드 구성
        payload: Dict[str, object] = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        
        # 공급자별 파라미터 설정
        # Azure: max_completion_tokens 사용, temperature는 deployment 설정 사용
        # OpenAI/OpenRouter: max_tokens, temperature 명시적 설정
        if provider == "azure":
            payload["max_completion_tokens"] = 500
        else:
            payload["temperature"] = 0.7
            payload["max_tokens"] = 500
        
        # 모델 지정 (Azure는 deployment에서 지정하므로 제외)
        if payload_model:
            payload["model"] = payload_model
        
        # API 호출
        logger.info(f"[TodoDetail][LLM] provider={provider} URL={url[:80]}... 요약/회신 생성 중...")
        logger.debug(f"[TodoDetail][LLM] payload={json.dumps(payload, ensure_ascii=False)[:300]}")
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            logger.info(f"[TodoDetail][LLM] 응답 수신 (status={response.status_code})")
            response.raise_for_status()
        except requests.exceptions.Timeout:
            logger.error("[TodoDetail][LLM] 타임아웃 (60초 초과)")
            raise ValueError("LLM 응답 시간이 초과되었습니다 (60초). 잠시 후 다시 시도해주세요.")
        except requests.exceptions.HTTPError as e:
            logger.error(f"[TodoDetail][LLM] HTTP 오류: {e.response.status_code} - {e.response.text[:500]}")
            raise ValueError(f"LLM API 오류 ({e.response.status_code}): {e.response.text[:200]}")
        except requests.exceptions.RequestException as e:
            logger.error(f"[TodoDetail][LLM] API 호출 실패: {type(e).__name__} - {str(e)}")
            raise ValueError(f"LLM API 호출 실패: {str(e)}")
        
        # 응답 파싱
        try:
            resp_json = response.json()
            logger.debug(f"[TodoDetail][LLM] 응답 JSON: {json.dumps(resp_json, ensure_ascii=False)[:500]}")
        except json.JSONDecodeError as e:
            logger.error(f"[TodoDetail][LLM] JSON 파싱 실패: {e}")
            raise ValueError(f"LLM 응답 파싱 실패: {str(e)}")
        
        choices = resp_json.get("choices") or []
        if not choices:
            logger.error("[TodoDetail][LLM] choices가 비어있음")
            raise ValueError("LLM 응답이 비어있습니다.")
        
        message = choices[0].get("message") or {}
        content = message.get("content") or ""
        
        if not content:
            logger.error("[TodoDetail][LLM] content가 비어있음")
            raise ValueError("LLM 응답 내용이 비어있습니다.")
        
        logger.info(f"[TodoDetail][LLM] 생성 완료 (길이: {len(content)}자)")
        return content.strip()

