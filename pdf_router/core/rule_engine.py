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
        if any(keyword in producer.lower() or keyword in creator.lower() for keyword in ppt_keywords):
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

    def detect_toc_page(self, features: Dict, is_ppt_format: bool = False, page_position: float = 0.0) -> Tuple[bool, float]:
        """
        检测页面是否为目录页
        :param features: 目录特征字典
        :param is_ppt_format: 是否为PPT格式的PDF
        :param page_position: 页面在文档中的位置（0~1），0表示开头，1表示末尾。
                              对于合并PDF，调用方可传入局部位置（相对于分段锚点的距离）
        :return: (是否为目录页, 置信度得分)
        """
        if not self.config.get("enable_toc_detection"):
            return False, 0.0

        if not features:
            return False, 0.0

        score = 0.0

        # 强特征：如果有目录关键词，直接给基础保底分
        has_keywords = features.get("has_toc_keywords", False)
        keyword_confidence = features.get("toc_keyword_confidence", 0.0)
        page_number_ratio = features.get("page_number_ratio", 0.0)
        line_count = features.get("line_count", 0)

        # --------------------------
        # 防误判过滤规则（优先级最高）
        # --------------------------
        # 1. 页面行数太少处理：
        #  - 5行以下：不可能是目录
        #  - 5-10行：有目录关键词即可判定为极简目录（降低要求，适配短目录）
        if line_count < 5:
            return False, 0.0
        if 5 <= line_count < 10:
            if not has_keywords or keyword_confidence < 0.4:  # 降低要求，有关键词即可
                return False, 0.0

        # 2. 关键词置信度过低，即使匹配到也认为不是有效目录标题
        # 5-10行的极简目录已在上面通过0.4阈值检查，这里只过滤更低置信度的噪声
        if has_keywords and keyword_confidence < 0.4:
            has_keywords = False
            keyword_confidence = 0.0

        # 3. 有关键词但页码占比极低（<10%），只是提到了"目录"词而已，不是目录页
        if has_keywords and page_number_ratio < 0.1:
            return False, 0.2

        # 4. 页面平均长度太长（>100字符），是正文页
        avg_line_length = features.get("avg_line_length", 0)
        if avg_line_length > 100:
            return False, 0.0

        # --------------------------
        # 强判定规则：高置信度关键词直接判定为目录
        # --------------------------
        if has_keywords and keyword_confidence >= 0.4 and page_number_ratio >= 0.05:
            # 明确有目录标题+有少量页码特征，直接判定为目录页，置信度很高
            return True, 0.9

        # --------------------------
        # 防表格/榜单误判规则：
        # --------------------------
        digit_ratio = features.get("digit_ratio", 0.0)
        indent_variance = features.get("indent_variance", 0.0)
        leader_line_ratio = features.get("leader_line_ratio", 0.0)

        # 情况A：没有目录关键词的页面，阈值提高，必须特征非常符合才判定为目录
        if not has_keywords:
            # 无关键词的页面，得分需要达到普通阈值的1.2倍才可能是目录
            # 同时数字占比过高（>20%）+ 无引导线，基本是榜单/表格，直接排除
            if digit_ratio > 0.2 and leader_line_ratio == 0:
                return False, 0.1
            # 无关键词的目录只能是多页目录的后续页，需要页码占比极高
            if page_number_ratio < 0.3:
                return False, 0.2

        # 情况B：有关键词的页面，表格容忍度稍高
        else:
            if digit_ratio > 0.35 and indent_variance > 10000:  # 数字多+缩进非常不规律
                score -= 0.2

        # 正常给分
        if has_keywords:
            score += 0.2  # 保底分，确保有关键词的页面不会被漏掉
            # 极简目录额外加分：行数少但有明确关键词，补偿页码少导致的得分不足
            if line_count < 15:
                score += 0.15

        # 1. 文本模式特征（权重60%）
        # 目录关键词
        if has_keywords:
            score += keyword_confidence * self.config.get("toc_keyword_weight")

        # 页码模式（权重提高，适配跨行页码）
        page_number_ratio = features.get("page_number_ratio", 0.0)
        score += page_number_ratio * self.config.get("toc_page_number_weight")

        # 引导线（权重降低，很多中文目录不用引导点）
        leader_line_ratio = features.get("leader_line_ratio", 0.0)
        score += leader_line_ratio * self.config.get("toc_leader_line_weight")

        # 缩进一致性
        indentation_consistency = features.get("indentation_consistency", 0.0)
        score += indentation_consistency * self.config.get("toc_indentation_weight")

        # 新增：短行密集度特征（目录普遍是大量短行）
        line_count = features.get("line_count", 0)
        avg_line_length = features.get("avg_line_length", 0)
        if line_count >= 10 and avg_line_length <= 30:
            # 10行以上，平均每行长度<30字符，符合目录短行特征
            short_line_factor = min(1.0, line_count / 30) * (1 - min(1.0, avg_line_length / 50))
            score += short_line_factor * 0.1  # 额外加10%权重

        # 2. 结构特征（权重30%）
        structure_score = 0.0
        # 行数量在15~50之间是典型目录页特征
        line_count = features.get("line_count", 0)
        if 15 <= line_count <= 50:
            structure_score += 0.5
        elif 5 <= line_count < 15:  # 少量行的可能是PPT目录
            structure_score += 0.3 if is_ppt_format else 0.1

        # 图片占比低
        image_ratio = features.get("image_coverage_ratio", 0.0)
        if image_ratio < 0.2:
            structure_score += 0.3
        elif image_ratio < 0.4 and is_ppt_format:  # PPT目录允许更高的图片占比
            structure_score += 0.2

        # 平均行长度适中
        avg_line_length = features.get("avg_line_length", 0)
        if 20 <= avg_line_length <= 80:
            structure_score += 0.2

        score += structure_score * self.config.get("toc_structure_weight")

        # 3. 上下文特征（权重10%）
        context_score = 0.0
        # 目录页通常出现在文档前10%位置
        max_position = self.config.get("max_toc_page_position", 0.1)
        if page_position <= max_position:
            context_score += 0.7
        elif page_position <= max_position * 2:  # 允许出现在前20%位置，适当降分
            context_score += 0.3

        score += context_score * self.config.get("toc_context_weight")

        # 得分归一化
        # 强特征：如果页码比例超过0.6，直接判定为目录页
        page_number_ratio = features.get("page_number_ratio", 0.0)
        if page_number_ratio >= 0.6:
            score = max(score, 0.7)

        score = min(score, 1.0)

        # 根据是否为PPT选择不同阈值
        threshold = self.config.get("toc_ppt_score_threshold") if is_ppt_format else self.config.get("toc_score_threshold")

        return score >= threshold, score
