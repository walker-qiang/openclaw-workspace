#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
财务分析模块
"""

from typing import Dict, Any, Optional


class FinancialAnalyzer:
    """财务分析器"""
    
    @staticmethod
    def analyze(financial_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析财务数据
        
        Args:
            financial_data: 财务数据字典
            
        Returns:
            分析结果
        """
        if not financial_data or 'indicators' not in financial_data:
            return {}
            
        indicators = financial_data['indicators']
        
        # 计算财务健康度评分（0-100）
        health_score = FinancialAnalyzer._calculate_health_score(indicators)
        
        # 评估各项指标
        roe_rating = FinancialAnalyzer._rate_roe(indicators.get('roe', 0))
        margin_rating = FinancialAnalyzer._rate_margin(indicators.get('gross_margin', 0), indicators.get('net_margin', 0))
        debt_rating = FinancialAnalyzer._rate_debt(indicators.get('debt_ratio', 0))
        growth_rating = FinancialAnalyzer._rate_growth(indicators.get('revenue_growth', 0), indicators.get('profit_growth', 0))
        
        return {
            'health_score': health_score,
            'health_level': FinancialAnalyzer._score_to_level(health_score),
            'ratings': {
                'roe': roe_rating,
                'margin': margin_rating,
                'debt': debt_rating,
                'growth': growth_rating
            },
            'key_metrics': {
                'roe': indicators.get('roe', 0),
                'gross_margin': indicators.get('gross_margin', 0),
                'net_margin': indicators.get('net_margin', 0),
                'debt_ratio': indicators.get('debt_ratio', 0),
                'current_ratio': indicators.get('current_ratio', 0),
                'eps': indicators.get('eps', 0),
                'revenue_growth': indicators.get('revenue_growth', 0),
                'profit_growth': indicators.get('profit_growth', 0),
            },
            'summary': FinancialAnalyzer._generate_summary(indicators, health_score)
        }
    
    @staticmethod
    def _calculate_health_score(indicators: Dict[str, float]) -> int:
        """
        计算财务健康度评分
        
        评分维度：
        - ROE (25 分): >20% 满分，>15% 20 分，>10% 15 分，>5% 10 分
        - 毛利率 (20 分): >40% 满分，>30% 15 分，>20% 10 分
        - 负债率 (20 分): <40% 满分，<60% 15 分，<70% 10 分
        - 增长率 (20 分): >30% 满分，>20% 15 分，>10% 10 分
        - 流动比率 (15 分): >2 满分，>1.5 10 分，>1 5 分
        """
        score = 0
        
        # ROE 评分 (25 分)
        roe = indicators.get('roe', 0)
        if roe > 20:
            score += 25
        elif roe > 15:
            score += 20
        elif roe > 10:
            score += 15
        elif roe > 5:
            score += 10
        elif roe > 0:
            score += 5
            
        # 毛利率评分 (20 分)
        gross_margin = indicators.get('gross_margin', 0)
        if gross_margin > 40:
            score += 20
        elif gross_margin > 30:
            score += 15
        elif gross_margin > 20:
            score += 10
        elif gross_margin > 10:
            score += 5
            
        # 负债率评分 (20 分) - 越低越好
        debt_ratio = indicators.get('debt_ratio', 100)
        if debt_ratio < 40:
            score += 20
        elif debt_ratio < 60:
            score += 15
        elif debt_ratio < 70:
            score += 10
        elif debt_ratio < 80:
            score += 5
            
        # 增长率评分 (20 分)
        revenue_growth = indicators.get('revenue_growth', 0)
        profit_growth = indicators.get('profit_growth', 0)
        avg_growth = (revenue_growth + profit_growth) / 2
        if avg_growth > 30:
            score += 20
        elif avg_growth > 20:
            score += 15
        elif avg_growth > 10:
            score += 10
        elif avg_growth > 0:
            score += 5
            
        # 流动比率评分 (15 分)
        current_ratio = indicators.get('current_ratio', 0)
        if current_ratio > 2:
            score += 15
        elif current_ratio > 1.5:
            score += 10
        elif current_ratio > 1:
            score += 5
            
        return min(100, max(0, score))
    
    @staticmethod
    def _rate_roe(roe: float) -> Dict[str, Any]:
        """评估 ROE"""
        if roe > 20:
            return {'level': '优秀', 'icon': '🟢', 'comment': 'ROE 超过 20%，盈利能力极强'}
        elif roe > 15:
            return {'level': '良好', 'icon': '🟢', 'comment': 'ROE 在 15-20%，盈利能力较强'}
        elif roe > 10:
            return {'level': '一般', 'icon': '🟡', 'comment': 'ROE 在 10-15%，盈利能力中等'}
        elif roe > 0:
            return {'level': '较弱', 'icon': '🟡', 'comment': 'ROE 低于 10%，盈利能力有待提升'}
        else:
            return {'level': '亏损', 'icon': '🔴', 'comment': 'ROE 为负，公司处于亏损状态'}
    
    @staticmethod
    def _rate_margin(gross_margin: float, net_margin: float) -> Dict[str, Any]:
        """评估利润率"""
        if gross_margin > 40 and net_margin > 20:
            return {'level': '优秀', 'icon': '🟢', 'comment': '毛利率和净利率双高，盈利质量优秀'}
        elif gross_margin > 30 and net_margin > 15:
            return {'level': '良好', 'icon': '🟢', 'comment': '利润率水平良好'}
        elif gross_margin > 20:
            return {'level': '一般', 'icon': '🟡', 'comment': '利润率处于行业中等水平'}
        else:
            return {'level': '偏低', 'icon': '🟡', 'comment': '利润率偏低，需关注成本控制'}
    
    @staticmethod
    def _rate_debt(debt_ratio: float) -> Dict[str, Any]:
        """评估负债水平"""
        if debt_ratio < 40:
            return {'level': '健康', 'icon': '🟢', 'comment': '负债率低，财务风险小'}
        elif debt_ratio < 60:
            return {'level': '合理', 'icon': '🟢', 'comment': '负债水平合理'}
        elif debt_ratio < 70:
            return {'level': '偏高', 'icon': '🟡', 'comment': '负债率偏高，需关注偿债风险'}
        else:
            return {'level': '高风险', 'icon': '🔴', 'comment': '负债率过高，财务风险较大'}
    
    @staticmethod
    def _rate_growth(revenue_growth: float, profit_growth: float) -> Dict[str, Any]:
        """评估成长性"""
        avg_growth = (revenue_growth + profit_growth) / 2
        if avg_growth > 30:
            return {'level': '高增长', 'icon': '🟢', 'comment': '营收和利润高速增长'}
        elif avg_growth > 20:
            return {'level': '稳健增长', 'icon': '🟢', 'comment': '保持稳健增长态势'}
        elif avg_growth > 10:
            return {'level': '低速增长', 'icon': '🟡', 'comment': '增速放缓'}
        elif avg_growth > 0:
            return {'level': '微增长', 'icon': '🟡', 'comment': '增长乏力'}
        else:
            return {'level': '负增长', 'icon': '🔴', 'comment': '业绩下滑，需警惕'}
    
    @staticmethod
    def _score_to_level(score: int) -> str:
        """将分数转换为等级"""
        if score >= 85:
            return '优秀 🟢'
        elif score >= 70:
            return '良好 🟢'
        elif score >= 55:
            return '一般 🟡'
        elif score >= 40:
            return '偏弱 🟡'
        else:
            return '较差 🔴'
    
    @staticmethod
    def _generate_summary(indicators: Dict[str, float], health_score: int) -> str:
        """生成财务分析摘要"""
        roe = indicators.get('roe', 0)
        growth = indicators.get('revenue_growth', 0)
        debt = indicators.get('debt_ratio', 0)
        
        summary_parts = []
        
        # ROE 评价
        if roe > 20:
            summary_parts.append(f"ROE 高达{roe:.1f}%，盈利能力极强")
        elif roe > 15:
            summary_parts.append(f"ROE 为{roe:.1f}%，盈利能力较强")
        elif roe < 0:
            summary_parts.append(f"ROE 为{roe:.1f}%，处于亏损状态")
            
        # 成长性评价
        if growth > 30:
            summary_parts.append(f"营收增长{growth:.1f}%，处于高速增长期")
        elif growth < 0:
            summary_parts.append(f"营收下滑{abs(growth):.1f}%，需关注经营压力")
            
        # 负债评价
        if debt > 70:
            summary_parts.append(f"负债率{debt:.1f}%偏高，注意财务风险")
        elif debt < 40:
            summary_parts.append(f"负债率{debt:.1f}%较低，财务稳健")
            
        if not summary_parts:
            return f"财务健康度{health_score}分，整体状况正常"
            
        return "；".join(summary_parts)
