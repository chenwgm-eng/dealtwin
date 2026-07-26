import sys, os, io, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import create_app
from werkzeug.datastructures import FileStorage

app = create_app()
with app.test_client() as c:
    text = 'This is a test document about ACME Corporation. John Smith is the CEO. Jane Doe is the CTO. They are planning to purchase new software.'
    f = FileStorage(stream=io.BytesIO(text.encode('utf-8')), filename='test.txt', content_type='text/plain')

    r = c.post('/api/graph/ontology/generate', data={
        'files': f,
        'simulation_requirement': 'Analyze ACME Corp organization structure',
        'project_name': 'Test'
    }, content_type='multipart/form-data')

    print(f'Status: {r.status_code}')
    data = r.get_json()
    if data.get('traceback'):
        print('TRACEBACK:')
        print(data['traceback'])
    elif data.get('success'):
        print('SUCCESS!')
        ont = data['data']['ontology']
        etypes = ont.get('entity_types', [])
        edtypes = ont.get('edge_types', [])
        print(f'Entity types: {len(etypes)}')
        print(f'Edge types: {len(edtypes)}')
        for et in etypes[:3]:
            name = et.get('name', '?')
            desc = et.get('description', '')[:60]
            print(f'  - {name}: {desc}')
    else:
        print(json.dumps(data, indent=2, ensure_ascii=False))
