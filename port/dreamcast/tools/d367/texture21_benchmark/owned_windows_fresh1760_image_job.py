"""One explicitly allocated native Windows argv; no shell, retries, deletion or promotion.
Default validates only. Root supplies exact plan/allocation hashes before --execute.
"""
from pathlib import Path
import argparse,ctypes as C,ctypes.wintypes as W,hashlib,json,os,shutil,subprocess,sys,threading,time

if os.name=='nt':import msvcrt

BASE_FLOOR=18*1024**3+64*1024**2
PRODUCTION=Path(r'C:\Flycast-Evidence\re4-dreamcast\texture21-benchmark-20261021\fresh1760-pair-01\M1')
PAYLOAD_ROOTS=()
PACK_CAP=1342177280;METADATA_CAP=16777216
PARENT_SEAL=Path(r'C:\Flycast-Evidence\re4-dreamcast\texture21-benchmark-20261021\fresh1760-disc-plan-01\UNIT-SHA256SUMS')
PARENT_SEAL_SHA='2e0d2afc61ae64ac1175e67bbcab223b6ad7cb2a45661f5d255b58cc5c72c917'
SOURCE_SEAL=Path(r'C:\Flycast-Evidence\re4-dreamcast\texture21-benchmark-20261021\fresh1760-image-tools-v2-01\SHA256SUMS')
SOURCE_SEAL_SHA='b6ad9e126e75a4c89f134077bd8765d22fc9f3cfaee5e6beef46aee8112ffc5b'
WRITER=SOURCE_SEAL.parent/'sources'/'fresh1760_stage_v2.py'
WRITER_SHA='6edaeb7e3fe90f0a7514c7ec3c0e76fc287d2a23031c1f3fabe8b32f46cdb1cb'
READER=SOURCE_SEAL.parent/'sources'/'fresh1760_readback.py'
READER_SHA='f83601d116db18d654b466cf2e537a7d9a65f123d7fe0bbccdab7fba53595119'
SOURCE='63644457a2251a398de174f47be650e1b2b4c791'
CONTROLS=Path(r'C:\Game Dev\Emulators\codex-lanes\texture21-benchmark\fresh1760-controller-controls')
ALLOCATIONS=Path(r'C:\Game Dev\Emulators\codex-lanes\texture21-benchmark')
MAX_LOG=8*1024**2
FINAL_METADATA_HEADROOM=64*1024


def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def canonical(p):
 p=Path(p).absolute()
 if p.resolve()!=p:raise ValueError('Path/ancestor alias refused: '+str(p))
 return p
def within(p,root):
 try:canonical(p).relative_to(canonical(root));return True
 except ValueError:return False
def require_cache_environment(root):
 # Prerequisite established by root BEFORE Python startup; never rewrite inherited env.
 expected=canonical(root/'pycache');raw=os.environ.get('PYTHONPYCACHEPREFIX');effective=sys.pycache_prefix
 if not sys.dont_write_bytecode or os.environ.get('PYTHONDONTWRITEBYTECODE')!='1':raise ValueError('Root must start Python with PYTHONDONTWRITEBYTECODE=1')
 if not raw or not effective or not Path(raw).is_absolute() or canonical(raw)!=expected or canonical(effective)!=expected:raise ValueError('Root must set effective absolute PYTHONPYCACHEPREFIX under charged metadata/pycache')
 if expected.exists():raise FileExistsError('Preserve existing pycache prefix; a fresh absent prefix is required')
 return dict(dont_write_bytecode=True,PYTHONDONTWRITEBYTECODE='1',effective_pycache_prefix=str(expected),inherited_without_override=True)
def digest_value(v):return isinstance(v,str)and len(v)==64 and all(c in'0123456789abcdef'for c in v)

