#include "include/gc_asset_motion_source.h"
// Narrow source-motion key residency adapter. Original FCV/SEQ evaluation stays
// in motion.cpp; original archive and whole-clip paths remain selectable.
#include "native_motion.h"
#include "re4dc_platform.h"
#include "../../room/room_storage.hpp"
#ifndef RE4DC_MOTION_RETIRE_PREFLIGHT
#define RE4DC_MOTION_RETIRE_PREFLIGHT 0
#endif
#if RE4DC_MOTION_RETIRE_PREFLIGHT != 0 && RE4DC_MOTION_RETIRE_PREFLIGHT != 1
#error MOTION_RETIRE_PREFLIGHT must be 0 or 1
#endif
#ifndef RE4DC_IO_PROBE
#define RE4DC_IO_PROBE 0
#endif
#if RE4DC_IO_PROBE
// Total time spent in motion-key misses (read + check + relocate); room-entry telemetry.
extern "C" { unsigned long long re4dc_motion_wait_total_us; }
#endif
#ifndef RE4DC_MOTION_RESUME
#define RE4DC_MOTION_RESUME 0
#endif
#if RE4DC_MOTION_RESUME
#include "motion_resume_journal.hpp"
extern "C" unsigned re4dc_fixture_source_frame();
extern "C" unsigned re4dc_heap_largest_current(unsigned*) __attribute__((weak));
#endif
#ifndef RE4DC_MOTION_RESERVE_SPILL
#define RE4DC_MOTION_RESERVE_SPILL 0
#endif
#ifndef RE4DC_MOTION_COLD_POOL
#define RE4DC_MOTION_COLD_POOL 0
#endif
#if RE4DC_MOTION_RESERVE_SPILL || RE4DC_MOTION_COLD_POOL || RE4DC_MOTION_RESUME
extern "C" int re4dc_static_heap_free();   // ui_bridge.cpp: heap 4 free bytes (-1 when inactive)
#endif
#ifndef RE4DC_MOTION_COLD_POOL_CASTLE
#define RE4DC_MOTION_COLD_POOL_CASTLE 0
#endif
#if RE4DC_MOTION_COLD_POOL_CASTLE
// MOTION_COLD_POOL_CASTLE=<bytes> (game30.mk, lane ch4found16): the cold pool's heap 4 margin in the castle rooms
// (r2xx) instead of MOTION_COLD_POOL's.
extern "C" unsigned re4dc_room_id_now();   // ui_bridge.cpp: pG->room_id (0x226), 0 before the game starts
static inline unsigned cold_pool_margin() {
    return (re4dc_room_id_now()>>8)==2?unsigned(RE4DC_MOTION_COLD_POOL_CASTLE):unsigned(RE4DC_MOTION_COLD_POOL);
}
#else
#define cold_pool_margin() unsigned(RE4DC_MOTION_COLD_POOL)
#endif
#include <kos.h>
#include <kos/net.h>
#include <kos/mutex.h>
#include <cstdio>
#include <cstring>
#include <cstdint>
#ifndef RE4DC_MOTION_CAPACITY
#define RE4DC_MOTION_CAPACITY 0
#endif
#if RE4DC_MOTION_CAPACITY
extern "C" void* re4dc_motion_alloc_optional(unsigned);
extern "C" int re4dc_motion_heap_handle();
extern "C" void* re4dc_motion_source_try_alloc(int,unsigned);
#endif
#ifndef RE4DC_MOTION_LEASE_LEAN
#define RE4DC_MOTION_LEASE_LEAN 0
#endif
// Explicit resource policy, separate from source evaluation and archive lifetime.
// Zero keeps the qualified hot-resident policy and contributes no new code.
#ifndef RE4DC_MOTION_PRESSURE_BYTES
#define RE4DC_MOTION_PRESSURE_BYTES 0
#endif
#if RE4DC_MOTION_PRESSURE_BYTES
static_assert(RE4DC_MOTION_PRESSURE_BYTES >= 65536 &&
              RE4DC_MOTION_PRESSURE_BYTES <= 1048576 &&
              RE4DC_MOTION_PRESSURE_BYTES % 32 == 0,
              "motion pressure budget must be 64 KiB..1 MiB, aligned to 32");
#endif
#ifndef RE4DC_MOTION_INDEX
#define RE4DC_MOTION_INDEX 0
#endif
// MOTION_OOM_EVICT=1: a key miss whose heap allocation fails (the room heap is full or fragmented,
// e.g. r100's after-ambush state) evicts least-recently-used unpinned keys from every binding and
// retries, instead of halting. Keys reload byte-identically (crc + fnv checked), so only I/O time
// changes. Never while the sub screen holds the suspended heaps.
#ifndef RE4DC_MOTION_OOM_EVICT
#define RE4DC_MOTION_OOM_EVICT 0
#endif

#ifndef RE4DC_MOTION_RESERVE
#define RE4DC_MOTION_RESERVE 0
#endif
#ifndef RE4DC_MOTION_BOUNDED_R11F
#define RE4DC_MOTION_BOUNDED_R11F 0
#endif
#ifndef RE4DC_MOTION_PRESSURE_BACKING
#define RE4DC_MOTION_PRESSURE_BACKING 0
#endif
#if defined(RE4DC_MOTION_RESERVE_PACK) && RE4DC_MOTION_RESERVE_PACK
extern "C" unsigned re4dc_heap_largest_current(unsigned*) __attribute__((weak));
#endif
#ifndef RE4DC_MOTION_RESERVE_PACK
#define RE4DC_MOTION_RESERVE_PACK 0
#endif
#if RE4DC_MOTION_CAPACITY && (!RE4DC_MOTION_RESERVE_PACK || !RE4DC_MOTION_PRESSURE_BACKING)
#error "motion capacity needs packed reserve and pressure backing"
#endif
#if RE4DC_MOTION_RESERVE_PACK && !RE4DC_MOTION_PRESSURE_BACKING
#error "motion reserve packing needs backing accounting"
#endif
#if RE4DC_MOTION_PRESSURE_BACKING && (!RE4DC_MOTION_RESERVE || !RE4DC_MOTION_PRESSURE_BYTES)
#error "motion backing accounting needs reserve and pressure budget"
#endif
#if RE4DC_MOTION_RESUME && (!RE4DC_MOTION_PRESSURE_BACKING || !RE4DC_MOVIE_HEAP_EVICT)
#error "motion resume needs backing accounting and movie eviction"
#endif
#if RE4DC_MOTION_BOUNDED_R11F
#if !RE4DC_MOTION_RESERVE || RE4DC_MOTION_USAGE_LOG
#error "bounded r11f motion needs reserve=1, usage_log=0"
#endif
#if RE4DC_MOTION_PRESSURE_BYTES != 262144
#error "bounded r11f motion is qualified with the existing 262144-byte pressure cap"
#endif
#endif
#ifndef RE4DC_MOTION_USAGE_LOG
#define RE4DC_MOTION_USAGE_LOG 0
#endif

