"""LLM 分析路由（客户概览/价值主张/竞争分析/痛点/发酵推演等）"""
from ._helpers import *  # noqa: E402, F401, F403
from ._helpers import sales_twin_bp  # noqa: E402, F401
from app.utils.prompt_templates import build_svs_opportunity_prompt


@sales_twin_bp.route('/projects/<int:project_id>/research', methods=['POST'])
def research_company(project_id):
    """网络调研目标公司背景信息（用于补充图谱构建上下文）"""
    project = get_project_or_404(project_id)

    if not project.customer_name:
        return jsonify({
            'success': False,
            'error': '项目未设置客户名称，无法进行网络调研'
        }), 400

    data = request.get_json() or {}
    extra_keywords = data.get('extra_keywords', '')

    from app.services.web_researcher import WebResearcher
    researcher = WebResearcher()
    result = researcher.research_company(
        company_name=project.customer_name,
        industry=project.industry or '',
        extra_keywords=extra_keywords
    )

    # 调研成功后，自动从识别出的关键决策岗位创建干系人
    if result.get('success') and result.get('organization'):
        from app.services.stakeholder_generator import StakeholderGenerator
        generator = StakeholderGenerator()
        stakeholder_result = generator.generate_from_research(
            project_id=project_id,
            organization=result['organization']
        )
        result['stakeholder_generation'] = stakeholder_result

    return jsonify(result), 200



@sales_twin_bp.route('/projects/<int:project_id>/competitive-analysis', methods=['POST'])
def generate_competitive_analysis(project_id):
    """基于SVS框架商机计划，用LLM生成竞争分析

    请求体：
    - document_texts: 可选，上传文档的文本内容列表
    """
    project = get_project_or_404(project_id)
    data = request.get_json() or {}
    document_texts = data.get('document_texts', []) or []
    stakeholders = Stakeholder.query.filter_by(project_id=project_id).all()
    context = _build_project_context(project, stakeholders, document_texts)

    # 注入我方公司/产品信息
    company_context = _build_company_context()
    if company_context:
        context = context + '\n\n' + company_context

    sections_spec = """- 必须包含以下四个小节：
  【强项（Strengths）】
  • 我方相对优势（结合产品/服务/资源具体描述）
  • 差异化能力

  【弱点（Weaknesses）】
  • 我方相对劣势
  • 需要弥补的短板

  【商机（Opportunities）】
  • 市场/客户层面的有利机会
  • 可利用的趋势

  【威胁（Threats）】
  • 主要竞品及其优劣势
  • 客户可能的选型标准中对我方不利的部分
  • 差异化突围策略"""

    prompt = build_svs_opportunity_prompt(
        context=context,
        section_name='竞争分析',
        field_name='competitive_analysis',
        methodology='进行SWOT分析',
        sections_spec=sections_spec,
        word_count='200-400字'
    )

    try:
        from app.utils.llm_client import LLMClient
        llm = LLMClient()
        result = llm.chat_json(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=2000
        )

        if not isinstance(result, dict):
            result = {}
        content = result.get('competitive_analysis', '')
        if not isinstance(content, str) or not content.strip():
            content = ''

        if content:
            content = (content or '')[:MAX_TEXT_FIELD_LENGTH]
            project.competitive_analysis = content
            project.updated_at = datetime.utcnow()
            db.session.commit()

        return jsonify({
            'success': True,
            'competitive_analysis': content,
            'project': project_to_dict(project)
        }), 200
    except Exception as e:
        return _llm_error_response('生成失败', e)



