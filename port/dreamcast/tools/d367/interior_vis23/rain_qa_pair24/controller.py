"""One grant-gated serial QA pair; owns one canonical lease and one SDK slot."""
import sys
if __name__=='__main__' and not (sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode):
 raise SystemExit('Controller requires isolated -I -S -B startup')
from pathlib import Path
import argparse,fcntl,json,os,signal,time,hashlib,types
# Authenticate exact source bytes, never SourceFileLoader or adjacent bytecode.
COMMON_SOURCE_SHA256='2d01c267f6ea24b68abe201680bfe29660ad6d3a25f58918ba7bf407ee9b0b87'
POSTBUILD_SOURCE_SHA256='fcb3df088f732e2454f42501c20e2ad833e38aeb623ee3eb2808beab5cc458b2'
_common_path=Path(__file__).resolve().with_name('common.py')
_common_source=_common_path.read_bytes()
if hashlib.sha256(_common_source).hexdigest()!=COMMON_SOURCE_SHA256:raise SystemExit('Common helper source changed')
if 'common' in sys.modules:
 c=sys.modules['common']
 if Path(c.__file__).resolve()!=_common_path:raise ImportError('Foreign cached common module')
else:c=types.ModuleType('common')
c.__file__=str(_common_path);sys.modules['common']=c
exec(compile(_common_source,str(_common_path),'exec',dont_inherit=True),c.__dict__)
POST_BOOTSTRAP="""import hashlib,pathlib,sys,types
script=pathlib.Path(sys.argv.pop(1)).resolve()
def load_source(name,path,expected):
 raw=path.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=expected:raise SystemExit('Authenticated helper source changed: '+str(path))
 module=types.ModuleType(name);module.__file__=str(path);sys.modules[name]=module
 exec(compile(raw,str(path),'exec',dont_inherit=True),module.__dict__)
 return module
load_source('common',script.with_name('common.py'),'2d01c267f6ea24b68abe201680bfe29660ad6d3a25f58918ba7bf407ee9b0b87')
sys.argv[0]=str(script)
load_source('__main__',script,'fcb3df088f732e2454f42501c20e2ad833e38aeb623ee3eb2808beab5cc458b2')
"""

def postbuild_command(arm,output):
 return ['/usr/bin/python3','-I','-S','-B','-c',POST_BOOTSTRAP,str(c.HERE/'postbuild.py'),'--arm',arm,'--output',str(output)]
TOOLS=Path('/opt/toolchains/dc/sh-elf/bin')
def check_grant(g,contract,digest,seal_sha):
 c.require(g.get('approved') is True and isinstance(g.get('grant_id'),str) and g['grant_id'] not in ['', 'ROOT_MUST_ASSIGN_UNIQUE_ID'] and g.get('authorization')=='SDK_QA_RAIN_OFF_ON' and g.get('source')==c.SOURCE and g.get('root')==str(c.ROOT) and g.get('contract_sha256')==digest and g.get('kit_seal_sha256')==seal_sha and g.get('budget')==contract['budget'],'Wrong root QA grant')

def authorize(contract):
 digest=c.sha(c.HERE/'CONTRACT.json');c.require(os.environ.get('RAIN8CE_QA_ALLOCATED')==digest,'Root QA allocation required')
 grant=Path(os.environ.get('RAIN8CE_QA_ROOT_GRANT','/nonexistent'));c.require(grant.is_file() and c.sha(grant)==os.environ.get('RAIN8CE_QA_GRANT_SHA256'),'Pinned root grant required')
 g=json.loads(grant.read_text());check_grant(g,contract,digest,c.sha(c.HERE/'KIT-SEAL.json'))
 c.require(not any(os.environ.get(k) for k in c.REFUSED_ENV),'Inherited build/compiler injection refused')
 seal=json.loads((c.HERE/'KIT-SEAL.json').read_text());c.verify({str(c.HERE/k):v for k,v in seal['files'].items()});return dict(grant=str(grant),sha256=c.sha(grant))
