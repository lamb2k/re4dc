"""Host controls for actual actor caller bodies and trace words; not ASM execution."""
from pathlib import Path
import hashlib,json,subprocess,os
T=Path(__file__).resolve().parents[5];G=T/'port/dreamcast/game';O=Path(os.environ.get('BACKFACE_ACTOR_OUTPUT','/root/probe/codex-backface-sh4zam-actors-objects02/host-dispatch-sealed-v2'))
assert os.environ.get('D367_SLOT_HELD')=='1';assert not O.exists();O.mkdir()
s=(G/'platform/native_actor_fast.cpp').read_text()
# Select only the mutually exclusive opening brace for the CPU2 host body;
# all method statements still come from the actual caller source.
opening='#if RE4DC_CPU_BACKFACE == 2\n            if (bf_on()) {\n#else\n            if (p.cull == 1 || p.cull == 2) {\n#endif'
assert s.count(opening)==1;s=s.replace(opening,'            if (bf_on()) {')
def body(start):
 a=s.index(start);b=s.index('{',a);depth=1;c=b+1
 while depth:
  if s[c]=='{':depth+=1
  elif s[c]=='}':depth-=1
  c+=1
 return s[a:c]
methods='\n'.join(body(k)for k in ['bool bf_on() const','void strip(const u8* index, unsigned n)','void bf_send(const u8* index, unsigned n)','void bf_whole(const u8* index, unsigned n)','bool whole(const u8* index, unsigned count, unsigned triangles)'])
emit=body('inline std::uint32_t* emit_sq(');a=emit.index('for (unsigned k = 0; k < n; ++k) {');b=emit.index('\n    }',a)+6;trace_loop=emit[a:b]
tag_scope=s[s.index('    const unsigned bf_tag='):s.index('\n#endif',s.index('    const unsigned bf_tag='))]
native=s;s=(G/'model_bridge.cpp').read_text();tag_getter=body('extern "C" unsigned re4dc_backface_model_tag(');s=native
program=r'''
#include <cstdint>
#include <cstring>
#include <vector>
#include <cassert>
#include <cstdio>
#define RE4DC_ACTOR_DIRECT 1
#define RE4DC_CPU_BACKFACE 2
#define RE4DC_BACKFACE_CENSUS 1
#define RE4DC_COARSE_ONE_SUBMIT 1
#define RE4DC_ACTOR_MOVCA 1
#define RE4DC_TA_HASH 1
#include "include/bfc_class.h"
#include "../../room/backface_sh4.hpp"
using u8=std::uint8_t;
struct pvr_vertex_t {std::uint32_t words[8];};
constexpr std::uint32_t PVR_CMD_VERTEX=0xe0000000u,PVR_CMD_VERTEX_EOL=0xf0000000u;
extern "C" {volatile unsigned re4dc_bfc_class=0,re4dc_bfc_id=0;}
struct cModel {unsigned char kindid,id;};
TAG_GETTER
unsigned tagged_class,tagged_id;
void generic_tag(const void* model){struct{const void* model;}p{model};
TAG_SCOPE
tagged_class=re4dc_bfc_class;tagged_id=re4dc_bfc_id;
}
BackfaceSq seen{};unsigned calls=0,legacy_strip=0,legacy_mesh=0,seen_class=0,seen_id=0;
extern "C" void shz_strip_sq(BackfaceSq* c){seen=*c;++calls;seen_class=re4dc_bfc_class;seen_id=re4dc_bfc_id;c->sent=3;c->pieces=1;c->q+=24;}
std::uint32_t* emit_sq(std::uint32_t* q,const pvr_vertex_t*,const u8*,unsigned n){++legacy_strip;return q+8*n;}
template<bool SQ>void* emit_meshlet(void* q,const pvr_vertex_t*,const u8*,unsigned n){++legacy_mesh;return static_cast<std::uint32_t*>(q)+8*n;}
void emit(pvr_vertex_t*,const pvr_vertex_t*,const u8*,unsigned){}
struct Part {struct{unsigned cull=1,material_flags=0,depth_mode=0;}p;struct{pvr_vertex_t* v;}cache;bool direct=true;std::uint32_t* sq;unsigned slots=0,used=0,input=0,output=0;std::uint32_t slab[256]{};bool room(unsigned){return true;}pvr_vertex_t* at(){return reinterpret_cast<pvr_vertex_t*>(slab);}
METHODS
};
std::vector<std::uint32_t> hashed;
extern "C" void re4dc_ta_hash(const void* p,unsigned bytes){assert(bytes==32);auto*w=static_cast<const std::uint32_t*>(p);hashed.insert(hashed.end(),w,w+8);}
extern "C" void re4dc_backface_sh4_trace(const void*,const u8*,unsigned,unsigned);
void c_trace(const pvr_vertex_t* cache,const u8* index,unsigned n){const std::uint32_t eol=PVR_CMD_VERTEX_EOL;
TRACE_LOOP
}
int main(){
 pvr_vertex_t cache[128]{};std::uint32_t q[512]{};u8 ids[]={0,1,0x82,3,4,5,0x86};Part p;p.cache.v=cache;p.sq=q;
 re4dc_bfc_class=3;p.whole(ids,7,3);assert(calls==1&&legacy_mesh==0&&seen.n==7&&seen.mask==0x17f&&seen.cull==1&&seen.cache==cache&&seen.indices==ids&&p.slots==3&&p.sq==q+24&&seen_class==3&&re4dc_bfc_class==3);
 calls=0;re4dc_bfc_class=4;re4dc_bfc_id=0x10;p.p.cull=2;p.strip(ids,3);assert(calls==1&&seen.mask==127&&seen.n==3&&seen.cull==2&&seen_class==4&&seen_id==0x10);
 calls=0;re4dc_bfc_class=5;re4dc_bfc_id=0x2b;p.whole(ids,7,3);assert(calls==1&&seen_class==5&&seen_id==0x2b);
 calls=0;p.p.cull=0;p.whole(ids,7,3);assert(calls==0&&legacy_mesh==1);p.strip(ids,3);assert(calls==0&&legacy_strip==1);
 p.p.cull=1;p.direct=false;p.whole(ids,7,3);assert(calls==0&&legacy_mesh==2);p.direct=true;
 p.p.material_flags=4;p.whole(ids,7,3);p.strip(ids,3);assert(calls==0);p.p.material_flags=0;
 for(unsigned depth:{1u,2u}){p.p.depth_mode=depth;p.whole(ids,7,3);p.strip(ids,3);assert(calls==0);}p.p.depth_mode=0;
 re4dc_bfc_class=0;p.strip(ids,3);assert(seen_class==6&&re4dc_bfc_class==0);
 for(unsigned i=0;i<128;++i)for(unsigned j=0;j<8;++j)cache[i].words[j]=j?0x12340000u+i*8+j:0xdeadbeefu;
 c_trace(cache,ids,3);auto c=hashed;hashed.clear();re4dc_backface_sh4_trace(cache,ids,3,127);assert(c==hashed&&c.size()==24);
 for(unsigned i=0;i<3;++i){assert(c[i*8]==(i==2?PVR_CMD_VERTEX_EOL:PVR_CMD_VERTEX));for(unsigned j=1;j<8;++j)assert(c[i*8+j]==cache[i].words[j]);}
 hashed.clear();re4dc_backface_sh4_trace(cache,ids,3,0x17f);assert(c==hashed);
 for(cModel m: {cModel{0,0},cModel{0,0x15},cModel{0,0x2b}}){re4dc_bfc_class=0;re4dc_bfc_id=0;generic_tag(&m);assert(tagged_class==(m.id==0?3u:m.id==0x15?4u:5u)&&tagged_id==m.id&&re4dc_bfc_class==0&&re4dc_bfc_id==0);}
 cModel object{1,0x15};re4dc_bfc_class=6;re4dc_bfc_id=0x99;generic_tag(&object);assert(tagged_class==6&&tagged_id==0x99);generic_tag(nullptr);assert(tagged_class==6&&tagged_id==0x99);
 std::puts("PASS actual caller dispatch/whole EOL mask/source classes/material bypass/MOVCA trace exact words");
}
'''.replace('METHODS',methods).replace('TRACE_LOOP',trace_loop).replace('TAG_GETTER',tag_getter).replace('TAG_SCOPE',tag_scope)
p=O/'host.cpp';p.write_text(program);cmd=['g++','-std=c++20','-O2','-Wall','-Wextra','-I'+str(G/'platform'),'-I'+os.environ['BACKFACE_SDK_INCLUDE'],str(p),str(G/'platform/backface_sh4_trace.cpp'),'-o',str(O/'host')];r=subprocess.run(cmd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(O/'compile.log').write_text(r.stdout);assert r.returncode==0,r.stdout
r=subprocess.run([str(O/'host')],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);assert r.returncode==0,r.stdout
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();j=dict(scope=__doc__,source=sha(G/'platform/native_actor_fast.cpp'),model_bridge=sha(G/'model_bridge.cpp'),common_header=sha(T/'port/dreamcast/room/backface_sh4.hpp'),actual_trace=sha(G/'platform/backface_sh4_trace.cpp'),program=sha(p),stdout=r.stdout,compiler_command=cmd,CPU2_single_strip_mask127=True,CPU2_whole_meshlet_one_call_mask0x17f=True,no_C_boundary_scan=True,BFC_sourceclasses_and_restore=True,generic_deferred_typed_model_tag_and_restore=True,cullnone_and_nondirect_unchanged=True,MOVCA_C_trace_matches_ASM_trace=True,all_words1to7_preserved=True,limits='Host mock records common ASM ABI calls; real SH-4 kernel output/cycles and target pixels remain separate gates.')
(O/'RECEIPT.json').write_text(json.dumps(j,indent=2)+'\n');print(json.dumps(dict(receipt=sha(O/'RECEIPT.json'),stdout=r.stdout)))