@sales_twin_bp.route('/projects/<int:project_id>/reformat-text', methods=['POST'])
def reformat_text(project_id):
    """用LLM对已有文本进行排版优化，不改变实质内容

    请求体：
    - field: 字段名（competitive_analysis）
    """
    project = get_project_or_404(project_id)
    data = request.get_json() or {}
    field = data.get('field')
    allowed_fields = ('competitive_analysis',)
    if field not in allowed_fields:
        return jsonify({'success': False, 'error': '不支持的字段'}), 400

    original = getattr(project, field, '') or ''
    if not original.strip():
        return jsonify({'success': False, 'error': '原文为空，无法排版'}), 400

    field_labels = {
        'competitive_analysis': '竞争分析',
    }

    prompt = f"""你是专业的文本排版助手。请对以下"{field_labels.get(field, field)}"内容进行排版优化，使其更易读，但不要改变实质内容。

# 原文
{original}

# 排版要求
- 保留原文的所有信息和要点，不要增删实质内容
- 识别原文中的逻辑分组，用"【】"标记小节标题（如原文已有【】标题则保留并优化）
- 把散落的要点用"• "前缀转为列表项
- 长段落拆分为短段落，每段聚焦一个主题
- 修正明显的标点和空格问题
- 语言风格保持与原文一致（中文）

# 输出格式
严格输出以下JSON结构：
{{
  "{field}": "排版后的内容"
}}

- 只输出JSON，不要其他内容"""

    try:
        from app.utils.llm_client import LLMClient
        llm = LLMClient()
        result = llm.chat_json(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=2000
        )

        if not isinstance(result, dict):
            result = {}
        content = result.get(field, '')
        if not isinstance(content, str) or not content.strip():
            content = original  # 失败则返回原文

        if content and content != original:
            content = (content or '')[:MAX_TEXT_FIELD_LENGTH]
            setattr(project, field, content)
            project.updated_at = datetime.utcnow()
            db.session.commit()

        return jsonify({
            'success': True,
            field: content,
            'project': project_to_dict(project)
        }), 200
    except Exception as e:
        return _llm_error_response('排版失败', e)



@sales_twin_bp.route('/projects/<int:project_id>/scan', methods=['POST'])
def scan_blind_spots(project_id):
    """扫描图谱盲区（手动触发，自动持久化到 BlindSpotReport，scan_source='manual'）"""
    from app.services.blind_spot_detector import BlindSpotDetector

    detector = BlindSpotDetector()
    result = detector.scan_project(project_id, scan_source='manual')

    return jsonify(result), 200


@sales_twin_bp.route('/projects/<int:project_id>/blind-spot-reports', methods=['GET'])
def get_blind_spot_reports(project_id):
    """获取项目盲区扫描历史报告列表（按时间倒序）"""
    from app.models.database import BlindSpotReport

    limit = request.args.get('limit', 10, type=int)
    limit = max(1, min(limit, 50))

    reports = BlindSpotReport.query.filter_by(project_id=project_id) \
        .order_by(BlindSpotReport.scanned_at.desc()).limit(limit).all()

    import json as _json
    report_list = []
    for r in reports:
        report_list.append({
            'id': r.id,
            'scan_source': r.scan_source,
            'overall_score': r.overall_score,
            'summary': r.summary or '',
            'findings': _json.loads(r.findings_json) if r.findings_json else [],
            'total_findings': r.total_findings,
            'total_stakeholders': r.total_stakeholders,
            'total_relationships': r.total_relationships,
            'scanned_at': r.scanned_at.isoformat() if r.scanned_at else None,
        })
    return jsonify({'success': True, 'data': report_list}), 200


@sales_twin_bp.route('/projects/<int:project_id>/blind-spot-latest', methods=['GET'])
def get_latest_blind_spot_report(project_id):
    """获取项目最新盲区报告（前端首次加载时调用，避免每次都重新扫描）"""
    from app.services.blind_spot_detector import BlindSpotDetector

    report = BlindSpotDetector.get_latest_report(project_id)
    if not report:
        return jsonify({'success': True, 'data': None}), 200
    return jsonify({'success': True, 'data': report}), 200



@sales_twin_bp.route('/projects/<int:project_id>/next-best-action', methods=['POST'])
def next_best_action(project_id):
    """生成下一步行动推荐"""
    from app.services.action_recommender import ActionRecommender
    
    recommender = ActionRecommender()
    result = recommender.recommend_actions(project_id)
    
    return jsonify(result), 200



