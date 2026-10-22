#!/usr/bin/env python3
"""Read-only after-NTFS-compression identity/allocation receipt. Never compresses."""
import argparse,ctypes,json,os,shutil
from pathlib import Path
from mipmap_pair_plan import sha,local
from file_charge import WinPin,safe_path
def allocation(path):
 if os.name!='nt':raise OSError('actual Windows file allocation API required')
 k=ctypes.WinDLL('kernel32',use_last_error=True);fn=k.GetCompressedFileSizeW;fn.argtypes=[ctypes.c_wchar_p,ctypes.POINTER(ctypes.c_uint32)];fn.restype=ctypes.c_uint32;high=ctypes.c_uint32();ctypes.set_last_error(0);low=fn(str(path),ctypes.byref(high));err=ctypes.get_last_error()
 if low==0xffffffff and err:raise ctypes.WinError(err)
 return low+(high.value<<32)
def main():
 ap=argparse.ArgumentParser(description=__doc__)
 for n in ['image','readback','out']:ap.add_argument('--'+n,type=Path,required=True)
 a=ap.parse_args();r=json.loads(a.readback.read_text());assert r['result']=='PASS'and r['all1743_LBAs_sizes_hashes']is True and local(r['track']['path']).resolve()==a.image.resolve()
 safe_path(a.image,a.image.parent)
 with WinPin(a.image,r['track']['sha256'])as held:
  assert held.initial['logical_bytes']==r['track']['bytes']
  out={'result':'PASS','same_uncompressed_image_identity':True,'image':str(a.image),'sha256':r['track']['sha256'],'logical_bytes':held.initial['logical_bytes'],'native_file_identity':held.initial,'actual_Windows_GetCompressedFileSizeW_bytes':held.allocated(),'C_free_bytes':shutil.disk_usage(a.image.parent).free,'readback_path':str(a.readback),'all1743_readback_receipt_sha256':sha(a.readback),'scope':'Pinned read-only handle verified samefileID/singlelink/fullSHA/readback. Lossless identity/allocation only; root must reserve SECONDstage+peers from fresh actual native allocation and Cfree. No guest/performance acceptance.'}
 with a.out.open('x')as f:json.dump(out,f,indent=2);f.write('\n')
 print(json.dumps(out))
if __name__=='__main__':main()
