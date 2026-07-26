"""待办与建议池路由"""
from ._helpers import *  # noqa: E402, F401, F403
from ._helpers import sales_twin_bp  # noqa: E402, F401
from ._helpers import _build_project_insight_summary  # noqa: E402, F401


@sales_twin_bp.route('/projects/<int:project_id>/tasks', methods=['GET'])
def get_tasks(project_id):
    """获取项目所有待办事项"""
    status_filter = request.args.get('status')
    query = OpportunityTask.query.filter_by(project_id=project_id)
    if status_filter:
        query = query.filter_by(status=status_filter)
    tasks = query.order_by(OpportunityTask.created_at.desc()).all()
    # 批量预加载关联干系人映射，避免 task_to_dict 内逐条 Stakeholder.query.get 产生 N+1
    stakeholder_ids = set()
    for t in tasks:
        if t.stakeholder_id:
            stakeholder_ids.add(t.stakeholder_id)
        if t.stakeholder_ids:
            try:
                ids = json.loads(t.stakeholder_ids)
                if isinstance(ids, list):
                    stakeholder_ids.update(ids)
            except (json.JSONDecodeError, TypeError):
                pass
    stakeholder_map = {
        s.id: s.name for s in Stakeholder.query.filter(Stakeholder.id.in_(stakeholder_ids)).all()
    } if stakeholder_ids else {}
    return jsonify({'tasks': [task_to_dict(t, stakeholder_map=stakeholder_map) for t in tasks], 'total': len(tasks)}), 200



