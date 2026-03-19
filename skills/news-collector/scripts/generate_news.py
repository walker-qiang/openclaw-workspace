#!/usr/bin/env python3
"""
News Collector v9.0
- Thread-safe stats via threading.Lock
- Parallel article content fetching (fixes N+1 bottleneck)
- Category-level parallelism (all 5 categories fetched concurrently)
- fetch_searxng uses retry + stats tracking
- Dynamic lunar calendar date via cnlunar
- Config-driven from config.json
"""

import os
import re
import json
import time
import threading
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from html import unescape

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "..", "config.json")
SEARXNG_URL = os.environ.get("SEARXNG_URL", "http://localhost:8080")
NEWS_OUTPUT = os.environ.get("NEWS_OUTPUT", "/tmp/news_brief.md")


def load_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"ERROR: Failed to load config from {CONFIG_PATH}: {e}")
        raise SystemExit(1)


CFG = load_config()

NEWS_SOURCES = {k: [tuple(v) for v in vs] for k, vs in CFG["news_sources"].items()}
CATEGORY_KEYWORDS = CFG["category_keywords"]
AI_MUST_HAVE = CFG["ai_must_have"]
AI_MUST_NOT_HAVE = CFG["ai_must_not_have"]
WISDOM_QUOTES = CFG["wisdom_quotes"]
CATEGORY_ICONS = CFG["category_icons"]
TIME_WINDOWS = CFG["time_windows"]
MAX_ITEMS = CFG["max_items_per_category"]
MAX_WORKERS = CFG["max_workers"]
FETCH_TIMEOUT = CFG["fetch_timeout"]
ARTICLE_TIMEOUT = CFG["article_timeout"]
RETRY_ATTEMPTS = CFG["retry_attempts"]
RETRY_DELAY = CFG["retry_delay_seconds"]

_stats = {"success": 0, "failed": 0, "retried": 0}
_stats_lock = threading.Lock()


def _inc_stat(key):
    with _stats_lock:
        _stats[key] += 1


# ---------------------------------------------------------------------------
# Network helpers with retry
# ---------------------------------------------------------------------------

def _do_fetch(url, timeout):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/json",
        "Accept-Language": "zh-CN,zh;q=0.9",
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def fetch_with_retry(url, timeout=None, retries=None):
    timeout = timeout or FETCH_TIMEOUT
    retries = retries if retries is not None else RETRY_ATTEMPTS
    for attempt in range(1 + retries):
        try:
            data = _do_fetch(url, timeout)
            _inc_stat("success")
            return data
        except Exception:
            if attempt < retries:
                _inc_stat("retried")
                time.sleep(RETRY_DELAY)
    _inc_stat("failed")
    return None


def fetch_searxng(query):
    params = urllib.parse.urlencode({"q": query, "format": "json"})
    url = f"{SEARXNG_URL}/search?{params}"
    raw = fetch_with_retry(url, timeout=FETCH_TIMEOUT, retries=1)
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return data.get("results", [])
    except (json.JSONDecodeError, ValueError):
        return []


# ---------------------------------------------------------------------------
# HTML / text helpers
# ---------------------------------------------------------------------------

def clean_html(text):
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', '', text)
    text = unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def extract_date_from_html(html):
    if not html:
        return None
    match = re.search(r'(\d{4})-(\d{2})-(\d{2})[T\s](\d{2}):(\d{2})', html)
    if match:
        try:
            return datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)),
                            int(match.group(4)), int(match.group(5)))
        except ValueError:
            pass
    match = re.search(r'(\d{4})-(\d{2})-(\d{2})', html)
    if match:
        try:
            return datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            pass
    if '今天' in html or '今日' in html or 'today' in html.lower():
        return datetime.now()
    if '昨天' in html or 'yesterday' in html.lower():
        return datetime.now() - timedelta(days=1)
    return None


def is_recent(date, hours=24):
    if not date:
        return False
    return (datetime.now() - date).total_seconds() <= (hours * 3600)


# ---------------------------------------------------------------------------
# Lunar calendar helper
# ---------------------------------------------------------------------------

def get_lunar_date_str():
    """Return today's lunar date string, e.g. '二月初一'. Falls back gracefully."""
    try:
        import cnlunar
        lunar = cnlunar.Lunar(datetime.now())
        month = lunar.lunarMonthCn.replace("小", "").replace("大", "")
        return f"{month}{lunar.lunarDayCn}"
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

