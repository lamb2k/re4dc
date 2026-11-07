// game/title: title screen task — logos, demo movies, main menu, omake (Ada / Mercenaries) select and
// the debug start menu (D:/Bio4/Prog/title.cpp).
#include "types.h"
#include "global.h"
#include "map_obj.h"
#include "light.h"
#include "widget.h"
#include "card.h"
#include "atari.h"
#include "sofdec.h"
#include "id_sys.h"
#include "fade.h"
#include "dvd.h"
#include "main_mem.h"
#include "main_sub.h"
#include "main.h"
#include "pad.h"
#include "joy.h"
#include "scheduler.h"
#include "snd.h"
#include "mes.h"
#include "view.h"
#include "game.h"
#include "item.h"
#include "read.h"
#include "option.h"
#include "mercenaries.h"
#include "room_jmp.h"
#include "stage.h"
#include "sce.h"
#include "pl_sub.h"
#include "eprintf.h"
#include "title.h"
#if !defined(__PPC__)
#include "re4dc_platform.h"
#endif

extern "C" void OSReport(const char* fmt, ...);
extern "C" void* memcpy(void* dst, const void* src, unsigned int n);

#define ID_TITLE 0x28
#define ID_MENU 0x29
#define ID_OMAKE 0x2A
#define ID_OMAKE_BG 0x2B
#define ID_OPTION 0x2C

#define KEY_A 0x80000000
#define KEY_B 0x40000000
#define KEY_START 0x1000
#define KEY_UP 0x01000000
#define KEY_DOWN 0x02000000
#define KEY_RIGHT 0x04000000
#define KEY_LEFT 0x08000000

// Reference setters: a store through a scalar reference is not a struct-member MEM, so the
// following pG load stays below it (see global.h FSet).
static inline void ISet(int& d, int v)
{
    d = v;
}
// Store through a reference (matching helper).
#line 58
static inline void CSet(s8& d, s8 v)
{
    d = v;
}
// Store through a reference (matching helper).
#line 62
static inline void BSet(u8& d, u8 v)
{
    d = v;
}

// Mercenaries character unlock bits live in pSys->unlock_flg (bit numbers from the charBit table).
static inline u32 omkFlagChk(u32 no)
{
    u32* tbl = &pSys->unlock_flg;
    return tbl[no >> 5] & (0x80000000 >> (no & 0x1F));
}

// stage_prev/room_prev written as one u16 through a plain pointer (aliases pG like G_ROOM_ID).
#if defined(__PPC__)
#define G_ROOM_ID_PREV (*(u16*) &pG->stage_prev)
#else
#define G_ROOM_ID_PREV (pG->room_id_prev)
#endif

// Sub-file of the core archive (pG->pArc): `ofs + (u32) arc` (integer arithmetic, ofs first).
#define G_ARC_PTR(field) ((void*) (pG->pArc->field + (u32) pG->pArc))

// Fade colours: word constants passed by address (see sscrn.cpp).
union FadeColor {
    GXColor c;
    u32 w;
};


// Read-error report of the original: the condition never holds, only the strings survive.
#define READ_ERROR(msg)                                           \
    if (0) {                                                      \
        OSReport(msg);                                            \
        OSReport("HALT %s(%d)\n", __FILE__, __LINE__);            \
    }

#if !defined(__PPC__) && RE4DC_DBG_WARP
extern "C" int re4dc_warp_title(void);
extern "C" int re4dc_warp_title_exit(void);
extern "C" void re4dc_warp_next_pos(void);
#endif
void titleInit(TitleWork* w);
void titleWait(TitleWork* w);
void titleNintendo(TitleWork* w);
void titleWarning(TitleWork* w);
void titleLogo(TitleWork* w);
void titleMain(TitleWork* w);
void titleSub(TitleWork* w);
void titleExit(TitleWork* w);
void titleSet(TitleWork* w, int time);
void titleMenuInit(TitleWork* w);
int titleMenuSelect(TitleWork* w);
void titleLevelInit(TitleWork* w);
int titleLevelSelect(TitleWork* w);
void titleLoop(TitleWork* w);
void id_color_copy(int src, int dst, u8 type);
void stageSelectInit(TitleWork* w);
int stageSelect(TitleWork* w);
void titleDebugMenu(TitleWork* w);

int TTL_CANCEL_WARNING = 45;
int TTL_CANCEL_CAPCOM = 120;
int TTL_CANCEL_CRI = 245;
static int TTL_CANCEL_DOLBY = 345;

// The title screen task (scheduler slot after boot): allocates the save buffer, item manager, the
// core / option data, then runs the title state machine (TitleWork Rno0) every frame until
// titleExit chains into GameTask.
void Title_task()
{
    static void (*titleFuncTbl[8])(TitleWork*) = {
        titleInit, titleWait, titleNintendo, titleWarning, titleLogo, titleMain, titleSub, titleExit,
    };
    TitleWork* w;

    pSaveData = GameSave.alloc();
    ItemMgr.init();
    CoreDataRead();
    OptionDataRead();
#line 114 "D:/Bio4/Prog/title.cpp"
    w = (TitleWork*) MEM_CALLOC(sizeof(TitleWork), 1, 13);
    for (;;) {
#if !defined(__PPC__) && RE4DC_DBG_WARP
        // Test warp rig (dbgwarp_bridge.cpp): once the title data is loaded, straight to titleExit.
        if (w->Rno0 >= 2 && w->Rno0 <= 6 && re4dc_warp_title()) {
            w->Rno0 = 7;
            w->Rno1 = 0;
        }
#endif
        titleFuncTbl[w->Rno0](w);
#if !defined(__PPC__)
        re4dc_fixture_state("title", w->Rno0, w->Rno1);
#endif
        TaskSleep(1);
    }
}

// State 0: 640 x 448 screen, starts reading the title sound bank, id buffers; Status_flg[2] 0x8000
// = title mode (movies keep the heap).
void titleInit(TitleWork* w)
{
    int req;

    ScreenReSize(640, 448);
#line 147 "D:/Bio4/Prog/title.cpp"
    req = DvdReadN("SS/cmn/title.snd", 0, 0, 0, 0, 0x8000, __FILE__, __LINE__);
    READ_ERROR("title.snd read error!!");
    // The work fields are written through the reference setters (the order and the ISet/FSet
    // forms decide the store schedule; found by brute force).
    ISet(w->req, req);
    w->Rno0 = 1;
    w->xC = 0;
    w->Rno1 = 0;
    ISet(w->scroll, 0);
    FSet(w->scroll_add, 1.5f);
    pG->Status_flg[2] |= 0x8000;
    IdAllocBuffer();
}

#if !defined(__PPC__) && defined(RE4DC_TITLE_ID_DIAG) && RE4DC_TITLE_ID_DIAG
// TITLE_ID_DIAG=1 (test only, #66 bug 6): every 30 calls, one line per live title / menu id unit.
static void titleIdDiag(TitleWork* w, int state)
{
    static unsigned calls;
    if ((calls++ % 30) != 0) return;
    IdUnit* u = IdSys.pUnit;
    for (int i = 0; i < IdSys.m_maxId; i++, u++) {
        if (u->be_flag == 0xFF || (u->classNo != ID_TITLE && u->classNo != ID_MENU)) continue;
        re4dc_log("TIDD st=%d cnt=%d i=%d be=%02x cls=%02x mark=%02x unit=%02x typ=%u par=%02x tex=%02x/%u tf=%02x tr=%u bl=%u col=%d,%d,%d,%d t=%d,%d,%d,%d end=%02x pos=%d,%d sz=%d,%d\n",
            state, w->counter, i, u->be_flag, u->classNo, u->markNo, u->unitNo, u->type, u->parentNo, u->texId, u->texNo,
            u->tex_flag, u->trans_type, u->blend_type, (int) u->col[0], (int) u->col[1], (int) u->col[2], (int) u->col[3],
            (s16) u->timer[0], (s16) u->timer[1], (s16) u->timer[2], (s16) u->timer[3], u->end, (int) u->pos.x, (int) u->pos.y,
            (int) u->sizeX, (int) u->size_H);
        static unsigned char keys_done[256];
        Hermite1* h = u->curve[2];
        if (h && !keys_done[u->unitNo]) {
            keys_done[u->unitNo] = 1;
            for (int k = 0; k < h->num && k < 12; k++)
                re4dc_log("TIDK unit=%02x num=%d k=%d t=%d v=%d out=%d in=%d col0a=%u col1=%08x\n", u->unitNo, (int) h->num, k,
                          (int) h->key[k].t, (int) (h->key[k].v * 100.0f), (int) (h->key[k].out * 100.0f), (int) (h->key[k].in * 100.0f),
                          u->col0[3], *(u32*) u->col1);
        }
    }
}
#define TITLE_ID_DIAG_CALL(w, st) titleIdDiag((w), (st))
#else
#define TITLE_ID_DIAG_CALL(w, st)
#endif

// Shows the title logo / background id layout (the alternate one once everything is unlocked,
// unlock_flg 0x40000000) at animation time `time`.
void titleSet(TitleWork* w, int time)
{
    IdSys.kill(0xFF, ID_TITLE);
    if (!(pSys->unlock_flg & 0x40000000)) {
        IdSys.set(TITLE_ARC_PTR(w->pDat, 6), 0xFF, ID_TITLE, 0x13, 6, 0);
    } else {
        IdSys.set(TITLE_ARC_PTR(w->pDat, 7), 0xFF, ID_TITLE, 0x13, 6, 0);
    }
    IdSys.setTimeS(IdSys.unitPtr(0, ID_TITLE), (s16) time);
}

