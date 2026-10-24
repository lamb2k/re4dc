// game/em_set.cpp: enemy creation from the room enemy list (ESL). pG->Em_list holds 256 EmListData
// entries (id, type, set, flag, hp, position in 10 unit steps, rotation in 1/16384 turns, stage /
// room); EmSetFromList creates every entry of the current room at room start and event code
// creates single entries with EmSetFromList2. Killed list enemies are recorded per list in the
// pG->em_dead bit tables so they stay dead when the room is re-entered.

#include "atari.h"
#include "light.h"
#include "em_set.h"
#if defined(RE4DC_ALIVE_CAP_DEFER_GOTO_R207) && RE4DC_ALIVE_CAP_DEFER_GOTO_R207
#include "em_wrap.h"  // original typed Ganado virtual setter
#endif
#if defined(RE4DC_ALIVE_CAP_R202_GATE) && RE4DC_ALIVE_CAP_R202_GATE
#include "alive_cap_r202_gate.h"
#endif
#include "global.h"
#include "db_log.h"
#if defined(RE4DC_GAME) && !defined(__PPC__) && defined(RE4DC_ISSUE52_ACTOR_DIAG) && RE4DC_ISSUE52_ACTOR_DIAG
#include "scheduler.h"
#include "issue52_actor_diag.h"
extern "C" unsigned long re4dc_issue52_source_task()
{
    // Same actual-thread mapping as NativeExecutingTask in scheduler.cpp.
    // pCTask alone can name a different source task while native I/O yields.
    OSThread* self = OSGetCurrentThread();
    for (u32 i = 0; i < TASK_NUM; ++i)
        if (&Task[i].Thread == self) return (unsigned long) &Task[i];
    return 0; // Outside a source task: collect no attributed evidence.
}
#endif
#if defined(RE4DC_ALIVE_CAP_NOVIS) && RE4DC_ALIVE_CAP_NOVIS
#include "flag_rsf.h"
#endif

extern cEm* pPL;   // game/em.cpp

cEm* errEm = 0;
static int emSetDummy = 0;

// Death bit of list entry `no` in the current enemy list (0 when no list is loaded).
// Death bit table of the current enemy list (pG->em_dead[pG->emlist_no]); the original computes
// it with byte arithmetic: the row offset is added to pG before the table offset.
#define EM_DEAD_TBL() ((u32*) (pG->em_list_no * 0x20 + (u32) pG + 0x501C))

// Death bit of list entry `no` in the current list (pG->em_list_no); 0 when no list is loaded.
static inline u32 EmSetDieCk(u32 no)
{
    u32 v;

    if (pG->em_list_no >= 0) {
        u32* tbl = EM_DEAD_TBL();

        v = tbl[no >> 5] & (0x80000000 >> (no & 31));
    } else {
        v = 0;
    }
    return v;
}

// Sets the death bit of list entry `no` in the current list.
static inline void EmSetDieOn(u32 no)
{
    if (pG->em_list_no >= 0) {
        u32* tbl = EM_DEAD_TBL();

        tbl[no >> 5] |= 0x80000000 >> (no & 31);
    }
}

// Counter update through a reference: the store is a plain scalar access, so pG is reloaded after it.
static inline void CntInc(u32& c) { c++; }

// While flags_68 bit21 is set only the enemies 3 and 4 may be created.
#define EM_SET_ID_NG(id) ((pG->Debug_flg[2] & 0x00200000) && ((id) != 3 && (id) != 4))

// Pulls an enemy work for `id`: the partner (0xF) and the parasite (0x25) are created at the back
// of the pool so they move after the others.
static inline cEm* EmCreate(u8 id)
{
    if (id == 0xF || id == 0x25) {
        return EmMgr.createBack(id);
    }
    return EmMgr.create(id);
}

// Copy the list entry into the fresh enemy work.
static inline void EmSetWork(cEm* em, EmListData* d, u8 no)
{
    f32 kx = 1000.0f;
    f32 kr = 3.1415927f / 16384.0f;
    f32 kp = 10.0f;

    em->type = d->type;
    em->set = d->set;
    em->flag = d->flag;
    em->Character = d->Character;
    em->Guard_r = (f32) d->Guard_r * kx;
    em->hp_max = em->hp = d->hp;
    em->ang.x = (f32) d->rot[0] * kr;
    em->ang.y = (f32) d->rot[1] * kr;
    em->ang.z = (f32) d->rot[2] * kr;
    em->pos.x = (f32) d->pos[0] * kp;
    em->pos.y = (f32) d->pos[1] * kp;
    em->pos.z = (f32) d->pos[2] * kp;
    em->pos_old = em->pos;
    em->emset_no = no;
}

// The same body as a macro for the two straight-line creators (EmSetFromList2, EmSetEvent). A pool
// constant expanded in the caller keeps RTX_UNCHANGING_P on its MEM; integrate.c drops it when it
// copies an inlined body (copy_rtx_and_substitute, `map->integrating`), so the inline's `lfs` loads
// carry true/anti dependences on every store around them and haifa cannot move them (they end up
// as `lis; lfs` pairs at the top of the block in the original). The loop in EmSetFromList keeps the
// inline (the invariants are hoisted differently with the macro: 11 words).
#define EM_SET_WORK(em, d, no)                                                            \
    do {                                                                                  \
        f32 kx = 1000.0f;                                                                 \
        f32 kr = 3.1415927f / 16384.0f;                                                   \
        f32 kp = 10.0f;                                                                   \
        (em)->type = (d)->type;                                                           \
        (em)->set = (d)->set;                                                             \
        (em)->flag = (d)->flag;                                                    \
        (em)->Character = (d)->Character;                                                             \
        (em)->Guard_r = (f32) (d)->Guard_r * kx;                                                 \
        (em)->hp_max = (em)->hp = (d)->hp;                                                 \
        (em)->ang.x = (f32) (d)->rot[0] * kr;                                             \
        (em)->ang.y = (f32) (d)->rot[1] * kr;                                             \
        (em)->ang.z = (f32) (d)->rot[2] * kr;                                             \
        (em)->pos.x = (f32) (d)->pos[0] * kp;                                             \
        (em)->pos.y = (f32) (d)->pos[1] * kp;                                             \
        (em)->pos.z = (f32) (d)->pos[2] * kp;                                             \
        (em)->pos_old = (em)->pos;                                                         \
        (em)->emset_no = (no);                                                             \
    } while (0)

// Squared XZ distance to the player. The `x374 = 1e16` reset is a caller statement AFTER this call:
// inside the inline its pool load loses RTX_UNCHANGING_P (see above) and wins the sched1 tie against
// the `dz * dz` multiply through the "independent of the last scheduled insn" class (haifa
// rank_for_schedule), which puts the constant one insn too early and costs it f12 (local-alloc's
// fake_birth avoids a register that died in the previous insn).
static inline void EmSetDist(cEm* em)
{
    f32 dz = pPL->pos.z - em->pos.z;
    f32 dx = pPL->pos.x - em->pos.x;

    em->plDist2 = dx * dx + dz * dz;
}

// Work `no` with the range check read through a manager copy (map_obj.h getWork). A plain
// `for (i = 0; i < EmMgr.nArray; i++)` around it gives the original shape: gcse PRE turns the second
// nArray read into a copy of the first (`mr r10, r0`), the bottom test uses that copy and the back
// edge is threaded past the check.
static inline cEm* emSetWork(u32 no)
{
    cEmMgr* m = &EmMgr;
    if (no >= m->nArray) {
        return 0;
    }
#if !defined(__PPC__)
    return m->workAt(no);
#else
    return (cEm*) ((u8*) m->pArray + m->size * no);
#endif
}

// 1 when no live enemy already carries list entry `no` (0xFF: always 1).
int checkListId(int no)
{
    u32 i;

    if (no == 0xFF) {
        return 1;
    }
    for (i = 0; i < EmMgr.nArray; i++) {
        cEm* em = emSetWork(i);
#if !defined(__PPC__)
        if (!em) continue;
#endif

        if ((em->be_flag & 0x201) == 1 && em->emset_no == (u8) no) {
            return 0;
        }
    }
    return 1;
}

