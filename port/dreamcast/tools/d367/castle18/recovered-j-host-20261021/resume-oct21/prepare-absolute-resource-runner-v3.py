from pathlib import Path
L=Path(r'C:\Game Dev\Emulators\codex-lanes\castle18');p=L/'guard-resume-41inner-47absolute-resources-v3.py';assert not p.exists();s=(L/'guard-resume-41inner-47absolute-resources-v2.py').read_text().replace('import sys,time,json,shutil,ctypes as C,ctypes.wintypes as W','import sys,time,json,shutil,ctypes as C,ctypes.wintypes as W,threading')
needle="verify();baseage=time.time()-(owner['start_filetime']/1e7-11644473600);t0=time.monotonic();close_sent=False"
s=s.replace(needle,needle+'''
 stop_sample=threading.Event();latest={'time':time.monotonic(),'free':None,'logical':None,'error':None}
 def sample_resources():
  while not stop_sample.is_set():
   try:
    free=shutil.disk_usage(D).free;logical=0
    for p in cap.rglob('*'):
     try:
      if p.is_file():logical+=p.stat().st_size
     except FileNotFoundError:pass
    latest.update(time=time.monotonic(),free=free,logical=logical,error=None)
   except BaseException as e:latest.update(time=time.monotonic(),error=repr(e));return
   stop_sample.wait(.2)
 threading.Thread(target=sample_resources,daemon=True,name='owned-cap-resource-sampler').start()''',1)
a=s.index('  free=shutil.disk_usage(D).free;logical=0',s.index('while k.WaitForSingleObject'))
b=s.index('  if age>=47:continue',a)
s=s[:a]+'''  snap=dict(latest);assert not snap['error'],('Resource sampler failed',snap['error']);assert time.monotonic()-snap['time']<1,'Resource sampler stalled; fail closed'
  if snap['free']is None:time.sleep(.025);continue
  free,logical=snap['free'],snap['logical'];age=baseage+time.monotonic()-t0;rows.append(dict(monotonic=time.monotonic(),process_age_seconds=age,free=free,cap_logical_bytes=logical,sample_monotonic=snap['time']))
'''+s[b:]
s=s.replace(" process_exited=bool(h and", " if 'stop_sample'in locals():stop_sample.set()\n process_exited=bool(h and",1)
s=s.replace('WM_CLOSE at45s or resource boundary, terminate only same verified process at47.1s if needed;','Filesystem sampler isolated on daemon thread; deadline loop never performs filesystem I/O. Fail closed if sampler stale1s. WM_CLOSE at45s or resource boundary, terminate only same verified process at47.1s if needed;')
compile(s,str(p),'exec');p.write_text(s)
p=L/'run-resume-41inner-47absolute-resource-guard-v3.py';assert not p.exists();s=(L/'run-resume-41inner-47absolute-resource-guard-v2.py').read_text().replace('resources-v2.py','resources-v3.py');compile(s,str(p),'exec');p.write_text(s)
print('v3 async filesystem sampler and pure deadline loop AST pass')
