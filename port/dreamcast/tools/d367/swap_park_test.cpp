// swap_park_test.cpp (SS_CERT host gate, 2026-10-04): the REAL game/actor_lifetime.inc and game/actor_swap_park.inc
// compiled on the host with a minimal material prelude, driven through their extern "C" entry points across a
// simulated sub screen swap. Archives, BINs, TPLs and cModelInfos live in an arena mapped below 4 GiB so the source
// helpers' 32-bit pointer words (ptrat) work unchanged. Build variants (swap_park_test.sh):
//   -DTEST_WIDE=0  two role words / 32-bit BlobMask, test row in word 1, test blob bit 20
//   -DTEST_WIDE=1  NATIVE_MODEL_REGISTRY(+_PACK), three role words / 64-bit BlobMask, test row 65 (word 2), blob bit 40
//   -DRE4DC_SS_CERT=0  knob off: only the gap reproduction runs (the original revocation is unchanged)
#include <cstdarg>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <cstdio>
#include <cstdlib>
#include <vector>
#include <sys/mman.h>
#define RE4DC_ACTOR_TRANSACTION 1
#define RE4DC_ACTOR_PL08 0
#define RE4DC_CROWD_CENSUS 0
#define RE4DC_CROWD_READOPT 0
#define RE4DC_NATIVE_MODEL_REGISTRY_TX 0
#define RE4DC_NATIVE_MODEL_REGISTRY_CENSUS 0
#if TEST_WIDE
#define RE4DC_NATIVE_MODEL_REGISTRY 1
#define RE4DC_NATIVE_MODEL_REGISTRY_PACK 1
#else
#define RE4DC_NATIVE_MODEL_REGISTRY 0
#define RE4DC_NATIVE_MODEL_REGISTRY_PACK 0
#endif
// Source structures, host layout: ModelData keeps the source's 32-bit section words at their offsets.
struct P32 { std::uint32_t v; };
inline bool operator==(P32 a,const void* p) {return a.v==std::uint32_t(reinterpret_cast<std::uintptr_t>(p));}
struct ModelData { P32 pHead;std::uint32_t w4,w8;P32 pClr,pTex,pWeight;std::uint32_t w24;P32 pParts;std::uint32_t w32[4];P32 vtxOrig,nrmOrig;std::uint32_t displist_num; };
static_assert(offsetof(ModelData,pParts)==28 && offsetof(ModelData,vtxOrig)==48 && offsetof(ModelData,nrmOrig)==52,"source offsets");
class cModelInfo { public: ModelData* pData;const void* tpl_addr;cModelInfo* pList; };
class cModel { public: unsigned serial;void* pParts;cModelInfo* pModelInfo;unsigned id; };
#include "actor_lifetime.h"
#include "actor_transaction_diag.h"
#define RE4DC_LEON_LIKE(app) ((app)==0x100u)
#define RE4DC_LEON_HEADLESS 0
#define RE4DC_HEAD_APP(app) 0
constexpr unsigned kRe4dcActorRoles=8u;
extern "C" unsigned re4dc_registry_sections(unsigned) {return 0;}
static unsigned log_lines;static char last_log[512];
extern "C" void re4dc_log(const char* f,...) {
    va_list a;va_start(a,f);std::vsnprintf(last_log,sizeof last_log,f,a);va_end(a);++log_lines;
    if(std::getenv("SWAP_PARK_LOG"))std::fputs(last_log,stdout);
}
constexpr std::uintptr_t kArena=0x10000000u;constexpr unsigned kArenaBytes=0x400000u;
namespace re4dc_material {
#if TEST_WIDE
#define RE4DC_ACTOR_WIDE_IDENTITY 1
constexpr unsigned kRoleMaskWords=3,kBlobMaskBits=64;using BlobMask=std::uint64_t;
constexpr unsigned kTestRole=65,kTestBlob=40;
#else
#define RE4DC_ACTOR_WIDE_IDENTITY 0
constexpr unsigned kRoleMaskWords=2,kBlobMaskBits=32;using BlobMask=unsigned;
constexpr unsigned kTestRole=40,kTestBlob=20;
#endif
constexpr unsigned kRoleMaskBits=kRoleMaskWords*32u;
struct Digest { unsigned bytes,crc,fnv; };
struct Texture { unsigned crc,fnv,width,height,format;unsigned sampler[8];unsigned palette_format;Digest palette; };
struct Model { unsigned header[10]; };
struct Role { unsigned appearance,role,source_bin,source_tpl;const Model* model;const Texture* textures;unsigned texture_count; };
struct SourceBlob { const Model* model;unsigned family,bin;Digest normalized; };
enum class Error : unsigned { None,BadRange };
Model test_model{},other_model{};
Role roles[kTestRole+1];
#if TEST_PARTNER_FIXTURE
SourceBlob source_blobs[kTestBlob+22]; // BIN4 plus 21 exact additional BINs; all fit the 64-bit host mask.
#else
SourceBlob source_blobs[kTestBlob+1];
#endif
#if RE4DC_NATIVE_MODEL_REGISTRY_PACK
constexpr unsigned kBaseRoles=sizeof(roles)/sizeof(roles[0]),kBaseBlobs=sizeof(source_blobs)/sizeof(source_blobs[0]);
struct RoomRows { const Role* roles;const SourceBlob* blobs;unsigned role_count,blob_count,generation; };
RoomRows room_rows{};
inline unsigned role_count() {return kBaseRoles+room_rows.role_count;}
inline const Role& role_row(unsigned r) {return r<kBaseRoles?roles[r]:room_rows.roles[r-kBaseRoles];}
inline unsigned blob_count() {return kBaseBlobs+room_rows.blob_count;}
inline const SourceBlob& blob_row(unsigned t) {return t<kBaseBlobs?source_blobs[t]:room_rows.blobs[t-kBaseBlobs];}
#define RE4DC_ROLE_COUNT (re4dc_material::role_count())
#define RE4DC_ROLE(r) (re4dc_material::role_row(r))
#define RE4DC_BLOB_COUNT (re4dc_material::blob_count())
#define RE4DC_BLOB(t) (re4dc_material::blob_row(t))
#else
#define RE4DC_ROLE_COUNT sizeof(roles)/sizeof(roles[0])
#define RE4DC_ROLE(r) roles[r]
#define RE4DC_BLOB_COUNT sizeof(source_blobs)/sizeof(source_blobs[0])
#define RE4DC_BLOB(t) source_blobs[t]
#endif
inline bool readable(const void* p,unsigned n) {
    const auto a=reinterpret_cast<std::uintptr_t>(p);return a>=kArena && a<=kArena+kArenaBytes && n<=kArena+kArenaBytes-a;
}
inline unsigned u32at(const void* p,unsigned at) {unsigned x;std::memcpy(&x,static_cast<const unsigned char*>(p)+at,4);return x;}
inline const void* ptrat(const void* p,unsigned at) {return reinterpret_cast<const void*>(std::uintptr_t(u32at(p,at)));}
inline void crcfnv(const unsigned char* b,unsigned n,unsigned& crc,unsigned& fnv) {
    crc=~0u;fnv=2166136261u;
    for(unsigned k=0;k<n;++k){crc^=b[k];fnv=(fnv^b[k])*16777619u;for(unsigned j=0;j<8;++j)crc=(crc>>1)^(0xedb88320u&(0u-(crc&1u)));}
    crc=~crc;
}
bool digest(const void* p,const Digest& want) {
    if(!readable(p,want.bytes))return false;
    unsigned c,f;crcfnv(static_cast<const unsigned char*>(p),want.bytes,c,f);return c==want.crc && f==want.fnv;
}
Error texture(const void*,const Texture&) {return Error::None;}  // texture_count 0 in every test row
}
#include "actor_lifetime.inc"

