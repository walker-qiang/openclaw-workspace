#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
风险分析模块
"""

from typing import Dict, Any, List
import requests


class RiskAnalyzer:
    """风险分析器"""
    
    @staticmethod
    def analyze(code: str, quote_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析风险因素
        
        Args:
            code: 股票代码
            quote_data: 行情数据
            
        Returns:
            风险分析结果
        """
        risks = []
        warnings = []
        
        # 1. 股价波动风险
        volatility_risk = RiskAnalyzer._analyze_volatility(quote_data)
        if volatility_risk:
            risks.append(volatility_risk)
            
        # 2. 估值风险
        valuation_risk = RiskAnalyzer._analyze_valuation_risk(quote_data)
        if valuation_risk:
            risks.append(valuation_risk)
            
        # 3. 流动性风险
        liquidity_risk = RiskAnalyzer._analyze_liquidity(quote_data)
        if liquidity_risk:
            risks.append(liquidity_risk)
            
        # 4. 股东增减持（A 股）
        if '.SH' in code or '.SZ' in code:
            shareholder_risk = RiskAnalyzer._check_shareholder_changes(code)
            if shareholder_risk:
                warnings.append(shareholder_risk)
                
        # 5. 限售股解禁
        lockup_risk = RiskAnalyzer._check_lockup_expiry(code)
        if lockup_risk:
            warnings.append(lockup_risk)
            
        # 6. 股权质押
        pledge_risk = RiskAnalyzer._check_share_pledge(code)
        if pledge_risk:
            warnings.append(pledge_risk)
            
        # 计算风险等级
        risk_level = RiskAnalyzer._calculate_risk_level(risks, warnings)
        
        return {
            'level': risk_level['level'],
            'icon': risk_level['icon'],
            'risks': risks,
            'warnings': warnings,
            'summary': RiskAnalyzer._generate_summary(risks, warnings, risk_level)
        }
    
    @staticmethod
    def _analyze_volatility(quote_data: Dict) -> Dict[str, Any]:
        """分析波动风险"""
        high_52w = quote_data.get('high_52w')
        low_52w = quote_data.get('low_52w')
        price = quote_data.get('price', 0)
        
        if high_52w and low_52w and high_52w > 0 and low_52w > 0:
            range_pct = (high_52w - low_52w) / low_52w * 100
            
            if range_pct > 100:
                return {
                    'type': '高波动',
                    'level': '中',
                    'icon': '🟡',
                    'description': f'52 周波动幅度{range_pct:.1f}%，股价波动较大'
                }
            elif range_pct > 50:
                return {
                    'type': '中等波动',
                    'level': '低',
                    'icon': '🟢',
                    'description': f'52 周波动幅度{range_pct:.1f}%，波动正常'
                }
                
        return None
    
    @staticmethod
    def _analyze_valuation_risk(quote_data: Dict) -> Dict[str, Any]:
        """分析估值风险"""
        pe = quote_data.get('pe_ttm')
        
        if pe and pe > 0:
            if pe > 50:
                return {
                    'type': '高估值',
                    'level': '高',
                    'icon': '🔴',
                    'description': f'PE 高达{pe:.1f}，估值风险较高'
                }
            elif pe > 35:
                return {
                    'type': '估值偏高',
                    'level': '中',
                    'icon': '🟡',
                    'description': f'PE 为{pe:.1f}，估值处于偏高水平'
                }
                
        return None
    
    @staticmethod
    def _analyze_liquidity(quote_data: Dict) -> Dict[str, Any]:
        """分析流动性风险"""
        volume = quote_data.get('volume', 0)
        amount = quote_data.get('amount', 0)
        market_cap = quote_data.get('market_cap', 0)
        
        # 计算换手率（简化）
        if market_cap > 0:
            turnover = amount / market_cap * 100
            
            if turnover < 0.1:
                return {
                    'type': '低流动性',
                    'level': '中',
                    'icon': '🟡',
                    'description': f'换手率{turnover:.2f}%，成交不活跃'
                }
                
        return None
    
    @staticmethod
    def _check_shareholder_changes(code: str) -> Dict[str, Any]:
        """检查股东增减持（简化版）"""
        # TODO: 实现股东增减持检查
        return None
    
    @staticmethod
    def _check_lockup_expiry(code: str) -> Dict[str, Any]:
        """检查限售股解禁（简化版）"""
        # TODO: 实现限售股解禁检查
        return None
    
    @staticmethod
    def _check_share_pledge(code: str) -> Dict[str, Any]:
        """检查股权质押（简化版）"""
        # TODO: 实现股权质押检查
        return None
    
    @staticmethod
    def _calculate_risk_level(risks: List[Dict], warnings: List[Dict]) -> Dict[str, Any]:
        """计算整体风险等级"""
        high_count = sum(1 for r in risks if r.get('level') == '高')
        medium_count = sum(1 for r in risks if r.get('level') == '中')
        warning_count = len(warnings)
        
        if high_count >= 2:
            return {'level': '高风险', 'icon': '🔴'}
        elif high_count == 1 or medium_count >= 2:
            return {'level': '中等风险', 'icon': '🟡'}
        elif medium_count == 1 or warning_count >= 2:
            return {'level': '低风险', 'icon': '🟢'}
        else:
            return {'level': '极低风险', 'icon': '🟢'}
    
    @staticmethod
    def _generate_summary(risks: List[Dict], warnings: List[Dict], risk_level: Dict) -> str:
        """生成风险摘要"""
        if not risks and not warnings:
            return "暂无明显风险因素"
            
        risk_types = [r.get('type', '') for r in risks]
        warning_types = [w.get('type', '') for w in warnings]
        
        all_items = risk_types + warning_types
        
        return f"关注：{', '.join(all_items[:3])}（{risk_level['level']}）"
