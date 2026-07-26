"""检查图谱节点字段"""
import json, urllib.request
with urllib.request.urlopen("http://127.0.0.1:5001/api/sales-twin/projects/2/graph", timeout=30) as r:
    d = json.loads(r.read().decode('utf-8'))
gd = d.get('graph_data') or {}
nodes = gd.get('nodes', [])
edges = gd.get('edges', [])
print(f"nodes: {len(nodes)}  edges: {len(edges)}")
print("\n--- 第一个节点的所有字段 ---")
if nodes:
    n = nodes[0]
    print(f"keys: {list(n.keys())}")
    print(json.dumps(n, ensure_ascii=False, indent=2))
print("\n--- 第一条边的所有字段 ---")
if edges:
    e = edges[0]
    print(f"keys: {list(e.keys())}")
    print(json.dumps(e, ensure_ascii=False, indent=2))
print("\n--- 所有节点 uuid 字段是否存在 ---")
for n in nodes[:5]:
    print(f"  uuid={n.get('uuid')!r}  id={n.get('id')!r}  name={n.get('name')!r}  labels={n.get('labels')}")
print("\n--- 所有边 source/target 字段 ---")
for e in edges[:5]:
    print(f"  source_node_uuid={e.get('source_node_uuid')!r}  target_node_uuid={e.get('target_node_uuid')!r}  source={e.get('source')!r}  target={e.get('target')!r}  fact_type={e.get('fact_type')!r}")
