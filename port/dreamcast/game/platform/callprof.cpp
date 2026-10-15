// CALLPROF=1 (game30.mk, diagnostic builds only; lane crowd12 2026-10-15): call sites of shared maths helpers by
// calls (ld --wrap thunks below keep every argument register) and actor parts per model per entry path. Printed
// every 120 frames (native_ps2_world.cpp's flush), then cleared. Rows are approximate under interrupts.
#ifndef RE4DC_CALLPROF
#define RE4DC_CALLPROF 0
#endif
#if RE4DC_CALLPROF
#include <cstdint>
extern "C" void re4dc_log(const char*,...);
namespace {
constexpr unsigned kKinds=16;
const char* const kNames[kKinds]={"PSMTXConcat","PSMTXInverse","PSMTXMultVec","PSMTXMultVecSR","RotVector","sinf","cosf","acosf","atan2f","sqrtf","memcmp","re4dc_sincosf","PSMTXRotAxisRad","PSMTXRotRad","RotMatrix","low_RotMatrix"};
struct Row { std::uintptr_t ra; unsigned calls; };
constexpr unsigned kRows=RE4DC_CALLPROF>=2?256:64;  // CALLPROF=2 (lane approx): 256 slots, top 48 rows
constexpr unsigned kTop=RE4DC_CALLPROF>=2?48:10;
Row rows[kKinds][kRows];
unsigned lost[kKinds];
struct PartRow { unsigned key; unsigned parts; };
PartRow parts[3][64];
volatile bool logging=false;
}
extern "C" void re4dc_callprof_note(unsigned kind,void* ra){
    if(logging||kind>=kKinds)return;
    const auto a=reinterpret_cast<std::uintptr_t>(ra);
    unsigned h=unsigned((a>>1)^(a>>7))&(kRows-1U);
    for(unsigned probe=0;probe<12;++probe,h=(h+1U)&(kRows-1U)){
        Row& r=rows[kind][h];
        if(r.ra==a || !r.ra){r.ra=a;++r.calls;return;}
    }
    ++lost[kind];
}
// path 0 re4dc_actor_submit, 1 one_chunk_core, 2 re4dc_model_submit; key = kindid << 8 | id (0xffff: no model)
extern "C" void re4dc_callprof_part_key(unsigned path,unsigned key){
    if(logging||path>2)return;
    for(PartRow& r:parts[path]){
        if(r.parts && r.key==key){++r.parts;return;}
        if(!r.parts){r.key=key;r.parts=1;return;}
    }
}
extern "C" void re4dc_callprof_log(unsigned frame,unsigned frames){
    logging=true;
    for(unsigned k=0;k<kKinds;++k){
        Row top[kTop]{};
        unsigned total=0;
        for(const Row& r:rows[k]){
            if(!r.ra)continue;
            total+=r.calls;
            for(unsigned i=0;i<kTop;++i)if(r.calls>top[i].calls){for(unsigned j=kTop-1;j>i;--j)top[j]=top[j-1];top[i]=r;break;}
        }
        if(total)re4dc_log("CALLPROF frame=%u fn=%s total=%u per_frame=%u lost=%u\n",frame,kNames[k],total,total/frames,lost[k]);
        for(unsigned i=0;i<kTop && top[i].ra;++i)
            re4dc_log("CALLPROF frame=%u fn=%s rank=%u ra=%08x calls=%u per_frame=%u\n",frame,kNames[k],i,unsigned(top[i].ra),
                top[i].calls,top[i].calls/frames);
        for(Row& r:rows[k])r={};
        lost[k]=0;
    }
    static const char* const kPath[3]={"actor_submit","one_chunk","model_submit"};
    for(unsigned p=0;p<3;++p){
        for(PartRow& r:parts[p]){
            if(!r.parts)continue;
            re4dc_log("PARTPROF frame=%u path=%s kind=%u id=%02x parts=%u per_frame_x10=%u\n",frame,kPath[p],r.key>>8,r.key&0xffU,
                r.parts,r.parts*10U/frames);
            r={};
        }
    }
    logging=false;
}
asm(R"ASM(
        .pushsection .text
        .global ___wrap_PSMTXConcat
        .type ___wrap_PSMTXConcat, @function
        .align 2
___wrap_PSMTXConcat:
        mov.l r4,@-r15
        mov.l r5,@-r15
        mov.l r6,@-r15
        mov.l r7,@-r15
        fmov.s fr4,@-r15
        fmov.s fr5,@-r15
        fmov.s fr6,@-r15
        fmov.s fr7,@-r15
        fmov.s fr8,@-r15
        fmov.s fr9,@-r15
        fmov.s fr10,@-r15
        fmov.s fr11,@-r15
        sts.l pr,@-r15
        sts pr,r5
        mov #0,r4
        mov.l 1f,r0
        jsr @r0
        nop
        lds.l @r15+,pr
        fmov.s @r15+,fr11
        fmov.s @r15+,fr10
        fmov.s @r15+,fr9
        fmov.s @r15+,fr8
        fmov.s @r15+,fr7
        fmov.s @r15+,fr6
        fmov.s @r15+,fr5
        fmov.s @r15+,fr4
        mov.l @r15+,r7
        mov.l @r15+,r6
        mov.l @r15+,r5
        mov.l @r15+,r4
        mov.l 2f,r0
        jmp @r0
        nop
        .align 2
1:      .long _re4dc_callprof_note
2:      .long ___real_PSMTXConcat
        .global ___wrap_PSMTXInverse
        .type ___wrap_PSMTXInverse, @function
        .align 2
___wrap_PSMTXInverse:
        mov.l r4,@-r15
        mov.l r5,@-r15
        mov.l r6,@-r15
        mov.l r7,@-r15
        fmov.s fr4,@-r15
        fmov.s fr5,@-r15
        fmov.s fr6,@-r15
        fmov.s fr7,@-r15
        fmov.s fr8,@-r15
        fmov.s fr9,@-r15
        fmov.s fr10,@-r15
        fmov.s fr11,@-r15
        sts.l pr,@-r15
        sts pr,r5
        mov #1,r4
        mov.l 1f,r0
        jsr @r0
        nop
        lds.l @r15+,pr
        fmov.s @r15+,fr11
        fmov.s @r15+,fr10
        fmov.s @r15+,fr9
        fmov.s @r15+,fr8
        fmov.s @r15+,fr7
        fmov.s @r15+,fr6
        fmov.s @r15+,fr5
        fmov.s @r15+,fr4
        mov.l @r15+,r7
        mov.l @r15+,r6
        mov.l @r15+,r5
        mov.l @r15+,r4
        mov.l 2f,r0
        jmp @r0
        nop
        .align 2
1:      .long _re4dc_callprof_note
2:      .long ___real_PSMTXInverse
        .global ___wrap_PSMTXMultVec
        .type ___wrap_PSMTXMultVec, @function
        .align 2
___wrap_PSMTXMultVec:
        mov.l r4,@-r15
        mov.l r5,@-r15
        mov.l r6,@-r15
        mov.l r7,@-r15
        fmov.s fr4,@-r15
        fmov.s fr5,@-r15
        fmov.s fr6,@-r15
        fmov.s fr7,@-r15
        fmov.s fr8,@-r15
        fmov.s fr9,@-r15
        fmov.s fr10,@-r15
        fmov.s fr11,@-r15
        sts.l pr,@-r15
        sts pr,r5
        mov #2,r4
        mov.l 1f,r0
        jsr @r0
        nop
        lds.l @r15+,pr
        fmov.s @r15+,fr11
        fmov.s @r15+,fr10
        fmov.s @r15+,fr9
        fmov.s @r15+,fr8
        fmov.s @r15+,fr7
        fmov.s @r15+,fr6
        fmov.s @r15+,fr5
        fmov.s @r15+,fr4
        mov.l @r15+,r7
        mov.l @r15+,r6
        mov.l @r15+,r5
        mov.l @r15+,r4
        mov.l 2f,r0
        jmp @r0
        nop
        .align 2
1:      .long _re4dc_callprof_note
2:      .long ___real_PSMTXMultVec
        .global ___wrap_PSMTXMultVecSR
        .type ___wrap_PSMTXMultVecSR, @function
        .align 2
___wrap_PSMTXMultVecSR:
        mov.l r4,@-r15
        mov.l r5,@-r15
        mov.l r6,@-r15
        mov.l r7,@-r15
        fmov.s fr4,@-r15
        fmov.s fr5,@-r15
        fmov.s fr6,@-r15
        fmov.s fr7,@-r15
        fmov.s fr8,@-r15
        fmov.s fr9,@-r15
        fmov.s fr10,@-r15
        fmov.s fr11,@-r15
        sts.l pr,@-r15
        sts pr,r5
        mov #3,r4
        mov.l 1f,r0
        jsr @r0
        nop
        lds.l @r15+,pr
        fmov.s @r15+,fr11
        fmov.s @r15+,fr10
        fmov.s @r15+,fr9
        fmov.s @r15+,fr8
        fmov.s @r15+,fr7
        fmov.s @r15+,fr6
        fmov.s @r15+,fr5
        fmov.s @r15+,fr4
        mov.l @r15+,r7
        mov.l @r15+,r6
        mov.l @r15+,r5
        mov.l @r15+,r4
        mov.l 2f,r0
        jmp @r0
        nop
        .align 2
1:      .long _re4dc_callprof_note
2:      .long ___real_PSMTXMultVecSR
        .global ___wrap_RotVector
        .type ___wrap_RotVector, @function
        .align 2
___wrap_RotVector:
        mov.l r4,@-r15
        mov.l r5,@-r15
        mov.l r6,@-r15
        mov.l r7,@-r15
        fmov.s fr4,@-r15
        fmov.s fr5,@-r15
        fmov.s fr6,@-r15
        fmov.s fr7,@-r15
        fmov.s fr8,@-r15
        fmov.s fr9,@-r15
        fmov.s fr10,@-r15
        fmov.s fr11,@-r15
        sts.l pr,@-r15
        sts pr,r5
        mov #4,r4
        mov.l 1f,r0
        jsr @r0
        nop
        lds.l @r15+,pr
        fmov.s @r15+,fr11
        fmov.s @r15+,fr10
        fmov.s @r15+,fr9
        fmov.s @r15+,fr8
        fmov.s @r15+,fr7
        fmov.s @r15+,fr6
        fmov.s @r15+,fr5
        fmov.s @r15+,fr4
        mov.l @r15+,r7
        mov.l @r15+,r6
        mov.l @r15+,r5
        mov.l @r15+,r4
        mov.l 2f,r0
        jmp @r0
        nop
        .align 2
1:      .long _re4dc_callprof_note
2:      .long ___real_RotVector
        .global ___wrap_sinf
        .type ___wrap_sinf, @function
        .align 2
___wrap_sinf:
        mov.l r4,@-r15
        mov.l r5,@-r15
        mov.l r6,@-r15
        mov.l r7,@-r15
        fmov.s fr4,@-r15
        fmov.s fr5,@-r15
        fmov.s fr6,@-r15
        fmov.s fr7,@-r15
        fmov.s fr8,@-r15
        fmov.s fr9,@-r15
        fmov.s fr10,@-r15
        fmov.s fr11,@-r15
        sts.l pr,@-r15
        sts pr,r5
        mov #5,r4
        mov.l 1f,r0
        jsr @r0
        nop
        lds.l @r15+,pr
        fmov.s @r15+,fr11
        fmov.s @r15+,fr10
        fmov.s @r15+,fr9
        fmov.s @r15+,fr8
        fmov.s @r15+,fr7
        fmov.s @r15+,fr6
        fmov.s @r15+,fr5
        fmov.s @r15+,fr4
        mov.l @r15+,r7
        mov.l @r15+,r6
        mov.l @r15+,r5
        mov.l @r15+,r4
        mov.l 2f,r0
        jmp @r0
        nop
        .align 2
1:      .long _re4dc_callprof_note
2:      .long ___real_sinf
        .global ___wrap_cosf
        .type ___wrap_cosf, @function
        .align 2
___wrap_cosf:
        mov.l r4,@-r15
        mov.l r5,@-r15
        mov.l r6,@-r15
        mov.l r7,@-r15
        fmov.s fr4,@-r15
        fmov.s fr5,@-r15
        fmov.s fr6,@-r15
        fmov.s fr7,@-r15
        fmov.s fr8,@-r15
        fmov.s fr9,@-r15
        fmov.s fr10,@-r15
        fmov.s fr11,@-r15
        sts.l pr,@-r15
        sts pr,r5
        mov #6,r4
        mov.l 1f,r0
        jsr @r0
        nop
        lds.l @r15+,pr
        fmov.s @r15+,fr11
        fmov.s @r15+,fr10
        fmov.s @r15+,fr9
        fmov.s @r15+,fr8
        fmov.s @r15+,fr7
        fmov.s @r15+,fr6
        fmov.s @r15+,fr5
        fmov.s @r15+,fr4
        mov.l @r15+,r7
        mov.l @r15+,r6
        mov.l @r15+,r5
        mov.l @r15+,r4
        mov.l 2f,r0
        jmp @r0
        nop
        .align 2
1:      .long _re4dc_callprof_note
2:      .long ___real_cosf
        .global ___wrap_acosf
        .type ___wrap_acosf, @function
        .align 2
___wrap_acosf:
        mov.l r4,@-r15
        mov.l r5,@-r15
        mov.l r6,@-r15
        mov.l r7,@-r15
        fmov.s fr4,@-r15
        fmov.s fr5,@-r15
        fmov.s fr6,@-r15
        fmov.s fr7,@-r15
        fmov.s fr8,@-r15
        fmov.s fr9,@-r15
        fmov.s fr10,@-r15
        fmov.s fr11,@-r15
        sts.l pr,@-r15
        sts pr,r5
        mov #7,r4
        mov.l 1f,r0
        jsr @r0
        nop
        lds.l @r15+,pr
        fmov.s @r15+,fr11
        fmov.s @r15+,fr10
        fmov.s @r15+,fr9
        fmov.s @r15+,fr8
        fmov.s @r15+,fr7
        fmov.s @r15+,fr6
        fmov.s @r15+,fr5
        fmov.s @r15+,fr4
        mov.l @r15+,r7
        mov.l @r15+,r6
        mov.l @r15+,r5
        mov.l @r15+,r4
        mov.l 2f,r0
        jmp @r0
        nop
        .align 2
1:      .long _re4dc_callprof_note
2:      .long ___real_acosf
        .global ___wrap_atan2f
        .type ___wrap_atan2f, @function
        .align 2
___wrap_atan2f:
        mov.l r4,@-r15
        mov.l r5,@-r15
        mov.l r6,@-r15
        mov.l r7,@-r15
        fmov.s fr4,@-r15
        fmov.s fr5,@-r15
        fmov.s fr6,@-r15
        fmov.s fr7,@-r15
        fmov.s fr8,@-r15
        fmov.s fr9,@-r15
        fmov.s fr10,@-r15
        fmov.s fr11,@-r15
        sts.l pr,@-r15
        sts pr,r5
        mov #8,r4
        mov.l 1f,r0
        jsr @r0
        nop
        lds.l @r15+,pr
        fmov.s @r15+,fr11
        fmov.s @r15+,fr10
        fmov.s @r15+,fr9
        fmov.s @r15+,fr8
        fmov.s @r15+,fr7
        fmov.s @r15+,fr6
        fmov.s @r15+,fr5
        fmov.s @r15+,fr4
        mov.l @r15+,r7
        mov.l @r15+,r6
        mov.l @r15+,r5
        mov.l @r15+,r4
        mov.l 2f,r0
        jmp @r0
        nop
        .align 2
1:      .long _re4dc_callprof_note
2:      .long ___real_atan2f
        .global ___wrap_sqrtf
        .type ___wrap_sqrtf, @function
        .align 2
___wrap_sqrtf:
        mov.l r4,@-r15
        mov.l r5,@-r15
        mov.l r6,@-r15
        mov.l r7,@-r15
        fmov.s fr4,@-r15
        fmov.s fr5,@-r15
        fmov.s fr6,@-r15
        fmov.s fr7,@-r15
        fmov.s fr8,@-r15
        fmov.s fr9,@-r15
        fmov.s fr10,@-r15
        fmov.s fr11,@-r15
        sts.l pr,@-r15
        sts pr,r5
        mov #9,r4
        mov.l 1f,r0
        jsr @r0
        nop
        lds.l @r15+,pr
        fmov.s @r15+,fr11
        fmov.s @r15+,fr10
        fmov.s @r15+,fr9
        fmov.s @r15+,fr8
        fmov.s @r15+,fr7
        fmov.s @r15+,fr6
        fmov.s @r15+,fr5
        fmov.s @r15+,fr4
        mov.l @r15+,r7
        mov.l @r15+,r6
        mov.l @r15+,r5
        mov.l @r15+,r4
        mov.l 2f,r0
        jmp @r0
        nop
        .align 2
1:      .long _re4dc_callprof_note
2:      .long ___real_sqrtf
        .global ___wrap_memcmp
        .type ___wrap_memcmp, @function
        .align 2
___wrap_memcmp:
        mov.l r4,@-r15
        mov.l r5,@-r15
        mov.l r6,@-r15
        mov.l r7,@-r15
        fmov.s fr4,@-r15
        fmov.s fr5,@-r15
        fmov.s fr6,@-r15
        fmov.s fr7,@-r15
        fmov.s fr8,@-r15
        fmov.s fr9,@-r15
        fmov.s fr10,@-r15
        fmov.s fr11,@-r15
        sts.l pr,@-r15
        sts pr,r5
        mov #10,r4
        mov.l 1f,r0
        jsr @r0
        nop
        lds.l @r15+,pr
        fmov.s @r15+,fr11
        fmov.s @r15+,fr10
        fmov.s @r15+,fr9
        fmov.s @r15+,fr8
        fmov.s @r15+,fr7
        fmov.s @r15+,fr6
        fmov.s @r15+,fr5
        fmov.s @r15+,fr4
        mov.l @r15+,r7
        mov.l @r15+,r6
        mov.l @r15+,r5
        mov.l @r15+,r4
        mov.l 2f,r0
        jmp @r0
        nop
        .align 2
1:      .long _re4dc_callprof_note
2:      .long ___real_memcmp
        .global ___wrap_re4dc_sincosf
        .type ___wrap_re4dc_sincosf, @function
        .align 2
___wrap_re4dc_sincosf:
        mov.l r4,@-r15
        mov.l r5,@-r15
        mov.l r6,@-r15
        mov.l r7,@-r15
        fmov.s fr4,@-r15
        fmov.s fr5,@-r15
        fmov.s fr6,@-r15
        fmov.s fr7,@-r15
        fmov.s fr8,@-r15
        fmov.s fr9,@-r15
        fmov.s fr10,@-r15
        fmov.s fr11,@-r15
        sts.l pr,@-r15
        sts pr,r5
        mov #11,r4
        mov.l 1f,r0
        jsr @r0
        nop
        lds.l @r15+,pr
        fmov.s @r15+,fr11
        fmov.s @r15+,fr10
        fmov.s @r15+,fr9
        fmov.s @r15+,fr8
        fmov.s @r15+,fr7
        fmov.s @r15+,fr6
        fmov.s @r15+,fr5
        fmov.s @r15+,fr4
        mov.l @r15+,r7
        mov.l @r15+,r6
        mov.l @r15+,r5
        mov.l @r15+,r4
        mov.l 2f,r0
        jmp @r0
        nop
        .align 2
1:      .long _re4dc_callprof_note
2:      .long ___real_re4dc_sincosf
        .global ___wrap_PSMTXRotAxisRad
        .type ___wrap_PSMTXRotAxisRad, @function
        .align 2
___wrap_PSMTXRotAxisRad:
        mov.l r4,@-r15
        mov.l r5,@-r15
        mov.l r6,@-r15
        mov.l r7,@-r15
        fmov.s fr4,@-r15
        fmov.s fr5,@-r15
        fmov.s fr6,@-r15
        fmov.s fr7,@-r15
        fmov.s fr8,@-r15
        fmov.s fr9,@-r15
        fmov.s fr10,@-r15
        fmov.s fr11,@-r15
        sts.l pr,@-r15
        sts pr,r5
        mov #12,r4
        mov.l 1f,r0
        jsr @r0
        nop
        lds.l @r15+,pr
        fmov.s @r15+,fr11
        fmov.s @r15+,fr10
        fmov.s @r15+,fr9
        fmov.s @r15+,fr8
        fmov.s @r15+,fr7
        fmov.s @r15+,fr6
        fmov.s @r15+,fr5
        fmov.s @r15+,fr4
        mov.l @r15+,r7
        mov.l @r15+,r6
        mov.l @r15+,r5
        mov.l @r15+,r4
        mov.l 2f,r0
        jmp @r0
        nop
        .align 2
1:      .long _re4dc_callprof_note
2:      .long ___real_PSMTXRotAxisRad
        .popsection
)ASM");
#if RE4DC_CALLPROF >= 2
// CALLPROF=2 (lane approx): the callers of re4dc_sincosf's callers.
asm(R"ASM(
        .pushsection .text
        .global ___wrap_PSMTXRotRad
        .type ___wrap_PSMTXRotRad, @function
        .align 2
___wrap_PSMTXRotRad:
        mov.l r4,@-r15
        mov.l r5,@-r15
        mov.l r6,@-r15
        mov.l r7,@-r15
        fmov.s fr4,@-r15
        fmov.s fr5,@-r15
        fmov.s fr6,@-r15
        fmov.s fr7,@-r15
        fmov.s fr8,@-r15
        fmov.s fr9,@-r15
        fmov.s fr10,@-r15
        fmov.s fr11,@-r15
        sts.l pr,@-r15
        sts pr,r5
        mov #13,r4
        mov.l 1f,r0
        jsr @r0
        nop
        lds.l @r15+,pr
        fmov.s @r15+,fr11
        fmov.s @r15+,fr10
        fmov.s @r15+,fr9
        fmov.s @r15+,fr8
        fmov.s @r15+,fr7
        fmov.s @r15+,fr6
        fmov.s @r15+,fr5
        fmov.s @r15+,fr4
        mov.l @r15+,r7
        mov.l @r15+,r6
        mov.l @r15+,r5
        mov.l @r15+,r4
        mov.l 2f,r0
        jmp @r0
        nop
        .align 2
1:      .long _re4dc_callprof_note
2:      .long ___real_PSMTXRotRad
        .global ___wrap__Z9RotMatrixPA4_fP3Vec
        .type ___wrap__Z9RotMatrixPA4_fP3Vec, @function
        .align 2
___wrap__Z9RotMatrixPA4_fP3Vec:
        mov.l r4,@-r15
        mov.l r5,@-r15
        mov.l r6,@-r15
        mov.l r7,@-r15
        fmov.s fr4,@-r15
        fmov.s fr5,@-r15
        fmov.s fr6,@-r15
        fmov.s fr7,@-r15
        fmov.s fr8,@-r15
        fmov.s fr9,@-r15
        fmov.s fr10,@-r15
        fmov.s fr11,@-r15
        sts.l pr,@-r15
        sts pr,r5
        mov #14,r4
        mov.l 1f,r0
        jsr @r0
        nop
        lds.l @r15+,pr
        fmov.s @r15+,fr11
        fmov.s @r15+,fr10
        fmov.s @r15+,fr9
        fmov.s @r15+,fr8
        fmov.s @r15+,fr7
        fmov.s @r15+,fr6
        fmov.s @r15+,fr5
        fmov.s @r15+,fr4
        mov.l @r15+,r7
        mov.l @r15+,r6
        mov.l @r15+,r5
        mov.l @r15+,r4
        mov.l 2f,r0
        jmp @r0
        nop
        .align 2
1:      .long _re4dc_callprof_note
2:      .long ___real__Z9RotMatrixPA4_fP3Vec
        .global ___wrap_low_RotMatrix
        .type ___wrap_low_RotMatrix, @function
        .align 2
___wrap_low_RotMatrix:
        mov.l r4,@-r15
        mov.l r5,@-r15
        mov.l r6,@-r15
        mov.l r7,@-r15
        fmov.s fr4,@-r15
        fmov.s fr5,@-r15
        fmov.s fr6,@-r15
        fmov.s fr7,@-r15
        fmov.s fr8,@-r15
        fmov.s fr9,@-r15
        fmov.s fr10,@-r15
        fmov.s fr11,@-r15
        sts.l pr,@-r15
        sts pr,r5
        mov #15,r4
        mov.l 1f,r0
        jsr @r0
        nop
        lds.l @r15+,pr
        fmov.s @r15+,fr11
        fmov.s @r15+,fr10
        fmov.s @r15+,fr9
        fmov.s @r15+,fr8
        fmov.s @r15+,fr7
        fmov.s @r15+,fr6
        fmov.s @r15+,fr5
        fmov.s @r15+,fr4
        mov.l @r15+,r7
        mov.l @r15+,r6
        mov.l @r15+,r5
        mov.l @r15+,r4
        mov.l 2f,r0
        jmp @r0
        nop
        .align 2
1:      .long _re4dc_callprof_note
2:      .long ___real_low_RotMatrix
        .popsection
)ASM");
#endif
#endif
