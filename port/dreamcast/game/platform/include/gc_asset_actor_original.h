#pragma once
// Pure bounded parser for the immutable, pre-calcModelAddr ModelData view.
// This proves constituent ownership, never provenance. No IO or allocation.
#include <cstdint>
#include <cstring>
namespace re4dc_gcasset {
struct OriginalModelProof {
    const unsigned char* data=nullptr;
    unsigned serial=0,offset[7]{},flags=0,counts=0,joints=0,format=0,shape=0;
    unsigned uv_bytes=0;
    unsigned color_bytes:19,weights:1,reserved:12;
    unsigned parts_bytes=0,shape_bytes=0;
    OriginalModelProof():color_bytes(0),weights(0),reserved(0){}
};
inline unsigned original_word(const void* p){unsigned x;std::memcpy(&x,p,4);return x;}
inline unsigned original_half(const void* p){unsigned short x;std::memcpy(&x,p,2);return x;}
inline bool original_inside(const void* base,unsigned bytes,const void* data,unsigned n){
    const auto a=reinterpret_cast<std::uintptr_t>(base),b=reinterpret_cast<std::uintptr_t>(data);
    return base && data && b>=a && b-a<=bytes && n<=bytes-unsigned(b-a);
}
inline bool original_range(const OriginalModelProof& p,const void* base,unsigned bytes,unsigned offset,unsigned n){
    const auto a=reinterpret_cast<std::uintptr_t>(p.data);
    return offset<=~std::uintptr_t(0)-a && original_inside(base,bytes,reinterpret_cast<const void*>(a+offset),n);
}
inline bool original_parse(OriginalModelProof& out,unsigned serial,const void* base,unsigned bytes,const void* data){
    out={};if(!serial || !original_inside(base,bytes,data,64))return false;
    const auto* d=static_cast<const unsigned char*>(data);const unsigned version=original_word(d+60);
    if(version!=0x20010801U && version!=0x20030818U)return false;
    OriginalModelProof p;p.data=d;p.serial=serial;
    constexpr unsigned fields[7]={0,12,16,20,28,48,52};
    for(unsigned i=0;i<7;++i)p.offset[i]=original_word(d+fields[i]);
    p.flags=original_word(d+32);p.counts=original_word(d+56);p.joints=original_word(d+24);
    p.format=original_word(d+40);p.shape=original_word(d+44);
    const unsigned nv=p.counts&65535U,nn=p.counts>>16,nparts=(p.joints>>8)&255U,nlist=p.joints>>16;
    if(!nv || !nn || !nparts || !nlist || nlist>4096 || (p.format&255U)>30 ||
       !original_range(p,base,bytes,p.offset[0],nparts*16) ||
       !original_range(p,base,bytes,p.offset[5],nv*8) ||
       !original_range(p,base,bytes,p.offset[6],nn*((p.flags&0x20000000U)?4:8)))return false;
    const unsigned ext=p.format>>16,weights=ext>255?ext:p.joints&255U;
    p.weights=weights && original_range(p,base,bytes,p.offset[3],weights*(ext>255?12:8));
    const unsigned stride=(p.flags&0x80000000U)?8:6;
    unsigned cursor=p.offset[4],max_uv=0,max_color=0;bool corners=false;
    for(unsigned k=0;k<nlist;++k){
        if(!original_range(p,base,bytes,cursor,32))return false;
        const unsigned n=original_word(d+cursor+24);if(n>1024U*1024 || cursor>~0U-32 ||
            !original_range(p,base,bytes,cursor+32,n))return false;
        const auto* stream=d+cursor+32;unsigned at=0;
        while(at<n){
            const unsigned op=stream[at++];if(!op)continue;
            if(n-at<2)return false;
            const unsigned count=(unsigned(stream[at])<<8)|stream[at+1];at+=2;
            if(count>(n-at)/stride || (op==0x80 && count%4) || (op==0x90 && count%3) ||
                (op!=0x80 && op!=0x90 && op!=0x98 && op!=0xa0))return false;
            for(unsigned j=0;j<count;++j){
                const auto* v=stream+at+j*stride;
                const unsigned vi=(unsigned(v[0])<<8)|v[1],ni=(unsigned(v[2])<<8)|v[3];
                const unsigned uv=(unsigned(v[stride-2])<<8)|v[stride-1];
                if(vi>=nv || ni>=nn)return false;
                if(!corners || uv>max_uv)max_uv=uv;
                if(stride==8){const unsigned color=(unsigned(v[4])<<8)|v[5];if(!corners || color>max_color)max_color=color;}
                corners=true;
            }
            at+=count*stride;
        }
        if(cursor+32>~0U-n)return false;
        cursor+=32+n;
    }
    if(!corners || cursor<p.offset[4])return false;
    p.parts_bytes=cursor-p.offset[4];p.uv_bytes=(max_uv+1)*4;
    if(!original_range(p,base,bytes,p.offset[2],p.uv_bytes))return false;
    if(stride==8 && original_range(p,base,bytes,p.offset[1],(max_color+1)*4))p.color_bytes=(max_color+1)*4;
    if(p.shape && original_range(p,base,bytes,p.shape,4)){
        const unsigned count=original_word(d+p.shape);
        if(count<=256 && p.shape<=~0U-4 && original_range(p,base,bytes,p.shape+4,count*8)){
            unsigned end=p.shape+4+count*8;bool good=true;
            for(unsigned i=0;i<count;++i){
                const auto* e=d+p.shape+4+i*8;const unsigned offset=original_word(e),num=original_word(e+4);
                if(num>65535 || offset>~0U-p.shape-4 || !original_range(p,base,bytes,p.shape+4+offset,num*8)){good=false;break;}
                const unsigned stop=p.shape+4+offset+num*8;if(stop>end)end=stop;
                for(unsigned j=0;j<num;++j)if(original_half(d+p.shape+4+offset+j*8)>=nv){good=false;break;}
            }
            if(good)p.shape_bytes=end-p.shape;
        }
    }
    out=p;return true;
}
// Runtime source fields are checked against captured offsets, not a fresh hash
// of relocated/morphed bytes. Prepared destinations need a separate derivation.
struct OriginalModelInput {
    const void* data=nullptr;const void* head=nullptr;const void* colors=nullptr;const void* uv=nullptr;
    const void* weights=nullptr;const void* parts=nullptr;const void* positions=nullptr;const void* normals=nullptr;
    const void* part=nullptr;const void* stream=nullptr;
    unsigned stream_bytes=0,flags=0,counts=0,joints=0,format=0,shape=0;
    bool uses_colors=false,uses_weights=false,uses_shape=false;
};
inline bool original_stream_contains(const OriginalModelProof& p,const void* target,unsigned bytes){
    if(!p.serial || !target || !bytes)return false;
    unsigned cursor=p.offset[4];
    for(unsigned k=0;k<(p.joints>>16);++k){
        if(cursor-p.offset[4]>p.parts_bytes || p.parts_bytes-(cursor-p.offset[4])<32)return false;
        const auto* part=p.data+cursor;const unsigned length=original_word(part+24);
        if(length>p.parts_bytes-(cursor-p.offset[4])-32)return false;
        if(original_inside(part+32,length,target,bytes))return true;
        cursor+=32+length;
    }
    return false;
}
inline bool original_fields(const OriginalModelProof& p,const OriginalModelInput& in){
    if(!p.serial || in.data!=p.data || in.flags!=p.flags || in.counts!=p.counts || in.joints!=p.joints ||
        in.format!=p.format || in.shape!=p.shape)return false;
    const void* actual[7]={in.head,in.colors,in.uv,in.weights,in.parts,in.positions,in.normals};
    for(unsigned i=0;i<7;++i){
        if(i==1 && !in.uses_colors)continue;
        if(i==3 && !in.uses_weights)continue;
        if(actual[i]!=p.data+p.offset[i])return false;
    }
    if((in.uses_colors && !p.color_bytes) || (in.uses_weights && !p.weights) ||
        (in.uses_shape && (!p.shape || !p.shape_bytes)))return false;
    return true;
}
inline bool original_select(const OriginalModelProof& p,const OriginalModelInput& in){
    if(!original_fields(p,in))return false;
    // Only a complete source-declared part, not an interior stream alias.
    unsigned cursor=p.offset[4];
    for(unsigned k=0;k<(p.joints>>16);++k){
        if(cursor-p.offset[4]>p.parts_bytes || p.parts_bytes-(cursor-p.offset[4])<32)return false;
        const auto* part=p.data+cursor;const unsigned bytes=original_word(part+24);
        if(bytes>p.parts_bytes-(cursor-p.offset[4])-32)return false;
        if(in.part==part)return in.stream==part+32 && in.stream_bytes==bytes;
        cursor+=32+bytes;
    }
    return false;
}
}
