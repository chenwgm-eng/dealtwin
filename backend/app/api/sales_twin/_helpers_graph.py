"""B2B销售数字孪生系统 - 图谱构建函数（从 _helpers.py 拆分）"""

import json
import re
import logging

from app.models.database import ProjectStrategyItem, ProjectWhyContext, Stakeholder
# 核心工具函数仍在 _helpers.py 中定义；此处依赖的 _now_iso_z / _extract_json_object
# 在 _helpers.py 中先于本模块的导入语句被定义，因此 from ._helpers import 可安全解析
# （_helpers.py 作为 re-export hub 始终先被加载）。
from ._helpers import _now_iso_z, _extract_json_object

logger = logging.getLogger(__name__)


# B2B核心实体类型（只保留这些类型的节点，过滤掉杂乱实体）
# 包含Organization以支持SVS公司结构图（组织层级架构）
B2B_CORE_NODE_TYPES = {
    # SVS 核心类型（6 个）
    'StrategicInitiative', 'BusinessGoal', 'PainPoint',
    'DecisionStage', 'Stakeholder', 'Organization',
    # Challenge Sales 扩展类型（5 个）
    'IndustryTrend', 'CurrentMeasure', 'ProjectContext',
    'StakeholderAgenda', 'Task'
}

# 实体类型中文标签
NODE_TYPE_LABELS = {
    # SVS 核心类型（6 个）
    'StrategicInitiative': 'Strategic Initiative',
    'BusinessGoal': 'Business Goal',
    'PainPoint': 'Pain Point',
    'DecisionStage': 'Decision Stage',
    'Stakeholder': 'Stakeholder',
    'Organization': 'Organization',
    'Person': 'Person',
    # Challenge Sales 扩展类型（5 个）
    'IndustryTrend': 'Industry Trend',
    'CurrentMeasure': 'Current Measure',
    'ProjectContext': 'Project Context',
    'StakeholderAgenda': 'Stakeholder Agenda',
    'Task': 'Task',
}

# 关系类型中文标签
EDGE_TYPE_LABELS = {
    # 核心关系
    'REPORTS_TO': 'Reports To',
    'DRIVES_GOAL': 'Drives Goal',
    'ADDRESSES_PAIN': 'Addresses Pain',
    'SUPPORTS': 'Supports',
    'OPPOSES': 'Opposes',
    'RESPONSIBLE_FOR': 'Responsible For',
    'APPROVES': 'Approves',
    'PARTICIPATES_IN': 'Participates In',
    'INFLUENCES': 'Influences',
    'OWNS_INITIATIVE': 'Owns Initiative',
    'PROCUREMENT_METHOD': 'Procurement Method',
    'PART_OF': 'Part Of',
    'HAS_ROLE': 'Has Role',
    'WORKS_AT': 'Works At',
    'LOCATED_IN': 'Located In',
    'RELATED_TO': 'Related To',
    'RELATED': 'Related',
    # Challenge Sales 扩展关系（10 个）
    'DRIVEN_BY_TREND': 'Driven By Trend',
    'GOAL_ALIGNS_INITIATIVE': 'Goal Aligns Initiative',
    'MEASURE_ADDRESSES_PAIN': 'Measure Addresses Pain',
    'ALIGNS_WITH': 'Aligns With',
    'TEACHING_REFRAMES': 'Teaching Reframes',
    'ASSIGNED_TO': 'Assigned To',
    'CONTRIBUTES_TO': 'Contributes To',
    'HAS_AGENDA': 'Has Agenda',
    'ADDRESSES_AGENDA': 'Addresses Agenda',
    'TARGETS_AGENDA': 'Targets Agenda',
}


def _filter_b2b_graph(graph_data):
    """过滤图谱数据，只保留B2B核心实体类型和它们之间的边"""
    if not graph_data:
        return graph_data

    nodes = graph_data.get('nodes', []) or []
    edges = graph_data.get('edges', []) or []

    # 过滤节点：只保留核心类型
    def get_node_type(node):
        labels = node.get('labels') or []
        for l in labels:
            if l in B2B_CORE_NODE_TYPES:
                return l
        # 兼容：有些节点用 entity_type 字段
        et = node.get('entity_type') or node.get('type')
        if et in B2B_CORE_NODE_TYPES:
            return et
        return None

    filtered_nodes = []
    kept_uuids = set()
    for n in nodes:
        nt = get_node_type(n)
        if nt:
            # 注入中文标签到节点属性
            n.setdefault('attributes', {})
            if 'node_type_label' not in n['attributes']:
                n['attributes']['node_type_label'] = NODE_TYPE_LABELS.get(nt, nt)
            n['attributes']['node_type'] = nt
            kept_uuids.add(n.get('uuid'))
            filtered_nodes.append(n)

    # 过滤边：两端节点都在保留集合中
    filtered_edges = []
    for e in edges:
        src = e.get('source_node_uuid')
        tgt = e.get('target_node_uuid')
        if src in kept_uuids and tgt in kept_uuids:
            # 注入中文标签
            etype = e.get('name') or e.get('fact_type') or ''
            if 'edge_type_label' not in (e.get('attributes') or {}):
                e.setdefault('attributes', {})
                e['attributes']['edge_type_label'] = EDGE_TYPE_LABELS.get(etype, etype)
            filtered_edges.append(e)

    merged = dict(graph_data)
    merged['nodes'] = filtered_nodes
    merged['edges'] = filtered_edges
    merged['node_count'] = len(filtered_nodes)
    merged['edge_count'] = len(filtered_edges)
    return merged



