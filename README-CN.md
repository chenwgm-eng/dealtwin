# DealTwin — B2B 商机数字孪生引擎

> 基于 SVS+Challenge Sales 销售框架的 AI 驱动商机管理系统

DealTwin 是一个面向 B2B 销售的智能商机管理工具，融合 **SVS（Solution Value Selling）** 流程框架与 **Challenger Sales** 互动技能，通过 LLM 驱动的数字孪生推演，帮助销售人员在商机全生命周期中做出更精准的决策。

## 两个版本

| | 社区版（本仓库） | 商业版（DealTwin Business） |
|---|---|---|
| 定位 | 个人销售工具 | 企业级 AI CRM |
| AI 能力 | **基础 AI**（部分能力） | **完整 AI**（全能力 + 高级 AI） |
| 客户关系管理 | ❌ | ✅ |
| 用户认证与 RBAC | ❌ | ✅ |
| 团队数据隔离 | ❌ | ✅ |
| 数据库 | SQLite | SQLite / PostgreSQL / MySQL |
| 许可证 | AGPL-3.0（开源） | 私有商业许可证 |

---

## 社区版能力（本仓库）

社区版面向个人销售，提供商机全流程管理与**基础 AI** 辅助：

### 商机管理

- **商机全流程**：SVS 五阶段（线索→商机确认→方案定义→商务确认→赢单/丢单）+ OM10-OM70 里程碑决策
- **干系人图谱**：可视化关系网络、决策链、影响力路径
- **阶段交付物追踪**：每个阶段的交付物清单与完成度跟踪
- **个人仪表盘**：商机概览、待办关注

### 基础 AI 能力

- **盲区扫描**：自动识别商机中的盲点与风险
- **行动建议**：基于商机状态生成下一步最佳行动
- **Challenger 话术**：7 步商业指导话术生成 + 社交风格定制
- **拜访预案**：结构化拜访准备
- **反馈解析**：自然语言拜访记录自动解析为结构化数据
- **仪表盘洞察**：AI 生成的销售洞察摘要

---

## 商业版 AI 能力（DealTwin Business）

商业版在社区版基础上，提供**完整 AI 能力**与**高级 AI 功能**：

### 完整 AI（社区版基础 AI 的增强版）

- **深度盲区扫描**：多维度交叉分析（组织/竞争/时机/预算），识别深层风险
- **智能行动编排**：基于干系人社交风格 + 采购角色的个性化行动策略推荐
- **Challenger 全套**：7 步话术 + Tailoring 定制 + Powerful Ask 生成 + 验证因子分析
- **发酵推演**：LLM 驱动的多轮闭门沙盘，模拟客户内部各方反应与博弈
- **智能拜访预案**：基于干系人议程 + 历史互动 + 竞争态势的综合预案

### 高级 AI（商业版独有）

- **客户智能画像**：自动抓取客户工商信息 + 行业动态 + 组织架构，AI 生成客户全景画像
- **组织架构 AI 分析**：自动解析客户汇报关系树，识别关键决策节点与影响力路径
- **学习模式自动归纳**：从赢单/丢单记录中自动提取成功模式与失败模式，沉淀团队销售知识库
- **跨商机策略推荐**：基于历史商机数据 + 学习模式库，为新商机推荐最优策略
- **团队协同 AI 建议**：分析团队商机分布与进展，AI 生成资源调配与协作建议
- **竞争情报 AI**：自动监控竞争对手动态，关联到相关商机进行风险预警
- **商机健康度 AI 评分**：多维度 AI 综合评估商机赢单概率与风险等级

### 企业级功能

- **客户关系管理**：客户树形管理、联系人、组织架构图谱、工商信息自动抓取
- **JWT 认证**：登录/登出 + token 管理
- **RBAC 三角色**：admin（管理员）/ manager（经理）/ sales（销售）
- **数据隔离**：基于角色自动过滤可见数据（admin 全部 / manager 团队 / sales 个人）
- **用户管理**：创建/禁用用户、角色分配、团队归属

---

## 技术栈

- **后端**：Flask + SQLAlchemy + APScheduler + OpenAI SDK
- **前端**：Vue 3 + Vite + Vue Router + Vue I18n + AntV G6
- **数据库**：SQLite（社区版默认）/ PostgreSQL / MySQL（商业版）
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

## 扩展机制

DealTwin 采用 **open-core** 架构，通过 `@edition` 注册表实现社区版与商业版的代码分离：

- 社区版提供 `@edition` 存根（`set_edition_provider` / `has_customer_module` / `has_auth`）
- 商业版启动时注入 `BusinessEditionProvider`，启用客户管理、认证、RBAC 等扩展
- 数据隔离通过 `scope provider` 实现（社区版 provider=None 零行为变化）

## 许可证

社区版采用 [GNU AGPL-3.0](LICENSE) 开源许可证。

商业版（DealTwin Business）采用私有商业许可证，不开源。

## 致谢

DealTwin 基于以下销售方法论设计：
- **SVS (Solution Value Selling)**：提供商机推进的流程框架
- **Challenger Sales**：提供客户互动的技能框架
## 联系方式

邮箱：chenwgm@126.com
