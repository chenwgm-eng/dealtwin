"""
阶段交付物追踪器 - 服务层

将 sales_stages/spec.md 中静态定义的五阶段任务清单/交付物清单固化为系统能力。
基于 SVS+Challenge Sales 框架：suspect → identity → define → confirm → close
（close 含 closed_won / closed_lost 两个终态）。

主要能力：
- STAGE_DEFINITIONS：六阶段（含 closed_won / closed_lost）静态定义常量
- init_project_stage_deliverables：为项目某阶段批量初始化交付物记录
- get_project_stage_deliverables：查询项目某阶段的交付物清单及完成状态
- update_deliverable_status：更新单个交付物项状态
- check_stage_readiness：执行阶段准入检查，返回推进建议
"""

from datetime import datetime
import json
from typing import Optional

from app import db
from app.models.database import (
    Project,
    ProjectStrategyItem,
    ProjectWhyContext,
    StageDeliverable,
    StateChangeLog,
)


def _parse_attachments(record):
    """从 StageDeliverable.attachments 字段解析附件列表"""
    if not record or not record.attachments:
        return []
    try:
        data = json.loads(record.attachments)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


# =============================================================================
# 阶段定义常量
# =============================================================================

# Suspect 阶段交付物分组键
_SUSPECT_DELIVERABLES = [
    {
        'key': 'account_plan',
        'name': '客户计划',
        'items': [
            {'key': 'company_structure', 'name': '公司结构图'},
            {'key': 'customer_strategy', 'name': '客户战略图'},
            {'key': 'sales_goals', 'name': '销售目标与任务'},
        ]
    },
    {
        'key': 'suspect_evaluation',
        'name': '线索评估记录',
        'items': [
            {'key': 'opportunity_scorecard', 'name': '商机评分卡'},
            {'key': 'om10_decision', 'name': 'OM10 决策记录'},
        ]
    },
    {
        'key': 'relationship_map',
        'name': '初始关系图谱',
        'items': [
            {'key': 'initial_map', 'name': '初始关系图谱', 'is_optional': True},
        ]
    },
]

# Identity 阶段交付物分组键
_IDENTITY_DELIVERABLES = [
    {
        'key': 'stakeholder_map',
        'name': '干系人图谱',
        'items': [
            {'key': 'stakeholder_list', 'name': '干系人列表（姓名、职位、角色）'},
            {'key': 'stakeholder_attributes', 'name': '干系人属性（决策力、支持度、紧迫感）'},
            {'key': 'relationship_lines', 'name': '关系连线（影响力权重）'},
        ]
    },
    {
        'key': 'customer_requirements',
        'name': '客户需求文档',
        'items': [
            {'key': 'pain_points', 'name': '业务痛点分析'},
            {'key': 'budget_range', 'name': '预算范围确认'},
            {'key': 'procurement_process', 'name': '采购流程说明'},
        ]
    },
    {
        'key': 'om20_decision',
        'name': 'OM20 决策记录',
        'items': [
            {'key': 'om20_decision_record', 'name': 'OM20 决策记录'},
        ]
    },
    {
        'key': 'pursuit_team',
        'name': '商机团队组建名单',
        'items': [
            {'key': 'team_roster', 'name': '商机团队组建名单（销售、售前）'},
        ]
    },
]

# Define 阶段交付物分组键
_DEFINE_DELIVERABLES = [
    {
        'key': 'opportunity_plan',
        'name': '商机计划',
        'items': [
            {'key': 'customer_background', 'name': '客户背景和需求'},
            {'key': 'value_proposition', 'name': '价值主张'},
            {'key': 'sales_strategy', 'name': '销售策略'},
            {'key': 'competitive_analysis', 'name': '竞争分析'},
            {'key': 'risk_assessment', 'name': '风险评估'},
            {'key': 'action_plan', 'name': '行动计划'},
        ]
    },
    {
        'key': 'solution_doc',
        'name': '解决方案文档',
        'items': [
            {'key': 'technical_solution', 'name': '技术方案'},
            {'key': 'commercial_solution', 'name': '商务方案'},
            {'key': 'roi_analysis', 'name': 'ROI 分析'},
        ]
    },
    {
        'key': 'om30_review',
        'name': 'OM30 策略评审记录',
        'items': [
            {'key': 'om30_review_record', 'name': 'OM30 策略评审记录'},
        ]
    },
    {
        'key': 'om40_approval',
        'name': 'OM40 投标批准文件',
        'items': [
            {'key': 'om40_approval_doc', 'name': 'OM40 投标批准文件'},
        ]
    },
    {
        'key': 'csp_draft',
        'name': '客户成功计划 (CSP) 草稿',
        'items': [
            {'key': 'csp_draft_doc', 'name': 'CSP 草稿'},
        ]
    },
]

# Confirm 阶段交付物分组键
_CONFIRM_DELIVERABLES = [
    {
        'key': 'negotiation_records',
        'name': '谈判记录',
        'items': [
            {'key': 'meeting_minutes', 'name': '会议纪要'},
            {'key': 'objection_handling', 'name': '异议处理记录'},
            {'key': 'term_changes', 'name': '条款变更记录'},
        ]
    },
    {
        'key': 'contract_files',
        'name': '合同文件',
        'items': [
            {'key': 'signed_contract', 'name': '签署的合同'},
            {'key': 'sow', 'name': 'SOW（工作说明书）'},
            {'key': 'final_csp', 'name': '最终版 CSP'},
        ]
    },
    {
        'key': 'om70_decision',
        'name': 'OM70 决策记录',
        'items': [
            {'key': 'win_loss_analysis', 'name': '赢单/丢单原因分析'},
        ]
    },
]


