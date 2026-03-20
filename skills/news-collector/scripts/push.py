#!/usr/bin/env python3
"""
统一新闻推送入口
流程：generate_news.py 生成 → 飞书 API 创建文档 → 写入内容 → 发送链接

用法：
  python3 push.py                    # 生成新闻 + 推送飞书文档
  python3 push.py --skip-generate    # 跳过生成，直接推送已有的新闻文件
  python3 push.py --dry-run          # 只生成，不推送
"""

import os
import sys
import re
import json
import time
import subprocess
import urllib.request
import urllib.parse
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE = os.environ.get("OPENCLAW_WORKSPACE", os.path.join(os.path.expanduser("~"), ".openclaw", "workspace"))
OPENCLAW_BIN = os.environ.get("OPENCLAW_BIN", "openclaw")
FEISHU_USER_ID = os.environ.get("FEISHU_USER_ID", "")
NEWS_FILE = os.environ.get("NEWS_OUTPUT", "/tmp/news_brief.md")
LOG_FILE = os.path.join(WORKSPACE, "memory", "news_push.log")

OPENCLAW_CONFIG = os.path.join(os.path.expanduser("~"), ".openclaw", "openclaw.json")
FEISHU_API_BASE = "https://open.feishu.cn/open-apis"

RETRY_ATTEMPTS = 2
RETRY_DELAY = 2


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts} - {msg}"
    print(line)
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def run_cmd(cmd, timeout=60):
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, cwd=WORKSPACE
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except FileNotFoundError:
        return -1, "", f"Command not found: {cmd[0]}"


def run_cmd_with_retry(cmd, timeout=60, retries=None):
    retries = retries if retries is not None else RETRY_ATTEMPTS
    for attempt in range(1 + retries):
        code, stdout, stderr = run_cmd(cmd, timeout)
        if code == 0:
            return code, stdout, stderr
        if attempt < retries:
            log(f"  Retry {attempt + 1}/{retries}: {stderr[:100]}")
            time.sleep(RETRY_DELAY)
    return code, stdout, stderr


# ---------------------------------------------------------------------------
# Feishu API (direct HTTP, no CLI dependency)
# ---------------------------------------------------------------------------

class FeishuAPI:
    """Direct Feishu/Lark API client using tenant access token."""

    def __init__(self):
        self._token = None
        self._token_expires = 0
        self._app_id = None
        self._app_secret = None
        self._load_credentials()

    def _load_credentials(self):
        try:
            with open(OPENCLAW_CONFIG, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            feishu = cfg.get("channels", {}).get("feishu", {})
            self._app_id = feishu.get("appId")
            self._app_secret = feishu.get("appSecret")
            if not self._app_id or not self._app_secret:
                raise ValueError("Missing appId or appSecret")
        except Exception as e:
            log(f"ERROR: Failed to load Feishu credentials: {e}")
            raise

    def _ensure_token(self):
        if self._token and time.time() < self._token_expires:
            return
        data = json.dumps({
            "app_id": self._app_id,
            "app_secret": self._app_secret,
        }).encode()
        req = urllib.request.Request(
            f"{FEISHU_API_BASE}/auth/v3/tenant_access_token/internal",
            data=data,
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode())
        if result.get("code") != 0:
            raise RuntimeError(f"Token error: {result}")
        self._token = result["tenant_access_token"]
        self._token_expires = time.time() + result.get("expire", 7000) - 60

    def _api_call(self, method, path, body=None):
        self._ensure_token()
        url = f"{FEISHU_API_BASE}{path}"
        encoded = json.dumps(body).encode() if body else None
        req = urllib.request.Request(url, data=encoded, method=method, headers={
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Bearer {self._token}",
        })
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"HTTP {e.code}: {error_body[:300]}")

    def create_document(self, title):
        result = self._api_call("POST", "/docx/v1/documents", {"title": title, "folder_token": ""})
        if result.get("code") != 0:
            raise RuntimeError(f"Create doc failed: {result}")
        doc = result["data"]["document"]
        return doc["document_id"]

    def write_blocks(self, doc_id, blocks):
        result = self._api_call(
            "POST",
            f"/docx/v1/documents/{doc_id}/blocks/{doc_id}/children",
            {"children": blocks, "index": 0},
        )
        if result.get("code") != 0:
            raise RuntimeError(f"Write blocks failed: code={result.get('code')} msg={result.get('msg')}")
        return True

    def get_block_count(self, doc_id):
        result = self._api_call("GET", f"/docx/v1/documents/{doc_id}/blocks/{doc_id}/children?document_revision_id=-1", None)
        if result.get("code") != 0:
            return 0
        return len(result.get("data", {}).get("items", []))


