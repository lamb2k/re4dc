// Complete production emit_pick/chunk_emit/restart members are inserted by the
// runner. Only external resource/SH-4/PVR boundaries are deterministic host spies.
#include <algorithm>
#include <array>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <string>
#include <vector>
#define RE4DC_SCENERY_CHUNK 1
#define RE4DC_MESH_FASTPATH 1
#define RE4DC_MESH_DIRECT 1
#define RE4DC_PS2_WORLD_MESH 1
#define RE4DC_SCENERY_REPLAY_LEAN 1
#define RE4DC_SCENERY_SUBMIT_BATCH 1
#define RE4DC_MESH_PRIME_LAZY 1
#define RE4DC_PS2_WORLD_LEAN 23
#define RE4DC_SCN_CENSUS 1
#define RE4DC_WORLD_CENSUS24 1
#define RE4DC_WORLD_PORTAL_COMPLETION 1
#define RE4DC_WORLD_PORTAL_CLIP_GATHER31 1
#define RE4DC_PS2_PVS 1
#ifndef RE4DC_SCENERY_STREAM
#define RE4DC_SCENERY_STREAM 1
#endif
#ifndef RE4DC_WORLD_MUTATION31
#define RE4DC_WORLD_MUTATION31 1
#endif
#ifndef RE4DC_WORLD_EMPTY_PREP01
#define RE4DC_WORLD_EMPTY_PREP01 0
#endif
@WORLD_CONTROL_PRELUDE@
#include "world_portal29.hpp"

constexpr std::uint32_t PVR_CMD_VERTEX=0xe0000000U;
struct pvr_vertex_t {
    std::uint32_t flags=0;float x=0,y=0,z=0,u=0,v=0;std::uint32_t argb=0,oargb=0;
};
struct Calls {
    unsigned bind=0,header=0,owner=0,camera=0,gather=0,borrow=0,acquire=0,constants=0;
    unsigned prime=0,corners=0,package=0,transforms=0,mutation=0,strips=0;
    unsigned end=0,close=0,abort=0,results=0,pvs=0,commits=0;
    std::vector<std::uint32_t> ta;
} calls;
struct StaticStats { unsigned groups_visible=0,bind_rejects=0,batches=0,reserve_rejects=0,strips=0,strips_culled=0; } stats;
unsigned scn_cen[10]{};
unsigned package_generation=1;
bool invalidate_on_end=false;
bool worldPackageSelectionCurrent(unsigned expected){return package_generation==expected;}
void re4dc_model_packet_abort(){++calls.abort;}
void re4dc_model_packet_commit(unsigned){++calls.commits;}
void re4dc_model_result(unsigned,unsigned,unsigned){++calls.results;}

