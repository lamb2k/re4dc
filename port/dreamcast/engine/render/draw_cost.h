#pragma once
/* Lane eng-draw1 (measurement only): the renderer's per-picture work counters, its phase stamps and its run-time lab arms.
   Nothing here changes the picture or the work of the default path. Counters are register sums added to a global once a
   strip, part or call (never once a vertex); a stamp is one clock read at a pass boundary; a lab arm is off unless a boot
   file read when the pack opens (before play: DLA, DLB) or a bench schedule token ("/X", engine/bench/main.c) sets it.

   Lab arms repeat one phase (its second run does the same work again, so the picture time grows by the phase's own cost)
   or change the renderer's near plane (N: the pre-fix renderer, a near plane that is not a number). In the E1 images a set
   interleaves its arms over the pictures (set A: picture % 6 = 1 stage, 2 copy, 3 select, 4 HUD, 5 near not a number;
   set B: picture % 5 = 1 weight sets, 2 normals lit, 3 actor emission, 4 the 2 ms delay control; 0 is the base) and the
   reader (tools/engine/drawcost.py) compares each arm picture with its base neighbours. While a set is on, the world's
   selection is made every picture (the unmoved-camera reuse is off for every picture, base pictures included). */
#include <stdint.h>
enum {
    DC_W_PIECES, DC_W_PLACES, DC_W_HEADERS, DC_W_STAGED, DC_W_STRIPS, DC_W_CORNERS, DC_W_CLIPSTRIPS, DC_W_CLIPTRIS,
    DC_W_CLIPOUT, DC_W_MESHLETS, DC_W_SELECTED, DC_W_FACEDROP,   /* FACEDROP: corners of strips E2 did not send (eng-draw2) */
    DC_A_CALLS, DC_A_PARTS, DC_A_PARTS_BOUND, DC_A_WS, DC_A_POS, DC_A_NRM, DC_A_NRMLIGHTS, DC_A_LIGHTS, DC_A_HEADERS,
    DC_A_STRIPS, DC_A_STRIPS_OUT, DC_A_CORNERS, DC_A_CLIPSTRIPS, DC_A_CLIPTRIS, DC_A_CLIPOUT,
    DC_H_RECTS,
    /* census (arm Z / boot set DLV, counts only, never timed): the invisible share. Each submitted triangle of a strip is
       classed on the screen positions the renderer already made: off-screen (all three corners past one screen edge),
       culling off in its header, or by the sign of its screen area (N: negative, P: positive; which sign the chip culls
       is read from the header's culling bits and checked by depth: the culled sign must be the farther one on closed
       characters, IW sums at 2^24). AREA: on-screen area clipped to 640 x 480, in pixels. DEAD: strips (and their
       corners) and vertices that no kept triangle uses, under each sign convention. CLIP: triangles the clipper got
       that were wholly in front (could have been drawn as strips), wholly behind (could have been rejected) or crossing.
       TR: translucent list area (world list 2 and the hair run), every on-screen triangle. */
    DC_V_W_TRIS, DC_V_W_OFF, DC_V_W_NOCULL, DC_V_W_NEG, DC_V_W_POS, DC_V_W_AREA_NOCULL, DC_V_W_AREA_NEG, DC_V_W_AREA_POS,
    DC_V_W_DEADSTRIPS_N, DC_V_W_DEADSTRIPS_P, DC_V_W_DEADCORNERS_N, DC_V_W_DEADCORNERS_P, DC_V_W_DEADVTX_N, DC_V_W_DEADVTX_P,
    DC_V_W_CLIP_FRONT, DC_V_W_CLIP_BEHIND, DC_V_W_CLIP_CROSS, DC_V_TR_AREA,
    DC_V_A_TRIS, DC_V_A_OFF, DC_V_A_NOCULL, DC_V_A_NEG, DC_V_A_POS, DC_V_A_AREA_NOCULL, DC_V_A_AREA_NEG, DC_V_A_AREA_POS,
    DC_V_A_DEADSTRIPS_N, DC_V_A_DEADSTRIPS_P, DC_V_A_DEADCORNERS_N, DC_V_A_DEADCORNERS_P, DC_V_A_DEADPOS_N, DC_V_A_DEADPOS_P,
    DC_V_A_DEADNRM_N, DC_V_A_DEADNRM_P, DC_V_A_IW_NEG, DC_V_A_IW_POS, DC_V_A_CULLMODE_CW, DC_V_A_CULLMODE_CCW,
    DC_V_W_CULLMODE_CW, DC_V_W_CULLMODE_CCW,
    /* characters, headers with culling off (all of them today): the sign of each on-screen triangle, and what would be
       dead if culling were on (C: kept-if-culled marks, bits 4 (N) and 8 (P)) */
    DC_V_A_NC_NEG, DC_V_A_NC_POS, DC_V_A_NC_AREA_NEG, DC_V_A_NC_AREA_POS,
    DC_V_A_CDEADSTRIPS_N, DC_V_A_CDEADSTRIPS_P, DC_V_A_CDEADCORNERS_N, DC_V_A_CDEADCORNERS_P, DC_V_A_CDEADPOS_N, DC_V_A_CDEADPOS_P,
    DC_COUNT
};
extern uint32_t dc_n[DC_COUNT];
#define DC_ADD(k,v) (dc_n[k]+=(uint32_t)(v))
/* the counter set clipped() charges (DC_W_CLIPTRIS or DC_A_CLIPTRIS; the output corners at +1) */
extern unsigned dc_clip;
enum { DL_STAGE2=1, DL_COPY2=2, DL_SELECT2=4, DL_HUD2=8, DL_NAN=16, DL_WS2=32, DL_LIGHT2=64, DL_EMIT2=128, DL_DELAY=256,
       DL_SKIN2=512,
       /* option arms (each tries one candidate change; set C, bench tokens X V G): X the world without a stage (each
          strip corner transformed where it is used), V the world copy with the stage pointer in a register and two
          corners an iteration, G no near clipping of the world (w raised to the near plane: an approximation) */
       /* lane eng-draw2, step W1: the world in front of the near plane is walked without a stage by default, so X and V
          no longer change anything (their bits and tokens stay so old schedules still parse) */
       DL_DIRECT=1024, DL_COPYV2=2048, DL_CLAMP=4096,
       DL_CENSUS=8192 };   /* the census (counts only; its timing is never used) */
