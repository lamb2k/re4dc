#include "platform/include/draw_fallback_audit.h"
#include <cstdio>
#include <cstring>

namespace re4dc { namespace dfa26 {
bool active=false;
alignas(32) uint32_t live[ReasonCount]{};
uint32_t overflow=0;
namespace {
Snapshot sealed{};
uint32_t tick=0, room=0, drawn=1, sequence=0;
bool valid=false, paused=false, have_room=false;
const char* const labels[]={
#define DFA26_REASON(symbol, label, unit) label,
#include "platform/include/draw_fallback_world.def"
#include "platform/include/draw_fallback_model.def"
#include "platform/include/draw_fallback_other.def"
#undef DFA26_REASON
};
const char* const units[]={
#define DFA26_REASON(symbol, label, unit) unit,
#include "platform/include/draw_fallback_world.def"
#include "platform/include/draw_fallback_model.def"
#include "platform/include/draw_fallback_other.def"
#undef DFA26_REASON
};
}
void begin_tick(uint32_t next_tick, uint32_t next_room) {
    active=false;
    if (paused) return;
    if (!have_room || next_room!=room) { valid=false; have_room=true; }
    tick=next_tick; room=next_room; drawn=1; overflow=0;
    std::memset(live,0,sizeof(live));
    active=true;
}
void decision(bool draw_attempt) { drawn=draw_attempt?1U:0U; }
void end_tick() {
    if (!active) return;
    active=false;
    // Keep the last tick that drew: under frame skip most ticks draw nothing, and sealing those zeros hid every
    // count on the console (r103 barn, 10-28: every row read drawn=0).
    if (!drawn && valid) return;
    sealed.sequence=++sequence; sealed.tick=tick; sealed.room=room;
    sealed.drawn=drawn; sealed.overflow=overflow;
    std::memcpy(sealed.items,live,sizeof(live));
    valid=true;
}
void pause() { active=false; paused=true; }
void resume() { active=false; paused=false; }
void reset() { active=false; paused=false; valid=false; have_room=false; sequence=0; }
bool snapshot(Snapshot* out) { if (!valid || !out) return false; *out=sealed; return true; }
const char* label(Reason reason) { return labels[reason]; }
const char* unit(Reason reason) { return units[reason]; }
unsigned line_count() { return valid?1U+(ReasonCount+3U)/4U:1U; }
int format_line(unsigned row, char* out, unsigned capacity) {
    if (!out || !capacity || row>=line_count()) return -1;
    int n=0;
    if (!valid) n=::snprintf(out,capacity,"F26 collecting complete tick");
    else if (!row) n=::snprintf(out,capacity,
        "F26 seq=%u tick=%u room=%03x drawn=%u overflow=%u items_per_tick=last_complete",
        sealed.sequence,sealed.tick,sealed.room,sealed.drawn,sealed.overflow);
    else {
        n=::snprintf(out,capacity,"F26");
        const unsigned first=(row-1U)*4U;
        for (unsigned i=first;i<ReasonCount && i<first+4U;++i) {
            if (n<0 || unsigned(n)>=capacity) { out[capacity-1]=0; return -1; }
            const int added=::snprintf(out+n,capacity-unsigned(n)," %s=%u",labels[i],sealed.items[i]);
            if (added<0) { out[capacity-1]=0; return -1; }
            n+=added;
        }
    }
    if (n<0 || unsigned(n)>=capacity) { out[capacity-1]=0; return -1; }
    return n;
}
} }
