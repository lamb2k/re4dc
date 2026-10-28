/* Short-strip fused scan and world batch continuation. No SDK caller returns
 * between world strips; the public prologue owns one FPU/register lease.
 * F bit(t-1-i) is original triangle i. No SQ store precedes the clip decision.
 */
        .macro SHZ_SHL64 lo,hi
        shll \lo
        rotcl \hi
        .endm
        .macro SHZ_SHR64 lo,hi
        shlr \hi
        rotcr \lo
        .endm
        .macro SHZ_LOAD_XY x,y,codes,stream
        mov.b @r4+,r0
        extu.b r0,r0
        .if \stream
        mov r0,r1
        .endif
        .if \codes == 0
        and r11,r0
        .endif
        .if \codes
        mov.b @(r0,r7),r1
        and r1,r2
        or r1,r3
        .endif
        .if \codes
        shld r11,r0
        .else
        shld r3,r0
        .endif
        add r8,r0
        add #4,r0
        fmov.s @r0+,fr\x
        fmov.s @r0,fr\y
        .endm
        .macro SHZ_PHASE label,ax,ay,bx,by,cx,cy,positive,codes,stream,next
\label:
        .if \stream
        mov r1,r0
        tst #128,r0
        bf .Lphase_terminal\@
        .endif
        dt r13
        bt .Lphase_terminal\@
        fsub fr\ay,fr2
        mov.b @r4+,r0
        fsub fr\ax,fr3
        fsub fr\ax,fr0
        extu.b r0,r0
        .if \stream
        mov r0,r1
        .endif
        fsub fr\ay,fr1
        .if \codes == 0
        and r11,r0
        .endif
        fmul fr3,fr2
        .if \codes
        mov.b @(r0,r7),r1
        shld r11,r0
        and r1,r2
        or r1,r3
        .else
        shld r3,r0
        .endif
        fneg fr2
        add r8,r0
        fmac fr0,fr1,fr2
        add #4,r0
        fmov.s @r0+,fr\ax
        fmov.s @r0,fr\ay
        .if \positive
        fcmp/gt fr14,fr2
        .else
        fcmp/gt fr2,fr14
        .endif
        /* FCMP has consumed this determinant. Seed the next compiler DAG
         * in the T latency, carry-pair slots and branch delay. These FMOVs
         * preserve T and never touch opposite-bank registers. */
        fmov fr\cy,fr2
        rotcl r5
        fmov fr\cx,fr0
        rotcl r6
        fmov fr\ax,fr3
        bra \next
        fmov fr\ay,fr1
.Lphase_terminal\@:
        SHZ_STRIP_AREA \ax,\ay,\bx,\by,\cx,\cy
        .if \positive
        fcmp/gt fr14,fr2
        .else
        fcmp/gt fr2,fr14
        .endif
        rotcl r5
        rotcl r6
        SHZ_JUMP .Lfused_scan_end
        .endm
        .macro SHZ_START label,codes,stream
\label:
        SHZ_LOAD_XY 8,9,\codes,\stream
        .if \stream
        mov r1,r0
        tst #128,r0
        bt 997f
        SHZ_JUMP .Lfused_scan_end
997:
        .endif
        dt r13
        bf 998f
        SHZ_JUMP .Lfused_scan_end
998:
        SHZ_LOAD_XY 10,11,\codes,\stream
        .if \stream
        mov r1,r0
        tst #128,r0
        bt 997f
        SHZ_JUMP .Lfused_scan_end
997:
        .endif
        dt r13
        bf 998f
        SHZ_JUMP .Lfused_scan_end
998:
        SHZ_LOAD_XY 12,13,\codes,\stream
        fmov fr11,fr2
        fmov fr12,fr3
        fmov fr10,fr0
        fmov fr13,fr1
        mov.l @(16,r14),r0
        cmp/eq #1,r0
        bt \label\()p0
        bra \label\()n0
        nop
        SHZ_PHASE \label\()p0,8,9,10,11,12,13,1,\codes,\stream,\label\()p1
        SHZ_PHASE \label\()p1,10,11,12,13,8,9,0,\codes,\stream,\label\()p2
        SHZ_PHASE \label\()p2,12,13,8,9,10,11,1,\codes,\stream,\label\()p3
        SHZ_PHASE \label\()p3,8,9,10,11,12,13,0,\codes,\stream,\label\()p4
        SHZ_PHASE \label\()p4,10,11,12,13,8,9,1,\codes,\stream,\label\()p5
        SHZ_PHASE \label\()p5,12,13,8,9,10,11,0,\codes,\stream,\label\()p0
        SHZ_PHASE \label\()n0,8,9,10,11,12,13,0,\codes,\stream,\label\()n1
        SHZ_PHASE \label\()n1,10,11,12,13,8,9,1,\codes,\stream,\label\()n2
        SHZ_PHASE \label\()n2,12,13,8,9,10,11,0,\codes,\stream,\label\()n3
        SHZ_PHASE \label\()n3,8,9,10,11,12,13,1,\codes,\stream,\label\()n4
        SHZ_PHASE \label\()n4,10,11,12,13,8,9,0,\codes,\stream,\label\()n5
        SHZ_PHASE \label\()n5,12,13,8,9,10,11,1,\codes,\stream,\label\()n0
        .endm