def _build_close_deliverables(is_won: bool):
    """构造 Close 阶段交付物清单（closed_won / closed_lost 共用模板）"""
    if is_won:
        close_report_items = [
            {'key': 'win_confirmation', 'name': '赢单确认'},
            {'key': 'contract_copy', 'name': '合同副本'},
        ]
    else:
        close_report_items = [
            {'key': 'loss_confirmation', 'name': '丢单确认'},
            {'key': 'loss_reason_analysis', 'name': '丢单原因分析'},
        ]
    deliverables = [
        {
            'key': 'close_report',
            'name': '关单报告',
            'items': close_report_items,
        },
        {
            'key': 'lessons_learned',
            'name': '经验教训文档',
            'items': [
                {'key': 'lessons_learned_doc', 'name': '经验教训文档'},
            ]
        },
    ]
    # 客户交接文档仅赢单场景适用
    if is_won:
        deliverables.append({
            'key': 'handover_doc',
            'name': '客户交接文档',
            'items': [
                {'key': 'handover_doc_to_delivery', 'name': '客户交接文档（→ 实施团队）'},
            ]
        })
    return deliverables


# =============================================================================
# 自动检查规则（基于项目数据自动判定交付物完成状态）
# =============================================================================

def _text_nonempty(text):
    """文本非空判定：非 None 且去空白后非空"""
    return bool(text and text.strip())


def _default_auto_check(project):
    """默认规则：无法自动判定，需人工确认"""
    return {'status': 'pending', 'reason': '系统暂无对应数据源，请人工确认后勾选完成'}


# ---- Suspect 阶段规则 ----

def _check_company_structure(project):
    """account_plan.company_structure：客户有联系人且联系人具备部门/职位或汇报关系"""
    customer = getattr(project, 'customer', None)
    if customer is None:
        return {'status': 'pending', 'reason': '未关联客户或无联系人'}
    contacts = getattr(customer, 'contacts', None) or []
    children = getattr(customer, 'children', None) or []
    contact_count = len(contacts)
    child_count = len(children)
    # 子公司存在即视为结构已建立（保留原有信号）
    if child_count > 0:
        return {'status': 'completed', 'reason': f'客户已关联 {contact_count} 个联系人、{child_count} 个子公司'}
    if contact_count == 0:
        return {'status': 'pending', 'reason': '未关联客户或无联系人'}
    # 联系人需具备部门+职位 或 汇报关系，才算结构图完整
    has_dept_pos = any(
        _text_nonempty(getattr(c, 'department', None))
        and _text_nonempty(getattr(c, 'position', None))
        for c in contacts
    )
    has_reports_to = any(getattr(c, 'reports_to_id', None) is not None for c in contacts)
    if has_dept_pos or has_reports_to:
        return {'status': 'completed', 'reason': f'客户已关联 {contact_count} 个联系人，且已建立部门/汇报关系'}
    return {'status': 'pending', 'reason': '联系人缺少部门/职位或汇报关系，结构图不完整'}


def _check_customer_strategy(project):
    """account_plan.customer_strategy：project.company_vision 非空，或客户档案的行业/核心产品/发展历程至少 2 项非空"""
    if _text_nonempty(getattr(project, 'company_vision', None)):
        return {'status': 'completed', 'reason': '已填写公司愿景'}
    customer = getattr(project, 'customer', None)
    if customer is not None:
        fields = [
            ('industry', '行业'),
            ('core_products', '核心产品'),
            ('company_history', '发展历程'),
        ]
        filled = [label for f, label in fields if _text_nonempty(getattr(customer, f, None))]
        if len(filled) >= 2:
            return {'status': 'completed', 'reason': f'客户档案已填写：{ "、".join(filled) }'}
    return {'status': 'pending', 'reason': '未填写公司愿景，且客户档案信息不足'}


def _check_sales_goals(project):
    """account_plan.sales_goals：项目有 ≥1 个 task，且至少 1 个 task 设置了 due_date"""
    tasks = getattr(project, 'tasks', None) or []
    count = len(tasks)
    if count == 0:
        return {'status': 'pending', 'reason': '暂无待办事项'}
    with_due = sum(1 for t in tasks if getattr(t, 'due_date', None) is not None)
    if with_due > 0:
        return {'status': 'completed', 'reason': f'已有 {count} 个待办事项，其中 {with_due} 个已设定截止时间'}
    return {'status': 'pending', 'reason': f'已有 {count} 个待办事项，但均未设定截止时间'}


def _check_opportunity_scorecard(project):
    """suspect_evaluation.opportunity_scorecard：四项确定性指标均已设置"""
    fields = [
        ('budget', '预算'),
        ('time_certainty', '时间确定性'),
        ('budget_certainty', '预算确定性'),
        ('tendency', '倾向性'),
    ]
    missing = [label for field, label in fields if getattr(project, field, None) is None]
    if not missing:
        return {'status': 'completed', 'reason': '四项确定性指标均已设置'}
    return {'status': 'pending', 'reason': '缺失指标：' + '、'.join(missing)}


def _check_initial_map(project):
    """relationship_map.initial_map：项目有 ≥1 个 stakeholder"""
    stakeholders = getattr(project, 'stakeholders', None) or []
    count = len(stakeholders)
    if count > 0:
        return {'status': 'completed', 'reason': f'已有 {count} 位干系人'}
    return {'status': 'pending', 'reason': '暂无干系人'}


# ---- Identity 阶段规则 ----

