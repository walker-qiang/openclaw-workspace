#!/usr/bin/env python3
"""
News Collector Skill
Fetch high-quality news from multiple sources
Test mode: python3 test_collector.py
"""

import os
import sys
import json
import urllib.request
import urllib.parse
import re
from datetime import datetime

SEARXNG_URL = os.environ.get("SEARXNG_URL", "http://localhost:8080")

# Categories with optimized queries (Chinese + English for coverage)
CATEGORIES = {
    "政治": [
        "国际政治 外交 局势 site:bbc.com OR site:cnn.com OR site:reuters.com",
        "国际新闻 site:xinhuanet.com OR site:people.com.cn OR site:cctv.com",
        "world politics international news",
    ],
    "经济": [
        "全球经济 金融 市场 site:bloomberg.com OR site:ft.com",
        "财经新闻 site:caixin.com OR site:cs.com.cn",
        "global economy finance market news",
    ],
    "军事": [
        "军事 国防 冲突 site:reuters.com OR site:bbc.com",
        "军事新闻 site:huanqiu.com OR site:chinamil.com.cn",
        "military defense news",
    ],
    "科技": [
        "科技 创新 突破 site:techcrunch.com OR site:wired.com",
        "科技新闻 site:36kr.com OR site:geekpark.net",
        "technology science innovation news",
    ],
    "AI": [
        "人工智能 AI 大模型 site:mit.edu OR site:technologyreview.com",
        "AI 新闻 site:qbitai.com OR site:机器之心.com",
        "artificial intelligence AI machine learning news",
    ],
}

# Trusted news domains
TRUSTED_DOMAINS = [
    # Chinese
    "xinhuanet.com", "people.com.cn", "cctv.com", "caixin.com",
    "thepaper.cn", "huanqiu.com", "chinanews.com", "36kr.com",
    # International
    "reuters.com", "bbc.com", "cnn.com", "bloomberg.com",
    "ft.com", "wsj.com", "theguardian.com", "scmp.com",
    # Tech
    "techcrunch.com", "wired.com", "theverge.com", "arstechnica.com",
    "technologyreview.com", "mit.edu"
]

# Skip these domains
SKIP_DOMAINS = [
    "zhihu.com", "baidu.com", "taobao.com", "jd.com",
    "douban.com", "bilibili.com", "youtube.com",
    "github.com", "stackoverflow.com", "wikipedia.org"
]

def fetch_searxng(query, timeout=10):
    """Fetch from SearXNG"""
    try:
        params = urllib.parse.urlencode({
            "q": query,
            "format": "json",
            "pageno": "1"
        })
        
        url = f"{SEARXNG_URL}/search?{params}"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = json.loads(response.read().decode())
            return data.get("results", [])
    except Exception as e:
        print(f"  SearXNG error: {e}")
        return []

def is_valid_news(item):
    """Check if item is valid news"""
    url = item.get("url", "").lower()
    title = item.get("title", "")
    content = item.get("content", "")
    
    # Must have title
    if not title or len(title) < 10:
        return False
    
    # Skip bad domains
    if any(skip in url for skip in SKIP_DOMAINS):
        return False
    
    # Must have some content
    if not content or len(content) < 30:
        return False
    
    # Skip tutorial/how-to content
    skip_words = ["教程", "如何使用", "怎么", "what is", "how to", "guide"]
    if any(w in title.lower() for w in skip_words):
        return False
    
    return True

def get_domain_priority(url):
    """Get priority based on domain (lower is better)"""
    url_lower = url.lower()
    if any(d in url_lower for d in TRUSTED_DOMAINS):
        return 0
    if ".com" in url_lower or ".cn" in url_lower:
        return 1
    return 2

def clean_text(text):
    """Clean text"""
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'http[s]?://\S+', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def fetch_news_for_category(category, queries):
    """Fetch news for a category with multiple queries"""
    all_items = []
    seen_urls = set()
    
    for query in queries:
        results = fetch_searxng(query, timeout=8)
        
        for item in results:
            url = item.get("url", "")
            
            # Skip duplicates
            if url in seen_urls:
                continue
            
            # Validate
            if not is_valid_news(item):
                continue
            
            seen_urls.add(url)
            
            all_items.append({
                "title": clean_text(item.get("title", "")),
                "content": clean_text(item.get("content", "")),
                "url": url,
                "priority": get_domain_priority(url)
            })
    
    # Sort by priority and take top 5
    all_items.sort(key=lambda x: x["priority"])
    return all_items[:5]

def test_all_categories():
    """Test fetching news for all categories"""
    print("=" * 50)
    print("News Collector Test")
    print("=" * 50)
    
    for category, queries in CATEGORIES.items():
        print(f"\n【{category}】")
        print("-" * 40)
        
        items = fetch_news_for_category(category, queries)
        
        if items:
            for i, item in enumerate(items, 1):
                print(f"\n{i}. {item['title']}")
                print(f"   来源：{item['url'][:50]}...")
                content = item['content'][:100]
                print(f"   摘要：{content}...")
        else:
            print("  未获取到新闻")
        
        print()

if __name__ == "__main__":
    test_all_categories()
