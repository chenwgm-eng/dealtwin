# SalesTwin 自进化引擎 (Self-Evolution Engine) v1.0 开发说明书

> **目标受众**: AI 辅助编程系统 (Cursor/Trae/Windsurf 等)
> **架构核心**: 引入量化交易思维，将销售上下文向量化（因子化），通过“多级微转化信号”与“探索-利用 (E&E) 机制”实现策略迭代闭环。

---

## 1. 数据库模型扩展 (Backend)
**修改文件**: `backend/app/models/database.py`

在现有模型末尾新增以下 4 张表，并生成 Alembic/手动 SQLite 迁移脚本：

```python
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, Date

class AIRecommendationLog(db.Model):
    __tablename__ = 'ai_recommendation_log'
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('project.id'))
    rec_type = Column(String(50)) # next_best_action, meeting_plan, blindspot_fix
    source_service = Column(String(50)) # 产生此建议的模块
    rec_text = Column(Text) # 给用户的自然语言文本
    structured_payload = Column(Text) # JSON: 结构化动作指令(target, priority等)

    # --- 状态向量化 (Factor Vectors) ---
    momentum_factor = Column(Float, default=0.0) # 动量: 近14天推进速度
    coverage_factor = Column(Float, default=0.0) # 覆盖: 关键决策人触达率
    completeness_factor = Column(Float, default=0.0) # 交付物: 阶段交付物完成度
    pain_factor = Column(Float, default=0.0) # 痛点: 业务痛点严重度
    stage_at_generation = Column(String(50)) # 截面阶段

    # --- 探索与利用 (E&E) ---
    is_exploration = Column(Boolean, default=False) # True=随机/LLM泛化, False=基于高胜率Pattern
    confidence_score = Column(Float, default=0.0) # UCB 或 历史胜率得分
    pattern_id = Column(Integer, ForeignKey('learning_pattern.id'), nullable=True) # 如果是Exploitation，关联的模式

    created_at = Column(DateTime, default=datetime.utcnow)

class AIRecommendationOutcome(db.Model):
    __tablename__ = 'ai_recommendation_outcome'
    id = Column(Integer, primary_key=True)
    recommendation_id = Column(Integer, ForeignKey('ai_recommendation_log.id'), unique=True)

    # L1: 采纳反馈
    is_adopted = Column(Boolean, default=False)
    adopted_task_id = Column(Integer, ForeignKey('opportunity_task.id'), nullable=True)
    reject_reason = Column(String(100)) # 信息不足/时机不对/已做过等

    # L2: 执行反馈
    is_executed = Column(Boolean, default=False)
    execution_result = Column(String(50)) # success / neutral / failed

    # L3: 阶段反馈 (短期)
    triggered_stage_advance = Column(Boolean, default=False) # 7天内是否推进阶段

    # L4: 终局反馈 (长期)
    final_win = Column(Boolean, nullable=True) # True=赢单, False=丢单

    scored_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class LearningPattern(db.Model):
    __tablename__ = 'learning_pattern'
    id = Column(Integer, primary_key=True)
    pattern_type = Column(String(50)) # success_pattern / failure_pattern
    name = Column(String(200))
    trigger_conditions_json = Column(Text) # JSON: 触发此模式的因子阈值边界
    recommended_play = Column(Text) # 建议打法

    # 统计指标
    evidence_count = Column(Integer, default=0) # 样本数
    success_rate = Column(Float, default=0.0) # 综合成功率

    status = Column(String(20), default='candidate') # candidate / approved / deprecated
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

---

## 2. 后端服务层改造 (Backend Services)

### 2.1 因子提取服务 (新建 `services/factor_extractor.py`)
提取当前项目的横截面特征向量。
*   `momentum_factor`: 查询 `StateChangeLog` 过去 14 天的记录数归一化。
*   `coverage_factor`: 查询当前已建联 `stakeholder` 的 `decision_power` 总和占所有已知干系人权重的比例。

### 2.2 改造行动推荐器 (`services/action_recommender.py`)
引入基于 UCB (Upper Confidence Bound) 的探索与利用机制。

```python
# 伪代码逻辑注入
def recommend_actions(self, project_id):
    factors = FactorExtractor.extract(project_id)
    approved_patterns = LearningPattern.query.filter_by(status='approved').all()

    candidates = []
    # 1. 匹配历史高胜率模式 (Exploitation)
    for p in approved_patterns:
        if self._match_conditions(factors, p.trigger_conditions_json):
            score = self._calculate_ucb_score(p.success_rate, p.evidence_count, total_plays)
            candidates.append({"play": p.recommended_play, "is_exploration": False, "score": score})

    # 2. 调用 LLM 生成新策略 (Exploration) - 设定 20% 的硬性探索配额
    if random.random() < 0.20 or not candidates:
        llm_play = self._generate_llm_stakeholder_actions(project_id, factors)
        candidates.append({"play": llm_play, "is_exploration": True, "score": 0.5}) # 基础分

    # 选出 Top 3 并写入 AIRecommendationLog
    # 返回给前端
