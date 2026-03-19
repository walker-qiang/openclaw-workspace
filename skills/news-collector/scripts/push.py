#!/usr/bin/env python3
"""
统一新闻推送入口
流程：generate_news.py 生成 -> 飞书文档 create -> write -> read 验证 -> 发送链接

用法：
  python3 push.py                    # 生成新闻 + 推送飞书文档
  python3 push.py --skip-generate    # 跳过生成，直接推送已有的新闻文件
  python3 push.py --dry-run          # 只生成，不推送
"""

import os
import sys
import re
import time
import subprocess
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE = os.environ.get("OPENCLAW_WORKSPACE", os.path.join(os.path.expanduser("~"), ".openclaw", "workspace"))
OPENCLAW_BIN = os.environ.get("OPENCLAW_BIN", "openclaw")
FEISHU_USER_ID = os.environ.get("FEISHU_USER_ID", "")
NEWS_FILE = os.environ.get("NEWS_OUTPUT", "/tmp/news_brief.md")
LOG_FILE = os.path.join(WORKSPACE, "memory", "news_push.log")

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
    """Run a shell command and return (returncode, stdout, stderr)."""
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
    """Run a shell command with automatic retry on failure."""
    retries = retries if retries is not None else RETRY_ATTEMPTS
    for attempt in range(1 + retries):
        code, stdout, stderr = run_cmd(cmd, timeout)
        if code == 0:
            return code, stdout, stderr
        if attempt < retries:
            log(f"  Retry {attempt + 1}/{retries} after failure: {stderr[:100]}")
            time.sleep(RETRY_DELAY)
    return code, stdout, stderr


def generate_news():
    """Run generate_news.py to produce the news file."""
    log("Step 1: Generating news...")
    code, stdout, stderr = run_cmd(
        [sys.executable, os.path.join(SCRIPT_DIR, "generate_news.py")],
        timeout=300,
    )
    if code != 0:
        log(f"ERROR: generate_news.py failed (exit {code}): {stderr[:500]}")
        return False
    if not os.path.exists(NEWS_FILE):
        log(f"ERROR: {NEWS_FILE} not created after generate_news.py")
        return False
    size = os.path.getsize(NEWS_FILE)
    log(f"News generated: {size} bytes")
    return True


def read_news_content():
    """Read the generated news markdown."""
    with open(NEWS_FILE, "r", encoding="utf-8") as f:
        return f.read()


def feishu_create_doc(title):
    """Create a Feishu doc (title only) and return doc_token. Retries on failure."""
    log(f"Step 2: Creating Feishu doc: {title}")
    code, stdout, stderr = run_cmd_with_retry(
        [OPENCLAW_BIN, "feishu_doc", "create", "--title", title]
    )
    if code != 0:
        log(f"ERROR: feishu_doc create failed (exit {code}): {stderr[:500]}")
        return None

    token_match = re.search(r'"?doc_token"?\s*[:=]\s*"?([A-Za-z0-9_-]+)"?', stdout)
    if token_match:
        token = token_match.group(1)
        log(f"Doc created, token: {token}")
        return token

    token_match = re.search(r'([A-Za-z0-9_-]{20,})', stdout)
    if token_match:
        token = token_match.group(1)
        log(f"Doc created (parsed token): {token}")
        return token

    log(f"ERROR: Could not parse doc_token from output: {stdout[:300]}")
    return None


def feishu_write_doc(doc_token, content):
    """Write content to an existing Feishu doc. Retries on failure."""
    log(f"Step 3: Writing content to doc {doc_token} ({len(content)} chars)")
    content_file = "/tmp/news_feishu_content.md"
    with open(content_file, "w", encoding="utf-8") as f:
        f.write(content)

    code, stdout, stderr = run_cmd_with_retry(
        [OPENCLAW_BIN, "feishu_doc", "write", "--doc_token", doc_token,
         "--content-file", content_file]
    )
    if code != 0:
        log(f"Write with --content-file failed, trying --content flag...")
        code, stdout, stderr = run_cmd_with_retry(
            [OPENCLAW_BIN, "feishu_doc", "write", "--doc_token", doc_token,
             "--content", content[:30000]]
        )
    if code != 0:
        log(f"ERROR: feishu_doc write failed (exit {code}): {stderr[:500]}")
        return False
    log("Content written successfully")
    return True


def feishu_verify_doc(doc_token):
    """Read back the doc and verify content was written (block_count > 1)."""
    log(f"Step 4: Verifying doc {doc_token}")
    code, stdout, stderr = run_cmd(
        [OPENCLAW_BIN, "feishu_doc", "read", "--doc_token", doc_token]
    )
    if code != 0:
        log(f"WARNING: feishu_doc read failed (exit {code}): {stderr[:300]}")
        return False

    block_match = re.search(r'block_count["\s:=]+(\d+)', stdout)
    if block_match:
        count = int(block_match.group(1))
        if count > 1:
            log(f"Verified: {count} blocks in document")
            return True
        else:
            log(f"WARNING: Only {count} block(s) — content may not have been written")
            return False

    if len(stdout.strip()) > 100:
        log("Verified: doc has content (no block_count field, but output is non-empty)")
        return True

    log("WARNING: Could not verify doc content")
    return False


def send_doc_link(doc_token, verified=True):
    """Send the document link via Feishu message."""
    doc_url = f"https://feishu.cn/docx/{doc_token}"
    ts = datetime.now().strftime("%m-%d %H:%M")

    warning = "" if verified else "\n⚠️ 注意：文档内容验证未通过，请手动检查文档是否完整"

    msg = (
        f"📰 全球要闻简报已更新 ({ts})\n\n"
        f"📄 查看详情：{doc_url}\n\n"
        f"内容包括：政治、经济、军事、科技、AI 五大领域{warning}"
    )

    log(f"Step 5: Sending link: {doc_url}")

    if FEISHU_USER_ID:
        code, stdout, stderr = run_cmd_with_retry(
            [OPENCLAW_BIN, "message", "send",
             "--channel", "feishu",
             "--target", f"user:{FEISHU_USER_ID}",
             "--message", msg]
        )
        if code == 0:
            log("Message sent via direct target")
            return True
        log(f"Direct send failed, falling back to sessions_send: {stderr[:200]}")

    code, stdout, stderr = run_cmd_with_retry(
        [OPENCLAW_BIN, "sessions", "send", "--label", "main", "--message", msg]
    )
    if code == 0:
        log("Message sent via sessions_send")
        return True

    log(f"ERROR: All send methods failed. Last error: {stderr[:300]}")
    log(f"Manual link: {doc_url}")
    return False


def main():
    args = sys.argv[1:]
    skip_generate = "--skip-generate" in args
    dry_run = "--dry-run" in args

    log("=" * 50)
    log("📰 News Push Start")
    log(f"  workspace: {WORKSPACE}")
    log(f"  openclaw:  {OPENCLAW_BIN}")
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

    doc_token = feishu_create_doc(doc_title)
    if not doc_token:
        return 1

    if not feishu_write_doc(doc_token, content):
        return 1

    verified = feishu_verify_doc(doc_token)
    send_doc_link(doc_token, verified=verified)

    log("DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
