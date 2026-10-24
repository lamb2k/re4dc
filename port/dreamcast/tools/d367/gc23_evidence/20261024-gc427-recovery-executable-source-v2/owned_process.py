"""Exact owned Windows process instance; no process-name or global termination."""
from pathlib import Path
import hashlib
if not __debug__:raise RuntimeError('Optimized Python refused')
def identity(handle,pid):
 import ctypes
 from ctypes import wintypes as w
 api=ctypes.WinDLL('kernel32',use_last_error=True)
 api.GetProcessTimes.argtypes=[w.HANDLE,*([ctypes.POINTER(w.FILETIME)]*4)];api.GetProcessTimes.restype=w.BOOL
 api.QueryFullProcessImageNameW.argtypes=[w.HANDLE,w.DWORD,w.LPWSTR,ctypes.POINTER(w.DWORD)];api.QueryFullProcessImageNameW.restype=w.BOOL
 times=[w.FILETIME() for _ in range(4)];assert api.GetProcessTimes(handle,*map(ctypes.byref,times))
 buf=ctypes.create_unicode_buffer(32768);n=w.DWORD(len(buf));assert api.QueryFullProcessImageNameW(handle,0,buf,ctypes.byref(n))
 p=Path(buf.value).resolve();created=(times[0].dwHighDateTime<<32)|times[0].dwLowDateTime
 return dict(pid=pid,creation_FILETIME=created,path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
def matches(actual,expected):
 assert all(actual[k]==expected[k] for k in ['pid','creation_FILETIME','path','sha256']),'Owned process instance mismatch'
def terminate(expected):
 import ctypes
 from ctypes import wintypes as w
 api=ctypes.WinDLL('kernel32',use_last_error=True)
 api.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];api.OpenProcess.restype=w.HANDLE
 api.TerminateProcess.argtypes=[w.HANDLE,w.UINT];api.TerminateProcess.restype=w.BOOL
 api.GetExitCodeProcess.argtypes=[w.HANDLE,ctypes.POINTER(w.DWORD)];api.GetExitCodeProcess.restype=w.BOOL
 api.WaitForSingleObject.argtypes=[w.HANDLE,w.DWORD];api.WaitForSingleObject.restype=w.DWORD
 api.CloseHandle.argtypes=[w.HANDLE];api.CloseHandle.restype=w.BOOL
 handle=api.OpenProcess(0x1000|1|0x100000,False,expected['pid']) # QUERY_LIMITED|TERMINATE|SYNCHRONIZE
 if not handle:
  err=ctypes.get_last_error()
  if err==87:return dict(already_exited=True)
  raise OSError(err,'Owned OpenProcess refused')
 try:
  status=w.DWORD();assert api.GetExitCodeProcess(handle,ctypes.byref(status))
  if status.value!=259:return dict(already_exited=True)
  actual=identity(handle,expected['pid']);matches(actual,expected);assert api.TerminateProcess(handle,97)
  wait=api.WaitForSingleObject(handle,3000);assert wait==0,('Owned exit not observed',wait)
  assert api.GetExitCodeProcess(handle,ctypes.byref(status)) and status.value!=259,'Owned exit status unknown'
  return dict(terminated_exact_instance=True,exit_observed=True,exit_code=status.value,wait_ms_cap=3000,identity=actual)
 finally:api.CloseHandle(handle)
