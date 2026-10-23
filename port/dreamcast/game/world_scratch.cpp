#include "world_scratch.h"
#if RE4DC_WORLD_SCRATCH
namespace re4dc { namespace world_scratch {
// CCR stable bits. OCI/ICI self-clearing invalidate commands are not state.
constexpr unsigned kOra=1U<<5,kOix=1U<<7,kNormal=(1U<<0)|(1U<<2)|(1U<<8);
constexpr unsigned kStable=(1U<<0)|(1U<<1)|(1U<<2)|kOra|kOix|(1U<<8)|(1U<<15);
bool Engine::reject(Fault why){++st.faults;st.last_fault=why;return false;}
bool Engine::expected() const {return (op.ccr()&kStable)==(saved|(changed?kOra:0));}
bool Engine::admit(unsigned receipt_version){
    if(window || frame || users)return reject(LiveConsumer);
    if(receipt_version!=1)return reject(NotAdmitted);
    if(!op.layout || !op.ocram || (reinterpret_cast<std::uintptr_t>(op.ocram)&31U))return reject(BadLayout);
    if((op.ccr()&kStable)!=kNormal)return reject(BadMode);
    thread=op.owner();if(!thread)return reject(WrongOwner);
    admitted=true;return true;
}
bool Engine::request(unsigned arm,unsigned iterations,unsigned target_room){
    if(!admitted)return reject(NotAdmitted);
    if(op.owner()!=thread)return reject(WrongOwner);
    if(arm>C || !iterations || iterations>kMaxWindow || !target_room)return reject(BadRequest);
    pending=true;pending_arm=arm;pending_frames=iterations;pending_room=target_room;st.requested=arm;
    return true; // no cache transition, even inside a live consumer
}
void Engine::finish(){
    if(!closing || users || frame || op.owner()!=thread)return;
    // Never overwrite a foreign CCR change, in any arm. Revoke admission.
    if(!expected()){reject(BadMode);admitted=false;}
    else if(changed){
        const auto t=op.clock();op.toggle(false);st.exit_us+=op.clock()-t;++st.exits;
        if((op.ccr()&kStable)!=saved){reject(BadMode);admitted=false;}
    }
    changed=false;window=false;closing=false;st.actual=admitted?A:3U;st.remaining=0;
    last_storage=nullptr;++st.epoch;op.reset_prime();
}
bool Engine::begin(unsigned current_room){
    if(!admitted)return false;
    if(op.owner()!=thread){reject(WrongOwner);cancel();return false;}
    if(frame){reject(BadFrame);cancel();return false;}
    if(closing){finish();if(!admitted)return false;}
    if(window && (!expected() || room!=current_room)){
        reject(room!=current_room?StaleRoom:BadMode);cancel();return false;
    }
    if(pending){
        if(users){reject(LiveConsumer);return false;}
        closing=window;finish();
        if(!admitted)return false;
        if(pending_room!=current_room){pending=false;return reject(StaleRoom);}
        if((op.ccr()&kStable)!=kNormal){pending=false;return reject(BadMode);}
        saved=op.ccr()&kStable;room=current_room;window=true;closing=false;
        st.actual=pending_arm;st.remaining=pending_frames;pending=false;
        if(st.actual!=A){const auto t=op.clock();op.toggle(true);st.enter_us+=op.clock()-t;++st.entries;changed=true;
            if(!expected()){reject(BadMode);cancel();return false;}}
        last_storage=nullptr;++st.epoch;op.reset_prime();
    }
    if(!window || closing)return false;
    frame=true;if(!++serial)++serial;frame_id=serial;return true;
}
void Engine::end(unsigned token,bool aborted){
    if(token && (!frame || frame_id!=token)){if(frame)reject(BadFrame);return;}
    if(aborted){cancel();return;}
    if(!frame){finish();return;}
    if(op.owner()!=thread){reject(WrongOwner);return;}
    frame=false;++st.frames;
    if(users){reject(LiveConsumer);closing=true;pending=false;}
    if(st.remaining && !--st.remaining)closing=true;
    finish();
}
void Engine::cancel(){
    pending=false;
    if(window){closing=true;frame=false;finish();}
}
int Engine::acquire(void* ram,void*& projected){
    projected=ram;
    if(!window)return 0;
    if(op.owner()!=thread){reject(WrongOwner);return -1;}
    if(!frame || closing){reject(BadFrame);return -1;}
    if(!expected()){reject(BadMode);closing=true;return -1;}
    if(users){reject(LiveConsumer);return -1;} // no nested or reentrant OCRAM / tail alias
    if(!ram || (reinterpret_cast<std::uintptr_t>(ram)&31U)){reject(BadLayout);return -1;}
    projected=st.actual==C?op.ocram:ram;
    if(projected!=last_storage){last_storage=projected;++st.epoch;op.reset_prime();}
    ++users;++st.borrows;return 1;
}
void Engine::release(){
    if(!users){reject(LiveConsumer);return;}
    if(op.owner()!=thread){reject(WrongOwner);return;}
    --users;finish();
}
}}
#ifndef RE4DC_WORLD_SCRATCH_HOST
#if !defined(RE4DC_WORLD_SCRATCH_RUNTIME_TEST)
#include <kos/thread.h>
#include <kos/irq.h>
#include <dc/cache.h>
#include <arch/timer.h>
#else
#define __ocram
extern "C" std::uintptr_t ws_test_owner();
extern "C" unsigned ws_test_ccr();
extern "C" void ws_test_toggle(bool);
extern "C" std::uint64_t ws_test_clock();
#endif
#include "platform/include/warp_late.h"
extern "C" void re4dc_log(const char*,...);
extern "C" void re4dc_world_scratch_prime_reset();
namespace {
// Occupy the complete KOS section. Another linked OCRAM allocation overflows
// its 8192-byte linker bound instead of silently sharing this array.
__ocram alignas(32) unsigned char projected_records[re4dc::world_scratch::kVertexBytes];
#if !defined(RE4DC_WORLD_SCRATCH_RUNTIME_TEST)
std::uintptr_t owner(){return irq_inside_int()?0:reinterpret_cast<std::uintptr_t>(thd_get_current());}
unsigned ccr(){return *reinterpret_cast<volatile unsigned*>(0xff00001cU);}
void toggle(bool on){dcache_toggle_ocram(on);}
std::uint64_t clock_us(){return timer_us_gettime64();}
#else
std::uintptr_t owner(){return ws_test_owner();}
unsigned ccr(){return ws_test_ccr();}
void toggle(bool on){ws_test_toggle(on);}
std::uint64_t clock_us(){return ws_test_clock();}
#endif
re4dc::world_scratch::Engine engine({owner,ccr,toggle,clock_us,re4dc_world_scratch_prime_reset,projected_records,
#if !defined(RE4DC_WORLD_SCRATCH_RUNTIME_TEST)
    reinterpret_cast<std::uintptr_t>(projected_records)==0x7c001000U && sizeof(projected_records)==8192
#else
    true
#endif
});
}
extern "C" {
volatile re4dc::world_scratch::Snapshot re4dc_world_scratch_snapshot{};
volatile re4dc::world_scratch::MeterSnapshot re4dc_world_scratch_meter_snapshot{};
volatile unsigned re4dc_world_scratch_live;
}
namespace {
using namespace re4dc::world_scratch;
LateChoice late_choice;
FrameMeter frame_meter;
bool meter_complete_published=false,meter_logged=false;
std::uintptr_t snapshot_owner=0;
bool writer_active=false,writer_cancelled=false;
volatile unsigned deferred_cancel=0;
// Only the renderer owner writes the sequence/engine. Foreign, IRQ or nested
// callers can request cancellation but cannot turn an odd writer even.
bool begin_write(bool claim=false){
    const auto current=owner();
    if(claim && !snapshot_owner && current)snapshot_owner=current;
    if(!current || current!=snapshot_owner || writer_active){deferred_cancel=1;return false;}
    writer_active=true;snapshot_write_begin(re4dc_world_scratch_snapshot);
    writer_cancelled=false;
    if(deferred_cancel){deferred_cancel=0;frame_meter.cancel();engine.cancel();writer_cancelled=true;}
    return true;
}
void end_write(){snapshot_write_end(re4dc_world_scratch_snapshot);writer_active=false;}

unsigned selected_mask=0,selected_room=0,selected_arm=0;
bool selected=false,started=false,terminal_logged=false,refused=false;
constexpr unsigned iterations=600;
void publish_meter(const Stats& st,const Snapshot& state){
    if(meter_complete_published)return;
    if(state.faults && (selected || refused))frame_meter.invalidate();
    frame_meter.observe(st);const auto totals=frame_meter.totals();
    MeterSnapshot value{};
    value.version=1;value.phase=totals.phase;value.window_serial=selected?1U:0U;
    value.arm=selected_arm;value.room=selected_room;value.periods=totals.periods;
    value.drawn=totals.drawn;value.skipped=totals.skipped;value.engine_frames=st.frames;
    value.borrows=st.borrows;value.entries=st.entries;value.exits=st.exits;
    value.faults=state.faults;value.last_fault=state.last_fault;value.ccr=state.ccr;value.restored=state.restored;
    value.wall_us_lo=unsigned(totals.wall_us);value.wall_us_hi=unsigned(totals.wall_us>>32);
    value.draw_us_lo=unsigned(totals.draw_us);value.draw_us_hi=unsigned(totals.draw_us>>32);
    value.skip_us_lo=unsigned(totals.skip_us);value.skip_us_hi=unsigned(totals.skip_us>>32);
    value.max_us_lo=unsigned(totals.max_us);value.max_us_hi=unsigned(totals.max_us>>32);
    value.enter_us_lo=state.enter_us_lo;value.enter_us_hi=state.enter_us_hi;
    value.exit_us_lo=state.exit_us_lo;value.exit_us_hi=state.exit_us_hi;
    value.target=iterations;value.kind=1;
    value.complete=totals.phase==3 && totals.periods==iterations && state.completed && state.restored;
    auto& dst=re4dc_world_scratch_meter_snapshot;
    ++dst.seq;asm volatile("" ::: "memory");
#define WS23_METER_STORE(name) dst.name=value.name
    WS23_METER_STORE(version);WS23_METER_STORE(phase);WS23_METER_STORE(window_serial);
    WS23_METER_STORE(arm);WS23_METER_STORE(room);WS23_METER_STORE(periods);
    WS23_METER_STORE(drawn);WS23_METER_STORE(skipped);WS23_METER_STORE(engine_frames);
    WS23_METER_STORE(borrows);WS23_METER_STORE(entries);WS23_METER_STORE(exits);
    WS23_METER_STORE(faults);WS23_METER_STORE(last_fault);WS23_METER_STORE(ccr);WS23_METER_STORE(restored);
    WS23_METER_STORE(wall_us_lo);WS23_METER_STORE(wall_us_hi);WS23_METER_STORE(draw_us_lo);WS23_METER_STORE(draw_us_hi);
    WS23_METER_STORE(skip_us_lo);WS23_METER_STORE(skip_us_hi);WS23_METER_STORE(max_us_lo);WS23_METER_STORE(max_us_hi);
    WS23_METER_STORE(enter_us_lo);WS23_METER_STORE(enter_us_hi);WS23_METER_STORE(exit_us_lo);WS23_METER_STORE(exit_us_hi);
    WS23_METER_STORE(target);WS23_METER_STORE(kind);WS23_METER_STORE(complete);
#undef WS23_METER_STORE
    asm volatile("" ::: "memory");++dst.seq;
    meter_complete_published=value.complete;
}
void publish(){
    const auto st=engine.stats();const unsigned mode=ccr();
    Snapshot value{};
    value.version=1;value.window_serial=selected?1U:0U;value.mask=selected_mask;
    value.room=selected_room;value.selected=selected_arm;value.requested=st.requested;
    value.actual=st.actual;value.remaining=st.remaining;value.frames=st.frames;
    value.borrows=st.borrows;value.entries=st.entries;value.exits=st.exits;
    value.faults=st.faults+(refused?1U:0U);value.last_fault=refused?BadRequest:st.last_fault;
    value.epoch=st.epoch;value.ccr=mode;value.iterations=iterations;
    value.completed=started && !st.remaining && st.frames==iterations && !value.faults;
    value.restored=(mode&kStable)==kNormal && st.actual==A && st.entries==st.exits;
    value.phase=value.faults?4U:st.remaining?2U:started?3U:selected?1U:0U;
    value.enter_us_lo=unsigned(st.enter_us);value.enter_us_hi=unsigned(st.enter_us>>32);
    value.exit_us_lo=unsigned(st.exit_us);value.exit_us_hi=unsigned(st.exit_us>>32);
    auto& dst=re4dc_world_scratch_snapshot;
    // Caller marked odd BEFORE any engine/CCR mutation.
    dst.version=value.version;
    dst.phase=value.phase;
    dst.window_serial=value.window_serial;
    dst.mask=value.mask;
    dst.room=value.room;
    dst.selected=value.selected;
    dst.requested=value.requested;
    dst.actual=value.actual;
    dst.remaining=value.remaining;
    dst.frames=value.frames;
    dst.borrows=value.borrows;
    dst.entries=value.entries;
    dst.exits=value.exits;
    dst.faults=value.faults;
    dst.last_fault=value.last_fault;
    dst.epoch=value.epoch;
    dst.ccr=value.ccr;
    dst.completed=value.completed;
    dst.restored=value.restored;
    dst.enter_us_lo=value.enter_us_lo;
    dst.enter_us_hi=value.enter_us_hi;
    dst.exit_us_lo=value.exit_us_lo;
    dst.exit_us_hi=value.exit_us_hi;
    dst.iterations=value.iterations;
    publish_meter(st,value);
    end_write();
    if(started && !st.remaining && !terminal_logged){
        terminal_logged=true;
        re4dc_log("WS23 end serial=1 selected=%u actual=%u frames=%u borrows=%u entries=%u exits=%u faults=%u ccr=%x complete=%u restored=%u enter_us=%u exit_us=%u\n",
            selected_arm,st.actual,st.frames,st.borrows,st.entries,st.exits,value.faults,mode,value.completed,value.restored,value.enter_us_lo,value.exit_us_lo);
    }
    if(meter_complete_published && !meter_logged){
        meter_logged=true;const auto t=frame_meter.totals();
        // mem.cpp re4dc_log uses char line[256]. Even UINT_MAX / ULLONG_MAX
        // fields fit these two complete lines (252 / 170 bytes incl newline).
        re4dc_log("WS23 wall-time serial=1 completed_arm=%u room=%x periods=%u drawn=%u skip=%u wall_us=%llu draw_us=%llu skip_us=%llu max_us=%llu transitions_in_wall=1\n",
            selected_arm,selected_room,t.periods,t.drawn,t.skipped,(unsigned long long)t.wall_us,
            (unsigned long long)t.draw_us,(unsigned long long)t.skip_us,(unsigned long long)t.max_us);
        re4dc_log("WS23 wall-state serial=1 completed_arm=%u room=%x entries=%u exits=%u borrows=%u faults=%u ccr=%x restored=%u\n",
            selected_arm,selected_room,st.entries,st.exits,st.borrows,value.faults,mode,value.restored);
    }
}
void select_once(unsigned room){
    // Room initialization may open the late rig before its world mesh loads,
    // or leave a nonzero mesh from the previous room. Readiness must precede
    // consuming the one-shot, admission and any mask refusal.
    const unsigned target_room=RE4DC_WARP_LATE_ROOM();
    if(!room || room!=target_room)return;
    const int choice=late_choice.take(true,RE4DC_WARP_LATE(~0U));
    if(choice==-1 || choice==-2)return;
    selected_mask=RE4DC_WARP_LATE(~0U);selected_room=room;
    if(choice<0){refused=true;re4dc_log("WS23 refused mask=%x room=%x\n",selected_mask,room);return;}
    selected=true;selected_arm=unsigned(choice);
    // Deliberate reviewed fixture is the authority; bits/version do not certify
    // this image. Main MUST audit exact main+all modules+KOS before launching it.
    const bool ok=engine.admit(1) && engine.request(selected_arm,iterations,room);
    re4dc_log("WS23 request serial=1 mask=%x arm=%u iterations=%u room=%x accepted=%u\n",selected_mask,selected_arm,iterations,room,unsigned(ok));
}
}
// Live arm (QA disc row / warp line `wscratch <arm>`): 0 A normal (no request: the ordinary path), 1 B half cache,
// 2 C scratch. While set, each 600-iteration window is requested again at the next frame begin, and after a room
// change, movie or cancel, so the arm stays on through normal play. Fixture (late-mask) runs keep their single window.
namespace {
bool live_admitted=false;unsigned live_logged=~0U,live_windows=0;
void live_rearm(unsigned room){
    if(selected || refused)return;
    const unsigned want=re4dc_world_scratch_live;
    const auto st=engine.stats();
    if(want!=live_logged){live_logged=want;re4dc_log("WS23 live arm=%u room=%x\n",want,room);}
    if(!want || want>C){if(st.remaining && st.actual!=A)engine.cancel();return;}
    if(!room)return;
    if(st.remaining){if(st.actual!=want)engine.cancel();return;} // arm change: restore first, re-request next begin
    if(!live_admitted)live_admitted=engine.admit(1);
    bool ok=live_admitted && engine.request(want,kMaxWindow,room);
    if(!ok){live_admitted=engine.admit(1);ok=live_admitted && engine.request(want,kMaxWindow,room);} // one retry
    if(ok){ // one line per 600-iteration window (~20 s): proves the arm stays on
        re4dc_log("WS23 live window n=%u arm=%u room=%x frames=%u borrows=%u faults=%u\n",++live_windows,want,room,st.frames,st.borrows,st.faults);
        return;
    }
    const auto s=engine.stats();
    re4dc_log("WS23 live refused arm=%u room=%x faults=%u last=%u\n",want,room,s.faults,s.last_fault);
    re4dc_world_scratch_live=0;
}
}
extern "C" int re4dc_world_scratch_admit(unsigned v){if(!begin_write())return 0;const int ok=engine.admit(v);publish();return ok;}
extern "C" int re4dc_world_scratch_request(unsigned a,unsigned n,unsigned r){if(!begin_write())return 0;const int ok=engine.request(a,n,r);publish();return ok;}
extern "C" void re4dc_world_scratch_begin(unsigned r){
    if(!begin_write(true))return;
    select_once(r);live_rearm(r);const bool was=started;
    engine.begin(r);if(engine.token())started=true;
    if(selected)frame_meter.attach(engine.token(),selected_arm,selected_room,engine.stats());
    publish();
    if(started && !was){const auto s=engine.stats();re4dc_log("WS23 active serial=1 arm=%u remaining=%u ccr=%x\n",s.actual,s.remaining,ccr());}
}
extern "C" unsigned re4dc_world_scratch_frame_token(){return owner()==snapshot_owner?engine.token():0;}
extern "C" void re4dc_world_scratch_end(unsigned token,int aborted){if(!begin_write())return;if(token)engine.end(token,aborted!=0);publish();}
extern "C" void re4dc_world_scratch_cancel(){if(!begin_write())return;frame_meter.cancel();engine.cancel();publish();}
extern "C" int re4dc_world_scratch_acquire(void* ram,void** out){*out=ram;if(!begin_write())return -1;const int ok=engine.acquire(ram,*out);if(ok<0 || writer_cancelled)publish();else end_write();return ok;}
extern "C" void re4dc_world_scratch_release(){if(!begin_write())return;const auto before=engine.stats();engine.release();const auto after=engine.stats();if(writer_cancelled || before.faults!=after.faults || before.actual!=after.actual || before.remaining!=after.remaining)publish();else end_write();}
extern "C" re4dc::world_scratch::Stats re4dc_world_scratch_stats(){return engine.stats();}
extern "C" void re4dc_world_scratch_boundary(int skipped,unsigned room){
    const auto now=clock_us();
    if(!begin_write(true))return;
    const auto st=engine.stats();
    const bool restored=(ccr()&kStable)==kNormal && st.actual==A && st.entries==st.exits;
    frame_meter.boundary(now,skipped!=0,room,st,engine.token(),restored);publish();
}
extern "C" int re4dc_world_scratch_meter_read(re4dc::world_scratch::MeterSnapshot* out){
    if(!out)return 0;
    const auto& source=re4dc_world_scratch_meter_snapshot;
    for(unsigned tries=0;tries<3;++tries){
        const unsigned seq=source.seq;if(seq&1U)continue;
        asm volatile("" ::: "memory");
        const auto* bytes=reinterpret_cast<const volatile unsigned char*>(&source);
        auto* dest=reinterpret_cast<unsigned char*>(out);
        for(unsigned i=0;i<sizeof(*out);++i)dest[i]=bytes[i];
        asm volatile("" ::: "memory");
        if(seq==source.seq && !(seq&1U))return out->version==1 && out->phase!=0;
    }
    return 0;
}
#endif
#endif
