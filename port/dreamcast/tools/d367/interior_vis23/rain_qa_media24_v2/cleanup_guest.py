"""Only future allocated owned Windows child cleanup; no start/attach of new guest."""
from pathlib import Path
import ctypes,hashlib,json,os,sys
def null_handle_status(error):
 if error==87:return {'status':'PROCESS_GONE_OR_INVALID_PID','contained':True,'win_error':error}
 raise RuntimeError('Containment UNKNOWN: OpenProcess failed win_error='+str(error))

HERE=Path(__file__).resolve().parent
if not (__debug__ and sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode):raise RuntimeError('Use -I -S -B')
seal=HERE/'TOOLCHAIN-SEAL.json'
if os.environ.get('RAIN_QA_GUEST_ALLOCATED')!=hashlib.sha256(seal.read_bytes()).hexdigest():raise RuntimeError('Exact separate root guest allocation required')
for n,p in json.loads(seal.read_bytes())['members'].items():
 b=(HERE/n).read_bytes()
 if len(b)!=p['size'] or hashlib.sha256(b).hexdigest()!=p['sha256']:raise RuntimeError('Kit changed')
plan=json.loads((HERE/'PLAN.json').read_bytes());arm=sys.argv[1]
if arm not in ['off','on']:raise RuntimeError('arm')
cap=Path('C:'+plan['captures'][arm][6:].replace('/','\\'));pidfile=cap/'flycast.pid'
if not pidfile.exists():raise SystemExit(0)
pid=int(pidfile.read_text())
if not 0<pid<0xffffffff:raise RuntimeError('Invalid owned PID')
expected=(cap/'flycast.exe').resolve()
if hashlib.sha256(expected.read_bytes()).hexdigest()!=plan['tools']['console']['identity']['sha256']:raise RuntimeError('cleanup executable bytes changed')
k=ctypes.WinDLL('kernel32',use_last_error=True)
k.OpenProcess.argtypes=[ctypes.c_ulong,ctypes.c_int,ctypes.c_ulong];k.OpenProcess.restype=ctypes.c_void_p
k.QueryFullProcessImageNameW.argtypes=[ctypes.c_void_p,ctypes.c_ulong,ctypes.c_wchar_p,ctypes.POINTER(ctypes.c_ulong)];k.QueryFullProcessImageNameW.restype=ctypes.c_int
k.TerminateProcess.argtypes=[ctypes.c_void_p,ctypes.c_uint];k.TerminateProcess.restype=ctypes.c_int
k.CloseHandle.argtypes=[ctypes.c_void_p]
ctypes.set_last_error(0)
h=k.OpenProcess(0x1000|1,False,pid)
if not h:
 result=null_handle_status(ctypes.get_last_error());print(json.dumps(result));raise SystemExit(0)
try:
 b=ctypes.create_unicode_buffer(32768);n=ctypes.c_ulong(len(b))
 if not k.QueryFullProcessImageNameW(h,0,b,ctypes.byref(n)):raise OSError(ctypes.get_last_error())
 if Path(b.value).resolve()!=expected:raise RuntimeError('PID executable path mismatch; refusal')
 if not k.TerminateProcess(h,0):raise OSError(ctypes.get_last_error())
finally:k.CloseHandle(h)
