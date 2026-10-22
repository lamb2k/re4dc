"""Conservative stage accounting; native credit only for pinned closed images."""
import ctypes,hashlib,json,os,stat
from pathlib import Path
from mipmap_pair_plan import local,sha
WOF=0x80000017
def roundup(n,unit=4096):return (n+unit-1)//unit*unit
def cluster_size(path):
 if os.name!='nt':return 4096
 k=ctypes.WinDLL('kernel32',use_last_error=True);D=ctypes.c_uint32;fn=k.GetDiskFreeSpaceW;fn.argtypes=[ctypes.c_wchar_p,ctypes.POINTER(D),ctypes.POINTER(D),ctypes.POINTER(D),ctypes.POINTER(D)];fn.restype=ctypes.c_int;s=D();b=D();free=D();total=D()
 if not fn(Path(path).absolute().anchor,ctypes.byref(s),ctypes.byref(b),ctypes.byref(free),ctypes.byref(total)):raise ctypes.WinError(ctypes.get_last_error())
 unit=s.value*b.value
 if not unit or unit&(unit-1):raise ValueError('invalid native allocation unit')
 return unit
def safe_path(path,root):
 path=Path(os.path.abspath(path));root=Path(os.path.abspath(root))
 if not path.is_relative_to(root):raise ValueError('charge path outside allocation root')
 for p in (path,*path.parents):
  if not p.exists()and not p.is_symlink():continue
  st=p.lstat()
  if stat.S_ISLNK(st.st_mode)or getattr(st,'st_reparse_tag',0)not in (0,WOF):raise ValueError('symlink/junction/unknown reparse charge refused')
  if getattr(st,'st_reparse_tag',0)==WOF and p!=path:raise ValueError('reparse parent refused')
 if not path.resolve().is_relative_to(root.resolve()):raise ValueError('resolved outside allocation')
 return path
def entries(root):
 root=safe_path(root,root)
 def walk(directory):
  with os.scandir(directory)as rows:
   for e in rows:
    p=safe_path(Path(e.path),root);s=p.lstat()
    if stat.S_ISDIR(s.st_mode):yield from walk(p)
    elif stat.S_ISREG(s.st_mode):yield p,s.st_size
    else:raise ValueError('nonregular allocation entry')
 yield from walk(root)
class WinPin:
 """Read-only handle denies writes/deletes for the entire credited interval."""
 def __init__(self,path,expected_sha):
  if os.name!='nt':raise OSError('native compressed credit requires Windows writer')
  self.path=Path(path);self.k=ctypes.WinDLL('kernel32',use_last_error=True);self.h=None
  D=ctypes.c_uint32
  class FT(ctypes.Structure):_fields_=[('lo',D),('hi',D)]
  class INFO(ctypes.Structure):_fields_=[('attrs',D),('created',FT),('accessed',FT),('written',FT),('volume',D),('sizehi',D),('sizelo',D),('links',D),('indexhi',D),('indexlo',D)]
  self.INFO=INFO;k=self.k;k.CreateFileW.argtypes=[ctypes.c_wchar_p,D,D,ctypes.c_void_p,D,D,ctypes.c_void_p];k.CreateFileW.restype=ctypes.c_void_p;k.CloseHandle.argtypes=[ctypes.c_void_p];k.CloseHandle.restype=ctypes.c_int;k.GetFileInformationByHandle.argtypes=[ctypes.c_void_p,ctypes.POINTER(INFO)];k.GetFileInformationByHandle.restype=ctypes.c_int;k.ReadFile.argtypes=[ctypes.c_void_p,ctypes.c_void_p,D,ctypes.POINTER(D),ctypes.c_void_p];k.ReadFile.restype=ctypes.c_int;k.GetCompressedFileSizeW.argtypes=[ctypes.c_wchar_p,ctypes.POINTER(D)];k.GetCompressedFileSizeW.restype=D
  h=k.CreateFileW(str(self.path),0x80000080,1,None,3,0x08000000,None)
  if h==ctypes.c_void_p(-1).value:raise ctypes.WinError(ctypes.get_last_error())
  self.h=h
  try:
   self.initial=self.identity();buf=ctypes.create_string_buffer(1048576);got=D();digest=hashlib.sha256();n=0
   while True:
    if not k.ReadFile(h,buf,len(buf),ctypes.byref(got),None):raise ctypes.WinError(ctypes.get_last_error())
    if not got.value:break
    digest.update(buf.raw[:got.value]);n+=got.value
   self.sha256=digest.hexdigest()
   if self.sha256!=expected_sha or n!=self.initial['logical_bytes']or self.identity()!=self.initial:raise ValueError('pinned full SHA/identity mismatch')
  except BaseException:self.close();raise
 def identity(self):
  r=self.INFO()
  if not self.k.GetFileInformationByHandle(self.h,ctypes.byref(r)):raise ctypes.WinError(ctypes.get_last_error())
  if r.links!=1 or r.attrs&0x10:raise ValueError('credit requires one link regular file')
  return {'volume_serial':r.volume,'file_index':r.indexlo+(r.indexhi<<32),'link_count':r.links,'logical_bytes':r.sizelo+(r.sizehi<<32),'creation_time':r.created.lo+(r.created.hi<<32)}
 def allocated(self):
  safe_path(self.path,self.path.parent)
  if self.identity()!=self.initial:raise ValueError('credited file identity/link changed')
  high=ctypes.c_uint32();ctypes.set_last_error(0);low=self.k.GetCompressedFileSizeW(str(self.path),ctypes.byref(high));err=ctypes.get_last_error()
  if low==0xffffffff and err:raise ctypes.WinError(err)
  return low+(high.value<<32)
 def close(self):
  if self.h is not None:self.k.CloseHandle(self.h);self.h=None
 def __enter__(self):return self
 def __exit__(self,*args):self.close()
