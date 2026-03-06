#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stock Analyzer Pro - 专业股票/基金分析工具
主入口模块
"""

import sys
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

# 添加父目录到路径
sys.path.insert(0, '/home/admin/.openclaw/workspace/skills/stock-analyzer-pro')

from scripts.data_sources.akshare_cn import AKShareDataSource
from scripts.data_sources.yfinance_us import YFinanceDataSource
from scripts.data_sources.fund_cn import FundDataSource
from scripts.analysis.financial import FinancialAnalyzer
from scripts.analysis.technical import TechnicalAnalyzer
from scripts.analysis.valuation import ValuationAnalyzer
from scripts.analysis.risk import RiskAnalyzer
from scripts.analysis.value_investing import ValueInvestingAnalyzer
from scripts.utils.formatter import ReportFormatter
from scripts.utils.data_validator import DataValidator


class StockAnalyzerPro:
    """股票/基金分析器主类"""
    
    def __init__(self):
        self.akshare = AKShareDataSource()
        self.yfinance = YFinanceDataSource()
        self.fund = FundDataSource()
        self.formatter = ReportFormatter()
        
    def detect_market(self, code: str) -> str:
        """
        检测股票代码所属市场
        
        Args:
            code: 股票代码或名称
            
        Returns:
            'cn_stock' | 'us_stock' | 'cn_fund' | 'unknown'
        """
        code = code.upper().strip()
        
        # A 股代码：6 位数字 + .SH/.SZ 或纯 6 位数字
        if code.endswith('.SH') or code.endswith('.SZ'):
            return 'cn_stock'
        if code.isdigit() and len(code) == 6:
            return 'cn_stock'
            
        # 港股代码：5 位数字 + .HK
        if code.endswith('.HK'):
            return 'cn_stock'  # AKShare 也支持港股
            
        # 美股代码：字母组合
        if code.isalpha() or (code.replace('.', '').replace('-', '').isalnum()):
            return 'us_stock'
            
        # 基金代码：6 位数字
        if code.isdigit() and len(code) == 6:
            # 需要进一步判断是股票还是基金
            return 'cn_fund'  # 默认按基金处理
            
        return 'unknown'
    
    def analyze_stock(self, code: str, market: str = 'auto') -> Dict[str, Any]:
        """
        分析股票
        
        Args:
            code: 股票代码或名称
            market: 市场类型，'auto' 自动检测
            
        Returns:
            分析报告字典
        """
        if market == 'auto':
            market = self.detect_market(code)
            
        # 获取数据源
        if market == 'us_stock':
            datasource = self.yfinance
        else:
            datasource = self.akshare
            
        # 获取基础数据
        print(f"📊 正在分析 {code}...")
        
        # 1. 获取实时行情
        quote_data = datasource.get_quote(code)
        if not quote_data:
            return {"error": f"无法获取 {code} 的行情数据"}
            
        # 1.5 获取 52 周高低点
        high_52w, low_52w = datasource.get_52week_range(code)
        if high_52w and low_52w:
            quote_data['high_52w'] = high_52w
            quote_data['low_52w'] = low_52w
            
        # 2. 获取财务数据
        financial_data = datasource.get_financials(code)
        
        # 2.5 将行情数据中的 ROE 补充到财务数据
        if financial_data and 'indicators' in financial_data:
            roe_from_quote = quote_data.get('roe')
            if roe_from_quote and roe_from_quote > 0:
                financial_data['indicators']['roe'] = roe_from_quote
        
        # 3. 获取历史行情（用于技术分析）
        history_data = datasource.get_history(code, period='1y')
        
        # 4. 数据真实性验证
        validation_report = DataValidator.generate_validation_report(quote_data, financial_data)
        
        # 如果数据验证问题严重，添加警告
        if validation_report['confidence_score'] < 70:
            print(f"⚠️ 数据可信度：{validation_report['confidence_score']}% ({validation_report['confidence_level']})")
            for issue in validation_report['issues'][:3]:
                print(f"   - {issue}")
        
        # 5. 执行分析
        financial_analysis = FinancialAnalyzer.analyze(financial_data) if financial_data else {}
        technical_analysis = TechnicalAnalyzer.analyze(history_data) if history_data is not None and len(history_data) > 0 else {}
        valuation_analysis = ValuationAnalyzer.analyze(quote_data, financial_data) if financial_data else {}
        risk_analysis = RiskAnalyzer.analyze(code, quote_data)
        value_analysis = ValueInvestingAnalyzer.analyze(quote_data, financial_data)
        
        # 6. 生成报告
        report = self.formatter.format_report(
            code=code,
            quote_data=quote_data,
            financial_analysis=financial_analysis,
            technical_analysis=technical_analysis,
            valuation_analysis=valuation_analysis,
            risk_analysis=risk_analysis,
            validation_report=validation_report,
            value_analysis=value_analysis
        )
        
        return report
    
    def analyze_fund(self, code: str) -> Dict[str, Any]:
        """
        分析基金
        
        Args:
            code: 基金代码或名称
            
        Returns:
            分析报告字典
        """
        print(f"📊 正在分析基金 {code}...")
        
        # 获取基金数据
        fund_info = self.fund.get_fund_info(code)
        if not fund_info:
            return {"error": f"无法获取基金 {code} 的信息"}
            
        # 获取净值历史
        nav_history = self.fund.get_nav_history(code, period='1y')
        
        # 获取持仓信息
        holdings = self.fund.get_holdings(code)
        
        # 生成基金分析报告
        report = self.formatter.format_fund_report(
            code=code,
            fund_info=fund_info,
            nav_history=nav_history,
            holdings=holdings
        )
        
        return report
    
    def quick_check(self, code: str) -> str:
        """
        快速检查股票/基金状态
        
        Args:
            code: 代码
            
        Returns:
            简要信息字符串
        """
        market = self.detect_market(code)
        
        if market == 'us_stock':
            quote = self.yfinance.get_quote(code)
        else:
            quote = self.akshare.get_quote(code)
            
        if not quote:
            return f"❌ 无法获取 {code} 的数据"
            
        return f"{quote.get('name', code)}: ¥{quote.get('price', 0):.2f} ({quote.get('change_percent', 0):+.2f}%) - PE: {quote.get('pe', 'N/A')}"


def main():
    """主函数 - 支持命令行和模块调用"""
    analyzer = StockAnalyzerPro()
    
    # 检查命令行参数
    if len(sys.argv) > 1:
        code = sys.argv[1]
        report = analyzer.analyze_stock(code)
        
        if "error" in report:
            print(f"❌ {report['error']}")
        else:
            print(report.get('markdown', str(report)))
    else:
        print("Stock Analyzer Pro - 专业股票/基金分析工具")
        print("用法：python main.py <股票代码>")
        print("示例：python main.py 600519")
        print("      python main.py AAPL")


if __name__ == "__main__":
    main()
