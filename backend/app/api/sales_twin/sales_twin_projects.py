"""项目 CRUD 与 Dashboard 路由"""
from ._helpers import *  # noqa: E402, F401, F403
from ._helpers import sales_twin_bp  # noqa: E402, F401
from .sales_twin_milestones import VALID_SALES_MODES  # noqa: E402, F401

# 合法关闭原因分类
VALID_CLOSE_REASONS = ('price', 'product', 'relationship', 'competition', 'timing', 'no_decision', 'other')


@sales_twin_bp.route('/projects', methods=['POST'])
def create_project():
    """创建项目"""
    data = request.get_json()

    required_fields = ['name']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'缺少必填字段: {field}'}), 400

    # 销售模式枚举校验（None 表示不设置）
    sales_mode = data.get('sales_mode')
    if sales_mode in ('', 'null'):
        sales_mode = None
    if sales_mode is not None and sales_mode not in VALID_SALES_MODES:
        return jsonify({'error': f'非法销售模式: {sales_mode}，可选值: {"/".join(VALID_SALES_MODES)} 或 null'}), 400

    project = Project(
        name=data['name'],
        customer_name=data.get('customer_name'),
        sales_stage=data.get('sales_stage', 'suspect'),
        budget=data.get('budget'),
        industry=data.get('industry'),
        company_vision=data.get('company_vision'),
        business_pain_points=data.get('business_pain_points'),
        expected_close_date=_parse_date(data.get('expected_close_date')),
        time_certainty=data.get('time_certainty'),
        budget_certainty=data.get('budget_certainty'),
        tendency=data.get('tendency'),
        sales_mode=sales_mode,
        # 数据归属：商业版记录创建者（scope provider 注入时）；社区版恒为 None
        owner_id=current_owner_id(),
    )
    
    db.session.add(project)
    db.session.commit()
    
    return jsonify({'project': project_to_dict(project)}), 200



@sales_twin_bp.route('/projects', methods=['GET'])
def get_projects():
    """获取项目列表（支持 ?page=1&per_page=20 分页）"""
    page, per_page = _parse_pagination_params()

    query = apply_project_scope(Project.query).order_by(Project.id)
    total = query.count()
    projects = query.offset((page - 1) * per_page).limit(per_page).all()
    items = [project_to_dict(p) for p in projects]
    has_next = (page * per_page) < total
    return jsonify({
        'projects': items,
        'items': items,
        'total': total,
        'page': page,
        'per_page': per_page,
        'has_next': has_next,
    }), 200



def _build_dashboard_expected_close(start_date, end_date):
    """预计关单视角：按 expected_close_date 聚合，按 sales_stage 分组"""
    expected_projects = apply_project_scope(Project.query).filter(
        Project.expected_close_date.between(start_date, end_date)
    ).all()

    lead_amount = 0.0
    lead_count = 0
    opportunity_amount = 0.0
    opportunity_count = 0
    breakdown_identity = {'amount': 0.0, 'count': 0}
    breakdown_define = {'amount': 0.0, 'count': 0}
    breakdown_confirm = {'amount': 0.0, 'count': 0}

    for p in expected_projects:
        budget = p.budget or 0.0
        stage = p.sales_stage
        if stage == 'suspect':
            lead_amount += budget
            lead_count += 1
        elif stage in ('identity', 'define', 'confirm'):
            opportunity_amount += budget
            opportunity_count += 1
            if stage == 'identity':
                breakdown_identity['amount'] += budget
                breakdown_identity['count'] += 1
            elif stage == 'define':
                breakdown_define['amount'] += budget
                breakdown_define['count'] += 1
            elif stage == 'confirm':
                breakdown_confirm['amount'] += budget
                breakdown_confirm['count'] += 1

    return {
        'lead_amount': round(lead_amount, 2),
        'lead_count': lead_count,
        'opportunity_amount': round(opportunity_amount, 2),
        'opportunity_count': opportunity_count,
        'opportunity_breakdown': {
            'identity': {
                'amount': round(breakdown_identity['amount'], 2),
                'count': breakdown_identity['count'],
            },
            'define': {
                'amount': round(breakdown_define['amount'], 2),
                'count': breakdown_define['count'],
            },
            'confirm': {
                'amount': round(breakdown_confirm['amount'], 2),
                'count': breakdown_confirm['count'],
            },
        },
    }


