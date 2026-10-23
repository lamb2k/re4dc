// game/em.cpp: the character work base (cEm) and its manager (cEmMgr): construction of the
// player / enemy / object classes by id, the per-frame emMove loop, the damage info (cDmgInfo).

#include "atari.h"
#include "ctrl.h"
#include "em.h"
#include "player.h"
#include "emobj.h"
#include "emdoor.h"
#include "emwep.h"
#include "embox.h"
#include "emwindow.h"
#include "emtorch.h"
#include "embarrel.h"
#include "emtree.h"
#include "emrock.h"
#include "emswitch.h"
#include "emitem.h"
#include "emhit.h"
#include "emBarred.h"
#include "emmine.h"
#include "emshield.h"
#include "emBar.h"
#include "snd.h"
#include "global.h"
#include "db_log.h"
#include "va_ppc.h"
#if defined(RE4DC_GAME) && !defined(__PPC__) && defined(RE4DC_ISSUE52_ACTOR_DIAG) && RE4DC_ISSUE52_ACTOR_DIAG
#include "issue52_actor_diag.h"
#endif
#if defined(RE4DC_EL_CENSUS) && RE4DC_EL_CENSUS
#include "el_census.h"   // EL_CENSUS (game30.mk; lane el): the running enemy and its skeleton census
#endif

extern "C" {
void RouteCk();                                     // route_ck.cpp
void* EmReadSearch(u8 id, int a, int b);            // read.cpp: the enemy's read table entry, 0 when not loaded
void ShapeMove(cModelInfo* info);                   // shape.cpp
void EmYarareDisp(cEm* em);                         // em_sub.cpp
void DrawOba(cModel* m);                            // at_mod.cpp
}

// cManager<T>::arrayFree / arrayAlloc: definitions in cManager.h (game.cpp instantiates them too).

const char* cEmMgr::idName[96] = {
    "PLAYER", "", "", "ASHLEY", "LUIS", "", "", "", "", "", "", "", "", "", "JET SKI", "MOTOR BOAT",
    "GANADO", "GANADO", "GANADO", "GANADO", "GANADO", "GANADO", "GANADO", "GANADO",
    "GANADO", "GANADO", "GANADO", "GANADO", "GANADO", "GANADO", "GANADO", "GANADO",
    "SPIDER", "DOG", "DOG", "CROW", "SNAKE S", "PARASITE", "COW", "BLACKBASS",
    "CHICKEN", "BAT", "TRAP", "ELGIGANTE", "INSECT BOSS", "INSECT HUMAN", "SPIDER S", "SALAMANDER",
    "SADDLER", "", "U3", "INSECTBOSS EVENT", "MAYOR", "MAYOR AFTER", "REGENERATER", "NO2",
    "NO2 AFTER", "NO3", "NO3 AFTER", "TRUCK", "ARMOR", "HELICOPTER", "", "",
    "OBJ", "DOOR", "WEP", "BOX", "WALL", "RACK", "WINDOW", "TORCH",
    "BARREL", "TREE", "ROCK", "SWITCH", "ITEM", "HIT", "BARRED", "MINE",
    "SHIELD",
};

cPlayer* pPL;
cEm* pSUB;
void (*EmInitFunc)(cEm* em);
void (*PlInitFunc)(cEm* em);

static u32 battleCheckFlag;

// The character manager: a cManager<cEm> pool of 0xDE0 byte works (type 2), one serial (Guid)
// counter for the works it hands out.
cEmMgr::cEmMgr() : cManager<cEm>(sizeof(cEm), 2)
{
    setName("cEmMgr");
    Guid = 0;
}

// cManager log hook: routes the manager's messages to pLog as level-6 warnings.
void cEmMgr::log(const char* fmt, ...)
{
    va_list ap;

    va_start(ap, fmt);
    pLog->vwarn(6, 0, fmt, ap);
}

