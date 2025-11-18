# Offline Agent 아키텍처 (11/17 업데이트)

## 전체 시스템 아키텍처

```mermaid
graph TB
    subgraph "UI Layer"
        MainWindow[MainWindow<br/>메인 윈도우]
        TodoPanel[TodoPanel<br/>TODO 관리]
        MessagePanel[MessagePanel<br/>메시지 그룹화]
        EmailPanel[EmailPanel<br/>이메일 필터링]
        AnalysisPanel[AnalysisResultPanel<br/>분석 결과]
    end
    
    subgraph "Service Layer"
        AnalysisPipeline[AnalysisPipelineService<br/>분석 파이프라인]
        Top3Service[Top3LLMSelector<br/>LLM 자동 선정]
        ProjectTagService[ProjectTagService<br/>프로젝트 태그]
        PersonaCacheService[PersonaTodoCacheService<br/>페르소나별 캐시]
        DeduplicationService[TodoDeduplicationService<br/>중복 제거]
    end
    
    subgraph "Data Layer"
        DataSourceManager[DataSourceManager<br/>데이터 소스 관리]
        VirtualOfficeSource[VirtualOfficeDataSource<br/>VirtualOffice API]
        TodoRepository[TodoRepository<br/>TODO 저장소]
        ProjectTagCache[ProjectTagCache<br/>프로젝트 태그 캐시]
    end
    
    subgraph "NLP Layer"
        PriorityRanker[PriorityRanker<br/>우선순위 분석]
        Summarizer[MessageSummarizer<br/>메시지 요약]
        ActionExtractor[ActionExtractor<br/>액션 추출]
        MessageGrouping[MessageGrouping<br/>메시지 그룹화]
    end
    
    subgraph "External Systems"
        VirtualOfficeAPI[VirtualOffice API<br/>Email/Chat/Sim]
        OpenAI[OpenAI API<br/>GPT-4o]
        SQLite[(SQLite DB<br/>todos_cache.db)]
    end
    
    MainWindow --> AnalysisPipeline
    MainWindow --> TodoPanel
    MainWindow --> MessagePanel
    MainWindow --> EmailPanel
    
    TodoPanel --> TodoRepository
    TodoPanel --> PersonaCacheService
    
    AnalysisPipeline --> DataSourceManager
    AnalysisPipeline --> PriorityRanker
    AnalysisPipeline --> Summarizer
    AnalysisPipeline --> ActionExtractor
    AnalysisPipeline --> Top3Service
    AnalysisPipeline --> DeduplicationService
    
    DataSourceManager --> VirtualOfficeSource
    VirtualOfficeSource --> VirtualOfficeAPI
    
    TodoRepository --> SQLite
    ProjectTagCache --> SQLite
    PersonaCacheService --> TodoRepository
    
    PriorityRanker --> OpenAI
    Summarizer --> OpenAI
    ActionExtractor --> OpenAI
    Top3Service --> OpenAI
    
    MessagePanel --> MessageGrouping
    ProjectTagService --> ProjectTagCache
```

## 데이터 수집 및 필터링 플로우

```mermaid
flowchart TD
    Start([페르소나 선택]) --> CheckCache{캐시 확인}
    
    CheckCache -->|캐시 히트| LoadCache[캐시에서 로드]
    CheckCache -->|캐시 미스| CollectData[데이터 수집 시작]
    
    LoadCache --> StartPolling[정기 폴링 시작]
    
    CollectData --> APICall[VirtualOffice API 호출]
    APICall --> EmailAPI[Email API<br/>mailbox 기준]
    APICall --> ChatAPI[Chat API<br/>handle 기준]
    
    EmailAPI --> Convert1[내부 포맷 변환<br/>recipient_type 판별]
    ChatAPI --> Convert2[내부 포맷 변환<br/>recipient_type 판별]
    
    Convert1 --> Merge[메시지 통합]
    Convert2 --> Merge
    
    Merge --> FilterFrom{발신 메시지<br/>필터링}
    FilterFrom -->|recipient_type='from'| Remove[제외]
    FilterFrom -->|recipient_type='to/cc/bcc'| Keep[유지]
    
    Remove --> FilterResult[필터링 완료]
    Keep --> FilterResult
    
    FilterResult --> SimTime[시뮬레이션 시간<br/>메타데이터 주입]
    SimTime --> Sort[날짜순 정렬]
    Sort --> Cache[캐시 저장]
    Cache --> Display[UI 표시]
    
    Display --> StartPolling
    
    StartPolling --> PollingLoop{정기 폴링<br/>5초마다}
    PollingLoop --> NewData{새 데이터?}
    NewData -->|있음| ProcessNew[새 메시지 처리]
    NewData -->|없음| PollingLoop
    
    ProcessNew --> ReAnalysis{재분석 필요?}
    ReAnalysis -->|페르소나 변경| ForceAnalysis[강제 재분석]
    ReAnalysis -->|캐시 히트 후| Skip[건너뛰기]
    ReAnalysis -->|일반 폴링| AutoAnalysis[자동 재분석]
    
    ForceAnalysis --> TodoGeneration
    AutoAnalysis --> TodoGeneration
    Skip --> PollingLoop
    
    TodoGeneration[TODO 생성 파이프라인]
    
    style FilterFrom fill:#ff9999
    style Remove fill:#ffcccc
    style Keep fill:#ccffcc
```

