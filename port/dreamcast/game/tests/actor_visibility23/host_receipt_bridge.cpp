#include "actor_visibility23_world.h"
#include "room_file.h"
#include <cstdint>
#define RE4DC_PVR_STREAM 1
static bool frame_ready=true,stream_aborted=false,stream_scene=true;
static unsigned actor_world_scene23_epoch=42,host_mode23=0;
static unsigned actor_world23_mode(){return host_mode23;}
extern "C" unsigned re4dc_ui_frame();
extern "C" int re4dc_ps2_placements_intact(unsigned,const unsigned char*,unsigned);
static int storage;
static struct {unsigned room=0x119;void* storage=&::storage;} ps2w;
static unsigned enemyVisSidecarCrc=0xfb5072f8;
static actor_visibility23::WorldReceipt actor_world23;
#include "ui_ready_actual.inc"
#include "world_ready_actual.inc"
extern "C" void host_receipt_begin(const float* v,const float* P,const float* V){
 actor_world23.bind(ps2w.storage,true);actor_world23.begin(re4dc_ui_frame(),v,P,V);
 unsigned bytes=0,version=0,flags=0;const re4dc_room_header* h=nullptr;
 actor_world23.metadata=re4dc_room_section("OCCL",&bytes,&version,&flags,&h);
}
extern "C" void host_receipt_emit(unsigned field,unsigned part,unsigned let,const unsigned char* strips,unsigned bytes,const unsigned char* codes,unsigned nv,unsigned limit){
 actor_world23.emit(field,part,let,strips,bytes,codes,nv,limit,3,60,50,25000,re4dc_actor_world23_scene(),host_mode23);
}
extern "C" void host_receipt_end(unsigned success){actor_world23.end(success);}
extern "C" void host_receipt_frame_state(unsigned ready,unsigned aborted){frame_ready=ready;stream_aborted=aborted;}
extern "C" void host_receipt_close(){actor_world23.close();}

extern "C" void host_receipt_scene_state(unsigned active,unsigned epoch){stream_scene=active;actor_world_scene23_epoch=epoch;}

extern "C" void host_receipt_mode(unsigned mode){host_mode23=mode;}
