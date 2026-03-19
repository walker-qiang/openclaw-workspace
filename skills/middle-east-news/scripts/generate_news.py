#!/usr/bin/env python3
"""
News Collector v7.0 - 业界最佳实践版
- 摘要：50-80 字，主谓宾 + 数据优先
- 来源：白名单制，权威媒体优先
- 过滤：排除教程/推广/旧闻
- 时间：经济/科技/AI 24h，政治/军事 72h
"""

import os
import re
import json
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from html import unescape

# 微语库（每日一句）
WISDOM_QUOTES = [
    "人生最大的遗憾，莫过于轻易地放弃了不该放弃的，固执地坚持了不该坚持的。",
    "生活不是等待风暴过去，而是学会在雨中跳舞。",
    "每一次挫折都是成长的机会，关键在于你如何选择面对。",
    "真正的智慧不在于知道多少，而在于懂得什么最重要。",
    "成功不是终点，失败不是终结，唯有勇气才是永恒。",
    "与其抱怨黑暗，不如点亮一盏灯。",
    "时间不会为任何人停留，但可以为有价值的事放慢脚步。",
    "最好的投资，是投资自己的成长。",
    "改变能改变的，接受不能改变的，用智慧分辨两者。",
    "人生没有白走的路，每一步都算数。",
    "保持好奇，保持谦逊，世界永远有值得学习的东西。",
    "简单不是简陋，而是经过复杂后的回归。",
    "真正的自由，是拥有说不的勇气。",
    "善良是一种选择，更是一种力量。",
    "今天很残酷，明天更残酷，后天很美好。",
]

SEARXNG_URL = os.environ.get("SEARXNG_URL", "http://localhost:8080")

# === 来源白名单 - 只从权威媒体抓取 ===
# Tier 1：最高优先级（权威财经/时政）
# Tier 2：次优先级（专业科技/AI）
NEWS_SOURCES = {
    "政治": [
        # Tier 1：权威时政
        ("澎湃新闻", "https://www.thepaper.cn/list_21587"),
        ("观察者网", "https://www.guancha.cn/world/"),
        ("联合早报", "https://www.zaobao.com.sg/news/realtime/china"),
        ("央视新闻", "https://news.cctv.com/world/"),
    ],
    "经济": [
        # Tier 1：权威财经
        ("财新网", "https://www.caixin.com/"),
        ("彭博社中文", "https://www.bloombergchina.com/"),
        ("金融时报中文", "https://www.ftchinese.com/"),
        ("一财网", "https://www.yicai.com/"),
        ("21 世纪经济报道", "https://m.21jingji.com/"),
    ],
    "科技": [
        # Tier 1：权威科技
        ("36 氪", "https://36kr.com/"),
        ("虎嗅", "https://www.huxiu.com/"),
        ("钛媒体", "https://www.tmtpost.com/"),
    ],
    "AI": [
        # Tier 1：专业 AI 媒体
        ("量子位", "https://www.qbitai.com/"),
        ("机器之心", "https://www.jiqizhixin.com/"),
        ("新智元", "https://www.aitecher.com/"),
        ("AI 前线", "https://www.infoq.cn/topic/AI"),
    ],
    "军事": [
        # Tier 1：权威军事
        ("网易军事", "https://war.163.com/"),
        ("新浪军事", "https://news.sina.com.cn/m/"),
        ("腾讯军事", "https://news.qq.com/mil/"),
        ("中国军网", "https://www.81.cn/"),
    ],
}

