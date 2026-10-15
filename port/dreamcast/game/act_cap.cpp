// D367 B1: Ganado activation cap (ACT_CAP=N in game30.mk; default 0 = not built).
//
// At most N Ganados (ids 0x10..0x20) are "active" per logic tick: they run emMove (AI, motion,
// skeleton) as usual. The others are "parked": cEmMgr::move skips their emMove and only keeps
// plDist2 current (the value emMove would write), so the group throttles (em10DashCk /
// em10StayCk count others by plDist2 and EM_STATUS_ACTIVE) keep counting them exactly.
// A parked Ganado stays in EmMgr's alive list with its be_flag, hp, position, routine and motion
// state untouched, so every alive / kill / wave / bell / door query sees it as before.
//
// Never parked (always active, even beyond N):
//   * not in the plain AI routine (r_no_0 != 1): init, damage, death, events, anything scripted;
//   * a threat routine: find, attack, grab, door / window bash, ladder, or holding the player;
//   * a pending damage record (dmg.m_Flag), the player's lock-on target, hp <= 0;
//   * within the engagement radius RE4DC_ACT_CAP_RANGE_M (horizontal, like plDist2). 12 m is
//     em10StayCk's own outer limit (L_pl_route > 12000 never stays, em10.cpp:23201) and the r101
//     tower rule's radius (144000000, em10.cpp:23128): L_pl_route is only refreshed inside a
//     Ganado's own move, and a route distance is at least the straight one, so a Ganado parked
//     beyond 12 m can never be counted as "closer" in another Ganado's StayCk;
//   * inside the previous frame's full view frustum inflated by RE4DC_ACT_CAP_VIEW_M;
//   * activated less than kHoldTicks ago (no thrash at the boundary).
// The rest are ranked by distance (the active ones get a 20% distance bonus: hysteresis) and the
// nearest fill the N slots.
//
// Resume is seamless because a parked Ganado is out of view and nothing about it changed: the
// next emMove continues its routine and motion from where they stopped, at the same position.
// Rendering is not hooked at all: ModelTrans frustum-culls before any skinning, so a parked
// Ganado costs nothing to draw; if the camera swings onto one between the logic tick and the
// render, it is drawn in its held pose (no pop-in) and becomes active on the next tick.
//
// RE4DC_ACT_CAP_CREEP=K (default 4, 0 = frozen): a parked Ganado still runs one full emMove
// every K ticks (staggered by slot so the cost is spread). It keeps walking its own AI route
// with collision at 1/K speed, so the crowd still closes in and the fight's pressure holds; the
// game's own weapon-zoom slow motion runs EmMgr.move every 3rd frame the same way.
//
// With N at or above the number of live Ganados nothing is ever parked and cEmMgr::move runs
// exactly the reference code path (the selection only reads game state): the logic trace is
// STRICT against the reference build.
//
// FAR_HALF=1|2 (game30.mk; lane farhalf 2026-10-15, backlog D1; default 0 = not compiled): far / off-screen
// Ganados update at half rate, in every room, independently of the cap above (built with or without it).
// Eligible on a tick = a Ganado (ids 0x10..0x20) in a whitelisted walking / idle routine (threat() below),
// farther than RE4DC_FAR_HALF_M metres from Leon (horizontal), outside the previous frame's view frustum
// inflated by RE4DC_ACT_CAP_VIEW_M, hp > 0, no pending damage, not the lock-on target, and not parked by the
// cap. An eligible Ganado alternates strictly: one tick full, one tick reduced (never two reduced ticks in a
// row; any ineligible tick is a full one), so one that turns visible or comes within N m is full on that tick.
//   1 = pose half (the exact candidate): the reduced tick runs the whole AI / routine / movement / collision
//       path and only skips the pose work (key evaluation, part matrices, foot IK, hokan blend) in MotionMove;
//       the parts then follow the body by translation (PartsWorldPosCalc). The Rnd stream is untouched.
//   2 = full half (approximation): the reduced tick skips emMove as the cap's parked tick does (plDist2 kept
//       current); the far Ganado walks at half speed and its Rnd draws move.
// Never runs while the radio-call sub screen has swapped the room lists (re4dc_ss_ui_order), during an event
// pause or while characters are frozen: every Ganado is then a full one.
#include "global.h"
#include "player.h"
#include "em.h"
#include "view.h"
#include "geometry.h"
#include "camera.h"
#include "re4dc_platform.h"
#include "warp_late.h"
#if defined(RE4DC_ACT_CAP_FAR_M) && RE4DC_ACT_CAP_FAR_M
#include "bench_lever.h"
#endif

