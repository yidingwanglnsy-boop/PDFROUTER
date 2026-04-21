# Copyright (c) Opendatalab. All rights reserved.
"""
PDF特征提取适配层
基于pymupdf实现，不需要依赖MinerU，纯CPU运行
封装所有PDF特征提取底层调用，隔离上层业务逻辑和底层依赖变化
"""
import fitz  # pymupdf
import re
from typing import Optional, Tuple, List, Dict
import io
from pdf_router.constants import PAGE_NUMBER_PATTERNS, LEADER_LINE_PATTERN


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

    @staticmethod
    def extract_text_with_positions(page: fitz.Page) -> List[Dict]:
        """
        提取页面文本及其位置和字体信息
        :param page: pymupdf页面对象
        :return: 文本块列表，每个块包含text, x0, y0, x1, y1, font_size
        """
        try:
            blocks = page.get_text("dict")["blocks"]
            text_blocks = []
            for block in blocks:
                if block["type"] == 0:  # 文本块
                    for line in block["lines"]:
                        for span in line["spans"]:
                            text_blocks.append({
                                "text": span["text"].strip(),
                                "x0": span["bbox"][0],
                                "y0": span["bbox"][1],
                                "x1": span["bbox"][2],
                                "y1": span["bbox"][3],
                                "font_size": span["size"]
                            })
            return text_blocks
        except Exception:
            return []

    @staticmethod
    def detect_page_number_patterns(lines: List[str]) -> Tuple[float, int]:
        """
        检测行末尾的页码模式，支持跨行页码（标题在上一行，页码在下一行）
        :param lines: 文本行列表
        :return: (页码行占比, 页码行数量)
        """
        if not lines:
            return 0.0, 0

        # 预编译正则表达式
        patterns = [re.compile(p) for p in PAGE_NUMBER_PATTERNS]
        page_number_lines = 0
        # 新增：统计跨行页码对
        cross_line_page_pairs = 0

        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            # 情况1：当前行末尾本身就是页码（常规模式）
            is_page_line = False
            for pattern in patterns:
                if pattern.search(line):
                    page_number_lines += 1
                    is_page_line = True
                    break

            # 情况2：跨行模式：当前行是短标题（<30字符），下一行是纯数字页码
            if not is_page_line and i < len(lines)-1 and len(line) < 30 and line:
                next_line = lines[i+1].strip()
                if next_line and next_line.isdigit() and len(next_line) <= 3:
                    # 标题 + 独立页码行，计数
                    cross_line_page_pairs += 1

        # 跨行模式的页码对权重和常规行一样
        total_page_indicators = page_number_lines + cross_line_page_pairs
        ratio = total_page_indicators / len(lines) if lines else 0.0
        return ratio, total_page_indicators

    @staticmethod
    def detect_dotted_leaders(lines: List[str]) -> Tuple[float, int]:
        """
        检测目录引导线模式
        :param lines: 文本行列表
        :return: (引导线行占比, 引导线行数量)
        """
        if not lines:
            return 0.0, 0

        pattern = re.compile(LEADER_LINE_PATTERN)
        leader_lines = 0

        for line in lines:
            if pattern.search(line):
                leader_lines += 1

        ratio = leader_lines / len(lines) if lines else 0.0
        return ratio, leader_lines

    @staticmethod
    def calculate_indentation_consistency(blocks: List[Dict]) -> float:
        """
        计算行缩进的一致性
        :param blocks: 带位置信息的文本块列表
        :return: 一致性分数（0~1），越高表示缩进越一致
        """
        if len(blocks) < 5:
            return 0.0

        # 收集所有文本块的x0坐标（左侧缩进）
        x0_values = [block["x0"] for block in blocks if block["text"].strip()]

        if len(x0_values) < 5:
            return 0.0

        # 按x0值分组，统计每个缩进级别的数量
        from collections import defaultdict
        indent_groups = defaultdict(int)
        for x0 in x0_values:
            # 按10像素精度分组，减少噪声
            rounded_x0 = round(x0, -1)
            indent_groups[rounded_x0] += 1

        # 计算最大组的占比作为一致性分数
        if not indent_groups:
            return 0.0

        max_count = max(indent_groups.values())
        consistency = max_count / len(x0_values)

        return consistency
