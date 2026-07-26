"""
DealTwin Backend - Flask应用工厂
"""

import os
import warnings

# 抑制 multiprocessing resource_tracker 的警告（来自第三方库如 transformers）
# 需要在所有其他导入之前设置
warnings.filterwarnings("ignore", message=".*resource_tracker.*")

from flask import Flask, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

from .config import Config
from .utils.logger import setup_logger, get_logger

db = SQLAlchemy()


def create_app(config_class=Config):
    """Flask应用工厂函数"""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # 初始化数据库
    db.init_app(app)

    # 启动时从数据库加载 LLM 配置（覆盖 .env 中的值）
    try:
        from .models.database import CompanyProfile
        with app.app_context():
            profile = CompanyProfile.query.first()
            if profile:
                if profile.llm_api_key:
                    app.config['LLM_API_KEY'] = profile.llm_api_key
                    config_class.LLM_API_KEY = profile.llm_api_key
                if profile.llm_base_url:
                    app.config['LLM_BASE_URL'] = profile.llm_base_url
                    config_class.LLM_BASE_URL = profile.llm_base_url
                if profile.llm_model_name:
                    app.config['LLM_MODEL_NAME'] = profile.llm_model_name
                    config_class.LLM_MODEL_NAME = profile.llm_model_name
    except Exception:
        pass  # 首次启动表不存在时静默跳过

    # 设置JSON编码：确保中文直接显示（而不是 \uXXXX 格式）
    # Flask >= 2.3 使用 app.json.ensure_ascii，旧版本使用 JSON_AS_ASCII 配置
    if hasattr(app, 'json') and hasattr(app.json, 'ensure_ascii'):
        app.json.ensure_ascii = False

    # 设置日志
    logger = setup_logger('dealtwin')

    # 只在 reloader 子进程中打印启动信息（避免 debug 模式下打印两次）
    is_reloader_process = os.environ.get('WERKZEUG_RUN_MAIN') == 'true'
    debug_mode = app.config.get('DEBUG', False)
    should_log_startup = not debug_mode or is_reloader_process

    if should_log_startup:
        logger.info("=" * 50)
        logger.info("DealTwin Backend 启动中...")
        logger.info("=" * 50)

    # 启用CORS（限定具体来源，避免任意网站跨域访问）
    cors_origins = app.config.get('CORS_ORIGINS', ['http://localhost:5173'])
    CORS(app, resources={r"/api/*": {"origins": cors_origins}})

    # 请求日志中间件
    @app.before_request
    def log_request():
        logger = get_logger('dealtwin.request')
        logger.debug(f"请求: {request.method} {request.path}")
        if request.content_type and 'json' in request.content_type:
            logger.debug(f"请求体: {request.get_json(silent=True)}")

    @app.after_request
    def log_response(response):
        logger = get_logger('dealtwin.request')
        logger.debug(f"响应: {response.status_code}")
        return response

    # 注册蓝图
    from .api import sales_twin_bp
    app.register_blueprint(sales_twin_bp, url_prefix='/api/sales-twin')

    # 健康检查
    @app.route('/health')
    def health():
        return {'status': 'ok', 'service': 'DealTwin Backend'}

    # 初始化后台定时任务调度器（仅在非 reloader 进程中启动，避免 debug 模式下重复启动）
    _init_scheduler(app, should_log_startup)

    if should_log_startup:
        logger.info("DealTwin Backend 启动完成")

    return app


def _init_scheduler(app, should_log_startup):
    """初始化 APScheduler 并注册白泽 Agent 后台任务

    项目使用 debug=True + use_reloader=False（单进程）模式运行。
    Flask-APScheduler 的 start() 在 debug 模式下会跳过启动（等待 reloader 子进程），
    但我们不使用 reloader，所以必须直接调用底层 APScheduler.start() 绕过此检查。
    """
    is_reloader_process = os.environ.get('WERKZEUG_RUN_MAIN') == 'true'
    debug_mode = app.config.get('DEBUG', False)
    use_reloader = os.environ.get('FLASK_RELOAD', 'false').lower() == 'true'
    is_reloader_parent = debug_mode and use_reloader and not is_reloader_process
    if is_reloader_parent:
        return

    from .extensions import scheduler
    scheduler.init_app(app)

    from .jobs.tasks import (
        daily_project_health_scan,
        weekly_strategy_evaluation,
        daily_customer_news_fetch,
    )

    # 先启动调度器，再添加任务：确保 add_job 时调度器已运行，
    # next_run_time 会被同步计算（避免 pending job 的 next_run_time 未设置的竞态）
    # 直接调用底层 _scheduler.start() 绕过 Flask-APScheduler 的 debug 模式跳过逻辑
    scheduler._scheduler.start()

    # 每日凌晨 2 点：商机盲区静默扫描
    scheduler.add_job(
        id='Daily_Health_Scan',
        func=daily_project_health_scan,
        trigger='cron',
        hour=2, minute=0,
        replace_existing=True,
    )

    # 每日凌晨 4 点：客户网络情报拉取
    scheduler.add_job(
        id='Daily_News_Fetch',
        func=daily_customer_news_fetch,
        trigger='cron',
        hour=4, minute=0,
        replace_existing=True,
    )

    # 每周五 23:59：量化策略复盘与模式提取
    scheduler.add_job(
        id='Weekly_Learning_Eval',
        func=weekly_strategy_evaluation,
        trigger='cron',
        day_of_week='fri',
        hour=23, minute=59,
        replace_existing=True,
    )

    if should_log_startup:
        logger = get_logger('dealtwin')
        logger.info("APScheduler 已启动，注册 3 个后台 Agent 任务")
