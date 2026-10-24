#pragma once
#include "gc_asset_gate.h"
#if RE4DC_GC_ASSET_GATE
namespace re4dc_gcasset {
// One SH4, one tiny caller-supplied IRQ critical section. No new 32-bit atomic
// runtime/library or SH4A-only instruction contract. The host control supplies
// a mutex critical section to exercise concurrent creation/exit requests.
// No wait, allocation, logging, G2 work or catalog access belongs in this state.
template<class Critical> struct AudioStop {
    unsigned state=0;
    enum : unsigned { Stop=1,Reader=2 };
    bool stopped() const { Critical guard;return (state&Stop)!=0; }
    void request() { Critical guard;state|=Stop; }
    bool reader_starting() {
        Critical guard;
        if(state)return false;
        state=Reader;return true;
    }
    void reader_exited() { Critical guard;state&=~Reader; }
    bool reader_idle() const { Critical guard;return (state&Reader)==0; }
};
}
#endif
