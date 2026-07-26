from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, DateTime, Enum, CheckConstraint, Date, Boolean, UniqueConstraint, Index
from sqlalchemy.orm import relationship

from app import db


class Customer(db.Model):
    """客户档案 - 独立客户实体，支持树形多层级（总公司/子公司）"""
    __tablename__ = 'customer'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    parent_id = Column(Integer, ForeignKey('customer.id'), nullable=True)

    # 工商注册信息
    unified_credit_code = Column(String(50), nullable=True)  # 统一社会信用代码
    registered_capital = Column(String(100), nullable=True)  # 注册资本
    establish_date = Column(Date, nullable=True)  # 成立日期
    legal_representative = Column(String(100), nullable=True)  # 法定代表人
    enterprise_type = Column(String(100), nullable=True)  # 企业类型
    operating_status = Column(String(50), nullable=True)  # 经营状态
    business_scope = Column(Text, nullable=True)  # 经营范围

    # 业务信息
    industry = Column(String(100), nullable=True)  # 所处行业
    core_products = Column(Text, nullable=True)  # 核心产品/服务
    company_history = Column(Text, nullable=True)  # 公司发展历程
    scale_employees = Column(String(50), nullable=True)  # 员工规模
    scale_revenue = Column(String(50), nullable=True)  # 营收规模
    branch_count = Column(Integer, nullable=True)  # 分支机构数

    # 工商联系人
    business_contact_name = Column(String(100), nullable=True)
    business_contact_phone = Column(String(50), nullable=True)
    business_contact_email = Column(String(100), nullable=True)

    # 地址
    registered_address = Column(String(500), nullable=True)  # 注册地址
    office_address = Column(String(500), nullable=True)  # 办公地址

    # 客户概览（从Project迁移，跨项目共享）
    customer_background = Column(Text, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    children = relationship('Customer', backref=db.backref('parent', remote_side='Customer.id'), cascade='all, delete-orphan')
    contacts = relationship('Contact', back_populates='customer', cascade='all, delete-orphan')
    projects = relationship('Project', back_populates='customer')


class Contact(db.Model):
    """客户联系人 - 独立于Stakeholder的轻量级联系人"""
    __tablename__ = 'contact'

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey('customer.id'), nullable=False)
    name = Column(String(100), nullable=False)
    department = Column(String(100), nullable=True)
    position = Column(String(100), nullable=True)
    phone = Column(String(50), nullable=True)
    email = Column(String(100), nullable=True)
    address = Column(String(500), nullable=True)
    remark = Column(Text, nullable=True)

    # 组织架构图谱：汇报关系（自引用）+ 来源标记
    reports_to_id = Column(Integer, ForeignKey('contact.id'), nullable=True)
    source = Column(String(20), nullable=False, default='manual')  # manual|web_search|llm_inferred

    # 互动触达状态手工覆盖：null=自动计算；red/yellow/green=手工指定
    interaction_status_override = Column(String(10), nullable=True)  # red|yellow|green

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    customer = relationship('Customer', back_populates='contacts')
    reports_to = relationship('Contact', remote_side='Contact.id', backref='subordinates')


