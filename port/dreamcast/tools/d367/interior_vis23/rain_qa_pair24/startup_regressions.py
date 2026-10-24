"""Actual canonical-wrapper startup negatives plus transparent parent host suite."""
from pathlib import Path
import copy,hashlib,json,os,resource,signal,subprocess,sys,tempfile,types
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import common as c
import controller
resource.setrlimit(resource.RLIMIT_AS,(268435456,268435456));resource.setrlimit(resource.RLIMIT_CORE,(0,0));signal.alarm(120)
def main():
 out=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else HERE/'HOST-RUN-V2';out.mkdir(exist_ok=False)
 parent=HERE.parent/'qa-pair-prep-v1';seal=json.loads((parent/'KIT-SEAL.json').read_text());c.require(c.sha(parent/'KIT-SEAL.json')=='42bd0d1c3ebfb46193ad78e7b62defdd8d74f7fd7bc870f6d4e39eb339d840a5','Parent seal')
 c.verify({str(parent/k):v for k,v in seal['files'].items()})
 c.HOST_ROOT.mkdir(exist_ok=True);root=Path(tempfile.mkdtemp(prefix='startup-v2-',dir=c.HOST_ROOT));poison=root/'poison';poison.mkdir();checks=[];markers=[]
 for name in ['argparse','common','sitecustomize','usercustomize']:
  marker=root/(name+'.sentinel');markers.append(marker);(poison/(name+'.py')).write_text('from pathlib import Path\nPath('+repr(str(marker))+').write_text("INJECTED")\nraise RuntimeError("INJECTED")\n')
 bash_marker=root/'bash.sentinel';markers.append(bash_marker);hook=root/'bash-hook.sh';hook.write_text('printf INJECTED > '+str(bash_marker)+'\n')
 startup_marker=root/'startup.sentinel';markers.append(startup_marker);startup=root/'python-startup.py';startup.write_text('from pathlib import Path\nPath('+repr(str(startup_marker))+').write_text("INJECTED")\n')
 base={k:v for k,v in os.environ.items() if not (k.startswith('PYTHON') or k.startswith('RAIN8CE_QA_') or k in ['BASH_ENV','ENV','LD_PRELOAD','LD_LIBRARY_PATH'])};base.update(RAIN8CE_QA_ROOT_GRANT='/nonexistent',RAIN8CE_QA_GRANT_SHA256='0'*64,RAIN8CE_QA_ALLOCATED='0'*64)
 canonical=['/bin/bash','-p',str(HERE/'execute.sh')]
 def run(name,argv,extra,expect,ok=False):
  env=dict(base,**extra);q=subprocess.run(argv,cwd=poison,env=env,text=True,capture_output=True,timeout=5)
  assert (q.returncode==0 if ok else q.returncode!=0) and expect in q.stderr+q.stdout,(name,q.returncode,q.stdout,q.stderr)
  assert not any(p.exists() for p in markers),name+' startup sentinel executed'
  log=root/(name+'.log');log.write_text(q.stdout+q.stderr);checks.append(dict(name=name,returncode=q.returncode,log=str(log),log_identity=c.identity(log),sentinels_absent=True))
 for name,value in [('PYTHONPATH',str(poison)),('PYTHONHOME',str(poison)),('PYTHONSTARTUP',str(startup)),('PYTHONUSERBASE',str(poison)),('PYTHONINSPECT','1'),('PYTHONBREAKPOINT','argparse.poison'),('PYTHONPYCACHEPREFIX',str(root/'untrusted-cache')),('PYTHONDONTWRITEBYTECODE','0'),('BASH_ENV',str(hook)),('ENV',str(hook))]:
  run('canonical-refuses-'+name,canonical,{name:value},'Startup injection refused: '+name)
 run('canonical-ignores-poison-CWD',canonical,{},'Root QA allocation required')
 run('isolated-controller-ignores-python-env',['/usr/bin/python3','-I','-S','-B',str(HERE/'controller.py'),'--execute'],dict(PYTHONPATH=str(poison),PYTHONHOME=str(poison),PYTHONSTARTUP=str(startup),PYTHONINSPECT='1'),'Root QA allocation required')
 run('nonisolated-controller-refuses',['/usr/bin/python3','-B',str(HERE/'controller.py'),'--execute'],{},'Controller requires isolated -I -S -B startup')
 command=controller.postbuild_command('off',root/'never-written.json');run('isolated-postbuild-bootstrap-help',command[:7]+['--help'],dict(PYTHONPATH=str(poison),PYTHONHOME=str(poison),PYTHONSTARTUP=str(startup),PYTHONINSPECT='1'),'--arm',ok=True)
 assert not (root/'never-written.json').exists() and not list(root.rglob('*.pyc'))
 # Parent's actual73-method suite is retained unchanged. Only canonical shell
 # invocation and the exclusive result name are adapted in RAM, not on disk.
 source=(HERE/'test_host.py').read_text();old="['/bin/bash',str(c.HERE/'execute.sh')]";assert source.count(old)==2
 source=source.replace(old,"['/bin/bash','-p',str(c.HERE/'execute.sh')]")
 assert source.count("c.HERE/'HOST-CONTROLS-SEALED.json'")==1;source=source.replace("c.HERE/'HOST-CONTROLS-SEALED.json'","Path("+repr(str(out))+")/'HOST-CONTROLS-V2-ADAPTED.json'")
 module=types.ModuleType('v2_parent_controls');module.__file__=str(HERE/'test_host.py');exec(compile(source,module.__file__,'exec'),module.__dict__);module.main()
 baseline=json.loads((out/'HOST-CONTROLS-V2-ADAPTED.json').read_text());assert baseline['count']==73 and baseline['status']=='HOST_ONLY_PASS'
 c.verify({str(parent/k):v for k,v in seal['files'].items()});c.check_inputs(c.load());[c.fresh_arm(c.ROOT/a) for a in ['off','on']]
 result=dict(status='STARTUP_SUCCESSOR_HOST_PASS',startup_checks=len(checks),parent_host_checks=73,total=73+len(checks),checks=checks,root=str(root),parent_seal_unchanged=True,adaptation=dict(canonical_shell='Two /bin/bash argv become /bin/bash -p',receipt='Fresh exclusive V2 result path',source_on_disk_unchanged=True),SDK_commands=0,Make_queries=0,bootstrap=0,stage=0,guest=0,scope='Actual host interpreter/wrapper startup, host orchestration and static retained evidence only; no SDK or runtime acceptance')
 c.exclusive_json(out/'STARTUP-CONTROLS.json',result);print(json.dumps({k:v for k,v in result.items() if k!='checks'}))
if __name__=='__main__':main()
