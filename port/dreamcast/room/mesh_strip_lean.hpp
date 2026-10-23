#pragma once
// MESH_STRIP_LEAN (default off): walk_lean(), the meshlet strip walk's common path in one register-resident
// loop. For kChecksAll meshlets (outcode bits 5..2 screen, 1..0 depth) on the store-queue sink, strip by
// strip from s until a strip that needs the clipper, or the end:
//   codes  all/any over the strip's outcodes: the same index bytes, the same sign-extending outcode loads
//          and the same and/or as mesh_fastpath.hpp codes() (all starts at 0xff, any at 0), so the words
//          are identical; the next index is loaded while the current code is folded in.
//   decide in meshlet()'s order: all&3 depth cull, any&3 or n > lim clip (stop: s is left on the strip's
//          count byte), all&0x3c screen cull, else emit. lim is the caller's current 'limit' (the slots
//          left after the cache borrow: ~119 on the PS2 world direct path, so the test is needed).
//   emit   the same bursts as emit_sq(): each referenced 32-byte cache entry by four 64-bit loads and four
//          pre-decrementing stores, EOL written into the last vertex's flags word before its burst leaves,
//          one PREF per vertex. The next index byte is loaded between the last load and the first store,
//          the next entry's address is formed during the stores, and the last vertex is peeled.
// FPSCR.SZ (64-bit fmov) is set once per call: nothing else in the loop uses the FPU.
// Returns s; q advances 32 B per emitted vertex; culled / emitted count the strips.
#include "mesh_fastpath.hpp"
#if defined(RE4DC_CPU_BACKFACE) && RE4DC_CPU_BACKFACE == 2
#include "backface_sh4.hpp"
#endif

