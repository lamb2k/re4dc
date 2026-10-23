#!/usr/bin/env python3
"""Actual linked SDK caller opcodes versus target-lowered C strip oracle."""
import argparse,sys,struct,itertools,random,json,hashlib
from pathlib import Path
here=Path(__file__).resolve().parent
sys.path.insert(0,str(here.parent/'backface_sh4_kernel'))
import object_test as base
class WalkMachine(base.Machine):
    def __init__(self,text,cache,stream,oc,limit,cull,fpscr=0,trace=False):
        super().__init__(text,cache,stream,255,cull,fpscr,trace)
        self.map(0xa000,oc)
        self.area_ops=0
        self.map(0x9000,struct.pack('<10I',0x8000,0x8000+len(stream),0xa000,0x2000,limit,cull,0xe0000000,3,5,7))
    def step(self,pc,delay=False):
        w=self.read(pc,2);n=(w>>8)&15;m=(w>>4)&15;R=self.reg
        if w&0xf00f in (0xf001,0xf002,0xf005,0xf00e):self.area_ops+=1
        if w&0xf000==0x9000:
            R[n]=base.signed(self.read(pc+4+(w&255)*2,2),16)&base.U32
        elif w&0xf00f==0x6000:R[n]=base.signed(self.read(R[m],1),8)&base.U32
        elif w&0xf00f==0x200b:R[n]|=R[m]
        elif w&0xf0ff==0x4010:R[n]=(R[n]-1)&base.U32;self.t=int(R[n]==0)
        elif w&0xff00 in (0x8d00,0x8f00):
            assert not delay
            condition=self.t==int(w&0xff00==0x8d00)
            target=pc+4+base.signed(w&255,8)*2 if condition else pc+4
            self.steps+=1;self.step(pc+2,True);return target
        else:return super().step(pc,delay)
        self.steps+=1;return pc+2
    def run(self):
        while self.pc!=0xfffffff0:
            if self.pc==0x700000:self.external();continue
            self.pc=self.step(self.pc);assert self.steps<400000
        assert self.reg[15]==self.initial_regs[15]
        assert self.reg[8:15]==self.initial_regs[8:15]
        assert self.fpscr==self.initial_fpscr
        bank=(self.initial_fpscr>>21)&1
        assert self.fp[bank][12:16]==self.initial_fp[bank][12:16]
        assert self.fp[bank^1]==self.initial_fp[bank^1]
        vals=[self.read(0x9000+i*4,4) for i in range(10)]
        assert vals[6]==0xe0000000+len(self.output)
        if self.trace:assert self.trace_output==self.output
        return bytes(self.output),vals[0]-0x8000,*vals[7:]
def expected(oracle,cache,stream,oc,limit,cull):
    s=0;out=b'';culled=3;emitted=5;tri=7
    while s<len(stream):
        n=stream[s]
        if not n:break
        ix=stream[s+1:s+1+n];assert len(ix)==n
        all_=255;any_=0
        for i in ix:all_&=oc[i];any_|=oc[i]
        if all_&3:culled+=1
        elif any_&3 or n>limit:break
        elif all_&60:culled+=1
        else:
            out+=oracle(cache,ix,255,cull)[0];emitted+=1;tri+=max(0,n-2)
        s+=n+1
    return out,s,culled,emitted,tri
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--objects',type=Path,required=True);p.add_argument('--report',type=Path,required=True);p.add_argument('--early-clip',action='store_true',help='Require the opt-in early depth exit instead of the original full scan');a=p.parse_args();assert not a.report.exists()
oracle=base.oracle_load(a.objects/'oracle.so');rng=random.Random(0x5d6c0de)
cache=base.generated_cache([(rng.uniform(-640,640),rng.uniform(-480,480)) for i in range(256)])
cases=[]
for n in (0,1,2,3,4,31,32,33,63,64,65,119,127,255):
    cases.append((bytes([n])+bytes(range(n)),bytes(256),255,'sizes'))
for code in (0,1,2,3,4,16,60,64,128,255):
    for position in (0,2,4):
        for n in (3,5,64):
            oc=bytearray(256);oc[100+min(position,n-1)]=code
            cases.append((bytes([3,0,1,2,n])+bytes(range(100,100+n))+bytes([3,10,11,12]),bytes(oc),255,'outcode-position'))
    oc=bytes([code])*256;cases.append((bytes([5,0,1,2,3,4]),oc,255,'outcode-all'))
