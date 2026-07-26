"""
建议池→待办事项生成器
从建议池中采纳的建议片段出发，结合项目完整状态和所有干系人历史互动记录，
用LLM生成具体、可执行的待办事项。
"""

import json
import logging
from typing import Dict, Any, List, Optional

from app import db
from app.models.database import (
    Project, Stakeholder, Relationship, OpportunityTask, SuggestionPool
)
from app.api.sales_twin._helpers import _build_project_insight_summary
from app.utils.llm_client import LLMClient
from app.services.stakeholder_history import build_stakeholder_history_text

logger = logging.getLogger(__name__)


class SuggestionTaskGenerator:
    """从建议池生成待办事项"""

    def __init__(self):
        self._llm = None

    def _get_llm(self):
        if self._llm is None:
            self._llm = LLMClient()
        return self._llm

    def generate_tasks(
        self,
        project_id: int,
        suggestion_ids: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """从建议池生成待办事项

        Args:
            project_id: 项目ID
            suggestion_ids: 指定建议ID列表，None=全部未消费的建议
        """
        project = Project.query.get_or_404(project_id)

        # 获取建议池内容
        if suggestion_ids:
            suggestions = SuggestionPool.query.filter(
                SuggestionPool.id.in_(suggestion_ids),
                SuggestionPool.project_id == project_id
            ).all()
        else:
            suggestions = SuggestionPool.query.filter_by(
                project_id=project_id,
                is_consumed=0
            ).order_by(SuggestionPool.created_at.desc()).all()

        if not suggestions:
            return {
                'success': False,
                'error': '建议池为空，没有可用的建议',
                'generated_tasks': []
            }

        # 构建LLM prompt
        prompt = self._build_prompt(project, suggestions)

        # 调用LLM生成待办
        try:
            llm = self._get_llm()
            result = llm.chat_json(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                max_tokens=4000
            )
        except Exception as e:
            logger.error(f"LLM从建议池生成待办失败: {e}")
            result = None

        if not result or not isinstance(result, dict):
            return {
                'success': False,
                'error': 'LLM生成失败，请稍后重试',
                'generated_tasks': []
            }

        # 解析并保存生成的待办
        raw_tasks = result.get('tasks', [])
        if not isinstance(raw_tasks, list):
            raw_tasks = []

        created_tasks = []
        suggestion_id_set = {s.id for s in suggestions}

        for item in raw_tasks:
            if not isinstance(item, dict):
                continue
            title = (item.get('title') or '').strip()
            if not title:
                continue

            # task_type 校验
            valid_types = {'blind_spot', 'address_concerns', 'build_alliance',
                           'provide_material', 'meeting', 'follow_up'}
            task_type = item.get('task_type', 'follow_up')
            if task_type not in valid_types:
                task_type = 'follow_up'

            # priority 校验
            valid_priorities = {'high', 'medium', 'low'}
            priority = item.get('priority', 'medium')
            if priority not in valid_priorities:
                priority = 'medium'

            # 查找目标干系人
            stakeholder_id = None
            target_name = (item.get('target_stakeholder') or '').strip()
            if target_name:
                sk = Stakeholder.query.filter_by(
                    project_id=project_id, name=target_name
                ).first()
                if sk:
                    stakeholder_id = sk.id

            # 记录来源元数据
            source_action = {
                'source_type': 'suggestion_pool',
                'suggestion_ids': list(suggestion_id_set),
                'target_stakeholder': target_name,
                'reasoning': item.get('reasoning', ''),
            }

            task = OpportunityTask(
                project_id=project_id,
                stakeholder_id=stakeholder_id,
                task_type=task_type,
                title=title,
                description=item.get('description', ''),
                priority=priority,
                status='pending',
                source='recommended_action',
                source_action=json.dumps(source_action, ensure_ascii=False)
            )
            db.session.add(task)
            created_tasks.append({
                'title': title,
                'description': item.get('description', ''),
                'task_type': task_type,
                'priority': priority,
                'target_stakeholder': target_name,
                'reasoning': item.get('reasoning', '')
            })

        # 标记建议为已消费
        for s in suggestions:
            s.is_consumed = 1

        db.session.commit()

        logger.info(f"从建议池生成了 {len(created_tasks)} 条待办")

        return {
            'success': True,
            'generated_count': len(created_tasks),
            'generated_tasks': created_tasks,
            'consumed_suggestion_ids': list(suggestion_id_set)
        }

    def _build_prompt(self, project: Project, suggestions: List[SuggestionPool]) -> str:
        """构建LLM提示词，包含项目完整状态、所有干系人历史记录、建议池内容"""

        # === 1. 项目背景 ===
        proj_parts = [f"项目名称: {project.name}"]
        if project.customer_name:
            proj_parts.append(f"客户名称: {project.customer_name}")
        if project.sales_stage:
            proj_parts.append(f"销售阶段: {project.sales_stage}")
        if project.industry:
            proj_parts.append(f"行业: {project.industry}")
        insight_summary = _build_project_insight_summary(project.id)
        if insight_summary:
            proj_parts.append(f"业务洞察: {insight_summary[:800]}")
        proj_context = '\n'.join(proj_parts)

        # === 2. 干系人画像 + 每人的历史互动记录 ===
        stakeholders = Stakeholder.query.filter_by(project_id=project.id).all()
        relationships = Relationship.query.filter_by(project_id=project.id).all()

        buyer_role_labels = {
            'mobilizer': '行动派/推动者', 'blocker': '反对者',
            'guide': '向导/内部顾问', 'champion': '支持者/倡导者',
            'skeptic': '怀疑者', 'coach': '教练/导师'
        }

        sk_lines = []
        history_lines = []
        for s in stakeholders:
            role_label = buyer_role_labels.get(s.buyer_role, s.buyer_role or '未分类')
            line = f"- 姓名: {s.name}"
            if s.position:
                line += f" | 职位: {s.position}"
            line += f" | 采购角色: {role_label}"
            line += f" | 决策力: {s.decision_power}/10 | 支持度: {s.support_level}/10 | 紧迫感: {s.urgency}/10"
            if s.responsibilities:
                line += f" | 职责: {s.responsibilities[:100]}"
            if s.personal_agenda:
                line += f" | 个人诉求: {s.personal_agenda[:100]}"
            sk_lines.append(line)

            # 聚合该干系人的历史互动记录
            try:
                history_text = build_stakeholder_history_text(
                    s.id, max_state_logs=5, max_tasks=6, max_plans=2, max_feedbacks=3
                )
                if history_text:
                    history_lines.append(f'#### {s.name}\n{history_text}')
            except Exception as e:
                logger.warning(f"获取干系人{s.id}历史记录失败: {e}")

        stakeholder_profile = '\n'.join(sk_lines) if sk_lines else '（暂无干系人）'

        # 关系网络
        sk_map = {s.id: s.name for s in stakeholders}
        rel_type_labels = {
            'direct_report': '直接汇报', 'peer': '同级', 'allies': '盟友',
            'conflict': '冲突', 'mentor': '导师', 'friend': '朋友'
        }
        rel_lines = []
        for r in relationships:
            src = sk_map.get(r.source_id, f'#{r.source_id}')
            tgt = sk_map.get(r.target_id, f'#{r.target_id}')
            rel = rel_type_labels.get(r.relationship_type, r.relationship_type)
            rel_lines.append(f"- {src} → {tgt}: {rel}")
        rel_profile = '\n'.join(rel_lines) if rel_lines else '（暂无已知关系）'

        # 历史互动记录
        history_section = ''
        if history_lines:
            history_section = f"""
## 干系人历史互动记录（避免重复已完成的工作）
{chr(10).join(history_lines)}
"""

        # === 3. 现有待办（避免重复） ===
        existing_tasks = OpportunityTask.query.filter_by(
            project_id=project.id
        ).filter(
            OpportunityTask.status.in_(['pending', 'in_progress'])
        ).order_by(OpportunityTask.created_at.desc()).limit(15).all()

        existing_tasks_str = ''
        if existing_tasks:
            existing_tasks_str = '\n## 现有待办事项（不要重复生成已有的待办）'
            for t in existing_tasks:
                existing_tasks_str += f'\n- [{t.priority}] {t.title}'

        # === 4. 建议池内容 ===
        source_labels = {
            'interview': '深度访谈',
            'report': '推演报告',
            'manual': '手动添加'
        }
        suggestion_lines = []
        for s in suggestions:
            source_label = source_labels.get(s.source, s.source)
            context_str = ''
            if s.source_context:
                try:
                    ctx = json.loads(s.source_context)
                    context_parts = []
                    if ctx.get('stakeholder_name'):
                        context_parts.append(f"干系人: {ctx['stakeholder_name']}")
                    if ctx.get('section_title'):
                        context_parts.append(f"章节: {ctx['section_title']}")
                    if context_parts:
                        context_str = f"（来源: {', '.join(context_parts)}）"
                except (json.JSONDecodeError, TypeError):
                    pass
            suggestion_lines.append(f"- [{source_label}]{context_str} {s.content}")

        suggestions_text = '\n'.join(suggestion_lines)

        return f"""你是一位资深B2B销售策略顾问。以下是从深度访谈对话和推演报告中采纳的一组建议片段。
请基于项目完整状态和干系人历史互动记录，将这些建议转化为具体、可执行的待办事项。

## 项目背景
{proj_context}

## 干系人画像
{stakeholder_profile}

## 干系人关系网络
{rel_profile}
{history_section}{existing_tasks_str}

## 建议池内容（用户从访谈/报告中采纳的建议）
{suggestions_text}

## 任务
将上述建议转化为具体、可执行的待办事项。要求：
1. **可执行**：每条待办明确说明"做什么、怎么做"
2. **关联干系人**：如果建议涉及特定干系人，必须指定 target_stakeholder（用干系人姓名）
3. **避免重复**：不要与"现有待办事项"重复，不要推荐历史互动记录中已完成的工作
4. **合并精简**：如果多条建议指向同一行动，合并为一条待办；如果某条建议过于笼统无法执行，跳过它
5. **合理分类**：根据行动性质选择 task_type（build_alliance/address_concerns/provide_material/meeting/follow_up/blind_spot）

## 输出格式（严格JSON）
{{
  "tasks": [
    {{
      "title": "待办标题（10-20字，行动导向）",
      "description": "具体执行内容（50-150字，说明做什么、怎么做）",
      "task_type": "build_alliance|address_concerns|provide_material|meeting|follow_up|blind_spot",
      "priority": "high|medium|low",
      "target_stakeholder": "干系人姓名（无关联则为空字符串）",
      "reasoning": "为什么生成这条待办（30-80字，基于建议内容和干系人状态）"
    }}
  ]
}}

只输出JSON，不要输出其他内容。"""
