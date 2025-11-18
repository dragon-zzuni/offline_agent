# Offline Agent 소프트웨어 아키텍처 (11/17 업데이트)

## C4 Model 기반 아키텍처 문서

이 문서는 C4 Model을 기반으로 Offline Agent의 소프트웨어 아키텍처를 4가지 레벨로 설명합니다.

---

## Level 1: System Context Diagram (시스템 컨텍스트)

```mermaid
C4Context
    title System Context Diagram - Offline Agent

    Person(pm, "프로젝트 매니저", "이정두, 김보연 등<br/>팀 커뮤니케이션 관리")
    
    System(offline_agent, "Offline Agent", "메시지/메일 통합 분석<br/>TODO 자동 생성<br/>회신 초안 작성")
    
    System_Ext(virtualoffice, "VirtualOffice API", "이메일/채팅 시뮬레이션<br/>REST API 제공")
    System_Ext(openai, "OpenAI API", "GPT-4o<br/>LLM 분석 서비스")
    SystemDb_Ext(vdos_db, "VDOS Database", "시뮬레이션 데이터<br/>tick_log, messages")
    
    Rel(pm, offline_agent, "사용", "PyQt6 Desktop App")
    Rel(offline_agent, virtualoffice, "데이터 수집", "REST API / HTTP")
    Rel(offline_agent, openai, "LLM 분석 요청", "REST API / HTTPS")
    Rel(offline_agent, vdos_db, "시뮬레이션 시간 조회", "SQLite")
    
    UpdateLayoutConfig($c4ShapeInRow="3", $c4BoundaryInRow="1")
```

### 시스템 설명

**Offline Agent**는 프로젝트 매니저가 팀 커뮤니케이션을 효율적으로 관리할 수 있도록 돕는 데스크톱 애플리케이션입니다.

**주요 기능:**
- 이메일/채팅 메시지 통합 분석
- AI 기반 TODO 자동 생성
- 우선순위 자동 판별
- 회신 초안 자동 작성
- 프로젝트별 태그 관리

**외부 시스템:**
- **VirtualOffice API**: 시뮬레이션된 이메일/채팅 데이터 제공
- **OpenAI API**: GPT-4o를 통한 자연어 처리
- **VDOS Database**: 시뮬레이션 시간 매핑 데이터

---

## Level 2: Container Diagram (컨테이너)

```mermaid
C4Container
    title Container Diagram - Offline Agent

    Person(pm, "프로젝트 매니저", "사용자")
    
    Container_Boundary(offline_agent, "Offline Agent") {
        Container(desktop_app, "Desktop Application", "Python, PyQt6", "사용자 인터페이스<br/>TODO/메시지/통계 표시")
        Container(analysis_engine, "Analysis Engine", "Python", "메시지 분석<br/>TODO 생성<br/>우선순위 판별")
        Container(data_layer, "Data Layer", "Python, SQLite", "데이터 수집/저장<br/>캐시 관리")
        ContainerDb(local_db, "Local Database", "SQLite", "todos_cache.db<br/>project_tags_cache.db")
    }
    
    System_Ext(virtualoffice, "VirtualOffice API", "Email/Chat Server")
    System_Ext(openai, "OpenAI API", "GPT-4o")
    SystemDb_Ext(vdos_db, "VDOS Database", "Simulation Data")
    
    Rel(pm, desktop_app, "사용", "GUI")
    Rel(desktop_app, analysis_engine, "분석 요청", "Python API")
    Rel(analysis_engine, data_layer, "데이터 요청", "Python API")
    Rel(data_layer, local_db, "읽기/쓰기", "SQLite")
    
    Rel(data_layer, virtualoffice, "데이터 수집", "REST API")
    Rel(analysis_engine, openai, "LLM 분석", "REST API")
    Rel(data_layer, vdos_db, "시간 매핑", "SQLite")
    
    UpdateLayoutConfig($c4ShapeInRow="2", $c4BoundaryInRow="1")
```

