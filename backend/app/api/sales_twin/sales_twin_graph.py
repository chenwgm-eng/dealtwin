"""图谱路由"""
from ._helpers import *  # noqa: E402, F401, F403
from ._helpers import sales_twin_bp  # noqa: E402, F401


@sales_twin_bp.route('/projects/<int:project_id>/graph', methods=['GET'])
def get_project_graph(project_id):
    """加载项目图谱数据（本体+图谱节点边）。

    图谱数据来源：数据库注入（项目字段、干系人、任务）。
    只要数据库有项目信息、干系人、任务，
    就返回完整的综合视图图谱（11 类节点 + 21 类关系）。
    """
    project = get_project_or_404(project_id)

    # 1. 查询数据库干系人和任务
    stakeholders = Stakeholder.query.filter_by(project_id=project_id).all()
    tasks = OpportunityTask.query.filter_by(project_id=project_id).all()

    # 2. 数据库注入：构建各类扩展节点和边
    stakeholder_nodes, stakeholder_edges = _build_stakeholder_graph(stakeholders)
    trend_nodes = _build_industry_trend_nodes(project)
    measure_nodes = _build_current_measure_nodes(project)
    pain_point_nodes = _build_pain_point_nodes(project)
    strategy_from_bg_nodes = _build_strategic_initiative_from_background(project)
    context_nodes = _build_project_context_nodes(project)
    agenda_nodes, agenda_edges = _build_stakeholder_agenda_nodes(stakeholders)
    task_nodes, task_edges = _build_task_nodes(tasks)

    # 3. 合并所有数据库注入的节点
    db_injected_nodes = (
        stakeholder_nodes + trend_nodes + measure_nodes + pain_point_nodes +
        strategy_from_bg_nodes + context_nodes +
        agenda_nodes + task_nodes
    )
    db_injected_edges = stakeholder_edges + agenda_edges + task_edges

    # 4. 合并数据库注入节点，按 uuid 去重
    # StrategicInitiative 节点按 name 字段去重
    all_nodes = []

    # 收集已存在的 uuid 和 StrategicInitiative 的 name
    existing_uuids = set()
    existing_strategy_names = set()
    for n in all_nodes:
        uuid = n.get('uuid')
        if uuid:
            existing_uuids.add(uuid)
        labels = n.get('labels') or []
        if 'StrategicInitiative' in labels:
            name = n.get('name') or (n.get('attributes') or {}).get('initiative_name')
            if name:
                existing_strategy_names.add(name)

    # 追加数据库注入节点（去重）
    for n in db_injected_nodes:
        uuid = n.get('uuid')
        labels = n.get('labels') or []
        # StrategicInitiative 节点按 name 去重
        if 'StrategicInitiative' in labels:
            name = n.get('name') or (n.get('attributes') or {}).get('initiative_name')
            if name and name in existing_strategy_names:
                continue  # 跳过重复的战略举措节点
            if name:
                existing_strategy_names.add(name)
        # 其他节点按 uuid 去重
        if uuid and uuid in existing_uuids:
            continue
        if uuid:
            existing_uuids.add(uuid)
        all_nodes.append(n)

    # 5. 合并数据库注入边
    all_edges = list(db_injected_edges)

    # 7. 组装扩展关系边（需要先识别各类节点用于连线）
    # 从合并后的节点中识别各类节点
    trend_nodes_for_edges = [n for n in all_nodes if 'IndustryTrend' in (n.get('labels') or [])]
    measure_nodes_for_edges = [n for n in all_nodes if 'CurrentMeasure' in (n.get('labels') or [])]
    strategy_nodes_for_edges = [n for n in all_nodes if 'StrategicInitiative' in (n.get('labels') or [])]
    goal_nodes_for_edges = [n for n in all_nodes if 'BusinessGoal' in (n.get('labels') or [])]
    pain_nodes_for_edges = [n for n in all_nodes if 'PainPoint' in (n.get('labels') or [])]
    context_nodes_for_edges = [n for n in all_nodes if 'ProjectContext' in (n.get('labels') or [])]
    agenda_nodes_for_edges = [n for n in all_nodes if 'StakeholderAgenda' in (n.get('labels') or [])]

    extended_edges = _build_extended_edges(
        project=project,
        stakeholders=stakeholders,
        tasks=tasks,
        trend_nodes=trend_nodes_for_edges,
        measure_nodes=measure_nodes_for_edges,
        strategy_nodes=strategy_nodes_for_edges,
        goal_nodes=goal_nodes_for_edges,
        pain_nodes=pain_nodes_for_edges,
        context_nodes=context_nodes_for_edges,
        agenda_nodes=agenda_nodes_for_edges,
    )
    all_edges.extend(extended_edges)

    # 8. 过滤：只保留 B2B 核心实体类型，注入中文标签
    merged_graph_data = _filter_b2b_graph({
        'nodes': all_nodes,
        'edges': all_edges,
        'node_count': len(all_nodes),
        'edge_count': len(all_edges),
    })

    # 9. 判断是否有图谱数据（含结构化战略项、WHY 上下文、竞争分析）
    strategy_items_count = ProjectStrategyItem.query.filter_by(project_id=project_id).count()
    why_contexts_count = ProjectWhyContext.query.filter_by(project_id=project_id).count()
    has_any_data = (
        len(stakeholders) > 0 or
        len(tasks) > 0 or
        strategy_items_count > 0 or
        why_contexts_count > 0 or
        bool(project.competitive_analysis and project.competitive_analysis.strip())
    )

    if not has_any_data:
        return jsonify({
            'has_graph': False,
            'message': '请先在概览页维护项目信息'
        }), 200

    # 10. 返回完整综合视图
    return jsonify({
        'has_graph': True,
        'graph_data': merged_graph_data,
        'message': '综合视图（数据库注入）',
    }), 200



