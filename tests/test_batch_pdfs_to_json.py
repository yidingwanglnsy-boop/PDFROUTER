import os
import json
from datetime import datetime
from pdf_router import PdfRouter

# 配置路径
TEST_PDF_DIR = os.path.join(os.path.dirname(__file__), "test_pdfs")
# 输出文件带时间戳，避免覆盖历史结果
OUTPUT_JSON = os.path.join(
    os.path.dirname(__file__),
    f"pdf_router_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
)

def batch_process_pdfs():
    """批量处理test_pdfs下所有PDF，提取特征并保存到JSON"""
    router = PdfRouter()

    # 初始化结果结构
    results = {
        "generate_time": datetime.now().isoformat(),
        "pdf_router_version": "1.1.0",
        "statistics": {
            "total_count": 0,
            "success_count": 0,
            "failed_count": 0
        },
        "pdf_list": []
    }

    # 检查测试目录
    if not os.path.exists(TEST_PDF_DIR):
        os.makedirs(TEST_PDF_DIR, exist_ok=True)
        print(f"⚠️  测试目录 {TEST_PDF_DIR} 不存在，已自动创建，请放入PDF文件后重新运行")
        return

    # 查找所有PDF文件
    pdf_files = [f for f in os.listdir(TEST_PDF_DIR) if f.lower().endswith(".pdf")]
    results["statistics"]["total_count"] = len(pdf_files)

    if not pdf_files:
        print(f"⚠️  测试目录 {TEST_PDF_DIR} 下没有找到PDF文件，请放入PDF后重新运行")
        return

    print(f"🚀 找到 {len(pdf_files)} 个PDF文件，开始批量处理...\n")

    # 遍历处理每个PDF
    for idx, pdf_file in enumerate(pdf_files, 1):
        pdf_path = os.path.join(TEST_PDF_DIR, pdf_file)
        print(f"[{idx}/{len(pdf_files)}] 处理: {pdf_file}")

        try:
            # 调用路由接口提取特征
            result = router.route(pdf_path)

            # 处理浮点数值，兼容JSON序列化
            if "features" in result:
                for k, v in result["features"].items():
                    if isinstance(v, float):
                        result["features"][k] = round(float(v), 4)

            # 保存成功结果
            results["pdf_list"].append({
                "file_name": pdf_file,
                "file_path": os.path.abspath(pdf_path),
                "status": "success",
                "features": result["features"],
                "marks": result["marks"],
                "process_priority": result["process_priority"],
                "recommended_backend": result["recommended_backend"]
            })
            results["statistics"]["success_count"] += 1
            print(f"✅  处理成功 | 标记: {result['marks']} | 推荐后端: {result['recommended_backend']}\n")

        except Exception as e:
            # 保存失败结果，不中断整个批量处理
            results["pdf_list"].append({
                "file_name": pdf_file,
                "file_path": os.path.abspath(pdf_path),
                "status": "failed",
                "error_msg": str(e)
            })
            results["statistics"]["failed_count"] += 1
            print(f"❌  处理失败 | 错误: {str(e)}\n")

    # 保存结果到JSON
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # 打印最终统计
    print("=" * 80)
    print(f"📊 批量处理完成！")
    print(f"总文件数: {results['statistics']['total_count']} | 成功: {results['statistics']['success_count']} | 失败: {results['statistics']['failed_count']}")
    print(f"📝 详细结果已保存到: {os.path.abspath(OUTPUT_JSON)}")
    print("=" * 80)

if __name__ == "__main__":
    batch_process_pdfs()
