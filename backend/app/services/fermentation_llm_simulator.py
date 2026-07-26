"""
LLM驱动的闭门发酵模拟器
按干系人职责/汇报线/影响力/管理层级推演多轮扩散互动，不基于时间天数
输出：故事化推演记录 + 态度变化 + 可采访
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from app import db
from app.models.database import (
    Project, Stakeholder, Relationship,
    FeedbackRecord, MeetingPlan, OpportunityTask, StateChangeLog
)
from app.api.sales_twin._helpers import _build_project_insight_summary
from app.utils.llm_client import LLMClient

logger = logging.getLogger(__name__)


class LLMFermentationSimulator:
    """LLM驱动的闭门发酵模拟器"""

    # 各阶段发酵推演重点（与 FermentationSimulator.STAGE_FERMENTATION_RULES.focus 保持一致）
    STAGE_FERMENTATION_FOCUS = {
        'suspect': '信息传播、关系网络影响、关键干系人态度变化。早期信息不对称强，应侧重信息沿汇报线/职责的扩散与消除',
        'identity': '信息传播、关系网络影响、关键干系人态度变化。侧重干系人角色识别与支持联盟建立的影响扩散',
        'define': '方案内部推广、异议处理效果、决策链共识形成。侧重方案价值认同的传播与异议化解',
        'confirm': '方案内部推广、异议处理效果、决策链共识形成。侧重商务条款影响与最后异议的处理传播',
        'closed_won': '合同条款影响、实施风险传播、未来合作意向。侧重长期关系维护与实施交接的风险传播',
        'closed_lost': '合同条款影响、实施风险传播、未来合作意向。侧重丢单原因的内部归因与未来合作铺垫',
    }

    def __init__(self):
        self._llm = None

    def _get_llm(self):
        if self._llm is None:
            self._llm = LLMClient()
        return self._llm

    def _get_stage_focus(self, sales_stage: str = None) -> str:
        """获取当前阶段的发酵推演重点（未知/未匹配阶段统一 fallback 到 suspect）"""
        if not sales_stage:
            return self.STAGE_FERMENTATION_FOCUS['suspect']
        return self.STAGE_FERMENTATION_FOCUS.get(
            sales_stage, self.STAGE_FERMENTATION_FOCUS['suspect']
        )

    def simulate(
        self,
        project_id: int,
        rounds: int = 3,
        related_task_ids: List[int] = None,
        related_feedback_ids: List[int] = None,
        related_materials: List[Dict] = None,
        days: int = None
    ) -> Dict[str, Any]:
        """运行LLM驱动的发酵模拟（按扩散轮次，非时间天数）

        Args:
            project_id: 项目ID
            rounds: 扩散轮次（按职责/汇报线/影响力/管理层级扩散讨论）
            related_task_ids: 关联待办ID
            related_feedback_ids: 关联反馈ID
            related_materials: 关联资料 [{name, type}]
            days: 已废弃，仅为向后兼容保留（如传入则映射为rounds）
        """
        # 向后兼容：旧调用方传入days
        if days is not None and rounds == 3:
            rounds = days
        project = Project.query.get_or_404(project_id)
        stakeholders = Stakeholder.query.filter_by(project_id=project_id).all()
        relationships = Relationship.query.filter_by(project_id=project_id).all()

        if not stakeholders:
            return {
                'project_id': project_id,
                'rounds': rounds,
                'narrative_history': [],
                'final_states': [],
                'conclusion': '无干系人数据，无法模拟',
                'trend': {'initial_avg': 0, 'final_avg': 0, 'change': 0}
            }

        # 收集上下文
        context = self._build_context(
            project, stakeholders, relationships,
            related_task_ids or [], related_feedback_ids or [],
            related_materials or []
        )

        # 初始状态快照
        initial_states = {
            s.id: {
                'id': s.id, 'name': s.name, 'position': s.position,
                'buyer_role': s.buyer_role,
                'support_level': float(s.support_level),
                'decision_power': float(s.decision_power),
                'urgency': float(s.urgency),
                'reports_to_id': s.reports_to_id,
                'level': s.level,
            }
            for s in stakeholders
        }

        narrative_history = [{
            'round': 0,
            'label': '会议结束时',
            'narrative': '本次会议/拜访结束，干系人各自带着会议中获得的信息回到岗位。接下来将基于自身职责、汇报线、影响力与管理层级进行私下互动扩散。',
            'state_changes': [],
            'states': self._format_states(initial_states)
        }]

        current_states = {k: dict(v) for k, v in initial_states.items()}

        # 逐轮扩散推演
        for r in range(1, rounds + 1):
            try:
                round_result = self._simulate_round(
                    project, stakeholders, relationships,
                    current_states, context, r, rounds
                )
                # 应用状态变化
                for change in round_result.get('state_changes', []):
                    sid = change.get('stakeholder_id')
                    if sid and sid in current_states:
                        new_support = change.get('new_support_level')
                        if new_support is not None:
                            current_states[sid]['support_level'] = float(new_support)
                        new_urgency = change.get('new_urgency')
                        if new_urgency is not None:
                            current_states[sid]['urgency'] = float(new_urgency)

                narrative_history.append({
                    'round': r,
                    'label': f'第{r}轮扩散',
                    'narrative': round_result.get('narrative', ''),
                    'interactions': round_result.get('interactions', []),
                    'state_changes': round_result.get('state_changes', []),
                    'states': self._format_states(current_states)
                })
            except Exception as e:
                logger.error(f"第{r}轮扩散模拟失败: {e}")
                narrative_history.append({
                    'round': r,
                    'label': f'第{r}轮扩散',
                    'narrative': f'（第{r}轮扩散异常：{str(e)[:100]}）',
                    'interactions': [],
                    'state_changes': [],
                    'states': self._format_states(current_states)
                })

        # 生成结论
        conclusion = self._generate_conclusion(narrative_history, initial_states, current_states)

        return {
            'project_id': project_id,
            'project_name': project.name,
            'rounds': rounds,
            'mode': 'narrative',
            'narrative_history': narrative_history,
            'final_states': self._format_states(current_states),
            'conclusion': conclusion,
            'trend': {
                'initial_avg': self._calc_avg_support(initial_states),
                'final_avg': self._calc_avg_support(current_states),
                'change': self._calc_avg_support(current_states) - self._calc_avg_support(initial_states)
            },
            'input_sources': {
                'related_task_ids': related_task_ids or [],
                'related_feedback_ids': related_feedback_ids or [],
                'related_materials': related_materials or [],
            }
        }

    def _build_context(
        self,
        project: Project,
        stakeholders: List[Stakeholder],
        relationships: List[Relationship],
        task_ids: List[int],
        feedback_ids: List[int],
        materials: List[Dict]
    ) -> Dict[str, Any]:
        """构建LLM上下文"""
        # 构建汇报关系映射
        sk_by_id = {s.id: s for s in stakeholders}
        # 干系人画像（含汇报对象/管理层级）
        sk_profiles = []
        for s in stakeholders:
            boss = sk_by_id.get(s.reports_to_id) if s.reports_to_id else None
            sk_profiles.append({
                'id': s.id,
                'name': s.name,
                'position': s.position or '未知',
                'level': s.level or '',
                'buyer_role': s.buyer_role or '未分类',
                'decision_power': s.decision_power,
                'support_level': s.support_level,
                'urgency': s.urgency,
                'responsibilities': s.responsibilities or '',
                'personal_agenda': s.personal_agenda or '',
                'reports_to': boss.name if boss else '',
                'reports_to_id': s.reports_to_id,
            })

        # 关系网络
        rel_list = []
        for r in relationships:
            src = next((s for s in stakeholders if s.id == r.source_id), None)
            tgt = next((s for s in stakeholders if s.id == r.target_id), None)
            if src and tgt:
                rel_list.append({
                    'source': src.name,
                    'target': tgt.name,
                    'type': r.relationship_type,
                    'influence_weight': r.influence_weight,
                })

        # 历史交流记录
        feedback_texts = []
        if feedback_ids:
            records = FeedbackRecord.query.filter(
                FeedbackRecord.id.in_(feedback_ids),
                FeedbackRecord.project_id == project.id
            ).all()
            for r in records:
                feedback_texts.append({
                    'date': r.created_at.strftime('%Y-%m-%d') if r.created_at else '',
                    'text': (r.feedback_text or '')[:300],
                    'summary': r.parse_summary or '',
                })

        # 待办事项
        task_list = []
        if task_ids:
            tasks = OpportunityTask.query.filter(
                OpportunityTask.id.in_(task_ids),
                OpportunityTask.project_id == project.id
            ).all()
            for t in tasks:
                task_list.append({
                    'title': t.title,
                    'status': t.status,
                    'stakeholder_name': next((s.name for s in stakeholders if s.id == t.stakeholder_id), ''),
                })

        return {
            'project': {
                'name': project.name,
                'customer_name': project.customer_name or '',
                'company_vision': project.company_vision or '',
                'business_pain_points': _build_project_insight_summary(project.id),
                'sales_stage': project.sales_stage or '',
            },
            'stakeholders': sk_profiles,
            'relationships': rel_list,
            'feedback_records': feedback_texts,
            'tasks': task_list,
            'materials': materials,
        }

    def _simulate_round(
        self,
        project: Project,
        stakeholders: List[Stakeholder],
        relationships: List[Relationship],
        current_states: Dict[int, Dict],
        context: Dict,
        round_idx: int,
        total_rounds: int
    ) -> Dict[str, Any]:
        """模拟单轮扩散互动（不基于时间，基于职责/汇报线/影响力/管理层级扩散）"""
        # 构建当前状态摘要（含汇报对象、管理层级）
        states_summary = []
        for sid, s in current_states.items():
            boss_name = s.get('reports_to_id')
            boss_label = ''
            if boss_name:
                boss = current_states.get(boss_name)
                boss_label = f"，汇报给={boss['name']}" if boss else ''
            level_label = f"，级别={s.get('level')}" if s.get('level') else ''
            states_summary.append(
                f"- {s['name']}（{s['position']}{level_label}{boss_label}，角色={s['buyer_role']}，"
                f"支持度={s['support_level']:.1f}/10，决策力={s['decision_power']:.0f}/10，"
                f"紧迫感={s['urgency']:.1f}/10）"
            )

        # 关系网络摘要
        rel_summary = []
        for r in context.get('relationships', []):
            rel_summary.append(
                f"- {r['source']} → {r['target']}（{r['type']}，影响力={r['influence_weight']}）"
            )

        # 历史交流摘要
        feedback_summary = []
        for f in context.get('feedback_records', []):
            feedback_summary.append(f"- [{f['date']}] {f['text'][:100]}")

        # 阶段感知上下文
        sales_stage = context.get('project', {}).get('sales_stage', '')
        stage_focus = self._get_stage_focus(sales_stage)

        prompt = f"""你是B2B销售资深顾问。请模拟会议结束后第{round_idx}轮（共{total_rounds}轮扩散）干系人之间的私下互动和态度演变。