def _build_stakeholder_graph(stakeholders):
    """把数据库干系人转成图谱节点格式，并基于职位自动生成关系边。

    Returns:
        (nodes, edges) 元组
    """
    if not stakeholders:
        return [], []

    nodes = []
    edges = []
    now = _now_iso_z()

    # 角色中文标签
    role_labels = {
        'champion': 'Champion',
        'guide': 'Guide',
        'skeptic': 'Skeptic',
        'coach': 'Coach',
        'mobilizer': 'Mobilizer',
        'blocker': 'Blocker',
    }

    for s in stakeholders:
        node_name = s.name
        nodes.append({
            'uuid': f'stakeholder_{s.id}',
            'name': node_name,
            'labels': ['Stakeholder'],
            'summary': f'{s.position or "Unknown Position"} - {role_labels.get(s.buyer_role, "Uncategorized")}',
            'attributes': {
                'name': node_name,
                'full_name': node_name,
                'position': s.position or '',
                'buyer_role': s.buyer_role or '',
                'role_label': role_labels.get(s.buyer_role, 'Uncategorized'),
                'decision_power': s.decision_power,
                'support_level': s.support_level,
                'urgency': s.urgency,
                'responsibilities': s.responsibilities or '',
                'personal_agenda': s.personal_agenda or '',
                'source': 'database',
            },
            'created_at': now,
        })

    # 基于职位自动生成 REPORTS_TO 关系
    # 一把手关键词（精确匹配，排除带"各"等泛指词的职位）
    # Note: these keywords match Chinese position titles stored in the database
    boss_keywords = ['局长', '总经理', '总裁', 'CEO', '行长', '书记', '司长', '厅长', '馆长']
    # 判断是否为真正的一把手
    def is_real_boss(s):
        if not s.position:
            return False
        pos = s.position
        # 排除泛指（"各处室..."等）
        if pos.startswith('各') or '各' in pos[:2]:
            return False
        # 排除副手
        if '副' in pos:
            return False
        return any(kw in pos for kw in boss_keywords)

    bosses = [s for s in stakeholders if is_real_boss(s)]
    # 如果没有精确匹配的一把手，退回用 champion + 高决策力
    if not bosses:
        bosses = [s for s in stakeholders
                  if s.buyer_role == 'champion' and s.decision_power >= 8
                  and not (s.position and (s.position.startswith('各') or '副' in s.position))]

    # 找副手（职位含"副"）
    deputies = [s for s in stakeholders
                if '副' in (s.position or '')
                and s not in bosses]
    # 技术负责人
    tech_leads = [s for s in stakeholders
                  if s.buyer_role == 'skeptic'
                  and s not in bosses and s not in deputies]

    # 只取第一个一把手作为汇报对象（避免多boss导致关系混乱）
    boss = bosses[0] if bosses else None

    for deputy in deputies:
        if boss and deputy.id != boss.id:
            edges.append(_make_edge(deputy.name, boss.name, 'REPORTS_TO',
                                   f'{deputy.position or deputy.name} reports to {boss.position or boss.name}',
                                   source_uuid=f'stakeholder_{deputy.id}',
                                   target_uuid=f'stakeholder_{boss.id}'))

    for tech in tech_leads:
        # 技术负责人向一把手汇报（如果有副手，向分管副手汇报）
        target = deputies[0] if deputies else boss
        if target and tech.id != target.id:
            edges.append(_make_edge(tech.name, target.name, 'REPORTS_TO',
                                   f'{tech.position or tech.name} reports to {target.position or target.name}',
                                   source_uuid=f'stakeholder_{tech.id}',
                                   target_uuid=f'stakeholder_{target.id}'))

    # 其他干系人向最近的上级汇报
    reported_ids = {s.id for s in bosses + deputies + tech_leads}
    others = [s for s in stakeholders if s.id not in reported_ids]
    for other in others:
        # 优先向副手汇报，其次向一把手
        target = deputies[0] if deputies else boss
        if target and other.id != target.id:
            edges.append(_make_edge(other.name, target.name, 'REPORTS_TO',
                                   f'{other.position or other.name} reports to {target.position or target.name}',
                                   source_uuid=f'stakeholder_{other.id}',
                                   target_uuid=f'stakeholder_{target.id}'))

    return nodes, edges



def _make_edge(source_name, target_name, edge_type, fact, source_uuid=None, target_uuid=None):
    """构造一条关系边"""
    now = _now_iso_z()
    return {
        'uuid': f'edge_{source_name}_{edge_type}_{target_name}',
        'name': edge_type,
        'fact': fact,
        'fact_type': edge_type,
        'source_node_name': source_name,
        'target_node_name': target_name,
        'source_node_uuid': source_uuid or f'stakeholder_{source_name}',
        'target_node_uuid': target_uuid or f'stakeholder_{target_name}',
        'attributes': {
            'edge_type': edge_type,
            'fact': fact,
        },
        'created_at': now,
    }



