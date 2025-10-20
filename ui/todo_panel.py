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

logger = logging.getLogger(__name__)

TODO_DB_PATH = os.path.join("data", "multi_project_8week_ko", "todos_cache.db")

TOP3_RULE_DEFAULT = {
    "priority_high": 3.0,
    "priority_medium": 2.0,
    "priority_low": 1.0,
    "deadline_emphasis": 24.0,
    "deadline_base": 1.0,
    "evidence_per_item": 0.1,
    "evidence_max_bonus": 0.5,
    "recipient_type_cc_penalty": 0.7,  # 참조(CC)로 받은 경우 가중치 (0.7 = 30% 감소)
}
_TOP3_RULES = deepcopy(TOP3_RULE_DEFAULT)
_TOP3_LAST_INSTRUCTION = ""
_KOREAN_NAME_SUFFIXES = ("선생님", "팀장", "부장", "님", "씨")
_KOREAN_PARTICLES = (
    "께서", "에서", "에게", "으로", "로", "와", "과", "은", "는", "이", "가",
    "을", "를", "도", "만", "부터", "까지", "에게서", "밖에", "로서", "로써",
    "이라서", "라서", "이라도", "라도", "이며", "이며도"
)

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

def get_top3_rules() -> Dict[str, float]:
    return dict(_TOP3_RULES)

def set_top3_rules(new_rules: Dict[str, float]) -> None:
    for key, default in TOP3_RULE_DEFAULT.items():
        value = new_rules.get(key)
        if value is None:
            continue
        try:
            value = float(value)
        except (TypeError, ValueError):
            continue
        if key.startswith("priority_") and value <= 0:
            continue
        if key == "deadline_emphasis" and value < 0:
            value = 0.0
        if key == "deadline_base" and value < 0.1:
            value = 0.1
        if key == "evidence_per_item" and value < 0:
            value = 0.0
        if key == "evidence_max_bonus" and value < 0:
            value = 0.0
        _TOP3_RULES[key] = value

