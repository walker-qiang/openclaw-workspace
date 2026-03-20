#!/usr/bin/env python3
"""
News Collector v11.0
- Importance-based ranking: major powers, crises, breakthroughs > minor events
- Auto-translation: English news translated to Chinese (not filtered out)
- RSS/Atom feed support (Google News, Al Jazeera, CNBC, TechCrunch)
- Mixed Chinese + international sources for true global coverage
- SearxNG supplement for ALL categories
- Thread-safe stats, parallel fetching at source and category level
- Self-contained lunar calendar (no external deps)
- Config-driven from config.json
"""

import os
import re
import json
import time
import threading
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
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
SEARCH_QUERIES = CFG.get("search_queries", {})
SEARCH_SKIP_SITES = CFG.get("search_skip_sites", [])
IMPORTANCE_KEYWORDS = CFG.get("importance_keywords", {})

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
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
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
# Translation: English → Chinese via Google Translate (no API key)
# ---------------------------------------------------------------------------

def _needs_translation(text):
    """Return True if text is predominantly non-Chinese and needs translation."""
    if not text:
        return False
    cn_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    alpha_chars = sum(1 for c in text if c.isalpha())
    if alpha_chars == 0:
        return False
    return cn_chars / alpha_chars < 0.3


def _translate_to_chinese(text):
    """Translate non-Chinese text to Chinese. Returns original on failure."""
    if not text or not _needs_translation(text):
        return text
    try:
        encoded = urllib.parse.quote(text[:500])
        url = (
            "https://translate.googleapis.com/translate_a/single"
            f"?client=gtx&sl=auto&tl=zh-CN&dt=t&q={encoded}"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
            return "".join(part[0] for part in data[0] if part[0])
    except Exception:
        return text


# ---------------------------------------------------------------------------
# Importance scoring: rank news by geopolitical/economic significance
# ---------------------------------------------------------------------------

def _importance_score(item):
    """Score by significance. Higher = more important. Major powers, crises,
    breakthroughs, and tech giants all contribute to the score."""
    text = (item.get("title", "") + " " + item.get("content", "")).lower()
    score = 0
    for kw in IMPORTANCE_KEYWORDS.get("major_powers", []):
        if kw.lower() in text:
            score += 15
            break
    for kw in IMPORTANCE_KEYWORDS.get("crises", []):
        if kw.lower() in text:
            score += 10
            break
    for kw in IMPORTANCE_KEYWORDS.get("breakthroughs", []):
        if kw.lower() in text:
            score += 5
            break
    for kw in IMPORTANCE_KEYWORDS.get("tech_giants", []):
        if kw.lower() in text:
            score += 8
            break
    if item.get("content"):
        score += 2
    return score


# ---------------------------------------------------------------------------
# HTML / text helpers
# ---------------------------------------------------------------------------

def clean_html(text):
    if not text:
        return ""
    text = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', '', text)
    text = unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _parse_date(date_str):
    """Parse date from various formats: RFC 822, ISO 8601, YYYY-MM-DD."""
    if not date_str:
        return None
    date_str = date_str.strip()
    # RFC 822 (RSS pubDate)
    try:
        dt = parsedate_to_datetime(date_str)
        return dt.replace(tzinfo=None)
    except Exception:
        pass
    # ISO 8601 (Atom published)
    try:
        clean = re.sub(r'(\.\d+)?([+-]\d{2}:\d{2}|Z)$', '', date_str)
        return datetime.fromisoformat(clean)
    except Exception:
        pass
    # YYYY-MM-DD with optional time
    m = re.search(r'(\d{4})-(\d{2})-(\d{2})[T\s]?(\d{2})?:?(\d{2})?', date_str)
    if m:
        try:
            parts = [int(m.group(i)) for i in range(1, 4)]
            h = int(m.group(4)) if m.group(4) else 0
            mi = int(m.group(5)) if m.group(5) else 0
            return datetime(parts[0], parts[1], parts[2], h, mi)
        except ValueError:
            pass
    if '今天' in date_str or '今日' in date_str:
        return datetime.now()
    if '昨天' in date_str:
        return datetime.now() - timedelta(days=1)
    return None


def is_recent(date, hours=24):
    """Check if a date is within the given time window. None = assume recent."""
    if not date:
        return True
    try:
        if hasattr(date, 'tzinfo') and date.tzinfo:
            date = date.replace(tzinfo=None)
        return (datetime.now() - date).total_seconds() <= (hours * 3600)
    except Exception:
        return True


# ---------------------------------------------------------------------------
# RSS / Atom feed parser
# ---------------------------------------------------------------------------

def _clean_rss_title(title, source_name=""):
    """Strip trailing ' - 新浪网' / ' - 36kr.com' source suffix from RSS titles."""
    if not source_name.startswith("Google"):
        return title
    # "标题内容 - 新浪网" or "标题 - 36kr.com" → "标题内容"
    m = re.search(r'\s*[-–—|]\s*[\w\u4e00-\u9fff.·]+(?:\s*[\w\u4e00-\u9fff.·]+)*$', title)
    if m and len(title[:m.start()].strip()) >= 6:
        return title[:m.start()].strip()
    return title


def _is_chinese_content(title):
    """Check if title has enough Chinese characters for a Chinese news brief."""
    cn_chars = sum(1 for c in title if '\u4e00' <= c <= '\u9fff')
    return cn_chars >= 5


def parse_rss_feed(xml_text, source_name=""):
    """Parse RSS 2.0 or Atom feed into a list of news items."""
    items = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    seen = set()

    def _process_entry(title, link, desc, pub):
        date = _parse_date(pub)

        if not title or len(title) < 8:
            return

        title = _clean_rss_title(title, source_name)

        key = title[:40]
        if key in seen:
            return
        seen.add(key)

        # Google News RSS: description = "title source" — not useful
        if desc and desc.startswith(title[:15]):
            desc = ""

        items.append({
            "title": title,
            "url": link,
            "source": source_name,
            "content": desc,
            "date": date,
        })

    # RSS 2.0: <rss><channel><item>
    for entry in root.findall('.//item'):
        _process_entry(
            clean_html(entry.findtext('title', '')),
            entry.findtext('link', ''),
            clean_html(entry.findtext('description', '')),
            entry.findtext('pubDate', ''),
        )

    if items:
        return items

    # Atom: <feed><entry>
    for entry in root.iter():
        if entry.tag.endswith('}entry') or entry.tag == 'entry':
            ns = entry.tag.replace('entry', '') if '}' in entry.tag else ''
            title_el = entry.find(f'{ns}title')
            link_el = entry.find(f'{ns}link')
            desc_el = entry.find(f'{ns}summary') or entry.find(f'{ns}content')
            pub_el = entry.find(f'{ns}published') or entry.find(f'{ns}updated')

            _process_entry(
                clean_html(title_el.text if title_el is not None and title_el.text else ''),
                link_el.get('href', '') if link_el is not None else '',
                clean_html(desc_el.text if desc_el is not None and desc_el.text else ''),
                pub_el.text if pub_el is not None and pub_el.text else '',
            )

    return items


# ---------------------------------------------------------------------------
# Lunar calendar — self-contained, no external dependencies
# ---------------------------------------------------------------------------

_LUNAR_INFO = [
    0x1e4a2, 0x095c0, 0x14ae0, 0x0a9a5, 0x1a4c0, 0x1b2a0, 0x0cab4, 0x0ad40, 0x135a0, 0x0aba2,
    0x095c0, 0x14b66, 0x149a0, 0x1a4a0, 0x1a4b5, 0x16a80, 0x1ad40, 0x15b42, 0x12b60, 0x092f7,
    0x092e0, 0x14960, 0x16965, 0x0d4a0, 0x0da80, 0x156b4, 0x056c0, 0x12ae0, 0x0a5e2, 0x092e0,
    0x0cac6, 0x1a940, 0x1d4a0, 0x0d535, 0x0b5a0, 0x056c0, 0x10dd3, 0x125c0, 0x191b7, 0x192a0,
    0x1a940, 0x1b156, 0x16aa0, 0x0ad40, 0x14b74, 0x04ba0, 0x125a0, 0x1a562, 0x152a0, 0x16aa7,
    0x0d940, 0x16aa0, 0x0a6b5, 0x09b40, 0x14b60, 0x08af3, 0x0a560, 0x15348, 0x1d2a0, 0x0d540,
    0x15d46, 0x156a0, 0x096c0, 0x155c4, 0x14ae0, 0x0a4c0, 0x1e4c3, 0x1b2a0, 0x0b6a7, 0x0ad40,
    0x12da0, 0x09ba5, 0x095a0, 0x149a0, 0x1a9a4, 0x1a4a0, 0x1aaa8, 0x16a80, 0x16d40, 0x12b56,
    0x12b60, 0x09360, 0x152e4, 0x14960, 0x164ea, 0x0d4a0, 0x0da80, 0x15e86, 0x156c0, 0x12ae0,
    0x095e5, 0x092e0, 0x0c960, 0x0e943, 0x1d4a0, 0x0d6a8, 0x0b580, 0x156c0, 0x12da5, 0x125c0,
    0x192c0, 0x1b2a4, 0x1a940, 0x1b4a0, 0x0eaa2, 0x0ad40, 0x15767, 0x04ba0, 0x125a0, 0x19565,
    0x152a0, 0x16940, 0x17544, 0x15aa0, 0x0aba9, 0x09740, 0x14b60, 0x0a2f6, 0x0a560, 0x15260,
    0x0f2a4, 0x0d540, 0x15aa0, 0x0b6a2, 0x096c0, 0x14dc6, 0x149c0, 0x1a4c0, 0x1d4c5, 0x1aa60,
    0x0b540, 0x0ed43, 0x12da0, 0x095eb, 0x095a0, 0x149a0, 0x1a176, 0x1a4a0, 0x1aa40, 0x1ba85,
    0x16b40, 0x0ada0, 0x0ab62, 0x09360, 0x14ae7, 0x14960, 0x154a0, 0x164b5, 0x0da40, 0x15b40,
    0x096d3,
]

_MONTH_CN = ['', '正月', '二月', '三月', '四月', '五月', '六月',
             '七月', '八月', '九月', '十月', '冬月', '腊月']


def _lunar_day_cn(day):
    if day == 10:
        return '初十'
    if day == 20:
        return '二十'
    if day == 30:
        return '三十'
    prefix = ['初', '十', '廿']
    digit = ['一', '二', '三', '四', '五', '六', '七', '八', '九']
    return prefix[day // 10] + digit[(day % 10) - 1]


def _lunar_year_days(info):
    total = 0
    for i in range(12):
        total += 30 if info & (0x10000 >> i) else 29
    if info & 0xf:
        total += 30 if info & 0x10 else 29
    return total


def _compute_lunar_date(dt):
    from datetime import date as _date
    base = _date(1900, 1, 31)
    target = _date(dt.year, dt.month, dt.day)
    offset = (target - base).days

    if offset < 0 or offset > 60000:
        return ""

    year_idx = 0
    while year_idx < len(_LUNAR_INFO):
        days = _lunar_year_days(_LUNAR_INFO[year_idx])
        if offset < days:
            break
        offset -= days
        year_idx += 1

    if year_idx >= len(_LUNAR_INFO):
        return ""

    info = _LUNAR_INFO[year_idx]
    leap = info & 0xf

    month = 0
    is_leap = False
    for m in range(1, 13):
        days = 30 if info & (0x10000 >> (m - 1)) else 29
        if offset < days:
            month = m
            break
        offset -= days

        if m == leap:
            leap_days = 30 if info & 0x10 else 29
            if offset < leap_days:
                month = m
                is_leap = True
                break
            offset -= leap_days

    if month == 0:
        return ""

    day = offset + 1
    month_str = _MONTH_CN[month]
    if is_leap:
        month_str = '闰' + month_str

    return f"{month_str}{_lunar_day_cn(day)}"


def get_lunar_date_str():
    """Return today's lunar date. Tries cnlunar first, falls back to builtin."""
    try:
        import cnlunar
        lunar = cnlunar.Lunar(datetime.now())
        month = lunar.lunarMonthCn.replace("小", "").replace("大", "")
        return f"{month}{lunar.lunarDayCn}"
    except Exception:
        pass
    try:
        return _compute_lunar_date(datetime.now())
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# AI-specific validation
# ---------------------------------------------------------------------------

def validate_ai_news(title, content=""):
    text = (title + " " + (content or "")).lower()
    if not any(kw.lower() in text for kw in AI_MUST_HAVE):
        return False
    if any(kw in text for kw in AI_MUST_NOT_HAVE):
        return False
    return True


# ---------------------------------------------------------------------------
# HTML news extraction
# ---------------------------------------------------------------------------

def extract_news_from_html(html, source_url=""):
    if not html:
        return []

    items = []
    base_url = "/".join(source_url.split("/")[:3])
    seen = set()
    page_date = _parse_date(html[:5000])
    current_month = datetime.now().month

    matches = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>([^<]{10,120})</a>', html, re.IGNORECASE)
    # Also try links with nested tags (e.g. <a><span>title</span></a>)
    matches += re.findall(
        r'<a[^>]+href="([^"]+)"[^>]*>\s*(?:<[^>]+>)*([^<]{10,120})(?:</[^>]+>)*\s*</a>',
        html, re.IGNORECASE
    )

    for href, raw_title in matches:
        title = clean_html(raw_title).strip()

        if len(title) < 12 or len(title) > 100:
            continue

        cn_chars = sum(1 for c in title if '\u4e00' <= c <= '\u9fff')
        en_words = len(re.findall(r'[a-zA-Z]{3,}', title))
        if cn_chars < 4 and en_words < 3:
            continue

        skip_words = ["首页", "更多", "广告", "登录", "下载", "专题", "直播",
                      "导航", "列表", "关于我们", "联系我们", "许可证", "京 B2",
                      "Cookie", "Subscribe", "Sign in", "Log in",
                      "投资机构库", "创投家", "CLUB", "排行榜", "课程", "活动报名"]
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

        date = _parse_date(html[:3000])

        boilerplate = ["Google 新闻", "Google News", "为您汇集来自世界各地",
                       "百度首页", "网易首页", "新浪首页"]

        # og:description (most reliable)
        match = re.search(
            r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\']([^"\']+)["\']',
            html, re.IGNORECASE)
        if match:
            desc = clean_html(match.group(1))
            if len(desc) > 30 and not any(bp in desc for bp in boilerplate):
                return desc, date

        # meta description
        match = re.search(
            r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']',
            html, re.IGNORECASE)
        if match:
            desc = clean_html(match.group(1))
            if len(desc) > 30 and not any(bp in desc for bp in boilerplate):
                return desc, date

        # First substantial paragraph
        paragraphs = re.findall(r'<p[^>]*>([^<]{40,500})</p>', html)
        for p in paragraphs[:3]:
            text = clean_html(p)
            if len(text) > 30 and not any(bp in text for bp in boilerplate):
                return text, date

        return "", date
    except Exception:
        return "", None


# ---------------------------------------------------------------------------
# Summary generation
# ---------------------------------------------------------------------------

def generate_summary(title, content):
    """Generate 50-80 char summary. Data-first, subject-verb-object."""
    if not content:
        clean = re.sub(r'[（(].*[)）]$', '', title).strip()
        return clean[:80]

    content = clean_html(content)

    low_quality = ["首页>", "导航", "专题", "广告", "推荐", "登录", "注册", "下载 APP", "扫码",
                   "Cookie", "Subscribe", "newsletter"]
    if any(p.lower() in content.lower() for p in low_quality):
        return re.sub(r'[（(].*[)）]$', '', title).strip()[:80]

    if re.search(r'我们是|旗下|新媒体|专注于|致力于|版权所有|©|京ICP|备案号', content):
        return re.sub(r'[（(].*[)）]$', '', title).strip()[:80]

    sentences = re.split(r'[。！？.!?]', content)
    meaningful = []
    for s in sentences:
        s = s.strip()
        if len(s) < 15:
            continue
        if any(w in s for w in ["广告", "推荐", "首页", "导航", "扫码", "关注", "更多"]):
            continue
        meaningful.append(s)

    if not meaningful:
        return re.sub(r'[（(].*[)）]$', '', title).strip()[:80]

    lead = meaningful[0]
    lead = re.sub(r'[（(][^)）]*[)）]', '', lead).strip()
    lead = re.sub(r'^[,，:：\s]+', '', lead)

    data_point = ""
    for s in meaningful[1:4]:
        if re.search(r'\d+[.%亿元万]', s):
            data_point = re.sub(r'[（(][^)）]*[)）]', '', s).strip()
            break

    if data_point and len(lead) < 60:
        summary = lead + "。" + data_point
    else:
        summary = lead

    if len(summary) > 100:
        summary = summary[:97] + "..."

    summary = re.sub(r'^[^\u4e00-\u9fa5a-zA-Z]+[:：]', '', summary).strip()
    summary = re.sub(r'^[,，:：\s]+', '', summary)

    return summary[:100]


# ---------------------------------------------------------------------------
# Source fetching: unified HTML + RSS
# ---------------------------------------------------------------------------

def _enrich_item(item, category):
    """Fetch article content for a single HTML-sourced item."""
    if category == "军事":
        if not any(kw in item["title"] for kw in CATEGORY_KEYWORDS["军事"]):
            return None

    if item["url"]:
        content, article_date = fetch_article_content(item["url"])
        if content and re.search(r'我们是|旗下|新媒体|专注于', content):
            return None
        item["content"] = content
        if article_date:
            item["date"] = article_date

    return item


def _fetch_html_source(source_name, url, category):
    """Fetch and enrich items from an HTML news page."""
    html = fetch_with_retry(url)
    if not html:
        return []

    items = extract_news_from_html(html, url)
    for item in items:
        item["source"] = source_name

    candidates = items[:MAX_ITEMS * 2]

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


def _fetch_rss_source(source_name, url):
    """Fetch and parse an RSS/Atom feed."""
    xml_text = fetch_with_retry(url, timeout=FETCH_TIMEOUT)
    if not xml_text:
        return []
    return parse_rss_feed(xml_text, source_name)


def _fetch_source(source_name, url, category, source_type="html"):
    if source_type == "rss":
        return _fetch_rss_source(source_name, url)
    else:
        return _fetch_html_source(source_name, url, category)


# ---------------------------------------------------------------------------
# SearxNG supplement (all categories)
# ---------------------------------------------------------------------------

def _search_news(category, hours=168):
    """Search SearxNG for supplementary news in any category."""
    queries = SEARCH_QUERIES.get(category, [])
    if not queries:
        return []

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

            if len(title) < 10 or len(title) > 120:
                continue
            if any(s in url.lower() for s in SEARCH_SKIP_SITES):
                continue

            cn_chars = sum(1 for c in title if '\u4e00' <= c <= '\u9fff')
            en_words = len(re.findall(r'[a-zA-Z]{3,}', title))
            if cn_chars < 3 and en_words < 3:
                continue

            skip_patterns = ["教程", "指南", "免费使用", "下载", "APP", "推广", "怎么使用"]
            if any(p in title for p in skip_patterns):
                continue

            title_key = title[:30]
            if title_key in seen:
                continue
            seen.add(title_key)

            pub_date = _parse_date(content) if content else None

            items.append({
                "title": title,
                "url": url,
                "source": "搜索",
                "content": content or "",
                "date": pub_date or datetime.now(),
            })

    print(f"      搜索补充 {len(items)} 条 {category} 新闻")
    return items


# ---------------------------------------------------------------------------
# Category-level fetch + filter
# ---------------------------------------------------------------------------

def _fetch_category(category, sources):
    """Fetch, filter, and rank news for one category."""
    print(f"  抓取 {category} 新闻...")
    check_hours = TIME_WINDOWS.get(category, 48)

    # Parallel fetch from all sources
    all_items = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {}
        for src in sources:
            name, url = src[0], src[1]
            stype = src[2] if len(src) > 2 else "html"
            futures[pool.submit(_fetch_source, name, url, category, stype)] = name
        for future in as_completed(futures):
            name = futures[future]
            try:
                items = future.result()
                print(f"    → {name}: {len(items)} 条")
                all_items.extend(items)
            except Exception as e:
                print(f"    → {name}: 抓取失败 ({e})")

    # Date filter: keep items with no date (assume recent) or recent date
    result = [i for i in all_items if is_recent(i.get("date"), hours=check_hours)]

    # Category-specific validation
    if category == "AI":
        validated = [i for i in result if validate_ai_news(i["title"], i.get("content", ""))]
        if len(validated) < len(result):
            print(f"      AI 过滤：{len(result)} → {len(validated)} 条")
        result = validated
    elif category == "军事":
        validated = [i for i in result
                     if any(kw.lower() in (i["title"] + " " + i.get("content", "")).lower()
                            for kw in CATEGORY_KEYWORDS["军事"])]
        if len(validated) < len(result):
            print(f"      军事过滤：{len(result)} → {len(validated)} 条")
        result = validated

    # SearxNG supplement if too few items
    if len(result) < 3:
        print(f"      {category} 不足 ({len(result)} 条)，搜索补充...")
        search_items = _search_news(category, hours=168)
        existing_keys = {i["title"][:30] for i in result}
        for item in search_items:
            if len(result) >= MAX_ITEMS:
                break
            if category == "AI" and not validate_ai_news(item["title"], item.get("content", "")):
                continue
            if item["title"][:30] not in existing_keys:
                result.append(item)
                existing_keys.add(item["title"][:30])

    # Deduplicate by title prefix AND URL
    seen_titles = set()
    seen_urls = set()
    unique = []
    for item in result:
        title_key = item["title"][:30]
        url_key = item.get("url", "").split("?")[0]
        if title_key in seen_titles or (url_key and url_key in seen_urls):
            continue
        seen_titles.add(title_key)
        if url_key:
            seen_urls.add(url_key)
        unique.append(item)

    # Rank by importance (geopolitical/economic significance), not content availability
    unique.sort(key=lambda x: _importance_score(x), reverse=True)

    # Enrich top candidates that lack content (skip Google News redirects)
    candidates = unique[:MAX_ITEMS + 3]
    to_enrich = [i for i in candidates
                 if not i.get("content")
                 and i.get("url")
                 and "news.google.com" not in i.get("url", "")]
    if to_enrich:
        print(f"      补充 {len(to_enrich)} 条文章摘要...")
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            def _fetch_content(item):
                content, date = fetch_article_content(item["url"])
                if content:
                    item["content"] = content
                if date and not item.get("date"):
                    item["date"] = date
                return item
            futures = [pool.submit(_fetch_content, i) for i in to_enrich]
            for f in as_completed(futures):
                try:
                    f.result()
                except Exception:
                    pass

    # Translate ALL non-Chinese titles and content instead of filtering them out
    to_translate = [i for i in unique if _needs_translation(i.get("title", ""))]
    if to_translate:
        print(f"      翻译 {len(to_translate)} 条非中文新闻...")
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            def _translate_item(item):
                item["title"] = _translate_to_chinese(item["title"])
                if item.get("content"):
                    item["content"] = _translate_to_chinese(item["content"])
                return item
            futures = [pool.submit(_translate_item, i) for i in to_translate]
            for f in as_completed(futures):
                try:
                    f.result()
                except Exception:
                    pass

    # Re-rank after enrichment and translation (translated keywords now match)
    unique.sort(key=lambda x: _importance_score(x), reverse=True)

    # Source diversity: cap per source to prevent one feed from dominating
    max_per_source = min(3, MAX_ITEMS - 1)
    diverse = []
    source_counts = {}
    for item in unique:
        src = item.get("source", "未知")
        count = source_counts.get(src, 0)
        if count < max_per_source:
            diverse.append(item)
            source_counts[src] = count + 1
    unique = diverse

    # Generate summaries
    for item in unique:
        item["summary"] = generate_summary(item["title"], item.get("content", ""))

    count = len(unique[:MAX_ITEMS])
    print(f"      最终 {count} 条 {category} ({check_hours}h)")
    return category, unique[:MAX_ITEMS]


# ---------------------------------------------------------------------------
# Markdown output
# ---------------------------------------------------------------------------

def fetch_all_news():
    print(f"[{datetime.now()}] 开始抓取新闻...")
    print()

    news_data = {}
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

        if not items:
            md.append("_暂无最新新闻_")
            md.append("")
            continue

        for i, item in enumerate(items, 1):
            title = item.get("title", "")
            summary = item.get("summary", "")
            source = item.get("source", "")

            md.append(f"### {i}. {title}")
            md.append("")
            if source:
                md.append(f"**来源**：{source}")
                md.append("")
            # Show summary if it adds info beyond the title
            if summary and summary != title and not summary.startswith(title[:20]):
                md.append(f"**摘要**：{summary}")
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
        f"_来源：中外权威媒体 + RSS 订阅 + 搜索引擎 | {check_hours_desc()} | 精炼摘要_"
    )
    md.append("")
    with _stats_lock:
        md.append(
            f"_网络统计：成功 {_stats['success']} | 重试 {_stats['retried']} | 失败 {_stats['failed']}_"
        )

    return "\n".join(md)


def check_hours_desc():
    windows = set(TIME_WINDOWS.values())
    if len(windows) == 1:
        return f"{windows.pop()}h 时效"
    return f"{min(windows)}-{max(windows)}h 时效"


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
