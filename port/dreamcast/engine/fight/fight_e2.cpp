// E2 fight slice (lane eng-e2): the village square fight (r101) at cap 4 on the E1 engine shell.
//
// The hosted behaviour: the Ganado library (src/em10) with the village square's set file (src/em15), the enemy list and
// creator (em_set.cpp, the cap 4 hold and park), the room script (st1/r101.cpp: waves, villagers, the finding of the
// player), the scenario helpers it calls (sce_com.cpp, sce_at.cpp) and the damage records. This file is the engine side
// they run on, in the order of the original's room start (sce_sys.cpp ScenarioRoomInit) and frame (ScenarioMove):
//   - room set-up: the enemy list of chapter 1 (etc/emleon00.esl) with the PS2 USA list rows (stage.cpp's PS2 list
//     patch, the chapter's PS2 spawn lists), the room script's init (R101Init), one scheduler pass, the room-entry
//     spawn (EmSetFromList: the list at cap 4), the areas (SceAtRoomSet);
//   - the Ganado module: em/em15 with its motion keys linked in place (no disc read in play) and the module entry;
//   - the enemy table's per-tick move (cEmMgr::move / emMove in their original order, knobs off);
//   - scenario tasks: each task is a KOS thread that the engine resumes once per tick, strictly one at a time (a
//     hand-off, never concurrent), so the run is deterministic (the boss slice's form);
//   - events: SceEventStart / SceEventEnd are the hosted sce_com.cpp; what they would play (the camera cut of the
//     reset wave is the hosted camera code's CutCall) runs as the hosted code drives it; event data files are not
//     played (EvtMgr stubs, logged);
//   - the per-tick trace of the enemy table (LE lines in the reference's field order) and the gameplay events.
#include "global.h"
#include "player.h"
#include "em.h"
#include "obj.h"
#include "model.h"
#include "em_set.h"
#include "sce_sys.h"
#include "sce.h"
#include "sce_at.h"
#include "scheduler.h"
#include "e1_engine.h"
#include "e1_core.h"
#include "e1_kos.h"
#include "boss_e2.h"
#include "fight_e2.h"
#include "game.h"
#include "fx.h"
#include "read.h"
#include "esp.h"
#include <new>
#include <string.h>
#include <stdio.h>

extern "C" void em15_prolog();              // src/em15/em15_set.cpp _prolog (renamed at build): EmInitFunc = the em10 init
void R101Init();                            // src/st1/r101.cpp (hosted)
void R101Main();
extern "C" void re4dc_aliveCapMove(int busy);   // src/game/em_set.cpp (hosted, cap 4)
extern cModInfoMgr ModInfoMgr;
extern void (*EmInitFunc)(cEm* em);
class cSubChar;
extern cSubChar* pSUB;
extern cPartsMgr PartsMgr;
extern "C" void ShapeMove(void* info);
extern "C" void* e1_file_load(const char* path, uint32_t* size, uint32_t align);
extern uint32_t e1_resident_bytes[4];
void* GetDataExt(void* arc, const char* tag, int no);

cSceSys SceSys;

// ---- room globals and tables ----
void e2_room_globals()
{
    pG->pl_costume = 0;          // chapter 1: Leon with the jacket (em/pl00)
    pG->Item_find_flg = 0x2000;  // the fixture's warp: find 0x00002000 (the operator's first call already made)
}
void e2_managers_room_init()
{
    ModInfoMgr.roomInit();
    ModInfoMgr.arrayAlloc(192);
    PartsMgr.roomInit();
    PartsMgr.arrayAlloc(1024);
    EmMgr.roomInit();
    EmMgr.arrayAlloc(64);
    ObjMgr.roomInit();
    ObjMgr.arrayAlloc(64);
}

