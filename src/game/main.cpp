#if defined(RE4DC_FALLBACK_AUDIT29) && RE4DC_FALLBACK_AUDIT29
#include "fallback_audit29.h"
#endif
#line 1
// game/main: entry point, frame loop, system init and reset handling (D:/Bio4/Prog/main.cpp).
#include "types.h"
#include "global.h"
#include "joy.h"

// .sbss objects in the order the original lays them out (uninitialised globals are emitted in
// first-declaration order, header externs included: main.h's pRK must come after these).
void* pFrame_buff[2];
void* pCurrent_buff;
f32 ZNEAR;
f32 ZFAR;
f32 ORTHO_T;
f32 ORTHO_B;
f32 ORTHO_L;
f32 ORTHO_R;

#include "main.h"
#include "main_sub.h"
#include "main_mem.h"
#include "view.h"
#include "atari.h"
#include "light.h"
#include "ctrl.h"
#include "map_obj.h"
#include "widget.h"
#include "card.h"
#include "event.h"
#include "sofdec.h"
#include "dvd.h"
#include "mes.h"
#include "id_sys.h"
#include "block.h"
#include "datactrl.h"
#include "em.h"
#include "obj.h"
#include "cockpit.h"
#include "room_data.h"
#include "db_log.h"
#include "scheduler.h"
#include "fade.h"
#include "cinesco.h"
#include "libgpu.h"
#include "trans_ot.h"
#include "pad.h"
#include "file.h"
#include "snd.h"
#include "dbmodule.h"
#include "cloth.h"
#include "filter.h"
#include "room_tex.h"
#include "TexRender.h"
#include "camera.h"
#include "gx_sub.h"
#include "gx.h"
#include "os_vi.h"
#include "rnd.h"
#include "sscrn.h"
#if defined(RE4DC_WORLD_CENSUS24) && RE4DC_WORLD_CENSUS24
#include "world_census24.h"
// Keep these calls on existing source lines: disabled builds retain __LINE__.
#define WC24_BEGIN() re4dc::wc24::begin_tick(pG->Frame_cnt, unsigned(pG->room_id));
#define WC24_END() re4dc::wc24::end_tick();
#define WC24_RESET() re4dc::wc24::reset();
#define WC24_WAIT() re4dc::wc24::WaitScope wc24_wait(re4dc::wc24::VblankWait);
#if RE4DC_PACE_CATCHUP
#define WC24_DECISION() re4dc::wc24::decision(!re4dc_pace_skipping);
#else
#define WC24_DECISION() re4dc::wc24::decision(true);
#endif
#else
#define WC24_BEGIN()
#define WC24_END()
#define WC24_RESET()
#define WC24_WAIT()
#define WC24_DECISION()
#endif
#if defined(RE4DC_DRAW_SETUP_AUDIT) && RE4DC_DRAW_SETUP_AUDIT
#include "draw_setup_audit.h"
#define DSA24_BEGIN() re4dc::dsa24::begin_tick(pG->Frame_cnt,unsigned(pG->room_id));
#define DSA24_END() re4dc::dsa24::end_tick();
#define DSA24_RESET() re4dc::dsa24::reset();
#define DSA24_SETUP_BEGIN() re4dc::dsa24::begin_setup();
#define DSA24_SETUP_END() re4dc::dsa24::end_setup();
#define DSA24_BEFORE(call) { const re4dc::dsa24::Scope dsa_begin(re4dc::dsa24::FrameBegin); call; }
#if RE4DC_PACE_CATCHUP
#define DSA24_DECISION() re4dc::dsa24::decision(!re4dc_pace_skipping);
#else
#define DSA24_DECISION() re4dc::dsa24::decision(true);
#endif
#else
#define DSA24_BEGIN()
#define DSA24_END()
#define DSA24_RESET()
#define DSA24_SETUP_BEGIN()
#define DSA24_SETUP_END()
#define DSA24_BEFORE(call) call
#define DSA24_DECISION()
#endif
#if defined(RE4DC_DRAW_FALLBACK_AUDIT) && RE4DC_DRAW_FALLBACK_AUDIT
#include "draw_fallback_audit.h"
#define DFA26_BEGIN() re4dc::dfa26::begin_tick(pG->Frame_cnt,unsigned(pG->room_id));
#define DFA26_END() re4dc::dfa26::end_tick();
#define DFA26_RESET() re4dc::dfa26::reset();
#if RE4DC_PACE_CATCHUP
#define DFA26_DECISION() re4dc::dfa26::decision(!re4dc_pace_skipping);
#else
#define DFA26_DECISION() re4dc::dfa26::decision(true);
#endif
#else
#define DFA26_BEGIN()
#define DFA26_END()
#define DFA26_RESET()
#define DFA26_DECISION()
#endif
#line 58

