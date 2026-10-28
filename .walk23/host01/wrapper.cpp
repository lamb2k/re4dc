#include <cstdint>
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
    void bf_send(const std::uint8_t* s,unsigned n){
        slots+=re4dc::bf::strip(cache,s,n,0xffU,p.cull,[&](const std::uint8_t* i,unsigned c){sq=re4dc::vp::emit_sq(sq,cache,i,c);});
    }
    const std::uint8_t* strips_bf(const std::uint8_t* s,const std::uint8_t* end,const re4dc::room::CompactVertex12* base,
                                  const re4dc::room::CompactBatch& batch,int& result){
        namespace vp=re4dc::vp;
        constexpr unsigned screen=vp::screen_mask(vp::kChecksAll),depth=vp::depth_mask(vp::kChecksAll);
        while(s<end){
            const unsigned n=*s++;
            input+=n-2;
            const vp::StripCodes c=vp::codes(outcodes,s,n);
            if(c.all&depth){stats.vertices+=n;++stats.strips_culled;s+=n;continue;}
            if((c.any&depth) || n>limit){
                if(n<=limit)stats.vertices+=n;
                result=clip_strip(base,batch,s,n);
                if(result<=0)return nullptr;
            }else{
                stats.vertices+=n;
                if(c.all&screen)++stats.strips_culled;
                else{bf_send(s,n);output+=n-2;++stats.strips;}
            }
            s+=n;
        }
        result=1;return nullptr;
    }
};
extern "C" void caller(const pvr_vertex_t* cache,const std::uint8_t* oc,const std::uint8_t* stream,unsigned len,unsigned limit,unsigned cull,int cliprc,std::uint32_t* out,unsigned* result){
 World w{cache,oc,out,0,0,0,limit,{cull},{},cliprc,0,0,0,stream};int rc=-99;re4dc::room::CompactBatch batch;
 auto* stop=w.strips_bf(stream,stream+len,nullptr,batch,rc);
 unsigned values[]={w.slots,w.input,w.output,w.stats.vertices,w.stats.strips_culled,w.stats.strips,w.clips,w.clip_n,w.clip_offset,unsigned(rc),unsigned(stop!=nullptr)};
 std::memcpy(result,values,sizeof values);
}
