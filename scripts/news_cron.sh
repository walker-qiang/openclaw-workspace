#!/bin/bash
# 新闻推送定时任务脚本
# 每 5 分钟执行一次，推送最新新闻到飞书文档

WORKSPACE="/home/admin/.openclaw/workspace"
SKILL_DIR="$WORKSPACE/skills/middle-east-news"
LOG_FILE="/tmp/news_cron.log"
TIMESTAMP=$(date +'%Y-%m-%d %H:%M')
DOC_TITLE="📰 全球要闻简报 - $TIMESTAMP"

echo "[$(date)] Starting news push..." >> "$LOG_FILE"

# 生成新闻
cd "$SKILL_DIR"
python3 scripts/generate_news.py 2>&1 >> "$LOG_FILE"

if [ ! -f /tmp/news_brief.md ]; then
    echo "[$(date)] ERROR: news_brief.md not created" >> "$LOG_FILE"
    exit 1
fi

# 读取新闻内容
NEWS_CONTENT=$(cat /tmp/news_brief.md)

# 使用 openclaw agent 推送新闻到飞书文档（明确指示创建文档流程）
openclaw agent \
    --session-id "d222102e-9f21-4fa7-9a2f-ac663b2f8dcb" \
    --message "请按以下流程推送新闻：
1. 用 feishu_doc create 创建文档，标题：$DOC_TITLE
2. 用 feishu_doc write 写入新闻内容
3. 用 feishu_doc read 验证内容已写入
4. 发送文档链接给我

新闻内容如下：
$NEWS_CONTENT" \
    --deliver \
    --channel feishu \
    2>&1 >> "$LOG_FILE"

echo "[$(date)] News push completed" >> "$LOG_FILE"
echo "---" >> "$LOG_FILE"
