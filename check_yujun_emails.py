import sqlite3

conn = sqlite3.connect('C:/Users/USER/Desktop/virtual-office-orchestration/virtualoffice/src/virtualoffice/vdos.db')
cursor = conn.cursor()

# 유준영이 보낸 최근 이메일 확인
cursor.execute('''
    SELECT id, subject, body, sent_at
    FROM emails 
    WHERE sender = 'yujunyoung@example.com'
    ORDER BY sent_at DESC 
    LIMIT 5
''')

print('=== 유준영이 보낸 최근 이메일 ===\n')
for idx, row in enumerate(cursor.fetchall(), 1):
    email_id, subject, body, sent_at = row
    print(f'[{idx}] ID: email_{email_id}')
    print(f'제목: {subject}')
    print(f'날짜: {sent_at}')
    print(f'내용:\n{body}')
    print('=' * 100)
    print()

conn.close()
