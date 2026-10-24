"""Source-only preparation: Git exports, read-only hashes and exact dead-option block."""
from pathlib import Path
import copy, hashlib, json, os, re, shlex, subprocess, tarfile, tempfile

HERE=Path(__file__).resolve().parent
LANE=HERE.parent
TREE=Path('/root/work/lanes/gc-motion24')
SOURCE='aab201ceac0e18107f64a3212398afe916793327'
SUB=Path('/root/work/lanes/gc-port23/port/dreamcast/game/third_party/sh4zam')
SUBREV='33fa4850cacb30dd0ad35485ef035526ec4ce782'
QA=Path('/dev/shm/gc-motion24-qa-memory-v2-dbqczoc8')
NORMAL=Path('/dev/shm/gc-motion24-full-pair-wrf50x14')
AUDIT=LANE/'kos-failure-audit-v1'
QA_TOOLS=LANE/'qa-memory-media-prep'

def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def row(p):return {'bytes':Path(p).stat().st_size,'sha256':sha(p)}
def read(p):return json.loads(Path(p).read_text())
def git(tree,*a):return subprocess.check_output(['git','-C',str(tree),*a])
def free(p):s=os.statvfs(p);return s.f_bavail*s.f_frsize
def used(p):return sum(q.stat().st_size for q in Path(p).rglob('*') if q.is_file() and not q.is_symlink())
def verify(pins):
 for p,pin in pins.items():assert row(p)==pin,('input changed',p)
def emit(p,j):Path(p).open('x').write(json.dumps(j,indent=1)+'\n')
def export(tree,rev,target):
 target.mkdir(parents=True)
 child=subprocess.Popen(['git','-C',str(tree),'archive','--format=tar',rev],stdout=subprocess.PIPE)
 with tarfile.open(fileobj=child.stdout,mode='r|') as stream:stream.extractall(target,filter='data')
 assert child.wait()==0

def actual_preflight(source,argv):
 """Only original R21 assignment and KNOWN/DEAD code, before env source/Make."""
 script=source/'port/dreamcast/tools/d367/build-r21.sh';text=script.read_text()
 start=text.index('R21=(');end=text.index('\n)',start)+2
 checks=text[text.index('KNOWN=$(cat '):text.index('make -C port/dreamcast/game -j')]
 snippet='set -euo pipefail\n'+text[start:end]+'\n'+checks
 assert not any(s in snippet for s in ['make -C','environ.sh','kos-env.sh','re4dc-knobs'])
 env={'PATH':'/usr/bin:/bin','HOME':'/root','LANG':'C','ASSETS':'/root/probe/lanes/play-actor-bundle',
      'ROOT':str(source),'OBJDIR':str(source.parent/'out/obj'),'OUT':str(source.parent/'out')}
 result=subprocess.run(['bash','-c',snippet,'exact-dead-option-check',*argv[2:]],cwd=source,env=env,capture_output=True,text=True,timeout=30)
 return {'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr,
   'script_sha256':sha(script),'snippet_sha256':hashlib.sha256(snippet.encode()).hexdigest(),
   'SDK_or_Make_or_env_source':False}

def semantic(plan):
 assert plan['source']==SOURCE and plan['arm_order']==['off','on'] and not plan['object_reuse']
 assert plan['budget']=={'owned_bytes_cap':2*1024**3,'C_admission_bytes':26*1024**3,'C_floor_bytes':24*1024**3,
     'RAM_admission_bytes':3*1024**3,'RAM_floor_bytes':512*1024**2,'per_arm_seconds':600,'jobs':1,
     'shared_slots':1,'canonical_tree_lease':str(TREE)}
 assert Path(plan['root']).parent==Path('/dev/shm') and Path(plan['root']).name.startswith('gc-motion24-kos-census-v1-')
 for arm in plan['arm_order']:
  argv=plan['commands'][arm];tokens=plan['proposal_tokens'][arm]
  assert argv==['bash',str(Path(plan['root'])/arm/'source/port/dreamcast/tools/d367/build-r21.sh'),*tokens]
  flags=dict(x.split('=',1) for x in tokens)
  assert flags==plan['final_caller_values'][arm]
  assert flags['KOS_CENSUS']=='1' and flags['KOS_SQUEEZE']=='1'
  assert flags['KOS_SQUEEZE_BYTES']==flags['KOS_SQUEEZE_FRAG']=='0'
  assert flags['GC_ASSET_GATE']==flags['GC_ASSET_MOTION_UNKNOWN']==str(int(arm=='on'))
  assert flags['GC_ASSET_CATALOG_SHA256']=='0' and flags['KOS_CACHE_P2_DIAG']=='0'
  assert not any(t.startswith(('OUT=','OBJDIR=','TARGET=','KOS_HEAP_CHECK=')) for t in tokens)
  assert plan['environment'][arm]['JOBS']=='1'
 assert [(a,b) for a,b in zip(plan['proposal_tokens']['off'],plan['proposal_tokens']['on']) if a!=b]==[
   ('GC_ASSET_GATE=0','GC_ASSET_GATE=1'),('GC_ASSET_MOTION_UNKNOWN=0','GC_ASSET_MOTION_UNKNOWN=1')]
 return True