extern "C" {
void __main();
void OSReport(const char* fmt, ...);
void OSInit();
u32 OSGetConsoleType();
void OSInitAlarm();
void VIInit();
void VIWaitForRetrace();
void VISetPostRetraceCallback(void (*cb)());
void LCEnable();
void PPCSync();
int DBIsDebuggerPresent();
u32 OSGetResetButtonState();
void PADRecalibrate(u32 mask);
void OSResetSystem(int reset, u32 resetCode, int forceMenu);
void GXCopyDisp(void* dest, u8 clear);
// game/title.cpp
void Title_task();
// game/debug.cpp
void ProcessTickInit();
void ProcessTickGet(int no, const char* name);
#if defined(RE4DC_TICK_LOG) && RE4DC_TICK_LOG
void ProcessTickLog();  // game/debug.cpp
#endif
void DebugControl();
void ConfigSet();
// game/trans.cpp
void Render();
#if defined(RE4DC_LOGIC_TRACE) && RE4DC_LOGIC_TRACE
extern "C" void re4dc_logic_trace_tick(void);  // port/dreamcast/game/logic_trace.cpp
#endif
#if RE4DC_PACE_CATCHUP
// port/dreamcast/game/pace.cpp (PACE_CATCHUP, pace.mk): frame pacing with render skip.
extern "C" int re4dc_pace_skipping;
extern "C" int re4dc_pace_drop_models;
#ifndef RE4DC_PACE_TRANS_SKIP
#define RE4DC_PACE_TRANS_SKIP 0
#endif
#define PTS(b) ((RE4DC_PACE_CATCHUP >= 2) && (RE4DC_PACE_TRANS_SKIP & (b)) && re4dc_pace_drop_models)
extern "C" void re4dc_pace_reset(void);
extern "C" void re4dc_pace_begin(void);
extern "C" void re4dc_pace_decide_image(void);
extern "C" int re4dc_pace_itask(void);
extern "C" int re4dc_pace_end(void);
extern "C" void re4dc_pace_test_draw(void);
extern "C" void re4dc_pace_test_tick(void);
#endif
#if defined(RE4DC_LOAD_INDICATOR) && RE4DC_LOAD_INDICATOR
extern "C" int re4dc_loadind_active;
extern "C" void re4dc_loadind_frame();
#endif
#if defined(RE4DC_OTHER_PROFILE) && RE4DC_OTHER_PROFILE
#define RE4DC_OTHER_UNIT "main"
#include "other_profile.h"
#else
#define OTHER_PHASE(p) ((void)0)
#endif
void SetPrimBuffPtr();
#if defined(RE4DC_MODEL_WALK_CHECK) && RE4DC_MODEL_WALK_CHECK
extern "C" void re4dc_ot_check(const char* where);  // model_asset_bridge.cpp (debug only)
#define MWC(w) re4dc_ot_check(w)
#else
#define MWC(w)
#endif
void Trans();
// game/eprintf.cpp
void EprintfInit();
void EprintfFlush();
// game/trans_lit.cpp
void LightSetInit();
// game/id_tex.cpp
void IdTexGameInit();
// game/eff_sys.cpp
void EspInit();
// game/shadow.cpp
void ShadowInit();
// game/item_model.cpp
void ItemModelInit();
// game/EtcModel.cpp
void EtcModelInit();
// game/card.cpp
void CardInit();
void CardDbgCacheSet();
// game/read.cpp
void EmReadInit();
void ReleasePlData();
void ReleaseWepData();
#if defined(RE4DC_RESET_MEM_FIX) && RE4DC_RESET_MEM_FIX && defined(RE4DC_ACTOR_PL08_PACK) && RE4DC_ACTOR_PL08_PACK
extern "C" void re4dc_pl08_pack_forget();  // port/dreamcast/game/coarse_actor_pl08_pack.inc
#endif
#if defined(RE4DC_WARP_AFTER_RESET) && RE4DC_WARP_AFTER_RESET
extern "C" void re4dc_warp_soft_reset(void);  // port/dreamcast/game/dbgwarp_bridge.cpp
#endif
// game/exception.cpp
void ExceptionInit();
// game/espgen.cpp
int EspgenInit();
}
void AllocDrawTmpBuf();   // game/TmpBuf.cpp
void DbmenuModuleInit();  // game/db_menu.cpp

