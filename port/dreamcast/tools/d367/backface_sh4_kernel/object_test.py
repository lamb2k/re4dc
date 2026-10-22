#!/usr/bin/env python3
"""Execute the actual SH4 object opcodes in a bounded host interpreter.

This is source/host/object evidence, NOT SH4 hardware or Flycast execution.
Unknown opcodes, out-of-range reads, incomplete SQ bursts and write overruns
fail. Oracle preserves the original strip routine while lowering its single
determinant expression to the actual CPU1 SH4 FMAC order. See build_oracle.py.
"""
import argparse, collections, ctypes, ctypes.util, hashlib, itertools, json, math, random, struct
from pathlib import Path

U32=0xffffffff
_libm=ctypes.CDLL(ctypes.util.find_library("m"))
_fmaf=_libm.fmaf
_fmaf.argtypes=[ctypes.c_float]*3
_fmaf.restype=ctypes.c_float
def signed(x,b=32):
    return x-(1<<b) if x&(1<<(b-1)) else x
def f32(x):
    try: return struct.unpack('<f',struct.pack('<f',x))[0]
    except OverflowError: return math.copysign(math.inf,x)
def fbits(x): return struct.unpack('<I',struct.pack('<f',f32(x)))[0]
def asfloat(x): return struct.unpack('<f',struct.pack('<I',x))[0]
def sha(x): return hashlib.sha256(x).hexdigest()

def text_section(path):
    blob=path.read_bytes()
    assert blob[:6]==b'\x7fELF\x01\x01'
    off=struct.unpack_from('<I',blob,32)[0]
    ent,n,names=struct.unpack_from('<3H',blob,46)
    sections=[struct.unpack_from('<10I',blob,off+i*ent) for i in range(n)]
    ns=sections[names]; strings=blob[ns[4]:ns[4]+ns[5]]
    name=lambda s: strings[s[0]:].split(b'\0')[0].decode()
    ti=next(i for i,s in enumerate(sections) if name(s)=='.text')
    s=sections[ti]; text=bytearray(blob[s[4]:s[4]+s[5]])
    for rs in sections:
        if rs[1] not in (4,9) or rs[7]!=ti: continue
        syms=sections[rs[6]]; names_s=sections[syms[6]]
        st=blob[names_s[4]:names_s[4]+names_s[5]]
        for at in range(rs[4],rs[4]+rs[5],12 if rs[1]==4 else 8):
            dest,info=struct.unpack_from('<II',blob,at)
            sym=struct.unpack_from('<IIIBBH',blob,syms[4]+(info>>8)*16)
            symbol=st[sym[0]:].split(b'\0')[0].decode()
            assert info&255==1,('unsupported relocation',info,symbol)
            assert symbol=='_re4dc_backface_sh4_trace' or sym[5]==ti,('foreign relocation',info,symbol,sym[5])
            addend=struct.unpack_from('<i',text,dest)[0]
            if rs[1]==4:addend+=struct.unpack_from('<i',blob,at+8)[0]
            base=0x700000 if symbol=='_re4dc_backface_sh4_trace' else 0x100000+sym[1]
            struct.pack_into('<I',text,dest,base+addend)
    return bytes(text)