### 컨테이너 설명

1. **Desktop Application (PyQt6)**
   - 사용자 인터페이스 제공
   - TODO/메시지/메일/통계 탭 관리
   - 실시간 알림 및 업데이트

2. **Analysis Engine**
   - 메시지 분석 파이프라인
   - 우선순위 판별 (키워드 + LLM)
   - TODO 생성 및 중복 제거
   - Top3 선정

3. **Data Layer**
   - VirtualOffice API 연동
   - 데이터 수집 및 필터링
   - 캐시 관리 (14일 TTL)
   - 시뮬레이션 시간 매핑

4. **Local Database (SQLite)**
   - TODO 저장소
   - 프로젝트 태그 캐시
   - 페르소나별 캐시

---

## Level 3: Component Diagram (컴포넌트)

```mermaid
C4Component
    title Component Diagram - Analysis Engine

    Container_Boundary(analysis_engine, "Analysis Engine") {
        Component(pipeline, "AnalysisPipelineService", "Python", "분석 파이프라인 조율")
        Component(priority, "PriorityRanker", "Python", "우선순위 분석<br/>키워드 + LLM")
        Component(summarizer, "MessageSummarizer", "Python", "메시지 요약<br/>LLM 기반")
        Component(extractor, "ActionExtractor", "Python", "액션 추출<br/>TODO 생성")
        Component(top3, "Top3LLMSelector", "Python", "Top3 선정<br/>자연어 규칙")
        Component(dedup, "TodoDeduplicationService", "Python", "중복 제거<br/>유사도 기반")
        Component(project_tag, "ProjectTagService", "Python", "프로젝트 태그<br/>RAG 기반")
    }
    
    Container(data_layer, "Data Layer", "Python", "데이터 수집/저장")
    Container(desktop_app, "Desktop App", "PyQt6", "UI")
    System_Ext(openai, "OpenAI API", "GPT-4o")
    
    Rel(desktop_app, pipeline, "분석 요청", "analyze_messages()")
    Rel(pipeline, data_layer, "메시지 수집", "collect_messages()")
    
    Rel(pipeline, priority, "우선순위 분석", "rank_priority()")
    Rel(pipeline, summarizer, "메시지 요약", "summarize()")
    Rel(pipeline, extractor, "액션 추출", "extract_actions()")
    Rel(pipeline, dedup, "중복 제거", "deduplicate()")
    Rel(pipeline, project_tag, "태그 생성", "tag_project()")
    Rel(pipeline, top3, "Top3 선정", "select_top3()")
    
    Rel(priority, openai, "LLM 분석", "GPT-4o API")
    Rel(summarizer, openai, "LLM 요약", "GPT-4o API")
    Rel(extractor, openai, "LLM 추출", "GPT-4o API")
    Rel(top3, openai, "LLM 선정", "GPT-4o API")
    Rel(project_tag, openai, "LLM 태깅", "GPT-4o API")
    
    UpdateLayoutConfig($c4ShapeInRow="3", $c4BoundaryInRow="1")
```


### 컴포넌트 설명

#### Analysis Engine 컴포넌트

1. **AnalysisPipelineService**
   - 전체 분석 파이프라인 조율
   - 각 컴포넌트 호출 순서 관리
   - 에러 처리 및 재시도 로직

2. **PriorityRanker**
   - 1단계: 키워드 기반 우선순위 판별
   - 2단계: LLM 기반 상세 분석
   - 긴급도, 발신자, 데드라인 등 종합 평가

3. **MessageSummarizer**
   - 메시지 요약 생성
   - 한줄 요약 (50자 이내)
   - 상세 요약 (200자 이내)

4. **ActionExtractor**
   - 액션 아이템 추출
   - TODO 생성
   - 데드라인 파싱

