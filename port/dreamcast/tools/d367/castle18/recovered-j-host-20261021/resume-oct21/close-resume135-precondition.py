from pathlib import Path
import ctypes as C,ctypes.wintypes as W,json
p=Path(r'C:\Flycast-Evidence\re4-dreamcast\castle18-20261018\Test21\recovered-j-content-20261021\route-walk135');o=json.loads((p/'owned-process.json').read_text());k=C.WinDLL('kernel32',use_last_error=True);u=C.WinDLL('user32',use_last_error=True)
k.OpenProcess.argtypes=[W.DWORD,W.BOOL,W.DWORD];k.OpenProcess.restype=W.HANDLE;k.GetProcessTimes.argtypes=[W.HANDLE]+[C.POINTER(W.FILETIME)]*4;k.QueryFullProcessImageNameW.argtypes=[W.HANDLE,W.DWORD,W.LPWSTR,C.POINTER(W.DWORD)];u.GetWindowThreadProcessId.argtypes=[W.HWND,C.POINTER(W.DWORD)];u.GetClassNameW.argtypes=[W.HWND,W.LPWSTR,C.c_int];u.PostMessageW.argtypes=[W.HWND,W.UINT,W.WPARAM,W.LPARAM];u.PostMessageW.restype=W.BOOL
h=k.OpenProcess(0x1000,False,o['pid']);assert h;a,b,c,d=(W.FILETIME()for _ in range(4));assert k.GetProcessTimes(h,C.byref(a),C.byref(b),C.byref(c),C.byref(d));assert a.dwLowDateTime+(a.dwHighDateTime<<32)==o['start_filetime'];name=C.create_unicode_buffer(32768);n=W.DWORD(32768);assert k.QueryFullProcessImageNameW(h,0,name,C.byref(n));assert Path(name.value).resolve()==(p/'flycast.exe').resolve()==Path(o['path']).resolve();wins=[];CALL=C.WINFUNCTYPE(W.BOOL,W.HWND,W.LPARAM);u.EnumWindows.argtypes=[CALL,W.LPARAM]
@CALL
def cb(hwnd,_):
 pid=W.DWORD();u.GetWindowThreadProcessId(hwnd,C.byref(pid));c=C.create_unicode_buffer(256);u.GetClassNameW(hwnd,c,256)
 if pid.value==o['pid'] and c.value=='SDL_app':wins.append(int(hwnd))
 return True
assert u.EnumWindows(cb,0);assert len(wins)==1,wins;assert u.PostMessageW(wins[0],0x10,0,0)
(p/'owned-precondition-wm-close.json').write_text(json.dumps(dict(reason='Own135 selected incorrectly while original inventory was still open; no route inputs sent. Exact owned window closed to preserve current903/90 menu state for herb recovery.',owner=o,hwnd=wins[0],complete=False),indent=2)+'\n');print('Exact owned SDL WM_CLOSE posted')