namespace re4dc {
namespace room {
struct CompactVertex12 { std::uint32_t id=0;std::uint32_t extra[2]{}; };
struct CompactBatch {float uv_bias[2]{},uv_scale[2]{};};
}
namespace wc24 {
enum Phase {Other,HeaderMaterial,Transform,Submit,Transformed};
struct Scope { explicit Scope(Phase){} void phase(Phase){} };
inline void count(Phase,unsigned){}
}
namespace vp {
using Vertex12=room::CompactVertex12;
constexpr unsigned kCacheSlots=264,kCacheEntries=256,kChecksAll=63;
struct Constants {
    float us,ub,uo,ut,vs,vb,vo,vt,near,far;
    unsigned and_mask,or_bits;const std::uint32_t* lut;struct F{} f;
    void finish(){++calls.constants;}
};
inline void prime(pvr_vertex_t* cache,unsigned n){
    calls.prime+=n;for(unsigned i=0;i<n;++i){cache[i].flags=PVR_CMD_VERTEX;cache[i].oargb=0;}
}
template<unsigned Checks>
inline void transform_sched(const Vertex12* in,unsigned n,pvr_vertex_t* cache,std::uint8_t* oc,const Constants&){
    static_assert(Checks==kChecksAll);
    calls.transforms+=n;
    for(unsigned i=0;i<n;++i){assert(cache[i].flags==PVR_CMD_VERTEX && cache[i].oargb==0);
        cache[i].argb=in[i].id;oc[i]=0;}
}
inline void transform_sched_ix(const Vertex12* base,const std::uint16_t* ix,unsigned n,
        pvr_vertex_t* cache,std::uint8_t* oc,const Constants&){
    calls.transforms+=n;
    for(unsigned i=0;i<n;++i){assert(cache[i].flags==PVR_CMD_VERTEX && cache[i].oargb==0);
        cache[i].argb=base[ix[i]].id;oc[i]=0;}
}
}
} // namespace re4dc
namespace lean {
constexpr unsigned kMode=23;
const pvr_vertex_t* prime_at=nullptr;unsigned primed=0;
struct {unsigned prime_reuse=0,prime_bad=0;} st;
}
struct Meshlet {unsigned first_vertex=0,vertex_count=64,strip_bytes=8;};
struct Package {
    Meshlet let;
    re4dc::room::CompactVertex12 data[64]{};
    std::uint16_t offsets[64]{};
    const std::uint8_t strips[8]={3,0,1,2,3,3,4,5};
    bool is_indexed=true;
    Package(){for(unsigned i=0;i<64;++i){data[i].id=1000+i;offsets[i]=std::uint16_t(63-i);}}
    const Meshlet* meshlets()const{++calls.package;return &let;}
    bool shared()const{return is_indexed;}
    bool indexed(const Meshlet&)const{++calls.package;return is_indexed;}
    const re4dc::room::CompactVertex12* vertices()const{++calls.package;return data;}
    const std::uint16_t* pool_offsets(const Meshlet&)const{++calls.package;return offsets;}
    const std::uint8_t* strip_begin(const Meshlet&)const{++calls.package;return strips;}
};
struct Part {float uv_bias[2]{},uv_scale[2]{1,1};} part;
struct Emitter {
    unsigned used=0,input=0,output=0,slots=0,limit=512;
    bool bound=false,submitted=false;
};
struct Spy : Emitter {
    struct Pick {std::uint16_t let;std::uint8_t nr,gmask,lo,hi;};
    Package package;
    struct {float uv_offset[2]{};} p;
    struct {float u_scale=1,v_scale=1;} packet;
    std::uint32_t lut_data[512]{};const std::uint32_t* lut=lut_data;
    pvr_vertex_t storage[512]{};
    pvr_vertex_t* dst=storage; pvr_vertex_t* cache=nullptr;
    std::uint8_t* outcodes=nullptr;
    re4dc::vp::Constants k{};
    re4dc::room::CompactBatch batch{};
    re4dc::room::CompactVertex12 gathering[64]{};
    re4dc::room::CompactVertex12* gather_pool=gathering;
    re4dc::room::CompactVertex12* gathered=nullptr;
    unsigned primed=0,alpha=0xff000000U;
    float near=1,far=1000;
    bool lean_part=true,vertex_alpha=false;
    const Meshlet* stream_l=nullptr;
    bool portal_depth_safe_clip=true;
    const std::uint8_t* portal_depth_outcodes=nullptr;
    unsigned pvs_pending[3]={~0U,~0U,0};
    std::uint16_t groups[16]{};
    const std::uint8_t* sg=reinterpret_cast<const std::uint8_t*>(groups);
    unsigned sg_groups=2;
    bool bind_failure=false,owner_failure=false,fail_after_header=false;
    bool invalidate_after_bind=false,gather_failure=false,scratch_failure=false;
    bool fail_after_first_strip=false,invalidate_after_strip=false;
    Spy(){groups[6]=4;groups[7]=0|(2<<8);groups[14]=8;groups[15]=3|(5<<8);}
    bool mutation_current(){++calls.mutation;return package_generation==1;}
    bool bind(){
        ++calls.bind;++calls.owner;
        if(owner_failure || bind_failure)return false;
        if(bound)return true;
        ++calls.camera;++calls.header;submitted=bound=true;
        calls.ta.push_back(0x48445200U);
        if(invalidate_after_bind)++package_generation;
        if(fail_after_header)return false;
        return true;
    }
    bool borrow_gather(){++calls.gather;if(gather_failure)return false;return borrow_gather_source();}
    bool borrow(){
        ++calls.borrow;if(scratch_failure)return false;
        const bool absent=cache==nullptr;const bool okay=borrow_source();
        if(okay && absent)++calls.acquire;
        return okay;
    }
    const re4dc::room::CompactVertex12* corners(const Meshlet& l){
        ++calls.corners;
        if(!package.is_indexed)return package.data;
        for(unsigned i=0;i<l.vertex_count;++i)gathering[i]=package.data[package.offsets[i]];
        return gathering;
    }
    void pvs_observed(const Meshlet&){++calls.pvs;}
    void strips_lean(const std::uint8_t* begin,const std::uint8_t* end,
            const re4dc::room::CompactVertex12*,const re4dc::room::CompactBatch&,int& result){
        for(auto at=begin;at<end;){
            const unsigned n=*at++;assert(n>=3 && at+n<=end);
            ++calls.strips;++stats.strips;
            calls.ta.push_back(0x53545200U|n);
            for(unsigned i=0;i<n;++i){assert(at[i]<package.let.vertex_count);calls.ta.push_back(cache[at[i]].argb);}
            at+=n;input+=n-2;output+=n-2;
            if(invalidate_after_strip)++package_generation;
            if(fail_after_first_strip){result=-1;return;}
        }
    }
    void end_direct(){++calls.end;if(invalidate_on_end)++package_generation;}
@WORLD_GEOMETRY_BORROW@
@WORLD_CONSUMER_MEMBERS@
};
void reset(){
    calls={};stats={};std::memset(scn_cen,0,sizeof scn_cen);
    package_generation=1;invalidate_on_end=false;lean::prime_at=nullptr;lean::primed=0;lean::st={};
}
int finish(Spy& e,const Spy::Pick* pk,unsigned n){
    const int result=e.chunk_emit(pk,n);
    struct Close {~Close(){++calls.close;}} close;
    struct {unsigned aborts=0;} c;
    unsigned nctx=1,npk=n;const unsigned draw_package_generation=1;
@WORLD_AFTER_END@
    if(result<0)re4dc_model_packet_abort();
    return result;
}
void json(const char* name,const Spy& e,int result,const Spy::Pick* pk,unsigned n){
    const auto completion=re4dc::portal29::Completion::emitted(result,e.submitted,e.input,e.output,
        re4dc::portal29::whole_source(pk,n,0,1));
    std::cout<<"{\"case\":\""<<name<<"\",\"result\":"<<result<<",\"submitted\":"<<e.submitted
        <<",\"input\":"<<e.input<<",\"output\":"<<e.output<<",\"completion\":"<<unsigned(completion.outcome)
        <<",\"witness\":"<<completion.witnessed()<<",\"bind\":"<<calls.bind<<",\"header\":"<<calls.header
        <<",\"owner\":"<<calls.owner<<",\"camera\":"<<calls.camera<<",\"gather\":"<<calls.gather
        <<",\"borrow\":"<<calls.borrow<<",\"acquire\":"<<calls.acquire<<",\"constants\":"<<calls.constants
        <<",\"prime\":"<<calls.prime<<",\"corners\":"<<calls.corners<<",\"package\":"<<calls.package
        <<",\"transforms\":"<<calls.transforms<<",\"mutation\":"<<calls.mutation<<",\"strips\":"<<calls.strips
        <<",\"end\":"<<calls.end<<",\"close\":"<<calls.close<<",\"abort\":"<<calls.abort
        <<",\"results\":"<<calls.results<<",\"pvs\":"<<calls.pvs<<",\"commits\":"<<calls.commits
        <<",\"groups_visible\":"<<stats.groups_visible<<",\"batches\":"<<stats.batches
        <<",\"bind_rejects\":"<<stats.bind_rejects<<",\"reserve_rejects\":"<<stats.reserve_rejects
        <<",\"census_empty_or_drawn\":"<<scn_cen[0]<<",\"census_corners\":"<<scn_cen[1]<<",\"ta\":[";
    for(unsigned i=0;i<calls.ta.size();++i){if(i)std::cout<<",";std::cout<<calls.ta[i];}
    std::cout<<"]}\n";
}
int main(){
    using Pick=Spy::Pick;
    const Pick empty{0,0,0,255,0},whole{0,0xff,0,0,0},subset{0,1,1,0,2};
    const auto one=[&](const char* name,const Pick& pick,auto configure){
        reset();Spy e;configure(e);const int result=finish(e,&pick,1);json(name,e,result,&pick,1);};
    const auto none=[](Spy&){};
    one("empty_indexed",empty,none);
    one("empty_plain",empty,[](Spy& e){e.package.is_indexed=false;});
    one("nonempty_indexed",whole,none);
    one("nonempty_plain",whole,[](Spy& e){e.package.is_indexed=false;});
    one("subset_indexed",subset,none);
    one("subset_plain",subset,[](Spy& e){e.package.is_indexed=false;});
    one("bind_refused_empty",empty,[](Spy& e){e.bind_failure=true;});
    one("owner_refused_empty",empty,[](Spy& e){e.owner_failure=true;});
    one("post_header_refused_empty",empty,[](Spy& e){e.fail_after_header=true;});
    one("pre_bind_mutation_empty",empty,[](Spy&){++package_generation;});
    one("post_bind_mutation_empty",empty,[](Spy& e){e.invalidate_after_bind=true;});
    one("scratch_exhausted_empty",empty,[](Spy& e){e.scratch_failure=true;});
    one("scratch_exhausted_live",whole,[](Spy& e){e.scratch_failure=true;});
    one("gather_unavailable_empty",empty,[](Spy& e){e.gather_failure=true;});
    one("gather_unavailable_live",whole,[](Spy& e){e.gather_failure=true;});
    one("partial_emit_failure",whole,[](Spy& e){e.fail_after_first_strip=true;});
    one("post_strip_mutation",whole,[](Spy& e){e.invalidate_after_strip=true;});
    one("post_end_mutation_empty",empty,[](Spy&){invalidate_on_end=true;});
    for(unsigned order=0;order<3;++order){
        reset();Spy e;
        const Pick pairs[3][2]={{empty,empty},{empty,whole},{whole,empty}};
        const char* names[3]={"two_empty_same_part","empty_then_live","live_then_empty"};
        const int result=finish(e,pairs[order],2);json(names[order],e,result,pairs[order],2);
    }
    // A following part must acquire/prime valid geometry state even when the
    // previous part ended empty. Restart uses the exact production member.
    reset();Spy next;
    assert(finish(next,&empty,1)==1);
    next.chunk_restart();next.limit=512;
    const int result=finish(next,&whole,1);json("empty_part_then_live_part",next,result,&whole,1);
}
