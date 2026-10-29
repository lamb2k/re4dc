// game/espgen45: effect controller 45, the weather (open-air) water surface (D:/Bio4/Prog/espgen45.cpp).
// A height-field grid (Espgen42Work: hA/hB height buffers, pos/nrm vertex arrays, a bump texture
// and a display list) that follows the camera target, is stirred by the noise texture 0xFE and drawn
// with a screen-copy refraction, an indirect bump stage, a specular texture and an optional mask.
// Room code overrides position/height/size/colour/parameters through the Estgen45Set* entry points
// (esp4c passes an Esp4cWork). Entry points: Espgen45_Move / _Trans / _SetFreeWork / _Destruct.
#include "light.h"
#include "atari.h"
#include "global.h"
#include "esp.h"
#include "espgen.h"
#include "math_sub.h"
#include "rnd.h"
#include "camera.h"
#include "os_vi.h"
#include "db_log.h"
#include "main_sub.h"
#include "joy.h"

#ifndef RE4DC_WATER45_LEAN
#define RE4DC_WATER45_LEAN 0
#endif
// RE4DC_WATER45_GRID_SKIP (ROUTE_CH13, r10b; needs RE4DC_WATER45_LEAN): no height-field grid at all.
// Logic reads only the plane (mat / inv / nx / ny: GetWaterHeight, GetWaterCrossPos); the grid feeds
// only the GX draw. The grid update takes no RNG; the init keeps its fRand1_1 calls (shared RNG).
#ifndef RE4DC_WATER45_GRID_SKIP
#define RE4DC_WATER45_GRID_SKIP 0
#endif
// RE4DC_WATER45_NATIVE (ROUTE_CH13, r10b; needs RE4DC_WATER45_LEAN): the water surface drawn natively
// (re4dc_water45_draw): the flat plane (mat) over the grid and its far border, the GameCube's "scene behind x
// TEV colour" as a PVR multiply. Without it nothing draws the lake (GX is a stub; the PS2 world has no water
// mesh) and the fog-coloured background shows through. Render only: reads the plane, writes nothing.
#ifndef RE4DC_WATER45_NATIVE
#define RE4DC_WATER45_NATIVE 0
#endif
#if RE4DC_WATER45_NATIVE && !RE4DC_WATER45_LEAN
#error RE4DC_WATER45_NATIVE replaces the GX draw that RE4DC_WATER45_LEAN removes
#endif
// RE4DC_WATER_PS2 (lane water16, 2026-10-16; render only; needs RE4DC_WATER45_NATIVE): the room water as the PS2 draws
// it (re4dc_water_ps2_draw below). Default 0.
#ifndef RE4DC_WATER_PS2
#define RE4DC_WATER_PS2 0
#endif
#if RE4DC_WATER_PS2 && !RE4DC_WATER45_NATIVE
#error RE4DC_WATER_PS2 needs RE4DC_WATER45_NATIVE
#endif

// Effect controller 45: weather water surface (same height-field model as Espgen42, following the
// camera). The Estgen45Set* entry points let the room script (esp4c) override its parameters.
// Espgen42 owns the water init (EspWaterInit): it resets this unit's overrides and g_pWater45.

// Parameter block handed over by esp4c (Esp4cWork, 0x20 bytes; the layout is esp4c.cpp's).
struct Esp4cWork {
    u8 Type;      // 0x00
    u8 Refrect_type;        // 0x01
    u8 Spec_Tex;        // 0x02
    u8 wave_ratio_base;        // 0x03
    s16 Shimmer_pow1;     // 0x04 indirect matrix parameters (SetIndMtx)
    s16 Shimmer_pow2;     // 0x06
    f32 damp;     // 0x08 (Espgen42Work::damp)
    f32 spread;   // 0x0C (Espgen42Work::spread)
    Vec ang;      // 0x10 surface rotation (SetWaterWork45)
    u8 flag;      // 0x1C
    u8 Mask_Tex;       // 0x1D
    u8 x1E;       // 0x1E
    u8 x1F;       // 0x1F
};

extern "C" {
// game/trans_lit.cpp
void commonWaterLightSet(cLight** list, int n, u32 alpha);
// Dolphin SDK performance monitor registers (base/PPCArch.h)
void PPCMtpmc1(u32 v);
void PPCMtpmc2(u32 v);
void PPCMtpmc3(u32 v);
void PPCMtpmc4(u32 v);
void PPCMtmmcr0(u32 v);
void PPCMtmmcr1(u32 v);
void Espgen45_Move00(EspgenWork* w);
void Espgen45_TransSub(EspgenWork* w);
void SetIndMtx_801291F4(Espgen42Work* p);   // the DOL's local SetIndMtx (Espgen42 owns the global one); sym_map name
EspgenWork* SetWaterWork45(EspgenWork* w, Vec* pos, Vec* rot, f32 size, u32 nx, u32 ny, f32 rate);
}

EspgenWork* g_pWater45;
static int g_bTargetCamera = 1;
static int g_bTargetHeight = 1;
static int g_bSizeOverWrite = 0;
static int g_bColorOverWrite = 0;
static int g_bColorMul = 0;
static int g_bSetParam = 0;
static f32 g_Target_x = 0.0f;
static f32 g_Target_y = 0.0f;
static f32 g_Target_z = 0.0f;
static f32 g_Size = 0.0f;
static u8 g_r = 0;
static u8 g_g = 0;
static u8 g_b = 0;
static u8 g_a = 0;
static f32 g_sr = 0.0f;
static f32 g_sg = 0.0f;
static f32 g_sb = 0.0f;
static f32 g_sa = 0.0f;
static f32 inv_mul = 1.0f;
static Esp4cWork g_Free;

static inline void ISet(int& d, int v) { d = v; }
static inline int IGet(int& d) { return d; }
static inline f32 FGet(f32& d) { return d; }
static inline void U8Set(u8& d, u8 v) { d = v; }

// Resets the room override state (camera-follow on, height-follow on, all overwrites off): called by
// EspWaterInit (Espgen42.cpp) at effect system init.
void Espgen45_static_init()
{
    g_bTargetCamera = 1;
    g_bTargetHeight = 1;
    g_Target_x = 10000000000.0f;
    g_Target_y = -10000000000.0f;
    g_Target_z = 100000000000.0f;
    g_bSizeOverWrite = 0;
    g_bColorOverWrite = 0;
    g_bColorMul = 0;
    g_bSetParam = 0;
    g_Size = 0.0f;
    g_r = 0;
    g_g = 0;
    g_b = 0;
    g_a = 0;
    g_sr = 0.0f;
    g_sg = 0.0f;
    g_sb = 0.0f;
    g_sa = 0.0f;
}

// u8 -> f32 through GQR2 from a stack byte (the compiler only emits psq_l from its own fpmem slot). volatile (no
// memory clobber): a volatile asm is a scheduling barrier for everything in RTL order around it, which is what puts
// the pos/cur address adds before the noise lbzx and the neighbour loads after it in the target's loop A.
// Loads straight into the destination variable (no statement-expression temp): the target's `psq_l f10; fsubs f10,f10`
// is one pseudo, the function-level `n`.
#if defined(__PPC__)
#define PSQ_L_U8_TO(dst, p) asm volatile("psq_l %0,0(%1),1,2" : "=f"(dst) : "b"(p), "m"(*(p)))
#else
#define PSQ_L_U8_TO(dst, p) ((dst) = (f32) *(const u8*) (p))
#endif

// Bump texture (I8, 8x4 tiles) index of grid point (x, y). x/8 before y/4 (the two signed divisions are
// separate blocks, so their order is the source order) and `(y / 4) << 5`: with `* 32` fold would
// reassociate the constant onto `(w1) >> 3` and hoist `(w1 >> 3) * 32`; the target keeps `srwi` in the loop.
#define BUMP_INDEX(x, y, w1) (((x) / 8) * 32 + (((y) / 4) << 5) * ((w1) >> 3) + (((y) & 3) << 3) + ((x) & 7))
// Noise texture (0xFE) index of grid point (x, y).
#define NOISE_INDEX(x, y) ((((y) << 6) & 0xB00) + (((x) << 2) & 0xA0) + (((y) & 3) << 3) + ((x) & 7))