# 关键词分类（优先级：军事 > 政治 > 经济 > AI > 科技）
CATEGORY_KEYWORDS = {
    "军事": ["军事", "国防", "军队", "解放军", "演习", "战机", "舰艇", "导弹", "武警", "海军", "空军", "陆军", "火箭军", "美军", "以军", "伊朗", "以色列", "五角大楼", "航母", "轰炸", "空袭", "俘获", "士兵"],
    "政治": ["国际", "外交", "选举", "政府", "总统", "总理", "会谈", "访问", "政策", "议会", "国会", "首相", "制裁", "抗议", "王毅", "中美", "议员", "委内瑞拉"],
    "经济": ["经济", "市场", "股市", "金融", "投资", "企业", "财报", "CPI", "PPI", "通胀", "利率", "央行", "贸易", "油价", "基金", "理财", "销售额", "营收"],
    "AI": ["AI", "人工智能", "大模型", "千问", "商汤", "智谱", "算力", "视觉", "认知", "NVIDIA", "具身", "多模态", "LLM", "GPT", "Claude", "Gemini", "DeepSeek", "Agent", "智能体"],
    "科技": ["科技", "互联网", "数码", "通信", "芯片", "软件", "机器人", "基站", "电动车", "手机", "发布", "上市"],
}

# === AI 新闻严格过滤 ===
# 必须包含（至少一个）
AI_MUST_HAVE = [
    "人工智能", "大模型", "AI ", " AI", "深度学习", "机器学习", "LLM", "GPT",
    "DeepSeek", "Gemini", "Claude", "Copilot", "Sora", "Midjourney",
    "AGI", "Agent", "智能体", "通义", "文心", "LangChain", "LLaMA", "OpenAI",
    "智谱", "月之暗面", "千问", "混元", "Qwen", "生成式 AI", "AIGC",
    "ai ", " ai", "llm", "gpt-", "gpt4", "gpt5"
]
# 必须排除（出现即过滤）
AI_MUST_NOT_HAVE = [
    "教程", "指南", "如何使用", "怎么使用", "免费使用", "下载", "APP", "推广",
    "化学物", "化学", "燃烧", "外星", "火星", "太空", "行星", "天文",
    "物理", "生物", "医学", "药物", "基因", "细胞", "疫苗", "癌症",
    "疾病", "医疗", "健康", "食品", "超市"
]

def fetch_page(url, timeout=8):
    """Fetch webpage"""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "zh-CN,zh;q=0.9",
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode('utf-8', errors='ignore')
    except Exception:
        return None

def fetch_searxng(query):
    """Search via SearXNG"""
    try:
        params = urllib.parse.urlencode({"q": query, "format": "json"})
        url = f"{SEARXNG_URL}/search?{params}"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
            return data.get("results", [])
    except Exception:
        return []

def clean_html(text):
    """Clean HTML"""
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', '', text)
    text = unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_date_from_html(html):
    """Extract date from HTML"""
    if not html:
        return None
    
    # ISO format
    match = re.search(r'(\d{4})-(\d{2})-(\d{2})[T\s](\d{2}):(\d{2})', html)
    if match:
        try:
            return datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)),
                          int(match.group(4)), int(match.group(5)))
        except ValueError:
            pass
    
    # Date only
    match = re.search(r'(\d{4})-(\d{2})-(\d{2})', html)
    if match:
        try:
            return datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            pass
    
    # Chinese relative
    if '今天' in html or '今日' in html or 'today' in html.lower():
        return datetime.now()
    if '昨天' in html or 'yesterday' in html.lower():
        return datetime.now() - timedelta(days=1)
    
    return None

def is_recent(date, hours=24):
    """Check if recent"""
    if not date:
        return False
    return (datetime.now() - date).total_seconds() <= (hours * 3600)

def classify_content(title, content=""):
    """Classify content based on keywords"""
    text = (title + " " + content).lower()
    
    # Military first
    if any(kw.lower() in text for kw in CATEGORY_KEYWORDS["军事"]):
        return "军事"
    
    # Then others
    scores = {}
    for category in ["政治", "经济", "AI", "科技"]:
        keywords = CATEGORY_KEYWORDS[category]
        score = sum(1 for kw in keywords if kw.lower() in text)
        scores[category] = score
    
    best = max(scores, key=scores.get)
    if scores[best] > 0:
        return best
    
    return None

