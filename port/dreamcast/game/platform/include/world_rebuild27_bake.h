#pragma once
// Private PS2-only house atlas routing. Included only by the default-off knob.
// Geometry/body and unchanged R4PW are authenticated by WORLD_REBUILD27 first.
namespace re4dc::world_bake27 {
struct Range { unsigned part,first,count,key[4]; };
#include "world_rebuild27_bake_certificates.inc"
constexpr unsigned range_count=sizeof(ranges)/sizeof(ranges[0]);
constexpr bool same_key(const unsigned* a,const unsigned* b){
    return a[0]==b[0] && a[1]==b[1] && a[2]==b[2] && a[3]==b[3];
}
constexpr int texture_slot(const unsigned* key){
    return same_key(key,textures[0])?0:same_key(key,textures[1])?1:-1;
}
constexpr bool valid(){
    if(!mesh_crc || !mesh_bytes || !range_count || range_count>16U ||
       sizeof(textures)/sizeof(textures[0])!=2U || same_key(textures[0],textures[1]))return false;
    for(const auto& t:textures)if(!(t[0]|t[1]) || t[2]!=512U || t[3]!=512U)return false;
    for(unsigned i=0;i<range_count;++i){const auto& r=ranges[i];
        if((r.part!=160U && r.part!=288U) || !r.count || r.first>=65536U ||
           r.count>65536U-r.first || texture_slot(r.key)<0)return false;
        if(i && (r.part<ranges[i-1].part ||
          (r.part==ranges[i-1].part && r.first<ranges[i-1].first+ranges[i-1].count)))return false;
    }
    return true;
}
static_assert(valid(), "Invalid private house bake routing certificate");
constexpr bool matches(unsigned room,unsigned crc,unsigned bytes){
    return room==0x101U && crc==mesh_crc && bytes==mesh_bytes;
}
constexpr int slot(unsigned part,unsigned let){
    for(const auto& r:ranges)if(part==r.part && let>=r.first && let-r.first<r.count)return texture_slot(r.key);
    return -1;
}
constexpr bool owns_part(unsigned part){for(const auto& r:ranges)if(part==r.part)return true;return false;}
template<class Pick> unsigned run(const Pick* picks,unsigned count,unsigned part){
    if(!count)return 0;
    const int first=slot(part,picks[0].let);unsigned n=1;
    while(n<count && slot(part,picks[n].let)==first)++n;
    return n;
}
} // namespace re4dc::world_bake27
