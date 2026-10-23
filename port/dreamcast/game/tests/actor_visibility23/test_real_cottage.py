"""Actual production OCCL + exact extracted placement guard, real candidate metadata.
World boxes/poses/views are host controls; this is not actual gameplay/Render admission.
"""
import ctypes as C,sys,json,struct,re,math,hashlib
from pathlib import Path
from fractions import Fraction as F
proof=json.loads(Path(sys.argv[2]).with_name("geometry-proof.json").read_text())
real_triangles=[vs for row in proof for vs in row["source_common_triangles"]]
def sub(a,b):return [x-y for x,y in zip(a,b)]
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
def ray_hit(eye,target,vs):
 e=list(map(F,eye));t=list(map(F,target));a,b,c=[list(map(F,v)) for v in vs];d=sub(t,e);u=sub(b,a);v=sub(c,a);h=cross(d,v);det=dot(u,h)
 if not det:return False
 inv=1/det;q=sub(e,a);alpha=dot(q,h)*inv;r=cross(q,u);beta=dot(d,r)*inv;fraction=dot(v,r)*inv
 return 0<=alpha and 0<=beta and alpha+beta<=1 and 0<fraction<1
ray_checks=0;cap_controls=0
L=C.CDLL(sys.argv[1]);arr=lambda xs:(C.c_float*len(xs))(*xs)
L.host_real_load.argtypes=[C.c_void_p,C.c_uint];L.host_real_state.argtypes=[C.c_uint]
L.re4dc_room_vis_hidden.argtypes=[C.POINTER(C.c_float),C.c_float,C.c_float,C.POINTER(C.c_float),C.POINTER(C.c_float)]
L.host_bounds_at_near.argtypes=[C.c_void_p,C.c_void_p,C.c_uint,C.c_uint,C.POINTER(C.c_float),C.c_uint,C.c_float]+[C.POINTER(C.c_float)]*6+[C.c_float]
L.host_world_error.argtypes=[C.POINTER(C.c_float)]*3+[C.c_float,C.POINTER(C.c_float),C.c_float]
L.host_groups.argtypes=[C.c_void_p,C.c_void_p,C.c_uint,C.c_uint,C.c_uint,C.c_uint,C.c_uint,C.POINTER(C.c_uint)]
data=open(sys.argv[2],'rb').read();buf=C.create_string_buffer(data);assert L.host_real_load(buf,len(data));L.host_real_state(0)
def view(x=112950,y=4000,z=20000):return arr([1,0,0,-x,0,1,0,-y,0,0,1,-z])
def box(v,lo,hi):return bool(L.re4dc_room_vis_hidden(v,1,25000,arr(lo),arr(hi)))
v=view();lo=[112850,3900,9900];hi=[113050,4100,10100]
assert box(v,lo,hi),'fully hidden upper-wall box'
assert not box(v,[118500,3900,9900],[120000,4100,10100]),'edge escapes both cottage panels'
assert not box(view(y=3350),[112850,3300,9900],[113050,3400,10100]),'real window-height opening must stay visible'
# State changes in the SAME ui frame must be observed by every hide, not cached.
for state in [1,2,3,4,5,6]:
 L.host_real_state(state);assert not box(v,lo,hi),('broken/moved/pose/source/gate/area',state)
 L.host_real_state(0);assert box(v,lo,hi)
