#!/usr/bin/env python3
"""Selected SH4 preparation/read-only validation; --run additionally needs root's grant.
No SDK process is started by seal/check/plan. Do not use --run before allocation.
"""
import argparse, ctypes, hashlib, json, os, pathlib, re, resource, shlex, signal, subprocess, time
HERE=pathlib.Path(__file__).resolve().parent
TREE=pathlib.Path('/root/work/lanes/rain-diag24')
BASE='bca44d58a1fa0a51fd87ba94deba8cba925c8998'
SOURCE='da413ff058f88fa136375ecff629610fc59c0e51'
RUNTIME='fdb5ed4212fc78823f625ab75b78cc237cfd181a'
OLD=pathlib.Path('/root/work/lanes/water-rain24-full-target-scratch')
UNITS=('filter06','espgen44')
CAP=256*1024*1024
LIMITS={'address_space_bytes':CAP,'owned_output_bytes':CAP,'jobs':1,'command_seconds':60,'wall_seconds':360,'C_floor_bytes':24*1024**3}
TOOLS={'cxx':'/root/work/kos-re4dc-d367/utils/build_wrappers/kos-c++','cc_wrapper':'/root/work/kos-re4dc-d367/utils/build_wrappers/kos-cc','driver':'/opt/toolchains/dc/sh-elf/bin/sh-elf-g++','bootstrap_c_driver':'/opt/toolchains/dc/sh-elf/bin/sh-elf-gcc','cc1':'/opt/toolchains/dc/sh-elf/libexec/gcc/sh-elf/15.2.0/cc1','cc1plus':'/opt/toolchains/dc/sh-elf/libexec/gcc/sh-elf/15.2.0/cc1plus','as':'/opt/toolchains/dc/sh-elf/bin/sh-elf-as','ld':'/opt/toolchains/dc/sh-elf/bin/sh-elf-ld','objcopy':'/opt/toolchains/dc/sh-elf/bin/sh-elf-objcopy','objdump':'/opt/toolchains/dc/sh-elf/bin/sh-elf-objdump','kos_env':'/root/work/kos-re4dc-d367/environ_base.sh','kos_arch_env':'/root/work/kos-re4dc-d367/environ_dreamcast.sh','kos_version':'/root/work/kos-re4dc-d367/include/kos/version.h','cache_h':'/root/work/kos-re4dc-d367/include/kos/cache.h','arch_cache_h':'/root/work/kos-re4dc-d367/kernel/arch/dreamcast/include/arch/cache.h','slot':'/root/probe/d367-buildslot.sh'}
def digest(b):return hashlib.sha256(b).hexdigest()
def pin(p):
 p=pathlib.Path(p);return {'path':str(p),'resolved':str(p.resolve()),'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())}
def write_json(p,value):
 with pathlib.Path(p).open('x') as f:json.dump(value,f,indent=2);f.write('\n')
def git_bytes(commit,path):return subprocess.check_output(['git','-C',str(TREE),'show',commit+':'+path])
def deps(text):
 # GCC Make syntax, first target only; escaped continuations and names supported.
 first=text.replace('\\\n',' ').splitlines()[0]
 if ': ' not in first:raise ValueError('dependency target missing')
 return shlex.split(first.split(': ',1)[1])
def source_rel(dep):
 p=(pathlib.PurePosixPath('port/dreamcast/game')/dep)
 parts=[]
 for x in p.parts:
  if x=='..':
   if not parts:raise ValueError('dependency escapes repository')
   parts.pop()
  elif x!='.':parts.append(x)
 return '/'.join(parts)
def normal_args(line):
 a=shlex.split(line)
 if a[0]!='kos-c++' or a.count('-o')!=1 or a.count('-c')!=1 or a.count('-MMD')!=1 or a.count('-MP')!=1:raise ValueError('normal argv shape')
 return a[1:]
def comparable(a):
 a=list(a);a[a.index('-o')+1]='<OWN_OUTPUT>'
 return [x for x in a if x!='-DRE4DC_RAIN_R10C_DC=1']
def case_specs():
 return [(f'base-f{f}',BASE,f,None) for f in (0,1)]+[(f'new-f{f}-d{d}',SOURCE,f,d) for f in (0,1) for d in ('absent','0','1')]
def seal(dest):
 dest=pathlib.Path(dest);dest.mkdir(parents=True,exist_ok=True)
 if (dest/'PINS.json').exists():raise ValueError('seal already exists')
 p={'base':BASE,'source':SOURCE,'runtime':RUNTIME,'scope':'PREPARATION ONLY; selected objects; no SDK executed','tools':{k:pin(v) for k,v in TOOLS.items()},'provider':pin(OLD/'off/out/re4dc-game.elf'),'normal':{},'inputs':{},'source_files':{},'case_names':[x[0] for x in case_specs()],'limits':LIMITS}
 files=set()
 for feature,arm in ((0,'off'),(1,'on')):
  log=OLD/arm/'build.log';p['inputs'][str(log)]=pin(log);resolved=OLD/arm/'out/resolved-knobs.txt';p['inputs'][str(resolved)]=pin(resolved);lines=log.read_text().splitlines()
  for unit in UNITS:
   found=[l for l in lines if l.startswith('kos-c++ ') and ('/'+unit+'.cpp') in l and ' -c ' in l]
   if len(found)!=1:raise ValueError('normal compile line not unique')
   d=OLD/arm/'out/obj/src/game'/(unit+'.d');p['inputs'][str(d)]=pin(d)
   a=normal_args(found[0]);p['normal'][f'{feature}/{unit}']={'argv':a,'line':found[0],'dependency_tokens':deps(d.read_text())}
   files.update(source_rel(x) for x in deps(d.read_text()))
 for unit in UNITS:
  a=p['normal']['0/'+unit]['argv'];b=p['normal']['1/'+unit]['argv']
  if comparable(a)!=comparable(b):raise ValueError('unexpected feature argv differences')
  expected=1 if unit=='filter06' else 0
  if b.count('-DRE4DC_RAIN_R10C_DC=1')!=expected or '-DRE4DC_RAIN_R10C_DC=1' in a:raise ValueError('feature-specific Make wiring')
 files.update(('port/dreamcast/kos-env.sh','port/dreamcast/game/effects30.mk'))
 for rel in sorted(files):
  a=git_bytes(BASE,rel);b=git_bytes(SOURCE,rel)
  if rel not in ('src/game/filter06.cpp','src/game/espgen44.cpp','port/dreamcast/game/effects30.mk') and a!=b:raise ValueError('unexpected dependency change '+rel)
  if rel in ('src/game/filter06.cpp','src/game/espgen44.cpp','port/dreamcast/game/effects30.mk') and git_bytes(RUNTIME,rel)!=b:raise ValueError('da/fdb runtime differs')
  p['source_files'][rel]={'base':{'sha256':digest(a),'bytes':len(a)},'new':{'sha256':digest(b),'bytes':len(b)}}
 for f in ('matrix.py','readback.py','run-matrix.sh','test_preparation.py','README.md'):
  p.setdefault('helpers',{})[f]={'sha256':digest((HERE/f).read_bytes()),'bytes':(HERE/f).stat().st_size}
 write_json(dest/'PINS.json',p);return p

def validate_tools(p):
 if set(p['tools'])!=set(TOOLS):raise ValueError('incomplete tool closure including bootstrap cc1')
 for row in p['tools'].values():
  if pin(row['path'])!=row:raise ValueError('pinned tool drift '+row['path'])
 return True

def validate(p):
 validate_tools(p)
 if (p['base'],p['source'],p['runtime'])!=(BASE,SOURCE,RUNTIME) or p['case_names']!=[x[0] for x in case_specs()] or p.get('limits')!=LIMITS:raise ValueError('wrong source/cases')
 for row in list(p['inputs'].values())+[p['provider']]:
  if pin(row['path'])!=row:raise ValueError('pinned input drift '+row['path'])
 for feature,arm in ((0,'off'),(1,'on')):
  lines=(OLD/arm/'build.log').read_text().splitlines()
  for unit in UNITS:
   row=p['normal'][f'{feature}/{unit}'];found=[x for x in lines if x.startswith('kos-c++ ') and ('/'+unit+'.cpp') in x and ' -c ' in x]
   if found!=[row['line']] or normal_args(row['line'])!=row['argv'] or deps((OLD/arm/'out/obj/src/game'/(unit+'.d')).read_text())!=row['dependency_tokens']:raise ValueError('normal argv/dependency provenance')
 for rel,row in p['source_files'].items():
  for name,commit in (('base',BASE),('new',SOURCE)):
   b=git_bytes(commit,rel)
   if {'sha256':digest(b),'bytes':len(b)}!=row[name]:raise ValueError('frozen source drift')
 for rel in ('src/game/filter06.cpp','src/game/espgen44.cpp','port/dreamcast/game/effects30.mk','port/dreamcast/kos-env.sh'):
  if digest((TREE/rel).read_bytes())!=p['source_files'][rel]['new']['sha256']:raise ValueError('canonical frozen runtime/environment drift '+rel)
 for name,row in p['helpers'].items():
  b=(HERE/name).read_bytes()
  if {'sha256':digest(b),'bytes':len(b)}!=row:raise ValueError('helper drift '+name)
 return True

def grant_check(p,pins_path,g,output):
 expected={'kind':'ROOT_SELECTED_SH4_GRANT','source':SOURCE,'base':BASE,'pins_sha256':digest(pathlib.Path(pins_path).read_bytes()),'output':str(pathlib.Path(output)),'jobs':1,'address_space_bytes':CAP,'owned_output_bytes':CAP,'command_seconds':60,'wall_seconds':360,'case_names':p['case_names']}
 if not isinstance(g,dict) or any(g.get(k)!=v for k,v in expected.items()) or g.get('authorized') is not True or not re.fullmatch(r'[A-Za-z0-9_-]{8,80}',g.get('grant_id','')):raise ValueError('missing/mismatched root allocation grant')
 return expected

def argv(p,feature,unit,diag,output):
 a=list(p['normal'][f'{feature}/{unit}']['argv'])
 a[a.index('-o')+1]=str(output)
 if diag not in (None,'absent','0','1'):raise ValueError('diag option')
 if diag not in (None,'absent'):a.insert(a.index('-MMD'),'-DRE4DC_RAIN_R10C_DIAG='+diag)
 a.insert(a.index('-MMD'),'-fstack-usage')
 return [p['tools']['cxx']['path']]+a

def cap_check(root):
 total=0
 for q in pathlib.Path(root).rglob('*'):
  if q.is_symlink():raise ValueError('owned output symlink')
  if q.is_file():total+=q.stat().st_size
 if total>CAP:raise ValueError('owned output cap exceeded')
 return total

def path_check(output):
 q=pathlib.Path(output)
 if q.parent!=pathlib.Path('/dev/shm') or not re.fullmatch(r'rain-diag24-target-[A-Za-z0-9_-]{8,80}',q.name) or q.exists():raise ValueError('fresh exact owned RAM output required')
 if pathlib.Path('/dev/shm').stat().st_dev!=q.parent.stat().st_dev:raise ValueError('RAM mount')
 return q

def reserve(p,pins_path,g,output):
 grant_check(p,pins_path,g,output);validate(p);root=path_check(output)
 if os.statvfs('/dev/shm').f_bavail*os.statvfs('/dev/shm').f_frsize<CAP+32*1024**2:raise ValueError('RAM admission')
 if os.statvfs('/mnt/c').f_bavail*os.statvfs('/mnt/c').f_frsize<p['limits']['C_floor_bytes']:raise ValueError('C floor')
 root.mkdir();write_json(root/'RESERVED.json',{'pins_sha256':digest(pathlib.Path(pins_path).read_bytes()),'grant':g,'state':'reserved under root allocation; SDK may follow'})
 return root

def execute(p,pins_path,g,output):
 # Only called after run-matrix.sh has acquired the canonical lease and SDK slot.
 if os.environ.get('RAIN_DIAG_MATRIX_SLOT')!=digest(pathlib.Path(pins_path).read_bytes()) or os.environ.get('D367_SLOT_HELD')!='1':raise ValueError('bounded wrapper required')
 grant_check(p,pins_path,g,output);validate(p);root=pathlib.Path(output)
 if root.is_symlink() or set(x.name for x in root.iterdir())!={'RESERVED.json','environment-bootstrap.log','environment.nul','bootstrap-tmp'}:raise ValueError('fresh reserved output required')
 reservation=json.loads((root/'RESERVED.json').read_text())
 if reservation.get('pins_sha256')!=digest(pathlib.Path(pins_path).read_bytes()) or reservation.get('grant')!=g:raise ValueError('reservation identity')
 def interrupted(sig,frame):raise InterruptedError('owned wrapper signal '+str(sig))
 signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
 start=time.monotonic();write_json(root/'grant.json',g);write_json(root/'pins.json',p)
 result={'source':SOURCE,'base':BASE,'runtime':RUNTIME,'pins_sha256':digest(pathlib.Path(pins_path).read_bytes()),'grant_id':g['grant_id'],'selected_compilation_complete':False,'artifacts':{},'commands':[],'case_names':p['case_names'],'limits':p['limits'],'SDK_only_after_explicit_root_grant':True}
 bench=root/'bench';cwd=bench/'port/dreamcast/game';cwd.mkdir(parents=True);tmp=root/'tmp';tmp.mkdir();os.environ['TMPDIR']=str(tmp)
 def command(a,tag,stdout=None):
  if time.monotonic()-start>p['limits']['wall_seconds']:raise ValueError('whole matrix deadline')
  cap_check(root);log=root/(tag+'.log');out=root/(tag+'.stdout') if stdout is None else stdout
  if log.exists() or out.exists():raise ValueError('log/output overwrite')
  result['commands'].append({'argv':a,'cwd':str(cwd),'stdout':str(out.relative_to(root)),'stderr':str(log.relative_to(root))})
  parent_pid=os.getpid()
  def limits():
   resource.setrlimit(resource.RLIMIT_AS,(CAP,CAP));os.setsid()
   # Prevent a surviving SDK process if this exact owner dies unexpectedly.
   libc=ctypes.CDLL(None,use_errno=True)
   if libc.prctl(1,signal.SIGKILL,0,0,0)!=0 or os.getppid()!=parent_pid:os._exit(125)
  with out.open('xb') as of,log.open('xb') as ef:
   child=subprocess.Popen(a,cwd=cwd,stdout=of,stderr=ef,env=os.environ.copy(),preexec_fn=limits)
   deadline=min(start+p['limits']['wall_seconds'],time.monotonic()+60)
   try:
    while child.poll() is None:
     cap_check(root)
     if time.monotonic()>deadline:raise ValueError('owned command deadline')
     time.sleep(.05)
    if child.returncode:raise ValueError('target command failed '+tag+' '+str(child.returncode))
   except BaseException:
    if child.poll() is None:os.killpg(child.pid,signal.SIGKILL)
    child.wait();raise
  cap_check(root)
 def dependency_pins(text):
  items={}
  allowed=[bench.resolve(),pathlib.Path('/root/work/kos-re4dc-d367').resolve(),pathlib.Path('/root/work/kos-ports').resolve(),pathlib.Path('/opt/toolchains/dc').resolve()]
  for d in deps(text):
   q=pathlib.Path(d);q=(cwd/q).resolve() if not q.is_absolute() else q.resolve()
   if not any(q.is_relative_to(x) for x in allowed):raise ValueError('unadmitted consumed dependency '+str(q))
   items[str(q)]=pin(q)
  return items
 try:
  # Fixed bench path/output spelling across arms. Only its two owned primaries change.
  for rel,row in p['source_files'].items():
   q=bench/rel;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(git_bytes(BASE,rel))
  for case,commit,feature,diag in case_specs():
   directory=root/'cases'/case;directory.mkdir(parents=True)
   for unit in UNITS:
    primary=bench/'src/game'/(unit+'.cpp');old=primary.read_bytes()
    if digest(old) not in [p['source_files']['src/game/'+unit+'.cpp'][x]['sha256'] for x in ('base','new')]:raise ValueError('owned bench primary drift')
    primary.write_bytes(git_bytes(commit,'src/game/'+unit+'.cpp'))
    scratch=root/'selected.o';a=argv(p,feature,unit,diag,scratch);stem=case+'-'+unit
    # Exact wrapper env is evidence; normal logged argv is not claimed to include wrapper-added flags.
    write_json(directory/(unit+'-argv.json'),{'normal_log_argv':p['normal'][f'{feature}/{unit}']['argv'],'selected_argv':a,'explicit_deltas':['own output operand','-fstack-usage']+([] if diag in(None,'absent') else ['-DRE4DC_RAIN_R10C_DIAG='+diag]),'KOS_CFLAGS':os.environ.get('KOS_CFLAGS'),'KOS_CPPFLAGS':os.environ.get('KOS_CPPFLAGS'),'KOS_CCPLUS':os.environ.get('KOS_CCPLUS'),'KOS_CC':os.environ.get('KOS_CC')})
    stripped=[x for x in a if x not in ('-MMD','-MP','-c')];idx=stripped.index('-o');del stripped[idx:idx+2]
    depfile=directory/(unit+'-before.d');command(stripped+['-M','-MT','selected.o'],stem+'-deps',depfile)
    before=dependency_pins(depfile.read_text());write_json(directory/(unit+'-before-pins.json'),before)
    command(stripped+['-E','-H'],stem+'-includes',directory/(unit+'.ii'))
    compile_a=list(a);compile_a[compile_a.index('-MMD')]='-MD';compile_a[compile_a.index('-MP'):compile_a.index('-MP')]=['-MF',str(root/'selected.d'),'-MT','selected.o']
    command(compile_a,stem+'-compile')
    after=dependency_pins((root/'selected.d').read_text())
    if before!=after:raise ValueError('precompile/actual dependency set or bytes changed')
    write_json(directory/(unit+'-actual-pins.json'),after)
    for ext in ('o','d','su'):(root/('selected.'+ext)).rename(directory/(unit+'.'+ext))
    command([p['tools']['objcopy']['path'],'--strip-debug',str(directory/(unit+'.o')),str(directory/(unit+'-nodebug.o'))],stem+'-strip')
    command([p['tools']['objdump']['path'],'-drwC',str(directory/(unit+'.o'))],stem+'-disassemble',directory/(unit+'-disassembly.txt'))
   command([p['tools']['ld']['path'],'-r','-EL','-o',str(directory/'pair.o')]+[str(directory/(u+'.o')) for u in UNITS],case+'-partial-link')
  validate(p);result['selected_compilation_complete']=True
 except BaseException as ex:
  result['failure']=repr(ex);raise
 finally:
  result['elapsed_seconds']=time.monotonic()-start;result['owned_bytes']=cap_check(root)
  for q in root.rglob('*'):
   if q.is_file():result['artifacts'][str(q.relative_to(root))]={'bytes':q.stat().st_size,'sha256':digest(q.read_bytes())}
  write_json(root/'matrix-result.json',result)
 return result

def main():
 ap=argparse.ArgumentParser();ap.add_argument('mode',choices=('seal','check','plan','reserve','run'));ap.add_argument('--pins',default=str(HERE/'PINS-ROOT-FIX-V2.json'));ap.add_argument('--out');ap.add_argument('--grant');args=ap.parse_args()
 if args.mode=='seal':print(json.dumps({'pins':str(pathlib.Path(args.pins)),'cases':seal(pathlib.Path(args.pins).parent)['case_names']}));return
 p=json.loads(pathlib.Path(args.pins).read_text());validate(p)
 if args.mode=='check':
  if args.grant:grant_check(p,args.pins,json.loads(pathlib.Path(args.grant).read_text()),args.out);path_check(args.out)
  print('PREPARATION pins valid; no SDK process executed');return
 if args.mode=='plan':
  print(json.dumps({'cases':case_specs(),'example_selected_argv':{u:argv(p,1,u,'1','<fresh-owned-root>/selected.o') for u in UNITS},'future_limits':p['limits'],'run_requires_root_grant':True},indent=2));return
 if not args.grant or not args.out:raise ValueError('--grant and --out required')
 if args.mode=='run':
  entries=(pathlib.Path(args.out)/'environment.nul').read_bytes().split(b'\0')
  if entries[-1]!=b'':raise ValueError('bootstrap environment not NUL terminated')
  env={}
  for entry in entries[:-1]:
   key,separator,value=entry.partition(b'=')
   if not separator or not re.fullmatch(rb'[A-Za-z_][A-Za-z0-9_]*',key) or key.decode() in env:raise ValueError('bootstrap environment key')
   env[key.decode()]=value.decode()
  if env.get('KOS_SH4_PRECISION')!='-m4-single' or env.get('KOS_CCPLUS')!=p['tools']['driver']['path'] or env.get('KOS_BASE')!='/root/work/kos-re4dc-d367':raise ValueError('bootstrap profile/driver drift')
  os.environ.clear();os.environ.update(env)
 (reserve if args.mode=='reserve' else execute)(p,args.pins,json.loads(pathlib.Path(args.grant).read_text()),args.out)
if __name__=='__main__':main()
