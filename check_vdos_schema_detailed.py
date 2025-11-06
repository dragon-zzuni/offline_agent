"""
vdos.db 스키마 상세 확인
"""
import sqlite3

vdos_db = "C:/Users/USER/Desktop/virtual-office-orchestration/virtualoffice/src/virtualoffice/vdos.db"

conn = sqlite3.connect(vdos_db)
cursor = conn.cursor()

print("=" * 80)
print("emails 테이블 스키마")
print("=" * 80)

cursor.execute("PRAGMA table_info(emails)")
columns = cursor.fetchall()
for col in columns:
    print(f"  {col[1]:20} {col[2]:15}")

print("\n" + "=" * 80)
print("email_recipients 테이블 스키마")
print("=" * 80)

cursor.execute("PRAGMA table_info(email_recipients)")
columns = cursor.fetchall()
for col in columns:
    print(f"  {col[1]:20} {col[2]:15}")

print("\n" + "=" * 80)
print("김용준 관련 이메일 확인")
print("=" * 80)

# 김용준이 수신자인 이메일 찾기 (email_recipients 테이블 사용)
cursor.execute("""
    SELECT e.id, e.sender, e.subject, er.address, er.kind
    FROM emails e
    JOIN email_recipients er ON e.id = er.email_id
    WHERE er.address = 'yongjun.kim@company.com'
    ORDER BY e.id DESC
    LIMIT 5
""")

emails = cursor.fetchall()
print(f"\n김용준(yongjun.kim@company.com)이 받은 이메일: {len(emails)}개 (샘플)")

for email_id, sender, subject, recipient, rec_type in emails:
    print(f"\n이메일 ID: {email_id}")
    print(f"  발신자: {sender}")
    print(f"  수신자: {recipient} ({rec_type})")
    print(f"  제목: {subject[:60]}")

print("\n" + "=" * 80)
print("정지원 관련 이메일 확인")
print("=" * 80)

# 정지원이 수신자인 이메일 찾기
cursor.execute("""
    SELECT e.id, e.sender, e.subject, er.address, er.kind
    FROM emails e
    JOIN email_recipients er ON e.id = er.email_id
    WHERE er.address = 'jungjiwon@koreaitcompany.com'
    ORDER BY e.id DESC
    LIMIT 5
""")

emails = cursor.fetchall()
print(f"\n정지원(jungjiwon@koreaitcompany.com)이 받은 이메일: {len(emails)}개 (샘플)")

for email_id, sender, subject, recipient, rec_type in emails:
    print(f"\n이메일 ID: {email_id}")
    print(f"  발신자: {sender}")
    print(f"  수신자: {recipient} ({rec_type})")
    print(f"  제목: {subject[:60]}")

conn.close()
