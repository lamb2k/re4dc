"""One fresh ON arm with authenticated completed OFF reuse. No automatic retry."""
import sys
if __name__=='__main__' and not(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode):raise SystemExit('Requires isolated -I -S -B startup')
from pathlib import Path
import argparse,copy,hashlib,json,os,resource,signal,time,types
HERE=Path(__file__).resolve().parent
PARENT=HERE.parent/'qa-pair-prep-v3'
PARENT_SEAL='dbe8377e75f6d631195883e08e2575e44dbf00969af76800294226207f5765d1'
OLD_RECEIPT='e0356a185a2dafe1368b66c5b6dedfa7b2bbd664f24c8f342019a081ca5dcf55'
OLD_POST='e21a8e47184b30a0dcbed1380e6a17c64c6fec3119b663e4254af5882289b3b4'
PINS={'common.py':'2d01c267f6ea24b68abe201680bfe29660ad6d3a25f58918ba7bf407ee9b0b87','controller.py':'c1c61ee4151e1320592462dc5e950a4af2e4bc7f4e1d542c5ee710fe97715873','postbuild.py':'fcb3df088f732e2454f42501c20e2ad833e38aeb623ee3eb2808beab5cc458b2','prepare.py':'21df87e3744ddaf7284b86657fc0e00636e126a5caa702e3466ce1b723fca15e'}
def digest(raw):return hashlib.sha256(raw).hexdigest()
def source_module(name,path,expected):
 raw=path.read_bytes()
 if digest(raw)!=expected:raise RuntimeError('Authenticated helper source changed '+str(path))
 module=types.ModuleType(name);module.__file__=str(path);sys.modules[name]=module;exec(compile(raw,str(path),'exec',dont_inherit=True),module.__dict__);return module

def context():
 raw=(PARENT/'KIT-SEAL.json').read_bytes()
 if digest(raw)!=PARENT_SEAL:raise RuntimeError('Reviewed V3 seal changed')
 seal=json.loads(raw)
 for name,row in seal['files'].items():
  path=PARENT/name
  if path.stat().st_size!=row['bytes'] or digest(path.read_bytes())!=row['sha256']:raise RuntimeError('Reviewed V3 member changed '+name)
 c=source_module('common',PARENT/'common.py',PINS['common.py']);ctl=source_module('reviewed_parent_controller',PARENT/'controller.py',PINS['controller.py']);post=source_module('continued_postbuild',PARENT/'postbuild.py',PINS['postbuild.py'])
 return c,ctl,post

def manifest(root,c):
 c.require(root.is_dir() and not root.is_symlink(),'Real owned tree required');result={}
 for p in sorted(root.rglob('*')):
  c.require(not p.is_symlink(),'Owned symlink refused '+str(p))
  if p.is_file():result[str(p.relative_to(root))]=c.identity(p)
 return result

def authenticate_off(c,ctl,post):
 plan=c.load();c.check_inputs(plan);receipt=c.ROOT/'qa-pair-result-v1/receipt.json';c.require(c.sha(receipt)==OLD_RECEIPT,'Exact preserved failed pair receipt')
 old=json.loads(receipt.read_text());c.require(old['complete'] is False and old['source']==c.SOURCE and old['arms']['off']['complete'] is True and old['arms']['on']['complete'] is False and old['failure']=="RuntimeError('Release priority hold')",'Only completed OFF / interrupted ON is reusable')
 grant=Path(old['authorization']['grant']);c.require(c.sha(grant)==old['authorization']['sha256'],'Original root grant changed');contract=json.loads((PARENT/'CONTRACT.json').read_text());ctl.check_grant(json.loads(grant.read_text()),contract,c.sha(PARENT/'CONTRACT.json'),PARENT_SEAL)
 actual_path=c.ROOT/'qa-pair-result-v1/off/postbuild.json';c.require(c.sha(actual_path)==OLD_POST==old['arms']['off']['postbuild_sha256'],'Completed OFF static readback pin')
 actual=json.loads(actual_path.read_text());fresh=json.loads(json.dumps(post.read_arm(plan,'off')));c.require(actual==fresh,'Whole completed OFF static artefacts changed')
 for key in ('files','addresses','sizes'):
  value=fresh['ELF'][key] if key!='files' else fresh['files']
  c.require(value==old['arms']['off'][key],'Completed OFF receipt identity changed '+key)
 return plan,old,fresh