#define HALT()                                                    \
    {                                                             \
        OSReport("HALT %s(%d)\n", __FILE__, __LINE__);            \
        RE4DC_HALT_STORE();                                       \
    }

// Stores through a scalar reference are not struct-member MEMs, so GCC 2.95 assumes they may
// alias pG/pSys/pRK and reloads the pointer after each one, as the original does.
static inline void U8Set(u8& d, u8 v) { d = v; }
static inline void S8Set(s8& d, s8 v) { d = v; }
static inline void U16Set(u16& d, u16 v) { d = v; }
static inline void U32Set(u32& d, u32 v) { d = v; }
// Word store at a byte offset from a member array: `*(u32*) ((u8*) base + ofs)` is an
// INDIRECT_REF of a cast (not of a PLUS_EXPR), so the MEM is not in-struct either.
static inline void U32SetOfs(void* base, int ofs, u32 v) { *(u32*) ((u8*) base + ofs) = v; }
static inline u32 U32GetOfs(void* base, int ofs) { return *(u32*) ((u8*) base + ofs); }

#line 40 "D:/Bio4/Prog/main.cpp"

const Vec vecZero = {0.0f, 0.0f, 0.0f};

GlobalWork Global;
SystemSaveWork SystemSave;
JOY Joy[4];
KeyWork Key;
u32 MainOt[5];
ScreenInfo Screen;

GlobalWork* pG = &Global;
SystemWork* pSys = (SystemWork*) &SystemSave;
#if defined(__PPC__)
int vsync_cnt = 0;
#else
// Busy-waited on by main() and dvd.cpp while the vblank handler advances it:
// the Dreamcast compiler must re-read it on every iteration.
volatile int vsync_cnt = 0;
#endif


RK* pRK;
char* pUser_name;
void* roomInfoAddr;
s8 system_vcnt;

static void systemScreenInit();

