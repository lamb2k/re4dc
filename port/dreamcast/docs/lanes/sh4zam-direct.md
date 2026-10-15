# Lane sh4zam-direct (2026-10-15): SH4ZAM direct mapping, phase 1

Status: **render-only arm adopted by the user for test 14** (10-15: "let's adopt the render only version for now"; the
r101 still sheet was "diff accepted"). The global arm is in the code behind the knob but is phase 2 and unmeasured.
Branch lane/sh4zam-direct (on test 13, dreamcast-port 1c79d543), worktree /root/probe/lanes-20261015/sh4zam/tree, local
commits only. Bench twin: lane/sh4zam-bench 472c4496 (bench/definitive 702d82ef + these commits).

Why: an SH4ZAM author reviewed platform/mtx_sh4.S. It hand-schedules the SDK's scalar FPU dataflow and never uses
XMTRX / FTRV / FIPR, because we required bit-identical results. His advice: "Make a branch. Tell it to directly map to
sh4zam calls as phase 1. Not fully optimal but will gain." The approximation rule (user 10-15) allows the change:
render-only results are judged on the look.

## Knobs (game30.mk; all default 0)
- `GAME_SH4ZAM=1 GAME_SH4ZAM_RENDER_ONLY=1` (the test 14 candidate). Only the render call sites take the SH4ZAM bodies.
  Logic is untouched.
- `GAME_SH4ZAM=1` alone (global, phase 2, UNMEASURED). Every PS* caller is rebound by a sed of ps_alias_sh4.ld
  (12 bindings), and re4dc_sincosf takes the FSCA path (lane approx's game30_trig.c code). It needs GAME_SH4_MATH=1,
  GAME_TRIG_LEAN=1 and GAME_SINCOS=1. It builds clean (szgrP, missing 0, PS* resolve to re4dc_zam_*). It changes
  gameplay, so its gate is decisions, never STRICT.
- `SH4ZAM_SELFTEST=1` (test builds only): "ZAMTEST" ulp lines at OSInit.
  - Caution: it moves boot timing, so do not take stills from a selftest build.
- It refuses to combine with SH4_APPROX_RENDER / SH4_APPROX_LOGIC (lane approx). Those knobs share the call-site macros.

## What is mapped (platform/sh4zam_direct.c, SH4ZAM v0.9.0, pin 0fd3a1e1, vendored headers from lane approx)
| entry point | SH4ZAM body | XMTRX |
|---|---|---|
| MTXConcat | `shz_xmtrx_load_cols_4x3(b rows)` + one `shz_xmtrx_transform_vec4` (FTRV) per row of a | **clobbered** |
| MTXMultVec / MultVecSR | `shz_dot8f` / `shz_dot6f` (FIPR) per row | untouched |
| MTXInverse | cofactors = `shz_vec3_cross` of rows, det by FIPR, 1/det by `shz_invf` (FSRRA) inside 2^+-60, translation by FIPR; det 0 returns 0 and leaves inv alone | untouched |
| MTXRotRad / RotAxisRad | `shz_sincosf` (FSCA); RotAxisRad normalises the axis with FSRRA | untouched |
| VECDotProduct / SquareMag | FIPR | untouched |
| VECMag / Normalize / Distance / SquareDistance | FIPR + FSRRA | untouched |
| VECCrossProduct | `shz_vec3_cross` (plain C, the same operation order: exact) | untouched |
| re4dc_sincosf | FSCA; \|x\| > ~201 rad, inf and NaN keep the exact path | untouched |
| Identity, Copy, Transpose, Scale, Trans, Reorder, VECAdd / Subtract / Scale | **not mapped**: pure data movement, no arithmetic for SH4ZAM to shorten; they keep the exact mtx_sh4.S bodies | - |

Layout: a GameCube Mtx (float[3][4], row-major, translation in column 3) is, word for word, an SH4ZAM `shz_mat4x3_t`
holding its transpose. Its rows are contiguous `shz_vec4_t`, so the concat loads b's rows as XMTRX columns, and FTRV of
a's row i gives row i of a x b. The 4th lane carries a_i3, the translation term. The concat is aliasing-safe (ab == a or
ab == b).

