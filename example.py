#!/usr/bin/env python3
"""
PDF Router 使用示例
"""
import tempfile
import os
from pdf_router import PdfRouter, SinglePagePdfRouter


def example_whole_document():
    """整文档PDF路由示例"""
    print("=== 整文档PDF路由示例 ===")

    # 初始化路由器
    router = PdfRouter()

    # 创建临时PDF文件（实际使用时替换为你的PDF路径）
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        # 这里写入模拟PDF内容，实际使用时直接传入真实路径
        pdf_path = f.name

    try:
        # 路由处理
        result = router.route(pdf_path)

        # 输出结果
        print(f"PDF路径: {result['pdf_path']}")
        print(f"特征: {result['features']}")
        print(f"标记: {result['marks']}")
        print(f"处理优先级: {result['process_priority']}")
        print(f"推荐后端: {result['recommended_backend']}")
        print(f"路由器版本: {result['router_version']}")
    finally:
        os.unlink(pdf_path)
    print()


def example_single_page():
    """单页PDF评估示例"""
    print("=== 单页PDF评估示例 ===")

    # 初始化单页路由器
    router = SinglePagePdfRouter()

    # 创建临时PDF文件
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        pdf_path = f.name

    try:
        # 评估第0页（第一页）
        result = router.evaluate_page(pdf_path, page_index=0)

        # 输出结果
        print(f"页面索引: {result['page_index']}")
        print(f"输入类型: {result['source_type']}")
        print(f"页面特征: {result['features']}")
        print(f"标记: {result['marks']}")
        print(f"处理优先级: {result['process_priority']}")
        print(f"推荐后端: {result['recommended_backend']}")
        print(f"处理建议: {result['processing_suggestions']}")
    finally:
        os.unlink(pdf_path)
    print()


def example_custom_config():
    """自定义配置示例"""
    print("=== 自定义配置示例 ===")

    # 自定义配置
    custom_config = {
        "scan_pdf_threshold": 0.6,  # 调整扫描PDF判定阈值
        "ppt_marker_score_threshold": 0.75,  # 调整PPT识别阈值
        "backend_preference": {
            "ppt_converted": "my_ppt_processor",  # 自定义PPT类型推荐后端
            "low_quality_scan": "my_ocr_engine"   # 自定义低质量扫描推荐后端
        }
    }

    # 使用自定义配置初始化路由器
    router = PdfRouter(custom_config)

    print("自定义配置已加载完成")
    print(f"扫描PDF阈值: {router.config_manager.get('scan_pdf_threshold')}")
    print(f"PPT识别阈值: {router.config_manager.get('ppt_marker_score_threshold')}")
    print(f"PPT类型推荐后端: {router.config_manager.get('backend_preference.ppt_converted')}")
    print()


if __name__ == "__main__":
    example_whole_document()
    example_single_page()
    example_custom_config()
    print("所有示例运行完成！")
