# Copyright (c) Opendatalab. All rights reserved.
"""
单页PDF评估API
新增v2.0.0功能，支持单页PDF路径或bytes输入，返回单页特征、标记、处理建议
"""
from typing import Dict, Optional, Union
from pathlib import Path
from ..config import ConfigManager
from ..core.feature_extractor import FeatureExtractor
from ..core.rule_engine import RuleEngine
from ..core.mark_generator import MarkGenerator
from ..constants import VERSION
from ..utils.io_utils import validate_pdf_path

class SinglePagePdfRouter:
    """
    单页PDF智能评估器
    支持输入单页PDF路径或二进制内容，返回单页的完整特征、类型标记、处理建议
    纯CPU运行，处理速度10-50ms/页
    """
    def __init__(self, config: Optional[Dict] = None):
        """
        初始化单页路由器
        :param config: 自定义配置，与PdfRouter配置体系完全兼容
        """
        self.config_manager = ConfigManager(config)
        self.feature_extractor = FeatureExtractor(self.config_manager)
        self.rule_engine = RuleEngine(self.config_manager)
        self.mark_generator = MarkGenerator(self.config_manager)

    def evaluate_page(self, page_input: Union[str, bytes], page_index: int = 0) -> Dict:
        """
        评估单页PDF
        :param page_input: PDF文件路径 或 PDF二进制内容
        :param page_index: 要评估的页面索引，默认0（第一页）
        :return: 单页评估结果，包含：
            - page_index: 评估的页面索引
            - source_type: 输入源类型（"path"或"bytes"）
            - features: 页面完整特征
            - marks: 类型标记列表
            - process_priority: 处理优先级
            - recommended_backend: 推荐后端
            - processing_suggestions: 定制化处理建议列表
            - router_version: 版本号
        """
        # 参数校验
        source_type = "unknown"
        if isinstance(page_input, str):
            source_type = "path"
            if not validate_pdf_path(page_input):
                raise FileNotFoundError(f"PDF文件不存在或不合法：{page_input}")
        elif isinstance(page_input, bytes):
            source_type = "bytes"
            if len(page_input) == 0:
                raise ValueError("PDF二进制内容为空")
        else:
            raise TypeError("page_input仅支持str（路径）或bytes（二进制）类型")

        # 1. 提取单页特征
        features = self.feature_extractor.extract_page_features(page_input, page_index)
        if not features:
            raise RuntimeError(f"PDF页面特征提取失败：page_index={page_index}")

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

        # 3. 生成标记和处理建议
        marks, priority, backend, suggestions = self.mark_generator.generate_page_marks(features, rule_results)

        # 4. 组装返回结果
        result = {
            "page_index": page_index,
            "source_type": source_type,
            "features": features,
            "marks": marks,
            "process_priority": priority,
            "recommended_backend": backend,
            "processing_suggestions": suggestions,
            "router_version": VERSION
        }
        return result
