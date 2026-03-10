#!/bin/bash
# 新闻推送触发脚本
# 用途：被 cron 调用，触发新闻推送流程

set -e

WORKSPACE="/home/admin/.openclaw/workspace"
LOG_FILE="$WORKSPACE/memory/news_push.log"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

log "========================================="
log "📰 新闻推送触发"
log "========================================="

# 创建触发文件，包含推送请求
TRIGGER_FILE="$WORKSPACE/.trigger_news_push"
cat > "$TRIGGER_FILE" << EOF
{
  "action": "push_news",
  "timestamp": "$(date -Iseconds)",
  "source": "cron"
}
EOF

log "✅ 触发文件已创建：$TRIGGER_FILE"
log "等待 OpenClaw agent 处理..."

# 脚本退出，由 OpenClaw agent 处理后续流程
