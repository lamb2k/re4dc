#include "world_scratch.h"
#include <cassert>
#include <cstdlib>
#include <cstring>
#include <initializer_list>
using namespace re4dc::world_scratch;
unsigned current=1,mode=0x105,mask=0x200,game_room=0x109;bool opened=true,interleave=false;
std::uint64_t clock_ticks=0;
extern "C" std::uintptr_t ws_test_owner(){return current;}
extern "C" unsigned ws_test_ccr(){return mode;}
extern "C" std::uint64_t ws_test_clock(){return clock_ticks;}
extern "C" void re4dc_log(const char*,...){}
extern "C" void re4dc_world_scratch_prime_reset(){}
extern "C" unsigned re4dc_warp_late(){return opened?mask:0;}
extern "C" int re4dc_warp_late_open(){return opened;}
extern "C" unsigned re4dc_warp_late_room(){return opened?game_room:0;}
extern "C" int re4dc_warp_late_set(){return 1;}
extern "C" void ws_test_toggle(bool on){
 auto& s=re4dc_world_scratch_snapshot;assert(s.seq&1);clock_ticks+=7;mode=on?0x125:0x105;
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
 if(argc>1 && !std::strncmp(argv[1],"meter-",6)){
  const auto scenario=argv[1]+6;
  const unsigned arm=!std::strcmp(scenario,"A")?A:!std::strcmp(scenario,"B")?B:C;
  mask=arm==A?0x80:arm==B?0x100:0x200;
  std::uint64_t total=0,draw=0,skip=0,maximum=0;
  clock_ticks=0x100000000ULL; // absolute timer crosses32bits; totals are separate64bit values
  for(unsigned i=0;i<600;++i){
   const bool skipped=(i&1)!=0;
   re4dc_world_scratch_boundary(skipped,0x109);
   re4dc_world_scratch_begin(0x109);
   assert(re4dc_world_scratch_snapshot.actual==arm && mode==(arm==A?0x105U:0x125U));
   const unsigned work=1000+i%3;
   clock_ticks+=work;
   if(!skipped){alignas(32) unsigned char ram[8192];void* out;assert(re4dc_world_scratch_acquire(ram,&out)>0);re4dc_world_scratch_release();}
   if(i==599 && !std::strcmp(scenario,"borrow")){alignas(32) static unsigned char held[8192];void* out;assert(re4dc_world_scratch_acquire(held,&out)>0);}
   re4dc_world_scratch_end(re4dc_world_scratch_frame_token(),0);
   clock_ticks+=500; // work/waits AFTER end-guard restore must not disappear
   const std::uint64_t period=work+500+(arm!=A && i==0?7:0)+(arm!=A && i==599?7:0);
   total+=period;if(skipped)skip+=period;else draw+=period;if(period>maximum)maximum=period;
  }
  MeterSnapshot s{};assert(re4dc_world_scratch_meter_read(&s));
  if(!std::strcmp(scenario,"borrow")){
   assert(s.phase==4 && !s.complete && s.faults && mode==0x125);
   re4dc_world_scratch_release();assert(mode==0x105);
   re4dc_world_scratch_boundary(0,0x109);assert(re4dc_world_scratch_meter_read(&s) && s.phase==4 && !s.complete);return 0;
  }
  assert(s.phase==2 && !s.complete && s.periods==599 && s.engine_frames==600 && s.restored && s.arm==arm);
  assert(re4dc_world_scratch_snapshot.completed && mode==0x105); // old ABI is runtime completion, not whole-period completion
  if(!std::strcmp(scenario,"cancel"))re4dc_world_scratch_cancel();
  if(!std::strcmp(scenario,"owner")){current=2;re4dc_world_scratch_boundary(0,0x109);current=1;}
  if(!std::strcmp(scenario,"mode"))mode=0x185;
  re4dc_world_scratch_boundary(0,!std::strcmp(scenario,"room")?0x101:0x109);
  assert(re4dc_world_scratch_meter_read(&s));
  if(!std::strcmp(scenario,"cancel") || !std::strcmp(scenario,"owner") || !std::strcmp(scenario,"room") || !std::strcmp(scenario,"mode")){
   assert(s.phase==4 && !s.complete);return 0;
  }
  auto us=[](unsigned lo,unsigned hi){return (std::uint64_t(hi)<<32)|lo;};
  assert(s.phase==3 && s.complete && s.periods==600 && s.drawn==300 && s.skipped==300 && s.arm==arm);
  assert(s.borrows==300 && !s.faults && s.restored && s.ccr==0x105);
  assert(us(s.wall_us_lo,s.wall_us_hi)==total && us(s.draw_us_lo,s.draw_us_hi)==draw && us(s.skip_us_lo,s.skip_us_hi)==skip);
  assert(total==draw+skip && us(s.max_us_lo,s.max_us_hi)==maximum);
  assert(us(s.enter_us_lo,s.enter_us_hi)==unsigned(arm!=A)*7 && us(s.exit_us_lo,s.exit_us_hi)==unsigned(arm!=A)*7);
  const auto completed=s;
  clock_ticks+=99999;re4dc_world_scratch_boundary(0,0x101);re4dc_world_scratch_cancel();
  assert(re4dc_world_scratch_meter_read(&s) && !std::memcmp(&s,&completed,sizeof(s))); // later ordinary A is never relabelled active C
  auto& record=re4dc_world_scratch_meter_snapshot;const unsigned seq=record.seq;record.seq=seq|1U;
  assert(!re4dc_world_scratch_meter_read(&s));record.seq=seq;assert(!re4dc_world_scratch_meter_read(nullptr));
  return 0;
 }
 if(argc>1 && !std::strcmp(argv[1],"admit")){
  auto& s=re4dc_world_scratch_snapshot;mode=0x185;
  re4dc_world_scratch_begin(0);assert(!s.faults && s.phase==0);
  re4dc_world_scratch_begin(0x109);assert(s.faults && s.phase==4 && !s.frames);
  // A real refusal remains consumed even after the hardware mode becomes valid.
  mode=0x105;re4dc_world_scratch_begin(0x109);assert(s.phase==4 && !s.remaining && !s.frames);return 0;
 }
 if(argc>1 && !std::strcmp(argv[1],"stale")){
  auto& s=re4dc_world_scratch_snapshot;
  re4dc_world_scratch_begin(0x109);assert(s.actual==C && s.remaining==600);
  re4dc_world_scratch_end(re4dc_world_scratch_frame_token(),0);
  // After real activation, stale room is a fault/cancel, never a retry.
  re4dc_world_scratch_begin(0x101);
  assert(mode==0x105 && s.actual==A && s.faults && !s.remaining && !s.completed && s.restored);
  re4dc_world_scratch_begin(0x109);assert(s.actual==A && !s.remaining && s.frames==1);return 0;
 }
 if(argc>1){
  const int arm=std::atoi(argv[1]);
  mask=arm==0?0x80:arm==1?0x100:arm==2?0x200:arm==3?0x180:0;
  auto& s=re4dc_world_scratch_snapshot;
  // Reproduce real boot: open late window but no loaded world, then a stale
  // nonzero mesh. Neither may consume, admit, fault, refuse or count a frame.
  for(unsigned room:{0U,0x101U,0U}){
   re4dc_world_scratch_begin(room);assert(s.phase==0 && !s.window_serial && !s.faults && !s.frames && mode==0x105);
   re4dc_world_scratch_end(re4dc_world_scratch_frame_token(),0);
  }
  opened=false;re4dc_world_scratch_begin(0x109);assert(s.phase==0 && !s.faults);opened=true;
  for(unsigned i=0;i<600;++i){
   re4dc_world_scratch_begin(0x109);
   if(arm<3){
    assert(s.phase==2 && s.actual==unsigned(arm) && s.remaining==600-i);
    assert(mode==(arm?0x125U:0x105U));
    if(i%2==0){alignas(32) unsigned char ram[8192];void* out;assert(re4dc_world_scratch_acquire(ram,&out)>0);re4dc_world_scratch_release();}
   }
   re4dc_world_scratch_end(re4dc_world_scratch_frame_token(),0);
   if(i==0 && arm>=3)mask=0x200; // refusal/OFF cannot rearm if a caller changes the mask
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
