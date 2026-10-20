// game/esp06.cpp: effect id 0x06, a sprite riding an effect path (EspGetPathAddr owner Work8[0],
// id Work8[1]). Dist advances by PathSpeed (prm 0xCC, +- xD4 random, accelerated by 0xD0 / 10)
// each frame; at the path end Flg (Work8[2]) bit0 loops (pausing StopFrame + random frames),
// bit1 parks at the end, else the sprite dies. Vec1 (degrees) / Vec0 (scale in 10ths) build
// PathMat, a transform applied to the path; Vec2 gives a start fraction along it.

#include "atari.h"
#include "re4dc_xm.h" // GAME_SH4ZAM_LOGIC (lane sh4zam-direct)
#include "light.h"
#include "math_sub.h"
#include "rnd.h"
#include "esp.h"

struct Esp06Work {
    u8 PathId;    // 0x00 (gen->xC9)
    u8 Flg;     // 0x01 bit0: loop, bit1: stop at the end, bit2: stopped, bit7: has matrix (gen->xCA)
    u16 pathId;   // 0x02 (gen->xC8)
    u16 seg;      // 0x04 current path segment (PathGetPos reads/writes a halfword)
    u8 pad_6[2];
    void* pPath;   // 0x08
    f32 Dist;     // 0x0C distance along the path
    Vec LocalPos;      // 0x10 base position
    Mtx PathMat;      // 0x1C rotation / scale applied to the path
    f32 PathSpeed;      // 0x4C
    f32 PathAccele;      // 0x50
    u8 StopFrame;  // 0x54 frames to wait at a loop restart (gen->xFC)
    u8 StopFrameRnd;   // 0x55 random addition to waitBase (gen->xFD)
    u8 wait;      // 0x56
};

// Path follower: moves the sprite along an effect path (loops / stops / dies at the end).
class cEsp06 : public cEsp {
public:
    Esp06Work m_Free;  // 0xF8

    virtual void move();
    virtual int SetFreeWork(EspGenWork* gen, u32* seed);
};

extern "C" {
int Esp06GetPathPos(cEsp06* esp);
void esp06_CommonMove(cEsp06* esp);
void esp06_Move00(cEsp06* esp);
void esp06_Move01(cEsp06* esp);
}

static void (*Esp06MoveTbl[])(cEsp06*) = { esp06_Move00, esp06_Move01 };

// EspCreateTbl[0x06] factory.
cEsp* Esp06_Create()
{
    return new cEsp06;
}

// Samples the path at Dist into m_Pos (weighted paths attached to a model use PathGetPosEm).
// Returns 0 when Dist is past either end.
int Esp06GetPathPos(cEsp06* esp)
{
    Esp06Work* w = &esp->m_Free;
    int ret;

    if (PathHasWeight(w->pPath)) {
        if (esp->m_pMod != NULL) {
            ret = PathGetPosEm(w->pPath, w->Dist, esp->m_pMod, &w->seg, &esp->m_Pos);
        } else {
            ret = PathGetPos(w->pPath, w->Dist, &w->seg, &esp->m_Pos);
        }
    } else {
        ret = PathGetPos(w->pPath, w->Dist, &w->seg, &esp->m_Pos);
    }
    return ret;
}

// The full per-frame update: on release from the parent bakes the parent matrix into LocalPos,
// speeds, angles and PathMat; integrates LocalPos (the path origin) with the base speed, applies
// scale / colour / life / animation, advances Dist (or counts down `wait`), handles the path end
// (loop / stop / die) and sets m_Pos = PathMat * path point + LocalPos.
void esp06_CommonMove(cEsp06* esp)
{
    Esp06Work* w = &esp->m_Free;
    Mtx m;

    if (esp->parent != pEffParentWorld && esp->m_Release_time != 0xFF && esp->m_Release_time <= esp->m_Life_time) {
        RE4DC_XM_LOAD(esp->parent->mat);
        RE4DC_XM_DIR(esp->parent->mat, &w->LocalPos, &w->LocalPos);
        RE4DC_XM_DIR(esp->parent->mat, &esp->m_Speed, &esp->m_Speed);
        RE4DC_XM_DIR(esp->parent->mat, &esp->m_Speed_plus, &esp->m_Speed_plus);
        if (esp->m_Tool_flg & 1) {
            RotMatrix(m, &esp->m_Ang);
            PSMTXConcat(esp->parent->mat, m, m);
            Matrix2AxisAngle(m, &esp->m_Ang);
        }
        PSMTXConcat(esp->parent->mat, w->PathMat, w->PathMat);
        w->Flg |= 0x80;
        esp->parent = pEffParentWorld;
    }
    if (esp->m_Pos_start_cnt <= esp->m_Life_time) {
        PSVECAdd(&w->LocalPos, &esp->m_Speed, &w->LocalPos);
        w->PathSpeed += w->PathAccele;
        PSVECAdd(&esp->m_Speed, &esp->m_Speed_plus, &esp->m_Speed);
        PSVECScale(&esp->m_Speed, &esp->m_Speed, esp->m_D_speed);
    }
    if (esp->m_Size_start_cnt <= esp->m_Life_time) {
        esp->m_Size_mul += esp->m_Size_plus;
        esp->m_Size_plus *= esp->m_D_size_plus;
        if (esp->m_Size_mul <= 0.0f) {
            PushEsp(esp);
            return;
        }
    }
    PSVECAdd(&esp->m_Ang, &esp->m_Ang_plus, &esp->m_Ang);
    if (esp->ColorUpdate()) {
        if (esp->m_Life_max != 0 && esp->m_Life_max <= esp->m_Life_time) {
            PushEsp(esp);
            return;
        }
        esp->m_Life_time++;
        if (!esp->AnmMove()) {
            PushEsp(esp);
            return;
        }
        {
            if (w->wait == 0) {
                w->Dist += w->PathSpeed;
            } else {
                w->wait--;
            }
            if (!Esp06GetPathPos(esp)) {
                if (w->Flg & 1) {
                    if (w->PathSpeed > 0.0f) {
                        w->Dist -= PathGetLength(w->pPath);
                    } else {
                        w->Dist += PathGetLength(w->pPath);
                    }
                    Esp06GetPathPos(esp);
                    w->wait = w->StopFrame;
                    if (w->StopFrameRnd != 0) {
                        w->StopFrame += (u32)Rnd() % w->StopFrameRnd;
                    }
                } else if (w->Flg & 2) {
                    if (w->PathSpeed > 0.0f) {
                        w->Dist = PathGetLength(w->pPath) - 0.1f;
                    } else {
                        w->Dist = 0.0f;
                    }
                    Esp06GetPathPos(esp);
                    w->Flg |= 4;
                } else {
                    PushEsp(esp);
                    return;
                }
            }
            if (w->Flg & 0x80) {
                PSMTXMultVec(w->PathMat, &esp->m_Pos, &esp->m_Pos);
            }
            PSVECAdd(&esp->m_Pos, &w->LocalPos, &esp->m_Pos);
        }
    }
}

