"""
赢单率预测服务
基于干系人支持度、决策影响力、关系网络计算赢单概率
"""

from typing import List, Dict, Any, Tuple
from collections import deque

from app import db
from app.models.database import Project, Stakeholder, Relationship


class WinRateCalculator:
    """赢单率计算器"""
    
    def __init__(self):
        pass
    
    def calculate_win_rate(self, project_id: int) -> Dict[str, Any]:
        """计算项目赢单率"""
        project = Project.query.get_or_404(project_id)
        
        stakeholders = Stakeholder.query.filter_by(project_id=project_id).all()
        relationships = Relationship.query.filter_by(project_id=project_id).all()
        
        if not stakeholders:
            return {
                'project_id': project_id,
                'project_name': project.name,
                'win_rate': 0,
                'total_stakeholders': 0,
                'weighted_support': 0,
                'key_supporters': [],
                'key_blockers': [],
                'shortest_path': [],
                'breakdown': {}
            }
        
        weighted_support = self._calculate_weighted_support(stakeholders)
        network_score = self._calculate_network_score(stakeholders, relationships)
        momentum_score = self._calculate_momentum_score(project_id)
        role_coverage = self._calculate_role_coverage(stakeholders)
        
        win_rate = self._compute_final_score(
            weighted_support,
            network_score,
            momentum_score,
            role_coverage
        )
        
        key_supporters = sorted(
            [s for s in stakeholders if s.support_level >= 7],
            key=lambda x: x.support_level * x.decision_power,
            reverse=True
        )[:5]
        
        key_blockers = sorted(
            [s for s in stakeholders if s.support_level <= 4],
            key=lambda x: x.decision_power,
            reverse=True
        )[:5]
        
        shortest_path = self._find_shortest_consensus_path(stakeholders, relationships)
        
        return {
            'project_id': project_id,
            'project_name': project.name,
            'win_rate': round(win_rate, 1),
            'total_stakeholders': len(stakeholders),
            'weighted_support': round(weighted_support, 1),
            'network_score': round(network_score, 1),
            'momentum_score': round(momentum_score, 1),
            'role_coverage': round(role_coverage, 1),
            'key_supporters': [self._stakeholder_summary(s) for s in key_supporters],
            'key_blockers': [self._stakeholder_summary(s) for s in key_blockers],
            'shortest_path': shortest_path,
            'breakdown': {
                'weighted_support_weight': 0.4,
                'network_weight': 0.25,
                'momentum_weight': 0.15,
                'role_coverage_weight': 0.2
            }
        }
    
    def _calculate_weighted_support(self, stakeholders: List[Stakeholder]) -> float:
        """计算加权支持度"""
        total_power = sum(s.decision_power for s in stakeholders)
        if total_power == 0:
            return 0
        
        weighted_sum = sum(
            s.support_level * s.decision_power
            for s in stakeholders
        )
        
        return (weighted_sum / total_power) * 10
    
    def _calculate_network_score(self, stakeholders: List[Stakeholder], relationships: List[Relationship]) -> float:
        """计算关系网络得分"""
        if len(stakeholders) <= 1:
            return 50.0
        
        stakeholder_ids = {s.id for s in stakeholders}
        
        connected_nodes = set()
        for r in relationships:
            if r.source_id in stakeholder_ids and r.target_id in stakeholder_ids:
                connected_nodes.add(r.source_id)
                connected_nodes.add(r.target_id)
        
        connectivity = len(connected_nodes) / len(stakeholders) * 100
        
        ally_relationships = [
            r for r in relationships
            if r.relationship_type in ('allies', 'direct_report', 'mentor', 'friend')
        ]
        conflict_relationships = [
            r for r in relationships
            if r.relationship_type == 'conflict'
        ]
        
        if len(relationships) > 0:
            alliance_ratio = len(ally_relationships) / len(relationships) * 100
        else:
            alliance_ratio = 50
        
        network_score = connectivity * 0.6 + alliance_ratio * 0.4
        
        return min(100, max(0, network_score))
    
    def _calculate_momentum_score(self, project_id: int) -> float:
        """计算势头得分（基于状态变更趋势）"""
        from app.models.database import StateChangeLog
        
        recent_logs = StateChangeLog.query.filter_by(
            project_id=project_id,
            attribute_name='support_level'
        ).order_by(StateChangeLog.created_at.desc()).limit(20).all()
        
        if not recent_logs:
            return 50.0
        
        positive_changes = 0
        negative_changes = 0
        
        for log in recent_logs:
            try:
                old_val = float(log.old_value)
                new_val = float(log.new_value)
                if new_val > old_val:
                    positive_changes += 1
                elif new_val < old_val:
                    negative_changes += 1
            except (ValueError, TypeError):
                continue
        
        total_changes = positive_changes + negative_changes
        if total_changes == 0:
            return 50.0
        
        momentum = (positive_changes / total_changes) * 100
        
        return min(100, max(0, momentum))
    
    def _calculate_role_coverage(self, stakeholders: List[Stakeholder]) -> float:
        """计算角色覆盖度"""
        roles_found = set()
        
        key_roles = {
            'decision_maker': ['CEO', 'CTO', 'CIO', 'COO', 'VP', '总监', '总经理', '总裁'],
            'financial': ['CFO', '财务', '预算', '采购'],
            'technical': ['CTO', 'CIO', '技术', '架构', '研发', '工程师', 'IT'],
            'business': ['业务', '产品', '运营', '市场', '销售'],
        }
        
        for stakeholder in stakeholders:
            text = f"{stakeholder.name} {stakeholder.position or ''} {stakeholder.level or ''} {stakeholder.responsibilities or ''}"
            
            for role, keywords in key_roles.items():
                for keyword in keywords:
                    if keyword in text:
                        roles_found.add(role)
                        break
        
        coverage = len(roles_found) / len(key_roles) * 100
        return coverage
    
    def _compute_final_score(
        self,
        weighted_support: float,
        network_score: float,
        momentum_score: float,
        role_coverage: float
    ) -> float:
        """计算最终赢单率"""
        score = (
            weighted_support * 0.4 +
            network_score * 0.25 +
            momentum_score * 0.15 +
            role_coverage * 0.2
        )
        
        return min(100, max(0, score))
    
    def _find_shortest_consensus_path(
        self,
        stakeholders: List[Stakeholder],
        relationships: List[Relationship]
    ) -> List[Dict]:
        """寻找达成共识的最短联结路径"""
        if not stakeholders or len(stakeholders) < 2:
            return []
        
        stakeholder_map = {s.id: s for s in stakeholders}
        stakeholder_ids = set(stakeholder_map.keys())
        
        high_supporters = [
            s for s in stakeholders
            if s.support_level >= 7 and s.decision_power >= 6
        ]
        
        high_power_low_support = [
            s for s in stakeholders
            if s.decision_power >= 7 and s.support_level < 5
        ]
        
        if not high_supporters or not high_power_low_support:
            return []
        
        adjacency = {s.id: [] for s in stakeholders}
        for r in relationships:
            if r.source_id in stakeholder_ids and r.target_id in stakeholder_ids:
                weight = r.influence_weight if r.influence_weight else 0.5
                if r.relationship_type == 'conflict':
                    weight = weight * 0.3
                elif r.relationship_type in ('allies', 'direct_report'):
                    weight = weight * 1.5
                
                adjacency[r.source_id].append((r.target_id, weight))
                adjacency[r.target_id].append((r.source_id, weight))
        
        best_path = None
        best_score = float('-inf')
        
        for supporter in high_supporters[:3]:
            for target in high_power_low_support[:3]:
                path = self._find_path(
                    supporter.id,
                    target.id,
                    adjacency,
                    stakeholder_map
                )
                if path:
                    path_score = sum(node['influence_score'] for node in path)
                    if path_score > best_score:
                        best_score = path_score
                        best_path = path
        
        return best_path if best_path else []
    
    def _find_path(
        self,
        start_id: int,
        end_id: int,
        adjacency: Dict,
        stakeholder_map: Dict
    ) -> List[Dict]:
        """使用BFS寻找路径"""
        if start_id == end_id:
            return []
        
        visited = {start_id}
        queue = deque([(start_id, [start_id])])
        
        while queue:
            current, path = queue.popleft()
            
            for neighbor, weight in adjacency.get(current, []):
                if neighbor in visited:
                    continue
                
                new_path = path + [neighbor]
                
                if neighbor == end_id:
                    result = []
                    for i, node_id in enumerate(new_path):
                        s = stakeholder_map[node_id]
                        result.append({
                            'id': node_id,
                            'name': s.name,
                            'position': s.position,
                            'support_level': s.support_level,
                            'decision_power': s.decision_power,
                            'influence_score': s.support_level * s.decision_power / 100,
                            'is_supporter': s.support_level >= 7,
                            'is_target': i == len(new_path) - 1
                        })
                    return result
                
                visited.add(neighbor)
                queue.append((neighbor, new_path))
        
        return []
    
    def _stakeholder_summary(self, stakeholder: Stakeholder) -> Dict:
        """干系人摘要"""
        return {
            'id': stakeholder.id,
            'name': stakeholder.name,
            'position': stakeholder.position,
            'support_level': stakeholder.support_level,
            'decision_power': stakeholder.decision_power,
            'urgency': stakeholder.urgency,
            'buyer_role': stakeholder.buyer_role,
            'influence_score': stakeholder.support_level * stakeholder.decision_power
        }
