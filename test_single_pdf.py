#!/usr/bin/env python3
"""
单独测试单个PDF的目录检测
"""
from pdf_router import TocDetector

detector = TocDetector()
pdf_path = "/home/wyd/daily/work/PDFROUTER/test_pdfs/2025年度手游APP买量数据报告-32页.pdf"

import fitz
# 先测试PDF能不能打开
try:
    doc = fitz.open(pdf_path)
    print(f"✅ PDF打开成功，共 {len(doc)} 页")
    # 手动读取为bytes
    pdf_bytes = doc.write()
    doc.close()
except Exception as e:
    print(f"❌ PDF打开失败：{e}")
    exit()

results = detector.detect_from_bytes(pdf_bytes)
print(f"detect_from_bytes返回结果数量：{len(results)}")
if not results:
    # 调试：直接调用内部逻辑
    from pdf_router.core.feature_extractor import FeatureExtractor
    from pdf_router.core.rule_engine import RuleEngine
    from pdf_router.config import ConfigManager

    config = ConfigManager()
    extractor = FeatureExtractor(config)
    rule = RuleEngine(config)

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page3 = doc.load_page(2)
    features = extractor.extract_toc_features(doc, 2)
    print("\n🔍 第3页提取的特征：")
    for k, v in features.items():
        if isinstance(v, float):
            print(f"  {k}: {v:.2f}")
        else:
            print(f"  {k}: {v}")
    is_toc, score = rule.detect_toc_page(features, page_position=2/len(doc))
    print(f"\n📊 检测结果：is_toc={is_toc}, score={score:.2f}, 阈值={config.get('toc_score_threshold')}")
    exit()

print(f"📄 {pdf_path} 检测结果：")
print("-"*70)
print(f"{'页码':<4} {'是否目录':<6} {'置信度':<8} {'有关键词':<8} {'页码占比':<8}")
print("-"*70)
for res in results:
    page_num = res['page_index'] + 1
    is_toc = "✅" if res['is_toc_page'] else "❌"
    conf = f"{res['confidence']:.2f}"
    has_key = "是" if res['features']['has_toc_keywords'] else "否"
    page_ratio = f"{res['features']['page_number_ratio']:.1%}"
    print(f"{page_num:<4} {is_toc:<6} {conf:<8} {has_key:<8} {page_ratio:<8}")

print("\n" + "-"*70)
toc_pages = [r['page_index']+1 for r in results if r['is_toc_page']]
print(f"🔍 共检测到目录页：{sorted(toc_pages)}")
# 特别输出第3页的所有特征
page3 = [r for r in results if r['page_index'] == 2][0]
print("\n📊 第3页（真正的目录）特征详情：")
for k, v in page3['features'].items():
    if isinstance(v, float):
        print(f"  {k}: {v:.2f}")
    else:
        print(f"  {k}: {v}")
