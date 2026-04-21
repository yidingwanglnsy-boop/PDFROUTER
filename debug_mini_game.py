#!/usr/bin/env python3
"""
调试小游戏买量报告的目录检测问题
"""
import fitz
from pdf_router.core.feature_extractor import FeatureExtractor
from pdf_router.core.rule_engine import RuleEngine
from pdf_router.config import ConfigManager

pdf_path = "/home/wyd/daily/work/PDFROUTER/test_pdfs/2025年度小游戏买量数据报告-40页.pdf"

config = ConfigManager()
extractor = FeatureExtractor(config)
rule = RuleEngine(config)

doc = fitz.open(pdf_path)
print(f"PDF共 {len(doc)} 页")

# 提取第三页（索引2）的特征
page_index = 2
features = extractor.extract_toc_features(doc, page_index)
print(f"\n🔍 第3页特征：")
for k, v in features.items():
    if isinstance(v, float):
        print(f"  {k}: {v:.2f}")
    else:
        print(f"  {k}: {v}")

# 查看页面文本内容
page = doc.load_page(page_index)
text = page.get_text()
print(f"\n📝 页面内容预览：\n{text[:500]}")

# 检测结果
page_position = page_index / len(doc)
is_toc, score = rule.detect_toc_page(features, page_position=page_position)
print(f"\n📊 检测结果：")
print(f"  是否目录：{is_toc}")
print(f"  得分：{score:.2f}")
print(f"  阈值：{config.get('toc_score_threshold')}")
print(f"  页面位置：{page_position:.1%}（前30%限制：{config.get('max_toc_page_position')*100}%）")

doc.close()
