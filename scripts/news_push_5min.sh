#!/bin/bash
# 新闻推送脚本（workspace 层入口）
# 代理到 skills/middle-east-news/scripts/daily_push.sh
#
# 环境变量（均有默认值）：
#   OPENCLAW_WORKSPACE  工作区路径
#   OPENCLAW_BIN        openclaw 二进制路径
#   SEARXNG_URL         SearXNG 地址
#   FEISHU_USER_ID      飞书用户 open_id

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

export OPENCLAW_WORKSPACE="${OPENCLAW_WORKSPACE:-$WORKSPACE_ROOT}"

exec "$WORKSPACE_ROOT/skills/middle-east-news/scripts/daily_push.sh" "$@"
