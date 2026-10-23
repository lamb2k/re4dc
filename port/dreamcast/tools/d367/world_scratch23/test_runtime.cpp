#include "world_scratch.h"
#include <cassert>
#include <cstdlib>
using namespace re4dc::world_scratch;
unsigned current=1,mode=0x105,mask=0x200;bool opened=true,interleave=false;
extern "C" std::uintptr_t ws_test_owner(){return current;}
extern "C" unsigned ws_test_ccr(){return mode;}
extern "C" std::uint64_t ws_test_clock(){return 1;}
extern "C" void re4dc_log(const char*,...){}
extern "C" void re4dc_world_scratch_prime_reset(){}
extern "C" unsigned re4dc_warp_late(){return opened?mask:0;}
extern "C" int re4dc_warp_late_open(){return opened;}
extern "C" int re4dc_warp_late_set(){return 1;}
extern "C" void ws_test_toggle(bool on){
 auto& s=re4dc_world_scratch_snapshot;assert(s.seq&1);mode=on?0x125:0x105;
 if(interleave){
  const auto seq=s.seq;current=2;
  re4dc_world_scratch_cancel();assert(!re4dc_world_scratch_admit(1));
  assert(!re4dc_world_scratch_request(A,1,0x109));re4dc_world_scratch_begin(0x109);
  alignas(32) unsigned char ram[8192];void* out=nullptr;assert(re4dc_world_scratch_acquire(ram,&out)<0);
  re4dc_world_scratch_release();re4dc_world_scratch_end(1,1);
  assert(s.seq==seq && (s.seq&1));current=1;interleave=false;
 }
 assert(s.seq&1);
}
int main(int argc,char** argv){
 if(argc>1){
  const int arm=std::atoi(argv[1]);
  mask=arm==0?0x80:arm==1?0x100:arm==2?0x200:arm==3?0x180:0;
  auto& s=re4dc_world_scratch_snapshot;
  for(unsigned i=0;i<600;++i){
   re4dc_world_scratch_begin(0x109);
   if(arm<3){
    assert(s.phase==2 && s.actual==unsigned(arm) && s.remaining==600-i);
    assert(mode==(arm?0x125U:0x105U));
    if(i%2==0){alignas(32) unsigned char ram[8192];void* out;assert(re4dc_world_scratch_acquire(ram,&out)>0);re4dc_world_scratch_release();}
   }
   re4dc_world_scratch_end(re4dc_world_scratch_frame_token(),0);
  }
  if(arm<3){assert(s.phase==3 && s.completed && s.restored && s.frames==600 && s.borrows==300 && s.entries==unsigned(arm!=0) && s.exits==s.entries);}
  else assert(mode==0x105 && s.frames==0 && s.phase==unsigned(arm==3?4:0));
  re4dc_world_scratch_begin(0x109);assert(mode==0x105 && !s.remaining);return 0;
 }

 auto& s=re4dc_world_scratch_snapshot;
 // Foreign pre-admission calls cannot claim writer identity or admit at boot.
 current=2;assert(!re4dc_world_scratch_admit(1));assert(!(s.seq&1));current=1;
 re4dc_world_scratch_begin(0x109);assert(mode==0x125 && s.phase==2 && s.actual==C);
 alignas(32) unsigned char ram[8192];void* out=nullptr;assert(re4dc_world_scratch_acquire(ram,&out)>0);
 // Preempt the owner with foreign cancellation while a live borrow remains.
 const auto seq=s.seq;current=2;re4dc_world_scratch_cancel();assert(s.seq==seq && mode==0x125);current=1;
 // Release consumes deferred cancellation under odd and restores only after retire.
 interleave=true;re4dc_world_scratch_release();
 assert(mode==0x105 && !(s.seq&1) && s.actual==A && s.phase==3 && !s.completed && s.restored);
 // An IRQ/deferred cancel cannot reopen the single-use late fixture.
 current=0;re4dc_world_scratch_cancel();current=1;
 re4dc_world_scratch_begin(0x109);assert(mode==0x105 && s.actual==A && s.remaining==0);
}
