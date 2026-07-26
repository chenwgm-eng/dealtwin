"""
Challenger 销售检查清单评估
对照 Challenger 方法论的关键动作，用纯 SQLAlchemy 查询评估项目完成度（不调LLM）
"""

import json
import logging
from typing import Dict, Any

from sqlalchemy import or_

from app.models.database import (
    Project, Stakeholder, MilestoneDecision, ChallengerTeaching,
    MeetingPlan, FeedbackRecord, OpportunityTask,
)

logger = logging.getLogger(__name__)


def _enum_val(val):
    """Enum 字段规范化为字符串"""
    if val is None:
        return None
    return val.value if hasattr(val, 'value') else str(val)


def evaluate_challenger_checklist(project_id: int) -> Dict[str, Any]:
    """评估项目的 Challenger 检查清单（5 项）

    Returns:
        {
            'items': [{'key', 'label', 'passed', 'detail', 'suggestion'}],
            'passed_count': int,
            'total': int
        }
    """
    project = Project.query.get_or_404(project_id)

    items = [
        _check_procurement_verified(project_id),
        _check_stakeholder_alignment(project_id),
        _check_commercial_insight(project_id),
        _check_powerful_ask(project_id),
        _check_verifiable_action(project_id),
    ]
    passed_count = sum(1 for item in items if item['passed'])
    return {
        'items': items,
        'passed_count': passed_count,
        'total': len(items)
    }


def _check_procurement_verified(project_id: int) -> Dict[str, Any]:
    """1. 采购进展验证：项目有拜访反馈记录，或有非 pending 的里程碑决策"""
    has_feedback = FeedbackRecord.query.filter_by(project_id=project_id).first() is not None
    has_decision = MilestoneDecision.query.filter(
        MilestoneDecision.project_id == project_id,
        MilestoneDecision.decision != 'pending'
    ).first() is not None
    passed = has_feedback or has_decision

    if passed:
        sources = []
        if has_feedback:
            sources.append('拜访反馈')
        if has_decision:
            sources.append('里程碑决策')
        detail = f'已有{"、".join(sources)}记录，采购进展已验证'
        suggestion = ''
    else:
        detail = '尚无拜访反馈或里程碑决策记录，采购进展未验证'
        suggestion = '请录入拜访反馈，或完成里程碑决策（如 OM10 Bid/No-Go），验证客户采购进展'
    return {
        'key': 'procurement_verified',
        'label': '采购进展验证',
        'passed': passed,
        'detail': detail,
        'suggestion': suggestion
    }


def _check_stakeholder_alignment(project_id: int) -> Dict[str, Any]:
    """2. 干系人达成一致：干系人>=3、至少1个 decision_maker、至少1个 mobilizer，并识别有无 blocker"""
    stakeholders = Stakeholder.query.filter_by(project_id=project_id).all()
    total = len(stakeholders)
    has_decision_maker = any(_enum_val(s.project_role) == 'decision_maker' for s in stakeholders)
    mobilizers = [s for s in stakeholders if _enum_val(s.buyer_role) == 'mobilizer']
    blockers = [s for s in stakeholders if _enum_val(s.buyer_role) == 'blocker']

    missing = []
    if total < 3:
        missing.append(f'干系人仅{total}人（需>=3）')
    if not has_decision_maker:
        missing.append('缺少 decision_maker（项目角色）')
    if not mobilizers:
        missing.append('缺少 mobilizer（角色类型）')
    passed = not missing

    blocker_desc = f'已识别{len(blockers)}个blocker' if blockers else '未发现blocker'
    if passed:
        detail = f'干系人{total}人，关键角色齐备，{blocker_desc}'
        suggestion = ''
    else:
        detail = f'干系人{total}人，{blocker_desc}；缺：{"、".join(missing)}'
        suggestion = '完善干系人地图：至少识别3名干系人，确认 decision_maker 与 mobilizer，并排查是否存在 blocker'
    return {
        'key': 'stakeholder_alignment',
        'label': '干系人达成一致',
        'passed': passed,
        'detail': detail,
        'suggestion': suggestion
    }


def _check_commercial_insight(project_id: int) -> Dict[str, Any]:
    """3. 商业见解已备：存在已生成的商业指导话术或拜访预案"""
    has_teaching = ChallengerTeaching.query.filter_by(
        project_id=project_id, status='generated'
    ).first() is not None
    has_plan = MeetingPlan.query.filter_by(
        project_id=project_id, status='generated'
    ).first() is not None
    passed = has_teaching or has_plan

    if passed:
        sources = []
        if has_teaching:
            sources.append('商业指导话术')
        if has_plan:
            sources.append('拜访预案')
        detail = f'已生成{"、".join(sources)}，商业见解已备'
        suggestion = ''
    else:
        detail = '尚无已生成的商业指导话术或拜访预案'
        suggestion = '生成 Challenger 商业指导话术或拜访预案，形成可传递的商业见解'
    return {
        'key': 'commercial_insight',
        'label': '商业见解已备',
        'passed': passed,
        'detail': detail,
        'suggestion': suggestion
    }


def _check_powerful_ask(project_id: int) -> Dict[str, Any]:
    """4. 有力的请求：最新已生成商业指导的 powerful_ask.what 非空"""
    latest = ChallengerTeaching.query.filter_by(
        project_id=project_id, status='generated'
    ).order_by(ChallengerTeaching.created_at.desc()).first()

    ask_what = ''
    if latest and latest.teaching_content:
        try:
            content = json.loads(latest.teaching_content)
        except (json.JSONDecodeError, TypeError):
            content = {}
        powerful_ask = content.get('powerful_ask') if isinstance(content, dict) else None
        if isinstance(powerful_ask, dict):
            ask_what = str(powerful_ask.get('what') or '').strip()
    passed = bool(ask_what)

    if passed:
        detail = f'最新商业指导已包含明确请求：{ask_what[:50]}'
        suggestion = ''
    else:
        detail = '尚无包含明确请求（powerful_ask.what）的商业指导'
        suggestion = '在商业指导中明确有力的请求四要素（why/when/who/what），特别是具体请求什么'
    return {
        'key': 'powerful_ask',
        'label': '有力的请求',
        'passed': passed,
        'detail': detail,
        'suggestion': suggestion
    }


def _check_verifiable_action(project_id: int) -> Dict[str, Any]:
    """5. 可验证客户行动：存在进行中/已完成且关联干系人的待办

    关联判定：stakeholder_id（主干系人）或 stakeholder_ids（JSON 数组）非空
    """
    task = OpportunityTask.query.filter(
        OpportunityTask.project_id == project_id,
        OpportunityTask.status.in_(['in_progress', 'completed']),
        or_(
            OpportunityTask.stakeholder_id.isnot(None),
            OpportunityTask.stakeholder_ids.isnot(None) & (OpportunityTask.stakeholder_ids != '[]')
        )
    ).first()
    passed = task is not None

    if passed:
        detail = f'存在推进中的客户行动：{task.title}'
        suggestion = ''
    else:
        detail = '尚无进行中/已完成且关联干系人的客户行动'
        suggestion = '创建关联干系人的行动待办并推进，获得可验证的客户行动承诺'
    return {
        'key': 'verifiable_action',
        'label': '可验证客户行动',
        'passed': passed,
        'detail': detail,
        'suggestion': suggestion
    }
