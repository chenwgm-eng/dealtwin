"""阶段交付物路由"""
import os
from ._helpers import *  # noqa: E402, F401, F403
from ._helpers import sales_twin_bp  # noqa: E402, F401


@sales_twin_bp.route('/projects/<int:project_id>/stage-deliverables', methods=['GET'])
def get_stage_deliverables(project_id):
    """获取项目阶段交付物清单（含完成状态与完成率）

    可选 query 参数 ?stage=<stage>，不传时使用项目当前 sales_stage。
    """
    project = get_project_or_404(project_id)
    stage = request.args.get('stage') or project.sales_stage

    from app.services.stage_deliverable_manager import get_project_stage_deliverables
    result = get_project_stage_deliverables(project_id, stage)
    if result is None:
        # 阶段定义无效
        return jsonify({'error': '阶段定义无效'}), 400

    return jsonify(result), 200



@sales_twin_bp.route('/projects/<int:project_id>/stage-deliverables/<deliverable_key>', methods=['PUT'])
def update_stage_deliverable(project_id, deliverable_key):
    """更新单个交付物项的完成状态与备注

    可选 query 参数 ?stage=<stage>，不传时使用项目当前 sales_stage。
    body: { is_completed: bool, notes?: string }
    """
    project = get_project_or_404(project_id)
    data = request.get_json() or {}
    if 'is_completed' not in data:
        return jsonify({'error': '缺少必填字段 is_completed'}), 400

    is_completed = data.get('is_completed')
    notes = data.get('notes')
    stage = request.args.get('stage') or project.sales_stage

    from app.services.stage_deliverable_manager import update_deliverable_status
    result = update_deliverable_status(project_id, stage, deliverable_key, is_completed, notes)
    if result is None:
        return jsonify({'error': '阶段定义无效'}), 400

    return jsonify(result), 200



@sales_twin_bp.route('/projects/<int:project_id>/stage-deliverables/<path:deliverable_key>/attachments', methods=['POST'])
def upload_stage_deliverable_attachments(project_id, deliverable_key):
    """为阶段交付物上传附件（技术方案、商务方案等系统无对应上下文的材料）

    body: multipart/form-data, field 'files' (支持多文件)
    可选 query 参数 ?stage=<stage>，不传时使用项目当前 sales_stage。
    """
    project = get_project_or_404(project_id)
    stage = request.args.get('stage') or project.sales_stage

    # 校验 deliverable_key 在该阶段定义中存在
    from app.services.stage_deliverable_manager import get_stage_definition, _flatten_deliverable_keys
    stage_definition = get_stage_definition(stage)
    if not stage_definition:
        return jsonify({'error': '阶段定义无效'}), 400
    all_keys = _flatten_deliverable_keys(stage_definition)
    if deliverable_key not in all_keys:
        return jsonify({'error': f'交付物键 {deliverable_key} 不属于阶段 {stage}'}), 400

    files = request.files.getlist('files')
    if not files or all(not f.filename for f in files):
        return jsonify({'error': '未检测到上传文件'}), 400

    # 确保附件目录存在：uploads/stage_deliverable_attachments/<project_id>/<stage>/<deliverable_key>/
    # deliverable_key 含点号（group_key.item_key），将点号替换为下划线避免文件系统歧义
    safe_key = deliverable_key.replace('.', '_')
    record_dir = os.path.join(STAGE_DELIVERABLE_ATTACHMENT_DIR, str(project_id), stage, safe_key)
    os.makedirs(record_dir, exist_ok=True)

    # 查找或创建 StageDeliverable 记录
    record = StageDeliverable.query.filter_by(
        project_id=project_id, stage=stage, deliverable_key=deliverable_key
    ).first()

    # 解析已有附件
    try:
        existing = json.loads(record.attachments) if (record and record.attachments) else []
    except (json.JSONDecodeError, TypeError):
        existing = []

    new_attachments = []
    for f in files:
        if not f or not f.filename or not _allowed_attachment(f.filename):
            continue
        original_filename = f.filename  # 保留原始文件名用于展示
        ext = os.path.splitext(f.filename)[1]  # 保留扩展名
        stored_filename = f'{uuid.uuid4().hex}{ext}'  # 存储名用 uuid 避免中文/冲突
        f.save(os.path.join(record_dir, stored_filename))
        size = os.path.getsize(os.path.join(record_dir, stored_filename))
        new_attachments.append({
            'filename': stored_filename,
            'original_filename': original_filename,
            'size': size,
            'uploaded_at': datetime.utcnow().isoformat()
        })

    if not new_attachments:
        return jsonify({'error': '所有文件类型不被允许'}), 400

    all_attachments = existing + new_attachments
    if record is None:
        # 防御性：创建记录（不修改 is_completed 状态）
        record = StageDeliverable(
            project_id=project_id,
            stage=stage,
            deliverable_key=deliverable_key,
            is_completed=False,
            completed_at=None,
            attachments=json.dumps(all_attachments, ensure_ascii=False),
        )
        db.session.add(record)
    else:
        record.attachments = json.dumps(all_attachments, ensure_ascii=False)
    db.session.commit()

    return jsonify({
        'success': True,
        'deliverable_key': deliverable_key,
        'attachments': all_attachments,
        'added': len(new_attachments),
        'message': f'已上传 {len(new_attachments)} 个附件'
    }), 200



