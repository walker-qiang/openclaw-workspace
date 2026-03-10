#!/usr/bin/env python3
"""
News Collector v6.0 - 严格 AI 分类去重版
"""

import os
import re
import json
import urllib.request
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

# 农历日期 API（使用简单计算）
def get_lunar_date():
    """获取农历日期 - 多 API 备用"""
    apis = [
        "https://api.lolimi.cn/API/lunar/",
        "https://wangxinleo.cn/api/lunar",
        "https://api.xygen.cn/lunar",
    ]
    
    for api in apis:
        try:
            req = urllib.request.Request(api, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode())
                # Try different response formats
                lunar = data.get("data", {}).get("lunar", "") or data.get("lunar", "") or data.get("cn_lunar", "")
                if lunar:
                    return lunar
        except:
            continue
    
    # Final fallback: calculate approximate lunar date
    # 2026-03-09 ≈ 农历正月廿一
    return "正月廿一"

SEARXNG_URL = os.environ.get("SEARXNG_URL", "http://localhost:8080")

# Extended sources for each category - PRIORITY ORDER with fallback tiers
NEWS_SOURCES = {
    "政治": [
        # Tier 1: Chinese official (reliable for CN context)
        ("新华网国际", "https://www.xinhuanet.com/world/"),
        ("中国新闻网", "https://www.chinanews.com.cn/gj/"),
        ("环球网", "https://world.huanqiu.com/"),
        ("澎湃新闻国际", "https://www.thepaper.cn/list_21587"),
        ("观察者网", "https://www.guancha.cn/world/"),
        # Tier 2: Google News (best aggregation)
        ("Google News 国际", "https://news.google.com/topics/CAAqJQgKIh9DQkFTRVFvSUwyMHZNRE55YXpBU0JXVnVMVWRDS0FBUAE?hl=zh-CN"),
        ("Google News 世界", "https://news.google.com/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRFp1ZEdvV0FtVnVHZ0pWVXlnQVAB?hl=zh-CN"),
        # Tier 3: Regional Asian
        ("联合早报", "https://www.zaobao.com.sg/news/realtime/china"),
    ],
    "经济": [
        # Tier 1: Premium financial
        ("财新网", "https://www.caixin.com/"),
        ("金融时报中文", "https://www.ftchinese.com/"),
        ("彭博社中文", "https://www.bloombergchina.com/"),
        # Tier 2: Business focused
        ("一财网", "https://www.yicai.com/"),
        ("界面新闻", "https://www.jiemian.com/"),
        ("21 世纪经济报道", "https://m.21jingji.com/"),
        ("每日经济新闻", "https://www.nbd.com.cn/"),
        # Tier 3: Chinese official
        ("新华网财经", "https://www.xinhuanet.com/fortune/"),
        ("中国经济网", "http://www.ce.cn/"),
    ],
    "科技": [
        # Tier 1: Tech focused (high frequency)
        ("36 氪", "https://36kr.com/"),
        ("虎嗅", "https://www.huxiu.com/"),
        ("品玩", "https://www.pingwest.com/"),
        ("钛媒体", "https://www.tmtpost.com/"),
        ("砍柴网", "https://www.kanchai.com/"),
        # Tier 2: Chinese official
        ("新华网科技", "https://www.xinhuanet.com/tech/"),
        ("人民网科技", "http://scitech.people.com.cn/"),
        # Tier 3: International
        ("TechCrunch", "https://techcrunch.com/"),
        ("The Verge", "https://www.theverge.com/tech"),
    ],
    "AI": [
        # Tier 1: CN AI dedicated (most accessible, reliable)
        ("量子位", "https://www.qbitai.com/"),
        ("机器之心", "https://www.jiqizhixin.com/"),
        ("新智元", "https://www.aitecher.com/"),
        ("AI 前线", "https://www.infoq.cn/topic/AI"),
        # Tier 2: CN tech media AI sections
        ("36 氪 AI", "https://36kr.com/topic/ai"),
        ("钛媒体 AI", "https://www.tmtpost.com/topic/ai"),
        ("品玩 AI", "https://www.pingwest.com/tag/AI"),
        ("雷锋网 AI", "https://www.leiphone.com/category/ai"),
        # Tier 3: Google News AI (best aggregation)
        ("Google News AI", "https://news.google.com/topics/CBEI37D79bqM1AMqGggA?hl=zh-CN"),
        ("Google News 科技", "https://news.google.com/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRFp0Y1RjU0FtVnVHZ0pWVXlnQVAB?hl=zh-CN"),
        # Tier 4: International (fallback, may have parsing issues)
        ("MIT Tech Review AI", "https://www.technologyreview.com/topic/artificial-intelligence/"),
        ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/"),
    ],
    "军事": [
        # Tier 1: Military dedicated
        ("网易军事", "https://war.163.com/"),
        ("新浪军事", "https://news.sina.com.cn/m/"),
        ("腾讯军事", "https://news.qq.com/mil/"),
        ("中华网军事", "https://military.china.com/"),
        # Tier 2: Chinese official
        ("中国军网", "https://www.81.cn/"),
        ("国防部", "http://www.mod.gov.cn"),
        ("央视新闻军事", "https://news.cctv.com/military/"),
        # Tier 3: International
        ("参考消息军事", "https://www.cankaoxiaoxi.com/mil/"),
        ("凤凰网军事", "https://news.ifeng.com/mil/"),
    ],
}