## TODO 생성 파이프라인

```mermaid
flowchart TD
    Start([메시지 수집 완료]) --> FilterStep1[1단계: 메시지 필터링]
    
    FilterStep1 --> ContentDup[본문 중복 제거<br/>유사도 90% 이상]
    ContentDup --> ShortMsg[짧은 메시지 제거<br/>20자 미만]
    ShortMsg --> SimpleGreet[단순 인사 제거<br/>'안녕하세요' 등]
    SimpleGreet --> SimpleUpdate[단순 업데이트 제거<br/>'공유드립니다' 등]
    SimpleUpdate --> RecipientPriority[TO/CC/BCC 우선순위<br/>TO > CC > BCC]
    
    RecipientPriority --> Merge[2단계: 메시지 병합<br/>90초 윈도우]
    
    Merge --> Priority[3단계: 우선순위 분석]
    Priority --> KeywordCheck{키워드 기반<br/>우선순위 판별}
    
    KeywordCheck -->|High| HighPriority[High 우선순위]
    KeywordCheck -->|Medium| MediumPriority[Medium 우선순위]
    KeywordCheck -->|Low| LowPriority[Low 우선순위]
    KeywordCheck -->|불확실| LLMPriority[LLM 우선순위 분석]
    
    LLMPriority --> HighPriority
    LLMPriority --> MediumPriority
    LLMPriority --> LowPriority
    
    HighPriority --> Summary[4단계: 메시지 요약<br/>LLM 기반]
    MediumPriority --> Summary
    LowPriority --> Summary
    
    Summary --> ActionExtract[5단계: 액션 추출<br/>LLM 기반]
    
    ActionExtract --> TempTodo[임시 TODO 생성<br/>1차 저장]
    
    TempTodo --> ProjectTag[6단계: 프로젝트 태그<br/>LLM 분석]
    ProjectTag --> Dedup[7단계: 중복 제거<br/>유사도 기반]
    
    Dedup --> FinalTodo[최종 TODO 저장]
    
    FinalTodo --> Top3Check{Top3 선정 필요?}
    Top3Check -->|Yes| Top3LLM[8단계: Top3 LLM 선정<br/>자연스러운 우선순위]
    Top3Check -->|No| Display
    
    Top3LLM --> Display[UI 표시]
    
    style FilterStep1 fill:#ffe6e6
    style Priority fill:#e6f3ff
    style Summary fill:#e6ffe6
    style ActionExtract fill:#fff0e6
    style ProjectTag fill:#f0e6ff
    style Top3LLM fill:#ffe6f0
```

## 페르소나별 캐싱 시스템

