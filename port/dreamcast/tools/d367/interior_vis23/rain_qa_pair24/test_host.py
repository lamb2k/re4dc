"""Host-only tests of actual production controller/readback helpers. No SDK commands."""
from pathlib import Path
import collections,copy,fcntl,json,os,resource,signal,subprocess,sys,tempfile,time
import common as c
import controller as controller
import postbuild as p
resource.setrlimit(resource.RLIMIT_AS,(268435456,268435456));resource.setrlimit(resource.RLIMIT_CORE,(0,0));signal.alarm(120)
def main():
 started=time.monotonic();plan=c.load();assert not list(c.HOST_ROOT.rglob('*')) or all(not x.is_symlink() for x in c.HOST_ROOT.rglob('*'));c.HOST_ROOT.mkdir(exist_ok=True);root=Path(tempfile.mkdtemp(prefix='case-',dir=c.HOST_ROOT));checks=[]
 def passed(n,fn):fn();checks.append(dict(name=n,pass_=True))
 def reject(n,fn,types=(RuntimeError,FileExistsError,BlockingIOError)):
  try:fn()
  except types as e:checks.append(dict(name=n,refused=True,reason=str(e)))
  else:raise AssertionError(n+' escaped')
 b=plan['budget'];good=dict(C_free=64*1024**3,RAM_free=64*1024**3,owned_bytes=0,release_active=False)
 passed('admission',lambda:c.boundaries(good,b,admission=True))
 for name,key,value,admit in [('C26', 'C_free',25*1024**3,True),('RAM3GiB','RAM_free',2*1024**3,True),('C24','C_free',23*1024**3,False),('RAM512MiB','RAM_free',511*1024**2,False),('total2GiB','owned_bytes',2*1024**3+1,False),('release-priority','release_active',True,False)]:
  r=dict(good);r[key]=value;reject(name,lambda r=r,a=admit:c.boundaries(r,b,admission=a))
 reject('600seconds',lambda:c.boundaries(good,b,601))
 reject('pathescape',lambda:c.contained(root,root.parent/'escape'));reject('root-as-output',lambda:c.contained(root,root))
 f=root/'pin';f.write_bytes(b'exact');pin=c.identity(f);passed('hashpin',lambda:c.verify({str(f):pin}));reject('hashmutation',lambda:c.verify({str(f):dict(pin,sha256='0'*64)}))
 link=root/'directory-symlink';link.symlink_to('/tmp',target_is_directory=True);reject('directory-symlink',lambda:c.used(root));link.unlink()
 fresh=root/'fresh';fresh.mkdir();passed('fresh-arm',lambda:c.fresh_arm(fresh));(fresh/'build.log').write_text('preserved');reject('nonfresh-arm',lambda:c.fresh_arm(fresh));assert (fresh/'build.log').read_text()=='preserved'
 blank=root/'broken';blank.mkdir();(blank/'out').symlink_to(root/'absent',target_is_directory=True);reject('broken-output-symlink',lambda:c.fresh_arm(blank));(blank/'out').unlink()
 reject('incomplete-arms',lambda:c.finishable({'off':dict(complete=True)}));reject('failed-arm',lambda:c.finishable({'off':dict(complete=True),'on':dict(complete=False)}));passed('both-complete',lambda:c.finishable({'off':dict(complete=True),'on':dict(complete=True)}))
 original_path=os.environ.get('PATH');os.environ['PATH']='/tmp/untrusted'
 try:env=c.clean_environment(plan,'off',root/'tmp');assert env['PATH']=='/usr/bin:/bin' and 'MAKEFLAGS' not in env and env['JOBS']=='1' and env['PYTHONDONTWRITEBYTECODE']=='1';checks.append(dict(name='clean-env-does-not-inherit-PATH',pass_=True))
 finally:
  if original_path is None:os.environ.pop('PATH')
  else:os.environ['PATH']=original_path
 # Grant-field fixtures below are data tests, not actual allocation files.
 contract=json.loads((c.HERE/'CONTRACT.json').read_text());grant=dict(approved=True,authorization='SDK_QA_RAIN_OFF_ON',source=c.SOURCE,root=str(c.ROOT),contract_sha256='digest',kit_seal_sha256='seal',budget=contract['budget'],grant_id='HOST-ONLY-NOT-AN-ALLOCATION')
 passed('grant-field-fixture-positive-only',lambda:controller.check_grant(grant,contract,'digest','seal'))
 for key,value in [('approved',False),('source','0'*40),('root','/tmp/foreign'),('contract_sha256','wrong'),('kit_seal_sha256','wrong'),('authorization','SDK_FULL_NORMAL_OFF_ON'),('grant_id','ROOT_MUST_ASSIGN_UNIQUE_ID'),('budget',dict(contract['budget'],per_arm_seconds=601))]:
  bad=dict(grant);bad[key]=value;reject('grant-'+key,lambda bad=bad:controller.check_grant(bad,contract,'digest','seal'))
 # Actual retained same-QA graph: 568 compilations,449 ordered links,14 overlays.
 qa=Path(plan['reference']['root']);hist=copy.deepcopy(plan);hist['root']=str(qa);log=(qa/'off/build.log').read_text();passed('actual-QA568-449-14',lambda:p.graph(log,hist,'off'))
 for name,old,new in [('wrong-argv','-ffp-contract=off','-ffast-math'),('wrong-overlay','gen_overlay: .ovl_pl0f','gen_overlay: .ovl_extra'),('OFF-rain',' -c ../../../src/game/filter06.cpp ',' -DRE4DC_RAIN_R10C_DIAG=1 -c ../../../src/game/filter06.cpp ')]:
  assert old in log;bad=log.replace(old,new,1);reject(name,lambda bad=bad:p.graph(bad,hist,'off'))
 bad=log.replace(' -c ../../../src/game/filter06.cpp ',' -DRE4DC_GC_ASSET_GATE=1 -c ../../../src/game/filter06.cpp ',1);reject('GC-on-macro',lambda:p.graph(bad,hist,'off'))
 names=[x.lower()+'.ovl' for x in plan['overlay_order']];passed('all14',lambda:p.overlays(names,plan));reject('missing-overlay',lambda:p.overlays(names[:-1],plan));reject('extra-overlay',lambda:p.overlays(names+['extra.ovl'],plan))
 for name in sorted(p.HELPERS):passed('actual-empty-'+name,lambda name=name:p.helper_identity(qa/'off/out/obj/platform'/(name+'.o')))
 reject('actual-nonempty-helper',lambda:p.helper_identity(qa/'on/out/obj/platform/gc_asset_motion_unknown.o'))
 e=p.e.elf(qa/'off/out/re4dc-game.elf',True);passed('actual-QA-OFF-ELF-raw',lambda:p.raw_identity(e,qa/'off/program.bin'));bad=copy.deepcopy(e);bad['raw_from_ELF']['sha256']='0'*64;reject('wrong-raw',lambda:p.raw_identity(bad,qa/'off/program.bin'))
 normal=Path('/dev/shm/rain8ce-full-normal-179r4a5c/on/out/re4dc-game.elf');ne=p.e.elf(normal);record=[s for s in p.fullsymbols(normal) if s['name']=='_re4dc_rain_r10c_diag'];passed('actual-normal-record-static-positive',lambda:p.validate_rain(record,ne['allocated_sections'],True));passed('absent-OFF-record',lambda:p.validate_rain([],ne['allocated_sections'],False));reject('OFF-retained-record',lambda:p.validate_rain(record,ne['allocated_sections'],False))
 for name,change in [('size',dict(bytes=127)),('binding',dict(info=0x10)),('visibility',dict(other=1)),('alignment',dict(value=record[0]['value']+4)),('P2',dict(value=0xac000000)),('outsideP1',dict(value=0x8d000000)),('outsideBSS',dict(value=0x8c000000))]:
  v=[dict(record[0],**change)];reject('record-'+name,lambda v=v:p.validate_rain(v,ne['allocated_sections'],True))
 # Actual retained QA dependency graph uses its own original source manifest.
 qp=json.loads((qa/'PREPARATION.json').read_text());depplan=copy.deepcopy(hist);depplan['source_manifest']=qp['source_manifests']['off'];dep=p.dependencies(depplan,'off');assert len(dep['files'])==516;checks.append(dict(name='actual-retained-QA516-dependency-files',pass_=True))
 external=next(x for x,y in dep['dependencies'].items() if y['kind']=='exact-external');bad=copy.deepcopy(depplan);bad['input_pins'].pop(external);reject('unrecorded-external',lambda:p.dependencies(bad,'off'))
 # Synthetic lease and slot paths only; no production lock acquired by tests.
 locks=root/'locks';locks.mkdir();contract=dict(canonical_lock=str(locks/'lease'),shared_slots=[str(locks/'slot1'),str(locks/'slot2')]);handles,slot=controller.acquire(contract);assert slot==contract['shared_slots'][0];reject('canonical-already-held',lambda:controller.acquire(contract));[h.close() for h in handles]
 one=open(contract['shared_slots'][0],'a+');fcntl.flock(one,fcntl.LOCK_EX|fcntl.LOCK_NB);handles,slot=controller.acquire(contract);assert slot==contract['shared_slots'][1] and len(handles)==2;[h.close() for h in handles];two=open(contract['shared_slots'][1],'a+');fcntl.flock(two,fcntl.LOCK_EX|fcntl.LOCK_NB);reject('both-slots-held',lambda:controller.acquire(contract));one.close();two.close();checks.append(dict(name='exactly-one-available-slot',pass_=True))
 # Exercise production run_owned with only absolute host Python children.
 sample=lambda _:dict(good);hostenv=dict(PATH='/usr/bin:/bin');argv=['/usr/bin/python3','-B','-c','pass'];passed('host-child-success',lambda:c.run_owned(argv,root,hostenv,root/'success.log',root,b,time.monotonic(),sample));reject('host-child-failure',lambda:c.run_owned(['/usr/bin/python3','-B','-c','raise SystemExit(7)'],root,hostenv,root/'failure.log',root,b,time.monotonic(),sample));reject('log-no-overwrite',lambda:c.run_owned(argv,root,hostenv,root/'success.log',root,b,time.monotonic(),sample))
 observed=[];original=c.subprocess.Popen
 def capture(argv,*a,**kw):
  assert argv[0]=='/usr/bin/python3','No SDK command allowed in host tests';ch=original(argv,*a,**kw);observed.append(ch);return ch
 sibling=original(['/usr/bin/python3','-B','-c','import time;time.sleep(30)'],start_new_session=True);c.subprocess.Popen=capture
 try:
  calls=[0]
  def cap(_):calls[0]+=1;return dict(good,owned_bytes=2*1024**3+1 if calls[0]>=2 else 0)
  reject('inflight-cap',lambda:c.run_owned(['/usr/bin/python3','-B','-c','import time;time.sleep(30)'],root,hostenv,root/'cap.log',root,b,time.monotonic(),cap));assert observed[-1].poll() is not None and sibling.poll() is None
  reject('inflight-deadline',lambda:c.run_owned(['/usr/bin/python3','-B','-c','import time;time.sleep(30)'],root,hostenv,root/'deadline.log',root,dict(b,per_arm_seconds=.1),time.monotonic(),sample));assert observed[-1].poll() is not None and sibling.poll() is None
  # Leader exits normally after creating an owned grandchild. It must be killed.
  pidfile=root/'grandchild.pid';code="import subprocess;from pathlib import Path;p=subprocess.Popen(['/usr/bin/python3','-B','-c','import time;time.sleep(30)']);Path("+repr(str(pidfile))+").write_text(str(p.pid))"
  passed('leader-exit-owned-grandchild-cleanup',lambda:c.run_owned(['/usr/bin/python3','-B','-c',code],root,hostenv,root/'grandchild.log',root,b,time.monotonic(),sample));pid=int(pidfile.read_text());stat=Path('/proc')/str(pid)/'stat';assert not stat.exists() or stat.read_text().split()[2]=='Z';assert sibling.poll() is None;checks.append(dict(name='sibling-unaffected',pass_=True))
 finally:c.subprocess.Popen=original;c.terminate(sibling)
 env={k:v for k,v in os.environ.items() if not k.startswith('RAIN8CE_QA_')};env['PYTHONDONTWRITEBYTECODE']='1';q=subprocess.run(['/bin/bash',str(c.HERE/'execute.sh')],env=env,text=True,capture_output=True,timeout=5);assert q.returncode!=0 and 'ROOT_QA_GRANT_REQUIRED' in q.stderr;checks.append(dict(name='wrapper-no-grant-before-SDK',pass_=True));(root/'grant-refusal.log').write_text(q.stderr)
 # Execute actual controller setup with explicit host-only auth/lock/input mocks.
 # It must preserve an authorized preflight failure before any child can start.
 sim=root/'preflight';sim.mkdir();oldroot=c.ROOT;oldload=c.load;oldcheck=c.check_inputs;oldauthorize=controller.authorize;oldacquire=controller.acquire;oldargv=sys.argv[:]
 try:
  c.ROOT=sim;c.load=lambda:plan;controller.authorize=lambda _:dict(scope='HOST-FIXTURE-NOT-ALLOCATION');controller.acquire=lambda _:([],'HOST-FIXTURE-NOT-SDK')
  def preflight_fail(_):raise RuntimeError('HOST_FORCED_PREFLIGHT_PIN_REFUSAL')
  c.check_inputs=preflight_fail;sys.argv=['controller.py','--execute'];reject('authorized-preflight-preserved',controller.main)
  failure=json.loads((sim/'qa-pair-result-v1/receipt.json').read_text());assert failure['complete'] is False and 'HOST_FORCED_PREFLIGHT_PIN_REFUSAL' in failure['failure'] and failure['arms']=={}
 finally:c.ROOT=oldroot;c.load=oldload;c.check_inputs=oldcheck;controller.authorize=oldauthorize;controller.acquire=oldacquire;sys.argv=oldargv
 env=dict(os.environ,RAIN8CE_QA_ROOT_GRANT='/nonexistent',RAIN8CE_QA_GRANT_SHA256='0'*64,RAIN8CE_QA_ALLOCATED='0'*64);q=subprocess.run(['/bin/bash',str(c.HERE/'execute.sh')],env=env,text=True,capture_output=True,timeout=5);assert q.returncode!=0 and 'Root QA allocation required' in q.stderr and 'usage:' not in q.stderr;checks.append(dict(name='wrapper-actual-controller-clean-execute-argument',pass_=True));(root/'wrong-allocation-refusal.log').write_text(q.stderr)
 c.check_inputs(plan);checks.append(dict(name='all-current-inputs-source-SDK-and-reference-pins',pass_=True));assert not list(c.ROOT.rglob('*.pyc')) and not list(c.HERE.rglob('*.pyc'));checks.append(dict(name='no-bytecache',pass_=True))
 result=dict(status='HOST_ONLY_PASS',count=len(checks),checks=checks,root=str(root),seconds=time.monotonic()-started,limits=dict(address_space=268435456,process_seconds=120),SDK_commands=0,Make_queries=0,bootstrap=0,staging=0,guest=0,scope='Host orchestration/static retained evidence; not new QA build or target execution')
 c.exclusive_json(c.HERE/'HOST-CONTROLS-SEALED.json',result);print(json.dumps({k:v for k,v in result.items() if k!='checks'}))
if __name__=='__main__':main()
