# Stock Analyzer Pro - 数据源 API 文档

## 数据源概览

本技能支持多个数据源，根据市场自动选择：

| 市场 | 数据源 | 是否需要 API Key | 覆盖率 |
|------|--------|-----------------|--------|
| A 股 | AKShare | 否 | ⭐⭐⭐⭐⭐ |
| 港股 | AKShare | 否 | ⭐⭐⭐⭐ |
| 美股 | yfinance | 否 | ⭐⭐⭐⭐⭐ |
| 基金 | AKShare | 否 | ⭐⭐⭐⭐ |

---

## AKShare 数据源 (A 股/港股/基金)

### 实时行情

```python
import akshare as ak

# A 股实时行情
df = ak.stock_zh_a_spot_em()

# 港股实时行情
df = ak.stock_hk_spot_em()

# 个股历史行情
df = ak.stock_zh_a_hist(
    symbol="000001",
    period="daily",
    start_date="20230101",
    end_date="20231231",
    adjust="qfq"  # 前复权
)
```

### 财务数据

```python
# 主要财务指标
df = ak.stock_financial_analysis_indicator(symbol="000001")

# 利润表
df = ak.stock_financial_report_sina(stock="000001", symbol="利润表")

# 资产负债表
df = ak.stock_financial_report_sina(stock="000001", symbol="资产负债表")

# 现金流量表
df = ak.stock_financial_report_sina(stock="000001", symbol="现金流量表")
```

### 基金数据

```python
# 基金基本信息
df = ak.fund_info_em(fund="000001")

# 基金净值历史
df = ak.fund_open_fund_info_em(fund="000001", indicator="单位净值走势")

# 基金持仓
df = ak.fund_portfolio_holdings_em(symbol="000001")
```

### 风险数据

```python
# 股东增减持
df = ak.stock_shareholder_change_em(symbol="000001")

# 限售股解禁
df = ak.stock_restricted_release_queue_sina(symbol="000001")

# 股权质押
df = ak.stock_shareholder_pledge_queue_em(symbol="000001")
```

---

## yfinance 数据源 (美股)

### 实时行情

```python
import yfinance as yf

ticker = yf.Ticker("AAPL")
info = ticker.info
hist = ticker.history(period="1d")
```

### 财务数据

```python
# 财务报表
income_stmt = ticker.financials
balance_sheet = ticker.balance_sheet
cashflow = ticker.cashflow

# 关键统计
pe = info.get('trailingPE')
pb = info.get('priceToBook')
roe = info.get('returnOnEquity')
```

---

## 技术指标计算

### 均线 (MA)

```python
df['MA5'] = df['close'].rolling(window=5).mean()
df['MA10'] = df['close'].rolling(window=10).mean()
df['MA20'] = df['close'].rolling(window=20).mean()
df['MA60'] = df['close'].rolling(window=60).mean()
```

### MACD

```python
exp1 = df['close'].ewm(span=12, adjust=False).mean()
exp2 = df['close'].ewm(span=26, adjust=False).mean()
df['DIF'] = exp1 - exp2
df['DEA'] = df['DIF'].ewm(span=9, adjust=False).mean()
df['MACD_hist'] = 2 * (df['DIF'] - df['DEA'])
```

### KDJ

```python
low_n = df['low'].rolling(window=9).min()
high_n = df['high'].rolling(window=9).max()
rsv = (df['close'] - low_n) / (high_n - low_n) * 100
df['K'] = rsv.ewm(com=2, adjust=False).mean()
df['D'] = df['K'].ewm(com=2, adjust=False).mean()
df['J'] = 3 * df['K'] - 2 * df['D']
```

### RSI

```python
delta = df['close'].diff()
gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
rs = gain / loss
df['RSI'] = 100 - (100 / (1 + rs))
```

### 布林带 (BOLL)

```python
df['BOLL_middle'] = df['close'].rolling(window=20).mean()
std = df['close'].rolling(window=20).std()
df['BOLL_upper'] = df['BOLL_middle'] + 2 * std
df['BOLL_lower'] = df['BOLL_middle'] - 2 * std
```

---

## 错误处理

```python
try:
    df = ak.stock_zh_a_hist(symbol="000001")
except Exception as e:
    print(f"获取数据失败：{e}")
    return None
```

---

## 性能优化

1. **数据缓存**: 对实时行情数据缓存 5 分钟
2. **批量获取**: 尽可能一次获取多个数据点
3. **异步处理**: 对于独立的数据请求，可使用 asyncio 并发

---

## 注意事项

1. AKShare 依赖网络，需要稳定的网络连接
2. 部分数据源可能有访问频率限制
3. 财务数据通常在财报发布后 1-2 天更新
4. 实时行情在交易时段每分钟更新

---

## 参考链接

- [AKShare 官方文档](https://akshare.akfamily.xyz/)
- [yfinance GitHub](https://github.com/ranaroussi/yfinance)
- [Tushare Pro](https://tushare.pro/) (可选，需要 API Token)
