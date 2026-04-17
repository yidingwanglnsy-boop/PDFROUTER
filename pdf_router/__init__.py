# Copyright (c) Opendatalab. All rights reserved.
"""
PDF智能路由器
纯CPU运行的PDF前置分类路由组件，支持7种PDF类型识别、自动推荐最优解析后端

v2.0.0版本新增功能：
1. 支持单页PDF评估
2. 代码模块化重构，提升可维护性和扩展性
"""
from .api.router_api import PdfRouter
from .api.single_page_api import SinglePagePdfRouter
from .adapters.ray_adapter import RayPdfRouterMapper
from .constants import (
    PdfTypeMark,
    ProcessPriorityMark,
    RecommendedBackendMark,
    VERSION
)

__version__ = VERSION
__author__ = "Opendatalab"
__all__ = [
    "PdfRouter",
    "SinglePagePdfRouter",
    "RayPdfRouterMapper",
    "PdfTypeMark",
    "ProcessPriorityMark",
    "RecommendedBackendMark"
]
