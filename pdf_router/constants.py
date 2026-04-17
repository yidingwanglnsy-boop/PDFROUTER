# Copyright (c) Opendatalab. All rights reserved.
"""
pdf_router 常量定义模块
所有枚举、固定阈值、默认配置项都在这里定义
"""
from typing import Dict

# ======================================
# PDF 类型标记定义
# ======================================
class PdfTypeMark:
    """PDF类型标记枚举"""
    TEXT_PDF = "text_pdf"                 # 纯文本PDF
    SCAN_PDF = "scan_pdf"                 # 扫描版PDF
    MIXED_PDF = "mixed_pdf"               # 混合PDF（部分扫描部分文本）
    CID_FONT_PDF = "cid_font_pdf"         # 包含大量CID字体的PDF（解析难度高）
    LOW_QUALITY_SCAN = "low_quality_scan" # 低质量扫描件
    COMPLEX_LAYOUT = "complex_layout"     # 复杂布局PDF（多栏、公式、表格多）
    PPT_CONVERTED = "ppt_converted"       # PPT/演示文稿转换生成的PDF

# ======================================
# 处理优先级标记定义
# ======================================
class ProcessPriorityMark:
    """处理优先级标记枚举"""
    SPEED_FIRST = "speed_first"           # 优先速度（纯文本简单布局）
    BALANCE = "balance"                   # 平衡速度和精度（普通混合/扫描）
    ACCURACY_FIRST = "accuracy_first"     # 优先精度（PPT/复杂布局）
    EXTREME_ACCURACY = "extreme_accuracy" # 极致精度要求（低质量/CID字体）

# ======================================
# 推荐后端标记定义
# ======================================
class RecommendedBackendMark:
    """推荐后端标记枚举"""
    PIPELINE = "pipeline"                 # 推荐MinerU pipeline后端（CPU/GPU通用）
    HYBRID = "hybrid"                     # 推荐MinerU hybrid后端（混合引擎）
    VLM = "vlm"                           # 推荐纯VLM模型（大模型高精度）
    SPECIAL_FORM = "special_form"         # 推荐专用表单/票据模型
    HANDWRITING = "handwriting"           # 推荐手写识别模型
    PPT_SPECIAL = "ppt_special"           # 推荐PPT专用解析模型

# ======================================
# 默认配置定义
# ======================================
DEFAULT_CONFIG: Dict = {
    # 分类阈值配置
    "scan_pdf_threshold": 0.3,            # 图片占比超过30%判定为扫描/混合类型
    "text_density_threshold": 100,        # 每页字符低于100判定为低文本密度
    "cid_font_threshold": 0.2,            # CID字体占比超过20%标记为CID字体PDF
    "complex_layout_threshold": 0.4,      # 复杂元素占比超过40%标记为复杂布局

    # PPT转PDF识别阈值
    "ppt_aspect_ratio_min": 1.3,          # PPT页面宽高比最小阈值（16:9≈1.77，4:3≈1.33）
    "ppt_aspect_ratio_max": 1.9,          # PPT页面宽高比最大阈值
    "ppt_image_ratio_threshold": 0.6,     # PPT图片占比阈值（通常PPT图片占比高）
    "ppt_avg_char_threshold": 100,        # PPT平均每页字符数阈值（通常PPT文字少）
    "ppt_marker_score_threshold": 0.5,    # PPT识别分数阈值

    # 功能开关
    "enable_ppt_detection": True,         # 是否启用PPT转PDF识别
    "enable_layout_analysis": True,       # 是否启用布局复杂度分析
    "max_sample_pages": 20,               # 整文档评估最多采样页数，减少CPU消耗

    # 后端适配规则
    "backend_preference": {
        "text_pdf": "pipeline",
        "mixed_pdf": "hybrid",
        "scan_pdf": "hybrid",
        "low_quality_scan": "vlm",
        "complex_layout": "hybrid",
        "cid_font_pdf": "vlm",
        "ppt_converted": "ppt_special"
    }
}

# ======================================
# 版本信息
# ======================================
VERSION = "2.0.0"
