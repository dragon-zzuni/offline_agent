@echo off
REM Smart Assistant 실행 스크립트 (Conda 전용)
REM Anaconda/Miniconda 사용자를 위한 스크립트

REM 현재 디렉토리를 스크립트 위치로 변경
cd /d "%~dp0"

REM 콘솔 창 제목 설정
title Smart Assistant v1.0

REM UTF-8 인코딩 설정
chcp 65001 >nul

echo ========================================
echo   Smart Assistant 시작 중...
echo ========================================
echo.

REM Conda 초기화 및 base 환경 활성화
if exist "%USERPROFILE%\miniconda3\Scripts\conda.exe" (
    call "%USERPROFILE%\miniconda3\Scripts\activate.bat"
    call conda activate base
    goto :run_app
)

if exist "%USERPROFILE%\anaconda3\Scripts\conda.exe" (
    call "%USERPROFILE%\anaconda3\Scripts\activate.bat"
    call conda activate base
    goto :run_app
)

REM C:\ProgramData 경로도 확인
if exist "C:\ProgramData\miniconda3\Scripts\conda.exe" (
    call "C:\ProgramData\miniconda3\Scripts\activate.bat"
    call conda activate base
    goto :run_app
)

if exist "C:\ProgramData\anaconda3\Scripts\conda.exe" (
    call "C:\ProgramData\anaconda3\Scripts\activate.bat"
    call conda activate base
    goto :run_app
)

echo [오류] Conda를 찾을 수 없습니다.
echo Anaconda Prompt를 열고 다음 명령어를 실행하세요:
echo   cd "%~dp0"
echo   python run_gui.py
echo.
pause
exit /b 1

:run_app
echo Conda 환경 활성화 완료
echo Smart Assistant 실행 중...
echo.
python run_gui.py

REM 오류 발생 시 대기
if errorlevel 1 (
    echo.
    echo ========================================
    echo   오류가 발생했습니다.
    echo ========================================
    echo.
    pause
)
