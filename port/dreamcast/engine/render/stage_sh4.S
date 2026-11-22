/* render/stage_sh4.S -- vertex kernels (the world's stage kernel m1_stage_world was removed by lane eng-draw2, step W1:
 * pieces in front of the near plane are walked without a stage, native_draw.inc walk_strips) (KOS -m4-single -ml; FPSCR.PR = SZ = 0 on entry and exit).
 *
 * m1_emit_actor_strip(sq, corners, n, proj, lit) -> sq
 *   r4 sq: store-queue pointer      r5 corners: n records (u16 position, u16 normal, u16 u, u16 v)
 *   r6 n >= 1                        r7 proj: position kernel output (32-byte records, x y 1/w at +4)
 *   @(0,r15) lit: u32 colour per normal
 *   One TA vertex per corner straight to the store queues: (flags,x),(y,z) as two 64-bit pairs, u, v from the corner,
 *   colour from the normal; the last corner ends the strip. Returns the next store-queue pointer.
 */
        .text

/* One corner: r5 corners++, r4 sq; r7 proj, r8 lit, flags (r9 unless named) for this corner, fr8 = 1/32768.
   Clobbers r0-r3, r10, fr0-fr5. */
        .macro  ACTOR_CORNER flags=r9
        mov.l   @r5+,r1                 /* position | normal << 16 */
        mov.l   @r5+,r2                 /* u | v << 16 */
        extu.w  r1,r3
        shlr16  r1
        shll2   r3
        shll2   r3
        shll    r3
        add     r7,r3                   /* proj + 32 position */
        shll2   r1
        mov     r1,r0
        mov.l   @(r0,r8),r10            /* colour */
        fschg
        fmov    @r3+,dr0                /* (flags, x) */
        fmov    @r3,dr2                 /* (y, 1/w) */
        fschg
        extu.w  r2,r0
        shlr16  r2
        lds     r0,fpul
        float   fpul,fr4
        lds     r2,fpul
        float   fpul,fr5
        fmul    fr8,fr4
        fmul    fr8,fr5
        mov     r4,r3
        add     #16,r3
        fschg
        fmov    dr2,@-r3
        fmov    dr0,@-r3
        fschg
        mov.l   \flags,@r4
        mov.l   r10,@(24,r4)
        mov     #0,r0
        mov.l   r0,@(28,r4)
        mov     r4,r3
        add     #24,r3
        fmov.s  fr5,@-r3
        fmov.s  fr4,@-r3
        pref    @r4
        mov     r4,r0
        xor     #32,r0
        mov     r0,r4
        .endm

        .align  5
        .global _m1_emit_actor_strip
        .type   _m1_emit_actor_strip, @function
_m1_emit_actor_strip:
        mov.l   r8,@-r15
        mov.l   r9,@-r15
        mov.l   r10,@-r15
        mov.l   @(12,r15),r8            /* lit */
        mova    .Lae_scale,r0
        fmov.s  @r0,fr8
        mov.l   .Lae_vertex,r9
        dt      r6
        bt      .Lae_last
        .align  2
.Lae_loop:
        ACTOR_CORNER
        dt      r6
        bf      .Lae_loop
.Lae_last:
        mov.l   .Lae_eol,r9
        ACTOR_CORNER
        mov     r4,r0
        mov.l   @r15+,r10
        mov.l   @r15+,r9
        rts
        mov.l   @r15+,r8
        .align  2
.Lae_vertex:
        .long   0xe0000000
.Lae_eol:
        .long   0xf0000000
.Lae_scale:
        .float  0.000030517578125
        .size   _m1_emit_actor_strip, .-_m1_emit_actor_strip

