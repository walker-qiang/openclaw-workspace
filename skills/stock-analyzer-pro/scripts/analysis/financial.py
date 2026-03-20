#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
财务分析模块
"""

from typing import Dict, Any, Optional


def _v(indicators: Dict, key: str, default=0):
    """Get indicator value, treating None as missing (returns default)."""
    val = indicators.get(key)
    return val if val is not None else default


def _has(indicators: Dict, key: str) -> bool:
    """Check if an indicator has real (non-None) data."""
    return indicators.get(key) is not None


class FinancialAnalyzer:
    """财务分析器"""

    @staticmethod
    def analyze(financial_data: Dict[str, Any]) -> Dict[str, Any]:
        if not financial_data or 'indicators' not in financial_data:
            return {}

        indicators = financial_data['indicators']

        health_score, scored_items, total_items = FinancialAnalyzer._calculate_health_score(indicators)

        roe_rating = FinancialAnalyzer._rate_roe(_v(indicators, 'roe'))
        margin_rating = FinancialAnalyzer._rate_margin(
            indicators.get('gross_margin'), indicators.get('net_margin'))
        debt_rating = FinancialAnalyzer._rate_debt(indicators.get('debt_ratio'))
        growth_rating = FinancialAnalyzer._rate_growth(
            indicators.get('revenue_growth'), indicators.get('profit_growth'))

        return {
            'health_score': health_score,
            'health_level': FinancialAnalyzer._score_to_level(health_score, scored_items, total_items),
            'data_completeness': f'{scored_items}/{total_items}',
            'ratings': {
                'roe': roe_rating,
                'margin': margin_rating,
                'debt': debt_rating,
                'growth': growth_rating,
            },
            'key_metrics': {
                'roe': indicators.get('roe'),
                'gross_margin': indicators.get('gross_margin'),
                'net_margin': indicators.get('net_margin'),
                'debt_ratio': indicators.get('debt_ratio'),
                'current_ratio': indicators.get('current_ratio'),
                'eps': indicators.get('eps'),
                'revenue_growth': indicators.get('revenue_growth'),
                'profit_growth': indicators.get('profit_growth'),
            },
            'report_date': financial_data.get('report_date', ''),
            'report_type': financial_data.get('report_type', ''),
            'summary': FinancialAnalyzer._generate_summary(indicators, health_score)
        }

    @staticmethod
    def _calculate_health_score(indicators: Dict) -> tuple:
        """
        Returns (score, scored_items, total_items).
        Only scores items that have real data. The score is normalized to 0-100.
        """
        max_score = 0
        raw_score = 0
        scored = 0
        total = 5  # ROE, gross_margin, debt_ratio, growth, current_ratio

        # ROE (25 pts)
        if _has(indicators, 'roe'):
            scored += 1
            max_score += 25
            roe = _v(indicators, 'roe')
            if roe > 20:
                raw_score += 25
            elif roe > 15:
                raw_score += 20
            elif roe > 10:
                raw_score += 15
            elif roe > 5:
                raw_score += 10
            elif roe > 0:
                raw_score += 5

        # Gross margin (20 pts)
        if _has(indicators, 'gross_margin'):
            scored += 1
            max_score += 20
            gm = _v(indicators, 'gross_margin')
            if gm > 40:
                raw_score += 20
            elif gm > 30:
                raw_score += 15
            elif gm > 20:
                raw_score += 10
            elif gm > 10:
                raw_score += 5

        # Debt ratio (20 pts)
        if _has(indicators, 'debt_ratio'):
            scored += 1
            max_score += 20
            dr = _v(indicators, 'debt_ratio', 100)
            if dr < 40:
                raw_score += 20
            elif dr < 60:
                raw_score += 15
            elif dr < 70:
                raw_score += 10
            elif dr < 80:
                raw_score += 5

        # Growth (20 pts)
        has_growth = _has(indicators, 'revenue_growth') or _has(indicators, 'profit_growth')
        if has_growth:
            scored += 1
            max_score += 20
            rg = _v(indicators, 'revenue_growth')
            pg = _v(indicators, 'profit_growth')
            cnt = sum(1 for x in [indicators.get('revenue_growth'), indicators.get('profit_growth')] if x is not None)
            avg = (rg + pg) / max(cnt, 1)
            if avg > 30:
                raw_score += 20
            elif avg > 20:
                raw_score += 15
            elif avg > 10:
                raw_score += 10
            elif avg > 0:
                raw_score += 5

        # Current ratio (15 pts)
        if _has(indicators, 'current_ratio'):
            scored += 1
            max_score += 15
            cr = _v(indicators, 'current_ratio')
            if cr > 2:
                raw_score += 15
            elif cr > 1.5:
                raw_score += 10
            elif cr > 1:
                raw_score += 5

        if max_score == 0:
            return 0, 0, total

        normalized = int(raw_score / max_score * 100)
        return min(100, max(0, normalized)), scored, total

    @staticmethod
    def _rate_roe(roe: float) -> Dict[str, Any]:
        if roe > 20:
            return {'level': '优秀', 'icon': '🟢', 'comment': 'ROE 超过 20%，盈利能力极强'}
        elif roe > 15:
            return {'level': '良好', 'icon': '🟢', 'comment': 'ROE 在 15-20%，盈利能力较强'}
        elif roe > 10:
            return {'level': '一般', 'icon': '🟡', 'comment': 'ROE 在 10-15%，盈利能力中等'}
        elif roe > 0:
            return {'level': '较弱', 'icon': '🟡', 'comment': 'ROE 低于 10%，盈利能力有待提升'}
        return {'level': '亏损', 'icon': '🔴', 'comment': 'ROE 为负，公司处于亏损状态'}

    @staticmethod
    def _rate_margin(gross_margin, net_margin) -> Dict[str, Any]:
        if gross_margin is None and net_margin is None:
            return {'level': '数据缺失', 'icon': '⚪', 'comment': '暂无利润率数据'}
        gm = gross_margin or 0
        nm = net_margin or 0
        if gm > 40 and nm > 20:
            return {'level': '优秀', 'icon': '🟢', 'comment': '毛利率和净利率双高，盈利质量优秀'}
        elif gm > 30 and nm > 15:
            return {'level': '良好', 'icon': '🟢', 'comment': '利润率水平良好'}
        elif gm > 20:
            return {'level': '一般', 'icon': '🟡', 'comment': '利润率处于行业中等水平'}
        return {'level': '偏低', 'icon': '🟡', 'comment': '利润率偏低，需关注成本控制'}

    @staticmethod
    def _rate_debt(debt_ratio) -> Dict[str, Any]:
        if debt_ratio is None:
            return {'level': '数据缺失', 'icon': '⚪', 'comment': '暂无负债率数据'}
        if debt_ratio < 40:
            return {'level': '健康', 'icon': '🟢', 'comment': '负债率低，财务风险小'}
        elif debt_ratio < 60:
            return {'level': '合理', 'icon': '🟢', 'comment': '负债水平合理'}
        elif debt_ratio < 70:
            return {'level': '偏高', 'icon': '🟡', 'comment': '负债率偏高，需关注偿债风险'}
        return {'level': '高风险', 'icon': '🔴', 'comment': '负债率过高，财务风险较大'}

    @staticmethod
    def _rate_growth(revenue_growth, profit_growth) -> Dict[str, Any]:
        if revenue_growth is None and profit_growth is None:
            return {'level': '数据缺失', 'icon': '⚪', 'comment': '暂无增长率数据'}
        rg = revenue_growth or 0
        pg = profit_growth or 0
        cnt = sum(1 for x in [revenue_growth, profit_growth] if x is not None)
        avg = (rg + pg) / max(cnt, 1)
        if avg > 30:
            return {'level': '高增长', 'icon': '🟢', 'comment': '营收和利润高速增长'}
        elif avg > 20:
            return {'level': '稳健增长', 'icon': '🟢', 'comment': '保持稳健增长态势'}
        elif avg > 10:
            return {'level': '低速增长', 'icon': '🟡', 'comment': '增速放缓'}
        elif avg > 0:
            return {'level': '微增长', 'icon': '🟡', 'comment': '增长乏力'}
        return {'level': '负增长', 'icon': '🔴', 'comment': '业绩下滑，需警惕'}

    @staticmethod
    def _score_to_level(score: int, scored_items: int, total_items: int) -> str:
        if scored_items == 0:
            return 'N/A（无财务数据）'
        suffix = f'（数据 {scored_items}/{total_items}）' if scored_items < total_items else ''
        if score >= 85:
            return f'优秀 🟢{suffix}'
        elif score >= 70:
            return f'良好 🟢{suffix}'
        elif score >= 55:
            return f'一般 🟡{suffix}'
        elif score >= 40:
            return f'偏弱 🟡{suffix}'
        return f'较差 🔴{suffix}'

    @staticmethod
    def _generate_summary(indicators: Dict, health_score: int) -> str:
        roe = _v(indicators, 'roe')
        growth = indicators.get('revenue_growth')
        debt = indicators.get('debt_ratio')

        parts = []

        if roe > 20:
            parts.append(f"ROE 高达{roe:.1f}%，盈利能力极强")
        elif roe > 15:
            parts.append(f"ROE 为{roe:.1f}%，盈利能力较强")
        elif roe < 0:
            parts.append(f"ROE 为{roe:.1f}%，处于亏损状态")

        if growth is not None:
            if growth > 30:
                parts.append(f"营收增长{growth:.1f}%，处于高速增长期")
            elif growth < 0:
                parts.append(f"营收下滑{abs(growth):.1f}%，需关注经营压力")

        if debt is not None:
            if debt > 70:
                parts.append(f"负债率{debt:.1f}%偏高，注意财务风险")
            elif debt < 40:
                parts.append(f"负债率{debt:.1f}%较低，财务稳健")

        if not parts:
            return f"财务健康度{health_score}分，整体状况正常"

        return "；".join(parts)