def _merge_stakeholders_into_graph(graph_data, stakeholder_nodes, stakeholder_edges):
    """把数据库干系人合并到Zep图谱数据中，避免重复节点。"""
    if not graph_data:
        return graph_data

    nodes = graph_data.get('nodes', []) or []
    edges = graph_data.get('edges', []) or []

    # 获取Zep图谱已有的节点名称
    existing_names = {n.get('name') for n in nodes if n.get('name')}

    # 只添加Zep图谱里不存在的干系人节点
    added_nodes = []
    for sn in stakeholder_nodes:
        if sn.get('name') not in existing_names:
            added_nodes.append(sn)
            existing_names.add(sn.get('name'))

    # 添加干系人之间的关系边
    existing_edge_keys = {
        (e.get('source_node_name'), e.get('name'), e.get('target_node_name'))
        for e in edges
    }
    added_edges = []
    for se in stakeholder_edges:
        key = (se.get('source_node_name'), se.get('name'), se.get('target_node_name'))
        if key not in existing_edge_keys:
            added_edges.append(se)
            existing_edge_keys.add(key)

    merged = dict(graph_data)
    merged['nodes'] = nodes + added_nodes
    merged['edges'] = edges + added_edges
    merged['node_count'] = len(merged['nodes'])
    merged['edge_count'] = len(merged['edges'])
    return merged



def _build_industry_trend_nodes(project):
    """从 ProjectStrategyItem 表查询行业趋势，生成 IndustryTrend 节点列表。

    查询 item_type='industry_trend' 的条目，按 sort_order 排序，每条转换为节点。
    表无数据时返回空列表（不 fallback 到文本切分）。
    """
    if not project or not getattr(project, 'id', None):
        return []

    items = (
        ProjectStrategyItem.query
        .filter_by(project_id=project.id, item_type='industry_trend')
        .order_by(ProjectStrategyItem.sort_order.asc())
        .all()
    )
    if not items:
        return []

    nodes = []
    for item in items:
        # 解析 metadata_json 中的扩展字段
        metadata = {}
        if item.metadata_json:
            try:
                metadata = json.loads(item.metadata_json) or {}
            except (json.JSONDecodeError, TypeError):
                metadata = {}
        node_name = item.name or ''
        created_at_str = (item.created_at.isoformat() + 'Z') if item.created_at else _now_iso_z()
        nodes.append({
            'uuid': f'industry_trend_{item.id}',
            'name': node_name,
            'labels': ['IndustryTrend'],
            'summary': f'Industry Trend: {node_name}',
            'attributes': {
                'trend_name': node_name,
                'trend_description': item.description or '',
                'impact_area': metadata.get('impact_area', '') if metadata else '',
                'source': 'database',
            },
            'created_at': created_at_str,
        })
    return nodes



def _build_current_measure_nodes(project):
    """从 ProjectStrategyItem 表查询当前措施，生成 CurrentMeasure 节点列表。

    查询 item_type='current_measure' 的条目，按 sort_order 排序，每条转换为节点。
    表无数据时返回空列表（不 fallback 到文本切分）。
    """
    if not project or not getattr(project, 'id', None):
        return []

    items = (
        ProjectStrategyItem.query
        .filter_by(project_id=project.id, item_type='current_measure')
        .order_by(ProjectStrategyItem.sort_order.asc())
        .all()
    )
    if not items:
        return []

    nodes = []
    for item in items:
        # 解析 metadata_json 中的扩展字段
        metadata = {}
        if item.metadata_json:
            try:
                metadata = json.loads(item.metadata_json) or {}
            except (json.JSONDecodeError, TypeError):
                metadata = {}
        node_name = item.name or ''
        created_at_str = (item.created_at.isoformat() + 'Z') if item.created_at else _now_iso_z()
        nodes.append({
            'uuid': f'current_measure_{item.id}',
            'name': node_name,
            'labels': ['CurrentMeasure'],
            'summary': f'Current Measure: {node_name}',
            'attributes': {
                'measure_name': node_name,
                'measure_description': item.description or '',
                'effectiveness': metadata.get('effectiveness', '未知') if metadata else '未知',
                'source': 'database',
            },
            'created_at': created_at_str,
        })
    return nodes