def classify_content(title, content=""):
    text = (title + " " + content).lower()

    if any(kw.lower() in text for kw in CATEGORY_KEYWORDS["军事"]):
        return "军事"

    scores = {}
    for category in ["政治", "经济", "AI", "科技"]:
        keywords = CATEGORY_KEYWORDS[category]
        scores[category] = sum(1 for kw in keywords if kw.lower() in text)

    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else None


def validate_ai_news(title, content=""):
    text = (title + " " + (content or "")).lower()
    if not any(kw.lower() in text for kw in AI_MUST_HAVE):
        return False
    if any(kw in text for kw in AI_MUST_NOT_HAVE):
        return False
    return True


# ---------------------------------------------------------------------------
# News extraction from HTML pages
# ---------------------------------------------------------------------------

def extract_news_from_html(html, source_url=""):
    if not html:
        return []

    items = []
    base_url = "/".join(source_url.split("/")[:3])
    seen = set()
    page_date = extract_date_from_html(html)
    current_month = datetime.now().month

    matches = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>([^<]{20,120})</a>', html, re.IGNORECASE)

    for href, raw_title in matches:
        title = clean_html(raw_title).strip()

        if len(title) < 15 or len(title) > 80:
            continue
        if sum(1 for c in title if '\u4e00' <= c <= '\u9fff') < 5:
            continue

        skip_words = ["首页", "更多", "广告", "登录", "下载", "专题", "直播",
                      "导航", "列表", "关于我们", "联系我们", "许可证", "经营许可证", "京 B2"]
        if any(w in title for w in skip_words):
            continue

        has_month_range = bool(re.search(r'\d{1,2}[-~一—至]\d{1,2}\u6708', title))
        all_months = re.findall(r'(\d{1,2})\u6708', title)
        skip_item = False
        for month_str in all_months:
            mentioned = int(month_str)
            if 1 <= mentioned <= 12 and mentioned != current_month:
                if has_month_range:
                    continue
                skip_item = True
                break
        if skip_item:
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


def fetch_article_content(url, timeout=None):
    timeout = timeout or ARTICLE_TIMEOUT
    try:
        html = fetch_with_retry(url, timeout=timeout, retries=0)
        if not html:
            return "", None

        match = re.search(
            r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']',
            html, re.IGNORECASE)
        if match:
            desc = unescape(match.group(1))
            if len(desc) > 30:
                return desc, extract_date_from_html(html)

        paragraphs = re.findall(r'<p[^>]*>([^<]{50,500})</p>', html)
        if paragraphs:
            return clean_html(paragraphs[0]), extract_date_from_html(html)

        return "", extract_date_from_html(html)
    except Exception:
        return "", None


# ---------------------------------------------------------------------------
# Summary generation
# ---------------------------------------------------------------------------

def generate_summary(title, content, category):
    """50-80 chars optimal, max 100. Subject-Verb-Object, data-first."""
    if not content:
        clean = re.sub(r'[（(].*[)）]$', '', title).strip()
        return clean[:80]

    content = clean_html(content)

    low_quality = ["首页>", "导航", "专题", "广告", "推荐", "登录", "注册", "下载 APP", "扫码"]
    if any(p in content for p in low_quality):
        return re.sub(r'[（(].*[)）]$', '', title).strip()[:80]

    if re.search(r'我们是 | 旗下 | 新媒体 | 专注于 | 致力于', content):
        return re.sub(r'[（(].*[)）]$', '', title).strip()[:80]

    sentences = re.split(r'[。！？.!?]', content)
    meaningful = []
    for s in sentences:
        s = s.strip()
        if len(s) < 20:
            continue
        if any(w in s for w in ["广告", "推荐", "首页", "导航", "扫码", "关注", "更多"]):
            continue
        if re.match(r'^[^\u4e00-\u9fa5]*([\u4e00-\u9fa5]{2,4}[,，][^\u4e00-\u9fa5]*)*[\u4e00-\u9fa5]{2,4}[,，]', s):
            continue
        if s.count(',') + s.count('，') > len(s) / 2:
            continue
        meaningful.append(s)

    if not meaningful:
        return re.sub(r'[（(].*[)）]$', '', title).strip()[:80]

    lead = meaningful[0]
    lead = re.sub(r'[（(][^)）]*[)）]', '', lead).strip()
    lead = re.sub(r'^[,，:：\s]+', '', lead)

    data_point = ""
    for s in meaningful[1:4]:
        if re.search(r'\d+[.%亿元]', s):
            data_point = re.sub(r'[（(][^)）]*[)）]', '', s).strip()
            break

    if data_point and len(lead) < 60:
        summary = lead + "。" + data_point
    else:
        summary = lead

    if len(summary) > 100:
        summary = summary[:97] + "..."

    summary = re.sub(r'^[^\u4e00-\u9fa5]+[:：]', '', summary).strip()
    summary = re.sub(r'^[,，:：\s]+', '', summary)
    summary = re.sub(r'[,，][^\u4e00-\u9fa5]*([\u4e00-\u9fa5]{2,4}[,，]){2,}.*$', '', summary)

    return summary[:100]


