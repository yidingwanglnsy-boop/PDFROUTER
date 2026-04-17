# Copyright (c) Opendatalab. All rights reserved.
"""
PDF路由器主API实现
和v1.1.0版本接口完全兼容，返回结构完全一致
"""
from typing import Dict, Optional
from pathlib import Path
from ..config import ConfigManager
from ..core.feature_extractor import FeatureExtractor
from ..core.rule_engine import RuleEngine
from ..core.mark_generator import MarkGenerator
from ..constants import VERSION

class PdfRouter:
    """
    PDF智能路由器
    输入PDF路径，返回PDF特征、类型标记、处理优先级、推荐后端
    完全兼容v1.1.0版本接口
    """
    def __init__(self, config: Optional[Dict] = None):
        """
        初始化路由器
        :param config: 自定义配置，会和默认配置深度合并
        """
        self.config_manager = ConfigManager(config)
        self.feature_extractor = FeatureExtractor(self.config_manager)
        self.rule_engine = RuleEngine(self.config_manager)
        self.mark_generator = MarkGenerator(self.config_manager)

    def route(self, pdf_path: str) -> Dict:
        """
        对外主接口：输入PDF路径，返回所有特征和标记
        :param pdf_path: PDF文件路径
        :return: 路由结果，结构与v1.1.0完全一致
        """
        if not Path(pdf_path).exists():
            raise FileNotFoundError(f"PDF文件不存在：{pdf_path}")

        # 1. 提取特征
        features = self.feature_extractor.extract_document_features(pdf_path)
        if not features:
            raise RuntimeError(f"PDF特征提取失败：{pdf_path}")

        # 2. 规则判定
        is_ppt, ppt_score = self.rule_engine.detect_ppt_converted(features)
        is_low_quality = self.rule_engine.judge_low_quality_scan(features)
        layout_complexity = self.rule_engine.evaluate_layout_complexity(features)
        rule_results = {
            "is_ppt_converted": is_ppt,
            "ppt_score": ppt_score,
            "is_low_quality_scan": is_low_quality,
            "layout_complexity": layout_complexity
        }
        # 补充特征
        features["is_ppt_converted"] = is_ppt
        features["ppt_score"] = ppt_score
        features["layout_complexity"] = layout_complexity
        features["is_low_quality_scan"] = is_low_quality

        # 3. 生成标记
        marks, priority, backend = self.mark_generator.generate_document_marks(features, rule_results)

        # 4. 组装返回结果，与v1.1.0完全一致
        result = {
            "pdf_path": pdf_path,
            "features": features,
            "marks": marks,
            "process_priority": priority,
            "recommended_backend": backend,
            "router_version": VERSION
        }
        return result