注意：这不是按天推演，而是按"信息扩散轮次"推演。每一轮代表信息/影响力沿职责、汇报线、影响力、管理层级的一次扩散。

## 项目背景
- 项目：{context['project']['name']}
- 客户：{context['project']['customer_name']}
- 公司愿景：{context['project']['company_vision']}
- 业务痛点：{context['project']['business_pain_points']}

## 当前销售阶段与发酵重点
项目当前处于 **{sales_stage or '未知'}** 阶段，本轮发酵推演应聚焦：
{stage_focus}

## 当前干系人状态
{chr(10).join(states_summary)}

## 关系网络
{chr(10).join(rel_summary) if rel_summary else '（无显式关系）'}

## 会议交流记录（发酵起点）
{chr(10).join(feedback_summary) if feedback_summary else '（无历史交流记录）'}

## 关联待办
{chr(10).join([f"- {t['title']}（{t['status']}，{t['stakeholder_name']}）" for t in context.get('tasks', [])]) or '（无）'}

## 模拟要求
1. 基于每个干系人的角色（mobilizer推动者/blocker阻碍者/guide引导者/champion冠军/skeptic怀疑者/coach教练）、支持度、决策力、个人诉求、职责、管理层级和汇报线，推演本轮信息/影响力的扩散互动
2. 扩散逻辑（核心）：
   - 沿汇报线扩散：下属向上汇报、上级向下传达、平级间横向沟通
   - 沿职责扩散：相关职责的干系人会就项目议题进行专业讨论
   - 沿影响力扩散：高决策力的干系人会主动游说他人、被影响者会反馈态度
   - 沿管理层级扩散：高层决策经中层传达至执行层，执行层的反馈回流至高层