def _check_stakeholder_list(project):
    """stakeholder_map.stakeholder_list：项目有 ≥1 个 stakeholder，且至少 1 个有职位"""
    stakeholders = getattr(project, 'stakeholders', None) or []
    count = len(stakeholders)
    if count == 0:
        return {'status': 'pending', 'reason': '暂无干系人'}
    with_position = sum(1 for s in stakeholders if _text_nonempty(getattr(s, 'position', None)))
    if with_position > 0:
        return {'status': 'completed', 'reason': f'已有 {count} 位干系人，其中 {with_position} 位已填写职位'}
    return {'status': 'pending', 'reason': f'已有 {count} 位干系人，但均未填写职位'}


def _check_stakeholder_attributes(project):
    """stakeholder_map.stakeholder_attributes：三维属性齐全，且至少 1 位已确认/1 位已识别角色类型"""
    stakeholders = getattr(project, 'stakeholders', None) or []
    if not stakeholders:
        return {'status': 'pending', 'reason': '暂无干系人'}
    incomplete = 0
    for s in stakeholders:
        if (getattr(s, 'decision_power', None) is None
                or getattr(s, 'support_level', None) is None
                or getattr(s, 'urgency', None) is None):
            incomplete += 1
    if incomplete > 0:
        return {'status': 'pending', 'reason': f'{incomplete} 位干系人属性不完整'}
    # 进一步检查：至少 1 位已确认 + 至少 1 位已识别角色类型
    confirmed_count = sum(1 for s in stakeholders if getattr(s, 'status', None) == 'confirmed')
    with_buyer_role = sum(1 for s in stakeholders if getattr(s, 'buyer_role', None) is not None)
    if confirmed_count == 0:
        return {'status': 'pending', 'reason': f'{len(stakeholders)} 位干系人属性完整，但均未确认'}
    if with_buyer_role == 0:
        return {'status': 'pending', 'reason': f'{len(stakeholders)} 位干系人属性完整，但角色类型未识别'}
    return {'status': 'completed', 'reason': f'{len(stakeholders)} 位干系人属性完整，{confirmed_count} 位已确认，{with_buyer_role} 位已识别角色'}


def _check_relationship_lines(project):
    """stakeholder_map.relationship_lines：项目有 ≥1 个 relationship"""
    relationships = getattr(project, 'relationships', None) or []
    count = len(relationships)
    if count > 0:
        return {'status': 'completed', 'reason': f'已有 {count} 条关系连线'}
    return {'status': 'pending', 'reason': '暂无关系连线'}


def _check_pain_points(project):
    """customer_requirements.pain_points：项目有 ≥1 个 ProjectStrategyItem(item_type='pain_point')"""
    if ProjectStrategyItem.query.filter_by(project_id=project.id, item_type='pain_point').count() >= 1:
        return {'status': 'completed', 'reason': '已填写业务痛点'}
    return {'status': 'pending', 'reason': '未填写业务痛点'}


def _check_budget_range(project):
    """customer_requirements.budget_range：project.budget 非空（not None and > 0）"""
    budget = getattr(project, 'budget', None)
    if budget is not None and budget > 0:
        return {'status': 'completed', 'reason': '已设置预算范围'}
    return {'status': 'pending', 'reason': '未设置预算范围'}


# ---- Define 阶段规则 ----

def _check_customer_background(project):
    """opportunity_plan.customer_background：项目有 ≥1 个 ProjectStrategyItem（任意类型）"""
    if ProjectStrategyItem.query.filter_by(project_id=project.id).count() >= 1:
        return {'status': 'completed', 'reason': '已填写客户背景'}
    return {'status': 'pending', 'reason': '未填写客户背景'}


def _check_value_proposition(project):
    """opportunity_plan.value_proposition：项目有 ≥1 个 ProjectWhyContext"""
    if ProjectWhyContext.query.filter_by(project_id=project.id).count() >= 1:
        return {'status': 'completed', 'reason': '已填写价值主张'}
    return {'status': 'pending', 'reason': '未填写价值主张'}


def _check_competitive_analysis(project):
    """opportunity_plan.competitive_analysis：project.competitive_analysis 非空"""
    if _text_nonempty(getattr(project, 'competitive_analysis', None)):
        return {'status': 'completed', 'reason': '已填写竞争分析'}
    return {'status': 'pending', 'reason': '未填写竞争分析'}


def _check_action_plan(project):
    """opportunity_plan.action_plan：项目有 ≥1 个 task，且至少 1 个有进展（in_progress/completed）"""
    tasks = getattr(project, 'tasks', None) or []
    count = len(tasks)
    if count == 0:
        return {'status': 'pending', 'reason': '暂无待办事项'}
    in_progress = sum(1 for t in tasks if getattr(t, 'status', None) in ('in_progress', 'completed'))
    if in_progress > 0:
        return {'status': 'completed', 'reason': f'已有 {count} 个待办事项，其中 {in_progress} 个有进展'}
    return {'status': 'pending', 'reason': f'已有 {count} 个待办事项，但均未启动'}


# ---- Confirm 阶段规则 ----

def _check_meeting_minutes(project):
    """negotiation_records.meeting_minutes：项目有 ≥1 个状态为 reviewed/completed 的 meeting_plan，且内容非空

    MeetingPlan.status 枚举为 pending/generated/reviewed；reviewed 视为已完成（兼容 completed 字符串）。
    """
    meeting_plans = getattr(project, 'meeting_plans', None) or []
    completed_count = sum(
        1 for p in meeting_plans
        if getattr(p, 'status', None) in ('reviewed', 'completed')
        and (_text_nonempty(getattr(p, 'meeting_purpose', None))
             or _text_nonempty(getattr(p, 'plan_content', None)))
    )
    if completed_count > 0:
        return {'status': 'completed', 'reason': f'已有 {completed_count} 个已审阅且内容完整的会议预案'}
    return {'status': 'pending', 'reason': '暂无已审阅且内容完整的会议预案'}