.Lbatch_dispatch:
        mov.l @(20,r15),r0
        tst r0,r0
        bf .Lbatch_world
        cmp/hs r10,r9
        bf .Lfused_begin
        bra .Lfinish
        nop
.Lbatch_world:
        mov.l @(24,r15),r9
        mov.l @(28,r15),r10
        cmp/hs r10,r9
        bf 995f
        SHZ_JUMP .Lfinish
995:
        mov.b @r9,r0
        extu.b r0,r0
        tst r0,r0
        bf 995f
        SHZ_JUMP .Lfinish
995:
        add #1,r9
        mov.l r9,@(4,r14)
        mov.l r0,@(8,r14)
        mov r9,r10
        add r0,r10
        mov.l r10,@(40,r15)
        mov #0,r1
        mov.l r1,@(12,r15)
        mov.b @r9,r0
        extu.b r0,r0
        mov.l @(32,r15),r7
        mov.b @(r0,r7),r1
        mov.l @(8,r14),r13
        mov.l @(36,r15),r0
        cmp/hi r0,r13
        bf .Lworld_first_code
        mov r1,r0
        tst #3,r0
        bf .Lworld_codes_gate
        SHZ_JUMP .Lfinish
.Lworld_first_code:
        mov r1,r0
        tst #63,r0
        bf .Lworld_codes_gate
        mov #64,r0
        cmp/hi r0,r13
        bt .Lworld_codes_gate
        bra .Lfused_begin
        nop
.Lworld_codes_gate:
        mov #1,r0
        mov.l r0,@(12,r15)
        mov.l @(8,r14),r0
        /* Long strips retain the qualified state machine. Codes still finish
         * before any write, under this same public register lease. */
        mov r9,r4
        mov r0,r13
        mov #-1,r2
        extu.b r2,r2
        mov #0,r3
        mov.l @(32,r15),r7
.Llong_codes:
        mov.b @r4+,r0
        extu.b r0,r0
        mov.b @(r0,r7),r1
        dt r13
        and r1,r2
        bf/s .Llong_codes
        or r1,r3
        mov.l r4,@(44,r15)
        bra .Lfused_world_decide
        nop
.Lfused_begin:
        mov.l r10,@(56,r15)
        mov r10,r13
        sub r9,r13
        mov #64,r0
        cmp/hi r0,r13
        bf .Lfused_count_ready
        mov.l @r15,r1
        tst r1,r1
        bf .Lfused_cap_stream
        SHZ_JUMP .Lstrip_start
.Lfused_cap_stream:
        mov #64,r13
.Lfused_count_ready:
        mov r9,r4
        mov #0,r5
        mov #0,r6
        mov #-1,r2
        extu.b r2,r2
        mov #0,r3
        fldi0 fr14
        mov.l @(20,r15),r0
        tst r0,r0
        bt .Lfused_actor_setup
        mov.l @(12,r15),r0
        cmp/eq #2,r0
        bt .Lfused_prepassed_setup
        mov #5,r11
        mov.l @(32,r15),r7
        SHZ_JUMP .Lfused_world_start
.Lfused_prepassed_setup:
        mov #5,r3
        SHZ_JUMP .Lfused_plain_start
.Lfused_actor_setup:
        mov #5,r3
        mov.l @r15,r0
        tst r0,r0
        bt .Lfused_dispatch_plain
        SHZ_JUMP .Lfused_stream_start
.Lfused_dispatch_plain:
        SHZ_JUMP .Lfused_plain_start
        SHZ_START .Lfused_world_start,1,0
        SHZ_START .Lfused_plain_start,0,0
        SHZ_START .Lfused_stream_start,0,1
.Lfused_scan_end:
        mov.l r4,@(44,r15)
        /* A64-index actor prefix without EOL is speculative: discard its
         * mask and enter the qualified long path from the original base. */
        mov.l @r15,r0
        tst r0,r0
        bt .Lfused_not_stream
        mov r1,r0
        tst #128,r0
        bf .Lfused_not_stream
        cmp/hs r10,r4
        bt .Lfused_not_stream
        SHZ_JUMP .Lstrip_start
