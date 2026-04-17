#!/usr/bin/env python3
"""
标记生成器单元测试
"""
import os
import unittest
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pdf_router.core.mark_generator import MarkGenerator
from pdf_router.config import ConfigManager
from pdf_router.constants import (
    PdfTypeMark, ProcessPriorityMark, RecommendedBackendMark
)


class TestMarkGenerator(unittest.TestCase):
    """标记生成器测试类"""

    def setUp(self):
        """初始化测试环境"""
        self.config_manager = ConfigManager()
        self.mark_generator = MarkGenerator(self.config_manager)

    def _generate_rule_results(self, features):
        """辅助方法，生成规则结果"""
        return {
            "is_ppt_converted": features.get("is_ppt_converted", False),
            "ppt_score": features.get("ppt_score", 0.0),
            "is_low_quality_scan": features.get("is_low_quality_scan", False),
            "layout_complexity": features.get("layout_complexity", 0.0)
        }

    def test_generate_document_marks_text_pdf(self):
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
        rule_results = self._generate_rule_results(features)

        marks, priority, backend = self.mark_generator.generate_document_marks(features, rule_results)

        self.assertIn(PdfTypeMark.TEXT_PDF, marks)
        self.assertEqual(priority, ProcessPriorityMark.SPEED_FIRST)
        self.assertEqual(backend, RecommendedBackendMark.PIPELINE)

    def test_generate_document_marks_scan_pdf(self):
        """测试扫描版PDF标记生成"""
        features = {
            "pdf_type": "ocr",
            "image_coverage_ratio": 0.8,
            "avg_chars_per_page": 50,
            "has_cid_font": False,
            "is_ppt_converted": False,
            "layout_complexity": 0.4,
            "is_low_quality_scan": False
        }
        rule_results = self._generate_rule_results(features)

        marks, priority, backend = self.mark_generator.generate_document_marks(features, rule_results)

        self.assertIn(PdfTypeMark.SCAN_PDF, marks)
        self.assertEqual(priority, ProcessPriorityMark.BALANCE)
        self.assertEqual(backend, RecommendedBackendMark.HYBRID)

    def test_generate_document_marks_cid_font_pdf(self):
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
        rule_results = self._generate_rule_results(features)

        marks, priority, backend = self.mark_generator.generate_document_marks(features, rule_results)

        self.assertIn(PdfTypeMark.CID_FONT_PDF, marks)
        self.assertEqual(priority, ProcessPriorityMark.EXTREME_ACCURACY)
        self.assertEqual(backend, RecommendedBackendMark.VLM)

    def test_generate_document_marks_low_quality_scan(self):
        """测试低质量扫描PDF标记生成"""
        features = {
            "pdf_type": "ocr",
            "image_coverage_ratio": 0.9,
            "avg_chars_per_page": 10,
            "has_cid_font": False,
            "is_ppt_converted": False,
            "layout_complexity": 0.6,
            "is_low_quality_scan": True
        }
        rule_results = self._generate_rule_results(features)

        marks, priority, backend = self.mark_generator.generate_document_marks(features, rule_results)

        self.assertIn(PdfTypeMark.LOW_QUALITY_SCAN, marks)
        self.assertEqual(priority, ProcessPriorityMark.EXTREME_ACCURACY)
        self.assertEqual(backend, RecommendedBackendMark.VLM)

    def test_generate_document_marks_ppt_converted(self):
        """测试PPT转换PDF标记生成"""
        features = {
            "pdf_type": "text",
            "image_coverage_ratio": 0.7,
            "avg_chars_per_page": 150,
            "has_cid_font": False,
            "is_ppt_converted": True,
            "layout_complexity": 0.5,
            "is_low_quality_scan": False
        }
        rule_results = self._generate_rule_results(features)

        marks, priority, backend = self.mark_generator.generate_document_marks(features, rule_results)

        self.assertIn(PdfTypeMark.PPT_CONVERTED, marks)
        self.assertEqual(priority, ProcessPriorityMark.ACCURACY_FIRST)
        self.assertEqual(backend, RecommendedBackendMark.PPT_SPECIAL)

    def test_generate_document_marks_complex_layout(self):
        """测试复杂布局PDF标记生成"""
        features = {
            "pdf_type": "text",
            "image_coverage_ratio": 0.6,
            "avg_chars_per_page": 200,
            "has_cid_font": False,
            "is_ppt_converted": False,
            "layout_complexity": 0.8,
            "is_low_quality_scan": False
        }
        rule_results = self._generate_rule_results(features)

        marks, priority, backend = self.mark_generator.generate_document_marks(features, rule_results)

        self.assertIn(PdfTypeMark.COMPLEX_LAYOUT, marks)
        self.assertEqual(priority, ProcessPriorityMark.ACCURACY_FIRST)
        self.assertEqual(backend, RecommendedBackendMark.HYBRID)

    def test_generate_document_marks_mixed_pdf(self):
        """测试混合类型PDF标记生成"""
        features = {
            "pdf_type": "text",
            "image_coverage_ratio": 0.5,
            "avg_chars_per_page": 250,
            "has_cid_font": False,
            "is_ppt_converted": False,
            "layout_complexity": 0.4,
            "is_low_quality_scan": False
        }
        rule_results = self._generate_rule_results(features)

        marks, priority, backend = self.mark_generator.generate_document_marks(features, rule_results)

        self.assertIn(PdfTypeMark.MIXED_PDF, marks)
        self.assertEqual(priority, ProcessPriorityMark.BALANCE)
        self.assertEqual(backend, RecommendedBackendMark.HYBRID)

    def test_generate_document_marks_multiple_types(self):
        """测试同时命中多种类型的优先级处理"""
        # 同时是CID字体+低质量扫描+PPT转换，应该取最高优先级的标记
        features = {
            "pdf_type": "ocr",
            "image_coverage_ratio": 0.9,
            "avg_chars_per_page": 10,
            "has_cid_font": True,
            "is_ppt_converted": True,
            "layout_complexity": 0.7,
            "is_low_quality_scan": True
        }
        rule_results = self._generate_rule_results(features)

        marks, priority, backend = self.mark_generator.generate_document_marks(features, rule_results)

        # 应该包含所有命中的标记
        self.assertIn(PdfTypeMark.CID_FONT_PDF, marks)
        self.assertIn(PdfTypeMark.LOW_QUALITY_SCAN, marks)
        self.assertIn(PdfTypeMark.PPT_CONVERTED, marks)
        # 优先级取最高的
        self.assertEqual(priority, ProcessPriorityMark.EXTREME_ACCURACY)
        # 推荐后端取最高优先级对应的
        self.assertEqual(backend, RecommendedBackendMark.VLM)

    def test_custom_backend_preference(self):
        """测试自定义后端偏好配置"""
        custom_config = {
            "backend_preference": {
                "ppt_converted": "my_custom_ppt_backend",
                "cid_font_pdf": "my_custom_cid_backend"
            }
        }
        config_manager = ConfigManager(custom_config)
        mark_generator = MarkGenerator(config_manager)

        # 测试PPT类型使用自定义后端
        features = {
            "pdf_type": "text",
            "has_cid_font": False,
            "is_ppt_converted": True,
            "is_low_quality_scan": False
        }
        rule_results = self._generate_rule_results(features)

        marks, priority, backend = mark_generator.generate_document_marks(features, rule_results)
        self.assertEqual(backend, "my_custom_ppt_backend")

        # 测试CID字体类型使用自定义后端
        features = {
            "pdf_type": "text",
            "has_cid_font": True,
            "is_ppt_converted": False,
            "is_low_quality_scan": False
        }
        rule_results = self._generate_rule_results(features)

        marks, priority, backend = mark_generator.generate_document_marks(features, rule_results)
        self.assertEqual(backend, "my_custom_cid_backend")


if __name__ == "__main__":
    unittest.main()
