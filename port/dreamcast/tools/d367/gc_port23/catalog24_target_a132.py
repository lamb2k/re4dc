"""Allocated two-TU SH4 pricing only. --prepare performs no SDK command."""
from pathlib import Path
import hashlib,json,os,resource,shlex,subprocess,sys,tempfile,time
TREE=Path('/root/work/lanes/gc-catalog24')
PARENT='1d63cffe3a232c402418f2f2d919e7abae476957'
SOURCE='a132648e8199b50a5ac51cec4d339fe7dbc60135'
FULL=Path('/root/work/lanes/gc-port23-full-target2-scratch')
EVIDENCE=Path('/mnt/c/Flycast-Evidence/re4-dreamcast/gc-port23-20261023/full-target-static1d63-current')
OWN=Path('/mnt/c/Game Dev/Emulators/codex-lanes/gc-catalog24')
PROFILE=Path('/root/probe/lanes/route/out-rrfb254e8rP')
UNITS=['platform/gc_asset_gate.cpp','platform/gc_asset_disc.cpp']
RUNTIME=['port/dreamcast/game/'+x for x in UNITS]+['port/dreamcast/game/platform/include/gc_asset_index.inc']
EXPORT=RUNTIME+['port/dreamcast/game/platform/include/'+x for x in ['gc_asset_gate.h','gc_asset_sha.inc','native_io.h']]
CAP=256*1024**2;FLOOR=24*1024**3

def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def git(*args):return subprocess.check_output(['git','-c','index.threads=1','-c','core.preloadIndex=false','-C',str(TREE),*args],text=True).strip()
def free():s=os.statvfs('/mnt/c');return s.f_bavail*s.f_frsize
def usage(p):return sum(x.stat().st_size for x in p.rglob('*') if x.is_file() and not x.is_symlink())
def command_rows(arm):
 found={}
 for line in (FULL/arm/'build.log').read_text().splitlines():
  if not line.startswith('kos-c++ '):continue
  a=shlex.split(line)
  if '-c' not in a:continue
  u=a[a.index('-c')+1]
  if u in UNITS:
   if u in found:raise RuntimeError('Duplicate actual compile '+u)
   found[u]=a
 if set(found)!=set(UNITS):raise RuntimeError('Missing real normal compile commands')
 return found

def preparation():
 if git('rev-parse','HEAD')!=SOURCE or git('status','--porcelain'):raise RuntimeError('Catalog source not clean/frozen')
 if free()<FLOOR:raise RuntimeError('C below24GiB')
 receipt=json.loads((EVIDENCE/'receipt.json').read_text());manifest=json.loads((EVIDENCE/'SHA256-MANIFEST.json').read_text())
 for n,row in manifest.items():
  if sha(EVIDENCE/n)!=row['sha256'] or (EVIDENCE/n).stat().st_size!=row['bytes']:raise RuntimeError('Full link receipt changed')
 pins={str(EVIDENCE/n):sha(EVIDENCE/n) for n in ['receipt.json','SUMMARY.json','SHA256-MANIFEST.json']}
 for name,expected in receipt['pins'].items():
  if sha(name)!=expected:raise RuntimeError('Parent full input changed: '+name)
  pins[name]=expected
 for arm in ['off','on']:
  p=FULL/arm/'build.log'
  if sha(p)!=receipt['arms'][arm]['buildlog_sha256']:raise RuntimeError('Actual full compile log changed')
  pins[str(p)]=sha(p)
  for p in [EVIDENCE/arm/'command.json',EVIDENCE/arm/'resolved-knobs.txt']:
   pins[str(p)]=sha(p)
 # Source diff is the explicit limit of retained old14 OFF proof. No new
 # programme is linked and no unchanged arm is recompiled or copied as new.
 changed=git('diff','--name-only',PARENT,SOURCE).splitlines()
 runtime=[n for n in changed if not n.startswith('port/dreamcast/tools/')]
 if set(runtime)!=set(RUNTIME):raise RuntimeError('Unexpected runtime changes: '+str(runtime))
 if len(changed)!=5:raise RuntimeError('Unexpected scope')
 rows={arm:command_rows(arm) for arm in ['off','on']}
 for u in UNITS:
  def norm(a):
   a=a.copy();a[a.index('-o')+1]='@OUTPUT'
   return [x for x in a if not x.startswith(('-DRE4DC_GC_ASSET_GATE=','-DRE4DC_GC_ASSET_CATALOG_SHA256='))]
  if norm(rows['off'][u])!=norm(rows['on'][u]):raise RuntimeError('Unmatched actual OFF/ON flags '+u)
  for arm in ['off','on']:
   a=rows[arm][u]
   if '-matomic-model=soft-gusa' not in a or '-std=gnu++20' not in a:raise RuntimeError('Profile drift')
 # Pin wrappers/tool executables by bytes; no version query or SDK invocation
 # in --prepare. Actual provider paths are queried only in the allocated run.
 tool=Path('/opt/toolchains/dc/sh-elf/bin')
 for p in [Path('/root/work/kos-re4dc-d367/utils/build_wrappers/kos-c++'),Path('/root/work/kos-re4dc-d367/utils/build_wrappers/kos-cc'),TREE/'port/dreamcast/kos-env.sh',*(tool/n for n in ['sh-elf-g++','sh-elf-size','sh-elf-nm','sh-elf-objcopy'])]:pins[str(p)]=sha(p)
 return dict(source=SOURCE,parent=PARENT,baseline='fb254e82ee6f9a3d9e34d53d1d442348a46b9cf2',profile=str(PROFILE),pins=pins,commands=rows,changed=changed,runtime_diff=runtime,arms=['absent','zero','on-catalog0','on-synthetic-pin'],arm_count=16,cap=CAP,c_floor=FLOOR,scope='Fresh selected gate/disc objects only, actual full normal flags. Retained old14 OFF programmes proof is historical plus unchanged runtime/input diff, not a new full link. Synthetic pin syntax/code retention only. No fullchain/heap/stage/guest/I001 acceptance.')

