# 验证数据结构
import json

with open(r'c:\myapp\data\errors.jsonl', 'r', encoding='utf-8') as f:
    for line in f:
        d = json.loads(line.strip())
        print(f"type={d.get('type')}, fields={list(d.keys())}")
        if d.get('type') == 'note':
            print(f"  note content: {json.dumps(d, ensure_ascii=False)[:200]}")