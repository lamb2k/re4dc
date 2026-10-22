#pragma once
#include <cstdint>

// Scoped36 policy/source provenance, never physical file integrity.
// Call only AFTER MeshPackage::adopt(...,true,true) and the genuine R4PW
// CRC/record validation. The four immutable full-file certificates come from
// 164 key-only remaps (160 OP,4 VA); all geometry/placements/pass/cull remain
// exact and the 36 RGB565 replacements have opaque alpha at every mip level.
// This does not certify filtered RGB appearance, final draws or performance.
namespace re4dc::rect21::provenance {
struct Certificate {
    unsigned room,world_bytes,placements,parts,meshes;
    std::uint32_t physical_body_crc,physical_file_fnv,mesh_crc;
    unsigned mesh_bytes;
    std::uint32_t source_crc;
};
inline constexpr Certificate certificates[] = {
#include "provenance_certificates.inc"
};
static_assert(sizeof(certificates)/sizeof(certificates[0])==4U);
inline std::uint32_t word(const unsigned char* b) {
    return std::uint32_t(b[0])|(std::uint32_t(b[1])<<8)|
           (std::uint32_t(b[2])<<16)|(std::uint32_t(b[3])<<24);
}
inline std::uint32_t fnv(const unsigned char* b,unsigned bytes) {
    std::uint32_t h=2166136261U;
    for(unsigned i=0;i<bytes;++i)h=(h^b[i])*16777619U;
    return h;
}
inline std::uint32_t policy_source_crc(unsigned room,const unsigned char* world,unsigned bytes,
                                       std::uint32_t mesh_crc,unsigned mesh_bytes,
                                       unsigned mesh_parts,unsigned mesh_count) {
    // Unknown tuples retain the actual CRC and ordinary mismatched-metadata
    // fallback. Neither the physical header nor any metadata byte is rewritten.
    if(!world || bytes<32U)return 0;
    const std::uint32_t actual=word(world+20);
    for(const auto& c:certificates) {
        if(room!=c.room || bytes!=c.world_bytes || mesh_crc!=c.mesh_crc ||
           mesh_bytes!=c.mesh_bytes || mesh_parts!=c.parts || mesh_count!=c.meshes ||
           actual!=c.physical_body_crc)continue;
        if(world[0]!='R' || world[1]!='4' || world[2]!='P' || world[3]!='W' ||
           word(world+4)!=1U || word(world+8)!=c.placements ||
           word(world+12)!=c.parts || word(world+16)!=c.meshes ||
           word(world+24)!=0U || word(world+28)!=0U ||
           bytes!=32U+16U*c.parts+52U*c.placements ||
           fnv(world,bytes)!=c.physical_file_fnv)continue;
        return c.source_crc;
    }
    return actual;
}
}