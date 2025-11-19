# ui/todo_panel.py
from __future__ import annotations

import os, sys, uuid, json, subprocess, logging, re
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Callable, Optional, Tuple

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QMessageBox, QHBoxLayout, QTextEdit, QPushButton, QDialog, QDialogButtonBox,
    QLineEdit, QComboBox, QFormLayout, QDoubleSpinBox, QCheckBox
)
from PyQt6.QtCore import QTimer, pyqtSignal, Qt
from PyQt6 import sip

# 분리된 헬퍼 및 위젯 import
from .todo_helpers import (
    _parse_iso_dt, _created_ts, _normalize_korean_name,
    _create_recipient_type_badge, _create_source_type_badge,
    _deadline_badge, _evidence_count, _source_message_dict,
    _is_unread, _priority_sort_key
)
from .widgets import End2EndCard
from .dialogs import Top3RuleDialog, Top3NaturalRuleDialog

# 서비스 import
from src.services import Top3Service, TOP3_RULE_DEFAULT, LLMClient
from .todo import TodoRepository
from .todo.controller import TodoPanelController

logger = logging.getLogger(__name__)


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

def _deadline_badge(todo: dict, reference_time: Optional[datetime] = None) -> Optional[tuple[str, str, str]]:
    """마감일 배지 생성
    
    Args:
        todo: TODO 딕셔너리
        reference_time: 기준 시간 (None이면 현재 시간 사용, VDOS 시뮬레이션 시간 전달 가능)
    """
    deadline = todo.get("deadline_ts") or todo.get("deadline")
    dt = _parse_iso_dt(deadline)
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    # 기준 시간 (시뮬레이션 시간 또는 현재 시간)
    now = reference_time if reference_time else datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    
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
# 1) BasicTodoItem: 일반 TODO 항목 위젯
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
        self.todo_data = todo  # 프로젝트 태그 업데이트를 위해 참조 저장
        self._unread = False
        self._unread_style = "QWidget{border:1px solid #FB923C; border-radius:10px; background:#FFF7ED;} QWidget:hover{border-color:#F97316; background:#FFE7D3;}"
        self._read_style = "QWidget{border:1px solid #D1D5DB; border-radius:10px; background:#E5E7EB;} QWidget:hover{border-color:#9CA3AF; background:#D1D5DB;}"
        
        # 기본 스타일을 읽음 상태로 설정 (노란색 깜빡임 방지)
        self.setStyleSheet(self._read_style)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 8, 12, 8)

        top = QHBoxLayout()
        top.setSpacing(8)
        self.top_layout = top  # 프로젝트 태그 업데이트를 위해 레이아웃 저장
        
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
        
        # 프로젝트 태그 추가
        self.project_tag_widget = None  # 프로젝트 태그 위젯 참조 저장
        project_code = todo.get("project")
        logger.debug(f"[프로젝트 태그] TODO {todo.get('id', 'unknown')}: project_code={project_code}")
        if project_code:
            try:
                from .widgets.project_tag_widget import create_project_tag_label
                project_tag = create_project_tag_label(project_code)
                if project_tag:
                    self.project_tag_widget = project_tag
                    top.addWidget(project_tag, 0)
                    logger.debug(f"[프로젝트 태그] ✅ {project_code} 태그 추가 완료")
                else:
                    logger.warning(f"[프로젝트 태그] ❌ {project_code} 태그 생성 실패")
            except ImportError as e:
                logger.warning(f"프로젝트 태그 위젯 로드 실패: {e}")
            except Exception as e:
                logger.error(f"프로젝트 태그 생성 오류: {e}")
        else:
            logger.debug(f"[프로젝트 태그] TODO {todo.get('id', 'unknown')}: 프로젝트 없음")
        
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
                    padding:8px 12px; 
                    border-radius:6px;
                    border:1px solid #E5E7EB;
                    line-height: 1.4;
                """)
                summary_label.setWordWrap(True)
                summary_label.setMaximumHeight(65)  # 높이 증가 (2줄 표시 가능)
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
        
        # 수신 시간 표시 (원본 메시지의 시뮬레이션 시간 사용)
        received_time = None
        
        # 1. source_message에서 원본 메시지의 date 가져오기 (VDOS DB의 sent_at)
        source_message = todo.get("source_message")
        if source_message:
            try:
                # source_message가 JSON 문자열이면 파싱
                if isinstance(source_message, str):
                    source_msg_dict = json.loads(source_message)
                else:
                    source_msg_dict = source_message
                
                # date 사용 (VDOS DB의 sent_at이 이미 시뮬레이션 시간)
                # simulated_datetime은 수집 시간이므로 사용하지 않음
                received_time = source_msg_dict.get("date")
            except:
                pass
        
        # 2. evidence에서 시도 (폴백)
        if not received_time:
            evidence = todo.get("evidence")
            if evidence:
                try:
                    evidence_list = json.loads(evidence) if isinstance(evidence, str) else evidence
                    if evidence_list and len(evidence_list) > 0:
                        first_msg = evidence_list[0]
                        received_time = first_msg.get("date")
                except:
                    pass
        
        # 3. 없으면 created_at 사용 (폴백)
        if not received_time:
            received_time = todo.get("created_at")
        
        if received_time:
            from utils.datetime_utils import parse_iso_datetime
            received_dt = parse_iso_datetime(received_time)
            if received_dt:
                # 한국 시간으로 변환하여 표시
                from datetime import timezone, timedelta
                kst = timezone(timedelta(hours=9))
                received_kst = received_dt.astimezone(kst)
                received_str = received_kst.strftime("%m/%d %H:%M")
                received_lbl = QLabel(f"수신 · {received_str}")
                received_lbl.setStyleSheet("color:#059669; background:#D1FAE5; padding:2px 6px; border-radius:8px;")
                meta.addWidget(received_lbl, 0)
        
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
        
        # 시뮬레이션 시간 가져오기 (parent가 TodoPanel인 경우)
        sim_time = None
        if parent and hasattr(parent, '_simulation_time'):
            sim_time = parent._simulation_time
        
        deadline_badge = _deadline_badge(todo, sim_time)
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

        # 초기 스타일 설정 (set_unread 호출 전에 명시적으로 설정)
        todo_id = todo.get("id", "unknown")
        if not unread:
            # 읽음 상태로 초기화
            logger.info(f"[BasicTodoItem.__init__] ✅ TODO {todo_id}: unread=False로 초기화 (회색)")
            self.new_badge.hide()
            self.setStyleSheet(self._read_style)
            self._unread = False
            
            # Qt 렌더링 후 스타일 재적용 (깜빡임 방지)
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, lambda: self.setStyleSheet(self._read_style) if not self._unread else None)
        else:
            # 안읽음 상태로 초기화
            logger.warning(f"[BasicTodoItem.__init__] ⚠️ TODO {todo_id}: unread=TRUE로 초기화 (노란색)!!!")
            self.new_badge.show()
            self.setStyleSheet(self._unread_style)
            self._unread = True
    
    def _create_brief_summary(self, description: str) -> str:
        """설명을 간단하게 요약 (가독성 개선)"""
        if not description:
            return ""
        
        # 여러 줄 공백 정리 (줄바꿈은 유지)
        lines = [line.strip() for line in description.split('\n') if line.strip()]
        
        # 빈 줄이 없으면 첫 2줄만, 있으면 첫 문단만
        if not lines:
            return ""
        
        # 첫 문장 또는 첫 줄 추출
        first_part = lines[0]
        
        # 한국어 문장 구분자로 분리 시도
        for separator in ['. ', '.\n', '! ', '?\n', '? ', '!\n']:
            if separator in first_part:
                first_part = first_part.split(separator)[0] + separator.strip()
                break
        
        # 너무 짧으면 두 번째 줄도 추가
        if len(first_part) < 30 and len(lines) > 1:
            second_line = lines[1]
            # 두 번째 줄이 너무 길지 않으면 추가
            if len(second_line) < 50:
                first_part = f"{first_part} {second_line}"
        
        # 최대 320자로 제한 (단어 중간에서 자르지 않도록)
        if len(first_part) > 320:
            truncated = first_part[:317]
            last_space = truncated.rfind(' ')
            if last_space > 200:  # 너무 앞에서 자르지 않도록
                return truncated[:last_space] + "..."
            return truncated + "..."
        
        return first_part

    def set_unread(self, unread: bool) -> None:
        """읽음/안읽음 상태 설정
        
        Args:
            unread: True면 안읽음, False면 읽음
        """
        # 위젯이 이미 삭제되었는지 확인
        try:
            if not self.new_badge or not self.new_badge.isVisible() and not unread:
                return
        except RuntimeError:
            # 위젯이 이미 삭제됨
            return
        
        # 디버깅: unread=True로 설정되는 경우 로그 출력
        todo_id = self.todo.get("id", "unknown")
        if unread:
            import traceback
            stack = ''.join(traceback.format_stack()[-5:-1])  # 최근 4개 호출 스택
            logger.warning(f"[BasicTodoItem.set_unread] ⚠️⚠️⚠️ TODO {todo_id}를 unread=TRUE로 설정! 호출 스택:\n{stack}")
        else:
            logger.info(f"[BasicTodoItem.set_unread] ✅ TODO {todo_id}를 unread=False로 설정 (회색)")
        
        self._unread = unread
        if unread:
            try:
                self.new_badge.show()
                self.setStyleSheet(self._unread_style)
            except RuntimeError:
                # 위젯이 삭제됨
                return
            
            # 10초 후 자동으로 읽음 처리 (알람 효과 자동 해제)
            if not hasattr(self, '_auto_read_timer'):
                from PyQt6.QtCore import QTimer
                self._auto_read_timer = QTimer(self)  # parent 설정으로 자동 정리
                self._auto_read_timer.setSingleShot(True)
                self._auto_read_timer.timeout.connect(self._safe_set_read)
            
            # 이미 실행 중인 타이머가 있으면 중지하고 다시 시작
            if self._auto_read_timer.isActive():
                self._auto_read_timer.stop()
            
            self._auto_read_timer.start(10000)  # 10초
        else:
            try:
                self.new_badge.hide()
                self.setStyleSheet(self._read_style)
            except RuntimeError:
                # 위젯이 삭제됨
                return
            
            # 타이머 정리
            if hasattr(self, '_auto_read_timer'):
                self._auto_read_timer.stop()
            
            try:
                if isinstance(self.todo, dict):
                    self.todo["_viewed"] = True
            except Exception:
                pass
    
    def _safe_set_read(self) -> None:
        """안전하게 읽음 상태로 변경 (타이머 콜백용)"""
        try:
            if self.new_badge and not sip.isdeleted(self):
                self.set_unread(False)
        except (RuntimeError, AttributeError):
            # 위젯이 이미 삭제됨
            pass

    def update_project_tag(self, project_code: str) -> None:
        """프로젝트 태그 업데이트 (비동기 분석 완료 후 호출)"""
        try:
            # 기존 프로젝트 태그 위젯 제거
            if self.project_tag_widget:
                self.top_layout.removeWidget(self.project_tag_widget)
                self.project_tag_widget.deleteLater()
                self.project_tag_widget = None
            
            # 새 프로젝트 태그 위젯 추가
            if project_code:
                from .widgets.project_tag_widget import create_project_tag_label
                project_tag = create_project_tag_label(project_code)
                if project_tag:
                    self.project_tag_widget = project_tag
                    # status 위젯 다음에 삽입 (인덱스 3)
                    self.top_layout.insertWidget(3, project_tag, 0)
                    logger.info(f"[프로젝트 태그] ✅ TODO {self.todo.get('id')}: {project_code} 태그 업데이트 완료")
        except Exception as e:
            logger.error(f"[프로젝트 태그] 업데이트 오류: {e}")
    
    def _emit_mark_done(self) -> None:
        self.mark_done_clicked.emit(self.todo)
# 2) TodoPanel 본체
# ─────────────────────────────────────────────────────────────────────────────
class TodoPanel(QWidget):
    def __init__(self, db_path=None, parent=None, top3_callback: Optional[Callable[[List[dict]], None]] = None):
        super().__init__(parent)

        self._repo = TodoRepository(db_path)
        self.db_path = str(self._repo.db_path)
        logger.info(f"[TodoPanel] DB 경로: {self.db_path}")

        # Top3/프로젝트 서비스는 후속 단계에서 주입
        self.top3_service: Optional[Top3Service] = None

        self.controller = TodoPanelController(repository=self._repo)
        self.llm_client: LLMClient = LLMClient()

        # 애플리케이션 시작 시 오래된 TODO만 정리 (14일 이상)
        logger.info("애플리케이션 시작: 오래된 TODO 데이터 정리")
        self.controller.cleanup_old_rows(days=14)
        
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
        self._simulation_time: Optional[datetime] = None  # VDOS 시뮬레이션 시간
        
        project_service: Optional[object] = None
        try:
            from .widgets.project_tag_widget import get_project_service
            from ..services.todo_migration_service import TodoMigrationService
            
            # 프로젝트 서비스 초기화
            project_service = get_project_service()
            logger.info(f"[프로젝트 태그] 프로젝트 서비스 초기화 완료: {type(project_service)}")
            
            # 데이터베이스 마이그레이션 실행 (project 컬럼 추가)
            migration_service = TodoMigrationService(self.db_path)
            migration_service.migrate_database()
            
        except Exception as e:
            logger.error(f"프로젝트 태그 서비스 로드 실패: {e}")
            # 기본 프로젝트 서비스 생성
            from src.services.project_tag_service import ProjectTagService
            
            # 프로젝트 태그 캐시 DB 경로 설정 (todos_cache.db와 같은 경로)
            import os
            cache_db_path = os.path.join(os.path.dirname(self.db_path), 'project_tags_cache.db')
            
            project_service = ProjectTagService(cache_db_path=cache_db_path)
            logger.info(f"[프로젝트 태그] 기본 프로젝트 서비스 생성 완료 (캐시: {cache_db_path})")

        self.controller.set_project_service(project_service)
        self.controller.set_top3_service(self.top3_service)
        
        # 비동기 프로젝트 태그 서비스 초기화
        self._init_async_project_tag_service(project_service)

        self.setup_ui()
        # refresh_todo_list() 호출 제거 - 초기화 상태 유지
        self._refresh_rule_tooltip()

        self.snooze_timer = QTimer(self)
        self.snooze_timer.setInterval(60 * 1000)
        self.snooze_timer.timeout.connect(self.on_snooze_timer)
        self.snooze_timer.start()

        # 프로젝트 태그 업데이트 타이머 (3초마다 - 빠른 UI 반영)
        self.project_update_timer = QTimer(self)
        self.project_update_timer.setInterval(3 * 1000)
        self.project_update_timer.timeout.connect(self.on_project_update_timer)
        self.project_update_timer.start()
        logger.info("[프로젝트 업데이트] 타이머 시작됨 (3초 간격)")

    def set_top3_service_instance(self, service: Optional[Top3Service]) -> None:
        self.top3_service = service
        self.controller.set_top3_service(service)
    
    def set_simulation_time(self, sim_time: Optional[datetime]) -> None:
        """VDOS 시뮬레이션 시간 설정 (마감일 계산 기준)"""
        self._simulation_time = sim_time
        if sim_time:
            logger.debug(f"시뮬레이션 시간 설정: {sim_time.strftime('%Y-%m-%d %H:%M')}")

    @property
    def repository(self) -> TodoRepository:
        """외부 모듈을 위한 TodoRepository 접근자."""
        return self._repo

    def _cleanup_old_rows(self, days: int = 14) -> None:
        try:
            self.controller.cleanup_old_rows(days)
        except Exception as e:
            logger.error(f"[TodoPanel] auto-cleanup error: {e}")

    def clear_all_todos(self) -> None:
        """모든 TODO 삭제 (UI 새로고침 포함)"""
        self.controller.delete_all()
        self.refresh_todo_list()
    
    def clear_all_todos_silent(self) -> None:
        """모든 TODO 삭제 (UI 새로고침 없음, 초기화용)"""
        try:
            self.controller.delete_all()
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
        
        # 캐시 상태 표시 위젯 추가
        self.cache_status_badge = QLabel()
        self.cache_status_badge.setStyleSheet("""
            QLabel {
                color: #059669;
                background: #D1FAE5;
                padding: 4px 10px;
                border-radius: 12px;
                font-weight: 600;
                font-size: 11px;
            }
        """)
        self.cache_status_badge.setVisible(False)
        top_header.addWidget(self.cache_status_badge)
        
        # 수동 새로고침 버튼 추가
        self.refresh_btn = QPushButton("🔄 새로고침")
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background: #3B82F6;
                color: white;
                padding: 6px 12px;
                border-radius: 6px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #2563EB;
            }
            QPushButton:pressed {
                background: #1D4ED8;
            }
        """)
        self.refresh_btn.setToolTip("현재 페르소나의 캐시를 무효화하고 재분석합니다")
        self.refresh_btn.clicked.connect(self._on_manual_refresh)
        top_header.addWidget(self.refresh_btn)


        # 프로젝트 필터 바 추가
        project_service = self.controller.project_service
        if project_service:
            try:
                from .widgets.project_tag_widget import ProjectTagBar
                self.project_tag_bar = ProjectTagBar()
                self.project_tag_bar.tag_clicked.connect(self._on_project_filter_changed)
            except ImportError as e:
                logger.warning(f"프로젝트 태그 바 로드 실패: {e}")
                self.project_tag_bar = None
        else:
            self.project_tag_bar = None

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
        # 프로젝트 태그 바 추가
        if self.project_tag_bar:
            root.addWidget(self.project_tag_bar)
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
            is_reset = dialog.should_reset()
            message, summary = self.top3_service.apply_natural_language_rules(text, reset=is_reset)
            
            # 1. 규칙 업데이트 팝업 먼저 표시
            QMessageBox.information(self, "Top-3 자연어 규칙", f"{message}\n\n{summary}")
            
            # 2. DB에서 다시 로드하여 Top3 재계산 (팝업 없이)
            self.refresh_todo_list(show_reasoning=False)
            self._refresh_rule_tooltip()
            
            # 3. 초기화가 아닐 때만 선정이유 팝업을 500ms 후에 표시
            if not is_reset:
                QTimer.singleShot(500, self._show_delayed_reasoning_popup)

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
    
    def _show_delayed_reasoning_popup(self) -> None:
        """지연된 선정이유 팝업 표시 (규칙 업데이트 팝업 이후)"""
        if not self.top3_service:
            return
        
        reasoning = self.top3_service.get_last_reasoning()
        if not reasoning:
            return
        
        # Top3 개수 계산
        top3_count = len([todo for todo in self._top3_all if todo.get("is_top3")])
        if top3_count == 0:
            return
        
        try:
            msg_box = QMessageBox()
            msg_box.setWindowTitle("✅ Top3 선정 완료")
            msg_box.setIcon(QMessageBox.Icon.Information)
            msg_box.setText(f"<b>{top3_count}개의 TODO가 Top3로 선정되었습니다</b>")
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
            logger.error(f"[TodoPanel] 선정이유 팝업 표시 오류: {e}")

    def on_snooze_timer(self) -> None:
        self.controller.release_snoozed()
        self.refresh_todo_list()

    def on_project_update_timer(self) -> None:
        """프로젝트 태그 업데이트 타이머 콜백: 새로 분석된 프로젝트 태그를 UI에 반영"""
        try:
            logger.info("[프로젝트 업데이트] 타이머 실행")
            
            # TODO 리스트를 다시 로드해서 프로젝트 태그 업데이트
            rows = self.controller.load_active_items()
            if not rows:
                logger.info("[프로젝트 업데이트] rows 없음 - 스킵")
                return
            
            logger.info(f"[프로젝트 업데이트] DB에서 {len(rows)}개 TODO 로드")
            
            # 프로젝트 태그가 실제로 변경되었는지 확인
            has_changes = False
            changes_detail = []
            for row in rows:
                todo_id = row.get('id')
                # DB 컬럼명은 'project_tag'
                new_project = row.get('project_tag') or row.get('project')
                
                # 현재 UI에 표시된 TODO와 비교
                if todo_id in self._item_widgets:
                    item, widget = self._item_widgets[todo_id]
                    if widget and hasattr(widget, 'todo_data'):
                        old_project = widget.todo_data.get('project')
                        if old_project != new_project:
                            has_changes = True
                            changes_detail.append(f"{todo_id}: {old_project} → {new_project}")
                            if len(changes_detail) < 5:  # 최대 5개만 로그
                                logger.info(f"[프로젝트 업데이트] 변경 감지: {todo_id}: '{old_project}' → '{new_project}'")
            
            # 변경사항이 없으면 프로젝트 태그 바만 업데이트 (초기 로드 대응)
            if not has_changes:
                logger.debug("[프로젝트 업데이트] 변경사항 없음 - 프로젝트 태그 바만 업데이트")
                self._update_project_tag_bar_from_todos(rows)
                return
            
            logger.info(f"[프로젝트 업데이트] 프로젝트 태그 변경 감지 - UI 업데이트")
            
            # 프로젝트 태그 바만 업데이트 (전체 새로고침 없이)
            self._update_project_tag_bar_from_todos(rows)
            
            # 각 TODO 위젯의 프로젝트 태그도 업데이트
            for i in range(self.todo_list.count()):
                item = self.todo_list.item(i)
                widget = self.todo_list.itemWidget(item)
                if widget and hasattr(widget, 'todo_data'):
                    todo_id = widget.todo_data.get('id')
                    # DB에서 최신 프로젝트 태그 가져오기
                    for row in rows:
                        if row.get('id') == todo_id:
                            # DB 컬럼명은 'project_tag'
                            new_project = row.get('project_tag') or row.get('project')
                            widget.todo_data['project'] = new_project
                            if hasattr(widget, 'update_project_tag'):
                                widget.update_project_tag(new_project)
                            break
        except Exception as e:
            logger.error(f"프로젝트 업데이트 타이머 오류: {e}")

    def populate_from_items(
        self,
        items: List[dict],
        incremental: bool = False,
        show_reasoning: bool = False,
    ) -> None:
        """TODO 데이터를 UI/저장소에 반영한다.

        Args:
            items: 새 TODO 리스트
            incremental: True면 기존 목록에 증분 반영
            show_reasoning: Top3 선정 이유 팝업 표시 여부
        """

        safe_count = len(items or [])
        logger.info(
            "[TodoPanel] populate_from_items 호출: %d개 (incremental=%s)",
            safe_count,
            incremental,
        )

        items = items or []
        if not items:
            if incremental:
                logger.info("[TodoPanel] 증분 업데이트에 추가할 항목이 없어 건너뜀")
                return
            logger.info("[TodoPanel] 항목이 없어 빈 목록으로 재구성")
            self._rebuild_from_rows([])
            return

        prepared = self.controller.prepare_items(items)
        prepared = self._deduplicate_todos(prepared)
        if not prepared:
            logger.info("[TodoPanel] 정규화 결과가 없어 업데이트를 건너뜀")
            return

        # 새로운 TODO들을 비동기 프로젝트 태그 분석 큐에 추가
        self.queue_new_todos_for_async_analysis(prepared)

        # 기존 캐시된 프로젝트 태그만 즉시 적용 (LLM 분석은 비동기로)
        self.update_project_tags(prepared)

        if incremental:
            logger.info("[TodoPanel] 증분 모드로 %d개 TODO 저장", len(prepared))
            self.controller.save_items(prepared, incremental=True)
            
            # 증분 모드: 새로 추가된 TODO도 viewed로 처리 (unread 없음)
            for item in prepared:
                todo_id = item.get("id")
                if todo_id:
                    self._viewed_ids.add(todo_id)
            logger.info(f"[TodoPanel] 증분 모드: {len(prepared)}개 새 TODO를 viewed로 처리")
            
            self.refresh_todo_list(show_reasoning=show_reasoning)
        else:
            logger.info("[TodoPanel] 전체 교체 모드로 %d개 TODO 저장", len(prepared))
            self.controller.save_items(prepared, incremental=False)
            
            # 전체 교체 모드: 모든 TODO를 viewed로 처리 (unread 없음)
            self._viewed_ids.clear()  # 기존 viewed_ids 초기화
            for item in prepared:
                todo_id = item.get("id")
                if todo_id:
                    self._viewed_ids.add(todo_id)
            logger.info(f"[TodoPanel] 전체 교체 모드: {len(self._viewed_ids)}개 TODO를 viewed로 처리")
            logger.info(f"[TodoPanel] _viewed_ids 샘플 (처음 5개): {list(self._viewed_ids)[:5]}")
            
            self._rebuild_from_rows(prepared, show_reasoning=show_reasoning)

    def _todo_identity(self, todo: dict) -> str:
        """TODO 고유 식별자 생성 (source_message + title + description)."""
        msg_id = None
        source_message = todo.get("source_message")
        if isinstance(source_message, str):
            try:
                source_message = json.loads(source_message)
            except Exception:
                source_message = None
        if isinstance(source_message, dict):
            msg_id = (
                source_message.get("msg_id")
                or source_message.get("id")
                or source_message.get("message_id")
            )
        
        # 제목 정규화
        title = (todo.get("title") or "").strip().lower()
        title_normalized = re.sub(r"\s+", " ", title).strip()
        
        # 메시지 ID가 있으면 메시지 ID + 제목으로 식별
        # (같은 메시지에서 여러 TODO가 나올 수 있으므로 제목 포함 필수)
        if msg_id:
            return f"msg:{msg_id}|title:{title_normalized}"

        # description(내용)을 기준으로 중복 판단
        description = (todo.get("description") or "").strip()
        deadline_hint = (todo.get("deadline") or todo.get("deadline_ts") or "").strip()
        deadline_bucket = deadline_hint[:10] if deadline_hint else ""
        
        # description이 있으면 내용 기반으로 중복 판단
        if description:
            normalized = re.sub(r"\s+", " ", description).strip().lower()
            if normalized:
                requester = (todo.get("requester") or "").strip().lower() or "-"
                due = deadline_bucket or "-"
                # 내용이 같으면 중복으로 간주 (제목은 무시)
                return f"desc:{normalized}|req:{requester}|due:{due}"

        # description이 없으면 제목+발신자+마감일 조합으로 판단
        requester = (todo.get("requester") or "").strip().lower() or "-"
        due = deadline_bucket or "-"
        return f"title:{title_normalized}|req:{requester}|due:{due}"

    def _deduplicate_todos(self, todos: List[dict]) -> List[dict]:
        """설명/원본이 동일한 TODO를 제거한다."""
        merged: Dict[str, dict] = {}
        duplicates_info = []  # 중복 정보 저장
        
        for todo in todos:
            identity = self._todo_identity(todo)
            if identity in merged:
                # 중복 발견 - 상세 정보 기록
                duplicates_info.append({
                    'identity': identity,
                    'original_title': merged[identity].get('title', ''),
                    'duplicate_title': todo.get('title', ''),
                    'original_desc': (merged[identity].get('description', '') or '')[:100],
                    'duplicate_desc': (todo.get('description', '') or '')[:100],
                    'requester': todo.get('requester', ''),
                    'deadline': todo.get('deadline', '')
                })
                merged[identity] = self._merge_todo_records(merged[identity], todo)
            else:
                merged[identity] = dict(todo)
        
        if len(merged) != len(todos):
            logger.info(
                "[TodoPanel] 중복 TODO %d개 정리 (총 %d개 → %d개)",
                len(todos) - len(merged),
                len(todos),
                len(merged),
            )
            
            # 중복된 TODO 상세 정보 출력 (처음 10개만)
            logger.info("[TodoPanel] === 중복 제거된 TODO 샘플 (최대 10개) ===")
            for idx, dup in enumerate(duplicates_info[:10], 1):
                logger.info(f"  [{idx}] Identity: {dup['identity']}")
                logger.info(f"      원본 제목: {dup['original_title']}")
                logger.info(f"      중복 제목: {dup['duplicate_title']}")
                logger.info(f"      원본 설명: {dup['original_desc']}...")
                logger.info(f"      중복 설명: {dup['duplicate_desc']}...")
                logger.info(f"      요청자: {dup['requester']}, 마감일: {dup['deadline']}")
                logger.info("")
        
        return list(merged.values())

    def _merge_todo_records(self, base: dict, candidate: dict) -> dict:
        """중복 TODO 간에 정보를 병합하고 더 풍부한 데이터를 유지한다."""
        merged = dict(base)
        desc_base = base.get("description") or ""
        desc_new = candidate.get("description") or ""
        if len(desc_new) > len(desc_base):
            merged["description"] = desc_new

        for key in [
            "title",
            "type",
            "deadline",
            "deadline_ts",
            "priority",
            "source_message",
            "requester",
            "status",
            "project",
            "persona_name",
            "project_full_name",
        ]:
            if not merged.get(key) and candidate.get(key):
                merged[key] = candidate[key]

        # type 우선순위: deadline > meeting > task 등
        priority_order = {"deadline": 3, "meeting": 2, "task": 1}
        cur_type = (merged.get("type") or "").lower()
        new_type = (candidate.get("type") or "").lower()
        if priority_order.get(new_type, 0) > priority_order.get(cur_type, 0):
            merged["type"] = candidate.get("type")

        return merged
    
    def refresh_todo_list(self, show_reasoning: bool = False, preserve_existing_on_empty: bool = True) -> None:
        """TODO 리스트 새로고침
        
        Args:
            show_reasoning: True면 Top3 선정이유 팝업 표시 (기본값: False)
            preserve_existing_on_empty: True면 새 데이터가 없을 때 기존 표시를 유지
        """
        logger.info(
            "[TodoPanel] refresh_todo_list 시작 (show_reasoning=%s, preserve_existing_on_empty=%s)",
            show_reasoning,
            preserve_existing_on_empty,
        )
        
        # 현재 페르소나 정보 가져오기
        persona_name = self._get_current_persona_name()
        persona_email = self._get_current_persona_email()
        persona_handle = self._get_current_persona_handle()
        
        # 페르소나 필터 설정
        self.controller.set_persona_filter(
            persona_name=persona_name,
            persona_email=persona_email,
            persona_handle=persona_handle
        )
        
        rows = self.controller.load_active_items()
        logger.info(f"[TodoPanel] DB에서 {len(rows)}개 TODO 로드")

        if not rows:
            # 기존 TODO가 있으면 유지 (백그라운드 분석 중)
            if preserve_existing_on_empty and self._all_rows:
                logger.info("[TodoPanel] TODO 없음 - 기존 TODO 유지 (백그라운드 분석 중)")
                return
            else:
                logger.warning("[TodoPanel] TODO 없음 - 빈 리스트 표시")
                self._rebuild_from_rows([])
                return

        # DB에서 로드한 기존 TODO는 모두 viewed로 처리 (새로고침 시)
        viewed_count = 0
        for row in rows:
            todo_id = row.get("id")
            if todo_id:
                self._viewed_ids.add(todo_id)
                viewed_count += 1
        logger.info(f"[TodoPanel] refresh_todo_list: {viewed_count}개 TODO를 viewed로 처리")
        
        self.update_project_tags(rows)
        self._rebuild_from_rows(rows, show_reasoning=show_reasoning)
    
    def _get_current_persona_email(self) -> Optional[str]:
        """현재 선택된 페르소나의 이메일 주소 가져오기"""
        try:
            # 부모 윈도우에서 선택된 페르소나 정보 가져오기
            parent_window = self.parent()
            while parent_window and not hasattr(parent_window, 'selected_persona'):
                parent_window = parent_window.parent()
            
            if parent_window and hasattr(parent_window, 'selected_persona') and parent_window.selected_persona:
                email = parent_window.selected_persona.email_address
                logger.debug(f"[TodoPanel] 현재 페르소나 이메일: {email}")
                return email
            else:
                logger.debug("[TodoPanel] 페르소나 정보를 찾을 수 없음")
                return None
        except Exception as e:
            logger.error(f"[TodoPanel] 페르소나 이메일 가져오기 오류: {e}")
            return None
    
    def _get_current_persona_name(self) -> Optional[str]:
        """현재 선택된 페르소나의 이름 가져오기"""
        try:
            # 부모 윈도우에서 선택된 페르소나 정보 가져오기
            parent_window = self.parent()
            while parent_window and not hasattr(parent_window, 'selected_persona'):
                parent_window = parent_window.parent()
            
            if parent_window and hasattr(parent_window, 'selected_persona') and parent_window.selected_persona:
                name = parent_window.selected_persona.name
                logger.debug(f"[TodoPanel] 현재 페르소나 이름: {name}")
                return name
            else:
                logger.debug("[TodoPanel] 페르소나 정보를 찾을 수 없음")
                return None
        except Exception as e:
            logger.error(f"[TodoPanel] 페르소나 이름 가져오기 오류: {e}")
            return None
    
    def _get_current_persona_handle(self) -> Optional[str]:
        """현재 선택된 페르소나의 채팅 핸들 가져오기"""
        try:
            # 부모 윈도우에서 선택된 페르소나 정보 가져오기
            parent_window = self.parent()
            while parent_window and not hasattr(parent_window, 'selected_persona'):
                parent_window = parent_window.parent()
            
            if parent_window and hasattr(parent_window, 'selected_persona') and parent_window.selected_persona:
                handle = parent_window.selected_persona.chat_handle
                logger.debug(f"[TodoPanel] 현재 페르소나 핸들: {handle}")
                return handle
            else:
                logger.debug("[TodoPanel] 페르소나 정보를 찾을 수 없음")
                return None
        except Exception as e:
            logger.error(f"[TodoPanel] 페르소나 핸들 가져오기 오류: {e}")
            return None

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

    def _rebuild_from_rows(self, rows: List[dict], show_reasoning: bool = False) -> None:
        """TODO 리스트 재구성
        
        Args:
            rows: TODO 리스트
            show_reasoning: True면 Top3 선정이유 팝업 표시 (기본값: False)
        """
        rows = self._deduplicate_todos(rows)
        if not rows:
            self._set_render_lists([], [], [])
            return

        cloned_rows: List[dict] = []
        for row in rows:
            cloned = dict(row)
            cloned["status"] = (cloned.get("status") or "pending").lower()
            cloned_rows.append(cloned)

        # Top3 계산 (선정이유 팝업 표시 여부 전달)
        top_ids = self.controller.calculate_top3(cloned_rows, show_reasoning=show_reasoning)
        
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

            unread_count = 0
            for idx, todo in enumerate(bucket):
                todo_id = todo.get("id")
                
                # unread 기능 비활성화 - 항상 읽음 상태로 표시
                is_new_todo = False
                unread = False
                
                if unread:
                    unread_count += 1
                
                # 디버깅: 처음 3개 TODO 또는 unread TODO만 로그 출력
                if idx < 3 or unread:
                    logger.info(f"[TodoPanel] 렌더링 TODO #{idx+1}: id={todo_id}, is_new={is_new_todo}, unread={unread}, in_viewed_ids={todo_id in self._viewed_ids if todo_id else 'N/A'}")
                
                # viewed 상태 업데이트
                if not is_new_todo:
                    todo["_viewed"] = True
                
                widget = BasicTodoItem(todo, parent=self, unread=unread)
                widget.mark_done_clicked.connect(self._on_mark_done_clicked)
                item = QListWidgetItem()
                item.setSizeHint(widget.sizeHint())
                item.setData(Qt.ItemDataRole.UserRole, todo)
                self.todo_list.addItem(item)
                self.todo_list.setItemWidget(item, widget)
                if todo_id:
                    self._item_widgets[todo_id] = (item, widget)
            
            if unread_count > 0:
                logger.info(f"[TodoPanel] {label} 섹션: {unread_count}개 unread TODO 발견!")

        if not any_items:
            self.todo_label.setVisible(False)
            self.todo_list.addItem("추가로 처리할 TODO가 없습니다.")
        else:
            self.todo_label.setVisible(True)

    def _match_filters(self, todo: dict) -> bool:
        # 프로젝트 필터 확인
        if not self.controller.match_project(todo):
            return False
        
        # 우선순위 필터 확인
        priority = self.priority_filter.currentData()
        if priority is None:
            priority = "all"
        todo_priority = (todo.get("priority") or "low").lower()
        if priority != "all" and todo_priority != priority:
            return False
        
        # 검색어 필터 확인
        search = self.search_input.text().strip().lower()
        if not search:
            return True
        haystack = " ".join([
            todo.get("title", ""),
            todo.get("description", ""),
            todo.get("requester", ""),
            todo.get("type", ""),
            todo.get("project", ""),  # 프로젝트도 검색 대상에 포함
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
        dlg = TodoDetailDialog(todo, self, llm_client=self.llm_client)
        dlg.exec()

    def show_top3_dialog(self) -> None:
        if not self._top3_cache:
            QMessageBox.information(self, "Top-3", "즉시 처리해야 할 항목이 없습니다.")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("Top-3 즉시 처리 카드")
        layout = QVBoxLayout(dlg)
        
        # 카드 리스트 저장 (나중에 unread 상태 업데이트용)
        cards = []
        
        for todo in self._top3_cache:
            todo_id = todo.get("id")
            already_viewed = todo.get("_viewed") or (todo_id in self._viewed_ids if todo_id else False)
            unread = _is_unread(todo) and not already_viewed
            card = End2EndCard(todo, parent=dlg, unread=unread)
            card.send_clicked.connect(self.on_send_clicked)
            card.hold_clicked.connect(self.on_hold_clicked)
            card.snooze_clicked.connect(self.on_snooze_clicked)
            layout.addWidget(card)
            cards.append((card, todo_id))
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, parent=dlg)
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)
        
        # 다이얼로그가 열리면 모든 카드를 읽음 처리
        def on_dialog_shown():
            for card, todo_id in cards:
                if todo_id:
                    self._viewed_ids.add(todo_id)
                # 1초 후 unread 상태 해제 (사용자가 볼 시간을 줌)
                QTimer.singleShot(1000, lambda c=card: c.set_unread(False))
        
        # 다이얼로그가 표시된 직후 실행
        QTimer.singleShot(100, on_dialog_shown)
        
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
            self.controller.snooze_until(
                payload.get("id"),
                until.isoformat(),
                datetime.now().isoformat(),
            )
            self.refresh_todo_list()
        except Exception as e:
            QMessageBox.critical(self, "스누즈 실패", str(e))

    def _mark_done(self, todo_id) -> None:
        if not todo_id:
            return
        now_iso = datetime.now().isoformat()
        try:
            db_updated = self.controller.mark_done(todo_id, now_iso)
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
    
    def _on_project_filter_changed(self, project_code: str) -> None:
        """프로젝트 필터 변경 이벤트 핸들러"""
        filter_code = project_code if project_code else None
        self.filter_by_project(filter_code)
    
    def filter_by_project(self, project_code: Optional[str]) -> None:
        """프로젝트별 TODO 필터링"""
        try:
            self.controller.set_project_filter(project_code)
            logger.info(f"프로젝트 필터 적용: {project_code or '전체'}")
            self._re_render()
        except Exception as e:
            logger.error(f"프로젝트 필터링 오류: {e}")
    
    def update_project_tags(self, todos: List[dict], force_immediate: bool = False) -> None:
        """프로젝트 태그를 컨트롤러에 위임하고 UI를 갱신한다."""
        todos = todos or []
        logger.info(f"[프로젝트 태그] update_project_tags 호출: {len(todos)}개 TODO")

        if not todos:
            self._update_project_tag_bar_from_todos([])
            return

        # 프로젝트 태그가 없는 TODO들을 비동기 분석 큐에 추가
        todos_without_project = [t for t in todos if not t.get('project')]
        if todos_without_project:
            logger.info(f"[프로젝트 태그] {len(todos_without_project)}개 TODO를 비동기 분석 큐에 추가")
            self.queue_new_todos_for_async_analysis(todos_without_project)

        # 즉시 UI 업데이트 (프로젝트 태그는 백그라운드에서 비동기 처리)
        try:
            self.controller.update_project_tags(todos)
        except Exception as exc:
            logger.error("[프로젝트 태그] 컨트롤러 동기화 실패: %s", exc, exc_info=True)

        try:
            self._update_project_tag_bar_from_todos(todos)
        except Exception as exc:
            logger.error("[프로젝트 태그] 태그 바 업데이트 실패: %s", exc, exc_info=True)
    

    
    def _init_async_project_tag_service(self, project_service):
        """비동기 프로젝트 태그 서비스 초기화"""
        try:
            from src.services.async_project_tag_service import get_async_project_tag_service
            
            self.async_project_service = get_async_project_tag_service(
                project_service, 
                self.controller.repository
            )
            
            if self.async_project_service:
                self.async_project_service.start()
                logger.info("🚀 비동기 프로젝트 태그 서비스 초기화 완료")
            
        except Exception as e:
            logger.warning(f"비동기 프로젝트 태그 서비스 초기화 실패: {e}")
            self.async_project_service = None
    
    def queue_new_todos_for_async_analysis(self, new_todos: List[dict]):
        """새로운 TODO들을 비동기 분석 큐에 추가 (현재 페르소나 우선순위 적용)"""
        if not self.async_project_service or not new_todos:
            return
        
        # 현재 페르소나 정보 가져오기
        current_persona_name = self._get_current_persona_name()
        
        # 프로젝트 태그가 없는 TODO만 필터링
        todos_needing_analysis = [
            todo for todo in new_todos 
            if not todo.get("project") and todo.get("id")
        ]
        
        if todos_needing_analysis:
            logger.info(f"🔄 {len(todos_needing_analysis)}개 새 TODO 비동기 프로젝트 태그 분석 큐에 추가 (현재 페르소나: {current_persona_name})")
            
            def on_project_analyzed(todo_id: str, project: str):
                """프로젝트 태그 분석 완료 콜백"""
                logger.debug(f"[AsyncProjectTag] 분석 완료: {todo_id} → {project}")
                # UI 업데이트는 주기적으로 일괄 처리 (성능 최적화)
                # 개별 TODO마다 refresh하면 성능 저하 발생
            
            # 현재 페르소나의 TODO를 우선순위로 큐에 추가
            priority_todos = []
            normal_todos = []
            
            for todo in todos_needing_analysis:
                todo_persona = todo.get("persona_name")
                # 현재 페르소나의 TODO는 우선순위 높음
                if current_persona_name and todo_persona == current_persona_name:
                    priority_todos.append(todo)
                else:
                    normal_todos.append(todo)
            
            # 우선순위 TODO 먼저 큐에 추가 (priority=True)
            for todo in priority_todos:
                todo_id = todo.get("id")
                if todo_id:
                    self.async_project_service.queue_todo_for_analysis(
                        todo_id, todo, on_project_analyzed, priority=True
                    )
            
            # 일반 TODO 나중에 큐에 추가 (priority=False)
            for todo in normal_todos:
                todo_id = todo.get("id")
                if todo_id:
                    self.async_project_service.queue_todo_for_analysis(
                        todo_id, todo, on_project_analyzed, priority=False
                    )
            
            if priority_todos:
                logger.info(f"⚡ {len(priority_todos)}개 현재 페르소나 TODO 우선 분석 큐에 추가")
            if normal_todos:
                logger.info(f"📋 {len(normal_todos)}개 일반 TODO 분석 큐에 추가")
    
    def get_async_project_tag_stats(self) -> dict:
        """비동기 프로젝트 태그 서비스 통계 반환"""
        if self.async_project_service:
            return self.async_project_service.get_stats()
        return {"error": "서비스 없음"}
    
    def cleanup_async_services(self):
        """비동기 서비스 정리"""
        if hasattr(self, 'async_project_service') and self.async_project_service:
            self.async_project_service.stop()
            logger.info("🛑 비동기 프로젝트 태그 서비스 정리 완료")
    
    def _update_project_tag_bar_from_todos(self, todos: List[dict]) -> None:
        """TODO 목록에서 프로젝트 태그 바 업데이트"""
        try:
            # 현재 TODO들에서 실제 사용 중인 프로젝트 추출
            active_projects = set()
            for todo in todos:
                # project_tag 또는 project 필드 모두 지원 (하위 호환성)
                project = todo.get("project_tag") or todo.get("project")
                if project and project.strip():
                    active_projects.add(project.strip())
            
            # DB에서도 프로젝트 태그 조회 (메모리에 없는 경우 대비)
            try:
                import sqlite3
                db_path = self.repository.db_path if hasattr(self.repository, 'db_path') else None
                if db_path:
                    conn = sqlite3.connect(db_path)
                    cur = conn.cursor()
                    cur.execute("SELECT DISTINCT project_tag FROM todos WHERE project_tag IS NOT NULL AND project_tag != ''")
                    results = cur.fetchall()
                    conn.close()
                    for (project,) in results:
                        if project and project.strip():
                            active_projects.add(project.strip())
                    if active_projects:
                        logger.debug(f"[프로젝트 태그] DB에서 {len(active_projects)}개 프로젝트 조회")
            except Exception as e:
                logger.debug(f"DB에서 프로젝트 조회 오류: {e}")
            
            self._update_project_tag_bar_with_projects(active_projects)
            
        except Exception as e:
            logger.error(f"프로젝트 태그 바 업데이트 오류: {e}")
    
    def _update_project_tag_bar_with_projects(self, active_projects: set) -> None:
        """프로젝트 세트로 프로젝트 태그 바 업데이트"""
        try:
            # 프로젝트 태그 바 업데이트
            if hasattr(self, 'project_tag_bar') and self.project_tag_bar:
                self.project_tag_bar.update_active_projects(active_projects)
                logger.info(f"[프로젝트 태그] 활성 프로젝트 업데이트: {active_projects}")
            elif hasattr(self.parent(), 'project_tag_bar') and self.parent().project_tag_bar:
                self.parent().project_tag_bar.update_active_projects(active_projects)
                logger.info(f"[프로젝트 태그] 부모 활성 프로젝트 업데이트: {active_projects}")
            else:
                # MainWindow에서 프로젝트 태그 바 찾기
                main_window = self._find_main_window()
                if main_window and hasattr(main_window, 'project_tag_bar') and main_window.project_tag_bar:
                    main_window.project_tag_bar.update_active_projects(active_projects)
                    logger.info(f"[프로젝트 태그] 메인윈도우 활성 프로젝트 업데이트: {active_projects}")
                else:
                    logger.warning("[프로젝트 태그] 프로젝트 태그 바를 찾을 수 없음")
                    
        except Exception as e:
            logger.error(f"프로젝트 태그 바 업데이트 오류: {e}")
    
            logger.error(f"프로젝트 태그 바 전용 업데이트 오류: {e}")
    
    def _find_main_window(self):
        """MainWindow 인스턴스 찾기"""
        try:
            parent = self.parent()
            while parent:
                if hasattr(parent, 'project_tag_bar'):
                    return parent
                parent = parent.parent()
            return None
        except Exception:
            return None
    
    def update_cache_status(self, is_cached: bool, cache_time: Optional[datetime] = None) -> None:
        """캐시 상태 표시 업데이트
        
        Args:
            is_cached: 캐시에서 로드되었는지 여부
            cache_time: 캐시 생성 시간 (캐시된 경우)
        """
        try:
            if not hasattr(self, 'cache_status_badge'):
                return
            
            if is_cached and cache_time:
                # 캐시 생성 시간 포맷팅
                from datetime import timezone, timedelta
                kst = timezone(timedelta(hours=9))
                cache_time_kst = cache_time.astimezone(kst)
                time_str = cache_time_kst.strftime("%H:%M:%S")
                
                # 경과 시간 계산
                now = datetime.now(timezone.utc)
                elapsed = now - cache_time
                elapsed_seconds = int(elapsed.total_seconds())
                
                if elapsed_seconds < 60:
                    elapsed_str = f"{elapsed_seconds}초 전"
                elif elapsed_seconds < 3600:
                    elapsed_str = f"{elapsed_seconds // 60}분 전"
                else:
                    elapsed_str = f"{elapsed_seconds // 3600}시간 전"
                
                # 캐시 배지 표시
                self.cache_status_badge.setText(f"💾 캐시됨 ({elapsed_str})")
                self.cache_status_badge.setToolTip(f"캐시 생성 시간: {time_str}\n경과 시간: {elapsed_str}")
                self.cache_status_badge.setStyleSheet("""
                    QLabel {
                        color: #059669;
                        background: #D1FAE5;
                        padding: 4px 10px;
                        border-radius: 12px;
                        font-weight: 600;
                        font-size: 11px;
                    }
                """)
                self.cache_status_badge.setVisible(True)
                logger.info(f"[TodoPanel] 캐시 상태 표시: 캐시됨 ({elapsed_str})")
            else:
                # 새로 분석된 데이터
                now = datetime.now(timezone.utc)
                kst = timezone(timedelta(hours=9))
                now_kst = now.astimezone(kst)
                time_str = now_kst.strftime("%H:%M:%S")
                
                self.cache_status_badge.setText(f"✨ 새로 분석됨 ({time_str})")
                self.cache_status_badge.setToolTip(f"분석 완료 시간: {time_str}")
                self.cache_status_badge.setStyleSheet("""
                    QLabel {
                        color: #1D4ED8;
                        background: #DBEAFE;
                        padding: 4px 10px;
                        border-radius: 12px;
                        font-weight: 600;
                        font-size: 11px;
                    }
                """)
                self.cache_status_badge.setVisible(True)
                logger.info(f"[TodoPanel] 캐시 상태 표시: 새로 분석됨 ({time_str})")
        except Exception as e:
            logger.error(f"[TodoPanel] 캐시 상태 업데이트 오류: {e}")
    
    def hide_cache_status(self) -> None:
        """캐시 상태 배지 숨기기"""
        try:
            if hasattr(self, 'cache_status_badge'):
                self.cache_status_badge.setVisible(False)
        except Exception:
            pass
    
    def _on_manual_refresh(self) -> None:
        """수동 새로고침 버튼 클릭 핸들러
        
        현재 페르소나의 캐시를 무효화하고 재분석을 트리거합니다.
        """
        try:
            logger.info("[TodoPanel] 수동 새로고침 요청")
            
            # MainWindow에 새로고침 요청 전달
            main_window = self._find_main_window()
            if main_window and hasattr(main_window, 'request_manual_refresh'):
                main_window.request_manual_refresh()
                logger.info("[TodoPanel] MainWindow에 새로고침 요청 전달 완료")
            else:
                # MainWindow를 찾을 수 없으면 직접 refresh_todo_list 호출
                logger.warning("[TodoPanel] MainWindow를 찾을 수 없어 직접 새로고침")
                self.refresh_todo_list()
        except Exception as e:
            logger.error(f"[TodoPanel] 수동 새로고침 오류: {e}")
            QMessageBox.warning(self, "새로고침 오류", f"새로고침 중 오류가 발생했습니다:\n{str(e)}")

