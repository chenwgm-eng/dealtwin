"""
Challenger 商业指导话术生成器
基于 Challenger Sale Vision Setting 七步法，结合项目上下文与目标干系人画像，
用LLM生成结构化商业指导话术（Commercial Teaching）
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from app import db
from app.models.database import (
    Project, Stakeholder, ChallengerTeaching,
    ProjectStrategyItem, ProjectWhyContext,
)
from app.api.sales_twin._helpers import _enum_str
from app.utils.llm_client import LLMClient

logger = logging.getLogger(__name__)

# Challenger 社交风格对应的定制沟通策略提示（tailoring_note 生成依据）
SOCIAL_STYLE_GUIDES = {
    'analytical': '分析型：提供充分数据与逻辑论证，准备细节验证材料，避免夸大其词',
    'driver': '推动型：直奔主题，强调效率、结果与时间节点，用简短有力的结论',
    'amiable': '亲和型：先建立信任与关系，强调团队支持与低风险实施路径，争取情感认可',
    'expressive': '表达型：认可其想法与愿景，用故事和愿景画面激发共鸣，让其参与共创',
}

# teaching_content 中的文本字段（归一化时补齐）
CONTENT_TEXT_FIELDS = (
    'warmer', 'reframe', 'rational_drowning', 'emotional_impact',
    'new_way', 'our_solution', 'call_to_action', 'tailoring_note',
)


class ChallengerTeachingGenerator:
    """Challenger 商业指导话术生成器"""

    def __init__(self):
        self._llm = None

    def _get_llm(self):
        if self._llm is None:
            self._llm = LLMClient()
        return self._llm

    def generate(
        self,
        project_id: int,
        stakeholder_id: Optional[int] = None,
        name: Optional[str] = None
    ) -> Dict[str, Any]:
        """生成商业指导话术（同步调用LLM）

        Args:
            project_id: 项目ID
            stakeholder_id: 目标干系人ID（可空=面向采购群体通用）
            name: 话术名称（为空时自动生成"商业指导-YYYYMMDD-HHMM"）

        Returns:
            {'success': True, 'teaching': {...}}

        Raises:
            RuntimeError: LLM 不可用或输出解析失败（由 API 层捕获返回 502）
        """
        project = Project.query.get_or_404(project_id)
        target = None
        if stakeholder_id:
            # 归属校验：目标干系人必须属于当前项目，跨项目引用返回 404
            target = Stakeholder.query.filter_by(
                id=stakeholder_id, project_id=project_id
            ).first_or_404()
        stakeholders = Stakeholder.query.filter_by(project_id=project_id).all()

        # 构建LLM提示词
        prompt = self._build_prompt(project, stakeholders, target)

        # 调用LLM生成话术
        result = self._call_llm(prompt)

        # 归一化输出结构（补齐缺失字段、校正类型）
        content = self._normalize_content(result)

        # 话术名称：未提供时自动生成（精确到秒避免重名）
        final_name = name or f"商业指导-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        # 保存到数据库
        teaching = ChallengerTeaching(
            project_id=project_id,
            stakeholder_id=target.id if target else None,
            name=final_name,
            teaching_content=json.dumps(content, ensure_ascii=False),
            status='generated'
        )
        db.session.add(teaching)
        db.session.commit()

        return {
            'success': True,
            'teaching': self.to_dict(teaching)
        }

    def _call_llm(self, prompt: str) -> Dict[str, Any]:
        """调用LLM并解析JSON输出（容错：正则提取JSON块，见 LLMClient.chat_json）

        LLM 不可用或解析失败时抛 RuntimeError（中文消息）。
        独立成方法便于测试 monkeypatch。
        """
        try:
            llm = self._get_llm()
        except Exception as e:
            logger.error(f"LLM客户端初始化失败: {e}")
            raise RuntimeError(f"LLM服务不可用：{e}")
        try:
            result = llm.chat_json(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                max_tokens=3500
            )
        except Exception as e:
            logger.error(f"LLM生成商业指导话术失败: {e}")
            raise RuntimeError(f"LLM生成商业指导话术失败：{e}")
        if not result or not isinstance(result, dict):
            raise RuntimeError("LLM返回内容解析失败，未获得有效的JSON结构")
        return result

    def _normalize_content(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """归一化LLM输出结构：补齐缺失字段、校正字段类型"""
        content = dict(result)
        # 文本字段统一为字符串
        for key in CONTENT_TEXT_FIELDS:
            val = content.get(key)
            content[key] = val if isinstance(val, str) else (str(val) if val else '')
        # powerful_ask 四要素
        powerful_ask = content.get('powerful_ask')
        if not isinstance(powerful_ask, dict):
            powerful_ask = {}
        content['powerful_ask'] = {
            k: (str(powerful_ask.get(k)) if powerful_ask.get(k) else '')
            for k in ('why', 'when', 'who', 'what')
        }
        # validation_factors 最多 3 条字符串
        factors = content.get('validation_factors')
        if not isinstance(factors, list):
            factors = [factors] if factors else []
        content['validation_factors'] = [str(f) for f in factors][:3]
        # 白名单过滤：丢弃契约外字段，保持存储结构严格
        allowed = set(CONTENT_TEXT_FIELDS) | {'powerful_ask', 'validation_factors'}
        return {k: v for k, v in content.items() if k in allowed}

    def _build_prompt(
        self,
        project: Project,
        stakeholders: List[Stakeholder],
        target: Optional[Stakeholder]
    ) -> str:
        """构建LLM提示词"""
        # 3-3-3 战略项（行业趋势/当前措施/痛点）
        strategy_labels = {
            'industry_trend': '行业趋势',
            'current_measure': '当前措施',
            'pain_point': '业务痛点',
        }
        strategy_lines = []
        for item_type, label in strategy_labels.items():
            items = (
                ProjectStrategyItem.query
                .filter_by(project_id=project.id, item_type=item_type)
                .order_by(ProjectStrategyItem.sort_order.asc())
                .all()
            )
            for item in items:
                strategy_lines.append(f'- [{label}] {item.name}：{item.description or ""}')
        strategy_str = '\n'.join(strategy_lines) if strategy_lines else '未录入'

        # 三个WHY（为什么改变/为什么是现在/为什么是我们）
        why_labels = {'why': 'Why Change', 'why_now': 'Why Now', 'why_us': 'Why Us'}
        why_lines = []
        why_contexts = ProjectWhyContext.query.filter_by(project_id=project.id).all()
        for ctx in why_contexts:
            label = why_labels.get(ctx.context_type, ctx.context_type)
            why_lines.append(f'- {label}：{ctx.context_text or ""}')
        why_str = '\n'.join(why_lines) if why_lines else '未录入'

        # 干系人地图（简述）
        sk_lines = []
        for s in stakeholders:
            sk_lines.append(
                f"- {s.name}（{s.position or '未知职位'}，项目角色:{_enum_str(s.project_role) or '未设定'}，"
                f"角色类型:{_enum_str(s.buyer_role) or '未分类'}，社交风格:{_enum_str(s.social_style) or '未识别'}，"
                f"支持度{s.support_level}/10，决策力{s.decision_power}/10，紧迫感{s.urgency}/10，"
                f"个人诉求:{s.personal_agenda or '未知'}）"
            )
        stakeholders_str = '\n'.join(sk_lines) if sk_lines else '暂无干系人'

        # 目标干系人详情与定制提示
        if target:
            social_style = _enum_str(target.social_style)
            style_guide = SOCIAL_STYLE_GUIDES.get(
                social_style, '未识别社交风格：给出面向采购群体的通用定制建议'
            )
            target_section = f"""## 目标干系人（本话术的主要沟通对象）