// ---- the Ganado module (read.cpp EmReadSearch, engine form): em/em15 with its motion keys in place ----
static uint32_t rd32(const uint8_t* p) { uint32_t v; memcpy(&v, p, 4); return v; }
static uint32_t container_walk(file_t f, uint32_t base, int depth, uint8_t* dst, uint32_t at)
{
    uint32_t rec[8 * 32];
    if (fs_seek(f, base + 0x20, SEEK_SET) < 0 || fs_read(f, rec, sizeof(rec)) <= 0) return at;
    for (unsigned i = 0; i < 32; i++) {
        const uint32_t* e = rec + 8 * i;
        if (e[0] == 0xFFFFFFFFu) break;
        if (e[0] == 0 && e[2] == 0) {
            if (dst) {
                fs_seek(f, base + e[3], SEEK_SET);
                fs_read(f, dst + at, e[1]);
            }
            at += (e[1] + 31u) & ~31u;
        } else if (e[0] == 4 && depth == 0) {
            at = container_walk(f, base + e[3], 1, dst, at);
        }
    }
    return at;
}
static uint32_t prefix_bytes(const uint8_t* p) { const uint32_t n = p[2]; return ((3 + 3 * n + 3) & ~3u) + 4 + 4 * n; }
struct FightModule { int id; const char* file; void (*prolog)(); uint8_t* arc; uint32_t bytes, keys, clips; void (*init)(cEm*); };
static FightModule mods[] = {{0x15, "/cd/em/em15.drs", em15_prolog, 0, 0, 0, 0, 0}};
uint32_t e2_module_bytes[2];
static void bind_motion_keys(FightModule& m)
{
    const uint32_t n = rd32(m.arc);
    for (uint32_t i = 0; i < n; i++) {
        if (memcmp(m.arc + 16 + 4 * n + 4 * i, "MTC", 3)) continue;
        const uint8_t* mtc = m.arc + rd32(m.arc + 16 + 4 * i);
        if (memcmp(mtc, "R4MOTBL", 7)) { e1_log("E2 module: MTC without R4MOTBL\n"); return; }
        const uint32_t count = rd32(mtc + 12);
        for (uint32_t j = 0; j < count; j++) {
            const uint8_t* e = mtc + 32 + 20 * j;
            const uint32_t ofs = rd32(e), size = rd32(e + 4);
            char path[64];
            snprintf(path, sizeof(path), "/cd/dc/mot/%08lx-%08lx.fcv", (unsigned long) rd32(e + 8), (unsigned long) rd32(e + 12));
            uint32_t got = 0;
            uint8_t* clip = (uint8_t*) e1_file_load(path, &got, 32);
            if (!clip || got != size || memcmp(clip, m.arc + ofs, prefix_bytes(m.arc + ofs))) {
                e1_log("E2 module: motion keys %s missing or not this archive's (%lu B, want %lu)\n", path,
                       (unsigned long) got, (unsigned long) size);
                continue;
            }
            for (uint32_t w = 0; w < n; w++) {
                uint8_t* word = m.arc + 16 + 4 * w;
                if (rd32(word) != ofs) continue;
                const uint32_t rel = (uint32_t) (uintptr_t) clip - (uint32_t) (uintptr_t) m.arc;
                memcpy(word, &rel, 4);
            }
            m.keys += size;
            m.clips++;
        }
    }
}
void* EmReadSearch(int id, void* addr, u32 size)
{
    (void) addr; (void) size;
    for (FightModule& m : mods) {
        if (m.id != id) continue;
        if (!m.arc) {
            file_t f = fs_open(m.file, O_RDONLY);
            if (f < 0) { e1_log("E2 module: missing %s\n", m.file); return 0; }
            m.bytes = container_walk(f, 0, 0, 0, 0);
            m.arc = (uint8_t*) memalign(32, m.bytes);
            if (m.arc) container_walk(f, 0, 0, m.arc, 0);
            fs_close(f);
            if (!m.arc) return 0;
            bind_motion_keys(m);
            fx_bind_archive(m.arc, m.bytes);
            fx_note_archive(m.file + 4, m.arc, m.bytes);
            e2_module_bytes[0] += m.bytes;
            e2_module_bytes[1] += m.keys;
            e1_log("E2 module: %s %lu B at %p, %lu motion clips' keys %lu B linked\n", m.file, (unsigned long) m.bytes,
                   m.arc, (unsigned long) m.clips, (unsigned long) m.keys);
            EmInitFunc = 0;
            m.prolog();
            m.init = EmInitFunc;
        }
        EmInitFunc = m.init;
        return m.arc;
    }
    e1_stub_hit("EmReadSearch(unhosted module)", id);
    return 0;
}

