// E2 boss slice (lane eng-boss): El Gigante's original AI (src/em2b) and its arena script (src/st1/r119) hosted on the
// E1 engine shell. This file is the engine side the hosted code runs on:
//   - room set-up for the arena (enemy list, the boss module's archive and entry, the room script's init);
//   - the enemy table's per-tick move (cEmMgr::move / emMove in their original order, knobs off);
//   - scenario tasks (SceExec / SceSleep): each task is a KOS thread that the engine resumes once per tick at the
//     ScenarioMove point, strictly one at a time (a hand-off, never concurrent), so the run is deterministic;
//   - the area trigger the room script arms (SceAtDataSet_exec): fired when the engine places the player, as the
//     reference's warp does (the player starts inside area 2);
//   - the per-tick trace of the enemy table (LE lines in the reference's field order).
// Effects go through boss_fx.cpp (the engine effect service), stubs of other behaviour through boss_stubs.cpp.
#include "global.h"
#include "player.h"
#include "em.h"
#include "obj.h"
#include "model.h"
#include "em_set.h"
#include "sce_sys.h"
#include "scheduler.h"
#include "e1_engine.h"
#include "e1_core.h"
#include "e1_kos.h"
#include "boss_e2.h"
#include "game.h"
#include <new>
#include <string.h>
#include <stdio.h>

extern "C" void em2b_prolog();              // src/em2b/em2b.cpp _prolog (renamed at build): EmInitFunc = Em2bInit
void R119Init();                            // src/st1/r119.cpp (hosted)
void R119Main();
extern cModInfoMgr ModInfoMgr;
extern void (*EmInitFunc)(cEm* em);   // em.cpp (engine: services/managers.cpp)
class cSubChar;
extern cSubChar* pSUB;
extern cPartsMgr PartsMgr;
extern "C" void ShapeMove(void* info);
extern "C" void* e1_file_load(const char* path, uint32_t* size, uint32_t align);

uint8_t* e2_em_arc;                          // em/em2b.drs body (the boss module's archive)
uint32_t e2_em_arc_bytes;
static uint8_t* drs_body_e2(const char* path, uint32_t* bytes)
{
    file_t f = fs_open(path, O_RDONLY);
    if (f < 0) { e1_log("E2 load: missing %s\n", path); return NULL; }
    uint32_t rec[64];
    fs_read(f, rec, sizeof(rec));
    uint32_t size = 0, off = 0;
    for (unsigned i = 8; i + 8 <= 64; i += 8) {
        if (rec[i] == 0xFFFFFFFFu) break;
        if (rec[i] == 0) { size = rec[i + 1]; off = rec[i + 3]; break; }
    }
    uint8_t* p = size ? (uint8_t*) memalign(32, size) : NULL;
    if (!p || fs_seek(f, off, SEEK_SET) < 0 || fs_read(f, p, size) != (ssize_t) size) {
        e1_log("E2 load: bad DRS %s\n", path); fs_close(f); free(p); return NULL;
    }
    fs_close(f);
    *bytes = size;
    return p;
}

// ---- room globals and tables ----
void e2_room_globals()
{
    pG->pl_costume = 1;          // chapter 2: Leon without the jacket (ReadPlayerData costume 1 = file 0x5A, em/pl08)
    pG->Item_find_flg = 0;
}
void e2_managers_room_init()
{
    ModInfoMgr.roomInit();
    ModInfoMgr.arrayAlloc(128);
    PartsMgr.roomInit();
    PartsMgr.arrayAlloc(512);
    EmMgr.roomInit();
    EmMgr.arrayAlloc(32);
    ObjMgr.roomInit();
    ObjMgr.arrayAlloc(64);
}

// ---- the enemy module read table (read.cpp EmReadSearch, engine form): the boss module only ----
void* EmReadSearch(int id, void* addr, u32 size)
{
    (void) addr; (void) size;
    if (id == 0x2B && e2_em_arc) {
        em2b_prolog();           // the module's entry: EmInitFunc = Em2bInit (the reference's EM_INIT_FUNC from its slot)
        return e2_em_arc;
    }
    e1_stub_hit("EmReadSearch(unhosted module)", id);
    return 0;
}