#ifndef RE4DC_ACT_CAP
#define RE4DC_ACT_CAP 0
#endif
#ifndef RE4DC_ACT_CAP_ROOM
#define RE4DC_ACT_CAP_ROOM 0x101   // stage << 8 | room; 0 = every room
#endif
#ifndef RE4DC_ACT_CAP_RANGE_M
#define RE4DC_ACT_CAP_RANGE_M 12
#endif
#ifndef RE4DC_ACT_CAP_VIEW_M
#define RE4DC_ACT_CAP_VIEW_M 3
#endif
#ifndef RE4DC_ACT_CAP_CREEP
#define RE4DC_ACT_CAP_CREEP 4
#endif
#ifndef RE4DC_ACT_CAP_LOG
#define RE4DC_ACT_CAP_LOG 0   // N > 0: one "AC" stats line per N ticks through re4dc_log
#endif
#ifndef RE4DC_ACT_CAP_TABLE
#define RE4DC_ACT_CAP_TABLE 0
#endif
#ifndef RE4DC_FAR_HALF
#define RE4DC_FAR_HALF 0
#endif
#if RE4DC_FAR_HALF
#ifndef RE4DC_FAR_HALF_M
#define RE4DC_FAR_HALF_M 12
#endif
#ifndef RE4DC_FAR_HALF_LOG
#define RE4DC_FAR_HALF_LOG 0   // N > 0: one "FH" census line per N ticks with live Ganados
#endif
extern "C" int re4dc_ss_ui_order() __attribute__((weak));   // sscrn_bridge.cpp: 1 while the room lists are swapped
#if defined(RE4DC_FAR_HALF_RT) && RE4DC_FAR_HALF_RT
// FAR_HALF_RT=1 (game30.mk; DBG_WARP test / benchmark builds): the run-time switch, set by each warp fixture
// (dbgwarp_bridge.cpp: 1 unless the fixture says `farhalf 0`), so one benchmark disc measures off and on.
extern "C" {
int re4dc_far_half_rt = 1;
}
#endif
#endif

