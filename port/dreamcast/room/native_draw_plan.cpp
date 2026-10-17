#include "native_draw_plan.hpp"
#include <limits>
#include <new>
#include <cmath>
#include <cstring>
#include <algorithm>

namespace re4dc::render {
namespace {
unsigned be16(const std::uint8_t* p) { return (unsigned(p[0])<<8)|p[1]; }
bool topology(unsigned op, unsigned n, DrawTopology& out) {
    switch(op) {
    case 0x80: out=DrawTopology::quads; return n%4==0;
    case 0x90: out=DrawTopology::triangles; return n%3==0;
    case 0x98: out=DrawTopology::strip; return true;
    case 0xa0: out=DrawTopology::fan; return true;
    default: return false;
    }
}
}
bool inspect_draw_plan(const std::uint8_t* stream, std::uint32_t bytes,
                       bool colored, std::uint32_t positions,
                       std::uint32_t normals, DrawPlanRequirements& out) {
    out={};
    if(!stream || bytes>1024*1024 || !positions || !normals) return false;
    DrawPlanRequirements r;
    const unsigned stride=colored?8:6;
    unsigned offset=0,last_end=0,last_op=0,last_n=0,repeats=0;
    while(offset<bytes) {
        const unsigned op=stream[offset++]; if(!op) continue;
        if(bytes-offset<2) return false;
        const unsigned n=be16(stream+offset); offset+=2;
        DrawTopology kind;
        if(offset>0xfffff || !topology(op,n,kind) || n>(bytes-offset)/stride) return false;
        const bool repeated=offset-3==last_end && op==last_op && n==last_n && repeats<16384;
        if(repeated)++repeats;else{++r.primitives;repeats=1;}
        last_op=op;last_n=n;last_end=offset+n*stride;r.corners+=n;
        for(unsigned i=0;i<n;++i) {
            const auto* c=stream+offset+i*stride;
            if(be16(c)>=positions || be16(c+2)>=normals) return false;
            const unsigned uv=be16(c+stride-2),color=colored?be16(c+4):0;
            if(uv>r.max_uv) r.max_uv=uv;
            if(color>r.max_color) r.max_color=color;
        }
        offset+=n*stride;
    }
    r.bytes=sizeof(NativeDrawPlan)+std::size_t(r.primitives)*sizeof(DrawPrimitive);
    out=r; return true;
}
NativeDrawPlan* prepare_draw_plan(void* storage, std::size_t capacity,
                                 const std::uint8_t* stream, std::uint32_t bytes,
                                 bool colored, const DrawPlanRequirements& r) {
    if(!storage || reinterpret_cast<std::uintptr_t>(storage)%alignof(NativeDrawPlan) ||
       !stream || r.bytes>capacity || r.bytes!=sizeof(NativeDrawPlan)+
         std::size_t(r.primitives)*sizeof(DrawPrimitive)) return nullptr;
    auto* plan=new(storage) NativeDrawPlan{r.primitives,r.corners,r.max_uv,r.max_color};
    auto* primitives=const_cast<DrawPrimitive*>(plan->primitives());
    unsigned offset=0,pi=0,ci=0,last_end=0,run_min=65535,run_max=0;
    const unsigned stride=colored?8:6;
    while(offset<bytes) {
        const unsigned op=stream[offset++]; if(!op) continue;
        if(bytes-offset<2) return nullptr;
        const unsigned n=be16(stream+offset); offset+=2;
        DrawTopology kind;
        if(offset>0xfffff || !topology(op,n,kind) || n>(bytes-offset)/stride ||
           n>r.corners-ci) return nullptr;
        if(pi && offset-3==last_end && primitives[pi-1].corner_count==n &&
           primitives[pi-1].topology==kind && primitives[pi-1].repeat_minus_one<16383){
            ++primitives[pi-1].repeat_minus_one;
        }else{
            if(pi>=r.primitives)return nullptr;
            auto& span=primitives[pi++];span.source_offset=offset;span.corner_count=n;span.topology=kind;span.repeat_minus_one=0;run_min=65535;run_max=0;
        }
        for(unsigned i=0;i<n;++i){unsigned id=be16(stream+offset+i*stride);
            run_min=std::min(run_min,id);run_max=std::max(run_max,id);}
        primitives[pi-1].local_base=run_min<4095 && run_max-run_min<64?run_min:4095;
        last_end=offset+n*stride;
        ci+=n;
        offset+=n*stride;
    }
    return pi==r.primitives && ci==r.corners?plan:nullptr;
}

namespace {
// These identities exist only on the installation stack. The persisted form is
// one LocalBatch descriptor, regardless of its number of source corner refs.
struct SpanChannel {
    struct Identity { std::uint16_t index,other,color; } ids[kLocalSlots];
    unsigned low=65536,high=0,unique=0;
    bool in_range=true,functional=true;
    // ids is kLocalSlots wide but only [0, unique) is ever read: construct without clearing it and copy only the
    // live entries (visit_draw_locals copies spans once or twice per primitive).
    SpanChannel(){}
    SpanChannel(const SpanChannel& o){*this=o;}
    SpanChannel& operator=(const SpanChannel& o){
        low=o.low;high=o.high;unique=o.unique;in_range=o.in_range;functional=o.functional;
        std::copy(o.ids,o.ids+o.unique,ids);
        return *this;
    }
    void add(unsigned index,unsigned other,unsigned color) {
        if(!in_range)return;
        low=std::min(low,index);high=std::max(high,index);
        if(high-low>=kLocalSlots){in_range=false;functional=false;unique=0;return;}
        unsigned i=0;while(i<unique && ids[i].index!=index)++i;
        if(i==unique)ids[unique++]={std::uint16_t(index),std::uint16_t(other),std::uint16_t(color)};
        else if(ids[i].other!=other || ids[i].color!=color)functional=false;
    }
    void merge(const SpanChannel& other) {
        if(!in_range)return;
        if(!other.in_range){in_range=false;functional=false;unique=0;return;}
        for(unsigned i=0;i<other.unique;++i)
            add(other.ids[i].index,other.ids[i].other,other.ids[i].color);
        functional=functional && other.functional;
    }
    unsigned count()const{return in_range && unique?high-low+1:0;}
};
struct SpanBuild {
    SpanChannel position,normal;
    unsigned first=0,corners=0;
    void add(const std::uint8_t* c,bool colored) {
        const unsigned p=be16(c),n=be16(c+2),color=colored?be16(c+4):0;
        position.add(p,n,color);normal.add(n,p,color);++corners;
    }
    LocalShadeMode shade()const {
        const bool p=position.count() && position.functional;
        const bool n=normal.count() && normal.functional;
        if(p && (!n || position.unique<=normal.unique))return LocalShadeMode::by_position;
        return n?LocalShadeMode::by_normal:LocalShadeMode::none;
    }
    bool useful_channel()const{return position.count() || normal.count();}
    unsigned score()const {
        unsigned score=0;
        if(position.count())score+=corners-position.unique;
        if(normal.count())score+=corners-normal.unique;
        const auto mode=shade();
        if(mode!=LocalShadeMode::none)
            score+=2*(corners-(mode==LocalShadeMode::by_position?position.unique:normal.unique));
        return score;
    }
    LocalBatch descriptor()const {
        return {first,corners,std::uint16_t(position.count()?position.low:0),
            std::uint16_t(normal.count()?normal.low:0),std::uint16_t(position.count()),
            std::uint16_t(normal.count()),shade(),0,std::uint16_t(std::min(score(),65535u))};
    }
};
// Greedily combine legal units without losing a channel or a functional shade
// relation that either input could reuse. A shade-less strip still qualifies
// position/normal work independently. No command or source corner is rewritten.
}
void visit_draw_locals(const NativeDrawPlan& plan,const std::uint8_t* stream,bool colored,void* context,void (*finish)(void*,const LocalBatch&)){
    if(!stream || !finish)return;
    const unsigned stride=colored?8:6;unsigned ordinal=0;
    SpanBuild state;
    auto flush=[&](){if(state.corners && state.score())finish(context,state.descriptor());state=SpanBuild{};};
    for(unsigned i=0;i<plan.primitive_count;++i){const auto& p=plan.primitives()[i];
        for(unsigned rep=0;rep<p.repeats();++rep){
            const auto* start=stream+p.corner_offset(rep,stride);
            const unsigned unit=p.topology==DrawTopology::triangles?3:p.topology==DrawTopology::quads?4:p.corner_count;
            if(!unit)continue;
            for(unsigned at=0;at<p.corner_count;at+=unit){
                SpanBuild next;next.first=ordinal+at;
                for(unsigned j=0;j<unit;++j)next.add(start+(at+j)*stride,colored);
                if(!next.useful_channel()){flush();continue;}
                if(!state.corners){state=next;continue;}
                SpanBuild joined=state;joined.corners+=next.corners;
                joined.position.merge(next.position);joined.normal.merge(next.normal);
                const bool position_lost=(state.position.count() || next.position.count()) && !joined.position.count();
                const bool normal_lost=(state.normal.count() || next.normal.count()) && !joined.normal.count();
                const bool shade_lost=(state.shade()!=LocalShadeMode::none || next.shade()!=LocalShadeMode::none) && joined.shade()==LocalShadeMode::none;
                if(position_lost || normal_lost || shade_lost){flush();state=next;}
                else state=joined;
            }
            ordinal+=p.corner_count;
        }
    }
    flush();
}
namespace {
bool higher_reuse(const LocalBatch& a,const LocalBatch& b){
    if(a.reuse_score!=b.reuse_score)return a.reuse_score>b.reuse_score;
    if(a.corner_count!=b.corner_count)return a.corner_count>b.corner_count;
    return a.first_corner<b.first_corner;
}
}
std::size_t prepare_draw_locals(void* storage,std::size_t capacity,const NativeDrawPlan& plan,
    const std::uint8_t* stream,bool colored){
    if(!stream)return 0;
    if(!storage){
        unsigned count=0;
        visit_draw_locals(plan,stream,colored,&count,[](void* context,const LocalBatch&){++*static_cast<unsigned*>(context);});
        return count?sizeof(DrawLocalPlan)+std::size_t(count)*sizeof(LocalBatch):0;
    }
    if(capacity<sizeof(DrawLocalPlan)+sizeof(LocalBatch) ||
       reinterpret_cast<std::uintptr_t>(storage)%alignof(DrawLocalPlan))return 0;
    const unsigned maximum=(capacity-sizeof(DrawLocalPlan))/sizeof(LocalBatch);
    auto* result=new(storage) DrawLocalPlan{};
    auto* entries=const_cast<LocalBatch*>(result->entries());unsigned count=0;
    // In-place bounded min heap. No candidate-sized staging allocation, and
    // admission changes metadata only: surviving draw order stays source order.
    struct Admission { LocalBatch* entries;unsigned count,maximum; } admission{entries,0,maximum};
    visit_draw_locals(plan,stream,colored,&admission,[](void* context,const LocalBatch& batch){
        auto& sink=*static_cast<Admission*>(context);
        auto* entries=sink.entries;auto& count=sink.count;
        if(count<sink.maximum){entries[count++]=batch;std::push_heap(entries,entries+count,higher_reuse);}
        else if(higher_reuse(batch,entries[0])){
            std::pop_heap(entries,entries+count,higher_reuse);entries[count-1]=batch;
            std::push_heap(entries,entries+count,higher_reuse);
        }
    });
    count=admission.count;
    if(!count)return 0;
    std::sort(entries,entries+count,[](const LocalBatch& a,const LocalBatch& b){return a.first_corner<b.first_corner;});
    unsigned corners=0;for(unsigned i=0;i<count;++i)corners+=entries[i].corner_count;
    const std::size_t bytes=sizeof(DrawLocalPlan)+std::size_t(count)*sizeof(LocalBatch);
    *result={count,corners,unsigned(bytes)};return bytes;
}
DrawPlanBounds* prepare_draw_bounds(void* storage,std::size_t capacity,const NativeDrawPlan& plan,
    const std::uint8_t* stream,bool colored,const std::uint8_t* positions,
    unsigned position_stride,float scale,bool primitive_bounds){
    const unsigned count=primitive_bounds?plan.primitive_count:0;
    if(!storage || !positions || !stream || !plan.corner_count || !std::isfinite(scale) ||
       capacity<sizeof(DrawPlanBounds)+count*sizeof(PrimitiveSphere))return nullptr;
    auto* out=new(storage) DrawPlanBounds{};out->primitive_count=count;
    const float huge=std::numeric_limits<float>::max();
    for(unsigned a=0;a<3;++a){out->group.minimum[a]=huge;out->group.maximum[a]=-huge;}
    const unsigned stride=colored?8:6;
    for(unsigned i=0;i<plan.primitive_count;++i){
        const auto& part=plan.primitives()[i];DrawBounds bounds;
        for(unsigned a=0;a<3;++a){bounds.minimum[a]=huge;bounds.maximum[a]=-huge;}
        for(unsigned repeat=0;repeat<part.repeats();++repeat)for(unsigned c=0;c<part.corner_count;++c){
            const auto* pos=positions+be16(stream+part.corner_offset(repeat,stride)+c*stride)*position_stride;
            for(unsigned a=0;a<3;++a){
                std::int16_t value;std::memcpy(&value,pos+2*a,2);const float v=value*scale;
                bounds.minimum[a]=std::min(bounds.minimum[a],v);bounds.maximum[a]=std::max(bounds.maximum[a],v);
            }
        }
        if(!part.corner_count)continue;
        if(primitive_bounds){
            auto& sphere=const_cast<PrimitiveSphere*>(out->primitives())[i];float radius2=0;
            for(unsigned a=0;a<3;++a){sphere.center[a]=(bounds.minimum[a]+bounds.maximum[a])*0.5f;
                const float extent=(bounds.maximum[a]-bounds.minimum[a])*0.5f;radius2+=extent*extent;}
            // Round outward so target sqrt/quantization cannot shrink the bound.
            sphere.radius=std::sqrt(radius2)*1.000001f+0.00001f;
        }
        for(unsigned a=0;a<3;++a){out->group.minimum[a]=std::min(out->group.minimum[a],bounds.minimum[a]);
            out->group.maximum[a]=std::max(out->group.maximum[a],bounds.maximum[a]);}
    }
    return out;
}
} // namespace re4dc::render
