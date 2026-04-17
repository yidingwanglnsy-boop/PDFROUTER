# Copyright (c) Opendatalab. All rights reserved.
"""
⚠️  兼容层文件，v2.0.0版本已将所有逻辑拆分到其他模块
本文件仅用于保持向下兼容，新代码请直接从顶层导入对应类：
from pdf_router import PdfRouter, SinglePagePdfRouter, RayPdfRouterMapper
"""
import warnings
from .api.router_api import PdfRouter as NewPdfRouter
from .adapters.ray_adapter import RayPdfRouterMapper as NewRayPdfRouterMapper
from .constants import (
    PdfTypeMark,
    ProcessPriorityMark,
    RecommendedBackendMark,
    VERSION
)

# 发出弃用警告，引导用户使用新的导入方式
warnings.warn(
    "pdf_router.py已被拆分到多个模块，v2.1.0版本将不再支持从本文件导入类，"
    "请改为从pdf_router顶层导入：from pdf_router import PdfRouter, RayPdfRouterMapper",
    DeprecationWarning,
    stacklevel=2
)

# 保持原有类名和接口完全兼容，内部委托给新实现
class PdfRouter(NewPdfRouter):
    """兼容旧版本的PdfRouter类，功能与新实现完全一致"""
    pass

class RayPdfRouterMapper(NewRayPdfRouterMapper):
    """兼容旧版本的RayPdfRouterMapper类，功能与新实现完全一致"""
    pass

# 保持原有导出的常量
__all__ = [
    "PdfRouter",
    "RayPdfRouterMapper",
    "PdfTypeMark",
    "ProcessPriorityMark",
    "RecommendedBackendMark"
]

__version__ = VERSION
