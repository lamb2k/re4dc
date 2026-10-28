#include "shz_strip_area.inc"
/* Common CPU_BACKFACE=2 strip classifier and store-queue emitter.
 * shz_strip_sq_t: cache,indices,n,mask,cull,q,sent,pieces at 0,4,...28.
 * mask low byte: 255 world (preserve normal command word), 127 actor
 * (synthesize VERTEX). mask bit 0x100: actor EOL-aware whole-index stream.
 * A strip with <3 indices emits nothing. cull must be 1 or 2; exclusions
 * and clipping belong to the existing callers, never to this kernel.
 *
 * One pass: hold the final vertex of the latest front triangle. A following
 * front within two back triangles commits the pending vertices as VERTEX;
 * the third back, EOL or input end commits only that last vertex as EOL.
 * Leading/trailing back runs disappear; short internal back runs remain.
 * Every new piece starts on an even original triangle, as backface_emit.hpp.
 *
 * Keeps the actual CPU1 target lowering: four fsub, rounded second product,
 * fneg then FMAC of the first product and negative second. No reassociated
 * edge determinant. Ordered comparison: zero and
 * unordered areas are not front. No C classifier, mask pass or fallback.
 *
 * SH ABI: preserve r8-r14, fr12-fr15, PR and exact incoming FPSCR. PR/SZ
 * forced zero internally; FR/rounding/DN remain unchanged. The trace-only
 * callback saves the opposite bank and normalizes FR=0 around ordinary C.
 * Copy bursts use DR0..6, leaving the opposite FP bank/XMTRX intact.
 * Source/host qualification is not a <=4-cycle or target-performance claim.
 */

#ifndef SHZ_STRIP_TRACE_CALLBACK
#define SHZ_STRIP_TRACE_CALLBACK _shz_strip_sq_trace
#endif
#ifndef SHZ_STRIP_TRACE
#define SHZ_STRIP_TRACE 0
#endif
#ifndef SHZ_STRIP_FAST
#define SHZ_STRIP_FAST 1
#endif

        .macro SHZ_JUMP target
        mov.l .Ljump_address\@,r0
        jmp @r0
        nop
        .align 2
.Ljump_address\@: .long \target
        .endm

        .text
        .align 5
        .global _shz_strip_sq
        .global _shz_strip_walk_sq
        .type _shz_strip_walk_sq,@function
        .type _shz_strip_sq,@function

/* FPSCR.SZ=1 while copying. DR0..6 leave the live x/y in fr8..13 intact.
 * command: 0 preserve world word0; 1 actor VERTEX; 2 terminal EOL.
 * r4=next emitted index ordinal; r8=cache,r9=strip index base,r11=mask,r12=SQ.
 * Clobbers r0,r1,r2 only. Caller controls SZ around one contiguous burst.
 */
        .macro COPY_VERTEX command
        mov     r4,r0
        mov.b   @(r0,r9),r1
        extu.b  r1,r1
        and     r11,r1
        shll2   r1
        shll2   r1
        add     r1,r1
        add     r8,r1
        fmov    @r1+,dr0
        fmov    @r1+,dr2
        fmov    @r1+,dr4
        fmov    @r1+,dr6
        add     #32,r12
        fmov    dr6,@-r12
        fmov    dr4,@-r12
        fmov    dr2,@-r12
        fmov    dr0,@-r12
        .if \command
        .if \command == 2
        mov     #-16,r2
        .else
        mov     #-32,r2
        .endif
        shll16  r2
        shll8   r2
        mov.l   r2,@r12
        .endif
        pref    @r12
        add     #32,r12
        add     #1,r4
        .endm

/* The all-front continuation owns a full pending B in DR0..6. Its x/y
 * words are consumed by the SQ stores before becoming exact determinant
 * temporaries. Cxy and the next Axy are the only four extra LS operations.
 * SZ=0 at entry/exit; compare direction and A-pair phase are unrolled.
 * mode 0 world, 1 explicit actor, 2 EOL-aware actor stream.
 */
        .macro FAST_STEP label,ax,ay,nx,ny,positive,mode,next
