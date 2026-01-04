import json
from pathlib import Path

# 모든 n8n JSON 파일
files = list(Path('D:/workspace/news').glob('n8n_*.json'))

for f in files:
    try:
        data = json.loads(f.read_text(encoding='utf-8'))
        modified = False
        
        for node in data.get('nodes', []):
            if node.get('type') == 'n8n-nodes-base.executeCommand':
                params = node.get('parameters', {})
                # timeout 없으면 추가 (1시간 = 3600000ms)
                if 'options' not in params:
                    params['options'] = {}
                if 'timeout' not in params['options']:
                    params['options']['timeout'] = 3600000
                    modified = True
                    print(f"  Added timeout to: {node.get('name', 'unknown')}")
        
        if modified:
            f.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
            print(f"Updated: {f.name}")
        else:
            print(f"No change: {f.name}")
    except Exception as e:
        print(f"Error {f.name}: {e}")
