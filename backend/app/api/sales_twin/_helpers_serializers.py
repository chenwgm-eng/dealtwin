"""B2B销售数字孪生系统 - 序列化与上下文构建函数（从 _helpers.py 拆分）"""

import json
import logging

from app.models.database import (
    Project, Stakeholder, Contact, Customer, MeetingPlan,
    OpportunityTask, FeedbackRecord, ProjectStrategyItem,
    ProjectWhyContext, CompanyProfile, CompanyAttachment,
)

logger = logging.getLogger(__name__)


def _build_project_context(project, stakeholders, document_texts):
    """构建项目上下文信息（供LLM生成客户概览/价值主张/竞争分析共用）"""
    sk_lines = []
    for s in stakeholders:
        sk_lines.append(
            f"- {s.name}（{s.position or ''}，角色:{s.buyer_role or ''}，"
            f"支持度{s.support_level}/10，决策力{s.decision_power}/10）"
            f"诉求:{s.personal_agenda or '未知'}"
        )
    stakeholders_str = '\n'.join(sk_lines) if sk_lines else 'No stakeholders'

    doc_str = ''
    if document_texts:
        doc_str = '\n\n## 上传文档内容\n' + '\n---\n'.join(
            (t[:3000] for t in document_texts if t)
        )

    # 业务痛点字段注入洞察摘要（含战略要素/Why 上下文/竞争分析），保持字段名不变以兼容调用方
    pain_points_summary = _build_project_insight_summary(project.id)

    return f"""# 项目信息
- 项目名称: {project.name or ''}
- 客户名称: {project.customer_name or ''}
- 行业: {project.industry or ''}
- 公司愿景: {project.company_vision or ''}
- 业务痛点: {pain_points_summary or ''}
- 预算: {project.budget or '未知'}
- 销售阶段: {project.sales_stage or ''}

## 已知干系人
{stakeholders_str}
{doc_str}"""



def _build_project_insight_summary(project_id):
    """构建项目洞察摘要：拼接战略要素、Why 上下文、竞争分析为单字符串（供 LLM prompt 使用）。

    读取 ProjectStrategyItem（4 类）、ProjectWhyContext（3 类）、Project.competitive_analysis，
    合并为约 800-1200 字的文本。每个小节无数据时跳过；全部无数据或项目不存在时返回空字符串。

    Args:
        project_id: 项目 ID

    Returns:
        拼接后的摘要字符串；无数据时返回 ''
    """
    project = Project.query.get(project_id)
    if not project:
        return ''

    sections = []

    # 1. 战略要素 4 类
    type_labels = {
        'industry_trend': 'Industry Trend',
        'pain_point': 'Pain Point',
        'current_measure': 'Current Measure',
        'strategic_initiative': 'Strategic Initiative',
    }
    severity_map = {'high': 'High', 'medium': 'Medium', 'low': 'Low'}
    effectiveness_map = {'high': 'High', 'medium': 'Medium', 'low': 'Low', 'none': 'None'}

    for item_type, label in type_labels.items():
        items = (
            ProjectStrategyItem.query
            .filter_by(project_id=project_id, item_type=item_type)
            .order_by(ProjectStrategyItem.sort_order.asc())
            .all()
        )
        if not items:
            continue
        lines = []
        for idx, item in enumerate(items, 1):
            metadata = {}
            if item.metadata_json:
                try:
                    metadata = json.loads(item.metadata_json) or {}
                except (json.JSONDecodeError, TypeError):
                    metadata = {}
            name = item.name or ''
            desc = item.description or ''
            if item_type == 'industry_trend':
                impact = metadata.get('impact_area', '') if metadata else ''
                lines.append(f'{idx}. {name}：{desc}（影响范围：{impact}）')
            elif item_type == 'pain_point':
                severity_raw = metadata.get('severity', '') if metadata else ''
                severity_label = severity_map.get(severity_raw, severity_raw)
                lines.append(f'{idx}. {name}：{desc}（严重程度：{severity_label}）')
            elif item_type == 'current_measure':
                eff_raw = metadata.get('effectiveness', '') if metadata else ''
                eff_label = effectiveness_map.get(eff_raw, eff_raw)
                lines.append(f'{idx}. {name}：{desc}（有效性：{eff_label}）')
            else:  # strategic_initiative
                lines.append(f'{idx}. {name}：{desc}')
        sections.append(f'【{label}】\n' + '\n'.join(lines))

    # 2. Why 上下文 3 类
    why_labels = {'why': 'Why Change', 'why_now': 'Why Now', 'why_us': 'Why Us'}
    why_contexts = ProjectWhyContext.query.filter_by(project_id=project_id).all()
    if why_contexts:
        why_lines = []
        for ctx in why_contexts:
            ctx_type = ctx.context_type or ''
            label = why_labels.get(ctx_type, ctx_type)
            text = ctx.context_text or ''
            why_lines.append(f'- {label}：{text}')
        sections.append('【价值主张】\n' + '\n'.join(why_lines))

    # 3. 竞争分析
    ca = (getattr(project, 'competitive_analysis', None) or '').strip()
    if ca:
        sections.append(f'【竞争分析】\n{ca}')

    return '\n\n'.join(sections)



