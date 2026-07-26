"""双版本架构字段迁移（幂等）：

1. project 表新增 owner_id（INTEGER NULL；商业版 RBAC 数据归属，社区版恒为 NULL）
2. dashboard_insight_cache 表新增 scope_key（VARCHAR(100) NOT NULL DEFAULT ''），
   唯一约束重建为 (start_date, end_date, scope_key)
   —— 该表为 LLM 洞察缓存，数据可丢弃：缺 scope_key 列时直接 DROP 后按当前模型重建。

兼容 SQLite / PostgreSQL / MySQL（ADD COLUMN IF NOT EXISTS 语法差异通过 inspect 前置判断规避）。

用法: python scripts/migrate_scope_v1.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import inspect, text

from app import create_app, db


def _column_names(inspector, table):
    return {c['name'] for c in inspector.get_columns(table)}


def migrate():
    app = create_app()
    with app.app_context():
        engine = db.engine

        # 1. project.owner_id
        if 'owner_id' not in _column_names(inspect(engine), 'project'):
            db.session.execute(text('ALTER TABLE project ADD COLUMN owner_id INTEGER NULL'))
            db.session.commit()
            print('[OK] project.owner_id 已添加')
        else:
            print('[SKIP] project.owner_id 已存在')

        # 2. dashboard_insight_cache.scope_key（缓存表可弃，缺列则重建）
        if 'scope_key' not in _column_names(inspect(engine), 'dashboard_insight_cache'):
            db.session.execute(text('DROP TABLE dashboard_insight_cache'))
            db.session.commit()
            from app.models.database import DashboardInsightCache
            DashboardInsightCache.__table__.create(engine)
            print('[OK] dashboard_insight_cache 已按 (start_date, end_date, scope_key) 唯一约束重建（旧缓存已清空）')
        else:
            print('[SKIP] dashboard_insight_cache.scope_key 已存在')


if __name__ == '__main__':
    migrate()