5. **Top3LLMSelector**
   - 자연어 규칙 적용
   - RAG 기반 컨텍스트 참조
   - Top3 TODO 선정

6. **TodoDeduplicationService**
   - 유사도 기반 중복 제거
   - 임베딩 벡터 비교
   - 중복 TODO 병합

7. **ProjectTagService**
   - 프로젝트 태그 자동 생성
   - 캐시 기반 빠른 조회
   - LLM 기반 프로젝트 식별

---

## Level 3: Component Diagram - Data Layer

```mermaid
C4Component
    title Component Diagram - Data Layer

    Container_Boundary(data_layer, "Data Layer") {
        Component(ds_manager, "DataSourceManager", "Python", "데이터 소스 관리<br/>추상화 레이어")
        Component(vo_source, "VirtualOfficeDataSource", "Python", "VirtualOffice API<br/>연동 및 변환")
        Component(vo_client, "VirtualOfficeClient", "Python", "HTTP 클라이언트<br/>재시도 로직")
        Component(converters, "Converters", "Python", "데이터 포맷 변환<br/>recipient_type 판별")
        Component(todo_repo, "TodoRepository", "Python", "TODO CRUD<br/>페르소나별 조회")
        Component(project_cache, "ProjectTagCache", "Python", "프로젝트 태그<br/>캐시 관리")
        Component(persona_cache, "PersonaTodoCacheService", "Python", "페르소나별<br/>캐시 관리")
    }
    
    ContainerDb(local_db, "Local Database", "SQLite", "todos_cache.db")
    System_Ext(virtualoffice, "VirtualOffice API", "REST API")
    SystemDb_Ext(vdos_db, "VDOS Database", "SQLite")
    Container(analysis_engine, "Analysis Engine", "Python", "분석 엔진")
    
    Rel(analysis_engine, ds_manager, "데이터 요청", "collect_messages()")
    Rel(ds_manager, vo_source, "소스 선택", "get_source()")
    Rel(vo_source, vo_client, "API 호출", "get_emails(), get_messages()")
    Rel(vo_source, converters, "데이터 변환", "convert_to_internal()")
    Rel(vo_client, virtualoffice, "HTTP 요청", "REST API")
    Rel(vo_source, vdos_db, "시간 매핑", "tick_log 조회")
    
    Rel(analysis_engine, todo_repo, "TODO 저장", "save_todo()")
    Rel(analysis_engine, project_cache, "태그 조회", "get_tag()")
    Rel(analysis_engine, persona_cache, "캐시 관리", "get_cache()")
    
    Rel(todo_repo, local_db, "읽기/쓰기", "SQLite")
    Rel(project_cache, local_db, "읽기/쓰기", "SQLite")
    Rel(persona_cache, todo_repo, "TODO 조회", "get_todos_by_persona()")
    
    UpdateLayoutConfig($c4ShapeInRow="3", $c4BoundaryInRow="1")
```

### Data Layer 컴포넌트 설명

1. **DataSourceManager**
   - 데이터 소스 추상화
   - 다중 소스 지원 (VirtualOffice, JSON 파일 등)
   - 소스 전환 로직

2. **VirtualOfficeDataSource**
   - VirtualOffice API 연동
   - 병렬 데이터 수집
   - 발신 메시지 필터링
   - 시뮬레이션 시간 주입

3. **VirtualOfficeClient**
   - HTTP 클라이언트
   - 재시도 로직 (최대 3회)
   - 타임아웃 관리 (10초)
   - 연결 풀링

4. **Converters**
   - API 응답 → 내부 포맷 변환
   - recipient_type 판별 (to/cc/bcc/from)
   - 페르소나 정보 매핑

5. **TodoRepository**
   - TODO CRUD 작업
   - 페르소나별 조회
   - 14일 자동 삭제
   - 트랜잭션 관리

6. **ProjectTagCache**
   - content_hash 기반 캐시
   - LRU 캐시 전략
   - 배치 업데이트

