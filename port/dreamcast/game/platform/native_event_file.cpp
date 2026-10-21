// Qualified immutable preloads use existing disc transport, without a pretend
// ARAM copy. Preparation validates the offline qualification certificate and
// file size. Installation checks every payload chunk before source activation.
#include "native_event_file.h"
#include "native_io.h"
#include "re4dc_platform.h"
#include "../../room/room_storage.hpp"
#include <kos.h>
#include <kos/net.h>
#include <cstring>
#include <cstdio>

#if defined(RE4DC_EVD_ARAM_ALLOC_RETRY) && RE4DC_EVD_ARAM_ALLOC_RETRY
#if !defined(RE4DC_CABIN_SOURCE) || !RE4DC_CABIN_SOURCE
#error EVD_ARAM_ALLOC_RETRY requires CABIN_SOURCE
#endif
#endif

namespace {
Re4dcEventFileStats stats{};
constexpr unsigned chunk_bytes=65536, max_bytes=4*1024*1024;
unsigned word(const unsigned char* p) { unsigned v;std::memcpy(&v,p,4);return v; }
bool exact(file_t f,void* dst,unsigned n) {
    auto* p=static_cast<unsigned char*>(dst);
    while(n) { auto got=fs_read(f,p,n);if(got<=0 || unsigned(got)>n)return false;p+=got;n-=got; }
    return true;
}
struct Copy {
    const unsigned char* crc;
    unsigned index;
    unsigned char* out;
    unsigned chunk_used;
    unsigned remaining;
};
bool consume(const unsigned char* p,std::size_t n,void* opaque) {
    auto& c=*static_cast<Copy*>(opaque);
    stats.bytes_read+=n;
    if(n>c.remaining)return false;
    while(n) {
        const auto room=chunk_bytes-c.chunk_used;
        const auto take=n<room?n:room;
        // The final allocation remains private until transfer succeeds. Keep
        // certificate boundaries independent of the storage bounce size.
        std::memcpy(c.out,p,take);
        c.out+=take;p+=take;n-=take;
        c.chunk_used+=take;c.remaining-=take;
        if(c.chunk_used==chunk_bytes || !c.remaining) {
            if(net_crc32le(c.out-c.chunk_used,c.chunk_used)!=word(c.crc+4*c.index++))return false;
            c.chunk_used=0;
        }
    }
    return true;
}
bool transfer(const char* name,unsigned bytes,void* dst,unsigned expected_certificate=0) {
    if(!re4dc_event_file_name(name) || !bytes || bytes>max_bytes || (bytes&31))return false;
    Re4dcIoScope io;
    char path[96],sidecar[104];
    if(!re4dc_dvd_native_path(name,path,sizeof(path)))return false;
    snprintf(sidecar,sizeof(sidecar),"%s.evq",path);
    file_t q=fs_open(sidecar,O_RDONLY);if(q<0)return false;
    unsigned char table[32+4*(max_bytes/chunk_bytes)];
    const unsigned count=(bytes+chunk_bytes-1)/chunk_bytes, length=32+4*count;
    bool ok=fs_total(q)==static_cast<ssize_t>(length) && exact(q,table,length);
    if(ok)stats.metadata_bytes_read+=length;
    fs_close(q);
    if(!ok || std::memcmp(table,"R4EVDREF",8) || word(table+8)!=1 ||
       word(table+12)!=bytes || word(table+16)!=chunk_bytes || word(table+20)!=count ||
       word(table+24)!=net_crc32le(reinterpret_cast<const unsigned char*>(name),std::strlen(name)) ||
       word(table+28)!=net_crc32le(table+32,4*count) ||
       (expected_certificate && expected_certificate!=net_crc32le(table,length)))return false;
    file_t f=fs_open(path,O_RDONLY);if(f<0)return false;
    Copy c{table+32,0,static_cast<unsigned char*>(dst),0,bytes};
    ok=fs_total(f)==static_cast<ssize_t>(bytes);
    // A preload is a qualified immutable reference, not a wasted full-file
    // read into the bounce buffer. Data becomes usable only after install.
    if(ok && dst)ok=re4dc::storage::read_chunks(f,bytes,consume,&c) && !c.remaining && c.index==count;
    fs_close(f);
    return ok;
}
int run(const char* name,unsigned bytes,void* dst,unsigned expected_certificate=0) {
    const auto start=timer_us_gettime64();
    bool ok=transfer(name,bytes,dst,expected_certificate);
    const auto elapsed=timer_us_gettime64()-start;
    const unsigned us=elapsed>0xffffffffULL?0xffffffffU:unsigned(elapsed);
    if(us>stats.worst_wait_us)stats.worst_wait_us=us;
    if(!ok)++stats.failures;
    else if(dst)++stats.installed;
    else ++stats.prepared;
    re4dc_log("event file: %s %s bytes=%u wait_us=%u success=%u\n",dst?"install":"prepare",name,bytes,us,ok);
    return ok;
}
}
extern "C" int re4dc_event_file_name(const char* name) {
    if(!name)return 0;
    const auto n=std::strlen(name);
    if(n<9 || n>=32 || std::strncmp(name,"evd/",4) || std::strcmp(name+n-4,".evd"))return 0;
    // Exact canonical identity; reject traversal, aliases and truncated names.
    for(unsigned i=4;i<n-4;++i)if(!((name[i]>='a' && name[i]<='z') ||
        (name[i]>='0' && name[i]<='9') || name[i]=='_'))return 0;
    return 1;
}
extern "C" int re4dc_event_file_prepare(const char* n,unsigned b) { return run(n,b,nullptr); }
// The caller owns a source-reviewed completion contract for this exact qualified
// conversion. This reads only its existing EVQ certificate/file size: no event
// bytes are activated and no mutable ARAM or enemy snapshot is manufactured.
extern "C" int re4dc_event_file_reference(const char* n,unsigned b,unsigned certificate_crc) {
    return certificate_crc ? run(n,b,nullptr,certificate_crc) : 0;
}
extern "C" int re4dc_event_file_install(const char* n,unsigned b,void* dst) { return dst?run(n,b,dst):0; }
extern "C" void re4dc_event_file_moved() { ++stats.moves; }
extern "C" const Re4dcEventFileStats* re4dc_event_file_stats() { return &stats; }
#if RE4DC_EVENT_SWAP_RELOAD
// EVENT_SWAP_RELOAD (lane ch5found16): see dvd.cpp re4dc_event_swap_reload. Runs: {u32 offset, u32 length, data
// padded to 4}; nearby differences (gap <= 8) share a run.
namespace {
file_t swap_open(const char* name,unsigned* total){
    char path[96];
    if(!name || !re4dc_dvd_native_path(name,path,sizeof(path)))return -1;
    file_t f=fs_open(path,O_RDONLY);
    if(f>=0)*total=unsigned(fs_total(f));
    return f;
}
struct RunWriter {
    unsigned char* out; unsigned cap,used; const unsigned char* mram; unsigned start,end; bool open,full;
    void close(){
        if(!open)return;
        open=false;
        const unsigned n=end-start, need=8+((n+3)&~3U);
        if(used+need>cap){full=true;return;}
        std::memcpy(out+used,&start,4);std::memcpy(out+used+4,&n,4);
        std::memcpy(out+used+8,mram+start,n);
        used+=need;
    }
    void diff(unsigned at){
        if(open && at-end<=8){end=at+1;return;}
        close();
        open=true;start=at;end=at+1;
    }
};
}
extern "C" unsigned long long re4dc_swap_reload_now_us(void){ return timer_us_gettime64(); }
extern "C" int re4dc_event_file_install_direct(const char* name,unsigned bytes,void* dst){
    const auto start=timer_us_gettime64();
    bool ok=false;
    do{
        if(!re4dc_event_file_name(name) || !bytes || bytes>max_bytes || (bytes&31) || !dst)break;
        Re4dcIoScope io;
        char path[96],sidecar[104];
        if(!re4dc_dvd_native_path(name,path,sizeof(path)))break;
        snprintf(sidecar,sizeof(sidecar),"%s.evq",path);
        file_t q=fs_open(sidecar,O_RDONLY);if(q<0)break;
        unsigned char table[32+4*(max_bytes/chunk_bytes)];
        const unsigned count=(bytes+chunk_bytes-1)/chunk_bytes, length=32+4*count;
        const bool have=fs_total(q)==static_cast<ssize_t>(length) && exact(q,table,length);
        fs_close(q);
        if(!have || std::memcmp(table,"R4EVDREF",8) || word(table+8)!=1 || word(table+12)!=bytes ||
           word(table+16)!=chunk_bytes || word(table+20)!=count ||
           word(table+24)!=net_crc32le(reinterpret_cast<const unsigned char*>(name),std::strlen(name)) ||
           word(table+28)!=net_crc32le(table+32,4*count))break;
        stats.metadata_bytes_read+=length;
        file_t f=fs_open(path,O_RDONLY);if(f<0)break;
        bool r=fs_total(f)==static_cast<ssize_t>(bytes);
        auto* p=static_cast<unsigned char*>(dst);
        for(unsigned i=0;r && i<count;++i){
            const unsigned at=i*chunk_bytes, n=bytes-at<chunk_bytes?bytes-at:chunk_bytes;
            r=exact(f,p+at,n) && net_crc32le(p+at,n)==word(table+32+4*i);
            if(r)stats.bytes_read+=n;
        }
        fs_close(f);
        ok=r;
    }while(0);
    const auto elapsed=timer_us_gettime64()-start;
    const unsigned us=elapsed>0xffffffffULL?0xffffffffU:unsigned(elapsed);
    if(us>stats.worst_wait_us)stats.worst_wait_us=us;
    if(ok)++stats.installed;else ++stats.failures;
    re4dc_log("event file: install-direct %s bytes=%u wait_us=%u success=%u\n",name,bytes,us,ok);
    return ok;
}
// The archive is the DRS file's top-level type-0 parts, each 32-byte aligned, in order (dvd.cpp cDvdQueue mode 0x8000:
// DvdHeader {type, size, dest, ofs, ...} 0x20-byte entries from file offset 0x20 to type -1). Segments map archive
// offsets to file offsets; bytes outside every segment (alignment padding) are kept as runs.
struct SwapSeg { unsigned mem,file,len; };
static int swap_segments(file_t f,unsigned total,SwapSeg* segs,int max){
    unsigned char e[32];unsigned mem=0;int n=0;
    for(unsigned at=0x20;at+32<=total && at<0x20+64*32;at+=32){
        if(fs_seek(f,at,SEEK_SET)!=static_cast<off_t>(at) || !exact(f,e,32))return -1;
        const unsigned type=word(e),size=word(e+4),ofs=word(e+12);
        if(type==0xffffffffU)return n;
        if(type!=0)continue;
        if(n==max || ofs>total || size>total-ofs)return -1;
        segs[n++]=SwapSeg{mem,ofs,size};
        mem+=(size+31)&~31U;
    }
    return -1;
}
extern "C" int re4dc_swap_reload_record(const char* file,const void* mram,unsigned bytes,void* bounce,unsigned bounce_bytes,
                                        void* runs,unsigned cap,unsigned* crc){
    unsigned total=0;
    Re4dcIoScope io;
    file_t f=swap_open(file,&total);
    if(f<0)return -1;
    SwapSeg segs[8];
    const int nseg=swap_segments(f,total,segs,8);
    RunWriter w{static_cast<unsigned char*>(runs),cap,0,static_cast<const unsigned char*>(mram),0,0,false,false};
    const auto* m=static_cast<const unsigned char*>(mram);
    const auto* b=static_cast<const unsigned char*>(bounce);
    bool ok=nseg>0;
    unsigned differing=0,covered=0;
    // walk the region in archive order: segment bytes are compared with the file, the rest are differences
    unsigned pos=0;
    for(int s=0;ok && s<nseg && pos<bytes;++s){
        for(;pos<segs[s].mem && pos<bytes;++pos){++differing;if(!w.full)w.diff(pos);}
        const unsigned end=segs[s].mem+segs[s].len<bytes?segs[s].mem+segs[s].len:bytes;
        if(pos>=end)continue;
        ok=fs_seek(f,segs[s].file+(pos-segs[s].mem),SEEK_SET)==static_cast<off_t>(segs[s].file+(pos-segs[s].mem));
        while(ok && pos<end){
            const unsigned n=end-pos<bounce_bytes?end-pos:bounce_bytes;
            ok=exact(f,bounce,n);
            for(unsigned i=0;ok && i<n;++i)if(m[pos+i]!=b[i]){++differing;if(!w.full)w.diff(pos+i);}
            pos+=n;covered+=n;
        }
    }
    fs_close(f);
    for(;ok && pos<bytes;++pos){++differing;if(!w.full)w.diff(pos);}
    w.close();
    re4dc_log("event swap reload: compare %s file=%u parts=%d region=%u covered=%u differing=%u used=%u full=%d ok=%d\n",
              file,total,nseg,bytes,covered,differing,w.used,w.full,ok);
    if(!ok || w.full)return -1;
    *crc=net_crc32le(m,bytes);
    return int(w.used);
}
extern "C" int re4dc_swap_reload_restore(const char* file,void* mram,unsigned bytes,const void* runs,unsigned used,unsigned crc){
    unsigned total=0;
    Re4dcIoScope io;
    file_t f=swap_open(file,&total);
    if(f<0)return 0;
    SwapSeg segs[8];
    const int nseg=swap_segments(f,total,segs,8);
    auto* m=static_cast<unsigned char*>(mram);
    bool ok=nseg>0;
    for(int s=0;ok && s<nseg;++s){
        if(segs[s].mem>=bytes)break;
        const unsigned n=segs[s].mem+segs[s].len<bytes?segs[s].len:bytes-segs[s].mem;
        ok=fs_seek(f,segs[s].file,SEEK_SET)==static_cast<off_t>(segs[s].file) && exact(f,m+segs[s].mem,n);
    }
    fs_close(f);
    const auto* r=static_cast<const unsigned char*>(runs);
    for(unsigned at=0;ok && at+8<=used;){
        unsigned o,n;std::memcpy(&o,r+at,4);std::memcpy(&n,r+at+4,4);
        if(o>bytes || n>bytes-o || at+8+n>used){ok=false;break;}
        std::memcpy(m+o,r+at+8,n);
        at+=8+((n+3)&~3U);
    }
    return ok && net_crc32le(m,bytes)==crc;
}
#endif
extern "C" void re4dc_event_file_reject_swap() {
    ++stats.failures;
    re4dc_missing("MemorySwap: immutable EVD requires mutable snapshot backing");
    __builtin_trap();
}

