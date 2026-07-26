"""验证项目列表和阶段检查"""
import json, urllib.request, urllib.error

BASE = "http://127.0.0.1:5001/api/sales-twin"

# 1. 项目列表
print("=== 项目列表 ===")
with urllib.request.urlopen(f"{BASE}/projects?page=1&per_page=20", timeout=30) as r:
    d = json.loads(r.read().decode('utf-8'))
    for p in d.get('items', []):
        print(f"  #{p['id']} name={repr(p.get('name'))} stage={p.get('sales_stage')}")
    print(f"  total={d.get('total')}")

# 2. 阶段检查（POST）
print("\n=== 阶段检查 POST ===")
req = urllib.request.Request(
    f"{BASE}/projects/2/stage-check",
    data=json.dumps({"stage": "define"}).encode('utf-8'),
    headers={'Content-Type': 'application/json'},
    method='POST'
)
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        result = json.loads(r.read().decode('utf-8'))
        print(f"  ready: {result.get('ready')}")
        print(f"  can_advance: {result.get('can_advance')}")
        print(f"  completion_rate: {result.get('completion_rate')}")
        print(f"  recommendation: {result.get('recommendation')}")
        print(f"  total_items: {result.get('total_items')}")
        print(f"  completed_items: {result.get('completed_items')}")
except urllib.error.HTTPError as e:
    print(f"  HTTP ERROR {e.code}: {e.read()[:300]}")

# 3. 阶段检查（GET，如果支持）
print("\n=== 阶段检查 GET ?stage=define ===")
try:
    with urllib.request.urlopen(f"{BASE}/projects/2/stage-check?stage=define", timeout=30) as r:
        result = json.loads(r.read().decode('utf-8'))
        print(f"  ready: {result.get('ready')}")
        print(f"  can_advance: {result.get('can_advance')}")
except urllib.error.HTTPError as e:
    print(f"  HTTP ERROR {e.code}: {e.read()[:200]}")
