# SH4ZAM upstream notes (lane sh4zam-adopt, 2026-10-15)

This file covers SH4ZAM v0.9.0 at pin 0fd3a1e1 (MIT, Falco Girgis and SH4ZAM Contributors). It lists where our
existing code beats a direct SH4ZAM mapping, and the API gaps and pitfalls we hit. It is written for the SH4ZAM
authors and for later lanes.

All numbers are MODELLED: the SH-4 hw model, hw ms per drawn frame, 10 traced frames at the r101 cross (frames
500-799, 6 Ganados + Leon). Each arm is compared with mask 0 at the same _end (one image, run-time mask in a .data
boot word). Instruction counts are per frame. These are not console numbers.

## Where ours beats the direct mapping

| Stage | Ours (function, ms, insn) | SH4ZAM mapping (ms, insn) | Why ours wins |
|---|---|---|---|
| Palette groups (0x1) | coarse_skin_sh4.S groups 0.214, 29.0k | shz_xmtrx_init_zero + shz_xmtrx_blend per weight, read back by columns: 0.388, 72.7k (+ memcpy / al4 copies +0.12) | blend reloads the source matrix through FMAC per weight, then the result must leave XMTRX by store. Ours accumulates the weighted rows in the front bank and stores once. Weights are mostly 1-2 per entry, so the blend's setup dominates. |
| Bones (0x1) | coarse_skin_sh4.S bones 0.116, 10.5k | load_cols_4x4 + transform_vec4 per column: 0.183, 29.7k | Two XMTRX loads per bone (inv, then inv x P) and column round trips through memory. Ours keeps inv x P in registers. |
| Skin table (0x2) | avk_build_all asm 0.139, 29.0k | XMTRX = screen once, transform_vec4 per column, dcache_alloc_line: 0.279 + 0.018, 61.8k | The table is small (~30 entries per actor), so the per-column call shape (load vec, FTRV, store vec) costs more than our scheduled asm, which interleaves the loads and stores. |
| Light directions (0x4) | probe_dirs_all scalar 0.209, 27.3k | XMTRX rows = directions once, one FTRV per palette column: 0.163, 20.1k | **SH4ZAM wins here** (-0.05 function-level; whole frame -0.04, inside noise). This is the one case of "load once, transform many". |
| Skinned vertex pass (0x8) | avk_sh4.S re4dc_avk_pos_skin_u16 2.247, 567k | C on shz_xmtrx_load_4x4 per run + transform_vec4 + shz_inv_sqrtf per vertex: 4.841, 816k | The asm software-pipelines u16 decode, FTRV, FSRRA and the 32-byte store across vertices, and reloads XMTRX only at palette-run changes (~770 per frame). The C composition serialises each FTRV result (about 4 cycles of latency) into the next call and cannot overlap the decode. 0x18 (run matrix built in XMTRX, never stored) is +3.22 for the frame. |
| Cache lines (0x40) | none (write-allocate fill) | shz_dcache_alloc_line per 32-byte vertex line: +0.187 in its own loop, pass_positions +0.15; the vertex pass gains only -0.13 | A separate pass over the lines costs more than the fills it saves, because the lines are hot in the store queue path anyway. It would need to sit inside the asm loop to pay. |
| memset (GAME_SHZ_MEMSET) | newlib L_store_long_loop 0.863 + memset 0.103 | shz_memset8 0.801 + our wrapper 0.402 (head and tail byte loops, volatile) + residual newlib 0.046 | FMOV.D halves the store count, but the clears are write-miss bound: shz_memset8 itself is only -0.06 against newlib's loop. Our alignment wrapper ate the rest. A MOVCA.L-based clear for 32-byte-aligned bodies would avoid the read-for-ownership; shz_memset8 does not use it. |

Phase 1 (render-only direct mapping: MTXConcat, Inverse, MultVec, RotRad, sincos) was a wash at matched layout (-0.35,
inside the +-0.4 layout noise; docs/lanes/sh4zam-direct.md). In the global rebinding, the SH4ZAM compositions of
PSMTXInverse (cofactor crosses + FIPR + FSRRA) and PSMTXMultVec (three shz_dot8f) took more cycles per call than
mtx_sh4.S, so they stay on mtx_sh4.S (game30.mk).

## Candidate upstream gain: the skinned vertex loop (coordinator decision 10-15: our asm stays, boot mask 0)

Both sides use the same strategy: XMTRX is loaded once per palette run, then there is one FTRV per vertex. The
difference is in how each vertex is scheduled.

