# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

个人自动化项目，包含两个独立 Agent 和一个未来架构方案：

1. **sports-agent/** — 体育新闻简报生成器，每天早上抓取过去 24 小时体育新闻生成 Markdown 简报并推送微信
2. **outfit-agent/** — 穿搭助手，根据场合 + 天气 + 个人风格生成穿搭建议，AI 生图并推送微信
3. **sports-news-architecture/architecture.md** — 未来 Web 版体育新闻站的技术架构方案

## 常用命令

### sports-agent

```bash
# 安装依赖
cd sports-agent && pip install -r requirements.txt

# 生成今日简报
python main.py

# 生成并推送到微信
python main.py --push

# 仅推送已有简报（不重新生成）
python main.py --push-only

# 指定日期生成
python main.py --date 2026-05-13

# 强制覆盖已有文件
python main.py --force

# Windows 下可直接双击 run.bat，或 run.bat push
```

### outfit-agent

```bash
# 安装依赖
cd outfit-agent && pip install -r requirements.txt

# 交互式运行
python main.py

# 自动模式（工作日=上班，周末=日常）
python main.py --auto

# Windows 下可直接双击 run.bat
```

## 项目结构

```
first-cc/
├── sports-agent/           # 体育新闻简报生成器
│   ├── main.py             # 主入口：argparse 解析，编排 5 步流程
│   ├── collector.py        # RSS 抓取 + 懂球帝 API + 去重 + 关键词分类
│   ├── config.py           # 数据源 URL、分类关键词、比分 API、推送 Token
│   ├── generator.py        # Markdown 简报生成 + 推送短版 + 比赛结果提取
│   ├── translator.py       # 英文→中文翻译（translators 库，缓存到 .trans_cache/）
│   ├── article_reader.py   # 全文抓取（trafilatura），补充 RSS 摘要不足
│   ├── scores.py           # ESPN 公开 Scoreboard API 采集比分 + 球员数据
│   ├── pusher.py           # PushPlus / Server酱 微信推送
│   ├── run.bat             # Windows 一键运行脚本
│   ├── scheduler_setup.ps1 # Windows 计划任务注册脚本
│   ├── .env.example        # 环境变量模板
│   ├── requirements.txt    # 依赖：feedparser, requests, trafilatura, lxml, translators
│   └── output/             # 生成的简报（git 跟踪）
│
├── outfit-agent/           # 穿搭助手
│   ├── main.py             # 主入口：交互式/自动模式，编排 7 步流程
│   ├── advisor.py          # 调用 DeepSeek API 生成穿搭建议（JSON 输出）
│   ├── weather.py          # wttr.in 免费天气 API
│   ├── image_gen.py        # Pollinations.ai 免费生图（flux-realism 模型）
│   ├── uploader.py         # ImgURL 图床上传
│   ├── pusher.py           # PushPlus 微信推送
│   ├── config.py           # API Key、城市、路径配置（dotenv 加载）
│   ├── aboutme.md          # 用户个人风格档案
│   ├── run.bat             # Windows 一键运行脚本
│   ├── .env.example        # 环境变量模板
│   ├── requirements.txt    # 依赖：requests, python-dotenv, Pillow
│   └── output/             # 生成的穿搭文档（git 跟踪）
│
├── sports-news-architecture/
│   └── architecture.md     # Next.js + PostgreSQL + Redis 体育新闻站架构方案
│
└── .github/workflows/      # GitHub Actions 定时任务
    ├── daily-briefing.yml  # 每天 UTC 02:17（北京时间 10:17）生成体育简报
    └── daily-outfit.yml    # 每天 UTC 23:57（北京时间 07:57）生成穿搭建议
```

## 架构要点

### sports-agent 数据处理流水线

```
RSS/API 抓取 → 去重 → 24h 过滤 → 清洗（过滤视频/劣质翻译）
  → 关键词分类（NBA/CBA/英超/中超/伤病/转会/其他）
  → 翻译（英文→中文，缓存到 .trans_cache/）
  → 全文补充（针对摘要不清晰的条目用 trafilatura 抓取原文）
  → 比分采集（ESPN 公开 API，含球员亮点数据）
  → 生成简报（完整 Markdown + 推送短版）
  → 质量 Review（检查标题过短、医疗类上下文、列表类）
  → 微信推送（PushPlus）
```

- 分类逻辑在 `collector.py::classify()` — 中文用子串匹配，英文用 `\b` 词边界
- 配置驱动：所有源、关键词、时间窗口在 `config.py` 集中管理
- 译文质量检查：`_is_gibberish_translation()` 检测逐词硬译（如连续出现"X的Y的"）
- 推送内容按联赛分类，每类最多 3 条，自动截断到 4000 字符

### outfit-agent 处理流程

```
输入场合/见谁 → 查天气（wttr.in）→ DeepSeek AI 分析
  → 生成穿搭建议（结构化 JSON）
  → Pollinations.ai 生图（flux-realism 模型，中景半身）
  → 上传 ImgURL 图床
  → 保存 Markdown 文档
  → 推送微信
```

- `advisor.py` 调用 DeepSeek API 返回固定 JSON 结构：analysis / outfit (tops/bottoms/shoes/accessories) / summary / image_prompt
- API 不可用时自动降级到 `_fallback_advice()` 本地兜底
- 自动模式 `--auto` 根据星期几（工作日/周末）推断场合

### 定时自动化

- GitHub Actions 每日自动运行两个 Agent，产出存档到 git 仓库
- sports-agent 也可通过 `scheduler_setup.ps1` 注册 Windows 计划任务
- 推送依赖 PushPlus Token，通过 GitHub Secrets 注入

### 环境变量配置

两个 Agent 都通过 `.env` 文件加载配置（`python-dotenv`）：
- `sports-agent/.env` 主要需要 `PUSHPLUS_TOKEN`
- `outfit-agent/.env` 需要 `DEEPSEEK_API_KEY`, `STABILITY_API_KEY`（已弃用）, `PUSHPLUS_TOKEN`, `IMGURL_UID`, `IMGURL_TOKEN`, `CITY`

注意：outfit-agent 的 `image_gen.py` 实际使用的是 Pollinations.ai（免费），已不再需要 Stability AI Key。`config.py` 中仍保留 `STABILITY_API_KEY` 配置但未使用。

## CI/CD

GitHub Actions 工作流在 `.github/workflows/` 下：
- `daily-briefing.yml` — Python 3.12，生成简报后 `git commit` 存档 output/
- `daily-outfit.yml` — Python 3.12，自动模式运行，存档 output/
- 两个 workflow 都包含 `workflow_dispatch` 支持手动触发