// Step 0 (the only step) of Espgen45MoveTbl: recentres the surface on the camera target (or the
// override target/height), rebuilds mat/inv with the size and wave_ratio scale, then simulates one
// frame: mode != 1 is a damped two-buffer wave equation (damp/spread) plus noise-texture excitation;
// mode 1 is the spring model (hA height, hB velocity). Both refresh the vertex heights, normals and
// the bump texture, then flush the arrays to memory for the GP. Sets Status_flg[0] bit 0x200
// (water present). Debug: L trigger with Debug_flg[1] 0x00800000 drops a wave in the middle.
void Espgen45_Move00(EspgenWork* w)
{
    static f32 g45_wave_mul = 0.001f;
    static f32 wt_pow = 10.0f;
    Espgen42Work* p = (Espgen42Work*) w->work;
    Vec d0;
    Vec d1;
    Vec v;
    Vec d2;
    Vec d3;
    Mtx m;
    u8 tmp;
    GXTexObj* tex;
    u8* noise;
    f32* c;
    u32 frame;
    f32 size;
    f32 rate;
    u8 rotY;
    u8 mode;
    int i;
    int j;
    int k;
    int nz;   // noise index / byte of both loops: one function-level pseudo (see loop A)
    // loop A's `j / 8` and loop B's `(i / 4) << 5`: one function-level pseudo (r10 in both loops; a block-local
    // `(i / 4) << 5` would be tied into the `mullw` by local-alloc, the target ties the nx term).
    int jx;
    // loop B's `k + p->nx` (before the call) and `p->nx` (after it): one function-level pseudo (r11 in both places,
    // "set 2 times; dies in 2 places" = no local-alloc tie, so the Z block's `addi r9,r11,1` starts a fresh r9 chain).
    int mx;
    // noise value of both loops: also one function-level pseudo (global alloc, f10 in both loops). A block-local `n`
    // ties to the loop-A psq_l output / loop-B frsp result and permutes the loop-A/B FPR names and the sched2 slots
    // of the loop-B sum chain (77 -> 47 words).
    f32 n;
    // normal pointer `&nrm[k]` of both loops: one function-level pseudo (36 refs / 170 insns, 1.06) ranks above loop B's
    // k*4 giv (35 / 169, 1.04) and k (32 / 215, 0.74) in global alloc and takes r30 for both loops; k*4 then finds r30
    // taken and gets r29, k r31. A block-local pointer per loop (18 / 111, 0.65) came after both (k*4 r30, pointer r29).
    Vec* nk;
    // `j & 7` of both loops (noise index and bump index): one function-level pseudo ranks above `i` in global alloc and
    // takes r24 (i r23, (k-nx)*12 r26); a block-local `j & 7` per loop came after i, which then took r24. u8 as in
    // Espgen42 (there the narrow store is the +1 loop.c insn that keeps the 4.0 pool pair for the outer pass).
    u8 j7;

    d0.x = 1.0f;
    d0.z = 0.0f;
    d1.x = 0.0f;
    d1.z = 1.0f;
    d2.x = -1.0f;
    d2.z = 0.0f;
    d3.x = 0.0f;
    d3.z = -1.0f;
    frame = pG->Frame_cnt % 60;
    BitOn(pG->Status_flg[0], 0x200);
    if (g_bTargetCamera == 1) {
        FSet(g_Target_x, pG->Cam.param.at.x);
        FSet(g_Target_z, pG->Cam.param.at.z);
    }
    FSet(p->pos0.x, g_Target_x);
    p->pos0.z = g_Target_z;
    if (IGet(g_bTargetHeight) == 1) {
        p->pos0.y = g_Target_y;
    } else {
        p->pos0.y = p->Base_y;
    }
    size = p->size;
    if (g_bSizeOverWrite == 1) {
        size = g_Size;
    }
    if (g_bSetParam == 0) {
        PSMTXScale(p->mat, size, size * 0.05f + 100.0f, size);
    } else {
        RotMatrix(p->mat, &g_Free.ang);
        PSMTXScale(m, size, size * 0.05f + 100.0f, size);
        PSMTXConcat(p->mat, m, p->mat);
    }
    if (g_bSetParam == 0) {
        rotY = p->rotY;
    } else {
        rotY = g_Free.wave_ratio_base;
    }
    rate = 1.0f - (f32) (int) rotY / 255.0f;
    if (rate == 0.0f) {
        rate = 0.0001f;
    }
    p->mat[1][1] *= rate;
    PSMTXTransApply(p->mat, p->mat, p->pos0.x, p->pos0.y, p->pos0.z);
    PSMTXInverse(p->mat, p->inv);
    PPCMtpmc1(0);
    PPCMtpmc2(0);
    PPCMtpmc3(0);
    PPCMtpmc4(0);
    PPCMtmmcr1(0x78000000);
    PPCMtmmcr0(0x42);
    tex = EspGetTexObj(0xFE, frame);
    if (tex == NULL) {
        return;
    }
#if RE4DC_WATER45_GRID_SKIP
    return;
#endif
    noise = (u8*) GXGetTexObjData(tex) + 0x80000000;
    u32 nx = p->nx;
    f32 hx = (f32) (int) (nx / 2);
    f32 hy = (f32) (int) (p->ny / 2);
    f32 inx = 1.0f / (f32) (int) nx * inv_mul;
    f32 iny = 1.0f / (f32) (int) p->ny * inv_mul;
    if (g_bSetParam == 0) {
        mode = p->mode;
    } else {
        mode = g_Free.Type;
    }
    if (mode != 1) {
        if ((pG->Debug_flg[1] & 0x00800000) && (Joy[0].on & 0x100)) {
            // The index is the loop variable `k` (target `lwz r31` = k's register, base+index `lfsx f0,hB,k4`).
            k = (int) ((f32) (int) (p->nx * p->ny) * 0.5f);
            // Byte offset in a variable: inside an address `p->hB[k]` expands to `(plus (mult k 4) hB)` (expr.c
            // both_summands puts a MULT first) = `lfsx k4,hB`; a register index keeps `(plus hB k4)` = `lfsx hB,k4`.
            u32 k4 = k * 4;
            *(f32*) ((u8*) p->hB + k4) -= wt_pow;
        }
        f32 damp;
        f32 spread;
        if (g_bSetParam == 0) {
            damp = p->damp;
        } else {
            damp = g_Free.damp;
        }
        f32 cdamp = 2.0f - damp * 4.0f;
        if (g_bSetParam == 0) {
            spread = p->spread;
        } else {
            spread = g_Free.spread;
        }
        f32* cur;
        f32* next;
        if (pG->Frame_cnt & 1) {
            cur = p->hA;
            next = p->hB;
        } else {
            cur = p->hB;
            next = p->hA;
        }
        f32 fy = 1.0f;
        for (i = 1; i < p->ny; i++) {
            f32 fx = 1.0f;
            k = i * (nx + 1);   // two statements: the product lands in k's register (`mullw r31; addi r31,r31,1`)
            k++;
            for (j = 1; j < (int) nx; j++) {
                int i3 = (i & 3) << 3;
                // The k*4 giv is discovered BEFORE the k*12 giv (`&p->pos[k]` below): loop.c emits the giv inits in bl->giv
                // order = reverse discovery, so the preheader is `mr r29,k12 | slwi r31,k,2` (k4 init last) and the two
                // `mulli` take r8/r10 as the target. With `c += k` as the first k*4 use the two inits were swapped.
                u32 k4 = k * 4;
                // Before the (volatile) psq_l: `lwz pos; add c; add pos+k12` issue before the noise lbzx (target order).
                Vec* pv = &p->pos[k];   // a pointer variable: `add pos,k12` (operand order); `p->pos[k].y = ..` gives `add k12,pos`
                // `c` is a function-level pointer set twice per iteration (set_in_loop != 1, so loop.c
                // does not treat it as a giv): the neighbours stay `lfs 4(c)/-4(c)` off `add c = cur + k*4`
                // and `*(c - nx - 1)` becomes `subf` + `lfs -4` off the hoisted `nx*4`.
                c = cur;
                c = (f32*) ((u8*) c + k4);
                // The index in the function-level `nz` (set in both loops = global pseudo, allocated after local-alloc): the
                // byte pseudo then finds r0 free in local-alloc (its fake-lifetime pass would refuse the register of a
                // block-local index dying at the lbzx), and global alloc gives nz r0 too: `lbzx r0,noise,r0; stb r0`.
                j7 = j & 7;
                nz = (((i) << 6) & 0xB00) + (((j) << 2) & 0xA0) + i3 + j7;
                tmp = noise[nz];
                PSQ_L_U8_TO(n, &tmp);
                n -= 80.0f;
                f32 sum = c[-1] + c[1] + *(c - nx - 1) + *(c + nx + 1);
                next[k] = damp * sum + cdamp * cur[k] - next[k];
                // FGet: a reference read is a MEM with neither the struct nor the scalar flag, so it depends on the
                // `stfsx next[k]` store (next's alias base is 0) and issues right after it like the target's
                // `lfs g45_wave_mul`; the plain static read is a fixed scalar that never aliases the in-struct store
                // and floated 6 insns up. The pos address is computed before the store (target `lwz pos` early).
                pv->y = next[k] = (n * FGet(g45_wave_mul) + next[k]) * spread;
#if !RE4DC_WATER45_LEAN
                Vec* nrm = p->nrm;   // before the v.x/v.z reads: kept across the call (`lfsx nrm[k].x`, `4(nrm+k*12)`)
                v.x = p->pos[k - 1].y - p->pos[k + 1].y;
                v.y = 2.0f;
                v.z = p->pos[k - nx].y - p->pos[k + nx].y;
                nk = &nrm[k];   // the function-level pointer (see its declaration); `nrm[k].y/.z` below fold onto it in cse
                PSVECScale(&v, nk, 1.0f / 2.3f);
                {
                    // BUMP_INDEX with the function-level `j7` (r24, see its declaration) as the last term.
                    // Both signed divisions through ONE temp `t` (the target's `mr r0,j .. srawi jx,r0 | cmpwi i; mr r0,i`: the
                    // second copy anti-depends on the first srawi in sched1, so the compare issues before it, and both temps
                    // share r0); `jx << 5` (a shift, not `jx * 32`: a MULT in an address sum is put first by expand and would
                    // start the add chain, the target starts it with the i term: `add r9,r9,r0`).
                    int t = j;
                    if (j < 0) t = j + 7;
                    jx = t >> 3;
                    t = i;
                    if (i < 0) t = i + 3;
                    p->bump[((t >> 2) << 5) * ((nx + 1) >> 3) + (jx << 5) + i3 + j7] = (u8) (nrm[k].x * 255.0f * 2.0f + 128.0f);
                }
                nrm[k].x += (fx - hx) * inx;
                nrm[k].z += (fy - hy) * iny;
                nrm[k].y *= 0.25f;
#endif
                fx += 1.0f;
                k++;
            }
            fy += 1.0f;
        }
    } else {
        // COMPILER-DIFF: loop.c move_movables. The target hoists one more invariant out of the inner loop before the
        // 4.0 pool pair (threshold 71 - 3 per moved insn), so 4.0 stays for the outer pass (outer preheader) and
        // 0.0018 moves in the inner pass 2. A codeless asm set of `i` used after the inner loop is that extra moved
        // insn (no register: it takes a free callee-saved GPR); emits nothing. The real construct is unknown.
        int dead;
        for (i = 1; i < p->ny; i++) {
            k = i * (p->nx + 1);
            for (j = 1; j < p->nx; j++) {
                asm("" : "=r"(dead) : "r"(i));
                j7 = j & 7;
                nz = (((i) << 6) & 0xB00) + (((j) << 2) & 0xA0) + (((i) & 3) << 3) + j7;   // NOISE_INDEX with the shared j7
                nz = noise[nz];   // same variable: `lbzx r0,noise,r0; xoris r0` (see loop A)
                // As in loop A: the pos address before the hB/hA stores (p has an unknown alias base, so a `lwz pos`
                // placed after them would wait for them; the target issues it before the first `stfsx hB[k]`).
                Vec* pv = &p->pos[k];
                f32* hA = p->hA;
                f32* hB = p->hB;
                c = hA;
                c += k;
                f32 sum = c[-1] + c[1] + *(c - p->ny - 1) + *(c + p->ny + 1);
                // n before the hB[k] update: the 0x4330/pool-double and 80.0 movables precede the 4.0 pair in loop.c's
                // list (the target's inner preheader order is lfd; lfs 80.0; lfs 1.0; ...; 4.0 is in the outer one).
                n = (f32) nz - 80.0f;
                // hB through a byte offset in a variable (`stfsx hB,k4` base first, see the wt_pow store above); hA's
                // address is the cse'd `c` (`(plus hA k4)` from `c += k`, a non-address context) and is base first as is.
                u32 k4 = k * 4;
#define HB (*(f32*) ((u8*) hB + k4))
                HB += sum - hA[k] * 4.0f;
                hA[k] += n * 0.0001f + HB * 0.04f;
                HB *= 0.92f;
#undef HB
                pv->y = n * 0.0018f + hA[k];
#if !RE4DC_WATER45_LEAN
                Vec* nrm = p->nrm;
                v.x = p->pos[k - 1].y - p->pos[k + 1].y;
                v.y = 2.0f;
                // `d` first: the `add mx` is then the last use of the `lhz nx` (REG_WEIGHT 0) and issues before the `subf`.
                int d = k - p->nx;
                mx = k + p->nx;
                v.z = p->pos[d].y - p->pos[mx].y;
                nk = &nrm[k];   // the function-level pointer shared with loop A (r30 in both loops, see its declaration)
                PSVECScale(&v, nk, 1.0f / 2.3f);
                {
                    // Loop B's index differs from loop A's: `j / 8` in its own statement (first division, own temp), the i
                    // term FIRST (`jx * nx8`: the nx chain `lhz; addi; srawi` is then evaluated after the i-division's branch,
                    // inside the Z block as in the target, and `mullw r9,r10,r9` ties the nx term), `jq << 5` (see loop A).
                    // COMPILER-DIFF: candidate #17 (r0 occupant): `j / 8` pinned to r0 = a hard-register conflict of the i
                    // copy `t_i` with r0 during the i-division blocks, so global.c's preference override skips r0 and t_i
                    // takes r9 (the target's `mr r9,i`); jq's shift then inherits r0 (`slwi r0,r0,5`).
                    register int jq PPC_REG("r0") = j / 8;
                    jx = (i / 4) << 5;
                    mx = p->nx;
                    // COMPILER-DIFF: candidate (sched1 slot fillers). Three codeless frame stores of `v` (dead after the
                    // call) that read `jx`: ready at t2, priority 90 (the `lfsx nrm[k].x` below may alias them), they take
                    // the t2/t3 issue slots and delay that load to t4, so the byte chain (fmuls .. psq_st) runs one cycle
                    // later and the fast-cast loadaddr (`unspec 17`, prints nothing) is born after the `mullw` (jx dead:
                    // it can take r10), the j loadaddr lives longer than the byte (byte r11, loadaddr r8) and `xoris j` is
                    // issued after the first index `add` (jq32 and the xoris share r0). Without them the loadaddr is issued
                    // at t2 and the xoris before the add: 49 words in the Z block. What the original had there is unknown.
                    asm("" : "=m"(v.x) : "r"(jx));
                    asm("" : "=m"(v.y) : "r"(jx));
                    asm("" : "=m"(v.z) : "r"(jx));
                    p->bump[jx * ((mx + 1) >> 3) + (jq << 5) + ((i & 3) << 3) + j7] = (u8) (nrm[k].x * 255.0f * 2.0f + 128.0f);
                }
                nrm[k].x += ((f32) j - (f32) (p->nx / 2)) * (1.0f / (f32) (int) p->nx);
                nk->z += ((f32) i - (f32) (p->ny / 2)) * (1.0f / (f32) (int) p->ny);
                nk->y *= 0.25f;
#endif
                k++;
            }
            asm("" : : "r"(dead));   // COMPILER-DIFF: use of the moved asm set (see above); emits nothing
        }
    }
    {
        u32 n = sizeof(Vec) * (p->nx + 1) * (p->ny + 1);   // nx first: fold attaches the 12 to (ny + 1) as the target
        DCStoreRange(p->pos, n);
#if !RE4DC_WATER45_LEAN
        DCStoreRange(p->nrm, n);
        DCStoreRange(p->bump, sizeof(Vec) * (p->nx + 1) * (p->ny + 1));
#endif
    }
}

// EspgenMoveTbl entry for controller type 0x45; frozen while Stop_flg bit 0x40000 is set.
void Espgen45_Move(EspgenWork* w)
{
    static void (*Espgen45MoveTbl[])(EspgenWork*) = {Espgen45_Move00};

    if (pG->Stop_flg & 0x40000) {
        return;
    }
    Espgen45MoveTbl[w->step](w);
}

