#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
恒生科技 ETF 分析
"""

import requests
import sys
sys.path.insert(0, '/home/admin/.openclaw/workspace/skills/stock-analyzer-pro')

from scripts.utils.formatter import ReportFormatter
from scripts.analysis.value_investing import ValueInvestingAnalyzer
from scripts.analysis.risk import RiskAnalyzer

# 获取 ETF 数据
url = "http://qt.gtimg.cn/q=sh513180"
resp = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
text = resp.text
start = text.find('"') + 1
end = text.rfind('"')
content = text[start:end]
parts = content.split('~')

# 解析数据
quote_data = {
    'code': '513180',
    'name': parts[1] if len(parts) > 1 else '恒生科技 ETF',
    'price': float(parts[3]) if len(parts) > 3 and parts[3] else 0,
    'change': float(parts[31]) if len(parts) > 31 and parts[31] else 0,
    'change_percent': float(parts[32]) if len(parts) > 32 and parts[32] else 0,
    'open': float(parts[5]) if len(parts) > 5 and parts[5] else 0,
    'high': float(parts[6]) if len(parts) > 6 and parts[6] else 0,
    'low': float(parts[7]) if len(parts) > 7 and parts[7] else 0,
    'pre_close': float(parts[4]) if len(parts) > 4 and parts[4] else 0,
    'volume': float(parts[8]) if len(parts) > 8 and parts[8] else 0,
    'amount': float(parts[37]) if len(parts) > 37 and parts[37] else 0,
    'market_cap': None,  # ETF 无市值
    'pe_ttm': None,  # ETF 无 PE
    'pb': float(parts[65]) if len(parts) > 65 and parts[65] else None,  # ETF 净值比
    'high_52w': float(parts[49]) if len(parts) > 49 and parts[49] else 0,  # 修正
    'low_52w': float(parts[48]) if len(parts) > 48 and parts[48] else 0,
    'source': 'tencent'
}

print("=== 恒生科技 ETF (513180) 数据 ===")
print(f"名称：{quote_data['name']}")
print(f"当前价：¥{quote_data['price']:.3f}")
print(f"涨跌幅：{quote_data['change_percent']:+.2f}%")
print(f"52 周范围：¥{quote_data['low_52w']:.3f} - ¥{quote_data['high_52w']:.3f}")
print(f"PB: {quote_data['pb']}")

# 价值投资分析
financial_data = None  # ETF 无财务数据
value_analysis = ValueInvestingAnalyzer.analyze(quote_data, financial_data)
risk_analysis = RiskAnalyzer.analyze(quote_data['code'], quote_data)

print("\n=== 价值投资分析 ===")
print(f"内在价值：¥{value_analysis.get('intrinsic_value', {}).get('comprehensive', 0):.3f}")
print(f"安全边际：{value_analysis.get('margin_of_safety', {}).get('percentage', 0):.1f}%")
print(f"估值水平：{value_analysis.get('valuation_level', {}).get('level', 'N/A')}")
print(f"价值投资评分：{value_analysis.get('value_score', 0)}/100")
print(f"投资建议：{value_analysis.get('recommendation', {}).get('action', 'N/A')}")
