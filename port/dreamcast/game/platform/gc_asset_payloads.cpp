#include "include/gc_asset_payloads.h"
#include "include/gc_asset_static.h"
#if RE4DC_GC_ASSET_GATE
#include <cstdint>
extern "C" void re4dc_log(const char*,...);
namespace re4dc_gcasset {
namespace {
PayloadProof* payloads;unsigned payload_count,payload_serial,payload_faults;
const PayloadQuadBatch* payload_quad_batch;
bool overlaps(const void* a,unsigned an,const void* b,unsigned bn){
    if(!a || !b || !an || !bn)return false;
    const auto x=reinterpret_cast<std::uintptr_t>(a),y=reinterpret_cast<std::uintptr_t>(b);
    return x<=y?y-x<an:x-y<bn;
}
bool prepare_owner(PayloadProof& proof,const void* owner,const void* base,unsigned bytes,const void* layout,unsigned layout_bytes){
    bool conflict=false;
    for(auto* old=payloads;old;old=old->next)if(old!=&proof && old->owner &&
        (old->owner==owner || overlaps(base,bytes,old->base,old->bytes) || overlaps(base,bytes,old->layout,old->layout_bytes) ||
         overlaps(layout,layout_bytes,old->base,old->bytes) || overlaps(layout,layout_bytes,old->layout,old->layout_bytes))){
        // A fully revoked composite may retain old accepted bookkeeping after
        // a memory-only close/free. Reap it only here at the safe cold capture.
        // Unpublished copy slots still own their buffers and are not composites.
        const bool revoked=old->owner!=owner && !old->serial && old->layout_asset.value &&
            (old->layout_bytes || !old->layout);
        payload_retire(*old);if(!revoked)conflict=true;
    }
    if(conflict){unresolved(SourceGeometry,"payload-owner-overlap");return false;}
    if(!proof.registered){
        if(payload_count==128){unresolved(SourceGeometry,"payload-owner-capacity");return false;}
        proof.next=payloads;payloads=&proof;proof.registered=true;++payload_count;
    }
    if(payload_serial>=0xfffffffeU){unresolved(SourceGeometry,"payload-serial-exhausted");return false;}
    return true;
}
#if defined(RE4DC_GC_ASSET_SRC) && RE4DC_GC_ASSET_SRC
extern "C" void re4dc_log(const char*,...);
static const void* gca_src_ra;static const char* gca_src_tag="none";
#define GCA_SRC_ENTER(t) do{gca_src_tag=(t);gca_src_ra=__builtin_return_address(0);}while(0)
#define GCA_SRC_LOG(k,d) re4dc_log("GC-ASSET-SRC kind=%s id=%02x%02x%02x%02x entry=%s ra=%08x\n",(k),(d).bytes[0],(d).bytes[1],(d).bytes[2],(d).bytes[3],gca_src_tag,(unsigned)(std::uintptr_t)gca_src_ra)
#else
#define GCA_SRC_ENTER(t) do{}while(0)
#define GCA_SRC_LOG(k,d) do{}while(0)
#endif
CheckedAsset capture(const char* kind,const void* data,unsigned bytes){
    const Digest digest=fingerprint(data,bytes);GCA_SRC_LOG(kind,digest);constexpr char hex[]="0123456789abcdef";char id[41];
    for(unsigned i=0;i<20;++i){id[2*i]=hex[digest.bytes[i]>>4];id[2*i+1]=hex[digest.bytes[i]&15];}id[40]=0;
    return bind_checked(kind,id,digest);
}
CheckedAsset capture_digest(const Digest& digest,const char* kind="geometry"){
    GCA_SRC_LOG(kind,digest);
    constexpr char hex[]="0123456789abcdef";char id[41];
    for(unsigned i=0;i<20;++i){id[2*i]=hex[digest.bytes[i]>>4];id[2*i+1]=hex[digest.bytes[i]&15];}id[40]=0;
    return bind_checked(kind,id,digest);
}
void flush(PayloadProof& proof){
    const unsigned mask=proof.uses;proof.uses=0;
    for(unsigned i=0;i<ConsumerCount;++i)if(mask&(1U<<i)){
        // Revocation retains identities accepted BEFORE the overwrite. A zero
        // serial cannot admit a new use; these pending old uses remain valid.
        if(!proof.owner || !proof.asset.value)unresolved(Consumer(i),"retired-payload");
        else {emitted_checked(Consumer(i),proof.asset);if(proof.layout_bytes || (!proof.layout && proof.layout_asset.value))emitted_checked(Consumer(i),proof.layout_asset);}
    }
}
}
namespace {
constexpr unsigned manifest_bad=0x80000000U,manifest_all=(1U<<StaticRoleCount)-1;
void manifest_word(unsigned char* p,unsigned n){for(unsigned i=0;i<4;++i)p[i]=static_cast<unsigned char>(n>>(8*i));}
unsigned manifest_word(const unsigned char* p){return unsigned(p[0])|(unsigned(p[1])<<8)|(unsigned(p[2])<<16)|(unsigned(p[3])<<24);}
bool manifest_digest(const unsigned char* p){unsigned n=0;for(unsigned i=0;i<32;++i)n|=p[i];return n!=0;}
bool manifest_row(const unsigned char* row,unsigned role){
    if(manifest_word(row)!=role+1)return false;
    const unsigned state=manifest_word(row+4),bytes=manifest_word(row+8);
    if(state==Accepted)return bytes && manifest_digest(row+20) && (role!=SDO3_BASE80 || bytes==80);
    // gc-catalog24b: Rejected = the reader looked and used none of the file (sealed, no bytes)
    return state<=Rejected && !bytes && !manifest_digest(row+20);
}
}
bool static_manifest_begin(StaticManifest& manifest,StaticOwner owner,unsigned room,unsigned profile,const void* base,unsigned bytes){
    manifest={};
    const auto at=reinterpret_cast<std::uintptr_t>(base);
    if(owner<StaticView || owner>StaticIndex || room>0xffffU || !base || !bytes || bytes>40U*1024*1024 || bytes>~std::uintptr_t(0)-at){
        manifest.seen=manifest_bad;return false;
    }
    const Digest geometry=fingerprint(base,bytes);
    if(!manifest_digest(geometry.bytes)){manifest.seen=manifest_bad;return false;}
    const unsigned char magic[8]={'G','C','S','T','C','0','0','1'};
    for(unsigned i=0;i<8;++i)manifest.data[i]=magic[i];
    manifest_word(manifest.data+8,1);manifest_word(manifest.data+12,owner);manifest_word(manifest.data+16,room);
    manifest_word(manifest.data+20,StaticRoleCount);manifest_word(manifest.data+24,profile);
    for(unsigned i=0;i<32;++i)manifest.data[32+i]=geometry.bytes[i];
    manifest.geometry_bytes=bytes;manifest.geometry_base=base;return true;
}
bool static_manifest_note(StaticManifest& manifest,StaticRole role,StaticState state,unsigned bytes,unsigned version,unsigned flags,const Digest* digest){
    if(unsigned(role)>=StaticRoleCount || (manifest.seen&manifest_bad) || (manifest.seen&(1U<<role))){manifest.seen|=manifest_bad;return false;}
    auto* row=manifest.data+64+unsigned(role)*52;
    manifest_word(row,unsigned(role)+1);manifest_word(row+4,state);manifest_word(row+8,bytes);
    manifest_word(row+12,version);manifest_word(row+16,flags);
    if(digest)for(unsigned i=0;i<32;++i)row[20+i]=digest->bytes[i];
    manifest.seen|=1U<<role;
    if(!manifest_row(row,role)){manifest.seen|=manifest_bad;return false;}
    return true;
}
bool static_manifest_bytes(StaticManifest& manifest,StaticRole role,const void* data,unsigned bytes,unsigned version,unsigned flags){
    const auto at=reinterpret_cast<std::uintptr_t>(data);
    if(!data || !bytes || bytes>40U*1024*1024 || bytes>~std::uintptr_t(0)-at){manifest.seen|=manifest_bad;return false;}
    const Digest digest=fingerprint(data,bytes);
    return static_manifest_note(manifest,role,Accepted,bytes,version,flags,&digest);
}
bool static_manifest_seal(const StaticManifest& manifest,Digest& digest){
    digest={};const auto* p=manifest.data;
    const unsigned char magic[8]={'G','C','S','T','C','0','0','1'};
    if(manifest.seen!=manifest_all || !manifest.geometry_base || !manifest.geometry_bytes || manifest.geometry_bytes>40U*1024*1024 ||
       manifest_word(p+8)!=1 || manifest_word(p+12)<StaticView || manifest_word(p+12)>StaticIndex ||
       manifest_word(p+16)>0xffffU || manifest_word(p+20)!=StaticRoleCount || manifest_word(p+28) || !manifest_digest(p+32))return false;
    for(unsigned i=0;i<8;++i)if(p[i]!=magic[i])return false;
    for(unsigned i=0;i<StaticRoleCount;++i)if(!manifest_row(p+64+i*52,i))return false;
    if(manifest_word(p+12)==StaticWorld && manifest_word(p+64+4)!=Accepted)return false;
    digest=fingerprint(p,sizeof manifest.data);return manifest_digest(digest.bytes);
}
bool payload_capture_composite(PayloadProof& proof,const void* owner,const void* base,unsigned bytes,const void* layout,unsigned layout_bytes,const StaticManifest& manifest){
    GCA_SRC_ENTER("payload_capture_composite");
    Digest composite{};
    const auto at=reinterpret_cast<std::uintptr_t>(base),side=reinterpret_cast<std::uintptr_t>(layout);
    if(!owner || !base || base!=manifest.geometry_base || !bytes || bytes!=manifest.geometry_bytes || bytes>~std::uintptr_t(0)-at ||
       bool(layout)!=bool(layout_bytes) || (layout && layout_bytes>~std::uintptr_t(0)-side) ||
       (manifest_word(manifest.data+12)==StaticWorld && !layout) ||
       (layout && manifest_word(manifest.data+64+8)!=layout_bytes) || !static_manifest_seal(manifest,composite)){
#if defined(RE4DC_GC_ASSET_PROF) && RE4DC_GC_ASSET_PROF
        {Digest probe{};re4dc_log("GC-ASSET-PROBE why=composite owner=%u base=%u bytes=%u/%u layout=%u/%u world=%u role1_bytes=%u seal=%u\n",
            owner?1u:0u,base==manifest.geometry_base?1u:0u,bytes,manifest.geometry_bytes,layout?1u:0u,layout_bytes,
            manifest_word(manifest.data+12)==StaticWorld?1u:0u,manifest_word(manifest.data+64+8),static_manifest_seal(manifest,probe)?1u:0u);
         for(unsigned i=0;i<StaticRoleCount;++i)re4dc_log("GC-ASSET-PROBE why=composite-role role=%u state=%u\n",i,manifest_word(manifest.data+64+i*52+4));}
#endif
        payload_retire(proof);unresolved(SourceGeometry,"composite-incomplete");return false;
    }
    if(proof.owner){payload_retire(proof);unresolved(SourceGeometry,"composite-without-retire");return false;}
    if(!prepare_owner(proof,owner,base,bytes,layout,layout_bytes))return false;
    Digest geometry{};for(unsigned i=0;i<32;++i)geometry.bytes[i]=manifest.data[32+i];
    const auto asset=capture_digest(geometry),interpretation=capture_digest(composite,"layout");
    if(!asset.value || !interpretation.value){unresolved(SourceGeometry,"composite-catalog-bind");return false;}
    proof.owner=owner;proof.base=base;proof.bytes=bytes;proof.layout=layout;proof.layout_bytes=layout_bytes;
    proof.asset=asset;proof.layout_asset=interpretation;proof.serial=++payload_serial;return true;
}
void payload_invalidate(PayloadProof& proof,const void* owner){
    proof.serial=0;
    if(!proof.registered || !owner || proof.owner!=owner)payload_faults|=1U<<SourceGeometry;
}
bool payload_capture_receipt(PayloadProof& proof,const void* owner,const Digest& digest,unsigned bytes){
    GCA_SRC_ENTER("payload_capture_receipt");
    if(!bytes || bytes>40U*1024*1024){payload_retire(proof);unresolved(SourceGeometry,"receipt-bounds");return false;}
    if(!payload_capture_digest(proof,owner,digest))return false;
    proof.bytes=bytes;return true;
}
bool static_manifest_receipt(StaticManifest& manifest,StaticRole role,const PayloadProof& proof,const void* owner,unsigned version,unsigned flags){
    AssetDescription description;
    if(!owner || proof.owner!=owner || !proof.serial || proof.base || proof.layout || proof.layout_asset.value ||
       !proof.bytes || !describe_checked(proof.asset,&description))return static_manifest_note(manifest,role,Unproven);
    return static_manifest_note(manifest,role,Accepted,proof.bytes,version,flags,&description.digest);
}
bool payload_capture(PayloadProof& proof,const void* owner,const void* base,unsigned bytes,const void* layout,unsigned layout_bytes){
    GCA_SRC_ENTER("payload_capture");
    if(!owner || !base || !bytes || bool(layout)!=bool(layout_bytes)){payload_retire(proof);unresolved(SourceGeometry,"payload-bounds");return false;}
    if(proof.owner){
        if(proof.owner==owner && proof.base==base && proof.bytes==bytes && proof.layout==layout && proof.layout_bytes==layout_bytes)return true;
        payload_retire(proof);unresolved(SourceGeometry,"payload-without-retire");return false;
    }
    if(!prepare_owner(proof,owner,base,bytes,layout,layout_bytes))return false;
    const CheckedAsset asset=capture("geometry",base,bytes),side=layout_bytes?capture("layout",layout,layout_bytes):CheckedAsset{};
    if(!asset.value || (layout_bytes && !side.value)){unresolved(SourceGeometry,"payload-catalog-bind");return false;}
    proof.owner=owner;proof.base=base;proof.bytes=bytes;proof.layout=layout;proof.layout_bytes=layout_bytes;
    proof.asset=asset;proof.layout_asset=side;proof.serial=++payload_serial;return true;
}
bool payload_capture_fragments(PayloadProof& proof,const void* owner,const PayloadSpan* spans,unsigned count){
    GCA_SRC_ENTER("payload_capture_fragments");
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
    GCA_SRC_ENTER("payload_capture_digest");
    if(!owner || proof.owner){payload_retire(proof);unresolved(SourceGeometry,"digest-owner");return false;}
    for(auto* old=payloads;old;old=old->next)if(old!=&proof && old->owner==owner){payload_retire(*old);unresolved(SourceGeometry,"digest-owner-overlap");return false;}
    if(!proof.registered){if(payload_count==128){unresolved(SourceGeometry,"payload-owner-capacity");return false;}
        proof.next=payloads;payloads=&proof;proof.registered=true;++payload_count;}
    if(payload_serial>=0xfffffffeU){unresolved(SourceGeometry,"payload-serial-exhausted");return false;}
    const CheckedAsset asset=capture_digest(digest);if(!asset.value){unresolved(SourceGeometry,"payload-catalog-bind");return false;}
    proof.owner=owner;proof.asset=asset;proof.serial=++payload_serial;return true;
}
bool payload_copy_register(PayloadProof& proof,const void* owner,const void* base,unsigned capacity){
    const auto start=reinterpret_cast<std::uintptr_t>(base);
    if(!owner || !base || !capacity || capacity>~std::uintptr_t(0)-start || proof.owner){unresolved(SourceGeometry,"copy-owner");return false;}
    bool conflict=false;
    for(auto* old=payloads;old;old=old->next)if(old!=&proof && old->owner &&
        (old->owner==owner || overlaps(base,capacity,old->base,old->bytes) || overlaps(base,capacity,old->layout,old->layout_bytes))){
        payload_retire(*old);conflict=true;
    }
    if(conflict){unresolved(SourceGeometry,"copy-owner-overlap");return false;}
    if(!proof.registered){if(payload_count==128){unresolved(SourceGeometry,"payload-owner-capacity");return false;}
        proof.next=payloads;payloads=&proof;proof.registered=true;++payload_count;}
    proof.owner=owner;proof.base=base;proof.bytes=capacity;return true;
}
bool payload_copy_current(const PayloadProof& proof){
    if(!proof.registered || !proof.owner || !proof.serial || !proof.layout || proof.layout_bytes)return false;
    const auto& source=*static_cast<const PayloadProof*>(proof.layout);
    return source.owner && source.serial && !source.layout_asset.value && source.serial==proof.layout_asset.value &&
        source.asset.value==proof.asset.value && checked_current(source.asset);
}
void payload_copy_invalidate(PayloadProof& proof,const void* owner){
    proof.serial=0;
    if(!proof.registered || !owner || proof.owner!=owner || !proof.base || !proof.bytes){payload_faults|=1U<<SourceGeometry;return;}
}
bool payload_copy_publish(PayloadProof& proof,const void* owner,const PayloadProof& source,unsigned source_serial){
    if(!proof.registered || !owner || proof.owner!=owner || !proof.base || !proof.bytes || proof.serial ||
       &proof==&source || !source.owner || !source_serial || source.serial!=source_serial || source.layout || source.layout_asset.value ||
       !checked_current(source.asset) || payload_serial>=0xfffffffeU){proof.serial=0;payload_faults|=1U<<SourceGeometry;return false;}
    // Preserve coalesced acknowledgements of the same original source across
    // copy generations. A different source cannot relabel pending old uses.
    if(proof.uses && proof.asset.value!=source.asset.value){payload_faults|=proof.uses;proof.uses=0;}
    proof.asset=source.asset;proof.layout=&source;proof.layout_asset.value=source_serial;
    proof.serial=++payload_serial;return true;
}
void payload_retire(PayloadProof& proof){
    flush(proof);proof.owner=proof.base=proof.layout=nullptr;proof.bytes=proof.layout_bytes=0;
    proof.asset={};proof.layout_asset={};proof.serial=proof.uses=0;
}
#if defined(RE4DC_GC_ASSET_PROF) && RE4DC_GC_ASSET_PROF
extern "C" void re4dc_log(const char*,...);
// Probe (diagnostic): first 32 distinct (why, address, caller) per run.
static inline bool gca_probe_once(const char* why,const void* a,const void* c){
    static const void* seen[24][3];static unsigned n;
    for(unsigned i=0;i<n;++i)if(seen[i][0]==why && seen[i][1]==a && seen[i][2]==c)return false;
    if(n>=24){return false;}
    seen[n][0]=why;seen[n][1]=a;seen[n][2]=c;++n;return true;
}
#define GCA_PROBE(why,a,c,fmt,...) do{if(gca_probe_once(why,a,c))re4dc_log("GC-ASSET-PROBE why=%s addr=%p caller=%p " fmt,why,a,c,##__VA_ARGS__);}while(0)
#else
#define GCA_PROBE(...) do{}while(0)
#endif
void payload_accept(PayloadProof* proof,unsigned serial,unsigned mask){
    const unsigned allowed=(1U<<SourceGeometry)|(1U<<Weapon);
    if(!proof || !serial || !proof->owner || proof->serial!=serial || !mask || (mask&~allowed) ||
       (proof->layout && !proof->layout_bytes && !payload_copy_current(*proof))){
        GCA_PROBE("unbound-payload",proof,__builtin_return_address(0),"serial=%u pserial=%u owner=%p layout=%p mask=%x\n",serial,proof?proof->serial:0u,proof?proof->owner:nullptr,proof?proof->layout:nullptr,mask);
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
    const bool valid=batch->uses && batch->count && batch->count<=48 && vertices && vertices==batch->vertices &&
        count==batch->vertex_count && count==batch->count*4;
    if(!valid)payload_faults|=1U<<SourceGeometry;
    // After exact packet-shape authentication each emitted quad has its own
    // frozen owner/serial/class. A stale Weapon receipt cannot erase that
    // known class, nor suppress a different valid owner in this same packet.
    else for(unsigned i=0;i<batch->count;++i){const auto& use=batch->uses[i];payload_accept(use.proof,use.serial,use.mask);}
    return true; // An invalid active batch must never fall back to ambient model identity.
}
PayloadScope::PayloadScope(PayloadProof& proof,const void* owner,const void* model,const void* info,unsigned mask):previous(source_use){
    source_use={0,mask,model,info,&proof};
    if(replay_use.serial!=0xffffffffU){
        source_use={replay_use.payload?replay_use.serial:0,replay_use.mask,model,info,replay_use.payload};
    }else if(proof.owner==owner && proof.serial)source_use={proof.serial,mask,model,info,&proof};
}
}
#endif