def run(plan):
 if os.environ.get('GC_CATALOG24_ALLOCATED')!=SOURCE:raise RuntimeError('Use allocated slot/tree wrapper')
 if os.environ.get('KOS_BASE')!='/root/work/kos-re4dc-d367':raise RuntimeError('Wrong real SDK')
 resource.setrlimit(resource.RLIMIT_AS,(CAP,CAP));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
 out=Path(tempfile.mkdtemp(prefix='gc-catalog24-a132-',dir='/dev/shm'));report=dict(plan,objects=[],complete=False,harness_sha256=sha(__file__))
 def save():(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
 def check():
  if free()<FLOOR or usage(out)>CAP:raise RuntimeError('Allocated floor/cap exceeded')
  if git('rev-parse','HEAD')!=SOURCE or git('status','--porcelain'):raise RuntimeError('Source changed')
  for n,d in report['pins'].items():
   if sha(n)!=d:raise RuntimeError('Pinned input changed '+n)
 save();print(str(out),flush=True)
 # Small immutable six-file exports, not source worktrees or whole media.
 for label,ref in [('parent',PARENT),('current',SOURCE)]:
  for name in EXPORT:
   p=out/label/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(subprocess.check_output(['git','-C',str(TREE),'show',ref+':'+name]))
 bins=Path(os.environ['KOS_CC_BASE'])/'bin'
 compiler=bins/'sh-elf-g++'
 libs=[Path(os.environ['KOS_BASE'])/'lib/dreamcast/libkallisti.a']
 for query in ['-print-libgcc-file-name','-print-file-name=libc.a']:
  p=Path(subprocess.check_output([str(compiler),'-m4-single','-ml',query],text=True).strip());assert p.is_file();libs.append(p)
 providers=libs+[FULL/'on/out/obj/platform/os.o',FULL/'on/out/obj/platform/mem.o']
 for p in providers:report['pins'][str(p)]=sha(p)
 save()
 for label,ref in [('parent',PARENT),('current',SOURCE)]:
  cwd=out/label/'port/dreamcast/game'
  for unit in UNITS:
   for arm in plan['arms']:
    check();a=plan['commands']['off' if arm in ('absent','zero') else 'on'][unit].copy()
    a=[x for x in a if x not in ('-MMD','-MD','-MP')]
    for option in ['-MF','-MT','-MQ']:
     while option in a:
      at=a.index(option);del a[at:at+2]
    if arm=='zero':a.append('-DRE4DC_GC_ASSET_GATE=0')
    if arm=='on-synthetic-pin':a=[('-DRE4DC_GC_ASSET_CATALOG_SHA256="'+'1'*64+'"') if x.startswith('-DRE4DC_GC_ASSET_CATALOG_SHA256=') else x for x in a]
    tag=label+'-'+Path(unit).stem+'-'+arm;obj=out/(tag+'.o');a[a.index('-o')+1]=str(obj);a.append('-fstack-usage')
    (out/(tag+'-command.json')).write_text(json.dumps(a,indent=2)+'\n');dep=out/(tag+'.d');started=time.monotonic()
    with (out/(tag+'.log')).open('w') as log:
     subprocess.run(a+['-M','-MF',str(dep),'-MT',tag],cwd=cwd,stdout=log,stderr=subprocess.STDOUT,check=True)
     names=shlex.split(dep.read_text().split(':',1)[1].replace('\\\n',' '));before={str((cwd/n).resolve()):sha((cwd/n).resolve()) for n in names}
     subprocess.run(a,cwd=cwd,stdout=log,stderr=subprocess.STDOUT,check=True)
    if any(sha(n)!=d for n,d in before.items()):raise RuntimeError('Dependency changed '+tag)
    (out/(tag+'-inputs.json')).write_text(json.dumps(before,indent=2)+'\n')
    stripped=out/(tag+'-nodebug.o');subprocess.run([str(bins/'sh-elf-objcopy'),'--strip-debug',str(obj),str(stripped)],check=True)
    size=subprocess.check_output([str(bins/'sh-elf-size'),str(obj)],text=True);undef=subprocess.check_output([str(bins/'sh-elf-nm'),'-u',str(obj)],text=True);defined=subprocess.check_output([str(bins/'sh-elf-nm'),'-g','--defined-only',str(obj)],text=True)
    for suffix,value in [('size',size),('undefined',undef),('defined',defined)]:(out/(tag+'-'+suffix+'.txt')).write_text(value)
    values=[int(x) for x in size.splitlines()[-1].split()[:3]]
    if arm in ('absent','zero') and (any(values) or defined.strip()):raise RuntimeError('OFF helper not empty '+tag)
    su=out/(tag+'.su')
    row=dict(source=ref,label=label,unit=unit,arm=arm,sha256=sha(obj),nodebug_sha256=sha(stripped),sections=dict(zip(['text','data','bss'],values)),inputs_sha256=sha(out/(tag+'-inputs.json')),command_sha256=sha(out/(tag+'-command.json')),su_sha256=sha(su),seconds=time.monotonic()-started)
    report['objects'].append(row);save();check();print(tag+' '+str(row['sections']),flush=True)
 lookup={(r['label'],r['unit'],r['arm']):r for r in report['objects']};report['off_identity']={};report['deltas']={}
 for u in UNITS:
  ref=lookup['parent',u,'absent']['nodebug_sha256']
  report['off_identity'][u]=all(lookup[label,u,arm]['nodebug_sha256']==ref for label in ['parent','current'] for arm in ['absent','zero'])
  if not report['off_identity'][u]:raise RuntimeError('Parent/current/absent/0 differs '+u)
  for arm in ['on-catalog0','on-synthetic-pin']:
   report['deltas'][u+' '+arm]={n:lookup['current',u,arm]['sections'][n]-lookup['parent',u,arm]['sections'][n] for n in ['text','data','bss']}
 # Query only real selected object/archive providers. Multiple archive candidates
 # are recorded; this is not a fresh final linker member-selection map.
 ext={}
 for p in providers:
  txt=subprocess.check_output([str(bins/'sh-elf-nm'),'-A','-g','--defined-only',str(p)],text=True,stderr=subprocess.DEVNULL)
  for line in txt.splitlines():
   fields=line.split()
   if len(fields)>=3 and fields[-2] in ('T','W','V','B','D','R','S','A'):
    ext.setdefault(fields[-1],[]).append({'provider':str(p),'definition':line})
 report['provider_closure']={}
 for arm in ['on-catalog0','on-synthetic-pin']:
  own={};imports=set()
  for u in UNITS:
   tag='current-'+Path(u).stem+'-'+arm
   for l in (out/(tag+'-defined.txt')).read_text().splitlines():
    fs=l.split()
    if len(fs)>=3:own.setdefault(fs[-1],[]).append(tag)
   for l in (out/(tag+'-undefined.txt')).read_text().splitlines():
    if l.split():imports.add(l.split()[-1])
  closure={n:{'selected_current_definitions':own.get(n,[]),'real_external_candidates':ext.get(n,[])} for n in sorted(imports)}
  missing=[n for n,d in closure.items() if not d['selected_current_definitions'] and not d['real_external_candidates']]
  report['provider_closure'][arm]={'imports':closure,'missing':missing,'note':'No aliases/stubs; real candidates only. Archive selection/final map not re-linked.'}
  if missing:raise RuntimeError('Missing actual providers '+str(missing))
 report['stack_scope']={'self_frames':'Every .su retained; compiler self frames only. Inlining/indirect FS providers mean no full chain/highwater/heap conclusion.','known_source_chains':['emitted_checked -> describe_checked -> index_row -> index_read_row -> index_read_at -> disc_read -> fs_seek/read','ensure_disc_catalog -> install_index -> fingerprint_read -> index_stream_read -> index_read_at -> disc_read']}
 check();report['complete']=True;report['owned_output_bytes']=usage(out);save();print('COMPLETE16 selected arms; no full link/heap/guest acceptance',flush=True)

if __name__=='__main__':
 plan=preparation();(OWN/'CATALOG24-TARGET-PREPARATION.json').write_text(json.dumps(plan,indent=2)+'\n')
 if '--prepare' in sys.argv:print('PREPARED16 arms, no SDK command; source/pins/actual commands verified')
 else:run(plan)
