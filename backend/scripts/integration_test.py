"""
系统集成测试 - B2B销售数字孪生
验证所有核心API是否正常工作
"""

import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app, db
from app.models.database import Project, Stakeholder, Relationship

app = create_app()

def run_tests():
    with app.test_client() as client:
        print("=" * 60)
        print("B2B销售数字孪生 - 系统集成测试")
        print("=" * 60)
        
        passed = 0
        failed = 0
        
        # 1. 健康检查
        print("\n1. 健康检查")
        try:
            resp = client.get('/health')
            assert resp.status_code == 200
            data = resp.get_json()
            print(f"   ✓ 状态: {data.get('status')}")
            passed += 1
        except Exception as e:
            print(f"   ✗ 失败: {e}")
            failed += 1
        
        # 2. 项目管理
        print("\n2. 项目管理")
        try:
            resp = client.post('/api/sales-twin/projects', json={
                'name': '集成测试项目',
                'sales_stage': 'suspect',
                'budget': 500000,
                'industry': '制造业',
                'business_pain_points': '供应链效率低下，成本控制困难'
            })
            assert resp.status_code == 200
            project = resp.get_json()['project']
            project_id = project['id']
            print(f"   ✓ 创建项目: {project['name']} (ID: {project_id})")
            passed += 1
        except Exception as e:
            print(f"   ✗ 创建项目失败: {e}")
            failed += 1
            return
        
        try:
            resp = client.get('/api/sales-twin/projects')
            assert resp.status_code == 200
            data = resp.get_json()
            print(f"   ✓ 获取项目列表: {len(data['projects'])} 个项目")
            passed += 1
        except Exception as e:
            print(f"   ✗ 获取项目列表失败: {e}")
            failed += 1
        
        # 3. 干系人管理
        print("\n3. 干系人管理")
        try:
            resp = client.post(f'/api/sales-twin/projects/{project_id}/stakeholders', json={
                'name': '张总',
                'position': 'CEO',
                'level': '高管',
                'buyer_role': 'champion',
                'support_level': 5,
                'decision_power': 10,
                'responsibilities': '公司战略决策',
                'personal_agenda': '提升公司竞争力'
            })
            assert resp.status_code == 200
            sh1 = resp.get_json()['stakeholder']
            print(f"   ✓ 添加干系人: {sh1['name']} ({sh1['position']})")
            passed += 1
        except Exception as e:
            print(f"   ✗ 添加干系人失败: {e}")
            failed += 1
        
        try:
            resp = client.post(f'/api/sales-twin/projects/{project_id}/stakeholders', json={
                'name': '李经理',
                'position': 'IT经理',
                'level': '中层',
                'buyer_role': 'mobilizer',
                'support_level': 8,
                'decision_power': 5,
                'responsibilities': '负责IT系统建设'
            })
            assert resp.status_code == 200
            sh2 = resp.get_json()['stakeholder']
            print(f"   ✓ 添加干系人: {sh2['name']} ({sh2['position']})")
            passed += 1
        except Exception as e:
            print(f"   ✗ 添加干系人失败: {e}")
            failed += 1
        
        try:
            resp = client.get(f'/api/sales-twin/projects/{project_id}/stakeholders')
            assert resp.status_code == 200
            data = resp.get_json()
            print(f"   ✓ 获取干系人列表: {len(data['stakeholders'])} 人")
            passed += 1
        except Exception as e:
            print(f"   ✗ 获取干系人失败: {e}")
            failed += 1
        
        # 4. 关系管理
        print("\n4. 关系管理")
        try:
            resp = client.post(f'/api/sales-twin/projects/{project_id}/relationships', json={
                'source_id': sh1['id'],
                'target_id': sh2['id'],
                'relationship_type': 'direct_report',
                'influence_weight': 0.8
            })
            assert resp.status_code == 200
            print(f"   ✓ 创建关系: {sh1['name']} → {sh2['name']}")
            passed += 1
        except Exception as e:
            print(f"   ✗ 创建关系失败: {e}")
            failed += 1
        
        try:
            resp = client.get(f'/api/sales-twin/projects/{project_id}/relationships')
            assert resp.status_code == 200
            data = resp.get_json()
            print(f"   ✓ 获取关系列表: {len(data['relationships'])} 条")
            passed += 1
        except Exception as e:
            print(f"   ✗ 获取关系失败: {e}")
            failed += 1
        
        # 5. 盲区扫描
        print("\n5. 盲区扫描")
        try:
            resp = client.post(f'/api/sales-twin/projects/{project_id}/scan')
            assert resp.status_code == 200
            data = resp.get_json()
            print(f"   ✓ 盲区扫描: 发现 {len(data.get('blind_spots', []))} 个盲区")
            for spot in data.get('blind_spots', [])[:3]:
                print(f"      - {spot['role_name']}: {spot['description']}")
            passed += 1
        except Exception as e:
            print(f"   ✗ 盲区扫描失败: {e}")
            failed += 1
        
        # 6. 下一步行动建议
        print("\n6. 下一步行动建议")
        try:
            resp = client.post(f'/api/sales-twin/projects/{project_id}/next-best-action')
            assert resp.status_code == 200
            data = resp.get_json()
            print(f"   ✓ 行动建议: {len(data.get('recommended_actions', []))} 条")
            for action in data.get('recommended_actions', [])[:2]:
                print(f"      - P{action['priority']}: {action['title']}")
            passed += 1
        except Exception as e:
            print(f"   ✗ 行动建议失败: {e}")
            failed += 1
        
        # 7. 赢单率预测
        print("\n7. 赢单率预测")
        try:
            resp = client.get(f'/api/sales-twin/projects/{project_id}/win-rate')
            assert resp.status_code == 200
            data = resp.get_json()
            print(f"   ✓ 赢单率: {data['win_rate']}%")
            print(f"      加权支持度: {data['weighted_support']}")
            print(f"      角色覆盖: {data['role_coverage']}%")
            passed += 1
        except Exception as e:
            print(f"   ✗ 赢单率预测失败: {e}")
            failed += 1
        
        # 8. 反馈解析
        print("\n8. 反馈解析")
        try:
            resp = client.post(f'/api/sales-twin/projects/{project_id}/feedback', json={
                'feedback': '今天和李经理聊了，他对方案非常认可，觉得能解决他们的大问题，而且很紧急希望尽快推进'
            })
            assert resp.status_code == 200
            data = resp.get_json()
            print(f"   ✓ 反馈解析: {data['total_changes']} 项变更")
            print(f"      摘要: {data.get('summary', '无')}")
            passed += 1
        except Exception as e:
            print(f"   ✗ 反馈解析失败: {e}")
            failed += 1
        
        # 9. 状态变更日志
        print("\n9. 状态变更日志")
        try:
            resp = client.get(f'/api/sales-twin/projects/{project_id}/state-logs?limit=10')
            assert resp.status_code == 200
            data = resp.get_json()
            print(f"   ✓ 状态日志: {data['total']} 条记录")
            passed += 1
        except Exception as e:
            print(f"   ✗ 状态日志失败: {e}")
            failed += 1
        
        # 10. 闭门发酵模拟
        print("\n10. 闭门发酵模拟")
        try:
            resp = client.post(f'/api/sales-twin/projects/{project_id}/fermentation', json={
                'days': 3
            })
            assert resp.status_code == 200
            data = resp.get_json()
            print(f"   ✓ 发酵模拟: {data['days']}天, {data['rounds']}轮")
            print(f"      趋势: {data['trend']['initial_avg']:.1f} → {data['trend']['final_avg']:.1f}")
            print(f"      结论: {data['conclusion'][:50]}...")
            passed += 1
        except Exception as e:
            print(f"   ✗ 发酵模拟失败: {e}")
            failed += 1
        
        # 总结
        print("\n" + "=" * 60)
        print(f"测试结果: 通过 {passed} 项, 失败 {failed} 项")
        print(f"通过率: {passed / (passed + failed) * 100:.1f}%")
        print("=" * 60)
        
        return failed == 0

if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
