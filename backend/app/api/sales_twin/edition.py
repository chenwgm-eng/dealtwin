"""DealTwin 社区版扩展注册表（@edition 存根）

社区版默认无客户管理/认证/RBAC 扩展。
商业版（dealtwin-business）通过注入 set_edition_provider 启用扩展功能。

用法（商业版）：
    from app.api.sales_twin.edition import set_edition_provider
    set_edition_provider(BusinessEditionProvider())
"""
from __future__ import annotations
from typing import Any, Callable

# 扩展点类型：商业版可注入的客户管理 API 工厂函数
EditionProvider = Any
_provider: EditionProvider | None = None


def set_edition_provider(provider: EditionProvider | None) -> None:
    """注入商业版扩展提供者（社区版不调用此函数）"""
    global _provider
    _provider = provider


def get_edition_provider() -> EditionProvider | None:
    """获取当前扩展提供者（社区版返回 None）"""
    return _provider


def has_customer_module() -> bool:
    """是否启用客户管理模块（社区版 False）"""
    return _provider is not None and getattr(_provider, 'customer_module_enabled', False)


def has_auth() -> bool:
    """是否启用认证模块（社区版 False）"""
    return _provider is not None and getattr(_provider, 'auth_enabled', False)