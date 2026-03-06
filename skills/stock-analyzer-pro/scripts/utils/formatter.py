#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
报告格式化输出模块
"""

from typing import Dict, Any, Optional
from datetime import datetime


class ReportFormatter:
    """报告格式化器"""
    
    def format_report(
        self,
        code: str,
        quote_data: Dict[str, Any],
        financial_analysis: Dict[str, Any],
        technical_analysis: Dict[str, Any],
        valuation_analysis: Dict[str, Any],
        risk_analysis: Dict[str, Any],
        validation_report: Optional[Dict[str, Any]] = None,
        value_analysis: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        格式化股票分析报告
        
        Returns:
            包含 markdown 报告和其他数据的字典
        """
        name = quote_data.get('name', code)
        price = quote_data.get('price', 0)
        change_pct = quote_data.get('change_percent', 0)
        
        # 生成综合评级
        rating = self._calculate_rating(financial_analysis, technical_analysis, valuation_analysis, risk_analysis)
        
        # 构建 Markdown 报告
        markdown = f"""## 📈 {name} ({code}) 分析报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}

---

### 🎯 核心指标

| 指标 | 数值 | 评估 |
|------|------|------|
| 当前价 | ¥{price:.2f} | {change_pct:+.2f}% |
| PE(TTM) | {quote_data.get('pe_ttm', 'N/A')} | {valuation_analysis.get('pe', {}).get('icon', '⚪')} |
| PB | {quote_data.get('pb', 'N/A')} | {valuation_analysis.get('pb', {}).get('icon', '⚪')} |
| 市值 | {self._format_market_cap(quote_data.get('market_cap', 0))} | - |
| 52 周范围 | {self._format_52w_range(quote_data)} | - |

---

### 💰 财务健康度：{financial_analysis.get('health_score', 0)}/100 {financial_analysis.get('health_level', 'N/A')}

"""
        
        # 财务指标详情
        if financial_analysis.get('key_metrics'):
            metrics = financial_analysis['key_metrics']
            markdown += f"""| 指标 | 数值 | 评级 |
|------|------|------|
| ROE | {metrics.get('roe', 0):.2f}% | {financial_analysis.get('ratings', {}).get('roe', {}).get('icon', '⚪')} |
| 毛利率 | {metrics.get('gross_margin', 0):.2f}% | {financial_analysis.get('ratings', {}).get('margin', {}).get('icon', '⚪')} |
| 净利率 | {metrics.get('net_margin', 0):.2f}% | {financial_analysis.get('ratings', {}).get('margin', {}).get('icon', '⚪')} |
| 负债率 | {metrics.get('debt_ratio', 0):.2f}% | {financial_analysis.get('ratings', {}).get('debt', {}).get('icon', '⚪')} |
| 营收增长 | {metrics.get('revenue_growth', 0):.2f}% | {financial_analysis.get('ratings', {}).get('growth', {}).get('icon', '⚪')} |

**财务点评**: {financial_analysis.get('summary', '暂无')}

---

"""
        
        # 技术面分析
        markdown += f"""### 📊 技术面：{technical_analysis.get('trend', {}).get('description', 'N/A')}

"""
        
        if technical_analysis.get('ma_analysis'):
            ma = technical_analysis['ma_analysis']
            markdown += f"""**均线位置**: {', '.join(ma.get('position', []))}

**关键点位**:
- 阻力位 1: ¥{technical_analysis.get('support_resistance', {}).get('resistance_1', 0):.2f}
- 阻力位 2: ¥{technical_analysis.get('support_resistance', {}).get('resistance_2', 0):.2f}
- 支撑位 1: ¥{technical_analysis.get('support_resistance', {}).get('support_1', 0):.2f}
- 支撑位 2: ¥{technical_analysis.get('support_resistance', {}).get('support_2', 0):.2f}

**技术指标**:
- MACD: {technical_analysis.get('macd', {}).get('signal', {}).get('signal', 'N/A')} {technical_analysis.get('macd', {}).get('signal', {}).get('icon', '')}
- KDJ: {technical_analysis.get('kdj', {}).get('signal', {}).get('signal', 'N/A')} {technical_analysis.get('kdj', {}).get('signal', {}).get('icon', '')}
- RSI: {technical_analysis.get('rsi', {}).get('signal', {}).get('signal', 'N/A')} {technical_analysis.get('rsi', {}).get('signal', {}).get('icon', '')}

**技术点评**: {technical_analysis.get('summary', '暂无')}

---

"""
        
        # 估值分析
        markdown += f"""### 💵 估值分析：{valuation_analysis.get('valuation_level', 'N/A')}

**PE 估值**: {valuation_analysis.get('pe', {}).get('comment', 'N/A')}

**PB 估值**: {valuation_analysis.get('pb', {}).get('comment', 'N/A')}

**合理价格区间**: ¥{valuation_analysis.get('fair_value', {}).get('low', 0):.2f} - ¥{valuation_analysis.get('fair_value', {}).get('high', 0):.2f}

**安全边际**: {valuation_analysis.get('margin_of_safety', {}).get('percentage', 0):.1f}% {valuation_analysis.get('margin_of_safety', {}).get('icon', '')}

**估值点评**: {valuation_analysis.get('summary', '暂无')}

---

"""
        
        # 风险分析
        markdown += f"""### ⚠️ 风险分析：{risk_analysis.get('icon', '⚪')} {risk_analysis.get('level', 'N/A')}

"""
        
        if risk_analysis.get('risks'):
            for risk in risk_analysis['risks']:
                markdown += f"- {risk.get('icon', '⚪')} **{risk.get('type', '')}**: {risk.get('description', '')}\n"
                
        if risk_analysis.get('warnings'):
            for warning in risk_analysis['warnings']:
                markdown += f"- {warning.get('icon', '⚪')} **{warning.get('type', '')}**: {warning.get('description', '')}\n"
                
        if not risk_analysis.get('risks') and not risk_analysis.get('warnings'):
            markdown += "暂无明显风险因素\n"
            
        markdown += f"""
**风险点评**: {risk_analysis.get('summary', '暂无')}

---

"""
        
        # 数据验证报告
        if validation_report:
            markdown += f"""### 🔍 数据可信度：{validation_report.get('icon', '⚪')} {validation_report.get('confidence_score', 0)}% ({validation_report.get('confidence_level', 'N/A')})

"""
            if validation_report.get('issues'):
                markdown += "**数据问题**:\n"
                for issue in validation_report['issues'][:5]:
                    markdown += f"- {issue}\n"
            else:
                markdown += "数据验证通过，无明显问题\n"
                
            markdown += "\n---\n\n"
            
        markdown += f"""
**风险点评**: {risk_analysis.get('summary', '暂无')}

---

"""
        
        # 综合评级
        markdown += f"""### 🏆 综合评级：{rating['rating']} {rating['icon']}

**评级说明**: {rating['description']}

**操作建议**: {rating['suggestion']}

---

> ⚠️ **免责声明**: 本报告仅供参考，不构成投资建议。投资有风险，入市需谨慎。
"""
        
        return {
            'markdown': markdown,
            'code': code,
            'name': name,
            'price': price,
            'rating': rating['rating'],
            'financial_score': financial_analysis.get('health_score', 0),
            'risk_level': risk_analysis.get('level', 'N/A'),
            'generated_at': datetime.now().isoformat()
        }
    
    def format_fund_report(
        self,
        code: str,
        fund_info: Dict[str, Any],
        nav_history: Optional[Any] = None,
        holdings: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        格式化基金分析报告
        """
        name = fund_info.get('name', code)
        fund_type = fund_info.get('type', '未知')
        manager = fund_info.get('manager', '未知')
        company = fund_info.get('company', '未知')
        nav = fund_info.get('nav', 0)
        nav_change = fund_info.get('nav_change', 0)
        
        markdown = f"""## 📈 {name} ({code}) 基金分析

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}