def load_contract(c):
 contract=json.loads((HERE/'CONTRACT.json').read_text());c.require(contract['source']==c.SOURCE and contract['parent_seal_sha256']==PARENT_SEAL and contract['old_receipt_sha256']==OLD_RECEIPT,'Continuation source/parent/receipt')
 c.require(contract['budget']==c.load()['budget'] and contract['canonical_lock']=='/tmp/d367-build-7d1f56a1729c.lock' and contract['shared_slots']==['/root/probe/d367-build.lock','/root/probe/d367-build2.lock'],'Unchanged budget/lease/slots required')
 root=Path(contract['root']);c.require(root.parent==Path('/dev/shm') and root.name.startswith('rain8ce-qa-on-cont-v1-') and root!=c.ROOT and not root.is_relative_to(c.ROOT) and not c.ROOT.is_relative_to(root),'Fresh disjoint continuation root')
 return contract,root

def check_inputs(contract,root,c):
 c.check_inputs(c.load());c.require(manifest(c.ROOT,c)==contract['old_root_manifest'],'Old completed/partial trees changed; never resume them')
 c.verify({str(root/'on/source'/name):row for name,row in c.load()['source_manifest'].items()})
 c.require(c.sha(Path(contract['off_postbuild_path']))==OLD_POST,'Original OFF readback changed')

def new_plan(root,c):
 plan=copy.deepcopy(c.load());old=Path(plan['root']);plan['root']=str(root);plan['commands']['on']=[x.replace(str(old/'on'),str(root/'on')) for x in plan['commands']['on']]
 plan['environment']['on']={k:v.replace(str(old/'on'),str(root/'on')) for k,v in plan['environment']['on'].items()};return plan

def resources(root,c):
 value=c.resources(c.ROOT);value['old_root_bytes']=c.used(c.ROOT);value['new_root_bytes']=c.used(root);value['continuation_kit_bytes']=c.used(HERE);value['owned_bytes']+=value['new_root_bytes']+value['continuation_kit_bytes'];return value

def check_grant(grant,contract,contract_sha,seal_sha):
 wanted=dict(approved=True,authorization='SDK_QA_RAIN_CONTINUE_ON',source=contract['source'],root=contract['root'],contract_sha256=contract_sha,kit_seal_sha256=seal_sha,budget=contract['budget'],old_receipt_sha256=OLD_RECEIPT,parent_seal_sha256=PARENT_SEAL)
 if not isinstance(grant.get('grant_id'),str) or grant['grant_id'] in ('','ROOT_MUST_ASSIGN_UNIQUE_ID') or any(grant.get(k)!=v for k,v in wanted.items()):raise RuntimeError('Wrong continuation root grant')

def authorize(contract,c):
 sha=c.sha(HERE/'CONTRACT.json');c.require(os.environ.get('RAIN8CE_QA_ALLOCATED')==sha,'Root continuation allocation required');path=Path(os.environ.get('RAIN8CE_QA_ROOT_GRANT','/nonexistent'));c.require(path.is_file() and c.sha(path)==os.environ.get('RAIN8CE_QA_GRANT_SHA256'),'Pinned continuation root grant required')
 check_grant(json.loads(path.read_text()),contract,sha,c.sha(HERE/'KIT-SEAL.json'));c.require(not any(os.environ.get(k) for k in c.REFUSED_ENV),'Inherited injection refused')
 seal=json.loads((HERE/'KIT-SEAL.json').read_text());c.verify({str(HERE/name):row for name,row in seal['files'].items()});return dict(path=str(path),identity=c.identity(path),contract_sha256=sha,controller_sha256=seal['files']['controller.py']['sha256'])

READ_BOOTSTRAP="""import hashlib,pathlib,sys,types
path=pathlib.Path(sys.argv.pop(1)).resolve();expected=sys.argv.pop(1);raw=path.read_bytes()
if hashlib.sha256(raw).hexdigest()!=expected:raise SystemExit('Continuation source changed')
module=types.ModuleType('__main__');module.__file__=str(path);sys.modules['__main__']=module;sys.argv[0]=str(path)
exec(compile(raw,str(path),'exec',dont_inherit=True),module.__dict__)
"""

