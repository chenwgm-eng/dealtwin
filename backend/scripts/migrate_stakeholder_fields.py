"""
迁移脚本：为 stakeholder 表添加 project_role、status、contact_id 字段

变更说明：
- 新增 project_role: 项目角色（technical_buyer/business_buyer/financial_buyer/influencer/decision_maker/user）
- 新增 status: 识别状态（confirmed/pending），默认 pending
- 新增 contact_id: 关联客户联系人 ID（可空）

注意：
- buyer_role 字段保留，前端展示改名为"角色类型"
- AI 生成的干系人默认 status='pending'
- 历史数据 status 统一设为 'confirmed'（已存在的人工创建数据）

使用方法：
    python scripts/migrate_stakeholder_fields.py
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app import create_app, db
from sqlalchemy import text


def migrate():
    app = create_app()
    with app.app_context():
        # 检查字段是否已存在
        inspector = db.inspect(db.engine)
        columns = [c['name'] for c in inspector.get_columns('stakeholder')]

        added = []

        if 'project_role' not in columns:
            print('添加 project_role 字段...')
            db.session.execute(text(
                "ALTER TABLE stakeholder ADD COLUMN project_role VARCHAR(20) NULL"
            ))
            added.append('project_role')
        else:
            print('project_role 字段已存在，跳过')

        if 'status' not in columns:
            print('添加 status 字段（默认 pending）...')
            db.session.execute(text(
                "ALTER TABLE stakeholder ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'pending'"
            ))
            added.append('status')
        else:
            print('status 字段已存在，跳过')

        if 'contact_id' not in columns:
            print('添加 contact_id 字段...')
            db.session.execute(text(
                "ALTER TABLE stakeholder ADD COLUMN contact_id INTEGER NULL"
            ))
            # 添加外键约束
            try:
                db.session.execute(text(
                    "ALTER TABLE stakeholder ADD CONSTRAINT fk_stakeholder_contact_id "
                    "FOREIGN KEY (contact_id) REFERENCES contact(id)"
                ))
            except Exception as e:
                print(f'外键约束可能已存在或失败（可忽略）: {e}')
            added.append('contact_id')
        else:
            print('contact_id 字段已存在，跳过')

        # 将历史数据标记为 confirmed（避免现有数据被视为"待识别"）
        if 'status' in added:
            print('将历史干系人 status 标记为 confirmed...')
            db.session.execute(text(
                "UPDATE stakeholder SET status = 'confirmed' WHERE status = 'pending' AND name NOT LIKE '[待识别]%'"
            ))

        # 添加 status CHECK 约束（如果不存在）
        try:
            db.session.execute(text(
                "ALTER TABLE stakeholder ADD CONSTRAINT stakeholder_status_range "
                "CHECK (status IN ('confirmed', 'pending'))"
            ))
            print('已添加 status CHECK 约束')
        except Exception as e:
            print(f'status CHECK 约束可能已存在（可忽略）: {e}')

        db.session.commit()
        print(f'\n迁移完成。新增字段: {added if added else "无"}')

        # 统计结果
        result = db.session.execute(text(
            "SELECT status, COUNT(*) FROM stakeholder GROUP BY status"
        ))
        print('\n干系人状态统计:')
        for row in result:
            print(f'  {row[0]}: {row[1]} 条')


if __name__ == '__main__':
    migrate()
