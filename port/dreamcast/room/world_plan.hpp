#pragma once
// R4SG v2: offline compiled traversal metadata and bounded scratch, inside the v1 allocation.
// Geometry/materials remain in the validated R4IM/R4PW. No allocation or runtime conversion.
#include <cstdint>
#include <cstring>

namespace re4dc::worldplan {
struct Placement { std::uint16_t affine; std::uint8_t passes,flags; };
struct Cell { float lo[3],hi[3]; std::uint16_t first,count; };
static_assert(sizeof(Placement)==4 && sizeof(Cell)==28);
struct View {
    std::uint8_t* data=nullptr;
    const std::uint32_t* h()const{return reinterpret_cast<const std::uint32_t*>(data);}
    template<class T> T* at(unsigned field)const{return reinterpret_cast<T*>(data+h()[field]);}
    bool adopt(std::uint8_t* b,unsigned size,unsigned lets,unsigned clusters,unsigned placements,unsigned parts,
               unsigned mesh_crc,unsigned mesh_bytes,unsigned side_crc,unsigned ids_crc,unsigned class_crc){
        data=nullptr;
        if(size<128 || std::memcmp(b,"R4SG",4))return false;
        const auto* w=reinterpret_cast<const std::uint32_t*>(b);
        if(w[1]!=2 || w[2]!=lets || !w[3] || w[3]>8 || w[4]!=mesh_crc || w[5]!=mesh_bytes || w[6]!=side_crc ||
           w[8]!=placements || w[9]!=parts || w[10]!=clusters || w[11]>placements || w[12]>8192 || w[13]>31 ||
           w[19]>3*placements || w[22]>placements || w[30]!=ids_crc || w[31]!=class_crc)return false;
        unsigned pos=128;
        auto take=[&](unsigned field,unsigned count,unsigned stride){
            pos=(pos+3U)&~3U;
            if(pos>size || w[field]!=pos || count>(size-pos)/stride)return false;
            pos+=count*stride;return true;
        };
        if(!take(14,lets,2) || !take(15,w[12],16) || !take(16,placements,4) || !take(17,parts,2) ||
           !take(18,4+w[19],2) || !take(20,w[13],28) || !take(21,w[22],2) || !take(25,lets,2) ||
           !take(26,clusters,1) || !take(27,w[11],48) || !take(28,w[11],1) || !take(29,108+w[13],1) ||
           w[23]!=w[25] || w[24]!=size-w[23])return false;
        data=b;
        for(unsigned i=0;i<lets;++i){const unsigned p=at<std::uint16_t>(14)[i];if((p>>13)+1>w[3] || (p&8191U)+(p>>13)+1>w[12]){data=nullptr;return false;}}
        const auto* pl=at<Placement>(16);
        for(unsigned i=0;i<placements;++i)if(!pl[i].passes || pl[i].passes>7 ||
            ((pl[i].flags&1U) && (pl[i].affine>=w[11] || (pl[i].flags>>3)>=w[13]))){data=nullptr;return false;}
        const auto* ix=at<std::uint16_t>(18);
        if(ix[0] || ix[3]!=w[19] || ix[1]>ix[2] || ix[2]>ix[3]){data=nullptr;return false;}
        for(unsigned p=0;p<3;++p){
            unsigned j=ix[p];
            for(unsigned i=0;i<placements;++i)if(pl[i].passes&(1U<<p)){
                if(j>=ix[p+1] || ix[4+j++]!=i){data=nullptr;return false;}
            }
            if(j!=ix[p+1]){data=nullptr;return false;}
        }
        // Scratch is zero in the authored file; a replayed mutable block must not be adopted as fresh metadata.
        for(unsigned i=w[23];i<size;++i)if(b[i]){data=nullptr;return false;}
        return true;
    }
    const std::uint16_t* groups(unsigned let,unsigned& count)const{
        const unsigned entry=at<std::uint16_t>(14)[let];count=(entry>>13)+1;
        return at<std::uint16_t>(15)+8*(entry&8191U);
    }
    void frame(const float* view,const float* projection,const float* viewport,float far)const{
        auto* key=at<std::uint8_t>(29);
        if(*reinterpret_cast<std::uint32_t*>(key+104) && !std::memcmp(key,view,48) &&
           !std::memcmp(key+48,projection,28) && !std::memcmp(key+76,viewport,24) && !std::memcmp(key+100,&far,4))return;
        std::memset(data+h()[23],0,h()[24]);
        std::memcpy(key,view,48);std::memcpy(key+48,projection,28);std::memcpy(key+76,viewport,24);std::memcpy(key+100,&far,4);
        *reinterpret_cast<std::uint32_t*>(key+104)=1;
    }
    std::uint16_t& meshlet(unsigned i)const{return at<std::uint16_t>(25)[i];}
    std::uint8_t& cluster(unsigned i)const{return at<std::uint8_t>(26)[i];}
    static unsigned select(const std::uint16_t* g,unsigned n,unsigned bits,std::uint16_t* r0,std::uint16_t* r1,
                           unsigned& lo,unsigned& hi,unsigned& culled){
        unsigned prev=0,nr=0;lo=255;hi=0;culled=0;
        for(unsigned i=0;i<n;++i,g+=8){
            const unsigned end=g[6];
            if(bits&(1U<<i)){r0[nr]=prev;r1[nr++]=end;const unsigned a=g[7]&255U,b=g[7]>>8;if(a<lo)lo=a;if(b>hi)hi=b;}
            else ++culled;
            prev=end;
        }
        return nr;
    }
    static unsigned selected(const std::uint16_t* g,unsigned n,const std::uint16_t* r1,unsigned nr){
        unsigned bits=0,j=0;
        for(unsigned i=0;i<n && j<nr;++i)if(g[8*i+6]==r1[j]){bits|=1U<<i;++j;}
        return bits;
    }
};
}
