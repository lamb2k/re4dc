#!/usr/bin/env bash
set -euo pipefail
python3 - <<'PY'
import pathlib,json,re
r=pathlib.Path('/mnt/c/Flycast-Evidence/re4-dreamcast/stat-bytes23/takeover-2a14662d');out={}
for n in ['boot','warp','h2']:
 p=r/('qa-'+n+'-r1');run=json.loads((p/'run-result.json').read_text());bound=json.loads((p/'bounded-launch.json').read_text());s=(p/'run-output.txt').read_text(errors='replace').replace('\0','')
 good=run.get('stopped')=='goal' and not run['errors'] and not bound['deadline_fired'] and not re.search(r'HALT|FAULT|MISSING|Out of memory',s)
 if n=='boot':good=good and bool(run['key_log']) and all(x['windows']>0 for x in run['key_log']) and 'phase=enter room=' in s
 if n=='warp':good=good and 'phase=enter room=103' in s
 m=re.findall(r'route movie terminal=1 id=10030 frames=(\d+)/(\d+)[^\n]*heap_before=(\d+)',s)
 if n=='h2':good=good and bool(m) and m[-1][:2]==('340','340')
 out[n]={'pass':bool(good),'elapsed_s':run['elapsed_s'],'deadline_fired':bound['deadline_fired'],'key_log':run['key_log'],'s30':m[-1] if m else None,'selftest_match':'STATDIAG selftest match' in s}
 assert good,(n,out[n])
(r/'qa-probes-results.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
PY
