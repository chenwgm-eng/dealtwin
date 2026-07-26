"""
图谱盲区预警服务 — LLM驱动版
基于挑战式销售方法论，由LLM根据项目实际情况评估盲区
"""

import json
import logging
from typing import List, Dict, Any, Optional

from app import db
from app.models.database import (
    Project, Stakeholder, Relationship,
    OpportunityTask, MeetingPlan, FeedbackRecord, StateChangeLog
)
from app.api.sales_twin._helpers import _build_project_insight_summary
from app.utils.llm_client import LLMClient

logger = logging.getLogger(__name__)


class BlindSpotDetector:
    """图谱盲区检测器 — LLM驱动"""

    def __init__(self):
        self._llm: Optional[LLMClient] = None

    def _get_llm(self) -> LLMClient:
        if self._llm is None:
            self._llm = LLMClient()
        return self._llm

    # =====================================================================
    # 主入口
    # =====================================================================

    def scan_project(self, project_id: int, scan_source: str = 'manual') -> Dict[str, Any]:
        """LLM驱动的盲区扫描

        Args:
            project_id: 项目 ID
            scan_source: 扫描来源标记 'manual'（HTTP 触发）/ 'cron'（后台定时）
        """
        project = Project.query.get_or_404(project_id)

        stakeholders = Stakeholder.query.filter_by(project_id=project_id).all()
        relationships = Relationship.query.filter_by(project_id=project_id).all()

        if not stakeholders:
            return {
                'project_id': project_id,
                'project_name': project.name,
                'total_stakeholders': 0,
                'total_relationships': 0,
                'overall_score': 0,
                'summary': '项目尚未添加任何干系人，无法进行盲区扫描',
                'findings': []
            }

        # 收集原始数据
        context = self._build_context(project, stakeholders, relationships)

        # 调用LLM分析（阶段感知）
        try:
            result = self._llm_analyze(context, sales_stage=project.sales_stage)
        except Exception as e:
            logger.warning(f"LLM盲区分析失败，退回规则分析: {e}")
            result = self._rule_based_fallback(project, stakeholders, relationships)

        result['project_id'] = project_id
        result['project_name'] = project.name
        result['total_stakeholders'] = len(stakeholders)
        result['total_relationships'] = len(relationships)
        result['scan_source'] = scan_source

        # 持久化扫描报告
        self._persist_report(project_id, scan_source, result)

        return result

    def _persist_report(self, project_id: int, scan_source: str, result: Dict[str, Any]) -> None:
        """将扫描结果持久化到 BlindSpotReport 表"""
        try:
            from app.models.database import BlindSpotReport
            findings = result.get('findings', [])
            report = BlindSpotReport(
                project_id=project_id,
                scan_source=scan_source,
                overall_score=result.get('overall_score', 0),
                summary=result.get('summary', ''),
                findings_json=json.dumps(findings, ensure_ascii=False, default=str),
                total_findings=len(findings),
                total_stakeholders=result.get('total_stakeholders', 0),
                total_relationships=result.get('total_relationships', 0),
            )
            db.session.add(report)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error(f"持久化盲区报告失败: {e}", exc_info=True)

    @staticmethod
    def get_latest_report(project_id: int) -> Optional[Dict[str, Any]]:
        """获取项目最新盲区报告（用于前端首次加载时展示）"""
        from app.models.database import BlindSpotReport
        report = BlindSpotReport.query.filter_by(project_id=project_id) \
            .order_by(BlindSpotReport.scanned_at.desc()).first()
        if not report:
            return None
        return {
            'project_id': project_id,
            'scan_source': report.scan_source,
            'overall_score': report.overall_score,
            'summary': report.summary or '',
            'findings': json.loads(report.findings_json) if report.findings_json else [],
            'total_findings': report.total_findings,
            'total_stakeholders': report.total_stakeholders,
            'total_relationships': report.total_relationships,
            'scanned_at': report.scanned_at.isoformat() if report.scanned_at else None,
        }

    # =====================================================================
    # 数据收集 — 构建LLM上下文
    # =====================================================================

    def _build_context(
        self, project: Project,
        stakeholders: List[Stakeholder],
        relationships: List[Relationship]
    ) -> str:
        """收集所有原始数据，构建LLM上下文"""
        sections = []

        # 1. 项目背景
        proj_parts = []
        if project.customer_name:
            proj_parts.append(f"客户: {project.customer_name}")
        if project.industry:
            proj_parts.append(f"行业: {project.industry}")
        if project.sales_stage:
            proj_parts.append(f"销售阶段: {project.sales_stage}")
        insight_summary = _build_project_insight_summary(project.id)
        if insight_summary:
            proj_parts.append(f"业务洞察: {insight_summary[:500]}")
        sections.append("## 项目背景\n" + "\n".join(proj_parts))

        # 2. 干系人画像 + 互动统计
        buyer_role_labels = {
            'mobilizer': '行动派', 'blocker': '反对者',
            'guide': '向导', 'champion': '支持者',
            'skeptic': '怀疑者', 'coach': '教练'
        }
        sk_lines = []
        for s in stakeholders:
            role_label = buyer_role_labels.get(s.buyer_role, s.buyer_role or '未分类')
            parts = [f"- {s.name}"]
            if s.position:
                parts.append(f"职位={s.position}")
            parts.append(f"项目角色={role_label}")
            parts.append(f"决策力={s.decision_power}/10")
            parts.append(f"支持度={s.support_level}/10")
            parts.append(f"紧迫感={s.urgency}/10")
            if s.responsibilities:
                parts.append(f"职责={s.responsibilities[:80]}")
            if s.personal_agenda:
                parts.append(f"个人诉求={s.personal_agenda[:80]}")

            # 互动统计
            visit_count = MeetingPlan.query.filter_by(stakeholder_id=s.id).count()
            total_tasks = OpportunityTask.query.filter_by(stakeholder_id=s.id).count()
            completed_tasks = OpportunityTask.query.filter_by(
                stakeholder_id=s.id, status='completed'
            ).count()
            feedback_count = FeedbackRecord.query.filter_by(
                project_id=project.id
            ).count()  # 项目级反馈，后续LLM可自行判断

            parts.append(f"拜访次数={visit_count}")
            parts.append(f"待办={total_tasks}(已完成{completed_tasks})")

            sk_lines.append(" | ".join(parts))

        sections.append("## 干系人画像与互动统计\n" + "\n".join(sk_lines))

        # 3. 关系网络
        sk_map = {s.id: s.name for s in stakeholders}
        rel_type_labels = {
            'direct_report': '直接汇报', 'peer': '同级', 'allies': '盟友',
            'conflict': '冲突', 'mentor': '导师', 'friend': '朋友'
        }
        rel_lines = []
        for r in relationships:
            src = sk_map.get(r.source_id, f'#{r.source_id}')
            tgt = sk_map.get(r.target_id, f'#{r.target_id}')
            rel = rel_type_labels.get(r.relationship_type, r.relationship_type)
            rel_lines.append(f"- {src} → {tgt}: {rel}")
        if not rel_lines:
            rel_lines.append("（暂无已建立的关系）")
        sections.append("## 关系网络\n" + "\n".join(rel_lines))

        # 4. 最近反馈记录（项目级，取最近10条）
        recent_feedbacks = FeedbackRecord.query.filter_by(
            project_id=project.id
        ).order_by(
            FeedbackRecord.created_at.desc()
        ).limit(10).all()

        fb_lines = []
        for fb in recent_feedbacks:
            content = (fb.feedback_text or '')[:150]
            fb_lines.append(f"- [{fb.created_at.strftime('%m-%d') if fb.created_at else ''}] {content}")
        if fb_lines:
            sections.append("## 最近沟通反馈\n" + "\n".join(fb_lines))

        # 5. 支持度变化轨迹
        state_logs = StateChangeLog.query.join(Stakeholder).filter(
            Stakeholder.project_id == project.id
        ).order_by(StateChangeLog.created_at.desc()).limit(15).all()

        log_lines = []
        for log in state_logs:
            sk_name = sk_map.get(log.stakeholder_id, f'#{log.stakeholder_id}')
            field = log.attribute_name or ''
            old_v = log.old_value or ''
            new_v = log.new_value or ''
            reason = (log.reasoning or '')[:80]
            log_lines.append(f"- {sk_name}: {field} {old_v}→{new_v} ({reason})")
        if log_lines:
            sections.append("## 支持度变化轨迹\n" + "\n".join(log_lines))

        return "\n\n".join(sections)

    # =====================================================================
    # 阶段感知 — 各阶段扫描重点
    # =====================================================================

    # 各阶段盲区扫描重点（基于 SVS+Challenge Sales 五阶段模型）
    STAGE_FOCUS = {
        'suspect': """- **客户信息完整性**：客户公司结构图、战略图、销售目标是否齐全
- **商机识别质量**：商机评分卡（战略契合度、预期收入、竞争强度、资源需求、成功概率）是否完成
- **初始关系建立**：是否已开始接触关键客户联系人
- **OM10 决策准备**：是否有足够信息支撑 Bid/No-Go 决策
- 关系图谱为 Optional，但初始绘制有助于后续阶段推进""",
        'identity': """- **干系人覆盖完整性**：是否识别了所有关键干系人（决策者、影响者、使用者、采购者）
- **客户需求确认程度**：业务痛点、预算范围、采购流程、决策时间节点是否明确
- **决策链覆盖**：从需求发起者到最终拍板人的完整链条是否清晰
- **OM20 决策准备**：是否有 preliminary 利益理解，是否组建商机团队
- **干系人属性准确性**：角色类型（Mobilizer/Blocker/Guide/Champion/Skeptic/Coach）、决策力、支持度、紧迫感是否准确评估""",
        'define': """- **解决方案覆盖度**：技术方案、商务方案、ROI 分析是否完整
- **竞争分析完整性**：竞争对手态势、差异化价值主张是否清晰
- **投标材料准备度**：综合提案（软件报价 + 工作说明书 + CSP）是否就绪
- **干系人共识程度**：内部利益相关者是否对齐销售策略
- **OM30/OM40 评审准备**：策略评审与投标批准的关键材料是否齐全""",
        'confirm': """- **合同条款风险**：法律、财务、交付条款是否存在隐患
- **干系人共识确认**：所有关键干系人是否支持方案，最后异议是否已处理
- **竞品动态**：竞争对手是否在最后阶段有新动作
- **签约障碍识别**：决策流程是否完成，是否有未预期的审批环节
- **OM70 决策准备**：合同文件是否就绪，赢单/丢单迹象是否清晰""",
        'closed_won': """- **交接完整性**：向实施团队的过渡（OM80）是否准备充分
- **续约风险**：客户成功计划 (CSP) 是否落地，未来续约风险点
- **经验教训沉淀**：赢单原因分析、可复制的成功要素是否记录""",
        'closed_lost': """- **丢单原因分析**：丢单的根本原因是否清晰记录
- **客户关系维护**：是否保持客户关系为未来商机铺路
- **经验教训沉淀**：改进点是否识别并记录""",
    }

    def _get_stage_focus(self, sales_stage: str = None) -> str:
        """获取当前阶段的盲区扫描重点（未知/未匹配阶段统一 fallback 到 suspect）"""
        if not sales_stage:
            return self.STAGE_FOCUS['suspect']
        return self.STAGE_FOCUS.get(sales_stage, self.STAGE_FOCUS['suspect'])

    # =====================================================================
    # LLM分析
    # =====================================================================

    def _llm_analyze(self, context: str, sales_stage: str = None) -> Dict[str, Any]:
        """调用LLM进行盲区分析（阶段感知）"""
        llm = self._get_llm()

        stage_focus = self._get_stage_focus(sales_stage)

        prompt = f"""你是一位资深B2B大客户销售策略顾问，精通挑战式销售（Challenger Sale）方法论与 SVS+Challenge Sales 五阶段框架。

请基于以下项目的实际数据，评估当前销售策略中的盲区和风险。

{context}

## 当前阶段重点

项目当前处于 **{sales_stage or '未知'}** 阶段，盲区扫描应聚焦该阶段的核心工作与交付物：

{stage_focus}

## 分析要求

请从挑战式销售的视角全面评估这个项目的干系人管理状况。**不要套用固定模板**，而是根据项目实际情况，找出最关键的风险和盲区。你可能需要关注（但不限于）以下方面：

- **决策链完整性**：是否覆盖了从需求发起者到最终拍板人的完整链条？有没有遗漏的关键环节？
- **沟通效率**：时间精力是否花在了对的人身上？有没有高决策力但被忽视的人？有没有聊得多但只是"talker"不推动进展的人？
- **支持联盟**：支持者够不够？反对者是否被识别和应对？有没有可能被争取的中立者？
- **互动深度**：沟通是否停留在表面？有没有实质性的待办产出？哪些干系人需要更深入的互动？
- **紧迫感管理**：关键干系人是否感到紧迫？有没有紧迫感低但决策力高的人需要被激发？
- **关系网络**：干系人之间的关系是否清晰？有没有可以通过内部盟友影响的目标人物？
- **顾此失彼**：是否过度依赖某一个人或某一类人？这种不平衡是否构成风险？
- **其他风险**：任何你基于数据发现的、上述未覆盖的风险

## 关键原则
1. **基于数据说话**：每个发现都必须引用具体的干系人数据（决策力、支持度、拜访次数等）
2. **聚焦最关键的2-5个问题**：不要罗列所有微小问题，只输出真正影响赢单的风险
3. **可执行**：每个发现都要有明确的下一步行动建议
4. **阶段对齐**：发现的问题应与当前阶段的核心工作和交付物紧密相关

## 输出格式（严格JSON）
{{
  "overall_score": 0-100的整数,
  "summary": "一句话概括当前最大的风险（20-40字）",
  "findings": [
    {{
      "category": "维度名称（如：决策链、沟通效率、支持联盟等，自行命名）",
      "title": "问题标题（10-20字）",
      "description": "具体问题描述（50-120字，引用具体数据）",
      "severity": "critical|high|medium|low",
      "stakeholder_name": "相关干系人姓名（如有，多个用逗号分隔；如不涉及特定干系人则为null）",
      "recommendation": "行动建议（30-80字，说明应该做什么）"
    }}
  ]
}}

只输出JSON，不要输出其他内容。"""

        result = llm.chat_json(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=3000
        )

        if not result or not isinstance(result, dict):
            raise ValueError("LLM返回格式无效")

        # 校验和清理
        score = result.get('overall_score', 50)
        try:
            score = int(score)
            score = max(0, min(100, score))
        except (ValueError, TypeError):
            score = 50

        findings = result.get('findings', [])
        if not isinstance(findings, list):
            findings = []

        # 清理每条finding
        valid_severities = {'critical', 'high', 'medium', 'low', 'positive'}
        cleaned_findings = []
        for f in findings:
            if not isinstance(f, dict):
                continue
            sev = f.get('severity', 'medium')
            if sev not in valid_severities:
                sev = 'medium'
            f['severity'] = sev
            cleaned_findings.append(f)

        return {
            'overall_score': score,
            'summary': result.get('summary', ''),
            'findings': cleaned_findings
        }

    # =====================================================================
    # 规则兜底（LLM失败时使用）
    # =====================================================================

    def _rule_based_fallback(
        self, project: Project,
        stakeholders: List[Stakeholder],
        relationships: List[Relationship]
    ) -> Dict[str, Any]:
        """LLM不可用时的简单规则分析"""
        findings = []
        sk_map = {s.id: s.name for s in stakeholders}

        # 1. 高决策力但零拜访
        for s in stakeholders:
            visit_count = MeetingPlan.query.filter_by(stakeholder_id=s.id).count()
            if s.decision_power >= 7 and visit_count == 0:
                findings.append({
                    'category': '沟通频率',
                    'title': f'{s.name}被忽视',
                    'description': f'{s.name}（决策力{s.decision_power}/10）从未被拜访，这是项目推进的重大风险',
                    'severity': 'high',
                    'stakeholder_name': s.name,
                    'recommendation': f'尽快安排与{s.name}的首次拜访'
                })

        # 2. 低支持度的高决策力干系人
        for s in stakeholders:
            if s.decision_power >= 6 and s.support_level <= 4:
                findings.append({
                    'category': '支持联盟',
                    'title': f'{s.name}支持度偏低',
                    'description': f'{s.name}（决策力{s.decision_power}/10，支持度{s.support_level}/10）是高决策力但低支持度，可能阻碍赢单',
                    'severity': 'high',
                    'stakeholder_name': s.name,
                    'recommendation': f'了解{s.name}的顾虑并针对性解决'
                })

        # 3. 沟通多但无待办产出
        for s in stakeholders:
            visit_count = MeetingPlan.query.filter_by(stakeholder_id=s.id).count()
            total_tasks = OpportunityTask.query.filter_by(stakeholder_id=s.id).count()
            if visit_count >= 2 and total_tasks == 0:
                findings.append({
                    'category': '互动质量',
                    'title': f'与{s.name}的沟通缺乏产出',
                    'description': f'{s.name}已拜访{visit_count}次但无任何待办产出，可能只是"talker"',
                    'severity': 'medium',
                    'stakeholder_name': s.name,
                    'recommendation': f'在下次拜访中设定明确的行动项和后续任务'
                })

        score = max(20, 100 - len(findings) * 15)

        return {
            'overall_score': score,
            'summary': f'发现{len(findings)}个潜在风险（规则分析，LLM不可用）',
            'findings': findings
        }
