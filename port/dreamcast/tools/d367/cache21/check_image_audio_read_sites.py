#!/usr/bin/env python3
"""Check audited source citation spans; this is not semantic or gameplay verification."""
from pathlib import Path
import json,hashlib
root=Path(__file__).resolve().parents[5];p=Path(__file__).with_name('image-audio-read-sites.json');j=json.loads(p.read_text())
ids={}
for r in j['pins']:
 s=(root/r['path']).read_text();assert s.count(r['needle'])==1,r['id'];v=''.join(s[s.index(r['needle']):].splitlines(keepends=True)[:r['lines']]);assert hashlib.sha256(v.encode()).hexdigest()==r['sha256'],r['id'];ids[r['id']]=True
for r in j['sites']:
 assert all(k in ids for k in r['pins']),r['id'];assert all(r[k] for k in ['caller','file','owner','lifetime','classification','remaining_verify']),r['id']
print(f"PASS {len(ids)} source citation spans / {len(j['sites'])} classified sites; runtime gaps remain OPEN")
