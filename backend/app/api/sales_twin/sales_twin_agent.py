"""白泽 Agent 调度中枢 API — 后台定时任务生命周期管理

提供 5 个路由：
- GET    /agent/jobs                获取任务列表
- POST   /agent/jobs/<id>/pause     暂停任务
- POST   /agent/jobs/<id>/resume    恢复任务
- POST   /agent/jobs/<id>/run       立即执行一次（不影响原时间表）
- PUT    /agent/jobs/<id>/schedule  更新 cron 规则
"""
from datetime import datetime, timezone

from flask import request, jsonify

from app.api.sales_twin import sales_twin_bp
from app.extensions import scheduler


def _parse_cron_expr(trigger) -> str:
    """从 APScheduler CronTrigger 解析为标准 5 字段 cron 表达式（分 时 日 月 周）

    APScheduler CronTrigger.fields 顺序为 year/month/day/week/day_of_week/hour/minute/second，
    取 minute hour day month day_of_week 组成标准格式。
    """
    try:
        if hasattr(trigger, 'fields') and trigger.fields:
            # fields 是按固定顺序排列的列表，通过 name 索引更稳健
            field_map = {f.name: str(f) for f in trigger.fields}
            minute = field_map.get('minute', '*')
            hour = field_map.get('hour', '*')
            day = field_map.get('day', '*')
            month = field_map.get('month', '*')
            day_of_week = field_map.get('day_of_week', '*')
            return f'{minute} {hour} {day} {month} {day_of_week}'
    except Exception:
        pass
    return str(trigger) if trigger else 'N/A'


@sales_twin_bp.route('/agent/jobs', methods=['GET'])
def get_agent_jobs():
    """获取所有后台 Agent 任务及调度信息"""
    jobs = scheduler.get_jobs()
    job_list = []
    for job in jobs:
        # 使用 getattr 防御 pending job 未计算 next_run_time 的情况
        next_run_time = getattr(job, 'next_run_time', None)
        job_list.append({
            'id': job.id,
            'name': job.name or job.id,
            'next_run_time': next_run_time.isoformat() if next_run_time else None,
            'is_paused': next_run_time is None,
            'cron_expr': _parse_cron_expr(job.trigger),
        })
    return jsonify({'success': True, 'data': job_list}), 200


@sales_twin_bp.route('/agent/jobs/<job_id>/pause', methods=['POST'])
def pause_job(job_id):
    """暂停指定任务"""
    try:
        scheduler.pause_job(job_id)
        return jsonify({'success': True, 'message': f'任务 {job_id} 已暂停'}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': f'暂停失败: {e}'}), 400


@sales_twin_bp.route('/agent/jobs/<job_id>/resume', methods=['POST'])
def resume_job(job_id):
    """恢复指定任务"""
    try:
        scheduler.resume_job(job_id)
        return jsonify({'success': True, 'message': f'任务 {job_id} 已恢复'}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': f'恢复失败: {e}'}), 400


@sales_twin_bp.route('/agent/jobs/<job_id>/run', methods=['POST'])
def run_job_now(job_id):
    """立即异步执行一次任务，不影响原有时间表"""
    try:
        scheduler.modify_job(job_id, next_run_time=datetime.now(timezone.utc))
        return jsonify({'success': True, 'message': f'任务 {job_id} 已触发执行'}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': f'触发失败: {e}'}), 400


@sales_twin_bp.route('/agent/jobs/<job_id>/schedule', methods=['PUT'])
def update_job_schedule(job_id):
    """更新任务的 cron 规则

    Body: {"hour": "2", "minute": "0", "day_of_week": "*"}
    """
    data = request.get_json() or {}
    hour = data.get('hour', '*')
    minute = data.get('minute', '0')
    day_of_week = data.get('day_of_week', '*')

    try:
        scheduler.modify_job(
            job_id,
            trigger='cron',
            hour=hour,
            minute=minute,
            day_of_week=day_of_week,
        )
        return jsonify({'success': True, 'message': f'任务 {job_id} 定时规则已更新'}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': f'更新失败: {e}'}), 400


@sales_twin_bp.route('/agent/jobs/<job_id>/runs', methods=['GET'])
def get_job_runs(job_id):
    """获取指定任务的最近运行历史记录

    Query: limit (默认 10，最大 50)
    """
    from app.models.database import AgentJobRun

    limit = request.args.get('limit', 10, type=int)
    limit = max(1, min(limit, 50))

    runs = AgentJobRun.query.filter_by(job_id=job_id) \
        .order_by(AgentJobRun.started_at.desc()).limit(limit).all()

    run_list = []
    for r in runs:
        run_list.append({
            'id': r.id,
            'job_id': r.job_id,
            'started_at': r.started_at.isoformat() if r.started_at else None,
            'finished_at': r.finished_at.isoformat() if r.finished_at else None,
            'status': r.status,
            'items_processed': r.items_processed,
            'items_succeeded': r.items_succeeded,
            'summary': r.summary or '',
            'error_message': r.error_message or '',
        })
    return jsonify({'success': True, 'data': run_list}), 200
