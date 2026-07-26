"""
配置管理
统一从项目根目录的 .env 文件加载配置
"""

import os
import secrets
import logging
from dotenv import load_dotenv

# 加载项目根目录的 .env 文件
# 路径: MiroFish/.env (相对于 backend/app/config.py)
project_root_env = os.path.join(os.path.dirname(__file__), '../../.env')

if os.path.exists(project_root_env):
    load_dotenv(project_root_env, override=True)
else:
    # 如果根目录没有 .env，尝试加载环境变量（用于生产环境）
    load_dotenv(override=True)


def _get_secret_key():
    """获取 SECRET_KEY：优先环境变量，否则随机生成并警告"""
    env_key = os.environ.get('SECRET_KEY')
    if env_key and env_key != 'dealtwin-default-secret':
        return env_key
    # 默认值随机生成（生产安全）：每次启动不同，session 会在重启后失效
    # 部署时务必通过环境变量设置固定值
    generated = secrets.token_hex(32)
    logging.getLogger(__name__).warning(
        "SECRET_KEY 未在环境变量中配置或为默认值，已随机生成。"
        "重启后所有 session 将失效，生产环境请务必设置固定的 SECRET_KEY 环境变量。"
    )
    return generated


class Config:
    """Flask配置类"""

    # Flask配置
    SECRET_KEY = _get_secret_key()
    # DEBUG 默认 False（生产安全）；开发时通过 .env 设置 FLASK_DEBUG=True
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'

    # JSON配置 - 禁用ASCII转义，让中文直接显示（而不是 \uXXXX 格式）
    JSON_AS_ASCII = False

    # LLM配置（统一使用OpenAI格式）
    # 项目硬约束：必须使用 Base URL: https://api.longcat.chat/openai, Model: LongCat-2.0
    LLM_API_KEY = os.environ.get('LLM_API_KEY')
    LLM_BASE_URL = os.environ.get('LLM_BASE_URL', 'https://api.longcat.chat/openai')
    LLM_MODEL_NAME = os.environ.get('LLM_MODEL_NAME', 'LongCat-2.0')

    # Tavily配置（网络搜索API）
    TAVILY_API_KEY = os.environ.get('TAVILY_API_KEY')

    # 实时联网搜索配置（多 provider 链式降级）
    # provider 优先级列表（逗号分隔）：tavily, baidu, sogou, llm_knowledge
    WEB_SEARCH_PROVIDERS = [
        p.strip() for p in os.environ.get(
            'WEB_SEARCH_PROVIDERS', 'tavily,baidu,sogou,llm_knowledge'
        ).split(',') if p.strip()
    ]
    WEB_SEARCH_TIMEOUT = int(os.environ.get('WEB_SEARCH_TIMEOUT', '15'))  # 单次请求超时秒数
    WEB_SEARCH_MAX_RESULTS = int(os.environ.get('WEB_SEARCH_MAX_RESULTS', '5'))  # 每个 provider 最大结果数
    WEB_SEARCH_REQUEST_INTERVAL = float(os.environ.get('WEB_SEARCH_REQUEST_INTERVAL', '2'))  # 直接抓取请求间隔秒数（反爬）

    # 单 provider 启用/禁用开关
    BAIDU_SEARCH_ENABLED = os.environ.get('BAIDU_SEARCH_ENABLED', 'True').lower() == 'true'
    SOGOU_SEARCH_ENABLED = os.environ.get('SOGOU_SEARCH_ENABLED', 'True').lower() == 'true'
    WEBSITE_SCRAPING_ENABLED = os.environ.get('WEBSITE_SCRAPING_ENABLED', 'True').lower() == 'true'
    BUSINESS_INFO_SCRAPING_ENABLED = os.environ.get('BUSINESS_INFO_SCRAPING_ENABLED', 'True').lower() == 'true'

    # CORS 允许的来源（逗号分隔；默认仅允许本地开发环境）
    CORS_ORIGINS = [
        origin.strip() for origin in os.environ.get(
            'CORS_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://localhost:3000,http://127.0.0.1:3000'
        ).split(',') if origin.strip()
    ]

    # 文件上传配置
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '../uploads')
    ALLOWED_EXTENSIONS = {'pdf', 'md', 'txt', 'markdown'}

    # 文本处理配置
    DEFAULT_CHUNK_SIZE = 500  # 默认切块大小
    DEFAULT_CHUNK_OVERLAP = 50  # 默认重叠大小

    # 数据库配置
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URI',
        'sqlite:///' + os.path.join(os.path.dirname(__file__), '../instance/sales_twin.db')
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # SQLite 并发写入优化：增加超时时间，避免 "database is locked" 错误
    SQLALCHEMY_ENGINE_OPTIONS = {
        'connect_args': {'timeout': 30},
        'pool_pre_ping': True,
    }

    # APScheduler 配置（后台 Agent 定时任务）
    SCHEDULER_API_ENABLED = False  # 不暴露内置调度器 API（使用自定义路由）
    SCHEDULER_TIMEZONE = "Asia/Shanghai"

    @classmethod
    def validate(cls) -> list[str]:
        """验证必要配置"""
        errors: list[str] = []
        if not cls.LLM_API_KEY:
            errors.append("LLM_API_KEY 未配置")
        return errors
