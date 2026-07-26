"""
B2B销售数字孪生系统 - 核心API
"""

import json
import os
import re
import uuid
import calendar
import logging
import threading
from flask import request, jsonify, send_from_directory
from datetime import datetime, date as date_type, timedelta

from app import db
from app.models.database import (
    Project, Stakeholder, Relationship, MeetingSimulation,
    OpportunityTask, StateChangeLog, MeetingPlan, FeedbackRecord,
    SuggestionPool, Customer, Contact, DashboardInsightCache, StageDeliverable,
    ProjectStrategyItem, ProjectWhyContext, CompanyProfile, CompanyAttachment,
    MilestoneDecision, ChallengerTeaching, LearningPattern
)
from app.services.dashboard_insight_generator import DashboardInsightGenerator
from app.services.scope import (
    apply_project_scope, scope_model_query, current_owner_id, get_project_or_404,
    current_scope_key,
)
from .. import sales_twin_bp

logger = logging.getLogger(__name__)

# Dashboard 洞察缓存生成锁：防止并发请求重复调用 LLM 并竞争写缓存
_dashboard_insight_lock = threading.Lock()


# 拜访记录附件上传目录
FEEDBACK_ATTACHMENT_DIR = os.path.join(os.path.dirname(__file__), '../../uploads/feedback_attachments')
# 阶段交付物附件上传目录（按 project_id/stage/deliverable_key 分级存放）
STAGE_DELIVERABLE_ATTACHMENT_DIR = os.path.join(os.path.dirname(__file__), '../../uploads/stage_deliverable_attachments')
ALLOWED_ATTACHMENT_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
                                  'txt', 'md', 'png', 'jpg', 'jpeg', 'gif', 'zip', 'rar'}

# 分页参数默认值
DEFAULT_PER_PAGE = 20
MAX_PER_PAGE = 100
# LLM 生成文本字段存储最大长度（防止数据库 TEXT 字段溢出）
MAX_TEXT_FIELD_LENGTH = 10000
# 错误消息回显最大长度（防止泄漏堆栈细节）
ERROR_MESSAGE_MAX_LENGTH = 200
# LLM prompt 中字段预览截断长度（控制 prompt 总长度）
PROMPT_FIELD_PREVIEW_LENGTH = 200




def _allowed_attachment(filename):
    """检查附件扩展名是否合法"""
    if not filename or '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in ALLOWED_ATTACHMENT_EXTENSIONS



def _parse_pagination_params():
    """从 request.args 解析分页参数（page/per_page），返回 (page, per_page)

    - page 最小为 1
    - per_page 默认 DEFAULT_PER_PAGE，限制在 [1, MAX_PER_PAGE]
    """
    page = max(request.args.get('page', 1, type=int), 1)
    per_page = min(max(request.args.get('per_page', DEFAULT_PER_PAGE, type=int), 1), MAX_PER_PAGE)
    return page, per_page



def _now_iso_z():
    """返回带 'Z' 后缀的当前 UTC ISO 时间字符串（用于图谱节点/边的 timestamp 字段）"""
    return datetime.utcnow().isoformat() + 'Z'



def _llm_error_response(prefix, e):
    """构造 LLM 路由统一错误响应（500）

    Args:
        prefix: 错误前缀（如"生成失败"、"排版失败"）
        e: 捕获的异常对象

    Returns:
        (jsonify(...), 500) 元组，可直接 return
    """
    return jsonify({
        'success': False,
        'error': f'{prefix}: {str(e)[:ERROR_MESSAGE_MAX_LENGTH]}'
    }), 500



def _parse_date(val):
    """安全解析日期字符串"""
    if not val or val in ('', 'null'):
        return None
    if isinstance(val, date_type):
        return val
    try:
        return date_type.fromisoformat(str(val)[:10])
    except (ValueError, TypeError):
        return None



