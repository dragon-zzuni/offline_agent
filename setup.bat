@echo off
REM Smart Assistant 설치 스크립트
REM 처음 설치 시 한 번만 실행하세요

cd /d "%~dp0"
title Smart Assistant 설치

chcp 65001 >nul

echo ========================================
echo   Smart Assistant 설치 마법사
echo ========================================
echo.
echo 이 스크립트는 Smart Assistant 실행에
echo 필요한 패키지를 자동으로 설치합니다.
echo.
pause

REM Conda 환경 찾기
set CONDA_FOUND=0

if exist "%USERPROFILE%\miniconda3\Scripts\activate.bat" (
    call "%USERPROFILE%\miniconda3\Scripts\activate.bat" base
    set CONDA_FOUND=1
    goto :install
)

if exist "%USERPROFILE%\anaconda3\Scripts\activate.bat" (
    call "%USERPROFILE%\anaconda3\Scripts\activate.bat" base
    set CONDA_FOUND=1
    goto :install
)

where conda >nul 2>&1
if not errorlevel 1 (
    call conda activate base
    set CONDA_FOUND=1
    goto :install
)

where python >nul 2>&1
if not errorlevel 1 (
    set CONDA_FOUND=1
    goto :install
)

echo.
echo [오류] Python 환경을 찾을 수 없습니다.
echo.
echo Anaconda 또는 Miniconda를 먼저 설치해주세요:
echo https://www.anaconda.com/download
echo.
pause
exit /b 1

:install
echo.
echo ========================================
echo   패키지 설치 중...
echo ========================================
echo.

REM requirements.txt 확인
if not exist requirements.txt (
    echo [오류] requirements.txt 파일을 찾을 수 없습니다.
    pause
    exit /b 1
)

REM 패키지 설치
python -m pip install --upgrade pip
pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo [오류] 패키지 설치 중 오류가 발생했습니다.
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo   설치 완료!
echo ========================================
echo.
echo Smart Assistant가 성공적으로 설치되었습니다.
echo.
echo 실행 방법:
echo 1. Smart_Assistant_Conda.bat 더블클릭
echo 2. 또는 바탕화면 바로가기 만들기
echo.
echo 바탕화면_바로가기_만들기.txt 파일을 참고하세요.
echo.
pause
