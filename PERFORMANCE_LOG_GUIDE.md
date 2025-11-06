# 성능 로그 추적 가이드

## 추가된 성능 로그

### 1. 메시지 변환 시간
```
⏱️ 변환 시간: 이메일 X.XX초 (N개), 메시지 X.XX초 (N개)
```

### 2. 중복 제거 시간
```
🔍 중복 메시지 제거: N개 → M개 (K개 중복) - X.XX초
```

### 3. 정렬 시간
```
⏱️ 정렬 시간: X.XX초 (N개)
```

## 앱 재실행 후 확인할 로그

```
2025-11-06 HH:MM:SS - data_sources.virtualoffice_source - INFO - 메시지 수집 시작
2025-11-06 HH:MM:SS - src.integrations.virtualoffice_client - INFO - 메시지 N개 조회 완료
2025-11-06 HH:MM:SS - data_sources.virtualoffice_source - INFO - ⏱️ 변환 시간: ...
2025-11-06 HH:MM:SS - data_sources.virtualoffice_source - INFO - 🔍 중복 메시지 제거: ...
2025-11-06 HH:MM:SS - data_sources.virtualoffice_source - INFO - ⏱️ 정렬 시간: ...
2025-11-06 HH:MM:SS - data_sources.virtualoffice_source - INFO - 메시지 수집 완료
```

## 예상 병목 지점

1. **메시지 변환** (가장 가능성 높음)
   - 7080개 메시지를 하나씩 변환
   - 각 메시지마다 persona_map 조회
   - 예상 시간: 2-3초

2. **중복 제거**
   - set 연산으로 빠름
   - 예상 시간: 0.1초 미만

3. **정렬**
   - Python의 Timsort (효율적)
   - 예상 시간: 0.1-0.2초

## 최적화 방안

### 즉시 적용 가능
1. **변환 함수 최적화**
   - persona_map 조회 캐싱
   - 불필요한 문자열 연산 제거

2. **배치 처리**
   - 1000개씩 청크로 나눠서 처리
   - 진행 상황 로그 출력

### 추가 최적화 (필요시)
1. **병렬 변환**
   - ThreadPoolExecutor로 변환 병렬화
   - CPU 코어 수만큼 워커 생성

2. **캐싱 강화**
   - 변환 결과 캐싱 (msg_id 기반)
   - 증분 수집 시 재변환 방지

## 다음 단계

1. **앱 재실행**
   ```bash
   python offline_agent/run_gui.py
   ```

2. **로그 확인**
   - 각 단계별 시간 측정
   - 가장 느린 부분 식별

3. **최적화 적용**
   - 병목 지점에 집중
   - 단계별로 개선 효과 측정
