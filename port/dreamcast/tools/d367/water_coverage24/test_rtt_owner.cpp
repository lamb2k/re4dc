#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <cstdio>
#define RE4DC_WATER_R100_MATERIAL 1
#define RE4DC_UI_HANDLES 1
#define RE4DC_PVR_RTT_STATS 0
#include "water24_material.hpp"
using pvr_ptr_t=void*;
unsigned frame=10,waits=0,allocs=0,frees=0;
bool good_context=true,good_entry=true,good_fence=true,fail_begin=false;
constexpr unsigned kSpritePacket=96,PVR_RAM_SIZE=8*1024*1024;
enum { PVR_LIST_TR_POLY=2,PVR_FB_CFG_2=0 };
unsigned registers[1];
#define PVR_GET(x) registers[x]
#define PVR_SET(x,y) (registers[x]=(y))
struct {unsigned bg_color;} pvr_state;
struct Entry{} entry;
struct Image{};
struct Re4dcEffectSprite {Image image;unsigned color=0xffffffff;float x[4]{},y[4]{};unsigned screen=0;};
Entry* resolve(const Image&,void*,bool){return &entry;}
void fx_packet(const Re4dcEffectSprite&,Entry*,unsigned char*){}
void re4dc_log(const char*,...){}
void* pvr_mem_malloc(unsigned n){++allocs;return std::malloc(n);}
void pvr_mem_free(void* p){++frees;std::free(p);}
void pvr_wait_render_done(){++waits;}
int pvr_scene_begin_rtt(void*,unsigned,unsigned,unsigned){return fail_begin?-1:0;}
int pvr_list_begin(unsigned){return 0;}
void pvr_scene_finish(){} void pvr_list_finish(){} void pvr_prim(void*,unsigned){}
void present_fence(){}
std::uint64_t timer_us_gettime64(){return 0;}
int geom=0,proof=0,source=0,receipt=0;
re4dc::water24::CaptureContext context{};
extern "C" int re4dc_water24_capture_context(unsigned slot,re4dc::water24::CaptureContext* out){
 if(!good_context || slot!=0){*out={};return 0;}*out=context;return 1;
}
extern "C" int re4dc_water24_capture_contributor(const void*,const re4dc::water24::CaptureContext*){return good_entry;}
extern "C" int re4dc_water24_capture_fence_ok(){return waits && good_fence;}
#include "pvr_rtt.inc"
unsigned checks=0;
#define CHECK(x) do{++checks;if(!(x)){std::printf("failed line %u\n",__LINE__);return 1;}}while(0)
void capture(){Re4dcEffectSprite sprite{};re4dc_rtt_capture_begin(0,64,64,128,128,0);rtt::capture(&sprite);re4dc_rtt_capture_end();re4dc_rtt_want(0);}
int main(){
 using namespace re4dc::water24; (void)rtt::wanted(0);(void)rtt::pending_count;(void)rtt::pending_mask;
 context.room=kRoom;context.geometry.owner=&geom;context.geometry.proof=&proof;context.geometry.generation=3;context.geometry.room_generation=7;
 context.geometry.bytes=kMeshBytes;context.geometry.mesh_crc=kMeshCrc;context.geometry.policy_crc=kPolicyCrc;context.geometry.ids_policy_crc=kIdsPolicyCrc;
 context.source_target=&source;context.slot=0;context.contributor_receipt=&receipt;context.receipt_serial=19;
 Request request{};request.geometry=context.geometry;request.source_object=&source;request.source_serial=1;request.room=kRoom;request.source_id=0;request.placement=request.mesh=request.part=0;
 capture();CHECK(allocs==1);frame=11;request.native_frame=frame;re4dc_rtt_render_pending();CHECK(waits==1);
 Target token{};CHECK(re4dc_water24_rtt_target(0,&request,&token));CHECK(re4dc_water24_rtt_current(&token));CHECK(token.capture_frame==10 && token.render_frame==11 && token.fence);
 capture();CHECK(allocs==1);CHECK(re4dc_water24_rtt_current(&token));
 {Target bad=token;bad.slot=1;CHECK(!re4dc_water24_rtt_current(&bad));bad=token;bad.source_target=&geom;CHECK(!re4dc_water24_rtt_current(&bad));bad=token;bad.fence++;CHECK(!re4dc_water24_rtt_current(&bad));}
 good_fence=false;CHECK(!re4dc_water24_rtt_current(&token));good_fence=true;
 frame=12;request.native_frame=frame;re4dc_rtt_render_pending();CHECK(waits==2);CHECK(!re4dc_water24_rtt_current(&token));CHECK(re4dc_water24_rtt_target(0,&request,&token));
 // Refused contributor taints this complete target; no positive receipt may publish.
 good_entry=false;capture();good_entry=true;frame=13;request.native_frame=frame;re4dc_rtt_render_pending();CHECK(waits==3);CHECK(!re4dc_water24_rtt_target(0,&request,&token));CHECK(!token.texture);
 capture();frame=14;request.native_frame=frame;fail_begin=true;re4dc_rtt_render_pending();CHECK(waits==3);CHECK(!re4dc_water24_rtt_target(0,&request,&token));fail_begin=false;
 capture();frame=15;request.native_frame=frame;re4dc_rtt_render_pending();CHECK(re4dc_water24_rtt_target(0,&request,&token));
 good_context=false;CHECK(!re4dc_water24_rtt_current(&token));good_context=true;
 context.geometry.room_generation++;CHECK(!re4dc_water24_rtt_current(&token));context.geometry.room_generation--;
 re4dc_rtt_capture_begin(0,128,64,256,128,0);CHECK(frees==1);CHECK(!re4dc_water24_rtt_current(&token));re4dc_rtt_capture_end();
 re4dc_rtt_room_reset();CHECK(!re4dc_water24_rtt_current(&token));
 frame=16;capture();frame=17;request.native_frame=frame;re4dc_rtt_render_pending();CHECK(re4dc_water24_rtt_target(0,&request,&token));CHECK(allocs==2);
 rtt::water_epochs.value=~0U;re4dc_rtt_room_reset();CHECK(rtt::water_epochs.exhausted);CHECK(!re4dc_water24_rtt_current(&token));
 std::printf("{\"actual_pvr_include_controls\":%u,\"existing_waits\":%u,\"allocs\":%u,\"frees\":%u}\n",checks,waits,allocs,frees);
}
