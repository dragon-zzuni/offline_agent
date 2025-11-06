@echo off
REM Mermaid 다이어그램을 PNG로 변환하는 스크립트
REM 사전 요구사항: npm install -g @mermaid-js/mermaid-cli

echo Mermaid CLI로 다이어그램 생성 중...

REM 1. 전체 구조
mmdc -i system_architecture.mmd -o system_architecture.png -w 1920 -H 1080 -b white

REM 2. 레이어 구조
mmdc -i layer_architecture.mmd -o layer_architecture.png -w 1920 -H 1080 -b white

REM 3. 상세 구조
mmdc -i detailed_structure.mmd -o detailed_structure.png -w 2400 -H 1600 -b white

REM 4. 데이터 플로우
mmdc -i data_flow.mmd -o data_flow.png -w 2400 -H 1600 -b white

echo 완료! PNG 파일이 생성되었습니다.
pause
