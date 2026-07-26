# 白泽 (BaiZe OS) - Agent 后台定时任务 (Cron) 扩展指南

> **目标受众**: AI 辅助编程系统 (Cursor/Trae/Windsurf 等)
> **架构核心**: 引入 `Flask-APScheduler`，赋予系统自主运行能力，使其能够在后台定期执行情报搜集、盲区扫描和量化策略复盘。

---

## 1. 依赖安装
在 `backend/requirements.txt` 中新增：
```text
Flask-APScheduler==1.12.4
```

---

## 2. 调度器扩展初始化
**新建文件**: `backend/app/extensions.py` (如果还没有的话，用于存放全局扩展)

```python
from flask_apscheduler import APScheduler

# 实例化调度器
scheduler = APScheduler()
```

---

## 3. 配置调度器
**修改文件**: `backend/app/config.py`

在 `Config` 类中新增 APScheduler 的配置：

```python
class Config:
    # ... 现有配置 ...

    # APScheduler 配置
    SCHEDULER_API_ENABLED = True  # 允许通过 API 管理任务（可选）
    SCHEDULER_TIMEZONE = "Asia/Shanghai"  # 设定时区
```

---

## 4. 编写后台 Agent 任务逻辑 (Jobs)
**新建目录与文件**: `backend/app/jobs/__init__.py` 和 `backend/app/jobs/tasks.py`

```python
# backend/app/jobs/tasks.py
from app.utils.logger import get_logger
from app.models.database import db, Project
from app.services.blind_spot_detector import BlindSpotDetector
# from app.services.learning_evaluator import LearningEvaluator # 之前设计的复盘服务
# from app.services.web_researcher import WebResearcher

logger = get_logger("baize_cron")

def daily_project_health_scan():
    # 每日商机健康度与盲区静默扫描
    logger.info("[Cron] 开启每日商机盲区扫描...")
    # 这里的 app 是从扩展中获取的，因为定时任务需要应用上下文
    from run import app 
    with app.app_context():
        # 获取所有活跃阶段的项目
        active_projects = Project.query.filter(~Project.sales_stage.in_(['closed_won', 'closed_lost'])).all()
        for proj in active_projects:
            try:
                detector = BlindSpotDetector()
                # 扫描发现盲区，可自动写入 Task 或生成提醒
                blindspots = detector.detect(proj.id)
                if blindspots:
                    logger.info(f"项目 {proj.name} 发现新盲区，已记录。")
                    # TODO: 调用 ActionRecommender 将紧急盲区转化为 OpportunityTask
            except Exception as e:
                logger.error(f"项目 {proj.id} 扫描失败: {str(e)}")

def weekly_strategy_evaluation():
    # 每周量化策略复盘与 Alpha 提取
    logger.info("[Cron] 开启每周量化策略提取...")
    from run import app
    with app.app_context():
        try:
            # evaluator = LearningEvaluator()
            # evaluator.run_batch_evaluation()
            logger.info("本周模式提取完成，等待总监审批。")
        except Exception as e:
            logger.error(f"每周策略复盘失败: {str(e)}")

def daily_customer_news_fetch():
    # 每日客户网络情报拉取
    logger.info("[Cron] 开启每日客户情报拉取...")
    # 调用 Tavily API 扫描项目关联客户的新闻
    pass
```

---

## 5. 注册并启动调度器
**修改文件**: `backend/app/__init__.py`

在 `create_app` 工厂函数中注册 Scheduler：

```python
from app.extensions import scheduler
from app.jobs.tasks import daily_project_health_scan, weekly_strategy_evaluation, daily_customer_news_fetch

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # ... 其他初始化 (db.init_app, CORS, etc.) ...

    # 初始化 Scheduler
    scheduler.init_app(app)

    # 注册定时任务 (Cron Jobs)
    # 每日凌晨 2 点：健康度扫描
    scheduler.add_job(id='Daily_Health_Scan', func=daily_project_health_scan, trigger='cron', hour=2, minute=0)

    # 每日凌晨 4 点：拉取网络情报
    scheduler.add_job(id='Daily_News_Fetch', func=daily_customer_news_fetch, trigger='cron', hour=4, minute=0)

    # 每周五 23:59：运行量化学习复盘
    scheduler.add_job(id='Weekly_Learning_Eval', func=weekly_strategy_evaluation, trigger='cron', day_of_week='fri', hour=23, minute=59)

    # 启动调度器
    scheduler.start()

    # ... 注册 Blueprint ...

    return app
```

---

## 6. (可选) 增加 Agent 监控 API
在 `sales_twin_bp` 中增加一个路由，供前端查看当前后台驻留了哪些 Agent 任务，以及它们的下一次执行时间。

```python
# backend/app/api/sales_twin/agent_monitor.py
from flask import jsonify
from app.api.sales_twin import sales_twin_bp
from app.extensions import scheduler

@sales_twin_bp.route('/agent/jobs', methods=['GET'])
def get_agent_jobs():
    # 获取所有后台自动任务的状态
    jobs = scheduler.get_jobs()
    job_list = []
    for job in jobs:
        job_list.append({
            "id": job.id,
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            "pending": job.pending
        })
    return jsonify({"success": True, "data": job_list})
```

---
**注意事项 (给 AI 编程助手的提示)**: 
在 Flask 中执行后台线程任务时，由于脱离了原本的 HTTP Request 请求生命周期，操作数据库 (`db.session`) 必须被包裹在 `with app.app_context():` 中，否则 SQLAlchemy 会抛出 `RuntimeError: Working outside of application context`。
