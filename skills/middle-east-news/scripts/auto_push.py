#!/usr/bin/env python3
# DEPRECATED — 请使用 push.py 代替。本文件保留仅供参考。
"""
[DEPRECATED] 每日新闻自动推送脚本
→ 替代方案：python3 push.py

本脚本只输出推送指令文本，不实际执行飞书操作。
"""

import os
import sys
import subprocess
from datetime import datetime

# 添加 OpenClaw 路径
sys.path.insert(0, '/opt/openclaw')

def run_command(cmd, cwd=None):
    """运行 shell 命令"""
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr

def main():
    print("=" * 50)
    print(f"📰 每日新闻自动推送 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 1. 生成新闻简报
    print("\n📝 步骤 1/3: 生成新闻简报...")
    returncode, stdout, stderr = run_command("python3 generate_news.py", cwd=script_dir)
    
    if returncode != 0:
        print(f"❌ 新闻生成失败：{stderr}")
        return 1
    
    print(f"✅ 新闻生成完成")
    print(stdout.strip())
    
    # 2. 读取新闻内容
    print("\n📄 步骤 2/3: 读取新闻内容...")
    news_file = "/tmp/news_brief.md"
    
    if not os.path.exists(news_file):
        print(f"❌ 新闻文件不存在：{news_file}")
        return 1
    
    with open(news_file, 'r', encoding='utf-8') as f:
        news_content = f.read()
    
    print(f"✅ 读取成功，共 {len(news_content)} 字符")
    
    # 3. 提取日期用于标题
    today = datetime.now().strftime("%Y 年 %m 月 %d 日")
    doc_title = f"📰 全球要闻简报 - {today}"
    
    # 4. 输出推送指令（由 OpenClaw 执行）
    print("\n📤 步骤 3/3: 准备推送...")
    print("\n" + "=" * 50)
    print("推送指令（由 OpenClaw 执行）：")
    print("=" * 50)
    print(f"""
# 创建飞书文档
feishu_doc create(title="{doc_title}")

# 写入内容
feishu_doc write(doc_token=<从上一步获取>, content=<新闻内容>)

# 发送链接给用户
message send(message="📰 今日新闻简报已生成\\n\\n链接：https://feishu.cn/docx/<doc_token>")
""")
    print("=" * 50)
    
    # 5. 记录日志
    log_file = os.path.join(os.path.dirname(script_dir), "memory", "news_push.log")
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - 新闻推送完成\n")
    
    print("\n✅ 推送准备完成")
    print("=" * 50)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