#if RE4DC_WATER45_NATIVE
extern "C" {
void GXGetProjectionv(f32* p);
void GXGetViewportv(f32* v);
float re4dc_fog_amount(float z);                    // platform/native_static.cpp
int re4dc_water45_quad(const float positions[4][3], const float rgb[4][3], const float* projection,
                       const float* viewport);      // platform/native_ui.cpp
#if defined(RE4DC_LAKE_RIPPLES) && RE4DC_LAKE_RIPPLES
int re4dc_lake_begin(void);                         // platform/native_lake.cpp (LAKE_RIPPLES)
void re4dc_lake_cell(const float pos[4][3], const float lake[4][2], const float fog[4], const float up[3],
                     const float sun[3], const float* projection, const float* viewport);
#endif
}
// Espgen45_TransSub's surface, natively: the GX path's far border (g45_mul = 15 grid sizes, unless flag bit 0
// bounds it to the grid) and grid as one flat plane in grid space (y 0), cut into WATER45_CELLS x WATER45_CELLS
// cells spaced t*|t| (fine near the centre, which follows the camera target). Each corner's factor is the
// GameCube's result over the scene behind: TEV C0 (col, overrides applied) x screen (stage 0; the raster alpha that
// blends it is the channel's white material alpha, 1), fogged toward the background: m = lerp(col, 1, fog).
// Cells whose four corners are fully fogged multiply by 1 and are skipped. No bump, refraction warp or specular.
#define WATER45_CELLS 16
extern "C" void re4dc_water45_draw(EspgenWork* w)
{
    if (G_ROOM_ID != 0x10b) {
        return;   // r10b only: the one espgen45 room the route draws and proves
    }
    Espgen42Work* p = (Espgen42Work*) w->work;
    GXColor col = p->col;
    if (g_bColorOverWrite == 1) {
        col.r = g_r; col.g = g_g; col.b = g_b; col.a = g_a;
    } else if (g_bColorMul == 1) {
        col.r = (u8) ((f32) col.r * (f32) (int) g_r / 255.0f);
        col.g = (u8) ((f32) col.g * (f32) (int) g_g / 255.0f);
        col.b = (u8) ((f32) col.b * (f32) (int) g_b / 255.0f);
    }
    CameraCurrentProjection();
    f32 projection[7];
    f32 viewport[6];
    GXGetProjectionv(projection);
    GXGetViewportv(viewport);
    Mtx mv;
    PSMTXConcat(pG->Cam.v_mat, p->mat, mv);
    const f32 c[3] = {(f32) col.r / 255.0f, (f32) col.g / 255.0f, (f32) col.b / 255.0f};
    const f32 ex = (p->flag & 1) ? (f32) (int) (p->nx >> 1) : 7.5f * (f32) (int) p->nx;
    const f32 ez = (p->flag & 1) ? (f32) (int) (p->ny >> 1) : 7.5f * (f32) (int) p->ny;
    // The cells centre on the eye over the plane (the room may pin the plane's centre: Estgen45SetTargetCamera(0)) and
    // reach the GX path's border around it (the far cells fade into the fog), clipped to the surface.
    Mtx vi;
    Vec eye = {0.0f, 0.0f, 0.0f};
    Vec le;
    PSMTXInverse(pG->Cam.v_mat, vi);
    PSMTXMultVec(vi, &eye, &eye);
    PSMTXMultVec(p->inv, &eye, &le);
    const f32 reach = 2.0f * (ex > ez ? ex : ez);   // covers the whole surface from any eye over it
#if defined(RE4DC_LAKE_RIPPLES) && RE4DC_LAKE_RIPPLES
    // LAKE_RIPPLES: each cell's world x, z corners and fog, the plane normal and a sun direction in view space.
    const int lake = re4dc_lake_begin();
    f32 lrow[2][WATER45_CELLS + 1][3];
    f32 up[3] = {mv[0][1], mv[1][1], mv[2][1]};
    f32 sun[3];
    {
        const f32 ul = sqrtf(up[0] * up[0] + up[1] * up[1] + up[2] * up[2]);
        for (int q = 0; q < 3; ++q) up[q] = ul > 0.0f ? up[q] / ul : 0.0f;
        const f32 lw[3] = {0.35f, 0.55f, -0.76f};   // world direction toward the light (low sun over the far shore)
        for (int q = 0; q < 3; ++q) {
            sun[q] = pG->Cam.v_mat[q][0] * lw[0] + pG->Cam.v_mat[q][1] * lw[1] + pG->Cam.v_mat[q][2] * lw[2];
        }
    }
#endif
    // Two rows of corners at a time (view-space position, factor): row j - 1 and row j bound row j - 1's cells.
    const int n = WATER45_CELLS;
    f32 row[2][WATER45_CELLS + 1][6];
    for (int j = 0; j <= n; ++j) {
        f32 (*cur)[6] = row[j & 1];
        f32 tz = (f32) (2 * j - n) / (f32) n;
        tz = tz * (tz < 0.0f ? -tz : tz);
        for (int i = 0; i <= n; ++i) {
            f32 tx = (f32) (2 * i - n) / (f32) n;
            tx = tx * (tx < 0.0f ? -tx : tx);
            f32 lx = le.x + tx * reach;
            f32 lz = le.z + tz * reach;
            lx = lx < -ex ? -ex : lx > ex ? ex : lx;
            lz = lz < -ez ? -ez : lz > ez ? ez : lz;
            Vec l = {lx, 0.0f, lz};
            Vec v;
            PSMTXMultVec(mv, &l, &v);
            cur[i][0] = v.x; cur[i][1] = v.y; cur[i][2] = v.z;
            const f32 f = v.z < 0.0f ? re4dc_fog_amount(-v.z) : 0.0f;
#if defined(RE4DC_LAKE_RIPPLES) && RE4DC_LAKE_RIPPLES
            {
                Vec wv;   // world mm (the plane's units are grid cells: Size_base_x mm each)
                PSMTXMultVec(p->mat, &l, &wv);
                lrow[j & 1][i][0] = wv.x; lrow[j & 1][i][1] = wv.z; lrow[j & 1][i][2] = f;
            }
#endif
            for (int q = 0; q < 3; ++q) {
                cur[i][3 + q] = c[q] + (1.0f - c[q]) * f;
            }
        }
        if (j == 0) {
            continue;
        }
        const f32 (*prev)[6] = row[(j - 1) & 1];
        for (int i = 0; i < n; ++i) {
            const f32* k[4] = {prev[i], prev[i + 1], cur[i], cur[i + 1]};
            f32 pos[4][3];
            f32 cr[4][3];
            int unity = 1;
            int behind = 1;
            for (int q = 0; q < 4; ++q) {
                for (int e = 0; e < 3; ++e) {
                    pos[q][e] = k[q][e];
                    cr[q][e] = k[q][3 + e];
                    if (cr[q][e] < 0.998f) {
                        unity = 0;
                    }
                }
                if (pos[q][2] < 0.0f) {
                    behind = 0;
                }
            }
            if (unity || behind) {
                continue;
            }
            re4dc_water45_quad(pos, cr, projection, viewport);
#if defined(RE4DC_LAKE_RIPPLES) && RE4DC_LAKE_RIPPLES
            if (lake) {
                const f32* lk[4] = {lrow[(j - 1) & 1][i], lrow[(j - 1) & 1][i + 1], lrow[j & 1][i], lrow[j & 1][i + 1]};
                f32 lxz[4][2];
                f32 fg[4];
                for (int q = 0; q < 4; ++q) {
                    lxz[q][0] = lk[q][0]; lxz[q][1] = lk[q][1]; fg[q] = lk[q][2];
                }
                re4dc_lake_cell(pos, lxz, fg, up, sun, projection, viewport);
            }
#endif
        }
    }
}

#if RE4DC_WATER_PS2
// WATER_PS2: the PS2 draws no generator water (SLUS_211.34: Espgen42_Trans is `jr ra`, Espgen45_Trans only clears
// Status_flg[1] 0x20; no grid, no screen copy). Its rooms carry the water as stacked Esp08 world planes: a flat dark
// base (core texture 0xf7), two slow scrolling layers of the room's water picture 0xf2 and an animated noise layer
// (0xfe / 0xef). Those records exist only in the PS2 EFF, so they are drawn here render-side, once per drawn image,
// from the table water_ps2_table.inc (tools/d367/water/water_ps2_table.py): no PS2 record is spawned and no effect
// slot, generator, area or Rnd() state is touched. Each row is one native layer (platform/include/native_water_ps2.inc:
// an eye-centred grid of textured translucent strips, UV repeat, table fog). Rows with an area draw while that effect
// area is on (EffGetAreaState, read only); the others while the room's water generator (42 or 45) is live. The
// texture pictures are the GameCube's effect textures by id (FX_PS2_PACK puts the PS2 picture under each GameCube
// key); animated ones show the pattern AnmMove would (the record's rate over the texture's anm table, from the vblank
// clock), every RE4DC_WATER_PS2_FLIP-th picture. The FX level dial drops the extra layers (the table's level column).
#include <string.h>
#include "tpl.h"
#include "native_ui.h"
struct WaterPs2Row {
    u16 room;
    s16 area;                        // effect area (EffGetAreaState); -1: while the room's water generator is live
    f32 x, y, z, hx, hz, ry, ru, rv, su, sv;
    u32 argb;
    u8 tex, src, dst, level, rate, ptn0;
};
#include "water_ps2_table.inc"
#ifndef RE4DC_WATER_PS2_FLIP
#define RE4DC_WATER_PS2_FLIP 8
#endif
extern "C" {
unsigned re4dc_ui_frame(void);
u32 re4dc_vi_retrace_count(void);
int re4dc_fx_level_get(void) __attribute__((weak));
int re4dc_water42_live(void);   // Espgen42.cpp (WATER_PS2)
}
static unsigned s_wps2_frame = ~0U;
static u8 s_wps2_dummy;

// WATER_PS2_ROOMS: the rooms drawn, bit 0 r107, 1 r108, 2 r10a, 3 r10b, 4 r11a, 5 r11b (default 0x3f: all six, lane water16b). A room left out
// keeps today's water (r10b: WATER45_NATIVE + LAKE_RIPPLES).
#ifndef RE4DC_WATER_PS2_ROOMS
#define RE4DC_WATER_PS2_ROOMS 0x3f
#endif
static int WaterPs2RoomOn(u32 room)
{
    static const u16 kRooms[6] = {0x107, 0x108, 0x10a, 0x10b, 0x11a, 0x11b};
    for (u32 i = 0; i < 6; ++i) {
        if (kRooms[i] == room) {
            return (RE4DC_WATER_PS2_ROOMS >> i) & 1;
        }
    }
    return 0;
}

#if defined(RE4DC_WATER_PS2_EXT) && RE4DC_WATER_PS2_EXT
// WATER_PS2_EXT (lane fix-water-traps23, 2026-10-23, GitHub #55 item 2; render only, default 0): the rivers of r10c /
// r10d / r10e and the r10c waterfall curtains as the PS2 draws them (SST Esp08 world planes of the room EFF, generated
// into water_ps2_ext.inc by tools/d367/water/water_ps2_ext.py). Same native layer as the rows above; each row carries
// its plane axes, so tilted and vertical planes (the waterfall) draw too. Rows with an area draw while that effect area
// is on (EffGetAreaState, read only), the others always (these rooms have no water generator), and only while the SST
// entry's display flag is on (GetSstDispFlag: r10c switches its pools when the dam is drained). No effect slot,
// generator, area or Rnd() state is touched. WATER_PS2_EXT_ROOMS: bit 0 r10c, 1 r10d, 2 r10e (default 7).
extern "C" void re4dc_log(const char* fmt, ...);
struct WaterPs2ExtRow {
    u16 room;
    s16 area;
    f32 p[3], ax[3], az[3];   // centre, plane axis x (sprite x), plane axis z (sprite y), world
    f32 hx, hz, ru, rv, su, sv;
    u32 argb;
    u8 tex, src, dst, level, rate, ptn0, disp;   // disp: the SST entry's display flag (GetSstDispFlag); 0xff none
};
extern "C" int GetSstDispFlag(u32 id);   // est.cpp (read only)
#include "water_ps2_ext.inc"
#ifndef RE4DC_WATER_PS2_EXT_ROOMS
#define RE4DC_WATER_PS2_EXT_ROOMS 7
#endif
static int WaterPs2ExtRoomOn(u32 room)
{
    return room >= 0x10c && room <= 0x10e && ((RE4DC_WATER_PS2_EXT_ROOMS >> (room - 0x10c)) & 1);
}
#endif

#if defined(RE4DC_WATER_LAYER29) && RE4DC_WATER_LAYER29
#include "water_layer29.h"
#include "water_layer29_package.h"
#include "water_layer29_source.inc"
extern "C" void re4dc_log(const char* fmt, ...);

