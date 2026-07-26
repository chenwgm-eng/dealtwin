"""自进化引擎 API — 推荐采纳/拒绝 + 学习模式管理"""
from datetime import datetime

from flask import request, jsonify

from app import db
from app.models.database import (
    AIRecommendationLog, AIRecommendationOutcome, LearningPattern,
    OpportunityTask, Stakeholder,
)
from app.api.sales_twin import sales_twin_bp
import json


@sales_twin_bp.route('/recommendations/<int:rec_id>/adopt', methods=['POST'])
def adopt_recommendation(rec_id):
    """采纳或拒绝推荐，记录 L1 反馈"""
    log = AIRecommendationLog.query.get_or_404(rec_id)
    data = request.get_json() or {}
    adopted = data.get('adopted', True)
    reject_reason = data.get('reject_reason')

    from app.services.outcome_tracker import OutcomeTracker
    tracker = OutcomeTracker()

    task = None
    if adopted:
        # 解析 structured_payload 创建 task
        payload = json.loads(log.structured_payload or '{}')
        # 复用现有 adopt-action 逻辑的核心部分
        action_type = payload.get('action_type', 'follow_up')
        type_map = {
            'build_alliance': 'build_alliance', 'address_concerns': 'address_concerns',
            'provide_material': 'provide_material', 'seek_intelligence': 'follow_up',
            'leverage_champion': 'build_alliance', 'blind_spot': 'blind_spot',
            'meeting': 'meeting', 'follow_up': 'follow_up'
        }
        task_type = type_map.get(action_type, 'follow_up')
        priority_score = payload.get('priority_score', 50)
        if priority_score >= 80:
            priority = 'high'
        elif priority_score >= 50:
            priority = 'medium'
        else:
            priority = 'low'

        # 查找目标干系人
        stakeholder_id = None
        target_name = payload.get('target_stakeholder')
        if target_name and target_name != '通用':
            sk = Stakeholder.query.filter_by(project_id=log.project_id, name=target_name).first()
            if sk:
                stakeholder_id = sk.id

        source_action = json.dumps({
            'action_type': action_type,
            'target_stakeholder': target_name,
            'priority_score': priority_score,
            'urgency': payload.get('urgency'),
            'reasoning': payload.get('reasoning'),
            'original_title': payload.get('title'),
            'recommendation_id': rec_id,
            'adopted_at': datetime.utcnow().isoformat()
        }, ensure_ascii=False)

        task = OpportunityTask(
            project_id=log.project_id,
            stakeholder_id=stakeholder_id,
            title=payload.get('title', '推荐行动'),
            description=payload.get('description', ''),
            task_type=task_type,
            priority=priority,
            status='pending',
            source='recommended_action',
            source_action=source_action
        )
        db.session.add(task)
        db.session.flush()

        tracker.record_l1_adoption(rec_id, adopted=True, task_id=task.id)
        db.session.commit()

        return jsonify({
            'success': True,
            'task': {
                'id': task.id, 'title': task.title, 'priority': task.priority,
                'status': task.status, 'project_id': task.project_id
            },
            'message': '推荐已采纳并创建待办'
        }), 200
    else:
        tracker.record_l1_adoption(rec_id, adopted=False, reject_reason=reject_reason)
        return jsonify({'success': True, 'message': '已记录拒绝原因'}), 200


@sales_twin_bp.route('/learning/patterns', methods=['GET'])
def get_learning_patterns():
    """获取学习模式列表"""
    status = request.args.get('status')
    query = LearningPattern.query
    if status:
        query = query.filter_by(status=status)
    patterns = query.order_by(LearningPattern.updated_at.desc()).all()
    return jsonify({
        'success': True,
        'patterns': [{
            'id': p.id,
            'pattern_type': p.pattern_type,
            'name': p.name,
            'trigger_conditions': json.loads(p.trigger_conditions_json) if p.trigger_conditions_json else {},
            'recommended_play': p.recommended_play,
            'evidence_count': p.evidence_count,
            'success_rate': p.success_rate,
            'status': p.status,
            'updated_at': p.updated_at.isoformat() if p.updated_at else None
        } for p in patterns]
    }), 200


@sales_twin_bp.route('/learning/patterns/<int:pattern_id>/approve', methods=['POST'])
def approve_pattern(pattern_id):
    p = LearningPattern.query.get_or_404(pattern_id)
    p.status = 'approved'
    db.session.commit()
    return jsonify({'success': True, 'message': '模式已准入生产'}), 200


@sales_twin_bp.route('/learning/patterns/<int:pattern_id>/deprecate', methods=['POST'])
def deprecate_pattern(pattern_id):
    p = LearningPattern.query.get_or_404(pattern_id)
    p.status = 'deprecated'
    db.session.commit()
    return jsonify({'success': True, 'message': '模式已废弃'}), 200