#if RE4DC_CABIN_SOURCE
// CABIN_CARRIER_OWNER_BEGIN
// Logical ARAM remains immutable unless this exact source unit has admitted a
// private, verified, mutable copy. No shared ARQ/audio implementation is used.
extern "C" int re4dc_cabin_source_unit_valid(const void*,unsigned,unsigned,unsigned);
extern "C" int re4dc_cabin_source_unit_clear(void*);
extern "C" int re4dc_cabin_source_unit_retire_ready(const void*,unsigned,unsigned,unsigned,const void*);
extern "C" int re4dc_cabin_source_unit_release(void*,unsigned);
extern "C" int re4dc_cabin_source_range_available(const void*,unsigned,unsigned);
extern "C" const void* re4dc_cabin_source_module(const void*,unsigned);
extern "C" int re4dc_cabin_source_allocation(const void*,unsigned,int*);
extern "C" void* re4dc_cabin_source_alloc(unsigned,int);
extern "C" int re4dc_cabin_source_free(void*,unsigned,int);
extern "C" int re4dc_cabin_source_swap_buffer(unsigned,unsigned,unsigned);
namespace {
enum CarrierState { CarrierAbsent,CarrierPreparing,CarrierReference,CarrierReady,CarrierSwap,CarrierMram,CarrierFailed };
struct CabinCarrier {
    void* unit; unsigned generation,logical,bytes; void* backing; int heap,backing_heap;
    void* mram; const void* module; const void* event;
    unsigned state,role,phase,readers; bool releasing;
};
struct CabinCarrierDma {
    const void* request; unsigned generation,owner,type,src,dst,bytes,state,token;
    void* mram; int heap;
};
CabinCarrier carriers[3]{};
CabinCarrierDma carrier_dma[16]{};
unsigned carrier_epoch,carrier_event_readers,carrier_dma_scope,carrier_dma_epoch;
bool carrier_fault;
static_assert(sizeof(carriers)+sizeof(carrier_dma)+sizeof(carrier_epoch)+
              sizeof(carrier_event_readers)+sizeof(carrier_dma_scope)+sizeof(carrier_dma_epoch)+sizeof(carrier_fault)<=1024,
              "review cabin carrier fixed metadata budget");
const char* carrier_names[3]={"evd/r11cs00.evd","evd/r11cs10.evd","evd/r11cs20.evd"};
const unsigned carrier_sizes[3]={27456,7296,5568};
const unsigned carrier_certificates[3]={0x71ab9c4d,0x8ede2d00,0x55c322f1};
int carrier_index(const char* name){
    if(name)for(unsigned i=0;i<3;++i)if(!std::strcmp(name,carrier_names[i]))return (int)i;
    return -1;
}
bool carrier_overlap(unsigned a,unsigned n,unsigned b,unsigned m){
    if(!n||!m)return false;
    if(a+n<a||b+m<b)return true;
    return a<b+m && b<a+n;
}
CabinCarrier* carrier_token(unsigned token){
    if(token)for(auto& c:carriers)if(c.state && c.generation==token)return &c;
    return nullptr;
}
unsigned carrier_number(const CabinCarrier& c){return unsigned(&c-carriers);}
bool carrier_current(const CabinCarrier& c){
    return c.state && c.unit && re4dc_cabin_source_unit_valid(c.unit,carrier_number(c),c.logical,c.bytes);
}
int carrier_fail(CabinCarrier* c){
    if(c){
        // A completed first exchange may already hold the only displaced module
        // copy. An error must never turn it into a reclaimable ordinary buffer.
        if(c->state==CarrierSwap && c->phase>=2)c->role=1;
        c->state=CarrierFailed;
    }
    return -1;
}
CabinCarrier* carrier_range(unsigned address,unsigned bytes){
    CabinCarrier* result=nullptr;
    for(auto& c:carriers)if(c.state && carrier_overlap(address,bytes,c.logical,c.bytes)){
        if(result){carrier_fault=true;return nullptr;}result=&c;
    }
    return result;
}
bool carrier_inside(unsigned address,unsigned bytes,unsigned base,unsigned size){
    return bytes && !(address&31) && !(bytes&31) && address>=base && address-base<=size && bytes<=size-(address-base);
}
bool carrier_mram_current(const CabinCarrier& c){
    int heap=-1;
    if(!c.mram || !re4dc_cabin_source_allocation(c.mram,c.bytes,&heap) || heap!=c.heap)return false;
    return !c.module || re4dc_cabin_source_module(c.mram,c.bytes)==c.module;
}
bool carrier_backing_current(const CabinCarrier& c){
    if(!c.backing)return true;
    int heap=-1;
    return re4dc_cabin_source_allocation(c.backing,c.bytes,&heap) && heap==c.backing_heap;
}
bool carrier_can_retire(const CabinCarrier& c){
    return c.state!=CarrierPreparing && c.state!=CarrierSwap && !c.readers &&
        !c.event && !carrier_event_readers && !carrier_dma_scope && !c.releasing && c.role!=1;
}
bool carrier_retirement_ready(const CabinCarrier& c){
    if(!carrier_can_retire(c) || !carrier_backing_current(c) ||
       (c.mram && !carrier_mram_current(c)) ||
       !re4dc_cabin_source_unit_retire_ready(c.unit,carrier_number(c),c.logical,c.bytes,c.mram))return false;
    const void* owned[]={c.backing,c.mram};
    for(const void* p:owned)if(p)for(const auto& other:carriers)if(&other!=&c && other.state &&
       (carrier_overlap((unsigned)(uintptr_t)p,c.bytes,(unsigned)(uintptr_t)other.backing,other.backing?other.bytes:0) ||
        carrier_overlap((unsigned)(uintptr_t)p,c.bytes,(unsigned)(uintptr_t)other.mram,other.mram?other.bytes:0)))return false;
    return !carrier_overlap((unsigned)(uintptr_t)c.backing,c.backing?c.bytes:0,
        (unsigned)(uintptr_t)c.mram,c.mram?c.bytes:0);
}
}
extern "C" int re4dc_cabin_carrier_prepare(void* unit,const char* name,unsigned bytes,unsigned logical){
    const int i=carrier_index(name);if(i<0)return 0;
    auto& c=carriers[i];
    if(carrier_fault || c.state || !unit || bytes!=carrier_sizes[i] || !logical || (logical&31) ||
       logical+bytes<logical || !re4dc_cabin_source_range_available(unit,logical,bytes) || carrier_epoch==0x7fffffffu)return -1;
    for(const auto& other:carriers)if(other.state && (other.unit==unit ||
       carrier_overlap(logical,bytes,other.logical,other.bytes)))return -1;
    c=CabinCarrier{};c.unit=unit;c.generation=++carrier_epoch;c.logical=logical;c.bytes=bytes;c.heap=c.backing_heap=-1;c.state=CarrierPreparing;
    // The lease exists before the certified reader can yield to another task.
    if(!carrier_current(c) || !run(name,bytes,nullptr,carrier_certificates[i]) || !carrier_current(c))return carrier_fail(&c);
    c.state=CarrierReference;return 1;
}
extern "C" int re4dc_cabin_carrier_clear(void* unit){
    for(auto& c:carriers)if(c.state && c.unit==unit){
        if(carrier_fault || !carrier_retirement_ready(c))return 0;
        c.releasing=true;
        // Both exact allocations were checked above. These synchronous frees
        // cannot yield between validation and the source ownership update.
        if(!re4dc_cabin_source_unit_release(c.unit,c.bytes)){
            c.releasing=false;return 0;
        }
        if(c.backing && !re4dc_cabin_source_free(c.backing,c.bytes,c.backing_heap)){
            c.releasing=false;return 0;
        }
        c=CabinCarrier{};
    }
    return 1;
}
extern "C" int re4dc_cabin_carriers_reset(){
    if(carrier_fault || carrier_event_readers || carrier_dma_scope)return 0;
    // Preflight the entire set; no partial identity erase on a refused reset.
    for(const auto& c:carriers)if(c.state && !carrier_retirement_ready(c))return 0;
    for(auto& c:carriers)if(c.state && !re4dc_cabin_source_unit_clear(c.unit))return 0;
    return 1;
}
extern "C" int re4dc_cabin_carrier_rebase(void* unit,unsigned address){
    for(auto& c:carriers)if(c.state && c.unit==unit){
        if(address==c.logical)return 1;
        if(!address || (address&31) || address+c.bytes<address || !carrier_current(c) ||
           !carrier_can_retire(c) || (c.state!=CarrierReference && c.state!=CarrierReady) || c.mram ||
           !re4dc_cabin_source_range_available(unit,address,c.bytes))return -1;
        for(const auto& other:carriers)if(&other!=&c && other.state &&
           carrier_overlap(address,c.bytes,other.logical,other.bytes))return -1;
        c.logical=address;return 1;
    }
    return 0;
}
extern "C" int re4dc_cabin_carrier_install(void* unit,void* destination){
    for(auto& c:carriers)if(c.state && c.unit==unit){
        if(carrier_fault || !carrier_current(c) || !destination || c.mram || c.event || c.readers ||
           carrier_event_readers || (c.state!=CarrierReference && c.state!=CarrierReady) || c.role==1)return -1;
        int heap=-1;
        if(!re4dc_cabin_source_allocation(destination,c.bytes,&heap))return -1;
        c.mram=destination;c.heap=heap;c.state=CarrierPreparing;
        bool ok;
        if(c.backing){std::memcpy(destination,c.backing,c.bytes);ok=true;}
        else ok=run(carrier_names[carrier_number(c)],c.bytes,destination,carrier_certificates[carrier_number(c)]);
        if(!ok || !carrier_current(c) || !carrier_mram_current(c)){
            // The failed destination has never been published and the certified
            // read has returned. Relinquish only that destination so the source
            // can free its own allocation; an existing backing stays owned.
            c.mram=nullptr;c.heap=-1;return carrier_fail(&c);
        }
        c.state=CarrierMram;return 1;
    }
    return 0;
}
extern "C" unsigned re4dc_cabin_carrier_reserved(const void* unit){
    for(const auto& c:carriers)if(c.state && c.unit==unit)return c.logical;
    return 0;
}
#if defined(RE4DC_EVD_ARAM_ALLOC_RETRY) && RE4DC_EVD_ARAM_ALLOC_RETRY
extern "C" unsigned re4dc_cabin_carrier_preload_epoch(const void* unit,unsigned logical,unsigned bytes){
    if(!unit || !logical || !bytes || carrier_fault || carrier_event_readers || carrier_dma_scope)return 0;
    const CabinCarrier* found=nullptr;
    for(const auto& c:carriers)if(c.state && c.unit==unit){
        // Only a prepared immutable source, with no installed allocation,
        // module role or accepted reader, can issue this read-only receipt.
        if(found || c.logical!=logical || c.bytes!=bytes || !c.generation || c.generation>0x7fffffffu || c.generation>carrier_epoch ||
           c.state!=CarrierReference || c.role || c.phase || c.backing || c.mram || c.module ||
           c.event || c.readers || c.releasing || c.heap!=-1 || c.backing_heap!=-1 || !carrier_current(c) ||
           !re4dc_cabin_source_unit_retire_ready(c.unit,carrier_number(c),logical,bytes,nullptr))return 0;
        for(const auto& d:carrier_dma)if(d.state && d.owner==carrier_number(c))return 0;
        found=&c;
    }
    return found?found->generation:0;
}
#endif
extern "C" int re4dc_cabin_carrier_unit_available(const void* unit){
    if(carrier_fault)return 0;
    for(const auto& c:carriers)if(c.state && c.unit==unit)return 0;
    return 1;
}
extern "C" int re4dc_cabin_carrier_mram_move(const void* unit,const void* destination){
    for(const auto& c:carriers)if(c.state && c.unit==unit)
        return !carrier_fault && carrier_current(c) && destination==c.mram ? 1 : -1;
    return 0;
}
extern "C" int re4dc_cabin_carrier_park(void* unit,unsigned* logical){
    for(auto& c:carriers)if(c.state && c.unit==unit){
        const unsigned target=logical && *logical ? *logical : c.logical;
        if(carrier_fault || carrier_number(c)>=2 || !logical || !carrier_current(c) ||
           c.state!=CarrierMram || !carrier_mram_current(c) || c.module || c.event ||
           c.readers || carrier_event_readers || !target || (target&31) ||
           target+c.bytes<target || !re4dc_cabin_source_range_available(unit,target,c.bytes))return -1;
        c.state=CarrierPreparing;
        if(!c.backing){c.backing=re4dc_cabin_source_alloc(c.bytes,c.heap);c.backing_heap=c.heap;}
        if(!c.backing || !carrier_current(c) || !carrier_mram_current(c))return carrier_fail(&c);
        std::memcpy(c.backing,c.mram,c.bytes);
        // The source frees its allocation only after this exact copy completes.
        c.logical=target;c.mram=nullptr;c.heap=-1;c.role=2;c.state=CarrierReady;*logical=target;return 1;
    }
    return 0;
}
extern "C" int re4dc_cabin_carrier_before_free(const void* p){
    if(!p)return 1;
    for(const auto& d:carrier_dma)if(d.state && d.mram==p)return 0;
    for(const auto& c:carriers)if(c.state && (p==c.backing || p==c.mram)){
        if(!(c.releasing && !c.readers && !c.event && !carrier_event_readers))return 0;
    }
    return 1;
}
extern "C" int re4dc_cabin_carriers_before_heap(const void* start,unsigned bytes){
    const unsigned address=(unsigned)(uintptr_t)start;
    if(carrier_fault || address+bytes<address)return 0;
    for(const auto& d:carrier_dma)if(d.state && d.mram &&
       carrier_overlap(address,bytes,(unsigned)(uintptr_t)d.mram,d.bytes))return 0;
    for(const auto& c:carriers)if(c.state &&
       (carrier_overlap(address,bytes,(unsigned)(uintptr_t)c.backing,c.backing?c.bytes:0) ||
        carrier_overlap(address,bytes,(unsigned)(uintptr_t)c.mram,c.mram?c.bytes:0)) && !carrier_retirement_ready(c))return 0;
    return 1;
}
extern "C" int re4dc_cabin_carriers_suspendable(const void* start,unsigned bytes){
    if(!re4dc_cabin_carriers_before_heap(start,bytes))return 0;
    const unsigned address=(unsigned)(uintptr_t)start;
    for(const auto& c:carriers)if(c.state &&
       (carrier_overlap(address,bytes,(unsigned)(uintptr_t)c.backing,c.backing?c.bytes:0) ||
        carrier_overlap(address,bytes,(unsigned)(uintptr_t)c.mram,c.mram?c.bytes:0)))return 0;
    return 1;
}
extern "C" int re4dc_cabin_carriers_retire_heap(const void* start,unsigned bytes){
    // The caller has checked every affected range and closed media before this
    // commit. Revalidate the whole local set before any non-yielding source free.
    if(!re4dc_cabin_carriers_before_heap(start,bytes))return 0;
    const unsigned address=(unsigned)(uintptr_t)start;
    for(auto& c:carriers)if(c.state &&
       (carrier_overlap(address,bytes,(unsigned)(uintptr_t)c.backing,c.backing?c.bytes:0) ||
        carrier_overlap(address,bytes,(unsigned)(uintptr_t)c.mram,c.mram?c.bytes:0)) &&
       !re4dc_cabin_source_unit_clear(c.unit))return 0;
    return 1;
}
extern "C" void re4dc_cabin_carriers_before_events(){
    if(carrier_event_readers==~0u){carrier_fault=true;return;}++carrier_event_readers;
}
extern "C" void re4dc_cabin_carriers_after_events(){
    if(!carrier_event_readers){carrier_fault=true;return;}--carrier_event_readers;
}
extern "C" int re4dc_cabin_carrier_event(const void* event,const void* data,const char* key){
    const char* canonical=key && !std::strncmp(key,"event/",6)?key+6:key;
    const int i=carrier_index(canonical);if(i<0)return 1;
    auto& c=carriers[i];
    if(!event || carrier_fault || !carrier_current(c) || data!=c.mram || !carrier_mram_current(c) || c.event ||
       !((c.state==CarrierReady && c.role==1) || c.state==CarrierMram))return 0;
    c.event=event;return 1;
}
extern "C" void re4dc_cabin_carrier_event_deleted(const void* event){
    for(auto& c:carriers)if(c.state && c.event==event)c.event=nullptr;
}
extern "C" unsigned re4dc_cabin_carrier_reverse_token(const void* unit,const void* module,const void* mram,unsigned bytes,int* heap){
    if(!heap || !module || !mram || carrier_fault || carrier_event_readers || carrier_dma_scope)return 0;
    for(const auto& c:carriers)if(c.unit==unit && c.state==CarrierReady && c.role==1 &&
       c.module==module && c.mram==mram && c.bytes==bytes && !c.readers && !c.event && !c.releasing &&
       carrier_current(c) && carrier_mram_current(c) && carrier_backing_current(c)){
        *heap=c.heap;return c.generation;
    }
    return 0;
}
extern "C" int re4dc_cabin_carrier_reverse_complete(const void* unit,const void* module,const void* mram,unsigned bytes,int heap,unsigned token){
    if(!token || !module || !mram || carrier_fault || carrier_event_readers || carrier_dma_scope)return 0;
    int current_heap=-1;
    if(re4dc_cabin_source_module(mram,bytes)!=module ||
       !re4dc_cabin_source_allocation(mram,bytes,&current_heap) || current_heap!=heap)return 0;
    for(const auto& c:carriers)if(c.unit==unit && c.generation==token && c.bytes==bytes && c.heap==heap &&
       c.state==CarrierReady && c.role==2 && !c.mram && !c.module && !c.readers && !c.event && !c.releasing &&
       carrier_current(c) && carrier_backing_current(c))return 1;
    return 0;
}
extern "C" int re4dc_cabin_carrier_swap_begin(void* mram,unsigned logical,unsigned bytes){
    CabinCarrier* cp=carrier_range(logical,bytes);
    if(carrier_fault)return -1;
    if(!cp)return 0;
    auto& c=*cp;
    if(carrier_number(c)>=2 || !carrier_current(c) || logical!=c.logical || bytes!=c.bytes ||
       c.readers || c.event || carrier_event_readers || carrier_dma_scope ||
       (c.state!=CarrierReference && c.state!=CarrierReady) || !mram ||
       (c.mram && c.mram!=mram))return -1;
    int heap=-1;const void* module=re4dc_cabin_source_module(mram,bytes);
    if(!module || !re4dc_cabin_source_allocation(mram,bytes,&heap))return -1;
    if(c.module && (c.module!=module || c.heap!=heap))return -1;
    c.mram=mram;c.module=module;c.heap=heap;c.state=CarrierPreparing;
    if(!c.backing){
        c.backing=re4dc_cabin_source_alloc(bytes,heap);c.backing_heap=heap;
        if(!c.backing || !run(carrier_names[carrier_number(c)],bytes,c.backing,carrier_certificates[carrier_number(c)]))return carrier_fail(&c);
    }
    if(!carrier_current(c) || !carrier_mram_current(c))return carrier_fail(&c);
    c.state=CarrierSwap;c.phase=0;return (int)c.generation;
}
extern "C" int re4dc_cabin_carrier_swap_scope(unsigned token,unsigned type){
    auto* c=carrier_token(token);
    if(carrier_dma_scope || !c || c->state!=CarrierSwap || !carrier_current(*c) ||
       !carrier_mram_current(*c) || c->readers || type>1 || c->phase!=(type==1?0u:1u))return 0;
    carrier_dma_scope=token;return 1;
}
extern "C" int re4dc_cabin_carrier_dma_admit(const void* request,unsigned type,unsigned src,unsigned dst,unsigned bytes){
    const unsigned scope=carrier_dma_scope;carrier_dma_scope=0;
    const unsigned address=type==0?dst:src;
    auto* c=carrier_range(address,bytes);
    if(carrier_fault)return -1;
    if(!c)return scope?-1:0;
    if(!request || type>1 || !carrier_current(*c) || !carrier_inside(address,bytes,c->logical,c->bytes) ||
       !c->backing || c->readers==~0u || c->state==CarrierFailed)return -1;
    if(c->state==CarrierSwap){
        if(scope!=c->generation || bytes!=c->bytes || address!=c->logical ||
           c->phase!=(type==1?0u:1u) || !carrier_mram_current(*c) ||
           !re4dc_cabin_source_swap_buffer(type,type==0?src:dst,bytes))return -1;
    }else if(scope || c->state!=CarrierReady || c->role==1 || c->event || carrier_event_readers)return -1;
    int heap=-1;void* mram=nullptr;
    if(c->state!=CarrierSwap){
        mram=(void*)(uintptr_t)(type==0?src:dst);
        if(!re4dc_cabin_source_allocation(mram,bytes,&heap))return -1;
    }
    if(carrier_dma_epoch==0x7fffffffu)return -1;
    for(const auto& d:carrier_dma)if(d.state && d.request==request)return -1;
    for(auto& d:carrier_dma)if(!d.state){
        d={request,c->generation,carrier_number(*c),type,src,dst,bytes,1,++carrier_dma_epoch,mram,heap};++c->readers;return 1;
    }
    return -1;
}
extern "C" int re4dc_cabin_carrier_dma_owned(const void* request){
    for(const auto& d:carrier_dma)if(d.state && d.request==request)return 1;return 0;
}
extern "C" int re4dc_cabin_carrier_dma_copy(const void* request,unsigned type,unsigned src,unsigned dst,unsigned bytes){
    for(auto& d:carrier_dma)if(d.state && d.request==request){
        auto& c=carriers[d.owner];
        if(carrier_fault || d.state!=1 || d.generation!=c.generation || d.type!=type || d.src!=src || d.dst!=dst || d.bytes!=bytes ||
           !carrier_current(c) || !c.backing || (c.state!=CarrierSwap && c.state!=CarrierReady))return carrier_fail(&c);
        int heap=-1;
        if(d.mram && (!re4dc_cabin_source_allocation(d.mram,bytes,&heap) || heap!=d.heap))return carrier_fail(&c);
        const unsigned address=type==0?dst:src;
        if(!carrier_inside(address,bytes,c.logical,c.bytes))return carrier_fail(&c);
        auto* backing=static_cast<unsigned char*>(c.backing)+(address-c.logical);
        if(type==0)std::memcpy(backing,(const void*)(uintptr_t)src,bytes);
        else std::memcpy((void*)(uintptr_t)dst,backing,bytes);
        if(c.state==CarrierSwap)++c.phase;
        d.state=2;return (int)d.token;
    }
    return 0;
}
extern "C" const void* re4dc_cabin_carrier_dma_callback(unsigned token){
    for(auto& d:carrier_dma)if(d.state && d.token==token){
        auto& c=carriers[d.owner];
        if(carrier_fault || d.state!=2 || c.generation!=d.generation || !carrier_current(c)){carrier_fail(&c);return nullptr;}
        d.state=3;return d.request;
    }
    // This entry point is used only by the owned transfer, never generic ARQ.
    // Tokens are never reused even when a source request slot is recycled.
    carrier_fault=true;return nullptr;
}
extern "C" int re4dc_cabin_carrier_dma_release(const void* request,int cancelled){
    for(auto& d:carrier_dma)if(d.state && d.request==request){
        auto& c=carriers[d.owner];
        if(c.generation!=d.generation || !c.readers || (cancelled?d.state!=1:d.state!=3))return carrier_fail(&c);
        --c.readers;d=CabinCarrierDma{};return 1;
    }
    return 0;
}
extern "C" int re4dc_cabin_carrier_swap_end(unsigned token,int success,const void* saved){
    auto* c=carrier_token(token);carrier_dma_scope=0;
    if(!success){
        // An owned software copy can have returned failure after marking the
        // owner failed. Preserve the current MRAM half even with that retained
        // request lease: no hardware ARQ was submitted for the owned request.
        if(c && c->phase==1 && carrier_current(*c) && carrier_mram_current(*c) &&
           carrier_backing_current(*c) && re4dc_cabin_source_swap_buffer(0,(unsigned)(uintptr_t)saved,c->bytes))
            std::memcpy(c->mram,saved,c->bytes);
        return carrier_fail(c);
    }
    if(!c || c->state!=CarrierSwap || c->readers || !carrier_current(*c) || !carrier_mram_current(*c))return carrier_fail(c);
    if(c->phase!=2)return carrier_fail(c);
    c->role=c->role==1?2:1;c->phase=0;c->state=CarrierReady;
    if(c->role==2){c->mram=nullptr;c->module=nullptr;}
    return 1;
}
// CABIN_CARRIER_OWNER_END
#endif