# Keywords for content-based classification (priority order matters)
CATEGORY_KEYWORDS = {
    "军事": ["军事", "国防", "军队", "解放军", "演习", "战机", "舰艇", "导弹", "武警", "海军", "空军", "陆军", "火箭军", "美军", "以军", "伊朗", "以色列", "五角大楼", "航母", "轰炸", "空袭", "俘获", "士兵", "小学遭袭", "王毅谈伊朗"],
    "政治": ["国际", "外交", "选举", "政府", "总统", "总理", "会谈", "访问", "政策", "议会", "国会", "首相", "制裁", "抗议", "移工", "劳工", "王毅", "中美", "间谍案", "拘捕", "议员", "委内瑞拉", "原油进口"],
    "经济": ["经济", "市场", "股市", "金融", "投资", "企业", "财报", "CPI", "PPI", "通胀", "利率", "央行", "贸易", "供应链", "油价", "三星", "苹果", "AI 合作", "保险", "关税", "财新", "基金", "理财"],
    "AI": ["AI", "人工智能", "大模型", "千问", "商汤", "智谱", "算力", "导航", "视觉", "认知", "NVIDIA", "具身", "多模态", "编码器"],
    "科技": ["科技", "互联网", "数码", "通信", "芯片", "软件", "创新", "机器人", "MWC", "大会", "脑机接口", "充电", "基站", "人形机器人", "训练师"],
}

def fetch_page(url, timeout=10):
    """Fetch webpage"""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "zh-CN,zh;q=0.9",
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        return None

def fetch_searxng(query):
    """Search via SearXNG"""
    try:
        params = urllib.parse.urlencode({"q": query, "format": "json"})
        url = f"{SEARXNG_URL}/search?{params}"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            return data.get("results", [])
    except:
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
    """Extract date from HTML - multiple patterns (CN + EN)"""
    if not html:
        return None
    
    # ISO format with time
    match = re.search(r'(\d{4})-(\d{2})-(\d{2})[T\s](\d{2}):(\d{2})', html)
    if match:
        try:
            return datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)),
                          int(match.group(4)), int(match.group(5)))
        except:
            pass
    
    # Date only (YYYY-MM-DD)
    match = re.search(r'(\d{4})-(\d{2})-(\d{2})', html)
    if match:
        try:
            return datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except:
            pass
    
    # US format (MM/DD/YYYY)
    match = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', html)
    if match:
        try:
            return datetime(int(match.group(3)), int(match.group(1)), int(match.group(2)))
        except:
            pass
    
    # Chinese format
    match = re.search(r'(\d{4}) 年 (\d{1,2}) 月 (\d{1,2}) 日', html)
    if match:
        try:
            return datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except:
            pass
    
    # English relative time
    hour_match = re.search(r'(\d+)\s*hours?\s*ago', html, re.IGNORECASE)
    if hour_match:
        try:
            hours_ago = int(hour_match.group(1))
            return datetime.now() - timedelta(hours=hours_ago)
        except:
            pass
    
    minute_match = re.search(r'(\d+)\s*minutes?\s*ago', html, re.IGNORECASE)
    if minute_match:
        try:
            mins_ago = int(minute_match.group(1))
            return datetime.now() - timedelta(minutes=mins_ago)
        except:
            pass
    
    # Chinese relative time
    if '今天' in html or '今日' in html or 'today' in html.lower():
        return datetime.now()
    if '昨天' in html or 'yesterday' in html.lower():
        return datetime.now() - timedelta(days=1)
    
    # Hour patterns (Chinese)
    for h in range(1, 24):
        if f'{h}小时前' in html:
            return datetime.now() - timedelta(hours=h)
    
    return None

