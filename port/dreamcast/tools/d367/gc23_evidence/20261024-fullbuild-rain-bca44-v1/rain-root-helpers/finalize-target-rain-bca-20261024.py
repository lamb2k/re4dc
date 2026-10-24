from pathlib import Path
import json,hashlib
rroot=Path(r'\\wsl.localhost\Ubuntu-24.04\dev\shm\rain-r10c-bca44-target-1yuvytg3')
e=Path(r'C:\Flycast-Evidence\re4-dreamcast\water-rain24\rain-target-bca44-current');e.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
r=json.loads((rroot/'report.json').read_text());assert r['complete'] and r['baseline_absent_zero_identical'] and len(r['objects'])==4
for row in r['objects']:
 stem=row['arm'];assert sha(rroot/(stem+'.o'))==row['sha256'] and sha(rroot/(stem+'-nodebug.o'))==row['nodebug_sha256']
for p in rroot.iterdir():
 if p.is_file() and p.suffix in ('.json','.log','.su','.txt','.d'):(e/p.name).write_bytes(p.read_bytes())
size=lambda row:list(map(int,row['size'].splitlines()[-1].split()[:3]))
delta=[b-a for a,b in zip(size(r['objects'][0]),size(r['objects'][-1]))]
base=set((rroot/'baseline-undefined.txt').read_text().splitlines());on=set((rroot/'on-undefined.txt').read_text().splitlines())
new=sorted(on-base)
actual=Path(r'\\wsl.localhost\Ubuntu-24.04\root\work\lanes\gc-port23-full-target2-scratch\off\symbols.txt').read_text().splitlines()
providers={name:[line for line in actual if line.split()[-1]==name.split()[-1]] for name in new}
assert all(v for v in providers.values())
s=dict(status='SH4_TRANSLATION_UNIT_COMPLETE_ONLY',source=r['source'],baseline_source=r['baseline_source'],off_identity=True,delta=dict(zip(['text','data','bss'],delta)),extra_import_actual_baseline_providers=providers,scope='Actual current rP compiler flags, four target arms and exact per-input pins. Full rain link/guest/lifecycle/stills/memory/performance/appearance/PS2 ancestry remain unqualified. This is not a performance improvement.')
(e/'SUMMARY.json').write_text(json.dumps(s,indent=2)+'\n')
(e/'SHA256-MANIFEST.json').write_text(json.dumps({p.name:dict(bytes=p.stat().st_size,sha256=sha(p)) for p in e.iterdir() if p.is_file() and p.name!='SHA256-MANIFEST.json'},indent=2)+'\n')
print(json.dumps(s,indent=2))