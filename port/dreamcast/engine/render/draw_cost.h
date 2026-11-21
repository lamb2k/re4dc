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
    DC_W_CLIPOUT, DC_W_MESHLETS, DC_W_SELECTED,
    DC_A_CALLS, DC_A_PARTS, DC_A_PARTS_BOUND, DC_A_WS, DC_A_POS, DC_A_NRM, DC_A_NRMLIGHTS, DC_A_LIGHTS, DC_A_HEADERS,
    DC_A_STRIPS, DC_A_STRIPS_OUT, DC_A_CORNERS, DC_A_CLIPSTRIPS, DC_A_CLIPTRIS, DC_A_CLIPOUT,
    DC_H_RECTS,
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
       DL_DIRECT=1024, DL_COPYV2=2048, DL_CLAMP=4096 };
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
