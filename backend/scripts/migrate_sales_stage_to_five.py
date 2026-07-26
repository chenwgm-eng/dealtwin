"""
数据库迁移脚本：将 Project.sales_stage 从旧版四阶段模型迁移到新版五阶段模型。

旧版 → 新版映射：
- discovery     → suspect
- qualification → identity
- proposal      → define
- negotiation   → confirm
- closed_won    → closed_won（保留）
- closed_lost   → closed_lost（保留）

可重复运行：仅更新仍为旧版值的记录，已迁移的记录不受影响。
"""

import os
import sys
import sqlite3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app


# 旧版 → 新版阶段映射
LEGACY_STAGE_MAPPING = {
    'discovery': 'suspect',
    'qualification': 'identity',
    'proposal': 'define',
    'negotiation': 'confirm',
    # closed_won / closed_lost 保留不变
}


def main():
    app = create_app()
    with app.app_context():
        db_path = app.config.get('SQLALCHEMY_DATABASE_URI')
        if db_path and db_path.startswith('sqlite:///'):
            db_path = db_path.replace('sqlite:///', '')
        else:
            db_path = os.path.join(os.path.dirname(__file__), '../instance/sales_twin.db')

        if not os.path.exists(db_path):
            print(f"数据库文件不存在: {db_path}，无需迁移")
            return

        print(f"迁移销售阶段: {db_path}")
        conn = sqlite3.connect(db_path)
        try:
            cur = conn.cursor()

            # 先统计各阶段当前数量
            cur.execute("SELECT sales_stage, COUNT(*) FROM project GROUP BY sales_stage")
            before = cur.fetchall()
            print("迁移前阶段分布:")
            for stage, count in before:
                print(f"  {stage or '(NULL)'}: {count}")

            total_updated = 0
            for old_stage, new_stage in LEGACY_STAGE_MAPPING.items():
                cur.execute(
                    "UPDATE project SET sales_stage = ? WHERE sales_stage = ?",
                    (new_stage, old_stage)
                )
                updated = cur.rowcount
                if updated > 0:
                    print(f"  [迁移] {old_stage} → {new_stage}: {updated} 条记录")
                total_updated += updated

            conn.commit()

            # 迁移后统计
            cur.execute("SELECT sales_stage, COUNT(*) FROM project GROUP BY sales_stage")
            after = cur.fetchall()
            print("迁移后阶段分布:")
            for stage, count in after:
                print(f"  {stage or '(NULL)'}: {count}")

            if total_updated == 0:
                print("无旧版阶段数据需要迁移（已是新版或无数据）")
            else:
                print(f"迁移完成，共更新 {total_updated} 条记录")
        finally:
            conn.close()


if __name__ == '__main__':
    main()