```

### 2.3 多级反馈追踪器 (新建 `services/outcome_tracker.py`)
监听系统事件（任务完成、阶段变更）。在任务标记完成 (`PUT /tasks/<id>`) 和阶段变更 (`PUT /projects/<id>/stage`) 的 API 路由中，异步或同步调用 `OutcomeTracker.update_l2_execution()` 和 `OutcomeTracker.update_l3_stage_advance()`。

---

## 3. API 路由层扩展 (Backend API)
**修改文件**: 建议在 `api/sales_twin/sales_twin_analysis.py` 中增加，或新建 `sales_twin_learning.py` 注册到蓝图。

1.  `POST /recommendations/<id>/adopt`
    *   接收 `{ "adopted": true, "reject_reason": null }` 或 `{ "adopted": false, "reject_reason": "时机不对" }`。
    *   如果是 adopted，自动创建一条 OpportunityTask，并把 `task.id` 回写到 `AIRecommendationOutcome.adopted_task_id`。
2.  `GET /learning/patterns`
    *   获取所有模式池，支持按 status 过滤。
3.  `POST /learning/patterns/<id>/approve` & `POST /learning/patterns/<id>/deprecate`
    *   人工审核接口。

---

## 4. 前端视图与组件改造 (Frontend)

### 4.1 建议卡片组件 (`src/components/salesTwin/ActionCard.vue` 假设有此组件)
当前 API `/projects/<id>/next-best-action` 返回数据中需包含 `recommendation_id`。
在卡片底部增加交互 UI：
```vue
<template>
  <div class="action-footer">
    <button @click="handleAdopt(true)" class="btn-primary">采纳为待办</button>
    <div class="reject-dropdown">
      <button @click="showReject = !showReject" class="btn-ghost">不适用</button>
      <ul v-if="showReject">
        <li @click="submitReject('信息不足')">信息不足</li>
        <li @click="submitReject('时机不对')">时机不对</li>
        <li @click="submitReject('不符合客户偏好')">不符合客户偏好</li>
      </ul>
    </div>
  </div>
</template>
```
调用新的 `/recommendations/<id>/adopt` 接口。

### 4.2 学习中心控制台 (`src/views/LearningCenter.vue` 新建)
供销售总监/系统管理员使用的“量化策略审核台”。
*   展示 `candidates` 状态的规则。
*   卡片显示：触发因子区间 (如 Momentum < 0.3 AND Coverage < 50%) -> 建议动作 -> 历史测试样本数 (Evidence: 12) -> 胜率 (Success Rate: 65%)。
*   操作按钮：`Approve (准入生产)` / `Deprecate (废弃)`。

### 4.3 `composables/useSalesTwin.js`
新增针对 Learning 相关的状态管理：
```javascript
const patterns = ref([]);
const fetchPatterns = async () => { ... }
const adoptRecommendation = async (recId, adoptData) => { ... }
```

---

## 5. 实施路径 (Execution Path)
1. **Model & Migration**: 先写 SQLAlchemy 模型并初始化表。
2. **API & Logger**: 改写 `ActionRecommender`，拦截它的输出，先落库 `AIRecommendationLog`，再吐给前端。
3. **Frontend Feedback**: 在前端增加采纳/拒绝按钮，跑通 L1（采纳层）反馈闭环。
4. **Tracker & L2/L3**: 在 Task Complete 和 Stage Change 接口埋点，跑通执行与结果反馈闭环。
5. **Pattern Extraction**: 最后实现周期性批处理脚本，定期汇总 Log 与 Outcome 生成 Pattern。
