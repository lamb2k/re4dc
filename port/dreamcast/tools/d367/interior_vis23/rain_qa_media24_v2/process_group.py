"""Bounded cleanup/reaping of one owned Linux stage session, including leader0."""
import ctypes,os,signal,time
from pathlib import Path

def enable_subreaper():
 libc=ctypes.CDLL(None,use_errno=True);previous=ctypes.c_int()
 if libc.prctl(37,ctypes.byref(previous),0,0,0)!=0:raise OSError(ctypes.get_errno(),'PR_GET_CHILD_SUBREAPER')
 if libc.prctl(36,1,0,0,0)!=0:raise OSError(ctypes.get_errno(),'PR_SET_CHILD_SUBREAPER')
 return previous.value

def members(pgid):
 rows=[]
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:
   fields=(p/'stat').read_text().rsplit(') ',1)[1].split()
   if int(fields[2])==pgid:rows.append({'pid':int(p.name),'state':fields[0],'ppid':int(fields[1]),'pgid':int(fields[2]),'session':int(fields[3])})
  except (OSError,ValueError,IndexError):continue
 return rows

def cleanup(child,previous_subreaper,seconds=3):
 old={s:signal.getsignal(s) for s in [signal.SIGTERM,signal.SIGHUP,signal.SIGINT]}
 for s in old:signal.signal(s,signal.SIG_IGN)
 report={'pgid':child.pid,'leader_returncode_before_cleanup':child.poll(),'reaped_descendants':[],'contained':False}
 deadline=time.monotonic()+seconds;sent=set()
 try:
  while True:
   child.poll();rows=members(child.pid);pids={r['pid'] for r in rows}
   if any(r['session']!=child.pid or r['ppid'] not in pids|{os.getpid()} for r in rows):raise RuntimeError('Unknown/nonowned stage group membership '+repr(rows))
   for r in rows:
    if r['pid']==child.pid or r['ppid']!=os.getpid():continue
    try:
     pid,status=os.waitpid(r['pid'],os.WNOHANG)
     if pid:report['reaped_descendants'].append({'pid':pid,'status':status})
    except ChildProcessError:pass
   rows=members(child.pid)
   if not rows:break
   now=time.monotonic();sig=signal.SIGTERM if now<deadline-1 else signal.SIGKILL
   if sig not in sent:
    try:os.killpg(child.pid,sig)
    except ProcessLookupError:pass
    sent.add(sig)
   if now>=deadline:raise RuntimeError('Owned stage descendants remain '+repr(rows))
   time.sleep(.02)
  child.wait(timeout=max(.01,deadline-time.monotonic()))
  report.update(contained=True,remaining=[],leader_returncode_after_cleanup=child.returncode)
  if not previous_subreaper:
   libc=ctypes.CDLL(None,use_errno=True)
   if libc.prctl(36,0,0,0,0)!=0:raise OSError(ctypes.get_errno(),'Restore process-local subreaper')
  return report
 finally:
  for s,h in old.items():signal.signal(s,h)
