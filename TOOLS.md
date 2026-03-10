# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

## ⚠️ 飞书文档操作注意事项

**血泪教训（2026-03-08）：**

`feishu_doc create` 的 `content` 参数**不会实际写入内容**！只创建标题，文档是空的。

**正确流程：**
1. `create` 创建文档（只设标题）
2. `write` 或 `append` 写入内容
3. **验证**：`read` 确认内容已写入
4. 发送链接给用户

**错误示范（不要这样做）：**
```
create(title="xxx", content="...") → 直接发送链接 ❌
```

**正确示范：**
```
create(title="xxx") → write(doc_token, content="...") → read 验证 → 发送链接 ✅
```

---

Add whatever helps you do your job. This is your cheat sheet.
