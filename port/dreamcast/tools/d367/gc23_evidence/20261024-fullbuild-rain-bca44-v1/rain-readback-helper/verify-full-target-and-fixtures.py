from pathlib import Path
import subprocess,json,hashlib
r=Path('/root/work/lanes/water-rain24');names=subprocess.check_output(['git','-C',str(r),'ls-files'],text=True).splitlines()
for p in names:
 if ('r10c' in p.lower() or 'warp' in p.lower() or 'qa' in p.lower()) and p.startswith('port/dreamcast/tools/d367/') and any(x in p for x in ['fullplay','test23','qa23','water','water_rain','rr/','qa/']):print(p)
# Readback actual complete full arm programme/profile without invoking target tools.
e=Path('/root/work/lanes/water-rain24-full-target-scratch');d=json.loads((e/'receipt.json').read_text());assert d['complete'];result={'receipt_sha256':hashlib.sha256((e/'receipt.json').read_bytes()).hexdigest(),'source':d['source'],'profile':d['profile'],'complete':True,'arms':{}}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
keys=['DBG_WARP','WARP_JUMP','QA_MENU','QA_SCENARIO','RAIN_R10C_DC','RAIN_DC','RAIN_PS2','RAIN_DC_N','D349_RENDERER_STACK','PVR_STREAM','NATIVE_LASER','EFFECT_SPRITES','QUALITY','QUALITY_LOD_PX','MESH_LOD_PX','SCENERY_FAR_LOD','R101_ALIVE_CAP','SCENERY_EMIT_CENSUS','WORLD_METER','PC_SAMPLER','KOS_CACHE_P2_DIAG','STAT_ROUTINE_BYTES','ESP_POOL_RECYCLE','R117_EFFECT_FAILURE_SAFE','KOS_CACHE_P2','R10C_SPAWN_LIVE_GUARD','EM_READ_RETRY','GC_ASSET_GATE']
for name,arm in d['arms'].items():
 out=e/name/'out';assert sha(e/name/'program.bin')==arm['raw_sha256'];assert sha(out/'resolved-knobs.txt')==arm['resolved_sha256'];assert sha(e/name/'build.log')==arm['buildlog_sha256'];assert not (e/name/'link-scratch/missing.txt').stat().st_size
 for f,meta in arm['files'].items():assert (out/f).stat().st_size==meta['bytes'] and sha(out/f)==meta['sha256'],(name,f)
 vals=dict(line.split('=',1) for line in (out/'resolved-knobs.txt').read_text().splitlines() if '=' in line and not line.startswith('#'))
 result['arms'][name]={'out':str(out),'raw_sha256':arm['raw_sha256'],'elf':arm['files']['re4dc-game.elf'],'files_verified':len(arm['files']),'resolved':{k:vals.get(k,'ABSENT') for k in keys},'size':arm['size']}
 if name=='off':
  assert (e/name/'program.bin').read_bytes()==(e/'baseline-program.bin').read_bytes()
  for f in arm['files']:
   if f.endswith('.ovl'):assert (out/f).read_bytes()==(Path(d['profile'])/f).read_bytes()
result['scope']='read-only hash/byte/profile verification; no SDK/guest/stage; rP programme is not rW/QA or live owner proof'
base=Path('/mnt/c/Game Dev/Emulators/codex-lanes/water-rain24');dest=base/'rain-r10c-target-followup';dest.mkdir(exist_ok=True);(dest/'TARGET-READBACK.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))