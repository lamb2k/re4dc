from pathlib import Path
import hashlib,json,os,shlex,signal,subprocess,time,shutil
TREE=Path('/root/work/lanes/water-rain24');SOURCE='bca44d58a1fa0a51fd87ba94deba8cba925c8998'
OWN=Path('/root/work/lanes/water-rain24-canary-bca44-20261024')
E=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/water-rain24/rain-bca44-console55-20261024')
REL=Path('/root/work/lanes/stat-bytes23-takeover-scratch/release');PROFILE=Path('/root/probe/lanes/route/out-rrfb254e8rP')
D=TREE/'port/dreamcast/tools/d367';SCRATCH=TREE/'port/dreamcast/game/obj';TOOL='/opt/toolchains/dc/sh-elf/bin/'
CAP=6*1024**3;ADMIT=30*1024**3;FLOOR=24*1024**3

def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def git(*a):return subprocess.check_output(['git','-C',str(TREE),*a],text=True,timeout=10).strip()
def identity(p):return {'bytes':p.stat().st_size,'sha256':sha(p)}
def free():return shutil.disk_usage('/mnt/c').free
def source():
 assert git('rev-parse','HEAD')==SOURCE and not git('status','--porcelain'),'source changed/dirty; preserve'
def assets(m):return {k:v for k,v in m.items() if k!='1ST_READ.BIN' and not(k.startswith('dc/') and k.endswith('.ovl')) and k not in ['dc/warp.txt','dc/padscript.txt','dc/w11.txt']}
def main():
 source();assert free()>=ADMIT;assert not OWN.exists() and not E.exists(),'fresh unique roots required'
 assert (TREE/'port/dreamcast/game/third_party/sh4zam/include/sh4zam/shz_xmtrx.h').is_file()
 original=json.loads(Path('/root/work/lanes/water-rain24-full-target-scratch/receipt.json').read_text());assert original['complete'] and original['source']==SOURCE
 manifest=json.loads((REL/'manifest.json').read_text());assert sha(REL/'manifest.json')=='a424cdc4f68460b0d5ea8f591c44c62eefeab85b67941410bc996680dce41547'
 args=shlex.split((PROFILE/'candidate.txt').read_text());assert all('=' in a and a.split('=',1)[0].replace('_','').isalnum() for a in args)
 # Source-owned data hard links are inputs, not newly allocated bytes in transient mastering work.
 shared_inodes={(p.stat().st_dev,p.stat().st_ino) for p in (REL/'tree').rglob('*') if p.is_file()}
 workparent=Path('/root/probe/lanes-20261014/fullplay/work');oldmasters=set(workparent.glob('master.*'))
 OWN.mkdir();E.mkdir(parents=True);(E/'identities').mkdir();(E/'fixtures').mkdir();(E/'capsules').mkdir()
 if SCRATCH.exists():shutil.copytree(SCRATCH,OWN/'preexisting-link-scratch')
 report={'source':SOURCE,'scope':'PREPARE ONLY matched g/rW canaries; NO GUEST/STILL/LIFECYCLE/APPEARANCE ACCEPTANCE','complete':False,'guests_started':0,'new_total_cap_bytes':CAP,'admission_free_bytes':free(),'floor_bytes':FLOOR,'root':str(OWN),'evidence':str(E),'normal_full_receipt':identity(Path('/root/work/lanes/water-rain24-full-target-scratch/receipt.json')),'arms':{},'peak_owned_bytes':0}
 pins={str(p):identity(p) for p in [PROFILE/'candidate.txt',PROFILE/'resolved-knobs.txt',REL/'manifest.json',REL/'IP.BIN',Path('/root/work/kos-re4dc-d367/lib/dreamcast/libkallisti.a'),D/'build-r21.sh',D/'fullplay/fp_master.sh',D/'fullplay/fp_iso.py',D/'qa20/src/lake-scene5.txt',TREE/'src/game/filter06.cpp',TREE/'port/dreamcast/game/effects30.mk']}
 report['inputs']=pins
 def save():
  (OWN/'receipt.json').write_text(json.dumps(report,indent=2)+'\n');(E/'identities/preparation-receipt.json').write_text(json.dumps(report,indent=2)+'\n')
 def allocation():
  seen=set();total=0
  roots=[OWN,E,SCRATCH,*[x for x in workparent.glob('master.*') if x not in oldmasters]]
  for root in roots:
   if not root.exists():continue
   for p in root.rglob('*'):
    if p.is_file() and not p.is_symlink():
     st=p.stat();key=st.st_dev,st.st_ino
     if key not in seen and key not in shared_inodes:total+=st.st_size;seen.add(key)
  report['peak_owned_bytes']=max(report['peak_owned_bytes'],total)
  return total
 def check():
  source();assert free()>=FLOOR,'C floor violated';assert allocation()<=CAP,'owned total allocation cap violated'
  assert all(identity(Path(p))==v for p,v in pins.items()),'pinned input changed'
 def bounded(cmd,log,env,budget):
  check();start=time.monotonic()
  with log.open('x') as f:
   child=subprocess.Popen(cmd,cwd=TREE,env=env,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
   try:
    while child.poll() is None:
     assert free()>=FLOOR and allocation()<=CAP and time.monotonic()-start<=budget,'cap/floor/time'
     time.sleep(2)
   except BaseException:
    os.killpg(child.pid,signal.SIGTERM)
    try:child.wait(timeout=5)
    except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
    report['owned_stop']={'pid':child.pid,'command':cmd,'log':str(log),'elapsed':time.monotonic()-start};save();raise
   assert child.returncode==0,'child failed; preserve '+str(log)
  check();return time.monotonic()-start
 env=dict(os.environ,ASSETS='/root/probe/lanes/play-actor-bundle',JOBS='4',SOURCE_DATE_EPOCH='1760000000',PYTHONDONTWRITEBYTECODE='1',RE4DC_KOS_BASE='/root/work/kos-re4dc-d367',PRUNE_AUTO='0',RE4DC_STAGE_EXT4='1',RE4DC_STAGE_ROOT=str(OWN/'stage-root'),RE4DC_DISCCACHE=str(E/'_cache'),RE4DC_DISCCACHE_CAP_GB='4')
 extras=['DBG_WARP=1','WARP_JUMP=1','PC_SAMPLER=0','TEX_CHECK=1','MCHECK_LEONGC=1','WORLD_METER=0','GAME_TICK_LOG=0','PHASE_METER=0']
 expected=dict(DBG_WARP='1',WARP_JUMP='1',PC_SAMPLER='0',TEX_CHECK='1',MCHECK_LEONGC='1',WORLD_METER='0',GAME_TICK_LOG='0',PHASE_METER='0',QA_MENU='0',RAIN_DC='1',RAIN_PS2='1',RAIN_DC_N='320',D349_RENDERER_STACK='1',PVR_STREAM='1',STAT_ROUTINE_BYTES='1',ESP_POOL_RECYCLE='1',R117_EFFECT_FAILURE_SAFE='1',KOS_CACHE_P2='1',KOS_CACHE_P2_DIAG='0',R10C_SPAWN_LIVE_GUARD='1',EM_READ_RETRY='1',R101_ALIVE_CAP='4',QUALITY='1',QUALITY_LOD_PX='5',SCENERY_FAR_LOD='4')
 for name,value in [('off','0'),('on','1')]:
  arm=OWN/'programmes'/(name+'-g');out=arm/'out';out.mkdir(parents=True)
  cmd=['bash',str(D/'build-r21.sh'),*args,*extras,'RAIN_R10C_DC='+value];(arm/'command.json').write_text(json.dumps(cmd,indent=2)+'\n');armenv=dict(env,OUT=str(out),OBJDIR=str(out/'obj'));seconds=bounded(cmd,arm/'build.log',armenv,360)
  assert not(SCRATCH/'missing.txt').read_text().strip();shutil.copytree(SCRATCH,arm/'link-scratch')
  vals=dict(line.split('=',1) for line in (out/'resolved-knobs.txt').read_text().splitlines() if '=' in line and not line.startswith('#'))
  for k,v in dict(expected,RAIN_R10C_DC=value).items():assert vals.get(k)==v,(k,v,vals.get(k))
  for k in ['SCENERY_DEDUP','PS2_PVS','SCENERY_SELECT_LEAN2','SCENERY_EMIT_PREFETCH','CPU_BACKFACE','ACTOR_BACKFACE','VRAM_ROOM_ARENA','KOS_WATCH','KOS_SQUEEZE','W11_FIXTURE','NATIVE_MODEL_REGISTRY_CENSUS']:
   if k in vals:assert vals[k]=='0',(k,vals[k])
  assert 'SCENERY_EMIT_CENSUS' not in vals or vals['SCENERY_EMIT_CENSUS']=='0'
  elf=out/'re4dc-game.elf';ovls=sorted(out.glob('*.ovl'));assert len(ovls)==14
  subprocess.run([TOOL+'sh-elf-objcopy','-R','.stack','-O','binary',str(elf),str(arm/'program.bin')],check=True,timeout=15)
  symbols=subprocess.check_output([TOOL+'sh-elf-nm','-S',str(elf)],text=True,timeout=15);(arm/'symbols.txt').write_text(symbols)
  sm={f[-1]:int(f[0],16) for line in symbols.splitlines() if len(f:=line.split())==4};syms=' '.join(hex(sm[k]-0x8c000000) for k in ['_re4dc_logbuf','_re4dc_log_head','_re4dc_stage']);(out/'syms.txt').write_text(syms+'\n');(out/'stack.txt').write_text(SOURCE+'\n');(out/'candidate.txt').write_text(shlex.join([*args,*extras,'RAIN_R10C_DC='+value])+'\n')
  programme={p.name:identity(p) for p in [elf,*ovls]};programme['raw']=identity(arm/'program.bin')
  base=E/'_discs'/(name+'-g');assert not base.exists();base.parent.mkdir(exist_ok=True)
  stage_seconds=bounded(['bash',str(D/'fullplay/fp_master.sh'),str(REL/'tree'),str(REL/'manifest.json'),str(REL/'IP.BIN'),str(base),str(out)],arm/'master.log',env,300)
  staged=json.loads((base/'base-manifest.json').read_text());assert assets(staged)==assets(manifest)
  assert staged['1ST_READ.BIN']=={'size':programme['raw']['bytes'],'sha256':programme['raw']['sha256']}
  for f in ovls:assert staged['dc/'+f.name]=={'size':programme[f.name]['bytes'],'sha256':programme[f.name]['sha256']}
  assert sha(base/'track03.iso')==(base/'track03.sha256').read_text().strip()
  report['arms'][name]={'profile':'matched g/rW; view canary only','out':str(out),'programme':programme,'raw':programme['raw'],'resolved_sha256':sha(out/'resolved-knobs.txt'),'syms':syms,'source':SOURCE,'build_seconds':seconds,'stage_seconds':stage_seconds,'base':str(base),'base_records':{p.name:identity(p) for p in base.iterdir() if p.is_file()},'flags':{k:vals.get(k) for k in [*expected,'RAIN_R10C_DC']}}
  for p in [out/'resolved-knobs.txt',out/'stack.txt',out/'candidate.txt',out/'syms.txt',arm/'command.json']:shutil.copyfile(p,E/'identities'/(name+'-g-'+p.name))
  shutil.copyfile(arm/'build.log',E/'identities'/(name+'-g-build.log'));shutil.copyfile(arm/'master.log',E/'identities'/(name+'-g-master.log'));save();print(name+' g/rW BUILT+STAGED; NO GUEST',flush=True)
 # Assert whole resolved profiles differ only at the intended option, not hidden inherited defaults.
 a,b=[dict(line.split('=',1) for line in (Path(report['arms'][n]['out'])/'resolved-knobs.txt').read_text().splitlines() if '=' in line and not line.startswith('#')) for n in ['off','on']]
 differences={k:[a.get(k),b.get(k)] for k in set(a)|set(b) if a.get(k)!=b.get(k)};assert differences=={'RAIN_R10C_DC':['0','1']},differences;report['resolved_differences']=differences
 fixture=(D/'qa20/src/lake-scene5.txt').read_text().rstrip()+'\nfreeze 330\n';(E/'fixtures/r10c-view.txt').write_text(fixture);(E/'fixtures/neutral-pad.txt').write_text('')
 for name in ['off','on']:
  capsule=E/'capsules'/name;capsule.mkdir();data=capsule/'data';data.mkdir()
  for f in ['T0000_vmu_save_A1.bin','vmu_save_A2.bin']:
   src=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/d367-harness-par/data')/f;assert sha(src)=='b4c5a531493665876fc72c3fcdef8ebd05fe0f7d14fb2aa73dd87d3586670b20';shutil.copyfile(src,data/f)
  shutil.copyfile(Path('/mnt/c/Flycast-Evidence/re4-dreamcast/d367-harness-par/emu.cfg'),capsule/'template-emu.cfg')
 report['fixtures']={p.name:identity(p) for p in (E/'fixtures').iterdir()};report['complete']=True;report['stage_complete_guests_blocked_pending_root_preflight']=True;check();save();print('BOTH CANARIES PREPARED; NO GUEST; peak_owned='+str(report['peak_owned_bytes']),flush=True)
if __name__=='__main__':main()