// Places the class for character `id` into the fresh work: id 0 the player (cPlLeon / cPlAshley
// by pG->pl_type, other player types through PlInitFunc), 1..0xE and every enemy id through the
// loaded enemy module (EmReadSearch + EmInitFunc; 0 when the module is not loaded), 0x40..0x51
// the object classes (door, weapon, box, rack, window, torch, barrel, tree, rock, switch, item,
// hit, barred, mine, shield, bar), 0xFF a bare cEm. Then assigns the serial, be_flag 0x40 |
// 0x02000000, emset_no 0xFF and stores the read table entry.
int cEmMgr::construct(cEm* p, u32 id)
{
#if defined(RE4DC_GAME) && !defined(__PPC__) && defined(RE4DC_ISSUE52_ACTOR_DIAG) && RE4DC_ISSUE52_ACTOR_DIAG
    const unsigned issue52_token = id == 0x12 ?
        re4dc_issue52_current(re4dc_issue52_source_task(), id) : 0;
    if (issue52_token) re4dc_issue52_detail(issue52_token,
        re4dc_issue52_source_task(), I52_CONSTRUCT_BEGIN, 0, 0);
#endif
    switch (id) {
    case 0:
        switch (pG->pl_type) {
        case 0:
            p = new (p) cPlLeon;
            break;
        case 1:
            p = new (p) cPlAshley;
            break;
        case 2:
        case 3:
        case 4:
        case 5:
            PlInitFunc(p);
            break;
        }
        break;
    case 1:
    case 2:
    case 3:
    case 4:
    case 5:
    case 6:
    case 7:
    case 8:
    case 9:
    case 0xA:
    case 0xB:
    case 0xC:
    case 0xD:
    case 0xE:
        p->subArc = (PlArc*)EmReadSearch(id, 0, 0);
        if (p->subArc == 0) {
            return 0;
        }
        EmInitFunc(p);
        break;
    case 0x40:
        p = new (p) cEmObj;
        break;
    case 0x41:
        p = new (p) cEmDoor;
        break;
    case 0x42:
        p = new (p) cEmWep;
        break;
    case 0x43:
        p = new (p) cEmBox;
        break;
    case 0x45:
        p = new (p) cEmRack;
        break;
    case 0x46:
        p = new (p) cEmWindow;
        break;
    case 0x47:
        p = new (p) cEmTorch;
        break;
    case 0x48:
        p = new (p) cEmBarrel;
        break;
    case 0x49:
        p = new (p) cEmTree;
        break;
    case 0x4A:
        p = new (p) cEmRock;
        break;
    case 0x4B:
        p = new (p) cEmSwitch;
        break;
    case 0x4C:
        p = new (p) cEmItem;
        break;
    case 0x4D:
        p = new (p) cEmHit;
        break;
    case 0x4E:
        p = new (p) cEmBarred;
        break;
    case 0x4F:
        p = new (p) cEmMine;
        break;
    case 0x50:
        p = new (p) cEmShield;
        break;
    case 0x51:
        p = new (p) cEmBar;
        break;
    case 0xFF:
        p = new (p) cEm;
        break;
    default:
        p->subArc = (PlArc*)EmReadSearch(id, 0, 0);
        if (p->subArc == 0) {
#if defined(RE4DC_GAME) && !defined(__PPC__) && defined(RE4DC_ISSUE52_ACTOR_DIAG) && RE4DC_ISSUE52_ACTOR_DIAG
            if (issue52_token) re4dc_issue52_detail(issue52_token,
                re4dc_issue52_source_task(), I52_CONSTRUCT_NO_ARC, 0, 0);
#endif
            return 0;
        }
#if defined(RE4DC_GAME) && !defined(__PPC__) && defined(RE4DC_ISSUE52_ACTOR_DIAG) && RE4DC_ISSUE52_ACTOR_DIAG
        // Close read attribution before the initializer can start nested work.
        if (issue52_token) re4dc_issue52_detail(issue52_token,
            re4dc_issue52_source_task(), I52_CONSTRUCT_INIT, 0, 0);
#endif
        EmInitFunc(p);
        break;
    }
    switch (p->id) {
    case 0x10:
    case 0x11:
    case 0x12:
    case 0x13:
    case 0x14:
    case 0x15:
    case 0x16:
    case 0x17:
    case 0x18:
    case 0x19:
    case 0x1A:
    case 0x1B:
    case 0x1C:
    case 0x1D:
    case 0x1E:
    case 0x1F:
    case 0x20:
        p->id = 0x10;
        break;
    }
    p->serial = Guid;
    Guid++;
    p->emset_no = 0xFF;
    p->be_flag |= 0x40;
    p->id = id;
    p->be_flag |= 0x02000000;
    p->subArc2 = p->subArc;
    return 1;
}

// Allocates the pool of `n` character works and clears the player / partner pointers.
int cEmMgr::arrayAlloc(u32 n)
{
    cManager<cEm>::arrayAlloc(n);
    pPL = 0;
    pSUB = 0;
    return 1;
}