class Project(db.Model):
    __tablename__ = 'project'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    customer_id = Column(Integer, ForeignKey('customer.id'), nullable=True)
    customer_name = Column(String(200), nullable=True)  # 保留向后兼容
    # 数据归属（商业版 RBAC：销售=本人/经理=团队/管理员=全部；社区版恒为 NULL 不过滤）
    owner_id = Column(Integer, nullable=True)
    # 销售阶段：suspect/identity/define/confirm/closed_won/closed_lost
    # 基于 SVS+Challenge Sales 五阶段模型
    sales_stage = Column(String(50), nullable=False, default='suspect')
    budget = Column(Float, nullable=True)

    industry = Column(String(100), nullable=True)
    company_vision = Column(Text, nullable=True)
    business_pain_points = Column(Text, nullable=True)

    # 商机计划相关（SVS框架：客户背景与需求/价值主张/竞争分析，LLM生成+人工可编辑）
    customer_background = Column(Text, nullable=True)
    value_proposition = Column(Text, nullable=True)
    competitive_analysis = Column(Text, nullable=True)

    # 预计关闭时间
    expected_close_date = Column(Date, nullable=True)

    # 销售数字孪生：确定性/倾向性（1=红/2=黄/3=绿，NULL=未设置）
    time_certainty = Column(Integer, nullable=True)
    budget_certainty = Column(Integer, nullable=True)
    tendency = Column(Integer, nullable=True)

    # SVS 销售模式：inside_sales / prescriptive_pursuit / value_solution_selling
    sales_mode = Column(String(50), nullable=True)

    # Win/Loss 复盘（OM70 关闭时填写）
    close_reason_category = Column(String(50), nullable=True)  # price/product/relationship/competition/timing/no_decision/other
    close_reason_detail = Column(Text, nullable=True)
    lessons_learned = Column(Text, nullable=True)

    # 关联的图谱项目ID（保留字段；SalesTwin 图谱已改为数据库注入式加载）
    graph_project_id = Column(String(100), nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    stakeholders = relationship('Stakeholder', back_populates='project', cascade='all, delete-orphan')
    customer = relationship('Customer', back_populates='projects')
    relationships = relationship('Relationship', back_populates='project', cascade='all, delete-orphan')
    meetings = relationship('MeetingSimulation', back_populates='project', cascade='all, delete-orphan')
    tasks = relationship('OpportunityTask', back_populates='project', cascade='all, delete-orphan')
    meeting_plans = relationship('MeetingPlan', back_populates='project', cascade='all, delete-orphan')
    feedback_records = relationship('FeedbackRecord', back_populates='project', cascade='all, delete-orphan')
    state_changes = relationship('StateChangeLog', back_populates='project', cascade='all, delete-orphan')
    suggestions = relationship('SuggestionPool', back_populates='project', cascade='all, delete-orphan')


class Stakeholder(db.Model):
    __tablename__ = 'stakeholder'

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('project.id'), nullable=False)
    name = Column(String(100), nullable=False)
    position = Column(String(100), nullable=True)
    level = Column(String(50), nullable=True)
    responsibilities = Column(Text, nullable=True)

    personal_agenda = Column(Text, nullable=True)

    # 角色类型（原"买家角色"）：行为定位
    buyer_role = Column(Enum('mobilizer', 'blocker', 'guide', 'champion', 'skeptic', 'coach', name='buyer_role_enum'), nullable=True)

    # Challenger 社交风格（影响 Tailoring 定制沟通）：analytical=分析型 / driver=推动型 / amiable=亲和型 / expressive=表达型
    social_style = Column(Enum('analytical', 'driver', 'amiable', 'expressive', name='social_style_enum'), nullable=True)

    # 项目角色：在采购决策中的职能
    project_role = Column(Enum('technical_buyer', 'business_buyer', 'financial_buyer', 'influencer', 'decision_maker', 'user', name='project_role_enum'), nullable=True)

    # 识别状态：confirmed=已确认 / pending=待识别（AI生成默认 pending）
    status = Column(String(20), nullable=False, default='pending')

    # 关联客户联系人（可空；为空表示第三方临时性人员）
    contact_id = Column(Integer, ForeignKey('contact.id'), nullable=True)

    # 汇报对象（自引用，指向同一项目内的另一个干系人）
    reports_to_id = Column(Integer, ForeignKey('stakeholder.id'), nullable=True)

    decision_power = Column(Integer, nullable=False, default=5)
    support_level = Column(Integer, nullable=False, default=5)
    urgency = Column(Integer, nullable=False, default=5)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship('Project', back_populates='stakeholders')
    contact = relationship('Contact', foreign_keys=[contact_id])

    __table_args__ = (
        CheckConstraint('decision_power >= 0 AND decision_power <= 10', name='decision_power_range'),
        CheckConstraint('support_level >= 0 AND support_level <= 10', name='support_level_range'),
        CheckConstraint('urgency >= 0 AND urgency <= 10', name='urgency_range'),
        CheckConstraint("status IN ('confirmed', 'pending')", name='stakeholder_status_range'),
    )


