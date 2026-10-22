"""Actual C bf::strip opcode classifier, with external copy/emitter explicitly excluded."""
from pathlib import Path
import importlib.util,subprocess,struct,re,json,hashlib,ctypes
D=Path('/root/probe/codex-backface-sh4zam-review/port/dreamcast/tools/d367/backface_sh4zam_review')
def mod(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
k=mod('kt','/root/probe/codex-backface-sh4zam-kernel/port/dreamcast/tools/d367/backface_sh4_kernel/object_test.py')
# Reuse model without executing its table-generation main body.
ns={};src=(D/'dynamic-kernel-model.py').read_text();exec(src.split('rows=[]')[0],ns)
price=ns['price'];base_decode=ns['decode']
def decode(op):
 if op.split()[0]=='jsr':return ('BR',2,['pr'],[op.split('@')[1]],{'bru'},[])
 return base_decode(op)
ns['decode']=decode

def loadfn(obj,keyword,stem='.text._ZN5re4dc2bf5strip'):
 b=obj.read_bytes();off=struct.unpack_from('<I',b,32)[0];ent,n,names=struct.unpack_from('<3H',b,46);ss=[struct.unpack_from('<10I',b,off+i*ent) for i in range(n)];st=ss[names];strings=b[st[4]:st[4]+st[5]]
 name=lambda s:strings[s[0]:].split(b'\0')[0].decode()
 ti=next(i for i,s in enumerate(ss) if name(s).startswith(stem) and keyword in name(s));s=ss[ti];data=bytearray(b[s[4]:s[4]+s[5]])
 for rs in ss:
  if rs[1]!=4 or rs[7]!=ti:continue
  sy=ss[rs[6]];sts=ss[sy[6]];tb=b[sts[4]:sts[4]+sts[5]]
  for at in range(rs[4],rs[4]+rs[5],12):
   dest,info,addend=struct.unpack_from('<IIi',b,at);sym=struct.unpack_from('<IIIBBH',b,sy[4]+(info>>8)*16);symbol=tb[sym[0]:].split(b'\0')[0].decode();assert info&255==1
   target=0x700000 if symbol=='_memcpy' else 0x700100
   struct.pack_into('<I',data,dest,target+addend)
 dis=subprocess.check_output(['/opt/toolchains/dc/sh-elf/bin/sh-elf-objdump','-d','-j',name(s),str(obj)],text=True)
 ops={}
 for line in dis.splitlines():
  m=re.match(r'\s*([0-9a-f]+):\s+[0-9a-f]{2} [0-9a-f]{2}\s+(.+)',line)
  if m:ops[int(m[1],16)+0x100000]=re.sub(r'\b(bt|bf)\.s\b',r'\1/s',m[2].split('!')[0].strip())
 return bytes(data),ops

class CM(k.Machine):
 def __init__(self,text,ops,cache,ix,cull):
  super().__init__(text,cache,ix,255,cull);self.ops=ops;self.events=[];self.fpUL=0;self.copies=0;self.emits=[];self.reg[15]=0x4ff000;self.reg[4:8]=[0x2000,0x8000,len(ix),cull];self.write(self.reg[15],0x9000,4);self.write(0x9000,0x9100,4)
 def step(self,pc,delay=False):
  i=len(self.events);self.events.append([pc,self.ops[pc],None]);w=self.read(pc,2);R=self.reg;n=(w>>8)&15;m=(w>>4)&15;nextpc=pc+2;handled=True
  if w&0xf00f==0x200b:R[n]|=R[m]
  elif w&0xf00f==0x000e:R[n]=self.read(R[m]+R[0],4)
  elif w&0xf00f==0x6000:R[n]=k.signed(self.read(R[m],1),8)&k.U32
  elif w&0xf000==0x9000:R[n]=k.signed(self.read(pc+4+(w&255)*2,2),16)&k.U32
  elif w&0xff00==0xc700:R[0]=((pc+4)&~3)+(w&255)*4
  elif w&0xff00==0x8400:R[0]=k.signed(self.read(R[m]+(w&15),1),8)&k.U32
  elif w&0xf00f==0x0004:self.write(R[n]+R[0],R[m],1)
  elif w&0xf00f==0x2000:self.write(R[n],R[m],1)
  elif w&0xf0ff==0x4010:R[n]=(R[n]-1)&k.U32;self.t=int(R[n]==0)
  elif w&0xf0ff==0x0029:R[n]=self.t
  elif w&0xf0ff==0xf09d:self.sf(n,0x3f800000)
  elif w&0xf0ff==0xf01d:self.fpUL=self.f(n)
  elif w&0xf0ff==0xf00d:self.sf(n,self.fpUL)
  elif w&0xff00 in (0x8d00,0x8f00):
   take=self.t==(w&0xff00==0x8d00);self.step(pc+2,True);nextpc=pc+4+(k.signed(w&255,8)*2 if take else 0)
  else:handled=False;nextpc=super().step(pc,delay)
  if handled:self.steps+=1
  self.events[i][2]=nextpc;return nextpc
 def runC(self):
  while self.pc!=0xfffffff0:
   if self.pc==0x700000:
    dst,src,n=self.reg[4:7]
    for i in range(n):self.write(dst+i,self.read(src+i,1),1)
    self.copies+=n;self.pc=self.pr;continue
   if self.pc==0x700100:
    self.emits.append(self.reg[6]);self.pc=self.pr;continue
   self.pc=self.step(self.pc);assert self.steps<50000
  return self.reg[0]
O=Path('/root/probe/lanes/route/out-bfasabcfc8a3pair01crW/obj/platform')
rows=[];pins={}
for kind,keyword in [('native_static','MeshDraw')]:
 obj=O/(kind+'.o');text,ops=loadfn(obj,keyword);pins[kind]=hashlib.sha256(obj.read_bytes()).hexdigest()
 for n in [4,8,16,32,64,128]:
  for pattern in ['front','back','mixed']:
   pts=[(float(i),float(i&1)*(1 if pattern=='front' else -1)) for i in range(n)]
   if pattern=='mixed':pts=[(float(i),float(((i//8)&1)*2-1)*(i&1)) for i in range(n)]
   m=CM(text,ops,k.generated_cache(pts),bytes(range(n)),2)
   try:sent=m.runC();cy=price(m.events)
   except Exception as e:print('FAIL',kind,n,pattern,str(e),[(hex(x[0]),x[1]) for x in m.events[-5:]]);raise
   assert sent==sum(m.emits)
   oracle=k.oracle_load(Path('/root/probe/backface-sh4zam-kernel-objects-20261022-201900-fmac07/oracle.so'))
   expected=oracle(k.generated_cache(pts),bytes(range(n)),255,2)
   assert sent==len(expected[0])//32 and len(m.emits)==expected[1]
   rows.append(dict(kind=kind,n=n,pattern=pattern,sent=sent,pieces=len(m.emits),external_memcpy_bytes=m.copies,classifier_only_modelled_cycles=cy,per_input_triangle=round(cy/(n-2),3)))
result=dict(scope='MODELLED actual C classifier opcodes only; external memcpy implementation and emitter callbacks excluded, caller walk also excluded',object_sha256=pins,rows=rows,limitations=['Census/hash diagnostics excluded by stubbing entire emit callback, along with actual SQ emitter; cannot claim this is complete C path.','Includes C function prologue/epilogue, classify, run scans, piece selection and actual call/return issue but not callback instructions.','No cache, memory, TA stalls or FPU exceptions; existing AVK latency/group approximation.'])
(D/'DYNAMIC-C-CLASSIFIER-MODEL.json').write_text(json.dumps(result,indent=2)+'\n')
for row in rows:
 if row['n']==64:print(row)