@sales_twin_bp.route('/projects/<int:project_id>/tasks/auto-sort', methods=['POST'])
def auto_sort_tasks(project_id):
    """基于SVS各阶段工作中心及交付物要求和挑战式销售方法，
    对项目所有 pending/in_progress 待办进行优先级和时间排序。
    返回排序建议（不直接修改数据库），前端可让用户确认后再应用。
    """
    project = get_project_or_404(project_id)
    pending_tasks = OpportunityTask.query.filter_by(project_id=project_id).filter(
        OpportunityTask.status.in_(['pending', 'in_progress'])
    ).order_by(OpportunityTask.created_at.desc()).all()

    if not pending_tasks:
        return jsonify({'success': True, 'suggestions': [], 'message': '暂无可排序的待办'}), 200

    try:
        from app.utils.llm_client import LLMClient
        llm = LLMClient()
    except Exception as e:
        return jsonify({'error': f'LLM客户端初始化失败: {e}'}), 500

    # 构建项目上下文
    proj_context_parts = []
    if project.customer_name:
        proj_context_parts.append(f"客户: {project.customer_name}")
    if project.industry:
        proj_context_parts.append(f"行业: {project.industry}")
    if project.sales_stage:
        proj_context_parts.append(f"当前销售阶段: {project.sales_stage}")
    pain_points_summary = _build_project_insight_summary(project.id)
    if pain_points_summary:
        proj_context_parts.append(f"业务痛点: {pain_points_summary[:PROMPT_FIELD_PREVIEW_LENGTH]}")
    if project.expected_close_date:
        proj_context_parts.append(f"预计关闭时间: {project.expected_close_date.isoformat()}")
    proj_context = '\n'.join(proj_context_parts) if proj_context_parts else '（无项目上下文）'

    # 构建待办清单
    task_lines = []
    for t in pending_tasks:
        sk_name = ''
        if t.stakeholder_id:
            sk = Stakeholder.query.get(t.stakeholder_id)
            if sk:
                sk_name = sk.name
        line = f"- ID:{t.id} | 标题: {t.title}"
        line += f" | 类型: {t.task_type} | 当前优先级: {t.priority}"
        line += f" | 目标干系人: {sk_name or '通用'}"
        if t.due_date:
            line += f" | 当前截止: {t.due_date.strftime('%Y-%m-%d')}"
        if t.description:
            line += f" | 描述: {t.description[:100]}"
        task_lines.append(line)
    tasks_text = '\n'.join(task_lines)

    prompt = f"""你是B2B销售项目经理，精通SVS（销售价值流）各阶段工作中心与交付物要求，以及挑战式销售（Challenger Sale）方法论。

## 项目背景
{proj_context}

## 待办事项清单（仅未完成项）
{tasks_text}

## SVS+Challenge Sales 五阶段工作中心与交付物
- **suspect（线索）**：客户编排、商机识别、初始关系建立，OM10 Bid/No-Go 决策。交付物：客户计划（公司结构图、客户战略图、销售目标）、线索评估记录
- **identity（商机确认）**：干系人识别与分析、客户需求确认、商机团队组建，OM20 Go/No-Go 决策。交付物：干系人图谱、客户需求文档、OM20 决策记录
- **define（方案定义）**：销售模式选择、解决方案设计、投标策略，OM30 策略评审 / OM40 投标批准。交付物：商机计划、解决方案文档、CSP 草稿
- **confirm（商务确认）**：商务谈判、合同准备、干系人共识确认，OM70 赢单/丢单。交付物：谈判记录、合同文件、OM70 决策记录
- **close（关单）**：赢单/丢单处理、知识沉淀、过渡到实施，OM80。交付物：关单报告、经验教训文档、客户交接文档

## 挑战式销售方法论要点
- 教学（Teaching）：向客户传授新视角，重塑其对问题的理解
- 量身定制（Tailoring）：针对不同干系人个性化传递价值
- 控制对话（Taking Control）：在价格等压力场景中掌控节奏

## 任务
基于项目当前阶段（{project.sales_stage or '未知'}），对每个待办重新评估：
1. **优先级**（high/medium/low）：根据该任务对推进当前SVS阶段工作中心与交付物的关键程度
2. **建议截止日期**（YYYY-MM-DD）：根据任务紧迫性和项目预计关闭时间合理排期
3. **排序权重**（1-100，数值越大越优先）：综合优先级和截止时间，作为最终排序依据

## 输出格式（严格JSON）
{{
  "suggestions": [
    {{
      "task_id": 数字,
      "suggested_priority": "high|medium|low",
      "suggested_due_date": "YYYY-MM-DD或null",
      "sort_weight": 1-100整数,
      "reason": "30-80字说明排序理由，结合SVS阶段和挑战式销售"
    }}
  ]
}}

只输出JSON，不要输出其他内容。"""

    try:
        result = llm.chat_json(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=2000
        )
        suggestions = result.get('suggestions', []) if isinstance(result, dict) else []
    except Exception as e:
        return jsonify({'error': f'LLM评估失败: {e}'}), 500

    # 按sort_weight降序排列
    valid_ids = {t.id for t in pending_tasks}
    valid_suggestions = [s for s in suggestions if s.get('task_id') in valid_ids]
    valid_suggestions.sort(key=lambda x: x.get('sort_weight', 0), reverse=True)

    return jsonify({
        'success': True,
        'suggestions': valid_suggestions,
        'sales_stage': project.sales_stage,
        'total': len(valid_suggestions)
    }), 200



@sales_twin_bp.route('/projects/<int:project_id>/tasks/apply-sort', methods=['POST'])
def apply_task_sort(project_id):
    """应用排序建议：批量更新task的priority和due_date"""
    project = get_project_or_404(project_id)
    data = request.get_json() or {}
    suggestions = data.get('suggestions', [])
    if not suggestions:
        return jsonify({'error': '缺少suggestions字段'}), 400

    updated = []
    for sug in suggestions:
        tid = sug.get('task_id')
        if not tid:
            continue
        task = OpportunityTask.query.filter_by(id=tid, project_id=project_id).first()
        if not task:
            continue
        if sug.get('suggested_priority') in ('high', 'medium', 'low'):
            task.priority = sug['suggested_priority']
        if sug.get('suggested_due_date'):
            try:
                task.due_date = datetime.fromisoformat(sug['suggested_due_date'])
            except (ValueError, TypeError):
                pass
        task.updated_at = datetime.utcnow()
        updated.append(task.id)

    db.session.commit()

    # 返回更新后的tasks
    tasks = OpportunityTask.query.filter_by(project_id=project_id).order_by(
        OpportunityTask.created_at.desc()
    ).all()
    return jsonify({
        'success': True,
        'updated_count': len(updated),
        'tasks': [task_to_dict(t) for t in tasks]
    }), 200



