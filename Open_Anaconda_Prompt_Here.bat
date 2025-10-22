@echo off
REM 현재 폴더에서 Anaconda Prompt 열기

REM 현재 디렉토리 저장
set CURRENT_DIR=%cd%

REM Anaconda Prompt 실행 (자동으로 base 환경 활성화됨)
if exist "%USERPROFILE%\miniconda3\Scripts\activate.bat" (
    start "Anaconda Prompt" cmd /k ""%USERPROFILE%\miniconda3\Scripts\activate.bat" base && cd /d "%CURRENT_DIR%" && echo Smart Assistant 폴더로 이동했습니다. && echo python run_gui.py 명령어로 실행하세요."
    exit
)

if exist "%USERPROFILE%\anaconda3\Scripts\activate.bat" (
    start "Anaconda Prompt" cmd /k ""%USERPROFILE%\anaconda3\Scripts\activate.bat" base && cd /d "%CURRENT_DIR%" && echo Smart Assistant 폴더로 이동했습니다. && echo python run_gui.py 명령어로 실행하세요."
    exit
)

if exist "C:\ProgramData\miniconda3\Scripts\activate.bat" (
    start "Anaconda Prompt" cmd /k ""C:\ProgramData\miniconda3\Scripts\activate.bat" base && cd /d "%CURRENT_DIR%" && echo Smart Assistant 폴더로 이동했습니다. && echo python run_gui.py 명령어로 실행하세요."
    exit
)

if exist "C:\ProgramData\anaconda3\Scripts\activate.bat" (
    start "Anaconda Prompt" cmd /k ""C:\ProgramData\anaconda3\Scripts\activate.bat" base && cd /d "%CURRENT_DIR%" && echo Smart Assistant 폴더로 이동했습니다. && echo python run_gui.py 명령어로 실행하세요."
    exit
)

echo Anaconda/Miniconda를 찾을 수 없습니다.
echo 시작 메뉴에서 "Anaconda Prompt"를 직접 실행하세요.
pause
