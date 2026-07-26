"""查看 HTTP 原始返回"""
import json, urllib.request

req = urllib.request.Request(
    "http://127.0.0.1:5001/api/sales-twin/projects/2/stage-check",
    data=json.dumps({"stage": "define"}).encode('utf-8'),
    headers={'Content-Type': 'application/json'},
    method='POST'
)
with urllib.request.urlopen(req, timeout=30) as r:
    raw = r.read().decode('utf-8')
    print("原始返回:")
    print(raw)
    print("\n解析后:")
    d = json.loads(raw)
    print(f"  keys: {list(d.keys())}")
    print(f"  ready: {d.get('ready')}")
    print(f"  can_advance: {d.get('can_advance')}")
