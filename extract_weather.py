#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""날씨 관련 메서드 추출 스크립트"""
import re

with open('src/ui/main_window.py', 'r', encoding='utf-8') as f:
    content = f.read()
    lines = content.split('\n')

# 날씨 관련 메서드 찾기
weather_methods = [
    '_fetch_weather_from_kma',
    'fetch_weather',
    '_describe_kma_weather',
    '_weather_tip',
    '_weather_description',
    '_extract_tomorrow_morning'
]

extracted_methods = []

for method_name in weather_methods:
    # 메서드 시작 찾기
    pattern = rf'    def {method_name}\(self.*?\):'
    match = re.search(pattern, content)
    if match:
        start_pos = match.start()
        
        # 메서드 끝 찾기 (다음 메서드 또는 클래스까지)
        next_method_pattern = r'\n    def [a-zA-Z_]'
        next_match = re.search(next_method_pattern, content[start_pos + 10:])
        
        if next_match:
            end_pos = start_pos + 10 + next_match.start()
        else:
            end_pos = len(content)
        
        method_content = content[start_pos:end_pos]
        extracted_methods.append((method_name, method_content))
        print(f'Found {method_name}: {len(method_content)} chars')

print(f'\nTotal methods extracted: {len(extracted_methods)}')