def main():
 ap=argparse.ArgumentParser();mode=ap.add_mutually_exclusive_group(required=True);mode.add_argument('--execute',action='store_true');mode.add_argument('--read-on',action='store_true');ap.add_argument('--output',type=Path);ap.add_argument('--contract-sha256');a=ap.parse_args();c,ctl,post=context();contract,root=load_contract(c)
 if a.read_on:
  resource.setrlimit(resource.RLIMIT_AS,(268435456,268435456));signal.alarm(120);c.require(a.contract_sha256 is not None and c.sha(HERE/'CONTRACT.json')==a.contract_sha256,'Pinned reader contract required');c.require(a.output is not None,'Fresh static output required');c.contained(root,a.output);check_inputs(contract,root,c);result=post.read_arm(new_plan(root,c),'on');c.exclusive_json(a.output,result);return
 auth=authorize(contract,c);locks,slot=ctl.acquire(contract)
 try:
  def stop(sig,frame):raise InterruptedError('Continuation signal '+str(sig))
  for sig in (signal.SIGTERM,signal.SIGHUP,signal.SIGINT):signal.signal(sig,stop)
  started=time.monotonic();budget=contract['budget'];result=c.contained(root,root/'continuation-result-v1');result.mkdir(exist_ok=False);report=dict(complete=False,source=c.SOURCE,authorization=auth,canonical_lease=contract['canonical_lock'],slot=slot,reused_OFF=dict(original_receipt_sha256=OLD_RECEIPT,postbuild_sha256=OLD_POST,complete=False),fresh_ON=dict(complete=False),scope='Reused fully authenticated OFF plus one entirely fresh ON; static programme identity only')
  journal=(result/'journal.jsonl').open('x')
  def event(value):journal.write(json.dumps(value)+'\n');journal.flush()
  def sample(_):
   value=resources(root,c);event(dict(monotonic=time.monotonic(),resources=value));return value
  try:
   check_inputs(contract,root,c);_,old,off=authenticate_off(c,ctl,post);c.boundaries(sample(root),budget,time.monotonic()-started,admission=True);report['reused_OFF'].update(complete=True,files=off['files'],addresses=off['ELF']['addresses'],sizes=off['ELF']['sizes'],original_seconds=old['arms']['off']['seconds'])
   arm=root/'on';c.fresh_arm(arm);c.require(manifest(arm/'source',c)==c.load()['source_manifest'],'Fresh ON export has extra/changed source files');plan=new_plan(root,c);tmp=result/'tmp';tmp.mkdir();env=c.clean_environment(plan,'on',tmp);command=plan['commands']['on'];c.exclusive_json(arm/'command.json',command);event(dict(status='ON_STARTED',argv=command))
   c.run_owned(command,arm/'source',env,arm/'build.log',root,budget,started,sample)
   elf=arm/'out/re4dc-game.elf';tools=ctl.TOOLS;commands=[([str(tools/'sh-elf-objcopy'),'-R','.stack','-O','binary',str(elf),str(arm/'program.bin')],result/'objcopy.log'),([str(tools/'sh-elf-nm'),'-S',str(elf)],arm/'symbols.txt'),([str(tools/'sh-elf-size'),str(elf)],arm/'size.txt'),([str(tools/'sh-elf-size'),'-A',str(elf)],arm/'sections.txt'),(['/usr/bin/python3','-I','-S','-B','-c',READ_BOOTSTRAP,str(HERE/'controller.py'),auth['controller_sha256'],'--read-on','--contract-sha256',auth['contract_sha256'],'--output',str(result/'postbuild.json')],result/'postbuild.log')]
   for argv,log in commands:event(dict(analysis_argv=argv));c.run_owned(argv,HERE,env,log,root,budget,started,sample)
   on=json.loads((result/'postbuild.json').read_text());c.require(on['complete'] is True,'Fresh ON incomplete');check_inputs(contract,root,c);c.boundaries(sample(root),budget,time.monotonic()-started);report['fresh_ON'].update(complete=True,files=on['files'],addresses=on['ELF']['addresses'],sizes=on['ELF']['sizes'],seconds=time.monotonic()-started);report['delta']={key:on['ELF']['sizes'][key]-off['ELF']['sizes'][key] for key in ('text','data','bss')};report['linked_end_delta']=on['ELF']['addresses']['_end']-off['ELF']['addresses']['_end'];report['complete']=True
  except BaseException as e:report['failure']=repr(e);raise
  finally:event(dict(status='FINAL',complete=report['complete']));journal.close();c.exclusive_json(result/'receipt.json',report)
 finally:
  for handle in reversed(locks):handle.close()
if __name__=='__main__':main()
