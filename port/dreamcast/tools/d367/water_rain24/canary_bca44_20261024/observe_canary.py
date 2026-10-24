"""Rain-owned view observer; actual current ELF/DWARF scalars plus two read-only VRAM samples. No actor/present proof."""
import ctypes,hashlib,importlib.util,json,os,pathlib,re,runpy,struct,subprocess,sys,threading,time
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
from force_limited import prepare_owned_config
BACKEND=pathlib.Path(__file__).with_name('stat_owned_ram.py')
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
 if m[1]!='330' or placed!=expected:raise ValueError('wrong freeze tick or actual placed room')
 return {'line':line,'tick':330,'placed_room':placed}
class Tail:
 def __init__(self,path):self.path=path;self.at=0;self.pending=b''
 def poll(self):
  try:
   with self.path.open('rb') as f:
    if f.seek(0,2)<self.at:raise ValueError('capture log truncated')
    f.seek(self.at);data=f.read();self.at=f.tell()
  except FileNotFoundError:return []
  rows=(self.pending+data).split(b'\n');self.pending=rows.pop();return [r.decode('ascii','replace') for r in rows]
def source_sample(reader,layout):
    if layout['source']!='bca44d58a1fa0a51fd87ba94deba8cba925c8998' or layout['arm'] not in ['off','on']:
        raise ValueError('wrong frozen layout source/arm')
    symbols=layout['symbols'];types=layout['types'];g=types['GlobalWork']['members'];f=types['Filter06Work']['members']
    pg=reader.u32(symbols['pG']['address']);ram.ram_offset(pg)
    frame=reader.u32(pg+g['Frame_cnt']['offset']);room=struct.unpack('<H',reader.read_pointer(pg+g['room_id']['offset'],2))[0]
    blob=reader.read_pointer(symbols['flt06']['address'],types['Filter06Work']['bytes'])
    def off(k):return f[k]['offset']
    pointer,count=struct.unpack_from('<I',blob,off('p'))[0],struct.unpack_from('<I',blob,off('num'))[0]
    speed=list(struct.unpack_from('<fff',blob,off('spd')));rate=struct.unpack_from('<f',blob,off('rate'))[0];scale=struct.unpack_from('<f',blob,off('scale'))[0]
    if not all(__import__('math').isfinite(v) for v in speed+[rate,scale]):raise ValueError('nonfinite filter source state')
    if pointer:ram.ram_offset(pointer)
    col=list(blob[off('col'):off('col')+4]);cur=list(blob[off('cur'):off('cur')+4]);alpha_min=blob[off('alphaMin')]
    signature=room==0x10c and pointer!=0 and count==1100 and col==[170,170,170,80] and speed==[21,-250,0] and rate==1 and scale==1 and alpha_min==0 and cur[3]!=0
    native={k:reader.u32(symbols[k]['address']) for k in ['s_raindc_frames','s_raindc_sent','s_raindc_pending','s_raindc_queued_room','s_raindc_queued_frame'] if k in symbols}
    after=reader.u32(pg+g['Frame_cnt']['offset'])
    return {'sample_monotonic':time.monotonic(),'pG':hex(pg),'room':room,'source_frame_before':frame,'source_frame_after':after,'source_frame_stable_during_scalar_read':frame==after,'filter':{'p':hex(pointer),'num':count,'target':col,'current':cur,'speed':speed,'rate':rate,'scale':scale,'alphaMin':alpha_min},'retained_source_signature_matches':signature,'native':native,'binding_limit':'sampled live scalars, not original owner/record or completed render/actor/viewport/present proof'}

