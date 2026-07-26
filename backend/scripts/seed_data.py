import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app, db
from app.models.database import Stakeholder, Project

app = create_app()
with app.app_context():
    project = Project.query.first()
    print(f"Project: {project.id} - {project.name}")
    
    s = Stakeholder(
        project_id=project.id,
        name="李明",
        position="CFO",
        level="高管",
        responsibilities="负责公司财务和预算",
        personal_agenda="降低运营成本，控制预算",
        buyer_role="blocker",
        decision_power=9,
        support_level=3,
        urgency=5
    )
    db.session.add(s)
    db.session.commit()
    print(f"Created stakeholder: {s.id} - {s.name}")
    
    s2 = Stakeholder(
        project_id=project.id,
        name="王芳",
        position="业务总监",
        level="中层",
        responsibilities="负责业务线运营",
        personal_agenda="提升业务效率，争取更多资源",
        buyer_role="mobilizer",
        decision_power=6,
        support_level=8,
        urgency=7
    )
    db.session.add(s2)
    db.session.commit()
    print(f"Created stakeholder: {s2.id} - {s2.name}")
    
    print("\nAll stakeholders:")
    for s in Stakeholder.query.filter_by(project_id=1).all():
        print(f"  {s.id}: {s.name} ({s.position}) - support={s.support_level}, power={s.decision_power}")
