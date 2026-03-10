# HEARTBEAT.md - 定时任务配置

# 每分钟检查新闻推送触发文件
检查 /.trigger_news_push 文件，如果存在则执行新闻推送：
1. 读取文件确认是新闻推送请求
2. 执行 /home/admin/.openclaw/workspace/skills/middle-east-news/scripts/generate_news.py 生成新闻
3. 创建飞书文档并写入内容
4. 发送文档链接给用户
5. 删除触发文件
