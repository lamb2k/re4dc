from pathlib import Path
import ast,copy,subprocess,resource,tempfile,shutil,time,json
R=Path('/mnt/c/Game Dev/Emulators/codex-lanes/gc-motion24/full-h2-prep-v2')
def limit():resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
results={}
for name in ['test_host.py','test_repairs.py']:
 start=time.monotonic()
 with (R/(name+'.log')).open('x') as out:p=subprocess.run(['/usr/bin/python3','-B','-E','-X','pycache_prefix=/dev/shm/h2v2-'+name,str(R/name)],stdout=out,stderr=subprocess.STDOUT,timeout=120,preexec_fn=limit)
 results[name]=dict(returncode=p.returncode,seconds=time.monotonic()-start);assert p.returncode==0
with tempfile.TemporaryDirectory(prefix='h2-v2-mutants-',dir='/dev/shm') as temp:
 for kind in ['late_timer_registration','implicit_return_UNKNOWN']:
  d=Path(temp)/kind;d.mkdir()
  for f in R.iterdir():
   if f.is_file():shutil.copyfile(f,d/f.name)
  if kind=='late_timer_registration':
   file=d/'windows_entry.py';tree=ast.parse(file.read_bytes());node=next(x for x in ast.walk(tree) if isinstance(x,ast.ClassDef) and x.name=='OwnedPopen');method=node.body[0];block=next(x for x in method.body if isinstance(x,ast.If) and any(isinstance(y,ast.Assign) and any(isinstance(z,ast.Name) and z.id=='guest' for z in y.targets) for y in x.body));ix=[i for i,x in enumerate(block.body) if isinstance(x,ast.Try)];assert len(ix)==2;block.body[ix[0]],block.body[ix[1]]=block.body[ix[1]],block.body[ix[0]]
  else:
   file=d/'run.py';tree=ast.parse(file.read_bytes());fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='retain_reservations');fn.body=[ast.Return(value=ast.Constant(value=False))]
  ast.fix_missing_locations(tree);raw=ast.unparse(tree)+'\n';compile(raw,str(file),'exec');file.write_text(raw)
  start=time.monotonic()
  with (R/('MUTANT-'+kind+'.log')).open('x') as out:p=subprocess.run(['/usr/bin/python3','-B','-E','-X','pycache_prefix='+str(d/'cache'),str(d/'test_repairs.py')],stdout=out,stderr=subprocess.STDOUT,timeout=120,preexec_fn=limit)
  assert p.returncode!=0,kind;results[kind]=dict(mutant_compiled=True,caught=True,returncode=p.returncode,seconds=time.monotonic()-start)
(R/'HOST-CONTROLS.json').write_text(json.dumps(dict(public=16,source_extracted_repairs=8,total=24,results=results,RAM_limit_bytes=256*1024**2,per_process_seconds_cap=120,SDK_stage_guest_native_query=False),indent=2)+'\n');print((R/'HOST-CONTROLS.json').read_text())