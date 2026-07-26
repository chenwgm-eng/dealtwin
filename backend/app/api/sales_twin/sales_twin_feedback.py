"""反馈记录与状态日志路由"""
import os
from ._helpers import *  # noqa: E402, F401, F403
from ._helpers import sales_twin_bp  # noqa: E402, F401


@sales_twin_bp.route('/projects/<int:project_id>/feedback', methods=['POST'])
def submit_feedback(project_id):
    """提交销售反馈，自动更新干系人状态（支持关联待办事项 + 附件上传）

    支持两种提交方式：
    1. JSON: {feedback, related_task_ids, related_meeting_plan_id}
    2. multipart/form-data: feedback(文本) + related_task_ids(JSON字符串) + related_meeting_plan_id + files(多文件)
       附件作为LLM解析的输入上下文之一
    """
    # 判断请求类型
    if request.content_type and 'multipart/form-data' in request.content_type:
        # multipart 模式：带附件提交
        feedback_text = request.form.get('feedback', '').strip()
        if not feedback_text:
            return jsonify({'error': '缺少feedback字段'}), 400

        # 解析关联待办
        related_task_ids_str = request.form.get('related_task_ids', '[]')
        try:
            related_task_ids = json.loads(related_task_ids_str) if related_task_ids_str else []
        except (json.JSONDecodeError, TypeError):
            related_task_ids = []

        related_meeting_plan_id = request.form.get('related_meeting_plan_id')
        if related_meeting_plan_id in ('', 'null', 'None'):
            related_meeting_plan_id = None
        else:
            try:
                related_meeting_plan_id = int(related_meeting_plan_id)
            except (ValueError, TypeError):
                related_meeting_plan_id = None

        # 收集上传的附件元信息（作为LLM解析输入）
        files = request.files.getlist('files')
        attachment_infos = []
        valid_files = []
        for f in files:
            if not f or not f.filename or not _allowed_attachment(f.filename):
                continue
            original_filename = f.filename  # 保留原始文件名用于展示
            ext = os.path.splitext(f.filename)[1]  # 保留扩展名
            stored_filename = f'{uuid.uuid4().hex}{ext}'  # 存储名用 uuid 避免中文/冲突
            type_ext = ext.lstrip('.').lower() if ext else ''
            attachment_infos.append({
                'filename': original_filename,
                'type': type_ext,
                'description': f'会议材料：{original_filename}'
            })
            valid_files.append((f, stored_filename, original_filename))

        from app.services.feedback_parser import FeedbackParserService
        parser = FeedbackParserService()
        result = parser.parse_feedback(
            project_id,
            feedback_text,
            related_task_ids=related_task_ids,
            related_meeting_plan_id=related_meeting_plan_id,
            attachment_infos=attachment_infos
        )

        # 保存附件到对应记录目录
        feedback_id = result.get('feedback_id')
        if feedback_id and valid_files:
            record_dir = os.path.join(FEEDBACK_ATTACHMENT_DIR, str(feedback_id))
            os.makedirs(record_dir, exist_ok=True)
            saved_attachments = []
            for f, stored_filename, original_filename in valid_files:
                f.save(os.path.join(record_dir, stored_filename))
                size = os.path.getsize(os.path.join(record_dir, stored_filename))
                saved_attachments.append({
                    'filename': stored_filename,
                    'original_filename': original_filename,
                    'size': size,
                    'uploaded_at': datetime.utcnow().isoformat()
                })
            # 更新记录的 attachments 字段
            record = FeedbackRecord.query.get(feedback_id)
            if record:
                record.attachments = json.dumps(saved_attachments, ensure_ascii=False)
                db.session.commit()
            result['attachments'] = saved_attachments
            result['attachment_count'] = len(saved_attachments)

        return jsonify(result), 200

    # JSON 模式：无附件
    data = request.get_json()
    if 'feedback' not in data:
        return jsonify({'error': '缺少feedback字段'}), 400

    from app.services.feedback_parser import FeedbackParserService
    parser = FeedbackParserService()
    result = parser.parse_feedback(
        project_id,
        data['feedback'],
        related_task_ids=data.get('related_task_ids'),
        related_meeting_plan_id=data.get('related_meeting_plan_id')
    )

    return jsonify(result), 200



