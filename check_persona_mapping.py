"""
페르소나 이름-이메일 매핑 확인
"""
import json

# VDOS 페르소나 파일 로드
with open('virtualoffice/src/virtualoffice/vdos-personas-2025-10-31.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
    personas = data['personas']

print("=" * 80)
print("VDOS 페르소나 이름-이메일 매핑")
print("=" * 80)

for p in personas:
    name = p.get('name', 'N/A')
    email = p.get('email_address', 'N/A')
    handle = p.get('chat_handle', 'N/A')
    print(f"{name:15} | {email:35} | {handle}")

# 특정 페르소나 확인
print("\n" + "=" * 80)
print("주요 페르소나 상세 정보")
print("=" * 80)

target_names = ['이정두', '김용준', '정지원']
for name in target_names:
    persona = next((p for p in personas if p.get('name') == name), None)
    if persona:
        print(f"\n👤 {name}:")
        print(f"   이메일: {persona.get('email_address')}")
        print(f"   채팅 핸들: {persona.get('chat_handle')}")
        print(f"   역할: {persona.get('role')}")
    else:
        print(f"\n❌ {name}: 페르소나를 찾을 수 없음")