7. **PersonaTodoCacheService**
   - 페르소나별 캐시 관리
   - 14일 TTL
   - 캐시 무효화 로직

---

## Level 3: Component Diagram - Desktop Application

```mermaid
C4Component
    title Component Diagram - Desktop Application (UI Layer)

    Container_Boundary(desktop_app, "Desktop Application") {
        Component(main_window, "MainWindow", "PyQt6", "메인 윈도우<br/>탭 관리")
        Component(todo_panel, "TodoPanel", "PyQt6", "TODO 리스트<br/>CRUD 작업")
        Component(msg_panel, "MessageSummaryPanel", "PyQt6", "메시지 그룹화<br/>시간별/발신자별")
        Component(email_panel, "EmailPanel", "PyQt6", "이메일 필터링<br/>TO/CC/BCC")
        Component(analysis_panel, "AnalysisResultPanel", "PyQt6", "분석 결과<br/>통계 표시")
        Component(stats_panel, "StatisticsPanel", "PyQt6", "통계 차트<br/>프로젝트별")
        Component(cache_controller, "AnalysisCacheController", "Python", "캐시 관리<br/>폴링 제어")
        Component(worker_thread, "WorkerThread", "PyQt6", "백그라운드 작업<br/>비동기 처리")
    }
    
    Container(analysis_engine, "Analysis Engine", "Python", "분석 엔진")
    Container(data_layer, "Data Layer", "Python", "데이터 레이어")
    Person(pm, "프로젝트 매니저", "사용자")
    
    Rel(pm, main_window, "사용", "GUI 조작")
    Rel(main_window, todo_panel, "탭 전환", "show()")
    Rel(main_window, msg_panel, "탭 전환", "show()")
    Rel(main_window, email_panel, "탭 전환", "show()")
    Rel(main_window, analysis_panel, "탭 전환", "show()")
    Rel(main_window, stats_panel, "탭 전환", "show()")
    
    Rel(main_window, cache_controller, "캐시 관리", "check_cache()")
    Rel(main_window, worker_thread, "백그라운드 작업", "start_analysis()")
    
    Rel(worker_thread, analysis_engine, "분석 요청", "analyze_messages()")
    Rel(cache_controller, data_layer, "데이터 수집", "collect_messages()")
    
    Rel(worker_thread, main_window, "결과 전달", "signal/slot")
    Rel(cache_controller, main_window, "알림", "signal/slot")
    
    UpdateLayoutConfig($c4ShapeInRow="3", $c4BoundaryInRow="1")
```

### Desktop Application 컴포넌트 설명

1. **MainWindow**
   - 메인 윈도우 관리
   - 탭 전환 로직
   - 페르소나 선택
   - 전역 상태 관리

2. **TodoPanel**
   - TODO 리스트 표시
   - 우선순위별 정렬
   - 프로젝트별 그룹화
   - Top3 하이라이트
   - CRUD 작업

3. **MessageSummaryPanel**
   - 메시지 그룹화 (시간/발신자/프로젝트)
   - 그룹 확장/축소
   - 검색 및 필터링
   - 상세 다이얼로그

4. **EmailPanel**
   - 이메일 필터링 (TO/CC/BCC)
   - 스레드 그룹화
   - 프로젝트 필터
   - 발신자 하이라이트

5. **AnalysisResultPanel**
   - 분석 결과 표시
   - 우선순위 분포
   - 메시지 요약
   - 액션 아이템

6. **StatisticsPanel**
   - 통계 차트 (Line, Pie, Bar)
   - 수신/우선순위/프로젝트 통계
   - 기간 선택
   - 내보내기 (PNG/CSV)

7. **AnalysisCacheController**
   - 캐시 확인 및 로드
   - 정기 폴링 (5초)
   - 증분 수집
   - 캐시 무효화

8. **WorkerThread**
   - 백그라운드 분석
   - UI 블로킹 방지
   - 진행 상황 알림
   - 에러 처리

