#!/usr/bin/env python3
# DEPRECATED — 请使用 generate_news.py + push.py 代替。本文件保留仅供参考。
"""
[DEPRECATED] Fetch Middle East news and send via Feishu
→ 替代方案：python3 push.py

本脚本为早期版本，功能已被 generate_news.py + push.py 覆盖。
"""

import os
import sys
import json
import subprocess
from datetime import datetime

# News sources for Middle East
NEWS_QUERIES = [
    "中东 最新新闻 site:reuters.com",
    "中东 局势 site:bbc.com",
    "Middle East news site:aljazeera.com",
    "中东 时事 2026",
]

def search_news(query, count=5):
    """Search news using Brave Search API via web_search tool"""
    try:
        # Use curl to call the search API
        cmd = [
            "curl", "-s", "-X", "POST",
            "http://localhost:8080/api/search",
            "-H", "Content-Type: application/json",
            "-d", json.dumps({
                "query": query,
                "count": count,
                "freshness": "day"
            })
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return json.loads(result.stdout)
    except Exception as e:
        print(f"Search error: {e}")
    return None

def format_news_items(results, source_name=""):
    """Format news results into readable text"""
    if not results or 'results' not in results:
        return []
    
    items = []
    for r in results.get('results', [])[:5]:
        title = r.get('title', '')
        url = r.get('url', '')
        content = r.get('content', '')[:200]
        date = r.get('publishedDate', '')
        
        if title and url:
            items.append(f"• {title}\n  {url}")
    
    return items

def send_feishu_message(content):
    """Send message via Feishu"""
    try:
        # Use OpenClaw message tool via CLI
        cmd = [
            "openclaw", "message", "send",
            "--target", "ou_69f6f6ff7c4bb1088485d1d3760a17ac",
            "--message", content
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.returncode == 0
    except Exception as e:
        print(f"Send error: {e}")
        return False

def main():
    """Main function to fetch and send news"""
    print(f"[{datetime.now()}] Fetching Middle East news...")
    
    all_news = []
    
    # Search from multiple sources
    for query in NEWS_QUERIES[:2]:  # Limit to 2 queries to avoid too many results
        results = search_news(query, count=3)
        if results:
            items = format_news_items(results)
            all_news.extend(items)
    
    if not all_news:
        # Fallback: use web_search tool directly
        print("Using fallback search...")
        all_news = [
            "• 中东新闻动态 - 请查看新闻网站获取最新信息",
            "  https://www.aljazeera.com/middle-east/",
            "  https://www.reuters.com/world/middle-east/"
        ]
    
    # Build message
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    message = f"📰 中东新闻速递 ({timestamp})\n\n"
    message += "\n\n".join(all_news[:8])  # Limit to 8 items
    message += "\n\n---\n_每 5 分钟自动推送_"
    
    print(f"Message:\n{message}")
    
    # Send via Feishu
    if send_feishu_message(message):
        print("[OK] News sent successfully")
    else:
        print("[FAIL] Failed to send news")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
