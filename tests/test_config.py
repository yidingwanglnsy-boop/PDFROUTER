#!/usr/bin/env python3
"""
配置管理器单元测试
"""
import os
import unittest
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pdf_router.config import ConfigManager
from pdf_router.constants import DEFAULT_CONFIG


class TestConfigManager(unittest.TestCase):
    """配置管理器测试类"""

    def test_default_config_loading(self):
        """测试默认配置加载正确性"""
        config_manager = ConfigManager()
        config = config_manager.config

        # 验证核心默认配置
        self.assertEqual(config["scan_pdf_threshold"], DEFAULT_CONFIG["scan_pdf_threshold"])
        self.assertEqual(config["ppt_marker_score_threshold"], DEFAULT_CONFIG["ppt_marker_score_threshold"])
        self.assertEqual(config["enable_ppt_detection"], DEFAULT_CONFIG["enable_ppt_detection"])
        self.assertEqual(config["max_sample_pages"], DEFAULT_CONFIG["max_sample_pages"])

    def test_custom_config_merge(self):
        """测试自定义配置深度合并"""
        custom_config = {
            "scan_pdf_threshold": 0.5,
            "backend_preference": {
                "ppt_converted": "custom_ppt_backend",
                "low_quality_scan": "custom_ocr_backend"
            },
            "custom_key": "custom_value"
        }

        config_manager = ConfigManager(custom_config)
        config = config_manager.config

        # 验证自定义配置已合并
        self.assertEqual(config["scan_pdf_threshold"], 0.5)
        self.assertEqual(config["backend_preference"]["ppt_converted"], "custom_ppt_backend")
        self.assertEqual(config["backend_preference"]["low_quality_scan"], "custom_ocr_backend")
        self.assertEqual(config["custom_key"], "custom_value")
        # 验证未覆盖的默认配置保持不变
        self.assertEqual(config["text_density_threshold"], DEFAULT_CONFIG["text_density_threshold"])

    def test_config_validation_threshold(self):
        """测试阈值类配置校验"""
        # 无效阈值：小于0
        custom_config = {"scan_pdf_threshold": -0.1}
        config_manager = ConfigManager(custom_config)
        self.assertEqual(config_manager.get("scan_pdf_threshold"), DEFAULT_CONFIG["scan_pdf_threshold"])

        # 无效阈值：大于1
        custom_config = {"scan_pdf_threshold": 1.5}
        config_manager = ConfigManager(custom_config)
        self.assertEqual(config_manager.get("scan_pdf_threshold"), 1.0)

        # 宽高比阈值允许大于1
        custom_config = {"ppt_aspect_ratio_max": 3.0}
        config_manager = ConfigManager(custom_config)
        self.assertEqual(config_manager.get("ppt_aspect_ratio_max"), 3.0)

    def test_config_validation_integer(self):
        """测试整数类配置校验"""
        # 非整数类型
        custom_config = {"max_sample_pages": "10"}
        config_manager = ConfigManager(custom_config)
        self.assertEqual(config_manager.get("max_sample_pages"), DEFAULT_CONFIG["max_sample_pages"])

        # 负整数
        custom_config = {"max_sample_pages": -5}
        config_manager = ConfigManager(custom_config)
        self.assertEqual(config_manager.get("max_sample_pages"), DEFAULT_CONFIG["max_sample_pages"])

    def test_config_validation_boolean(self):
        """测试布尔类配置校验"""
        # 非布尔类型
        custom_config = {"enable_ppt_detection": "true"}
        config_manager = ConfigManager(custom_config)
        self.assertTrue(config_manager.get("enable_ppt_detection"))

        custom_config = {"enable_ppt_detection": 0}
        config_manager = ConfigManager(custom_config)
        self.assertFalse(config_manager.get("enable_ppt_detection"))

    def test_config_get_method(self):
        """测试get方法按路径获取配置"""
        custom_config = {
            "backend_preference": {
                "ppt_converted": "custom_ppt_backend"
            }
        }
        config_manager = ConfigManager(custom_config)

        # 直接获取
        self.assertEqual(config_manager.get("scan_pdf_threshold"), DEFAULT_CONFIG["scan_pdf_threshold"])
        # 路径获取
        self.assertEqual(config_manager.get("backend_preference.ppt_converted"), "custom_ppt_backend")
        # 不存在的键返回默认值
        self.assertEqual(config_manager.get("non_existent_key", "default"), "default")
        self.assertEqual(config_manager.get("backend_preference.non_existent", "default"), "default")


if __name__ == "__main__":
    unittest.main()
