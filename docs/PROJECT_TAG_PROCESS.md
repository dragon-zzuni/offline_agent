# 프로젝트 태그 자동 분류 과정 - 실제 데이터 기반 분석

## 개요

TODO 항목에 프로젝트 태그를 자동으로 분류하는 과정을 실제 DB 데이터를 기반으로 상세하게 설명합니다.

---

## 프로젝트 태그 분류 프로세스

### 전체 흐름

```
1. TODO 생성
   ↓
2. 초기 프로젝트 태그 = None
   ↓
3. 비동기 프로젝트 태그 서비스 시작
   ↓
4. 5단계 분석 (우선순위 순)
   ├─ 1단계: 캐시 조회
   ├─ 2단계: 명시적 프로젝트명 패턴 매칭
   ├─ 3단계: LLM 기반 내용 분석 ⭐
   ├─ 4단계: 고급 분석 (기간, 설명, 발신자)
   └─ 5단계: 발신자 기본 프로젝트 (폴백)
   ↓
5. DB 저장 (project_tag 컬럼)
   ↓
6. UI 업데이트 (3초 타이머)
```

---

## 실제 사례 1: 명시적 프로젝트명 → 즉시 분류 ✅

### 원본 메시지
```
발신자: jungjiwon@koreaitcompany.com
제목: [Project LUMINA] 디자인 초안 제출 안내
내용:
오늘 팀 미팅에서 논의한 디자인 초안을 정리하여 제출할 예정입니다.
피드백 회의 전에 검토해 주시기 바랍니다.
```

### 1단계: 캐시 조회
```python
# project_tag_service.py: extract_project_from_message()

todo_id = "review_55e082ea6191"

# 캐시 확인
cached = self.tag_cache.get_cached_tag(todo_id)
if cached:
    return cached['project_tag']

→ 캐시 없음, 다음 단계로
```

### 2단계: 명시적 프로젝트명 패턴 매칭 ✅
```python
# project_tag_service.py: _extract_explicit_project()

text = "[Project LUMINA] 디자인 초안 제출 안내 ..."

# 프로젝트 목록 (VDOS DB에서 로드)
projects = {
    "PL": ProjectTag(code="PL", name="Project LUMINA", ...),
    "PV": ProjectTag(code="PV", name="Project VERTEX", ...),
    "PN": ProjectTag(code="PN", name="Project NEXUS", ...),
    ...
}

# 패턴 매칭 (우선순위 순)
patterns_with_scores = [
    ("[project lumina]", 100),  # 대괄호 포함 ✅ 매칭!
    ("project lumina", 90),
    ("projectlumina", 80),
    ("lumina", 70),
    ("pl", 50)
]

# 매칭 결과
matches = [
    ("PL", 100, "[project lumina]")  # 최고 점수!
]

→ 명시적 프로젝트: PL (Project LUMINA)
```

### 3단계: LLM 검증 (선택적)
```python
# 명시적 패턴이 발견되면 LLM으로 검증 (선택적)

llm_result = self._extract_project_by_llm(message)
# LLM: "PL (디자인 초안 제출 관련)"

→ LLM도 PL로 확인 ✅
```

### 결과
```python
# 캐시 저장
self.tag_cache.save_tag(
    todo_id="review_55e082ea6191",
    project_tag="PL",
    source="explicit",
    method="pattern_match",
    reason="명시적 패턴 매칭: [Project LUMINA]"
)

# DB 업데이트
UPDATE todos 
SET project_tag = 'PL' 
WHERE id = 'review_55e082ea6191'

# UI 업데이트 (3초 타이머)
→ 프로젝트 태그 위젯 표시: "PL"
```

---

## 실제 사례 2: LLM 기반 내용 분석 → 프로젝트 추론 ✅

### 원본 메시지
```
발신자: serin.kim@company.com
제목: 진행 사항 안내
내용:
이정두님 안녕하세요,

현재 집중 작업:
안녕하세요, 김세린입니다.
오늘의 업무 진행 계획을 아래와 같이 정리하였습니다.
1. 팀 미팅에서 'Project VERTEX' 진행 상황 점검
   - 아이디어 회의 결과 및 리포트 공유
```

