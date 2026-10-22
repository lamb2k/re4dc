# Common backface kernel: correctness baseline, optimization open

Base QA22-All: `20752045a856121ef97cef92662e31bd661b4988`.
The common assembly consumes the main-owned 32-byte BackfaceSq context.
World mask255 preserves nonterminal cache command words. Actor mask127
synthesizes VERTEX/EOL. Actor mask383 additionally scans EOL-bit7 boundaries
inside assembly, including streams with more than255 total indices.

The kernel uses the original C determinant's four subtractions, two products,
subtraction and ordered comparison. No reassociated edges, fipr/FMA, C facing
fallback, whole-strip keep array or C EOL scan. It streams with a delayed final
front vertex; trailing/leading back runs drop, inner runs below three stay,
and restarts begin at even original parity. Material exclusions and clipping
remain caller-owned.

## Object qualification

`oracle.cpp` includes the actual `room/backface_emit.hpp`; the only stand-in is
the public 32-byte PVR vertex structure in include/dc/pvr.h. Compile the oracle
with `-fno-fast-math -ffp-contract=off`. `object_test.py` loads actual ELF32 SH4
machinecode (and actual trace-hook relocations), rejects unknown opcodes and
interprets it with memory guards and a two-slot SQ model. PREF records a full
32-byte burst immediately, so late EOL repair and incomplete writes fail.

Initial actual objects: trace0 SHA256
`b1dff8a1518d5e4979bb02fb04a374d1e1d151d17b79a42a87204359e402c3b5`,
trace1 SHA256
`b5d421810509a99ee3dbfc5f77fa95ba3a65dad21856249403d55433577f9486`.

1,067 bounded cases / 2,134 trace-off/on comparisons passed, including all
binary facing-run patterns up to nine triangles, random masks/culls and sizes
through256, zero/subnormal/near-limit/infinity/NaN inputs, and EOL streams of
300/1024/2048 indices. Actual emitted words and piece counts match the actual
C template. The explicit C reference is array-safe only through256; its
documented production strip limit is255. No C-oracle claim for a longer
individual strip.

Sixteen entry FR/SZ/PR combinations passed emitted-word, all16 opposite-bank
sentinel, callee-save GPR/FPR, PR and exact FPSCR restoration checks. Production
copy bursts use current-bank DR0..6, preserving XMTRX. Trace-only code saves
both live active registers and the complete opposite bank, normalizes FR0 for
ordinary C, then restores them. The adversarial simulated hook clobbers
caller-save GPR/FPR and XF words; its replay of each actual emitted piece
matches the PREF output without any facing recomputation.

This is **host interpretation of actual SH4 object opcodes**, not SH4 hardware,
Flycast, pixels, KOS, s30, a whole programme or physical-console acceptance.
The host interpreter is deliberately limited to emitted opcodes; it is not a
timing model and does not establish SH4 cache, FPU-exception or TA behaviour.

## Performance is not accepted

The first generic path is a correctness baseline. An independent source issue
model found roughly67 world /75 actor cycles on a steady all-front path before
several omitted costs, far above the requested <=4 incremental cycles over
the existing lean copies. These initial numbers do not apply to any later
optimized source. No performance/FPS gain is claimed and this baseline must
not be presented as an accepted optimization.

Next: a scheduled all-front path with pending full B vertex in DR0..6, Axy
in alternating FR8/9 versus FR10/11, Cxy in FR12/13, and exact determinant
operations after the corresponding SQ stores consume B's x/y words. Only
two Cxy loads plus two retained Bxy moves add LS work in that proposed path;
the theoretical four-extra-LS floor is not a cycle result. Mixed runs retain
the exact assembly state machine. Actual object oracle and independent
full-path scheduling gates remain mandatory after changes.