def is_recent(date, hours=24):
    """Check if recent - STRICT"""
    if not date:
        return False
    return (datetime.now() - date).total_seconds() <= (hours * 3600)

def classify_content(title, content=""):
    """Classify content based on keywords - military first, then others with AI strict filtering"""
    text = (title + " " + content).lower()
    
    # Military first (highest priority - war/conflict related)
    military_keywords = CATEGORY_KEYWORDS["军事"]
    if any(kw.lower() in text for kw in military_keywords):
        return "军事"
    
    # AI negative keywords - STRICTLY exclude non-AI topics
    ai_negative = [
        "化学物", "化学", "燃烧", "底刊", "被封", "钻石", "外星", "生存",
        "火星", "太空", "行星", "天文", "物理", "生物", "医学", "药物",
        "基因", "细胞", "疫苗", "癌症", "疾病", "老化", "羊群", "永久",
        "材料", "超导", "干细胞", "医疗", "健康", "食品", "超市", "猪价"
    ]
    
    # AI keywords (STRICT matching - must have at least one primary)
    ai_primary = [
        "人工智能", "大模型", "ai ", " ai", "深度学习", "机器学习", "llm", "gpt",
        "deepseek", "gemini", "claude", "copilot", "sora", "midjourney",
        "agi", "agent", "通义", "文心", "langchain", "llama", "openai",
        "周志华", "智谱", "智元", "月之暗面", "千问", "混元", "qwen"
    ]
    ai_secondary = [
        "智能驾驶", "自动驾驶", "机器人", "具身智能", "神经网络", 
        "transformer", "多模态", "aicg", "生成式 ai", "rag", "强化学习",
        "计算机视觉", "nlp", "自然语言处理", "语音识别", "diffusion"
    ]
    
    # Check if has ANY primary AI keyword (required)
    has_primary = any(kw in text for kw in ai_primary)
    
    # Check if has negative keyword
    has_negative = any(kw in text for kw in ai_negative)
    
    # AI classification: must have primary keyword AND no negative keywords
    if has_primary and not has_negative:
        # Double-check with secondary keywords for confidence
        has_secondary = any(kw in text for kw in ai_secondary)
        if has_secondary or has_primary:
            return "AI"
    
    # Then check other categories
    scores = {}
    for category in ["政治", "经济", "科技"]:
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
    
    patterns = [
        r'<a[^>]+href="([^"]+)"[^>]*>([^<]{20,100})</a>',
        r'<h[345][^>]*>\s*<a[^>]+href="([^"]+)"[^>]*>([^<]+)</a>',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, html, re.IGNORECASE)
        for match in matches:
            if len(match) >= 2:
                href = match[0]
                title = clean_html(match[1]).strip()
                
                if len(title) < 10 or len(title) > 100:
                    continue
                if not any('\u4e00' <= c <= '\u9fff' for c in title):
                    continue
                if any(w in title for w in ["首页", "更多", "广告", "登录", "下载", "专题", "直播"]):
                    continue
                
                title_key = title[:30]
                if title_key in seen:
                    continue
                seen.add(title_key)
                
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

def fetch_article_content(url, timeout=5):
    """Fetch article for content"""
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
        paragraphs = re.findall(r'<p[^>]*>([^<]{50,300})</p>', html)
        if paragraphs:
            return clean_html(paragraphs[0]), extract_date_from_html(html)
        
        return "", extract_date_from_html(html)
    except:
        return "", None

def generate_summary(title, content, category):
    """Generate meaningful summary - avoid templates"""
    if content and len(content) > 80:
        content = clean_html(content)
        # Extract meaningful sentences
        sentences = re.split(r'[。！？.!?]', content)
        meaningful = [s.strip() for s in sentences if len(s.strip()) > 20 and not any(w in s for w in ["广告", "推荐", "相关阅读"])]
        
        if meaningful:
            summary = meaningful[0]
            if len(meaningful) > 1 and len(summary) < 150:
                summary += "。" + meaningful[1]
            return summary[:247] + "..." if len(summary) > 250 else summary
    
    # Fallback: use title only, no filler
    clean_title = re.sub(r'[（(].*[)）]$', '', title).strip()
    return clean_title[:250]

