# Copyright (c) Opendatalab. All rights reserved.
"""
目录检测API模块
提供独立的目录页检测功能，支持路径和字节两种输入方式
"""
import fitz
import io
from typing import List, Dict, Union, Tuple
from ..config import ConfigManager
from ..core.feature_extractor import FeatureExtractor
from ..core.rule_engine import RuleEngine
from ..utils.io_utils import read_pdf_to_bytes
from ..constants import VERSION


class TocDetector:
    """
    目录页检测器
    不依赖OCR，纯CPU运行，支持中英文目录和PPT格式目录检测
    """
    def __init__(self, config: Union[Dict, ConfigManager] = None):
        """
        初始化目录检测器
        :param config: 配置字典或配置管理器实例
        """
        if isinstance(config, ConfigManager):
            self.config = config
        else:
            self.config = ConfigManager(config or {})

        self.feature_extractor = FeatureExtractor(self.config)
        self.rule_engine = RuleEngine(self.config)

    def detect_from_path(self, pdf_path: str) -> List[Dict]:
        """
        从PDF文件路径检测目录页
        :param pdf_path: PDF文件路径
        :return: 每页的检测结果列表，按页码顺序排列
        """
        pdf_bytes = read_pdf_to_bytes(pdf_path)
        if not pdf_bytes:
            return []

        return self._detect_from_bytes_internal(pdf_bytes)

    def detect_from_bytes(self, pdf_bytes: bytes) -> List[Dict]:
        """
        从PDF二进制内容检测目录页
        :param pdf_bytes: PDF二进制数据
        :return: 每页的检测结果列表，按页码顺序排列
        """
        if not pdf_bytes:
            return []

        return self._detect_from_bytes_internal(pdf_bytes)

    def get_continuous_toc_pages(self, pdf_bytes: bytes) -> List[bool]:
        """
        获取连续的目录页标识列表
        如果检测到的目录页不连续，只返回最前面连续的页号作为目录页

        :param pdf_bytes: PDF二进制数据
        :return: 长度等于PDF页数的列表，每个元素为True/False表示该页是否目录页
        """
        if not pdf_bytes:
            return []

        # 获取检测结果
        detection_results = self._detect_from_bytes_internal(pdf_bytes)
        page_count = len(detection_results)

        # 提取被判定为目录的页面索引
        toc_indices = [r["page_index"] for r in detection_results if r["is_toc_page"]]

        if not toc_indices:
            return [False] * page_count

        # 找出最前面的连续目录页范围
        first_toc = toc_indices[0]
        continuous_end = first_toc

        # 从第一个目录页开始，检查后续页面是否连续都是目录页
        for i in range(first_toc + 1, page_count):
            if detection_results[i]["is_toc_page"]:
                continuous_end = i
            else:
                break

        # 构造结果列表
        result = [False] * page_count
        for i in range(first_toc, continuous_end + 1):
            result[i] = True

        return result

    def get_continuous_toc_pages_from_path(self, pdf_path: str) -> List[bool]:
        """
        从PDF文件路径获取连续的目录页标识列表

        :param pdf_path: PDF文件路径
        :return: 长度等于PDF页数的列表，每个元素为True/False表示该页是否目录页
        """
        pdf_bytes = read_pdf_to_bytes(pdf_path)
        return self.get_continuous_toc_pages(pdf_bytes)

    def _detect_from_bytes_internal(self, pdf_bytes: bytes) -> List[Dict]:
        """
        内部方法：从PDF二进制数据检测目录页
        :param pdf_bytes: PDF二进制数据
        :return: 检测结果列表
        """
        try:
            doc = fitz.open(stream=io.BytesIO(pdf_bytes), filetype="pdf")
            page_count = len(doc)
            results = []

            max_page_range = self.config.get("max_toc_page_range", 6)

            for page_index in range(page_count):
                # 计算页面在文档中的相对位置
                page_position = page_index / page_count if page_count > 0 else 0.0

                # 应用页码范围惩罚：超过配置范围的页面降低置信度
                page_penalty = 1.0
                if page_index + 1 > max_page_range:
                    page_penalty = 0.3

                # 提取目录特征
                toc_features = self.feature_extractor.extract_toc_features(doc, page_index)
                if not toc_features:
                    results.append({
                        "page_index": page_index,
                        "is_toc_page": False,
                        "confidence": 0.0,
                        "toc_type": None,
                        "features": {},
                        "version": VERSION
                    })
                    continue

                # 检测是否为PPT格式（重用已有PPT检测逻辑）
                # 先提取页面基础特征用于PPT检测
                page_features = self.feature_extractor.extract_page_features(pdf_bytes, page_index)
                is_ppt_format = False
                if page_features:
                    is_ppt_format, _ = self.rule_engine.detect_ppt_converted(page_features)

                # 检测是否为目录页
                is_toc_page, confidence = self.rule_engine.detect_toc_page(
                    toc_features,
                    is_ppt_format=is_ppt_format,
                    page_position=page_position
                )

                # 应用页码范围惩罚
                confidence = confidence * page_penalty

                # 构造结果
                result = {
                    "page_index": page_index,
                    "is_toc_page": is_toc_page,
                    "confidence": round(confidence, 4),
                    "toc_type": "ppt" if is_ppt_format and is_toc_page else "document" if is_toc_page else None,
                    "features": {
                        "has_toc_keywords": toc_features.get("has_toc_keywords", False),
                        "toc_keyword_confidence": round(toc_features.get("toc_keyword_confidence", 0.0), 4),
                        "page_number_ratio": round(toc_features.get("page_number_ratio", 0.0), 4),
                        "has_dotted_leaders": toc_features.get("has_dotted_leaders", False),
                        "leader_line_ratio": round(toc_features.get("leader_line_ratio", 0.0), 4),
                        "indentation_consistency": round(toc_features.get("indentation_consistency", 0.0), 4),
                        "line_count": toc_features.get("line_count", 0),
                        "avg_line_length": round(toc_features.get("avg_line_length", 0.0), 2),
                        "image_coverage_ratio": round(toc_features.get("image_coverage_ratio", 0.0), 4)
                    },
                    "version": VERSION
                }

                results.append(result)

            # 新增：分段锚点检测 + 局部位置重评分
            # 识别合并PDF中每个子报告的目录起始页，用局部位置重评分
            results = self._apply_section_aware_rescoring(results)

            # 新增：连续目录页后处理逻辑（基于锚点范围扩展）
            results = self._post_process_continuous_toc(results)

            doc.close()
            return results

        except Exception as e:
            return []

    def _detect_section_anchors(self, results: List[Dict]) -> List[int]:
        """
        识别分段锚点：有强目录关键词的页面
        :return: 锚点页面索引列表
        """
        anchors = []
        for r in results:
            f = r["features"]
            if (f.get("has_toc_keywords", False) and
                    f.get("toc_keyword_confidence", 0) >= 0.4 and
                    f.get("page_number_ratio", 0) >= 0.05):
                anchors.append(r["page_index"])
        return anchors if anchors else [0]

    def _compute_local_positions(self, results: List[Dict], anchors: List[int]) -> List[float]:
        """
        计算每个页面相对于所在分段锚点的局部位置
        :return: 每个页面的局部位置列表（0~1）
        """
        page_count = len(results)
        local_positions = []

        for i in range(page_count):
            # 找到当前页面之前最近的锚点
            anchor = 0
            for a in anchors:
                if a <= i:
                    anchor = a
                else:
                    break

            # 找到所在分段的长度（到下一个锚点的距离）
            next_anchor = page_count
            for a in anchors:
                if a > i:
                    next_anchor = a
                    break

            section_length = next_anchor - anchor
            if section_length <= 0:
                section_length = 1

            local_pos = (i - anchor) / section_length
            local_positions.append(local_pos)

        return local_positions

    def _apply_section_aware_rescoring(self, results: List[Dict]) -> List[Dict]:
        """
        分段锚点检测 + 局部位置重评分
        对于合并PDF，识别每个子报告的起始页（有强目录关键词），
        然后用局部位置（相对于锚点的距离）对接近阈值的页面重新评分
        """
        if not results:
            return results

        anchors = self._detect_section_anchors(results)

        # 如果只有一个锚点（或默认锚点），说明是单一文档，不需要重评分
        if len(anchors) <= 1:
            return results

        local_positions = self._compute_local_positions(results, anchors)

        # 对未判定为目录但接近阈值的页面，用局部位置重新评分
        threshold = self.config.get("toc_score_threshold", 0.52)
        page_count = len(results)
        features_list = [r["features"] for r in results]

        for i in range(page_count):
            result = results[i]
            local_pos = local_positions[i]

            # 只对接近阈值且未判定为目录的页面重评分
            if not result["is_toc_page"] and result["confidence"] >= threshold * 0.85:
                # 用局部位置重新调用规则引擎
                is_toc_page, new_score = self.rule_engine.detect_toc_page(
                    features_list[i],
                    is_ppt_format=result.get("toc_type") == "ppt",
                    page_position=local_pos
                )
                if is_toc_page:
                    result["is_toc_page"] = True
                    result["confidence"] = max(result["confidence"], round(new_score, 4))

        return results

    def _post_process_continuous_toc(self, results: List[Dict]) -> List[Dict]:
        """
        后处理：识别连续的目录页，提高召回率
        规则：
        1. 找到所有已经被判定为目录的页面作为种子页
        2. 检查种子页前后各2页的范围，如果得分>=阈值*0.7，且具有目录特征，也判定为目录
           （适配多页目录只有第一页有关键词的情况）
        """
        if not results:
            return results

        threshold = self.config.get("toc_score_threshold", 0.6)
        low_threshold = threshold * 0.7  # 连续页阈值更宽松
        page_count = len(results)

        # 第一步：找出所有种子目录页和高得分候选页
        is_toc = [r["is_toc_page"] for r in results]
        scores = [r["confidence"] for r in results]
        features = [r["features"] for r in results]

        # 第二步：扩展连续目录页
        for i in range(page_count):
            if is_toc[i]:
                # 向前扩展最多2页
                start = max(0, i - 2)
                for j in range(start, i):
                    if scores[j] >= low_threshold:
                        if (features[j].get("page_number_ratio", 0) >= 0.2 or
                            features[j].get("leader_line_ratio", 0) >= 0.15):
                            is_toc[j] = True
                            scores[j] = max(scores[j], threshold * 0.85)
                # 向后扩展最多2页
                end = min(page_count - 1, i + 2)
                for j in range(i + 1, end + 1):
                    if scores[j] >= low_threshold:
                        if (features[j].get("page_number_ratio", 0) >= 0.2 or
                            features[j].get("leader_line_ratio", 0) >= 0.15):
                            is_toc[j] = True
                            scores[j] = max(scores[j], threshold * 0.85)

        # 更新结果
        for i in range(page_count):
            results[i]["is_toc_page"] = is_toc[i]
            results[i]["confidence"] = round(scores[i], 4)
            if is_toc[i] and not results[i]["toc_type"]:
                results[i]["toc_type"] = "document"

        return results
