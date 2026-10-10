// PS2_WORLD_DRAW=1: full authored r101 world; isolated presentation candidate.
// Original collision, object/event lifecycles and gameplay do not use this data.
#ifndef RE4DC_PS2_WORLD_DRAW
#define RE4DC_PS2_WORLD_DRAW 0
#endif
#ifndef RE4DC_PS2_WORLD_MESH
#define RE4DC_PS2_WORLD_MESH 0
#endif
#ifndef RE4DC_PS2_WORLD_KERNEL
#define RE4DC_PS2_WORLD_KERNEL 0
#endif
#define RE4DC_PS2_NEAR_ONLY (RE4DC_PS2_WORLD_KERNEL==3 || RE4DC_PS2_WORLD_KERNEL==4)
#ifndef RE4DC_PS2_WORLD_COLOR_ALL
#define RE4DC_PS2_WORLD_COLOR_ALL 0
#endif
#if RE4DC_PS2_WORLD_DRAW
#include "re4dc_screen.h"
#include <kos/fs.h>
#include <fcntl.h>
#include <dc/pvr.h>
#include <cmath>
#include "native_render_profile.hpp"
#include "include/native_ps2_world.h"
// FOG_FAR_CAP (post30.mk, look study 2026-10-10): the PS2 world's 25 m cap follows FOG_FAR.
#ifdef RE4DC_FAR_CAP
#define RE4DC_PS2_FAR RE4DC_FAR_CAP
#else
#define RE4DC_PS2_FAR 25000
#endif
#include "include/native_model.h"
#include "../../room/ps2_source_owner.hpp"
extern "C" void* re4dc_static_alloc(unsigned);
extern "C" void re4dc_static_free(void*);
extern "C" int re4dc_static_heap_free();
extern "C" unsigned re4dc_ui_frame();
extern "C" void re4dc_log(const char*,...);
#if defined(RE4DC_MEMPROF) && RE4DC_MEMPROF
extern "C" void re4dc_memprof_log(unsigned frame,unsigned frames); // platform/memprof.cpp
#endif
extern "C" int re4dc_room4_state(unsigned*,unsigned*,unsigned*,unsigned*,unsigned*);
extern "C" void re4dc_profile_source(re4dc::profile::Source*);
extern "C" int re4dc_ps2_world_packet(unsigned,unsigned,unsigned,unsigned,unsigned,Re4dcModelPacket*);
#if RE4DC_PS2_WORLD_KERNEL==4
extern "C" int re4dc_ps2_world_packet_cull(unsigned,unsigned,unsigned,unsigned,unsigned,unsigned,Re4dcModelPacket*);
#endif

