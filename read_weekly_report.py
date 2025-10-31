#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
주간업무보고 엑셀 파일 읽기
"""
import openpyxl
from pathlib import Path

# 엑셀 파일 경로
excel_path = Path("../4주차 주간업무보고 (인턴 김용준).xlsx")

# 엑셀 파일 열기
wb = openpyxl.load_workbook(excel_path)
ws = wb.active

print("=" * 80)
print("4주차 주간업무보고 (인턴 김용준)")
print("=" * 80)
print()

# 모든 셀 내용 출력
for row in ws.iter_rows(values_only=True):
    # 빈 행 건너뛰기
    if all(cell is None for cell in row):
        continue
    
    # 행 출력
    row_text = []
    for cell in row:
        if cell is not None:
            row_text.append(str(cell))
    
    if row_text:
        print(" | ".join(row_text))

print()
print("=" * 80)