def _build_dashboard_actual_close(start_date, end_date):
    """实际关单视角：按 updated_at 在时间范围内，closed_won/closed_lost 聚合

    注意类型转换：expected_close_date 是 Date，updated_at 是 DateTime
    """
    start_dt = datetime.combine(start_date, datetime.min.time())
    end_dt = datetime.combine(end_date, datetime.max.time())
    closed_projects = Project.query.filter(
        Project.sales_stage.in_(['closed_won', 'closed_lost']),
        Project.updated_at.between(start_dt, end_dt),
    ).all()

    won_amount = 0.0
    won_count = 0
    lost_amount = 0.0
    lost_count = 0
    for p in closed_projects:
        budget = p.budget or 0.0
        if p.sales_stage == 'closed_won':
            won_amount += budget
            won_count += 1
        elif p.sales_stage == 'closed_lost':
            lost_amount += budget
            lost_count += 1

    total_closed = won_count + lost_count
    win_rate = round(won_count / total_closed * 100, 1) if total_closed > 0 else None

    return {
        'won_amount': round(won_amount, 2),
        'won_count': won_count,
        'lost_amount': round(lost_amount, 2),
        'lost_count': lost_count,
        'win_rate': win_rate,
    }


def _build_dashboard_attention_items(now):
    """重点关注事项（跨所有项目，不受时间范围限制）"""
    # 逾期待办：due_date < now 且 status 不在 completed/cancelled；先查 top5 再查总数
    overdue_tasks_q = scope_model_query(OpportunityTask.query.filter(
        OpportunityTask.due_date < now,
        ~OpportunityTask.status.in_(['completed', 'cancelled']),
    ), OpportunityTask).order_by(OpportunityTask.due_date.asc())
    overdue_tasks = overdue_tasks_q.limit(5).all()
    overdue_count = overdue_tasks_q.count()

    # 批量预加载逾期任务对应的项目名映射，避免循环内 Project.query.get 产生 N+1
    overdue_proj_ids = {t.project_id for t in overdue_tasks if t.project_id}
    overdue_proj_map = {
        p.id: p.name for p in Project.query.filter(Project.id.in_(overdue_proj_ids)).all()
    } if overdue_proj_ids else {}

    overdue_tasks_list = []
    for t in overdue_tasks:
        project_name = overdue_proj_map.get(t.project_id, '') if t.project_id else ''
        overdue_tasks_list.append({
            'id': t.id,
            'title': t.title,
            'project_id': t.project_id,
            'project_name': project_name,
            'due_date': t.due_date.isoformat() if t.due_date else None,
            'priority': t.priority,
        })

    # 今日到期待办数：DATE(due_date)=CURRENT_DATE AND status IN ('pending','in_progress')
    today_due_count = scope_model_query(OpportunityTask.query.filter(
        db.func.date(OpportunityTask.due_date) == db.func.current_date(),
        OpportunityTask.status.in_(['pending', 'in_progress']),
    ), OpportunityTask).count()

    # 待识别干系人数
    pending_stakeholders_count = scope_model_query(
        Stakeholder.query.filter_by(status='pending'), Stakeholder
    ).count()

    # 红色触达状态联系人数（客户级数据，商业版内全员可见，不按项目隔离）
    red_contacts_count = Contact.query.filter_by(interaction_status_override='red').count()

    # 待处理拜访预案数（pending/generated）
    pending_plans_count = scope_model_query(MeetingPlan.query.filter(
        MeetingPlan.status.in_(['pending', 'generated'])
    ), MeetingPlan).count()

    return {
        'overdue_tasks': overdue_tasks_list,
        'overdue_count': overdue_count,
        'today_due_count': today_due_count,
        'pending_stakeholders_count': pending_stakeholders_count,
        'red_contacts_count': red_contacts_count,
        'pending_plans_count': pending_plans_count,
    }


