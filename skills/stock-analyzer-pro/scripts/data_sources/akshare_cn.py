#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A 股/港股数据源 - 使用新浪财经 API（无需 akshare）
兼容 Python 3.6+
"""

import requests
import pandas as pd
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any


class AKShareDataSource:
    """新浪财经数据源类（替代 akshare）"""
    
    def __init__(self):
        self.cache = {}
        self.cache_ttl = 300  # 5 分钟缓存
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def _normalize_code(self, code: str) -> str:
        """标准化股票代码"""
        code = code.strip().upper()
        
        if code.endswith('.SH') or code.endswith('.SZ') or code.endswith('.HK'):
            return code
            
        if code.isdigit():
            if code.startswith('6'):
                return f"{code}.SH"
            elif code.startswith('0') or code.startswith('3'):
                return f"{code}.SZ"
            elif code.startswith('9'):
                return f"{code}.SH"
                
        return code
    
    def _cn_stock_code_to_sina(self, code: str) -> str:
        """转换为腾讯 API 格式：sh600519 或 hk00700"""
        code = self._normalize_code(code)
        if '.SH' in code:
            return 'sh' + code.replace('.SH', '')
        elif '.SZ' in code:
            return 'sz' + code.replace('.SZ', '')
        elif '.HK' in code:
            # 港股格式：hk00700
            hk_code = code.replace('.HK', '')
            return 'hk' + hk_code.zfill(4)  # 补齐 4 位
        return code
    
    def get_quote(self, code: str) -> Optional[Dict[str, Any]]:
        """
        获取实时行情（使用腾讯 API）
        """
        try:
            sina_code = self._cn_stock_code_to_sina(code)
            url = f"http://qt.gtimg.cn/q={sina_code}"
            
            resp = self.session.get(url, timeout=10)
            resp.raise_for_status()
            
            # 解析腾讯返回数据：v_sh600519="1~贵州茅台~600519~1393.65~..."
            text = resp.text
            start = text.find('"') + 1
            end = text.rfind('"')
            if start <= 0 or end <= start:
                return None
                
            content = text[start:end]
            parts = content.split('~')
            if len(parts) < 30:
                return None
                
            # 腾讯数据格式解析
            name = parts[1]
            price = float(parts[3]) if parts[3] else 0
            pre_close = float(parts[4]) if parts[4] else price
            open_p = float(parts[5]) if parts[5] else price
            high = float(parts[6]) if parts[6] else price
            low = float(parts[7]) if parts[7] else price
            volume = float(parts[8]) if parts[8] else 0  # 港股已经是股数
            
            # 港股和 A 股字段略有不同
            is_hk = '.HK' in code or 'hk' in sina_code
            
            if is_hk:
                # 港股字段：31=涨跌额，32=涨跌幅，39=PE, 44=市值 (亿港元), 71=PB
                change = float(parts[31]) if len(parts) > 31 and parts[31] else price - pre_close
                change_percent = float(parts[32]) if len(parts) > 32 and parts[32] else (change / pre_close * 100) if pre_close > 0 else 0
                pe_ttm = float(parts[39]) if len(parts) > 39 and parts[39] else None
                market_cap = float(parts[44]) * 1e9 if len(parts) > 44 and parts[44] else None  # 亿港元转港币
                pb = float(parts[71]) if len(parts) > 71 and parts[71] else None
                amount = volume * price  # 成交额
            else:
                # A 股字段
                change = price - pre_close
                change_percent = (change / pre_close * 100) if pre_close > 0 else 0
                pe_ttm = float(parts[39]) if len(parts) > 39 and parts[39] else None
                market_cap = float(parts[45]) * 1e8 if len(parts) > 45 and parts[45] else None  # 亿转元
                pb = float(parts[46]) if len(parts) > 46 and parts[46] else None
                amount = float(parts[37]) if len(parts) > 37 and parts[37] else 0
            
            # ROE: A 股=65, 港股=57
            roe = float(parts[57]) if len(parts) > 57 and parts[57] else None
            if not is_hk:
                roe = float(parts[65]) if len(parts) > 65 and parts[65] else roe
            
            # 52 周高低：港股=33,34 / A 股=48,49
            high_52w = float(parts[33]) if is_hk and len(parts) > 33 and parts[33] else None
            low_52w = float(parts[34]) if is_hk and len(parts) > 34 and parts[34] else None
            if not is_hk:
                high_52w = float(parts[48]) if len(parts) > 48 and parts[48] else high_52w
                low_52w = float(parts[49]) if len(parts) > 49 and parts[49] else low_52w
            
            return {
                'code': code.replace('.SH', '').replace('.SZ', '').replace('.HK', ''),
                'name': name,
                'price': price,
                'change': change,
                'change_percent': change_percent,
                'open': open_p,
                'high': high,
                'low': low,
                'pre_close': pre_close,
                'volume': volume,
                'amount': amount,
                'market_cap': market_cap,
                'pe_ttm': pe_ttm,
                'pb': pb,
                'roe': roe,
                'high_52w': high_52w,
                'low_52w': low_52w,
                'source': 'tencent'
            }
            
        except Exception as e:
            print(f"获取行情数据失败：{e}")
            
        return None
    
    def get_history(self, code: str, period: str = '1y') -> Optional[pd.DataFrame]:
        """
        获取历史行情（使用腾讯 API）
        """
        try:
            sina_code = self._cn_stock_code_to_sina(code)
            stock_code = sina_code[2:]
            market = 'sh' if 'sh' in sina_code else 'sz'
            
            # 腾讯历史数据 API
            url = f"http://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={market}{stock_code},,,,{min(365, 320)},60&fq=qfq"
            
            resp = self.session.get(url, timeout=10)
            resp.raise_for_status()
            
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
        获取 52 周高低点
        """
        history = self.get_history(code, period='1y')
        if history is None or len(history) == 0:
            return None, None
            
        high_52w = history['high'].max()
        low_52w = history['low'].min()
        
        return float(high_52w), float(low_52w)
    
    def get_financials(self, code: str) -> Optional[Dict[str, Any]]:
        """
        获取财务数据（使用腾讯 API 扩展字段）
        """
        try:
            sina_code = self._cn_stock_code_to_sina(code)
            
            # 腾讯 API 获取更详细的财务数据
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
            
            # 腾讯字段映射（详细版）
            # 完整字段参考：http://qt.gtimg.cn/q=sh600519
            # 0:类型 1:名称 2:代码 3:当前价 4:昨收 5:今开 6:最高 7:最低
            # 36:ROE 39:PE 46:PB 49:BPS
            
            price = float(parts[3]) if len(parts) > 3 and parts[3] else 0
            pre_close = float(parts[4]) if len(parts) > 4 and parts[4] else price
            
            # PE 字段：39=静态 PE, 40=动态 PE (TTM)
            pe_ttm = float(parts[40]) if len(parts) > 40 and parts[40] else None
            pe_static = float(parts[39]) if len(parts) > 39 and parts[39] else None
            pe = pe_ttm if pe_ttm else pe_static
            
            # PB 字段：46
            pb = float(parts[46]) if len(parts) > 46 and parts[46] else None
            
            # ROE 字段：A 股=65, 美股=57
            # 腾讯 A 股字段：65=ROE(百分比)
            roe = float(parts[65]) if len(parts) > 65 and parts[65] else None
            
            # BVPS 字段：49
            bvps = float(parts[49]) if len(parts) > 49 and parts[49] else None
            
            # 如果 BVPS 无效，从 PB 反推
            if (not bvps or bvps <= 0) and pb and pb > 0 and price:
                bvps = price / pb
            
            # 如果 EPS 无效，从 PE 反推
            eps = (price / pe) if pe and pe > 0 and price else None
            
            return {
                'indicators': {
                    'roe': roe if roe else 0,
                    'gross_margin': 0,
                    'net_margin': 0,
                    'debt_ratio': 0,
                    'current_ratio': 0,
                    'eps': eps if eps else 0,
                    'bvps': bvps if bvps else 0,
                    'revenue_growth': 0,
                    'profit_growth': 0,
                },
                'income': {},
                'balance': {},
                'cashflow': {},
                'report_date': datetime.now().strftime('%Y-%m-%d')
            }
            
        except Exception as e:
            print(f"获取财务数据失败：{e}")
            
        return None
    
    def get_industry_pe(self, industry: str) -> Optional[float]:
        """获取行业平均 PE（简化版）"""
        return None
