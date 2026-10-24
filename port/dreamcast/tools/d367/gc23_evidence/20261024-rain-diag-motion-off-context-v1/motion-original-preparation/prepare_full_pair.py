"""Source-only preparation. No SDK/Make/link command is executed by this file."""
from pathlib import Path
import argparse,hashlib,json,os,shlex,subprocess,tarfile,tempfile,shutil
TREE=Path('/root/work/lanes/gc-motion24')
SOURCE='aab201ceac0e18107f64a3212398afe916793327'
OLD='1d63cffe3a232c402418f2f2d919e7abae476957'
SUBMODULE=Path('/root/work/lanes/gc-port23/port/dreamcast/game/third_party/sh4zam')
SUBCOMMIT='33fa4850cacb30dd0ad35485ef035526ec4ce782'
FULL=Path('/root/work/lanes/gc-port23-full-target2-scratch')
PROFILE=Path('/root/probe/lanes/route/out-rrfb254e8rP')
ASSETS=Path('/root/probe/lanes/play-actor-bundle')
OWN=Path(__file__).resolve().parent
SDK=Path('/root/work/kos-re4dc-d367')
OVERLAYS=['pl0f','em2f','em22','em2b','pl11','pl14','em3b','em35','st1_0','st1_1','st1_2','st1_3','st2_0','Sscrn']
CAP=2*1024**3;FLOOR=24*1024**3

def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def git(tree,*args,binary=False):return subprocess.check_output(['git','-c','index.threads=1','-c','core.preloadIndex=false','-C',str(tree),*args],text=not binary)
def export(tree,ref,target):
 target.mkdir(parents=True)
 process=subprocess.Popen(['git','-C',str(tree),'archive','--format=tar',ref],stdout=subprocess.PIPE)
 with tarfile.open(fileobj=process.stdout,mode='r|') as archive:archive.extractall(target,filter='data')
 if process.wait():raise RuntimeError('source archive failed')
def used(root):return sum(q.stat().st_size for q in root.rglob('*') if q.is_file() and not q.is_symlink())