# ---------------------------------------------------------------------------
# Markdown → Feishu DocX blocks converter
# ---------------------------------------------------------------------------

def _parse_inline(text):
    """Parse inline markdown (bold, italic, links) into Feishu text elements."""
    elements = []
    pos = 0

    pattern = re.compile(
        r'\[([^\]]+)\]\(([^)]+)\)'    # [text](url)
        r'|\*\*(.+?)\*\*'             # **bold**
        r'|_(.+?)_'                    # _italic_
    )

    for m in pattern.finditer(text):
        if m.start() > pos:
            elements.append({"text_run": {"content": text[pos:m.start()]}})

        if m.group(1) is not None:
            encoded_url = urllib.parse.quote(m.group(2), safe=':/?&=#%')
            elements.append({"text_run": {
                "content": m.group(1),
                "text_element_style": {"link": {"url": encoded_url}},
            }})
        elif m.group(3) is not None:
            elements.append({"text_run": {
                "content": m.group(3),
                "text_element_style": {"bold": True},
            }})
        elif m.group(4) is not None:
            elements.append({"text_run": {
                "content": m.group(4),
                "text_element_style": {"italic": True},
            }})
        pos = m.end()

    if pos < len(text):
        elements.append({"text_run": {"content": text[pos:]}})

    if not elements:
        elements.append({"text_run": {"content": text or " "}})

    return elements


def markdown_to_blocks(md_text):
    """Convert markdown text to Feishu DocX block format."""
    blocks = []
    lines = md_text.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i].rstrip()
        i += 1

        if not line:
            continue

        if line.startswith("# "):
            blocks.append({
                "block_type": 3,
                "heading1": {"elements": _parse_inline(line[2:]), "style": {}},
            })
        elif line.startswith("## "):
            blocks.append({
                "block_type": 4,
                "heading2": {"elements": _parse_inline(line[3:]), "style": {}},
            })
        elif line.startswith("### "):
            blocks.append({
                "block_type": 5,
                "heading3": {"elements": _parse_inline(line[4:]), "style": {}},
            })
        elif line.strip() == "---":
            blocks.append({"block_type": 22, "divider": {}})
        elif line.startswith("> "):
            blocks.append({
                "block_type": 2,
                "text": {"elements": _parse_inline("💬 " + line[2:]), "style": {}},
            })
        else:
            blocks.append({
                "block_type": 2,
                "text": {"elements": _parse_inline(line), "style": {}},
            })

    return blocks


# ---------------------------------------------------------------------------
# Push flow
# ---------------------------------------------------------------------------

def generate_news():
    log("Step 1: Generating news...")
    code, stdout, stderr = run_cmd(
        [sys.executable, os.path.join(SCRIPT_DIR, "generate_news.py")],
        timeout=300,
    )
    if code != 0:
        log(f"ERROR: generate_news.py failed (exit {code}): {stderr[:500]}")
        return False
    if not os.path.exists(NEWS_FILE):
        log(f"ERROR: {NEWS_FILE} not created")
        return False
    size = os.path.getsize(NEWS_FILE)
    log(f"News generated: {size} bytes")
    return True


def read_news_content():
    with open(NEWS_FILE, "r", encoding="utf-8") as f:
        return f.read()


