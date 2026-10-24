"""Tiny Windows read-only backend for an exact owned Flycast capture; no process starts/input/writes."""
from pathlib import Path
import ctypes, json, math, re, struct, time

def ram_offset(pointer):
    if not 0x0c000000 <= (pointer & 0x1fffffff) < 0x0d000000:
        raise ValueError('pointer outside Dreamcast 16MiB main RAM')
    return pointer & 0xffffff

def decode_model(blob):
    if len(blob) < 0x296: raise ValueError('short cModel sample')
    pos=list(struct.unpack_from('<fff',blob,0x94));frame=struct.unpack_from('<f',blob,0x290)[0]
    if not all(math.isfinite(x) for x in pos+[frame]): raise ValueError('nonfinite source state')
    stat=blob[0xfc:0x100]
    return {'pos':pos,'routine_bytes':list(stat),'native_stat':f'{int.from_bytes(stat,"little"):08x}',
            'canonical_stat':f'{int.from_bytes(stat,"big"):08x}','id':blob[0x100],'type':blob[0x101],
            'pMotion':hex(struct.unpack_from('<I',blob,0x1d8)[0]),'motState':struct.unpack_from('<H',blob,0x21a)[0],
            'frame':frame,'frameMax':struct.unpack_from('<H',blob,0x294)[0]}

class OwnedRam:
    """Open only PID+image named by this owned capture. Retry construction while guest initializes."""
    def __init__(self,evidence,pid):
        self.cap=Path(evidence);self.pid=int(pid);self.handle=None
        if int((self.cap/'flycast.pid').read_text()) != self.pid:raise ValueError('capture PID mismatch')
        k=ctypes.WinDLL('kernel32',use_last_error=True);self.kernel=k
        k.OpenProcess.argtypes=[ctypes.c_ulong,ctypes.c_int,ctypes.c_ulong];k.OpenProcess.restype=ctypes.c_void_p
        k.ReadProcessMemory.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t,ctypes.POINTER(ctypes.c_size_t)]
        k.CloseHandle.argtypes=[ctypes.c_void_p]
        k.QueryFullProcessImageNameW.argtypes=[ctypes.c_void_p,ctypes.c_ulong,ctypes.c_wchar_p,ctypes.POINTER(ctypes.c_ulong)]
        self.handle=k.OpenProcess(0x10|0x400,False,self.pid)
        if not self.handle:raise ctypes.WinError(ctypes.get_last_error())
        try:
            image=ctypes.create_unicode_buffer(32768);size=ctypes.c_ulong(len(image))
            if not k.QueryFullProcessImageNameW(self.handle,0,image,ctypes.byref(size)):raise ctypes.WinError(ctypes.get_last_error())
            if Path(image.value).resolve() != (self.cap/'flycast.exe').resolve():raise ValueError('owned image mismatch')
            self.image=image.value
            matches=re.findall(r'RAM\(16 MB\) ([0-9A-Fa-f]+)',(self.cap/'flycast.log').read_text(errors='replace'))
            if not matches:raise ValueError('RAM base not initialized')
            self.ram=int(matches[-1],16)
        except BaseException:
            self.close();raise
    def close(self):
        if self.handle:self.kernel.CloseHandle(self.handle);self.handle=None
    def __enter__(self):return self
    def __exit__(self,*unused):self.close()
    def read_offset(self,offset,count):
        if not self.handle or not 0<=offset<=0x1000000-count or count<1:raise ValueError('invalid owned read extent')
        data=ctypes.create_string_buffer(count);n=ctypes.c_size_t()
        if not self.kernel.ReadProcessMemory(self.handle,self.ram+offset,data,count,ctypes.byref(n)) or n.value!=count:
            raise OSError('incomplete read-only RAM sample')
        return data.raw
    def read_pointer(self,pointer,count):return self.read_offset(ram_offset(pointer),count)
    def u32(self,address):return struct.unpack('<I',self.read_pointer(address,4))[0]
    def player(self,ppl_symbol):
        pointer=self.u32(ppl_symbol)
        result=decode_model(self.read_pointer(pointer,0x298))
        result.update(pPL=hex(pointer),sample_monotonic=time.monotonic())
        return result

def capture_frames(evidence,output,state):
    """Use preserved RGB565 helper; output must be new. State/VRAM are asynchronous."""
    import importlib.util,shutil
    cap=Path(evidence);out=Path(output)
    fb=re.findall(r'fb=[0-9a-f]+,[0-9a-f]+',(cap/'run-output.txt').read_text(errors='replace'))
    if not fb:raise ValueError('framebuffer pointers not logged')
    spec=importlib.util.spec_from_file_location('owned_vram_capture',cap/'capture_ui_vram.py')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    out.mkdir(parents=True,exist_ok=False)
    for name in ['emu.cfg','flycast.log','flycast.pid']:shutil.copyfile(cap/name,out/name)
    (out/'boot.log').write_text(fb[-1]+'\n',encoding='utf-16')
    (out/'observed-state.json').write_text(json.dumps(state,indent=2)+'\n')
    return mod.capture(out,out/'frames')

if __name__=='__main__':
    # Pure synthetic field decoder check only. Never starts or accesses a guest.
    b=bytearray(0x298);struct.pack_into('<fff',b,0x94,1.25,-2.5,3.75);b[0xfc:0x100]=bytes([0,15,2,1])
    struct.pack_into('<I',b,0x1d8,0x8c123456);struct.pack_into('<H',b,0x21a,0x1234);struct.pack_into('<f',b,0x290,27.5);struct.pack_into('<H',b,0x294,60)
    s=decode_model(b)
    assert s['pos']==[1.25,-2.5,3.75] and s['routine_bytes']==[0,15,2,1]
    assert s['canonical_stat']=='000f0201' and s['native_stat']=='01020f00'
    assert s['pMotion']=='0x8c123456' and s['motState']==0x1234 and s['frame']==27.5 and s['frameMax']==60
    assert ram_offset(0xac123456)==0x123456
    for bad in [0,0x8bffffff,0x8d000000,0xa5000000]:
        try:ram_offset(bad)
        except ValueError:pass
        else:raise AssertionError('invalid pointer accepted')
    print('synthetic source-field decoder PASS; no guest opened')