def classify_view(arm,states,logtext):
    signature=bool(states) and all(x['retained_source_signature_matches'] for x in states)
    counter=any(x['native']['s_raindc_frames']>0 and x['native']['s_raindc_sent']>0 for x in states)
    rows=[{'frame':int(f),'streaks':int(n),'sent':int(s)} for f,n,s in re.findall(r'rain dc: frame=(\d+) room=10c streaks=(\d+) sent=(\d+)',logtext)]
    native=counter and any(x['streaks']>0 and x['sent']>0 for x in rows)
    if not signature:label='UNEXERCISED: actual retained source signature absent'
    elif arm=='on' and not native:label='UNEXERCISED: source signature present, fresh room10c native emission evidence absent'
    elif arm=='off' and native:label='UNEXPECTED: native room10c emission in OFF control; no acceptance'
    elif arm=='off':label='source-signature OFF control observed; callback invocation not directly witnessed'
    else:label='source signature and fresh native room10c emission observed; limited view only'
    return {'source_signature_exercised':signature,'native_emission_counter_observed':counter,'fresh_room10c_native_log_rows':rows,'native_room10c_emission_observed':native,'feature_observation':label,'callback_ticket_direct_proof':False,'automatic_visual_or_lifecycle_pass':False}

def main():
 harness=pathlib.Path(sys.argv[1]);layout_path=pathlib.Path(sys.argv[2]);layout=json.loads(layout_path.read_text());expected=sys.argv[3];args=sys.argv[4:];cap=pathlib.Path(args[args.index('--cap')+1]);original=subprocess.Popen
 if original.__name__!='BoundedPopen' or os.environ.get('RE4DC_EMU')!='console' or os.environ.get('FP_NOLIMIT')!='0':raise RuntimeError('exact55 outer guard +explicit limited console required')
 stop=threading.Event();worker=None;guest=None;receipt={'scope':'Visible fixed authored scene only; no strict actor/viewport/presentation/full-runtime-pose proof','source_freeze_relation':'room-relative freeze330 is before completion; actual current global source frame sampled per read; no completed frame inferred','backend_sha256':digest(BACKEND),'wrapper_sha256':digest(__file__),'expected_room':expected,'layout_path':str(layout_path),'layout_sha256':digest(layout_path),'arm':layout['arm'],'marker':None,'errors':[],'images':[]}
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
      first_state=source_sample(reader,layout);receipt['actual_source_at_marker']=first_state
      if first_state['room']!=int(expected,16):raise ValueError('actual source room mismatch')
      log=(cap/'flycast.log').read_text(errors='replace');addresses=re.findall(r'VRAM64\(8 MB\) ([0-9A-Fa-f]+)',log)
      if not addresses:raise ValueError('owned VRAM base not initialized')
      address=int(addresses[-1],16);receipt['owned_VRAM64_address']=hex(address);samples=[]
      for index in range(2):
       if index:time.sleep(.15)
       before=source_sample(reader,layout)
       if before['room']!=int(expected,16):raise ValueError('source room changed before VRAM read')
       start=time.monotonic();data=ctypes.create_string_buffer(mod.VRAM_SIZE);n=ctypes.c_size_t()
       if not reader.kernel.ReadProcessMemory(reader.handle,address,data,mod.VRAM_SIZE,ctypes.byref(n)) or n.value!=mod.VRAM_SIZE:raise OSError('incomplete exact-owned VRAM read')
       end=time.monotonic();after=source_sample(reader,layout)
       if after['room']!=int(expected,16):raise ValueError('source room changed after VRAM read')
       samples.append(data.raw);receipt.setdefault('reads',[]).append({'index':index,'start_monotonic':start,'end_monotonic':end,'bytes':n.value,'seconds_after_marker':start-receipt['marker_observed_monotonic'],'actual_source_before':before,'actual_source_after':after})
      states=[x[k] for x in receipt['reads'] for k in ['actual_source_before','actual_source_after']]
      receipt.update(classify_view(layout['arm'],states,(cap/'run-output.txt').read_text(errors='replace')))
      receipt['source_frame_stable_between_reads']=len({x['source_frame_before'] for x in states}|{x['source_frame_after'] for x in states})==1
      receipt['callback_limit']='ticket can be transient; sampled state/cumulative counters do not prove all callbacks/cancels or original controller owner'
      reader.close();reader=None
      from PIL import Image
      out=cap/'rain-canary-frames';out.mkdir(exist_ok=False);raws=[[frame_bytes(data,off,mod) for off in offsets] for data in samples];receipt['buffer_stable_between_reads']=[raws[0][i]==raws[1][i] for i in range(2)]
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
   (cap/'rain-canary-capture.json').write_text(json.dumps(receipt,indent=2)+'\n')
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