static_assert(unsigned(WATER29_SOURCE_VERSION) == unsigned(WATER29_VERSION), "water source metadata version");
static const Water29SourceSpan* Water29Source(u32 room)
{
    for (unsigned i = 0; i < sizeof(kWater29SourceSpans) / sizeof(kWater29SourceSpans[0]); ++i) {
        if (kWater29SourceSpans[i].room == room) return &kWater29SourceSpans[i];
    }
    return 0;
}
static uint32_t Water29SourceKey(u32 room)
{
    const Water29SourceSpan* span = Water29Source(room);
    return span ? span->source_key : 0;
}
static int Water29RoomEnabled(u32 room)
{
    if (WaterPs2RoomOn(room)) return 1;
#if defined(RE4DC_WATER_PS2_EXT) && RE4DC_WATER_PS2_EXT
    if (WaterPs2ExtRoomOn(room)) return 1;
#endif
    return 0;
}
static Water29Store s_water29_bound;
static Water29View s_water29_bound_view, s_water29_compiled_view;
static u32 s_water29_compiled_room;
static int s_water29_compiled_ready;
static u32 s_water29_refused_room;
static uint32_t s_water29_refused_source;
static int s_water29_refused;
static u32 s_water29_admission_refused, s_water29_partial;
static u32 s_water29_last_log_frame = ~0U;
static Water29Admission s_water29_last_admission;
static uint32_t s_water29_archive_incarnation, s_water29_archive_active;

// Public span adapter for other qualified owners and their source-bound rows.
// Publication copies rows, so caller mutation or backing reuse cannot affect
// the current image's selection or a queued WaterNode.
extern "C" int re4dc_water29_bind(const Water29Definition* def, unsigned available,
                                   const Water29SourceBytes* main_source, const Water29SourceBytes* ext_source)
{
    if (!def || available < sizeof(*def) || (uintptr_t) def % alignof(Water29Definition)) {
        return WATER29_REFUSED;
    }
    const uint32_t key = Water29RoomEnabled(def->room) ? Water29SourceKey(def->room) : 0;
    const Water29Result r = key ? water29Publish(&s_water29_bound, def, available, main_source, ext_source,
                                                 def->room, key, &s_water29_bound_view) : WATER29_REFUSED;
    if (r == WATER29_REFUSED) {
        s_water29_refused_room = def->room;
        s_water29_refused_source = key;
        s_water29_refused = 1;
    } else {
        s_water29_refused = 0;
    }
    return r;
}
extern "C" void re4dc_water29_retire(uint32_t owner, uint32_t incarnation)
{
    if (s_water29_bound.valid && s_water29_bound.definition.owner == owner &&
        s_water29_bound.definition.incarnation == incarnation) {
        s_water29_bound.valid = 0;
    }
}

// The loaded room archive, rather than an arbitrary row pointer, is the
// authority for this publication. Each read gets a new token even if the DVD
// allocator returns the same address. Exhaustion refuses instead of wrapping.
extern "C" void re4dc_water29_retire_archive()
{
    if (s_water29_archive_active) {
        re4dc_water29_retire(WATER29_ARCHIVE_OWNER, s_water29_archive_active);
        s_water29_archive_active = 0;
    }
    s_water29_refused = 0;
}
extern "C" int re4dc_water29_bind_archive(const void* archive, unsigned available, uint32_t room)
{
    re4dc_water29_retire_archive();
    const uint32_t key = Water29RoomEnabled(room) ? Water29SourceKey(room) : 0;
    if (s_water29_archive_incarnation == ~uint32_t(0)) {
        s_water29_refused_room = room;
        s_water29_refused_source = key;
        s_water29_refused = 1;
        return WATER29_REFUSED;
    }
    const uint32_t incarnation = ++s_water29_archive_incarnation;
    Water29PackageView member;
    const Water29Result opened = water29PackageOpen(archive, available, room, key, incarnation, &member);
    if (opened == WATER29_UNBOUND) return opened;
    if (opened == WATER29_REFUSED) {
        s_water29_refused_room = room;
        s_water29_refused_source = key;
        s_water29_refused = 1;
        return opened;
    }
    const Water29Result published = water29PackagePublish(&s_water29_bound, &member,
                                                           &s_water29_bound_view);
    if (published == WATER29_REFUSED) {
        s_water29_refused_room = room;
        s_water29_refused_source = key;
        s_water29_refused = 1;
    }
    if (published == WATER29_BOUND || published == WATER29_NO_WATER) {
        s_water29_archive_active = incarnation;
    }
    return published;
}

// Adapter: the original room table spans are copied neither at build nor per
// frame. The same loader validates their counts, extents and source identity.
static Water29Result Water29CompiledUncached(u32 room, Water29View* view)
{
    const Water29SourceSpan* span = Water29RoomEnabled(room) ? Water29Source(room) : 0;
    if (!span) {
        return water29Load(0, 0, 0, 0, room, 0, view);
    }
    const unsigned main_count = WaterPs2RoomOn(room) ? span->main_count : 0;
    if (span->main_first + main_count > sizeof(kWaterPs2) / sizeof(kWaterPs2[0])) {
        return water29Load(0, 0, 0, 0, room, 0, view);
    }
    const WaterPs2Row* main = main_count ? &kWaterPs2[span->main_first] : 0;
#if defined(RE4DC_WATER_PS2_EXT) && RE4DC_WATER_PS2_EXT
    const unsigned ext_count = WaterPs2ExtRoomOn(room) ? span->ext_count : 0;
    if (span->ext_first + ext_count > sizeof(kWaterPs2Ext) / sizeof(kWaterPs2Ext[0])) {
        return water29Load(0, 0, 0, 0, room, 0, view);
    }
    const WaterPs2ExtRow* ext = ext_count ? &kWaterPs2Ext[span->ext_first] : 0;
    const Water29SourceBytes ext_source = {kWaterPs2Ext, sizeof(kWaterPs2Ext), 0x434F4D50u, 1};
#else
    const void* ext = 0;
    unsigned ext_count = 0;
#endif
    if (!main_count && !ext_count) {
        return water29Load(0, 0, 0, 0, room, span->source_key, view);
    }
    Water29Definition def = {};
    def.magic = WATER29_MAGIC;
    def.version = WATER29_VERSION;
    def.extent = sizeof(def);
    def.room = room;
    def.source_key = span->source_key;
    def.owner = 0x434F4D50u;  // COMP: immutable compiled source tables
    def.incarnation = 1;
    def.result = WATER29_BOUND;
    def.main_count = main_count;
    def.main_bytes = main_count * sizeof(WaterPs2Row);
    def.ext_count = ext_count;
    def.ext_index_base = ext_count ? span->ext_first : 0;
#if defined(RE4DC_WATER_PS2_EXT) && RE4DC_WATER_PS2_EXT
    def.ext_bytes = ext_count * sizeof(WaterPs2ExtRow);
#endif
    def.main_rows = main;
    def.ext_rows = ext;
    const Water29SourceBytes main_source = {kWaterPs2, sizeof(kWaterPs2), 0x434F4D50u, 1};
    return water29Load(&def, sizeof(def), &main_source,
#if defined(RE4DC_WATER_PS2_EXT) && RE4DC_WATER_PS2_EXT
                       &ext_source,
#else
                       0,
#endif
                       room, span->source_key, view);
}
static Water29Result Water29Compiled(u32 room, Water29View* view)
{
    if (s_water29_compiled_ready && s_water29_compiled_room == room) {
        *view = s_water29_compiled_view;
        return view->result;
    }
    const Water29Result r = Water29CompiledUncached(room, view);
    s_water29_compiled_room = room;
    s_water29_compiled_view = *view;
    s_water29_compiled_ready = 1;
    return r;
}
static Water29Result Water29Select(u32 room, Water29View* view)
{
    const uint32_t key = Water29RoomEnabled(room) ? Water29SourceKey(room) : 0;
    if (s_water29_bound.valid && s_water29_bound.definition.room == room && key) {
        if (s_water29_bound_view.source_key == key && s_water29_bound_view.owner == s_water29_bound.definition.owner &&
            s_water29_bound_view.incarnation == s_water29_bound.definition.incarnation) {
            *view = s_water29_bound_view;
            return view->result;
        }
    }
    const Water29Result r = Water29Compiled(room, view);
    if (r == WATER29_UNBOUND && s_water29_refused && s_water29_refused_room == room &&
        s_water29_refused_source == key) {
        view->result = WATER29_REFUSED;
        return WATER29_REFUSED;
    }
    return r;
}

// Admission is per layer. A wholly refused r10b image can still draw its
// existing native GameCube generator surface; after partial publication it
// cannot be undone, so report refusal without duplicating the accepted layers.
static void Water29Finish(unsigned accepted, unsigned refused)
{
    s_water29_last_admission = refused ? (accepted ? WATER29_PARTIAL_REFUSAL : WATER29_TOTAL_REFUSAL) :
                               (accepted ? WATER29_ADMITTED : WATER29_NOT_ATTEMPTED);
    if (s_water29_last_admission != WATER29_PARTIAL_REFUSAL &&
        s_water29_last_admission != WATER29_TOTAL_REFUSAL) {
        return;
    }
    if (s_water29_last_admission == WATER29_PARTIAL_REFUSAL) {
        ++s_water29_partial;
    } else if (G_ROOM_ID == 0x10b && g_pWater45 && (g_pWater45->flag & 1) && !(g_pWater45->flag & 2)) {
        re4dc_water45_draw(g_pWater45);
    }
    const unsigned f = re4dc_ui_frame();
    if (s_water29_last_log_frame == ~0U || f - s_water29_last_log_frame >= 600U) {
        s_water29_last_log_frame = f;
        re4dc_log("water29: room=%03x accepted=%u refused=%u partial=%u total_refused=%u\n",
                  (unsigned) G_ROOM_ID, accepted, refused, (unsigned) s_water29_partial,
                  (unsigned) s_water29_admission_refused);
    }
}
#endif

// 1 when the current room has PS2 water rows (and is in WATER_PS2_ROOMS).
extern "C" int re4dc_water_ps2_rows(void)
{
#if defined(RE4DC_WATER_LAYER29) && RE4DC_WATER_LAYER29
    Water29View view;
    return Water29Select(G_ROOM_ID, &view) == WATER29_BOUND;
#else
#if defined(RE4DC_WATER_PS2_EXT) && RE4DC_WATER_PS2_EXT
    if (WaterPs2ExtRoomOn(G_ROOM_ID)) {
        return 1;
    }
#endif
    if (!WaterPs2RoomOn(G_ROOM_ID)) {
        return 0;
    }
    for (u32 i = 0; i < sizeof(kWaterPs2) / sizeof(kWaterPs2[0]); ++i) {
        if (kWaterPs2[i].room == G_ROOM_ID) {
            return 1;
        }
    }
    return 0;
#endif
}

// The pattern cEsp::AnmMove would show `tick` ticks into the loop (Anm_cnt += rate per tick; a pattern of time T
// x 32 counts), then every RE4DC_WATER_PS2_FLIP-th picture.
static u32 WaterPs2Pattern(const WaterPs2Row& r, const EspTexWk* tw, u32 n, u32 tick)
{
    const EspAnmData* anm = tw->pAnm;
    if (n <= 1 || anm == NULL || r.rate == 0) {
        return 0;
    }
    u32 frames = anm->Frames;
    if (frames == 0 || frames > n) {
        frames = n;
    }
    u32 total = 0;
    for (u32 i = 0; i < frames; ++i) {
        total += anm->Data_num ? anm->Frame_cnt[anm->Frames + i] : 1;
    }
    if (total == 0) {
        return 0;
    }
    u32 units = (tick * (u32) r.rate) % (total * 32u);
    u32 p = 0;
    for (; p < frames; ++p) {
        const u32 t = (anm->Data_num ? anm->Frame_cnt[anm->Frames + p] : 1) * 32u;
        if (units < t) {
            break;
        }
        units -= t;
    }
    p = (p + r.ptn0) % frames;
    if (frames >= RE4DC_WATER_PS2_FLIP) {
        p -= p % RE4DC_WATER_PS2_FLIP;
    }
    return p;
}

