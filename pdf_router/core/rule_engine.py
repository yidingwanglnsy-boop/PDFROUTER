# Copyright (c) Opendatalab. All rights reserved.
"""
规则引擎模块
实现所有识别规则、判定逻辑，完全无状态，支持多线程安全调用
"""
from typing import Dict, Tuple
from ..config import ConfigManager
from ..constants import PdfTypeMark

class RuleEngine:
    """规则引擎"""
    def __init__(self, config: ConfigManager):
        """
        初始化规则引擎
        :param config: 配置管理器实例
        """
        self.config = config

    def detect_ppt_converted(self, features: Dict) -> Tuple[bool, float]:
        """
        检测是否为PPT转换的PDF页面/文档
        多维度加权打分，得分超过阈值判定为PPT
        :param features: 提取的PDF特征
        :return: (是否为PPT, 得分)
        """
        if not self.config.get("enable_ppt_detection"):
            return False, 0.0

        score = 0.0
        # 1. 宽高比匹配，权重30%
        aspect_ratio = features.get("aspect_ratio", 0.0)
        min_ratio = self.config.get("ppt_aspect_ratio_min")
        max_ratio = self.config.get("ppt_aspect_ratio_max")
        if min_ratio <= aspect_ratio <= max_ratio:
            score += 0.3

        # 2. 元数据匹配，权重40%
        metadata = features.get("metadata", {})
        producer = metadata.get("producer", "")
        creator = metadata.get("creator", "")
        ppt_keywords = ["powerpoint", "ppt", "pptx", "wps presentation", "keynote", "slides"]
        if any(keyword in producer or keyword in creator for keyword in ppt_keywords):
            score += 0.4

        # 3. 高图片占比匹配，权重15%
        image_ratio = features.get("image_coverage_ratio", 0.0)
        if image_ratio >= self.config.get("ppt_image_ratio_threshold"):
            score += 0.15

        # 4. 低文本密度匹配，权重15%
        avg_chars = features.get("avg_chars_per_page", features.get("char_count", 999))
        if avg_chars <= self.config.get("ppt_avg_char_threshold"):
            score += 0.15

        score = min(score, 1.0)
        threshold = self.config.get("ppt_marker_score_threshold")
        return score >= threshold, score

    def judge_low_quality_scan(self, features: Dict) -> bool:
        """
        判定是否为低质量扫描件
        判定规则：OCR类型 + 图片占比>80% + 字符数<20
        :param features: 提取的PDF特征
        :return: 是否为低质量扫描
        """
        if features.get("pdf_type") != "ocr":
            return False
        image_ratio = features.get("image_coverage_ratio", 0.0)
        char_count = features.get("avg_chars_per_page", features.get("char_count", 0))
        return image_ratio > 0.8 and char_count < 20

    def evaluate_layout_complexity(self, features: Dict) -> float:
        """
        评估布局复杂度，得分范围0~1，得分越高越复杂
        计算规则：
        - 图片占比：权重40%
        - 低文本密度：权重30%
        - 包含CID字体：权重30%
        :param features: 提取的PDF特征
        :return: 复杂度得分
        """
        if not self.config.get("enable_layout_analysis"):
            return 0.0

        complexity = 0.0
        # 高图片占比增加复杂度
        image_ratio = features.get("image_coverage_ratio", 0.0)
        complexity += image_ratio * 0.4

        # 低文本密度增加复杂度
        avg_chars = features.get("avg_chars_per_page", features.get("char_count", 999))
        if avg_chars < self.config.get("text_density_threshold"):
            complexity += 0.3

        # CID字体增加复杂度
        if features.get("has_cid_font", False):
            complexity += 0.3

        return min(complexity, 1.0)