```mermaid
flowchart TD
    Start([페르소나 선택]) --> GenerateKey[캐시 키 생성<br/>email_handle]
    
    GenerateKey --> CheckCache{캐시 존재?}
    
    CheckCache -->|Yes| ValidateCache{캐시 유효?<br/>14일 이내}
    CheckCache -->|No| FetchNew[새로 수집]
    
    ValidateCache -->|Valid| LoadCache[캐시 로드]
    ValidateCache -->|Expired| CleanCache[만료 캐시 삭제]
    
    CleanCache --> FetchNew
    
    LoadCache --> CheckPersona{페르소나별<br/>TODO 존재?}
    
    CheckPersona -->|Yes| LoadPersonaTodo[페르소나 TODO 로드]
    CheckPersona -->|No| CreatePersonaTodo[페르소나 TODO 생성]
    
    LoadPersonaTodo --> Display[UI 표시]
    CreatePersonaTodo --> Display
    
    FetchNew --> Collect[데이터 수집]
    Collect --> Filter[필터링]
    Filter --> Analyze[분석]
    Analyze --> SaveCache[캐시 저장]
    
    SaveCache --> SavePersonaTodo[페르소나별 TODO 저장<br/>persona_name/email/handle]
    SavePersonaTodo --> Display
    
    Display --> PollingStart[정기 폴링 시작]
    
    PollingStart --> PollingLoop{5초마다 체크}
    PollingLoop --> NewMsg{새 메시지?}
    
    NewMsg -->|Yes| IncrementalFetch[증분 수집<br/>since_id 사용]
    NewMsg -->|No| PollingLoop
    
    IncrementalFetch --> UpdateCache[캐시 업데이트]
    UpdateCache --> ReAnalyze[재분석]
    ReAnalyze --> UpdatePersonaTodo[페르소나 TODO 업데이트]
    UpdatePersonaTodo --> Notify[UI 알림]
    Notify --> PollingLoop
    
    style CheckCache fill:#e6f3ff
    style LoadCache fill:#ccffcc
    style SaveCache fill:#ffcccc
    style PollingLoop fill:#fff0e6
```

## 프로젝트 태그 시스템

```mermaid
flowchart TD
    Start([TODO 생성]) --> CheckEvidence{Evidence 존재?}
    
    CheckEvidence -->|No| NoTag[태그 없음]
    CheckEvidence -->|Yes| ExtractContext[컨텍스트 추출<br/>subject + body]
    
    ExtractContext --> CheckCache{프로젝트 태그<br/>캐시 확인}
    
    CheckCache -->|캐시 히트| LoadTag[캐시에서 로드]
    CheckCache -->|캐시 미스| LLMAnalysis[LLM 분석<br/>프로젝트 식별]
    
    LLMAnalysis --> ParseResult{파싱 성공?}
    
    ParseResult -->|Yes| ValidateTag{유효한 태그?}
    ParseResult -->|No| RetryParse[재시도<br/>최대 2회]
    
    RetryParse --> ParseResult
    
    ValidateTag -->|Valid| SaveCache[캐시 저장<br/>content_hash 기준]
    ValidateTag -->|Invalid| NoTag
    
    SaveCache --> AssignTag[TODO에 태그 할당]
    LoadTag --> AssignTag
    
    AssignTag --> UpdateUI[UI 업데이트<br/>프로젝트별 그룹화]
    NoTag --> UpdateUI
    
    UpdateUI --> AsyncBatch{비동기 배치<br/>처리 필요?}
    
    AsyncBatch -->|Yes| QueueBatch[배치 큐에 추가<br/>10개씩 묶음]
    AsyncBatch -->|No| Complete
    
    QueueBatch --> ProcessBatch[백그라운드 처리<br/>병렬 LLM 호출]
    ProcessBatch --> UpdateCache[캐시 일괄 업데이트]
    UpdateCache --> Complete([완료])
    
    style CheckCache fill:#e6f3ff
    style LLMAnalysis fill:#ffe6e6
    style SaveCache fill:#ccffcc
    style AsyncBatch fill:#fff0e6
```

## 메시지 그룹화 시스템

```mermaid
flowchart TD
    Start([메시지 탭 선택]) --> LoadMessages[메시지 로드]
    
    LoadMessages --> CheckGrouping{그룹화 모드?}
    
    CheckGrouping -->|시간 기반| TimeGroup[시간 범위 그룹화]
    CheckGrouping -->|발신자 기반| SenderGroup[발신자별 그룹화]
    CheckGrouping -->|프로젝트 기반| ProjectGroup[프로젝트별 그룹화]
    
    TimeGroup --> SelectRange{범위 선택}
    SelectRange -->|Day| DayGroup[일별 그룹<br/>sim_day_index]
    SelectRange -->|Week| WeekGroup[주별 그룹<br/>sim_week_index]
    SelectRange -->|Month| MonthGroup[월별 그룹<br/>sim_month_index]
    
    DayGroup --> DisplayGroup
    WeekGroup --> DisplayGroup
    MonthGroup --> DisplayGroup
    
    SenderGroup --> GroupBySender[발신자별 분류<br/>sender 기준]
    GroupBySender --> DisplayGroup
    
    ProjectGroup --> ExtractProject[프로젝트 추출<br/>subject 파싱]
    ExtractProject --> GroupByProject[프로젝트별 분류]
    GroupByProject --> DisplayGroup
    
    DisplayGroup[그룹 표시] --> ExpandGroup{그룹 확장?}
    
    ExpandGroup -->|Yes| ShowDetails[상세 메시지 표시<br/>시간순 정렬]
    ExpandGroup -->|No| ShowSummary[요약 정보만 표시<br/>개수, 최신 메시지]
    
    ShowDetails --> MessageDetail[메시지 상세 다이얼로그]
    ShowSummary --> MessageDetail
    
    MessageDetail --> ShowEvidence{Evidence 표시}
    ShowEvidence --> ShowMetadata[메타데이터 표시<br/>sim_time, project 등]
    
    ShowMetadata --> Complete([완료])
    
    style TimeGroup fill:#e6f3ff
    style SenderGroup fill:#ffe6e6
    style ProjectGroup fill:#e6ffe6
```

