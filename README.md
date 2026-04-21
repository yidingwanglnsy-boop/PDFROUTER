# PDF 智能路由算子
<p align="center">
    <img src="https://img.shields.io/badge/Version-2.0.0-brightgreen.svg">
    <img src="https://img.shields.io/badge/Python-3.8+-blue.svg">
    <img src="https://img.shields.io/badge/License-AGPLv3-orange.svg">
    <img src="https://img.shields.io/badge/CPU%20Only-green.svg">
</p>

## 功能概述
pdf_router是一个**纯CPU运行、零依赖MinerU**的智能PDF路由组件，可直接作为Ray Data Mapper使用，对PDF进行预评估和特征打标，后续根据标记位选择对应场景的SOTA模型处理，大幅提升大规模PDF处理的效率和准确率。

底层基于PyMuPDF实现，不需要任何GPU资源，不需要安装复杂的深度学习依赖，开箱即用。

## ✨ 核心特性
✅ **纯CPU运行**：无需GPU/NPU资源，成本极低，可部署在任意节点<br>
✅ **Ray原生适配**：符合Ray Data Mapper接口规范，支持分布式批量处理<br>
✅ **7类PDF识别**：支持纯文本/扫描/混合/CID字体/低质量扫描/复杂布局/PPT转换PDF识别<br>
✅ **高性能**：整文档处理10-100ms/份，单页处理10-50ms/页，对整体流程影响可忽略<br>
✅ **零侵入**：不依赖任何第三方私有API，可独立升级使用<br>
✅ **易扩展**：规则式实现，新增特征和标记非常方便<br>
✅ **完全向后兼容**：v2.0.0版本100%兼容v1.1.0版本接口，升级无需修改代码

## 🎯 v2.0.0 新增功能
### 1. 目录页检测功能（全新功能）
支持智能检测PDF中的目录（TOC）页：
- 多语言支持：中英文目录关键词识别（目录、目次、Contents等）
- 多格式识别：支持文档型目录和PPT转换型目录
- 页码范围约束：默认只关注前6页，减少误报
- 连续页筛选：自动保留最前面的连续目录页
- 支持合并PDF：通过分段锚点机制处理多个子报告的场景

### 2. 单页PDF评估能力（全新功能）
支持输入单页PDF路径或二进制内容，返回：
- 单页完整特征：宽高、宽高比、图片占比、字符数、CID字体检测等
- 智能标记：7种PDF类型标记
- 处理优先级：速度优先/平衡/精度优先/极致精度
- 推荐后端：自动匹配最优解析后端
- 定制化处理建议：根据页面特征给出具体的处理方案建议

### 3. 代码架构优化
- 模块化拆分：按职责拆分为配置、特征提取、规则引擎、标记生成、适配层等模块
- 可扩展性大幅提升：新增识别规则、标记类型无需修改核心流程
- 可维护性提升：代码结构清晰，分层明确，便于二次开发
- 依赖简化：移除对MinerU的依赖，仅需要PyMuPDF即可运行

## 🚀 快速开始
### 安装依赖
```bash
# 核心安装（仅需要PyMuPDF，纯CPU，推荐）
pip install pdf-router

# 或者源码安装（开发者使用）
git clone https://github.com/opendatalab/pdf-router.git
cd pdf-router
pip install -e .

# 如需使用Ray分布式能力，额外安装Ray
pip install ray
```

### 基础使用（原有整文档评估，完全兼容）
```python
from pdf_router import PdfRouter

# 初始化路由算子
router = PdfRouter()

# 处理单个PDF
result = router.route("test.pdf")

# 查看结果
print("PDF特征：", result["features"])
print("标记位：", result["marks"])
print("处理优先级：", result["process_priority"])
print("推荐后端：", result["recommended_backend"])
```

