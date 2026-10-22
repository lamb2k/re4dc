from pathlib import Path
import ctypes,json,os
R=Path('C:/Flycast-Evidence/re4-dreamcast/qa21-combined-regression-20261021');k=ctypes.WinDLL('kernel32',use_last_error=True);k.GetCompressedFileSizeW.argtypes=[ctypes.c_wchar_p,ctypes.POINTER(ctypes.c_ulong)];k.GetCompressedFileSizeW.restype=ctypes.c_ulong
seen=set();allocated=0;logical=0;files=0
for p in R.rglob('*'):
 if not p.is_file():continue
 s=p.stat();identity=(s.st_dev,s.st_ino)
 if identity in seen:continue
 seen.add(identity);high=ctypes.c_ulong();low=k.GetCompressedFileSizeW(str(p),ctypes.byref(high));assert low!=0xffffffff or ctypes.get_last_error()==0
 allocated+=(high.value<<32)|low;logical+=s.st_size;files+=1
out={'scope':'Unique NTFS file identities deduplicated across own evidence hardlinks; physical storage allocation, plus WSL source/build counted separately','ntfs_unique_files':files,'ntfs_allocated_bytes':allocated,'ntfs_unique_logical_bytes':logical,'wsl_source_build_estimate_bytes':(127+98)*1024**2,'total_upper_estimate_bytes':allocated+(127+98)*1024**2,'reserved_bytes':int(2.3*1024**3)}
print(json.dumps(out))