.Lfused_not_stream:
        mov.l @(20,r15),r0
        tst r0,r0
        bt .Lfused_mask
        mov #-1,r11
        extu.b r11,r11
        mov.l @(12,r15),r0
        cmp/eq #2,r0
        bf .Lfused_world_decide
        bra .Lfused_mask
        nop
.Lfused_world_decide:
        mov r2,r0
        tst #3,r0
        bf .Lbatch_world_cull
        mov r3,r0
        tst #3,r0
        bt 996f
        SHZ_JUMP .Lfinish
996:
        mov.l @(8,r14),r1
        mov.l @(36,r15),r0
        cmp/hi r0,r1
        bf 995f
        SHZ_JUMP .Lfinish
995:
        mov r2,r0
        tst #60,r0
        bf .Lbatch_world_cull
        mov #64,r0
        cmp/hi r0,r1
        bf .Lworld_short_decided
        SHZ_JUMP .Lstrip_start
.Lworld_short_decided:
        mov.l @(12,r15),r0
        cmp/eq #1,r0
        bf .Lfused_mask
        mov #2,r0
        mov.l r0,@(12,r15)
        bra .Lfused_begin
        nop
.Lfused_mask:
        mov.l @(44,r15),r13
        sub r9,r13
        add #-2,r13
        cmp/pl r13
        bf .Lfused_complete
        mov r5,r0
        or r6,r0
        tst r0,r0
        bt .Lfused_complete
        /* All-front needs neither mask algebra nor a bit-by-bit span walk. */
        mov #32,r0
        cmp/hi r0,r13
        bt .Lfused_all_hi
        mov r6,r0
        tst r0,r0
        bf .Lfused_mixed
        mov r13,r0
        add #-32,r0
        mov #-1,r1
        shld r0,r1
        cmp/eq r1,r5
        bt .Lfused_all_front
        bra .Lfused_mixed
        nop
.Lfused_all_hi:
        mov #-1,r0
        cmp/eq r0,r5
        bf .Lfused_mixed
        mov r13,r0
        add #-64,r0
        mov #-1,r1
        shld r0,r1
        cmp/eq r1,r6
        bf .Lfused_mixed
.Lfused_all_front:
        mov r13,r4
        mov #0,r13
        mov #0,r0
        mov.l r0,@(8,r15)
        bra .Lfused_emit
        nop
.Lfused_mixed:
        /* K=F|((F<<1)&(F>>1))|((F<<1)&(F>>2))|((F<<2)&(F>>1)). */
        mov r5,r4
        mov r6,r7
        mov r5,r0
        mov r6,r1
        SHZ_SHL64 r0,r1
        mov r5,r2
        mov r6,r3
        SHZ_SHR64 r2,r3
        and r2,r0
        and r3,r1
        or r0,r4
        or r1,r7
        SHZ_SHR64 r2,r3
        mov r5,r0
        mov r6,r1
        SHZ_SHL64 r0,r1
        and r2,r0
        and r3,r1
        or r0,r4
        or r1,r7
        mov r5,r0
        mov r6,r1
        SHZ_SHL64 r0,r1
        SHZ_SHL64 r0,r1
        mov r5,r2
        mov r6,r3
        SHZ_SHR64 r2,r3
        and r2,r0
        and r3,r1
        or r0,r4
        or r1,r7
        /* Reverse original run starts R=K&~(K>>1), before parity repair. */
        mov r4,r0
        mov r7,r1
        SHZ_SHR64 r0,r1
        not r0,r0
        not r1,r1
        and r4,r0
        and r7,r1
        mov r13,r2
        mov #1,r3
        tst r3,r2
        bt .Lfused_even_t
        mov.l .Lfused_odd_mask,r2
        bra .Lfused_repair
        nop
.Lfused_even_t:
        mov.l .Lfused_even_mask,r2
.Lfused_repair:
        and r2,r0
        and r2,r1
        SHZ_SHL64 r0,r1
        or r4,r0
        or r7,r1
        mov r0,r5
        mov r1,r6
        /* Normalize reverse E to its most significant bit for span traversal.
         * No shift uses64 or relies on masked shift32 behaviour. */
        mov #32,r0
        cmp/hi r0,r13
        bt .Lfused_normalize_hi
        sub r13,r0
        shld r0,r5
        mov r5,r6
        mov #0,r5
        bra .Lfused_spans
        nop
