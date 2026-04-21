#!/usr/bin/env python3
"""
分析数据报告的目录和误判页特征
"""
import fitz

PDF_PATH = "/home/wyd/daily/work/PDFROUTER/test_pdfs/2025年度手游APP买量数据报告-32页.pdf"
# 要分析的页码：第3页（真正的目录，0-based是2）、误判的15、16、17、24页（0-based 14,15,16,23）
PAGES = [2, 14, 15, 16, 23]

doc = fitz.open(PDF_PATH)

for page_idx in PAGES:
    page = doc.load_page(page_idx)
    print(f"\n{'='*80}")
    print(f"📄 第 {page_idx+1} 页 内容预览:")
    print(f"{'='*80}")

    text = page.get_text()
    print(text[:800])  # 显示前800字符

    # 计算特征
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    line_count = len(lines)
    avg_line_len = sum(len(l) for l in lines)/line_count if line_count else 0
    digit_count = sum(c.isdigit() for c in text)
    digit_ratio = digit_count/len(text) if text else 0
    has_toc_keyword = any(k in text for k in ["目录", "CONTENTS", "Contents", "TOC"])

    print(f"\n📊 特征统计:")
    print(f"总行数: {line_count}")
    print(f"平均行长度: {avg_line_len:.1f}")
    print(f"数字占比: {digit_ratio:.1%}")
    print(f"包含目录关键词: {'是' if has_toc_keyword else '否'}")

    # 统计各行结构
    end_with_digit = sum(1 for l in lines if l and l[-1].isdigit())
    short_lines = sum(1 for l in lines if len(l) < 30)
    print(f"末尾带数字的行: {end_with_digit} ({end_with_digit/line_count*100:.1f}%)")
    print(f"短行(长度<30)占比: {short_lines/line_count*100:.1f}%")

doc.close()