/* Lane eng-draw4 (step 3b): m1_emit_actor_run(sq, run) -> sq, the strips of one part walked inside the kernel (the C
 * form of step 3a called m1_emit_actor_strip once a strip: a call, a prologue and the tests of the C loop each strip).
 *   r4 sq; r5 run: EmitRun {p, stop, proj, lit, sc, corners} at offsets 0, 4, 8, 12, 16, 20 (native_actor.inc).
 *   p: the part's strip stream (u32 n >= 1, then n corner records as above), p < stop on entry.
 *   sc 0: every strip is emitted (a part inside the frustum). Else one code byte a strip: 0x80 dropped (skipped);
 *   bit 5 crosses the near plane: the kernel stops AT that strip (run->p, run->sc point at it) for the C clipper.
 *   corners += n for each strip emitted. Per strip the first n - 1 corners go four to a block (singles until the count
 *   left is a multiple of four), the last with the end-of-strip flags: the same stores as m1_emit_actor_strip, corner
 *   for corner (ACTOR_CORNER). Branch ranges: bt/bf reach 254 bytes, so long back edges are bra. */
        .macro  STRIP_BODY
        mov.l   @r5+,r6                 /* n */
        add     r6,r11
        add     #-1,r6                  /* the corners before the last */
1:
        mov     r6,r0
        tst     #3,r0
        bt      2f
        ACTOR_CORNER
        bra     1b
        add     #-1,r6
2:
        tst     r6,r6
        bf      4f
        bra     3f
        nop
4:
        ACTOR_CORNER
        ACTOR_CORNER
        ACTOR_CORNER
        ACTOR_CORNER
        add     #-4,r6
        tst     r6,r6
        bt      3f
        bra     4b
        nop
3:
        ACTOR_CORNER r14
        .endm

        .align  5
        .global _m1_emit_actor_run
        .type   _m1_emit_actor_run, @function
_m1_emit_actor_run:
        mov.l   r8,@-r15
        mov.l   r9,@-r15
        mov.l   r10,@-r15
        mov.l   r11,@-r15
        mov.l   r12,@-r15
        mov.l   r13,@-r15
        mov.l   r14,@-r15
        mov.l   r5,@-r15                /* run */
        mov.l   @(4,r5),r13             /* stop */
        mov.l   @(8,r5),r7              /* proj */
        mov.l   @(12,r5),r8             /* lit */
        mov.l   @(16,r5),r12            /* sc */
        mov.l   @(20,r5),r11            /* corners */
        mov.l   @r5,r5                  /* p */
        mova    .Lar_scale,r0
        fmov.s  @r0,fr8
        mov.l   .Lar_vertex,r9
        mov.l   .Lar_eol,r14
        tst     r12,r12
        bt      .Lar_in
        bra     .Lar_bound
        nop
.Lar_in:                                /* inside part: every strip */
        STRIP_BODY
        cmp/hs  r13,r5
        bt      .Lar_done
        bra     .Lar_in
        nop
        .align  2
.Lar_vertex:
        .long   0xe0000000
.Lar_eol:
        .long   0xf0000000
.Lar_scale:
        .float  0.000030517578125
.Lar_done:
        mov.l   @r15+,r1                /* run */
        mov.l   r5,@r1
        mov.l   r12,@(16,r1)
        mov.l   r11,@(20,r1)
        mov     r4,r0
        mov.l   @r15+,r14
        mov.l   @r15+,r13
        mov.l   @r15+,r12
        mov.l   @r15+,r11
        mov.l   @r15+,r10
        mov.l   @r15+,r9
        rts
        mov.l   @r15+,r8
.Lar_bound:                             /* boundary part: one code a strip */
        cmp/hs  r13,r5
        bt      .Lar_done
        mov.b   @r12,r0
        cmp/pz  r0
        bt      .Lar_keep
        mov.l   @r5+,r0                 /* dropped: skip its corners */
        add     #1,r12
        shll2   r0
        shll    r0
        bra     .Lar_bound
        add     r0,r5
.Lar_keep:
        tst     #32,r0
        bf      .Lar_done               /* crosses the near plane: the C clipper's */
        add     #1,r12
        STRIP_BODY
        bra     .Lar_bound
        nop
        .size   _m1_emit_actor_run, .-_m1_emit_actor_run

/* Lane eng-draw5 (item 2): the skinned position kernel without texture coordinates, generated from the released
 * kernel's generator (render/gen/mkavk_xy.py). */
#include "avk_xy_sh4.inc"
