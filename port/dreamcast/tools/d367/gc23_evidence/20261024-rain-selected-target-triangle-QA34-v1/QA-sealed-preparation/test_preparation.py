"""Pure-host preparation controls. Never runs geniso/SDK/stage/guest."""
from pathlib import Path
import ast,copy,importlib.util,json,os,tempfile,types
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('future_master',HERE/'future_master.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def main():
 controls=[]
 def expect(name,fn,refusal=False):
  try:value=fn()
  except (ValueError,AssertionError) as e:
   if not refusal:raise
   controls.append(dict(name=name,refused=True,reason=str(e)));return
  if refusal:raise AssertionError('Unsafe acceptance '+name)
  controls.append(dict(name=name,passed=True));return value
 for p in HERE.glob('*.py'):ast.parse(p.read_text());controls.append(dict(name='syntax-'+p.name,passed=True))
 original=m.read(HERE/'CURRENT-CANDIDATE-MANIFEST.json');off=m.read(HERE/'OFF-EXPECTED-MANIFEST.json');on=m.read(HERE/'ON-EXPECTED-MANIFEST.json');plan=m.read(HERE/'MEDIA-PLAN.json');allowed=set(plan['allowed_differences'])
 expect('exact-OFF18',lambda:m.exact_manifest(original,off,allowed,off));expect('exact-ON18',lambda:m.exact_manifest(original,on,allowed,on))
 for name,edit in [('changed-texture',lambda x:x['dc/tex.pak'].update(sha256='0'*64)),('extra-overlay',lambda x:x.update({'dc/unrelated.ovl':dict(size=1,sha256='0'*64)})),('missing-overlay',lambda x:x.pop('dc/em22.ovl')),('wrong-arm-overlay',lambda x:x.update({'dc/em22.ovl':on['dc/em22.ovl']})),('fixture-content',lambda x:x['dc/warp.txt'].update(sha256='0'*64)),('unapproved-dedup-alternate',lambda x:x.update({'dc/native/r10d/alternate.bin':dict(size=1,sha256='0'*64)}))]:
  changed=copy.deepcopy(off);edit(changed);expect(name,lambda:m.exact_manifest(original,changed,allowed,off),True)
 with tempfile.TemporaryDirectory(prefix='gc-qa-media-controls-',dir='/dev/shm') as tmp:
  root=Path(tmp);expect('fresh-child',lambda:m.absolute_fresh(root/'fresh',root));(root/'old').mkdir();expect('existing-output-refused',lambda:m.absolute_fresh(root/'old',root),True);expect('parent-escape-refused',lambda:m.absolute_fresh(root/'..'/'escape',root),True);expect('relative-output-refused',lambda:m.absolute_fresh('relative',root),True);(root/'alias').symlink_to(root/'old');expect('symlink-refused',lambda:m.absolute_fresh(root/'alias'/'fresh',root),True)
  expect('owned-directory-symlink-refused',lambda:m.owned_bytes([root]),True)
  # Use a separate non-symlink root for the hardlink counting control.
  root=root/'count';root.mkdir()
  a=root/'a';a.write_bytes(b'preserved');os.link(a,root/'b');assert m.owned_bytes([root])==len(b'preserved');controls.append(dict(name='hardlink-bytes-counted-once',passed=True))
 original_check=m.subprocess.check_output;original_usage=m.shutil.disk_usage
 try:
  for win,wsl,refuse in [(28,27,False),(23,28,True),(28,23,True)]:
   m.subprocess.check_output=lambda *a,**kw:str(win*1024**3);m.shutil.disk_usage=lambda *a:types.SimpleNamespace(free=wsl*1024**3)
   expect('lower-floor-'+str(win)+'-'+str(wsl),lambda:m.floor(24*1024**3),refuse)
 finally:m.subprocess.check_output=original_check;m.shutil.disk_usage=original_usage
 for key in ['../outside','/absolute','dc/../../outside','dc//ambiguous','./noncanonical']:
  expect('source-key-refused-'+key,lambda:m.safe_key(key),True)
 text=(HERE/'future_master.py').read_text();assert "run(['genisoimage'" not in text and "run(['python3'" not in text and "run(['/usr/bin/genisoimage'" in text;controls.append(dict(name='absolute-pinned-host-tool-execution',passed=True))
 old_path=os.environ.get('PATH')
 try:
  os.environ['PATH']='/untrusted/synthetic'
  expect('synthetic-PATH-relative-tool-refused',lambda:m.host_argv(['genisoimage']),True)
  expect('synthetic-PATH-foreign-absolute-tool-refused',lambda:m.host_argv(['/untrusted/synthetic/genisoimage']),True)
  expect('synthetic-PATH-pinned-tool-retained',lambda:m.host_argv(['/usr/bin/genisoimage']))
 finally:
  if old_path is None:os.environ.pop('PATH',None)
  else:os.environ['PATH']=old_path
 old=os.environ.pop('GC_QA_MEDIA_ALLOCATED',None)
 try:expect('root-grant-absent-no-stage',lambda:m.main('off'),True)
 finally:
  if old is not None:os.environ['GC_QA_MEDIA_ALLOCATED']=old
 assert not Path(plan['base_paths']['off']).exists() and not Path(plan['base_paths']['on']).exists() and not Path(plan['work_paths']['off']).exists()
 result=dict(status='PREPARATION_CONTROLS_PASS_NO_STAGE',controls=controls,stage_run=False,SDK_run=False,genisoimage_run=False,guest_run=False)
 with (HERE/'PREPARATION-CONTROLS-r4.json').open('x') as f:json.dump(result,f,indent=1);f.write('\n')
 print(json.dumps(dict(status=result['status'],controls=len(controls))))
if __name__=='__main__':main()
