#include "world_draw_meter.h"
#if defined(RE4DC_WORLD_DRAW_METER) && RE4DC_WORLD_DRAW_METER
#include <arch/timer.h>
#include "platform/include/native_render_profile.hpp"
extern "C" int re4dc_room4_state(unsigned*,unsigned*,unsigned*,unsigned*,unsigned*);
extern "C" void re4dc_disc_meter_totals(unsigned*, unsigned long long*, unsigned long long*) __attribute__((weak));
extern "C" int re4dc_view_dist_get() __attribute__((weak));
namespace {
re4dc::worldmeter::Meter meter;
unsigned active_frame;
unsigned view_setting() { return re4dc_view_dist_get?unsigned(re4dc_view_dist_get()):~0u; }
re4dc::worldmeter::Identity identity(bool* stopped=nullptr) {
    re4dc::profile::Source source{}; re4dc_profile_source(&source);
    unsigned generation=0,c=0,b=0,s=0,r=0;
    re4dc_room4_state(&generation,&c,&b,&s,&r);
    if(stopped)*stopped=source.stop!=0;
    return {source.room,generation};
}
bool disc(unsigned& reads) {
    reads=0;
    if(!re4dc_disc_meter_totals)return false;
    unsigned long long bytes=0,blocked=0;
    re4dc_disc_meter_totals(&reads,&bytes,&blocked); return true;
}
}
namespace re4dc { namespace worldmeter {
unsigned clock_us() { return unsigned(timer_us_gettime64()); }
void record(Pass pass, unsigned start, unsigned end, bool ok, float view) {
    meter.pass(active_frame,pass,start,end,ok,unsigned(view));
}
}}
extern "C" void re4dc_world_meter_begin(unsigned frame) {
    active_frame=frame;
    unsigned reads=0; const bool known=disc(reads); bool stopped=false;
    const auto id=identity(&stopped); meter.begin(frame,id,known,reads,stopped,view_setting());
}
extern "C" void re4dc_world_meter_end(unsigned frame, int drawn) {
    unsigned reads=0; const bool known=disc(reads); bool stopped=false;
    const auto id=identity(&stopped); meter.end(frame,id,drawn!=0,known,reads,stopped);
}
extern "C" void re4dc_world_meter_reset() { meter.reset(); }
extern "C" re4dc::worldmeter::Snapshot re4dc_world_meter_snapshot(unsigned room) {
    const auto id=identity(); return id.room==room?meter.snapshot(id,view_setting()):re4dc::worldmeter::Snapshot{};
}
#endif