// Program entry: systemStartInit (hardware/OS/GX/sound/memory), then per (soft) reset
// systemRestartInit, restores the reset-keep block (pRK: system flags, language, unlock flags,
// mercenaries records), starts the title task and runs the frame loop forever: pad read, debug,
// render set-up, TaskScheduler (game logic), id sprites, Trans (3D draw), DVD/sound watchers,
// fades, messages, cinescope, the 2D OT, log flush, interrupt tasks, render done, vsync wait
// (GetSystemVcnt frames), buffer swap and systemResetCheck (soft reset -> RESTART).
int main()
{
    int i;
    int j;
    int ret;

    systemStartInit();
RESTART: WC24_RESET() DSA24_RESET() DFA26_RESET()
#if defined(RE4DC_FALLBACK_AUDIT29) && RE4DC_FALLBACK_AUDIT29
    re4dc::fa29::reset();
#endif
#line 82
    {
        systemRestartInit();
#if RE4DC_VMU_CONTEXT && !defined(__PPC__)
        re4dc_vmu_reset();
#endif
#if RE4DC_PACE_CATCHUP
        re4dc_pace_reset();
#endif
        if (pRK->valid) {
            U32Set(pSys->flags, pRK->sys_flags);
            U8Set(pSys->language, pRK->language);
            U8Set(pSys->region, pRK->region);
            U8Set(pG->language, pRK->game_language);
            U32Set(pSys->unlock_flg, pRK->sys_unlock_flg);
            for (i = 0; i < 16; i += 4) {
                U32SetOfs(pSys->merc_stage, i, U32GetOfs(pRK->sys_merc_stage, i));
            }
            for (j = 0; j < 2; j++) {
                U32SetOfs(pSys->merc_rank, j * 4, pRK->sys_merc_rank[j]);
            }
            if ((s32) pRK->g_flags_54 < 0) {
                pG->System_flg |= 0x80000000;
            }
            if (pRK->g_flags_54 & 0x40000000) {
                pG->System_flg |= 0x40000000;
            }
        }
        ret = 0;
        if (pG->System_flg & 0x8) {
            U16Set(pG->room_id, 0x120);
            pG->JumpPoint = 0;
            pSys->language = 1;
            pG->debug_mode = 0;
            pG->pl_type = 0;
            BitOff(pG->Debug_flg[3], 0x2000);
        }
        TaskExec(0, Title_task, 0);
        for (;;) { WC24_BEGIN() DSA24_BEGIN() DFA26_BEGIN()
#if defined(RE4DC_FALLBACK_AUDIT29) && RE4DC_FALLBACK_AUDIT29
            re4dc::fa29::begin_tick(pG->Frame_cnt,unsigned(pG->room_id));
#endif
#line 120
#if defined(RE4DC_LOGIC_TRACE) && RE4DC_LOGIC_TRACE
            // Determinism trace (LOGIC_TRACE=1 test builds only): the state left by the previous
            // iteration's complete logic + render pass, independent of how long rendering took.
            re4dc_logic_trace_tick();
#endif
#if RE4DC_PACE_CATCHUP
            // Draw or skip this iteration (re4dc_pace_skipping: Render_before, ModelRender,
            // Render_swap); the logic tick below runs in full either way.
            re4dc_pace_begin();
#endif
            OTHER_PHASE(4); WC24_DECISION() DSA24_DECISION() DFA26_DECISION() // definitive bench_iter boundary: after pace_begin
#if defined(RE4DC_FALLBACK_AUDIT29) && RE4DC_FALLBACK_AUDIT29
#if RE4DC_PACE_CATCHUP
            re4dc::fa29::decision(!re4dc_pace_skipping);
#else
            re4dc::fa29::decision(true);
#endif
#endif
#line 131
            StopwatchInit();
            ProcessTickInit(); DSA24_SETUP_BEGIN()
            MWC("top");
            DSA24_BEFORE(Render_before());
            ClearOTagR(MainOt, 5);
            PadRead();
            DebugControl();
            Render();
#if RE4DC_PACE_CATCHUP
            re4dc_pace_test_draw();
#endif
            ProcessTickGet(4, "RENDER SETUP"); DSA24_SETUP_END()
            SetPrimBuffPtr();
            ClearOt();
            MWC("clear");
            pG->Frame_cnt++;
            OTHER_PHASE(0);
            TaskScheduler();
            OTHER_PHASE(4);
            MWC("tasks");
#if RE4DC_VMU_CONTEXT && !defined(__PPC__)
            re4dc_vmu_snapshot();
#endif
#if RE4DC_PACE_CATCHUP
            re4dc_pace_test_tick();
            re4dc_pace_decide_image();  // v2: whether this tick's image (models) is dropped
#endif
            ProcessTickGet(5, "TaskScheduler");
#if defined(RE4DC_LOAD_INDICATOR) && RE4DC_LOAD_INDICATOR
            // LOAD_INDICATOR (PS2 main loop): while the loading id is up, the ids move and draw after the fade.
            if (!re4dc_loadind_active)
#endif
            if (!(pG->System_flg & 0x100000) || (pG->Status_flg[0] & 0x40000)) {
                IdSys.move();
            }
#if defined(RE4DC_LOAD_INDICATOR) && RE4DC_LOAD_INDICATOR
            if (!re4dc_loadind_active)
#endif
            if (!(pG->System_flg & 0x100000) || (pG->Status_flg[0] & 0x40000)) {
#if RE4DC_PACE_CATCHUP
                if (!PTS(128))
#endif
                IdSys.trans();
            }
            if (!(pG->System_flg & 0x100000)) {
                Trans();
            }
            MWC("trans");
            Dvd.Watcher();
            SndWatcher();
            MWC("watch");
            ProcessTickGet(5, "SndWatcher");
            FadeControl(0);
            cMes.Move();
#if RE4DC_PACE_CATCHUP
            if (!PTS(512))
#endif
            cMes.Trans();
            MWC("mes");
            CinescoMove();
            if (!(pG->Debug_flg[0] & 0x8000)) {
                Draw_cinesco();
            }
            FadeControl(1);
            MWC("fade");
#if defined(RE4DC_LOAD_INDICATOR) && RE4DC_LOAD_INDICATOR
            if (re4dc_loadind_active) {
                re4dc_loadind_frame();
            }
#endif
#if RE4DC_PACE_CATCHUP
            if (!PTS(256))
#endif
            DrawOTag(&MainOt[4]);
            MWC("otag");
            if (pG->debug_mode != 7) {
                pLog->disp();
            }
            EprintfFlush();
            ProcessTickGet(2, "PROCESS CPU");
#if RE4DC_PACE_CATCHUP
            if (re4dc_pace_itask())
#endif
            iTaskScheduler();
            MWC("itask");
            Render_done();
            MWC("rdone");
            Block.checkCommand();
            DC.check();
            Block.checkCondition();
            ProcessTickGet(3, "DRAW REMAIN");
            OTHER_PHASE(5);
#if RE4DC_PACE_CATCHUP
            if (!re4dc_pace_skipping)
#endif
            { WC24_WAIT() RE4DC_DOORSPIN(0); while (vsync_cnt < GetSystemVcnt() - 1) {} RE4DC_DOORSPIN(1); }
            Render_swap();
            PPCSync();
#if RE4DC_PACE_CATCHUP
            // The anchor clock (29.97 ticks/s) replaces the per-iteration wait while pacing.
            if (!re4dc_pace_end())
#endif
            { WC24_WAIT() RE4DC_DOORSPIN(0); while (vsync_cnt < GetSystemVcnt()) {} RE4DC_DOORSPIN(1); }
            vsync_cnt = 0;
            systemVSyncPost();
            BitOff(pG->System_flg, 0x10000000);
            ProcessTickGet(0, "PROCESS TOTAL");
#if defined(RE4DC_TICK_LOG) && RE4DC_TICK_LOG
            ProcessTickLog();  // GAME_TICK_LOG: per-subsystem timing line every N frames
#endif
            MWC("end");
            ret = systemResetCheck(); WC24_END() DSA24_END() DFA26_END()
#if defined(RE4DC_FALLBACK_AUDIT29) && RE4DC_FALLBACK_AUDIT29
            re4dc::fa29::end_tick();
#endif
#line 243
            if (ret == 1) {
                goto RESTART;
            }
        }
    }
#line 181 "D:/Bio4/Prog/main.cpp"
    OSPanic(__FILE__, __LINE__, "End of biohazard4");
    return 0;
}