@sales_twin_bp.route('/projects/<int:project_id>/action-brief/<int:stakeholder_id>', methods=['POST'])
def generate_action_brief(project_id, stakeholder_id):
    """生成单人拜访简报"""
    from app.services.action_recommender import ActionRecommender
    
    recommender = ActionRecommender()
    result = recommender.generate_action_brief(project_id, stakeholder_id)
    
    return jsonify(result), 200



@sales_twin_bp.route('/projects/<int:project_id>/win-rate', methods=['GET'])
def get_win_rate(project_id):
    """获取赢单率预测"""
    from app.services.win_rate_calculator import WinRateCalculator
    
    calculator = WinRateCalculator()
    result = calculator.calculate_win_rate(project_id)
    
    return jsonify(result), 200



@sales_twin_bp.route('/projects/<int:project_id>/fermentation', methods=['POST'])
def simulate_fermentation(project_id):
    """模拟闭门发酵过程（支持narrative/numeric/hybrid模式，按扩散轮次推演）"""
    data = request.get_json() or {}

    # 优先使用 rounds（扩散轮次），向后兼容 days
    rounds = data.get('rounds')
    days = data.get('days')
    if rounds is None:
        rounds = days if days is not None else 3
    mode = data.get('mode', 'narrative')  # narrative（LLM叙事）/ numeric（数值）/ hybrid（结合）
    related_task_ids = data.get('related_task_ids', [])
    related_feedback_ids = data.get('related_feedback_ids', [])
    related_materials = data.get('related_materials', [])

    if mode == 'numeric':
        # 旧版纯数值模式
        initial_events = data.get('initial_events', [])
        if related_task_ids:
            tasks = OpportunityTask.query.filter(
                OpportunityTask.id.in_(related_task_ids),
                OpportunityTask.project_id == project_id
            ).all()
            for task in tasks:
                target_sk_id = task.stakeholder_id
                if not target_sk_id:
                    continue
                impact = 1 if task.status == 'completed' else 0
                initial_events.append({
                    'stakeholder_id': target_sk_id,
                    'support_impact': impact,
                    'source': f'task:{task.id}:{task.title}'
                })
        if related_feedback_ids:
            records = FeedbackRecord.query.filter(
                FeedbackRecord.id.in_(related_feedback_ids),
                FeedbackRecord.project_id == project_id
            ).all()
            for record in records:
                try:
                    task_ids = json.loads(record.related_task_ids) if record.related_task_ids else []
                except (json.JSONDecodeError, TypeError):
                    task_ids = []
                for tid in task_ids:
                    task = OpportunityTask.query.get(tid)
                    if task and task.stakeholder_id:
                        initial_events.append({
                            'stakeholder_id': task.stakeholder_id,
                            'support_impact': 1,
                            'source': f'feedback:{record.id}'
                        })
        from app.services.fermentation_simulator import FermentationSimulator
        simulator = FermentationSimulator()
        result = simulator.simulate_fermentation(project_id, days=rounds, initial_events=initial_events)
        result['input_sources'] = {
            'related_task_ids': related_task_ids,
            'related_feedback_ids': related_feedback_ids,
            'related_materials': related_materials,
            'total_initial_events': len(initial_events)
        }
        return jsonify(result), 200

    # narrative / hybrid 模式：LLM驱动
    from app.services.fermentation_llm_simulator import LLMFermentationSimulator
    llm_sim = LLMFermentationSimulator()
    result = llm_sim.simulate(
        project_id,
        rounds=rounds,
        related_task_ids=related_task_ids,
        related_feedback_ids=related_feedback_ids,
        related_materials=related_materials
    )

    # hybrid模式：附加数值趋势作为补充
    if mode == 'hybrid':
        result['mode'] = 'hybrid'
        result['numeric_supplement'] = {
            'trend': result.get('trend', {}),
            'note': '数值趋势已融入LLM叙事推演'
        }

    return jsonify(result), 200



