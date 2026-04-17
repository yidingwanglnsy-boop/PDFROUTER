#!/usr/bin/env python3
"""
PDF Router 实际批量处理示例
适用于真实业务场景下的大规模PDF文档预处理
"""
import os
import json
import time
from pathlib import Path
from tqdm import tqdm
from pdf_router import PdfRouter, SinglePagePdfRouter
from pdf_router.constants import PdfTypeMark, ProcessPriorityMark


def batch_process_whole_documents(pdf_dir: str, output_dir: str, custom_config: dict = None):
    """
    批量处理目录下所有PDF文件（整文档粒度）
    :param pdf_dir: 存放PDF文件的目录路径
    :param output_dir: 结果输出目录
    :param custom_config: 自定义路由器配置
    """
    # 创建输出目录
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    results_path = os.path.join(output_dir, f"pdf_router_results_{int(time.time())}.json")

    # 初始化路由器
    router = PdfRouter(custom_config)

    # 获取所有PDF文件
    pdf_files = list(Path(pdf_dir).rglob("*.pdf"))
    print(f"找到 {len(pdf_files)} 个PDF文件待处理")

    # 获取所有枚举值
    pdf_type_marks = [getattr(PdfTypeMark, attr) for attr in dir(PdfTypeMark) if not attr.startswith('_')]
    priority_marks = [getattr(ProcessPriorityMark, attr) for attr in dir(ProcessPriorityMark) if not attr.startswith('_')]

    # 处理结果
    results = []
    stats = {
        "total": len(pdf_files),
        "success": 0,
        "failed": 0,
        "type_distribution": {mark: 0 for mark in pdf_type_marks},
        "priority_distribution": {priority: 0 for priority in priority_marks}
    }

    # 批量处理
    for pdf_path in tqdm(pdf_files, desc="处理PDF文档"):
        try:
            # 路由处理
            result = router.route(str(pdf_path))
            results.append(result)

            # 更新统计信息
            stats["success"] += 1
            for mark in result["marks"]:
                if mark in stats["type_distribution"]:
                    stats["type_distribution"][mark] += 1
            if result["process_priority"] in stats["priority_distribution"]:
                stats["priority_distribution"][result["process_priority"]] += 1

            # 业务分流处理示例（根据实际需求修改）
            process_document_by_type(result)

        except Exception as e:
            stats["failed"] += 1
            results.append({
                "pdf_path": str(pdf_path),
                "status": "failed",
                "error": str(e)
            })
            print(f"处理 {pdf_path} 失败: {str(e)}")

    # 保存结果
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump({
            "stats": stats,
            "results": results
        }, f, ensure_ascii=False, indent=2)

    # 输出统计报告
    print(f"\n=== 批量处理完成 ===")
    print(f"总文件数: {stats['total']}")
    print(f"成功: {stats['success']}")
    print(f"失败: {stats['failed']}")
    print(f"\nPDF类型分布:")
    for mark, count in stats["type_distribution"].items():
        if count > 0:
            print(f"  {mark}: {count} 个")
    print(f"\n处理优先级分布:")
    for priority, count in stats["priority_distribution"].items():
        if count > 0:
            print(f"  {priority}: {count} 个")
    print(f"\n结果已保存到: {results_path}")

    return stats, results


def process_document_by_type(router_result: dict):
    """
    根据路由结果分流处理PDF文档的业务逻辑示例
    实际使用时可以根据自己的需求修改此函数
    """
    pdf_path = router_result["pdf_path"]
    marks = router_result["marks"]
    recommended_backend = router_result["recommended_backend"]

    # 示例业务逻辑：根据不同类型调用不同处理后端
    if PdfTypeMark.TEXT_PDF in marks:
        # 纯文本PDF：调用快速文本提取流程
        process_text_pdf(pdf_path)
    elif PdfTypeMark.SCAN_PDF in marks or PdfTypeMark.LOW_QUALITY_SCAN in marks:
        # 扫描件/低质量扫描：调用OCR识别流程
        process_scan_pdf(pdf_path, recommended_backend)
    elif PdfTypeMark.PPT_CONVERTED in marks:
        # PPT转换的PDF：调用PPT专用解析流程
        process_ppt_pdf(pdf_path)
    elif PdfTypeMark.CID_FONT_PDF in marks:
        # CID字体PDF：调用特殊编码识别流程
        process_cid_pdf(pdf_path)
    elif PdfTypeMark.COMPLEX_LAYOUT in marks:
        # 复杂布局PDF：调用图文混排解析流程
        process_complex_pdf(pdf_path)
    else:
        # 混合类型/其他：调用通用处理流程
        process_generic_pdf(pdf_path, recommended_backend)


