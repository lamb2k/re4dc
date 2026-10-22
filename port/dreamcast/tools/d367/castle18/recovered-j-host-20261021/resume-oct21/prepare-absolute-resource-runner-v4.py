from pathlib import Path
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18');p=L/'guard-resume-41inner-47absolute-resources-v4.py';assert not p.exists();s=(L/'guard-resume-41inner-47absolute-resources-v3.py').read_text()
s=s.replace("k.CloseHandle.argtypes=[W.HANDLE]", "k.CloseHandle.argtypes=[W.HANDLE];k.GetExitCodeProcess.argtypes=[W.HANDLE,C.POINTER(W.DWORD)]",1)
s=s.replace('rows=[];actions=[];owner=None;h=None;', 'rows=[];actions=[];owner=None;h=None;identity_pinned=False;closed_identity=None;',1)
a=s.index(' def verify():');b=s.index(' verify();baseage=',a)
s=s[:a]+''' def verify():
  global identity_pinned
  a,b,c,d=(W.FILETIME()for _ in range(4));assert k.GetProcessTimes(h,C.byref(a),C.byref(b),C.byref(c),C.byref(d)),'Live process times query failed';assert a.dwLowDateTime+(a.dwHighDateTime<<32)==owner['start_filetime'],'Live process start identity mismatch'
  if k.WaitForSingleObject(h,0)==0:assert identity_pinned,'Process exited before initial identity pin';return False
  p=C.create_unicode_buffer(32768);n=W.DWORD(32768);ok=k.QueryFullProcessImageNameW(h,0,p,C.byref(n))
  if not ok and k.WaitForSingleObject(h,0)==0 and identity_pinned:return False
  assert ok,'Live image path query failed';assert Path(p.value).resolve()==cap/'flycast.exe','Live executable identity mismatch';identity_pinned=True
  return k.WaitForSingleObject(h,0)==258
'''+s[b:]
s=s.replace("   verify();assert k.TerminateProcess(h,73);", "   if not verify():continue\n   assert k.TerminateProcess(h,73);",1)
s=s.replace('   verify();wins=[]', '   if not verify():continue\n   wins=[]',1)
s=s.replace("assert u.EnumWindows(cb,0);assert len(wins)==1,wins;assert u.PostMessageW(wins[0],0x10,0,0);close_sent=True;", "assert u.EnumWindows(cb,0)\n   if k.WaitForSingleObject(h,0)==0:continue\n   assert len(wins)==1,wins;posted=u.PostMessageW(wins[0],0x10,0,0)\n   if not posted and k.WaitForSingleObject(h,0)==0:continue\n   assert posted;close_sent=True;",1)
needle=" verify();exit_age=baseage+time.monotonic()-t0;assert exit_age<47.5,('Absolute process bound exceeded',exit_age)"
assert needle in s
s=s.replace(needle," assert identity_pinned and k.WaitForSingleObject(h,0)==0,'Retained pinned process handle must signal exit'\n code=W.DWORD();assert k.GetExitCodeProcess(h,C.byref(code))and code.value!=259,'Pinned process handle must provide final exit code'\n a,b,c,d=(W.FILETIME()for _ in range(4));times_ok=bool(k.GetProcessTimes(h,C.byref(a),C.byref(b),C.byref(c),C.byref(d)))\n if times_ok:assert a.dwLowDateTime+(a.dwHighDateTime<<32)==owner['start_filetime'],'Retained process creation time changed'\n closed_identity=dict(initial_live_identity_pinned=True,retained_handle_signaled=True,exit_code=code.value,postexit_times_available=times_ok,postexit_path_query=False)\n exit_age=baseage+time.monotonic()-t0;assert exit_age<47.5,('Absolute process bound exceeded',exit_age)",1)
s=s.replace("actions.append(dict(action='watcher_exception_fail_closed',error=repr(e)))", "import traceback\n actions.append(dict(action='watcher_exception_fail_closed',error=repr(e),traceback=traceback.format_exc()))",1)
s=s.replace("  verify();assert k.TerminateProcess(h,74);assert k.WaitForSingleObject(h,300)==0;actions.append(dict(action='exact_owned_fail_closed_termination',reason=repr(e)))", "  if verify():\n   assert k.TerminateProcess(h,74);assert k.WaitForSingleObject(h,300)==0;actions.append(dict(action='exact_owned_fail_closed_termination',reason=repr(e)))",1)
s=s.replace('owner=owner,process_exited=', 'owner=owner,closed_identity=closed_identity,process_exited=',1)
compile(s,str(p),'exec');p.write_text(s)
p=L/'run-resume-41inner-47absolute-resource-guard-v4.py';assert not p.exists();s=(L/'run-resume-41inner-47absolute-resource-guard-v3.py').read_text().replace('resources-v3.py','resources-v4.py');compile(s,str(p),'exec');p.write_text(s)
print('v4 postexit handle/exitcode receipt AST valid; no guest')
