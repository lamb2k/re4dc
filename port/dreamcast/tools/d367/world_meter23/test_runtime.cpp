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
    re4dc_world_meter_outcome(re4dc_world_meter_token(),f,1);
    re4dc_world_meter_end(f,1);
}
static void passes() {
    assert(RE4DC_WORLD_MEASURE(Opaque,12500,1)==1);
    assert(RE4DC_WORLD_MEASURE(FarShell,12500,1)==1);
    assert(RE4DC_WORLD_MEASURE(PunchThrough,25000,1)==1);
    assert(RE4DC_WORLD_MEASURE(Translucent,25000,1)==1);
}
static void fill(unsigned start=1) { for(unsigned f=start;f<start+60;++f)frame(f); }
int main() {
    assert(!re4dc_world_meter_snapshot(room).valid);
    fill();
    auto s=re4dc_world_meter_snapshot(room);
    assert(s.valid && s.samples==60 && s.mean_us==400 && s.peak_us==400 && s.read_frames==1);
    assert(s.view_setting==2 && s.shell_frames==60 && s.shell_ok_frames==60);
    assert(!re4dc_world_meter_snapshot(0x100).valid);
    setting=1; assert(!re4dc_world_meter_snapshot(room).valid); setting=2;
    ++generation; assert(!re4dc_world_meter_snapshot(room).valid);
    re4dc_world_meter_reset(); assert(!re4dc_world_meter_snapshot(room).valid);
    // Callback-before-end, and callback-after-end consumed by snapshot, both seal exactly once.
    fill();
    re4dc_world_meter_begin(61); passes();
    const unsigned delayed=re4dc_world_meter_token();
    re4dc_world_meter_end(61,1); assert(!re4dc_world_meter_snapshot(room).valid);
    re4dc_world_meter_outcome(delayed,61,1);
    assert(re4dc_world_meter_snapshot(room).last==60); // New partial window; old completed stays frozen.
    // Negative pass returns must invalidate despite renderer acceptance.
    re4dc_world_meter_begin(62);
    assert(RE4DC_WORLD_MEASURE(Opaque,12500,-1)==-1);
    assert(RE4DC_WORLD_MEASURE(PunchThrough,25000,1)==1);
    assert(RE4DC_WORLD_MEASURE(Translucent,25000,1)==1);
    re4dc_world_meter_outcome(re4dc_world_meter_token(),62,1);re4dc_world_meter_end(62,1);
    assert(!re4dc_world_meter_snapshot(room).valid);
    // Guard, resolve/queue failure, negative outcome and earlier discard all fail closed.
    for(unsigned kind=0;kind<4;++kind) {
        re4dc_world_meter_reset(); fill(); re4dc_world_meter_begin(61); passes();
        re4dc_world_meter_outcome(re4dc_world_meter_token(),61,kind==3?1:kind==2?-1:0);
        re4dc_world_meter_end(61,kind==3?0:1); assert(!re4dc_world_meter_snapshot(room).valid);
    }
    // Wrong token/frame cannot satisfy a pending frame; next begin rejects unresolved context.
    re4dc_world_meter_reset();fill();re4dc_world_meter_begin(61);passes();
    const unsigned old_token=re4dc_world_meter_token();
    re4dc_world_meter_outcome(old_token,60,1);re4dc_world_meter_end(61,1);
    assert(!re4dc_world_meter_snapshot(room).valid);
    re4dc_world_meter_begin(62);passes();re4dc_world_meter_outcome(old_token,61,1);
    re4dc_world_meter_end(62,1);assert(!re4dc_world_meter_snapshot(room).valid);
    // A late callback after reset cannot revive an abandoned frame, even with the same frame number.
    re4dc_world_meter_reset();re4dc_world_meter_begin(61);passes();
    re4dc_world_meter_outcome(old_token,61,1);re4dc_world_meter_end(61,1);
    assert(!re4dc_world_meter_snapshot(room).valid);
    // Pending readback revalidates room/generation/View after outcome publication.
    for(unsigned change=0;change<3;++change) {
        re4dc_world_meter_reset();fill();re4dc_world_meter_begin(61);passes();
        const unsigned token=re4dc_world_meter_token();re4dc_world_meter_end(61,1);
        if(change==0)++room;else if(change==1)++generation;else setting=1;
        re4dc_world_meter_outcome(token,61,1);assert(!re4dc_world_meter_snapshot(room).valid);
        if(change==0)--room;else if(change==1)--generation;else setting=2;
    }
    // Duplicate completion before seal is ambiguous; after seal it cannot add a second sample.
    re4dc_world_meter_reset();fill();re4dc_world_meter_begin(61);passes();
    unsigned token=re4dc_world_meter_token();
    re4dc_world_meter_outcome(token,61,1);re4dc_world_meter_outcome(token,61,1);
    re4dc_world_meter_end(61,1);assert(!re4dc_world_meter_snapshot(room).valid);
    re4dc_world_meter_reset();fill();token=re4dc_world_meter_token();
    re4dc_world_meter_outcome(token,60,1);assert(re4dc_world_meter_snapshot(room).samples==60);
    puts("world meter: actual callbacks, signed failures, guarded receipts, pending/late/reset/duplicate outcomes and live identity PASS");
}
