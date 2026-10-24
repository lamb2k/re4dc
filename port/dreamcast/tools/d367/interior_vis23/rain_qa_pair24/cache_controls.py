"""Actual wrapper/postbuild hostile adjacent-cache probes; no SDK tools."""
from pathlib import Path
import ast,hashlib,importlib.util,json,os,py_compile,resource,shutil,signal,subprocess,sys,tempfile
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import common as c
import controller
resource.setrlimit(resource.RLIMIT_AS,(268435456,268435456));resource.setrlimit(resource.RLIMIT_CORE,(0,0));signal.alarm(120)
def main():
 out=Path(sys.argv[1]).resolve();out.mkdir(exist_ok=True);parent=HERE.parent/'qa-pair-prep-v2';ps=json.loads((parent/'KIT-SEAL.json').read_text());c.verify({str(parent/k):v for k,v in ps['files'].items()})
 root=Path(tempfile.mkdtemp(prefix='cache-v3-',dir=c.HOST_ROOT));checks=[]
 base={k:v for k,v in os.environ.items() if not (k.startswith('PYTHON') or k.startswith('RAIN8CE_QA_') or k in ['BASH_ENV','ENV','LD_PRELOAD','LD_LIBRARY_PATH'])};base.update(RAIN8CE_QA_ROOT_GRANT='/nonexistent',RAIN8CE_QA_GRANT_SHA256='0'*64,RAIN8CE_QA_ALLOCATED='0'*64)
 def case(name,source,poison,route,expect,positive=False,mutate=None):
  work=root/name;work.mkdir();names=['execute.sh','controller.py','common.py','postbuild.py','elf_reader.py','CONTRACT.json']
  for n in names:shutil.copyfile(source/n,work/n)
  assert all((work/n).read_bytes()==(source/n).read_bytes() for n in names)
  markers=[];cache={}
  for helper in poison:
   marker=work/(helper+'.sentinel');markers.append(marker);payload=work/('payload-'+helper);payload.write_text('from pathlib import Path\nPath('+repr(str(marker))+').write_text("CACHE_POISON")\nraise RuntimeError("CACHE_POISON_EXECUTED")\n')
   path=Path(importlib.util.cache_from_source(str(work/helper)));py_compile.compile(str(payload),cfile=str(path),dfile=str(work/helper),doraise=True,invalidation_mode=py_compile.PycInvalidationMode.UNCHECKED_HASH);cache[str(path)]=c.identity(path)
  if mutate:
   marker=work/'source.sentinel';markers.append(marker);f=work/mutate;f.write_bytes(f.read_bytes()+('\nfrom pathlib import Path\nPath('+repr(str(marker))+').write_text("SOURCE_POISON")\n').encode())
  if route=='wrapper':argv=['/bin/bash','-p',str(work/'execute.sh')]
  elif route=='controller':argv=['/usr/bin/python3','-I','-S','-B',str(work/'controller.py'),'--execute']
  else:
   if source==parent:
    tree=ast.parse((parent/'controller.py').read_text());bootstrap=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='POST_BOOTSTRAP' for t in n.targets))
   else:bootstrap=controller.POST_BOOTSTRAP
   argv=['/usr/bin/python3','-I','-S','-B','-c',bootstrap,str(work/'postbuild.py'),'--help']
  q=subprocess.run(argv,cwd=work,env=base,text=True,capture_output=True,timeout=5);log=work/'result.log';log.write_text(q.stdout+q.stderr)
  assert expect in q.stdout+q.stderr,(name,q.returncode,q.stdout,q.stderr)
  assert (any(m.exists() for m in markers) if positive else not any(m.exists() for m in markers)),name+' unexpected sentinel state'
  c.verify(cache)
  if not mutate:assert all((work/n).read_bytes()==(source/n).read_bytes() for n in names)
  checks.append(dict(name=name,route=route,source=str(source),positive_old_loader=positive,mutated_source=mutate,returncode=q.returncode,marker_observations={str(m):m.exists() for m in markers},cache_preserved=cache,log=dict(path=str(log),identity=c.identity(log))))
 case('old-controller-fixture-demonstrates-cache',parent,['common.py'],'controller','CACHE_POISON_EXECUTED',positive=True)
 case('old-post-ELF-fixture-demonstrates-cache',parent,['elf_reader.py'],'post','CACHE_POISON_EXECUTED',positive=True)
 case('wrapper-ignores-common-pyc',HERE,['common.py'],'wrapper','Root QA allocation required')
 case('post-ignores-common-pyc',HERE,['common.py'],'post','--arm')
 case('post-ignores-ELF-pyc',HERE,['elf_reader.py'],'post','--arm')
 case('post-ignores-main-pyc',HERE,['postbuild.py'],'post','--arm')
 case('post-ignores-all-pyc',HERE,['common.py','postbuild.py','elf_reader.py'],'post','--arm')
 case('wrapper-rejects-common-source',HERE,['common.py'],'wrapper','Common helper source changed',mutate='common.py')
 case('post-rejects-common-source',HERE,['common.py'],'post','Authenticated helper source changed',mutate='common.py')
 case('post-rejects-main-source',HERE,['postbuild.py'],'post','Authenticated helper source changed',mutate='postbuild.py')
 case('post-rejects-ELF-source',HERE,['elf_reader.py'],'post','ELF helper source changed',mutate='elf_reader.py')
 c.verify({str(parent/k):v for k,v in ps['files'].items()});result=dict(status='CACHE_SOURCE_ONLY_HOST_PASS',count=len(checks),checks=checks,root=str(root),parent_seal_unchanged=True,SDK_commands=0,Make_queries=0,SDK_bootstrap=0,stage=0,guest=0,scope='Host Python helper cache/source admission only; no Dreamcast cache or execution acceptance')
 c.exclusive_json(out/'CACHE-CONTROLS.json',result);print(json.dumps({k:v for k,v in result.items() if k!='checks'}))
if __name__=='__main__':main()