#if defined(RE4DC_ALIVE_CAP) && RE4DC_ALIVE_CAP
// ALIVE_CAP=N (Makefile; lane alivecap 2026-10-15, user rule 10-15 "Ganados at 6"; CHANGES GAMEPLAY by design):
// at most N Ganados (ids 0x10..0x20, the range the room scripts count with SceCountEmAlive) alive at once, game
// wide. Start-list Ganados beyond N are held at room entry: not created, their list entry left as it is (alive,
// not set), so a re-entry or a load starts the same way. Held ones come in one at a time through EmSetFromList2
// (death bits honoured), at least 30 frames apart, outside events and pauses, while fewer than N are alive, the
// one farthest from Leon first. SceCountEmAlive counts the held entries as alive, so every room script's alive
// test, wave trigger and kill count (base - alive) reads exactly as without the cap; SceDestroyEm drops held
// entries of its range as it destroys live ones. A held entry that room code sends itself (setEm /
// cEmWrap::setPtr: they create through EmSetFromList2) follows the send rule below; a Ganado this cap lets in counts
// toward N from its creation, before its first ACTIVE frame (aliveCapLive's fresh list). A room-code send (EmSetFromList2, also under setEm / cEmWrap) of a
// Ganado while N are alive is deferred the same way: it returns errEm (no enemy) and the entry joins the hold,
// except the entries whose callers dereference the returned enemy unchecked (aliveCapKeep: those rooms are the
// documented exceptions and may pass N). Census and gates: C:\Game Dev\Emulators\ALIVECAP-20261015.md.
// r101 is skipped when R101_ALIVE_CAP (the same N) runs its own hold / queue (RE4DC_ALIVE_CAP_R101).
#ifndef RE4DC_ALIVE_CAP_LOG
#define RE4DC_ALIVE_CAP_LOG 0
#endif
#ifndef RE4DC_ALIVE_CAP_PARK
#define RE4DC_ALIVE_CAP_PARK 0
#endif
#if RE4DC_ALIVE_CAP_PARK
#include "camera.h"
#include "geometry.h"
#endif
extern "C" void OSReport(const char* fmt, ...);
static u8 aliveCapHeld[64];
static u8 aliveCapSent[64];   // 1: a deferred room-code send (its list alive bit is the caller's business)
static int aliveCapN;
static u32 aliveCapLast;
static int aliveCapReleasing;
#if defined(RE4DC_ALIVE_CAP_DEFER_FLAGS) && RE4DC_ALIVE_CAP_DEFER_FLAGS
// OR commands belong to the queued ESL entry, shared by every room handle.
// Keep cEmWrap's original 12-byte ABI; 64 masks cost 256 bytes only when enabled.
static u32 aliveCapPendingFlags[64];
#endif
#if defined(RE4DC_ALIVE_CAP_DEFER_GOTO_R207) && RE4DC_ALIVE_CAP_DEFER_GOTO_R207
// Bounded r207 pilot only: copy the command, never borrow a caller Vec or grow
// cEmWrap. Valid is separate from mode (mode 0 is a real source command).
struct AliveCapPendingGoto { Vec pos; int mode; u32 valid, firstFlags; };
static_assert(sizeof(AliveCapPendingGoto) == 24, "deferred Goto record");
static AliveCapPendingGoto aliveCapPendingGoto[64];
#endif

// Sends never deferred: the room code dereferences the returned enemy without a check (census 2026-10-15).
// r100 ambush 03-05 (ems[0..2]), fire trio 06-08 (event motion), house Ganado 0x25; r10c entry 02 and the ambush
// 06-0C (ems[0..6]); r10f the gondola riders and 32 / 35; r11c (GameCube cabin, bit 0x40 off) Luis C8 and C9-D1.
static const u32 aliveCapKeepTbl[] = {
    0x10003, 0x10004, 0x10005, 0x10006, 0x10007, 0x10008, 0x10025,
    0x10C02,
#if !(defined(RE4DC_ROUTE_CH21_FULL) && RE4DC_ROUTE_CH21_FULL)
    // ROUTE_CH21_FULL (lane ch2rooms20): r10c's ambush checks its sends, so 06-0C go through the cap (held, not kept).
    0x10C06, 0x10C07, 0x10C08, 0x10C09, 0x10C0A, 0x10C0B, 0x10C0C,
#endif
#if defined(RE4DC_ROUTE_CH3) && RE4DC_ROUTE_CH3
    // Island (stage 3 lane census 2026-10-15): r300 the gate event Ganado 0x4B (setEvtMotion on getPtr()),
    // r303 entry 0x24 (em->flag / EstSet on the return).
    0x3004B, 0x30324,
    // r327 (ch5found16 switch run 10-17): the Ganado that disables the lamp switch, 0x9E (r327_SetSwitchDisable
    // em2.setEm inside the disable cut), and the gatling Ganado 0x7C (r327_GatlingGanadoSet em[3], hp 5000, its own cut).
    // Both are sent during their events; held by the cap they were dropped by the appear cut's far delete.
    0x3279E, 0x3277C,
#endif
};
static int aliveCapKeep(int no)
{
    const u32 key = ((u32) (pG->stage_no << 8 | pG->room_no) << 8) | (u32) no;
    u32 k;

    for (k = 0; k < sizeof(aliveCapKeepTbl) / sizeof(aliveCapKeepTbl[0]); k++) {
        if (aliveCapKeepTbl[k] == key) {
            return 1;
        }
    }
    if ((key >> 8) == 0x10F) {   // r10f: 32, 35 and the gondola riders 36-3B, 4B-4F
        return no == 0x32 || no == 0x35 || (no >= 0x36 && no <= 0x3B) || (no >= 0x4B && no <= 0x4F);
    }
    if ((key >> 8) == 0x11C) {   // r11c: Luis and the GameCube cabin nine
        return no >= 0xC8 && no <= 0xD1;
    }
    return 0;
}

static inline int aliveCapGanado(int id)
{
    return id >= 0x10 && id <= 0x20;
}

// I-006 (user 2026-10-18): castle Novistadors share the Ganado budget.
// Reuse the held ESL queue, never park an existing Novistador: castle room
// scripts retain wrappers/pointers and parking would retire their work.
#if defined(RE4DC_ALIVE_CAP_NOVIS) && RE4DC_ALIVE_CAP_NOVIS
static inline int aliveCapEnemy(int id)
{
    return aliveCapGanado(id) || (pG->stage_no == 2 && id == 0x2D);
}
#else
#define aliveCapEnemy aliveCapGanado
#endif

#if defined(RE4DC_ALIVE_CAP_NOVIS) && RE4DC_ALIVE_CAP_NOVIS
// r213's statue callback acts on every wrapper, including held sends. Restore
// its persistent source state on later admission, after the original first
// move: C5/C8 must die through their own routine, never vanish from the queue.
static void aliveCapRestoreNovisRoom(cEm* em, int no)
{
    if (!aliveCapReleasing || !em || em == errEm || em->id != 0x2D) {
        return;
    }
    // r205_Em88Appear sets this alert flag immediately after its send.
    if (pG->room_id == 0x205 && no == 0x58 && RsfCheck(0x205, 8)) {
        em->flag |= 1;
    }
    if (pG->room_id != 0x213 || no < 0xC2 || no > 0xCA || !RsfCheck(0x213, 2)) {
        return;
    }
    em->flag |= 0x20000000;
    if (no == 0xC5 || no == 0xC8) {
        em->hp = 0;
    }
}
#endif

// A held entry still waiting: not set, of the current room, and (start-list holds) still alive in the list.
static int aliveCapWaitingK(int k)
{
    const int no = aliveCapHeld[k];
    EmListData* d = EM_LIST(no);

    if (d->be_flag & 2) {
        return 0;
    }
    if (!aliveCapSent[k] && !(d->be_flag & 1)) {
        return 0;
    }
    return pG->stage_no == d->room >> 8 && pG->room_no == (d->room & 0xFF);
}

