"""
数据库迁移脚本：创建 stage_deliverable 表（阶段交付物追踪）。

通过 db.create_all() 创建表（自动读取 StageDeliverable 模型定义）。
可重复运行：若表已存在则跳过。
"""

import os
import sys
import sqlite3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app, db


def table_exists(conn, table):
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    return len(cur.fetchall()) > 0


def main():
    app = create_app()
    with app.app_context():
        db_path = app.config.get('SQLALCHEMY_DATABASE_URI')
        if db_path and db_path.startswith('sqlite:///'):
            db_path = db_path.replace('sqlite:///', '')
        else:
            db_path = os.path.join(os.path.dirname(__file__), '../instance/sales_twin.db')

        if not os.path.exists(db_path):
            print(f"数据库文件不存在: {db_path}，将直接 create_all")
            db.create_all()
            print("已通过 create_all 创建表（含 stage_deliverable）")
            return

        print(f"迁移数据库: {db_path}")
        table = 'stage_deliverable'
        conn = sqlite3.connect(db_path)
        try:
            already_exists = table_exists(conn, table)
        finally:
            conn.close()

        if already_exists:
            print(f"  [跳过] {table} 表已存在")
        else:
            db.create_all()
            print(f"  [新增] 已创建 {table} 表")
        print("迁移完成")


if __name__ == '__main__':
    main()
