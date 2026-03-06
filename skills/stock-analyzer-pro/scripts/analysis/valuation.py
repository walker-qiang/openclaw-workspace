#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
估值分析模块
"""

from typing import Dict, Any, Optional


class ValuationAnalyzer:
    """估值分析器"""
    
    @staticmethod
    def analyze(quote_data: Dict[str, Any], financial_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析估值水平
        
        Args:
            quote_data: 行情数据
            financial_data: 财务数据（可选）
            
        Returns:
            估值分析结果
        """
        if not quote_data:
            return {'error': '缺少行情数据'}
            
        pe_ttm = quote_data.get('pe_ttm')
        pb = quote_data.get('pb')
        price = quote_data.get('price', 0)
        
        # PE 分析
        pe_analysis = ValuationAnalyzer._analyze_pe(pe_ttm, financial_data)
        
        # PB 分析
        pb_analysis = ValuationAnalyzer._analyze_pb(pb, financial_data)
        
        # 计算合理价格区间
        fair_value = ValuationAnalyzer._estimate_fair_value(quote_data, financial_data)
        
        # 安全边际
        margin_of_safety = ValuationAnalyzer._calculate_margin_of_safety(price, fair_value)
        
        return {
            'pe': pe_analysis,
            'pb': pb_analysis,
            'fair_value': fair_value,
            'margin_of_safety': margin_of_safety,
            'valuation_level': ValuationAnalyzer._assess_valuation(pe_analysis, pb_analysis),
            'summary': ValuationAnalyzer._generate_summary(pe_analysis, pb_analysis, margin_of_safety)
        }
    
    @staticmethod
    def _analyze_pe(pe_ttm: Optional[float], financial_data: Optional[Dict]) -> Dict[str, Any]:
        """分析 PE 估值"""
        if pe_ttm is None or pe_ttm <= 0:
            return {
                'value': None,
                'level': '无法评估',
                'icon': '⚪',
                'comment': 'PE 为负或无数据，无法用 PE 估值'
            }
            
        # PE 分位数评估（简化版，实际应该用历史分位）
        if pe_ttm < 10:
            level = '低估'
            icon = '🟢'
            comment = 'PE 低于 10，处于历史低位区间'
        elif pe_ttm < 15:
            level = '偏低'
            icon = '🟢'
            comment = 'PE 在 10-15 区间，估值偏低'
        elif pe_ttm < 25:
            level = '合理'
            icon = '🟡'
            comment = 'PE 在 15-25 区间，估值合理'
        elif pe_ttm < 35:
            level = '偏高'
            icon = '🟠'
            comment = 'PE 在 25-35 区间，估值偏高'
        else:
            level = '高估'
            icon = '🔴'
            comment = 'PE 超过 35，处于历史高位区间'
            
        return {
            'value': pe_ttm,
            'level': level,
            'icon': icon,
            'comment': comment,
            'percentile': ValuationAnalyzer._estimate_pe_percentile(pe_ttm)
        }
    
    @staticmethod
    def _analyze_pb(pb: Optional[float], financial_data: Optional[Dict]) -> Dict[str, Any]:
        """分析 PB 估值"""
        if pb is None or pb <= 0:
            return {
                'value': None,
                'level': '无法评估',
                'icon': '⚪',
                'comment': 'PB 为负或无数据'
            }
            
        if pb < 1:
            level = '低估'
            icon = '🟢'
            comment = 'PB 低于 1，股价低于净资产'
        elif pb < 2:
            level = '偏低'
            icon = '🟢'
            comment = 'PB 在 1-2 区间，估值偏低'
        elif pb < 4:
            level = '合理'
            icon = '🟡'
            comment = 'PB 在 2-4 区间，估值合理'
        elif pb < 6:
            level = '偏高'
            icon = '🟠'
            comment = 'PB 在 4-6 区间，估值偏高'
        else:
            level = '高估'
            icon = '🔴'
            comment = 'PB 超过 6，估值较高'
            
        return {
            'value': pb,
            'level': level,
            'icon': icon,
            'comment': comment
        }
    
    @staticmethod
    def _estimate_pe_percentile(pe: float) -> int:
        """估算 PE 历史分位数（简化版）"""
        # 实际应该查询历史 PE 数据计算分位数
        # 这里用简化的经验公式
        if pe < 10:
            return 20
        elif pe < 15:
            return 35
        elif pe < 20:
            return 50
        elif pe < 30:
            return 70
        else:
            return 85
    
    @staticmethod
    def _estimate_fair_value(quote_data: Dict, financial_data: Optional[Dict]) -> Dict[str, float]:
        """估算合理价格区间"""
        price = quote_data.get('price', 0)
        pe_ttm = quote_data.get('pe_ttm')
        eps = financial_data.get('indicators', {}).get('eps', 0) if financial_data else 0
        
        # 方法 1: PE 法
        if pe_ttm and pe_ttm > 0:
            # 假设合理 PE 为 15-25
            fair_pe_low = 15
            fair_pe_high = 25
            fair_value_pe_low = fair_pe_low * eps if eps > 0 else price * 0.8
            fair_value_pe_high = fair_pe_high * eps if eps > 0 else price * 1.2
        else:
            fair_value_pe_low = price * 0.8
            fair_value_pe_high = price * 1.2
            
        # 方法 2: 布林带中轨（如果有技术数据）
        # 这里简化处理
        
        return {
            'low': round(fair_value_pe_low, 2),
            'high': round(fair_value_pe_high, 2),
            'mid': round((fair_value_pe_low + fair_value_pe_high) / 2, 2),
            'method': 'PE 估值法'
        }
    
    @staticmethod
    def _calculate_margin_of_safety(price: float, fair_value: Dict) -> Dict[str, Any]:
        """计算安全边际"""
        fair_mid = fair_value.get('mid', price)
        
        if fair_mid <= 0:
            return {
                'percentage': 0,
                'level': '无法计算',
                'icon': '⚪'
            }
            
        margin = (fair_mid - price) / fair_mid * 100
        
        if margin > 30:
            level = '很高'
            icon = '🟢'
        elif margin > 15:
            level = '较高'
            icon = '🟢'
        elif margin > 0:
            level = '一般'
            icon = '🟡'
        elif margin > -15:
            level = '较低'
            icon = '🟠'
        else:
            level = '很低'
            icon = '🔴'
            
        return {
            'percentage': round(margin, 2),
            'level': level,
            'icon': icon
        }
    
    @staticmethod
    def _assess_valuation(pe_analysis: Dict, pb_analysis: Dict) -> str:
        """综合评估估值水平"""
        pe_level = pe_analysis.get('level', '')
        pb_level = pb_analysis.get('level', '')
        
        # 统计低估和高估的数量
        low_count = sum(1 for l in [pe_level, pb_level] if l in ['低估', '偏低'])
        high_count = sum(1 for l in [pe_level, pb_level] if l in ['高估', '偏高'])
        
        if low_count >= 2:
            return '低估 🟢'
        elif low_count == 1:
            return '偏低 🟢'
        elif high_count >= 2:
            return '高估 🔴'
        elif high_count == 1:
            return '偏高 🟠'
        else:
            return '合理 🟡'
    
    @staticmethod
    def _generate_summary(pe_analysis: Dict, pb_analysis: Dict, margin: Dict) -> str:
        """生成估值摘要"""
        pe_comment = pe_analysis.get('comment', '')
        pb_comment = pb_analysis.get('comment', '')
        margin_pct = margin.get('percentage', 0)
        
        parts = []
        
        if pe_comment:
            parts.append(pe_comment)
        if pb_comment and pb_comment != pe_comment:
            parts.append(pb_comment)
            
        if margin_pct > 20:
            parts.append(f"安全边际{margin_pct:.1f}%，具备投资价值")
        elif margin_pct < -20:
            parts.append(f"高估{abs(margin_pct):.1f}%，注意风险")
            
        return "；".join(parts) if parts else "估值水平正常"