#if defined(RE4DC_ALIVE_CAP_DEFER_FLAGS) && RE4DC_ALIVE_CAP_DEFER_FLAGS
// Preserve source setFlag calls while no actor exists. Do not change the ESL
// record or create/activate an actor merely to deliver a command.
extern "C" int re4dc_aliveCapSetFlag(int no, u32 bits)
{
    for (int k = 0; k < aliveCapN; k++) {
        if (aliveCapHeld[k] == no && aliveCapWaitingK(k)) {
            aliveCapPendingFlags[k] |= bits;
            return 1;
        }
    }
    return 0;
}

#if defined(RE4DC_ALIVE_CAP_DEFER_GOTO_R207) && RE4DC_ALIVE_CAP_DEFER_GOTO_R207
static int aliveCapGotoR207Eligible(int no, int id)
{
    return pG->room_id == 0x207 && no >= 0 && no < 256 &&
           EM_LIST(no)->room == 0x207 && EM_LIST(no)->id == id &&
           id >= 0x10 && id <= 0x20 && id != 0x18;
}

extern "C" int re4dc_aliveCapSetGotoR207(int no, const Vec* pos, int mode)
{
    if (!pos || no < 0 || no >= 256 || !aliveCapGotoR207Eligible(no, EM_LIST(no)->id)) return 0;
    for (int k = 0; k < aliveCapN; k++) {
        if (aliveCapHeld[k] == no && aliveCapWaitingK(k)) {
            AliveCapPendingGoto& command = aliveCapPendingGoto[k];
            if (!command.valid) command.firstFlags = aliveCapPendingFlags[k];
            command.pos = *pos;
            command.mode = mode;
            command.valid = 1;
            return 1;
        }
    }
    return 0;
}

extern "C" int re4dc_aliveCapGetGotoR207(int no, int* mode)
{
    if (!mode || no < 0 || no >= 256 || !aliveCapGotoR207Eligible(no, EM_LIST(no)->id)) return 0;
    for (int k = 0; k < aliveCapN; k++) {
        if (aliveCapHeld[k] == no && aliveCapWaitingK(k) && aliveCapPendingGoto[k].valid) {
            *mode = aliveCapPendingGoto[k].mode;
            return 1;
        }
    }
    return 0;
}

// Original first AI init already ran. The first Goto's OR snapshot preserves
// setGoto's sticky work-flag 0x100 effect; applying the final OR mask first would
// lose it. Only the latest copied target/mode is needed. Do not cast Novistadors.
static void aliveCapDeliverGotoR207(cEm* em, int no, u32 bits, const AliveCapPendingGoto& command)
{
    if (command.valid && aliveCapGotoR207Eligible(no, em->id)) {
        em->flag |= command.firstFlags;
        Vec pos = command.pos;
        ((cEmGanado*) em)->setGoto(&pos, command.mode);
    }
    em->flag |= bits;
}
#endif

// A direct repeat send or room-start creation can consume a held entry without
// Take/Move removing it first. Deliver only after the original first AI move.
static void aliveCapApplyPending(cEm* em, int no)
{
    for (int k = 0; k < aliveCapN; k++) {
        if (aliveCapHeld[k] == no) {
#if defined(RE4DC_ALIVE_CAP_DEFER_GOTO_R207) && RE4DC_ALIVE_CAP_DEFER_GOTO_R207
            aliveCapDeliverGotoR207(em, no, aliveCapPendingFlags[k], aliveCapPendingGoto[k]);
            aliveCapPendingGoto[k] = {};
#else
            em->flag |= aliveCapPendingFlags[k];
#endif
            aliveCapPendingFlags[k] = 0;
            return;
        }
    }
}

// Allocation refusal must not consume a queued command or its original order.
// A failed creator has not run first AI initialization, so it cannot insert a
// new hold. Explicit death/room invalidation still discards the old command.
static void aliveCapRestorePending(int slot, int no, int sent, u32 bits
#if defined(RE4DC_ALIVE_CAP_DEFER_GOTO_R207) && RE4DC_ALIVE_CAP_DEFER_GOTO_R207
                                   , const AliveCapPendingGoto& command
#endif
                                   )
{
    EmListData* d = EM_LIST(no);
    if (EmSetDieCk(no) || (d->be_flag & 2) || (!sent && !(d->be_flag & 1)) ||
        pG->stage_no != d->room >> 8 || pG->room_no != (d->room & 0xFF)) {
        return;
    }
    for (int j = aliveCapN; j > slot; j--) {
        aliveCapHeld[j] = aliveCapHeld[j - 1];
        aliveCapSent[j] = aliveCapSent[j - 1];
        aliveCapPendingFlags[j] = aliveCapPendingFlags[j - 1];
#if defined(RE4DC_ALIVE_CAP_DEFER_GOTO_R207) && RE4DC_ALIVE_CAP_DEFER_GOTO_R207
        aliveCapPendingGoto[j] = aliveCapPendingGoto[j - 1];
#endif
    }
    aliveCapHeld[slot] = (u8) no;
    aliveCapSent[slot] = (u8) sent;
    aliveCapPendingFlags[slot] = bits;
#if defined(RE4DC_ALIVE_CAP_DEFER_GOTO_R207) && RE4DC_ALIVE_CAP_DEFER_GOTO_R207
    aliveCapPendingGoto[slot] = command;
#endif
    aliveCapN++;
}
#endif

// Adds entry `no` to the hold unless it is there already (a deferred init send the start list meets again).
static void aliveCapPush(int no, int sent)
{
    int k;

    for (k = 0; k < aliveCapN; k++) {
        if (aliveCapHeld[k] == no) {
            return;
        }
    }
    if (aliveCapN < (int) sizeof(aliveCapHeld)) {
#if defined(RE4DC_ALIVE_CAP_DEFER_FLAGS) && RE4DC_ALIVE_CAP_DEFER_FLAGS
        aliveCapPendingFlags[aliveCapN] = 0;
#if defined(RE4DC_ALIVE_CAP_DEFER_GOTO_R207) && RE4DC_ALIVE_CAP_DEFER_GOTO_R207
        aliveCapPendingGoto[aliveCapN] = {};
#endif
#endif
        aliveCapSent[aliveCapN] = (u8) sent;
        aliveCapHeld[aliveCapN++] = (u8) no;
    }
}

// Ganados created from the list (start list, sends, releases) in the last 600 frames that are alive but not yet
// ACTIVE (coordinator decision 10-15, st3 lane r301: a Ganado that spawns in - not ACTIVE for its first frames -
// was not counted, so back-to-back sends in that window passed N; r301 reached 7). They count toward N from their
// creation; the room scripts' own SceCountEmAlive is unchanged (PS2 semantics).
#define ALIVE_CAP_FRESH 16
static cEm* aliveCapFreshEm[ALIVE_CAP_FRESH];
static u32 aliveCapFreshF[ALIVE_CAP_FRESH];
static u8 aliveCapFreshNo[ALIVE_CAP_FRESH];

static int aliveCapRoom();

static void aliveCapNoteFresh(cEm* em, int no)
{
    int k, slot = 0;
    u32 oldest = 0;

    if (em == 0 || em == errEm || !aliveCapEnemy(em->id) || !aliveCapRoom()) {
        return;
    }
    for (k = 0; k < ALIVE_CAP_FRESH; k++) {
        if (aliveCapFreshEm[k] == 0) {
            slot = k;
            break;
        }
        if ((u32) (pG->Frame_cnt - aliveCapFreshF[k]) >= oldest) {
            oldest = (u32) (pG->Frame_cnt - aliveCapFreshF[k]);
            slot = k;
        }
    }
    aliveCapFreshEm[slot] = em;
    aliveCapFreshF[slot] = pG->Frame_cnt;
    aliveCapFreshNo[slot] = (u8) no;
}