def _build_pain_point_nodes(project):
    """从 ProjectStrategyItem 表查询痛点，生成 PainPoint 节点列表。

    查询 item_type='pain_point' 的条目，按 sort_order 排序，每条转换为节点。
    表无数据时返回空列表（不依赖 Zep 抽取，不 fallback 到文本切分）。
    """
    if not project or not getattr(project, 'id', None):
        return []

    items = (
        ProjectStrategyItem.query
        .filter_by(project_id=project.id, item_type='pain_point')
        .order_by(ProjectStrategyItem.sort_order.asc())
        .all()
    )
    if not items:
        return []

    nodes = []
    for item in items:
        # 解析 metadata_json 中的扩展字段
        metadata = {}
        if item.metadata_json:
            try:
                metadata = json.loads(item.metadata_json) or {}
            except (json.JSONDecodeError, TypeError):
                metadata = {}
        node_name = item.name or ''
        created_at_str = (item.created_at.isoformat() + 'Z') if item.created_at else _now_iso_z()
        nodes.append({
            'uuid': f'pain_point_{item.id}',
            'name': node_name,
            'labels': ['PainPoint'],
            'summary': f'Pain Point: {node_name}',
            'attributes': {
                'pain_name': node_name,
                'pain_description': item.description or '',
                'severity': metadata.get('severity', '') if metadata else '',
                'source': 'database',
            },
            'created_at': created_at_str,
        })
    return nodes



def _build_strategic_initiative_from_background(project):
    """从 ProjectStrategyItem 表查询战略举措，生成 StrategicInitiative 节点列表。

    查询 item_type='strategic_initiative' 的条目，按 sort_order 排序，每条转换为节点。
    与 Zep 抽取的 StrategicInitiative 节点的去重在 get_project_graph 合并阶段处理（按 name 字段去重）。
    表无数据时返回空列表（不 fallback 到文本切分）。
    """
    if not project or not getattr(project, 'id', None):
        return []

    items = (
        ProjectStrategyItem.query
        .filter_by(project_id=project.id, item_type='strategic_initiative')
        .order_by(ProjectStrategyItem.sort_order.asc())
        .all()
    )
    if not items:
        return []

    nodes = []
    for item in items:
        # 解析 metadata_json 中的扩展字段
        metadata = {}
        if item.metadata_json:
            try:
                metadata = json.loads(item.metadata_json) or {}
            except (json.JSONDecodeError, TypeError):
                metadata = {}
        node_name = item.name or ''
        created_at_str = (item.created_at.isoformat() + 'Z') if item.created_at else _now_iso_z()
        nodes.append({
            'uuid': f'strategic_initiative_bg_{item.id}',
            'name': node_name,
            'labels': ['StrategicInitiative'],
            'summary': f'Strategic Initiative (from background): {node_name}',
            'attributes': {
                'initiative_name': node_name,
                'initiative_description': item.description or '',
                'time_horizon': metadata.get('time_horizon', '未知') if metadata else '未知',
                'source': 'database_background',
            },
            'created_at': created_at_str,
        })
    return nodes



def _build_project_context_nodes(project):
    """从 ProjectWhyContext 表查询 WHY 上下文，生成 ProjectContext 节点列表。

    查询该项目下所有 ProjectWhyContext 条目（why/why_now/why_us 三类），
    每条转换为节点。表无数据时返回空列表（不 fallback 到文本切分）。
    """
    if not project or not getattr(project, 'id', None):
        return []

    contexts = ProjectWhyContext.query.filter_by(project_id=project.id).all()
    if not contexts:
        return []

    # context_type → 中文名映射
    type_name_map = {'why': 'Why Change', 'why_now': 'Why Now', 'why_us': 'Why Us'}

    nodes = []
    for ctx in contexts:
        ctx_type = ctx.context_type or ''
        name = type_name_map.get(ctx_type, ctx_type)
        created_at_str = (ctx.created_at.isoformat() + 'Z') if ctx.created_at else _now_iso_z()
        nodes.append({
            'uuid': f'project_context_{ctx_type}',
            'name': name,
            'labels': ['ProjectContext'],
            'summary': f'Project Context: {name}',
            'attributes': {
                'context_type': ctx_type,
                'context_text': ctx.context_text or '',
                'rationale': ctx.rationale or '',
                'source': 'database',
            },
            'created_at': created_at_str,
        })
    return nodes