def process_text_pdf(pdf_path: str):
    """纯文本PDF处理示例"""
    # 实际业务逻辑：比如调用pymupdf提取文本，保存到数据库等
    # print(f"处理纯文本PDF: {pdf_path}")
    pass


def process_scan_pdf(pdf_path: str, backend: str):
    """扫描件PDF处理示例"""
    # 实际业务逻辑：调用对应的OCR引擎处理
    # print(f"处理扫描件PDF: {pdf_path}, 使用后端: {backend}")
    pass


def process_ppt_pdf(pdf_path: str):
    """PPT类型PDF处理示例"""
    # 实际业务逻辑：提取PPT结构，保留版式信息等
    # print(f"处理PPT转换PDF: {pdf_path}")
    pass


def process_cid_pdf(pdf_path: str):
    """CID字体PDF处理示例"""
    # 实际业务逻辑：转换编码，调用支持CID字体的解析器
    # print(f"处理CID字体PDF: {pdf_path}")
    pass


def process_complex_pdf(pdf_path: str):
    """复杂布局PDF处理示例"""
    # 实际业务逻辑：调用版面分析模型，区分文本、表格、图片等
    # print(f"处理复杂布局PDF: {pdf_path}")
    pass


def process_generic_pdf(pdf_path: str, backend: str):
    """通用PDF处理示例"""
    # 实际业务逻辑：根据推荐后端调用对应处理流程
    # print(f"通用处理PDF: {pdf_path}, 使用后端: {backend}")
    pass


def batch_process_single_pages(pdf_dir: str, output_dir: str):
    """
    批量处理PDF文件的所有页面（单页粒度）
    适用于需要按页处理的场景，比如文档拆分、单页OCR优化等
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    router = SinglePagePdfRouter()
    pdf_files = list(Path(pdf_dir).rglob("*.pdf"))

    print(f"批量单页处理，共 {len(pdf_files)} 个PDF文件")

    all_page_results = []
    for pdf_path in tqdm(pdf_files, desc="处理PDF页面"):
        try:
            # 获取PDF总页数（实际使用时可以用pymupdf获取）
            import fitz
            doc = fitz.open(str(pdf_path))
            total_pages = len(doc)
            doc.close()

            # 逐页处理
            doc_results = []
            for page_idx in range(total_pages):
                page_result = router.evaluate_page(str(pdf_path), page_index=page_idx)
                doc_results.append(page_result)

                # 单页业务处理示例
                # if PdfTypeMark.SCAN_PDF in page_result["marks"]:
                #     process_single_scan_page(pdf_path, page_idx, page_result)

            all_page_results.append({
                "pdf_path": str(pdf_path),
                "total_pages": total_pages,
                "page_results": doc_results
            })

        except Exception as e:
            print(f"处理 {pdf_path} 页面失败: {str(e)}")
            all_page_results.append({
                "pdf_path": str(pdf_path),
                "status": "failed",
                "error": str(e)
            })

    # 保存结果
    output_path = os.path.join(output_dir, f"single_page_results_{int(time.time())}.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_page_results, f, ensure_ascii=False, indent=2)

    print(f"单页处理完成，结果已保存到: {output_path}")
    return all_page_results


if __name__ == "__main__":
    # 配置参数（根据实际情况修改）
    PDF_DIRECTORY = "./test_pdfs"  # 替换为你的PDF目录路径
    OUTPUT_DIRECTORY = "./output"  # 结果输出目录

    # 自定义配置示例
    custom_config = {
        "scan_pdf_threshold": 0.5,
        "ppt_marker_score_threshold": 0.7,
        "backend_preference": {
            "low_quality_scan": "my_custom_ocr_engine",
            "ppt_converted": "my_ppt_parser"
        }
    }

    # 示例1: 整文档批量处理
    print("=== 启动整文档批量处理 ===")
    if os.path.exists(PDF_DIRECTORY):
        stats, results = batch_process_whole_documents(
            pdf_dir=PDF_DIRECTORY,
            output_dir=OUTPUT_DIRECTORY,
            custom_config=custom_config
        )
    else:
        print(f"PDF目录 {PDF_DIRECTORY} 不存在，请先创建并放入PDF文件")

    # 示例2: 单页粒度批量处理（需要时取消注释）
    # print("\n=== 启动单页粒度批量处理 ===")
    # if os.path.exists(PDF_DIRECTORY):
    #     page_results = batch_process_single_pages(
    #         pdf_dir=PDF_DIRECTORY,
    #         output_dir=OUTPUT_DIRECTORY
    #     )
    # else:
    #     print(f"PDF目录 {PDF_DIRECTORY} 不存在")

    print("\n所有处理任务完成！")
