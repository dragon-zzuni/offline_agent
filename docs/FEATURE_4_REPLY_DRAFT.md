# 기능 4: 회신 초안 자동 작성

## TODO 상세 페이지에서 자동 요약 + 회신 초안 생성

```mermaid
flowchart TD
    Start([TODO 상세 페이지 열기]) --> LoadTodo[TODO 정보 로드<br/>- Title<br/>- Description<br/>- Evidence<br/>- Priority]
    
    LoadTodo --> ShowDetail[상세 정보 표시<br/>TodoDetailDialog]
    
    ShowDetail --> UserAction{사용자 액션}
    
    UserAction -->|회신 초안 생성| StartDraft[회신 초안 생성 시작]
    UserAction -->|닫기| End([완료])
    
    StartDraft --> GatherContext[컨텍스트 수집]
    
    GatherContext --> ExtractRequester[요청자 정보<br/>- 이름<br/>- 역할<br/>- 이메일/핸들]
    
    GatherContext --> ExtractDeadline[데드라인 정보<br/>- 명시적 데드라인<br/>- 암묵적 긴급도]
    
    GatherContext --> ExtractContent[요청 내용<br/>- 핵심 요청사항<br/>- 배경 정보<br/>- 기대사항]
    
    ExtractRequester --> BuildPrompt
    ExtractDeadline --> BuildPrompt
    ExtractContent --> BuildPrompt
    
    BuildPrompt[프롬프트 구성] --> PromptTemplate[템플릿 적용<br/>- 인사말<br/>- 본문 구조<br/>- 마무리]
    
    PromptTemplate --> AddPersonalization[개인화 요소 추가<br/>- 요청자 이름<br/>- 프로젝트명<br/>- 맥락 반영]
    
    AddPersonalization --> GPT4[GPT-4o API 호출<br/>회신 초안 생성]
    
    GPT4 --> GenerateDraft[초안 생성<br/>- 인사 및 감사<br/>- 요청 확인<br/>- 답변/계획<br/>- 데드라인 언급<br/>- 마무리]
    
    GenerateDraft --> ParseDraft[초안 파싱<br/>- 제목<br/>- 본문<br/>- 서명]
    
    ParseDraft --> ShowDraft[초안 표시<br/>편집 가능한 텍스트]
    
    ShowDraft --> UserReview{사용자 검토}
    
    UserReview -->|수정| EditDraft[초안 수정<br/>실시간 편집]
    UserReview -->|재생성| RegenerateDraft[재생성 요청<br/>다른 톤/스타일]
    UserReview -->|복사| CopyDraft[클립보드 복사]
    UserReview -->|저장| SaveDraft[파일로 저장<br/>.txt 또는 .md]
    
    EditDraft --> ShowDraft
    RegenerateDraft --> GPT4
    
    CopyDraft --> Notify[복사 완료 알림]
    SaveDraft --> Notify
    
    Notify --> End
    
    style GatherContext fill:#e6f3ff
    style GPT4 fill:#ffe6e6
    style ShowDraft fill:#ccffcc
    style UserReview fill:#fff0e6
```


## 맞춤형 회신 생성 상세 플로우

```mermaid
flowchart TD
    Start([회신 초안 생성]) --> AnalyzeRequester[요청자 분석]
    
    AnalyzeRequester --> CheckRole{요청자 역할}
    
    CheckRole -->|CEO/임원| ToneFormal[격식 있는 톤<br/>'검토하겠습니다']
    CheckRole -->|PM/리더| ToneProf[전문적인 톤<br/>'확인했습니다']
    CheckRole -->|팀원| ToneFriendly[친근한 톤<br/>'확인했어요']
    
    ToneFormal --> AnalyzeContext
    ToneProf --> AnalyzeContext
    ToneFriendly --> AnalyzeContext
    
    AnalyzeContext[맥락 분석] --> CheckUrgency{긴급도}
    
    CheckUrgency -->|High| ResponseQuick[신속 대응 강조<br/>'즉시 처리하겠습니다']
    CheckUrgency -->|Medium| ResponseNormal[일반 대응<br/>'검토 후 회신드리겠습니다']
    CheckUrgency -->|Low| ResponseRelaxed[여유 있는 대응<br/>'확인 후 공유드리겠습니다']
    
    ResponseQuick --> AnalyzeDeadline
    ResponseNormal --> AnalyzeDeadline
    ResponseRelaxed --> AnalyzeDeadline
    
    AnalyzeDeadline[데드라인 분석] --> CheckDeadline{데드라인 명시?}
    
    CheckDeadline -->|Yes| MentionDeadline[데드라인 언급<br/>'X일까지 완료하겠습니다']
    CheckDeadline -->|No| EstimateTime[예상 시간 제시<br/>'이번 주 내 완료 예정']
    
    MentionDeadline --> BuildStructure
    EstimateTime --> BuildStructure
    
    BuildStructure[구조 구성] --> Greeting[1. 인사 및 감사<br/>'안녕하세요, 메시지 감사합니다']
    
    Greeting --> Acknowledge[2. 요청 확인<br/>'X 건에 대해 확인했습니다']
    
    Acknowledge --> Response[3. 답변/계획<br/>'다음과 같이 진행하겠습니다']
    
    Response --> Timeline[4. 일정 제시<br/>'X일까지 완료 예정입니다']
    
    Timeline --> Closing[5. 마무리<br/>'추가 문의사항 있으시면 말씀해주세요']
    
    Closing --> Signature[6. 서명<br/>'감사합니다, [이름]']
    
    Signature --> FinalDraft[최종 초안 완성]
    
    FinalDraft --> QualityCheck{품질 검증}
    
    QualityCheck -->|Pass| Output[초안 출력]
    QualityCheck -->|Fail| Regenerate[재생성]
    
    Regenerate --> BuildStructure
    
    Output --> End([완료])
    
    style AnalyzeRequester fill:#e6f3ff
    style AnalyzeContext fill:#ffe6e6
    style AnalyzeDeadline fill:#fff0e6
    style BuildStructure fill:#e6ffe6
    style FinalDraft fill:#ccffcc
```