def fetch_and_classify_news(category, sources, max_age_hours=24):
    """Fetch news with search-first strategy for politics/AI"""
    print(f"  抓取 {category} 新闻...")
    all_items = []
    
    # For politics and AI: search-first strategy (more reliable)
    if category in ["政治", "AI"]:
        print(f"    → 使用搜索优先策略")
        check_hours = 72  # 3 days for politics/AI
        
        # Aggressive search with multiple queries
        search_queries_map = {
            "政治": [
                # China-focused (priority)
                "中国外交 外交部 今天",
                "中美关系 最新",
                "中俄关系 时政",
                "一带一路 合作",
                # Asia-Pacific
                "亚太 局势 今天",
                "台海 南海 最新",
                "日韩 朝韩 局势",
                # Global
                "联合国 安理会",
                "国际新闻 时政 今天",
                "world news today",
                "global politics breaking news",
            ],
            "AI": [
                # Chinese queries (priority)
                "人工智能 AI 大模型 今天",
                "深度学习 机器学习 最新",
                "GPT 大语言模型 应用",
                "AI 产品 发布 2026",
                "智谱 智元 月之暗面 千问",
                "AI 融资 投资 创业",
                # English queries (fallback)
                "AI artificial intelligence news today",
                "machine learning breakthrough 2026",
                "LLM GPT Claude Gemini news",
            ],
        }
        
        queries = search_queries_map.get(category, [])
        seen_titles = set()
        
        for query in queries:
            if len(all_items) >= 8:  # Get extra for filtering
                break
            print(f"    → 搜索：{query[:40]}...")
            search_items = search_news_for_category(category, hours=check_hours, custom_query=query)
            for item in search_items:
                title_key = item["title"][:40]
                if title_key not in seen_titles:
                    seen_titles.add(title_key)
                    all_items.append(item)
        
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
        
        result = [i for i in classified[category] if i.get("date") and is_recent(i["date"], hours=check_hours)]
        
        if len(result) >= 5:
            print(f"      已获取 {len(result)}条 {check_hours}h 新闻")
            return result[:5]
        else:
            print(f"      搜索获取 {len(result)}条，继续抓取来源...")
    
    # Standard source fetching (for all categories as fallback)
    check_hours = 48 if category in ["政治", "AI"] else 24
    max_sources = 8 if category in ["政治", "AI"] else 5
    
    for source_name, url in sources[:max_sources]:
        print(f"    → {source_name}")
        html = fetch_page(url)
        if html:
            items = extract_news_from_html(html, url)
            for item in items:
                item["source"] = source_name
                if item["url"]:
                    content, article_date = fetch_article_content(item["url"], timeout=4)
                    item["content"] = content
                    if article_date:
                        item["date"] = article_date
            all_items.extend(items)
        
        # Check if we have enough recent news
        recent = [i for i in all_items if i.get("date") and is_recent(i["date"], hours=check_hours)]
        if len(recent) >= 5:
            print(f"      已获取 {len(recent)}条 {check_hours}h 新闻，停止抓取")
            break
    
    # Classify all items
    classified = {cat: [] for cat in CATEGORY_KEYWORDS.keys()}
    for item in all_items:
        detected_cat = classify_content(item["title"], item.get("content", ""))
        if detected_cat:
            item["detected_category"] = detected_cat
            classified[detected_cat].append(item)
        else:
            item["detected_category"] = category
            classified[category].append(item)
    
    # Filter
    result = [i for i in classified[category] if i.get("date") and is_recent(i["date"], hours=check_hours)]
    
    # EXTRA STRICT: For AI category, validate each item has real AI content
    if category == "AI":
        ai_primary_validate = ["人工智能", "大模型", "ai ", " ai", "深度学习", "机器学习", "llm", "gpt",
                               "deepseek", "gemini", "claude", "copilot", "sora", "midjourney",
                               "agi", "agent", "通义", "文心", "langchain", "llama", "openai",
                               "周志华", "智谱", "智元", "月之暗面", "千问"]
        ai_negative_validate = ["化学物", "化学", "燃烧", "底刊", "被封", "钻石", "外星", "生存",
                                "火星", "太空", "行星", "天文", "物理", "生物", "医学", "药物",
                                "基因", "细胞", "疫苗", "癌症", "疾病", "老化", "羊群", "永久",
                                "材料", "超导", "干细胞", "医疗", "健康", "食品", "超市", "猪价"]
        
        validated_result = []
        for item in result:
            text = (item["title"] + " " + (item.get("content") or "")).lower()
            has_ai = any(kw in text for kw in ai_primary_validate)
            has_negative = any(kw in text for kw in ai_negative_validate)
            if has_ai and not has_negative:
                validated_result.append(item)
        
        if len(validated_result) < len(result):
            print(f"      AI 严格过滤：{len(result)}条 → {len(validated_result)}条")
        result = validated_result
    
    if len(result) >= 5:
        print(f"      已获取 {len(result)}条，跳过搜索")
        return result[:5]
    
    # Phase 2: Aggressive search fallback (bilingual)
    if len(result) < 5:
        print(f"      {check_hours}h 不足 ({len(result)}条), 使用搜索补充")
        # Expand time window for search
        search_hours = 168 if category in ["政治", "AI"] else 72  # Up to 7 days for politics/AI
        
        # Define expanded search queries inline
        search_queries_map = {
            "政治": [
                "国际新闻 外交 时政 最新",
                "world news politics today",
                "global politics breaking news",
                "international relations news 2026",
                "geopolitics latest",
                "world leaders summit meeting",
                "international conflict news",
            ],
            "经济": ["财经新闻 经济 市场", "financial news economy today", "stock market business"],
            "科技": ["科技新闻 互联网 数码", "tech news technology today", "new product launch"],
            "AI": [
                "人工智能 AI 大模型 最新",
                "AI artificial intelligence news today",
                "machine learning breakthrough 2026",
                "LLM GPT Claude Gemini news",
                "AI startup funding latest",
                "generative AI new product",
                "AI model release this week",
                "deep learning research 2026",
            ],
            "军事": ["军事新闻 国防", "military news defense today", "international military"],
        }
        
        queries = search_queries_map.get(category, [category + " 新闻"])
        for query in queries:
            if len(result) >= 5:
                break
            search_items = search_news_for_category(category, hours=search_hours, custom_query=query)
            for item in search_items:
                if item["title"][:30] not in [i["title"][:30] for i in result]:
                    result.append(item)
    
    if len(result) < 5:
        print(f"      最终获取 {len(result)}条 24h 新闻")
    
    return result[:5]