// Hook after the vsync wait; empty.
void systemVSyncPost()
{
}

// VI post-retrace callback: counts vsyncs, resumes the interrupt task scheduler once the frame's
// vsync count is reached, and checks for a hang.
void postVSyncCallback()
{
    vsync_cnt++; RE4DC_TAIL_VB();
    if (vsync_cnt >= GetSystemVcnt()) {
        iTaskSuspend();
    }
    if (!(pG->System_flg & 0x20000000)) {
        haltExecCheck();
    }
}

// Halts the game (write to 0x11111111) when no frame was presented for 3600 vsyncs and no
// debugger is attached (hang detector).
void haltExecCheck()
{
    int dbg = DBIsDebuggerPresent();
    if (dbg == 0 && vsync_cnt > 3599) {
#line 548 "D:/Bio4/Prog/main.cpp"
        HALT();
    }
}

// Once at boot: clears the global work, OS/font/language, dev-mode host file system, exception
// handler, VI (black), DVD, memory card, performance counters, heaps, task scheduler, screen
// (Render_init), lights, RNG, OT, sound, Sofdec, id system (0x80 units), log, debug module, DVD
// size table and messages.
void systemStartInit()
{
    memclr_asm(pG, sizeof(GlobalWork));
    OSInit();
    setLanguage();
    RomFontSetting();
    if (OSGetConsoleType() & 0xF0000000) {
        pG->dev_mode = 1;
    }
    if (pG->dev_mode == 1) {
        InitFile();
        if (file_path("d:\\bio4") == 0) {
            file_path("c:/");
        }
    }
    ExceptionInit();
    OSInitAlarm();
    VIInit();
    systemVISetBlack(1);
    LCEnable();
    VIWaitForRetrace();
    VISetPostRetraceCallback(postVSyncCallback);
    Dvd.Init();
    CardInit();
#if defined(__PPC__)
    asm("li 3, 4\n"
        "oris 3, 3, 4\n"
        "mtspr 914, 3\n"
        "li 3, 5\n"
        "oris 3, 3, 5\n"
        "mtspr 915, 3\n"
        "li 3, 6\n"
        "oris 3, 3, 6\n"
        "mtspr 916, 3\n"
        "li 3, 7\n"
        "oris 3, 3, 7\n"
        "mtspr 917, 3"
        :
        :
        : "r3");
#endif
    SystemMemInit();
    if (pG->dev_mode == 1) {
        CardDbgCacheSet();
    }
    TaskSchedulerInit();
    systemScreenInit();
    Render_init();
    LightSetInit();
    RndInit(0xD37);
    InitOt();
    SndInit();
    SofdecInit();
    IdSys.gameInit(0x80);
    IdTexGameInit();
    EprintfInit();
    LogInit();
    init_dbmodule();
    Dvd.SizeTableRead();
    cMes.init();
}