// Live Ganados: SceCountEmAlive's own test (alive and ACTIVE), plus fresh ones not yet ACTIVE; without the held
// entries.
static int aliveCapLive()
{
    int cnt = 0;
    u32 i;
    int k;

    for (i = 0; i < EmMgr.nArray; i++) {
        cEm* em = emSetWork(i);
        if (!em) continue;
        if (aliveCapEnemy(em->id) && em->isAlive() && em->checkStatus(EM_STATUS_ACTIVE) != 0) {
            cnt++;
        }
    }
    for (k = 0; k < ALIVE_CAP_FRESH; k++) {
        cEm* em = aliveCapFreshEm[k];

        if (em == 0) {
            continue;
        }
        if ((u32) (pG->Frame_cnt - aliveCapFreshF[k]) >= 600 || !em->isAlive() || !aliveCapEnemy(em->id) ||
            em->emset_no != aliveCapFreshNo[k] || em->checkStatus(EM_STATUS_ACTIVE) != 0) {
            aliveCapFreshEm[k] = 0;   // active (counted above), gone, reused or old
            continue;
        }
        cnt++;
    }
    return cnt;
}

static int aliveCapRoom()
{
#if defined(RE4DC_ALIVE_CAP_R101) && RE4DC_ALIVE_CAP_R101
    if (pG->stage_no == 1 && pG->room_no == 1) {
        return 0;   // r101: R101_ALIVE_CAP (same N)
    }
#endif
    return 1;
}

// cEmWrap (src/st/em_wrap.cpp; lane ch5found16 10-17, "held sends are alive"): 1 while list entry `no` waits in the
// hold. A room-script handle whose send the cap held reads alive and active until the entry is released (the handle
// re-attaches to the enemy) or dropped (dead), as the PS2, where the send was never held, would see it.
extern "C" int re4dc_aliveCapHeldEntry(int no)
{
    int k;

    for (k = 0; k < aliveCapN; k++) {
        if (aliveCapHeld[k] == (u8) no && aliveCapWaitingK(k)) {
            return 1;
        }
    }
    return 0;
}

// cEmWrap needs held entry `no` now: drop = 0 (getPtr: the room code uses the enemy) creates it over the cap, as a
// release would; drop = 1 (destroy) takes it out of the hold and clears its list alive bit, as a destroy does.
// Returns the enemy (0 when dropped or not created).
extern "C" cEm* re4dc_aliveCapTake(int no, int drop)
{
    int k, j, sent;
    cEm* em = 0;

    for (k = 0; k < aliveCapN; k++) {
        if (aliveCapHeld[k] == (u8) no && aliveCapWaitingK(k)) {
            break;
        }
    }
    if (k == aliveCapN) {
        return 0;
    }
    sent = aliveCapSent[k];
#if defined(RE4DC_ALIVE_CAP_DEFER_FLAGS) && RE4DC_ALIVE_CAP_DEFER_FLAGS
    const u32 pending = aliveCapPendingFlags[k];
#if defined(RE4DC_ALIVE_CAP_DEFER_GOTO_R207) && RE4DC_ALIVE_CAP_DEFER_GOTO_R207
    const AliveCapPendingGoto pendingGoto = aliveCapPendingGoto[k];
#endif
#endif
    for (j = k + 1; j < aliveCapN; j++) {
        aliveCapHeld[j - 1] = aliveCapHeld[j];
        aliveCapSent[j - 1] = aliveCapSent[j];
#if defined(RE4DC_ALIVE_CAP_DEFER_FLAGS) && RE4DC_ALIVE_CAP_DEFER_FLAGS
        aliveCapPendingFlags[j - 1] = aliveCapPendingFlags[j];
#if defined(RE4DC_ALIVE_CAP_DEFER_GOTO_R207) && RE4DC_ALIVE_CAP_DEFER_GOTO_R207
        aliveCapPendingGoto[j - 1] = aliveCapPendingGoto[j];
#endif
#endif
    }
    aliveCapN--;
    if (drop) {
        EM_LIST(no)->be_flag &= ~1;
    } else {
        aliveCapReleasing = 1;
        em = EmSetFromList2(no, 1);
        aliveCapReleasing = 0;
#if defined(RE4DC_ALIVE_CAP_DEFER_FLAGS) && RE4DC_ALIVE_CAP_DEFER_FLAGS
        if (em && em != errEm) {
#if defined(RE4DC_ALIVE_CAP_DEFER_GOTO_R207) && RE4DC_ALIVE_CAP_DEFER_GOTO_R207
            aliveCapDeliverGotoR207(em, no, pending, pendingGoto);
#else
            em->flag |= pending;
#endif
        } else {
            em = 0;
            aliveCapRestorePending(k, no, sent, pending
#if defined(RE4DC_ALIVE_CAP_DEFER_GOTO_R207) && RE4DC_ALIVE_CAP_DEFER_GOTO_R207
                                   , pendingGoto
#endif
                                   );
        }
#endif
        if (em && sent) {
            EmListSetAlive(no, 1);
        }
    }
#if RE4DC_ALIVE_CAP_LOG
    OSReport("alivecap: %s 0x%02x room %03x frame %u live %d held %d (room handle%s)\n", drop ? "drop" : "take", no,
             (unsigned) pG->room_id, (unsigned) pG->Frame_cnt, aliveCapLive(), aliveCapN,
             drop ? " destroy" : em ? " needs the enemy" : " needs the enemy: refused");
#endif
    return em;
}

// Held entries with id in lo..hi (hi -1 = just lo), added to SceCountEmAlive.
extern "C" int re4dc_aliveCapHeldCount(int lo, int hi)
{
    int cnt = 0;
    int k;

    if (hi == -1) {
        hi = lo;
    }
    for (k = 0; k < aliveCapN; k++) {
        const int no = aliveCapHeld[k];
        const int id = EM_LIST(no)->id;
        if (id >= lo && id <= hi && aliveCapWaitingK(k)) {
            cnt++;
        }
    }
    return cnt;
}

// SceDestroyEm(lo, hi): held entries of the range go too, their list entry cleared as a destroy clears it.
extern "C" void re4dc_aliveCapDestroy(int lo, int hi)
{
    int k, n = 0;

    if (hi == -1) {
        hi = lo;
    }
    for (k = 0; k < aliveCapN; k++) {
        const int no = aliveCapHeld[k];
        EmListData* d = EM_LIST(no);
        if (d->id >= lo && d->id <= hi && aliveCapWaitingK(k)) {
            d->be_flag &= ~1;
#if RE4DC_ALIVE_CAP_LOG
            OSReport("alivecap: destroy held 0x%02x room %03x\n", no, (unsigned) d->room);
#endif
            continue;
        }
        aliveCapSent[n] = aliveCapSent[k];
#if defined(RE4DC_ALIVE_CAP_DEFER_FLAGS) && RE4DC_ALIVE_CAP_DEFER_FLAGS
        aliveCapPendingFlags[n] = aliveCapPendingFlags[k];
#if defined(RE4DC_ALIVE_CAP_DEFER_GOTO_R207) && RE4DC_ALIVE_CAP_DEFER_GOTO_R207
        aliveCapPendingGoto[n] = aliveCapPendingGoto[k];
#endif
#endif
        aliveCapHeld[n++] = (u8) no;
    }
    aliveCapN = n;
}

