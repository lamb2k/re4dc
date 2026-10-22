#define RE4DC_WORLD_DRAW_METER 1
#include "world_draw_meter.h"
#include "platform/include/native_render_profile.hpp"
#include <cassert>
#include <cstdio>
static unsigned room=0x101, generation=7, reads=0, setting=2;
static uint64_t now=0;
uint64_t timer_us_gettime64() { now+=100; return now; }
extern "C" void re4dc_profile_source(re4dc::profile::Source* out) { *out={};out->room=room; }
extern "C" int re4dc_room4_state(unsigned* gen,unsigned*,unsigned*,unsigned*,unsigned*) { *gen=generation;return 1; }
extern "C" int re4dc_view_dist_get() { return int(setting); }
extern "C" void re4dc_disc_meter_totals(unsigned* r,unsigned long long* bytes,unsigned long long* block) {
    *r=reads;*bytes=0;*block=0;
}
static void frame(unsigned f) {
    re4dc_world_meter_begin(f);
    assert(RE4DC_WORLD_MEASURE(Opaque,12500,1)==1);
    assert(RE4DC_WORLD_MEASURE(FarShell,12500,1)==1);
    assert(RE4DC_WORLD_MEASURE(PunchThrough,25000,1)==1);
    assert(RE4DC_WORLD_MEASURE(Translucent,25000,1)==1);
    if(f==4)++reads;
    re4dc_world_meter_end(f,1);
}
int main() {
    assert(!re4dc_world_meter_snapshot(room).valid);
    for(unsigned f=1;f<=60;++f)frame(f);
    auto s=re4dc_world_meter_snapshot(room);
    assert(s.valid && s.samples==60 && s.mean_us==400 && s.peak_us==400 && s.read_frames==1);
    assert(s.view_setting==2 && s.shell_frames==60 && s.shell_ok_frames==60);
    assert(!re4dc_world_meter_snapshot(0x100).valid);
    setting=1; assert(!re4dc_world_meter_snapshot(room).valid); setting=2;
    ++generation; assert(!re4dc_world_meter_snapshot(room).valid);
    re4dc_world_meter_reset(); assert(!re4dc_world_meter_snapshot(room).valid);
    puts("world meter: actual runtime callbacks, weak source exports, timer calls and frozen identity PASS");
}
