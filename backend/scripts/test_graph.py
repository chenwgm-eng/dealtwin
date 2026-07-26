"""Test the filtered graph API."""
import requests

r = requests.get("http://localhost:5001/api/sales-twin/projects/2/graph")
print(f"Status: {r.status_code}")
data = r.json()
print(f"Has graph: {data.get('has_graph')}")
gd = data.get('graph_data')
if gd:
    nodes = gd.get('nodes', [])
    edges = gd.get('edges', [])
    print(f"Nodes: {len(nodes)}, Edges: {len(edges)}")
    # Show node types
    type_counts = {}
    for n in nodes:
        labels = n.get('labels', [])
        nt = next((l for l in labels if l != 'Entity'), 'Unknown')
        type_counts[nt] = type_counts.get(nt, 0) + 1
    print(f"Node types: {type_counts}")
    # Show first few nodes
    for n in nodes[:5]:
        labels = n.get('labels', [])
        nt = next((l for l in labels if l != 'Entity'), 'Unknown')
        print(f"  {nt}: {n.get('name')} (labels={labels})")
    # Show edge types
    edge_types = {}
    for e in edges:
        et = e.get('name') or e.get('fact_type', 'Unknown')
        edge_types[et] = edge_types.get(et, 0) + 1
    print(f"Edge types: {edge_types}")
else:
    print(f"No graph_data. Message: {data.get('message')}")
    print(f"Error: {data.get('graph_data_error')}")