// State 1: waits for the memory card check and the sound bank, loads "SS/<lang>/title.dat" and its
// textures, then goes to the Nintendo logo — or, when the title was already shown (pRK) straight
// to the main menu (or the omake menu after an Ada / Mercenaries session).
void titleWait(TitleWork* w)
{
    static char title_dat[] = "SS/___/title.dat";

    switch (w->Rno1) {
    case 0:
        if (CardCheckDone() == 1) {
            int stat = Dvd.ReadCheck(w->req, 0, 0, 0);
            if (stat == 1) {
                FadeKill(0);
                systemVISetBlack(0);
                w->Rno1 = 1;
            }
        }
        break;
    case 1:
        setLangExt3(title_dat + 3);
#line 210 "D:/Bio4/Prog/title.cpp"
        w->req = DvdReadN(title_dat, 0, 0, 0, 0, 4, __FILE__, __LINE__);
        READ_ERROR("%s read error!!");
        w->Rno1 = 2;
        break;
    case 2: {
        int stat = Dvd.ReadCheck(w->req, 0, 0, (void**) &w->pDat);
        if (stat == 1) {
            pG->nPrim = 0x20000;
            primInit();
            IdTexRoomInit();
            IdSys.roomInit();
            IdTexDataLoad(TITLE_ARC_PTR(w->pDat, 4), TEX_OWNER_ID_TITLE);
            {
                register u8 z PPC_REG("r11");  // COMPILER-DIFF: #13 (REG_EQUIV zero reloaded into r11)
                z = 0;
                CSet(w->Rno0, 2);
                ISet(w->sndFlag, 1);
                w->Rno1 = z;
                ISet(w->counter, 0);
                ISet(w->dbg_mode, 0);
            }
            if (pRK->title_shown != 0) {
                w->Rno0 = 5;
                w->counter = 585;
                titleSet(w, 585);
                if ((s32) pG->System_flg < 0 || (pG->System_flg & 0x40000000)) {
                    w->saveStep = w->Rno1;
                    w->saveSub = w->Rno2;
                    w->saveX3 = w->Rno3;
                    w->saveCnt = w->counter;
                    w->Rno0 = 6;
                    w->Rno1 = 0;
                }
            }
        }
        {
            Camera* cam = &pG->Cam;
            C_MTXPerspective(cam->ProjMat, cam->param.fovy, 4.0f / 3.0f, ZNEAR, ZFAR);
            cam->dist = PSVECDistance(&cam->param.pos, &cam->param.at);
            C_MTXLookAt(cam->v_mat, &cam->param.pos, &cam->up, &cam->param.at);
        }
        break;
    }
    }
}

// State 2: fades the Nintendo logo in and out (a second pad skips to the menu).
void titleNintendo(TitleWork* w)
{
    static int wait_cnt = 0;
    FadeColor c0;
    FadeColor c1;

    if (PadCheckStatus(&Joy[1]) == 1) {
        FadeKill(0);
        w->Rno0 = 5;
        w->Rno1 = 0;
        w->counter = 585;
        titleSet(w, 585);
        return;
    }
    switch (w->Rno1) {
    case 0:
        IdSys.set(TITLE_ARC_PTR(w->pDat, 0xB), 0xFF, ID_TITLE, 0x13, 6, 0);
        c0.w = 0x000000FF;
        c1.w = 0x00000000;
        FadeSet(0x80000000, &c0.c, &c1.c, 15, 0, 0);
        wait_cnt = 0;
        w->Rno1++;
        break;
    case 1:
        if (wait_cnt++ > 60) {
            c0.w = 0x00000000;
            c1.w = 0x000000FF;
            FadeSet(0, &c0.c, &c1.c, 15, 0, 0);
            w->Rno1++;
        }
        break;
    case 2:
        if ((Fade[0].flags & 1) == 0) {
            FadeKill(0);
            w->Rno1 = 0;
            w->Rno0 = 3;
            titleSet(w, w->counter);
        }
        break;
    }
}

// State 3: the health warning for 105 frames; START (after 45) fades it early.
void titleWarning(TitleWork* w)
{
    IdUnit* u = IdSys.unitPtr(0, ID_TITLE);
    FadeColor c0;
    FadeColor c1;

    w->counter++;
    if (PadCheckStatus(&Joy[1]) == 1) {
        w->counter = 585;
        w->Rno0 = 5;
        w->Rno1 = 0;
        IdSys.setTimeS(u, (s16) w->counter);
        return;
    }
    switch (w->Rno1) {
    case 0:
        if (w->counter > 105) {
            w->Rno1 = 0;
            w->Rno0 = 4;
        } else if (w->counter > TTL_CANCEL_WARNING) {
            if (Key.trg & KEY_START) {
                c0.w = 0x00000000;
                c1.w = 0x000000FF;
                FadeSet(0, &c0.c, &c1.c, 15, 0, 0);
                w->Rno1 = 1;
            }
        }
        break;
    case 1:
        if ((Fade[0].flags & 1) == 0) {
            FadeKill(0);
            w->counter = 105;
            w->Rno1 = 0;
            w->Rno0 = 4;
            IdSys.setTimeS(u, (s16) w->counter);
        }
        break;
    }
}

// State 4: the Capcom (to 230), CRI (330) and Dolby (585) logos on the id timeline, each
// skippable with START after its TTL_CANCEL_* frame; the title BGM starts at LOGO_CALL_FRAME.
void titleLogo(TitleWork* w)
{
    IdUnit* u = IdSys.unitPtr(0, ID_TITLE);
    static u32 LOGO_CALL_FRAME = TTL_CANCEL_DOLBY;
    FadeColor c0;
    FadeColor c1;

    w->counter++;
    TITLE_ID_DIAG_CALL(w, 4);
#if !defined(__PPC__) && defined(RE4DC_TITLE_ID_DIAG) && RE4DC_TITLE_ID_DIAG
    if (Key.on || Key.trg)
        re4dc_log("TKEY rno=%d/%d cnt=%d on=%08x trg=%08x sys=%08x\n", w->Rno0, w->Rno1, w->counter,
                  (unsigned) Key.on, (unsigned) Key.trg, (unsigned) pG->System_flg);
#endif
    switch (w->Rno1) {
    case 0:
        if (w->counter > 230) {
            w->Rno1 = 2;
        } else if (w->counter > TTL_CANCEL_CAPCOM) {
            if (Key.trg & KEY_START) {
                c0.w = 0x00000000;
                c1.w = 0x000000FF;
                FadeSet(0, &c0.c, &c1.c, 15, 0, 0);
                w->Rno1 = 1;
            }
        }
        break;
    case 1:
        if ((Fade[0].flags & 1) == 0) {
            FadeKill(0);
            w->counter = 230;
            w->Rno1 = 2;
            IdSys.setTimeS(u, (s16) w->counter);
        }
        break;
    case 2:
        if (w->counter > 330) {
            w->Rno1 = 4;
        } else if (w->counter > TTL_CANCEL_CRI) {
            if (Key.trg & KEY_START) {
                c0.w = 0x00000000;
                c1.w = 0x000000FF;
                FadeSet(0, &c0.c, &c1.c, 15, 0, 0);
                w->Rno1 = 3;
            }
        }
        break;
    case 3:
        if ((Fade[0].flags & 1) == 0) {
            FadeKill(0);
            w->counter = 330;
            w->Rno1 = 4;
            IdSys.setTimeS(u, (s16) w->counter);
        }
        break;
    case 4:
        if (w->counter > 585) {
            w->Rno1 = 6;
        } else if (w->counter > TTL_CANCEL_DOLBY) {
            if (Key.trg & KEY_START) {
                c0.w = 0x00000000;
                c1.w = 0x000000FF;
                FadeSet(0, &c0.c, &c1.c, 15, 0, 0);
                w->Rno1 = 5;
            }
        }
        break;
    case 5:
        if ((Fade[0].flags & 1) == 0) {
            FadeKill(0);
            w->counter = 585;
            w->Rno1 = 6;
            IdSys.setTimeS(u, (s16) w->counter);
        }
        break;
    case 6:
        w->Rno0 = 5;
        w->Rno1 = 0;
        break;
    }
    if ((u32) w->counter > LOGO_CALL_FRAME && w->sndFlag == 1) {
        SndCall(6, 4, 0, 0, 0, 0);
        w->sndFlag = 0;
    }
}

// Loads the main menu id layout: 5 entries (new game, Ada, Mercenaries, load, options) once all
// is unlocked, else 3 (new game, load, options); cursor on "load".
void titleMenuInit(TitleWork* w)
{
    IdSys.kill(0xFF, ID_MENU);
    if (pSys->unlock_flg & 0x40000000) {
        IdSys.set(TITLE_ARC_PTR(w->pDat, 9), 0xFF, ID_MENU, 0x13, 5, 0);
        w->menu_num = 5;
        w->menu[0] = IdSys.unitPtr(1, ID_MENU);
        w->menu[1] = IdSys.unitPtr(7, ID_MENU);
        w->menu[2] = IdSys.unitPtr(9, ID_MENU);
        w->menu[3] = IdSys.unitPtr(3, ID_MENU);
        w->menu[4] = IdSys.unitPtr(5, ID_MENU);
        w->cursor = 3;
    } else {
        IdSys.set(TITLE_ARC_PTR(w->pDat, 8), 0xFF, ID_MENU, 0x13, 5, 0);
        w->menu_num = 3;
        w->menu[0] = IdSys.unitPtr(1, ID_MENU);
        w->menu[1] = IdSys.unitPtr(5, ID_MENU);
        w->menu[2] = IdSys.unitPtr(3, ID_MENU);
        w->cursor = 1;
    }
    w->scroll = 0;
    w->scroll_add = 1.5f;
}