class ChargeSession:
 def __init__(self,root,plan,plan_sha,credits,output,pin=WinPin):
  self.root=Path(root);self.pins={};self.cluster=cluster_size(root)
  try:
   for declared in credits:
    receipt_path=safe_path(local(declared['receipt_path']),self.root)
    if sha(receipt_path)!=declared['sha256']:raise ValueError('credit receipt changed')
    r=json.loads(receipt_path.read_text());path=safe_path(local(r['image']),self.root)
    if path==Path(output).absolute()or path in self.pins:raise ValueError('active output/duplicate credit')
    rbpath=safe_path(local(r['readback_path']),self.root)
    if sha(rbpath)!=r['all1743_readback_receipt_sha256']:raise ValueError('readback receipt changed')
    rb=json.loads(rbpath.read_text());arm=rb['arm']
    if not(r['result']=='PASS'and r['same_uncompressed_image_identity']is True and rb['result']=='PASS'and rb['all1743_LBAs_sizes_hashes']is True and rb['all15_programme_exact']is True and len(rb['files'])==1743 and rb['plan_sha256']==plan_sha and local(rb['track']['path']).absolute()==path and rb['track']['sha256']==r['sha256']==plan['arms'][arm]['predicted']['sha256']and rb['track']['bytes']==r['logical_bytes']==plan['track_bytes']):raise ValueError('credit lacks exact plan/fullreadback/image binding')
    held=pin(path,r['sha256']);self.pins[path]=held
    if held.initial!=r['native_file_identity']:raise ValueError('receipt fileID/links changed')
  except BaseException:self.close();raise
 def charge(self):
  total=0;seen=set()
  for p,n in entries(self.root):
   held=self.pins.get(p)
   if held:total+=roundup(held.allocated(),self.cluster);seen.add(p)
   else:total+=roundup(n,self.cluster)
  if seen!=set(self.pins):raise ValueError('credited path disappeared')
  return total
 def close(self):
  for held in self.pins.values():held.close()
  self.pins={}
 def __enter__(self):return self
 def __exit__(self,*args):self.close()
def conservative_charge(root):return sum(roundup(n,cluster_size(root))for p,n in entries(root))
def publish_no_replace(source,target):
 """Atomic no-overwrite, including POSIX where Path.rename would replace."""
 if os.name=='nt':
  k=ctypes.WinDLL('kernel32',use_last_error=True);k.MoveFileExW.argtypes=[ctypes.c_wchar_p,ctypes.c_wchar_p,ctypes.c_uint32];k.MoveFileExW.restype=ctypes.c_int
  if not k.MoveFileExW(str(source),str(target),8):raise ctypes.WinError(ctypes.get_last_error())
 else:
  # link is atomic exclusive target publication; never rename/replace fallback.
  os.link(source,target,follow_symlinks=False);Path(source).unlink()
