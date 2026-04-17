# Copyright (c) Opendatalab. All rights reserved.
"""
PDF特征提取适配层
基于pymupdf实现，不需要依赖MinerU，纯CPU运行
封装所有PDF特征提取底层调用，隔离上层业务逻辑和底层依赖变化
"""
import fitz  # pymupdf
from typing import Optional, Tuple, List
import io


class MinerUAdapter:
    """PDF特征提取适配器 - 基于pymupdf实现"""
    @staticmethod
    def classify_pdf_type(pdf_bytes: bytes) -> str:
        """
        分类PDF类型
        :param pdf_bytes: PDF二进制内容
        :return: "text" 或 "ocr"
        """
        try:
            doc = fitz.open(stream=io.BytesIO(pdf_bytes), filetype="pdf")
            total_chars = 0
            # 采样前3页判断
            sample_pages = min(3, len(doc))
            for page_idx in range(sample_pages):
                page = doc.load_page(page_idx)
                text = page.get_text()
                total_chars += len(text.strip())
            doc.close()
            # 平均每页字符少于50判断为扫描件类型
            return "ocr" if total_chars / sample_pages < 50 else "text"
        except Exception:
            # 分类失败默认返回text，降级处理
            return "text"

    @staticmethod
    def get_image_coverage_ratio(pdf_bytes: bytes, page_indices: List[int]) -> float:
        """
        获取指定页面的平均图片占比
        :param pdf_bytes: PDF二进制内容
        :param page_indices: 要计算的页面索引列表
        :return: 图片占比（0~1）
        """
        try:
            doc = fitz.open(stream=io.BytesIO(pdf_bytes), filetype="pdf")
            total_ratio = 0.0
            valid_pages = 0

            for page_idx in page_indices:
                if page_idx >= len(doc):
                    continue
                page = doc.load_page(page_idx)
                page_area = page.rect.width * page.rect.height
                if page_area <= 0:
                    continue

                # 计算所有图片的总面积
                images = page.get_images(full=True)
                img_total_area = 0.0
                for img in images:
                    xref = img[0]
                    pix = fitz.Pixmap(doc, xref)
                    img_area = pix.width * pix.height
                    img_total_area += img_area
                    if pix.n >= 5:  # CMYK
                        pix = fitz.Pixmap(fitz.csRGB, pix)
                    pix = None

                ratio = min(1.0, img_total_area / page_area)
                total_ratio += ratio
                valid_pages += 1

            doc.close()
            return total_ratio / valid_pages if valid_pages > 0 else 0.0
        except Exception as e:
            return 0.0

    @staticmethod
    def get_avg_char_count(pdf_bytes: bytes, page_indices: List[int]) -> int:
        """
        获取指定页面的平均字符数
        :param pdf_bytes: PDF二进制内容
        :param page_indices: 要计算的页面索引列表
        :return: 平均每页字符数
        """
        try:
            doc = fitz.open(stream=io.BytesIO(pdf_bytes), filetype="pdf")
            total_chars = 0
            valid_pages = 0

            for page_idx in page_indices:
                if page_idx >= len(doc):
                    continue
                page = doc.load_page(page_idx)
                text = page.get_text()
                total_chars += len(text.strip())
                valid_pages += 1

            doc.close()
            return int(total_chars / valid_pages) if valid_pages > 0 else 0
        except Exception:
            return 0

    @staticmethod
    def has_cid_font(pdf_bytes: bytes, page_indices: List[int]) -> bool:
        """
        检测PDF是否包含CID字体（无Unicode映射的字体）
        :param pdf_bytes: PDF二进制内容
        :param page_indices: 要检测的页面索引列表
        :return: 是否包含CID字体
        """
        try:
            doc = fitz.open(stream=io.BytesIO(pdf_bytes), filetype="pdf")
            # 检测所有字体
            for page_idx in page_indices:
                if page_idx >= len(doc):
                    continue
                page = doc.load_page(page_idx)
                fonts = page.get_fonts()
                for font in fonts:
                    font_name = font[3].lower()
                    # CID字体特征
                    if "cid" in font_name or "identity" in font_name or "unicode" in font_name:
                        doc.close()
                        return True
            doc.close()
            return False
        except Exception:
            return False
