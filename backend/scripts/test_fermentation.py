import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app, db
from app.models.database import Stakeholder, Relationship
from app.services.fermentation_simulator import FermentationSimulator

app = create_app()
with app.app_context():
    project_id = 1
    
    existing = Relationship.query.filter_by(project_id=project_id).all()
    if not existing:
        r1 = Relationship(
            project_id=project_id,
            source_id=2,
            target_id=3,
            relationship_type='conflict',
            influence_weight=0.8
        )
        db.session.add(r1)
        
        r2 = Relationship(
            project_id=project_id,
            source_id=3,
            target_id=1,
            relationship_type='allies',
            influence_weight=0.7
        )
        db.session.add(r2)
        
        db.session.commit()
        print("添加了关系数据")
    else:
        print(f"已有 {len(existing)} 条关系数据")
    
    print("\n=== 闭门发酵模拟（3天）===")
    simulator = FermentationSimulator()
    result = simulator.simulate_fermentation(project_id, days=3)
    
    print(f"项目：{result['project_name']}")
    print(f"模拟天数：{result['days']}天")
    print(f"结论：{result['conclusion']}")
    print(f"趋势：初始{result['trend']['initial_avg']} → 最终{result['trend']['final_avg']} ({'+' if result['trend']['change'] > 0 else ''}{round(result['trend']['change'], 1)})")
    
    print("\n各轮状态：")
    for h in result['history']:
        print(f"\n  [{h['label']}] 加权平均支持度: {h['average_support']}")
        for s in h['states']:
            print(f"    {s['name']:8s} ({s['position']:6s}) support={s['support_level']:.1f}, role={s['buyer_role']}")
