#!/usr/bin/env python3
"""
目录检测API单元测试
"""
import os
import unittest
import sys
import tempfile
import fitz
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pdf_router import TocDetector


class TestTocApi(unittest.TestCase):
    """目录检测API测试类"""

    def setUp(self):
        """初始化测试环境"""
        self.toc_detector = TocDetector()

    def create_test_pdf_with_toc(self, is_ppt: bool = False, is_chinese: bool = True) -> bytes:
        """创建测试用PDF，包含目录页"""
        doc = fitz.open()

        # 添加PPT元数据
        if is_ppt:
            doc.set_metadata({
                "producer": "Microsoft PowerPoint",
                "creator": "Microsoft Office PowerPoint",
                "title": "Test PPT Document"
            })

        # 创建目录页
        toc_page = doc.new_page()

        # 添加标题
        title = "目录" if is_chinese else "Contents"
        toc_page.insert_text((50, 70), title, fontsize=20)

        # 添加目录项
        y_position = 120
        for i in range(1, 11):
            chapter = f"第{i}章 测试章节{i}" if is_chinese else f"Chapter {i} Test Chapter {i}"
            page_num = f"{i+1}"
            # 添加引导线
            leader = "." * 50
            line = f"{chapter} {leader} {page_num}"
            toc_page.insert_text((50, y_position), line, fontsize=12)
            y_position += 30

        # 添加正文页
        for i in range(10):
            page = doc.new_page()
            page.insert_text((50, 70), f"正文页 {i+1}" if is_chinese else f"Content Page {i+1}", fontsize=12)
            page.insert_text((50, 100), "这是测试正文内容。" * 20 if is_chinese else "This is test content. " * 20, fontsize=12)

        # 如果是PPT格式，设置宽高比为16:9
        if is_ppt:
            for page in doc:
                page.set_mediabox(fitz.Rect(0, 0, 1920, 1080))

        pdf_bytes = doc.write()
        doc.close()
        return pdf_bytes

    def test_detect_from_bytes_chinese_document(self):
        """测试从字节流检测中文文档目录"""
        pdf_bytes = self.create_test_pdf_with_toc(is_ppt=False, is_chinese=True)
        results = self.toc_detector.detect_from_bytes(pdf_bytes)

        self.assertGreaterEqual(len(results), 11)  # 1目录页 + 10正文页
        # 第一页应该是目录页
        self.assertTrue(results[0]["is_toc_page"])
        self.assertEqual(results[0]["toc_type"], "document")
        self.assertGreater(results[0]["confidence"], 0.6)

        # 正文页不应该是目录页
        for result in results[1:]:
            self.assertFalse(result["is_toc_page"])
            self.assertIsNone(result["toc_type"])

    def test_detect_from_bytes_english_document(self):
        """测试从字节流检测英文文档目录"""
        pdf_bytes = self.create_test_pdf_with_toc(is_ppt=False, is_chinese=False)
        results = self.toc_detector.detect_from_bytes(pdf_bytes)

        self.assertGreaterEqual(len(results), 11)
        self.assertTrue(results[0]["is_toc_page"])
        self.assertEqual(results[0]["toc_type"], "document")
        self.assertGreater(results[0]["confidence"], 0.6)

    def test_detect_from_bytes_ppt_format(self):
        """测试从字节流检测PPT格式目录"""
        pdf_bytes = self.create_test_pdf_with_toc(is_ppt=True, is_chinese=True)
        results = self.toc_detector.detect_from_bytes(pdf_bytes)

        self.assertGreaterEqual(len(results), 11)
        self.assertTrue(results[0]["is_toc_page"])
        self.assertEqual(results[0]["toc_type"], "ppt")
        self.assertGreater(results[0]["confidence"], 0.5)

    def test_detect_from_path(self):
        """测试从文件路径检测目录"""
        pdf_bytes = self.create_test_pdf_with_toc()

        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(pdf_bytes)
            temp_path = f.name

        try:
            results = self.toc_detector.detect_from_path(temp_path)
            self.assertGreaterEqual(len(results), 11)
            self.assertTrue(results[0]["is_toc_page"])
        finally:
            # 删除临时文件
            os.unlink(temp_path)

    def test_invalid_pdf_input(self):
        """测试无效PDF输入处理"""
        # 空字节
        results = self.toc_detector.detect_from_bytes(b"")
        self.assertEqual(len(results), 0)

        # 无效文件路径
        results = self.toc_detector.detect_from_path("/nonexistent/path/test.pdf")
        self.assertEqual(len(results), 0)

        # 损坏的PDF内容
        results = self.toc_detector.detect_from_bytes(b"%PDF-1.4 corrupted content")
        self.assertEqual(len(results), 0)


if __name__ == "__main__":
    unittest.main()
