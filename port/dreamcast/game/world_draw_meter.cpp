#include "world_draw_meter.h"
#if defined(RE4DC_WORLD_DRAW_METER) && RE4DC_WORLD_DRAW_METER
#include <arch/timer.h>
#include <arch/irq.h>
#include "platform/include/native_render_profile.hpp"
extern "C" int re4dc_room4_state(unsigned*,unsigned*,unsigned*,unsigned*,unsigned*);
extern "C" void re4dc_disc_meter_totals(unsigned*, unsigned long long*, unsigned long long*) __attribute__((weak));
extern "C" int re4dc_view_dist_get() __attribute__((weak));
namespace {
re4dc::worldmeter::Meter meter;
unsigned active_frame;
unsigned active_token=0;
struct Receipt { unsigned token=0,frame=0; bool ready=false,accepted=false; } receipt;
struct Pending {
    unsigned frame=0,token=0,setting=~0u,reads=0;
    re4dc::worldmeter::Identity id{};
    bool active=false,drawn=false,known=false,stopped=false;
} pending;
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
bool outcome(unsigned token,unsigned frame,bool& accepted) {
    // The presenter may publish concurrently. Keep every receipt field under the
    // same short interrupt exclusion; no Meter state is touched by that thread.
    const int irq=irq_disable(); const Receipt copy=receipt; irq_restore(irq);
    if(!copy.ready || copy.token!=token || copy.frame!=frame)return false;
    accepted=copy.accepted; return true;
}
void settle(bool discard_pending) {
    if(!pending.active)return;
    bool accepted=false;
    if(!outcome(pending.token,pending.frame,accepted) && !discard_pending)return;
    const auto live=identity();
    accepted=accepted && re4dc::worldmeter::same(live,pending.id) && view_setting()==pending.setting;
    meter.end(pending.frame,live,pending.drawn && accepted,pending.known,pending.reads,pending.stopped);
    pending.active=false;
}
}
namespace re4dc { namespace worldmeter {
unsigned clock_us() { return unsigned(timer_us_gettime64()); }
void record(Pass pass, unsigned start, unsigned end, bool ok, float view) {
    meter.pass(active_frame,pass,start,end,ok,unsigned(view));
}
}}
extern "C" void re4dc_world_meter_begin(unsigned frame) {
    // One renderer resolution is outstanding at most. Never wait here; unresolved
    // prior context is rejected before starting a new live accumulator frame.
    settle(true);
    ++active_token; if(!active_token)++active_token;
    active_frame=frame;
    unsigned reads=0; const bool known=disc(reads); bool stopped=false;
    const auto id=identity(&stopped); meter.begin(frame,id,known,reads,stopped,view_setting());
}
extern "C" void re4dc_world_meter_end(unsigned frame, int drawn) {
    unsigned reads=0; const bool known=disc(reads); bool stopped=false;
    const auto id=identity(&stopped);
    if(!drawn) { meter.end(frame,id,false,known,reads,stopped); pending.active=false; return; }
    pending={frame,active_token,view_setting(),reads,id,true,true,known,stopped};
    settle(false);
}
extern "C" unsigned re4dc_world_meter_token() { return active_token; }
extern "C" void re4dc_world_meter_outcome(unsigned token,unsigned frame,int accepted) {
    const int irq=irq_disable();
    // Multiple scene outcomes for one token are ambiguous and fail closed.
    const bool duplicate=receipt.ready && receipt.token==token && receipt.frame==frame;
    receipt={token,frame,true,accepted>0 && !duplicate};
    irq_restore(irq);
}
extern "C" void re4dc_world_meter_reset() {
    meter.reset(); pending.active=false; ++active_token; if(!active_token)++active_token;
}
extern "C" re4dc::worldmeter::Snapshot re4dc_world_meter_snapshot(unsigned room) {
    settle(false);
    const auto id=identity(); return id.room==room?meter.snapshot(id,view_setting()):re4dc::worldmeter::Snapshot{};
}
#endif
