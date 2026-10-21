#pragma once
#include "coarse_actor_transaction.h"

#ifndef RE4DC_LEON_ATLAS_SPLIT
#define RE4DC_LEON_ATLAS_SPLIT 0
#endif

// Uninstalled adapter. The owner must still prove the original source material,
// reserve a disjoint global immutable-ID range, pin the new texture/run bytes,
// and retire/reset their proofs with the source package generation. This header
// never bypasses the transaction, material certificate or texture leases.
namespace re4dc_atlas_split {
using re4dc_source::ByteSpan;
using re4dc_source::ChunkInput;
constexpr unsigned MaxSplitRuns=14;
struct Run { ByteSpan uv{},stream{}; unsigned triangles=0,isolated=0; };
struct Bundle {
    unsigned appearance=0,role=0,source_crc=0,source_fnv=0,epoch=0;
    ChunkInput source{};
    Re4dcUiImage source_image{},tile_image{};
    unsigned tile_crc=0,tile_fnv=0,run_count=0;
    Run runs[MaxSplitRuns]{};
};
// This range must be reserved by the real immutable-table owner. Local overlap
// checks below do not prove global ownership or expand the compiled table.
struct ReservedIds { unsigned first=0,table_end=0; };
inline bool same(ByteSpan a,ByteSpan b) { return a.data==b.data && a.size==b.size; }
inline bool same(const ChunkInput& a,const ChunkInput& b) {
    return same(a.positions,b.positions) && same(a.normals,b.normals) && same(a.uv,b.uv) &&
        same(a.stream,b.stream) && same(a.weights,b.weights) && a.position_count==b.position_count &&
        a.normal_count==b.normal_count && a.palette_count==b.palette_count && a.triangles==b.triangles && a.bones==b.bones;
}
inline bool same(const Re4dcUiImage& a,const Re4dcUiImage& b) {
    return a.pixels==b.pixels && a.palette==b.palette && a.width==b.width && a.height==b.height &&
        a.format==b.format && a.palette_format==b.palette_format && a.palette_bytes==b.palette_bytes;
}
inline bool opaque_image(const Re4dcUiImage& a,unsigned side) {
    return a.pixels && !a.palette && a.width==side && a.height==side && a.format==6 &&
        a.palette_format==0xffffffffu && !a.palette_bytes;
}
class Qualified {
    Bundle bundle_{};
    bool ready_=false;
    friend bool qualify(const Bundle&,Qualified&);
    friend bool bind(const Re4dcActorPlan&,const Qualified&,unsigned,ReservedIds,Re4dcActorPlan&);
};
// The package owner calls this before retiring any byte span or reusing an epoch.
// It invalidates the prepared binding; it does not release or own the backing.
inline void retire(Qualified& q) { q=Qualified{}; }
namespace detail {
// Only construct after the complete bounded stream passed source preflight.
class Triangles {
    const unsigned char* h_;
    unsigned meshlet_=0,index_=0,length_=0;
    const unsigned char* first_=nullptr;
    const unsigned char* second_=nullptr;
public:
    explicit Triangles(ByteSpan stream):h_(stream.data) {}
    bool next(const unsigned char* (&corners)[3]) {
        using namespace re4dc_source;
        while(meshlet_<pre_u16(h_+4)) {
            const auto* table=h_+32+meshlet_*8;
            const unsigned ni=(pre_u32(table)>>8)&4095;
            if(index_==ni){++meshlet_;index_=length_=0;continue;}
            const unsigned at=h_[pre_u16(h_+10)*4u+pre_u16(table+6)+index_++];
            const auto* record=h_+pre_u16(h_+8)*4u+(pre_u16(table+4)+(at&127u))*6u;
            const unsigned before=length_++;
            if(before==0)first_=record;
            else if(before==1)second_=record;
            else {
                corners[0]=((before-2)&1u)?second_:first_;
                corners[1]=((before-2)&1u)?first_:second_;
                corners[2]=record;
                first_=second_;second_=record;
                if(at&128u)length_=0;
                return true;
            }
        }
        return false;
    }
};
inline bool same_corner(const unsigned char* a,const unsigned char* b,ByteSpan old_uv,ByteSpan new_uv,bool isolated) {
    using re4dc_source::pre_u16;
    if(pre_u16(a)!=pre_u16(b) || pre_u16(a+2)!=pre_u16(b+2))return false;
    const auto* old=old_uv.data+pre_u16(a+4)*4u;
    const auto* now=new_uv.data+pre_u16(b+4)*4u;
    unsigned u=pre_u16(old),v=pre_u16(old+2);
    if(isolated) {
        if(u<384u*64u || u>512u*64u || v<256u*64u || v>384u*64u)return false;
        u=(u-384u*64u)*4u;v=(v-256u*64u)*4u;
    }
    return pre_u16(now)==u && pre_u16(now+2)==v;
}
}
// Cold qualification only: actual source preflight validates every run before a
// prepared view can be bound. Bytes/spans must remain immutable and pinned for
// the complete epoch. No allocations or game pointers are dereferenced.
inline bool qualify(const Bundle& b,Qualified& out) {
#if !RE4DC_LEON_ATLAS_SPLIT
    (void)b;(void)out;return false;
#else
    const bool standard=b.appearance==0x100u;
    if((!standard && b.appearance!=0x108u && b.appearance!=0x109u) || b.role!=(standard?1u:0u) || !b.epoch ||
       b.source_crc!=(standard?0xec255e66u:0x7506e95fu) || b.source_fnv!=(standard?0x76812316u:0x68cf2211u) ||
       b.tile_crc!=(standard?0x3662c0aau:0xfefdf580u) || b.tile_fnv!=(standard?0xc9e71c00u:0xf15c1f47u) ||
       !opaque_image(b.source_image,512u) || !opaque_image(b.tile_image,128u) ||
       b.source_image.pixels==b.tile_image.pixels || b.source.bones!=119u ||
       b.run_count<3 || b.run_count>MaxSplitRuns)return false;
    re4dc_source::ChunkProof proof{};
    if(re4dc_source::preflight_chunk(b.source,proof)!=re4dc_source::BlobError::None)return false;
    detail::Triangles original(b.source.stream);
    unsigned triangles=0,isolated=0,previous=2;
    for(unsigned i=0;i<b.run_count;++i) {
        const auto& r=b.runs[i];
        if(r.isolated>1 || !r.triangles || r.isolated==previous || r.triangles>b.source.triangles-triangles)return false;
        previous=r.isolated;isolated+=r.isolated;triangles+=r.triangles;
        auto chunk=b.source;chunk.uv=r.uv;chunk.stream=r.stream;chunk.triangles=r.triangles;
        if(re4dc_source::preflight_chunk(chunk,proof)!=re4dc_source::BlobError::None)return false;
        if(std::memcmp(b.source.stream.data+6,r.stream.data+6,2) ||
           std::memcmp(b.source.stream.data+16,r.stream.data+16,16))return false;
        detail::Triangles changed(r.stream);
        const unsigned char* before[3];const unsigned char* after[3];
        for(unsigned t=0;t<r.triangles;++t) {
            if(!original.next(before) || !changed.next(after))return false;
            for(unsigned c=0;c<3;++c)
                if(!detail::same_corner(before[c],after[c],b.source.uv,r.uv,r.isolated!=0))return false;
        }
        if(changed.next(after))return false;
    }
    if(!isolated || isolated==b.run_count || triangles!=b.source.triangles)return false;
    const unsigned char* remaining[3];if(original.next(remaining))return false;
    Qualified next{};next.bundle_=b;next.ready_=true;out=next;return true;
#endif
}
// Atomic plan edit after the original owner has built its ordinary plan. A
// failed/default-off call leaves out untouched, including when out aliases in.
// Palette callbacks, role chunks, infos and existing materials/runs are copied.
inline bool bind(const Re4dcActorPlan& in,const Qualified& qualified,unsigned current_epoch,
                 ReservedIds ids,Re4dcActorPlan& out) {
#if !RE4DC_LEON_ATLAS_SPLIT
    (void)in;(void)qualified;(void)current_epoch;(void)ids;(void)out;return false;
#else
    if(!qualified.ready_)return false;
    const auto& b=qualified.bundle_;
    if(current_epoch!=b.epoch || !current_epoch || in.appearance!=b.appearance ||
       in.count!=(b.appearance==0x100u?8u:b.appearance==0x109u?7u:9u) || b.role>=in.count ||
       in.crc!=b.source_crc || in.fnv!=b.source_fnv || !same(in.image,b.source_image) ||
       !same(in.input[b.role],b.source) || !in.material_count || in.material_count>=kRe4dcActorMaterials ||
       !in.run_count || in.run_count>kRe4dcActorRuns || b.run_count-1>kRe4dcActorRuns-in.run_count ||
       !ids.first || ids.first>ids.table_end || b.run_count-1>ids.table_end-ids.first)return false;
    const auto& atlas=in.materials[0];
    if(!same(atlas.image,b.source_image) || atlas.crc!=b.source_crc || atlas.fnv!=b.source_fnv ||
       atlas.mask.pixels || atlas.mask.palette || atlas.mask.palette_bytes || atlas.material_flags ||
       atlas.blend || atlas.depth_mode || atlas.mask_ref!=256 || atlas.mask_same_uv || atlas.wrap_s || atlas.wrap_t)return false;
    const unsigned last=ids.first+b.run_count-1;
    auto reserved=[&](unsigned id){return id>=ids.first && id<=last;};
    for(unsigned i=0;i<in.count;++i)if(reserved(in.immutable_asset_id[i]))return false;
    for(unsigned i=0;i<in.material_count;++i)
        if(in.materials[i].image.pixels==b.tile_image.pixels ||
           (in.materials[i].crc==b.tile_crc && in.materials[i].fnv==b.tile_fnv))return false;
    unsigned found=0,at=0,previous=0;
    for(unsigned i=0;i<in.run_count;++i) {
        const auto& r=in.runs[i];
        if(r.role>=in.count || r.material>=in.material_count || !r.immutable_asset_id || reserved(r.immutable_asset_id) ||
           (i && r.role<previous))return false;
        previous=r.role;
        if(r.role==b.role) {
            if(++found>1 || r.material || r.immutable_asset_id!=in.immutable_asset_id[b.role] ||
               r.triangles!=b.source.triangles || !same(r.uv,b.source.uv) || !same(r.stream,b.source.stream))return false;
            at=i;
        }
    }
    if(found!=1)return false;
    Re4dcActorPlan next=in;
    const unsigned material=next.material_count++;
    next.materials[material]={};
    next.materials[material].image=b.tile_image;next.materials[material].crc=b.tile_crc;next.materials[material].fnv=b.tile_fnv;
    next.run_count=0;
    for(unsigned i=0;i<in.run_count;++i) {
        if(i!=at)next.runs[next.run_count++]=in.runs[i];
        else for(unsigned j=0;j<b.run_count;++j) {
            const auto& source=b.runs[j];auto& run=next.runs[next.run_count++];
            run={};run.role=b.role;run.material=source.isolated?material:0u;
            run.immutable_asset_id=ids.first+j;run.triangles=source.triangles;run.uv=source.uv;run.stream=source.stream;
        }
    }
    out=next;return true;
#endif
}
}