namespace {
#if RE4DC_ACT_CAP_TABLE
// ACT_CAP_TABLE=1 (user 2026-10-13): per-room caps, replacing ACT_CAP / ACT_CAP_ROOM. A room missing from the
// table has no cap. kScripted marks a room whose set fight must stay exact (to be set for r10b, r119 and the
// r11c / r11d fights once they are measured): no cap there either. Bosses and specials are never parked
// anyway (isGanado: ids 0x10..0x20 only), nor is any Ganado matched by the never-park rules below.
enum : u8 { kScripted = 1 };
struct RoomCap {
    u16 room;   // stage << 8 | room
    u8 cap;     // active Ganados per tick
    u8 flags;
};
constexpr RoomCap kRoomCaps[] = {
    {0x101, 5, 0},   // r101 village fight (test 9: PS2 rules + cap 5 measured)
};
#endif
int g_cap;   // this tick's cap (roomOn)

constexpr int kMax = 64;          // EmMgr holds far fewer Ganados; extras are never parked
constexpr unsigned kHoldTicks = 45;
constexpr f32 kRange2 = (f32) (RE4DC_ACT_CAP_RANGE_M * 1000) * (f32) (RE4DC_ACT_CAP_RANGE_M * 1000);
constexpr f32 kViewR = (f32) (RE4DC_ACT_CAP_VIEW_M * 1000);
constexpr f32 kBodyY = 900.0f;     // sphere centre above the feet
constexpr f32 kBodyR = 1200.0f;    // Ganado body radius

struct Entry {
    cEm* em;
    u32 serial;
    u32 activeSince;   // tick it last became active
    u8 parked;
    u8 seen;
    u8 must;
    u8 slot;
    f32 key;
#if RE4DC_FAR_HALF
    u8 fh;      // eligible for the half rate this tick
    u8 phase;   // 1 = this tick is the reduced one
#endif
};
Entry g_e[kMax];
int g_n;
u32 g_tick;
#if RE4DC_FAR_HALF
// FH census (RE4DC_FAR_HALF_LOG): per window, ticks with live Ganados, live / eligible / reduced sums and maxima,
// reduced ticks dropped by a late damage / death (late), and wake-ups (eligible -> ineligible transitions).
struct FhStats {
    u32 ticks, live, elig, red, late, wakes, maxLive, maxElig;
    u32 near, thr, view, thrOnly, rtn, rtnMask[4];   // FAR_HALF_LOG reasons (sums), the last refused routine r_no_0/1
    u32 fogged;                                        // in the frustum but beyond the draw range
} g_fh;
#endif

// Stats (RE4DC_ACT_CAP_LOG): per window, max/sum of the per-tick counts.
struct Stats {
    u32 ticks, live, act, park, must, eng, threat, creep, resumes, parks;
    u32 maxLive, maxAct, maxEng, maxThreat;
} g_st;

inline bool isGanado(const cEm* e) { return e->id >= 0x10 && e->id <= 0x20; }

// Never-park states (routine numbers: em10.cpp:588-708, EM_RTN / EmRoutineSet em10.cpp:549-562).
bool threat(cEm* e)
{
    // r_no_0: 0 init, 2 damage, 3 die, 4 scenario. A Ganado only reaches r_no_0 = 0xFF (deleted,
    // counted as a kill by SceCountEmAlive) by running its die routine, and the die routine clears
    // EM_STATUS_ACTIVE (em10.cpp:16036): parking one there would stall r101's kill count.
    if (e->r_no_0 != 1) return true;
    // r_no_1: park only walking / idle routines (whitelist). Everything else stays active:
    // find 0x0D (em10SomebodyFindNowCk blocks the others' shout), attacks 0x21-0x32 / 0x6D, grabs
    // 0x33-0x3A, door / window bash 0x3D / 0x3F (one basher at a time, em10DootAtkCk), ladders and
    // jumps 0x40-0x45, falls, knock-down / wake, pickups, fuse lighting and every scripted routine.
    switch (e->r_no_1) {
    case 0x00: case 0x01: case 0x02:             // Wait, Keeper, Hide
    case 0x07: case 0x08: case 0x09:             // r101 Bucket, Suki, Cart (village idles)
    case 0x10: case 0x11: case 0x12: case 0x13:  // Walk, Dash, Back, Goto
    case 0x14: case 0x15:                        // GuardWalk, Turn180
    case 0x1A: case 0x1B: case 0x1D:             // SitDown, Stay, Guard
    case 0x4C: case 0x4E: case 0x4F:             // R100WalkStay, StayWalk, AttackWait
    case 0x5D:                                   // FindLost
        break;
    default:
        return true;
    }
    if (pPL->dmgType == (int) e) return true;   // holds the player (EmCatchPLSet, em_sub.cpp:2453)
    return false;
}

bool inView(const cEm* e)
{
    GeoSphere s;
    s.pos.x = e->pos.x;
    s.pos.y = e->pos.y + kBodyY;
    s.pos.z = e->pos.z;
    s.r = kBodyR + kViewR;
    return collision_sphere_hexahedron(&s, (GeoHexahedron*) CameraViewFrustumPtr(&pG->Cam)) != 0;
}

bool roomOn()
{
#if RE4DC_FAR_HALF && !RE4DC_ACT_CAP && !RE4DC_ACT_CAP_TABLE
    return false;   // FAR_HALF built without a cap: the cap never parks
#endif
#if defined(RE4DC_DBG_WARP) && RE4DC_DBG_WARP
    // late-activation arms (warp_late.h): the cap works only once the late mask's bit 8 is open
    if (RE4DC_WARP_LATE_SET() && !RE4DC_WARP_LATE(RE4DC_LATE_ACT_CAP)) return false;
#endif
    if (!pG || !pPL) return false;
#if RE4DC_ACT_CAP_TABLE
    {
        const u32 room = ((u32) pG->stage_no << 8) | pG->room_no;
        const RoomCap* rc = 0;
        for (const RoomCap& t : kRoomCaps)
            if (t.room == room) { rc = &t; break; }
        if (!rc || (rc->flags & kScripted)) return false;
        g_cap = rc->cap;
    }
#else
    if (RE4DC_ACT_CAP_ROOM && (((u32) pG->stage_no << 8) | pG->room_no) != (u32) RE4DC_ACT_CAP_ROOM) return false;
    g_cap = RE4DC_ACT_CAP;
#endif
    // event pause / frozen characters: emMove already skips or the scene is scripted
    if (pG->Status_flg[1] & 0x10000000) return false;
    if (pG->Stop_flg & 0x20000000) return false;
    return true;
}

Entry* find(cEm* e)
{
    for (int i = 0; i < g_n; i++)
        if (g_e[i].em == e && g_e[i].serial == e->serial) return &g_e[i];
    if (g_n == kMax) return 0;
    Entry& n = g_e[g_n++];
    n.em = e; n.serial = e->serial; n.activeSince = g_tick; n.parked = 0; n.seen = 0; n.must = 0;
    n.slot = (u8) (g_n - 1); n.key = 0.0f;
#if RE4DC_FAR_HALF
    n.fh = 0; n.phase = (u8) (e->serial & 1);   // staggers the reduced ticks of a group
#endif
    return &n;
}

#if RE4DC_FAR_HALF
// FAR_HALF: on screen = inside the last view frustum (inflated as the cap's test) and nearer than the draw range. The
// draw range is the build's FOG_FAR (RE4DC_FAR_HALF_DRAW_MM, millimetre-scale source units; 0 = none): the Dreamcast fog
// table reaches 100 % there and actors and scenery are culled at it, so an in-frustum Ganado beyond it is not on screen.
bool onScreen(const cEm* e, f32 d2)
{
#if defined(RE4DC_FAR_HALF_DRAW_MM) && RE4DC_FAR_HALF_DRAW_MM > 0
    constexpr f32 kDraw = (f32) RE4DC_FAR_HALF_DRAW_MM + kBodyR + kViewR;
    if (d2 > kDraw * kDraw) return false;
#endif
    return inView(e);
}

// FAR_HALF: may this tick reduce anything at all (same pauses as roomOn, plus the swapped sub screen lists).
bool farHalfOn()
{
#if defined(RE4DC_FAR_HALF_RT) && RE4DC_FAR_HALF_RT
    if (!re4dc_far_half_rt) return false;
#endif
    if (!pG || !pPL) return false;
    if (re4dc_ss_ui_order && re4dc_ss_ui_order()) return false;
    if (pG->Status_flg[1] & 0x10000000) return false;
    if (pG->Stop_flg & 0x20000000) return false;
    return true;
}

void logFarHalf()
{
#if RE4DC_FAR_HALF_LOG
    if (g_fh.ticks < RE4DC_FAR_HALF_LOG) return;
    const unsigned t = g_fh.ticks;
    re4dc_log("FH t=%u rm=%x n=%u mode=%u live=%u/%u elig=%u/%u red=%u late=%u wake=%u near=%u view=%u thr=%u "
              "thronly=%u fog=%u rtn=%x mask=%08x,%08x,%08x,%08x\n", (unsigned) pG->Frame_cnt,
              ((unsigned) pG->stage_no << 8) | pG->room_no, t, (unsigned) RE4DC_FAR_HALF, g_fh.live * 10 / t,
              g_fh.maxLive, g_fh.elig * 10 / t, g_fh.maxElig, g_fh.red, g_fh.late, g_fh.wakes, g_fh.near * 10 / t,
              g_fh.view * 10 / t, g_fh.thr * 10 / t, g_fh.thrOnly * 10 / t, g_fh.fogged * 10 / t, (unsigned) g_fh.rtn,
              (unsigned) g_fh.rtnMask[0],
              (unsigned) g_fh.rtnMask[1], (unsigned) g_fh.rtnMask[2], (unsigned) g_fh.rtnMask[3]);
    g_fh = FhStats();
#endif
}
#endif

void logStats()
{
#if RE4DC_ACT_CAP_LOG
    if (g_st.ticks < RE4DC_ACT_CAP_LOG) return;
    const unsigned t = g_st.ticks;
    re4dc_log("AC t=%u n=%u live=%u/%u act=%u/%u park=%u must=%u eng=%u/%u thr=%u/%u creep=%u res=%u prk=%u\n",
              (unsigned) pG->Frame_cnt, t, g_st.live * 10 / t, g_st.maxLive, g_st.act * 10 / t, g_st.maxAct,
              g_st.park * 10 / t, g_st.must * 10 / t, g_st.eng * 10 / t, g_st.maxEng, g_st.threat * 10 / t,
              g_st.maxThreat, g_st.creep, g_st.resumes, g_st.parks);
    g_st = Stats();
#endif
}
}  // namespace

