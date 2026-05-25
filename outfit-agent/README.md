# 穿搭助手 — Mango 每日穿搭顾问

> 每天早上根据场合 + 天气 + 你的风格，给出穿搭建议并生成效果图。

---

## 功能

1. **问场合** — 今天去什么场合？见什么人？
2. **查天气** — 自动查询当地今日天气
3. **AI 穿搭建议** — 结合你的个人风格档案，用 AI 给出个性化搭配
4. **生成图片** — 调用 Stability AI 生成穿搭效果图
5. **存档** — 保存到 `output/` 目录的 Markdown 文档
6. **微信推送** — 通过 PushPlus 推送到微信

---

## 快速开始

### 1. 填写个人风格档案

编辑 `aboutme.md`，如实填写你的体型、肤色、风格偏好等信息。
（不填也能跑，但建议填写以获得更个性化的建议）

### 2. 配置 API Key

复制 `.env.example` 为 `.env`，填入你的 Key：

```ini
DEEPSEEK_API_KEY=sk-xxx       # DeepSeek API Key（已有）
STABILITY_API_KEY=sk-xxx      # Stability AI Key（需注册）
PUSHPLUS_TOKEN=xxx            # PushPlus 微信推送 Token（已有）
CITY=广州                     # 所在城市
```

- **DeepSeek** — 已有，用你 Claude 的那个 Key
- **Stability AI** — 去 [platform.stability.ai](https://platform.stability.ai) 注册免费拿 Credits
- **PushPlus** — 体育新闻已经在用的 Token

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 运行

```bash
python main.py
```

或双击 `run.bat`（Windows）。

---

## 项目结构

```
outfit-agent/
├── main.py            # 主入口（交互式问答）
├── advisor.py         # 调用 DeepSeek API 生成穿搭建议
├── weather.py         # 查询天气（wttr.in 免费接口）
├── image_gen.py       # Stability AI 生成穿搭图片
├── pusher.py          # PushPlus 微信推送
├── config.py          # 配置加载
├── aboutme.md         # ← 你的个人风格档案
├── .env               # API Keys（不上传 git）
├── requirements.txt   # Python 依赖
├── run.bat            # 一键运行
└── output/            # 生成的穿搭文档
    └── 2026-05-21-今日穿搭.md
```

---

## 流程说明

```
启动 → 输入场合 → 输入见谁 → 查天气
  → AI 分析穿搭建议
  → Stability AI 生图
  → 保存 md 文档
  → 推送微信
```

---

## 后续扩展

| 阶段 | 功能 |
|------|------|
| V1.0 | 当前：交互式问答 + AI 建议 + 生图 + 推送 |
| V1.1 | 接入即梦/其他生图引擎 |
| V1.2 | 定时提醒（每天早上自动问你今天安排） |
| V2.0 | Web 界面 / 小程序 |
