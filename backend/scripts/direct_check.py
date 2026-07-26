"""直接调用 check_stage_readiness 验证"""
import sys
sys.path.insert(0, r'd:\BattleFish\MiroFish\backend')
from app import create_app, db
from app.services.stage_deliverable_manager import check_stage_readiness

app = create_app()
with app.app_context():
    result = check_stage_readiness(2, stage='define')
    print("直接调用 check_stage_readiness(2, stage='define'):")
    print(f"  type: {type(result)}")
    print(f"  keys: {list(result.keys()) if result else 'None'}")
    print(f"  ready: {result.get('ready') if result else 'N/A'}")
    print(f"  can_advance: {result.get('can_advance') if result else 'N/A'}")
    print(f"  completion_rate: {result.get('completion_rate') if result else 'N/A'}")