def main():
 assert not (HERE/'PREPARATION.json').exists()
 assert git(TREE,'rev-parse','HEAD').decode().strip()==SOURCE and not git(TREE,'status','--porcelain')
 assert free('/mnt/c')>=26*1024**3 and free('/dev/shm')>=3*1024**3
 proposal=read(AUDIT/'NEXT-DIAGNOSTIC-PAIR.json');old=read(QA/'PREPARATION.json')
 assert proposal['source']==old['source']==SOURCE
 pins=dict(old['input_pins']);verify(pins)
 def pin(p):pins[str(p)]=row(p)
 # Preserve original audit and existing programme identities without mutation.
 preserved={}
 for root,names in [(AUDIT,['CAPTURE-ARITHMETIC.json','SOURCE-BINARY-READBACK.json','NEXT-DIAGNOSTIC-PAIR.json','SELECTED-LIBC-DISASSEMBLY.txt']),
   (QA,['PREPARATION.json','qa-receipt.json']),(NORMAL,['PREPARATION.json','receipt.json','continuation-v1/receipt.json'])]:
  for n in names:preserved[str(root/n)]=row(root/n)
 for root in [QA,NORMAL]:
  for arm in ['off','on']:
   for p in [root/arm/'program.bin',root/arm/'build.log',root/arm/'command.json',root/arm/'out/re4dc-game.elf',root/arm/'out/resolved-knobs.txt',*(root/arm/'out').glob('*.ovl')]:preserved[str(p)]=row(p)
 # Exact actual .d inventory; current non-system external dependencies are new prehashes.
 oldcensus=read(QA_TOOLS/'DEPENDENCY-CENSUS.json');depfiles={};external={};unretained=[]
 for group,root,names in [('QA',QA,['baseline','off','on']),('normal',NORMAL,['off','on'])]:
  for arm in names:
   actual=sorted((root/arm/'out').rglob('*.d'));prior=oldcensus['arms'][group+'-'+arm]
   assert {str(p) for p in actual}=={r['path'] for r in prior['dependency_files']}
   for p in actual:
    depfiles[str(p)]=row(p)
    logical=p.read_text().replace('\\\n',' ').splitlines()[0]
    target,items=logical.split(':',1)
    for token in shlex.split(items):
     q=Path(token);q=(q if q.is_absolute() else root/arm/'source/port/dreamcast/game'/q).resolve()
     if q.is_relative_to(root/arm/'source') or q.is_relative_to(root/arm/'out'):
      if not q.exists():
       assert '/platform/sdk/gen/' in str(q) and q.suffix=='.c'
       unretained.append(str(q))
      continue
     assert q.is_file();external[str(q)]=row(q);pin(q)
 # All six historical omissions, the exact EOL bridge and pg5 generator inputs are bound afresh.
 for p in oldcensus['unrecorded_externals']:pin(Path(p))
 pg5=Path('/root/probe/lanes-20261010/ps2cast-all-assets/pg5')
 for p in sorted(pg5.rglob('*')):
  if p.is_file():pin(p)
 for name in ['DEPENDENCY-CENSUS.json','HAIR-EOL-BRIDGE.json','SIX-KEY-SUPPLEMENT.json','ROOT-SUPPLEMENTAL-CLOSURE-v1.json']:
  pin(QA_TOOLS/name)
 bridge=read(QA_TOOLS/'HAIR-EOL-BRIDGE.json');hair=Path(bridge['current']['path']);hb=hair.read_bytes()
 assert row(hair)=={k:bridge['current'][k] for k in ['bytes','sha256']}
 assert b'\r' not in hb and hashlib.sha256(hb.replace(b'\n',b'\r\n')).hexdigest()==bridge['reconstructed_historical']['sha256']
 # Source/sysroot inputs from original SDK pins are verified, not refreshed silently.
 for name in ['make','bash','grep','sort','sed','awk','sha256sum','flock','md5sum','timeout']:
  pin(Path('/usr/bin')/name)
 pin(Path('/root/probe/d367-buildslot.sh'))
 root=Path(tempfile.mkdtemp(prefix='gc-motion24-kos-census-v1-',dir='/dev/shm'))
 manifests={};commands={};envs={};basewraps={}
 for arm in ['off','on']:
  src=root/arm/'source';export(TREE,SOURCE,src)
  sub=src/'port/dreamcast/game/third_party/sh4zam'
  if sub.exists():sub.rmdir()
  export(SUB,SUBREV,sub)
  manifests[arm]={p.relative_to(src).as_posix():row(p) for p in src.rglob('*') if p.is_file()}
  assert manifests[arm]==old['source_manifests'][arm]
  assert not (root/arm/'out').exists() and not (src/'port/dreamcast/game/obj').exists() and not list(src.rglob('*.o'))
  original=proposal['commands'][arm];assert row(original['original_command_file'])['sha256']==original['original_sha256']
  original_argv=read(original['original_command_file'])
  assert original_argv[2:]+['KOS_CENSUS=1']==original['ordered_tokens']
  commands[arm]=['bash',str(src/'port/dreamcast/tools/d367/build-r21.sh'),*original['ordered_tokens']]
  envs[arm]={'PATH':'/usr/bin:/bin','HOME':'/root','USER':'root','LANG':'C','LC_ALL':'C','TERM':'dumb',
   'ASSETS':'/root/probe/lanes/play-actor-bundle','OUT':str(root/arm/'out'),'OBJDIR':str(root/arm/'out/obj'),
   'JOBS':'1','SOURCE_DATE_EPOCH':'1760000000','PYTHONDONTWRITEBYTECODE':'1','RE4DC_KOS_BASE':'/root/work/kos-re4dc-d367',
   'TMPDIR':str(root/arm/'tmp')}
  oldlink=next(x for x in (QA/arm/'build.log').read_text().splitlines() if 'bash tools/link.sh ' in x)
  basewraps[arm]=re.findall(r'-Wl,--wrap=([A-Za-z0-9_]+)',oldlink)
 plan={'status':'PREPARED_NOT_RUN_ATTRIBUTION_ONLY','source':SOURCE,'submodule':SUBREV,'root':str(root),'arm_order':['off','on'],
  'commands':commands,'proposal_tokens':{a:proposal['commands'][a]['ordered_tokens'] for a in ['off','on']},
  'final_caller_values':{a:dict(x.split('=',1) for x in commands[a][2:]) for a in ['off','on']},'environment':envs,
  'source_manifests':manifests,'input_pins':pins,'preserved_artifacts':preserved,'actual_existing_d_files':depfiles,
  'external_actual_d_dependencies':external,'unretained_generated_SDK_intermediates':sorted(set(unretained)),
  'historical_omissions':list(oldcensus['unrecorded_externals']),'historical_EOL_disclosure':'Current LF bytes freshly pinned; exact invertible CRLF bridge retained. No retroactive prehash claim.',
  'baseline_wraps':basewraps,'expected_raw_object_counts':{'off':449,'on':455},'expected_overlays':old['expected_overlays'],
  'budget':{'owned_bytes_cap':2*1024**3,'C_admission_bytes':26*1024**3,'C_floor_bytes':24*1024**3,'RAM_admission_bytes':3*1024**3,
   'RAM_floor_bytes':512*1024**2,'per_arm_seconds':600,'jobs':1,'shared_slots':1,'canonical_tree_lease':str(TREE)},
  'object_reuse':False,'future_fixture':proposal['future_fixture'],'no_SDK_or_Make_or_env_source':True,
  'limits':'Attribution diagnostic only. Not original memory/performance/coverage/guest/staging qualification; future final ELF must prove mode1 reentrant routes. Census loss/row overflow/unreconciled bytes remain UNKNOWN.'}
 semantic(plan)
 plan['dead_option_preflight']={a:actual_preflight(root/a/'source',commands[a]) for a in ['off','on']}
 assert all(v['returncode']==0 for v in plan['dead_option_preflight'].values())
 wrong=actual_preflight(root/'off/source',commands['off']+['KOS_CENSUS_TYP0=1'])
 assert wrong['returncode']==1 and 'KOS_CENSUS_TYP0' in wrong['stderr']
 plan['dead_option_negative']=wrong
 assert used(root)<2*1024**3 and free('/mnt/c')>=24*1024**3 and free('/dev/shm')>=512*1024**2
 emit(HERE/'PREPARATION.json',plan);emit(root/'PREPARATION.json',plan)
 emit(HERE/'PREPARATION-RECEIPT.json',{'status':'SOURCE_EXPORT_AND_EXACT_DEAD_OPTION_PREFLIGHT_PASS_NOT_RUN','root':str(root),
  'source_files_per_arm':{a:len(m) for a,m in manifests.items()},'source_bytes_per_arm':{a:sum(r['bytes'] for r in m.values()) for a,m in manifests.items()},
  'input_pins':len(pins),'actual_existing_d_files':len(depfiles),'current_external_d_dependencies':len(external),
  'six_historical_omissions':len(plan['historical_omissions']),'pg5_files':len([p for p in pg5.rglob('*') if p.is_file()]),
  'plan_sha256':sha(HERE/'PREPARATION.json'),'owned_bytes':used(root),'SDK_or_Make_or_env_source_or_stage_or_guest':False})
 print((HERE/'PREPARATION-RECEIPT.json').read_text())
if __name__=='__main__':main()
