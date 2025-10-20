# Smart Assistant v1.1.7 릴리스 노트

**릴리스 날짜**: 2025-10-17 (예정)

## 🎯 주요 개선사항

### 1. Azure OpenAI API 오류 수정

Azure OpenAI API 버전 오류를 수정하여 요약/회신 생성 기능이 정상 작동합니다.
- 잘못된 API 버전 `2025-04-01-preview` → 안정적인 `2024-08-01-preview`로 변경
- 400 Bad Request 오류 해결

### 2. 메일 탭 추가

TODO 가치가 있는 이메일만 필터링하여 표시하는 새로운 메일 탭을 추가했습니다.
- 요청/질문/확인/회의/마감 등 키워드 기반 자동 필터링
- 간결한 미리보기와 발신자 정보 표시
- 메신저와 분리하여 이메일만 별도 관리

### 3. 메시지 탭 개선

메신저 메시지만 일별/주간/월별 요약하여 빠른 결과를 제공합니다.
- 이메일은 메일 탭으로 분리
- 메신저 메시지만 빠르게 요약하여 성능 향상
- 일별/주간/월별 요약 단위 선택 가능

### 4. 스마트 메시지 필터링 (v1.1.6)

PM에게 **수신된** 메시지만 TODO로 변환하는 스마트 필터링 기능을 추가했습니다. 이제 PM이 **보낸** 메시지는 자동으로 제외되어 업무 관리 정확도가 크게 향상되었습니다.

## ✨ 새로운 기능

### 1. PM 수신 메시지 자동 필터링

#### 이메일 필터링
- **수신자 확인**: `to`, `cc`, `bcc` 필드에서 PM 이메일 주소 확인
- **자동 제외**: PM이 발신자인 이메일은 TODO로 변환되지 않음
- **정확한 판단**: 모든 수신자 필드를 종합적으로 확인

```python
# 이메일 필터링 로직
if msg_type == "email":
    recipients = msg.get("recipients", []) or []
    cc = msg.get("cc", []) or []
    bcc = msg.get("bcc", []) or []
    all_recipients = [r.lower() for r in (recipients + cc + bcc)]
    return pm_email in all_recipients
```

#### 메신저 필터링
- **DM 룸 확인**: DM 룸의 참여자 목록에서 PM 핸들 확인
- **그룹 채팅**: 기본적으로 포함 (추후 개선 예정)
- **룸 슬러그 파싱**: `dm:pm:designer` 형식에서 PM 핸들 추출

```python
# 메신저 필터링 로직
elif msg_type == "messenger":
    room_slug = (msg.get("room_slug") or "").lower()
    
    # DM 룸인 경우 PM handle이 포함되어 있는지 확인
    if room_slug.startswith("dm:"):
        room_parts = room_slug.split(":")
        return pm_handle in room_parts
    
    # 그룹 채팅은 일단 포함
    return True
```

### 2. 로깅 강화

필터링 전후 메시지 수를 로그로 출력하여 추적이 용이합니다:

```
👤 PM 필터링: email=pm.1@quickchat.dev, handle=pm
👤 PM 수신 메시지 필터링 완료: chat 753→108, email 1021→148
```

## 📝 변경된 파일

- `main.py`: `collect_messages()` 메서드에 PM 수신 메시지 필터링 로직 추가 (약 50줄)
- `README.md`: 스마트 메시지 필터링 기능 문서화
- `CHANGELOG.md`: v1.1.6 변경사항 추가
- `REFACTORING_SUMMARY.md`: 최신 변경사항 반영

## 🎬 사용 시나리오

### 시나리오 1: 이메일 수신
```
1. PM이 to 필드에 포함된 이메일 수신
2. 자동으로 TODO로 변환됨
3. PM이 발신한 이메일은 제외됨
```

### 시나리오 2: 메신저 DM
```
1. 디자이너가 PM에게 DM 발송 (dm:pm:designer)
2. PM이 참여자이므로 TODO로 변환됨
3. PM이 다른 사람에게 보낸 DM은 제외됨
```

### 시나리오 3: 그룹 채팅
```
1. 그룹 채팅 메시지는 기본적으로 포함
2. 추후 PM 멘션 확인 기능 추가 예정
```

## 🔄 업그레이드 방법

### 기존 사용자
```bash
# 저장소 업데이트
git pull origin main

# 의존성 확인 (변경 없음)
pip install -r requirements.txt

# 애플리케이션 실행
python run_gui.py
```

### 새로운 사용자
```bash
# 저장소 클론
git clone <repository-url>
cd smart_assistant

# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정
cp .env.example .env
# .env 파일 편집하여 API 키 설정

# 애플리케이션 실행
python run_gui.py
```

## 🐛 버그 수정

이번 릴리스에는 버그 수정이 포함되지 않았습니다. 새로운 기능 추가에 집중했습니다.

## 📊 성능 개선

- **필터링 효율성**: 리스트 컴프리헨션으로 효율적인 필터링
- **메모리 사용량**: 변경 없음
- **실행 속도**: 필터링 로직 추가로 약간의 오버헤드 발생 (무시할 수준)

## ⚠️ 주의사항

### PM 프로필 설정
- PM의 이메일 주소와 채팅 핸들이 `team_personas.json`에 올바르게 설정되어 있어야 합니다
- 기본값: `pm.1@quickchat.dev`, `pm`

### 그룹 채팅
- 현재 그룹 채팅은 모든 메시지를 포함합니다
- 추후 PM 멘션 확인 기능이 추가될 예정입니다

## 🔮 향후 계획

### v1.1.7 (예정)
- [ ] 그룹 채팅에서 PM 멘션 확인
- [ ] 메시지 발신자가 PM인 경우 명시적으로 제외
- [ ] 필터링 규칙을 설정 파일로 관리
- [ ] 필터링 통계 UI 표시

### v1.2.0 (예정)
- [ ] 분석 결과 UI 개선 (좌우 분할 레이아웃)
- [ ] TODO 영구 저장 옵션 추가
- [ ] 다국어 지원 (영어)

## 💡 사용 팁

### 1. PM 프로필 확인
`data/mobile_4week_ko/team_personas.json` 파일에서 PM 정보를 확인하세요:
```json
{
  "name": "Kim Jihoon",
  "email_address": "pm.1@quickchat.dev",
  "chat_handle": "pm",
  "role": "PM"
}
```

### 2. 필터링 로그 확인
콘솔 또는 로그 파일에서 필터링 결과를 확인할 수 있습니다:
```
👤 PM 수신 메시지 필터링 완료: chat 753→108, email 1021→148
```

### 3. 테스트
`test_todo_filtering.py` 스크립트로 필터링 로직을 테스트할 수 있습니다:
```bash
python test_todo_filtering.py
```

## 🙏 감사의 말

이번 릴리스는 사용자 피드백을 바탕으로 TODO 관리 정확도를 크게 개선했습니다. PM이 보낸 메시지가 TODO로 변환되는 문제를 해결하여 업무 관리가 더욱 효율적으로 개선되었습니다.

## 📞 지원

- 이슈 리포팅: GitHub Issues
- 문서: [README.md](README.md)
- 개발 가이드: [DEVELOPMENT.md](docs/DEVELOPMENT.md)

---

**전체 변경사항**: [v1.1.5...v1.1.6](https://github.com/yourusername/smart_assistant/compare/v1.1.5...v1.1.6)
