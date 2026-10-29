#include "platform/include/fallback_audit29.h"
#include <arch/irq.h>
#include <cstdio>
#include <cstring>
#if defined(RE4DC_FALLBACK_WINDOW35) && RE4DC_FALLBACK_WINDOW35
#include "platform/include/fallback_window35.h"
#include "platform/include/draw_fallback_audit.h"
#endif

extern "C" void re4dc_fa29_actor_reset(void) __attribute__((weak));

namespace re4dc { namespace fa29 {
namespace {
struct State {
    Snapshot sealed;
    uint32_t totals[ReasonCount], current[ReasonCount];
    uint32_t tick, room, ticks, draws, overflow, outside_tick, sequence;
    bool active, paused, have_room, draw, valid;
};
alignas(32) State state{};
#if defined(RE4DC_FALLBACK_WINDOW35) && RE4DC_FALLBACK_WINDOW35
uint32_t window_tick_overflow=0;
#endif
const char* const labels[]={
#define FA29_REASON(symbol, label, unit) label,
#include "platform/include/fallback_audit29.def"
#undef FA29_REASON
#if defined(RE4DC_FALLBACK_AUDIT35) && RE4DC_FALLBACK_AUDIT35
#define FA35_REASON(symbol, label, unit) label,
#include "platform/include/fallback_audit35.def"
#undef FA35_REASON
#endif
};
const char* const units[]={
#define FA29_REASON(symbol, label, unit) unit,
#include "platform/include/fallback_audit29.def"
#undef FA29_REASON
#if defined(RE4DC_FALLBACK_AUDIT35) && RE4DC_FALLBACK_AUDIT35
#define FA35_REASON(symbol, label, unit) unit,
#include "platform/include/fallback_audit35.def"
#undef FA35_REASON
#endif
};
void add(uint32_t& value, uint32_t amount) {
    if (amount>UINT32_MAX-value) { value=UINT32_MAX; state.overflow=1; }
    else value+=amount;
}
}
void hit(Reason reason, uint32_t amount) {
    if (unsigned(reason)>=ReasonCount || !amount) return;
    const int saved=irq_disable();
    if (!state.paused && state.have_room) {
#if defined(RE4DC_FALLBACK_WINDOW35) && RE4DC_FALLBACK_WINDOW35
        if(state.active && amount>UINT32_MAX-state.current[reason])window_tick_overflow=1;
#endif
        add(state.totals[reason],amount);
        if (state.active) add(state.current[reason],amount);
        else add(state.outside_tick,1);
    }
    irq_restore(saved);
}
bool collecting() { return state.active && !state.paused && state.have_room; }
void begin_tick(uint32_t tick, uint32_t room) {
    const int saved=irq_disable();
    bool reset_actor=false;
    state.active=false;
    if (!state.paused) {
        if (!state.have_room || room!=state.room) {
            // A new room invalidates the previous draw as well as its totals.
            // This is the only automatic reset; paused QA snapshots stay fixed.
            const uint32_t seq=state.sequence;
            std::memset(&state,0,sizeof(state));
            state.sequence=seq;
            state.have_room=true;
            state.room=room;
            reset_actor=true;
        }
        std::memset(state.current,0,sizeof(state.current));
#if defined(RE4DC_FALLBACK_WINDOW35) && RE4DC_FALLBACK_WINDOW35
        window_tick_overflow=0;
#endif
        state.tick=tick; state.draw=true; state.active=true;
    }
    irq_restore(saved);
    if (reset_actor && re4dc_fa29_actor_reset) re4dc_fa29_actor_reset();
#if defined(RE4DC_FALLBACK_WINDOW35) && RE4DC_FALLBACK_WINDOW35
    if(state.active)fw35::begin_tick(tick,room);
#endif
}
void decision(bool draw_attempt) {
    const int saved=irq_disable();
    if (state.active) state.draw=draw_attempt;
    irq_restore(saved);
}
void end_tick() {
    const int saved=irq_disable();
#if defined(RE4DC_FALLBACK_WINDOW35) && RE4DC_FALLBACK_WINDOW35
    const bool window_complete=state.active;
#endif
    if (state.active) {
        state.active=false;
        add(state.ticks,1);
        if (state.draw) {
            add(state.draws,1);
            state.sealed.draw_tick=state.tick;
            state.sealed.draw_valid=1;
            std::memcpy(state.sealed.last_draw,state.current,sizeof(state.current));
        }
        // The room totals include skipped ticks and asynchronous work. They
        // must never be divided by draws to claim a per-drawn-tick frequency.
        state.sealed.sequence=++state.sequence;
        state.sealed.tick=state.tick; state.sealed.room=state.room;
        state.sealed.ticks=state.ticks; state.sealed.draws=state.draws;
        state.sealed.overflow=state.overflow;
        state.sealed.outside_tick=state.outside_tick;
        std::memcpy(state.sealed.totals,state.totals,sizeof(state.totals));
        state.valid=true;
    }
    irq_restore(saved);
#if defined(RE4DC_FALLBACK_WINDOW35) && RE4DC_FALLBACK_WINDOW35
    // Current arrays are immutable after active=false; worker events now reach
    // room totals/outside only. Never scan or update the ring with IRQs masked.
    if(window_complete)fw35::end_tick(state.draw,dfa26::live,dfa26::overflow,state.current,window_tick_overflow,state.sealed.outside_tick);
#endif
}
#if defined(RE4DC_FALLBACK_WINDOW35) && RE4DC_FALLBACK_WINDOW35
void pause() {
    const int saved=irq_disable();state.active=false;state.paused=true;irq_restore(saved);
    fw35::pause();
}
void resume() {
    const int saved=irq_disable();state.active=false;state.paused=false;irq_restore(saved);
    fw35::resume();
}
#else
void pause() { const int saved=irq_disable(); state.active=false; state.paused=true; irq_restore(saved); }
void resume() { const int saved=irq_disable(); state.active=false; state.paused=false; irq_restore(saved); }
#endif
void reset() {
    const int saved=irq_disable(); std::memset(&state,0,sizeof(state)); irq_restore(saved);
    if (re4dc_fa29_actor_reset) re4dc_fa29_actor_reset();
#if defined(RE4DC_FALLBACK_WINDOW35) && RE4DC_FALLBACK_WINDOW35
    window_tick_overflow=0;fw35::reset();
#endif
}
bool snapshot(Snapshot* out) {
    if (!out) return false;
    const int saved=irq_disable();
    const bool valid=state.valid;
    if (valid) *out=state.sealed;
    irq_restore(saved);
    return valid;
}
const char* label(Reason reason) { return unsigned(reason)<ReasonCount?labels[reason]:"invalid"; }
const char* unit(Reason reason) { return unsigned(reason)<ReasonCount?units[reason]:"invalid"; }
#if defined(RE4DC_FALLBACK_WINDOW35) && RE4DC_FALLBACK_WINDOW35
unsigned line_count() { return state.valid?2U+(1U+unsigned(fw35::available()))*((ReasonCount+3U)/4U):1U; }
int format_line(unsigned row, char* out, unsigned capacity) {
    if(!out || !capacity || row>=line_count())return -1;
    int n;
    const auto& s=state.sealed;
    if(!state.valid)n=::snprintf(out,capacity,"FA29 collecting complete tick");
    else if(!row)n=::snprintf(out,capacity,
        "FA29 seq=%u tick=%u room=%03x ticks=%u draws=%u overflow=%u outside=%u totals=room",
        unsigned(s.sequence),unsigned(s.tick),unsigned(s.room),unsigned(s.ticks),unsigned(s.draws),unsigned(s.overflow),unsigned(s.outside_tick));
    else if(row==1)return fw35::fa_header(out,capacity);
    else{
        const unsigned rows=(ReasonCount+3U)/4U;
        const bool last=row-2U>=rows;
        const unsigned first=((row-2U)%rows)*4U;
        n=::snprintf(out,capacity,last?"FA29W":"FA29T");
        for(unsigned i=first;i<ReasonCount && i<first+4U;++i){
            if(n<0 || unsigned(n)>=capacity){out[capacity-1]=0;return -1;}
            const int added=last?
                ::snprintf(out+n,capacity-unsigned(n)," %s=%llu",labels[i],static_cast<unsigned long long>(fw35::fa_sum(i))):
                ::snprintf(out+n,capacity-unsigned(n)," %s=%u",labels[i],unsigned(s.totals[i]));
            if(added<0){out[capacity-1]=0;return -1;}n+=added;
        }
    }
    if(n<0 || unsigned(n)>=capacity){out[capacity-1]=0;return -1;}
    return n;
}
#else
unsigned line_count() { return state.valid?2U+2U*((ReasonCount+3U)/4U):1U; }
int format_line(unsigned row, char* out, unsigned capacity) {
    // Only the game/QA thread seals or formats. Worker threads modify totals,
    // never sealed; a whole diagnostic capture sees one immutable snapshot.
    if (!out || !capacity || row>=line_count()) return -1;
    int n;
    const auto& s=state.sealed;
    if (!state.valid) n=::snprintf(out,capacity,"FA29 collecting complete tick");
    else if (!row) n=::snprintf(out,capacity,
        "FA29 seq=%u tick=%u room=%03x ticks=%u draws=%u overflow=%u outside=%u totals=room",
        unsigned(s.sequence),unsigned(s.tick),unsigned(s.room),unsigned(s.ticks),unsigned(s.draws),unsigned(s.overflow),unsigned(s.outside_tick));
    else if (row==1) n=::snprintf(out,capacity,
        "FA29 lastdraw=%u valid=%u async=included totals_not_per_draw=1",
        unsigned(s.draw_tick),unsigned(s.draw_valid));
    else {
        const unsigned rows=(ReasonCount+3U)/4U;
        const bool last=row-2U>=rows;
        const unsigned first=((row-2U)%rows)*4U;
        n=::snprintf(out,capacity,last?"FA29D":"FA29T");
        for (unsigned i=first;i<ReasonCount && i<first+4U;++i) {
            if (n<0 || unsigned(n)>=capacity) { out[capacity-1]=0; return -1; }
            const int added=::snprintf(out+n,capacity-unsigned(n)," %s=%u",labels[i],unsigned(last?s.last_draw[i]:s.totals[i]));
            if (added<0) { out[capacity-1]=0; return -1; }
            n+=added;
        }
    }
    if (n<0 || unsigned(n)>=capacity) { out[capacity-1]=0; return -1; }
    return n;
}
#endif
} }
