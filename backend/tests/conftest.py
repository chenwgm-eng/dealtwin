import sys
import os

# 将 backend/ 加入 sys.path，使 `from app import ...` 可用
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from app import create_app, db
from app.config import Config


class TestConfig(Config):
    """测试配置：使用内存 SQLite，跳过调度器

    - SQLALCHEMY_DATABASE_URI: 内存数据库，不影响开发环境数据
    - DEBUG=True: 配合 FLASK_RELOAD=true 环境变量跳过 APScheduler 启动
      (_init_scheduler 中 is_reloader_parent = debug_mode and use_reloader and not is_reloader_process)
    """
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


@pytest.fixture
def app(monkeypatch):
    # 跳过 APScheduler 启动：模拟 reloader 父进程
    monkeypatch.setenv('FLASK_RELOAD', 'true')
    monkeypatch.delenv('WERKZEUG_RUN_MAIN', raising=False)

    app = create_app(config_class=TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()