// Rno0 == 0: first frame; runs the common update and moves to Rno0 1.
void esp06_Move00(cEsp06* esp)
{
    esp06_CommonMove(esp);
    esp->m_Rno0 = 1;
}

// Rno0 == 1: steady state, the common update.
void esp06_Move01(cEsp06* esp)
{
    esp06_CommonMove(esp);
}

// Dispatches on m_Rno0 through Esp06MoveTbl.
void cEsp06::move()
{
    Esp06MoveTbl[m_Rno0](this);
}

// Resolves the path (fails when missing), reads speed / acceleration / wait parameters, forces
// the speed sign to match prm 0xCC, builds PathMat from Vec1 rotation and Vec0 scale, and picks
// the start distance from Vec2 (percent + random percent, wrapped) or the far end for a negative
// speed.
int cEsp06::SetFreeWork(EspGenWork* gen, u32* seed)
{
    Esp06Work* w = &m_Free;
    f32 t;

    w->pathId = gen->Work8[0];
    w->PathId = gen->Work8[1];
    w->Flg = gen->Work8[2];
    w->PathSpeed = (f32)(s32)gen->prm.w.xCC;
    w->PathAccele = (f32)(s32)gen->prm.w.xD0 * 0.1f;
    w->PathSpeed += (f32)(s32)gen->xD4 * fRandSeed1_1(seed);
    w->StopFrame = gen->WorkSp8[0];
    w->StopFrameRnd = gen->WorkSp8[1];
    if ((f32)(s32)gen->prm.w.xCC != 0.0f) {
        if ((f32)(s32)gen->prm.w.xCC > 0.0f) {
            if (w->PathSpeed < 0.0f) {
                w->PathSpeed = -w->PathSpeed;
            }
        } else {
            if (w->PathSpeed > 0.0f) {
                w->PathSpeed = -w->PathSpeed;
            }
        }
    }
    w->pPath = EspGetPathAddr(w->pathId, w->PathId);
    if (w->pPath == NULL) {
        return 0;
    }
    w->LocalPos = m_Pos;
    if (gen->Vec1.x != 0.0f || gen->Vec1.y != 0.0f || gen->Vec1.z != 0.0f) {
        Vec r;

        r = *(Vec*)&gen->Vec1.x;
        w->Flg |= 0x80;
        PSVECScale(&r, &r, 0.017453292f);
        RotMatrix(w->PathMat, &r);
    } else {
        PSMTXIdentity(w->PathMat);
    }
    if (gen->Vec0.x != 0.0f || gen->Vec0.y != 0.0f || gen->Vec0.z != 0.0f) {
        Vec s;
        Mtx sm;

        s = *(Vec*)&gen->Vec0.x;
        w->Flg |= 0x80;
        PSVECScale(&s, &s, 0.1f);
        s.x += 1.0f;
        s.y += 1.0f;
        s.z += 1.0f;
        PSMTXScale(sm, s.x, s.y, s.z);
        PSMTXConcat(w->PathMat, sm, w->PathMat);
    }
    if (gen->Vec2.x != 0.0f || gen->Vec2.y != 0.0f) {
        t = gen->Vec2.x * 0.01f;
        t += gen->Vec2.y * 0.01f * fRandSeed0_1(seed);
        if (t > 1.0f) {
            t -= (f32)(u32)t;
        }
        if (t < 0.0f) {
            t += (f32)(u32)(-t) + 1.0f;
        }
        w->Dist = t * PathGetLength(w->pPath);
    } else if (w->PathSpeed < 0.0f) {
        w->Dist = PathGetLength(w->pPath);
    }
    return 1;
}