def _persist_top3_rules() -> None:
    global _TOP3_LAST_INSTRUCTION
    try:
        os.makedirs(os.path.dirname(CONFIG_STORE_PATH), exist_ok=True)
        try:
            with open(CONFIG_STORE_PATH, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except FileNotFoundError:
            data = {}
        except json.JSONDecodeError:
            data = {}
        data.setdefault("top3_rules", {})
        data["top3_rules"]["weights"] = get_top3_rules()
        data["top3_rules"]["entities"] = get_entity_rules()
        data["top3_rules"]["instruction"] = _TOP3_LAST_INSTRUCTION
        with open(CONFIG_STORE_PATH, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
    except Exception as exc:
        print(f"[TodoPanel] 규칙 저장 실패: {exc}")


def _load_persisted_top3_rules() -> None:
    global _TOP3_LAST_INSTRUCTION
    try:
        with open(CONFIG_STORE_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        return
    except json.JSONDecodeError:
        print("[TodoPanel] 규칙 로드 실패: JSON 파싱 오류")
        return
    except Exception as exc:
        print(f"[TodoPanel] 규칙 로드 실패: {exc}")
        return

    rules = (data.get("top3_rules") or {}) if isinstance(data, dict) else {}
    weights = rules.get("weights")
    entities = rules.get("entities")
    instruction = rules.get("instruction")

    if isinstance(weights, dict) and weights:
        set_top3_rules(weights)
    if isinstance(entities, dict):
        update_entity_rules(entities, reset=True)
    if isinstance(instruction, str):
        _TOP3_LAST_INSTRUCTION = instruction


ENTITY_RULES_DEFAULT = {
    "requester": {},
    "keyword": {},
    "type": {},
}
_TOP3_ENTITY_RULES = deepcopy(ENTITY_RULES_DEFAULT)


def get_entity_rules() -> Dict[str, Dict[str, float]]:
    return {k: dict(v) for k, v in _TOP3_ENTITY_RULES.items()}


def update_entity_rules(new_rules: Dict[str, Dict[str, float]] | None, reset: bool = False) -> None:
    if reset:
        for cat in ENTITY_RULES_DEFAULT:
            _TOP3_ENTITY_RULES[cat].clear()
    if not new_rules:
        return
    for category, mapping in new_rules.items():
        if category not in _TOP3_ENTITY_RULES:
            continue
        dest = _TOP3_ENTITY_RULES[category]
        for key, value in (mapping or {}).items():
            if value is None:
                continue

            name_candidates: List[str] = []
            bonus_value: Optional[float] = None

            key_lower = key.lower() if isinstance(key, str) else ""
            if isinstance(value, dict):
                for k in ("match", "matches", "name", "names", "target", "value"):
                    v = value.get(k)
                    if isinstance(v, str) and v.strip():
                        name_candidates.append(v.strip())
                for k in ("bonus", "weight", "score", "value"):
                    v = value.get(k)
                    if isinstance(v, (int, float)):
                        bonus_value = float(v)
                        break
            elif isinstance(value, (list, tuple)):
                for item in value:
                    if isinstance(item, str):
                        name_candidates.append(item.strip())
                    elif isinstance(item, (int, float)):
                        bonus_value = float(item)
            elif isinstance(value, str):
                name_candidates.append(value.strip())
            elif isinstance(value, (int, float)):
                bonus_value = float(value)
                if key_lower not in {"match", "matches", "name", "names", "target", "value"}:
                    name_candidates.append(key)

            if not name_candidates:
                if not key_lower or key_lower in {"match", "matches", "name", "names", "target", "value"}:
                    continue
                name_candidates.append(key)

            if bonus_value is None or bonus_value <= 0:
                bonus_value = 1.0

            bonus_value = min(bonus_value, 3.0)
            for candidate in name_candidates:
                candidate = candidate.strip()
                if not candidate:
                    continue
                clean_candidate = _normalize_korean_name(candidate)
                if clean_candidate and re.fullmatch(r"[가-힣]{2,6}", clean_candidate):
                    candidate_key = clean_candidate.lower()
                else:
                    candidate_key = candidate.lower()
                if not candidate_key:
                    continue
                dest[candidate_key] = max(dest.get(candidate_key, 0.0), bonus_value)


def describe_top3_rules() -> str:
    rules = get_top3_rules()
    parts = [
        f"우선순위 가중치 H/M/L: {rules.get('priority_high',0):.2f}/{rules.get('priority_medium',0):.2f}/{rules.get('priority_low',0):.2f}",
        f"마감 보너스 기준: base {rules.get('deadline_base',0):.2f}, emphasis {rules.get('deadline_emphasis',0):.1f}",
        f"근거 보너스: +{rules.get('evidence_per_item',0):.2f}/item (최대 {rules.get('evidence_max_bonus',0):.2f})",
    ]
    entity = get_entity_rules()
    requester = ", ".join(f"{k}:{v:.2f}" for k, v in entity.get("requester", {}).items())
    keyword = ", ".join(f"{k}:{v:.2f}" for k, v in entity.get("keyword", {}).items())
    etype = ", ".join(f"{k}:{v:.2f}" for k, v in entity.get("type", {}).items())
    if requester:
        parts.append(f"요청자 가중치: {requester}")
    if keyword:
        parts.append(f"키워드 가중치: {keyword}")
    if etype:
        parts.append(f"유형 가중치: {etype}")
    return "\n".join(parts)


def _extract_json_from_text(content: str) -> Optional[dict]:
    try:
        return json.loads(content)
    except Exception:
        pass
    match = re.search(r"\{.*\}", content, re.DOTALL)
    if not match:
        return None
    snippet = match.group(0)
    try:
        return json.loads(snippet)
    except Exception:
        return None


def _try_llm_parse_rules(text: str) -> tuple[Optional[dict], str]:
    provider = (LLM_CONFIG.get("provider") or "azure").lower()
    model = LLM_CONFIG.get("model") or "openrouter/auto"
    headers: Dict[str, str] = {}
    url: Optional[str] = None
    payload_model: Optional[str] = model

    if provider == "azure":
        api_key = LLM_CONFIG.get("azure_api_key") or os.getenv("AZURE_OPENAI_KEY")
        endpoint = (LLM_CONFIG.get("azure_endpoint") or os.getenv("AZURE_OPENAI_ENDPOINT") or "").rstrip("/")
        deployment = LLM_CONFIG.get("azure_deployment") or os.getenv("AZURE_OPENAI_DEPLOYMENT")
        api_version = LLM_CONFIG.get("azure_api_version") or os.getenv("AZURE_OPENAI_API_VERSION") or "2024-02-15"
        if not api_key or not endpoint or not deployment:
            return None, "AZURE_OPENAI_KEY/ENDPOINT/DEPLOYMENT가 설정되어 있지 않습니다."
        url = f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"
        headers = {"api-key": api_key, "Content-Type": "application/json"}
        payload_model = None  # Azure는 deployment 경로로 모델을 지정
    elif provider == "openai":
        api_key = LLM_CONFIG.get("openai_api_key") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None, "OPENAI_API_KEY가 설정되어 있지 않습니다."
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    elif provider == "openrouter":
        api_key = LLM_CONFIG.get("openrouter_api_key") or os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            return None, "OPENROUTER_API_KEY가 설정되어 있지 않습니다."
        base_url = LLM_CONFIG.get("openrouter_base_url") or "https://openrouter.ai/api/v1"
        url = f"{base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", "https://localhost"),
            "X-Title": os.getenv("OPENROUTER_APP_NAME", "SmartAssistant"),
            "Content-Type": "application/json",
        }
    else:
        return None, f"지원되지 않는 LLM 공급자입니다: {provider}"

    system_prompt = (
        "You are a parser that converts natural language rules into a json object.\n"
        "Return a json object with keys:\n"
        "{\n"
        '  \"priority_weights\": {\"priority_high\": float, \"priority_medium\": float, \"priority_low\": float},\n'
        '  \"entity_rules\": {\n'
        '      \"requester\": {\"match\": bonus},\n'
        '      \"keyword\": {\"match\": bonus},\n'
        '      \"type\": {\"match\": bonus}\n'
        "  },\n"
        '  \"reset\": bool\n'
        "}\n"
        "Use bonuses between 0.1 and 2.0. Omit keys that are not provided.\n"
        "Do not add prose; reply with json only."
    )
    try:
        payload: Dict[str, object] = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
        }
        if payload_model:
            payload["model"] = payload_model

        token_limit_raw = LLM_CONFIG.get("max_tokens")
        try:
            token_limit = int(float(token_limit_raw)) if token_limit_raw is not None else None
        except (TypeError, ValueError):
            token_limit = None

        if provider == "azure":
            if token_limit:
                payload["max_completion_tokens"] = token_limit
            payload["response_format"] = {"type": "json_object"}
        else:
            payload["temperature"] = 0.0
            if token_limit:
                payload["max_tokens"] = token_limit
            if provider == "openai":
                payload["response_format"] = {"type": "json_object"}

        logger.info("[Top3Rules][LLM] provider=%s text=%s", provider, text[:200])
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        resp_json = response.json()
        logger.debug("[Top3Rules][LLM] response=%s", json.dumps(resp_json, ensure_ascii=False)[:500])

        choices = resp_json.get("choices") or []
        content = ""
        if choices:
            message = choices[0].get("message") or {}
            content = message.get("content") or ""
        parsed = _extract_json_from_text(content or "")
        if not parsed:
            return None, "LLM 응답에서 JSON을 찾지 못했습니다."
        return parsed, ""
    except requests.RequestException as exc:
        logger.warning("[Top3Rules][LLM] request error: %s", exc)
        return None, f"LLM 요청 실패: {exc}"
    except Exception as exc:
        logger.warning("[Top3Rules][LLM] processing error: %s", exc)
        return None, f"LLM 처리 오류: {exc}"


