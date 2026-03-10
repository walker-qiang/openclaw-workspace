---
name: middle-east-news
description: 新闻收集与推送技能。直接从权威新闻网站抓取内容，生成包含详细摘要的新闻简报，支持飞书文档推送。
---

# News Collector - 新闻收集与推送技能

直接从权威新闻网站抓取新闻，生成**详细摘要版**新闻简报，自动创建飞书文档并推送。

## 功能特点

1. **智能抓取** - 从 20+ 权威新闻源自动抓取
2. **详细摘要** - 每条新闻包含 100-300 字详细说明
3. **五大领域** - 政治、经济、军事、科技、AI 各 5 条
4. **飞书文档** - 自动创建格式化的飞书文档
5. **定时推送** - 支持 OpenClaw cron 定时任务

## 新闻源

| 领域 | 来源 |
|------|------|
| 🏛️ 政治 | Google News、新华网、环球网、澎湃新闻、联合早报 |
| 💰 经济 | 财新网、一财网、彭博社中文、金融时报中文 |
| ⚔️ 军事 | 网易军事、环球网军事、新华网军事 |
| 🔬 科技 | 钛媒体、36 氪、虎嗅、晚点 LatePost |
| 🤖 AI | 量子位、机器之心、新智元、AI 前线 |

## 核心脚本

| 脚本 | 用途 |
|------|------|
| `generate_news.py` | 核心新闻抓取脚本（38KB） |
| `fetch_news.py` | 新闻抓取模块 |
| `push_news.py` | 推送逻辑 |
| `push_to_feishu_doc.py` | 飞书文档推送 |
| `trigger_push.sh` | 定时任务触发脚本 |

## 使用方法

### 方式一：手动执行

```bash
# 1. 生成新闻简报
cd /home/admin/.openclaw/workspace/skills/middle-east-news/scripts
python3 generate_news.py

# 输出：/tmp/news_brief.md
```

### 方式二：OpenClaw cron 定时推送（推荐）

```bash
# 查看当前配置
openclaw cron list

# 修改推送时间（如每天早上 8 点）
openclaw cron edit <job-id> --cron "0 8 * * *"

# 手动触发测试
openclaw cron run <job-id>
```

### 方式三：Agent 自动执行

发送消息："推送新闻" 或 "生成新闻简报"

Agent 会自动执行完整流程：
1. 运行 `generate_news.py` 生成新闻
2. 使用 `feishu_doc create` 创建文档（只设标题）
3. 使用 `feishu_doc write` 写入新闻内容
4. 使用 `feishu_doc read` 验证内容已写入
5. 发送文档链接到当前会话

## ⚠️ 重要注意事项

### feishu_doc 使用陷阱

**`feishu_doc create` 的 `content` 参数不会实际写入内容！**

正确流程：
```bash
# 1. 创建文档（只设标题）
feishu_doc create --title "📰 全球要闻简报 - 2026 年 03 月 10 日"
# 返回：doc_token

# 2. 写入内容
feishu_doc write --doc_token <token> --content <markdown>

# 3. 验证
feishu_doc read --doc_token <token>
# 确认 block_count > 1

# 4. 发送链接
message send --channel feishu --message "📰 新闻简报：https://feishu.cn/docx/<token>"
```

### 飞书消息推送

isolated session 中无法直接使用 `message send` 到飞书，需要：
- 明确指定 `--target user:ou_xxx` 或 `--target chat:chat_id`
- 或使用 `sessions_send` 发送到主会话

## 输出格式

```markdown
# 📰 全球要闻简报

**日期**：2026 年 03 月 10 日 星期二
**农历**：正月廿一

_更新时间：2026-03-10 08:00_

---

## 🏛️ 政治

### 1. 新闻标题

**来源**：Google News 国际

**摘要**：详细说明 100-300 字，包含事件背景、关键信息、后续影响等。

### 2. 另一条新闻...

---

## 💡 微语

> 人生没有白走的路，每一步都算数。

---

**共 25 条精选新闻 · AI 深度摘要版**
```

## 定时任务配置示例

```bash
# 每天早上 8 点推送
openclaw cron add --name "每日新闻推送" \
  --cron "0 8 * * *" \
  --message "请执行新闻推送流程：
1. 运行 generate_news.py 生成新闻
2. 读取 /tmp/news_brief.md
3. feishu_doc create 创建文档（只设标题）
4. feishu_doc write 写入内容
5. feishu_doc read 验证
6. 使用 message send --channel feishu --target user:ou_xxx 发送文档链接" \
  --session isolated \
  --no-deliver \
  --tz "Asia/Shanghai"
```

## 故障排查

### 新闻抓取失败
- 检查网络连接
- 检查 SearXNG 服务是否运行（军事/AI 新闻依赖搜索）
- 查看日志：`cat /home/admin/.openclaw/workspace/memory/news_cron.log`

### 文档创建成功但内容为空
- 确认使用了 `feishu_doc write` 而不是只靠 `create` 的 content 参数
- 验证：`feishu_doc read --doc_token <token>` 检查 block_count

### 消息推送失败
- isolated session 需要明确指定 `--target`
- 检查飞书 open_id 是否正确

## 相关文件

- 新闻数据：`/tmp/news_brief.md`
- 推送日志：`/home/admin/.openclaw/workspace/memory/news_cron.log`
- 触发文件：`/home/admin/.openclaw/workspace/.trigger_news_push`
