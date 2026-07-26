"""
数据库迁移脚本：将 stage_deliverable 表中 deliverable_key 的
pm10/pm20/pm30/pm40/pm70 前缀迁移为 om10/om20/om30/om40/om70。

对应 OM 里程碑命名统一重构（PM → OM）。
可重复运行：若记录已迁移则跳过（rowcount=0）。
"""

import os
import sys
import sqlite3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app


def main():
    app = create_app()
    with app.app_context():
        db_path = app.config.get('SQLALCHEMY_DATABASE_URI')
        if db_path and db_path.startswith('sqlite:///'):
            db_path = db_path.replace('sqlite:///', '')
        else:
            db_path = os.path.join(os.path.dirname(__file__), '../instance/sales_twin.db')

        if not os.path.exists(db_path):
            print(f"数据库文件不存在: {db_path}")
            return

        print(f"迁移数据库: {db_path}")
        conn = sqlite3.connect(db_path)
        try:
            # 依次将 deliverable_key 中的 pm10/pm20/pm30/pm40/pm70 替换为 om 前缀
            # 注意：本场景键名不存在前缀嵌套问题（如 pm10 不会误匹配 pm100），顺序不严格要求
            migrations = [
                ('pm10', 'om10'),
                ('pm20', 'om20'),
                ('pm30', 'om30'),
                ('pm40', 'om40'),
                ('pm70', 'om70'),
            ]
            for old, new in migrations:
                cur = conn.execute(
                    "UPDATE stage_deliverable SET deliverable_key = REPLACE(deliverable_key, ?, ?) "
                    "WHERE deliverable_key LIKE ?",
                    (old, new, f'%{old}%')
                )
                print(f"  [替换] {old} → {new}: 影响 {cur.rowcount} 行")
            conn.commit()
            print("迁移完成")
        finally:
            conn.close()


if __name__ == '__main__':
    main()