---

### 🎯 基本信息

| 项目 | 内容 |
|------|------|
| 基金类型 | {fund_type} |
| 基金公司 | {company} |
| 基金经理 | {manager} |
| 当前净值 | ¥{nav:.4f} |
| 日涨跌 | {nav_change:+.2f}% |

---

### 📊 业绩表现

"""
        
        # 如果有净值历史，计算收益率
        if nav_history is not None and len(nav_history) > 0:
            markdown += self._calculate_fund_returns(nav_history)
        else:
            markdown += "暂无历史净值数据\n"
            
        markdown += """
---

### 💼 重仓持仓

"""
        
        if holdings and holdings.get('stocks'):
            stocks = holdings['stocks']
            markdown += "| 股票 | 代码 | 持仓比例 |\n|------|------|----------|\n"
            # 显示前 5 大重仓股
            for i in range(min(5, len(stocks))):
                stock = stocks[i] if isinstance(stocks, list) else list(stocks.values())[i]
                markdown += f"| {stock.get('股票名称', 'N/A')} | {stock.get('股票代码', 'N/A')} | {stock.get('占净值比', 'N/A')}% |\n"
        else:
            markdown += "暂无持仓数据\n"
            
        markdown += """
---

> ⚠️ **免责声明**: 基金过往业绩不代表未来表现，投资需谨慎。
"""
        
        return {
            'markdown': markdown,
            'code': code,
            'name': name,
            'nav': nav,
            'type': fund_type
        }
    
    def _calculate_rating(
        self,
        financial: Dict,
        technical: Dict,
        valuation: Dict,
        risk: Dict
    ) -> Dict[str, Any]:
        """计算综合评级"""
        score = 0
        max_score = 100
        
        # 财务评分 (40 分)
        financial_score = financial.get('health_score', 50)
        score += financial_score * 0.4
        
        # 技术面评分 (20 分)
        trend_type = technical.get('trend', {}).get('type', '震荡')
        if trend_type == '多头':
            score += 20
        elif trend_type == '空头':
            score += 0
        else:
            score += 10
            
        # 估值评分 (25 分)
        valuation_level = valuation.get('valuation_level', '合理')
        if '低估' in valuation_level:
            score += 25
        elif '偏低' in valuation_level:
            score += 20
        elif '合理' in valuation_level:
            score += 15
        elif '偏高' in valuation_level:
            score += 5
        else:
            score += 0
            
        # 风险扣分 (15 分)
        risk_level = risk.get('level', '低风险')
        if '极低' in risk_level:
            score += 15
        elif '低' in risk_level:
            score += 12
        elif '中等' in risk_level:
            score += 5
        else:
            score += 0
            
        # 确定评级
        if score >= 85:
            rating = '强烈推荐'
            icon = '🟢'
            description = '基本面优秀，技术面强势，估值合理，风险可控'
            suggestion = '可积极配置'
        elif score >= 70:
            rating = '推荐'
            icon = '🟢'
            description = '基本面良好，具备投资价值'
            suggestion = '可逢低布局'
        elif score >= 55:
            rating = '中性'
            icon = '🟡'
            description = '各方面表现均衡，无明显优势'
            suggestion = '观望为主'
        elif score >= 40:
            rating = '谨慎'
            icon = '🟠'
            description = '存在一定风险因素'
            suggestion = '谨慎参与，控制仓位'
        else:
            rating = '回避'
            icon = '🔴'
            description = '基本面或估值存在较大问题'
            suggestion = '建议回避'
            
        return {
            'rating': rating,
            'icon': icon,
            'score': round(score),
            'description': description,
            'suggestion': suggestion
        }
    
    def _format_market_cap(self, market_cap: float) -> str:
        """格式化市值"""
        if not market_cap or market_cap <= 0:
            return "N/A"
        if market_cap >= 1e12:
            return f"{market_cap / 1e12:.2f}万亿"
        elif market_cap >= 1e10:
            return f"{market_cap / 1e10:.2f}百亿"
        elif market_cap >= 1e8:
            return f"{market_cap / 1e8:.2f}亿"
        else:
            return f"{market_cap:.2f}"
    
    def _format_52w_range(self, quote_data: Dict) -> str:
        """格式化 52 周范围"""
        low = quote_data.get('low_52w')
        high = quote_data.get('high_52w')
        if low and high and low > 0 and high > 0:
            return f"{low:.2f} - {high:.2f}"
        return "N/A"
    
    def _calculate_fund_returns(self, nav_history) -> str:
        """计算基金收益率"""
        # 简化实现
        return "暂无详细业绩数据\n"