3. 角色行为：推动者会游说他人、阻碍者会散布疑虑、冠军会主动推进、怀疑者会犹豫观望、教练会提供内部信息、引导者会引荐资源
4. 态度变化要有因果：每次变化都源于本轮具体的互动事件
5. 本轮是第{round_idx}轮（共{total_rounds}轮），初期轮次侧重上下级与平级扩散，后期轮次侧重跨层级与跨部门扩散
6. **阶段对齐**：互动内容与态度变化应与当前阶段（{sales_stage or '未知'}）的发酵重点紧密对齐

## 输出格式（严格JSON）
{{
  "narrative": "本轮扩散的整体氛围叙事描述（100-200字，描述信息如何沿职责/汇报线/影响力/管理层级扩散）",
  "interactions": [
    {{
      "actor": "主动方干系人姓名",
      "action": "具体动作（如：向直接上级汇报/召集下属开会/横向联系平级/跨部门沟通）",
      "target": "被动方干系人姓名（可空）",
      "content": "互动内容摘要（50-100字）",
      "effect": "效果描述（如：对方态度软化/对方更加抵触/无明显变化）"
    }}
  ],
  "state_changes": [
    {{
      "stakeholder_id": 干系人ID,
      "stakeholder_name": "姓名",
      "old_support_level": 旧支持度,
      "new_support_level": 新支持度,
      "old_urgency": 旧紧迫感,
      "new_urgency": 新紧迫感,
      "reason": "变化原因（20-50字）"
    }}
  ]
}}