---

## Level 4: Code Diagram (클래스 다이어그램)

```mermaid
classDiagram
    class MainWindow {
        -QTabWidget tabs
        -TodoPanel todo_panel
        -MessageSummaryPanel msg_panel
        -AnalysisCacheController cache_controller
        -WorkerThread worker
        +__init__()
        +setup_ui()
        +on_persona_changed()
        +start_analysis()
        +update_ui()
    }
    
    class AnalysisPipelineService {
        -DataSourceManager data_source_manager
        -PriorityRanker priority_ranker
        -MessageSummarizer summarizer
        -ActionExtractor action_extractor
        -Top3LLMSelector top3_service
        +analyze_messages() Dict
        +_filter_messages() List
        +_rank_priority() List
        +_extract_actions() List
    }
    
    class VirtualOfficeDataSource {
        -VirtualOfficeClient client
        -Dict selected_persona
        -int last_email_id
        -int last_message_id
        +collect_messages() List
        +collect_new_data_batch() Dict
        +_filter_sent_messages() List
        +_annotate_simulation_timestamps() None
    }
    
    class TodoRepository {
        -Connection conn
        -str db_path
        +save_todo() int
        +get_all() List
        +get_todos_by_persona() List
        +update_todo() bool
        +delete_todo() bool
        +cleanup_old_todos() int
    }
    
    class PriorityRanker {
        -OpenAI client
        -Dict keyword_patterns
        +rank_priority() str
        +_keyword_check() Optional~str~
        +_llm_analysis() str
    }
    
    class Top3LLMSelector {
        -OpenAI client
        -str natural_language_rules
        +select_top3() List
        +_build_context() str
        +_query_rag() Dict
    }
    
    MainWindow --> AnalysisPipelineService : uses
    MainWindow --> TodoRepository : uses
    AnalysisPipelineService --> VirtualOfficeDataSource : uses
    AnalysisPipelineService --> PriorityRanker : uses
    AnalysisPipelineService --> Top3LLMSelector : uses
    AnalysisPipelineService --> TodoRepository : uses
    VirtualOfficeDataSource --> VirtualOfficeClient : uses
```

### 주요 클래스 설명

#### MainWindow
- **책임**: UI 전체 관리, 사용자 이벤트 처리
- **주요 메서드**:
  - `on_persona_changed()`: 페르소나 변경 시 캐시 확인 및 데이터 로드
  - `start_analysis()`: 백그라운드 분석 시작
  - `update_ui()`: 분석 결과로 UI 업데이트

#### AnalysisPipelineService
- **책임**: 분석 파이프라인 조율
- **주요 메서드**:
  - `analyze_messages()`: 전체 분석 파이프라인 실행
  - `_filter_messages()`: 메시지 필터링 (중복, 짧은 메시지 등)
  - `_rank_priority()`: 우선순위 판별
  - `_extract_actions()`: 액션 추출 및 TODO 생성

#### VirtualOfficeDataSource
- **책임**: VirtualOffice API 연동 및 데이터 변환
- **주요 메서드**:
  - `collect_messages()`: 전체 메시지 수집
  - `collect_new_data_batch()`: 증분 수집 (정기 폴링용)
  - `_filter_sent_messages()`: 발신 메시지 제외
  - `_annotate_simulation_timestamps()`: 시뮬레이션 시간 주입

#### TodoRepository
- **책임**: TODO 데이터 영속성 관리
- **주요 메서드**:
  - `save_todo()`: TODO 저장
  - `get_todos_by_persona()`: 페르소나별 TODO 조회
  - `cleanup_old_todos()`: 14일 경과 TODO 삭제

---

## 아키텍처 패턴

### 1. Layered Architecture (계층형 아키텍처)