L.host_real_identity(0);assert not box(v,lo,hi);L.host_real_identity(1);assert box(v,lo,hi)
assert not box(view(z=18000),lo,hi),'opposite face refuses'
# Actual source points with synthetic equal identity palettes/root translation.
# This prices opportunity only; there is no current-animation/AI claim.
results=[]
for filename in sys.argv[3:]:
 text=open(filename).read();arrays={}
 for prefix,kind,body in re.findall(r'alignas\(32\) static (?:const )?unsigned char ((?:a\d+_)?i\d+)_(pos|gx)\[\] = \{(.*?)\};',text,re.S):
  arrays[prefix,kind]=bytes(int(v.strip(),0) for v in body.replace('\n',',').split(',') if v.strip())
 row={'sha256':hashlib.sha256(text.encode()).hexdigest(),'eligible_sections':0,'eligible_records':0,'hidden_sections':0,'hidden_records':0,'groups':0,'kind':'real source / SYNTHETIC palette-root-view; real cottage polygons'}
 for (prefix,kind),s in arrays.items():
  if not re.search(r'i[01]$',prefix) or kind!='gx' or s[:2]!=b'\xfe\3' or (prefix,'pos') not in arrays:continue
  raw=arrays[prefix,'pos'];pos=C.create_string_buffer(raw);nm=struct.unpack_from('<H',s,4)[0];off=struct.unpack_from('<H',s,8)[0]*4;rs=3+bool(s[2]&1)+bool(s[2]&2)
  entries=1+max(struct.unpack_from('<H',raw,i+6)[0] for i in range(0,len(raw),8));palette=arr([1,0,0,0,1,0,0,0,1,0,0,0]*entries)
  mv=arr([1,0,0,0,0,1,0,0,0,0,1,-10000]);P=arr([0,1,0,1,0,-.001,-1]);V=arr([0,0,640,480,0,1])
  for mi in range(nm):
   c,first,_=struct.unpack_from('<IHH',s,32+mi*8);nv=c&255;record=s[off+first*rs*2:off+(first+nv)*rs*2];rr=b''.join(record[i*rs*2:i*rs*2+6] for i in range(nv));rec=C.create_string_buffer(rr);groups=C.c_uint();L.re4dc_actor_visibility23_reset()
   if not L.host_groups(pos,rec,1,nv,len(raw)//8,8,3,C.byref(groups)):continue
   lower=arr([0]*3);upper=arr([0]*3)
   if not L.host_bounds_at_near(pos,rec,nv,len(raw)//8,palette,entries,1/16,mv,v,P,V,lower,upper,50):continue
   assert L.host_world_error(v,P,V,50,arr([118646,6015,19630]),50)
   row['eligible_sections']+=1;row['eligible_records']+=nv;row['groups']+=groups.value
   if L.re4dc_room_vis_hidden(v,50,25000,lower,upper):
    row['hidden_sections']+=1;row['hidden_records']+=nv
    for j in range(nv):
     vi=struct.unpack_from('<H',rr,j*6)[0];x,y,z,_=struct.unpack_from('<hhhH',raw,vi*8);world=[112950+x/16,4000+y/16,10000+z/16]
     assert all(lower[a]<=world[a]<=upper[a] for a in range(3))
     assert any(ray_hit([112950,4000,20000],world,tri) for tri in real_triangles),(prefix,mi,j,world)
     ray_checks+=1
   if not cap_controls:
    assert L.host_bounds_at_near(pos,rec,nv,len(raw)//8,palette,entries,1/16,mv,v,P,V,lower,upper,10)
    assert not L.host_bounds_at_near(pos,rec,nv,len(raw)//8,palette,entries,1/16,mv,v,P,V,lower,upper,1)
    huge=arr([1,0,0,-500001,0,1,0,-4000,0,0,1,-20000])
    assert not L.host_bounds_at_near(pos,rec,nv,len(raw)//8,palette,entries,1/16,mv,huge,P,V,lower,upper,50)
    skew=arr([1.001,0,0,100000,0,1,0,0,0,0,1,0])
    assert not L.host_bounds_at_near(pos,rec,nv,len(raw)//8,palette,entries,1/16,mv,skew,P,V,lower,upper,50)
    assert not L.host_world_error(v,P,V,50,arr([10000000]*3),50)
    assert not L.host_world_error(v,P,V,50,arr([118646,6015,19630]),1)
    cap_controls=6
 results.append(row)
print(json.dumps({'real_panels':2,'fully_hidden':True,'partial_edge_kept':True,'window_opening_kept':True,'live_state_same_frame_negative_cases':6,'identity_refusal':True,'opposite_side_refusal':True,'exact_real_triangle_ray_checks':ray_checks,'coverage_cap_and_range_controls':cap_controls,'source_opportunities':results},indent=2))