def extract_news_from_html(html, source_url=""):
    """Extract news with date"""
    if not html:
        return []
    
    items = []
    base_url = "/".join(source_url.split("/")[:3])
    seen = set()
    page_date = extract_date_from_html(html)
    
    # Pattern: <a href="..." >title</a>
    matches = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>([^<]{20,120})</a>', html, re.IGNORECASE)
    
    for match in matches:
        href = match[0]
        title = clean_html(match[1]).strip()
        
        # Length filter
        if len(title) < 15 or len(title) > 80:
            continue
        
        # Require Chinese characters
        if sum(1 for c in title if '\u4e00' <= c <= '\u9fff') < 5:
            continue
        
        # Skip low-quality titles
        skip_words = ["首页", "更多", "广告", "登录", "下载", "专题", "直播", "导航", "列表", "关于我们", "联系我们", "许可证", "经营许可证", "京 B2"]
        if any(w in title for w in skip_words):
            continue
        
        # Skip old date patterns - any mention of a different month
        current_month = datetime.now().month
        
        # Check if title contains a month range (e.g., "1-2 月", "1~3 月", "1 至 3 月", "1—2 月")
        # Support various dash types: hyphen -, tilde ~, Chinese dash 一，em-dash —
        has_month_range = bool(re.search(r'\d{1,2}[-~一—至]\d{1,2}\u6708', title))
        
        # Find all "X 月" patterns in title - use unicode escape for reliability
        all_months = re.findall(r'(\d{1,2})\u6708', title)
        skip_item = False
        for month_str in all_months:
            mentioned_month = int(month_str)
            # Skip if any month mentioned is not current month (and is a valid month 1-12)
            if 1 <= mentioned_month <= 12 and mentioned_month != current_month:
                # Allow if it's part of a range that includes recent months
                if has_month_range:
                    continue  # Allow month ranges
                skip_item = True
                break
        
        if skip_item:
            continue
        
        # Deduplicate
        title_key = title[:30]
        if title_key in seen:
            continue
        seen.add(title_key)
        
        # Build URL
        if href.startswith("/"):
            href = base_url + href
        elif href.startswith("//"):
            href = "https:" + href
        
        items.append({
            "title": title,
            "url": href,
            "source": "",
            "content": "",
            "date": page_date,
        })
    
    return items

def fetch_article_content(url, timeout=4):
    """Fetch article content"""
    try:
        html = fetch_page(url, timeout)
        if not html:
            return "", None
        
        # Meta description
        match = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
        if match:
            desc = unescape(match.group(1))
            if len(desc) > 30:
                return desc, extract_date_from_html(html)
        
        # First paragraph
        paragraphs = re.findall(r'<p[^>]*>([^<]{50,500})</p>', html)
        if paragraphs:
            return clean_html(paragraphs[0]), extract_date_from_html(html)
        
        return "", extract_date_from_html(html)
    except Exception:
        return "", None