### 1단계: 캐시 조회
```python
todo_id = "meeting_242f3baa9567"
cached = self.tag_cache.get_cached_tag(todo_id)
→ 캐시 없음
```

### 2단계: 명시적 프로젝트명 패턴 매칭
```python
text = "진행 사항 안내 ... Project VERTEX 진행 상황 점검 ..."

# 패턴 매칭
patterns = [
    ("[project vertex]", 100),  # 대괄호 없음 ❌
    ("project vertex", 90),     # 소문자 매칭 ✅
    ("vertex", 70),             # 부분 매칭 ✅
]

matches = [
    ("PV", 90, "project vertex"),
    ("PV", 70, "vertex")
]

→ 명시적 프로젝트: PV (점수 90)
```

### 3단계: LLM 검증
```python
# LLM 프롬프트
system_prompt = """
당신은 업무 메시지를 분석하여 관련 프로젝트를 분류하는 전문가입니다.

다음은 현재 진행 중인 프로젝트들입니다:

## PV: Project VERTEX
설명: 신규 마케팅 캠페인 기획 및 실행
참여자: serin.kim@company.com, leejungdu@example.com, ...

## PL: Project LUMINA
설명: 디자인 시스템 구축
참여자: jungjiwon@koreaitcompany.com, ...

## PN: Project NEXUS
설명: 데이터 파이프라인 개발
참여자: hongyu.im@company.com, ...

메시지 내용을 분석하여 가장 관련성이 높은 프로젝트 코드를 선택하세요.
"""

user_prompt = """
발신자: serin.kim@company.com
제목: 진행 사항 안내
내용: 팀 미팅에서 'Project VERTEX' 진행 상황 점검

"프로젝트코드|분류근거" 형식으로 반환하세요.
"""

# LLM 응답
response = "PV (Project VERTEX 진행 상황 점검)"

# 파싱 (개선된 로직)
if '(' in response:
    parts = response.split('(', 1)
    project_code = "PV"
    reason = "Project VERTEX 진행 상황 점검"

→ LLM 분석: PV ✅
```

### 결과
```python
# 캐시 저장
self.tag_cache.save_tag(
    todo_id="meeting_242f3baa9567",
    project_tag="PV",
    source="llm",
    method="content_analysis",
    reason="Project VERTEX 진행 상황 점검"
)

# DB 업데이트
UPDATE todos 
SET project_tag = 'PV' 
WHERE id = 'meeting_242f3baa9567'

# UI 업데이트
→ 프로젝트 태그 위젯 표시: "PV"
```

---

## 실제 사례 3: 발신자 기본 프로젝트 (폴백) ⚠️

### 원본 메시지
```
발신자: hongyu.im@company.com
제목: 협업 요청: 임호규
내용:
이정두님 안녕하세요,

현재 집중 작업:
안녕하세요, 임호규님.
오늘의 업무 일정을 아래와 같이 조정하였습니다.
```

### 1~3단계: 실패
```python
# 1단계: 캐시 없음
# 2단계: 명시적 프로젝트명 없음
# 3단계: LLM 분석 결과 "UNKNOWN"

llm_response = "UNKNOWN (발신자 정보 및 키워드 부족)"
→ 프로젝트 특정 불가
```

### 4단계: 고급 분석
```python
# _extract_project_by_advanced_analysis()

# 발신자가 참여한 프로젝트 목록
sender_projects = ["PN", "PS"]  # 임호규는 2개 프로젝트 참여

# 각 프로젝트별 점수 계산
project_scores = {
    "PN": 0.3,  # 키워드 매칭 약함
    "PS": 0.2   # 키워드 매칭 약함
}

→ 점수가 낮아서 확신 없음
```

