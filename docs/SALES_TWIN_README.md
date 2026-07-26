# B2B 销售数字孪生 - 快速启动指南

## 系统概述

B2B销售数字孪生系统将客户方干系人智能体化，内置政治博弈与社会关系模拟，解决ToB销售的核心痛点。

## 功能模块

### 核心功能

1. **项目管理** - 销售项目全生命周期管理
2. **干系人图谱** - 客户方干系人关系网络可视化
3. **盲区扫描** - 自动识别缺失关键角色和关系网络问题
4. **策略顾问** - AI生成下一步行动建议和拜访简报
5. **反馈无感更新** - 自然语言会议纪要自动解析更新
6. **状态时间轴** - 干系人态度变化历史追踪
7. **赢单率预测** - 多维度综合评估赢单概率
8. **闭门发酵模拟** - 会后社会影响传播模拟

## 技术架构

```
┌─────────────────────────────────────────┐
│           前端 (Vue 3 + D3.js)         │
│  项目管理 | 图谱可视化 | 策略建议         │
└───────────────────┬─────────────────────┘
                    │ REST API
┌───────────────────▼─────────────────────┐
│        后端 (Flask + SQLAlchemy)        │
│  项目 | 干系人 | 关系 | 盲区检测          │
│  行动推荐 | 反馈解析 | 赢单率 | 发酵模拟   │
└───────────────────┬─────────────────────┘
                    │
┌───────────────────▼─────────────────────┐
│          数据库 (SQLite)                  │
│  Project / Stakeholder / Relationship      │
│  StateChangeLog / MeetingSimulation      │
└─────────────────────────────────────────┘
```

## 快速启动

### 1. 启动后端服务

```bash
cd backend

# 安装依赖
pip install -r requirements.txt

# 初始化数据库
python scripts/init_db.py

# 启动服务
python -m flask run --port 5001
```

后端服务将在 http://localhost:5001

### 2. 启动前端服务

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端服务将在 http://localhost:3000

### 3. 访问系统

打开浏览器访问 http://localhost:3000，点击顶部导航栏的"🎯 销售数字孪生"进入系统，或直接访问 http://localhost:3000/sales-twin

## API 接口列表

### 项目管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/sales-twin/projects | 获取项目列表 |
| GET | /api/sales-twin/projects/:id | 获取项目详情 |
| POST | /api/sales-twin/projects | 创建项目 |
| PUT | /api/sales-twin/projects/:id | 更新项目 |
| DELETE | /api/sales-twin/projects/:id | 删除项目 |

### 干系人管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/sales-twin/projects/:id/stakeholders | 获取干系人列表 |
| POST | /api/sales-twin/projects/:id/stakeholders | 添加干系人 |
| PUT | /api/sales-twin/projects/:id/stakeholders/:sid | 更新干系人 |
| DELETE | /api/sales-twin/projects/:id/stakeholders/:sid | 删除干系人 |

### 关系管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/sales-twin/projects/:id/relationships | 获取关系列表 |
| POST | /api/sales-twin/projects/:id/relationships | 创建关系 |
| PUT | /api/sales-twin/projects/:id/relationships/:rid | 更新关系 |
| DELETE | /api/sales-twin/projects/:id/relationships/:rid | 删除关系 |

### 核心分析服务

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/sales-twin/projects/:id/scan | 盲区扫描 |
| POST | /api/sales-twin/projects/:id/next-best-action | 下一步行动建议 |
| POST | /api/sales-twin/projects/:id/action-brief/:sid | 单人拜访简报 |
| POST | /api/sales-twin/projects/:id/feedback | 提交反馈并解析 |
| GET | /api/sales-twin/projects/:id/state-logs | 状态变更日志 |
| GET | /api/sales-twin/projects/:id/win-rate | 赢单率预测 |
| POST | /api/sales-twin/projects/:id/fermentation | 闭门发酵模拟 |

## 核心算法说明

### 赢单率计算 (Win Rate)

综合评分权重：
- 加权支持度: 40% (决策力加权平均支持度)
- 网络得分: 25% (关系连通性+联盟比例)
- 势头得分: 15% (近期态度变化趋势)
- 角色覆盖: 20% (5类关键角色覆盖度)

### 闭门发酵模拟

基于社会影响传播模型：
- 关系类型影响力系数: 盟友(0.8) > 上下级(0.7) > 导师(0.6) > 朋友(0.5) > 中立(0.3) > 竞争(0.1) > 冲突(-0.5)
- Mobilizer/Blocker 角色放大系数: 1.5x
- 每日迭代一次态度传播

### 反馈解析引擎

双层解析策略：
1. 规则引擎优先（快速匹配常见模式）
2. LLM 深度解析（规则未匹配时降级）

支持自动更新属性：支持度、决策力、紧迫感、角色

## 数据模型

### 关键枚举值

**buyer_role (干系人角色)：
- mobilizer: 推动者
- blocker: 阻碍者
- guide: 引导者
- champion: 冠军支持者
- skeptic: 怀疑者
- coach: 教练

**relationship_type (关系类型)：
- direct_report: 上下级
- peer: 平级
- allies: 盟友
- conflict: 冲突
- mentor: 导师
- friend: 朋友

**sales_stage (销售阶段)：
- discovery: 需求发现
- proposal: 方案设计
- negotiation: 商务谈判
- closing: 赢单阶段

## 测试

运行集成测试：

```bash
cd backend
python scripts/integration_test.py
```

## 目录结构

```
backend/
├── app/
│   ├── api/              # API路由
│   │   └── sales_twin.py    # 销售数字孪生API
│   ├── services/         # 业务服务
│   │   ├── blind_spot_detector.py   # 盲区检测器
│   │   ├── action_recommender.py    # 行动推荐器
│   │   ├── feedback_parser.py      # 反馈解析器
│   │   ├── win_rate_calculator.py   # 赢单率计算器
│   │   └── fermentation_simulator.py # 发酵模拟器
│   └── models/
│       └── database.py     # 数据模型
├── scripts/
│   ├── init_db.py         # 数据库初始化
│   └── integration_test.py # 集成测试
└── instance/
    └── sales_twin.db       # SQLite数据库

frontend/
├── src/
│   ├── views/
│   │   └── SalesTwin.vue   # 销售数字孪生主页面
│   ├── api/
│   │   └── salesTwin.js    # API封装
│   └── router/             # 路由配置
```