// Called by cEmMgr::move once per tick, before the emMove loop. Reads game state only.
extern "C" void re4dc_act_cap_select(void)
{
    g_tick++;
    for (int i = 0; i < g_n; i++) g_e[i].seen = 0;
    const bool on = roomOn();
    int live = 0, must = 0, eng = 0, thr = 0;
    if (pPL) {
        for (cEm* e = EmMgr.pAlive; e; e = (cEm*) e->pNext) {
            if ((e->be_flag & 0x201) != 1 || !isGanado(e)) continue;
            Entry* x = find(e);
            if (!x) continue;
            x->seen = 1;
            live++;
            const f32 dx = pPL->pos.x - e->pos.x, dz = pPL->pos.z - e->pos.z;
            const f32 d2 = dx * dx + dz * dz;
            const bool t = threat(e);
            const bool near = d2 < kRange2;
            eng += near;
            thr += t;
#if defined(RE4DC_ACT_CAP_FAR_M) && RE4DC_ACT_CAP_FAR_M
            // ACT_CAP_FAR_M (game30.mk): beyond D metres the view rule no longer keeps a Ganado active
            constexpr f32 kFar2 = (f32) (RE4DC_ACT_CAP_FAR_M * 1000) * (f32) (RE4DC_ACT_CAP_FAR_M * 1000);
#if defined(RE4DC_BENCH_LEVERS) && RE4DC_BENCH_LEVERS
            const bool farOk = RE4DC_LEVER(RE4DC_LV_FAR) && d2 > kFar2;
#else
            const bool farOk = d2 > kFar2;
#endif
            x->must = !on || t || near || e->hp <= 0 || e->dmg.m_Flag || pPL->pLockEm == e ||
                      (!x->parked && g_tick - x->activeSince < kHoldTicks) || (!farOk && inView(e));
#else
            x->must = !on || t || near || e->hp <= 0 || e->dmg.m_Flag || pPL->pLockEm == e ||
                      (!x->parked && g_tick - x->activeSince < kHoldTicks) || inView(e);
#endif
            x->key = x->parked ? d2 : d2 * 0.64f;
            must += x->must;
        }
    }
    // drop entries whose Ganado is gone (dead, destroyed, room change)
    int w = 0;
    for (int i = 0; i < g_n; i++)
        if (g_e[i].seen) { g_e[w] = g_e[i]; g_e[w].slot = (u8) w; w++; }
    g_n = w;
    // fill the free slots nearest first (selection by repeated minimum: n is small)
    int slots = on ? g_cap - must : 0;   // off: every Ganado is a must anyway
    for (int i = 0; i < g_n; i++) g_e[i].seen = g_e[i].must;   // seen = chosen active
    while (slots-- > 0) {
        int best = -1;
        for (int i = 0; i < g_n; i++)
            if (!g_e[i].seen && (best < 0 || g_e[i].key < g_e[best].key)) best = i;
        if (best < 0) break;
        g_e[best].seen = 1;
    }
    int act = 0, park = 0;
    for (int i = 0; i < g_n; i++) {
        Entry& x = g_e[i];
        const u8 p = !x.seen;
        if (x.parked && !p) { x.activeSince = g_tick; g_st.resumes++; }
        if (!x.parked && p) g_st.parks++;
        x.parked = p;
        act += !p; park += p;
    }
#if RE4DC_FAR_HALF
    // FAR_HALF: which of the cap's active Ganados take this tick reduced (strict alternation while eligible)
    {
        constexpr f32 kFh2 = (f32) (RE4DC_FAR_HALF_M * 1000) * (f32) (RE4DC_FAR_HALF_M * 1000);
        const bool fon = farHalfOn();
        int elig = 0, red = 0;
        for (int i = 0; i < g_n; i++) {
            Entry& x = g_e[i];
            cEm* e = x.em;
            bool f = false;
            if (fon && !x.parked) {
                const f32 dx = pPL->pos.x - e->pos.x, dz = pPL->pos.z - e->pos.z;
                const f32 d2 = dx * dx + dz * dz;
                f = d2 > kFh2 && !threat(e) && e->hp > 0 && !e->dmg.m_Flag && pPL->pLockEm != e && !onScreen(e, d2);
#if RE4DC_FAR_HALF_LOG
                // census of the reasons (each counted on its own) and the routines the whitelist refused
                const bool nr = d2 <= kFh2, th = threat(e), vw = onScreen(e, d2);
                g_fh.near += nr; g_fh.thr += th; g_fh.view += vw; g_fh.fogged += inView(e) && !vw;
                if (th && !nr && !vw) {   // far and unseen, refused only for its routine
                    g_fh.thrOnly++;
                    g_fh.rtn = ((u32) e->r_no_0 << 8) | e->r_no_1;
                    if (e->r_no_0 == 1 && e->r_no_1 < 128) g_fh.rtnMask[e->r_no_1 >> 5] |= 1u << (e->r_no_1 & 31);
                }
#endif
            }
            if (f) {
                x.phase ^= 1;
                elig++;
                red += x.phase;
            } else {
                if (x.fh) g_fh.wakes++;
                x.phase = (u8) (x.serial & 1);
            }
            x.fh = f;
        }
        if (live) {
            g_fh.ticks++; g_fh.live += live; g_fh.elig += elig; g_fh.red += red;
            if ((u32) live > g_fh.maxLive) g_fh.maxLive = live;
            if ((u32) elig > g_fh.maxElig) g_fh.maxElig = elig;
            logFarHalf();
        }
    }
#endif
#if RE4DC_ACT_CAP_LOG
    if (live) {
        g_st.ticks++; g_st.live += live; g_st.act += act; g_st.park += park; g_st.must += must;
        g_st.eng += eng; g_st.threat += thr;
        if ((u32) live > g_st.maxLive) g_st.maxLive = live;
        if ((u32) act > g_st.maxAct) g_st.maxAct = act;
        if ((u32) eng > g_st.maxEng) g_st.maxEng = eng;
        if ((u32) thr > g_st.maxThreat) g_st.maxThreat = thr;
        logStats();
    }
#else
    (void) act; (void) park; (void) eng; (void) thr;
#endif
}

