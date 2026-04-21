#!/usr/bin/env python3
"""
简单测试目录检测结果
"""
from pdf_router import TocDetector

detector = TocDetector()

test_pdfs = [
    "2025年度手游APP买量数据报告-32页.pdf",
    "2025全球手游市场营销洞察&创意拆解报告-24页.pdf",
    "2025 Q1-Q3 全球手游买量风向与策略洞察-51页.pdf",
    "pdf_20260419_20260420.pdf"
]

for pdf_name in test_pdfs:
    pdf_path = f"/home/wyd/daily/work/PDFROUTER/test_pdfs/{pdf_name}"
    print(f"\n{'='*60}")
    print(f"📄 {pdf_name}")
    print('='*60)
    try:
        results = detector.detect_from_path(pdf_path)
        toc_pages = [r['page_index']+1 for r in results if r['is_toc_page']]
        if toc_pages:
            print(f"✅ 检测到目录页：{sorted(toc_pages)}")
            for page in toc_pages:
                conf = [r['confidence'] for r in results if r['page_index'] == page-1][0]
                print(f"   第 {page} 页，置信度：{conf:.2f}")
        else:
            print("❌ 未检测到目录页")
    except Exception as e:
        print(f"❌ 检测失败：{e}")
