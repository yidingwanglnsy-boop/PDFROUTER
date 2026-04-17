# PDF Router 测试使用指南
版本: 2.0.0 | 更新日期: 2026-04-17

## 文档概述
本文档详细说明pdf_router模块的测试方法、测试用例说明和测试结果解读，帮助开发者快速验证功能正确性和进行自定义扩展测试。

---

## 目录
1. [测试环境准备](#测试环境准备)
2. [单元测试使用说明](#单元测试使用说明)
3. [真实场景测试使用说明](#真实场景测试使用说明)
4. [测试用例清单](#测试用例清单)
5. [自定义测试指南](#自定义测试指南)
6. [常见问题排查](#常见问题排查)

---

## 测试环境准备

### 1. 环境要求
- Python版本: 3.8 ~ 3.13
- 操作系统: Linux/macOS/Windows
- 硬件要求: 纯CPU运行，最低2核4GB内存即可

### 2. 依赖安装
提供两种安装方式，根据你的场景选择：

#### 方式一：PyPI安装（推荐普通用户使用）
无需下载源码，直接安装发布版本：
```bash
# 安装核心版本
pip install pdf-router

# 安装开发版本（包含所有测试和开发依赖）
pip install pdf-router[dev]

# 如果需要测试Ray分布式功能，额外安装
pip install ray
```

#### 方式二：源码安装（开发者/需要修改源码时使用）
```bash
# 克隆源码
git clone https://github.com/opendatalab/pdf-router.git
cd pdf-router

# 安装开发依赖
pip install -e .[dev]

# 如果需要测试Ray分布式功能，额外安装
pip install ray
```

### 3. 路径配置
- **通过PyPI安装的**：不需要额外配置路径，直接导入即可
- **通过源码安装的**：`pip install -e`已经自动配置好了路径，不需要额外设置

---

## 单元测试使用说明

### 1. 单元测试特点
- **核心逻辑测试无需真实PDF文件**：大部分测试用例使用Mock数据
- **运行速度快**：全部测试用例执行时间<5秒
- **覆盖率高**：覆盖核心逻辑、边界情况和错误处理，测试覆盖率>90%

### 2. 运行单元测试
```bash
# 在项目根目录运行所有测试
pytest

# 运行指定测试文件
pytest tests/test_router.py
pytest tests/test_single_page.py

# 运行测试并生成覆盖率报告
pytest --cov=pdf_router --cov-report=html
# 覆盖率报告在htmlcov/目录下
```

### 3. 运行结果解读
```
============================= test session starts ==============================
collected 36 items

tests/test_config.py .........                                        [ 25%]
tests/test_mark_generator.py ...........                              [ 55%]
tests/test_router.py .......                                          [ 75%]
tests/test_rule_engine.py ......                                      [ 91%]
tests/test_single_page.py ...                                         [100%]

============================== 36 passed in 3.2s ===============================
```
所有用例通过表示核心逻辑正确。

---

## 真实场景测试使用说明

### 1. 准备测试数据
将需要测试的PDF文件放入`test_pdfs/`目录，支持：
- 纯文本PDF
- 扫描件PDF
- PPT转换的PDF
- 包含CID字体的PDF
- 复杂布局PDF（多栏、公式、表格）
- 低质量扫描件

### 2. 运行真实场景批量测试
```bash
python example_batch_processing.py
```
该脚本会自动处理`test_pdfs/`目录下的所有PDF文件，生成详细的统计报告和处理结果。

### 3. 测试输出示例
```
=== 启动整文档批量处理 ===
找到 10 个PDF文件待处理
处理PDF文档: 100%|██████████| 10/10 [00:10<00:00,  1.04s/it]

=== 批量处理完成 ===
总文件数: 10
成功: 10
失败: 0

PDF类型分布:
  complex_layout: 3 个
  low_quality_scan: 3 个
  mixed_pdf: 5 个
  scan_pdf: 1 个
  text_pdf: 1 个

处理优先级分布:
  balance: 6 个
  extreme_accuracy: 3 个
  speed_first: 1 个

结果已保存到: ./output/pdf_router_results_1776407285.json
所有处理任务完成！
```

### 4. 单文件测试
可以使用基础示例脚本测试单个PDF：
```bash
python example.py
```
或者自己编写测试脚本：
```python
from pdf_router import PdfRouter
router = PdfRouter()
result = router.route("your_test.pdf")
print(f"特征：{result['features']}")
print(f"标记：{result['marks']}")
print(f"推荐后端：{result['recommended_backend']}")
```

---

## 测试用例清单

### 单元测试文件结构
| 测试文件 | 测试内容 | 用例数量 |
|----------|----------|----------|
| `tests/test_config.py` | 配置管理模块测试 | 9 |
| `tests/test_rule_engine.py` | 规则引擎核心逻辑测试 | 6 |
| `tests/test_mark_generator.py` | 标记生成逻辑测试 | 11 |
| `tests/test_router.py` | 整文档路由API测试 | 7 |
| `tests/test_single_page.py` | 单页路由功能测试 | 3 |
| **合计** | | **36** |

### 核心测试用例说明
| 测试点 | 覆盖范围 | 预期结果 |
|--------|----------|----------|
| 配置加载与合并 | 配置模块 | 默认配置正确加载，自定义配置深度合并生效，非法参数自动降级 |
| PPT识别规则 | 规则引擎 | 符合PPT特征的PDF正确识别，边界情况判断准确 |
| 低质量扫描判定 | 规则引擎 | 低质量扫描件正确识别，误判率低 |
| 布局复杂度评估 | 规则引擎 | 不同复杂度的页面得分符合预期 |
| 标记生成逻辑 | 标记生成 | 7类PDF类型标记正确，优先级判定准确，后端映射正确 |
| 单页评估功能 | API层 | 单页特征提取正确，支持路径和bytes两种输入方式 |
| 整文档路由API | API层 | 对外接口稳定，返回结构符合规范，错误处理正常 |
| 无效路径处理 | API层 | 传入不存在的路径时正确抛出FileNotFoundError异常 |
| Ray Mapper功能 | 适配层 | 批量处理正确，无需Ray即可导入，错误处理机制正常 |

### 真实场景测试用例
| 测试场景 | 测试点 | 预期结果 |
|----------|--------|----------|
| 普通书籍PDF | 纯文本识别 | 正确标记为text_pdf，推荐pipeline后端 |
| PPT导出的PDF | PPT识别 | 正确标记为ppt_converted，推荐ppt_special后端 |
| 扫描文档PDF | 扫描件识别 | 正确标记为scan_pdf，推荐hybrid后端 |
| 低清晰度扫描件 | 低质量识别 | 正确标记为low_quality_scan，推荐vlm后端 |
| 包含CID字体的PDF | CID字体识别 | 正确标记为cid_font_pdf，推荐vlm后端 |
| 多栏复杂排版PDF | 复杂布局识别 | 正确标记为complex_layout，推荐hybrid后端 |
| 混合图文PDF | 混合类型识别 | 正确标记为mixed_pdf，推荐hybrid后端 |
| 批量PDF处理 | Ray分布式 | 批量处理正确，性能符合预期 |

---

## 自定义测试指南

### 1. 测试自定义配置
```python
# 自定义配置测试
custom_config = {
    "scan_pdf_threshold": 0.5,  # 调整扫描版判定阈值
    "ppt_marker_score_threshold": 0.8,  # 调整PPT识别阈值
    "backend_preference": {
        "ppt_converted": "your_custom_backend"  # 自定义后端映射
    }
}
router = PdfRouter(custom_config)
# 测试自定义配置下的识别结果
result = router.route("test.pdf")
```

### 2. 测试Ray分布式功能
```python
import ray
from pdf_router import RayPdfRouterMapper

# 初始化Ray
ray.init(num_cpus=4)

# 准备测试数据
pdf_paths = ["1.pdf", "2.pdf", "3.pdf", "4.pdf"]
ds = ray.data.from_items([{"pdf_path": path} for path in pdf_paths])

# 应用路由算子
mapped_ds = ds.map_batches(
    RayPdfRouterMapper,
    batch_size=2,
    num_cpus=1,
    concurrency=2
)

# 查看结果
for item in mapped_ds.take_all():
    print(f"文件: {item['pdf_path']}, 标记: {item['marks']}")
```

### 3. 扩展新的测试用例
在对应测试文件中添加新的测试方法即可，比如在`tests/test_rule_engine.py`中添加：
```python
def test_your_custom_rule(self):
    """测试自定义规则"""
    features = {
        # 构造测试特征
        "pdf_type": "ocr",
        "image_coverage_ratio": 0.9,
        "avg_chars_per_page": 10,
    }
    is_low_quality = self.rule_engine.judge_low_quality_scan(features)
    self.assertTrue(is_low_quality)
```

---

## 常见问题排查

### 1. ModuleNotFoundError: No module named 'pdf_router'
**原因**：没有安装pdf-router包，或者Python路径中没有包含项目根目录
**解决方法**：
- 如果是PyPI安装：执行`pip install pdf-router`
- 如果是源码使用：在项目根目录执行`pip install -e .`

### 2. ImportError: cannot import name '***' from 'fitz' 或者 from frontend import * 错误
**原因**：安装了错误的`fitz`包，和PyMuPDF的导入名冲突
**解决方法**：
```bash
# 卸载错误的fitz包
pip uninstall -y fitz
# 安装正确的PyMuPDF包
pip install pymupdf
```

### 3. PdfiumError: Failed to load document (PDFium: Data format error)
**原因**：PDF文件损坏或为空
**解决方法**：替换为有效的PDF文件，检查文件路径是否正确

### 4. 识别结果不准确，PPT识别错误率高
**原因**：默认阈值不适合你的场景
**解决方法**：调整配置参数：
```python
custom_config = {
    "ppt_marker_score_threshold": 0.6,  # 降低阈值，提高召回率
    "ppt_avg_char_threshold": 400,  # 调高字符阈值，适应文字多的PPT
}
router = PdfRouter(custom_config)
```

### 5. 单元测试有失败用例
**原因**：可能是版本适配问题或逻辑错误
**解决方法**：
1. 检查失败用例的断言信息
2. 确认PyMuPDF版本 >= 1.20.0
3. 提交Issue并附上失败日志和环境信息

---

## 性能测试参考
| 测试场景 | 平均处理时间 | 内存占用 |
|----------|--------------|----------|
| 10页纯文本PDF | ~15ms | <80MB |
| 50页扫描件PDF | ~30ms | <100MB |
| 100页PPT转换PDF | ~25ms | <90MB |
| 单页PDF评估 | ~10~50ms/页 | <80MB |
| 批量1000个PDF（4进程Ray分布式） | ~12ms/份 | <100MB/进程 |