def _build_company_context():
    """构建我方公司上下文文本，用于注入 LLM prompt

    从 CompanyProfile 和 CompanyAttachment 读取公司介绍、产品介绍和附件文本。
    返回空字符串表示无公司信息。
    """
    profile = CompanyProfile.query.first()
    if not profile:
        return ''

    parts = []
    if profile.company_name:
        parts.append(f"## 我方公司：{profile.company_name}")
    if profile.company_intro:
        parts.append(f"### 公司介绍\n{profile.company_intro}")
    if profile.product_intro:
        parts.append(f"### 产品介绍\n{profile.product_intro}")

    # 附件文本（截断前 2000 字）
    attachments = CompanyAttachment.query.order_by(CompanyAttachment.uploaded_at.asc()).all()
    if attachments:
        texts = [a.extracted_text for a in attachments if a.extracted_text]
        if texts:
            combined = '\n\n---\n\n'.join(texts)[:2000]
            parts.append(f"### 产品资料附件\n{combined}")

    return '\n\n'.join(parts) if parts else ''



def suggestion_to_dict(s):
    """建议池条目转字典"""
    return {
        'id': s.id,
        'project_id': s.project_id,
        'content': s.content,
        'source': s.source,
        'source_context': json.loads(s.source_context) if s.source_context else None,
        'is_consumed': bool(s.is_consumed),
        'created_at': s.created_at.isoformat() if s.created_at else None,
        'updated_at': s.updated_at.isoformat() if s.updated_at else None,
    }



