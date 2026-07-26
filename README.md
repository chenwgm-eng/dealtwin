# DealTwin — B2B 商机数字孪生引擎

> 基于 SVS+Challenge Sales 销售框架的 AI 驱动商机管理系统（社区版）

DealTwin 是一个面向 B2B 销售的智能商机管理工具，融合 **SVS（Solution Value Selling）** 流程框架与 **Challenger Sales** 互动技能，通过 LLM 驱动的数字孪生推演，帮助销售人员在商机全生命周期中做出更精准的决策。

## 核心能力

- **商机全流程管理**：基于 SVS 五阶段（线索→商机确认→方案定义→商务确认→赢单/丢单）+ OM10-OM70 里程碑决策
- **干系人图谱**：可视化干系人关系网络、决策链、影响力路径
- **AI 盲区扫描**：自动识别商机中的盲点与风险
- **行动建议引擎**：基于商机状态生成下一步最佳行动
- **闭门发酵推演**：LLM 驱动的多轮沙盘推演，模拟各方反应
- **Challenger 商业指导**：7 步商业话术生成 + 社交风格定制
- **拜访预案与反馈解析**：结构化拜访准备 + 自然语言反馈自动解析
- **阶段交付物追踪**：每个阶段的交付物清单与完成度跟踪
- **个人仪表盘**：商机概览、AI 智能洞察、待办关注
- **Agent 定时任务**：后台自动盲区扫描、策略复盘

## 技术栈

- **后端**：Flask + SQLAlchemy + APScheduler + OpenAI SDK
- **前端**：Vue 3 + Vite + Vue Router + Vue I18n + AntV G6
- **数据库**：SQLite（默认，零配置）/ PostgreSQL / MySQL（可配置）
- **LLM**：兼容 OpenAI API 格式的任意模型

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+
- uv（Python 包管理器）

### 安装

```bash
# 克隆仓库
git clone https://github.com/chenwgm-eng/dealtwin.git
cd dealtwin

# 安装后端依赖
cd backend
uv sync
cd ..

# 安装前端依赖
cd frontend
npm install
cd ..

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入 LLM_API_KEY
```

### 启动

```bash
# 在项目根目录执行
npm run dev
```

这会同时启动后端（Flask :5001）和前端（Vite :3000）。

浏览器访问 http://localhost:3000 即可使用。

### 生产构建

```bash
cd frontend
npm run build
# 构建产物在 frontend/dist/
```

## 项目结构

```
dealtwin/
├── backend/
│   ├── app/
│   │   ├── api/sales_twin/    # API 路由（按业务域拆分）
│   │   ├── models/            # 数据模型
│   │   ├── services/          # 业务服务（LLM、推演、检测等）
│   │   ├── jobs/              # 后台定时任务
│   │   └── utils/             # 工具函数
│   ├── scripts/               # 数据库迁移脚本
│   ├── tests/                 # 测试
│   └── run.py                 # 启动入口
├── frontend/
│   └── src/
│       ├── api/               # API 调用
│       ├── components/         # Vue 组件
│       ├── composables/        # 组合式函数
│       ├── views/              # 页面视图
│       └── i18n/               # 国际化
├── locales/                   # 中英文语言包
├── docs/                      # 文档
└── .env.example               # 环境变量模板
```

## 社区版 vs 商业版

DealTwin 采用 **open-core** 架构：

| 特性 | 社区版（本仓库） | 商业版（dealtwin-business） |
|------|------------------|---------------------------|
| 商机全流程管理 | ✅ | ✅ |
| 干系人图谱与拜访 | ✅ | ✅ |
| AI 全套能力 | ✅ | ✅ |
| 个人仪表盘 | ✅ | ✅ |
| 客户关系管理 | ❌ | ✅ |
| 用户认证与 RBAC | ❌ | ✅ |
| 团队数据隔离 | ❌ | ✅ |
| PostgreSQL/MySQL | ❌ | ✅ |

商业版基于本仓库扩展，通过 `@edition` 注册表注入客户管理、认证、RBAC 等扩展功能。

## 许可证

[GNU AGPL-3.0](LICENSE)

## 致谢

DealTwin 基于以下销售方法论设计：
- **SVS (Solution Value Selling)**：提供商机推进的流程框架
- **Challenger Sales**：提供客户互动的技能框架