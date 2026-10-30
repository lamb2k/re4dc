// D328: no new I/O/cache or effect selection. Borrowed metadata and packed data
// share the source archive lifetime; callers own one 300-byte decode scratch.
#include "native_effect.h"
#include "re4dc_platform.h"
#include <kos.h>
#include <kos/net.h>
#include <cstring>
#include <cstdint>
#ifndef RE4DC_EFFECT_BIND_DIAG
#define RE4DC_EFFECT_BIND_DIAG 0
#endif
#ifndef RE4DC_OB_DECODE
#define RE4DC_OB_DECODE 0
#endif
#if defined(RE4DC_WATER_LAYER29) && RE4DC_WATER_LAYER29
extern "C" void re4dc_water29_retire_archive();
#endif
#if defined(RE4DC_CLOTH_MATERIAL11) && RE4DC_CLOTH_MATERIAL11
extern "C" void re4dc_cloth_material_retire11();
#define RE4DC_CLOTH_ROOM_RETIRE11() re4dc_cloth_material_retire11();
#else
#define RE4DC_CLOTH_ROOM_RETIRE11()
#endif
#line 15
#if RE4DC_EFFECT_BIND_DIAG
extern "C" { unsigned re4dc_effect_bind_fail_line; }  // file scope: not in the unnamed namespace
// ocbp line by line (no 16 KB purge-all buffer): write back dirty lines, drop the rest, so the next read is from RAM
extern "C" void re4dc_dcache_purge(const void* p, unsigned n)
{
    for (uintptr_t a = (uintptr_t) p & ~(uintptr_t) 31; a < (uintptr_t) p + n; a += 32) __asm__ __volatile__("ocbp @%0" : : "r"(a) : "memory");
}
#endif
namespace {
struct Binding { unsigned char* archive; unsigned bytes; const unsigned char* entries; unsigned count; };
Binding bindings[6]{}; // four module owners, persistent core, current room
Re4dcEffectStats stats{};
#if RE4DC_OB_DECODE
// GAME_OB_DECODE (game30.mk; exact): this unit builds at -O1, where each 4-byte memcpy of word() and
// decode() was a library call (~1,260 per square tick). A 4-aligned word is read in place (the same
// four bytes memcpy copies); any other address keeps memcpy.
typedef std::uint32_t __attribute__((may_alias)) ObWord;
static_assert(sizeof(unsigned) == sizeof(ObWord), "word size");
inline unsigned word(const unsigned char* p) {
    if(!(reinterpret_cast<std::uintptr_t>(p)&3))return *reinterpret_cast<const ObWord*>(p);
    unsigned v;std::memcpy(&v,p,4);return v;
}
#if RE4DC_OB_DECODE == 2
unsigned long obDecChk[3]; // calls, fast-path calls, mismatching calls ("OBD")
#endif
#else
unsigned word(const unsigned char* p) { unsigned v;std::memcpy(&v,p,4);return v; }
#endif
unsigned half(const unsigned char* p) { unsigned short v;std::memcpy(&v,p,2);return v; }
const unsigned char* entry(const Binding& b,unsigned i) { return b.entries+12*i; }
[[noreturn]] void fail(const char* why) { ++stats.failures;re4dc_missing(why);__builtin_trap(); }
bool eligible(const unsigned char* r) {
    bool copy=false;
    switch(r[1]) { case 0:case 1:case 2:case 3:case 7:case 9:case 11:case 16:case 17:
        case 22:case 26:case 64:case 69:case 70:case 74:case 254:copy=true; }
    return copy && (r[264]==0 || (r[264]==1 && r[265]==0));
}
bool decode(const unsigned char* p,unsigned bytes,void* out) {
    if(bytes<12 || (bytes&3) || word(p+8)>>11)return false;
    unsigned count=0;for(unsigned i=0;i<3;++i)count+=__builtin_popcount(word(p+4*i));
    if(bytes!=12+4*count)return false;
    auto* dst=static_cast<unsigned char*>(out);unsigned at=12;
#if RE4DC_OB_DECODE
    // Aligned record and output that do not overlap: the three mask words are read once and each
    // output word is stored in place. For every i the source reads the same mask bit and, when it is
    // set, the next value word, so the 75 words written are the same (the byte-count test above keeps
    // the value reads inside the record).
    const auto pa=reinterpret_cast<std::uintptr_t>(p),da=reinterpret_cast<std::uintptr_t>(out);
    bool fast=!((pa|da)&3) && (da+300<=pa || pa+bytes<=da);
#if RE4DC_OB_DECODE == 2
    alignas(4) unsigned char mine[300];
    ++obDecChk[0];
#endif
    if(fast) {
#if RE4DC_OB_DECODE == 2
        auto* d=reinterpret_cast<ObWord*>(mine);
#else
        auto* d=static_cast<ObWord*>(out);
#endif
        const auto* s=reinterpret_cast<const ObWord*>(p);
        const ObWord* v=s+3;
        for(unsigned k=0;k<3;++k) {
            unsigned m=s[k];
            for(unsigned b=k<2?32:11;b;--b,m>>=1)*d++=(m&1)?*v++:0;
        }
#if RE4DC_OB_DECODE != 2
        return true;
#else
        ++obDecChk[1];
#endif
    }
#endif
    for(unsigned i=0;i<75;++i) {
        unsigned value=0;
        if(word(p+4*(i/32))&(1U<<(i%32))) { value=word(p+at);at+=4; }
        std::memcpy(dst+4*i,&value,4);
    }
#if RE4DC_OB_DECODE == 2
    if(fast && std::memcmp(mine,dst,300))++obDecChk[2];
    if(obDecChk[0]%1024==1)re4dc_log("OBD calls=%lu fast=%lu mis=%lu\n",obDecChk[0],obDecChk[1],obDecChk[2]);
#endif
    return true;
}
// Last sequence whose head is <= offset. Packed heads are sorted by converter.
unsigned sequence(const Binding& b,unsigned off) {
    unsigned lo=0,hi=b.count;
    while(lo<hi) { unsigned mid=lo+(hi-lo)/2;if(word(entry(b,mid))<=off)lo=mid+1;else hi=mid; }
    return lo?lo-1:b.count;
}
}
#if RE4DC_EFFECT_BIND_DIAG
// EFFECT_BIND_DIAG=1 (lane discread 10-15, console diagnosis; default 0 = image unchanged): the source line of the check
// that refused an archive, for the MISSING line in read.cpp (data damage vs a full or stale binding table).
#define BIND_FAIL (re4dc_effect_bind_fail_line = __LINE__, 0)
#else
#define BIND_FAIL 0
#endif
static int bind_archive(void* archive,unsigned bytes,unsigned owner) {
    auto* a=static_cast<unsigned char*>(archive);if(!a || bytes<16)return BIND_FAIL;
    const unsigned n=word(a),rel=word(a+4);if(n>(bytes-16)/8)return BIND_FAIL;
    const unsigned char* table=nullptr;unsigned table_off=0;
    for(unsigned i=0;i<n;++i)if(!std::memcmp(a+16+4*n+4*i,"ESQ",4)) {
        if(table)return BIND_FAIL;
        table_off=word(a+16+4*i);
        if(table_off>bytes || bytes-table_off<32)return BIND_FAIL;
        table=a+table_off;
    }
    if(!table)return 1;
    const unsigned end=owner>=4?bytes:rel;
    if((owner>=4?rel!=0:(rel>bytes || bytes-rel!=64)) || (table_off&31) || table_off<16+8*n || table_off>=end ||
       end-table_off<32 || std::memcmp(table,"R4ESQTBL",8) || word(table+8)!=1 ||
       word(table+16)!=12 || word(table+24)!=bytes || word(table+28))return BIND_FAIL;
    const unsigned count=word(table+12);
    if(!count || count>4096 || count>(end-table_off-32)/12 ||
       net_crc32le(table+32,12*count)!=word(table+20))return BIND_FAIL;
    unsigned previous_end=16+8*n,records=0;
    alignas(4) unsigned char scratch[300];
    for(unsigned i=0;i<count;++i) {
        const auto* e=table+32+12*i;unsigned off=word(e),span=word(e+4),nr=word(e+8);
        if(off<previous_end || off>table_off || span>table_off-off || span<48 ||
           (off&3) || (span&31) || nr!=half(a+off) || !nr || nr>(span-48)/4)return BIND_FAIL;
        const auto* head=a+off;unsigned expected=48+4*nr;
        for(unsigned j=0;j<nr;++j) {
            unsigned v=word(head+48+4*j),start=v&~1U;
            if(start!=expected || start>span || (start&3))return BIND_FAIL;
            unsigned end=j+1<nr?(word(head+48+4*(j+1))&~1U):span;
            if(end<=start || end>span)return BIND_FAIL;
            unsigned len=300;
            if(v&1) {
                if(end-start<12 || word(head+start+8)>>11)return BIND_FAIL;
                len=12;for(unsigned k=0;k<3;++k)len+=4*__builtin_popcount(word(head+start+4*k));
                if(len>=300 || len>end-start || !decode(head+start,len,scratch) || !eligible(scratch))return BIND_FAIL;
            }
            if(len>end-start || (j+1<nr && len!=end-start))return BIND_FAIL;
            expected=start+len;
        }
        for(unsigned p=expected;p<span;++p)if(head[p])return BIND_FAIL;
        if(span-expected>=32)return BIND_FAIL;
        previous_end=off+span;records+=nr;
    }
    Binding* free=nullptr;
    for(auto& b:bindings)if(b.archive==a)return BIND_FAIL;
    for(unsigned i=owner;i<(owner>=4?owner+1:4);++i)if(!bindings[i].archive && !free)free=&bindings[i];
    if(!free)return BIND_FAIL;
    *free={a,bytes,table+32,count};stats.sequences+=count;stats.records+=records;
    re4dc_log("effect bind: archive=%u sequences=%u records=%u metadata=borrowed scratch=300 no-io\n",bytes,count,records);
    return 1;
}
extern "C" int re4dc_effect_bind(void* a,unsigned n) { return bind_archive(a,n,0); }
extern "C" int re4dc_effect_bind_core(void* a,unsigned n) { return bind_archive(a,n,4); }
extern "C" int re4dc_effect_bind_room(void* a,unsigned n) { return bind_archive(a,n,5); }
extern "C" void re4dc_effect_unbind(void* archive) {
    // Retain the original source archive lifetime and teardown suspension.
    // The REL epilog runs first; no decoded allocation or global scratch.
    for(auto& b:bindings)if(b.archive==archive && archive) {
        stats.sequences-=b.count;for(unsigned i=0;i<b.count;++i)stats.records-=word(entry(b,i)+8);
        b={};return;
    }
}
extern "C" void re4dc_effect_retire_room() { RE4DC_CLOTH_ROOM_RETIRE11()
    // The source has suspended room updates before replacing the room heap.
#if defined(RE4DC_WATER_LAYER29) && RE4DC_WATER_LAYER29
    re4dc_water29_retire_archive();
#endif
    re4dc_effect_unbind(bindings[5].archive);
}
extern "C" void* re4dc_effect_record_ref(void* head,unsigned index) {
    auto* h=static_cast<unsigned char*>(head);if(!h || index>=half(h))fail("effect record index");
    const auto ptr=reinterpret_cast<std::uintptr_t>(head);
    for(const auto& b:bindings) {
        const auto base=reinterpret_cast<std::uintptr_t>(b.archive);
        if(!b.archive || ptr<base || ptr-base>=b.bytes)continue;
        unsigned s=sequence(b,ptr-base);
        if(s<b.count && word(entry(b,s))==ptr-base) {
            unsigned ref=word(h+48+4*index);
            return reinterpret_cast<void*>((ptr+(ref&~1U))|(ref&1));
        }
    }
    return h+48+300*index;
}
extern "C" void* re4dc_effect_record_read(void* reference,void* scratch) {
    auto ptr=reinterpret_cast<std::uintptr_t>(reference);
    if(!(ptr&1)) { ++stats.raw_reads;return reference; }
    auto started=timer_us_gettime64();ptr&=~std::uintptr_t(1);
    for(const auto& b:bindings) {
        const auto base=reinterpret_cast<std::uintptr_t>(b.archive);
        if(!b.archive || ptr<base || ptr-base>=b.bytes)continue;
        unsigned s=sequence(b,ptr-base);if(s==b.count)break;
        const auto* e=entry(b,s);const auto* h=b.archive+word(e);unsigned off=ptr-(base+word(e));
        unsigned lo=0,hi=word(e+8);
        while(lo<hi) { unsigned m=lo+(hi-lo)/2;if((word(h+48+4*m)&~1U)<off)lo=m+1;else hi=m; }
        if(lo==word(e+8) || word(h+48+4*lo)!=(off|1))break;
        unsigned len=12;for(unsigned k=0;k<3;++k)len+=4*__builtin_popcount(word(h+off+4*k));
        if(!scratch || !decode(h+off,len,scratch))break;
        ++stats.reads;const auto elapsed=timer_us_gettime64()-started;
#if defined(RE4DC_EFFECT_STATS_LOG) && RE4DC_EFFECT_STATS_LOG
        // EFFECT_STATS_LOG=1 (test only, lane ch4found16 2026-10-17): every new worst compact-record decode, and a
        // summary every 4096 compact reads (decode only; the record's effect work is not timed).
        if(elapsed>stats.worst_decode_us)
            re4dc_log("effect decode: worst %u us (reads %u raw %u records %u)\n",unsigned(elapsed),stats.reads,
                      stats.raw_reads,stats.records);
        else if(!(stats.reads&4095))
            re4dc_log("effect decode: reads %u raw %u worst %u us\n",stats.reads,stats.raw_reads,
                      unsigned(stats.worst_decode_us));
#endif
        if(elapsed>stats.worst_decode_us)stats.worst_decode_us=elapsed;
        return scratch;
    }
    fail("effect record outside live qualified archive");
}
extern "C" void re4dc_effect_get_stats(Re4dcEffectStats* out) { *out=stats; }
