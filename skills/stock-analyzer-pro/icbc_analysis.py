#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工商银行 (601398) 深度分析
基于正确数据重新评估
"""

import sys
sys.path.insert(0, '/home/admin/.openclaw/workspace/skills/stock-analyzer-pro')

from scripts.analysis.value_investing import ValueInvestingAnalyzer

# 基于真实数据（修正后）
# 工商银行实际数据参考：
# - 当前价：¥7.11
# - 每股净资产：约¥10.60（根据 PB 0.67 反推）
# - EPS: 约¥1.03（根据 PE 6.91 反推）
# - ROE: 约 8.8%
# - 历史 PE 范围：5-8 倍
# - 历史 PB 范围：0.5-0.9 倍

quote_data = {
    'code': '601398',
    'name': '工商银行',
    'price': 7.11,
    'pe_ttm': 6.91,
    'pb': 0.67,
    'dividend_yield': 0.05,  # 约 5% 股息率
}

financial_data = {
    'indicators': {
        'roe': 8.8,
        'eps': 1.03,
        'bvps': 10.60,
    }
}

# 价值投资分析
value_analysis = ValueInvestingAnalyzer.analyze(quote_data, financial_data)

print("="*80)
print("工商银行 (601398) - 价值投资分析（修正版）")
print("="*80)

print(f"\n【核心数据】")
print(f"当前价：¥{quote_data['price']:.2f}")
print(f"PE: {quote_data['pe_ttm']:.2f} 倍")
print(f"PB: {quote_data['pb']:.2f} 倍")
print(f"ROE: {financial_data['indicators']['roe']:.1f}%")
print(f"股息率：{quote_data['dividend_yield']*100:.1f}%")

print(f"\n【价值投资分析】")
intrinsic_value = value_analysis.get('intrinsic_value', {})
print(f"内在价值估算：")
print(f"  - PE 法：¥{intrinsic_value.get('pe_method', {}).get('mid', 0):.2f}")
print(f"  - PB 法：¥{intrinsic_value.get('pb_method', {}).get('mid', 0):.2f}")
print(f"  - 格雷厄姆公式：¥{intrinsic_value.get('graham_formula', 0):.2f}")
print(f"  - 综合估值：¥{intrinsic_value.get('comprehensive', 0):.2f}")

margin = value_analysis.get('margin_of_safety', {})
print(f"\n安全边际：{margin.get('percentage', 0):.1f}% ({margin.get('level', 'N/A')})")

valuation = value_analysis.get('valuation_level', {})
print(f"估值水平：{valuation.get('level', 'N/A')}")
print(f"评估：{valuation.get('comment', 'N/A')}")

zones = value_analysis.get('buy_zone', {})
print(f"\n【买入区间】")
print(f"  - 保守买入：¥{zones.get('conservative', 0):.2f}（5 折）")
print(f"  - 激进买入：¥{zones.get('aggressive', 0):.2f}（7 折）")

zones = value_analysis.get('sell_zone', {})
print(f"\n【卖出区间】")
print(f"  - 开始卖出：¥{zones.get('start', 0):.2f}（1.5 倍）")
print(f"  - 坚决卖出：¥{zones.get('aggressive', 0):.2f}（2 倍）")

rec = value_analysis.get('recommendation', {})
print(f"\n【投资建议】")
print(f"价值投资评分：{value_analysis.get('value_score', 0)}/100")
print(f"建议：{rec.get('action', 'N/A')} {rec.get('icon', '⚪')}")
print(f"策略：{rec.get('strategy', '')}")

print(f"\n【按你的价值投资理念评估】")
print(f"✓ 低估值：PE 6.9 倍，PB 0.67 倍，符合'低买'")
print(f"✓ 高股息：股息率约 5%，提供稳定现金流")
print(f"✓ 安全边际：{margin.get('percentage', 0):.1f}%，{'充足' if margin.get('percentage', 0) > 30 else '一般'}")
print(f"⚠ 成长性：ROE 8.8%，银行业中等水平")
print(f"⚠ 当前位置：需确认是否接近 52 周低点")

print("\n" + "="*80)
