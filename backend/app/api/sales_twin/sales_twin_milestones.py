"""SVS 里程碑决策与销售模式路由"""
from ._helpers import *  # noqa: E402, F401, F403
from ._helpers import sales_twin_bp  # noqa: E402, F401
from app.models.database import MilestoneDecision
from sqlalchemy.exc import IntegrityError

# 合法销售模式
VALID_SALES_MODES = ('inside_sales', 'prescriptive_pursuit', 'value_solution_selling')
# 里程碑中文标签（同时作为合法里程碑枚举与返回顺序）
MILESTONE_LABELS = {
    'om10': 'Bid/No-Go 决策',
    'om20': 'Go/No-Go 决策',
    'om30': '销售策略评审',
    'om40': '投标批准',
    'om70': '赢单/丢单',
}
# 合法决策值
VALID_DECISIONS = ('go', 'no_go', 'pending')
# 五维评估字段（1-5 分）
SCORE_FIELDS = ('strategic_fit', 'revenue_scale', 'competitive_intensity',
                'resource_requirement', 'success_probability')


def _milestone_to_dict(md, milestone):
    """里程碑决策转字典（md 为 None 时返回 pending 占位）"""
    d = {
        'id': md.id if md else None,
        'project_id': md.project_id if md else None,
        'milestone': milestone,
        'milestone_label': MILESTONE_LABELS[milestone],
        'decision': md.decision if md else 'pending',
        'rationale': md.rationale if md else None,
        'decided_by': md.decided_by if md else None,
        'decided_at': md.decided_at.isoformat() if md and md.decided_at else None,
        'created_at': md.created_at.isoformat() if md and md.created_at else None,
        'updated_at': md.updated_at.isoformat() if md and md.updated_at else None,
    }
    for field in SCORE_FIELDS:
        d[field] = getattr(md, field) if md else None
    return d



@sales_twin_bp.route('/projects/<int:project_id>/milestones', methods=['GET'])
def get_milestones(project_id):
    """获取项目的 5 个里程碑决策（未建记录的以 pending 占位返回）"""
    project = get_project_or_404(project_id)
    records = {
        md.milestone: md
        for md in MilestoneDecision.query.filter_by(project_id=project_id).all()
    }
    milestones = [_milestone_to_dict(records.get(ms), ms) for ms in MILESTONE_LABELS]
    return jsonify({'milestones': milestones}), 200



@sales_twin_bp.route('/projects/<int:project_id>/milestones/<milestone>', methods=['PUT'])
def upsert_milestone(project_id, milestone):
    """创建或更新里程碑决策（每项目每里程碑仅一条）

    请求体: {decision, strategic_fit?..., rationale?, decided_by?}
    decision 非 pending 时自动写入 decided_at
    """
    project = get_project_or_404(project_id)
    if milestone not in MILESTONE_LABELS:
        return jsonify({'error': f'非法里程碑: {milestone}，可选值: {"/".join(MILESTONE_LABELS)}'}), 400

    data = request.get_json() or {}
    decision = data.get('decision')
    if decision not in VALID_DECISIONS:
        return jsonify({'error': f'非法决策值: {decision}，可选值: go/no_go/pending'}), 400

    # 校验五维评分（1-5 的整数）
    scores = {}
    for field in SCORE_FIELDS:
        if field in data and data[field] is not None:
            try:
                val = int(data[field])
            except (TypeError, ValueError):
                return jsonify({'error': f'评分字段 {field} 必须为 1-5 的整数'}), 400
            if val < 1 or val > 5:
                return jsonify({'error': f'评分字段 {field} 必须为 1-5 的整数'}), 400
            scores[field] = val

    # upsert：每项目每里程碑仅一条
    md = MilestoneDecision.query.filter_by(project_id=project_id, milestone=milestone).first()
    old_decision = md.decision if md else 'pending'
    if md is None:
        md = MilestoneDecision(project_id=project_id, milestone=milestone)
        db.session.add(md)
        try:
            # 先 flush 检测唯一约束冲突（并发 upsert 竞争）
            db.session.flush()
        except IntegrityError:
            db.session.rollback()
            # 竞争失败：记录已被并发请求创建，转为更新
            md = MilestoneDecision.query.filter_by(project_id=project_id, milestone=milestone).first_or_404()
            old_decision = md.decision

    md.decision = decision
    for field, val in scores.items():
        setattr(md, field, val)
    if 'rationale' in data:
        md.rationale = data['rationale']
    if 'decided_by' in data:
        md.decided_by = data['decided_by']
    # decision 非 pending 时记录决策时间；回到 pending 则清空
    md.decided_at = datetime.utcnow() if decision != 'pending' else None
    md.updated_at = datetime.utcnow()

    # 决策变化时写状态变更日志
    if old_decision != decision:
        log = StateChangeLog(
            project_id=project_id,
            stakeholder_id=None,
            change_object='milestone',
            attribute_name=milestone,
            old_value=old_decision,
            new_value=decision,
            reasoning=data.get('rationale') or '手动编辑',
            change_source='manual_edit'
        )
        db.session.add(log)

    db.session.commit()
    return jsonify({'success': True, 'milestone': _milestone_to_dict(md, milestone)}), 200



@sales_twin_bp.route('/projects/<int:project_id>/sales-mode', methods=['PUT'])
def update_sales_mode(project_id):
    """更新项目销售模式（null 表示清除）"""
    project = get_project_or_404(project_id)
    data = request.get_json() or {}

    sales_mode = data.get('sales_mode')
    if sales_mode in ('', 'null'):
        sales_mode = None
    if sales_mode is not None and sales_mode not in VALID_SALES_MODES:
        return jsonify({'error': f'非法销售模式: {sales_mode}，可选值: {"/".join(VALID_SALES_MODES)} 或 null'}), 400

    old_val = project.sales_mode
    if old_val != sales_mode:
        log = StateChangeLog(
            project_id=project_id,
            stakeholder_id=None,
            change_object=project.name,
            attribute_name='sales_mode',
            old_value=old_val or '空',
            new_value=sales_mode or '空',
            reasoning='手动编辑',
            change_source='manual_edit'
        )
        db.session.add(log)

    project.sales_mode = sales_mode
    project.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'success': True, 'project': project_to_dict(project)}), 200