namespace {
using namespace re4dc_material;using namespace re4dc_material::life;
unsigned fails,checks;
#define CHECK(c) do{++checks;if(!(c)){++fails;std::printf("FAIL %s:%d %s (%s)\n",__func__,__LINE__,#c,last_log);}}while(0)
unsigned char* const arena=reinterpret_cast<unsigned char*>(kArena);
unsigned char* const W=arena+0x100000;constexpr unsigned WB=0x40000;  // the swapped window
std::uintptr_t hole_lo,hole_hi;                                        // a skipped free cell inside it
std::vector<unsigned char> backing;
constexpr unsigned kApp=5,kBin=64,kTplOff=128,kArchiveBytes=160;
const unsigned kFields[7]={0,12,16,20,28,48,52},kOffs[7]={4,8,24,32,36,40,44};
void pristine_bin(unsigned char* b) {
    for(unsigned k=0;k<kBin;++k)b[k]=static_cast<unsigned char>(0x30+k*7);
    for(unsigned j=0;j<7;++j)std::memcpy(b+kFields[j],&kOffs[j],4);
}
int saved(const void* p,unsigned n) {
    const auto a=reinterpret_cast<std::uintptr_t>(p);
    return !(hole_hi>hole_lo && a<hole_hi && a+n>hole_lo);
}
void reset() {
    for(auto& o:archives)o={};for(auto& a:assets)a={};for(auto& i:infos_live)i={};for(auto& b:bindings)b={};
    serial=1;epoch=1;exhausted=false;
#if RE4DC_SS_CERT
    park={};for(auto& p:park_archives)p={};for(auto& a:park_assets)a={};for(auto& p:park_infos)p={};
#endif
#if RE4DC_NATIVE_MODEL_REGISTRY_PACK
    room_rows={};
#endif
    std::memset(arena,0,kArenaBytes);hole_lo=hole_hi=0;
}
struct Arch { unsigned char* base;cModelInfo* info;cModel m; };
// A DRS with one BIN (entry 4) and one TPL (entry 5) at `at`, adopted as family 2 under key `at` and relocated as
// the source does after adoption; its cModelInfo at `info_at`, adopted through the load-time proof.
void relocate(const Arch& a) {
    for(unsigned j=0;j<7;++j){const unsigned p=unsigned(reinterpret_cast<std::uintptr_t>(a.base+kBin+kOffs[j]));std::memcpy(a.base+kBin+kFields[j],&p,4);}
}
// relocated=false: the archive is adopted but calcModelAddr has not run yet (no instance: r102's em18 read ahead of
// setEm(0x4C)), so no cModelInfo exists either; relocate() + re4dc_actor_info_adopt() do it later.
Arch make(unsigned char* at,unsigned char* info_at,bool adopt_info=true,bool relocated=true) {
    Arch a{at,reinterpret_cast<cModelInfo*>(info_at),{}};
    std::memset(at,0,kArchiveBytes);
    const unsigned head[4]={2,0,kBin,kTplOff};std::memcpy(at,head,8);std::memcpy(at+16,head+2,8);
    std::memcpy(at+24,"BIN\0TPL\0",8);
    pristine_bin(at+kBin);
    const unsigned self=unsigned(reinterpret_cast<std::uintptr_t>(at+kTplOff));std::memcpy(at+kTplOff+8,&self,4);
    re4dc_actor_archive_adopt(at,at,kArchiveBytes,2);
    if(!relocated)return a;
    relocate(a);
    *a.info=cModelInfo{reinterpret_cast<ModelData*>(at+kBin),at+kTplOff,nullptr};
    a.m.pModelInfo=a.info;a.m.serial=1;
    if(adopt_info)re4dc_actor_info_adopt(a.info);
    return a;
}
// No live record: no proof (and the cModelInfo, possibly cleared with the window, is not walked).
bool proof(Arch& a) {return find_info(a.info) && re4dc_actor_material_owner_proof(&a.m,a.info,kApp,0,RE4DC_ACTOR_MATERIAL_RECORD_REVISION)==1;}
unsigned live_archives() {unsigned n=0;for(const auto& o:archives)n+=o.key!=nullptr;return n;}
unsigned revision_of(const void* key) {for(const auto& o:archives)if(o.key==key)return o.revision;return 0;}
// The swap as sscrn_bridge.cpp does it: save, (park), clear the window; restore everything but the hole, (unpark).
void swap_open() {
    backing.assign(W,W+WB);
#if RE4DC_SS_CERT
    re4dc_actor_swap_park(W,WB,saved);
#endif
    std::memset(W,0xA5,WB);
}
void ui_frees() {  // the sub screen's own frees while open, then MemDestroyHeap(12)
    re4dc_actor_forget_range(W+0x800,0x40);re4dc_actor_info_retire(W+0x2000);re4dc_actor_data_move(W+0x3000);
    re4dc_actor_forget_range(W+0x1000,WB-0x2000);
}
void swap_close(bool restored=true) {
    for(unsigned k=0;k<WB;++k){const auto a=reinterpret_cast<std::uintptr_t>(W+k);if(!(a>=hole_lo && a<hole_hi))W[k]=backing[k];}
#if RE4DC_SS_CERT
    re4dc_actor_swap_unpark(restored);
#else
    (void)restored;
#endif
}

void gap_without_park() {  // the reported gap: heap-12 destroy revokes the archive; restored bytes cannot re-adopt
    reset();Arch a=make(W+0x10000,W+0x20000);CHECK(proof(a));
    backing.assign(W,W+WB);std::memset(W,0xA5,WB);
    re4dc_actor_forget_range(W+0x1000,WB-0x2000);
    for(unsigned k=0;k<WB;++k)W[k]=backing[k];
    CHECK(!proof(a));re4dc_actor_info_adopt(a.info);CHECK(!proof(a));CHECK(live_archives()==0);
}
#if RE4DC_SS_CERT
void repair() {
    reset();Arch a=make(W+0x10000,W+0x20000);CHECK(proof(a));
    const unsigned rev0=revision_of(W+0x10000),epoch0=epoch;
    swap_open();
    CHECK(!proof(a));CHECK(live_archives()==0);CHECK(park.narchive==1 && park.nasset==1 && park.ninfo==1);
    ui_frees();CHECK(park.temporary==4);CHECK(park.dropped_archives==0 && park.dropped_infos==0);
    swap_close();
    CHECK(proof(a));const unsigned rev1=revision_of(W+0x10000);CHECK(rev1 && rev1!=rev0);CHECK(epoch!=epoch0);
    CHECK(park.published_archives==1 && park.published_assets==1 && park.published_infos==1 && !park.open);
    const auto* i=find_info(a.info);CHECK(i && assets[i->asset].owner_revision==rev1 && i->tpl_revision==rev1);
    // A second open/close of the same room repeats it; a close without an open does nothing.
    swap_open();ui_frees();swap_close();CHECK(proof(a));CHECK(revision_of(W+0x10000)!=rev1);
    const unsigned n=live_archives();re4dc_actor_swap_unpark(1);CHECK(live_archives()==n && proof(a));
    // Genuine invalidation after close still works.
    re4dc_actor_forget_range(W+0x10000,kArchiveBytes);CHECK(!proof(a));
}
void restore_failed() {
    reset();Arch a=make(W+0x10000,W+0x20000);swap_open();ui_frees();swap_close(false);
    CHECK(!proof(a));CHECK(live_archives()==0);CHECK(park.dropped_archives==1);
}
void bytes_changed() {
    reset();Arch a=make(W+0x10000,W+0x20000);swap_open();ui_frees();
    backing[0x10000+kTplOff+20]^=1;  // the restored archive differs in one byte
    swap_close();CHECK(!proof(a));CHECK(live_archives()==0);
}
void skipped_free_cell() {
    reset();Arch a=make(W+0x10000,W+0x20000);
    hole_lo=reinterpret_cast<std::uintptr_t>(W+0x10000+kTplOff);hole_hi=hole_lo+16;
    swap_open();CHECK(park.narchive==0 && park.revoked_at_open==1);CHECK(!proof(a));
    swap_close();CHECK(!proof(a));
    // An info in a skipped cell: dropped at open, its archive (outside the window) stays live.
    reset();Arch b=make(arena+0x10000,W+0x30000);
    hole_lo=reinterpret_cast<std::uintptr_t>(W+0x30000);hole_hi=hole_lo+8;
    swap_open();CHECK(park.ninfo==0 && park.dropped_infos==1 && live_archives()==1);swap_close();CHECK(!proof(b));
}
void cross_boundary() {
    unsigned char* at=W+WB-80;  // the archive's last 80 bytes lie outside the window
    reset();{Arch a=make(at,arena+0x20000);swap_open();ui_frees();swap_close();CHECK(proof(a));}
    reset();{Arch a=make(at,arena+0x20000);swap_open();at[kArchiveBytes-4]^=1;ui_frees();swap_close();CHECK(!proof(a));}
    reset();{Arch a=make(at,arena+0x20000);swap_open();re4dc_actor_forget_range(W+WB,64);CHECK(park.dropped_archives==1);swap_close();CHECK(!proof(a));}
    reset();{Arch a=make(at,arena+0x20000);swap_open();re4dc_actor_data_move(W+WB+8);swap_close();CHECK(!proof(a));}
}
void genuine_retire() {
    reset();{Arch a=make(W+0x10000,W+0x20000);swap_open();re4dc_actor_archive_retire(W+0x10000);swap_close();CHECK(!proof(a));}
    reset();{Arch a=make(W+0x10000,W+0x20000);swap_open();re4dc_actor_archive_retire_transient();swap_close();CHECK(!proof(a));}
    reset();{Arch a=make(W+0x10000,W+0x20000);swap_open();re4dc_actor_forget_all();swap_close();CHECK(!proof(a));}
    reset();{Arch a=make(W+0x10000,W+0x20000);swap_open();re4dc_actor_data_move(W+0x10000+8);swap_close();CHECK(proof(a));}
}
void overlapping_owner() {
    // A new adoption over the parked bytes (here a copy inside the window, under another key) drops the parked one.
    reset();{Arch a=make(W+0x10000,W+0x20000);swap_open();
        unsigned char* b=W+0x10000+32;std::memset(b,0,kArchiveBytes);re4dc_actor_archive_adopt(arena+0x300000,b,kArchiveBytes,2);
        CHECK(park.dropped_archives==1);swap_close();CHECK(!proof(a));}
    // The same key adopted again elsewhere (the owner reloaded): dropped.
    reset();{Arch a=make(W+0x10000,W+0x20000);swap_open();make(arena+0x40000,arena+0x50000);
        re4dc_actor_archive_adopt(W+0x10000,arena+0x40000,kArchiveBytes,2);swap_close();CHECK(!proof(a));}
    // A live owner over the bytes at close (inserted directly): dropped.
    reset();{Arch a=make(W+0x10000,W+0x20000);swap_open();
        archives[7]={arena+0x300000,W+0x10000+16,32,999,2};swap_close();CHECK(!proof(a));}
    // A live owner with the parked key at close (elsewhere, inserted directly): dropped.
    reset();{Arch a=make(W+0x10000,W+0x20000);swap_open();
        archives[7]={W+0x10000,arena+0x300000,32,999,2};swap_close();CHECK(!proof(a));}
    // A parked asset record no longer current() against the restored bytes (its section moved): dropped.
    reset();{Arch a=make(W+0x10000,W+0x20000);swap_open();park_assets[0].a.section[2]=W;swap_close();
        CHECK(!proof(a) && live_archives()==0);}
    // A live record for the parked cModelInfo at close: the parked one is dropped, the live one stays.
    reset();{Arch a=make(W+0x10000,W+0x20000);swap_open();infos_live[kInfos-1].info=a.info;swap_close();
        CHECK(park.dropped_infos==1 && find_info(a.info)==&infos_live[kInfos-1]);}
}
void outside_objects() {
    // An info outside the window naming a parked archive: kept when unchanged, dropped when freed or rebound.
    reset();{Arch a=make(W+0x10000,arena+0x20000);swap_open();CHECK(park.ninfo==1);ui_frees();swap_close();CHECK(proof(a));}
    reset();{Arch a=make(W+0x10000,arena+0x20000);swap_open();re4dc_actor_forget_range(arena+0x20000,sizeof(cModelInfo));
        swap_close();CHECK(!proof(a));re4dc_actor_info_adopt(a.info);CHECK(proof(a));}
    reset();{Arch a=make(W+0x10000,arena+0x20000);swap_open();a.info->tpl_addr=arena;swap_close();CHECK(!proof(a));}
    reset();{Arch a=make(W+0x10000,arena+0x20000);swap_open();re4dc_actor_info_retire(arena+0x20000);swap_close();CHECK(!proof(a));}
    // An info inside the window naming an archive outside it: unavailable while open, back unless its owner changed.
    reset();{Arch a=make(arena+0x10000,W+0x20000);swap_open();CHECK(!proof(a) && live_archives()==1);ui_frees();swap_close();CHECK(proof(a));}
    reset();{Arch a=make(arena+0x10000,W+0x20000);swap_open();re4dc_actor_archive_retire(arena+0x10000);
        make(arena+0x10000,arena+0x60000,false);swap_close();CHECK(!proof(a));}
}
void serials() {
    reset();{Arch a=make(W+0x10000,W+0x20000);swap_open();serial=~0u-1;swap_close();  // revision ok, asset serial exhausted
        CHECK(!proof(a));CHECK(exhausted && live_archives()==0);}
    reset();{Arch a=make(W+0x10000,W+0x20000);serial=~0u;next();swap_open();CHECK(park.narchive==0 && park.revoked_at_open==1);
        swap_close();CHECK(!proof(a));}
}
void nested_and_pending() {
    reset();{Arch a=make(W+0x10000,W+0x20000);swap_open();re4dc_actor_swap_park(W,WB,saved);CHECK(park.nested==1);
        swap_close();CHECK(!proof(a));}
    reset();{Arch a=make(W+0x10000,W+0x20000);for(auto& x:assets)if(x.data)x.pending=77;
        swap_open();CHECK(park.narchive==0 && park.revoked_at_open==1);swap_close();CHECK(!proof(a));}
}
void capacity() {
    reset();Arch a[5];
    for(unsigned k=0;k<5;++k)a[k]=make(W+0x10000+k*0x1000,W+0x20000+k*0x100);
    for(unsigned k=0;k<5;++k)CHECK(proof(a[k]));
    swap_open();CHECK(park.narchive==kParkArchives && park.revoked_at_open==1);ui_frees();swap_close();
    unsigned back=0;for(unsigned k=0;k<5;++k)back+=proof(a[k]);CHECK(back==kParkArchives);
}
#if TEST_PARTNER_FIXTURE
// Two real source archives adopted through the production entry point: the r207 capacity shape,
// not direct fabrication of live certificates. Extra BINs have the same independently hashed fixture
// geometry at distinct source entries; only BIN4 has a model-info instance.
Arch make_many(unsigned char* at,unsigned char* info_at,unsigned nbins) {
    CHECK(nbins>=1 && nbins<=23);
    constexpr unsigned bytes=0x1900,boff=0x200,tploff=0x1800;
    std::memset(at,0,bytes);const unsigned count=nbins+1;
    std::memcpy(at,&count,4);
    for(unsigned i=0;i<count;++i) {
        const unsigned off=i==1?tploff:boff+(i?i-1:0)*0x80;
        std::memcpy(at+16+i*4,&off,4);
        std::memcpy(at+16+count*4+i*4,i==1?"TPL":"BIN",3);
        if(i!=1)pristine_bin(at+off);
    }
    const unsigned self=unsigned(reinterpret_cast<std::uintptr_t>(at+tploff));
    std::memcpy(at+tploff+8,&self,4);
    re4dc_actor_archive_adopt(at,at,bytes,2);
    for(unsigned i=0;i<nbins;++i) {
        Arch part{at+boff+i*0x80-kBin,nullptr,{}};
        relocate(part);
    }
    Arch a{at,reinterpret_cast<cModelInfo*>(info_at),{}};
    *a.info=cModelInfo{reinterpret_cast<ModelData*>(at+boff),at+tploff,nullptr};
    a.m.pModelInfo=a.info;a.m.serial=1;re4dc_actor_info_adopt(a.info);return a;
}
void partner_capacity() {
    // Extra source entries 6..27; 23 BINs can exercise the still-refused 33-asset case.
    unsigned char raw[kBin];pristine_bin(raw);unsigned c,f;crcfnv(raw,kBin,c,f);
    for(unsigned i=1;i<=21;++i)source_blobs[kTestBlob+i]={&test_model,2,5+i,{kBin,c,f}};
    auto pair=[](unsigned n) {
        Arch a=make_many(W+0x10000,W+0x24000,n);
        Arch b=make_many(W+0x14000,W+0x24100,10);
        CHECK(proof(a) && proof(b));CHECK(live_archives()==2);
        return std::vector<Arch>{a,b};
    };
    reset();auto a=pair(22);swap_open();
#if RE4DC_SS_CERT_PARTNER_CAPACITY
    CHECK(park.narchive==2 && park.nasset==32 && park.revoked_at_open==0);
#else
    CHECK(park.narchive==1 && park.nasset==22 && park.revoked_at_open==1);
#endif
    ui_frees();swap_close();CHECK(proof(a[0]));
#if RE4DC_SS_CERT_PARTNER_CAPACITY
    CHECK(proof(a[1]));CHECK(park.published_assets==32);
#else
    CHECK(!proof(a[1]));
#endif
    // The larger park must still reject a changed source archive and an unsaved byte.
    reset();a=pair(22);swap_open();backing[0x14000+0x210]^=1;swap_close();
    CHECK(proof(a[0]) && !proof(a[1]));
    reset();a=pair(22);hole_lo=reinterpret_cast<std::uintptr_t>(W+0x14008);hole_hi=hole_lo+1;
    swap_open();CHECK(park.revoked_at_open==1);swap_close();CHECK(proof(a[0]) && !proof(a[1]));
    // Capacity is bounded: 23+10 still cannot park both. The 23rd BIN uses no new template,
    // so add its reviewed source row temporarily in the existing unused row zero.
    source_blobs[0]={&test_model,2,27,{kBin,c,f}};
    reset();a=pair(23);swap_open();CHECK(park.narchive==1 && park.nasset==23 && park.revoked_at_open==1);
    swap_close();CHECK(proof(a[0]) && !proof(a[1]));
}
#endif
void room_rows_change() {
#if RE4DC_NATIVE_MODEL_REGISTRY_PACK
    reset();{room_rows_publish(nullptr,0,nullptr,0,7);Arch a=make(W+0x10000,W+0x20000);swap_open();swap_close();CHECK(proof(a));}
    reset();{room_rows_publish(nullptr,0,nullptr,0,7);Arch a=make(W+0x10000,W+0x20000);swap_open();
        room_rows_publish(nullptr,0,nullptr,0,8);swap_close();CHECK(!proof(a));}
#endif
}
void unrelocated_at_open() {
    // An adopted archive whose BIN is not relocated yet when the sub screen opens (PS2_CAST_MERCHANT, r102 em18).
    // Knob off: the unpark revokes the archive (its asset was not current() at open, so it cannot be at close).
    // RE4DC_NMR_PARK_UNRELOCATED: republished as it was; relocation + info adoption after close then prove it.
    reset();{Arch a=make(W+0x10000,W+0x20000,false,false);CHECK(live_archives()==1);swap_open();ui_frees();swap_close();
#if RE4DC_NMR_PARK_UNRELOCATED
        CHECK(live_archives()==1 && park.published_archives==1 && park.published_assets==1);
        relocate(a);*a.info=cModelInfo{reinterpret_cast<ModelData*>(a.base+kBin),a.base+kTplOff,nullptr};
        a.m.pModelInfo=a.info;a.m.serial=1;re4dc_actor_info_adopt(a.info);CHECK(proof(a));
        // An asset that was current at open and is not at close is still dropped (a moved section).
        reset();Arch b=make(W+0x10000,W+0x20000);swap_open();park_assets[0].a.section[2]=W;swap_close();
        CHECK(!proof(b) && live_archives()==0);
#else
        (void)a;CHECK(live_archives()==0);
#endif
    }
}
#endif
}