// Cursor movement shared by the main menu and the level select.
#define TITLE_MENU_MOVE(w)                                                                 \
    {                                                                                      \
        int old = (w)->cursor;                                                             \
        if (Key.trg & KEY_UP) {                                                            \
            (w)->cursor = old - 1;                                                         \
        }                                                                                  \
        if (Key.trg & KEY_DOWN) {                                                          \
            (w)->cursor++;                                                                 \
        }                                                                                  \
        (w)->cursor = (w)->cursor < 0 ? 0 : ((w)->cursor > (w)->menu_num - 1 ? (w)->menu_num - 1 : (w)->cursor); \
        if (old != (w)->cursor) {                                                          \
            SndCall(0, 10, 0, 0, 0, 0);                                                    \
        }                                                                                  \
        {                                                                                  \
            int i;                                                                         \
            for (i = 0; i < (w)->menu_num; i++) {                                           \
                if (i == (w)->cursor) {                                                    \
                    (w)->menu[i]->be_flag |= 8;                                              \
                } else {                                                                   \
                    (w)->menu[i]->be_flag &= ~8;                                             \
                }                                                                          \
            }                                                                              \
        }                                                                                  \
        if ((w)->menu_num > 1 && (Key.trg & (KEY_UP | KEY_DOWN))) {                        \
            int i;                                                                         \
            for (i = 0; i < (w)->menu_num; i++) {                                           \
                IdUnit* u = (w)->menu[i];                                                  \
                u->timer[3] = 0;                                                           \
                u->timer[1] = 0;                                                           \
                u->timer[2] = 0;                                                           \
                u->timer[0] = 0;                                                           \
            }                                                                              \
        }                                                                                  \
    }

// A on the main menu: returns 1 new game (3-entry menu), 6 new game (5-entry: level select first),
// 2 Assignment Ada, 3 Mercenaries, 4 load, 5 options; 0 = nothing chosen.
int titleMenuSelect(TitleWork* w)
{
    int ret = 0;

    if (Key.trg & KEY_A) {
        if (pSys->unlock_flg & 0x40000000) {
            switch (w->cursor) {
            case 0:
                ret = 6;
                break;
            case 1:
                ret = 2;
                break;
            case 2:
                ret = 3;
                break;
            case 3:
                ret = 4;
                break;
            case 4:
                ret = 5;
                break;
            }
        } else {
            switch (w->cursor) {
            case 0:
                ret = 1;
                break;
            case 1:
                ret = 4;
                break;
            case 2:
                ret = 5;
                break;
            }
        }
        return ret;
    }
    TITLE_MENU_MOVE(w);
    return 0;
}

// Loads the difficulty menu (easy / normal, plus professional when unlocked... 2 or 3 entries).
void titleLevelInit(TitleWork* w)
{
    IdSys.kill(0xFF, ID_MENU);
    IdSys.set(TITLE_ARC_PTR(w->pDat, 0xA), 0xFF, ID_MENU, 0x13, 5, 0);
    w->menu[0] = IdSys.unitPtr(1, ID_MENU);
    w->menu[1] = IdSys.unitPtr(3, ID_MENU);
    w->menu[2] = IdSys.unitPtr(5, ID_MENU);
    if (pSys->language == 1) {
        IdSys.unitPtr(5, ID_MENU)->be_flag &= ~8;
        IdSys.unitPtr(6, ID_MENU)->be_flag &= ~8;
        w->menu_num = 2;
    } else {
        w->menu_num = 3;
    }
    w->cursor = 1;
}

// A on the difficulty menu sets pG->Game_level (by cursor and language); returns 1 when chosen.
int titleLevelSelect(TitleWork* w)
{
    if (Key.trg & KEY_A) {
        if (pSys->language == 0) {
            switch (w->cursor) {
            case 0:
                pG->game_mode = 6;
                break;
            case 1:
            default:
                pG->game_mode = 5;
                break;
            case 2:
                pG->game_mode = 3;
                break;
            }
        } else if (pSys->language == 1) {
            if (w->cursor == 0) {
                pG->game_mode = 6;
            } else {
                pG->game_mode = 5;
            }
        } else {
            switch (w->cursor) {
            case 0:
                pG->game_mode = 6;
                break;
            case 1:
            default:
                pG->game_mode = 5;
                break;
            case 2:
                pG->game_mode = 3;
                break;
            }
        }
        return 1;
    }
    TITLE_MENU_MOVE(w);
    return 0;
}

// State 5, the main menu: Rno1 0 menu setup, 1 selection (new game -> the fade-out into the game
// (Rno1 3), Ada / Mercenaries -> the omake screens (state 6) with System_flg bit31 / 0x40000000,
// load -> the card (7), options -> the option screen (4)), 2 difficulty select, 5 / 6 the demo
// movies after 600 idle frames (e3_jpn.sfd, then demo0 / demo1 alternating), 8 the "no save"
// message. The background scrolls (titleLoop) meanwhile.
#if !defined(__PPC__) && RE4DC_QUALITY
// D367 quality picker (port/dreamcast/game/quality_picker.cpp): once per boot, before the menu.
extern "C" int re4dc_quality_picker_wanted(void);
extern "C" void re4dc_quality_picker_open(void);
extern "C" int re4dc_quality_picker_move(void);
extern "C" void re4dc_quality_freeze(const char* where);
#endif

