"""Exact basic interval oracles; real source geometry under synthetic poses/views.
No private vertices are stored in this file. Run with host.so and actual header paths.
"""
import ctypes as C,random,math,struct,re,sys,json,hashlib
from fractions import Fraction as F
lib=C.CDLL(sys.argv[1]);random.seed(23023)
class I(C.Structure):_fields_=[('lo',C.c_float),('hi',C.c_float)]
for name in ['add','mul','div']:
 f=getattr(lib,'shz_bounds_'+name);f.argtypes=[I,I,C.POINTER(I)];f.restype=C.c_int
lib.shz_bounds_mode_supported.argtypes=[C.c_uint];lib.shz_bounds_mode_supported.restype=C.c_int
lib.host_groups.argtypes=[C.c_void_p,C.c_void_p,C.c_uint,C.c_uint,C.c_uint,C.c_uint,C.c_uint,C.POINTER(C.c_uint)]
lib.host_bounds.argtypes=[C.c_void_p,C.c_void_p,C.c_uint,C.c_uint,C.POINTER(C.c_float),C.c_uint,C.c_float]+[C.POINTER(C.c_float)]*6
lib.re4dc_actor_visibility23_reset.argtypes=[]
F32=lambda x:struct.unpack('<f',struct.pack('<f',x))[0]
floatarray=lambda x:(C.c_float*len(x))(*x)
lib.host_panel.argtypes=[C.c_uint]
lib.re4dc_room_vis_hidden.argtypes=[C.POINTER(C.c_float),C.c_float,C.c_float,C.POINTER(C.c_float),C.POINTER(C.c_float)]
checks=0;reject=0
for mode in [0,1,1<<18,(1<<18)|1]:assert lib.shz_bounds_mode_supported(mode)
for mode in [2,3,1<<19,1<<20,1<<21,*[1<<i for i in range(7,12)]]:assert not lib.shz_bounds_mode_supported(mode)
# Exact rational endpoint oracle: cancellation, signed zero, extremes and RZ.
crt=C.CDLL(None);crt.fesetround.argtypes=[C.c_int]
for rounding in [0,0xc00]:
 assert crt.fesetround(rounding)==0
 for j in range(8000):
  vals=[F32(math.ldexp(random.uniform(-2,2),random.randrange(-120,120))) for _ in range(4)]
  a=I(*sorted(vals[:2]));b=I(*sorted(vals[2:]));out=I()
  for name in ['add','mul','div']:
   fn=getattr(lib,'shz_bounds_'+name);ok=fn(a,b,C.byref(out))
   if not ok:reject+=1;continue
   if name=='div':assert not b.lo<=0<=b.hi
   exact=[F(x)+F(y) if name=='add' else F(x)*F(y) if name=='mul' else F(x)/F(y) for x in [a.lo,a.hi] for y in [b.lo,b.hi]]
   assert F(out.lo)<=min(exact)<=max(exact)<=F(out.hi),(name,a.lo,a.hi,b.lo,b.hi,out.lo,out.hi)
   checks+=1
