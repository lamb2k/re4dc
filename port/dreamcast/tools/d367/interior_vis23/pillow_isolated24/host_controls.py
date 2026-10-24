from pathlib import Path
import hashlib,json,os,py_compile,shutil,subprocess,sys,tempfile
R=Path(__file__).resolve().parent
PY=Path(sys.executable)
m=json.loads((R/'PILLOW-PINS.json').read_bytes())
launcher=R/'pillow_launcher.py'
OUT=R/'HOST-CONTROLS.json'
assert not OUT.exists()
rows=[]
def run(name,args,expect=0,env=None):
 p=subprocess.run([str(PY),'-I','-S','-B','-X','pycache_prefix='+str(R/('absent-'+name+'-cache')),str(launcher),*args],capture_output=True,text=True,env=env,timeout=45)
 rows.append({'name':name,'argv':p.args,'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
 assert (p.returncode==expect if expect==0 else p.returncode!=0),name
 return p
run('rgb-png',['--self-test'])
env=dict(os.environ,PYTHONPATH=str(R/'untrusted-site'),PYTHONHOME=str(R/'absent-home'))
(R/'untrusted-site').mkdir();(R/'untrusted-site'/'PIL.py').write_text("raise RuntimeError('untrusted site executed')")
run('isolated-env',['--self-test'],env=env)
cap=R/'owned-help-path';assert not cap.exists()
env=dict(os.environ,RE4DC_EMU='console')
a=['--',m['inputs']['bound']['path'],m['inputs']['harness']['path'],'--cap',str(cap),'--syms','0 0 0','--seconds','45','--period','25','--help']
run('actual-wrapper-help',a,env=env)
bound=json.loads((cap/'bounded-launch.json').read_text());assert 'pid' not in bound and bound['harness_sha256']==m['inputs']['harness']['sha256'] and bound['deadline_seconds']==55
rows.append({'name':'actual-unchanged-bound-no-guest','state':bound,'pass':True})
# Import actual unchanged capture template without invoking capture (no RAM/process access).
scope={'__name__':'capture_dependency_control','__file__':m['inputs']['capture_template']['path']}
exec(compile(Path(m['inputs']['capture_template']['path']).read_bytes(),scope['__file__'],'exec'),scope)
assert callable(scope['capture']);rows.append({'name':'capture-template-compiles-no-call','pass':True})
# Test source-only loaders against real matching-source hash pyc headers in owned copies.
T=Path(tempfile.mkdtemp(prefix='pillow-only-host-'))
try:
 pkg=T/'PIL';shutil.copytree(m['package_root'],pkg,ignore=shutil.ignore_patterns('__pycache__'))
 dm=json.loads(json.dumps(m));dm['package_root']=str(pkg)
 def clone(tag):
  d=T/tag;d.mkdir();raw=(json.dumps(dm,indent=2)+'\n').encode();(d/'PILLOW-PINS.json').write_bytes(raw)
  txt=launcher.read_text().replace("PINS_SHA256='"+hashlib.sha256((R/'PILLOW-PINS.json').read_bytes()).hexdigest()+"'","PINS_SHA256='"+hashlib.sha256(raw).hexdigest()+"'")
  (d/'pillow_launcher.py').write_text(txt);return d
 def sub(d,tag,ok=True):
  p=subprocess.run([str(PY),'-I','-S','-B','-X','pycache_prefix='+str(T/('absent-'+tag)),str(d/'pillow_launcher.py'),'--self-test'],capture_output=True,text=True,timeout=45)
  rows.append({'name':tag,'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr});assert (p.returncode==0)==ok,tag
  return p
 marker=T/'POISON-EXECUTED'
 poison=T/'poison.py';poison.write_text('from pathlib import Path\nPath('+repr(str(marker))+').write_text("bad")\nraise RuntimeError("stale cache executed")\n')
 import importlib.util,struct
 import importlib._bootstrap_external as be
 for name in ['__init__.py','Image.py','PngImagePlugin.py','_version.py']:
  target=pkg/name;cache=Path(importlib.util.cache_from_source(str(target)));cache.parent.mkdir(exist_ok=True)
  code=compile(poison.read_bytes(),str(target),'exec')
  cache.write_bytes(be._code_to_hash_pyc(code,importlib.util.source_hash(target.read_bytes()),checked=False))
 caches={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in pkg.rglob('*.pyc')}
 d=clone('cache-copy');sub(d,'adjacent-valid-hash-cache-ignored');assert not marker.exists()
 assert caches=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in pkg.rglob('*.pyc')}
 rows.append({'name':'cache-bytes-preserved-no-sentinel','caches':caches,'pass':True})
 for name in ['__init__.py','Image.py','_imaging.cp312-win_amd64.pyd']:
  f=pkg/name;old=f.read_bytes();f.write_bytes(old+b'!')
  q=sub(d,'mutated-'+name,False);assert 'pinned bytes changed' in q.stderr;f.write_bytes(old)
 extra=pkg/'Unpinned.py';extra.write_text('pass');q=sub(d,'extra-module',False);assert 'membership changed' in q.stderr;extra.unlink()
 # Freshprefix check fails before imports even if otherwise valid.
 existing=T/'exists';existing.mkdir()
 p=subprocess.run([str(PY),'-I','-S','-B','-X','pycache_prefix='+str(existing),str(launcher),'--self-test'],capture_output=True,text=True,timeout=45)
 assert p.returncode!=0 and 'absent fresh' in p.stderr;rows.append({'name':'existing-cache-prefix-refused','stderr':p.stderr,'pass':True})
 # Preserve all test files, including poison/cache, owned small host evidence.
 (R/'OWNED-HOST-SCRATCH.json').write_text(json.dumps({'path':str(T),'bytes':sum(p.stat().st_size for p in T.rglob('*') if p.is_file()),'disposable':False,'reason':'preserved source/cache mutants; no guest or captured image'},indent=2)+'\n')
except BaseException:
 (R/'FAILED-HOST-CONTROLS.json').write_text(json.dumps(rows,indent=2)+'\n');raise
OUT.write_text(json.dumps({'status':'HOST_ONLY_PASS_NO_GUEST_NO_CAPTURED_IMAGES','checks':rows,'count':len(rows)},indent=2)+'\n')
print('PASS',len(rows),OUT)
