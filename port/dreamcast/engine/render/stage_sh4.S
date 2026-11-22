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

/* One corner: r5 corners++, r4 sq; r7 proj, r8 lit, r9 flags for this corner, fr8 = 1/32768. Clobbers r0-r3,
   r10, fr0-fr5. */
        .macro  ACTOR_CORNER
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
        mov.l   r9,@r4
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
