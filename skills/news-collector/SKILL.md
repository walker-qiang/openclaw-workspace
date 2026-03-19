---
name: news-collector
description: 新闻收集与推送技能。从权威新闻源抓取内容，生成五大领域（政治、经济、军事、科技、AI）的精炼摘要简报，支持飞书文档推送。
---

# News Collector - 新闻收集与推送技能

从权威新闻源抓取新闻，生成**精炼摘要版**新闻简报，自动创建飞书文档并推送。

## 功能特点

1. **智能抓取** - 从权威新闻源白名单自动抓取
2. **精炼摘要** - 每条新闻包含 50-80 字精炼摘要（主谓宾结构，数据优先）
3. **五大领域** - 政治、经济、军事、科技、AI 各 5 条
4. **飞书文档** - 自动创建格式化的飞书文档（create → write → read 验证）
5. **定时推送** - 支持 cron 定时任务
6. **并行抓取** - 多线程并发抓取，提升性能
7. **自动重试** - 网络请求失败自动重试

## 新闻源

| 领域 | 来源 |
|------|------|
| 🏛️ 政治 | 澎湃新闻、观察者网、联合早报、央视新闻 |
| 💰 经济 | 财新网、彭博社中文、金融时报中文、一财网、21 世纪经济报道 |
| ⚔️ 军事 | 网易军事、新浪军事、腾讯军事、中国军网 |
| 🔬 科技 | 36 氪、虎嗅、钛媒体 |
| 🤖 AI | 量子位、机器之心、新智元、AI 前线 |

## 文件结构

```
scripts/
├── generate_news.py       # 核心：新闻抓取 + 分类 + 摘要生成 → /tmp/news_brief.md
├── push.py                # 统一推送入口：generate → feishu create → write → read → send
├── daily_push.sh          # cron 入口（调用 push.py）
└── trigger_push.sh        # 触发文件方式（写 .trigger_news_push 等 agent 处理）
config.json                # 新闻源、关键词、微语库等配置
```

## 使用方法

### 方式一：手动执行（仅生成）

```bash
cd skills/news-collector/scripts
python3 generate_news.py
# 输出：/tmp/news_brief.md
```

### 方式二：生成 + 推送飞书

```bash
python3 push.py                 # 生成新闻 + 推送飞书文档
python3 push.py --dry-run       # 只生成，不推送
python3 push.py --skip-generate # 跳过生成，直接推送已有文件
```

### 方式三：cron 定时推送

```bash
./daily_push.sh
```

### 方式四：Agent 自动执行

发送消息："推送新闻" 或 "生成新闻简报"

Agent 会自动执行 push.py 完成完整流程。

## 环境变量

所有脚本通过环境变量配置，均有合理默认值：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `OPENCLAW_WORKSPACE` | `$HOME/.openclaw/workspace` | 工作区路径 |
| `OPENCLAW_BIN` | `openclaw` | openclaw 二进制路径 |
| `SEARXNG_URL` | `http://localhost:8080` | SearXNG 搜索引擎地址 |
| `FEISHU_USER_ID` | (空) | 飞书用户 open_id（用于定向推送） |
| `NEWS_OUTPUT` | `/tmp/news_brief.md` | 新闻简报输出路径 |

## 飞书文档推送流程

**重要**：`feishu_doc create` 的 `content` 参数不会实际写入内容！

正确流程（已在 `push.py` 中实现）：

1. `feishu_doc create --title "..."` → 获取 doc_token
2. `feishu_doc write --doc_token TOKEN --content CONTENT` → 写入内容
3. `feishu_doc read --doc_token TOKEN` → 验证 block_count > 1
4. 发送文档链接（验证失败时会发出警告）

## 输出格式

```markdown
# 📰 全球要闻简报

**日期**：2026 年 03 月 19 日 星期四

_更新时间：2026-03-19 08:00_

---

## 🏛️ 政治

### 1. 新闻标题

**来源**：澎湃新闻

**摘要**：50-80 字精炼摘要...

---

## 💡 微语

> 人生没有白走的路，每一步都算数。

---

**共 25 条精选新闻 · AI 精炼摘要版**
```

## 故障排查

### 新闻抓取失败
- 检查网络连接
- 检查 SearXNG 服务是否运行：`curl $SEARXNG_URL`
- 查看日志：`cat $OPENCLAW_WORKSPACE/memory/news_cron.log`

### 文档创建成功但内容为空
- 确认使用了 `push.py`（已内置 create → write → read 验证）
- 手动验证：`openclaw feishu_doc read --doc_token TOKEN`

### 消息推送失败
- isolated session 需要设置 `FEISHU_USER_ID` 环境变量
- 或使用 `sessions_send` 到主会话（push.py 会自动回退）

## 相关文件

- 新闻输出：`/tmp/news_brief.md`（可通过 `NEWS_OUTPUT` 环境变量配置）
- 推送日志：`$OPENCLAW_WORKSPACE/memory/news_push.log`
- Cron 日志：`$OPENCLAW_WORKSPACE/memory/news_cron.log`
- 触发文件：`$OPENCLAW_WORKSPACE/.trigger_news_push`