# ---------------------------------------------------------------------------
# Unified category fetching with parallel article content
# ---------------------------------------------------------------------------

def _enrich_item(item, category):
    """Fetch article content for a single item. Designed to run in thread pool."""
    if category == "军事":
        if not any(kw in item["title"] for kw in CATEGORY_KEYWORDS["军事"]):
            return None

    if item["url"]:
        content, article_date = fetch_article_content(item["url"])
        if content and re.search(r'我们是 | 旗下 | 新媒体 | 专注于', content):
            return None
        item["content"] = content
        if article_date:
            item["date"] = article_date

    return item


def _fetch_source(source_name, url, category):
    """Fetch a single source, then parallel-enrich article content."""
    html = fetch_with_retry(url)
    if not html:
        return []

    items = extract_news_from_html(html, url)
    for item in items:
        item["source"] = source_name

    # Limit candidates before fetching article details
    candidates = items[:MAX_ITEMS * 2]

    # Parallel fetch article content for candidates
    result = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(_enrich_item, item, category): item for item in candidates}
        for future in as_completed(futures):
            try:
                enriched = future.result()
                if enriched is not None:
                    result.append(enriched)
            except Exception:
                pass

    return result


def _fetch_category(category, sources):
    """Fetch and classify news for a single category. Designed for top-level parallelism."""
    print(f"  抓取 {category} 新闻...")
    check_hours = TIME_WINDOWS.get(category, 24)

    all_items = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {
            pool.submit(_fetch_source, name, url, category): name
            for name, url in sources
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                items = future.result()
                print(f"    → {name}: {len(items)} 条")
                all_items.extend(items)
            except Exception as e:
                print(f"    → {name}: 抓取失败 ({e})")

    # Classify and filter
    classified = {cat: [] for cat in CATEGORY_KEYWORDS}
    for item in all_items:
        detected = classify_content(item["title"], item.get("content", ""))
        if detected:
            item["detected_category"] = detected
            classified[detected].append(item)
        else:
            item["detected_category"] = category
            classified[category].append(item)

    result = [i for i in classified[category]
              if i.get("date") and is_recent(i["date"], hours=check_hours)]

    # AI: strict validation + search supplement
    if category == "AI":
        validated = [i for i in result if validate_ai_news(i["title"], i.get("content", ""))]
        if len(validated) < len(result):
            print(f"      AI 严格过滤：{len(result)} 条 → {len(validated)} 条")
        result = validated

        if len(result) < 3:
            print(f"      AI 不足 ({len(result)} 条)，使用搜索补充...")
            search_items = _search_ai_news(hours=168)
            existing_keys = {i["title"][:30] for i in result}
            for item in search_items:
                if len(result) >= MAX_ITEMS:
                    break
                if validate_ai_news(item["title"], item.get("content", "")):
                    if item["title"][:30] not in existing_keys:
                        result.append(item)
                        existing_keys.add(item["title"][:30])
            if result:
                print(f"      搜索补充后：{len(result)} 条")

    # Deduplicate
    seen = set()
    unique = []
    for item in result:
        key = item["title"][:30]
        if key not in seen:
            seen.add(key)
            unique.append(item)

    # Generate summaries
    for item in unique:
        item["summary"] = generate_summary(
            item["title"],
            item.get("content", ""),
            item.get("detected_category", category),
        )

    count = len(unique[:MAX_ITEMS])
    print(f"      最终获取 {count} 条 {check_hours}h 新闻")
    return category, unique[:MAX_ITEMS]


def _search_ai_news(hours=48):
    queries = CFG.get("ai_search_queries", [])
    skip_sites = CFG.get("ai_search_skip_sites", [])
    items = []
    seen = set()

    for query in queries:
        if len(items) >= MAX_ITEMS:
            break
        results = fetch_searxng(query)
        for r in results:
            if len(items) >= MAX_ITEMS:
                break

            title = clean_html(r.get("title", ""))
            url = r.get("url", "")
            content = r.get("content", "")

            if len(title) < 15 or len(title) > 100:
                continue
            if any(s in url.lower() for s in skip_sites):
                continue
            if sum(1 for c in title if '\u4e00' <= c <= '\u9fff') < 5:
                continue

            skip_patterns = ["教程", "指南", "免费使用", "下载", "APP", "推广", "怎么使用"]
            if any(p in title for p in skip_patterns):
                continue

            title_key = title[:30]
            if title_key in seen:
                continue
            seen.add(title_key)

            pub_date = extract_date_from_html(content) if content else None

            items.append({
                "title": title,
                "url": url,
                "source": "搜索",
                "content": content,
                "date": pub_date or datetime.now(),
                "detected_category": "AI",
            })

    print(f"      搜索获取 {len(items)} 条 AI 新闻")
    return items


# ---------------------------------------------------------------------------
# Markdown output
# ---------------------------------------------------------------------------

def fetch_all_news():
    print(f"[{datetime.now()}] 开始抓取新闻...")
    print()

    news_data = {}
    # All categories in parallel
    with ThreadPoolExecutor(max_workers=len(NEWS_SOURCES)) as pool:
        futures = {
            pool.submit(_fetch_category, cat, sources): cat
            for cat, sources in NEWS_SOURCES.items()
        }
        for future in as_completed(futures):
            cat_name = futures[future]
            try:
                category, items = future.result()
                news_data[category] = items
                print(f"  ✅ {category}: {len(items)} 条")
            except Exception as e:
                print(f"  ❌ {cat_name}: 失败 ({e})")
                news_data[cat_name] = []

    # Preserve original category order from config
    ordered = {}
    for cat in NEWS_SOURCES:
        ordered[cat] = news_data.get(cat, [])
    return ordered


def build_markdown(news_data):
    now = datetime.now()
    ts = now.strftime("%Y-%m-%d %H:%M")
    weekday_cn = {
        "Monday": "星期一", "Tuesday": "星期二", "Wednesday": "星期三",
        "Thursday": "星期四", "Friday": "星期五", "Saturday": "星期六", "Sunday": "星期日",
    }
    weekday_str = weekday_cn.get(now.strftime("%A"), "")

    wisdom_idx = (now.day - 1) % len(WISDOM_QUOTES)
    wisdom = WISDOM_QUOTES[wisdom_idx]

    lunar_str = get_lunar_date_str()

    md = ["# 📰 全球要闻简报", ""]
    md.append(f"**日期**：{now.strftime('%Y 年 %m 月 %d 日')} {weekday_str}")
    if lunar_str:
        md.append(f"**农历**：{lunar_str}")
    md.append("")
    md.append(f"_更新时间：{ts}_")
    md.append("")
    md.append("---")
    md.append("")

    total = 0
    for category, items in news_data.items():
        icon = CATEGORY_ICONS.get(category, "📌")
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
    md.append(
        f"_筛选标准：权威媒体白名单 | 智能内容分类 | 严格 AI 过滤 | 24-72h 时效 | 50-80 字精炼摘要_"
    )
    md.append("")
    with _stats_lock:
        md.append(
            f"_网络统计：成功 {_stats['success']} | 重试 {_stats['retried']} | 失败 {_stats['failed']}_"
        )

    return "\n".join(md)


def main():
    news_data = fetch_all_news()
    print("\n生成文档...")
    md = build_markdown(news_data)

    with open(NEWS_OUTPUT, "w", encoding="utf-8") as f:
        f.write(md)

    print(f"✓ 已保存到 {NEWS_OUTPUT}")
    print(f"✓ 总字符数：{len(md)}")
    with _stats_lock:
        print(f"✓ 网络统计：成功 {_stats['success']} | 重试 {_stats['retried']} | 失败 {_stats['failed']}")

    return NEWS_OUTPUT


if __name__ == "__main__":
    main()
