#include "include/gc_asset_members.h"
#if RE4DC_GC_ASSET_GATE
#include <cstdint>
#include <cstring>
#include <cstdlib>
#include <cstdio>
#include <atomic>
extern "C" void re4dc_log(const char*,...);
namespace re4dc_gcasset {
SourceUse source_use;
ReplayUse replay_use;
namespace {
constexpr unsigned ArchiveCount=16, MemberCount=256;   // gc-catalog24b: SMD/SHD/ITM/EFF members (was 128)
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
// gc-catalog24b: model offset-table containers. SMD (include/scroll.h cSmd,
// getBinPtr), SHD (shadow.h ShdHeader, ofsTbl relative to itself) and ITM
// (item_model.cpp ItemModelPack, bin table {num, ofs[]}). A BIN starts at
// table + ofs[i] and ends at the next larger table offset (else the limit:
// the next table or the entry end). Unused slots (outside the table's data)
// are skipped. build_catalog.py table_bins is the same rule.
template<class F> void table_bins(const Span& c,unsigned tbl,unsigned idx0,unsigned n,unsigned limit,F&& f){
    if(tbl>c.bytes || n>4096 || idx0+4*n>c.bytes-tbl || limit>c.bytes-tbl)return;
    const unsigned lo=idx0+4*n;
    for(unsigned i=0;i<n;++i){
        const unsigned o=word(c.base,tbl+idx0+4*i);
        if(o<lo || o>=limit)continue;
        bool dup=false;for(unsigned j=0;j<i && !dup;++j)dup=word(c.base,tbl+idx0+4*j)==o;
        if(dup)continue;
        unsigned end=limit;
        for(unsigned j=0;j<n;++j){const unsigned q=word(c.base,tbl+idx0+4*j);if(q>o && q<end)end=q;}
        if(end-o>=64)f(Span{c.base+tbl+o,nullptr,end-o,0});
    }
}
template<class F> void container_bins(const unsigned char* tag,const Span& c,F&& f){
    if(c.bytes<16)return;
    if(!std::memcmp(tag,"SMD",3) || !std::memcmp(tag,"SHD",3)){
        const unsigned t=word(c.base,4);
        if(t<16 || t>c.bytes-4 || (t&3))return;
        const unsigned first=word(c.base,t);
        if(first<4 || (first&3))return;
        unsigned limit=c.bytes-t;
        if(!std::memcmp(tag,"SMD",3)){const unsigned tt=word(c.base,8);if(tt>t && tt<=c.bytes)limit=tt-t;}
        table_bins(c,t,0,first/4,limit,f);
    }else if(!std::memcmp(tag,"EFF",3)){
        // eff_sys.cpp EffData v0xB: ofsEfm (0x2C) = {num, ofs[]} of EffEfmEnt
        // {x0, ofsModel, ofsTpl, ofsMot, ofsX} (entry-relative). The model ends at
        // the entry's next non-zero section offset, else the next entry / the end.
        if(c.bytes<0x30 || word(c.base,0)!=0xB)return;
        const unsigned t=word(c.base,0x2c);
        if(t<0x30 || t>c.bytes-4 || (t&3))return;
        const unsigned n=word(c.base,t);
        if(n>4096 || 4+4*n>c.bytes-t)return;
        for(unsigned i=0;i<n;++i){
            const unsigned e=t+word(c.base,t+4+4*i);
            if(e<t || e>c.bytes-20)continue;
            const unsigned m=e+word(c.base,e+4);
            if(m<e+20 || m>=c.bytes)continue;
            unsigned end=c.bytes;
            for(unsigned k=2;k<5;++k){const unsigned o=word(c.base,e+4*k);if(o && e+o>m && e+o<end)end=e+o;}
            for(unsigned j=0;j<n;++j){const unsigned q=t+word(c.base,t+4+4*j);if(q>m && q<end)end=q;}
            if(end-m>=64)f(Span{c.base+m,nullptr,end-m,0});
        }
    }else if(!std::memcmp(tag,"ITM",3)){
        const unsigned ob=word(c.base,8),ot=word(c.base,12);
        if(ob<16 || ob>c.bytes-4 || (ob&3))return;
        table_bins(c,ob,4,word(c.base,ob),ot>ob && ot<=c.bytes?ot-ob:c.bytes-ob,f);
    }
}
bool container_tag(const unsigned char* tag){return !std::memcmp(tag,"SMD",3) || !std::memcmp(tag,"SHD",3) || !std::memcmp(tag,"ITM",3) || !std::memcmp(tag,"EFF",3);}
bool find(const Archive& owner,const void* data,Span& result) {
    unsigned count;if(!table(owner,count) || !contains(owner.base,owner.bytes,data,1))return false;
    const unsigned tags=16+count*4;bool found=false;
    for(unsigned i=0;i<count;++i) {
        const auto* tag=owner.base+tags+4*i;
        if(std::memcmp(tag,"BIN",3) && std::memcmp(tag,"ETM",3) && !container_tag(tag))continue;
        Span current;if(!entry(owner,i,current))return false;
        if(!contains(current.base,current.bytes,data,1))continue;
        if(container_tag(tag)) {
            bool hit=false;Span child;
            container_bins(tag,current,[&](const Span& s){if(!hit && contains(s.base,s.bytes,data,1)){child=s;hit=true;}});
            if(!hit)return false;
            current=child;
        }
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
        // Container members (SMD/SHD/ITM/EFF) are not pre-hashed: their BINs are
        // captured unmutated at calcModelAddr (member_capture hashes them then),
        // and their pre tables would cost KOS heap (r101 core EFF: OOM at 10-25).
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
void member_move(const void* owner,void* base) {
    for(unsigned i=0;i<ArchiveCount;++i)if(archives[i].owner==owner) {
        member_flush();
        for(auto& member:members)if(member.base && member.owner==i)member={};
        archives[i].base=static_cast<unsigned char*>(base);archives[i].generation=++generation;return;
    }
}
void member_retire(const void* owner) { for(unsigned i=0;i<ArchiveCount;++i)if(archives[i].owner==owner)revoke(i); }
void member_retire_archive(const void* base) { for(unsigned i=0;i<ArchiveCount;++i)if(archives[i].owner && archives[i].base==base)revoke(i); }
void member_retire_transient() { for(unsigned i=0;i<ArchiveCount;++i)if(archives[i].owner && archives[i].transient)revoke(i); }
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
bool member_capture(const void* data) {
    for(const auto& member:members)if(current(member) && contains(member.base,member.bytes,data,1))return true;
    unsigned owner=ArchiveCount;Span span;
    for(unsigned i=0;i<ArchiveCount;++i)if(archives[i].owner && contains(archives[i].base,archives[i].bytes,data,1)) {
        if(owner!=ArchiveCount || !find(archives[i],data,span)) { 
#if defined(RE4DC_GC_ASSET_PROF) && RE4DC_GC_ASSET_PROF
            {unsigned cnt=0;char tg[5]="----";unsigned eo=0,eb=0;if(table(archives[i],cnt))for(unsigned k=0;k<cnt;++k){Span sp;if(entry(archives[i],k,sp)&&contains(sp.base,sp.bytes,data,1)){std::memcpy(tg,archives[i].base+16+cnt*4+4*k,4);eo=unsigned(sp.base-archives[i].base);eb=sp.bytes;break;}}
             for(unsigned q=0;q<4;++q)if(tg[q]<32||tg[q]>126)tg[q]='.';
             GCA_PROBE("member-span",data,__builtin_return_address(0),"arch=%p bytes=%u tag=%s entry_off=%u entry_bytes=%u data_off=%u owner_family=%u\n",archives[i].base,archives[i].bytes,tg,eo,eb,unsigned(static_cast<const unsigned char*>(data)-archives[i].base),unsigned(archives[i].family));}
#endif
unresolved(SourceGeometry,"member-span");return false; }
        owner=i;
    }
    if(owner==ArchiveCount) { 
#if defined(RE4DC_GC_ASSET_PROF) && RE4DC_GC_ASSET_PROF
            {static unsigned dumps;if(dumps<2){++dumps;for(unsigned k=0;k<ArchiveCount;++k)if(archives[k].owner)re4dc_log("GC-ASSET-PROBE archive k=%u base=%p bytes=%u family=%u transient=%u\n",k,archives[k].base,archives[k].bytes,unsigned(archives[k].family),archives[k].transient?1u:0u);}}
            GCA_PROBE("member-unbound",data,__builtin_return_address(0),"head=%08x %08x\n",static_cast<const unsigned*>(data)[0],static_cast<const unsigned*>(data)[1]);
#endif
unresolved(SourceGeometry,"member-unbound");return false; }
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
// gc-catalog24b (bit 9, Motion): one identity per FCV/SEQ clip key, the
// "<crc32>-<fnv1a>" of the clip bytes as the disc holds them (the dc/mot key
// naming). An MTC-keyed proxy FCV takes its MTC record's key; an inline FCV/SEQ
// hashes its archive span, with the FCV's in-place relocated key table read
// back as offsets. digest = sha256 of the 8-byte key {crc,fnv} (little endian).
// Uses are latched (bounded) on the evaluating thread, emitted at the frame flush.
namespace {
// Per adopted archive, one bit per directory entry: this clip was handled in the
// current visit (bound + latched, or its fault counted). A clip is hashed and bound
// once per visit, never per evaluated frame. 16 x 68 B; pointers outside any
// adopted archive or not at an FCV/SEQ entry go to a 16-slot fault ring.
constexpr unsigned MotionPendingCount=48,MotionDoneEntries=512,MotionFaultRing=16;
struct MotionDone{unsigned generation;unsigned char bits[MotionDoneEntries/8];};
MotionDone motion_done[ArchiveCount];
const void* motion_fault_ring[MotionFaultRing];unsigned motion_fault_next;
unsigned motion_pending[MotionPendingCount],motion_pending_count;
enum MotionFault{MotionUnbound,MotionNested,MotionBind,MotionCapacity,MotionBusy,MotionFaults};
unsigned motion_faults[MotionFaults];
std::atomic_flag motion_lock=ATOMIC_FLAG_INIT;
struct MotionKey{unsigned crc=0xffffffffU,fnv=2166136261U;
    void add(unsigned char b){fnv=(fnv^b)*16777619U;crc^=b;for(int k=0;k<8;++k)crc=crc&1?(crc>>1)^0xEDB88320U:crc>>1;}};
unsigned fcv_prefix(const unsigned char* p){const unsigned n=p[2];return ((3+3*n+3)&~3U)+4+4*n;}
bool mtc_key(const Archive& a,unsigned count,unsigned offset,unsigned& crc,unsigned& fnv){
    const unsigned tags=16+count*4;
    for(unsigned i=0;i<count;++i)if(!std::memcmp(a.base+tags+4*i,"MTC",3)){
        Span m;if(!entry(a,i,m) || m.bytes<32 || std::memcmp(m.base,"R4MOTBL",7))return false;
        const unsigned rows=word(m.base,12),stride=word(m.base,16);
        if(stride<20 || rows>(m.bytes-32)/stride)return false;
        for(unsigned r=0;r<rows;++r){const unsigned char* e=m.base+32+r*stride;
            if(word(e,0)==offset){crc=word(e,8);fnv=word(e,12);return true;}}
        return false;
    }
    return false;
}
void motion_fault(MotionFault f){if(motion_faults[f]!=~0U)++motion_faults[f];}
bool motion_pointer_fault(const void* data,MotionFault f){   // counted once per pointer per visit
    for(const void* q:motion_fault_ring)if(q==data)return true;
    motion_fault_ring[motion_fault_next++%MotionFaultRing]=data;motion_fault(f);return true;
}
}
void motion_use(const void* pointer) {
    const auto* data=static_cast<const unsigned char*>(pointer);
    if(!data)return;
    if(motion_lock.test_and_set(std::memory_order_acquire)){motion_fault(MotionBusy);return;}
    struct Release{~Release(){motion_lock.clear(std::memory_order_release);}} release;
    unsigned owner=ArchiveCount;
    for(unsigned i=0;i<ArchiveCount;++i)if(archives[i].owner && contains(archives[i].base,archives[i].bytes,data,1)){owner=i;break;}
    if(owner==ArchiveCount){motion_pointer_fault(data,MotionUnbound);return;}
    const Archive& a=archives[owner];unsigned count;
    if(!table(a,count)){motion_pointer_fault(data,MotionUnbound);return;}
    const unsigned offset=unsigned(data-a.base),tags=16+count*4;unsigned index=count;bool fcv=false;
    for(unsigned i=0;i<count;++i)if(word(a.base,16+4*i)==offset){
        const auto* tag=a.base+tags+4*i;
        if(!std::memcmp(tag,"FCV",3) || !std::memcmp(tag,"SEQ",3)){index=i;fcv=!std::memcmp(tag,"FCV",3);break;}
    }
    if(index==count){motion_pointer_fault(data,MotionNested);return;}
    auto& done=motion_done[owner];
    if(done.generation!=a.generation){done.generation=a.generation;std::memset(done.bits,0,sizeof done.bits);}
    const bool tracked=index<MotionDoneEntries;
    if(tracked && (done.bits[index/8]>>(index%8)&1))return;
    if(motion_pending_count==MotionPendingCount){motion_fault(MotionCapacity);return;}   // retried at a later use
    if(tracked)done.bits[index/8]|=1U<<(index%8);
    Span span;if(!entry(a,index,span)){motion_fault(MotionNested);return;}
    unsigned crc,fnv;
    if(!(fcv && mtc_key(a,count,offset,crc,fnv))){
        MotionKey key;unsigned lo=0,hi=0;
        if(fcv && span.bytes>=4){const unsigned head=fcv_prefix(data);
            if(head<=span.bytes && 4*unsigned(data[2])<=head){lo=head-4*unsigned(data[2]);hi=head;}}
        const auto base=unsigned(reinterpret_cast<std::uintptr_t>(data));
        for(unsigned j=0;j<span.bytes;){
            if(j>=lo && j<hi && !((j-lo)&3)){
                unsigned w=word(data,j);if(int(w)<0)w-=base;   // relocated in place by the source evaluator
                for(unsigned k=0;k<4;++k)key.add((unsigned char)(w>>(8*k)));
                j+=4;
            } else key.add(data[j++]);
        }
        crc=~key.crc;fnv=key.fnv;
    }
    char id[24];::snprintf(id,sizeof id,"%08x-%08x",crc,fnv);
    unsigned char k8[8];std::memcpy(k8,&crc,4);std::memcpy(k8+4,&fnv,4);
    const CheckedAsset asset=bind_checked("motion",id,fingerprint(k8,8));
    if(!asset.value){motion_fault(MotionBind);return;}
    motion_pending[motion_pending_count++]=asset.value;
}
void motion_flush() {
    unsigned pending[MotionPendingCount],n=0,faults[MotionFaults];
    if(motion_lock.test_and_set(std::memory_order_acquire))return;   // a use holds it: next flush
    n=motion_pending_count;std::memcpy(pending,motion_pending,n*sizeof(unsigned));motion_pending_count=0;
    std::memcpy(faults,motion_faults,sizeof faults);std::memset(motion_faults,0,sizeof motion_faults);
    motion_lock.clear(std::memory_order_release);
    static const char* const why[MotionFaults]={"motion-unbound","motion-nested","motion-catalog-bind","motion-capacity","motion-busy"};
    for(unsigned f=0;f<MotionFaults;++f)for(unsigned c=0;c<faults[f];++c)unresolved(Motion,why[f]);
    for(unsigned i=0;i<n;++i)emitted_checked(Motion,CheckedAsset{pending[i]});
}
// Visit boundary: every clip is reported again in the new visit.
void motion_visit_reset() {
    if(motion_lock.test_and_set(std::memory_order_acquire))return;
    for(auto& d:motion_done)d.generation=0;
    for(auto& q:motion_fault_ring)q=nullptr;
    motion_lock.clear(std::memory_order_release);
}
}
extern "C" void re4dc_gcasset_capture_model(const void* data) { re4dc_gcasset::member_capture(data); }
extern "C" void re4dc_gcasset_motion_use(const void* data) { re4dc_gcasset::motion_use(data); }
extern "C" void re4dc_gcasset_retire_archive(const void* base) { re4dc_gcasset::member_retire_archive(base); }
// block.cpp (gc-catalog24b): st*/rNNN_NN.dat block archives, adopted as loaded
// (before BlockCreate relocates their BINs), moved with pool compaction,
// retired where the block's draw owner is unbound.
extern "C" void re4dc_gcasset_block_adopt(const void* owner,void* archive,unsigned bytes) {
    if(re4dc_gcasset::ensure_disc_catalog())re4dc_gcasset::member_adopt(owner,archive,bytes,true);
}
extern "C" void re4dc_gcasset_block_move(const void* owner,void* base) { re4dc_gcasset::member_move(owner,base); }
extern "C" void re4dc_gcasset_block_retire(const void* owner) { re4dc_gcasset::member_retire(owner); }
#endif
