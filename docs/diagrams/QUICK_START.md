# 🚀 다이어그램 PNG 변환 - 빠른 시작 가이드

## ⚡ 가장 빠른 방법 (1분)

### 1. HTML 뷰어 사용 (즉시 확인)

```bash
# viewer.html 파일을 브라우저로 열기
start viewer.html  # Windows
open viewer.html   # Mac
```

브라우저에서 다이어그램을 확인하고 **우클릭 → 이미지 저장**으로 PNG 저장!

---

### 2. Mermaid Live Editor (온라인, 추천!)

**단계:**
1. https://mermaid.live/ 접속
2. 원하는 .mmd 파일 열기 (메모장)
3. 내용 복사 → 왼쪽 에디터에 붙여넣기
4. 우측 상단 "Actions" → "PNG" → "4x" 선택
5. 다운로드!

**파일 목록:**
- `system_architecture.mmd` - 전체 구조
- `layer_architecture.mmd` - 레이어 구조  
- `detailed_structure.mmd` - 상세 구조
- `data_flow.mmd` - 데이터 플로우

**장점:**
✅ 설치 불필요  
✅ 고해상도 (4x = 4배 확대)  
✅ 한글 완벽 지원  
✅ 배경색 선택 가능  

---

## 📊 PPT/PDF에 바로 넣기

### PowerPoint

1. Mermaid Live에서 PNG 다운로드 (4x 해상도)
2. PPT 열기 → "삽입" → "그림"
3. 다운로드한 PNG 선택
4. 크기 조정 (Shift 누르고 드래그)

**권장 설정:**
- 해상도: 4x (고해상도)
- 배경: 흰색
- 크기: 슬라이드 너비의 80-90%

---

## 🎨 고급 옵션

### 로컬 변환 (Mermaid CLI)

```bash
# 설치 (Node.js 필요)
npm install -g @mermaid-js/mermaid-cli

# 변환
mmdc -i system_architecture.mmd -o system_architecture.png -w 1920 -H 1080 -b white

# 또는 배치 파일 실행
generate_diagrams.bat
```

---

## 📁 생성할 파일

발표 자료용으로 다음 4개 PNG 파일을 생성하세요:

1. **system_architecture.png** (1920x1080)
   - 전체 시스템 구조
   - 슬라이드 1-2장

2. **layer_architecture.png** (1920x1080)
   - 4계층 아키텍처
   - 슬라이드 3-4장

3. **detailed_structure.png** (2400x1600)
   - 상세 컴포넌트 구조
   - 슬라이드 5-6장

4. **data_flow.png** (2400x1600)
   - 시퀀스 다이어그램
   - 슬라이드 7-8장

---

## 💡 팁

### 고해상도 출력
- Mermaid Live: **4x 해상도** 선택
- CLI: `-w 3840 -H 2160` (4K)

### 배경색
- PPT 흰색 배경: `-b white`
- 투명 배경: `-b transparent`

### 한글 깨짐 방지
- Mermaid Live 사용 (자동 처리)
- 또는 폰트 설정:
  ```mermaid
  %%{init: {'themeVariables': { 'fontFamily':'Malgun Gothic'}}}%%
  ```

---

## 🆘 문제 해결

**Q: 다이어그램이 잘림**  
A: 해상도 증가 또는 4x 선택

**Q: 한글이 깨짐**  
A: Mermaid Live 사용 (권장)

**Q: CLI 설치 실패**  
A: 온라인 도구 사용 (설치 불필요)

---

## 📞 더 자세한 정보

- 전체 가이드: `README.md`
- 원본 문서: `../../ARCHITECTURE_PRESENTATION.md`
- Mermaid 공식: https://mermaid.js.org/

---

**작성일**: 2025-10-31
