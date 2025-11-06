"""
vdos.db에서 페르소나와 메시지 매핑 확인
"""
import sqlite3

vdos_db = "C:/Users/USER/Desktop/virtual-office-orchestration/virtualoffice/src/virtualoffice/vdos.db"

conn = sqlite3.connect(vdos_db)
cursor = conn.cursor()

print("=" * 80)
print("VDOS DB 페르소나 정보")
print("=" * 80)

# 페르소나 테이블 확인
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print(f"\n테이블 목록: {[t[0] for t in tables]}")

# people 테이블 확인
if ('people',) in tables:
    cursor.execute("SELECT id, name, email_address, chat_handle FROM people LIMIT 20")
    people = cursor.fetchall()
    print(f"\n👥 People 테이블 ({len(people)}명):")
    for person_id, name, email, handle in people:
        print(f"  {person_id:3} | {name:15} | {email:35} | {handle}")

# 특정 페르소나 확인
print("\n" + "=" * 80)
print("주요 페르소나 상세 확인")
print("=" * 80)

target_names = ['이정두', '김용준', '정지원']
for name in target_names:
    cursor.execute("SELECT id, name, email_address, chat_handle FROM people WHERE name = ?", (name,))
    person = cursor.fetchone()
    if person:
        person_id, pname, email, handle = person
        print(f"\n👤 {pname} (ID: {person_id}):")
        print(f"   이메일: {email}")
        print(f"   채팅 핸들: {handle}")
        
        # 이 페르소나가 받은 이메일 개수 확인
        if ('emails',) in tables:
            cursor.execute("SELECT COUNT(*) FROM emails WHERE recipient_address = ?", (email,))
            email_count = cursor.fetchone()[0]
            print(f"   받은 이메일: {email_count}개")
        
        # 이 페르소나가 받은 메시지 개수 확인
        if ('messages',) in tables:
            cursor.execute("SELECT COUNT(*) FROM messages WHERE recipient_handle = ?", (handle,))
            msg_count = cursor.fetchone()[0]
            print(f"   받은 메시지: {msg_count}개")
    else:
        print(f"\n❌ {name}: DB에서 찾을 수 없음")

# 김용준이 받은 이메일 샘플 확인
print("\n" + "=" * 80)
print("김용준이 받은 이메일 샘플 (최근 5개)")
print("=" * 80)

cursor.execute("""
    SELECT id, sender_address, recipient_address, subject 
    FROM emails 
    WHERE recipient_address = 'yongjun.kim@company.com' 
    ORDER BY id DESC 
    LIMIT 5
""")
emails = cursor.fetchall()

if emails:
    for email_id, sender, recipient, subject in emails:
        print(f"\n이메일 ID: {email_id}")
        print(f"  발신자: {sender}")
        print(f"  수신자: {recipient}")
        print(f"  제목: {subject[:60]}")
else:
    print("\n김용준이 받은 이메일이 없습니다.")

# 정지원이 받은 이메일 샘플 확인
print("\n" + "=" * 80)
print("정지원이 받은 이메일 샘플 (최근 5개)")
print("=" * 80)

# 먼저 정지원의 이메일 주소 확인
cursor.execute("SELECT email_address FROM people WHERE name = '정지원'")
jiwon_email_result = cursor.fetchone()

if jiwon_email_result:
    jiwon_email = jiwon_email_result[0]
    print(f"정지원 이메일: {jiwon_email}")
    
    cursor.execute("""
        SELECT id, sender_address, recipient_address, subject 
        FROM emails 
        WHERE recipient_address = ? 
        ORDER BY id DESC 
        LIMIT 5
    """, (jiwon_email,))
    emails = cursor.fetchall()
    
    if emails:
        for email_id, sender, recipient, subject in emails:
            print(f"\n이메일 ID: {email_id}")
            print(f"  발신자: {sender}")
            print(f"  수신자: {recipient}")
            print(f"  제목: {subject[:60]}")
    else:
        print(f"\n정지원({jiwon_email})이 받은 이메일이 없습니다.")
else:
    print("\n정지원을 DB에서 찾을 수 없습니다.")

conn.close()