class Relationship(db.Model):
    __tablename__ = 'relationship'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('project.id'), nullable=False)
    source_id = Column(Integer, ForeignKey('stakeholder.id'), nullable=False)
    target_id = Column(Integer, ForeignKey('stakeholder.id'), nullable=False)
    
    relationship_type = Column(Enum('direct_report', 'peer', 'allies', 'conflict', 'mentor', 'friend', name='relationship_type_enum'), nullable=False)
    
    influence_weight = Column(Float, nullable=False, default=0.5)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    project = relationship('Project', back_populates='relationships')
    
    __table_args__ = (
        CheckConstraint('influence_weight >= 0 AND influence_weight <= 1', name='influence_weight_range'),
    )


class MeetingSimulation(db.Model):
    __tablename__ = 'meeting_simulation'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('project.id'), nullable=False)
    name = Column(String(200), nullable=False)
    
    input_pdfs = Column(Text, nullable=True)
    participants = Column(Text, nullable=True)
    
    simulation_result = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default='pending')
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    project = relationship('Project', back_populates='meetings')


class OpportunityTask(db.Model):
    __tablename__ = 'opportunity_task'

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('project.id'), nullable=False)
    stakeholder_id = Column(Integer, ForeignKey('stakeholder.id'), nullable=True)
    # 关联多个干系人（JSON数组，存干系人ID）；stakeholder_id 保留作为主干系人/兼容字段
    stakeholder_ids = Column(Text, nullable=True)

    task_type = Column(Enum('blind_spot', 'address_concerns', 'build_alliance', 'provide_material', 'meeting', 'follow_up', name='task_type_enum'), nullable=False)

    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    action_brief = Column(Text, nullable=True)

    priority = Column(String(20), nullable=False, default='medium')
    # pending(待办) / in_progress(进行中) / completed(已完成) / cancelled(已取消)
    status = Column(String(20), nullable=False, default='pending')

    # 来源：recommended_action(从行动建议采纳) / manual(手动创建) / feedback(反馈生成)
    source = Column(String(50), nullable=False, default='manual')
    # 采纳自哪条行动建议的标识（JSON: {target_stakeholder, action_type, priority_score...}）
    source_action = Column(Text, nullable=True)
    # 关联反馈ID（反馈更新该待办时记录）
    related_feedback = Column(Text, nullable=True)
    # 计划完成时间
    due_date = Column(DateTime, nullable=True)
    # 完成时间
    completed_at = Column(DateTime, nullable=True)
    # 完成备注
    completion_note = Column(Text, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship('Project', back_populates='tasks')


class MeetingPlan(db.Model):
    """拜访前预案（结构化预案生成）"""
    __tablename__ = 'meeting_plan'

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('project.id'), nullable=False)
    stakeholder_id = Column(Integer, ForeignKey('stakeholder.id'), nullable=False)
    # 关联多个干系人（JSON数组，存干系人ID）；stakeholder_id 保留作为主干系人/兼容字段
    stakeholder_ids = Column(Text, nullable=True)

    name = Column(String(200), nullable=False)
    meeting_purpose = Column(String(200), nullable=True)  # 会议目的
    meeting_type = Column(String(50), nullable=True)      # first_visit/proposal_report/objection_handling/relationship_maintenance

    # 关联的待办事项ID（JSON数组）
    related_task_ids = Column(Text, nullable=True)
    # 关联资料描述（JSON数组：文件名/类型）
    related_materials = Column(Text, nullable=True)

    # LLM生成的结构化预案（JSON）
    plan_content = Column(Text, nullable=True)
    # 状态: pending / generated / reviewed
    status = Column(String(50), nullable=False, default='pending')

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship('Project', back_populates='meeting_plans')