// 1 when cEmMgr::move must skip this work's emMove this tick (parked and not its creep tick).
extern "C" int re4dc_act_cap_parked(cEm* e)
{
    for (int i = 0; i < g_n; i++) {
        const Entry& x = g_e[i];
        if (x.em != e) continue;
#if RE4DC_FAR_HALF
        // FAR_HALF: an active Ganado on its reduced tick -> 1 (=2: skip emMove) or 2 (=1: pose skip), unless it
        // was hit or killed earlier in this tick
        if (!x.parked && x.serial == e->serial && x.fh && x.phase) {
            if ((e->be_flag & 0x201) != 1 || e->hp <= 0 || e->dmg.m_Flag) {
                g_fh.late++;
                return 0;
            }
            return RE4DC_FAR_HALF == 2 ? 1 : 2;
        }
#endif
        if (!x.parked || x.serial != e->serial) return 0;
        // hit or killed earlier in this tick (explosion, another Ganado): react this tick
        if ((e->be_flag & 0x201) != 1 || e->hp <= 0 || e->dmg.m_Flag) return 0;
#if RE4DC_ACT_CAP_CREEP
        if ((g_tick + x.slot) % RE4DC_ACT_CAP_CREEP == 0) {
            g_st.creep++;
            return 0;
        }
#endif
        return 1;
    }
    return 0;
}
