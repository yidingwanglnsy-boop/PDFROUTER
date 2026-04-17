# Copyright (c) Opendatalab. All rights reserved.
"""
特征提取模块
支持整文档特征提取和单页特征提取两种模式
"""
from typing import Dict, Optional, Union
from ..config import ConfigManager
from ..adapters.mineru_adapter import MinerUAdapter
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