class FeedbackRecord(db.Model):
    """反馈记录（与待办关联）"""
    __tablename__ = 'feedback_record'

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('project.id'), nullable=False)

    # 关联的待办事项ID（JSON数组，表示这次反馈完成了哪些待办）
    related_task_ids = Column(Text, nullable=True)
    # 关联的拜访预案ID（可选）
    related_meeting_plan_id = Column(Integer, nullable=True)

    feedback_text = Column(Text, nullable=False)
    # 解析结果摘要
    parse_summary = Column(Text, nullable=True)
    # 总变更数
    total_changes = Column(Integer, nullable=False, default=0)
    # 附件（JSON数组：[{filename, original_filename, size, uploaded_at}]）
    attachments = Column(Text, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    project = relationship('Project', back_populates='feedback_records')


class StateChangeLog(db.Model):
    __tablename__ = 'state_change_log'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('project.id'), nullable=False)
    stakeholder_id = Column(Integer, ForeignKey('stakeholder.id'), nullable=True)
    
    change_object = Column(String(100), nullable=False)
    attribute_name = Column(String(50), nullable=False)
    old_value = Column(String(100), nullable=True)
    new_value = Column(String(100), nullable=False)
    
    reasoning = Column(Text, nullable=True)
    
    change_source = Column(String(50), nullable=False, default='manual')
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    project = relationship('Project', back_populates='state_changes')


class SuggestionPool(db.Model):
    """建议池（从深度访谈对话、推演报告中采纳的建议片段）"""
    __tablename__ = 'suggestion_pool'

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('project.id'), nullable=False)

    content = Column(Text, nullable=False)
    # 来源: interview(深度访谈) / report(推演报告) / manual(手动添加)
    source = Column(String(50), nullable=False, default='manual')
    # 来源上下文 JSON: {stakeholder_name, section_title, ...}
    source_context = Column(Text, nullable=True)

    # 是否已被采纳生成待办
    is_consumed = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship('Project', back_populates='suggestions')


