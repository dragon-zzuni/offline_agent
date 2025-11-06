"""
TODO DB에 project_full_name 컬럼 추가 및 데이터 마이그레이션
"""
import sqlite3
import os

# VDOS DB에서 프로젝트 정보 가져오기
vdos_db = r"C:\Users\USER\Desktop\virtual-office-orchestration\virtualoffice\src\virtualoffice\vdos.db"
vdos_conn = sqlite3.connect(vdos_db)
vdos_cursor = vdos_conn.cursor()

vdos_cursor.execute("SELECT id, project_name FROM project_plans")
projects = vdos_cursor.fetchall()

# 프로젝트 코드 매핑 (수동)
project_mapping = {
    20: ("CC", "Care Connect 2.0 리디자인"),
    21: ("HA", "HealthCore API 리팩토링"),
    22: ("WELL", "WellLink 브랜드 런칭 캠페인"),
    23: ("WI", "WellLink Insight Dashboard"),
    24: ("CI", "CareBridge Integration (CPO 주관)")
}

print("=" * 80)
print("프로젝트 매핑")
print("=" * 80)
for proj_id, (code, name) in project_mapping.items():
    print(f"{code}: {name}")

vdos_conn.close()

# TODO DB 업데이트
todo_db = r"C:\Users\USER\Desktop\virtual-office-orchestration\virtualoffice\src\virtualoffice\todos_cache.db"
todo_conn = sqlite3.connect(todo_db)
todo_cursor = todo_conn.cursor()

# 1. project_full_name 컬럼 추가 (이미 있으면 무시)
print("\n" + "=" * 80)
print("1. project_full_name 컬럼 추가")
print("=" * 80)
try:
    todo_cursor.execute("ALTER TABLE todos ADD COLUMN project_full_name TEXT")
    print("✅ project_full_name 컬럼 추가 완료")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("ℹ️ project_full_name 컬럼이 이미 존재합니다")
    else:
        raise

# 2. 기존 TODO에 project_full_name 업데이트
print("\n" + "=" * 80)
print("2. 기존 TODO에 project_full_name 업데이트")
print("=" * 80)

code_to_fullname = {code: name for _, (code, name) in project_mapping.items()}

for code, fullname in code_to_fullname.items():
    todo_cursor.execute("""
        UPDATE todos
        SET project_full_name = ?
        WHERE project = ? AND (project_full_name IS NULL OR project_full_name = '')
    """, (fullname, code))
    
    updated = todo_cursor.rowcount
    if updated > 0:
        print(f"✅ {code} → {fullname}: {updated}개 TODO 업데이트")

todo_conn.commit()

# 3. 결과 확인
print("\n" + "=" * 80)
print("3. 업데이트 결과 확인")
print("=" * 80)

todo_cursor.execute("""
    SELECT project, project_full_name, COUNT(*) as cnt
    FROM todos
    GROUP BY project, project_full_name
    ORDER BY project
""")

results = todo_cursor.fetchall()
for project, fullname, cnt in results:
    print(f"{project}: {fullname} ({cnt}개)")

todo_conn.close()

print("\n" + "=" * 80)
print("✅ 마이그레이션 완료!")
print("=" * 80)