def task_to_dict(task, stakeholder_map=None):
    """待办事项转字典

    stakeholder_map: 可选的 {stakeholder_id: name} 映射，传入时避免循环内逐条查询数据库（N+1 优化）。
    """
    # 查找关联干系人
    stakeholder_name = ''
    if task.stakeholder_id:
        if stakeholder_map is not None:
            stakeholder_name = stakeholder_map.get(task.stakeholder_id, '') or ''
        else:
            sk = Stakeholder.query.get(task.stakeholder_id)
            if sk:
                stakeholder_name = sk.name

    # 解析多个关联干系人
    stakeholder_ids_list = []
    stakeholder_names = []
    if task.stakeholder_ids:
        try:
            stakeholder_ids_list = json.loads(task.stakeholder_ids)
        except (json.JSONDecodeError, TypeError):
            stakeholder_ids_list = []
    # 兼容：如果 stakeholder_ids 为空但 stakeholder_id 有值，回填
    if not stakeholder_ids_list and task.stakeholder_id:
        stakeholder_ids_list = [task.stakeholder_id]
    for sid in stakeholder_ids_list:
        if stakeholder_map is not None:
            name = stakeholder_map.get(sid)
            if name:
                stakeholder_names.append(name)
        else:
            sk = Stakeholder.query.get(sid)
            if sk:
                stakeholder_names.append(sk.name)

    # 解析 source_action
    source_action = None
    if task.source_action:
        try:
            source_action = json.loads(task.source_action)
        except (json.JSONDecodeError, TypeError):
            source_action = None

    return {
        'id': task.id,
        'project_id': task.project_id,
        'stakeholder_id': task.stakeholder_id,
        'stakeholder_ids': stakeholder_ids_list,
        'stakeholder_name': stakeholder_name,
        'stakeholder_names': stakeholder_names,
        'task_type': task.task_type,
        'title': task.title,
        'description': task.description,
        'action_brief': task.action_brief,
        'priority': task.priority,
        'status': task.status,
        'source': task.source,
        'source_action': source_action,
        'related_feedback': task.related_feedback,
        'due_date': task.due_date.isoformat() if task.due_date else None,
        'completed_at': task.completed_at.isoformat() if task.completed_at else None,
        'completion_note': task.completion_note,
        'created_at': task.created_at.isoformat() if task.created_at else None,
        'updated_at': task.updated_at.isoformat() if task.updated_at else None
    }



def feedback_record_to_dict(record):
    """反馈记录转字典"""
    try:
        related_task_ids = json.loads(record.related_task_ids) if record.related_task_ids else []
    except (json.JSONDecodeError, TypeError):
        related_task_ids = []
    try:
        attachments = json.loads(record.attachments) if record.attachments else []
    except (json.JSONDecodeError, TypeError):
        attachments = []
    return {
        'id': record.id,
        'project_id': record.project_id,
        'related_task_ids': related_task_ids,
        'related_meeting_plan_id': record.related_meeting_plan_id,
        'feedback_text': record.feedback_text,
        'parse_summary': record.parse_summary,
        'total_changes': record.total_changes,
        'attachments': attachments,
        'created_at': record.created_at.isoformat() if record.created_at else None
    }



def project_to_dict(project):
    """项目对象转字典"""
    pain_point_item = (
        ProjectStrategyItem.query
        .filter_by(project_id=project.id, item_type='pain_point')
        .order_by(ProjectStrategyItem.id)
        .first()
    )
    pain_points_summary = ''
    if pain_point_item:
        pp_name = pain_point_item.name or ''
        pp_desc = pain_point_item.description or ''
        pain_points_summary = (f'{pp_name}：{pp_desc}')[:80]
    return {
        'id': project.id,
        'name': project.name,
        'customer_id': project.customer_id,
        'customer_name': project.customer_name,
        'sales_stage': project.sales_stage,
        'budget': project.budget,
        'industry': project.industry,
        'company_vision': project.company_vision,
        'business_pain_points': project.business_pain_points,
        'customer_background': project.customer_background,
        'value_proposition': project.value_proposition,
        'competitive_analysis': project.competitive_analysis,
        'expected_close_date': project.expected_close_date.isoformat() if project.expected_close_date else None,
        'time_certainty': project.time_certainty,
        'budget_certainty': project.budget_certainty,
        'tendency': project.tendency,
        'sales_mode': project.sales_mode,
        'close_reason_category': project.close_reason_category,
        'close_reason_detail': project.close_reason_detail,
        'lessons_learned': project.lessons_learned,
        'graph_project_id': project.graph_project_id,
        'pain_points_summary': pain_points_summary,
        'created_at': project.created_at.isoformat() if project.created_at else None,
        'updated_at': project.updated_at.isoformat() if project.updated_at else None
    }



def _enum_str(val):
    """将 Enum 字段规范化为字符串（避免前端拿到 Enum 实例导致 select 无法匹配）"""
    if val is None:
        return None
    return val.value if hasattr(val, 'value') else str(val)