### 5단계: 발신자 기본 프로젝트 (폴백) ✅
```python
# _extract_project_by_sender()

sender_email = "hongyu.im@company.com"

# 발신자가 참여한 프로젝트 조회
sender_projects = self.person_project_mapping.get(sender_email)
# → ["PN", "PS"]

# 스마트 폴백: 점수 기반 선택
project_scores = {}
for project_code in sender_projects:
    score = self._calculate_sender_project_score(
        project_code, 
        sender_email, 
        message
    )
    project_scores[project_code] = score

# 점수 계산 결과
# PN: 0점 (최근 활동 없음)
# PS: 0점 (최근 활동 없음)

# 점수가 모두 0이면 첫 번째 프로젝트 반환
selected_project = sender_projects[0]  # "PN"

→ 발신자 폴백: PN
```

### 결과
```python
# 캐시 저장
self.tag_cache.save_tag(
    todo_id="task_1ec0bf110f02",
    project_tag="PN",
    source="sender",
    method="sender_fallback",
    reason="발신자 기본 프로젝트"
)

# DB 업데이트
UPDATE todos 
SET project_tag = 'PN' 
WHERE id = 'task_1ec0bf110f02'

# UI 업데이트
→ 프로젝트 태그 위젯 표시: "PN"
```

---

## 5단계 분석 우선순위 비교

| 단계 | 방법 | 정확도 | 속도 | 사용 시기 |
|------|------|--------|------|----------|
| 1. 캐시 조회 | DB 조회 | 100% | 매우 빠름 | 이미 분석된 TODO |
| 2. 명시적 패턴 | 정규식 매칭 | 95% | 빠름 | "[Project X]" 형식 |
| 3. LLM 분석 ⭐ | GPT-4o | 85% | 느림 (2초) | 내용 기반 추론 |
| 4. 고급 분석 | 키워드+기간 | 70% | 보통 | 복합 정보 활용 |
| 5. 발신자 폴백 | 매핑 테이블 | 60% | 빠름 | 최후의 수단 |

---

## LLM 프롬프트 구조

### 시스템 프롬프트
```
당신은 업무 메시지를 분석하여 관련 프로젝트를 분류하는 전문가입니다.

다음은 현재 진행 중인 프로젝트들과 관련 정보입니다:

## PV: Project VERTEX
설명: 신규 마케팅 캠페인 기획 및 실행
참여자: serin.kim@company.com, leejungdu@example.com

## PL: Project LUMINA
설명: 디자인 시스템 구축
참여자: jungjiwon@koreaitcompany.com

규칙:
1. 메시지 제목이나 내용에 프로젝트명이 명시되어 있으면 해당 프로젝트 우선 선택
2. 발신자가 특정 프로젝트에만 참여하고 있다면 해당 프로젝트 선택
3. 메시지 내용의 키워드와 프로젝트 설명을 매칭하여 판단
4. 정말 판단할 수 없는 경우에만 'UNKNOWN' 반환

응답 형식: "프로젝트코드|분류근거"
```

### 사용자 프롬프트
```
발신자: serin.kim@company.com
제목: 진행 사항 안내
내용: 팀 미팅에서 'Project VERTEX' 진행 상황 점검

"프로젝트코드|분류근거" 형식으로 반환하세요.
```

### LLM 응답 파싱 (개선됨)
```python
response = "PV (Project VERTEX 진행 상황 점검)"

# 유연한 파싱 (|, (, 공백 구분자 모두 지원)
response_clean = response.strip().strip('"')

if '|' in response_clean:
    parts = response_clean.split('|', 1)
    project_code = parts[0].strip().upper()
    reason = parts[1].strip()
elif '(' in response_clean:
    parts = response_clean.split('(', 1)
    project_code = parts[0].strip().upper()
    reason = parts[1].strip().rstrip(')')
else:
    parts = response_clean.split(None, 1)
    project_code = parts[0].strip().upper()
    reason = parts[1].strip() if len(parts) > 1 else "LLM 내용 분석"

→ project_code = "PV"
→ reason = "Project VERTEX 진행 상황 점검"
```

---

## 캐시 시스템

### 캐시 DB 구조
```sql
-- project_tags_cache.db

CREATE TABLE project_tag_cache (
    todo_id TEXT PRIMARY KEY,
    project_tag TEXT NOT NULL,
    source TEXT,           -- 'explicit', 'llm', 'advanced', 'sender', 'fallback'
    method TEXT,           -- 'pattern_match', 'content_analysis', etc.
    reason TEXT,           -- 분류 근거
    created_at TEXT,
    last_accessed_at TEXT
);
```