// read.cpp SearchEmModule: the loaded module record (the room script swaps event data through it; the engine plays
// no event data, so only the archive and its size are given)
static ReadModule mod_rec;
ReadModule* SearchEmModule(int id)
{
    for (FightModule& m : mods)
        if (m.id == id && m.arc) { mod_rec.pArc = m.arc; mod_rec.size = m.bytes; return &mod_rec; }
    e1_stub_hit("SearchEmModule(not loaded)", id);
    return &mod_rec;
}

// ---- cEmMgr::construct for the hosted kinds (em.cpp's default branch: an enemy module) ----
int e2_construct(cEm* p, unsigned id, unsigned guid)
{
    if (id < 0x10 || id >= 0x40) { e1_stub_hit("cEmMgr::construct(unhosted kind)", id); return 0; }
    p->subArc = (PlArc*) EmReadSearch(id, 0, 0);
    if (p->subArc == 0) return 0;
    // The module's init constructs the shared class in place; built without RE4DC_GAME, src/em15's Em15Init takes the
    // value-initialising form (new (em) cEm10()), which zeroes the archive pointer the original keeps (the GameCube's
    // construct leaves it in place for em10_R0_Init's set function). The engine puts it back.
    PlArc* arc = p->subArc;
    EmInitFunc(p);
    if (!p->subArc) p->subArc = arc;
    if (p->id >= 0x10 && p->id <= 0x20) p->id = 0x10;
    p->serial = guid;
    p->emset_no = 0xFF;
    p->be_flag |= 0x40;
    p->id = id;
    p->be_flag |= 0x02000000;
    p->subArc2 = p->subArc;
    e2_event(E2EV_SPAWN, p, id);
    return 1;
}

// ---- the enemy table's move (em.cpp cEmMgr::move + emMove, knobs off) ----
extern "C" void EmYarareDisp(cEm* em);
u32 SndCall(u16 blk, u16 no, Vec*, int, int, cUnit*);
static void em_move(cEm* em)
{
    if ((em->be_flag & 0x201) != 1) { e2_event(E2EV_GONE, em, em->id); EmMgr.destroy(em); return; }
    if ((pG->Status_flg[1] & 0x10000000) && !(em->be_flag & 0x800)) return;
    if (em == pPL) return;
    if ((void*) em == (void*) pSUB && (pG->Stop_flg & 0x1000)) return;
    f32 dz = pPL->pos.z - em->pos.z;
    f32 dx = pPL->pos.x - em->pos.x;
    em->plDist2 = dx * dx + dz * dz;
    em->l_sub = 1e16f;
    em->dmg.move();
    em->move();
    if ((em->be_flag & 0x201) != 1) return;
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
    em->invisible_factor2 = 1.0f;
}
static int skip_em_move_flag();
void e2_em_move()
{
    if (skip_em_move_flag()) return;
    EmMgr.dieCheck();
    if (pG->Stop_flg & 0x20000000) return;
    for (cEm* p = EmMgr.pAlive; p;) {
        cEm* cur = p;
        p = (cEm*) p->pNext;
        em_move(cur);
    }
    e2_watch_hp();
}