def _check_objection_handling(project):
    """negotiation_records.objection_handling：项目有 ≥1 条 feedback_record，且至少 1 条 feedback_text 非空"""
    feedback_records = getattr(project, 'feedback_records', None) or []
    count = len(feedback_records)
    if count == 0:
        return {'status': 'pending', 'reason': '暂无反馈记录'}
    with_text = sum(1 for f in feedback_records if _text_nonempty(getattr(f, 'feedback_text', None)))
    if with_text > 0:
        return {'status': 'completed', 'reason': f'已有 {count} 条反馈记录，其中 {with_text} 条内容完整'}
    return {'status': 'pending', 'reason': f'已有 {count} 条反馈记录，但反馈内容均为空'}


# ---- 推断式检查规则（无直接字段，基于相关数据推断） ----

def _check_procurement_process(project):
    """customer_requirements.procurement_process：决策人已识别则视为采购流程已了解

    无 procurement_process 字段，用 Stakeholder.project_role='decision_maker' 作为代理指标。
    """
    stakeholders = getattr(project, 'stakeholders', None) or []
    decision_maker_count = sum(
        1 for s in stakeholders if getattr(s, 'project_role', None) == 'decision_maker'
    )
    if decision_maker_count > 0:
        return {'status': 'completed', 'reason': f'已识别 {decision_maker_count} 位决策人，采购流程已摸清'}
    return {'status': 'pending', 'reason': '尚未识别决策人，采购流程未确认'}


def _check_sales_strategy(project):
    """opportunity_plan.sales_strategy：竞争分析非空 + 项目有 ≥1 个 ProjectWhyContext 则视为销售策略已形成

    无 sales_strategy 字段，用 competitive_analysis + ProjectWhyContext 综合推断。
    """
    has_competitive = _text_nonempty(getattr(project, 'competitive_analysis', None))
    has_value = ProjectWhyContext.query.filter_by(project_id=project.id).count() >= 1
    if has_competitive and has_value:
        return {'status': 'completed', 'reason': '已具备价值主张与竞争分析，销售策略已形成'}
    missing = []
    if not has_value:
        missing.append('价值主张')
    if not has_competitive:
        missing.append('竞争分析')
    return {'status': 'pending', 'reason': '销售策略要素缺失：' + '、'.join(missing)}


def _check_risk_assessment(project):
    """opportunity_plan.risk_assessment：已产生盲区行动待办则视为已做风险评估

    注：BlindSpotFinding 不是持久化模型，findings 来自 BlindSpotDetector.scan_project() 返回的
    dict 列表且未持久化到 project.findings。此处用 OpportunityTask(task_type='blind_spot') 作为
    代理指标：存在 blind_spot 待办即说明盲区扫描已执行并产生了可行动的发现。
    """
    tasks = getattr(project, 'tasks', None) or []
    blind_spot_count = sum(1 for t in tasks if getattr(t, 'task_type', None) == 'blind_spot')
    if blind_spot_count > 0:
        return {'status': 'completed', 'reason': f'已识别 {blind_spot_count} 项盲区行动待办'}
    return {'status': 'pending', 'reason': '暂无盲区扫描记录，未做风险评估'}


def _check_term_changes(project):
    """negotiation_records.term_changes：至少 1 条 feedback 的 total_changes > 0

    无 term_changes 字段，用 FeedbackRecord.total_changes 推断条款变更记录。
    """
    feedback_records = getattr(project, 'feedback_records', None) or []
    change_count = sum(1 for f in feedback_records if (getattr(f, 'total_changes', 0) or 0) > 0)
    if change_count > 0:
        return {'status': 'completed', 'reason': f'已有 {change_count} 条反馈包含条款变更'}
    return {'status': 'pending', 'reason': '暂无条款变更记录'}


def _check_win_confirmation(project):
    """close_report.win_confirmation：项目 sales_stage == closed_won 即视为已确认赢单"""
    if getattr(project, 'sales_stage', None) == 'closed_won':
        return {'status': 'completed', 'reason': '项目已进入赢单阶段'}
    return {'status': 'pending', 'reason': '项目尚未进入赢单阶段'}


def _check_loss_confirmation(project):
    """close_report.loss_confirmation：项目 sales_stage == closed_lost 即视为已确认丢单"""
    if getattr(project, 'sales_stage', None) == 'closed_lost':
        return {'status': 'completed', 'reason': '项目已进入丢单阶段'}
    return {'status': 'pending', 'reason': '项目尚未进入丢单阶段'}


def _auto_check_deliverable(project, deliverable_key):
    """根据 deliverable_key 查找并执行对应自动检查规则

    Args:
        project: Project 模型实例
        deliverable_key: 完整键（group_key.item_key）

    Returns:
        {'status': 'completed'|'pending', 'reason': str}
    """
    rule = _AUTO_CHECK_RULES.get(deliverable_key)
    if rule is None:
        return _default_auto_check(project)
    try:
        result = rule(project)
        if not isinstance(result, dict) or 'status' not in result:
            return _default_auto_check(project)
        return result
    except Exception as e:
        return {'status': 'pending', 'reason': f'自动检查异常: {e}'}


