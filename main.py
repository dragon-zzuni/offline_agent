# -*- coding: utf-8 -*-
"""
Smart Assistant 메인 애플리케이션
이메일과 메신저 메시지를 수집하고, LLM으로 분석하여 TODO 리스트를 생성하는 시스템
"""
import asyncio
import logging
import sys
import os
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

# 프로젝트 루트를 Python 경로에 추가 (src/ 포함) — 반드시 내부 모듈 임포트보다 먼저 실행
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from nlp.draft import build_email_draft
from utils.datetime_utils import parse_iso_datetime, is_in_time_range, ensure_utc_aware
from data_sources.manager import DataSourceManager
from data_sources.json_source import JSONDataSource
from data_sources.virtualoffice_source import VirtualOfficeDataSource
from services.analysis_pipeline_service import AnalysisPipelineService
# 로컬 JSON 파일은 더 이상 사용하지 않음 (VDOS DB 사용)
# DEFAULT_DATASET_ROOT = project_root / "data" / "multi_project_8week_ko"
DEFAULT_DATASET_ROOT = None  # VirtualOffice 전용

# # Windows 한글 출력 설정
# import sys
# if hasattr(sys.stdout, "reconfigure"):  # Python 3.7+
#     sys.stdout.reconfigure(encoding="utf-8")
#     sys.stderr.reconfigure(encoding="utf-8")
# # 아니면 아예 아무 것도 안 해도 됨


from nlp.summarize import MessageSummarizer
from nlp.priority_ranker import PriorityRanker
from nlp.action_extractor import ActionExtractor



def _to_aware_iso(ts: str | None) -> str:
    """문자열 타임스탬프를 UTC aware ISO8601로 표준화."""
    if not ts:
        return datetime.now(timezone.utc).isoformat()
    s = ts.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)  # tz 포함/미포함 모두 허용
    except Exception:
        # YYYY-MM-DD HH:MM:SS 같은 포맷 처리
        try:
            dt = datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
        except Exception:
            return datetime.now(timezone.utc).isoformat()

    if dt.tzinfo is None:
        # naive면 UTC로 간주
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        # 타임존 있으면 UTC로 변환
        dt = dt.astimezone(timezone.utc)
    return dt.isoformat()

def _sort_key(msg: dict) -> datetime:
    """날짜 키를 UTC aware datetime으로 반환(정렬용)."""
    try:
        return datetime.fromisoformat(msg["date"])
    except Exception:
        try:
            return datetime.fromisoformat(_to_aware_iso(msg.get("date")))
        except Exception:
            return datetime.min.replace(tzinfo=timezone.utc)

# 로깅 설정 (간단하게)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def coalesce_messages(msgs, window_seconds=90, max_chars=1200):
    out = []
    last = None
    for m in sorted(msgs, key=lambda x: x["date"]):
        if last and (m["platform"] == last["platform"]
                     and m["sender"] == last["sender"]
                     and abs(datetime.fromisoformat(m["date"]) - datetime.fromisoformat(last["date"])) <= timedelta(seconds=window_seconds)):
            # 합치기
            merged = last["content"] + "\n" + (m["content"] or "")
            if len(merged) > max_chars:
                merged = merged[:max_chars] + " ..."
            last["content"] = merged
            last["body"]    = merged
            last["msg_id"] += f"+{m['msg_id']}"
            last["date"]     = m["date"]  # 최신으로
        else:
            mm = dict(m)
            text = mm.get("content") or ""
            if len(text) > max_chars:
                text = text[:max_chars] + " ..."
                mm["content"] = text
                mm["body"]    = text
            out.append(mm)
            last = mm
    return out

def _trim(s: str, n: int) -> str:
    if not s:
        return ""
    s = s.strip()
    return s if len(s) <= n else s[:n] + " ..."

async def build_overall_analysis_text(self, analysis_results: list, max_chars_total: int = 8000) -> str:
    """
    분석 탭에 뿌릴 통합 텍스트 생성:
      - 전체 메시지(제목/내용) 묶어 1회 요약
      - High / Medium / Low 섹션과 구분선
    """
    # 1) 전체 메시지에서 제목/내용 취합
    buffet = []
    acc = 0
    for r in analysis_results:
        msg = r["message"]
        sender = msg.get("sender") or ""
        subj = (msg.get("subject") or msg.get("content") or msg.get("body") or "").strip()
        line = f"{sender}: {subj}"
        if acc + len(line) > max_chars_total:
            break
        buffet.append(line); acc += len(line) + 1
    big_text = "\n".join(buffet)

    # 2) 1회 요약
    ov = await self.summarizer.summarize_message(big_text, sender="multi", subject="전체 메시지 요약")
    overview = ov.summary if hasattr(ov, "summary") else str(ov)

    # 3) 우선순위 섹션
    lines = []
    lines.append("📊 분석 결과 (통합)")
    lines.append("=" * 60)
    lines.append(overview.strip() or "(요약 없음)")
    lines.append("")

    buckets = {"high": [], "medium": [], "low": []}
    for r in analysis_results:
        pr = r["priority"]
        level = (pr.get("priority_level") if isinstance(pr, dict) else getattr(pr, "priority_level", "low")).lower()
        buckets.setdefault(level, []).append(r)
    lines.append(f"High {len(buckets['high'])} · Medium {len(buckets['medium'])} · Low {len(buckets['low'])}")
    lines.append("")

    def _format_record(idx: int, record: Dict) -> list[str]:
        msg = record["message"]
        sender = msg.get("sender") or "알수없음"
        platform = msg.get("platform") or "-"
        when = (msg.get("date") or "")[:16]
        raw = (msg.get("subject") or msg.get("content") or msg.get("body") or "").strip()
        snippet = (raw[:120] + "...") if len(raw) > 120 else raw
        sum_obj = record.get("summary")
        sum_txt = ""
        if isinstance(sum_obj, dict):
            sum_txt = sum_obj.get("summary") or ""
        elif sum_obj is not None:
            sum_txt = getattr(sum_obj, "summary", "") or ""
        sum_txt = sum_txt.strip()
        actions = record.get("actions") or []
        action_line = ""
        if actions:
            samples = []
            for a in actions[:3]:
                if isinstance(a, dict):
                    title = a.get("title") or a.get("description") or a.get("task") or ""
                    if title:
                        samples.append(title[:40] + ("..." if len(title) > 40 else ""))
            if samples:
                action_line = f"   └ 액션({len(actions)}): " + "; ".join(samples)
            else:
                action_line = f"   └ 액션 {len(actions)}건"
        block = [
            f"{idx}. {sender} · {platform} · {when}",
            f"   └ 내용: {snippet}" if snippet else "   └ 내용: (비어 있음)"
        ]
        if sum_txt:
            block.append(f"   └ 요약: {sum_txt}")
        if action_line:
            block.append(action_line)
        return block

    def push_bucket(name: str, items: list[Dict]):
        total = len(items)
        title = name.upper()
        lines.append(f"◆ {title} 우선순위 ({total}건)")
        if not items:
            lines.append("   └ 해당 항목 없음")
            lines.append("")
            return
        for idx, record in enumerate(items[:5], 1):
            lines.extend(_format_record(idx, record))
        if total > 5:
            lines.append(f"   ... 외 {total - 5}건")
        lines.append("")

    push_bucket("high", buckets.get("high", []))
    push_bucket("medium", buckets.get("medium", []))
    push_bucket("low", buckets.get("low", []))

    return "\n".join(lines)



