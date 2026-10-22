"""Concrete Windows operations; importing this module performs NO native query.
Source-only candidate. Construct only from a separately reviewed/allocated parent.
"""
import ctypes as C
import hashlib
import ntpath
import os

D=C.c_uint32
Q=C.c_uint64
H=C.c_void_p


def canonical(path):
    text=str(path).replace('/', '\\')
    if text.startswith('\\\\?\\'):
        text=text[4:]
    if not ntpath.isabs(text) or ntpath.splitdrive(text)[0].lower()!='c:' or ntpath.normpath(text)!=text:
        raise ValueError('noncanonical C path: '+text)
    return ntpath.normcase(text)


class FileId(C.Structure):
    _fields_=[('volume',Q),('identifier',C.c_ubyte*16)]
class Basic(C.Structure):
    _fields_=[(n,C.c_int64) for n in ('creation','access','write','change')]+[('attributes',D)]
class Standard(C.Structure):
    _fields_=[('allocated',C.c_int64),('size',C.c_int64),('links',D),('deleted',C.c_ubyte),('directory',C.c_ubyte)]


class WindowsApi:
    def __init__(self):
        if os.name!='nt':raise RuntimeError('native collector Windows only')
        k=self.k=C.WinDLL('kernel32',use_last_error=True)
        signatures={
          'CreateFileW':([C.c_wchar_p,D,D,H,D,D,H],H),
          'GetFileInformationByHandleEx':([H,C.c_int,H,D],C.c_int),
          'GetFinalPathNameByHandleW':([H,C.c_wchar_p,D,D],D),
          'FindFirstFileNameW':([C.c_wchar_p,D,C.POINTER(D),C.c_wchar_p],H),
          'FindNextFileNameW':([H,C.POINTER(D),C.c_wchar_p],C.c_int),
          'FindClose':([H],C.c_int),'CloseHandle':([H],C.c_int),
          'ReadFile':([H,H,D,C.POINTER(D),H],C.c_int),
          'SetFilePointerEx':([H,C.c_int64,C.POINTER(C.c_int64),D],C.c_int),
          'SetFileInformationByHandle':([H,C.c_int,H,D],C.c_int),
          'GetCurrentProcess':([],H),
          'DuplicateHandle':([H,H,H,C.POINTER(H),D,C.c_int,D],C.c_int),
          'GetProcessId':([H],D),
          'GetProcessTimes':([H]+[C.POINTER(Q)]*4,C.c_int),
          'WaitForSingleObject':([H,D],D),
          'QueryFullProcessImageNameW':([H,D,C.c_wchar_p,C.POINTER(D)],C.c_int),
          'IsProcessInJob':([H,H,C.POINTER(C.c_int)],C.c_int),
          'QueryInformationJobObject':([H,C.c_int,H,D,C.POINTER(D)],C.c_int),
          'GetSystemTimeAsFileTime':([C.POINTER(Q)],None),
        }
        for name,(args,result) in signatures.items():
            f=getattr(k,name);f.argtypes=args;f.restype=result

    def checked(self,result):
        if not result:raise C.WinError(C.get_last_error())
        return result

    def close(self,handle):self.checked(self.k.CloseHandle(handle))

    def open_file(self,path,delete=False,directory=False):
        canonical(path)
        access=0x80 if directory else 0x80000000
        if delete:access|=0x10000
        # Deny file writers; a pre-existing incompatible writer makes open fail.
        # Delete sharing permits namespace changes; repeated full-name/identity
        # checks detect them. Directory ancestors do not share DELETE.
        share=3 if directory else 5
        flags=0x00200000 | (0x02000000 if directory else 0)
        h=self.k.CreateFileW(str(path),access,share,None,3,flags,None)
        if h in (None,0,C.c_void_p(-1).value):raise C.WinError(C.get_last_error())
        try:
            if self.stat(h)['attributes']&0x400:raise RuntimeError('reparse point refused: '+str(path))
            if self.final_path(h)!=canonical(path):raise RuntimeError('native path alias refused')
            return h
        except BaseException:self.close(h);raise

    def final_path(self,h):
        buf=C.create_unicode_buffer(32768);n=self.k.GetFinalPathNameByHandleW(h,buf,len(buf),0)
        if not n or n>=len(buf):raise RuntimeError('native final path unavailable/truncated')
        return canonical(buf.value)

    def stat(self,h):
        ident=FileId();basic=Basic();std=Standard()
        for kind,obj in ((18,ident),(0,basic),(1,std)):
            self.checked(self.k.GetFileInformationByHandleEx(h,kind,C.byref(obj),C.sizeof(obj)))
        return dict(volume=ident.volume,native_file_id='0x'+format(int.from_bytes(bytes(ident.identifier),'little'),'032x'),
                    size=std.size,allocated=std.allocated,links=std.links,deleted=bool(std.deleted),directory=bool(std.directory),
                    mtime_ns=(basic.write-116444736000000000)*100,attributes=basic.attributes)

    def names(self,path):
        # Fixed ample buffer and bounded count: MORE_DATA/any partial enumeration refuses.
        n=D(32768);buf=C.create_unicode_buffer(n.value);h=self.k.FindFirstFileNameW(str(path),0,C.byref(n),buf)
        if h in (None,0,C.c_void_p(-1).value):raise C.WinError(C.get_last_error())
        names=[]
        try:
            while True:
                if not buf.value.startswith('\\'):raise RuntimeError('invalid volume relative link name')
                names.append(canonical('C:'+buf.value))
                if len(names)>8:raise RuntimeError('unexpected image reference count')
                n=D(32768)
                if not self.k.FindNextFileNameW(h,C.byref(n),buf):
                    error=C.get_last_error()
                    if error==38:break # ERROR_HANDLE_EOF documented for enumeration end
                    raise C.WinError(error)
            if len(set(names))!=len(names):raise RuntimeError('duplicate native link name')
            return sorted(names)
        finally:self.checked(self.k.FindClose(h))

    def hash_file(self,h,guard):
        self.checked(self.k.SetFilePointerEx(h,0,None,0));digest=hashlib.sha256();total=0
        buf=C.create_string_buffer(8*1024*1024)
        while True:
            guard();read=D();self.checked(self.k.ReadFile(h,buf,len(buf),C.byref(read),None))
            if not read.value:break
            digest.update(buf.raw[:read.value]);total+=read.value
        guard();return {'sha256':digest.hexdigest(),'bytes':total}

    def delete_opened_link(self,h):
        # Handle was opened through the exact owned current alias with DELETE access.
        # Closing after disposition removes this alias; never a baseline pathname unlink.
        yes=C.c_int(1);self.checked(self.k.SetFileInformationByHandle(h,4,C.byref(yes),C.sizeof(yes)))
        self.close(h)

    def duplicate(self,source_process,remote_handle):
        result=H();self.checked(self.k.DuplicateHandle(source_process,remote_handle,self.k.GetCurrentProcess(),C.byref(result),0,False,2))
        return result.value

    def process(self,h,job,pinned=None,require_live=False):
        pid=self.checked(self.k.GetProcessId(h));times=[Q() for _ in range(4)]
        self.checked(self.k.GetProcessTimes(h,*[C.byref(t) for t in times]));created,exited,kernel,user=[t.value for t in times]
        status=self.k.WaitForSingleObject(h,0)
        if status not in (0,258):raise RuntimeError('native process wait failed: '+str(status))
        if not created or (exited and exited<created):raise RuntimeError('invalid retained process times')
        if pinned is not None and (pid!=pinned['pid'] or created!=pinned['start_filetime']):raise RuntimeError('retained process birth changed')
        if not exited and status==258:
            buf=C.create_unicode_buffer(32768);n=D(len(buf))
            try:self.checked(self.k.QueryFullProcessImageNameW(h,0,buf,C.byref(n)))
            except OSError:
                # Same505f pending/signaled distinction: only an already pinned
                # retained handle with a newly observed exit may skip path query.
                if pinned is None:raise
                retry=[Q() for _ in range(4)];self.checked(self.k.GetProcessTimes(h,*[C.byref(t) for t in retry]))
                if not retry[1].value:raise
                return self.process(h,job,pinned,require_live)
            path=canonical(buf.value)
            member=C.c_int();self.checked(self.k.IsProcessInJob(h,job,C.byref(member)))
            if not member.value:raise RuntimeError('retained process outside exact private job')
            if pinned is not None and path!=canonical(pinned['path']):raise RuntimeError('retained process path changed')
            phase='live'
        else:
            if pinned is None:raise RuntimeError('cannot establish new identity after process exit')
            path=canonical(pinned['path']);phase='exited' if status==0 and exited else 'pending'
        if require_live and phase!='live':raise RuntimeError('required exact process not live')
        return dict(pid=pid,start_filetime=created,path=path,exit_filetime=exited,wait_status=status,phase=phase,kernel_100ns=kernel,user_100ns=user)

    def job_pids(self,job):
        # JobObjectBasicProcessIdList: 2 DWORD then ULONG_PTR list. 128 bound.
        class List(C.Structure):_fields_=[('assigned',D),('count',D),('ids',C.c_size_t*128)]
        data=List();self.checked(self.k.QueryInformationJobObject(job,3,C.byref(data),C.sizeof(data),None))
        if data.count>128 or data.assigned!=data.count:raise RuntimeError('private job enumeration incomplete')
        return sorted(data.ids[:data.count])

    def now_filetime(self):
        result=Q();self.k.GetSystemTimeAsFileTime(C.byref(result));return result.value