// At boot and after every soft reset: pad, clears the game part of the global work, heap 1
// (game), the OT/fade/cinescope/id/message/data cache/temp buffers, room inits of every manager,
// filters, cloth, cockpit, room data, tex render, item/etc models, events, camera, view, sound,
// background colour, config, brightness from the reset-keep block, debug/roomInfo.dat, log mode.
void systemRestartInit()
{
    int i;
    int ret;

    PadInit();
    memclr_asm(&pG->Rno0, sizeof(GlobalWork) - 0x20);
    MemReplaceHeap(0, 1);
    MemSetCurrentHeap(1);
    systemWorkInit();
    InitOt();
    FadeInit();
    CinescoInit();
    IdSys.roomInit();
    {
        MessageControl* mes = &cMes;
        for (i = 0; i < 16; i++) {
            mes->Delete(i);
        }
    }
    DC.init();
    AllocDrawTmpBuf();
    EmMgr.roomInit();
    ObjMgr.roomInit();
    LightMgr.init(0);
    EspInit();
    RoomTexInit();
    EspgenInit();
    CtrlMgr.roomInit();
    ShadowInit();
    FilterInit();
    ClothInit();
    Cckpt.gameInit();
    RoomData.init();
    TexRenderMgrInit();
    ItemModelInit();
    EtcModelInit();
    EvtMgr.init();
    CameraGameInit();
    View.gameInit(&pG->Cam);
    SndInit2();
    bio4_GXSetCopyClear(g_sysBgColor, 0xFFFFFF);
    GXCopyDisp(pCurrent_buff, 1);
    ConfigSet();
    if (DBIsDebuggerPresent() == 0) {
        BitOff(pG->System_flg, 0x20000);
        BitOff(pG->System_flg, 0x10000);
    }
    if (pRK->brightness == 0) {
        U8Set(pRK->brightness, 0x40);
    }
    U8Set(pSys->brightness, pRK->brightness);
#line 752 "D:/Bio4/Prog/main.cpp"
    ret = DvdReadN("debug/roomInfo.dat", 0, 0, 0, 0, 5, __FILE__, __LINE__);
    if (Dvd.ReadCheck(ret, 0, 0, &roomInfoAddr) < 0) {
        roomInfoAddr = 0;
    }
    pLog->modeSet(200, 0, 150, 4);
    SelfScreenShotInit();
}