注意：
- state_changes只列出有变化的干系人，没变化的不列
- 支持度变化幅度合理（单轮变化通常不超过2分）
- interactions至少2条，最多5条
- 只输出JSON，不要其他内容"""

        try:
            llm = self._get_llm()
            result = llm.chat_json(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.6,
                max_tokens=2000
            )
            # 验证stakeholder_id
            valid_ids = set(current_states.keys())
            for change in result.get('state_changes', []):
                sid = change.get('stakeholder_id')
                if sid not in valid_ids:
                    # 尝试按name匹配
                    name = change.get('stakeholder_name', '')
                    for sk_id, sk in current_states.items():
                        if sk['name'] == name:
                            change['stakeholder_id'] = sk_id
                            break
            return result
        except Exception as e:
            logger.error(f"LLM推演第{round_idx}轮扩散失败: {e}")
            return {
                'narrative': f'第{round_idx}轮扩散进行中（LLM推演异常，使用降级模式）',
                'interactions': [],
                'state_changes': []
            }

    def interview(
        self,
        project_id: int,
        stakeholder_id: int,
        question: str,
        simulation_context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """采访干系人（基于模拟历史）"""
        stakeholder = Stakeholder.query.get_or_404(stakeholder_id)
        project = Project.query.get_or_404(project_id)

        # 构建干系人画像
        profile = f"""你是{stakeholder.name}，{stakeholder.position or ''}。
