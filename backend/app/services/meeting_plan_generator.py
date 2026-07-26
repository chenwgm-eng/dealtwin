"""
拜访前预案生成器
基于目标干系人画像 + 项目上下文 + 关联待办/资料，用LLM生成结构化拜访预案
"""

import json
import logging
from typing import Dict, Any, List, Optional

from app import db
from app.models.database import Project, Stakeholder, OpportunityTask, MeetingPlan, FeedbackRecord
from app.api.sales_twin._helpers import _build_project_insight_summary
from app.utils.llm_client import LLMClient
from app.services.stakeholder_history import build_stakeholder_history_text

logger = logging.getLogger(__name__)


class MeetingPlanGenerator:
    """拜访前预案生成器"""

    def __init__(self):
        self._llm = None

    def _get_llm(self):
        if self._llm is None:
            self._llm = LLMClient()
        return self._llm

    def generate_plan(
        self,
        project_id: int,
        stakeholder_id: int,
        meeting_purpose: str,
        meeting_type: str = 'first_visit',
        related_task_ids: List[int] = None,
        related_materials: List[Dict] = None,
        plan_name: str = '',
        stakeholder_ids: List[int] = None
    ) -> Dict[str, Any]:
        """生成结构化拜访预案

        Args:
            project_id: 项目ID
            stakeholder_id: 目标干系人ID（主干系人）
            meeting_purpose: 会议目的
            meeting_type: 会议类型（first_visit/proposal_report/objection_handling/relationship_maintenance）
            related_task_ids: 关联待办事项ID列表
            related_materials: 关联资料列表 [{name, type}]
            plan_name: 预案名称
            stakeholder_ids: 关联多个干系人ID列表
        """
        project = Project.query.get_or_404(project_id)
        stakeholder = Stakeholder.query.get_or_404(stakeholder_id)

        # 关联多个干系人（兼容：若未传，回填主干系人）
        all_stakeholder_ids = list(stakeholder_ids or [])
        if stakeholder_id and stakeholder_id not in all_stakeholder_ids:
            all_stakeholder_ids.insert(0, stakeholder_id)
        # 查询所有关联干系人
        all_stakeholders = Stakeholder.query.filter(
            Stakeholder.id.in_(all_stakeholder_ids),
            Stakeholder.project_id == project_id
        ).all() if all_stakeholder_ids else [stakeholder]

        # 收集关联待办
        related_tasks = []
        if related_task_ids:
            related_tasks = OpportunityTask.query.filter(
                OpportunityTask.id.in_(related_task_ids),
                OpportunityTask.project_id == project_id
            ).all()

        # 构建LLM提示词（传入所有干系人）
        prompt = self._build_prompt(
            project, all_stakeholders, meeting_purpose, meeting_type,
            related_tasks, related_materials or []
        )

        # 调用LLM生成预案
        try:
            llm = self._get_llm()
            result = llm.chat_json(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                max_tokens=3500
            )
        except Exception as e:
            logger.error(f"LLM生成拜访预案失败: {e}")
            result = None

        if not result or not isinstance(result, dict):
            # LLM失败时返回基础结构
            result = {
                'opening': f'与{stakeholder.name}的开场介绍',
                'key_topics': [meeting_purpose or '项目沟通'],
                'expected_objections': [],
                'response_strategies': [],
                'success_criteria': '完成预定沟通目标',
                'follow_up_actions': [],
                'notes': 'LLM生成失败，请人工补充'
            }

        # 预案标题：如果用户未提供名称，则用LLM根据预案内容生成
        final_name = plan_name
        if not final_name:
            final_name = self._generate_plan_name(
                all_stakeholders, meeting_purpose, meeting_type, related_tasks, result
            )

        # 保存到数据库
        plan = MeetingPlan(
            project_id=project_id,
            stakeholder_id=stakeholder_id,
            stakeholder_ids=json.dumps(all_stakeholder_ids, ensure_ascii=False),
            name=final_name,
            meeting_purpose=meeting_purpose,
            meeting_type=meeting_type,
            related_task_ids=json.dumps(related_task_ids or []),
            related_materials=json.dumps(related_materials or []),
            plan_content=json.dumps(result, ensure_ascii=False),
            status='generated'
        )
        db.session.add(plan)
        db.session.commit()

        return {
            'success': True,
            'plan_id': plan.id,
            'plan': {
                'id': plan.id,
                'name': plan.name,
                'stakeholder_id': plan.stakeholder_id,
                'stakeholder_ids': all_stakeholder_ids,
                'stakeholder_name': stakeholder.name,
                'meeting_purpose': plan.meeting_purpose,
                'meeting_type': plan.meeting_type,
                'related_task_ids': related_task_ids or [],
                'related_materials': related_materials or [],
                'plan_content': result,
                'status': plan.status,
                'created_at': plan.created_at.isoformat() if plan.created_at else None
            }
        }

    def _generate_plan_name(
        self,
        stakeholders: List[Stakeholder],
        meeting_purpose: str,
        meeting_type: str,
        related_tasks: List[OpportunityTask],
        plan_content: Dict
    ) -> str:
        """用LLM根据预案内容生成简洁准确的标题（严格禁止套话）

        关键修复：兜底逻辑不再使用 meeting_type（避免默认值污染标题），
        而是用关键议题或会议目的。LLM 生成后还会做关键词过滤。
        """
        if not stakeholders:
            stakeholders = []
        primary = stakeholders[0] if stakeholders else None
        primary_name = primary.name if primary else '拜访'

        # 收集该主干系人已有预案数，帮助LLM判断是第几次沟通
        existing_count = 0
        if primary:
            existing_count = MeetingPlan.query.filter_by(
                stakeholder_id=primary.id
            ).count()

        # 多干系人姓名
        all_names = '、'.join(s.name for s in stakeholders[:3]) if stakeholders else primary_name

        tasks_summary = ''
        if related_tasks:
            tasks_summary = '\n'.join(
                f'- {t.title}' for t in related_tasks[:5]
            )

        key_topics = plan_content.get('key_topics', []) if isinstance(plan_content, dict) else []
        topics_str = '、'.join(key_topics[:3]) if key_topics else ''

        # 开场白作为额外内容线索
        opening = plan_content.get('opening', '') if isinstance(plan_content, dict) else ''
        opening_brief = opening[:60] if opening else ''

        prompt = f"""请为以下拜访预案生成一个简洁的中文标题（10-18字之间）。

## 上下文
- 目标干系人: {all_names}
- 会议目的: {meeting_purpose or '推进项目'}
- 关联待办: {tasks_summary or '无'}
- 预案关键议题: {topics_str or '无'}
- 开场白摘要: {opening_brief or '无'}
- 该干系人已有预案数: {existing_count}（本次为第{existing_count + 1}次沟通）

## 标题要求（务必严格遵守）
1. 标题必须反映本次拜访的**实际内容/议题**（如"造价控制方案确认""ROI数据跟进""技术架构对齐"）
2. **绝对禁止**使用以下套话：初次拜访、第N次拜访、首次沟通、首次拜访、拜访沟通、项目沟通
3. 如果该干系人已有预案（第{existing_count + 1}次），标题应体现**延续性**（如"方案修订跟进""顾虑化解沟通"）
4. 格式："{primary_name} - <核心议题>"，例如"{primary_name} - 造价控制方案确认"
5. 只输出标题文本，不要引号、不要解释、不要换行

直接输出标题文本："""

        # 禁用词列表（LLM 仍可能违规时的后置过滤）
        forbidden_words = ['初次拜访', '首次拜访', '第N次拜访', '第1次拜访', '第一次拜访',
                           '首次沟通', '首次访问', '初次沟通', '初次访问']
        # 兜底标题候选：优先用议题，其次会议目的，最后用"项目沟通"
        def _fallback_name():
            if topics_str:
                return f'{primary_name} - {topics_str[:15]}'
            if meeting_purpose:
                # 取会议目的前15字
                return f'{primary_name} - {meeting_purpose[:15]}'
            return f'{primary_name} - 项目沟通'

        try:
            llm = self._get_llm()
            name = llm.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=80
            )
            if name:
                # 清理可能的引号、换行、前后空白
                name = name.strip().strip('"\'""''').strip().split('\n')[0].strip()
                # 限制长度
                if len(name) > 30:
                    name = name[:30]
                # 后置过滤：若仍包含禁用词，使用兜底
                if any(w in name for w in forbidden_words):
                    logger.warning(f"LLM生成的标题含禁用词，使用兜底: {name}")
                    return _fallback_name()
                # 若标题只是干系人名+拜访类型，也用兜底
                if meeting_type and name.endswith(meeting_type):
                    return _fallback_name()
                return name
        except Exception as e:
            logger.warning(f"LLM生成预案标题失败: {e}")

        return _fallback_name()

    def _build_prompt(
        self,
        project: Project,
        stakeholders: List[Stakeholder],
        meeting_purpose: str,
        meeting_type: str,
        related_tasks: List[OpportunityTask],
        related_materials: List[Dict]
    ) -> str:
        """构建LLM提示词（支持多干系人）"""
        if not stakeholders:
            stakeholders = []
        primary = stakeholders[0] if stakeholders else None

        # 干系人画像（多干系人：主干系人详述，其他简述）
        def _profile_block(sk, is_primary=False):
            prefix = '## 目标干系人画像（主干系人）' if is_primary else '## 参与干系人'
            return f"""{prefix}
- 姓名: {sk.name}
- 职位: {sk.position or '未知'}
- 采购角色: {sk.buyer_role or '未分类'}
- 决策力: {sk.decision_power}/10
- 支持度: {sk.support_level}/10
- 紧迫感: {sk.urgency}/10
- 职责: {sk.responsibilities or '未知'}
- 个人诉求: {sk.personal_agenda or '未知'}"""

        sk_profile = _profile_block(primary, is_primary=True) if primary else ''
        if len(stakeholders) > 1:
            for sk in stakeholders[1:5]:
                sk_profile += '\n\n' + _profile_block(sk, is_primary=False)

        # 项目上下文
        proj_context = f"""## 项目背景
- 项目名称: {project.name}
- 客户名称: {project.customer_name or '未知'}
- 销售阶段: {project.sales_stage}
- 公司愿景: {project.company_vision or '未知'}
- 业务痛点: {_build_project_insight_summary(project.id) or '未知'}"""

        # 该干系人的历史互动记录（基于主干系人）
        history_section = ''
        if primary:
            try:
                history_text = build_stakeholder_history_text(
                    primary.id, max_state_logs=6, max_tasks=10, max_plans=3, max_feedbacks=4
                )
                if history_text:
                    history_section = f"""

## 该干系人的历史互动记录（基于历史保持沟通连续性，避免重复）
{history_text}
"""
            except Exception as e:
                logger.warning(f"获取干系人{primary.id}历史记录失败: {e}")

        # 关联待办
        tasks_str = ''
        if related_tasks:
            tasks_str = '\n## 本次拜访需推进的待办事项'
            for t in related_tasks:
                tasks_str += f'\n- [{t.priority}] {t.title}: {t.description or ""}'

        # 关联资料
        materials_str = ''
        if related_materials:
            materials_str = '\n## 本次拜访可用的资料'
            for m in related_materials:
                materials_str += f'\n- {m.get("name", "未知资料")} ({m.get("type", "")})'

        return f"""你是一位资深B2B销售教练。请为以下拜访场景生成一份结构化拜访预案。

{proj_context}

{sk_profile}
{history_section}
## 会议信息
- 会议类型: {meeting_type}
- 会议目的: {meeting_purpose or '推进项目'}{tasks_str}{materials_str}

## 输出格式（严格JSON）
{{
  "opening": "开场白（30秒内，建立连接并引入主题）",
  "key_topics": ["关键议题1", "关键议题2", "关键议题3"],
  "expected_objections": [
    {{
      "objection": "预期的异议或顾虑",
      "underlying_concern": "背后的真实关切",
      "response": "应对话术"
    }}
  ],
  "response_strategies": [
    {{
      "strategy": "策略名称",
      "tactic": "具体战术",
      "talking_points": "关键话术要点"
    }}
  ],
  "success_criteria": "本次拜访成功的衡量标准",
  "follow_up_actions": ["后续行动1", "后续行动2"],
  "risk_warnings": ["风险提示1", "风险提示2"]
}}

要求：
1. 基于该干系人的采购角色、支持度、决策力和个人诉求定制
2. 应对话术要具体可执行，不是套话
3. **保持连续性**：如果提供了"历史互动记录"，本次拜访预案必须在历史沟通基础上延续推进——已讨论过的议题可简要回顾但不要重复展开，已知的异议要针对性跟进而非重新发现，已完成的事项确认结果后推进下一步
4. 控制在1500字以内
只输出JSON，不要输出其他内容。"""

    def get_plans(self, project_id: int) -> Dict[str, Any]:
        """获取项目的所有拜访预案"""
        plans = MeetingPlan.query.filter_by(project_id=project_id).order_by(
            MeetingPlan.created_at.desc()
        ).all()

        return {
            'project_id': project_id,
            'plans': [self._plan_to_dict(p) for p in plans],
            'total': len(plans)
        }

    def get_plan(self, plan_id: int) -> Dict[str, Any]:
        """获取单个拜访预案"""
        plan = MeetingPlan.query.get_or_404(plan_id)
        return {
            'success': True,
            'plan': self._plan_to_dict(plan)
        }

    def _plan_to_dict(self, plan: MeetingPlan) -> Dict:
        """转字典（动态计算预案状态：completed/active/基础状态）

        状态优先级：
        1. completed: 已关联拜访记录，或关联待办全部完成
        2. active: 关联待办仍处于 pending/in_progress
        3. 基础状态: pending/generated/reviewed
        """
        stakeholder = Stakeholder.query.get(plan.stakeholder_id)
        try:
            plan_content = json.loads(plan.plan_content) if plan.plan_content else None
        except (json.JSONDecodeError, TypeError):
            plan_content = None
        try:
            related_task_ids = json.loads(plan.related_task_ids) if plan.related_task_ids else []
        except (json.JSONDecodeError, TypeError):
            related_task_ids = []
        try:
            related_materials = json.loads(plan.related_materials) if plan.related_materials else []
        except (json.JSONDecodeError, TypeError):
            related_materials = []
        try:
            stakeholder_ids_list = json.loads(plan.stakeholder_ids) if plan.stakeholder_ids else []
        except (json.JSONDecodeError, TypeError):
            stakeholder_ids_list = []
        # 兼容：若无 stakeholder_ids 回填主干系人
        if not stakeholder_ids_list and plan.stakeholder_id:
            stakeholder_ids_list = [plan.stakeholder_id]
        # 查询所有关联干系人姓名
        stakeholder_names = []
        if stakeholder_ids_list:
            sks = Stakeholder.query.filter(Stakeholder.id.in_(stakeholder_ids_list)).all()
            stakeholder_names = [s.name for s in sks]

        # 动态计算预案状态
        dynamic_status = plan.status
        has_feedback = FeedbackRecord.query.filter_by(
            related_meeting_plan_id=plan.id
        ).first() is not None
        if has_feedback:
            dynamic_status = 'completed'
        else:
            # 检查关联待办状态
            if related_task_ids:
                all_tasks = OpportunityTask.query.filter(
                    OpportunityTask.id.in_(related_task_ids)
                ).all()
                active_tasks = [t for t in all_tasks if t.status in ('pending', 'in_progress')]
                completed_tasks = [t for t in all_tasks if t.status in ('completed',)]
                # 关联待办全部完成（至少1个完成且无活动）→ completed
                if all_tasks and not active_tasks and completed_tasks:
                    dynamic_status = 'completed'
                elif active_tasks:
                    dynamic_status = 'active'

        return {
            'id': plan.id,
            'project_id': plan.project_id,
            'stakeholder_id': plan.stakeholder_id,
            'stakeholder_ids': stakeholder_ids_list,
            'stakeholder_name': stakeholder.name if stakeholder else '',
            'stakeholder_names': stakeholder_names,
            'name': plan.name,
            'meeting_purpose': plan.meeting_purpose,
            'meeting_type': plan.meeting_type,
            'related_task_ids': related_task_ids,
            'related_materials': related_materials,
            'plan_content': plan_content,
            'status': dynamic_status,
            'db_status': plan.status,
            'created_at': plan.created_at.isoformat() if plan.created_at else None,
            'updated_at': plan.updated_at.isoformat() if plan.updated_at else None
        }
