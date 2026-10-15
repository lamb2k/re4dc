# Where the CPU goes at the r101 cross, and why (2026-10-15)

## The answer in plain words

The CPU is high because **the code around the vertex maths costs more than the maths**. The vertex kernels are
already near the SH-4's limit (35-38 cycles a vertex, scheduled). But the 30k vertices of a picture are cut into
~616 world meshlets of only **25 corners each** and ~75 character part draws, and every piece pays a large fixed fee.
A world meshlet pays ~3.4k cycles of tests and setup before its first corner. A character part pays ~30k cycles of
bookkeeping, through 4-5 layers (GC game, bridge, owner/transaction, native actor, packet). Each vertex then makes
2-3 trips through memory (decode and transform into a cache, light, copy into the store queue). The frame runs
~1,550 different functions (12M instructions a picture), so the 8 KB instruction cache and 16 KB data cache thrash.
Half the console's cycles are cache waits, and it averages 0.6 instructions a cycle where the SH-4 can issue 2.
Drawing is ~55 ms of the 99 ms picture; a lean SH-4 path would draw the same vertices in ~10 ms. The other
~33 ms is game logic, which runs twice per picture (drawn plus skipped tick). That logic is real simulation (Ganados,
Leon's cloth, effects, collision), not port overhead.

## Sources and labels

- **CONSOLE**: the user's console, bench 76f40d95 (test 12.1 + BENCHMARK, PACE_MODE=fast, cap 6), Part 1 run 2, r101
  cross, room frames 300..1199. One picture = 1 drawn + 1 skipped tick = 99.2 ms: LOGIC 33.1, ACTOR PREP 2.8,
  ACTOR DRAW 28.4, WORLD 19.1, OTHER 15.8. D-stall 30%, I-stall 21%.
- **MODELLED**: hwsim trace of that same disc, scene and window. It has 40 traced ticks, alternating 20 drawn and 20
  skipped (`D:\Flycast-Evidence\re4-dreamcast\hwcal-20261015\hw-cross\proj\rep\functions.tsv`, `nominal.pcs.tsv`).
  Per picture = 2 x the per-tick average.
- **fit**: MODELLED nominal re-priced per function with the current console fit (lane storemiss: +6 cycles per D
  fill, +5 per I fill, 0 per store miss, overlap 0.79). Total 88.5 ms against CONSOLE 99.2.
- **corr**: fit x1.13 for render stages. That is the midpoint of the render residual the storemiss lane left
  unexplained (1.07-1.19). Logic stays x1.0. World check: 16.1 x 1.13 = 18.2 against CONSOLE WORLD 19.1.
- **Unit counts** are MODELLED, from that trace:
  - Loop counts of the kernels (PC exec histograms; the avk loops do 2 vertices an iteration): 15.6k world corners
    transformed, 14.1k character vertices positioned and 8.5k lit through the avk light kernels per picture.
  - Entry counts of the functions per picture (x2 of per tick): MeshDraw::draw 616, box_mask 573, sg_select 367,
    box_class 354, world_out 208, MeshDraw::run 110, pass_positions 149, re4dc_draw_model_part 75,
    re4dc_actor_submit 50, build_lights 51, pwc runs 187, PSMTXConcat 1,367, memcpy 2,668, memset 1,498.
  - World strip vertices are 30.1k, and back faces are 3,391 of 7,339 in-view triangles (lane t2exact, test 13,
    MODELLED).
- **Lean figures are ESTIMATES from code** (instruction counts at the SH-4's dual issue, not measured):
  - KOS `kernel/arch/dreamcast/math/matrix.s` `_mat_transform_sq`: 31 instructions per vertex, one FTRV and one FDIV
    for 1/w, written straight into the store queue. About 16-20 cycles a vertex; ~12-16 with FSRRA in place of FDIV,
    as `shz_invf_fsrra` in `sh4zam/shz_scalar.h` and our own avk kernels do.
  - Lighting: 3 FIPR plus clamp and pack, ~12-15 cycles.
  - Store-queue copy of a 32-byte vertex: ~8 cycles.
  - Frustum test of a box or sphere with FIPR: ~40-60 cycles.
  - Draw state per part: XMTRX load + PVR header + cull, ~1-2k cycles generous.
  - The KOS example `examples/dreamcast/pvr/pvrmark_strips_direct` is the direct-to-store-queue model.
- **Trap found:** the memlay drawn/skip trace (hwmodel-ml-skip) holds a one-off asset conversion. Its frame 1033 takes
  107.8 ms, and actor `Converter::*` shows 3.1 ms per drawn tick there against 0.24 here. Do not price from that
  trace without dropping that frame.

Cycles are at 200 MHz (1 ms = 200k cycles). "Compute" means issue plus dependency plus branch; "stall" means I and D
cache misses plus prefetch waits.

## 1. WORLD path (15.6k corners, 30.1k strip vertices, 616 meshlet visits per picture)

| Stage | Functions | ms/picture fit / corr | Units | Cycles per corner, compute + stall | Lean SH-4 need | Gap (corr) | In plain words |
|---|---|---|---|---|---|---|---|
| W1 walk / cull / LOD | ps2_pass, world_out, MeshDraw::run/draw, box_class, box_mask, sg_select/sg_coef, concat_u, load_screen, ps2_world_direct_begin | 9.15 / **10.34** | 2.8 passes, 208 placement tests, 354 cluster tests, 616 meshlet visits, 110 parts | **133** = 72 + 61 (I 37, D 24); **3.4k per meshlet visit** | about 1k box tests x ~50 + 110 part setups x ~1k: **~0.5 ms** | **~9.8** | Deciding what to draw costs more than drawing it |
| W2 transform | vp::transform_sched (mesh_fastpath_sched.hpp) | 4.06 / **4.59** | 15.6k corners, 73 instructions each | **59** = 47 + 12 (D: colour LUT and cache-entry fills) | `_mat_transform_sq` + LUT colour, ~22: **~1.7 ms** | 2.9 | Turning stored points into screen points |
| W3 strip emit | walk_lean, strips_lean | 2.35 / **2.66** | 30.1k strip vertices | **34** (17.7 per strip vertex) | store-queue copy ~8 per strip vertex: **~1.2 ms** | 1.5 | Copying finished points to the graphics chip |
| W4 clip | Emitter::clip_strip | 0.58 / **0.66** | ~100 clipped strips | 8 | same | ~0 | Cutting triangles at the near plane |
| **World total** | | 16.14 / **18.24** (CONSOLE 19.1) | | **234 (1.17 us)** | **~3.4 ms (~44 cycles)** | **~14.8** | |

Why one corner costs ~1.2-1.6 us when the transform is 0.29 us (the coordinator's question):

- **Transform: 59 of 234 cycles.**
- **Walk / cull / LOD: 133 cycles.** That is ~3.4k cycles per meshlet spread over its 25 corners.
- **Strip copy: 34 cycles.** **Clip: 8 cycles.**
- **Outside the WORLD bucket:** the console's frozen-sweep figure of "1.6 us" (23.0 ms / 14.3k vertices) also carries
  ~4 ms that disappears with the world but is filed elsewhere (sweep WORLD bucket 18.9 of the 23.0 delta). That ~4 ms
  is the PS2 world direct begin, fog, the packet/OT entries and buffer clears.

**Back faces (MODELLED):** 61% of the transformed corners (10.5k a frame) are used only by back-facing triangles.
- **Ideal ceiling:** skipping them would save 0.61 x (W2 4.6) + ~0.46 x (W3 2.7) = **~4 ms corr** (~22% of WORLD).
- **Not reachable:** back and front faces share corners inside every meshlet. The best fixed grouping (G=8 cones)
  reaches 13.5% of corners, ~0.6 ms gross, and its tests cost about as much (t2exact: NOT BUILT). The PVR already culls
  back faces for free on the GPU side.
- **Characters** skin every vertex the same way: closed meshes, about half back-facing, the same sharing, so the same
  verdict.

**Back-face work is a meaningful share of the cost, but culling cannot reach it: fewer vertices or cheaper vertices
can.**

## 2. ACTOR path (14.1k vertices positioned, 8.5k lit, 149 meshlet passes, 75 part draws per picture)

| Stage | Functions | ms/picture fit / corr | Units | Cycles per vertex, compute + stall | Lean SH-4 need | Gap (corr) | In plain words |
|---|---|---|---|---|---|---|---|
| A1 per-part / per-object setup | re4dc_actor_submit, one_chunk, ModelRender, getPartsPtr, Trans, owner_* binds/palettes, actor_transaction_*, role/identity, prepare_model_assets, draw_model_part, model_submit, TextureLeases, sob::take, mv_emit (~200 functions) | 9.89 / **11.18** | 75 part draws (50 native actor submits), 32 ModelRender | **159** = 95 + 64 (I 38, D 26); **~30k per part draw** | ~2k per part: **~0.75 ms** | **~10.4** | Paperwork before each body part is drawn |
| A2 pose / matrices (both ticks) | re4dc_pwc_ftrv_run, re4dc_pmc_run, PSMTXConcat/Inverse/MultVec, coarse_skin_bones, wpal | 5.50 / ~5.8 | 187 skeleton passes, 1,367 concats (~200 cycles each, scalar exact) | (per concat ~200) | FTRV concat ~25 cycles: **~1.5 ms** | ~4.3 (the logic half must stay exact) | Building the bone matrices |
| A4 skin + transform | re4dc_avk_pos_{skin,rigid}_{s16,u16}, sk1 | 4.67 / **5.28** | 14.1k vertices, ~79 instructions each | **75** = 54 (35-38 scheduled + palette switches + call) + 21 | FTRV + FSRRA + outcode + store, ~24: **~1.7 ms** | 3.6 | Bending and placing the skin |
| A5 lighting | re4dc_avk_light_*, build_lights (51 per picture), probe_lights, avk_build_dirs, probe_dirs_all, cLightMgr/LightSetModel | 4.43 / **5.01** | 8.5k lit vertices | **118 per lit vertex** (kernel 33.5-35; the rest is per-part light setup) | 3 FIPR + pack ~15, lights once per actor: **~0.8 ms** | 4.2 | Shading the characters |
| A6 strip emit / clip | Part::whole (91), Part::strips (29), pass_positions wrapper | 2.56 / **2.89** | 14.1k vertices | **41** | store-queue copy, ~10 per vertex: **~0.7 ms** | 2.2 | Copying finished points to the graphics chip |
| A3 conversion | Converter::* | 0.24 / 0.27 | one-off / LOD rebuild | - | offline | 0.3 | Converting a model the first time |
| **Actor total (A1, A3-A6)** | | 21.79 / **24.6** (CONSOLE ACTOR DRAW + PREP 31.2, which also holds part of the packet layer) | | **349 (1.75 us)** all-in; **190** without A1 | **~4 ms (~57)** | **~20** | |

CONSOLE cross-check (frozen sweep): Leon 6.7k vertices = 7.5 ms (224 cycles a vertex all-in); 5 Ganados 9.6k =
11.6 ms (242 cycles).

Rest of the render-side CPU per picture, corr:
- **Packet / UI / OT / GX layer: 6.7.** UI image load/resolve 1.2, model packets 0.7, clearOt/ExecOt 0.8, GX stubs
  ~0.3, diagnostics flags ~0.2.
- **memset/memcpy/memcmp: 4.1**, from 4,166 calls.
- **Effects draw setup: 2.6.** **KOS threads/IRQ: 2.0.** **Audio: 1.6.**

## 3. LOGIC (CONSOLE 33.1 per picture = 16.55 per tick; MODELLED 15.16 per tick, LOGIC-WASTE-CENSUS trace A, same disc)

| Owner | MODELLED ms per tick | Of which | Real simulation or port overhead |
|---|---|---|---|
| Ganados (5.8 updates a tick at cap 6) | 4.88 = **0.84 each** | motion keys 0.15, wall collision 0.13, route/sight lines 0.11, foot IK maths 0.11, skeleton 0.10, AI/state 0.09, IK floor 0.06, body-body 0.05, IRQ 0.03 | real |
| Leon | 3.40 | jacket cloth 1.39, state 0.18, rest pose/collision | real (cloth could run at half rate: approximation, -0.8 per picture) |
| Effects logic | 2.28 | cEsp48 particles 1.04 (273 a tick), CommonMove 0.58, haze 0.30 | real (half rate: approximation, ~-0.9) |
| Props, objects, other creatures, em manager | 2.72 | cEmBox/Door/Rack 0.94, em26/em28 0.86, objMove 0.62 (243 a tick), emMove 0.30 | real |
| Camera, events, sound, rest | 1.88 | camera lines 0.54, SceAtCheck/scheduler 0.45, sound 0.20 | real, sound partly port |
| GC task model on KOS threads, IRQ | 0.52 | OSSignalSemaphore / thd_pass / genwait 0.30, IRQ 0.22 | **port overhead** |

- **Fixed part** (no Leon, no Ganados) is 6.9 ms a tick; Leon 3.4; each Ganado 0.84 (backlog fit 1.15 with the T_SKIP
  share).
- **Top functions, ms per tick (MODELLED):**
  - cEmMgr::move tree 6.99 (inclusive)
  - Motion keys 2.97
  - EspMove 2.18
  - Collision of all kinds 3.16
  - Skeleton 1.69 (exact asm twins)
  - Foot IK 1.22
- **Port overhead in logic:** about **0.7-1.0 ms per tick (5-7%)**: the GC task model 0.52, plus sound and frame-glue
  pieces.
- **No GX state in logic.** GX stubs sit on the render side: 0.27 at the cross, 1.05 at the farm.
- **Repeated work, measured:** each exact memo candidate gave at most 0.2 ms. The memo's compare costs about what it
  saves (getPos, camera lines, wall reuse, pose skip: CLOSED).
- **Stalls:** logic stalls 36% in the fit (console ~45%). Its code is the GC game's own, already compiled for size and
  speed; there is no lean twin to compare against.
- **Conclusion:** logic is high because the game simulates a lot, twice per picture. It is not port waste.

## 4. Why the three biggest gaps cost what they do (code read, t15int 772a238a)

**A1, character part setup (~30k cycles per part draw; gap ~10 ms).**
- Each part walks a chain of separately written layers: `ModelRender` / `Trans` (GC game) ->
  `re4dc_draw_model_part` -> `re4dc_model_submit` -> actor transaction (`identity`, `role_bindings`,
  `owned_source`, `owner_*_bind` / `_palettes`) -> `re4dc_actor_submit`.
- `re4dc_actor_submit` (native_actor_fast.cpp:4631) then re-derives, every frame and for every part:
  - the near and far distances from the projection;
  - the blob lookup and the LOD-pending check;
  - the deferral check;
  - `prepare_frame`;
  - a fog-gate depth: a hand-scheduled loop over the whole skin palette, run per part;
  - light sets (`build_lights`: 51 a picture, per part, not per actor);
  - texture leases and census counters.
- Almost none of these inputs change between frames for a bound actor. The cost is repeated re-discovery plus
  pointer chasing across many small structures.
- That is why A1 shows 24% I-stall: ~200 functions on the per-part path compete for an 8 KB I-cache.
- Earlier narrow trims (g1parts, ACTOR_NO_CLEAR, native part list for world props) each found 0.2-0.8 ms, because the
  cost is spread thin. The structure is the cost, not one function.

**W1, world walk / cull (~3.4k cycles per 25-corner meshlet; gap ~10 ms).**
- `MeshDraw::meshlet` (native_static.cpp ~2160) runs these steps per meshlet:
  1. `box_mask` against the planes (573 a picture, ~330 cycles each);
  2. the strip-group select, `sg_select` (367, ~590 cycles);
  3. for indexed v3 meshlets, a **gather copy** of every corner into a side buffer (`corners()`: an extra pass);
  4. a lazy prime of the cache's constant words;
  5. the transform into the cache;
  6. the strip walk.
- Above the meshlets sit `box_class` per cluster (354), `MeshDraw::run` per part (110, ~1.8k cycles) and the placement
  walk (`ps2_pass` ~59k cycles per pass).
- Every step sits behind several `#if` knob paths and counters. That keeps the hot code large: W1 is 28% I-stall.
- With only 25 corners a meshlet, the fixed fee (~3.4k cycles) is 2.3x the meshlet's own transform (~1.5k).
- The meshlet tests about break even: they reject ~22% of meshlets (616 visits, ~480 transformed). That saves ~3.4k
  corners x ~93 cycles = ~1.6 ms, against ~4 ms of tests. Deleting them is not the fix. **Bigger meshlets with a
  cheaper visit are.**

**A4 + A5 + A6, character vertices (190 cycles each against ~57 lean; gap ~10 ms).**
- The kernels themselves are good (avk_sh4.S: 35-38 cycles per position, 33.5-35 per light, FTRV + FSRRA + FIPR).
  The cost is the data flow around them, in four parts:
  1. **Three passes per meshlet.** The position pass writes 32-byte entries into a 4 KiB vertex cache. The light pass
     re-reads normals and writes the same entries again. The emit pass (`Part::whole` / `strips`) re-reads them and
     copies them by index into the packet or store queue. That makes 3 calls and 3 loop prologues per meshlet, 149
     meshlets a picture, ~94 vertices each.
  2. **Format conversion every frame.** Positions are s16/u16 and n16 normals go through `lds`/`float` (FPUL) per
     component. s8 normals use a 256-entry float table, and that table is a D-cache tenant. The 1,080 n16 normal misses
     a picture have no PREF (t2exact B6).
  3. **Palette switches.** A record whose palette index changes branches out of the loop and reloads XMTRX from the
     skin table, which happens many times per meshlet.
  4. **Light setup per part.** `build_lights` + `probe_lights` + `avk_build_dirs` + `probe_dirs_all` run per part.
     They take about half of A5.
- Write-allocate (MOVCA) and read prefetch are already closed: console Bench A = 0, and B6 is below 0.2 ms. The
  stores are not the cost; the instruction count and the extra passes are.

## 5. Top 3 fixes, ranked by ms and confidence

| # | Lever | Game area | Work it cuts | In plain words | ms per picture | Label / confidence | Exact or approximation |
|---|---|---|---|---|---|---|---|
| 1 | Fewer world vertices in view: a PS2-sourced world LOD / draw distance, converted offline per room | Every outdoor room (r101 cross first) | World corners and strips, and the meshlets and clusters visited (W1-W3 all scale with them) | Draw the far village with simpler or fewer buildings | **-3.9 (18.8 m) to -7.9 (12.5 m)** | **CONSOLE**, frozen cross sweep, drawn tick; high | Approximation (look: still pair; user decides) |
| 2 | Per-actor draw plan: resolve the part list, palettes, textures, light set and fog gate once at bind time (and when the plan changes), then replay it with one native call per actor | All characters (Leon, Ganados, animals, merchant) | A1 per-part bookkeeping (11.2 corr) plus per-part light setup (~2.5 of A5) | Do the paperwork once per character instead of every body part, every frame | **~-5 to -7** (target ~5-8k cycles per part, from ~30k) | ESTIMATE from MODELLED corr; medium-low: spread over ~200 functions; price a hwproject arm before building | Exact (same parts, order and triangles; TA hash identity gate) |
| 3 | One-pass character vertex kernel: position + light + emit for whole meshlets straight to the store queue; s8 normals for every cast model (offline); lights per actor | All characters | A4 + A5 + A6 passes (13.2 corr): the cache round trip, the second normal read, three calls per meshlet | Process each character point once instead of three times | **~-3 to -4** | ESTIMATE; low-medium | Exact if the FP operations stay the kernels' own; the s8 normal conversion is render-only (still pair) |

- **Why fix 3 needs assembly** (optimization rule): the simpler options are measured and closed. MOVCA = 0 on the
  console, prefetch < 0.2, memo levers < 0.2. Data layout (s8 normals, light per actor) goes first. Only the fused
  loop needs the kernel generator (mkavk.py templates), which already exists.
- **Not in the top 3:**
  - **World meshlet driver** (merge meshlets offline to ~100 corners, a cluster-level accept, one tight visit loop):
    ~-2 to -4 ESTIMATE, exact geometry. It is the exact twin of fix 1 and the next candidate.
  - **Logic rate approximations:** cloth -0.8, effects -0.9, far Ganado AI half rate.
  - **I-cache layout** (LINK_ORDER regen): console A/B only.
- **Together**, fixes 1-3 take the drawn tick from ~74 to ~55-62 ms (CONSOLE 74 minus the estimates above; only fix 1 is console-measured). The 20 fps floor (D <= 50)
  also needs the exact world twin and the logic rate levers.