class StageDeliverable(db.Model):
    """阶段交付物追踪 - 记录每个项目各阶段交付物的完成状态

    基于 sales_stages spec 定义的任务清单和交付物清单，落地为可勾选/检查的系统能力。
    """
    __tablename__ = 'stage_deliverable'
    __table_args__ = (
        # 同一项目同一阶段同一交付物键唯一
        UniqueConstraint('project_id', 'stage', 'deliverable_key', name='uq_stage_deliverable'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('project.id'), nullable=False)
    # 阶段枚举：suspect/identity/define/confirm/closed_won/closed_lost
    stage = Column(String(50), nullable=False)
    # 交付物唯一键（同阶段内唯一），如 'account_plan.company_structure'
    deliverable_key = Column(String(100), nullable=False)
    is_completed = Column(Boolean, nullable=False, default=False)
    completed_at = Column(DateTime, nullable=True)
    # 操作人（可选，未来接入用户系统后使用）
    completed_by = Column(String(100), nullable=True)
    # 备注（可选）
    notes = Column(Text, nullable=True)
    # 附件清单（JSON 数组：[{filename, original_filename, size, uploaded_at}]）
    # 与 FeedbackRecord.attachments 格式一致，便于复用前端样式
    attachments = Column(Text, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship('Project', backref='stage_deliverables')


class DashboardInsightCache(db.Model):
    """Dashboard 智能洞察缓存 - 按 (start_date, end_date, scope_key) 唯一，避免重复 LLM 调用

    scope_key：数据权限范围指纹（社区版恒为 ''；商业版按可见 owner 集合区分，防止跨用户串数据）
    """
    __tablename__ = 'dashboard_insight_cache'
    __table_args__ = (
        UniqueConstraint('start_date', 'end_date', 'scope_key', name='uix_dashboard_insight_start_end'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    start_date = Column(Date, nullable=False, index=True)
    end_date = Column(Date, nullable=False, index=True)
    scope_key = Column(String(100), nullable=False, default='')
    period = Column(String(32), nullable=True)  # 自定义模式时为 None
    label = Column(String(32), nullable=False)  # 如"本季度"/"自定义"
    insights_json = Column(Text, nullable=False)  # 存 JSON 字符串

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<DashboardInsightCache {self.label} {self.start_date}~{self.end_date}>'


class ProjectStrategyItem(db.Model):
    """项目战略要素条目 - 结构化存储客户背景中的行业趋势/当前措施/痛点/战略举措。

    由 _migrate_legacy_text_to_structured 从 project.customer_background 切分迁移而来，
    也可由前端手动新增。替代原 customer_background 大文本字段，支持细粒度编辑和图谱连线。
    """
    __tablename__ = 'project_strategy_item'
    __table_args__ = (
        # 同一项目同一类型下排序值唯一，避免重复迁移
        UniqueConstraint('project_id', 'item_type', 'sort_order', name='uq_project_strategy_item_pid_itype_sort'),
        # 加速按项目+类型分组查询
        Index('ix_project_strategy_item_pid_itype', 'project_id', 'item_type'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('project.id'), nullable=False)
    # 条目类型：industry_trend(行业趋势) / current_measure(当前措施) / pain_point(痛点) / strategic_initiative(战略举措)
    item_type = Column(String(50), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    # JSON 字符串：存储 impact_area/effectiveness/severity 等扩展字段
    metadata_json = Column(Text, nullable=True)
    sort_order = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship('Project', backref='strategy_items')


class ProjectWhyContext(db.Model):
    """项目 Why 上下文 - 结构化存储价值主张中的 why/why_now/why_us 三段。

    由 _migrate_legacy_text_to_structured 从 project.value_proposition 切分迁移而来，
    也可由前端手动编辑。替代原 value_proposition 大文本字段，支撑 Tailoring 关系连线。
    """
    __tablename__ = 'project_why_context'
    __table_args__ = (
        # 同一项目同一类型只能 1 条
        UniqueConstraint('project_id', 'context_type', name='uq_project_why_context_pid_ctype'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('project.id'), nullable=False)
    # 上下文类型：why(为什么改变) / why_now(为什么是现在) / why_us(为什么是我们)
    context_type = Column(String(50), nullable=False)
    context_text = Column(Text, nullable=True)
    rationale = Column(Text, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship('Project', backref='why_contexts')


class CompanyProfile(db.Model):
    """我方公司档案 - 单例（仅 1 行），存储公司介绍、产品介绍和 LLM 配置"""
    __tablename__ = 'company_profile'

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_name = Column(String(200), nullable=True)
    company_intro = Column(Text, nullable=True)
    product_intro = Column(Text, nullable=True)
    # LLM 配置（运行时可覆盖 .env 中的值；为空时 fallback 到 Config）
    llm_api_key = Column(String(500), nullable=True)
    llm_base_url = Column(String(500), nullable=True)
    llm_model_name = Column(String(200), nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class CompanyAttachment(db.Model):
    """公司产品附件 - 上传的 PDF/MD/TXT 文件，提取文本用于 LLM prompt"""
    __tablename__ = 'company_attachment'

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_name = Column(String(200), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(50), nullable=True)
    file_size = Column(Integer, nullable=True)
    extracted_text = Column(Text, nullable=True)  # 提取的文本内容（用于 LLM prompt）

    uploaded_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class AIRecommendationLog(db.Model):
    """AI 推荐日志 — 记录每次推荐的状态向量和探索/利用标记"""
    __tablename__ = 'ai_recommendation_log'
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('project.id'), nullable=True)
    rec_type = Column(String(50))  # next_best_action, meeting_plan, blindspot_fix
    source_service = Column(String(50))  # 产生此建议的模块
    rec_text = Column(Text)  # 给用户的自然语言文本
    structured_payload = Column(Text)  # JSON: 结构化动作指令

    # 状态向量化 (Factor Vectors)
    momentum_factor = Column(Float, default=0.0)
    coverage_factor = Column(Float, default=0.0)
    completeness_factor = Column(Float, default=0.0)
    pain_factor = Column(Float, default=0.0)
    stage_at_generation = Column(String(50))

    # 探索与利用 (E&E)
    is_exploration = Column(Boolean, default=False)
    confidence_score = Column(Float, default=0.0)
    pattern_id = Column(Integer, ForeignKey('learning_pattern.id'), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)


class AIRecommendationOutcome(db.Model):
    """AI 推荐结果追踪 — 多级反馈"""
    __tablename__ = 'ai_recommendation_outcome'
    id = Column(Integer, primary_key=True, autoincrement=True)
    recommendation_id = Column(Integer, ForeignKey('ai_recommendation_log.id'), unique=True)

    # L1: 采纳反馈
    is_adopted = Column(Boolean, default=False)
    adopted_task_id = Column(Integer, ForeignKey('opportunity_task.id'), nullable=True)
    reject_reason = Column(String(100))

    # L2: 执行反馈
    is_executed = Column(Boolean, default=False)
    execution_result = Column(String(50))  # success / neutral / failed

    # L3: 阶段反馈 (短期)
    triggered_stage_advance = Column(Boolean, default=False)

    # L4: 终局反馈 (长期)
    final_win = Column(Boolean, nullable=True)

    scored_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class LearningPattern(db.Model):
    """学习模式 — 从历史推荐结果中提取的成功/失败模式"""
    __tablename__ = 'learning_pattern'
    id = Column(Integer, primary_key=True, autoincrement=True)
    pattern_type = Column(String(50))  # success_pattern / failure_pattern
    name = Column(String(200))
    trigger_conditions_json = Column(Text)  # JSON: 触发因子阈值
    recommended_play = Column(Text)

    evidence_count = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)

    status = Column(String(20), default='candidate')  # candidate / approved / deprecated
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BlindSpotReport(db.Model):
    """盲区扫描报告 - 持久化每次扫描结果，支持手动/cron两种来源

    每个 project 保留全部历史报告，前端按时间倒序取最新一份展示。
    """
    __tablename__ = 'blind_spot_report'
    __table_args__ = (
        Index('ix_blind_spot_report_pid_time', 'project_id', 'scanned_at'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('project.id'), nullable=False)
    scan_source = Column(String(20), nullable=False)  # manual / cron
    overall_score = Column(Integer, default=0)
    summary = Column(Text)
    findings_json = Column(Text)  # JSON: findings 列表
    total_findings = Column(Integer, default=0)
    total_stakeholders = Column(Integer, default=0)
    total_relationships = Column(Integer, default=0)
    scanned_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    project = relationship('Project', backref='blind_spot_reports')


class AgentJobRun(db.Model):
    """Agent 后台任务运行历史 - 记录每次 cron 执行的状态和产出摘要

    供 AgentJobManager 页面展示最近运行记录，让用户直观看到 Agent 工作状态。
    """
    __tablename__ = 'agent_job_run'
    __table_args__ = (
        Index('ix_agent_job_run_jobid_time', 'job_id', 'started_at'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(100), nullable=False)  # Daily_Health_Scan / Daily_News_Fetch / Weekly_Learning_Eval
    started_at = Column(DateTime, nullable=False)
    finished_at = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False)  # success / failed / partial
    items_processed = Column(Integer, default=0)
    items_succeeded = Column(Integer, default=0)
    summary = Column(Text)
    error_message = Column(Text)


class CustomerIntelSnapshot(db.Model):
    """客户情报历史快照 - 每次拉取的客户网络情报独立存储，可追溯变化

    替代原 tasks.py 中写回 Customer.profile_overview 的逻辑（该字段实际不存在）。
    """
    __tablename__ = 'customer_intel_snapshot'
    __table_args__ = (
        Index('ix_customer_intel_snapshot_cid_time', 'customer_id', 'fetched_at'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey('customer.id'), nullable=True)  # 可为空（项目仅存客户名时）
    customer_name = Column(String(200), nullable=False)
    industry = Column(String(100), nullable=True)
    report_text = Column(Text)
    source = Column(String(20), nullable=False)  # manual / cron
    fetched_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    customer = relationship('Customer', backref='intel_snapshots')


class MilestoneDecision(db.Model):
    """SVS 里程碑决策记录（OM10 Bid/No-Go、OM20 Go/No-Go、OM30 策略评审、OM40 投标批准、OM70 赢/丢单）

    每个项目每个里程碑仅一条记录（决策可更新，保留历史于 StateChangeLog）。
    五维评估（1-5 分）对应 SVS 商机评估维度：战略契合度/预期收入规模/竞争强度/资源需求/成功概率。
    """
    __tablename__ = 'milestone_decision'
    __table_args__ = (
        UniqueConstraint('project_id', 'milestone', name='uq_milestone_decision_project_milestone'),
        CheckConstraint('strategic_fit >= 1 AND strategic_fit <= 5', name='md_strategic_fit_range'),
        CheckConstraint('revenue_scale >= 1 AND revenue_scale <= 5', name='md_revenue_scale_range'),
        CheckConstraint('competitive_intensity >= 1 AND competitive_intensity <= 5', name='md_competitive_intensity_range'),
        CheckConstraint('resource_requirement >= 1 AND resource_requirement <= 5', name='md_resource_requirement_range'),
        CheckConstraint('success_probability >= 1 AND success_probability <= 5', name='md_success_probability_range'),
    )

    MILESTONES = ('om10', 'om20', 'om30', 'om40', 'om70')

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('project.id'), nullable=False)
    milestone = Column(String(20), nullable=False)  # om10/om20/om30/om40/om70
    decision = Column(String(20), nullable=False, default='pending')  # go / no_go / pending

    # 五维评估（1-5 分，可空=未评估）
    strategic_fit = Column(Integer, nullable=True)
    revenue_scale = Column(Integer, nullable=True)
    competitive_intensity = Column(Integer, nullable=True)
    resource_requirement = Column(Integer, nullable=True)
    success_probability = Column(Integer, nullable=True)

    rationale = Column(Text, nullable=True)  # 决策依据
    decided_by = Column(String(100), nullable=True)  # 决策人
    decided_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship('Project', backref=db.backref('milestone_decisions', cascade='all, delete-orphan'))


class ChallengerTeaching(db.Model):
    """Challenger 商业指导话术（Vision Setting 七步法）

    teaching_content JSON 结构：
    - warmer: 热身（建立关系）
    - reframe: 重构（问题背后的问题）
    - rational_drowning: 理性冲击
    - emotional_impact: 感性冲击
    - new_way: 新方法
    - our_solution: 我方方案
    - call_to_action: 行动号召
    - powerful_ask: {why, when, who, what} 有力的请求四要素
    - validation_factors: [认可要素列表]（可验证的客户行动信号）
    - tailoring_note: 针对目标干系人社交风格的定制沟通建议
    """
    __tablename__ = 'challenger_teaching'
    __table_args__ = (
        Index('ix_challenger_teaching_pid_time', 'project_id', 'created_at'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('project.id'), nullable=False)
    # 目标干系人（可空=面向采购群体通用）
    stakeholder_id = Column(Integer, ForeignKey('stakeholder.id'), nullable=True)

    name = Column(String(200), nullable=False)
    teaching_content = Column(Text, nullable=True)  # JSON，见 docstring
    status = Column(String(50), nullable=False, default='pending')  # pending / generated

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship('Project', backref=db.backref('challenger_teachings', cascade='all, delete-orphan'))
    # 干系人删除时由 API 层将 stakeholder_id 置空，保留通用话术
    stakeholder = relationship('Stakeholder', foreign_keys=[stakeholder_id])