def _resolve_reports_to_from_contact(project_id, contact):
    """根据客户联系人的汇报关系，在项目干系人中查找对应的汇报对象

    客户联系人 contact.reports_to_id 指向上级 contact.id。
    在项目干系人中查找 contact_id == 上级 contact.id 的干系人，
    若找到则返回其 id，否则返回 None。
    """
    if not contact or not contact.reports_to_id:
        return None
    boss_contact_id = contact.reports_to_id
    boss_stakeholder = Stakeholder.query.filter_by(
        project_id=project_id, contact_id=boss_contact_id
    ).first()
    return boss_stakeholder.id if boss_stakeholder else None



def stakeholder_to_dict(stakeholder, reports_to_map=None, contact_map=None):
    """干系人对象转字典

    reports_to_map: 可选的 {stakeholder_id: name} 映射，用于解析 stakeholder.reports_to_id 的姓名（N+1 优化）。
    contact_map: 可选的 {contact_id: Contact} 映射，用于解析关联联系人及联系人的汇报对象姓名（N+1 优化）。
                 该映射中 Contact 的 reports_to_id 也应能在同一映射中找到，以解析 boss 联系人姓名。
    """
    # 查询汇报对象名称
    reports_to_name = None
    if stakeholder.reports_to_id:
        if reports_to_map is not None:
            reports_to_name = reports_to_map.get(stakeholder.reports_to_id)
        else:
            boss = Stakeholder.query.get(stakeholder.reports_to_id)
            if boss:
                reports_to_name = boss.name
    # 查询关联联系人信息
    contact_info = None
    if stakeholder.contact_id:
        if contact_map is not None:
            contact = contact_map.get(stakeholder.contact_id)
        else:
            contact = Contact.query.get(stakeholder.contact_id)
        if contact:
            reports_to_name = None
            if contact.reports_to_id:
                if contact_map is not None:
                    boss_ct = contact_map.get(contact.reports_to_id)
                else:
                    boss_ct = Contact.query.get(contact.reports_to_id)
                if boss_ct:
                    reports_to_name = boss_ct.name
            contact_info = {
                'id': contact.id,
                'name': contact.name,
                'department': contact.department,
                'position': contact.position,
                'phone': contact.phone,
                'email': contact.email,
                'customer_id': contact.customer_id,
                'reports_to_id': contact.reports_to_id,
                'reports_to_name': reports_to_name,
            }
    return {
        'id': stakeholder.id,
        'project_id': stakeholder.project_id,
        'name': stakeholder.name,
        'position': stakeholder.position,
        'level': stakeholder.level,
        'responsibilities': stakeholder.responsibilities,
        'personal_agenda': stakeholder.personal_agenda,
        'buyer_role': _enum_str(stakeholder.buyer_role),
        'social_style': _enum_str(stakeholder.social_style),
        'project_role': _enum_str(stakeholder.project_role),
        'status': stakeholder.status or 'pending',
        'contact_id': stakeholder.contact_id,
        'contact_info': contact_info,
        'reports_to_id': stakeholder.reports_to_id,
        'reports_to_name': reports_to_name,
        'decision_power': stakeholder.decision_power,
        'support_level': stakeholder.support_level,
        'urgency': stakeholder.urgency,
        'created_at': stakeholder.created_at.isoformat() if stakeholder.created_at else None,
        'updated_at': stakeholder.updated_at.isoformat() if stakeholder.updated_at else None
    }



def relationship_to_dict(relationship):
    """关系对象转字典"""
    return {
        'id': relationship.id,
        'project_id': relationship.project_id,
        'source_id': relationship.source_id,
        'target_id': relationship.target_id,
        'relationship_type': relationship.relationship_type,
        'influence_weight': relationship.influence_weight,
        'created_at': relationship.created_at.isoformat() if relationship.created_at else None,
        'updated_at': relationship.updated_at.isoformat() if relationship.updated_at else None
    }