@sales_twin_bp.route('/projects/<int:project_id>/fermentation/interview', methods=['POST'])
def interview_stakeholder(project_id):
    """采访干系人（基于发酵模拟历史）"""
    data = request.get_json() or {}
    stakeholder_id = data.get('stakeholder_id')
    question = data.get('question', '').strip()
    simulation_context = data.get('simulation_context')

    if not stakeholder_id or not question:
        return jsonify({'error': '需要 stakeholder_id 和 question'}), 400

    from app.services.fermentation_llm_simulator import LLMFermentationSimulator
    sim = LLMFermentationSimulator()
    result = sim.interview(project_id, stakeholder_id, question, simulation_context)
    return jsonify(result), 200



def _build_fermentation_report_prompt(project, fermentation_result, stakeholders):
    """构造发酵推演报告的 LLM prompt

    Returns:
        (prompt, rounds, conclusion, trend) - trend/conclusion/rounds 供降级报告使用
    """
    sk_profiles = []
    for s in stakeholders:
        sk_profiles.append({
            'name': s.name or '',
            'position': s.position or '',
            'buyer_role': s.buyer_role or '',
            'support_level': float(s.support_level or 0),
            'decision_power': float(s.decision_power or 0),
            'urgency': float(s.urgency or 0),
            'personal_agenda': s.personal_agenda or '',
        })

    # 序列化推演结果关键信息
    narrative_history = fermentation_result.get('narrative_history', []) or []
    trend = fermentation_result.get('trend', {}) or {}
    conclusion = fermentation_result.get('conclusion', '') or ''
    rounds = fermentation_result.get('rounds') or fermentation_result.get('days', 0) or 0

    # 构建推演摘要文本
    round_summaries = []
    for nh in narrative_history:
        label = nh.get('label', '') or ''
        narrative = nh.get('narrative', '') or ''
        interactions = nh.get('interactions', []) or []
        state_changes = nh.get('state_changes', []) or []
        interactions_text = '; '.join(
            f"{it.get('actor','')} {it.get('action','')}" for it in interactions
        )
        changes_text = '; '.join(
            f"{c.get('stakeholder_name','')} 支持度 {c.get('old_support_level','?')}→{c.get('new_support_level','?')}"
            for c in state_changes
        )
        round_summaries.append(f"{label}: {narrative} 互动:[{interactions_text}] 变化:[{changes_text}]")

    prompt = f"""你是B2B销售数字孪生系统的分析顾问。请基于以下闭门发酵推演结果，生成一份专业的结构化推演报告。

# 项目背景
- 项目名称: {project.name or ''}
- 客户名称: {project.customer_name or ''}
- 业务洞察: {_build_project_insight_summary(project.id) or ''}
- 公司愿景: {project.company_vision or ''}

# 干系人画像
{json.dumps(sk_profiles, ensure_ascii=False, indent=2)}

# 推演结果摘要
- 扩散轮次: {rounds}轮
- 初始平均支持度: {trend.get('initial_avg', '-')}
- 最终平均支持度: {trend.get('final_avg', '-')}
- 变化趋势: {trend.get('change', '-')}
- 推演结论: {conclusion}

# 各轮扩散详情
{chr(10).join(round_summaries) if round_summaries else '无扩散详情'}

# 报告要求
请生成一份结构化推演报告，包含以下JSON结构：
{{
  "title": "报告主标题（20字以内，概括推演核心发现）",
  "summary": "报告摘要（80-150字，概述推演结论与关键洞察）",
  "sections": [
    {{
      "title": "章节标题",
      "content": "章节正文（150-300字，深入分析）",
      "bullets": ["要点1", "要点2", "要点3"]
    }}
  ]
}}

报告必须包含以下章节（按顺序）：
1. 推演概述 - 概括推演场景与整体态势演变
2. 关键干系人态势分析 - 分析核心干系人支持度/决策力变化及原因
3. 风险预警 - 识别支持度下降或立场摇摆的干系人及潜在风险
4. 机会洞察 - 识别可利用的支持度提升机会与突破口
5. 行动建议 - 基于推演结果给出下一步具体可执行的销售行动建议

注意：
- 报告语言为中文
- 内容要具体、可执行，基于实际干系人画像和推演数据，不要空话套话
- bullets每个章节3-5条要点
- 只输出JSON，不要其他内容"""

    return prompt, rounds, conclusion, trend


