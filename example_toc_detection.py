#!/usr/bin/env python3
"""
目录检测API使用示例
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from pdf_router import TocDetector


def main():
    # 初始化目录检测器
    detector = TocDetector()

    if len(sys.argv) != 2:
        print("使用方法: python example_toc_detection.py <pdf文件路径>")
        print("功能说明: 检测PDF中的目录页，输出每页的检测结果")
        return

    pdf_path = sys.argv[1]

    print(f"正在检测PDF文件: {pdf_path}")
    print("=" * 80)

    # 检测目录页
    results = detector.detect_from_path(pdf_path)

    if not results:
        print("PDF文件读取失败或为空")
        return

    # 输出结果
    toc_pages = []
    for result in results:
        page_num = result["page_index"] + 1  # 转换为用户熟悉的1-based页码
        is_toc = result["is_toc_page"]
        confidence = result["confidence"]
        toc_type = result["toc_type"]

        status = "✓ 目录页" if is_toc else "✗ 正文页"
        type_info = f"({toc_type}类型)" if toc_type else ""

        print(f"页码 {page_num:3d}: {status} {type_info} 置信度: {confidence:.2f}")

        if is_toc:
            toc_pages.append(page_num)

    print("=" * 80)
    if toc_pages:
        print(f"检测到目录页: {', '.join(map(str, sorted(toc_pages)))}")
    else:
        print("未检测到目录页")


if __name__ == "__main__":
    main()
