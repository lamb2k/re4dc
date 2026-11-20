// E2 fight slice (lane eng-e2): the trace and the gameplay events of the village square fight.
//   LE lines: every enemy-table work but the player, in the reference's field order (logic_trace.cpp em_diag), so the
//   old game's LE lines compare directly (s/fight_pr.py);
//   GE lines: gameplay events (spawn, gone, hit, kill) with the tick and the list entry, recorded as they happen;
//   LL line: the player's life and state.
#include "global.h"
#include "player.h"
#include "em.h"
#include "e1_engine.h"
#include "e1_core.h"
#include "boss_e2.h"
#include "fight_e2.h"
#include "fx.h"
#include <string.h>
#include <stdio.h>

template <class T> static unsigned w4(const T& v) { unsigned w = 0; memcpy(&w, &v, sizeof(v) < 4 ? sizeof(v) : 4); return w; }

struct GameEvent { uint16_t tick, kind; uint8_t entry, id; int16_t a, b; };
#define E2_EVENTS 512
static GameEvent events[E2_EVENTS];
static unsigned n_events, n_kind[E2EV_KINDS];
static const char* const kind_name[E2EV_KINDS] = {"", "spawn", "gone", "hit", "kill"};

void e2_event(int kind, cEm* em, int arg)
{
    n_kind[kind]++;
    if (n_events < E2_EVENTS)
        events[n_events++] = {(uint16_t) e1_tick, (uint16_t) kind, (uint8_t) em->emset_no, (uint8_t) em->id, (int16_t) arg, 0};
}

// Life per work slot, last tick: a drop is a hit, reaching 0 a kill (the original's die check follows on its own).
static int16_t last_hp[64];
static uint32_t last_serial[64];
void e2_watch_hp()
{
    for (cEm* e = EmMgr.pAlive; e; e = (cEm*) e->pNext) {
        if (e == pPL || e->id < 0x10 || e->id > 0x20) continue;
        const unsigned slot = ((uintptr_t) e - (uintptr_t) EmMgr.pArray) / EmMgr.size;
        if (slot >= 64) continue;
        if (last_serial[slot] != e->serial + 1) { last_serial[slot] = e->serial + 1; last_hp[slot] = e->hp; continue; }
        if (e->hp < last_hp[slot]) {
            n_kind[E2EV_HIT]++;
            if (n_events < E2_EVENTS)
                events[n_events++] = {(uint16_t) e1_tick, E2EV_HIT, (uint8_t) e->emset_no, (uint8_t) e->id, last_hp[slot], (int16_t) e->hp};
            if (e->hp <= 0 && last_hp[slot] > 0) {
                n_kind[E2EV_KILL]++;
                if (n_events < E2_EVENTS)
                    events[n_events++] = {(uint16_t) e1_tick, E2EV_KILL, (uint8_t) e->emset_no, (uint8_t) e->id, last_hp[slot], (int16_t) e->hp};
            }
        }
        last_hp[slot] = e->hp;
    }
}

void e2_trace_tick(unsigned tick, char* out, unsigned cap, unsigned* used)
{
    unsigned k = 0;
    for (cEm* e = EmMgr.pAlive; e; e = (cEm*) e->pNext) {
        if (e == pPL) continue;
        int n = snprintf(out + *used, cap - *used, "LE t=%u k=%u id=%x type=%x be=%08x stat=%08x ms=%x hp=%x mf=%08x pos=%08x,%08x,%08x ay=%08x e=%02x\n",
                         tick, k++, w4(e->id), w4(e->type), w4(e->be_flag), w4(e->stat), w4(e->Motion.Mot_state), w4(e->hp),
                         w4(e->Motion.Mot_frame), w4(e->pos.x), w4(e->pos.y), w4(e->pos.z), w4(e->ang.y), (unsigned) e->emset_no);
        if (n > 0 && *used + n < cap) *used += n;
    }
    if (pPL) {
        int n = snprintf(out + *used, cap - *used, "LL t=%u hp=%x st=%08x ms=%x sp=%08lx fx=%u\n", tick, w4(pPL->hp), w4(pPL->stat),
                         w4(pPL->Motion.Mot_state), (unsigned long) pG->Stop_flg, fx_live_count());
        if (n > 0 && *used + n < cap) *used += n;
    }
}

void e2_events_report()
{
    for (unsigned k = 1; k < E2EV_KINDS; k++) e1_log("E2 EVENTS %s %u\n", kind_name[k], n_kind[k]);
    for (unsigned i = 0; i < n_events; i++)
        e1_log("GE t=%u %s e=%02x id=%x a=%d b=%d\n", events[i].tick, kind_name[events[i].kind], events[i].entry, events[i].id,
               events[i].a, events[i].b);
}
void e2_report()
{
    e2_events_report();
    fx_report();
}
void e2_fx_move() { fx_move(); }
void e2_after_tick() {}
void e2_fx_room_init() { fx_room_init(); }
