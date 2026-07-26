# SalesTwin Code Wiki - 项目代码百科全书

> 本文档提供 SalesTwin 项目的完整代码结构说明，帮助开发者快速理解项目架构、核心模块、关键类与函数、依赖关系以及运行方式。

---

## 目录

1. [项目概述](#1-项目概述)
2. [整体架构](#2-整体架构)
3. [后端模块详解](#3-后端模块详解)
4. [前端模块详解](#4-前端模块详解)
5. [数据库模型](#5-数据库模型)
6. [核心服务与关键类](#6-核心服务与关键类)
7. [API 接口概览](#7-api-接口概览)
8. [依赖关系与技术栈](#8-依赖关系与技术栈)
9. [项目运行与部署](#9-项目运行与部署)
10. [Agent 后台任务调度系统](#10-agent-后台任务调度系统)

---

## 1. 项目概述

### 1.1 项目定位

**SalesTwin** 是一款基于《挑战者销售》理论的 B2B 销售数字孪生系统，将客户侧干系人转化为具备内部政治博弈与社交动态的智能体，提供从线索到赢单的全周期销售领航与推演沙盘能力。

> 历史背景：项目早期为 MiroFish（社媒舆论模拟）双产品线，已于 2026-07 完成剥离，仅保留 SalesTwin 一条产品线。

### 1.2 核心工作流

```
Step 1: 商机台账 → 项目创建、阶段切换、商机历程追踪
Step 2: 客户档案 → 客户/联系人/组织架构管理 + 客户级概览
Step 3: 商机概览 → 业务洞察（行业趋势/痛点/当前措施/价值主张/竞争分析）+ 阶段交付物
Step 4: 干系人图谱 → 干系人 CRUD + 关系网络 + 盲区扫描 + 行动推荐
Step 5: 推演作战室 → 闭门发酵模拟 + 深度访谈 + 报告生成 + 反馈解析
```

### 1.3 核心目录结构

```
MiroFish/                       # 仓库根（历史命名保留）
├── backend/                    # Python Flask 后端
│   ├── app/
│   │   ├── api/                # API 路由层
│   │   │   └── sales_twin/     # SalesTwin 蓝图子模块（唯一蓝图）
│   │   ├── jobs/               # 后台定时任务（Flask-APScheduler）
│   │   ├── models/             # 数据模型层（SQLAlchemy ORM）
│   │   ├── services/           # 业务服务层
│   │   └── utils/              # 工具类
│   ├── scripts/                # 迁移脚本与测试
│   ├── uploads/                # 上传文件存储
│   └── instance/               # SQLite 数据库
├── frontend/                   # Vue 3 前端
│   └── src/
│       ├── api/                # API 请求封装
│       ├── components/         # 组件
│       │   ├── salesTwin/      # SalesTwin 主功能组件
│       │   └── dashboard/      # 仪表盘子组件
│       ├── composables/        # 组合式函数
│       ├── constants/          # 常量（销售阶段等）
│       ├── router/             # 路由
│       ├── styles/             # 全局样式
│       ├── views/              # 页面视图
│       └── i18n/               # 国际化
├── docs/                       # 项目文档
├── locales/                    # 国际化语言包
└── scripts/                    # 根目录脚本
```

---

## 2. 整体架构

### 2.1 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (Vue 3)                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────┐  │
│  │ SalesTwin│ │ Customer │ │  Graph   │ │  Workspace    │  │
│  │  Sidebar │ │  Manage  │ │  Visual  │ │  (推演作战室)  │  │
│  └──────────┘ └──────────┘ └──────────┘ └───────────────┘  │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTP
┌───────────────────────────▼─────────────────────────────────┐
│                      Backend (Flask)                         │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              API Layer (sales_twin_bp)               │    │
│  │  projects | stakeholders | customers | tasks |       │    │
│  │  meetings | feedback | graph | analysis | strategy  │    │
│  └─────────────────────────┬───────────────────────────┘    │
│                            │                                │
│  ┌─────────────────────────▼───────────────────────────┐    │
│  │                  Service Layer                       │    │
│  │  ┌─────────────┐ ┌──────────────┐ ┌──────────────┐ │    │
│  │  │ Feedback    │ │ Action       │ │ WinRate      │ │    │
│  │  │ Parser      │ │ Recommender  │ │ Calculator   │ │    │
│  │  └─────────────┘ └──────────────┘ └──────────────┘ │    │
│  │  ┌─────────────┐ ┌──────────────┐ ┌──────────────┐ │    │
│  │  │ BlindSpot   │ │ Fermentation │ │ Meeting Plan │ │    │
│  │  │ Detector    │ │ LLM Simulator│ │ Generator    │ │    │
│  │  └─────────────┘ └──────────────┘ └──────────────┘ │    │
│  │  ┌─────────────┐ ┌──────────────┐ ┌──────────────┐ │    │
│  │  │ Stage       │ │ Suggestion   │ │ Dashboard    │ │    │
│  │  │ Deliverable │ │ Task         │ │ Insight      │ │    │
│  │  │ Manager     │ │ Generator    │ │ Generator    │ │    │
│  │  └─────────────┘ └──────────────┘ └──────────────┘ │    │
│  └─────────────────────────────────────────────────────┘    │
│                            │                                │
│  ┌─────────────────────────▼───────────────────────────┐    │
│  │           Agent Scheduler (Flask-APScheduler)        │    │
│  │  Daily_Health_Scan | Daily_News_Fetch |              │    │
│  │  Weekly_Learning_Eval                                │    │
│  │  → 持久化到 BlindSpotReport / CustomerIntelSnapshot  │    │
│  │  → 运行历史记录到 AgentJobRun                         │    │
│  └─────────────────────────┬───────────────────────────┘    │
│                            │                                │
│  ┌─────────────────────────▼───────────────────────────┐    │
│  │                Model Layer (SQLAlchemy)              │    │
│  │  Project | Customer | Contact | Stakeholder |       │    │
│  │  Relationship | Task | StrategyItem | WhyContext |  │    │
│  │  StageDeliverable | Feedback | StateChangeLog |     │    │
│  │  BlindSpotReport | AgentJobRun |                    │    │
│  │  CustomerIntelSnapshot | ...                        │    │
│  └─────────────────────────────────────────────────────┘    │
└───────────────────────────┬─────────────────────────────────┘
                            │
                ┌───────────┴───────────┐
                ▼                       ▼
           SQLite DB                LLM API
           (本地持久化)          (OpenAI 兼容)
```

### 2.2 单产品模式

系统仅保留 SalesTwin 一条产品线，所有功能通过 `/sales-twin` 入口访问。

---

## 3. 后端模块详解

### 3.1 应用入口与配置

**启动入口**：[run.py](file:///d:/BattleFish/MiroFish/backend/run.py)
- 处理 Windows 控制台中文乱码
- 验证配置完整性
- 创建 Flask 应用并启动

**应用工厂**：[app/__init__.py](file:///d:/BattleFish/MiroFish/backend/app/__init__.py)
- `create_app(config_class=Config)` — Flask 应用工厂函数
- 初始化 SQLAlchemy、CORS、日志
- 注册唯一蓝图 `sales_twin_bp`，URL 前缀 `/api/sales-twin`
- `_init_scheduler()` — 初始化 Flask-APScheduler，注册 3 个定时任务（见第 10 章）
- 提供 `/health` 健康检查接口（返回 `{"service": "SalesTwin Backend"}`）

**配置管理**：[app/config.py](file:///d:/BattleFish/MiroFish/backend/app/config.py)
- 从项目根目录 `.env` 加载环境变量
- 核心配置项：
  - `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL_NAME` — LLM 配置
  - `SQLALCHEMY_DATABASE_URI` — 数据库连接（默认 SQLite）
  - `UPLOAD_FOLDER` — 文件上传目录
  - `CORS_ORIGINS` — 允许的前端来源
- `Config.validate()` — 验证必要配置是否完整

### 3.2 API 路由层（app/api/sales_twin/）

SalesTwin 蓝图按业务域拆分为 13 个子模块，共约 100 个路由：

#### 3.2.1 _helpers.py — 蓝图公共辅助
**文件**：[api/sales_twin/_helpers.py](file:///d:/BattleFish/MiroFish/backend/app/api/sales_twin/_helpers.py)

蓝图内共享的辅助函数集合：
- `project_to_dict(project)` — Project 序列化为 dict，包含 `pain_points_summary` 字段（从首条 pain_point 类型的 ProjectStrategyItem 拼接 name+description，截断 80 字）
- `_build_project_context(project_id)` — 构建 LLM 上下文 dict（干系人、关系、任务、项目信息）
- `_build_project_insight_summary(project_id)` — **业务洞察摘要生成器**，从结构化表拼接 LLM 友好文本，是下游 LLM 消费者（行动推荐/盲区扫描/发酵模拟/任务建议/会议预案/客户概览等）的统一数据源。按 6 段拼接：行业趋势 / 客户痛点 / 当前措施 / 战略举措 / 价值主张（三个WHY）/ 竞争分析；每段无数据时跳过
- `_build_*_nodes` 系列 — 5 个图谱节点构造函数（ProjectContext/IndustryTrend/PainPoint/CurrentMeasure/Stakeholder），从结构化表读取
- `get_stage_definition(stage)` — 读取阶段定义（核心目标/进入条件/退出条件/任务清单/交付物清单）

#### 3.2.2 sales_twin_projects.py — 项目管理
**蓝图前缀**：`/api/sales-twin`

| 接口 | 方法 | 说明 |
|------|------|------|
| `/projects` | GET/POST | 项目列表/创建 |
| `/projects/<id>` | GET/PUT/DELETE | 项目详情/更新/删除 |
| `/projects/<id>/stage` | PUT | 切换销售阶段（写 StateChangeLog） |
| `/projects/<id>/stage-timeline` | GET | 商机阶段时间线（见 6.15） |
| `/projects/<id>/stage-deliverables` | GET/POST | 阶段交付物列表/手动勾选 |
| `/projects/<id>/stage-deliverables/<key>/attachment` | POST/GET/DELETE | 交付物附件上传/下载/删除 |

#### 3.2.3 sales_twin_stakeholders.py — 干系人管理
| 接口 | 方法 | 说明 |
|------|------|------|
| `/projects/<id>/stakeholders` | GET/POST | 干系人列表/创建 |
| `/projects/<id>/stakeholders/merge` | POST | 合并干系人 |
| `/stakeholders/<id>` | GET/PUT/DELETE | 干系人详情/更新/删除 |
| `/relationships` | GET/POST/PUT/DELETE | 关系连线 CRUD |

#### 3.2.4 sales_twin_customers.py — 客户管理
| 接口 | 方法 | 说明 |
|------|------|------|
| `/customers` | GET/POST | 客户列表/创建 |
| `/customers/<id>` | GET/PUT/DELETE | 客户详情/更新/删除 |
| `/customers/merge` | POST | 合并客户 |
| `/customers/<id>/contacts` | GET/POST | 联系人列表/创建 |
| `/customers/<id>/contacts/<cid>` | PUT/DELETE | 联系人更新/删除 |
| `/customers/<id>/org-graph` | GET | 客户组织架构图谱 |
| `/customers/<id>/generate-overview` | POST | 客户级概览 LLM 生成 |
| `/customers/<id>/intel-snapshots` | GET | 客户情报历史快照列表（来源 Agent 后台任务持久化） |

#### 3.2.5 sales_twin_tasks.py — 待办任务
| 接口 | 方法 | 说明 |
|------|------|------|
| `/projects/<id>/tasks` | GET/POST | 任务列表/创建 |
| `/projects/<id>/tasks/adopt-action` | POST | 采纳行动建议为任务 |
| `/projects/<id>/tasks/auto-sort` | POST | AI 自动排序任务 |
| `/tasks/<id>` | PUT/DELETE | 任务更新/删除 |

#### 3.2.6 sales_twin_meetings.py — 拜访预案
| 接口 | 方法 | 说明 |
|------|------|------|
| `/projects/<id>/meeting-plans` | GET/POST | 预案列表/创建 |
| `/meeting-plans/<id>` | GET/PUT/DELETE | 预案详情/更新/删除 |

#### 3.2.7 sales_twin_feedback.py — 反馈解析
| 接口 | 方法 | 说明 |
|------|------|------|
| `/projects/<id>/feedback` | POST | 提交反馈并自动解析更新（FeedbackParser） |
| `/projects/<id>/feedback-records` | GET | 反馈记录列表 |

#### 3.2.8 sales_twin_graph.py — 干系人图谱
| 接口 | 方法 | 说明 |
|------|------|------|
| `/projects/<id>/graph` | GET | 获取项目图谱数据（节点+边） |

`has_any_data` 判断：`ProjectStrategyItem` 或 `ProjectWhyContext` 有记录，或 `competitive_analysis` 非空。

#### 3.2.9 sales_twin_analysis.py — AI 分析与生成
| 接口 | 方法 | 说明 |
|------|------|------|
| `/projects/<id>/scan` | POST | 盲区扫描（手动触发，scan_source='manual'，自动持久化到 BlindSpotReport） |
| `/projects/<id>/blind-spot-reports` | GET | 盲区扫描历史报告列表（按时间倒序，默认 limit=10） |
| `/projects/<id>/blind-spot-latest` | GET | 获取最新盲区报告（前端进项目时自动加载，避免重新扫描） |
| `/projects/<id>/next-best-action` | POST | 下一步行动推荐 |
| `/projects/<id>/action-brief/<sid>` | POST | 单点拜访简报 |
| `/projects/<id>/win-rate` | GET | 赢单率计算 |
| `/projects/<id>/fermentation` | POST | 闭门发酵模拟 |
| `/projects/<id>/fermentation/interview` | POST | 干系人深度访谈 |
| `/projects/<id>/fermentation/report` | POST | 发酵推演报告 |
| `/projects/<id>/competitive-analysis` | POST | LLM 生成竞争分析 |
| `/projects/<id>/reformat-text` | POST | 文本重排（白名单仅 `competitive_analysis`） |
| `/projects/<id>/strategy-items/ai-generate` | POST | AI 生成 3-3-3 战略项草稿 |
| `/projects/<id>/why-contexts/ai-generate` | POST | AI 生成三个WHY草稿 |

> 历史变更：`/customer-overview`、`/value-proposition`、`/business-pain-points` 三个 LLM 文本生成器路由已删除，对应文本字段已废弃，统一以结构化表为单一数据源。

#### 3.2.10 sales_twin_strategy.py — 战略要素 CRUD
| 接口 | 方法 | 说明 |
|------|------|------|
| `/projects/<id>/strategy-items` | GET/POST | 战略项列表/创建（4 类：industry_trend/pain_point/current_measure/strategic_initiative，每类最多 3 条） |
| `/strategy-items/<id>` | PUT/DELETE | 战略项更新/删除 |
| `/projects/<id>/why-contexts` | GET | 三个WHY 列表（why/why_now/why_us，每类至多 1 条，upsert 语义） |
| `/projects/<id>/why-contexts/<type>` | PUT | upsert 单条 WHY |
| `/why-contexts/<id>` | DELETE | 删除 WHY |

#### 3.2.11 sales_twin_stage.py — 阶段交付物
| 接口 | 方法 | 说明 |
|------|------|------|
| `/projects/<id>/stage-deliverables` | GET | 阶段交付物列表（含自动检查状态 + 手动勾选状态 + 附件） |
| `/projects/<id>/stage-deliverables` | POST | 手动勾选/取消勾选交付物 |
| `/projects/<id>/stage-deliverables/<key>/attachment` | POST/GET/DELETE | 交付物附件上传/下载/删除 |

#### 3.2.12 sales_twin_settings.py — 系统设置
| 接口 | 方法 | 说明 |
|------|------|------|
| `/settings/llm` | GET/PUT | LLM 配置（API Key/Base URL/Model，运行时可修改无需重启） |
| `/settings/company` | GET/PUT | 公司信息（名称/简介/产品简介，注入 AI 生成 prompt） |
| `/settings/company/attachments` | GET/POST | 公司产品文档附件（PDF/MD/TXT，自动提取文本供 AI 分析） |
| `/settings/company/attachments/<id>` | DELETE | 删除产品文档附件 |

#### 3.2.13 sales_twin_agent.py — Agent 任务管理
| 接口 | 方法 | 说明 |
|------|------|------|
| `/agent/jobs` | GET | 获取所有定时任务列表（3 个：Daily_Health_Scan/Daily_News_Fetch/Weekly_Learning_Eval） |
| `/agent/jobs/<job_id>` | GET | 获取指定任务详情 |
| `/agent/jobs/<job_id>/schedule` | PUT | 修改任务调度配置（cron 表达式 / 时区） |
| `/agent/jobs/<job_id>/run` | POST | 立即手动触发指定任务 |
| `/agent/jobs/<job_id>/runs` | GET | 获取任务最近运行历史记录（来自 AgentJobRun 表，默认 limit=10） |

### 3.3 服务层（app/services/）

服务层是业务逻辑的核心，共 15 个服务模块。详见 [第 6 章](#6-核心服务与关键类)。

### 3.4 模型层（app/models/）

#### 3.4.1 database.py — 核心数据模型
包含所有 SQLAlchemy ORM 模型定义（18 张表），详见 [第 5 章](#5-数据库模型)。

### 3.5 工具层（app/utils/）

| 模块 | 说明 | 核心类/函数 |
|------|------|------------|
| [llm_client.py](file:///d:/BattleFish/MiroFish/backend/app/utils/llm_client.py) | LLM 客户端封装（OpenAI 兼容格式） | `LLMClient.chat()`, `LLMClient.extract_json()` |
| [llm_tools.py](file:///d:/BattleFish/MiroFish/backend/app/utils/llm_tools.py) | LLM 工具函数 | Prompt 模板构建、JSON 提取 |
| [file_parser.py](file:///d:/BattleFish/MiroFish/backend/app/utils/file_parser.py) | 文件解析器 | `FileParser.parse_pdf()`, `parse_text()` |
| [logger.py](file:///d:/BattleFish/MiroFish/backend/app/utils/logger.py) | 日志系统（默认 logger 名 `salestwin`） | `setup_logger()`, `get_logger()` |

---

## 4. 前端模块详解

### 4.1 技术栈

- **框架**：Vue 3（Composition API + `<script setup>`）
- **构建工具**：Vite 7.x
- **路由**：Vue Router 4
- **国际化**：Vue I18n 11
- **HTTP 客户端**：Axios
- **图谱可视化**：@antv/g6 5.x + D3.js 7.x
- **样式**：原生 CSS（无 UI 框架，定制化黑白橙极简风格）

### 4.2 入口与配置

**主入口**：[src/main.js](file:///d:/BattleFish/MiroFish/frontend/src/main.js)
- 创建 Vue 应用实例
- 注册 Vue Router、Vue I18n
- 挂载到 `#app`

**根组件**：[src/App.vue](file:///d:/BattleFish/MiroFish/frontend/src/App.vue)
- 仅包含 `<router-view>` 路由出口
- 全局样式重置与字体设置

**构建配置**：[vite.config.js](file:///d:/BattleFish/MiroFish/frontend/vite.config.js)
- 端口：3000
- API 代理：`/api` → `http://localhost:5001`
- 路径别名：`@` → `src/`, `@locales` → `../locales`

### 4.3 路由结构（src/router/）

| 路径 | 页面组件 | 说明 |
|------|---------|------|
| `/` | — | 重定向到 `/sales-twin` |
| `/sales-twin` | SalesTwin.vue | SalesTwin 主界面（唯一入口） |

### 4.4 核心页面（src/views/）

#### 4.4.1 SalesTwin.vue — SalesTwin 主页面
**文件**：[views/SalesTwin.vue](file:///d:/BattleFish/MiroFish/frontend/src/views/SalesTwin.vue)

采用**侧边栏 + 主内容区**布局：
- **左侧边栏**：[SalesTwinSidebar.vue](file:///d:/BattleFish/MiroFish/frontend/src/components/SalesTwinSidebar.vue) — 全局菜单（仪表盘/客户管理/商机台账）+ 项目菜单（概览/商机历程/干系人图谱/干系人列表/盲区/行动/待办/会议/拜访/反馈/作战室）
- **主内容区**：根据 `activeMenu` 切换不同视图

支持的功能模块（`activeMenu` 取值）：
- `dashboard` — 仪表盘（DashboardMetrics + InsightPanel + AttentionItems）
- `projects` — 商机台账列表（ProjectList）
- `overview` — 商机概览（ProjectInfoSection + BusinessInsightSection + StageDeliverablesPanel）
- `timeline` — 商机历程（StageTimeline）
- `graph` — 干系人权力图谱（GraphView）
- `stakeholders` — 干系人列表管理（StakeholderView）
- `blindspot` / `actions` / `tasks` / `meeting` / `visit` — WorkspaceView 子菜单
- `workspace` — 推演作战室（WorkspaceView）
- `feedback` — 反馈记录与更新
- `customers` — 客户管理（CustomerManagement）
- `customer_overview` / `customer_contacts` / `customer_opportunities` / `customer_org` — 客户详情子菜单

#### 4.4.2 SalesDashboard.vue — 仪表盘
**文件**：[views/SalesDashboard.vue](file:///d:/BattleFish/MiroFish/frontend/src/views/SalesDashboard.vue)
- DashboardMetrics — 关键指标卡片
- InsightPanel — LLM 智能洞察（按时间范围）
- AttentionItems — 重点关注事项

### 4.5 核心组件（src/components/）

#### 4.5.1 SalesTwin 子组件（components/salesTwin/）

| 组件 | 说明 |
|------|------|
| [ProjectList.vue](file:///d:/BattleFish/MiroFish/frontend/src/components/salesTwin/ProjectList.vue) | 商机台账列表（卡片摘要读 `pain_points_summary`） |
| [OverviewPane.vue](file:///d:/BattleFish/MiroFish/frontend/src/components/salesTwin/OverviewPane.vue) | 项目概览面板（ProjectInfoSection + BusinessInsightSection + StageDeliverablesPanel） |
| [ProjectInfoSection.vue](file:///d:/BattleFish/MiroFish/frontend/src/components/salesTwin/ProjectInfoSection.vue) | 项目基础信息卡片 |
| [BusinessInsightSection.vue](file:///d:/BattleFish/MiroFish/frontend/src/components/salesTwin/BusinessInsightSection.vue) | **业务洞察统一面板**（5 Tab：行业趋势/痛点/当前措施/价值主张/竞争分析） |
| [StageDeliverablesPanel.vue](file:///d:/BattleFish/MiroFish/frontend/src/components/salesTwin/StageDeliverablesPanel.vue) | 阶段交付物追踪面板 |
| [StageTimeline.vue](file:///d:/BattleFish/MiroFish/frontend/src/components/salesTwin/StageTimeline.vue) | 商机历程时间线 |
| [GraphView.vue](file:///d:/BattleFish/MiroFish/frontend/src/components/salesTwin/GraphView.vue) | 干系人权力图谱视图（G6/D3 可视化） |
| [StakeholderView.vue](file:///d:/BattleFish/MiroFish/frontend/src/components/salesTwin/StakeholderView.vue) | 干系人列表管理 |
| [SimulationView.vue](file:///d:/BattleFish/MiroFish/frontend/src/components/salesTwin/SimulationView.vue) | 推演模拟视图 |
| [WorkspaceView.vue](file:///d:/BattleFish/MiroFish/frontend/src/components/salesTwin/WorkspaceView.vue) | 作战室视图（盲区/行动/待办/会议/拜访 子菜单，盲区页显示上次扫描时间+来源标签） |
| [AgentJobManager.vue](file:///d:/BattleFish/MiroFish/frontend/src/components/salesTwin/AgentJobManager.vue) | Agent 任务管理面板（3 个定时任务卡片 + 最近运行记录展示） |
| [SettingsPanel.vue](file:///d:/BattleFish/MiroFish/frontend/src/components/salesTwin/SettingsPanel.vue) | 系统设置面板（LLM 配置 + 公司信息 + 产品文档附件） |
| [LearningCenter.vue](file:///d:/BattleFish/MiroFish/frontend/src/components/salesTwin/LearningCenter.vue) | 智能进化中心（模式筛选/卡片列表/批准/弃用） |
| [CustomerManagement.vue](file:///d:/BattleFish/MiroFish/frontend/src/components/salesTwin/CustomerManagement.vue) | 客户管理模块 |
| [NewProjectModal.vue](file:///d:/BattleFish/MiroFish/frontend/src/components/salesTwin/NewProjectModal.vue) | 新建项目弹窗 |
| [NewCustomerModal.vue](file:///d:/BattleFish/MiroFish/frontend/src/components/salesTwin/NewCustomerModal.vue) | 新建客户弹窗 |
| [NewTaskModal.vue](file:///d:/BattleFish/MiroFish/frontend/src/components/salesTwin/NewTaskModal.vue) | 新建任务弹窗 |
| [NewPlanModal.vue](file:///d:/BattleFish/MiroFish/frontend/src/components/salesTwin/NewPlanModal.vue) | 新建拜访预案弹窗 |
| [StageCheckModal.vue](file:///d:/BattleFish/MiroFish/frontend/src/components/salesTwin/StageCheckModal.vue) | 阶段切换前检查弹窗 |
| [StakeholderAddModal.vue](file:///d:/BattleFish/MiroFish/frontend/src/components/salesTwin/StakeholderAddModal.vue) | 添加干系人弹窗 |
| [StakeholderDeleteConfirmModal.vue](file:///d:/BattleFish/MiroFish/frontend/src/components/salesTwin/StakeholderDeleteConfirmModal.vue) | 删除干系人确认弹窗 |
| [GenericConfirmModal.vue](file:///d:/BattleFish/MiroFish/frontend/src/components/salesTwin/GenericConfirmModal.vue) | 通用确认弹窗（替代原生 confirm） |
| [GlobalToast.vue](file:///d:/BattleFish/MiroFish/frontend/src/components/salesTwin/GlobalToast.vue) | 全局 Toast 通知（替代原生 alert） |

> 历史变更：`StrategyItemsPanel.vue` 和 `WhyContextsPanel.vue` 已删除，功能合并到 BusinessInsightSection.vue 的 5 个 Tab 中。

#### 4.5.2 通用组件

| 组件 | 说明 |
|------|------|
| [SalesTwinSidebar.vue](file:///d:/BattleFish/MiroFish/frontend/src/components/SalesTwinSidebar.vue) | SalesTwin 左侧导航栏 |
| [BaseGraph.vue](file:///d:/BattleFish/MiroFish/frontend/src/components/BaseGraph.vue) | 图谱基类组件（统一 UI/UX：CSS 变量/工具栏/详情面板/空状态） |
| [CustomerOrgGraph.vue](file:///d:/BattleFish/MiroFish/frontend/src/components/CustomerOrgGraph.vue) | 客户组织架构图谱（预设布局，孤立节点纵向排列左侧，连通节点分层横向排列） |
| [CustomerProfile.vue](file:///d:/BattleFish/MiroFish/frontend/src/components/CustomerProfile.vue) | 客户档案展示 |
| [GraphPanel.vue](file:///d:/BattleFish/MiroFish/frontend/src/components/GraphPanel.vue) | 图谱侧边栏（缩略图） |
| [StakeholderDetailPanel.vue](file:///d:/BattleFish/MiroFish/frontend/src/components/StakeholderDetailPanel.vue) | 干系人详情面板 |
| [SuggestionPoolDrawer.vue](file:///d:/BattleFish/MiroFish/frontend/src/components/SuggestionPoolDrawer.vue) | 建议池抽屉 |
| [SalesDeepInterview.vue](file:///d:/BattleFish/MiroFish/frontend/src/components/SalesDeepInterview.vue) | 深度访谈组件 |
| [SalesSimulationReport.vue](file:///d:/BattleFish/MiroFish/frontend/src/components/SalesSimulationReport.vue) | 发酵推演报告组件 |

#### 4.5.3 仪表盘子组件（components/dashboard/）

| 组件 | 说明 |
|------|------|
| [DashboardMetrics.vue](file:///d:/BattleFish/MiroFish/frontend/src/components/dashboard/DashboardMetrics.vue) | 关键指标卡片 |
| [InsightPanel.vue](file:///d:/BattleFish/MiroFish/frontend/src/components/dashboard/InsightPanel.vue) | LLM 智能洞察面板 |
| [AttentionItems.vue](file:///d:/BattleFish/MiroFish/frontend/src/components/dashboard/AttentionItems.vue) | 重点关注事项 |
| [TimeRangeSelector.vue](file:///d:/BattleFish/MiroFish/frontend/src/components/dashboard/TimeRangeSelector.vue) | 时间范围选择器 |

### 4.6 API 请求层（src/api/）

| 文件 | 说明 |
|------|------|
| [index.js](file:///d:/BattleFish/MiroFish/frontend/src/api/index.js) | Axios 实例封装（请求/响应拦截器） |
| [salesTwin.js](file:///d:/BattleFish/MiroFish/frontend/src/api/salesTwin.js) | SalesTwin 全部 API 封装（约 100+ 个接口，含 Agent 任务管理、盲区报告持久化、客户情报快照、自进化引擎、系统设置） |

### 4.7 组合式函数（src/composables/）

**useSalesTwin.js** — SalesTwin 核心状态管理
**文件**：[composables/salesTwin/useSalesTwin.js](file:///d:/BattleFish/MiroFish/frontend/src/composables/salesTwin/useSalesTwin.js)

SalesTwin 前端核心状态与逻辑层（约 1000+ 行），管理：
- 项目、干系人、关系、任务、预案、客户、联系人等数据状态
- 图谱加载、构建、刷新逻辑
- AI 功能调用（盲区扫描、行动推荐、发酵模拟等）
- 反馈提交与解析
- `graphSidebar` ref（控制图谱侧边栏显示）
- `loadProjectData()` 进入项目时自动调用 `getLatestBlindSpotReport` 加载数据库中的最新盲区报告，避免每次重新扫描

**useSalesTwinWorkspace.js** — 作战室状态管理
**文件**：[composables/salesTwin/useSalesTwinWorkspace.js](file:///d:/BattleFish/MiroFish/frontend/src/composables/salesTwin/useSalesTwinWorkspace.js)

作战室事件处理层，包含：
- `handleScanBlindSpots()` — 触发盲区扫描（manual 来源）
- `handleLoadActions()` / `handleAdoptAction()` / `handleRejectAction()` — 行动建议生成/采纳/拒绝（自进化引擎双路路由）
- `handleAutoSortTasks()` / `handleApplyTaskSort()` — 待办智能排序
- 待办、预案、反馈的内联编辑与状态变更处理

**useConfirmToast.js** — 确认弹窗与 Toast 通知的响应式单例
- `requestConfirm(options)` — 替代原生 `confirm()`
- `showToast(message, type)` — 替代原生 `alert()`，支持 success/error/warning/info

**formatters.js** — 格式化工具函数
- `formatCurrency()` — 货币格式化
- `formatDate()` / `formatDateTime()` — 日期格式化
- `formatStructuredText()` — 结构化文本渲染
- `truncateText()` — 文本截断
- `formatFileSize()` — 文件大小格式化

### 4.8 常量与配置

**src/constants/salesStages.js** — 销售阶段定义（全系统唯一来源）
- `SALES_STAGES` — 6 个阶段（suspect/identity/define/confirm/closed_won/closed_lost）
- `STAGE_LABELS` — 阶段中文标签
- `STAGE_DESCRIPTIONS` — 阶段描述（含 OM 里程碑）
- `ACTIVE_STAGES` — 活跃阶段列表
- `CLOSED_STAGES` — 终态阶段列表
- `LEGACY_STAGE_MAPPING` — 旧版四阶段 → 新版五阶段映射（discovery/qualification/proposal/negotiation → suspect/identity/define/confirm）

### 4.9 国际化（src/i18n/ + locales/）

- 语言：中文（zh）、英文（en）
- 语言包位置：`/locales/zh.json`, `/locales/en.json`
- 仅保留 `common`、`meta`、`graph` 三个命名空间
- 配置：[locales/languages.json](file:///d:/BattleFish/MiroFish/locales/languages.json)

---

## 5. 数据库模型

### 5.1 数据库配置
- **类型**：SQLite（默认），可通过 `DATABASE_URI` 环境变量切换
- **ORM**：Flask-SQLAlchemy 3.x + SQLAlchemy 2.x
- **数据库文件**：`backend/instance/sales_twin.db`

### 5.2 核心数据表（18 张）

#### 5.2.1 customer — 客户档案表
**文件**：[models/database.py#L8](file:///d:/BattleFish/MiroFish/backend/app/models/database.py#L8)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 主键 |
| name | String(200) | 客户名称 |
| parent_id | Integer FK | 父客户 ID（支持树形层级） |
| unified_credit_code | String(50) | 统一社会信用代码 |
| registered_capital | String(100) | 注册资本 |
| establish_date | Date | 成立日期 |
| legal_representative | String(100) | 法定代表人 |
| industry | String(100) | 所属行业 |
| core_products | Text | 核心产品/服务 |
| customer_background | Text | 客户概览 |
| created_at / updated_at | DateTime | 创建/更新时间 |

**关系**：`children`（子客户）、`contacts`（联系人）、`projects`（关联商机）

#### 5.2.2 contact — 客户联系人表
**文件**：[models/database.py#L54](file:///d:/BattleFish/MiroFish/backend/app/models/database.py#L54)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 主键 |
| customer_id | Integer FK | 所属客户 ID |
| name | String(100) | 姓名 |
| department | String(100) | 部门 |
| position | String(100) | 职位 |
| phone / email | String | 联系方式 |
| reports_to_id | Integer FK | 汇报对象（自引用） |
| source | String(20) | 来源：manual/web_search/llm_inferred |

#### 5.2.3 project — 商机项目表
**文件**：[models/database.py#L82](file:///d:/BattleFish/MiroFish/backend/app/models/database.py#L82)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 主键 |
| name | String(200) | 项目名称 |
| customer_id | Integer FK | 关联客户 ID |
| customer_name | String(200) | 客户名称（冗余，向后兼容） |
| sales_stage | String(50) | 销售阶段：suspect/identity/define/confirm/closed_won/closed_lost |
| budget | Float | 预算规模 |
| industry | String(100) | 行业 |
| company_vision | Text | 公司愿景/战略目标 |
| business_pain_points | Text | 业务痛点（**已废弃**，结构化数据存 ProjectStrategyItem） |
| customer_background | Text | 客户背景（**已废弃**，结构化数据存 ProjectStrategyItem） |
| value_proposition | Text | 价值主张（**已废弃**，结构化数据存 ProjectWhyContext） |
| competitive_analysis | Text | 竞争分析（仍使用，BusinessInsightSection Tab 5） |
| expected_close_date | Date | 预计关闭日期 |
| time_certainty / budget_certainty | Integer | 时间/预算确定性（1红/2黄/3绿） |
| tendency | Integer | 倾向性（1红/2黄/3绿） |

> 历史变更：`business_pain_points`、`customer_background`、`value_proposition` 三个文本字段已废弃，下游 LLM 消费者统一改用 `_build_project_insight_summary()` 从结构化表拼接摘要。字段保留仅为向后兼容，不再写入新数据。

**关系**：`stakeholders`、`relationships`、`tasks`、`meeting_plans`、`feedback_records`、`state_changes`、`suggestions`、`strategy_items`、`why_contexts`

#### 5.2.4 stakeholder — 干系人表
**文件**：[models/database.py#L128](file:///d:/BattleFish/MiroFish/backend/app/models/database.py#L128)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 主键 |
| project_id | Integer FK | 所属项目 ID |
| name | String(100) | 姓名 |
| position | String(100) | 职位 |
| level | String(50) | 职级：高管/中层/基层/未填写 |
| responsibilities | Text | 职责范围 |
| personal_agenda | Text | 个人私利/动机 |
| buyer_role | Enum | 项目角色：mobilizer/blocker/guide/champion/skeptic/coach |
| reports_to_id | Integer FK | 汇报对象（自引用） |
| decision_power | Integer 0-10 | 决策影响力 |
| support_level | Integer 0-10 | 支持度 |
| urgency | Integer 0-10 | 紧迫感 |

#### 5.2.5 relationship — 关系连线表
**文件**：[models/database.py#L173](file:///d:/BattleFish/MiroFish/backend/app/models/database.py#L173)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 主键 |
| project_id | Integer FK | 项目 ID |
| source_id | Integer FK | 源干系人 ID |
| target_id | Integer FK | 目标干系人 ID |
| relationship_type | Enum | 关系类型：direct_report/peer/allies/conflict/mentor/friend |
| influence_weight | Float 0-1 | 影响力权重 |

#### 5.2.6 opportunity_task — 商机推进任务表
**文件**：[models/database.py#L214](file:///d:/BattleFish/MiroFish/backend/app/models/database.py#L214)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 主键 |
| project_id | Integer FK | 项目 ID |
| stakeholder_id / stakeholder_ids | Integer / Text | 关联干系人（主干系人 + 多干系人 JSON） |
| task_type | Enum | 任务类型：blind_spot/address_concerns/build_alliance/provide_material/meeting/follow_up |
| title / description | String/Text | 标题/描述 |
| action_brief | Text | 单点拜访简报内容 |
| priority | String(20) | 优先级：high/medium/low |
| status | String(20) | 状态：pending/in_progress/completed/cancelled |
| source | String(50) | 来源：recommended_action/manual/feedback |
| source_action | Text | 来源行动建议元数据（JSON） |
| due_date / completed_at | DateTime | 截止/完成时间 |
| completion_note | Text | 完成备注 |

#### 5.2.7 meeting_plan — 拜访预案表
**文件**：[models/database.py#L252](file:///d:/BattleFish/MiroFish/backend/app/models/database.py#L252)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 主键 |
| project_id / stakeholder_id(s) | Integer / Text | 项目与干系人 |
| name | String(200) | 预案名称 |
| meeting_purpose | String(200) | 会议目的 |
| meeting_type | String(50) | 会议类型：初次拜访/方案汇报/异议处理/关系维护 |
| related_task_ids | Text | 关联待办 ID（JSON 数组） |
| related_materials | Text | 关联资料（JSON 数组） |
| plan_content | Text | LLM 生成的结构化预案（JSON） |
| status | String(50) | 状态：pending/generated/reviewed |

#### 5.2.8 feedback_record — 反馈记录表
**文件**：[models/database.py#L282](file:///d:/BattleFish/MiroFish/backend/app/models/database.py#L282)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 主键 |
| project_id | Integer FK | 项目 ID |
| related_task_ids | Text | 关联待办 ID（JSON 数组） |
| related_meeting_plan_id | Integer | 关联拜访预案 ID |
| feedback_text | Text | 原始反馈文本 |
| parse_summary | Text | 解析结果摘要 |
| total_changes | Integer | 总变更数 |
| attachments | Text | 附件列表（JSON 数组） |

#### 5.2.9 state_change_log — 状态变更日志表
**文件**：[models/database.py#L307](file:///d:/BattleFish/MiroFish/backend/app/models/database.py#L307)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 主键 |
| project_id / stakeholder_id | Integer FK | 项目/干系人 ID |
| change_object | String(100) | 变更对象 |
| attribute_name | String(50) | 属性名 |
| old_value / new_value | String | 旧值/新值 |
| reasoning | Text | AI 归因解释 |
| change_source | String(50) | 变更来源：manual_edit/manual/feedback/fermentation/... |

> 重要：`attribute_name='sales_stage'` 的日志中，`old_value`/`new_value` 可能保留旧版四阶段值（discovery/qualification/proposal/negotiation）。后端 `get_project_stage_timeline` 通过 `_normalize_stage()` 在读取时映射到新版五阶段，不修改原始日志数据。

#### 5.2.10 suggestion_pool — 建议池表
**文件**：[models/database.py#L328](file:///d:/BattleFish/MiroFish/backend/app/models/database.py#L328)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 主键 |
| project_id | Integer FK | 项目 ID |
| content | Text | 建议内容 |
| source | String(50) | 来源：interview/report/manual |
| source_context | Text | 来源上下文（JSON） |
| is_consumed | Integer | 是否已被采纳生成待办 |

#### 5.2.11 stage_deliverable — 阶段交付物追踪表
**文件**：[models/database.py#L350](file:///d:/BattleFish/MiroFish/backend/app/models/database.py#L350)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 主键 |
| project_id | Integer FK | 项目 ID |
| stage | String(50) | 阶段：suspect/identity/define/confirm/closed_won/closed_lost |
| deliverable_key | String(100) | 交付物键（与阶段定义中的 key 对应） |
| manual_status | String(20) | 手动勾选状态：confirmed/unchecked |
| attachments | Text | 附件列表（JSON 数组，含文件名/路径/上传时间） |

**唯一约束**：`(project_id, stage, deliverable_key)`

#### 5.2.12 dashboard_insight_cache — 仪表盘洞察缓存表
**文件**：[models/database.py#L383](file:///d:/BattleFish/MiroFish/backend/app/models/database.py#L383)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 主键 |
| start_date / end_date | Date | 时间范围 |
| period | String(32) | 周期标识（自定义模式为 None） |
| label | String(32) | 显示标签（如"本季度"） |
| insights_json | Text | 洞察内容 JSON 字符串 |

**唯一约束**：`(start_date, end_date)`

#### 5.2.13 project_strategy_item — 项目战略要素表
**文件**：[models/database.py#L404](file:///d:/BattleFish/MiroFish/backend/app/models/database.py#L404)

结构化存储客户背景中的行业趋势/当前措施/痛点/战略举措。替代原 `project.customer_background` 大文本字段，支持细粒度编辑和图谱连线。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 主键 |
| project_id | Integer FK | 项目 ID |
| item_type | String(50) | 条目类型：industry_trend/current_measure/pain_point/strategic_initiative |
| name | String(200) | 名称 |
| description | Text | 描述 |
| metadata_json | Text | JSON 扩展字段（impact_area/effectiveness/severity） |
| sort_order | Integer | 排序值 |

**唯一约束**：`(project_id, item_type, sort_order)` — 每类最多 3 条
**索引**：`(project_id, item_type)` — 加速分组查询

#### 5.2.14 project_why_context — 项目三个WHY表
**文件**：[models/database.py#L434](file:///d:/BattleFish/MiroFish/backend/app/models/database.py#L434)

结构化存储价值主张中的 why/why_now/why_us 三段。替代原 `project.value_proposition` 大文本字段，支撑 Tailoring 关系连线。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 主键 |
| project_id | Integer FK | 项目 ID |
| context_type | String(50) | 上下文类型：why/why_now/why_us |
| context_text | Text | 正文 |
| rationale | Text | 理由说明（可选） |

**唯一约束**：`(project_id, context_type)` — 每类至多 1 条（upsert 语义）

#### 5.2.15 meeting_simulation — 会议模拟记录表
**文件**：[models/database.py#L195](file:///d:/BattleFish/MiroFish/backend/app/models/database.py#L195)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 主键 |
| project_id | Integer FK | 项目 ID |
| name | String(200) | 名称 |
| input_pdfs | Text | 输入 PDF 列表 |
| participants | Text | 参会者列表 |
| simulation_result | Text | 模拟结果 |
| status | String(50) | 状态：pending/running/completed/failed |

#### 5.2.16 blind_spot_report — 盲区扫描报告持久化表
**文件**：[models/database.py](file:///d:/BattleFish/MiroFish/backend/app/models/database.py)

持久化每次盲区扫描结果（手动触发 / Agent 后台定时触发），前端进入项目时自动加载最新报告，避免重复扫描。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 主键 |
| project_id | Integer FK | 项目 ID |
| scan_source | String(20) | 扫描来源：manual（HTTP 触发）/ cron（后台定时） |
| overall_score | Integer | 图谱健康度评分（0-100） |
| summary | Text | 扫描摘要 |
| findings_json | Text | 盲区发现列表（JSON） |
| total_findings | Integer | 盲区发现总数 |
| total_stakeholders | Integer | 干系人总数 |
| total_relationships | Integer | 关系总数 |
| scanned_at | DateTime | 扫描时间 |

**索引**：`(project_id, scanned_at)` — 加速按项目查询最新报告
**关系**：`project`（反向引用 `blind_spot_reports`）

#### 5.2.17 agent_job_run — Agent 任务运行历史表
**文件**：[models/database.py](file:///d:/BattleFish/MiroFish/backend/app/models/database.py)

记录每个 Agent 后台任务的每次执行，供 AgentJobManager 页面展示运行历史。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 主键 |
| job_id | String(100) | 任务 ID（如 Daily_Health_Scan） |
| started_at | DateTime | 开始时间 |
| finished_at | DateTime | 结束时间 |
| status | String(20) | 状态：success / failed / partial |
| items_processed | Integer | 处理项目总数 |
| items_succeeded | Integer | 成功项目数 |
| summary | Text | 运行摘要 |
| error_message | Text | 错误信息 |

**索引**：`(job_id, started_at)` — 加速按任务查询历史

**生命周期管理**（在 [jobs/tasks.py](file:///d:/BattleFish/MiroFish/backend/app/jobs/tasks.py) 中）：
- `_start_job_run(job_id)` — 任务开始时创建记录（默认 status=failed，防止异常退出导致无结束记录）
- `_finish_job_run(run, status, summary, error_message, items_processed, items_succeeded)` — 任务结束时更新最终状态

#### 5.2.18 customer_intel_snapshot — 客户情报历史快照表
**文件**：[models/database.py](file:///d:/BattleFish/MiroFish/backend/app/models/database.py)

持久化 Agent 后台任务拉取的客户情报，替代原写回 `Customer.profile_overview` 的逻辑（该字段不存在）。

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer PK | 主键 |
| customer_id | Integer FK | 客户 ID（可空） |
| customer_name | String(200) | 客户名称 |
| industry | String(100) | 行业 |
| report_text | Text | 情报报告全文 |
| source | String(20) | 来源：manual / cron |
| fetched_at | DateTime | 拉取时间 |

**索引**：`(customer_id, fetched_at)` — 加速按客户查询情报历史
**关系**：`customer`（反向引用 `intel_snapshots`）

---

## 6. 核心服务与关键类

### 6.1 反馈解析服务
**类**：`FeedbackParserService`
**文件**：[services/feedback_parser.py](file:///d:/BattleFish/MiroFish/backend/app/services/feedback_parser.py)

**职责**：解析非结构化销售纪要文本，自动更新干系人属性。

**核心方法**：
- `parse_feedback(project_id, feedback_text, related_task_ids, ...)` — 解析反馈并应用更新
- `_parse_with_llm(...)` — 使用 LLM 解析（支持识别新干系人 + 更新现有干系人）
- `_parse_with_rules(...)` — 规则解析（降级方案）
- `_apply_update(project_id, update)` — 应用单条属性更新并记录变更日志

**完成关键词识别**：反馈包含"完成/已沟通/已送达/确认/同意"等关键词时自动标记关联任务为已完成。

### 6.2 行动推荐服务
**类**：`ActionRecommender`
**文件**：[services/action_recommender.py](file:///d:/BattleFish/MiroFish/backend/app/services/action_recommender.py)

**职责**：基于图谱热力值计算，生成 Next Best Action 推荐。

**核心方法**：
- `recommend_actions(project_id)` — 生成下一步行动推荐列表
- `_generate_blind_spot_actions(blind_spots)` — 从盲区生成行动
- `_generate_llm_stakeholder_actions(...)` — LLM 生成干系人策略行动（上下文来自 `_build_project_insight_summary`）
- `_generate_relationship_actions(...)` — 从关系网络生成行动

### 6.3 盲区检测服务
**类**：`BlindSpotDetector`
**文件**：[services/blind_spot_detector.py](file:///d:/BattleFish/MiroFish/backend/app/services/blind_spot_detector.py)

**职责**：扫描图谱完整性，主动预警盲区，并将结果持久化到 `BlindSpotReport` 表。

**检测维度**：缺失关键角色、信息不足、关系断裂、支持度低、决策链不完整等。

**核心方法**：
- `scan_project(project_id, scan_source='manual')` — 执行盲区扫描，scan_source 区分手动触发（manual）和后台定时（cron）
- `_persist_report(project_id, scan_source, result)` — 将扫描结果持久化到 BlindSpotReport 表
- `get_latest_report(project_id)` — 静态方法，获取项目最新盲区报告（前端首次加载时调用）

### 6.4 赢单率计算器
**类**：`WinRateCalculator`
**文件**：[services/win_rate_calculator.py](file:///d:/BattleFish/MiroFish/backend/app/services/win_rate_calculator.py)

**职责**：基于干系人支持度、决策影响力、关系网络计算赢单概率。

**计算维度（权重）**：
- 加权支持度（40%）：`support_level × decision_power` 加权平均
- 网络得分（25%）：关系网络连通性、影响力传导
- 动能得分（15%）：近期状态变化趋势
- 角色覆盖度（20%）：关键决策角色覆盖情况

### 6.5 LLM 闭门发酵模拟器
**类**：`LLMFermentationSimulator`
**文件**：[services/fermentation_llm_simulator.py](file:///d:/BattleFish/MiroFish/backend/app/services/fermentation_llm_simulator.py)

**职责**：按干系人职责/汇报线/影响力推演多轮扩散互动（故事化叙事模式）。

**核心方法**：
- `simulate(project_id, rounds, ...)` — 运行发酵模拟
- `interview(stakeholder_id, question, simulation_context)` — 与模拟后的干系人对话
- `_build_context(...)` — 构建模拟上下文（项目洞察摘要 + 干系人 + 关系 + 待办 + 反馈）

### 6.6 拜访预案生成器
**类**：`MeetingPlanGenerator`
**文件**：[services/meeting_plan_generator.py](file:///d:/BattleFish/MiroFish/backend/app/services/meeting_plan_generator.py)

**职责**：生成结构化的拜访前预案（基于 Challenger Sales 方法论）。

### 6.7 建议任务生成器
**类**：`SuggestionTaskGenerator`
**文件**：[services/suggestion_task_generator.py](file:///d:/BattleFish/MiroFish/backend/app/services/suggestion_task_generator.py)

**职责**：从建议池条目生成待办任务。

### 6.8 干系人生成器
**类**：`StakeholderGenerator`
**文件**：[services/stakeholder_generator.py](file:///d:/BattleFish/MiroFish/backend/app/services/stakeholder_generator.py)

**职责**：基于项目信息 LLM 生成干系人草稿。

### 6.9 干系人历史服务
**类**：`StakeholderHistory`
**文件**：[services/stakeholder_history.py](file:///d:/BattleFish/MiroFish/backend/app/services/stakeholder_history.py)

**职责**：干系人属性变更历史聚合与查询。

### 6.10 仪表盘洞察生成器
**类**：`DashboardInsightGenerator`
**文件**：[services/dashboard_insight_generator.py](file:///d:/BattleFish/MiroFish/backend/app/services/dashboard_insight_generator.py)

**职责**：按时间范围生成仪表盘 LLM 智能洞察，结果缓存到 `dashboard_insight_cache` 表避免重复调用。

### 6.11 网络调研服务
**类**：`WebResearcher`
**文件**：[services/web_researcher.py](file:///d:/BattleFish/MiroFish/backend/app/services/web_researcher.py)

**职责**：客户背景调研，基于 Tavily API 网络搜索 + 网站爬取。

**相关模块**：
- [web_search_providers.py](file:///d:/BattleFish/MiroFish/backend/app/services/web_search_providers.py) — 搜索提供商抽象
- [website_scraper.py](file:///d:/BattleFish/MiroFish/backend/app/services/website_scraper.py) — 网站内容爬取
- [business_info_scraper.py](file:///d:/BattleFish/MiroFish/backend/app/services/business_info_scraper.py) — 工商信息爬取

### 6.12 LLM 客户端
**类**：`LLMClient`
**文件**：[utils/llm_client.py](file:///d:/BattleFish/MiroFish/backend/app/utils/llm_client.py)

**职责**：统一封装 LLM API 调用（OpenAI 兼容格式）。

**核心方法**：
- `chat(messages, temperature, max_tokens, response_format)` — 发送聊天请求
- `extract_json(...)` — 从 LLM 输出中提取 JSON
- 兼容性处理：支持 `reasoning_content` 字段（LongCat/MiniMax 等模型）

### 6.13 阶段交付物管理器
**类**：`StageDeliverableManager`（模块级函数）
**文件**：[services/stage_deliverable_manager.py](file:///d:/BattleFish/MiroFish/backend/app/services/stage_deliverable_manager.py)

**职责**：阶段交付物追踪与自动检查。

**核心能力**：
- `get_stage_deliverables(project_id)` — 获取项目当前阶段的交付物列表（含自动检查状态 + 手动勾选状态 + 附件）
- 5 个自动检查规则（基于结构化表计数，不读废弃文本字段）：
  - `_check_pain_points` — `ProjectStrategyItem(item_type='pain_point')` 计数 ≥ 1
  - `_check_customer_background` — `ProjectStrategyItem` 任意类型计数 ≥ 1
  - `_check_value_proposition` — `ProjectWhyContext` 计数 ≥ 1
  - `_check_sales_strategy` — `competitive_analysis` 非空 且 `ProjectWhyContext` 计数 ≥ 1
  - `_check_competitive_analysis` — `competitive_analysis` 非空
- 交付物附件管理（upload/download/delete）

### 6.14 业务洞察摘要生成器
**函数**：`_build_project_insight_summary(project_id)`
**文件**：[api/sales_twin/_helpers.py](file:///d:/BattleFish/MiroFish/backend/app/api/sales_twin/_helpers.py)

**职责**：从结构化表拼接 LLM 友好的业务洞察摘要文本，作为下游 LLM 消费者的**唯一数据源**。

**数据来源**：
- `ProjectStrategyItem` 4 类（industry_trend/pain_point/current_measure/strategic_initiative）
- `ProjectWhyContext` 3 类（why/why_now/why_us）
- `Project.competitive_analysis`

**输出格式**：按 6 段拼接（行业趋势 / 客户痛点 / 当前措施 / 战略举措 / 价值主张 / 竞争分析），每段无数据时跳过。

**下游消费者**（7 个服务/路由统一调用）：
- `action_recommender` — 行动推荐
- `blind_spot_detector` — 盲区扫描
- `fermentation_llm_simulator` — 发酵模拟
- `meeting_plan_generator` — 拜访预案
- `suggestion_task_generator` — 建议任务
- `sales_twin_tasks` — 任务优先级评估
- `sales_twin_analysis._build_fermentation_report_prompt` — 发酵报告

### 6.15 商机阶段时间线
**函数**：`get_project_stage_timeline(project_id)`
**文件**：[services/stage_deliverable_manager.py](file:///d:/BattleFish/MiroFish/backend/app/services/stage_deliverable_manager.py)

**职责**：从 `StateChangeLog` 推导项目各销售阶段的时间区间，返回时间线数据供前端 StageTimeline.vue 渲染。

**核心逻辑**：
- 查询 `attribute_name='sales_stage'` 的变更日志（按时间升序）
- 去重：映射后 `old_value == new_value` 的冗余记录过滤
- 构建时间区间：`(stage, started_at, ended_at)`
- 通过 `_normalize_stage()` 将旧版四阶段值（discovery/qualification/proposal/negotiation）映射到新版五阶段（suspect/identity/define/confirm），不修改原始日志数据

**旧版阶段映射表**（`_LEGACY_STAGE_MAPPING`）：
- `discovery` → `suspect`（线索）
- `qualification` → `identity`（商机确认）
- `proposal` → `define`（方案定义）
- `negotiation` → `confirm`（商务确认）

---

## 7. API 接口概览

### 7.1 接口总览

| 模块 | 前缀 | 接口数量 | 主要功能 |
|------|------|---------|---------|
| SalesTwin | `/api/sales-twin` | ~100 | 完整的 B2B 销售数字孪生功能（含 Agent 任务管理、盲区报告持久化、自进化引擎、系统设置） |
| Health | `/health` | 1 | 健康检查 |

### 7.2 接口响应格式

所有 API 统一返回格式：

```json
{
  "success": true,
  "data": { ... },
  "message": "操作成功"
}
```

错误响应：

```json
{
  "success": false,
  "error": "错误描述",
  "traceback": "..."  // 仅开发模式
}
```

---

## 8. 依赖关系与技术栈

### 8.1 后端依赖（Python）

**核心框架**：
- `flask>=3.0.0` — Web 框架
- `flask-cors>=6.0.0` — CORS 支持
- `flask-sqlalchemy>=3.0.0` — ORM
- `flask-apscheduler>=1.13.1` — 后台定时任务调度（Agent 任务系统）
- `apscheduler>=3.11.2` — APScheduler 核心
- `sqlalchemy>=2.0.0` — SQLAlchemy 核心

**AI 与 LLM**：
- `openai>=1.0.0` — OpenAI SDK（统一 LLM 调用格式，兼容 LongCat 等模型）

**工具库**：
- `python-dotenv>=1.0.0` — 环境变量加载
- `pydantic>=2.0.0` — 数据验证

> 历史变更：已移除 `zep-cloud`、`camel-oasis`、`camel-ai`、`PyMuPDF`、`chardet`、`charset-normalizer`、`alembic` 等未使用依赖。

### 8.2 前端依赖（JavaScript）

**核心框架**：
- `vue: ^3.5.24` — Vue 3
- `vue-router: ^4.6.3` — 路由
- `vue-i18n: ^11.3.0` — 国际化

**数据可视化**：
- `@antv/g6: ^5.1.1` — 图可视化引擎（干系人图谱）
- `d3: ^7.9.0` — D3.js（辅助数据可视化）

**工具库**：
- `axios: ^1.14.0` — HTTP 客户端

**开发工具**：
- `vite: ^7.2.4` — 构建工具
- `@vitejs/plugin-vue: ^6.0.1` — Vue 3 Vite 插件

### 8.3 外部服务依赖

| 服务 | 用途 | 必需性 |
|------|------|--------|
| LLM API（OpenAI 兼容） | 所有 AI 功能：本体生成、对话、解析、推荐等 | ✅ 必需 |
| Tavily API | 网络搜索（客户背景调研） | ⚪ 可选 |

---

## 9. 项目运行与部署

### 9.1 前置要求

| 工具 | 版本要求 | 说明 |
|------|---------|------|
| Node.js | 18+ | 前端运行环境 |
| Python | ≥3.11, ≤3.12 | 后端运行环境 |
| uv | 最新版 | Python 包管理器（推荐） |

### 9.2 环境变量配置

复制 `.env.example` 为 `.env` 并填入配置：

```env
# 必填
LLM_API_KEY=your_api_key
LLM_BASE_URL=https://api.longcat.chat/openai
LLM_MODEL_NAME=LongCat-2.0

# 可选
TAVILY_API_KEY=your_tavily_api_key
FLASK_PORT=5001
FLASK_DEBUG=True
DATABASE_URI=sqlite:///...
```

### 9.3 本地开发启动

#### 方式一：根目录一键启动（推荐）

```bash
# 安装所有依赖
npm run setup:all

# 同时启动前后端
npm run dev
```

#### 方式二：分别启动

```bash
# 后端（必须用 --no-reload 避免环境变量缓存问题）
cd backend
uv venv
uv pip install -r requirements.txt
python -m flask run --port 5001 --no-reload

# 前端（新开终端）
cd frontend
npm install
npm run dev
```

**服务地址**：
- 前端：`http://localhost:3000`
- 后端 API：`http://localhost:5001`
- 健康检查：`http://localhost:5001/health`

### 9.4 Docker 部署

```bash
# 1. 配置环境变量
cp .env.example .env

# 2. 启动容器
docker compose up -d
```

默认端口映射：
- 前端：3000
- 后端：5001

### 9.5 数据库初始化

首次启动时 Flask-SQLAlchemy 会自动创建数据表。

手动初始化：

```bash
cd backend
python scripts/init_db.py
```

### 9.6 常用脚本（backend/scripts/）

| 脚本 | 用途 |
|------|------|
| `init_db.py` | 初始化数据库 |
| `seed_data.py` | 填充示例数据 |
| `migrate_sales_stage_to_five.py` | 旧版四阶段 → 新版五阶段迁移（仅迁移 `project.sales_stage`，日志表在读取时映射） |
| `migrate_stage_deliverable.py` | 阶段交付物表迁移 |
| `migrate_stage_deliverable_attachments.py` | 阶段交付物附件字段迁移 |
| `migrate_add_certainty_fields.py` | 项目确定性字段迁移 |
| `migrate_stakeholder_fields.py` | 干系人字段迁移 |
| `migrate_dashboard_insight_cache.py` | 仪表盘洞察缓存表迁移 |
| `test_feedback.py` | 测试反馈解析 |
| `test_fermentation.py` | 测试发酵模拟 |
| `test_winrate.py` | 测试赢单率计算 |

---

## 附录

### A. 销售阶段定义（五阶段模型）

基于 SVS+Challenge Sales 框架，含 OM 里程碑：

| 阶段标识 | 阶段名称 | OM 里程碑 | 说明 |
|---------|---------|---------|------|
| suspect | 线索 | OM10 Bid/No-Go | 客户编排、商机识别 |
| identity | 商机确认 | OM20 Go/No-Go | 干系人识别、需求确认 |
| define | 方案定义 | OM30 策略评审 / OM40 投标批准 | 方案设计、投标策略 |
| confirm | 商务确认 | OM70 赢单/丢单 | 商务谈判、合同签署 |
| closed_won | 赢单 | OM70 Won | 已签约 |
| closed_lost | 丢单 | OM70 Lost | 已关闭 |

**旧版 → 新版映射**（保留供历史数据兼容）：
- `discovery` → `suspect`
- `qualification` → `identity`
- `proposal` → `define`
- `negotiation` → `confirm`
- `closed_won` / `closed_lost` 保留不变

### B. 项目角色（Buyer Role）

| 角色 | 英文 | 说明 |
|------|------|------|
| 推动者/行动派 | mobilizer | 积极推动项目，主动寻求变革 |
| 反对者/阻碍者 | blocker | 反对项目，制造障碍 |
| 向导/指导者 | guide | 提供内部信息和指导 |
| 支持者/拥护者 | champion | 强力支持者，内部倡导者 |
| 怀疑者 | skeptic | 持怀疑态度，需要说服 |
| 教练 | coach | 内部教练，提供帮助和建议 |

### C. 关系类型

| 类型 | 英文 | 说明 |
|------|------|------|
| 直接汇报 | direct_report | 上下级汇报关系 |
| 平级协作 | peer | 同级同事 |
| 盟友 | allies | 私交联盟，互相支持 |
| 利益冲突 | conflict | 存在利益冲突 |
| 导师 | mentor | 师徒/指导关系 |
| 朋友 | friend | 私人朋友关系 |

### D. 业务洞察 5 Tab 结构

业务洞察面板（BusinessInsightSection.vue）采用 5 Tab 统一布局，替代原 3 个独立面板（BusinessInsightSection + StrategyItemsPanel + WhyContextsPanel）：

| Tab | 名称 | 数据源 | AI 生成按钮 |
|-----|------|--------|------------|
| 1 | 行业趋势 | `ProjectStrategyItem(item_type='industry_trend')` 最多 3 条 | AI 深度分析（Tab 1-3 共享） |
| 2 | 痛点 | `ProjectStrategyItem(item_type='pain_point')` 最多 3 条 | 同上 |
| 3 | 当前措施 | `ProjectStrategyItem(item_type='current_measure')` 最多 3 条 | 同上 |
| 4 | 价值主张 | `ProjectWhyContext` 3 类（why/why_now/why_us），每类至多 1 条 | AI 生成（独立） |
| 5 | 竞争分析 | `Project.competitive_analysis` 文本字段 | AI 生成（独立） |

默认激活 Tab 1（行业趋势）。AI 生成按钮根据当前激活 Tab 动态切换显示。

---

## 10. Agent 后台任务调度系统

### 10.1 概述

白泽系统集成 Flask-APScheduler 后台任务调度器，自动执行商机健康扫描、客户情报拉取、销售模式学习评估等定时任务，解决"后台自动运行的 Agent 任务的结论存储到哪"的核心问题。

### 10.2 核心文件

| 文件 | 职责 |
|------|------|
| [app/__init__.py](file:///d:/BattleFish/MiroFish/backend/app/__init__.py) | `_init_scheduler()` 初始化调度器并注册 3 个定时任务 |
| [app/extensions.py](file:///d:/BattleFish/MiroFish/backend/app/extensions.py) | scheduler 单例（`scheduler = Scheduler()`） |
| [app/config.py](file:///d:/BattleFish/MiroFish/backend/app/config.py) | `SCHEDULER_API_ENABLED=False`、`SCHEDULER_TIMEZONE="Asia/Shanghai"` |
| [app/jobs/tasks.py](file:///d:/BattleFish/MiroFish/backend/app/jobs/tasks.py) | 3 个 cron job 函数 + AgentJobRun 生命周期管理 |
| [app/api/sales_twin/sales_twin_agent.py](file:///d:/BattleFish/MiroFish/backend/app/api/sales_twin/sales_twin_agent.py) | Agent 任务管理 API（列表/详情/调度/手动触发/运行历史） |
| [frontend/src/components/salesTwin/AgentJobManager.vue](file:///d:/BattleFish/MiroFish/frontend/src/components/salesTwin/AgentJobManager.vue) | 前端管理面板 |

### 10.3 定时任务清单

| 任务 ID | 函数 | 默认调度 | 职责 | 持久化目标 |
|---------|------|---------|------|-----------|
| `Daily_Health_Scan` | `daily_project_health_scan` | 每日 03:00 | 对所有活跃项目执行盲区扫描 | `BlindSpotReport`（scan_source='cron'）+ `AgentJobRun` |
| `Daily_News_Fetch` | `daily_customer_news_fetch` | 每日 04:00 | 拉取所有客户的最新情报 | `CustomerIntelSnapshot`（source='cron'）+ `AgentJobRun` |
| `Weekly_Learning_Eval` | `weekly_strategy_evaluation` | 每周一 05:00 | 评估学习模式、生成候选模式 | `AgentJobRun` |

### 10.4 AgentJobRun 生命周期

所有 cron job 函数遵循统一的生命周期模式，确保运行历史可追溯：

```python
def some_job():
    app = _get_app()
    with app.app_context():
        run = _start_job_run('Job_Id')  # 创建记录，默认 status='failed'
        try:
            # ... 业务逻辑 ...
            _finish_job_run(run, 'success', summary, items_processed=N, items_succeeded=M)
        except Exception as e:
            _finish_job_run(run, 'failed', error_message=str(e))
```

- `_start_job_run(job_id)` — 任务开始时创建 AgentJobRun 记录，默认 status='failed'（防止异常退出导致无结束记录）
- `_finish_job_run(run, status, ...)` — 任务结束时更新最终状态、摘要、统计

### 10.5 关键实现细节

- **App Context**：后台任务脱离 HTTP 请求，所有 db 操作必须包裹在 `with app.app_context():` 中
- **Debug 模式陷阱**：Flask-APScheduler 在 debug 模式下会重复启动调度器，通过 `scheduler._scheduler.start()` 绕过
- **手动触发**：`POST /agent/jobs/<job_id>/run` 立即触发指定任务，5 秒后前端自动刷新运行记录
- **前端展示**：AgentJobManager.vue 每个任务卡片下方显示"最近运行"区域，包含状态点（绿=success/红=failed/黄=partial）、时间戳、摘要
- **盲区报告持久化**：手动触发扫描（scan_source='manual'）和后台定时扫描（scan_source='cron'）都持久化到 BlindSpotReport 表，前端默认显示最新一份
- **前端自动加载**：进入项目时 `useSalesTwin.loadProjectData()` 自动调用 `getLatestBlindSpotReport` 从数据库读取最新报告，避免每次重新扫描

### 10.6 数据持久化架构

```
Agent 后台任务（cron/manual）
  ├─ BlindSpotReport      ← 盲区扫描结果（含 scan_source 标记）
  ├─ AgentJobRun          ← 任务运行历史（生命周期：_start_job_run → _finish_job_run）
  └─ CustomerIntelSnapshot ← 客户情报历史快照（替代不存在的 profile_overview 字段）

前端读取
  ├─ 进入项目 → getLatestBlindSpotReport() → 立即显示最新报告（无需重新扫描）
  ├─ Agent 任务页 → getAgentJobRuns() → 显示最近运行记录
  └─ 历史报告/快照 API → 支持时间线回溯
```

---

*文档生成时间：2026-07-22*
*基于 SalesTwin 项目代码库自动分析生成*