\label:
        mov.b   @r6+,r3
        extu.b  r3,r3
        mov     r3,r0
        and     r11,r0
        shll2   r0
        shll2   r0
        add     r0,r0
        add     r8,r0
        mov     r0,r7
        add     #4,r0
        fmov.s  @r0+,fr12
        fmov.s  @r0,fr13
        fmov    fr1,fr\nx
        fmov    fr2,fr\ny
        fschg
        fmov    dr6,@-r12
        fmov    dr4,@-r12
        fmov    dr2,@-r12
        SH4ZAM_BACKFACE_CX \ax
        fmov    dr0,@-r12
        SH4ZAM_BACKFACE_CY \ay
        SH4ZAM_BACKFACE_BX \ax
        .if \mode
        mov.l   r2,@r12
        .endif
        SH4ZAM_BACKFACE_PRODUCT \ay
        fschg
        SH4ZAM_BACKFACE_FMAC
        .if \positive
        fcmp/gt fr14,fr2
        .else
        fcmp/gt fr2,fr14
        .endif
        fschg
        fmov    @r7+,dr0
        fmov    @r7+,dr2
        fmov    @r7+,dr4
        fmov    @r7+,dr6
        fschg
        bf      .Lfast_back\@
        pref    @r12
        add     #64,r12
        .if \mode == 2
        mov     r3,r0
        tst     #128,r0
        bf      .Lfast_end\@
        .endif
        cmp/hi  r6,r10
        bt      \next
.Lfast_end\@:
        bra     .Lfast_terminal
        nop
.Lfast_back\@:
        /* No PREF: reconstruct slow counters only on this uncommon exit. */
        mov     r6,r13
        sub     r9,r13
        add     #-3,r13
        mov     r13,r5
        add     #-1,r5
        mov     r13,r4
        add     #1,r4
        .if \nx != 10
        fmov    fr\nx,fr10
        fmov    fr\ny,fr11
        .endif
        fmov    fr1,fr12
        fmov    fr2,fr13
        fldi0   fr7
        mov.l   r3,@(4,r15)
        bra     .Lback
        nop
        .endm

/* Trace the actual completed piece, without repeating any facing decisions.
 * Stack locals before macro: mode0,raw4,piece_start8,reserved12.
 */
        .macro TRACE_PIECE
#if SHZ_STRIP_TRACE
        mov.l   @(8,r15),r0
        mov     r5,r2
        add     #3,r2
        sub     r0,r2
        add     r9,r0
        mov.l   r4,@-r15
        mov.l   r5,@-r15
        mov.l   r6,@-r15
        mov.l   r7,@-r15
        fmov.s  fr7,@-r15
        fmov.s  fr8,@-r15
        fmov.s  fr9,@-r15
        fmov.s  fr10,@-r15
        fmov.s  fr11,@-r15
        fmov.s  fr12,@-r15
        fmov.s  fr13,@-r15
        sts.l   fpscr,@-r15
        sts.l   pr,@-r15
        frchg
        .irp reg,0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15
        fmov.s  fr\reg,@-r15
        .endr
        frchg
        mov     r0,r5
        mov     r8,r4
        mov     r2,r6
        mov     r11,r7
        sts     fpscr,r0
        mov     #1,r1
        shll16  r1
        shll2   r1
        shll2   r1
        shll    r1
        not     r1,r1
        and     r1,r0
        lds     r0,fpscr
        mov.l   .Ltrace_address\@,r0
        jsr     @r0
        nop
        bra     .Ltrace_after\@
        nop
        .align 2
.Ltrace_address\@:
        .long SHZ_STRIP_TRACE_CALLBACK
.Ltrace_after\@:
        mov     r15,r0
        add     #68,r0
        mov.l   @r0,r0
        mov     #1,r1
        shll16  r1
        shll2   r1
        shll2   r1
        shll    r1
        xor     r1,r0
        lds     r0,fpscr
        .irp reg,15,14,13,12,11,10,9,8,7,6,5,4,3,2,1,0
        fmov.s  @r15+,fr\reg
        .endr
        lds.l   @r15+,pr
        lds.l   @r15+,fpscr
        fmov.s  @r15+,fr13
        fmov.s  @r15+,fr12
        fmov.s  @r15+,fr11
        fmov.s  @r15+,fr10
        fmov.s  @r15+,fr9
        fmov.s  @r15+,fr8
        fmov.s  @r15+,fr7
        mov.l   @r15+,r7
        mov.l   @r15+,r6
        mov.l   @r15+,r5
        mov.l   @r15+,r4
#endif
        .endm

