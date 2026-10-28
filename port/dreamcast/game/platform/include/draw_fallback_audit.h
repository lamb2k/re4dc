#ifndef RE4DC_DRAW_FALLBACK_AUDIT_H
#define RE4DC_DRAW_FALLBACK_AUDIT_H

// Include only with DRAW_FALLBACK_AUDIT enabled. One renderer/game-thread
// writer; no allocation, clock reads, formatting or IRQ masking in hit().
#include <stdint.h>
namespace re4dc { namespace dfa26 {
enum Reason {
#define DFA26_REASON(symbol, label, unit) symbol,
#include "draw_fallback_world.def"
#include "draw_fallback_model.def"
#include "draw_fallback_other.def"
#undef DFA26_REASON
    ReasonCount
};
struct Snapshot {
    uint32_t sequence, tick, room, drawn, overflow;
    uint32_t items[ReasonCount];
};
extern bool active;
extern uint32_t live[ReasonCount], overflow;
inline void hit(Reason reason, uint32_t amount=1) {
    if (!active) return;
    const uint32_t old=live[reason];
    const uint32_t value=old+amount;
    if (value<old) { live[reason]=UINT32_MAX; overflow=1; }
    else live[reason]=value;
}
void begin_tick(uint32_t tick, uint32_t room);
void decision(bool draw_attempt);
void end_tick();
void pause();
void resume();
void reset();
bool snapshot(Snapshot* out);
unsigned line_count();
int format_line(unsigned row, char* out, unsigned capacity);
const char* label(Reason);
const char* unit(Reason);
} }
#endif
