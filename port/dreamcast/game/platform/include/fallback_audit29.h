#ifndef RE4DC_FALLBACK_AUDIT29_H
#define RE4DC_FALLBACK_AUDIT29_H

// Include only from a standalone RE4DC_FALLBACK_AUDIT29 block. The counter
// implementation serializes game, disc and sound-thread writers with KOS IRQ
// save/restore. No allocation, I/O, formatting or timer in hit().
#include <stdint.h>
namespace re4dc { namespace fa29 {
enum Reason {
#define FA29_REASON(symbol, label, unit) symbol,
#include "fallback_audit29.def"
#undef FA29_REASON
    ReasonCount
};
struct Snapshot {
    uint32_t sequence, tick, room, ticks, draws, overflow, outside_tick;
    uint32_t draw_tick, draw_valid;
    uint32_t totals[ReasonCount];
    uint32_t last_draw[ReasonCount];
};
void hit(Reason reason, uint32_t amount=1);
void begin_tick(uint32_t tick, uint32_t room);
void decision(bool draw_attempt);
void end_tick();
void pause();
void resume();
void reset();
// Game-thread only: actor attribution uses the same active/paused boundary.
// Async disc/sound writers use hit(), whose room totals also cover outside ticks.
bool collecting();
bool snapshot(Snapshot* out);
unsigned line_count();
int format_line(unsigned row, char* out, unsigned capacity);
const char* label(Reason reason);
const char* unit(Reason reason);
} }
#endif
