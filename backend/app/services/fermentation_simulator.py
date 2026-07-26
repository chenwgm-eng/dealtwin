"""
闭门发酵模拟服务
模拟会议结束后，干系人之间的私下互动和态度变化
基于Mobilizer/Blocker角色和关系网络进行社会影响传播
阶段感知：根据项目所处销售阶段（suspect/identity/define/confirm/
closed_won/closed_lost）调整发酵规则与影响传播侧重
"""

from typing import List, Dict, Any
from copy import deepcopy

from app import db
from app.models.database import Project, Stakeholder, Relationship


class FermentationSimulator:
    """闭门发酵模拟器（阶段感知）"""

    # 阶段发酵规则配置
    # - information_asymmetry: 信息不对称消除因子（早期阶段更高，信息传播为主）
    # - value_diffusion: 价值认同传播因子（中期阶段更高，方案/价值认同为主）
    # - long_term_factor: 长期关系影响因子（Close 阶段更高，长期维护为主）
    # - role_amplifier: 角色放大系数（按阶段调整不同角色的传播权重）
    STAGE_FERMENTATION_RULES = {
        'suspect': {
            'focus': '信息传播、关系网络影响、关键干系人态度变化',
            'information_asymmetry': 1.3,   # 早期信息不对称强，传播更活跃
            'value_diffusion': 0.7,
            'long_term_factor': 0.5,
            'role_amplifier': {
                'mobilizer': 1.5, 'blocker': 1.3, 'guide': 1.4,
                'champion': 1.2, 'skeptic': 1.0, 'coach': 1.3,
            },
        },
        'identity': {
            'focus': '信息传播、关系网络影响、关键干系人态度变化',
            'information_asymmetry': 1.2,
            'value_diffusion': 0.9,
            'long_term_factor': 0.6,
            'role_amplifier': {
                'mobilizer': 1.5, 'blocker': 1.4, 'guide': 1.4,
                'champion': 1.2, 'skeptic': 1.1, 'coach': 1.3,
            },
        },
        'define': {
            'focus': '方案内部推广、异议处理效果、决策链共识形成',
            'information_asymmetry': 0.9,
            'value_diffusion': 1.3,   # 方案阶段价值认同传播更活跃
            'long_term_factor': 0.7,
            'role_amplifier': {
                'mobilizer': 1.4, 'blocker': 1.5, 'guide': 1.3,
                'champion': 1.5, 'skeptic': 1.3, 'coach': 1.2,
            },
        },
        'confirm': {
            'focus': '方案内部推广、异议处理效果、决策链共识形成',
            'information_asymmetry': 0.8,
            'value_diffusion': 1.4,
            'long_term_factor': 0.8,
            'role_amplifier': {
                'mobilizer': 1.4, 'blocker': 1.5, 'guide': 1.3,
                'champion': 1.5, 'skeptic': 1.4, 'coach': 1.2,
            },
        },
        'closed_won': {
            'focus': '合同条款影响、实施风险传播、未来合作意向',
            'information_asymmetry': 0.6,
            'value_diffusion': 1.0,
            'long_term_factor': 1.4,   # 赢单后长期关系维护更重要
            'role_amplifier': {
                'mobilizer': 1.3, 'blocker': 1.0, 'guide': 1.2,
                'champion': 1.4, 'skeptic': 0.9, 'coach': 1.3,
            },
        },
        'closed_lost': {
            'focus': '合同条款影响、实施风险传播、未来合作意向',
            'information_asymmetry': 0.6,
            'value_diffusion': 0.9,
            'long_term_factor': 1.3,
            'role_amplifier': {
                'mobilizer': 1.2, 'blocker': 1.0, 'guide': 1.2,
                'champion': 1.3, 'skeptic': 1.0, 'coach': 1.3,
            },
        },
    }

    # 默认发酵规则（阶段未知或未匹配时使用，suspect 为销售流程起点）
    DEFAULT_RULES = STAGE_FERMENTATION_RULES['suspect']

    def __init__(self):
        self.influence_factor = {
            'allies': 0.8,
            'direct_report': 0.7,
            'mentor': 0.6,
            'friend': 0.5,
            'neutral': 0.3,
            'competing': 0.1,
            'conflict': -0.5,
        }

    def _get_stage_rules(self, sales_stage: str = None) -> Dict[str, Any]:
        """获取当前阶段的发酵规则（未知/未匹配阶段统一 fallback 到 suspect）"""
        if not sales_stage:
            return self.DEFAULT_RULES
        return self.STAGE_FERMENTATION_RULES.get(sales_stage, self.DEFAULT_RULES)

    def simulate_fermentation(
        self,
        project_id: int,
        days: int = 3,
        initial_events: List[Dict] = None
    ) -> Dict[str, Any]:
        """模拟闭门发酵过程（阶段感知）"""
        project = Project.query.get_or_404(project_id)

        stakeholders = Stakeholder.query.filter_by(project_id=project_id).all()
        relationships = Relationship.query.filter_by(project_id=project_id).all()

        if not stakeholders:
            return {
                'project_id': project_id,
                'days': days,
                'rounds': 0,
                'final_states': [],
                'history': [],
                'conclusion': '无干系人数据'
            }

        # 获取阶段发酵规则
        stage_rules = self._get_stage_rules(project.sales_stage)

        state_history = []

        current_state = {}
        for s in stakeholders:
            current_state[s.id] = {
                'id': s.id,
                'name': s.name,
                'position': s.position,
                'buyer_role': s.buyer_role,
                'support_level': float(s.support_level),
                'decision_power': float(s.decision_power),
                'urgency': float(s.urgency),
            }

        if initial_events:
            for event in initial_events:
                target_id = event.get('stakeholder_id')
                if target_id and target_id in current_state:
                    impact = event.get('support_impact', 0)
                    current_state[target_id]['support_level'] = min(
                        10, max(0, current_state[target_id]['support_level'] + impact)
                    )

        state_history.append({
            'round': 0,
            'label': '会议结束时',
            'states': deepcopy(current_state)
        })

        for day in range(1, days + 1):
            new_state = deepcopy(current_state)

            for s in stakeholders:
                s_state = current_state[s.id]
                total_influence = 0.0
                influence_weight = 0.0

                for r in relationships:
                    other_id = None
                    rel_type = r.relationship_type or 'neutral'

                    if r.source_id == s.id and r.target_id in current_state:
                        other_id = r.target_id
                    elif r.target_id == s.id and r.source_id in current_state:
                        other_id = r.source_id

                    if not other_id:
                        continue

                    other_state = current_state[other_id]

                    base_factor = self.influence_factor.get(rel_type, 0.3)
                    power_factor = other_state['decision_power'] / 10.0
                    relationship_strength = (r.influence_weight or 0.5)

                    support_diff = other_state['support_level'] - s_state['support_level']

                    # 阶段感知的影响计算：
                    # - 信息不对称消除（早期阶段更活跃）
                    # - 价值认同传播（中期阶段更活跃）
                    # - 长期关系影响（Close 阶段更活跃）
                    info_factor = stage_rules['information_asymmetry']
                    value_factor = stage_rules['value_diffusion']
                    long_term = stage_rules['long_term_factor']

                    # 综合传播系数：信息传播 + 价值认同 + 长期关系
                    # support_diff > 0 表示对方更支持，正向影响；< 0 表示对方更反对
                    diffusion_coef = (info_factor + value_factor) / 2.0
                    influence = (base_factor * power_factor * relationship_strength
                                 * support_diff * 0.1 * diffusion_coef)
                    # 长期关系因子：对盟友/朋友关系有正向加成
                    # 仅当对方支持度更高时才产生正向影响，避免对方更反对时也拉高支持度
                    if rel_type in ('allies', 'friend', 'mentor') and support_diff > 0:
                        influence += base_factor * power_factor * long_term * 0.05

                    # 角色放大系数（阶段感知）
                    role_amp = stage_rules['role_amplifier'].get(other_state['buyer_role'], 1.0)
                    influence *= role_amp

                    total_influence += influence
                    influence_weight += abs(base_factor * power_factor * relationship_strength)

                if influence_weight > 0:
                    net_change = total_influence / influence_weight * 10
                    new_support = s_state['support_level'] + net_change
                    new_state[s.id]['support_level'] = min(10, max(0, new_support))

            current_state = new_state

            round_label = f'第{day}天'
            if day == days:
                round_label = f'第{day}天(最终)'

            state_history.append({
                'round': day,
                'label': round_label,
                'states': deepcopy(current_state)
            })

        conclusion = self._generate_conclusion(state_history, stage_rules)

        return {
            'project_id': project_id,
            'project_name': project.name,
            'sales_stage': project.sales_stage,
            'stage_focus': stage_rules['focus'],
            'days': days,
            'rounds': days + 1,
            'final_states': self._format_states(current_state),
            'history': [
                {
                    'round': h['round'],
                    'label': h['label'],
                    'states': self._format_states(h['states']),
                    'average_support': self._calc_avg_support(h['states'])
                }
                for h in state_history
            ],
            'conclusion': conclusion,
            'trend': {
                'initial_avg': self._calc_avg_support(state_history[0]['states']),
                'final_avg': self._calc_avg_support(state_history[-1]['states']),
                'change': (
                    self._calc_avg_support(state_history[-1]['states']) -
                    self._calc_avg_support(state_history[0]['states'])
                )
            }
        }
    
    def _generate_conclusion(
        self,
        history: List[Dict],
        stage_rules: Dict[str, Any] = None
    ) -> str:
        """生成模拟结论（含阶段焦点）"""
        initial_avg = self._calc_avg_support(history[0]['states'])
        final_avg = self._calc_avg_support(history[-1]['states'])
        change = final_avg - initial_avg

        parts = []

        # 阶段焦点说明
        if stage_rules and stage_rules.get('focus'):
            parts.append(f"阶段发酵重点：{stage_rules['focus']}")

        if change > 1:
            parts.append(f"整体支持度呈上升趋势（+{round(change, 1)}分）")
        elif change < -1:
            parts.append(f"整体支持度呈下降趋势（{round(change, 1)}分）")
        else:
            parts.append("整体支持度相对稳定")
        
        final_states = history[-1]['states']
        
        high_support = [
            (s['name'], s['support_level'])
            for s in final_states.values()
            if s['support_level'] >= 7
        ]
        low_support = [
            (s['name'], s['support_level'])
            for s in final_states.values()
            if s['support_level'] <= 4
        ]
        
        if high_support:
            names = '、'.join([n for n, _ in high_support[:3]])
            parts.append(f"支持者阵营：{names}")
        
        if low_support:
            names = '、'.join([n for n, _ in low_support[:3]])
            parts.append(f"反对/疑虑阵营：{names}")
        
        biggest_gainer = None
        biggest_gain = -999
        biggest_loser = None
        biggest_loss = 999
        
        for sid, final in final_states.items():
            initial = history[0]['states'][sid]
            diff = final['support_level'] - initial['support_level']
            if diff > biggest_gain:
                biggest_gain = diff
                biggest_gainer = final['name']
            if diff < biggest_loss:
                biggest_loss = diff
                biggest_loser = final['name']
        
        if biggest_gainer and biggest_gain > 0.5:
            parts.append(f"态度变化最大（积极）：{biggest_gainer}（+{round(biggest_gain, 1)}分）")
        
        if biggest_loser and biggest_loss < -0.5:
            parts.append(f"态度变化最大（消极）：{biggest_loser}（{round(biggest_loss, 1)}分）")
        
        return '；'.join(parts) + '。'
    
    def _format_states(self, states: Dict) -> List[Dict]:
        """格式化状态列表"""
        result = []
        for sid, state in sorted(states.items(), key=lambda x: x[1]['decision_power'], reverse=True):
            result.append({
                'id': state['id'],
                'name': state['name'],
                'position': state['position'],
                'buyer_role': state['buyer_role'],
                'support_level': round(state['support_level'], 1),
                'decision_power': state['decision_power'],
                'urgency': state['urgency'],
                'influence_score': round(state['support_level'] * state['decision_power'] / 100, 3)
            })
        return result
    
    def _calc_avg_support(self, states: Dict) -> float:
        """计算平均支持度"""
        if not states:
            return 0
        total = sum(s['support_level'] * s['decision_power'] for s in states.values())
        total_power = sum(s['decision_power'] for s in states.values())
        if total_power == 0:
            return 0
        return round(total / total_power, 2)
