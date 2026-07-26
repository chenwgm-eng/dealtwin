"""B2B销售数字孪生系统 - Dashboard 工具函数（从 _helpers.py 拆分）"""

import json
import calendar
import logging
from datetime import date as date_type

from app import db
from app.models.database import DashboardInsightCache
from app.services.scope import current_scope_key

logger = logging.getLogger(__name__)


def _resolve_dashboard_time_range(period=None, start=None, end=None):
    """解析 Dashboard 时间范围

    优先级：
    1. 若 start 和 end 同时提供，使用自定义范围（label="自定义"）
    2. 否则使用 period（两者均无时默认 period='this_quarter'）

    季度定义：Q1=1-3月, Q2=4-6月, Q3=7-9月, Q4=10-12月
    下一季度：若当前是 Q3，下一季度是 Q4（Q4 下一季度为次年 Q1）

    Args:
        period: 可选，值为 this_month/this_quarter/next_quarter/this_year
        start: 可选，YYYY-MM-DD 字符串
        end: 可选，YYYY-MM-DD 字符串

    Returns:
        (start_date: datetime.date, end_date: datetime.date, label: str)
    """
    today = date_type.today()

    # 优先级1：自定义范围
    if start and end:
        try:
            start_date = date_type.fromisoformat(str(start)[:10])
            end_date = date_type.fromisoformat(str(end)[:10])
            return (start_date, end_date, 'Custom')
        except (ValueError, TypeError):
            pass  # 解析失败则回退到 period

    # 优先级2：period，默认 this_quarter
    if not period:
        period = 'this_quarter'

    # 当前季度序号（1-4）
    cur_quarter = (today.month - 1) // 3 + 1

    def _quarter_bounds(year, quarter):
        """计算指定年份季度的起止日期"""
        start_month = (quarter - 1) * 3 + 1
        end_month = start_month + 2
        q_start = date_type(year, start_month, 1)
        q_end = date_type(year, end_month, calendar.monthrange(year, end_month)[1])
        return q_start, q_end

    if period == 'this_month':
        start_date = today.replace(day=1)
        end_date = today.replace(day=calendar.monthrange(today.year, today.month)[1])
        label = 'This Month'
    elif period == 'this_quarter':
        start_date, end_date = _quarter_bounds(today.year, cur_quarter)
        label = 'This Quarter'
    elif period == 'next_quarter':
        if cur_quarter == 4:
            start_date, end_date = _quarter_bounds(today.year + 1, 1)
        else:
            start_date, end_date = _quarter_bounds(today.year, cur_quarter + 1)
        label = 'Next Quarter'
    elif period == 'this_year':
        start_date = today.replace(month=1, day=1)
        end_date = today.replace(month=12, day=31)
        label = 'This Year'
    else:
        # 未知 period 值，回退到本季度
        start_date, end_date = _quarter_bounds(today.year, cur_quarter)
        label = 'This Quarter'

    return (start_date, end_date, label)



def _get_cached_insights(start_date, end_date):
    """按时间范围+数据权限范围查询缓存的智能洞察，命中返回 dict，未命中返回 None"""
    try:
        cache = DashboardInsightCache.query.filter_by(
            start_date=start_date, end_date=end_date, scope_key=current_scope_key()
        ).first()
        if cache is None:
            return None
        return json.loads(cache.insights_json)
    except Exception as e:
        logger.warning(f"读取 Dashboard 洞察缓存失败: {e}")
        return None



def _save_insights_to_cache(start_date, end_date, period, label, insights):
    """保存智能洞察到缓存（按 时间范围+数据权限范围 upsert）"""
    try:
        scope_key = current_scope_key()
        cache = DashboardInsightCache.query.filter_by(
            start_date=start_date, end_date=end_date, scope_key=scope_key
        ).first()
        insights_json = json.dumps(insights, ensure_ascii=False)
        if cache is None:
            cache = DashboardInsightCache(
                start_date=start_date,
                end_date=end_date,
                scope_key=scope_key,
                period=period,
                label=label,
                insights_json=insights_json,
            )
            db.session.add(cache)
        else:
            cache.period = period
            cache.label = label
            cache.insights_json = insights_json
        db.session.commit()
    except Exception as e:
        logger.warning(f"保存 Dashboard 洞察缓存失败: {e}")
        db.session.rollback()
