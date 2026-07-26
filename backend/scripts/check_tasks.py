"""检查任务字段"""
import json, urllib.request
with urllib.request.urlopen("http://127.0.0.1:5001/api/sales-twin/projects/2/tasks", timeout=30) as r:
    d = json.loads(r.read().decode('utf-8'))
arr = d.get('tasks', [])
for t in arr:
    print(f"id={t['id']} priority={t.get('priority')!r} status={t.get('status')!r} source={t.get('source')!r} task_type={t.get('task_type')!r} stakeholder_name={t.get('stakeholder_name')!r}")
