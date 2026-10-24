from pathlib import Path
import hashlib,json,subprocess
tree=Path('/root/work/lanes/dedup-offline23-current-d5c');source='4be08e0110592510e3630c01fa9f49b3ac2fed3d';base='d5c1ceab9e06461462669b3ce1d28a379747a74a'
o=Path('/root/probe/lanes/route/out-dd23cur4be08e01offrP');b=Path('/root/probe/lanes/route/out-au23ld5c1rP')
ev=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/dedup-offline23-20261023/current-4be08e01')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert (o/'stack.txt').read_text().splitlines()==[source];assert (b/'stack.txt').read_text().splitlines()==[base]
assert not (o/'missing.txt').read_bytes() and not (b/'missing.txt').read_bytes()
def knobs(p):return dict(x.split('=',1) for x in p.read_text().splitlines() if '=' in x)
ko,kb=knobs(o/'resolved-knobs.txt'),knobs(b/'resolved-knobs.txt')
assert ko['SCENERY_DEDUP']=='0'
def norm(v,out,tr):return v.replace(str(out),'@OUT@').replace(tr,'@TREE@') if isinstance(v,str) else v
nb={k:norm(v,b,'/root/work/lanes/audits23-land') for k,v in kb.items()};no={k:norm(v,o,str(tree)) for k,v in ko.items()}
diff={k:[nb.get(k),no.get(k)] for k in set(nb)|set(no) if nb.get(k)!=no.get(k)}
assert not diff,sorted(diff)
rows={}
for label,d in [('baseline',b),('currentoff',o)]:
 raw=Path('/dev/shm')/('dedup4be-off-identity-'+label+'.bin')
 assert not raw.exists()
 subprocess.run(['/opt/toolchains/dc/sh-elf/bin/sh-elf-objcopy','-R','.stack','-O','binary',str(d/'re4dc-game.elf'),str(raw)],check=True)
 ovls={p.name:sha(p) for p in d.glob('*.ovl')};assert len(ovls)==14
 rows[label]=dict(path=str(d),stack_sha256=sha(d/'stack.txt'),resolved_sha256=sha(d/'resolved-knobs.txt'),elf_sha256=sha(d/'re4dc-game.elf'),raw_sha256=sha(raw),raw_bytes=raw.stat().st_size,overlays=ovls)
assert rows['baseline']['raw_sha256']==rows['currentoff']['raw_sha256']=='49a4173a1792823ff5e275b0681b2c354c4e45140b7078d87c1253f2e926090b'
assert rows['baseline']['overlays']==rows['currentoff']['overlays']
report=dict(status='PASS_ACTUAL_CURRENT_OFF_MAIN_AND_ALL14_IDENTITY',source=source,baseline_source=base,resolved_differences=diff,programmes=rows,limits='Actual fresh OFF link identical; prior baseline guest evidence is reusable only with exact fixture/data/programme binding, not automatically a fresh target gate.')
(ev/'current-off-identity.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(status=report['status'],source=source,raw=rows['currentoff']['raw_sha256'],overlays=14)))
