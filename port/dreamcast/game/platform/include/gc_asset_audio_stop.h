#pragma once
#include "gc_asset_gate.h"
#if RE4DC_GC_ASSET_GATE
namespace re4dc_gcasset {
// Terminal-only stop, not a room handoff. Audio callback admission is serialized
// by its existing mutex. Reader creation and stop use one atomic word so stop
// cannot report idle in the gap before a detached reader starts. Only the real
// reader exit, after its last disc/G2 operation, releases the reader bit.
// No allocation, logging, waits or catalog access belongs in this state.
struct AudioStop {
    unsigned state = 0;
    enum : unsigned { Stop = 1, Reader = 2 };
    bool stopped() const { return (__atomic_load_n(&state, __ATOMIC_ACQUIRE)&Stop)!=0; }
    void request() { __atomic_fetch_or(&state, Stop, __ATOMIC_ACQ_REL); }
    bool reader_starting() {
        unsigned expected=0;
        return __atomic_compare_exchange_n(&state,&expected,Reader,false,__ATOMIC_ACQ_REL,__ATOMIC_ACQUIRE);
    }
    void reader_exited() { __atomic_fetch_and(&state, ~Reader, __ATOMIC_RELEASE); }
    bool reader_idle() const { return (__atomic_load_n(&state, __ATOMIC_ACQUIRE)&Reader)==0; }
};
static_assert(sizeof(AudioStop)==4,"price terminal audio state explicitly");
}
#endif
