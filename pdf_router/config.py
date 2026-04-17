# Copyright (c) Opendatalab. All rights reserved.
"""
配置管理模块
负责默认配置加载、自定义配置合并、配置校验
"""
from typing import Dict, Optional
from copy import deepcopy
from .constants import DEFAULT_CONFIG

class ConfigManager:
    """配置管理器"""
    def __init__(self, custom_config: Optional[Dict] = None):
        """
        初始化配置管理器
        :param custom_config: 自定义配置，会和默认配置深度合并
        """
        self._config = self._merge_config(deepcopy(DEFAULT_CONFIG), custom_config or {})
        self._validate_config()

    def _merge_config(self, default: Dict, custom: Dict) -> Dict:
        """
        深度合并配置，自定义配置优先级高于默认配置
        :param default: 默认配置
        :param custom: 自定义配置
        :return: 合并后的配置
        """
        merged = default.copy()
        for key, value in custom.items():
            if isinstance(value, dict) and key in merged and isinstance(merged[key], dict):
                merged[key] = self._merge_config(merged[key], value)
            else:
                merged[key] = value
        return merged

    def _validate_config(self) -> None:
        """
        校验配置参数合法性，不合法的参数自动修正并给出警告
        """
        # 阈值类参数校验，确保在0~1范围内
        threshold_keys = [
            "scan_pdf_threshold", "text_density_threshold", "cid_font_threshold",
            "complex_layout_threshold", "ppt_aspect_ratio_min", "ppt_aspect_ratio_max",
            "ppt_image_ratio_threshold", "ppt_marker_score_threshold"
        ]
        for key in threshold_keys:
            if key in self._config:
                value = self._config[key]
                if not isinstance(value, (int, float)):
                    self._config[key] = DEFAULT_CONFIG[key]
                elif value < 0 or value > 10: # 宽高比允许到10，其他阈值0~1
                    if key in ["ppt_aspect_ratio_min", "ppt_aspect_ratio_max"] and value <= 10:
                        pass
                    else:
                        self._config[key] = max(0.0, min(1.0, float(value)))

        # 数字类参数校验，确保是正整数
        int_keys = ["ppt_avg_char_threshold", "max_sample_pages"]
        for key in int_keys:
            if key in self._config:
                value = self._config[key]
                if not isinstance(value, int) or value <= 0:
                    self._config[key] = DEFAULT_CONFIG[key]

        # 布尔类参数校验
        bool_keys = ["enable_ppt_detection", "enable_layout_analysis"]
        for key in bool_keys:
            if key in self._config:
                if not isinstance(self._config[key], bool):
                    self._config[key] = bool(self._config[key])

    @property
    def config(self) -> Dict:
        """获取合并后的完整配置"""
        return deepcopy(self._config)

    def get(self, key: str, default=None):
        """获取指定配置项"""
        keys = key.split('.')
        value = self._config
        for k in keys:
            if k not in value:
                return default
            value = value[k]
        return value