def _heuristic_rules_from_text(text: str) -> Optional[dict]:
    if not text:
        return None
    if "reset" in text.lower() or "초기화" in text:
        return {"reset": True}

    lines = [line.strip() for line in re.split(r"[.;\n]", text) if line.strip()]
    entity_rules = {"requester": {}, "keyword": {}, "type": {}}
    priority_weights: Dict[str, float] = {}

    for line in lines:
        lower = line.lower()
        name_bonus = 2.0 if any(word in lower for word in ["최우선", "항상", "무조건", "must", "high", "urgent", "가장 먼저"]) else 1.2
        keyword_bonus = 1.0

        for name in re.findall(r"[가-힣]{2,6}(?:선생님|부장|팀장|님|씨)?", line):
            cleaned = _normalize_korean_name(name)
            if len(cleaned) >= 2:
                key = cleaned.lower()
                entity_rules["requester"][key] = max(entity_rules["requester"].get(key, 0.0), name_bonus)

        for eng in re.findall(r"[A-Z][a-z]+(?: [A-Z][a-z]+)+", line):
            key = eng.strip().lower()
            entity_rules["requester"][key] = max(entity_rules["requester"].get(key, 0.0), name_bonus)

        for word in re.findall(r"[A-Za-z]{3,}", line):
            w = word.lower()
            if w in {"priority", "high", "medium", "low", "urgent", "always"}:
                continue
            entity_rules["keyword"][w] = max(entity_rules["keyword"].get(w, 0.0), keyword_bonus)

        if "버그" in line or "bug" in lower:
            entity_rules["type"]["bug"] = max(entity_rules["type"].get("bug", 0.0), 1.2)
        if "긴급" in line or "incident" in lower:
            entity_rules["type"]["incident"] = max(entity_rules["type"].get("incident", 0.0), 1.5)

        if any(word in lower for word in ["high", "최우선", "최고", "가장 먼저"]):
            priority_weights["priority_high"] = max(priority_weights.get("priority_high", TOP3_RULE_DEFAULT["priority_high"]), TOP3_RULE_DEFAULT["priority_high"] + 1.5)
        if any(word in lower for word in ["medium", "중간", "보통"]):
            priority_weights["priority_medium"] = max(priority_weights.get("priority_medium", TOP3_RULE_DEFAULT["priority_medium"]), TOP3_RULE_DEFAULT["priority_medium"] + 0.5)
        if any(word in lower for word in ["low", "낮", "덜 중요"]):
            priority_weights["priority_low"] = max(0.2, TOP3_RULE_DEFAULT["priority_low"] - 0.5)

    note = "휴리스틱으로 규칙을 해석했습니다."
    return {"priority_weights": priority_weights, "entity_rules": entity_rules, "note": note}


