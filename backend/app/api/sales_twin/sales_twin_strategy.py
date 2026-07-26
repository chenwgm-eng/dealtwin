"""项目战略要素 CRUD 路由

提供对 ProjectStrategyItem 的增删改查，替代原 customer_background 大文本字段，
支持按 item_type 分组返回、每类最多 3 条限制、sort_order 自动递增。
"""
from ._helpers import *  # noqa: E402, F401, F403
from ._helpers import sales_twin_bp, ProjectWhyContext  # noqa: E402, F401


# 允许的战略项类型
ALLOWED_ITEM_TYPES = ('industry_trend', 'current_measure', 'pain_point', 'strategic_initiative')
# 每类战略项最多条数
MAX_ITEMS_PER_TYPE = 3


def _strategy_item_to_dict(item):
    """战略项对象转字典（metadata_json 解析为对象）"""
    metadata = None
    if item.metadata_json:
        try:
            metadata = json.loads(item.metadata_json)
        except (json.JSONDecodeError, TypeError):
            metadata = None
    return {
        'id': item.id,
        'project_id': item.project_id,
        'item_type': item.item_type,
        'name': item.name,
        'description': item.description,
        'metadata': metadata,
        'sort_order': item.sort_order,
        'created_at': item.created_at.isoformat() if item.created_at else None,
        'updated_at': item.updated_at.isoformat() if item.updated_at else None,
    }


@sales_twin_bp.route('/projects/<int:project_id>/strategy-items', methods=['GET'])
def list_strategy_items(project_id):
    """获取项目所有战略项，按 item_type 分组返回"""
    get_project_or_404(project_id)
    items = ProjectStrategyItem.query.filter_by(project_id=project_id).order_by(
        ProjectStrategyItem.item_type, ProjectStrategyItem.sort_order
    ).all()
    grouped = {t: [] for t in ALLOWED_ITEM_TYPES}
    for it in items:
        grouped.setdefault(it.item_type, []).append(_strategy_item_to_dict(it))
    return jsonify({'strategy_items': grouped}), 200


@sales_twin_bp.route('/projects/<int:project_id>/strategy-items', methods=['POST'])
def create_strategy_item(project_id):
    """新建战略项

    请求体：{ item_type, name, description, metadata }
    - item_type 必须在允许枚举内
    - 同类型最多 MAX_ITEMS_PER_TYPE 条，超过返回 400
    - sort_order 自动取该类型现有最大值 + 1
    """
    get_project_or_404(project_id)
    data = request.get_json() or {}
    item_type = data.get('item_type')
    name = (data.get('name') or '').strip()

    if item_type not in ALLOWED_ITEM_TYPES:
        return jsonify({'error': f'item_type 必须为 {list(ALLOWED_ITEM_TYPES)} 之一'}), 400
    if not name:
        return jsonify({'error': 'name 不能为空'}), 400

    # 校验同类型条数上限
    existing_count = ProjectStrategyItem.query.filter_by(
        project_id=project_id, item_type=item_type
    ).count()
    if existing_count >= MAX_ITEMS_PER_TYPE:
        return jsonify({'error': f'{item_type} 已达上限 {MAX_ITEMS_PER_TYPE} 条'}), 400

    # sort_order 自动递增：取该类型当前最大 sort_order + 1
    latest = ProjectStrategyItem.query.filter_by(
        project_id=project_id, item_type=item_type
    ).order_by(ProjectStrategyItem.sort_order.desc()).first()
    max_sort = latest.sort_order if latest else 0

    # metadata 序列化为 JSON 字符串存储
    metadata = data.get('metadata')
    metadata_json = json.dumps(metadata, ensure_ascii=False) if metadata is not None else None

    item = ProjectStrategyItem(
        project_id=project_id,
        item_type=item_type,
        name=name,
        description=data.get('description'),
        metadata_json=metadata_json,
        sort_order=max_sort + 1,
    )
    db.session.add(item)
    db.session.commit()
    return jsonify({'success': True, 'strategy_item': _strategy_item_to_dict(item)}), 201


