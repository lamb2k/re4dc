from pathlib import Path
import json,hashlib,subprocess,tempfile
E=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/dedup-offline23-20261023/current-4be08e01')
plan=json.loads((E/'private-qa-plan-prelink.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
S='4be08e0110592510e3630c01fa9f49b3ac2fed3d'
rows={}
with tempfile.TemporaryDirectory(prefix='dedup-qa-pins-',dir='/dev/shm') as ram:
 for arm in ('off','on'):
  x=plan['arms'][arm];p=Path(x['program_out'])
  assert (p/'stack.txt').read_text()==S+'\n' and not (p/'missing.txt').read_bytes()
  k=dict(l.split('=',1) for l in (p/'resolved-knobs.txt').read_text().splitlines() if '=' in l)
  for n,v in x['required_resolved_knobs'].items():assert k[n]==v,(arm,n,k.get(n),v)
  for n in ['WORLD_METER','STAT_DIAG','KOS_CACHE_P2_DIAG','VRAM_ROOM_ARENA','KOS_WATCH','KOS_SQUEEZE','NATIVE_MODEL_REGISTRY_CENSUS']:assert k[n]=='0',(arm,n)
  for n in ['SCENERY_SELECT_ONLY','SCENERY_REPLAY_LEAN','SCENERY_SUBMIT_BATCH','STAT_ROUTINE_BYTES','ESP_POOL_RECYCLE','R117_EFFECT_FAILURE_SAFE','KOS_CACHE_P2','R10C_SPAWN_LIVE_GUARD','EM_READ_RETRY']:assert k[n]=='1',(arm,n)
  raw=Path(ram)/(arm+'.bin')
  subprocess.run(['/opt/toolchains/dc/sh-elf/bin/sh-elf-objcopy','-R','.stack','-O','binary',str(p/'re4dc-game.elf'),str(raw)],check=True)
  ovs={f.name:sha(f) for f in p.glob('*.ovl')};assert len(ovs)==14
  candidate=Path('/root/work/lanes/dedup-offline23-current-d5c-scratch/qa/programs')/('candidate-route'+x['label'])
  assert candidate.is_dir()
  scrambled=Path(ram)/(arm+'-scrambled.bin')
  subprocess.run(['/root/work/kos/utils/scramble/scramble',str(raw),str(scrambled)],check=True)
  assert sha(candidate/'1ST_READ.BIN')==sha(scrambled)
  for n,h in ovs.items():assert sha(candidate/n)==h
  rows[arm]=dict(label=x['label'],path=str(p),elf_sha256=sha(p/'re4dc-game.elf'),raw_sha256=sha(raw),raw_bytes=raw.stat().st_size,scrambled_sha256=sha(scrambled),resolved_sha256=sha(p/'resolved-knobs.txt'),overlays=ovs,candidate=str(candidate),required_resolved=x['required_resolved_knobs'])
out=E/'qa-programme-pins-r1.json';assert not out.exists()
out.write_text(json.dumps(dict(status='PASS_NORMAL_QA_PROGRAMMES_ONLY_NO_MEDIA_STAGED',source=S,plan_sha256=sha(E/'private-qa-plan-prelink.json'),arms=rows,limits='Exact source4be normal QA programmes and correct private candidate/all14 bound. No target memory/movie/QA-menu or media acceptance from this receipt.'),indent=2)+'\n')
print('QA_PROGRAMME_PINS_PASS',[(k,v['raw_sha256']) for k,v in rows.items()])