- 姓名: {target.name}
- 职位: {target.position or '未知'}
- 项目角色: {_enum_str(target.project_role) or '未设定'}
- 角色类型: {_enum_str(target.buyer_role) or '未分类'}
- 社交风格: {social_style or '未识别'}
- 支持度: {target.support_level}/10，决策力: {target.decision_power}/10，紧迫感: {target.urgency}/10
- 个人诉求: {target.personal_agenda or '未知'}

## 定制沟通策略提示
{style_guide}"""
        else:
            target_section = """## 目标干系人
未指定（面向采购群体通用）

## 定制沟通策略提示
未指定目标干系人：给出面向采购群体的通用定制建议"""

        return f"""你是一位精通 Challenger Sale（挑战式销售）方法论的资深B2B销售教练。请基于以下项目上下文，生成一套"商业指导话术"（Commercial Teaching），采用 Vision Setting 七步对话模型。

## 项目信息
- 项目名称: {project.name}
- 客户名称: {project.customer_name or '未知'}
- 销售阶段: {project.sales_stage}
- 预算: {project.budget if project.budget is not None else '未知'}
- 客户背景与需求: {project.customer_background or '未录入'}
- 价值主张: {project.value_proposition or '未录入'}
- 竞争分析: {project.competitive_analysis or '未录入'}

## 客户3-3-3战略要素
{strategy_str}

## 三个WHY
{why_str}