@sales_twin_bp.route('/projects/<int:project_id>/tasks', methods=['POST'])
def create_task(project_id):
    """手动创建待办事项"""
    project = get_project_or_404(project_id)
    data = request.get_json()

    if not data.get('title'):
        return jsonify({'error': '缺少title字段'}), 400

    # action_type 映射到 task_type
    task_type = data.get('task_type') or data.get('action_type') or 'follow_up'
    # 验证 task_type 合法
    valid_types = ['blind_spot', 'address_concerns', 'build_alliance', 'provide_material', 'meeting', 'follow_up']
    if task_type not in valid_types:
        task_type = 'follow_up'

    task = OpportunityTask(
        project_id=project_id,
        stakeholder_id=data.get('stakeholder_id'),
        stakeholder_ids=json.dumps(data.get('stakeholder_ids') or ([data['stakeholder_id']] if data.get('stakeholder_id') else []), ensure_ascii=False),
        task_type=task_type,
        title=data['title'],
        description=data.get('description'),
        priority=data.get('priority', 'medium'),
        status='pending',
        source='manual',
        due_date=datetime.fromisoformat(data['due_date']) if data.get('due_date') else None
    )
    db.session.add(task)
    db.session.commit()

    return jsonify({'task': task_to_dict(task)}), 200



def _decide_action_merge_with_llm(candidate_tasks, data, action_type, target_name, priority_score):
    """调用 LLM 判断新行动建议是否应合并到现有待办。

    Returns:
        (merge_decision: dict|None, merged_task_id: int|None)
    """
    if not candidate_tasks:
        return None, None
    try:
        from app.utils.llm_client import LLMClient
        llm = LLMClient()

        # 构造候选待办摘要
        cand_lines = []
        for t in candidate_tasks:
            sk_name = ''
            if t.stakeholder_id:
                sk = Stakeholder.query.get(t.stakeholder_id)
                if sk:
                    sk_name = sk.name
            cand_lines.append(
                f"- ID:{t.id} | 标题: {t.title}"
                f" | 目标: {sk_name or '通用'}"
                f" | 类型: {t.task_type}"
                f" | 优先级: {t.priority}"
                f" | 描述: {(t.description or '')[:120]}"
            )
        candidates_text = '\n'.join(cand_lines)

        new_action_text = (
            f"新行动建议标题: {data.get('title')}\n"
            f"目标干系人: {target_name or '通用'}\n"
            f"行动类型: {action_type}\n"
            f"优先级分数: {priority_score}\n"
            f"描述: {(data.get('description') or '')[:PROMPT_FIELD_PREVIEW_LENGTH]}\n"
            f"理由: {(data.get('reasoning') or '')[:PROMPT_FIELD_PREVIEW_LENGTH]}"
        )

        prompt = f"""你是B2B销售项目协作助手。请判断这条"新行动建议"是否应该合并到下面"已有待办事项"中的某一项，还是应该新建一项独立待办。

## 新行动建议
{new_action_text}

## 已有待办事项
{candidates_text}

## 判断规则
- 合并条件：新建议与已有待办**目标干系人相同**且**核心行动一致**（仅描述细节差异），或者标题高度雷同
- 否则应新建独立待办
- 如果选择合并，merge_task_id 必须填上面"已有待办事项"中确实存在的 ID
- 如果选择新建，merge_task_id 填 null

## 输出格式（严格JSON）
{{
  "decision": "merge" | "new",
  "merge_task_id": 数字或null,
  "reason": "判断理由（30-80字）",
  "merged_title": "若合并，建议的新标题（保留两边的核心信息）；若新建则填null"
}}

只输出JSON，不要输出其他内容。"""

        result = llm.chat_json(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=500
        )
        if result and isinstance(result, dict):
            merge_decision = result
            merged_task_id = None
            # 验证merge_task_id确实在候选列表中
            if result.get('decision') == 'merge':
                mid = result.get('merge_task_id')
                if mid and any(t.id == int(mid) for t in candidate_tasks):
                    merged_task_id = int(mid)
                else:
                    # LLM给出的ID无效，降级为新建
                    merge_decision['decision'] = 'new'
                    merge_decision['merge_task_id'] = None
            return merge_decision, merged_task_id
    except Exception:
        # LLM判断失败，降级为直接新建
        pass
    return None, None


