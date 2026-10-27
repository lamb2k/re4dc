#pragma once
#include <cstdint>

// Private 792-descriptor candidate policy/source provenance.
// Call only AFTER MeshPackage::adopt(...,true,true) and the genuine R4PW
// CRC/record validation. These 27 immutable full-file certificates describe
// key-only remaps; geometry/placements/pass/cull remain exact. The added alpha
// descriptors preserve the reviewed shipped-class or intentional-unlisted policy.
// Filtered mip appearance remains unaccepted; r11f/r200 ownership remains held.
// This does not certify filtered RGB appearance, final draws or performance.
namespace re4dc::rect21::provenance {
struct Certificate {
    unsigned room,world_bytes,placements,parts,meshes;
    std::uint32_t physical_body_crc,physical_file_fnv,mesh_crc;
    unsigned mesh_bytes;
    std::uint32_t source_crc;
};
#if defined(RE4DC_SCENERY_N256) && RE4DC_SCENERY_N256
// SCENERY_N256=1 (scenery-cut25): the same 27 rows with the r101 / r103 package crc + bytes of the 256-vertex meshlet
// re-exports (data set n256w25). Swapped, not added: no static growth (the r100 s30 heap-4 floor).
inline constexpr Certificate certificates_base[] = {
#include "provenance_certificates.inc"
};
#if defined(RE4DC_WORLD_SG26) && RE4DC_WORLD_SG26
// WORLD_SG26=1 (lane worldopt26 2026-10-26): data set wsg26 renumbers the corners of 24 certified n256 packages
// (spatial strip groups, same bytes): only their mesh crc differs from the n256 table (sg26_rows_match below).
inline constexpr Certificate certificates_n256[] = {
#include "provenance_certificates_n256.inc"
};
inline constexpr Certificate certificates[] = {
#include "provenance_certificates_sg26.inc"
};
static_assert(sizeof(certificates)==sizeof(certificates_n256));
constexpr bool sg26_rows_match() {
    for(unsigned i=0;i<sizeof(certificates)/sizeof(certificates[0]);++i){
        const auto& a=certificates_n256[i];const auto& b=certificates[i];
        if(a.room!=b.room || a.world_bytes!=b.world_bytes || a.placements!=b.placements || a.parts!=b.parts ||
           a.meshes!=b.meshes || a.physical_body_crc!=b.physical_body_crc || a.physical_file_fnv!=b.physical_file_fnv ||
           a.mesh_bytes!=b.mesh_bytes || a.source_crc!=b.source_crc)return false;
    }
    return true;
}
static_assert(sg26_rows_match());
#else
inline constexpr Certificate certificates[] = {
#include "provenance_certificates_n256.inc"
};
#endif
static_assert(sizeof(certificates)==sizeof(certificates_base));
constexpr bool n256_rows_match() {
    unsigned swapped=0;
    for(unsigned i=0;i<sizeof(certificates)/sizeof(certificates[0]);++i){
        const auto& a=certificates_base[i];const auto& b=certificates[i];
        if(a.room!=b.room || a.world_bytes!=b.world_bytes || a.placements!=b.placements || a.parts!=b.parts ||
           a.meshes!=b.meshes || a.physical_body_crc!=b.physical_body_crc || a.physical_file_fnv!=b.physical_file_fnv ||
           a.source_crc!=b.source_crc)return false;
        if(a.mesh_crc!=b.mesh_crc || a.mesh_bytes!=b.mesh_bytes){
            if(a.room!=0x100U && a.room!=0x101U && a.room!=0x102U && a.room!=0x103U && a.room!=0x104U && a.room!=0x105U && a.room!=0x106U &&
               a.room!=0x107U && a.room!=0x108U && a.room!=0x109U && a.room!=0x10aU && a.room!=0x10bU && a.room!=0x10cU &&
               a.room!=0x10fU && a.room!=0x111U && a.room!=0x112U && a.room!=0x113U && a.room!=0x117U && a.room!=0x118U &&
               a.room!=0x119U && a.room!=0x11aU && a.room!=0x11bU && a.room!=0x11cU && a.room!=0x11dU && a.room!=0x11eU)return false;
            ++swapped;
        }
    }
    return swapped==25U;  // n256w25 + n256x25 + n256z25 + world-n256all + n256r100: r100 r101 r102 r103 r104 r105 r106 r107 r108 r109 r10a r10b r10c r10f r111 r112 r113 r117 r118 r119 r11a r11b r11c r11d r11e
}
static_assert(n256_rows_match());
#else
inline constexpr Certificate certificates[] = {
#include "provenance_certificates.inc"
};
#endif
static_assert(sizeof(certificates)/sizeof(certificates[0])==27U);
#if defined(RE4DC_WORLD_REBUILD27) && RE4DC_WORLD_REBUILD27
// The private experiment changes r101's render geometry, not its placements,
// materials, source identities or changing-object ownership. Candidate receipts
// pin the full source/output hashes offline. Admission still requires the exact
// physical R4PW file, an adopted mesh layout, and its recomputed body CRC below.
// This certifies only that binding; it does not certify appearance or visibility.
#include "world_rebuild27_certificates.inc"
static_assert(sizeof(rebuild27_certificates)/sizeof(rebuild27_certificates[0])>0U);
static_assert(sizeof(rebuild27_certificates)/sizeof(rebuild27_certificates[0])<=64U);
constexpr bool rebuild27_rows_match_source() {
    for(const auto& c:rebuild27_certificates) {
        bool matched=false;
        for(const auto& original:certificates) {
            if(c.room==0x101U && original.room==c.room &&
               c.world_bytes==original.world_bytes && c.placements==original.placements &&
               c.parts==original.parts && c.meshes==original.meshes &&
               c.physical_body_crc==original.physical_body_crc &&
               c.physical_file_fnv==original.physical_file_fnv &&
               c.source_crc==original.source_crc && c.mesh_bytes>0U)matched=true;
        }
        if(!matched)return false;
    }
    return true;
}
static_assert(rebuild27_rows_match_source());
#endif
inline std::uint32_t word(const unsigned char* b) {
    return std::uint32_t(b[0])|(std::uint32_t(b[1])<<8)|
           (std::uint32_t(b[2])<<16)|(std::uint32_t(b[3])<<24);
}
inline std::uint32_t fnv(const unsigned char* b,unsigned bytes) {
    std::uint32_t h=2166136261U;
    for(unsigned i=0;i<bytes;++i)h=(h^b[i])*16777619U;
    return h;
}
#if defined(RE4DC_WORLD_REBUILD27) && RE4DC_WORLD_REBUILD27
inline std::uint32_t policy_source_crc(unsigned room,const unsigned char* world,unsigned bytes,
                                       std::uint32_t mesh_crc,unsigned mesh_bytes,
                                       unsigned mesh_parts,unsigned mesh_count
                                       ,const unsigned char* mesh=nullptr,
                                       std::uint32_t (*mesh_crc32)(const unsigned char*,unsigned)=nullptr
                                       ) {
#else
inline std::uint32_t policy_source_crc(unsigned room,const unsigned char* world,unsigned bytes,
                                       std::uint32_t mesh_crc,unsigned mesh_bytes,
                                       unsigned mesh_parts,unsigned mesh_count) {
#endif
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
#if defined(RE4DC_WORLD_REBUILD27) && RE4DC_WORLD_REBUILD27
    for(const auto& c:rebuild27_certificates) {
        if(room!=c.room || bytes!=c.world_bytes || mesh_crc!=c.mesh_crc ||
           mesh_bytes!=c.mesh_bytes || mesh_parts!=c.parts || mesh_count!=c.meshes ||
           actual!=c.physical_body_crc)continue;
        if(world[0]!='R' || world[1]!='4' || world[2]!='P' || world[3]!='W' ||
           word(world+4)!=1U || word(world+8)!=c.placements ||
           word(world+12)!=c.parts || word(world+16)!=c.meshes ||
           word(world+24)!=0U || word(world+28)!=0U ||
           bytes!=32U+16U*c.parts+52U*c.placements ||
           fnv(world,bytes)!=c.physical_file_fnv)continue;
        // MeshPackage::adopt checks layout/commands, not the stored body CRC.
        // Only these new candidate rows require this additional load-time check.
        // R4IM's CRC covers everything after its fixed 80-byte header, including
        // the v2/v3 LOD header. Use the caller's existing CRC implementation.
        if(!mesh || !mesh_crc32 || mesh_bytes<80U ||
           mesh[0]!='R' || mesh[1]!='4' || mesh[2]!='I' || mesh[3]!='M' ||
           word(mesh+8)!=mesh_bytes || word(mesh+12)!=mesh_crc ||
           word(mesh+16)!=mesh_count || word(mesh+20)!=mesh_parts ||
           mesh_crc32(mesh+80U,mesh_bytes-80U)!=mesh_crc)continue;
        return c.source_crc;
    }
#endif
    return actual;
}
}
