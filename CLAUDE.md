# first-cc 项目 — Claude 备忘录

## 项目结构

### 1. sports-agent/
体育新闻简报生成器 — 每天早上采集 NBA/CBA/英超/中超 新闻，生成 Markdown 简报并推送微信。
- `python main.py --push` 运行并推送
- 使用 PushPlus 推微信

### 2. outfit-agent/
穿搭助手 — 问场合 → 查天气 → AI 穿搭建议 → Stability AI 生图 → 存档 md → 推微信
- `python main.py` 交互式运行
- 需要先填 aboutme.md（个人风格档案）
- 需要 Stability AI API Key（生图）

## 穿搭助手概念
会主动询问我今天要去什么场合、会见什么人，然后查今天当地天气，根据 aboutme 的风格和行程给出穿搭建议，生成穿搭图片，推送微信，并保存到当天日期文档。