def main():
 a=argparse.ArgumentParser();a.add_argument('--prepare',action='store_true',required=True);a.parse_args()
 if git(TREE,'rev-parse','HEAD').strip()!=SOURCE or git(TREE,'status','--porcelain').strip():raise RuntimeError('aab not frozen clean')
 if git(SUBMODULE,'rev-parse','HEAD').strip()!=SUBCOMMIT or git(SUBMODULE,'status','--porcelain').strip():raise RuntimeError('original submodule pin changed')
 if not (SUBMODULE/'include/sh4zam/shz_xmtrx.h').is_file():raise RuntimeError('submodule headers missing')
 pins={}
 def pin(path):
  path=Path(path);row={'bytes':path.stat().st_size,'sha256':sha(path)};pins[str(path)]=row;return row
 oldreceipt=json.loads((FULL/'receipt.json').read_text());assert oldreceipt['source']==OLD and oldreceipt['complete']
 original_manifest={}
 for q in FULL.rglob('*'):
  if q.is_file() and not q.is_symlink():original_manifest[str(q)]={'bytes':q.stat().st_size,'sha256':sha(q)}
 # Pin actual profile, source helpers, private fixed build includes and tool bytes.
 for q in [PROFILE/'candidate.txt',PROFILE/'resolved-knobs.txt',PROFILE/'re4dc-game.elf',*PROFILE.glob('*.ovl'),SDK/'lib/dreamcast/libkallisti.a',OWN/'run_full_pair.py',OWN/'run_full_pair.sh',OWN/'readback_full_prep.py',Path(__file__)]:pin(q)
 for q in ASSETS.rglob('*'):
  if q.is_file():pin(q)
 tools=Path('/opt/toolchains/dc/sh-elf/bin')
 for name in ['sh-elf-g++','sh-elf-gcc','sh-elf-as','sh-elf-ld','sh-elf-nm','sh-elf-objcopy','sh-elf-size','sh-elf-c++filt']:pin(tools/name)
 for q in [SDK/'utils/build_wrappers/kos-c++',SDK/'utils/build_wrappers/kos-cc',Path('/opt/toolchains/dc/sh-elf/libexec/gcc/sh-elf/15.2.0/cc1plus'),Path('/opt/toolchains/dc/sh-elf/libexec/gcc/sh-elf/15.2.0/cc1'),Path('/opt/toolchains/dc/sh-elf/lib/gcc/sh-elf/15.2.0/libgcc.a'),Path('/opt/toolchains/dc/sh-elf/sh-elf/lib/libc.a'),Path('/root/probe/d367-buildslot.sh')]:pin(q)
 # Freeze SDK/system source headers and real archives, not only the KOS archive.
 for directory in [SDK/'include',SDK/'kernel',SDK/'addons/include',Path('/root/work/kos-ports/include'),Path('/opt/toolchains/dc/sh-elf/lib/gcc/sh-elf/15.2.0/include'),Path('/opt/toolchains/dc/sh-elf/sh-elf/include')]:
  for q in directory.rglob('*'):
   if q.is_file() and (directory!=SDK/'kernel' or q.suffix in ['.h','.hpp','.inc','.inl','.c','.cpp','.S','.s','.sh','.mk']):pin(q)
 for directory in [SDK/'lib/dreamcast',SDK/'addons/lib/dreamcast',Path('/root/work/kos-ports/lib')]:
  for q in directory.glob('*.a'):pin(q)
 for q in [SDK/'environ.sh',SDK/'environ_base.sh',SDK/'environ_dreamcast.sh',SDK/'Makefile.rules',Path('/usr/bin/python3.12')]:
  if q.is_file():pin(q)
 args=shlex.split((PROFILE/'candidate.txt').read_text())
 assert all('=' in x and x.split('=',1)[0].replace('_','').isalnum() for x in args)
 assert not any(x.startswith(('GC_ASSET_GATE=','GC_ASSET_CATALOG_SHA256=','GC_ASSET_MOTION_UNKNOWN=')) for x in args)
 if any(x.startswith(('OUT=','OBJDIR=','TARGET=')) for x in args):raise RuntimeError('baseline has output override')
 # Read actual link order and complete helper pipeline; never replay cached overlays.
 old_graph={}
 for arm,count in [('off',448),('on',453)]:
  lines=(FULL/arm/'build.log').read_text().splitlines();line=next(x for x in lines if 'bash tools/link.sh ' in x);av=shlex.split(line);objects=[x for x in av if x.endswith('.o')];assert len(objects)==count
  ov=[x.split('gen_overlay: .ovl_',1)[1].split()[0] for x in lines if 'gen_overlay: .ovl_' in x];assert ov==OVERLAYS
  addresses={}
  for entry in (FULL/arm/'symbols.txt').read_text().splitlines():
   fields=entry.split()
   if len(fields)>=3 and fields[-1] in ['_end','_etext','_edata','__bss_start','__bss_end']:addresses[fields[-1]]=int(fields[0],16)
  assert '_end' in addresses
  old_graph[arm]={'addresses':addresses,'raw_link_line':line,'raw_object_order':objects,'object_count':count,'overlay_order':ov,'helper_pipeline':'aliases -> pass1 -> missing gate -> base/discard helper reachability -> final link ->14 shifted links/gen_overlay -> OVL_ID patch -> remove overlay sections -> size'}
 current_make=git(TREE,'show',SOURCE+':port/dreamcast/game/Makefile')
 old_make=git(TREE,'show',OLD+':port/dreamcast/game/Makefile');assert current_make==old_make
 linkscript=git(TREE,'show',SOURCE+':port/dreamcast/game/tools/link.sh');assert linkscript==git(TREE,'show',OLD+':port/dreamcast/game/tools/link.sh')
 changed=git(TREE,'diff','--name-only',OLD,SOURCE,'--','port/dreamcast/game').splitlines();changed_tus=[x for x in changed if x.endswith(('.cpp','.c'))]
 expected_tus=['platform/gc_asset_gate.cpp','platform/gc_asset_disc.cpp','platform/native_ui.cpp','platform/native_model.cpp','platform/native_actor_fast.cpp','model_bridge.cpp','platform/gc_asset_motion_unknown.cpp']
 assert set(changed_tus)=={'port/dreamcast/game/'+x for x in expected_tus}
 root=Path(tempfile.mkdtemp(prefix='gc-motion24-full-pair-',dir='/dev/shm'))
 source=root/'off/source';export(TREE,SOURCE,source)
 sub=source/'port/dreamcast/game/third_party/sh4zam';
 if sub.exists():sub.rmdir()
 export(SUBMODULE,SUBCOMMIT,sub)
 # Normal build pipeline does not query Git. Original source/submodule remain
 # untouched; each arm has private ignored generated files and game/obj scratch.
 for name in ['off','on']:
  if name=='on':shutil.copytree(source,root/'on/source',symlinks=True)
 source_manifest={str(q.relative_to(source)):{'bytes':q.stat().st_size,'sha256':sha(q)} for q in source.rglob('*') if q.is_file()}
 commands={};env={}
 for name,gate,motion in [('off','0','0'),('on','1','1')]:
  arm=root/name;commands[name]=['bash',str(arm/'source/port/dreamcast/tools/d367/build-r21.sh'),*args,'GC_ASSET_GATE='+gate,'GC_ASSET_CATALOG_SHA256=0','GC_ASSET_MOTION_UNKNOWN='+motion]
  env[name]={'ASSETS':str(ASSETS),'OUT':str(arm/'out'),'OBJDIR':str(arm/'out/obj'),'JOBS':'1','SOURCE_DATE_EPOCH':'1760000000','PYTHONDONTWRITEBYTECODE':'1','RE4DC_KOS_BASE':str(SDK)}
 plan={'status':'PREPARED_NOT_RUN','source':SOURCE,'old_full_source':OLD,'root':str(root),'commands':commands,'environment':env,'candidate_sha256':sha(PROFILE/'candidate.txt'),'source_manifest':source_manifest,'source_files_per_arm':len(source_manifest),'source_export_bytes_per_arm':used(source),'submodule_commit':SUBCOMMIT,'input_pins':pins,'original_old_full_manifest':original_manifest,'old_graph':old_graph,'changed_runtime_files':changed,'changed_translation_units':changed_tus,'expected_current_raw_object_counts':{'off':448,'on':454},'expected_overlays':OVERLAYS,'object_reuse':{'selected33_16':'NOT_ELIGIBLE_AS_NORMAL_DROP_IN: removed dependency flags, new macro placement/global flag changes are not normalized away','unchanged_old_objects':'None reused in this plan. All normal objects and14 overlays rebuilt fresh from current source.','helper_off':'absent from Make graph, no newhelper object compiled/linked in OFF','ON':'Gate1 MotionUnknown1 catalog0 only; no installed catalog/provenance/coverage claim'},'budget':{'owned_bytes_cap':CAP,'C_floor_bytes':FLOOR,'C_admission_bytes':26*1024**3,'RAM_admission_bytes':3*1024**3,'RAM_floor_bytes':512*1024**2,'per_arm_seconds':1800,'jobs':1,'shared_slots':1,'canonical_tree_lease':str(TREE),'release_priority':True,'old_full_pair_bytes':sum(x['bytes'] for x in original_manifest.values()),'old_link_scratch_observed_bytes':50595750,'additional_preserved_preparation_roots':[str(q) for q in Path('/dev/shm').glob('gc-motion24-full-pair-*') if q!=root],'expected_approx_owned_peak_bytes':1000*1024**2,'estimate_limit':'Two source copies~200MB +fresh outputs comparable to old pair~300MB +two private linker scratch~100MB +transients +preserved prior preparation exports;2GiB total owned cap. Jobs1 time unmeasured; oldJ4 arms40.24/42.46s do not establish fresh elapsed.'},'no_execution':{'SDK':0,'Make_queries':0,'links':0,'staging':0,'guest':0},'source_script_sha256':sha(__file__),'limits':['Fresh established normal build-r21 pipeline, not link replay/oldELF reused as current','Each full link regenerates alias/missing/helper ordering and all14 overlays; missing symbols or GC aliases fail','No source/recipe/staging/guest/integration change','Actual linked_end/segments and OFF raw+14 identity remain unmeasured until allocated run','If path-derived input affects OFF identity, preserve failed programmes/logs; do not change profile to force equality']}
 assert used(root)<CAP
 (root/'PREPARATION.json').write_text(json.dumps(plan,indent=2)+'\n');(OWN/'PREPARATION.json').write_text(json.dumps(plan,indent=2)+'\n')
 print(json.dumps({'status':plan['status'],'root':str(root),'source_files_per_arm':len(source_manifest),'source_export_bytes_per_arm':used(source),'fresh_arms':2,'object_reuse':False,'SDK_commands':0,'plan_sha256':sha(OWN/'PREPARATION.json')},indent=2))

if __name__=='__main__':main()