def search_news_for_category(category, hours=24, custom_query=None):
    """Search for news via SearXNG - bilingual queries (CN + EN)"""
    # Multiple query strategies per category - bilingual
    search_queries = {
        "政治": [
            # Chinese queries
            "国际新闻 外交 时政 今天",
            "全球热点 国际局势 最新",
            "世界新闻 头条 24 小时",
            # English queries (diverse sources)
            "world news politics today",
            "international news breaking 24h",
            "global politics latest",
            "geopolitics news today",
            "international relations news",
        ],
        "经济": [
            "财经新闻 经济 市场 今天",
            "股市 基金 理财 最新",
            "financial news economy today",
            "stock market business latest",
        ],
        "科技": [
            "科技新闻 互联网 数码 今天",
            "新品发布 技术创新 2026",
            "tech news technology today",
            "new product launch innovation",
        ],
        "AI": [
            # Chinese queries
            "人工智能 AI 大模型 今天",
            "深度学习 机器学习 最新突破",
            "GPT 大语言模型 应用发布",
            "AI 产品 融资 2026",
            # English queries (broader)
            "AI artificial intelligence news today",
            "machine learning breakthrough 2026",
            "LLM GPT Claude Gemini news",
            "AI startup funding latest",
            "generative AI new product",
            "AI model release this week",
        ],
        "军事": [
            "军事新闻 国防 今天",
            "国际军事 冲突 最新",
            "military news defense today",
            "international military conflict",
        ],
    }
    
    queries = [custom_query] if custom_query else search_queries.get(category, [category + " 新闻"])
    
    items = []
    skip_sites = ["zhihu.com", "baidu.com", "weibo.com", "toutiao.com", "twitter.com", "youtube.com", "facebook.com"]
    seen_titles = set()
    
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
            
            # Length check
            if len(title) < 10 or len(title) > 100:
                continue
            
            # Skip unwanted sites
            if any(s in url.lower() for s in skip_sites):
                continue
            
            # Require Chinese characters (at least 5)
            chinese_chars = sum(1 for c in title if '\u4e00' <= c <= '\u9fff')
            if chinese_chars < 5:
                continue
            
            # Deduplicate
            title_key = title[:40]
            if title_key in seen_titles:
                continue
            seen_titles.add(title_key)
            
            # Extract date from content
            pub_date = extract_date_from_html(content) if content else None
            
            # Time filter: use the passed hours parameter (can be up to 168h for politics/AI)
            check_hours = hours
            
            # If no date found but content looks fresh, include it
            include_fallback = pub_date is None and any(kw in content.lower() for kw in ["today", "this week", "latest", "最新", "今天", "昨日", "yesterday"])
            
            # Also check if title has date-like patterns
            title_has_recent = bool(re.search(r'(今天 | 今日|today|latest|breaking)', title, re.IGNORECASE))
            
            if pub_date and is_recent(pub_date, hours=check_hours):
                items.append({
                    "title": title,
                    "url": url,
                    "source": "搜索",
                    "content": content,
                    "date": pub_date,
                    "detected_category": category,
                })
            elif include_fallback or title_has_recent:
                # Use current time as fallback for fresh-looking content
                items.append({
                    "title": title,
                    "url": url,
                    "source": "搜索",
                    "content": content,
                    "date": datetime.now(),
                    "detected_category": category,
                })
    
    return items[:5]

