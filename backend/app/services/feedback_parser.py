"""
会后无感更新服务
Feedback Parser - 解析非结构化销售纪要，自动更新干系人属性
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import re
import json

from app import db
from app.models.database import (
    Project, Stakeholder, StateChangeLog, OpportunityTask, FeedbackRecord
)
from app.utils.llm_client import LLMClient

logger = logging.getLogger(__name__)

# 有效的买方角色枚举（用于校验 LLM 输出）
VALID_BUYER_ROLES = {'mobilizer', 'blocker', 'guide', 'champion', 'skeptic', 'coach'}


class FeedbackParserService:
    """销售纪要解析服务"""

    def __init__(self):
        self.llm_client = LLMClient()

    def parse_feedback(
        self,
        project_id: int,
        feedback_text: str,
        related_task_ids: List[int] = None,
        related_meeting_plan_id: int = None,
        attachment_infos: List[Dict] = None
    ) -> Dict[str, Any]:
        """解析销售反馈并更新干系人状态（支持新建干系人 + 关联待办 + 附件上下文）

        事务边界：整个解析流程在单个事务中完成，任何步骤失败则全部回滚，
        避免部分提交导致数据不一致（例如日志写失败但干系人已创建）。
        """
        project = Project.query.get_or_404(project_id)
        stakeholders = Stakeholder.query.filter_by(project_id=project_id).all()

        # 优先用LLM解析（能识别新干系人），失败再退回规则
        parsed_result = self._parse_with_llm(feedback_text, stakeholders, attachment_infos)

        # 如果LLM也解析失败，尝试规则解析（仅针对已有干系人）
        if not parsed_result.get('updates') and not parsed_result.get('new_stakeholders'):
            parsed_result = self._parse_with_rules(feedback_text, stakeholders)

        applied_updates = []
        feedback_record = None

        try:
            # 1. 先创建新干系人（仅 add，不 commit）
            for new_sk in parsed_result.get('new_stakeholders', []):
                result = self._create_new_stakeholder(project_id, new_sk)
                if result:
                    applied_updates.append(result)

            # 2. 再更新已有干系人属性（仅 add，不 commit）
            for update in parsed_result.get('updates', []):
                result = self._apply_update(project_id, update)
                if result:
                    applied_updates.append(result)

            # 3. 更新关联的待办事项状态（仅修改对象，不 commit）
            task_updates = []
            if related_task_ids:
                task_updates = self._update_related_tasks(
                    project_id, related_task_ids, feedback_text, parsed_result
                )

            # 4. 保存反馈记录
            feedback_record = FeedbackRecord(
                project_id=project_id,
                related_task_ids=json.dumps(related_task_ids or []),
                related_meeting_plan_id=related_meeting_plan_id,
                feedback_text=feedback_text,
                parse_summary=parsed_result.get('summary', ''),
                total_changes=len(applied_updates)
            )
            db.session.add(feedback_record)

            # 统一提交：所有变更原子化，失败则全部回滚
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error(f"parse_feedback 事务失败，已回滚: {e}", exc_info=True)
            raise

        # 获取最近的状态变更日志（提交后查询才能拿到最新数据）
        log_count = max(len(applied_updates), 10)
        state_change_logs = StateChangeLog.query.filter_by(
            project_id=project_id
        ).order_by(StateChangeLog.created_at.desc()).limit(log_count).all()

        return {
            'project_id': project_id,
            'feedback_id': feedback_record.id if feedback_record else None,
            'original_feedback': feedback_text,
            'parsed_updates': applied_updates,
            'total_changes': len(applied_updates),
            'summary': parsed_result.get('summary', ''),
            'task_updates': task_updates if 'task_updates' in locals() else [],
            'state_logs': [self._log_to_dict(log) for log in state_change_logs]
        }

    def _update_related_tasks(
        self,
        project_id: int,
        task_ids: List[int],
        feedback_text: str,
        parsed_result: Dict
    ) -> List[Dict]:
        """根据反馈内容更新关联的待办事项状态（不提交事务，由调用方统一 commit）"""
        tasks = OpportunityTask.query.filter(
            OpportunityTask.id.in_(task_ids),
            OpportunityTask.project_id == project_id
        ).all()

        updates = []
        # 简单规则：如果反馈中包含"完成/已沟通/已送达/确认/同意"等词，标记待办为已完成
        completion_keywords = ['完成', '已沟通', '已送达', '已发送', '确认', '同意', '搞定', '推进', '已拜访', '已开会']
        is_completed = any(kw in feedback_text for kw in completion_keywords)

        for task in tasks:
            if task.status in ['completed', 'cancelled']:
                continue

            old_status = task.status
            if is_completed:
                task.status = 'completed'
                task.completed_at = datetime.utcnow()
                task.completion_note = f'反馈关联完成: {feedback_text[:100]}'
            else:
                # 没有明确完成信号，标记为进行中
                task.status = 'in_progress'

            task.related_feedback = feedback_text[:500]
            updates.append({
                'task_id': task.id,
                'title': task.title,
                'old_status': old_status,
                'new_status': task.status,
                'completed': is_completed
            })

        # 不再在此处 commit，由 parse_feedback 统一提交
        return updates
    
    def _parse_with_rules(self, feedback_text: str, stakeholders: List[Stakeholder]) -> Dict[str, Any]:
        """使用规则引擎初步解析"""
        updates = []
        summary_parts = []
        
        for stakeholder in stakeholders:
            name_pattern = re.compile(re.escape(stakeholder.name), re.IGNORECASE)
            if not name_pattern.search(feedback_text):
                continue
            
            support_up_patterns = [
                rf'{re.escape(stakeholder.name)}.*?(同意|认可|支持|看好|觉得不错|接受|赞同)',
                rf'{re.escape(stakeholder.name)}.*?支持度.*?(上升|提高|增加|\+\s*(\d+)|从\s*(\d+)\s*到\s*(\d+)|升到\s*(\d+))',
            ]
            
            for pattern in support_up_patterns:
                match = re.search(pattern, feedback_text, re.IGNORECASE)
                if match:
                    old_val = stakeholder.support_level
                    new_val = min(10, old_val + 1)
                    updates.append({
                        'stakeholder_id': stakeholder.id,
                        'stakeholder_name': stakeholder.name,
                        'attribute': 'support_level',
                        'old_value': str(old_val),
                        'new_value': str(new_val),
                        'reasoning': f'根据纪要："{stakeholder.name}表达了认可/支持态度"'
                    })
                    summary_parts.append(f'{stakeholder.name}支持度: {old_val}→{new_val}')
                    break
            
            support_down_patterns = [
                rf'{re.escape(stakeholder.name)}.*?(担心|顾虑|担忧|害怕|怕|反对|不认同|质疑|有疑问|犹豫|纠结)',
                rf'{re.escape(stakeholder.name)}.*?支持度.*?(下降|降低|减少|-\s*(\d+))',
            ]
            
            for pattern in support_down_patterns:
                match = re.search(pattern, feedback_text, re.IGNORECASE)
                if match:
                    old_val = stakeholder.support_level
                    new_val = max(0, old_val - 1)
                    if len(updates) > 0 and updates[-1]['stakeholder_id'] == stakeholder.id and updates[-1]['attribute'] == 'support_level':
                        break
                    updates.append({
                        'stakeholder_id': stakeholder.id,
                        'stakeholder_name': stakeholder.name,
                        'attribute': 'support_level',
                        'old_value': str(old_val),
                        'new_value': str(new_val),
                        'reasoning': f'根据纪要："{stakeholder.name}存在顾虑/担忧"'
                    })
                    summary_parts.append(f'{stakeholder.name}支持度: {old_val}→{new_val}')
                    break
            
            urgency_patterns = [
                rf'{re.escape(stakeholder.name)}.*?(紧急|紧迫|着急|尽快|马上|立刻|时间紧)',
            ]
            
            for pattern in urgency_patterns:
                match = re.search(pattern, feedback_text, re.IGNORECASE)
                if match:
                    old_val = stakeholder.urgency
                    new_val = min(10, old_val + 2)
                    updates.append({
                        'stakeholder_id': stakeholder.id,
                        'stakeholder_name': stakeholder.name,
                        'attribute': 'urgency',
                        'old_value': str(old_val),
                        'new_value': str(new_val),
                        'reasoning': f'根据纪要："{stakeholder.name}表现出紧迫感"'
                    })
                    summary_parts.append(f'{stakeholder.name}紧迫感: {old_val}→{new_val}')
                    break
            
            decision_patterns = [
                rf'{re.escape(stakeholder.name)}.*?(决策者|拍板|说了算|最终决定|有决策权)',
            ]
            
            for pattern in decision_patterns:
                match = re.search(pattern, feedback_text, re.IGNORECASE)
                if match:
                    old_val = stakeholder.decision_power
                    new_val = min(10, old_val + 1)
                    updates.append({
                        'stakeholder_id': stakeholder.id,
                        'stakeholder_name': stakeholder.name,
                        'attribute': 'decision_power',
                        'old_value': str(old_val),
                        'new_value': str(new_val),
                        'reasoning': f'根据纪要："{stakeholder.name}具有决策权"'
                    })
                    summary_parts.append(f'{stakeholder.name}决策力: {old_val}→{new_val}')
                    break
        
        return {
            'updates': updates,
            'summary': '；'.join(summary_parts) if summary_parts else ''
        }
    
    def _parse_with_llm(self, feedback_text: str, stakeholders: List[Stakeholder], attachment_infos: List[Dict] = None) -> Dict[str, Any]:
        """使用LLM深度解析（支持识别新干系人 + 附件上下文）"""
        try:
            if stakeholders:
                stakeholder_info = '\n'.join([
                    f"- ID:{s.id} 姓名:{s.name} 职位:{s.position or '未知'} "
                    f"决策力:{s.decision_power} 支持度:{s.support_level} 紧迫感:{s.urgency} "
                    f"角色:{s.buyer_role or '未知'}"
                    for s in stakeholders
                ])
            else:
                stakeholder_info = "（当前项目尚未录入任何干系人）"

            # 附件上下文（作为解析输入之一）
            attachment_section = ''
            if attachment_infos:
                attachment_list = '\n'.join(
                    f"- {a['filename']} ({a.get('type', '未知类型')})"
                    for a in attachment_infos
                )
                attachment_section = f"""