def require_image_bindings(plan,inputs,allocation=None):
 if plan.get('source')!=SOURCE or plan.get('arm')!='M1':raise ValueError('Only new792 candidate M1 source allowed')
 for path,h in ((PARENT_SEAL,PARENT_SEAL_SHA),(SOURCE_SEAL,SOURCE_SEAL_SHA),(WRITER,WRITER_SHA),(READER,READER_SHA)):
  if inputs.get(str(path))!=h or sha(path)!=h:raise ValueError('Fixed data/source/writer/reader pin')
 image_plan=canonical(plan['image_plan_path']);h=plan['image_plan_sha256']
 if inputs.get(str(image_plan))!=h or sha(image_plan)!=h:raise ValueError('Exact bound image plan required')
 ip=json.loads(image_plan.read_text());m=ip['programme'];a=ip['programme_admission'];ap=canonical(a['path'])
 if ip['schema']!='fresh1760-paired-image-plan-v1'or ip['source']!=SOURCE or m['runtime_source']!=SOURCE:raise ValueError('Qualified792 image plan source')
 if ip['data_unit']!=dict(path=str(PARENT_SEAL),sha256=PARENT_SEAL_SHA):raise ValueError('Fixed parent data unit')
 if plan['programme_admission_path']!=str(ap)or plan['programme_admission_sha256']!=a['sha256']or inputs.get(str(ap))!=a['sha256']or sha(ap)!=a['sha256']:raise ValueError('Actual programme admission pin')
 admission=json.loads(ap.read_text())
 if admission['schema']!='qualified792-programme-stage-admission-v1'or admission['qualified']is not True or admission['source']!=SOURCE:raise ValueError('Actual qualified programme admission')
 proof={}
 for name in ('qualification','independent','consumer','tool_closure','manifest'):
  ref=admission[name];path=canonical(ref['path']);digest=ref['sha256']
  if inputs.get(str(path))!=digest or sha(path)!=digest:raise ValueError('Qualified programme proof source pin: '+name)
  proof[name]=json.loads(path.read_text())
 q=proof['qualification'];ind=proof['independent'];consumer=proof['consumer'];manifest=proof['manifest'];tool=proof['tool_closure']
 for field,expected in (('ELF_sha256',m['ELF']['sha256']),('programme_sha256',m['programme_sha256'])):
  if not digest_value(expected)or not all(r.get(field)==expected for r in(q,ind,consumer))or plan.get(field)!=expected:raise ValueError('Exact q/ind/consumer/plan programme identity')
 if manifest!=m or consumer.get('source')!=SOURCE or consumer.get('new_programme_qualified')is not True or consumer.get('all_consumer_gates_qualified')is not True:raise ValueError('Exact qualified linked consumer/manifest')
 if tool.get('qualified')is not True or tool.get('complete_actual_exec_plugin_tool_closure')is not True or tool.get('new_unit_pre_post')is not True or tool.get('source')!=SOURCE:raise ValueError('Actual new exec/plugin pre-post closure')
 if plan.get('consumer_sha256')!=admission['consumer']['sha256']:raise ValueError('Explicit actual consumer digest')
 if ip['arms']['M1']['predicted']['bytes']!=ip['image_bytes']or not digest_value(ip['arms']['M1']['predicted']['sha256']):raise ValueError('Exact candidate predicted image identity')
 if plan.get('expected_image_bytes')!=ip['image_bytes']or plan.get('expected_image_sha256')!=ip['arms']['M1']['predicted']['sha256']or plan.get('uncompressed_forecast_bytes')!=ip['proposal']['exact_uncompressed_forecast_bytes']:raise ValueError('Explicit candidate predicted bytes/hash/forecast')
 if ip['proposal']['exact_uncompressed_forecast_bytes']>PACK_CAP or ip['image_bytes']>PACK_CAP-METADATA_CAP:raise ValueError('Candidate physical aggregate forecast')
 if ip['source_sha256'].get(WRITER.name)!=WRITER_SHA or ip['source_sha256'].get(READER.name)!=READER_SHA:raise ValueError('Child dependency source pins')
 for name,digest in ip['source_sha256'].items():
  path=WRITER.parent/name
  if Path(name).name!=name or inputs.get(str(path))!=digest or sha(path)!=digest:raise ValueError('All local child dependency pins')
 if allocation is not None:
  for key in ('image_plan_sha256','programme_admission_sha256','ELF_sha256','programme_sha256','consumer_sha256'):
   if allocation.get(key)!=plan[key]:raise ValueError('Exact outer allocation programme/image pin')
 return ip

