"""
数据库迁移脚本：为 Contact 新增 interaction_status_override 字段（手工覆盖互动触达状态）。

SQLite 支持 ALTER TABLE ADD COLUMN，可直接为已有表添加列。
可重复运行：若列已存在则跳过。
"""

import os
import sys
import sqlite3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app, db


def column_exists(conn, table, column):
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cur.fetchall())


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
            print("已通过 create_all 创建表（含新字段）")
            return

        print(f"迁移数据库: {db_path}")
        conn = sqlite3.connect(db_path)
        try:
            table, column, col_type = 'contact', 'interaction_status_override', 'VARCHAR(10)'
            if column_exists(conn, table, column):
                print(f"  [跳过] {table}.{column} 已存在")
            else:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
                print(f"  [新增] {table}.{column} ({col_type})")
            conn.commit()
            print("迁移完成")
        finally:
            conn.close()


if __name__ == '__main__':
    main()