## 本次拜访附带材料（结合材料内容综合分析反馈）
{attachment_list}

注意：以上材料是本次拜访中使用的会议纪要/方案/演示文档等，请结合材料名称推断拜访场景的完整性，但干系人状态变化仍以"销售反馈原文"为准。
"""

            prompt = f"""你是一个B2B销售纪要分析助手。请分析销售反馈，提取干系人状态变化，并识别纪要中首次出现的新干系人。

## 项目已有干系人列表
{stakeholder_info}

## 销售反馈原文
{feedback_text}
{attachment_section}

## 任务
请识别两类信息：

### 类型A：新干系人（纪要中提到的、不在已有列表中的人）
对于每个新干系人，请根据纪要内容推断其初始属性：
- name: 姓名（必填）
- position: 职位（如果纪要提到）
- buyer_role: 买方角色，从以下选一：mobilizer(行动派/推动者), blocker(反对者), guide(向导/内部顾问), champion(支持者/倡导者), skeptic(怀疑者), coach(教练/导师)
- decision_power: 决策影响力 0-10（决策者=9-10，部门负责人=6-8，普通参与=3-5，影响者=4-6）
- support_level: 支持度 0-10（明确支持=8-10，倾向支持=6-7，中立=5，有顾虑=3-4，反对=1-2）
- urgency: 紧迫感 0-10（时间紧/尽快=8-10，较急=6-7，一般=5，不急=3-4）
- responsibilities: 职责（如果纪要提到）
- personal_agenda: 个人诉求（如果纪要提到，如"关注实施周期和交付质量"）

