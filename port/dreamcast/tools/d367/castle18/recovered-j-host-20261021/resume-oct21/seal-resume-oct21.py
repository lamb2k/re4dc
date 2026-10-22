from pathlib import Path
import json,sys,hashlib,shutil,datetime
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18')
D=Path(r'C:\Flycast-Evidence\re4-dreamcast\castle18-20261018\Test21\recovered-j-content-20261021')
O=Path(r'\\wsl.localhost\Ubuntu-24.04\root\probe\codex-castle18\port\dreamcast\tools\d367\castle18')
n=int(sys.argv[1]);summary=sys.argv[2];doing=sys.argv[3];assert 128<=n<=999
rows=[json.loads((D/f'route-walk{i}-checkpoint-proof.json').read_text()) for i in range(128,n+1)]
assert all(r['result']['emulator_exited'] for r in rows)
name=f'recovered-j-resume-128-{n}-20261021.json';p=O/name;assert not p.exists()
host=O/'recovered-j-host-20261021'/'resume-oct21';host.mkdir(exist_ok=True)
files=['prepare-recovered-j-bounded-arm.py','audit-recovered-j-checkpoint.py','seal-resume-oct21.py','owned-window-recovered-j-r201-sealed-injury-recovery-still.py','owned-window-recovered-j-r201-sealed-health-far-track-weakpoint-still.py','owned-window-recovered-j-r201-original-Continue90-still.py']
files += [f'run-recovered-j-route-walk{i}.{ext}' for i in range(128,n+1) for ext in ['py','sh']]
identities=[]
for f in files:
 src=L/f;dst=host/f
 if dst.exists():assert dst.read_bytes()==src.read_bytes(),f
 else:shutil.copyfile(src,dst)
 identities.append(dict(path=f,sha256=hashlib.sha256(src.read_bytes()).hexdigest()))
receipt=dict(scope='Resumed original recovered-J lineage. Source and controls only; Flycast progression results do not establish release or physical Dreamcast acceptance.',summary=summary,checkpoints=rows,host_inputs=identities,next=doing,source='codex/castle18 runtime12a841d7c',program='c21jmW ELF4d823b496b9a402baadabe7f679c089fa0fd55c7ffd175ec634915745a11487f',image='b67ac21eff8d819ef9ca5f0997b4c16401cb98a3d304feb65aa4b90f7affbeb6',original127_preserved=True,shared_claims=[])
p.write_text(json.dumps(receipt,indent=2)+'\n')
shutil.copyfile(p,D/name)
ix=json.loads((D/'screenshot-index.json').read_text());seen={e['png'] for e in ix['entries']}
for r in rows:
 for c in r['screenshot_contexts']:
  for png in c['png_paths']:
   if png not in seen:ix['entries'].append(dict(run=r['run'],action=summary,png=png,source_interval=c['source_frame_interval'],health=r['health']));seen.add(png)
(D/'screenshot-index.json').write_text(json.dumps(ix,indent=2)+'\n')
r=rows[-1];lines=(L/'STATUS.md').read_text().splitlines();stamp=datetime.datetime.now().astimezone().isoformat(timespec='seconds')
updates={'Done:':'Done: '+summary,'Doing now:':'Doing now: '+doing,'Next:':'Next: Finish original Garrador, stairs, waves and chapter-end save, then continue I-011 queue.','Blocked / Needs the user:':'Blocked / Needs the user: none. Live Garrador and chapter completion remain open; inherited formal texture/motion/audio failures remain separate.','State:':'State: WORKING. Branch: codex/castle18. Checkout: /root/probe/codex-castle18. No shared source claim.','Last pushed:':'Last pushed: prior 6f456359d; resumed progression evidence commit follows.','Updated:':f'Updated: {stamp}. Actual {n}, source {r["source_frame"]}, state {r["state_sha256"]}, health {r["health"]}. Original127 and all death/Continue lineage preserved.'}
for i,line in enumerate(lines):
 for prefix,text in updates.items():
  if line.startswith(prefix):lines[i]=text;break
(L/'STATUS.md').write_text('\n'.join(lines)+'\n')
with (L/'HANDBACK.md').open('a',encoding='utf-8') as f:f.write(f'\n## Resumed original progression through {n}, {stamp}\n{summary}\n{doing}\nActual source {r["source_frame"]}, state {r["state_sha256"]}, health {r["health"]}. Full exact program, input, screenshot and source interval receipts: {p}. No runtime source/build/assets/recipe changes; no release or physical Dreamcast acceptance.\n')
print(p)