def _extract_json_object(text):
    """从LLM输出中提取JSON对象

    处理三种常见情况：
    1. 纯JSON文本
    2. ```json ... ``` 代码块包裹
    3. JSON前后有额外说明文字

    Returns:
        解析后的dict/list，解析失败返回None
    """
    if not text:
        return None
    cleaned = text.strip()
    # 去除markdown代码块标记
    cleaned = re.sub(r'^```(?:json)?\s*\n?', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\n?```\s*$', '', cleaned)
    cleaned = cleaned.strip()
    # 尝试直接解析
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    # 正则提取第一个JSON对象
    m = re.search(r'\{[\s\S]*\}', cleaned)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            return None
    return None


# === 以下函数/常量已拆分到子模块，此处 re-export 以保持向后兼容 ===
# 核心工具函数（_now_iso_z / _extract_json_object）必须在本文件中先于子模块导入语句被定义，
# 子模块通过 from ._helpers import _now_iso_z, _extract_json_object 引用。
from ._helpers_graph import (
    B2B_CORE_NODE_TYPES, NODE_TYPE_LABELS, EDGE_TYPE_LABELS,
    _filter_b2b_graph, _build_stakeholder_graph, _make_edge,
    _merge_stakeholders_into_graph, _build_industry_trend_nodes,
    _build_current_measure_nodes, _build_pain_point_nodes,
    _build_strategic_initiative_from_background, _build_project_context_nodes,
    _build_stakeholder_agenda_nodes, _build_task_nodes,
    _infer_task_agenda_mapping, _build_extended_edges,
)
from ._helpers_serializers import (
    suggestion_to_dict, task_to_dict, feedback_record_to_dict,
    project_to_dict, _enum_str, _resolve_reports_to_from_contact,
    stakeholder_to_dict, relationship_to_dict, customer_to_dict,
    _compute_interaction_stats, compute_contact_interaction_status,
    contact_to_dict, _build_project_context, _build_project_insight_summary,
    _build_company_context,
)
from ._helpers_dashboard import (
    _resolve_dashboard_time_range, _get_cached_insights, _save_insights_to_cache,
)


__all__ = [
    # 常量与配置
    'FEEDBACK_ATTACHMENT_DIR', 'STAGE_DELIVERABLE_ATTACHMENT_DIR',
    'ALLOWED_ATTACHMENT_EXTENSIONS', 'DEFAULT_PER_PAGE', 'MAX_PER_PAGE',
    'MAX_TEXT_FIELD_LENGTH', 'ERROR_MESSAGE_MAX_LENGTH', 'PROMPT_FIELD_PREVIEW_LENGTH',
    # Flask/DB 对象
    'db', 'sales_twin_bp', 'logger', '_dashboard_insight_lock',
    # 模块级依赖（子模块通过星号导入使用）
    'json', 'os', 're', 'uuid', 'calendar', 'threading',
    'request', 'jsonify', 'send_from_directory',
    'datetime', 'date_type', 'timedelta',
    # ORM 模型
    'Project', 'Stakeholder', 'Relationship', 'MeetingSimulation',
    'OpportunityTask', 'StateChangeLog', 'MeetingPlan', 'FeedbackRecord',
    'SuggestionPool', 'Customer', 'Contact', 'DashboardInsightCache',
    'StageDeliverable', 'ProjectStrategyItem', 'ProjectWhyContext',
    'CompanyProfile', 'CompanyAttachment', 'DashboardInsightGenerator',
    'MilestoneDecision', 'ChallengerTeaching', 'LearningPattern',
    # 工具函数
    '_allowed_attachment', '_parse_pagination_params', '_now_iso_z',
    '_llm_error_response', '_parse_date', '_extract_json_object',
    '_filter_b2b_graph', '_resolve_dashboard_time_range',
    '_get_cached_insights', '_save_insights_to_cache',
    '_build_project_context', '_build_project_insight_summary',
    '_build_company_context', '_build_stakeholder_graph', '_make_edge',
    '_merge_stakeholders_into_graph',
    # 数据权限范围（社区版 provider=None 时零行为变化）
    'apply_project_scope', 'scope_model_query', 'current_owner_id', 'get_project_or_404',
    'current_scope_key',
    # 序列化函数
    'suggestion_to_dict', 'task_to_dict', 'feedback_record_to_dict',
    'project_to_dict', '_enum_str', '_resolve_reports_to_from_contact',
    'stakeholder_to_dict', 'relationship_to_dict', 'customer_to_dict',
    '_compute_interaction_stats', 'compute_contact_interaction_status',
    'contact_to_dict',
    # 图谱构建函数
    '_build_industry_trend_nodes', '_build_current_measure_nodes',
    '_build_pain_point_nodes', '_build_strategic_initiative_from_background',
    '_build_project_context_nodes', '_build_stakeholder_agenda_nodes',
    '_build_task_nodes', '_build_extended_edges', '_infer_task_agenda_mapping',
]
