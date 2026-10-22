# Common CPU_BACKFACE=2 kernel: exact target arithmetic, timing gate open

Base QA22-All20752045. The 32-byte BackfaceSq ABI is unchanged. Mask255 is
world; mask127 is explicit actor strips; mask383 scans actor bit7 EOL streams
inside assembly. No C classification or EOL scanning fallback is used.

The generic state machine and fused pending-vertex continuation preserve the
C strip run/parity rules and exact emitted words. Leading/trailing backs drop;
inner back runs shorter than three remain; new pieces start at even original
triangle parity. Material exclusions and clip decisions remain caller-owned.

## Actual C arithmetic is the contract

The final target CPU1 native_static.o AND native_actor_fast.o lower the C
expression to four rounded subtractions, a rounded second product, FNEG, then
FMAC of the first product plus that negative second product. The original C
reference stays unchanged. Earlier strict non-FMA host-oracle tests establish
only that earlier source interpretation; they do not establish target parity.

A finite witness proves the distinction. A=(0,0),
B=(570.0137939453125,438.41583251953125), C=2B gives strict two-product area
0x00000000 but actual-C FMAC area0xbc480b30, so cull2/even accepts it.
The current assembly uses the target FMUL/FNEG/FMAC order in BOTH paths.
The current FMA-path scalar register move explicitly runs with FPSCR.SZ=0.

build_oracle.py generates a private header from the original backface_emit.hpp
with only the determinant line lowered to std::fma. It pins the source and
transformed header hashes and host library. CPU1 source is read-only. This is
an explicitly target-lowered C template oracle, not an unmodified host-C or
actual target execution claim. The original C run/emit algorithm is retained.

## Object qualification

Latest outputs: /root/probe/backface-sh4zam-kernel-objects-20261022-202252-fmac08.
Actual GCC SH4 objects were compiled once in isolated fmac07 then copied with
identical hashes into fmac08 for expanded host tests. Trace0 SHA256:
b35c978b5d42f366ff2faad3008dc29f4d2d7b370d7c581d25a4c9efeaa78ad2.
Trace1 SHA256:
32ef2271f804cc11e8b36fc563daf41b6b131e0178b385db58501cbc48f44aae.

2,110 bounded cases /4,220 trace-off/on comparisons pass: exhaustive binary
facing patterns through nine triangles for both world/actor masks; random
sizes through256; long all-front/all-back zigzags; the FMAC cancellation
witness; zero/subnormal/near-limit/infinity/NaN; EOL streams300/1024/2048.
The original C array bound limits an individual reference strip to256.

32 FR/SZ/PR/DN entry-mode combinations pass using finite exact coordinates.
All16 opposite-bank/XMTRX sentinels, callee GPR/FPR, PR and original FPSCR
are preserved. The trace callback adversarially clobbers caller-save registers
and XF; emitted-piece replay exactly matches actual PREF bursts. Every SQ
burst is complete before PREF; EOL and parity/front words compare exactly.
Rounding-mode alternatives and actual FPU exception/trap behaviour are not
claimed by the deliberately bounded interpreter.

These are host interpretations of actual SH4 opcodes plus a target-lowered C
oracle. They are not Flycast, pixel, KOS, s30, full release or physical-console
acceptance. Objects04 were accidentally rebuilt over prior outputs; retained
historical receipt and exact impact ledger are in the external kernel lane.

## Performance acceptance remains open

The generic correctness path was too slow. The new all-front continuation
keeps pending B in DR0..6, Axy in alternating FR8/9 versus FR10/11 and Cxy in
FR12/13. Determinant work begins only after SQ stores consume B words. Mixed
runs return to the exact state machine. Trace remains optional.

Independent full-path MODELLED schedules are being recomputed after the FMAC
correction; old strict-kernel timings do not apply. The requested <=4
incremental cycles/triangle is NOT accepted and no FPS/performance improvement
is claimed. Actual pixel/memory gates and independent caller-inclusive timing
remain necessary before the private QA disc is described as qualified.