/* census helpers (draw_cost.inc) */
void dc_census_tri(unsigned base,float x0,float y0,float z0,float x1,float y1,float z1,float x2,float y2,float z2,
                   unsigned cull,unsigned* kept);   /* base: DC_V_W_TRIS or DC_V_A_TRIS; kept: bit 1 kept under N, 2 under P */
void dc_census_tr(float x0,float y0,float x1,float y1,float x2,float y2);
extern uint32_t dc_arm_now;      /* this picture's arms */
extern uint32_t dc_lab_bench;    /* the bench window's arms (every picture of the window) */
extern unsigned dc_interleave;   /* E1 boot sets: 0 none, 1 set A, 2 set B */
extern unsigned dc_mute;         /* a repeated phase's second run is not counted */
#define DC_ARM(bit) (dc_arm_now&(bit))
/* arm N: the renderer's near plane as the E1 images had it before lane eng-e1l (p23 / (p22 - 1) not a number); read
   through a volatile so the compiler cannot fold it */
extern volatile union DcNan { uint32_t u; float f; } dc_nan;
#define DC_NEAR(x) (DC_ARM(DL_NAN)?dc_nan.f:(x))
enum { DS_VIS0, DS_PREP1, DS_SKY0, DS_SKY1, DS_W0A, DS_W0B, DS_W1A, DS_W1B, DS_W2A, DS_W2B, DS_HUD0, DS_HUD1, DS_COUNT };
void dc_stamp(unsigned k);
void dc_lab_open(void);
extern uint32_t dc_frame_base;   /* the bench: the window's first picture number minus 1 */
void dc_window_begin(void);      /* the bench: pictures 1..600 of the window from here */
void native_draw_report(void);   /* E1 images: after play (core/frame.cpp e1_report) */
void native_draw_report_window(unsigned window);   /* the bench: after each window */