| | avk_sh4.S re4dc_avk_pos_skin_u16 (ours) | sh4zam_skin.c re4dc_shz_pos_skin_u16 (shz_xmtrx_load_4x4 / apply_3x4 + shz_xmtrx_transform_vec4 + shz_inv_sqrtf) |
|---|---|---|
| hw ms per frame (r101 cross) | 2.247 | 4.841 |
| cycles per frame (200 MHz) | ~449k | ~968k (2.15x) |
| instructions per frame | 567k | 816k (1.44x) |
| cycles per instruction | 0.79 | 1.19 |
| XMTRX reloads per frame | ~770 (palette-run changes) | the same ~770 (each also builds screen x entry x q in XMTRX) |

Why ours is faster:
- **One pass does everything.** The u16 position and uv decode (FLOAT from int16), the FTRV, the FSRRA of w*w, the
  perspective multiply, the six outcode compares and the uv scale/bias are interleaved in one loop. The C version does
  the same work, but GCC can't overlap the FTRV result latency (~4 cycles) or the FSRRA latency with the next vertex's
  loads: transform_vec4 is an asm statement that returns its result in registers, so the compiler treats it as a
  serial point. That is the CPI gap (0.79 vs 1.19).
- **Fused FSRRA.** Ours issues FSRRA on w*w while the x/y FMULs of the previous vertex retire. The C version waits on
  the inv result before x and y.
- **Outcodes are not the difference.** GCC also compiles the six outcode compares without per-plane branches (6
  branches in the whole C function against 14 in ours, which is unrolled). The gap is the serialised FTRV and FSRRA
  latency and the extra decode and store instructions (1.44x the count).
- **No per-run copy.** The C run setup scales the palette entry into a stack pq[12], then shz_xmtrx_apply_3x4 reads it
  back. Ours folds q into the entry once when the skin table is built (the 0x2 stage).
- **Call overhead is not the cause.** The SH4ZAM calls inline, so there is no call/return per vertex. The cost is
  in scheduling and in the extra instructions.

What upstream could add to close it: a batch `shz_xmtrx_transform_vec4_n` / `transform_point3_n` with a two-vertex
software pipeline, plus a variant that also returns 1/w (FSRRA) and the outcode mask. Our avk_sh4.S loop is the
reference implementation. We can share it under SH4ZAM's MIT terms if the author wants it.

## API gaps and pitfalls (for upstream)

1. **shz_matrix.h is not self-contained for vendoring.** With only the xmtrx / vector / scalar / mem headers, shz_mat4x4_t /
   shz_mat3x4_t are forward-declared. GCC then cannot see which bytes an asm "m" operand touches, and we had to add
   compiler barriers around every local matrix passed to load/store calls. Suggestion: give the asm operands a sized
   array type, e.g. `"m"(*(const float(*)[16])p)`.
2. **No blend-accumulate that leaves the result in XMTRX for a following FTRV batch with one store.** The palette group
   case wants: XMTRX = sum of w_i x M_i, then transform N vectors. The blend API works, but each call is a full
   matrix pass. A `shz_xmtrx_blend_n(const shz_mat4x4_t* const* m, const float* w, int n)` with the loads
   interleaved would close most of the 0x1 gap.
3. **No pipelined batch transform.** `shz_xmtrx_transform_vec4` per element cannot overlap FTRV latency with the next load
   and store. A batch entry point (`shz_xmtrx_transform_vec4_n(src, dst, n, stride)`) or a documented
   two-element unrolled pattern would let C callers approach hand asm. Our u16-decoded vertex pass shows the gap is
   about 2x.
4. **memset8 uses FMOV.D stores but no MOVCA.L.** For large aligned clears, MOVCA.L for the first store in each 32-byte line
   avoids the line fill. Store count is not the limit on SH-4 here; write misses are.
5. **FSCA precision** (inherited from phase 1): shz_sincosf's 1/65536-turn step gives about 1e-4 relative error near 0.
   That is fine for render. The gameplay arm keeps the exact path beyond about 201 rad, and for inf and NaN.
6. **No bugs found** in the vendored code at the pin. Every routine kept PR=0 SZ=0 on exit, and frchg / fschg are
   paired inside single asm statements.

## What we keep from SH4ZAM

- The light-direction stage (0x4) as an option. It is exact enough for render, the cost is a wash, and the code is
  simpler than our scalar loop.
- The logic-site load-once pattern (include/re4dc_xm.h, GAME_SH4ZAM_LOGIC). Whether it pays is measured in the
  lane doc.