.Lfused_normalize_hi:
        sub r13,r0
        mov r5,r1
        shld r0,r1
        add #32,r0
        shld r0,r6
        shld r0,r5
        or r1,r6
.Lfused_spans:
        mov #0,r4
.Lfused_find:
        SHZ_SHL64 r5,r6
        bf .Lfused_skip
        mov.l r4,@(8,r15)
.Lfused_run:
        add #1,r4
        dt r13
        bt .Lfused_emit
        SHZ_SHL64 r5,r6
        bt .Lfused_run
.Lfused_emit:
        mov.l r5,@(48,r15)
        mov.l r6,@(52,r15)
        mov.l r4,@(60,r15)
        mov r4,r5
        add #-1,r5
        mov r4,r7
        add #1,r7
        mov.l @(8,r15),r4
        mov.l @(28,r14),r0
        add #1,r0
        mov.l r0,@(28,r14)
        /* Peeled lean SQ burst: one address/load/store stream per span. */
        mov r9,r6
        add r4,r6
        sub r4,r7
        mov r7,r4
        mov #5,r7
        mov.b @r6+,r0
        extu.b r0,r0
        and r11,r0
        shld r7,r0
        add r8,r0
        add #32,r12
        fschg
        mov r11,r1
        mov #127,r2
        cmp/eq r2,r1
        bt .Lfused_actor_copy
.Lfused_world_copy:
        fmov @r0+,dr0
        fmov @r0+,dr2
        fmov @r0+,dr4
        fmov @r0+,dr6
        mov.b @r6+,r1
        fmov dr6,@-r12
        extu.b r1,r0
        fmov dr4,@-r12
        shld r7,r0
        fmov dr2,@-r12
        add r8,r0
        fmov dr0,@-r12
        dt r4
        pref @r12
        bf/s .Lfused_world_copy
        add #64,r12
        bra .Lfused_terminal
        nop
.Lfused_actor_copy:
        mov #-32,r2
        shll16 r2
        shll8 r2
.Lfused_actor_loop:
        fmov @r0+,dr0
        fmov @r0+,dr2
        fmov @r0+,dr4
        fmov @r0+,dr6
        mov.b @r6+,r1
        fmov dr6,@-r12
        extu.b r1,r0
        fmov dr4,@-r12
        and r11,r0
        fmov dr2,@-r12
        shld r7,r0
        fmov dr0,@-r12
        add r8,r0
        mov.l r2,@r12
        dt r4
        pref @r12
        bf/s .Lfused_actor_loop
        add #64,r12
.Lfused_terminal:
        fmov @r0+,dr0
        mov #-16,r2
        fmov @r0+,dr2
        shll16 r2
        fmov @r0+,dr4
        shll8 r2
        fmov @r0+,dr6
        fmov dr6,@-r12
        fmov dr4,@-r12
        fmov dr2,@-r12
        fmov dr0,@-r12
        mov.l r2,@r12
        pref @r12
        add #32,r12
        fschg
        TRACE_PIECE
        fldi0 fr14
        mov.l @(48,r15),r5
        mov.l @(52,r15),r6
        mov.l @(60,r15),r4
        tst r13,r13
        bt .Lfused_complete
.Lfused_skip:
        add #1,r4
        dt r13
        bf .Lfused_find
.Lfused_complete:
        mov.l @(44,r15),r6
        mov.l @(56,r15),r10
        bra .Lbatch_complete
        nop
        .align 2
.Lfused_odd_mask: .long 0xaaaaaaaa
.Lfused_even_mask: .long 0x55555555
.Lbatch_world_cull:
        mov.l @(16,r15),r0
        mov.l @(28,r0),r1
        add #1,r1
        mov.l r1,@(28,r0)
        bra .Lbatch_world_advance
        nop
.Lbatch_complete:
        mov.l @(20,r15),r0
        tst r0,r0
        bf .Lbatch_world_accept
        mov r6,r9
        SHZ_JUMP .Lbatch_dispatch
.Lbatch_world_accept:
        mov.l @(16,r15),r0
        mov.l @(32,r0),r1
        add #1,r1
        mov.l r1,@(32,r0)
        mov.l @(8,r14),r2
        mov #2,r3
        cmp/hs r3,r2
        bt .Lbatch_triangle_count
        mov #2,r2
.Lbatch_triangle_count:
        add #-2,r2
        mov.l @(36,r0),r1
        add r2,r1
        mov.l r1,@(36,r0)
.Lbatch_world_advance:
        mov.l @(40,r15),r0
        mov.l r0,@(24,r15)
        SHZ_JUMP .Lbatch_dispatch
