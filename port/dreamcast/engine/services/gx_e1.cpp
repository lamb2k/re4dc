// The GameCube graphics calls the hosted behaviour still makes (lane eng-e1). The engine draws from its tables, not from
// GX: the laser-sight and debug-line draws of cObjWep go nowhere (the laser is an E1 gap, see the hand-back). The one
// call with an engine meaning is GXSetProjection: the hosted camera (view.cpp) sets the projection there, and the
// engine camera record (services/draw.cpp) takes it from e1_projection.
#include "types.h"
#define __declspec(x) __attribute__((x))
#include <dolphin/gx.h>
#include <string.h>
#include "e1_engine.h"

extern "C" {
float e1_projection[7];   // GX projection parameters: type, then the six non-trivial terms (as GXSetProjectionv)
volatile unsigned char e1_gxfifo[32] asm("_GXWGFifo");
}

void GXSetProjection(const f32 m[4][4], GXProjectionType type)
{
    e1_projection[0] = (f32) type;
    if (type == GX_PERSPECTIVE) {
        e1_projection[1] = m[0][0];
        e1_projection[2] = m[0][2];
        e1_projection[3] = m[1][1];
        e1_projection[4] = m[1][2];
        e1_projection[5] = m[2][2];
        e1_projection[6] = m[2][3];
    } else {
        e1_projection[1] = m[0][0];
        e1_projection[2] = m[0][3];
        e1_projection[3] = m[1][1];
        e1_projection[4] = m[1][3];
        e1_projection[5] = m[2][2];
        e1_projection[6] = m[2][3];
    }
}
void GXSetCullMode(GXCullMode) {}
void GXClearVtxDesc(void) {}
void GXSetVtxDesc(GXAttr, GXAttrType) {}
void GXSetVtxAttrFmt(GXVtxFmt, GXAttr, GXCompCnt, GXCompType, u8) {}
void GXSetNumTexGens(u8) {}
void GXBegin(GXPrimitive, GXVtxFmt, u16) {}
void GXSetNumChans(u8) {}
void GXSetChanCtrl(GXChannelID, GXBool, GXColorSrc, GXColorSrc, u32, GXDiffuseFn, GXAttnFn) {}
void GXSetBlendMode(GXBlendMode, GXBlendFactor, GXBlendFactor, GXLogicOp) {}
void GXSetZMode(GXBool, GXCompare, GXBool) {}
void GXSetTevOp(GXTevStageID, GXTevMode) {}
void GXSetTevOrder(GXTevStageID, GXTexCoordID, GXTexMapID, GXChannelID) {}
void GXSetNumTevStages(u8) {}
void GXLoadPosMtxImm(const f32[3][4], u32) {}
void GXSetCurrentMtx(u32) {}
