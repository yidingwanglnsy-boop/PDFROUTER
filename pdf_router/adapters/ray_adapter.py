# Copyright (c) Opendatalab. All rights reserved.
"""
Ray分布式适配层
实现Ray Data Mapper接口，支持分布式批量处理PDF
完全兼容原有RayPdfRouterMapper接口
"""
from typing import Dict, List, Any
from ..api.router_api import PdfRouter

class RayPdfRouterMapper:
    """
    Ray Data Mapper 算子
    符合Ray Data map_batches接口规范，支持分布式批量处理
    完全兼容v1.1.0版本接口
    """
    def __init__(self, config: Dict = None):
        """
        初始化算子，Ray会在每个Worker上实例化一次
        :param config: 自定义配置
        """
        self.router = PdfRouter(config)

    def __call__(self, batch: Dict[str, List[Any]]) -> Dict[str, List[Any]]:
        """
        处理一批数据，每个Worker并行执行
        :param batch: 输入批量数据，格式：{"pdf_path": [path1, path2, ...], 其他字段...}
        :return: 新增字段后的批量数据，新增字段：
            - features: 特征列表
            - marks: 标记列表
            - process_priority: 优先级列表
            - recommended_backend: 推荐后端列表
        """
        features_list = []
        marks_list = []
        priority_list = []
        backend_list = []

        for pdf_path in batch["pdf_path"]:
            try:
                result = self.router.route(pdf_path)
                features_list.append(result["features"])
                marks_list.append(result["marks"])
                priority_list.append(result["process_priority"])
                backend_list.append(result["recommended_backend"])
            except Exception as e:
                # 错误降级处理，单个文件失败不影响整个批次
                features_list.append({"error": str(e)})
                marks_list.append(["error"])
                priority_list.append("balance")
                backend_list.append("pipeline")

        # 追加到原batch返回，保留原有字段
        batch["features"] = features_list
        batch["marks"] = marks_list
        batch["process_priority"] = priority_list
        batch["recommended_backend"] = backend_list
        return batch