void titleMain(TitleWork* w)
{
    static int demo_loop_cnt = 0;
    FadeColor c0;
    FadeColor c1;

    pRK->title_shown = 1;
    TITLE_ID_DIAG_CALL(w, 5);
#if !defined(__PPC__) && defined(RE4DC_TITLE_ID_DIAG) && RE4DC_TITLE_ID_DIAG
    if (Key.on || Key.trg)
        re4dc_log("TKEY rno=%d/%d cnt=%d on=%08x trg=%08x sys=%08x\n", w->Rno0, w->Rno1, w->counter,
                  (unsigned) Key.on, (unsigned) Key.trg, (unsigned) pG->System_flg);
#endif
    if (!(pG->System_flg & 0x100) && (pSys->unlock_flg & 0x40000000)) {
        titleLoop(w);
    }
    switch (w->Rno1) {
    case 0:
#if !defined(__PPC__) && RE4DC_QUALITY
        if (re4dc_quality_picker_wanted()) {
            re4dc_quality_picker_open();
            w->Rno1 = 9;
            break;
        }
#endif
        titleMenuInit(w);
        w->Rno1 = 1;
        demo_loop_cnt = 600;
        break;
#if !defined(__PPC__) && RE4DC_QUALITY
    case 9:
        if (re4dc_quality_picker_move()) {
            titleMenuInit(w);
            w->Rno1 = 1;
            demo_loop_cnt = 600;
        }
        break;
#endif
    case 1: {
        int sel = titleMenuSelect(w);
        BitOff(pG->System_flg, 0x80000000);
        BitOff(pG->System_flg, 0x40000000);
        switch (sel) {
        case 1:
            Snd.room_ok = 1;
            if (pSys->language == 0) {
                w->se_id = SndCall(6, 0, 0, 0, 0, 0);
            } else {
                w->se_id = SndCall(6, 2, 0, 0, 0, 0);
            }
            VibSetData((VibDataTbl*) G_ARC_PTR(ofs_1C), 0x10, 1);
            c0.w = 0x00000000;
            c1.w = 0x000000FF;
            FadeSet(0, &c0.c, &c1.c, 90, 0, 0);
            w->Rno1 = 3;
            break;
        case 6:
            titleLevelInit(w);
            w->Rno1 = 2;
            SndCall(0, 4, 0, 0, 0, 0);
            break;
        case 2:
        case 3:
            switch (sel) {
            case 2:
                pG->System_flg |= 0x80000000;
                break;
            case 3:
                pG->System_flg |= 0x40000000;
                break;
            }
            w->saveStep = w->Rno1;
            w->saveSub = w->Rno2;
            w->saveX3 = w->Rno3;
            w->saveCnt = w->counter;
            w->Rno0 = 6;
            w->Rno1 = 0;
            w->omk_char_no = 0;
            SndCall(0, 4, 0, 0, 0, 0);
            break;
        case 4:
            w->Rno1 = 7;
            SndCall(0, 4, 0, 0, 0, 0);
            break;
        case 5:
            IdTexRelease(TEX_OWNER_ID_TITLE);
            IdSys.kill(0xFF, ID_TITLE);
            IdSys.kill(0xFF, ID_MENU);
            MesData.ptr[2] = (u8*) G_ARC_PTR(ofs_28);
            OptScrn.init(1);
            IdTexDataLoad(G_ARC_PTR(ofs_74), TEX_OWNER_ID_COCKPIT);
            IdTexDataLoad(TITLE_ARC_PTR(w->pDat, 0xC), TEX_OWNER_ID_EVENT);
            IdSys.set(TITLE_ARC_PTR(w->pDat, 0xD), 0xFF, ID_OPTION, 0x13, 5, 0);
            w->saveCnt = w->counter;
            w->Rno1 = 4;
            SndCall(0, 0x33, 0, 0, 0, 0);
            break;
        }
        if (w->Rno1 == 1 && !(pG->System_flg & 8)) {
            if (Key.trg & (KEY_UP | KEY_DOWN)) {
                demo_loop_cnt = 600;
            }
            if (demo_loop_cnt > 0) {
                demo_loop_cnt--;
                if (demo_loop_cnt == 0) {
                    c0.w = 0x00000000;
                    c1.w = 0x000000FF;
                    FadeSet(0, &c0.c, &c1.c, 15, 0, 0);
                    w->Rno2 = 0;
                    w->Rno1 = 6;
                }
            } else {
                demo_loop_cnt = 600;
            }
        }
        break;
    }
    case 2:
        if (Key.trg & KEY_B) {
            titleMenuInit(w);
            w->Rno1 = 1;
        } else if (titleLevelSelect(w) != 0) {
            Snd.room_ok = 1;
            if (pSys->language == 0) {
                w->se_id = SndCall(6, 0, 0, 0, 0, 0);
            } else {
                w->se_id = SndCall(6, 2, 0, 0, 0, 0);
            }
            VibSetData((VibDataTbl*) G_ARC_PTR(ofs_1C), 0x10, 1);
            c0.w = 0x00000000;
            c1.w = 0x000000FF;
            FadeSet(0, &c0.c, &c1.c, 90, 0, 0);
            w->Rno1 = 3;
        }
        break;
    case 3:
        w->Rno0 = 7;
        break;
    case 4:
        if (OptScrn.move() == 1) {
            IdTexRelease(TEX_OWNER_ID_COCKPIT);
            IdTexRelease(TEX_OWNER_ID_EVENT);
            IdSys.kill(0xFF, ID_OPTION);
            OptScrn.quit();
            IdTexDataLoad(TITLE_ARC_PTR(w->pDat, 4), TEX_OWNER_ID_TITLE);
            w->Rno0 = 5;
            w->Rno1 = 0;
            w->cursor = 2;
            w->counter = w->saveCnt;
            titleSet(w, w->saveCnt);
        }
        break;
    case 5:
        switch (w->Rno2) {
        case 0:
            if ((Fade[0].flags & 1) == 0) {
                w->Rno2++;
            }
            break;
        case 1:
            systemVISetBlack(1);
            FadeKill(0);
            ScreenReSize(512, 448);
            Sofdec.Initialize("movie/e3_jpn.sfd", 0);
            w->Rno2++;
            break;
        case 2:
            if (!Sofdec.isPlay()) {
                systemVISetBlack(1);
                ScreenReSize(640, 448);
                systemVISetBlack(0);
                c0.w = 0x000000FF;
                c1.w = 0x00000000;
                FadeSet(0x80000000, &c0.c, &c1.c, 15, 0, 0);
                w->Rno2++;
            }
            break;
        case 3:
            if ((Fade[0].flags & 1) == 0) {
                w->Rno2 = 0;
                w->Rno1 = 1;
            }
            break;
        }
        break;
    case 6:
        switch (w->Rno2) {
        case 0:
            if ((Fade[0].flags & 1) == 0) {
                w->Rno2++;
                w->demo_no = w->demo_no == 0;
            }
            break;
        case 1:
            systemVISetBlack(1);
            FadeKill(0);
            ScreenReSize(512, 448);
            if (w->demo_no) {
                Sofdec.Initialize("movie/demo0.sfd", 0);
            } else {
                Sofdec.Initialize("movie/demo1.sfd", 0);
            }
            w->Rno2++;
            break;
        case 2:
            if (!Sofdec.isPlay()) {
                systemVISetBlack(1);
                ScreenReSize(640, 448);
                systemVISetBlack(0);
                c0.w = 0x000000FF;
                c1.w = 0x00000000;
                FadeSet(0x80000000, &c0.c, &c1.c, 15, 0, 0);
                w->Rno2++;
            }
            break;
        case 3:
            if ((Fade[0].flags & 1) == 0) {
                w->Rno1 = 1;
            }
            break;
        }
        break;
    case 7:
        if (CardLoad() == 1) {
            w->Rno1 = 3;
            pG->System_flg |= 0x100;
        } else {
            pG->System_flg |= 0x04000000;
            return;
        }
        break;
    case 8:
        switch (w->Rno2) {
        case 0: {
            IdUnit* u = IdSys.unitPtr(0, ID_TITLE);
            if (w->counter <= 584) {
                w->counter = 645;
            }
            IdSys.setTimeS(u, (s16) w->counter);
            w->dbg_mode = 1;
            w->Rno2++;
        }
        case 1:
            if (Joy[0].trg & 0x1100) {
                int zero = 0;  // COMPILER-DIFF: #13 (single-use zero set in another block: update_equiv_regs moves the `li` next to the store, it takes r0 after the x3 temp)
                w->Rno0 = 7;
                if ((s32) pG->System_flg < 0 || (pG->System_flg & 0x40000000)) {
                    w->saveSub = w->Rno2;
                    w->saveStep = w->Rno1;
                    w->saveX3 = w->Rno3;
                    w->saveCnt = w->counter;
                    w->Rno0 = 6;
                    w->Rno1 = zero;
                } else {
                    Snd.room_ok = 1;
                    c0.w = 0x00000000;
                    c1.w = 0x000000FF;
                    FadeSet(0, &c0.c, &c1.c, 0, 0, 0);
                }
            }
            titleDebugMenu(w);
            break;
        }
        break;
    }
    if (w->counter > 54000) {
        w->counter = 54000;
    }
}

// The scrolling title background: drifts left at scroll_add, the stick / d-pad take over its
// speed (C-stick up / down changes the layer), wrapping at twice the width.
void titleLoop(TitleWork* w)
{
    static f32 width = 900.0f;
    static f32 zoom_in_limit = 170.0f;
    IdUnit* u;

    IdSys.unitPtr(1, ID_TITLE)->scr.x = width * 0.0f;
    IdSys.unitPtr(2, ID_TITLE)->scr.x = width * 1.0f;
    IdSys.unitPtr(3, ID_TITLE)->scr.x = width * -1.0f;
    IdSys.unitPtr(4, ID_TITLE)->scr.x = width * -2.0f;
    IdSys.unitPtr(5, ID_TITLE)->scr.x = width * 2.0f;
    u = IdSys.unitPtr(6, ID_TITLE);
    if (w->scroll == 0) {
        u->scr.x -= w->scroll_add;
        if (Key.on & (KEY_RIGHT | KEY_LEFT)) {
            w->scroll = 1;
        }
    } else {
        if ((f32) Key.stickX != 0.0f) {
            f32 spd = (f32) Key.stickX / 59.0f * 3.0f;
            u->scr.x -= spd;
            if (__builtin_fabsf((f32) Key.stickX) > 3.0f) {
                w->scroll_add = spd;
            }
        } else {
            u->scr.x -= w->scroll_add;
        }
        if (Key.on & 0x00400000) {
            u->scr.z -= 5.0f;
        }
        if (Key.on & 0x00800000) {
            u->scr.z += 5.0f;
        }
        u->scr.z = u->scr.z < 0.0f ? 0.0f : (u->scr.z > zoom_in_limit ? zoom_in_limit : u->scr.z);
    }
    if (u->scr.x > width * 2.0f) {
        u->scr.x -= width * 3.0f;
    }
    if (u->scr.x < -width) {
        u->scr.x += width * 3.0f;
    }
}

// Copies the colour of id unit `src` to unit `dst`.
void id_color_copy(int src, int dst, u8 type)
{
    IdUnit* s = IdSys.unitPtr(src, type);
    IdUnit* d = IdSys.unitPtr(dst, type);

    d->col0[0] = s->col0[0];
    d->col0[1] = s->col0[1];
    d->col0[2] = s->col0[2];
    d->col0[3] = s->col0[3];
    d->curve[2] = s->curve[2];
}