def _build_fermentation_report_id(project_id):
    """构造发酵推演报告 ID：REF-YYYYMMDD-NNNN"""
    return f"REF-{datetime.utcnow().strftime('%Y%m%d')}-{project_id:04d}"


def _build_fermentation_report_fallback(project_id, rounds, conclusion, trend, err_msg):
    """LLM 失败时生成降级结构化报告"""
    return {
        'id': _build_fermentation_report_id(project_id),
        'title': '推演分析报告',
        'summary': conclusion or '基于发酵推演生成的分析报告',
        'sections': [
            {
                'title': '推演概述',
                'content': f'本次推演模拟了{rounds}轮的信息扩散过程。{conclusion}',
                'bullets': [
                    f'初始平均支持度: {trend.get("initial_avg", "-")}',
                    f'最终平均支持度: {trend.get("final_avg", "-")}',
                    f'变化趋势: {trend.get("change", "-")}',
                ]
            },
            {
                'title': '行动建议',
                'content': '建议针对支持度下降的干系人加强沟通，对支持度提升的干系人巩固联盟关系。',
                'bullets': ['持续跟进核心决策者态度', '针对风险干系人制定专项沟通计划']
            }
        ],
        'note': f'LLM生成失败，使用降级报告: {err_msg[:100]}'
    }


@sales_twin_bp.route('/projects/<int:project_id>/fermentation/report', methods=['POST'])
def generate_fermentation_report(project_id):
    """基于发酵推演结果生成结构化推演报告

    请求体：
    - fermentation_result: 前端缓存的推演结果对象
    """
    project = get_project_or_404(project_id)
    data = request.get_json() or {}
    fermentation_result = data.get('fermentation_result') or data.get('fermentationResult')

    if not fermentation_result:
        return jsonify({'error': '缺少 fermentation_result'}), 400

    # 收集干系人画像，供报告引用
    stakeholders = Stakeholder.query.filter_by(project_id=project_id).all()
    prompt, rounds, conclusion, trend = _build_fermentation_report_prompt(
        project, fermentation_result, stakeholders
    )

    try:
        from app.utils.llm_client import LLMClient
        llm = LLMClient()
        report = llm.chat_json(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=3000
        )

        # 防御性处理：确保结构完整
        if not isinstance(report, dict):
            report = {}
        report.setdefault('title', '推演分析报告')
        report.setdefault('summary', conclusion or '基于发酵推演生成的分析报告')
        if not isinstance(report.get('sections'), list):
            report['sections'] = []
        # 确保每个section结构完整
        for sec in report['sections']:
            if not isinstance(sec, dict):
                continue
            sec.setdefault('title', '')
            sec.setdefault('content', '')
            if not isinstance(sec.get('bullets'), list):
                sec['bullets'] = []
        report['id'] = _build_fermentation_report_id(project_id)

        return jsonify(report), 200
    except Exception as e:
        # 降级：返回基础结构化报告
        fallback = _build_fermentation_report_fallback(project_id, rounds, conclusion, trend, str(e))
        return jsonify(fallback), 200



def _find_nested_dict_with_keys(obj, target_keys, max_depth=4):
    """递归查找包含至少一个目标 key 的子字典

    用于防御性解析 LLM 输出：LongCat-2.0 偶尔将真实数据包装在 thought/plan/details
    或 prompt/schema 等结构中，而非直接返回顶层目标 key。

    Args:
        obj: 待搜索的对象（dict / list / str）
        target_keys: 目标 key 元组（如 ('industry_trends', 'pain_points', 'current_measures')）
        max_depth: 最大递归深度，避免极端嵌套导致递归爆炸

    Returns:
        命中的 dict（包含至少一个 target key）；未命中返回 None。
        若顶层 dict 本身就包含目标 key，直接返回顶层。
    """
    if not isinstance(obj, dict) or max_depth < 0:
        return None

    # 当前层级是否包含任意目标 key
    if any(k in obj for k in target_keys):
        return obj

    # 递归下钻：对 dict 值与 list 元素继续搜索
    for v in obj.values():
        if isinstance(v, dict):
            found = _find_nested_dict_with_keys(v, target_keys, max_depth - 1)
            if found is not None:
                return found
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, dict):
                    found = _find_nested_dict_with_keys(item, target_keys, max_depth - 1)
                    if found is not None:
                        return found
    return None


