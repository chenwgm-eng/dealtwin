"""快速验证 graph API 修复"""
import json, urllib.request
with urllib.request.urlopen("http://127.0.0.1:5001/api/sales-twin/projects/2/graph", timeout=30) as r:
    d = json.loads(r.read().decode('utf-8'))
print('has_graph:', d.get('has_graph'))
print('status:', d.get('status'))
print('graph_data_error:', d.get('graph_data_error'))
gd = d.get('graph_data') or {}
print('graph_data nodes:', len(gd.get('nodes', [])))
print('graph_data edges:', len(gd.get('edges', [])))
for n in gd.get('nodes', [])[:15]:
    labels = n.get('labels') or []
    attrs = n.get('attributes') or {}
    name = attrs.get('name') or attrs.get('title') or '?'
    label = attrs.get('node_type_label') or (labels[0] if labels else '?')
    print(f"  [{label}] {name}")
print('---')
for e in gd.get('edges', [])[:10]:
    print(f"  {e.get('type')} {e.get('source')} -> {e.get('target')}")