for limit in (0,1,2,3,4,63,64,65,119,255):
    cases.append((bytes([3,0,1,2,64])+bytes(range(64))+bytes([3,6,7,8]),bytes(256),limit,'limit-stop'))
for i in range(50):
    stream=bytearray();oc=bytearray(256)
    for j in range(8):
        n=rng.randint(1,64);stream.extend([n]+[rng.randrange(256) for _ in range(n)])
    for j in range(10):oc[rng.randrange(256)]=rng.choice((0,0,0,1,2,4,16,128))
    cases.append((bytes(stream),bytes(oc),rng.randrange(1,256),'random-batch'))
# Gates must actually elide area, not merely preserve output after wasted math.
for position in (1,31,32,63):
    oc=bytearray(256);oc[position]=1
    cases.append((bytes([64])+bytes(range(64)),bytes(oc),255,'interior-first-zero-depth'))
for code,limit,kind in ((1,255,'gate-depth-all'),(4,255,'gate-screen-all'),(0,63,'gate-limit-first-zero'),(1,63,'gate-depth-before-limit')):
    cases.append((bytes([64])+bytes(range(64)),bytes([code])*256,limit,kind))
oc=bytearray(256);oc[0]=1
cases.append((bytes([64])+bytes(range(64)),bytes(oc),63,'gate-limit-first-depth'))
oc=bytearray(256);oc[0]=4
cases.append((bytes([64])+bytes(range(64)),bytes(oc),255,'prepassed-eligible-first-screen'))
oc=bytearray([4])*256;oc[0]=0
cases.append((bytes([64])+bytes(range(64)),bytes(oc),255,'eligible-first-zero-later-screen'))
passed=0;groups={}
for stream,oc,limit,kind in cases:
    groups[kind]=groups.get(kind,0)+1
    for cull,trace in itertools.product((1,2),(0,1)):
        text=base.text_section(a.objects/('walk-trace%d.elf'%trace))
        m=WalkMachine(text,cache,stream,oc,limit,cull,trace=bool(trace));m.pc=struct.unpack_from('<I',(a.objects/('walk-trace%d.elf'%trace)).read_bytes(),24)[0]
        try:got=m.run()
        except AssertionError as error:raise AssertionError((kind,len(stream),limit,cull,trace,str(error),list(m.ring))) from error
        want=expected(oracle,cache,stream,oc,limit,cull)
        if kind.startswith('gate-'):assert m.area_ops==0,(kind,m.area_ops)
        if kind=='interior-first-zero-depth':
            if a.early_clip:assert m.area_ops<62*7,(kind,m.area_ops)
            else:assert m.area_ops==62*7,(kind,m.area_ops)
        if kind in ('prepassed-eligible-first-screen','eligible-first-zero-later-screen'):assert m.area_ops==62*7,(kind,m.area_ops)
        assert got==want,(kind,len(stream),limit,cull,trace,len(got[0]),len(want[0]),got[1:],want[1:]);passed+=1
for bits in range(16):
    fpscr=((bits&1)<<21)|((bits&2)<<19)|((bits&4)<<17)|((bits&8)<<15)
    stream=bytes([5,0,1,2,3,4,3,5,6,7]);oc=bytes(256)
    for trace in (0,1):
        text=base.text_section(a.objects/('walk-trace%d.elf'%trace));m=WalkMachine(text,cache,stream,oc,255,2,fpscr,trace=bool(trace));m.pc=struct.unpack_from('<I',(a.objects/('walk-trace%d.elf'%trace)).read_bytes(),24)[0]
        assert m.run()==expected(oracle,cache,stream,oc,255,2)
result=dict(scope=__doc__,comparisons=passed,mode_controls=32,cases=len(cases),groups=groups,exact_words=True,clip_stop_pointer=True,all_any_order=True,counts=True,callee_fpscr_xf=True,no_hardware_claim=True,conservative_rejects_skip_all_area=True,interior_crossing_cost_explicit=True,early_clip=a.early_clip,files={p.name:base.sha(p.read_bytes()) for p in a.objects.glob('walk-trace*.elf')})
a.report.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
