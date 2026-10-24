#pragma once
// Build 12: opt-in payload layouts expressed by ordinary R4IM v3 plain
// meshlets. This header is included only by the candidate world reader.
// It does not change MeshPackage's format, inline definition or ownership.
#include "instanced_mesh.hpp"

namespace re4dc::scenery_data {
enum class Kind : unsigned { None, LocalIndexed, DirectStrips };
constexpr std::uint32_t kLocalIndexed=0x31494c53U; // 'SLI1'
constexpr std::uint32_t kDirectStrips=0x31534453U; // 'SDS1'

inline Kind kind(const room::MeshPackage& package){
    const unsigned marker=package.header().reserved[3];
    return marker==kLocalIndexed?Kind::LocalIndexed:marker==kDirectStrips?Kind::DirectStrips:Kind::None;
}
inline const char* stem(Kind value){return value==Kind::LocalIndexed?"ps2-sli1":"ps2-sds1";}
inline std::uint32_t marker(Kind value){return value==Kind::LocalIndexed?kLocalIndexed:kDirectStrips;}
inline unsigned source_bytes(const room::MeshPackage& package){
    return kind(package)==Kind::None?package.header().bytes:package.header().reserved[1];
}
inline unsigned source_crc(const room::MeshPackage& package){
    return kind(package)==Kind::None?package.header().crc:package.header().reserved[2];
}

// A candidate always names an unmodified source header. The reader binds
// these words to the actual standard file, rather than trusting its marker.
inline bool source_header(const room::MeshHeader& head,unsigned bytes){
    return !std::memcmp(head.magic,"R4IM",4) && (head.version==2U || head.version==3U) &&
        head.bytes==bytes && head.reserved[0]==room::kColorArgb1555 &&
        !head.reserved[1] && !head.reserved[2] && !head.reserved[3];
}

// After MeshPackage::adopt: all ordinary ranges and strip indices are already
// checked. Prove the extra representation invariants once, before publishing
// the package. A malformed marker must never authorize unchecked SQ output.
inline const char* validate(const room::MeshPackage& package,Kind expected,
                            unsigned source_bytes,unsigned source_crc){
    const auto& head=package.header();
    if(!package.valid() || expected==Kind::None || head.version!=3U ||
       head.reserved[0]!=room::kColorArgb1555 || kind(package)!=expected)
        return "variant marker";
    if(head.reserved[1]!=source_bytes || head.reserved[2]!=source_crc)
        return "variant source identity";
    // Queued world picks store the absolute meshlet ID in uint16_t.
    // Sequential expansion must not create an ID that aliases an earlier one.
    if(head.meshlet_count>65536U)return "variant meshlet id capacity";
    // chunk_select reserves part.meshlet_count picks, then selects one level
    // per cluster. Individually in-range overlapping levels must not make
    // that total exceed the reservation. Subtract to avoid sum overflow.
    for(unsigned i=0;i<head.part_count;++i){
        unsigned remaining=package.parts()[i].meshlet_count;
        const auto& lod=package.part_lods()[i];
        for(unsigned c=lod.first_cluster;c<lod.first_cluster+lod.cluster_count;++c){
            const auto& cluster=package.clusters()[c];
            unsigned maximum=0;
            for(unsigned l=cluster.first_level;l<cluster.first_level+cluster.level_count;++l){
                const unsigned count=package.levels()[l].meshlet_count;
                if(count>maximum)maximum=count;
            }
            if(maximum>remaining)return "variant pick capacity";
            remaining-=maximum;
        }
    }
    unsigned next=0;
    for(unsigned i=0;i<head.meshlet_count;++i){
        const auto& meshlet=package.meshlets()[i];
        if(package.indexed(meshlet) || meshlet.first_vertex!=next)
            return "variant local range";
        next+=meshlet.vertex_count;
        const auto* vertices=package.vertices()+meshlet.first_vertex;
        for(unsigned k=0;k<meshlet.vertex_count;++k){
            const auto& v=vertices[k];
            if(v.x<meshlet.bounds_min[0] || v.x>meshlet.bounds_max[0] ||
               v.y<meshlet.bounds_min[1] || v.y>meshlet.bounds_max[1] ||
               v.z<meshlet.bounds_min[2] || v.z>meshlet.bounds_max[2])
                return "variant bounds";
        }
        if(expected==Kind::DirectStrips){
            const auto* s=package.strip_begin(meshlet);
            const auto* end=s+meshlet.strip_bytes;
            unsigned consumed=0;
            while(s<end){
                const unsigned n=*s++;
                if(n>meshlet.vertex_count-consumed)return "direct strip extent";
                for(unsigned k=0;k<n;++k)if(s[k]!=consumed+k)return "direct strip sequence";
                consumed+=n;s+=n;
            }
            if(consumed!=meshlet.vertex_count)return "direct unused vertices";
        }
    }
    return next==head.vertex_count?nullptr:"variant vertex extent";
}

// The emitter consumes this view, not package offsets or the physical 28-byte
// metadata layout. A future draw/bounds split can change this one boundary.
struct Payload {
    const room::CompactVertex12* vertices;
    const std::uint8_t* strips;
    unsigned vertex_count,strip_bytes;
};
inline Payload payload(const room::MeshPackage& package,const room::Meshlet& meshlet){
    return {package.vertices()+meshlet.first_vertex,package.strip_begin(meshlet),
            meshlet.vertex_count,meshlet.strip_bytes};
}
}
