
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
extern "C" unsigned re4dc_backface_model_tag(const void* model) {
    const auto* m=static_cast<const cModel*>(model);
    if(!m || m->kindid!=0)return 0;
    const unsigned id=unsigned(m->id);
    return ((id==0?3u:(id>=0x10 && id<=0x20)?4u:5u)<<8)|id;
}
unsigned tagged_class,tagged_id;
void generic_tag(const void* model){struct{const void* model;}p{model};
    const unsigned bf_tag=re4dc_backface_model_tag(p.model);
    RE4DC_BFC_SCOPE(bf_tag?bf_tag>>8:unsigned(re4dc_bfc_class),bf_tag?bf_tag&255u:unsigned(re4dc_bfc_id));
tagged_class=re4dc_bfc_class;tagged_id=re4dc_bfc_id;
}
BackfaceSq seen{};unsigned calls=0,legacy_strip=0,legacy_mesh=0,seen_class=0,seen_id=0;
extern "C" void shz_strip_sq(BackfaceSq* c){seen=*c;++calls;seen_class=re4dc_bfc_class;seen_id=re4dc_bfc_id;c->sent=3;c->pieces=1;c->q+=24;}
std::uint32_t* emit_sq(std::uint32_t* q,const pvr_vertex_t*,const u8*,unsigned n){++legacy_strip;return q+8*n;}
template<bool SQ>void* emit_meshlet(void* q,const pvr_vertex_t*,const u8*,unsigned n){++legacy_mesh;return static_cast<std::uint32_t*>(q)+8*n;}
void emit(pvr_vertex_t*,const pvr_vertex_t*,const u8*,unsigned){}
struct Part {struct{unsigned cull=1,material_flags=0,depth_mode=0;}p;struct{pvr_vertex_t* v;}cache;bool direct=true;std::uint32_t* sq;unsigned slots=0,used=0,input=0,output=0;std::uint32_t slab[256]{};bool room(unsigned){return true;}pvr_vertex_t* at(){return reinterpret_cast<pvr_vertex_t*>(slab);}
bool bf_on() const {
        // Generic/source submissions need the same material exclusions as
        // owned runs. Preserve their original copy/header for these parts.
        return (p.cull == 1 || p.cull == 2) && !(p.material_flags & 4u) && p.depth_mode == 0;
    }
void strip(const u8* index, unsigned n) {
#if RE4DC_ACTOR_DIRECT
#if RE4DC_COARSE_ONE_SUBMIT == 2
        if (direct) one_tap_strip(cache.v, index, n);
#endif
#if defined(RE4DC_CPU_BACKFACE) && RE4DC_CPU_BACKFACE
#if RE4DC_CPU_BACKFACE == 2
        if (direct && bf_on()) { bf_send(index, n); return; }
#else
        if (direct && (p.cull == 1 || p.cull == 2)) { bf_send(index, n); return; }
#endif
#endif
        if (direct) { sq = emit_sq(sq, cache.v, index, n); slots += n; return; }
#endif
        emit(at(), cache.v, index, n); used += n;
    }
void bf_send(const u8* index, unsigned n) {
#if RE4DC_CPU_BACKFACE == 2
#if defined(RE4DC_BACKFACE_CENSUS) && RE4DC_BACKFACE_CENSUS
        RE4DC_BFC_SCOPE((re4dc_bfc_class>=3u && re4dc_bfc_class<=5u)?unsigned(re4dc_bfc_class):6u,unsigned(re4dc_bfc_id));
#endif
        // An unclipped strip: assembly classifies and emits its kept runs;
        // mask127 removes the actor EOL bit from every cache lookup.
        slots += re4dc::bf::strip_sq(cache.v, index, n, 127u, p.cull, sq);
#else
        slots += re4dc::bf::strip(cache.v, index, n, 127u, p.cull,
                                  [&](const std::uint8_t* i, unsigned c) { sq = emit_sq(sq, cache.v, i, c); });
#endif
    }
void bf_whole(const u8* index, unsigned n) {
#if defined(RE4DC_BACKFACE_CENSUS) && RE4DC_BACKFACE_CENSUS
        RE4DC_BFC_SCOPE((re4dc_bfc_class>=3u && re4dc_bfc_class<=5u)?unsigned(re4dc_bfc_class):6u,unsigned(re4dc_bfc_id));
#endif
        // One whole-meshlet call retains the assembly index/SQ walk. The
        // kernel resets strip parity at bit7 EOL (mask0x17f); no C scan.
        slots += re4dc::bf::stream_sq(cache.v, index, n, p.cull, sq);
    }
bool whole(const u8* index, unsigned count, unsigned triangles) {
        if (!room(count)) return false;
#if RE4DC_ACTOR_DIRECT
        if (direct) {
#if RE4DC_COARSE_ONE_SUBMIT == 2
            one_tap_meshlet(cache.v, index, count);
#endif
#if defined(RE4DC_CPU_BACKFACE) && RE4DC_CPU_BACKFACE
            if (bf_on()) {
#if RE4DC_CPU_BACKFACE == 2
                bf_whole(index, count);
#else
                // the meshlet's strips (bit 7 = the strip's last index), each through the back-face split
                unsigned a = 0;
                for (unsigned k = 0; k < count; ++k)
                    if (index[k] & 128u) { bf_send(index + a, k + 1 - a); a = k + 1; }
                if (a < count) bf_send(index + a, count - a);
#endif
                input += triangles; output += triangles;
                return true;
            }
#endif
            sq = static_cast<std::uint32_t*>(emit_meshlet<true>(sq, cache.v, index, count)); slots += count;
        } else
#endif
        { emit_meshlet<false>(at(), cache.v, index, count); used += count; }
        input += triangles; output += triangles;
        return true;
    }
};
std::vector<std::uint32_t> hashed;
extern "C" void re4dc_ta_hash(const void* p,unsigned bytes){assert(bytes==32);auto*w=static_cast<const std::uint32_t*>(p);hashed.insert(hashed.end(),w,w+8);}
extern "C" void re4dc_backface_sh4_trace(const void*,const u8*,unsigned,unsigned);
void c_trace(const pvr_vertex_t* cache,const u8* index,unsigned n){const std::uint32_t eol=PVR_CMD_VERTEX_EOL;
for (unsigned k = 0; k < n; ++k) {
        std::uint32_t w[8];
        __builtin_memcpy(w, cache + (index[k] & 127u), 32);
#if RE4DC_ACTOR_MOVCA
        // MOVCA leaves cache word0 unprimed; hash the command the SQ loop
        // actually writes, matching CPU_BACKFACE=2's actor trace.
        w[0] = k + 1 == n ? eol : PVR_CMD_VERTEX;
#else
        if (k + 1 == n) w[0] = eol;
#endif
        re4dc_ta_hash(w, 32);
    }
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