// PS2 EmFarDelete / EmFarDeleteNoWrap (include/em_far_delete.h) with held entries (coordinator decision 10-15,
// st3 lane r301): the PS2 far delete leaves `keep` Ganados and the ones it removes are gone, so held entries count
// as Ganados there too. Drops up to `max` waiting Ganado entries of this room (latest held first); with clearAlive
// (NoWrap) their list alive bit is cleared as the delete clears a live one's, else (wrap) the entry is left alive and
// not set, as a wrap delete leaves it. Returns the number dropped.
extern "C" int re4dc_aliveCapFarDrop(int max, int clearAlive)
{
    int k, dropped = 0;

    for (k = aliveCapN - 1; k >= 0 && dropped < max; k--) {
        const int no = aliveCapHeld[k];
        EmListData* d = EM_LIST(no);
        int j;

        if (!aliveCapGanado(d->id) || !aliveCapWaitingK(k)) {
            continue;
        }
        if (clearAlive) {
            d->be_flag &= ~1;
        }
#if RE4DC_ALIVE_CAP_LOG
        OSReport("alivecap: far delete drops held 0x%02x room %03x%s\n", no, (unsigned) pG->room_id,
                 clearAlive ? "" : " (wrap: entry kept)");
#endif
        for (j = k + 1; j < aliveCapN; j++) {
            aliveCapHeld[j - 1] = aliveCapHeld[j];
            aliveCapSent[j - 1] = aliveCapSent[j];
#if defined(RE4DC_ALIVE_CAP_DEFER_FLAGS) && RE4DC_ALIVE_CAP_DEFER_FLAGS
            aliveCapPendingFlags[j - 1] = aliveCapPendingFlags[j];
#if defined(RE4DC_ALIVE_CAP_DEFER_GOTO_R207) && RE4DC_ALIVE_CAP_DEFER_GOTO_R207
            aliveCapPendingGoto[j - 1] = aliveCapPendingGoto[j];
#endif
#endif
        }
        aliveCapN--;
        dropped++;
    }
    return dropped;
}

#if RE4DC_ALIVE_CAP_PARK
// ALIVE_CAP_PARK=1 (PS2_CH1_ENEMY): when more than N are alive anyway (sends kept for their callers, event
// Ganados), the farthest off-screen one is parked as the PS2 EmFarDelete picks (3D d2 > 3000, sphere y+1000 r1000
// outside the view, not types 2/5/6/0xA/0xD/0x16, not flag 0x10000000) - but re-queued instead of deleted: its list
// entry goes back to "alive, not set" and into the hold, so it counts as alive (SceCountEmAlive), is released again
// below the cap and no kill / death link is recorded. Only an unhurt Ganado in its plain AI routine, created from a
// list entry of this room, not a kept entry, and not in a room whose code holds enemy pointers of its sends (r101 has
// its own cap; r100 the ambush pointer list W->ems[0..6]; r104 / r10a / r10c / r10f / r11c / r11d wrappers or batches).
static int aliveCapParkRoom()
{
    switch (pG->stage_no << 8 | pG->room_no) {
    case 0x100:   // r100_em_set keeps W->ems[0..6] (lists 3-5, 0x12, 0x13, 0x26, 0x27) and reads them later: a park
                  // there freed live pointers (heap 4 corruption from the s20 ambush, test 13 RC H2 gate)
    case 0x101: case 0x104: case 0x10A: case 0x10C: case 0x10F: case 0x11C: case 0x11D:
        return 0;
#if defined(RE4DC_PS2_CH3_ENEMY) && RE4DC_PS2_CH3_ENEMY
    // PS2_CH3_ENEMY: the castle chapter 3 rooms keep cEmWrap pointers of their sends (r201..r20f; r20a and
    // r20d send nothing that matters, kept out too): hold only, no parking.
    case 0x200: case 0x201: case 0x202: case 0x203: case 0x204: case 0x205: case 0x206: case 0x207:
    case 0x208: case 0x209: case 0x20A: case 0x20B: case 0x20C: case 0x20D: case 0x20E: case 0x20F:
        return 0;
#endif
#if defined(RE4DC_ROUTE_CH3) && RE4DC_ROUTE_CH3
    // Island rooms whose code keeps cEmWrap / enemy pointers of its sends (stage 3 lane census 2026-10-15): the cap
    // holds their sends at send time, nothing is parked. r303 r30e r316 r31d r321 (no wrappers) park as usual.
    case 0x300: case 0x301: case 0x304: case 0x305: case 0x306: case 0x307: case 0x308: case 0x309:
    case 0x30B: case 0x30C: case 0x30D: case 0x30F: case 0x310: case 0x311: case 0x31B: case 0x31C:
    case 0x320: case 0x327: case 0x332: case 0x333:
        return 0;
#endif
#if defined(RE4DC_PS2_CH4_ENEMY) && RE4DC_PS2_CH4_ENEMY
    // PS2_CH4_ENEMY: the castle chapter 4 rooms (r210..r22b, r201 / r206 revisits are chapter 3 cases above) keep
    // cEmWrap pointers of their sends (r216 armors, r223 em[], r226 em[], r227 elevator / far-side wraps): hold only.
    case 0x210: case 0x211: case 0x212: case 0x213: case 0x214: case 0x215: case 0x216: case 0x217:
    case 0x218: case 0x219: case 0x21A: case 0x21B: case 0x21C: case 0x21D: case 0x21E: case 0x21F:
    case 0x220: case 0x221: case 0x222: case 0x223: case 0x224: case 0x225: case 0x226: case 0x227:
    case 0x228: case 0x229: case 0x22A: case 0x22B: case 0x22C:
        return 0;
#endif
    }
    return 1;
}

static void aliveCapPark(int live)
{
    static u32 last;
    cEm* best = 0;
    f32 bestD = 0.0f;
    u32 i;

    if (live <= RE4DC_ALIVE_CAP_N || !aliveCapRoom() || !aliveCapParkRoom() || (u32) (pG->Frame_cnt - last) < 30) {
        return;
    }
    for (i = 0; i < EmMgr.nArray; i++) {
        cEm* em = emSetWork(i);
        f32 dx, dy, dz, d2;

        if (!em || !aliveCapGanado(em->id) || !em->isAlive() || em->checkStatus(EM_STATUS_ACTIVE) == 0) {
            continue;
        }
        switch (em->type) {
        case 0x16: case 2: case 5: case 6: case 0xA: case 0xD:
            continue;
        }
        if ((em->flag & 0x10000000) || em->r_no_0 != 1 || em->hp != em->hp_max || (em->dmg.m_Flag & 1)) {
            continue;
        }
        const int no = em->emset_no;
        if (no == 0xFF || aliveCapKeep(no)) {
            continue;
        }
        EmListData* d = EM_LIST(no);
        if (d->id != em->id || pG->stage_no != d->room >> 8 || pG->room_no != (d->room & 0xFF)) {
            continue;
        }
        {
            GeoSphere sph;

            sph.pos = em->pos;
            sph.pos.y += 1000.0f;
            sph.r = 1000.0f;
            if (collision_sphere_hexahedron(&sph, (GeoHexahedron*) CameraViewFrustumPtr(&pG->Cam))) {
                continue;   // in view
            }
        }
        dx = em->pos.x - pPL->pos.x;
        dy = em->pos.y - pPL->pos.y;
        dz = em->pos.z - pPL->pos.z;
        d2 = dx * dx + dy * dy + dz * dz;
        if (!(d2 > 3000.0f) || !(d2 > bestD)) {
            continue;
        }
        bestD = d2;
        best = em;
    }
    if (best == 0) {
        return;
    }
    const int no = best->emset_no;
    EmListData* d = EM_LIST(no);

    last = pG->Frame_cnt;
    d->be_flag = (u8) ((d->be_flag | 1) & ~2);   // alive in the list, not set: EmSetFromList2 can create it again
    aliveCapPush(no, 0);
    EmMgr.destroy(best);
    aliveCapLast = pG->Frame_cnt;                 // the next release waits its 30 frames
#if RE4DC_ALIVE_CAP_LOG
    OSReport("alivecap: park 0x%02x room %03x frame %u live %d held %d\n", no, (unsigned) pG->room_id,
             (unsigned) pG->Frame_cnt, live - 1, aliveCapN);
#endif
}
#endif