def _build_dashboard_recent_changes(now):
    """近30天状态变更摘要（用于 LLM 上下文）"""
    thirty_days_ago = now - timedelta(days=30)
    recent_state_logs = StateChangeLog.query.filter(
        StateChangeLog.created_at >= thirty_days_ago
    ).order_by(StateChangeLog.created_at.desc()).limit(30).all()

    # 预加载项目名映射，避免逐条查询
    proj_ids = {log.project_id for log in recent_state_logs}
    proj_name_map = {
        p.id: p.name for p in Project.query.filter(Project.id.in_(proj_ids)).all()
    } if proj_ids else {}

    recent_state_changes = []
    for log in recent_state_logs:
        project_name = proj_name_map.get(log.project_id, f'#{log.project_id}')
        ts = log.created_at.strftime('%Y-%m-%d %H:%M') if log.created_at else ''
        text = (
            f"[{ts}] {project_name} - "
            f"{log.change_object or ''}.{log.attribute_name or ''}: "
            f"{log.old_value or ''} → {log.new_value or ''}"
        )
        recent_state_changes.append(text)
    return recent_state_changes


def _build_dashboard_insights(start_date, end_date, period, label, dashboard_data):
    """构造 dashboard_data 并调用 LLM 生成洞察（含缓存）

    先查缓存，命中则跳过 LLM 调用；未命中才调用 LLM 并写入缓存。
    加锁避免并发请求重复调用 LLM 并竞争写缓存。
    """
    with _dashboard_insight_lock:
        cached_insights = _get_cached_insights(start_date, end_date)
        if cached_insights is not None:
            logger.info(f"Dashboard 洞察缓存命中: {label} ({start_date} ~ {end_date})")
            return cached_insights
        generator = DashboardInsightGenerator()
        llm_insights = generator.generate(dashboard_data)
        # LLM 失败时不写缓存（避免错误结果被缓存），仅返回 fallback
        if generator.last_error:
            logger.warning(f"Dashboard 智能洞察 LLM 调用失败，未写入缓存: {label} ({start_date} ~ {end_date})")
        else:
            _save_insights_to_cache(start_date, end_date, period, label, llm_insights)
            logger.info(f"Dashboard 洞察已生成并写入缓存: {label} ({start_date} ~ {end_date})")
    return llm_insights


@sales_twin_bp.route('/dashboard', methods=['GET'])
def get_dashboard():
    """销售 Dashboard 聚合 API

    返回结构：{time_range, expected_close, actual_close, attention_items, llm_insights}
    - expected_close：按 expected_close_date 在时间范围内的项目，按 sales_stage 聚合
    - actual_close：按 updated_at 在时间范围内的 closed_won/closed_lost 项目聚合
    - attention_items：跨所有项目的重点关注事项（不受时间范围限制）
    - llm_insights：基于聚合数据由 LLM 生成的跨项目洞察
    """
    period = request.args.get('period')
    start = request.args.get('start')
    end = request.args.get('end')
    start_date, end_date, label = _resolve_dashboard_time_range(period, start, end)

    expected_close = _build_dashboard_expected_close(start_date, end_date)
    actual_close = _build_dashboard_actual_close(start_date, end_date)
    now = datetime.utcnow()
    attention_items = _build_dashboard_attention_items(now)
    recent_state_changes = _build_dashboard_recent_changes(now)

    time_range = {
        'label': label,
        'start': start_date.isoformat(),
        'end': end_date.isoformat(),
    }
    dashboard_data = {
        'time_range': time_range,
        'expected_close': expected_close,
        'actual_close': actual_close,
        'attention_items': attention_items,
        'recent_state_changes': recent_state_changes,
    }
    llm_insights = _build_dashboard_insights(start_date, end_date, period, label, dashboard_data)

    result = {
        'time_range': time_range,
        'expected_close': expected_close,
        'actual_close': actual_close,
        'attention_items': attention_items,
        'llm_insights': llm_insights,
    }
    return jsonify(result), 200



