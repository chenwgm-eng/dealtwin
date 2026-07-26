"""检查脏数据"""
import json, urllib.request

BASE = "http://127.0.0.1:5001/api/sales-twin"

# 项目列表
with urllib.request.urlopen(f"{BASE}/projects?page=1&per_page=20", timeout=30) as r:
    d = json.loads(r.read().decode('utf-8'))
print("=== 项目列表 ===")
for p in d.get('items', []):
    name_repr = repr(p.get('name'))
    print(f"  #{p['id']} name={name_repr} stage={p.get('sales_stage')}")

# 项目1 的任务
print("\n=== 项目1 的任务 ===")
try:
    with urllib.request.urlopen(f"{BASE}/projects/1/tasks", timeout=30) as r:
        d = json.loads(r.read().decode('utf-8'))
        arr = d.get('tasks', [])
        for t in arr:
            print(f"  #{t['id']} title={repr(t.get('title'))}")
except Exception as e:
    print(f"  ERROR: {e}")

# 项目1 的反馈
print("\n=== 项目1 的反馈 ===")
try:
    with urllib.request.urlopen(f"{BASE}/projects/1/feedback-records", timeout=30) as r:
        d = json.loads(r.read().decode('utf-8'))
        arr = d if isinstance(d, list) else d.get('feedback_records', d.get('records', []))
        for f in arr:
            print(f"  #{f['id']} text={repr((f.get('feedback_text') or '')[:80])}")
except Exception as e:
    print(f"  ERROR: {e}")

# 项目2 的任务（检查是否有乱码）
print("\n=== 项目2 的任务 ===")
with urllib.request.urlopen(f"{BASE}/projects/2/tasks", timeout=30) as r:
    d = json.loads(r.read().decode('utf-8'))
    arr = d.get('tasks', [])
    for t in arr:
        print(f"  #{t['id']} title={repr(t.get('title'))}")

# 项目2 的反馈（检查是否有乱码）
print("\n=== 项目2 的反馈 ===")
with urllib.request.urlopen(f"{BASE}/projects/2/feedback-records", timeout=30) as r:
    d = json.loads(r.read().decode('utf-8'))
    arr = d if isinstance(d, list) else d.get('feedback_records', d.get('records', []))
    for f in arr:
        print(f"  #{f['id']} text={repr((f.get('feedback_text') or '')[:80])}")