### 新增单页PDF评估使用
```python
from pdf_router import SinglePagePdfRouter

# 初始化单页路由器
router = SinglePagePdfRouter()

# 1. 路径输入方式，评估第0页（第一页）
result = router.evaluate_page("single_page_test.pdf")

# 2. 二进制输入方式，评估第1页
# with open("single_page_test.pdf", "rb") as f:
#     pdf_bytes = f.read()
# result = router.evaluate_page(pdf_bytes, page_index=1)

# 查看结果
print("页面索引：", result["page_index"])
print("输入类型：", result["source_type"])
print("页面特征：", result["features"])
print("标记位：", result["marks"])
print("处理优先级：", result["process_priority"])
print("推荐后端：", result["recommended_backend"])
print("处理建议：", result["processing_suggestions"])
```

### 新增目录页检测使用
```python
from pdf_router.api.toc_api import TocDetector

# 初始化目录检测器
detector = TocDetector()

# 方式1：从路径检测目录页
results = detector.detect_from_path("example.pdf")
for page_result in results:
    if page_result["is_toc_page"]:
        print(f"页码 {page_result['page_index'] + 1} 是目录页，置信度: {page_result['confidence']}")

# 方式2：获取连续目录页标识列表（推荐用于实际应用）
toc_pages = detector.get_continuous_toc_pages_from_path("example.pdf")
# toc_pages 是一个长度等于PDF页数的列表，每个元素为True/False
for i, is_toc in enumerate(toc_pages):
    if is_toc:
        print(f"页码 {i + 1} 是连续目录页")

# 方式3：从二进制内容检测
# with open("example.pdf", "rb") as f:
#     pdf_bytes = f.read()
# toc_pages = detector.get_continuous_toc_pages(pdf_bytes)
```

### Ray分布式批量使用（完全兼容）
```python
import ray
from pdf_router import RayPdfRouterMapper

# 初始化Ray
ray.init(num_cpus=8)

# 创建数据集
pdf_paths = ["/path/to/1.pdf", "/path/to/2.pdf", "/path/to/3.pdf"]
ds = ray.data.from_items([{"pdf_path": path} for path in pdf_paths])

# 应用路由算子
mapped_ds = ds.map_batches(
    RayPdfRouterMapper,
    batch_size=10,
    num_cpus=1,
    concurrency=4
)

# 查看结果
for item in mapped_ds.take_all():
    print(f"文件：{item['pdf_path']}, 标记：{item['marks']}, 推荐后端：{item['recommended_backend']}")
```

### 自定义配置
```python
custom_config = {
    # PDF路由配置
    "scan_pdf_threshold": 0.5,  # 调整扫描版判定阈值
    "ppt_marker_score_threshold": 0.8,  # 调整PPT识别阈值，降低误判率
    "backend_preference": {
        "ppt_converted": "your_custom_ppt_model"  # 自定义PPT类型的推荐后端
    },
    # TOC检测配置
    "max_toc_page_range": 10,  # 调整目录最大页码范围（默认6页）
    "toc_score_threshold": 0.5,  # 调整目录检测置信度阈值（默认0.52）
}

# 整文档路由器
router = PdfRouter(custom_config)

# 单页路由器，共用同一套配置体系
page_router = SinglePagePdfRouter(custom_config)

# 目录检测器，共用同一套配置体系
from pdf_router.api.toc_api import TocDetector
toc_detector = TocDetector(custom_config)
```

## 🏷️ 支持的标记说明
### PDF类型标记
| 标记 | 含义 |
|------|------|
| `text_pdf` | 纯文本PDF |
| `scan_pdf` | 扫描版PDF |
| `mixed_pdf` | 混合PDF（部分扫描部分文本） |
| `cid_font_pdf` | 包含大量CID字体的PDF（解析难度高，普通文本提取会乱码） |
| `low_quality_scan` | 低质量扫描件 |
| `complex_layout` | 复杂布局PDF（多栏、公式、表格多） |
| `ppt_converted` | PPT/演示文稿转换生成的PDF |

### 处理优先级标记
| 标记 | 含义 | 适用场景 |
|------|------|----------|
| `speed_first` | 优先速度 | 纯文本、布局简单的PDF |
| `balance` | 平衡速度和精度 | 普通混合、普通扫描PDF |
| `accuracy_first` | 优先精度 | PPT、复杂布局PDF |
| `extreme_accuracy` | 极致精度要求 | 低质量扫描、CID字体PDF |

