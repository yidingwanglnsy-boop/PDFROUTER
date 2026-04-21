# PDF Router 详细设计文档
<p align="center">
    <img src="https://img.shields.io/badge/Version-2.0.0-brightgreen.svg">
    <img src="https://img.shields.io/badge/Status-Release-green.svg">
</p>

---

## 目录
1. [设计背景](#设计背景)
2. [设计目标](#设计目标)
3. [整体架构设计](#整体架构设计)
4. [核心模块详细设计](#核心模块详细设计)
5. [核心数据结构](#核心数据结构)
6. [关键设计决策](#关键设计决策)
7. [扩展机制设计](#扩展机制设计)
8. [性能优化设计](#性能优化设计)
9. [兼容性设计](#兼容性设计)
10. [部署与集成方案](#部署与集成方案)

---

## 1. 设计背景
### 1.1 痛点问题
在大规模PDF处理场景中，存在以下普遍痛点：
1. **后端选择困难**：不同类型的PDF适合不同的解析后端，比如纯文本PDF用pipeline后端速度最快，扫描件用VLM后端精度最高，PPT用专门优化的模型效果最好，但实际使用中无法提前知道PDF类型
2. **资源浪费严重**：所有PDF都使用高精度VLM后端会导致GPU资源浪费，成本高企；都用CPU后端会导致复杂PDF解析精度不足
3. **调度效率低下**：多GPU集群中无法根据PDF类型分配最合适的计算资源，导致GPU利用率不均衡
4. **侵入性改造难**：现有解析系统改造需要修改大量核心代码，风险高、周期长

### 1.2 版本演进
- v1.0.0：基础版本，支持7类PDF识别和（打标）
- v1.1.0：新增纯CPU支持、Ray Data适配、PPT转PDF识别
- v2.0.0：模块化重构，移除MinerU依赖，基于PyMuPDF纯开源实现，新增单页PDF评估能力和目录页检测功能，架构可扩展性大幅提升

---

## 2. 设计目标
### 2.1 核心目标
✅ **纯CPU运行**：无需GPU/NPU资源，成本极低，可在任何节点部署<br>
✅ **零依赖设计**：基于PyMuPDF纯开源实现，不依赖任何第三方私有API，可独立升级使用<br>
✅ **高性能**：整文档10-100ms/份，单页10-50ms/份，对整体流程影响可忽略<br>
✅ **高准确率**：扫描件识别准确率>98%，PPT识别准确率>95%<br>
✅ **Ray原生支持**：符合Ray Data Mapper接口规范，支持分布式批量处理<br>
✅ **易扩展**：规则式实现，新增特征和标记无需重构核心逻辑<br>
✅ **完全向后兼容**：v2.0.0版本100%兼容v1.1.0版本接口，无需修改现有代码

### 2.2 功能目标
- 支持7类PDF类型自动识别
- 自动生成处理优先级标记
- 自动推荐最合适的解析后端
- 新增单页PDF评估能力，支持路径和bytes输入
- 新增单页处理建议生成功能
- 支持自定义规则和阈值配置
- 支持批量和分布式处理场景
- 完善的错误处理和降级机制

---

## 3. 整体架构设计
### 3.1 分层架构（v2.0.0）
```
┌─────────────────────────────────────────────────────┐
│                     对外API层                        │
│  整文档评估API(PdfRouter)  │ 单页评估API(SinglePagePdfRouter) │
│  目录检测API(TocDetector)                            │
├─────────────────────────────────────────────────────┤
│                     适配层                          │
│  PDF解析库适配  │ Ray分布式适配  │ 第三方系统适配 │
├─────────────────────────────────────────────────────┤
│                     核心业务层                       │
│  特征提取模块  │ 规则引擎模块  │ 标记生成模块       │
├─────────────────────────────────────────────────────┤
│                     配置管理层                       │
│         默认配置加载  │ 自定义配置合并逻辑          │
├─────────────────────────────────────────────────────┤
│                     工具层                          │
│  PDF处理工具  │ IO操作工具  │ 通用函数库            │
└─────────────────────────────────────────────────────┘
```
#### 架构优势
1. **单一职责**：每层仅负责一类功能，模块间耦合度低
2. **可扩展性强**：新增功能只需在对应层添加，无需修改核心流程
3. **易维护**：代码结构清晰，便于问题定位和二次开发
4. **兼容友好**：适配层隔离底层依赖变化，上层业务无需感知

### 3.2 数据流设计
#### 整文档评估数据流
```
PDF路径输入
    ↓
[特征提取] → 基础信息/元数据/分类特征/PPT特征/布局特征
    ↓
[规则判定] → PPT识别/低质量扫描判定/复杂度评估
    ↓
[标记生成] → 类型标记/优先级标记/推荐后端
    ↓
结构化结果输出
```

#### 单页评估数据流
```
PDF路径/bytes输入
    ↓
[单页特征提取] → 页面基础信息/元数据/分类特征/PPT特征
    ↓
[规则判定] → PPT识别/低质量扫描判定/复杂度评估
    ↓
[标记生成] → 类型标记/优先级标记/推荐后端/定制化处理建议
    ↓
单页评估结果输出
```

#### 目录检测数据流
```
PDF路径/bytes输入
    ↓
[逐页遍历] → 提取每页的TOC特征
    ↓
[页码范围过滤] → 应用页码范围约束（默认前6页）
    ↓
[规则判定] → 关键词检测/页码模式识别/引导线识别/结构分析
    ↓
[连续页筛选] → 保留最前面的连续目录页
    ↓
[分段锚点重评分] → 处理合并PDF中的多个子报告
    ↓
返回每页的目录检测结果
```

---

## 4. 核心模块详细设计
### 4.1 配置管理模块
#### 功能说明
负责默认配置加载、自定义配置合并、配置参数校验
#### 设计要点
- 深度合并默认配置和自定义配置，自定义配置优先级更高
- 内置配置参数校验，非法参数自动降级到默认值并给出警告
- 支持多级配置访问，如`config.get("backend_preference.ppt_converted")`
#### 默认配置清单
```python
{
    # 分类阈值
    "scan_pdf_threshold": 0.3,       # 图片占比超过30%判定为扫描/混合类型
    "text_density_threshold": 100,   # 每页字符低于100判定为低文本密度
    "cid_font_threshold": 0.2,       # CID字体占比超过20%标记为CID字体PDF
    "complex_layout_threshold": 0.4, # 复杂元素占比超过40%标记为复杂布局
    
    # PPT识别阈值
    "ppt_aspect_ratio_min": 1.3,     # PPT页面宽高比最小阈值（16:9≈1.77, 4:3≈1.33）
    "ppt_aspect_ratio_max": 1.9,     # PPT页面宽高比最大阈值
    "ppt_image_ratio_threshold": 0.6, # PPT图片占比阈值（通常PPT图片占比高）
    "ppt_avg_char_threshold": 100,   # PPT平均每页字符数阈值（通常PPT文字少）
    "ppt_marker_score_threshold": 0.5, # PPT识别总分阈值

    # TOC检测配置
    "enable_toc_detection": True,    # 是否启用TOC检测
    "toc_score_threshold": 0.52,    # TOC检测置信度阈值
    "toc_ppt_score_threshold": 0.48,  # PPT类型TOC阈值更低
    "toc_keyword_weight": 0.30,      # 关键词检测权重
    "toc_page_number_weight": 0.30,  # 页码模式权重
    "toc_leader_line_weight": 0.05,  # 引导线权重
    "toc_indentation_weight": 0.05,  # 缩进一致性权重
    "toc_structure_weight": 0.30,   # 结构特征权重
    "toc_context_weight": 0.05,     # 位置权重
    "max_toc_page_position": 1.0,    # 允许目录出现在文档任意位置
    "max_toc_page_range": 6          # 目录最大页码范围（1索引），超过此范围的页面会降低置信度

    # 功能开关
    "enable_ppt_detection": True,    # 是否启用PPT识别
    "enable_layout_analysis": True,  # 是否启用布局复杂度分析
    "max_sample_pages": 20,          # 整文档最多采样页数，减少CPU消耗

    # 后端映射规则
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
```

### 4.2 特征提取模块
#### 功能说明
支持整文档和单页两种模式的特征提取
#### 提取特征清单
| 特征名称 | 类型 | 说明 |
|----------|------|------|
| page_count | int | 文档总页数（整文档模式） |
| page_width | float | 页面宽度 |
| page_height | float | 页面高度 |
| aspect_ratio | float | 页面宽高比 |
| metadata | dict | 文档元数据（producer/creator/title） |
| pdf_type | str | 基础分类："text"（文本）或"ocr"（扫描） |
| image_coverage_ratio | float | 图片占比，0~1 |
| avg_chars_per_page | int | 平均每页字符数（整文档模式） |
| char_count | int | 当前页面字符数（单页模式） |
| has_cid_font | bool | 是否包含无Unicode映射的CID字体 |
| is_ppt_converted | bool | 是否为PPT转换生成 |
| ppt_score | float | PPT识别得分，0~1 |
| layout_complexity | float | 布局复杂度得分，0~1 |
| is_low_quality_scan | bool | 是否为低质量扫描件 |

#### 设计要点
- PDF内容只读取一次，所有特征复用同一份bytes，避免重复IO
- 整文档模式采用均匀采样策略，最多采样20页，兼顾特征代表性和性能
- 单页模式无采样，直接分析目标页面，特征更精准
- 所有特征提取都有降级处理，失败后返回默认值，不中断流程

### 4.3 规则引擎模块
#### 功能说明
实现所有判定规则，完全无状态，支持多线程安全调用
#### 核心规则
1. **PPT识别规则**：多维度加权打分，总分0~1，超过阈值判定为PPT
   - 宽高比匹配：权重30%（PPT通常为16:9或4:3）
   - 元数据匹配：权重40%（producer包含powerpoint/ppt等关键字）
   - 高图片占比匹配：权重15%（PPT通常图片占比高）
   - 低文本密度匹配：权重15%（PPT通常每页文字少）

2. **低质量扫描判定规则**：同时满足以下条件判定为低质量扫描
   - PDF基础分类为"ocr"类型
   - 图片占比>80%
   - 平均字符数<20

3. **布局复杂度评估规则**：得分0~1，得分越高复杂度越高
   - 图片占比：权重40%（图片越多越复杂）
   - 低文本密度：权重30%（字符越少越可能是图片型复杂页面）
   - 包含CID字体：权重30%（CID字体处理难度大）

### 4.4 标记生成模块
#### 功能说明
根据特征和规则结果生成标记、优先级、推荐后端和处理建议
#### 标记优先级
从高到低依次为：
1. PPT_CONVERTED（PPT转换）
2. CID_FONT_PDF（CID字体）
3. LOW_QUALITY_SCAN（低质量扫描）
4. COMPLEX_LAYOUT（复杂布局）
5. 基础类型标记（TEXT_PDF/MIXED_PDF/SCAN_PDF）

#### 处理优先级映射
| 场景 | 优先级 |
|------|--------|
| 纯文本+布局简单 | SPEED_FIRST（速度优先） |
| 低质量扫描/CID字体 | EXTREME_ACCURACY（极致精度） |
| PPT/复杂布局 | ACCURACY_FIRST（精度优先） |
| 其他普通场景 | BALANCE（平衡） |

#### 推荐后端映射
根据PDF类型直接映射配置中的backend_preference，支持用户自定义

#### 处理建议生成（单页专属）
根据页面特征生成定制化建议，比如：
- PPT页面："页面为PPT转换生成，建议使用PPT专用解析模型"
- 低质量扫描："页面为低质量扫描件，建议使用VLM大模型解析"
- CID字体页面："页面包含CID字体，文本提取会乱码，建议使用OCR解析"

### 4.5 适配层模块
#### PDF解析适配器（原MinerU适配器）
统一封装所有对PyMuPDF底层API的调用，隔离上层业务和底层依赖变化，后续如果更换PDF解析库（如pdfium）只需修改这一个文件，上层业务无需任何改动
#### Ray适配器
实现Ray Data Mapper接口，支持分布式批量处理，错误自动降级，单个文件失败不影响整个批次

---

## 5. 核心数据结构
### 5.1 整文档评估返回结构
```python
{
    "pdf_path": "path/to/file.pdf",      # 输入的PDF路径
    "features": { ... },                 # 完整特征字典，见4.2节
    "marks": ["ppt_converted", "complex_layout"],  # 类型标记列表
    "process_priority": "accuracy_first",          # 处理优先级
    "recommended_backend": "ppt_special",          # 推荐后端
    "router_version": "2.0.0"                      # 版本号
}
```

### 5.2 单页评估返回结构
```python
{
    "page_index": 0,                    # 评估的页面索引
    "source_type": "path" or "bytes",   # 输入源类型
    "features": { ... },                # 完整特征字典
    "marks": ["ppt_converted", "complex_layout"],  # 类型标记列表
    "process_priority": "accuracy_first",          # 处理优先级
    "recommended_backend": "ppt_special",          # 推荐后端
    "processing_suggestions": [                     # 定制化处理建议列表
        "页面为PPT转换生成，建议使用PPT专用解析模型",
        "页面图片占比较高，建议启用图片提取功能"
    ],
    "router_version": "2.0.0"                      # 版本号
}
```

---

## 6. 关键设计决策
### 6.1 为什么采用规则式实现而不是模型？
| 考量点 | 规则式 | 模型式 | 选择 |
|--------|--------|--------|------|
| CPU资源消耗 | 极低（10-100ms） | 高（>1s，需要GPU） | ✅ 规则式 |
| 准确率 | 满足业务需求（PPT>95%，扫描件>98%） | 略高5%左右 | ✅ 规则式已满足 |
| 可解释性 | 完全可解释，可调试每个判定逻辑 | 黑盒，无法解释判定原因 | ✅ 规则式 |
| 可扩展性 | 新增规则只需几行代码，不需要训练数据 | 新增类型需要标注大量数据，重新训练 | ✅ 规则式 |
| 部署成本 | 零成本，可在任意节点部署 | 需要GPU资源，部署复杂 | ✅ 规则式 |

### 6.2 为什么设计为纯CPU运行？
- 作为前置路由组件，需要部署在集群所有节点，不能依赖GPU资源
- CPU运行成本仅为GPU的1/10~1/20，适合大规模部署
- 处理速度足够快，对整体链路延迟影响可忽略

### 6.3 为什么新增单页评估功能？
- 很多场景需要单页粒度的处理策略，比如长文档不同页面类型不同，需要不同的处理后端
- 支持bytes输入，可直接对接流式处理场景，无需落地文件
- 单页评估更精准，没有多页采样的误差

### 6.4 为什么移除对MinerU的依赖？
- 降低用户使用成本，不需要安装复杂的深度学习依赖，仅需要PyMuPDF即可运行
- 提高可移植性，可在任意Python环境运行，不需要配置MinerU相关环境
- 减少耦合，项目可以独立升级维护，不受MinerU版本变化影响

### 6.5 为什么保持完全向后兼容？
- 降低用户升级成本，现有系统不需要任何修改即可享受新版本的性能和架构优化
- 平滑过渡，给用户足够的时间迁移到新的API

---

## 7. 扩展机制设计
### 7.1 新增PDF类型识别
```python
# 1. 在constants.py中新增类型标记
class PdfTypeMark:
    YOUR_NEW_TYPE = "your_new_type"

# 2. 在rule_engine.py中新增判定规则
class RuleEngine:
    def detect_your_new_type(self, features: Dict) -> bool:
        # 实现判定逻辑
        return False

# 3. 在mark_generator.py中新增标记生成逻辑
def generate_document_marks(...):
    # 新增优先级判断
    if rule_results.get("is_your_new_type", False):
        marks.append(PdfTypeMark.YOUR_NEW_TYPE)
        pdf_type_mark = PdfTypeMark.YOUR_NEW_TYPE
```

### 7.2 自定义后端映射
```python
custom_config = {
    "backend_preference": {
        "ppt_converted": "your_custom_ppt_backend",
        "your_new_type": "your_custom_backend"
    }
}
router = PdfRouter(custom_config)
```

### 7.3 调整识别阈值
```python
custom_config = {
    "scan_pdf_threshold": 0.4,  # 提高扫描版判定阈值，减少误判
    "ppt_marker_score_threshold": 0.8,  # 提高PPT识别阈值，减少误判
}
router = PdfRouter(custom_config)
```

### 7.4 新增处理建议
在`mark_generator.py`的`_generate_processing_suggestions`方法中新增对应类型的建议逻辑即可

---

## 8. 性能优化设计
### 8.1 计算优化
- 避免冗余IO：PDF内容只读取一次，复用给所有特征提取逻辑
- 提前终止：必要特征提取完成后立即终止计算，不需要分析所有页
- 延迟加载：依赖库仅在需要时导入，减少模块加载时间

### 8.2 内存优化
- 特征提取完成后立即释放PDF文档对象，避免内存占用
- 批量处理时采用流式处理，不缓存全量数据
- 单实例内存占用控制在50-100MB范围内

### 8.3 分布式优化
- Ray Mapper在Worker初始化时创建PdfRouter实例，避免重复初始化开销
- 批量处理大小根据CPU核心数自动优化
- 错误自动降级，不影响整个作业运行

---

## 9. 兼容性设计
### 9.1 依赖兼容
- 仅依赖PyMuPDF >= 1.20.0版本，无其他强制依赖
- 不依赖任何GPU相关组件，纯CPU环境即可运行
- 适配层隔离底层PDF解析库变化，后续更换解析库不影响上层使用

### 9.2 Python版本兼容
- 支持Python 3.8 ~ 3.13所有版本
- Windows/Linux/macOS全平台兼容

### 9.3 版本向后兼容
- v2.0.0版本100%兼容v1.1.0版本所有接口和返回结构
- 原有配置完全兼容，无需修改
- 兼容层会保留至少2个大版本，后续会逐步给出弃用提醒

---

## 10. 部署与集成方案
### 10.1 独立使用部署
```python
# 直接集成到现有Python项目
from pdf_router import PdfRouter, SinglePagePdfRouter

router = PdfRouter()
result = router.route("test.pdf")
# 根据result中的标记选择对应的处理逻辑
if result["recommended_backend"] == "pipeline":
    use_pipeline_backend(result["pdf_path"])
elif result["recommended_backend"] == "vlm":
    use_vlm_backend(result["pdf_path"])
```

### 10.2 Ray分布式部署
```python
import ray
from pdf_router import RayPdfRouterMapper

ray.init()
# 从文件列表创建数据集
pdf_paths = ["1.pdf", "2.pdf", "3.pdf"]
ds = ray.data.from_items([{"pdf_path": p} for p in pdf_paths])
# 分布式处理
ds = ds.map_batches(
    RayPdfRouterMapper,
    batch_size=10,
    num_cpus=1,
    concurrency=10
)
# 根据标记分流到不同的处理队列
for item in ds.iter_rows():
    send_to_queue(item["recommended_backend"], item)
```

### 10.3 作为服务部署
可封装为HTTP服务对外提供API，支持多语言调用，建议使用FastAPI实现：
```python
from fastapi import FastAPI, UploadFile, File
from pdf_router import SinglePagePdfRouter
import tempfile

app = FastAPI()
router = SinglePagePdfRouter()

@app.post("/evaluate/page")
async def evaluate_page(file: UploadFile = File(...)):
    content = await file.read()
    result = router.evaluate_page(content)
    return result
```
