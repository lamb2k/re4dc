// game/espgen44: effect controller 44, screen filter parameter setter (D:/Bio4/Prog/espgen44.cpp).
// The record programs Filter05 (Id 0) or Filter06 (Id != 0) from its colour/size fields when set
// up, and resets the filter to zero when the controller is destroyed; it does nothing per frame.
#include "atari.h"
#include "light.h"
#include "esp.h"
#include "espgen.h"
#include "filter.h"
#if defined(RE4DC_RAIN_R10C_DIAG) && RE4DC_RAIN_R10C_DIAG
extern "C" u32 re4dc_rain_diag_generation();
extern "C" void re4dc_rain_diag_bind44(u32, const void*, const void*, const void*, u32, u32, u32);
extern "C" void re4dc_rain_diag_destruct44(const void*);
#endif

struct Espgen44Work {
    u8 type;           // 0x14 0 = Filter05, 1 = Filter06
};

// EspgenMoveTbl entry for controller type 0x44: nothing per frame (the filter runs on its own).
void Espgen44_Move(EspgenWork* w)
{
}

// EspgenTransTbl entry: nothing to draw.
void Espgen44_Trans(EspgenWork* w)
{
}

// Filter05SetParam with all-immediate arguments: the original issues the FPR argument copies
// interleaved before the trailing `li`s (`fmr f2; li r7; fmr f3; li r8; li r9`), which GCC 2.95
// only produces when the float parameters are declared first (atari_init.h idiom).
void Filter05SetParamF(f32 x, f32 y, f32 z, int a, int b, int c, int d, int e, int f, int g) asm("Filter05SetParam__Fiiiiiiifff");
// Same call with loaded arguments (Espgen44_SetFreeWork): there the original's move order is the
// five leading ints, the three floats, then the two trailing ints (`lbz r9` early, `lfs f1` after
// `lbz r7`, `lbz r8` last) — a per-call-site interleaving (the only one of 7 tried that matches).
void Filter05SetParamM(int a, int b, int c, int d, int e, f32 x, f32 y, f32 z, int f, int g) asm("Filter05SetParam__Fiiiiiiifff");

// Destruct entry: turns the filter the record programmed back off (Filter05SetParam / Filter06SetParam
// with all-zero parameters).
void Espgen44_Destruct(EspgenWork* w)
{
    Espgen44Work* p = (Espgen44Work*) w->work;

    switch (p->type) {
    case 0:
        Filter05SetParamF(0.0f, 0.0f, 0.0f, 0, 0, 0, 0, 0, 0, 0);
        break;
    case 1: {
#if defined(RE4DC_RAIN_R10C_DIAG) && RE4DC_RAIN_R10C_DIAG
        re4dc_rain_diag_destruct44(w);
#endif
        Vec zero = {0.0f, 0.0f, 0.0f};
        Filter06SetParam(0, 0, 0, 0, 0, 0.0f, &zero, 0.0f, &zero, 0.0f, 0);
        break;
    }
    }
}

// Programs the filter from the record: level = Work8[0]*100+100, colour Col_start_rgba, Col_d_a,
// scale = Size_base_x*0.005; Filter05 (Id 0) takes Blend_type and kind Tex_id, Filter06 takes
// Speed/R_speed as vectors and kind Work8[1].
int Espgen44_SetFreeWork(EspgenWork* w, EspGenWork* rec, EspSeqData* head, cModel* model, u16 parts, Mtx* mtx,
                         Vec* pos, Vec* rot, EspSeqOpt* pSct)
{
    Espgen44Work* p = (Espgen44Work*) w->work;
    if (rec->Id == 0) {
        p->type = 0;
    } else {
        p->type = 1;
    }

    switch (p->type) {
    case 0: {
        int level = (s8) rec->Work8[0] * 100 + 100;
        f32 scale = rec->Size_base_x * 0.005f;
        int kind = rec->Tex_id;
        Filter05SetParamM(level, rec->Col_start_r, rec->Col_start_g, rec->Col_start_b, rec->Col_start_a, rec->Col_d_a, 0.0f, scale, rec->Blend_type, kind);
        break;
    }
    case 1: {
        int level = (s8) rec->Work8[0] * 100 + 100;
        f32 scale = rec->Size_base_x * 0.005f;
        int kind = rec->Work8[1];
#if defined(RE4DC_RAIN_R10C_DIAG) && RE4DC_RAIN_R10C_DIAG
        const u32 before = re4dc_rain_diag_generation();
#endif
        Filter06SetParam(level, rec->Col_start_r, rec->Col_start_g, rec->Col_start_b, rec->Col_start_a, rec->Col_d_a, &rec->Speed, 0.0f, &rec->R_speed, scale,
                         kind);
#if defined(RE4DC_RAIN_R10C_DIAG) && RE4DC_RAIN_R10C_DIAG
        re4dc_rain_diag_bind44(before, w, rec, head, w->info.owner,
            (w->flag & 3) == 1 && w->id == 0x44 && rec->Kind == 1 && rec->Espgen_id == 0x44 && rec->Id != 0,
            ((u32) rec->Id << 8) | rec->Kind);
#endif
        break;
    }
    }
    return 1;
}

// the split object pads .rodata to 8 bytes
asm(".section .rodata; .balign 8");
