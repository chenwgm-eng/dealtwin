"""
API路由模块
"""

from flask import Blueprint

sales_twin_bp = Blueprint('sales_twin', __name__)

from . import sales_twin  # noqa: E402, F401