assert crt.fesetround(0)==0
# Unsupported boundary arithmetic must fail rather than output an inward box.
for x,y in [(2**-126,2**-126),(2**127,2**127)]:assert not lib.shz_bounds_mul(I(x,x),I(y,y),C.byref(I()))
for x in [float('nan'),float('inf'),2**-149]:assert not lib.shz_bounds_add(I(x,x),I(1,1),C.byref(I()))
assert not lib.shz_bounds_div(I(1,1),I(-1,1),C.byref(I()))
# Cache key/lifetime, over-capacity, invalid VI and reset tests.
pos=(C.c_short*40)(*[v for i in range(10) for v in (i,i*2,-i,i)])
rec=(C.c_ushort*30)(*[v for i in range(10) for v in (i,0,0)])
n=C.c_uint()
assert lib.host_groups(pos,rec,1,8,10,8,3,C.byref(n)) and n.value==8
assert not lib.host_groups(pos,rec,1,9,10,8,3,C.byref(n))
assert not lib.host_groups(pos,rec,0,8,10,8,3,C.byref(n))
assert not lib.host_groups(pos,rec,1,8,10,6,3,C.byref(n))
assert not lib.host_groups(pos,rec,1,8,1,8,3,C.byref(n))
lib.re4dc_actor_visibility23_reset()
assert lib.host_groups(pos,rec,2,8,10,8,3,C.byref(n))
# Real package headers, with clearly SYNTHETIC palette poses and opaque panels.
results=[];oracle_vertices=0
for filename in sys.argv[2:]:
 text=open(filename).read();arrays={}
 for prefix,kind,body in re.findall(r'alignas\(32\) static (?:const )?unsigned char ((?:a\d+_)?i\d+)_(pos|gx)\[\] = \{(.*?)\};',text,re.S):
  arrays[prefix,kind]=bytes(int(v.strip(),0) for v in body.replace('\n',',').split(',') if v.strip())
 row={'sha256':hashlib.sha256(text.encode()).hexdigest(),'kind':'real package, synthetic palette/camera/panel; not guest','eligible_records':0,'bounded_records':0,'groups':0,'panel_hidden_records':0,'opening_kept_records':0}
 for (prefix,kind),s in arrays.items():
  if kind!='gx' or s[:2]!=b'\xfe\3' or (prefix,'pos') not in arrays:continue
  raw=arrays[prefix,'pos'];posbuf=C.create_string_buffer(raw);nm=struct.unpack_from('<H',s,4)[0];off=struct.unpack_from('<H',s,8)[0]*4;rs=3+bool(s[2]&1)+bool(s[2]&2)
  entries=1+max(struct.unpack_from('<H',raw,i+6)[0] for i in range(0,len(raw),8))
  # Per-palette affine positions, including scale/shear/rotation/translation.
  palettes=[]
  for k in range(entries):
   ang=(k%11)*.07;co=F32(math.cos(ang));si=F32(math.sin(ang));palettes += [co,si,0,-si,co,0,.02,0,1,(k%5)*3,(k%7)*2,0]
  pal=floatarray(palettes);q=1/16
  view=floatarray([1,0,0,0,0,1,0,0,0,0,1,0]);mv=floatarray([1,0,0,0,0,1,0,0,0,0,1,-12000])
  proj=floatarray([0,1,0,1,0,-.001,-1]);viewport=floatarray([0,0,640,480,0,1])
  for mi in range(nm):
   c,first,_=struct.unpack_from('<IHH',s,32+mi*8);nv=c&255;record=s[off+first*rs*2:off+(first+nv)*rs*2]
   # Bridge uses3words; strip optional attrs for test only, never runtime source.
   rr=b''.join(record[i*rs*2:i*rs*2+6] for i in range(nv));recbuf=C.create_string_buffer(rr)
   lib.re4dc_actor_visibility23_reset();n=C.c_uint()
   if not lib.host_groups(posbuf,recbuf,1,nv,len(raw)//8,8,3,C.byref(n)):continue
   row['eligible_records']+=nv;row['groups']+=n.value
   lo=floatarray([0]*3);hi=floatarray([0]*3)
   if not lib.host_bounds(posbuf,recbuf,nv,len(raw)//8,pal,entries,q,mv,view,proj,viewport,lo,hi):continue
   row['bounded_records']+=nv
   points=[]
   # Exact-double scalar oracle of every actual source point under this pose.
   for i in range(nv):
    vi=struct.unpack_from('<H',rr,i*6)[0];x,y,z,pi=struct.unpack_from('<hhhH',raw,vi*8);P=palettes[pi*12:pi*12+12];xyz=[x*q,y*q,z*q]
    v=[sum(P[c*3+a]*xyz[c] for c in range(3))+P[9+a] for a in range(3)];v[2]-=12000
    assert all(lo[a]<=v[a]<=hi[a] for a in range(3)),(prefix,mi,tuple(lo),v,tuple(hi))
    oracle_vertices+=1
    points.append(v)
   # Actual unchanged production OCCL predicate, synthetic opaque slabs.
   lib.host_panel(0)
   hidden=lib.re4dc_room_vis_hidden(view,1,25000,lo,hi)
   if hidden:
    row['panel_hidden_records']+=nv
    # Every exact oracle ray intersects the opaque panel (both slab faces).
    for xyz in points:
     for zface in [-5990,-6010]:
      t=zface/xyz[2];assert 0<t<1
      assert abs(xyz[0]*t)<5000 and abs(xyz[1]*t)<5000
   lib.host_panel(1)
   gap_hidden=lib.re4dc_room_vis_hidden(view,1,25000,lo,hi)
   opening=any(abs(xyz[0]*(-6000/xyz[2]))<200 for xyz in points)
   if opening:assert not gap_hidden;row['opening_kept_records']+=nv
   for mode in [2,3,4]:
    lib.host_panel(mode);assert not lib.re4dc_room_vis_hidden(view,1,25000,lo,hi)
   # Near-straddling, singular camera, non-normal palette always fail open.
   badmv=floatarray([1,0,0,0,0,1,0,0,0,0,1,0]);assert not lib.host_bounds(posbuf,recbuf,nv,len(raw)//8,pal,entries,q,badmv,view,proj,viewport,lo,hi)
   badview=floatarray([0]*12);assert not lib.host_bounds(posbuf,recbuf,nv,len(raw)//8,pal,entries,q,mv,badview,proj,viewport,lo,hi)
 results.append(row)
print(json.dumps({'exact_endpoint_checks':checks,'unsupported_operations':reject,'real_source_oracle_vertices':oracle_vertices,'packages':results},indent=2))
