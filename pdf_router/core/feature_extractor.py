# Copyright (c) Opendatalab. All rights reserved.
"""
特征提取模块
支持整文档特征提取和单页特征提取两种模式
"""
import fitz
import re
import io
from typing import Dict, Optional, Union, List
from ..config import ConfigManager
from ..adapters.mineru_adapter import MinerUAdapter
from ..constants import TOC_KEYWORDS
from ..utils.pdf_utils import (
    get_pdf_page_count,
    get_pdf_page_size,
    get_pdf_metadata,
    get_sample_page_indices
)
from ..utils.io_utils import read_pdf_to_bytes

class FeatureExtractor:
    """特征提取器"""
    def __init__(self, config: ConfigManager):
        """
        初始化特征提取器
        :param config: 配置管理器实例
        """
        self.config = config
        self.mineru_adapter = MinerUAdapter()

    def extract_document_features(self, pdf_path: str) -> Optional[Dict]:
        """
        提取整文档的特征
        :param pdf_path: PDF文件路径
        :return: 文档特征字典，失败返回None
        """
        pdf_bytes = read_pdf_to_bytes(pdf_path)
        if not pdf_bytes:
            return None

        features = {}
        # 1. 基础信息
        page_count = get_pdf_page_count(pdf_bytes) or 0
        features["page_count"] = page_count
        if page_count <= 0:
            return None

        first_page_size = get_pdf_page_size(pdf_bytes, 0) or (0, 0)
        features["page_width"], features["page_height"] = first_page_size
        features["aspect_ratio"] = first_page_size[0] / first_page_size[1] if first_page_size[1] > 0 else 0.0

        # 2. 元数据
        features["metadata"] = get_pdf_metadata(pdf_bytes)

        # 3. 采样页面
        sample_pages = get_sample_page_indices(page_count, self.config.get("max_sample_pages"))
        if not sample_pages:
            return None

        # 4. 分类特征
        features["pdf_type"] = self.mineru_adapter.classify_pdf_type(pdf_bytes)
        features["image_coverage_ratio"] = self.mineru_adapter.get_image_coverage_ratio(pdf_bytes, sample_pages)
        features["avg_chars_per_page"] = self.mineru_adapter.get_avg_char_count(pdf_bytes, sample_pages)
        features["has_cid_font"] = self.mineru_adapter.has_cid_font(pdf_bytes, sample_pages)

        return features

    def extract_page_features(self, pdf_input: Union[str, bytes], page_index: int = 0) -> Optional[Dict]:
        """
        提取单页PDF的特征
        :param pdf_input: PDF文件路径或二进制内容
        :param page_index: 要提取的页面索引，默认0
        :return: 页面特征字典，失败返回None
        """
        pdf_bytes = read_pdf_to_bytes(pdf_input)
        if not pdf_bytes:
            return None

        features = {}
        # 1. 基础信息
        page_count = get_pdf_page_count(pdf_bytes) or 0
        if page_count <= 0 or page_index < 0 or page_index >= page_count:
            return None

        page_size = get_pdf_page_size(pdf_bytes, page_index) or (0, 0)
        features["page_width"], features["page_height"] = page_size
        features["aspect_ratio"] = page_size[0] / page_size[1] if page_size[1] > 0 else 0.0

        # 2. 元数据
        features["metadata"] = get_pdf_metadata(pdf_bytes)

        # 3. 分类特征，单页模式只采样当前页面
        target_pages = [page_index]
        features["pdf_type"] = self.mineru_adapter.classify_pdf_type(pdf_bytes)
        features["image_coverage_ratio"] = self.mineru_adapter.get_image_coverage_ratio(pdf_bytes, target_pages)
        features["char_count"] = self.mineru_adapter.get_avg_char_count(pdf_bytes, target_pages) # 单页是实际字符数
        features["has_cid_font"] = self.mineru_adapter.has_cid_font(pdf_bytes, target_pages)

        return features

    def extract_toc_features(self, doc: fitz.Document, page_index: int) -> Optional[Dict]:
        """
        提取页面的目录相关特征
        :param doc: pymupdf文档对象
        :param page_index: 页面索引
        :return: 目录特征字典，失败返回None
        """
        try:
            if page_index < 0 or page_index >= len(doc):
                return None

            page = doc.load_page(page_index)
            features = {}

            # 1. 提取带位置的文本块
            text_blocks = self.mineru_adapter.extract_text_with_positions(page)
            if not text_blocks:
                return None

            # 2. 提取所有文本行
            lines = [block["text"] for block in text_blocks if block["text"].strip()]
            if not lines:
                return None

            # 3. 检测目录关键词
            has_toc_keywords = False
            toc_keyword_confidence = 0.0
            max_font_size = max(block["font_size"] for block in text_blocks) if text_blocks else 0

            # 关键词通常出现在页面顶部，且字体较大
            top_blocks = [block for block in text_blocks if block["y0"] < page.rect.height * 0.3]  # 扩大顶部范围到30%
            for block in top_blocks:
                text = block["text"].strip()
                if not text:
                    continue
                # 处理关键词中间有空格的情况：去掉文本中所有空格再匹配
                text_no_space = text.replace(" ", "").replace("\t", "").replace("\u3000", "")
                # 检查中英文关键词
                for lang, keywords in TOC_KEYWORDS.items():
                    for keyword in keywords:
                        keyword_no_space = keyword.replace(" ", "")
                        # 匹配：原文包含关键词 或者 去空格后包含去空格的关键词
                        if keyword in text or keyword_no_space in text_no_space:
                            has_toc_keywords = True
                            # 1. 字体大小权重：越大权重越高，最大字体的关键词权重拉满
                            font_size_factor = min(1.2, block["font_size"] / max_font_size) if max_font_size > 0 else 0.7
                            # 2. 位置权重：越靠上权重越高
                            position_factor = 1.0 - (block["y0"] / (page.rect.height * 0.3))
                            # 3. 匹配完整关键词置信度更高
                            exact_match_factor = 1.2 if keyword == text or keyword_no_space == text_no_space else 1.0 if keyword in text[:len(keyword)] or keyword_no_space in text_no_space[:len(keyword_no_space)] else 0.7
                            toc_keyword_confidence = max(
                                toc_keyword_confidence,
                                font_size_factor * position_factor * exact_match_factor
                            )

            features["has_toc_keywords"] = has_toc_keywords
            features["toc_keyword_confidence"] = toc_keyword_confidence

            # 4. 检测页码模式
            page_number_ratio, page_number_count = self.mineru_adapter.detect_page_number_patterns(lines)
            features["page_number_ratio"] = page_number_ratio
            features["page_number_count"] = page_number_count

            # 5. 检测引导线
            leader_line_ratio, leader_line_count = self.mineru_adapter.detect_dotted_leaders(lines)
            features["has_dotted_leaders"] = leader_line_count > 0
            features["leader_line_ratio"] = leader_line_ratio

            # 6. 计算缩进一致性
            indentation_consistency = self.mineru_adapter.calculate_indentation_consistency(text_blocks)
            features["indentation_consistency"] = indentation_consistency

            # 7. 结构特征
            features["line_count"] = len(lines)
            features["avg_line_length"] = sum(len(line) for line in lines) / len(lines) if lines else 0

            # 8. 图片占比（重用已有方法，需要单独计算当前页）
            # 先将单页转换为bytes
            pdf_bytes = doc.write()
            features["image_coverage_ratio"] = self.mineru_adapter.get_image_coverage_ratio(pdf_bytes, [page_index])

            # 9. 新增：计算数字占比和缩进方差（用于区分表格和目录）
            all_text = "".join([b["text"] for b in text_blocks if b["text"]])
            digit_count = sum(c.isdigit() for c in all_text)
            features["digit_ratio"] = digit_count / len(all_text) if all_text else 0.0

            # 计算所有文本块x0坐标的方差，方差越大说明缩进越不规律（表格特征）
            if len(text_blocks) >= 10:
                x_values = [b["x0"] for b in text_blocks]
                mean_x = sum(x_values) / len(x_values)
                var_x = sum((x - mean_x)**2 for x in x_values) / len(x_values)
                features["indent_variance"] = var_x
            else:
                features["indent_variance"] = 0.0

            return features

        except Exception as e:
            return None
