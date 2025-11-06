"""VDOS DB 프로젝트 정보 확인"""
import sqlite3

vdos_db = r"C:\Users\USER\Desktop\virtual-office-orchestration\virtualoffice\src\virtualoffice\vdos.db"
conn = sqlite3.connect(vdos_db)
cursor = conn.cursor()

# 테이블 목록
print("=" * 80)
print("VDOS DB 테이블 목록")
print("=" * 80)
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
for table in tables:
    print(f"- {table[0]}")

# project_assignments 테이블 확인
print("\n" + "=" * 80)
print("project_assignments 테이블 스키마")
print("=" * 80)
cursor.execute("PRAGMA table_info(project_assignments)")
columns = cursor.fetchall()
for col in columns:
    print(f"{col[1]} ({col[2]})")

# project_plans 테이블 확인
print("\n" + "=" * 80)
print("project_plans 테이블 스키마")
print("=" * 80)
cursor.execute("PRAGMA table_info(project_plans)")
columns = cursor.fetchall()
for col in columns:
    print(f"{col[1]} ({col[2]})")

# 프로젝트 정보 가져오기
print("\n" + "=" * 80)
print("프로젝트 정보")
print("=" * 80)
cursor.execute("""
    SELECT id, project_name, project_summary
    FROM project_plans
    ORDER BY id
""")
projects = cursor.fetchall()
for proj_id, name, summary in projects:
    print(f"ID {proj_id}: {name}")
    print(f"  요약: {summary[:100] if summary else 'N/A'}")
    print()

conn.close()
