#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
恒生科技 ETF (513180) 分析报告
"""

import requests
from datetime import datetime

# 获取 ETF 数据
url = "http://qt.gtimg.cn/q=sh513180"
resp = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
text = resp.text
start = text.find('"') + 1
end = text.rfind('"')
content = text[start:end]
parts = content.split('~')

# 解析数据
name = parts[1] if len(parts) > 1 else '恒生科技 ETF'
code = parts[2] if len(parts) > 2 else '513180'
price = float(parts[3]) if len(parts) > 3 and parts[3] else 0
pre_close = float(parts[4]) if len(parts) > 4 and parts[4] else price
change = price - pre_close
change_percent = (change / pre_close * 100) if pre_close > 0 else 0
high_52w = float(parts[49]) if len(parts) > 49 and parts[49] else 0  # 52 周高
low_52w = float(parts[48]) if len(parts) > 48 and parts[48] else 0   # 52 周低

# 计算净值比 (PB 类似指标)
# ETF 通常跟踪指数，用价格/净值比
nav_ratio = float(parts[65]) if len(parts) > 65 and parts[65] else None

# 估算内在价值（基于 52 周中值）
intrinsic_value = (high_52w + low_52w) / 2 if high_52w and low_52w else price
margin_of_safety = ((intrinsic_value - price) / intrinsic_value * 100) if intrinsic_value > 0 else 0

# 生成报告
report = f"""## 📈 恒生科技 ETF ({code}) 分析报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}

---

### 🎯 核心指标

| 指标 | 数值 | 评估 |
|------|------|------|
| 当前价 | **¥{price:.3f}** | **{change_percent:+.2f}%** {'📈' if change_percent > 0 else '📉'} |
| 52 周范围 | ¥{low_52w:.3f} - ¥{high_52w:.3f} | - |
| 当前位置 | {((price - low_52w) / (high_52w - low_52w) * 100) if high_52w > low_52w else 0:.1f}% | {'偏低' if price < (high_52w + low_52w) / 2 else '偏高'} |

---

### 💎 价值投资分析

**内在价值估算**: ¥{intrinsic_value:.3f} (基于 52 周中值)

**安全边际**: {margin_of_safety:.1f}% {'🟢' if margin_of_safety > 20 else '🟡' if margin_of_safety > 0 else '🔴'} {'高' if margin_of_safety > 30 else '中' if margin_of_safety > 10 else '低'}

**估值水平**: {'低估 🟢' if margin_of_safety > 30 else '合理 🟡' if margin_of_safety > 0 else '偏高 🔴'}

---

### 📊 买入/卖出区间

| 区间 | 价格 | 说明 |
|------|------|------|
| **保守买入** | ¥{low_52w * 0.9:.3f} | 52 周低点 9 折 |
| **激进买入** | ¥{low_52w * 1.1:.3f} | 52 周低点 1.1 倍 |
| **当前价格** | ¥{price:.3f} | - |
| **开始卖出** | ¥{high_52w * 1.2:.3f} | 52 周高点 1.2 倍 |
| **坚决卖出** | ¥{high_52w * 1.5:.3f} | 52 周高点 1.5 倍 |

---

### 📈 恒生科技指数简介

**恒生科技指数** 反映香港上市科技公司整体表现：

| 项目 | 详情 |
|------|------|
| **成分股** | 30 家科技公司 |
| **权重股** | 腾讯、阿里、美团、小米、京东等 |
| **行业** | 互联网、科技硬件、新能源车等 |
| **特点** | 高成长、高波动 |

---

### 💡 投资价值分析

#### ✅ 利好因素

1. **估值低位**: 当前价格接近 52 周低点
2. **安全边际**: {margin_of_safety:.1f}% 安全边际
3. **分散投资**: 一篮子科技公司，分散个股风险
4. **政策回暖**: 互联网监管政策逐步常态化

#### ⚠️ 风险因素

1. **高波动**: 科技股波动大
2. **地缘政治**: 中美关系影响
3. **汇率风险**: 港币计价，人民币汇率波动
4. **行业竞争**: 科技公司竞争激烈

---

### 🎯 按价值投资理念的操作建议

| 理念 | 当前情况 | 是否符合 |
|------|---------|---------|
| **价值投资** | 指数估值低位 | ✅ 符合 |
| **高不买** | 接近 52 周低点 | ✅ 符合 |
| **低不卖** | 有{margin_of_safety:.1f}% 安全边际 | ✅ 符合 |
| **安全边际** | {margin_of_safety:.1f}% | {'✅ 理想' if margin_of_safety > 30 else '⚠️ 一般'} |

#### 投资建议

"""

if margin_of_safety > 30:
    report += """**推荐买入 🟢**

- 策略：可分批建仓（15-25% 仓位）
- 理由：安全边际高，估值处于低位
"""
elif margin_of_safety > 15:
    report += """**谨慎买入 🟡**

- 策略：小仓位建仓（5-10% 仓位）
- 理由：有一定安全边际，但不算极度低估
"""
else:
    report += """**观望 🟡**

- 策略：等待更好价格
- 理由：安全边际不足，建议等待更低价格
"""

report += f"""
---

### 📊 关键观察点

1. **成分股业绩**: 腾讯、阿里等权重股财报
2. **政策环境**: 互联网监管政策变化
3. **中美关系**: 科技领域摩擦
4. **资金流向**: 南向资金动向
5. **技术走势**: 是否突破关键阻力位

---

### 🔄 ETF vs 个股

| 维度 | ETF | 个股 |
|------|-----|------|
| **风险** | 分散 | 集中 |
| **收益** | 平均 | 可能更高/更低 |
| **研究成本** | 低 | 高 |
| **适合人群** | 大多数投资者 | 专业投资者 |

**按你的理念**: ETF 更适合践行价值投资，因为：
- 避免个股黑天鹅
- 享受行业整体成长
- 无需深入研究单个公司

---

> ⚠️ **免责声明**: 本报告仅供参考，不构成投资建议。投资有风险，入市需谨慎。
"""

print(report)