namespace re4dc { namespace room { namespace ps2 {
namespace {
#include "include/ps2_world_data.inc"
int open_file(void*,const char* p){return int(fs_open(p,O_RDONLY));}
std::int64_t file_size(void*,int f){return fs_total(file_t(f));}
std::ptrdiff_t read_file(void*,int f,void* p,std::size_t n){return fs_read(file_t(f),p,n);}
void close_file(void*,int f){fs_close(file_t(f));}
void* allocate(void*,std::size_t n){return n<=UINT32_MAX?re4dc_static_alloc(unsigned(n)):nullptr;}
void release(void*,void* p){re4dc_static_free(p);}
bool current(void*,Owner& o){
    unsigned generation=0,c,b,s,r;
    const bool live=re4dc_room4_state(&generation,&c,&b,&s,&r)!=0;
    o.generation=generation;
    re4dc::profile::Source source{};re4dc_profile_source(&source);o.room=source.room;return live;
}
SourceOwner& storage(){static SourceOwner owner({nullptr,open_file,file_size,read_file,close_file,allocate,release,current});return owner;}
struct Counters {unsigned groups=0,reject_groups=0,input=0,output=0,packets=0,failed=0,clipped=0,culls=0;};
struct Frame {
    Owner owner{},attempted{};float screen[3][4]{},far=25000;
    unsigned frame=~0u,flushed=~0u,fallbacks=0;bool pending=false;
    Counters count[3];
} state;
int fallback(unsigned reason){
    ++state.fallbacks;const unsigned frame=re4dc_ui_frame();
    if(state.fallbacks<=4 || !(frame%120))re4dc_log("PS2WORLD fallback frame=%u reason=%u count=%u collision_piece0=kept\n",frame,reason,state.fallbacks);
    return 0;
}
struct Vertex {float x,y,w,u,v,r,g,b,a;};
float clamp(float f){return f<0?0:f>1?1:f;}
unsigned channel(float f){return unsigned(clamp(f)*255.0f+0.5f);}
unsigned color(const Vertex& v){return channel(v.a)<<24|channel(v.r)<<16|channel(v.g)<<8|channel(v.b);}
float distance(const Vertex& v,unsigned plane){
    switch(plane){case 0:return v.w-40;case 1:return state.far-v.w;case 2:return v.x;
        case 3:return RE4DC_SCREEN_W*v.w-v.x;case 4:return v.y;default:return RE4DC_SCREEN_H*v.w-v.y;}
}
Vertex interpolate(const Vertex& a,const Vertex& b,float t){
    return {a.x+t*(b.x-a.x),a.y+t*(b.y-a.y),a.w+t*(b.w-a.w),
        a.u+t*(b.u-a.u),a.v+t*(b.v-a.v),a.r+t*(b.r-a.r),
        a.g+t*(b.g-a.g),a.b+t*(b.b-a.b),a.a+t*(b.a-a.a)};
}
void normal_light(unsigned placement,const PlacementRecord& p,const std::int16_t* pos,const std::int16_t* normal,float factor,float* rgb){
    // Reproduce the reviewed GC cut0 sun/sky reference, not an invented PS2 light claim.
    const auto& ref=ps2_reference_lighting[placement-79];float world[3],n[3];
    for(unsigned r=0;r<3;++r){
        world[r]=p.affine[r][3];n[r]=0;
        for(unsigned c=0;c<3;++c){world[r]+=p.affine[r][c]*(pos[c]*factor);n[r]+=ref.rotation[r*3+c]*normal[c];}
        rgb[r]=ps2_ambient[r];
    }
    const float norm=std::sqrt(n[0]*n[0]+n[1]*n[1]+n[2]*n[2]);
    if(norm>0)for(auto& x:n)x/=norm;
    for(const auto& l:ref.lights){
        float d[3];for(unsigned c=0;c<3;++c)d[c]=l.pos[c]-world[c];
        const float len=std::sqrt(d[0]*d[0]+d[1]*d[1]+d[2]*d[2]);
        if(len<=0)continue;
        for(auto& x:d)x/=len;
        float cosine=d[0]*l.dir[0]+d[1]*l.dir[1]+d[2]*l.dir[2];if(cosine<0)cosine=0;
        float dot=n[0]*d[0]+n[1]*d[1]+n[2]*d[2];if(dot<0)dot=0;
        float num=l.a[0]+l.a[1]*cosine+l.a[2]*cosine*cosine;if(num<0)num=0;
        const float den=l.k[0]+l.k[1]*len+l.k[2]*len*len;
        if(den>0)for(unsigned c=0;c<3;++c)rgb[c]+=l.col[c]*num/den*dot;
    }
    for(unsigned c=0;c<3;++c)rgb[c]=clamp(rgb[c]);
}
#if RE4DC_PS2_WORLD_KERNEL
// PS2_WORLD_KERNEL=1: the coarse-world kernel shape on the PS2 package (render only).
// A group is rejected only when the old eight-corner test would reject it too, and takes
// the fast path only when every box point is inside all six planes by more than the old
// margin, so the clipper would pass its triangles through unchanged. Fast-path vertices
// use the same float expressions as vertex()/triangle() (-ffp-contract=off), so the
// emitted words are identical. =2 also runs the old tests and counts any disagreement.
struct Projected {float x,y,z,u,v;unsigned argb,out;};
struct KernelCounters {unsigned inside=0,crossing=0,unsafe=0,extra=0,badin=0,badcolor=0,range_reject=0,range_inside=0,badrange=0,strips=0,strip_vertices=0,long_strips=0;};
KernelCounters kernel[3];
// Static reference lighting: the NORMAL placements' packed corner colours, built once per
// adopted owner (the light, the package and the texture gains are constants).
// Also each range's bound: the union of its groups' boxes (a contained box's margin is never
// larger, so a range verdict of reject/inside holds for every group in it).
struct RangeBound {std::uint16_t first_group,group_count;std::int16_t minimum[3],maximum[3];std::uint16_t valid,reserved;};
// Clusters: the union box of each run of 8 consecutive groups in a range (same containment rule).
struct ClusterBox {std::int16_t minimum[3],maximum[3];};
constexpr unsigned kCluster=8;
struct LightCache {Owner owner{};std::uint32_t* offset=nullptr;std::uint32_t* argb=nullptr;RangeBound* bounds=nullptr;
    ClusterBox* clusters=nullptr;std::uint32_t* cluster_first=nullptr;unsigned corners=0,bytes=0;bool tried=false,groups_ok=false;} light_cache;
void light_cache_free(){
    if(light_cache.offset)re4dc_static_free(light_cache.offset);
    light_cache=LightCache{};
}
#endif
}

// The only friend of the package/owner. Borrowed pool addresses are used inside
// this synchronous call only; Frame stores copied camera/identity scalars.
class WorldDraw {
    SourceOwner& source_;const SpanPackage& package_;
    bool live() const {return source_.live() && same_owner(state.owner,source_.owner_);}
    template<class T>T record(Section section,unsigned index) const{return package_.record<T>(section,index);}
    const std::uint8_t* at(unsigned offset)const{return package_.payload_.data+offset;}
    static void compose(const PlacementRecord& p,float factor,float screen[3][4]){
        for(unsigned r=0;r<3;++r){
            for(unsigned c=0;c<3;++c){screen[r][c]=0;for(unsigned k=0;k<3;++k)screen[r][c]+=state.screen[r][k]*p.affine[k][c]*factor;}
            screen[r][3]=state.screen[r][3];for(unsigned k=0;k<3;++k)screen[r][3]+=state.screen[r][k]*p.affine[k][3];
        }
    }
    static bool reject(const OrderedBoundRecord& g,const float screen[3][4]){
        unsigned mask=63;
        for(unsigned bits=0;bits<8;++bits){
            Vertex v{};float xyz[3];
            for(unsigned r=0;r<3;++r){xyz[r]=screen[r][3];for(unsigned c=0;c<3;++c)xyz[r]+=screen[r][c]*((bits&(1u<<c))?g.maximum[c]:g.minimum[c]);}
            v.x=xyz[0];v.y=xyz[1];v.w=xyz[2];
            // Inflate the rejection boundary for SH4 float composition/rounding.
            // This only admits extra work; the triangle clipper remains authoritative.
            const float margin=32+(std::fabs(v.x)+std::fabs(v.y)+RE4DC_SCREEN_W*std::fabs(v.w))*0.00001f;
            unsigned outside=0;for(unsigned k=0;k<6;++k)if(distance(v,k)<-margin)outside|=1u<<k;
            mask&=outside;
        }
        return mask!=0;
    }
    Vertex vertex(const TemplateRecord& t,const PlacementRecord& p,const float screen[3][4],const Ps2Texture& texture,unsigned corner) const{
        const auto* c=at(t.corner.offset+corner*6);const auto* pos=at(t.position.offset+(u16(c)&0x7fff)*6);
        const auto* uv=at(t.uv.offset+u16(c+2)*4);const auto* attr=at(t.attribute.offset+u16(c+4)*(t.attribute_kind?6:4));
        std::int16_t q[3]={i16(pos),i16(pos+2),i16(pos+4)};Vertex v{};float xyz[3];
        for(unsigned r=0;r<3;++r){xyz[r]=screen[r][3];for(unsigned j=0;j<3;++j)xyz[r]+=screen[r][j]*q[j];}
        v.x=xyz[0];v.y=xyz[1];v.w=xyz[2];
        v.u=i16(uv)*(1.0f/256);v.v=i16(uv+2)*(1.0f/256);
        float rgb[3];
        if(t.attribute_kind){std::int16_t n[3]={i16(attr),i16(attr+2),i16(attr+4)};normal_light(p.placement,p,q,n,t.factor,rgb);v.a=1;}
        else {for(unsigned j=0;j<3;++j)rgb[j]=attr[j]*(1.0f/128);v.a=attr[3]*(1.0f/128);}
        v.r=clamp(rgb[0]*texture.gain[0]);v.g=clamp(rgb[1]*texture.gain[1]);v.b=clamp(rgb[2]*texture.gain[2]);
        return v;
    }
    static unsigned triangle(const Vertex& a,const Vertex& b,const Vertex& c,unsigned cull,pvr_vertex_t* output,Counters& stats){
        ++stats.input;Vertex aa[12]={a,b,c},bb[12];Vertex* in=aa;Vertex* out=bb;unsigned count=3;
        for(unsigned plane=0;plane<6 && count;++plane){
            unsigned next=0;Vertex prev=in[count-1];float pd=distance(prev,plane);
            for(unsigned i=0;i<count;++i){const Vertex now=in[i];const float nd=distance(now,plane);
                if((pd<0)!=(nd<0))out[next++]=interpolate(prev,now,pd/(pd-nd));
                if(nd>=0)out[next++]=now;
                prev=now;pd=nd;
            }
            count=next;Vertex* swap=in;in=out;out=swap;
        }
        if(count<3){++stats.clipped;return 0;}
        if(count!=3)++stats.clipped;
        unsigned written=0;
        for(unsigned j=1;j+1<count;++j){
            const Vertex* v[3]={in,in+j,in+j+1};float x[3],y[3],z[3];
            for(unsigned k=0;k<3;++k){z[k]=1/v[k]->w;x[k]=v[k]->x*z[k];y[k]=v[k]->y*z[k];}
            const float area=(x[1]-x[0])*(y[2]-y[0])-(y[1]-y[0])*(x[2]-x[0]);
            if((cull==0 && area>=0)||(cull==1 && area<=0)||area==0){++stats.culls;continue;}
            for(unsigned k=0;k<3;++k)output[written++]={k==2?PVR_CMD_VERTEX_EOL:PVR_CMD_VERTEX,x[k],y[k],z[k],v[k]->u,v[k]->v,color(*v[k]),0};
        }
        return written;
    }
public:
    explicit WorldDraw(SourceOwner& owner):source_(owner),package_(owner.package_){}
    bool qualified()const{
        if(!source_.live())return false;
        const auto& h=package_.header_;
        if(h.base.payload_crc32!=ps2_payload_crc || h.base.triangle_count!=51237 || h.table[ordered_ranges].count!=342 || h.table[placements].count!=209)return false;
        // Generated reference lighting only covers the22 original NORMAL placements.
        for(unsigned pi=0;pi<209;++pi){const auto p=record<PlacementRecord>(placements,pi);const auto t=record<TemplateRecord>(templates,p.template_index);
            if(bool(t.attribute_kind)!=(pi>=79 && pi<=100))return false;}
        return true;
    }
    Owner owner()const{return source_.owner_;}
    bool draw(unsigned pass){
        auto& stats=state.count[pass];
        for(unsigned ri=0;ri<342;++ri){
            const auto& policy=ps2_policy[ri];if(policy.pass!=pass)continue;
            if(!live()){++stats.failed;return false;}
            const auto r=record<OrderedRangeRecord>(ordered_ranges,ri);const auto p=record<PlacementRecord>(placements,r.placement);
            const auto t=record<TemplateRecord>(templates,r.template_index);const auto& tex=ps2_textures[policy.texture];
            float screen[3][4];compose(p,t.factor,screen);Re4dcModelPacket packet{};unsigned used=0;bool failed=false;
            for(unsigned gi=0;gi<r.group_count && !failed;++gi){
                const auto g=record<OrderedBoundRecord>(ordered_bounds,r.first_group+gi);++stats.groups;
                if(reject(g,screen)){++stats.reject_groups;continue;}
                Vertex ring[3];unsigned length=0;
                for(unsigned ci=g.first_corner;ci<g.first_corner+g.corner_count;++ci){
                    ring[length%3]=vertex(t,p,screen,tex,ci);
                    if(length>=2){
                        pvr_vertex_t scratch[30];const Vertex& a=ring[(length-2)%3];const Vertex& b=ring[(length-1)%3];const Vertex& c=ring[length%3];
                        const unsigned n=(length&1)?triangle(c,b,a,policy.cull,scratch,stats):triangle(a,b,c,policy.cull,scratch,stats);
                        if(n){
                            if(!packet.vertices || used+n>packet.capacity){
                                if(used){re4dc_model_packet_commit(used);stats.output+=used/3;used=0;}
                                if(!re4dc_ps2_world_packet(tex.crc,tex.fnv,tex.width,tex.height,pass,&packet)||packet.capacity<n||!live()){
                                    ++stats.failed;failed=true;
                                    if(stats.failed<=8)re4dc_log("PS2WORLD reject frame=%u pass=%u range=%u key=%08x-%08x\n",state.frame,pass,ri,tex.crc,tex.fnv);
                                    break;
                                }
                                ++stats.packets;
                            }
                            std::memcpy(static_cast<pvr_vertex_t*>(packet.vertices)+used,scratch,n*sizeof(pvr_vertex_t));used+=n;
                        }
                    }
                    ++length;if(u16(at(t.corner.offset+ci*6))&0x8000)length=0;
                }
            }
            if(used){re4dc_model_packet_commit(used);stats.output+=used/3;}
        }
        return stats.failed==0;
    }
#if RE4DC_PS2_WORLD_KERNEL
    // vertex()'s colour, packed exactly as color() packs it after triangle().
    unsigned corner_argb(const TemplateRecord& t,const PlacementRecord& p,const Ps2Texture& texture,unsigned corner) const{
        const auto* c=at(t.corner.offset+corner*6);const auto* pos=at(t.position.offset+(u16(c)&0x7fff)*6);
        const auto* attr=at(t.attribute.offset+u16(c+4)*(t.attribute_kind?6:4));
        std::int16_t q[3]={i16(pos),i16(pos+2),i16(pos+4)};Vertex v{};float rgb[3];
        if(t.attribute_kind){std::int16_t n[3]={i16(attr),i16(attr+2),i16(attr+4)};normal_light(p.placement,p,q,n,t.factor,rgb);v.a=1;}
        else {for(unsigned j=0;j<3;++j)rgb[j]=attr[j]*(1.0f/128);v.a=attr[3]*(1.0f/128);}
        v.r=clamp(rgb[0]*texture.gain[0]);v.g=clamp(rgb[1]*texture.gain[1]);v.b=clamp(rgb[2]*texture.gain[2]);
        return color(v);
    }
    // Built at adopt: one packed colour per lit range corner (offset[ri]==~0u: not cached).
    void build_light_cache(){
        if(light_cache.tried && same_owner(light_cache.owner,source_.owner_))return;
        light_cache_free();light_cache.tried=true;light_cache.owner=source_.owner_;
        unsigned corners=0,all_corners=0;
        for(unsigned ri=0;ri<342;++ri){const auto r=record<OrderedRangeRecord>(ordered_ranges,ri);all_corners+=r.corner_count;
            if(RE4DC_PS2_WORLD_COLOR_ALL || record<TemplateRecord>(templates,r.template_index).attribute_kind)corners+=r.corner_count;}
        unsigned clusters=0;bool groups_ok=true;const unsigned group_table=package_.header_.table[ordered_bounds].count;
        for(unsigned ri=0;ri<342;++ri){const auto r=record<OrderedRangeRecord>(ordered_ranges,ri);
            clusters+=(r.group_count+kCluster-1)/kCluster;
            if(r.first_group>group_table || r.group_count>group_table-r.first_group)groups_ok=false;}
        const unsigned bytes=342*4+corners*4+342*sizeof(RangeBound)+342*4+clusters*sizeof(ClusterBox);
        auto* block=static_cast<std::uint32_t*>(re4dc_static_alloc(bytes));
        re4dc_log("PS2KERNEL light-cache all=%u corners=%u clusters=%u groups_ok=%u bytes=%u %s heap=%d\n",all_corners,corners,clusters,unsigned(groups_ok),bytes,block?"ok":"refused",re4dc_static_heap_free());
        if(!block)return;
        light_cache.offset=block;light_cache.argb=block+342;light_cache.corners=corners;light_cache.bytes=bytes;
        light_cache.bounds=reinterpret_cast<RangeBound*>(block+342+corners);
        light_cache.cluster_first=reinterpret_cast<std::uint32_t*>(light_cache.bounds+342);
        light_cache.clusters=reinterpret_cast<ClusterBox*>(light_cache.cluster_first+342);
        light_cache.groups_ok=groups_ok;unsigned next_cluster=0;
        unsigned next=0;
        for(unsigned ri=0;ri<342;++ri){
            const auto r=record<OrderedRangeRecord>(ordered_ranges,ri);const auto t=record<TemplateRecord>(templates,r.template_index);
            auto& rb=light_cache.bounds[ri];rb=RangeBound{};rb.valid=r.group_count>0;
            light_cache.cluster_first[ri]=next_cluster;
            for(unsigned gi=0;gi<r.group_count;++gi){const auto g=record<OrderedBoundRecord>(ordered_bounds,r.first_group+gi);
                auto& cb=light_cache.clusters[next_cluster+gi/kCluster];
                for(unsigned j=0;j<3;++j){
                    if(!gi||g.minimum[j]<rb.minimum[j])rb.minimum[j]=g.minimum[j];
                    if(!gi||g.maximum[j]>rb.maximum[j])rb.maximum[j]=g.maximum[j];
                    if(!(gi%kCluster)||g.minimum[j]<cb.minimum[j])cb.minimum[j]=g.minimum[j];
                    if(!(gi%kCluster)||g.maximum[j]>cb.maximum[j])cb.maximum[j]=g.maximum[j];}}
            next_cluster+=(r.group_count+kCluster-1)/kCluster;
            if(!RE4DC_PS2_WORLD_COLOR_ALL && !t.attribute_kind){block[ri]=~0u;continue;}
            const auto p=record<PlacementRecord>(placements,r.placement);const auto& tex=ps2_textures[ps2_policy[ri].texture];
            block[ri]=next;
            for(unsigned i=0;i<r.corner_count;++i)light_cache.argb[next+i]=corner_argb(t,p,tex,r.first_corner+i);
            next+=r.corner_count;
        }
    }
    // An OrderedBoundRecord read in place (the table is range-checked once in build_light_cache).
    OrderedBoundRecord group(unsigned index) const{
        const std::uint8_t* q=package_.table(ordered_bounds).data+std::size_t(index)*20;
        OrderedBoundRecord g;g.first_corner=u32(q);g.corner_count=u16(q+4);g.reserved=u16(q+6);
        for(unsigned j=0;j<3;++j){g.minimum[j]=i16(q+8+2*j);g.maximum[j]=i16(q+14+2*j);}
        return g;
    }
    // vertex() without the colour (same position and uv expressions).
    Vertex position(const TemplateRecord& t,const float screen[3][4],unsigned corner) const{
        const auto* c=at(t.corner.offset+corner*6);const auto* pos=at(t.position.offset+(u16(c)&0x7fff)*6);
        const auto* uv=at(t.uv.offset+u16(c+2)*4);
        std::int16_t q[3]={i16(pos),i16(pos+2),i16(pos+4)};float xyz[3];
        for(unsigned r=0;r<3;++r){xyz[r]=screen[r][3];for(unsigned j=0;j<3;++j)xyz[r]+=screen[r][j]*q[j];}
        Vertex v;v.x=xyz[0];v.y=xyz[1];v.w=xyz[2];v.u=i16(uv)*(1.0f/256);v.v=i16(uv+2)*(1.0f/256);v.r=v.g=v.b=v.a=0;
        return v;
    }
    // One corner, transformed and projected with triangle()'s expressions.
    Projected project(const TemplateRecord& t,const float screen[3][4],unsigned corner,unsigned argb) const{
        const auto* c=at(t.corner.offset+corner*6);const auto* pos=at(t.position.offset+(u16(c)&0x7fff)*6);
        const auto* uv=at(t.uv.offset+u16(c+2)*4);
        std::int16_t q[3]={i16(pos),i16(pos+2),i16(pos+4)};float xyz[3];
        for(unsigned r=0;r<3;++r){xyz[r]=screen[r][3];for(unsigned j=0;j<3;++j)xyz[r]+=screen[r][j]*q[j];}
        Vertex v{};v.x=xyz[0];v.y=xyz[1];v.w=xyz[2];
        Projected o;o.z=1/v.w;o.x=v.x*o.z;o.y=v.y*o.z;
        o.u=i16(uv)*(1.0f/256);o.v=i16(uv+2)*(1.0f/256);o.argb=argb;
        // Screen-edge outcode (=3): a triangle wholly past one edge is what the clipper empties.
        o.out=(o.x<0?1u:0u)|(o.x>RE4DC_SCREEN_W?2u:0u)|(o.y<0?4u:0u)|(o.y>RE4DC_SCREEN_H?8u:0u);
        return o;
    }
    // The six planes in the range's local coordinates, built once per range.
    struct PlaneSet {float a[6][3],b[6],s[3][4],fs[3][3];};
    static void planes(const float screen[3][4],float far,PlaneSet& ps){
        for(unsigned r=0;r<3;++r)for(unsigned j=0;j<4;++j){ps.s[r][j]=screen[r][j];if(j<3)ps.fs[r][j]=std::fabs(screen[r][j]);}
        for(unsigned k=0;k<6;++k){
            float* a=ps.a[k];float& b=ps.b[k];
            switch(k){
            case 0:for(unsigned j=0;j<3;++j)a[j]=screen[2][j];b=screen[2][3]-40;break;
            case 1:for(unsigned j=0;j<3;++j)a[j]=-screen[2][j];b=far-screen[2][3];break;
            case 2:for(unsigned j=0;j<3;++j)a[j]=screen[0][j];b=screen[0][3];break;
            case 3:for(unsigned j=0;j<3;++j)a[j]=RE4DC_SCREEN_W*screen[2][j]-screen[0][j];b=RE4DC_SCREEN_W*screen[2][3]-screen[0][3];break;
            case 4:for(unsigned j=0;j<3;++j)a[j]=screen[1][j];b=screen[1][3];break;
            default:for(unsigned j=0;j<3;++j)a[j]=RE4DC_SCREEN_H*screen[2][j]-screen[1][j];b=RE4DC_SCREEN_H*screen[2][3]-screen[1][3];break;
            }
        }
    }
    // Same verdict as classify(), with the planes precomputed (identical float expressions).
    static unsigned classify(const OrderedBoundRecord& g,const PlaneSet& ps){
        float c[3],h[3];
        for(unsigned j=0;j<3;++j){c[j]=(float(g.minimum[j])+float(g.maximum[j]))*0.5f;h[j]=(float(g.maximum[j])-float(g.minimum[j]))*0.5f;}
        float centre[3],radius[3];
        for(unsigned r=0;r<3;++r){
            centre[r]=ps.s[r][3];radius[r]=0;
            for(unsigned j=0;j<3;++j){centre[r]+=ps.s[r][j]*c[j];radius[r]+=ps.fs[r][j]*h[j];}
        }
        const float margin=32+(std::fabs(centre[0])+radius[0]+std::fabs(centre[1])+radius[1]+RE4DC_SCREEN_W*(std::fabs(centre[2])+radius[2]))*0.00002f;
        unsigned result=2;
        for(unsigned k=0;k<6;++k){
            const float* a=ps.a[k];
            float d=ps.b[k],e=0;for(unsigned j=0;j<3;++j){d+=a[j]*c[j];e+=std::fabs(a[j])*h[j];}
            if(d+e<-margin)return 0;
            if(d-e<=margin && (!RE4DC_PS2_NEAR_ONLY || k<2))result=1;
        }
        return result;
    }
    // 0 reject, 1 crossing (old per-triangle clip path), 2 wholly inside (fast path).
    static unsigned classify(const OrderedBoundRecord& g,const float screen[3][4],float far){
        float c[3],h[3];
        for(unsigned j=0;j<3;++j){c[j]=(float(g.minimum[j])+float(g.maximum[j]))*0.5f;h[j]=(float(g.maximum[j])-float(g.minimum[j]))*0.5f;}
        float centre[3],radius[3];
        for(unsigned r=0;r<3;++r){
            centre[r]=screen[r][3];radius[r]=0;
            for(unsigned j=0;j<3;++j){centre[r]+=screen[r][j]*c[j];radius[r]+=std::fabs(screen[r][j])*h[j];}
        }
        // >= reject()'s per-corner margin at every box point, doubled for rounding.
        const float margin=32+(std::fabs(centre[0])+radius[0]+std::fabs(centre[1])+radius[1]+RE4DC_SCREEN_W*(std::fabs(centre[2])+radius[2]))*0.00002f;
        unsigned result=2;
        for(unsigned k=0;k<6;++k){
            float a[3],b;
            switch(k){
            case 0:for(unsigned j=0;j<3;++j)a[j]=screen[2][j];b=screen[2][3]-40;break;
            case 1:for(unsigned j=0;j<3;++j)a[j]=-screen[2][j];b=far-screen[2][3];break;
            case 2:for(unsigned j=0;j<3;++j)a[j]=screen[0][j];b=screen[0][3];break;
            case 3:for(unsigned j=0;j<3;++j)a[j]=RE4DC_SCREEN_W*screen[2][j]-screen[0][j];b=RE4DC_SCREEN_W*screen[2][3]-screen[0][3];break;
            case 4:for(unsigned j=0;j<3;++j)a[j]=screen[1][j];b=screen[1][3];break;
            default:for(unsigned j=0;j<3;++j)a[j]=RE4DC_SCREEN_H*screen[2][j]-screen[1][j];b=RE4DC_SCREEN_H*screen[2][3]-screen[1][3];break;
            }
            float d=b,e=0;for(unsigned j=0;j<3;++j){d+=a[j]*c[j];e+=std::fabs(a[j])*h[j];}
            if(d+e<-margin)return 0;
            // =3: only the near/far planes need the clipper; the PVR takes off-screen x/y
            // (the coarse world's near-only rule), so screen-edge crossings stay on the fast path.
            if(d-e<=margin && (!RE4DC_PS2_NEAR_ONLY || k<2))result=1;
        }
        return result;
    }
#if RE4DC_PS2_NEAR_ONLY
    // triangle() limited to the near/far planes (screen edges are left to the PVR); a triangle
    // wholly past one screen edge is dropped as the clipper would drop it. No array value-init.
    static unsigned triangle_nf(const Vertex* const tri[3],unsigned cull,pvr_vertex_t* output,Counters& stats){
        ++stats.input;
        Vertex aa[12],bb[12];Vertex* in=aa;Vertex* out=bb;unsigned count=3;
        aa[0]=*tri[0];aa[1]=*tri[1];aa[2]=*tri[2];
        const bool inside=distance(aa[0],0)>=0&&distance(aa[1],0)>=0&&distance(aa[2],0)>=0&&
                          distance(aa[0],1)>=0&&distance(aa[1],1)>=0&&distance(aa[2],1)>=0;
        if(!inside){
            for(unsigned plane=0;plane<2 && count;++plane){
                unsigned next=0;Vertex prev=in[count-1];float pd=distance(prev,plane);
                for(unsigned i=0;i<count;++i){const Vertex now=in[i];const float nd=distance(now,plane);
                    if((pd<0)!=(nd<0))out[next++]=interpolate(prev,now,pd/(pd-nd));
                    if(nd>=0)out[next++]=now;
                    prev=now;pd=nd;
                }
                count=next;Vertex* swap=in;in=out;out=swap;
            }
            if(count<3){++stats.clipped;return 0;}
            if(count!=3)++stats.clipped;
        }
        unsigned written=0;
        for(unsigned j=1;j+1<count;++j){
            const Vertex* v[3]={in,in+j,in+j+1};float x[3],y[3],z[3];unsigned oc=15;
            for(unsigned k=0;k<3;++k){z[k]=1/v[k]->w;x[k]=v[k]->x*z[k];y[k]=v[k]->y*z[k];
                oc&=(x[k]<0?1u:0u)|(x[k]>RE4DC_SCREEN_W?2u:0u)|(y[k]<0?4u:0u)|(y[k]>RE4DC_SCREEN_H?8u:0u);}
            if(oc){++stats.clipped;continue;}
            const float area=(x[1]-x[0])*(y[2]-y[0])-(y[1]-y[0])*(x[2]-x[0]);
            if((cull==0 && area>=0)||(cull==1 && area<=0)||area==0){++stats.culls;continue;}
            for(unsigned k=0;k<3;++k)output[written++]={k==2?PVR_CMD_VERTEX_EOL:PVR_CMD_VERTEX,x[k],y[k],z[k],v[k]->u,v[k]->v,color(*v[k]),0};
        }
        return written;
    }
#endif
    bool draw_kernel(unsigned pass){
        auto& stats=state.count[pass];auto& ks=kernel[pass];
        for(unsigned ri=0;ri<342;++ri){
            const auto& policy=ps2_policy[ri];if(policy.pass!=pass)continue;
            if(!live()){++stats.failed;return false;}
            const auto r=record<OrderedRangeRecord>(ordered_ranges,ri);const auto p=record<PlacementRecord>(placements,r.placement);
            const auto t=record<TemplateRecord>(templates,r.template_index);const auto& tex=ps2_textures[policy.texture];
            const std::uint32_t* lit=nullptr;
            if(light_cache.offset && light_cache.offset[ri]!=~0u && same_owner(light_cache.owner,source_.owner_))lit=light_cache.argb+light_cache.offset[ri];
            float screen[3][4];compose(p,t.factor,screen);Re4dcModelPacket packet{};unsigned used=0;bool failed=false;
            // The old path's packet rule: a new packet when the next n words do not fit.
            auto reserve=[&](unsigned n)->bool{
                if(!packet.vertices || used+n>packet.capacity){
                    if(used){re4dc_model_packet_commit(used);stats.output+=used/3;used=0;}
#if RE4DC_PS2_WORLD_KERNEL==4
                    // The header carries the authored cull (PVR back-face test), so strips need no software area test.
                    if(!re4dc_ps2_world_packet_cull(tex.crc,tex.fnv,tex.width,tex.height,pass,policy.cull,&packet)||packet.capacity<n||!live()){
#else
                    if(!re4dc_ps2_world_packet(tex.crc,tex.fnv,tex.width,tex.height,pass,&packet)||packet.capacity<n||!live()){
#endif
                        ++stats.failed;failed=true;
                        if(stats.failed<=8)re4dc_log("PS2WORLD reject frame=%u pass=%u range=%u key=%08x-%08x\n",state.frame,pass,ri,tex.crc,tex.fnv);
                        return false;
                    }
                    ++stats.packets;
                }
                return true;
            };
            PlaneSet pset;planes(screen,state.far,pset);
            unsigned range_kind=1;
            if(light_cache.bounds && light_cache.bounds[ri].valid && same_owner(light_cache.owner,source_.owner_)){
                const auto& rb=light_cache.bounds[ri];OrderedBoundRecord box{};
                for(unsigned j=0;j<3;++j){box.minimum[j]=rb.minimum[j];box.maximum[j]=rb.maximum[j];}
                range_kind=classify(box,pset);
            }
            if(!range_kind){
                ++ks.range_reject;stats.groups+=r.group_count;stats.reject_groups+=r.group_count;
#if RE4DC_PS2_WORLD_KERNEL==2
                for(unsigned gi=0;gi<r.group_count;++gi){const auto g=record<OrderedBoundRecord>(ordered_bounds,r.first_group+gi);
                    if(classify(g,screen,state.far))++ks.badrange;
                    if(!reject(g,screen))++ks.unsafe;}
#endif
                continue;
            }
            if(range_kind==2)++ks.range_inside;
            const bool fast_groups=light_cache.groups_ok && light_cache.clusters && same_owner(light_cache.owner,source_.owner_);
            // Emits one projected triangle in triangle()'s order and rules; false when the packet failed.
            auto emit=[&](const Projected* const v[3])->bool{
                const float area=(v[1]->x-v[0]->x)*(v[2]->y-v[0]->y)-(v[1]->y-v[0]->y)*(v[2]->x-v[0]->x);
                if(v[0]->out & v[1]->out & v[2]->out){++stats.clipped;return true;}
                if((policy.cull==0 && area>=0)||(policy.cull==1 && area<=0)||area==0){++stats.culls;return true;}
                if(!reserve(3))return false;
                auto* out=static_cast<pvr_vertex_t*>(packet.vertices)+used;
                for(unsigned k=0;k<3;++k)out[k]={k==2?PVR_CMD_VERTEX_EOL:PVR_CMD_VERTEX,v[k]->x,v[k]->y,v[k]->z,v[k]->u,v[k]->v,v[k]->argb,0};
                used+=3;return true;
            };
            auto argb_of=[&](unsigned ci)->unsigned{
                const unsigned local=ci-r.first_corner;
                return lit && local<r.corner_count?lit[local]:corner_argb(t,p,tex,ci);
            };
            for(unsigned gc=0;gc<r.group_count && !failed;gc+=kCluster){
                const unsigned gn=r.group_count-gc<kCluster?r.group_count-gc:kCluster;
                unsigned cluster_kind=range_kind;
                if(fast_groups && range_kind==1){
                    const auto& cb=light_cache.clusters[light_cache.cluster_first[ri]+gc/kCluster];OrderedBoundRecord box{};
                    for(unsigned j=0;j<3;++j){box.minimum[j]=cb.minimum[j];box.maximum[j]=cb.maximum[j];}
                    cluster_kind=classify(box,pset);
                }
                if(!cluster_kind){
                    stats.groups+=gn;stats.reject_groups+=gn;
#if RE4DC_PS2_WORLD_KERNEL==2
                    for(unsigned gi=gc;gi<gc+gn;++gi){const auto g=record<OrderedBoundRecord>(ordered_bounds,r.first_group+gi);
                        if(classify(g,screen,state.far))++ks.badrange;
                        if(!reject(g,screen))++ks.unsafe;}
#endif
                    continue;
                }
            for(unsigned gi=gc;gi<gc+gn && !failed;++gi){
                const auto g=fast_groups?group(r.first_group+gi):record<OrderedBoundRecord>(ordered_bounds,r.first_group+gi);++stats.groups;
#if RE4DC_PS2_WORLD_KERNEL==2
                const unsigned kind=classify(g,screen,state.far);
                if(cluster_kind==2 && kind!=2)++ks.badrange;
                const bool old_reject=reject(g,screen);
                if(!kind && !old_reject)++ks.unsafe;
                if(kind && old_reject)++ks.extra;
                if(kind==2)for(unsigned ci=g.first_corner;ci<g.first_corner+g.corner_count;++ci){
                    const auto* c=at(t.corner.offset+ci*6);const auto* pos=at(t.position.offset+(u16(c)&0x7fff)*6);
                    bool bad=false;for(unsigned j=0;j<3;++j){const int q=i16(pos+2*j);if(q<g.minimum[j]||q>g.maximum[j])bad=true;}
                    const Vertex v=vertex(t,p,screen,tex,ci);for(unsigned k=0;k<6;++k)if(distance(v,k)<0)bad=true;
                    if(bad)++ks.badin;
                    if(lit && ci-r.first_corner<r.corner_count && lit[ci-r.first_corner]!=color(v))++ks.badcolor;
                }
#else
                const unsigned kind=cluster_kind==2?2u:classify(g,pset);
#endif
                if(!kind){++stats.reject_groups;continue;}
                const unsigned end=g.first_corner+g.corner_count;
#if RE4DC_PS2_NEAR_ONLY
                if(kind==1){
                    // Near/far crossing: a triangle inside both planes is projected directly
                    // (triangle()'s expressions); only a triangle across near/far is clipped, and
                    // only against those two planes.
                    ++ks.crossing;
                    Vertex ring[3];unsigned length=0;
                    for(unsigned ci=g.first_corner;ci<end && !failed;++ci){
                        ring[length%3]=vertex(t,p,screen,tex,ci);
                        if(length>=2){
                            const Vertex& a=ring[(length-2)%3];const Vertex& b=ring[(length-1)%3];const Vertex& c=ring[length%3];
                            const Vertex* tri[3];
                            if(length&1){tri[0]=&c;tri[1]=&b;tri[2]=&a;}else{tri[0]=&a;tri[1]=&b;tri[2]=&c;}
                            pvr_vertex_t scratch[30];const unsigned n=triangle_nf(tri,policy.cull,scratch,stats);
                            if(n){
                                if(!reserve(n))break;
                                std::memcpy(static_cast<pvr_vertex_t*>(packet.vertices)+used,scratch,n*sizeof(pvr_vertex_t));used+=n;
                            }
                        }
                        ++length;if(u16(at(t.corner.offset+ci*6))&0x8000)length=0;
                    }
                    continue;
                }
#endif
                if(kind==1){
                    ++ks.crossing;
                    Vertex ring[3];unsigned length=0;
                    for(unsigned ci=g.first_corner;ci<end;++ci){
                        ring[length%3]=vertex(t,p,screen,tex,ci);
                        if(length>=2){
                            pvr_vertex_t scratch[30];const Vertex& a=ring[(length-2)%3];const Vertex& b=ring[(length-1)%3];const Vertex& c=ring[length%3];
                            const unsigned n=(length&1)?triangle(c,b,a,policy.cull,scratch,stats):triangle(a,b,c,policy.cull,scratch,stats);
                            if(n){
                                if(!reserve(n))break;
                                std::memcpy(static_cast<pvr_vertex_t*>(packet.vertices)+used,scratch,n*sizeof(pvr_vertex_t));used+=n;
                            }
                        }
                        ++length;if(u16(at(t.corner.offset+ci*6))&0x8000)length=0;
                    }
                    continue;
                }
                ++ks.inside;
#if RE4DC_PS2_WORLD_KERNEL==4
                // Whole source strips (EOL at the strip end only); the PVR culls by the header.
                // A strip longer than kMaxStrip goes out per triangle (same order and rules).
                constexpr unsigned kMaxStrip=64;
                for(unsigned ci=g.first_corner;ci<end && !failed;){
                    unsigned se=ci;
                    while(se<end){const bool last=u16(at(t.corner.offset+se*6))&0x8000;++se;if(last)break;}
                    const unsigned n=se-ci;
                    if(n>=3 && n<=kMaxStrip){
                        stats.input+=n-2;
                        if(!reserve(n))break;
                        auto* out=static_cast<pvr_vertex_t*>(packet.vertices)+used;
                        for(unsigned k=0;k<n;++k){const Projected o=project(t,screen,ci+k,argb_of(ci+k));
                            out[k]={k+1==n?PVR_CMD_VERTEX_EOL:PVR_CMD_VERTEX,o.x,o.y,o.z,o.u,o.v,o.argb,0};}
                        used+=n;++ks.strips;ks.strip_vertices+=n;
                    }
                    else if(n>kMaxStrip){
                        ++ks.long_strips;Projected ring[3];unsigned length=0;
                        for(unsigned k=ci;k<se;++k){
                            ring[length%3]=project(t,screen,k,argb_of(k));
                            if(length>=2){
                                ++stats.input;const Projected* v[3];
                                if(length&1){v[0]=&ring[length%3];v[1]=&ring[(length-1)%3];v[2]=&ring[(length-2)%3];}
                                else {v[0]=&ring[(length-2)%3];v[1]=&ring[(length-1)%3];v[2]=&ring[length%3];}
                                if(!emit(v))break;
                            }
                            ++length;
                        }
                    }
                    ci=se;
                }
                continue;
#endif
                Projected ring[3];unsigned length=0;
                for(unsigned ci=g.first_corner;ci<end;++ci){
                    ring[length%3]=project(t,screen,ci,argb_of(ci));
                    if(length>=2){
                        ++stats.input;
                        const Projected* v[3];
                        if(length&1){v[0]=&ring[length%3];v[1]=&ring[(length-1)%3];v[2]=&ring[(length-2)%3];}
                        else {v[0]=&ring[(length-2)%3];v[1]=&ring[(length-1)%3];v[2]=&ring[length%3];}
                        if(!emit(v))break;
                    }
                    ++length;if(u16(at(t.corner.offset+ci*6))&0x8000)length=0;
                }
            }
            }
            if(used){re4dc_model_packet_commit(used);stats.output+=used/3;}
        }
        return stats.failed==0;
    }
#endif
};
}}}
#if RE4DC_PS2_WORLD_FOG_SOURCE
// PS2_WORLD_FOG_SOURCE (game30.mk): the source GX fog state at this frame's scenery draw (pass 0), which the frame's
// PT / TR flush keeps: the flush runs after the source has turned fog off for later draws.
extern "C" unsigned re4dc_fog_enabled();
static unsigned ps2_world_fog=1;
extern "C" unsigned re4dc_ps2_world_fog(){return ps2_world_fog;}
// The latched state is logged when it changes (once per room fog switch; the fog qualification's source fog record).
static unsigned ps2_world_fog_logged=2;
static inline void re4dc_ps2_world_fog_latch(){
    ps2_world_fog=re4dc_fog_enabled();
    if(ps2_world_fog!=ps2_world_fog_logged){
        ps2_world_fog_logged=ps2_world_fog;
        re4dc_log("ps2 world fog: source fog %s at the scenery draw\n",ps2_world_fog?"on":"off");
    }
}
#define RE4DC_PS2_WORLD_FOG_LATCH() re4dc_ps2_world_fog_latch()
#else
#define RE4DC_PS2_WORLD_FOG_LATCH() ((void)0)
#endif
// Rooms whose scenery the PS2 world package replaces (trans.cpp COARSE_SCENERY_FALLBACK).
#if RE4DC_PS2_WORLD_ROOMS
// PS2_WORLD_ROOMS (game30.mk): r100, r101 and r103, each from its own package (native_static.cpp ps2_open),
// unless that package failed to open: then the room's own scenery draws.
extern "C" int re4dc_ps2_mesh_failed(unsigned room);
extern "C" void re4dc_ps2_mesh_select(unsigned room);
extern "C" int re4dc_ps2_world_room(unsigned room); // native_static.cpp: the rooms with a package
extern "C" int re4dc_ps2_world_covers(unsigned room){
    return re4dc_ps2_world_room(room) && !re4dc_ps2_mesh_failed(room);
}
#else
extern "C" int re4dc_ps2_world_covers(unsigned room){return room==0x101;}
#endif
extern "C" int re4dc_ps2_world_draw(unsigned room,const float screen[3][4],float far){
    using namespace re4dc::room::ps2;
    RE4DC_PS2_WORLD_FOG_LATCH();
#if RE4DC_PS2_WORLD_MESH
    // PS2_WORLD_MESH: the converted R4IM package (native_static.cpp); the .r4p is never loaded.
    (void)screen;state.pending=false;
#if RE4DC_PS2_WORLD_ROOMS
    if(!re4dc_ps2_world_covers(room)){if(!re4dc_ps2_mesh_failed(room))re4dc_ps2_mesh_retire();return 0;}
    re4dc_ps2_mesh_select(room);
#else
    if(room!=0x101){re4dc_ps2_mesh_retire();return 0;}
#endif
    if(!finite_word(far) || far<=40)return fallback(3);
    state.frame=re4dc_ui_frame();state.flushed=~0u;state.far=far<RE4DC_PS2_FAR?far:RE4DC_PS2_FAR;
    const bool drawn=re4dc_ps2_mesh_draw(0,state.far)!=0;state.pending=true;
    return drawn?1:fallback(4);
#endif
    state.pending=false;auto& owner=storage();Owner now{};
    if(room!=0x101 || !current(nullptr,now) || now.room!=room){owner.retire();return 0;}
    if(!owner.live()){
        if(same_owner(now,state.attempted))return fallback(1);
        state.attempted=now;
        const int before=re4dc_static_heap_free();
        const auto status=owner.load("/cd/dc/native/r101/ps2-world.r4p",{0x101,ps2_asset_owner,1191800});
        re4dc_log("PS2WORLD adopt room=%03x gen=%u status=%u package=%u bytes=%u heap=%d/%d\n",room,unsigned(now.generation),unsigned(status),unsigned(owner.package_error()),unsigned(owner.resident_bytes()),before,re4dc_static_heap_free());
    }
    WorldDraw draw(owner);if(!draw.qualified())return fallback(2);
    for(unsigned r=0;r<3;++r)for(unsigned c=0;c<4;++c)if(!finite_word(screen[r][c]))return fallback(3);
    if(!finite_word(far) || far<=40)return fallback(3);
    state.owner=draw.owner();state.frame=re4dc_ui_frame();state.flushed=~0u;state.far=far<RE4DC_PS2_FAR?far:RE4DC_PS2_FAR;
    std::memcpy(state.screen,screen,sizeof(state.screen));for(auto& c:state.count)c={};
#if RE4DC_PS2_WORLD_KERNEL
    for(auto& k:kernel)k={};
    draw.build_light_cache();
    const bool complete=draw.draw_kernel(0);state.pending=true;
#else
    const bool complete=draw.draw(0);state.pending=true;
#endif
    // Failure leaves piece0 collision fallback enabled; already emitted triangles
    // are not falsely called complete. PT/TR success is separately reported.
    return complete?1:fallback(4);
}
#if RE4DC_PS2_WORLD_MESH && RE4DC_PS2_WORLD_ROOMS >= 2
// PS2_WORLD_ROOMS=2, an image the coarse path does not draw (native_static.cpp re4dc_ps2_mesh_source, camera
// already set): pass 0 now; re4dc_ps2_world_flush draws PT / TR as for a coarse image.
extern "C" int re4dc_ps2_world_source_draw(){
    using namespace re4dc::room::ps2;
    RE4DC_PS2_WORLD_FOG_LATCH();
    state.frame=re4dc_ui_frame();state.flushed=~0u;state.far=RE4DC_PS2_FAR;
    const bool drawn=re4dc_ps2_mesh_draw(0,state.far)!=0;state.pending=true;
    return drawn;
}
#endif
extern "C" int re4dc_ps2_world_pending(){
    using namespace re4dc::room::ps2;
    return state.pending && state.frame==re4dc_ui_frame() && state.flushed!=state.frame;
}
extern "C" void re4dc_ps2_world_flush(){
    using namespace re4dc::room::ps2;
    if(!state.pending || state.frame!=re4dc_ui_frame() || state.flushed==state.frame)return;
    state.flushed=state.frame;state.pending=false;
#if defined(RE4DC_MEMPROF) && RE4DC_MEMPROF
    if(!(state.frame%120))re4dc_memprof_log(state.frame,120);
#endif
#if RE4DC_PS2_WORLD_MESH
    {
        const bool pt=re4dc_ps2_mesh_draw(1,state.far)!=0,tr=re4dc_ps2_mesh_draw(2,state.far)!=0;
        if(!(state.frame%120) || !pt || !tr)re4dc_ps2_mesh_log(state.frame);
        return;
    }
#endif
    WorldDraw draw(storage());
#if RE4DC_PS2_WORLD_KERNEL
    const bool pt=draw.draw_kernel(1),tr=draw.draw_kernel(2);
#else
    const bool pt=draw.draw(1),tr=draw.draw(2);
#endif
    if(!(state.frame%120) || !pt || !tr || state.count[0].failed){
        for(unsigned p=0;p<3;++p){const auto& c=state.count[p];
            re4dc_log("PS2WORLD frame=%u pass=%u groups=%u reject=%u input=%u out=%u packets=%u fail=%u clip=%u cull=%u\n",state.frame,p,c.groups,c.reject_groups,c.input,c.output,c.packets,c.failed,c.clipped,c.culls);
#if RE4DC_PS2_WORLD_KERNEL
            const auto& k=kernel[p];
            re4dc_log("PS2KERNEL frame=%u pass=%u mode=%u inside=%u crossing=%u unsafe=%u extra=%u badin=%u badcolor=%u range_reject=%u range_inside=%u badrange=%u strips=%u strip_vertices=%u long_strips=%u\n",state.frame,p,unsigned(RE4DC_PS2_WORLD_KERNEL),k.inside,k.crossing,k.unsafe,k.extra,k.badin,k.badcolor,k.range_reject,k.range_inside,k.badrange,k.strips,k.strip_vertices,k.long_strips);
#endif
        }
    }
}
extern "C" void re4dc_ps2_world_retire(){
#if RE4DC_PS2_WORLD_MESH
    re4dc_ps2_mesh_retire();
#endif
    using namespace re4dc::room::ps2;state.pending=false;state.frame=~0u;state.owner={};state.attempted={};state.fallbacks=0;storage().retire();
#if RE4DC_PS2_WORLD_KERNEL
    light_cache_free();
#endif
}
#endif
