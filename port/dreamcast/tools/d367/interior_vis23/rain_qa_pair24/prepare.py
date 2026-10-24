"""One-time host-only Git export and exact retained-QA contract construction."""
from pathlib import Path
import collections,hashlib,json,os,shlex,shutil,subprocess,tarfile,tempfile,time
HERE=Path(__file__).resolve().parent
GC=HERE.parent.parent/'gc-motion24'
TREE=Path('/root/work/lanes/codex-composition-int24')
SOURCE='8ce5ee2d00027268c3e69c9c300b819c1b14c63f'
SUBTREE=Path('/root/work/lanes/gc-port23/port/dreamcast/game/third_party/sh4zam')
SUB='33fa4850cacb30dd0ad35485ef035526ec4ce782'
QA=Path('/dev/shm/gc-motion24-qa-memory-v2-dbqczoc8')
NORMAL=Path('/dev/shm/rain8ce-full-normal-179r4a5c')
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def ident(p):return dict(bytes=Path(p).stat().st_size,sha256=sha(p))
def need(v,s):
 if not v:raise RuntimeError(s)
def git(tree,*args):return subprocess.check_output(['/usr/bin/git','--no-optional-locks','-C',str(tree),*args],text=True).strip()
def export(tree,ref,target):
 target.mkdir(parents=True,exist_ok=False)
 child=subprocess.Popen(['/usr/bin/git','--no-optional-locks','-C',str(tree),'archive','--format=tar',ref],stdout=subprocess.PIPE,start_new_session=True)
 try:
  with tarfile.open(fileobj=child.stdout,mode='r|') as tar:
   for member in tar:
    need(not member.issym() and not member.islnk() and (member.isdir() or member.isfile()),'Archive special/link refused')
    dest=target/member.name;need(dest.resolve().is_relative_to(target.resolve()),'Archive escape')
    tar.extract(member,target,filter='data')
  need(child.wait(timeout=30)==0,'Git archive failure')
 finally:
  child.stdout.close()
  if child.poll() is None:child.terminate();child.wait(timeout=3)