ABI: -m4-single -ml. FPSCR is PR=0 SZ=0 on entry and exit, and SH4ZAM's frchg / fschg are paired inside single asm
statements. SH-GCC 15.2 compiles the headers unchanged (-std=gnu11).

Render-only call sites (include/dolphin/mtx.h and vec.h macros):
- `RE4DC_RENDER_MTXConcat` / `RotRad`: lane approx's list.
  - trans.cpp: calcWeightMat skin palette, commonModelTrans / frontNativeModelTrans / invisInfoModelview / sceneryGate
    modelviews.
  - esp_sub.cpp: EspCommonTrans sprite matrices.
  - Native actor transaction / Leon pipe / invis owner / crowd gate / coarse modelviews.
  - The ID quad.
- New in this lane: `RE4DC_RENDER_MTXInverse`, used by the calcWeightMat palette inverse, the commonModelTrans (both
  branches) and frontNativeModelTrans normal matrices, and EspCommonTrans's normal matrix.
- New in this lane: `RE4DC_RENDER_MTXMultVec`, used by EspCommonTrans's sprite position.

## XMTRX ownership rules
Audit 10-15 (read-only, every XMTRX loader in the game link):
- Only `re4dc_zam_MTXConcat` writes XMTRX. Every other mapped routine uses FIPR / FSRRA / FSCA.
- **Render-only arm: safe.** No path loads XMTRX, then runs a render concat (directly or in a callee), then uses XMTRX
  without reloading:
  - native_actor_fast (load_xmtrx, avk kernels), native_model, native_static (load_screen), mesh_fastpath, pwc_sh4,
    coarse_skin_sh4 and model.cpp skelRows each load XMTRX for themselves and call no PSMTX / VEC function inside their
    window.
  - The lazy palette (calcWeightMat via re4dc_skin_palette_resolve) runs before its consumer loads.
- **Global arm (phase 2):** coarse.cpp keeps `load_rows(g_S)` live across draw_actors / draw_effects.
  - coarse.cpp:787 `PSMTXMultVec` inside that window would be a hazard only if MultVec clobbered XMTRX. It does not (FIPR).
  - That loop is also off in the recipe (COARSE_FX_SPRITES=2).
  - A later phase that moves MultVec to FTRV must add `load_rows(g_S)` after it.
- Latent, older than this lane and off in the recipe: ACTOR_EARLY_COARSE=1 skips a `load_rows` reload (coarse.cpp ~698).
- **Rule for new code:** treat every PSMTXConcat / RE4DC_RENDER_MTXConcat call as clobbering XMTRX (xf0-xf15). Reload
  XMTRX after any call into game code before the next FTRV. Nothing may assume XMTRX survives a call.
  - KOS saves the back bank on IRQ and thread switch, so only same-thread calls matter.

## Results (test 13 data, cap 6)
Labels: FLYCAST = emulator measurement; MODELLED = SH-4 hw model (PACE_MODE=off cost builds, hw ms per drawn frame).
There are no CONSOLE numbers yet. The ZAMR2 bench disc is for that.

### Correctness
- Knob-off: szkrP image **c1ae83dd** = test 13 (t13mrP), and the 6 overlays are identical. **PASS**
- Build: missing.txt empty on every arm (rP, mW, rT, cost rW; global szgrP).
- Image size: _end +736 B (play, 8c41c53c -> 8c41c81c).
  - Bench: KOS minimum -768 B at 48 KiB squeeze (73,376 vs 74,144).
