#!/usr/bin/env python3
"""
批量检测test_pdfs目录下所有PDF的目录页
"""
import os
import sys
from pdf_router import TocDetector

def main():
    # 配置项
    TEST_PDFS_DIR = "/home/wyd/daily/work/PDFROUTER/test_pdfs"
    # 可自定义检测配置，调整严格程度
    CUSTOM_CONFIG = {
        "toc_score_threshold": 0.52,  # 适配复杂目录的默认阈值
        "toc_keyword_weight": 0.25,   # 提高关键词权重，有关键词优先考虑
        "toc_page_number_weight": 0.30,  # 页码特征权重，支持跨行检测
        "toc_leader_line_weight": 0.05,  # 降低引导线权重，适配无引导点的中文目录
        "toc_context_weight": 0.05,  # 降低页面位置权重
        "max_toc_page_position": 0.99  # 允许目录出现在文档任意位置
    }

    # 初始化检测器
    detector = TocDetector(CUSTOM_CONFIG)

    # 获取所有PDF文件
    pdf_files = sorted([f for f in os.listdir(TEST_PDFS_DIR) if f.lower().endswith(".pdf")])

    if not pdf_files:
        print("❌ 没有找到PDF文件")
        return

    print(f"🔍 开始批量检测目录页，共 {len(pdf_files)} 个PDF文件")
    print("=" * 100)

    # 统计信息
    total_pdfs = len(pdf_files)
    pdfs_with_toc = 0
    total_toc_pages = 0
    failed_pdfs = []

    # 逐个处理PDF
    for idx, pdf_file in enumerate(pdf_files, 1):
        pdf_path = os.path.join(TEST_PDFS_DIR, pdf_file)
        print(f"[{idx}/{total_pdfs}] 处理: {pdf_file}")

        try:
            results = detector.detect_from_path(pdf_path)

            if not results:
                print(f"   ❌ 无法读取PDF或文件损坏")
                failed_pdfs.append(pdf_file)
                continue

            # 统计目录页
            toc_pages = []
            for result in results:
                if result["is_toc_page"]:
                    page_num = result["page_index"] + 1  # 转换为1-based页码
                    toc_pages.append(page_num)

            # 输出结果
            toc_count = len(toc_pages)
            total_toc_pages += toc_count
            if toc_count > 0:
                pdfs_with_toc += 1
                toc_pages_str = ", ".join(map(str, sorted(toc_pages)))
                print(f"   ✅ 检测到 {toc_count} 个目录页: 页码 {toc_pages_str}")
            else:
                print(f"   ℹ️  未检测到目录页")

        except Exception as e:
            print(f"   ❌ 处理失败: {str(e)}")
            failed_pdfs.append(pdf_file)

        print("-" * 80)

    # 输出汇总统计
    print("\n" + "=" * 100)
    print("📊 批量检测结果汇总")
    print("=" * 100)
    print(f"总PDF文件数: {total_pdfs}")
    print(f"成功处理: {total_pdfs - len(failed_pdfs)} 个")
    print(f"处理失败: {len(failed_pdfs)} 个")
    if failed_pdfs:
        print(f"失败文件列表: {', '.join(failed_pdfs)}")
    print(f"包含目录页的PDF: {pdfs_with_toc} 个 ({(pdfs_with_toc/total_pdfs)*100:.1f}%)")
    print(f"总共检测到目录页: {total_toc_pages} 页")
    print(f"平均每个PDF包含目录页: {total_toc_pages/total_pdfs:.1f} 页")

    print("\n💡 提示: 如果需要更高的召回率，可以在CUSTOM_CONFIG中降低toc_score_threshold的值")
    print("   阈值越低，检测出的目录页越多，但可能会增加误判率")

if __name__ == "__main__":
    main()
