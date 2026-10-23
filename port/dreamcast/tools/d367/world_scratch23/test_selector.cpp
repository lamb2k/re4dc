#include "world_scratch.h"
#include <cassert>
#include <initializer_list>
using namespace re4dc::world_scratch;
volatile Snapshot snap{};
unsigned mode=0x105;
std::uintptr_t owner(){return 1;}
unsigned ccr(){return mode;}
void toggle(bool on){
    // Paused writer at the actual injected hardware-mode change: old C fields
    // must be unobservable as a valid even record even before publish copies.
    assert(snap.seq&1);mode=on?0x125:0x105;
    assert(snap.seq&1);
}
std::uint64_t clock_us(){return 1;}
void reset(){}
alignas(32) unsigned char ram[8192],ocram[8192];
int main(){
Engine engine({owner,ccr,toggle,clock_us,reset,ocram,true});
snapshot_write_begin(snap);assert(engine.admit(1));assert(engine.request(C,1,0x109));assert(engine.begin(0x109));snap.phase=2;snap.actual=C;snap.ccr=mode;snapshot_write_end(snap);
assert(!(snap.seq&1) && snap.actual==C && mode==0x125);
snapshot_write_begin(snap);engine.end(engine.token());
// Engine restored but stale C fields still present: reader MUST reject odd.
assert(mode==0x105 && snap.actual==C && (snap.seq&1));
snap.actual=A;snap.phase=3;snap.ccr=mode;snapshot_write_end(snap);
assert(!(snap.seq&1) && snap.actual==A && snap.ccr==0x105);
for(unsigned m: {0x80U,0x100U,0x200U}){LateChoice c;assert(c.take(false,m)==-1);assert(!c.consumed);assert(c.take(true,m)==(m==0x80U?0:m==0x100U?1:2));assert(c.take(true,m)==-1);}for(unsigned m:{0U,1U,0x20U,0x40U,0x180U,0x300U,0x280U,0x400U,0x81U,~0U}){LateChoice c;assert(c.take(true,m)==(m? -3:-2));assert(c.take(true,0x80U)==-1);}}
