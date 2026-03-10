#!/bin/bash
# 新闻推送脚本 - 每 5 分钟执行一次
# 用法：./news_push_5min.sh

set -e

WORKSPACE="/home/admin/.openclaw/workspace"
SKILL_DIR="$WORKSPACE/skills/middle-east-news"
OUTPUT_FILE="/tmp/news_brief_5min.md"
DOC_TITLE="📰 全球要闻简报 - $(date +'%Y-%m-%d %H:%M')"

cd "$SKILL_DIR"

# 生成新闻
python3 scripts/generate_news.py

# 读取新闻内容
NEWS_CONTENT=$(cat /tmp/news_brief.md)

# 创建飞书文档（使用 openclaw message 发送到当前会话）
# 这里通过 openclaw sessions_send 发送到主会话
openclaw sessions send --label "main" "📰 **5 分钟新闻更新**

_更新时间：$(date +'%Y-%m-%d %H:%M')_

新闻已生成，共 25 条精选新闻。

（文档创建功能需要额外配置，当前仅通知）"

echo "[$(date)] News push completed"
