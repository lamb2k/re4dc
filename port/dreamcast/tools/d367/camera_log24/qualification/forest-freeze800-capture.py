"""Marker-triggered exact-owned framebuffer read; scoped stills, no runtime pose qualification."""
import ctypes,hashlib,importlib.util,json,os,pathlib,re,runpy,struct,subprocess,sys,threading,time
sys.path.insert(0,str(pathlib.Path(r'C:\Game Dev\Emulators\codex-lanes\world-emit23\current-stills')))
from force_limited import prepare_owned_config
BACKEND=pathlib.Path(r'C:\Game Dev\Emulators\codex-lanes\stat-bytes23\stat_owned_ram.py')
spec=importlib.util.spec_from_file_location('owned_ram',BACKEND);ram=importlib.util.module_from_spec(spec);spec.loader.exec_module(ram)
def digest(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def frame_bytes(data,offset,mod):
 if len(data)!=mod.VRAM_SIZE or offset%4 or offset+640*480*2>len(data):raise ValueError('frame extent invalid')
 out=bytearray(640*480*2)
 for word in range(0,len(out),4):
  pos=mod.map_32bit_vram(offset+word);out[word:word+4]=data[pos:pos+4]
 return bytes(out)
def marker(line,placed,expected):
 m=re.search(r'warp: frozen at tick (\d+)\b',line)
 if not m:return None
 if m[1]!='800' or placed!=expected:raise ValueError('wrong freeze tick or actual placed room')
 return {'line':line,'tick':800,'placed_room':placed}
class Tail:
 def __init__(self,path):self.path=path;self.at=0;self.pending=b''
 def poll(self):
  try:
   with self.path.open('rb') as f:
    if f.seek(0,2)<self.at:raise ValueError('capture log truncated')
    f.seek(self.at);data=f.read();self.at=f.tell()
  except FileNotFoundError:return []
  rows=(self.pending+data).split(b'\n');self.pending=rows.pop();return [r.decode('ascii','replace') for r in rows]
def main():
 harness=pathlib.Path(sys.argv[1]);expected=sys.argv[2];args=sys.argv[3:];cap=pathlib.Path(args[args.index('--cap')+1]);original=subprocess.Popen
 if original.__name__!='BoundedPopen' or os.environ.get('RE4DC_EMU')!='console' or os.environ.get('FP_NOLIMIT')!='0':raise RuntimeError('exact55 outer guard +explicit limited console required')
 stop=threading.Event();worker=None;guest=None;receipt={'scope':'Visible fixed authored scene only; no strict actor/viewport/presentation/full-runtime-pose proof','source_freeze_relation':'Freeze800 holds presentation buffers; no independently sampled complete runtime pose or rendered-frame identity is asserted.','backend_sha256':digest(BACKEND),'wrapper_sha256':digest(__file__),'expected_room':expected,'marker':None,'errors':[],'images':[]}
 def observe(proc):
  reader=None;tail=Tail(cap/'run-output.txt');placed=None;fb=None
  try:
   while not stop.is_set() and proc.poll() is None:
    for line in tail.poll():
     m=re.search(r'warp: placed room=([0-9a-f]{3}) pl=',line)
     if m:placed=m[1];receipt['placed_line']=line
     m=re.search(r'fb=([0-9a-f]+),([0-9a-f]+)',line)
     if m:fb=[int(x,16) for x in m.groups()];receipt['framebuffer_line']=line
     event=marker(line,placed,expected)
     if event:
      receipt['marker']=event;receipt['marker_observed_monotonic']=time.monotonic()
      if fb is None:raise ValueError('no source framebuffer addresses before freeze')
      cfg=(cap/'emu.cfg').read_text()
      if re.findall(r'(?mi)^aica\.LimitFPS\s*=\s*(.*?)\s*$',cfg)!=['yes']:raise ValueError('actual config not explicitly limited')
      receipt['actual_config_sha256']=digest(cap/'emu.cfg');pre=json.loads((cap/'limitfps-prelaunch.json').read_text());receipt['config_matches_prelaunch']=receipt['actual_config_sha256']==pre['actual_config_sha256']
      if not receipt['config_matches_prelaunch']:raise ValueError('config changed after prelaunch')
      module=importlib.util.spec_from_file_location('vram_decode',cap/'capture_ui_vram.py');mod=importlib.util.module_from_spec(module);module.loader.exec_module(mod);receipt['capture_backend_sha256']=digest(cap/'capture_ui_vram.py')
      offsets=[mod.framebuffer_offset(p) for p in fb];receipt['framebuffer_pointers']=[hex(p) for p in fb];receipt['offsets']=offsets
      reader=ram.OwnedRam(cap,proc.pid);receipt.update(pid=proc.pid,process_image=reader.image)
      log=(cap/'flycast.log').read_text(errors='replace');addresses=re.findall(r'VRAM64\(8 MB\) ([0-9A-Fa-f]+)',log)
      if not addresses:raise ValueError('owned VRAM base not initialized')
      address=int(addresses[-1],16);receipt['owned_VRAM64_address']=hex(address);samples=[]
      for index in range(2):
       if index:time.sleep(.15)
       start=time.monotonic();data=ctypes.create_string_buffer(mod.VRAM_SIZE);n=ctypes.c_size_t()
       if not reader.kernel.ReadProcessMemory(reader.handle,address,data,mod.VRAM_SIZE,ctypes.byref(n)) or n.value!=mod.VRAM_SIZE:raise OSError('incomplete exact-owned VRAM read')
       end=time.monotonic();samples.append(data.raw);receipt.setdefault('reads',[]).append({'index':index,'start_monotonic':start,'end_monotonic':end,'bytes':n.value,'seconds_after_marker':start-receipt['marker_observed_monotonic']})
      reader.close();reader=None
      from PIL import Image
      out=cap/'freeze800-frames';out.mkdir(exist_ok=False);raws=[[frame_bytes(data,off,mod) for off in offsets] for data in samples];receipt['buffer_stable_between_reads']=[raws[0][i]==raws[1][i] for i in range(2)]
      for sample,data in enumerate(samples):
       dest=out/('first' if sample==0 else 'second');dest.mkdir()
       for index,off in enumerate(offsets):
        raw=dest/('fb'+str(index)+'.rgb565');raw.write_bytes(raws[sample][index]);image=dest/('fb'+str(index)+'.png');Image.frombytes('RGB',(640,480),mod.decode_rgb565(data,off)).save(image);receipt['images'].append({'sample':sample,'buffer':index,'path':str(image.relative_to(cap)),'sha256':digest(image),'raw565_sha256':digest(raw),'dimensions':[640,480]})
      receipt['capture_completed']=True;return
    stop.wait(.02)
  except Exception as exc:receipt['errors'].append(repr(exc))
  finally:
   if reader:reader.close()
   receipt['actual_config_final_sha256']=digest(cap/'emu.cfg') if (cap/'emu.cfg').exists() else None
   (cap/'freeze800-capture.json').write_text(json.dumps(receipt,indent=2)+'\n')
 class CapturedPopen(original):
  def __init__(self,*a,**kw):
   nonlocal guest,worker
   cmd=a[0] if a else kw.get('args',[]);owned=isinstance(cmd,(list,tuple)) and pathlib.Path(str(cmd[0])).name.lower()=='flycast.exe'
   if owned:
    if guest is not None:raise RuntimeError('second owned child refused')
    if pathlib.Path(str(cmd[0])).resolve()!=cap.resolve()/'flycast.exe':raise RuntimeError('foreign capture child refused')
    prepare_owned_config(cap)
   super().__init__(*a,**kw)
   if owned:guest=self;worker=threading.Thread(target=observe,args=(self,),daemon=True);worker.start()
 subprocess.Popen=CapturedPopen
 try:sys.argv=[str(harness),*args];runpy.run_path(str(harness),run_name='__main__')
 finally:
  stop.set()
  if worker:worker.join(timeout=5)
if __name__=='__main__':main()
