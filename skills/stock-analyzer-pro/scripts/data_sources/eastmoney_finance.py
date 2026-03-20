#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
东方财富财务数据源

通过 datacenter.eastmoney.com 公开 API 获取完整财务指标，
包括毛利率、净利率、负债率、流动比率、增长率等腾讯 API 缺失的数据。
"""

import requests
from typing import Dict, Any, Optional
from datetime import datetime


class EastMoneyFinanceSource:
    """东方财富财务数据获取器"""

    _BASE_URL = (
        "https://datacenter.eastmoney.com/securities/api/data/v1/get"
    )
    _REPORT_NAME = "RPT_F10_FINANCE_MAINFINADATA"
    _COLUMNS = ",".join([
        "SECURITY_CODE", "SECURITY_NAME_ABBR", "REPORT_DATE", "REPORT_TYPE",
        "EPSJB",              # 基本每股收益
        "BPS",                # 每股净资产
        "ROEJQ",              # 加权 ROE
        "XSMLL",              # 销售毛利率
        "XSJLL",              # 销售净利率
        "ZCFZL",              # 资产负债率
        "LD",                 # 流动比率
        "SD",                 # 速动比率
        "TOTALOPERATEREVE",   # 营业总收入
        "PARENTNETPROFIT",    # 归母净利润
        "TOTALOPERATEREVETZ", # 营收同比增长 %
        "PARENTNETPROFITTZ",  # 净利润同比增长 %
        "MGJYXJJE",           # 每股经营现金流
    ])

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        })

    def _code_to_seccode(self, code: str) -> str:
        """将简码转为东方财富格式 600519 -> 600519"""
        code = code.strip().upper()
        for suffix in (".SH", ".SZ", ".HK"):
            code = code.replace(suffix, "")
        return code

    def get_financial_indicators(self, code: str) -> Optional[Dict[str, Any]]:
        """
        获取最新一期主要财务指标。

        Returns:
            与现有 financial_data['indicators'] 兼容的字典，或 None。
        """
        sec_code = self._code_to_seccode(code)
        params = {
            "reportName": self._REPORT_NAME,
            "columns": self._COLUMNS,
            "filter": f'(SECURITY_CODE="{sec_code}")',
            "pageSize": "4",
            "sortColumns": "REPORT_DATE",
            "sortTypes": "-1",
            "source": "HSF10",
            "client": "PC",
        }

        try:
            resp = self.session.get(self._BASE_URL, params=params, timeout=10)
            resp.raise_for_status()
            payload = resp.json()

            if not payload.get("success") or not payload.get("result"):
                return None

            rows = payload["result"].get("data")
            if not rows:
                return None

            latest = rows[0]
            name = latest.get("SECURITY_NAME_ABBR", "")

            roe = self._safe_float(latest.get("ROEJQ"))
            gross_margin = self._safe_float(latest.get("XSMLL"))
            net_margin = self._safe_float(latest.get("XSJLL"))
            debt_ratio = self._safe_float(latest.get("ZCFZL"))
            current_ratio = self._safe_float(latest.get("LD"))
            quick_ratio = self._safe_float(latest.get("SD"))
            eps = self._safe_float(latest.get("EPSJB"))
            bvps = self._safe_float(latest.get("BPS"))
            revenue_growth = self._safe_float(latest.get("TOTALOPERATEREVETZ"))
            profit_growth = self._safe_float(latest.get("PARENTNETPROFITTZ"))
            ocf_per_share = self._safe_float(latest.get("MGJYXJJE"))

            report_date = (latest.get("REPORT_DATE") or "")[:10]
            report_type = latest.get("REPORT_TYPE", "")

            return {
                "indicators": {
                    "roe": roe,
                    "gross_margin": gross_margin,
                    "net_margin": net_margin,
                    "debt_ratio": debt_ratio,
                    "current_ratio": current_ratio,
                    "quick_ratio": quick_ratio,
                    "eps": eps,
                    "bvps": bvps,
                    "revenue_growth": revenue_growth,
                    "profit_growth": profit_growth,
                    "ocf_per_share": ocf_per_share,
                },
                "name": name,
                "report_date": report_date,
                "report_type": report_type,
                "source": "eastmoney",
                "income": {},
                "balance": {},
                "cashflow": {},
            }

        except Exception as e:
            print(f"东方财富财务数据获取失败：{e}")
            return None

    def get_industry(self, code: str) -> Optional[str]:
        """获取股票所属行业（东方财富 EM2016 分类）"""
        sec_code = self._code_to_seccode(code)
        params = {
            "reportName": "RPT_F10_ORG_BASICINFO",
            "columns": "SECURITY_CODE,EM2016",
            "filter": f'(SECURITY_CODE="{sec_code}")',
            "pageSize": "1",
            "source": "HSF10",
            "client": "PC",
        }
        try:
            resp = self.session.get(self._BASE_URL, params=params, timeout=8)
            resp.raise_for_status()
            payload = resp.json()
            rows = (payload.get("result") or {}).get("data")
            if rows and rows[0].get("EM2016"):
                return rows[0]["EM2016"]
        except Exception:
            pass
        return None

    @staticmethod
    def _safe_float(val) -> float:
        if val is None:
            return 0.0
        try:
            return float(val)
        except (ValueError, TypeError):
            return 0.0
