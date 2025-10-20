# Changelog

Smart Assistant의 모든 주요 변경사항이 이 파일에 문서화됩니다.

형식은 [Keep a Changelog](https://keepachangelog.com/ko/1.0.0/)를 기반으로 하며,
이 프로젝트는 [Semantic Versioning](https://semver.org/lang/ko/)을 따릅니다.

## [Unreleased]

## [1.2.1+++++++++++] - 2025-10-20

### 개선됨
- **🎨 메시지 요약 패널 코드 정리**: 디버그 로그 제거 및 코드 간소화
  - `_format_period()` 메서드에서 불필요한 디버그 출력 제거
  - 예외 처리 간소화 (오류 메시지 출력 제거)
  - 코드 가독성 향상 및 성능 최적화
  - 날짜 형식 표시 로직 간결화
  - 일별: "2025년 10월 20일 (월)"
  - 주별: "2025년 10/14 ~ 10/20" (동일 연도) 또는 "2025년 10/14 ~ 2026년 01/03" (연도 다름)
  - 월별: "2025년 10월"

### 기술적 변경
- `ui/message_summary_panel.py`: `_format_period()` 메서드 정리
  - 디버그 로그 제거 (print 문 삭제)
  - 예외 처리 간소화 (Exception as e → Exception)
  - 중복 코드 제거 및 직접 반환 패턴 적용
  - 약 20줄의 디버그 코드 제거로 성능 향상

### 문서
- README.md 메시지 그룹화 섹션 업데이트
  - 깔끔한 날짜 표시 기능 추가
  - 예외 처리 강화 명시
  - 날짜 형식 예시 추가

## [1.2.1+++++++++] - 2025-10-20

### 개선됨
- **👥 발신자별 우선순위 맵 추가**: 메시지 요약에 발신자별 최고 우선순위 정보 포함
  - 각 발신자의 최고 우선순위를 자동 계산하여 `sender_priority_map`에 저장
  - MessageSummaryPanel에서 색상 코딩된 배지로 표시
  - High 우선순위: 빨간색 배지 (#High)
  - Medium 우선순위: 노란색 배지 (#Medium)
  - Low 우선순위: 회색 배지 (태그 없음)
  - 우선순위 순서: High(3) > Medium(2) > Low(1)
- **📝 간결한 요약 추가**: `brief_summary` 필드를 요약 딕셔너리에 추가
  - 1-2줄로 핵심 내용을 빠르게 파악
  - 총 메시지 수, 이메일/메신저 구분, 주요 발신자 정보 포함

### 기술적 변경
- `ui/main_window.py`: `_update_message_summaries()` 메서드 개선
  - 발신자별 우선순위 계산 로직 추가
  - 분석 결과에서 우선순위 정보 추출
  - 최고 우선순위 유지 로직 구현
  - `sender_priority_map`과 `brief_summary`를 딕셔너리에 추가
  - GroupedSummary 객체를 딕셔너리로 변환하여 추가 정보 포함

### 문서
- README.md 메시지 그룹화 섹션 업데이트
  - 발신자별 우선순위 맵 기능 추가
  - 사용 예시 코드 업데이트
  - 주요 개선사항 명시
- UPDATE_SUMMARY_v1.2.1+++++++++.md 추가
- REFACTORING_v1.2.1+++++++++_SUMMARY.md 추가

### 개선됨 (이전 버전)
- **📝 로깅 시스템 개선**: 모든 주요 모듈에 로거 추가
  - `ui/main_window.py`에 로거 초기화 추가
  - 모듈별 독립적인 로거 사용으로 디버깅 용이성 향상
  - 일관된 로깅 패턴 적용
- **🕐 분석 결과 패널 수신 시간 표시**: 메시지 카드에 수신 시간 정보 추가
  - 형식: 🕐 수신: YYYY-MM-DD HH:MM
  - ISO 8601 형식 자동 파싱
  - 파싱 실패 시 조용히 무시 (에러 없음)
  - 시각적으로 구분되는 스타일 (회색, 이탤릭체)

## [1.2.1+++++++] - 2025-10-20

### 개선됨
- **🎨 좌측 패널 너비 추가 최적화**: 250px에서 220px로 추가 축소하여 공간 효율성 극대화
  - 우측 결과 패널이 30px 더 넓어져 정보 가독성 추가 향상
  - TODO 리스트, 메시지 요약, 분석 결과가 더욱 넓게 표시됨
  - 좌측 패널은 여전히 모든 컨트롤에 접근 가능 (스크롤 지원)
  - 1920x1080 해상도에서 우측 패널 1570px → 1600px로 확대
  - 단계적 최적화: 350px → 250px → 220px

### 기술적 변경
- `ui/main_window.py`: `create_left_panel()` 메서드 수정
  - `scroll_area.setMaximumWidth(220)` (250 → 220)
  - `scroll_area.setMinimumWidth(220)` (250 → 220)
  - 주석 업데이트 (한국어)

### 문서
- README.md UI 구성 섹션 업데이트
  - 좌측 패널 너비 220px로 수정
  - 단계적 최적화 내용 추가
- UPDATE_SUMMARY_v1.2.1+++++++.md 추가
- REFACTORING_v1.2.1+++++++_SUMMARY.md 추가

## [1.2.1++++++] - 2025-10-20

### 개선됨
- **🎨 좌측 패널 너비 최적화**: 350px에서 250px로 축소하여 공간 효율성 향상
  - 우측 결과 패널이 100px 더 넓어져 정보 가독성 대폭 향상
  - TODO 리스트, 메시지 요약, 분석 결과가 더 넓게 표시됨
  - 좌측 패널은 여전히 모든 컨트롤에 접근 가능 (스크롤 지원)
  - 1920x1080 해상도에서 우측 패널 1570px → 1670px로 확대

### 기술적 변경
- `ui/main_window.py`: `create_left_panel()` 메서드 수정
  - `scroll_area.setMaximumWidth(250)` (350 → 250)
  - `scroll_area.setMinimumWidth(250)` (350 → 250)
  - 주석 업데이트 (한국어)

### 문서
- README.md UI 구성 섹션 업데이트
  - 좌측 패널 너비 250px로 수정
  - 공간 효율성 개선 내용 추가
- UPDATE_SUMMARY_v1.2.1++++++.md 추가
- REFACTORING_v1.2.1++++++_SUMMARY.md 추가

## [1.2.1+++++] - 2025-10-20

### 추가됨
- **📊 AnalysisResultPanel 컴포넌트**: 분석 결과를 좌우 분할 레이아웃으로 표시
  - 좌측 요약 영역: 전체 통계, 우선순위 분포, 주요 발신자 TOP5
  - 우측 상세 영역: 우선순위별 메시지 카드 (High/Medium/Low 섹션)
  - QSplitter로 비율 조절 가능 (기본 30:70)
  - 카드 형태의 직관적인 메시지 표시
  - 호버 효과로 시각적 피드백 제공
  - 메시지 타입 아이콘 (📧 이메일, 💬 메신저)
  - 액션 수 표시 (📋 액션 N개)
  - 우선순위별 색상 코딩 (High: 빨강, Medium: 노랑, Low: 회색)
  - 최대 10개 메시지만 표시 (성능 최적화)

### 개선됨
- **🎨 UI 스타일 시스템 활용**: AnalysisResultPanel이 중앙 집중식 스타일 시스템 사용
  - `ui/styles.py`의 Colors, FontSizes, FontWeights, Spacing, BorderRadius 활용
  - 일관된 디자인 언어 적용
  - 유지보수성 향상

### 기술적 변경
- `ui/analysis_result_panel.py`: 신규 파일 추가 (586줄)
  - `AnalysisResultPanel` 클래스: 메인 패널 컴포넌트
  - `_create_summary_panel()`: 좌측 요약 영역 생성
  - `_create_detail_panel()`: 우측 상세 영역 생성
  - `update_analysis()`: 분석 결과 업데이트 메서드
  - `_create_stats_card()`: 전체 통계 카드 생성
  - `_create_priority_distribution_card()`: 우선순위 분포 카드 생성
  - `_create_top_senders_card()`: 주요 발신자 카드 생성
  - `_create_priority_section()`: 우선순위 섹션 생성
  - `_create_message_card()`: 메시지 카드 생성

### 문서
- README.md 업데이트
  - AnalysisResultPanel 사용법 추가
  - 프로젝트 구조에 analysis_result_panel.py 추가
  - 우측 패널 설명 업데이트
  - 주요 기능에 분석 결과 패널 추가

## [1.2.1++++] - 2025-10-20

### 개선됨
- **🎨 UI 레이아웃 최적화**: 좌우 패널 stretch factor 조정
  - 좌측 패널: stretch factor 0 (고정 크기)
  - 우측 패널: stretch factor 1 (확장 가능)
  - 창 크기 조절 시 좌측 패널은 고정, 우측 패널만 확장/축소
  - 일관된 UI 경험 제공
  - 좌측 제어 패널의 너비가 항상 350px로 유지됨
  - 우측 결과 패널이 남은 공간을 모두 활용하여 더 많은 정보 표시 가능

### 기술적 변경
- `ui/main_window.py`: 
  - `init_ui()` 메서드의 레이아웃 stretch factor 조정
  - 좌측 패널: `main_layout.addWidget(left_panel, 0)` (고정)
  - 우측 패널: `main_layout.addWidget(right_panel, 1)` (확장)

## [1.2.1+++] - 2025-10-20

### 개선됨
- **📜 좌측 패널 스크롤 지원**: 많은 컨트롤이 있어도 편리하게 접근 가능
  - `QScrollArea`를 사용하여 좌측 패널을 스크롤 가능하게 개선
  - 수직 스크롤만 활성화 (필요시 자동 표시)
  - 수평 스크롤 비활성화로 레이아웃 안정성 향상
  - 최소/최대 너비 350px로 고정
  - 프레임 스타일 제거로 시각적 간결성 향상
  - 화면 크기가 작아도 모든 컨트롤에 접근 가능
  - 사용자 경험 대폭 향상

### 문서
- README.md 업데이트 (UI 구성 섹션)
- HOTFIX_LEFT_PANEL_SCROLL.md 추가

## [1.2.1++] - 2025-10-20

### 개선됨
- **📊 MessageSummaryPanel 호환성 개선**: GroupedSummary 객체와 딕셔너리 모두 지원
  - `_format_period()` 메서드가 GroupedSummary 객체의 속성과 딕셔너리 키 모두 처리
  - 타입 체크 로직 추가로 유연성 향상
  - 하위 호환성 유지

## [1.2.1] - 2025-10-20

### 추가됨
- **⏰ 시간 범위 선택기 통합**: 왼쪽 제어 패널에 시간 범위 선택 위젯 추가
  - 시작/종료 시간 직접 입력 가능
  - 빠른 선택 버튼 (최근 1시간, 4시간, 오늘, 어제, 최근 7일, 전체 기간)
  - 시간 범위 변경 시 자동으로 메시지 필터링 옵션에 저장
  
- **📨 메시지 탭 개선**: MessageSummaryPanel로 전면 교체
  - 일별/주별/월별 요약 단위 선택 가능
  - 카드 형태로 그룹화된 메시지 표시
  - 발신자별 우선순위 배지 (High/Medium/Low)
  - 간결한 요약 (1-2줄) 및 주요 포인트 자동 추출 (최대 3개)
  
- **📧 수신 타입 구분 표시**: TODO 리스트에서 참조(CC)/직접 수신(TO) 구분
  - TODO 카드에 수신 타입 배지 표시 (참조(CC), 숨은참조(BCC))
  - TODO 상세 다이얼로그에 수신 타입 정보 표시
  - 데이터베이스에 `recipient_type` 컬럼 추가 (자동 마이그레이션)

### 변경됨
- **🗑️ 타임라인 탭 제거**: 사용 빈도가 낮아 제거
  - TODO, 메시지, 분석 결과 3개 탭만 유지
  - UI 간소화 및 사용자 경험 개선
  
- **⚖️ CC 메일 가중치 조정**: TOP3 우선순위 계산 시 참조 메일 가중치 낮춤
  - 참조(CC) 수신 메일: 가중치 30% 감소 (0.7 배수)
  - 숨은참조(BCC) 수신 메일: 가중치 37% 감소 (0.63 배수)
  - 직접 수신한 중요 메일이 TOP3에 우선 표시됨

### 수정됨
- **⏰ 시간 범위 필터링**: 정상 작동 확인
  - 최근 7일, 특정 기간, 시작/종료 시간 필터 모두 정상 작동
  - 필터링 로그 개선으로 디버깅 용이

### 기술적 변경
- `ui/main_window.py`: 
  - TimeRangeSelector 통합 및 시간 범위 변경 핸들러 추가
  - MessageSummaryPanel 통합 및 요약 단위 변경 핸들러 추가
  - 타임라인 탭 제거
  - 메시지 그룹화 및 요약 생성 로직 추가
- `main.py`: 메시지 수집 시 `recipient_type` 필드 설정
- `ui/todo_panel.py`: CC 패널티 적용, UI 배지 표시, DB 스키마 업데이트
- 테스트 파일 추가: `test_recipient_type.py`, `test_time_range_filtering.py`

### 변경됨
- **📁 데이터셋 변경**: 기본 데이터셋을 `multi_project_8week_ko`로 변경 (v1.2.0)
  - 기존: mobile_4week_ko (4주 데이터, 모바일 앱 팀)
  - 신규: multi_project_8week_ko (8주 데이터, 멀티 프로젝트 팀)
  - PM 이메일: pm.1@multiproject.dev
  - 팀 구성: PM, 디자이너, 개발자, DevOps (4명)
  - 마이그레이션 가이드: [DATASET_MIGRATION.md](docs/DATASET_MIGRATION.md)

### 변경됨
- **💾 TODO 영구 저장**: 앱 재시작 시에도 TODO가 유지됩니다 (v1.1.9+)
  - 기존: 앱 시작 시 모든 TODO 자동 삭제
  - 개선: 앱 시작 시 TODO 유지 (14일 이상 된 것만 자동 정리)
  - 사용자가 원하면 수동으로 "모두 삭제" 버튼 사용 가능
  - 탭 전환 시에도 TODO 유지
  - 데이터 손실 방지 및 사용자 경험 개선

### 추가됨
- **🎯 주제 기반 메시지 요약**: 메시지 내용에서 주요 주제를 자동으로 추출 (v1.1.8++)
  - `_extract_topics_from_messages()` 메서드 추가
  - 10개 주제 카테고리 지원 (미팅, 보고서, 검토, 개발, 버그, 배포, 테스트, 디자인, 일정, 승인)
  - 한글 + 영어 키워드 동시 지원 (30개 이상의 키워드)
  - 최대 20개 메시지 분석으로 성능 최적화
  - Counter 기반 효율적인 주제 카운팅

### 개선됨
- **🔍 LLM 호출 디버깅 강화**: TODO 상세 다이얼로그 LLM 호출 로깅 및 에러 처리 개선 (v1.1.9)
  - 타임아웃 30초 → 60초로 확대
  - 상세한 로그 출력 (URL, 페이로드, 응답 상태, 생성 길이)
  - 에러 타입별 구분 처리 (Timeout, HTTPError, JSONDecodeError)
  - 사용자 친화적인 에러 메시지 제공
  - 빈 응답 검증 로직 추가

### 수정됨
- **🔧 Azure OpenAI API 파라미터 최적화**: TODO 상세 다이얼로그 LLM 호출 개선
  - `max_tokens` → `max_completion_tokens` (Azure 전용 파라미터)
  - `temperature` 제거 (Azure는 기본값 사용)
  - 공급자별 파라미터 분기 처리로 안정성 향상
  - OpenAI 및 OpenRouter는 기존 파라미터 유지

### 추가됨
- **📁 데이터셋 마이그레이션**: multi_project_8week_ko 데이터셋으로 전환 (v1.2.0)
  - `docs/DATASET_MIGRATION.md`: 마이그레이션 가이드 문서
  - 기존: mobile_4week_ko (4주 데이터)
  - 신규: multi_project_8week_ko (8주 데이터)
  - PM: 이민주 (pm.1@multiproject.dev)
  - 팀 구성: PM, 디자이너, 개발자, 데보옵스 (4명)

- **📊 분석 결과 탭 개선 방안 문서**: 대시보드 스타일 제안 (v1.1.9)
  - `docs/ANALYSIS_TAB_IMPROVEMENT.md`: 3가지 개선 옵션 제시
  - 옵션 1: 대시보드 스타일 (카드 + 차트)
  - 옵션 2: 탭 분할 (간단)
  - 옵션 3: 아코디언 스타일 (중간)
  - Phase별 구현 순서 및 코드 예시 포함

- **📚 Summarizer 사용 흐름 문서화**: MessageSummarizer 완전 가이드 (v1.1.8)
  - `docs/SUMMARIZER_FLOW.md`: 전체 사용 흐름 및 데이터 구조 문서화
  - 메인 분석 파이프라인에서의 사용법
  - 그룹 요약 생성 과정
  - TODO 상세 다이얼로그 LLM 호출
  - GUI 표시 위치 및 코드 위치 매핑
  - 입력/출력 데이터 구조 상세 설명
  - 트러블슈팅 가이드

- **🎨 UI 스타일 시스템 추가**: 일관된 디자인 시스템 구축 (v1.1.8)
  - `ui/styles.py`: 중앙 집중식 색상 팔레트 및 스타일 정의
  - Tailwind CSS 기반 색상 체계 (Primary, Secondary, Success, Warning, Danger)
  - 폰트 크기 및 굵기 표준화 (XS ~ XXXL, Normal ~ Extrabold)
  - 간격 및 여백 상수 정의 (XS: 4px ~ XXL: 32px)
  - 재사용 가능한 스타일 문자열 (버튼, 카드, 배지, 제목 등)
  - 우선순위별 색상 헬퍼 함수
  - 아이콘 및 이모지 시스템 (Icons 클래스)
  - HTML 배지 생성 헬퍼 함수
  - `docs/UI_STYLES.md`: 스타일 시스템 가이드 문서
  - `ui/styles.py`: 중앙 집중식 색상 팔레트 및 스타일 정의
  - Tailwind CSS 기반 색상 체계 (Primary, Secondary, Success, Warning, Danger)
  - 폰트 크기 및 굵기 표준화 (XS ~ XXXL, Normal ~ Extrabold)
  - 간격 및 여백 상수 정의 (XS: 4px ~ XXL: 32px)
  - 재사용 가능한 스타일 문자열 (버튼, 카드, 배지, 제목 등)
  - 우선순위별 색상 헬퍼 함수





- **📧 메일 탭 추가**: TODO 가치가 있는 이메일만 필터링하여 표시 (v1.1.7)
  - `EmailPanel` 컴포넌트 추가: 키워드 기반 휴리스틱 필터링
  - `EmailItem` 위젯: 카드 형태의 이메일 미리보기
  - 요청, 회의, 마감일, 승인 등 업무 관련 키워드 자동 감지
  - 실시간 필터링 카운트 표시
  - 호버 효과로 시각적 피드백 제공
  - 메신저와 분리하여 이메일만 별도 관리

- **📨 메시지 탭 개선**: 메신저 메시지만 일별/주간 요약
  - 이메일은 메일 탭으로 분리
  - 메신저 메시지만 빠르게 요약하여 성능 향상
  - 일별/주간/월별 요약 단위 선택 가능
- **✅ 스마트 메시지 필터링**: PM 수신 메시지만 자동 필터링 (v1.1.6)
  - 이메일: `to`, `cc`, `bcc` 필드에서 PM 이메일 주소 확인
  - 메신저: DM 룸의 참여자 목록에서 PM 핸들 확인
  - 그룹 채팅은 기본적으로 포함 (추후 개선 예정)
  - PM이 **보낸** 메시지는 자동으로 제외하여 업무 관리 정확도 향상
  - 필터링 전후 메시지 수를 로그로 출력하여 추적 용이
  - **성능 대폭 향상**: 전체 메시지 분석 → PM 수신 메시지만 분석으로 처리 시간 단축



- **🔧 Azure OpenAI API 파라미터 최적화**: TODO 상세 다이얼로그 LLM 호출 개선 (v1.1.8+)
  - `ui/todo_panel.py`: 공급자별 API 파라미터 분기 처리
  - **Azure**: `max_completion_tokens` 사용, `temperature` 제거 (기본값 사용)
  - **OpenAI/OpenRouter**: 기존 `max_tokens`, `temperature` 유지
  - API 버전 `2024-08-01-preview` 사용 권장
  - 요약 생성 및 회신 초안 작성 기능 안정성 향상

- **🐛 Azure OpenAI API 버전 오류 수정**
  - 잘못된 API 버전 `2025-04-01-preview` → 안정적인 `2024-08-01-preview`로 변경
  - 400 Bad Request 오류 해결
  - 요약/회신 생성 기능 정상 작동
- **🐛 버그 수정**: `requests` 모듈 import 누락 오류 해결
  - `ui/todo_panel.py`에서 `requests` 모듈을 최상단에서 import하도록 수정
  - 요약/회신 생성 시 "name 'requests' is not defined" 오류 해결

### 개선됨
- **📌 메시지 탭 주요 포인트 자동 추출**: 분석 결과 없이도 작동 (v1.1.9+)
  - 메시지 내용에서 직접 주요 포인트 추출
  - 제목 우선, 없으면 본문 첫 문장 사용
  - 발신자 정보 포함 (예: "Kim Jihoon: 오늘 오전 2일차 작업 진행 상황 점검...")
  - 최대 3개 포인트 표시
  - 분석 결과가 있으면 우선 사용, 없으면 메시지 내용 기반으로 폴백
  - 너무 짧은 문장(10자 미만) 자동 제외
  - 최대 80자로 제한하여 가독성 향상

- **⚡ 메시지 수집 속도 개선**: TODO 먼저 표시, 요약은 실시간 생성 (v1.1.9)
  - 메시지 수집 후 TODO 리스트 즉시 표시
  - 메시지 탭: 수집된 메시지 수만 표시
  - 요약 단위 선택 시 실시간으로 요약 생성
  - 기존: 모든 요약 생성 후 화면 표시 (느림)
  - 개선: TODO 먼저 표시 → 필요시 요약 생성 (빠름)

- **🔍 TODO 상세 다이얼로그 로깅 강화**: 요약/회신 생성 디버깅 (v1.1.9)
  - 타임아웃 30초 → 60초로 확대
  - 상세한 에러 메시지 및 로깅
  - API 호출 URL, 페이로드, 응답 로깅
  - 타임아웃, HTTP 오류, JSON 파싱 오류 구분

- **📋 TODO 설명 최적화**: 첫 줄이 보이므로 간단하게 (v1.1.9)
  - 요약 길이: 150자 → 100자로 축소
  - 첫 2문장 → 첫 1문장으로 축소
  - 첫 줄에 이미 전체 설명이 보이므로 중복 제거

- **📝 메시지 탭 요약 개선**: 실제 내용 기반 의미있는 요약 (v1.1.8+)
  - **주요 주제 자동 추출**: 메시지 내용에서 키워드 분석하여 주제 파악
    - 지원 주제: 미팅, 보고서, 검토, 개발, 버그, 배포, 테스트, 디자인, 일정, 승인
    - 한글 + 영어 키워드 동시 지원 (예: "미팅", "meeting", "mtg")
    - 최대 20개 메시지 분석하여 상위 3개 주제 추출
  - **개선된 요약 형식**:
    - 기존: "총 82건의 메시지가 수집되었습니다"
    - 개선: "미팅, 보고서 관련 82건 (긴급 5건) 주요 발신자: Kim Jihoon (40건)"
  - **우선순위 강조**: 긴급/중요 메시지 수를 명시적으로 표시
  - **발신자 정보**: 주요 발신자와 메시지 수 포함
  - **성능 최적화**: 최대 20개 메시지만 분석하여 빠른 응답

- **📋 TODO 설명 확대**: 더 자세한 정보 표시 (v1.1.8)
  - 요약 길이: 80자 → 150자로 확대
  - 첫 문장 → 첫 2문장으로 확대
  - 기존: "미팅참석"
  - 개선: "조기 퇴근드 수 후 디자인 수정이 들어와서, 15시에서 16시까지는 실제 수정 사항 검토와 최종 피드백 반영을 하시고..."
  - 무슨 내용인지 바로 파악 가능

- **✅ TODO 제목 간결화**: 액션 제목을 한 단어로 표시
  - "미팅참석", "업무처리", "문서검토", "답변작성", "마감작업"
  - 기존: "미팅 참석: 시작은 09:00부터 15분 가량 간단한 스탠드업 미팅으로..."
  - 개선: "미팅참석"
  
- **⚡ 성능 개선**: 불필요한 LLM 호출 최소화
  - 상위 20개 메시지만 요약하여 처리 시간 단축
  - 메시지가 50개 이상일 경우 전체 대화 요약 스킵
  
- **코드 리팩토링**: naive datetime 변환 로직 통합
  - `utils/datetime_utils.py`에 `ensure_utc_aware()` 유틸리티 함수 추가
  - `main.py`의 중복 코드 제거 (시간 범위 필터링 로직 개선)
  - 코드 재사용성 및 유지보수성 향상

### 수정됨
- **의존성 명시**: `ui/todo_panel.py`에 `requests` 모듈 import 추가
  - LLM API 호출을 위한 HTTP 클라이언트
  - `requirements.txt`에 이미 포함되어 있음 (`requests==2.31.0`)

## [1.1.5] - 2025-10-17

### 추가됨
- **TODO 상세 다이얼로그 개선**
  - 상하 분할 레이아웃: 원본 메시지(상단)와 요약/액션(하단) 영역 분리
  - LLM 기반 실시간 요약 생성: 원본 메시지를 3-5개 불릿 포인트로 간결하게 요약
  - 자동 회신 초안 작성: LLM이 원본 메시지를 분석하여 정중하고 명확한 회신 초안 생성
  - 개선된 UI/UX: 더 넓은 다이얼로그(600x700), 명확한 섹션 구분, 시각적 피드백

### 변경됨
- `ui/todo_panel.py`: `TodoDetailDialog` 클래스 대폭 개선
  - 다이얼로그 크기 확대 (420x520 → 600x700)
  - 원본 메시지 표시 영역 개선 (최소 높이 200px)
  - 요약 생성 버튼 추가 (📋 요약 생성)
  - 회신 초안 작성 버튼 추가 (✉️ 회신 초안 작성)
  - LLM API 호출 메서드 추가 (`_call_llm`, `_call_llm_for_summary`, `_call_llm_for_reply`)
  - Azure OpenAI, OpenAI, OpenRouter 지원
- `ui/time_range_selector.py`: 기본 시간 범위 개선
  - 기본 범위를 24시간에서 30일로 확대
  - "메시지 없음" 오류 발생 빈도 감소
  - 대부분의 오프라인 데이터를 기본적으로 포함

### 개선됨
- TODO 상세 정보 확인 시 사용자 경험 대폭 향상
- 원본 메시지와 요약을 한 화면에서 비교 가능
- 회신 작성 시간 단축 (LLM 자동 초안 생성)
- 시간 범위 선택 기본값 개선으로 초보 사용자 경험 향상

## [1.1.5] - 2025-10-17

### 추가됨
- **TODO 상세 다이얼로그 개선**
  - 상하 분할 레이아웃: 상단(원본 메시지) + 하단(요약/액션)
  - LLM 기반 요약 생성 버튼: 원본 메시지를 3-5개 불릿 포인트로 요약
  - LLM 기반 회신 초안 작성 버튼: 정중하고 명확한 회신 자동 생성
  - 실시간 LLM 호출로 즉시 요약/회신 생성

- **TODO 리스트 요약 개선**
  - 각 TODO 항목에 간단한 요약 표시 (회색 박스)
  - 첫 문장만 추출하여 최대 80자로 제한
  - 줄바꿈 제거 및 공백 정리로 가독성 향상

- **시간 범위 선택 개선**
  - "전체 기간" 버튼 추가: 1년 전부터 현재까지 모든 메시지 포함
  - 기본 시간 범위를 최근 30일로 변경 (기존 24시간에서 확대)
  - 전체 기간 버튼 클릭 시 자동으로 적용

### 개선됨
- **사용자 경험 개선**
  - TODO 리스트에서 긴 설명이 깔끔하게 요약되어 표시
  - 상세 다이얼로그에서 원본과 요약을 명확히 구분
  - 버튼 상태 관리로 생성 중/완료 상태 명확히 표시
  - 시간 범위 기본값 개선으로 "메시지 없음" 오류 감소

### 변경됨
- `ui/todo_panel.py`: TodoDetailDialog 클래스 전면 개편
  - 상하 분할 레이아웃 적용
  - LLM 호출 메서드 추가 (_call_llm, _generate_summary, _generate_reply)
  - BasicTodoItem에 _create_brief_summary 메서드 추가

- `ui/time_range_selector.py`: 시간 범위 선택 개선
  - 기본 범위를 최근 30일로 변경
  - "전체 기간" 버튼 추가 및 자동 적용 기능

### 수정됨
- **시간 범위 필터링 문제 해결** (중요!)
  - **타임존 비교 오류 수정**: naive datetime과 aware datetime 비교 문제 해결
  - naive datetime을 UTC aware datetime으로 자동 변환
  - 기본값이 최근 24시간으로 설정되어 오래된 데이터가 필터링되는 문제 수정
  - 사용자가 "메시지 없음" 오류를 자주 겪는 문제 해결

### 문서화
- `docs/TODO_DETAIL_IMPROVEMENTS.md`: 상세 개선사항 문서 추가

## [1.1.4] - 2025-10-17

### 개선됨
- **시간 범위 필터링 사용자 경험 개선**
  - 선택한 시간 범위에 메시지가 없을 경우 경고 로그 자동 출력
  - 사용자가 시간 범위를 조정하거나 '전체 기간' 옵션을 선택하도록 안내
  - 빈 결과에 대한 명확한 피드백 제공으로 혼란 방지

### 변경됨
- `main.py`: 시간 범위 필터링 후 메시지 수 검증 로직 추가
  - 필터링 결과가 0건일 때 경고 메시지 출력
  - 로그 레벨: WARNING

## [1.1.3] - 2025-10-17

### 추가됨
- **TODO 자동 초기화**: 애플리케이션 시작 시 이전 세션의 TODO 데이터를 자동으로 초기화
  - `TodoPanel.__init__()`: 초기화 시 `clear_all_todos_silent()` 호출
  - `clear_all_todos_silent()`: UI 새로고침 없이 데이터베이스의 모든 TODO 삭제
  - 항상 최신 분석 결과로 시작하여 데이터 일관성 보장

### 변경됨
- `ui/todo_panel.py`: 초기화 로직 개선
  - 애플리케이션 시작 시 `refresh_todo_list()` 호출 제거
  - 초기화 상태 유지로 불필요한 UI 업데이트 방지

### 개선됨
- 데이터 일관성: 이전 세션의 오래된 TODO가 남아있지 않도록 보장
- 사용자 경험: 항상 깨끗한 상태에서 새로운 분석 시작

## [1.1.2] - 2025-10-17

### 추가됨
- **로깅 시스템 준비**: `ui/main_window.py`에 로깅 모듈 추가
  - 향후 상세한 애플리케이션 동작 추적 및 디버깅 지원 예정
  - 로거 인스턴스 초기화 완료

### 개선됨
- 코드 구조 개선: 로깅 인프라 준비로 향후 유지보수성 향상

## [1.1.1] - 2025-10-17

### 추가됨
- **메시지 데이터 접근 개선**: `run_full_cycle()` 메서드의 반환값에 `messages` 필드 추가
  - GUI에서 수집된 메시지 원본 데이터에 직접 접근 가능
  - 메시지 그룹화 및 요약 기능과의 통합 개선

### 변경됨
- `main.py::run_full_cycle()`: 반환 딕셔너리에 `messages` 필드 추가
  - 기존: `{"success": True, "todo_list": {...}, "analysis_results": [...], "collected_messages": 58}`
  - 변경: `{"success": True, "todo_list": {...}, "analysis_results": [...], "collected_messages": 58, "messages": [...]}`

## [1.1.0] - 2025-10-17

### 추가됨
- **시간 범위 선택 기능**: 특정 오프라인 기간의 메시지만 선택하여 분석 가능
  - TimeRangeSelector 컴포넌트 추가
  - 빠른 선택 버튼 (최근 1시간, 4시간, 오늘, 어제, 최근 7일)
  - 사용자 정의 시간 범위 설정 지원
  - `collect_messages()` 메서드에 `time_range` 파라미터 추가
  - 시간 범위 필터링 로직 구현 (시작/종료 시간 기반)
  - **Naive datetime 자동 변환**: naive datetime을 UTC aware로 자동 변환
  - **상세 로깅**: 필터링 전후 메시지 수 비교 로그 추가
  
- **메시지 그룹화 및 요약 기능**: 일/주/월 단위로 메시지 그룹화
  - `nlp/message_grouping.py`: 그룹화 유틸리티 함수
  - `nlp/grouped_summary.py`: 그룹 요약 데이터 모델
  - 그룹별 통계 자동 계산 (우선순위 분포, 주요 발신자)
  
- **MessageSummaryPanel 컴포넌트**: 메시지 탭 UI 개선
  - 요약 단위 선택 (일별/주별/월별 라디오 버튼)
  - 카드 형태 요약 표시
  - **발신자별 우선순위 배지**: 색상 코딩된 배지로 우선순위 표시
    - High: 빨간색 배지 + #High 태그
    - Medium: 노란색 배지 + #Medium 태그
    - Low: 회색 배지 (태그 없음)
  - **간결한 요약**: 1-2줄로 핵심 내용 빠르게 파악
  - **주요 포인트**: 최대 3개의 핵심 포인트 자동 추출
  - 스크롤 가능한 요약 리스트

- **날씨 정보 기능**: 오늘/내일 날씨 및 업무 팁 제공
  - 기상청 API 연동 (한국 주요 도시)
  - Open-Meteo API 폴백 지원
  - 날씨 기반 업무 팁 자동 생성

- **Top-3 즉시 처리**: 가장 중요한 3개 TODO 자동 선정
  - 우선순위, 데드라인, 근거 수 기반 점수 계산
  - 좌측 패널에 Top-3 요약 표시

### 변경됨
- **MessageSummarizer**: 그룹 요약 메서드 추가
  - `summarize_group()`: 그룹 메시지 통합 요약
  - `batch_summarize_groups()`: 여러 그룹 동시 요약
  
- **main_window.py**: UI 구조 개선
  - 좌측 패널에 시간 범위 선택기 추가
  - 메시지 탭을 MessageSummaryPanel로 교체
  - `_update_message_summaries()`: 그룹화된 요약 생성 로직
  - `_generate_brief_summary()`: 간결한 요약 생성
  - `_extract_key_points()`: 주요 포인트 추출
  - 발신자별 최고 우선순위 계산 로직 추가

- **message_summary_panel.py**: 카드 표시 로직 개선
  - `_create_sender_badges()`: 발신자 배지 생성 (우선순위 포함)
  - `brief_summary` 필드로 간결한 요약 표시
  - `key_points` 최대 3개로 제한
  - 불필요한 docstring 간소화

### 문서화
- README.md 업데이트: 새로운 기능 및 사용법 추가
- MESSAGE_SUMMARY_PANEL.md: 발신자별 우선순위 배지 문서화
- MESSAGE_GROUPING.md: 메시지 그룹화 기능 가이드
- TIME_RANGE_SELECTOR.md: 시간 범위 선택 컴포넌트 가이드
- tasks.md: 구현 완료 항목 업데이트

### 수정됨
- 날씨 API 타임아웃 처리 개선
- 한글 출력 인코딩 안정화 (Windows)
- UI 스타일 일관성 개선 (Fusion 테마, 전역 폰트)
- **시간 범위 필터링 개선**: 
  - Naive datetime을 UTC aware로 자동 변환
  - 필터링 전후 메시지 수 비교 로그 추가
  - 날짜 파싱 실패 시 상세 디버그 로그 출력
- 중복 코드 제거 (`collect_messages` 메서드 정리)

## [1.0.0] - 2025-10-01

### 추가됨
- 초기 릴리스
- 오프라인 메시지 로딩 기능
- LLM 기반 분석 파이프라인
- TODO 자동 생성 및 관리
- PyQt6 기반 GUI
- SQLite 데이터베이스 (TODO 캐시)
- 온라인/오프라인 모드 전환
- 일일/주간 요약 기능

[1.1.5]: https://github.com/yourusername/smart_assistant/compare/v1.1.4...v1.1.5
[1.1.4]: https://github.com/yourusername/smart_assistant/compare/v1.1.3...v1.1.4
[1.1.3]: https://github.com/yourusername/smart_assistant/compare/v1.1.2...v1.1.3
[1.1.2]: https://github.com/yourusername/smart_assistant/compare/v1.1.1...v1.1.2
[1.1.1]: https://github.com/yourusername/smart_assistant/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/yourusername/smart_assistant/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/yourusername/smart_assistant/releases/tag/v1.0.0