_shz_strip_sq:
        mov #0,r7
        bra .Lpublic_enter
        nop
_shz_strip_walk_sq:
        mov #1,r7
.Lpublic_enter:
        mov.l   r8,@-r15
        mov.l   r9,@-r15
        mov.l   r10,@-r15
        mov.l   r11,@-r15
        mov.l   r12,@-r15
        mov.l   r13,@-r15
        mov.l   r14,@-r15
        sts.l   pr,@-r15
        sts.l   fpscr,@-r15
        sts     fpscr,r0
        mov.l   .Lsingle_mask,r1
        bra     .Lmode_start
        and     r1,r0
        .align 2
.Lsingle_mask:
        .long 0xffe7ffff
.Lmode_start:
        lds     r0,fpscr
        fmov.s  fr12,@-r15
        fmov.s  fr13,@-r15
        fmov.s  fr14,@-r15
        fmov.s  fr15,@-r15
        add     #-96,r15
        mov.l   r4,@(16,r15)
        mov.l   r7,@(20,r15)
        mov     #0,r0
        mov.l   r0,@(12,r15)
        mov     r15,r14
        add     #64,r14
        tst     r7,r7
        bf      .Lworld_initialize
        .irp off,0,4,8,12,16,20
        mov.l   @(\off,r4),r0
        mov.l   r0,@(\off,r14)
        .endr
        mov     #0,r0
        mov.l   r0,@(32,r15)
        bra     .Lcontext_ready
        nop
.Lworld_initialize:
        mov.l   @(0,r4),r0
        mov.l   r0,@(24,r15)
        mov.l   @(4,r4),r0
        mov.l   r0,@(28,r15)
        mov.l   @(8,r4),r0
        mov.l   r0,@(32,r15)
        mov.l   @(16,r4),r0
        mov.l   r0,@(36,r15)
        mov.l   @(12,r4),r0
        mov.l   r0,@(0,r14)
        mov.l   @(20,r4),r0
        mov.l   r0,@(16,r14)
        mov.l   @(24,r4),r0
        mov.l   r0,@(20,r14)
        mov     #-1,r0
        extu.b  r0,r0
        mov.l   r0,@(12,r14)
        mov     #0,r0
        mov.l   r0,@(4,r14)
        mov.l   r0,@(8,r14)
.Lcontext_ready:
        mov.l   @(0,r14),r8
        mov.l   @(4,r14),r9
        mov.l   @(8,r14),r10
        add     r9,r10
        mov.l   @(12,r14),r11
        mov     r11,r0
        mov     #1,r1
        shll8   r1
        and     r1,r0
        mov.l   r0,@r15
        extu.b  r11,r11
        mov.l   @(20,r14),r12
        mov     #0,r0
        mov.l   r0,@(24,r14)
        mov.l   r0,@(28,r14)
        mov.l   @(16,r14),r0
        cmp/eq  #1,r0
        bt      .Lvalid_cull
        cmp/eq  #2,r0
        bt      .Lvalid_cull
        bra     .Lfinish
        nop
.Lvalid_cull:
        mov     r11,r0
        cmp/eq  #127,r0
        bt      .Lvalid_mask
        mov     #-1,r1
        extu.b  r1,r1
        cmp/eq  r1,r0
        bt      .Lvalid_mask
        bra     .Lfinish
        nop
.Lvalid_mask:
        fldi0   fr7
        bra     .Lbatch_dispatch
        nop
.Lstrip_start:
        fldi0 fr7
        mov     r9,r6
        mov     #0,r13
        mov     #-1,r5
        mov     #0,r4
        cmp/hs  r10,r6
        bf      .Lfirst
        bra     .Lfinish
        nop
.Lfirst:
        mov.b   @r6+,r1
        extu.b  r1,r1
        mov.l   @r15,r0
        tst     r0,r0
        bt      .Lfirst_xy
        mov     r1,r0
        tst     #128,r0
        bt      .Lfirst_xy
        bra     .Lnext_strip
        nop
.Lfirst_xy:
        mov     r1,r0
        and     r11,r0
        shll2   r0
        shll2   r0
        add     r0,r0
        add     r8,r0
        add     #4,r0
        fmov.s  @r0+,fr8
        fmov.s  @r0,fr9
        cmp/hs  r10,r6
        bf      .Lsecond
        bra     .Lfinish
        nop
