#include "include/gc_asset_motion_source.h"
#if RE4DC_GC_ASSET_MOTION_SOURCE
#include <cstdint>
#include <cstring>
#include <new>
#include <type_traits>
namespace re4dc_gcasset {
namespace {
constexpr unsigned SourceCount=128,SubjectCount=64,MaxBytes=40U*1024*1024;
struct Source {const void* owner=nullptr;const void* base=nullptr;unsigned bytes=0,serial=0,role=0;CheckedAsset asset{};bool used=false;const void* alias=nullptr;unsigned alias_bytes=0;Digest digest{};};
struct SubjectReceipt {unsigned serial[MotionSourceLimit]{},count=0,fault=0;};
struct Subject {const void* owner=nullptr;SubjectReceipt receipt{};unsigned generation=0;};
struct State {
    Source sources[SourceCount]{};Subject subjects[SubjectCount]{};
    unsigned next_serial=0,subject_generation=0,faults=0,scope_depth=0;const void* view=nullptr;
    MotionReceipt context{},pending{};bool pending_accounted=false,frozen_context=false;
};
State* state=nullptr;unsigned bootstrap_fault=0;
static_assert(sizeof(void*)!=4 || sizeof(State)<=MotionStorageBytes,"Motion state must fit its existing 12KiB slab partition");
static_assert(alignof(State)<=MotionStorageAlignment,"caller supplies 32-byte aligned backing");
static_assert(std::is_trivially_destructible<State>::value,"common slab has process lifetime; generations retire separately");
static_assert(sizeof(void*)!=4 || sizeof(Source)<=68,"bounded immutable source metadata");
static_assert(sizeof(void*)!=4 || sizeof(MotionReceipt)==64,"bounded receipt with exact subject-generation witnesses");
bool contains(const void* base,unsigned bytes,const void* p,unsigned n){
    const auto a=reinterpret_cast<std::uintptr_t>(base),b=reinterpret_cast<std::uintptr_t>(p);
    return base && p && bytes && n && b>=a && b-a<=bytes && n<=bytes-(b-a);
}
bool bounds(const void* p,unsigned bytes){return p && bytes && bytes<=MaxBytes && bytes<=~std::uintptr_t(0)-reinterpret_cast<std::uintptr_t>(p);}
bool overlap(const void* a,unsigned an,const void* b,unsigned bn){
    const auto x=reinterpret_cast<std::uintptr_t>(a),y=reinterpret_cast<std::uintptr_t>(b);
    return x<=y?y-x<an:x-y<bn;
}
template<class Receipt> void add(Receipt& out,unsigned serial){
    if(!serial){out.fault=1;return;}
    for(unsigned i=0;i<out.count;++i)if(out.serial[i]==serial)return;
    if(out.count==MotionSourceLimit){out.fault=1;return;}
    out.serial[out.count++]=serial;
}
template<class Receipt> void merge(MotionReceipt& out,const Receipt& in){
    if(in.count>MotionSourceLimit){out.fault=1;return;}
    out.fault|=in.fault;
    for(unsigned i=0;i<in.count;++i)add(out,in.serial[i]);
}
Subject* subject(const void* owner,bool create){
    if(!owner)return nullptr;
    Subject* free=nullptr;
    for(auto& s:state->subjects){if(s.owner==owner)return &s;if(!s.owner && !free)free=&s;}
    if(create && free && state->subject_generation<0xfffffffeU){free->owner=owner;free->generation=++state->subject_generation;return free;}
    return nullptr;
}
unsigned lookup(const void* p,MotionSourceRole role){
    unsigned serial=0;
    for(const auto& s:state->sources)if(s.serial && contains(s.base,s.bytes,p,1) && (s.role==unsigned(role) || s.role==MotionEvd || (role==MotionShape && s.role==MotionFcv))){
        if(serial)return 0;
        serial=s.serial;
    }
    return serial;
}
CheckedAsset capture_digest(const Digest& digest){
    char id[41];constexpr char hex[]="0123456789abcdef";
    for(unsigned i=0;i<20;++i){id[2*i]=hex[digest.bytes[i]>>4];id[2*i+1]=hex[digest.bytes[i]&15];}id[40]=0;
    return bind_checked("motion",id,digest);
}
CheckedAsset capture(const void* base,unsigned bytes){return capture_digest(fingerprint(base,bytes));}
unsigned word(const unsigned char* p){unsigned v;std::memcpy(&v,p,4);return v;}
unsigned half(const unsigned char* p){return unsigned(p[0])|(unsigned(p[1])<<8);}
unsigned stride(unsigned type){constexpr unsigned sizes[16]={12,8,6,0,10,6,4,0,9,5,3,0,0,0,0,4};return type<16?sizes[type]:0;}
bool leaf(const void* base,unsigned bytes,const void* key,unsigned type){
    const unsigned size=stride(type);if(!size || !contains(base,bytes,key,2))return false;
    const auto* p=static_cast<const unsigned char*>(key);unsigned left=bytes-unsigned(p-static_cast<const unsigned char*>(base));
    for(unsigned axis=0;axis<3;++axis){
        if(left<2)return false;
        const unsigned count=half(p);
        if(!count || count>(left-2)/(2+size))return false;
        const unsigned used=2+count*(2+size);p+=used;left-=used;
    }
    return true;
}
bool original_fcv(const void* base,unsigned bytes){
    if(bytes<16)return false;
    const auto* p=static_cast<const unsigned char*>(base);const unsigned count=p[2];
    const unsigned prefix=((3+3*count+3)&~3U)+4+4*count;
    if(!count || prefix>bytes)return false;
    const unsigned table=prefix-4*count;
    for(unsigned i=0;i<count;++i){const unsigned at=word(p+table+4*i);if(at<prefix || at>=bytes || !leaf(base,bytes,p+at,half(p+3+2*i)>>12))return false;}
    return true;
}
MotionReceipt selected(const void* owner){
    auto* s=subject(owner,false);MotionReceipt result{};
    if(s)merge(result,s->receipt);else result.fault=1;
    return result;
}
}
bool motion_source_adopt(const void* owner,const void* base,unsigned bytes,MotionSourceRole role){
    if(!state){bootstrap_fault=1;return false;}
    if(!owner || !bounds(base,bytes) || role<MotionFcv || role>MotionBind){unresolved(Motion,"motion-source-bounds");return false;}
    Source* free=nullptr;
    for(auto& s:state->sources){
        if(s.serial && s.owner==owner && s.base==base){
            if(s.bytes==bytes && s.role==unsigned(role))return true;
            unresolved(Motion,"motion-source-replaced-without-retire");return false;
        }
        if(s.serial && overlap(base,bytes,s.base,s.bytes)){unresolved(Motion,"motion-source-overlap");return false;}
        if(!s.owner && !s.used && !free)free=&s;
    }
    if(!free || state->next_serial>=0xfffffffeU){unresolved(Motion,"motion-source-capacity-or-serial");return false;}
    // Relocated tables contain absolute pointers. Reject those before a new
    // owner can accidentally call prepared output an original FCV source.
    if((role==MotionFcv || role==MotionShape) && !original_fcv(base,bytes)){
        unresolved(Motion,"motion-original-fcv-layout");return false;
    }
    const CheckedAsset asset=capture(base,bytes);
    if(!asset.value){unresolved(Motion,"motion-source-catalog-bind");return false;}
    *free={owner,base,bytes,++state->next_serial,unsigned(role),asset,false};return true;
}
bool motion_source_archive(const void* owner,const void* base,unsigned bytes){
    if(!state){bootstrap_fault=1;return false;}
    if(!owner || !bounds(base,bytes) || bytes<16){unresolved(Motion,"motion-archive-bounds");return false;}
    const auto* p=static_cast<const unsigned char*>(base);const unsigned count=word(p),rel=word(p+4);
    if(count>4096 || count>(bytes-16)/8 || (rel && rel>bytes)){unresolved(Motion,"motion-archive-directory");return false;}
    const unsigned directory=16+8*count;bool external=false;
    for(unsigned i=0;i<count;++i){
        const unsigned at=word(p+16+4*i);if(at<directory || at>=bytes){unresolved(Motion,"motion-archive-span");return false;}
        const auto* tag=p+16+4*count+4*i;
        const bool motion_member=!std::memcmp(tag,"FCV",3) || !std::memcmp(tag,"BIN",3) ||
            !std::memcmp(tag,"EVD",3) || !std::memcmp(tag,"EVS",3);
        // A nonzero REL offset terminates original asset ownership. Never
        // reinterpret REL/code bytes as a last BIN/FCV by falling back to EOF.
        if(rel && motion_member && at>=rel){unresolved(Motion,"motion-member-at-rel");return false;}
        if(!std::memcmp(tag,"MTC",3))external=true;
        // Zero-tag alias slots may point at their next real member. Reject all
        // nonempty aliases so no captured span has two interpretations.
        for(unsigned j=0;j<i;++j)if(word(p+16+4*j)==at && word(tag) && word(p+16+4*count+4*j)){
            unresolved(Motion,"motion-archive-alias");return false;
        }
    }
    bool good=true;
    for(unsigned i=0;i<count;++i){
        const auto* tag=p+16+4*count+4*i;MotionSourceRole role;
        if(!std::memcmp(tag,"FCV",3)){if(external)continue;role=MotionFcv;}
        else if(!std::memcmp(tag,"EVD",3) || !std::memcmp(tag,"EVS",3))role=MotionEvd;
        else if(!std::memcmp(tag,"BIN",3))role=MotionBind;
        else continue;
        const unsigned at=word(p+16+4*i);unsigned end=rel>at?rel:bytes;
        for(unsigned j=0;j<count;++j){const unsigned next=word(p+16+4*j);if(next>at && next<end)end=next;}
        if(end<=at || !motion_source_adopt(owner,p+at,end-at,role))good=false;
    }
    return good;
}
unsigned motion_source_external_capture(const void* owner,const void* proxy,unsigned proxy_bytes,const void* original,unsigned bytes){
    if(!state){bootstrap_fault=1;return 0;}
    if(!owner || !bounds(proxy,proxy_bytes) || !bounds(original,bytes) || !original_fcv(original,bytes))return 0;
    if(proxy_bytes>bytes || std::memcmp(proxy,original,proxy_bytes))return 0;
    Source* free=nullptr;
    for(auto& s:state->sources){
        if(s.owner==owner)return 0; // overwrite must revoke before capture
        if(s.serial && overlap(original,bytes,s.base,s.bytes))return 0;
        if(!s.owner && !s.used && !free)free=&s;
    }
    if(!free || state->next_serial>=0xfffffffeU)return 0;
    const Digest digest=fingerprint(original,bytes);
    *free={owner,original,bytes,++state->next_serial,MotionFcv,{},false,proxy,proxy_bytes,digest};
    return free->serial;
}
unsigned motion_source_external_serial(const void* owner,const void* data,const void* proxy){
    if(!state)return 0;
    for(const auto& s:state->sources)if(s.owner==owner && s.base==data && s.alias==proxy && s.serial)return s.serial;
    return 0;
}
bool motion_source_external_publish(const void* owner,unsigned serial){
    if(!state){bootstrap_fault=1;return false;}
    for(auto& s:state->sources)if(s.owner==owner && s.serial==serial && s.alias){
        if(s.asset.value)return checked_current(s.asset);
        const CheckedAsset asset=capture_digest(s.digest);
        if(!asset.value){unresolved(Motion,"motion-external-catalog-bind");return false;}
        // Publication is after acquire's mutex release while this Slot is
        // lease-pinned. A reused owner or serial cannot take this identity.
        if(s.owner!=owner || s.serial!=serial){unresolved(Motion,"motion-external-publication-race");return false;}
        s.asset=asset;return true;
    }
    unresolved(Motion,"motion-external-source-unbound");return false;
}
void motion_source_external_invalidate(const void* owner){
    if(!state)return;
    for(auto& s:state->sources)if(s.owner==owner){
        // Old accepted uses keep their original checked token until unlocked
        // flush. The revoked serial cannot grant any new/deferred use.
        if(s.used){s.owner=nullptr;s.base=nullptr;s.bytes=0;s.serial=0;s.alias=nullptr;s.alias_bytes=0;}
        else s={};
    }
}
bool motion_source_storage_bind(void* base,unsigned bytes){
    if(!base || (reinterpret_cast<std::uintptr_t>(base)&(MotionStorageAlignment-1)) || bytes<MotionStorageBytes || bytes<sizeof(State))return false;
    if(state)return state==base;
    state=new(base) State{};return true;
}
bool motion_source_idle(){
    if(!state || state->scope_depth)return false;
    for(const auto& source:state->sources)if(source.used)return false;
    return true;
}
void motion_source_flush(){
    if(bootstrap_fault){bootstrap_fault=0;unresolved(Motion,"motion-source-storage-unbound");}
    if(!state)return;
    if(state->faults){unresolved(Motion,"motion-source-unbound-accepted");state->faults=0;}
    for(auto& s:state->sources)if(s.used){s.used=false;emitted_checked(Motion,s.asset);if(!s.owner)s={};}
}
void motion_source_retire(const void* owner){
    if(!state)return;
    if(!owner)return;
    motion_source_flush();
    for(auto& s:state->sources)if(s.owner==owner)s={};
}
void motion_source_retire_base(const void* base){
    if(!state)return;
    if(!base)return;
    const void* owners[SourceCount]{};unsigned n=0;
    // Base is either an exact direct source or the beginning of its archive.
    // Archive loaders retire by owner, this helper deliberately cannot guess
    // an enclosing allocation from an arbitrary interior address.
    for(const auto& s:state->sources)if(s.owner && s.base==base)owners[n++]=s.owner;
    for(unsigned i=0;i<n;++i)motion_source_retire(owners[i]);
}
void motion_source_note(const void* owner,const void* source,MotionSourceRole role){
    if(!state){bootstrap_fault=1;return;}
    auto* s=subject(owner,true);if(!s)return;
    // Skeletal/shape keys require the actual evaluated leaf pointer. A valid
    // source header alone cannot bless rebound or externally supplied keys.
    add(s->receipt,(role==MotionBind || role==MotionEvd)?lookup(source,role):0);
}
void motion_source_note_key(const void* owner,const void* header,const void* key,unsigned type,MotionSourceRole role){
    if(!state){bootstrap_fault=1;return;}
    auto* target=subject(owner,true);if(!target)return;
    unsigned found=0;
    for(const auto& s:state->sources)if(s.serial && s.asset.value &&
        (s.role==MotionFcv || s.role==MotionShape || s.role==MotionEvd) &&
        (contains(s.base,s.bytes,header,3) || (s.alias && header==s.alias && s.alias_bytes>=3)) && leaf(s.base,s.bytes,key,type)){
        if(found){add(target->receipt,0);return;}found=s.serial;
    }
    if(role!=MotionFcv && role!=MotionShape)found=0;
    add(target->receipt,found);
}
void motion_source_reset(const void* owner){
    if(!state)return;
    for(auto& s:state->subjects)if(s.owner==owner)s={};
    if(state->view==owner)state->view=nullptr;
}
MotionReceipt motion_source_snapshot(const void* model,const void* info){
    if(!state){MotionReceipt result{};result.fault=1;return result;}
    MotionReceipt result=selected(model);
    if(info && info!=model)merge(result,selected(info));
    if(state->view)merge(result,selected(state->view));
    // An absent camera source is unresolved. This does not establish zero use.
    else result.fault=1;
    result.model=model;result.info=info;result.view=state->view;
    if(auto* s=subject(model,false))result.model_generation=s->generation;
    if(auto* s=subject(info,false))result.info_generation=s->generation;
    if(auto* s=subject(state->view,false))result.view_generation=s->generation;
    return result;
}
namespace {
bool witness(const void* owner,unsigned generation){
    if(!owner)return generation==0;
    const auto* s=subject(owner,false);return s && generation && s->generation==generation;
}
bool receipt_current(const MotionReceipt& receipt,const void* model,const void* info){
    return model && receipt.model==model && receipt.info==info &&
        witness(model,receipt.model_generation) && witness(info,receipt.info_generation) &&
        witness(receipt.view,receipt.view_generation) && (!receipt.view || receipt.view==state->view);
}
MotionReceipt rejected(){MotionReceipt receipt{};receipt.fault=1;return receipt;}
}
void motion_source_view(const void* owner){if(state)state->view=owner;else bootstrap_fault=1;}
void motion_source_view_retire(const void* owner){if(!state)return;if(state->view==owner)state->view=nullptr;motion_source_reset(owner);}
MotionReceipt motion_source_current(){return state?state->context:rejected();}
MotionReceipt motion_source_exchange(const MotionReceipt& receipt){if(!state)return rejected();const auto old=state->context;state->context=receipt;return old;}
bool motion_source_replay_active(){return state && state->frozen_context;}
MotionReceipt motion_source_scope_enter(const void* model,const void* info){
    if(!state){bootstrap_fault=1;return rejected();}
    ++state->scope_depth;
    const auto old=state->context;
    if(state->frozen_context){if(!receipt_current(state->context,model,info))state->context=rejected();}
    else state->context=motion_source_snapshot(model,info);
    return old;
}
MotionReceipt motion_source_replay_enter(const MotionReceipt& receipt){
    if(!state){bootstrap_fault=1;return rejected();}
    ++state->scope_depth;
    const auto old=state->context;state->frozen_context=true;
    state->context=receipt_current(receipt,receipt.model,receipt.info)?receipt:rejected();return old;
}
void motion_source_restore(const MotionReceipt& receipt,bool frozen){if(!state)return;if(state->scope_depth)--state->scope_depth;else state->faults=1;state->context=receipt;state->frozen_context=frozen;}
void motion_source_prepare(){if(!state){bootstrap_fault=1;return;}state->pending=state->context;state->pending_accounted=false;}
void motion_source_accept(const MotionReceipt& receipt,unsigned records){
    if(!state){if(records)bootstrap_fault=1;return;}
    if(!records)return;
    if(!receipt_current(receipt,receipt.model,receipt.info)){state->faults=1;return;}
    if(receipt.fault || receipt.count>MotionSourceLimit || !receipt.count)state->faults=1;
    if(receipt.count>MotionSourceLimit)return;
    for(unsigned i=0;i<receipt.count;++i){
        Source* found=nullptr;
        for(auto& s:state->sources)if(s.serial==receipt.serial[i] && s.serial){found=&s;break;}
        if(found && checked_current(found->asset))found->used=true;else state->faults=1;
    }
}
void motion_source_accept_pending(unsigned records){
    if(!state){if(records)bootstrap_fault=1;return;}
    if(!records)return;
    if(state->pending_accounted){state->pending_accounted=false;state->faults=1;return;}
    motion_source_accept(state->pending,records);
}
void motion_source_accept_current(unsigned records){motion_source_accept(motion_source_current(),records);}
void motion_source_pending_accounted(){if(!state)return;state->pending_accounted=true;state->pending={};}
#if defined(RE4DC_GC_ASSET_TEST) && RE4DC_GC_ASSET_TEST
void motion_source_test_serial(unsigned serial){if(state)state->next_serial=serial;}
unsigned motion_source_test_storage_bytes(){return sizeof(State);}
#endif
}
#endif
