# Mango 个人体育新闻站 — 技术架构方案

> 适用场景：个人 / 小团队开发，内容为主，可能包含实时比分、个性化推荐。

---

## 1. 前端框架与 UI 库

| 层级 | 推荐方案 | 理由 |
|------|----------|------|
| **框架** | **Next.js 14+ (App Router)** | SSR/SSG 对 SEO 极友好（新闻站核心），Vercel 生态成熟，支持 ISR 增量更新 |
| **语言** | TypeScript | 类型安全，维护成本低 |
| **样式** | Tailwind CSS + shadcn/ui | 快速搭建新闻卡片、导航、布局；shadcn 组件可定制，无样式入侵 |
| **移动端** | PWA (Progressive Web App) | 无需开发独立 App，用户可“添加到主屏幕”，支持离线缓存和推送 |
| **状态管理** | Zustand / Jotai | 轻量，适合个人项目，比 Redux 少 boilerplate |
| **数据获取** | SWR / React Query | 缓存、重试、自动刷新，非常适合新闻列表和实时比分 |

**备选**：如果更偏向原生 App 体验，可用 **React Native (Expo)**，但内容型站点 PWA 性价比更高。

---

## 2. 后端 / API 方案

推荐：**Serverless / Edge 优先，逐步演进**

| 阶段 | 方案 | 说明 |
|------|------|------|
| **MVP 阶段** | **Next.js API Routes + Vercel Serverless Functions** | 零运维，按调用付费，和前端同仓库开发 |
| **进阶阶段** | **Vercel Edge Functions / Cloudflare Workers** | 全球边缘节点，低延迟，适合实时比分推送 |
| **数据聚合层** | 独立的 **Node.js / Python 定时脚本**（可跑在 Railway / Render / 自建 VPS） | 负责爬取/拉取第三方体育数据，清洗后写入数据库 |

**为什么不选传统后端？**
个人项目优先降低运维负担。Next.js API Routes 足以覆盖 90% 需求（认证、CRUD、RSS 聚合）。

---

## 3. 数据库选型

采用 **PostgreSQL + Redis** 组合，兼顾关系型数据与缓存/实时需求。

| 数据类型 | 数据库 | 说明 |
|----------|--------|------|
| **新闻文章** | PostgreSQL | 结构化内容（标题、正文、作者、分类、标签、发布时间），支持全文搜索 |
| **用户数据** | PostgreSQL | 用户表、收藏、阅读历史、偏好设置 |
| **实时比分** | Redis | 高频写入、TTL 过期，配合 Pub/Sub 推送 |
| **缓存层** | Redis | 热点新闻、API 响应缓存，减轻数据库压力 |
| **搜索** | PostgreSQL `tsvector` / Meilisearch | 初期用 Postgres 全文搜索即可；量大后接入 Meilisearch（轻量、易部署） |

**托管推荐**：
- **Neon**（Serverless PostgreSQL，按量付费，分支功能适合开发）
- **Upstash**（Serverless Redis，全球边缘，低延迟）

---

## 4. 新闻与数据获取策略

体育新闻来源分三层，避免直接大规模爬取（法律风险 + 反爬）。

### 4.1 优先：官方 API / RSS
| 来源 | 方式 | 内容 |
|------|------|------|
| 新浪体育 / ESPN / BBC Sport | RSS Feed | 新闻标题 + 摘要 + 链接 |
| 各大联赛官方 API | 官方/合作 API | 赛程、比分、球员数据 |
| 聚合 API (如 TheSportsDB, API-Football) | 付费 API | 统一格式的多项目数据 |

### 4.2 次选：定向爬取（需遵守 robots.txt）
- 用 **Python + Scrapy / Playwright** 写定时爬虫
- 只爬取公开列表页，不爬付费内容
- 存储时保留原文链接，做摘要/索引，避免版权争议

### 4.3 实时比分
- 接入 **WebSocket 数据服务商**（如 Sportmonks, FeedConstruct）
- 或爬取公开比分页面（低频率，配合缓存）

**架构示意**：
```
外部数据源 (RSS/API/爬虫)
    ↓
数据聚合服务 (Python/Node 定时任务)
    ↓
清洗 → 去重 → 分类 → 存入 PostgreSQL / Redis
    ↓
Next.js API → 前端展示
```

---

## 5. 部署与托管