#if RE4DC_ACT_CAP || RE4DC_ACT_CAP_TABLE
// D367 B1 activation cap (game30.mk ACT_CAP, port/dreamcast/game/act_cap.cpp).
extern "C" void re4dc_act_cap_select(void);
extern "C" int re4dc_act_cap_parked(cEm* em);

// A parked Ganado's tick instead of emMove: only the player distance, computed as emMove does,
// which the other Ganados' group throttles read (em10DashCk / em10StayCk).
static void emParkMove(cEm* em)
{
    f32 dx;
    f32 dz;

    dz = pPL->pos.z - em->pos.z;
    dx = pPL->pos.x - em->pos.x;
    em->plDist2 = dx * dx + dz * dz;
    em->l_sub = 1e16f;
}
#endif

// Per-frame character update (game loop): dieCheck, the enemy route check, then emMove on every
// live work. Under Stop_flg 0x20000000 (characters frozen) only the partner (pSUB) moves, and
// not when Stop_flg 0x1000 freezes her too.
void cEmMgr::move()
{
    cEm* p;
    void (*func)(cEm*);

    dieCheck();
    RouteCk();
    if (!(pG->Stop_flg & 0x20000000)) {
#if RE4DC_ACT_CAP || RE4DC_ACT_CAP_TABLE
        re4dc_act_cap_select();
#endif
        p = pAlive;
        func = emMove;
        while (p) {
            cEm* cur = p;

            p = (cEm*) p->pNext;
#if RE4DC_ACT_CAP || RE4DC_ACT_CAP_TABLE
            if (re4dc_act_cap_parked(cur)) {
                emParkMove(cur);
                continue;
            }
#endif
            func(cur);
        }
    } else if (pSUB && !(pG->Stop_flg & 0x1000)) {
        emMove(pSUB);
    }
}

// Releases a character work: validates the pointer and its live flags (be_flag 0x201 == 1),
// runs the work's push() cleanup and returns it to the pool.
void cEmMgr::destroy(cEm* p)
{
    if ((u32) p < RE4_MEM_LO || (u32) p > RE4_MEM_HI || (p->be_flag & 0x201) != 1) {
        pLog->err(0, 0, "cEmMgr::destroy() WORK IS ALREADY DEAD. %08X", p);
        return;
    }
    p->push();
    cManager<cEm>::destroy(p);
}

// 1 when any live character has EM_STATUS_ATTACKING set (used for the battle music / save
// prompt rules).
int cEmMgr::isBattle()
{
    cEm* p;
    void (*func)(cEm*);

    // reference store: keeps the pAlive load below it (global.h BitSet)
    BitSet(battleCheckFlag, 0);
    func = battleCheck;
    p = pAlive;
    while (p) {
        cEm* cur = p;

        p = (cEm*) p->pNext;
        func(cur);
    }
    return battleCheckFlag;
}

// isBattle helper: raises battleCheckFlag for a character with EM_STATUS_ATTACKING.
void battleCheck(cEm* em)
{
    if (em->checkStatus(0)) {
        battleCheckFlag = 1;
    }
}

// destroyAll helper: destroys every character except the player (id 0).
void killEm(cEm* em)
{
    if (em->id != 0) {
        EmMgr.destroy(em);
    }
}

// Destroys every live character except the player (room change).
void cEmMgr::destroyAll()
{
    cEm* p;
    void (*func)(cEm*);

    p = pAlive;
    func = killEm;
    while (p) {
        cEm* cur = p;

        p = (cEm*) p->pNext;
        func(cur);
    }
}

// Next live character with `id` after `start` (from the head when start is NULL); NULL when none.
cEm* cEmMgr::getEmPtr(int id, cEm* start)
{
    cEm* p;

    p = start;
    if (p) {
        p = (cEm*) p->pNext;
    } else {
        p = pAlive;
    }
    while (p) {
        if (p->id == id) {
            return p;
        }
        p = (cEm*) p->pNext;
    }
    return 0;
}

// Base character constructor: builds the damage info and the default work (initWork).
cEm::cEm()
{
    initWork();
}

// Sets EM_STATUS bit `bit` in `status`.
void cEm::setStatus(int bit)
{
    status |= 1 << bit;
}

// Clears EM_STATUS bit `bit`.
void cEm::clearStatus(int bit)
{
    status &= ~(1 << bit);
}

// 1 when EM_STATUS bit `bit` is set.
int cEm::checkStatus(int bit)
{
    if (status & (1 << bit)) {
        return 1;
    }
    return 0;
}

