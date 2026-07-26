"""多级反馈追踪器 — 监听系统事件，更新推荐结果"""
import logging
from datetime import datetime, timedelta

from app import db
from app.models.database import AIRecommendationLog, AIRecommendationOutcome

logger = logging.getLogger(__name__)


class OutcomeTracker:
    """追踪 AI 推荐的多级反馈"""

    def record_l1_adoption(self, recommendation_id, adopted=True, reject_reason=None, task_id=None):
        """L1: 采纳/拒绝反馈"""
        log = AIRecommendationLog.query.get(recommendation_id)
        if not log:
            return
        outcome = AIRecommendationOutcome.query.filter_by(recommendation_id=recommendation_id).first()
        if not outcome:
            outcome = AIRecommendationOutcome(recommendation_id=recommendation_id)
            db.session.add(outcome)
        outcome.is_adopted = adopted
        if not adopted and reject_reason:
            outcome.reject_reason = reject_reason
        if adopted and task_id:
            outcome.adopted_task_id = task_id
        db.session.commit()

    def update_l2_execution(self, task_id, execution_result='success'):
        """L2: 任务执行完成反馈 — 通过 adopted_task_id 关联"""
        outcome = AIRecommendationOutcome.query.filter_by(adopted_task_id=task_id).first()
        if not outcome:
            return
        outcome.is_executed = True
        outcome.execution_result = execution_result
        db.session.commit()

    def update_l3_stage_advance(self, project_id):
        """L3: 阶段推进反馈 — 检查近7天采纳的推荐是否触发了阶段推进"""
        cutoff = datetime.utcnow() - timedelta(days=7)
        outcomes = AIRecommendationOutcome.query.join(AIRecommendationLog).filter(
            AIRecommendationLog.project_id == project_id,
            AIRecommendationOutcome.is_adopted == True,
            AIRecommendationOutcome.scored_at >= cutoff
        ).all()
        for outcome in outcomes:
            outcome.triggered_stage_advance = True
        db.session.commit()

    def update_l4_final(self, project_id, is_win):
        """L4: 终局反馈 — 项目赢单/丢单时调用"""
        outcomes = AIRecommendationOutcome.query.join(AIRecommendationLog).filter(
            AIRecommendationLog.project_id == project_id
        ).all()
        for outcome in outcomes:
            outcome.final_win = is_win
        db.session.commit()