@sales_twin_bp.route('/projects/<int:project_id>/state-logs', methods=['GET'])
def get_state_logs(project_id):
    """获取状态变更日志"""
    limit = request.args.get('limit', 50, type=int)
    
    from app.services.feedback_parser import FeedbackParserService
    
    parser = FeedbackParserService()
    result = parser.get_state_logs(project_id, limit=limit)
    
    return jsonify(result), 200



@sales_twin_bp.route('/projects/<int:project_id>/feedback-records', methods=['GET'])
def get_feedback_records(project_id):
    """获取项目所有反馈记录"""
    records = FeedbackRecord.query.filter_by(project_id=project_id).order_by(
        FeedbackRecord.created_at.desc()
    ).all()
    return jsonify({
        'records': [feedback_record_to_dict(r) for r in records],
        'total': len(records)
    }), 200



@sales_twin_bp.route('/feedback-records/<int:record_id>', methods=['GET'])
def get_feedback_record(record_id):
    """获取单条反馈记录的完整内容（用于查看完整会议记录）"""
    record = FeedbackRecord.query.get_or_404(record_id)
    return jsonify({
        'record': feedback_record_to_dict(record)
    }), 200



@sales_twin_bp.route('/feedback-records/<int:record_id>/attachments', methods=['POST'])
def upload_feedback_attachments(record_id):
    """为拜访记录上传附件（会议纪要、材料等）"""
    record = FeedbackRecord.query.get_or_404(record_id)
    files = request.files.getlist('files')
    if not files or all(not f.filename for f in files):
        return jsonify({'error': '未检测到上传文件'}), 400

    # 确保附件目录存在
    record_dir = os.path.join(FEEDBACK_ATTACHMENT_DIR, str(record_id))
    os.makedirs(record_dir, exist_ok=True)

    # 解析已有附件
    try:
        existing = json.loads(record.attachments) if record.attachments else []
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
    record.attachments = json.dumps(all_attachments, ensure_ascii=False)
    record.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({
        'success': True,
        'record': feedback_record_to_dict(record),
        'added': len(new_attachments),
        'message': f'已上传 {len(new_attachments)} 个附件'
    }), 200



@sales_twin_bp.route('/feedback-records/<int:record_id>/attachments/<path:filename>', methods=['GET'])
def download_feedback_attachment(record_id, filename):
    """下载拜访记录附件"""
    if '/' in filename or '\\' in filename or '..' in filename:
        return jsonify({'error': '非法文件名'}), 404
    record = FeedbackRecord.query.get_or_404(record_id)
    # 安全校验：filename 必须在该记录的 attachments 列表中
    try:
        attachments = json.loads(record.attachments) if record.attachments else []
    except (json.JSONDecodeError, TypeError):
        attachments = []
    matched = next((a for a in attachments if a.get('filename') == filename), None)
    if not matched:
        return jsonify({'error': '附件不存在'}), 404

    record_dir = os.path.join(FEEDBACK_ATTACHMENT_DIR, str(record_id))
    return send_from_directory(
        record_dir,
        filename,
        as_attachment=True,
        download_name=matched.get('original_filename', filename)
    ), 200



@sales_twin_bp.route('/feedback-records/<int:record_id>/attachments/<path:filename>', methods=['DELETE'])
def delete_feedback_attachment(record_id, filename):
    """删除拜访记录附件"""
    if '/' in filename or '\\' in filename or '..' in filename:
        return jsonify({'error': '非法文件名'}), 404
    record = FeedbackRecord.query.get_or_404(record_id)
    try:
        attachments = json.loads(record.attachments) if record.attachments else []
    except (json.JSONDecodeError, TypeError):
        attachments = []
    matched = next((a for a in attachments if a.get('filename') == filename), None)
    if not matched:
        return jsonify({'error': '附件不存在'}), 404

    # 从磁盘删除
    file_path = os.path.join(FEEDBACK_ATTACHMENT_DIR, str(record_id), filename)
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
        'record': feedback_record_to_dict(record),
        'message': '附件已删除'
    }), 200