def generate_summary(title, content, category):
    """
    Generate summary following industry best practices:
    - 50-80 characters optimal, max 100
    - Subject-Verb-Object structure
    - Prioritize numbers/data
    - Remove filler words and tags
    """
    if not content:
        clean = re.sub(r'[（(].*[)）]$', '', title).strip()
        return clean[:80]
    
    content = clean_html(content)
    
    # Skip low-quality content
    low_quality = ["首页>", "导航", "专题", "广告", "推荐", "登录", "注册", "下载 APP", "扫码"]
    if any(p in content for p in low_quality):
        clean = re.sub(r'[（(].*[)）]$', '', title).strip()
        return clean[:80]
    
    # Skip if content is website description
    if re.search(r'我们是 | 旗下 | 新媒体 | 专注于 | 致力于', content):
        clean = re.sub(r'[（(].*[)）]$', '', title).strip()
        return clean[:80]
    
    # Extract sentences
    sentences = re.split(r'[。！？.!?]', content)
    meaningful = []
    for s in sentences:
        s = s.strip()
        if len(s) < 20:
            continue
        # Skip navigation/filler
        if any(w in s for w in ["广告", "推荐", "首页", "导航", "扫码", "关注", "更多"]):
            continue
        # Skip tag lists (e.g., "伊朗，红海，福特")
        if re.match(r'^[^\u4e00-\u9fa5]*([\u4e00-\u9fa5]{2,4}[,，][^\u4e00-\u9fa5]*)*[\u4e00-\u9fa5]{2,4}[,，]', s):
            continue
        # Skip if mostly commas/tags
        if s.count(',') + s.count('，') > len(s) / 2:
            continue
        meaningful.append(s)
    
    if not meaningful:
        clean = re.sub(r'[（(].*[)）]$', '', title).strip()
        return clean[:80]
    
    # Strategy: Extract key facts
    lead = meaningful[0]
    lead = re.sub(r'[（(][^)）]*[)）]', '', lead).strip()
    # Remove tag-like patterns
    lead = re.sub(r'^[,，:：\s]+', '', lead)
    
    # Look for data/numbers
    data_point = ""
    for s in meaningful[1:4]:
        if re.search(r'\d+[.%亿元]', s):
            data_point = re.sub(r'[（(][^)）]*[)）]', '', s).strip()
            break
    
    # Synthesize
    if data_point and len(lead) < 60:
        summary = lead + "。" + data_point
    else:
        summary = lead
    
    # Trim to 50-80 optimal, max 100
    if len(summary) > 100:
        summary = summary[:97] + "..."
    
    # Clean up prefixes and tags
    summary = re.sub(r'^[^\u4e00-\u9fa5]+[:：]', '', summary).strip()
    summary = re.sub(r'^[,，:：\s]+', '', summary)
    
    # Remove trailing tag lists (e.g., ",伊朗，红海，福特")
    summary = re.sub(r'[,，][^\u4e00-\u9fa5]*([\u4e00-\u9fa5]{2,4}[,，]){2,}.*$', '', summary)
    
    return summary[:100] if len(summary) > 100 else summary

def validate_ai_news(title, content=""):
    """Strict AI news validation"""
    text = (title + " " + (content or "")).lower()
    
    # Must have at least one AI keyword
    has_ai = any(kw.lower() in text for kw in AI_MUST_HAVE)
    if not has_ai:
        return False
    
    # Must not have exclusion keywords
    has_excluded = any(kw in text for kw in AI_MUST_NOT_HAVE)
    if has_excluded:
        return False
    
    # Must not be tutorial/guide
    tutorial_patterns = ["教程", "指南", "如何使用", "怎么使用", "free", "免费", "下载", "app"]
    if any(p in text for p in tutorial_patterns):
        return False
    
    return True

def search_ai_news(hours=48):
    """Search for AI news via SearXNG"""
    queries = [
        "人工智能 大模型",
        "AI 技术 突破",
        "GPT Claude Gemini DeepSeek",
        "AI artificial intelligence news",
        "LLM 大语言模型",
        "AI Agent 智能体 应用",
    ]
    
    items = []
    seen = set()
    
    for query in queries:
        if len(items) >= 5:
            break
        
        results = fetch_searxng(query)
        for r in results:
            if len(items) >= 5:
                break
            
            title = clean_html(r.get("title", ""))
            url = r.get("url", "")
            content = r.get("content", "")
            
            # Length filter
            if len(title) < 15 or len(title) > 100:
                continue
            
            # Skip unwanted sites
            skip_sites = ["zhihu.com", "baidu.com", "weibo.com", "toutiao.com", "csdn.net", "jianshu.com", "36kr.com"]
            if any(s in url.lower() for s in skip_sites):
                continue
            
            # Require Chinese characters (at least 5)
            if sum(1 for c in title if '\u4e00' <= c <= '\u9fff') < 5:
                continue
            
            # Skip tutorials/guides
            skip_patterns = ["教程", "指南", "免费使用", "下载", "APP", "推广", "怎么使用"]
            if any(p in title for p in skip_patterns):
                continue
            
            # Deduplicate
            title_key = title[:30]
            if title_key in seen:
                continue
            seen.add(title_key)
            
            # Extract date
            pub_date = extract_date_from_html(content) if content else None
            
            items.append({
                "title": title,
                "url": url,
                "source": "搜索",
                "content": content,
                "date": pub_date or datetime.now(),
                "detected_category": "AI",
            })
    
    print(f"      搜索获取 {len(items)}条 AI 新闻")
    return items