// Once per frame (ScenarioMove, busy = event / item / pause): one held Ganado in below the cap.
extern "C" void re4dc_aliveCapMove(int busy)
{
    int k, n = 0, best = -1;
    f32 bestD = -1.0f;

#if RE4DC_ALIVE_CAP_LOG
    {   // diagnostic: each new per-room peak of live Ganados
        static u16 pkRoom;
        static int pk;
        const int live = aliveCapLive();

        if (pG->room_id != pkRoom) {
            pkRoom = pG->room_id;
            pk = 0;
        }
        if (live > pk) {
            pk = live;
            OSReport("alivecap: peak %d room %03x frame %u held %d\n", live, (unsigned) pG->room_id,
                     (unsigned) pG->Frame_cnt, re4dc_aliveCapHeldCount(0x10, 0x20)
#if defined(RE4DC_ALIVE_CAP_NOVIS) && RE4DC_ALIVE_CAP_NOVIS
                     + (pG->stage_no == 2 ? re4dc_aliveCapHeldCount(0x2D, -1) : 0)
#endif
                     );
        }
    }
#endif
#if RE4DC_ALIVE_CAP_PARK
    if (!busy && pPL != 0) {
        aliveCapPark(aliveCapLive());
    }
#endif
    if (aliveCapN == 0 || busy || pPL == 0) {
        return;
    }
    if ((u32) (pG->Frame_cnt - aliveCapLast) < 30 || aliveCapLive() >= RE4DC_ALIVE_CAP_N) {
        return;
    }
    for (k = 0; k < aliveCapN; k++) {
        const int no = aliveCapHeld[k];
        if (!aliveCapWaitingK(k)) {
            continue;   // set or killed by room code meanwhile, or another room: out of the hold
        }
        EmListData* d = EM_LIST(no);
        const f32 dx = (f32) d->pos[0] * 10.0f - pPL->pos.x;
        const f32 dz = (f32) d->pos[2] * 10.0f - pPL->pos.z;
        const f32 dist = dx * dx + dz * dz;
        aliveCapSent[n] = aliveCapSent[k];
#if defined(RE4DC_ALIVE_CAP_DEFER_FLAGS) && RE4DC_ALIVE_CAP_DEFER_FLAGS
        aliveCapPendingFlags[n] = aliveCapPendingFlags[k];
#if defined(RE4DC_ALIVE_CAP_DEFER_GOTO_R207) && RE4DC_ALIVE_CAP_DEFER_GOTO_R207
        aliveCapPendingGoto[n] = aliveCapPendingGoto[k];
#endif
#endif
        aliveCapHeld[n++] = (u8) no;
        if (dist > bestD) {
            bestD = dist;
            best = n - 1;
        }
    }
    aliveCapN = n;
    if (best < 0) {
        return;
    }
    const int no = aliveCapHeld[best];
    const int sent = aliveCapSent[best];
#if defined(RE4DC_ALIVE_CAP_DEFER_FLAGS) && RE4DC_ALIVE_CAP_DEFER_FLAGS
    const u32 pending = aliveCapPendingFlags[best];
#if defined(RE4DC_ALIVE_CAP_DEFER_GOTO_R207) && RE4DC_ALIVE_CAP_DEFER_GOTO_R207
    const AliveCapPendingGoto pendingGoto = aliveCapPendingGoto[best];
#endif
#endif
    for (k = best + 1; k < aliveCapN; k++) {
        aliveCapHeld[k - 1] = aliveCapHeld[k];
        aliveCapSent[k - 1] = aliveCapSent[k];
#if defined(RE4DC_ALIVE_CAP_DEFER_FLAGS) && RE4DC_ALIVE_CAP_DEFER_FLAGS
        aliveCapPendingFlags[k - 1] = aliveCapPendingFlags[k];
#if defined(RE4DC_ALIVE_CAP_DEFER_GOTO_R207) && RE4DC_ALIVE_CAP_DEFER_GOTO_R207
        aliveCapPendingGoto[k - 1] = aliveCapPendingGoto[k];
#endif
#endif
    }
    aliveCapN--;
    aliveCapLast = pG->Frame_cnt;
    aliveCapReleasing = 1;
    cEm* em = EmSetFromList2(no, 1);
    aliveCapReleasing = 0;
#if defined(RE4DC_ALIVE_CAP_DEFER_FLAGS) && RE4DC_ALIVE_CAP_DEFER_FLAGS
    if (em && em != errEm) {
#if defined(RE4DC_ALIVE_CAP_DEFER_GOTO_R207) && RE4DC_ALIVE_CAP_DEFER_GOTO_R207
        aliveCapDeliverGotoR207(em, no, pending, pendingGoto);
#else
        em->flag |= pending;
#endif
    } else {
        em = 0;
        aliveCapRestorePending(best, no, sent, pending
#if defined(RE4DC_ALIVE_CAP_DEFER_GOTO_R207) && RE4DC_ALIVE_CAP_DEFER_GOTO_R207
                                   , pendingGoto
#endif
                                   );
    }
#endif
    if (em && sent) {
        EmListSetAlive(no, 1);   // as the deferred setEm(..., setAlive 1) would have
    }
#if RE4DC_ALIVE_CAP_LOG
    OSReport("alivecap: release 0x%02x room %03x frame %u live %d held %d %s%s\n", no, (unsigned) pG->room_id,
             (unsigned) pG->Frame_cnt, aliveCapLive(), aliveCapN, em ? "ok" : "refused", sent ? " (send)" : "");
#else
    (void) em;
#endif
}

// EM_WRAP_HELD_NOW (include/em_wrap.h): re4dc_aliveCapHeldEntry, and with ALIVE_CAP_LOG the first skips per site
// are logged ("alivecap: site") so a run shows that each room probe met a held send.
extern "C" int re4dc_aliveCapHeldSite(int no, const char* file, int line)
{
    const int held = re4dc_aliveCapHeldEntry(no);
#if RE4DC_ALIVE_CAP_LOG
    static int lines[24], counts[24];
    if (held) {
        int k;
        for (k = 0; k < 24 && lines[k] && lines[k] != line; k++) {
        }
        if (k < 24) {
            lines[k] = line;
            if (counts[k]++ < 3) {
                const char* b = file;
                for (const char* p = file; *p; p++) {
                    if (*p == '/') b = p + 1;
                }
                OSReport("alivecap: site %s:%d skips held 0x%02x room %03x frame %u\n", b, line, no,
                         (unsigned) pG->room_id, (unsigned) pG->Frame_cnt);
            }
        }
    }
#else
    (void) file;
    (void) line;
#endif
    return held;
}

// 1 while the cap is full in a capped room (N Ganados alive): room code that creates Ganados without the list send
// (EmSetEvent: r208 feeding over the wall) waits instead of going over the cap.
extern "C" int re4dc_aliveCapFull()
{
    return !aliveCapReleasing && aliveCapRoom() && aliveCapLive() >= RE4DC_ALIVE_CAP_N;
}

// EmSetFromList2: 1 = a room-code send of a Ganado while N are alive, now held (errEm to the caller).
extern "C" int re4dc_aliveCapDefer(int no, int id)
{
    int k;

    if (aliveCapReleasing || !aliveCapEnemy(id) || !aliveCapRoom() || aliveCapKeep(no)) {
        return 0;
    }
    if (aliveCapLive() < RE4DC_ALIVE_CAP_N) {
        return 0;
    }
    for (k = 0; k < aliveCapN; k++) {
        if (aliveCapHeld[k] == no) {
            return 1;   // already held: still waiting
        }
    }
    if (aliveCapN >= (int) sizeof(aliveCapHeld)) {
        return 0;
    }
    aliveCapPush(no, 1);
#if RE4DC_ALIVE_CAP_LOG
    OSReport("alivecap: defer send 0x%02x room %03x (live %d held %d)\n", no, (unsigned) pG->room_id, aliveCapLive(),
             aliveCapN);
#endif
    return 1;
}
#endif