def apply_natural_language_rules(text: str, reset: bool = False) -> tuple[str, str]:
    global _TOP3_LAST_INSTRUCTION
    cleaned_text = text.strip()

    if reset or not cleaned_text:
        _TOP3_LAST_INSTRUCTION = "" if reset else cleaned_text
        set_top3_rules(TOP3_RULE_DEFAULT)
        update_entity_rules({}, reset=True)
        _persist_top3_rules()
        logger.info("[Top3Rules] rules reset by user input")
        return "규칙을 기본값으로 초기화했습니다.", describe_top3_rules()

    parsed, llm_message = _try_llm_parse_rules(cleaned_text)
    heuristics = _heuristic_rules_from_text(cleaned_text)
    parsed_note = ""
    note = ""
    if parsed:
        note = "LLM 결과를 적용했습니다."
        parsed_note = note
    if heuristics:
        if parsed:
            parsed.setdefault("priority_weights", {})
            parsed["priority_weights"].update(heuristics.get("priority_weights") or {})
            ent = parsed.setdefault("entity_rules", {})
            for cat, mapping in (heuristics.get("entity_rules") or {}).items():
                ent.setdefault(cat, {})
                for k, v in mapping.items():
                    ent[cat][k] = max(ent[cat].get(k, 0.0), v)
            note = parsed_note + " + 휴리스틱 보완"
        else:
            parsed = heuristics
            note = parsed.get("note", "휴리스틱 규칙을 적용했습니다.")
            if llm_message:
                note += f" (LLM 실패: {llm_message})"
    if not parsed:
        msg = "규칙을 해석하지 못했습니다."
        if llm_message:
            msg += f" (LLM 실패: {llm_message})"
        logger.warning("[Top3Rules] failed to parse rules: %s", msg)
        return msg, describe_top3_rules()

    if parsed.get("reset"):
        _TOP3_LAST_INSTRUCTION = ""
        set_top3_rules(TOP3_RULE_DEFAULT)
        update_entity_rules({}, reset=True)
        _persist_top3_rules()
        logger.info("[Top3Rules] applied reset directive from rules")
    else:
        priority_weights = parsed.get("priority_weights")
        if priority_weights:
            set_top3_rules({**get_top3_rules(), **priority_weights})
        entity_rules = parsed.get("entity_rules")
        if entity_rules:
            update_entity_rules(entity_rules, reset=True)
        _TOP3_LAST_INSTRUCTION = cleaned_text
        _persist_top3_rules()
        logger.info(
            "[Top3Rules] applied rules. weights=%s entities=%s",
            get_top3_rules(),
            get_entity_rules(),
        )

    summary = describe_top3_rules()
    return note, summary


