# Mango 体育新闻简报生成器

> 最小可用版本 (MVP) —— 每天早上自动抓取过去24小时体育新闻，生成 Markdown 简报。

---

## 项目结构

```
sports-agent/
├── main.py           # 主入口：采集 -> 分类 -> 生成 Markdown
├── collector.py      # RSS 抓取 + 去重 + 时间过滤 + 关键词分类
├── generator.py      # Markdown 格式化输出
├── config.py         # 数据源配置 + 关键词 + 输出规则
├── run.bat           # Windows 一键运行脚本
├── output/           # 生成的简报存放目录
│   └── 2024-05-13-今日体育简报.md
└── README.md         # 本文件
```

---

## 快速开始

### 1. 环境准备

已安装 Python 3.8+，执行：

```bash
pip install feedparser requests beautifulsoup4 lxml
```

### 2. 生成今日简报

```bash
cd sports-agent
python main.py
```

或双击 `run.bat`（Windows）。

输出文件在 `output/2026-05-13-今日体育简报.md`。

### 3. 强制重新生成

```bash
python main.py --force
```

---

## 关注范围

| 分类 | 说明 |
|------|------|
| NBA | 美国职业篮球 |
| CBA | 中国职业篮球 |
| 英超 | 英格兰足球超级联赛 |
| 中超 | 中国足球超级联赛 |
| 伤病 | 球员伤病、复出、手术 |
| 转会 | 签约、续约、交易、选秀 |

分类规则在 `config.py` 的 `CATEGORIES` 中定义，可按喜好调整关键词。

---

## 数据源

当前接入（无需 API Key）：

| 来源 | 内容 | 语言 |
|------|------|------|
| ESPN NBA RSS | NBA 新闻 | 英文 |
| ESPN Soccer RSS | 足球新闻 | 英文 |
| BBC Sport RSS | 综合体育 | 英文 |

> 中文源（新浪体育 RSS 等）已预留配置，视网络情况在 `config.py` 中取消注释即可。

### 进阶：接入 NewsAPI

如需中文新闻，可去 [newsapi.org](https://newsapi.org) 免费注册获取 API Key，
在 `collector.py` 中添加 NewsAPI 调用（100次/天免费额度）。

---

## 设置每天早上自动运行（Windows 计划任务）

1. 按 `Win + R`，输入 `taskschd.msc` 回车
2. 右侧点击 **创建基本任务**
3. 名称：`Mango体育简报`
4. 触发器：**每天** 08:00
5. 操作：**启动程序**
   - 程序：`C:\Users\wangm\first-cc\sports-agent\run.bat`
   - 起始于：`C:\Users\wangm\first-cc\sports-agent`
6. 完成

每天早上 8 点，电脑会自动运行脚本，在 `output/` 文件夹生成当日简报。

---

## 后续扩展路线

| 阶段 | 功能 | 方案 |
|------|------|------|
| MVP | RSS 聚合 + Markdown 简报 | 当前已实现 |
| V1.1 | 接入中文源 + 比赛比分 | 添加虎扑/直播吧爬虫，或接入体育数据 API |
| V1.2 | AI 摘要 + 重点提炼 | 接入 Claude API / 本地大模型，对新闻做中文摘要 |
| V2.0 | Web 前端 + 历史检索 | Next.js + 静态站点生成，每日简报自动部署到网页 |

---

## 自定义配置

编辑 `config.py`：

- `RSS_SOURCES`：增删数据源
- `CATEGORIES`：调整分类关键词
- `TIME_WINDOW`：修改时间窗口（默认 24 小时）
- `MAX_ITEMS_PER_CATEGORY`：每类最多显示条数
