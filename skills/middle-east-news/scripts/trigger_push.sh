#!/bin/bash
# 新闻推送触发脚本（供 cron 调用，写入触发文件等待 agent 处理）
#
# 环境变量：
#   OPENCLAW_WORKSPACE  工作区路径（默认 $HOME/.openclaw/workspace）

set -e

WORKSPACE="${OPENCLAW_WORKSPACE:-$HOME/.openclaw/workspace}"
LOG_FILE="$WORKSPACE/memory/news_push.log"
TRIGGER_FILE="$WORKSPACE/.trigger_news_push"

mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

log "📰 News push triggered"

cat > "$TRIGGER_FILE" << EOF
{
  "action": "push_news",
  "timestamp": "$(date -Iseconds)",
  "source": "cron"
}
EOF

log "✅ Trigger file created: $TRIGGER_FILE"