int main() {
    void* m=mmap(reinterpret_cast<void*>(kArena),kArenaBytes,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS|MAP_FIXED_NOREPLACE,-1,0);
    if(m!=reinterpret_cast<void*>(kArena)){std::printf("arena map failed\n");return 2;}
    using namespace re4dc_material;
    for(auto& r:roles)r={999,0,4,5,&other_model,nullptr,0};
    for(auto& b:source_blobs)b={&other_model,0,4,{}};
    roles[kTestRole]={kApp,0,4,5,&test_model,nullptr,0};
    unsigned char bin[kBin];pristine_bin(bin);unsigned c,f;crcfnv(bin,kBin,c,f);
    source_blobs[kTestBlob]={&test_model,2,4,{kBin,c,f}};
    gap_without_park();
#if RE4DC_SS_CERT
    repair();restore_failed();bytes_changed();skipped_free_cell();cross_boundary();genuine_retire();overlapping_owner();
    outside_objects();serials();nested_and_pending();capacity();room_rows_change();unrelocated_at_open();
#if TEST_PARTNER_FIXTURE
    partner_capacity();
#endif
#endif
    std::printf("swap_park_test ss_cert=%d wide=%d role_words=%u blob_bits=%u test_role=%u test_blob=%u checks=%u fails=%u log=%u %s\n",
                RE4DC_SS_CERT,TEST_WIDE,kRoleMaskWords,kBlobMaskBits,kTestRole,kTestBlob,checks,fails,log_lines,fails?"FAIL":"PASS");
    return fails?1:0;
}