def _merge_action_into_existing_task(target_task, data, source_action, action_brief_value, priority):
    """将新行动建议合并到现有待办（描述/简报/优先级/source_action 元数据）"""
    merged_note = f"\n\n[合并自行动建议：{data.get('title')}]"
    if data.get('description'):
        merged_note += f"\n{data['description']}"
    if data.get('reasoning'):
        merged_note += f"\n理由：{data['reasoning']}"
    # 更新描述（保留原描述）
    original_desc = target_task.description or ''
    target_task.description = (original_desc + merged_note).strip()
    # 优先级取较高者
    priority_rank = {'high': 3, 'medium': 2, 'low': 1}
    if priority_rank.get(priority, 0) > priority_rank.get(target_task.priority, 0):
        target_task.priority = priority
    # 合并source_action元数据
    existing_sa = None
    if target_task.source_action:
        try:
            existing_sa = json.loads(target_task.source_action)
        except (json.JSONDecodeError, TypeError):
            existing_sa = None
    if not isinstance(existing_sa, dict):
        existing_sa = {'merged_from': []}
    merged_list = existing_sa.get('merged_from', [])
    try:
        new_sa = json.loads(source_action)
        merged_list.append(new_sa)
        existing_sa['merged_from'] = merged_list
    except (json.JSONDecodeError, TypeError):
        pass
    target_task.source_action = json.dumps(existing_sa, ensure_ascii=False)
    # 合并action_brief
    if action_brief_value and not target_task.action_brief:
        target_task.action_brief = action_brief_value
    target_task.updated_at = datetime.utcnow()
    db.session.commit()


def _create_task_from_action(project_id, stakeholder_id, task_type, data, priority, source_action, action_brief_value):
    """从行动建议新建待办事项"""
    task = OpportunityTask(
        project_id=project_id,
        stakeholder_id=stakeholder_id,
        # 同步写入 stakeholder_ids JSON 数组，与 create_task 保持一致
        # 避免 _compute_interaction_stats 等依赖 stakeholder_ids 的查询漏算
        stakeholder_ids=json.dumps([stakeholder_id] if stakeholder_id else [], ensure_ascii=False),
        task_type=task_type,
        title=data['title'],
        description=data.get('description'),
        action_brief=action_brief_value,
        priority=priority,
        status='pending',
        source='recommended_action',
        source_action=source_action,
        due_date=datetime.fromisoformat(data['due_date']) if data.get('due_date') else None
    )
    db.session.add(task)
    db.session.commit()
    return task


