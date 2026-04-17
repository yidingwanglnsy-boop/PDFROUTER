#!/usr/bin/env python3
"""
规则引擎单元测试
"""
import os
import unittest
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pdf_router.core.rule_engine import RuleEngine
from pdf_router.config import ConfigManager


class TestRuleEngine(unittest.TestCase):
    """规则引擎测试类"""

    def setUp(self):
        """初始化测试环境"""
        self.config_manager = ConfigManager()
        self.rule_engine = RuleEngine(self.config_manager)

    def test_detect_ppt_converted_typical_case(self):
        """测试典型PPT转换PDF检测"""
        features = {
            "aspect_ratio": 1.777,  # 16:9标准PPT比例
            "metadata": {"producer": "Microsoft PowerPoint"},
            "image_coverage_ratio": 0.7,
            "avg_chars_per_page": 80
        }
        is_ppt, score = self.rule_engine.detect_ppt_converted(features)
        self.assertTrue(is_ppt)
        self.assertGreater(score, self.config_manager.get("ppt_marker_score_threshold"))

    def test_detect_ppt_converted_partial_features(self):
        """测试只有部分PPT特征的检测"""
        # 只有PowerPoint元数据
        features = {
            "aspect_ratio": 1.333,  # 4:3
            "metadata": {"producer": "Microsoft PowerPoint"},
            "image_coverage_ratio": 0.2,
            "avg_chars_per_page": 500
        }
        is_ppt, score = self.rule_engine.detect_ppt_converted(features)
        self.assertTrue(is_ppt)

        # 只有比例和图片占比，没有元数据
        features = {
            "aspect_ratio": 1.777,
            "metadata": {},
            "image_coverage_ratio": 0.8,
            "avg_chars_per_page": 100
        }
        is_ppt, score = self.rule_engine.detect_ppt_converted(features)
        self.assertTrue(is_ppt)

    def test_detect_ppt_converted_negative_case(self):
        """测试非PPT PDF检测"""
        features = {
            "aspect_ratio": 1.333,
            "metadata": {"producer": "Adobe Acrobat"},
            "image_coverage_ratio": 0.1,
            "avg_chars_per_page": 800
        }
        is_ppt, score = self.rule_engine.detect_ppt_converted(features)
        self.assertFalse(is_ppt)
        self.assertLess(score, self.config_manager.get("ppt_marker_score_threshold"))

    def test_detect_ppt_converted_edge_cases(self):
        """测试PPT检测边界情况"""
        # 刚好达到阈值
        features = {
            "aspect_ratio": 1.3,
            "metadata": {"producer": "powerpoint"},
            "image_coverage_ratio": 0.6,
            "avg_chars_per_page": 300
        }
        is_ppt, score = self.rule_engine.detect_ppt_converted(features)
        self.assertTrue(is_ppt)

        # 刚好低于阈值
        features = {
            "aspect_ratio": 1.0,
            "metadata": {},
            "image_coverage_ratio": 0.3,
            "avg_chars_per_page": 500
        }
        is_ppt, score = self.rule_engine.detect_ppt_converted(features)
        self.assertFalse(is_ppt)

    def test_judge_low_quality_scan_positive_case(self):
        """测试低质量扫描件判定阳性情况"""
        # 典型低质量扫描：OCR类型+高图片占比+极低字符
        features = {
            "pdf_type": "ocr",
            "image_coverage_ratio": 0.9,
            "avg_chars_per_page": 10
        }
        self.assertTrue(self.rule_engine.judge_low_quality_scan(features))

    def test_judge_low_quality_scan_negative_case(self):
        """测试低质量扫描件判定阴性情况"""
        # 普通扫描：字符数足够
        features = {
            "pdf_type": "ocr",
            "image_coverage_ratio": 0.8,
            "avg_chars_per_page": 200
        }
        self.assertFalse(self.rule_engine.judge_low_quality_scan(features))

        # 纯文本PDF，即使字符少也不是低质量扫描
        features = {
            "pdf_type": "text",
            "image_coverage_ratio": 0.1,
            "avg_chars_per_page": 10
        }
        self.assertFalse(self.rule_engine.judge_low_quality_scan(features))

    def test_evaluate_layout_complexity(self):
        """测试布局复杂度评估"""
        # 高复杂度：高图片占比+低文本密度+含CID字体
        features = {
            "image_coverage_ratio": 1.0,
            "avg_chars_per_page": 50,
            "has_cid_font": True
        }
        complexity = self.rule_engine.evaluate_layout_complexity(features)
        self.assertGreaterEqual(complexity, 0.7)

        # 中等复杂度：中等图片占比+中等文本密度
        features = {
            "image_coverage_ratio": 0.5,
            "avg_chars_per_page": 200,
            "has_cid_font": False
        }
        complexity = self.rule_engine.evaluate_layout_complexity(features)
        self.assertGreaterEqual(complexity, 0.3)
        self.assertLess(complexity, 0.7)

        # 低复杂度：低图片占比+高文本密度
        features = {
            "image_coverage_ratio": 0.1,
            "avg_chars_per_page": 800,
            "has_cid_font": False
        }
        complexity = self.rule_engine.evaluate_layout_complexity(features)
        self.assertLess(complexity, 0.3)


if __name__ == "__main__":
    unittest.main()