def _build_stakeholder_agenda_nodes(stakeholders):
    """遍历干系人列表，从 responsibilities 和 personal_agenda 生成 StakeholderAgenda 节点和 HAS_AGENDA 边。

    - responsibilities 切分为多条业务诉求（agenda_type="业务"）
    - personal_agenda 切分为多条个人诉求（agenda_type="个人"）
    - 字段空则不生成该类诉求；按分号或换行切分多条诉求

    Returns:
        (nodes, edges) 元组；干系人列表为空或所有字段为空返回 ([], [])
    """
    if not stakeholders:
        return [], []

    nodes = []
    edges = []
    now = _now_iso_z()

    for s in stakeholders:
        if not s or not getattr(s, 'id', None):
            continue

        stakeholder_id = s.id
        stakeholder_name = (s.name or '').strip()

        # 业务诉求（从 responsibilities 切分，按分号或换行）
        responsibilities = (getattr(s, 'responsibilities', None) or '').strip()
        if responsibilities:
            items = re.split(r'[;\n]', responsibilities)
            items = [item.strip() for item in items if item.strip()]
            for seq, item in enumerate(items, start=1):
                agenda_name = f'{stakeholder_name} Business Agenda {seq}'
                agenda_uuid = f'agenda_{stakeholder_id}_business_{seq}'
                nodes.append({
                    'uuid': agenda_uuid,
                    'name': agenda_name,
                    'labels': ['StakeholderAgenda'],
                    'summary': f'Stakeholder Agenda: {agenda_name}',
                    'attributes': {
                        'agenda_text': item,
                        'agenda_type': 'business',
                        'priority': 'medium',
                        'stakeholder_id': stakeholder_id,
                        'stakeholder_name': stakeholder_name,
                        'source': 'database',
                    },
                    'created_at': now,
                })
                edges.append(_make_edge(
                    stakeholder_name, agenda_name, 'HAS_AGENDA',
                    f'{stakeholder_name} has business agenda {seq}',
                    source_uuid=f'stakeholder_{stakeholder_id}',
                    target_uuid=agenda_uuid,
                ))

        # 个人诉求（从 personal_agenda 切分，按分号或换行）
        personal_agenda = (getattr(s, 'personal_agenda', None) or '').strip()
        if personal_agenda:
            items = re.split(r'[;\n]', personal_agenda)
            items = [item.strip() for item in items if item.strip()]
            for seq, item in enumerate(items, start=1):
                agenda_name = f'{stakeholder_name} Personal Agenda {seq}'
                agenda_uuid = f'agenda_{stakeholder_id}_personal_{seq}'
                nodes.append({
                    'uuid': agenda_uuid,
                    'name': agenda_name,
                    'labels': ['StakeholderAgenda'],
                    'summary': f'Stakeholder Agenda: {agenda_name}',
                    'attributes': {
                        'agenda_text': item,
                        'agenda_type': 'personal',
                        'priority': 'medium',
                        'stakeholder_id': stakeholder_id,
                        'stakeholder_name': stakeholder_name,
                        'source': 'database',
                    },
                    'created_at': now,
                })
                edges.append(_make_edge(
                    stakeholder_name, agenda_name, 'HAS_AGENDA',
                    f'{stakeholder_name} has personal agenda {seq}',
                    source_uuid=f'stakeholder_{stakeholder_id}',
                    target_uuid=agenda_uuid,
                ))

    return nodes, edges



def _build_task_nodes(tasks):
    """遍历 OpportunityTask 列表生成 Task 节点和 ASSIGNED_TO / CONTRIBUTES_TO 边。

    - priority 映射：high→高、medium→中、low→低、urgent→紧急；其他原值保留
    - status 映射：pending→待处理、in_progress→进行中、completed→已完成、cancelled→已取消；其他原值保留
    - ASSIGNED_TO 边：source=task_{id}、target=stakeholder_{stakeholder_id}（仅当 stakeholder_id 非空）
    - CONTRIBUTES_TO 边：source=task_{id}、target=business_goal_{related_goal}（仅当 related_goal 非空）

    注意：spec 中使用 target_stakeholder_id 字段名，OpportunityTask 模型实际字段为 stakeholder_id；
    related_goal 字段当前模型中不存在，使用 getattr 安全获取以便前向兼容。

    Returns:
        (nodes, edges) 元组；tasks 为空返回 ([], [])
    """
    if not tasks:
        return [], []

    nodes = []
    edges = []
    now = _now_iso_z()

    priority_map = {
        'high': 'High',
        'medium': 'Medium',
        'low': 'Low',
        'urgent': 'Urgent',
    }
    status_map = {
        'pending': 'Pending',
        'in_progress': 'In Progress',
        'completed': 'Completed',
        'cancelled': 'Cancelled',
    }

    def _enum_to_str(val):
        """将 Enum 或字符串规范化为字符串"""
        if val is None:
            return ''
        if hasattr(val, 'value'):
            return val.value
        return str(val)

    for task in tasks:
        if not task or not getattr(task, 'id', None):
            continue

        task_id = task.id
        title = (task.title or '').strip()
        task_uuid = f'task_{task_id}'

        # priority / status / task_type 枚举值映射
        priority_raw = _enum_to_str(task.priority)
        priority_label = priority_map.get(priority_raw, priority_raw)

        status_raw = _enum_to_str(task.status)
        status_label = status_map.get(status_raw, status_raw)

        task_type_str = _enum_to_str(task.task_type)

        # due_date（DateTime 字段）
        due_date_str = ''
        if task.due_date:
            if hasattr(task.due_date, 'isoformat'):
                due_date_str = task.due_date.isoformat()
            else:
                due_date_str = str(task.due_date)

        nodes.append({
            'uuid': task_uuid,
            'name': title,
            'labels': ['Task'],
            'summary': f'Task: {title}',
            'attributes': {
                'title': title,
                'task_type': task_type_str,
                'priority': priority_label,
                'status': status_label,
                'due_date': due_date_str,
                'description': task.description or '',
                'source': 'database',
            },
            'created_at': now,
        })

        # ASSIGNED_TO 边（仅当 stakeholder_id 非空）
        target_stakeholder_id = getattr(task, 'target_stakeholder_id', None) or getattr(task, 'stakeholder_id', None)
        if target_stakeholder_id:
            stakeholder_name = ''
            try:
                sk = Stakeholder.query.get(target_stakeholder_id)
                if sk:
                    stakeholder_name = sk.name or ''
            except Exception:
                stakeholder_name = ''
            stakeholder_display = stakeholder_name or f'Stakeholder {target_stakeholder_id}'
            edges.append(_make_edge(
                title, stakeholder_display, 'ASSIGNED_TO',
                f'Task "{title}" assigned to {stakeholder_display}',
                source_uuid=task_uuid,
                target_uuid=f'stakeholder_{target_stakeholder_id}',
            ))

        # CONTRIBUTES_TO 边（仅当 related_goal 非空）
        related_goal = getattr(task, 'related_goal', None)
        if related_goal:
            related_goal_str = str(related_goal)
            edges.append(_make_edge(
                title, related_goal_str, 'CONTRIBUTES_TO',
                f'Task "{title}" contributes to {related_goal_str}',
                source_uuid=task_uuid,
                target_uuid=f'business_goal_{related_goal_str}',
            ))

    return nodes, edges