class Machine:
    def __init__(self,text,cache,indices,mask,cull,fpscr=0,trace=False):
        self.text=text; self.mem={}; self.reg=[(0x81374101+i*0x04030201)&U32 for i in range(16)]
        self.fp=[[0x3e800001+i*0x1701+b*0x10000 for i in range(16)] for b in range(2)]
        self.fpscr=fpscr; self.t=0; self.pr=0xfffffff0; self.pc=0x100000; self.steps=0
        self.sq=bytearray(64); self.written=[0,0]; self.output=bytearray(); self.trace_output=bytearray()
        self.spans=[]; self.trace=trace
        self.map(0x100000,text); self.map(0x2000,cache); self.map(0x8000,indices)
        self.map(0x9000,struct.pack('<8I',0x2000,0x8000,len(indices),mask,cull,0xe0000000,99,99))
        self.map(0x4f0000,bytes(0x10000)); self.reg[15]=0x500000; self.reg[4]=0x9000
        self.initial_regs=list(self.reg); self.initial_fp=[list(x) for x in self.fp]
        self.initial_fpscr=fpscr
        self.ring=collections.deque(maxlen=24)
    def map(self,a,b):
        for i,x in enumerate(b): self.mem[a+i]=x
    def read(self,a,n):
        assert all(a+i in self.mem for i in range(n)),('unmapped read',hex(a),n,hex(self.pc))
        return int.from_bytes(bytes(self.mem[a+i] for i in range(n)),'little')
    def write(self,a,v,n):
        b=(v&((1<<(8*n))-1)).to_bytes(n,'little')
        if 0xe0000000<=a<0xe0010000:
            slot=(a>>5)&1
            assert (a&31)+n<=32
            self.sq[a&63:(a&63)+n]=b
            self.written[slot]|=((1<<n)-1)<<(a&31)
        else:
            assert all(a+i in self.mem for i in range(n)),('unmapped write',hex(a),n)
            for i,x in enumerate(b): self.mem[a+i]=x
    def f(self,i): return self.fp[(self.fpscr>>21)&1][i]
    def sf(self,i,v): self.fp[(self.fpscr>>21)&1][i]=v&U32
    def arithmetic(self,op,a,b):
        def denorm(x):
            if self.fpscr&(1<<18) and x&0x7f800000==0: x&=0x80000000
            return asfloat(x)
        av,bv=denorm(a),denorm(b)
        value=av-bv if op==1 else av*bv
        out=fbits(value)
        if self.fpscr&(1<<18) and out&0x7f800000==0: out&=0x80000000
        return out
    def external(self):
        assert self.trace and self.fpscr&0x380000==0,('callback mode',hex(self.fpscr))
        cache,ix,n,mask=self.reg[4:8]
        self.spans.append((ix-0x8000,n,mask))
        for i in range(n):
            index=self.read(ix+i,1)&mask
            words=[self.read(cache+index*32+j*4,4) for j in range(8)]
            if mask==127: words[0]=0xe0000000
            if i+1==n: words[0]=0xf0000000
            self.trace_output.extend(struct.pack('<8I',*words))
        ret=self.pr
        for i in range(8): self.reg[i]=(0xdead1000+i)&U32
        # An adversarial ABI-valid hook clobbers caller-save FR0..11 and XF,
        # while preserving normal bank0 FR12..15 and callee-save GPRs.
        for i in range(12): self.fp[0][i]=0x7fc10000+i
        for i in range(16): self.fp[1][i]=0x7fc20000+i
        self.fpscr=0x380001
        self.pr=0xdead7777
        self.pc=ret
    def step(self,pc,delay=False):
        self.ring.append((hex(pc),hex(self.pr),hex(self.reg[15]),hex(self.fpscr)))
        w=self.read(pc,2); n=(w>>8)&15; m=(w>>4)&15; self.steps+=1
        R=self.reg; nextpc=pc+2; target=None
        if w==0x0009: pass
        elif w==0x000b: target=self.pr
        elif w==0xf3fd: self.fpscr^=1<<20
        elif w==0xfbfd: self.fpscr^=1<<21
        elif w&0xf000==0xe000: R[n]=signed(w&255,8)&U32
        elif w&0xf000==0x7000: R[n]=(R[n]+signed(w&255,8))&U32
        elif w&0xf000==0xd000: R[n]=self.read(((pc+4)&~3)+(w&255)*4,4)
        elif w&0xf000==0x5000: R[n]=self.read(R[m]+(w&15)*4,4)
        elif w&0xf000==0x1000: self.write(R[n]+(w&15)*4,R[m],4)
        elif w&0xf00f==0x6003: R[n]=R[m]
        elif w&0xf00f==0x6002: R[n]=self.read(R[m],4)
        elif w&0xf00f==0x6006:
            a=R[m]; R[n]=self.read(a,4)
            if n!=m:R[m]=(a+4)&U32
        elif w&0xf00f==0x6004:
            a=R[m]; R[n]=signed(self.read(a,1),8)&U32
            if n!=m:R[m]=(a+1)&U32
        elif w&0xf00f==0x000c: R[n]=signed(self.read(R[0]+R[m],1),8)&U32
        elif w&0xf00f==0x600c: R[n]=R[m]&255
        elif w&0xf00f==0x6007: R[n]=(~R[m])&U32
        elif w&0xf00f==0x2006:
            v=R[m];R[n]=(R[n]-4)&U32;self.write(R[n],v,4)
        elif w&0xf00f==0x2002: self.write(R[n],R[m],4)
        elif w&0xf00f==0x300c: R[n]=(R[n]+R[m])&U32
        elif w&0xf00f==0x3008: R[n]=(R[n]-R[m])&U32
        elif w&0xf00f==0x2009: R[n]&=R[m]
        elif w&0xf00f==0x200a: R[n]^=R[m]
        elif w&0xf00f==0x200b: R[n]|=R[m]
        elif w&0xf00f==0x2008: self.t=int((R[n]&R[m])==0)
        elif w&0xff00==0xc900: R[0]&=w&255
        elif w&0xff00==0xc800: self.t=int(R[0]&(w&255)==0)
        elif w&0xff00==0x8800: self.t=int(R[0]==signed(w&255,8)&U32)
        elif w&0xf00f==0x3002: self.t=int(R[n]>=R[m])
        elif w&0xf00f==0x3006: self.t=int(R[n]>R[m])
        elif w&0xf00f==0x3000: self.t=int(R[n]==R[m])
        elif w&0xf0ff==0x4011: self.t=int(signed(R[n])>=0)
        elif w&0xf0ff==0x4015: self.t=int(signed(R[n])>0)
        elif w&0xf0ff==0x4010:R[n]=(R[n]-1)&U32;self.t=int(R[n]==0)
        elif w&0xf0ff==0x4024:
            old=self.t;self.t=(R[n]>>31)&1;R[n]=((R[n]<<1)|old)&U32
        elif w&0xf0ff==0x4025:
            old=self.t;self.t=R[n]&1;R[n]=(R[n]>>1)|(old<<31)
        elif w&0xf00f==0x400d:
            count=signed(R[m]);amount=(-count)&31
            R[n]=((R[n]<<(count&31))&U32) if count>=0 else (0 if amount==0 else R[n]>>amount)
        elif w&0xf0ff==0x402b:target=R[n]
        elif w&0xf0ff in (0x4008,0x4018,0x4028): R[n]=(R[n]<<{0x4008:2,0x4018:8,0x4028:16}[w&0xf0ff])&U32
        elif w&0xf0ff==0x4000: self.t=(R[n]>>31)&1;R[n]=(R[n]<<1)&U32
        elif w&0xf0ff==0x4009: R[n]>>=2
        elif w&0xf0ff==0x4001: self.t=R[n]&1;R[n]>>=1
        elif w&0xff00 in (0x8900,0x8b00):
            if self.t==(w&0xff00==0x8900): nextpc=pc+4+signed(w&255,8)*2
        elif w&0xff00 in (0x8d00,0x8f00):
            assert not delay
            condition=self.t==int(w&0xff00==0x8d00)
            target=pc+4+signed(w&255,8)*2 if condition else pc+4
        elif w&0xf000==0xa000: target=pc+4+signed(w&4095,12)*2
        elif w&0xf0ff==0x400b: target=R[n];self.pr=pc+4
        elif w&0xf0ff==0x002a: R[n]=self.pr
        elif w&0xf0ff==0x006a: R[n]=self.fpscr
        elif w&0xf0ff in (0x4022,0x4062):
            R[n]=(R[n]-4)&U32;self.write(R[n],self.pr if w&0xf0ff==0x4022 else self.fpscr,4)
        elif w&0xf0ff==0x406a: self.fpscr=R[n]
        elif w&0xf0ff in (0x4026,0x4066):
            value=self.read(R[n],4);R[n]+=4
            if w&0xf0ff==0x4026:self.pr=value
            else:self.fpscr=value
        elif w&0xf0ff==0xf08d: self.sf(n,0)
        elif w&0xf00f==0xf00c:
            assert not self.fpscr&(1<<20),('unexpected double register move',hex(w))
            self.sf(n,self.f(m))
        elif w&0xf00f in (0xf001,0xf002): self.sf(n,self.arithmetic(w&15,self.f(n),self.f(m)))
        elif w&0xf0ff==0xf04d: self.sf(n,self.f(n)^0x80000000)
        elif w&0xf00f==0xf00e:
            values=[self.f(0),self.f(m),self.f(n)]
            if self.fpscr&(1<<18): values=[v&0x80000000 if v&0x7f800000==0 else v for v in values]
            out=fbits(_fmaf(*[asfloat(v) for v in values]))
            if self.fpscr&(1<<18) and out&0x7f800000==0: out&=0x80000000
            self.sf(n,out)
        elif w&0xf00f==0xf005: self.t=int(asfloat(self.f(n))>asfloat(self.f(m)))
        elif w&0xf00f in (0xf008,0xf009):
            size=8 if self.fpscr&(1<<20) else 4
            assert not (size==8 and n&1),('unexpected XD load',hex(w))
            a=R[m];value=self.read(a,size);self.sf(n,value&U32)
            if size==8:self.sf(n+1,value>>32)
            if w&15==9:R[m]=(R[m]+size)&U32
        elif w&0xf00f==0xf00b:
            size=8 if self.fpscr&(1<<20) else 4
            assert not (size==8 and m&1),('unexpected XD store',hex(w))
            value=self.f(m)|(self.f(m+1)<<32 if size==8 else 0)
            R[n]=(R[n]-size)&U32;self.write(R[n],value,size)
        elif w&0xf0ff==0x0083:
            a=R[n];slot=(a>>5)&1
            assert 0xe0000000<=a<0xe0010000 and a&31==0
            assert self.written[slot]==U32,('incomplete SQ burst',hex(a),hex(self.written[slot]))
            self.output.extend(self.sq[slot*32:slot*32+32]);self.written[slot]=0
        else: raise AssertionError(('unsupported SH4 opcode',hex(pc),hex(w)))
        if target is not None:
            assert not delay,('branch in delay slot',hex(pc))
            self.step(pc+2,True)
            nextpc=target
        return nextpc
    def run(self):
        while self.pc!=0xfffffff0:
            if self.pc==0x700000:self.external();continue
            self.pc=self.step(self.pc)
            assert self.steps<200000,('loop bound',hex(self.pc))
        assert self.reg[15]==self.initial_regs[15]
        assert self.reg[8:15]==self.initial_regs[8:15]
        assert self.fpscr==self.initial_fpscr
        bank=(self.initial_fpscr>>21)&1
        assert self.fp[bank][12:16]==self.initial_fp[bank][12:16], 'callee FPRs changed'
        assert self.fp[bank^1]==self.initial_fp[bank^1], 'XMTRX/opposite bank changed'
        q=self.read(0x9014,4);sent=self.read(0x9018,4);pieces=self.read(0x901c,4)
        assert q==0xe0000000+len(self.output) and sent*32==len(self.output)
        if self.trace:assert self.trace_output==self.output and len(self.spans)==pieces
        return bytes(self.output),pieces