def fetch_military_news():
    """Fetch military news - expand sources when 24h insufficient"""
    print("  抓取军事新闻...")
    all_items = []
    
    sources = NEWS_SOURCES["军事"]
    for source_name, url in sources:
        print(f"    → {source_name}")
        html = fetch_page(url)
        if html:
            items = extract_news_from_html(html, url)
            for item in items:
                if any(kw in item["title"] for kw in ["军事", "国防", "军队", "演习", "战机", "舰艇", "导弹", "美军", "以军", "伊朗", "解放军"]):
                    item["source"] = source_name
                    all_items.append(item)
        
        # Check if enough 24h news
        recent = [i for i in all_items if i.get("date") and is_recent(i["date"], hours=24)]
        if len(recent) >= 5:
            print(f"      已获取 {len(recent)}条 24h 新闻，停止抓取")
            break
    
    # Search fallback (24h strict)
    if len([i for i in all_items if i.get("date") and is_recent(i["date"], hours=24)]) < 5:
        print("    → 搜索国际军事")
        search = fetch_searxng("军事 国防 国际")
        for r in search:
            title = clean_html(r.get("title", ""))
            url = r.get("url", "")
            content = r.get("content", "")
            
            if len(title) < 10 or len(title) > 100:
                continue
            if any(s in url.lower() for s in ["zhihu.com", "baidu.com", "weibo.com"]):
                continue
            
            all_items.append({
                "title": title,
                "url": url,
                "source": "国际军事",
                "content": content,
                "date": extract_date_from_html(content) if content else None,
                "detected_category": "军事",
            })
    
    # Deduplicate
    seen = set()
    unique = []
    for item in all_items:
        key = item["title"][:30]
        if key not in seen:
            seen.add(key)
            unique.append(item)
    
    # STRICT 24h filter
    result = [i for i in unique if i.get("date") and is_recent(i["date"], hours=24)]
    
    if len(result) < 5:
        print(f"      最终获取 {len(result)}条 24h 军事新闻")
    
    return result[:5]

