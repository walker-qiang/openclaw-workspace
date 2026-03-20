#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
估值分析模块 -- 支持行业差异化估值
"""

from typing import Dict, Any, Optional, Tuple, List


# 行业合理 PE / PB 区间（经验值，来自历史中位数）
# 格式: (pe_low, pe_mid, pe_high), (pb_low, pb_mid, pb_high)
_INDUSTRY_PROFILES: Dict[str, Dict[str, Any]] = {
    "银行":       {"pe": (4, 6, 8),     "pb": (0.4, 0.7, 1.0)},
    "保险":       {"pe": (8, 12, 16),    "pb": (0.8, 1.2, 1.8)},
    "证券":       {"pe": (15, 22, 30),   "pb": (1.0, 1.5, 2.5)},
    "房地产":     {"pe": (5, 8, 12),     "pb": (0.5, 1.0, 1.5)},
    "钢铁":       {"pe": (5, 8, 12),     "pb": (0.6, 1.0, 1.5)},
    "煤炭":       {"pe": (5, 8, 12),     "pb": (0.8, 1.2, 2.0)},
    "石油":       {"pe": (6, 10, 15),    "pb": (0.8, 1.2, 2.0)},
    "电力":       {"pe": (10, 15, 20),   "pb": (1.0, 1.5, 2.5)},
    "公用事业":   {"pe": (10, 15, 22),   "pb": (1.0, 1.5, 2.5)},
    "汽车":       {"pe": (10, 18, 28),   "pb": (1.5, 2.5, 4.0)},
    "家电":       {"pe": (10, 15, 22),   "pb": (2.0, 3.0, 5.0)},
    "食品饮料":   {"pe": (20, 30, 40),   "pb": (4.0, 7.0, 12.0)},
    "白酒":       {"pe": (22, 30, 40),   "pb": (5.0, 8.0, 14.0)},
    "医药":       {"pe": (20, 30, 45),   "pb": (3.0, 5.0, 8.0)},
    "半导体":     {"pe": (25, 40, 60),   "pb": (3.0, 5.0, 10.0)},
    "电子":       {"pe": (20, 30, 45),   "pb": (2.5, 4.0, 7.0)},
    "计算机":     {"pe": (25, 40, 60),   "pb": (3.0, 5.0, 8.0)},
    "通信":       {"pe": (20, 30, 45),   "pb": (2.0, 3.5, 6.0)},
    "传媒":       {"pe": (20, 30, 50),   "pb": (2.0, 3.5, 6.0)},
    "新能源":     {"pe": (20, 35, 55),   "pb": (3.0, 5.0, 9.0)},
    "军工":       {"pe": (30, 45, 65),   "pb": (3.0, 5.0, 8.0)},
    "消费":       {"pe": (18, 28, 38),   "pb": (3.0, 5.0, 8.0)},
    "互联网":     {"pe": (20, 35, 55),   "pb": (3.0, 6.0, 12.0)},
}

_DEFAULT_PROFILE = {"pe": (10, 18, 28), "pb": (1.0, 2.5, 5.0)}


def _match_industry_profile(industry: Optional[str]) -> Dict[str, Any]:
    """根据行业名称模糊匹配估值参数"""
    if not industry:
        return _DEFAULT_PROFILE
    for keyword, profile in _INDUSTRY_PROFILES.items():
        if keyword in industry:
            return profile
    return _DEFAULT_PROFILE


class ValuationAnalyzer:
    """估值分析器"""

    @staticmethod
    def analyze(
        quote_data: Dict[str, Any],
        financial_data: Optional[Dict[str, Any]],
        industry: Optional[str] = None,
        history_data=None,
    ) -> Dict[str, Any]:
        if not quote_data:
            return {'error': '缺少行情数据'}

        pe_ttm = quote_data.get('pe_ttm')
        pb = quote_data.get('pb')
        price = quote_data.get('price', 0)
        profile = _match_industry_profile(industry)

        # Compute real PE percentile from history + TTM EPS
        pe_percentile = None
        if pe_ttm and pe_ttm > 0 and price > 0 and history_data is not None:
            ttm_eps = price / pe_ttm
            pe_percentile = ValuationAnalyzer._compute_pe_percentile(history_data, ttm_eps, pe_ttm)

        pe_analysis = ValuationAnalyzer._analyze_pe(pe_ttm, profile, pe_percentile)
        pb_analysis = ValuationAnalyzer._analyze_pb(pb, profile)
        fair_value = ValuationAnalyzer._estimate_fair_value(quote_data, financial_data, profile)
        margin_of_safety = ValuationAnalyzer._calculate_margin_of_safety(price, fair_value)

        return {
            'pe': pe_analysis,
            'pb': pb_analysis,
            'fair_value': fair_value,
            'margin_of_safety': margin_of_safety,
            'valuation_level': ValuationAnalyzer._assess_valuation(pe_analysis, pb_analysis),
            'industry': industry or '通用',
            'summary': ValuationAnalyzer._generate_summary(pe_analysis, pb_analysis, margin_of_safety)
        }

    @staticmethod
    def _compute_pe_percentile(history_data, eps: float, current_pe: float) -> Optional[int]:
        """
        Compute PE percentile using historical closing prices and current EPS.
        Returns an integer 0-100 or None if insufficient data.
        """
        if eps is None or eps <= 0:
            return None
        try:
            closes = history_data['close'].dropna().tolist()
            if len(closes) < 30:
                return None
            pe_series = [c / eps for c in closes if c and c > 0]
            if not pe_series:
                return None
            below = sum(1 for p in pe_series if p <= current_pe)
            return int(below / len(pe_series) * 100)
        except Exception:
            return None

    @staticmethod
    def _analyze_pe(pe_ttm: Optional[float], profile: Dict, pe_percentile: Optional[int] = None) -> Dict[str, Any]:
        if pe_ttm is None or pe_ttm <= 0:
            return {
                'value': None,
                'level': '无法评估',
                'icon': '⚪',
                'comment': 'PE 为负或无数据，无法用 PE 估值'
            }

        pe_low, pe_mid, pe_high = profile["pe"]

        if pe_ttm < pe_low:
            level, icon = '低估', '🟢'
            comment = f'PE {pe_ttm:.1f} 低于行业合理下限 {pe_low}'
        elif pe_ttm < pe_mid:
            level, icon = '偏低', '🟢'
            comment = f'PE {pe_ttm:.1f} 处于行业合理区间偏低位置 ({pe_low}-{pe_mid})'
        elif pe_ttm <= pe_high:
            level, icon = '合理', '🟡'
            comment = f'PE {pe_ttm:.1f} 在行业合理区间 ({pe_mid}-{pe_high})'
        elif pe_ttm <= pe_high * 1.3:
            level, icon = '偏高', '🟠'
            comment = f'PE {pe_ttm:.1f} 高于行业合理上限 {pe_high}'
        else:
            level, icon = '高估', '🔴'
            comment = f'PE {pe_ttm:.1f} 远超行业合理上限 {pe_high}'

        if pe_percentile is not None:
            comment += f'（近一年分位 {pe_percentile}%）'

        result = {'value': pe_ttm, 'level': level, 'icon': icon, 'comment': comment}
        if pe_percentile is not None:
            result['percentile'] = pe_percentile
        return result

    @staticmethod
    def _analyze_pb(pb: Optional[float], profile: Dict) -> Dict[str, Any]:
        if pb is None or pb <= 0:
            return {
                'value': None,
                'level': '无法评估',
                'icon': '⚪',
                'comment': 'PB 为负或无数据'
            }

        pb_low, pb_mid, pb_high = profile["pb"]

        if pb < pb_low:
            level, icon = '低估', '🟢'
            comment = f'PB {pb:.2f} 低于行业合理下限 {pb_low}'
        elif pb < pb_mid:
            level, icon = '偏低', '🟢'
            comment = f'PB {pb:.2f} 处于偏低位置 ({pb_low}-{pb_mid})'
        elif pb <= pb_high:
            level, icon = '合理', '🟡'
            comment = f'PB {pb:.2f} 在行业合理区间 ({pb_mid}-{pb_high})'
        elif pb <= pb_high * 1.3:
            level, icon = '偏高', '🟠'
            comment = f'PB {pb:.2f} 高于行业合理上限 {pb_high}'
        else:
            level, icon = '高估', '🔴'
            comment = f'PB {pb:.2f} 远超行业合理上限 {pb_high}'

        return {'value': pb, 'level': level, 'icon': icon, 'comment': comment}

    @staticmethod
    def _estimate_fair_value(
        quote_data: Dict,
        financial_data: Optional[Dict],
        profile: Dict,
    ) -> Dict[str, float]:
        price = quote_data.get('price', 0)
        eps = financial_data.get('indicators', {}).get('eps', 0) if financial_data else 0

        pe_low, pe_mid, pe_high = profile["pe"]

        if eps and eps > 0:
            fair_value_pe_low = pe_low * eps
            fair_value_pe_high = pe_high * eps
        else:
            fair_value_pe_low = price * 0.8
            fair_value_pe_high = price * 1.2

        return {
            'low': round(fair_value_pe_low, 2),
            'high': round(fair_value_pe_high, 2),
            'mid': round((fair_value_pe_low + fair_value_pe_high) / 2, 2),
            'method': 'PE 估值法（行业参数）'
        }

    @staticmethod
    def _calculate_margin_of_safety(price: float, fair_value: Dict) -> Dict[str, Any]:
        fair_mid = fair_value.get('mid', price)
        if fair_mid <= 0:
            return {'percentage': 0, 'level': '无法计算', 'icon': '⚪'}

        margin = (fair_mid - price) / fair_mid * 100

        if margin > 30:
            level, icon = '很高', '🟢'
        elif margin > 15:
            level, icon = '较高', '🟢'
        elif margin > 0:
            level, icon = '一般', '🟡'
        elif margin > -15:
            level, icon = '较低', '🟠'
        else:
            level, icon = '很低', '🔴'

        return {'percentage': round(margin, 2), 'level': level, 'icon': icon}

    @staticmethod
    def _assess_valuation(pe_analysis: Dict, pb_analysis: Dict) -> str:
        pe_level = pe_analysis.get('level', '')
        pb_level = pb_analysis.get('level', '')

        low_count = sum(1 for lv in [pe_level, pb_level] if lv in ('低估', '偏低'))
        high_count = sum(1 for lv in [pe_level, pb_level] if lv in ('高估', '偏高'))

        if low_count >= 2:
            return '低估 🟢'
        elif low_count == 1:
            return '偏低 🟢'
        elif high_count >= 2:
            return '高估 🔴'
        elif high_count == 1:
            return '偏高 🟠'
        return '合理 🟡'

    @staticmethod
    def _generate_summary(pe_analysis: Dict, pb_analysis: Dict, margin: Dict) -> str:
        parts = []
        pe_comment = pe_analysis.get('comment', '')
        pb_comment = pb_analysis.get('comment', '')
        margin_pct = margin.get('percentage', 0)

        if pe_comment:
            parts.append(pe_comment)
        if pb_comment and pb_comment != pe_comment:
            parts.append(pb_comment)
        if margin_pct > 20:
            parts.append(f"安全边际{margin_pct:.1f}%，具备投资价值")
        elif margin_pct < -20:
            parts.append(f"高估{abs(margin_pct):.1f}%，注意风险")

        return "；".join(parts) if parts else "估值水平正常"