def customer_to_dict(c, include_children=False, include_contacts=False, include_projects=False, include_all_projects=False):
    """客户对象转字典

    include_all_projects: 汇总所有子公司（递归）的项目，每个项目附带 customer_name
    """
    d = {
        'id': c.id,
        'name': c.name,
        'parent_id': c.parent_id,
        # 工商注册信息
        'unified_credit_code': c.unified_credit_code,
        'registered_capital': c.registered_capital,
        'establish_date': c.establish_date.isoformat() if c.establish_date else None,
        'legal_representative': c.legal_representative,
        'enterprise_type': c.enterprise_type,
        'operating_status': c.operating_status,
        'business_scope': c.business_scope,
        # 业务信息
        'industry': c.industry,
        'core_products': c.core_products,
        'company_history': c.company_history,
        'scale_employees': c.scale_employees,
        'scale_revenue': c.scale_revenue,
        'branch_count': c.branch_count,
        # 工商联系人
        'business_contact_name': c.business_contact_name,
        'business_contact_phone': c.business_contact_phone,
        'business_contact_email': c.business_contact_email,
        # 地址
        'registered_address': c.registered_address,
        'office_address': c.office_address,
        # 客户概览
        'customer_background': c.customer_background,
        'created_at': c.created_at.isoformat() if c.created_at else None,
        'updated_at': c.updated_at.isoformat() if c.updated_at else None,
    }
    if include_children:
        d['children'] = [customer_to_dict(ch, include_projects=include_projects) for ch in (c.children or [])]
    if include_contacts:
        # 共享 customer_cache：当前客户 c 已在内存中，直接预填；遍历联系人时
        # _compute_interaction_stats 内的 Customer.query.get(ct.customer_id) 可命中此缓存。
        customer_cache = {c.id: c}
        d['contacts'] = [contact_to_dict(ct, include_interaction=include_all_projects, customer_cache=customer_cache) for ct in (c.contacts or [])]
    if include_projects:
        d['projects'] = [{
            'id': p.id, 'name': p.name, 'sales_stage': p.sales_stage,
            'budget': p.budget,
            'expected_close_date': p.expected_close_date.isoformat() if p.expected_close_date else None,
        } for p in (c.projects or [])]
    if include_all_projects:
        # 递归汇总所有子公司项目，附带客户名
        all_projects = []
        def _collect(node):
            for p in (node.projects or []):
                all_projects.append({
                    'id': p.id, 'name': p.name, 'sales_stage': p.sales_stage,
                    'budget': p.budget,
                    'expected_close_date': p.expected_close_date.isoformat() if p.expected_close_date else None,
                    'customer_id': node.id,
                    'customer_name': node.name,
                })
            for ch in (node.children or []):
                _collect(ch)
        _collect(c)
        d['all_projects'] = all_projects
    return d