// Virtual: can this character be thrown / knocked by the player? Base: never (0).
int cEm::checkThrow()
{
    return 0;
}

// Assigns the item the character drops when destroyed / killed (id, count, item flags, auto
// pickup flags, item effect type); EmSetDropItem spawns it.
void cEm::setItem(u16 item_id, u16 num, u16 item_flg, u16 auto_item_flg, u8 item_eff)
{
    Item_id = item_id;
    Item_num = num;
    Item_flg = item_flg;
    Auto_item_flg = auto_item_flg;
    itemFlag = item_eff;
}

// Clears the drop item (Item_id 0xFFFF).
void cEm::setNoItem()
{
    Item_id = 0xFFFF;
    Item_num = 0;
    Item_flg = 0;
    Auto_item_flg = 0;
    itemFlag = 0;
}

#if defined(RE4DC_LOGIC_LOD_EM) && RE4DC_LOGIC_LOD_EM > 1
#include "dmg.h"
// LOGIC_LOD_EM=N (logiclod.mk; lane logiclod20 2026-10-20; an APPROXIMATION, default 0 = off; 2..4): far or off-screen
// enemies and farm animals run their whole frame step (move = AI + motion, skeleton with foot IK and cloth, old
// position) only every Nth tick, staggered by serial. Covered:
// - Ganados (ids 0x10..0x20, act_cap.cpp isGanado) only in a walking / idle routine (r_no_0 1, r_no_1 in act_cap.cpp's
//   park whitelist: Wait, Keeper, Hide, the r101 idles, Walk, Dash, Back, Goto, GuardWalk, Turn180, SitDown, Stay,
//   Guard, R100WalkStay, StayWalk, AttackWait, FindLost) and not holding Leon. Attacks, grabs, finds, door bashes,
//   ladders, damage, death and every scripted routine run every tick.
// - cows (em26) and chickens (em28) anywhere, the dog (em21) in r103 only (lane animfar17's rule).
// Skipped only while far (> LOGIC_LOD_FAR units from Leon, default 25 m, past the 25 m fog) or off screen (more than
// LOGIC_LOD_NEAR units away, default 5 m, and more than 60 degrees off the camera axis or behind it). Never skipped:
// the creation tick, a pending hit (dmg.m_Flag), a tick inside an explosion / fire volume (DmgMgr.hitCheck).
// Kills, drops, triggers and waves run in the actors' own move as before; far walkers move at 1/N speed off screen and
// the Rnd() stream differs, so this is gameplay-equivalent, not STRICT.
static int re4dc_logic_lod_skip(cEm* em)
{
    const int ganado = em->id >= 0x10 && em->id <= 0x20;
    if (ganado) {
        if (em->r_no_0 != 1 || pPL->dmgType == (int) em) {
            return 0;
        }
        switch (em->r_no_1) {
        case 0x00: case 0x01: case 0x02: case 0x07: case 0x08: case 0x09:
        case 0x10: case 0x11: case 0x12: case 0x13: case 0x14: case 0x15:
        case 0x1A: case 0x1B: case 0x1D: case 0x4C: case 0x4E: case 0x4F: case 0x5D:
            break;
        default:
            return 0;
        }
    } else if (em->id != 0x26 && em->id != 0x28 && !(em->id == 0x21 && pG->room_id == 0x103)) {
        return 0;
    } else if (em->r_no_0 == 0) {
        return 0;
    }
    if (em->dmg.m_Flag) {
        return 0;
    }
    if ((((u32) pG->Frame_cnt + (u32) em->serial) % RE4DC_LOGIC_LOD_EM) == 0) {
        return 0;
    }
    if (em->plDist2 <= (f32) RE4DC_LOGIC_LOD_NEAR * (f32) RE4DC_LOGIC_LOD_NEAR) {
        return 0;
    }
    if (em->plDist2 <= (f32) RE4DC_LOGIC_LOD_FAR * (f32) RE4DC_LOGIC_LOD_FAR) {
        const Camera* cam = &pG->Cam;
        const f32 vx = em->pos.x - cam->param.pos.x;
        const f32 vy = em->pos.y - cam->param.pos.y;
        const f32 vz = em->pos.z - cam->param.pos.z;
        const f32 f = -(vx * cam->Look.x + vy * cam->Look.y + vz * cam->Look.z);   // Look = pos - at: forward is -Look
        if (f > 0.0f && f * f >= 0.25f * (vx * vx + vy * vy + vz * vz)) {
            return 0;   // on screen
        }
    }
    if (DmgMgr.hitCheck(&em->pos, 0)) {
        return 0;
    }
    return 1;
}
#endif

