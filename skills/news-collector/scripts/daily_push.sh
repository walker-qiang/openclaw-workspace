#!/bin/bash
# 每日新闻推送 cron 入口
# 用法：daily_push.sh [--dry-run]
#
# 环境变量（均有默认值）：
#   OPENCLAW_WORKSPACE  工作区路径
#   OPENCLAW_BIN        openclaw 二进制路径
#   SEARXNG_URL         SearXNG 地址
#   FEISHU_USER_ID      飞书用户 open_id

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export OPENCLAW_WORKSPACE="${OPENCLAW_WORKSPACE:-$HOME/.openclaw/workspace}"
LOG_FILE="$OPENCLAW_WORKSPACE/memory/news_cron.log"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

mkdir -p "$(dirname "$LOG_FILE")"

log "========================================="
log "📰 每日新闻推送开始"
log "========================================="

cd "$SCRIPT_DIR"
python3 push.py "$@" 2>&1 | tee -a "$LOG_FILE"
EXIT_CODE=${PIPESTATUS[0]}

if [ $EXIT_CODE -eq 0 ]; then
    log "✅ 推送完成"
else
    log "❌ 推送失败 (exit $EXIT_CODE)"
fi

log "========================================="
exit $EXIT_CODE