def _infer_task_agenda_mapping(tasks, agenda_nodes):
    """通过 LLM 推断任务与干系人诉求的对应关系。

    Args:
        tasks: OpportunityTask 列表
        agenda_nodes: StakeholderAgenda 节点列表（来自 _build_stakeholder_agenda_nodes 返回的 nodes 部分）

    Returns:
        [{task_id, agenda_id}] 映射列表；任一输入为空、LLM 不可用或解析失败时返回空列表
        （不抛出异常，不阻塞图谱渲染）
    """
    if not tasks or not agenda_nodes:
        return []

    try:
        from app.utils.llm_client import LLMClient
    except Exception as e:
        logger.warning(f'导入 LLMClient 失败，跳过任务-诉求映射推断: {e}')
        return []

    # 构造任务列表（id + title + description）
    task_list = []
    for t in tasks:
        if not t or not getattr(t, 'id', None):
            continue
        task_list.append({
            'id': t.id,
            'title': (t.title or '').strip(),
            'description': (t.description or '').strip(),
        })

    # 构造诉求列表（uuid + name + agenda_text + stakeholder_name）
    agenda_list = []
    for a in agenda_nodes:
        if not isinstance(a, dict):
            continue
        uuid_ = a.get('uuid')
        if not uuid_:
            continue
        attrs = a.get('attributes') or {}
        agenda_list.append({
            'uuid': uuid_,
            'name': a.get('name', ''),
            'agenda_text': attrs.get('agenda_text', ''),
            'stakeholder_name': attrs.get('stakeholder_name', ''),
        })

    if not task_list or not agenda_list:
        return []

    system_prompt = (
        '你是 B2B 销售数字孪生系统的智能助手。请根据任务列表和干系人诉求列表，推断每个任务针对哪些诉求。'
        '只返回 JSON 数组，每个元素形如 {"task_id": 任务ID, "agenda_id": 诉求节点uuid}。'
        '如果没有明显对应关系，返回空数组 []。'
    )

    user_message = json.dumps({
        'tasks': task_list,
        'agendas': agenda_list,
    }, ensure_ascii=False)

    messages = [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': user_message},
    ]

    try:
        llm = LLMClient()
        response = llm.chat_json(messages=messages, temperature=0.2, max_tokens=1500)
    except Exception as e:
        logger.warning(f'LLM 调用失败（任务-诉求映射推断）: {e}')
        return []

    # chat_json 已解析 JSON；防御性处理 dict/list/str 三种返回
    mappings = response
    if isinstance(response, str):
        # 字符串回退：用 _extract_json_object 提取
        extracted = _extract_json_object(response)
        mappings = extracted if isinstance(extracted, list) else []
    elif isinstance(response, dict):
        # LLM 偶尔会返回 {"mappings": [...]} 形式
        for key in ('mappings', 'data', 'result', 'results', 'items'):
            if isinstance(response.get(key), list):
                mappings = response[key]
                break
        else:
            mappings = []

    if not isinstance(mappings, list):
        return []

    # 清洗结果：只保留包含 task_id 和 agenda_id 的字典元素
    result = []
    for item in mappings:
        if not isinstance(item, dict):
            continue
        task_id = item.get('task_id')
        agenda_id = item.get('agenda_id')
        if task_id is None or agenda_id is None:
            continue
        result.append({'task_id': task_id, 'agenda_id': str(agenda_id)})

    return result