```mermaid
graph TB
    subgraph "Presentation Layer"
        UI[PyQt6 UI Components]
    end
    
    subgraph "Application Layer"
        Services[Service Layer<br/>AnalysisPipelineService<br/>Top3LLMSelector<br/>ProjectTagService]
    end
    
    subgraph "Domain Layer"
        NLP[NLP Components<br/>PriorityRanker<br/>MessageSummarizer<br/>ActionExtractor]
    end
    
    subgraph "Infrastructure Layer"
        Data[Data Layer<br/>DataSourceManager<br/>TodoRepository<br/>Caches]
    end
    
    subgraph "External Systems"
        External[VirtualOffice API<br/>OpenAI API<br/>SQLite DB]
    end
    
    UI --> Services
    Services --> NLP
    Services --> Data
    Data --> External
    NLP --> External
    
    style UI fill:#e6f3ff
    style Services fill:#ffe6e6
    style NLP fill:#fff0e6
    style Data fill:#e6ffe6
    style External fill:#f0e6ff
```

### 2. Repository Pattern (저장소 패턴)

```mermaid
classDiagram
    class IRepository {
        <<interface>>
        +save()
        +get()
        +update()
        +delete()
    }
    
    class TodoRepository {
        +save_todo()
        +get_all()
        +get_todos_by_persona()
        +update_todo()
        +delete_todo()
    }
    
    class ProjectTagCache {
        +save_tag()
        +get_tag()
        +update_tag()
        +delete_tag()
    }
    
    class PersonaTodoCacheService {
        +save_cache()
        +get_cache()
        +invalidate_cache()
    }
    
    IRepository <|.. TodoRepository
    IRepository <|.. ProjectTagCache
    IRepository <|.. PersonaTodoCacheService
```

### 3. Strategy Pattern (전략 패턴)

```mermaid
classDiagram
    class DataSource {
        <<interface>>
        +collect_messages()
        +get_personas()
        +get_source_type()
    }
    
    class VirtualOfficeDataSource {
        +collect_messages()
        +get_personas()
        +get_source_type()
    }
    
    class JSONDataSource {
        +collect_messages()
        +get_personas()
        +get_source_type()
    }
    
    class DataSourceManager {
        -DataSource current_source
        +set_source()
        +collect_messages()
    }
    
    DataSource <|.. VirtualOfficeDataSource
    DataSource <|.. JSONDataSource
    DataSourceManager --> DataSource
```

### 4. Observer Pattern (관찰자 패턴)

```mermaid
classDiagram
    class Subject {
        <<interface>>
        +attach(observer)
        +detach(observer)
        +notify()
    }
    
    class AnalysisCacheController {
        -List~Observer~ observers
        +attach()
        +detach()
        +notify()
        +check_new_data()
    }
    
    class Observer {
        <<interface>>
        +update()
    }
    
    class MainWindow {
        +update()
        +on_new_data()
    }
    
    class TodoPanel {
        +update()
        +refresh_todos()
    }
    
    Subject <|.. AnalysisCacheController
    Observer <|.. MainWindow
    Observer <|.. TodoPanel
    AnalysisCacheController --> Observer
```

---

## 데이터 흐름 아키텍처

```mermaid
flowchart LR
    subgraph "External"
        API[VirtualOffice API]
        LLM[OpenAI GPT-4o]
        DB[(VDOS DB)]
    end
    
    subgraph "Data Collection"
        Client[VirtualOfficeClient]
        Source[VirtualOfficeDataSource]
        Convert[Converters]
    end
    
    subgraph "Processing"
        Filter[Message Filters]
        Pipeline[AnalysisPipeline]
        NLP[NLP Components]
    end
    
    subgraph "Storage"
        Cache[Cache Services]
        Repo[TodoRepository]
        LocalDB[(SQLite)]
    end
    
    subgraph "Presentation"
        UI[PyQt6 UI]
    end
    
    API --> Client
    DB --> Source
    Client --> Source
    Source --> Convert
    Convert --> Filter
    Filter --> Pipeline
    Pipeline --> NLP
    NLP --> LLM
    Pipeline --> Cache
    Pipeline --> Repo
    Cache --> LocalDB
    Repo --> LocalDB
    Repo --> UI
    Cache --> UI
    
    style API fill:#e6f3ff
    style LLM fill:#ffe6e6
    style Pipeline fill:#fff0e6
    style LocalDB fill:#e6ffe6
    style UI fill:#f0e6ff
```