def _compute_interaction_stats(ct, customer_cache=None):
    """统计联系人的拜访预案/任务/反馈记录数（不含状态判定）

    customer_cache: 可选的 {customer_id: Customer} 映射，传入时避免同一客户下多个联系人
                    重复 Customer.query.get 产生 N+1（customer_to_dict 内共享此缓存）。
    """
    empty_stats = {'plans': 0, 'tasks': 0, 'feedbacks': 0, 'completed_tasks': 0}
    if not ct or not ct.customer_id:
        return empty_stats

    if customer_cache is not None and ct.customer_id in customer_cache:
        customer = customer_cache[ct.customer_id]
    else:
        customer = Customer.query.get(ct.customer_id)
        if customer_cache is not None:
            customer_cache[ct.customer_id] = customer
    if not customer:
        return empty_stats

    project_ids = set()
    def _collect_projects(node):
        for p in (node.projects or []):
            project_ids.add(p.id)
        for ch in (node.children or []):
            _collect_projects(ch)
    _collect_projects(customer)

    if not project_ids:
        return empty_stats

    contacts_name = (ct.name or '').strip()
    contacts_pos = (ct.position or '').strip()
    matched_stakeholder_ids = set()
    # TODO: 批量优化 —— 按联系人姓名逐条查询 Stakeholder，跨联系人循环时存在 N+1
    stakeholders = Stakeholder.query.filter(
        Stakeholder.project_id.in_(project_ids),
        Stakeholder.name == contacts_name
    ).all()
    for s in stakeholders:
        if not contacts_pos or not s.position or s.position.strip() == contacts_pos:
            matched_stakeholder_ids.add(s.id)

    stats = dict(empty_stats)
    if not matched_stakeholder_ids:
        return stats

    sid_list = list(matched_stakeholder_ids)

    # TODO: 批量优化 —— MeetingPlan / OpportunityTask / FeedbackRecord 均按联系人
    # 匹配的 stakeholder_id 过滤，跨联系人循环时存在 N+1；如需优化可改为一次性
    # 拉取客户下所有相关记录后在内存中按 stakeholder_id 分组。
    # 当前 N+1 暂可接受：批量优化需重构 API 响应格式（按联系人聚合改为按客户聚合后分发），
    # 且 customer_cache 已消除最频繁的 Customer.query.get 重复查询。
    plans = MeetingPlan.query.filter(
        MeetingPlan.project_id.in_(project_ids),
        MeetingPlan.stakeholder_id.in_(sid_list)
    ).all()
    extra_plans = MeetingPlan.query.filter(
        MeetingPlan.project_id.in_(project_ids),
        ~MeetingPlan.stakeholder_id.in_(sid_list)
    ).all()
    for p in extra_plans:
        if p.stakeholder_ids:
            try:
                ids_json = json.loads(p.stakeholder_ids)
                if isinstance(ids_json, list) and any(sid in matched_stakeholder_ids for sid in ids_json):
                    plans.append(p)
            except Exception:
                pass
    stats['plans'] = len(plans)

    tasks = OpportunityTask.query.filter(
        OpportunityTask.project_id.in_(project_ids),
        OpportunityTask.stakeholder_id.in_(sid_list)
    ).all()
    extra_tasks = OpportunityTask.query.filter(
        OpportunityTask.project_id.in_(project_ids),
        ~OpportunityTask.stakeholder_id.in_(sid_list)
    ).all()
    for t in extra_tasks:
        if t.stakeholder_ids:
            try:
                ids_json = json.loads(t.stakeholder_ids)
                if isinstance(ids_json, list) and any(sid in matched_stakeholder_ids for sid in ids_json):
                    tasks.append(t)
            except Exception:
                pass
    stats['tasks'] = len(tasks)
    stats['completed_tasks'] = len([t for t in tasks if t.status == 'completed'])

    plan_ids = [p.id for p in plans]
    task_ids = [t.id for t in tasks]
    feedback_count = 0
    if plan_ids:
        feedback_count += FeedbackRecord.query.filter(
            FeedbackRecord.project_id.in_(project_ids),
            FeedbackRecord.related_meeting_plan_id.in_(plan_ids)
        ).count()
    if task_ids:
        candidate_feedbacks = FeedbackRecord.query.filter(
            FeedbackRecord.project_id.in_(project_ids),
            FeedbackRecord.related_task_ids.isnot(None)
        ).all()
        seen_fb_ids = set()
        for fb in candidate_feedbacks:
            if fb.id in seen_fb_ids:
                continue
            if fb.related_task_ids:
                try:
                    rel_ids = json.loads(fb.related_task_ids)
                    if isinstance(rel_ids, list) and any(tid in task_ids for tid in rel_ids):
                        feedback_count += 1
                        seen_fb_ids.add(fb.id)
                except Exception:
                    pass
    stats['feedbacks'] = feedback_count
    return stats