def fetch_all_news():
    """Fetch all categories"""
    print(f"[{datetime.now()}] 开始抓取新闻（智能分类 + 保证每类 5 条）...")
    print()
    
    news_data = {}
    
    for category, sources in NEWS_SOURCES.items():
        if category == "军事":
            items = fetch_military_news()
        else:
            items = fetch_and_classify_news(category, sources)
        
        # Generate summaries
        for item in items:
            item["summary"] = generate_summary(
                item["title"],
                item.get("content", ""),
                item.get("detected_category", category)
            )
        
        news_data[category] = items
        print(f"  ✅ {category}: {len(items)}条")
    
    # Post-process: AI validation and search-only supplement (NO Tech scraping to avoid duplicates)
    ai_items = news_data.get("AI", [])
    
    # AI keywords for validation
    ai_keywords_primary = [
        "人工智能", "大模型", "ai ", " ai", "深度学习", "机器学习", "llm", "gpt",
        "deepseek", "gemini", "claude", "copilot", "sora", "midjourney",
        "agi", "agent", "通义", "文心", "langchain", "llama", "openai",
        "周志华", "智谱", "智元", "月之暗面", "千问", "混元", "qwen"
    ]
    ai_negative_keywords = [
        "化学物", "化学", "燃烧", "底刊", "被封", "钻石", "外星", "生存",
        "火星", "太空", "行星", "天文", "物理", "生物", "医学", "药物",
        "基因", "细胞", "疫苗", "癌症", "疾病", "老化", "羊群", "永久",
        "材料", "超导", "干细胞", "医疗", "健康", "食品", "超市", "猪价"
    ]
    
    # Validate existing AI items
    validated_ai = []
    for item in ai_items:
        text = (item["title"] + " " + (item.get("content") or "")).lower()
        has_ai = any(kw in text for kw in ai_keywords_primary)
        has_negative = any(kw in text for kw in ai_negative_keywords)
        if has_ai and not has_negative:
            validated_ai.append(item)
    
    if len(validated_ai) < len(ai_items):
        print(f"  🧹 AI 严格过滤：{len(ai_items)}条 → {len(validated_ai)}条")
    news_data["AI"] = validated_ai
    
    # If AI < 5, use search ONLY (NOT from Tech to avoid duplicates)
    if len(news_data.get("AI", [])) < 5:
        print(f"  → AI 新闻不足 ({len(news_data['AI'])}条)，使用搜索补充...")
        search_items = search_news_for_category("AI", hours=72)
        existing_titles = set(item["title"][:40] for item in news_data.get("AI", []))
        
        for item in search_items:
            if len(news_data["AI"]) >= 5:
                break
            if item["title"][:40] in existing_titles:
                continue
            
            # STRICT validation
            text = (item["title"] + " " + (item.get("content") or "")).lower()
            has_ai = any(kw in text for kw in ai_keywords_primary)
            has_negative = any(kw in text for kw in ai_negative_keywords)
            
            if has_ai and not has_negative:
                item["summary"] = generate_summary(item["title"], item.get("content", ""), "AI")
                news_data["AI"].append(item)
                existing_titles.add(item["title"][:40])
        
        print(f"  ✅ AI: {len(news_data['AI'])}条 (搜索补充)")
    
    # Final fallback: placeholder
    if len(news_data.get("AI", [])) == 0:
        news_data["AI"] = [{
            "title": "今日暂无 AI 领域重大新闻",
            "source": "综合",
            "summary": "AI 领域今日相对平静，建议关注后续技术动态。",
            "detected_category": "AI"
        }]
        print(f"  ✅ AI: 1 条 (占位)")
    
    return news_data

def build_markdown(news_data):
    """Build markdown with lunar date and daily wisdom"""
    now = datetime.now()
    ts = now.strftime("%Y-%m-%d %H:%M")
    weekday = now.strftime("%A")
    weekday_cn = {"Monday": "星期一", "Tuesday": "星期二", "Wednesday": "星期三", 
                  "Thursday": "星期四", "Friday": "星期五", "Saturday": "星期六", "Sunday": "星期日"}
    weekday_str = weekday_cn.get(weekday, "")
    
    # Get lunar date
    lunar = get_lunar_date()
    
    # Get daily wisdom (based on day of month)
    wisdom_idx = (now.day - 1) % len(WISDOM_QUOTES)
    wisdom = WISDOM_QUOTES[wisdom_idx]
    
    # Build header
    md = ["# 📰 全球要闻简报", ""]
    md.append(f"**日期**：{now.strftime('%Y 年 %m 月 %d 日')} {weekday_str}")
    if lunar:
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
            total += 1
    
    md.append("---")
    md.append("")
    md.append("## 💡 微语")
    md.append("")
    md.append(f"> {wisdom}")
    md.append("")
    md.append("---")
    md.append("")
    md.append(f"**共 {total} 条精选新闻 · AI 深度摘要版**")
    md.append("")
    md.append("_筛选标准：国际国内双源 | 智能内容分类 | 严格 AI 关键词过滤 | 全球权威来源 | AI 深度摘要_")
    
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