// State 6, the omake (Ada / Mercenaries) screens: loads "omk_t0/1.dat", the start / back menu
// (Rno1 3-4; a first Mercenaries start also unlocks the base characters), Mercenaries character
// select (6-8, locked characters greyed by unlock_flg bits) and stage select (stageSelect), B goes
// back to the main menu with its saved state (5).
void titleSub(TitleWork* w)
{
    static char omake_dat[] = "SS/___/omk_tX.dat";
    static void* omk_addr = 0;
    static u32 snd_id;
    static int title_snd_wait = 7;
    int charBit[5] = {4, 4, 6, 5, 7};
#define OMK_PTR(no) TITLE_ARC_PTR((TitleArc*) omk_addr, no)

    switch (w->Rno1) {
    case 0:
        if ((s32) pG->System_flg < 0) {
            omake_dat[12] = '0';
        } else if (pG->System_flg & 0x40000000) {
            omake_dat[12] = '1';
        }
        setLangExt3(omake_dat + 3);
        omk_addr = 0;
#line 1157 "D:/Bio4/Prog/title.cpp"
        w->req = DvdReadN(omake_dat, 0, 0, 0, 0, 4, __FILE__, __LINE__);
        if (w->req == 0) {
            break;
        }
        FadeSetW(0, 5, 0, 0);
        w->Rno1++;
        if ((s32) pG->System_flg < 0) {
            snd_id = SndStrReq(0, 60, 0x80000003, 0, 0, 0.0f);
        } else if (pG->System_flg & 0x40000000) {
            snd_id = SndStrReq(0, 55, 0x80000003, 0, 0, 0.0f);
        }
        break;
    case 1:
        if (Dvd.ReadCheck(w->req, &w->omkSize, 0, (void**) &w->pOmk) != 0) {
            omk_addr = w->pOmk;
            w->Rno1++;
        }
        break;
    case 2:
        if ((Fade[0].flags & 1) == 0) {
            w->Rno1++;
        }
        break;
    case 3: {
        FadeSetW(0x80000000, 5, 0, 0);
        IdTexDataLoad(OMK_PTR(4), TEX_OWNER_ID_EVENT);
        IdSys.kill(0xFF, ID_TITLE);
        IdSys.kill(0xFF, ID_MENU);
        IdSys.set(OMK_PTR(5), 0xFF, ID_OMAKE_BG, 0x13, 5, 0);
        IdSys.set(OMK_PTR(6), 0xFF, ID_OMAKE, 0x13, 4, 0);
        if (pG->System_flg & 0x40000000) {
            if (!(pSys->unlock_flg & 0x08000000)) {
                IdSys.unitPtr(4, ID_OMAKE_BG)->be_flag &= ~8;
            }
            if (!(pSys->unlock_flg & 0x02000000)) {
                IdSys.unitPtr(1, ID_OMAKE_BG)->be_flag &= ~8;
            }
            if (!(pSys->unlock_flg & 0x04000000)) {
                IdSys.unitPtr(2, ID_OMAKE_BG)->be_flag &= ~8;
            }
            if (!(pSys->unlock_flg & 0x01000000)) {
                IdSys.unitPtr(3, ID_OMAKE_BG)->be_flag &= ~8;
            }
        }
        w->omk_menu_no = 0;
        w->Rno1++;
        break;
    }
    case 4:
        if (Key.trg & KEY_B) {
            FadeSetW(0, 5, 0, 0);
            w->Rno1++;
            SndCall(0, 5, 0, 0, 0, 0);
            SndStrReq(snd_id, 4, 200, 0);
        } else if (Key.trg & KEY_A) {
            if (w->omk_menu_no == 0) {
                if ((s32) pG->System_flg < 0) {
                    w->Rno0 = 7;
                    FadeSetW(0, 90, 0, 0);
                    pG->pl_type = 2;
                    pG->pl_costume = 1;
                    w->se_id = SndCall(6, 6, 0, 0, 0, 0);
                    SndStrReq(snd_id, 4, 200, 0);
                } else if (pG->System_flg & 0x40000000) {
                    if (!(pSys->unlock_flg & 0x00400000)) {
                        pSys->unlock_flg |= 0x00400000;
                        {
                            int ofs;
                            for (ofs = 0; ofs < 0x10; ofs += 4) {
                                u8* tbl = (u8*) pSys + 0x10;
                                *(u32*) ((u32) tbl + ofs) = 0;
                            }
                        }
                        // Index form: the eliminable biv gives check_dbra_loop's bct (insert_bct refuses a
                        // known count below 3); the integer address keeps the pSys reload in the loop, and
                        // `i << 2` (not `i * 4`) keeps the table as the first `stwx` operand.
                        {
                            int i;
                            for (i = 0; i < 2; i++) {
                                u8* tbl = (u8*) pSys + 0x20;
                                *(u32*) ((u32) tbl + (i << 2)) = 0;
                            }
                        }
                    }
                    if (DebugTrg(1)) {
                        BitOff(pSys->unlock_flg, 0x08000000);
                        BitOff(pSys->unlock_flg, 0x02000000);
                        BitOff(pSys->unlock_flg, 0x04000000);
                        BitOff(pSys->unlock_flg, 0x01000000);
                    }
                    // Every fade of this function is the FadeSetW inline (its own colour pair at 32/36):
                    // here `&col.start` is PRE'd across the loops (`addi r29,r1,32`, `mr r4,r29`) while
                    // `&col.end` stays a hard-register argument set (`addi r5,r1,36` at the call).
                    FadeSetW(0, 5, 0, 0);
                    w->omk_char_no = 0;
                    w->Rno1 = 6;
                    SndCall(0, 60, 0, 0, 0, 0);
                }
            } else {
                FadeSetW(0, 5, 0, 0);
                w->Rno1++;
                SndCall(0, 5, 0, 0, 0, 0);
                SndStrReq(snd_id, 4, 200, 0);
            }
        } else if (Key.trg & (KEY_UP | KEY_DOWN)) {
            s8 old = w->omk_menu_no;
            if (Key.trg & KEY_UP) {
                w->omk_menu_no = 0;
            } else {
                w->omk_menu_no = 1;
            }
            if (old != w->omk_menu_no) {
                SndCall(0, 10, 0, 0, 0, 0);
            }
        }
        if (w->omk_menu_no == 0) {
            IdSys.unitPtr(0, ID_OMAKE)->be_flag |= 8;
            IdSys.unitPtr(1, ID_OMAKE)->be_flag &= ~8;
        } else {
            IdSys.unitPtr(0, ID_OMAKE)->be_flag &= ~8;
            IdSys.unitPtr(1, ID_OMAKE)->be_flag |= 8;
        }
        break;
    case 5:
        if ((Fade[0].flags & 1) == 0) {
            IdTexRelease(TEX_OWNER_ID_EVENT);
            IdSys.kill(0xFF, ID_OMAKE_BG);
            IdSys.kill(0xFF, ID_OMAKE);
            Mem_free(w->pOmk);
            FadeSetW(0x80000000, 5, 0, 0);
            w->Rno0 = 5;
            w->Rno1 = w->saveStep;
            w->Rno2 = w->saveSub;
            w->Rno3 = w->saveX3;
            w->counter = w->saveCnt;
            titleSet(w, w->saveCnt);
            titleMenuInit(w);
        }
        break;
    case 6:
        if ((Fade[0].flags & 1) == 0) {
            IdTexRelease(TEX_OWNER_ID_EVENT);
            IdSys.kill(0xFF, ID_OMAKE_BG);
            IdSys.kill(0xFF, ID_OMAKE);
            w->Rno1++;
        }
        break;
    case 7: {
        int i;
        FadeSetW(0x80000000, 5, 0, 0);
        IdTexDataLoad(OMK_PTR(4), TEX_OWNER_ID_EVENT);
        IdSys.set(OMK_PTR(7), 0xFF, ID_OMAKE, 0x13, 4, 0);
        for (i = 0; i < 5; i++) {
            IdUnit* u = IdSys.unitPtr(i, ID_OMAKE);
            u->texNo = i;
            u->tex_flag |= 2;
        }
        w->Rno1++;
        break;
    }
    case 8: {
        if (!(pSys->unlock_flg & 0x08000000)) {
            id_color_copy(0xFD, 1, ID_OMAKE);
        } else {
            id_color_copy(0xFC, 1, ID_OMAKE);
        }
        if (!(pSys->unlock_flg & 0x02000000)) {
            id_color_copy(0xFD, 2, ID_OMAKE);
        } else {
            id_color_copy(0xFC, 2, ID_OMAKE);
        }
        if (!(pSys->unlock_flg & 0x04000000)) {
            id_color_copy(0xFD, 3, ID_OMAKE);
        } else {
            id_color_copy(0xFC, 3, ID_OMAKE);
        }
        if (!(pSys->unlock_flg & 0x01000000)) {
            id_color_copy(0xFD, 4, ID_OMAKE);
        } else {
            id_color_copy(0xFC, 4, ID_OMAKE);
        }
        if ((Key.on & 0x20000) && w->omk_char_no != 0) {
            u32 bit = charBit[w->omk_char_no];
            u32* tbl = &pSys->unlock_flg;
            BitOn(tbl[bit >> 5], 0x80000000 >> (bit & 0x1F));
        }
        if (Key.trg & KEY_B) {
            FadeSetW(0, 5, 0, 0);
            w->Rno1++;
            SndCall(0, 5, 0, 0, 0, 0);
        } else if (Key.trg & KEY_A) {
            if (w->omk_char_no != 0) {
                u32 bit = charBit[w->omk_char_no];
                u32* tbl = &pSys->unlock_flg;
                if (!(tbl[bit >> 5] & (0x80000000 >> (bit & 0x1F)))) {
                    SndCall(0, 5, 0, 0, 0, 0);
                    break;
                }
            }
            switch (w->omk_char_no) {
            case 0:
                pG->pl_type = 0;
                pG->pl_costume = 1;
                break;
            case 1:
                pG->pl_type = 2;
                pG->pl_costume = 0;
                break;
            case 2:
                pG->pl_type = 4;
                pG->pl_costume = 0;
                break;
            case 3:
                pG->pl_type = 3;
                pG->pl_costume = 0;
                break;
            case 4:
                pG->pl_type = 5;
                pG->pl_costume = 0;
                break;
            }
            w->Rno1 = 10;
            w->omk_stage_no = 0;
            FadeSetW(0, 15, 0, 0);
            SndCall(0, 0x3F, 0, 0, 0, 0);
        } else if (Key.rep & (KEY_RIGHT | KEY_LEFT)) {
            s8 old = w->omk_char_no;
            if (Key.rep & KEY_LEFT) {
                w->omk_char_no--;
            } else {
                w->omk_char_no++;
            }
            w->omk_char_no = w->omk_char_no < 0 ? 4 : (w->omk_char_no > 4 ? 0 : w->omk_char_no);
            if (old != w->omk_char_no) {
                SndCall(0, 0x3E, 0, 0, 0, 0);
            }
        }
        {
            s8 sel = w->omk_char_no;
            IdUnit* a = IdSys.unitPtr(sel, ID_OMAKE);
            IdUnit* b = IdSys.unitPtr(0xFE, ID_OMAKE);
            IdUnit* u;
            b->scr = a->scr;
            u = IdSys.unitPtr(5, ID_OMAKE);
            u->texNo = sel;
            u->tex_flag |= 2;
            u = IdSys.unitPtr(6, ID_OMAKE);
            u->texNo = sel;
            u->tex_flag |= 2;
        }
        if (w->omk_char_no == 0 || omkFlagChk(charBit[w->omk_char_no])) {
            id_color_copy(0xFC, 5, ID_OMAKE);
        } else {
            id_color_copy(0xFD, 5, ID_OMAKE);
            IdSys.unitPtr(6, ID_OMAKE)->texNo = 5;
        }
        break;
    }
    case 9:
        if ((Fade[0].flags & 1) == 0) {
            IdTexRelease(TEX_OWNER_ID_EVENT);
            IdSys.kill(0xFF, ID_OMAKE_BG);
            IdSys.kill(0xFF, ID_OMAKE);
            w->Rno1 = 3;
        }
        break;
    case 10:
        if ((Fade[0].flags & 1) == 0) {
            IdSys.kill(0xFF, ID_OMAKE_BG);
            IdSys.kill(0xFF, ID_OMAKE);
            w->Rno1 = 11;
        }
        break;
    case 11:
        FadeSetW(0x80000000, 15, 0, 0);
        w->Rno1 = 12;
        stageSelectInit(w);
        break;
    case 12:
        if (Key.trg & KEY_B) {
            w->Rno1 = 6;
            SndCall(0, 5, 0, 0, 0, 0);
        } else if (stageSelect(w) != 0) {
            w->Rno2 = 0;
            w->Rno1 = 13;
        }
        break;
    case 13:
        w->Rno2++;
        if (w->Rno2 == title_snd_wait) {
            w->se_id = SndCall(6, 8, 0, 0, 0, 0);
        }
        if (w->Rno2 > 30) {
            w->Rno0 = 7;
            FadeSetW(0, 60, 0, 0);
            SndStrReq(snd_id, 4, 200, 0);
        }
        break;
    }
}

