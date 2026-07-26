"""
干系人自动生成服务
从网络调研结果中识别关键决策岗位，自动创建占位干系人
"""

import logging
from typing import Dict, Any, List

from app import db
from app.models.database import Project, Stakeholder

logger = logging.getLogger(__name__)


class StakeholderGenerator:
    """从调研结果自动生成干系人"""

    # 职位关键词到buyer_role的映射
    ROLE_KEYWORDS = {
        'champion': ['局长', '主任', '总经理', '总裁', 'CEO', '行长', '书记', '司长', '厅长'],
        'guide': ['副总', '副局', '副主', '助理', '办公室主任', '秘书', '采购', 'CFO', '财务'],
        'skeptic': ['总工程师', '总师', 'CTO', 'CIO', '技术', '架构', '研发', '信息中心'],
        'coach': ['顾问', '专家', '参事', '调研员'],
        'mobilizer': ['项目', '业务', '运营', '产品', '市场'],
    }

    # buyer_role的中文标签
    ROLE_LABELS = {
        'champion': '支持者/决策者',
        'guide': '向导/内部顾问',
        'skeptic': '技术评估者',
        'coach': '教练/专家',
        'mobilizer': '行动派/推动者',
        'blocker': '反对者',
    }

    def generate_from_research(
        self,
        project_id: int,
        organization: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        从调研结果的组织架构信息自动创建干系人

        Args:
            project_id: 项目ID
            organization: 调研返回的组织架构信息
                {
                    "departments": ["部门1", "部门2"],
                    "key_positions": ["局长", "副局长", "总工程师", ...],
                    "decision_chain": ["环节1", "环节2", ...]
                }

        Returns:
            {
                'created': list,    # 新创建的干系人
                'skipped': list,    # 跳过的（已存在）
                'total_created': int
            }
        """
        if not organization or not isinstance(organization, dict):
            return {'created': [], 'skipped': [], 'total_created': 0}

        key_positions = organization.get('key_positions', [])
        if not key_positions or not isinstance(key_positions, list):
            return {'created': [], 'skipped': [], 'total_created': 0}

        # 获取项目已有的干系人，避免重复创建
        existing = Stakeholder.query.filter_by(project_id=project_id).all()
        existing_positions = {s.position for s in existing if s.position}

        created = []
        skipped = []

        for position in key_positions:
            if not isinstance(position, str) or not position.strip():
                continue

            position = position.strip()

            # 去重：如果已有同职位的干系人，跳过
            if position in existing_positions:
                skipped.append(position)
                continue

            # 推断buyer_role
            buyer_role = self._infer_role(position)

            # 推断决策力（决策者高，副手中等，技术评估者中等偏高）
            decision_power = self._infer_decision_power(position, buyer_role)

            # 创建占位干系人
            stakeholder = Stakeholder(
                project_id=project_id,
                name=f'[待识别]{position}',
                position=position,
                buyer_role=buyer_role,
                decision_power=decision_power,
                support_level=5,   # 中立，待评估
                urgency=5,         # 中等，待评估
                status='pending',  # AI 生成默认"待识别"
                responsibilities=f'调研识别的关键决策岗位：{position}',
                personal_agenda=None
            )
            db.session.add(stakeholder)
            created.append({
                'name': stakeholder.name,
                'position': position,
                'buyer_role': buyer_role,
                'role_label': self.ROLE_LABELS.get(buyer_role, '未分类'),
                'decision_power': decision_power
            })
            existing_positions.add(position)  # 避免本次循环内重复

        db.session.commit()

        logger.info(f"项目 {project_id} 从调研结果创建了 {len(created)} 个干系人，跳过 {len(skipped)} 个")

        return {
            'created': created,
            'skipped': skipped,
            'total_created': len(created)
        }

    def _infer_role(self, position: str) -> str:
        """根据职位关键词推断买方角色"""
        position_lower = position.lower()
        for role, keywords in self.ROLE_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in position_lower:
                    return role
        # 默认归为向导
        return 'guide'

    def _infer_decision_power(self, position: str, buyer_role: str) -> int:
        """根据职位和角色推断决策力"""
        # 一把手高决策力
        first_boss_keywords = ['局长', '主任', '总经理', '总裁', 'CEO', '行长', '书记', '司长', '厅长']
        for kw in first_boss_keywords:
            if kw in position and '副' not in position:
                return 9

        # 副手中等偏高
        if '副' in position:
            return 7

        # 技术负责人中等偏高
        if buyer_role == 'skeptic':
            return 7

        # 采购/财务中等
        if buyer_role == 'guide':
            return 6

        # 其他中等
        return 5