// OT callback (layer 0x10): the room's PS2 water layers, bottom-up, once per drawn image.
extern "C" void re4dc_water_ps2_draw(void*)
{
    const unsigned f = re4dc_ui_frame();
    if (f == s_wps2_frame) {
        return;
    }
    s_wps2_frame = f;
#if defined(RE4DC_WATER_LAYER29) && RE4DC_WATER_LAYER29
    s_water29_last_admission = WATER29_NOT_ATTEMPTED;
    Water29View selected;
    if (Water29Select(G_ROOM_ID, &selected) != WATER29_BOUND) {
        return;
    }
    unsigned accepted_count = 0, refused_count = 0;
#endif
    const int live = (g_pWater45 != NULL && (g_pWater45->flag & 1) && !(g_pWater45->flag & 2)) || re4dc_water42_live();
    const int level = re4dc_fx_level_get ? re4dc_fx_level_get() : 0;
    CameraCurrentProjection();
    Re4dcWaterLayer L;
    memset(&L, 0, sizeof(L));
    GXGetProjectionv(L.projection);
    GXGetViewportv(L.viewport);
    const Mtx& vm = pG->Cam.v_mat;
    Mtx vi;
    PSMTXInverse(vm, vi);
    const f32 ex = vi[0][3], ez = vi[2][3];
    const u32 tick = re4dc_vi_retrace_count() >> 1;
    GXColor fin = {0xFF, 0xFF, 0xFF, 0xFF};
    const int fin_on = EffIsSetFinalCol();
    if (fin_on) {
        EffGetFinalCol(&fin);
    }
#if defined(RE4DC_WATER_LAYER29) && RE4DC_WATER_LAYER29
    const WaterPs2Row* main_rows = selected.main_rows;
    const unsigned main_count = selected.main_count;
    for (u32 i = 0; i < main_count; ++i) {
        const WaterPs2Row& r = main_rows[i];
#else
    for (u32 i = 0; i < sizeof(kWaterPs2) / sizeof(kWaterPs2[0]); ++i) {
        const WaterPs2Row& r = kWaterPs2[i];
#endif
        if (r.room != G_ROOM_ID || level > r.level) {
            continue;
        }
        if (r.area < 0 ? !live : !EffGetAreaState(r.area)) {
            continue;
        }
        memset(&L.image, 0, sizeof(L.image));
        if (r.tex != 0xF7) {   // 0xf7: the core's white picture, drawn untextured
            const EspTexWk* tw = &g_pEspSys->Esp_tex_tbl[r.tex];
            if (tw->Owner == 0xD2 || tw->pTpl == NULL || tw->pTpl->numDescriptors == 0) {
                continue;
            }
            const TEXDescriptor* td = TEXGet(tw->pTpl, WaterPs2Pattern(r, tw, tw->pTpl->numDescriptors, tick));
            const TEXHeader* th = td->textureHeader;
            L.image.pixels = th->data;
            L.image.width = th->width;
            L.image.height = th->height;
            L.image.format = th->format;
            L.image.palette_format = 0xffffffffU;
            if (td->CLUTHeader) {
                L.image.palette = td->CLUTHeader->data;
                L.image.palette_format = td->CLUTHeader->format;
                L.image.palette_bytes = td->CLUTHeader->numEntries * 2;
            }
        }
        const f32 c = cosf(r.ry), s = sinf(r.ry);
        Mtx m = {{c, 0.0f, s, r.x}, {0.0f, 1.0f, 0.0f, r.y}, {-s, 0.0f, c, r.z}};
        Mtx mv;
        PSMTXConcat(vm, m, mv);
        memcpy(L.mv, mv, sizeof(L.mv));
        const f32 dx = ex - r.x, dz = ez - r.z;
        L.eye_x = c * dx - s * dz;
        L.eye_z = s * dx + c * dz;
        L.half_x = r.hx;
        L.half_z = r.hz;
        L.u_per_mm = r.ru;
        L.v_per_mm = r.rv;
        L.u0 = r.su * (f32) tick;
        L.u0 -= (f32) (s32) L.u0;
        L.v0 = r.sv * (f32) tick;
        L.v0 -= (f32) (s32) L.v0;
        u32 a = r.argb >> 24, cr = (r.argb >> 16) & 0xFF, cg = (r.argb >> 8) & 0xFF, cb = r.argb & 0xFF;
        if (fin_on) {
            cr = cr * fin.r >> 8;
            cg = cg * fin.g >> 8;
            cb = cb * fin.b >> 8;
            a = a * fin.a >> 8;
        }
        L.argb = a << 24 | cr << 16 | cg << 8 | cb;
        L.src = r.src;
        L.dst = r.dst;
#if defined(RE4DC_WATER_LAYER29) && RE4DC_WATER_LAYER29
        const int accepted = re4dc_water_layer(&L);
        if (!accepted) {
            ++s_water29_admission_refused;
            ++refused_count;
        } else {
            ++accepted_count;
        }
#else
        re4dc_water_layer(&L);
#endif
    }
#if defined(RE4DC_WATER_PS2_EXT) && RE4DC_WATER_PS2_EXT
#if defined(RE4DC_WATER_LAYER29) && RE4DC_WATER_LAYER29
    if (!selected.ext_count) {
        Water29Finish(accepted_count, refused_count);
        return;
    }
    const WaterPs2ExtRow* ext_rows = selected.ext_rows;
    const unsigned ext_count = selected.ext_count;
    const unsigned ext_index_base = selected.ext_index_base;
#else
    if (!WaterPs2ExtRoomOn(G_ROOM_ID)) {
        return;
    }
#endif
    static u32 s_ext_room = 0, s_ext_missing = 0, s_ext_on = ~0U;   // missing pictures once per room; drawn-row mask
    if (s_ext_room != G_ROOM_ID) {
        s_ext_room = G_ROOM_ID;
        s_ext_missing = 0;
        s_ext_on = ~0U;
    }
    u32 on_mask = 0;
    const f32 ey = vi[1][3];
#if defined(RE4DC_WATER_LAYER29) && RE4DC_WATER_LAYER29
    for (u32 i = 0; i < ext_count; ++i) {
        const WaterPs2ExtRow& r = ext_rows[i];
#else
    for (u32 i = 0; i < sizeof(kWaterPs2Ext) / sizeof(kWaterPs2Ext[0]); ++i) {
        const WaterPs2ExtRow& r = kWaterPs2Ext[i];
#endif
        if (r.room != G_ROOM_ID || level > r.level) {
            continue;
        }
        if ((r.area >= 0 && !EffGetAreaState(r.area)) || (r.disp != 0xFF && !GetSstDispFlag(r.disp))) {
            continue;
        }
#if defined(RE4DC_WATER_LAYER29) && RE4DC_WATER_LAYER29
        on_mask |= 1u << ((i + ext_index_base) & 31);
#else
        on_mask |= 1u << (i & 31);
#endif
        memset(&L.image, 0, sizeof(L.image));
        if (r.tex != 0xF7) {
            const EspTexWk* tw = &g_pEspSys->Esp_tex_tbl[r.tex];
            if (tw->Owner == 0xD2 || tw->pTpl == NULL || tw->pTpl->numDescriptors == 0) {
#if defined(RE4DC_WATER_LAYER29) && RE4DC_WATER_LAYER29
                if (!(s_ext_missing & (1u << ((i + ext_index_base) & 31)))) {
                    s_ext_missing |= 1u << ((i + ext_index_base) & 31);
#else
                if (!(s_ext_missing & (1u << (i & 31)))) {
                    s_ext_missing |= 1u << (i & 31);
#endif
                    re4dc_log("water ext: room=%03x row %u texture %02x not loaded (row skipped)\n", (unsigned) G_ROOM_ID,
                              (unsigned) i, (unsigned) r.tex);
                }
                continue;
            }
            WaterPs2Row pr;
            memset(&pr, 0, sizeof(pr));
            pr.rate = r.rate;
            pr.ptn0 = r.ptn0;
            const TEXDescriptor* td = TEXGet(tw->pTpl, WaterPs2Pattern(pr, tw, tw->pTpl->numDescriptors, tick));
            const TEXHeader* th = td->textureHeader;
            L.image.pixels = th->data;
            L.image.width = th->width;
            L.image.height = th->height;
            L.image.format = th->format;
            L.image.palette_format = 0xffffffffU;
            if (td->CLUTHeader) {
                L.image.palette = td->CLUTHeader->data;
                L.image.palette_format = td->CLUTHeader->format;
                L.image.palette_bytes = td->CLUTHeader->numEntries * 2;
            }
        }
        const f32 ny[3] = {r.az[1] * r.ax[2] - r.az[2] * r.ax[1], r.az[2] * r.ax[0] - r.az[0] * r.ax[2],
                           r.az[0] * r.ax[1] - r.az[1] * r.ax[0]};
        Mtx m = {{r.ax[0], ny[0], r.az[0], r.p[0]}, {r.ax[1], ny[1], r.az[1], r.p[1]}, {r.ax[2], ny[2], r.az[2], r.p[2]}};
        Mtx mv;
        PSMTXConcat(vm, m, mv);
        memcpy(L.mv, mv, sizeof(L.mv));
        const f32 dx = ex - r.p[0], dy = ey - r.p[1], dz = ez - r.p[2];
        L.eye_x = dx * r.ax[0] + dy * r.ax[1] + dz * r.ax[2];
        L.eye_z = dx * r.az[0] + dy * r.az[1] + dz * r.az[2];
        L.half_x = r.hx;
        L.half_z = r.hz;
        L.u_per_mm = r.ru;
        L.v_per_mm = r.rv;
        L.u0 = r.su * (f32) tick;
        L.u0 -= (f32) (s32) L.u0;
        L.v0 = r.sv * (f32) tick;
        L.v0 -= (f32) (s32) L.v0;
        u32 a = r.argb >> 24, cr = (r.argb >> 16) & 0xFF, cg = (r.argb >> 8) & 0xFF, cb = r.argb & 0xFF;
        if (fin_on) {
            cr = cr * fin.r >> 8;
            cg = cg * fin.g >> 8;
            cb = cb * fin.b >> 8;
            a = a * fin.a >> 8;
        }
        L.argb = a << 24 | cr << 16 | cg << 8 | cb;
        L.src = r.src;
        L.dst = r.dst;
#if defined(RE4DC_WATER_LAYER29) && RE4DC_WATER_LAYER29
        const int accepted = re4dc_water_layer(&L);
        if (!accepted) {
            ++s_water29_admission_refused;
            ++refused_count;
        } else {
            ++accepted_count;
        }
#else
        re4dc_water_layer(&L);
#endif
    }
    if (on_mask != s_ext_on) {   // the rows whose area / display flag is on (table index bits), on each change
        s_ext_on = on_mask;
        re4dc_log("water ext: room=%03x rows on %08x\n", (unsigned) G_ROOM_ID, (unsigned) on_mask);
    }
#endif
#if defined(RE4DC_WATER_LAYER29) && RE4DC_WATER_LAYER29
    Water29Finish(accepted_count, refused_count);
#endif
}

// EspgenTrans (espgen.cpp), once per drawn image: the room's PS2 water as one OT entry (layer 0x10, the GameCube water
// generators' layer). Render only.
extern "C" void re4dc_water_ps2_queue(void)
{
    // No entry while the frame's prim buffer is absent (room entry): AddOtDirect would fail and log a PrimBuffer
    // OVERFLOW pair per image, and those log writes shift the room-entry wall time (r10b STRICT, water16).
    const u32 prim = (u32) pG->prim_cnt;
    if (prim < RE4_MEM_LO || prim > RE4_MEM_HI) {
        return;
    }
    if (re4dc_water_ps2_rows()) {
        AddOtDirect(0x10, &s_wps2_dummy, (void (*)()) re4dc_water_ps2_draw, 1, 0x80, NULL, 0.0f);
    }
}
#endif

// The surface's OT entry (layer 0x10, as Espgen45_Trans queues Espgen45_TransSub): drawn in the render pass of the
// image being built. Espgen45_Trans and the logic-only coarse pass (espgen.cpp) call it; render only.
extern "C" void re4dc_water45_queue(EspgenWork* w)
{
#if RE4DC_WATER_PS2
#if defined(RE4DC_WATER_LAYER29) && RE4DC_WATER_LAYER29
    Water29View selected;
    const Water29Result result = Water29Select(G_ROOM_ID, &selected);
    if (result == WATER29_BOUND || result == WATER29_NO_WATER) {
        return;   // qualified source definition owns this room's water result
    }
#else
    if (re4dc_water_ps2_rows()) {
        return;   // WATER_PS2: the PS2 layers replace the GameCube surface (re4dc_water_ps2_queue)
    }
#endif
#endif
    if (G_ROOM_ID == 0x10b && (w->flag & 1) && !(w->flag & 2)) {
        AddOtDirect(0x10, w, (void (*)()) re4dc_water45_draw, 1, 0x80, NULL, 0.0f);
    }
}

// EspSpriteEmit (esp_sub.cpp): 1 when the r10b surface is drawn natively this frame, the eye is above the plane and all
// four view-space corners are under it: the GameCube's water Z hides such a sprite (drawn after the water's OT layer).
extern "C" int re4dc_water45_hides(const f32 (*corner)[3])
{
    EspgenWork* w = g_pWater45;
    if (w == NULL || !(w->flag & 1) || (w->flag & 2) || G_ROOM_ID != 0x10b) {
        return 0;
    }
    Espgen42Work* p = (Espgen42Work*) w->work;
    // The plane y = h in view space: normal n = R (0, 1, 0), offset d = -(n . (R (0, h, 0) + t)); a point's side is
    // n . x + d (> 0: above). The eye is the view origin: above when d > 0.
    const Mtx& V = pG->Cam.v_mat;
    const f32 h = p->mat[1][3];
    const f32 nx = V[0][1], ny = V[1][1], nz = V[2][1];
    const f32 d = -(nx * (V[0][1] * h + V[0][3]) + ny * (V[1][1] * h + V[1][3]) + nz * (V[2][1] * h + V[2][3]));
    if (!(d > 0.0f)) {
        return 0;
    }
    for (int i = 0; i < 4; ++i) {
        if (nx * corner[i][0] + ny * corner[i][1] + nz * corner[i][2] + d >= 0.0f) {
            return 0;
        }
    }
    return 1;
}
#endif

// EspgenTransTbl entry: queues Espgen45_TransSub in OT layer 0x10 (drawn after the opaque scene) and
// clears Status_flg[1] bit 0x20 (the "override parameters changed this frame" flag).
void Espgen45_Trans(EspgenWork* w)
{
    if ((w->flag & 1) && !(w->flag & 2)) {
#if !RE4DC_WATER45_LEAN
        AddOtDirect(0x10, w, (void (*)()) Espgen45_TransSub, 1, 0x80, NULL, 0.0f);
#elif RE4DC_WATER45_NATIVE
        re4dc_water45_queue(w);
#endif
    }
    pG->Status_flg[1] &= ~0x20;
}

// Loads indirect texture matrix 1 for the bump stage: S scale indS*0.001+0.01, T scale
// indT*0.007+0.07 (or the Esp4cWork Shimmer_pow1/2 when the parameter override is on).
void SetIndMtx_801291F4(Espgen42Work* p)
{
    f32 m[2][3];
    s16 indS;
    s16 indT;

    if (g_bSetParam == 0) {
        indS = p->indS;
    } else {
        indS = g_Free.Shimmer_pow1;
    }
    if (g_bSetParam == 0) {
        indT = p->indT;
    } else {
        indT = g_Free.Shimmer_pow2;
    }
    m[0][0] = (f32) indS * 0.001f + 0.01f;
    m[0][1] = 0.0f;
    m[0][2] = 0.0f;
    m[1][0] = 0.0f;
    m[1][1] = (f32) indT * 0.007f + 0.07f;
    m[1][2] = 0.0f;
    GXSetIndTexMtx(1, m, 1);
}

// Border quads of the unbounded surface: grid half sizes in grid units; the far edge is
// g45_mul cells out, the near edge g45_mul2, normals follow SetWaterWork45's slope.
#define G45_NXH ((f32) (int) (p->nx >> 1))
#define G45_NXHN ((f32) (-(int) p->nx / 2))
#define G45_NX ((f32) (int) p->nx)
#define G45_NXN ((f32) (-(int) p->nx))
#define G45_NY ((f32) (int) p->ny)
#define G45_NYN ((f32) (-(int) p->ny))
#define G45_NYU ((f32) p->ny)

// One vertex = one inline with all eight values as parameters, normal first: every value is evaluated
// before the first FIFO store (one (f32)(-ny) conversion serves the normal z and the position z), and the
// ny conversion precedes the nx one because the normal arguments come first.
static inline void Vtx45(f32 nx, f32 ny, f32 nz, f32 x, f32 y, f32 z, f32 s, f32 t)
{
    GXPosition3f32(x, y, z);
    GXNormal3f32(nx, ny, nz);
    GXTexCoord2f32(s, t);
}

// Draws the water: lights a dummy model at the surface (5 cloth lights + ambient amb, colour overrides
// applied), copies the screen (below the 56 px border) into draw temp buffer 0xE as the refraction
// texture projected with the camera, adds the bump indirect stage (SetIndMtx), the environment
// specular texture (p->texId, view-space normals) and the mask texture when flag bit 1; then, unless
// flag bit 0, four far border quads (g45_mul cells out) and finally the grid display list.
void Espgen45_TransSub(EspgenWork* w)
{
    static f32 g45_mul = 15.0f;
    static f32 g45_mul2 = 1.0f;
    GxStageWork* st;
    Espgen42Work* p;
    void* buf;
    s32 stage;

    if (!(w->flag & 1) || (w->flag & 2)) {
        return;
    }
    st = &pG->gxStage;
    p = (Espgen42Work*) w->work;
    st->tevStage = 0;
    st->texMap = 0;
    st->texCoord = 0;
    CameraCurrentProjection();
    GXSetCullMode(0);
    GXSetZMode(1, 3, 1);
    cModel model;
    u8 modelPad[0x320 - sizeof(cModel)];
    PSMTXIdentity(model.mat);
    {
        static const Vec p0 = {0.0f, 0.0f, 0.0f};
        static const Vec p1 = {10000.0f, 10000.0f, 10000.0f};
        model.LightInfo.init2(1, 0, &p0, &p1, 0x10);
    }
    model.pos.x = p->mat[0][3];
    model.pos.y = p->mat[1][3];
    model.pos.z = p->mat[2][3];
    LightMgr.setClothN(&model, 5);
    GXColor amb = p->amb;
    if (g_bColorOverWrite == 1) {
        amb.r = (u8) (g_sr * 255.0f);
        amb.g = (u8) (g_sg * 255.0f);
        amb.b = (u8) (g_sb * 255.0f);
        amb.a = (u8) (g_sa * 255.0f);
    } else if (g_bColorMul == 1) {
        amb.r = (u8) ((f32) amb.r * g_sr);
        amb.g = (u8) ((f32) amb.g * g_sg);
        amb.b = (u8) ((f32) amb.b * g_sb);
        amb.a = (u8) ((f32) amb.a * g_sa);
    }
    commonWaterLightSet(model.LightInfo.pLight, 5, amb.a);
    GXColor white;
    white.r = white.g = white.b = white.a = 0xFF;
    GXSetChanMatColor(4, white);
    GXSetChanAmbColor(4, amb);
    Mtx nrm;
    Mtx mv;
    Mtx tmp;
    PSMTXConcat(pG->Cam.v_mat, p->mat, mv);
    PSMTXCopy(p->mat, tmp);
    tmp[1][1] = p->size * 0.05f + 100.0f;
    PSMTXConcat(pG->Cam.v_mat, tmp, tmp);
    PSMTXInverse(tmp, nrm);
    PSMTXTranspose(nrm, nrm);
    GXLoadNrmMtxImm(nrm, 0);
    GXLoadPosMtxImm(mv, 0);
    GXSetCurrentMtx(0);
    GXSetBlendMode(1, 4, 5, 0);
    buf = GetDrawTmpBufAddr(0xE);
    if (buf == NULL) {
        pLog->warn(0, 0, "Espgen45() : not enough memory");
        return;
    }
    {
        f32 ofs = 56.0f;
        GXSetTexCopySrc(0, (u32) ofs, (u32) Screen.width, (u32) (Screen.height - ofs));
        GXSetTexCopyDst((u32) Screen.width / 2, (u32) ((f32) ((u32) Screen.height / 2) - ofs), 6, 1);
        GXCopyTex(buf, 0);
        GXPixModeSync();
        GXInvalidateTexAll();
        {
            GXTexObj tex;
            Mtx tm;
            Mtx pm;
            GXInitTexObj(&tex, buf, (u32) Screen.width / 2, (u32) ((f32) ((u32) Screen.height / 2) - ofs), 6, 0, 0, 0);
            GXLoadTexObj(&tex, st->texMap);
            C_MTXLightPerspective(pm, pG->Cam.param.fovy, 1.3333334f, 0.5f, -0.6666667f, 0.5f, 0.5f);
            PSMTXConcat(pm, mv, tm);
            GXLoadTexMtxImm(tm, 0x1E, 0);
            GXSetTexCoordGen(st->texCoord, 0, 0, 0x1E);
            GXColor col = p->col;
            if (g_bColorOverWrite == 1) {
                col.r = g_r;
                col.g = g_g;
                col.b = g_b;
                col.a = g_a;
            } else if (g_bColorMul == 1) {
                col.r = (u8) ((f32) col.r * (f32) (int) g_r / 255.0f);
                col.g = (u8) ((f32) col.g * (f32) (int) g_g / 255.0f);
                col.b = (u8) ((f32) col.b * (f32) (int) g_b / 255.0f);
                col.a = (u8) ((f32) col.a * (f32) (int) g_a / 255.0f);
            }
            GXSetTevColor(1, col);
            GXSetTevOrder(st->tevStage, st->texCoord, st->texMap, 4);
            GXSetTevColorIn(st->tevStage, 0xF, 2, 8, 0xF);
            if (p->stages > 0) {
                GXSetTevColorOp(st->tevStage, 0, 0, 2, 1, 0);
            } else {
                GXSetTevColorOp(st->tevStage, 0, 0, 0, 1, 0);
            }
            GXSetTevAlphaIn(st->tevStage, 7, 7, 7, 5);
            GXSetTevAlphaOp(st->tevStage, 0, 0, 0, 1, 0);
            stage = st->tevStage;
            st->tevStage++;
            st->texMap++;
            st->texCoord++;
            GXInitTexObj(&tex, p->bump, p->nx, p->ny, 1, 0, 0, 0);
            GXLoadTexObj(&tex, st->texMap);
            GXSetNumIndStages(1);
            GXSetTexCoordGen(st->texCoord, 1, 4, 0x3C);
            GXSetIndTexOrder(0, st->texCoord, st->texMap);
            GXSetIndTexCoordScale(0, 0, 0);
            SetIndMtx_801291F4(p);
            GXSetTevIndWarp(stage, 0, 1, 0, 1);
            st->texCoord++;
            st->texMap++;
            if (p->stages > 1) {
                GXSetTevOrder(st->tevStage, st->texCoord, st->texMap, 4);
                GXSetTevColorIn(st->tevStage, 0xF, 0, 0, 0xF);
                GXSetTevColorOp(st->tevStage, 0, 0, 2, 1, 0);
                GXSetTevAlphaIn(st->tevStage, 7, 7, 7, 5);
                GXSetTevAlphaOp(st->tevStage, 0, 0, 0, 1, 0);
                st->tevStage++;
                st->texMap++;
                st->texCoord++;
            }
            if (p->stages > 2) {
                GXSetTevOrder(st->tevStage, st->texCoord, st->texMap, 4);
                GXSetTevColorIn(st->tevStage, 0xF, 0, 0, 0xF);
                GXSetTevColorOp(st->tevStage, 0, 0, 2, 1, 0);
                GXSetTevAlphaIn(st->tevStage, 7, 7, 7, 5);
                GXSetTevAlphaOp(st->tevStage, 0, 0, 0, 1, 0);
                st->tevStage++;
                st->texMap++;
                st->texCoord++;
            }
        }
        {
            GXTexObj* tex2 = EspGetTexObj(p->texId, 0);
            if (tex2 == NULL) {
                pLog->err(0, 0, "Espgen45 : TexId[%x] invalid.", p->texId);
                tex2 = &Specular;
            }
            GXLoadTexObj(tex2, st->texMap);
        }
        {
            Mtx ms;
            Mtx mt;
            Mtx m3;
            PSMTXCopy(pG->Cam.v_mat, m3);
            PSMTXInverse(m3, m3);
            PSMTXTranspose(m3, m3);
            PSMTXScale(ms, 1.0f, -0.5f, 0.0f);
            PSMTXTrans(mt, 0.5f, 0.5f, 1.0f);
            PSMTXConcat(ms, m3, m3);
            PSMTXConcat(mt, m3, m3);
            GXLoadTexMtxImm(m3, 0x21, 0);
        }
        GXSetTexCoordGen(st->texCoord, 0, 1, 0x21);
        GXSetTevOrder(st->tevStage, st->texCoord, st->texMap, 4);
        GXSetTevColorIn(st->tevStage, 0xF, 0xA, 9, 0);
        GXSetTevColorOp(st->tevStage, 0, 0, 0, 1, 0);
        GXSetTevAlphaIn(st->tevStage, 7, 7, 7, 5);
        GXSetTevAlphaOp(st->tevStage, 0, 0, 0, 1, 0);
        st->tevStage++;
        st->texMap++;
        st->texCoord++;
        if ((IGet(g_bSetParam) == 1 && (g_Free.flag & 2)) || (IGet(g_bSetParam) == 0 && (p->flag & 2))) {
            u8 texId;
            EspTexWk* tw;
            if (g_bSetParam == 1) {
                texId = g_Free.Mask_Tex;
            } else {
                texId = p->Mask_Tex;
            }
            tw = EspGetTexWk(texId, 1);
            if (tw == NULL || tw->Owner == 0xD2) {
                pLog->err(0, 0, "ESP : Mask_TexId[%x] no data", texId);
            } else {
                // the same frame slots as the first block's tex/tm: PRE shares their addresses
                GXTexObj tex;
                GXTlutObj tlut;
                TEXDescriptor* td = TEXGet(tw->pTpl, 0);
                TEXHeader* th = td->textureHeader;

                if (th->format == 8 || th->format == 9) {
                    GXInitTexObjCI(&tex, th->data, th->width, th->height, th->format, 0, 0, 0, 1);
                    GXInitTlutObj(&tlut, td->CLUTHeader->data, td->CLUTHeader->format, td->CLUTHeader->numEntries);
                    GXLoadTlut(&tlut, 1);
                } else {
                    GXInitTexObj(&tex, th->data, th->width, th->height, th->format, 0, 0, 0);
                }
                GXLoadTexObj(&tex, st->texMap);
                GXLoadTexMtxImm(tw->mtx, 0x21, 1);
                GXSetTexCoordGen(st->texCoord, 1, 4, 0x21);
                GXSetTevOrder(st->tevStage, st->texCoord, st->texMap, 4);
                GXSetTevColorIn(st->tevStage, 0xF, 0xF, 0xF, 0);
                GXSetTevColorOp(st->tevStage, 0, 0, 0, 1, 0);
                GXSetTevAlphaIn(st->tevStage, 7, 4, 5, 7);
                GXSetTevAlphaOp(st->tevStage, 0, 0, 0, 1, 0);
                st->tevStage++;
                st->texMap++;
                st->texCoord++;
            }
        }
        GXSetNumTevStages(st->tevStage);
        GXSetNumTexGens(st->texCoord);
        if (!(p->flag & 1)) {
            Vec n;
            f32 hx;
            f32 hy;
            f32 inx;
            f32 iny;
            f32 far;

            GXClearVtxDesc();
            GXSetVtxDesc(9, 1);
            GXSetVtxDesc(0xA, 1);
            GXSetVtxDesc(0xD, 1);
            GXSetVtxAttrFmt(0, 9, 1, 4, 0);
            GXSetVtxAttrFmt(0, 0xA, 0, 4, 0);
            GXSetVtxAttrFmt(0, 0xD, 1, 4, 0);
            hx = G45_NXH;
            hy = (f32) (int) (p->ny >> 1);
            inx = 1.0f / G45_NX * inv_mul;
            iny = 1.0f / G45_NY * inv_mul;
            far = g45_mul / g45_mul2;
            {
                GXBegin(0x80, 0, 4);
                f32 nx = (g45_mul2 * 0.0f - hx) * inx;
                Vtx45(nx, 0.25f, (G45_NYN * g45_mul2 + hy) * iny * far, G45_NXHN * g45_mul, 0.0f, G45_NYN * 0.5f * g45_mul, 0.0f, 0.0f);
                f32 nz = (g45_mul2 * 0.0f - hy) * iny;
                Vtx45((G45_NX * g45_mul2 - hx) * inx, 0.25f, (G45_NYN * g45_mul2 + hy) * iny * far, G45_NXH * g45_mul, 0.0f, G45_NYN * 0.5f * g45_mul, 1.0f, 0.0f);
                Vtx45((G45_NX * g45_mul2 - hx) * inx, 0.25f, nz, G45_NXH * g45_mul2, 0.0f, G45_NYN * 0.5f * g45_mul2, 1.0f, 1.0f);
                n.x = nx;
                n.y = 0.25f;
                n.z = nz;
                Vtx45(n.x, n.y, n.z, G45_NXHN * g45_mul2, 0.0f, G45_NYN * 0.5f * g45_mul2, 0.0f, 1.0f);
            }
            {
                GXBegin(0x80, 0, 4);
                f32 nz = (g45_mul2 * 0.0f - hy) * iny;
                Vtx45((G45_NX * g45_mul2 - hx) * inx, 0.25f, nz, G45_NXH * g45_mul2, 0.0f, G45_NYN * 0.5f * g45_mul2, 0.0f, 0.0f);
                Vtx45((G45_NX * g45_mul2 - hx) * inx * far, 0.25f, nz, G45_NXH * g45_mul, 0.0f, G45_NYN * 0.5f * g45_mul, 1.0f, 0.0f);
                Vtx45((G45_NX * g45_mul2 - hx) * inx * far, 0.25f, (G45_NY * g45_mul2 - hy) * iny, G45_NXH * g45_mul, 0.0f, G45_NYU * 0.5f * g45_mul, 1.0f, 1.0f);
                n.x = (G45_NX * g45_mul2 - hx) * inx;
                n.y = 0.25f;
                n.z = (G45_NY * g45_mul2 - hy) * iny;
                Vtx45(n.x, n.y, n.z, G45_NXH * g45_mul2, 0.0f, G45_NYU * 0.5f * g45_mul2, 0.0f, 1.0f);
            }
            {
                GXBegin(0x80, 0, 4);
                f32 nx = (g45_mul2 * 0.0f - hx) * inx;
                Vtx45(nx, 0.25f, (G45_NY * g45_mul2 - hy) * iny, G45_NXHN * g45_mul2, 0.0f, G45_NYU * 0.5f * g45_mul2, 0.0f, 1.0f);
                n.x = nx;
                Vtx45((G45_NX * g45_mul2 - hx) * inx, 0.25f, (G45_NY * g45_mul2 - hy) * iny, G45_NXH * g45_mul2, 0.0f, G45_NYU * 0.5f * g45_mul2, 1.0f, 1.0f);
                Vtx45((G45_NX * g45_mul2 - hx) * inx, 0.25f, (G45_NY * g45_mul2 - hy) * iny * far, G45_NXH * g45_mul, 0.0f, G45_NYU * 0.5f * g45_mul, 1.0f, 0.0f);
                n.z = (G45_NY * g45_mul2 - hy) * iny * far;
                n.y = 0.25f;
                Vtx45(n.x, n.y, n.z, G45_NXHN * g45_mul, 0.0f, G45_NYU * 0.5f * g45_mul, 0.0f, 0.0f);
            }
            {
                GXBegin(0x80, 0, 4);
                f32 nz = (g45_mul2 * 0.0f - hy) * iny;
                f32 nx = (g45_mul2 * 0.0f - hx) * inx;
                Vtx45((G45_NXN * g45_mul2 + hx) * inx * far, 0.25f, nz, G45_NXHN * g45_mul, 0.0f, G45_NYN * 0.5f * g45_mul, 0.0f, 0.0f);
                Vtx45(nx, 0.25f, nz, G45_NXHN * g45_mul2, 0.0f, G45_NYN * 0.5f * g45_mul2, 1.0f, 0.0f);
                Vtx45(nx, 0.25f, (G45_NY * g45_mul2 - hy) * iny, G45_NXHN * g45_mul2, 0.0f, G45_NYU * 0.5f * g45_mul2, 1.0f, 1.0f);
                n.x = (G45_NXN * g45_mul2 + hx) * inx * far;
                n.y = 0.25f;
                n.z = (G45_NY * g45_mul2 - hy) * iny;
                Vtx45(n.x, n.y, n.z, G45_NXHN * g45_mul, 0.0f, G45_NYU * 0.5f * g45_mul, 0.0f, 1.0f);
            }
        }
        GXClearVtxDesc();
        GXSetVtxDesc(9, 3);
        GXSetVtxDesc(10, 3);
        GXSetVtxDesc(13, 1);
        GXSetVtxAttrFmt(0, 9, 1, 4, 0);
        GXSetVtxAttrFmt(0, 10, 0, 4, 0);
        GXSetVtxAttrFmt(0, 13, 1, 4, 0);
        GXSetArray(9, p->pos, sizeof(Vec));
        GXSetArray(10, p->nrm, sizeof(Vec));
        GXCallDisplayList(p->dl, p->dlSize);
        GXSetNumTevStages(1);
        GXSetNumTexGens(0);
        GXSetNumIndStages(0);
        GXSetTevDirect(0);
        GXSetTevDirect(1);
    }
}

// Allocates a controller from the pool and builds a water surface on it (SetWaterWork45).
// Dead-stripped from the DOL (string kept, no pool: STRIP_UNUSED): pulls a generator and sets the
// surface up.
static EspgenWork* SetWater(Vec* pos, Vec* rot, f32 size, u32 nx, u32 ny, f32 rate)
{
    EspgenWork* w;

    if (PullEspgen(&w) == 0) {
        pLog->err(0, 0, "Espgen45 : work pull failed");
        return NULL;
    }
    return SetWaterWork45(w, pos, rot, size, nx, ny, rate);
}

// Builds the surface work: id 0x45, nx x ny cells of `size` units, matrix (with the rotation
// override), allocates hA/hB/pos/nrm/bump and the strip display list (memory group 13), fills the
// zig-zag triangle strip indices/UVs, the flat grid positions (random +-0.2 ripple), the sloped
// normals and zero edge heights. Returns NULL (controller released) when an allocation fails.
EspgenWork* SetWaterWork45(EspgenWork* w, Vec* pos, Vec* rot, f32 size, u32 nx, u32 ny, f32 rate)
{
    Espgen42Work* p = (Espgen42Work*) w->work;
    Mtx m;
    u32 n;
    u8* d;
    int i;
    int j;
    int k;
    f32 fx;
    f32 fy;

    w->id = 0x45;
    p->nx = nx;
    p->ny = ny;
    p->size = size;
    p->damp = 0.05f;
    p->spread = 0.95f;
    p->pos0 = *pos;
    if (IGet(g_bSetParam) == 0) {
        PSMTXScale(p->mat, p->size, p->size * 0.05f + 100.0f, p->size);
    } else {
        RotMatrix(p->mat, &g_Free.ang);
        PSMTXScale(m, p->size, p->size * 0.05f + 100.0f, p->size);
        PSMTXConcat(p->mat, m, p->mat);
    }
    PSMTXTransApply(p->mat, p->mat, p->pos0.x, p->pos0.y, p->pos0.z);
    PSMTXInverse(p->mat, p->inv);
    if (rate == 0.0f) {
        rate = 0.0001f;
    }
    p->mat[1][1] *= rate;
#if RE4DC_WATER45_GRID_SKIP
    p->hA = NULL;
    p->hB = NULL;
    p->pos = NULL;
#else
    n = sizeof(f32) * (p->nx + 1) * (p->ny + 1);
#line 1452 "D:/Bio4/Prog/espgen45.cpp"
    p->hA = (f32*) MEM_ALLOC(n, 1, 13);
    if (p->hA == NULL) {
        goto nomem;
    }
    memclr_asm(p->hA, n);
#line 1459 "D:/Bio4/Prog/espgen45.cpp"
    p->hB = (f32*) MEM_ALLOC(n, 1, 13);
    if (p->hB == NULL) {
        goto nomem;
    }
    memclr_asm(p->hB, n);
    n = sizeof(Vec) * (p->nx + 1) * (p->ny + 1);
#line 1468 "D:/Bio4/Prog/espgen45.cpp"
    p->pos = (Vec*) MEM_ALLOC(n, 1, 13);
    if (p->pos == NULL) {
        goto nomem;
    }
    memclr_asm(p->pos, n);
#endif
#if !RE4DC_WATER45_LEAN
#line 1475 "D:/Bio4/Prog/espgen45.cpp"
    p->nrm = (Vec*) MEM_ALLOC(n, 1, 13);
    if (p->nrm == NULL) {
        goto nomem;
    }
    memclr_asm(p->nrm, n);
#line 1484 "D:/Bio4/Prog/espgen45.cpp"
    p->bump = (u8*) MEM_ALLOC(sizeof(Vec) * p->nx * p->ny, 1, 13);
    if (p->bump == NULL) {
        goto nomem;
    }
    p->dlSize = ((p->nx + 1) * 2 * p->ny * 12 + 0x61) & ~0x1F;
#line 1497 "D:/Bio4/Prog/espgen45.cpp"
    p->dl = (u8*) MEM_ALLOC(p->dlSize, 1, 13);
    if (p->dl == NULL) {
    nomem:
        pLog->err(0, 0, "Espgen45 : not enough memory");
        PushEspgen(w);
        return NULL;
    }
    memclr_asm(p->dl, p->dlSize);
    GXClearVtxDesc();
    GXSetVtxDesc(9, 3);
    GXSetVtxDesc(10, 3);
    GXSetVtxDesc(13, 1);
    GXSetVtxAttrFmt(0, 9, 1, 4, 0);
    GXSetVtxAttrFmt(0, 10, 0, 4, 0);
    GXSetVtxAttrFmt(0, 13, 1, 4, 0);
    d = p->dl;
    *d = 0;
    d++;
    *d = 0x98;
    d++;
    *(u16*) d = (p->nx + 1) * 2 * p->ny;
    d += 2;
    for (i = 0; i < p->ny; i++) {
        k = i * (p->nx + 1);
        for (j = 0; j < p->nx + 1; j++) {
            *(u16*) d = k;
            d += 2;
            *(u16*) d = k;
            d += 2;
            *(f32*) d = (f32) j / (f32) (p->nx + 1);
            d += 4;
            *(f32*) d = (f32) i / (f32) (p->ny + 1);
            d += 4;
            *(u16*) d = p->nx + (k + 1);
            d += 2;
            *(u16*) d = p->nx + (k + 1);
            d += 2;
            *(f32*) d = (f32) j / (f32) (p->nx + 1);
            d += 4;
            *(f32*) d = (f32) (i + 1) / (f32) (p->ny + 1);
            d += 4;
            k++;
        }
        i++;
        if (i < p->ny) {
            for (j = p->nx; j >= 0; j--) {
                k = i * (p->nx + 1) + j;
                *(u16*) d = k;
                d += 2;
                *(u16*) d = k;
                d += 2;
                *(f32*) d = (f32) j / (f32) (p->nx + 1);
                d += 4;
                *(f32*) d = (f32) i / (f32) (p->ny + 1);
                d += 4;
                *(u16*) d = p->nx + (k + 1);
                d += 2;
                *(u16*) d = p->nx + (k + 1);
                d += 2;
                *(f32*) d = (f32) j / (f32) (p->nx + 1);
                d += 4;
                *(f32*) d = (f32) (i + 1) / (f32) (p->ny + 1);
                d += 4;
            }
        }
    }
#else
    // RE4DC_WATER45_LEAN (ROUTE_CH13, r10b): the normal / bump / display-list buffers only feed the GX
    // draw (refraction + indirect bump), which the Dreamcast does not run: the PS2 world draws the lake.
    // The height field (hA / hB / pos) and its RNG use are unchanged.
    p->nrm = NULL;
    p->bump = NULL;
    p->dl = NULL;
    p->dlSize = 0;
    if (0) {
    nomem:
        pLog->err(0, 0, "Espgen45 : not enough memory");
        PushEspgen(w);
        return NULL;
    }
#endif
    // One counter pair for the init loops: `jj` (inner fRand loop, then the two x edges: it crosses the
    // call, so callee-saved r28) and `i2`/`idx` (fRand rows, `i2 = p->ny` for the far edge, the two y edges).
    int jj;
    int i2;
    int idx;
#if RE4DC_WATER45_GRID_SKIP
    for (i2 = 0; i2 < p->ny + 1; i2++) {
        for (jj = 0; jj < p->nx + 1; jj++) {
            (void) fRand1_1();   // the grid init's shared-RNG draws, same count and order
        }
    }
    return w;
#else
    fy = 0.0f;
    for (i2 = 0; i2 < p->ny + 1; i2++) {
        idx = i2 * (p->nx + 1);
        fx = 0.0f;
        for (jj = 0; jj < p->nx + 1; jj++) {
            p->pos[idx].x = fx - (f32) (int) (p->nx / 2);
            p->pos[idx].y = fRand1_1() * 0.2f;
            fx += 1.0f;
            p->pos[idx].z = fy - (f32) (int) (p->ny / 2);
#if !RE4DC_WATER45_LEAN
            p->nrm[idx].x = 0.0f;
            p->nrm[idx].y = 1.0f;
            p->nrm[idx].z = 0.0f;
#endif
            p->hA[idx] = 0.0f;
            p->hB[idx] = 0.0f;
#if !RE4DC_WATER45_LEAN
            Vec* n = &p->nrm[idx];
            n->x += ((f32) jj - (f32) (int) (p->nx / 2)) * (1.0f / (f32) (int) p->nx);
            n->z += ((f32) i2 - (f32) (int) (p->ny / 2)) * (1.0f / (f32) (int) p->ny);
            n->y *= 0.25f;
#endif
            idx++;
        }
        fy += 1.0f;
    }
    {
        static f32 g45_init_y = 0.0f;
        static f32 g45_init_y2 = 0.0f;
        for (jj = 0; jj < p->nx + 1; jj++) {
            p->pos[jj].y = FGet(g45_init_y);
        }
        i2 = p->ny;
        idx = i2 * (p->nx + 1);
        for (jj = 0; jj < p->nx + 1; jj++) {
            p->pos[idx + jj].y = FGet(g45_init_y);
        }
        // The y edges also go through `idx` (one pseudo across all four loops = the target's r8 in every
        // loop), and the far edge is `idx = row; idx += nx` (the product lands in idx's register, not a temp).
        for (i2 = 0; i2 < p->ny + 1; i2++) {
            idx = i2 * (p->nx + 1);
            p->pos[idx].y = FGet(g45_init_y2);
        }
        for (i2 = 0; i2 < p->ny + 1; i2++) {
            idx = i2 * (p->nx + 1);
            idx += p->nx;
            p->pos[idx].y = FGet(g45_init_y2);
        }
    }
    // Block-local sizes at the tail: local-alloc ties the `nx + 1` temp into them (`addi r30; mullw r30`);
    // the function-level `n` is only the MEM_ALLOC size.
    {
        u32 n2 = sizeof(Vec) * (p->nx + 1) * (p->ny + 1);
        DCStoreRange(p->pos, n2);
#if !RE4DC_WATER45_LEAN
        DCStoreRange(p->nrm, n2);
#endif
    }
#if !RE4DC_WATER45_LEAN
    DCStoreRange(p->bump, sizeof(Vec) * (p->nx + 1) * (p->ny + 1));
#endif
    {
        u32 n3 = sizeof(f32) * (p->nx + 1) * (p->ny + 1);
        DCStoreRange(p->hA, n3);
        DCStoreRange(p->hB, n3);
    }
#if !RE4DC_WATER45_LEAN
    DCStoreRange(p->dl, p->dlSize);
#endif
    return w;
#endif   // RE4DC_WATER45_GRID_SKIP
}

// Frees the six grid buffers and clears g_pWater45.
void Espgen45_Destruct(EspgenWork* w)
{
    Espgen42Work* p = (Espgen42Work*) w->work;

    if (p->hA != NULL) {
        Mem_free(p->hA);
        p->hA = NULL;
    }
    if (p->hB != NULL) {
        Mem_free(p->hB);
        p->hB = NULL;
    }
    if (p->pos != NULL) {
        Mem_free(p->pos);
        p->pos = NULL;
    }
    if (p->nrm != NULL) {
        Mem_free(p->nrm);
        p->nrm = NULL;
    }
    if (p->bump != NULL) {
        Mem_free(p->bump);
        p->bump = NULL;
    }
    if (p->dl != NULL) {
        Mem_free(p->dl);
        p->dl = NULL;
    }
    g_pWater45 = NULL;
}

// Builds the water from the effect record: grid WorkSp8[0..1] (default 64, max 184, rounded down to a
// multiple of 8), wave ratio WorkSp8[2], Tool_flg bit 0 = no border quads, bit 0x4000 = mask texture
// MaskTex_id; colour Col_start, ambient Col_d*255, mode Work8[0] (2: damp/spread from Work8[1..2]),
// specular Tex_id, indirect strengths prm.h xCE/xD2, stages Work8[3]. Registers g_pWater45 and runs
// the first move. Returns 0 when the noise texture 0xFE or memory is missing.
int Espgen45_SetFreeWork(EspgenWork* w, EspGenWork* rec, EspSeqData* head, cModel* model, u16 parts, Mtx* mtx,
                         Vec* pos, Vec* rot, EspSeqOpt* pSct)
{
    Espgen42Work* p = (Espgen42Work*) w->work;
    Vec r;
    u32 nx = 0x40;
    u32 ny = 0x40;
    f32 rate;

    if (EspGetTexObj(0xFE, 0) == NULL) {
        pLog->err(0, 0, "Espgen45 : WaterTex(0xfe) not found!");
        return 0;
    }
    if (rec->Tool_flg & 1) {
        p->flag |= 1;
    }
    if (rec->Tool_flg & 0x4000) {
        p->flag |= 2;
        p->Mask_Tex = rec->MaskTex_id;
        p->flag |= 1;
    }
    if (rec->WorkSp8[0] != 0) {
        nx = rec->WorkSp8[0];
        if (nx > 0xB8) {
            nx = 0xB8;
            pLog->warn(0, 0, "ESP_WATER : width > 184");
        }
    }
    if (rec->WorkSp8[1] != 0) {
        ny = rec->WorkSp8[1];
        if (ny > 0xB8) {
            ny = 0xB8;
            pLog->warn(0, 0, "ESP_WATER : height > 184");
        }
    }
    if (nx & 7) {
        u32 n = nx - (nx & 7);
        pLog->warn(0, 0, "ESP_WATER : width (%d -> %d)", nx, n);
        nx = n;
    }
    if (ny & 7) {
        u32 n = ny - (ny & 7);
        pLog->warn(0, 0, "ESP_WATER : height (%d -> %d)", ny, n);
        ny = n;
    }
    rate = 1.0f - (f32) (int) rec->WorkSp8[2] / 255.0f;
    p->rotY = rec->WorkSp8[2];
    PSVECScale(&rec->Ang, &r, 6.28f / 360.0f);
    if (SetWaterWork45(w, (Vec*) &rec->Pos.x, &r, rec->Size_base_x, nx, ny, rate) != 0) {
        p->col.r = rec->Col_start_r;
        p->col.g = rec->Col_start_g;
        p->col.b = rec->Col_start_b;
        p->col.a = rec->Col_start_a;
        p->amb.r = rec->Col_d_r * 255.0f;
        p->amb.g = rec->Col_d_g * 255.0f;
        p->amb.b = rec->Col_d_b * 255.0f;
        p->amb.a = rec->Col_d_a * 255.0f;
        p->mode = rec->Work8[0];
        p->Base_y = p->pos0.y;
        if (p->mode == 2) {
            p->damp = 0.5f - (f32) (s8) rec->Work8[1] * 0.005f;
            if (p->damp > 0.5f) {
                p->damp = 0.5f;
            }
            if (p->damp < 0.0f) {
                p->damp = 0.0f;
            }
            p->spread = 0.99f - (f32) (int) rec->Work8[2] * 0.001f;
        }
        p->texId = rec->Tex_id;
        p->indS = rec->prm.h.xCE;
        p->indT = rec->prm.h.xD2;
        p->stages = rec->Work8[3];
        g_pWater45 = w;
        Espgen45_Move(w);
        return 1;
    }
    return 0;
}

// Room override: 1 = the surface follows the camera target (default), 0 = uses Estgen45SetTargetPos.
void Estgen45SetTargetCamera(int on)
{
    g_bTargetCamera = on;
}

// Room override: 1 = surface height from Estgen45SetHeight, 0 = the record's Base_y.
void Estgen45SetTargetHeight(int on)
{
    g_bTargetHeight = on;
}

// Room override: use the Estgen45SetSize size instead of the record's.
void Estgen45SetSizeOverWrite(int on)
{
    g_bSizeOverWrite = on;
}

// Room override: replace the record colours by the Estgen45SetColor values.
void Estgen45SetColorOverWrite(int on)
{
    g_bColorOverWrite = on;
}

// Room override: multiply the record colours by the Estgen45SetColor values.
void Estgen45SetColorMul(int on)
{
    g_bColorMul = on;
}

// Room override: take Type/wave ratio/damp/spread/indirect/rotation/mask from the Esp4cWork block.
void Estgen45SetParamOverWrite(int on)
{
    g_bSetParam = on;
}

// Sets the override centre of the surface and flags Status_flg[1] bit 0x20.
void Estgen45SetTargetPos(f32 x, f32 z)
{
    FSet(g_Target_x, x);
    FSet(g_Target_z, z);
    pG->Status_flg[1] |= 0x20;
}

// Sets the override water height.
void Estgen45SetHeight(f32 h)
{
    FSet(g_Target_y, h);
    pG->Status_flg[1] |= 0x20;
}

// Sets the override cell size.
void Estgen45SetSize(f32 size)
{
    FSet(g_Size, size);
    pG->Status_flg[1] |= 0x20;
}

// Sets the override tev colour (r,g,b,a) and ambient/scale factors (rs..as, 0..1).
void Estgen45SetColor(u8 r, u8 g, u8 b, u8 a, f32 rs, f32 gs, f32 bs, f32 as)
{
    U8Set(g_r, r);
    U8Set(g_g, g);
    U8Set(g_b, b);
    U8Set(g_a, a);
    FSet(g_sr, rs);
    FSet(g_sg, gs);
    FSet(g_sb, bs);
    FSet(g_sa, as);
    pG->Status_flg[1] |= 0x20;
}

// Copies the esp4c parameter block used when the parameter override is on.
void Estgen45SetParam(Esp4cWork* w)
{
    g_Free = *w;
    pG->Status_flg[1] |= 0x20;
}

asm(".section .sdata; .balign 8");