def validate(plan_path,plan_sha,allocation_path,allocation_sha):
 pp=canonical(plan_path)
 if sha(pp)!=plan_sha:raise ValueError('Plan SHA differs')
 plan=json.loads(pp.read_text());root=canonical(plan['approved_output_root']);test=plan.get('control_test')is True
 if not((test and within(root,CONTROLS)and root!=CONTROLS)or(not test and root==PRODUCTION)):raise ValueError('Unapproved candidate-only namespace')
 if not test:
  if plan.get('schema')!='fresh1760-candidate-controller-plan-v1':raise ValueError('Exact candidate controller schema')
  require_cache_environment(root)
 if plan.get('approved_payload_roots')!=[]:raise ValueError('No external image/mirror/temp output roots approved')
 receipt=canonical(plan['receipt']);log=canonical(plan['log'])
 if not test and(receipt!=root/'controller.json'or log!=root/'controller.log'):raise ValueError('Exact fixed controller receipt/log paths')
 if not within(receipt,root)or not within(log,root)or receipt==log or receipt.exists()or log.exists():raise ValueError('Fresh separate owned receipt/log required')
 if not receipt.parent.is_dir()or not log.parent.is_dir():raise ValueError('Root prepares exact metadata parents')
 outputs=plan['new_outputs']
 if not isinstance(outputs,list)or len(outputs)!=len(set(outputs)):raise ValueError('Explicit distinct output list')
 for output in outputs:
  if not within(output,root)or Path(output).exists():raise ValueError('Output exists or escapes candidate root')
 if not test:
  expected=[str(root/'gdemu')]+[str(root/'gdemu'/n)for n in('track01.bin','track02.raw','disc.gdi','track03.iso')]+[str(root/'full-readback.json'),str(root/'child-result.json')]
  if set(outputs)!=set(expected):raise ValueError('Exact image/smalltrack/readback new output set')
  if any(root.iterdir()):raise ValueError('Candidate root must be freshly prepared empty metadata')
 argv=plan['argv']
 if not isinstance(argv,list)or len(argv)<2 or not all(isinstance(x,str)and x and'\0'not in x for x in argv):raise ValueError('One explicit native argv')
 exe=canonical(argv[0]);cwd=canonical(plan['cwd']);inputs=plan['input_sha256']
 if not cwd.is_dir()or not exe.is_file()or exe.suffix.lower()!='.exe'or exe.name.lower()in('wsl.exe','bash.exe','cmd.exe','powershell.exe','pwsh.exe'):raise ValueError('Native executable/cwd only')
 if inputs.get(str(exe))!=sha(exe):raise ValueError('Exact native executable pin')
 for path,digest in inputs.items():
  if sha(canonical(path))!=digest:raise ValueError('Input SHA differs: '+path)
 if not test:require_image_bindings(plan,inputs)
 child=canonical(plan['child_allocation_path']);child_sha=plan['child_allocation_sha256']
 if not within(child,CONTROLS if test else ALLOCATIONS)or within(child,root)or inputs.get(str(child))!=child_sha:raise ValueError('Exact separate child allocation outside outputs')
 expected=[str(exe),str(WRITER),'write','--plan',plan.get('image_plan_path','TEST'),'--plan-sha256',plan.get('image_plan_sha256','TEST'),'--allocation',str(child),'--allocation-sha256',child_sha,'--arm','M1']
 if not test and(argv!=expected or canonical(argv[1])!=WRITER):raise ValueError('Exact candidate v2 writer argv; no extras')
 absolute=float(plan['absolute_seconds']);peers=plan['peer_reserved_bytes'];cap=plan['max_output_bytes'];logcap=plan['log_limit_bytes']
 if(not test and absolute!=130)or(test and not .3<=absolute<=3):raise ValueError('Unreviewed outer deadline')
 if type(peers)!=int or peers<0 or type(cap)!=int or cap<1 or type(logcap)!=int or not 1<=logcap<=MAX_LOG:raise ValueError('Explicit resource limits')
 if not test and(cap!=PACK_CAP or peers!=67108864 or plan.get('metadata_cap_bytes')!=METADATA_CAP or plan.get('inner_seconds')!=120):raise ValueError('Exact proposed image/metadata/peer/inner limits')
 ap=canonical(allocation_path)
 if not within(ap,CONTROLS if test else ALLOCATIONS)or within(ap,root)or sha(ap)!=allocation_sha:raise ValueError('Exact separate outer allocation')
 allocation=json.loads(ap.read_text())
 if allocation.get('allocated')is not True or allocation.get('plan_sha256')!=plan_sha or allocation.get('controller_sha256')!=sha(__file__)or canonical(allocation['approved_output_root'])!=root or not allocation.get('allocation_id'):raise ValueError('Root outer allocation/controller/plan binding')
 if allocation.get('approved_payload_roots')!=[]or allocation.get('max_output_bytes')!=cap or allocation.get('peer_reserved_bytes')!=peers or allocation.get('runtime_floor_bytes')!=BASE_FLOOR+peers:raise ValueError('Explicit aggregate/floor/peer roots allocation')
 if not test:
  if allocation.get('metadata_cap_bytes')!=METADATA_CAP or allocation.get('writer_source_sha256')!=WRITER_SHA or allocation.get('child_allocation_sha256')!=child_sha or allocation.get('data_unit_seal_sha256')!=PARENT_SEAL_SHA or allocation.get('source_unit_seal_sha256')!=SOURCE_SEAL_SHA:raise ValueError('Exact outer writer/child/source/data allocation')
  require_image_bindings(plan,inputs,allocation)
  ca=json.loads(child.read_text());wanted=dict(stage_authorized=True,candidate_contract_valid=True,source=SOURCE,arm='M1',plan_sha256=plan['image_plan_sha256'],writer_source_sha256=WRITER_SHA,allocation_cap_bytes=PACK_CAP,metadata_cap_bytes=METADATA_CAP,peer_reserved_bytes=peers,runtime_floor_bytes=BASE_FLOOR,inner_seconds=120,approved_output_root=str(root),controller_path=str(Path(__file__).absolute()),controller_source_sha256=sha(__file__))
  if not ca.get('allocation_id')or any(ca.get(k)!=v for k,v in wanted.items())or ca.get('compression_credits'):raise ValueError('Exact child allocation matches actual argv/writer/plan/controller')
 return plan,root,receipt,log,exe,cwd,allocation


