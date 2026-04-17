#!/usr/bin/env python3
"""
PDF路由器对外接口测试
测试公共API的正确性、兼容性和异常处理
"""
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pdf_router import PdfRouter, RayPdfRouterMapper
from pdf_router.constants import (
    PdfTypeMark, ProcessPriorityMark, RecommendedBackendMark, VERSION
)


class TestPdfRouter(unittest.TestCase):
    """PDF路由算子单元测试，测试对外公共API"""

    def setUp(self):
        """初始化测试环境"""
        self.router = PdfRouter()
        # 创建临时测试PDF文件（空文件，用于路径存在性测试）
        self.temp_pdf = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        self.temp_pdf.close()

    def tearDown(self):
        """清理测试环境"""
        os.unlink(self.temp_pdf.name)

    def test_initialization_default_config(self):
        """测试默认初始化配置"""
        router = PdfRouter()
        # 验证配置已加载
        self.assertIsNotNone(router.config_manager)
        self.assertIsNotNone(router.feature_extractor)
        self.assertIsNotNone(router.rule_engine)
        self.assertIsNotNone(router.mark_generator)

    def test_initialization_custom_config(self):
        """测试自定义配置初始化"""
        custom_config = {
            "scan_pdf_threshold": 0.5,
            "ppt_marker_score_threshold": 0.8,
            "enable_ppt_detection": True,
            "backend_preference": {
                "ppt_converted": "custom_ppt_backend"
            }
        }
        router = PdfRouter(custom_config)
        # 验证自定义配置已生效
        self.assertEqual(router.config_manager.get("scan_pdf_threshold"), 0.5)
        self.assertEqual(router.config_manager.get("ppt_marker_score_threshold"), 0.8)
        self.assertEqual(router.config_manager.get("backend_preference.ppt_converted"), "custom_ppt_backend")

    def test_route_invalid_pdf_path(self):
        """测试传入不存在的PDF路径时的异常处理"""
        with self.assertRaises(FileNotFoundError):
            self.router.route("/path/does/not/exist.pdf")

    @patch("pdf_router.core.feature_extractor.FeatureExtractor.extract_document_features")
    def test_route_feature_extraction_failure(self, mock_extract):
        """测试特征提取失败时的异常处理"""
        mock_extract.return_value = None
        with self.assertRaises(RuntimeError):
            self.router.route(self.temp_pdf.name)

    @patch("pdf_router.core.feature_extractor.FeatureExtractor.extract_document_features")
    def test_route_text_pdf(self, mock_extract):
        """测试纯文本PDF路由结果"""
        # Mock特征返回
        mock_extract.return_value = {
            "pdf_type": "text",
            "image_coverage_ratio": 0.1,
            "avg_chars_per_page": 500,
            "has_cid_font": False,
            "page_count": 10,
            "metadata": {}
        }

        result = self.router.route(self.temp_pdf.name)

        # 验证返回结构完整
        self.assertEqual(result["pdf_path"], self.temp_pdf.name)
        self.assertEqual(result["router_version"], VERSION)
        self.assertIn("features", result)
        self.assertIn("marks", result)
        self.assertIn("process_priority", result)
        self.assertIn("recommended_backend", result)

        # 验证标记正确
        self.assertIn(PdfTypeMark.TEXT_PDF, result["marks"])
        self.assertEqual(result["process_priority"], ProcessPriorityMark.SPEED_FIRST)
        self.assertEqual(result["recommended_backend"], RecommendedBackendMark.PIPELINE)

    @patch("pdf_router.core.feature_extractor.FeatureExtractor.extract_document_features")
    def test_route_scan_pdf(self, mock_extract):
        """测试扫描版PDF路由结果"""
        mock_extract.return_value = {
            "pdf_type": "ocr",
            "image_coverage_ratio": 0.8,
            "avg_chars_per_page": 50,
            "has_cid_font": False,
            "page_count": 5,
            "metadata": {}
        }

        result = self.router.route(self.temp_pdf.name)
        self.assertIn(PdfTypeMark.SCAN_PDF, result["marks"])
        self.assertEqual(result["process_priority"], ProcessPriorityMark.BALANCE)
        self.assertEqual(result["recommended_backend"], RecommendedBackendMark.HYBRID)

    @patch("pdf_router.core.feature_extractor.FeatureExtractor.extract_document_features")
    def test_route_cid_font_pdf(self, mock_extract):
        """测试含CID字体PDF路由结果"""
        mock_extract.return_value = {
            "pdf_type": "text",
            "image_coverage_ratio": 0.2,
            "avg_chars_per_page": 300,
            "has_cid_font": True,
            "page_count": 20,
            "metadata": {}
        }

        result = self.router.route(self.temp_pdf.name)
        self.assertIn(PdfTypeMark.CID_FONT_PDF, result["marks"])
        self.assertEqual(result["process_priority"], ProcessPriorityMark.EXTREME_ACCURACY)
        self.assertEqual(result["recommended_backend"], RecommendedBackendMark.VLM)

    @patch("pdf_router.core.feature_extractor.FeatureExtractor.extract_document_features")
    def test_route_ppt_converted_pdf(self, mock_extract):
        """测试PPT转换PDF路由结果"""
        mock_extract.return_value = {
            "pdf_type": "text",
            "image_coverage_ratio": 0.7,
            "avg_chars_per_page": 100,
            "has_cid_font": False,
            "page_count": 30,
            "metadata": {"producer": "Microsoft PowerPoint"},
            "aspect_ratio": 1.777  # 16:9
        }

        result = self.router.route(self.temp_pdf.name)
        self.assertIn(PdfTypeMark.PPT_CONVERTED, result["marks"])
        self.assertEqual(result["process_priority"], ProcessPriorityMark.ACCURACY_FIRST)
        self.assertEqual(result["recommended_backend"], RecommendedBackendMark.PPT_SPECIAL)

    @patch("pdf_router.core.feature_extractor.FeatureExtractor.extract_document_features")
    def test_route_low_quality_scan_pdf(self, mock_extract):
        """测试低质量扫描PDF路由结果"""
        mock_extract.return_value = {
            "pdf_type": "ocr",
            "image_coverage_ratio": 0.9,
            "avg_chars_per_page": 10,
            "has_cid_font": False,
            "page_count": 15,
            "metadata": {}
        }

        result = self.router.route(self.temp_pdf.name)
        self.assertIn(PdfTypeMark.LOW_QUALITY_SCAN, result["marks"])
        self.assertEqual(result["process_priority"], ProcessPriorityMark.EXTREME_ACCURACY)
        self.assertEqual(result["recommended_backend"], RecommendedBackendMark.VLM)

    @patch("pdf_router.core.feature_extractor.FeatureExtractor.extract_document_features")
    def test_route_mixed_pdf(self, mock_extract):
        """测试混合类型PDF路由结果"""
        mock_extract.return_value = {
            "pdf_type": "text",
            "image_coverage_ratio": 0.5,
            "avg_chars_per_page": 200,
            "has_cid_font": False,
            "page_count": 25,
            "metadata": {}
        }

        result = self.router.route(self.temp_pdf.name)
        self.assertIn(PdfTypeMark.MIXED_PDF, result["marks"])
        self.assertEqual(result["process_priority"], ProcessPriorityMark.BALANCE)
        self.assertEqual(result["recommended_backend"], RecommendedBackendMark.HYBRID)

    def test_ray_mapper_without_ray(self):
        """测试Ray适配器在Ray未安装时的延迟导入错误"""
        # 清除已导入的Ray模块（如果有）
        if 'ray' in sys.modules:
            del sys.modules['ray']

        with self.assertRaises(ImportError):
            # 实例化时应该抛出导入错误，提示安装Ray
            RayPdfRouterMapper()


if __name__ == "__main__":
    unittest.main()