// ---- scenario tasks: one KOS thread per task, resumed by the engine once per tick (strict hand-off) ----
// Ordering: the original links each task into ordering slot otPrio and walks the table from slot 15 down; within a
// slot the engine keeps creation order (stated in the lane doc).
struct E2Task {
    TaskFunc func;
    int arg;
    kthread_t* thd;
    semaphore_t go, back;
    unsigned wake;
    int prio, otprio, alive, killed;
    ScePrim prim;
};
#define E2_TASKS 24
static E2Task tasks[E2_TASKS];
static E2Task* current;
static unsigned sce_tick;
unsigned e2_task_runs;
static void* task_entry(void* a)
{
    E2Task* t = (E2Task*) a;
    sem_wait(&t->go);
    ((void (*)(int)) t->func)(t->arg);
    t->alive = 0;
    sem_signal(&t->back);
    return 0;
}
static int slot_of(int prio)
{
    if (prio >= 5 && prio <= 17) return prio;
    for (int s = 17; s >= 5; s--) {
        int used = 0;
        for (unsigned i = 0; i < E2_TASKS; i++) if (tasks[i].alive && tasks[i].prio == s) used = 1;
        if (!used) return s;
    }
    return -1;
}
extern "C" ScePrim* SceExec(int prio, TaskFunc func, int arg, u8 flag, int otPrio, void* model)
{
    (void) flag; (void) model;
    if (prio == 0) { ((void (*)(int)) func)(arg); return 0; }
    const int slot = slot_of(prio);
    if (slot < 0) { e1_stub_hit("SceExec(no free slot)", prio); return 0; }
    for (unsigned i = 0; i < E2_TASKS; i++) {
        E2Task* t = &tasks[i];
        if (t->alive) continue;
        memset(t, 0, sizeof(*t));
        t->func = func; t->arg = arg; t->prio = slot; t->otprio = otPrio; t->alive = 1; t->wake = sce_tick;
        sem_init(&t->go, 0); sem_init(&t->back, 0);
        t->thd = thd_create(0, task_entry, t);
        t->prim.task = (TASK*) t;
        if (sce_tick < 2) e1_log("E2 task %u slot %d ot %d func %p arg %d tick %u\n", i, slot, otPrio, (void*) func, arg, sce_tick);
        return &t->prim;
    }
    e1_stub_hit("SceExec(no free task)", prio);
    return 0;
}
static void task_yield(int frames)
{
    E2Task* t = current;
    if (!t) { e1_stub_hit("SceSleep(outside a task)", frames); return; }
    t->wake = sce_tick + (frames > 0 ? frames : 1);
    sem_signal(&t->back);
    sem_wait(&t->go);
}
extern "C" void SceSleep(int frames) { task_yield(frames); }
void TaskSleep(int frames) { task_yield(frames); }
extern "C" void SceExit()
{
    E2Task* t = current;
    if (!t) return;
    t->alive = 0;
    sem_signal(&t->back);
    for (;;) sem_wait(&t->go);
}
void SceKill(int prio)
{
    for (unsigned i = 0; i < E2_TASKS; i++)
        if (tasks[i].alive && tasks[i].prio == prio && &tasks[i] != current) tasks[i].killed = 1, tasks[i].alive = 0;
}
void SceKill(void (*func)(int))
{
    for (unsigned i = 0; i < E2_TASKS; i++)
        if (tasks[i].alive && (void*) tasks[i].func == (void*) func && &tasks[i] != current) tasks[i].killed = 1, tasks[i].alive = 0;
}
ScePrim* SceCTask() { return current ? &current->prim : &tasks[0].prim; }
// sce_sys.cpp SceSetEventCancel (engine form): the cancel continuation is kept; the fixture never cancels.
void SceSetEventCancel(int on, TaskFunc func, int arg, int flagNo, int sndFlag)
{
    SceSys.event_cancel_enable = on == 1;
    SceSys.pCancelFunc = func;
    SceSys.cancelArg = arg;
    SceSys.cancelFlagNo = flagNo;
    SceSys.sndFlag = sndFlag;
}
// One scheduler pass (sce_sys.cpp cSceSys::scheduler): every task runs at most once a pass (its `running` mark), and
// after each run the walk starts again from the table's head, so a task another task created this pass also runs in
// this pass, as on the original.
static void scheduler_pass()
{
    bool ran[E2_TASKS] = {};
    for (;;) {
        E2Task* next = 0;
        unsigned idx = 0;
        for (int ot = 15; ot >= 0 && !next; ot--)
            for (unsigned i = 0; i < E2_TASKS; i++) {
                E2Task* t = &tasks[i];
                if (ran[i] || !t->alive || t->killed || t->wake > sce_tick || t->otprio != ot) continue;
                next = t; idx = i;
                break;
            }
        if (!next) return;
        if (pG->Stop_flg & 0x800000) return;
        ran[idx] = true;
        current = next;
        sem_signal(&next->go);
        sem_wait(&next->back);
        current = 0;
        e2_task_runs++;
    }
}

