@echo off
REM Smart Assistant 실행 스크립트
REM 이 파일을 더블클릭하면 Smart Assistant가 실행됩니다

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

REM Conda 환경 찾기 및 활성화
set CONDA_FOUND=0

REM Miniconda 경로 확인
if exist "%USERPROFILE%\miniconda3\Scripts\activate.bat" (
    echo Miniconda 환경 발견...
    call "%USERPROFILE%\miniconda3\Scripts\activate.bat" base
    set CONDA_FOUND=1
    goto :run_app
)

REM Anaconda 경로 확인
if exist "%USERPROFILE%\anaconda3\Scripts\activate.bat" (
    echo Anaconda 환경 발견...
    call "%USERPROFILE%\anaconda3\Scripts\activate.bat" base
    set CONDA_FOUND=1
    goto :run_app
)

REM Conda가 PATH에 있는지 확인
where conda >nul 2>&1
if not errorlevel 1 (
    echo Conda 환경 활성화 중...
    call conda activate base
    set CONDA_FOUND=1
    goto :run_app
)

REM Python이 PATH에 있는지 확인
where python >nul 2>&1
if not errorlevel 1 (
    echo Python 발견...
    set CONDA_FOUND=1
    goto :run_app
)

REM 모든 방법 실패
echo.
echo [오류] Python 환경을 찾을 수 없습니다.
echo.
echo 다음 중 하나를 수행해주세요:
echo 1. Anaconda/Miniconda를 설치
echo 2. Python을 PATH에 등록
echo 3. Anaconda Prompt에서 직접 실행: python run_gui.py
echo.
pause
exit /b 1

:run_app
REM Smart Assistant 실행
echo.
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
