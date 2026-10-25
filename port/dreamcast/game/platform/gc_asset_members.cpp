#include "include/gc_asset_members.h"
#if RE4DC_GC_ASSET_GATE
#include <cstdint>
#include <cstring>
#include <cstdlib>
extern "C" void re4dc_log(const char*,...);
namespace re4dc_gcasset {
SourceUse source_use;
ReplayUse replay_use;
namespace {
constexpr unsigned ArchiveCount=16, MemberCount=128;
struct Archive {
    const void* owner;const unsigned char* base;unsigned bytes,generation;bool transient;OwnerFamily family;
} archives[ArchiveCount];
struct Member {
    const unsigned char* base;const char* name;CheckedAsset asset;
    unsigned bytes,owner,generation,serial,arc,uses;
} members[MemberCount];
unsigned generation=1,serial=1;
unsigned use_faults;
static_assert(sizeof(void*)!=4 || (sizeof(Archive)<=24 && sizeof(Member)<=36),"bounded member metadata budget");
struct Span { const unsigned char* base=nullptr;const char* name=nullptr;unsigned bytes=0,arc=0; };
bool contains(const void* base,unsigned bytes,const void* pointer,unsigned count) {
    const auto a=reinterpret_cast<std::uintptr_t>(base),b=reinterpret_cast<std::uintptr_t>(pointer);
    return base && pointer && b>=a && b-a<=bytes && count<=bytes-(b-a);
}
unsigned word(const unsigned char* base,unsigned offset) {
    unsigned value;std::memcpy(&value,base+offset,4);return value;
}
bool table(const Archive& owner,unsigned& count) {
    if(!owner.owner || owner.bytes<16)return false;
    count=word(owner.base,0);
    return count<=4096 && 16+count*8<=owner.bytes;
}
// Same span and empty-slot alias rules as actor_lifetime.inc::entry. This
// parser supplies bounds only, never that actor registry's origin verdict.
bool entry(const Archive& owner,unsigned index,Span& span) {
    unsigned count;if(!table(owner,count) || index>=count)return false;
    const unsigned directory=16+count*8,tags=16+count*4,at=word(owner.base,16+index*4);
    if(at<directory || at>=owner.bytes)return false;
    unsigned empty_first=index;
    while(empty_first && word(owner.base,16+(empty_first-1)*4)==at && !word(owner.base,tags+(empty_first-1)*4))--empty_first;
    unsigned end=owner.bytes,rel=word(owner.base,4);
    if(rel>at && rel<end)end=rel;
    for(unsigned i=0;i<count;++i)if(i!=index) {
        const unsigned offset=word(owner.base,16+i*4);
        if(offset==at && (i<empty_first || i>=index))return false;
        if(offset>at && offset<end)end=offset;
    }
    span={owner.base+at,nullptr,end-at,index+4};return true;
}
bool valid_name(const char* name) {
    unsigned i=0;for(;i<32 && name[i];++i) {
        const unsigned char c=name[i];
        if(!((c>='a' && c<='z') || (c>='A' && c<='Z') || (c>='0' && c<='9') || c=='.' || c=='_' || c=='-'))return false;
    }
    return i>0 && i<32;
}
bool bin_name(const char* name) {
    unsigned i=0;while(i<32 && name[i])++i;
    return i>4 && i<32 && name[i-4]=='.' && (name[i-3]=='b' || name[i-3]=='B') &&
        (name[i-2]=='i' || name[i-2]=='I') && (name[i-1]=='n' || name[i-1]=='N');
}
bool named(const Span& etm,const void* data,Span& result) {
    if(etm.bytes<32)return false;
    const unsigned count=word(etm.base,0);if(count>4096)return false;
    unsigned cursor=32;bool found=false;
    for(unsigned i=0;i<count;++i) {
        if(cursor>etm.bytes || etm.bytes-cursor<64)return false;
        const unsigned bytes=word(etm.base,cursor);
        const char* name=reinterpret_cast<const char*>(etm.base+cursor+32);
        if(bytes<64 || bytes>etm.bytes-cursor || !valid_name(name))return false;
        // Reject duplicate names, including case-only aliases, before trusting
        // any candidate. Member records stay bounded by their enclosing ETM.
        unsigned earlier=32;
        for(unsigned j=0;j<i;++j) {
            const char* old=reinterpret_cast<const char*>(etm.base+earlier+32);bool same=true;
            for(unsigned k=0;k<32;++k) {
                const unsigned char x=name[k],y=old[k];
                const unsigned a=x>='A'&&x<='Z'?x+32:x,b=y>='A'&&y<='Z'?y+32:y;
                if(a!=b){same=false;break;}if(!x)break;
            }
            if(same)return false;
            earlier+=word(etm.base,earlier);
        }
        const unsigned char* base=etm.base+cursor+64;
        if(bin_name(name) && contains(base,bytes-64,data,1)) { if(found)return false;result={base,name,bytes-64,0};found=true; }
        cursor+=bytes;
    }
    return found;
}
bool find(const Archive& owner,const void* data,Span& result) {
    unsigned count;if(!table(owner,count) || !contains(owner.base,owner.bytes,data,1))return false;
    const unsigned tags=16+count*4;bool found=false;
    for(unsigned i=0;i<count;++i) {
        const auto* tag=owner.base+tags+4*i;
        if(std::memcmp(tag,"BIN",3) && std::memcmp(tag,"ETM",3))continue;
        Span current;if(!entry(owner,i,current))return false;
        if(!contains(current.base,current.bytes,data,1))continue;
        if(!std::memcmp(tag,"ETM",3)) { Span child;if(!named(current,data,child))return false;current=child; }
        if(found)return false;
        result=current;found=true;
    }
    return found;
}
bool current(const Member& member) {
    return member.base && member.owner<ArchiveCount && archives[member.owner].owner &&
        archives[member.owner].generation==member.generation &&
        contains(archives[member.owner].base,archives[member.owner].bytes,member.base,member.bytes);
}
// gc-catalog24b (coordinator 10-24, option iii): every BIN member (direct or an
// ETM .bin) is hashed at adopt, before relocation/fixup, from the archive bytes as
// loaded; member_capture binds that digest. One KOS block per archive, 36 B per
// model member, freed at revoke. Same span rules as find()/named().
struct Pre { unsigned offset,bytes;Digest digest; };
Pre* pre[ArchiveCount];unsigned pre_count[ArchiveCount];
void pre_free(unsigned owner){std::free(pre[owner]);pre[owner]=nullptr;pre_count[owner]=0;}
template<class F> void each_model(const Archive& owner,F&& f){
    unsigned count;if(!table(owner,count))return;
    const unsigned tags=16+count*4;
    for(unsigned i=0;i<count;++i){
        const auto* tag=owner.base+tags+4*i;
        if(std::memcmp(tag,"BIN",3) && std::memcmp(tag,"ETM",3))continue;
        Span current;if(!entry(owner,i,current))continue;
        if(!std::memcmp(tag,"BIN",3)){f(current);continue;}
        if(current.bytes<32)continue;
        const unsigned n=word(current.base,0);if(n>4096)continue;
        unsigned cursor=32;
        for(unsigned k=0;k<n;++k){
            if(cursor>current.bytes || current.bytes-cursor<64)break;
            const unsigned bytes=word(current.base,cursor);
            const char* name=reinterpret_cast<const char*>(current.base+cursor+32);
            if(bytes<64 || bytes>current.bytes-cursor || !valid_name(name))break;
            if(bin_name(name))f(Span{current.base+cursor+64,name,bytes-64,0});
            cursor+=bytes;
        }
    }
}
void pre_hash(unsigned owner){
    pre_free(owner);
    const Archive& a=archives[owner];unsigned n=0;
    each_model(a,[&](const Span&){++n;});
    if(!n)return;
    if(!(pre[owner]=static_cast<Pre*>(std::malloc(n*sizeof(Pre))))){unresolved(SourceGeometry,"member-prehash-alloc");return;}
    each_model(a,[&](const Span& s){
        if(pre_count[owner]<n)pre[owner][pre_count[owner]++]={unsigned(s.base-a.base),s.bytes,fingerprint(s.base,s.bytes)};
    });
}
bool pre_digest(unsigned owner,const Span& span,Digest& out){
    const unsigned offset=unsigned(span.base-archives[owner].base);
    for(unsigned i=0;i<pre_count[owner];++i)if(pre[owner][i].offset==offset && pre[owner][i].bytes==span.bytes){out=pre[owner][i].digest;return true;}
    return false;
}
void revoke(unsigned owner) {
    member_flush();
    for(auto& member:members)if(member.base && member.owner==owner)member={};
    archives[owner]={};pre_free(owner);
}
}
bool member_adopt(const void* owner,void* archive,unsigned bytes,bool transient,OwnerFamily family) {
    if(!owner || !archive || bytes<16 || generation==0xffffffffU) { unresolved(SourceGeometry,"member-adopt");return false; }
    unsigned free=ArchiveCount;
    for(unsigned i=0;i<ArchiveCount;++i) {
        if(archives[i].owner==owner) {
            if(archives[i].base==archive && archives[i].bytes==bytes) {
                if(archives[i].family==family)return true;
                revoke(i);unresolved(SourceGeometry,"member-owner-family");return false;
            }
            revoke(i);free=i;break;
        }
        if(!archives[i].owner && free==ArchiveCount)free=i;
    }
    bool conflict=false;
    for(unsigned i=0;i<ArchiveCount;++i)if(archives[i].owner) {
        const auto a=reinterpret_cast<std::uintptr_t>(archive),b=reinterpret_cast<std::uintptr_t>(archives[i].base);
        if(a<=b ? b-a<bytes : a-b<archives[i].bytes) { revoke(i);conflict=true; }
    }
    if(conflict) { unresolved(SourceGeometry,"member-owner-overlap");return false; }
    if(free==ArchiveCount) { unresolved(SourceGeometry,"member-owner-capacity");return false; }
    Archive candidate{owner,static_cast<unsigned char*>(archive),bytes,++generation,transient,family};unsigned count;
    if(!table(candidate,count)) { unresolved(SourceGeometry,"member-directory");return false; }
    archives[free]=candidate;pre_hash(free);return true;
}
void member_retire(const void* owner) { for(unsigned i=0;i<ArchiveCount;++i)if(archives[i].owner==owner)revoke(i); }
void member_retire_archive(const void* base) { for(unsigned i=0;i<ArchiveCount;++i)if(archives[i].owner && archives[i].base==base)revoke(i); }
void member_retire_transient() { for(unsigned i=0;i<ArchiveCount;++i)if(archives[i].owner && archives[i].transient)revoke(i); }
bool member_capture(const void* data) {
    for(const auto& member:members)if(current(member) && contains(member.base,member.bytes,data,1))return true;
    unsigned owner=ArchiveCount;Span span;
    for(unsigned i=0;i<ArchiveCount;++i)if(archives[i].owner && contains(archives[i].base,archives[i].bytes,data,1)) {
        if(owner!=ArchiveCount || !find(archives[i],data,span)) { unresolved(SourceGeometry,"member-span");return false; }
        owner=i;
    }
    if(owner==ArchiveCount) { unresolved(SourceGeometry,"member-unbound");return false; }
    if(span.bytes<64 || !contains(span.base,span.bytes,data,64) || serial>=0xfffffffeU) { unresolved(SourceGeometry,"member-model-bounds");return false; }
    for(auto& member:members)if(!member.base) {
        Digest digest;const bool adopted=pre_digest(owner,span,digest);
        if(!adopted)digest=fingerprint(span.base,span.bytes);   // adopt-time bytes first
#if defined(RE4DC_GC_ASSET_HARVEST) && RE4DC_GC_ASSET_HARVEST
        re4dc_log("GC-ASSET-NOTE member adopted=%u archive_bytes=%u offset=%u bytes=%u\n",adopted?1U:0U,
            archives[owner].bytes,unsigned(span.base-archives[owner].base),span.bytes);
#endif
        constexpr char hex[]="0123456789abcdef";char id[41];
        for(unsigned i=0;i<20;++i){id[2*i]=hex[digest.bytes[i]>>4];id[2*i+1]=hex[digest.bytes[i]&15];}id[40]=0;
        const CheckedAsset asset=bind_checked("model",id,digest);
        if(!asset.value){unresolved(SourceGeometry,"member-catalog-bind");return false;}
        member={span.base,span.name,asset,span.bytes,owner,archives[owner].generation,++serial,span.arc,0};
        return true;
    }
    unresolved(SourceGeometry,"member-capacity");return false;
}
bool member_lookup(const void* data,ModelMember* out) {
    if(!out)return false;
    for(const auto& member:members)if(current(member) && contains(member.base,member.bytes,data,64)) {
        *out={member.asset,member.serial,member.arc,unsigned(static_cast<const unsigned char*>(data)-member.base),{}};
        out->family=archives[member.owner].family;
        if(member.name)for(unsigned i=0;i<31 && member.name[i];++i) {
            const unsigned char c=member.name[i];out->name[i]=c>='A'&&c<='Z'?c+32:c;
        }
        return true;
    }
    return false;
}
bool member_contains(unsigned serial,const void* data,unsigned bytes) {
    if(!serial || !bytes)return false;
    for(const auto& member:members)if(current(member) && member.serial==serial)
        return contains(member.base,member.bytes,data,bytes);
    return false;
}
void member_accept(unsigned serial,unsigned mask) {
    const unsigned allowed=(1U<<SourceGeometry)|(1U<<Weapon);
    if(!serial || !mask || (mask&~allowed)) { use_faults|=mask&allowed?mask&allowed:1U<<SourceGeometry;return; }
    for(auto& member:members)if(current(member) && member.serial==serial) {member.uses|=mask;return;}
    use_faults|=mask;
}
void member_flush() {
    const unsigned faults=use_faults;use_faults=0;
    for(unsigned i=0;i<ConsumerCount;++i)if(faults&(1U<<i))unresolved(Consumer(i),"unbound-accepted-model");
    for(auto& member:members)if(member.uses) {
        const unsigned mask=member.uses;member.uses=0;
        if(!current(member)) {unresolved(SourceGeometry,"retired-accepted-model");continue;}
        for(unsigned i=0;i<ConsumerCount;++i)if(mask&(1U<<i))emitted_checked(Consumer(i),member.asset);
    }
}
#if defined(RE4DC_GC_ASSET_TEST) && RE4DC_GC_ASSET_TEST
void member_test_serial(unsigned value){serial=value;}
#endif
}
extern "C" void re4dc_gcasset_capture_model(const void* data) { re4dc_gcasset::member_capture(data); }
extern "C" void re4dc_gcasset_retire_archive(const void* base) { re4dc_gcasset::member_retire_archive(base); }
#endif