.Lsecond:
        mov.b   @r6+,r1
        extu.b  r1,r1
        mov.l   @r15,r0
        tst     r0,r0
        bt      .Lsecond_xy
        mov     r1,r0
        tst     #128,r0
        bt      .Lsecond_xy
        bra     .Lnext_strip
        nop
.Lsecond_xy:
        mov     r1,r0
        and     r11,r0
        shll2   r0
        shll2   r0
        add     r0,r0
        add     r8,r0
        add     #4,r0
        fmov.s  @r0+,fr10
        fmov.s  @r0,fr11
        cmp/hs  r10,r6
        bf      .Ltriangle
        bra     .Lfinish
        nop

.Ltriangle:
        mov.b   @r6+,r0
        extu.b  r0,r0
        mov.l   r0,@(4,r15)
        and     r11,r0
        shll2   r0
        shll2   r0
        add     r0,r0
        add     r8,r0
        add     #4,r0
        fmov.s  @r0+,fr12
        fmov.s  @r0,fr13
        SH4ZAM_BACKFACE_AREA
        mov     r13,r2
        mov     #1,r0
        and     r0,r2
        mov.l   @(16,r14),r0
        and     #1,r0
        xor     r0,r2
        tst     r2,r2
        bt      .Lnegative_front
        fcmp/gt fr7,fr2
        bra     .Lfront_test
        nop
.Lnegative_front:
        fcmp/gt fr2,fr7
.Lfront_test:
        bf      .Lback

        /* Front: commit through vertex i+1; keep i+2 pending for EOL. */
        cmp/pz  r5
        bt      .Lcontinue_piece
        mov     r13,r4
        mov     #-2,r0
        and     r0,r4
        mov.l   r4,@(8,r15)
        mov.l   @(28,r14),r0
        add     #1,r0
        mov.l   r0,@(28,r14)
.Lcontinue_piece:
        mov     r13,r5
        mov     r13,r7
        add     #2,r7
        fschg
        mov     r11,r0
        cmp/eq  #127,r0
        bf      .Lemit_world
.Lemit_actor:
        COPY_VERTEX 1
        cmp/hs  r7,r4
        bf      .Lemit_actor
        bra     .Lemit_done
        nop
.Lemit_world:
        COPY_VERTEX 0
        cmp/hs  r7,r4
        bf      .Lemit_world
.Lemit_done:
        fschg
        fldi0   fr7
#if SHZ_STRIP_FAST
        cmp/hs  r10,r6
        bf      .Lfast_check_marker
        bra     .Lstrip_end
        nop
.Lfast_check_marker:
        mov.l   @r15,r0
        tst     r0,r0
        bt      .Lfast_warmup
        mov.l   @(4,r15),r0
        tst     #128,r0
        bt      .Lfast_warmup
        bra     .Lstrip_end
        nop
.Lfast_warmup:
        fmov    fr10,fr8
        fmov    fr11,fr9
        fldi0   fr14
        mov     r4,r0
        mov.b   @(r0,r9),r1
        extu.b  r1,r1
        and     r11,r1
        shll2   r1
        shll2   r1
        add     r1,r1
        add     r8,r1
        fschg
        fmov    @r1+,dr0
        fmov    @r1+,dr2
        fmov    @r1+,dr4
        fmov    @r1+,dr6
        fschg
        add     #32,r12
        add     #1,r13
        mov     r13,r1
        mov.l   @(16,r14),r0
        xor     r0,r1
        mov     #1,r0
        and     r0,r1
        mov     #-32,r2
        shll16  r2
        shll8   r2
        mov     r11,r0
        cmp/eq  #127,r0
        bt      .Lfast_actor_mode
        tst     r1,r1
        bt      .Lfast_w_negative
        bra     .Lfast_wp8
        nop
.Lfast_w_negative:
        bra     .Lfast_wn8
        nop
.Lfast_actor_mode:
        mov.l   @r15,r0
        tst     r0,r0
        bf      .Lfast_stream_mode
        tst     r1,r1
        bt      .Lfast_a_negative
        bra     .Lfast_ap8
        nop
.Lfast_a_negative:
        bra     .Lfast_an8
        nop
.Lfast_stream_mode:
        tst     r1,r1
        bt      .Lfast_s_negative
        bra     .Lfast_sp8
        nop
.Lfast_s_negative:
        bra     .Lfast_sn8
        nop
