#!/usr/bin/env python3
"""
单页PDF评估功能测试用例
"""
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
# 导入新版本API
from pdf_router import SinglePagePdfRouter, PdfTypeMark, ProcessPriorityMark, RecommendedBackendMark

class TestSinglePagePdfRouter(unittest.TestCase):
    """单页路由器测试类"""
    def setUp(self):
        """初始化测试环境"""
        self.router = SinglePagePdfRouter()
        # 创建临时空PDF文件，仅用于路径校验测试
        self.temp_pdf = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        self.temp_pdf.close()
        # 模拟的有效PDF bytes（用于mock测试）
        self.mock_pdf_bytes = b"%PDF-1.4 mock valid pdf content"

    def tearDown(self):
        """清理测试环境"""
        os.unlink(self.temp_pdf.name)

    def test_initialization(self):
        """测试初始化和自定义配置"""
        # 测试默认配置
        router = SinglePagePdfRouter()
        self.assertIsNotNone(router)

        # 测试自定义配置
        custom_config = {
            "ppt_marker_score_threshold": 0.8,
            "backend_preference": {
                "ppt_converted": "my_custom_ppt_backend"
            }
        }
        router = SinglePagePdfRouter(custom_config)
        self.assertEqual(router.config_manager.get("ppt_marker_score_threshold"), 0.8)
        self.assertEqual(router.config_manager.get("backend_preference.ppt_converted"), "my_custom_ppt_backend")

    @patch("pdf_router.core.feature_extractor.read_pdf_to_bytes")
    @patch("pdf_router.core.feature_extractor.get_pdf_page_count")
    @patch("pdf_router.core.feature_extractor.get_pdf_page_size")
    @patch("pdf_router.core.feature_extractor.get_pdf_metadata")
    @patch("pdf_router.adapters.mineru_adapter.MinerUAdapter.classify_pdf_type")
    @patch("pdf_router.adapters.mineru_adapter.MinerUAdapter.get_image_coverage_ratio")
    @patch("pdf_router.adapters.mineru_adapter.MinerUAdapter.get_avg_char_count")
    @patch("pdf_router.adapters.mineru_adapter.MinerUAdapter.has_cid_font")
    def test_evaluate_text_page(self, mock_has_cid, mock_avg_char, mock_image_ratio, mock_classify,
                                mock_metadata, mock_page_size, mock_page_count, mock_read_bytes):
        """测试纯文本单页评估"""
        # Mock返回值
        mock_read_bytes.return_value = self.mock_pdf_bytes
        mock_page_count.return_value = 1
        mock_page_size.return_value = (595, 842)  # A4
        mock_metadata.return_value = {"producer": "word", "creator": "word"}
        mock_classify.return_value = "text"
        mock_image_ratio.return_value = 0.1
        mock_avg_char.return_value = 500
        mock_has_cid.return_value = False

        # 测试路径输入
        result = self.router.evaluate_page(self.temp_pdf.name)
        self.assertEqual(result["page_index"], 0)
        self.assertEqual(result["source_type"], "path")
        self.assertIn(PdfTypeMark.TEXT_PDF, result["marks"])
        self.assertEqual(result["process_priority"], ProcessPriorityMark.SPEED_FIRST)
        self.assertEqual(result["recommended_backend"], RecommendedBackendMark.PIPELINE)
        self.assertTrue(any("纯文本类型" in sug for sug in result["processing_suggestions"]))

    @patch("pdf_router.core.feature_extractor.read_pdf_to_bytes")
    @patch("pdf_router.core.feature_extractor.get_pdf_page_count")
    @patch("pdf_router.core.feature_extractor.get_pdf_page_size")
    @patch("pdf_router.core.feature_extractor.get_pdf_metadata")
    @patch("pdf_router.adapters.mineru_adapter.MinerUAdapter.classify_pdf_type")
    @patch("pdf_router.adapters.mineru_adapter.MinerUAdapter.get_image_coverage_ratio")
    @patch("pdf_router.adapters.mineru_adapter.MinerUAdapter.get_avg_char_count")
    @patch("pdf_router.adapters.mineru_adapter.MinerUAdapter.has_cid_font")
    def test_evaluate_ppt_page(self, mock_has_cid, mock_avg_char, mock_image_ratio, mock_classify,
                               mock_metadata, mock_page_size, mock_page_count, mock_read_bytes):
        """测试PPT单页评估"""
        # Mock返回值符合PPT特征
        mock_read_bytes.return_value = self.mock_pdf_bytes
        mock_page_count.return_value = 1
        mock_page_size.return_value = (1920, 1080)  # 16:9 PPT
        mock_metadata.return_value = {"producer": "powerpoint", "creator": "ppt"}
        mock_classify.return_value = "text"
        mock_image_ratio.return_value = 0.75  # 超过0.7触发图片占比高的建议
        mock_avg_char.return_value = 80
        mock_has_cid.return_value = False

        # 测试bytes输入
        result = self.router.evaluate_page(self.mock_pdf_bytes)
        self.assertEqual(result["source_type"], "bytes")
        self.assertIn(PdfTypeMark.PPT_CONVERTED, result["marks"])
        self.assertEqual(result["process_priority"], ProcessPriorityMark.ACCURACY_FIRST)
        self.assertEqual(result["recommended_backend"], RecommendedBackendMark.PPT_SPECIAL)
        self.assertTrue(any("PPT转换生成" in sug for sug in result["processing_suggestions"]))
        self.assertTrue(any("图片占比较高" in sug for sug in result["processing_suggestions"]))

    @patch("pdf_router.core.feature_extractor.read_pdf_to_bytes")
    @patch("pdf_router.core.feature_extractor.get_pdf_page_count")
    @patch("pdf_router.core.feature_extractor.get_pdf_page_size")
    @patch("pdf_router.adapters.mineru_adapter.MinerUAdapter.classify_pdf_type")
    @patch("pdf_router.adapters.mineru_adapter.MinerUAdapter.get_image_coverage_ratio")
    @patch("pdf_router.adapters.mineru_adapter.MinerUAdapter.get_avg_char_count")
    def test_evaluate_low_quality_scan(self, mock_avg_char, mock_image_ratio, mock_classify,
                                       mock_page_size, mock_page_count, mock_read_bytes):
        """测试低质量扫描页评估"""
        mock_read_bytes.return_value = self.mock_pdf_bytes
        mock_page_count.return_value = 1
        mock_page_size.return_value = (595, 842)
        mock_classify.return_value = "ocr"
        mock_image_ratio.return_value = 0.9
        mock_avg_char.return_value = 10

        result = self.router.evaluate_page(self.temp_pdf.name)
        self.assertIn(PdfTypeMark.LOW_QUALITY_SCAN, result["marks"])
        self.assertEqual(result["process_priority"], ProcessPriorityMark.EXTREME_ACCURACY)
        self.assertEqual(result["recommended_backend"], RecommendedBackendMark.VLM)
        self.assertTrue(any("低质量扫描件" in sug for sug in result["processing_suggestions"]))

    def test_invalid_input(self):
        """测试异常输入"""
        # 不存在的路径
        with self.assertRaises(FileNotFoundError):
            self.router.evaluate_page("non_existent_pdf_12345.pdf")
        # 空bytes
        with self.assertRaises(ValueError):
            self.router.evaluate_page(b"")
        # 不支持的类型
        with self.assertRaises(TypeError):
            self.router.evaluate_page(12345) # 数字类型

if __name__ == "__main__":
    print("=" * 70)
    print("运行单页PDF评估功能测试...")
    print("=" * 70)
    unittest.main(verbosity=2)
