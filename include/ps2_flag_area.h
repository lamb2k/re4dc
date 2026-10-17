#pragma once
// PS2 flag areas absent from the GameCube AEV (lane ch4found16, 2026-10-16; included only under PS2_ENEMY_CASTLE
// bits). A PS2 room's code tests a per-frame area flag (Room_flg[2] / [3], cleared by SceAtWorkLoopInit each frame)
// that only the PS2 AEV sets; this adds the PS2 record (type 4, kind 0: event flag `no`) as the r111 port does
// (src/st1/r111.cpp r111_ps2FlagArea): allocated with native ownership, then linked into the room's area list
// after the last source area of ordering table 2. Area data from tools/d367/ps2ref/ps2roomdiff.py `aev`.
#include "area.h"
#include "libgpu.h"
#include "sce_at.h"
#include "player.h"
extern "C" void OSPanic(const char* file, int line, const char* msg, ...);

static inline SceAtWork* re4dc_ps2FlagArea(const AreaData* area, int flagNo, u8 trigger, const char* who)
{
    SceAtWork* prev = 0;
    for (int n = 0x7F; n >= 0 && prev == 0; n--) {
        SceAtWork* w = SceAtPtr(n);
        if (w != 0 && w->otNo == 2) {
            prev = w;
        }
    }
    if (prev == 0) {
        OSPanic(__FILE__, __LINE__, "%s: no source AEV area to link the PS2 flag area after", who);
        return 0;
    }
    Vec corners[4];
    for (int i = 0; i < 4; i++) {
        corners[i].x = area->u.xz4.p[i].x;
        corners[i].y = area->u.xz4.floor;
        corners[i].z = area->u.xz4.p[i].z;
    }
    int no = SceAtCreateExecAt(pPL, corners, 0, 1, 1, area->u.xz4.height, 2, 0.0f, 0.0f, 0, 0, 0, 0, 0);
    SceAtWork* at = no >= 0 ? SceAtPtr(no) : 0;
    if (at == 0) {
        OSPanic(__FILE__, __LINE__, "%s: PS2 AEV allocation failed", who);
        return 0;
    }
    DelPrim((u32*) sceAtSetOtStart(), (u32*) at);
    at->area = *area;
    at->type = 4;
    at->trigger = trigger;
    at->checkType = 1;
    at->checkFlag = 0;
    at->pParent = 0;
    at->parentParts = 0;
    at->angleRange = 45;
    at->flg.kind = 0;
    at->flg.off = 0;
    at->flg.no = (u16) flagNo;
    AddPrim((u32*) prev, (u32*) at);
    return at;
}
