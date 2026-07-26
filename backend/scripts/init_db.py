"""
数据库初始化脚本
用于创建所有数据库表
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app, db


def init_database():
    """初始化数据库"""
    app = create_app()
    
    with app.app_context():
        db_dir = os.path.join(os.path.dirname(__file__), '../instance')
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)
        
        db.create_all()
        print("数据库表创建成功！")
        
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"已创建表: {tables}")


if __name__ == '__main__':
    init_database()