#else
        bra     .Lboundary
        nop
#endif

.Lback:
        cmp/pz  r5
        bf      .Lboundary
        mov     r13,r0
        sub     r5,r0
        cmp/eq  #3,r0
        bf      .Lboundary
        /* Third back: the previous final front vertex becomes EOL. */
        fschg
        COPY_VERTEX 2
        fschg
        fldi0   fr7
        TRACE_PIECE
        mov     #-1,r5
.Lboundary:
        cmp/hs  r10,r6
        bt      .Lstrip_end
        mov.l   @r15,r0
        tst     r0,r0
        bt      .Ladvance
        mov.l   @(4,r15),r0
        tst     #128,r0
        bf      .Lstrip_end
.Ladvance:
        fmov    fr10,fr8
        fmov    fr11,fr9
        fmov    fr12,fr10
        fmov    fr13,fr11
        add     #1,r13
        bra     .Ltriangle
        nop
.Lstrip_end:
        cmp/pz  r5
        bf      .Lnext_strip
        fschg
        COPY_VERTEX 2
        fschg
        fldi0   fr7
        TRACE_PIECE
.Lnext_strip:
        SHZ_JUMP .Lbatch_complete
#if SHZ_STRIP_FAST
        FAST_STEP .Lfast_wn8,8,9,10,11,0,0,.Lfast_wp10
        FAST_STEP .Lfast_wp10,10,11,8,9,1,0,.Lfast_wn8
        FAST_STEP .Lfast_wp8,8,9,10,11,1,0,.Lfast_wn10
        FAST_STEP .Lfast_wn10,10,11,8,9,0,0,.Lfast_wp8
        FAST_STEP .Lfast_an8,8,9,10,11,0,1,.Lfast_ap10
        FAST_STEP .Lfast_ap10,10,11,8,9,1,1,.Lfast_an8
        FAST_STEP .Lfast_ap8,8,9,10,11,1,1,.Lfast_an10
        FAST_STEP .Lfast_an10,10,11,8,9,0,1,.Lfast_ap8
        FAST_STEP .Lfast_sn8,8,9,10,11,0,2,.Lfast_sp10
        FAST_STEP .Lfast_sp10,10,11,8,9,1,2,.Lfast_sn8
        FAST_STEP .Lfast_sp8,8,9,10,11,1,2,.Lfast_sn10
        FAST_STEP .Lfast_sn10,10,11,8,9,0,2,.Lfast_sp8
.Lfast_terminal:
        /* Current C is the terminal pending front vertex, already in DR. */
        mov     r6,r5
        sub     r9,r5
        add     #-3,r5
        fschg
        fmov    dr6,@-r12
        fmov    dr4,@-r12
        fmov    dr2,@-r12
        fmov    dr0,@-r12
        mov     #-16,r0
        shll16  r0
        shll8   r0
        mov.l   r0,@r12
        pref    @r12
        add     #32,r12
        fschg
        fldi0   fr7
        TRACE_PIECE
        SHZ_JUMP .Lbatch_complete
#endif
.Lfinish:
        mov.l   @(16,r15),r4
        mov.l   @(20,r15),r0
        tst     r0,r0
        bf      .Lworld_finish
        mov     r12,r0
        mov.l   @(20,r14),r1
        sub     r1,r0
        shlr2   r0
        shlr2   r0
        shlr    r0
        mov.l   r0,@(24,r4)
        mov.l   r12,@(20,r4)
        mov.l   @(28,r14),r0
        mov.l   r0,@(28,r4)
        bra     .Lrestore_public
        nop
.Lworld_finish:
        mov.l   @(24,r15),r0
        mov.l   r0,@r4
        mov.l   r12,@(24,r4)
.Lrestore_public:
        add     #96,r15
        fmov.s  @r15+,fr15
        fmov.s  @r15+,fr14
        fmov.s  @r15+,fr13
        fmov.s  @r15+,fr12
        lds.l   @r15+,fpscr
        lds.l   @r15+,pr
        mov.l   @r15+,r14
        mov.l   @r15+,r13
        mov.l   @r15+,r12
        mov.l   @r15+,r11
        mov.l   @r15+,r10
        mov.l   @r15+,r9
        mov.l   @r15+,r8
        rts
        nop
#include "shz_strip_fused.inc"
        .size _shz_strip_sq,.-_shz_strip_sq
