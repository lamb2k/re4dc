// Build 31: portable validation and receipt state for package-bound PCL2/WP29.
// Included only by WORLD_PORTAL29. No private coordinates or game data.
#pragma once
#include <cstdint>
#include <cstring>
#include <cmath>

namespace re4dc::portal29 {
constexpr unsigned kMarker=0x39325057U,kMaxWitnesses=256U,kHeader=64U;
struct Witness { std::uint32_t placement,part; };
struct Layout {
    unsigned room=0,mesh_crc=0,policy_crc=0,mesh_bytes=0;
    unsigned cells=0,portals=0,houses=0,witnesses=0,proof_offset=0,bytes=0;
    float near_max=0;
};
inline unsigned word(const unsigned char* b,unsigned off){unsigned v;std::memcpy(&v,b+off,4);return v;}
inline float scalar(const unsigned char* b,unsigned off){float v;std::memcpy(&v,b+off,4);return v;}
inline unsigned half(const unsigned char* b,unsigned off){return unsigned(b[off])|(unsigned(b[off+1])<<8);}
inline unsigned crc(const unsigned char* b,unsigned bytes,bool file=false){
    unsigned c=~0U;
    for(unsigned i=0;i<bytes;++i){
        c^=(file && i>=60U && i<64U)?0U:b[i];
        for(unsigned bit=0;bit<8;++bit)c=(c>>1)^(0xedb88320U&(0U-(c&1U)));
    }
    return ~c;
}
inline bool bounded(float f){return std::isfinite(f) && std::fabs(f)<=1000000.0f;}
// No dereference beyond the checked 64-byte prefix. Counts bound all products.
inline bool layout(const unsigned char* b,unsigned n,Layout& out){
    if(!b || n<kHeader || std::memcmp(b,"PCL2",4) || word(b,40)!=kMarker || word(b,52)!=1U)return false;
    Layout h;
    h.room=word(b,4);h.mesh_crc=word(b,8);h.policy_crc=word(b,12);h.mesh_bytes=word(b,16);
    h.cells=word(b,20);h.portals=word(b,24);h.bytes=word(b,28);h.near_max=scalar(b,32);
    h.houses=word(b,36);h.proof_offset=word(b,44);h.witnesses=word(b,48);
    if(h.room>0xfffU || !h.mesh_bytes || !h.cells || h.cells>4096U || h.portals>16384U ||
       !h.houses || h.houses>64U || !h.witnesses || h.witnesses>kMaxWitnesses ||
       !bounded(h.near_max) || h.near_max<1.0f || h.near_max>100000.0f || h.bytes!=n ||
       h.proof_offset!=kHeader+32U*h.houses+28U*h.cells+24U*h.portals ||
       n!=h.proof_offset+8U*h.witnesses)return false;
    if(crc(b,n,true)!=word(b,60) || crc(b+h.proof_offset,8U*h.witnesses)!=word(b,56))return false;
    unsigned next_cell=0;
    const unsigned co=kHeader+32U*h.houses,po=co+28U*h.cells;
    for(unsigned house=0;house<h.houses;++house){
        const unsigned ho=kHeader+32U*house;
        const unsigned first=half(b,ho+24),count=half(b,ho+26);
        if(first!=next_cell || !count || count>h.cells-first || word(b,ho+28))return false;
        next_cell+=count;
        float outer[6];for(unsigned a=0;a<6;++a){outer[a]=scalar(b,ho+4U*a);if(!bounded(outer[a]))return false;}
        for(unsigned a=0;a<3;++a)if(!(outer[a]<outer[a+3]))return false;
        for(unsigned c=first;c<first+count;++c){
            const unsigned at=co+28U*c;
            for(unsigned a=0;a<3;++a){
                const float lo=scalar(b,at+4U*a),hi=scalar(b,at+12U+4U*a);
                if(!bounded(lo)||!bounded(hi)||lo>hi ||
                   lo-outer[a]<h.near_max+64.0f || outer[a+3]-hi<h.near_max+64.0f)return false;
            }
            const unsigned fp=half(b,at+24),np=half(b,at+26);
            if(np>24U || fp>h.portals || np>h.portals-fp)return false;
            for(unsigned p=fp;p<fp+np;++p){
                const unsigned pt=po+24U*p,axis=word(b,pt);
                if(axis>2U)return false;
                const float plane=scalar(b,pt+4),u0=scalar(b,pt+8),u1=scalar(b,pt+12),v0=scalar(b,pt+16),v1=scalar(b,pt+20);
                if(!bounded(plane)||!bounded(u0)||!bounded(u1)||!bounded(v0)||!bounded(v1)||
                   !(u0<u1 && v0<v1) || (plane!=outer[axis] && plane!=outer[axis+3]))return false;
            }
        }
    }
    if(next_cell!=h.cells)return false;
    unsigned last_pl=0,last_part=0;
    for(unsigned q=0;q<h.witnesses;++q){
        const unsigned pl=word(b,h.proof_offset+8U*q),part=word(b,h.proof_offset+8U*q+4U);
        if(q && (pl<last_pl || (pl==last_pl && part<=last_part)))return false;
        last_pl=pl;last_part=part;
    }
    out=h;return true;
}

// Successful opaque source parts belong to one exact image/camera/generation.
// A skipped or refused part never commits. A changed key clears every receipt.
struct Receipts {
    unsigned frame=~0U,scene=~0U,generation=~0U,count=0;
    unsigned bits[kMaxWitnesses/32]{};
    float key[27]{};
    void clear(){frame=scene=generation=~0U;count=0;std::memset(bits,0,sizeof(bits));}
    void sync(unsigned f,unsigned s,unsigned g,const float* k){
        if(frame!=f || scene!=s || generation!=g || std::memcmp(key,k,sizeof(key))){
            clear();frame=f;scene=s;generation=g;std::memcpy(key,k,sizeof(key));
        }
    }
    void commit(unsigned q){
        if(q>=kMaxWitnesses)return;
        const unsigned mask=1U<<(q&31U);
        if(!(bits[q>>5]&mask)){bits[q>>5]|=mask;++count;}
    }
    bool complete(unsigned n)const{return n && n<=kMaxWitnesses && count==n;}
};
} // namespace re4dc::portal29
