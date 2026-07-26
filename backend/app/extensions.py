"""Flask 扩展实例（全局单例）

此处仅声明扩展实例，不绑定具体 app。
具体绑定在 create_app 工厂中通过 init_app 完成。
"""

from flask_apscheduler import APScheduler

# 后台定时任务调度器
# 在 create_app 中通过 scheduler.init_app(app) 绑定应用
scheduler = APScheduler()
