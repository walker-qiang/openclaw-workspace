#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多数据源股票数据获取模块

支持数据源：
1. 腾讯 API（主数据源）
2. 新浪财经（备用）
3. 东方财富（财务数据）

优先级：腾讯 > 新浪 > 东方财富
自动 fallback 机制
"""

import requests
from typing import Dict, Any, Optional, List


class MultiSourceDataSource:
    """多数据源数据获取器"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def get_quote(self, code: str) -> Optional[Dict[str, Any]]:
        """
        获取行情数据（多数据源）
        
        Args:
            code: 股票代码
            
        Returns:
            行情数据字典
        """
        # 尝试数据源 1: 腾讯 API
        quote = self._get_from_tencent(code)
        if quote and self._validate_quote(quote):
            return quote
        
        # 尝试数据源 2: 新浪财经
        quote = self._get_from_sina(code)
        if quote and self._validate_quote(quote):
            return quote
        
        # 都失败
        return None
    
    def _get_from_tencent(self, code: str) -> Optional[Dict[str, Any]]:
        """从腾讯 API 获取数据"""
        try:
            # 转换为腾讯格式
            sina_code = self._convert_code_for_tencent(code)
            url = f"http://qt.gtimg.cn/q={sina_code}"
            
            resp = self.session.get(url, timeout=10)
            if resp.status_code != 200:
                return None
            
            text = resp.text
            start = text.find('"') + 1
            end = text.rfind('"')
            if start <= 0 or end <= start:
                return None
            
            content = text[start:end]
            parts = content.split('~')
            
            if len(parts) < 30:
                return None
            
            is_hk = '.HK' in code or 'hk' in sina_code
            
            # 解析数据
            name = parts[1]
            price = float(parts[3]) if len(parts) > 3 and parts[3] else 0
            pre_close = float(parts[4]) if len(parts) > 4 and parts[4] else price
            
            # 基础数据
            quote = {
                'code': code.replace('.SH', '').replace('.SZ', '').replace('.HK', ''),
                'name': name,
                'price': price,
                'change': price - pre_close,
                'change_percent': ((price - pre_close) / pre_close * 100) if pre_close > 0 else 0,
                'open': float(parts[5]) if len(parts) > 5 and parts[5] else price,
                'high': float(parts[6]) if len(parts) > 6 and parts[6] else price,
                'low': float(parts[7]) if len(parts) > 7 and parts[7] else price,
                'pre_close': pre_close,
                'volume': float(parts[8]) if len(parts) > 8 and parts[8] else 0,
                'source': 'tencent'
            }
            
            # PE/PB/ROE
            if is_hk:
                quote['pe_ttm'] = float(parts[39]) if len(parts) > 39 and parts[39] else None
                quote['pb'] = float(parts[71]) if len(parts) > 71 and parts[71] else None
                quote['roe'] = float(parts[57]) if len(parts) > 57 and parts[57] else None
                quote['market_cap'] = float(parts[44]) * 1e9 if len(parts) > 44 and parts[44] else None
            else:
                quote['pe_ttm'] = float(parts[39]) if len(parts) > 39 and parts[39] else None
                quote['pb'] = float(parts[46]) if len(parts) > 46 and parts[46] else None
                quote['roe'] = float(parts[65]) if len(parts) > 65 and parts[65] else None
                quote['market_cap'] = float(parts[45]) * 1e8 if len(parts) > 45 and parts[45] else None
            
            # 52 周高低（需要验证）
            high_52w = None
            low_52w = None
            
            if is_hk:
                high_52w = float(parts[33]) if len(parts) > 33 and parts[33] else None
                low_52w = float(parts[34]) if len(parts) > 34 and parts[34] else None
            else:
                high_52w = float(parts[48]) if len(parts) > 48 and parts[48] else None
                low_52w = float(parts[49]) if len(parts) > 49 and parts[49] else None
            
            # 验证 52 周数据
            if high_52w and low_52w:
                if price > high_52w * 1.1 or price < low_52w * 0.9:
                    # 数据异常，清空
                    high_52w = None
                    low_52w = None
            
            quote['high_52w'] = high_52w
            quote['low_52w'] = low_52w
            
            return quote
            
        except Exception as e:
            print(f"腾讯 API 获取失败：{e}")
            return None
    
    def _get_from_sina(self, code: str) -> Optional[Dict[str, Any]]:
        """从新浪财经获取数据（备用）"""
        try:
            # 转换为新浪格式
            sina_code = self._convert_code_for_sina(code)
            url = f"http://hq.sinajs.cn/list={sina_code}"
            
            resp = self.session.get(url, timeout=10)
            if resp.status_code != 200:
                return None
            
            text = resp.text
            # 解析：var hq_str_sh600519="名称，当前价，昨收，今开，最高，最低，..."
            match = text.split('=')[1].strip('"').split('",')
            if len(match) < 2:
                return None
            
            content = match[1] if len(match) > 1 else match[0]
            parts = content.split(',')
            
            if len(parts) < 32:
                return None
            
            name = parts[0]
            price = float(parts[3]) if parts[3] else 0
            pre_close = float(parts[2]) if parts[2] else price
            
            return {
                'code': code.replace('.SH', '').replace('.SZ', '').replace('.HK', ''),
                'name': name,
                'price': price,
                'change': price - pre_close,
                'change_percent': ((price - pre_close) / pre_close * 100) if pre_close > 0 else 0,
                'open': float(parts[1]) if parts[1] else price,
                'high': float(parts[4]) if parts[4] else price,
                'low': float(parts[5]) if parts[5] else price,
                'pre_close': pre_close,
                'volume': float(parts[8]) if parts[8] else 0,
                'pe_ttm': None,  # 新浪不直接提供
                'pb': None,
                'roe': None,
                'market_cap': None,
                'high_52w': None,
                'low_52w': None,
                'source': 'sina'
            }
            
        except Exception as e:
            print(f"新浪财经获取失败：{e}")
            return None
    
    def _validate_quote(self, quote: Dict) -> bool:
        """
        验证数据有效性
        
        Returns:
            True if valid, False otherwise
        """
        if not quote:
            return False
        
        # 必须有价格和名称
        if not quote.get('price') or not quote.get('name'):
            return False
        
        # 价格必须为正
        if quote['price'] <= 0:
            return False
        
        # 如果有 52 周数据，验证合理性
        high_52w = quote.get('high_52w')
        low_52w = quote.get('low_52w')
        price = quote['price']
        
        if high_52w and low_52w:
            if low_52w > high_52w:
                return False
            if price > high_52w * 1.1 or price < low_52w * 0.9:
                return False
        
        return True
    
    def _convert_code_for_tencent(self, code: str) -> str:
        """转换为腾讯 API 格式"""
        code = code.strip().upper()
        
        if '.HK' in code:
            hk_code = code.replace('.HK', '')
            return 'hk' + hk_code.zfill(4)
        elif '.SH' in code:
            return 'sh' + code.replace('.SH', '')
        elif '.SZ' in code:
            return 'sz' + code.replace('.SZ', '')
        elif code.startswith('6'):
            return 'sh' + code
        else:
            return 'sz' + code
    
    def _convert_code_for_sina(self, code: str) -> str:
        """转换为新浪 API 格式"""
        code = code.strip().upper()
        
        if '.HK' in code:
            # 港股新浪格式：rt_hk00700
            hk_code = code.replace('.HK', '')
            return 'rt_hk' + hk_code.zfill(4)
        elif '.SH' in code:
            return 'sh' + code.replace('.SH', '')
        elif '.SZ' in code:
            return 'sz' + code.replace('.SZ', '')
        elif code.startswith('6'):
            return 'sh' + code
        else:
            return 'sz' + code
    
    def get_history(self, code: str, period: str = '1y') -> Optional[Any]:
        """
        获取历史行情（从腾讯 API）
        返回 DataFrame 或 None
        """
        try:
            import pandas as pd
            from datetime import datetime, timedelta
            
            sina_code = self._convert_code_for_tencent(code)
            stock_code = sina_code[2:]
            market = 'sh' if 'sh' in sina_code else 'sz'
            
            # 腾讯历史数据 API
            url = f"http://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={market}{stock_code},,,,{min(365, 320)},60&fq=qfq"
            
            resp = self.session.get(url, timeout=10)
            if resp.status_code != 200:
                return None
            
            data = resp.json()
            if not data.get('data', {}).get(market + stock_code, {}).get('qfq'):
                return None
            
            klines = data['data'][market + stock_code]['qfq']
            
            kdata = []
            for k in klines:
                if len(k) >= 7:
                    kdata.append({
                        'date': k[0],
                        'open': float(k[1]) if k[1] else 0,
                        'close': float(k[2]) if k[2] else 0,
                        'high': float(k[3]) if k[3] else 0,
                        'low': float(k[4]) if k[4] else 0,
                        'volume': float(k[5]) if k[5] else 0,
                        'amount': float(k[6]) if k[6] else 0
                    })
            
            if not kdata:
                return None
            
            df = pd.DataFrame(kdata)
            return df[['date', 'open', 'high', 'low', 'close', 'volume']]
            
        except Exception as e:
            print(f"获取历史数据失败：{e}")
            return None
    
    def get_52week_range(self, code: str) -> tuple:
        """
        获取 52 周高低点（从历史数据计算）
        """
        history = self.get_history(code, period='1y')
        if history is None or len(history) == 0:
            return None, None
        
        high_52w = history['high'].max()
        low_52w = history['low'].min()
        
        return float(high_52w), float(low_52w)
    
    def get_financials(self, code: str) -> Optional[Dict[str, Any]]:
        """
        获取财务数据（从腾讯 API）
        """
        try:
            sina_code = self._convert_code_for_tencent(code)
            url = f"http://qt.gtimg.cn/q={sina_code}"
            
            resp = self.session.get(url, timeout=10)
            if resp.status_code != 200:
                return None
            
            text = resp.text
            start = text.find('"') + 1
            end = text.rfind('"')
            if start <= 0 or end <= start:
                return None
            
            content = text[start:end]
            parts = content.split('~')
            
            is_hk = '.HK' in code or 'hk' in sina_code
            
            # ROE: A 股=65, 港股=57
            roe = float(parts[57]) if len(parts) > 57 and parts[57] else None
            if not is_hk:
                roe = float(parts[65]) if len(parts) > 65 and parts[65] else roe
            
            # EPS 和 BVPS 从 PE/PB 反推
            price = float(parts[3]) if len(parts) > 3 and parts[3] else 0
            pe = float(parts[39]) if len(parts) > 39 and parts[39] else None
            pb = float(parts[46]) if len(parts) > 46 and parts[46] else None
            
            eps = (price / pe) if pe and pe > 0 else None
            bvps = (price / pb) if pb and pb > 0 else None
            
            return {
                'indicators': {
                    'roe': roe if roe else 0,
                    'eps': eps if eps else 0,
                    'bvps': bvps if bvps else 0,
                    'gross_margin': 0,  # 腾讯不提供
                    'net_margin': 0,
                    'debt_ratio': 0,
                    'current_ratio': 0,
                    'revenue_growth': 0,
                    'profit_growth': 0,
                },
                'income': {},
                'balance': {},
                'cashflow': {},
                'report_date': ''
            }
            
        except Exception as e:
            print(f"获取财务数据失败：{e}")
            return None
