import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app, db
from app.models.database import Stakeholder

app = create_app()
with app.app_context():
    stakeholders = Stakeholder.query.all()
    for s in stakeholders:
        print(f"ID: {s.id}, Name: {s.name}, Position: {s.position}, Support: {s.support_level}")
    
    print("\n--- Testing rule-based parsing ---")
    from app.services.feedback_parser import FeedbackParserService
    parser = FeedbackParserService()
    
    stakeholders = Stakeholder.query.filter_by(project_id=1).all()
    feedback = "今天见了CTO张三，聊了降本方案，他同意了但怕系统崩溃，对系统稳定性有顾虑"
    
    print(f"Feedback: {feedback}")
    result = parser._parse_with_rules(feedback, stakeholders)
    print(f"Updates found: {len(result['updates'])}")
    for u in result['updates']:
        print(f"  - {u['stakeholder_name']} {u['attribute']}: {u['old_value']} -> {u['new_value']}")
