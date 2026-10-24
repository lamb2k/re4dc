from pathlib import Path
import hashlib,json,subprocess
source='4be08e0110592510e3630c01fa9f49b3ac2fed3d';ref='5e4de9a0262d3629c9833c959557de198b2e9f0c'
o=Path('/root/probe/lanes/route/out-dd23cur4be08e01offrT');b=Path('/root/probe/lanes/route/out-au23on5e4drT')
ev=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/dedup-offline23-20261023/current-4be08e01')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert (o/'stack.txt').read_text().splitlines()==[source] and (b/'stack.txt').read_text().splitlines()==[ref]
def knobs(d):return dict(s.split('=',1) for s in (d/'resolved-knobs.txt').read_text().splitlines() if '=' in s)
ko,kb=knobs(o),knobs(b)
def norm(v,d,t):return v.replace(str(d),'@OUT@').replace(t,'@TREE@')
no={k:norm(v,o,'/root/work/lanes/dedup-offline23-current-d5c') for k,v in ko.items()}
nb={k:norm(v,b,'/root/work/lanes/audits23-target-on') for k,v in kb.items()}
diff={k:[nb.get(k),no.get(k)] for k in set(nb)|set(no) if nb.get(k)!=no.get(k)}
assert not diff,sorted(diff)
rows={}
for name,d in [('reference',b),('currentoff',o)]:
    raw=Path('/dev/shm')/('dedup4be-trace-identity-'+name+'.bin');assert not raw.exists()
    subprocess.run(['/opt/toolchains/dc/sh-elf/bin/sh-elf-objcopy','-R','.stack','-O','binary',str(d/'re4dc-game.elf'),str(raw)],check=True)
    ovls={p.name:sha(p) for p in d.glob('*.ovl')};assert len(ovls)==14
    rows[name]=dict(path=str(d),raw_sha256=sha(raw),overlays=ovls,knobs_sha256=sha(d/'resolved-knobs.txt'),stack_sha256=sha(d/'stack.txt'),elf_sha256=sha(d/'re4dc-game.elf'))
assert rows['currentoff']['raw_sha256']==rows['reference']['raw_sha256']
assert rows['currentoff']['overlays']==rows['reference']['overlays']
(ev/'current-off-trace-identity.json').write_text(json.dumps(dict(status='PASS_ACTUAL_OFF_TRACE_MAIN_AND_ALL14_IDENTITY',source=source,reference_source=ref,programmes=rows,normalized_resolved_differences=diff,reuse='Qualified5e bell/Mendez baseline capture eligible only after additional exact fixture/data/capture binding; reuse is not a fresh guest'),indent=2)+'\n')
print('CURRENT_OFF_TRACE_MAIN_ALL14_IDENTITY_PASS',rows['currentoff']['raw_sha256'])