@sales_twin_bp.route('/projects/<int:project_id>/strategy-items/<int:item_id>', methods=['PUT'])
def update_strategy_item(project_id, item_id):
    """更新战略项（item_type 不可改）

    请求体：{ name, description, metadata }
    """
    item = ProjectStrategyItem.query.filter_by(id=item_id, project_id=project_id).first()
    if not item:
        return jsonify({'error': '战略项不存在或不属于该项目'}), 404

    data = request.get_json() or {}
    if 'name' in data:
        name = (data.get('name') or '').strip()
        if not name:
            return jsonify({'error': 'name 不能为空'}), 400
        item.name = name
    if 'description' in data:
        item.description = data.get('description')
    if 'metadata' in data:
        metadata = data.get('metadata')
        item.metadata_json = json.dumps(metadata, ensure_ascii=False) if metadata is not None else None

    db.session.commit()
    return jsonify({'success': True, 'strategy_item': _strategy_item_to_dict(item)}), 200


@sales_twin_bp.route('/projects/<int:project_id>/strategy-items/<int:item_id>', methods=['DELETE'])
def delete_strategy_item(project_id, item_id):
    """删除战略项"""
    item = ProjectStrategyItem.query.filter_by(id=item_id, project_id=project_id).first()
    if not item:
        return jsonify({'error': '战略项不存在或不属于该项目'}), 404

    db.session.delete(item)
    db.session.commit()
    return jsonify({'success': True}), 200


# 允许的 WHY 上下文类型
ALLOWED_CONTEXT_TYPES = ('why', 'why_now', 'why_us')


def _why_context_to_dict(ctx):
    """WHY 上下文对象转字典"""
    return {
        'id': ctx.id,
        'project_id': ctx.project_id,
        'context_type': ctx.context_type,
        'context_text': ctx.context_text,
        'rationale': ctx.rationale,
        'created_at': ctx.created_at.isoformat() if ctx.created_at else None,
        'updated_at': ctx.updated_at.isoformat() if ctx.updated_at else None,
    }


@sales_twin_bp.route('/projects/<int:project_id>/why-contexts', methods=['GET'])
def list_why_contexts(project_id):
    """获取项目所有 WHY 上下文，按 context_type 分组返回

    每类至多 1 条（由唯一约束保证），未填写类型返回 null。
    响应：{ "why_contexts": { "why": {...}或null, "why_now": {...}或null, "why_us": {...}或null } }
    """
    get_project_or_404(project_id)
    contexts = ProjectWhyContext.query.filter_by(project_id=project_id).all()
    grouped = {t: None for t in ALLOWED_CONTEXT_TYPES}
    for ctx in contexts:
        if ctx.context_type in grouped:
            grouped[ctx.context_type] = _why_context_to_dict(ctx)
    return jsonify({'why_contexts': grouped}), 200


@sales_twin_bp.route('/projects/<int:project_id>/why-contexts', methods=['POST', 'PUT'])
def upsert_why_context(project_id):
    """新建或更新 WHY 上下文（upsert 语义：按 context_type 唯一）

    请求体：{ context_type, context_text, rationale? }
    - context_type 必须在 ['why', 'why_now', 'why_us']
    - context_text 不能为空
    - rationale 可选
    - 同一 (project_id, context_type) 已有记录则更新，否则新建
    """
    get_project_or_404(project_id)
    data = request.get_json() or {}
    context_type = data.get('context_type')
    context_text = (data.get('context_text') or '').strip()

    if context_type not in ALLOWED_CONTEXT_TYPES:
        return jsonify({'error': f'context_type 必须为 {list(ALLOWED_CONTEXT_TYPES)} 之一'}), 400
    if not context_text:
        return jsonify({'error': 'context_text 不能为空'}), 400

    rationale = data.get('rationale')

    # 按 (project_id, context_type) upsert：存在则更新，不存在则新建
    existing = ProjectWhyContext.query.filter_by(
        project_id=project_id, context_type=context_type
    ).first()
    if existing:
        existing.context_text = context_text
        existing.rationale = rationale
        ctx = existing
    else:
        ctx = ProjectWhyContext(
            project_id=project_id,
            context_type=context_type,
            context_text=context_text,
            rationale=rationale,
        )
        db.session.add(ctx)

    db.session.commit()
    return jsonify({'success': True, 'why_context': _why_context_to_dict(ctx)}), 200


@sales_twin_bp.route('/projects/<int:project_id>/why-contexts/<int:context_id>', methods=['DELETE'])
def delete_why_context(project_id, context_id):
    """删除 WHY 上下文（校验 context_id 属于该 project_id）"""
    ctx = ProjectWhyContext.query.filter_by(
        id=context_id, project_id=project_id
    ).first()
    if not ctx:
        return jsonify({'error': 'WHY 上下文不存在或不属于该项目'}), 404

    db.session.delete(ctx)
    db.session.commit()
    return jsonify({'success': True}), 200