## 캐시 및 성능 최적화

```mermaid
flowchart TD
    Start([시스템 시작]) --> InitCache[캐시 초기화]
    
    InitCache --> LoadPersonas[페르소나 목록 로드]
    LoadPersonas --> BuildMaps[페르소나 맵 구성<br/>email/handle 기준]
    
    BuildMaps --> CheckDB{DB 연결 확인}
    
    CheckDB -->|성공| LoadTickLog[tick_log 로드<br/>시뮬레이션 시간]
    CheckDB -->|실패| SkipSimTime[시뮬레이션 시간<br/>매핑 건너뛰기]
    
    LoadTickLog --> BuildTimeMap[시간 매핑 구성<br/>tick → datetime]
    BuildTimeMap --> Ready
    SkipSimTime --> Ready
    
    Ready[시스템 준비 완료] --> UserAction{사용자 액션}
    
    UserAction -->|페르소나 변경| ChangePersona[페르소나 변경]
    UserAction -->|시간 범위 변경| ChangeTimeRange[시간 범위 변경]
    UserAction -->|새로고침| ManualRefresh[수동 새로고침]
    
    ChangePersona --> InvalidateCache[캐시 무효화]
    InvalidateCache --> ResetIDs[증분 수집 ID 리셋]
    ResetIDs --> FullReload[전체 재수집]
    
    ChangeTimeRange --> FilterCache[캐시 필터링<br/>시간 범위 적용]
    FilterCache --> QuickDisplay[빠른 표시]
    
    ManualRefresh --> IncrementalFetch[증분 수집<br/>since_id 사용]
    IncrementalFetch --> MergeCache[캐시 병합]
    
    FullReload --> SaveCache[캐시 저장]
    MergeCache --> SaveCache
    
    SaveCache --> CleanupCheck{정리 필요?}
    
    CleanupCheck -->|메시지 > 11000| CleanupOld[오래된 메시지 정리<br/>최신 10000개 유지]
    CleanupCheck -->|TODO > 14일| CleanupExpired[만료 TODO 삭제]
    CleanupCheck -->|No| UpdateUI
    
    CleanupOld --> UpdateUI
    CleanupExpired --> UpdateUI
    
    UpdateUI[UI 업데이트] --> Ready
    
    style InitCache fill:#e6f3ff
    style InvalidateCache fill:#ffcccc
    style SaveCache fill:#ccffcc
    style CleanupCheck fill:#fff0e6
```

## 주요 컴포넌트 상호작용

