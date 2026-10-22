Implementation update: the short-strip scan, six-phase rotation, mask selection, lean SQ spans and batch register lease below are now implemented and opcode-tested in the SDK patch. This original design record is retained for comparison. The current task is reducing complete caller cost against OFF; see README.md and evidence/fused09.

# Fused SDK implementation following the API boundary

The first unit only establishes the library boundary and an exact opcode
baseline. It deliberately leaves the old cost visible. Do not integrate this
as a speed improvement or describe vertex reduction as a net render win.

Owned source indices<=64 means triangles<=62. A reusable integer-mask helper
must still handle0/1/2/63/64 triangle masks. No SQ write or PREF may occur before
all/any/depth/limit decides that a world strip can emit. Cull-none, alpha-mask,
no-depth-write and model eligibility remain outside SDK invocation.

Proposed batch assembly register allocation (not implemented): r14 API context,
r8 projected cache, r9 current strip base, r10 strip/end pointer, r11 index mask,
r12 SQ cursor, r13 remaining count, r4 index cursor, r5/r6 reversed-facing mask,
r7 optional outcode base, r2/r3 all/any, r0/r1 address/raw-index scratch. Spill
batch end, original count, next strip and final all/any to fixed stack locals
only at strip boundaries. One prologue owns exact FPSCR and callee/XF preservation
for the complete batch. Large/exceptional streams enter the qualified SDK state
machine without returning through RE4 or using a C facing fallback.

FR8/9,FR10/11,FR12/13 contain three raw XY pairs. Six phases specialize both
ABC rotation and parity, so each next vertex replaces the oldest pair without
four coordinate-copy instructions or a parity branch each triangle. FR0..3 are
four rounded-difference temporaries; FR14 is zero. Preserve the actual target
operation DAG: four FSUB, rounded second-product FMUL, FNEG, FMAC first product
plus negative rounded second. No edge recurrence, two-product subtraction or
FIPR shoelace substitution. Interleave integer index/outcode/address/loop work
with independent arithmetic. Baseball Render.s1041 and1379..1504 supplies
rotation/scheduling guidance; its precision, leading-only policy, memory layout
and opposite-bank use do not satisfy these contracts.

Chronological ROTCL produces reverse mask: original triangle i is bit(t-1-i).
Use a real logical64 shift for every cross-word operation. With valid mask V:

    K = (F | ((F<<1)&(F>>1)) | ((F<<1)&(F>>2))
           | ((F<<2)&(F>>1))) & V
    R = K & ~(K>>1) & V
    E = (K | ((R & oddOriginalMask)<<1)) & V

Compute R before repairing parity. oddOriginalMask is0xaaaaaaaaaaaaaaaa for
odd t, otherwise0x5555555555555555. For a normalized forward bit-i mask,
R=K&~(K<<1), oddMask=0xaaaaaaaaaaaaaaaa, repair shifts right instead. Avoid mixing
those representations. Contiguous original triangle spans[a,b) emit vertices
[a,b+2); all normal front vertex words remain exact, only each span's terminal
flags become EOL. Actor ordinary flags synthesize VERTEX; world ordinary flags
are preserved. Original starts odd are extended one triangle earlier by E.

All-front should jump directly to one peeled lean SQ loop; all-back emits no
vertices. Mixed E spans use that same lean loop, no facing recomputation. Actor
whole streams can exceed255 total indices, end at bit7 and reset parity for
each strip. Prefer fusing marker detection into index loads rather than adding
another C or index-only scan. Keep the whole batch's lease over these strips.

Independent mask proof in review branch63ddf8f33 covered141436 cases, exhaustive
through16bits plus30..34 and60..64 boundaries. Re-run against actual SH4 mask
opcodes, including cross-word carries; mathematical proof does not qualify the
new runtime. Retain the original C oracle and the0xbc480b30 cancellation witness.
Extend current4916 comparisons/64 mode controls with fused all/any/clip/limit,
62-triangle masks, actor marker boundaries and adversarial trace callbacks.

The model's approximate14 dual-issue-cycle/triangle resource floor is before
run selection/emission. Four incremental cycles is not established. Price the
actual entire caller and weighted scene distributions against OFF after each
meaningful structural change. Root still owns real runtime binding, scene/asset
identity, matched pixels, OFF programme identity, KOS/s30 and final packaging.
