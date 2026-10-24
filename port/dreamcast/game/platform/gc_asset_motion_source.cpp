#include "include/gc_asset_motion_source.h"
#if RE4DC_GC_ASSET_MOTION_SOURCE
#include <cstdint>
#include <cstring>
namespace re4dc_gcasset {
namespace {
constexpr unsigned SourceCount=128,SubjectCount=64,MaxBytes=40U*1024*1024;
struct Source {const void* owner=nullptr;const void* base=nullptr;unsigned bytes=0,serial=0,role=0;CheckedAsset asset{};bool used=false;};
struct Subject {const void* owner=nullptr;MotionReceipt receipt{};};
Source sources[SourceCount];Subject subjects[SubjectCount];
unsigned next_serial=0,faults=0;const void* view=nullptr;
MotionReceipt context{},pending{};bool pending_accounted=false;
static_assert(sizeof(void*)!=4 || sizeof(Source)<=28,"bounded immutable source metadata");
static_assert(sizeof(MotionReceipt)==40,"fixed eight-contributor receipt");
bool contains(const void* base,unsigned bytes,const void* p,unsigned n){
    const auto a=reinterpret_cast<std::uintptr_t>(base),b=reinterpret_cast<std::uintptr_t>(p);
    return base && p && bytes && n && b>=a && b-a<=bytes && n<=bytes-(b-a);
}
bool bounds(const void* p,unsigned bytes){return p && bytes && bytes<=MaxBytes && bytes<=~std::uintptr_t(0)-reinterpret_cast<std::uintptr_t>(p);}
bool overlap(const void* a,unsigned an,const void* b,unsigned bn){
    const auto x=reinterpret_cast<std::uintptr_t>(a),y=reinterpret_cast<std::uintptr_t>(b);
    return x<=y?y-x<an:x-y<bn;
}
void add(MotionReceipt& out,unsigned serial){
    if(!serial){out.fault=1;return;}
    for(unsigned i=0;i<out.count;++i)if(out.serial[i]==serial)return;
    if(out.count==MotionSourceLimit){out.fault=1;return;}
    out.serial[out.count++]=serial;
}
void merge(MotionReceipt& out,const MotionReceipt& in){
    if(in.count>MotionSourceLimit){out.fault=1;return;}
    out.fault|=in.fault;
    for(unsigned i=0;i<in.count;++i)add(out,in.serial[i]);
}
Subject* subject(const void* owner,bool create){
    if(!owner)return nullptr;
    Subject* free=nullptr;
    for(auto& s:subjects){if(s.owner==owner)return &s;if(!s.owner && !free)free=&s;}
    if(create && free){free->owner=owner;return free;}
    return nullptr;
}
unsigned lookup(const void* p,MotionSourceRole role){
    unsigned serial=0;
    for(const auto& s:sources)if(s.serial && contains(s.base,s.bytes,p,1) && (s.role==unsigned(role) || s.role==MotionEvd)){
        if(serial)return 0;
        serial=s.serial;
    }
    return serial;
}
CheckedAsset capture(const void* base,unsigned bytes){
    const Digest digest=fingerprint(base,bytes);char id[41];constexpr char hex[]="0123456789abcdef";
    for(unsigned i=0;i<20;++i){id[2*i]=hex[digest.bytes[i]>>4];id[2*i+1]=hex[digest.bytes[i]&15];}id[40]=0;
    return bind_checked("motion",id,digest);
}
unsigned word(const unsigned char* p){unsigned v;std::memcpy(&v,p,4);return v;}
MotionReceipt selected(const void* owner){
    auto* s=subject(owner,false);if(s)return s->receipt;
    MotionReceipt result{};result.fault=1;return result;
}
}
bool motion_source_adopt(const void* owner,const void* base,unsigned bytes,MotionSourceRole role){
    if(!owner || !bounds(base,bytes) || role<MotionFcv || role>MotionBind){unresolved(Motion,"motion-source-bounds");return false;}
    Source* free=nullptr;
    for(auto& s:sources){
        if(s.serial && s.owner==owner && s.base==base){
            if(s.bytes==bytes && s.role==unsigned(role))return true;
            unresolved(Motion,"motion-source-replaced-without-retire");return false;
        }
        if(s.serial && overlap(base,bytes,s.base,s.bytes)){unresolved(Motion,"motion-source-overlap");return false;}
        if(!s.owner && !free)free=&s;
    }
    if(!free || next_serial>=0xfffffffeU){unresolved(Motion,"motion-source-capacity-or-serial");return false;}
    const CheckedAsset asset=capture(base,bytes);
    if(!asset.value){unresolved(Motion,"motion-source-catalog-bind");return false;}
    *free={owner,base,bytes,++next_serial,unsigned(role),asset,false};return true;
}
bool motion_source_archive(const void* owner,const void* base,unsigned bytes){
    if(!owner || !bounds(base,bytes) || bytes<16){unresolved(Motion,"motion-archive-bounds");return false;}
    const auto* p=static_cast<const unsigned char*>(base);const unsigned count=word(p),rel=word(p+4);
    if(count>4096 || count>(bytes-16)/8 || (rel && rel>bytes)){unresolved(Motion,"motion-archive-directory");return false;}
    const unsigned directory=16+8*count;bool external=false;
    for(unsigned i=0;i<count;++i){
        const unsigned at=word(p+16+4*i);if(at<directory || at>=bytes){unresolved(Motion,"motion-archive-span");return false;}
        const auto* tag=p+16+4*count+4*i;if(!std::memcmp(tag,"MTC",3))external=true;
        // Zero-tag alias slots may point at their next real member. Reject all
        // nonempty aliases so no captured span has two interpretations.
        for(unsigned j=0;j<i;++j)if(word(p+16+4*j)==at && word(tag) && word(p+16+4*count+4*j)){
            unresolved(Motion,"motion-archive-alias");return false;
        }
    }
    bool good=true;
    for(unsigned i=0;i<count;++i){
        const auto* tag=p+16+4*count+4*i;MotionSourceRole role;
        if(!std::memcmp(tag,"FCV",3)){if(external){good=false;continue;}role=MotionFcv;}
        else if(!std::memcmp(tag,"EVD",3))role=MotionEvd;
        else if(!std::memcmp(tag,"BIN",3))role=MotionBind;
        else continue;
        const unsigned at=word(p+16+4*i);unsigned end=rel>at?rel:bytes;
        for(unsigned j=0;j<count;++j){const unsigned next=word(p+16+4*j);if(next>at && next<end)end=next;}
        if(end<=at || !motion_source_adopt(owner,p+at,end-at,role))good=false;
    }
    if(external)unresolved(Motion,"motion-external-keys-unbound");
    return good;
}
void motion_source_flush(){
    if(faults){unresolved(Motion,"motion-source-unbound-accepted");faults=0;}
    for(auto& s:sources)if(s.used){s.used=false;emitted_checked(Motion,s.asset);}
}
void motion_source_retire(const void* owner){
    if(!owner)return;
    motion_source_flush();
    for(auto& s:sources)if(s.owner==owner)s={};
}
void motion_source_retire_base(const void* base){
    if(!base)return;
    const void* owners[SourceCount]{};unsigned n=0;
    // Base is either an exact direct source or the beginning of its archive.
    // Archive loaders retire by owner, this helper deliberately cannot guess
    // an enclosing allocation from an arbitrary interior address.
    for(const auto& s:sources)if(s.owner && s.base==base)owners[n++]=s.owner;
    for(unsigned i=0;i<n;++i)motion_source_retire(owners[i]);
}
void motion_source_note(const void* owner,const void* source,MotionSourceRole role){
    auto* s=subject(owner,true);if(!s)return;
    add(s->receipt,lookup(source,role));
}
void motion_source_reset(const void* owner){
    for(auto& s:subjects)if(s.owner==owner)s={};
    if(view==owner)view=nullptr;
}
MotionReceipt motion_source_snapshot(const void* model,const void* info){
    MotionReceipt result=selected(model);
    if(info && info!=model)merge(result,selected(info));
    if(view)merge(result,selected(view));
    // An absent camera source is unresolved. This does not establish zero use.
    else result.fault=1;
    return result;
}
void motion_source_view(const void* owner){view=owner;}
void motion_source_view_retire(const void* owner){if(view==owner)view=nullptr;motion_source_reset(owner);}
MotionReceipt motion_source_current(){return context;}
MotionReceipt motion_source_exchange(const MotionReceipt& receipt){const auto old=context;context=receipt;return old;}
void motion_source_prepare(){pending=context;pending_accounted=false;}
void motion_source_accept(const MotionReceipt& receipt,unsigned records){
    if(!records)return;
    if(receipt.fault || receipt.count>MotionSourceLimit || !receipt.count)faults=1;
    if(receipt.count>MotionSourceLimit)return;
    for(unsigned i=0;i<receipt.count;++i){
        Source* found=nullptr;
        for(auto& s:sources)if(s.serial==receipt.serial[i] && s.serial){found=&s;break;}
        if(found && checked_current(found->asset))found->used=true;else faults=1;
    }
}
void motion_source_accept_pending(unsigned records){
    if(!records)return;
    if(pending_accounted){pending_accounted=false;faults=1;return;}
    motion_source_accept(pending,records);
}
void motion_source_accept_current(unsigned records){motion_source_accept(context,records);}
void motion_source_pending_accounted(){pending_accounted=true;pending={};}
#if defined(RE4DC_GC_ASSET_TEST) && RE4DC_GC_ASSET_TEST
void motion_source_test_serial(unsigned serial){next_serial=serial;}
#endif
}
#endif
