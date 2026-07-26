"""B2B销售数字孪生系统 - 核心API（包聚合）

将原 sales_twin.py（4527 行）拆分为多个子模块，按业务域组织。
所有路由仍注册到 sales_twin_bp（在 app.api 包中创建），URL 与函数签名完全向后兼容。

子模块：
- _helpers: 共享 imports/常量/helper 函数（含 to_dict 系列）
- sales_twin_projects: 项目 CRUD + Dashboard
- sales_twin_stakeholders: 干系人 + 关系
- sales_twin_analysis: LLM 分析类路由
- sales_twin_tasks: 待办 + 建议池
- sales_twin_feedback: 反馈记录 + 状态日志
- sales_twin_stage: 阶段交付物
- sales_twin_customers: 客户 + 联系人
- sales_twin_meetings: 会议计划
- sales_twin_graph: 图谱
- sales_twin_strategy: 项目战略项 + 三个WHY上下文
- sales_twin_challenger: Challenger 商业指导 + 检查清单
- sales_twin_milestones: SVS 里程碑决策 + 销售模式
"""
# re-export sales_twin_bp，支持 `from .sales_twin import sales_twin_bp`
from .. import sales_twin_bp  # noqa: E402, F401

# 触发各子模块加载，注册路由到 sales_twin_bp
from . import _helpers  # noqa: E402, F401
from . import sales_twin_projects  # noqa: E402, F401
from . import sales_twin_stakeholders  # noqa: E402, F401
from . import sales_twin_analysis  # noqa: E402, F401
from . import sales_twin_tasks  # noqa: E402, F401
from . import sales_twin_feedback  # noqa: E402, F401
from . import sales_twin_stage  # noqa: E402, F401
from . import sales_twin_meetings  # noqa: E402, F401
from . import sales_twin_graph  # noqa: E402, F401
from . import sales_twin_strategy  # noqa: E402, F401
from . import sales_twin_learning  # noqa: E402, F401
from . import sales_twin_settings  # noqa: E402, F401
from . import sales_twin_agent  # noqa: E402, F401
from . import sales_twin_challenger  # noqa: E402, F401
from . import sales_twin_milestones  # noqa: E402, F401
from . import edition  # noqa: E402, F401  # @edition 扩展注册表存根
