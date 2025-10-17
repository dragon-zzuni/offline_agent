@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

echo ========================================
echo    Smart Assistant GUI 실행
echo ========================================
echo.
echo AI 기반 스마트 어시스턴트 GUI를 실행합니다.
echo.

py run_gui.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo 오류가 발생했습니다. Python과 PyQt6가 설치되어 있는지 확인해주세요.
    pause
)