@sales_twin_bp.route('/projects/<int:project_id>/tasks/adopt-action', methods=['POST'])
def adopt_recommended_action(project_id):
    """采纳行动建议，转为待办事项。
    调用LLM判断是否合并到现有待办还是新建一项待办。
    """
    project = get_project_or_404(project_id)
    data = request.get_json()

    if not data.get('title'):
        return jsonify({'error': '缺少title字段'}), 400

    # action_type 映射到 task_type
    action_type = data.get('action_type', 'follow_up')
    type_map = {
        'build_alliance': 'build_alliance',
        'address_concerns': 'address_concerns',
        'provide_material': 'provide_material',
        'seek_intelligence': 'follow_up',
        'leverage_champion': 'build_alliance',
        'blind_spot': 'blind_spot',
        'meeting': 'meeting',
        'follow_up': 'follow_up'
    }
    task_type = type_map.get(action_type, 'follow_up')

    # priority 映射
    priority_score = data.get('priority_score', 50)
    if priority_score >= 80:
        priority = 'high'
    elif priority_score >= 50:
        priority = 'medium'
    else:
        priority = 'low'

    # 查找目标干系人
    stakeholder_id = None
    target_name = data.get('target_stakeholder')
    if target_name and target_name != '通用':
        sk = Stakeholder.query.filter_by(
            project_id=project_id, name=target_name
        ).first()
        if sk:
            stakeholder_id = sk.id

    # 构造 source_action 元数据
    source_action = json.dumps({
        'action_type': action_type,
        'target_stakeholder': target_name,
        'priority_score': priority_score,
        'urgency': data.get('urgency'),
        'reasoning': data.get('reasoning'),
        'original_title': data.get('title'),
        'adopted_at': datetime.utcnow().isoformat()
    }, ensure_ascii=False)

    action_brief_value = json.dumps({
        'pain_point_statement': data.get('pain_point_statement'),
        'insight_challenge': data.get('insight_challenge'),
        'solution_intro': data.get('solution_intro')
    }, ensure_ascii=False) if any(data.get(k) for k in ['pain_point_statement', 'insight_challenge', 'solution_intro']) else None

    # 拉取项目下所有未完成/未取消的待办，让LLM判断是否合并
    candidate_tasks = OpportunityTask.query.filter_by(project_id=project_id).filter(
        OpportunityTask.status.in_(['pending', 'in_progress'])
    ).order_by(OpportunityTask.created_at.desc()).all()

    merge_decision, merged_task_id = _decide_action_merge_with_llm(
        candidate_tasks, data, action_type, target_name, priority_score
    )

    # 根据判断结果执行合并或新建
    if merged_task_id:
        target_task = OpportunityTask.query.get(merged_task_id)
        _merge_action_into_existing_task(target_task, data, source_action, action_brief_value, priority)
        # 自进化引擎：记录 L1 采纳反馈
        rec_id = data.get('recommendation_id')
        if rec_id:
            try:
                from app.services.outcome_tracker import OutcomeTracker
                OutcomeTracker().record_l1_adoption(rec_id, adopted=True, task_id=target_task.id)
            except Exception:
                pass
        return jsonify({
            'success': True,
            'task': task_to_dict(target_task),
            'merge_decision': merge_decision,
            'message': f"行动建议已合并到待办「{target_task.title}」"
        }), 200

    # 否则新建待办
    task = _create_task_from_action(
        project_id, stakeholder_id, task_type, data, priority, source_action, action_brief_value
    )
    # 自进化引擎：记录 L1 采纳反馈
    rec_id = data.get('recommendation_id')
    if rec_id:
        try:
            from app.services.outcome_tracker import OutcomeTracker
            OutcomeTracker().record_l1_adoption(rec_id, adopted=True, task_id=task.id)
        except Exception:
            pass

    return jsonify({
        'success': True,
        'task': task_to_dict(task),
        'merge_decision': merge_decision or {'decision': 'new', 'merge_task_id': None, 'reason': 'LLM判断失败，默认新建'},
        'message': f'行动建议已采纳为待办事项: {task.title}'
    }), 200