// Mercenaries stage select layout, cursor on stage 0.
void stageSelectInit(TitleWork* w)
{
    TitleArc* omk = w->pOmk;

    IdSys.kill(0xFF, ID_OMAKE);
    IdSys.set(TITLE_ARC_PTR(omk, 8), 0xFF, ID_OMAKE, 0x13, 4, 0);
    w->omk_stage_no = 0;
}

// Mercenaries stage select: d-pad over the 2 x 2 stages (locked ones by unlock_flg), shows the
// saved high scores per stage; A returns 1.
int stageSelect(TitleWork* w)
{
    int ret = 0;
    MercSaveWork save;
    int mode;

    if (Key.trg & KEY_A) {
        ret = 1;
    } else if (Key.rep & (KEY_UP | KEY_DOWN | KEY_RIGHT | KEY_LEFT)) {
        s8 old = w->omk_stage_no;
        if (Key.rep & KEY_UP) {
            if (old > 1) {
                w->omk_stage_no -= 2;
            }
        } else if (Key.rep & KEY_DOWN) {
            if (old <= 1) {
                w->omk_stage_no += 2;
            }
        } else if (Key.rep & KEY_LEFT) {
            if (w->omk_stage_no & 1) {
                w->omk_stage_no -= 1;
            }
        } else if (Key.rep & KEY_RIGHT) {
            if ((w->omk_stage_no & 1) == 0) {
                w->omk_stage_no += 1;
            }
        }
        w->omk_stage_no = w->omk_stage_no < 0 ? 3 : (w->omk_stage_no > 3 ? 0 : w->omk_stage_no);
        if (old != w->omk_stage_no) {
            SndCall(0, 0x3E, 0, 0, 0, 0);
        }
    }
    {
        int i;
        for (i = 0; i < 4; i++) {
            IdUnit* u = IdSys.unitPtr(i + 0x11, ID_OMAKE);
            u->texNo = i;
            u->tex_flag |= 2;
        }
    }
    {
        int i;
        for (i = 0; i < 4; i++) {
            IdUnit* u = IdSys.unitPtr(i + 0x21, ID_OMAKE);
            if (w->omk_stage_no == i) {
                u->be_flag &= ~8;
            } else {
                u->be_flag |= 8;
            }
        }
    }
    IdSys.unitPtr(0x31, ID_OMAKE)->be_flag &= ~8;
    IdSys.unitPtr(0x32, ID_OMAKE)->be_flag &= ~8;
    IdSys.unitPtr(0x33, ID_OMAKE)->be_flag &= ~8;
    IdSys.unitPtr(0x34, ID_OMAKE)->be_flag &= ~8;
    if (ret == 1) {
        IdUnit* u = IdSys.unitPtr(w->omk_stage_no + 0x31, ID_OMAKE);
        u->be_flag |= 8;
        IdSys.setTime(u, 0);
    }
    {
        IdUnit* u;
        u = IdSys.unitPtr(1, ID_OMAKE);
        if (pSys->unlock_flg & 0x08000000) {
            u->be_flag &= ~8;
        } else {
            u->be_flag |= 8;
        }
        u->texNo = 0;
        u->tex_flag |= 2;
        u = IdSys.unitPtr(2, ID_OMAKE);
        if (pSys->unlock_flg & 0x02000000) {
            u->be_flag &= ~8;
        } else {
            u->be_flag |= 8;
        }
        u->texNo = 1;
        u->tex_flag |= 2;
        u = IdSys.unitPtr(3, ID_OMAKE);
        if (pSys->unlock_flg & 0x04000000) {
            u->be_flag &= ~8;
        } else {
            u->be_flag |= 8;
        }
        u->texNo = 2;
        u->tex_flag |= 2;
        u = IdSys.unitPtr(4, ID_OMAKE);
        if (pSys->unlock_flg & 0x01000000) {
            u->be_flag &= ~8;
        } else {
            u->be_flag |= 8;
        }
        u->texNo = 3;
        u->tex_flag |= 2;
        // The target's `li r30,0` sits right before MercSysGetSaveWork; a plain `mode = 0` there lets
        // jump1 turn the first `if` into a store-flag (`xori/subfic/adde`: reg_set_last finds the
        // constant), earlier it is hoisted. A mask cse cannot fold (no nonzero-bits logic) is not a
        // constant for jump1; combine folds it to `(set mode 0)` (no REG_EQUAL note) after cse2.
        // COMPILER-DIFF: #13 (constant spelled as a combine-folded mask)
        mode = ((u32) u >> 16) & 0xFFFF0000;
    }
    {
        MercSysGetSaveWork(&save);
        if (pG->pl_type == 2) {
            mode = 1;
        }
        if (pG->pl_type == 4) {
            mode = 2;
        }
        if (pG->pl_type == 3) {
            mode = 3;
        }
        if (pG->pl_type == 5) {
            mode = 4;
        }
        int i;
        int rank;
        for (i = 0; i < 4; i++) {
            int j;
            rank = save.rank[mode][i];
            if (rank == 0) {
                IdSys.unitPtr(i * 16 + 0x40, ID_OMAKE)->be_flag &= ~8;
            } else {
                IdSys.unitPtr(i * 16 + 0x40, ID_OMAKE)->be_flag |= 8;
            }
            for (j = 0; j < 5; j++) {
                if (j < rank) {
                    IdSys.unitPtr(i * 16 + 0x41 + j, ID_OMAKE)->be_flag |= 8;
                } else {
                    IdSys.unitPtr(i * 16 + 0x41 + j, ID_OMAKE)->be_flag &= ~8;
                }
            }
            // A do-while(0) body (a macro in the original): its loop depth weights the two
            // `save.stage[i].score` reads so the `i * 12` giv outranks `rank` in global-alloc (r28/r27).
            do {
            if (save.stage[i].score == 0) {
                for (j = 0; j < 8; j++) {
                    IdSys.unitPtr(i * 16 + 0x80 + j, ID_OMAKE)->be_flag &= ~8;
                }
            } else {
                IdUnit* u = IdSys.unitPtr(i * 16 + 0x88, ID_OMAKE);
                u->be_flag |= 8;
                u->tex_flag |= 2;
                IdSetNum(&IdSys, i * 16 + 0x81, ID_OMAKE, save.stage[i].score, 9999999, 7, 0);
            }
            } while (0);
        }
    }
    return ret;
}

static cRoomJmp* pRj;

