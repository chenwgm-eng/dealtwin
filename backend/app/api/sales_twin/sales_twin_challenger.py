"""Challenger 商业指导与检查清单路由"""
from ._helpers import *  # noqa: E402, F401, F403
from ._helpers import sales_twin_bp  # noqa: E402, F401


@sales_twin_bp.route('/projects/<int:project_id>/challenger-teachings', methods=['POST'])
def create_challenger_teaching(project_id):
    """生成 Challenger 商业指导话术（同步调用LLM）

    请求体: {stakeholder_id?, name?}
    LLM 不可用或输出解析失败时返回 502
    """
    from app.services.challenger_teaching_generator import ChallengerTeachingGenerator
    project = get_project_or_404(project_id)
    data = request.get_json() or {}

    generator = ChallengerTeachingGenerator()
    try:
        result = generator.generate(
            project_id=project_id,
            stakeholder_id=data.get('stakeholder_id'),
            name=data.get('name')
        )
    except RuntimeError as e:
        # 截断错误消息，避免泄露底层异常细节（API地址/鉴权信息等）
        return jsonify({'success': False, 'error': str(e)[:200]}), 502
    return jsonify(result), 201



@sales_twin_bp.route('/projects/<int:project_id>/challenger-teachings', methods=['GET'])
def get_challenger_teachings(project_id):
    """获取项目的所有商业指导话术（时间倒序）"""
    from app.services.challenger_teaching_generator import ChallengerTeachingGenerator
    project = get_project_or_404(project_id)
    generator = ChallengerTeachingGenerator()
    return jsonify(generator.get_list(project_id)), 200



@sales_twin_bp.route('/challenger-teachings/<int:teaching_id>', methods=['GET'])
def get_challenger_teaching(teaching_id):
    """获取单个商业指导话术"""
    from app.services.challenger_teaching_generator import ChallengerTeachingGenerator
    generator = ChallengerTeachingGenerator()
    result = generator.get(teaching_id)
    return jsonify(result), 200



@sales_twin_bp.route('/challenger-teachings/<int:teaching_id>', methods=['PUT'])
def update_challenger_teaching(teaching_id):
    """更新商业指导话术（允许改 name 和 teaching_content 内各字段）"""
    from app.services.challenger_teaching_generator import ChallengerTeachingGenerator
    data = request.get_json() or {}
    generator = ChallengerTeachingGenerator()
    try:
        result = generator.update(teaching_id, data)
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    return jsonify(result), 200



@sales_twin_bp.route('/challenger-teachings/<int:teaching_id>', methods=['DELETE'])
def delete_challenger_teaching(teaching_id):
    """删除商业指导话术"""
    from app.services.challenger_teaching_generator import ChallengerTeachingGenerator
    generator = ChallengerTeachingGenerator()
    generator.delete(teaching_id)
    return '', 204



@sales_twin_bp.route('/projects/<int:project_id>/challenger-checklist', methods=['GET'])
def get_challenger_checklist(project_id):
    """评估项目的 Challenger 检查清单（5 项，不调LLM）"""
    from app.services.challenger_checklist import evaluate_challenger_checklist
    project = get_project_or_404(project_id)
    return jsonify(evaluate_challenger_checklist(project_id)), 200