@sales_twin_bp.route('/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    """更新待办事项（支持编辑/状态变更）"""
    task = OpportunityTask.query.get_or_404(task_id)
    data = request.get_json()

    if 'title' in data:
        task.title = data['title']
    if 'description' in data:
        task.description = data['description']
    if 'priority' in data:
        if data['priority'] not in ('high', 'medium', 'low'):
            return jsonify({'error': 'priority 必须为 high/medium/low'}), 400
        task.priority = data['priority']
    if 'stakeholder_id' in data:
        sid = data['stakeholder_id']
        if sid is not None:
            sk = Stakeholder.query.filter_by(id=sid, project_id=task.project_id).first()
            if not sk:
                return jsonify({'error': 'stakeholder_id 不属于当前项目'}), 400
        task.stakeholder_id = sid
    if 'stakeholder_ids' in data:
        task.stakeholder_ids = json.dumps(data['stakeholder_ids'] or [], ensure_ascii=False)
    if 'due_date' in data:
        task.due_date = datetime.fromisoformat(data['due_date']) if data.get('due_date') else None
    if 'status' in data:
        if data['status'] not in ('pending', 'in_progress', 'completed', 'cancelled'):
            return jsonify({'error': 'status 非法'}), 400
        old_status = task.status
        task.status = data['status']
        if data['status'] == 'completed' and old_status != 'completed':
            task.completed_at = datetime.utcnow()
            task.completion_note = data.get('completion_note', '')
            # 自进化引擎：记录 L2 执行完成反馈
            try:
                from app.services.outcome_tracker import OutcomeTracker
                OutcomeTracker().update_l2_execution(task.id, execution_result='success')
            except Exception:
                pass
    if 'completion_note' in data:
        task.completion_note = data['completion_note']

    task.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({'task': task_to_dict(task)}), 200



@sales_twin_bp.route('/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    """删除待办事项"""
    task = OpportunityTask.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    return jsonify({'success': True, 'message': '待办事项已删除'}), 200



@sales_twin_bp.route('/projects/<int:project_id>/suggestions', methods=['GET'])
def get_suggestions(project_id):
    """获取项目建议池列表"""
    suggestions = SuggestionPool.query.filter_by(
        project_id=project_id
    ).order_by(SuggestionPool.created_at.desc()).all()
    return jsonify({
        'suggestions': [suggestion_to_dict(s) for s in suggestions],
        'total': len(suggestions)
    }), 200



@sales_twin_bp.route('/projects/<int:project_id>/suggestions', methods=['POST'])
def add_suggestion(project_id):
    """添加建议到建议池（从访谈/报告选中文字采纳）"""
    get_project_or_404(project_id)
    data = request.get_json()

    content = (data.get('content') or '').strip()
    if not content:
        return jsonify({'error': '缺少content字段'}), 400

    suggestion = SuggestionPool(
        project_id=project_id,
        content=content,
        source=data.get('source', 'manual'),
        source_context=json.dumps(data.get('source_context'), ensure_ascii=False) if data.get('source_context') else None,
        is_consumed=0
    )
    db.session.add(suggestion)
    db.session.commit()

    return jsonify({'suggestion': suggestion_to_dict(suggestion)}), 200



@sales_twin_bp.route('/suggestions/<int:suggestion_id>', methods=['PUT'])
def update_suggestion(suggestion_id):
    """编辑建议池条目"""
    suggestion = SuggestionPool.query.get_or_404(suggestion_id)
    data = request.get_json()

    if 'content' in data:
        content = (data['content'] or '').strip()
        if not content:
            return jsonify({'error': 'content不能为空'}), 400
        suggestion.content = content
    if 'source_context' in data:
        suggestion.source_context = json.dumps(data['source_context'], ensure_ascii=False) if data['source_context'] else None

    db.session.commit()
    return jsonify({'suggestion': suggestion_to_dict(suggestion)}), 200



@sales_twin_bp.route('/suggestions/<int:suggestion_id>', methods=['DELETE'])
def delete_suggestion(suggestion_id):
    """删除建议池条目"""
    suggestion = SuggestionPool.query.get_or_404(suggestion_id)
    db.session.delete(suggestion)
    db.session.commit()
    return jsonify({'success': True}), 200



@sales_twin_bp.route('/projects/<int:project_id>/suggestions/generate-tasks', methods=['POST'])
def generate_tasks_from_suggestions(project_id):
    """从建议池调用LLM生成待办事项（获取项目完整状态+所有历史记录）"""
    get_project_or_404(project_id)
    data = request.get_json() or {}

    from app.services.suggestion_task_generator import SuggestionTaskGenerator
    generator = SuggestionTaskGenerator()
    result = generator.generate_tasks(
        project_id=project_id,
        suggestion_ids=data.get('suggestion_ids')  # None=全部未消费的
    )
    return jsonify(result), 200



