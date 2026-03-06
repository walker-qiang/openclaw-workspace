#!/bin/bash
# Stock Analyzer Pro - 测试脚本

SKILL_DIR="/home/admin/.openclaw/workspace/skills/stock-analyzer-pro"

echo "================================"
echo "  Stock Analyzer Pro 测试"
echo "================================"
echo ""

# 测试 A 股
echo "📊 测试 A 股：贵州茅台 (600519)"
echo "--------------------------------"
python3 "$SKILL_DIR/scripts/main.py" 600519
echo ""

# 测试美股
echo "📊 测试美股：Apple (AAPL)"
echo "--------------------------------"
python3 "$SKILL_DIR/scripts/main.py" AAPL
echo ""

# 测试基金
echo "📊 测试基金：华夏成长混合 (000001)"
echo "--------------------------------"
python3 "$SKILL_DIR/scripts/main.py" 000001
echo ""

echo "================================"
echo "  测试完成"
echo "================================"
