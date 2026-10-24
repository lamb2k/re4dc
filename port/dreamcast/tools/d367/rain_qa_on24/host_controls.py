"""Bounded source/host controls only; no SDK invocation or production lock."""
import sys
if __name__=='__main__' and not(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode):raise SystemExit('Use -I -S -B')
from pathlib import Path
import argparse,copy,hashlib,json,os,py_compile,resource,signal,subprocess,tempfile,types
from unittest.mock import patch
HERE=Path(__file__).resolve().parent

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--controller-sha256',required=True);ap.add_argument('--output',type=Path,default=HERE/'HOST-CONTROLS.json');a=ap.parse_args();resource.setrlimit(resource.RLIMIT_AS,(268435456,268435456));signal.alarm(120);raw=(HERE/'controller.py').read_bytes();assert hashlib.sha256(raw).hexdigest()==a.controller_sha256
 m=types.ModuleType('continued_host_control');m.__file__=str(HERE/'controller.py');sys.modules[m.__name__]=m;exec(compile(raw,m.__file__,'exec',dont_inherit=True),m.__dict__);c,ctl,post=m.context();contract,root=m.load_contract(c);checks=[]
 def passed(name,fn):fn();checks.append(dict(name=name,pass_=True))
 def reject(name,fn):
  try:fn()
  except RuntimeError as e:checks.append(dict(name=name,refused=True,reason=str(e)))
  else:raise AssertionError(name+' accepted')
 plan,old,off=m.authenticate_off(c,ctl,post);checks.append(dict(name='actual-whole-OFF-static-readback-equals-original',pass_=True,files=len(off['files']),compile=off['graph']['compile_commands_matched'],links=len(off['graph']['objects'])))
 passed('all-old-and-new-source-input-pins',lambda:m.check_inputs(contract,root,c));assert m.manifest(root/'on/source',c)==plan['source_manifest'];c.fresh_arm(root/'on');checks.append(dict(name='actual-fresh-ON7746-no-output',pass_=True))
 reject('actual-old-partial-ON-cannot-resume',lambda:c.fresh_arm(c.ROOT/'on'))
 actual_sha=c.sha
 with patch.object(c,'check_inputs',return_value=None),patch.object(c,'sha',side_effect=lambda p:'0'*64 if str(p).endswith('qa-pair-result-v1/receipt.json') else actual_sha(p)):
  reject('old-receipt-byte-drift',lambda:m.authenticate_off(c,ctl,post))
 with patch.object(c,'SOURCE','0'*40):reject('foreign-source-profile',lambda:m.load_contract(c))
 new=m.new_plan(root,c);assert new['commands']['off']==plan['commands']['off'];assert new['commands']['on']==[x.replace(str(c.ROOT/'on'),str(root/'on')) for x in plan['commands']['on']];assert new['reference']==plan['reference'];checks.append(dict(name='only-ON-owned-paths-change-no-OFF-build',pass_=True))
 good=dict(C_free=64*1024**3,RAM_free=64*1024**3,owned_bytes=100,release_active=False)
 with patch.object(c,'resources',return_value=dict(good)),patch.object(c,'used',side_effect=lambda p:{c.ROOT:70,root:20,HERE:10}[p]):
  value=m.resources(root,c);assert value['owned_bytes']==130 and value['old_root_bytes']==70 and value['new_root_bytes']==20;checks.append(dict(name='combined-budget-includes-old-partial-new-and-kit',pass_=True))
 reject('combined-two-GiB-exceeded',lambda:c.boundaries(dict(good,owned_bytes=2*1024**3+1),contract['budget']))
 reject('real-release-priority-not-suppressed',lambda:c.boundaries(dict(good,release_active=True),contract['budget']))
 grant=dict(approved=True,grant_id='HOST_ONLY_NO_ALLOCATION',authorization='SDK_QA_RAIN_CONTINUE_ON',source=c.SOURCE,root=str(root),contract_sha256='contract',kit_seal_sha256='seal',budget=contract['budget'],old_receipt_sha256=m.OLD_RECEIPT,parent_seal_sha256=m.PARENT_SEAL)
 passed('grant-data-positive-no-allocation',lambda:m.check_grant(grant,contract,'contract','seal'))
 for key,value in [('approved',False),('authorization','SDK_QA_RAIN_OFF_ON'),('source','0'*40),('root',str(c.ROOT)),('contract_sha256','wrong'),('old_receipt_sha256','wrong'),('parent_seal_sha256','wrong'),('kit_seal_sha256','wrong'),('budget',dict(contract['budget'],jobs=2))]:
  bad=dict(grant);bad[key]=value;reject('grant-'+key,lambda bad=bad:m.check_grant(bad,contract,'contract','seal'))
 with tempfile.TemporaryDirectory(prefix='rain-on-host-',dir='/dev/shm') as temp:
  work=Path(temp);source=work/'source.py';ok=work/'source-marker';poison=work/'cache-marker';source.write_text('open('+repr(str(ok))+",'w').write('SOURCE_ONLY')\n");fake=work/'fake.py';fake.write_text('open('+repr(str(poison))+",'w').write('CACHE_POISON')\n");cache=Path(__import__('importlib.util',fromlist=['cache_from_source']).cache_from_source(str(source)));py_compile.compile(str(fake),cfile=str(cache),doraise=True,invalidation_mode=py_compile.PycInvalidationMode.UNCHECKED_HASH);cache_sha=c.sha(cache)
  argv=['/usr/bin/python3','-I','-S','-B','-c',m.READ_BOOTSTRAP,str(source),c.sha(source)];q=subprocess.run(argv,capture_output=True,text=True,timeout=5);assert q.returncode==0 and ok.exists() and not poison.exists() and c.sha(cache)==cache_sha;checks.append(dict(name='pinned-reader-bootstrap-ignores-adjacent-cache',pass_=True))
  q=subprocess.run(argv[:7]+['0'*64],capture_output=True,text=True,timeout=5);assert q.returncode!=0 and 'Continuation source changed' in q.stderr;checks.append(dict(name='reader-bootstrap-refuses-source-drift',pass_=True))
 env={k:v for k,v in os.environ.items() if not(k.startswith('PYTHON') or k in ('BASH_ENV','ENV','LD_PRELOAD','LD_LIBRARY_PATH'))};env.update(RAIN8CE_QA_ROOT_GRANT='/nonexistent',RAIN8CE_QA_GRANT_SHA256='0'*64,RAIN8CE_QA_ALLOCATED='0'*64);before=(root/'continuation-result-v1').exists();q=subprocess.run(['/bin/bash','-p',str(HERE/'execute.sh')],env=env,capture_output=True,text=True,timeout=10);assert q.returncode!=0 and 'Root continuation allocation required' in q.stderr and (root/'continuation-result-v1').exists()==before;checks.append(dict(name='actual-wrapper-invalid-allocation-before-any-SDK-lock-child',pass_=True,stderr=q.stderr))
 # Mock only SDK/lease/auth actions; production flow still constructs one new ON
 # arm, all analysis commands and a truthful reused-OFF/fresh-ON receipt.
 for fail in (False,True):
  with tempfile.TemporaryDirectory(prefix='rain8ce-qa-on-cont-v1-host-',dir='/dev/shm') as temp:
   public=Path(temp);(public/'on/source').mkdir(parents=True);calls=[];localplan=copy.deepcopy(plan);localplan['source_manifest']={};localcontract=dict(contract,root=str(public));auth=dict(scope='HOST_ONLY_NOT_ALLOCATION',contract_sha256=c.sha(HERE/'CONTRACT.json'),controller_sha256=a.controller_sha256)
   fake_on=dict(complete=True,files={'HOST_ONLY':{}},ELF=dict(addresses=off['ELF']['addresses'],sizes=off['ELF']['sizes']))
   def run(argv,cwd,env,log,*args):
    calls.append(argv)
    if fail:raise RuntimeError('Release priority hold')
    if '--read-on'in argv:c.exclusive_json(Path(argv[argv.index('--output')+1]),fake_on)
   previous_argv=sys.argv[:];previous_signals={s:signal.getsignal(s) for s in (signal.SIGTERM,signal.SIGHUP,signal.SIGINT)}
   try:
    with patch.object(m,'context',return_value=(c,ctl,post)),patch.object(m,'load_contract',return_value=(localcontract,public)),patch.object(m,'authorize',return_value=auth),patch.object(ctl,'acquire',return_value=([],'HOST_ONLY_NO_SLOT')),patch.object(m,'check_inputs',return_value=None),patch.object(m,'authenticate_off',return_value=(plan,old,off)),patch.object(m,'resources',return_value=dict(good)),patch.object(c,'load',return_value=localplan),patch.object(c,'run_owned',side_effect=run):
     sys.argv=['controller.py','--execute']
     if fail:reject('host-mock-release-failure-is-preserved',m.main)
     else:m.main()
   finally:
    sys.argv=previous_argv
    for s,handler in previous_signals.items():signal.signal(s,handler)
   report=json.loads((public/'continuation-result-v1/receipt.json').read_text());assert report['reused_OFF']['complete'] and report['complete'] is(not fail);assert len(calls)==(1 if fail else 6);assert all(str(c.ROOT/'on/source') not in json.dumps(row) and str(c.ROOT/'off/source') not in json.dumps(row) for row in calls);assert str(public/'on/source') in json.dumps(calls[0]);checks.append(dict(name='mock-flow-'+('failure-no-retry' if fail else 'one-new-ON-no-OFF-rebuild'),pass_=True,intercepted_requests=len(calls),actual_SDK_commands=0))
 m.check_inputs(contract,root,c);c.fresh_arm(root/'on');result=dict(status='CONTINUATION_HOST_PASS',count=len(checks),checks=checks,controller_sha256=a.controller_sha256,root=str(root),OFF_static_rechecked=True,old_failure_preserved=True,new_ON_unbuilt=True,SDK_commands=0,Make_queries=0,bootstrap=0,stage=0,guests=0)
 c.exclusive_json(a.output,result);print(json.dumps({k:v for k,v in result.items() if k!='checks'}))
if __name__=='__main__':main()
