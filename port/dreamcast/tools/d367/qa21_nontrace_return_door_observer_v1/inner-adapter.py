"""Owned source-only inner adapter; launches only when explicitly invoked by reviewed outer.
No entrypoint is called during source/mock tests. Uses retained runner unchanged;
all changed limits/inputs are explicit and receipts bind both sources.
"""
import argparse,ctypes,hashlib,importlib.util,json,os,pathlib,re,sys,threading,time
P=pathlib.Path(__file__).parent

def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def validate_role(profile,mode,seed):
 if mode!='return-door01':raise ValueError('this child seal allows only return-door01')
 roles={r['name']:r for r in profile['roles']}
 if mode not in roles:raise ValueError('unreviewed role')
 if (mode=='cold-shoot01')!=(seed is None):raise ValueError('cold has no seed; later roles require same-program seed')
 return roles[mode]

def input_allowed(cap,disabled,elapsed):
 return not disabled and not (pathlib.Path(cap)/'inputs-disabled.json').exists() and elapsed<40.75

def publish_input_failure(cap,error):
 cap=pathlib.Path(cap);marker=cap/'input-failure.json'
 if marker.exists():return
 payload={'error':str(error),'pulse_telemetry':getattr(error,'pulse_telemetry',None),'scope':'failed qualification; unavailable telemetry is null'}
 pending=cap/'input-failure.pending'
 with pending.open('x') as f:json.dump(payload,f)
 os.replace(pending,marker)

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--profile',type=pathlib.Path,required=True);ap.add_argument('--mode',required=True);ap.add_argument('--cap',type=pathlib.Path,required=True);ap.add_argument('--seed',type=pathlib.Path);a=ap.parse_args()
 # No filesystem mutation or subprocess occurs before containment release.
 if sys.stdin.buffer.readline()!=b'owned-job-ready\n':raise RuntimeError('missing owned private-job release')
 profile=json.loads(a.profile.read_text());role=validate_role(profile,a.mode,a.seed);cap=a.cap
 if cap!=pathlib.Path(profile['evidence_root'])/'return-door-observer01':raise RuntimeError('wrong fixed child output contract')
 if cap.exists() or cap.resolve()!=cap.absolute():raise RuntimeError('evidence destination exists/alias')
 deps=profile['retained_dependencies'];runnerpath=pathlib.Path(deps['checkpoint_runner18.py']['path'])
 sys.path.insert(0,str(runnerpath.parent));sys.path.insert(0,str(P))
 for row in deps.values():
  if hashlib.sha256(pathlib.Path(row['path']).read_bytes()).hexdigest()!=row['sha256']:raise RuntimeError('retained dependency changed')
 from observe import Observer
 core=load('controller',P/'controller-core.py');broker=load('broker',P/'capture-budget.py').Budget();runner=load('runner',runnerpath)
 footprint=load('footprint',profile['retained_dependencies']['evidence_footprint.py']['path'])
 if pathlib.Path(runner.TEMPLATE).resolve()!=pathlib.Path(profile['template']['path']).resolve():raise RuntimeError('retained runner template differs')
 runner.FLOOR=18*1024**3+64*1024**2;runner.CAPTURE_LIMIT=60000000;runner.usage=lambda folder:footprint.measure(folder,pathlib.Path(profile['disc']['path']))['charged_bytes']
 # Original recipe/template only; no limit/default changes in any production file.
 os.environ['RE4DC_MAX_FLYCASTS']='16';os.environ['FP_NOLIMIT']='1'
 for key in ['RE4DC_CHECKPOINT_SEED','RE4DC_CHECKPOINT_LOG_HEAD','HW_FLYCAST','HWTRACE_ALIGN','RE4DC_EMU','RE4DC_CONSOLE_DYNAREC']:os.environ.pop(key,None)
 if a.seed:
  from checkpoint import verify
  disc_identity={'files':{n:r['sha256'] for n,r in profile['disc']['files'].items()},'program_sha256':profile['fixed_runtime']['program_sha256'],'elf_sha256':profile['fixed_runtime']['elf_sha256']}
  parent=verify(a.seed,pathlib.Path(profile['elf_path']),profile['observer']['binding'],profile['observer']['layout'],disc_identity,runner.emu_exe())
  parent_role=json.loads((a.seed/'inner-control.json').read_text())['mode'];expected='cold-shoot01' if a.mode=='return-door01' else 'return-door01'
  if parent_role!=expected:raise RuntimeError('same-program parent role differs')
  os.environ['RE4DC_CHECKPOINT_SEED']=str(a.seed);os.environ['RE4DC_CHECKPOINT_LOG_HEAD']=str(parent['audit']['log_head'])
 runner.KEYS.update(ltrig=(0x21,0),rtrig=(0x2f,0),fwd=(0x17,0),back=(0x25,0),turnleft=(0x24,0),turnright=(0x26,0));runner.VK.update(ltrig=0x46,rtrig=0x56,fwd=0x49,back=0x4b,turnleft=0x4a,turnright=0x4c)
 observer=Observer(cap,profile['observer']['binding'],profile['observer']['layout']);engine={'cold-shoot01':core.Shooting,'return-door01':core.Door,'cinematic01':core.Cinematic}[a.mode]();done=threading.Event();lock=threading.RLock();input_disabled=False;state={'mode':a.mode,'checkpoint_parent':str(a.seed) if a.seed else None,'source_only_prior_tests':True,'memory_writes':False,'inputs':[],'captures':[],'errors':[]};qacount=0
 qa_steps=[]
 if a.mode=='cold-shoot01':
  for line in pathlib.Path(role['keys']).read_text().splitlines():
   line=line.split('#')[0].strip()
   if line:qa_steps.append(line.split('|')[2].strip().split()[0])
 def elapsed():
  v=ctypes.c_ulonglong();observer.k.GetSystemTimeAsFileTime.argtypes=[ctypes.POINTER(ctypes.c_ulonglong)];observer.k.GetSystemTimeAsFileTime(ctypes.byref(v));return (v.value-observer.start)/1e7
 def native_post(key,up):
  if not observer.handle:raise RuntimeError('no owned observer handle')
  t=[ctypes.c_ulonglong() for _ in range(4)]
  if not observer.k.GetProcessTimes(observer.handle,*[ctypes.byref(x) for x in t]) or t[0].value!=observer.start:raise RuntimeError('input retained start mismatch')
  if t[1].value:
   if up:return {'queued':False,'messages':[],'reason':'retained guest already exited'}
   raise RuntimeError('no down to exited guest')
  # Live path rechecked before posts; this retained observer handle cannot target recycled PID.
  path=ctypes.create_unicode_buffer(32768);n=ctypes.c_ulong(len(path))
  if not observer.k.QueryFullProcessImageNameW(observer.handle,0,path,ctypes.byref(n)):
   ended=[ctypes.c_ulonglong() for _ in range(4)]
   if up and observer.k.GetProcessTimes(observer.handle,*[ctypes.byref(x) for x in ended]) and ended[0].value==observer.start and ended[1].value:return {'queued':False,'messages':[],'reason':'retained guest exited during path query'}
   raise RuntimeError('live input path unavailable')
  if pathlib.Path(path.value).resolve()!=(cap/'flycast.exe').resolve():raise RuntimeError('input path mismatch')
  if not up and not input_allowed(cap,input_disabled or bool(state['errors']) or runner.STOP_REQUESTED,elapsed()):raise RuntimeError('no keydown after disabled/cutoff')
  windows=runner.windows_of(observer.pid)
  if not windows:raise RuntimeError('exact owned windows unavailable for required queue')
  scan,ext=runner.KEYS[key];flags=1|(scan<<16)|(ext<<24)|(((1<<30)|(1<<31)) if up else 0)
  runner.user32.PostMessageW.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_size_t,ctypes.c_ssize_t]
  runner.user32.GetWindowThreadProcessId.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_ulong)]
  native={'queued':False,'messages':[],'pid':observer.pid,'start_filetime':observer.start,'scope':'PostMessageW return interval only; game acknowledgement unavailable'}
  try:
   for hwnd in windows:
    owner=ctypes.c_ulong()
    if not runner.user32.GetWindowThreadProcessId(hwnd,ctypes.byref(owner)) or owner.value!=observer.pid:raise RuntimeError('owned HWND changed before input queue')
    before=time.monotonic();queued=runner.user32.PostMessageW(hwnd,0x101 if up else 0x100,runner.VK[key],flags);after=time.monotonic()
    native['messages'].append({'hwnd':int(hwnd),'before_monotonic':before,'after_monotonic':after,'post_succeeded':bool(queued)})
    if not queued:raise ctypes.WinError(ctypes.get_last_error())
   native['queued']=True
   state['inputs'].append({'key':key,'up':up,'guest_s':elapsed(),'state':observer.last,'native_queue':native})
  except BaseException as error:error.native_queue_telemetry=native;raise
  return native
 failure_lock=threading.Lock()
 def input_failure(error):
  state['errors'].append('input deadline: '+str(error));runner.STOP_REQUESTED=True
  try:
   # Final name appears only after complete JSON, before outer job termination.
   # IO is after keyup, separate from the pure independent hardstop thread.
   with failure_lock:publish_input_failure(cap,error)
  except OSError as marker_error:state['errors'].append('input-failure marker unavailable: '+str(marker_error))
 inputs=load('input_deadlines',P/'input-deadlines.py').Inputs(native_post,elapsed,input_failure)
 def synchronize(forced=False):core.released_events(engine,a.mode,inputs.keys(),inputs.drain(),forced)
 def post(key,up,bound=None):
  if up:inputs.up(key);return
  if bound is None:bound=engine.pending_hold if a.mode=='return-door01' else (1.5 if key=='rtrig' else .15)
  when=inputs.down(key,bound)
  if not (a.mode=='cold-shoot01' and qacount<len(qa_steps)):core.actual_posted(engine,a.mode,key,when,observer.last)
 def release_all():inputs.release_all('normal-release');synchronize()
 def qa_press(pid,names,hold):
  nonlocal qacount
  with lock:
   if a.mode!='cold-shoot01' or qacount>=len(qa_steps) or names!=[qa_steps[qacount]] or hold>.15:raise RuntimeError('unreviewed/static input')
   limit=time.monotonic()+1
   while observer.handle is None:
    if not observer.register() and time.monotonic()>limit:raise RuntimeError('QA input owned observer registration unavailable')
    time.sleep(.01)
   if pid!=observer.pid:raise RuntimeError('runner PID differs')
   try:post(names[0],False,bound=hold);time.sleep(hold)
   finally:post(names[0],True)
   qacount+=1;return len(runner.windows_of(pid))
 runner.press=qa_press
 def capture_work(label):
  existing=sum(1 for _ in cap.rglob('*.png'));charged=runner.usage(cap)
  if not broker.request(label,existing,charged,final=label=='final'):raise RuntimeError('bounded capture unavailable')
  text=(cap/'run-output.txt').read_text(errors='replace');fb=re.findall(r'fb=[0-9a-f]+,[0-9a-f]+',text)
  if not fb:raise RuntimeError('source framebuffer unavailable')
  folder=cap/'events'/label;folder.mkdir(parents=True);before=observer.last
  import shutil
  for n in ['emu.cfg','flycast.log','flycast.pid']:shutil.copyfile(cap/n,folder/n)
  (folder/'boot.log').write_text(fb[-1]+'\n',encoding='utf-16');module=load('capture',cap/'capture_ui_vram.py');module.capture(folder,folder/'frames');observer.sample();after=observer.last
  (folder/'state-context.json').write_text(json.dumps({'before':before,'after':after,'non_atomic':True},indent=2)+'\n');broker.validate(sum(1 for _ in cap.rglob('*.png')));state['captures'].append(label)
 def capture(label):
  # No live held key may enter a blocking capture. Observer lock is deliberately
  # unrelated to Inputs.lock, so per-key release timers can always run.
  helper=load('capture_release',P/'input-deadlines.py')
  return helper.release_before_capture(inputs,synchronize,lambda:capture_work(label))
 def watch():
  nonlocal input_disabled
  try:
   final=False
   while not done.wait(.05):
    with lock:
     if state['errors']:raise RuntimeError('owned input guard failed')
     synchronize();observer.sample();synchronize()
     if not observer.handle or not observer.last:continue
     e=elapsed()
     if e>=40.75:release_all();continue
     if e>=39.3 and not final:input_disabled=True;capture('final');final=True
     if input_disabled:continue
     if a.mode=='cold-shoot01' and qacount<len(qa_steps):continue
     row=observer.last;native_text=(cap/'run-output.txt').read_text(errors='replace');row['death_demo_log_observed']='--DIEDEMO START!!' in native_text;age=time.monotonic()-row['observed_monotonic'];args=(row,age,e)
     manual='PlayingManual2' in (cap/'run-output.txt').read_text(errors='replace')
     if a.mode=='cinematic01' and a.seed:manual=manual or json.loads((a.seed/'inner-control.json').read_text()).get('original_manual_witness',False)
     actions=engine.step(*args,manual_log=manual) if a.mode=='cinematic01' else engine.step(*args)
     for action in actions:
      if 'capture'in action:
       state.setdefault('witnesses',[]).append(action);capture(action['capture']+'-'+str(len(state['captures'])))
      if 'down'in action:
       observer.sample();synchronize();fresh=observer.last;nowage=time.monotonic()-fresh['observed_monotonic']
       # Captures can consume time; every down is re-gated on a new sample.
       valid=core.policy.valid_sample(fresh) and 0<=nowage<=.2 and fresh.get('qa_flags')==0
       if a.mode=='cold-shoot01':valid=valid and core.policy.ordinary_weapon_ready(fresh) and fresh['global']['room']==0x103
       elif a.mode=='return-door01':valid=valid and core.policy.free_play(fresh) and fresh['global']['room']==0x103
       else:valid=valid and manual and fresh.get('subscreen_type')==64 and fresh.get('ssloop')==1 and fresh['global']['room']==0x101
       if not valid:raise RuntimeError('fresh post-capture input gate failed')
       post(action['down'],False)
      if 'up'in action:post(action['up'],True)
      if 'proof'in action:state.setdefault('discharges',[]).append(action['proof'])
     state['last']=observer.last;state['original_manual_witness']=manual and observer.last.get('subscreen_type')==64 and observer.last['global']['room']==0x101
  except EOFError:pass # retained process ended; no further input or handle query
  except BaseException as error:state['errors'].append(type(error).__name__+': '+str(error));runner.STOP_REQUESTED=True
  finally:
   with lock:
    try:release_all()
    except BaseException as error:state['errors'].append('release: '+str(error))
 thread=threading.Thread(target=watch,name='owned-readonly-controller',daemon=True);thread.start()
 logs=json.loads((P/'exact-log-symbols.json').read_text())['symbols'];syms=' '.join(hex(logs[n][0]['address']-0x8c000000) for n in ['_re4dc_logbuf','_re4dc_log_head','_re4dc_stage'])
 sys.argv=[str(runnerpath),'--disc',profile['disc']['path'],'--cap',str(cap),'--syms',syms,'--seconds','41','--period','0','--name',a.mode,'--keys',role['keys']]
 try:runner.main()
 finally:
  done.set()
  try:thread.join(timeout=2)
  finally:inputs.close()
  if thread.is_alive():raise RuntimeError('observer/controller thread still active; outer private job must reap')
  observer.close()
  if cap.exists():(cap/'inner-control.json').write_text(json.dumps(state,indent=2)+'\n')
 if state['errors']:raise RuntimeError('; '.join(state['errors']))
 # Checkpoint audit/seal runs AFTER outer wait/job close, not inside guest deadline.
if __name__=='__main__':main()