_AUTO_CHECK_RULES = {
    # Suspect 阶段
    'account_plan.company_structure': _check_company_structure,
    'account_plan.customer_strategy': _check_customer_strategy,
    'account_plan.sales_goals': _check_sales_goals,
    'suspect_evaluation.opportunity_scorecard': _check_opportunity_scorecard,
    'relationship_map.initial_map': _check_initial_map,
    # Identity 阶段
    'stakeholder_map.stakeholder_list': _check_stakeholder_list,
    'stakeholder_map.stakeholder_attributes': _check_stakeholder_attributes,
    'stakeholder_map.relationship_lines': _check_relationship_lines,
    'customer_requirements.pain_points': _check_pain_points,
    'customer_requirements.budget_range': _check_budget_range,
    'customer_requirements.procurement_process': _check_procurement_process,
    # Define 阶段
    'opportunity_plan.customer_background': _check_customer_background,
    'opportunity_plan.value_proposition': _check_value_proposition,
    'opportunity_plan.competitive_analysis': _check_competitive_analysis,
    'opportunity_plan.sales_strategy': _check_sales_strategy,
    'opportunity_plan.risk_assessment': _check_risk_assessment,
    'opportunity_plan.action_plan': _check_action_plan,
    # Confirm 阶段
    'negotiation_records.meeting_minutes': _check_meeting_minutes,
    'negotiation_records.objection_handling': _check_objection_handling,
    'negotiation_records.term_changes': _check_term_changes,
    # Close 阶段
    'close_report.win_confirmation': _check_win_confirmation,
    'close_report.loss_confirmation': _check_loss_confirmation,
}


# 里程碑命名说明：sales_stages/spec.md 使用 PM（Project Manager）命名，但本系统沿用 OM
# （Opportunity Manager）命名以保持与前端一致，避免破坏现有 UI；下方 pm_milestone 字段值
# 均为 OM 命名（如 OM10/OM20/OM30/OM40/OM70/OM80），请勿改为 PM 命名。
STAGE_DEFINITIONS = {
    'suspect': {
        'pm_milestone': 'OM10 Bid/No-Go',
        'core_objective': '识别和评估潜在销售商机，建立客户关系',
        'entry_conditions': ['项目已创建'],
        'exit_conditions': ['OM10 决策完成（Go/No-Go）'],
        'tasks': [
            {
                'name': '客户编排 (Account Orchestration)',
                'subtasks': [
                    '建立客户公司结构图（组织架构、决策流程、关键利益相关者）',
                    '(Optional) 绘制初始关系图谱（与各层级关系、影响力网络、沟通渠道）—— 随着销售推进持续完善',
                    '分析客户战略图（业务战略、市场定位、竞争优势）',
                    '设定销售目标与任务',
                ]
            },
            {
                'name': '线索识别 (Suspect Identification)',
                'subtasks': [
                    '从多个渠道识别潜在商机（市场调研、客户反馈、合作伙伴）',
                    '评估商机质量（战略契合度、预期收入规模、竞争强度、资源需求、成功概率）',
                ]
            },
            {
                'name': 'OM10 Bid/No-Go 决策',
                'subtasks': [
                    '确认潜在商机存在',
                    '评估是否值得投入资源',
                    '决定是否进入 Identity 阶段',
                    '如果 No-Go：销售保持商机在线索阶段并脱离接触',
                ]
            }
        ],
        'deliverables': _SUSPECT_DELIVERABLES,
    },
    'identity': {
        'pm_milestone': 'OM20 Go/No-Go',
        'core_objective': '确认商机真实性，识别关键干系人，理解客户需求',
        'entry_conditions': ['OM10 Go 决策完成'],
        'exit_conditions': ['OM20 决策完成，商机团队组建'],
        'tasks': [
            {
                'name': '干系人识别与分析',
                'subtasks': [
                    '识别客户方所有关键干系人（决策者、影响者、使用者、采购者）',
                    '分析每个干系人的角色类型（Mobilizer/Blocker/Guide/Champion/Skeptic/Coach）',
                    '评估每个干系人的决策影响力、支持度、紧迫感',
                    '完善关系图谱（汇报、协作、联盟、冲突）',
                ]
            },
            {
                'name': '客户需求确认',
                'subtasks': [
                    '深入了解客户业务痛点',
                    '确认预算范围和采购流程',
                    '识别竞争态势',
                    '确认客户决策流程和时间节点',
                ]
            },
            {
                'name': 'OM20 Go/No-Go 决策',
                'subtasks': [
                    '销售和售前获得客户 preliminary 利益理解',
                    '决定是否继续推进',
                    '组建商机团队',
                ]
            }
        ],
        'deliverables': _IDENTITY_DELIVERABLES,
    },
    'define': {
        'pm_milestone': 'OM30 销售策略评审 / OM40 投标批准',
        'core_objective': '选择合适的销售模式，制定解决方案和投标策略',
        'entry_conditions': ['OM20 Go 决策完成'],
        'exit_conditions': ['OM30 策略评审完成 / OM40 投标批准完成'],
        'tasks': [
            {
                'name': '销售模式选择',
                'subtasks': [
                    '评估商机复杂度',
                    '选择销售模式（Inside Sales / Prescriptive Pursuit / Value Solution Selling）',
                    '确定合作伙伴参与策略',
                ]
            },
            {
                'name': '解决方案设计',
                'subtasks': [
                    '基于客户需求设计解决方案',
                    '制定价值主张',
                    '准备 ROI 分析和 TCO 对比',
                    '设计客户成功计划 (CSP) 草稿',
                ]
            },
            {
                'name': 'OM30 销售策略评审',
                'subtasks': [
                    '内部利益相关者对齐销售策略',
                    '对齐价值实现时间',
                    '风险评估与应对',
                ]
            },
            {
                'name': 'OM40 投标批准',
                'subtasks': [
                    '准备综合提案（软件报价 + 工作说明书 + CSP）',
                    '内部审批（法律、财务、收入确认）',
                    '提交投标文件',
                ]
            }
        ],
        'deliverables': _DEFINE_DELIVERABLES,
    },
    'confirm': {
        'pm_milestone': 'OM40 投标批准 → OM70 赢单/丢单',
        'core_objective': '完成商务谈判，达成合同签署',
        'entry_conditions': ['OM40 投标批准完成'],
        'exit_conditions': ['合同已签署或谈判失败'],
        'tasks': [
            {
                'name': '商务谈判',
                'subtasks': [
                    '与客户关键决策者会议',
                    '呈现综合提案（遵循 CSP 结构）',
                    '处理客户异议',
                    '价格和条款谈判',
                ]
            },
            {
                'name': '合同准备',
                'subtasks': [
                    '准备合同文件',
                    '法律条款审核',
                    '财务条款确认',
                    '交付条款明确',
                ]
            },
            {
                'name': '干系人共识确认',
                'subtasks': [
                    '确保所有关键干系人支持方案',
                    '处理最后异议',
                    '确认决策流程完成',
                ]
            },
            {
                'name': 'OM70 赢单/丢单',
                'subtasks': [
                    '验证合同文件已签署',
                    '商机进入 Closed Won 或 Closed Lost',
                ]
            }
        ],
        'deliverables': _CONFIRM_DELIVERABLES,
    },
    'closed_won': {
        'pm_milestone': 'OM70 赢单 → OM80 过渡到实施',
        'core_objective': '正式关闭商机，过渡到实施团队',
        'entry_conditions': ['合同已签署'],
        'exit_conditions': ['商机正式关闭，已交接实施团队'],
        'tasks': [
            {
                'name': '赢单场景',
                'subtasks': [
                    '合同正式签署',
                    '商机状态更新为 Closed Won',
                    '过渡到实施团队（OM80）',
                    '总结经验教训',
                ]
            },
            {
                'name': '知识沉淀',
                'subtasks': [
                    '更新干系人数据库',
                    '记录竞争情报',
                    '归档项目文档',
                ]
            }
        ],
        'deliverables': _build_close_deliverables(is_won=True),
    },
    'closed_lost': {
        'pm_milestone': 'OM70 丢单 → 商机归档',
        'core_objective': '正式关闭商机，记录丢单原因并保持客户关系',
        'entry_conditions': ['谈判终止'],
        'exit_conditions': ['商机正式关闭，丢单原因已记录'],
        'tasks': [
            {
                'name': '丢单场景',
                'subtasks': [
                    '商机状态更新为 Closed Lost',
                    '记录丢单原因',
                    '分析改进点',
                    '保持客户关系（未来商机）',
                ]
            },
            {
                'name': '知识沉淀',
                'subtasks': [
                    '更新干系人数据库',
                    '记录竞争情报',
                    '归档项目文档',
                ]
            }
        ],
        'deliverables': _build_close_deliverables(is_won=False),
    },
}