### 推荐后端标记
| 标记 | 含义 |
|------|------|
| `pipeline` | 推荐MinerU pipeline后端（CPU/GPU通用，速度最快） |
| `hybrid` | 推荐MinerU hybrid后端（混合引擎，平衡速度和精度） |
| `vlm` | 推荐纯VLM大模型（精度最高，速度最慢，成本最高） |
| `special_form` | 推荐专用表单/票据模型 |
| `handwriting` | 推荐手写识别模型 |
| `ppt_special` | 推荐PPT专用解析模型 |

## 📊 性能指标
| 测试场景 | 平均处理时间 | 内存占用 |
|----------|--------------|----------|
| 10页纯文本PDF（整文档） | ~15ms | <80MB |
| 50页扫描件PDF（整文档） | ~30ms | <100MB |
| 100页PPT转换PDF（整文档） | ~25ms | <90MB |
| 单页PDF评估 | ~10~50ms/页 | <80MB |
| 批量1000个PDF（4进程Ray分布式） | ~12ms/份 | <100MB/进程 |
| **识别准确率** | 扫描件>98%，PPT>95% | - |

## 📁 目录结构
```
pdf-router/
├── pdf_router/                     # 核心包目录
│   ├── __init__.py                  # 对外导出接口
│   ├── constants.py                 # 常量、枚举定义
│   ├── config.py                    # 配置管理
│   ├── core/                        # 核心业务层
│   │   ├── feature_extractor.py     # 特征提取（支持整文档+单页）
│   │   ├── rule_engine.py           # 规则判定引擎
│   │   └── mark_generator.py        # 标记生成（含处理建议）
│   ├── adapters/                    # 适配层
│   │   ├── mineru_adapter.py        # PDF解析库统一适配（基于PyMuPDF）
│   │   └── ray_adapter.py           # Ray分布式适配
│   ├── api/                         # 对外API层
│   │   ├── router_api.py            # 整文档评估API（原有）
│   │   └── single_page_api.py       # 单页评估API（新增）
│   ├── utils/                       # 工具层
│   │   ├── pdf_utils.py             # PDF通用工具
│   │   └── io_utils.py              # IO通用工具
│   └── v1_compat.py                 # v1版本兼容层（原有接口兼容）
├── tests/                           # 测试用例目录
│   ├── test_router.py               # 整文档路由API测试
│   ├── test_single_page.py          # 单页路由功能测试
│   ├── test_config.py               # 配置管理测试
│   ├── test_rule_engine.py          # 规则引擎测试
│   └── test_mark_generator.py       # 标记生成测试
├── example.py                       # 基础使用示例
├── example_batch_processing.py      # 批量处理实际场景示例
├── README.md                        # 本文件
├── DESIGN.md                        # 详细设计文档
├── TEST_GUIDE.md                    # 测试使用指南
├── pyproject.toml                   # 打包配置
└── LICENSE                          # 许可证文件
```

## ❓ 常见问题
### Q1: 运行出现ImportError: cannot import name '***' from 'fitz'错误
A: 这是因为安装了错误的`fitz`包，执行以下命令修复：
```bash
pip uninstall -y fitz
pip install pymupdf
```

### Q2: 单页评估和整文档评估的区别？
A:
- 整文档评估会对文档进行多页采样，给出整个文档的整体评估结果，适合批量分流场景
- 单页评估只对指定页面进行精准评估，给出该页面的专属特征和建议，适合单页粒度处理场景

### Q3: 如何调整识别阈值，减少误判？
A: 初始化时传入自定义配置即可调整：
```python
custom_config = {
    "scan_pdf_threshold": 0.6,  # 提高扫描版判定阈值，减少误判
    "ppt_marker_score_threshold": 0.7,  # 调整PPT识别阈值
}
router = PdfRouter(custom_config)
```

### Q4: 如何新增自定义的PDF类型识别？
A: 参考`DESIGN.md`中的扩展机制设计，只需少量代码即可新增类型支持。

## 📄 许可证
本项目基于AGPLv3许可证开源，详见LICENSE文件。
