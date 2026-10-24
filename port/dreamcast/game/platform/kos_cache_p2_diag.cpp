#include "include/kos_cache_p2_diag.h"
#if RE4DC_KOS_CACHE_P2_DIAG
#include <kos/irq.h>
#include <kos/cache.h>
#include <stddef.h>
#include <stdint.h>
extern "C" void re4dc_log(const char*, ...);
extern "C" {
// All accesses after startup are via P2. Do not initialize/write this via P1.
alignas(32) volatile Re4dcCacheP2Counters re4dc_cache_p2_diag_counters;
}
static_assert(sizeof(Re4dcCacheP2Counters)==64, "cache diag isolated lines");
static_assert(offsetof(Re4dcCacheP2Counters,full512)==32, "assembly layout");
static_assert(offsetof(Re4dcCacheP2Counters,overflow)==28, "assembly layout");
namespace {
unsigned active_room=0xffff, phase=0, sequence=0, hook_reject=0;
bool startup_coherent=false;
// phase 0=boot,1=live room,2=unattributed transition. No loading guess.
const char* const phases[]={"boot","live","transition"};
volatile Re4dcCacheP2Counters* counters(){
#if defined(RE4DC_CACHE_DIAG_HOST_TEST)
    return &re4dc_cache_p2_diag_counters;
#else
    return reinterpret_cast<volatile Re4dcCacheP2Counters*>(
        reinterpret_cast<uintptr_t>(&re4dc_cache_p2_diag_counters)|uintptr_t(0xa0000000));
#endif
}
void report(unsigned frame,unsigned next_room,unsigned next_phase){
    Re4dcCacheP2Counters copy{};
    const auto saved=irq_disable();
    // A future unsafe hook must not log while its caller already masks IRQs.
    if(unsigned(saved)&0x100000f0U){++hook_reject;irq_restore(saved);return;}
    if(!startup_coherent){
        // KOS zeroes BSS through P1 after cache enable. First P2 snapshot
        // must see those zeros even if no whole helper has run yet.
        // 64B aligned range uses two OCBWB lines, never the whole helper.
        // If a helper already ran, the P1 alias is clean: P2 counts survive.
        dcache_wback_range(reinterpret_cast<uintptr_t>(&re4dc_cache_p2_diag_counters),
                           sizeof(re4dc_cache_p2_diag_counters));
        startup_coherent=true;
    }
    volatile uint32_t* in=reinterpret_cast<volatile uint32_t*>(counters());
    uint32_t* out=reinterpret_cast<uint32_t*>(&copy);
    for(unsigned i=0;i<sizeof(copy)/4;++i){out[i]=in[i];in[i]=0;}
    const unsigned room=active_room, old_phase=phase, seq=++sequence, bad_hook=hook_reject;
    active_room=next_room;phase=next_phase;
    irq_restore(saved);
    // Formatting/logging only after restoring the caller's unmasked SR.
    re4dc_log("cachep2diag room=%04x phase=%s seq=%u frame=%u calls=%u timed=%u rejected=%u unavailable=%u overflow=%x hook_reject=%u\n",
        room,phases[old_phase],seq,frame,copy.calls,copy.timed,copy.rejected,copy.unavailable,copy.overflow,bad_hook);
    const uint64_t capacity=uint64_t(copy.full512)*16384+uint64_t(copy.ram256)*8192;
    re4dc_log("cachep2diag time room=%04x seq=%u ticks=%08x:%08x max=%u full512=%u ram256=%u capacity=%08x:%08x\n",
        room,seq,copy.total_hi,copy.total_lo,copy.max_ticks,copy.full512,copy.ram256,unsigned(capacity>>32),unsigned(capacity));
}
}
extern "C" void re4dc_cache_p2_diag_enter(unsigned room){report(0,room,1);}
extern "C" void re4dc_cache_p2_diag_leave(unsigned room){
    if(phase==1 && room!=active_room)++hook_reject;
    report(0,0xffff,2);
}
extern "C" void re4dc_cache_p2_diag_poll(unsigned room,unsigned frame){
    if(frame%150!=0)return;
    if(phase!=1 || room!=active_room){++hook_reject;report(frame,0xffff,2);return;}
    report(frame,room,1);
}
#endif
