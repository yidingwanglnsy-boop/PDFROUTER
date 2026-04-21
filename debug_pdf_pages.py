#!/usr/bin/env python3
"""
提取指定PDF页面的文本和结构特征
"""
import fitz
import os

PDF_PATH = "/home/wyd/daily/work/PDFROUTER/test_pdfs/2025 Q1-Q3 全球手游买量风向与策略洞察-51页.pdf"
PAGES_TO_CHECK = [0, 3, 4]  # 0-based，对应第1、4、5页

doc = fitz.open(PDF_PATH)

for page_idx in PAGES_TO_CHECK:
    page = doc.load_page(page_idx)
    print(f"\n{'='*80}")
    print(f"📄 第 {page_idx+1} 页 内容:")
    print(f"{'='*80}")

    # 提取文本
    text = page.get_text()
    print(text[:1000])  # 显示前1000字符

    # 提取文本块和位置
    print(f"\n🔍 页内结构特征:")
    blocks = page.get_text("dict")["blocks"]
    text_blocks = [b for b in blocks if b["type"] == 0]

    # 统计特征
    line_end_numbers = 0
    has_dots = 0
    line_count = 0

    for block in text_blocks:
        for line in block["lines"]:
            line_text = "".join([span["text"] for span in line["spans"]]).strip()
            if not line_text:
                continue
            line_count += 1
            # 检查是否以数字结尾
            if line_text and line_text[-1].isdigit():
                # 检查末尾是否是连续数字
                for i in range(len(line_text)-1, -1, -1):
                    if not line_text[i].isdigit() and line_text[i] not in [".", ",", "、", " "]:
                        break
                if len(line_text) - i > 1:  # 至少两位数字
                    line_end_numbers += 1
            # 检查是否有多个连续点
            if "..." in line_text or "。。。" in line_text:
                has_dots += 1

    print(f"总文本行: {line_count}")
    print(f"末尾带数字的行: {line_end_numbers} ({line_end_numbers/line_count*100:.1f}%)")
    print(f"带引导点(...)的行: {has_dots}")
    print(f"是否包含目录关键词: {'是' if any(k in text for k in ['目录', 'CONTENTS', 'Contents', 'TOC']) else '否'}")

doc.close()