def compute_contact_interaction_status(ct, customer_cache=None):
    """计算联系人互动触达状态：red(未联系) / yellow(有联系但不理想) / green(联系顺畅)

    优先级：
    1. 手工覆盖（interaction_status_override 非空时直接返回）
    2. 自动计算（基于联系记录统计）

    自动计算判定规则：
    - red：无任何拜访预案/任务/反馈记录
    - green：有反馈记录（说明拜访后有结果回填）
    - yellow：有拜访预案/任务但无反馈

    customer_cache: 透传给 _compute_interaction_stats，用于跨联系人共享 Customer 查询。
    """
    empty_stats = {'plans': 0, 'tasks': 0, 'feedbacks': 0, 'completed_tasks': 0}
    if not ct or not ct.customer_id:
        return {'status': 'red', 'stats': empty_stats}

    # 始终计算统计信息（即使手工覆盖也返回统计）
    stats = _compute_interaction_stats(ct, customer_cache=customer_cache)

    # 手工覆盖优先
    if ct.interaction_status_override in ('red', 'yellow', 'green'):
        return {'status': ct.interaction_status_override, 'stats': stats, 'manual': True}

    # 自动判定
    total_activity = stats['plans'] + stats['tasks'] + stats['feedbacks']
    if total_activity == 0:
        status = 'red'
    elif stats['feedbacks'] > 0:
        status = 'green'
    else:
        status = 'yellow'

    return {'status': status, 'stats': stats}



def contact_to_dict(ct, include_interaction=False, include_stakeholders=False, customer_cache=None):
    """联系人对象转字典

    include_interaction: 是否计算互动触达状态（较重，仅在客户详情接口启用）
    include_stakeholders: 是否附加该联系人作为干系人参与的商机列表
    customer_cache: 透传给 compute_contact_interaction_status 的 {customer_id: Customer} 缓存，
                    用于在 customer_to_dict 内跨联系人共享 Customer 查询（N+1 优化）。
    """
    d = {
        'id': ct.id,
        'customer_id': ct.customer_id,
        'name': ct.name,
        'department': ct.department,
        'position': ct.position,
        'phone': ct.phone,
        'email': ct.email,
        'address': ct.address,
        'remark': ct.remark,
        'reports_to_id': ct.reports_to_id,
        'source': ct.source or 'manual',
        'created_at': ct.created_at.isoformat() if ct.created_at else None,
        'updated_at': ct.updated_at.isoformat() if ct.updated_at else None,
    }
    if include_interaction:
        interaction = compute_contact_interaction_status(ct, customer_cache=customer_cache)
        d['interaction_status'] = interaction['status']
        d['interaction_stats'] = interaction['stats']
        d['interaction_manual'] = interaction.get('manual', False)
    if include_stakeholders:
        # 反向查询该联系人作为干系人参与的所有商机
        # 按 project_id 去重：同一项目下可能存在多条 stakeholder 记录（脏数据或历史遗留），
        # 仅保留每个项目最新更新的一条，避免前端"参与商机"列表出现重复项目
        stakes = Stakeholder.query.filter_by(contact_id=ct.id).order_by(Stakeholder.updated_at.desc()).all()
        # 批量查询所有需要的 Project，避免在循环内逐条 Project.query.get 产生 N+1
        project_ids = {s.project_id for s in stakes if s.project_id}
        projects_map = {p.id: p for p in Project.query.filter(Project.id.in_(project_ids)).all()} if project_ids else {}
        seen_project_ids = set()
        opp_list = []
        for s in stakes:
            if not s.project_id or s.project_id in seen_project_ids:
                continue
            proj = projects_map.get(s.project_id)
            if not proj:
                continue
            seen_project_ids.add(s.project_id)
            opp_list.append({
                'stakeholder_id': s.id,
                'project_id': proj.id,
                'project_name': proj.name,
                'budget': proj.budget,
                'expected_close_date': proj.expected_close_date.isoformat() if proj.expected_close_date else None,
                'sales_stage': proj.sales_stage,
                'buyer_role': _enum_str(s.buyer_role),
                'project_role': _enum_str(s.project_role),
                'support_level': s.support_level,
                'decision_power': s.decision_power,
                'urgency': s.urgency,
                'status': s.status or 'pending',
            })
        # 按更新时间倒序（最近修改的在前）
        d['opportunities'] = opp_list
    return d
