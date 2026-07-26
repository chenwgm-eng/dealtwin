"""测试阶段交付物勾选 API"""
import json, urllib.request, urllib.error

BASE = "http://127.0.0.1:5001/api/sales-twin"

# 1. 先获取当前阶段交付物列表，找一个未完成的 key
with urllib.request.urlopen(f"{BASE}/projects/2/stage-deliverables", timeout=30) as r:
    d = json.loads(r.read().decode('utf-8'))

print(f"当前阶段: {d.get('stage')}")
target_key = None
for grp in d.get('deliverables', []):
    for it in grp.get('items', []):
        print(f"  {it.get('key')}: is_completed={it.get('is_completed')} effective={it.get('effective_completed')}")
        if not it.get('is_completed') and not target_key:
            target_key = it.get('key')

if not target_key:
    print("没有未完成的交付物可测试")
    exit()

print(f"\n选择 target_key = {target_key}")

# 2. PUT 勾选
payload = {"is_completed": True, "notes": "测试勾选"}
req = urllib.request.Request(
    f"{BASE}/projects/2/stage-deliverables/{target_key}",
    data=json.dumps(payload).encode('utf-8'),
    headers={'Content-Type': 'application/json'},
    method='PUT'
)
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        result = json.loads(r.read().decode('utf-8'))
        print(f"PUT 成功: {json.dumps(result, ensure_ascii=False)[:300]}")
except urllib.error.HTTPError as e:
    print(f"PUT 失败 HTTP {e.code}: {e.read()[:300]}")
except Exception as e:
    print(f"PUT 异常: {e}")

# 3. 再 GET 确认
with urllib.request.urlopen(f"{BASE}/projects/2/stage-deliverables", timeout=30) as r:
    d2 = json.loads(r.read().decode('utf-8'))
for grp in d2.get('deliverables', []):
    for it in grp.get('items', []):
        if it.get('key') == target_key:
            print(f"验证: is_completed={it.get('is_completed')} effective={it.get('effective_completed')}")
            break

# 4. 取消勾选恢复原状
req2 = urllib.request.Request(
    f"{BASE}/projects/2/stage-deliverables/{target_key}",
    data=json.dumps({"is_completed": False, "notes": ""}).encode('utf-8'),
    headers={'Content-Type': 'application/json'},
    method='PUT'
)
try:
    with urllib.request.urlopen(req2, timeout=30) as r:
        print(f"恢复成功")
except Exception as e:
    print(f"恢复失败: {e}")