// Room start: creates every list entry that is alive (be_flag bit0), not yet set (bit1), not
// recorded dead, belongs to the current stage / room, has an id and is not blocked by the debug
// filter; copies the entry into the work, marks it set (bit1, toggling bits 2/3), computes the
// player distance and runs the first move.
void EmSetFromList()
{
    u32 i;
#if defined(RE4DC_ALIVE_CAP) && RE4DC_ALIVE_CAP
    int capLive = -1;
    int k, n = 0;

    for (k = 0; k < aliveCapN; k++) {   // keep this room's waiting entries (sends deferred by its init function)
        if (aliveCapWaitingK(k)) {
            aliveCapSent[n] = aliveCapSent[k];
#if defined(RE4DC_ALIVE_CAP_DEFER_FLAGS) && RE4DC_ALIVE_CAP_DEFER_FLAGS
            aliveCapPendingFlags[n] = aliveCapPendingFlags[k];
#if defined(RE4DC_ALIVE_CAP_DEFER_GOTO_R207) && RE4DC_ALIVE_CAP_DEFER_GOTO_R207
            aliveCapPendingGoto[n] = aliveCapPendingGoto[k];
#endif
#endif
            aliveCapHeld[n++] = aliveCapHeld[k];
        }
    }
    aliveCapN = n;
    if (aliveCapRoom()) {
        capLive = aliveCapLive();   // Ganados the room's init function already set
    }
#endif

#if defined(RE4DC_ALIVE_CAP_R202_GATE) && RE4DC_ALIVE_CAP_R202_GATE
    // Keep the original list filters and creation body. The permutation puts the
    // gate's operator in the fourth-slot budget before an unrelated catapult.
    for (u32 order = 0; order < 256; order++) {
        i = re4dc_r202_gate::entry((unsigned) pG->room_id, order);
#else
    for (i = 0; i < 256; i++) {
#endif
        EmListData* d = EM_LIST(i);
        cEm* em;

        if (!(d->be_flag & 1)) {
            continue;
        }
        if (d->be_flag & 2) {
            continue;
        }
        if (EmSetDieCk(i)) {
            continue;
        }
        if (pG->stage_no != d->room >> 8) {
            continue;
        }
        if (pG->room_no != (d->room & 0xFF)) {
            continue;
        }
#if defined(RE4DC_ANIMALS_OFF) && RE4DC_ANIMALS_OFF
        // ANIMALS_OFF (Makefile): the stage 1 ambient animals are not spawned (cows 0x26, chickens 0x28, the set-0 dog
        // 0x21); the bear-trap dog (set 1) and the El Gigante dog (set 2) are scripted and stay.
        if (pG->stage_no == 1 && (d->id == 0x26 || d->id == 0x28 || (d->id == 0x21 && d->set == 0))) {
            d->be_flag &= ~1;
            OSReport("animals off: r%03x entry 0x%02x id 0x%02x not spawned\n", (unsigned) d->room, (unsigned) i, (unsigned) d->id);
            continue;
        }
#endif
        if (checkListId(i) == 0) {
            continue;
        }
        // d->id read directly: the range fold of EM_SET_ID_NG keeps the QImode load and the int
        // uses share one PRE'd `clrlwi`; a `u8 id` local is promoted and never masked.
        if (d->id == 0) {
            continue;
        }
        if (EM_SET_ID_NG(d->id)) {
            continue;
        }
#if defined(RE4DC_ALIVE_CAP) && RE4DC_ALIVE_CAP
        if (capLive >= 0 && aliveCapEnemy(d->id)) {
            if (capLive >= RE4DC_ALIVE_CAP_N && aliveCapN < (int) sizeof(aliveCapHeld)) {
                aliveCapPush((int) i, 0);
#if RE4DC_ALIVE_CAP_LOG
                OSReport("alivecap: hold 0x%02x room %03x (live %d cap %d)\n", (int) i, (unsigned) pG->room_id,
                         capLive, RE4DC_ALIVE_CAP_N);
#endif
                continue;
            }
            capLive++;
        }
#endif
        em = EmCreate(d->id);
        if (em == 0) {
            pLog->err(0, 0, "EmSetFromList() Em set failed, Id = %x", d->id);
            continue;
        }
        EmSetWork(em, d, i);
        d->be_flag |= 2;
        if (d->be_flag & 4) {
            d->be_flag |= 8;
            d->be_flag &= ~4;
        } else if (!(d->be_flag & 8)) {
            d->be_flag |= 4;
        }
        EmSetDist(em);
        em->l_sub = 1.0e16f;
        em->move();
#if defined(RE4DC_ALIVE_CAP) && RE4DC_ALIVE_CAP
        aliveCapNoteFresh(em, (int) i);
#if defined(RE4DC_ALIVE_CAP_DEFER_FLAGS) && RE4DC_ALIVE_CAP_DEFER_FLAGS
        aliveCapApplyPending(em, (int) i);
#endif
#endif
    }
}

#if defined(RE4DC_EM_READ_RETRY) && RE4DC_EM_READ_RETRY
// EM_MUST (issue #52, coordinator 10-22): a progress-critical spawn (boss, the r11b boat) is never skipped. While
// re4dc_emSetMust is set, a failed EmCreate (its module read failed even after readEmData's retries) sleeps with a
// growing backoff capped at 60 frames (2 s) and tries again, with no limit: a slow load, never a soft-lock.
extern "C" void re4dc_em_sleep(int frames);   // read.cpp
extern "C" void OSReport(const char* fmt, ...);
extern "C" int re4dc_emSetMust;
int re4dc_emSetMust;
extern "C" void* re4dc_em_must_end(void* em)
{
    re4dc_emSetMust = 0;
    return em;
}
static cEm* emMustCreate(cEm* em, u8 id)
{
    int t;

    for (t = 1; em == 0 && re4dc_emSetMust; t++) {
        int f = 4 * t;

        if (f > 60) {
            f = 60;
        }
        OSReport("emset: required enemy id %x not created, retry %d in %d frames\n", (unsigned) id, t, f);
        re4dc_em_sleep(f);
        em = EmCreate(id);
    }
    return em;
}
#endif

// Creates list entry `no` on demand (room event scripts): same checks as EmSetFromList, the
// death bit only with chkDead. Returns the enemy, or errEm when nothing was created.
cEm* EmSetFromList2(int no, int chkDead)
{
    EmListData* d = EM_LIST(no);
    cEm* em;
#if defined(RE4DC_GAME) && !defined(__PPC__) && defined(RE4DC_ISSUE52_ACTOR_DIAG) && RE4DC_ISSUE52_ACTOR_DIAG
    unsigned issue52_token = 0;
    if (no == 2 && pG->room_id == 0x10c)
        issue52_token = re4dc_issue52_begin(re4dc_issue52_source_task(),
            pG->Frame_cnt, pG->room_id, no, d->id);
#define I52_ADMISSION_RETURN(why, value) do { \
    if (issue52_token) re4dc_issue52_finish(issue52_token, re4dc_issue52_source_task(), \
        why, (unsigned long) (value), pG->Frame_cnt); \
    return value; \
} while (0)
#else
#define I52_ADMISSION_RETURN(why, value) return value
#endif

    if (EM_SET_ID_NG(d->id)) {
        I52_ADMISSION_RETURN(I52_ID_FILTER, errEm);
    }
    if (pG->stage_no != d->room >> 8) {
        I52_ADMISSION_RETURN(I52_STAGE, errEm);
    }
    if (pG->room_no != (d->room & 0xFF)) {
        I52_ADMISSION_RETURN(I52_ROOM, errEm);
    }
    if (d->be_flag & 2) {
        I52_ADMISSION_RETURN(I52_ALREADY_SET, errEm);
    }
    if (d->id == 0) {
        I52_ADMISSION_RETURN(I52_ZERO_ID, errEm);
    }
    if (chkDead) {
        if (EmSetDieCk(no)) {
            I52_ADMISSION_RETURN(I52_DEAD, errEm);
        }
    }
    if (checkListId(no) == 0) {
        I52_ADMISSION_RETURN(I52_LIST_FILTER, errEm);
    }
#if defined(RE4DC_ALIVE_CAP) && RE4DC_ALIVE_CAP
    if (re4dc_aliveCapDefer(no, d->id)) {
        I52_ADMISSION_RETURN(I52_CAP, errEm);
    }
#endif
    em = EmCreate(d->id);
#if defined(RE4DC_EM_READ_RETRY) && RE4DC_EM_READ_RETRY
    em = emMustCreate(em, d->id);
#endif
    if (em == 0) {
        pLog->err(0, 0, "EmSetFromList2() Em set failed, Id = %x", d->id);
        I52_ADMISSION_RETURN(I52_CREATE_FAILED, errEm);
    }
    EM_SET_WORK(em, d, no);
    d->be_flag |= 2;
    if (d->be_flag & 4) {
        d->be_flag |= 8;
        d->be_flag &= ~4;
    } else if (!(d->be_flag & 8)) {
        d->be_flag |= 4;
    }
    EmSetDist(em);
    em->l_sub = 1.0e16f;
    em->move();
#if defined(RE4DC_ALIVE_CAP) && RE4DC_ALIVE_CAP
    aliveCapNoteFresh(em, no);
#if defined(RE4DC_ALIVE_CAP_NOVIS) && RE4DC_ALIVE_CAP_NOVIS
    aliveCapRestoreNovisRoom(em, no);
#endif
#if defined(RE4DC_ALIVE_CAP_DEFER_FLAGS) && RE4DC_ALIVE_CAP_DEFER_FLAGS
    aliveCapApplyPending(em, no);
#endif
#endif
    I52_ADMISSION_RETURN(I52_CREATED, em);
#undef I52_ADMISSION_RETURN
}

