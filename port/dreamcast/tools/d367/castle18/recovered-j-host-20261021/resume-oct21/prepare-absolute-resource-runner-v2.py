from pathlib import Path
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18');p=L/'guard-resume-41inner-47absolute-resources-v2.py';assert not p.exists();s=(L/'guard-resume-41inner-47absolute-resources.py').read_text()
s=s.replace("age=baseage+time.monotonic()-t0;free=shutil.disk_usage(D).free;logical=sum(p.stat().st_size for p in cap.rglob('*')if p.is_file());rows.append(dict(monotonic=time.monotonic(),process_age_seconds=age,free=free,cap_logical_bytes=logical))", "age=baseage+time.monotonic()-t0")
needle="  if not close_sent and(age>=45 or free<18*1024**3+64*1024**2 or logical>60*1024**2):"
s=s.replace(needle,"  free=shutil.disk_usage(D).free;logical=0\n  for p in cap.rglob('*'):\n   try:\n    if p.is_file():logical+=p.stat().st_size\n   except FileNotFoundError:pass\n  age=baseage+time.monotonic()-t0;rows.append(dict(monotonic=time.monotonic(),process_age_seconds=age,free=free,cap_logical_bytes=logical))\n  if age>=47:continue\n"+needle,1)
s=s.replace('finally:\n if h:k.CloseHandle(h)', "except BaseException as e:\n actions.append(dict(action='watcher_exception_fail_closed',error=repr(e)))\n if h and k.WaitForSingleObject(h,0)==258:\n  verify();assert k.TerminateProcess(h,74);assert k.WaitForSingleObject(h,300)==0;actions.append(dict(action='exact_owned_fail_closed_termination',reason=repr(e)))\n raise\nfinally:\n process_exited=bool(h and k.WaitForSingleObject(h,0)==0)\n if h:k.CloseHandle(h)",1)
s=s.replace('owner=owner,runtime_floor=',"owner=owner,process_exited=process_exited,runtime_floor=",1)
compile(s,str(p),'exec');p.write_text(s)
p=L/'run-resume-41inner-47absolute-resource-guard-v2.py';assert not p.exists();s=(L/'run-resume-41inner-47absolute-resource-guard.py').read_text().replace('guard-resume-41inner-47absolute-resources.py','guard-resume-41inner-47absolute-resources-v2.py')
a=s.index('finally:\n');s=s[:a]+'''finally:
 watch.wait(timeout=85)
 guarded=json.loads((cap/'owned-resource-guard.json').read_text());assert guarded['process_exited'],'Guard has not verified owned process exit; do not claim closed'
 status(f'No guest is active; exact resource watcher verified run{n} process exit. Inspect its checkpoint, screenshots and guard receipt before continuing.')
 assert watch.returncode==0,('Guard failed closed; inspect preserved checkpoint',watch.returncode)
'''
compile(s,str(p),'exec');p.write_text(s)
print('v2 guard and runner AST valid, no guest')