@sales_twin_bp.route('/projects/<int:project_id>/strategy-items/ai-generate', methods=['POST'])
def ai_generate_strategy_items(project_id):
    """AI 生成战略项草稿（草稿模式，不写库）

    基于项目信息、关联客户信息、干系人、任务列表，调用 LLM 按 SVS 3-3-3 分析法
    生成 9 条战略项草稿（3 趋势 + 3 痛点 + 3 措施）。

    响应：{ "success": true, "draft": { "industry_trends": [...], "pain_points": [...], "current_measures": [...] } }
    """
    project = get_project_or_404(project_id)

    # 收集项目字段
    project_info = {
        'name': project.name or '',
        'customer_name': project.customer_name or '',
        'industry': project.industry or '',
        'competitive_analysis': (project.competitive_analysis or '')[:300],
    }

    # 收集关联客户字段（通过 customer_id 关联到 Customer 表）
    customer_info = {'core_products': '', 'company_history': ''}
    if project.customer_id:
        customer = Customer.query.get(project.customer_id)
        if customer:
            customer_info = {
                'core_products': (customer.core_products or '')[:PROMPT_FIELD_PREVIEW_LENGTH],
                'company_history': (customer.company_history or '')[:PROMPT_FIELD_PREVIEW_LENGTH],
            }

    # 收集干系人列表（department 通过 contact 关联获取）
    stakeholders = Stakeholder.query.filter_by(project_id=project_id).all()
    sk_list = []
    for s in stakeholders:
        department = ''
        if s.contact_id:
            contact = Contact.query.get(s.contact_id)
            if contact:
                department = contact.department or ''
        sk_list.append({
            'name': s.name or '',
            'position': s.position or '',
            'department': department,
            'responsibilities': (s.responsibilities or '')[:PROMPT_FIELD_PREVIEW_LENGTH],
            'personal_agenda': (s.personal_agenda or '')[:PROMPT_FIELD_PREVIEW_LENGTH],
        })

    # 收集任务列表
    tasks = OpportunityTask.query.filter_by(project_id=project_id).all()
    task_list = []
    for t in tasks:
        task_type = t.task_type
        if hasattr(task_type, 'value'):
            task_type = task_type.value
        task_list.append({
            'title': t.title or '',
            'description': (t.description or '')[:PROMPT_FIELD_PREVIEW_LENGTH],
            'task_type': task_type or '',
            'priority': t.priority or '',
        })

    context_json = json.dumps({
        'project': project_info,
        'customer': customer_info,
        'stakeholders': sk_list,
        'tasks': task_list,
    }, ensure_ascii=False, indent=2)

    prompt = f"""你是 B2B 销售数字孪生系统的战略分析助手。请基于 SVS 3-3-3 分析法，根据以下项目上下文生成 9 条战略项草稿：3 条行业趋势 + 3 条痛点 + 3 条客户当前措施。

# 项目上下文
{context_json}

# 任务要求
- 行业趋势（industry_trends）：识别客户所在行业的 3 个关键变化/趋势，说明对客户的影响领域
- 痛点（pain_points）：识别客户当前业务中的 3 个核心痛点，标注严重程度（high/medium/low）
- 当前措施（current_measures）：识别客户为应对痛点已采取的 3 个主要措施，评估有效性（high/medium/low/none）

# 输出格式
严格输出以下 JSON 结构（不要输出 markdown 代码块标记，不要附加任何说明文字）：
{{
  "industry_trends": [
    {{"name": "趋势名称（10-30字）", "description": "详细描述（50-150字）", "impact_area": "影响领域"}},
    {{"name": "...", "description": "...", "impact_area": "..."}},
    {{"name": "...", "description": "...", "impact_area": "..."}}
  ],
  "pain_points": [
    {{"name": "痛点名称（10-30字）", "description": "详细描述（50-150字）", "severity": "high|medium|low"}},
    {{"name": "...", "description": "...", "severity": "..."}},
    {{"name": "...", "description": "...", "severity": "..."}}
  ],
  "current_measures": [
    {{"name": "措施名称（10-30字）", "description": "详细描述（50-150字）", "effectiveness": "high|medium|low|none"}},
    {{"name": "...", "description": "...", "effectiveness": "..."}},
    {{"name": "...", "description": "...", "effectiveness": "..."}}
  ]
}}

注意：直接输出 JSON 数据，不要包含 thought/plan/reasoning/schema 等思考过程字段或元数据字段。"""

    messages = [
        {"role": "system", "content": "你是数据生成助手。严格按用户指定的 JSON 结构直接输出数据，不要包含 thought/plan/reasoning/schema 等任何元数据字段或思考过程。"},
        {"role": "user", "content": prompt},
    ]

    # LLM 客户端初始化失败（如 API key 未配置）→ 500
    try:
        from app.utils.llm_client import LLMClient
        llm = LLMClient()
    except Exception as e:
        return _llm_error_response('AI 生成失败', e)

    # chat_json 内部已尝试清理 markdown 代码块；JSON 解析仍失败 → 502
    try:
        result = llm.chat_json(
            messages=messages,
            temperature=0.5,
            max_tokens=2000
        )
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': f'AI 返回内容无法解析为 JSON: {str(e)[:ERROR_MESSAGE_MAX_LENGTH]}'
        }), 502
    except Exception as e:
        return _llm_error_response('AI 生成失败', e)

    if not isinstance(result, dict):
        return jsonify({
            'success': False,
            'error': 'AI 返回内容结构异常（非 JSON 对象）'
        }), 502

    # 防御性解析：LongCat-2.0 偶尔将真实数据包装在 thought/plan/details 或 prompt/schema 等结构中
    # 递归查找包含目标 key 的子对象，最多下钻 4 层
    target_keys = ('industry_trends', 'pain_points', 'current_measures')
    extracted = _find_nested_dict_with_keys(result, target_keys, max_depth=4)

    # 若递归查找未命中，但顶层已是期望结构，仍走原 result
    source = extracted if extracted is not None else result

    # 规范化草稿：确保三个数组都存在（即便 LLM 漏了某段也返回空数组）
    draft = {
        'industry_trends': source.get('industry_trends') if isinstance(source.get('industry_trends'), list) else [],
        'pain_points': source.get('pain_points') if isinstance(source.get('pain_points'), list) else [],
        'current_measures': source.get('current_measures') if isinstance(source.get('current_measures'), list) else [],
    }

    # 草稿模式：不调用 db.session.add / db.session.commit，由前端调用 POST /strategy-items 持久化
    return jsonify({'success': True, 'draft': draft}), 200



