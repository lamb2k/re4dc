
#include "actor_visibility23.h"
#include "actor_visibility23_window.h"
#include "actor_visibility23_world.h"
#include "room_file.h"
#include <cassert>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <vector>
struct State {bool has_late=true,late_logged=false;unsigned late_room=0x119,late_tick=100,late_mask=0;} wp;
struct Global {unsigned room_id=0x119,Frame_cnt=100;} game,*pG=&game;
static int source;
static struct {unsigned room=0;void* storage=nullptr;void* parts=nullptr;} ps2w;
static actor_visibility23::WorldReceipt actor_world23;
static unsigned enemyVisSidecarCrc=0xfb5072f8,metadata_room=0x119,version=2,bytes=1376;
static re4dc_room_header header={136,33,1000,-2000,-10000};
static std::vector<unsigned char> blob;static bool section=true;
extern "C" unsigned re4dc_room_file_room(){return metadata_room;}
extern "C" const void* re4dc_room_section(const char*,unsigned* b,unsigned* v,unsigned* f,const re4dc_room_header** h){*b=bytes;*v=version;*f=0;*h=&header;return section?blob.data():nullptr;}
static Re4dcActorVisibility23Stats stats{};
extern "C" unsigned re4dc_actor_visibility23_mode=0;
extern "C" void re4dc_log(const char*,...){}
extern "C" const Re4dcActorVisibility23Stats* re4dc_actor_visibility23_stats(){return &stats;}
extern "C" void re4dc_actor_visibility23_reset(){++stats.resets;}
#include "actual_readiness.inc"
static void loaded(unsigned room=0x119){ps2w.room=room;ps2w.storage=&source;ps2w.parts=&source;actor_world23.bind(&source,true);}
static void bind(unsigned n,unsigned funded=1){re4dc_actor_visibility23_bind(n,funded,n*10);}
int main(int argc,char** argv){
 assert(argc==4);std::ifstream f(argv[1],std::ios::binary);blob={std::istreambuf_iterator<char>(f),{}};assert(blob.size()==1376);
 wp.late_mask=std::strtoul(argv[2],nullptr,0);const unsigned expected=wp.late_mask==32?1:wp.late_mask==64?2:0;
 const unsigned scenario=std::strtoul(argv[3],nullptr,0);
 // The actual neutral getter is read-only, including absent/null/wrong room/ticks.
 wp.has_late=false;assert(!re4dc_warp_late_room());wp.has_late=true;pG=nullptr;assert(!re4dc_warp_late_room());pG=&game;
 game.room_id=0;assert(!re4dc_warp_late_room());game.room_id=0x119;game.Frame_cnt=99;assert(!re4dc_warp_late_room());game.Frame_cnt=100;assert(re4dc_warp_late_room()==0x119&&!wp.late_logged);
 // Execute actual wrapper+context, not a duplicate admission predicate.
 bind(1);assert(!fixture23.spent);loaded(0x101);bind(2);assert(!fixture23.spent);
 loaded();metadata_room=0x101;bind(3);assert(!fixture23.spent);metadata_room=0x119;
 bind(4,0);assert(!fixture23.spent);ps2w.parts=nullptr;bind(5);assert(!fixture23.spent);ps2w.parts=&source;
 actor_world23.owner=false;bind(6);assert(!fixture23.spent);actor_world23.owner=true;
 enemyVisSidecarCrc=1;bind(7);assert(!fixture23.spent);enemyVisSidecarCrc=0xfb5072f8;
 section=false;bind(8);assert(!fixture23.spent);section=true;
 version=1;bind(9);assert(!fixture23.spent);version=2;bytes=1375;bind(10);assert(!fixture23.spent);bytes=1376;
 header.w=135;bind(11);assert(!fixture23.spent);header.w=136;
 blob[100]^=1;bind(12);assert(!fixture23.spent&&stats.metadata_checks==1&&stats.metadata_bytes==1376);blob[100]^=1;
 // No completed wall pass, camera cell or actor cut is required to start any arm.
 assert(!actor_world23.complete);bind(13);assert(fixture23.spent&&re4dc_actor_visibility23_mode==expected);
 if(wp.late_mask&~0x60U || (wp.late_mask&0x60U)==0x60U){assert(!fixture23.active);const auto scans=stats.metadata_checks;wp.late_mask=64;bind(14);assert(!fixture23.active&&stats.metadata_checks==scans);return 0;}
 assert(fixture23.active&&fixture23.frames==1);const auto scans=stats.metadata_checks;bind(13);assert(fixture23.frames==1);
 // Repeated serial must neither report nor rehash admission.
 assert(stats.metadata_checks==scans);
 if(scenario){
  switch(scenario){case 1:ps2w.room=0;break;case 2:ps2w.room=0x101;break;case 3:metadata_room=0;break;case 4:blob[100]^=1;break;case 5:game.room_id=0x101;break;case 6:break;case 7:wp.late_mask=32;break;case 8:actor_world23.close();break;}
  bind(14,scenario!=6);assert(!fixture23.active&&!re4dc_actor_visibility23_mode);loaded();metadata_room=0x119;game.room_id=0x119;
  const auto stop=stats.metadata_checks;bind(15);assert(!fixture23.active&&stats.metadata_checks==stop);
 }else{
  for(unsigned n=14;n<=612;n++)bind(n);assert(fixture23.frames==600&&fixture23.active);bind(613);assert(!fixture23.active&&!re4dc_actor_visibility23_mode);
  const auto stop=stats.metadata_checks;bind(614);assert(stats.metadata_checks==stop&&!fixture23.active);
 }
 std::printf("actual wrapper/context PASS mask=%u scenario=%u scans=%u bytes=%u\n",wp.late_mask,scenario,stats.metadata_checks,stats.metadata_bytes);
}