def main():
 need(not (HERE/'PREPARATION.json').exists(),'Single use; preserve old preparation')
 need(git(TREE,'rev-parse','HEAD')==SOURCE and not git(TREE,'status','--porcelain'),'Exact clean canonical8ce required')
 need(git(TREE,'ls-tree',SOURCE,'port/dreamcast/game/third_party/sh4zam').split()[2]==SUB,'Exact gitlink')
 normal=json.loads((NORMAL/'PREPARATION.json').read_text());oldcontract=json.loads((GC/'full-normal-rain8ce-exec-v1/CONTRACT.json').read_text());qr=json.loads((QA/'qa-receipt.json').read_text());qp=json.loads((QA/'PREPARATION.json').read_text());need(qr['complete'] is True,'Completed QA reference')
 pins=dict(normal['input_pins']);toolpins=dict(oldcontract['tool_pins'])
 def pin(p):p=Path(p);pins[str(p)]=ident(p);return pins[str(p)]
 for name in ['qa-receipt.json','PREPARATION.json','off/build.log','off/command.json','off/out/resolved-knobs.txt']:
  pin(QA/name)
 for name in ['ROOT-SUPPLEMENTAL-CLOSURE-v1.json','DEPENDENCY-CENSUS.json','HAIR-EOL-BRIDGE.json']:
  pin(GC/'qa-memory-media-prep'/name)
 expected={}
 for name,row in qr['arms']['off']['files'].items():
  if name!='program.bin' and not name.endswith('.ovl'):continue
  p=QA/'off'/('program.bin' if name=='program.bin' else 'out/'+name);need(ident(p)==row,'Retained QA bytes drift');pin(p);expected[name]=row
 need(expected['program.bin']['sha256']=='e0168b780b102356c9bc3ee785753a659be6a020b1d1d3f8db92f14a90c16de5' and len(expected)==15,'Exact QA identity')
 log=(QA/'off/build.log').read_text();compiled=[shlex.split(s) for s in log.splitlines() if ' -c ' in s and ' -o ' in s];link=[shlex.split(s) for s in log.splitlines() if 'bash tools/link.sh ' in s];need(len(compiled)==568 and len(link)==1,'QA actual compile/link inventory')
 objects=[x for x in link[0] if x.endswith('.o')];need(len(objects)==len(set(objects))==449,'Actual QA449')
 argv=json.loads((QA/'off/command.json').read_text());need(argv==qp['commands']['off'],'QA command receipt')
 need(not any(x.startswith(('RAIN_R10C_DC=','RAIN_R10C_DIAG=')) for x in argv[2:]),'Unmodified QA reference has no rain macros')
 flags=dict(x.split('=',1) for x in argv[2:]);critical=dict(DBG_WARP='1',WARP_JUMP='1',TEX_CHECK='1',MCHECK_LEONGC='1',KOS_WATCH='1',KOS_SQUEEZE='1',W11_FIXTURE='1',PC_SAMPLER='0',QA_MENU='0',WORLD_METER='0',KOS_CACHE_P2_DIAG='0',KOS_SQUEEZE_BYTES='0',KOS_SQUEEZE_FRAG='0',GC_ASSET_GATE='0',GC_ASSET_MOTION_UNKNOWN='0',GC_ASSET_CATALOG_SHA256='0')
 need(all(flags.get(k)==v for k,v in critical.items()),'QA exact common profile')
 root=Path(tempfile.mkdtemp(prefix='rain8ce-qa-pair-v1-',dir='/dev/shm'));export(TREE,SOURCE,root/'off/source');sub=root/'off/source/port/dreamcast/game/third_party/sh4zam';sub.rmdir();export(SUBTREE,SUB,sub)
 shutil.copytree(root/'off/source',root/'on/source',symlinks=False)
 manifest={str(p.relative_to(root/'off/source')):ident(p) for p in sorted((root/'off/source').rglob('*')) if p.is_file()}
 need(manifest==normal['source_manifest'],'Fresh Git exports must match exact current8ce inputs')
 commands={};environment={}
 for arm in ['off','on']:
  commands[arm]=['/bin/bash',str(root/arm/'source/port/dreamcast/tools/d367/build-r21.sh'),*argv[2:],'PS2_PVS_BATCH_COMPOSE=0','PS2_PVS_EFFECTIVE0_SOURCES=0','RAIN_R10C_DC='+str(int(arm=='on')),'RAIN_R10C_DIAG='+str(int(arm=='on'))]
  environment[arm]=dict(ASSETS='/root/probe/lanes/play-actor-bundle',OUT=str(root/arm/'out'),OBJDIR=str(root/arm/'out/obj'),JOBS='1',SOURCE_DATE_EPOCH='1760000000',PYTHONDONTWRITEBYTECODE='1',RE4DC_KOS_BASE='/root/work/kos-re4dc-d367')
 winpy=Path('/mnt/c/Users/lambd/AppData/Local/Programs/Python/Python312/python.exe')
 for p in ['/usr/bin/python3.12','/usr/bin/git','/usr/bin/bash','/usr/bin/make',winpy]:toolpins[str(p)]=ident(p)
 route=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/water-rain24/rain-bca44-console55-20261024/captures')
 routes={}
 for arm in ['off','on']:
  for name in ['fixture-warp.txt','fixture-pad.txt','run-output.txt']:
   p=route/(arm+'-r10c-view-v1')/name;routes[str(p)]=pin(p)
 for p in [HERE/'prepare.py',NORMAL/'PREPARATION.json',GC/'full-normal-rain8ce-exec-v1/CONTRACT.json']:pin(p)
 for p,row in {**pins,**toolpins}.items():need(ident(p)==row,'Current pin drift '+p)
 budget=dict(per_arm_seconds=600,owned_bytes_cap=2*1024**3,C_admission_bytes=26*1024**3,C_floor_bytes=24*1024**3,RAM_admission_bytes=3*1024**3,RAM_floor_bytes=512*1024**2,jobs=1,poll_seconds=0.5,shared_slots=1)
 plan=dict(schema=1,status='PREPARED_NOT_RUN',source=SOURCE,root=str(root),canonical_tree=str(TREE),submodule=dict(path='port/dreamcast/game/third_party/sh4zam',commit=SUB),source_manifest=manifest,source_files_per_arm=len(manifest),source_bytes_per_arm=sum(x['bytes'] for x in manifest.values()),commands=commands,environment=environment,input_pins=pins,tool_pins=toolpins,reference=dict(root=str(QA),arm='off',compile_count=568,object_count=449,object_order=[x.rsplit('/obj/',1)[1] for x in objects],compile_log_pin=ident(QA/'off/build.log')),OFF_expected=expected,OFF_end=qr['arms']['off']['addresses']['_end'],critical_common=critical,overlay_order=normal['overlay_order'],budget=budget,object_reuse=False,route_proposal=dict(pins=routes,scope='Authenticated historical bca44 canary route only; not current diagnostic runtime or guest evidence'),historical_supplemental_closure=ident(GC/'qa-memory-media-prep/ROOT-SUPPLEMENTAL-CLOSURE-v1.json'),no_execution=dict(SDK=0,Make_query=0,bootstrap=0,stage=0,guest=0))
 for p in [HERE/'PREPARATION.json',root/'PREPARATION.json']:
  with p.open('x') as f:json.dump(plan,f,indent=1);f.write('\n')
 print(json.dumps(dict(status=plan['status'],root=str(root),source_files=len(manifest),compile=568,objects=449,pins=len(pins),toolpins=len(toolpins),plan_sha256=sha(HERE/'PREPARATION.json'))))
if __name__=='__main__':main()