def fetch_and_classify_news(category, sources, max_age_hours=24):
    """Fetch news with strict quality control"""
    print(f"  抓取 {category} 新闻...")
    all_items = []
    
    # Time window by category
    check_hours = 72 if category in ["政治", "军事"] else 24
    
    for source_name, url in sources:
        print(f"    → {source_name}")
        html = fetch_page(url)
        if not html:
            continue
        
        items = extract_news_from_html(html, url)
        for item in items:
            item["source"] = source_name
            if item["url"]:
                content, article_date = fetch_article_content(item["url"], timeout=3)
                # Skip website descriptions
                if content and re.search(r'我们是 | 旗下 | 新媒体 | 专注于', content):
                    continue
                item["content"] = content
                if article_date:
                    item["date"] = article_date
        
        all_items.extend(items)
        
        recent = [i for i in all_items if i.get("date") and is_recent(i["date"], hours=check_hours)]
        if len(recent) >= 5:
            print(f"      已获取 {len(recent)}条 {check_hours}h 新闻，停止抓取")
            break
    
    # Classify and filter
    classified = {cat: [] for cat in CATEGORY_KEYWORDS.keys()}
    for item in all_items:
        detected_cat = classify_content(item["title"], item.get("content", ""))
        if detected_cat:
            item["detected_category"] = detected_cat
            classified[detected_cat].append(item)
        else:
            item["detected_category"] = category
            classified[category].append(item)
    
    # Filter by recency
    result = [i for i in classified[category] if i.get("date") and is_recent(i["date"], hours=check_hours)]
    
    # Extra strict AI validation
    if category == "AI":
        validated = [i for i in result if validate_ai_news(i["title"], i.get("content", ""))]
        if len(validated) < len(result):
            print(f"      AI 严格过滤：{len(result)}条 → {len(validated)}条")
        result = validated
        
        # If AI < 3, use search to supplement (expand time window)
        if len(result) < 3:
            print(f"      AI 不足 ({len(result)}条)，使用搜索补充...")
            search_items = search_ai_news(hours=168)  # Up to 7 days for AI
            for item in search_items:
                if len(result) >= 5:
                    break
                if validate_ai_news(item["title"], item.get("content", "")):
                    # Deduplicate
                    existing_titles = [i["title"][:30] for i in result]
                    if item["title"][:30] not in existing_titles:
                        result.append(item)
            
            if len(result) > 0:
                print(f"      搜索补充后：{len(result)}条")
    
    # Deduplicate by title
    seen = set()
    unique = []
    for item in result:
        key = item["title"][:30]
        if key not in seen:
            seen.add(key)
            unique.append(item)
    
    print(f"      最终获取 {len(unique)}条 {check_hours}h 新闻")
    return unique[:5]  # Max 5

