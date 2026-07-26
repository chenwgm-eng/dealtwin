"""因子提取服务 — 提取项目横截面特征向量"""
from datetime import datetime, timedelta

from app import db
from app.models.database import (
    Project, Stakeholder, Relationship, StateChangeLog,
    ProjectStrategyItem, StageDeliverable,
)


class FactorExtractor:
    """提取项目的量化因子向量"""

    def extract(self, project_id: int) -> dict:
        """返回 {'momentum': 0.0-1.0, 'coverage': 0.0-1.0, 'completeness': 0.0-1.0, 'pain': 0.0-1.0, 'stage': '...'}"""
        return {
            'momentum': self._momentum_factor(project_id),
            'coverage': self._coverage_factor(project_id),
            'completeness': self._completeness_factor(project_id),
            'pain': self._pain_factor(project_id),
            'stage': self._stage_factor(project_id),
        }

    def _momentum_factor(self, project_id):
        """近14天 StateChangeLog 记录数归一化（最多5条=1.0）"""
        cutoff = datetime.utcnow() - timedelta(days=14)
        count = StateChangeLog.query.filter(
            StateChangeLog.project_id == project_id,
            StateChangeLog.created_at >= cutoff
        ).count()
        return min(count / 5.0, 1.0)

    def _coverage_factor(self, project_id):
        """已建联干系人的 decision_power 总和占所有干系人 decision_power 总和的比例"""
        stakeholders = Stakeholder.query.filter_by(project_id=project_id).all()
        if not stakeholders:
            return 0.0
        total_power = sum(s.decision_power or 0 for s in stakeholders)
        if total_power == 0:
            return 0.0
        # "已建联" = 有关系连线的干系人
        rels = Relationship.query.filter_by(project_id=project_id).all()
        connected_ids = set()
        for r in rels:
            connected_ids.add(r.source_id)
            connected_ids.add(r.target_id)
        connected_power = sum(s.decision_power or 0 for s in stakeholders if s.id in connected_ids)
        return min(connected_power / total_power, 1.0)

    def _completeness_factor(self, project_id):
        """当前阶段交付物完成度"""
        project = Project.query.get(project_id)
        if not project:
            return 0.0
        stage = project.sales_stage
        if not stage:
            return 0.0
        deliverables = StageDeliverable.query.filter_by(project_id=project_id, stage=stage).all()
        if not deliverables:
            return 0.0
        confirmed = sum(1 for d in deliverables if d.is_completed)
        return confirmed / len(deliverables) if deliverables else 0.0

    def _pain_factor(self, project_id):
        """业务痛点严重度 — 基于 pain_point 类型 StrategyItem 数量归一化（最多3条=1.0）"""
        count = ProjectStrategyItem.query.filter_by(
            project_id=project_id, item_type='pain_point'
        ).count()
        return min(count / 3.0, 1.0)

    def _stage_factor(self, project_id):
        project = Project.query.get(project_id)
        return project.sales_stage if project else None
