#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
价值投资分析模块

基于格雷厄姆 - 巴菲特价值投资理念：
1. 内在价值估算
2. 安全边际计算
3. 低估/高估判断
4. 买入/卖出区间
"""

from typing import Dict, Any, Optional, Tuple

from scripts.analysis.valuation import _match_industry_profile, _DEFAULT_PROFILE


class ValueInvestingAnalyzer:
    """价值投资分析器"""
    
    @staticmethod
    def analyze(quote_data: Dict[str, Any], financial_data: Optional[Dict[str, Any]], industry: Optional[str] = None) -> Dict[str, Any]:
        """
        价值投资分析
        
        Args:
            quote_data: 行情数据
            financial_data: 财务数据
            
        Returns:
            价值投资分析报告
        """
        if not quote_data:
            return {'error': '缺少行情数据'}
        
        price = quote_data.get('price', 0)
        pe = quote_data.get('pe_ttm')
        pb = quote_data.get('pb')
        profile = _match_industry_profile(industry)
        
        # 1. 内在价值估算（多种方法）
        intrinsic_value = ValueInvestingAnalyzer._estimate_intrinsic_value(quote_data, financial_data, profile)
        
        # 2. 安全边际计算
        margin_of_safety = ValueInvestingAnalyzer._calculate_margin_of_safety(price, intrinsic_value)
        
        # 3. 低估/高估判断
        valuation_level = ValueInvestingAnalyzer._assess_valuation(price, intrinsic_value, pe, pb)
        
        # 4. 买入/卖出区间
        buy_zone, sell_zone = ValueInvestingAnalyzer._calculate_zones(intrinsic_value)
        
        # 5. 价值投资评分（0-100）
        value_score = ValueInvestingAnalyzer._calculate_value_score(price, intrinsic_value, pe, pb, financial_data)
        
        # 6. 投资建议
        recommendation = ValueInvestingAnalyzer._generate_recommendation(valuation_level, value_score)
        
        return {
            'intrinsic_value': intrinsic_value,
            'margin_of_safety': margin_of_safety,
            'valuation_level': valuation_level,
            'buy_zone': buy_zone,
            'sell_zone': sell_zone,
            'value_score': value_score,
            'recommendation': recommendation,
            'summary': ValueInvestingAnalyzer._generate_summary(price, intrinsic_value, margin_of_safety, valuation_level, recommendation)
        }
    
    @staticmethod
    def _estimate_intrinsic_value(quote_data: Dict, financial_data: Optional[Dict], profile: Optional[Dict] = None) -> Dict[str, float]:
        """
        估算内在价值（多种方法，使用行业参数）
        """
        if profile is None:
            profile = _DEFAULT_PROFILE

        price = quote_data.get('price', 0)
        pe = quote_data.get('pe_ttm')
        pb = quote_data.get('pb')

        # Prefer TTM EPS derived from PE_TTM (more accurate for valuation)
        eps = (price / pe) if pe and pe > 0 else None
        bvps = (price / pb) if pb and pb > 0 else None

        if financial_data and 'indicators' in financial_data:
            fin_bvps = financial_data['indicators'].get('bvps')
            if fin_bvps and fin_bvps > 0:
                bvps = fin_bvps
            if not eps:
                fin_eps = financial_data['indicators'].get('eps')
                if fin_eps and fin_eps > 0:
                    eps = fin_eps

        pe_low, pe_mid, pe_high = profile["pe"]
        pb_low, pb_mid, pb_high = profile["pb"]

        if eps and eps > 0:
            pe_value_low = eps * pe_low
            pe_value_mid = eps * pe_mid
            pe_value_high = eps * pe_high
        else:
            pe_value_low = pe_value_mid = pe_value_high = None

        if bvps and bvps > 0:
            pb_value_low = bvps * pb_low
            pb_value_mid = bvps * pb_mid
            pb_value_high = bvps * pb_high
        else:
            pb_value_low = pb_value_mid = pb_value_high = None
        
        # 方法 3: 格雷厄姆公式
        if eps and eps > 0 and bvps and bvps > 0:
            graham_value = (22.5 * eps * bvps) ** 0.5
        else:
            graham_value = None
        
        # 综合估值（取平均）
        values = [v for v in [pe_value_mid, pb_value_mid, graham_value] if v is not None]
        if values:
            comprehensive_value = sum(values) / len(values)
        else:
            comprehensive_value = price  #  fallback
        
        return {
            'pe_method': {
                'low': pe_value_low,
                'mid': pe_value_mid,
                'high': pe_value_high
            },
            'pb_method': {
                'low': pb_value_low,
                'mid': pb_value_mid,
                'high': pb_value_high
            },
            'graham_formula': graham_value,
            'comprehensive': comprehensive_value,
            'eps': eps,
            'bvps': bvps
        }
    
    @staticmethod
    def _calculate_margin_of_safety(price: float, intrinsic_value: Dict) -> Dict[str, Any]:
        """
        计算安全边际
        
        安全边际 = (内在价值 - 当前价格) / 内在价值 × 100%
        """
        iv = intrinsic_value.get('comprehensive', price)
        
        if iv <= 0:
            return {
                'percentage': 0,
                'level': '无法计算',
                'icon': '⚪',
                'comment': '内在价值无法计算'
            }
        
        margin = (iv - price) / iv * 100
        
        # 安全边际评级
        if margin >= 50:
            level = '极高'
            icon = '🟢'
            comment = '安全边际极高，极具投资价值'
        elif margin >= 30:
            level = '高'
            icon = '🟢'
            comment = '安全边际高，具备良好投资价值'
        elif margin >= 20:
            level = '中等'
            icon = '🟢'
            comment = '有一定安全边际'
        elif margin >= 10:
            level = '较低'
            icon = '🟡'
            comment = '安全边际较低，需谨慎'
        elif margin >= 0:
            level = '低'
            icon = '🟡'
            comment = '几乎没有安全边际'
        else:
            level = '负'
            icon = '🔴'
            comment = f'高估{abs(margin):.1f}%，无安全边际'
        
        return {
            'percentage': round(margin, 1),
            'level': level,
            'icon': icon,
            'comment': comment
        }
    
    @staticmethod
    def _assess_valuation(price: float, intrinsic_value: Dict, pe: Optional[float], pb: Optional[float]) -> Dict[str, Any]:
        """
        评估估值水平
        """
        iv = intrinsic_value.get('comprehensive', price)
        
        ratio = price / iv if iv > 0 else 1
        
        if ratio < 0.5:
            level = '极度低估'
            icon = '🟢'
            comment = '价格低于内在价值 50% 以上，罕见机会'
        elif ratio < 0.7:
            level = '低估'
            icon = '🟢'
            comment = '价格低于内在价值 30% 以上，值得买入'
        elif ratio < 0.85:
            level = '偏低'
            icon = '🟢'
            comment = '价格略低于内在价值，可以考虑'
        elif ratio < 1.0:
            level = '合理'
            icon = '🟡'
            comment = '价格接近内在价值，合理区间'
        elif ratio < 1.2:
            level = '偏高'
            icon = '🟠'
            comment = '价格高于内在价值 20% 以内'
        elif ratio < 1.5:
            level = '高估'
            icon = '🔴'
            comment = '价格高于内在价值 50% 以内'
        else:
            level = '严重高估'
            icon = '🔴'
            comment = '价格远高于内在价值，风险较大'
        
        return {
            'level': level,
            'icon': icon,
            'comment': comment,
            'price_to_value_ratio': round(ratio, 2)
        }
    
    @staticmethod
    def _calculate_zones(intrinsic_value: Dict) -> Tuple[Dict[str, float], Dict[str, float]]:
        """
        计算买入/卖出区间
        
        买入区：内在价值的 50%-70%
        卖出区：内在价值的 150%-200%
        """
        iv = intrinsic_value.get('comprehensive', 0)
        
        buy_zone = {
            'aggressive': round(iv * 0.7, 2),  # 激进买入价（7 折）
            'conservative': round(iv * 0.5, 2),  # 保守买入价（5 折）
            'comment': '股价跌至此区间可分批买入'
        }
        
        sell_zone = {
            'start': round(iv * 1.5, 2),  # 开始卖出价（1.5 倍）
            'aggressive': round(iv * 2.0, 2),  # 坚决卖出价（2 倍）
            'comment': '股价涨至此区间可分批卖出'
        }
        
        return buy_zone, sell_zone
    
    @staticmethod
    def _calculate_value_score(price: float, intrinsic_value: Dict, pe: Optional[float], 
                               pb: Optional[float], financial_data: Optional[Dict]) -> int:
        """
        计算价值投资评分（0-100）
        
        评分维度：
        - 安全边际（40 分）
        - PE 估值（20 分）
        - PB 估值（20 分）
        - ROE（20 分）
        """
        score = 0
        
        # 1. 安全边际评分（40 分）
        margin = ValueInvestingAnalyzer._calculate_margin_of_safety(price, intrinsic_value)
        margin_pct = margin.get('percentage', 0)
        if margin_pct >= 50:
            score += 40
        elif margin_pct >= 30:
            score += 32
        elif margin_pct >= 20:
            score += 24
        elif margin_pct >= 10:
            score += 16
        elif margin_pct >= 0:
            score += 8
        
        # 2. PE 估值评分（20 分）
        if pe and pe > 0:
            if pe < 10:
                score += 20
            elif pe < 15:
                score += 16
            elif pe < 20:
                score += 12
            elif pe < 25:
                score += 8
            elif pe < 30:
                score += 4
        
        # 3. PB 估值评分（20 分）
        if pb and pb > 0:
            if pb < 1:
                score += 20
            elif pb < 1.5:
                score += 16
            elif pb < 2:
                score += 12
            elif pb < 3:
                score += 8
            elif pb < 4:
                score += 4
        
        # 4. ROE 评分（20 分）
        if financial_data and 'indicators' in financial_data:
            roe = financial_data['indicators'].get('roe', 0)
            if roe >= 20:
                score += 20
            elif roe >= 15:
                score += 16
            elif roe >= 10:
                score += 12
            elif roe >= 5:
                score += 8
            elif roe > 0:
                score += 4
        
        return min(100, max(0, score))
    
    @staticmethod
    def _generate_recommendation(valuation_level: Dict, value_score: int) -> Dict[str, str]:
        """
        生成投资建议
        """
        level = valuation_level.get('level', '')
        
        if value_score >= 80:
            action = '强烈推荐买入'
            icon = '🟢'
            strategy = '可大仓位买入（20-30% 仓位）'
        elif value_score >= 65:
            action = '推荐买入'
            icon = '🟢'
            strategy = '可分批建仓（10-20% 仓位）'
        elif value_score >= 50:
            action = '观望'
            icon = '🟡'
            strategy = '等待更好价格，小仓位观察（5% 以内）'
        elif value_score >= 35:
            action = '谨慎持有'
            icon = '🟠'
            strategy = '持有但不加仓，考虑减仓'
        else:
            action = '建议卖出'
            icon = '🔴'
            strategy = '建议卖出或清仓'
        
        return {
            'action': action,
            'icon': icon,
            'strategy': strategy,
            'value_score': value_score
        }
    
    @staticmethod
    def _generate_summary(price: float, intrinsic_value: Dict, margin: Dict, 
                         valuation_level: Dict, recommendation: Dict) -> str:
        """
        生成价值投资摘要
        """
        iv = intrinsic_value.get('comprehensive', 0)
        margin_pct = margin.get('percentage', 0)
        
        parts = []
        
        # 内在价值
        if iv > 0:
            parts.append(f'内在价值约¥{iv:.2f}')
        
        # 安全边际
        if margin_pct > 30:
            parts.append(f'安全边际{margin_pct:.1f}%，{margin.get("level", "")}')
        elif margin_pct < 0:
            parts.append(f'高估{abs(margin_pct):.1f}%')
        
        # 估值水平
        parts.append(valuation_level.get('comment', ''))
        
        # 投资建议
        parts.append(f'建议：{recommendation.get("action", "")}')
        
        return '；'.join(parts)
