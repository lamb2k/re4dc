"""Future allocation-only fresh same-QA baseline/OFF/ON. No execution during prepare."""
from pathlib import Path
import hashlib,json,os,signal,subprocess,time
OWN=Path(__file__).resolve().parent
TREE=Path('/root/work/lanes/gc-motion24')
SOURCE='aab201ceac0e18107f64a3212398afe916793327'
PROFILE=Path('/root/probe/lanes/route/out-rrfb254e8rP')
TOOLS=Path('/opt/toolchains/dc/sh-elf/bin')

def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def free(p):s=os.statvfs(p);return s.f_bavail*s.f_frsize
def used(p):return sum(q.stat().st_size for q in p.rglob('*') if q.is_file() and not q.is_symlink())
def git(*a):return subprocess.check_output(['git','-c','index.threads=1','-c','core.preloadIndex=false','-C',str(TREE),*a],text=True).strip()

def main():
 if os.environ.get('GC_MOTION24_FULL_ALLOCATED')!=SOURCE or os.environ.get('GC_MOTION24_FULL_SLOT')!='1':raise RuntimeError('Root allocation and shared slot required')
 plan=json.loads((OWN/'PREPARATION.json').read_text());root=Path(plan['root']);budget=plan['budget']
 if os.environ.get('GC_MOTION24_QA_ALLOCATED')!=sha(OWN/'PREPARATION.json'):raise RuntimeError('Root exact QA plan allocation required')
 if (root/'qa-receipt.json').exists():raise RuntimeError('No restart or overwrite of unique run')
 if free('/mnt/c')<budget['C_admission_bytes'] or free('/dev/shm')<budget['RAM_admission_bytes']:raise RuntimeError('Admission capacity')
 def owned():return used(root)+sum(used(Path(p)) for p in budget.get('additional_preserved_preparation_roots',[]))
 report={'source':SOURCE,'scope':'Fresh same-QA fb254 baseline and aab OFF/ON full links; no stage/guest/installed catalog/provenance/coverage acceptance','preparation_sha256':sha(OWN/'PREPARATION.json'),'source_manifest_sha256':hashlib.sha256(json.dumps(plan['source_manifests'],sort_keys=True).encode()).hexdigest(),'arms':{},'complete':False,'runner_sha256':sha(__file__)}
 def save():(root/'qa-receipt.json').write_text(json.dumps(report,indent=2)+'\n')
 def check():
  tp=json.loads((OWN/'RUNNER-PINS.json').read_text())
  if os.environ.get('GC_MOTION24_QA_TOOLS_ALLOCATED')!=sha(OWN/'RUNNER-PINS.json'):raise RuntimeError('Root exact tool seal required')
  for n,row in tp.items():
   if (OWN/n).stat().st_size!=row['bytes'] or sha(OWN/n)!=row['sha256']:raise RuntimeError('QA tool changed '+n)
  if git('rev-parse','HEAD')!=SOURCE or git('status','--porcelain'):raise RuntimeError('Frozen aab source changed')
  for p,row in plan['input_pins'].items():
   if Path(p).stat().st_size!=row['bytes'] or sha(p)!=row['sha256']:raise RuntimeError('Pinned input changed '+p)
  for p,row in {**plan['original_normal_pair_manifest'],**plan['preserved_failed_root_manifest']}.items():
   if Path(p).stat().st_size!=row['bytes'] or sha(p)!=row['sha256']:raise RuntimeError('Original full-pair input/output changed '+p)
  for arm in plan['arm_order']:
   for name,row in plan['source_manifests'][arm].items():
    p=root/arm/'source'/name
    if p.stat().st_size!=row['bytes'] or sha(p)!=row['sha256']:raise RuntimeError('Private source changed '+str(p))
  if free('/mnt/c')<budget['C_floor_bytes'] or free('/dev/shm')<budget['RAM_floor_bytes'] or owned()>budget['owned_bytes_cap']:raise RuntimeError('Capacity boundary')
 def sdk(argv,**kw):
  report.setdefault('analysis_commands',[]).append(argv);save();return subprocess.check_output(argv,text=True,**kw)
 def symbols(path):
  text=sdk([str(TOOLS/'sh-elf-nm'),'-S',str(path)]);values={}
  for line in text.splitlines():
   a=line.split()
   if len(a)>=3 and a[-1] in ['_end','_etext','_edata','__bss_start','__bss_end']:values[a[-1]]=int(a[0],16)
  return text,values
 save()
 try:
  check()
  from prepare_successor import actual_preflight,feature_signature,feature_absent
  feature_absent(feature_signature(root/'baseline/source'))
  preflights={a:actual_preflight(root/a/'source',plan['commands'][a]) for a in plan['arm_order']}
  assert all(x['returncode']==0 for x in preflights.values())
  report['actual_deadknob_preflight']=preflights;save()
  for name in plan['arm_order']:
   arm=root/name;out=arm/'out';scratch=arm/'source/port/dreamcast/game/obj'
   if out.exists() or scratch.exists():raise RuntimeError('Fresh output/linker scratch not empty '+name)
   env=os.environ.copy();env.update(plan['environment'][name]);command=plan['commands'][name];(arm/'command.json').write_text(json.dumps(command,indent=2)+'\n')
   report['arms'][name]={'started':True,'command_sha256':sha(arm/'command.json'),'environment':plan['environment'][name]};save();started=time.monotonic()
   with (arm/'build.log').open('w') as log:
    child=subprocess.Popen(command,cwd=arm/'source',env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    while child.poll() is None:
     elapsed=time.monotonic()-started;resources={'elapsed':elapsed,'C_free':free('/mnt/c'),'RAM_free':free('/dev/shm'),'owned_bytes':owned()}
     if resources['C_free']<budget['C_floor_bytes'] or resources['RAM_free']<budget['RAM_floor_bytes'] or resources['owned_bytes']>budget['owned_bytes_cap'] or elapsed>budget['per_arm_seconds']:
      (arm/'owned-termination.json').write_text(json.dumps(resources,indent=2)+'\n');os.killpg(child.pid,signal.SIGTERM)
      try:child.wait(timeout=5)
      except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
      raise RuntimeError('Owned build stopped at budget; preserve outputs '+name)
     time.sleep(2)
    if child.returncode:raise RuntimeError('Fresh build failed '+name+' rc='+str(child.returncode))
   if not (scratch/'missing.txt').is_file() or (scratch/'missing.txt').stat().st_size:raise RuntimeError('Fresh missing-symbol inventory is not empty')
   generated_aliases=(scratch/'aliases.ld').read_text();missing_cpp=(scratch/'missing.cpp').read_text()
   if 'gcasset' in generated_aliases or 'gcasset' in missing_cpp or 'motion_unknown' in generated_aliases:raise RuntimeError('Diagnostic alias/stub attempted')
   elf=out/'re4dc-game.elf';raw=arm/'program.bin'
   report.setdefault('analysis_commands',[]).append([str(TOOLS/'sh-elf-objcopy'),'-R','.stack','-O','binary',str(elf),str(raw)]);save()
   subprocess.run(report['analysis_commands'][-1],check=True)
   sym,addresses=symbols(elf);(arm/'symbols.txt').write_text(sym)
   logsym={}
   for ln in sym.splitlines():
    z=ln.split()
    if len(z)==4 and z[-1] in ['_re4dc_logbuf','_re4dc_log_head','_re4dc_stage']:logsym[z[-1]]=int(z[0],16)
   assert len(logsym)==3
   (arm/'syms.txt').write_text(' '.join(hex(logsym[k]-0x8c000000) for k in ['_re4dc_logbuf','_re4dc_log_head','_re4dc_stage'])+'\n')
   size=sdk([str(TOOLS/'sh-elf-size'),str(elf)]);(arm/'size.txt').write_text(size)
   sections=sdk([str(TOOLS/'sh-elf-size'),'-A',str(elf)]);(arm/'sections.txt').write_text(sections)
   resolved=dict(x.split('=',1) for x in (out/'resolved-knobs.txt').read_text().splitlines() if '=' in x and not x.startswith('#'))
   expect={'GC_ASSET_GATE':'1' if name=='on' else '0','GC_ASSET_MOTION_UNKNOWN':'1' if name=='on' else '0','GC_ASSET_CATALOG_SHA256':'0','STAT_ROUTINE_BYTES':'1','KOS_CACHE_P2':'1','KOS_CACHE_P2_DIAG':'0','SCENERY_DEDUP':'0','SCENERY_EMIT_PREFETCH':'0','SCENERY_SELECT_LEAN2':'0','CPU_BACKFACE':'0','ACTOR_BACKFACE':'0','VRAM_ROOM_ARENA':'0','PC_SAMPLER':'0','DBG_WARP':'1','WARP_JUMP':'1','TEX_CHECK':'1','MCHECK_LEONGC':'1','KOS_WATCH':'1','KOS_SQUEEZE':'1','W11_FIXTURE':'1','KOS_SQUEEZE_BYTES':'0','KOS_SQUEEZE_FRAG':'0','QA_MENU':'0','WORLD_METER':'0'}
   if name=='baseline':
    for key in ['GC_ASSET_GATE','GC_ASSET_CATALOG_SHA256','GC_ASSET_MOTION_UNKNOWN']:expect.pop(key)
    assert not any(key in resolved for key in ['GC_ASSET_GATE','GC_ASSET_CATALOG_SHA256','GC_ASSET_MOTION_UNKNOWN'])
   wrong={k:[v,resolved.get(k)] for k,v in expect.items() if resolved.get(k)!=v}
   if wrong:raise RuntimeError('Current normal resolved flags wrong '+str(wrong))
   overlays=sorted(out.glob('*.ovl'));assert {q.name for q in overlays}=={q.lower()+'.ovl' for q in plan['expected_overlays']}
   # Prove actual Make object graph and helper order, not just knob labels.
   import shlex
   linkline=next(x for x in (arm/'build.log').read_text().splitlines() if 'bash tools/link.sh ' in x);a=shlex.split(linkline);objects=[x for x in a if x.endswith('.o')]
   assert len(objects)==plan['expected_current_raw_object_counts'][name]
   motionobjects=[x for x in objects if x.endswith('/gc_asset_motion_unknown.o')]
   if name!='on':assert not motionobjects
   else:
    assert len(motionobjects)==1
    index=objects.index(motionobjects[0]);assert objects[index-1].endswith('/gc_asset_audio.o') and objects[index+1].endswith('/mtx.o')
   compiled_motion=[x for x in (arm/'build.log').read_text().splitlines() if '-c platform/gc_asset_motion_unknown.cpp ' in x]
   assert len(compiled_motion)==(0 if name=='baseline' else 1)
   if name=='off':
    assert not any('-DRE4DC_GC_ASSET_MOTION_UNKNOWN' in x or '-DRE4DC_GC_ASSET_GATE' in x for x in compiled_motion)
    import struct
    hb=(out/'obj/platform/gc_asset_motion_unknown.o').read_bytes();assert hb[:7]==b'\x7fELF\x01\x01\x01'
    eh=struct.unpack_from('<16sHHIIIIIHHHHHH',hb);assert eh[2]==42
    sh=[struct.unpack_from('<IIIIIIIIII',hb,eh[6]+i*eh[11]) for i in range(eh[12])]
    assert not sum(x[5] for x in sh if x[2]&2)
    hn=sdk([str(TOOLS/'sh-elf-nm'),str(out/'obj/platform/gc_asset_motion_unknown.o')]);assert not hn.strip()
   if name=='on':assert '-DRE4DC_GC_ASSET_MOTION_UNKNOWN=1' in compiled_motion[0]
   files={q.name:{'bytes':q.stat().st_size,'sha256':sha(q)} for q in [elf,raw,*overlays]}
   identity={}
   if name=='off':
    baseline=report['arms']['baseline'];assert addresses['_end']==baseline['addresses']['_end']
    assert sha(raw)==baseline['raw_sha256']
    for q in overlays:identity[q.name]=sha(q)==baseline['files'][q.name]['sha256'];assert identity[q.name]
   check()
   report['arms'][name].update({'complete':True,'seconds':time.monotonic()-started,'files':files,'addresses':addresses,'size':size,'resolved_sha256':sha(out/'resolved-knobs.txt'),'build_log_sha256':sha(arm/'build.log'),'raw_object_count':len(objects),'OFF_overlay_identity':identity,'raw_sha256':sha(raw),'missing_bytes':0,'owned_bytes':owned()});save();print(name+' FRESH FULL NORMAL LINK COMPLETE; no runtime/heap/coverage claim',flush=True)
  off,on=report['arms']['off'],report['arms']['on']
  report['end_delta_vs_fresh_OFF']=on['addresses']['_end']-off['addresses']['_end']
  report['end_delta_vs_same_QA_baseline']=on['addresses']['_end']-report['arms']['baseline']['addresses']['_end']
  report['QA_vs_normal_end']={n:report['arms'][n]['addresses']['_end']-plan['normal_programmes'][n]['addresses']['_end'] for n in ['off','on']}
  check();report['complete']=True;save();print('THREE FRESH QA LINKS COMPLETE; OFF vs same-QA baseline raw/all14 checked, linked_end priced only',flush=True)
 except Exception as exc:
  report['complete']=False;report['failure']=repr(exc);report['owned_bytes']=owned();save();raise

if __name__=='__main__':main()