def push_to_feishu(title, content):
    """Create Feishu doc, write content blocks, verify, return doc URL."""
    api = FeishuAPI()

    log(f"Step 2: Creating Feishu doc: {title}")
    doc_id = api.create_document(title)
    log(f"Doc created: {doc_id}")

    log(f"Step 3: Converting markdown to blocks...")
    blocks = markdown_to_blocks(content)
    log(f"Converted {len(blocks)} blocks")

    # Write in batches (API limit: ~50 blocks per request)
    batch_size = 40
    for batch_start in range(0, len(blocks), batch_size):
        batch = blocks[batch_start:batch_start + batch_size]
        log(f"  Writing blocks {batch_start + 1}-{batch_start + len(batch)}...")
        try:
            api.write_blocks(doc_id, batch)
        except RuntimeError as e:
            log(f"  WARNING: Block write error: {e}")
            log(f"  Retrying with individual blocks...")
            for j, block in enumerate(batch):
                try:
                    api.write_blocks(doc_id, [block])
                except Exception as e2:
                    log(f"  Skip block {batch_start + j}: {e2}")

    log(f"Step 4: Verifying doc...")
    count = api.get_block_count(doc_id)
    verified = count > 1
    if verified:
        log(f"Verified: {count} blocks")
    else:
        log(f"WARNING: Only {count} block(s)")

    doc_url = f"https://feishu.cn/docx/{doc_id}"
    return doc_url, verified


def _detect_feishu_user_id():
    """Auto-detect Feishu user open_id from openclaw sessions."""
    if FEISHU_USER_ID:
        return FEISHU_USER_ID
    try:
        code, stdout, _ = run_cmd([OPENCLAW_BIN, "sessions", "--json"], timeout=10)
        if code == 0:
            data = json.loads(stdout)
            sessions = data if isinstance(data, list) else data.get("sessions", [])
            for s in sessions:
                key = s.get("key", "")
                m = re.search(r'feishu:direct:(ou_[a-f0-9]+)', key)
                if m:
                    return m.group(1)
    except Exception:
        pass
    return None


def send_doc_link(doc_url, verified=True):
    ts = datetime.now().strftime("%m-%d %H:%M")
    warning = "" if verified else "\n⚠️ 注意：文档内容可能不完整，请手动检查"
    msg = (
        f"📰 全球要闻简报已更新 ({ts})\n\n"
        f"📄 查看详情：{doc_url}\n\n"
        f"内容包括：政治、经济、军事、科技、AI 五大领域{warning}"
    )

    log(f"Step 5: Sending link: {doc_url}")

    user_id = _detect_feishu_user_id()
    if user_id:
        target = f"user:{user_id}" if not user_id.startswith("user:") else user_id
        code, stdout, stderr = run_cmd_with_retry(
            [OPENCLAW_BIN, "message", "send",
             "--channel", "feishu",
             "--target", target,
             "--message", msg]
        )
        if code == 0:
            log(f"Message sent to {user_id}")
            return True
        log(f"Send failed: {stderr[:200]}")

    log(f"ERROR: Could not send message. Manual link: {doc_url}")
    return False


def main():
    args = sys.argv[1:]
    skip_generate = "--skip-generate" in args
    dry_run = "--dry-run" in args

    log("=" * 50)
    log("📰 News Push Start")
    log(f"  workspace: {WORKSPACE}")
    log(f"  dry_run:   {dry_run}")
    log("=" * 50)

    if not skip_generate:
        if not generate_news():
            return 1
    else:
        if not os.path.exists(NEWS_FILE):
            log(f"ERROR: --skip-generate but {NEWS_FILE} does not exist")
            return 1
        log(f"Skipping generation, using existing {NEWS_FILE}")

    content = read_news_content()
    log(f"News content: {len(content)} chars")

    if dry_run:
        log("Dry run — skipping Feishu push")
        log("DONE")
        return 0

    today = datetime.now().strftime("%Y 年 %m 月 %d 日")
    doc_title = f"📰 全球要闻简报 - {today}"

    try:
        doc_url, verified = push_to_feishu(doc_title, content)
    except Exception as e:
        log(f"ERROR: Feishu push failed: {e}")
        return 1

    send_doc_link(doc_url, verified=verified)

    log("DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