@sales_twin_bp.route('/dashboard/insights/refresh', methods=['POST'])
def refresh_dashboard_insights():
    """强制刷新 Dashboard 智能洞察：删除指定时间范围的缓存

    简化方案：仅删除缓存，前端收到响应后再调用 GET /dashboard（此时缓存已清，会重新调用 LLM 生成新洞察并写入缓存）。

    请求体: {period?, start?, end?}
    响应: {time_range: {label, start, end}, message: str}
    """
    data = request.get_json(silent=True) or {}
    period = data.get('period')
    start = data.get('start')
    end = data.get('end')
    start_date, end_date, label = _resolve_dashboard_time_range(period, start, end)

    # 删除旧缓存（仅当前数据权限范围的缓存，避免误删其他用户的）
    try:
        DashboardInsightCache.query.filter_by(
            start_date=start_date, end_date=end_date, scope_key=current_scope_key()
        ).delete()
        db.session.commit()
    except Exception as e:
        logger.warning(f"删除旧洞察缓存失败: {e}")
        db.session.rollback()

    return jsonify({
        'time_range': {
            'label': label,
            'start': start_date.isoformat(),
            'end': end_date.isoformat(),
        },
        'message': '缓存已清除，请重新调用 GET /dashboard 获取新洞察'
    }), 200



@sales_twin_bp.route('/projects/<int:project_id>', methods=['GET'])
def get_project(project_id):
    """获取项目详情"""
    project = get_project_or_404(project_id)
    return jsonify({'project': project_to_dict(project)}), 200



@sales_twin_bp.route('/projects/<int:project_id>', methods=['PUT'])
def update_project(project_id):
    """更新项目（关键字段变更记录到StateChangeLog）"""
    project = get_project_or_404(project_id)
    data = request.get_json()

    # 需要记录变更日志的字段
    logged_fields = {
        'name': '项目名称',
        'customer_id': '关联客户',
        'customer_name': '客户名称',
        'sales_stage': '销售阶段',
        'budget': '预算',
        'expected_close_date': '预计关闭时间',
        'industry': '行业',
        'company_vision': '公司愿景',
        'business_pain_points': '业务痛点',
        'customer_background': '客户背景与需求',
        'value_proposition': '价值主张',
        'competitive_analysis': '竞争分析',
        'sales_mode': '销售模式',
    }

    # 销售模式枚举校验（None 表示清除）
    if 'sales_mode' in data:
        if data['sales_mode'] is None or data['sales_mode'] in ('', 'null'):
            data['sales_mode'] = None
        elif data['sales_mode'] not in VALID_SALES_MODES:
            return jsonify({'error': f'非法销售模式: {data["sales_mode"]}，可选值: {"/".join(VALID_SALES_MODES)} 或 null'}), 400

    reasoning = data.get('edit_reason') or '手动编辑'
    change_logs = []

    for field, label in logged_fields.items():
        if field not in data:
            continue
        old_val = getattr(project, field)
        new_val = data[field]
        # 日期字段处理
        if field == 'expected_close_date':
            if new_val in ('', None):
                new_val = None
            elif isinstance(new_val, str):
                try:
                    from datetime import date as date_type
                    new_val = date_type.fromisoformat(new_val[:10])
                except (ValueError, TypeError):
                    continue
        # 预算字段类型转换
        if field == 'budget':
            if new_val in ('', None):
                new_val = None
            else:
                try:
                    new_val = float(new_val)
                except (TypeError, ValueError):
                    continue
        # customer_id 处理：空值转 None，同时联动更新 customer_name
        if field == 'customer_id':
            if new_val in ('', None, 0):
                new_val = None
            else:
                try:
                    new_val = int(new_val)
                except (TypeError, ValueError):
                    continue
            # 联动更新 customer_name
            if new_val is None:
                project.customer_name = None
            else:
                customer = Customer.query.get(new_val)
                if customer:
                    project.customer_name = customer.name
                else:
                    continue  # 客户不存在，跳过
        # 比较旧值和新值
        old_str = old_val.isoformat() if hasattr(old_val, 'isoformat') and old_val else (str(old_val) if old_val is not None else '')
        new_str = new_val.isoformat() if hasattr(new_val, 'isoformat') and new_val else (str(new_val) if new_val is not None else '')
        if old_str == new_str:
            continue
        # 记录变更日志
        log = StateChangeLog(
            project_id=project_id,
            stakeholder_id=None,
            change_object=project.name,
            attribute_name=field,
            old_value=old_str or '空',
            new_value=new_str or '空',
            reasoning=reasoning,
            change_source='manual_edit'
        )
        db.session.add(log)
        change_logs.append({'field': field, 'label': label, 'old': old_str, 'new': new_str})
        setattr(project, field, new_val)

    # 确定性/倾向性（1=红/2=黄/3=绿）
    for cert_field in ('time_certainty', 'budget_certainty', 'tendency'):
        if cert_field in data:
            val = data[cert_field]
            if val is not None:
                try:
                    val = int(val)
                    if val not in (1, 2, 3):
                        val = None
                except (TypeError, ValueError):
                    val = None
            setattr(project, cert_field, val)

    project.updated_at = datetime.utcnow()
    db.session.commit()

    # 自进化引擎：阶段推进反馈（L3）— sales_stage 实际变更时触发
    if any(cl['field'] == 'sales_stage' for cl in change_logs):
        try:
            from app.services.outcome_tracker import OutcomeTracker
            OutcomeTracker().update_l3_stage_advance(project_id)
        except Exception:
            pass

    return jsonify({
        'project': project_to_dict(project),
        'change_logs': change_logs,
        'total_changes': len(change_logs)
    }), 200