namespace re4dc::vp {
#if defined(__sh__)
static_assert(PVR_CMD_VERTEX_EOL==0xf0000000U,"walk_lean builds EOL as -16 << 24");
inline const std::uint8_t* walk_lean(const std::uint8_t* s,const std::uint8_t* end,const std::uint8_t* oc,
                                     const pvr_vertex_t* cache,unsigned lim,std::uint32_t*& q,unsigned& culled,unsigned& emitted){
    std::uint32_t* sq=q;unsigned c=culled,e=emitted;
    const std::uint8_t* ip;unsigned n,all,any,t;
    __asm__ __volatile__(
        "fschg\n"
        "1:\n\t"
        "cmp/hs  %[end],%[s]\n\t"           /* s >= end: done */
        "bt      9f\n\t"
        "mov.b   @%[s]+,%[n]\n\t"           /* n */
        "mov     #-1,%[all]\n\t"
        "mov     %[s],%[ip]\n\t"
        "extu.b  %[n],%[n]\n\t"
        "mov.b   @%[ip]+,r0\n\t"            /* codes: index 0 */
        "extu.b  %[all],%[all]\n\t"         /* all = 0xff */
        "mov     #0,%[any]\n\t"
        "dt      %[n]\n\t"
        "bt/s    3f\n\t"
        "extu.b  r0,r0\n"
        "2:\n\t"
        "mov.b   @(r0,%[oc]),%[t]\n\t"      /* code k */
        "mov.b   @%[ip]+,r0\n\t"            /* index k+1 */
        "dt      %[n]\n\t"
        "and     %[t],%[all]\n\t"
        "extu.b  r0,r0\n\t"
        "bf/s    2b\n\t"
        "or      %[t],%[any]\n"
        "3:\n\t"
        "mov.b   @(r0,%[oc]),%[t]\n\t"      /* last code */
        "mov     %[ip],%[n]\n\t"
        "and     %[t],%[all]\n\t"
        "sub     %[s],%[n]\n\t"             /* n again (ip = s + n) */
        "or      %[t],%[any]\n\t"
        "mov     %[all],r0\n\t"
        "tst     #3,r0\n\t"                 /* depth cull */
        "bf/s    5f\n\t"
        "mov     %[any],r0\n\t"
        "tst     #3,r0\n\t"                 /* clip: stop on the count byte */
        "bf/s    8f\n\t"
        "mov     %[all],r0\n\t"
        "cmp/hi  %[lim],%[n]\n\t"           /* clip: n > limit */
        "bt      8f\n\t"
        "tst     #60,r0\n\t"                /* screen cull */
        "bf/s    5f\n\t"
        "mov.b   @%[s]+,%[t]\n\t"           /* emit: index 0 (harmless if culled: s is reset from ip) */
        "add     #32,%[sq]\n\t"             /* sq = this vertex's slot + 32 */
        "extu.b  %[t],r0\n\t"
        "shll2   r0\n\t"
        "shll2   r0\n\t"
        "add     r0,r0\n\t"
        "dt      %[n]\n\t"
        "bt/s    7f\n\t"
        "add     %[cache],r0\n"
        "6:\n\t"                            /* n-1 vertices */
        "fmov    @r0+,dr0\n\t"
        "dt      %[n]\n\t"
        "fmov    @r0+,dr2\n\t"
        "fmov    @r0+,dr4\n\t"
        "fmov    @r0+,dr6\n\t"
        "mov.b   @%[s]+,%[t]\n\t"           /* next index */
        "fmov    dr6,@-%[sq]\n\t"
        "extu.b  %[t],r0\n\t"
        "fmov    dr4,@-%[sq]\n\t"
        "shll2   r0\n\t"
        "fmov    dr2,@-%[sq]\n\t"
        "shll2   r0\n\t"
        "fmov    dr0,@-%[sq]\n\t"
        "add     r0,r0\n\t"             /* not shll: T carries dt's result to bf/s */
        "pref    @%[sq]\n\t"
        "add     %[cache],r0\n\t"
        "bf/s    6b\n\t"
        "add     #64,%[sq]\n"               /* the next slot + 32 */
        "7:\n\t"                            /* last vertex: EOL into its flags word before 'pref' */
        "fmov    @r0+,dr0\n\t"
        "mov     #-16,%[t]\n\t"
        "fmov    @r0+,dr2\n\t"
        "shll16  %[t]\n\t"
        "fmov    @r0+,dr4\n\t"
        "shll8   %[t]\n\t"
        "fmov    @r0+,dr6\n\t"
        "add     #1,%[e]\n\t"
        "fmov    dr6,@-%[sq]\n\t"
        "fmov    dr4,@-%[sq]\n\t"
        "fmov    dr2,@-%[sq]\n\t"
        "fmov    dr0,@-%[sq]\n\t"
        "mov.l   %[t],@%[sq]\n\t"
        "pref    @%[sq]\n\t"
        "bra     1b\n\t"
        "add     #32,%[sq]\n"
        "5:\n\t"                            /* culled: s past the indices */
        "mov     %[ip],%[s]\n\t"
        "bra     1b\n\t"
        "add     #1,%[c]\n"
        "8:\n\t"
        "add     #-1,%[s]\n"
        "9:\n\t"
        "fschg\n"
        : [s]"+r"(s),[sq]"+r"(sq),[c]"+r"(c),[e]"+r"(e),[ip]"=&r"(ip),[n]"=&r"(n),[all]"=&r"(all),
          [any]"=&r"(any),[t]"=&r"(t)
        : [end]"r"(end),[oc]"r"(oc),[cache]"r"(cache),[lim]"r"(lim)
        : "r0","fr0","fr1","fr2","fr3","fr4","fr5","fr6","fr7","t","memory");
    q=sq;culled=c;emitted=e;
    return s;
}
#if defined(RE4DC_CPU_BACKFACE) && RE4DC_CPU_BACKFACE == 2
// The CPU2 culling walk keeps the pipelined integer outcode scan. Facing,
// run selection, parity and the peeled SQ bursts are the common SH-4 kernel;
// there is no C facing or C strip emitter fallback. Stops on the count byte of
// the first depth-crossing / oversize strip, as walk_lean does. Source packages
// have validated positive strip counts; world indices use all eight bits.
inline const std::uint8_t* walk_lean_sq(const std::uint8_t* s,const std::uint8_t* end,const std::uint8_t* oc,
                                       const pvr_vertex_t* cache,unsigned lim,unsigned cull,std::uint32_t*& q,
                                       unsigned& culled,unsigned& emitted,unsigned& accepted_triangles){
    shz_strip_walk_t context{s,end,oc,cache,lim,cull,q,culled,emitted,accepted_triangles};
    shz_strip_walk_sq(&context);
    q=context.q;culled=context.culled;emitted=context.emitted;
    accepted_triangles=context.accepted_triangles;
    s=context.cursor;
    return s;
}
#endif
#endif
} // namespace re4dc::vp
