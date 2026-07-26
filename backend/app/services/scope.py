"""数据权限范围（scope）提供者机制 —— 双版本架构核心扩展缝

社区版（salestwin）：单用户，不注入 provider，所有查询不过滤、owner_id 恒为 None。
商业版（salestwin-business）：business_ext 在应用启动时注入 provider（set_scope_provider），
实现 RBAC 三角色（admin/manager/sales）的数据隔离。

设计约束：
- provider 为 None 时，本模块所有函数必须零行为变化（社区版语义）
- scoped_* 返回 None 表示"不过滤"（社区版/管理员），返回列表表示可见 owner_id 集合
"""

import logging
from typing import Optional, List

logger = logging.getLogger(__name__)

_provider = None


def set_scope_provider(provider):
    """注入 scope provider（商业版在 create_app 后调用一次）。

    provider 需实现：
    - current_owner_id() -> Optional[int]：当前请求用户 ID（无登录上下文返回 None）
    - scoped_owner_ids() -> Optional[List[int]]：可见 owner_id 集合；None 表示不过滤
    """
    global _provider
    _provider = provider
    logger.info(f"数据权限范围提供者已注入: {type(provider).__name__}")


def get_scope_provider():
    return _provider


def current_owner_id() -> Optional[int]:
    """当前请求归属的用户 ID；社区版或无登录上下文时为 None"""
    if _provider is None:
        return None
    try:
        return _provider.current_owner_id()
    except Exception:
        # 请求上下文外（定时任务等）调用失败时按无过滤处理
        return None


def scoped_owner_ids() -> Optional[List[int]]:
    """当前请求可见的 owner_id 列表；None 表示不过滤（社区版/管理员）"""
    if _provider is None:
        return None
    try:
        return _provider.scoped_owner_ids()
    except Exception:
        return None


def _cached_visible_project_ids():
    """可见项目 ID 集合（请求级缓存）。返回 None 表示不过滤。"""
    owner_ids = scoped_owner_ids()
    if owner_ids is None:
        return None
    # 请求上下文内用 flask.g 缓存，避免 dashboard 等聚合接口多次打 DB
    try:
        from flask import g, has_request_context
        if has_request_context():
            cached = getattr(g, '_scoped_project_ids', None)
            if cached is not None:
                return cached
    except RuntimeError:
        has_request_context = lambda: False  # noqa: E731

    from app.models.database import Project
    if not owner_ids:
        ids = []
    else:
        ids = [pid for (pid,) in Project.query.with_entities(Project.id)
               .filter(Project.owner_id.in_(owner_ids)).all()]

    try:
        if has_request_context():
            g._scoped_project_ids = ids
    except RuntimeError:
        pass
    return ids


def apply_project_scope(query):
    """对 Project 查询应用数据权限过滤。无 provider 或不过滤时原样返回。"""
    owner_ids = scoped_owner_ids()
    if owner_ids is None:
        return query
    from app.models.database import Project
    # owner_ids 为空列表时 in_([]) 生成恒假条件，自然查无结果
    return query.filter(Project.owner_id.in_(owner_ids))


def scope_model_query(query, model):
    """对含 project_id 列的模型查询按可见项目集合过滤（不过滤时原样返回）"""
    ids = _cached_visible_project_ids()
    if ids is None:
        return query
    return query.filter(model.project_id.in_(ids))


def get_project_or_404(project_id: int):
    """按数据权限范围获取项目；越权访问与不存在一样返回 404（不泄露存在性）"""
    from app.models.database import Project
    return apply_project_scope(
        Project.query.filter(Project.id == project_id)
    ).first_or_404()


def current_scope_key() -> str:
    """当前数据范围指纹（用于按范围隔离的缓存键，如 Dashboard LLM 洞察缓存）。

    无范围过滤（社区版/管理员）返回 ''；有范围时返回 'owners:1,2,3'。
    """
    ids = scoped_owner_ids()
    if ids is None:
        return ''
    return 'owners:' + ','.join(str(i) for i in sorted(ids))
