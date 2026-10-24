"""No SDK tests: actual production control functions and retained ELF/log evidence."""
from pathlib import Path
import copy,json,os,subprocess,sys,tempfile,time
import common as c
import postbuild as p

def main():
 plan=c.load();root=Path(tempfile.mkdtemp(prefix='case-',dir='/dev/shm/rain8ce-controller-host-owned-v1'));checks=[]
 def reject(name,fn,types=(RuntimeError,FileExistsError)):
  try:fn()
  except types:checks.append(name)
  else:raise AssertionError(name+' escaped')
 def passed(name,fn):fn();checks.append(name)
 budget=plan['budget'];good=dict(C_free=64*1024**3,RAM_free=64*1024**3,owned_bytes=0)
 passed('normal-boundaries',lambda:c.boundaries(good,budget,elapsed=0,admission=True))
 for name,key,value in [('C-admission','C_free',25*1024**3),('RAM-admission','RAM_free',2*1024**3),('owned-cap','owned_bytes',2*1024**3+1),('C-floor','C_free',23*1024**3),('RAM-floor','RAM_free',511*1024**2),('release-priority','release_active',True)]:
  values=dict(good);values[key]=value;reject(name,lambda v=values,n=name:c.boundaries(v,budget,admission=n.endswith('admission')))
 reject('deadline',lambda:c.boundaries(good,budget,elapsed=601))
 reject('outside-path',lambda:c.contained(root,root.parent/'escaped'))
 reject('root-as-output',lambda:c.contained(root,root))
 f=root/'pin';f.write_bytes(b'exact\n');r=c.identity(f);passed('exact-input-pin',lambda:c.verify({str(f):r}))
 reject('wrong-hash',lambda:c.verify({str(f):dict(r,sha256='0'*64)}))
 reject('wrong-source-size',lambda:c.verify({str(f):dict(r,bytes=999)}))
 link=root/'symlink';link.symlink_to('/tmp');reject('owned-symlink',lambda:c.used(root));link.unlink()
 reject('incomplete-arms',lambda:c.finishable({'off':{'complete':True}}))
 reject('child-failed-not-complete',lambda:c.finishable({'off':{'complete':True},'on':{'complete':False}}))
 passed('both-complete',lambda:c.finishable({'off':{'complete':True},'on':{'complete':True}}))
 names=[x.lower()+'.ovl' for x in plan['overlay_order']];passed('all14',lambda:p.overlays(names,plan));reject('missing-overlay',lambda:p.overlays(names[:-1],plan));reject('extra-overlay',lambda:p.overlays(names+['extra.ovl'],plan))
 # Actual retained normal compilation/link graph; mutations change actual log bodies.
 historical=Path('/dev/shm/gc-motion24-full-pair-wrf50x14');log=(historical/'off/build.log').read_text();hist=copy.deepcopy(plan);hist['root']=str(historical)
 passed('actual567-compile448-link14-overlay-graph',lambda:p.graph(log,hist,'off'))
 bad=log.replace(' -c ../../../src/game/filter06.cpp ',' -DRE4DC_RAIN_R10C_DIAG=1 -c ../../../src/game/filter06.cpp ');reject('OFF-rain-macro',lambda:p.graph(bad,hist,'off'))
 bad=log.replace('-ffp-contract=off','-ffast-math',1);reject('changed-actual-argv',lambda:p.graph(bad,hist,'off'))
 bad=log.replace('gen_overlay: .ovl_pl0f','gen_overlay: .ovl_extra',1);reject('overlay-pipeline-changed',lambda:p.graph(bad,hist,'off'))
 actualhelpers={x.stem for x in (historical/'off/out/obj/platform').glob('gc_asset_*.o')}
 assert actualhelpers==p.HELPERS;checks.append('all-six-actual-helper-names')
 for name in sorted(actualhelpers):passed('actual-empty-'+name,lambda name=name:p.helper_identity(historical/'off/out/obj/platform'/(name+'.o')))
 empty=historical/'off/out/obj/platform/gc_asset_motion_unknown.o';passed('actual-empty-helper-compiled-once',lambda:p.helper_identity(empty))
 nonempty=historical/'on/out/obj/platform/gc_asset_motion_unknown.o';reject('nonempty-helper',lambda:p.helper_identity(nonempty))
 actual=p.e.elf(historical/'off/out/re4dc-game.elf',True);passed('actual-ELF-stack-only-raw-extraction',lambda:p.raw_identity(actual,historical/'off/program.bin'))
 bad=copy.deepcopy(actual);bad['raw_from_ELF']['sha256']='0'*64;reject('wrong-raw-hash',lambda:p.raw_identity(bad,historical/'off/program.bin'))
 # Exact actual dependency reader: pin normal source, reject new external input.
 dr=root/'deps';source=dr/'off/source';out=dr/'off/out';(source/'port/dreamcast/game').mkdir(parents=True);out.mkdir();sf=source/'input.h';sf.write_bytes(b'owned source');external=root/'external.h';external.write_bytes(b'outside')
 df=out/'test.d';mini=dict(root=str(dr),source_manifest={'input.h':c.identity(sf)},input_pins={str(external.resolve()):c.identity(external)})
 df.write_text('x.o: '+str(sf)+' '+str(external)+'\n');passed('actual-source-external-dependencies',lambda:p.dependencies(mini,'off'))
 noexternal=copy.deepcopy(mini);noexternal['input_pins']={};reject('new-external-refused',lambda:p.dependencies(noexternal,'off'))
 sf.write_bytes(b'mutated');reject('source-input-changed',lambda:p.dependencies(mini,'off'))
 # Exercise real process monitor with HOST Python only. No SDK/PATH bootstrap.
 env=dict(os.environ);childargv=[sys.executable,'-B','-c','pass'];sample=lambda _:dict(good)
 passed('host-child-success',lambda:c.run_owned(childargv,root,env,root/'success.log',root,budget,time.monotonic(),sample))
 reject('host-child-failure',lambda:c.run_owned([sys.executable,'-B','-c','raise SystemExit(7)'],root,env,root/'failure.log',root,budget,time.monotonic(),sample))
 reject('existing-log-no-overwrite',lambda:c.run_owned(childargv,root,env,root/'success.log',root,budget,time.monotonic(),sample));assert (root/'success.log').read_bytes()==b''
 launched=[];original=c.subprocess.Popen
 def capture(argv,*a,**kw):
  assert argv[0]==sys.executable,'No SDK child allowed in host controls';child=original(argv,*a,**kw);launched.append(child);return child
 c.subprocess.Popen=capture
 sibling=original([sys.executable,'-B','-c','import time;time.sleep(20)'],start_new_session=True)
 try:
  calls=[0]
  def cap_sample(_):
   calls[0]+=1;return dict(good,owned_bytes=budget['owned_bytes_cap']+1 if calls[0]>=2 else 0)
  reject('inflight-cap-cleanup',lambda:c.run_owned([sys.executable,'-B','-c','import time;time.sleep(20)'],root,env,root/'cap.log',root,budget,time.monotonic(),cap_sample))
  assert launched[-1].poll() is not None and sibling.poll() is None;checks.append('cleanup-only-owned-child-group')
  tiny=dict(budget,per_arm_seconds=.6);beg=time.monotonic()
  reject('inflight-deadline-cleanup',lambda:c.run_owned([sys.executable,'-B','-c','import time;time.sleep(20)'],root,env,root/'timeout.log',root,tiny,beg,sample))
  assert launched[-1].poll() is not None and time.monotonic()-beg<5;checks.append('half-second-poll-deadline-observed')
 finally:c.subprocess.Popen=original;c.terminate(sibling)
 # Wrapper absent-grant path is an actual host shell and must stop before SDK slot.
 env={k:v for k,v in os.environ.items() if not k.startswith('RAIN8CE_')};q=subprocess.run(['bash',str(c.HERE/'execute.sh')],env=env,text=True,capture_output=True)
 assert q.returncode!=0 and 'ROOT_GRANT_REQUIRED' in q.stderr;checks.append('wrapper-no-grant-no-SDK')
 c.check_inputs(plan);checks.append('all-frozen-source-and-input-pins')
 result=dict(status='HOST_CONTROLLER_CONTROLS_PASS',controls=checks,count=len(checks),root=str(root),SDK_commands=0,Make_queries=0,links=0,guest=0)
 print(json.dumps(result,indent=2))
if __name__=='__main__':main()
