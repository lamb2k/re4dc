from pathlib import Path
import hashlib,json,os,resource,shlex,subprocess,sys,tempfile,time,traceback
OWN=Path('/mnt/c/Game Dev/Emulators/codex-lanes/gc-motion24')
PREP=OWN/'target-prep';sys.path.insert(0,str(PREP))
from readback_prep import validate
TREE=Path('/root/work/lanes/gc-motion24')
SOURCE='aab201ceac0e18107f64a3212398afe916793327'
CAP=256*1024**2;FLOOR=24*1024**3

def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def free():s=os.statvfs('/mnt/c');return s.f_bavail*s.f_frsize
def git(*a):return subprocess.check_output(['git','-c','index.threads=1','-c','core.preloadIndex=false','-C',str(TREE),*a],text=True).strip()
def usage(p):return sum(f.stat().st_size for f in p.rglob('*') if f.is_file() and not f.is_symlink())
def execute(a,cwd,log):
 with log.open('wb') as f:r=subprocess.run(a,cwd=cwd,stdout=f,stderr=subprocess.STDOUT)
 if r.returncode:raise RuntimeError('Command failed '+str(r.returncode)+' '+str(log))
 return r.returncode

def main():
 if os.environ.get('GC_MOTION24_ALLOCATED')!=SOURCE:raise RuntimeError('Missing exact root allocation')
 resource.setrlimit(resource.RLIMIT_AS,(CAP,CAP));resource.setrlimit(resource.RLIMIT_CORE,(0,0))
 plan=json.loads((PREP/'PREPARATION.json').read_text());validate(plan)
 grant=json.loads((OWN/'ROOT-TARGET-GRANT.json').read_text())
 if grant['source']!=SOURCE or grant['preparation_sha256']!=sha(PREP/'PREPARATION.json') or grant['runner_sha256']!=sha(__file__):raise RuntimeError('Root grant mismatch')
 for k,v in plan['execution_environment_required'].items():
  if k not in ['wrapper'] and os.environ.get(k)!=v:raise RuntimeError('Environment mismatch '+k)
 if git('rev-parse','HEAD')!=SOURCE or git('status','--porcelain'):raise RuntimeError('Source not frozen')
 if free()<FLOOR:raise RuntimeError('C floor')
 out=Path(tempfile.mkdtemp(prefix='gc-motion24-target-run-',dir='/dev/shm'));export=Path(plan['export'])
 bins=Path(os.environ['KOS_CC_BASE'])/'bin'
 report={'source':SOURCE,'runtime':plan['runtime'],'parent':plan['parent'],'preparation_sha256':sha(PREP/'PREPARATION.json'),'runner_sha256':sha(__file__),'out':str(out),'export':str(export),'objects':[],'complete':False,'scope':'Fresh selected objects only; no full programme, runtime, heap, guest, coverage or provenance acceptance'}
 def save():(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
 def check():
  if free()<FLOOR or usage(out)+usage(export)>CAP:raise RuntimeError('Floor/owned output cap')
  if git('rev-parse','HEAD')!=SOURCE or git('status','--porcelain'):raise RuntimeError('Source moved')
 save();print(str(out),flush=True)
 try:
  for row in plan['arms']:
   check();tag=row['tag'];cwd=Path(row['cwd']);obj=out/(tag+'.o');a=row['argv'].copy();a[a.index('-o')+1]=str(obj)
   (out/(tag+'-command.json')).write_text(json.dumps(a,indent=2)+'\n')
   dep=out/(tag+'.d');d=a.copy();d[d.index('-c')]='-M';d[d.index('-o')+1]=str(dep);d=[x for x in d if x!='-fstack-usage']
   (out/(tag+'-dependency-command.json')).write_text(json.dumps(d,indent=2)+'\n')
   started=time.monotonic();execute(d,cwd,out/(tag+'-dependency.log'))
   text=dep.read_text().replace('\\\n',' ');names=shlex.split(text.split('\n',1)[0].split(':',1)[1]);pins={}
   for n in names:
    p=Path(n);p=p if p.is_absolute() else (cwd/p).resolve()
    if not p.is_file():raise RuntimeError('Missing full dependency '+str(p))
    pins[str(p)]={'bytes':p.stat().st_size,'sha256':sha(p)}
   if not pins:raise RuntimeError('Empty full dependency closure')
   (out/(tag+'-dependencies.json')).write_text(json.dumps(pins,indent=2)+'\n')
   execute(a,cwd,out/(tag+'-compile.log'))
   for p,pin in pins.items():
    if Path(p).stat().st_size!=pin['bytes'] or sha(p)!=pin['sha256']:raise RuntimeError('Dependency changed '+p)
   stripped=out/(tag+'-stripped.o');execute([str(bins/'sh-elf-objcopy'),'--strip-debug',str(obj),str(stripped)],cwd,out/(tag+'-strip.log'))
   sizes=subprocess.check_output([str(bins/'sh-elf-size'),str(obj)],text=True);(out/(tag+'-size.txt')).write_text(sizes)
   values=sizes.splitlines()[-1].split();sec=dict(zip(['text','data','bss'],map(int,values[:3])))
   for name,args in [('sections',['sh-elf-size','-A']),('defined',['sh-elf-nm','-C','--defined-only']),('undefined',['sh-elf-nm','-C','-u'])]:
    execute([str(bins/args[0]),*args[1:],str(obj)],cwd,out/(tag+'-'+name+'.txt'))
   su=obj.with_suffix('.su')
   item={'tag':tag,'unit':row['unit'],'label':row['label'],'gate':row['gate'],'motion':row['motion'],'sections':sec,'object_sha256':sha(obj),'stripped_sha256':sha(stripped),'dependency_count':len(pins),'dependencies_sha256':sha(out/(tag+'-dependencies.json')),'seconds':time.monotonic()-started,'stack_usage_sha256':sha(su) if su.is_file() else None,'empty_required':row['empty_required']}
   if row['empty_required']:
    if any(sec.values()):raise RuntimeError('OFF helper not section-empty')
    if (out/(tag+'-defined.txt')).read_text().strip():raise RuntimeError('OFF helper has defined symbols')
   report['objects'].append(item);save();print(json.dumps({'done':len(report['objects']),'of':len(plan['arms']),'tag':tag,'sections':sec}),flush=True)
  identity=[]
  for unit in ['native_ui','native_model','native_actor_fast','model_bridge']:
   for gate in [0,1]:
    tags=['parent-'+unit+'-gate'+str(gate)+'-motionabsent','current-'+unit+'-gate'+str(gate)+'-motionabsent','current-'+unit+'-gate'+str(gate)+'-motionzero']
    rows=[next(x for x in report['objects'] if x['tag']==t) for t in tags]
    if len({x['stripped_sha256'] for x in rows})!=1:raise RuntimeError('Disabled object identity mismatch '+str(tags))
    identity.append({'unit':unit,'gate':gate,'stripped_sha256':rows[0]['stripped_sha256'],'arms':tags})
  report['disabled_identity']=identity
  parent=[x for x in report['objects'] if x['label']=='parent' and x['gate']==1]
  on=[x for x in report['objects'] if x['motion']=='on']
  report['selected_ON_delta']={k:sum(x['sections'][k] for x in on)-sum(x['sections'][k] for x in parent) for k in ['text','data','bss']}
  helper=next(x for x in on if x['unit']=='platform/gc_asset_motion_unknown.cpp')
  if helper['sections']['bss']>32:raise RuntimeError('Helper raw BSS cap exceeded')
  # Mangled symbol closure. Existing full ON ELF and real SDK archives are
  # candidate providers only, not a freshly linked map or chain acceptance.
  provider_names=[n for n in plan['input_pins'] if n.endswith(('libkallisti.a','libgcc.a','libc.a','re4dc-game.elf'))]
  defs=set();providers=[]
  for n in provider_names+[str(out/(x['tag']+'.o')) for x in on]:
   raw=subprocess.check_output([str(bins/'sh-elf-nm'),'--defined-only',n],text=True,stderr=subprocess.DEVNULL)
   for line in raw.splitlines():
    v=line.split()
    if len(v)>=3 and v[-2].upper() in ['T','D','B','R','W','V','A','S','C']:defs.add(v[-1])
   providers.append({'path':n,'sha256':sha(n)})
  needed=set()
  for x in on:
   raw=subprocess.check_output([str(bins/'sh-elf-nm'),'-u',str(out/(x['tag']+'.o'))],text=True)
   for line in raw.splitlines():
    v=line.split()
    if len(v)>=2 and v[-2]=='U':needed.add(v[-1])
  missing=sorted(needed-defs);report['provider_closure']={'needed':len(needed),'missing':missing,'providers':providers,'limit':'Candidate real providers and selected objects only; no new full programme/map, aliases or stubs'}
  if missing:raise RuntimeError('Missing real provider '+str(missing))
  validate(plan);check();report['complete']=True;save()
 except BaseException as e:
  report['failure']=repr(e);report['traceback']=traceback.format_exc();save();raise
 finally:
  report['owned_output_bytes']=usage(out)+usage(export);save();print(json.dumps({'out':str(out),'complete':report['complete'],'objects':len(report['objects']),'failure':report.get('failure')}),flush=True)

if __name__=='__main__':main()