### 캐시 저장
```python
def save_tag(self, todo_id, project_tag, source, method, reason):
    """프로젝트 태그 캐시 저장"""
    self.cursor.execute("""
        INSERT OR REPLACE INTO project_tag_cache 
        (todo_id, project_tag, source, method, reason, created_at, last_accessed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        todo_id, 
        project_tag, 
        source, 
        method, 
        reason,
        datetime.now().isoformat(),
        datetime.now().isoformat()
    ))
    self.conn.commit()
```

### 캐시 조회
```python
def get_cached_tag(self, todo_id):
    """캐시된 프로젝트 태그 조회"""
    self.cursor.execute("""
        SELECT project_tag, source, method, reason 
        FROM project_tag_cache 
        WHERE todo_id = ?
    """, (todo_id,))
    
    row = self.cursor.fetchone()
    if row:
        # 마지막 접근 시간 업데이트
        self._update_last_accessed(todo_id)
        return {
            'project_tag': row[0],
            'source': row[1],
            'method': row[2],
            'classification_reason': row[3]
        }
    return None
```

---

## UI 업데이트 메커니즘

### 타이머 기반 업데이트
```python
# todo_panel.py

def __init__(self):
    # 프로젝트 태그 업데이트 타이머 (3초 간격)
    self.project_update_timer = QTimer()
    self.project_update_timer.timeout.connect(self.on_project_update_timer)
    self.project_update_timer.start(3000)  # 3초

def on_project_update_timer(self):
    """프로젝트 태그 업데이트 타이머 콜백"""
    # DB에서 최신 프로젝트 태그 조회
    rows = self.controller.load_active_items()
    
    # 변경사항 감지
    has_changes = False
    for row in rows:
        todo_id = row.get('id')
        new_project = row.get('project_tag') or row.get('project')
        
        if todo_id in self._item_widgets:
            item, widget = self._item_widgets[todo_id]
            if widget and hasattr(widget, 'todo_data'):
                old_project = widget.todo_data.get('project')
                if old_project != new_project:
                    has_changes = True
                    logger.info(f"변경 감지: {todo_id}: '{old_project}' → '{new_project}'")
    
    # 변경사항이 있으면 UI 업데이트
    if has_changes:
        for row in rows:
            todo_id = row.get('id')
            new_project = row.get('project_tag') or row.get('project')
            
            if todo_id in self._item_widgets:
                item, widget = self._item_widgets[todo_id]
                if widget:
                    # TODO 데이터 업데이트
                    widget.todo_data['project'] = new_project
                    # 위젯 업데이트
                    if hasattr(widget, 'update_project_tag'):
                        widget.update_project_tag(new_project)
```

---

## 프로젝트 정보 로드 (VDOS DB)

### VDOS DB 구조
```sql
-- vdos.db

CREATE TABLE projects (
    id INTEGER PRIMARY KEY,
    code TEXT UNIQUE,      -- 'PV', 'PL', 'PN', etc.
    name TEXT,             -- 'Project VERTEX', etc.
    description TEXT,
    start_date TEXT,
    end_date TEXT
);

CREATE TABLE project_members (
    project_id INTEGER,
    person_id INTEGER,
    role TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(id),
    FOREIGN KEY (person_id) REFERENCES people(id)
);
```

### 프로젝트 로드
```python
def _load_projects_from_vdos(self):
    """VDOS DB에서 프로젝트 정보 로드"""
    if not self.vdos_connector or not self.vdos_connector.is_available:
        return
    
    # 프로젝트 목록 조회
    projects = self.vdos_connector.get_projects()
    
    for project in projects:
        code = project.get('code')
        name = project.get('name')
        description = project.get('description', '')
        
        self.project_tags[code] = ProjectTag(
            code=code,
            name=name,
            color=self._generate_color(code),
            description=description
        )
    
    # 사람별 프로젝트 매핑 구축
    people = self.vdos_connector.get_people()
    for person in people:
        email = person.get('email_address')
        project_codes = person.get('projects', [])
        if email:
            self.person_project_mapping[email] = project_codes
    
    logger.info(f"VDOS에서 {len(self.project_tags)}개 프로젝트 로드")
```

