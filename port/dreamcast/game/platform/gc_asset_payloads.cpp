#include "include/gc_asset_payloads.h"
#if RE4DC_GC_ASSET_GATE
#include <cstdint>
namespace re4dc_gcasset {
namespace {
PayloadProof* payloads;unsigned payload_count,payload_serial,payload_faults;
const PayloadQuadBatch* payload_quad_batch;
bool overlaps(const void* a,unsigned an,const void* b,unsigned bn){
    if(!a || !b || !an || !bn)return false;
    const auto x=reinterpret_cast<std::uintptr_t>(a),y=reinterpret_cast<std::uintptr_t>(b);
    return x<=y?y-x<an:x-y<bn;
}
CheckedAsset capture(const char* kind,const void* data,unsigned bytes){
    const Digest digest=fingerprint(data,bytes);constexpr char hex[]="0123456789abcdef";char id[41];
    for(unsigned i=0;i<20;++i){id[2*i]=hex[digest.bytes[i]>>4];id[2*i+1]=hex[digest.bytes[i]&15];}id[40]=0;
    return bind_checked(kind,id,digest);
}
CheckedAsset capture_digest(const Digest& digest){
    constexpr char hex[]="0123456789abcdef";char id[41];
    for(unsigned i=0;i<20;++i){id[2*i]=hex[digest.bytes[i]>>4];id[2*i+1]=hex[digest.bytes[i]&15];}id[40]=0;
    return bind_checked("geometry",id,digest);
}
void flush(PayloadProof& proof){
    const unsigned mask=proof.uses;proof.uses=0;
    for(unsigned i=0;i<ConsumerCount;++i)if(mask&(1U<<i)){
        if(!proof.owner || !proof.serial)unresolved(Consumer(i),"retired-payload");
        else {emitted_checked(Consumer(i),proof.asset);if(proof.layout_bytes)emitted_checked(Consumer(i),proof.layout_asset);}
    }
}
}
bool payload_capture(PayloadProof& proof,const void* owner,const void* base,unsigned bytes,const void* layout,unsigned layout_bytes){
    if(!owner || !base || !bytes || bool(layout)!=bool(layout_bytes)){payload_retire(proof);unresolved(SourceGeometry,"payload-bounds");return false;}
    if(proof.owner){
        if(proof.owner==owner && proof.base==base && proof.bytes==bytes && proof.layout==layout && proof.layout_bytes==layout_bytes)return true;
        payload_retire(proof);unresolved(SourceGeometry,"payload-without-retire");return false;
    }
    bool conflict=false;
    for(auto* old=payloads;old;old=old->next)if(old!=&proof && old->owner &&
        (old->owner==owner || overlaps(base,bytes,old->base,old->bytes) || overlaps(base,bytes,old->layout,old->layout_bytes) ||
         overlaps(layout,layout_bytes,old->base,old->bytes) || overlaps(layout,layout_bytes,old->layout,old->layout_bytes))){payload_retire(*old);conflict=true;}
    if(conflict){unresolved(SourceGeometry,"payload-owner-overlap");return false;}
    if(!proof.registered){
        if(payload_count==128){unresolved(SourceGeometry,"payload-owner-capacity");return false;}
        proof.next=payloads;payloads=&proof;proof.registered=true;++payload_count;
    }
    if(payload_serial>=0xfffffffeU){unresolved(SourceGeometry,"payload-serial-exhausted");return false;}
    const CheckedAsset asset=capture("geometry",base,bytes),side=layout_bytes?capture("layout",layout,layout_bytes):CheckedAsset{};
    if(!asset.value || (layout_bytes && !side.value)){unresolved(SourceGeometry,"payload-catalog-bind");return false;}
    proof.owner=owner;proof.base=base;proof.bytes=bytes;proof.layout=layout;proof.layout_bytes=layout_bytes;
    proof.asset=asset;proof.layout_asset=side;proof.serial=++payload_serial;return true;
}
bool payload_capture_fragments(PayloadProof& proof,const void* owner,const PayloadSpan* spans,unsigned count){
    // Stable compiled source owner only, before preparation. Reloaded packages
    // must use the bounded contiguous capture/retire protocol instead.
    if(!owner || !spans || !count || count>48 || proof.owner){
        payload_retire(proof);unresolved(SourceGeometry,"fragment-owner");return false;
    }
    unsigned bytes=16+4*count;
    for(unsigned i=0;i<count;++i){
        const auto base=reinterpret_cast<std::uintptr_t>(spans[i].data);
        if(!base || !spans[i].bytes || spans[i].bytes>40U*1024*1024-bytes ||
           base+spans[i].bytes<base){unresolved(SourceGeometry,"fragment-bounds");return false;}
        bytes+=spans[i].bytes;
    }
    // Reuse registry/capacity/serial protections; publish only after the entire
    // borrowed sequence hashes successfully.
    struct Reader {
        const PayloadSpan* spans;unsigned count,stage=0,at=0;
        unsigned char word[16]={'G','C','F','R','A','G','0','1',0,0,0,0,0,0,0,0};
        static unsigned read(void* context,void* target,unsigned requested){
            auto& r=*static_cast<Reader*>(context);auto* out=static_cast<unsigned char*>(target);unsigned written=0;
            while(written<requested){
                const void* data;unsigned size;
                if(!r.stage){data=r.word;size=16;}
                else {const unsigned index=(r.stage-1)/2;if(index>=r.count)break;
                    if(r.stage&1){const unsigned n=r.spans[index].bytes;for(unsigned k=0;k<4;++k)r.word[k]=n>>(8*k);data=r.word;size=4;}
                    else {data=r.spans[index].data;size=r.spans[index].bytes;}}
                const unsigned left=size-r.at,take=left<requested-written?left:requested-written;
                const auto* p=static_cast<const unsigned char*>(data)+r.at;
                for(unsigned i=0;i<take;++i)out[written+i]=p[i];
                written+=take;r.at+=take;
                if(r.at==size){r.at=0;++r.stage;}
            }
            return written;
        }
    } reader{spans,count};
    for(unsigned k=0;k<4;++k)reader.word[8+k]=count>>(8*k);
    Digest digest{};if(!fingerprint_read(digest,Reader::read,&reader,bytes))return false;
    return payload_capture_digest(proof,owner,digest);
}
bool payload_capture_digest(PayloadProof& proof,const void* owner,const Digest& digest){
    if(!owner || proof.owner){payload_retire(proof);unresolved(SourceGeometry,"digest-owner");return false;}
    for(auto* old=payloads;old;old=old->next)if(old!=&proof && old->owner==owner){payload_retire(*old);unresolved(SourceGeometry,"digest-owner-overlap");return false;}
    if(!proof.registered){if(payload_count==128){unresolved(SourceGeometry,"payload-owner-capacity");return false;}
        proof.next=payloads;payloads=&proof;proof.registered=true;++payload_count;}
    if(payload_serial>=0xfffffffeU){unresolved(SourceGeometry,"payload-serial-exhausted");return false;}
    const CheckedAsset asset=capture_digest(digest);if(!asset.value){unresolved(SourceGeometry,"payload-catalog-bind");return false;}
    proof.owner=owner;proof.asset=asset;proof.serial=++payload_serial;return true;
}
void payload_retire(PayloadProof& proof){
    flush(proof);proof.owner=proof.base=proof.layout=nullptr;proof.bytes=proof.layout_bytes=0;
    proof.asset={};proof.layout_asset={};proof.serial=proof.uses=0;
}
void payload_accept(PayloadProof* proof,unsigned serial,unsigned mask){
    const unsigned allowed=(1U<<SourceGeometry)|(1U<<Weapon);
    if(!proof || !serial || !proof->owner || proof->serial!=serial || !mask || (mask&~allowed)){
        payload_faults|=(mask&allowed)?mask&allowed:1U<<SourceGeometry;return;
    }
    proof->uses|=mask;
}
void payload_flush_all(){
    const unsigned faults=payload_faults;payload_faults=0;
    for(unsigned i=0;i<ConsumerCount;++i)if(faults&(1U<<i))unresolved(Consumer(i),"unbound-accepted-payload");
    for(auto* proof=payloads;proof;proof=proof->next)flush(*proof);
}
PayloadQuadScope::PayloadQuadScope(const PayloadQuadBatch& batch):previous(payload_quad_batch){
    if(previous)payload_faults|=1U<<SourceGeometry;
    payload_quad_batch=&batch;
}
PayloadQuadScope::~PayloadQuadScope(){payload_quad_batch=previous;}
bool payload_quads_accept(const void* vertices,unsigned count){
    const auto* batch=payload_quad_batch;if(!batch)return false;
    const unsigned allowed=(1U<<SourceGeometry)|(1U<<Weapon);
    bool valid=batch->uses && batch->count && batch->count<=48 && vertices && vertices==batch->vertices &&
        count==batch->vertex_count && count==batch->count*4;
    for(unsigned i=0;valid && i<batch->count;++i){const auto& use=batch->uses[i];
        valid=use.proof && use.serial && use.proof->owner && use.proof->serial==use.serial && use.mask && !(use.mask&~allowed);
    }
    if(!valid)payload_faults|=1U<<SourceGeometry;
    else for(unsigned i=0;i<batch->count;++i){const auto& use=batch->uses[i];payload_accept(use.proof,use.serial,use.mask);}
    return true; // An invalid active batch must never fall back to ambient model identity.
}
PayloadScope::PayloadScope(PayloadProof& proof,const void* owner,const void* model,const void* info,unsigned mask):previous(source_use){
    source_use={};
    if(replay_use.serial!=0xffffffffU){
        if(replay_use.payload)source_use={replay_use.serial,replay_use.mask,model,info,replay_use.payload};
    }else if(proof.owner==owner && proof.serial)source_use={proof.serial,mask,model,info,&proof};
}
}
#endif