#if defined(RE4DC_BODY_CORPSE) && RE4DC_BODY_CORPSE
#include "dmg.h"
// BODY_CORPSE=1 (bodysvc20.mk; lane bodysvc20 2026-10-20, master plan P3 "dead enemies cost near zero"; an
// APPROXIMATION, default 0 = off): a settled Ganado corpse skips its whole frame step. Settled = a Ganado (ids
// 0x10..0x20 but 0x18: every cEm10) resting in Die_Cramp's last state (r_no_0 3, r_no_1 0, r_no_2 2: bodies that
// never dissolve) or in Die_Lost's last state (r_no_1 3, r_no_2 2: a dissolved body, invisible and without collision,
// whose work stays alive with Reset_enable set; measured 10-20: every r103 farm kill ends here and still ran its
// whole step and ShapeMove every tick) whose position has not changed bit for bit for BODY_CORPSE_TICKS consecutive ticks (default 90: every death
// motion has ended by then). Its skeleton, part matrices and collision stay as the last full step left them, so it is
// drawn unchanged. Never skipped: a pending hit (dmg.m_Flag), a tick inside an explosion / fire volume
// (DmgMgr.hitCheck), any other routine. Scripts that remove bodies (Die_Lost, destroy) still run: a skipped corpse is
// still a live work. Kills, drops and counters happen at the death itself (Die_Cramp state 0), before any skip.
#ifndef RE4DC_BODY_CORPSE_TICKS
#define RE4DC_BODY_CORPSE_TICKS 90
#endif
struct BodyCorpse {
    const cEm* em;
    u32 frame;    // pG->Frame_cnt of the last look
    u32 ticks;    // consecutive settled ticks
    u32 pos[3];   // the position's bits
};
static BodyCorpse re4dc_body_corpse[32];
#if defined(RE4DC_BODY_LOG) && RE4DC_BODY_LOG
extern "C" void re4dc_log(const char* fmt, ...);
#endif
static int re4dc_body_corpse_skip(cEm* em)
{
#if defined(RE4DC_BODY_LOG) && RE4DC_BODY_LOG
    if (em->id >= 0x10 && em->id <= 0x20 && em->r_no_0 == 3 && ((u32) pG->Frame_cnt % 60) == 0) {
        re4dc_log("bodysvc: f=%u dead em=%08x id=%02x r=%u/%u/%u room_id32=%08x\n", (u32) pG->Frame_cnt, (u32) em,
                  em->id, em->r_no_0, em->r_no_1, em->r_no_2, (u32) pG->room_id32);
    }
#endif
    if (em->id < 0x10 || em->id > 0x20 || em->id == 0x18 || em->r_no_0 != 3 || (em->r_no_1 != 0 && em->r_no_1 != 3) ||
        em->r_no_2 != 2) {
        return 0;
    }
    const u32 now = (u32) pG->Frame_cnt;
    u32 pb[3];
    __builtin_memcpy(pb, &em->pos, 12);
    BodyCorpse* e = 0;
    BodyCorpse* lru = &re4dc_body_corpse[0];
    for (int i = 0; i < 32; i++) {
        BodyCorpse* c = &re4dc_body_corpse[i];
        if (c->em == em) {
            e = c;
            break;
        }
        if ((u32) (now - c->frame) > (u32) (now - lru->frame)) {
            lru = c;
        }
    }
    if (!e || e->frame + 1 != now || __builtin_memcmp(e->pos, pb, 12) != 0) {
        if (!e) {
            e = lru;
            e->em = em;
        }
        e->frame = now;
        e->ticks = 0;
        __builtin_memcpy(e->pos, pb, 12);
        return 0;
    }
    e->frame = now;
    if (e->ticks < RE4DC_BODY_CORPSE_TICKS) {
        e->ticks++;
        return 0;
    }
    if (em->dmg.m_Flag || DmgMgr.hitCheck(&em->pos, 0)) {
        e->ticks = 0;
        return 0;
    }
#if defined(RE4DC_BODY_LOG) && RE4DC_BODY_LOG
    {
        // BODY_LOG=1 (test arms only): skipped corpse steps, one line per 300 ticks
        static u32 skips, last;
        skips++;
        if (now - last >= 300) {
            last = now;
            re4dc_log("bodysvc: f=%u corpse skips=%u\n", now, skips);
        }
    }
#endif
    return 1;
}
#endif

