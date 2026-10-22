#!/usr/bin/env python3
"""Host controls for the diagnostic. Uses the real header and extracted real C caller.
No target object, game programme, asset, or guest is built by this script.
"""
import argparse, ctypes as C, hashlib, json, pathlib, random, re, subprocess
BASE='a2477bd2b4d2dc5354fe1bbcc5b5c6b45312928f'
TREE=pathlib.Path(__file__).resolve().parents[5]
DC=TREE/'port/dreamcast'
def digest(b): return hashlib.sha256(b).hexdigest()
def source(path): return (TREE/path).read_text()
def body(text, signature):
    start=text.index(signature); opening=text.index('{',start); depth=1; i=opening+1
    while depth:
        depth+=(text[i]=='{')-(text[i]=='}'); i+=1
    return text[start:i]
def run(out):
    out.mkdir(parents=True,exist_ok=False)
    stub=out/'dc'; stub.mkdir()
    (stub/'pvr.h').write_text('#pragma once\n#include <cstdint>\nstruct pvr_vertex_t { std::uint32_t flags; float x,y,z,u,v; std::uint32_t argb,oargb; };\nstatic_assert(sizeof(pvr_vertex_t)==32);\n')
    header=DC/'room/backface_emit.hpp'; original=subprocess.check_output(['git','-C',str(TREE),'show',BASE+':port/dreamcast/room/backface_emit.hpp'])
    (out/'original').mkdir(); (out/'original/backface_emit.hpp').write_bytes(original)
    native=source('port/dreamcast/game/platform/native_static.cpp')
    send=body(native,'    void bf_send('); walk=body(native,'    const std::uint8_t* strips_bf(')
    wrapper=r'''#include <cstdint>
#include <cstring>
#include <backface_emit.hpp>
namespace re4dc::room { struct CompactVertex12{}; struct CompactBatch{}; }
namespace re4dc::vp {
constexpr unsigned kChecksAll=15;
constexpr unsigned screen_mask(unsigned){return 0x3c;}
constexpr unsigned depth_mask(unsigned){return 3;}
struct StripCodes { unsigned all,any; };
inline StripCodes codes(const std::uint8_t* oc,const std::uint8_t* idx,unsigned n){
 StripCodes c{255,0}; for(unsigned i=0;i<n;++i){int v=std::int8_t(oc[idx[i]]);c.all&=v;c.any|=v;}return c;
}
inline std::uint32_t* emit_sq(std::uint32_t* q,const pvr_vertex_t* c,const std::uint8_t* idx,unsigned n){
 for(unsigned i=0;i<n;++i){std::memcpy(q,c+idx[i],32);if(i+1==n)q[0]=0xf0000000;q+=8;}return q;
}
}
extern "C" unsigned capture(const pvr_vertex_t* cache,const std::uint8_t* idx,unsigned n,unsigned mask,unsigned cull,std::uint32_t* out,unsigned* pieces){
 unsigned count=0; unsigned sent=re4dc::bf::strip(cache,idx,n,mask,cull,[&](const std::uint8_t* p,unsigned k){pieces[count++]=k;out=re4dc::vp::emit_sq(out,cache,p,k);});pieces[256]=count;return sent;
}
struct World {
 const pvr_vertex_t* cache;const std::uint8_t* outcodes;std::uint32_t* sq;
 unsigned slots=0,input=0,output=0,limit; struct {unsigned cull;}p;
 struct {unsigned vertices=0,strips_culled=0,strips=0;}stats;
 int clip_rc;unsigned clips=0,clip_n=0,clip_offset=0;const std::uint8_t* begin;
 int clip_strip(const re4dc::room::CompactVertex12*,const re4dc::room::CompactBatch&,const std::uint8_t* s,unsigned n){++clips;clip_n=n;clip_offset=s-begin;return clip_rc;}
SEND
WALK
};
extern "C" void caller(const pvr_vertex_t* cache,const std::uint8_t* oc,const std::uint8_t* stream,unsigned len,unsigned limit,unsigned cull,int cliprc,std::uint32_t* out,unsigned* result){
 World w{cache,oc,out,0,0,0,limit,{cull},{},cliprc,0,0,0,stream};int rc=-99;re4dc::room::CompactBatch batch;
 auto* stop=w.strips_bf(stream,stream+len,nullptr,batch,rc);
 unsigned values[]={w.slots,w.input,w.output,w.stats.vertices,w.stats.strips_culled,w.stats.strips,w.clips,w.clip_n,w.clip_offset,unsigned(rc),unsigned(stop!=nullptr)};
 std::memcpy(result,values,sizeof values);
}
'''.replace('SEND',send).replace('WALK',walk)
    (out/'wrapper.cpp').write_text(wrapper)
    libs={}; commands=[]
    for arm,inc,flag in [('original',out/'original',[]),('probe0',DC/'room',[]),('keepall',DC/'room',['-DRE4DC_BACKFACE_KEEP_ALL=1'])]:
        cmd=['g++','-std=c++20','-O2','-shared','-fPIC','-fno-fast-math','-ffp-contract=off','-I'+str(out),'-I'+str(inc),*flag,str(out/'wrapper.cpp'),'-o',str(out/(arm+'.so'))]
        subprocess.run(cmd,check=True);commands.append(cmd)
        lib=C.CDLL(str(out/(arm+'.so')))
        lib.capture.argtypes=[C.c_void_p,C.c_void_p,C.c_uint,C.c_uint,C.c_uint,C.c_void_p,C.c_void_p];lib.capture.restype=C.c_uint
        lib.caller.argtypes=[C.c_void_p,C.c_void_p,C.c_void_p,C.c_uint,C.c_uint,C.c_uint,C.c_int,C.c_void_p,C.c_void_p]
        libs[arm]=lib
    # Default-off preprocessed template is exactly the original after comments/line markers.
    pp=[]
    for inc in (out/'original',DC/'room'):
        pp.append(subprocess.check_output(['g++','-E','-P','-std=c++20','-I'+str(out),'-I'+str(inc),str(out/'wrapper.cpp')]))
    assert pp[0]==pp[1]
    rng=random.Random(0x57414c4b); cache=(C.c_uint32*(256*8))()
    import struct
    bits=lambda f:struct.unpack('<I',struct.pack('<f',f))[0]
    for i in range(256):
        words=[0xe0000000,bits(rng.uniform(-64,64)),bits(rng.uniform(-64,64)),rng.getrandbits(32),rng.getrandbits(32),rng.getrandbits(32),rng.getrandbits(32),rng.getrandbits(32)]
        for j,v in enumerate(words):cache[8*i+j]=v
    def capture(lib,idx,n,mask,cull):
        inp=(C.c_uint8*max(1,len(idx)))(*idx);outwords=(C.c_uint32*(4096*8))(*([0xdeadbeef]*(4096*8)));pieces=(C.c_uint*257)()
        sent=lib.capture(cache,inp,n,mask,cull,outwords,pieces)
        assert outwords[sent*8]==0xdeadbeef
        return list(outwords[:sent*8]),list(pieces[:pieces[256]]),sent
    def expected(indices):
        result=[]
        for i,x in enumerate(indices):
            words=list(cache[x*8:x*8+8]);words[0]=0xf0000000 if i+1==len(indices) else words[0];result+=words
        return result
    strip_cases=0
    for n in range(256):
      for mask in (0x7f,0xff):
       idx=[rng.randrange(256) for _ in range(n)]
       for cull in (1,2):
        base=capture(libs['original'],idx,n,mask,cull)
        assert capture(libs['probe0'],idx,n,mask,cull)==base
        actual=capture(libs['keepall'],idx,n,mask,cull)
        assert actual==(expected([x&mask for x in idx]) if n>=3 else [],[n] if n>=3 else [],n if n>=3 else 0)
        strip_cases+=1
    # Keep-all must copy nonfinite XY and all attribute bits without attempting facing.
    cache[1]=0x7fc12345;cache[2]=0xff800000
    assert capture(libs['keepall'],[0,255,0],3,255,1)==(expected([0,255,0]),[3],3)
    # Caller controls use the unedited C caller body; clipping is an observed continuation stub.
    def caller_case(strips,oc,limit,cliprc=1):
        stream=[]
        for idx in strips:stream += [len(idx)]+idx
        inp=(C.c_uint8*max(1,len(stream)))(*stream);codes=(C.c_uint8*256)(*oc);outwords=(C.c_uint32*(8192*8))(*([0xdeadbeef]*(8192*8)));result=(C.c_uint*11)()
        libs['keepall'].caller(cache,codes,inp,len(stream),limit,1,cliprc,outwords,result)
        vals=[0,0,0,0,0,0,0,0,0,1,0];want=[];offset=0
        for idx in strips:
            n=len(idx);vals[1]+=n-2;allcode=255;anycode=0
            for x in idx:allcode&=oc[x];anycode|=oc[x]
            if allcode&3:vals[3]+=n;vals[4]+=1
            elif anycode&3 or n>limit:
                if n<=limit:vals[3]+=n
                vals[6]+=1;vals[7]=n;vals[8]=offset+1
                if cliprc<=0:vals[9]=cliprc&0xffffffff;break
            else:
                vals[3]+=n
                if allcode&0x3c:vals[4]+=1
                else:vals[0]+=n;vals[2]+=n-2;vals[5]+=1;want+=expected(idx)
            offset+=n+1
        assert list(result)==vals,(strips,limit,cliprc,list(result),vals)
        assert list(outwords[:len(want)])==want
        assert outwords[len(want)]==0xdeadbeef
    caller_cases=0
    # Every count/limit edge, screen/depth ordering, each interior crossing, signed outcodes.
    for n in (3,4,31,32,63,64,127,128,254,255):
      indices=list(range(n))
      patterns=[([0]*256,255),([1]*256,255),([4]*256,255),([0x84]*256,255),([0]*256,n-1),([1]*256,n-1),([4]*256,n-1)]
      for at in sorted(set([0,1,n//2,n-1])):
        codes=[0]*256;codes[at]=1;patterns.append((codes,255));patterns.append((codes,n-1))
      for codes,limit in patterns:
       for rc in (-1,0,1):caller_case([indices,[2,1,0]],codes,limit,rc);caller_cases+=1
    for _ in range(256):
        strips=[[rng.randrange(256) for _ in range(rng.randrange(3,65))] for _ in range(rng.randrange(1,10))]
        codes=[rng.choice([0,0,0,1,2,4,8,0x80,0xfc]) for _ in range(256)]
        caller_case(strips,codes,rng.choice([3,31,64,255]),rng.choice([-1,0,1]));caller_cases+=1
    # Empty caller batch is legal; zero/one/two count bytes are invalid upstream strip streams.
    caller_case([], [0]*256,255);caller_cases+=1
    report=dict(base=BASE,header_sha256=digest(header.read_bytes()),native_static_sha256=digest(native.encode()),extracted_send_sha256=digest(send.encode()),extracted_walk_sha256=digest(walk.encode()),strip_cases=strip_cases,nonfinite_keep_all_cases=1,caller_cases=caller_cases,default_preprocessed_template_identical=True,commands=commands,limits=['Host-only exact words/order and original-header equivalence; no target-FMAC or hardware claim.','Actual C caller extracted verbatim; codes and SQ copying use portable faithful stubs. Clip continuation is observed, not a host build of the real clipper.','n0/1/2 tested only at bf::strip entry; caller stream format requires n>=3. Oversize means n>limit, not count>255.'])
    (out/'host-receipt.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ('commands',)},indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=pathlib.Path,required=True);a=p.parse_args();run(a.output.resolve())