_load_persisted_top3_rules()


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
        recipient_type TEXT DEFAULT 'to'
    )
    """)
    
    # 기존 테이블에 recipient_type 컬럼 추가 (마이그레이션)
    try:
        cur.execute("ALTER TABLE todos ADD COLUMN recipient_type TEXT DEFAULT 'to'")
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

def _parse_iso_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        try:
            return datetime.fromisoformat(value)
        except Exception:
            return None

def _created_ts(todo: dict) -> float:
    dt = _parse_iso_dt(todo.get("created_at"))
    if not dt:
        return 0.0
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()

def _is_truthy(v) -> bool:
    return v in (1, "1", True, "true", "TRUE", "True")

def _score_for_top3(todo: dict) -> float:
    rules = _TOP3_RULES
    priority = (todo.get("priority") or "low").lower()
    priority_weights = {
        "high": rules.get("priority_high", 3.0),
        "medium": rules.get("priority_medium", 2.0),
        "low": rules.get("priority_low", 1.0),
    }
    w_priority = priority_weights.get(priority, rules.get("priority_low", 1.0))

    deadline_raw = todo.get("deadline_ts") or todo.get("deadline")
    w_deadline = rules.get("deadline_base", 1.0)
    if deadline_raw:
        dl = _parse_iso_dt(deadline_raw)
        if dl:
            if dl.tzinfo is None:
                dl = dl.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            hours_left = max(0.0, (dl - now).total_seconds() / 3600.0)
            emphasis = max(0.0, rules.get("deadline_emphasis", 24.0))
            if emphasis > 0:
                w_deadline = rules.get("deadline_base", 1.0) + (emphasis / (emphasis + hours_left))

    evidence = todo.get("evidence")
    if not isinstance(evidence, list):
        try:
            evidence = json.loads(evidence or "[]")
        except Exception:
            evidence = []
    per_item = max(0.0, rules.get("evidence_per_item", 0.1))
    max_bonus = max(0.0, rules.get("evidence_max_bonus", 0.5))
    w_evidence = 1.0 + min(max_bonus, per_item * len(evidence))

    rule_multiplier = 1.0
    priority_bonus = 0.0
    entity_rules = _TOP3_ENTITY_RULES
    requester = (todo.get("requester") or "").lower()
    if requester:
        for match, bonus in entity_rules.get("requester", {}).items():
            if match and match in requester:
                priority_bonus += bonus
                rule_multiplier += bonus * 0.25

    text_fields = " ".join([
        todo.get("title", ""),
        todo.get("description", ""),
        todo.get("type", ""),
    ]).lower()
    for match, bonus in entity_rules.get("keyword", {}).items():
        if match and match in text_fields:
            priority_bonus += bonus * 0.5
            rule_multiplier += bonus * 0.25
    todo_type = (todo.get("type") or "").lower()
    for match, bonus in entity_rules.get("type", {}).items():
        if match and match in todo_type:
            priority_bonus += bonus * 0.5
            rule_multiplier += bonus * 0.25

    rule_multiplier = max(0.5, min(rule_multiplier, 6.0))
    if priority_bonus > 0:
        priority_floor = max(rules.get("priority_high", 3.0) + priority_bonus, 3.5)
    else:
        priority_floor = 0.0
    priority_term = max(0.1, w_priority + priority_bonus, priority_floor)

    # 참조(CC) 패널티 적용
    recipient_type = (todo.get("recipient_type") or "to").lower()
    cc_penalty = 1.0
    if recipient_type == "cc":
        cc_penalty = rules.get("recipient_type_cc_penalty", 0.7)
    elif recipient_type == "bcc":
        cc_penalty = rules.get("recipient_type_cc_penalty", 0.7) * 0.9  # BCC는 더 낮게

    return (priority_term * rule_multiplier) * w_deadline * w_evidence * cc_penalty

def _pick_top3(items: List[dict]) -> List[str]:
    cand = [
        t for t in items
        if (t.get("status") or "pending").lower() not in ("done",)
    ]
    cand.sort(key=lambda t: (_score_for_top3(t), _created_ts(t)), reverse=True)
    top_ids: List[str] = []
    for t in cand:
        tid = t.get("id")
        if not tid:
            continue
        if tid not in top_ids:
            top_ids.append(tid)
        if len(top_ids) == 3:
            break
    return top_ids

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
    if todo.get("_viewed"):
        return False
    src = _source_message_dict(todo)
    if not src:
        return False
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
class Top3RuleDialog(QDialog):
    def __init__(self, current_rules: Dict[str, float], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Top-3 기준 설정")
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)
        desc = QLabel("각 가중치를 조정하면 Top-3 선정 점수에 바로 반영됩니다.")
        desc.setWordWrap(True)
        desc.setStyleSheet("color:#374151;")
        layout.addWidget(desc)

        form = QFormLayout()

        self.priority_high = QDoubleSpinBox()
        self.priority_high.setRange(0.1, 10.0)
        self.priority_high.setSingleStep(0.1)
        self.priority_high.setDecimals(1)

        self.priority_medium = QDoubleSpinBox()
        self.priority_medium.setRange(0.1, 10.0)
        self.priority_medium.setSingleStep(0.1)
        self.priority_medium.setDecimals(1)

        self.priority_low = QDoubleSpinBox()
        self.priority_low.setRange(0.1, 10.0)
        self.priority_low.setSingleStep(0.1)
        self.priority_low.setDecimals(1)

        self.deadline_emphasis = QDoubleSpinBox()
        self.deadline_emphasis.setRange(0.0, 168.0)
        self.deadline_emphasis.setSingleStep(1.0)
        self.deadline_emphasis.setDecimals(1)

        self.evidence_per_item = QDoubleSpinBox()
        self.evidence_per_item.setRange(0.0, 1.0)
        self.evidence_per_item.setSingleStep(0.05)
        self.evidence_per_item.setDecimals(2)

        self.evidence_max_bonus = QDoubleSpinBox()
        self.evidence_max_bonus.setRange(0.0, 5.0)
        self.evidence_max_bonus.setSingleStep(0.1)
        self.evidence_max_bonus.setDecimals(2)

        form.addRow("High 우선순위 가중치", self.priority_high)
        form.addRow("Medium 우선순위 가중치", self.priority_medium)
        form.addRow("Low 우선순위 가중치", self.priority_low)
        form.addRow("마감 임박 보너스 (기본 24)", self.deadline_emphasis)
        form.addRow("근거 1개당 보너스", self.evidence_per_item)
        form.addRow("근거 보너스 최대치", self.evidence_max_bonus)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._apply_initial(current_rules)

    def _apply_initial(self, rules: Dict[str, float]) -> None:
        self.priority_high.setValue(rules.get("priority_high", TOP3_RULE_DEFAULT["priority_high"]))
        self.priority_medium.setValue(rules.get("priority_medium", TOP3_RULE_DEFAULT["priority_medium"]))
        self.priority_low.setValue(rules.get("priority_low", TOP3_RULE_DEFAULT["priority_low"]))
        self.deadline_emphasis.setValue(rules.get("deadline_emphasis", TOP3_RULE_DEFAULT["deadline_emphasis"]))
        self.evidence_per_item.setValue(rules.get("evidence_per_item", TOP3_RULE_DEFAULT["evidence_per_item"]))
        self.evidence_max_bonus.setValue(rules.get("evidence_max_bonus", TOP3_RULE_DEFAULT["evidence_max_bonus"]))

    def rules(self) -> Dict[str, float]:
        return {
            "priority_high": self.priority_high.value(),
            "priority_medium": self.priority_medium.value(),
            "priority_low": self.priority_low.value(),
            "deadline_emphasis": self.deadline_emphasis.value(),
            "deadline_base": TOP3_RULE_DEFAULT["deadline_base"],
            "evidence_per_item": self.evidence_per_item.value(),
            "evidence_max_bonus": self.evidence_max_bonus.value(),
        }


class Top3NaturalRuleDialog(QDialog):
    def __init__(self, parent=None, seed_text: Optional[str] = None, summary_text: Optional[str] = None):
        super().__init__(parent)
        self.setWindowTitle("자연어 규칙 입력")
        self.setMinimumSize(420, 320)

        layout = QVBoxLayout(self)
        info = QLabel(
            "자연어로 Top-3 우선순위 규칙을 입력하세요.\n"
            "예) \"박부장님 메일은 최우선\" 또는 \"버그 보고서는 우선순위 높게\""
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        if summary_text:
            summary_box = QTextEdit()
            summary_box.setReadOnly(True)
            summary_box.setPlainText(summary_text)
            summary_box.setStyleSheet("background:#F3F4F6; color:#1F2937;")
            summary_box.setFixedHeight(90)
            layout.addWidget(summary_box)

        self.editor = QTextEdit()
        self.editor.setPlaceholderText("규칙을 입력하세요...")
        if seed_text:
            self.editor.setPlainText(seed_text)
        layout.addWidget(self.editor, 1)

        self.reset_box = QCheckBox("기존 규칙 초기화")
        layout.addWidget(self.reset_box)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def rule_text(self) -> str:
        return self.editor.toPlainText().strip()

    def reset_requested(self) -> bool:
        return self.reset_box.isChecked()


# ─────────────────────────────────────────────────────────────────────────────
# 3) BasicTodoItem: 일반 TODO 카드
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
        
        # 수신 타입 배지 추가 (v1.2.1+)
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
        
        # 수신 타입 표시 (참조/직접 수신)
        recipient_badge = _create_recipient_type_badge(todo.get("recipient_type"))
        if recipient_badge:
            meta.addWidget(recipient_badge, 0)
        
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
        else:
            self.new_badge.hide()
            self.setStyleSheet(self._read_style)
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
    def __init__(self, db_path=TODO_DB_PATH, parent=None, top3_callback: Optional[Callable[[List[dict]], None]] = None):
        super().__init__(parent)

        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = get_conn(db_path)
        init_db(self.conn)

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
        self.top3_popup_btn = QPushButton("팝업으로 보기")
        self.top3_popup_btn.setEnabled(False)
        self.top3_popup_btn.clicked.connect(self.show_top3_dialog)
        top_header.addWidget(self.top3_label)
        top_header.addWidget(self.top3_rule_btn)
        top_header.addWidget(self.top3_nl_btn)
        top_header.addStretch(1)
        top_header.addWidget(self.top3_popup_btn)

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
        dialog = Top3RuleDialog(get_top3_rules(), self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            set_top3_rules(dialog.rules())
            _persist_top3_rules()
            self._rebuild_from_rows(self._all_rows or [])
            self._refresh_rule_tooltip()
            QMessageBox.information(self, "Top-3 기준", describe_top3_rules())

    def open_top3_nl_dialog(self) -> None:
        dialog = Top3NaturalRuleDialog(self, seed_text=_TOP3_LAST_INSTRUCTION, summary_text=describe_top3_rules())
        if dialog.exec() == QDialog.DialogCode.Accepted:
            text = dialog.rule_text()
            message, summary = apply_natural_language_rules(text, reset=dialog.reset_requested())
            self._rebuild_from_rows(self._all_rows or [])
            self._refresh_rule_tooltip()
            QMessageBox.information(self, "Top-3 자연어 규칙", f"{message}\n\n{summary}")

    def _refresh_rule_tooltip(self) -> None:
        summary = describe_top3_rules()
        if _TOP3_LAST_INSTRUCTION:
            summary += f"\n\n최근 자연어 규칙: {_TOP3_LAST_INSTRUCTION}"
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

        self._rebuild_from_rows(new_rows)

    def refresh_todo_list(self) -> None:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM todos WHERE status!='done' ORDER BY created_at DESC")
        rows = [dict(r) for r in cur.fetchall()]

        if not rows:
            if self._all_rows:
                # DB가 비어도 기존 메모리 상태를 유지
                self._set_render_lists(self._all_rows, self._top3_all or [], self._rest_all or [])
                return
            self._rebuild_from_rows([])
            return

        top_ids = _pick_top3(rows)
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
            self.top3_popup_btn.setEnabled(False)
            self._current_top3 = []
            return

        self.top3_label.setText(f"🔺 Top-3 (즉시 처리) · {len(top3)}")
        self.top3_popup_btn.setEnabled(True)
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

        top_ids = _pick_top3(cloned_rows)
        for row in cloned_rows:
            row_id = row.get("id")
            row["is_top3"] = 1 if row_id and row_id in top_ids else 0

        top3_items = sorted(
            [row for row in cloned_rows if row.get("id") in top_ids],
            key=lambda t: (_score_for_top3(t), _created_ts(t)),
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










