"""会议计划路由"""
from ._helpers import *  # noqa: E402, F401, F403
from ._helpers import sales_twin_bp  # noqa: E402, F401


@sales_twin_bp.route('/projects/<int:project_id>/meeting-plans', methods=['GET'])
def get_meeting_plans(project_id):
    """获取项目所有拜访预案"""
    from app.services.meeting_plan_generator import MeetingPlanGenerator
    generator = MeetingPlanGenerator()
    result = generator.get_plans(project_id)
    return jsonify(result), 200



@sales_twin_bp.route('/projects/<int:project_id>/meeting-plans', methods=['POST'])
def create_meeting_plan(project_id):
    """生成拜访预案"""
    from app.services.meeting_plan_generator import MeetingPlanGenerator
    project = get_project_or_404(project_id)
    data = request.get_json()

    stakeholder_id = data.get('stakeholder_id')
    if not stakeholder_id:
        return jsonify({'error': '缺少stakeholder_id'}), 400

    generator = MeetingPlanGenerator()
    result = generator.generate_plan(
        project_id=project_id,
        stakeholder_id=stakeholder_id,
        meeting_purpose=data.get('meeting_purpose', ''),
        meeting_type=data.get('meeting_type', 'first_visit'),
        related_task_ids=data.get('related_task_ids', []),
        related_materials=data.get('related_materials', []),
        plan_name=data.get('name', ''),
        stakeholder_ids=data.get('stakeholder_ids', [])
    )
    return jsonify(result), 200



@sales_twin_bp.route('/meeting-plans/<int:plan_id>', methods=['GET'])
def get_meeting_plan(plan_id):
    """获取单个拜访预案"""
    from app.services.meeting_plan_generator import MeetingPlanGenerator
    generator = MeetingPlanGenerator()
    result = generator.get_plan(plan_id)
    return jsonify(result), 200



@sales_twin_bp.route('/meeting-plans/<int:plan_id>', methods=['PUT'])
def update_meeting_plan(plan_id):
    """更新拜访预案（仅支持活动状态：pending/generated/reviewed）
    可更新字段：name, meeting_purpose, meeting_type, status, plan_content,
                stakeholder_id, stakeholder_ids, related_task_ids
    """
    plan = MeetingPlan.query.get_or_404(plan_id)
    data = request.get_json() or {}

    # 字段白名单
    if 'name' in data:
        plan.name = data['name'] or plan.name
    if 'meeting_purpose' in data and data['meeting_purpose'] is not None:
        plan.meeting_purpose = data['meeting_purpose']
    if 'meeting_type' in data and data['meeting_type'] is not None:
        plan.meeting_type = data['meeting_type']
    if 'status' in data and data['status'] in ('pending', 'generated', 'reviewed'):
        plan.status = data['status']
    if 'plan_content' in data and data['plan_content'] is not None:
        # plan_content 可以是 dict 或 str
        if isinstance(data['plan_content'], (dict, list)):
            plan.plan_content = json.dumps(data['plan_content'], ensure_ascii=False)
        else:
            plan.plan_content = data['plan_content']
    if 'stakeholder_id' in data and data['stakeholder_id']:
        plan.stakeholder_id = data['stakeholder_id']
    if 'stakeholder_ids' in data:
        # JSON数组，存干系人ID列表
        plan.stakeholder_ids = json.dumps(data['stakeholder_ids'] or [], ensure_ascii=False)
    if 'related_task_ids' in data:
        plan.related_task_ids = json.dumps(data['related_task_ids'] or [], ensure_ascii=False)

    plan.updated_at = datetime.utcnow()
    db.session.commit()

    # 复用 generator 的 _plan_to_dict 返回完整字段
    from app.services.meeting_plan_generator import MeetingPlanGenerator
    generator = MeetingPlanGenerator()
    return jsonify({
        'success': True,
        'plan': generator._plan_to_dict(plan),
        'message': '拜访预案已更新'
    }), 200



@sales_twin_bp.route('/meeting-plans/<int:plan_id>', methods=['DELETE'])
def delete_meeting_plan(plan_id):
    """删除拜访预案（建议仅对活动中的预案使用）"""
    plan = MeetingPlan.query.get_or_404(plan_id)
    plan_name = plan.name
    db.session.delete(plan)
    db.session.commit()
    return jsonify({
        'success': True,
        'message': f'拜访预案「{plan_name}」已删除'
    }), 200