# 3) TodoDetailDialog: 상세 조회 다이얼로그
# ─────────────────────────────────────────────────────────────────────────────

class TodoDetailDialog(QDialog):
    """TODO 상세 다이얼로그 - 상하 분할 레이아웃"""
    
    def __init__(self, todo: dict, parent=None, llm_client: Optional[LLMClient] = None):
        super().__init__(parent)
        self.todo = todo
        self._llm_client: LLMClient = llm_client or LLMClient()
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
        self.summary_text.setPlaceholderText("'요약 생성' 버튼을 클릭하여 요약을 생성하세요.")
        self.summary_text.setStyleSheet("background:#F9FAFB; border:1px solid #E5E7EB; border-radius:6px; padding:8px;")
        self.summary_text.setMinimumHeight(120)
        
        # 처음에는 빈 상태로 시작 (요약 생성 버튼을 눌러야만 표시)
        self.summary_text.setPlainText("")
        
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
            # Azure OpenAI를 사용하여 요약 생성
            from openai import AzureOpenAI
            import os
            
            client = AzureOpenAI(
                api_key=os.getenv("AZURE_OPENAI_KEY"),
                api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview"),
                azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
            )
            
            prompt = f"""다음 TODO 항목의 내용을 분석하여 JSON 형식으로 요약해주세요.

제목: {self.todo.get("title", "")}
요청자: {self.todo.get("requester", "")}
내용:
{content}

다음 JSON 형식으로 응답해주세요:
{{
  "summary": "전체 요약 (1-2문장)",
  "key_points": ["핵심 포인트 1", "핵심 포인트 2", "핵심 포인트 3"]
}}"""
            
            response = client.chat.completions.create(
                model=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o"),
                messages=[
                    {"role": "system", "content": "당신은 업무 내용을 명확하고 간결하게 요약하는 전문가입니다. 반드시 JSON 형식으로만 응답하세요."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=400,
                temperature=0.5,
                response_format={"type": "json_object"}
            )
            
            result_text = response.choices[0].message.content
            
            # JSON 파싱
            try:
                import json
                result = json.loads(result_text)
                summary_parts = []
                
                # 전체 요약
                if result.get("summary"):
                    summary_parts.append(result["summary"])
                    summary_parts.append("")  # 빈 줄
                
                # 핵심 포인트
                if result.get("key_points"):
                    summary_parts.append("📌 핵심 포인트:")
                    for point in result["key_points"]:
                        summary_parts.append(f"  - {point}")
                
                summary = "\n".join(summary_parts)
            except:
                # JSON 파싱 실패 시 원본 텍스트 사용
                summary = result_text
            
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
            # Azure OpenAI를 사용하여 회신 초안 생성
            from openai import AzureOpenAI
            import os
            
            client = AzureOpenAI(
                api_key=os.getenv("AZURE_OPENAI_KEY"),
                api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview"),
                azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
            )
            
            prompt = f"""다음 메시지에 대한 전문적이고 정중한 회신 초안을 작성해주세요.

원본 메시지:
발신자: {sender}
내용: {content}

회신 초안을 작성해주세요 (한국어로):"""
            
            response = client.chat.completions.create(
                model=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o"),
                messages=[
                    {"role": "system", "content": "당신은 전문적인 비즈니스 이메일 작성 도우미입니다."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            reply = response.choices[0].message.content
            self.reply_text.setPlainText(reply)
        except Exception as e:
            logger.error(f"회신 초안 생성 실패: {e}")
            self.reply_text.setPlainText(f"회신 초안 생성 중 오류가 발생했습니다:\n{str(e)}")
        finally:
            self.generate_reply_btn.setEnabled(True)
            self.generate_reply_btn.setText("✉️ 회신 초안 작성")
    
    def _display_original_content(self):
        """원본 메시지 내용을 요약 영역에 표시 (더 이상 사용하지 않음 - 위쪽에만 표시)"""
        # 이 메서드는 더 이상 사용하지 않습니다.
        # 원본 메시지는 위쪽 "원본 메시지" 섹션에만 표시되고,
        # 아래쪽 "요약 및 액션" 섹션은 요약 생성 버튼을 눌렀을 때만 내용이 표시됩니다.
        pass