// ---- the chapter's PS2 enemy list (stage.cpp readEmList with the PS2 USA rows of list 0, PS2_ENEMY_ROOMS 0x33f) ----
static void ps2_list0()
{
    static const u8 dead00[] = {0x1A, 0x1B, 0x4E, 0x50, 0x54, 0x55, 0x57, 0x58, 0x5C,
                                0xA5, 0xA6, 0xA7, 0xA8, 0xA9, 0xED, 0xEE, 0xEF, 0xC2, 0xC3};
    EM_LIST(3)->flag = 0x8000003C;      // r100 (bit 0x01)
    EM_LIST(4)->flag = 0x2000003C;
    EM_LIST(0xF1)->flag = 0x01032400;   // r104 (bit 0x04)
    EM_LIST(0xF1)->Character = 1;
    for (unsigned i = 0; i < sizeof(dead00); i++) EM_LIST(dead00[i])->be_flag &= ~1;
    for (unsigned i = 0x22; i <= 0x24; i++) { EM_LIST(i)->flag |= 0x80; EM_LIST(i)->Character = 0; }
    EM_LIST(0x45)->flag &= ~0x400;
    EM_LIST(0x46)->flag &= ~0x400;
}

// ---- room init (sce_sys.cpp ScenarioRoomInit order) ----
static GameSaveData save_data;
static GameSaveBlock save_global;
void e2_watchdog_start();
void e2_room_init()
{
    e2_watchdog_start();
    pSaveData = &save_data;
    save_data.pGlobal = &save_global;
    // a new game's difficulty points (game.cpp GamePointInit(0): 5500, rank 5; the fixture's warp starts a new game):
    // enemy damage and the AI read the rank
    GamePointInit(0);
    uint32_t n = 0;
    uint8_t* list = (uint8_t*) e1_file_load("/cd/etc/emleon00.esl", &n, 32);
    if (list && n <= sizeof(pG->Em_list)) { memset(pG->Em_list, 0, sizeof(pG->Em_list)); memcpy(pG->Em_list, list, n); }
    else e1_log("E2 load: etc/emleon00.esl missing or %lu B\n", (unsigned long) n);
    free(list);
    pG->em_list_no = 0;
    ps2_list0();
    // game.cpp gameRoomInit, the parts this slice needs, in its order: the effect service's room start with the common
    // effect data (eff_sys.cpp EspInit: core owners 0 and 0xD1) and the room's (EFF, owner 1); packed records of the
    // archives bound for decoding; the scenario areas (AEV, ITA); the enemy list's room state.
    e2_fx_room_init();
    fx_note_archive("etc/core.das", e1_core_arc, e1_resident_bytes[3]);
    // the room archive is loaded reduced to the sections the fight reads (core/loader.cpp): its effect data is named
    // by section for the equivalence check, which reads the same section from the disc's archive
    if (void* eff = GetDataExt(pG->pRoom, "EFF", 0)) fx_note_archive("st1/r101.arc:EFF", eff, 0x100000);
    fx_note_archive("em/wep02.drs", e1_wep_arc, e1_resident_bytes[1]);
    fx_note_archive("em/pl00.drs", e1_pl_arc, e1_resident_bytes[0]);
    fx_bind_archive(e1_core_arc, e1_resident_bytes[3]);
    fx_bind_archive(e1_room_arc, e1_resident_bytes[2]);
    fx_bind_archive(e1_wep_arc, e1_resident_bytes[1]);
    fx_bind_archive(e1_pl_arc, e1_resident_bytes[0]);
    EspDataLoad(pG->pArc->ofs_14 + (u32) pG->pArc, 0, 0);
    EspDataLoad(pG->pArc->ofs_50 + (u32) pG->pArc, 0xD1, 0);
    if (void* eff = GetDataExt(pG->pRoom, "EFF", 0)) EspDataLoad((u32) eff, 1, 0);
    SceAtInit(GetDataExt(pG->pRoom, "AEV", 0), GetDataExt(pG->pRoom, "ITA", 0));
    EmSetRoomInit();
    SceSys.event_start_cnt = 0;
    SceSys.cancelFlagNo = -1;
    SceSys.sndFlag = 1;
}

