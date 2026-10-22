// Included once after the pl08 package/owner and immutable-ID declarations.
// Default-off render candidate; source palette, owner and material proofs stay.
#include "../tools/d367/texture_atlas21/atlas_bind.h"
#include "leon_atlas_split_data.h"
namespace {
namespace atlas_owner {
struct Cache {
    re4dc_atlas_split::Qualified proof{};
    re4dc_source::ChunkInput input{};
    Re4dcUiImage image{};
    unsigned epoch=0,crc=0,fnv=0;
    bool attempted=false,ready=false;
};
Cache cache[3];
unsigned texture_tokens[2];
unsigned index(unsigned app) {return app==0x100u?0u:app==0x108u?1u:app==0x109u?2u:3u;}
re4dc_atlas_split::ReservedIds ids(unsigned i) {
    return i==0?re4dc_atlas_split::ReservedIds{kLeonAtlasAsset0,kLeonAtlasAsset0+8u}:
                re4dc_atlas_split::ReservedIds{kLeonAtlasAsset0+9u,kLeonAtlasAsset0+21u};
}
unsigned epoch(unsigned i) {
    if(i==0)return 1;
    return pl08_pack.published?pl08_pack.generation:0u;
}
bool prepare(const Re4dcActorPlan& p,unsigned i) {
    using namespace re4dc_atlas_split;
    const unsigned e=epoch(i),role=i==0?1u:0u;
    if(!e || role>=p.count)return false;
    auto& c=cache[i];
    if(!c.attempted || c.epoch!=e || c.crc!=p.crc || c.fnv!=p.fnv || !same(c.input,p.input[role]) || !same(c.image,p.image)) {
        retire(c.proof);c.ready=false;c.attempted=true;c.epoch=e;c.crc=p.crc;c.fnv=p.fnv;
        c.input=p.input[role];c.image=p.image;
        Bundle b{};b.appearance=p.appearance;b.role=role;b.epoch=e;b.source=c.input;
        b.source_crc=p.crc;b.source_fnv=p.fnv;b.source_image=p.image;
        b.tile_image={&texture_tokens[i==0?0:1],nullptr,128,128,6,0xffffffffu,0};
        if(leon_atlas_data::populate(b))c.ready=qualify(b,c.proof);
    }
    return c.ready;
}
}
}
extern "C" int re4dc_atlas_apply(Re4dcActorPlan* p) {
    if(!p)return 0;
    const unsigned i=atlas_owner::index(p->appearance);
    if(i>=3 || !atlas_owner::prepare(*p,i))return 0;
    return re4dc_atlas_split::bind(*p,atlas_owner::cache[i].proof,atlas_owner::epoch(i),atlas_owner::ids(i),*p)?1:0;
}
extern "C" int re4dc_atlas_has_tile(const Re4dcActorPlan* p) {
    if(!p || !p->material_count || p->material_count>kRe4dcActorMaterials)return 0;
    const auto& m=p->materials[p->material_count-1];
    return (m.crc==0x3662c0aau && m.fnv==0xc9e71c00u) || (m.crc==0xfefdf580u && m.fnv==0xf15c1f47u);
}
extern "C" int re4dc_atlas_project(const Re4dcActorPlan* p,Re4dcActorPlan* out) {
    if(!p || !out || !p->material_count || p->material_count>kRe4dcActorMaterials)return 0;
    const unsigned i=atlas_owner::index(p->appearance);if(i>=3)return 0;
    const auto& m=p->materials[p->material_count-1];
    const unsigned c=i==0?0x3662c0aau:0xfefdf580u,f=i==0?0xc9e71c00u:0xf15c1f47u;
    // Capability inspection cannot create a new proof from a retained old plan.
    // Only a freshly built ordinary owner plan may prepare after publication.
    if(m.crc!=c || m.fnv!=f || !atlas_owner::cache[i].ready ||
       atlas_owner::cache[i].epoch!=atlas_owner::epoch(i))return 0;
    return re4dc_atlas_split::project(*p,atlas_owner::cache[i].proof,atlas_owner::epoch(i),atlas_owner::ids(i),*out)?1:0;
}
extern "C" void re4dc_atlas_retire_pl08() {
    for(unsigned i=1;i<3;++i) {
        re4dc_atlas_split::retire(atlas_owner::cache[i].proof);
        atlas_owner::cache[i]=atlas_owner::Cache{};
    }
}
extern "C" int re4dc_atlas_texture_key(const Re4dcUiImage* image,unsigned* crc,unsigned* fnv) {
    if(!image || !crc || !fnv || image->width!=128 || image->height!=128 || image->format!=6 ||
       image->palette || image->palette_bytes || image->palette_format!=0xffffffffu)return 0;
    if(image->pixels==&atlas_owner::texture_tokens[0]){*crc=0x3662c0aau;*fnv=0xc9e71c00u;return 1;}
    if(image->pixels==&atlas_owner::texture_tokens[1]){*crc=0xfefdf580u;*fnv=0xf15c1f47u;return 1;}
    return 0;
}
extern "C" unsigned re4dc_atlas_capability(const Re4dcActorPlan* p) {
    Re4dcActorPlan original{};
    return re4dc_atlas_project(p,&original)?re4dc_actor_material_runs_capability(&original):0u;
}
