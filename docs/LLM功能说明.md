# SalesTwin 系统 LLM 功能说明文档

> 本文档详细说明 SalesTwin（销售数字孪生）系统中所有涉及大语言模型（LLM）调用的功能，以及部分相关的不调用 LLM 的规则型功能（便于对比理解）。
>
> 每个功能按 **输入 → 逻辑 → 输出** 三段式描述，便于开发、测试与产品理解。

---

## 目录

- [一、LLM 配置总览](#一llm-配置总览)
- [二、功能分类索引](#二功能分类索引)
- [三、图谱与本体](#三图谱与本体)
  - [1. 本体生成（Ontology Generation）](#1-本体生成ontology-generation)
  - [2. 图谱构建（Build Graph）](#2-图谱构建build-graph)
- [四、销售分析与洞察](#四销售分析与洞察)
  - [3. 盲区扫描（Blind Spot Scan）](#3-盲区扫描blind-spot-scan)
  - [4. 下一步建议（Next Best Actions）](#4-下一步建议next-best-actions)
  - [5. 商机质量评分（Win Rate）](#5-商机质量评分win-rate纯规则)
  - [6. 阶段检查（Stage Check）](#6-阶段检查stage-check纯规则)
  - [7. Dashboard 智能洞察](#7-dashboard-智能洞察)
- [五、推演与模拟](#五推演与模拟)
  - [8. 闭门发酵（Closed-door Fermentation）](#8-闭门发酵closed-door-fermentation)
  - [9. 客户访谈（Customer Interview）](#9-客户访谈customer-interview)
  - [10. 发酵推演报告](#10-发酵推演报告fermentation-report)
- [六、反馈与行动](#六反馈与行动)
  - [11. 反馈解析（Feedback Parser）](#11-反馈解析feedback-parser)
  - [12. 建议池 → 待办生成](#12-建议池--待办生成suggestion-task-generator)
  - [13. 行动建议合并判断](#13-行动建议合并判断action-merge-decision)
- [七、任务管理](#七任务管理)
  - [14. 任务自动排序（Auto Sort Tasks）](#14-任务自动排序auto-sort-tasks)
- [八、客户与会议](#八客户与会议)
  - [15. 网络检索联系人（Web Research）](#15-网络检索联系人web-research)
  - [16. 拜访预案生成（Meeting Plan Generator）](#16-拜访预案生成meeting-plan-generator)
- [九、商机计划四件套](#九商机计划四件套)
  - [17-20. SVS 商机计划生成](#17-20-svs-商机计划生成customer-overview--value-proposition--competitive-analysis--business-pain-points)
  - [21. 文本排版优化（Reformat Text）](#21-文本排版优化reformat-text)
- [十、架构设计要点](#十架构设计要点)
- [十一、功能总览速查表](#十一功能总览速查表)

---

## 一、LLM 配置总览

| 配置项 | 值 / 位置 |
|---|---|
| **Base URL** | `https://api.longcat.chat/openai` |
| **Model** | `LongCat-2.0` |
| **API Key 来源** | 环境变量 `LLM_API_KEY` |
| **配置文件** | `backend/app/config.py` 第 50-52 行 |
| **客户端封装** | `backend/app/utils/llm_client.py` 的 `LLMClient` 类 |
| **调用方法** | `LLMClient.chat(messages, temperature, max_tokens)` 返回文本；`LLMClient.chat_json(...)` 返回 dict |
| **JSON 模式** | 使用 OpenAI `response_format={"type": "json_object"}`，并自动清理 markdown 代码块 + 正则兜底提取 |
| **CoT 处理** | 自动移除 `<think>...</think>` 残留（`llm_client.py` 第 88-92 行） |
| **配置校验** | `Config.validate()` 第 107-119 行强制校验 Base URL / Model 符合硬约束 |
| **延迟初始化** | 多数服务采用 `self._llm = None` + `_get_llm()` 模式，避免无 LLM 配置时启动失败 |

---

## 二、功能分类索引

SalesTwin 系统共包含 **21 个核心功能**，其中 **19 个调用 LLM**，**2 个为纯规则**（商机质量评分、阶段检查）。

| 分类 | 功能编号 | 功能名称 |
|---|---|---|
| 图谱与本体 | 1, 2 | 本体生成、图谱构建 |
| 销售分析与洞察 | 3, 4, 5, 6, 7 | 盲区扫描、下一步建议、商机质量评分、阶段检查、Dashboard 洞察 |
| 推演与模拟 | 8, 9, 10 | 闭门发酵、客户访谈、发酵报告 |
| 反馈与行动 | 11, 12, 13 | 反馈解析、建议池→待办、行动合并判断 |
| 任务管理 | 14 | 任务自动排序 |
| 客户与会议 | 15, 16 | 网络检索、拜访预案 |
| 商机计划 | 17-21 | 客户背景、价值主张、竞争分析、业务痛点、文本排版 |

---

## 三、图谱与本体

### 1. 本体生成（Ontology Generation）

根据上传文档和需求描述，让 LLM 生成知识图谱的本体定义（实体类型 + 关系类型）。

- **后端函数**：`OntologyGenerator.generate()`
- **文件位置**：[backend/app/services/ontology_generator.py](file:///d:/BattleFish/MiroFish/backend/app/services/ontology_generator.py#L306-L356) 第 306-356 行
- **API 路由**：`POST /api/graph/ontology/generate`（[backend/app/api/graph.py](file:///d:/BattleFish/MiroFish/backend/app/api/graph.py#L122) 第 122 行）
- **前端触发**：[frontend/src/api/graph.js](file:///d:/BattleFish/MiroFish/frontend/src/api/graph.js#L11) `generateOntology()`

#### 输入

| 输入类型 | 内容 |
|---|---|
| **用户输入** | `simulation_requirement`（必填，研究需求描述）、`files`（必填，PDF/MD/TXT 文件）、`project_name`、`additional_context`、`ontology_mode`（`social_simulation` 默认 / `b2b_sales`） |
| **数据库上下文** | 无（独立功能，不依赖项目数据） |
| **LLM Prompt** | 两套系统提示词：`SOCIAL_SIMULATION_ONTOLOGY_PROMPT`（社媒舆论模拟，需 10 个实体类型含 Person/Organization 兜底）和 `B2B_SALES_ONTOLOGY_PROMPT`（B2B 销售，必须含 6 个核心类型：StrategicInitiative/BusinessGoal/PainPoint/DecisionStage/Stakeholder/Organization） |
| **文本截断** | `MAX_TEXT_LENGTH_FOR_LLM = 50000`（5 万字） |

#### 逻辑

1. 校验 `simulation_requirement` 和 `files` 非空（硬约束）
2. 读取文件内容，拼接为文本上下文
3. 根据 `ontology_mode` 选择系统提示词
4. 调用 `LLMClient.chat_json(temperature=0.3, max_tokens=4096)`，单次调用
5. `_validate_and_process()` 后处理：校验类型、补齐兜底实体、PascalCase 命名规范化、Zep API 限制（最多 10 实体类型 + 10 边类型）、B2B 模式强制补 6 个核心类型

#### 输出

```json
{
  "entity_types": [...],
  "edge_types": [...],
  "analysis_summary": "..."
}
```

- **持久化**：保存到 `Project.ontology` 字段（JSON）和 `project.analysis_summary`，同时落盘到项目目录
- **前端展示**：在"商机图谱"页面显示生成的本体结构
- **错误处理**：异常直接抛出 500，含 traceback；无降级策略

---

### 2. 图谱构建（Build Graph）

基于本体定义和上传文件，通过 Zep Cloud API 异步构建知识图谱。

- **后端函数**：`GraphBuilderService.build_graph_async()`
- **文件位置**：[backend/app/services/graph_builder.py](file:///d:/BattleFish/MiroFish/backend/app/services/graph_builder.py)
- **API 路由**：`POST /api/graph/build`（[backend/app/api/graph.py](file:///d:/BattleFish/MiroFish/backend/app/api/graph.py#L263) 第 263 行）
- **前端触发**：[frontend/src/api/graph.js](file:///d:/BattleFish/MiroFish/frontend/src/api/graph.js#L29) `buildGraph()`

#### 输入

| 输入类型 | 内容 |
|---|---|
| **用户输入** | JSON：`project_id`（必填）、`graph_name`、`chunk_size`（默认 500）、`chunk_overlap`（默认 50）、`force` |
| **数据库上下文** | 项目的 `ontology` 字段、上传的文件内容 |
| **LLM Prompt** | 无（本系统代码不直接调用 LLM） |

#### 逻辑

1. **本系统代码不直接调用 LLM**
2. 通过 Zep Cloud API（`ZEP_API_KEY`）异步构建图谱
3. 文本分块 → 创建 Zep 图谱 → 设置本体 → 异步分块添加节点和边 → 更新任务状态
4. Zep 内部可能使用 LLM，但本项目代码不直接调

#### 输出

- 返回任务 ID，前端通过轮询获取进度
- 图谱数据存储在 Zep Cloud
- **错误处理**：异常写入 task_manager 状态为 FAILED，错误消息回显

---

## 四、销售分析与洞察

### 3. 盲区扫描（Blind Spot Scan）

基于挑战式销售方法论，让 LLM 识别项目中的销售盲区和风险。

- **后端函数**：`BlindSpotDetector.scan_project()`
- **文件位置**：[backend/app/services/blind_spot_detector.py](file:///d:/BattleFish/MiroFish/backend/app/services/blind_spot_detector.py#L35-L68) 第 35-68 行
- **API 路由**：`POST /api/sales-twin/projects/<id>/scan`（[backend/app/api/sales_twin/sales_twin_analysis.py](file:///d:/BattleFish/MiroFish/backend/app/api/sales_twin/sales_twin_analysis.py#L397-L405) 第 397-405 行）
- **前端触发**：[frontend/src/api/salesTwin.js](file:///d:/BattleFish/MiroFish/frontend/src/api/salesTwin.js#L117) `scanBlindSpots()`

#### 输入

| 输入类型 | 内容 |
|---|---|
| **用户输入** | URL 参数 `project_id` |
| **数据库上下文** | `_build_context()` 第 74-180 行构建：项目背景 + 干系人画像（含拜访次数/待办统计）+ 关系网络 + 最近 10 条反馈 + 最近 15 条状态变更日志 |
| **LLM Prompt** | 阶段感知（`STAGE_FOCUS` 字典，第 187-214 行定义 suspect/identity/define/confirm/closed_won/closed_lost 六阶段扫描重点）；基于挑战式销售方法论，要求 LLM 输出 2-5 个最关键风险 |

#### 逻辑

1. 从数据库读取项目完整上下文
2. 根据 `sales_stage` 选择对应的扫描重点
3. 调用 `LLMClient.chat_json(temperature=0.4, max_tokens=3000)`，单次调用
4. LLM 返回 2-5 个 finding，每个含 category/title/description/severity/stakeholder_name/recommendation

#### 输出

```json
{
  "overall_score": 0-100,
  "summary": "...",
  "findings": [
    {
      "category": "...",
      "title": "...",
      "description": "...",
      "severity": "high|medium|low",
      "stakeholder_name": "...",
      "recommendation": "..."
    }
  ]
}
```

- **持久化**：不写库，仅返回前端展示
- **错误处理**：LLM 失败时退回 `_rule_based_fallback()`（第 324-377 行），基于规则识别"高决策力零拜访/低支持度高决策力/沟通多无待办"等基础风险

---

### 4. 下一步建议（Next Best Actions）

基于项目状态和干系人画像，让 LLM 生成下一步行动建议。

- **后端函数**：`ActionRecommender.recommend_actions()`
- **文件位置**：[backend/app/services/action_recommender.py](file:///d:/BattleFish/MiroFish/backend/app/services/action_recommender.py#L48-L100) 第 48-100 行
- **API 路由**：`POST /api/sales-twin/projects/<id>/next-best-action`（[backend/app/api/sales_twin/sales_twin_analysis.py](file:///d:/BattleFish/MiroFish/backend/app/api/sales_twin/sales_twin_analysis.py#L409-L417) 第 409-417 行）
- **前端触发**：[frontend/src/api/salesTwin.js](file:///d:/BattleFish/MiroFish/frontend/src/api/salesTwin.js#L124) `nextBestAction()`

#### 输入

| 输入类型 | 内容 |
|---|---|
| **用户输入** | URL 参数 `project_id` |
| **数据库上下文** | 项目信息 + stakeholders + relationships + active_tasks（pending/in_progress）+ `BlindSpotDetector.scan_project()` 的 findings（盲区行动）+ 历史互动记录（`build_stakeholder_history_text`） |
| **LLM Prompt** | 阶段感知（`STAGE_ACTION_GUIDANCE` 第 399-419 行定义六阶段行动重心）；要求每个 action 含 target_stakeholder/title/description/reasoning/action_type/priority_score(60-95)/urgency/estimated_effort |

#### 逻辑

1. 调用盲区扫描获取 findings
2. 构建干系人历史互动记录
3. 调用 `LLMClient.chat_json(temperature=0.4, max_tokens=4000)`，单次调用
4. `_dedupe_against_tasks()` 第 102-163 行去重：与已有待办按 target + action_type 或标题 2-gram Jaccard 相似度 ≥0.6/0.8 过滤
5. 截取 top 10 返回

#### 输出

```json
{
  "actions": [...top10],
  "recommended_actions": [...],
  "total_actions": 10,
  "project_id": 1,
  "project_name": "..."
}
```

- **action_type**：`build_alliance` / `address_concerns` / `provide_material` / `seek_intelligence` / `leverage_champion`
- **持久化**：不写库，前端展示建议池
- **错误处理**：LLM 失败时退回 `_generate_stakeholder_actions()`（第 479-536 行）规则生成，基于 support_level/decision_power/urgency/buyer_role 阈值产出基础行动

---

### 5. 商机质量评分（Win Rate）（纯规则）

> **不调用 LLM**，纯规则计算。

- **后端函数**：`WinRateCalculator.calculate_win_rate()`
- **文件位置**：[backend/app/services/win_rate_calculator.py](file:///d:/BattleFish/MiroFish/backend/app/services/win_rate_calculator.py)
- **API 路由**：`GET /api/sales-twin/projects/<id>/win-rate`

#### 输入

- URL 参数 `project_id`

#### 逻辑

纯规则计算：加权支持度 + 网络得分 + 势头 + 角色覆盖度

#### 输出

商机赢单率评分及明细

---

### 6. 阶段检查（Stage Check）（纯规则）

> **不调用 LLM**，纯规则检查。

- **后端函数**：`check_stage_readiness()`
- **文件位置**：[backend/app/services/stage_deliverable_manager.py](file:///d:/BattleFish/MiroFish/backend/app/services/stage_deliverable_manager.py)
- **API 路由**：`POST /api/sales-twin/projects/<id>/stage-check`（[backend/app/api/sales_twin/sales_twin_stage.py](file:///d:/BattleFish/MiroFish/backend/app/api/sales_twin/sales_twin_stage.py#L213-L227) 第 213-227 行）

#### 输入

- URL 参数 `project_id`，可选 query 参数 `stage`

#### 逻辑

纯规则检查：基于 stakeholder position、task status、customer industry、feedback content 等进行 granular validation

#### 输出

```json
{
  "stage": "define",
  "completion_rate": 0.5,
  "total_items": 10,
  "completed_items": 5,
  "pending_items": [...],
  "exit_conditions_check": {...},
  "recommendation": "...",
  "can_advance": false,
  "ready": false
}
```

---

### 7. Dashboard 智能洞察

跨项目聚合数据，让 LLM 扮演销售策略顾问生成洞察。

- **后端函数**：`DashboardInsightGenerator.generate()`
- **文件位置**：[backend/app/services/dashboard_insight_generator.py](file:///d:/BattleFish/MiroFish/backend/app/services/dashboard_insight_generator.py#L26-L44) 第 26-44 行
- **API 路由**：
  - `GET /api/sales-twin/dashboard`（[backend/app/api/sales_twin/sales_twin_projects.py](file:///d:/BattleFish/MiroFish/backend/app/api/sales_twin/sales_twin_projects.py#L253-L295) 第 253-295 行）
  - `POST /api/sales-twin/dashboard/insights/refresh`（第 299-331 行）强制刷新
- **前端触发**：进入 Dashboard 页面时自动触发

#### 输入

| 输入类型 | 内容 |
|---|---|
| **用户输入** | 时间范围（start_date, end_date） |
| **数据库上下文** | `_build_context_text()` 第 46-108 行构建：时间范围 + 预计关单聚合（lead/opportunity 按 sales_stage 分组）+ 实际关单聚合（won/lost/win_rate）+ 重点关注事项（逾期待办 top5、今日到期、待识别干系人、红色触达联系人、待处理拜访预案）+ 近 30 天状态变更摘要 |
| **LLM Prompt** | 要求 LLM 扮演"资深 B2B 大客户销售策略顾问"，基于聚合数据从跨项目视角识别管线健康度/赢单能力/执行风险/机会捕捉/行动优先级 |

#### 逻辑

1. 检查 `DashboardInsightCache` 表是否命中缓存（按 start_date + end_date）
2. 未命中时调用 `LLMClient.chat_json(temperature=0.4, max_tokens=2000)`，单次调用
3. 使用 `_dashboard_insight_lock` 线程锁避免并发请求重复调用 LLM
4. LLM 失败时不写缓存（避免错误结果被缓存）

#### 输出

```json
{
  "time_range": {...},
  "expected_close": {...},
  "actual_close": {...},
  "attention_items": {...},
  "llm_insights": {
    "executive_summary": "...",
    "risk_alerts": [...],
    "opportunities": [...],
    "priority_actions": [...]
  }
}
```

- **持久化**：写入 `DashboardInsightCache` 表
- **错误处理**：失败时返回 `_fallback_insights()` 空洞察（`executive_summary: "智能洞察暂不可用"`）

---

## 五、推演与模拟

### 8. 闭门发酵（Closed-door Fermentation）

模拟信息在干系人网络中的扩散过程，每轮调一次 LLM。

- **后端函数**：`LLMFermentationSimulator.simulate()`
- **文件位置**：[backend/app/services/fermentation_llm_simulator.py](file:///d:/BattleFish/MiroFish/backend/app/services/fermentation_llm_simulator.py#L51-L176) 第 51-176 行
- **API 路由**：`POST /api/sales-twin/projects/<id>/fermentation`（[backend/app/api/sales_twin/sales_twin_analysis.py](file:///d:/BattleFish/MiroFish/backend/app/api/sales_twin/sales_twin_analysis.py#L445-L526) 第 445-526 行）
- **前端触发**：[frontend/src/api/salesTwin.js](file:///d:/BattleFish/MiroFish/frontend/src/api/salesTwin.js#L182) `simulateFermentation()`

#### 输入

| 输入类型 | 内容 |
|---|---|
| **用户输入** | JSON：`rounds`（扩散轮次，默认 3）、`mode`（narrative/numeric/hybrid，默认 narrative）、`related_task_ids`、`related_feedback_ids`、`related_materials` |
| **数据库上下文** | `_build_context()` 第 178-263 行构建：项目背景 + 干系人画像（含汇报对象、管理层级）+ 关系网络 + 历史反馈 + 关联待办 + 关联材料 |
| **LLM Prompt** | 阶段感知（`STAGE_FERMENTATION_FOCUS` 第 26-33 行定义六阶段发酵推演重点）；要求 LLM 模拟信息沿职责/汇报线/影响力/管理层级扩散 |

#### 逻辑

1. 构建完整上下文
2. **每轮调一次** `_simulate_round()` 第 265-400 行，`chat_json(temperature=0.6, max_tokens=2000)`
3. 总共 `rounds` 次 LLM 调用
4. 每轮输出 narrative（100-200字叙事）+ interactions(2-5条) + state_changes（含 stakeholder_id/old/new support_level/urgency/reason）
5. 累积 narrative_history，计算 trend

#### 输出

```json
{
  "project_id": 1,
  "project_name": "...",
  "rounds": 3,
  "mode": "narrative",
  "narrative_history": [...],
  "final_states": {...},
  "conclusion": "...",
  "trend": {
    "initial_avg": 5.0,
    "final_avg": 6.5,
    "change": 1.5
  },
  "input_sources": {...}
}
```

- **持久化**：不写库，返回前端展示
- **错误处理**：单轮失败时返回降级文本"（第N轮扩散异常：...）"，整体流程继续；状态不应用
- **混合模式**：mode=hybrid 时附加 numeric_supplement；mode=numeric 走 `FermentationSimulator`（纯规则，不调 LLM）

---

### 9. 客户访谈（Customer Interview）

模拟采访干系人，LLM 扮演干系人第一人称回答问题。

- **后端函数**：`LLMFermentationSimulator.interview()`
- **文件位置**：[backend/app/services/fermentation_llm_simulator.py](file:///d:/BattleFish/MiroFish/backend/app/services/fermentation_llm_simulator.py#L402-L487) 第 402-487 行
- **API 路由**：`POST /api/sales-twin/projects/<id>/fermentation/interview`（[backend/app/api/sales_twin/sales_twin_analysis.py](file:///d:/BattleFish/MiroFish/backend/app/api/sales_twin/sales_twin_analysis.py#L530-L544) 第 530-544 行）
- **前端触发**：[frontend/src/api/salesTwin.js](file:///d:/BattleFish/MiroFish/frontend/src/api/salesTwin.js#L197) `interviewStakeholder()`

#### 输入

| 输入类型 | 内容 |
|---|---|
| **用户输入** | JSON：`stakeholder_id`（必填）、`question`（必填）、`simulation_context`（发酵模拟历史） |
| **数据库上下文** | 干系人画像（name/position/buyer_role/support_level/decision_power/urgency/responsibilities/personal_agenda）+ 项目背景 |
| **LLM Prompt** | system_msg 强制要求"绝对禁止输出任何分析、推理、思考步骤、草稿、编号列表或元说明"；要求第一人称口语回答 150 字以内 |

#### 逻辑

1. 读取干系人画像和发酵历史
2. 调用 `LLMClient.chat(messages, temperature=0.7, max_tokens=1000)`，**非 JSON 模式**，单次调用
3. `_strip_cot()` 第 489-557 行剥离推理模型残留的"分析请求/起草回答/草稿N：/最终回答/数字标题分段"等 CoT 内容，4 级策略逐步尝试

#### 输出

```json
{
  "stakeholder_id": 1,
  "stakeholder_name": "...",
  "question": "...",
  "answer": "..."
}
```

- **持久化**：不写库
- **错误处理**：失败返回 `answer: "（采访失败：...）"`

---

### 10. 发酵推演报告（Fermentation Report）

基于发酵推演结果，让 LLM 生成结构化分析报告。

- **后端函数**：`generate_fermentation_report()`（路由函数内联）
- **文件位置**：[backend/app/api/sales_twin/sales_twin_analysis.py](file:///d:/BattleFish/MiroFish/backend/app/api/sales_twin/sales_twin_analysis.py#L670-L720) 第 670-720 行
- **API 路由**：`POST /api/sales-twin/projects/<id>/fermentation/report`
- **前端触发**：[frontend/src/api/salesTwin.js](file:///d:/BattleFish/MiroFish/frontend/src/api/salesTwin.js#L210) `generateFermentationReport()`

#### 输入

| 输入类型 | 内容 |
|---|---|
| **用户输入** | JSON：`fermentation_result`（前端缓存的发酵推演结果对象） |
| **数据库上下文** | 项目背景 + 干系人画像（JSON） |
| **LLM Prompt** | `_build_fermentation_report_prompt()` 第 548-636 行构造：包含推演结果摘要（rounds/trend/conclusion）+ 各轮扩散详情；要求 LLM 生成 5 章节结构化报告 |

#### 逻辑

1. 接收前端传入的 fermentation_result
2. 调用 `LLMClient.chat_json(temperature=0.5, max_tokens=3000)`，单次调用
3. LLM 生成 5 章节：推演概述/关键干系人态势分析/风险预警/机会洞察/行动建议

#### 输出

```json
{
  "id": "REF-YYYYMMDD-NNNN",
  "title": "...",
  "summary": "...",
  "sections": [
    {"title": "...", "content": "...", "bullets": [...]}
  ]
}
```

- **持久化**：不写库，返回前端展示
- **错误处理**：LLM 失败时调用 `_build_fermentation_report_fallback()` 第 644-667 行返回降级报告（含推演概述+行动建议两章节）

---

## 六、反馈与行动

### 11. 反馈解析（Feedback Parser）

解析用户提交的反馈文本，自动识别新干系人和已有干系人属性变化。

- **后端函数**：`FeedbackParserService.parse_feedback()`
- **文件位置**：[backend/app/services/feedback_parser.py](file:///d:/BattleFish/MiroFish/backend/app/services/feedback_parser.py#L30-L109) 第 30-109 行
- **API 路由**：`POST /api/sales-twin/projects/<id>/feedback`（[backend/app/api/sales_twin/sales_twin_feedback.py](file:///d:/BattleFish/MiroFish/backend/app/api/sales_twin/sales_twin_feedback.py#L6-L105) 第 6-105 行）
- **前端触发**：[frontend/src/api/salesTwin.js](file:///d:/BattleFish/MiroFish/frontend/src/api/salesTwin.js#L147) `submitFeedback()`，支持 JSON 和 multipart/form-data 两种提交方式

#### 输入

| 输入类型 | 内容 |
|---|---|
| **用户输入** | `feedback`（必填，文本）、`related_task_ids`、`related_meeting_plan_id`、`files`（附件，作为 LLM 解析输入上下文） |
| **数据库上下文** | 已有干系人列表（ID/姓名/职位/决策力/支持度/紧迫感/角色） |
| **LLM Prompt** | 要求 LLM 识别两类信息：A) 新干系人（含推断的 name/position/buyer_role/decision_power/support_level/urgency/responsibilities/personal_agenda）；B) 已有干系人属性变化（support_level/decision_power/urgency/buyer_role） |

#### 逻辑

1. 接收反馈文本和附件
2. 调用 `LLMClient.chat_json(temperature=0.2, max_tokens=2000)`，单次调用
3. 校验 `buyer_role` ∈ `VALID_BUYER_ROLES = {'mobilizer', 'blocker', 'guide', 'champion', 'skeptic', 'coach'}`
4. **单个事务原子化**：创建新 Stakeholder（status='pending'）、更新已有 Stakeholder 属性、创建 FeedbackRecord、StateChangeLog（change_source='feedback_parser'）、关联待办自动完成（包含"完成/已沟通/已送达/确认/同意"等关键词）

#### 输出

```json
{
  "project_id": 1,
  "feedback_id": 1,
  "original_feedback": "...",
  "parsed_updates": {...},
  "total_changes": 3,
  "summary": "...",
  "task_updates": [...],
  "state_logs": [...]
}
```

- **持久化**：写库（Stakeholder、FeedbackRecord、StateChangeLog、OpportunityTask）
- **事务边界**：单个事务原子化，失败全部回滚（第 56-92 行）
- **错误处理**：LLM 失败时退回 `_parse_with_rules()`（第 154-251 行）基于正则匹配关键词识别"支持度上升/下降/紧迫感/决策者"

---

### 12. 建议池 → 待办生成（Suggestion Task Generator）

将建议池中的条目批量转化为可执行的待办任务。

- **后端函数**：`SuggestionTaskGenerator.generate_tasks()`
- **文件位置**：[backend/app/services/suggestion_task_generator.py](file:///d:/BattleFish/MiroFish/backend/app/services/suggestion_task_generator.py#L32-L166) 第 32-166 行
- **API 路由**：`POST /api/sales-twin/projects/<id>/suggestions/generate-tasks`（[backend/app/api/sales_twin/sales_twin_tasks.py](file:///d:/BattleFish/MiroFish/backend/app/api/sales_twin/sales_twin_tasks.py#L587-L599) 第 587-599 行）
- **前端触发**：[frontend/src/api/salesTwin.js](file:///d:/BattleFish/MiroFish/frontend/src/api/salesTwin.js#L456) `generateTasksFromSuggestions()`

#### 输入

| 输入类型 | 内容 |
|---|---|
| **用户输入** | JSON：`suggestion_ids`（可选，None=全部未消费的建议） |
| **数据库上下文** | 项目完整状态（含 customer_background/value_proposition）+ 干系人画像 + 关系网络 + 每个干系人的历史互动记录 + 现有待办（防重复）+ 建议池内容（含来源标签 interview/report/manual） |
| **LLM Prompt** | 要求 LLM 转化为可执行待办，输出 title/description/task_type/priority/target_stakeholder/reasoning |

#### 逻辑

1. 读取指定建议（或全部未消费建议）
2. 构建项目完整上下文
3. 调用 `LLMClient.chat_json(temperature=0.4, max_tokens=4000)`，单次调用
4. 创建 `OpportunityTask`（source='recommended_action', source_action 含 source_type='suggestion_pool'）
5. 标记 `SuggestionPool.is_consumed=1`

#### 输出

```json
{
  "success": true,
  "generated_count": 5,
  "generated_tasks": [...],
  "consumed_suggestion_ids": [...]
}
```

- **持久化**：写库（OpportunityTask、SuggestionPool）
- **错误处理**：LLM 失败返回 `success: False, error: "LLM生成失败，请稍后重试"`，不抛异常

---

### 13. 行动建议合并判断（Action Merge Decision）

用户采纳建议池中的行动时，让 LLM 判断是合并到已有待办还是新建待办。

- **后端函数**：`_decide_action_merge_with_llm()`
- **文件位置**：[backend/app/api/sales_twin/sales_twin_tasks.py](file:///d:/BattleFish/MiroFish/backend/app/api/sales_twin/sales_twin_tasks.py#L226-L309) 第 226-309 行
- **API 路由**：间接调用，通过 `POST /api/sales-twin/projects/<id>/tasks/adopt-action`（第 373-464 行）
- **前端触发**：[frontend/src/api/salesTwin.js](file:///d:/BattleFish/MiroFish/frontend/src/api/salesTwin.js#L235) `adoptRecommendedAction()`

#### 输入

| 输入类型 | 内容 |
|---|---|
| **用户输入** | 用户点击"采纳"按钮 |
| **数据库上下文** | 新行动建议（title/target/action_type/priority_score/description/reasoning）+ 候选待办清单 |
| **LLM Prompt** | 要求 LLM 判断 merge 或 new，merge 时必须指定 merge_task_id |

#### 逻辑

1. 获取行动建议和候选待办清单
2. 调用 `LLMClient.chat_json(temperature=0.2, max_tokens=500)`，单次调用
3. 根据 LLM 判断：
   - merge：调用 `_merge_action_into_existing_task()` 合并
   - new：调用 `_create_task_from_action()` 新建
4. **action_type → task_type 映射**：`build_alliance→build_alliance`, `address_concerns→address_concerns`, `provide_material→provide_material`, `seek_intelligence→follow_up`, `leverage_champion→build_alliance`, `blind_spot→blind_spot`, `meeting→meeting`, `follow_up→follow_up`
5. **priority_score → priority 映射**：≥80→high, ≥50→medium, <50→low

#### 输出

- 返回 `(merge_decision: dict, merged_task_id: int|None)`
- **持久化**：写库（OpportunityTask 新建或更新）+ 记录 source_action 元数据
- **错误处理**：LLM 失败或异常时默认新建（第 306-308 行 `pass`）；merge_task_id 无效时降级为 new

---

## 七、任务管理

### 14. 任务自动排序（Auto Sort Tasks）

基于 SVS+Challenge Sales 五阶段模型，让 LLM 为待办重新评估优先级。

- **后端函数**：`auto_sort_tasks()`（路由函数内联实现 LLM 调用）
- **文件位置**：[backend/app/api/sales_twin/sales_twin_tasks.py](file:///d:/BattleFish/MiroFish/backend/app/api/sales_twin/sales_twin_tasks.py#L33-L146) 第 33-146 行
- **API 路由**：`POST /api/sales-twin/projects/<id>/tasks/auto-sort`
- **前端触发**：[frontend/src/api/salesTwin.js](file:///d:/BattleFish/MiroFish/frontend/src/api/salesTwin.js#L243) `autoSortTasks()`

#### 输入

| 输入类型 | 内容 |
|---|---|
| **用户输入** | URL 参数 `project_id` |
| **数据库上下文** | 项目上下文（customer_name/industry/sales_stage/business_pain_points/expected_close_date）+ 待办清单（id/title/task_type/priority/target_stakeholder/due_date/description） |
| **LLM Prompt** | 基于 SVS+Challenge Sales 五阶段模型（suspect/identity/define/confirm/closed_won/closed_lost）+ 挑战式销售方法论（Teaching/Tailoring/Taking Control），要求 LLM 为每个待办重新评估 priority(high/medium/low)、suggested_due_date、sort_weight(1-100)、reason |

#### 逻辑

1. 从数据库读取项目下所有 pending/in_progress 待办
2. 调用 `LLMClient.chat_json(temperature=0.3, max_tokens=2000)`，单次调用
3. **不直接修改数据库**，仅返回排序建议
4. 前端确认后调用 `POST /api/sales-twin/projects/<id>/tasks/apply-sort`（第 150-187 行）批量更新 task.priority 和 due_date

#### 输出

```json
{
  "success": true,
  "suggestions": [
    {
      "task_id": 1,
      "priority": "high",
      "suggested_due_date": "2026-08-01",
      "sort_weight": 95,
      "reason": "..."
    }
  ],
  "sales_stage": "define",
  "total": 10
}
```

- **持久化**：不直接写库，需用户确认后通过 apply-sort 接口写入
- **错误处理**：LLM 初始化失败返回 500；LLM 调用失败返回 500 `{error: "LLM评估失败: ..."}`；无降级策略

---

## 八、客户与会议

### 15. 网络检索联系人（Web Research）

> **重要说明**：基于 LLM 训练数据生成，**非实时联网**。

- **后端函数**：`WebResearcher.research_company()`
- **文件位置**：[backend/app/services/web_researcher.py](file:///d:/BattleFish/MiroFish/backend/app/services/web_researcher.py#L33-L117) 第 33-117 行
- **API 路由**：`POST /api/sales-twin/projects/<id>/research`（[backend/app/api/sales_twin/sales_twin_analysis.py](file:///d:/BattleFish/MiroFish/backend/app/api/sales_twin/sales_twin_analysis.py#L7-L39) 第 7-39 行）
- **前端触发**：[frontend/src/api/salesTwin.js](file:///d:/BattleFish/MiroFish/frontend/src/api/salesTwin.js#L371) `researchCompany()`

#### 输入

| 输入类型 | 内容 |
|---|---|
| **用户输入** | JSON：`extra_keywords`（可选） |
| **数据库上下文** | 项目的 `customer_name`（必填，否则 400）和 `industry` |
| **LLM Prompt** | 要求 LLM 扮演"资深 B2B 销售调研分析师"，基于训练数据知识生成 4 维度调研报告：组织概况/战略方向/组织架构（含 key_positions 决策岗位，**不编造人名**）/采购动态 |

#### 逻辑

1. 读取项目 customer_name 和 industry
2. 调用 `LLMClient.chat_json(temperature=0.3, max_tokens=3500)`，单次调用
3. LLM 基于训练数据生成结构化调研报告
4. 调研成功后自动调用 `StakeholderGenerator.generate_from_research()`（基于规则从 key_positions 创建占位干系人，不调 LLM）

#### 输出

```json
{
  "company_name": "...",
  "success": true,
  "report": "文本报告（最长 8000 字）",
  "raw_results": {...},
  "organization": {
    "departments": [...],
    "key_positions": [...],
    "decision_chain": [...]
  },
  "queries": [...],
  "stakeholder_generation": {...}
}
```

- **持久化**：不写库（占位干系人会写库）
- **错误处理**：失败返回 `success: False, error: "调研失败: ..."`；不抛异常
- **报告长度**：`MAX_REPORT_LEN = 8000`，超出截断

---

### 16. 拜访预案生成（Meeting Plan Generator）

基于干系人画像和历史互动，让 LLM 生成拜访预案。

- **后端函数**：`MeetingPlanGenerator.generate_plan()`
- **文件位置**：[backend/app/services/meeting_plan_generator.py](file:///d:/BattleFish/MiroFish/backend/app/services/meeting_plan_generator.py#L29-L143) 第 29-143 行
- **API 路由**：`POST /api/sales-twin/projects/<id>/meeting-plans`（[backend/app/api/sales_twin/sales_twin_meetings.py](file:///d:/BattleFish/MiroFish/backend/app/api/sales_twin/sales_twin_meetings.py#L16-L38) 第 16-38 行）
- **前端触发**：[frontend/src/api/salesTwin.js](file:///d:/BattleFish/MiroFish/frontend/src/api/salesTwin.js#L275) `createMeetingPlan()`

#### 输入

| 输入类型 | 内容 |
|---|---|
| **用户输入** | JSON：`stakeholder_id`（必填）、`meeting_purpose`、`meeting_type`（默认"初次拜访"）、`related_task_ids`、`related_materials`、`name`、`stakeholder_ids`（多干系人） |
| **数据库上下文** | 干系人画像 + 项目背景 + 历史互动记录（`build_stakeholder_history_text`）+ 关联待办 + 关联资料 |
| **LLM Prompt** | 主预案：要求输出 opening/key_topics/expected_objections/response_strategies/success_criteria/follow_up_actions/risk_warnings；标题：禁用"初次拜访"等套话，强调反映实际议题 |

#### 逻辑

1. **两次 LLM 调用**：
   - 第一次：`chat_json(temperature=0.4, max_tokens=3500)` 生成预案主体
   - 第二次：`_generate_plan_name()` 第 145-241 行 `chat(temperature=0.3, max_tokens=80)` 生成标题（仅当用户未提供 name 时）
2. forbidden_words 列表过滤"初次拜访/首次拜访/第N次拜访"等禁用词

#### 输出

```json
{
  "success": true,
  "plan_id": 1,
  "plan": {
    "id": 1,
    "name": "...",
    "stakeholder_id": 1,
    "stakeholder_ids": [...],
    "stakeholder_name": "...",
    "meeting_purpose": "...",
    "meeting_type": "...",
    "related_task_ids": [...],
    "related_materials": [...],
    "plan_content": {
      "opening": "...",
      "key_topics": [...],
      "expected_objections": [...],
      "response_strategies": [...],
      "success_criteria": [...],
      "follow_up_actions": [...],
      "risk_warnings": [...]
    },
    "status": "generated",
    "created_at": "..."
  }
}
```

- **持久化**：创建 `MeetingPlan` 记录，plan_content 字段存 JSON
- **错误处理**：LLM 失败时返回基础结构（opening/key_topics=[meeting_purpose]/notes="LLM生成失败，请人工补充"）；标题生成失败时用 `_fallback_name()`（优先用 key_topics，其次 meeting_purpose）

---

## 九、商机计划四件套

### 17-20. SVS 商机计划生成（Customer Overview / Value Proposition / Competitive Analysis / Business Pain Points）

这四个功能结构高度相似，统一描述。

- **后端函数**：`generate_customer_overview` / `generate_value_proposition` / `generate_competitive_analysis` / `generate_business_pain_points`
- **文件位置**：[backend/app/api/sales_twin/sales_twin_analysis.py](file:///d:/BattleFish/MiroFish/backend/app/api/sales_twin/sales_twin_analysis.py#L43-L315) 第 43-108 / 112-176 / 180-247 / 251-315 行
- **API 路由**：
  - `POST /api/sales-twin/projects/<id>/customer-overview`
  - `POST /api/sales-twin/projects/<id>/value-proposition`
  - `POST /api/sales-twin/projects/<id>/competitive-analysis`
  - `POST /api/sales-twin/projects/<id>/business-pain-points`
- **前端触发**：[frontend/src/api/salesTwin.js](file:///d:/BattleFish/MiroFish/frontend/src/api/salesTwin.js#L380) 第 380/389/398/407 行

#### 输入

| 输入类型 | 内容 |
|---|---|
| **用户输入** | JSON：`document_texts`（可选，上传文档文本列表） |
| **数据库上下文** | 通过 `_build_project_context()` 构建含项目信息+干系人+文档 |
| **LLM Prompt** | 统一通过 `build_svs_opportunity_prompt()` 构造（`backend/app/utils/prompt_templates.py`），传入 context + section_name + field_name + methodology + sections_spec + word_count |

#### 四个功能的 sections_spec 差异

| 功能 | sections_spec |
|---|---|
| **客户背景** | 行业重大变化/企业战略目标/当前措施与痛点（3-3-3 分析法） |
| **价值主张** | 为什么改变/为什么是现在/为什么是我们（Challenge Sales 重构逻辑） |
| **竞争分析** | SWOT 四象限 |
| **业务痛点** | 运营效率/组织决策/技术架构痛点 |

#### 逻辑

1. 每个路由独立调用 `LLMClient.chat_json(temperature=0.5, max_tokens=2000)`，单次调用
2. 字段长度限制 `MAX_TEXT_FIELD_LENGTH = 10000` 截断

#### 输出

```json
{
  "success": true,
  "<field_name>": "生成的内容",
  "project": {...}
}
```

- **持久化**：更新 Project 对应字段（customer_background/value_proposition/competitive_analysis/business_pain_points）+ updated_at
- **错误处理**：LLM 失败时调用 `_llm_error_response()` 返回 500 `{success: False, error: "生成失败: ..."}`；无降级策略

---

### 21. 文本排版优化（Reformat Text）

对已生成的文本字段进行排版优化，保留信息不增删内容。

- **后端函数**：`reformat_text()`（路由函数内联）
- **文件位置**：[backend/app/api/sales_twin/sales_twin_analysis.py](file:///d:/BattleFish/MiroFish/backend/app/api/sales_twin/sales_twin_analysis.py#L319-L393) 第 319-393 行
- **API 路由**：`POST /api/sales-twin/projects/<id>/reformat-text`
- **前端触发**：[frontend/src/api/salesTwin.js](file:///d:/BattleFish/MiroFish/frontend/src/api/salesTwin.js#L416) `reformatText()`

#### 输入

| 输入类型 | 内容 |
|---|---|
| **用户输入** | JSON：`field`（必填，限 `business_pain_points`/`value_proposition`/`competitive_analysis`/`customer_background` 之一） |
| **数据库上下文** | 读取 Project 对应字段的当前内容 |
| **LLM Prompt** | 要求"保留原文所有信息和要点，不增删实质内容"，识别逻辑分组用【】标记小节标题，散落要点用 • 转列表项，长段落拆短 |

#### 逻辑

1. 校验 field 参数合法性
2. 读取 Project 对应字段内容
3. 调用 `LLMClient.chat_json(temperature=0.3, max_tokens=2000)`，单次调用
4. LLM 返回排版后的文本

#### 输出

```json
{
  "success": true,
  "<field>": "排版后的内容",
  "project": {...}
}
```

- **持久化**：更新 Project 对应字段
- **错误处理**：LLM 失败或返回空时返回原文（不报错）；其他异常 500

---

## 十、架构设计要点

### 1. 统一 LLM 客户端

所有 LLM 调用都通过 `LLMClient`（[backend/app/utils/llm_client.py](file:///d:/BattleFish/MiroFish/backend/app/utils/llm_client.py)）封装，使用 OpenAI SDK 兼容格式，支持 `chat()` 和 `chat_json()` 两种模式。

### 2. 延迟初始化模式

除 `FeedbackParserService` 在 `__init__` 直接创建 LLMClient 外，其他服务普遍采用 `self._llm = None` + `_get_llm()` 模式，避免无 LLM 配置时启动失败。

### 3. JSON 解析健壮性

`chat_json()` 自动清理 markdown 代码块标记 + 正则提取 `{...}` 兜底；`_helpers.py` 中的 `_extract_json_object()` 提供类似能力供路由层使用。

### 4. CoT 残留处理

- `llm_client.py` 第 88-92 行自动移除 `<think>...</think>` 标签
- `fermentation_llm_simulator.py` 的 `_strip_cot()` 进一步处理 markdown 式 CoT（"分析请求/起草回答/草稿N：/最终回答"等）

### 5. 阶段感知设计

`ActionRecommender.STAGE_ACTION_GUIDANCE`、`BlindSpotDetector.STAGE_FOCUS`、`LLMFermentationSimulator.STAGE_FERMENTATION_FOCUS` 三个字典分别定义六阶段（suspect/identity/define/confirm/closed_won/closed_lost）的对应重点，未知阶段 fallback 到 suspect。

### 6. 降级策略分级

| 降级级别 | 功能 | 描述 |
|---|---|---|
| **强降级**（规则兜底） | 盲区扫描、下一步建议、反馈解析 | LLM 失败时退回规则算法 |
| **弱降级**（空结果/基础结构） | Dashboard 洞察、拜访预案、发酵报告、文本排版 | 返回基础结构或原文 |
| **无降级**（直接报错） | 本体生成、任务排序、SVS 四件套 | 直接抛 500 |

### 7. 缓存与并发控制

仅 Dashboard 洞察使用 `DashboardInsightCache` 表 + `_dashboard_insight_lock` 线程锁，避免并发请求重复调用 LLM。

### 8. 历史互动记录复用

[backend/app/services/stakeholder_history.py](file:///d:/BattleFish/MiroFish/backend/app/services/stakeholder_history.py) 的 `build_stakeholder_history_text()` 在下一步建议、拜访预案、建议池→待办三个功能中被复用，提供干系人级别的 state_logs + tasks + plans + feedbacks 聚合上下文。

### 9. 去重机制

- **下一步建议**：使用 `_dedupe_against_tasks()` 按 target + action_type 或标题 2-gram Jaccard 相似度过滤
- **建议池→待办**：在 prompt 中显式要求 LLM 避免与现有待办重复

### 10. 配置硬约束

`Config.validate()` 强制校验 Base URL 必须为 `https://api.longcat.chat/openai`、Model 必须为 `LongCat-2.0`，违反时返回错误（[config.py](file:///d:/BattleFish/MiroFish/backend/app/config.py#L107-L119) 第 107-119 行）。

---

## 十一、功能总览速查表

| # | 功能 | API 路由 | HTTP 方法 | LLM | Temperature | Max Tokens | 降级策略 |
|---|---|---|---|---|---|---|---|
| 1 | 本体生成 | `/api/graph/ontology/generate` | POST | ✅ | 0.3 | 4096 | 无（抛 500） |
| 2 | 图谱构建 | `/api/graph/build` | POST | ❌（Zep API） | - | - | - |
| 3 | 盲区扫描 | `/api/sales-twin/projects/<id>/scan` | POST | ✅ | 0.4 | 3000 | 规则兜底 |
| 4 | 下一步建议 | `/api/sales-twin/projects/<id>/next-best-action` | POST | ✅ | 0.4 | 4000 | 规则兜底 |
| 5 | 商机质量评分 | `/api/sales-twin/projects/<id>/win-rate` | GET | ❌（纯规则） | - | - | - |
| 6 | 阶段检查 | `/api/sales-twin/projects/<id>/stage-check` | POST | ❌（纯规则） | - | - | - |
| 7 | Dashboard 洞察 | `/api/sales-twin/dashboard` | GET | ✅ | 0.4 | 2000 | 空洞察+缓存跳过 |
| 8 | 闭门发酵 | `/api/sales-twin/projects/<id>/fermentation` | POST | ✅（每轮） | 0.6 | 2000 | 单轮降级文本 |
| 9 | 客户访谈 | `/api/sales-twin/projects/<id>/fermentation/interview` | POST | ✅ | 0.7 | 1000 | 返错误消息 |
| 10 | 发酵报告 | `/api/sales-twin/projects/<id>/fermentation/report` | POST | ✅ | 0.5 | 3000 | 降级报告 |
| 11 | 反馈解析 | `/api/sales-twin/projects/<id>/feedback` | POST | ✅ | 0.2 | 2000 | 规则兜底 |
| 12 | 建议池→待办 | `/api/sales-twin/projects/<id>/suggestions/generate-tasks` | POST | ✅ | 0.4 | 4000 | 返 success=False |
| 13 | 行动合并判断 | `/api/sales-twin/projects/<id>/tasks/adopt-action`（间接） | POST | ✅ | 0.2 | 500 | 默认新建 |
| 14 | 任务自动排序 | `/api/sales-twin/projects/<id>/tasks/auto-sort` | POST | ✅ | 0.3 | 2000 | 无（返 500） |
| 15 | 网络检索 | `/api/sales-twin/projects/<id>/research` | POST | ✅ | 0.3 | 3500 | 返 success=False |
| 16 | 拜访预案生成 | `/api/sales-twin/projects/<id>/meeting-plans` | POST | ✅×2 | 0.4 / 0.3 | 3500 / 80 | 基础结构+兜底标题 |
| 17 | 客户背景 | `/api/sales-twin/projects/<id>/customer-overview` | POST | ✅ | 0.5 | 2000 | 无（抛 500） |
| 18 | 价值主张 | `/api/sales-twin/projects/<id>/value-proposition` | POST | ✅ | 0.5 | 2000 | 无（抛 500） |
| 19 | 竞争分析 | `/api/sales-twin/projects/<id>/competitive-analysis` | POST | ✅ | 0.5 | 2000 | 无（抛 500） |
| 20 | 业务痛点 | `/api/sales-twin/projects/<id>/business-pain-points` | POST | ✅ | 0.5 | 2000 | 无（抛 500） |
| 21 | 文本排版 | `/api/sales-twin/projects/<id>/reformat-text` | POST | ✅ | 0.3 | 2000 | 返原文 |

---

> **文档版本**：v1.0
> **最后更新**：2026-07-20
> **维护说明**：本文档与代码同步维护，新增 LLM 功能或修改现有功能时请同步更新本文档。
