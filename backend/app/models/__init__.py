"""
数据模型模块
"""

# 显式 import SQLAlchemy 模型，确保 db.create_all() 能创建对应表
from .database import (
    ProjectStrategyItem, ProjectWhyContext, CompanyProfile, CompanyAttachment,
    AIRecommendationLog, AIRecommendationOutcome, LearningPattern,
    BlindSpotReport, AgentJobRun, CustomerIntelSnapshot,
)  # noqa: F401

__all__ = [
    'ProjectStrategyItem', 'ProjectWhyContext', 'CompanyProfile', 'CompanyAttachment',
    'AIRecommendationLog', 'AIRecommendationOutcome', 'LearningPattern',
    'BlindSpotReport', 'AgentJobRun', 'CustomerIntelSnapshot',
]