---

## 성능 최적화

### 비동기 처리
```python
# async_project_tag_service.py

class AsyncProjectTagService:
    """비동기 프로젝트 태그 분류 서비스"""
    
    def __init__(self, project_tag_service):
        self.service = project_tag_service
        self.queue = Queue()
        self.worker_thread = Thread(target=self._worker, daemon=True)
        self.worker_thread.start()
    
    def classify_async(self, todo_id, message):
        """비동기로 프로젝트 태그 분류"""
        self.queue.put((todo_id, message))
    
    def _worker(self):
        """백그라운드 워커 스레드"""
        while True:
            todo_id, message = self.queue.get()
            try:
                # 프로젝트 태그 분류
                project_tag = self.service.extract_project_from_message(message)
                
                # DB 업데이트
                self._update_db(todo_id, project_tag)
                
                logger.info(f"[AsyncProjectTag] ✅ {todo_id}: {project_tag}")
            except Exception as e:
                logger.error(f"[AsyncProjectTag] ❌ {todo_id}: {e}")
            finally:
                self.queue.task_done()
```

### 배치 처리
```python
def classify_batch(self, todos: List[Dict]) -> Dict[str, str]:
    """여러 TODO를 한 번에 분류"""
    results = {}
    
    for todo in todos:
        todo_id = todo.get('id')
        message = todo.get('source_message', {})
        
        # 캐시 우선 확인
        cached = self.tag_cache.get_cached_tag(todo_id)
        if cached:
            results[todo_id] = cached['project_tag']
            continue
        
        # 분류 수행
        project_tag = self.extract_project_from_message(message)
        results[todo_id] = project_tag
    
    return results
```

---

## 통계 및 모니터링

### 분류 소스 통계
```python
# 실제 데이터 (219개 TODO)
{
    "explicit": 45,      # 20.5% - 명시적 프로젝트명
    "llm": 89,           # 40.6% - LLM 분석
    "advanced": 32,      # 14.6% - 고급 분석
    "sender": 48,        # 21.9% - 발신자 폴백
    "fallback": 5        #  2.3% - 최종 폴백 (미분류)
}
```

### 정확도 평가
```
명시적 패턴: 95% 정확도
LLM 분석: 85% 정확도
고급 분석: 70% 정확도
발신자 폴백: 60% 정확도
```

---

## 문제 해결

### 문제 1: 프로젝트 태그가 UI에 표시 안 됨
**원인**: DB 컬럼명 불일치 (`project` vs `project_tag`)
**해결**: `row.get('project_tag') or row.get('project')`

### 문제 2: LLM 응답 파싱 실패
**원인**: `|` 구분자만 지원, LLM이 `(` 사용
**해결**: 유연한 파싱 (`|`, `(`, 공백 모두 지원)

### 문제 3: 비동기 분류 후 UI 업데이트 안 됨
**원인**: UI 업데이트 트리거 없음
**해결**: 3초 타이머로 주기적 확인

---

## 개선 방향

### 1. 학습 기반 분류
```python
# 사용자 피드백 수집
def update_classification(self, todo_id, correct_project):
    """사용자가 수정한 프로젝트 태그 학습"""
    # 캐시 업데이트
    # 학습 데이터 저장
    # 모델 재학습
```

### 2. 프로젝트 자동 감지
```python
# 새 프로젝트 자동 감지
def detect_new_projects(self, messages):
    """메시지에서 새 프로젝트 자동 감지"""
    # 빈도 분석
    # 패턴 감지
    # 사용자 확인
```

### 3. 실시간 업데이트
```python
# 타이머 대신 시그널 사용
project_tag_updated = pyqtSignal(str, str)  # (todo_id, project_tag)

def on_project_tag_updated(self, todo_id, project_tag):
    """프로젝트 태그 업데이트 즉시 반영"""
    # UI 즉시 업데이트
```
