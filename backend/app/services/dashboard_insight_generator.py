"""
Dashboard 智能洞察生成器
基于系统全局上下文，由 LLM 单次调用生成跨项目视角的智能分析与行动建议
"""
import logging
from typing import Dict, Any, List

from app.utils.llm_client import LLMClient

logger = logging.getLogger(__name__)


class DashboardInsightGenerator:
    """Dashboard 智能洞察生成器"""

    def __init__(self):
        self.llm_client = None  # 延迟初始化
        self.last_error = False  # 上一次 generate 是否失败（调用方可据此跳过缓存写入）

    def _get_llm(self):
        """延迟初始化 LLM 客户端"""
        if self.llm_client is None:
            self.llm_client = LLMClient()
        return self.llm_client

    def generate(self, dashboard_data: Dict[str, Any]) -> Dict[str, Any]:
        """生成智能洞察

        流程：构造 prompt -> 调用 LLM -> 校验返回结果；任意步骤失败则降级返回空洞察。
        失败时将 self.last_error 置为 True，调用方可据此跳过缓存写入。
        """
        self.last_error = False
        try:
            prompt = self._build_prompt(dashboard_data)
            result = self._get_llm().chat_json(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                max_tokens=2000
            )
            return self._validate_insights(result)
        except Exception as e:
            logger.warning(f"Dashboard 智能洞察生成失败，使用降级返回: {e}")
            self.last_error = True
            return self._fallback_insights()

    def _build_context_text(self, dashboard_data: Dict[str, Any]) -> str:
        """构造结构化上下文文本（供 LLM 阅读的聚合数据）"""
        sections: List[str] = []

        # 1. 时间范围
        time_range = dashboard_data.get('time_range') or {}
        label = time_range.get('label', '本季度')
        start = time_range.get('start')
        end = time_range.get('end')
        sections.append(f"## 时间范围\n{label} {start} 至 {end}")

        # 2. 预计关单聚合
        ec = dashboard_data.get('expected_close') or {}
        lines = [
            f"- 线索(suspect)：{ec.get('lead_count', 0)} 个 / 金额 {ec.get('lead_amount', 0):.2f}",
            f"- 商机(identity+define+confirm)：{ec.get('opportunity_count', 0)} 个 / 金额 {ec.get('opportunity_amount', 0):.2f}",
        ]
        breakdown = ec.get('opportunity_breakdown') or {}
        for stage in ('identity', 'define', 'confirm'):
            item = breakdown.get(stage) or {}
            lines.append(
                f"  - {stage}：{item.get('count', 0)} 个 / 金额 {item.get('amount', 0):.2f}"
            )
        sections.append("## 预计关单聚合\n" + "\n".join(lines))

        # 3. 实际关单聚合
        ac = dashboard_data.get('actual_close') or {}
        win_rate = ac.get('win_rate')
        win_rate_text = f"{win_rate:.1f}%" if isinstance(win_rate, (int, float)) else "N/A"
        lines = [
            f"- 赢单(closed_won)：{ac.get('won_count', 0)} 个 / 金额 {ac.get('won_amount', 0):.2f}",
            f"- 丢单(closed_lost)：{ac.get('lost_count', 0)} 个 / 金额 {ac.get('lost_amount', 0):.2f}",
            f"- 赢单率：{win_rate_text}",
        ]
        sections.append("## 实际关单聚合\n" + "\n".join(lines))

        # 4. 重点关注事项
        ai = dashboard_data.get('attention_items') or {}
        lines = [
            f"- 逾期待办总数：{ai.get('overdue_count', 0)}",
            f"- 今日到期待办：{ai.get('today_due_count', 0)}",
            f"- 待识别干系人：{ai.get('pending_stakeholders_count', 0)}",
            f"- 红色触达状态联系人：{ai.get('red_contacts_count', 0)}",
            f"- 待处理/已生成拜访预案：{ai.get('pending_plans_count', 0)}",
        ]
        overdue_tasks = ai.get('overdue_tasks') or []
        if overdue_tasks:
            lines.append("\n逾期待办 Top 5：")
            for t in overdue_tasks:
                lines.append(
                    f"  - [{t.get('priority', 'medium')}] {t.get('title', '')} "
                    f"(项目: {t.get('project_name', '')}, 到期: {t.get('due_date', '')})"
                )
        sections.append("## 重点关注事项\n" + "\n".join(lines))

        # 5. 近30天状态变更摘要
        recent_changes = dashboard_data.get('recent_state_changes') or []
        if recent_changes:
            sections.append(
                "## 近30天状态变更摘要\n" + "\n".join(f"- {c}" for c in recent_changes)
            )

        return "\n\n".join(sections)

    def _build_prompt(self, dashboard_data: Dict[str, Any]) -> str:
        """构造完整 LLM prompt"""
        context = self._build_context_text(dashboard_data)
        return f"""你是一位资深B2B大客户销售策略顾问，精通挑战式销售（Challenger Sale）方法论。

请基于以下 Dashboard 聚合数据，从跨项目视角进行全局分析与判断，给出销售管理层面的洞察。

{context}

## 分析要求

基于上述聚合数据，识别当前销售管理中的关键风险、机会和优先行动。你可能需要关注（但不限于）以下方面：

- **管线健康度**：线索、商机、赢单/丢单的数量与金额配比是否合理？是否存在管线断层？
- **赢单能力**：赢单率是否健康？丢单金额是否过高？丢单原因是否有共性？
- **执行风险**：逾期待办是否集中在某些项目？今日到期任务是否过多？关键干系人识别是否滞后？
- **机会捕捉**：哪些商机金额大且阶段靠后？哪些线索值得加速推进？
- **行动优先级**：销售管理者本周应优先处理的 3-5 件事

## 关键原则

1. **基于数据说话**：每个洞察都必须引用具体的聚合数据
2. **跨项目视角**：不要聚焦单个项目，而是从全局销售管理角度分析
3. **聚焦最关键问题**：不要罗列所有微小问题，只输出真正影响销售目标的风险和机会
4. **可执行**：每个行动建议都要明确说明应该做什么、由谁负责、何时完成

## 输出格式（严格JSON）
{{
  "executive_summary": "一句话概括当前销售全局状况（30-80字）",
  "risk_alerts": [
    {{
      "level": "critical|high|medium",
      "category": "风险类别（如：管线断层、赢单能力、执行风险等）",
      "title": "风险标题（10-20字）",
      "description": "具体描述（50-120字，引用具体数据）",
      "impact": "潜在影响（30-80字）",
      "suggestion": "应对建议（30-80字）"
    }}
  ],
  "opportunities": [
    {{
      "title": "机会标题（10-20字）",
      "description": "机会描述（50-120字，引用具体数据）",
      "potential_value": "潜在价值（如：金额、数量等）",
      "action": "把握建议（30-80字）"
    }}
  ],
  "priority_actions": [
    {{
      "sequence": 1,
      "title": "行动标题（10-20字）",
      "description": "行动描述（50-100字）",
      "owner": "建议负责人/角色",
      "deadline": "建议完成时间（如：本周内、3天内等）"
    }}
  ]
}}

只输出JSON，不要输出其他内容。"""

    def _validate_insights(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """校验 LLM 返回结果，确保字段类型与白名单合规"""
        if not isinstance(result, dict):
            return self._fallback_insights()

        # executive_summary 必须是字符串
        summary = result.get('executive_summary')
        if not isinstance(summary, str) or not summary.strip():
            summary = '智能洞察暂不可用'

        # 提取并校验列表
        risk_alerts = self._clean_list(result.get('risk_alerts'))
        opportunities = self._clean_list(result.get('opportunities'))
        priority_actions = self._clean_list(result.get('priority_actions'))

        # risk_alerts：level 必须在白名单内
        valid_levels = {'critical', 'high', 'medium'}
        for r in risk_alerts:
            level = r.get('level')
            if level not in valid_levels:
                r['level'] = 'medium'

        # priority_actions：按 sequence 升序排序
        try:
            priority_actions.sort(
                key=lambda x: x.get('sequence', 999) if isinstance(x.get('sequence'), (int, float)) else 999
            )
        except Exception:
            pass

        return {
            'executive_summary': summary,
            'risk_alerts': risk_alerts,
            'opportunities': opportunities,
            'priority_actions': priority_actions,
        }

    @staticmethod
    def _clean_list(items) -> List[Dict[str, Any]]:
        """过滤非 dict 元素，返回干净的列表"""
        if not isinstance(items, list):
            return []
        return [it for it in items if isinstance(it, dict)]

    def _fallback_insights(self) -> Dict[str, Any]:
        """降级返回空洞察"""
        return {
            'executive_summary': '智能洞察暂不可用',
            'risk_alerts': [],
            'opportunities': [],
            'priority_actions': []
        }
