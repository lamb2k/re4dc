from pathlib import Path
import sys,json,hashlib,shutil,datetime
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18');D=Path(r'C:\Flycast-Evidence\re4-dreamcast\castle18-20261018\Test21\recovered-j-content-20261021');O=Path(r'\\wsl.localhost\Ubuntu-24.04\root\probe\codex-castle18\port\dreamcast\tools\d367\castle18');H=O/'recovered-j-host-20261021/resume-oct21'
a,b=map(int,sys.argv[1:3]);summary,doing=sys.argv[3:5];assert 151<=a<=b<=999
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def copy_host(name):
 src=L/name;dst=H/name
 if dst.exists():assert src.read_bytes()==dst.read_bytes(),name
 else:shutil.copyfile(src,dst)
 return dict(path=name,sha256=sha(src))
inputs=[copy_host('seal-resume-delta.py'),copy_host('audit-resume-bell-context.py')];rows=[]
for n in range(a,b+1):
 cap=D/f'route-walk{n}';proof_path=D/f'route-walk{n}-checkpoint-proof.json';p=json.loads(proof_path.read_text());assert p['result']['emulator_exited'];assert sha(cap/'data/disc.state')==p['state_sha256']
 row=dict(run=cap.name,source=p['source_frame'],state_sha256=p['state_sha256'],health=p['health'],phase=p['phase'],Stop=p['Stop'],SSLoop=p['SSLoop'],run_result=p['result'],full_checkpoint_proof=dict(path=str(proof_path),sha256=sha(proof_path)),inputs=json.loads((D/f'route-walk{n}-inputs.json').read_text()),screenshots=[])
 for x in p['screenshot_contexts']:
  row['screenshots'].append(dict(source_frame_interval=x['source_frame_interval'],health_before=x['health_before'],health_after=x['health_after'],images=[dict(path=z,sha256=sha(Path(z)))for z in x['png_paths']]))
 for suffix in ['exact-combat','bell-context']:
  q=D/f'route-walk{n}-{suffix}.json'
  if q.exists():row[suffix]=json.loads(q.read_text())
 rows.append(row)
 for ext in ['py','sh']:inputs.append(copy_host(f'run-recovered-j-route-walk{n}.{ext}'))
target=O/f'recovered-j-resume-{a}-{b}-20261021.json';assert not target.exists()
record=dict(scope='Compact source/control/evidence index; all detailed immutable proofs remain at the cited C paths. No data, gameplay or state writes. Flycast results establish no release or physical Dreamcast acceptance.',summary=summary,next=doing,program_runtime='12a841d7c',program_elf_sha256='4d823b496b9a402baadabe7f679c089fa0fd55c7ffd175ec634915745a11487f',image_sha256='b67ac21eff8d819ef9ca5f0997b4c16401cb98a3d304feb65aa4b90f7affbeb6',original127_preserved=True,shared_claims=[],checkpoints=rows,host_inputs=inputs)
target.write_text(json.dumps(record,indent=2)+'\n');shutil.copyfile(target,D/target.name)
ix=json.loads((D/'screenshot-index.json').read_text());seen={x['png']for x in ix['entries']}
for row in rows:
 for c in row['screenshots']:
  for im in c['images']:
   if im['path']not in seen:ix['entries'].append(dict(run=row['run'],action=summary,png=im['path'],source_interval=c['source_frame_interval'],health=row['health']));seen.add(im['path'])
(D/'screenshot-index.json').write_text(json.dumps(ix,indent=2)+'\n')
stamp=datetime.datetime.now().astimezone().isoformat(timespec='seconds');latest=rows[-1];lines=(L/'STATUS.md').read_text().splitlines()
updates={'Done:':'Done: '+summary,'Doing now:':'Doing now: '+doing,'Next:':'Next: Finish the original Garrador encounter, stairs, waves and chapter-end save, then continue the chapter queue.','Blocked / Needs the user:':'Blocked / Needs the user: none. Garrador and chapter completion remain open; formal texture, motion and audio gates are separate.','State:':'State: WORKING. Branch: codex/castle18. Checkout: /root/probe/codex-castle18. No shared source claims.','Updated:':f'Updated: {stamp}. Actual {b}; source {latest["source"]}; state {latest["state_sha256"]}; health {latest["health"]}. Original127 and authentic death/Continue lineage retained.'}
for i,line in enumerate(lines):
 for prefix,value in updates.items():
  if line.startswith(prefix):lines[i]=value;break
(L/'STATUS.md').write_text('\n'.join(lines)+'\n')
with (L/'HANDBACK.md').open('a',encoding='utf-8')as f:f.write(f'\n## Original combat {a} through {b}, {stamp}\n{summary}\n{doing}\nExact source/program/asset identities, screenshots and closed-state receipts: {target}. No release or hardware acceptance.\n')
print(target)
