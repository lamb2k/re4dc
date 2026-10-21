#!/usr/bin/env python3
"""Run a prepared scene through existing fp_run; Windows only, no full disc stage."""
import argparse
import ctypes
from ctypes import wintypes as W
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base',required=True,help='frozen fullplay base with fixture slots; never modified')
    p.add_argument('--scene',required=True,help='directory prepared by bench.py scene')
    p.add_argument('--cap',required=True,help='new capture directory')
    p.add_argument('--syms',required=True,help='actual matching ELF log/head/stage physical addresses')
    p.add_argument('--seconds',type=int,default=50,choices=range(30,51))
    p.add_argument('--reservation',required=True,help='root-issued resource reservation receipt, JSON')
    a=p.parse_args()
    if os.name!='nt':raise SystemExit('Windows Python required by fp_run')
    scene=Path(a.scene); plan=json.loads((scene/'scene.json').read_text())
    if hashlib.sha256((scene/'warp.txt').read_bytes()).hexdigest()!=plan['warp']['sha256']:
        raise SystemExit('prepared warp changed')
    reservation=json.loads(Path(a.reservation).read_text())
    if reservation.get('owner')!='texture21-benchmark' or not reservation.get('guest_slot'):
        raise SystemExit('missing owned resource reservation')
    if time.time()>=reservation.get('expires_unix',0):raise SystemExit('expired resource reservation')
    if Path(a.cap).exists():raise SystemExit('capture directory already exists')
    # Existing harness uses isolated linked tracks, PID-scoped WM_KEY input only,
    # screenshots every five seconds and disk guards. capture.sh holds trace_lock.
    runner=Path(__file__).resolve().parents[1]/'fullplay/fp_run.py'
    cmd=[sys.executable,str(runner),'--base',a.base,'--warp',str(scene/'warp.txt'),
         '--cap',a.cap,'--syms',a.syms,'--seconds',str(a.seconds),'--period','5',
         '--name','texture21-'+plan['scene']]
    env=os.environ.copy();env['RE4DC_MAX_FLYCASTS']='16'
    # fp_run allows a reader drain after its requested limit. Independently cap
    # the actual owned guest at49 seconds using a pinned process handle and image
    # path; PID reuse or another lane's window can never be targeted.
    cap=Path(a.cap)
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.argtypes=[W.DWORD,W.BOOL,W.DWORD];kernel.OpenProcess.restype=W.HANDLE
    kernel.QueryFullProcessImageNameW.argtypes=[W.HANDLE,W.DWORD,W.LPWSTR,ctypes.POINTER(W.DWORD)]
    kernel.GetProcessTimes.argtypes=[W.HANDLE,ctypes.POINTER(W.FILETIME),ctypes.POINTER(W.FILETIME),ctypes.POINTER(W.FILETIME),ctypes.POINTER(W.FILETIME)]
    kernel.TerminateProcess.argtypes=[W.HANDLE,W.UINT];kernel.CloseHandle.argtypes=[W.HANDLE]
    started=time.time();runner_proc=subprocess.Popen(cmd,env=env)
    handle=None; guest_started=None; watchdog={'terminated_at_limit':False}
    try:
        while runner_proc.poll() is None:
            if handle is None and (cap/'flycast.pid').exists():
                pid=int((cap/'flycast.pid').read_text())
                probe=kernel.OpenProcess(0x1001,False,pid)
                if not probe:raise OSError('cannot pin owned guest process')
                image=ctypes.create_unicode_buffer(32768);count=W.DWORD(len(image))
                if not kernel.QueryFullProcessImageNameW(probe,0,image,ctypes.byref(count)):
                    kernel.CloseHandle(probe);raise OSError('cannot verify owned guest image')
                if Path(image.value).resolve()!= (cap/'flycast.exe').resolve():
                    kernel.CloseHandle(probe);raise RuntimeError('guest ownership mismatch')
                times=[W.FILETIME() for _ in range(4)]
                if not kernel.GetProcessTimes(probe,*[ctypes.byref(x) for x in times]):
                    kernel.CloseHandle(probe);raise OSError('cannot verify guest creation time')
                guest_started=((times[0].dwHighDateTime<<32)+times[0].dwLowDateTime)/1e7-11644473600
                if guest_started<started-1:
                    kernel.CloseHandle(probe);raise RuntimeError('stale guest pid file')
                handle=probe;watchdog['pid']=pid;watchdog['image']=image.value
            if handle is not None and time.time()-guest_started>=49:
                kernel.TerminateProcess(handle,0)
                watchdog['terminated_at_limit']=True
                watchdog['guest_seconds_at_termination']=time.time()-guest_started
                break
            if time.time()-started>120:raise RuntimeError('runner did not establish a bounded guest')
            time.sleep(.1)
        code=runner_proc.wait(timeout=15)
    finally:
        if handle is not None:
            kernel.TerminateProcess(handle,0)
            kernel.CloseHandle(handle)
        if runner_proc.poll() is None:
            runner_proc.terminate();runner_proc.wait(timeout=10)
        if cap.exists():(cap/'guest-watchdog.json').write_text(json.dumps(watchdog,indent=2)+'\n')
    if cap.exists():
        (cap/'benchmark-scene.json').write_text(json.dumps(plan,indent=2)+'\n')
        (cap/'resource-reservation.json').write_text(json.dumps(reservation,indent=2)+'\n')
        (cap/'benchmark-scope.txt').write_text('Flycast capture only. Validate actual source frame window and scene before comparing. Host screenshot times are not source frames. No physical Dreamcast acceptance.\n')
    raise SystemExit(code)

if __name__=='__main__':main()
