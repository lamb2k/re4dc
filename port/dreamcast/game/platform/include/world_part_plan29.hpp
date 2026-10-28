// Build31: immutable, ordered world-part setup records. No camera, source state,
// texture handle, UV animation or transform is retained here.
#pragma once
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <limits>

namespace re4dc { namespace wp29 {
struct Span { std::uint32_t first,count; };
struct Record {
    unsigned key[6];
    std::uint16_t index,meshlets;
    std::uint8_t original_pass,texture,flags,pad;
};
static_assert(sizeof(Record)==32,"one sequential setup record per cache line");
static_assert(sizeof(unsigned)==4,"renderer texture keys are 32-bit unsigned words");
static_assert(sizeof(Span)==8,"three spans per mesh");
constexpr unsigned kMaxBytes=64U*1024U;
constexpr unsigned kHeapFloor=96U*1024U;
inline unsigned pass_mask(unsigned pass,unsigned flags,bool foliage,bool trans){
    unsigned mask=1U<<pass;
    if(pass==2 && !(flags&1U)){
        if(foliage)mask|=2U;
        if(trans)mask|=3U;
    }
    return mask;
}
struct Layout { unsigned meshes=0,records=0,offset=0,bytes=0; };
template<class Package,class Meta>
inline bool measure(const Package& pk,const Meta* meta,bool foliage,bool trans,Layout& out){
    out={};
    const auto& h=pk.header();
    if(!meta || !h.mesh_count || h.mesh_count>kMaxBytes/24U || h.part_count>65536U)return false;
    unsigned count=0;
    for(unsigned m=0;m<h.mesh_count;++m){
        const auto& mesh=pk.meshes()[m];
        if(mesh.first_part>h.part_count || mesh.part_count>h.part_count-mesh.first_part)return false;
        for(unsigned k=0;k<mesh.part_count;++k){
            const unsigned index=mesh.first_part+k;const auto& p=meta[index];
            if(index>65535U || p.pass>2 || p.cull>2 || pk.parts()[index].meshlet_count>65535U)return false;
            const unsigned mask=pass_mask(p.pass,p.reserved,foliage,trans);
            count+=(mask&1U)+((mask>>1)&1U)+((mask>>2)&1U);
            if(count>kMaxBytes/sizeof(Record))return false;
        }
    }
    const unsigned offset=(h.mesh_count*3U*sizeof(Span)+31U)&~31U;
    if(count>(kMaxBytes-offset)/sizeof(Record))return false;
    out={h.mesh_count,count,offset,offset+count*unsigned(sizeof(Record))};
    return true;
}
template<class Package,class Meta>
inline bool compile(void* memory,unsigned capacity,const Package& pk,const Meta* meta,
                    bool foliage,bool trans,Layout& out){
    if(!memory || (reinterpret_cast<std::uintptr_t>(memory)&31U) ||
       !measure(pk,meta,foliage,trans,out) || capacity<out.bytes)return false;
    auto* spans=static_cast<Span*>(memory);
    auto* records=reinterpret_cast<Record*>(static_cast<unsigned char*>(memory)+out.offset);
    unsigned cursor=0;
    for(unsigned m=0;m<out.meshes;++m){
        const auto& mesh=pk.meshes()[m];
        for(unsigned pass=0;pass<3;++pass){
            Span& s=spans[3U*m+pass];s.first=cursor;
            for(unsigned k=0;k<mesh.part_count;++k){
                const unsigned index=mesh.first_part+k;const auto& p=meta[index];
                if(!(pass_mask(p.pass,p.reserved,foliage,trans)&(1U<<pass)))continue;
                Record& r=records[cursor++];
                r.key[0]=p.crc;r.key[1]=p.fnv;r.key[2]=p.width;r.key[3]=p.height;
                r.key[4]=pass;r.key[5]=p.cull;
                r.index=std::uint16_t(index);r.meshlets=std::uint16_t(pk.parts()[index].meshlet_count);
                r.original_pass=p.pass;r.texture=p.texture;r.flags=p.reserved;r.pad=0;
            }
            s.count=cursor-s.first;
        }
    }
    return cursor==out.records;
}
template<class Meta> inline Meta metadata(const Record& r){
    return Meta{r.key[0],r.key[1],std::uint16_t(r.key[2]),std::uint16_t(r.key[3]),
                r.original_pass,std::uint8_t(r.key[5]),r.texture,r.flags};
}
}}