def native():
 k=C.WinDLL('kernel32',use_last_error=True)
 class SECURITY(C.Structure):_fields_=[('nLength',W.DWORD),('lpSecurityDescriptor',C.c_void_p),('bInheritHandle',W.BOOL)]
 class STARTUP(C.Structure):_fields_=[('cb',W.DWORD),('lpReserved',W.LPWSTR),('lpDesktop',W.LPWSTR),('lpTitle',W.LPWSTR),('dwX',W.DWORD),('dwY',W.DWORD),('dwXSize',W.DWORD),('dwYSize',W.DWORD),('dwXCountChars',W.DWORD),('dwYCountChars',W.DWORD),('dwFillAttribute',W.DWORD),('dwFlags',W.DWORD),('wShowWindow',W.WORD),('cbReserved2',W.WORD),('lpReserved2',C.c_void_p),('hStdInput',W.HANDLE),('hStdOutput',W.HANDLE),('hStdError',W.HANDLE)]
 class PROCESS(C.Structure):_fields_=[('hProcess',W.HANDLE),('hThread',W.HANDLE),('dwProcessId',W.DWORD),('dwThreadId',W.DWORD)]
 S=C.c_size_t;Q=C.c_ulonglong;D=W.DWORD
 class BASIC(C.Structure):_fields_=[('PerProcessUserTimeLimit',C.c_longlong),('PerJobUserTimeLimit',C.c_longlong),('LimitFlags',D),('MinimumWorkingSetSize',S),('MaximumWorkingSetSize',S),('ActiveProcessLimit',D),('Affinity',S),('PriorityClass',D),('SchedulingClass',D)]
 class IO(C.Structure):_fields_=[(n,Q)for n in ('ReadOperationCount','WriteOperationCount','OtherOperationCount','ReadTransferCount','WriteTransferCount','OtherTransferCount')]
 class EXTENDED(C.Structure):_fields_=[('BasicLimitInformation',BASIC),('IoInfo',IO),('ProcessMemoryLimit',S),('JobMemoryLimit',S),('PeakProcessMemoryUsed',S),('PeakJobMemoryUsed',S)]
 class ACCOUNT(C.Structure):_fields_=[(n,C.c_longlong)for n in ('TotalUserTime','TotalKernelTime','ThisPeriodTotalUserTime','ThisPeriodKernelTime')]+[(n,D)for n in ('TotalPageFaultCount','TotalProcesses','ActiveProcesses','TotalTerminatedProcesses')]
 k.CreateJobObjectW.argtypes=[C.c_void_p,W.LPCWSTR];k.CreateJobObjectW.restype=W.HANDLE
 k.SetInformationJobObject.argtypes=[W.HANDLE,C.c_int,C.c_void_p,D];k.AssignProcessToJobObject.argtypes=[W.HANDLE,W.HANDLE];k.IsProcessInJob.argtypes=[W.HANDLE,W.HANDLE,C.POINTER(W.BOOL)];k.TerminateJobObject.argtypes=[W.HANDLE,W.UINT]
 k.CreateProcessW.argtypes=[W.LPCWSTR,W.LPWSTR,C.c_void_p,C.c_void_p,W.BOOL,D,C.c_void_p,W.LPCWSTR,C.POINTER(STARTUP),C.POINTER(PROCESS)];k.CreateProcessW.restype=W.BOOL
 k.ResumeThread.argtypes=[W.HANDLE];k.ResumeThread.restype=D;k.TerminateProcess.argtypes=[W.HANDLE,W.UINT]
 k.GetProcessTimes.argtypes=[W.HANDLE]+[C.POINTER(W.FILETIME)]*4;k.QueryFullProcessImageNameW.argtypes=[W.HANDLE,D,W.LPWSTR,C.POINTER(D)];k.GetExitCodeProcess.argtypes=[W.HANDLE,C.POINTER(D)];k.WaitForSingleObject.argtypes=[W.HANDLE,D];k.CloseHandle.argtypes=[W.HANDLE]
 k.QueryInformationJobObject.argtypes=[W.HANDLE,C.c_int,C.c_void_p,D,C.POINTER(D)]
 k.GetCompressedFileSizeW.argtypes=[W.LPCWSTR,C.POINTER(D)];k.GetCompressedFileSizeW.restype=D
 return k,STARTUP,PROCESS,EXTENDED,ACCOUNT