def acquire(contract):
 handles=[]
 try:
  lease=open(contract['canonical_lock'],'a+');handles.append(lease);fcntl.flock(lease,fcntl.LOCK_EX|fcntl.LOCK_NB)
  slot=None
  for path in contract['shared_slots']:
   h=open(path,'a+')
   try:fcntl.flock(h,fcntl.LOCK_EX|fcntl.LOCK_NB)
   except BlockingIOError:h.close();continue
   handles.append(h);slot=path;break
  c.require(slot is not None,'No shared SDK slot available')
  return handles,slot
 except BaseException:
  for h in handles:h.close()
  raise

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--execute',action='store_true',required=True);ap.parse_args()
 def stop(sig,frame):raise InterruptedError('Controller signal '+str(sig))
 for sig in [signal.SIGTERM,signal.SIGHUP,signal.SIGINT]:signal.signal(sig,stop)
 contract=json.loads((c.HERE/'CONTRACT.json').read_text());auth=authorize(contract);plan=c.load();locks,slot=acquire(contract)
 try:
  budget=plan['budget']
  result=c.contained(c.ROOT,c.ROOT/'qa-pair-result-v1');result.mkdir(exist_ok=False)
  report=dict(complete=False,source=c.SOURCE,contract_sha256=c.sha(c.HERE/'CONTRACT.json'),preparation_sha256=c.PLAN_SHA,authorization=auth,canonical_lease=contract['canonical_lock'],slot=slot,arms={},scope='QA rain programme only; no staging/guest/cache/heap/physical acceptance')
  journal=(result/'journal.jsonl').open('x')
  def event(o):journal.write(json.dumps(o)+'\n');journal.flush()
  try:
   c.check_inputs(plan);c.boundaries(c.resources(c.ROOT),budget,admission=True)
   for arm in ['off','on']:
    c.check_inputs(plan);a=c.ROOT/arm;out=a/'out';scratch=a/'source/port/dreamcast/game/obj'
    c.fresh_arm(a)
    c.boundaries(c.resources(c.ROOT),budget,admission=True)
    ad=result/arm;ad.mkdir();tmp=ad/'tmp';tmp.mkdir();started=time.monotonic();env=c.clean_environment(plan,arm,tmp);command=plan['commands'][arm];c.exclusive_json(a/'command.json',command)
    report['arms'][arm]=dict(complete=False,command_sha256=c.sha(a/'command.json'),environment=env,owned_tmpdir=str(tmp));event(dict(arm=arm,status='STARTED',argv=command))
    def sample(p):
     r=c.resources(p);event(dict(arm=arm,monotonic=time.monotonic(),resources=r));return r
    c.run_owned(command,a/'source',env,a/'build.log',c.ROOT,budget,started,sample)
    elf=out/'re4dc-game.elf';raw=a/'program.bin'
    commands=[([str(TOOLS/'sh-elf-objcopy'),'-R','.stack','-O','binary',str(elf),str(raw)],ad/'objcopy.log'),([str(TOOLS/'sh-elf-nm'),'-S',str(elf)],a/'symbols.txt'),([str(TOOLS/'sh-elf-size'),str(elf)],a/'size.txt'),([str(TOOLS/'sh-elf-size'),'-A',str(elf)],a/'sections.txt'),(postbuild_command(arm,ad/'postbuild.json'),ad/'postbuild.log')]
    for argv,log in commands:event(dict(arm=arm,analysis_argv=argv));c.run_owned(argv,c.HERE,env,log,c.ROOT,budget,started,sample)
    post=json.loads((ad/'postbuild.json').read_text());c.require(post['complete'] is True,'Incomplete postbuild');c.check_inputs(plan);c.boundaries(sample(c.ROOT),budget,time.monotonic()-started)
    report['arms'][arm].update(complete=True,seconds=time.monotonic()-started,postbuild_sha256=c.sha(ad/'postbuild.json'),files=post['files'],addresses=post['ELF']['addresses'],sizes=post['ELF']['sizes']);event(dict(arm=arm,status='COMPLETE'))
   c.finishable(report['arms']);c.check_inputs(plan);report['delta']={k:report['arms']['on']['sizes'][k]-report['arms']['off']['sizes'][k] for k in ['text','data','bss']};report['linked_end_delta']=report['arms']['on']['addresses']['_end']-report['arms']['off']['addresses']['_end'];report['owned_bytes']=c.used(c.ROOT)+c.used(c.HERE)+(c.used(c.HOST_ROOT) if c.HOST_ROOT.exists() else 0);report['complete']=True
  except BaseException as e:report['complete']=False;report['failure']=repr(e);raise
  finally:event(dict(status='FINAL',complete=report['complete']));journal.close();c.exclusive_json(result/'receipt.json',report)
 finally:
  for h in reversed(locks):h.close()
if __name__=='__main__':main()
