import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app, db
from app.services.win_rate_calculator import WinRateCalculator

app = create_app()
with app.app_context():
    calculator = WinRateCalculator()
    result = calculator.calculate_win_rate(1)
    
    print(f"Project: {result['project_name']}")
    print(f"Win Rate: {result['win_rate']}%")
    print(f"Total Stakeholders: {result['total_stakeholders']}")
    print(f"\nBreakdown:")
    print(f"  Weighted Support: {result['weighted_support']} (weight: {result['breakdown']['weighted_support_weight']})")
    print(f"  Network Score: {result['network_score']} (weight: {result['breakdown']['network_weight']})")
    print(f"  Momentum Score: {result['momentum_score']} (weight: {result['breakdown']['momentum_weight']})")
    print(f"  Role Coverage: {result['role_coverage']} (weight: {result['breakdown']['role_coverage_weight']})")
    
    print(f"\nKey Supporters:")
    for s in result['key_supporters']:
        print(f"  {s['name']} ({s['position']}) - support={s['support_level']}, power={s['decision_power']}")
    
    print(f"\nKey Blockers:")
    for s in result['key_blockers']:
        print(f"  {s['name']} ({s['position']}) - support={s['support_level']}, power={s['decision_power']}")
    
    print(f"\nShortest Consensus Path:")
    if result['shortest_path']:
        for i, node in enumerate(result['shortest_path']):
            marker = "→" if i > 0 else " "
            print(f"  {marker} {node['name']} ({node['position']}) - support={node['support_level']}")
    else:
        print("  No path found")
