#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
프로젝트 태그 캐시 경로 확인 스크립트
"""
import sys
import os
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from services.project_tag_service import ProjectTagService

def main():
    print("=" * 60)
    print("프로젝트 태그 캐시 경로 확인")
    print("=" * 60)
    
    # ProjectTagService 초기화
    service = ProjectTagService()
    
    print(f"\n✅ VDOS DB 경로: {service.vdos_db_path}")
    
    if service.tag_cache:
        print(f"✅ 캐시 DB 경로: {service.tag_cache.db_path}")
        
        # 경로 검증
        cache_path = Path(service.tag_cache.db_path)
        vdos_path = Path(service.vdos_db_path)
        
        if cache_path.parent == vdos_path.parent:
            print("✅ 캐시와 VDOS DB가 같은 디렉토리에 있습니다!")
            print(f"   디렉토리: {cache_path.parent}")
        else:
            print("❌ 경고: 캐시와 VDOS DB가 다른 디렉토리에 있습니다!")
            print(f"   VDOS 디렉토리: {vdos_path.parent}")
            print(f"   캐시 디렉토리: {cache_path.parent}")
        
        # 파일 존재 확인
        if cache_path.exists():
            size = cache_path.stat().st_size
            print(f"✅ 캐시 파일 존재: {size:,} bytes")
        else:
            print("⚠️ 캐시 파일이 아직 생성되지 않았습니다 (정상)")
    else:
        print("❌ 캐시가 초기화되지 않았습니다!")
    
    # 프로젝트 정보 확인
    print(f"\n📊 로드된 프로젝트: {len(service.project_tags)}개")
    for code, tag in service.project_tags.items():
        print(f"   - {code}: {tag.name}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
