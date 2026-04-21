# Copyright (c) Opendatalab. All rights reserved.
"""
测试脚本：使用 get_continuous_toc_pages 检测 test_pdfs 目录下的所有 PDF 文件
"""
import os
import time
from pdf_router.api.toc_api import TocDetector


def test_all_pdfs():
    """检测 test_pdfs 目录下所有 PDF 文件的连续目录页"""
    pdf_dir = "test_pdfs"

    if not os.path.exists(pdf_dir):
        print(f"错误：目录 {pdf_dir} 不存在")
        return

    # 获取所有 PDF 文件
    pdf_files = sorted([f for f in os.listdir(pdf_dir) if f.endswith('.pdf')])

    if not pdf_files:
        print(f"目录 {pdf_dir} 中没有 PDF 文件")
        return

    print(f"共检测 {len(pdf_files)} 个 PDF 文件\n")
    print("=" * 100)

    # 初始化检测器
    detector = TocDetector()

    # 统计信息
    stats = {
        "total": len(pdf_files),
        "with_toc": 0,
        "without_toc": 0,
        "total_pages": 0,
        "total_toc_pages": 0,
        "processing_time": 0
    }

    # 逐个检测
    for i, filename in enumerate(pdf_files, 1):
        filepath = os.path.join(pdf_dir, filename)

        try:
            start_time = time.time()
            result = detector.get_continuous_toc_pages_from_path(filepath)
            elapsed = time.time() - start_time

            # 统计
            stats["total_pages"] += len(result)
            stats["processing_time"] += elapsed

            # 获取目录页码
            toc_pages = [j + 1 for j, is_toc in enumerate(result) if is_toc]

            if toc_pages:
                stats["with_toc"] += 1
                stats["total_toc_pages"] += len(toc_pages)
            else:
                stats["without_toc"] += 1

            # 输出结果
            print(f"{i:2d}. {filename[:55]:55s}")
            print(f"    总页数: {len(result):3d} | 目录页: {str(toc_pages) if toc_pages else '无':30s} | 耗时: {elapsed*1000:6.1f}ms")

        except Exception as e:
            print(f"{i:2d}. {filename[:55]:55s}")
            print(f"    错误: {str(e)[:50]}")

    print("=" * 100)
    print("\n统计结果:")
    print(f"  总文件数: {stats['total']}")
    print(f"  检测到目录的文件数: {stats['with_toc']} ({stats['with_toc']/stats['total']*100:.1f}%)")
    print(f"  未检测到目录的文件数: {stats['without_toc']} ({stats['without_toc']/stats['total']*100:.1f}%)")
    print(f"  总页数: {stats['total_pages']}")
    print(f"  检测到的目录页总数: {stats['total_toc_pages']}")
    print(f"  平均每个文件耗时: {stats['processing_time']/stats['total']*1000:.1f}ms")
    print(f"  总耗时: {stats['processing_time']:.2f}s")


if __name__ == "__main__":
    test_all_pdfs()
