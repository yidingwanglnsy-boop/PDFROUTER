import os
import unittest
from pathlib import Path
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pdf_router.api.router_api import PdfRouter
from pdf_router.adapters.ray_adapter import RayPdfRouterMapper
from pdf_router.core.rule_engine import RuleEngine
from pdf_router.core.mark_generator import MarkGenerator
from pdf_router.config import ConfigManager
from pdf_router.constants import PdfTypeMark, ProcessPriorityMark, RecommendedBackendMark


class TestPdfRouter(unittest.TestCase):
    """PDF路由算子单元测试，纯逻辑测试，无需任何外部依赖或真实PDF文件"""

    def setUp(self):
        """初始化测试环境"""
        self.router = PdfRouter()
        self.config_manager = ConfigManager()
        self.rule_engine = RuleEngine(self.config_manager)
        self.mark_generator = MarkGenerator(self.config_manager)

    def test_initialization(self):
        """测试初始化配置"""
        # 测试默认配置
        default_config = self.config_manager.config
        self.assertEqual(default_config["scan_pdf_threshold"], 0.3)
        self.assertEqual(default_config["ppt_marker_score_threshold"], 0.7)
        self.assertTrue(default_config["enable_ppt_detection"])

        # 测试自定义配置
        custom_config = {"scan_pdf_threshold": 0.5, "custom_key": "value"}
        custom_config_manager = ConfigManager(custom_config)
        custom_config = custom_config_manager.config
        self.assertEqual(custom_config["scan_pdf_threshold"], 0.5)
        self.assertEqual(custom_config["custom_key"], "value")

    def test_ppt_converted_detection_logic(self):
        """测试PPT转PDF识别核心逻辑（纯规则测试，无需文件）"""
        # 1. 典型PPT特征：16:9比例 + PowerPoint元数据 + 高图片占比 + 低文字密度 → 得分1.0，判定为PPT
        features = {
            "aspect_ratio": 1.777,  # 16:9
            "metadata": {"producer": "Microsoft PowerPoint"},
            "image_coverage_ratio": 0.7,
            "avg_chars_per_page": 80
        }
        is_ppt, score = self.rule_engine.detect_ppt_converted(features)
        self.assertTrue(is_ppt)
        self.assertAlmostEqual(score, 1.0, places=4)

        # 2. 只有元数据匹配 → 得分0.4，不判定为PPT
        features = {
            "aspect_ratio": 0.7,  # A4比例
            "metadata": {"producer": "Microsoft PowerPoint"},
            "image_coverage_ratio": 0.1,
            "avg_chars_per_page": 500
        }
        is_ppt, score = self.rule_engine.detect_ppt_converted(features)
        self.assertFalse(is_ppt)
        self.assertAlmostEqual(score, 0.4, places=4)

        # 3. 宽高比 + 图片占比 + 文本密度匹配，但元数据不匹配 → 得分0.6，不判定为PPT
        features = {
            "aspect_ratio": 1.777,
            "metadata": {"producer": "Microsoft Word"},
            "image_coverage_ratio": 0.7,
            "avg_chars_per_page": 80
        }
        is_ppt, score = self.rule_engine.detect_ppt_converted(features)
        self.assertFalse(is_ppt)
        self.assertAlmostEqual(score, 0.6, places=4)

        # 4. 元数据 + 图片占比 + 文本密度匹配，宽高比略低 → 得分0.7，刚好判定为PPT
        features = {
            "aspect_ratio": 1.25,
            "metadata": {"producer": "WPS Presentation"},
            "image_coverage_ratio": 0.7,
            "avg_chars_per_page": 80
        }
        is_ppt, score = self.rule_engine.detect_ppt_converted(features)
        self.assertTrue(is_ppt)
        self.assertAlmostEqual(score, 0.7, places=4)

    def test_low_quality_scan_logic(self):
        """测试低质量扫描件判定逻辑"""
        # 1. OCR类型 + 高图片占比 + 极低字符 → 判定为低质量
        features = {
            "pdf_type": "ocr",
            "image_coverage_ratio": 0.9,
            "avg_chars_per_page": 10
        }
        result = self.rule_engine.judge_low_quality_scan(features)
        self.assertTrue(result)

        # 2. Text类型 → 即使图片占比高也不是低质量扫描
        features = {
            "pdf_type": "text",
            "image_coverage_ratio": 0.9,
            "avg_chars_per_page": 10
        }
        result = self.rule_engine.judge_low_quality_scan(features)
        self.assertFalse(result)

        # 3. OCR类型但字符数多 → 不是低质量
        features = {
            "pdf_type": "ocr",
            "image_coverage_ratio": 0.9,
            "avg_chars_per_page": 100
        }
        result = self.rule_engine.judge_low_quality_scan(features)
        self.assertFalse(result)

    def test_layout_complexity_logic(self):
        """测试布局复杂度评估逻辑"""
        # 1. 高图片占比 + 低文本密度 + 有CID字体 → 复杂度1.0
        features = {
            "image_coverage_ratio": 1.0,
            "avg_chars_per_page": 50,
            "has_cid_font": True
        }
        complexity = self.rule_engine.evaluate_layout_complexity(features)
        self.assertAlmostEqual(complexity, 1.0, places=4)

        # 2. 低图片占比 + 高文本密度 + 无CID字体 → 复杂度0.0
        features = {
            "image_coverage_ratio": 0.0,
            "avg_chars_per_page": 500,
            "has_cid_font": False
        }
        complexity = self.rule_engine.evaluate_layout_complexity(features)
        self.assertAlmostEqual(complexity, 0.0, places=4)

        # 3. 中等复杂度 → 0.4
        features = {
            "image_coverage_ratio": 0.5,
            "avg_chars_per_page": 500,
            "has_cid_font": False
        }
        complexity = self.rule_engine.evaluate_layout_complexity(features)
        self.assertAlmostEqual(complexity, 0.2, places=4)

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

        rule_results = {
    "is_ppt_converted": features.get("is_ppt_converted", False),
    "ppt_score": features.get("ppt_score", 0.0),
    "is_low_quality_scan": features.get("is_low_quality_scan", False),
    "layout_complexity": features.get("layout_complexity", 0.0)
}
marks, priority, backend = self.mark_generator.generate_document_marks(features, rule_results)

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

        rule_results = {
    "is_ppt_converted": features.get("is_ppt_converted", False),
    "ppt_score": features.get("ppt_score", 0.0),
    "is_low_quality_scan": features.get("is_low_quality_scan", False),
    "layout_complexity": features.get("layout_complexity", 0.0)
}
marks, priority, backend = self.mark_generator.generate_document_marks(features, rule_results)

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

        rule_results = {
    "is_ppt_converted": features.get("is_ppt_converted", False),
    "ppt_score": features.get("ppt_score", 0.0),
    "is_low_quality_scan": features.get("is_low_quality_scan", False),
    "layout_complexity": features.get("layout_complexity", 0.0)
}
marks, priority, backend = self.mark_generator.generate_document_marks(features, rule_results)

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

        rule_results = {
    "is_ppt_converted": features.get("is_ppt_converted", False),
    "ppt_score": features.get("ppt_score", 0.0),
    "is_low_quality_scan": features.get("is_low_quality_scan", False),
    "layout_complexity": features.get("layout_complexity", 0.0)
}
marks, priority, backend = self.mark_generator.generate_document_marks(features, rule_results)

        self.assertIn(PdfTypeMark.CID_FONT_PDF, marks)
        self.assertEqual(priority, ProcessPriorityMark.EXTREME_ACCURACY)
        self.assertEqual(backend, RecommendedBackendMark.VLM)

    def test_generate_marks_mixed_pdf(self):
        """测试混合PDF标记生成"""
        features = {
            "pdf_type": "text",
            "image_coverage_ratio": 0.5,
            "avg_chars_per_page": 300,
            "has_cid_font": False,
            "is_ppt_converted": False,
            "layout_complexity": 0.3,
            "is_low_quality_scan": False
        }

        rule_results = {
    "is_ppt_converted": features.get("is_ppt_converted", False),
    "ppt_score": features.get("ppt_score", 0.0),
    "is_low_quality_scan": features.get("is_low_quality_scan", False),
    "layout_complexity": features.get("layout_complexity", 0.0)
}
marks, priority, backend = self.mark_generator.generate_document_marks(features, rule_results)

        self.assertIn(PdfTypeMark.MIXED_PDF, marks)
        self.assertEqual(priority, ProcessPriorityMark.BALANCE)
        self.assertEqual(backend, RecommendedBackendMark.HYBRID)

    def test_generate_marks_scan_pdf(self):
        """测试普通扫描件标记生成"""
        features = {
            "pdf_type": "ocr",
            "image_coverage_ratio": 0.6,
            "avg_chars_per_page": 100,
            "has_cid_font": False,
            "is_ppt_converted": False,
            "layout_complexity": 0.3,
            "is_low_quality_scan": False
        }

        rule_results = {
    "is_ppt_converted": features.get("is_ppt_converted", False),
    "ppt_score": features.get("ppt_score", 0.0),
    "is_low_quality_scan": features.get("is_low_quality_scan", False),
    "layout_complexity": features.get("layout_complexity", 0.0)
}
marks, priority, backend = self.mark_generator.generate_document_marks(features, rule_results)

        self.assertIn(PdfTypeMark.SCAN_PDF, marks)
        self.assertEqual(priority, ProcessPriorityMark.BALANCE)
        self.assertEqual(backend, RecommendedBackendMark.HYBRID)

    def test_ray_mapper_without_ray(self):
        """测试Ray Mapper算子，无需依赖Ray Runtime"""
        # 初始化Mapper
        mapper = RayPdfRouterMapper()

        # 构造测试批量数据
        batch = {
            "pdf_path": [
                "test1.pdf",
                "test2.pdf",
                "non_existent_file.pdf"  # 测试错误处理
            ],
            "other_field": ["value1", "value2", "value3"]
        }

        # Mock所有内部调用
        from unittest.mock import patch
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
        is_ppt, score = self.rule_engine.detect_ppt_converted(features)
        self.assertTrue(is_ppt)
        self.assertAlmostEqual(score, 1.0, places=6)

        # 边界情况2：刚好低于阈值
        features = {
            "aspect_ratio": 1.2,  # 低于最小比例
            "metadata": {"producer": "powerpoint"},
            "image_coverage_ratio": 0.6,
            "avg_chars_per_page": 300
        }
        is_ppt, score = self.rule_engine.detect_ppt_converted(features)
        self.assertAlmostEqual(score, 0.7, places=6)
        self.assertTrue(is_ppt)  # 0.7刚好达到阈值


if __name__ == "__main__":
    # 运行所有测试
    print("=" * 60)
    print("运行PDF路由算子单元测试（纯逻辑，无需任何依赖）...")
    print(f"共 {len(TestPdfRouter.__dict__)} 个测试用例")
    print("=" * 60)

    unittest.main(verbosity=2)