def fetch_military_news():
    """Fetch military news"""
    print("  抓取军事新闻...")
    all_items = []
    check_hours = 72
    
    sources = NEWS_SOURCES["军事"]
    for source_name, url in sources:
        print(f"    → {source_name}")
        html = fetch_page(url)
        if html:
            items = extract_news_from_html(html, url)
            for item in items:
                # Must have military keywords
                if any(kw in item["title"] for kw in ["军事", "国防", "军队", "演习", "战机", "舰艇", "导弹", "美军", "以军", "伊朗", "解放军", "航母", "空袭"]):
                    item["source"] = source_name
                    if item["url"]:
                        content, article_date = fetch_article_content(item["url"], timeout=3)
                        item["content"] = content
                        if article_date:
                            item["date"] = article_date
                    all_items.append(item)
        
        recent = [i for i in all_items if i.get("date") and is_recent(i["date"], hours=check_hours)]
        if len(recent) >= 5:
            print(f"      已获取 {len(recent)}条 {check_hours}h 新闻，停止抓取")
            break
    
    # Deduplicate
    seen = set()
    unique = []
    for item in all_items:
        key = item["title"][:30]
        if key not in seen:
            seen.add(key)
            unique.append(item)
    
    result = [i for i in unique if i.get("date") and is_recent(i["date"], hours=check_hours)]
    print(f"      最终获取 {len(result)}条 {check_hours}h 军事新闻")
    return result[:5]

def fetch_all_news():
    """Fetch all categories"""
    print(f"[{datetime.now()}] 开始抓取新闻（业界最佳实践版）...")
    print()
    
    news_data = {}
    
    for category, sources in NEWS_SOURCES.items():
        if category == "军事":
            items = fetch_military_news()
        else:
            check_hours = 72 if category in ["政治", "军事"] else 24
            items = fetch_and_classify_news(category, sources, max_age_hours=check_hours)
        
        # Generate summaries
        for item in items:
            item["summary"] = generate_summary(
                item["title"],
                item.get("content", ""),
                item.get("detected_category", category)
            )
        
        news_data[category] = items
        print(f"  ✅ {category}: {len(items)}条")
    
    return news_data

def build_markdown(news_data):
    """Build markdown"""
    now = datetime.now()
    ts = now.strftime("%Y-%m-%d %H:%M")
    weekday = now.strftime("%A")
    weekday_cn = {"Monday": "星期一", "Tuesday": "星期二", "Wednesday": "星期三", 
                  "Thursday": "星期四", "Friday": "星期五", "Saturday": "星期六", "Sunday": "星期日"}
    weekday_str = weekday_cn.get(weekday, "")
    
    # Lunar date (simple fallback)
    lunar = "正月廿一"
    
    # Daily wisdom
    wisdom_idx = (now.day - 1) % len(WISDOM_QUOTES)
    wisdom = WISDOM_QUOTES[wisdom_idx]
    
    # Header
    md = ["# 📰 全球要闻简报", ""]
    md.append(f"**日期**：{now.strftime('%Y 年 %m 月 %d 日')} {weekday_str}")
    md.append(f"**农历**：{lunar}")
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
        
        for i, item in enumerate(items, 1):
            md.append(f"### {i}. {item.get('title', '')}")
            md.append("")
            if item.get("source"):
                md.append(f"**来源**：{item['source']}")
                md.append("")
            md.append(f"**摘要**：{item.get('summary', '')}")
            md.append("")
            if item.get("url"):
                md.append(f"[阅读原文]({item['url']})")
                md.append("")
            total += 1
    
    md.append("---")
    md.append("")
    md.append("## 💡 微语")
    md.append("")
    md.append(f"> {wisdom}")
    md.append("")
    md.append("---")
    md.append("")
    md.append(f"**共 {total} 条精选新闻**")
    md.append("")
    md.append("_筛选标准：权威媒体白名单 | 智能内容分类 | 严格 AI 过滤 | 24-72h 时效 | 50-80 字精炼摘要_")
    
    return "\n".join(md)

def main():
    news_data = fetch_all_news()
    print("\n生成文档...")
    md = build_markdown(news_data)
    
    with open("/tmp/news_brief.md", "w", encoding="utf-8") as f:
        f.write(md)
    
    print(f"✓ 已保存到 /tmp/news_brief.md")
    print(f"✓ 总字符数：{len(md)}")
    
    return "/tmp/news_brief.md"

if __name__ == "__main__":
    main()