@sales_twin_bp.route('/projects/<int:project_id>/stage-deliverables/<path:deliverable_key>/attachments/<path:filename>', methods=['GET'])
def download_stage_deliverable_attachment(project_id, deliverable_key, filename):
    """下载阶段交付物附件"""
    if '/' in filename or '\\' in filename or '..' in filename:
        return jsonify({'error': '非法文件名'}), 404
    project = get_project_or_404(project_id)
    stage = request.args.get('stage') or project.sales_stage

    record = StageDeliverable.query.filter_by(
        project_id=project_id, stage=stage, deliverable_key=deliverable_key
    ).first()
    if not record:
        return jsonify({'error': '交付物记录不存在'}), 404

    try:
        attachments = json.loads(record.attachments) if record.attachments else []
    except (json.JSONDecodeError, TypeError):
        attachments = []
    matched = next((a for a in attachments if a.get('filename') == filename), None)
    if not matched:
        return jsonify({'error': '附件不存在'}), 404

    safe_key = deliverable_key.replace('.', '_')
    record_dir = os.path.join(STAGE_DELIVERABLE_ATTACHMENT_DIR, str(project_id), stage, safe_key)
    return send_from_directory(
        record_dir,
        filename,
        as_attachment=True,
        download_name=matched.get('original_filename', filename)
    ), 200



@sales_twin_bp.route('/projects/<int:project_id>/stage-deliverables/<path:deliverable_key>/attachments/<path:filename>', methods=['DELETE'])
def delete_stage_deliverable_attachment(project_id, deliverable_key, filename):
    """删除阶段交付物附件"""
    if '/' in filename or '\\' in filename or '..' in filename:
        return jsonify({'error': '非法文件名'}), 404
    project = get_project_or_404(project_id)
    stage = request.args.get('stage') or project.sales_stage

    record = StageDeliverable.query.filter_by(
        project_id=project_id, stage=stage, deliverable_key=deliverable_key
    ).first()
    if not record:
        return jsonify({'error': '交付物记录不存在'}), 404

    try:
        attachments = json.loads(record.attachments) if record.attachments else []
    except (json.JSONDecodeError, TypeError):
        attachments = []
    matched = next((a for a in attachments if a.get('filename') == filename), None)
    if not matched:
        return jsonify({'error': '附件不存在'}), 404

    # 从磁盘删除
    safe_key = deliverable_key.replace('.', '_')
    file_path = os.path.join(STAGE_DELIVERABLE_ATTACHMENT_DIR, str(project_id), stage, safe_key, filename)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except OSError:
            pass

    # 从 attachments 字段移除
    attachments = [a for a in attachments if a.get('filename') != filename]
    record.attachments = json.dumps(attachments, ensure_ascii=False) if attachments else None
    db.session.commit()

    return jsonify({
        'success': True,
        'deliverable_key': deliverable_key,
        'attachments': attachments,
        'message': '附件已删除'
    }), 200



@sales_twin_bp.route('/projects/<int:project_id>/stage-check', methods=['POST'])
def run_stage_check(project_id):
    """执行阶段准入检查，返回推进建议

    使用项目当前 sales_stage 进行检查；可通过 ?stage=<stage_name> 指定其他阶段。
    """
    project = get_project_or_404(project_id)

    from app.services.stage_deliverable_manager import check_stage_readiness
    stage = request.args.get('stage')
    result = check_stage_readiness(project_id, stage=stage)
    if result is None:
        return jsonify({'error': '阶段定义无效'}), 400

    return jsonify(result), 200



@sales_twin_bp.route('/projects/<int:project_id>/stage-timeline', methods=['GET'])
def get_stage_timeline(project_id):
    """获取项目阶段时间线"""
    from app.services.stage_deliverable_manager import get_project_stage_timeline
    try:
        result = get_project_stage_timeline(project_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
