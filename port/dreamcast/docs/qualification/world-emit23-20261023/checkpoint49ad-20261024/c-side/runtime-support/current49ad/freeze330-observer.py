"""Read-only freeze330 diagnostic. Always refuses strict pixels: completed bindings absent."""
import argparse,ctypes,hashlib,importlib.util,json,math,pathlib,re,struct,time
SOURCE='49ad20f9932d638ddb7becf5db6f86b92e0a76a2'
VRAM_BYTES=8*1024*1024
class Refused(ValueError):pass
def require(ok,why):
 if not ok:raise Refused(why)
def digest(b):return hashlib.sha256(b).hexdigest()
def u32(b,o=0):return struct.unpack_from('<I',b,o)[0]
def s32(b,o=0):return struct.unpack_from('<i',b,o)[0]
def floats(b,o,n):
 v=list(struct.unpack_from('<'+'f'*n,b,o));require(all(math.isfinite(x) for x in v),'nonfinite floats');return v
def load_module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def coherent_read(read,address,size,attempts=3):
 for _ in range(attempts):
  first=read(address,4);blob=read(address,size);last=read(address,4)
  if u32(first)==u32(blob)==u32(last) and not u32(first)&1:return blob
 raise Refused('torn/odd completed snapshot after bounded retries')
def source_decode(b):
 require(len(b)==112,'source ABI');return {'tick':u32(b),'system':u32(b,4),'stop':u32(b,8),'room':u32(b,12),'player':floats(b,48,6),'camera':floats(b,72,8),'motion_frame':floats(b,104,1)[0],'motion_state':u32(b,108),'sha256':digest(b)}
def profile_decode(b):
 require(len(b)==428 and not u32(b)&1,'profile ABI/sequence');return {'sequence':u32(b),'frame':u32(b,4),'source':source_decode(b[316:428]),'clock_valid':u32(b,8),'sha256':digest(b)}
def frame_decode(b):
 require(len(b)==192 and not u32(b)&1,'completed frame ABI/sequence');return {'sequence':u32(b),'frame':u32(b,4),'queue_drops':u32(b,156),'present_requested':u32(b,184),'aborted':u32(b,188),'aggregate_work_sha256':digest(b[8:128]),'sha256':digest(b)}
def pvr_decode(b):
 require(len(b)==520,'PVR ABI');view=s32(b,44);require(view in (0,1),'PVR view_target')
 buffers=[{'offset':u32(b,312+i*8),'bytes':u32(b,316+i*8)} for i in range(2)]
 for fb in buffers:require(fb['offset']%4==0 and 640*480*2<=fb['bytes']<=VRAM_BYTES and 0<=fb['offset']<=VRAM_BYTES-fb['bytes'],'VRAM frame extent')
 return {'valid':s32(b),'view_target':view,'ta_busy':s32(b,76),'render_busy':s32(b,80),'render_completed':s32(b,84),'buffers':buffers,'width':s32(b,332),'height':s32(b,336),'fsaa':s32(b,468),'frame_count':u32(b,452),'vblank_count_observation_only':u32(b,448),'clip':[u32(b,o) for o in (356,360,364,368)],'sha256':digest(b)}
