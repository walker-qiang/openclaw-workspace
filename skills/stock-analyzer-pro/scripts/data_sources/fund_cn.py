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
        获取基金基本信息和业绩（从 pingzhongdata JS）
        """
        try:
            url = f"http://fund.eastmoney.com/pingzhongdata/{code}.js"
            resp = self.session.get(url, timeout=10)

            if resp.status_code != 200:
                return None

            content = resp.text

            def _extract(pattern, default=''):
                m = re.search(pattern, content)
                return m.group(1) if m else default

            name = _extract(r'fS_name\s*=\s*"([^"]+)"')
            fund_type = _extract(r'fund_type\s*=\s*"([^"]+)"')
            nav_date = _extract(r'netWorthDate\s*=\s*"([^"]+)"')

            syl_1m = self._safe_float(_extract(r'syl_1y="([^"]+)"', None))
            syl_3m = self._safe_float(_extract(r'syl_3y="([^"]+)"', None))
            syl_6m = self._safe_float(_extract(r'syl_6y="([^"]+)"', None))
            syl_1y = self._safe_float(_extract(r'syl_1n="([^"]+)"', None))

            nav = 0.0
            nav_trend_match = re.search(r'Data_netWorthTrend\s*=\s*\[(.*?)\];', content, re.DOTALL)
            if nav_trend_match:
                try:
                    trend_data = json.loads('[' + nav_trend_match.group(1) + ']')
                    if trend_data:
                        nav = float(trend_data[-1].get('y', 0))
                except Exception:
                    pass

            manager = ''
            mgr_start = re.search(r'Data_currentFundManager\s*=\s*\[', content)
            if mgr_start:
                nm = re.search(r'"name":"([^"]+)"', content[mgr_start.end():mgr_start.end() + 500])
                if nm:
                    manager = nm.group(1)

            company = ''
            size = ''

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
                'nav_change': 0,
                'performance': {
                    '1m': syl_1m,
                    '3m': syl_3m,
                    '6m': syl_6m,
                    '1y': syl_1y,
                },
                'source': 'eastmoney',
            }

        except Exception as e:
            print(f"获取基金信息失败：{e}")

        return None

    @staticmethod
    def _safe_float(val):
        if val is None:
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None
    
    def get_nav_history(self, code: str, period: str = '1y') -> Optional[pd.DataFrame]:
        """获取净值历史"""
        try:
            url = f"http://api.fund.eastmoney.com/f10/lsjz?fundCode={code}&pageIndex=1&pageSize=250"
            resp = self.session.get(url, timeout=10)

            if resp.status_code != 200:
                return None

            data = resp.json()
            records = None
            if isinstance(data.get('Data'), dict):
                records = data['Data'].get('LSJZList')
            elif isinstance(data.get('Data'), list):
                records = data['Data']

            if not records:
                return None

            df = pd.DataFrame(records)
            df = df.rename(columns={
                'FSRQ': 'date',
                'DWJZ': 'nav',
                'LJJZ': 'accumulated_nav',
                'JZZZL': 'change_percent',
            })

            cols = [c for c in ['date', 'nav', 'accumulated_nav', 'change_percent'] if c in df.columns]
            return df[cols] if cols else None

        except Exception as e:
            print(f"获取净值历史失败：{e}")

        return None
    
    def get_holdings(self, code: str) -> Optional[Dict[str, Any]]:
        """获取基金持仓（从 HTML 页面解析）"""
        try:
            url = f"http://fundf10.eastmoney.com/FundArchivesDatas.aspx?type=jjcc&code={code}&topline=10"
            resp = self.session.get(url, timeout=10)

            if resp.status_code != 200:
                return None

            html = resp.text
            stocks = []

            rows = re.findall(
                r'<tr><td>\d+</td>'
                r"<td><a[^>]*>([^<]+)</a></td>"                  # code
                r"<td class='tol'><a[^>]*>([^<]+)</a></td>"       # name
                r".*?"
                r"占净值<br\s*/>比例</th>.*?</thead>"
                r"|"
                r"<tr><td>\d+</td>"
                r"<td><a[^>]*>([^<]+)</a></td>"
                r"<td class='tol'><a[^>]*>([^<]+)</a></td>",
                html, re.DOTALL,
            )

            # Simpler approach: extract rows from the table
            row_pattern = re.compile(
                r'<tr><td>\d+</td>'
                r'<td><a[^>]*>(\w+)</a></td>'          # stock code
                r"<td class='tol'><a[^>]*>([^<]+)</a>"  # stock name
                r'.*?'
                r"占净值\s*(?:<br\s*/?>)?\s*比例.*?</th>"
                r"|"
                r'<tr><td>(\d+)</td>'
                r'<td><a[^>]*>(\w+)</a></td>'
                r"<td class='tol'><a[^>]*>([^<]+)</a>",
                re.DOTALL
            )

            # Use a more direct approach
            code_pattern = re.compile(
                r"<tr><td>(\d+)</td>"
                r"<td><a[^>]*>(\w+)</a></td>"
                r"<td class='tol'><a[^>]*>([^<]+)</a></td>"
                r"(?:.*?占净值.*?比例.*?|.*?)"
                r"(?:.*?<td[^>]*>([^<]*?%?)</td>)?"
            )

            # Simpler regex for each row
            for m in re.finditer(
                r"<tr><td>(\d+)</td>"                       # seq
                r"<td><a[^>]*>(\w+)</a></td>"               # code
                r"<td class='tol'><a[^>]*>([^<]+)</a></td>" # name
                r".*?</tr>",
                html, re.DOTALL
            ):
                seq, scode, sname = m.group(1), m.group(2), m.group(3)
                # Extract ratio from the row content
                row_html = m.group(0)
                ratio_match = re.search(r"(\d+\.\d+)%", row_html)
                ratio = ratio_match.group(1) if ratio_match else 'N/A'
                stocks.append({
                    '股票代码': scode,
                    '股票名称': sname,
                    '占净值比': ratio,
                })

            if not stocks:
                return None

            return {
                'stocks': stocks,
                'bonds': {},
                'date': '',
            }

        except Exception as e:
            print(f"获取持仓数据失败：{e}")

        return None
    
    def get_nav_trend(self, code: str) -> Optional[list]:
        """从 pingzhongdata 获取净值走势数据（时间戳 + 净值）"""
        try:
            url = f"http://fund.eastmoney.com/pingzhongdata/{code}.js"
            resp = self.session.get(url, timeout=10)
            if resp.status_code != 200:
                return None

            m = re.search(r'Data_netWorthTrend\s*=\s*\[(.*?)\];', resp.text, re.DOTALL)
            if not m:
                return None

            trend = json.loads('[' + m.group(1) + ']')
            return trend if trend else None
        except Exception:
            return None