// Default projection constants (ZNEAR 100, ZFAR 1,000,000, 640x480 ortho), 2 vsyncs per frame,
// Screen = the render mode size and default brightness.
static void systemScreenInit()
{
    GXRenderModeObj* rm = &Rmode;

    ZNEAR = 100.0f;
    ZFAR = 1000000.0f;
    ORTHO_T = 240.0f;
    ORTHO_B = -240.0f;
    ORTHO_L = -320.0f;
    ORTHO_R = 320.0f;
    SetSystemVcnt(2);
    Screen.x = 0.0f;
    Screen.y = 0.0f;
    Screen.width = (f32) rm->fbWidth;
    Screen.height = (f32) rm->efbHeight;
    U8Set(pSys->brightness, 0x40);
    OSReport("width = %d\n", rm->fbWidth);
    OSReport("height = %d\n", rm->efbHeight);
}

// Default global state: debug mode, start room r120 (Part 0), Leon, game mode 5, costumes 0,
// user name buffer and language 1.
void systemWorkInit()
{
    systemScreenInit();
    S8Set(pG->debug_mode, 1);
    S8Set(pG->debug_disp, -1);
    U16Set(pG->room_id, 0x120);
    U16Set(pG->next_room, pG->room_id);
    U8Set(pG->pl_type, 0);
    U8Set(pG->game_mode, 5);
    U8Set(pG->game_costume, 0);
    U8Set(pG->pl_costume, 0);
#line 823 "D:/Bio4/Prog/main.cpp"
    pUser_name = (char*) mem_calloc(0x40, __FILE__, __LINE__, 1, 13);
    U8Set(pSys->language, 1);
    U8Set(pSys->region, 1);
    U8Set(pG->language, 1);
}

// Frames per game update in vsyncs (1 = 60 Hz, 2 = 30 Hz).
void SetSystemVcnt(int vcnt)
{
    if (vcnt > 0) {
        system_vcnt = vcnt;
    } else {
        system_vcnt = 1;
    }
}

// Current vsyncs per frame.
int GetSystemVcnt()
{
    return system_vcnt;
}

// Reset button handling: on release sets System_flg 0x8000 and, when the game allows it (no 0x200
// lock), performs the hard reset (systemHardReset + OSResetSystem). Returns 1 when resetting.
int checkHardReset()
{
    static u8 reset_check = 0;

    if (reset_check == 0) {
        if (OSGetResetButtonState() == 1) {
            reset_check = 1;
        }
    } else {
        if (OSGetResetButtonState() == 0) {
            reset_check = 0;
            pG->System_flg |= 0x8000;
        }
    }
    if (pG->System_flg & 0x8000) {
        if (!(pG->System_flg & 0x200)) {
            systemHardReset();
            PADRecalibrate(0xF0000000);
            OSResetSystem(0, 0, 0);
            return 1;
        }
    }
    return 0;
}

// End of frame: the soft-reset combo (B+X+START held 30 frames) sets 0x4000000; then hard reset
// check, and a pending soft reset (unless locked by 0x200) runs systemSoftReset and returns 1.
int systemResetCheck()
{
    static u8 Soft_reset_cnt = 0;

    if ((Joy[0].on & 0x1600) == 0x1600) {
        Soft_reset_cnt += GetSystemVcnt();
        if (Soft_reset_cnt > 30) {
            if (pG->dev_mode == 1) {
                pG->System_flg |= 0x4000000;
            } else {
                pG->System_flg |= 0x8000;
            }
        }
    } else {
        Soft_reset_cnt = 0;
    }
    checkHardReset();
    if (!(pG->System_flg & 0x8000)) {
        if (pG->System_flg & 0x4000000) {
            if (!(pG->System_flg & 0x200)) {
                systemSoftReset();
                return 1;
            }
        }
    }
    return 0;
}

