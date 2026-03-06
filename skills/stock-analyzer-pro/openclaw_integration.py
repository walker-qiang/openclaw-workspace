#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stock Analyzer Pro - OpenClaw 集成模块

此模块提供 OpenClaw 工具调用接口，让 AI 可以通过自然语言调用股票分析功能。
"""

import sys
import os
import json
from typing import Dict, Any, Optional

# 添加技能目录到路径
SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SKILL_DIR)

from scripts.main import StockAnalyzerPro

# 缓存分析器实例
_analyzer = None


def get_analyzer() -> StockAnalyzerPro:
    """获取或创建分析器实例"""
    global _analyzer
    if _analyzer is None:
        _analyzer = StockAnalyzerPro()
    return _analyzer


def analyze_stock(code: str, market: str = 'auto') -> Dict[str, Any]:
    """
    分析股票/基金
    
    Args:
        code: 股票代码或名称（如：600519, AAPL, 贵州茅台）
        market: 市场类型 ('auto' | 'cn_stock' | 'us_stock' | 'cn_fund')
        
    Returns:
        包含分析报告的字典
    """
    analyzer = get_analyzer()
    
    # 检测是股票还是基金
    if code.isdigit() and len(code) == 6:
        # 可能是 A 股或基金，先尝试股票
        result = analyzer.analyze_stock(code, market)
        if 'error' not in result:
            return result
        # 如果失败，尝试基金
        return analyzer.analyze_fund(code)
    else:
        # 其他情况按股票处理
        return analyzer.analyze_stock(code, market)


def quick_check(code: str) -> str:
    """
    快速检查股票/基金状态
    
    Args:
        code: 股票代码
        
    Returns:
        简要信息字符串
    """
    analyzer = get_analyzer()
    return analyzer.quick_check(code)


def search_stock(keyword: str) -> list:
    """
    搜索股票（简化版）
    
    Args:
        keyword: 关键词（股票名称或代码）
        
    Returns:
        匹配的股票列表
    """
    # 简化实现：直接返回常见股票
    # 实际应该调用搜索 API
    stocks = {
        '茅台': ['600519', '贵州茅台'],
        '腾讯': ['0700.HK', '腾讯控股'],
        '阿里': ['9988.HK', '阿里巴巴'],
        '平安': ['601318', '中国平安'],
        '招行': ['600036', '招商银行'],
    }
    
    results = []
    for key, value in stocks.items():
        if key in keyword:
            results.append({'code': value[0], 'name': value[1]})
    
    return results


# OpenClaw 工具调用入口
def main():
    """OpenClaw 工具调用入口"""
    if len(sys.argv) < 2:
        print(json.dumps({
            'error': '请提供股票代码',
            'usage': 'python openclaw_integration.py <股票代码> [市场类型]'
        }, ensure_ascii=False))
        return
    
    code = sys.argv[1]
    market = sys.argv[2] if len(sys.argv) > 2 else 'auto'
    
    try:
        result = analyze_stock(code, market)
        print(json.dumps(result, ensure_ascii=False, default=str))
    except Exception as e:
        print(json.dumps({
            'error': str(e),
            'code': code
        }, ensure_ascii=False))


if __name__ == '__main__':
    main()