// State 7, leaving the title: chooses the start room — a new game starts at stage 1's first room
// (debug menu picks otherwise), a load restores the save (CardLoad, System_flg 0x100 continue),
// Ada / Mercenaries start at their rooms with the chosen character / stage; sets the new-game
// flag (System_flg 0x2000), the next position and chains into GameTask.
void titleExit(TitleWork* w)
{
#if !defined(__PPC__) && RE4DC_QUALITY
    re4dc_quality_freeze("titleExit");
#endif
    if ((s32) pG->System_flg >= 0 && !(pG->System_flg & 0x40000000)) {
        pG->pl_type = 0;
        pG->game_costume = 0;
    }
    if (!(pG->System_flg & 0x100) && (s32) pG->System_flg >= 0 && !(pG->System_flg & 0x40000000)) {
        pRj = new cRoomJmp(roomInfoAddr);
#if !defined(__PPC__) && RE4DC_DBG_WARP
        const int warp = re4dc_warp_title_exit();  // the warp room replaces config.txt's
#else
        const int warp = 0;
#endif
        w->Stage = pG->stage_no;
        w->Room[w->Stage] = pRj->getRoomIdx(pG->stage_no, pG->room_no);
        w->JumpPoint = pG->JumpPoint;
        w->em_list_no = checkEmListNo(pRj->getRoomInfo(w->Stage, w->Room[w->Stage])->roomNo);
        w->load_no = 1;
        w->menu_x = 340;
        w->menu_y = 60;
        w->se_id = 0;
        while (!warp && !(Joy[0].trg & 0x1100)) {
            titleDebugMenu(w);
            TaskSleep(1);
        }
        G_ROOM_ID = pRj->getRoomInfo(w->Stage, w->Room[w->Stage] + w->JumpPoint)->roomNo;
        pG->JumpPoint = w->JumpPoint;
        pG->em_list_no = w->em_list_no;
        if (pG->em_list_no > 3) {
            pG->Scenario_flg[0] |= 0x10000000;
        } else if (pG->em_list_no > 2) {
            pG->Scenario_flg[0] |= 0x40000;
        }
        switch (w->c_pos) {
        case 1:
            if (CardLoad() == 1) {
                pG->System_flg |= 0x100;
            } else {
                pG->System_flg |= 0x04000000;
            }
            return;
        case 2:
            G_ROOM_ID = 0x120;
            pG->JumpPoint = 0;
            pG->pl_type = 0;
            break;
        case 0x12:
            BitOn(pSys->unlock_flg, 0x40000000);
            pG->System_flg |= 0x04000000;
            return;
        }
        if ((s32) pG->System_flg >= 0 && !(pG->System_flg & 0x40000000)) {
            PlSetCostume();
        }
        if (!(pG->x4FB8_32 & 0xFF0000FF)) {
            u32 room = pG->room_id32 & 0xFFFF0000;
            if (room == 0x01200000 || room == 0x01000000 || room == 0x01010000 || room == 0x01030000 || room == 0x01060000) {
                pG->pl_costume = 0;
            } else {
                pG->pl_costume = 1;
                pG->Item_find_flg |= 0x00200000;
            }
        }
        if (pG->stage_no == 2) {
            BitOn(pG->Debug_flg[3], 0x00800000);
            if (pG->room_id != 0x200) {
                BitOn(pG->Scenario_flg[0], 0x00800000);
            }
        } else if (pG->stage_no == 3) {
            BitOn(pG->Debug_flg[3], 0x40000);
            BitOn(pG->Scenario_flg[0], 0x10000);
            if (pG->room_id == 0x333) {
                BitOn(pG->Debug_flg[3], 0x20000);
            }
        }
        switch (pG->stage_no) {
        case 0:
            break;
        case 1:
            BitOn(pG->Item_find_flg, 4);
            break;
        case 2:
            BitOn(pG->Item_find_flg, 4);
            BitOn(pG->Item_find_flg, 2);
            if ((pG->room_id32 & 0xFFFF00FF) != 0x02000000) {
                BitOn(pG->Scenario_flg[0], 0x00800000);
            }
            break;
        }
        pRj->getRoomInfo(pG->stage_no, pG->JumpPoint + pRj->getRoomIdx(pG->stage_no, pG->room_no))->setNextPos();
#if !defined(__PPC__) && RE4DC_DBG_WARP
        if (warp) {
            re4dc_warp_next_pos();
        }
#endif
        delete pRj;
        if (pG->pl_type == 6) {
            pG->pl_type = 0;
            BitOn(pG->Status_flg[3], 0x04000000);
        }
    }
    {
        u8 point = 0;
        BitOff(pG->Debug_flg[3], 0x00200000);
        if (!(pG->System_flg & 0x100)) {
            pG->System_flg |= 0x2000;
        }
        G_ROOM_ID_PREV = 0xFFF;
        pG->em_list_no = -1;
        if (pG->System_flg & 0x80000000) {
            G_ROOM_ID = 0x405;
            pG->JumpPoint = point;
            pG->Part = point;
            FSet(pG->sub_pos.x, 28450.0f);
        FSet(pG->sub_pos.y, -16798.0f);
        FSet(pG->sub_pos.z, -40000.0f);
        FSet(pG->sub_angle, -2.49f);
        } else if (pG->System_flg & 0x40000000) {
        switch (w->omk_stage_no) {
        case 0:
            G_ROOM_ID = 0x400;
            pG->JumpPoint = point;
            pG->Part = point;
            FSet(pG->sub_pos.x, -12400.0f);
            FSet(pG->sub_pos.y, 2576.0f);
            FSet(pG->sub_pos.z, 31080.0f);
            FSet(pG->sub_angle, 2.486f);
            break;
        case 1:
            G_ROOM_ID = 0x402;
            pG->JumpPoint = point;
            pG->Part = point;
            FSet(pG->sub_pos.x, 21035.0f);
            FSet(pG->sub_pos.y, 3065.0f);
            FSet(pG->sub_pos.z, -26370.0f);
            FSet(pG->sub_angle, -1.53f);
            break;
        case 2:
            G_ROOM_ID = 0x403;
            pG->JumpPoint = point;
            pG->Part = point;
            FSet(pG->sub_pos.x, 31558.0f);
            FSet(pG->sub_pos.y, 8314.0f);
            FSet(pG->sub_pos.z, 38823.0f);
            FSet(pG->sub_angle, 2.345f);
            break;
        case 3:
            G_ROOM_ID = 0x404;
            pG->JumpPoint = point;
            pG->Part = point;
            FSet(pG->sub_pos.x, -640.0f);
            FSet(pG->sub_pos.y, 0.0f);
            FSet(pG->sub_pos.z, -15890.0f);
            FSet(pG->sub_angle, 3.13f);
            break;
        }
        } else {
            memcpy((u8*) pG + 0x4FC0, &pG->NextPos, sizeof(Vec));
            FSet(pG->sub_angle, pG->NextY);
            G_ROOM_ID = pG->next_room;
            pG->Part = pG->next_point;
        }
    }
    if (w->se_id != 0) {
        while (SndEndCheck(w->se_id) == 0) {
            TaskSleep(1);
        }
    }
    IdTexRelease(TEX_OWNER_ID_TITLE);
    IdTexRelease(TEX_OWNER_ID_EVENT);
    IdSys.roomInit();
    primFree();
    if (w->pDat) {
        Mem_free(w->pDat);
        w->pDat = 0;
    }
    if ((s32) pG->System_flg < 0 || (pG->System_flg & 0x40000000)) {
        Mem_free(w->pOmk);
    }
    pG->Status_flg[2] &= ~0x8000;
    IdFreeBuffer();
    Mem_free(w);
    systemVISetBlack(1);
    ScreenReSize(512, 448);
    TaskChain(GameTask, 0);
}

// COMPILER-DIFF: #4 (int argument to an s8 parameter: the original passes `no` without the extsb)
s8 RjGetPointNumI(cRoomJmp* rj, s8 stage, int room) asm("getPointNum__8cRoomJmpScSc");
s8 RjGetNextPointNoI(cRoomJmp* rj, s8 stage, int room, s8 point, int dir) asm("getNextPointNo__8cRoomJmpScScSci");