// Event enemy from a list entry outside the room list (never called in the DOL).
cEm* EmSetEvent(EmListData* d)
{
    cEm* em;

    if (EM_SET_ID_NG(d->id)) {
        return errEm;
    }
    em = EmCreate(d->id);
#if defined(RE4DC_EM_READ_RETRY) && RE4DC_EM_READ_RETRY
    em = emMustCreate(em, d->id);
#endif
    if (em == 0) {
        pLog->err(0, 0, "EmSetEvent() Em set failed, Id = %x", d->id);
        return errEm;
    }
    EM_SET_WORK(em, d, 0xFF);
    d->be_flag = 7;
#if defined(RE4DC_ALIVE_CAP_LOG) && RE4DC_ALIVE_CAP_LOG
    OSReport("alivecap: event set id 0x%02x room %03x frame %u%c", (unsigned) d->id, (unsigned) pG->room_id,
             (unsigned) pG->Frame_cnt, 10);
#endif
    EmSetDist(em);
    em->l_sub = 1.0e16f;
    em->move();
    return em;
}

#if defined(RE4DC_OB_SCAN) && RE4DC_OB_SCAN && defined(RE4DC_WORKAT_INLINE) && RE4DC_WORKAT_INLINE
#define OB_EM 1
// GAME_OB_SCAN: an enemy passes the live test only while it is on EmMgr's alive list (create links
// it after construct; destroy unlinks it before marking 0x200), so the list is searched instead of
// every slot. With one match that is the answer (the source returns its first match in slot order);
// with none, none; with two or more, or a frozen / pushed pool, the caller runs the source loop.
#if RE4DC_OB_SCAN == 2
extern "C" unsigned long re4dc_ob_chk[12];   // dmg.cpp
#endif
static inline int obEmFind(int no, cEm** res)
{
    cEm* hit = 0;
    cEm* p;

    if (re4dc_frozen_pools || EmMgr.pArrayPush != 0 || EmMgr.pArray == 0) {
        return 0;
    }
    for (p = EmMgr.pAlive; p != 0; p = (cEm*) p->pNext) {
        if ((p->be_flag & 0x201) == 1 && p->emset_no == (u8) no) {
            if (hit != 0) {
                return 0;
            }
            hit = p;
        }
    }
    *res = hit;
    return 1;
}
#endif
// The live enemy created from list entry `no`; NULL when none (or no == 0xFF).
cEm* GetEmPtrFromList(int no)
{
    u32 i;

    if (no == 0xFF) {
        return 0;
    }
#if defined(OB_EM)
    {
        cEm* r = 0;
        int ok = obEmFind(no, &r);
#if RE4DC_OB_SCAN == 2
        cEm* src = 0;
        re4dc_ob_chk[5]++;
        for (i = 0; i < EmMgr.nArray; i++) {
            cEm* em = emSetWork(i);
            if (!em) continue;
            if ((em->be_flag & 0x201) == 1 && em->emset_no == (u8) no) {
                src = em;
                break;
            }
        }
        if (!ok) {
            re4dc_ob_chk[7]++;
        } else if (r != src) {
            re4dc_ob_chk[6]++;
        }
        return src;
#else
        if (ok) {
            return r;
        }
#endif
    }
#endif
    for (i = 0; i < EmMgr.nArray; i++) {
        cEm* em = emSetWork(i);
#if !defined(__PPC__)
        if (!em) continue;
#endif

        if ((em->be_flag & 0x201) == 1 && em->emset_no == (u8) no) {
            return em;
        }
    }
    return 0;
}

// The list entry an enemy was created from; NULL for enemies not from the list (emset_no 0xFF).
EmListData* GetListPtrFromEm(cEm* em)
{
    if (em->emset_no == 0xFF) {
        return 0;
    }
    return EM_LIST(em->emset_no);
}

// Enemy id of list entry `no` (0xFF for an invalid index).
u8 GetEmIdFromList(u32 no)
{
    EmListData* list;

    if (no >= 0xFF) {
        return 0xFF;
    }
    list = (EmListData*) pG->Em_list;
    return list[no].id;
}

// Sets / clears the alive bit (be_flag bit0) of list entry `no`, only for entries of the current
// stage / room.
void EmListSetAlive(int no, int on)
{
    EmListData* d = EM_LIST(no);

    if (pG->stage_no != d->room >> 8) {
        return;
    }
    if (pG->room_no != (d->room & 0xFF)) {
        return;
    }
    if (on == 1) {
        d->be_flag |= 1;
    } else {
        d->be_flag &= ~1;
    }
}

// Records the death of a list enemy in the current death bit table (so it is not re-created),
// except in stage 4 rooms and under the debug flags that keep enemies respawning.
void EmSetDie(cEm* em)
{
    if (pG->Debug_flg[2] & 0x04000000) {
        return;
    }
    if ((pG->room_id32 & 0xFFFF0000) == 0x00040000) {
        return;
    }
    if (pG->Debug_flg[3] & 0x00080000) {
        return;
    }
    if (EmSetDieCk(em->emset_no)) {
        return;
    }
    EmSetDieOn(em->emset_no);
}

// Counts a kill in the chapter and game kill counters (results screen).
void EmSetDieCnt()
{
    CntInc(pG->c_kill_cnt);
    CntInc(pG->g_kill_cnt);
}

// Room change: clears the "set" bit of every list entry so the new room can create its enemies.
void EmSetRoomInit()
{
    int i;

#if defined(RE4DC_ALIVE_CAP_DEFER_FLAGS) && RE4DC_ALIVE_CAP_DEFER_FLAGS
    // This reset precedes the new room's init scripts, including same-room
    // Continue and a replaced ESL list. Old commands must not follow reused IDs.
    for (i = 0; i < 64; i++) {
        aliveCapPendingFlags[i] = 0;
#if defined(RE4DC_ALIVE_CAP_DEFER_GOTO_R207) && RE4DC_ALIVE_CAP_DEFER_GOTO_R207
        aliveCapPendingGoto[i] = {};
#endif
    }
#endif

    for (i = 0; i < 256; i++) {
        EmListData* d = EM_LIST(i);

        d->be_flag &= ~2;
    }
}

// Every 30 frames: intended to delete waiting list enemies; the loop body is empty in the
// shipped game.
void EmListWaitDelete()
{
    int i;

    if (pG->Frame_cnt % 30 != 0) {
        return;
    }
    for (i = 0; i < 256; i++) {
    }
}
