# Copyright (c) Opendatalab. All rights reserved.
"""
PDF通用工具函数模块
封装PDF处理的通用操作，不依赖业务逻辑
"""
import fitz
from typing import Tuple, Optional
import io

def get_pdf_page_count(pdf_bytes: bytes) -> Optional[int]:
    """
    获取PDF总页数
    :param pdf_bytes: PDF二进制内容
    :return: 页数，失败返回None
    """
    try:
        with fitz.open(stream=io.BytesIO(pdf_bytes), filetype="pdf") as doc:
            return len(doc)
    except Exception:
        return None

def get_pdf_page_size(pdf_bytes: bytes, page_index: int = 0) -> Optional[Tuple[float, float]]:
    """
    获取指定页面的尺寸（宽, 高）
    :param pdf_bytes: PDF二进制内容
    :param page_index: 页面索引，默认0
    :return: (width, height)，失败返回None
    """
    try:
        with fitz.open(stream=pdf_bytes, filetype='pdf') as doc:
            if page_index < 0 or page_index >= len(doc):
                return None
            page = doc.load_page(page_index)
            rect = page.rect
            return (rect.width, rect.height)
    except Exception:
        return None

def get_pdf_metadata(pdf_bytes: bytes) -> dict:
    """
    获取PDF元数据
    :param pdf_bytes: PDF二进制内容
    :return: 元数据字典，包含producer、creator、title等字段
    """
    metadata = {
        "producer": "",
        "creator": "",
        "title": ""
    }
    try:
        with fitz.open(stream=pdf_bytes, filetype='pdf') as doc:
            doc_metadata = doc.metadata
            metadata["producer"] = doc_metadata.get("producer", "").lower()
            metadata["creator"] = doc_metadata.get("creator", "").lower()
            metadata["title"] = doc_metadata.get("title", "").lower()
    except Exception:
        pass
    return metadata

def get_sample_page_indices(total_pages: int, max_sample_pages: int) -> list:
    """
    获取采样页面索引，均匀采样前、中、后页
    :param total_pages: 总页数
    :param max_sample_pages: 最多采样页数
    :return: 采样索引列表，按升序排列
    """
    if total_pages <= 0 or max_sample_pages <= 0:
        return []
    if total_pages <= max_sample_pages:
        return list(range(total_pages))
    if max_sample_pages == 1:
        return [0]

    indices = []
    step = (total_pages - 1) / (max_sample_pages - 1)
    for i in range(max_sample_pages):
        idx = round(i * step)
        idx = max(0, min(total_pages - 1, idx))
        if idx not in indices:
            indices.append(idx)
    # 不足的话补全
    if len(indices) < max_sample_pages:
        for idx in range(total_pages):
            if idx not in indices:
                indices.append(idx)
                if len(indices) == max_sample_pages:
                    break
    return sorted(indices)