# =============================================================================
# 服务层函数
# =============================================================================

def get_stage_definition(stage: str) -> Optional[dict]:
    """返回指定阶段的定义，包括任务清单和交付物清单

    Args:
        stage: 阶段键（suspect/identity/define/confirm/closed_won/closed_lost）

    Returns:
        阶段定义 dict；若 stage 不存在返回 None
    """
    return STAGE_DEFINITIONS.get(stage)


def _flatten_deliverable_keys(stage_definition: dict) -> list:
    """从阶段定义中展开所有交付物项的完整 key（格式：group_key.item_key）"""
    keys = []
    for group in stage_definition.get('deliverables', []):
        group_key = group['key']
        for item in group.get('items', []):
            keys.append(f"{group_key}.{item['key']}")
    return keys


def init_project_stage_deliverables(project_id: int, stage: str) -> int:
    """为指定阶段所有交付物项创建 is_completed=false 记录（若已存在则跳过）

    Args:
        project_id: 项目 ID
        stage: 阶段键

    Returns:
        新创建的记录数；若 stage 非法返回 0
    """
    stage_definition = get_stage_definition(stage)
    if not stage_definition:
        return 0

    all_keys = _flatten_deliverable_keys(stage_definition)
    if not all_keys:
        return 0

    # 查询当前已存在的记录键集合
    existing_records = StageDeliverable.query.filter_by(
        project_id=project_id, stage=stage
    ).all()
    existing_keys = {r.deliverable_key for r in existing_records}

    created_count = 0
    for key in all_keys:
        if key in existing_keys:
            continue
        record = StageDeliverable(
            project_id=project_id,
            stage=stage,
            deliverable_key=key,
            is_completed=False,
            completed_at=None,
        )
        db.session.add(record)
        created_count += 1

    if created_count > 0:
        db.session.commit()

    return created_count