你的角色是{stakeholder.buyer_role or '未分类'}。
你的支持度={stakeholder.support_level}/10，决策力={stakeholder.decision_power}/10，紧迫感={stakeholder.urgency}/10。
你的职责：{stakeholder.responsibilities or '未知'}
你的个人诉求：{stakeholder.personal_agenda or '未知'}
"""

        # 模拟历史上下文
        history_str = ''
        if simulation_context and simulation_context.get('narrative_history'):
            history_str = '\n## 会议后的发酵经过\n'
            for h in simulation_context['narrative_history']:
                if h.get('narrative'):
                    history_str += f"\n### {h['label']}\n{h['narrative']}\n"
                for interaction in h.get('interactions', []):
                    history_str += f"- {interaction.get('actor', '')}{interaction.get('action', '')}"
                    if interaction.get('target'):
                        history_str += f"（针对{interaction['target']}）"
                    history_str += f"：{interaction.get('content', '')}\n"

        system_msg = (
            "你正在扮演一个真实人物接受采访。你的输出必须是该人物的第一人称口语回答本身，"
            "绝对禁止输出任何分析、推理、思考步骤、草稿、编号列表或元说明。"
            "不要出现『分析请求』『确定立场』『起草回答』『草稿』等字样。"
            "直接说出这个人物会说的那句话，就像在真实对话中一样。"
        )

        prompt = f"""{profile}

{history_str}

## 项目背景
项目：{project.name}
客户：{project.customer_name or ''}
公司愿景：{project.company_vision or ''}
业务痛点：{_build_project_insight_summary(project.id)}

## 采访要求
现在有人当面问你一个问题。请直接以{stakeholder.name}的身份，用第一人称口语回答。
- 只输出你说的那番话本身，不要输出任何思考过程、分析步骤、草稿或编号列表
- 不要出现"分析"、"理由"、"草稿"、"步骤"等元词汇
- 语气符合你的职位和角色，150字以内
- 回答必须是一段连贯的话，不是列表

问题：{question}

