from pathlib import Path
import hashlib
L=Path(__file__).parent;p=L/'guard-resume-41inner-47absolute-resources-v4.py';assert hashlib.sha256(p.read_bytes()).hexdigest()=='c166c7a00d8b34082dd9c5cb4957bd66a4d10e54abbc3104aa316e11c70571e7';s=p.read_text()
needle=" verify();baseage=time.time()-(owner['start_filetime']/1e7-11644473600);t0=time.monotonic();close_sent=False"
helper=''' def collect_pinned_exit(reason):
  # A successful TerminateProcess request is asynchronous. Keep the ORIGINAL owned handle
  # until it signals, without any dead-PID path query and without extending47.5s.
  assert identity_pinned,'No initial live PID/path/start identity pin'
  while True:
   signal=k.WaitForSingleObject(h,0);now_age=baseage+time.monotonic()-t0
   if signal==0:
    code=W.DWORD();assert k.GetExitCodeProcess(h,C.byref(code))and code.value!=259,'Pinned handle lacks final exit code'
    a,b,c,d=(W.FILETIME()for _ in range(4));times_ok=bool(k.GetProcessTimes(h,C.byref(a),C.byref(b),C.byref(c),C.byref(d)))
    if times_ok:assert a.dwLowDateTime+(a.dwHighDateTime<<32)==owner['start_filetime'],'Retained creation time changed'
    observed_age=baseage+time.monotonic()-t0;assert observed_age<47.5,('Absolute process bound exceeded',observed_age)
    return dict(initial_live_identity_pinned=True,retained_handle_signaled=True,exit_code=code.value,postexit_times_available=times_ok,postexit_path_query=False,proof_reason=reason),observed_age
   assert signal==258,('Unexpected pinned handle wait status',signal)
   assert now_age<47.45,('Pinned process exit not witnessed before absolute margin',now_age)
   k.WaitForSingleObject(h,min(20,max(1,int((47.45-now_age)*1000))))

'''
assert needle in s;s=s.replace(needle,helper+needle)
old="assert k.TerminateProcess(h,73);actions.append(dict(action='exact_owned_absolute_termination',age=age,reason='47.5s absolute bound; WM_CLOSE grace exhausted'));assert k.WaitForSingleObject(h,300)==0,'Exact process did not exit within absolute guard grace';break"
new="assert k.TerminateProcess(h,73);actions.append(dict(action='exact_owned_absolute_termination',age=age,reason='47.5s absolute bound; WM_CLOSE grace exhausted'));break"
assert old in s;s=s.replace(old,new)
a=s.index(" assert identity_pinned and k.WaitForSingleObject(h,0)==0,'Retained pinned process handle must signal exit'");b=s.index('except BaseException as e:',a)
s=s[:a]+" closed_identity,exit_age=collect_pinned_exit('normal or absolute loop exit')\n"+s[b:]
old=""" if h and k.WaitForSingleObject(h,0)==258:
  if verify():
   assert k.TerminateProcess(h,74);assert k.WaitForSingleObject(h,300)==0;actions.append(dict(action='exact_owned_fail_closed_termination',reason=repr(e)))
 raise"""
new=""" try:
  if h:
   if k.WaitForSingleObject(h,0)==258 and verify():
    assert k.TerminateProcess(h,74);actions.append(dict(action='exact_owned_fail_closed_termination_requested',reason=repr(e),age=baseage+time.monotonic()-t0))
   if identity_pinned:
    closed_identity,exit_age=collect_pinned_exit('exception fail-closed cleanup')
    actions.append(dict(action='exact_owned_fail_closed_exit_witnessed',age=exit_age,exit_code=closed_identity['exit_code']))
 except BaseException as cleanup_error:
  actions.append(dict(action='exception_cleanup_exit_proof_failed',error=repr(cleanup_error)))
 raise"""
assert old in s;s=s.replace(old,new)
s=s.replace('Fail closed if sampler stale1s. WM_CLOSE at45s or resource boundary, terminate only same verified process at47.1s if needed; no gameplay memory writes.','Fail closed if sampler stale1s. WM_CLOSE at45s or resource boundary, terminate only same verified process at47.1s if needed. Asynchronous termination cleanup retains pinned handle until exit proof within47.5, preserving failed run status; no gameplay memory writes.')
compile(s,'supervisor-v5','exec');out=L/'guard-resume-41inner-47absolute-resources-v5.py';assert not out.exists();out.write_text(s);print(hashlib.sha256(out.read_bytes()).hexdigest())
