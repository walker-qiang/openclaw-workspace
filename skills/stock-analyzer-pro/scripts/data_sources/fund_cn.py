#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基金数据源 - 使用天天基金 API（兼容 Python 3.6+）
"""

import requests
import pandas as pd
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any


class FundDataSource:
    """天天基金数据源类"""
    
    def __init__(self):
        self.cache = {}
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'http://fund.eastmoney.com/'
        })
    
    def get_fund_info(self, code: str) -> Optional[Dict[str, Any]]:
        """
        获取基金基本信息
        """
        try:
            # 获取基金基本信息
            url = f"http://fund.eastmoney.com/pingzhongdata/{code}.js"
            resp = self.session.get(url, timeout=10)
            
            if resp.status_code != 200:
                return None
                
            # 解析 JS 返回的数据
            content = resp.text
            
            # 提取基金名称
            name_match = re.search(r'fS_name\s*=\s*"([^"]+)"', content)
            name = name_match.group(1) if name_match else ''
            
            # 提取基金类型
            type_match = re.search(r'fund_type\s*=\s*"([^"]+)"', content)
            fund_type = type_match.group(1) if type_match else ''
            
            # 提取最新净值
            nav_match = re.search(r'netWorthDate\s*=\s*"([^"]+)"', content)
            nav_date = nav_match.group(1) if nav_match else ''
            
            # 获取净值数据
            nav_url = f"http://api.fund.eastmoney.com/f10/lsjz?fundCode={code}&pageIndex=1&pageSize=1"
            nav_resp = self.session.get(nav_url, timeout=5)
            nav_data = nav_resp.json() if nav_resp.status_code == 200 else {}
            
            nav = 0
            nav_change = 0
            if nav_data.get('Data'):
                latest = nav_data['Data'][0] if nav_data['Data'] else {}
                nav = float(latest.get('LJJZ', 0))
                nav_change = float(latest.get('JZZZL', 0))
            
            # 获取基金详情
            info_url = f"http://fund.eastmoney.com/{code}.html"
            info_resp = self.session.get(info_url, timeout=5)
            
            # 提取基金经理
            manager_match = re.search(r'基金经理：</span><a[^>]*>([^<]+)', info_resp.text)
            manager = manager_match.group(1).strip() if manager_match else ''
            
            # 提取基金公司
            company_match = re.search(r'基金公司：</span><a[^>]*>([^<]+)', info_resp.text)
            company = company_match.group(1).strip() if company_match else ''
            
            return {
                'code': code,
                'name': name,
                'type': fund_type,
                'manager': manager,
                'company': company,
                'establish_date': '',
                'size': '',
                'nav': nav,
                'nav_date': nav_date,
                'nav_change': nav_change,
                'source': 'eastmoney'
            }
            
        except Exception as e:
            print(f"获取基金信息失败：{e}")
            
        return None
    
    def get_nav_history(self, code: str, period: str = '1y') -> Optional[pd.DataFrame]:
        """
        获取净值历史
        """
        try:
            url = f"http://api.fund.eastmoney.com/f10/lsjz?fundCode={code}&pageIndex=1&pageSize=100"
            resp = self.session.get(url, timeout=10)
            
            if resp.status_code != 200:
                return None
                
            data = resp.json()
            if not data.get('Data'):
                return None
                
            df = pd.DataFrame(data['Data'])
            df = df.rename(columns={
                'FSRQ': 'date',
                'DWJZ': 'nav',
                'LJJZ': 'accumulated_nav',
                'JZZZL': 'change_percent'
            })
            
            return df[['date', 'nav', 'accumulated_nav', 'change_percent']]
            
        except Exception as e:
            print(f"获取净值历史失败：{e}")
            
        return None
    
    def get_holdings(self, code: str) -> Optional[Dict[str, Any]]:
        """
        获取基金持仓
        """
        try:
            url = f"http://api.fund.eastmoney.com/f10/JJCC?fundcode={code}"
            resp = self.session.get(url, timeout=10)
            
            if resp.status_code != 200:
                return None
                
            data = resp.json()
            if not data.get('Data'):
                return None
                
            stocks = data['Data']
            
            return {
                'stocks': stocks,
                'bonds': {},
                'date': stocks[0].get('PDATE', '') if stocks else ''
            }
            
        except Exception as e:
            print(f"获取持仓数据失败：{e}")
            
        return None
    
    def get_performance(self, code: str) -> Optional[Dict[str, float]]:
        """
        获取基金业绩表现
        """
        try:
            url = f"http://api.fund.eastmoney.com/f10/JJYJ?fundcode={code}"
            resp = self.session.get(url, timeout=10)
            
            if resp.status_code != 200:
                return None
                
            data = resp.json()
            
            return {
                'ytd': 0,
                '1m': 0,
                '3m': 0,
                '6m': 0,
                '1y': 0,
                '3y': 0,
                '5y': 0,
            }
            
        except Exception as e:
            print(f"获取业绩数据失败：{e}")
            
        return None