namespace {
constexpr unsigned kArchives=4, kEntries=255, kClipLimit=32768;
struct Slot { unsigned char* data; unsigned pins; std::uint64_t used; };
struct Binding {
    unsigned char* archive; unsigned bytes;
    const unsigned char* records; unsigned count;
    Slot* slots; unsigned budget, hot_bytes, resident;
#if RE4DC_MOTION_CAPACITY
    unsigned char overflow[32]; // only new reclaimable v2 payloads, never slabs/hot/v3
    int overflow_heap;
#endif
#if RE4DC_MOTION_BOUNDED_R11F
    bool bounded; // static binding marker; checked before any suspended archive/slot access
#endif
#if RE4DC_MOTION_RESERVE_PACK
    bool joined; // existing bounded flag stays in place; slab[1] is a non-owning half
#endif
#if RE4DC_MOTION_RESERVE
    // MOTION_RESERVE=1: the cold part of the budget (two clips of the largest cold size) is
    // allocated at bind, so a later miss never allocates from a full heap 4 (the r100 ambush:
    // "motion key allocation" would trap). Cold loads take a free slab, else evict the LRU cold clip.
    unsigned char* slab[2]; unsigned slab_bytes;
#endif
#if RE4DC_MOTION_USAGE_LOG
    unsigned char* seen;   // first acquire per entry since bind (hot-set audit)
#endif
};
struct Owner { const void* thread; unsigned leases; };
Binding bindings[kArchives]{};
#if RE4DC_MOTION_RESUME
re4dc::motion::ResumeJournal resume_journal;
re4dc::motion::ResumeTickets resume_pending;
bool resume_pending_live;
#endif
#if RE4DC_SUBSCREEN
// Sub screen open (sscrn_bridge.cpp): the game's heaps 2/3/4 are suspended and their cells in
// the swapped area hold sub screen data, so nothing already resident may be evicted (freed
// into a suspended heap). Misses outside heap4 are rejected below. New bounded bindings
// are skipped before their archive range or borrowed records/slots are inspected.
bool hold;
#endif
Owner owners[32]{};
Re4dcMotionStats stats{};
#if defined(RE4DC_MOTION_STATS_LOG) && RE4DC_MOTION_STATS_LOG
// MOTION_STATS_LOG (Makefile): keys used per binding (bits by entry), for the window, the 5-window block and since bind.
unsigned char ws_win[kArchives][32], ws_blk[kArchives][32], ws_all[kArchives][32];
unsigned ws_windows;
inline void ws_touch(const Binding& b,unsigned i) {
    const unsigned k=unsigned(&b-bindings);if(k>=kArchives || i>=256)return;
    const unsigned char m=(unsigned char)(1u<<(i&7));ws_win[k][i>>3]|=m;ws_blk[k][i>>3]|=m;ws_all[k][i>>3]|=m;
}
#endif
std::uint64_t stamp;
mutex_t lock=MUTEX_INITIALIZER;
#if RE4DC_MOTION_CAPACITY
const void* lock_owner;
unsigned required_waiters;
bool capacity_retiring;
#if RE4DC_MOTION_RESUME
const void* capacity_movie_owner;
#endif
bool overflow_key(const Binding& b,unsigned i) { return (b.overflow[i>>3] & (1u<<(i&7)))!=0; }
void overflow_mark(Binding& b,unsigned i,bool on) {
    const unsigned char bit=static_cast<unsigned char>(1u<<(i&7));
    if(on)b.overflow[i>>3]|=bit;else b.overflow[i>>3]&=static_cast<unsigned char>(~bit);
}
void locked_enter() { int old=irq_disable();lock_owner=thd_current;irq_restore(old); }
void locked_leave() { int old=irq_disable();lock_owner=nullptr;irq_restore(old); }
#endif
unsigned word(const unsigned char* p) { unsigned n;std::memcpy(&n,p,4);return n; }
unsigned aligned(unsigned n) { return (n+31)&~31U; }
#if RE4DC_MOTION_BOUNDED_R11F
#include "native_motion_r11f_profiles.inc"
#endif
#ifndef RE4DC_MOTION_FAST_READ
#define RE4DC_MOTION_FAST_READ 0
#endif
#if RE4DC_MOTION_FAST_READ
// MOTION_FAST_READ=1: read a key (<= 32 KiB) straight into its 32-byte-aligned residency
// block. KOS fs_iso9660 reads a misaligned destination (storage::read_file's bounce copy
// path) one sector per GD command: ~98 ms per key in Flycast, 75 keys per r100 entry. An
// aligned destination at offset 0 takes one stream command for the 32-byte multiple; the
// <32-byte tail is then read through the block cache after a seek moves the fd off the
// stream (KOS's own sub-32-byte stream request is the one that never returns, R4_5A).
// Returns bytes read, -1 on open/size failure, -2 when dst is not 32-byte aligned.
int fast_key_read(const char* path, unsigned char* dst, unsigned size) {
    if(reinterpret_cast<std::uintptr_t>(dst)&31U)return -2;
    const file_t f=fs_open(path,O_RDONLY);
    if(f==FILEHND_INVALID)return -1;
    if(fs_total(f)!=ssize_t(size)) { fs_close(f);return -1; }
    const unsigned body=size&~31U;unsigned got=0;
    while(got<body) { const ssize_t n=fs_read(f,dst+got,body-got);if(n<=0)break;got+=unsigned(n); }
    if(got==body && got<size) {
        if(got) { fs_seek(f,0,SEEK_SET);fs_seek(f,got,SEEK_SET); }   // pointer moves: stream aborted
        alignas(32) unsigned char tail[64];                         // tail+16: misaligned on purpose
        const unsigned start=got;
        while(got<size) { const ssize_t n=fs_read(f,tail+16+(got-start),size-got);if(n<=0)break;got+=unsigned(n); }
        std::memcpy(dst+start,tail+16,got-start);
    }
    fs_close(f);
    return int(got);
}
#endif
unsigned prefix(const unsigned char* p) { unsigned n=p[2];return ((3+3*n+3)&~3U)+4+4*n; }
[[noreturn]] void fail(const char* reason) {
    ++stats.failures;re4dc_log("motion residency failure: %s\n",reason);
    re4dc_missing(reason); __builtin_trap();
}
// Called with IRQ exclusion for ownership, independent of the I/O mutex. The
// native OS cancellation hook drains these scopes before destroying a thread.
#if RE4DC_MOTION_LEASE_LEAN
Owner* owner_add() {
    int old=irq_disable();const void* me=thd_current;
    for(auto& o:owners) if(o.thread==me) { ++o.leases;irq_restore(old);return &o; }
    for(auto& o:owners) if(!o.leases) { o={me,1};irq_restore(old);return &o; }
    irq_restore(old);fail("motion owner capacity");
}
#else
void owner_add() {
    int old=irq_disable();const void* me=thd_current;
    for(auto& o:owners) if(o.thread==me) { ++o.leases;irq_restore(old);return; }
    for(auto& o:owners) if(!o.leases) { o={me,1};irq_restore(old);return; }
    irq_restore(old);fail("motion owner capacity");
}
#endif
void owner_drop() {
    int old=irq_disable();
    for(auto& o:owners) if(o.thread==thd_current && o.leases) {
        if(!--o.leases)o.thread=nullptr;
        irq_restore(old);return;
    }
    irq_restore(old);fail("motion lease owner mismatch");
}
struct Locked {
#if RE4DC_MOTION_LEASE_LEAN
    // This guard's count keeps the static slot occupied across mutex_lock and
    // until its destructor. Retaining a lease need not find that same slot again.
    Owner* owner;
    Locked():owner(owner_add()) { mutex_lock(&lock);
#if RE4DC_MOTION_CAPACITY
        locked_enter();
#endif
    }
    void retain_lease() {
        int old=irq_disable();
        if(owner->thread!=thd_current || !owner->leases) {
            irq_restore(old);fail("motion lease owner mismatch");
        }
#if RE4DC_MOTION_LEASE_LEAN == 2
        Owner* found=nullptr;
        for(auto& o:owners)if(o.thread==thd_current) { found=&o;break; }
        if(found!=owner) { irq_restore(old);fail("motion lease owner shadow mismatch"); }
        static unsigned checked=0;
        const bool report=(++checked & 4095U)==0;
#endif
        ++owner->leases;
        irq_restore(old);
#if RE4DC_MOTION_LEASE_LEAN == 2
        if(report)re4dc_log("MOTION_LEASE_CHECK calls=%u mismatch=0\n",checked);
#endif
    }
#else
    Locked() { owner_add();mutex_lock(&lock);
#if RE4DC_MOTION_CAPACITY
        locked_enter();
#endif
    }
#endif
    ~Locked() {
#if RE4DC_MOTION_CAPACITY
        locked_leave();
#endif
        mutex_unlock(&lock);owner_drop();
    }
};
const unsigned char* record(const Binding& b,unsigned i) { return b.records+20*i; }
#if RE4DC_MOTION_RESERVE_PACK
const unsigned char* reserved_base(const Binding& b,const unsigned char* p) {
    if(!p)return nullptr;
    const auto address=reinterpret_cast<std::uintptr_t>(p);
    for(unsigned i=0;i<(b.joined?1u:2u);++i)if(const auto* slab=b.slab[i]) {
        const auto base=reinterpret_cast<std::uintptr_t>(slab);
        const unsigned span=b.joined?2*b.slab_bytes:b.slab_bytes;
        if(address>=base && address-base<span)return slab;
    }
    return nullptr;
}
bool reserved_data(const Binding& b,const unsigned char* p) {
    return reserved_base(b,p)!=nullptr;
}
#endif
void discard(Binding& b,unsigned i) {
    auto& s=b.slots[i];if(!s.data)return;
    if(s.pins)fail("motion discard pinned");
#if RE4DC_GC_ASSET_MOTION_SOURCE
    re4dc_gcasset::motion_source_external_invalidate(&s);
#endif
    const unsigned bytes=aligned(word(record(b,i)+4));
#if RE4DC_MOTION_RESERVE_PACK
    if(!reserved_data(b,s.data)) // subregions stay with their slab until binding retirement
#elif RE4DC_MOTION_RESERVE
    if(s.data!=b.slab[0] && s.data!=b.slab[1])   // a slab stays with the binding
#endif
    re4dc_motion_free(s.data);
#if RE4DC_MOTION_CAPACITY
    overflow_mark(b,i,false);
#endif
    s={};b.resident-=bytes;stats.resident_bytes-=bytes;
}
#if RE4DC_MOTION_RESERVE
bool slab_busy(const Binding& b,const unsigned char* p) {
    for(unsigned j=0;j<b.count;++j)if(b.slots[j].data==p)return true;
    return false;
}
#if RE4DC_MOTION_RESERVE_PACK
// First-fit gaps, derived from the existing slot table. Never move live/cached
// payloads: a leased relocated FCV table keeps exactly the same address. V2
// prefers one allocation of the unchanged two-slab payload; its old two-cell
// fallback remains packable separately. Strict v3 keeps two whole-clip cells.
unsigned char* reserve_fit(const Binding& b,unsigned bytes) {
#if RE4DC_MOTION_BOUNDED_R11F
    if(b.bounded) {
        for(auto* p:b.slab)if(!slab_busy(b,p))return p;
        return nullptr;
    }
#endif
    if(bytes>b.slab_bytes)return nullptr;
    for(unsigned i=0;i<(b.joined?1u:2u);++i)if(auto* slab=b.slab[i]) {
        const unsigned span=b.joined?2*b.slab_bytes:b.slab_bytes;
        const auto base=reinterpret_cast<std::uintptr_t>(slab),end=base+span;
        auto candidate=base;
        while(candidate<=end-bytes) {
            auto next=candidate;
            for(unsigned j=0;j<b.count;++j)if(b.slots[j].data) {
                const auto p=reinterpret_cast<std::uintptr_t>(b.slots[j].data);
                if(p<base || p>=end)continue;
                const auto finish=p+aligned(word(record(b,j)+4));
                if(candidate<finish && p<candidate+bytes && finish>next)next=finish;
            }
            if(next==candidate)return reinterpret_cast<unsigned char*>(candidate);
            candidate=next; // strict progress past at least one occupied interval
        }
    }
    return nullptr;
}
// Same payload bound, with a single owning base when the raw SDK cell can
// fit payload + MotionAllocation32 + MAD32 + SDKcell32. An absent query or
// fragmented heap takes the old two-allocation path without a failed large
// required allocation. A race/allocator refusal also falls back safely.
bool reserve_allocate(Binding& b,unsigned largest) {
    b.slab_bytes=aligned(largest);
    bool v2=true;
#if RE4DC_MOTION_BOUNDED_R11F
    v2=!b.bounded;
#endif
    unsigned free_bytes=0;
    const unsigned whole=2*b.slab_bytes;
    if(v2 && re4dc_heap_largest_current &&
       re4dc_heap_largest_current(&free_bytes)>=whole+96 && free_bytes>=whole+96) {
        if(auto* base=static_cast<unsigned char*>(re4dc_motion_alloc(whole))) {
            b.joined=true;b.slab[0]=base;b.slab[1]=base+b.slab_bytes;
            stats.metadata_bytes+=whole;return true;
        }
    }
    for(auto*& p:b.slab) {
        p=static_cast<unsigned char*>(re4dc_motion_alloc(b.slab_bytes));
        if(!p)return false;
        stats.metadata_bytes+=b.slab_bytes;
    }
    return true;
}
#endif
#endif
void release_binding(Binding& b) {
    for(unsigned i=0;i<b.count;++i) if(b.slots[i].pins)fail("motion archive retired while pinned");
#if RE4DC_MOTION_RESUME
    resume_journal.binding_changed(unsigned(&b-bindings));
#endif
    for(unsigned i=0;i<b.count;++i)discard(b,i);
    stats.metadata_bytes-=aligned(b.count*sizeof(Slot));stats.hot_bytes-=b.hot_bytes;
#if RE4DC_MOTION_RESERVE
#if RE4DC_MOTION_RESERVE_PACK
    for(unsigned i=0;i<(b.joined?1u:2u);++i)if(b.slab[i])re4dc_motion_free(b.slab[i]);
    // Charge only successful allocations, including partial fallback failure.
    stats.metadata_bytes-=b.joined?2*b.slab_bytes:((b.slab[0]!=nullptr)+(b.slab[1]!=nullptr))*b.slab_bytes;
#else
    for(auto* p:b.slab)if(p)re4dc_motion_free(p);
#if RE4DC_MOTION_BOUNDED_R11F
    // New profile accounting charges each successful slab allocation separately.
    stats.metadata_bytes-=b.bounded?((b.slab[0]!=nullptr)+(b.slab[1]!=nullptr))*b.slab_bytes:2*b.slab_bytes;
#else
    stats.metadata_bytes-=2*b.slab_bytes;
#endif
#endif
#endif
#if RE4DC_MOTION_USAGE_LOG
    if(b.seen)re4dc_motion_free(b.seen);
#endif
    re4dc_motion_free(b.slots);b={};
#if defined(RE4DC_MOTION_STATS_LOG) && RE4DC_MOTION_STATS_LOG
    {const unsigned k=unsigned(&b-bindings);if(k<kArchives){std::memset(ws_win[k],0,32);std::memset(ws_blk[k],0,32);std::memset(ws_all[k],0,32);}}
#endif
}
#if RE4DC_MOTION_PRESSURE_BYTES
// Called only under Locked, before a miss allocates its payload. Archive and
// proxy identities, slot tables, pins, and source MotionWork stay untouched.
// A hot flag remains a preload hint here, rather than a permanent RAM lease.
// Each iteration removes a positive-sized entry, so at most 4*255 iterations.
#if RE4DC_MOTION_PRESSURE_BACKING
// Reserved slabs are already allocated and charged as binding metadata. Their
// occupied payload is useful residency telemetry, not another heap allocation.
// Keep the existing global heap-key cap; fixed backing and slot tables remain
// bounded separately by successful binding admission. Called only under Locked
// after the suspended-heap hold check below.
#if !RE4DC_MOTION_RESERVE_PACK
bool reserved_data(const Binding& b,const unsigned char* p) {
    return p && (p==b.slab[0] || p==b.slab[1]);
}
#endif
unsigned pressure_heap_bytes() {
    unsigned bytes=0;
    for(const auto& b:bindings)if(b.archive)
        for(unsigned i=0;i<b.count;++i)if(b.slots[i].data && !reserved_data(b,b.slots[i].data))
            bytes+=aligned(word(record(b,i)+4));
    return bytes;
}
#endif
void pressure_room_for(unsigned bytes) {
    if(re4dc_motion_current_heap()!=4)fail("motion pressure outside owning room heap");
#if RE4DC_SUBSCREEN
    if(hold)return; // suspended room cells must never be read/freed by eviction
#endif
    if(bytes>RE4DC_MOTION_PRESSURE_BYTES)fail("motion pressure clip exceeds budget");
#if RE4DC_MOTION_PRESSURE_BACKING
    unsigned resident=pressure_heap_bytes();
    while(resident>RE4DC_MOTION_PRESSURE_BYTES-bytes) {
#else
    while(stats.resident_bytes>RE4DC_MOTION_PRESSURE_BYTES-bytes) {
#endif
#if defined(RE4DC_MOTION_PRESSURE_GROW) && RE4DC_MOTION_PRESSURE_GROW
        // MOTION_PRESSURE_GROW: over the cap, evict only while heap 4 would keep less than the margin after this key.
        if(re4dc_static_heap_free()>=int(bytes+RE4DC_MOTION_PRESSURE_GROW))break;
#endif
        Binding* victim=nullptr;unsigned index=0;
        std::uint64_t oldest=~std::uint64_t(0);
        for(auto& q:bindings) {
            if(!q.archive)continue;
            for(unsigned j=0;j<q.count;++j) {
                const auto& slot=q.slots[j];
#if RE4DC_MOTION_PRESSURE_BACKING
                if(reserved_data(q,slot.data))continue; // discarding a slab key frees no heap
#endif
                if(slot.data && !slot.pins && slot.used<oldest) {
                    victim=&q;index=j;oldest=slot.used;
                }
            }
        }
        if(!victim)fail("motion pressure live leases exceed budget");
#if RE4DC_MOTION_PRESSURE_BACKING
        resident-=aligned(word(record(*victim,index)+4));
#endif
        discard(*victim,index);++stats.evictions;
    }
}
#endif
#if RE4DC_MOTION_OOM_EVICT
unsigned char* oom_evict_alloc(unsigned bytes) {
#if RE4DC_SUBSCREEN
    if(hold)return nullptr;
#endif
    static unsigned events;
    unsigned evicted=0,freed=0;unsigned char* data=nullptr;
    while(!data) {
        Binding* victim=nullptr;unsigned index=0;
        std::uint64_t oldest=~std::uint64_t(0);
        for(auto& q:bindings) {
            if(!q.archive)continue;
            for(unsigned j=0;j<q.count;++j) {
                const auto& slot=q.slots[j];
#if RE4DC_MOTION_RESERVE_PACK
                if(reserved_data(q,slot.data))continue;
#elif RE4DC_MOTION_RESERVE
                if(slot.data==q.slab[0] || slot.data==q.slab[1])continue;   // evicting a slab user frees nothing
#endif
                if(slot.data && !slot.pins && slot.used<oldest) { victim=&q;index=j;oldest=slot.used; }
            }
        }
        if(!victim)break;
        freed+=aligned(word(record(*victim,index)+4));
        discard(*victim,index);++stats.evictions;++evicted;
        data=static_cast<unsigned char*>(re4dc_motion_alloc(bytes));
    }
    if(++events<=16 || (events&255)==0)
        re4dc_log("motion oom evict #%u: need=%u evicted=%u freed=%u resident=%u %s\n",events,bytes,evicted,freed,
                  stats.resident_bytes,data?"ok":"FAILED");
    return data;
}
#endif
#if RE4DC_MOTION_CAPACITY
// Caller owns the motion mutex. Never speculate while a required source request
// is draining us. Reserve pointers and strict v3's two-cell policy never change.
unsigned char* overflow_alloc(Binding& b,unsigned bytes) {
#if RE4DC_SUBSCREEN
    if(hold)return nullptr;
#endif
#if RE4DC_MOTION_BOUNDED_R11F
    if(b.bounded)return nullptr;
#endif
    int old=irq_disable();const bool waiting=required_waiters!=0;irq_restore(old);
    if(waiting || capacity_retiring)return nullptr;
    unsigned pinned=0;
    for(const auto& q:bindings)if(q.archive)for(unsigned j=0;j<q.count;++j) {
        const auto& slot=q.slots[j];
        if(slot.data && slot.pins && !reserved_data(q,slot.data))pinned+=aligned(word(record(q,j)+4));
    }
    // pressure_room_for may reject an all-pinned cap. Optional overflow must
    // fall back to the established reserve path rather than create that failure.
    if(bytes>unsigned(RE4DC_MOTION_PRESSURE_BYTES) || pinned>unsigned(RE4DC_MOTION_PRESSURE_BYTES)-bytes)return nullptr;
    pressure_room_for(bytes);
    auto* data=static_cast<unsigned char*>(re4dc_motion_alloc_optional(bytes));
    if(data)b.overflow_heap=re4dc_motion_heap_handle();
    return data;
}
#endif
#if RE4DC_MOTION_RESUME
unsigned* load(Binding& b,unsigned i,unsigned char* prepared=nullptr) {
#else
unsigned* load(Binding& b,unsigned i) {
#endif
    const auto* e=record(b,i);auto& s=b.slots[i];
#if defined(RE4DC_MOTION_STATS_LOG) && RE4DC_MOTION_STATS_LOG
    ws_touch(b,i);
#endif
    if(s.data) { ++stats.hits;s.used=++stamp; }
    else {
        ++stats.misses;const auto started=timer_us_gettime64();
#if RE4DC_MOTION_CAPACITY
        bool new_overflow=false;
#endif
        const unsigned size=word(e+4),bytes=aligned(size);
#if RE4DC_MOTION_PRESSURE_BYTES
#if !RE4DC_MOTION_PRESSURE_BACKING
        pressure_room_for(bytes);
#endif
#else
#if RE4DC_SUBSCREEN
        while(!hold && b.resident+bytes>b.budget) {
#else
        while(b.resident+bytes>b.budget) {
#endif
            unsigned victim=b.count;std::uint64_t oldest=~std::uint64_t(0);
            for(unsigned j=0;j<b.count;++j) {
                const auto& q=b.slots[j];
                if(q.data && !q.pins && !word(record(b,j)+16) && q.used<oldest) { oldest=q.used;victim=j; }
            }
            if(victim==b.count)fail("motion working set exceeds qualified budget");
            discard(b,victim);++stats.evictions;
        }
#endif
        if(re4dc_motion_current_heap()!=4)fail("motion miss outside owning room heap");
#if RE4DC_MOTION_RESUME
        // Resume preflight already allocated this exact owning-heap payload.
        // Reuse the same read/retry/identity/relocation path without pressure,
        // slab replacement, OOM eviction or a second allocation.
        unsigned char* data=prepared;
        if(!data) {
#else
        unsigned char* data=nullptr;
#endif
#if RE4DC_MOTION_RESERVE
#if RE4DC_SUBSCREEN
        if(!hold && b.slab_bytes && !word(e+16) && bytes<=b.slab_bytes) {
#else
        if(b.slab_bytes && !word(e+16) && bytes<=b.slab_bytes) {
#endif
            for(;;) {
#if RE4DC_MOTION_RESERVE_PACK
                data=reserve_fit(b,bytes);
#else
                for(auto* p:b.slab)if(!slab_busy(b,p)) { data=p;break; }
#endif
                if(data)break;
#if RE4DC_MOTION_CAPACITY
                data=overflow_alloc(b,bytes);
                if(data) { new_overflow=true;break; }
#endif
#if RE4DC_MOTION_RESERVE_SPILL
                // Both slabs busy: cache this key in heap 4 while the source keeps its margin (MOTION_RESERVE_SPILL).
                if(
#if RE4DC_MOTION_BOUNDED_R11F
                    !b.bounded &&
#endif
                    re4dc_static_heap_free()>=int(bytes+RE4DC_MOTION_RESERVE_SPILL)) {
                    static unsigned spills;
                    if(++spills<=4 || (spills&1023)==0)re4dc_log("motion reserve: spill #%u bytes=%u heap4=%d\n",spills,bytes,re4dc_static_heap_free());
                    break;
                }
#endif
#if RE4DC_MOTION_COLD_POOL && RE4DC_MOTION_PRESSURE_BYTES
                // MOTION_COLD_POOL (game30.mk): both slabs busy; this key joins the pressure pool (already evicted down
                // to the cap) while heap 4 keeps the margin; a failed allocation evicts a slab user below, as before.
                if(
#if RE4DC_MOTION_BOUNDED_R11F
                    !b.bounded &&
#endif
                    re4dc_static_heap_free()>=int(bytes+cold_pool_margin())) {
#if RE4DC_MOTION_PRESSURE_BACKING
                    pressure_room_for(bytes); // this path really allocates a heap-backed key
#endif
                    data=static_cast<unsigned char*>(re4dc_motion_alloc(bytes));
                    static unsigned pooled,refused;
                    if(data) {
                        if(++pooled<=4 || (pooled&255)==0)re4dc_log("motion cold pool: use #%u bytes=%u resident=%u heap4=%d\n",pooled,bytes,stats.resident_bytes,re4dc_static_heap_free());
                        break;
                    }
                    if(++refused<=4 || (refused&255)==0)re4dc_log("motion cold pool: allocation failed #%u bytes=%u, slab eviction\n",refused,bytes);
                }
#endif
                unsigned victim=b.count;std::uint64_t oldest=~std::uint64_t(0);
                for(unsigned j=0;j<b.count;++j) {
                    const auto& q=b.slots[j];
#if RE4DC_MOTION_RESERVE_PACK
                    if(reserved_data(b,q.data) && !q.pins && q.used<oldest) { oldest=q.used;victim=j; }
#else
                    if((q.data==b.slab[0] || q.data==b.slab[1]) && !q.pins && q.used<oldest) { oldest=q.used;victim=j; }
#endif
                }
                if(victim==b.count)fail("motion reserve slabs pinned");
                discard(b,victim);++stats.evictions;
            }
            static unsigned uses;
            if(++uses<=4 || (uses&255)==0)
                re4dc_log("motion reserve: use #%u bytes=%u slab=%u free=%s\n",uses,bytes,b.slab_bytes,
#if RE4DC_MOTION_RESERVE_PACK
                          reserve_fit(b,bytes)?"1":"0");
#else
                          (slab_busy(b,b.slab[0]) && slab_busy(b,b.slab[1]))?"0":"1");
#endif
        }
#if RE4DC_MOTION_BOUNDED_R11F
        if(b.bounded && !data)fail("bounded motion requires reserved slab");
#endif
        if(!data)
#endif
        {
#if RE4DC_MOTION_PRESSURE_BACKING
            pressure_room_for(bytes); // a reserved-slab fill never reaches this allocation
#endif
            data=static_cast<unsigned char*>(re4dc_motion_alloc(bytes));
        }
#if RE4DC_MOTION_OOM_EVICT
        if(!data)data=oom_evict_alloc(bytes);
#endif
#if RE4DC_MOTION_RESUME
        }
#endif
        if(!data)fail("motion key allocation");
        re4dc::storage::Arena arena;arena.init(data,bytes);
        char path[64];snprintf(path,sizeof(path),"/cd/dc/mot/%08x-%08x.fcv",word(e+8),word(e+12));
#if RE4DC_MOTION_READ_FAULT_TEST
        static unsigned faults;const bool fault=++faults%unsigned(RE4DC_MOTION_READ_FAULT_TEST)==0;
#endif
#if RE4DC_MOTION_FAST_READ
#if RE4DC_MOTION_READ_FAULT_TEST
        const int fast=fault?0:fast_key_read(path,data,size);
#else
        const int fast=fast_key_read(path,data,size);
#endif
        if(fast>=0 && unsigned(fast)==size) {
            stats.bytes_read+=size;
        } else {
            // Short (the stream request met another GD DMA in flight: "Previous DMA request is in
            // progress") or unaligned: read the whole key again through the storage reader below.
            static unsigned shorts;
            if(fast>=0 && (++shorts<=8 || (shorts&63)==0))
                re4dc_log("motion fast read short #%u: got=%d size=%u, storage read\n",shorts,fast,size);
#endif
        auto result=re4dc::storage::read_file(arena,path);
        while(result.error && !std::strcmp(result.error,"storage reader re-entry") &&
              timer_us_gettime64()-started<5000000) {
            thd_pass();result=re4dc::storage::read_file(arena,path);
        }
#if RE4DC_MOTION_READ_FAULT_TEST
        if(fault)result.size=0;  // test: the first storage read of a faulted key reports short
#endif
        // Issue #25: a GD read error on hardware stopped the game during the intro ("motion key read"). Read the
        // key again into the same block (fresh arena) up to 3 times before giving up. Error path only.
        for(unsigned retry=1;(result.error || result.size!=size) && retry<=3U;++retry) {
            static unsigned retries;
            if(++retries<=16 || (retries&63)==0)
                re4dc_log("motion key read retry %u (#%u): %s error=%s got=%u size=%u\n",retry,retries,path,
                          result.error?result.error:"short",unsigned(result.size),size);
            // Back off 10 / 100 / 500 ms: a GD (GDEMU SD) error can last longer than the 30 ms the three retries
            // used to span. Each retry gets its own 5 s window for a reader held by another thread (a texture or
            // stream read); measured from the load's start, a slow first error left no window, and a busy reader
            // ("storage reader re-entry") then used up all three retries without reading the disc once.
            thd_sleep(retry==1U?10U:retry==2U?100U:500U);
            const auto retry_started=timer_us_gettime64();
            arena.init(data,bytes);
            result=re4dc::storage::read_file(arena,path);
            while(result.error && !std::strcmp(result.error,"storage reader re-entry") &&
                  timer_us_gettime64()-retry_started<5000000) {
                thd_pass();result=re4dc::storage::read_file(arena,path);
            }
        }
        if(result.error || result.size!=size) {
#if RE4DC_MOTION_RESERVE_PACK
            if(!reserved_data(b,data))
#elif RE4DC_MOTION_BOUNDED_R11F
            if(!b.bounded)
#endif
            re4dc_motion_free(data);fail("motion key read"); }
        stats.bytes_read+=result.size;
#if RE4DC_MOTION_FAST_READ
        }
#endif
        unsigned fnv=2166136261U;for(unsigned j=0;j<size;++j)fnv=(fnv^data[j])*16777619U;
        const auto* proxy=b.archive+word(e);const unsigned head=prefix(proxy);
        if(net_crc32le(data,size)!=word(e+8) || fnv!=word(e+12) || std::memcmp(proxy,data,head)) {

#if RE4DC_MOTION_RESERVE_PACK
            if(!reserved_data(b,data))
#elif RE4DC_MOTION_BOUNDED_R11F
            if(!b.bounded)
#endif
            re4dc_motion_free(data);fail("motion identity/header mismatch");
        }
#if RE4DC_GC_ASSET_MOTION_SOURCE
        // The complete read, CRC/FNV and original proxy-prefix checks above
        // succeeded. Compute immutable SHA before ANY offset becomes a pointer.
        // This cold path holds only the existing motion mutex, never SQ/LH/G2.
        // Binding to the catalog waits until acquire returns with a pinned lease.
        re4dc_gcasset::motion_source_external_capture(&s,proxy,head,data,size);
#endif
        auto* table=reinterpret_cast<unsigned*>(data+head-4*data[2]);
        for(unsigned j=0;j<data[2];++j) {
            const unsigned offset=table[j];
            if(offset<head || offset>=size) {
#if RE4DC_GC_ASSET_MOTION_SOURCE
            re4dc_gcasset::motion_source_external_invalidate(&s);
#endif
#if RE4DC_MOTION_RESERVE_PACK
            if(!reserved_data(b,data))
#elif RE4DC_MOTION_BOUNDED_R11F
            if(!b.bounded)
#endif
#if RE4DC_GC_ASSET_MOTION_SOURCE
            { // Keep the original ownership condition attached to this free.
#endif
            re4dc_motion_free(data);
#if RE4DC_GC_ASSET_MOTION_SOURCE
            }
#endif
            fail("motion key offset"); }
            table[j]=static_cast<unsigned>(reinterpret_cast<std::uintptr_t>(data)+offset);
        }
        s.data=data;s.used=++stamp;b.resident+=bytes;stats.resident_bytes+=bytes;
#if RE4DC_MOTION_CAPACITY
        overflow_mark(b,i,new_overflow);
#endif
        if(stats.resident_bytes>stats.peak_cache_bytes)stats.peak_cache_bytes=stats.resident_bytes;
        ++stats.loads;const auto wait=timer_us_gettime64()-started;
#if RE4DC_IO_PROBE
        re4dc_motion_wait_total_us+=wait;
#endif
        if(wait>stats.worst_wait_us)stats.worst_wait_us=wait;
#if RE4DC_MOTION_MISS_LOG
        // MOTION_MISS_LOG=1 (diagnostic, log only): every key miss with its clip and wait (the first 256, then every 16th).
        { static unsigned misses;++misses;
          if(misses<=256 || !(misses&15))
              re4dc_log("motion miss #%u: archive=%u entry=%u bytes=%u wait_us=%u slab=%d evictions=%u\n",misses,b.bytes,i,size,
                        unsigned(wait),
#if RE4DC_MOTION_RESERVE
#if RE4DC_MOTION_RESERVE_PACK
                        int(reserved_data(b,data)),
#else
                        int(data==b.slab[0] || data==b.slab[1]),
#endif
#else
                        0,
#endif
                        unsigned(stats.evictions)); }
#endif
    }
    return reinterpret_cast<unsigned*>(s.data+prefix(s.data)-4*s.data[2]);
}
}
#if RE4DC_MOTION_CAPACITY
namespace {
// Keep cancellation draining across mutex contention and every pin wait, not
// merely while Locked is alive. No allocation, I/O or logging in this scope.
struct RequiredScope {
    RequiredScope() { owner_add();int old=irq_disable();++required_waiters;irq_restore(old); }
    ~RequiredScope() { int old=irq_disable();--required_waiters;irq_restore(old);owner_drop(); }
};
bool can_wait_required() {
    // KOS returns the complete prior SR. A partial IMASK, blocked exceptions
    // (BL), or exception register bank (RB) is still a protected caller context.
    // Restore that exact state; never enable it just to wait for cache readers.
    constexpr unsigned protected_sr=0x300000f0U;
    int old=irq_disable();bool allowed=thd_current && !irq_inside_int() && !(unsigned(old)&protected_sr) && lock_owner!=thd_current;
    for(const auto& o:owners)if(o.thread==thd_current && o.leases)allowed=false;
    irq_restore(old);return allowed;
}
// Required source memory may reclaim only candidate overflow. Existing hot
// residency, slab backing and movie-victim tickets keep their original policy.
Binding* overflow_victim(int heap,unsigned* index,bool* pinned) {
    Binding* victim=nullptr;std::uint64_t oldest=~std::uint64_t(0);*pinned=false;
    for(auto& b:bindings)if(b.archive && b.overflow_heap==heap)for(unsigned i=0;i<b.count;++i)if(overflow_key(b,i)) {
        auto& slot=b.slots[i];
        if(!slot.data)continue;
        if(slot.pins) { *pinned=true;continue; }
        if(slot.used<oldest) { oldest=slot.used;victim=&b;*index=i; }
    }
    return victim;
}
}
extern "C" void* re4dc_motion_required_alloc(int heap,unsigned bytes) {
    // Binding metadata/reserve admission already owns this mutex. Reclaim in
    // place using only SDK try/free calls: no recursive lock or native alloc,
    // no pin wait, and no false final required-allocation diagnostic.
    int old=irq_disable();const bool internal=thd_current && lock_owner==thd_current;irq_restore(old);
    if(internal) {
#if RE4DC_SUBSCREEN
        if(hold)return nullptr;
#endif
        if(re4dc_motion_heap_handle()!=heap)return nullptr;
        for(;;) {
            if(void* p=re4dc_motion_source_try_alloc(heap,bytes))return p;
            unsigned i=0;bool pinned=false;auto* victim=overflow_victim(heap,&i,&pinned);
            if(!victim)return nullptr;
            discard(*victim,i);++stats.evictions;
        }
    }
    // A same-thread evaluator, IRQ,
    // or caller-masked critical section cannot wait for itself or another CPU
    // owner; these unsupported call contexts retain the original NULL result.
    if(!can_wait_required())return nullptr;
    RequiredScope request;
    for(;;) {
        bool pinned=false;
        {
            Locked guard;
#if RE4DC_SUBSCREEN
            if(hold)return nullptr;
#endif
            if(re4dc_motion_heap_handle()!=heap)return nullptr;
            for(;;) {
                // Allocate before dropping the mutex: cache refill cannot take
                // the gap just reclaimed for the exact required request.
                if(void* p=re4dc_motion_source_try_alloc(heap,bytes))return p;
                unsigned i=0;auto* victim=overflow_victim(heap,&i,&pinned);
                if(!victim)break;
#if RE4DC_MOTION_RESUME
                // The movie's own staging request is still a movie loan.
                // Background/equipment pressure during it is not a ticket.
                if(capacity_movie_owner==thd_current)resume_journal.movie_evicted(unsigned(victim-bindings),i);
#endif
                discard(*victim,i);++stats.evictions;
            }
        }
        if(!pinned)return nullptr;
        // All selected lease consumers are bounded evaluator-only scopes; the
        // source proof and host concurrent pin test are mandatory for this wait.
        thd_pass();
    }
}
extern "C" int re4dc_motion_capacity_retire() {
    if(!can_wait_required())return 0;
    RequiredScope request;
    for(;;) {
        bool pinned=false;
        {
            Locked guard;
#if RE4DC_SUBSCREEN
            if(hold)return 0;
#endif
            const int heap=re4dc_motion_heap_handle();
            for(;;) {
                unsigned i=0;auto* victim=overflow_victim(heap,&i,&pinned);
                if(!victim)break;
                discard(*victim,i);++stats.evictions;
            }
            if(!pinned) { capacity_retiring=true;return 1; }
        }
        thd_pass();
    }
}
#endif
extern "C" int re4dc_motion_thread_busy(const void* owner) {
    int old=irq_disable();unsigned busy=0;
    for(const auto& o:owners) if(o.thread==owner)busy=o.leases;
    irq_restore(old);return busy!=0;
}
extern "C" void re4dc_motion_get_stats(Re4dcMotionStats* out) { Locked guard;*out=stats; }
#if defined(RE4DC_MOTION_STATS_LOG) && RE4DC_MOTION_STATS_LOG
// dvd_read_safe.cpp, each DISCRD window close: one MOTWS line per bound archive (keys used: count / bytes).
extern "C" void re4dc_motion_ws_window() {
    Locked guard;const bool blk_end=++ws_windows%5==0;
    for(unsigned k=0;k<kArchives;++k) {
        const auto& b=bindings[k];if(!b.archive)continue;
        unsigned n[3]={0,0,0},by[3]={0,0,0},cold=0;
        for(unsigned i=0;i<b.count && i<256;++i) {
            const unsigned char m=(unsigned char)(1u<<(i&7));const unsigned sz=aligned(word(record(b,i)+4));
            if(ws_win[k][i>>3]&m){++n[0];by[0]+=sz;if(!word(record(b,i)+16))cold+=sz;}
            if(ws_blk[k][i>>3]&m){++n[1];by[1]+=sz;}
            if(ws_all[k][i>>3]&m){++n[2];by[2]+=sz;}
        }
        re4dc_log("MOTWS: archive=%u entries=%u win=%u/%u (cold %u) block5=%u/%u%s bind=%u/%u resident=%u\n",b.bytes,b.count,
                  n[0],by[0],cold,n[1],by[1],blk_end?" end":"",n[2],by[2],b.resident);
        std::memset(ws_win[k],0,32);if(blk_end)std::memset(ws_blk[k],0,32);
    }
}
#endif
extern "C" int re4dc_motion_bind(void* archive,unsigned bytes) {
    Locked guard;auto* a=static_cast<unsigned char*>(archive);
    if(!a || bytes<16)return 0;
    const unsigned n=word(a),rel=word(a+4);if(n>(bytes-16)/8)return 0;
    const unsigned char* mtc=nullptr;unsigned mtc_offset=0;
    for(unsigned i=0;i<n;++i)if(!std::memcmp(a+16+4*n+4*i,"MTC",4)) {
        if(mtc || i!=n-1)return 0;
        mtc_offset=word(a+16+4*i);
        if(mtc_offset>bytes || bytes-mtc_offset<32)return 0;
        mtc=a+mtc_offset;
    }
    if(!mtc)return 1; // ordinary source archive, no cache allocated
    // D325 qualifies room-owned em12, before heap4 reset. Frozen stage heaps
    // and the ARAM/shooting-range swap require a distinct ownership audit.
    if(re4dc_motion_current_heap()!=4)return 0;
#if RE4DC_MOTION_BOUNDED_R11F
    if(rel>bytes || bytes-rel!=64 || mtc_offset<16+8*n ||
       mtc_offset>=rel || rel-mtc_offset<32 || (mtc_offset&31) ||
       std::memcmp(mtc,"R4MOTBL\0",8) || word(mtc+16)!=20 || word(mtc+24)!=bytes)return 0;
    unsigned clip_limit=kClipLimit;bool bounded=false;
    if(word(mtc+8)==3u) {
#if RE4DC_SUBSCREEN
        if(hold)return 0;
#endif
        clip_limit=bounded_profile(a,bytes,rel,mtc);
        if(!clip_limit)return 0;
        bounded=true;
    } else if(word(mtc+8)!=2u || word(mtc+28)!=kClipLimit)return 0;
#else
    if(rel>bytes || bytes-rel!=64 || mtc_offset<16+8*n ||
       mtc_offset>=rel || rel-mtc_offset<32 || (mtc_offset&31) ||
       std::memcmp(mtc,"R4MOTBL\0",8) || word(mtc+8)!=2 || word(mtc+16)!=20 ||
       word(mtc+24)!=bytes || word(mtc+28)!=kClipLimit)return 0;
#endif
    const unsigned count=word(mtc+12);
    if(!count || count>kEntries || count>(rel-mtc_offset-32)/20 ||
       net_crc32le(mtc+32,count*20)!=word(mtc+20))return 0;
    unsigned hot=0,largest=0,prev=0;
    for(unsigned i=0;i<count;++i) {
        const auto* e=mtc+32+20*i;const unsigned off=word(e),size=word(e+4),flags=word(e+16);
        if(off<16+8*n || off>=mtc_offset || (off&31) || off<=prev ||
#if RE4DC_MOTION_BOUNDED_R11F
           size>clip_limit || (bounded && flags) ||
#else
           size>kClipLimit ||
#endif
           size<32 || (size&31) || flags>1 || !a[off+2])return 0;
        unsigned head=prefix(a+off);if(head>size || head>mtc_offset-off)return 0;
        bool found=false;unsigned end=mtc_offset;
        for(unsigned j=0;j<n;++j) {
            unsigned p=word(a+16+4*j);if(p>off && p<end)end=p;
            if(p==off) { if(std::memcmp(a+16+4*n+4*j,"FCV",4))return 0;found=true; }
        }
        if(!found || aligned(head)!=end-off || head>=size)return 0;
        if(flags)hot+=size;else if(size>largest)largest=size;
        const auto* table=a+off+head-4*a[off+2];
        for(unsigned j=0;j<a[off+2];++j)if(word(table+4*j)<head || word(table+4*j)>=size)return 0;
        prev=off;
    }
    Binding* b=nullptr;
    for(auto& q:bindings) { if(q.archive==a)return 0;if(!q.archive && !b)b=&q; }
    if(!b)return 0;
    const unsigned meta=aligned(count*sizeof(Slot));auto* slots=static_cast<Slot*>(re4dc_motion_alloc(meta));
    if(!slots)return 0;
    std::memset(slots,0,meta);
    // Selected recurring/response set plus two largest cold clips. D325 is
    // diagnostic until the source prefetch/concurrency closure is complete.
    // Hot entries are never LRU victims; a budget miss is explicit, not thrash.
    *b={a,bytes,mtc+32,count,slots,hot+2*largest,hot,0};
#if RE4DC_MOTION_CAPACITY
    capacity_retiring=false;
#endif
#if RE4DC_MOTION_BOUNDED_R11F
    b->bounded=bounded;
#endif
    stats.metadata_bytes+=meta;stats.hot_bytes+=hot;
#if RE4DC_MOTION_RESUME
    resume_journal.binding_changed(unsigned(b-bindings));
#endif
#if RE4DC_MOTION_RESERVE
    if(largest) {
#if RE4DC_MOTION_RESERVE_PACK
        if(!reserve_allocate(*b,largest)) {re4dc_log("motion bind: reserve backing of 2x%u failed\n",b->slab_bytes);release_binding(*b);return 0;}
        re4dc_log("motion reserve: backing=%s payload=%u\n",b->joined?"joined":"two-cell",2*b->slab_bytes);
#else
        b->slab_bytes=aligned(largest);
        for(auto*& p:b->slab) {
            p=static_cast<unsigned char*>(re4dc_motion_alloc(b->slab_bytes));
            if(!p) { re4dc_log("motion bind: reserve slab of %u failed\n",b->slab_bytes);release_binding(*b);return 0; }
#if RE4DC_MOTION_BOUNDED_R11F
            if(b->bounded)stats.metadata_bytes+=b->slab_bytes;
#endif
        }
#if RE4DC_MOTION_BOUNDED_R11F
        if(!b->bounded)
#endif
        stats.metadata_bytes+=2*b->slab_bytes;
#endif
        re4dc_log("motion reserve: bind slabs=2x%u\n",b->slab_bytes);
    }
#endif
#if RE4DC_MOTION_USAGE_LOG
    b->seen=static_cast<unsigned char*>(re4dc_motion_alloc(aligned(count)));
    if(b->seen)std::memset(b->seen,0,aligned(count));
#endif
    for(unsigned i=0;i<count;++i)if(word(record(*b,i)+16))load(*b,i);
    re4dc_log("motion bind: archive=%u entries=%u hot=%u cache-budget=%u metadata=%u\n",bytes,count,hot,b->budget,meta);
#if RE4DC_MOTION_PRESSURE_BYTES
    re4dc_log("motion pressure: cap=%u resident=%u peak=%u pinned=%u evictions=%u loads=%u\n",
        unsigned(RE4DC_MOTION_PRESSURE_BYTES),stats.resident_bytes,stats.peak_cache_bytes,
        stats.pinned_bytes,stats.evictions,stats.loads);
#endif
    return 1;
}
extern "C" int re4dc_motion_acquire(const void* header,unsigned** table) {
    if(!header)return 0;
#if !RE4DC_MOTION_LEASE_LEAN
    const auto started=timer_us_gettime64();
#endif
    Locked guard;
    if(!stats.metadata_bytes)return 0;
    const auto p=reinterpret_cast<std::uintptr_t>(header);
    for(unsigned bno=0;bno<kArchives;++bno) {
        auto& b=bindings[bno];
#if RE4DC_MOTION_BOUNDED_R11F && RE4DC_SUBSCREEN
        if(hold && b.bounded)continue; // no archive-range, MTC or slot reads across the room/UI swap
#endif
        auto base=reinterpret_cast<std::uintptr_t>(b.archive);
        if(!base || p<base || p-base>=b.bytes)continue;
#if RE4DC_MOTION_INDEX
        // GAME_MOTION_INDEX (design-logic P4): re4dc_motion_bind accepts a table only when the record
        // offsets are strictly increasing (off<=prev rejects it), so the offsets are unique and sorted
        // and a binary search finds the one record the linear scan finds (8 probes instead of up to
        // 255 unaligned word() reads per acquire). The lease, pins, stats and load() are unchanged.
        unsigned lo=0,hi=b.count;const unsigned want=unsigned(p-base);
        while(lo<hi) { const unsigned mid=(lo+hi)>>1;if(word(record(b,mid))<want)lo=mid+1;else hi=mid; }
        for(unsigned i=lo;i<b.count && i==lo;++i)if(word(record(b,i))==want) {
#else
        for(unsigned i=0;i<b.count;++i)if(word(record(b,i))==p-base) {
#endif
            *table=load(b,i);auto& s=b.slots[i];
#if RE4DC_MOTION_USAGE_LOG
            if(b.seen && !b.seen[i]) { b.seen[i]=1;re4dc_log("motion use: archive=%u entry=%u bytes=%u hot=%u\n",b.bytes,i,word(record(b,i)+4),word(record(b,i)+16)); }
#endif
            if(!s.pins++) { stats.pinned_bytes+=word(record(b,i)+4);if(stats.pinned_bytes>stats.peak_pinned_bytes)stats.peak_pinned_bytes=stats.pinned_bytes; }
#if RE4DC_MOTION_LEASE_LEAN
            guard.retain_lease();
            // worst_wait_us keeps actual miss/load timing; hit-path timing was
            // telemetry only. The load() timers and I/O probe are unchanged.
#else
            owner_add();
            const auto wait=timer_us_gettime64()-started;
            if(wait>stats.worst_wait_us)stats.worst_wait_us=wait;
#endif
#if RE4DC_MOTION_RESUME
            resume_journal.acquired(bno,i,re4dc_fixture_source_frame());
#endif
            return bno*256+i+1;
        }
    }
    return 0;
}
#if RE4DC_GC_ASSET_MOTION_SOURCE
extern "C" unsigned re4dc_motion_gcasset_counter_lock(){return unsigned(irq_disable());}
extern "C" void re4dc_motion_gcasset_counter_unlock(unsigned old){irq_restore(int(old));}
extern "C" void re4dc_motion_gcasset_publish(int token,const void* header) {
    const void* source_owner=nullptr;unsigned source_serial=0;
    {
        Locked guard;
        if(token>0 && token<=int(kArchives*256)) {
            const unsigned t=unsigned(token-1);auto& b=bindings[t/256];const unsigned i=t%256;
            if(b.archive && i<b.count) {
                auto& s=b.slots[i];
                if(s.pins && s.data && header==b.archive+word(record(b,i))) {
                    source_owner=&s;
                    source_serial=re4dc_gcasset::motion_source_external_serial(&s,s.data,header);
                }
            }
        }
    } // actual mutex unlock; the acquire lease still pins Slot and Binding
    re4dc_gcasset::motion_source_external_publish(source_owner,source_serial);
}
extern "C" int re4dc_motion_gcasset_idle() {
    // Root first stops the real game/model producers. This finite witness
    // then refuses an in-flight load/mutex owner or any outstanding lease.
    // It is not an assertion that an instantaneously empty queue is stopped.
    if(mutex_trylock(&lock)!=0)return 0;
    bool idle=true;const int old=irq_disable();
    for(const auto& o:owners)if(o.thread && o.leases)idle=false;
    irq_restore(old);
    for(const auto& b:bindings)if(b.archive)for(unsigned i=0;i<b.count;++i)if(b.slots[i].pins)idle=false;
    mutex_unlock(&lock);return idle?1:0;
}
#endif
extern "C" void re4dc_motion_release(int token) {
    Locked guard;if(token<=0 || token>int(kArchives*256))fail("motion lease token");
    unsigned t=token-1;auto& b=bindings[t/256];unsigned i=t%256;
    if(!b.archive || i>=b.count || !b.slots[i].pins)fail("motion unbalanced release");
    if(!--b.slots[i].pins)stats.pinned_bytes-=word(record(b,i)+4);
    owner_drop(); // retain loaded bytes and relocated table until actual eviction
}
extern "C" void re4dc_motion_unbind(void* archive) {
    Locked guard;for(auto& b:bindings)if(b.archive==archive && archive)release_binding(b);
}
#if RE4DC_SUBSCREEN
extern "C" int re4dc_motion_owner_live(const void* p);  // motion_bridge.cpp
extern "C" void re4dc_motion_hold(int on) { Locked guard;hold=on!=0;
#if RE4DC_MOTION_RESUME
    if(hold){resume_journal.cancel_movie();resume_pending={};resume_pending_live=false;}
#endif
}
// Sub screen close, after the area holds the game's bytes again: a slot table inside the area
// is back to its state at open; clips loaded meanwhile came from heap 12, which is gone. Those
// slots (and a binding whose table was in heap 12) are forgotten, not freed, and the resident
// and pinned totals are recounted from the tables. Returns the slots dropped.
extern "C" unsigned re4dc_motion_forget_dead_heaps() {
    Locked guard;unsigned n=0,resident=0,pinned=0;
    for(auto& b:bindings) {
        if(!b.archive)continue;
        if(b.slots && !re4dc_motion_owner_live(b.slots)) {
#if RE4DC_MOTION_RESERVE
            stats.metadata_bytes-=2*b.slab_bytes;
#endif
            stats.metadata_bytes-=aligned(b.count*sizeof(Slot));stats.hot_bytes-=b.hot_bytes;
#if RE4DC_MOTION_RESUME
            resume_journal.binding_changed(unsigned(&b-bindings));
#endif
            b={};++n;continue;
        }
        b.resident=0;
        for(unsigned i=0;i<b.count;++i) {
            auto& s=b.slots[i];
#if RE4DC_MOTION_RESERVE_PACK
            // owner_live reads the allocator header before a base pointer.
            // Packed FCVs borrow the slab allocation; an interior FCV has none.
            const auto* owner=reserved_base(b,s.data);
            if(s.data && !re4dc_motion_owner_live(owner?owner:s.data)){
#if RE4DC_MOTION_RESUME
                resume_journal.key_forgotten(unsigned(&b-bindings),i);
#endif
#if RE4DC_MOTION_CAPACITY
                overflow_mark(b,i,false);
#endif
                s={};++n;}
#else
            if(s.data && !re4dc_motion_owner_live(s.data)){
#if RE4DC_MOTION_RESUME
                resume_journal.key_forgotten(unsigned(&b-bindings),i);
#endif
                s={};++n;}
#endif
            if(!s.data)continue;
            b.resident+=aligned(word(record(b,i)+4));
            if(s.pins)pinned+=word(record(b,i)+4);
        }
        resident+=b.resident;
    }
    stats.resident_bytes=resident;stats.pinned_bytes=pinned;hold=false;
    return n;
}
#endif
extern "C" void re4dc_motion_retire_all() {
    Locked guard;
#if RE4DC_MOTION_RETIRE_PREFLIGHT
    // Validate the complete set under the same lock used for retirement.
    // A later pinned binding must not leave earlier bindings already freed.
    for(const auto& b:bindings)if(b.archive)
        for(unsigned i=0;i<b.count;++i)
            if(b.slots[i].pins)fail("motion archive retired while pinned");
#endif
    for(auto& b:bindings)if(b.archive)release_binding(b);
}
#if RE4DC_MOVIE_HEAP_EVICT
// MOVIE_HEAP_EVICT=1 (game30.mk): a route movie whose staging allocation fails evicts the least recently
// used unpinned motion key and retries (native_movie.cpp plm_alloc). The movie owns the frame, so no
// character animates while it plays; an evicted key reloads from disc at its next use, as after
// MOTION_OOM_EVICT. Returns the bytes freed, 0 when no key can go.
#if RE4DC_MOTION_RESUME
namespace { unsigned evict_heap_key(bool movie) {
#else
extern "C" unsigned re4dc_motion_evict_one() {
#endif
    Locked guard;
#if RE4DC_SUBSCREEN
    if(hold)return 0;
#endif
    Binding* victim=nullptr;unsigned index=0;
    std::uint64_t oldest=~std::uint64_t(0);
    for(auto& q:bindings) {
        if(!q.archive)continue;
        for(unsigned j=0;j<q.count;++j) {
            const auto& slot=q.slots[j];
#if RE4DC_MOTION_RESERVE_PACK
            if(reserved_data(q,slot.data))continue;
#elif RE4DC_MOTION_RESERVE
            if(slot.data==q.slab[0] || slot.data==q.slab[1])continue;   // evicting a slab user frees nothing
#endif
            if(slot.data && !slot.pins && slot.used<oldest) { victim=&q;index=j;oldest=slot.used; }
        }
    }
    if(!victim)return 0;
    const unsigned freed=aligned(word(record(*victim,index)+4));
#if RE4DC_MOTION_RESUME
    if(movie)resume_journal.movie_evicted(unsigned(victim-bindings),index);
#endif
    discard(*victim,index);++stats.evictions;
    return freed;
}
#if RE4DC_MOTION_RESUME
}
extern "C" unsigned re4dc_motion_evict_one() { return evict_heap_key(false); }
extern "C" unsigned re4dc_motion_movie_evict_one() { return evict_heap_key(true); }
#endif
#endif

#if RE4DC_MOTION_RESUME
extern "C" void re4dc_motion_movie_begin() {
    Locked guard;
#if RE4DC_SUBSCREEN
    if(hold){resume_journal.cancel_movie();resume_pending={};resume_pending_live=false;return;}
#endif
    if(re4dc_motion_current_heap()!=4){resume_journal.cancel_movie();resume_pending={};resume_pending_live=false;return;}
#if RE4DC_MOTION_CAPACITY
    capacity_movie_owner=thd_current;
#endif
    if(!resume_journal.begin_movie(re4dc_fixture_source_frame())) {
#if RE4DC_MOTION_CAPACITY
        capacity_movie_owner=nullptr;
#endif
        resume_journal.cancel_movie();resume_pending={};resume_pending_live=false; // fail closed for an unexpected nested owner
        re4dc_log("motion resume: nested movie owner, tracking cancelled\n");
    }
}
extern "C" void re4dc_motion_movie_finish(int retiring) {
    Locked guard;auto ended=resume_journal.finish_movie();
#if RE4DC_MOTION_CAPACITY
    capacity_movie_owner=nullptr;
#endif
#if RE4DC_SUBSCREEN
    if(hold)retiring=1;
#endif
    if(retiring || re4dc_motion_current_heap()!=4){resume_pending={};resume_pending_live=false;return;}
    // A skipped movie may immediately open its cancel/QTE clip before the
    // route reaches its final boundary. Keep still-current tickets from both.
    if(resume_pending_live)for(unsigned k=0;k<kArchives;++k)
        if(resume_journal.current(resume_pending,k) && resume_journal.current(ended,k))
            for(unsigned w=0;w<8;++w)ended.keys[k][w]|=resume_pending.keys[k][w];
    resume_pending=ended;resume_pending_live=false;
    for(const auto& row:resume_pending.keys)for(const auto bits:row)if(bits)resume_pending_live=true;
}
extern "C" unsigned re4dc_motion_movie_restore() {
    Locked guard;if(!resume_pending_live)return 0;
    auto tickets=resume_pending;resume_pending={};resume_pending_live=false;
#if RE4DC_SUBSCREEN
    if(hold)return 0; // no borrowed archive/record/slot access across suspension
#endif
    if(re4dc_motion_current_heap()!=4 || !re4dc_heap_largest_current)return 0;
    if(!resume_journal.restrict_recent(tickets,re4dc_fixture_source_frame()))return 0;
    unsigned count=0,bytes=0,margin=0;bool refused=false;
    for(unsigned k=0;k<kArchives;++k) {
        const auto& b=bindings[k];if(!b.archive || !resume_journal.current(tickets,k))continue;
        for(unsigned i=0;i<b.count;++i)if(tickets.contains(k,i) && !b.slots[i].data) {
#if RE4DC_MOTION_BOUNDED_R11F
            if(b.bounded){refused=true;continue;} // v3 never gains a heap-key path
#endif
            const auto* e=record(b,i);bytes+=aligned(word(e+4));++count;
            if(!word(e+16)) {
                unsigned cold=~0u;
#if RE4DC_MOTION_RESERVE_SPILL
                cold=RE4DC_MOTION_RESERVE_SPILL;
#endif
#if RE4DC_MOTION_COLD_POOL
                if(cold_pool_margin()<cold)cold=cold_pool_margin();
#endif
                if(cold==~0u)refused=true;
                else if(cold>margin)margin=cold;
            }
        }
    }
    if(!count)return 0;
    unsigned free_bytes=0,largest=re4dc_heap_largest_current(&free_bytes);
    constexpr unsigned allocation_overhead=96; // MotionAllocation32 + MAD tag32 + SDK heap cell32
    const unsigned overhead=count*allocation_overhead;
    const unsigned need=bytes+overhead;
    const bool cap=bytes<=RE4DC_MOTION_PRESSURE_BYTES && pressure_heap_bytes()<=RE4DC_MOTION_PRESSURE_BYTES-bytes;
    if(refused || !cap || largest<need || free_bytes<need || margin>free_bytes-need) {
        re4dc_log("motion resume: deferred keys=%u bytes=%u margin=%u free=%u largest=%u policy=%d cap=%d\n",count,bytes,margin,free_bytes,largest,refused?0:1,cap?1:0);
        return 0;
    }
    unsigned restored=0,read=0;
    for(unsigned k=0;k<kArchives;++k) {
        auto& b=bindings[k];if(!b.archive || !resume_journal.current(tickets,k))continue;
        for(unsigned i=0;i<b.count;++i)if(tickets.contains(k,i) && !b.slots[i].data) {
            const unsigned n=aligned(word(record(b,i)+4));
            largest=re4dc_heap_largest_current(&free_bytes);
            // Other resource owners can allocate while storage yields. Stop
            // safely rather than invoke OOM/pressure eviction or force memory.
            if(re4dc_motion_current_heap()!=4 || largest<n+allocation_overhead || free_bytes<n+allocation_overhead || margin>free_bytes-n-allocation_overhead)goto done;
            auto* data=static_cast<unsigned char*>(re4dc_motion_alloc(n));if(!data)goto done;
            load(b,i,data);++restored;read+=n;
        }
    }
 done:
    re4dc_log("motion resume: planned=%u restored=%u bytes=%u deferred=%u evictions=0\n",count,restored,read,count-restored);
    return restored;
}
#endif