---

## 배포 아키텍처

```mermaid
C4Deployment
    title Deployment Diagram - Offline Agent

    Deployment_Node(user_pc, "사용자 PC", "Windows 10/11") {
        Deployment_Node(python_env, "Python Environment", "Python 3.10+") {
            Container(desktop_app, "Offline Agent", "PyQt6 Desktop App", "메인 애플리케이션")
        }
        
        Deployment_Node(local_storage, "Local Storage", "File System") {
            ContainerDb(sqlite_db, "SQLite Database", "SQLite 3", "todos_cache.db<br/>project_tags_cache.db")
            ContainerDb(vdos_db, "VDOS Database", "SQLite 3", "vdossnapshot.db")
        }
    }
    
    Deployment_Node(cloud, "Cloud Services", "Internet") {
        Deployment_Node(virtualoffice_server, "VirtualOffice Server", "FastAPI") {
            Container(email_api, "Email API", "FastAPI", "Port 8002")
            Container(chat_api, "Chat API", "FastAPI", "Port 8001")
            Container(sim_api, "Sim Manager API", "FastAPI", "Port 8015")
        }
        
        Deployment_Node(openai_cloud, "OpenAI Platform", "Cloud") {
            Container(gpt4, "GPT-4o API", "REST API", "LLM 서비스")
        }
    }
    
    Rel(desktop_app, sqlite_db, "읽기/쓰기", "SQLite")
    Rel(desktop_app, vdos_db, "읽기", "SQLite")
    Rel(desktop_app, email_api, "HTTP 요청", "REST API")
    Rel(desktop_app, chat_api, "HTTP 요청", "REST API")
    Rel(desktop_app, sim_api, "HTTP 요청", "REST API")
    Rel(desktop_app, gpt4, "HTTPS 요청", "REST API")
    
    UpdateLayoutConfig($c4ShapeInRow="2", $c4BoundaryInRow="1")
```

### 배포 환경

**로컬 환경:**
- Windows 10/11
- Python 3.10+
- PyQt6
- SQLite 3

**외부 서비스:**
- VirtualOffice API (로컬 또는 원격)
- OpenAI API (클라우드)

---

## 보안 아키텍처

```mermaid
flowchart TD
    User[사용자] --> Auth[인증 레이어]
    
    Auth --> APIKey{API 키 검증}
    
    APIKey -->|Valid| Access[접근 허용]
    APIKey -->|Invalid| Deny[접근 거부]
    
    Access --> Encrypt[데이터 암호화]
    
    Encrypt --> LocalDB[(로컬 DB<br/>SQLite)]
    Encrypt --> ExternalAPI[외부 API<br/>HTTPS]
    
    LocalDB --> Decrypt[데이터 복호화]
    ExternalAPI --> Decrypt
    
    Decrypt --> Display[UI 표시]
    
    style Auth fill:#ffe6e6
    style Encrypt fill:#e6ffe6
    style Decrypt fill:#e6f3ff
```

### 보안 고려사항

1. **API 키 관리**
   - 환경 변수 (.env)
   - 평문 저장 금지
   - 키 로테이션 지원

2. **데이터 보호**
   - 로컬 DB 암호화 (선택사항)
   - HTTPS 통신
   - 민감 정보 마스킹

3. **접근 제어**
   - 페르소나별 데이터 격리
   - 캐시 TTL (14일)
   - 자동 로그아웃

---

## 성능 아키텍처

### 캐싱 전략

