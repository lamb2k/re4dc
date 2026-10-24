"""Grant-only serial fresh builds. Import does not execute SDK tools."""
from pathlib import Path
import argparse,fcntl,json,os,sys,time,signal
import common as c
TOOLS=Path('/opt/toolchains/dc/sh-elf/bin')

def authorization(contract):
 digest=c.sha(c.HERE/'CONTRACT.json');c.require(os.environ.get('RAIN8CE_FULL_ALLOCATED')==digest,'Root allocation required')
 grant=Path(os.environ.get('RAIN8CE_ROOT_GRANT','/nonexistent'));c.require(grant.is_file() and c.sha(grant)==os.environ.get('RAIN8CE_GRANT_SHA256'),'Pinned root grant required')
 g=json.loads(grant.read_text());c.require(g.get('approved') is True and g.get('source')==c.SOURCE and g.get('contract_sha256')==digest and g.get('authorization')=='SDK_FULL_NORMAL_OFF_ON','Wrong root grant')
 c.require(os.readlink('/proc/self/fd/7')==contract['canonical_lock'],'Canonical lease descriptor required');fcntl.flock(7,fcntl.LOCK_EX|fcntl.LOCK_NB)
 held=[]
 for fd in [8,9]:
  try:path=os.readlink('/proc/self/fd/'+str(fd))
  except FileNotFoundError:continue
  if path in ['/root/probe/d367-build.lock','/root/probe/d367-build2.lock']:
   fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);held.append(path)
 c.require(len(held)==1 and os.environ.get('D367_SLOT_HELD')=='1','Exactly one actual shared SDK slot required')
 c.verify(contract['tool_pins']);return dict(grant=str(grant),sha256=c.sha(grant),slot=held[0])

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--execute',action='store_true',required=True);ap.parse_args()
 def interrupted(sig,frame):raise InterruptedError('Controller signal '+str(sig))
 signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGHUP,interrupted)
 contract=json.loads((c.HERE/'CONTRACT.json').read_text());auth=authorization(contract);plan=c.load();root=Path(plan['root']);budget=plan['budget']
 c.require(not any(os.environ.get(k) for k in contract['refused_environment']), 'Inherited compiler/build injection refused')
 c.check_inputs(plan);c.boundaries(c.resources(root),budget,admission=True)
 result=c.contained(root,root/contract['result_relative']);result.mkdir(exist_ok=False)
 report=dict(complete=False,source=c.SOURCE,preparation_sha256=c.PLAN_SHA,contract_sha256=c.sha(c.HERE/'CONTRACT.json'),controller_sha256=c.sha(__file__),authorization=auth,arms={},scope='Fresh normal rain pair linked programme price/identity only; no guest/cache execution/heap/coverage acceptance')
 journal=(result/'journal.jsonl').open('x')
 def event(obj):journal.write(json.dumps(obj)+'\n');journal.flush()
 try:
  for arm in ['off','on']:
   c.check_inputs(plan);a=root/arm;out=a/'out';scratch=a/'source/port/dreamcast/game/obj'
   c.require(not out.exists() and not scratch.exists() and not (a/'build.log').exists() and not (a/'program.bin').exists() and not (a/'command.json').exists(),'Fresh arm outputs required')
   adir=result/arm;adir.mkdir();tmp=adir/'tmp';tmp.mkdir();started=time.monotonic()
   env=os.environ.copy();env.update(plan['environment'][arm]);env['TMPDIR']=str(tmp);env['TMP']=str(tmp);env['TEMP']=str(tmp)
   command=plan['commands'][arm];c.exclusive_json(a/'command.json',command)
   report['arms'][arm]=dict(complete=False,command_sha256=c.sha(a/'command.json'),environment=plan['environment'][arm],owned_tmpdir=str(tmp));event(dict(arm=arm,status='STARTED',argv=command))
   def sample(p):
    r=c.resources(p);event(dict(arm=arm,monotonic=time.monotonic(),resources=r));return r
   c.run_owned(command,a/'source',env,a/'build.log',root,budget,started,sample)
   elf=out/'re4dc-game.elf';raw=a/'program.bin'
   analyses=[([str(TOOLS/'sh-elf-objcopy'),'-R','.stack','-O','binary',str(elf),str(raw)],adir/'objcopy.log'),([str(TOOLS/'sh-elf-nm'),'-S',str(elf)],a/'symbols.txt'),([str(TOOLS/'sh-elf-size'),str(elf)],a/'size.txt'),([str(TOOLS/'sh-elf-size'),'-A',str(elf)],a/'sections.txt')]
   for argv,log in analyses:
    event(dict(arm=arm,analysis_argv=argv));c.run_owned(argv,a/'source',env,log,root,budget,started,sample)
   argv=[sys.executable,'-B',str(c.HERE/'postbuild.py'),'--arm',arm,'--output',str(adir/'postbuild.json')]
   c.run_owned(argv,c.HERE,env,adir/'postbuild.log',root,budget,started,sample)
   post=json.loads((adir/'postbuild.json').read_text());c.require(post['complete'] is True,'Postbuild incomplete')
   c.check_inputs(plan);c.boundaries(c.resources(root),budget,time.monotonic()-started)
   report['arms'][arm].update(complete=True,seconds=time.monotonic()-started,postbuild=str(adir/'postbuild.json'),postbuild_sha256=c.sha(adir/'postbuild.json'),files=post['files'],addresses=post['ELF']['addresses'],sizes=post['ELF']['sizes']);event(dict(arm=arm,status='COMPLETE'))
  c.finishable(report['arms']);c.check_inputs(plan)
  report['delta']={k:report['arms']['on']['sizes'][k]-report['arms']['off']['sizes'][k] for k in ['text','data','bss']};report['linked_end_delta']=report['arms']['on']['addresses']['_end']-report['arms']['off']['addresses']['_end'];report['owned_bytes']=c.used(root);report['complete']=True
 except BaseException as exc:
  report['complete']=False;report['failure']=repr(exc);raise
 finally:
  event(dict(status='FINAL',complete=report['complete']));journal.close();c.exclusive_json(result/'receipt.json',report)
if __name__=='__main__':main()