| 服务 | 用途 | 推荐平台 |
|------|------|----------|
| **前端 + API** | Next.js 应用 | **Vercel**（最优）或 Cloudflare Pages |
| **数据库** | PostgreSQL | **Neon** 或 Supabase |
| **缓存/实时** | Redis | **Upstash** |
| **爬虫/定时任务** | 数据聚合脚本 | **Railway** / Render / 国内阿里云函数计算 |
| **图片/静态资源** | CDN | Cloudflare R2 / AWS S3 + CloudFront |
| **域名 + DNS** | - | Cloudflare |

**成本预估（MVP 阶段）**：
- Vercel Hobby：免费
- Neon 免费额度：足够起步
- Upstash 免费额度：足够起步
- 爬虫服务：Railway $5/月 或阿里云按量
- **总计：≈ 0 ~ 50 元/月**

---

## 6. 认证方案（个人化功能）

新闻站需要“个人化”（收藏、偏好、历史记录），推荐：

| 方案 | 推荐 | 理由 |
|------|------|------|
| **Auth 服务** | **NextAuth.js (Auth.js)** | 和 Next.js 深度集成，支持 OAuth 2.0 |
| **登录方式** | 微信扫码 / GitHub / Google | 国内用户优先微信；技术用户可给 GitHub |
| **自建账户** | 邮箱 + 密码 | 可用，但需处理验证码、找回密码，增加维护成本 |
| **权限模型** | 简单 RBAC：读者 / 管理员 | 个人站初期只需区分“是否登录” |

**数据隐私**：用户阅读历史、偏好标签存储在 PostgreSQL，敏感字段加密。

---

## 7. 项目目录结构建议

采用 **Monorepo** 管理，前后端同仓库，爬虫独立目录。

```
sports-news/
├── apps/
│   └── web/                    # Next.js 主应用
│       ├── app/                # App Router (页面)
│       │   ├── (home)/         # 首页
│       │   ├── news/[slug]/    # 新闻详情
│       │   ├── scores/         # 实时比分
│       │   ├── favorites/      # 我的收藏
│       │   └── api/            # API Routes
│       ├── components/         # 公共组件
│       ├── lib/                # 工具函数、API 客户端
│       ├── hooks/              # 自定义 Hooks
│       ├── stores/             # Zustand 状态
│       ├── types/              # TypeScript 类型
│       └── public/             # 静态资源
│
├── packages/
│   ├── ui/                     # shadcn/ui 组件库（可复用）
│   ├── shared/                 # 共享类型、常量、工具
│   └── config/                 # ESLint, TS, Tailwind 配置
│
├── services/
│   └── aggregator/             # 数据聚合服务（爬虫/同步）
│       ├── src/
│       │   ├── sources/        # 各数据源适配器
│       │   ├── parsers/        # 内容解析
│       │   ├── pipeline/       # 清洗、去重、分类
│       │   └── scheduler/      # 定时任务
│       └── Dockerfile
│
├── infra/                      # 基础设施配置
│   ├── docker-compose.yml      # 本地开发环境
│   └── vercel.json
│
├── turbo.json                  # Turborepo 任务编排
├── pnpm-workspace.yaml
└── README.md
```

**工具链**：
- **包管理**：pnpm + Turborepo（Monorepo 标准）
- **代码规范**：ESLint + Prettier + Husky（提交前检查）
- **CI/CD**：GitHub Actions → Vercel 自动部署

---

## 8. 演进路线图

| 阶段 | 目标 | 技术重点 |
|------|------|----------|
| **Week 1-2** | MVP 上线 | Next.js + Tailwind + Postgres + RSS 聚合 |
| **Month 1** | 个性化 + 收藏 | NextAuth + 用户表 + 收藏功能 |
| **Month 2** | 实时比分 | Redis + WebSocket + 第三方体育 API |
| **Month 3** | 搜索 + 推送 | Meilisearch + Web Push + PWA |
| **后期** | 多语言 / App | i18n + React Native / Flutter |

---

## 总结

| 维度 | 推荐选择 |
|------|----------|
| 前端 | Next.js 14 + Tailwind + shadcn/ui + PWA |
| 后端 | Next.js API Routes (Serverless) |
| 数据库 | PostgreSQL (Neon) + Redis (Upstash) |
| 数据获取 | RSS/API 为主，定向爬取为辅 |
| 部署 | Vercel + Neon + Upstash + Railway |
| 认证 | NextAuth.js + 微信/GitHub OAuth |
| 仓库 | pnpm Monorepo (Turborepo) |

这套方案的核心优势是：**低运维、低成本、可渐进扩展**。Mango 作为个人开发者，可以把精力集中在内容和产品体验上，而不是服务器维护。
