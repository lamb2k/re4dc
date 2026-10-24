"""One grant-gated serial QA pair; owns one canonical lease and one SDK slot."""
from pathlib import Path
import argparse,fcntl,json,os,signal,time
import common as c
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
    commands=[([str(TOOLS/'sh-elf-objcopy'),'-R','.stack','-O','binary',str(elf),str(raw)],ad/'objcopy.log'),([str(TOOLS/'sh-elf-nm'),'-S',str(elf)],a/'symbols.txt'),([str(TOOLS/'sh-elf-size'),str(elf)],a/'size.txt'),([str(TOOLS/'sh-elf-size'),'-A',str(elf)],a/'sections.txt'),(['/usr/bin/python3','-B',str(c.HERE/'postbuild.py'),'--arm',arm,'--output',str(ad/'postbuild.json')],ad/'postbuild.log')]
    for argv,log in commands:event(dict(arm=arm,analysis_argv=argv));c.run_owned(argv,c.HERE,env,log,c.ROOT,budget,started,sample)
    post=json.loads((ad/'postbuild.json').read_text());c.require(post['complete'] is True,'Incomplete postbuild');c.check_inputs(plan);c.boundaries(sample(c.ROOT),budget,time.monotonic()-started)
    report['arms'][arm].update(complete=True,seconds=time.monotonic()-started,postbuild_sha256=c.sha(ad/'postbuild.json'),files=post['files'],addresses=post['ELF']['addresses'],sizes=post['ELF']['sizes']);event(dict(arm=arm,status='COMPLETE'))
   c.finishable(report['arms']);c.check_inputs(plan);report['delta']={k:report['arms']['on']['sizes'][k]-report['arms']['off']['sizes'][k] for k in ['text','data','bss']};report['linked_end_delta']=report['arms']['on']['addresses']['_end']-report['arms']['off']['addresses']['_end'];report['owned_bytes']=c.used(c.ROOT)+c.used(c.HERE)+(c.used(c.HOST_ROOT) if c.HOST_ROOT.exists() else 0);report['complete']=True
  except BaseException as e:report['complete']=False;report['failure']=repr(e);raise
  finally:event(dict(status='FINAL',complete=report['complete']));journal.close();c.exclusive_json(result/'receipt.json',report)
 finally:
  for h in reversed(locks):h.close()
if __name__=='__main__':main()