def get_project_stage_deliverables(project_id: int, stage: Optional[str] = None) -> Optional[dict]:
    """返回阶段交付物清单及完成状态

    Args:
        project_id: 项目 ID
        stage: 阶段键；为 None 时使用项目当前 sales_stage

    Returns:
        阶段交付物详情 dict；项目不存在或阶段非法时返回 None
    """
    project = Project.query.get(project_id)
    if not project:
        return None

    if stage is None:
        stage = project.sales_stage

    stage_definition = get_stage_definition(stage)
    if not stage_definition:
        return None

    # 初始化该阶段所有交付物记录（防御性：缺失的补齐）
    init_project_stage_deliverables(project_id, stage)

    # 拉取该阶段所有记录，构建 key -> record 映射
    records = StageDeliverable.query.filter_by(
        project_id=project_id, stage=stage
    ).all()
    record_map = {r.deliverable_key: r for r in records}

    # 组装响应
    deliverables_response = []
    total_required = 0       # 非 Optional 项总数
    completed_required = 0   # 非 Optional 已完成项数

    for group in stage_definition.get('deliverables', []):
        group_key = group['key']
        group_response = {
            'key': group_key,
            'name': group['name'],
            'items': []
        }
        for item in group.get('items', []):
            full_key = f"{group_key}.{item['key']}"
            is_optional = bool(item.get('is_optional', False))
            record = record_map.get(full_key)
            is_completed = bool(record.is_completed) if record else False
            completed_at = record.completed_at.isoformat() if (record and record.completed_at) else None
            notes = record.notes if record else None
            attachments = _parse_attachments(record)

            # 自动检查：基于项目数据判定该交付物是否已具备内容
            auto_result = _auto_check_deliverable(project, full_key)
            auto_status = auto_result['status']
            auto_reason = auto_result['reason']
            effective_completed = is_completed or (auto_status == 'completed')

            group_response['items'].append({
                'key': full_key,
                'name': item['name'],
                'is_completed': is_completed,
                'completed_at': completed_at,
                'notes': notes,
                'is_optional': is_optional,
                'auto_status': auto_status,
                'auto_reason': auto_reason,
                'effective_completed': effective_completed,
                'attachments': attachments,
            })

            # 完成度统计：Optional 项不计入分母；基于综合状态判定
            if not is_optional:
                total_required += 1
                if effective_completed:
                    completed_required += 1

        deliverables_response.append(group_response)

    # 完成率：Optional 项不计入分母，结果保留一位小数
    if total_required > 0:
        completion_rate = round((completed_required / total_required) * 100, 1)
    else:
        completion_rate = 0.0

    return {
        'stage': stage,
        'pm_milestone': stage_definition.get('pm_milestone'),
        'core_objective': stage_definition.get('core_objective'),
        'entry_conditions': stage_definition.get('entry_conditions', []),
        'exit_conditions': stage_definition.get('exit_conditions', []),
        'tasks': stage_definition.get('tasks', []),
        'deliverables': deliverables_response,
        'completion_rate': completion_rate,
    }


def update_deliverable_status(
    project_id: int,
    stage: str,
    deliverable_key: str,
    is_completed: bool,
    notes: Optional[str] = None,
) -> Optional[dict]:
    """更新交付物状态和备注

    若记录不存在则创建（防御性）。
    completed_at 在 is_completed=True 时设为当前时间，False 时设为 None。

    Args:
        project_id: 项目 ID
        stage: 阶段键
        deliverable_key: 交付物完整键（group_key.item_key）
        is_completed: 是否完成
        notes: 备注（可选）

    Returns:
        更新后的交付物项 dict；项目或阶段非法时返回 None
    """
    project = Project.query.get(project_id)
    if not project:
        return None

    stage_definition = get_stage_definition(stage)
    if not stage_definition:
        return None

    all_keys = set(_flatten_deliverable_keys(stage_definition))
    if deliverable_key not in all_keys:
        return None

    # 查找已有记录
    record = StageDeliverable.query.filter_by(
        project_id=project_id, stage=stage, deliverable_key=deliverable_key
    ).first()

    now = datetime.utcnow() if is_completed else None

    if record is None:
        # 防御性：记录不存在则创建（即使 deliverable_key 不在定义中，也允许记录）
        record = StageDeliverable(
            project_id=project_id,
            stage=stage,
            deliverable_key=deliverable_key,
            is_completed=is_completed,
            completed_at=now,
            notes=notes,
        )
        db.session.add(record)
    else:
        record.is_completed = is_completed
        record.completed_at = now
        if notes is not None:
            record.notes = notes

    db.session.commit()

    return {
        'key': record.deliverable_key,
        'stage': record.stage,
        'is_completed': bool(record.is_completed),
        'completed_at': record.completed_at.isoformat() if record.completed_at else None,
        'notes': record.notes,
        'attachments': _parse_attachments(record),
    }


def check_stage_readiness(project_id: int, stage: Optional[str] = None) -> Optional[dict]:
    """执行阶段检查，返回检查报告

    Args:
        project_id: 项目 ID
        stage: 阶段键；为 None 时使用项目当前 sales_stage

    Returns:
        检查报告 dict；项目或阶段非法时返回 None
    """
    project = Project.query.get(project_id)
    if not project:
        return None

    if stage is None:
        stage = project.sales_stage

    stage_definition = get_stage_definition(stage)
    if not stage_definition:
        return None

    # 复用 get_project_stage_deliverables 获取完成状态
    stage_data = get_project_stage_deliverables(project_id, stage)
    if not stage_data:
        return None

    completion_rate_value = stage_data['completion_rate']

    # 统计非 Optional 项总数与已完成数（从 stage_data 重新聚合，确保一致）
    total_required = 0
    completed_required = 0
    pending_items = []
    for group in stage_data['deliverables']:
        for item in group['items']:
            if item['is_optional']:
                continue
            total_required += 1
            if item.get('effective_completed'):
                completed_required += 1
            else:
                pending_items.append({
                    'key': item['key'],
                    'name': item['name'],
                    'group_name': group['name'],
                })

    # 退出条件检查（简化实现：所有非 Optional 交付物完成则视为所有退出条件满足）
    all_required_completed = (total_required > 0 and completed_required == total_required)
    exit_conditions_check = [
        {'condition': cond, 'satisfied': all_required_completed}
        for cond in stage_definition.get('exit_conditions', [])
    ]
    all_exit_satisfied = all(c['satisfied'] for c in exit_conditions_check)

    # 推进建议
    if completion_rate_value < 80:
        can_advance = False
        recommendation = '暂缓推进，请优先完成未完成交付物'
    elif all_exit_satisfied:
        can_advance = True
        recommendation = '可以推进到下一阶段'
    else:
        can_advance = False
        recommendation = '完成度达标但退出条件未满足，请补充相关交付物'

    return {
        'stage': stage,
        'completion_rate': completion_rate_value,
        'total_items': total_required,
        'completed_items': completed_required,
        'pending_items': pending_items,
        'exit_conditions_check': exit_conditions_check,
        'recommendation': recommendation,
        'can_advance': can_advance,
        'ready': can_advance,
    }


