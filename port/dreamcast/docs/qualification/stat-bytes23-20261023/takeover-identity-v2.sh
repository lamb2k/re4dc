#!/usr/bin/env bash
set -euo pipefail
python3 - <<'PY'
import pathlib,subprocess,hashlib,json,re
root=pathlib.Path('/mnt/c/Flycast-Evidence/re4-dreamcast/stat-bytes23/takeover-2a14662d');ram=pathlib.Path('/dev/shm/stat-takeover-final-identity');ram.mkdir(exist_ok=True)
tool='/opt/toolchains/dc/sh-elf/bin/sh-elf-objcopy';outs={a:pathlib.Path('/root/probe/lanes/route')/n for a,n in [('base','out-rr933936erP'),('off','out-sb23off2a14rP'),('on','out-sb23on2a14rP')]}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
r={'source':'2a14662d4b025031cd93f64eed6a5d8159d473b7','baseline':'933936ea7f45ba81c09277a780ed00111407aa23','arms':{}}
for a,o in outs.items():
 b=ram/(a+'.bin');subprocess.run([tool,'-R','.stack','-O','binary',str(o/'re4dc-game.elf'),str(b)],check=True)
 r['arms'][a]={'main_raw_sha256':sha(b),'elf_sha256':sha(o/'re4dc-game.elf'),'overlays':{p.name:sha(p) for p in sorted(o.glob('*.ovl'))}}
assert r['arms']['base']['main_raw_sha256']==r['arms']['off']['main_raw_sha256'];assert r['arms']['base']['overlays']==r['arms']['off']['overlays']
r['off_identity_pass']=True;r['h2']={}
for a in ['off','on']:
 p=root/('h2-'+a+'-r2');s=(p/'run-output.txt').read_text(errors='replace').replace('\0','');run=json.loads((p/'run-result.json').read_text());bound=json.loads((p/'bounded-launch.json').read_text());rows=re.findall(r'route movie terminal=1 id=10030 frames=(\d+)/(\d+)[^\n]*heap_before=(\d+)',s)
 assert rows and rows[-1][:2]==('340','340'),rows
 assert not re.search(r'HALT|FAULT|Out of memory|MISSING',s)
 assert run['stopped']=='goal' and not run['errors'] and not bound['deadline_fired']
 r['h2'][a]={'frames':rows[-1][:2],'heap_before':int(rows[-1][2]),'elapsed_s':run['elapsed_s'],'deadline_fired':bound['deadline_fired'],'source_heap_restored':bool(re.search(r'world static: r100 arena restored=1',s))}
assert r['h2']['on']['heap_before']>=r['h2']['off']['heap_before']
r['h2']['matched_memory_pass']=True
(root/'target-identity-and-h2.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='arms'}))
PY
