"""
DB 직접 확인
"""
import sqlite3

db_path = "C:/Users/USER/Desktop/virtual-office-orchestration/virtualoffice/src/virtualoffice/todos_cache.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 전체 TODO 조회
cursor.execute("SELECT id, title, persona_name, requester FROM todos LIMIT 10")
rows = cursor.fetchall()

print(f"DB 경로: {db_path}")
print(f"전체 TODO 개수: {len(rows)}")
print("\n최근 10개 TODO:")
for row in rows:
    print(f"  - {row[0]}: {row[1]} (페르소나: {row[2]}, 요청자: {row[3]})")

# 페르소나별 통계
cursor.execute("SELECT persona_name, COUNT(*) FROM todos GROUP BY persona_name")
stats = cursor.fetchall()
print("\n페르소나별 통계:")
for persona, count in stats:
    print(f"  - {persona or 'NULL'}: {count}개")

conn.close()