// Debug start menu (title): stage / room / point, player type, costume, level and mode, edited
// with the pad and shown with eprintf; writes the choice into pG before titleExit.
void titleDebugMenu(TitleWork* w)
{
    static char* title_debug_tbl[21] = {
        "DEBUG GAME", "LOAD GAME", "NEW GAME", "STAGE", "ROOM", "JUMP_POINT", "EM_LIST", "PAGE",
        "ENEMY SET", "ETC SET", "SOUND MODE", "SCENARIO", "USE DBMEM", "SHOOT MODE", "PL COSTUME",
        "LANGUAGE", "EFF_COUNTRY", "GAME_COUNTRY", "OMAKE GAME", "GAME LEVEL", "CAPTION",
    };
    static char* pl_type_tbl[7] = {"LEON", "ASHLEY", "ADA", "HUNK", "KLAUSER", "WESKER", "LEON+ASHLEY"};
    static char* sound_mode[3] = {"MONO", "STEREO", "DPL2"};
    static char* shoot_mode[3] = {"OFF", "PHOTO", "VIDEO"};
    static char* language_tbl[8] = {"JPN", "USA", "ENG", "GER", "FRA", "ESP", "ITA", "KOR"};
    static char* game_mode_tbl[7] = {"DEFAULT", "VERY_EASY", "2", "EASY", "3", "NORMAL", "HARD"};
    CRoomInfo* info;
    s16 x;
    s16 y;
    int i;
    int lines = 21;
    int no;
    int num;

    if (Joy[0].on & 0x00200000) {
        w->menu_x += 4;
    }
    if (Joy[0].on & 0x00100000) {
        w->menu_x -= 4;
    }
    if (Joy[0].on & 0x00400000) {
        w->menu_y += 4;
    }
    if (Joy[0].on & 0x00800000) {
        w->menu_y -= 4;
    }
    x = w->menu_x;
    y = w->menu_y;
    info = pRj->getRoomInfo(w->Stage, w->Room[w->Stage] + w->JumpPoint);
    if (pRj->checkRoomNo(w->Stage, w->Room[w->Stage]) == w->Room[w->Stage]) {
        eprintf(x, y - 16, 4, 0, "%s", info->name);
    }
    for (i = 0; i < lines; i++) {
        int col = 0;
        if (i == w->c_pos) {
            col = 6;
        }
        eprintf(x, y + i * 16, col, 0, "%s", title_debug_tbl[i]);
    }
    eprintf(x - 8, y + w->c_pos * 16, 0, 0, ">");
    y -= 16;
    eprintf(x + 96, y += 16, 4, 0, "%s", pl_type_tbl[pG->pl_type]);
    eprintf(x + 96, y += 16, 4, 0, "");
    eprintf(x + 96, y += 16, 4, 0, "");
    eprintf(x + 96, y += 16, 4, 0, "%x", w->Stage);
    eprintf(x + 96, y += 16, 4, 0, "%02x", info->room);
    eprintf(x + 96, y += 16, 4, 0, "%x", w->JumpPoint);
    eprintf(x + 96, y += 16, 4, 0, "%s", getEmListDbgName(w->em_list_no));
    eprintf(x + 96, y += 16, 4, 0, "%d", pG->debug_mode);
    eprintf(x + 96, y += 16, 4, 0, "%s", (pG->Debug_flg[2] & 0x00200000) ? "OFF" : "ON");
    eprintf(x + 96, y += 16, 4, 0, "%s", (pG->Debug_flg[3] & 0x800) ? "OFF" : "ON");
    eprintf(x + 96, y += 16, 4, 0, "%s", sound_mode[pSys->sound_mode]);
    eprintf(x + 96, y += 16, 4, 0, "%s", (pG->Debug_flg[2] & 0x04000000) ? "OFF" : "ON");
    eprintf(x + 96, y += 16, 4, 0, "%s", (pG->Debug_flg[3] & 0x00200000) ? "ON" : "OFF");
    eprintf(x + 96, y += 16, 4, 0, "%s", shoot_mode[(s8) pG->shooting_mode]);
    eprintf(x + 96, y += 16, 4, 0, "%d", pG->game_costume);
    eprintf(x + 96, y += 16, 4, 0, "%s", language_tbl[pSys->language]);
    eprintf(x + 96, y += 16, 4, 0, "%s", language_tbl[pSys->region]);
    eprintf(x + 96, y += 16, 4, 0, "%s", language_tbl[pG->language]);
    if ((s32) pG->System_flg < 0) {
        eprintf(x + 96, y += 16, 4, 0, "ADA GAME");
    } else if (pG->System_flg & 0x40000000) {
        eprintf(x + 96, y += 16, 4, 0, "ETC GAME");
    } else {
        y += 16;
    }
    eprintf(x + 96, y += 16, 4, 0, "%s", game_mode_tbl[pG->game_mode]);
    eprintf(x + 96, y += 16, 4, 0, "%s", (pG->Debug_flg[2] & 0x400) ? "OFF" : "ON");

    if (Joy[0].rep & 0x00080008) {
        w->c_pos--;
    }
    if (Joy[0].rep & 0x00040004) {
        w->c_pos++;
    }
    w->c_pos = w->c_pos < 0 ? lines - 1 : (w->c_pos > lines - 1 ? 0 : w->c_pos);
    switch (w->c_pos) {
    case 0:
        if (Joy[0].trg & 0x00020002) {
            pG->pl_type = (pG->pl_type + 1) % 7;
        }
        if (Joy[0].trg & 0x00010001) {
            pG->pl_type = (pG->pl_type + 6) % 7;
        }
        break;
    case 1:
        if (Joy[0].rep & 0x00020002) {
            w->load_no++;
        }
        if (Joy[0].trg & 0x00010001) {
            w->load_no--;
        }
        w->load_no = w->load_no == 0 ? 10 : (w->load_no > 10 ? 1 : w->load_no);
        break;
    case 2:
        break;
    case 3:
        if (Joy[0].rep2 & 0x00020002) {
            w->Stage = pRj->getNextStageNo(w->Stage, 1);
            w->JumpPoint = 0;
            w->em_list_no = checkEmListNo(pRj->getRoomInfo(w->Stage, w->Room[w->Stage])->roomNo);
        }
        if (Joy[0].rep2 & 0x00010001) {
            w->Stage = pRj->getNextStageNo(w->Stage, -1);
            w->JumpPoint = 0;
            w->em_list_no = checkEmListNo(pRj->getRoomInfo(w->Stage, w->Room[w->Stage])->roomNo);
        }
        no = pRj->checkRoomNo(w->Stage, w->Room[w->Stage]);
        if (no >= 0) {
            w->Room[w->Stage] = no;
        }
        break;
    case 4:
        if (Joy[0].rep2 & 0x00020002) {
            w->Room[w->Stage] = pRj->getNextRoomNo(w->Stage, w->Room[w->Stage], 1);
            w->JumpPoint = 0;
            w->em_list_no = checkEmListNo(pRj->getRoomInfo(w->Stage, w->Room[w->Stage])->roomNo);
        }
        if (Joy[0].rep2 & 0x00010001) {
            w->Room[w->Stage] = pRj->getNextRoomNo(w->Stage, w->Room[w->Stage], -1);
            w->JumpPoint = 0;
            w->em_list_no = checkEmListNo(pRj->getRoomInfo(w->Stage, w->Room[w->Stage])->roomNo);
        }
        break;
    case 5:
        no = (s8) pRj->getRoomInfo(w->Stage, w->Room[w->Stage])->room;
        if (Joy[0].rep2 & 0x00020002) {
            if (RjGetPointNumI(pRj, w->Stage, no) - 1 == w->JumpPoint) {
                w->JumpPoint = 0;
            } else {
                w->JumpPoint = RjGetNextPointNoI(pRj, w->Stage, no, w->JumpPoint, 1);
            }
        }
        if (Joy[0].rep2 & 0x00010001) {
            if (w->JumpPoint == 0) {
                w->JumpPoint = RjGetPointNumI(pRj, w->Stage, no) - 1;
            } else {
                w->JumpPoint = RjGetNextPointNoI(pRj, w->Stage, no, w->JumpPoint, -1);
            }
        }
        w->JumpPoint = w->JumpPoint < 0 ? 0 : (w->JumpPoint > RjGetPointNumI(pRj, w->Stage, no) - 1 ? RjGetPointNumI(pRj, w->Stage, no) - 1 : w->JumpPoint);
        break;
    case 6:
        num = w->em_list_no;
        if (Joy[0].rep & 0x00020002) {
            num++;
        }
        if (Joy[0].rep & 0x00010001) {
            num--;
        }
        num = num < 0 ? 0 : (num > getEmListNum() - 1 ? getEmListNum() - 1 : num);
        w->em_list_no = num;
        break;
    case 7:
        if (Joy[0].rep & 0x00020002) {
            pG->debug_mode++;
        }
        if (Joy[0].rep & 0x00010001) {
            pG->debug_mode--;
        }
        pG->debug_mode = pG->debug_mode < 0 ? 24 : (pG->debug_mode > 24 ? 0 : pG->debug_mode);
        break;
    case 8:
        if (Joy[0].trg & 0x00030003) {
            pG->Debug_flg[2] ^= 0x00200000;
        }
        break;
    case 9:
        if (Joy[0].trg & 0x00030003) {
            pG->Debug_flg[3] ^= 0x800;
        }
        break;
    case 10: {
        int old;
        num = pSys->sound_mode;
        old = num;
        if (Joy[0].trg & 0x00020002) {
            num++;
        }
        if (Joy[0].trg & 0x00010001) {
            num--;
        }
        num = num < 0 ? 0 : (num > 2 ? 2 : num);
        if (num != old) {
            pSys->sound_mode = num;
            SndSetOutputMode(pSys->sound_mode, 0);
        }
        break;
    }
    case 11:
        if (Joy[0].trg & 0x00030003) {
            pG->Debug_flg[2] ^= 0x04000000;
        }
        break;
    case 12:
        break;
    case 13:
        num = (s8) pG->shooting_mode;
        if (Joy[0].trg & 0x00020002) {
            num++;
        }
        if (Joy[0].trg & 0x00010001) {
            num--;
        }
        num = num < 0 ? 0 : (num > 2 ? 2 : num);
        pG->shooting_mode = num;
        break;
    case 14:
        num = pG->game_costume;
        if (Joy[0].trg & 0x00020002) {
            num++;
        }
        if (Joy[0].trg & 0x00010001) {
            num--;
        }
        num = num < 0 ? 0 : (num > 1 ? 1 : num);
        pG->game_costume = num;
        break;
    case 15:
        num = pSys->language;
        if (Joy[0].trg & 0x00020002) {
            num++;
        }
        if (Joy[0].trg & 0x00010001) {
            num--;
        }
        num = num < 0 ? 0 : (num > 7 ? 7 : num);
        pSys->language = num;
        break;
    case 16:
        num = pSys->region;
        if (Joy[0].trg & 0x00020002) {
            num++;
        }
        if (Joy[0].trg & 0x00010001) {
            num--;
        }
        num = num < 0 ? 0 : (num > 7 ? 7 : num);
        pSys->region = num;
        break;
    case 17:
        num = pG->language;
        if (Joy[0].trg & 0x00020002) {
            num++;
        }
        if (Joy[0].trg & 0x00010001) {
            num--;
        }
        num = num < 0 ? 0 : (num > 7 ? 7 : num);
        pG->language = num;
        break;
    case 18:
        break;
    case 19:
        num = pG->game_mode;
        if (Joy[0].trg & 0x00020002) {
            num++;
        }
        if (Joy[0].trg & 0x00010001) {
            num--;
        }
        num = num <= 0 ? 1 : (num > 6 ? 6 : num);
        pG->game_mode = num;
        break;
    case 20:
        if (Joy[0].trg & 0x00030003) {
            pG->Debug_flg[2] ^= 0x400;
        }
        break;
    }
}
