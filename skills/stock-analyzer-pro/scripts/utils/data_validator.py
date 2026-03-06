#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据真实性自查模块

验证获取的数据是否合理，检测异常值
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime


class DataValidator:
    """数据验证器"""
    
    # 合理数据范围
    REASONABLE_RANGES = {
        'price': (0.01, 1000000),      # 股价：0.01 - 100 万
        'pe': (-1000, 1000),            # PE: -1000 - 1000
        'pb': (0.01, 100),              # PB: 0.01 - 100
        'change_percent': (-50, 50),    # 涨跌幅：-50% - 50%
        'roe': (-100, 200),             # ROE: -100% - 200%
        'market_cap': (1e6, 1e14),      # 市值：100 万 - 100 万亿
    }
    
    @staticmethod
    def validate_quote_data(quote_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        验证行情数据
        
        Returns:
            (是否通过验证，问题列表)
        """
        issues = []
        
        if not quote_data:
            return False, ['行情数据为空']
        
        # 检查股价
        price = quote_data.get('price')
        if price is not None:
            if price <= 0:
                issues.append(f'股价异常：{price} (应该>0)')
            elif price < DataValidator.REASONABLE_RANGES['price'][0]:
                issues.append(f'股价过低：{price}')
            elif price > DataValidator.REASONABLE_RANGES['price'][1]:
                issues.append(f'股价过高：{price}')
        
        # 检查 PE
        pe = quote_data.get('pe_ttm')
        if pe is not None:
            min_pe, max_pe = DataValidator.REASONABLE_RANGES['pe']
            if pe < min_pe or pe > max_pe:
                issues.append(f'PE 异常：{pe} (合理范围：{min_pe}-{max_pe})')
            # PE 为负表示亏损，需要特别说明
            if pe < 0:
                issues.append(f'PE 为负 ({pe})，公司处于亏损状态')
        
        # 检查 PB
        pb = quote_data.get('pb')
        if pb is not None:
            min_pb, max_pb = DataValidator.REASONABLE_RANGES['pb']
            if pb < min_pb or pb > max_pb:
                issues.append(f'PB 异常：{pb} (合理范围：{min_pb}-{max_pb})')
        
        # 检查涨跌幅
        change_pct = quote_data.get('change_percent')
        if change_pct is not None:
            min_chg, max_chg = DataValidator.REASONABLE_RANGES['change_percent']
            if change_pct < min_chg or change_pct > max_chg:
                issues.append(f'涨跌幅异常：{change_pct}%')
        
        # 检查市值
        market_cap = quote_data.get('market_cap')
        if market_cap is not None and market_cap > 0:
            min_mc, max_mc = DataValidator.REASONABLE_RANGES['market_cap']
            if market_cap < min_mc:
                issues.append(f'市值过小：{market_cap}')
            elif market_cap > max_mc:
                issues.append(f'市值过大：{market_cap}')
        
        # 检查 52 周高低点
        high_52w = quote_data.get('high_52w')
        low_52w = quote_data.get('low_52w')
        if high_52w and low_52w:
            if low_52w > high_52w:
                issues.append(f'52 周高低点异常：低点 ({low_52w}) > 高点 ({high_52w})')
            if price:
                if price > high_52w * 1.1:
                    issues.append(f'当前价 ({price}) 高于 52 周高点 ({high_52w}) 超过 10%')
                if price < low_52w * 0.9:
                    issues.append(f'当前价 ({price}) 低于 52 周低点 ({low_52w}) 超过 10%')
        
        is_valid = len(issues) == 0
        return is_valid, issues
    
    @staticmethod
    def validate_financial_data(financial_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        验证财务数据
        
        Returns:
            (是否通过验证，问题列表)
        """
        issues = []
        
        if not financial_data or 'indicators' not in financial_data:
            return False, ['财务数据为空']
        
        indicators = financial_data['indicators']
        
        # 检查 ROE
        roe = indicators.get('roe')
        if roe is not None:
            min_roe, max_roe = DataValidator.REASONABLE_RANGES['roe']
            if roe < min_roe or roe > max_roe:
                issues.append(f'ROE 异常：{roe}%')
            # ROE 过高可能是数据错误
            if roe > 100:
                issues.append(f'ROE 过高 ({roe}%)，可能是数据错误（正常应<50%）')
        
        # 检查负债率
        debt_ratio = indicators.get('debt_ratio')
        if debt_ratio is not None:
            if debt_ratio < 0:
                issues.append(f'负债率为负：{debt_ratio}%')
            elif debt_ratio > 100:
                issues.append(f'负债率超过 100%：{debt_ratio}% (资不抵债)')
        
        # 检查毛利率
        gross_margin = indicators.get('gross_margin')
        if gross_margin is not None:
            if gross_margin < -50:
                issues.append(f'毛利率异常低：{gross_margin}%')
            elif gross_margin > 90:
                issues.append(f'毛利率异常高：{gross_margin}% (可能数据错误)')
        
        # 检查增长率
        revenue_growth = indicators.get('revenue_growth')
        profit_growth = indicators.get('profit_growth')
        if revenue_growth is not None:
            if revenue_growth > 500:
                issues.append(f'营收增长异常高：{revenue_growth}%')
        if profit_growth is not None:
            if profit_growth > 1000:
                issues.append(f'利润增长异常高：{profit_growth}%')
        
        is_valid = len(issues) == 0
        return is_valid, issues
    
    @staticmethod
    def cross_validate(quote_data: Dict[str, Any], financial_data: Dict[str, Any]) -> List[str]:
        """
        交叉验证不同数据源的一致性
        
        Returns:
            问题列表
        """
        issues = []
        
        # 从 PE 和价格反推 EPS，与财务数据对比
        price = quote_data.get('price')
        pe = quote_data.get('pe_ttm')
        eps_quote = price / pe if pe and pe > 0 and price else None
        
        eps_financial = financial_data.get('indicators', {}).get('eps') if financial_data else None
        
        if eps_quote and eps_financial:
            diff_ratio = abs(eps_quote - eps_financial) / eps_financial
            if diff_ratio > 0.5:  # 差异超过 50%
                issues.append(f'EPS 数据不一致：行情数据={eps_quote:.2f}, 财务数据={eps_financial:.2f}')
        
        # 从 PB 和价格反推 BVPS，与财务数据对比
        pb = quote_data.get('pb')
        bvps_quote = price / pb if pb and pb > 0 and price else None
        
        bvps_financial = financial_data.get('indicators', {}).get('bvps') if financial_data else None
        
        if bvps_quote and bvps_financial:
            diff_ratio = abs(bvps_quote - bvps_financial) / bvps_financial
            if diff_ratio > 0.5:
                issues.append(f'BVPS 数据不一致：行情数据={bvps_quote:.2f}, 财务数据={bvps_financial:.2f}')
        
        return issues
    
    @staticmethod
    def generate_validation_report(quote_data: Dict[str, Any], financial_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成数据验证报告
        
        Returns:
            验证报告字典
        """
        quote_valid, quote_issues = DataValidator.validate_quote_data(quote_data)
        financial_valid, financial_issues = DataValidator.validate_financial_data(financial_data)
        cross_issues = DataValidator.cross_validate(quote_data, financial_data)
        
        all_issues = quote_issues + financial_issues + cross_issues
        
        # 计算可信度评分
        total_checks = 10  # 总检查项数
        failed_checks = len(all_issues)
        confidence_score = max(0, 100 - (failed_checks / total_checks * 100))
        
        if confidence_score >= 90:
            confidence_level = '高'
            icon = '🟢'
        elif confidence_score >= 70:
            confidence_level = '中'
            icon = '🟡'
        else:
            confidence_level = '低'
            icon = '🔴'
        
        return {
            'is_valid': quote_valid and financial_valid,
            'confidence_score': round(confidence_score, 1),
            'confidence_level': confidence_level,
            'icon': icon,
            'issues': all_issues,
            'quote_issues': quote_issues,
            'financial_issues': financial_issues,
            'cross_issues': cross_issues,
            'checked_at': datetime.now().isoformat()
        }