// Per-character frame step for every work but the player: skips hidden works during an event
// pause (Status_flg[1] 0x10000000 unless be_flag 0x800) and the frozen partner; caches the
// squared distance to the player (plDist2), ticks the damage info, runs the virtual move(), then
// the shape (skeleton) update, the queued SE (seNo), old position update, hit box debug display
// and bounding boxes, and resets invisible_factor2.
void emMove(cEm* em)
{
    f32 dx;
    f32 dz;

    if ((em->be_flag & 0x201) != 1) {
        pLog->err(2, 0, "emMove() DEAD WORK CALLED %08X(ID:%02X)", em, em->id);
        EmMgr.destroy(em);
        return;
    }
    if ((pG->Status_flg[1] & 0x10000000) && !(em->be_flag & 0x800)) {
        return;
    }
    if (em == pPL) {
        return;
    }
    if (em == pSUB && (pG->Stop_flg & 0x1000)) {
        return;
    }
    dz = pPL->pos.z - em->pos.z;
    dx = pPL->pos.x - em->pos.x;
    em->plDist2 = dx * dx + dz * dz;
    em->l_sub = 1e16f;
#if defined(RE4DC_LOGIC_LOD_EM) && RE4DC_LOGIC_LOD_EM > 1
    if (re4dc_logic_lod_skip(em)) {
        return;
    }
#endif
#if defined(RE4DC_BODY_CORPSE) && RE4DC_BODY_CORPSE
    if (re4dc_body_corpse_skip(em)) {
        em->invisible_factor2 = 1.0f;
        return;
    }
#endif
    em->dmg.move();
#if defined(RE4DC_EL_CENSUS) && RE4DC_EL_CENSUS
    re4dc_elc_em = em;
    em->move();
    re4dc_elc_em = 0;
    if ((em->be_flag & 0x201) == 1) {
        elcEmAfterMove(em);
    }
#else
    em->move();
#endif
    if ((em->be_flag & 0x201) != 1) {
        return;
    }
    em->be_flag &= ~0x20000000;
    ShapeMove(em->pModelInfo);
    if (em->seNo) {
        int no = em->seNo - 1;
        cModel* parts = em->getPartsPtr(0);

        SndCall(8, no, &parts->world, em->id, 0, em);
        em->seNo = 0;
    }
    em->updateOldPos();
    EmYarareDisp(em);
    if (pG->Debug_flg[2] & 0x10000000) {
        DrawOba(em);
    }
    if (em->be_flag & 0x80000000) {
        em->drawAllBoundingBox(em->pModelInfo);
    }
    em->invisible_factor2 = 1.0f;
}

// Virtual per-frame behaviour; the base character does nothing.
void cEm::move()
{
}

// Default work state: be_flag 0x21 (alive, ...), kindid 0.
int cEm::initWork()
{
    be_flag = 0x21;
    kindid = 0;
    return 1;
}

// Damage info starts cleared.
cDmgInfo::cDmgInfo()
{
    clear();
}

// Registers a hit on the character: stat = flag | 1 (a hit is pending), lifetime `timer` frames
// (bit7 = hold until cleared), damage kind, hit position / radius and the hit box that was hit.
// The character's own move reads and clears it.
void cDmgInfo::set(int flag, int timer, u8 kind, Vec* p, f32 r, YARARE_INFO* prt)
{
    m_Flag = flag | 1;
    m_Timer = timer;
    m_Wep = kind;
    m_PosFrom = *p;
    m_Dist = r;
    m_pDamageYarare = prt;
}

// Sets only the state byte and the timer (player damage motions).
void cDmgInfo::set(int flag, int timer)
{
    m_Flag = flag;
    m_Timer = timer;
}

// Forgets the registered hit.
void cDmgInfo::clear()
{
    m_Flag = 0;
    m_Timer = 0;
}

// Per-frame: counts the timer down (unless bit7 holds it) and clears the hit state when it
// reaches 0, so an unhandled hit expires.
void cDmgInfo::move()
{
    if (m_Timer & 0x80) {
        return;
    }
    if ((m_Timer & 0x7F) == 0) {
        return;
    }
    m_Timer--;
    if (m_Timer == 0) {
        m_Flag = 0;
    }
}

cEmMgr EmMgr;
