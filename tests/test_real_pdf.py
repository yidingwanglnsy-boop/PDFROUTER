import sys
import os

# 把MinerU根目录加到Python路径，无需安装即可导入
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pdf_router import PdfRouter

def test_real_pdfs():
    router = PdfRouter()

    test_pdf_dir = os.path.join(os.path.dirname(__file__), "test_pdfs")

    # # 测试纯文本PDF
    # text_pdf_path = os.path.join(test_pdf_dir, "text_pdf.pdf")
    # print(f"\n===== 测试纯文本PDF: {text_pdf_path} =====")
    # result = router.route(text_pdf_path)
    # print(f"PDF特征：\n  页数: {result['features']['page_count']}\n  平均每页字符数: {result['features']['avg_chars_per_page']}\n  图片占比: {result['features']['image_coverage_ratio']:.2f}\n  是否是PPT转换: {result['features']['is_ppt_converted']}")
    # print(f"标记位：{result['marks']}")
    # print(f"处理优先级：{result['process_priority']}")
    # print(f"推荐后端：{result['recommended_backend']}")

    # 测试PPT转换的PDF
    ppt_pdf_path = os.path.join(test_pdf_dir, "ppt_pdf_real.pdf")
    print(f"\n===== 测试PPT转换PDF: {ppt_pdf_path} =====")
    result = router.route(ppt_pdf_path)
    print(f"PDF特征：\n  页数: {result['features']['page_count']}\n  平均每页字符数: {result['features']['avg_chars_per_page']}\n  图片占比: {result['features']['image_coverage_ratio']:.2f}\n  是否是PPT转换: {result['features']['is_ppt_converted']}\n  PPT分数: {result['features']['ppt_score']:.2f}")
    print(f"标记位：{result['marks']}")
    print(f"处理优先级：{result['process_priority']}")
    print(f"推荐后端：{result['recommended_backend']}")

    print("\n✅ 所有真实PDF测试完成！")

if __name__ == "__main__":
    test_real_pdfs()