```mermaid
sequenceDiagram
    participant User
    participant MainWindow
    participant AnalysisPipeline
    participant DataSource
    participant VirtualOfficeAPI
    participant NLP
    participant TodoRepository
    participant UI
    
    User->>MainWindow: 페르소나 선택 (이정두)
    MainWindow->>AnalysisPipeline: analyze_messages()
    
    AnalysisPipeline->>DataSource: collect_messages()
    DataSource->>VirtualOfficeAPI: get_emails(mailbox)
    DataSource->>VirtualOfficeAPI: get_messages(handle)
    
    VirtualOfficeAPI-->>DataSource: 이메일 105개
    VirtualOfficeAPI-->>DataSource: 채팅 133개
    
    DataSource->>DataSource: 내부 포맷 변환<br/>recipient_type 판별
    DataSource->>DataSource: 발신 메시지 필터링<br/>238개 → 135개
    DataSource->>DataSource: 시뮬레이션 시간 주입
    
    DataSource-->>AnalysisPipeline: 필터링된 메시지 135개
    
    AnalysisPipeline->>AnalysisPipeline: apply_all_filters()<br/>중복/짧은 메시지 제거
    AnalysisPipeline->>AnalysisPipeline: coalesce_messages()<br/>90초 윈도우 병합
    
    AnalysisPipeline->>NLP: 우선순위 분석
    NLP-->>AnalysisPipeline: High/Medium/Low
    
    AnalysisPipeline->>NLP: 메시지 요약
    NLP-->>AnalysisPipeline: 요약 텍스트
    
    AnalysisPipeline->>NLP: 액션 추출
    NLP-->>AnalysisPipeline: TODO 리스트
    
    AnalysisPipeline->>TodoRepository: save_todo()<br/>임시 저장
    
    AnalysisPipeline->>NLP: 프로젝트 태그 분석
    NLP-->>AnalysisPipeline: 프로젝트 태그
    
    AnalysisPipeline->>AnalysisPipeline: 중복 제거
    
    AnalysisPipeline->>TodoRepository: update_todo()<br/>최종 저장
    
    AnalysisPipeline->>NLP: Top3 LLM 선정
    NLP-->>AnalysisPipeline: Top3 TODO
    
    AnalysisPipeline-->>MainWindow: 분석 완료
    
    MainWindow->>UI: 결과 표시
    UI-->>User: TODO 리스트 표시
    
    Note over MainWindow,DataSource: 정기 폴링 시작 (5초마다)
    
    loop 정기 폴링
        MainWindow->>DataSource: collect_new_data_batch()
        DataSource->>VirtualOfficeAPI: 증분 수집 (since_id)
        VirtualOfficeAPI-->>DataSource: 새 메시지
        DataSource->>DataSource: 발신 메시지 필터링
        DataSource-->>MainWindow: 새 메시지 (필터링됨)
        
        alt 새 메시지 있음
            MainWindow->>AnalysisPipeline: 재분석
            AnalysisPipeline-->>UI: UI 업데이트
        else 새 메시지 없음
            MainWindow->>MainWindow: 대기
        end
    end
```

## 핵심 데이터 구조

```mermaid
classDiagram
    class Message {
        +str msg_id
        +str sender
        +str sender_email
        +str sender_handle
        +str subject
        +str body
        +str content
        +datetime date
        +str type (email/messenger)
        +str recipient_type (to/cc/bcc/from)
        +dict metadata
        +str simulated_datetime
        +int sim_day_index
        +int sim_week_index
    }
    
    class Todo {
        +int id
        +str title
        +str description
        +str priority (High/Medium/Low)
        +str status (Pending/Completed)
        +datetime created_at
        +datetime due_date
        +str project_tag
        +str persona_name
        +str persona_email
        +str persona_handle
        +list evidence
        +list reasoning
        +bool is_top3
    }
    
    class Persona {
        +int id
        +str name
        +str email_address
        +str chat_handle
        +str role
        +dict metadata
    }
    
    class ProjectTag {
        +int id
        +str content_hash
        +str project_name
        +str confidence
        +datetime created_at
        +dict metadata
    }
    
    class CacheEntry {
        +str cache_key
        +str persona_email
        +str persona_handle
        +datetime last_updated
        +int message_count
        +int todo_count
        +bool is_valid
    }
    
    Message "1..*" --> "1" Persona : sent_by
    Todo "1..*" --> "1..*" Message : evidence
    Todo "1" --> "1" Persona : assigned_to
    Todo "1" --> "0..1" ProjectTag : tagged_with
    CacheEntry "1" --> "1" Persona : belongs_to
    CacheEntry "1" --> "1..*" Todo : contains
```

## 성능 최적화 포인트

1. **데이터 수집 최적화**
   - 병렬 API 호출 (이메일 + 채팅 동시 수집)
   - 증분 수집 (since_id 사용)
   - 발신 메시지 조기 필터링 (238개 → 135개)

2. **캐싱 전략**
   - 페르소나별 캐시 (14일 TTL)
   - 프로젝트 태그 캐시 (content_hash 기반)
   - 시뮬레이션 상태 캐시 (2초 TTL)

3. **메모리 관리**
   - 메시지 캐시 자동 정리 (최대 10,000개)
   - TODO 자동 삭제 (14일 경과)
   - 만료 캐시 정리

4. **LLM 호출 최적화**
   - 키워드 기반 우선순위 판별 (LLM 호출 감소)
   - 배치 처리 (프로젝트 태그 10개씩)
   - 비동기 백그라운드 처리

5. **UI 반응성**
   - 임시 TODO 즉시 표시 (1차 저장)
   - 백그라운드 LLM 분석 (2차 업데이트)
   - 정기 폴링 (5초 간격)
