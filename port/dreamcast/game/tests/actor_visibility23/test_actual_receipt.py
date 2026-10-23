"""Actual extracted readiness getters + receipt, real source strips, current state.
No native Render call or guest execution is implied by these host controls.
"""
import ctypes as C,sys,json,struct
from pathlib import Path
L=C.CDLL(sys.argv[1]);out=Path(sys.argv[2]);inp=Path(sys.argv[3])
arr=lambda xs:(C.c_float*len(xs))(*xs)
P=arr([0,1,0,1,0,-.001,-1]);V=arr([0,0,640,480,0,1])
L.host_real_load.argtypes=[C.c_void_p,C.c_uint]
L.host_receipt_begin.argtypes=[C.POINTER(C.c_float)]*3
L.host_receipt_emit.argtypes=[C.c_uint]*3+[C.c_void_p,C.c_uint,C.c_void_p,C.c_uint,C.c_uint]
L.re4dc_actor_world23_ready.argtypes=[C.POINTER(C.c_float)]*3+[C.c_float]*2
data=(out/'OCCL.bin').read_bytes();blob=C.create_string_buffer(data);assert L.host_real_load(blob,len(data))
proof=json.loads((out/'geometry-proof.json').read_text());mesh=(inp/'ps2-world.re4mesh').read_bytes()
o_let=struct.unpack_from('<I',mesh,48)[0];o_strip=struct.unpack_from('<I',mesh,56)[0]
def fill(field,fault=0):
 row=next(x for x in proof if x['field']==field)
 seen=set()
 for need in row['required_meshlet_alternatives']:
  key=need['part'],need['meshlet']
  if key in seen:continue
  seen.add(key)
  fv,fs,sb,nv,sc=struct.unpack_from('<IIIHH',mesh,o_let+28*need['meshlet'])
  start=o_strip+fs+(2*nv if sc&0x8000 else 0);strip=C.create_string_buffer(mesh[start:start+sb]);codes=(C.c_ubyte*nv)()
  if fault==1:
   for i in range(nv):codes[i]=1
  if fault==2:
   for i in range(nv):codes[i]=4
  L.host_receipt_emit(field,need['part'],need['meshlet'],strip,sb,codes,nv,255)
def ready(v):return bool(L.re4dc_actor_world23_ready(v,P,V,50,25000))
cases=0
for field,x in [(5,112950),(7,117050)]:
 v=arr([1,0,0,-x,0,1,0,-4000,0,0,1,-20000])
 for fault in [0,1,2]:
  L.host_real_state(0);L.host_receipt_frame_state(1,0);L.host_receipt_scene_state(1,42);L.host_receipt_begin(v,P,V);fill(field,fault)
  assert not ready(v);L.host_receipt_end(1);assert ready(v)==(fault==0);cases+=1
 L.host_receipt_begin(v,P,V);fill(field);L.host_receipt_end(0);assert not ready(v);cases+=1
 L.host_receipt_begin(v,P,V);fill(field);L.host_receipt_end(1);assert ready(v)
 for state in [1,2,3,4,5]:
  L.host_real_state(state);assert not ready(v);L.host_real_state(0);assert ready(v);cases+=1
 for live,abort in [(0,0),(1,1)]:
  L.host_receipt_frame_state(live,abort);assert not ready(v);cases+=1
 L.host_receipt_frame_state(1,0);assert ready(v)
 changed=arr(list(v));changed[3]+=1;assert not ready(changed);cases+=1
 L.host_receipt_scene_state(0,42);assert not ready(v);cases+=1
 L.host_receipt_scene_state(1,43);assert not ready(v);cases+=1
 L.host_receipt_begin(v,P,V);fill(field);L.host_receipt_end(1);assert ready(v);cases+=1
 L.host_receipt_scene_state(1,0xffffffff);assert not ready(v);cases+=1
 L.host_receipt_scene_state(1,43);assert ready(v)
 L.host_real_identity(1);assert not ready(v);cases+=1 # increments actual stub UI frame
 L.host_receipt_close();assert not ready(v);cases+=1
print(json.dumps({'actual_getter_controls':cases,'source':'exact native_static/native_ui getter definitions, actual mesh strip bytes; synthetic frame/state/palette only'},indent=2))