@sales_twin_bp.route('/projects/<int:project_id>/why-contexts/ai-generate', methods=['POST'])
def ai_generate_why_contexts(project_id):
    """AI 生成三个 WHY 上下文草稿（草稿模式，不写库）

    基于项目信息（competitive_analysis、industry、name）和战略要素（4 类）
    调用 LLM 生成 3 条 WHY 上下文：why / why_now / why_us。

    响应：{ "success": true, "draft": { "why": {...}, "why_now": {...}, "why_us": {...} } }
    """
    project = get_project_or_404(project_id)

    # 收集战略要素（4 类，每类最多 3 条，拼接 name + description）
    strategy_items_by_type = {}
    for item_type in ('industry_trend', 'pain_point', 'current_measure', 'strategic_initiative'):
        items = (
            ProjectStrategyItem.query
            .filter_by(project_id=project_id, item_type=item_type)
            .order_by(ProjectStrategyItem.sort_order.asc())
            .limit(3)
            .all()
        )
        strategy_items_by_type[item_type] = [
            {'name': it.name or '', 'description': it.description or ''}
            for it in items
        ]

    # 收集项目信息（完整文本，便于 LLM 生成有深度的 WHY 论述）
    project_info = {
        'name': project.name or '',
        'industry': project.industry or '',
        'competitive_analysis': (project.competitive_analysis or '')[:300],
        'strategy_items': strategy_items_by_type,
    }

    # 注入我方公司/产品信息
    company_context = _build_company_context()

    prompt = f"""你是 B2B 销售数字孪生系统的价值主张分析助手。请根据以下项目信息，按照 Challenge Sales 的重构逻辑生成 3 条 WHY 上下文。

# 项目信息
{json.dumps(project_info, ensure_ascii=False, indent=2)}

# 我方公司与产品信息
{company_context or '（未配置公司信息，请基于通用行业认知生成）'}

# 生成要求
- why（为什么改变）：从行业痛点切入，说明客户为什么需要改变现状，不改变的代价
- why_now（为什么是现在）：强调时机紧迫性（行业变化/政策/竞争压力等），错过窗口期的风险
- why_us（为什么是我们）：结合上方"我方公司与产品信息"中的产品特点和技术优势，突出我方差异化优势和可量化的业务价值，与客户战略的契合点

# 输出格式
严格输出以下 JSON 结构（不要输出 markdown 代码块标记，不要附加任何说明文字）：
{{
  "why": {{
    "context_text": "为什么改变的完整论述（150-300字）",
    "rationale": "论述逻辑的简短说明（50-100字）"
  }},
  "why_now": {{
    "context_text": "为什么是现在的完整论述（150-300字）",
    "rationale": "论述逻辑的简短说明（50-100字）"
  }},
  "why_us": {{
    "context_text": "为什么是我们的完整论述（150-300字）",
    "rationale": "论述逻辑的简短说明（50-100字）"
  }}
}}

注意：直接输出 JSON 数据，不要包含 thought/plan/reasoning/schema 等思考过程字段或元数据字段。"""

    messages = [
        {"role": "system", "content": "你是数据生成助手。严格按用户指定的 JSON 结构直接输出数据，不要包含 thought/plan/reasoning/schema 等任何元数据字段或思考过程。"},
        {"role": "user", "content": prompt},
    ]

    # LLM 客户端初始化失败（如 API key 未配置）→ 500
    try:
        from app.utils.llm_client import LLMClient
        llm = LLMClient()
    except Exception as e:
        return _llm_error_response('AI 生成失败', e)

    # chat_json 内部已尝试清理 markdown 代码块；JSON 解析仍失败 → 502
    try:
        result = llm.chat_json(
            messages=messages,
            temperature=0.5,
            max_tokens=2000
        )
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': f'AI 返回内容无法解析为 JSON: {str(e)[:ERROR_MESSAGE_MAX_LENGTH]}'
        }), 502
    except Exception as e:
        return _llm_error_response('AI 生成失败', e)

    if not isinstance(result, dict):
        return jsonify({
            'success': False,
            'error': 'AI 返回内容结构异常（非 JSON 对象）'
        }), 502

    # 防御性解析：LongCat-2.0 偶尔将真实数据包装在 thought/plan/details 或 prompt/schema 等结构中
    target_keys = ('why', 'why_now', 'why_us')
    extracted = _find_nested_dict_with_keys(result, target_keys, max_depth=4)
    source = extracted if extracted is not None else result

    # 规范化草稿：确保三个段都存在且结构完整
    def _normalize_section(section):
        if not isinstance(section, dict):
            return {'context_text': '', 'rationale': ''}
        return {
            'context_text': section.get('context_text') or '',
            'rationale': section.get('rationale') or '',
        }

    draft = {
        'why': _normalize_section(source.get('why')),
        'why_now': _normalize_section(source.get('why_now')),
        'why_us': _normalize_section(source.get('why_us')),
    }

    # 草稿模式：不调用 db.session.add / db.session.commit，由前端调用 POST /why-contexts 持久化
    return jsonify({'success': True, 'draft': draft}), 200



