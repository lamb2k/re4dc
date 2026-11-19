/* render/stage_sh4.S -- E0 bench vertex kernels (KOS -m4-single -ml; FPSCR.PR = SZ = 0 on entry and exit).
 *
 * m1_stage_world(out, remap, vertices, color, pairs, uvp)
 *   r4 out: TA vertices, 32 bytes each (32-byte aligned)   r5 remap: u16 vertex offsets
 *   r6 vertices: biased int16 x, y, z, u, v (12-byte records) r7 color: u32 TA colours, one per staged vertex
 *   @(0,r15) pairs: vertex pairs to stage                    @(4,r15) uvp: u0, v0, du, dv (floats)
 *   XMTRX holds the placement's screen matrix. Writes flags, x/w, y/w, 1/w, u, v, argb, 0 per vertex; the line is
 *   allocated with movca.l (no fill read). Two vertices per iteration (fv0 and fv4) so one vertex's loads and
 *   conversions overlap the other's transform. Stages an even count: the caller allows one vertex of overrun.
 *
 * m1_emit_actor_strip(sq, corners, n, proj, lit) -> sq
 *   r4 sq: store-queue pointer      r5 corners: n records (u16 position, u16 normal, u16 u, u16 v)
 *   r6 n >= 1                        r7 proj: position kernel output (32-byte records, x y 1/w at +4)
 *   @(0,r15) lit: u32 colour per normal
 *   One TA vertex per corner straight to the store queues: (flags,x),(y,z) as two 64-bit pairs, u, v from the corner,
 *   colour from the normal; the last corner ends the strip. Returns the next store-queue pointer.
 */
        .text
        .align  5
        .global _m1_stage_world
        .type   _m1_stage_world, @function
_m1_stage_world:
        mov.l   r8,@-r15
        mov.l   r9,@-r15
        mov.l   r10,@-r15
        mov.l   r11,@-r15
        mov.l   r12,@-r15
        fmov.s  fr12,@-r15
        fmov.s  fr13,@-r15
        fmov.s  fr14,@-r15
        fmov.s  fr15,@-r15
        mov.l   @(36,r15),r3            /* pairs (5 words + 4 floats pushed) */
        mov.l   @(40,r15),r0            /* uvp */
        fmov.s  @r0+,fr12               /* u0 */
        fmov.s  @r0+,fr13               /* v0 */
        fmov.s  @r0+,fr14               /* du */
        fmov.s  @r0+,fr15               /* dv */
        tst     r3,r3
        bt      .Lsw_done
        mov.l   .Lsw_flags,r8
        .align  2
.Lsw_loop:
        mov.w   @r5+,r1
        mov.w   @r5+,r2
        extu.w  r1,r1
        extu.w  r2,r2
        shll2   r1
        shll2   r2
        mov     r1,r9
        mov     r2,r10
        add     r9,r9
        add     r10,r10
        add     r9,r1
        add     r10,r2
        add     r6,r1                   /* A: vertices + 12 r */
        add     r6,r2                   /* B */
        mov.w   @r1+,r0
        lds     r0,fpul
        mov.w   @r2+,r0
        float   fpul,fr0
        lds     r0,fpul
        mov.w   @r1+,r0
        float   fpul,fr4
        lds     r0,fpul
        mov.w   @r2+,r0
        float   fpul,fr1
        lds     r0,fpul
        mov.w   @r1+,r0
        float   fpul,fr5
        lds     r0,fpul
        mov.w   @r2+,r0
        float   fpul,fr2
        lds     r0,fpul
        fldi1   fr3
        float   fpul,fr6
        fldi1   fr7
        ftrv    xmtrx,fv0
        mov.w   @r1+,r0
        lds     r0,fpul
        mov.w   @r1,r0
        float   fpul,fr8                /* A u */
        lds     r0,fpul
        mov.w   @r2+,r0
        float   fpul,fr9                /* A v */
        lds     r0,fpul
        ftrv    xmtrx,fv4
        mov.w   @r2,r0
        float   fpul,fr10               /* B u */
        lds     r0,fpul
        mov.l   @r7+,r11                /* A colour */
        float   fpul,fr11               /* B v */
        mov.l   @r7+,r12                /* B colour */
        fmul    fr3,fr3
        fmul    fr14,fr8
        fmul    fr15,fr9
        fsrra   fr3                     /* A 1/|w| */
        fmul    fr7,fr7
        fadd    fr12,fr8
        fadd    fr13,fr9
        fsrra   fr7                     /* B 1/|w| */
        fmul    fr3,fr0
        fmul    fr3,fr1
        fmul    fr14,fr10
        fmul    fr15,fr11
        fmul    fr7,fr4
        fmul    fr7,fr5
        fadd    fr12,fr10
        fadd    fr13,fr11
        mov     r8,r0
        movca.l r0,@r4                  /* A line: flags, allocated without a fill */
        mov     r4,r1
        add     #32,r1
        mov     #0,r0
        mov.l   r0,@-r1
        mov.l   r11,@-r1
        fmov.s  fr9,@-r1
        fmov.s  fr8,@-r1
        fmov.s  fr3,@-r1
        fmov.s  fr1,@-r1
        fmov.s  fr0,@-r1
        add     #32,r4
        mov     r8,r0
        movca.l r0,@r4                  /* B line */
        mov     r4,r1
        add     #32,r1
        mov     #0,r0
        mov.l   r0,@-r1
        mov.l   r12,@-r1
        fmov.s  fr11,@-r1
        fmov.s  fr10,@-r1
        fmov.s  fr7,@-r1
        fmov.s  fr5,@-r1
        fmov.s  fr4,@-r1
        dt      r3
        bf/s    .Lsw_loop
        add     #32,r4
.Lsw_done:
        fmov.s  @r15+,fr15
        fmov.s  @r15+,fr14
        fmov.s  @r15+,fr13
        fmov.s  @r15+,fr12
        mov.l   @r15+,r12
        mov.l   @r15+,r11
        mov.l   @r15+,r10
        mov.l   @r15+,r9
        rts
        mov.l   @r15+,r8
        .align  2
.Lsw_flags:
        .long   0xe0000000
        .size   _m1_stage_world, .-_m1_stage_world

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