## 干系人地图
{stakeholders_str}

{target_section}

## 输出格式（严格JSON）
{{
  "warmer": "热身：建立融洽关系并说明来意的开场话术",
  "reframe": "重构：指出客户认知盲区，把对话从客户自认为的问题重构到真正的问题上",
  "rational_drowning": "理性冲击：量化不改变的业务指标损失（金额/效率/风险）",
  "emotional_impact": "感性冲击：故事化场景，让客户对问题感同身受",
  "new_way": "新方法：客户应采用的全新解决思路（先不谈我方产品）",
  "our_solution": "我方方案：自然引回我方方案如何支撑新方法",
  "call_to_action": "行动号召：本次沟通希望客户承诺的下一步",
  "powerful_ask": {{
    "why": "为什么提出该请求",
    "when": "何时提出",
    "who": "向谁提出",
    "what": "具体请求什么（必须明确可执行）"
  }},
  "validation_factors": ["可验证的客户认可信号1", "可验证的客户认可信号2", "可验证的客户认可信号3"],
  "tailoring_note": "针对目标干系人社交风格与采购角色的定制沟通建议"
}}

要求：
1. reframe 必须出其不意——揭示客户未意识到的问题，且能自然引回我方方案
2. rational_drowning 要给出具体的业务指标损失量化，不要泛泛而谈
3. emotional_impact 用故事化场景描述（某角色在某情境下的困境），让客户产生情绪共鸣
4. tailoring_note 必须按上方"定制沟通策略提示"和干系人采购角色定制
5. 话术具体可执行，禁止空话套话
6. 语言为中文，只输出JSON，不要输出其他内容。"""

    def get_list(self, project_id: int) -> Dict[str, Any]:
        """获取项目的所有商业指导话术（时间倒序）"""
        teachings = ChallengerTeaching.query.filter_by(project_id=project_id).order_by(
            ChallengerTeaching.created_at.desc()
        ).all()
        return {
            'teachings': [self.to_dict(t) for t in teachings]
        }

    def get(self, teaching_id: int) -> Dict[str, Any]:
        """获取单个商业指导话术"""
        teaching = ChallengerTeaching.query.get_or_404(teaching_id)
        return {
            'success': True,
            'teaching': self.to_dict(teaching)
        }

    def update(self, teaching_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """更新商业指导话术（允许改 name 和 teaching_content 内各字段，合并式更新）

        Raises:
            ValueError: name 或 teaching_content 类型非法（由 API 层捕获返回 400）
        """
        teaching = ChallengerTeaching.query.get_or_404(teaching_id)

        if 'name' in data and data['name']:
            if not isinstance(data['name'], str) or len(data['name']) > 200:
                raise ValueError('name 必须为不超过 200 字符的字符串')
            teaching.name = data['name']
        if 'teaching_content' in data:
            if not isinstance(data['teaching_content'], dict):
                raise ValueError('teaching_content 必须为对象')
            # 合并更新 teaching_content 内各字段（未提交的字段保持原值）
            try:
                content = json.loads(teaching.teaching_content) if teaching.teaching_content else {}
            except (json.JSONDecodeError, TypeError):
                content = {}
            content.update(data['teaching_content'])
            # 与生成路径一致：归一化结构，防止脏字段/错误类型入库
            content = self._normalize_content(content)
            teaching.teaching_content = json.dumps(content, ensure_ascii=False)

        teaching.updated_at = datetime.utcnow()
        db.session.commit()

        return {
            'success': True,
            'teaching': self.to_dict(teaching)
        }

    def delete(self, teaching_id: int):
        """删除商业指导话术"""
        teaching = ChallengerTeaching.query.get_or_404(teaching_id)
        db.session.delete(teaching)
        db.session.commit()

    def to_dict(self, teaching: ChallengerTeaching) -> Dict:
        """转字典（teaching_content 解析为对象）"""
        try:
            content = json.loads(teaching.teaching_content) if teaching.teaching_content else None
        except (json.JSONDecodeError, TypeError):
            content = None
        stakeholder = Stakeholder.query.get(teaching.stakeholder_id) if teaching.stakeholder_id else None
        return {
            'id': teaching.id,
            'project_id': teaching.project_id,
            'stakeholder_id': teaching.stakeholder_id,
            'stakeholder_name': stakeholder.name if stakeholder else '',
            'name': teaching.name,
            'teaching_content': content,
            'status': teaching.status,
            'created_at': teaching.created_at.isoformat() if teaching.created_at else None,
            'updated_at': teaching.updated_at.isoformat() if teaching.updated_at else None
        }
