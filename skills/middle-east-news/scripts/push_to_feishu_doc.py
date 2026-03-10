#!/usr/bin/env python3
"""
News Collector - Push to Feishu Doc
Fetch news and create/update Feishu document
"""

import os
import sys
import json
import urllib.request
import re
import subprocess
from datetime import datetime

SEARXNG_URL = "http://localhost:8080"

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
    except:
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
        
        skip = ["首页", "更多", "登录", "广告", "下载"]
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
        items = []
        for url in urls[:2]:
            html = fetch_page(url)
            if html:
                items.extend(extract_news(html, url))
        
        # Dedupe
        seen = set()
        unique = []
        for item in items:
            if item["title"] not in seen:
                seen.add(item["title"])
                unique.append(item)
        
        result[category] = unique[:5]
    
    return result

def create_or_update_doc(news_data):
    """Create or update Feishu doc with news"""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    date_only = datetime.now().strftime("%Y-%m-%d")
    
    # Build markdown content
    md_lines = []
    md_lines.append(f"# 📰 全球要闻简报")
    md_lines.append("")
    md_lines.append(f"_更新时间：{ts}_")
    md_lines.append("")
    md_lines.append("---")
    md_lines.append("")
    
    total = 0
    for category, items in news_data.items():
        md_lines.append(f"## {category}")
        md_lines.append("")
        
        if items:
            for i, item in enumerate(items, 1):
                title = item["title"]
                url = item["url"]
                md_lines.append(f"{i}. [{title}]({url})")
            total += len(items)
        else:
            md_lines.append("_暂无新闻_")
        
        md_lines.append("")
    
    md_lines.append("---")
    md_lines.append("")
    md_lines.append(f"**共 {total} 条新闻**")
    md_lines.append("")
    md_lines.append("_来源：BBC/新华网/环球网/新浪财经等权威媒体_")
    
    md_content = "\n".join(md_lines)
    
    # Use feishu_doc tool to create/update
    doc_title = f"全球要闻简报 {date_only}"
    
    try:
        # Try to create new doc
        cmd = [
            "/home/admin/.local/share/pnpm/openclaw",
            "feishu_doc", "create",
            "--title", doc_title,
            "--content", md_content
        ]
        
        result = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd="/home/admin/.openclaw/workspace"
        )
        stdout, stderr = result.communicate()
        
        output = stdout.decode()
        
        # Extract doc URL from output
        if "doc_token" in output or "https://" in output:
            # Find URL pattern
            import re
            url_match = re.search(r'https://[^\s"\'<>]+', output)
            if url_match:
                return url_match.group()
        
        return None
        
    except Exception as e:
        print(f"Error creating doc: {e}")
        return None

def send_message_with_link(doc_url):
    """Send Feishu message with doc link using sessions_send"""
    ts = datetime.now().strftime("%m-%d %H:%M")
    
    msg = f"📰 全球要闻简报已更新 ({ts})\n\n"
    msg += f"📄 查看详情：{doc_url}\n\n"
    msg += "内容包括：政治、经济、军事、科技、AI 五大领域\n"
    msg += "来源：BBC/新华网/环球网等权威媒体"
    
    try:
        env = os.environ.copy()
        env["PATH"] = "/home/admin/.local/share/pnpm:/home/linuxbrew/.linuxbrew/bin:/usr/local/bin:/usr/bin:/bin"
        env["HOME"] = "/home/admin"
        
        # Use sessions_send to send to main session
        cmd = ["/home/admin/.local/share/pnpm/openclaw", "sessions", "send",
               "--label", "main",
               "--message", msg]
        
        result = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 cwd="/home/admin/.openclaw/workspace", env=env)
        stdout, stderr = result.communicate()
        
        print(f"sessions_send stdout: {stdout.decode()}")
        print(f"sessions_send stderr: {stderr.decode()}")
        
        return result.returncode == 0
    except Exception as e:
        print(f"Error sending message: {e}")
        return False

def main():
    print(f"[{datetime.now()}] Fetching news...")
    
    # Fetch news
    news_data = fetch_all_news()
    
    total = sum(len(items) for items in news_data.values())
    print(f"Collected {total} news items")
    
    # Create doc
    print("Creating Feishu doc...")
    doc_url = create_or_update_doc(news_data)
    
    if doc_url:
        print(f"Doc created: {doc_url}")
        
        # Send message with link
        if send_message_with_link(doc_url):
            print("[OK] Sent")
            return 0
    
    print("[FAIL]")
    return 1

if __name__ == "__main__":
    sys.exit(main())