def _build_extended_edges(project, stakeholders, tasks, trend_nodes, measure_nodes,
                          strategy_nodes, goal_nodes, pain_nodes, context_nodes, agenda_nodes):
    """组装 9 类扩展关系边中的 7 类（HAS_AGENDA / ASSIGNED_TO / CONTRIBUTES_TO 已在 Task 8/9 中实现）。

    Teaching 关系（3 类）：
    - DRIVEN_BY_TREND: StrategicInitiative → IndustryTrend
    - GOAL_ALIGNS_INITIATIVE: BusinessGoal → StrategicInitiative
    - MEASURE_ADDRESSES_PAIN: CurrentMeasure → PainPoint

    Taking Control 关系（3 类）：
    - ALIGNS_WITH: ProjectContext → StrategicInitiative
    - TEACHING_REFRAMES: ProjectContext → IndustryTrend / CurrentMeasure
    - ADDRESSES_AGENDA: ProjectContext → StakeholderAgenda

    Tailoring 关系（1 类）：
    - TARGETS_AGENDA: Task → StakeholderAgenda（通过 LLM 推断）

    Args:
        project: Project 模型实例（保留参数以备后用）
        stakeholders: Stakeholder 列表（保留参数以备后用）
        tasks: OpportunityTask 列表
        trend_nodes: IndustryTrend 节点列表
        measure_nodes: CurrentMeasure 节点列表
        strategy_nodes: StrategicInitiative 节点列表（Zep + database_background 合并后）
        goal_nodes: BusinessGoal 节点列表
        pain_nodes: PainPoint 节点列表
        context_nodes: ProjectContext 节点列表
        agenda_nodes: StakeholderAgenda 节点列表

    Returns:
        edges 列表；任何节点列表为空时对应类型边不生成，不报错
    """
    MAX_EDGES_PER_TYPE = 20  # 每类关系最多保留 20 条边，防止全连接导致图谱爆炸
    edges = []

    def _add_edge(source_name, target_name, edge_type, rationale, source_uuid, target_uuid):
        """构造一条边并附加中文 rationale 字段"""
        edge = _make_edge(
            source_name, target_name, edge_type, rationale,
            source_uuid=source_uuid, target_uuid=target_uuid,
        )
        edge.setdefault('attributes', {})['rationale'] = rationale
        edges.append(edge)

    # 1. DRIVEN_BY_TREND: StrategicInitiative → IndustryTrend
    if strategy_nodes and trend_nodes:
        count = 0
        for strategy in strategy_nodes:
            if count >= MAX_EDGES_PER_TYPE:
                break
            strategy_uuid = strategy.get('uuid') if isinstance(strategy, dict) else None
            strategy_name = (strategy.get('name') if isinstance(strategy, dict) else '') or ''
            if not strategy_uuid:
                continue
            for trend in trend_nodes:
                if count >= MAX_EDGES_PER_TYPE:
                    break
                trend_uuid = trend.get('uuid') if isinstance(trend, dict) else None
                trend_name = (trend.get('name') if isinstance(trend, dict) else '') or ''
                if not trend_uuid:
                    continue
                rationale = f'{strategy_name} driven by {trend_name}'
                _add_edge(strategy_name, trend_name, 'DRIVEN_BY_TREND',
                          rationale, strategy_uuid, trend_uuid)
                count += 1

    # 2. GOAL_ALIGNS_INITIATIVE: BusinessGoal → StrategicInitiative
    if goal_nodes and strategy_nodes:
        count = 0
        for goal in goal_nodes:
            if count >= MAX_EDGES_PER_TYPE:
                break
            goal_uuid = goal.get('uuid') if isinstance(goal, dict) else None
            goal_name = (goal.get('name') if isinstance(goal, dict) else '') or ''
            if not goal_uuid:
                continue
            for strategy in strategy_nodes:
                if count >= MAX_EDGES_PER_TYPE:
                    break
                strategy_uuid = strategy.get('uuid') if isinstance(strategy, dict) else None
                strategy_name = (strategy.get('name') if isinstance(strategy, dict) else '') or ''
                if not strategy_uuid:
                    continue
                rationale = f'{goal_name} aligns with {strategy_name}'
                _add_edge(goal_name, strategy_name, 'GOAL_ALIGNS_INITIATIVE',
                          rationale, goal_uuid, strategy_uuid)
                count += 1

    # 3. MEASURE_ADDRESSES_PAIN: CurrentMeasure → PainPoint
    if measure_nodes and pain_nodes:
        count = 0
        for measure in measure_nodes:
            if count >= MAX_EDGES_PER_TYPE:
                break
            measure_uuid = measure.get('uuid') if isinstance(measure, dict) else None
            measure_name = (measure.get('name') if isinstance(measure, dict) else '') or ''
            if not measure_uuid:
                continue
            for pain in pain_nodes:
                if count >= MAX_EDGES_PER_TYPE:
                    break
                pain_uuid = pain.get('uuid') if isinstance(pain, dict) else None
                pain_name = (pain.get('name') if isinstance(pain, dict) else '') or ''
                if not pain_uuid:
                    continue
                rationale = f'{measure_name} addresses {pain_name}'
                _add_edge(measure_name, pain_name, 'MEASURE_ADDRESSES_PAIN',
                          rationale, measure_uuid, pain_uuid)
                count += 1

    # 4. ALIGNS_WITH: ProjectContext → StrategicInitiative
    if context_nodes and strategy_nodes:
        count = 0
        for context in context_nodes:
            if count >= MAX_EDGES_PER_TYPE:
                break
            context_uuid = context.get('uuid') if isinstance(context, dict) else None
            context_name = (context.get('name') if isinstance(context, dict) else '') or ''
            if not context_uuid:
                continue
            context_attrs = context.get('attributes') if isinstance(context, dict) else None
            context_type = (context_attrs or {}).get('context_type', '') if isinstance(context_attrs, dict) else ''
            for strategy in strategy_nodes:
                if count >= MAX_EDGES_PER_TYPE:
                    break
                strategy_uuid = strategy.get('uuid') if isinstance(strategy, dict) else None
                strategy_name = (strategy.get('name') if isinstance(strategy, dict) else '') or ''
                if not strategy_uuid:
                    continue
                if context_type == 'why':
                    rationale = f'{context_name} aligns with strategy {strategy_name}'
                elif context_type == 'why_now':
                    rationale = f'{context_name} aligns with strategy timing {strategy_name}'
                elif context_type == 'why_us':
                    rationale = f'{context_name} aligns with strategy differentiation {strategy_name}'
                else:
                    rationale = f'{context_name} aligns with strategy {strategy_name}'
                _add_edge(context_name, strategy_name, 'ALIGNS_WITH',
                          rationale, context_uuid, strategy_uuid)
                count += 1

    # 5. TEACHING_REFRAMES: ProjectContext → IndustryTrend / CurrentMeasure
    if context_nodes and (trend_nodes or measure_nodes):
        trend_count = 0
        measure_count = 0
        for context in context_nodes:
            if trend_count >= MAX_EDGES_PER_TYPE and measure_count >= MAX_EDGES_PER_TYPE:
                break
            context_uuid = context.get('uuid') if isinstance(context, dict) else None
            context_name = (context.get('name') if isinstance(context, dict) else '') or ''
            if not context_uuid:
                continue
            for trend in (trend_nodes or []):
                if trend_count >= MAX_EDGES_PER_TYPE:
                    break
                trend_uuid = trend.get('uuid') if isinstance(trend, dict) else None
                trend_name = (trend.get('name') if isinstance(trend, dict) else '') or ''
                if not trend_uuid:
                    continue
                rationale = f'{context_name} reframes understanding of {trend_name}'
                _add_edge(context_name, trend_name, 'TEACHING_REFRAMES',
                          rationale, context_uuid, trend_uuid)
                trend_count += 1
            for measure in (measure_nodes or []):
                if measure_count >= MAX_EDGES_PER_TYPE:
                    break
                measure_uuid = measure.get('uuid') if isinstance(measure, dict) else None
                measure_name = (measure.get('name') if isinstance(measure, dict) else '') or ''
                if not measure_uuid:
                    continue
                rationale = f'{context_name} reframes understanding of {measure_name}'
                _add_edge(context_name, measure_name, 'TEACHING_REFRAMES',
                          rationale, context_uuid, measure_uuid)
                measure_count += 1

    # 6. ADDRESSES_AGENDA: ProjectContext → StakeholderAgenda
    if context_nodes and agenda_nodes:
        count = 0
        for context in context_nodes:
            if count >= MAX_EDGES_PER_TYPE:
                break
            context_uuid = context.get('uuid') if isinstance(context, dict) else None
            context_name = (context.get('name') if isinstance(context, dict) else '') or ''
            if not context_uuid:
                continue
            for agenda in agenda_nodes:
                if count >= MAX_EDGES_PER_TYPE:
                    break
                agenda_uuid = agenda.get('uuid') if isinstance(agenda, dict) else None
                agenda_name = (agenda.get('name') if isinstance(agenda, dict) else '') or ''
                if not agenda_uuid:
                    continue
                rationale = f'{context_name} addresses {agenda_name}'
                _add_edge(context_name, agenda_name, 'ADDRESSES_AGENDA',
                          rationale, context_uuid, agenda_uuid)
                count += 1

    # 7. TARGETS_AGENDA: Task → StakeholderAgenda（LLM 推断）
    try:
        mappings = _infer_task_agenda_mapping(tasks, agenda_nodes)
    except Exception as e:
        logger.warning(f'调用 _infer_task_agenda_mapping 异常（不阻塞图谱渲染）: {e}')
        mappings = []

    if mappings:
        # 构造 task_uuid → task 查找表
        task_map = {}
        for t in (tasks or []):
            if not t or not getattr(t, 'id', None):
                continue
            task_map[f'task_{t.id}'] = t
        # 构造 agenda_uuid → agenda 节点查找表
        agenda_map = {}
        for a in (agenda_nodes or []):
            if isinstance(a, dict) and a.get('uuid'):
                agenda_map[a.get('uuid')] = a

        for mapping in mappings:
            if not isinstance(mapping, dict):
                continue
            task_id = mapping.get('task_id')
            agenda_id = mapping.get('agenda_id')
            if task_id is None or not agenda_id:
                continue

            task_uuid = f'task_{task_id}'
            task = task_map.get(task_uuid)
            if not task:
                continue
            task_title = (task.title or '').strip()

            agenda = agenda_map.get(agenda_id)
            if not agenda:
                continue
            agenda_name = agenda.get('name', '') or ''

            rationale = f'Task {task_title} targets agenda {agenda_name}'
            _add_edge(task_title, agenda_name, 'TARGETS_AGENDA',
                      rationale, task_uuid, agenda_id)

    return edges
