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

            def _f(idx):
                """Safely parse a float from parts[idx]."""
                if idx < len(parts) and parts[idx]:
                    try:
                        return float(parts[idx])
                    except ValueError:
                        return None
                return None

            name = parts[1]
            price = _f(3) or 0
            pre_close = _f(4) or price

            if is_hk:
                quote = {
                    'code': code.replace('.HK', ''),
                    'name': name,
                    'price': price,
                    'change': price - pre_close,
                    'change_percent': ((price - pre_close) / pre_close * 100) if pre_close > 0 else 0,
                    'open': _f(5) or price,
                    'high': _f(33) or price,
                    'low': _f(34) or price,
                    'pre_close': pre_close,
                    'volume': _f(36) or _f(29) or 0,
                    'pe_ttm': _f(39),
                    'pb': _f(58),
                    'roe': _f(65),
                    'market_cap': (_f(44) or 0) * 1e8 if _f(44) else None,
                    'high_52w': _f(48),
                    'low_52w': _f(49),
                    'source': 'tencent',
                }
            else:
                quote = {
                    'code': code.replace('.SH', '').replace('.SZ', ''),
                    'name': name,
                    'price': price,
                    'change': price - pre_close,
                    'change_percent': ((price - pre_close) / pre_close * 100) if pre_close > 0 else 0,
                    'open': _f(5) or price,
                    'high': _f(33) or price,
                    'low': _f(34) or price,
                    'pre_close': pre_close,
                    'volume': _f(36) or _f(6) or 0,
                    'pe_ttm': _f(39),
                    'pb': _f(46),
                    'roe': _f(65),
                    'market_cap': (_f(45) or 0) * 1e8 if _f(45) else None,
                    'high_52w': _f(67),
                    'low_52w': _f(68),
                    'source': 'tencent',
                }
            
            return quote
            
        except Exception as e:
            print(f"腾讯 API 获取失败：{e}")
            return None
    
    def _get_from_sina(self, code: str) -> Optional[Dict[str, Any]]:
        """从新浪财经获取数据（备用）"""
        try:
            sina_code = self._convert_code_for_sina(code)
            url = f"http://hq.sinajs.cn/list={sina_code}"

            resp = self.session.get(url, timeout=10, headers={
                "Referer": "http://finance.sina.com.cn",
            })
            if resp.status_code != 200:
                return None

            # Sina returns GBK-encoded text: var hq_str_sh600519="name,open,preclose,price,high,low,...\n";
            text = resp.content.decode('gbk', errors='ignore')
            eq_pos = text.find('=')
            if eq_pos < 0:
                return None
            data_str = text[eq_pos + 2:].rstrip().rstrip(';').strip('"')
            parts = data_str.split(',')

            if len(parts) < 32:
                return None

            name = parts[0]
            open_p = float(parts[1]) if parts[1] else 0
            pre_close = float(parts[2]) if parts[2] else 0
            price = float(parts[3]) if parts[3] else 0
            high = float(parts[4]) if parts[4] else price
            low = float(parts[5]) if parts[5] else price
            volume = float(parts[8]) if parts[8] else 0
            amount = float(parts[9]) if parts[9] else 0

            if price <= 0:
                return None

            return {
                'code': code.replace('.SH', '').replace('.SZ', '').replace('.HK', ''),
                'name': name,
                'price': price,
                'change': price - pre_close,
                'change_percent': ((price - pre_close) / pre_close * 100) if pre_close > 0 else 0,
                'open': open_p if open_p > 0 else price,
                'high': high,
                'low': low,
                'pre_close': pre_close,
                'volume': volume,
                'amount': amount,
                'pe_ttm': None,
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
            return 'hk' + hk_code.zfill(5)
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
            return 'rt_hk' + hk_code.zfill(5)
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
        获取历史行情（从腾讯 kline API）
        统一使用 kline/kline 端点，支持 A 股和港股
        """
        try:
            import pandas as pd

            tencent_code = self._convert_code_for_tencent(code)
            url = (
                f"http://web.ifzq.gtimg.cn/appstock/app/kline/kline"
                f"?param={tencent_code},day,,,320"
            )

            resp = self.session.get(url, timeout=10)
            if resp.status_code != 200:
                return None

            data = resp.json()
            entry = data.get('data', {}).get(tencent_code, {})

            klines = entry.get('day') or entry.get('qfq') or entry.get('')
            if not klines:
                return None

            kdata = []
            for k in klines:
                if len(k) >= 6:
                    kdata.append({
                        'date': k[0],
                        'open': float(k[1]) if k[1] else 0,
                        'close': float(k[2]) if k[2] else 0,
                        'high': float(k[3]) if k[3] else 0,
                        'low': float(k[4]) if k[4] else 0,
                        'volume': float(k[5]) if k[5] else 0,
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
        """获取财务数据（从腾讯 API，仅 PE/PB/ROE）"""
        try:
            tencent_code = self._convert_code_for_tencent(code)
            url = f"http://qt.gtimg.cn/q={tencent_code}"

            resp = self.session.get(url, timeout=10)
            if resp.status_code != 200:
                return None

            text = resp.content.decode('gbk', errors='ignore')
            start = text.find('"') + 1
            end = text.rfind('"')
            if start <= 0 or end <= start:
                return None

            parts = text[start:end].split('~')
            is_hk = tencent_code.startswith('hk')

            def _f(idx):
                if idx < len(parts) and parts[idx]:
                    try:
                        return float(parts[idx])
                    except ValueError:
                        return None
                return None

            price = _f(3) or 0
            pe = _f(39)
            pb = _f(58) if is_hk else _f(46)
            roe = _f(65)

            eps = (price / pe) if pe and pe > 0 else None
            bvps = (price / pb) if pb and pb > 0 else None

            return {
                'indicators': {
                    'roe': roe or 0,
                    'eps': eps or 0,
                    'bvps': bvps or 0,
                    'gross_margin': 0,
                    'net_margin': 0,
                    'debt_ratio': 0,
                    'current_ratio': 0,
                    'revenue_growth': 0,
                    'profit_growth': 0,
                },
                'income': {},
                'balance': {},
                'cashflow': {},
                'report_date': '',
            }

        except Exception as e:
            print(f"获取财务数据失败：{e}")
            return None