@sales_twin_bp.route('/projects/<int:project_id>', methods=['DELETE'])
def delete_project(project_id):
    """删除项目"""
    project = get_project_or_404(project_id)
    db.session.delete(project)
    db.session.commit()
    return jsonify({'success': True, 'message': '项目已删除'}), 200



@sales_twin_bp.route('/projects/<int:project_id>/close-review', methods=['PUT'])
def close_project_review(project_id):
    """关闭复盘（仅 closed_won/closed_lost）：记录赢/丢单原因并沉淀 LearningPattern

    请求体: {close_reason_category, close_reason_detail?, lessons_learned?}
    同名复盘模式（同 category + 同项目名）已存在时 evidence_count 累加并更新 recommended_play
    """
    project = get_project_or_404(project_id)
    data = request.get_json() or {}

    if project.sales_stage not in ('closed_won', 'closed_lost'):
        return jsonify({'error': '仅已关闭（closed_won/closed_lost）的项目可填写关闭复盘'}), 400

    category = data.get('close_reason_category')
    if category not in VALID_CLOSE_REASONS:
        return jsonify({'error': f'非法关闭原因分类: {category}，可选值: {"/".join(VALID_CLOSE_REASONS)}'}), 400

    project.close_reason_category = category
    # 仅在传入时更新，避免部分提交清空已有内容
    if 'close_reason_detail' in data:
        project.close_reason_detail = data['close_reason_detail']
    if 'lessons_learned' in data:
        project.lessons_learned = data['lessons_learned']
    project.updated_at = datetime.utcnow()

    # 审计日志：赢/丢单归因变更可追溯
    log = StateChangeLog(
        project_id=project_id,
        stakeholder_id=None,
        change_object=project.name,
        attribute_name='close_reason_category',
        old_value='',
        new_value=category,
        reasoning=data.get('close_reason_detail') or '关闭复盘',
        change_source='manual_edit'
    )
    db.session.add(log)

    # 沉淀 LearningPattern：赢单→成功模式，丢单→失败模式
    # 模式名不含项目名，使同类原因跨项目累加证据数，形成可复用打法
    pattern_type = 'success_pattern' if project.sales_stage == 'closed_won' else 'failure_pattern'
    pattern_name = f'{pattern_type}-{category}'
    pattern = LearningPattern.query.filter_by(name=pattern_name).first()
    if pattern:
        pattern.evidence_count = (pattern.evidence_count or 0) + 1
        if 'lessons_learned' in data:
            pattern.recommended_play = data['lessons_learned']
    else:
        pattern = LearningPattern(
            pattern_type=pattern_type,
            name=pattern_name,
            recommended_play=data.get('lessons_learned'),
            status='candidate',
            evidence_count=1,
        )
        db.session.add(pattern)

    db.session.commit()
    return jsonify({
        'success': True,
        'project': project_to_dict(project),
        'pattern': {
            'id': pattern.id,
            'pattern_type': pattern.pattern_type,
            'name': pattern.name,
            'recommended_play': pattern.recommended_play,
            'evidence_count': pattern.evidence_count,
            'status': pattern.status,
        },
        'message': '关闭复盘已保存'
    }), 200