// The scenario's room start (sce_sys.cpp ScenarioRoomInit: the room script's init, one scheduler pass, the room-entry
// spawn at cap 4, the areas). The old game runs it on the frame after the player is placed (its enemies' first logged
// state is the creation move's, one tick after the player's first), so the engine runs it as tick 1's scenario step,
// and the enemy table does not move again that tick.
static int scenario_started, skip_em_move;
static int skip_em_move_flag() { const int s = skip_em_move; skip_em_move = 0; return s; }
static void scenario_room_init()
{
    SceExecInitCondition();
    R101Init();
    scheduler_pass();
    EmSetFromList();
    SceAtRoomSet();
    e1_log("E2 room init: alive %d tasks %u weapon %d/%d lv %d/%d/%d/%d\n", SceCountEmAlive(0x10, 0x20), e2_task_runs, (int) pG->weapon_no, (int) pG->weapon_type, (int) pG->weapon_lv_power, (int) pG->weapon_lv_speed, (int) pG->weapon_lv_reload, (int) pG->weapon_lv_blt);
}

// ---- per tick (sce_sys.cpp ScenarioMove, engine form): room main, tasks, moving areas, the cap's release ----
void e2_scenario_move(unsigned tick)
{
    sce_tick = tick;
    if (!scenario_started) {
        if (tick == 0) return;   // room_init's own pass (tick 0): the scenario starts on tick 1
        scenario_started = 1;
        scenario_room_init();
        skip_em_move = 1;
        return;
    }
    GameAddPoint(0);
    SceExecCheckCondition();
    if (!(pG->Status_flg[0] & 0x100000)) R101Main();
    scheduler_pass();
    SceAtCheckMoveScrAt();
    re4dc_aliveCapMove(SceSys.event_start_cnt != 0 || SceSys.m_item_get != 0 || SceSys.pause != 0 ||
                       (pG->Status_flg[0] & 0x101000) != 0);
}

// ---- a stall watchdog (diagnostic): every 2 s without a new tick it prints the main thread's saved pc and pr (the
// address list maps them to functions: s/a2l.sh) ----
static kthread_t* main_thd;
static void* watchdog(void*)
{
    uint32_t last = ~0u;
    unsigned same = 0;
    for (;;) {
        thd_sleep(2000);
        if (e1_state[3]) return 0;   // the run is over (report printed): nothing to watch
        if (e1_tick != last) { last = e1_tick; same = 0; continue; }
        if (++same > 8) continue;
        if (main_thd) e1_log("E2 STALL tick %lu pc %08lx pr %08lx r14 %08lx\n", (unsigned long) e1_tick,
                             (unsigned long) main_thd->context.pc, (unsigned long) main_thd->context.pr,
                             (unsigned long) main_thd->context.r[14]);
        for (unsigned i = 0; i < E2_TASKS; i++)
            if (tasks[i].alive && tasks[i].thd)
                e1_log("E2 STALL task %u pc %08lx pr %08lx\n", i, (unsigned long) tasks[i].thd->context.pc,
                       (unsigned long) tasks[i].thd->context.pr);
    }
    return 0;
}
void e2_watchdog_start()
{
    main_thd = thd_get_current();
    thd_create(1, watchdog, 0);
}
