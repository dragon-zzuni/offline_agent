"""
프로젝트 코드 → 풀네임 매핑 유틸리티
"""
import sqlite3
import os
from typing import Dict, Optional

# 프로젝트 코드 → ID 매핑 (VDOS DB 기준)
PROJECT_CODE_TO_ID = {
    "CC": 20,
    "HA": 21,
    "WELL": 22,
    "WI": 23,
    "CI": 24
}

# 캐시
_project_fullname_cache: Optional[Dict[str, str]] = None


def get_project_fullname(project_code: str) -> Optional[str]:
    """프로젝트 코드로 풀네임 가져오기
    
    Args:
        project_code: 프로젝트 코드 (CC, HA, WELL, WI, CI)
        
    Returns:
        프로젝트 풀네임 또는 None
    """
    global _project_fullname_cache
    
    if _project_fullname_cache is None:
        _project_fullname_cache = _load_project_fullnames()
    
    return _project_fullname_cache.get(project_code)


def _load_project_fullnames() -> Dict[str, str]:
    """VDOS DB에서 프로젝트 풀네임 로드"""
    try:
        # VDOS DB 경로 찾기
        vdos_db_path = _find_vdos_db()
        if not vdos_db_path:
            return {}
        
        conn = sqlite3.connect(vdos_db_path)
        cursor = conn.cursor()
        
        # 프로젝트 정보 가져오기
        cursor.execute("SELECT id, project_name FROM project_plans")
        projects = cursor.fetchall()
        
        # 코드 → 풀네임 매핑 생성
        mapping = {}
        for proj_id, name in projects:
            # ID로 코드 찾기
            for code, pid in PROJECT_CODE_TO_ID.items():
                if pid == proj_id:
                    mapping[code] = name
                    break
        
        conn.close()
        return mapping
        
    except Exception as e:
        print(f"[ProjectFullnameMapper] 프로젝트 풀네임 로드 실패: {e}")
        return {}


def _find_vdos_db() -> Optional[str]:
    """VDOS DB 경로 찾기"""
    # 가능한 경로들
    possible_paths = [
        # 상대 경로 (offline_agent 기준)
        os.path.join(os.path.dirname(__file__), "../../../virtualoffice/src/virtualoffice/vdos.db"),
        # 절대 경로
        r"C:\Users\USER\Desktop\virtual-office-orchestration\virtualoffice\src\virtualoffice\vdos.db",
    ]
    
    for path in possible_paths:
        abs_path = os.path.abspath(path)
        if os.path.exists(abs_path):
            return abs_path
    
    return None


# 초기화 시 캐시 로드
_project_fullname_cache = _load_project_fullnames()
