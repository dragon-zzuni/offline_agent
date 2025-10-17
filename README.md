# Smart Assistant

오프라인 데이터셋(`data/mobile_4week_ko`)을 기반으로 모바일 앱 팀의 이메일·메신저 대화를 분석하고, PM 시점의 TODO를 자동 생성하는 데스크톱 도우미입니다. 네트워크가 없는 환경에서도 최신 데이터를 수동으로 불러오고, 온라인으로 전환되면 한 번 자동으로 전체 분석을 수행합니다.

## 🚀 주요 기능
- **📚 오프라인 메시지 로딩**: `chat_communications.json` / `email_communications.json` / `team_personas.json`을 읽어 최신 대화와 인물 정보를 통합합니다.
- **🤖 LLM 기반 분석 파이프라인**: 메시지 요약, 우선순위 산정, 액션 추출까지 한 번에 수행합니다.
- **📋 TODO 보드**: 추출된 업무를 우선순위/근거/드래프트와 함께 저장하고, PyQt6 UI에서 즉시 확인·편집·완료 처리할 수 있습니다.
- **🔁 온라인 모드 감지**: 오프라인에서 작업하다가 온라인으로 전환되면 자동으로 한 차례 데이터를 재분석합니다. 온라인 상태에서도 필요 시 수동으로 재실행할 수 있습니다.

## 📁 프로젝트 구조
```
smart_assistant/
├── config/                 # 전역 설정 (경로, LLM, UI 등)
├── data/
│   └── mobile_4week_ko/    # 오프라인 데이터셋 (chat/email/persona/final_state)
├── logs/                   # 실행 로그
├── nlp/                    # 요약, 우선순위, 액션 추출 모듈
├── tools/                  # 보조 스크립트
├── ui/                     # PyQt6 기반 GUI 컴포넌트
├── main.py                 # SmartAssistant 코어 엔진
├── run_gui.py              # GUI 실행 스크립트
└── requirements.txt        # 의존성 목록
```

## 🛠️ 설치
```bash
pip install -r requirements.txt
```

데이터셋은 `data/mobile_4week_ko`에 포함되어 있으며, 추가 설정 없이 바로 사용할 수 있습니다. LLM API 키(OpenAI 등)를 환경변수로 설정하면 고급 요약/추출 기능을, 설정하지 않으면 기본 휴리스틱 기반 파이프라인을 사용합니다.

## ⚙️ 사용 방법
### GUI 실행
```bash
python run_gui.py
```
- 좌측 패널에서 현재 데이터셋 경로와 상태를 확인하고, `메시지 수집 시작` 버튼으로 분석을 실행합니다.
- 온라인 상태로 전환하면 자동으로 한 번 분석이 트리거되며, 이후에는 필요할 때마다 수동 실행이 가능합니다.
- TODO 탭에서 우선순위, 근거, 초안 등의 정보를 확인·편집할 수 있습니다.

### 코드에서 사용
```python
import asyncio
from main import SmartAssistant, DEFAULT_DATASET_ROOT

async def main():
    assistant = SmartAssistant()

    dataset_config = {
        "dataset_root": str(DEFAULT_DATASET_ROOT),
        "force_reload": True,
    }
    collect_options = {
        "messenger_limit": 40,
        "email_limit": 40,
        "force_reload": True,
    }

    result = await assistant.run_full_cycle(dataset_config, collect_options)

    if result.get("success"):
        todo_list = result["todo_list"]
        print(f"생성된 TODO 수: {todo_list['summary']['total']}개")
        for item in todo_list["items"][:5]:
            print(f"- [{item['priority']}] {item['title']}")
    else:
        print("오류:", result.get("error"))

asyncio.run(main())
```

## 📂 데이터셋 구성
| 파일 | 설명 |
| --- | --- |
| `chat_communications.json` | 팀 DM 로그 (sender, room_slug, sent_at 등) |
| `email_communications.json` | 팀 메일 기록 (sender, recipients, body 등) |
| `team_personas.json` | PM/디자이너/개발자/DevOps 인물 정보 |
| `final_state.json` | 시뮬레이션 상태 (tick, sim_time 등) |

애플리케이션은 이 JSON들만으로 동작하며, 로그인이나 외부 API 호출이 필요 없습니다.

## 📊 출력 예시
```
📦 총 58개 메시지 수집 (chat 35, email 23)
🎯 우선순위 분포: High 6 / Medium 14 / Low 8
🔥 상위 TODO
- [HIGH] 김민수님 오전 일정 정리 및 고객 피드백 요청
- [HIGH] 프로토타입 초안 내부 리뷰 준비
- [MEDIUM] 서버 검증 결과 요약 메일 발송
```

## 🔄 TODO 저장소
- 생성된 TODO는 `data/mobile_4week_ko/todos_cache.db`(SQLite)에 저장됩니다.
- `ui/todo_panel.py`에서 항목 상태 변경, 스누즈, Top3 재계산 등을 지원합니다.

## 🗺️ 향후 개선 아이디어
- [ ] 데이터셋 교체/버전 선택 UI
- [ ] 분석 결과 리포트 PDF/Markdown 자동 생성
- [ ] QA용 자동 테스트 스크립트
- [ ] 추가 언어(EN) 대응

## 📝 라이선스 & 기여
- MIT License
- 버그/개선 아이디어는 Issue 또는 PR로 환영합니다!
