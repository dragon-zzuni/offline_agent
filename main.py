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

from nlp.draft import build_email_draft

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
DEFAULT_DATASET_ROOT = project_root / "data" / "mobile_4week_ko"

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
    """스마트 어시스턴트 메인 클래스"""
    
    def __init__(self, dataset_root: Optional[Path | str] = None):
        self.dataset_root = Path(dataset_root) if dataset_root else DEFAULT_DATASET_ROOT

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
        self._dataset_loaded = False
        self._dataset_last_loaded: Optional[datetime] = None

    def set_dataset_root(self, dataset_root: Path | str) -> None:
        """데이터셋 루트를 변경하고 다음 수집 시 재로드하도록 표시."""
        self.dataset_root = Path(dataset_root)
        self._dataset_loaded = False

    def _load_json(self, filename: str) -> Any:
        path = self.dataset_root / filename
        if not path.exists():
            raise FileNotFoundError(f"데이터 파일을 찾을 수 없습니다: {path}")
        with path.open("r", encoding="utf-8") as fp:
            return json.load(fp)

    def _ensure_dataset(self, force_reload: bool = False) -> None:
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
    ):
        """오프라인 데이터셋에서 메시지를 수집한 뒤 공통 포맷으로 반환"""
        logger.info("📥 메시지 수집 시작 (mobile_4week_ko)")
        self._ensure_dataset(force_reload=force_reload)

        chat_messages = list(self._chat_messages)
        email_messages = list(self._email_messages)

        def _apply_limit(items: List[Dict[str, Any]], limit: Optional[int]) -> List[Dict[str, Any]]:
            if not limit:
                return items
            ordered = sorted(items, key=_sort_key, reverse=True)
            return ordered[:limit]

        # messenger_limit를 우선 적용하고, 없으면 json_limit 사용 (하위 호환용)
        chat_messages = _apply_limit(chat_messages, messenger_limit or json_limit)
        email_messages = _apply_limit(email_messages, email_limit)

        combined = chat_messages + email_messages

        if overall_limit:
            combined = sorted(combined, key=_sort_key, reverse=True)[:overall_limit]

        merged = coalesce_messages(combined, window_seconds=90, max_chars=1200)
        merged.sort(key=_sort_key, reverse=True)

        self.collected_messages = merged
        logger.info(
            "📦 총 %d개 메시지 수집 (chat %d, email %d)",
            len(self.collected_messages),
            len(chat_messages),
            len(email_messages),
        )
        return self.collected_messages
        # 4) 최신순 정렬 → 전체 상한
        all_messages = coalesce_messages(all_messages, window_seconds=90, max_chars=1200)
        all_messages.sort(key=_sort_key, reverse=True)

        if overall_limit:
            all_messages = all_messages[:overall_limit]

        self.collected_messages = all_messages
        logger.info(f"📥 총 {len(all_messages)}개 메시지 수집 완료")
        return all_messages
    # main.py (핵심 흐름 정리 예시)

    async def analyze_messages(self):
        if not self.collected_messages:
            logger.warning("분석할 메시지가 없습니다.")
            return []

        logger.info("🔍 메시지 분석 시작...")

        # 1) 우선순위 분류
        logger.info("🎯 우선순위 분류 중...")
        self.ranked_messages = await self.priority_ranker.rank_messages(self.collected_messages)

        TOP_N = 60
        top_msgs = [m for (m, _) in self.ranked_messages][:TOP_N]

        # 2) 상위 N개 요약
        logger.info(f"📝 상위 {TOP_N}개 메시지 요약 중...")
        self.summaries = await self.summarizer.batch_summarize(top_msgs)

        # msg_id → summary 맵
        summary_by_id = {}
        for m, s in zip(top_msgs, self.summaries):
            if s and not getattr(s, "original_id", None):
                s.original_id = m.get("msg_id")
            summary_by_id[m["msg_id"]] = s

        # 3) 액션 추출
        logger.info("⚡ 액션 추출 중...")
        actions = await self.action_extractor.batch_extract_actions(top_msgs)
        self.extracted_actions = actions

        actions_by_id = {}
        for a in actions:
            src = getattr(a, "source_message_id", None) or (a.get("source_message_id") if isinstance(a, dict) else None)
            if not src:
                continue
            actions_by_id.setdefault(src, []).append(a)

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

        # 5) 전체 메시지(메신저+이메일) 요약 텍스트 생성
        conv_text = ""
        self.conversation_summary = None
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


        # 6) 분석 결과 탭 텍스트 생성 (우선순위 섹션 포함)
        sections_text = await build_overall_analysis_text(self, results)
        self.analysis_report_text = sections_text


        logger.info(f"🔍 {len(results)}개 메시지 분석 완료")
        return results

        
    async def generate_todo_list(self, analysis_results: List[Dict]) -> Dict:
        """TODO 리스트 생성"""
        logger.info("📋 TODO 리스트 생성 중...")

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

        for result in analysis_results or []:
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
                todo_item = {
                    "id": action.get("action_id"),
                    "title": action.get("title"),
                    "description": action.get("description"),
                    "priority": action.get("priority", priority_level),  # 액션에 없으면 result 우선순위 사용
                    "deadline": action.get("deadline"),                  # ISO 문자열 권장
                    "requester": action.get("requester") or (result.get("message") or {}).get("sender"),
                    "type": action.get("action_type"),
                    "status": "pending",
                    "source_message": {
                        "id": (result.get("message") or {}).get("msg_id"),
                        "sender": (result.get("message") or {}).get("sender"),
                        "subject": (result.get("message") or {}).get("subject"),
                        "platform": (result.get("message") or {}).get("platform"),
                    },
                    "created_at": action.get("created_at"),
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
                reasons = (pr.get("reasons") or [])[:3]
                todo_item["evidence"] = json.dumps(reasons, ensure_ascii=False)
                todo_item["deadline_confidence"] = result.get("deadline_confidence", "mid")

                # ❸ 정렬에 쓰일 값 준비
                todo_item["_priority_val"] = priority_value.get(todo_item["priority"], 1)
                todo_item["_deadline_dt"] = _parse_deadline(todo_item.get("deadline"))

                todo_items.append(todo_item)

        # ❹ 정렬: 우선순위 내림차순, 마감 오름차순
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
            for idx, (_, item) in enumerate(scored_items):
                if idx < high_cut:
                    item["priority"] = "high"
                    high_priority_count += 1
                elif idx >= low_cut:
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
        """전체 사이클 실행"""
        try:
            await self.initialize(dataset_config)

            collect_kwargs = collect_options or {}
            messages = await self.collect_messages(**collect_kwargs)

            if not messages:
                return {"error": "수집된 메시지가 없습니다."}

            analysis_results = await self.analyze_messages()
            todo_list = await self.generate_todo_list(analysis_results)

            return {
                "success": True,
                "todo_list": todo_list,
                "analysis_results": analysis_results,
                "collected_messages": len(messages),
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
    print("Smart Assistant v1.0")
    print("=" * 50)
    
    # 환경변수 확인
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
        print("   LLM 기능은 기본 모드로 동작합니다.")
    
    asyncio.run(test_smart_assistant())


