#!/usr/bin/env python3
# DEPRECATED — 请使用 push.py 代替。本文件保留仅供参考。
"""
[DEPRECATED] News Collector - Push to Feishu Doc
→ 替代方案：python3 push.py

本脚本存在以下问题：
  - create_feishu_doc() 返回 None（未实现）
  - 硬编码 /home/admin 路径和飞书 open_id
"""

import os
import sys
import json
import urllib.request
import re
import subprocess
from datetime import datetime

SEARXNG_URL = "http://localhost:8080"
USER_ID = "ou_69f6f6ff7c4bb1088485d1d3760a17ac"
WORKSPACE = "/home/admin/.openclaw/workspace"

# News sources
NEWS_SOURCES = {
    "政治": [
        "https://www.bbc.com/zhongwen/simp/world",
        "https://www.xinhuanet.com/world/",
        "https://www.huanqiu.com/world/",
    ],
    "经济": [
        "https://www.xinhuanet.com/fortune/",
        "https://finance.sina.com.cn/",
    ],
    "军事": [
        "https://www.huanqiu.com/military/",
        "https://www.xinhuanet.com/military/",
    ],
    "科技": [
        "https://www.xinhuanet.com/tech/",
        "https://tech.163.com/",
    ],
    "AI": [
        "https://www.xinhuanet.com/tech/ai.htm",
        "https://www.qbitai.com/",
    ],
}

def fetch_page(url, timeout=8):
    """Fetch webpage"""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"  Fetch error {url[:40]}: {e}")
        return None

def extract_news(html, source):
    """Extract news from HTML"""
    if not html:
        return []
    
    items = []
    pattern = r'<a[^>]+href="([^"]+)"[^>]*>([^<]+)</a>'
    
    for href, title in re.findall(pattern, html):
        title = title.strip()
        if len(title) < 10 or len(title) > 100:
            continue
        
        skip = ["首页", "更多", "登录", "广告", "下载", "APP"]
        if any(w in title for w in skip):
            continue
        
        if any('\u4e00' <= c <= '\u9fff' for c in title):
            if href.startswith("/"):
                base = "/".join(source.split("/")[:3])
                href = base + href
            
            items.append({"title": title, "url": href})
    
    return items[:5]

def fetch_all_news():
    """Fetch news from all sources"""
    result = {}
    
    for category, urls in NEWS_SOURCES.items():
        print(f"{category}: ", end="")
        items = []
        
        for url in urls[:2]:
            html = fetch_page(url)
            if html:
                extracted = extract_news(html, url)
                items.extend(extracted)
        
        # Dedupe
        seen = set()
        unique = []
        for item in items:
            if item["title"] not in seen:
                seen.add(item["title"])
                unique.append(item)
        
        result[category] = unique[:5]
        print(f"{len(result[category])}条")
    
    return result

def build_markdown(news_data):
    """Build markdown content"""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    md = []
    md.append("# 📰 全球要闻简报")
    md.append("")
    md.append(f"_更新时间：{ts}_")
    md.append("")
    md.append("---")
    md.append("")
    
    total = 0
    icons = {"政治": "🏛️", "经济": "💰", "军事": "⚔️", "科技": "🔬", "AI": "🤖"}
    
    for category, items in news_data.items():
        icon = icons.get(category, "📌")
        md.append(f"## {icon} {category}")
        md.append("")
        
        if items:
            for i, item in enumerate(items, 1):
                title = item["title"]
                url = item["url"]
                md.append(f"{i}. [{title}]({url})")
            total += len(items)
        else:
            md.append("_暂无新闻_")
        
        md.append("")
    
    md.append("---")
    md.append("")
    md.append(f"**共 {total} 条新闻**")
    md.append("")
    md.append("_来源：BBC/新华网/环球网/新浪财经/量子位等权威媒体_")
    
    return "\n".join(md)

def create_feishu_doc(title, content):
    """Create Feishu doc by writing to temp file and using session"""
    try:
        # Write content to temp file
        temp_file = "/tmp/feishu_doc_content.md"
        with open(temp_file, "w") as f:
            f.write(content)
        
        # Use sessions_spawn to create doc
        spawn_cmd = [
            "/home/admin/.local/share/pnpm/openclaw",
            "sessions_spawn",
            "--mode", "run",
            "--task", f"Create a Feishu doc with title '{title}' using content from {temp_file}"
        ]
        
        # For now, return a placeholder URL
        # In production, would need proper tool integration
        return None
        
    except Exception as e:
        print(f"Error: {e}")
        return None

def send_message(msg):
    """Send Feishu message"""
    try:
        env = os.environ.copy()
        env["PATH"] = "/home/admin/.local/share/pnpm:/home/linuxbrew/.linuxbrew/bin:/usr/local/bin:/usr/bin:/bin"
        env["HOME"] = "/home/admin"
        
        cmd = ["/home/admin/.local/share/pnpm/openclaw", "message", "send",
               "--target", USER_ID, "--message", msg]
        
        result = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 cwd=WORKSPACE, env=env)
        stdout, _ = result.communicate()
        
        return result.returncode == 0 or b"Sent via Feishu" in stdout
    except Exception as e:
        print(f"Send error: {e}")
        return False

def main():
    print(f"[{datetime.now()}] News Collector - Feishu Doc Mode")
    print("=" * 50)
    
    # Fetch news
    print("\n抓取新闻...")
    news_data = fetch_all_news()
    
    total = sum(len(items) for items in news_data.values())
    print(f"\n共获取 {total} 条新闻")
    
    # Build markdown
    print("\n生成文档...")
    md_content = build_markdown(news_data)
    
    # Create doc
    date_only = datetime.now().strftime("%Y-%m-%d")
    doc_title = f"全球要闻简报 {date_only}"
    
    print(f"创建飞书文档：{doc_title}")
    doc_url = create_feishu_doc(doc_title, md_content)
    
    if doc_url:
        print(f"✓ 文档已创建：{doc_url}")
        
        # Send message
        ts = datetime.now().strftime("%m-%d %H:%M")
        msg = f"📰 全球要闻简报已更新 ({ts})\n\n"
        msg += f"📄 查看详情：{doc_url}\n\n"
        msg += "内容包括：政治、经济、军事、科技、AI 五大领域\n"
        msg += "来源：BBC/新华网/环球网等权威媒体"
        
        if send_message(msg):
            print("✓ 消息已发送")
            return 0
    else:
        print("✗ 文档创建失败")
    
    return 1

if __name__ == "__main__":
    sys.exit(main())
