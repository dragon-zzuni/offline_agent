# tools/import_chat_logs.py
from pathlib import Path
import os, csv, sqlite3

PROJECT_ROOT = Path(__file__).resolve().parents[1]
IMPORT_DIR   = PROJECT_ROOT / "data" / "messenger" / "import"
DB_PATH      = Path(os.getenv("MESSENGER_DB_PATH", PROJECT_ROOT / "data" / "messenger" / "messages.db"))

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS messages (
  id        INTEGER PRIMARY KEY,
  room      TEXT,
  username  TEXT,
  message   TEXT,
  timestamp TEXT,
  type      TEXT,
  url       TEXT,
  filename  TEXT,
  color     TEXT
);
CREATE INDEX IF NOT EXISTS idx_messages_room_time ON messages(room, timestamp);
"""

def ensure_db(conn):
    conn.executescript(SCHEMA_SQL)
    conn.commit()

def parse_psv_table(txt_path: Path):
    """
    파이프(|) 구분의 마크다운 표 형태를 파싱.
    1행: 헤더, 2행: --- 구분선, 3행~: 데이터
    """
    rows = []
    with txt_path.open("r", encoding="utf-8") as f:
        lines = [ln.strip() for ln in f.readlines() if ln.strip()]
    # 표 형태 라인만 추출 (| 로 시작하고 끝나는 줄)
    table_lines = [ln for ln in lines if ln.startswith("|") and ln.endswith("|")]
    if not table_lines:
        return rows

    def split_line(line: str):
        # 양쪽 파이프 제거 후 '|' 기준 분리
        parts = [c.strip() for c in line.strip("|").split("|")]
        return parts

    header = split_line(table_lines[0])
    # 두 번째 줄이 구분선(---)인지 확인
    data_start_idx = 2 if all(set(c) <= set("-: ") for c in split_line(table_lines[1])) else 1

    for line in table_lines[data_start_idx:]:
        parts = split_line(line)
        # 컬럼 수 어긋남 방어: 초과분은 마지막 컬럼에 합치기, 부족하면 패딩
        if len(parts) > len(header):
            parts = parts[:len(header)-1] + ["|".join(parts[len(header)-1:])]
        elif len(parts) < len(header):
            parts = parts + [""] * (len(header) - len(parts))
        row = dict(zip(header, parts))
        rows.append(row)
    return rows

def upsert_rows(conn, rows):
    """
    id PRIMARY KEY 기준으로 UPSERT
    """
    sql = """
    INSERT INTO messages (id, room, username, message, timestamp, type, url, filename, color)
    VALUES (:id, :room, :username, :message, :timestamp, :type, :url, :filename, :color)
    ON CONFLICT(id) DO UPDATE SET
      room=excluded.room,
      username=excluded.username,
      message=excluded.message,
      timestamp=excluded.timestamp,
      type=excluded.type,
      url=excluded.url,
      filename=excluded.filename,
      color=excluded.color;
    """
    # 키 이름 정규화 (공백/대소문자 편차 방지)
    norm = lambda d, k: d.get(k) or d.get(k.lower()) or d.get(k.upper()) or ""
    for r in rows:
        payload = {
            "id":        int(norm(r, "id")) if str(norm(r, "id")).strip().isdigit() else None,
            "room":      norm(r, "room"),
            "username":  norm(r, "username"),
            "message":   norm(r, "message"),
            "timestamp": norm(r, "timestamp"),
            "type":      norm(r, "type"),
            "url":       norm(r, "url"),
            "filename":  norm(r, "filename"),
            "color":     norm(r, "color"),
        }
        if payload["id"] is None:
            continue
        conn.execute(sql, payload)

def main():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        ensure_db(conn)
        txt_files = sorted(IMPORT_DIR.glob("*.txt"))
        if not txt_files:
            print(f"[INFO] no txt in {IMPORT_DIR}")
            return
        total = 0
        for p in txt_files:
            rows = parse_psv_table(p)
            upsert_rows(conn, rows)
            conn.commit()
            print(f"[OK] {p.name}: {len(rows)} rows")
            total += len(rows)
        print(f"[DONE] inserted/updated: {total} rows into {DB_PATH}")

if __name__ == "__main__":
    main()
