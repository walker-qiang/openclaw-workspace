#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
美股数据源 - 使用 Yahoo Finance API（兼容 Python 3.6+）
"""

import requests
import pandas as pd
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any


class YFinanceDataSource:
    """Yahoo Finance 数据源类（使用直接 API 调用）"""
    
    def __init__(self):
        self.cache = {}
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def get_quote(self, code: str) -> Optional[Dict[str, Any]]:
        """
        获取美股实时行情（使用腾讯 API）
        """
        try:
            # 腾讯美股 API
            url = f"http://qt.gtimg.cn/q=us{code}"
            
            resp = self.session.get(url, timeout=10)
            resp.raise_for_status()
            
            text = resp.text
            start = text.find('"') + 1
            end = text.rfind('"')
            if start <= 0 or end <= start:
                return None
                
            content = text[start:end]
            parts = content.split('~')
            
            if len(parts) < 50:
                return None
            
            # 腾讯美股字段映射（根据实际返回）
            name = parts[1] if len(parts) > 1 else code
            price = float(parts[3]) if len(parts) > 3 and parts[3] else 0
            pre_close = float(parts[4]) if len(parts) > 4 and parts[4] else price
            # 美股腾讯 API 字段不同，简化处理
            open_p = price
            high = float(parts[33]) if len(parts) > 33 and parts[33] else price
            low = float(parts[34]) if len(parts) > 34 and parts[34] else price
            volume = float(parts[6]) if len(parts) > 6 and parts[6] else 0
            
            change = price - pre_close
            change_percent = (change / pre_close * 100) if pre_close > 0 else 0
            
            # PE: 39
            pe_ttm = float(parts[39]) if len(parts) > 39 and parts[39] else None
            
            # PB: 64
            pb = float(parts[64]) if len(parts) > 64 and parts[64] else None
            
            # ROE: 57
            roe = float(parts[57]) if len(parts) > 57 and parts[57] else None
            
            # 市值：45 (亿美元)
            market_cap = float(parts[45]) * 1e9 if len(parts) > 45 and parts[45] else 0  # 美元
            
            # 52 周高低：48, 49
            high_52w = float(parts[48]) if len(parts) > 48 and parts[48] else None
            low_52w = float(parts[49]) if len(parts) > 49 and parts[49] else None
            
            # 从 PE 反推 EPS
            eps = (price / pe_ttm) if pe_ttm and pe_ttm > 0 else None
            
            return {
                'code': code,
                'name': name,
                'price': price,
                'change': change,
                'change_percent': change_percent,
                'open': open_p,
                'high': high,
                'low': low,
                'volume': volume,
                'market_cap': market_cap,
                'pe_ttm': pe_ttm,
                'pb': pb,
                'roe': roe,
                'eps': eps,
                'dividend_yield': None,
                'high_52w': high_52w,
                'low_52w': low_52w,
                'beta': None,
                'source': 'tencent'
            }
            
        except Exception as e:
            print(f"获取美股行情失败：{e}")
            
        return None
    
    def get_history(self, code: str, period: str = '1y') -> Optional[pd.DataFrame]:
        """
        获取历史行情
        """
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{code}"
            params = {
                'interval': '1d',
                'range': period
            }
            
            resp = self.session.get(url, params=params, timeout=10)
            resp.raise_for_status()
            
            data = resp.json()
            if not data.get('chart', {}).get('result'):
                return None
                
            result = data['chart']['result'][0]
            quote = result.get('indicators', {}).get('quote', [{}])[0]
            timestamp = result.get('timestamp', [])
            
            df = pd.DataFrame({
                'date': [datetime.fromtimestamp(ts).strftime('%Y-%m-%d') for ts in timestamp],
                'open': quote.get('open', []),
                'high': quote.get('high', []),
                'low': quote.get('low', []),
                'close': quote.get('close', []),
                'volume': quote.get('volume', [])
            })
            
            return df
            
        except Exception as e:
            print(f"获取历史数据失败：{e}")
            
        return None
    
    def get_financials(self, code: str) -> Optional[Dict[str, Any]]:
        """
        获取财务数据（简化版）
        """
        return {
            'indicators': {
                'roe': 0,
                'gross_margin': 0,
                'net_margin': 0,
                'debt_ratio': 0,
                'eps': 0,
                'revenue_growth': 0,
            },
            'income': {},
            'balance': {},
            'cashflow': {},
            'report_date': datetime.now().strftime('%Y-%m-%d')
        }
    
    def get_52week_range(self, code: str) -> tuple:
        """
        获取 52 周高低点
        """
        quote = self.get_quote(code)
        if quote:
            return quote.get('high_52w'), quote.get('low_52w')
        return None, None
