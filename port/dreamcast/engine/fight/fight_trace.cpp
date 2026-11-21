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
#include "dmg.h"
#include "skel.h"
#include "e1_skel_view.h"
#include <string.h>
#include <stdio.h>

template <class T> static unsigned w4(const T& v) { unsigned w = 0; memcpy(&w, &v, sizeof(v) < 4 ? sizeof(v) : 4); return w; }

struct GameEvent { uint16_t tick, kind; uint8_t entry, id; int16_t a, b; uint8_t wep, part; };
#define E2_EVENTS 512
static GameEvent events[E2_EVENTS];
static unsigned n_events, n_kind[E2EV_KINDS];
static const char* const kind_name[E2EV_KINDS] = {"", "spawn", "gone", "hit", "kill"};

void e2_event(int kind, cEm* em, int arg)
{
    n_kind[kind]++;
    if (n_events < E2_EVENTS)
        events[n_events++] = {(uint16_t) e1_tick, (uint16_t) kind, (uint8_t) em->emset_no, (uint8_t) em->id, (int16_t) arg, 0, 0, 0};
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
            const uint8_t wep = (uint8_t) e->dmg.m_Wep, part = e->dmg.m_pDamageYarare ? (uint8_t) e->dmg.m_pDamageYarare->partsNo : 0xFF;
            n_kind[E2EV_HIT]++;
            if (n_events < E2_EVENTS)
                events[n_events++] = {(uint16_t) e1_tick, E2EV_HIT, (uint8_t) e->emset_no, (uint8_t) e->id, last_hp[slot], (int16_t) e->hp, wep, part};
            if (e->hp <= 0 && last_hp[slot] > 0) {
                n_kind[E2EV_KILL]++;
                if (n_events < E2_EVENTS)
                    events[n_events++] = {(uint16_t) e1_tick, E2EV_KILL, (uint8_t) e->emset_no, (uint8_t) e->id, last_hp[slot], (int16_t) e->hp, wep, part};
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
        e1_log("GE t=%u %s e=%02x id=%x a=%d b=%d wep=%x part=%x\n", events[i].tick, kind_name[events[i].kind], events[i].entry,
               events[i].id, events[i].a, events[i].b, events[i].wep, events[i].part);
}
// lane eng-e2a: the enemy hit geometry's counters (services/aim/em_hit.cpp)
extern "C" struct EmHitCounters {
    unsigned line_tests, line_capsules, line_cubes, cube_mirrored, quads, line_hits;
    unsigned sphere_tests, sphere_boxes, sphere_hits, dm_pos, atk_sphere, atk_line, atk_hits;
    unsigned racks, water, catch_moves, bloods, blood_scatter, bomb_lists, bomb_player, debug_draws;
} emhit_cnt;
// lane eng-e2a item 2: the damage volumes' counters (services/volumes/dmg_vol.cpp)
extern "C" struct DmgCounters { unsigned sets_seen, tests, hits, ticks, expired, freed, logs, debug_draws; } dmg_cnt
    __attribute__((weak));   // weak: the control build DMG_ORIG=1 links dmg.cpp whole
// lane eng-e2a item 3: the scenario areas' counters (services/volumes/area_vol.cpp; weak: the control build AREA_ORIG=1)
extern "C" struct AreaCounters { unsigned hit_tests, hits, eye_tests, centres, inside_points, inits, bad_types; } area_cnt
    __attribute__((weak));
// lane eng-e2f: the screen tests (the GX projection queries' answers, fight_stubs.cpp; em10ScreenInCk, services/em10)
extern "C" unsigned e2_gx_projections;
extern "C" struct Em10CamCounters { unsigned shots, shakes, wall_pulls, wall_hits, installs, screen_checks, screen_on; } em10c_cnt;
void e2_report()
{
    e2_events_report();
    fx_report();
    const EmHitCounters& h = emhit_cnt;
    e1_log("E2 EMHIT lines %u (capsules %u cubes %u mirrored %u quads %u hits %u) spheres %u (boxes %u hits %u) dmpos %u "
           "attacks %u lines %u hits %u racks %u water %u catch %u bloods %u scatter %u blasts %u blast-player %u debug-draws %u\n",
           h.line_tests, h.line_capsules, h.line_cubes, h.cube_mirrored, h.quads, h.line_hits, h.sphere_tests, h.sphere_boxes,
           h.sphere_hits, h.dm_pos, h.atk_sphere, h.atk_line, h.atk_hits, h.racks, h.water, h.catch_moves, h.bloods,
           h.blood_scatter, h.bomb_lists, h.bomb_player, h.debug_draws);
    if (&dmg_cnt) e1_log("E2 DMG table %u records, tests %u hits %u ticks %u expired %u freed %u pool-logs %u debug-draws %u\n",
           (unsigned) DmgMgr.nArray, dmg_cnt.tests, dmg_cnt.hits, dmg_cnt.ticks, dmg_cnt.expired, dmg_cnt.freed, dmg_cnt.logs,
           dmg_cnt.debug_draws);
    e1_log("E2 SCREEN projections %u em10-checks %u on-screen %u cut-ins %u\n", e2_gx_projections, em10c_cnt.screen_checks,
           em10c_cnt.screen_on, em10c_cnt.shots);
    if (&area_cnt) e1_log("E2 AREA hit-tests %u hits %u eye-tests %u centres %u inside-points %u inits %u bad-types %u\n",
           area_cnt.hit_tests, area_cnt.hits, area_cnt.eye_tests, area_cnt.centres, area_cnt.inside_points, area_cnt.inits,
           area_cnt.bad_types);
}
// lane eng-e2a item 2: the damage volumes' tick (services/volumes/dmg_vol.cpp cDmgMgr::move), after the camera as the
// game's main loop and the PC reference (hostref replay.cpp) run it
void e2_after_tick() { DmgMgr.move(); }
void e2_fx_room_init() { fx_room_init(); }

// The Ganados for the picture (fight_draw.inc): each alive enemy-table work of the village square's Ganado kinds, its
// record, its native skeleton table (pointers only, as services/draw.cpp's skel_view) and the pack's base model for its
// kind (native_actor.inc model_index: type 3 -> 3, 4 -> 4, 11 -> 5, otherwise 2), identity = id | type << 8.
extern "C" unsigned e2_actor_list(const void** models, E1SkelView* views, unsigned* bases, unsigned* idents, unsigned max)
{
    unsigned n = 0;
    for (cEm* e = EmMgr.pAlive; e && n < max; e = (cEm*) e->pNext) {
        if (e == pPL || e->id < 0x10 || e->id > 0x20 || !(e->be_flag & 1)) continue;
        const SkelTable* t = skel_table_of(e);
        if (!t) continue;
        E1SkelView& v = views[n];
        v.world = &t->world[0].m[0][0];
        v.pal = &t->pal[0].m[0][0];
        v.bind[0] = t->soa + SK_BX * t->cap;
        v.bind[1] = t->soa + SK_BY * t->cap;
        v.bind[2] = t->soa + SK_BZ * t->cap;
        v.n = t->n;
        const unsigned type = e->type;
        models[n] = e;
        bases[n] = type == 3 ? 3 : type == 4 ? 4 : type == 11 ? 5 : 2;
        idents[n] = (unsigned) e->id | type << 8;
        n++;
    }
    return n;
}