def run(plan,root,receipt,log,exe,cwd,allocation,plan_sha,allocation_sha):
 k,STARTUP,PROCESS,EXTENDED,ACCOUNT=native();D=W.DWORD;pi=PROCESS();job=None;assigned=False;resumed=False;job_empty=False;reader=None;sampler=None;hard=None;pipe_r=pipe_w=nullfd=logfd=receiptfd=None
 stop=threading.Event();sample_stop=threading.Event();failures=[];actions=[];log_bytes=0;log_seen=0;latest={'time':time.monotonic(),'free':None,'bytes':None,'error':None};deadline=float(plan['absolute_seconds']);floor=BASE_FLOOR+plan['peer_reserved_bytes'];origin=None;pin=None
 result={'schema':'owned-native-fresh1760-candidate-image-job','qualified':False,'allocation':allocation,'allocation_sha256':allocation_sha,'plan_sha256':plan_sha,'controller_sha256':sha(__file__),'argv':plan['argv'],'cwd':str(cwd),'approved_output_root':str(root),'runtime_floor_bytes':floor,'absolute_seconds':deadline,'log_limit_bytes':plan['log_limit_bytes'],'output_cap_bytes':plan['max_output_bytes'],'source_scope':'One exact native argv only; no image/guest acceptance inferred; partial outputs preserved','actions':actions,'errors':failures}
 result.update(approved_payload_roots=plan['approved_payload_roots'],aggregate_accounting='Sum per-file max(4096-rounded logical,native allocated where available), one exact candidate root including metadata, smalltracks, partials and image; no compression credit or source-image exclusion.',unsupported_unc_allocation={})
 result['inherited_python_cache_environment']=dict(dont_write_bytecode=bool(sys.dont_write_bytecode),PYTHONDONTWRITEBYTECODE=os.environ.get('PYTHONDONTWRITEBYTECODE'),effective_pycache_prefix=sys.pycache_prefix,inherited_without_override=True)
 result['image_reference']={key:plan.get(key)for key in('image_plan_path','image_plan_sha256','programme_admission_sha256','ELF_sha256','programme_sha256','consumer_sha256')}
 def checked(v):
  if not v:raise C.WinError(C.get_last_error())
  return v
 def fail(reason):failures.append(reason)
 def terminate(reason):
  actions.append({'termination_requested':reason,'elapsed':time.monotonic()-origin if origin else None})
  if job:checked(k.TerminateJobObject(job,124))
 def times():
  a,b,c,d=(W.FILETIME()for _ in range(4));checked(k.GetProcessTimes(pi.hProcess,C.byref(a),C.byref(b),C.byref(c),C.byref(d)));return a.dwLowDateTime+(a.dwHighDateTime<<32),b.dwLowDateTime+(b.dwHighDateTime<<32)
 def live_pin():
  created,exited=times()
  if pin and created!=pin['start_filetime']:raise RuntimeError('Retained creation identity changed')
  if exited:return False
  p=C.create_unicode_buffer(32768);n=D(32768);checked(k.QueryFullProcessImageNameW(pi.hProcess,0,p,C.byref(n)))
  if Path(p.value).resolve()!=exe:raise RuntimeError('Native executable path differs')
  return True
 def size_tree():
  total=0;metadata=0
  for owned in [root]+[Path(x)for x in plan['approved_payload_roots']]:
   if owned.is_symlink():raise RuntimeError('Output root alias refused')
   for p in owned.rglob('*'):
    try:
     if p.is_symlink():raise RuntimeError('Output alias refused')
     if p.is_file():
      logical=p.stat().st_size;rounded=(logical+4095)//4096*4096;high=D();C.set_last_error(0);low=k.GetCompressedFileSizeW(str(p),C.byref(high));error=C.get_last_error()
      if low==0xffffffff and error:
       if str(p).lower().startswith('\\\\wsl.localhost\\ubuntu-24.04\\')and error in (1,50,120):
        allocated=rounded;result['unsupported_unc_allocation'][str(p)]=error
       else:raise C.WinError(error)
      else:allocated=(high.value<<32)+low
      charged=max(rounded,allocated);total+=charged
      if not p.is_relative_to(root/'gdemu'):metadata+=charged
    except FileNotFoundError:continue
  if not plan.get('control_test')and metadata+FINAL_METADATA_HEADROOM>METADATA_CAP:raise RuntimeError('Image metadata16MiB cap/final reserve')
  return total
 def resources():
  while not sample_stop.is_set():
   try:latest.update(time=time.monotonic(),free=shutil.disk_usage('C:/').free,bytes=size_tree(),error=None);latest['time']=time.monotonic()
   except BaseException as e:latest.update(time=time.monotonic(),error=repr(e));return
   sample_stop.wait(.2)
 def log_reader():
  nonlocal log_bytes,log_seen
  try:
   while True:
    data=os.read(pipe_r,8192)
    if not data:break
    log_seen+=len(data);remaining=plan['log_limit_bytes']-log_bytes
    if remaining>0:
     chosen=data[:remaining];written=0
     while written<len(chosen):written+=os.write(logfd,chosen[written:])
     log_bytes+=written
    if len(data)>remaining:fail('Combined stdout/stderr log cap reached');terminate('log cap');break
  except BaseException as e:
   fail('Log collector: '+repr(e))
   try:terminate('log collector failure')
   except BaseException as x:fail('Log cleanup: '+repr(x))
 def hard_guard():
  # Captured job handle only; no filesystem, sampler, identity or logger waits.
  owned_job=job
  while not stop.wait(.01):
   if time.monotonic()-origin>=max(.05,deadline-.2):
    fail('Conservative absolute deadline');actions.append({'hardstop_requested_elapsed':time.monotonic()-origin})
    if not k.TerminateJobObject(owned_job,124):fail('Hardstop native termination failed')
    return
 try:
  admission=floor+(0 if plan.get('control_test')is True else plan['max_output_bytes'])
  if shutil.disk_usage('C:/').free<admission:raise RuntimeError('Fresh runtime floor plus allocated aggregate growth before output reservation')
  receiptfd=os.open(receipt,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);logfd=os.open(log,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
  initial=json.dumps(result,indent=2).encode();os.write(receiptfd,initial)
  if size_tree()+FINAL_METADATA_HEADROOM>plan['max_output_bytes']:raise RuntimeError('Output cap/final receipt reserve before process creation')
  job=checked(k.CreateJobObjectW(None,None));limits=EXTENDED();limits.BasicLimitInformation.LimitFlags=0x2000|0x8;limits.BasicLimitInformation.ActiveProcessLimit=1
  checked(k.SetInformationJobObject(job,9,C.byref(limits),C.sizeof(limits)))
  pipe_r,pipe_w=os.pipe();os.set_inheritable(pipe_w,True);nullfd=os.open(os.devnull,os.O_RDONLY);os.set_inheritable(nullfd,True)
  startup=STARTUP();startup.cb=C.sizeof(startup);startup.dwFlags=0x100;startup.hStdInput=msvcrt.get_osfhandle(nullfd);startup.hStdOutput=startup.hStdError=msvcrt.get_osfhandle(pipe_w)
  command=C.create_unicode_buffer(subprocess.list2cmdline(plan['argv']));origin=time.monotonic()
  checked(k.CreateProcessW(str(exe),command,None,None,True,0x4|0x08000000,None,str(cwd),C.byref(startup),C.byref(pi)))
  created,_=times();pin={'pid':int(pi.dwProcessId),'start_filetime':created,'path':str(exe)};result['identity']=pin
  if not live_pin():raise RuntimeError('Suspended process exited before identity pin')
  checked(k.AssignProcessToJobObject(job,pi.hProcess));member=W.BOOL();checked(k.IsProcessInJob(pi.hProcess,job,C.byref(member)))
  if not member.value:raise RuntimeError('Suspended process not in captured job')
  assigned=True;result['created_suspended_assigned_before_resume']=True
  os.close(pipe_w);pipe_w=None;os.close(nullfd);nullfd=None
  reader=threading.Thread(target=log_reader,daemon=True,name='bounded-writer-log');sampler=threading.Thread(target=resources,daemon=True,name='writer-resource-sampler');hard=threading.Thread(target=hard_guard,daemon=True,name='writer-hard-deadline')
  hard.start();reader.start();sampler.start()
  if k.ResumeThread(pi.hThread)==0xffffffff:raise C.WinError(C.get_last_error())
  resumed=True;actions.append({'resumed_elapsed':time.monotonic()-origin})
  while k.WaitForSingleObject(pi.hProcess,0)==258:
   if failures:raise RuntimeError('Asynchronous guard failure')
   snap=dict(latest)
   if snap['error'] or time.monotonic()-snap['time']>1:raise RuntimeError('Resource sample unavailable/stale: '+str(snap['error']))
   if snap['free'] is not None and (snap['free']<floor or snap['bytes']+FINAL_METADATA_HEADROOM>plan['max_output_bytes']):raise RuntimeError('Runtime disk floor/output cap/final receipt reserve')
   time.sleep(.025)
  result['normal_loop_exit']=True
 except BaseException as e:fail(type(e).__name__+': '+str(e))
 finally:
  if pi.hProcess:
   if k.WaitForSingleObject(pi.hProcess,0)==258:
    try:
     if assigned:terminate('finally fail-closed')
     else:checked(k.TerminateProcess(pi.hProcess,125));actions.append({'suspended_unassigned_terminated':True})
    except BaseException as e:fail('Termination cleanup: '+repr(e))
   # Keep hard guard and original handle until exit and WHOLE job empty proof.
   end=(origin+deadline) if origin else time.monotonic()+1
   while k.WaitForSingleObject(pi.hProcess,0)==258 and time.monotonic()<end:time.sleep(.01)
   signaled=k.WaitForSingleObject(pi.hProcess,0)==0;result['retained_handle_signaled']=signaled
   if signaled:
    try:
     code=D();checked(k.GetExitCodeProcess(pi.hProcess,C.byref(code)));created,exited=times()
     if not pin or created!=pin['start_filetime'] or not exited or code.value==259:raise RuntimeError('Exit identity/code not established')
     duration=(exited-created)/1e7;result.update(exit_code=code.value,actual_process_seconds=duration,postexit_path_query=False,retained_creation_match=True)
     if duration>deadline:fail('Actual process duration exceeded absolute bound')
     if code.value!=0:fail('Writer nonzero exit: '+str(code.value))
    except BaseException as e:fail('Exit proof: '+repr(e))
   else:fail('No retained exit proof within absolute bound')
  if job:
   try:
    until=(origin+deadline) if origin else time.monotonic()+1
    while True:
     accounting=ACCOUNT();checked(k.QueryInformationJobObject(job,1,C.byref(accounting),C.sizeof(accounting),None))
     if accounting.ActiveProcesses==0:job_empty=True;break
     if time.monotonic()>=until:raise RuntimeError('Whole private job not empty within absolute bound')
     time.sleep(.01)
   except BaseException as e:fail('Job empty proof: '+repr(e))
  result['whole_job_empty']=job_empty
  if job_empty:stop.set()
  if hard:
   hard.join(timeout=1)
   if hard.is_alive():fail('Hard guard still live; handles retained')
  sample_stop.set()
  if reader:
   reader.join(timeout=2)
   if reader.is_alive():fail('Log reader did not join')
  if sampler:sampler.join(timeout=.1)
  result.update(log_bytes=log_bytes,log_bytes_seen=log_seen,assigned=assigned,resumed=resumed)
  if job_empty and (hard is None or not hard.is_alive()) and (reader is None or not reader.is_alive()):
   for handle in (pi.hThread,pi.hProcess,job):
    if handle:k.CloseHandle(handle)
   result['handles_closed_after_empty']=True
  for fd in (pipe_w,nullfd,pipe_r):
   if fd is not None:
    try:os.close(fd)
    except OSError:pass
  if job_empty:
   try:
    result['final_free_bytes']=shutil.disk_usage('C:/').free;result['final_output_bytes']=size_tree()
    result['final_metadata_reserved_bytes']=FINAL_METADATA_HEADROOM
    if result['final_free_bytes']<floor or result['final_output_bytes']+FINAL_METADATA_HEADROOM>plan['max_output_bytes']:fail('Post-exit runtime floor/output cap/final receipt reserve')
   except BaseException as e:fail('Post-exit resource proof: '+repr(e))
  result['qualified']=bool(not failures and resumed and job_empty and result.get('retained_creation_match') and result.get('exit_code')==0)
  if receiptfd is not None:
   try:
    data=(json.dumps(result,indent=2)+'\n').encode();os.lseek(receiptfd,0,os.SEEK_SET);os.ftruncate(receiptfd,0);offset=0
    while offset<len(data):offset+=os.write(receiptfd,data[offset:])
   finally:os.close(receiptfd)
  if logfd is not None and not (reader and reader.is_alive()):os.close(logfd)
 return result

def main():
 if os.name!='nt':raise RuntimeError('Native Windows only')
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--plan',required=True);ap.add_argument('--plan-sha256',required=True);ap.add_argument('--allocation',required=True);ap.add_argument('--allocation-sha256',required=True);ap.add_argument('--execute',action='store_true');a=ap.parse_args()
 plan,root,receipt,log,exe,cwd,allocation=validate(a.plan,a.plan_sha256,a.allocation,a.allocation_sha256)
 if not a.execute:print(json.dumps({'prepared_only':True,'controller_sha256':sha(__file__),'plan_sha256':a.plan_sha256,'argv':plan['argv']}));return
 result=run(plan,root,receipt,log,exe,cwd,allocation,a.plan_sha256,a.allocation_sha256)
 print(json.dumps({'qualified':result['qualified'],'receipt':str(receipt),'exit_code':result.get('exit_code'),'errors':result['errors']}));raise SystemExit(0 if result['qualified'] else 1)
if __name__=='__main__':main()