### 类型B：已有干系人的属性变化
对于已在列表中的干系人，识别其 support_level / decision_power / urgency / buyer_role 的变化。

请以JSON格式输出，格式如下：
{{
  "new_stakeholders": [
    {{
      "name": "张老师",
      "position": "项目负责人",
      "buyer_role": "champion",
      "decision_power": 9,
      "support_level": 8,
      "urgency": 7,
      "responsibilities": "项目决策，关注实施周期和交付质量",
      "personal_agenda": "关注实施周期和交付质量",
      "reasoning": "纪要明确指出张老师是项目决策者，对项目有较高支持度和紧迫感"
    }}
  ],
  "updates": [
    {{
      "stakeholder_id": 1,
      "stakeholder_name": "张三",
      "attribute": "support_level",
      "old_value": "5",
      "new_value": "7",
      "reasoning": "在会议中明确表达了对方案的认可"
    }}
  ],
  "summary": "一句话总结纪要要点"
}}

## 重要规则
1. new_stakeholders 数组只放纪要中提到的、不在已有列表中的人
2. updates 数组只放已有干系人的属性变化
3. buyer_role 必须是 mobilizer/blocker/guide/champion/skeptic/coach 之一
4. decision_power/support_level/urgency 必须是0-10的整数
5. 如果纪要中没有提到任何干系人，返回空数组
6. 只输出JSON，不要输出其他内容"""

            result = self.llm_client.chat_json(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=2000
            )

            if result and isinstance(result, dict):
                # 确保字段完整性
                result.setdefault('new_stakeholders', [])
                result.setdefault('updates', [])
                result.setdefault('summary', '')
                return result

        except Exception as e:
            logger.warning(f"LLM解析失败: {e}")

        return {
            'updates': [],
            'new_stakeholders': [],
            'summary': ''
        }

    def _create_new_stakeholder(self, project_id: int, new_sk: Dict) -> Optional[Dict]:
        """根据LLM解析结果创建新干系人"""
        name = new_sk.get('name', '').strip()
        if not name:
            return None

        # 避免重复创建（同名干系人已存在则跳过）
        existing = Stakeholder.query.filter_by(
            project_id=project_id, name=name
        ).first()
        if existing:
            return None

        # 解析并校验各属性
        def clamp_int(val, default=5, lo=0, hi=10):
            try:
                v = int(val)
                return max(lo, min(hi, v))
            except (ValueError, TypeError):
                return default

        valid_roles = {'mobilizer', 'blocker', 'guide', 'champion', 'skeptic', 'coach'}
        buyer_role = new_sk.get('buyer_role')
        if buyer_role not in valid_roles:
            buyer_role = None

        decision_power = clamp_int(new_sk.get('decision_power'), 5)
        support_level = clamp_int(new_sk.get('support_level'), 5)
        urgency = clamp_int(new_sk.get('urgency'), 5)

        stakeholder = Stakeholder(
            project_id=project_id,
            name=name,
            position=new_sk.get('position'),
            buyer_role=buyer_role,
            decision_power=decision_power,
            support_level=support_level,
            urgency=urgency,
            status='pending',  # 从会议纪要识别的新干系人默认"待识别"
            responsibilities=new_sk.get('responsibilities'),
            personal_agenda=new_sk.get('personal_agenda')
        )
        db.session.add(stakeholder)
        db.session.commit()

        reasoning = new_sk.get('reasoning', '从会议纪要中识别的新干系人')

        # 记录创建日志
        log = StateChangeLog(
            project_id=project_id,
            stakeholder_id=stakeholder.id,
            change_object=name,
            attribute_name='create_stakeholder',
            old_value='',
            new_value=f'决策力={decision_power}, 支持度={support_level}, 紧迫感={urgency}, 角色={buyer_role or "未指定"}',
            reasoning=reasoning,
            change_source='feedback_parser'
        )
        db.session.add(log)
        db.session.commit()

        return {
            'stakeholder_id': stakeholder.id,
            'stakeholder_name': name,
            'attribute': 'create_stakeholder',
            'old_value': '',
            'new_value': f'决策力={decision_power}, 支持度={support_level}, 紧迫感={urgency}, 角色={buyer_role or "未指定"}',
            'reasoning': reasoning,
            'is_new_stakeholder': True
        }
    
    def _apply_update(self, project_id: int, update: Dict) -> Optional[Dict]:
        """应用单个更新"""
        stakeholder_id = update.get('stakeholder_id')
        attribute = update.get('attribute')
        new_value = update.get('new_value')
        reasoning = update.get('reasoning', '')
        
        if not stakeholder_id or not attribute or new_value is None:
            return None
        
        stakeholder = Stakeholder.query.get(stakeholder_id)
        if not stakeholder:
            return None
        
        old_value = str(getattr(stakeholder, attribute, ''))
        
        if old_value == str(new_value):
            return None
        
        try:
            if attribute in ['decision_power', 'support_level', 'urgency']:
                setattr(stakeholder, attribute, int(new_value))
            elif attribute == 'buyer_role':
                # Enum 字段校验：仅允许合法的买方角色枚举值
                role_val = str(new_value)
                if role_val not in VALID_BUYER_ROLES:
                    logger.warning(f"_apply_update 拒绝非法 buyer_role 值: {role_val}")
                    return None
                setattr(stakeholder, attribute, role_val)
            else:
                setattr(stakeholder, attribute, str(new_value))
        except (ValueError, TypeError):
            return None

        log = StateChangeLog(
            project_id=project_id,
            stakeholder_id=stakeholder_id,
            change_object=stakeholder.name,
            attribute_name=attribute,
            old_value=old_value,
            new_value=str(new_value),
            reasoning=reasoning,
            change_source='feedback_parser'
        )

        db.session.add(log)
        # 不在此处 commit，由 parse_feedback 统一提交

        return {
            'stakeholder_id': stakeholder_id,
            'stakeholder_name': stakeholder.name,
            'attribute': attribute,
            'old_value': old_value,
            'new_value': str(new_value),
            'reasoning': reasoning
        }
    
    def get_state_logs(self, project_id: int, limit: int = 50) -> Dict[str, Any]:
        """获取状态变更日志"""
        logs = StateChangeLog.query.filter_by(
            project_id=project_id
        ).order_by(
            StateChangeLog.created_at.desc()
        ).limit(limit).all()
        
        return {
            'project_id': project_id,
            'total': len(logs),
            'logs': [self._log_to_dict(log) for log in logs]
        }
    
    def _log_to_dict(self, log: StateChangeLog) -> Dict:
        """日志转字典"""
        return {
            'id': log.id,
            'project_id': log.project_id,
            'stakeholder_id': log.stakeholder_id,
            'change_object': log.change_object,
            'attribute_name': log.attribute_name,
            'old_value': log.old_value,
            'new_value': log.new_value,
            'reasoning': log.reasoning,
            'change_source': log.change_source,
            'created_at': log.created_at.isoformat() if log.created_at else None
        }
