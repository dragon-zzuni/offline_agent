# drafts.py (새 파일)
from datetime import datetime

def build_email_draft(todo: dict, user_profile: dict | None = None) -> tuple[str, str]:
    """(subject, body) 반환. user_profile 로 말투/서명 개인화 가능."""
    title = todo.get("title","")
    requester = todo.get("requester","")
    deadline = todo.get("deadline_ts","")
    proj = todo.get("project","")
    greeting = "안녕하세요," if not user_profile else user_profile.get("greeting","안녕하세요,")

    subject = f"[확인 요청] {title}" if proj is None else f"[{proj}] {title} 건"
    body = (
        f"{greeting} {requester}님,\n\n"
        f"{title} 건 관련하여 아래와 같이 확인 및 회신드립니다.\n"
        f"- 데드라인: {deadline or '미기재'}\n"
        f"- 주요 포인트: {', '.join(todo.get('key_points', [])) if todo.get('key_points') else '요점 정리 예정'}\n\n"
        "추가로 필요한 사항이 있으면 말씀 부탁드립니다.\n\n"
        "--\n"
        "보낸이 서명(자동)\n"
    )
    return subject, body
