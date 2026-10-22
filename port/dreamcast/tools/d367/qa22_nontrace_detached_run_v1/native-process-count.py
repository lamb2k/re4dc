"""Read-only Toolhelp32 basename count. Importing performs no native query."""
import ctypes as C,os
D=C.c_uint32;H=C.c_void_p
class Entry(C.Structure):
 _fields_=[('size',D),('usage',D),('pid',D),('heap',C.c_size_t),('module',D),('threads',D),('parent',D),('priority',C.c_int32),('flags',D),('exe',C.c_uint16*260)]
class QueryError(OSError):
 def __init__(self,operation,code):super().__init__(code,operation);self.winerror=code
class Native:
 def __init__(self):
  if os.name!='nt':raise RuntimeError('Windows native counter only')
  self.k=C.WinDLL('kernel32',use_last_error=True)
  for name,args,result in [('CreateToolhelp32Snapshot',[D,D],H),('Process32FirstW',[H,C.POINTER(Entry)],C.c_int),('Process32NextW',[H,C.POINTER(Entry)],C.c_int),('CloseHandle',[H],C.c_int)]:
   fn=getattr(self.k,name);fn.argtypes=args;fn.restype=result
 def __getattr__(self,name):return getattr(self.k,name)
 def error(self):return C.get_last_error()
def count_flycasts(api=None):
 api=api if api is not None else Native();handle=api.CreateToolhelp32Snapshot(2,0)
 invalid=(1<<(C.sizeof(H)*8))-1
 if handle in (None,0,-1,invalid):raise QueryError('CreateToolhelp32Snapshot',api.error())
 try:
  entry=Entry();entry.size=C.sizeof(Entry);count=0;seen=set()
  present=api.Process32FirstW(handle,C.byref(entry))
  if not present:
   code=api.error()
   if code==18:return 0
   raise QueryError('Process32FirstW',code)
  while True:
   if entry.pid in seen or len(seen)>=65536:raise RuntimeError('duplicate/excessive process snapshot')
   seen.add(entry.pid)
   name=bytes(entry.exe).decode('utf-16-le','surrogatepass').split('\0',1)[0]
   if name.casefold()=='flycast.exe':count+=1
   if not api.Process32NextW(handle,C.byref(entry)):
    code=api.error() # capture before CloseHandle can overwrite thread last-error
    if code!=18:raise QueryError('Process32NextW',code)
    return count
 finally:
  if not api.CloseHandle(handle):raise QueryError('CloseHandle(snapshot)',api.error())
