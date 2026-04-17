# Copyright (c) Opendatalab. All rights reserved.
"""
标记生成模块
根据提取的特征和规则判定结果，生成类型标记、处理优先级、推荐后端和处理建议
"""
from typing import Dict, Tuple, List
from ..config import ConfigManager
from ..constants import (
    PdfTypeMark,
    ProcessPriorityMark,
    RecommendedBackendMark
)

class MarkGenerator:
    """标记生成器"""
    def __init__(self, config: ConfigManager):
        """
        初始化标记生成器
        :param config: 配置管理器实例
        """
        self.config = config

    def generate_document_marks(self, features: Dict, rule_results: Dict) -> Tuple[List[str], str, str]:
        """
        生成整文档的标记
        :param features: 提取的特征
        :param rule_results: 规则引擎判定结果
        :return: (类型标记列表, 处理优先级, 推荐后端)
        """
        marks = []
        pdf_type_mark = ""
        priority = ""
        backend = ""

        # 1. 最高优先级标记：PPT转换
        if rule_results.get("is_ppt_converted", False):
            marks.append(PdfTypeMark.PPT_CONVERTED)
            pdf_type_mark = PdfTypeMark.PPT_CONVERTED

        # 2. 次高优先级：CID字体
        if features.get("has_cid_font", False):
            marks.append(PdfTypeMark.CID_FONT_PDF)
            if not pdf_type_mark:
                pdf_type_mark = PdfTypeMark.CID_FONT_PDF

        # 3. 次高优先级：低质量扫描
        if rule_results.get("is_low_quality_scan", False):
            marks.append(PdfTypeMark.LOW_QUALITY_SCAN)
            if not pdf_type_mark:
                pdf_type_mark = PdfTypeMark.LOW_QUALITY_SCAN

        # 4. 基础类型标记
        if not pdf_type_mark:
            pdf_type = features.get("pdf_type", "text")
            image_ratio = features.get("image_coverage_ratio", 0.0)
            scan_threshold = self.config.get("scan_pdf_threshold")
            if pdf_type == "text":
                if image_ratio < scan_threshold:
                    marks.append(PdfTypeMark.TEXT_PDF)
                    pdf_type_mark = PdfTypeMark.TEXT_PDF
                else:
                    marks.append(PdfTypeMark.MIXED_PDF)
                    pdf_type_mark = PdfTypeMark.MIXED_PDF
            else: # ocr类型
                marks.append(PdfTypeMark.SCAN_PDF)
                pdf_type_mark = PdfTypeMark.SCAN_PDF

        # 5. 复杂布局标记
        layout_complexity = rule_results.get("layout_complexity", 0.0)
        if layout_complexity > self.config.get("complex_layout_threshold"):
            marks.append(PdfTypeMark.COMPLEX_LAYOUT)

        # 6. 处理优先级
        if pdf_type_mark == PdfTypeMark.TEXT_PDF and layout_complexity < 0.2:
            priority = ProcessPriorityMark.SPEED_FIRST
        elif pdf_type_mark in [PdfTypeMark.LOW_QUALITY_SCAN, PdfTypeMark.CID_FONT_PDF]:
            priority = ProcessPriorityMark.EXTREME_ACCURACY
        elif PdfTypeMark.COMPLEX_LAYOUT in marks or pdf_type_mark == PdfTypeMark.PPT_CONVERTED:
            priority = ProcessPriorityMark.ACCURACY_FIRST
        else:
            priority = ProcessPriorityMark.BALANCE

        # 7. 推荐后端
        backend_preference = self.config.get("backend_preference", {})
        backend = backend_preference.get(pdf_type_mark, RecommendedBackendMark.HYBRID)

        return marks, priority, backend

    def generate_page_marks(self, features: Dict, rule_results: Dict) -> Tuple[List[str], str, str, List[str]]:
        """
        生成单页的标记和处理建议
        :param features: 提取的单页特征
        :param rule_results: 规则引擎判定结果
        :return: (类型标记列表, 处理优先级, 推荐后端, 处理建议列表)
        """
        # 复用文档标记生成逻辑
        marks, priority, backend = self.generate_document_marks(features, rule_results)
        # 生成单页专属的处理建议
        suggestions = self._generate_processing_suggestions(marks, features, rule_results)
        return marks, priority, backend, suggestions

    def _generate_processing_suggestions(self, marks: List[str], features: Dict, rule_results: Dict) -> List[str]:
        """
        根据页面特征生成定制化处理建议
        :param marks: 类型标记列表
        :param features: 页面特征
        :param rule_results: 规则结果
        :return: 建议列表
        """
        suggestions = []
        # PPT建议
        if PdfTypeMark.PPT_CONVERTED in marks:
            ppt_score = rule_results.get("ppt_score", 0.0)
            suggestions.append(f"页面为PPT转换生成，建议使用PPT专用解析模型（识别得分：{ppt_score:.2f}）")
            image_ratio = features.get("image_coverage_ratio", 0.0)
            if image_ratio > 0.7:
                suggestions.append("页面图片占比较高，建议启用图片提取和OCR功能")
        # 低质量扫描建议
        if PdfTypeMark.LOW_QUALITY_SCAN in marks:
            suggestions.append("页面为低质量扫描件，建议使用VLM大模型解析，禁用快速文本提取")
        # CID字体建议
        if PdfTypeMark.CID_FONT_PDF in marks:
            suggestions.append("页面包含CID字体，文本提取会出现乱码，建议使用VLM或OCR解析")
        # 复杂布局建议
        if PdfTypeMark.COMPLEX_LAYOUT in marks:
            complexity = rule_results.get("layout_complexity", 0.0)
            suggestions.append(f"页面布局复杂度较高（得分：{complexity:.2f}），建议启用高级布局分析")
        # 扫描PDF建议
        if PdfTypeMark.SCAN_PDF in marks and PdfTypeMark.LOW_QUALITY_SCAN not in marks:
            suggestions.append("页面为扫描件，建议使用hybrid混合引擎解析，平衡速度和精度")
        # 混合PDF建议
        if PdfTypeMark.MIXED_PDF in marks:
            suggestions.append("页面为图文混合类型，建议启用公式和表格识别功能")
        # 纯文本建议
        if PdfTypeMark.TEXT_PDF in marks and len(suggestions) == 0:
            suggestions.append("页面为纯文本类型，建议使用pipeline快速解析，无需大模型")
        return suggestions
