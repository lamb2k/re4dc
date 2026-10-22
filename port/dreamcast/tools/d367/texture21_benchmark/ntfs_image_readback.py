#!/usr/bin/env python3
"""Read-only after-NTFS-compression identity/allocation receipt. Never compresses."""
import argparse,ctypes,json,os,shutil
from pathlib import Path
from mipmap_pair_plan import sha,local
def allocation(path):
 if os.name!='nt':raise OSError('actual Windows file allocation API required')
 k=ctypes.WinDLL('kernel32',use_last_error=True);fn=k.GetCompressedFileSizeW;fn.argtypes=[ctypes.c_wchar_p,ctypes.POINTER(ctypes.c_uint32)];fn.restype=ctypes.c_uint32;high=ctypes.c_uint32();ctypes.set_last_error(0);low=fn(str(path),ctypes.byref(high));err=ctypes.get_last_error()
 if low==0xffffffff and err:raise ctypes.WinError(err)
 return low+(high.value<<32)
def main():
 ap=argparse.ArgumentParser(description=__doc__)
 for n in ['image','readback','out']:ap.add_argument('--'+n,type=Path,required=True)
 a=ap.parse_args();r=json.loads(a.readback.read_text());assert r['result']=='PASS'and r['all1743_LBAs_sizes_hashes']is True and local(r['track']['path']).resolve()==a.image.resolve()
 assert a.image.stat().st_size==r['track']['bytes']and sha(a.image)==r['track']['sha256']
 out={'result':'PASS','same_uncompressed_image_identity':True,'image':str(a.image),'sha256':r['track']['sha256'],'logical_bytes':a.image.stat().st_size,'actual_Windows_GetCompressedFileSizeW_bytes':allocation(a.image),'C_free_bytes':shutil.disk_usage(a.image.parent).free,'all1743_readback_receipt_sha256':sha(a.readback),'scope':'Lossless file identity/allocation only; no guest, no performance or gameplay acceptance. Root must freshly reserve remaining SECONDstage+peers above floor using actual free bytes.'}
 with a.out.open('x')as f:json.dump(out,f,indent=2);f.write('\n')
 print(json.dumps(out))
if __name__=='__main__':main()