// Shared reset work: closes the sub screen, clears tasks, releases enemy/player/weapon/room
// modules, and saves system flags/language/unlock/mercenaries/card state into the reset-keep block.
void systemResetCommon()
{
    int i;

    SubScreenExitCore(&SubScreenWk);
    TaskAllClear();
    EmReadInit();
    ReleasePlData();
#if defined(RE4DC_RESET_MEM_FIX) && RE4DC_RESET_MEM_FIX && defined(RE4DC_ACTOR_PL08_PACK) && RE4DC_ACTOR_PL08_PACK
    re4dc_pl08_pack_forget();  // RESET_MEM_FIX: the pl08 package follows the released archive (coarse_actor_pl08_pack.inc)
#endif
    ReleaseWepData();
    RoomData.stopRelData();
    U32Set(pRK->sys_flags, pSys->flags);
    U8Set(pRK->language, pSys->language);
    U8Set(pRK->region, pSys->region);
    U8Set(pRK->game_language, pG->language);
    U32Set(pRK->sys_unlock_flg, pSys->unlock_flg);
    U32Set(pRK->g_flags_54, pG->System_flg);
    for (i = 0; i < 4; i++) {
        U32SetOfs(pRK->sys_merc_stage, i * 4, pSys->merc_stage[i]);
    }
    for (i = 0; i < 2; i++) {
        U32SetOfs(pRK->sys_merc_rank, i * 4, pSys->merc_rank[i]);
    }
    U32Set(pRK->card_checked, pG->CardStatus >> 31);
    U8Set(pRK->valid, 1);
}

// Blacks the screen and runs the common reset (the OS then reboots).
void systemHardReset()
{
    OSReport("--HARD_RESET START!!\n");
    systemVISetBlack(1);
    VIFlush();
    VIWaitForRetrace();
    systemResetCommon();
    OSReport("--HARD_RESET END!!\n");
}

#if defined(RE4DC_GAME) && !defined(__PPC__) && RE4DC_RESET_RETIRE_BEFORE_HEAPS
extern "C" void re4dc_room_leave();
extern "C" void re4dc_motion_retire_all();
extern "C" void re4dc_effect_retire_room();
extern "C" void re4dc_ui_retire_room();
#endif
// Blacks the screen, cancels DVD/ARAM transfers, resets sound, debug allocations and all heaps,
// runs the common reset and re-inits the ROM font (the frame loop then restarts).
void systemSoftReset()
{
    OSReport("--SOFT_RESET START!!\n");
    systemVISetBlack(1);
    VIFlush();
    VIWaitForRetrace();
    GXDrawDone();
    Dvd.ReadCancelAll();
    Aram.DmaCancelAll();
    SndSoftReset();
    DbmenuModuleInit();
#if defined(RE4DC_GAME) && !defined(__PPC__) && RE4DC_RESET_RETIRE_BEFORE_HEAPS
    // Restore suspended storage and stop its producers before native retirement.
    // The common UI/task calls below are idempotent after this prephase.
    SubScreenExitCore(&SubScreenWk);
    TaskAllClear();
    re4dc_room_leave();
    // Preserve per-module cleanup order while all source heaps are still alive.
    // The unconditional trio also covers a reset without an active Room4 owner.
    systemResetCommon();
    re4dc_motion_retire_all();
    re4dc_effect_retire_room();
    re4dc_ui_retire_room();
#endif
    ResetDebugAlloc();
    MemClearAllHeap();
    SndSystemReset();
#if !defined(RE4DC_GAME) || defined(__PPC__) || !RE4DC_RESET_RETIRE_BEFORE_HEAPS
    systemResetCommon();
#endif
    RomFontSetting();
    pG->IsMessageInit = 0;
#if defined(RE4DC_WARP_AFTER_RESET) && RE4DC_WARP_AFTER_RESET
    re4dc_warp_soft_reset();  // test rig (WARP_AFTER_RESET=1): an after_reset warp.txt warps from the next title
#endif
    OSReport("--SOFT_RESET END!!\n");
}

// Fixed language 1 / region 1 for this build.
void setLanguage()
{
    U8Set(pSys->language, 1);
    U8Set(pSys->region, pSys->language);
    U8Set(pG->language, pSys->language);
}
