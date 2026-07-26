"""
Next Best Action推荐服务
基于图谱热力值计算，生成下一步行动推荐
"""

import json
import logging
import random
from typing import List, Dict, Any

from app import db
from app.models.database import Project, Stakeholder, Relationship, OpportunityTask
from app.api.sales_twin._helpers import _build_project_insight_summary
from .blind_spot_detector import BlindSpotDetector
from .stakeholder_history import build_stakeholder_history_text
from ..utils.llm_client import LLMClient

logger = logging.getLogger(__name__)


class ActionRecommender:
    """行动推荐器"""

    def __init__(self):
        self.blind_spot_detector = BlindSpotDetector()
        self.llm_client = None  # 延迟初始化，避免无LLM配置时启动失败

    # 严重度到优先级(P1-P4)的映射
    SEVERITY_TO_PRIORITY = {
        'critical': 1,
        'high': 2,
        'medium': 3,
        'low': 4
    }

    # 严重度到基础 priority_score 的映射
    SEVERITY_TO_SCORE = {
        'critical': 100,
        'high': 80,
        'medium': 60,
        'low': 40
    }

    def _get_llm(self):
        """延迟初始化LLM客户端"""
        if self.llm_client is None:
            self.llm_client = LLMClient()
        return self.llm_client

    def recommend_actions(self, project_id: int) -> Dict[str, Any]:
        """生成下一步行动推荐"""
        project = Project.query.get_or_404(project_id)

        stakeholders = Stakeholder.query.filter_by(project_id=project_id).all()
        relationships = Relationship.query.filter_by(project_id=project_id).all()
        # 获取尚未完成/取消的待办事项，避免生成重复行动建议
        active_tasks = OpportunityTask.query.filter_by(project_id=project_id).filter(
            OpportunityTask.status.in_(['pending', 'in_progress'])
        ).order_by(OpportunityTask.created_at.desc()).all()

        blind_spots = self.blind_spot_detector.scan_project(project_id)

        actions = []

        # 1. 盲区行动（基于LLM分析的findings生成）
        actions.extend(self._generate_blind_spot_actions(blind_spots))

        # 2. 干系人策略（LLM生成，结合职位/诉求/角色定制，并参考已有待办避免重复）
        llm_actions = self._generate_llm_stakeholder_actions(
            project, stakeholders, relationships, active_tasks
        )
        if llm_actions:
            actions.extend(llm_actions)
        else:
            # LLM失败时退回规则生成
            actions.extend(self._generate_stakeholder_actions(stakeholders))

        # 3. 关系网络行动（规则生成）
        actions.extend(self._generate_relationship_actions(stakeholders, relationships))

        # 4. 基于已有待办过滤重复行动建议（标题相似度+目标干系人+action_type）
        if active_tasks:
            actions = self._dedupe_against_tasks(actions, active_tasks)

        # 为所有 action 补齐 priority 字段（前端按 P1/P2/P3/P4 渲染）
        for action in actions:
            if 'priority' not in action:
                action['priority'] = self._score_to_priority(action.get('priority_score', 0))

        actions.sort(key=lambda x: x['priority_score'], reverse=True)

        top_actions = actions[:10]

        # --- 自进化引擎：日志落库 ---
        try:
            top_actions = self._log_recommendations(project_id, top_actions)
        except Exception as e:
            logger.warning(f"自进化引擎日志落库失败，跳过: {e}")

        return {
            'project_id': project_id,
            'project_name': project.name,
            'total_actions': len(actions),
            # 兼容字段：保留 actions 给老调用方
            'actions': top_actions,
            # 前端期望字段
            'recommended_actions': top_actions
        }

    def _log_recommendations(self, project_id: int, top_actions: List[Dict]) -> List[Dict]:
        """将推荐落库到 AIRecommendationLog，并注入 recommendation_id；E&E 标记探索/利用"""
        from .factor_extractor import FactorExtractor
        from app.models.database import AIRecommendationLog, LearningPattern

        factors = FactorExtractor().extract(project_id)

        # E&E: 检查是否有 approved patterns 可匹配
        approved_patterns = LearningPattern.query.filter_by(status='approved').all()

        logged_actions = []
        for action in top_actions:
            # 判断是否为探索：LLM 来源有 20% 概率被标记为探索
            is_exploration = action.get('source') == 'llm' and random.random() < 0.20

            # 匹配 pattern（简单实现：按因子阈值匹配）
            matched_pattern_id = None
            if not is_exploration and approved_patterns:
                for p in approved_patterns:
                    try:
                        conditions = json.loads(p.trigger_conditions_json or '{}')
                        if self._match_factor_conditions(factors, conditions):
                            matched_pattern_id = p.id
                            break
                    except (ValueError, TypeError):
                        continue

            # 计算置信度
            confidence = action.get('priority_score', 70) / 100.0

            log_entry = AIRecommendationLog(
                project_id=project_id,
                rec_type='next_best_action',
                source_service=action.get('source', 'unknown'),
                rec_text=action.get('title', ''),
                structured_payload=json.dumps(action, ensure_ascii=False, default=str),
                momentum_factor=factors['momentum'],
                coverage_factor=factors['coverage'],
                completeness_factor=factors['completeness'],
                pain_factor=factors['pain'],
                stage_at_generation=factors['stage'],
                is_exploration=is_exploration,
                confidence_score=confidence,
                pattern_id=matched_pattern_id
            )
            db.session.add(log_entry)
            db.session.flush()  # 获取 log_entry.id

            # 给 action 注入 recommendation_id
            action['recommendation_id'] = log_entry.id
            logged_actions.append(action)

        db.session.commit()
        return logged_actions

    def _match_factor_conditions(self, factors, conditions):
        """检查因子是否满足 pattern 的触发条件"""
        for key, threshold in conditions.items():
            factor_key = key.replace('_factor', '')
            if factor_key in factors and isinstance(threshold, (int, float)):
                if factors[factor_key] < threshold:
                    return False
        return True

    def _dedupe_against_tasks(self, actions: List[Dict], active_tasks: List[OpportunityTask]) -> List[Dict]:
        """过滤与已有待办事项重复的行动建议
        判定规则：目标干系人相同 + (action_type相同 或 标题字符相似度>0.6)
        """
        def _normalize(s):
            return ''.join(c for c in (s or '').lower() if c.isalnum())

        def _title_sim(a, b):
            a, b = _normalize(a), _normalize(b)
            if not a or not b:
                return 0.0
            if a == b:
                return 1.0
            # 简易Jaccard相似度（按2-gram）
            sa = set(a[i:i+2] for i in range(len(a)-1)) if len(a) > 1 else {a}
            sb = set(b[i:i+2] for i in range(len(b)-1)) if len(b) > 1 else {b}
            if not sa or not sb:
                return 1.0 if a == b else 0.0
            return len(sa & sb) / len(sa | sb)

        # 解析task的source_action以获取action_type和target_stakeholder
        task_signatures = []
        for t in active_tasks:
            sig = {'title': t.title, 'action_type': None, 'target': None}
            if t.source_action:
                try:
                    sa = json.loads(t.source_action)
                    sig['action_type'] = sa.get('action_type')
                    sig['target'] = sa.get('target_stakeholder')
                except (json.JSONDecodeError, TypeError):
                    pass
            # 若无source_action信息，使用task.task_type反推
            if not sig['action_type']:
                sig['action_type'] = t.task_type
            # 若无target，从stakeholder_id查
            if not sig['target'] and t.stakeholder_id:
                sk = Stakeholder.query.get(t.stakeholder_id)
                if sk:
                    sig['target'] = sk.name
            task_signatures.append(sig)

        filtered = []
        for action in actions:
            a_target = action.get('target_stakeholder') or ''
            a_type = action.get('action_type') or ''
            a_title = action.get('title') or ''
            is_dup = False
            for sig in task_signatures:
                same_target = a_target and sig['target'] and a_target == sig['target']
                same_type = a_type and sig['action_type'] and a_type == sig['action_type']
                title_sim = _title_sim(a_title, sig['title'])
                # 重复判定：目标相同且（类型相同 或 标题相似度高）
                if same_target and (same_type or title_sim >= 0.6):
                    is_dup = True
                    break
                # 标题高度相似也视为重复（无论目标是否相同）
                if title_sim >= 0.8:
                    is_dup = True
                    break
            if not is_dup:
                filtered.append(action)
        return filtered

    def _generate_llm_stakeholder_actions(
        self,
        project: Project,
        stakeholders: List[Stakeholder],
        relationships: List[Relationship],
        active_tasks: List[OpportunityTask] = None
    ) -> List[Dict]:
        """用LLM基于干系人完整信息生成针对性策略（非套话模板，阶段感知）"""
        if not stakeholders:
            return []

        try:
            llm = self._get_llm()

            # 构建干系人画像 + 历史互动摘要
            buyer_role_labels = {
                'mobilizer': '行动派/推动者', 'blocker': '反对者',
                'guide': '向导/内部顾问', 'champion': '支持者/倡导者',
                'skeptic': '怀疑者', 'coach': '教练/导师'
            }
            sk_lines = []
            history_lines = []
            for s in stakeholders:
                role_label = buyer_role_labels.get(s.buyer_role, s.buyer_role or '未分类')
                line = f"- 姓名: {s.name}"
                if s.position:
                    line += f" | 职位: {s.position}"
                line += f" | 采购角色: {role_label}"
                line += f" | 决策力: {s.decision_power}/10 | 支持度: {s.support_level}/10 | 紧迫感: {s.urgency}/10"
                if s.responsibilities:
                    line += f" | 职责: {s.responsibilities}"
                if s.personal_agenda:
                    line += f" | 个人诉求: {s.personal_agenda}"
                sk_lines.append(line)

                # 聚合该干系人的历史互动记录（精简模式，控制token）
                try:
                    history_text = build_stakeholder_history_text(
                        s.id, max_state_logs=3, max_tasks=4, max_plans=1, max_feedbacks=2
                    )
                    if history_text:
                        history_lines.append(f'#### {s.name}\n{history_text}')
                except Exception as e:
                    logger.warning(f"获取干系人{s.id}历史记录失败: {e}")

            stakeholder_profile = '\n'.join(sk_lines)

            # 历史互动记录（如果有）
            history_section = ''
            if history_lines:
                history_section = f"""

## 干系人历史互动记录（避免重复已完成的工作，保持推进连续性）
{chr(10).join(history_lines)}
"""

            # 已安排的待办事项（用于避免重复推荐）
            active_tasks_section = ''
            if active_tasks:
                sk_map = {s.id: s.name for s in stakeholders}
                task_lines = []
                for t in active_tasks:
                    target_name = sk_map.get(t.stakeholder_id, '通用')
                    line = f"- [待办] {t.title}"
                    if t.description:
                        line += f"（{t.description[:80]}）"
                    line += f" | 目标: {target_name} | 优先级: {t.priority}"
                    if t.due_date:
                        line += f" | 截止: {t.due_date.strftime('%Y-%m-%d')}"
                    task_lines.append(line)
                active_tasks_section = f"""

## 已安排的待办事项（**严禁**推荐与下列待办重复或高度雷同的行动）
{chr(10).join(task_lines)}
"""

            # 构建关系网络
            rel_lines = []
            sk_map = {s.id: s.name for s in stakeholders}
            rel_type_labels = {
                'direct_report': '直接汇报', 'peer': '同级', 'allies': '盟友',
                'conflict': '冲突', 'mentor': '导师', 'friend': '朋友'
            }
            for r in relationships:
                src = sk_map.get(r.source_id, f'#{r.source_id}')
                tgt = sk_map.get(r.target_id, f'#{r.target_id}')
                rel = rel_type_labels.get(r.relationship_type, r.relationship_type)
                rel_lines.append(f"- {src} → {tgt}: {rel}")
            rel_profile = '\n'.join(rel_lines) if rel_lines else '（暂无已知关系）'

            # 项目上下文
            proj_context_parts = []
            if project.customer_name:
                proj_context_parts.append(f"客户: {project.customer_name}")
            if project.industry:
                proj_context_parts.append(f"行业: {project.industry}")
            pain_points_summary = _build_project_insight_summary(project.id)
            if pain_points_summary:
                proj_context_parts.append(f"业务痛点: {pain_points_summary[:200]}")
            if project.company_vision:
                proj_context_parts.append(f"公司战略: {project.company_vision[:200]}")
            proj_context = '\n'.join(proj_context_parts) if proj_context_parts else '（无项目上下文）'

            # 阶段感知上下文
            stage_guidance = self._get_stage_action_guidance(project.sales_stage)

            prompt = f"""你是一位资深B2B销售策略顾问。请基于以下项目背景和干系人画像，为每个干系人生成具体、可执行、个性化的推进策略。

## 项目背景
{proj_context}

## 当前销售阶段：{project.sales_stage or '未知'}

{stage_guidance}

## 干系人画像
{stakeholder_profile}

## 干系人关系网络
{rel_profile}
{history_section}{active_tasks_section}
## 任务
为每个干系人生成1条**最关键**的下一步推进策略。要求：
1. **具体到该干系人**：结合其职位、个人诉求、采购角色、支持度/决策力/紧迫感，不能是通用套话
2. **可执行**：明确说明"做什么、怎么做、用什么材料、找谁配合"
3. **有理由**：说明为什么对这个干系人采用这个策略（基于他的诉求和状态）
4. **差异化**：不同角色、不同支持度的干系人，策略必须不同
   - 高支持高决策力(champion/支持者)：深化结盟，让其成为内部倡导者，提供弹药让他帮你说服其他人
   - 高决策力低支持(blocker/反对者)：先了解反对原因，针对性解决或绕过
   - 高紧迫感低支持：快速提供POC/案例数据证明价值
   - 向导/教练(guide/coach)：请教内部信息，了解决策链和隐性规则
   - 怀疑者(skeptic)：用同行案例、数据对比说话
5. **阶段对齐**：策略应与当前销售阶段（{project.sales_stage or '未知'}）的工作重心和交付物紧密对齐
6. **避免重复**：如果提供了"历史互动记录"或"已安排的待办事项"，必须避免推荐已经完成或已做过的事情，应在历史基础上推进下一步；已完成的待办不要再推荐，已拜访过的议题不要重复；与已安排待办雷同的行动不要再次推荐

## 输出格式（严格JSON）
{{
  "actions": [
    {{
      "target_stakeholder": "干系人姓名",
      "title": "策略标题（10-15字，行动导向）",
      "description": "具体策略内容（80-150字，说明做什么、怎么做）",
      "reasoning": "为什么采用这个策略（50-100字，基于该干系人的诉求和状态）",
      "action_type": "build_alliance|address_concerns|provide_material|seek_intelligence|leverage_champion",
      "priority_score": 60-95的整数,
      "urgency": "high|medium|low",
      "estimated_effort": "high|medium|low"
    }}
  ]
}}

## action_type说明
- build_alliance: 建立结盟/深化关系
- address_concerns: 解决顾虑/应对反对
- provide_material: 提供定向材料/POC/案例
- seek_intelligence: 获取内部情报/了解决策链
- leverage_champion: 利用支持者影响他人

只输出JSON，不要输出其他内容。"""

            result = llm.chat_json(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                max_tokens=4000
            )

            if not result or not isinstance(result, dict):
                return []

            raw_actions = result.get('actions', [])
            if not isinstance(raw_actions, list):
                return []

            # 找到姓名→stakeholder.id的映射，便于前端联动
            name_to_id = {s.name: s.id for s in stakeholders}

            actions = []
            for item in raw_actions:
                if not isinstance(item, dict):
                    continue
                target_name = item.get('target_stakeholder', '').strip()
                if not target_name:
                    continue

                # 校验priority_score范围
                try:
                    priority_score = int(item.get('priority_score', 70))
                    priority_score = max(60, min(95, priority_score))
                except (ValueError, TypeError):
                    priority_score = 70

                valid_urgency = {'high', 'medium', 'low'}
                urgency = item.get('urgency', 'medium')
                if urgency not in valid_urgency:
                    urgency = 'medium'

                valid_effort = {'high', 'medium', 'low'}
                effort = item.get('estimated_effort', 'medium')
                if effort not in valid_effort:
                    effort = 'medium'

                valid_types = {'build_alliance', 'address_concerns', 'provide_material', 'seek_intelligence', 'leverage_champion'}
                action_type = item.get('action_type', 'build_alliance')
                if action_type not in valid_types:
                    action_type = 'build_alliance'

                sk_id = name_to_id.get(target_name)
                action_id = f"llm_stakeholder_{sk_id}" if sk_id else f"llm_stakeholder_{target_name}"

                actions.append({
                    'id': action_id,
                    'title': item.get('title', f'推进{target_name}'),
                    'description': item.get('description', ''),
                    'reasoning': item.get('reasoning', ''),
                    'target_stakeholder': target_name,
                    'target_stakeholder_id': sk_id,
                    'action_type': action_type,
                    'priority_score': priority_score,
                    'urgency': urgency,
                    'estimated_effort': effort,
                    'source': 'llm'
                })

            logger.info(f"LLM生成了 {len(actions)} 条干系人策略")
            return actions

        except Exception as e:
            logger.error(f"LLM生成干系人策略失败，将退回规则生成: {e}")
            return []

    # =====================================================================
    # 阶段感知 — 各阶段行动指引
    # =====================================================================

    # 各阶段行动重心与推荐类型（基于 SVS+Challenge Sales 五阶段模型）
    STAGE_ACTION_GUIDANCE = {
        'suspect': """### 阶段重心：客户调研、商机识别、初始触点建立、OM10 准备
- 推荐行动类型：调研类（了解客户战略/组织架构）、识别类（识别关键联系人/决策链）、接触类（建立初始关系）
- 重点关注：客户公司结构图、客户战略图、销售目标设定、商机评分卡、OM10 决策准备
- 关系图谱为 Optional，可随销售推进逐步完善""",
        'identity': """### 阶段重心：干系人分析、需求挖掘、关系建立、OM20 准备
- 推荐行动类型：分析类（干系人角色与影响力评估）、挖掘类（业务痛点/预算/采购流程）、结盟类（建立支持联盟）
- 重点关注：干系人角色类型识别（Mobilizer/Blocker/Guide/Champion/Skeptic/Coach）、决策力/支持度/紧迫感评估、关系网络完善、商机团队组建""",
        'define': """### 阶段重心：方案设计、价值证明、竞争定位、投标准备
- 推荐行动类型：方案类（技术方案/商务方案设计）、材料类（ROI 分析/POC/案例）、结盟类（内部对齐/策略评审）
- 重点关注：销售模式选择、解决方案设计、价值主张、CSP 草稿、OM30 策略评审、OM40 投标批准""",
        'confirm': """### 阶段重心：谈判准备、合同条款、共识确认、风险应对
- 推荐行动类型：谈判类（商务谈判/条款沟通）、确认类（干系人共识确认）、应对类（异议处理/风险应对）
- 重点关注：综合提案呈现、异议处理、价格条款谈判、合同法律审核、OM70 赢单/丢单""",
        'closed_won': """### 阶段重心：交接计划、经验总结、续约铺垫
- 推荐行动类型：交接类（向实施团队过渡）、归档类（经验教训沉淀/文档归档）
- 重点关注：合同签署确认、OM80 过渡到实施、客户成功计划落地、经验教训总结""",
        'closed_lost': """### 阶段重心：原因分析、关系维护、改进沉淀
- 推荐行动类型：归档类（丢单原因分析/改进点记录）、关系维护类（保持客户关系）
- 重点关注：丢单原因记录、客户关系维护、改进点识别""",
    }

    def _get_stage_action_guidance(self, sales_stage: str = None) -> str:
        """获取当前阶段的行动指引（未知/未匹配阶段统一 fallback 到 suspect）"""
        if not sales_stage:
            return self.STAGE_ACTION_GUIDANCE['suspect']
        return self.STAGE_ACTION_GUIDANCE.get(
            sales_stage, self.STAGE_ACTION_GUIDANCE['suspect']
        )

    def _score_to_priority(self, score: int) -> int:
        """priority_score 转换为 P1-P4 优先级"""
        if score >= 90:
            return 1
        if score >= 75:
            return 2
        if score >= 55:
            return 3
        return 4

    def _generate_blind_spot_actions(self, blind_spot_data: Dict) -> List[Dict]:
        """基于LLM盲区分析findings生成行动建议"""
        actions = []
        findings = blind_spot_data.get('findings', [])
        if not findings:
            # 兼容旧格式（如果有）
            for key in ['blind_spots', 'frequency_issues', 'quality_issues',
                        'balance_issues', 'trend_issues', 'relationship_issues']:
                findings.extend(blind_spot_data.get(key, []))

        for finding in findings:
            if not isinstance(finding, dict):
                continue
            if finding.get('severity') == 'positive':
                continue

            sev = finding.get('severity', 'medium')
            score = self.SEVERITY_TO_SCORE.get(sev, 50)
            priority = self.SEVERITY_TO_PRIORITY.get(sev, 4)
            name = finding.get('stakeholder_name') or ''
            title = finding.get('title', finding.get('category', '盲区发现'))
            desc = finding.get('recommendation', finding.get('description', ''))

            action = {
                'id': f"blind_spot_{finding.get('category', 'finding')}_{name or 'project'}",
                'title': title,
                'description': desc,
                'action_type': 'blind_spot',
                'priority_score': score,
                'priority': priority,
                'urgency': 'high' if sev in ('critical', 'high') else 'medium',
                'estimated_effort': 'medium'
            }
            if name:
                action['target_stakeholder'] = name
            actions.append(action)

        return actions

    
    def _generate_stakeholder_actions(self, stakeholders: List[Stakeholder]) -> List[Dict]:
        """基于干系人状态生成行动"""
        actions = []
        
        for stakeholder in stakeholders:
            if stakeholder.support_level < 5 and stakeholder.decision_power >= 5:
                actions.append({
                    'id': f"stakeholder_{stakeholder.id}_address_concerns",
                    'title': f"打消{stakeholder.name}的顾虑",
                    'description': f"{stakeholder.name}支持度较低({stakeholder.support_level}/10)，但决策影响力较高({stakeholder.decision_power}/10)，需要了解其顾虑并针对性解决",
                    'target_stakeholder': stakeholder.name,
                    'target_stakeholder_id': stakeholder.id,
                    'action_type': 'address_concerns',
                    'priority_score': 75,
                    'urgency': 'high',
                    'estimated_effort': 'high'
                })
            
            if stakeholder.support_level >= 7 and stakeholder.decision_power >= 6:
                actions.append({
                    'id': f"stakeholder_{stakeholder.id}_build_alliance",
                    'title': f"与{stakeholder.name}建立结盟",
                    'description': f"{stakeholder.name}是高支持者({stakeholder.support_level}/10)且有较高决策力({stakeholder.decision_power}/10)，应加深关系，争取成为内部倡导者",
                    'target_stakeholder': stakeholder.name,
                    'target_stakeholder_id': stakeholder.id,
                    'action_type': 'build_alliance',
                    'priority_score': 70,
                    'urgency': 'medium',
                    'estimated_effort': 'medium'
                })
            
            if stakeholder.urgency >= 7 and stakeholder.support_level < 7:
                actions.append({
                    'id': f"stakeholder_{stakeholder.id}_provide_material",
                    'title': f"向{stakeholder.name}提供定向材料",
                    'description': f"{stakeholder.name}紧迫感较高({stakeholder.urgency}/10)但支持度不足，需要提供针对性材料来证明方案价值",
                    'target_stakeholder': stakeholder.name,
                    'target_stakeholder_id': stakeholder.id,
                    'action_type': 'provide_material',
                    'priority_score': 65,
                    'urgency': 'medium',
                    'estimated_effort': 'medium'
                })
            
            if stakeholder.buyer_role == 'blocker':
                actions.append({
                    'id': f"stakeholder_{stakeholder.id}_address_blocker",
                    'title': f"处理{stakeholder.name}的反对意见",
                    'description': f"{stakeholder.name}是反对者，需要了解其反对原因，寻找解决方案或绕过策略",
                    'target_stakeholder': stakeholder.name,
                    'target_stakeholder_id': stakeholder.id,
                    'action_type': 'address_concerns',
                    'priority_score': 90,
                    'urgency': 'high',
                    'estimated_effort': 'high'
                })
        
        return actions
    
    def _generate_relationship_actions(self, stakeholders: List[Stakeholder], relationships: List[Relationship]) -> List[Dict]:
        """基于关系网络生成行动"""
        actions = []
        
        stakeholder_ids = {s.id for s in stakeholders}
        source_ids = {r.source_id for r in relationships}
        target_ids = {r.target_id for r in relationships}
        
        connected_ids = source_ids.union(target_ids)
        isolated_ids = stakeholder_ids - connected_ids
        
        for stakeholder_id in isolated_ids:
            stakeholder = next((s for s in stakeholders if s.id == stakeholder_id), None)
            if stakeholder and stakeholder.decision_power >= 5:
                actions.append({
                    'id': f"relationship_{stakeholder_id}_connect",
                    'title': f"建立与{stakeholder.name}的关系连接",
                    'description': f"{stakeholder.name}目前在图谱中是孤立节点，建议通过现有干系人引荐建立联系",
                    'target_stakeholder': stakeholder.name,
                    'target_stakeholder_id': stakeholder.id,
                    'action_type': 'build_alliance',
                    'priority_score': 60,
                    'urgency': 'medium',
                    'estimated_effort': 'low'
                })
        
        for stakeholder in stakeholders:
            if stakeholder.buyer_role == 'mobilizer' and stakeholder.support_level >= 6:
                high_decision_stakeholders = [
                    s for s in stakeholders 
                    if s.id != stakeholder.id and s.decision_power >= 7
                ]
                
                for target in high_decision_stakeholders:
                    has_relationship = any(
                        (r.source_id == stakeholder.id and r.target_id == target.id) or
                        (r.source_id == target.id and r.target_id == stakeholder.id)
                        for r in relationships
                    )
                    
                    if not has_relationship:
                        actions.append({
                            'id': f"relationship_{stakeholder.id}_{target.id}_bridge",
                            'title': f"推动{stakeholder.name}影响{target.name}",
                            'description': f"{stakeholder.name}是行动派，建议推动其向高决策力的{target.name}进行内部推销",
                            'source_stakeholder': stakeholder.name,
                            'target_stakeholder': target.name,
                            'action_type': 'build_alliance',
                            'priority_score': 75,
                            'urgency': 'medium',
                            'estimated_effort': 'medium'
                        })
        
        return actions
    
    def generate_action_brief(self, project_id: int, stakeholder_id: int) -> Dict[str, Any]:
        """生成单人拜访简报"""
        project = Project.query.get_or_404(project_id)
        stakeholder = Stakeholder.query.get_or_404(stakeholder_id)
        
        brief = {
            'project_id': project_id,
            'project_name': project.name,
            'stakeholder_id': stakeholder_id,
            'stakeholder_name': stakeholder.name,
            'stakeholder_position': stakeholder.position,
            'sections': []
        }
        
        pain_point_section = self._generate_pain_point_section(project, stakeholder)
        if pain_point_section:
            brief['sections'].append(pain_point_section)
        
        insight_section = self._generate_insight_section(project, stakeholder)
        if insight_section:
            brief['sections'].append(insight_section)
        
        solution_section = self._generate_solution_section(project, stakeholder)
        if solution_section:
            brief['sections'].append(solution_section)
        
        brief['key_messages'] = self._generate_key_messages(stakeholder)
        
        return brief
    
    def _generate_pain_point_section(self, project: Project, stakeholder: Stakeholder) -> Dict:
        """生成痛点陈述部分"""
        return {
            'title': '痛点陈述',
            'content': self._build_pain_point_content(project, stakeholder),
            'purpose': '用客户的语言描述其当前面临的挑战，建立同理心'
        }
    
    def _build_pain_point_content(self, project: Project, stakeholder: Stakeholder) -> str:
        """构建痛点陈述内容"""
        pain_points = []

        pain_points_summary = _build_project_insight_summary(project.id)
        if pain_points_summary:
            pain_points.append(f"当前业务痛点：{pain_points_summary}")

        if stakeholder.personal_agenda:
            pain_points.append(f"个人关注点：{stakeholder.personal_agenda}")
        
        if stakeholder.position:
            pain_points.append(f"作为{stakeholder.position}，您可能面临的挑战包括：")
        
        if stakeholder.responsibilities:
            pain_points.append(f"职责范围：{stakeholder.responsibilities}")
        
        return "\n".join(pain_points)
    
    def _generate_insight_section(self, project: Project, stakeholder: Stakeholder) -> Dict:
        """生成破坏固有认知部分"""
        return {
            'title': '破坏固有认知',
            'content': self._build_insight_content(project, stakeholder),
            'purpose': '引入新视角，挑战客户的现状思维'
        }
    
    def _build_insight_content(self, project: Project, stakeholder: Stakeholder) -> str:
        """构建破坏固有认知内容"""
        insights = []
        
        if project.industry:
            insights.append(f"行业洞察：在{project.industry}领域，领先企业正在采取不同的做法...")
        
        if stakeholder.buyer_role == 'skeptic':
            insights.append("针对您可能存在的疑虑，我们观察到...")
        
        if stakeholder.support_level < 5:
            insights.append("很多客户最初也认为...，但实际体验后发现...")
        
        return "\n".join(insights) if insights else "行业最佳实践表明，传统做法可能存在盲区..."
    
    def _generate_solution_section(self, project: Project, stakeholder: Stakeholder) -> Dict:
        """生成引入方案部分"""
        return {
            'title': '引入方案',
            'content': self._build_solution_content(project, stakeholder),
            'purpose': '将解决方案与客户痛点精准对接'
        }
    
    def _build_solution_content(self, project: Project, stakeholder: Stakeholder) -> str:
        """构建引入方案内容"""
        solutions = []
        
        solutions.append("我们的方案能够帮助您：")
        
        if stakeholder.decision_power >= 7:
            solutions.append("- 快速实现业务目标，提升决策效率")
        
        if stakeholder.support_level < 5:
            solutions.append("- 降低风险，确保平稳过渡")
        
        if stakeholder.urgency >= 7:
            solutions.append("- 快速见效，满足紧迫需求")
        
        return "\n".join(solutions)
    
    def _generate_key_messages(self, stakeholder: Stakeholder) -> List[str]:
        """生成关键信息点"""
        messages = []
        
        if stakeholder.buyer_role == 'mobilizer':
            messages.append("强调方案对业务的直接价值和可量化成果")
        elif stakeholder.buyer_role == 'blocker':
            messages.append("先倾听顾虑，再针对性解决，避免直接反驳")
        elif stakeholder.buyer_role == 'skeptic':
            messages.append("用数据和案例说话，提供可验证的证据")
        elif stakeholder.buyer_role == 'coach':
            messages.append("请教对方经验，建立信任关系")
        
        if stakeholder.decision_power >= 8:
            messages.append("聚焦战略价值和长期回报")
        else:
            messages.append("强调具体功能和短期效益")
        
        return messages