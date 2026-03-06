#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
技术分析模块
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Tuple


class TechnicalAnalyzer:
    """技术分析器"""
    
    @staticmethod
    def analyze(history_data: pd.DataFrame) -> Dict[str, Any]:
        """
        分析历史行情数据
        
        Args:
            history_data: 包含 date, open, high, low, close, volume 的 DataFrame
            
        Returns:
            技术分析结果
        """
        if history_data is None or len(history_data) < 60:
            return {'error': '数据不足，需要至少 60 个交易日数据'}
            
        df = history_data.copy()
        
        # 计算均线
        df = TechnicalAnalyzer._calculate_ma(df)
        
        # 计算 MACD
        df = TechnicalAnalyzer._calculate_macd(df)
        
        # 计算 KDJ
        df = TechnicalAnalyzer._calculate_kdj(df)
        
        # 计算 RSI
        df = TechnicalAnalyzer._calculate_rsi(df)
        
        # 计算布林带
        df = TechnicalAnalyzer._calculate_boll(df)
        
        # 获取最新数据
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        
        # 趋势判断
        trend = TechnicalAnalyzer._analyze_trend(df, latest)
        
        # 支撑/阻力位
        support_resistance = TechnicalAnalyzer._find_support_resistance(df, latest)
        
        # 信号判断
        signals = TechnicalAnalyzer._generate_signals(df, latest, prev)
        
        return {
            'trend': trend,
            'ma_analysis': TechnicalAnalyzer._analyze_ma(df, latest),
            'macd': {
                'dif': float(latest.get('DIF', 0)),
                'dea': float(latest.get('DEA', 0)),
                'histogram': float(latest.get('MACD_hist', 0)),
                'signal': TechnicalAnalyzer._interpret_macd(latest, prev)
            },
            'kdj': {
                'k': float(latest.get('KDJ_K', 0)),
                'd': float(latest.get('KDJ_D', 0)),
                'j': float(latest.get('KDJ_J', 0)),
                'signal': TechnicalAnalyzer._interpret_kdj(latest)
            },
            'rsi': {
                'rsi6': float(latest.get('RSI6', 0)),
                'rsi12': float(latest.get('RSI12', 0)),
                'rsi24': float(latest.get('RSI24', 0)),
                'signal': TechnicalAnalyzer._interpret_rsi(latest)
            },
            'boll': {
                'upper': float(latest.get('BOLL_upper', 0)),
                'middle': float(latest.get('BOLL_middle', 0)),
                'lower': float(latest.get('BOLL_lower', 0)),
                'position': TechnicalAnalyzer._analyze_boll_position(latest)
            },
            'support_resistance': support_resistance,
            'signals': signals,
            'summary': TechnicalAnalyzer._generate_summary(trend, signals)
        }
    
    @staticmethod
    def _calculate_ma(df: pd.DataFrame) -> pd.DataFrame:
        """计算均线"""
        df['MA5'] = df['close'].rolling(window=5).mean()
        df['MA10'] = df['close'].rolling(window=10).mean()
        df['MA20'] = df['close'].rolling(window=20).mean()
        df['MA60'] = df['close'].rolling(window=60).mean()
        df['MA120'] = df['close'].rolling(window=120).mean()
        df['MA250'] = df['close'].rolling(window=250).mean()
        return df
    
    @staticmethod
    def _calculate_macd(df: pd.DataFrame) -> pd.DataFrame:
        """计算 MACD"""
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['DIF'] = exp1 - exp2
        df['DEA'] = df['DIF'].ewm(span=9, adjust=False).mean()
        df['MACD_hist'] = 2 * (df['DIF'] - df['DEA'])
        return df
    
    @staticmethod
    def _calculate_kdj(df: pd.DataFrame) -> pd.DataFrame:
        """计算 KDJ"""
        low_n = df['low'].rolling(window=9).min()
        high_n = df['high'].rolling(window=9).max()
        rsv = (df['close'] - low_n) / (high_n - low_n) * 100
        df['KDJ_K'] = rsv.ewm(com=2, adjust=False).mean()
        df['KDJ_D'] = df['KDJ_K'].ewm(com=2, adjust=False).mean()
        df['KDJ_J'] = 3 * df['KDJ_K'] - 2 * df['KDJ_D']
        return df
    
    @staticmethod
    def _calculate_rsi(df: pd.DataFrame) -> pd.DataFrame:
        """计算 RSI"""
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI14'] = 100 - (100 / (1 + rs))
        
        # 计算不同周期的 RSI
        df['RSI6'] = TechnicalAnalyzer._calculate_rsi_period(df['close'], 6)
        df['RSI12'] = TechnicalAnalyzer._calculate_rsi_period(df['close'], 12)
        df['RSI24'] = TechnicalAnalyzer._calculate_rsi_period(df['close'], 24)
        return df
    
    @staticmethod
    def _calculate_rsi_period(close: pd.Series, period: int) -> pd.Series:
        """计算指定周期的 RSI"""
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    @staticmethod
    def _calculate_boll(df: pd.DataFrame) -> pd.DataFrame:
        """计算布林带"""
        df['BOLL_middle'] = df['close'].rolling(window=20).mean()
        std = df['close'].rolling(window=20).std()
        df['BOLL_upper'] = df['BOLL_middle'] + 2 * std
        df['BOLL_lower'] = df['BOLL_middle'] - 2 * std
        return df
    
    @staticmethod
    def _analyze_trend(df: pd.DataFrame, latest: pd.Series) -> Dict[str, Any]:
        """分析趋势"""
        close = latest['close']
        ma5 = latest.get('MA5', 0)
        ma10 = latest.get('MA10', 0)
        ma20 = latest.get('MA20', 0)
        ma60 = latest.get('MA60', 0)
        
        # 判断多头/空头排列
        if ma5 > ma10 > ma20 > ma60:
            trend_type = '多头'
            strength = '强'
            icon = '📈'
        elif ma5 < ma10 < ma20 < ma60:
            trend_type = '空头'
            strength = '强'
            icon = '📉'
        elif close > ma20 and ma5 > ma10:
            trend_type = '多头'
            strength = '中'
            icon = '📈'
        elif close < ma20 and ma5 < ma10:
            trend_type = '空头'
            strength = '中'
            icon = '📉'
        else:
            trend_type = '震荡'
            strength = '弱'
            icon = '➡️'
            
        return {
            'type': trend_type,
            'strength': strength,
            'icon': icon,
            'description': f"{trend_type}趋势（{strength}）"
        }
    
    @staticmethod
    def _analyze_ma(df: pd.DataFrame, latest: pd.Series) -> Dict[str, Any]:
        """分析均线"""
        close = latest['close']
        ma5 = latest.get('MA5', 0)
        ma10 = latest.get('MA10', 0)
        ma20 = latest.get('MA20', 0)
        
        position = []
        if close > ma5:
            position.append('站上 5 日线')
        else:
            position.append('跌破 5 日线')
            
        if close > ma10:
            position.append('站上 10 日线')
        else:
            position.append('跌破 10 日线')
            
        if close > ma20:
            position.append('站上 20 日线')
        else:
            position.append('跌破 20 日线')
            
        return {
            'position': position,
            'ma5': float(ma5),
            'ma10': float(ma10),
            'ma20': float(ma20),
            'ma60': float(latest.get('MA60', 0))
        }
    
    @staticmethod
    def _interpret_macd(latest: pd.Series, prev: pd.Series) -> Dict[str, Any]:
        """解读 MACD 信号"""
        dif = latest.get('DIF', 0)
        dea = latest.get('DEA', 0)
        hist = latest.get('MACD_hist', 0)
        prev_hist = prev.get('MACD_hist', 0)
        
        if dif > dea and prev_hist <= 0:
            return {'signal': '金叉', 'icon': '🟢', 'comment': 'MACD 金叉，看涨信号'}
        elif dif < dea and prev_hist >= 0:
            return {'signal': '死叉', 'icon': '🔴', 'comment': 'MACD 死叉，看跌信号'}
        elif hist > 0:
            return {'signal': '多头', 'icon': '🟢', 'comment': 'MACD 红柱，多头强势'}
        elif hist < 0:
            return {'signal': '空头', 'icon': '🔴', 'comment': 'MACD 绿柱，空头强势'}
        else:
            return {'signal': '中性', 'icon': '⚪', 'comment': 'MACD 方向不明'}
    
    @staticmethod
    def _interpret_kdj(latest: pd.Series) -> Dict[str, Any]:
        """解读 KDJ 信号"""
        k = latest.get('KDJ_K', 0)
        d = latest.get('KDJ_D', 0)
        j = latest.get('KDJ_J', 0)
        
        if k > 80 and d > 80:
            return {'signal': '超买', 'icon': '🔴', 'comment': 'KDJ 超买区，警惕回调'}
        elif k < 20 and d < 20:
            return {'signal': '超卖', 'icon': '🟢', 'comment': 'KDJ 超卖区，可能反弹'}
        elif k > d:
            return {'signal': '金叉', 'icon': '🟢', 'comment': 'KDJ 金叉，看涨'}
        elif k < d:
            return {'signal': '死叉', 'icon': '🔴', 'comment': 'KDJ 死叉，看跌'}
        else:
            return {'signal': '中性', 'icon': '⚪', 'comment': 'KDJ 方向不明'}
    
    @staticmethod
    def _interpret_rsi(latest: pd.Series) -> Dict[str, Any]:
        """解读 RSI 信号"""
        rsi = latest.get('RSI14', 50)
        
        if rsi > 70:
            return {'signal': '超买', 'icon': '🔴', 'comment': 'RSI 超买，可能回调'}
        elif rsi < 30:
            return {'signal': '超卖', 'icon': '🟢', 'comment': 'RSI 超卖，可能反弹'}
        elif rsi > 50:
            return {'signal': '强势', 'icon': '🟢', 'comment': 'RSI 在 50 以上，多头强势'}
        else:
            return {'signal': '弱势', 'icon': '🔴', 'comment': 'RSI 在 50 以下，空头弱势'}
    
    @staticmethod
    def _analyze_boll_position(latest: pd.Series) -> str:
        """分析布林带位置"""
        close = latest['close']
        upper = latest.get('BOLL_upper', 0)
        middle = latest.get('BOLL_middle', 0)
        lower = latest.get('BOLL_lower', 0)
        
        if close >= upper:
            return '触及上轨（可能回调）'
        elif close >= middle:
            return '中轨上方（偏强）'
        elif close >= lower:
            return '中轨下方（偏弱）'
        else:
            return '触及下轨（可能反弹）'
    
    @staticmethod
    def _find_support_resistance(df: pd.DataFrame, latest: pd.Series) -> Dict[str, float]:
        """寻找支撑位和阻力位"""
        # 近期高低点
        recent_high = df['high'].tail(20).max()
        recent_low = df['low'].tail(20).min()
        
        # 均线支撑/阻力
        ma20 = latest.get('MA20', 0)
        ma60 = latest.get('MA60', 0)
        
        # 整数关口
        close = latest['close']
        round_num = round(close / 10) * 10
        
        return {
            'resistance_1': float(recent_high),
            'resistance_2': float(max(ma60, recent_high * 1.05)),
            'support_1': float(recent_low),
            'support_2': float(min(ma20, recent_low * 0.95)),
            'psychological': float(round_num)
        }
    
    @staticmethod
    def _generate_signals(df: pd.DataFrame, latest: pd.Series, prev: pd.Series) -> list:
        """生成交易信号"""
        signals = []
        
        # 均线信号
        if latest['close'] > latest.get('MA5', 0) and prev['close'] <= prev.get('MA5', 0):
            signals.append({'type': '买入', 'reason': '站上 5 日均线', 'strength': '中'})
        elif latest['close'] < latest.get('MA5', 0) and prev['close'] >= prev.get('MA5', 0):
            signals.append({'type': '卖出', 'reason': '跌破 5 日均线', 'strength': '中'})
            
        # MACD 信号
        if latest.get('DIF', 0) > latest.get('DEA', 0) and prev.get('DIF', 0) <= prev.get('DEA', 0):
            signals.append({'type': '买入', 'reason': 'MACD 金叉', 'strength': '强'})
        elif latest.get('DIF', 0) < latest.get('DEA', 0) and prev.get('DIF', 0) >= prev.get('DEA', 0):
            signals.append({'type': '卖出', 'reason': 'MACD 死叉', 'strength': '强'})
            
        return signals
    
    @staticmethod
    def _generate_summary(trend: Dict, signals: list) -> str:
        """生成技术分析摘要"""
        trend_desc = trend.get('description', '')
        signal_count = len(signals)
        
        if signal_count == 0:
            return f"当前{trend_desc}，暂无明确交易信号"
        else:
            latest_signal = signals[-1]
            return f"当前{trend_desc}，最新信号：{latest_signal['type']}（{latest_signal['reason']}）"