class SmartAssistant:
    """스마트 어시스턴트 메인 클래스
    
    레거시 호환성을 위해 유지되는 클래스입니다.
    내부적으로 AnalysisPipelineService를 사용하여 분석을 수행합니다.
    """
    
    def __init__(self, dataset_root: Optional[Path | str] = None):
        # 로컬 JSON 파일은 더 이상 사용하지 않음 (VDOS 전용)
        self.dataset_root = None  # VirtualOffice 전용

        self.summarizer = MessageSummarizer()
        self.priority_ranker = PriorityRanker()
        self.action_extractor = ActionExtractor()
        
        self.collected_messages: List[Dict[str, Any]] = []
        self.summaries = []
        self.ranked_messages = []
        self.extracted_actions = []

        self.analysis_report_text = ""     # 분석 결과 탭에 뿌릴 통합 리포트 문자열
        self.conversation_summary = None   # 대화 단위 요약(딕셔너리)

        self.personas: List[Dict[str, Any]] = []
        self.persona_by_email: Dict[str, Dict[str, Any]] = {}
        self.persona_by_handle: Dict[str, Dict[str, Any]] = {}
        self.user_profile: Optional[Dict[str, Any]] = None

        self._chat_messages: List[Dict[str, Any]] = []
        self._email_messages: List[Dict[str, Any]] = []
        self._message_index: Dict[str, Dict[str, Any]] = {}
        self._dataset_loaded = False
        self._dataset_last_loaded: Optional[datetime] = None
        
        # DataSourceManager 추가 (VirtualOffice 전용)
        self.data_source_manager = DataSourceManager()
        # JSON 소스는 설정하지 않음 (VirtualOffice만 사용)
        
        # AnalysisPipelineService는 lazy initialization (순환 참조 방지)
        self._pipeline_service = None
        
        # ProjectTagService 초기화 (프로젝트 태그 자동 할당)
        try:
            from services.project_tag_service import ProjectTagService
            self.project_tag_service = ProjectTagService()
            logger.info("✅ ProjectTagService 초기화 완료")
        except Exception as e:
            logger.warning(f"⚠️ ProjectTagService 초기화 실패: {e}")
            self.project_tag_service = None
        
        # Top3Service 초기화
        self.top3_service = None
        self._init_top3_service()

    def _setup_default_json_source(self) -> None:
        """기본 JSON 데이터 소스 설정"""
        # JSON 데이터 소스 생성
        json_source = JSONDataSource(self.dataset_root)
        
        # 데이터 소스 매니저에 등록
        self.data_source_manager.set_source(json_source, "json")
        
        # 페르소나 정보 설정
        self.persona_by_handle = json_source.persona_by_handle
        self.user_profile = json_source.user_profile
        
        logger.info("✅ 기본 JSON 데이터 소스 설정 완료")
    
    def set_dataset_root(self, dataset_root: Path | str) -> None:
        """데이터셋 루트를 변경하고 다음 수집 시 재로드하도록 표시."""
        self.dataset_root = Path(dataset_root)
        self._dataset_loaded = False
        # 데이터 소스도 업데이트
        self._setup_default_json_source()
    
    def set_json_source(self) -> None:
        """JSON 파일 데이터 소스로 전환"""
        self._setup_default_json_source()
        logger.info("✅ JSON 파일 데이터 소스로 전환 완료")
    
    def _init_top3_service(self):
        """Top3Service 초기화"""
        try:
            from services.top3_service import Top3Service
            
            # people 데이터 로드 (이메일 → 이름 매핑용)
            people_data = []
            if hasattr(self, 'personas') and self.personas:
                people_data = self.personas
            
            # Top3Service 초기화
            self.top3_service = Top3Service(
                people_data=people_data
            )
            
            logger.info("✅ Top3Service 초기화 완료")
            
        except Exception as e:
            logger.error(f"❌ Top3Service 초기화 실패: {e}")
            self.top3_service = None
    
    def _ensure_pipeline_service(self):
        """AnalysisPipelineService lazy initialization (순환 참조 방지)"""
        if self._pipeline_service is None:
            self._pipeline_service = AnalysisPipelineService(
                data_source_manager=self.data_source_manager,
                priority_ranker=self.priority_ranker,
                summarizer=self.summarizer,
                action_extractor=self.action_extractor,
                user_profile=self.user_profile,
                top3_service=self.top3_service  # Top3Service 주입
            )
        return self._pipeline_service
    
    def set_virtualoffice_source(self, client, persona: Dict[str, Any]) -> None:
        """VirtualOffice 데이터 소스로 전환
        
        Args:
            client: VirtualOfficeClient 인스턴스
            persona: 선택된 페르소나 정보 딕셔너리 또는 PersonaInfo 객체
        """
        # PersonaInfo 객체인 경우 딕셔너리로 변환
        if hasattr(persona, '__dict__'):
            persona_dict = {
                'name': persona.name,
                'email_address': persona.email_address,
                'chat_handle': persona.chat_handle,
                'role': persona.role,
                'id': persona.id
            }
        else:
            persona_dict = persona
        
        vo_source = VirtualOfficeDataSource(
            client=client,
            selected_persona=persona_dict
        )
        self.data_source_manager.set_source(vo_source, "virtualoffice")
        
        # VirtualOffice 소스에서 로드한 페르소나 정보를 SmartAssistant에 동기화
        self.personas = vo_source.personas
        self.persona_by_email = vo_source.persona_by_email
        self.persona_by_handle = vo_source.persona_by_handle
        self.user_profile = persona_dict  # 선택된 페르소나를 user_profile로 설정
        
        # AnalysisPipelineService에도 user_profile 업데이트 (lazy initialization)
        pipeline = self._ensure_pipeline_service()
        pipeline.set_user_profile(persona_dict)
        
        logger.info(f"✅ VirtualOffice 데이터 소스로 전환 완료 (페르소나: {persona_dict.get('name', 'Unknown')})")

    def _load_json(self, filename: str) -> Any:
        # dataset_root가 None이면 FileNotFoundError 발생
        if self.dataset_root is None:
            raise FileNotFoundError(f"데이터 파일을 찾을 수 없습니다: {filename} (dataset_root가 설정되지 않음)")
        
        path = self.dataset_root / filename
        if not path.exists():
            raise FileNotFoundError(f"데이터 파일을 찾을 수 없습니다: {path}")
        with path.open("r", encoding="utf-8") as fp:
            return json.load(fp)

    def _ensure_dataset(self, force_reload: bool = False) -> None:
        # VirtualOffice 모드일 때는 데이터셋 로드 건너뛰기
        if self.dataset_root is None:
            logger.debug("VirtualOffice 모드: 데이터셋 로드 건너뛰기")
            return
        
        if self._dataset_loaded and not force_reload:
            return
        self._load_dataset()

    def _load_dataset(self) -> None:
        logger.info(f"📂 데이터셋 로드: {self.dataset_root}")

        personas_payload = []
        try:
            personas_payload = self._load_json("team_personas.json")
        except FileNotFoundError as exc:
            logger.warning(str(exc))
        except json.JSONDecodeError as exc:
            logger.error(f"persona JSON 파싱 실패: {exc}")

        if isinstance(personas_payload, list):
            self.personas = personas_payload
        else:
            self.personas = []

        self.persona_by_email = {
            (p.get("email_address") or "").lower(): p
            for p in self.personas
            if p.get("email_address")
        }
        self.persona_by_handle = {
            (p.get("chat_handle") or "").lower(): p
            for p in self.personas
            if p.get("chat_handle")
        }
        self.user_profile = next(
            (p for p in self.personas if (p.get("chat_handle") or "").lower() == "pm"),
            None,
        )

        try:
            chat_payload = self._load_json("chat_communications.json")
        except FileNotFoundError as exc:
            logger.warning(str(exc))
            chat_payload = {}
        except json.JSONDecodeError as exc:
            logger.error(f"chat JSON 파싱 실패: {exc}")
            chat_payload = {}
        self._chat_messages = self._build_chat_messages(chat_payload)

        try:
            email_payload = self._load_json("email_communications.json")
        except FileNotFoundError as exc:
            logger.warning(str(exc))
            email_payload = {}
        except json.JSONDecodeError as exc:
            logger.error(f"email JSON 파싱 실패: {exc}")
            email_payload = {}
        self._email_messages = self._build_email_messages(email_payload)

        self._dataset_loaded = True
        self._dataset_last_loaded = datetime.now(timezone.utc)

    def _build_chat_messages(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        rooms = payload.get("rooms", {}) if isinstance(payload, dict) else {}
        messages: List[Dict[str, Any]] = []
        for room_slug, entries in rooms.items():
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                sender_handle = (entry.get("sender") or "").strip()
                persona = self.persona_by_handle.get(sender_handle.lower())
                sender_name = persona.get("name") if persona else sender_handle
                iso_date = _to_aware_iso(entry.get("sent_at"))
                msg = {
                    "msg_id": f"chat_{room_slug}_{entry.get('id')}",
                    "sender": sender_name or sender_handle or "Unknown",
                    "sender_handle": sender_handle or None,
                    "sender_email": (persona or {}).get("email_address"),
                    "subject": "",
                    "body": entry.get("body") or "",
                    "content": entry.get("body") or "",
                    "date": iso_date,
                    "type": "messenger",
                    "platform": room_slug or "chat",
                    "room_slug": room_slug,
                    "is_read": True,
                    "metadata": {
                        "chat_id": entry.get("id"),
                        "raw_sender": sender_handle,
                        "persona": persona,
                        "room_slug": room_slug,
                    },
                }
                messages.append(msg)
        messages.sort(key=_sort_key)
        return messages

    def _build_email_messages(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        mailboxes = payload.get("mailboxes", {}) if isinstance(payload, dict) else {}
        messages: List[Dict[str, Any]] = []
        for mailbox, entries in mailboxes.items():
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                sender_email = (entry.get("sender") or "").strip()
                persona = self.persona_by_email.get(sender_email.lower())
                sender_display = persona.get("name") if persona else sender_email or "Unknown"
                iso_date = _to_aware_iso(entry.get("sent_at"))
                body = entry.get("body") or ""
                msg = {
                    "msg_id": f"email_{entry.get('id')}_{sender_email or mailbox}",
                    "sender": sender_display,
                    "sender_email": sender_email or None,
                    "sender_handle": (persona or {}).get("chat_handle"),
                    "subject": entry.get("subject") or "",
                    "body": body,
                    "content": body,
                    "date": iso_date,
                    "type": "email",
                    "platform": "email",
                    "mailbox": mailbox,
                    "recipients": entry.get("to") or [],
                    "cc": entry.get("cc") or [],
                    "bcc": entry.get("bcc") or [],
                    "thread_id": entry.get("thread_id"),
                    "is_read": True,
                    "metadata": {
                        "mailbox": mailbox,
                        "email_id": entry.get("id"),
                        "persona": persona,
                    },
                }
                messages.append(msg)
        messages.sort(key=_sort_key)
        return messages

    
    async def initialize(self, dataset_config: Optional[Dict[str, Any]] = None):
        """데이터셋 기반으로 시스템 초기화"""
        logger.info("🚀 Smart Assistant 초기화 중...")
        
        dataset_root = None
        force_reload = False
        if dataset_config:
            dataset_root = (
                dataset_config.get("dataset_root")
                or dataset_config.get("path")
                or dataset_config.get("root")
            )
            force_reload = dataset_config.get("force_reload", False)
        if dataset_root:
            self.set_dataset_root(dataset_root)

        self._ensure_dataset(force_reload=force_reload)
        logger.info("✅ 초기화 완료 (오프라인 데이터셋)")

        
    async def collect_messages(
        self,
        email_limit: Optional[int] = None,
        messenger_limit: Optional[int] = None,
        json_limit: Optional[int] = None,
        _rooms=None,
        _include_system: bool = False,
        overall_limit: Optional[int] = None,
        force_reload: bool = False,
        time_range: Optional[Dict[str, Any]] = None,
    ):
        """데이터 소스에서 메시지를 수집한 뒤 공통 포맷으로 반환
        
        DataSourceManager를 통해 현재 설정된 데이터 소스(JSON 또는 VirtualOffice)에서
        메시지를 수집합니다. 기존 인터페이스를 유지하면서 데이터 소스 추상화를 제공합니다.
        
        Args:
            email_limit: 이메일 최대 개수
            messenger_limit: 메신저 최대 개수
            json_limit: JSON 최대 개수 (하위 호환)
            _rooms: 룸 필터 (사용 안 함)
            _include_system: 시스템 메시지 포함 여부
            overall_limit: 전체 메시지 최대 개수
            force_reload: 강제 리로드 여부
            time_range: 시간 범위 필터 {"start": datetime, "end": datetime}
        """
        logger.info(f"📥 메시지 수집 시작 (소스: {self.data_source_manager.source_type})")
        
        # 데이터셋 로드 (JSON 소스인 경우에만 필요)
        if self.data_source_manager.source_type == "json":
            self._ensure_dataset(force_reload=force_reload)
        
        # DataSourceManager를 통해 메시지 수집
        collect_options = {
            "email_limit": email_limit,
            "messenger_limit": messenger_limit or json_limit,  # 하위 호환
            "overall_limit": overall_limit,
            "time_range": time_range,
            "force_reload": force_reload,
        }
        
        messages = await self.data_source_manager.collect_messages(collect_options)
        
        # 기존 인터페이스 호환성을 위해 chat/email 분리
        chat_messages = [m for m in messages if m.get("type") == "messenger"]
        email_messages = [m for m in messages if m.get("type") == "email"]
        
        # 메시지 병합 (연속된 메시지 합치기)
        # 주의: coalesce_messages는 미리보기용으로만 사용하고, 원본 메시지는 _message_index에 저장
        merged = coalesce_messages(messages, window_seconds=90, max_chars=1200)
        merged.sort(key=_sort_key, reverse=True)

        self.collected_messages = merged
        # 원본 메시지 전체 내용 보존을 위한 인덱스 (병합 전 원본 메시지 사용)
        self._message_index = {
            msg.get("msg_id"): msg for msg in messages if msg.get("msg_id")
        }
        # 병합된 메시지도 인덱스에 추가 (msg_id가 여러 개인 경우 대비)
        for msg in merged:
            msg_id = msg.get("msg_id")
            if msg_id and msg_id not in self._message_index:
                self._message_index[msg_id] = msg
        logger.info(
            "📦 총 %d개 메시지 수집 (chat %d, email %d)",
            len(self.collected_messages),
            len(chat_messages),
            len(email_messages),
        )
        return self.collected_messages

    async def analyze_messages(self):
        """메시지 분석 (레거시 호환성 유지)
        
        내부적으로 AnalysisPipelineService를 사용하여 분석을 수행합니다.
        기존 API를 유지하면서 서비스로 위임합니다.
        """
        if not self.collected_messages:
            logger.warning("분석할 메시지가 없습니다.")
            return []

        # 수집된 메시지 타입 분석
        email_count = len([m for m in self.collected_messages if m.get("type") == "email" or m.get("platform") == "email"])
        message_count = len([m for m in self.collected_messages if m.get("type") == "messenger" or m.get("platform") == "messenger"])
        other_count = len(self.collected_messages) - email_count - message_count
        logger.info(f"🔍 분석 대상 메시지: 이메일 {email_count}개, 메신저 {message_count}개, 기타 {other_count}개 (총 {len(self.collected_messages)}개)")

        logger.info("🔍 메시지 분석 시작...")

        # 0) TO/CC/BCC 중복 제거 (같은 이메일을 TO, CC, BCC로 받았을 때 TO만 유지)
        logger.info("🔄 TO/CC/BCC 중복 제거 중...")
        email_groups = {}  # (sender, subject, timestamp) -> [messages]
        
        for msg in self.collected_messages:
            if msg.get("platform") == "email" or msg.get("type") == "email":
                sender = msg.get("sender", "")
                subject = msg.get("subject", "")
                timestamp = msg.get("date") or msg.get("timestamp") or msg.get("datetime") or ""
                
                # 같은 발신자, 제목, 시간의 이메일을 그룹화
                key = (sender, subject, timestamp)
                if key not in email_groups:
                    email_groups[key] = []
                email_groups[key].append(msg)
        
        # TO > CC > BCC 우선순위로 중복 제거
        deduplicated_messages = []
        to_cc_bcc_removed = 0
        
        for key, msgs in email_groups.items():
            if len(msgs) == 1:
                deduplicated_messages.extend(msgs)
            else:
                # TO, CC, BCC로 분류
                to_msgs = [m for m in msgs if m.get("recipient_type", "to").lower() == "to"]
                cc_msgs = [m for m in msgs if m.get("recipient_type", "").lower() == "cc"]
                bcc_msgs = [m for m in msgs if m.get("recipient_type", "").lower() == "bcc"]
                
                # TO가 있으면 TO만, 없으면 CC, 그것도 없으면 BCC
                if to_msgs:
                    deduplicated_messages.extend(to_msgs)
                    to_cc_bcc_removed += len(cc_msgs) + len(bcc_msgs)
                    if len(msgs) > 1:
                        sender, subject, _ = key
                        logger.debug(f"TO/CC/BCC 중복: {sender} - {subject[:30]} (TO {len(to_msgs)}개 유지, CC {len(cc_msgs)}개 + BCC {len(bcc_msgs)}개 제거)")
                elif cc_msgs:
                    deduplicated_messages.extend(cc_msgs)
                    to_cc_bcc_removed += len(bcc_msgs)
                else:
                    deduplicated_messages.extend(bcc_msgs)
        
        # 메신저 메시지는 그대로 추가
        for msg in self.collected_messages:
            if msg.get("platform") != "email" and msg.get("type") != "email":
                deduplicated_messages.append(msg)
        
        if to_cc_bcc_removed > 0:
            logger.info(f"🔄 TO/CC/BCC 중복 제거: {to_cc_bcc_removed}개 제거 ({len(self.collected_messages)}개 → {len(deduplicated_messages)}개)")
        
        # 중복 제거된 메시지로 교체
        self.collected_messages = deduplicated_messages

        # 1) 우선순위 분류
        logger.info("🎯 우선순위 분류 중...")
        self.ranked_messages = await self.priority_ranker.rank_messages(self.collected_messages)

        # 2단계 TODO 생성 전략 (개선):
        # 1단계: 키워드 기반으로 임시 TODO 생성 (빠름, 제한 없음)
        # 2단계: 생성된 모든 임시 TODO의 원본 메시지를 LLM으로 분석
        # 3단계: LLM이 action_required=true로 판단한 것만 최종 TODO로
        
        # 1) 키워드 기반 임시 TODO 생성 (제한 없음)
        logger.info("⚡ 1단계: 키워드 기반 임시 TODO 생성 중...")
        logger.info("   → 모든 메시지에서 키워드 패턴으로 TODO 후보 추출 (빠르지만 정확도 낮음)")
        user_email = (self.user_profile or {}).get("email_address", "pm.1@quickchat.dev")
        all_messages = [m for (m, _) in self.ranked_messages]
        
        # 1-1) 사전 필터링: 너무 짧거나 단순 인사 메시지 제외
        filtered_messages = []
        too_short_count = 0
        greeting_count = 0
        simple_update_count = 0
        
        # 단순 인사 패턴
        greeting_only_patterns = [
            "안녕하세요", "안녕하십니까", "수고하세요", "수고하십시오", "감사합니다", "고맙습니다",
            "hello", "hi there", "good morning", "good afternoon", "good evening",
            "좋은 하루 되세요", "좋은 하루", "화이팅", "파이팅"
        ]
        
        # 간단 업데이트 패턴 (의미 없는 상태 공유) - 제목이나 내용에 포함
        simple_update_patterns = [
            "간단 업데이트", "업무 공유", "현재 작업 상황", "작업 상황 공유", "오늘의 일정",
            "현재 집중 작업", "작업자:", "업데이트:", "진행 상황", "상황 공유",
            "simple update", "status update", "quick update", "daily update", "work update"
        ]
        
        for msg in all_messages:
            content = (msg.get("content") or msg.get("body") or "").strip()
            subject = (msg.get("subject") or "").strip()
            combined = f"{subject} {content}".lower()
            
            # 너무 짧은 메시지 (15자 미만)
            if len(content) < 15:
                too_short_count += 1
                continue
            
            # 단순 인사만 있는 메시지 (40자 미만)
            if len(content) < 40:
                content_clean = content.lower().strip().replace("!", "").replace(".", "").replace("~", "").replace(",", "").strip()
                is_greeting_only = any(pattern in content_clean for pattern in [p.lower() for p in greeting_only_patterns])
                
                # 구체적인 내용이 없으면 제외
                if is_greeting_only:
                    greeting_count += 1
                    logger.debug(f"[1차 필터링] 단순 인사 제외: {content[:30]}")
                    continue
            
            # 간단 업데이트 메시지 (200자 미만이면서 간단 업데이트 패턴 포함하고 액션 키워드 없음)
            if len(content) < 200:
                has_simple_update = any(pattern in combined for pattern in simple_update_patterns)
                
                if has_simple_update:
                    # 구체적인 액션 키워드가 있는지 확인
                    action_keywords = [
                        "요청", "부탁", "확인해", "검토해", "제출", "보고서", "회의", "미팅", "마감", "완료해",
                        "필요", "해주", "드립니다", "바랍니다",
                        "request", "please", "check", "review", "submit", "report", "meeting", "deadline", "need"
                    ]
                    has_action = any(keyword in combined for keyword in action_keywords)
                    
                    if not has_action:
                        simple_update_count += 1
                        logger.debug(f"[1차 필터링] 간단 업데이트 제외: {subject[:30]} - {content[:50]}")
                        continue
            
            filtered_messages.append(msg)
        
        if too_short_count > 0 or greeting_count > 0 or simple_update_count > 0:
            logger.info(f"🔍 1차 필터링: 짧은 메시지 {too_short_count}개, 단순 인사 {greeting_count}개, 간단 업데이트 {simple_update_count}개 제외")
            logger.info(f"   → {len(all_messages)}개 → {len(filtered_messages)}개 메시지로 TODO 후보 추출")
        
        # 모든 메시지에서 키워드 기반 액션 추출
        temp_actions = await self.action_extractor.batch_extract_actions(
            filtered_messages,
            user_email=user_email,
        )
        logger.info(f"⚡ 1단계 완료: 키워드 기반 임시 TODO {len(temp_actions)}개 생성")
        
        # 1-0) 생성된 TODO 중 의미 없는 것만 필터링 (제목 길이는 상관없음)
        filtered_actions = []
        meaningless_count = 0
        
        for action in temp_actions:
            description = (action.description if hasattr(action, 'description') else action.get('description', '')).strip()
            
            # description이 비어있거나 너무 짧으면 (10자 미만) 제외
            if len(description) < 10:
                meaningless_count += 1
                title = (action.title if hasattr(action, 'title') else action.get('title', ''))
                logger.debug(f"[TODO 필터링] description 너무 짧음: {title[:50]}")
                continue
            
            # 통과한 TODO 추가
            filtered_actions.append(action)
        
        if meaningless_count > 0:
            logger.info(f"🔍 TODO 필터링: 의미 없음 {meaningless_count}개 제외 ({len(temp_actions)}개 → {len(filtered_actions)}개)")
        
        temp_actions = filtered_actions
        
        # 1-1) 임시 TODO 중복 제거 (내용 기반, 90% 이상 유사도)
        if temp_actions:
            def _calculate_similarity(text1: str, text2: str) -> float:
                """두 텍스트의 유사도 계산 (0.0 ~ 1.0)"""
                if not text1 or not text2:
                    return 0.0
                
                # 간단한 단어 기반 유사도 (Jaccard similarity)
                words1 = set(text1.lower().split())
                words2 = set(text2.lower().split())
                
                if not words1 or not words2:
                    return 0.0
                
                intersection = words1 & words2
                union = words1 | words2
                
                return len(intersection) / len(union) if union else 0.0
            
            # 같은 source_message_id로 그룹화
            from collections import defaultdict
            message_groups = defaultdict(list)
            for action in temp_actions:
                msg_id = action.source_message_id if hasattr(action, 'source_message_id') else None
                if msg_id:
                    message_groups[msg_id].append(action)
            
            # 각 그룹에서 중복 제거
            filtered_actions = []
            duplicate_count = 0
            
            for msg_id, actions in message_groups.items():
                if len(actions) == 1:
                    # 그룹에 액션이 1개면 그대로 추가
                    filtered_actions.extend(actions)
                else:
                    # 여러 개면 내용 유사도 기반 중복 제거 (90% 이상)
                    kept_actions = []
                    
                    for action in actions:
                        is_duplicate = False
                        action_desc = action.description if hasattr(action, 'description') else ""
                        
                        # 이미 유지하기로 한 액션들과 비교
                        for kept in kept_actions:
                            kept_desc = kept.description if hasattr(kept, 'description') else ""
                            similarity = _calculate_similarity(action_desc, kept_desc)
                            
                            # 유사도 90% 이상이면 중복으로 간주
                            if similarity >= 0.9:
                                is_duplicate = True
                                # 유형 우선순위: meeting > deadline > review > task > response
                                type_priority = {
                                    "meeting": 5,
                                    "deadline": 4,
                                    "review": 3,
                                    "task": 2,
                                    "response": 1
                                }
                                
                                current_type = action.action_type if hasattr(action, 'action_type') else ""
                                kept_type = kept.action_type if hasattr(kept, 'action_type') else ""
                                
                                current_type_priority = type_priority.get(current_type, 0)
                                kept_type_priority = type_priority.get(kept_type, 0)
                                
                                # 현재 액션이 더 높은 우선순위 유형이면 교체
                                if current_type_priority > kept_type_priority:
                                    kept_actions.remove(kept)
                                    kept_actions.append(action)
                                    logger.debug(f"[임시TODO 중복제거] {kept_type} → {current_type} 교체 (유사도: {similarity:.2f})")
                                else:
                                    logger.debug(f"[임시TODO 중복제거] {current_type} 제거 (유사도: {similarity:.2f}, 유지: {kept_type})")
                                
                                duplicate_count += 1
                                break
                        
                        if not is_duplicate:
                            kept_actions.append(action)
                    
                    filtered_actions.extend(kept_actions)
            
            # 메시지 ID가 없는 액션들도 추가
            for action in temp_actions:
                msg_id = action.source_message_id if hasattr(action, 'source_message_id') else None
                if not msg_id:
                    filtered_actions.append(action)
            
            if duplicate_count > 0:
                logger.info(f"🔄 임시 TODO 중복 제거: {duplicate_count}개 제거 ({len(temp_actions)}개 → {len(filtered_actions)}개)")
            
            temp_actions = filtered_actions
        
        # 2) 임시 TODO가 생성된 메시지만 LLM 분석
        # 임시 TODO의 source_message_id로 원본 메시지 찾기
        temp_action_msg_ids = set()
        for action in temp_actions:
            # ActionItem은 dataclass이므로 속성으로 접근
            msg_id = action.source_message_id if hasattr(action, 'source_message_id') else None
            if msg_id:
                temp_action_msg_ids.add(msg_id)
        
        # 원본 메시지 찾기
        msg_by_id = {m.get("msg_id"): m for m in all_messages}
        all_messages_to_analyze = [msg_by_id[msg_id] for msg_id in temp_action_msg_ids if msg_id in msg_by_id]
        
        # 정보 공유 필터링 제거: 모든 메시지를 LLM이 판단하도록 변경
        # - 배치 처리 + Rate Limit 회피가 구현되어 있음
        # - LLM이 action_required를 정확하게 판단
        logger.info(f"📝 {len(all_messages_to_analyze)}개 메시지 LLM 분석 준비 (필터링 없음)")
        
        # Rate Limit 방지: 배치로 나누어 분석
        BATCH_SIZE = 50  # 배치당 메시지 수 (50개씩)
        
        # 우선순위가 높은 메시지 우선 (ranked_messages 순서 활용)
        # 전체 메시지를 우선순위 순으로 정렬
        ranked_msg_ids = [m.get("msg_id") for m, _ in self.ranked_messages]
        messages_to_analyze = []
        
        # 우선순위 순서대로 추가
        for msg_id in ranked_msg_ids:
            msg = next((m for m in all_messages_to_analyze if m.get("msg_id") == msg_id), None)
            if msg:
                messages_to_analyze.append(msg)
        
        # ranked_messages에 없는 메시지도 추가
        for msg in all_messages_to_analyze:
            if msg not in messages_to_analyze:
                messages_to_analyze.append(msg)
        
        total_to_analyze = len(messages_to_analyze)
        logger.info(f"📝 2단계: LLM으로 {total_to_analyze}개 메시지 배치 분석 시작...")
        logger.info(f"   → 임시 TODO가 생성된 {len(temp_action_msg_ids)}개 메시지 중 {total_to_analyze}개 분석 (배치 크기: {BATCH_SIZE}개)")
        
        # 배치로 나누어 분석 + 배치별 TODO 저장
        all_summaries = []
        num_batches = (total_to_analyze + BATCH_SIZE - 1) // BATCH_SIZE
        
        for batch_idx in range(num_batches):
            start_idx = batch_idx * BATCH_SIZE
            end_idx = min(start_idx + BATCH_SIZE, total_to_analyze)
            batch_messages = messages_to_analyze[start_idx:end_idx]
            
            logger.info(f"   📦 배치 {batch_idx + 1}/{num_batches}: {len(batch_messages)}개 메시지 분석 중...")
            
            # 배치 분석
            batch_summaries = await self.summarizer.batch_summarize(batch_messages)
            all_summaries.extend(batch_summaries)
            
            logger.info(f"   ✅ 배치 {batch_idx + 1}/{num_batches} 완료 (누적: {len(all_summaries)}/{total_to_analyze}개)")
            
            # 배치별 TODO 생성 및 저장 (UI 즉시 업데이트)
            try:
                # 현재 배치의 summary를 msg_id로 매핑
                batch_summary_by_id = {}
                for m, s in zip(batch_messages, batch_summaries):
                    if s and not getattr(s, "original_id", None):
                        s.original_id = m.get("msg_id")
                    batch_summary_by_id[m["msg_id"]] = s
                
                # 현재 배치의 액션만 필터링
                batch_filtered_actions = []
                for action in temp_actions:
                    msg_id = action.source_message_id if hasattr(action, 'source_message_id') else None
                    if msg_id in batch_summary_by_id:
                        summary = batch_summary_by_id[msg_id]
                        if summary and hasattr(summary, "action_required") and summary.action_required:
                            batch_filtered_actions.append(action)
                
                # 배치 TODO 생성
                if batch_filtered_actions:
                    batch_todos = []
                    persona_name = self.user_profile.get('name') if hasattr(self, 'user_profile') and self.user_profile else None
                    
                    for action in batch_filtered_actions:
                        msg_id = action.source_message_id if hasattr(action, 'source_message_id') else None
                        # 전체 메시지 리스트에서 찾기 (배치에 없을 수도 있음)
                        message = msg_by_id.get(msg_id) if msg_id else None
                        if message:
                            # TODO 아이템 생성
                            recipient_type = message.get("recipient_type", "to")
                            platform = message.get("platform", "")
                            source_type = "메일" if platform == "email" else "메시지"
                            
                            # 원본 메시지에서 전체 내용 가져오기
                            original_content = message.get("content") or message.get("body") or ""
                            original_subject = message.get("subject") or ""
                            
                            todo_item = {
                                "id": action.action_id if hasattr(action, 'action_id') else action.get("action_id"),
                                "title": action.title if hasattr(action, 'title') else action.get("title"),
                                "description": action.description if hasattr(action, 'description') else action.get("description"),
                                "priority": action.priority if hasattr(action, 'priority') else action.get("priority", "medium"),
                                "deadline": action.deadline if hasattr(action, 'deadline') else action.get("deadline"),
                                "requester": (action.requester if hasattr(action, 'requester') else action.get("requester")) or message.get("sender"),
                                "type": action.action_type if hasattr(action, 'action_type') else action.get("action_type"),
                                "status": "pending",
                                "recipient_type": recipient_type,
                                "source_type": source_type,
                                "persona_name": persona_name,
                                "source_message": {
                                    "id": message.get("msg_id"),
                                    "sender": message.get("sender"),
                                    "subject": original_subject,
                                    "content": original_content,  # 전체 내용 포함
                                    "body": original_content,     # body도 포함 (호환성)
                                    "platform": message.get("platform"),
                                    "recipient_type": recipient_type,
                                    "is_read": True,
                                    "date": message.get("date") or message.get("timestamp") or message.get("sent_at"),
                                },
                                "created_at": action.created_at if hasattr(action, 'created_at') else action.get("created_at"),
                                "_viewed": False,
                            }
                            batch_todos.append(todo_item)
                    
                    # DB에 저장 (직접 SQLite 사용)
                    if batch_todos:
                        import sqlite3
                        from pathlib import Path
                        
                        # TODO DB 경로 (virtualoffice/src/virtualoffice/todos_cache.db)
                        project_root = Path(__file__).parent
                        db_path = project_root.parent / "virtualoffice" / "src" / "virtualoffice" / "todos_cache.db"
                        
                        conn = sqlite3.connect(str(db_path))
                        cur = conn.cursor()
                        
                        for todo in batch_todos:
                            cur.execute("""
                                INSERT OR REPLACE INTO todos (
                                    id, title, description, priority, deadline, deadline_ts,
                                    requester, type, status, source_message, created_at, updated_at,
                                    snooze_until, is_top3, evidence, deadline_confidence,
                                    recipient_type, source_type, persona_name, project_tag, draft_subject, draft_body
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                todo.get("id"),
                                todo.get("title"),
                                todo.get("description"),
                                todo.get("priority"),
                                todo.get("deadline"),
                                None,  # deadline_ts
                                todo.get("requester"),
                                todo.get("type"),
                                todo.get("status", "pending"),
                                json.dumps(todo.get("source_message"), ensure_ascii=False) if todo.get("source_message") else None,
                                todo.get("created_at") or datetime.now(timezone.utc).isoformat(),
                                datetime.now(timezone.utc).isoformat(),
                                None,  # snooze_until
                                0,  # is_top3
                                todo.get("evidence"),
                                todo.get("deadline_confidence"),
                                todo.get("recipient_type"),
                                todo.get("source_type"),
                                todo.get("persona_name"),
                                todo.get("project"),
                                todo.get("draft_subject"),
                                todo.get("draft_body")
                            ))
                        
                        conn.commit()
                        conn.close()
                        logger.info(f"   💾 배치 {batch_idx + 1}/{num_batches}: {len(batch_todos)}개 TODO 저장 완료 → UI 업데이트 가능")
            except Exception as e:
                logger.error(f"   ❌ 배치 {batch_idx + 1} TODO 저장 실패: {e}", exc_info=True)
        
        self.summaries = all_summaries
        logger.info(f"✅ 전체 LLM 분석 완료: {len(self.summaries)}개 메시지")
        
        # msg_id → summary 맵
        summary_by_id = {}
        for m, s in zip(messages_to_analyze, self.summaries):
            if s and not getattr(s, "original_id", None):
                s.original_id = m.get("msg_id")
            summary_by_id[m["msg_id"]] = s
        
        # 3) LLM이 action_required=true로 판단한 메시지의 액션만 유지
        filtered_actions = []
        filtered_out_count = 0
        
        for action in temp_actions:
            # ActionItem은 dataclass이므로 속성으로 접근
            msg_id = action.source_message_id if hasattr(action, 'source_message_id') else None
            summary = summary_by_id.get(msg_id)
            
            if summary and hasattr(summary, "action_required"):
                if summary.action_required:
                    filtered_actions.append(action)
                else:
                    filtered_out_count += 1
                    action_title = action.title if hasattr(action, 'title') else 'Unknown'
                    logger.debug(f"LLM 필터링: {action_title} (action_required=false)")
            else:
                # LLM 분석 실패 시 키워드 기반 결과 유지
                filtered_actions.append(action)
        
        logger.info(f"✅ 3단계: LLM 필터링 완료")
        logger.info(f"   → 키워드 기반 {len(temp_actions)}개 → LLM 검증 후 {len(filtered_actions)}개 최종 선정 ({filtered_out_count}개 제외)")
        logger.info(f"   → LLM 미분석 메시지의 TODO는 키워드 기반 결과 유지 ({len(temp_action_msg_ids) - len(messages_to_analyze)}개 메시지)")
        self.extracted_actions = filtered_actions

        # filtered_actions를 사용해야 함 (LLM 필터링 후)
        actions_by_id = {}
        for a in filtered_actions:  # actions가 아니라 filtered_actions 사용
            src = getattr(a, "source_message_id", None) or (a.get("source_message_id") if isinstance(a, dict) else None)
            if not src:
                continue
            actions_by_id.setdefault(src, []).append(a)

        logger.info(f"🔍 [DEBUG] actions_by_id 생성: {len(actions_by_id)}개 메시지에 액션 있음")

        # 4) 결과 병합 (전체 랭킹 순서 보존)
        results = []
        for message, priority in self.ranked_messages:
            mid = message["msg_id"]
            s   = summary_by_id.get(mid)
            pr  = priority.to_dict() if hasattr(priority, "to_dict") else priority
            acts = [x.to_dict() if hasattr(x, "to_dict") else x for x in actions_by_id.get(mid, [])]
            results.append({
                "message": message,
                "summary": (s.to_dict() if hasattr(s, "to_dict") else (s.__dict__ if s else None)),
                "priority": pr,
                "actions": acts,
                "analysis_timestamp": datetime.now().isoformat()
            })

        # 5) 전체 메시지 요약 (성능 개선: 메시지가 많을 경우 스킵)
        conv_text = ""
        self.conversation_summary = None
        
        # 메시지가 50개 이하일 때만 전체 대화 요약 수행
        if len(self.collected_messages) <= 50:
            try:
                all_msgs = sorted(self.collected_messages, key=_sort_key)
                if all_msgs:
                    conv = await self.summarizer.summarize_conversation(all_msgs)
                    summary_line = ""
                    if isinstance(conv, dict):
                        self.conversation_summary = conv
                        summary_line = conv.get("summary", "") or ""
                    elif hasattr(conv, "summary"):
                        summary_line = getattr(conv, "summary", "") or ""
                        maybe_dict = getattr(conv, "__dict__", None)
                        if isinstance(maybe_dict, dict):
                            self.conversation_summary = maybe_dict
                    elif isinstance(conv, str):
                        summary_line = conv
                    summary_line = (summary_line or "").strip()
                    if summary_line:
                        conv_text = "■ 대화 흐름 요약\n" + ("═" * 60) + f"\n{summary_line}"
            except Exception as e:
                logger.warning(f"대화 요약 실패: {e}")
        else:
            logger.info(f"메시지가 {len(self.collected_messages)}개로 많아 전체 대화 요약을 스킵합니다.")


        # 6) 분석 결과 탭 텍스트 생성 (우선순위 섹션 포함)
        sections_text = await build_overall_analysis_text(self, results)
        self.analysis_report_text = sections_text


        logger.info(f"🔍 {len(results)}개 메시지 분석 완료")
        return results

        
    async def generate_todo_list(self, analysis_results: List[Dict]) -> Dict:
        """TODO 리스트 생성"""
        logger.info("📋 TODO 리스트 생성 중...")
        logger.info(f"🔍 [DEBUG] analysis_results 개수: {len(analysis_results or [])}")

        # 1단계: TO/CC/BCC 중복 제거 (같은 이메일을 TO, CC, BCC로 받았을 때 TO만 유지)
        email_groups = {}  # email_id -> [results]
        for result in analysis_results or []:
            message = result.get("message", {})
            if message.get("platform") == "email":
                # 이메일의 고유 ID (thread_id나 subject+sender 조합)
                email_id = message.get("thread_id") or f"{message.get('subject')}_{message.get('sender')}"
                if email_id:
                    if email_id not in email_groups:
                        email_groups[email_id] = []
                    email_groups[email_id].append(result)
        
        # TO > CC > BCC 우선순위로 중복 제거
        filtered_results = []
        to_cc_bcc_removed = 0
        
        for email_id, results in email_groups.items():
            if len(results) == 1:
                filtered_results.extend(results)
            else:
                # TO, CC, BCC로 분류
                to_results = [r for r in results if r.get("message", {}).get("recipient_type", "to").lower() == "to"]
                cc_results = [r for r in results if r.get("message", {}).get("recipient_type", "").lower() == "cc"]
                bcc_results = [r for r in results if r.get("message", {}).get("recipient_type", "").lower() == "bcc"]
                
                # TO가 있으면 TO만, 없으면 CC, 그것도 없으면 BCC
                if to_results:
                    filtered_results.extend(to_results)
                    to_cc_bcc_removed += len(cc_results) + len(bcc_results)
                    if cc_results or bcc_results:
                        logger.debug(f"TO/CC/BCC 중복 제거: {email_id[:50]} - TO {len(to_results)}개 유지, CC {len(cc_results)}개 + BCC {len(bcc_results)}개 제거")
                elif cc_results:
                    filtered_results.extend(cc_results)
                    to_cc_bcc_removed += len(bcc_results)
                else:
                    filtered_results.extend(bcc_results)
        
        # 메신저 메시지는 그대로 추가
        for result in analysis_results or []:
            message = result.get("message", {})
            if message.get("platform") != "email":
                filtered_results.append(result)
        
        if to_cc_bcc_removed > 0:
            logger.info(f"🔄 TO/CC/BCC 중복 제거: {to_cc_bcc_removed}개 제거 ({len(analysis_results)}개 → {len(filtered_results)}개)")
        
        # 필터링된 결과로 교체
        analysis_results = filtered_results

        todo_items: List[Dict] = []
        high_priority_count = 0
        medium_priority_count = 0
        low_priority_count = 0

        # 우선순위 문자열 → 숫자 맵 (정렬용)
        priority_value = {"high": 3, "medium": 2, "low": 1}

        def _parse_deadline(d: str | None) -> datetime:
            if not d:
                return datetime.max.replace(tzinfo=timezone.utc)
            try:
                raw = datetime.fromisoformat(d.replace("Z", "+00:00")) if "Z" in d else datetime.fromisoformat(d)
                if raw.tzinfo is None:
                    return raw.replace(tzinfo=timezone.utc)
                return raw.astimezone(timezone.utc)
            except Exception:
                return datetime.max.replace(tzinfo=timezone.utc)

        total_actions = 0
        for result in analysis_results or []:
            actions_count = len(result.get('actions', []))
            total_actions += actions_count
            if actions_count > 0:
                logger.debug(f"🔍 [DEBUG] result actions: {actions_count}")
            pr = (result.get("priority") or {})
            priority_level = pr.get("priority_level", "low")

            # 우선순위 카운팅
            if priority_level == "high":
                high_priority_count += 1
            elif priority_level == "medium":
                medium_priority_count += 1
            else:
                low_priority_count += 1

            # 액션들을 TODO 아이템으로 변환
            for action in result.get("actions", []):
                # 원본 메시지에서 recipient_type 가져오기
                source_msg = result.get("message") or {}
                msg_id = (
                    source_msg.get("msg_id")
                    or source_msg.get("id")
                    or (source_msg.get("message_id") if isinstance(source_msg.get("message_id"), str) else None)
                )
                original_msg = None
                if msg_id:
                    original_msg = self._message_index.get(msg_id)
                    if not original_msg:
                        # 안전망: message_index가 비어있을 때 기존 리스트에서 검색
                        original_msg = next(
                            (m for m in self.collected_messages if m.get("msg_id") == msg_id),
                            None,
                        )
                if not original_msg:
                    original_msg = source_msg
                recipient_type = source_msg.get("recipient_type", "to")
                platform = source_msg.get("platform", "")
                
                # 소스 타입 결정 (메일/메시지)
                source_type = "메일" if platform == "email" else "메시지"
                
                persona_name = None
                if hasattr(self, 'user_profile') and self.user_profile:
                    persona_name = self.user_profile.get('name')

                source_metadata = (
                    original_msg.get("metadata")
                    or source_msg.get("metadata")
                    or {}
                )
                date_candidates = [
                    original_msg.get("date"),
                    source_metadata.get("original_date"),
                    original_msg.get("timestamp"),
                    original_msg.get("sent_at"),
                    original_msg.get("created_at"),
                    source_msg.get("date"),
                    source_msg.get("timestamp"),
                    source_msg.get("sent_at"),
                    source_msg.get("created_at"),
                ]
                received_time = next((value for value in date_candidates if value), None)
                simulated_time = (
                    original_msg.get("simulated_datetime")
                    or source_metadata.get("simulated_datetime")
                    or source_msg.get("simulated_datetime")
                    or source_metadata.get("simulated_datetime")
                )

                # 원본 메시지에서 전체 내용 가져오기 (잘림 방지)
                original_content = original_msg.get("content") or original_msg.get("body") or source_msg.get("content") or source_msg.get("body") or ""
                original_subject = original_msg.get("subject") or source_msg.get("subject") or ""
                
                source_message_payload = {
                    "id": original_msg.get("msg_id") or source_msg.get("msg_id") or source_msg.get("id"),
                    "sender": original_msg.get("sender") or source_msg.get("sender"),
                    "subject": original_subject,
                    "content": original_content,  # 전체 내용 포함 (잘림 방지)
                    "body": original_content,     # body도 포함 (호환성)
                    "platform": original_msg.get("platform") or source_msg.get("platform"),
                    "recipient_type": recipient_type,
                    "is_read": True,  # 새로 생성된 TODO는 기본적으로 읽음 처리
                }
                if received_time:
                    source_message_payload["date"] = received_time
                if simulated_time:
                    source_message_payload["simulated_datetime"] = simulated_time
                sim_day_index = original_msg.get("sim_day_index") or source_msg.get("sim_day_index")
                if sim_day_index:
                    source_message_payload["sim_day_index"] = sim_day_index
                sim_time = original_msg.get("sim_time") or source_msg.get("sim_time")
                if sim_time:
                    source_message_payload["sim_time"] = sim_time
                if source_metadata:
                    source_message_payload["metadata"] = dict(source_metadata)
                
                todo_item = {
                    "id": action.get("action_id"),
                    "title": action.get("title"),
                    "description": action.get("description"),
                    "priority": action.get("priority", priority_level),  # 액션에 없으면 result 우선순위 사용
                    "deadline": action.get("deadline"),                  # ISO 문자열 권장
                    "requester": action.get("requester") or source_msg.get("sender"),
                    "type": action.get("action_type"),
                    "status": "pending",
                    "recipient_type": recipient_type,  # 수신 타입 추가 (to/cc/bcc)
                    "source_type": source_type,  # 소스 타입 추가 (메일/메시지)
                    "persona_name": persona_name,  # 페르소나 이름 추가
                    "source_message": source_message_payload,
                    "created_at": action.get("created_at"),
                    "_viewed": False,  # 아직 사용자가 확인하지 않음
                }

                # ❶ 각 todo_item 별로 초안 생성
                try:
                    # 사용자 프로필이 있다면 반영 (없으면 None)
                    user_profile = getattr(self, "user_profile", None)
                    subject, body = build_email_draft(todo_item, user_profile=user_profile)
                    todo_item["draft_subject"] = subject
                    todo_item["draft_body"] = body
                except NameError:
                    # build_email_draft 미구현/미임포트 시 안전가드
                    todo_item["draft_subject"] = f"[확인 요청] {todo_item.get('title','')}"
                    todo_item["draft_body"] = (
                        f"안녕하세요,\n\n{todo_item.get('title','')} 관련하여 확인 부탁드립니다.\n"
                        f"- 데드라인: {todo_item.get('deadline') or '미기재'}\n\n감사합니다.\n"
                    )

                # ❷ Evidence chips / deadline confidence (result 컨텍스트 기반)
                reasons = (pr.get("reasoning") or [])[:3]
                todo_item["evidence"] = json.dumps(reasons, ensure_ascii=False)
                todo_item["deadline_confidence"] = result.get("deadline_confidence", "mid")

                # ❸ 프로젝트 태그는 나중에 비동기로 처리 (초기 TODO 생성 속도 향상)
                todo_item["project"] = None
                
                # ❹ 정렬에 쓰일 값 준비
                todo_item["_priority_val"] = priority_value.get(todo_item["priority"], 1)
                todo_item["_deadline_dt"] = _parse_deadline(todo_item.get("deadline"))

                todo_items.append(todo_item)

        # ❹ 정렬: 우선순위 내림차순, 마감 오름차순
        todo_items.sort(key=lambda x: (-x["_priority_val"], x["_deadline_dt"]))
        
        # ❹-0 중복 제거: 같은 메시지에서 생성된 TODO 중 내용이 유사한 것 제거
        if todo_items:
            def _calculate_similarity(text1: str, text2: str) -> float:
                """두 텍스트의 유사도 계산 (0.0 ~ 1.0)"""
                if not text1 or not text2:
                    return 0.0
                
                # 간단한 단어 기반 유사도 (Jaccard similarity)
                words1 = set(text1.lower().split())
                words2 = set(text2.lower().split())
                
                if not words1 or not words2:
                    return 0.0
                
                intersection = words1 & words2
                union = words1 | words2
                
                return len(intersection) / len(union) if union else 0.0
            
            # 같은 source_message_id로 그룹화
            from collections import defaultdict
            message_groups = defaultdict(list)
            for todo in todo_items:
                msg_id = todo.get("source_message", {}).get("id")
                if msg_id:
                    message_groups[msg_id].append(todo)
            
            # 각 그룹에서 중복 제거
            filtered_todos = []
            duplicate_count = 0
            
            for msg_id, todos in message_groups.items():
                if len(todos) == 1:
                    # 그룹에 TODO가 1개면 그대로 추가
                    filtered_todos.extend(todos)
                else:
                    # 여러 개면 내용 유사도 기반 중복 제거
                    kept_todos = []
                    
                    for todo in todos:
                        is_duplicate = False
                        todo_desc = todo.get("description", "")
                        
                        # 이미 유지하기로 한 TODO들과 비교
                        for kept in kept_todos:
                            kept_desc = kept.get("description", "")
                            similarity = _calculate_similarity(todo_desc, kept_desc)
                            
                            # 유사도 70% 이상이면 중복으로 간주
                            if similarity >= 0.7:
                                is_duplicate = True
                                # 유형 우선순위: meeting > deadline > review > task > response
                                type_priority = {
                                    "meeting": 5,
                                    "deadline": 4,
                                    "review": 3,
                                    "task": 2,
                                    "response": 1
                                }
                                
                                current_type_priority = type_priority.get(todo.get("type"), 0)
                                kept_type_priority = type_priority.get(kept.get("type"), 0)
                                
                                # 현재 TODO가 더 높은 우선순위 유형이면 교체
                                if current_type_priority > kept_type_priority:
                                    kept_todos.remove(kept)
                                    kept_todos.append(todo)
                                    logger.info(f"[중복제거] {kept.get('type')} → {todo.get('type')} 교체 (유사도: {similarity:.2f})")
                                else:
                                    logger.info(f"[중복제거] {todo.get('type')} 제거 (유사도: {similarity:.2f}, 유지: {kept.get('type')})")
                                
                                duplicate_count += 1
                                break
                        
                        if not is_duplicate:
                            kept_todos.append(todo)
                    
                    filtered_todos.extend(kept_todos)
            
            # 메시지 ID가 없는 TODO들도 추가
            for todo in todo_items:
                if not todo.get("source_message", {}).get("id"):
                    filtered_todos.append(todo)
            
            if duplicate_count > 0:
                logger.info(f"🔄 중복 TODO {duplicate_count}개 제거 ({len(todo_items)}개 → {len(filtered_todos)}개)")
            
            todo_items = filtered_todos
            # 다시 정렬
            todo_items.sort(key=lambda x: (-x["_priority_val"], x["_deadline_dt"]))

        # ❹-1 우선순위 재보정(편중 완화)
        if todo_items:
            now_utc = datetime.now(timezone.utc)
            scored_items: List[tuple[float, Dict]] = []
            for t in todo_items:
                base = priority_value.get(t.get("priority", "low"), 1)
                deadline_dt = t.get("_deadline_dt") or datetime.max.replace(tzinfo=timezone.utc)
                if deadline_dt == datetime.max:
                    urgency = 0.0
                else:
                    if deadline_dt.tzinfo is None:
                        deadline_dt = deadline_dt.replace(tzinfo=timezone.utc)
                    hours_left = (deadline_dt - now_utc).total_seconds() / 3600.0
                    if hours_left <= 24:
                        urgency = 1.5
                    elif hours_left <= 72:
                        urgency = 1.0
                    elif hours_left <= 168:
                        urgency = 0.5
                    else:
                        urgency = 0.0
                evidence_count = 0
                try:
                    evidence_count = len(json.loads(t.get("evidence") or "[]"))
                except Exception:
                    pass
                evidence_bonus = min(0.6, 0.2 * evidence_count)
                score = base + urgency + evidence_bonus
                scored_items.append((score, t))

            scored_items.sort(key=lambda x: x[0], reverse=True)
            total = len(scored_items)
            if total == 1:
                boundaries = (1, 1)
            elif total == 2:
                boundaries = (1, 2)
            else:
                high_cut = max(1, round(total * 0.3))
                low_cut = total - max(1, round(total * 0.2))
                if low_cut <= high_cut:
                    low_cut = min(total, high_cut + 1)
                boundaries = (high_cut, low_cut)

            high_cut, low_cut = boundaries
            high_priority_count = medium_priority_count = low_priority_count = 0
            for idx, (score, item) in enumerate(scored_items):
                # 원래 우선순위 저장
                original_priority = item.get("priority", "low")
                
                if idx < high_cut:
                    # 원래 LOW였고 점수도 낮으면 MEDIUM까지만
                    if original_priority == "low" and score < 2.0:
                        item["priority"] = "medium"
                        medium_priority_count += 1
                    else:
                        item["priority"] = "high"
                        high_priority_count += 1
                elif idx >= low_cut:
                    # 원래 HIGH였으면 MEDIUM까지만
                    if original_priority == "high":
                        item["priority"] = "medium"
                        medium_priority_count += 1
                    else:
                        item["priority"] = "low"
                        low_priority_count += 1
                else:
                    item["priority"] = "medium"
                    medium_priority_count += 1

        # ❺ Top-3 마킹
        for i, t in enumerate(todo_items):
            t["is_top3"] = (i < 3)
            # 내부 정렬 키 제거(직렬화 안전)
            t.pop("_priority_val", None)
            t.pop("_deadline_dt", None)

        # ❻ 리턴 페이로드
        todo_list = {
            "summary": {
                "high": high_priority_count,
                "medium": medium_priority_count,
                "low": low_priority_count,
                "total": len(todo_items),
            },
            "items": todo_items,
        }
        logger.info(f"🔍 [DEBUG] 전체 actions: {total_actions}개, 최종 TODO: {len(todo_items)}개")
        return todo_list
        
    async def cleanup(self):
        """리소스 정리"""
        logger.info("🧹 리소스 정리 중...")
        logger.info("✅ 정리 완료")
    
    async def run_full_cycle(
        self,
        dataset_config: Optional[Dict[str, Any]] = None,
        collect_options: Optional[Dict[str, Any]] = None,
    ) -> Dict:
        """전체 사이클 실행
        
        데이터셋 초기화부터 TODO 생성까지 전체 워크플로우를 실행합니다.
        
        Args:
            dataset_config: 데이터셋 설정 딕셔너리
            collect_options: 메시지 수집 옵션 딕셔너리
            
        Returns:
            실행 결과 딕셔너리:
            - success (bool): 성공 여부
            - todo_list (Dict): 생성된 TODO 리스트
            - analysis_results (List[Dict]): 분석 결과 리스트
            - collected_messages (int): 수집된 메시지 수
            - messages (List[Dict]): 수집된 메시지 원본 데이터 (v1.1.1+)
            - error (str): 오류 메시지 (실패 시)
        """
        try:
            # 데이터셋 초기화
            await self.initialize(dataset_config)

            # 메시지 수집
            collect_kwargs = collect_options or {}
            messages = await self.collect_messages(**collect_kwargs)

            if not messages:
                return {"error": "수집된 메시지가 없습니다."}

            # 메시지 분석
            analysis_results = await self.analyze_messages()
            
            # TODO 생성
            todo_list = await self.generate_todo_list(analysis_results)

            # 결과 반환
            return {
                "success": True,
                "todo_list": todo_list,
                "analysis_results": analysis_results,
                "collected_messages": len(messages),
                "messages": messages,  # GUI에서 사용 (v1.1.1+)
            }

        except Exception as e:
            logger.error(f"전체 사이클 실행 오류: {e}")
            return {"error": str(e)}

        finally:
            await self.cleanup()


# 테스트 함수
async def test_smart_assistant():
    """스마트 어시스턴트 테스트"""
    print("🚀 Smart Assistant 테스트 시작")
    
    dataset_config = {
        "dataset_root": DEFAULT_DATASET_ROOT,
        "force_reload": True,
    }
    collect_options = {
        "email_limit": None,
        "messenger_limit": None,
    }
    
    assistant = SmartAssistant()
    
    try:
        result = await assistant.run_full_cycle(dataset_config, collect_options)
        
        if result.get("success"):
            todo_list = result["todo_list"]
            
            print(f"\n📋 TODO 리스트 생성 완료!")
            print(f"총 {todo_list['total_items']}개 아이템")
            print(f"우선순위: High({todo_list['priority_stats']['high']}), Medium({todo_list['priority_stats']['medium']}), Low({todo_list['priority_stats']['low']})")
            
            print(f"\n🔥 상위 5개 TODO:")
            for i, item in enumerate(todo_list["items"][:5], 1):
                print(f"{i}. [{item['priority'].upper()}] {item['title']}")
                print(f"   요청자: {item['requester']}")
                if item['deadline']:
                    print(f"   데드라인: {item['deadline']}")
                print(f"   타입: {item['type']}")
                print()
        else:
            print(f"❌ 오류: {result.get('error')}")
    
    except Exception as e:
        print(f"❌ 테스트 오류: {e}")


if __name__ == "__main__":
    # 간단한 테스트 실행
    print("Smart Assistant v1.1.5")
    print("=" * 50)
    
    # 환경변수 확인
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
        print("   LLM 기능은 기본 모드로 동작합니다.")
    
    asyncio.run(test_smart_assistant())


