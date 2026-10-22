"""Charge new evidence; exact existing immutable track references add no file data."""
import os
from pathlib import Path
TRACKS=('track01.bin','track02.raw','track03.iso')
def allocated_bytes(p,st):
 if hasattr(st,'st_blocks'):return st.st_blocks*512
 if os.name=='nt':
  import ctypes
  k=ctypes.WinDLL('kernel32',use_last_error=True);k.GetCompressedFileSizeW.argtypes=[ctypes.c_wchar_p,ctypes.POINTER(ctypes.c_ulong)];k.GetCompressedFileSizeW.restype=ctypes.c_ulong
  high=ctypes.c_ulong();ctypes.set_last_error(0);low=k.GetCompressedFileSizeW(str(p),ctypes.byref(high));error=ctypes.get_last_error()
  if low==0xffffffff and error:
   if error in (2,3):raise FileNotFoundError(p)
   raise ctypes.WinError(error)
  return (high.value<<32)|low
 return st.st_size
def measure(root,disc):
 root=Path(root);disc=Path(disc);logical=0;allocated=0;excluded=[]
 for p in root.rglob('*'):
  try:
   if not p.is_file():continue
   st=p.stat();allocation=allocated_bytes(p,st)
   if p.parent==root and p.name in TRACKS and p.samefile(disc/p.name):
    original=(disc/p.name).stat();assert st.st_size==original.st_size
    excluded.append({'path':str(p),'reference':str(disc/p.name),'logical_bytes':st.st_size,'allocated_bytes':allocation,'new_file_data_bytes':0,'identity':{'device':st.st_dev,'inode':st.st_ino,'links':st.st_nlink}})
    continue
   logical+=st.st_size;allocated+=allocation
  except FileNotFoundError:continue # ordinary atomic-write/remove race
 return {'charged_logical_bytes':logical,'charged_allocated_bytes':allocated,'charged_bytes':max(logical,allocated),'excluded_exact_track_references':excluded}
