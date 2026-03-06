# Stock Analyzer Pro - OpenClaw 工具定义

## 工具名称

`stock_analyze`

## 工具描述

专业股票/基金分析工具 - 提供 A 股、港股、美股、基金的全维度分析报告

## 触发关键词

当用户消息包含以下关键词时触发：

- 分析股票 / 分析基金
- XXX 股票怎么样 / XXX 基金怎么样
- 查看 XXX 的财务 / XXX 的技术面 / XXX 的估值
- 股票代码 + 分析相关词
- 具体股票名称（如：贵州茅台、腾讯控股、Apple）

## 工具调用

```bash
python3 /home/admin/.openclaw/workspace/skills/stock-analyzer-pro/openclaw_integration.py <股票代码> [市场类型]
```

### 参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| code | string | 是 | 股票代码或名称 |
| market | string | 否 | 市场类型 (auto/cn_stock/us_stock/cn_fund) |

### 返回格式

```json
{
  "markdown": "完整的 Markdown 分析报告",
  "code": "600519",
  "name": "贵州茅台",
  "price": 1393.65,
  "rating": "推荐",
  "financial_score": 75,
  "risk_level": "低风险",
  "generated_at": "2026-03-06T12:00:00"
}
```

## 使用示例

### 示例 1：分析 A 股

**用户**: 分析一下贵州茅台

**工具调用**:
```bash
python3 /home/admin/.openclaw/workspace/skills/stock-analyzer-pro/openclaw_integration.py 600519
```

### 示例 2：分析美股

**用户**: Apple 的股票怎么样

**工具调用**:
```bash
python3 /home/admin/.openclaw/workspace/skills/stock-analyzer-pro/openclaw_integration.py AAPL us_stock
```

### 示例 3：分析基金

**用户**: 易方达蓝筹精选混合

**工具调用**:
```bash
python3 /home/admin/.openclaw/workspace/skills/stock-analyzer-pro/openclaw_integration.py 000001 cn_fund
```

## 注意事项

1. **输出处理**: 返回的 `markdown` 字段可直接展示给用户
2. **错误处理**: 如果返回包含 `error` 字段，向用户显示错误信息
3. **免责声明**: 所有分析报告已包含免责声明，无需额外添加
4. **数据延迟**: 实时行情可能有 1-2 分钟延迟

## 支持的市场

| 市场 | 代码示例 | 数据源 |
|------|---------|--------|
| A 股 | 600519, 000001, 300750 | 腾讯 API |
| 港股 | 0700.HK, 9988.HK | 腾讯 API |
| 美股 | AAPL, MSFT, TSLA | Yahoo API |
| 基金 | 000001, 110022 | 天天基金 |
