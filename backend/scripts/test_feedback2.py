import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app, db
from app.models.database import Stakeholder
from app.services.feedback_parser import FeedbackParserService

app = create_app()
with app.app_context():
    stakeholders = Stakeholder.query.filter_by(project_id=1).all()
    print("Stakeholders:")
    for s in stakeholders:
        print(f"  {s.id}: {s.name} ({s.position}) support={s.support_level}")
    
    parser = FeedbackParserService()
    
    print("\n=== Test 1: CFO顾虑 ===")
    feedback1 = "今天见了CFO李明，他担心成本太高，对预算控制有顾虑"
    result = parser.parse_feedback(1, feedback1)
    print(f"Changes: {result['total_changes']}")
    for u in result['parsed_updates']:
        print(f"  {u['stakeholder_name']} {u['attribute']}: {u['old_value']} -> {u['new_value']}")
    
    print("\n=== Test 2: 王芳紧迫感 ===")
    feedback2 = "王芳说项目很紧急，需要尽快推进"
    result = parser.parse_feedback(1, feedback2)
    print(f"Changes: {result['total_changes']}")
    for u in result['parsed_updates']:
        print(f"  {u['stakeholder_name']} {u['attribute']}: {u['old_value']} -> {u['new_value']}")
    
    print("\n=== State Logs ===")
    logs = parser.get_state_logs(1, limit=10)
    print(f"Total logs: {logs['total']}")
    for log in logs['logs']:
        print(f"  {log['change_object']} {log['attribute_name']}: {log['old_value']} -> {log['new_value']}")