```mermaid
flowchart TD
    Request[요청] --> L1{L1 Cache<br/>메모리}
    
    L1 -->|Hit| Return1[즉시 반환<br/>< 1ms]
    L1 -->|Miss| L2{L2 Cache<br/>SQLite}
    
    L2 -->|Hit| Return2[빠른 반환<br/>< 10ms]
    L2 -->|Miss| L3{L3 Cache<br/>API}
    
    L3 -->|Hit| Return3[API 반환<br/>< 100ms]
    L3 -->|Miss| LLM[LLM 분석<br/>< 5s]
    
    LLM --> Save[캐시 저장]
    Save --> Return4[결과 반환]
    
    Return1 --> End([완료])
    Return2 --> End
    Return3 --> End
    Return4 --> End
    
    style L1 fill:#ccffcc
    style L2 fill:#e6ffe6
    style L3 fill:#fff0e6
    style LLM fill:#ffe6e6
```

### 병렬 처리

```mermaid
flowchart LR
    Start([시작]) --> Parallel{병렬 처리}
    
    Parallel -->|Thread 1| Email[이메일 수집<br/>105개]
    Parallel -->|Thread 2| Chat[채팅 수집<br/>133개]
    Parallel -->|Thread 3| SimTime[시뮬레이션 시간<br/>매핑]
    
    Email --> Merge[결과 병합]
    Chat --> Merge
    SimTime --> Merge
    
    Merge --> Filter[필터링<br/>238개 → 135개]
    
    Filter --> End([완료])
    
    style Parallel fill:#e6f3ff
    style Merge fill:#ccffcc
```

---

## 확장성 아키텍처

### 플러그인 아키텍처

```mermaid
classDiagram
    class PluginInterface {
        <<interface>>
        +initialize()
        +execute()
        +cleanup()
    }
    
    class DataSourcePlugin {
        +collect_data()
    }
    
    class AnalysisPlugin {
        +analyze()
    }
    
    class ExportPlugin {
        +export()
    }
    
    class PluginManager {
        -List~Plugin~ plugins
        +register_plugin()
        +load_plugins()
        +execute_plugins()
    }
    
    PluginInterface <|.. DataSourcePlugin
    PluginInterface <|.. AnalysisPlugin
    PluginInterface <|.. ExportPlugin
    PluginManager --> PluginInterface
```

### 마이크로서비스 확장 (미래)

```mermaid
graph TB
    subgraph "Desktop App"
        UI[PyQt6 UI]
    end
    
    subgraph "Backend Services (Future)"
        Gateway[API Gateway]
        Auth[Auth Service]
        Analysis[Analysis Service]
        Storage[Storage Service]
        Notification[Notification Service]
    end
    
    subgraph "Data Stores"
        PostgreSQL[(PostgreSQL)]
        Redis[(Redis Cache)]
        S3[(S3 Storage)]
    end
    
    UI --> Gateway
    Gateway --> Auth
    Gateway --> Analysis
    Gateway --> Storage
    Gateway --> Notification
    
    Analysis --> Redis
    Storage --> PostgreSQL
    Storage --> S3
    
    style UI fill:#e6f3ff
    style Gateway fill:#ffe6e6
    style Analysis fill:#fff0e6
    style Storage fill:#e6ffe6
```

---

## 요약

이 문서는 Offline Agent의 소프트웨어 아키텍처를 C4 Model 기반으로 4가지 레벨에서 설명했습니다:

1. **System Context**: 전체 시스템과 외부 시스템의 관계
2. **Container**: 주요 컨테이너 (Desktop App, Analysis Engine, Data Layer)
3. **Component**: 각 컨테이너 내부의 컴포넌트 구조
4. **Code**: 주요 클래스 다이어그램

추가로 아키텍처 패턴, 데이터 흐름, 배포, 보안, 성능, 확장성 측면에서의 아키텍처도 다루었습니다.