// ---- cEmMgr::construct for the arena's enemy-table kinds (em.cpp's switch, the hosted cases) ----
#include "emtree.h"
#include "emtorch.h"
int e2_construct(cEm* p, unsigned id, unsigned guid)
{
    e1_log("E2 construct id %x at %p tick %lu\n", id, (void*) p, (unsigned long) e1_tick);
    switch (id) {
    case 0x47: p = new (p) cEmTorch; break;
    case 0x49: p = new (p) cEmTree; break;
    default:
        if (id < 0x10 || id >= 0x40) { e1_stub_hit("cEmMgr::construct(unhosted kind)", id); return 0; }
        p->subArc = (PlArc*) EmReadSearch(id, 0, 0);
        if (p->subArc == 0) return 0;
        EmInitFunc(p);
        break;
    }
    p->serial = guid;
    p->emset_no = 0xFF;
    p->be_flag |= 0x40;
    p->id = id;
    p->be_flag |= 0x02000000;
    p->subArc2 = p->subArc;
    return 1;
}

// ---- the enemy table's move (em.cpp cEmMgr::move + emMove, knobs off; RouteCk not hosted: no route nodes here) ----
extern "C" void EmYarareDisp(cEm* em);
u32 SndCall(u16 blk, u16 no, Vec*, int, int, cUnit*);
static void em_move(cEm* em)
{
    if ((em->be_flag & 0x201) != 1) { EmMgr.destroy(em); return; }
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
void e2_em_move()
{
    EmMgr.dieCheck();
    if (pG->Stop_flg & 0x20000000) return;
    for (cEm* p = EmMgr.pAlive; p;) {
        cEm* cur = p;
        p = (cEm*) p->pNext;
        em_move(cur);
    }
}

// ---- scenario tasks: one KOS thread per task, resumed by the engine once per tick (strict hand-off) ----
struct E2Task {
    TaskFunc func;
    kthread_t* thd;
    semaphore_t go, back;
    unsigned wake;       // engine tick at which it runs next
    int prio, alive, killed, started;
    ScePrim prim;
};
#define E2_TASKS 24
static E2Task tasks[E2_TASKS];
static E2Task* current;
static unsigned sce_tick;
unsigned e2_task_runs;
static void* task_entry(void* arg)
{
    E2Task* t = (E2Task*) arg;
    sem_wait(&t->go);
    t->func();
    t->alive = 0;
    sem_signal(&t->back);
    return 0;
}
extern "C" ScePrim* SceExec(int prio, TaskFunc func, int arg, u8 flag, int otPrio, void* model)
{
    (void) arg; (void) flag; (void) otPrio; (void) model;
    for (unsigned i = 0; i < E2_TASKS; i++) {
        E2Task* t = &tasks[i];
        if (t->alive) continue;
        memset(t, 0, sizeof(*t));
        t->func = func; t->prio = prio; t->alive = 1; t->wake = sce_tick;
        sem_init(&t->go, 0); sem_init(&t->back, 0);
        t->thd = thd_create(0, task_entry, t);
        t->prim.task = (TASK*) t;
        e1_log("E2 task %u created prio %d func %p tick %u\n", i, prio, (void*) func, sce_tick);
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
    for (;;) sem_wait(&t->go);   // never resumed
}
void SceKill(int prio)
{
    for (unsigned i = 0; i < E2_TASKS; i++) if (tasks[i].alive && tasks[i].prio == prio && &tasks[i] != current) tasks[i].killed = 1;
}
// One scheduler pass (sce_sys.cpp SceSys.scheduler, engine form): every live task whose wake tick has come runs until
// it sleeps or ends, in creation order.
static void scheduler_pass()
{
    for (unsigned i = 0; i < E2_TASKS; i++) {
        E2Task* t = &tasks[i];
        if (!t->alive || t->killed || t->wake > sce_tick) continue;
        current = t;
        if (e2_task_runs < 8) e1_log("E2 run task %u tick %u\n", i, sce_tick);
        sem_signal(&t->go);
        sem_wait(&t->back);
        current = 0;
        e2_task_runs++;
    }
}

// ---- area triggers (sce_at.cpp SceAtDataSet_exec, engine form): the room script's area-2 appearance task ----
static TaskFunc area_func[16];
extern "C" void SceAtDataSet_exec(int no, int prio, int a, TaskFunc func, void* obj, int b)
{
    (void) prio; (void) a; (void) obj; (void) b;
    if (no >= 0 && no < 16) area_func[no] = func;
    e1_log("E2 area %d armed func %p\n", no, (void*) func);
}
extern "C" void SceAtSetEnable(int no, int on) { (void) no; (void) on; }

// ---- room init: enemy list, boss archive, room script ----
static GameSaveData save_data;          // the save block the difficulty code mirrors its points into (game.cpp)
static GameSaveBlock save_global;
void e2_room_init()
{
    pSaveData = &save_data;
    save_data.pGlobal = &save_global;
    uint32_t n = 0;
    uint8_t* list = (uint8_t*) e1_file_load("/cd/EMLIST.BIN", &n, 32);
    if (list && n == sizeof(pG->Em_list)) memcpy(pG->Em_list, list, n);
    else e1_log("E2 load: EMLIST.BIN missing or %lu B\n", (unsigned long) n);
    free(list);
    // the boss archive with its motion clips in place (bake/em_archive.py: the old port keeps them out of the
    // archive and reads them on use; the engine reads no disc in play)
    e2_em_arc = (uint8_t*) e1_file_load("/cd/EM2B.ARC", &e2_em_arc_bytes, 32);
    e1_log("E2 load: em2b archive %lu B at %p\n", (unsigned long) e2_em_arc_bytes, e2_em_arc);
    R119Init();
    if (area_func[2]) SceExec(SCE_PRIO_DEF_2, area_func[2], 0, 0, 0, 0);   // the player starts inside area 2
    // The reference fires the area on the tick the warp places the player (its tick 184 = engine tick 0): the
    // scenario pass and the enemy-table move of that tick run here, before the first engine tick.
    e2_scenario_move(0);
    e2_em_move();
}

// ---- per tick: ScenarioMove (room main, tasks), then the enemy table ----
void e2_scenario_move(unsigned tick)
{
    sce_tick = tick;
    GameAddPoint(0);            // gameMainLoop: the difficulty rank update, before the scenario
    if (tick < 2) e1_log("E2 tick %u tasks %u\n", tick, e2_task_runs);
    R119Main();
    scheduler_pass();
}

// ---- trace: the reference's LE line for every enemy-table work but the player (logic_trace.cpp em_diag) ----
template <class T> static unsigned w4(const T& v) { unsigned w = 0; memcpy(&w, &v, sizeof(v) < 4 ? sizeof(v) : 4); return w; }
void e2_trace_tick(unsigned tick, char* out, unsigned cap, unsigned* used)
{
    unsigned k = 0;
    for (cEm* e = EmMgr.pAlive; e; e = (cEm*) e->pNext) {
        if (e == pPL) continue;
        int n = snprintf(out + *used, cap - *used, "LE t=%u k=%u id=%x type=%x be=%08x stat=%08x ms=%x hp=%x mf=%08x pos=%08x,%08x,%08x ay=%08x\n",
                         tick, k++, w4(e->id), w4(e->type), w4(e->be_flag), w4(e->stat), w4(e->Motion.Mot_state), w4(e->hp),
                         w4(e->Motion.Mot_frame), w4(e->pos.x), w4(e->pos.y), w4(e->pos.z), w4(e->ang.y));
        if (n > 0 && *used + n < cap) *used += n;
    }
    if (pPL) {
        int n = snprintf(out + *used, cap - *used, "LL t=%u hp=%x st=%08x ms=%x\n", tick, w4(pPL->hp), w4(pPL->stat),
                         w4(pPL->Motion.Mot_state));
        if (n > 0 && *used + n < cap) *used += n;
    }
}