# =============================================================================
# 商机阶段时间线
# =============================================================================

# 阶段 → 中文标签映射（与前端 salesStages.js 保持一致）
_STAGE_LABELS = {
    'suspect': '线索',
    'identity': '商机确认',
    'define': '方案定义',
    'confirm': '商务确认',
    'closed_won': '赢单',
    'closed_lost': '丢单',
}

# 旧版四阶段 → 新版五阶段映射（与 scripts/migrate_sales_stage_to_five.py 一致）
# StateChangeLog 中的 old_value/new_value 可能保留旧版值，读取时需统一映射
_LEGACY_STAGE_MAPPING = {
    'discovery': 'suspect',
    'qualification': 'identity',
    'proposal': 'define',
    'negotiation': 'confirm',
    # closed_won / closed_lost 保留不变
}


def _normalize_stage(stage):
    """将旧版阶段值映射到新版；新版值原样返回"""
    if not stage:
        return stage
    return _LEGACY_STAGE_MAPPING.get(stage, stage)


def get_project_stage_timeline(project_id):
    """获取项目阶段时间线 - 从 StateChangeLog 推导各阶段时间区间

    Returns:
        dict: {
            'project_id': int,
            'project_name': str,
            'current_stage': str,
            'stages': [
                {
                    'stage': str,
                    'label': str,
                    'om_milestone': str,
                    'started_at': str (ISO),
                    'ended_at': str (ISO) or None,
                    'duration_days': int or None,
                    'is_current': bool,
                    'core_objective': str,
                    'entry_conditions': list,
                    'exit_conditions': list,
                    'tasks': list,
                    'deliverables': list,
                    'completion_rate': float,
                    'completed_items': int,
                    'total_items': int,
                }
            ]
        }
    """
    project = Project.query.get_or_404(project_id)

    # 查询 sales_stage 变更日志（按时间升序）
    logs = StateChangeLog.query.filter_by(
        project_id=project_id, attribute_name='sales_stage'
    ).order_by(StateChangeLog.created_at.asc()).all()

    # 去重：过滤 old_value == new_value 的冗余记录（映射后再比较，避免旧版同义值被保留）
    logs = [
        log for log in logs
        if _normalize_stage(log.old_value) != _normalize_stage(log.new_value)
    ]

    # 构建阶段时间区间列表：(stage, started_at, ended_at)
    stage_intervals = []
    if not logs:
        # 无变更记录：从创建至今一直处于当前阶段
        stage_intervals.append((project.sales_stage, project.created_at, None))
    else:
        # 初始阶段（第一条日志的 old_value；为空时 fallback 到当前阶段）
        # 对旧版值统一映射到新版
        initial_stage = _normalize_stage(logs[0].old_value) or project.sales_stage
        stage_intervals.append((initial_stage, project.created_at, logs[0].created_at))
        # 后续每次变更产生的新阶段
        for i, log in enumerate(logs):
            started_at = log.created_at
            ended_at = logs[i + 1].created_at if (i + 1) < len(logs) else None
            stage_intervals.append((_normalize_stage(log.new_value), started_at, ended_at))

    now = datetime.utcnow()
    stages_response = []
    for stage, started_at, ended_at in stage_intervals:
        stage_definition = get_stage_definition(stage)
        if stage_definition is None:
            # 未知阶段（数据异常），跳过详情但保留时间区间
            om_milestone = None
            core_objective = None
            entry_conditions = []
            exit_conditions = []
            tasks = []
            deliverables = []
            completion_rate = 0.0
            completed_items = 0
            total_items = 0
        else:
            stage_data = get_project_stage_deliverables(project_id, stage)
            if stage_data is None:
                continue
            om_milestone = stage_definition.get('pm_milestone')
            core_objective = stage_definition.get('core_objective')
            entry_conditions = stage_definition.get('entry_conditions', [])
            exit_conditions = stage_definition.get('exit_conditions', [])
            tasks = stage_data.get('tasks', [])
            deliverables = stage_data.get('deliverables', [])
            completion_rate = stage_data.get('completion_rate', 0.0)
            # 从 deliverables 聚合 completed_items / total_items（仅非 Optional 项）
            total_items = 0
            completed_items = 0
            for group in deliverables:
                for item in group.get('items', []):
                    if item.get('is_optional'):
                        continue
                    total_items += 1
                    if item.get('effective_completed'):
                        completed_items += 1

        # 持续时长
        if ended_at is None:
            duration_days = (now - started_at).days
        else:
            duration_days = (ended_at - started_at).days

        stages_response.append({
            'stage': stage,
            'label': _STAGE_LABELS.get(stage, stage),
            'om_milestone': om_milestone,
            'started_at': started_at.isoformat() if started_at else None,
            'ended_at': ended_at.isoformat() if ended_at else None,
            'duration_days': duration_days,
            'is_current': stage == project.sales_stage,
            'core_objective': core_objective,
            'entry_conditions': entry_conditions,
            'exit_conditions': exit_conditions,
            'tasks': tasks,
            'deliverables': deliverables,
            'completion_rate': completion_rate,
            'completed_items': completed_items,
            'total_items': total_items,
        })

    # 按时间倒序排列（最新的阶段在前，最早的在后）
    stages_response.reverse()

    return {
        'project_id': project_id,
        'project_name': project.name,
        'current_stage': project.sales_stage,
        'stages': stages_response,
    }
