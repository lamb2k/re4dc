#include "types.h"
#include "main_mem.h"
#include "st_room.h"
#include "atari.h"
#include "light.h"
#include "flag_rsf.h"
#include "player.h"
#include "esp.h"

// PS2_ENEMY_ROOMS bit 0x10 (lane ps2enemy 2026-10-14) runs the PS2 r11a rules (chapter 2-1 and ROUTE_CH22 alike);
// its held list rows come from that bit only (stage.cpp), so ROUTE_CH22 alone keeps the GameCube r11a.
#if defined(RE4DC_GAME) && !defined(__PPC__) && \
    defined(RE4DC_PS2_ENEMY_ROOMS) && (RE4DC_PS2_ENEMY_ROOMS & 0x10)
#define CH22_PS2_ROOM 1
#include "libgpu.h"
#include "sce_at.h"
#include "em_set.h"
#include "global.h"
#include "sce.h"
#include "sce_sys.h"
extern "C" void OSPanic(const char* file, int line, const char* msg, ...);
#else
#define CH22_PS2_ROOM 0
#endif

#if CH22_PS2_ROOM
#include "em_wrap.h"
#endif
#if defined(RE4DC_PS2_ENEMY_ROOMS) && (RE4DC_PS2_ENEMY_ROOMS & 0x10)
#include "dbg_tool.h"
#define R11A_PS2_LOG(no) OSReport("ps2en: r11a sends 0x%02x (alive %d)\n", no, SceCountEmAlive(0x10, 0x20))
#else
#define R11A_PS2_LOG(no)
#endif

// Room 1-1a (D:/Bio4/Prog/r11a.cpp): the lake shore path. R11aInit attaches the water ripple / splash
// effects to the player and registers the water hit-effect table; R11aMain keeps the player's footstep
// type on the water variant. The PS2 route also has source area-driven enemy waves.

struct R11aWork {
    u8 pad[1];
};

static R11aWork* r11a_work;

// Hit effects of attribute type 2 (water)
static const AtEffInfo r11a_eff_info = {
    1, {1, 0x2C}, {1, 0x2F}, {1, 0x2E}, {1, 0x2D}, {1, 0x20}, {1, 0x20}, {1, 0x2B}, {1, 0x2F},
};

#if CH22_PS2_ROOM
// PS2 USA st1_2.rel 0xa5d0..0xa7a8: the cap is checked once each tick,
// then each room flag can independently activate one held enemy.
static void r11a_ps2EmSet()
{
    for (;;) {
        if ((u32) SceCountEmAlive(0x10, 0x20) < 9) {
            if (pG->Room_flg[2] & 0x40000000) {
                if (RsfCheck(G_ROOM_ID, 0) == 0) {
                    RsfSet(G_ROOM_ID, 0);
                    setEm(0x16, -1, 0, 1, 1);
                    R11A_PS2_LOG(0x16);
                } else if (RsfCheck(G_ROOM_ID, 1) == 0) {
                    RsfSet(G_ROOM_ID, 1);
                    setEm(0x18, -1, 0, 1, 1);
                    R11A_PS2_LOG(0x18);
                }
            }
            if (pG->Room_flg[2] & 0x80000000) {
                if (RsfCheck(G_ROOM_ID, 2) == 0) {
                    RsfSet(G_ROOM_ID, 2);
                    setEm(0x1C, -1, 0, 1, 1);
                    R11A_PS2_LOG(0x1C);
                } else if (RsfCheck(G_ROOM_ID, 3) == 0) {
                    RsfSet(G_ROOM_ID, 3);
                    setEm(0x1D, -1, 0, 1, 1);
                    R11A_PS2_LOG(0x1D);
                }
            }
        }
        SceSleep(1);
    }
}