你的回答："""

        try:
            llm = self._get_llm()
            response = llm.chat(
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            # 后处理：剥离推理模型可能残留的CoT
            answer = self._strip_cot(response)
            return {
                'stakeholder_id': stakeholder_id,
                'stakeholder_name': stakeholder.name,
                'question': question,
                'answer': answer
            }
        except Exception as e:
            logger.error(f"采访失败: {e}")
            return {
                'stakeholder_id': stakeholder_id,
                'stakeholder_name': stakeholder.name,
                'question': question,
                'answer': f'（采访失败：{str(e)[:100]}）'
            }

    def _strip_cot(self, text: str) -> str:
        """剥离推理模型残留的Chain-of-Thought，只保留最终回答"""
        if not text or not isinstance(text, str):
            return text if isinstance(text, str) else str(text)

        original = text.strip()
        # 已移除 <think> 由 llm_client 处理，这里处理 markdown 式 CoT

        cot_markers = [
            '分析请求', '确定核心立场', '确定立场', '起草回答', '草稿',
            '思考步骤', '分析：', '理由：', '推理过程', '思维过程',
            'step 1', 'step 2', '步骤1', '步骤2',
        ]
        has_cot = any(m in original for m in cot_markers)

        if not has_cot:
            return original

        import re

        # 策略1：找最后一个"草稿N："后的内容
        draft_matches = list(re.finditer(r'\*{0,2}草稿\s*\d+\*{0,2}\s*[:：]', original))
        if draft_matches:
            last = draft_matches[-1]
            candidate = original[last.end():].strip()
            # 去掉列表前缀如 "* " 或 "- "
            candidate = re.sub(r'^[\*\-]\s+', '', candidate)
            candidate = candidate.strip('"\'""''「」""')
            # 去掉草稿自身的前缀标记如 *草稿1：*
            candidate = re.sub(r'^\*{0,2}草稿\s*\d+\*{0,2}\s*[:：]\s*', '', candidate).strip()
            candidate = re.sub(r'^[\*\-]\s+', '', candidate)
            candidate = candidate.strip('"\'""''「」""')
            if candidate and len(candidate) >= 8:
                return candidate

        # 策略2：找"最终回答"/"我的回答"/"回答："标记
        final_markers = ['最终回答', '我的回答', '最终：', '回答内容', '最终答案', '正式回答']
        for marker in final_markers:
            idx = original.rfind(marker)
            if idx >= 0:
                candidate = original[idx + len(marker):].strip()
                candidate = re.sub(r'^[:：]\s*', '', candidate)
                candidate = candidate.strip('"\'""''「」""')
                if candidate and len(candidate) >= 8:
                    return candidate

        # 策略3：按"数字. **标题**"分段，取最后一段
        sections = re.split(r'\n\d+\.\s*\*{0,2}[^\n]{1,40}\*{0,2}\s*\n', original)
        if len(sections) > 1:
            last_section = sections[-1].strip()
            # 去掉草稿前缀
            last_section = re.sub(r'^\*{0,2}草稿\s*\d+\*{0,2}\s*[:：]\s*', '', last_section).strip()
            last_section = last_section.strip('"\'""''「」""')
            if last_section and len(last_section) >= 8:
                return last_section

        # 策略4：找最后一个以"你的回答："或类似提示结尾后的内容
        tail_markers = ['你的回答：', '回答：', '答：']
        for marker in tail_markers:
            idx = original.rfind(marker)
            if idx >= 0:
                candidate = original[idx + len(marker):].strip()
                candidate = candidate.strip('"\'""''「」""')
                if candidate and len(candidate) >= 5:
                    return candidate

        # 无法可靠提取，返回原文
        logger.warning(f"采访回答CoT清理失败，返回原文: {original[:200]}")
        return original

    def _format_states(self, states: Dict[int, Dict]) -> List[Dict]:
        """格式化状态列表"""
        result = []
        for sid, s in sorted(states.items(), key=lambda x: x[1]['decision_power'], reverse=True):
            result.append({
                'id': s['id'],
                'name': s['name'],
                'position': s.get('position', ''),
                'buyer_role': s.get('buyer_role', ''),
                'support_level': round(s['support_level'], 1),
                'decision_power': round(s['decision_power'], 1),
                'urgency': round(s['urgency'], 1),
            })
        return result

    def _calc_avg_support(self, states: Dict[int, Dict]) -> float:
        """计算加权平均支持度"""
        if not states:
            return 0
        total = sum(s['support_level'] * s['decision_power'] for s in states.values())
        total_power = sum(s['decision_power'] for s in states.values())
        if total_power == 0:
            return 0
        return round(total / total_power, 2)

    def _generate_conclusion(
        self,
        history: List[Dict],
        initial_states: Dict,
        final_states: Dict
    ) -> str:
        """生成模拟结论"""
        initial_avg = self._calc_avg_support(initial_states)
        final_avg = self._calc_avg_support(final_states)
        change = final_avg - initial_avg

        parts = []

        if change > 1:
            parts.append(f"扩散期整体支持度上升（+{round(change, 1)}分），项目动能增强")
        elif change < -1:
            parts.append(f"扩散期整体支持度下降（{round(change, 1)}分），出现阻力信号")
        else:
            parts.append("扩散期整体支持度相对稳定")

        # 找出变化最大的干系人
        biggest_gainer = None
        biggest_gain = -999
        biggest_loser = None
        biggest_loss = 999

        for sid, final in final_states.items():
            initial = initial_states.get(sid, {})
            diff = final['support_level'] - initial.get('support_level', 0)
            if diff > biggest_gain:
                biggest_gain = diff
                biggest_gainer = final['name']
            if diff < biggest_loss:
                biggest_loss = diff
                biggest_loser = final['name']

        if biggest_gainer and biggest_gain > 0.5:
            parts.append(f"态度正向变化最大：{biggest_gainer}（+{round(biggest_gain, 1)}分）")
        if biggest_loser and biggest_loss < -0.5:
            parts.append(f"态度负向变化最大：{biggest_loser}（{round(biggest_loss, 1)}分）")

        # 统计互动数
        total_interactions = sum(len(h.get('interactions', [])) for h in history)
        parts.append(f"扩散期共发生{total_interactions}次私下互动")

        return '；'.join(parts) + '。'
