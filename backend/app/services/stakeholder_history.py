"""
干系人历史互动记录聚合服务
将分散在多张表中的历史沟通数据（状态变化、待办执行、拜访预案、反馈纪要）聚合为文本，
注入行动建议和拜访预案的LLM prompt，避免生成重复或脱离上下文的建议。
"""

import json
import logging
from typing import Optional

from app.models.database import (
    Stakeholder, StateChangeLog, OpportunityTask,
    MeetingPlan, FeedbackRecord
)

logger = logging.getLogger(__name__)


def _fmt_date(dt) -> str:
    if not dt:
        return ''
    return dt.strftime('%m-%d')


def build_stakeholder_history_text(
    stakeholder_id: int,
    max_state_logs: int = 5,
    max_tasks: int = 8,
    max_plans: int = 2,
    max_feedbacks: int = 3
) -> str:
    """构建干系人历史互动记录文本，用于注入LLM prompt

    聚合4类历史数据：
    - StateChangeLog: 态度/属性变化轨迹（含变化理由）
    - OpportunityTask: 历史待办及完成情况（含完成备注）
    - MeetingPlan: 历史拜访预案（议题、异议）
    - FeedbackRecord: 历史沟通反馈纪要（原文摘要）

    Args:
        stakeholder_id: 干系人ID
        max_state_logs: 最多取多少条状态变化
        max_tasks: 最多取多少条待办
        max_plans: 最多取多少条拜访预案
        max_feedbacks: 最多取多少条反馈纪要

    Returns:
        格式化的历史记录文本块；无历史时返回空字符串
    """
    stakeholder = Stakeholder.query.get(stakeholder_id)
    if not stakeholder:
        return ''

    # 1. 状态变化轨迹（按时间倒序）
    state_logs = StateChangeLog.query.filter_by(
        stakeholder_id=stakeholder_id
    ).order_by(
        StateChangeLog.created_at.desc()
    ).limit(max_state_logs).all()

    # 2. 历史待办（按时间倒序）
    tasks = OpportunityTask.query.filter_by(
        stakeholder_id=stakeholder_id
    ).order_by(
        OpportunityTask.created_at.desc()
    ).limit(max_tasks).all()

    # 3. 历史拜访预案（按时间倒序）
    plans = MeetingPlan.query.filter_by(
        stakeholder_id=stakeholder_id
    ).order_by(
        MeetingPlan.created_at.desc()
    ).limit(max_plans).all()

    # 4. 历史反馈纪要
    # FeedbackRecord没有直接的stakeholder_id，通过两条路径间接关联：
    #   路径A: related_meeting_plan_id -> MeetingPlan.stakeholder_id
    #   路径B: related_task_ids JSON -> OpportunityTask.stakeholder_id
    task_ids = {t.id for t in tasks}
    plan_ids = {p.id for p in plans}

    all_feedbacks = FeedbackRecord.query.filter_by(
        project_id=stakeholder.project_id
    ).order_by(
        FeedbackRecord.created_at.desc()
    ).limit(50).all()

    related_feedbacks = []
    seen_fb_ids = set()
    for fb in all_feedbacks:
        if len(related_feedbacks) >= max_feedbacks:
            break
        if fb.id in seen_fb_ids:
            continue

        is_related = False
        # 路径A：通过预案ID关联
        if fb.related_meeting_plan_id and fb.related_meeting_plan_id in plan_ids:
            is_related = True
        # 路径B：通过待办ID关联
        elif fb.related_task_ids and task_ids:
            try:
                fb_task_ids = set(json.loads(fb.related_task_ids))
                if fb_task_ids & task_ids:
                    is_related = True
            except (json.JSONDecodeError, TypeError):
                pass

        if is_related:
            related_feedbacks.append(fb)
            seen_fb_ids.add(fb.id)

    # 无历史数据时返回空
    if not state_logs and not tasks and not plans and not related_feedbacks:
        return ''

    sections = []

    # --- 状态变化轨迹 ---
    if state_logs:
        attr_labels = {
            'support_level': '支持度',
            'decision_power': '决策力',
            'urgency': '紧迫感',
            'buyer_role': '采购角色',
            'position': '职位',
            'responsibilities': '职责',
            'personal_agenda': '个人诉求',
            'create_stakeholder': '创建',
            'merged': '合并'
        }
        lines = ['### 态度变化轨迹']
        for log in state_logs:
            attr = attr_labels.get(log.attribute_name, log.attribute_name)
            date = _fmt_date(log.created_at)
            old = log.old_value or '无'
            reasoning = f'（{log.reasoning}）' if log.reasoning else ''
            lines.append(f'- [{date}] {attr}: {old} → {log.new_value}{reasoning}')
        sections.append('\n'.join(lines))

    # --- 历史待办与执行情况 ---
    if tasks:
        status_labels = {
            'pending': '待办',
            'in_progress': '进行中',
            'completed': '已完成',
            'cancelled': '已取消'
        }
        lines = ['### 历史待办与执行情况']
        for t in tasks:
            status = status_labels.get(t.status, t.status)
            line = f'- [{status}] {t.title}'
            if t.status == 'completed' and t.completion_note:
                line += f'（完成备注: {t.completion_note[:80]}）'
            elif t.status in ('pending', 'in_progress') and t.description:
                line += f'（{t.description[:80]}）'
            lines.append(line)
        sections.append('\n'.join(lines))

    # --- 历史拜访预案 ---
    if plans:
        lines = ['### 历史拜访预案']
        for p in plans:
            date = _fmt_date(p.created_at)
            line = f'- [{date}] {p.meeting_type or "拜访"} - 目的: {p.meeting_purpose or "未指定"}'
            if p.plan_content:
                try:
                    content = json.loads(p.plan_content)
                    topics = content.get('key_topics', [])
                    if topics:
                        topics_str = ', '.join(str(t) for t in topics[:3])
                        line += f'；议题: {topics_str}'
                    objections = content.get('expected_objections', [])
                    if objections:
                        obs = []
                        for o in objections[:2]:
                            if isinstance(o, dict):
                                obs.append(o.get('objection', ''))
                            else:
                                obs.append(str(o))
                        line += f'；已知异议: {", ".join(obs)}'
                except (json.JSONDecodeError, TypeError):
                    pass
            lines.append(line)
        sections.append('\n'.join(lines))

    # --- 历史沟通反馈纪要 ---
    if related_feedbacks:
        lines = ['### 历史沟通反馈纪要']
        for fb in related_feedbacks:
            date = _fmt_date(fb.created_at)
            text = (fb.feedback_text or '')[:300]
            line = f'- [{date}] {text}'
            if fb.parse_summary:
                line += f'（解析摘要: {fb.parse_summary[:100]}）'
            lines.append(line)
        sections.append('\n'.join(lines))

    return '\n\n'.join(sections)