// PS2 AEV3/4 flag64/65 follow native2/type5.
static AreaData r11aPs2Areas[2] = {
    {1, AREA_TYPE_XZ4, 0, {{-17611.4844f, 27844.0254f, 750.0f, {{70668.6172f, 66441.6016f}, {91927.8672f, 85510.2578f}, {48055.3711f, 125758.156f}, {46259.9062f, 87999.8281f}}}}},
    {1, AREA_TYPE_XZ4, 0, {{-18419.1875f, 45832.7539f, 750.0f, {{-67727.8438f, 52214.3633f}, {24456.8496f, 65787.0703f}, {15635.1504f, 117966.641f}, {-60501.168f, 85953.7969f}}}}},
};

// Allocate with native ownership/cleanup and a free number, then insert at the
// source AEV position. Item areas can already occupy the PS2 logical number.
static SceAtWork* r11a_ps2FlagArea(SceAtWork* prev, AreaData* area, int flagNo)
{
    if (prev == 0 || prev->otNo != 2) {
        OSPanic(__FILE__, __LINE__, "ch22 r11a: unexpected AEV boundary");
        return 0;
    }
    Vec corners[4];
    for (int i = 0; i < 4; i++) {
        corners[i].x = area->u.xz4.p[i].x;
        corners[i].y = area->u.xz4.floor;
        corners[i].z = area->u.xz4.p[i].z;
    }
    int no = SceAtCreateExecAt(pPL, corners, 0, 1, 1, area->u.xz4.height,
                             2, 0.0f, 0.0f, 0, 0, 0, 0, 0);
    SceAtWork* at = no >= 0 ? SceAtPtr(no) : 0;
    if (at == 0) {
        OSPanic(__FILE__, __LINE__, "ch22 r11a: PS2 AEV allocation failed");
        return 0;
    }
    DelPrim((u32*) sceAtSetOtStart(), (u32*) at);
    at->area = *area;
    at->type = 4;
    at->pParent = 0;
    at->parentParts = 0;
    at->angleRange = 45;
    at->flg.kind = 0;
    at->flg.off = 0;
    at->flg.no = flagNo;
    AddPrim((u32*) prev, (u32*) at);
    return at;
}

static void r11a_ps2Init()
{
    SceAtWork* prev = SceAtPtr(2);
    if (prev == 0 || prev->type != 5 || prev->otNo != 2) {
        OSPanic(__FILE__, __LINE__, "ch22 r11a: expected source AEV2 boundary");
        return;
    }
    for (int i = 0; i < 2; i++) {
        prev = r11a_ps2FlagArea(prev, &r11aPs2Areas[i], 64 + i);
        if (prev == 0) return;
    }
    // PS2 R11aInit 0xa504: preserve entry-side selection and wrapper args.
    if (pG->room_id_prev == 0x119) {
        setEm(0x1C, -1, 0, 1, 1);
        setEm(0x1D, -1, 0, 1, 1);
    } else {
        setEm(0x16, -1, 0, 1, 1);
        setEm(0x18, -1, 0, 1, 1);
    }
    R11A_PS2_LOG(pG->room_id_prev == 0x119 ? 0x1C1D : 0x1618);
    SceExec(0x12, (TaskFunc) r11a_ps2EmSet, 0, 0, SCE_PRIO_DEF_2, 0);
}
#endif

// Room init: two persistent player effects (EstSet types 3/1: the water ripple / splash attached to
// pPL) and the water hit-effect table for attribute type EAT_ET_WATER.
void R11aInit()
{
    void* zero = 0;

#line 46 "D:/Bio4/Prog/r11a.cpp"
    r11a_work = (R11aWork*) MEM_CALLOC(1, 1, 0xd);

    EstSet((int) pPL, -1, 0, 0, 3, 2, 0, 0, (u32) pPL, zero);
    EstSet((int) pPL, -1, 0, 0, 1, 0, 0, 0, (u32) pPL, zero);
    EatMgr.registEffInfo(EAT_ET_WATER, (AtEffInfo*) &r11a_eff_info);
#if CH22_PS2_ROOM
    r11a_ps2Init();
#endif
}

// Per frame: keep the player's footstep/OT type switched to the water variant while in the lake room.
void R11aMain()
{
    setPlWaterOtType();
}