def generated_cache(points,flags=True):
    words=[]
    for i,(x,y) in enumerate(points):
        words.extend([0x91000000+i if flags else 0xe0000000,fbits(x),fbits(y),
            0x3f800000+i,0x3c812301+i,0x3d123001+i,0x81234567^i,0x34567890+i])
    while len(words)<256*8: words.extend([0xe0000000,0,0,0,0,0,0,0])
    return struct.pack('<%dI'%len(words),*words)

def oracle_load(path):
    lib=ctypes.CDLL(str(path))
    f=lib.backface_oracle
    f.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_uint,ctypes.c_uint,ctypes.c_uint,ctypes.c_void_p,ctypes.POINTER(ctypes.c_uint)]
    f.restype=ctypes.c_uint
    def oracle(cache,ix,mask,cull):
        cb=ctypes.create_string_buffer(cache);ib=ctypes.create_string_buffer(ix)
        out=ctypes.create_string_buffer((len(ix)*3+16)*32);pieces=ctypes.c_uint()
        n=f(cb,ib,len(ix),mask,cull,out,ctypes.byref(pieces))
        return out.raw[:n*32],pieces.value
    return oracle

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--objects',type=Path,required=True)
    p.add_argument('--report',type=Path,required=True);args=p.parse_args()
    assert not args.report.exists()
    oracle=oracle_load(args.objects/'oracle.so')
    texts=[text_section(args.objects/('kernel-trace%d.o'%t)) for t in (0,1)]
    cases=[]
    # Every facing-run pattern up to nine triangles, realizable by zig-zag y.
    for t in range(1,10):
        for bits in itertools.product((0,1),repeat=t):
            ys=[0.0,1.0]
            for i,b in enumerate(bits):
                want=(-1.0 if b else 1.0)*(-1.0 if i&1 else 1.0)
                ys.append(2*ys[-1]-ys[-2]+want)
            for mask in (127,255):
                cases.append((generated_cache(list(enumerate(ys))),bytes(range(t+2)),mask,2,'runs'))
    cases.append((generated_cache([(0,0),(570.0137939453125,438.41583251953125),(1140.027587890625,876.8316650390625)]),bytes([0,1,2]),255,2,'FMAC-cancellation-witness'))
    rng=random.Random(0xbacface)
    for length in (0,1,2,3,4,7,31,64,127,255,256):
        for cull in (1,2):
            pts=[(rng.uniform(-1000,1000),rng.uniform(-1000,1000)) for _ in range(256)]
            ix=bytes(rng.randrange(128) for _ in range(length))
            cases.append((generated_cache(pts),ix,127,cull,'random'))
    special=[0.0,-0.0,2**-126,2**-149,1.0,-1.0,3.4028234663852886e38,math.inf,-math.inf,math.nan]
    for length in (16,64,127,255,256):
        for cull in (1,2):
            for mask in (127,255):
                count=min(length,128) if mask==127 else length
                pts=[(float(i),float((i&1)*2-1)) for i in range(count)]
                cases.append((generated_cache(pts),bytes(range(count)),mask,cull,'long-zigzag'))
    for v in special:
        for cull in (1,2):
            cases.append((generated_cache([(0,0),(v,1),(1,v),(1,1),(2,2)]),bytes(range(5)),255,cull,'nonfinite/edge'))
    for count in (300,1024,2048):
        ix=[]
        while len(ix)<count:
            size=min(rng.randrange(1,65),count-len(ix))
            part=[rng.randrange(128) for _ in range(size)];part[-1]|=128;ix.extend(part)
        cases.append((generated_cache([(rng.random()*640,rng.random()*480) for _ in range(128)]),bytes(ix),383,2,'whole-stream'))
    passed=0;counts={};maxsteps=0
    for cache,ix,mask,cull,kind in cases:
        expected=oracle(cache,ix,mask,cull)
        for trace in (0,1):
            # FR/SZ sentinels are exercised on representative cases below;
            # exhaustive run semantics use ordinary default C mode.
            machine=Machine(texts[trace],cache,ix,mask,cull,trace=bool(trace))
            try: actual=machine.run()
            except AssertionError as error:
                raise AssertionError((kind,trace,mask,cull,len(ix),str(error),list(machine.ring))) from error
            assert actual==expected,(kind,trace,mask,cull,len(ix),actual[1],expected[1])
            passed+=1;maxsteps=max(maxsteps,machine.steps)
        counts[kind]=counts.get(kind,0)+1
    cache=generated_cache([(i,float(i%3)) for i in range(32)])
    ix=bytes([0,1,2,3,4,133,6,7,8,9,10,139])
    modecases=0
    for fr,sz,pr,dn,trace in itertools.product((0,1),repeat=5):
        fpscr=(fr<<21)|(sz<<20)|(pr<<19)|(dn<<18)
        machine=Machine(texts[trace],cache,ix,383,2,fpscr,trace=bool(trace))
        assert machine.run()==oracle(cache,ix,383,2)
        modecases+=1
    ax,ay=0.0,0.0
    bx,by=570.0137939453125,438.41583251953125
    cx,cy=1140.027587890625,876.8316650390625
    product2=f32(f32(by-ay)*f32(cx-ax))
    strict=f32(f32(f32(bx-ax)*f32(cy-ay))-product2)
    fused=_fmaf(f32(bx-ax),f32(cy-ay),-product2)
    assert fbits(strict)==0 and fbits(fused)==0xbc480b30
    result=dict(arithmetic_witness=dict(strict_bits='00000000',target_fmac_bits='bc480b30',scope='host libm fmaf plus matching target-opcode execution'),scope='host interpretation of actual SH4 object opcodes plus original C template with target FMAC determinant lowering; no guest/hardware',
        cases=len(cases),per_case_trace_variants=2,comparisons=passed,case_groups=counts,
        fpscr_fr_sz_pr_dn_combinations=modecases,all_16_xf_sentinels_preserved=True,
        callee_registers_preserved=True,trace_hook_clobbers_checked=True,
        sq_bursts_complete=True,exact_emitted_words=True,max_interpreted_instructions=maxsteps,
        object_sha256={p.name:sha(p.read_bytes()) for p in args.objects.glob('*.o')},
        source_sha256=sha(Path(__file__).read_bytes()))
    args.report.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
