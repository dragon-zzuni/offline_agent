"""
프로젝트 코드 → 풀네임 매핑 유틸리티
"""
import sqlite3
import os
import re
from typing import Dict, Optional

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
        
        # 프로젝트 정보 가져오기 (동적으로 코드 생성)
        cursor.execute("SELECT project_name FROM project_plans")
        projects = cursor.fetchall()
        
        mapping: Dict[str, str] = {}
        for (project_name,) in projects:
            if not project_name:
                continue
            code = generate_project_code(project_name)
            # 동일 코드가 여러 번 등장할 수 있으므로 가장 긴 이름을 유지
            existing = mapping.get(code)
            if not existing or len(project_name) > len(existing):
                mapping[code] = project_name

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


def generate_project_code(project_name: str) -> str:
    """프로젝트 이름에서 약어 생성 (ProjectTagService와 동일 로직)"""
    if not project_name:
        return "UNK"
    
    english_words = re.findall(r'[A-Za-z]+', project_name)
    
    if len(english_words) >= 2:
        return ''.join(word[0].upper() for word in english_words[:2])
    elif len(english_words) == 1:
        return english_words[0][:4].upper()
    
    korean_words = re.findall(r'[가-힣]+', project_name)
    if korean_words:
        return korean_words[0][:2].upper()
    
    numbers = re.findall(r'\d+', project_name)
    if numbers:
        return f"P{numbers[0][:3]}"
    
    return f"P{abs(hash(project_name)) % 1000:03d}"


# 초기화 시 캐시 로드
_project_fullname_cache = _load_project_fullnames()