def actor_roster(read,manager_blob,max_actors=512):
 require(len(manager_blob)==56,'manager ABI');array,n,stride,head=(u32(manager_blob,o) for o in (4,8,12,20))
 require(n<=4096 and (not n or 800<=stride<=16384),'manager bounds')
 require(not u32(manager_blob,28),'pushed manager storage not qualified')
 def offset(pointer,count):
  physical=pointer&0x1fffffff;require(0x0c000000<=physical and physical+count<=0x0d000000,'actor pointer outside RAM');return pointer
 if n:offset(array,n*stride)
 seen=set();rows=[]
 while head:
  require(head not in seen and len(seen)<min(n,max_actors),'cyclic/overlong actor roster');seen.add(head)
  require(array<=head<array+n*stride and (head-array)%stride==0,'actor not exact manager slot')
  blob=read(head,800);require(u32(blob,4)&0x601,'non-live roster node')
  rows.append({'address':head,'slot':(head-array)//stride,'flags':u32(blob,4),'serial':u32(blob,248),'routine_bytes':list(blob[252:256]),'id':blob[256],'type':blob[257],'parts':blob[258],'pos':floats(blob,148,3),'angle':floats(blob,160,3),'scale':floats(blob,172,3),'matrix_sha256':digest(blob[12:60]),'raw_current_model_sha256':digest(blob)})
  head=u32(blob,8)
 return {'array':array,'nArray':n,'stride':stride,'actors':rows,'scope':'LIVE roster at freeze, not completed-render actors'}
def package_inventory(blob):
 require(len(blob)==0x18800,'entry array ABI');rows=[]
 for slot in range(len(blob)//224):
  e=blob[slot*224:(slot+1)*224]
  if not e[76]:continue
  rows.append({'slot':slot,'key':[u32(e,64),u32(e,68)],'pin_frame':u32(e,72),'upload_complete':e[45],'vram_bytes':u32(e,52),'texture_table':u32(e,24),'package_header':u32(e,20),'package_sha256':digest(e[:64])})
 return {'entries':rows,'sha256':digest(blob),'scope':'LIVE retained pool, not completed-frame owner table'}
def read_vram_same_handle(owned,address):
 require(owned.handle is not None,'closed owned handle');buffer=ctypes.create_string_buffer(VRAM_BYTES);count=ctypes.c_size_t()
 ok=owned.kernel.ReadProcessMemory(owned.handle,address,buffer,VRAM_BYTES,ctypes.byref(count))
 require(ok and count.value==VRAM_BYTES,'incomplete same-handle VRAM read');return buffer.raw

def snapshot(owned,layout):
 syms=layout['symbols'];read=owned.read_pointer
 def raw(k):s=syms[k];return read(s['address'],s['size'])
 def scalar(k,signed=False):b=raw(k);return s32(b) if signed else (u32(b) if len(b)==4 else b[0])
 profile=profile_decode(coherent_read(read,syms['profile']['address'],428));completed=frame_decode(coherent_read(read,syms['completed']['address'],192))
 pg=scalar('pG');glob=read(pg,34432);types=layout['types'];g=types['GlobalWork']['members'];cam=g['Cam']+types['Camera']['members']['param']
 return {'profile':profile,'completed':completed,'source_begin':source_decode(raw('source_begin')),'global_tick':u32(glob,g['Frame_cnt']),'live_camera':floats(glob,cam,8),'global_state_sha256':digest(glob),'pvr':pvr_decode(raw('pvr')),'viewport':floats(raw('viewport'),0,6),'projection':floats(raw('projection'),0,7),'pipeline':{k:scalar(k,signed=(k=='pending')) for k in ['pending','flip','manual','steady_q','steady_watch','submitted','resolved','failures','ui_frame','frame_ready','stream_scene','loads']},'EmMgr':actor_roster(read,raw('EmMgr')),'ObjMgr':actor_roster(read,raw('ObjMgr')),'packages':package_inventory(raw('entries'))}
def stable_key(s):
 # Vblank count advances while a held picture is stable; it is not source phase.
 x=json.loads(json.dumps(s));x['pvr'].pop('vblank_count_observation_only');x['pvr'].pop('sha256');return x

def assess(a,b,layout,room,marker_tick):
 reasons=[]
 def check(ok,why):
  if not ok:reasons.append(why)
 check(marker_tick==330 and a['global_tick']==b['global_tick']==330,'exact freeze/global tick330 missing')
 check(stable_key(a)==stable_key(b),'source/render/present/upload/roster changed across VRAM read')
 for s in (a,b):
  p=s['profile'];f=s['completed'];q=s['pipeline'];v=s['pvr']
  check(p['frame']==f['frame'],'completed profile/UI frame mismatch')
  check(p['source']['room']==room,'completed source room mismatch')
  check(p['source']['tick']==328 and s['source_begin']['tick']==329,'source call-order relationship not matched')
  check(q['ui_frame']==f['frame']+1,'expected next UI frame not matched')
  check(f['present_requested']==1 and not f['aborted'] and not f['queue_drops'],'completed intent/abort/drop refusal')
  check(v['valid']==1 and not v['render_busy'] and not v['render_completed'] and q['pending']==-1 and not q['flip'],'KOS completion/flip remains pending')
  check(not q['steady_q'] and not q['steady_watch'] and not q['failures'],'steady queue/watch or presentation failure')
  check(v['width']==640 and v['height']==480 and not v['fsaa'],'RGB565 backend extent unsupported')
  check(all(e['upload_complete']==1 for e in s['packages']['entries']),'live package upload incomplete')
 missing=list(layout['unproven_completed_bindings']);require(missing,'manifest cannot erase unproven bindings')
 return {'readonly_snapshot_consistent':not reasons,'snapshot_refusals':reasons,'strict_pixel_qualified':False,'strict_pixel_refusals':missing,'scope':'phase-observed/asynchronous diagnostic only, never a strict pixel gate'}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--cap',required=True);ap.add_argument('--pid',required=True,type=int);ap.add_argument('--layout',required=True);ap.add_argument('--binding',required=True);ap.add_argument('--room',required=True,type=lambda x:int(x,0));ap.add_argument('--output',required=True);ap.add_argument('--owned-backend',required=True);a=ap.parse_args();cap=pathlib.Path(a.cap);out=pathlib.Path(a.output);require(not out.exists(),'existing output refused')
 layout=json.loads(pathlib.Path(a.layout).read_text());binding=json.loads(pathlib.Path(a.binding).read_text());require(layout['source']==SOURCE==binding['source'],'source mismatch');require(layout['elf_sha256']==binding['elf_sha256'],'exact ELF layout mismatch');require(binding['cap']==str(cap.resolve()) and binding['pid']==a.pid,'owned cap/PID binding mismatch');require(digest((cap/'flycast.exe').read_bytes())==binding['executable_sha256'],'owned executable hash mismatch')
 require(digest(pathlib.Path(a.layout).read_bytes())==binding['layout_sha256'],'layout receipt mismatch')
 deadline=float(binding['guest_deadline_monotonic']);require(time.monotonic()<deadline<=time.monotonic()+55,'guest bound unavailable/expired')
 text=(cap/'run-output.txt').read_text(errors='replace');markers=re.findall(r'warp: frozen at tick (\d+)',text);require(markers==['330'],'exact one freeze330 marker required');require('[LOG OVERRUN' not in text,'log overrun');require('rend.EmulateFramebuffer=yes' in (cap/'emu.cfg').read_text(),'framebuffer emulation required')
 require(digest(pathlib.Path(a.owned_backend).read_bytes())==layout['backends']['owned']['sha256'],'owned backend source pin')
 require(digest((cap/'capture_ui_vram.py').read_bytes())==binding['decoder_sha256']==layout['backends']['decoder']['sha256'],'decoder source binding')
 backend=load_module('owned_ram',a.owned_backend);decoder=load_module('rgb565_decoder',cap/'capture_ui_vram.py')
 with backend.OwnedRam(cap,a.pid) as owned:
  # Keep this exact image-validated handle for every RAM and VRAM read. No second OpenProcess.
  original_read=owned.read_pointer
  def bounded_read(address,count):
   require(time.monotonic()<deadline,'exact guest read deadline reached');return original_read(address,count)
  owned.read_pointer=bounded_read
  addresses=re.findall(r'VRAM64\(8 MB\) ([0-9A-Fa-f]+)',(cap/'flycast.log').read_text(errors='replace'));require(bool(addresses),'VRAM base absent')
  vram_address=int(addresses[-1],16);start=time.monotonic();before=snapshot(owned,layout);require(time.monotonic()<deadline,'guest deadline');vram=read_vram_same_handle(owned,vram_address);after=snapshot(owned,layout);verdict=assess(before,after,layout,a.room,330)
  require(time.monotonic()<deadline,'guest deadline before second VRAM read');again=read_vram_same_handle(owned,vram_address);final=snapshot(owned,layout)
  from PIL import Image
  out.mkdir(parents=True,exist_ok=False);frames=[]
  for i,fb in enumerate(after['pvr']['buffers']):
   offset=fb['offset'];rgb=decoder.decode_rgb565(vram,offset);rgb2=decoder.decode_rgb565(again,offset)
   require(len(rgb)==640*480*3,'decoder extent');p=out/f'fb{i}.png';Image.frombytes('RGB',(640,480),rgb).save(p)
   frames.append({'index':i,'offset':offset,'shown_by_observed_KOS':i==after['pvr']['view_target'],'png_sha256':digest(p.read_bytes()),'decoded_rgb_sha256':digest(rgb),'second_read_same_pixels':rgb==rgb2})
  if stable_key(after)!=stable_key(final) or not all(f['second_read_same_pixels'] for f in frames):verdict['readonly_snapshot_consistent']=False;verdict['snapshot_refusals'].append('changed state/pixels on bounded second read')
  report={'source':SOURCE,'elf_sha256':layout['elf_sha256'],'pid':a.pid,'owned_image':owned.image,'same_owned_handle_used':True,'duration_s':time.monotonic()-start,'before':before,'after':after,'final':final,'frames':frames,'verdict':verdict,'layout_sha256':digest(pathlib.Path(a.layout).read_bytes()),'binding_sha256':digest(pathlib.Path(a.binding).read_bytes()),'vram_sha256':digest(vram)}
  (out/'receipt.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(verdict))
if __name__=='__main__':main()