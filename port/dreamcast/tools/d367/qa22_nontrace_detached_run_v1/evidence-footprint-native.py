"""Own evidence: native AllocationSize/EndOfFile; exact immutable aliases excluded."""
import ctypes,importlib.util,os
from pathlib import Path
TRACKS=('track01.bin','track02.raw','track03.iso');_API=None

def native_extent(path,stat):
 global _API
 if os.name!='nt':return {'size':stat.st_size,'allocated':stat.st_blocks*512 if hasattr(stat,'st_blocks') else stat.st_size}
 if _API is None:
  source=Path(__file__).parent/'reference-hooks'/'native_reference_api.py';spec=importlib.util.spec_from_file_location('owned_extent_api',source);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);_API=module.WindowsApi()
 h=_API.k.CreateFileW(str(path),0x80,7,None,3,0x00200000,None)
 if h in (None,0,-1,(1<<(ctypes.sizeof(ctypes.c_void_p)*8))-1):
  code=ctypes.get_last_error()
  if code in (2,3):raise FileNotFoundError(path)
  raise ctypes.WinError(code)
 try:
  value=_API.stat(h)
  if value['attributes']&0x400 or value['deleted'] or value['directory'] or min(value['size'],value['allocated'])<0:raise RuntimeError('invalid/replaced evidence file extent')
  return {'size':value['size'],'allocated':value['allocated']}
 finally:_API.close(h)

def measure(root,disc,extent=native_extent):
 root=Path(root);disc=Path(disc);logical=allocated=charged=0;excluded=[];directories=4096 if root.exists() else 0
 for path in root.rglob('*'):
  try:
   if path.is_dir():directories+=4096;continue
   if not path.is_file():continue
   if path.is_symlink():raise RuntimeError('evidence file alias/reparse refused')
   st=path.stat();value=extent(path,st)
   if path.parent==root and path.name in TRACKS and path.samefile(disc/path.name):
    original=(disc/path.name).stat()
    if st.st_size!=original.st_size or value['size']!=original.st_size:raise RuntimeError('exact immutable track size changed')
    excluded.append({'path':str(path),'reference':str(disc/path.name),'logical_bytes':value['size'],'allocated_bytes':value['allocated'],'new_file_data_bytes':0,'identity':{'device':st.st_dev,'inode':st.st_ino,'links':st.st_nlink}});continue
   logical+=value['size'];allocated+=value['allocated'];charged+=max(value['size'],value['allocated'])
  except FileNotFoundError:continue # unchanged ordinary atomic-write/remove race
 return {'charged_logical_bytes':logical,'charged_allocated_bytes':allocated,'charged_directory_bytes':directories,'charged_bytes':charged+directories,'excluded_exact_track_references':excluded}
