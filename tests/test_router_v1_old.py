import sys
import os
# 把MinerU根目录加到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import tempfile
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
from pdf_router import PdfRouter, RayPdfRouterMapper, PdfTypeMark, ProcessPriorityMark, RecommendedBackendMark

class TestPdfRouter(unittest.TestCase):
    """PDF路由算子单元测试，无需依赖Ray和真实PDF文件"""

    def setUp(self):
        """初始化测试环境"""
        self.router = PdfRouter()
        # 创建临时测试PDF文件（空文件，用于路径存在性测试）
        self.temp_pdf = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        self.temp_pdf.close()

    def tearDown(self):
        """清理测试环境"""
        os.unlink(self.temp_pdf.name)

    def test_initialization(self):
        """测试初始化配置"""
        # 测试默认配置
        self.assertEqual(self.router.config["scan_pdf_threshold"], 0.3)
        self.assertEqual(self.router.config["ppt_marker_score_threshold"], 0.7)
        self.assertTrue(self.router.config["enable_ppt_detection"])

        # 测试自定义配置
        custom_config = {"scan_pdf_threshold": 0.5, "custom_key": "value"}
        custom_router = PdfRouter(custom_config)
        self.assertEqual(custom_router.config["scan_pdf_threshold"], 0.5)
        self.assertEqual(custom_router.config["custom_key"], "value")

    @patch("pdf_router.pdf_router.get_page_count")
    @patch("pdf_router.pdf_router.get_page_size")
    @patch("pdf_router.pdf_router.classify_hybrid")
    @patch("pdf_router.pdf_router.get_high_image_coverage_ratio_pdfium")
    @patch("pdf_router.pdf_router.get_avg_cleaned_chars_per_page_pdfium")
    @patch("pdf_router.pdf_router.detect_cid_font_signal_pypdf")
    @patch("pdf_router.pdf_router.PdfRouter._extract_pdf_metadata")
    def test_extract_features_text_pdf(self, mock_metadata, mock_cid, mock_avg_chars,
                                       mock_image_ratio, mock_classify, mock_page_size,
                                       mock_page_count):
        """测试纯文本PDF特征提取"""
        # Mock返回值
        mock_page_count.return_value = 10
        mock_page_size.return_value = (595, 842)  # A4比例
        mock_classify.return_value = "text"
        mock_image_ratio.return_value = 0.1  # 低图片占比
        mock_avg_chars.return_value = 500  # 高文本密度
        mock_cid.return_value = False
        mock_metadata.return_value = {"producer": "microsoft word", "creator": "word"}

        features = self.router.extract_pdf_features(self.temp_pdf.name)

        # 验证特征
        self.assertEqual(features["page_count"], 10)
        self.assertAlmostEqual(features["aspect_ratio"], 595/842)
        self.assertEqual(features["pdf_type"], "text")
        self.assertEqual(features["image_coverage_ratio"], 0.1)
        self.assertEqual(features["avg_chars_per_page"], 500)
        self.assertFalse(features["has_cid_font"])
        self.assertFalse(features["is_ppt_converted"])
        self.assertFalse(features["is_low_quality_scan"])

    @patch("pdf_router.pdf_router.get_page_count")
    @patch("pdf_router.pdf_router.get_page_size")
    @patch("pdf_router.pdf_router.classify_hybrid")
    @patch("pdf_router.pdf_router.get_high_image_coverage_ratio_pdfium")
    @patch("pdf_router.pdf_router.get_avg_cleaned_chars_per_page_pdfium")
    @patch("pdf_router.pdf_router.detect_cid_font_signal_pypdf")
    @patch("pdf_router.pdf_router.PdfRouter._extract_pdf_metadata")
    def test_ppt_converted_detection(self, mock_metadata, mock_cid, mock_avg_chars,
                                     mock_image_ratio, mock_classify, mock_page_size,
                                     mock_page_count):
        """测试PPT转PDF识别"""
        # Mock返回值，符合PPT特征
        mock_page_count.return_value = 20
        mock_page_size.return_value = (1920, 1080)  # 16:9 PPT比例
        mock_classify.return_value = "text"
        mock_image_ratio.return_value = 0.7  # 高图片占比
        mock_avg_chars.return_value = 150  # 低文本密度
        mock_cid.return_value = False
        mock_metadata.return_value = {"producer": "microsoft powerpoint", "creator": "ppt"}

        features = self.router.extract_pdf_features(self.temp_pdf.name)

        # 验证PPT识别结果
        self.assertTrue(features["is_ppt_converted"])
        self.assertGreaterEqual(features["ppt_score"], 0.7)

    @patch("pdf_router.pdf_router.get_page_count")
    @patch("pdf_router.pdf_router.get_page_size")
    @patch("pdf_router.pdf_router.classify_hybrid")
    @patch("pdf_router.pdf_router.get_high_image_coverage_ratio_pdfium")
    @patch("pdf_router.pdf_router.get_avg_cleaned_chars_per_page_pdfium")
    @patch("pdf_router.pdf_router.detect_cid_font_signal_pypdf")
    @patch("pdf_router.pdf_router.PdfRouter._extract_pdf_metadata")
    def test_scan_pdf_detection(self, mock_metadata, mock_cid, mock_avg_chars,
                                mock_image_ratio, mock_classify, mock_page_size,
                                mock_page_count):
        """测试扫描版PDF识别"""
        mock_page_count.return_value = 5
        mock_page_size.return_value = (595, 842)
        mock_classify.return_value = "ocr"
        mock_image_ratio.return_value = 0.9  # 高图片占比
        mock_avg_chars.return_value = 10  # 极低文本密度
        mock_cid.return_value = False
        mock_metadata.return_value = {}

        features = self.router.extract_pdf_features(self.temp_pdf.name)

        self.assertEqual(features["pdf_type"], "ocr")
        self.assertTrue(features["is_low_quality_scan"])

    def test_generate_marks_text_pdf(self):
        """测试纯文本PDF标记生成"""
        features = {
            "pdf_type": "text",
            "image_coverage_ratio": 0.1,
            "avg_chars_per_page": 500,
            "has_cid_font": False,
            "is_ppt_converted": False,
            "layout_complexity": 0.1,
            "is_low_quality_scan": False
        }

        marks, priority, backend = self.router.generate_marks(features)

        self.assertIn(PdfTypeMark.TEXT_PDF, marks)
        self.assertEqual(priority, ProcessPriorityMark.SPEED_FIRST)
        self.assertEqual(backend, RecommendedBackendMark.PIPELINE)

    def test_generate_marks_ppt_pdf(self):
        """测试PPT转PDF标记生成"""
        features = {
            "pdf_type": "text",
            "image_coverage_ratio": 0.7,
            "avg_chars_per_page": 150,
            "has_cid_font": False,
            "is_ppt_converted": True,
            "layout_complexity": 0.5,
            "is_low_quality_scan": False
        }

        marks, priority, backend = self.router.generate_marks(features)

        self.assertIn(PdfTypeMark.PPT_CONVERTED, marks)
        self.assertIn(PdfTypeMark.COMPLEX_LAYOUT, marks)
        self.assertEqual(priority, ProcessPriorityMark.ACCURACY_FIRST)
        self.assertEqual(backend, RecommendedBackendMark.PPT_SPECIAL)

    def test_generate_marks_low_quality_scan(self):
        """测试低质量扫描件标记生成"""
        features = {
            "pdf_type": "ocr",
            "image_coverage_ratio": 0.9,
            "avg_chars_per_page": 10,
            "has_cid_font": False,
            "is_ppt_converted": False,
            "layout_complexity": 0.6,
            "is_low_quality_scan": True
        }

        marks, priority, backend = self.router.generate_marks(features)

        self.assertIn(PdfTypeMark.LOW_QUALITY_SCAN, marks)
        self.assertEqual(priority, ProcessPriorityMark.EXTREME_ACCURACY)
        self.assertEqual(backend, RecommendedBackendMark.VLM)

    def test_generate_marks_cid_font_pdf(self):
        """测试CID字体PDF标记生成"""
        features = {
            "pdf_type": "text",
            "image_coverage_ratio": 0.2,
            "avg_chars_per_page": 300,
            "has_cid_font": True,
            "is_ppt_converted": False,
            "layout_complexity": 0.3,
            "is_low_quality_scan": False
        }

        marks, priority, backend = self.router.generate_marks(features)

        self.assertIn(PdfTypeMark.CID_FONT_PDF, marks)
        self.assertEqual(priority, ProcessPriorityMark.EXTREME_ACCURACY)
        self.assertEqual(backend, RecommendedBackendMark.VLM)

    def test_ray_mapper_without_ray(self):
        """测试Ray Mapper算子，无需依赖Ray Runtime"""
        # 初始化Mapper
        mapper = RayPdfRouterMapper()

        # 构造测试批量数据
        batch = {
            "pdf_path": [
                self.temp_pdf.name,
                self.temp_pdf.name,
                "non_existent_file.pdf"  # 测试错误处理
            ],
            "other_field": ["value1", "value2", "value3"]
        }

        # Mock所有内部调用
        with patch.object(mapper.router, 'route') as mock_route:
            # 前两个文件正常返回
            mock_route.side_effect = [
                {"features": {"page_count": 10}, "marks": ["text_pdf"], "process_priority": "speed_first", "recommended_backend": "pipeline"},
                {"features": {"page_count": 20}, "marks": ["ppt_converted"], "process_priority": "accuracy_first", "recommended_backend": "ppt_special"},
                FileNotFoundError("File not found")  # 第三个文件报错
            ]

            # 调用Mapper
            result = mapper(batch)

            # 验证输出
            self.assertEqual(len(result["pdf_path"]), 3)
            self.assertEqual(len(result["features"]), 3)
            self.assertEqual(len(result["marks"]), 3)
            self.assertEqual(len(result["process_priority"]), 3)
            self.assertEqual(len(result["recommended_backend"]), 3)

            # 验证第一个文件结果
            self.assertEqual(result["marks"][0], ["text_pdf"])
            self.assertEqual(result["recommended_backend"][0], "pipeline")

            # 验证第二个文件结果
            self.assertEqual(result["marks"][1], ["ppt_converted"])
            self.assertEqual(result["recommended_backend"][1], "ppt_special")

            # 验证错误处理
            self.assertEqual(result["marks"][2], ["error"])
            self.assertEqual(result["recommended_backend"][2], "pipeline")

            # 验证原字段保留
            self.assertEqual(result["other_field"], ["value1", "value2", "value3"])

    def test_invalid_pdf_path(self):
        """测试无效PDF路径错误处理"""
        with self.assertRaises(FileNotFoundError):
            self.router.route("non_existent_pdf_file_12345.pdf")

    def test_ppt_detection_edge_cases(self):
        """测试PPT识别的边界情况"""
        # 边界情况1：刚好达到阈值
        features = {
            "aspect_ratio": 1.3,
            "metadata": {"producer": "powerpoint"},
            "image_coverage_ratio": 0.6,
            "avg_chars_per_page": 300
        }
        is_ppt, score = self.router._detect_ppt_converted(features)
        self.assertTrue(is_ppt)
        self.assertAlmostEqual(score, 1.0, places=6)  # 用近似比较避免浮点数精度问题

        # 边界情况2：刚好低于阈值
        features = {
            "aspect_ratio": 1.2,  # 低于最小比例
            "metadata": {"producer": "powerpoint"},
            "image_coverage_ratio": 0.6,
            "avg_chars_per_page": 300
        }
        is_ppt, score = self.router._detect_ppt_converted(features)
        self.assertAlmostEqual(score, 0.7, places=6)  # 用近似比较避免浮点数精度问题
        self.assertTrue(is_ppt)  # 0.7刚好达到阈值

if __name__ == "__main__":
    # 运行所有测试
    print("=" * 60)
    print("运行PDF路由算子单元测试...")
    print("=" * 60)

    unittest.main(verbosity=2)
