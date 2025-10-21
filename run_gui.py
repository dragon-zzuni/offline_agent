# -*- coding: utf-8 -*-
"""
Smart Assistant GUI 실행 스크립트
"""
import sys
import os
from pathlib import Path

# Windows 한글 출력 설정
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['PYTHONUTF8'] = '1'

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# GUI 실행 (src wrapper)
from src.ui.main_window import main

if __name__ == "__main__":
    main()
