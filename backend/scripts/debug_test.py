import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app

app = create_app()

with app.test_client() as client:
    resp = client.post('/api/sales-twin/projects', json={
        'name': '集成测试项目',
        'sales_stage': 'suspect',
        'budget': 500000,
        'industry': '制造业',
        'business_pain_points': '供应链效率低下，成本控制困难'
    })
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.get_data(as_text=True)}")