- Unit test (SH4ZAM_SELFTEST, FLYCAST: Flycast's FTRV / FIPR / FSRRA / FSCA emulation, not the console)
  - Method: 2000 random game-like affine matrices and vectors per routine against the exact C bodies.
  - maxulp counts outputs at least 1/1024 of the call's largest output. maxrel = max |error| / largest |output|.

  | routine | maxulp | max abs | max rel |
  |---|---|---|---|
  | MTXConcat (affine, translation up to 2000) | 106 | 9.8e-4 | 5.5e-7 |
  | MTXConcat (general entries) | 333 | 1e-6 | 1.6e-7 |
  | MTXMultVec / MultVecSR | 112 / 315 | 2.4e-4 | 3.6e-7 / 3.9e-7 |
  | MTXInverse | 303 | 5.9e-3 | 2.8e-7 |
  | MTXRotRad / RotAxisRad, sincosf (FSCA) | large near 0 | 9.6e-5 | 9.6e-5 / 1.2e-4 (FSCA's 1/65536-turn step) |
  | VECDot / SquareMag / Mag / Normalize / Distance | 74 / 2 / 2 / 3 / 2 | - | <= 5.9e-6 (dot: cancellation) |
  | VECCrossProduct | 0 | 0 | 0 |

  - bad = 0 everywhere: no NaN/inf mismatch and no singular-return mismatch.
  - The aliasing check (ab == a) gave identical results.
- STRICT (logic untouched; FLYCAST traces, frame alignment, stop tick 2000):
  - Window A (H2, r100): **MUST-IDENTICAL**, 2002 records.
  - Window B (r101 bell fight): **MUST-IDENTICAL**, 2002 records.
- TEX_CHECK=2 + LEON-GC on the r101 cross: TEXCHK PASS, LEON-GC PASS, pair missing / open failed / upload FAILED 0,
  wrap=0, alive 6.
- Look: still sheet `C:\Game Dev\Emulators\SH4ZAM-RENDER-ONLY-STILL-SHEET-r101cross.png`.
  - Setup: r101 cross, logic frozen at global tick 700, PACE_MODE=off cost builds.
  - Result: **99 px differ, max 9 levels**, embers / fire sprites only. User: "diff accepted".
  - Trap: paced (PACE_MODE=fast) stills are not comparable across arms. The frozen frame keeps the sub-tick render
    state of the last skip pattern, so any cost change moves the camera / poses by a pixel or two. On the paced mW arms,
    control vs ZAM differed 58%, and so did control paced vs control unpaced.
- KOS squeeze 48 KiB (KOS_WATCH twin fpszW, base kostwin from the test 13 release tree): **PASS 10/10**, 0 OOM lines.
  - Minimum headroom: fight 6,160 / 6,120 B (test 13: 6,576); call 39,536; door103 19,896; leave100 / leave103 6,360.
  - Host problems, not failures:
    - The first pass lost 6 runs to fp_run's C: 15 GiB disk floor. I freed my own bench twin discs and reran.
    - The door scene missed its r103 marker in 60 s of wall time on a loaded host (vbl 3255 at 54.7 s; test 13 entered
      r103 at vbl 3377, 56.7 s). It passed at 120 s: r103 entered at vbl 3390 / 56.9 s game wall time.
  - Evidence: C:\Flycast-Evidence\re4-dreamcast\sh4zam-20261015\kos-sz (fight, call), kos-sz2 (leave100, leave103),
    kos-sz3 (door).

### Cost (MODELLED, hw ms per drawn frame, 10 traced frames)
r101 cross, global frames 500-799. Arms:
- control szhkrW
- ZAM szhrrW
- layout control szhprW: knob-off + IMAGE_PAD_BYTES=704, the same _end as the ZAM arm

| part | control | layout ctl | ZAM | ZAM - layout ctl |
|---|---|---|---|---|
| world submit | 17.27 | 18.69 | 18.68 | -0.01 |
| actor submit (ACTOR DRAW) | 9.99 | 10.49 | 10.47 | -0.02 |
| skinning | 3.81 | 3.90 | 3.90 | +0.01 |
| motion/animation | 4.25 | 4.56 | 4.20 | -0.36 |
| effects update + setup | 5.26 | 5.10 | 5.03 | -0.07 |
| shared math/copies | 4.97 | 5.06 | 4.90 | -0.16 |
| logic (enemy + player + collision) | 4.04 | 4.07 | 4.05 | -0.02 |
| **total** | **57.29** | **59.50** | **59.15** | **-0.35** |

- **The mapped routines themselves** (function rows, layout control -> ZAM; MODELLED):
  - concat 0.448 -> 0.412 (-0.036; 36.4k instructions moved to a body with half the count)
  - inverse +0.014; MultVec +0.018 (~20 calls)
  - RotRad + sincosf -0.010
  - Net about -0.03 ms, with 24.7k fewer instructions per frame (-0.3%).
- **Layout dominates.** Moving _end by 704-768 B costs +2.2 ms MODELLED by itself: D-misses in walk_lean /
  transform_sched with the same instruction counts.
  - The naive ZAM-vs-control delta (+1.85 ms) is that layout effect, not the mapping.
  - The -0.35 at matched layout is inside the hw model's code-layout noise (+-0.4).
  - On the console, any test 14 merge moves _end anyway.
- r101 house (s21 siege), global frames 1700-1999:
  - Control 56.23, layout control 57.29 (+1.07 from the _end shift alone), ZAM 56.98.
  - **ZAM vs layout control: -0.31** (shared math -0.26, ACTOR DRAW -0.06, skinning -0.02, world +0.14,
    motion -0.35 noise, unclassified +0.34 noise).
- Verdict, MODELLED: phase 1 is a wash, as the lane approx review expected for per-call one-offs. The gain the review
  promises needs phase 2 (below). The ZAMR2 console A/B against Part 1 is the only real-time judge.

### Bench disc (console A/B)
`C:\Game Dev\Emulators\RE4DC-Bench-ZAMR2-472c4496`
- gdemu/ plus RE4DC-Benchmark-NOT-THE-GAME-472c4496-ZAMR2-GDEMU.zip (zip 1337a653) and SHA256SUMS.
- track03 0604ec5ad9009b3accbd8714e6b268c5d032c91e15f9115fb2f6231213a56e7a.
- Program: bench/definitive 702d82ef + GAME_SH4ZAM=1 GAME_SH4ZAM_RENDER_ONLY=1. Data and fixtures: Part 1, FIXSET 1 2 6.

Gates (FLYCAST):
- Knob-off bench build = Part 1 p4B image 269fc2f2.
- r1 and r2 state hashes match each other and Part 1 control 76f40d95: scene 1 0c1ce839, scene 2 38d93274, sweep
  b4882f3e. The sweep-end tick differs by 1 (render-time count).
- Whole bench under the align logger (interpreter, 745 s): 0 MISALIGN, results pages reached, hashes = the control's
  align run.
- KOS squeeze 48 KiB, one block and 4 KiB pieces: 0 OOM; minimum 73,376 / 73,368 B.
- FLYCAST scene 1: fps 18.5, cpu 33.8 ms (control 18.6 / 33.6).

## Phase 2 (not built)
1. **Keep XMTRX resident across batches.** calcWeightMat does inv x part x bind for ~30 parts per actor. Load inv once
   and FTRV each part's rows, instead of two load + 3-FTRV concats per part. The same for the modelview chains
   (`Cam.v_mat x (part x x5C)` in commonModelTrans / native transaction / Leon pipe): load v_mat once per actor and
   transform each part's rows.
   - Ownership: a resident-XMTRX batch must own XMTRX from its load to its last FTRV and call nothing in between.
2. **FIPR for dot products in logic** (VECDotProduct, MultVecSR) is already mapped in the global arm. It needs the
   decisions gate (gameplay changes).
3. **Batch transforms.** The effect sprites (EspCommonTrans) do four concats + RotRad + MultVec per sprite: build one
   resident view x parent matrix per parent and transform the sprites in a run.
4. Fix the layout before measuring: measure phase 2 against an IMAGE_PAD_BYTES-matched control, as here.
   _end shifts are worth +-2 ms MODELLED.
5. Global arm: the decisions run (r101 bell, H2 / r100, fight) and the gameplay-equivalence summary. Not done
   (out of scope after the user's 10-15 choice).

## Evidence
- D:\Flycast-Evidence\re4-dreamcast\sh4zam-20261015:
  - sr1 / sr2 (ZAM stills + TEXCHK, selftest in sr1), sk1 (control), sk3 / sr3 (unpaced still pair)
  - stA-* / stB-* (STRICT), strict/
  - hwmodel-hck2 / hcr2 / hcp2 / hhk2 / hhr2 / hhp2
  - _tools (zrun.sh, stilldiff.py, brun.sh)
- C:\Flycast-Evidence\re4-dreamcast\sh4zam-20261015: KOS squeeze runs and the kostwin base.
- C:\Flycast-Evidence\re4-dreamcast\zamr2-s126-{r1,r2,align,kos49152-0,kos49152-1}-472c4496: bench gates.
- Scripts: /root/probe/lanes-20261015/sh4zam (zhw.sh, warps, logs-build.txt).
