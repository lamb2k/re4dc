# Lane t2exact: tranche 2 exact levers (2026-10-15)

Branch lane/t2exact from dreamcast-port 1c79d543 (test 13), worktree /root/probe/lanes-20261015/t2exact/tree, work
files in /root/probe/lanes-20261015/t2exact (build/run scripts, warp files, price.py / lineprof.py / pcprof.py /
callers.py). Local commits only; the coordinator lands. Every knob is default 0 (t2exact.mk): the knob-off image is
test 13's (objcopy -R .stack c1ae83dd, 6 overlays identical).

Levers (PERF-BACKLOG-CH1-2-20261015.md section 4): A2b GC render census removals, B4 world walk lean, B6 read-side
prefetch; B5 (I-cache code size) added by the coordinator.

Labels: MODELLED = the SH-4 hw model (hwproject, nominal penalties). MODELLED-corrected = MODELLED x the
HWMODEL-CALIBRATION-20261015 part factors (WORLD x1.23, ACTOR DRAW x1.25, OTHER x1.15, LOGIC x1.06), for exact work
removal only. CONSOLE = the user's console. Cache / layout / prefetch levers (B5, B6) are not priced by the model (it
charges a D miss ~10 cycles, the console ~24.5): they go to a console A/B.

## Scenes and windows

- r101 cross: benchpub scene 1 without its bench line (cross-warp.txt): Leon by the cross, crowd alerted at room
  frame 30, god, no input, cap 6. Global frames 500..799, 10 traced (stride 30).
- r103 farm: benchpub scene 4 without its bench line (farm-warp.txt): wide view over the farm, 5 Ganados not alerted.
  Global frames 500..799, 10 traced.
- Data set T13_DATA (t11-fix.py), build = test 13 recipe (test13/t13-build.sh rW + PACE_MODE=off PC_SAMPLER_BYTES=8192).
- Evidence: D:\Flycast-Evidence\re4-dreamcast\t2exact-20261015\hwmodel-* (hw model), C:\Flycast-Evidence\re4-dreamcast\
  t2exact-20261015\<run> (Flycast trace / gate runs).

## Control (knob-off cost arm t2crW, 7075c866)

| scene | MODELLED ms/frame | game-render | scenery | actors | logic |
|---|---|---|---|---|---|
| r101 cross | 57.3 [48.9..69.5] | 18.6 | 16.6 | 7.6 | 7.0 |
| r103 farm | 88.0 [75.8..105.3] | 32.3 | 15.8 | 17.7 | 9.3 |

Function groups each lever targets (price.py, MODELLED hw ms per frame, cross / farm):

| group | cross | farm |
|---|---|---|
| A2b #3 GX state (15-18 GX stubs) | 0.27 | 1.05 |
| A2b #11 coarse hooks (sourceActorIdentity, coarse source lookups, room4 state) | 0.28 | 0.55 |
| A2b #12 re4dc_model_diagnostic_enabled (lane g1parts G1_DIAG_INLINE, not repeated here) | 0.05 | 0.12 |
| B4 placement walk (ps2_pass self, world_out, dyn) | 1.65 | 1.63 |
| B4 cluster / meshlet tests (MeshDraw draw/run, box tests, sg_select) | 6.01 | 3.74 |
| B4 strip walk (walk_lean, clip; per strip, not walk overhead) | 3.10 | 3.47 |
| B6 world transform (transform_sched) | 4.44 (dmiss 0.36) | 5.35 (dmiss 0.44) |
| B6 skin / light kernels (avk_*) | 3.71 (dmiss 0.55) | 4.25 (dmiss 0.55) |

## A2b: GC_CENSUS_TRIM

Knob GC_CENSUS_TRIM=1 (t2exact.mk; exact, render only). What it does: the per-call leftovers of the GameCube render census.
- #3 GX state: gx_fast.h inlines the hot GXGetProjectionv / GXGetViewportv / GXSetProjection callers (re4dc_draw_model_part,
  EspCommonTrans, the UI ID quad, CameraSetProjection): they copy / store gx_stub.cpp's state words in place of the call
  (the viewport copy adds the RES_ALTERNATE line jitter exactly as GXGetViewportv does; gx_stub.cpp has an #error if the
  two settings disagree). include/gx.h includes gx_fast.h at its end (adding an #include to esp_sub.cpp shifted __LINE__
  and changed EspCommonTrans's code with the knob off).
- #11 coarse hooks: trans.cpp sourceActorIdentity reads room heap 4's live flag and generation through two exported
  pointers instead of calling re4dc_room4_state(); re4dc_coarse_actor_source / re4dc_coarse_ganado_source find a static
  chunk element from the table's address range (chunk_find.h) instead of comparing every element.
- #12 is lane g1parts' G1_DIAG_INLINE (test 14), not repeated.

Knob-off identity: PASS (x3krP: image c1ae83dd + 6 overlays identical to test 13's t2krP, with the A2b and B4 code in the tree).

| scene (frames 500..799, 10 traced) | control t2crW | a2rW (95b1c618) | delta MODELLED | target groups (price.py) | MODELLED-corrected (OTHER x1.15) |
|---|---|---|---|---|---|
| r101 cross | 57.3 | 57.0 | -0.3 | 0.55 -> 0.39 (-0.16; GX -0.11, hooks -0.05) | -0.35 |
| r103 farm | 88.0 | 87.6 | -0.4 | 1.60 -> 1.12 (-0.48; GX -0.40, hooks -0.08) | -0.46 |

The saving is in game-render-side (effects' EspCommonTrans and the actor part setup), so the OTHER factor applies. The
farm pays more because its GX getters run ~350 times a frame (effects + actor parts); the coarse hooks mostly did not
move: sourceActorIdentity's own body is the cost, not re4dc_room4_state. I-cache fills a frame: 108,990 -> 107,956
(cross), 154,741 -> 154,068 (farm).

Gates (all on the committed tree 4633156c, knob on):
- STRICT + decisions vs the knob-off control, same fixtures: r101 cross fight (stop 800) STRICT, MUST-IDENTICAL, 802
  ticks; door103 (stop 1400) STRICT, MUST-IDENTICAL, 1402 ticks, DOORDEMO END reached; 0 overruns (a2-fight / a2-door vs
  c0-fight / c0-door).
- Align logger (interpreter, 60 s each): r101 fight 0 MISALIGN, halt / missing 0 (reached the fight, PS2 world and
  actors drawn); the door103 run reached r101 only in 60 s (the door is covered by STRICT and the KOS door runs).
- KOS squeeze 48 KiB (twin fpa2sqW, mastered on the test 13 release tree): GATE PASS, 10 runs: fight min 6,488 B, call
  39,944 B, door 20,528 B, leave100 / leave103 6,688 B; 0 out-of-memory / MISSING / HALT.
- Ready for test 15: yes (exact, render only; small: -0.3 / -0.4 ms MODELLED, -0.35 / -0.46 corrected).

## B4: PS2_WALK_CELLS (DROPPED)

Built and measured, not committed (patch kept at /root/probe/lanes-20261015/t2exact/b4-ps2-walk-cells.patch, on
native_static.cpp of 1c79d543). Design: at package open, bin the fixed placements (no dynamic id slot, not the sky row,
not wider than a cell) on a 5 x 6 X/Z grid, the cell id in bits 3..7 of the pass-mask byte, each cell's box the union
of its placements' world_out boxes; each pass tests the 30 cells against the world planes once and ps2_pass skips the
placements of a cell that is wholly outside a plane, before reading their placement and mesh records. =2 check build:
world_out still runs for each skipped placement and counts any it would not reject.

- Correctness (check build b4crW, 60 s runs): r101 cross 223 placements, 202 fixed, 154 binned (48 wider than a
  cell), ~76 skipped a frame, bad=0; r103 farm 134 placements, only 9 fixed (the rest have a dynamic id slot), 8
  binned, ~4 skipped a frame, bad=0. halt / missing /
  fault 0.
- Cost (b4rW 175f1a2d vs t2crW): r101 cross 57.3 -> 59.8, r103 farm 88.0 -> 86.2 MODELLED. Neither is the lever. The
  pipeline column (issue + dependency + branch, independent of cache placement) did not move: placement walk 0.65 ->
  0.65 (cross), 0.63 -> 0.68 (farm); scenery pipe 11.8 -> 11.9 on both. world_out fell 0.11 ms at the cross, but the
  cell tests in ps2_pass cost what they saved. The +2.5 / -1.8 ms are cache placement: native_static.cpp's code and
  data grew, every scenery function moved, and the I and D fills of MeshDraw::draw, transform_sched, box_mask,
  sg_select changed (cross: imiss +1.0, dmiss +0.65 ms in scenery alone).
- Why it cannot pay: the cross walk does 669 placement iterations a frame, the pass mask already rejects 434 of them
  for a byte compare, and only ~235 reach world_out (~140 rejected, ~93 drawn). The fixed 2-7 ms console world walk is
  in the meshlet level (MeshDraw::draw / run, sg_select, box tests: 6.0 ms cross) and the strip walk (3.1 ms), and that
  work belongs to the ~93 placements that are drawn: a cell or PVS pre-reject cannot remove it.
- Verdict: DROPPED (< 0.2 ms MODELLED on both scenes, in the layout-independent pipe column). Finding for A6 / B5:
  a layout shift alone moved the cross by +2.5 ms MODELLED (I and D fills), larger than every exact lever in this lane.

## B4 rescoped: offline occlusion PVS (coordinator 10-15, ceiling measured first)

Existing culling in the PS2 world path (native_static.cpp), so nothing is duplicated: the pass mask byte per placement;
lean::world_out (world-plane pretest of the placement box); the placement box frustum + 25 m depth cull (box_class /
group_visible); per cluster the same box test, then the LOD level and strip-group selection (sg_select); the fog far.
Visibility data: only PS2_INTERIOR_CULL (r100 house interior portals, offline) and PS2_AREA_HIDE (r107: the PS2 room
code's per-area SMD groups). No occlusion culling for outdoor rooms; no GC / PS2 PVS data.

Ceiling (MODELLED-free count, the user's camera positions): the game logged its camera every frame (PS2_PVS build, warp
line "pvs 2"), frames 500..799: 56 cameras at the r101 cross, 35 at the r103 farm (cam-cross / cam-farm runs).
tools/d367/ps2world/pvs/pvs_cast.cpp "ceil" shoots a ray through every pixel (640 x 480; 2560 x 1920 on 8 cameras to
check convergence) with the game's projection, from the near plane to the 25 m cull depth, against the package's
level-0 triangles (only opaque, static triangles occlude; one-sided ones only from the front). A cluster instance is
visible when any ray hits it before an occluder. "In frustum" = the instance's world box is inside the frustum and the
25 m depth (what the existing culls keep). Vertex counts are level-0 meshlet vertices.

| scene | in frustum (verts / instances per frame) | visible | occluded share (exact, per view) |
|---|---|---|---|
| r101 cross | 37,568 / 210 | 18,877 / 90 | 49.8% (47-55%); 48.1% at 2560 x 1920 |
| r103 farm | 32,056 / 142 | 23,153 / 101 | 27.8%, but all of it is dynamic placements (125 of r103's 134 placements have a unique id); static only: ~0% |
| r103 farm, dynamic placements also occluding (baked spots) | 32,056 | 18,543 | 42.2% |

What an offline cell PVS keeps of that (r101 cross, same cameras, the set of the camera's cell intersected with the
frustum; level-0 vertices drawn of the 37,568 in frustum):

| cell set | drawn | cut |
|---|---|---|
| exact per view (the ceiling, needs per-frame occlusion) | 18,877 (50%) | 50% |
| 2 m cells, eyes 1.0-2.8 m, 3x3 per cell, 16k directions, no dilation | 32,953 (88%) | 12% |
| 2 m cells, conservative (neighbour cells + 3 m near + non-opaque within 60 m) | 34,228 (91%) | 9% |
| 4 m cells, eyes 0.4-3.6 m, conservative (the whole room: 86 KB file) | 35,094 (93%) | 7% |

Why the cell set loses most of it: moving the eye 1-2 m sideways or up reveals a sliver of many clusters between the
houses (535 clusters, each a large piece), and one pixel makes a cluster visible. Per-view occlusion is real (half the
in-frustum world at the cross); a static per-cell set captures a fifth of it.

ms: at the cross the per-cluster world work (everything in scenery except the ~1.6 ms placement walk) is ~15 ms
MODELLED for ~37.6k in-frustum level-0 vertices, so a cut share s is worth about s x 15 ms MODELLED (x1.23 corrected).
This overstates: the occluded clusters are the far ones, drawn at coarser LOD levels.
- cell PVS (7-12%): ~1.0-1.8 ms MODELLED, ~1.3-2.2 corrected, at most. r103 farm: ~0 (its occludable world is
  dynamic placements, which a static set must keep).
- per-view ceiling (48-50%): this figure is WRONG as a ceiling (corrected below, "OCCLUDER_CULL"): it counts cluster
  instances whose box meets the frustum but whose triangles are off screen, which the strip-group selection already
  drops. What a box test against even a perfect depth buffer can cut is 6.2% (cross) / 13.5% (farm).

Runtime (built, default 0, in the tree): PS2_PVS=1 (t2exact.mk) reads /cd/dc/native/rXXX/ps2-world.pvs, finds the
camera's cell once per frame and skips clusters (and whole placements) whose bit is clear. Runtime toggle
re4dc_ps2_pvs_on (default PS2_PVS_DEFAULT=1; warp line "pvs 0|1"; re4dc_ps2_pvs_set() for a benchmark sweep row);
"pvs 2" = no set + a per-frame PS2CAM camera log line (used above). No file / another package's file / a camera outside
the cells: no culling. Run so far: the camera-log mode (cam-cross, cam-farm: halt / missing / fault 0, file=absent
path); the set path has not run (no .pvs on a disc yet). Knob-off identity: test 13 image c1ae83dd + 6 overlays.

Tools (tools/d367/ps2world/pvs): pvs_prep.py (package -> instances + triangles), pvs_cast.cpp (cell sets; "verify"
random eyes; "ceil" logged cameras), pvs_emit.py (conservative sets -> .pvs file, stats, verify).

### PVS format (shared with lane worldlod)

Cluster instance id = position in this walk of the package: placements in R4PW array order; for each, its mesh's parts
in order; for each part, its part_lod clusters in order (first_cluster .. +cluster_count). r101 (bake13 package): 223
placements, 554 instances. A far-LOD level added to a cluster keeps the id (it is the same cluster). The .pvs file
(pvs_emit.py docstring): 64-byte header R4PV v1 with the package's mesh crc / bytes and R4PW crc, an X/Z grid (x0, z0,
cell mm, nx, nz) of 8-byte cells {u16 set (0xffff none), i16 ylo, yhi decimetres}, then deduplicated bit sets
((ninst+7)/8 bytes, bit i = instance i). Memory (heap 4): r101 4 m cells 86 KB (+ 0.5 KB offsets); 5 m cells 55 KB.

Verdict: the r101 cell PVS is worth ~1-2 ms MODELLED at most (under or near the coordinator's ~1 ms bar once LOD is
counted), r103 ~0. Stopped here for the coordinator's decision (10-15: "if under ~1 ms at the cross, tell me before
building more"). Coordinator 10-15: cell PVS DROPPED (the PS2_PVS runtime stays in the tree, default 0; its "pvs 2"
camera-log mode is the useful part).

## OCCLUDER_CULL: runtime occluder test (funded 10-15 on the 48-50% ceiling; NOT built, ceiling re-measured)

Offline extraction (tools/d367/ps2world/pvs/occ_build.py build): conservative planar rectangles from the package's
static opaque triangles (50 mm coverage raster, eroded one cell, shrunk by cell + LOD error + 30 mm, plane pushed behind
its triangles). r101: 1,146 rectangles (73 KB; ~100 kept = ~6 KB); r103: 13 (the farm's buildings are dynamic
placements, which never occlude). Simulated runtime on the logged cameras (frames 500..799; 56 cross, 35 farm), cluster
level, against the 25 m cull and frustum the game already applies:

| test | r101 cross: in-frustum verts culled | r103 farm |
|---|---|---|
| 5-plane frusta of the 16 largest on-screen rectangles (the funded design) | 0.0% | 0.0% |
| all rectangles fused into a 640 x 480 depth raster (hi-Z; far beyond the design) | 0.0% (0.7% at meshlet level) | 0.0% |
| cluster box vs the TRUE depth buffer of all geometry (no occluder can do better) | 6.2% | 13.5% (dynamic placements counted as occluders) |
| triangles never seen by a pixel (not reachable by any box test) | 61.9% of 7,339 in the view volume | 70.9% of 8,565 |

Why: the clusters are large (vertex-weighted median extent 13.8 m) and 9.8k in-frustum vertices a frame belong to
clusters that straddle the near plane; one visible pixel keeps a whole cluster. The flat walls that qualify as exact
occluders cover ~15% of the screen and are not in front of whole clusters. Of the never-seen triangles at the cross,
3,391 a frame are back faces (the PVR culls them; the CPU still transforms them), 1,148 front faces of 4 px or more are
truly hidden, 793 are under 4 px (pixel sampling).

ms: 6.2% x ~15 ms = ~0.9 ms MODELLED at the cross for a PERFECT occluder (unbuildable); the funded design measures 0.
Verdict: NOT BUILT (the coordinator's rule: under ~1 ms at the cross, report first). What could pay instead is finer
granularity (strip groups / meshlets culled by a cheap test, or smaller clusters offline), which is the world LOD /
cluster layout lane's ground, not an occluder test.

## Back-face (normal cone) culling before the transform (coordinator 10-15: ceiling first; NOT built)

Question: at the cross, 3,391 of the 7,339 in-view triangles per frame are back faces. Can the CPU skip their vertices
before the transform? Tool tools/d367/ps2world/pvs/cone.py works on the same logged cameras (frames 500..799; 56 cross,
35 farm). Its runtime model is MeshDraw: the clusters in the frustum, the LOD level (lod_px 5: 198 / 12 levels a frame at
the cross and 127 / 15 at the farm, matching the game's PS2MESH lod counters), the meshlet box test, and today's strip
groups (r101 .r4sg; r103 has none: its sg_tests are 0). Back face: one-sided part (cull != 0) seen from the side
opposite cross(b - a, c - a) (strip parity as the package; flat one-sided ground is 79% / 65% up-facing by this rule).

4. Existing CPU back-face rejection: none before the transform. MeshDraw::meshlet transforms every corner (or the strip
   groups' corner range), and strips are accepted, culled or clipped by outcodes (screen edges, near, far) only. Only
   clipped triangles get an area test after the transform (clip_projected_triangle, p.cull). The PVR culls the rest by
   the part's cull mode.

Corners transformed per frame: model 17,173 cross / 22,671 farm (the game counts 20.8k / 25.8k with passes 1-2). The
world transform (vp::transform_sched) costs 4.44 / 5.35 ms MODELLED, which is 0.21 us a corner.

| skippable corners / frame | r101 cross | r103 farm |
|---|---|---|
| per-triangle ideal: corners used only by back faces (no test could get these without per-view groups) | 10,463 (60.9%) | 6,965 (30.7%) |
| 1. whole meshlets all back-facing (today's unit) | 94 (0.5%) | 149 (0.7%) |
| 1. today's strip groups all back-facing (one corner range lo..hi, as sg_select) | 982 (5.7%) | 149 (0.7%) |
| 2. orientation groups G=4 (k-means of normals per meshlet), one range, exact per-view condition | 1,942 (11.3%) | 2,902 (12.8%) |
| 2. G=4, runtime cone test (axis, half angle, bounding sphere), one range | 1,266 (7.4%) | 1,788 (7.9%) |
| 2. G=8, cone test, each kept group's own corner range (several transform calls) | 2,326 (13.5%) | 3,532 (15.6%) |
| 2. G=8, groups owning their corners (shared corners duplicated: +15k cross / +3.5k farm), cone test | net -6,605 (worse) | net +1,693 |
| extra strip vertices sent by regrouping (2 per new strip break), G=4 / G=8 | +2,456 / +5,077 (of 30.1k) | +1,832 / +3,254 (of 24.2k) |

3. ms (MODELLED; corrected x1.23 WORLD): the best realisable row (G=8, cone, per-group ranges) saves 2,326 x 0.21 us =
   0.50 ms gross at the cross (0.61 corrected), 3,532 x 0.21 = 0.73 ms at the farm (0.90 corrected). That is before
   the runtime test (480 / 409 transformed meshlets a frame x 8 cone tests ~ 3.8k tests, ~0.3-0.4 ms with the record
   reads; sg_select's 400 tests a frame cost 1.18 ms today), the extra transform calls per range (~0.2-0.4 ms) and the
   extra strip vertices (~0.06 ms CPU, more TA work). With G=4 and one range: 0.27 / 0.37 ms gross against ~0.2 ms of
   tests. Net: about 0 at the cross and at most ~0.2-0.3 ms at the farm. Below the 0.2 ms bar on the cross, so NOT BUILT.
Why the ideal 61% does not survive: back-facing triangles share corners with front-facing ones within a meshlet (one
corner range, or duplicated corners), and a fixed group is all back-facing only for some views (k-means cones are
~60-90 degrees wide). The waste is real (6-10k corners a frame) but sits below any fixed-group granularity. Reaching it
needs view-dependent work per triangle, after the transform (that is what the PVR already does for free on the GPU
side).

## B6: read-side prefetch

Finding (MODELLED per-instruction profile, pcprof.py): both streams the backlog names already prefetch their input.
- World transform (mesh_fastpath_sched.hpp): PREF 3 vertices ahead on the vertex stream; the stream's own read misses
  are ~0.02 ms. Its D misses are the colour LUT reads (two 1 KB tables, 1238 + 531 misses a frame at the cross,
  990 + 920 at the farm: evicted by the streaming vertex data and the vertex cache writes in the direct-mapped 16 KB
  operand cache) and write misses to the vertex cache entries (2587 / 3201 a frame).
- Skin kernels (avk_sh4.S): the position records are prefetched (pfwait 0.17 ms: issued a little late). The read
  misses left are the bone palette matrices at a palette change (~215 a frame per load, pos_skin_u16) and the n16
  normal stream of re4dc_avk_light_skin_n16, which has no PREF (565 + 515 misses a frame at the cross).
- What is left for a read-side PREF: the n16 normal stream (1,080 read misses a frame at the cross, ~1,000 at the farm).
  At the console's own price (~24.5 cycles a miss, HWMODEL-CALIBRATION-20261015) that is 1,080 x 24.5 / 200 MHz =
  0.13 ms a frame, the most a perfect prefetch could recover; the model (10 cycles a miss) says 0.05. The colour LUT
  reads are indexed by the vertex's own colour bytes, so a PREF for them needs the next vertex's colour loaded and
  decoded a vertex ahead (~9 more instructions per vertex in a loop scheduled to 34.5 cycles): the issue cost is about
  as large as the misses it would hide (1,769 a frame = 0.22 ms CONSOLE at best).
- Verdict: DROPPED, not built. Below 0.2 ms even at the console's miss price on both scenes, so no console A/B was spent
  on it. Recorded for a later lane (not read-side, so not B6): the vertex cache entries are written with ordinary
  stores into lines that are not in the cache (2,587 write misses a frame at the cross, 3,201 at the farm). The SH-4
  fetches each such line from RAM before the store. MOVCA.L (allocate without the fetch) would remove those fills, an
  estimated 0.3-0.4 ms CONSOLE. It needs the whole 32-byte entry written, starting with the MOVCA store, inside the
  scheduled assembly kernel (mesh_fastpath_sched.hpp writes 24 of the 32 bytes). Per the optimization rule that needs a
  console A/B, plus a reason why a layout change is not enough, before anyone builds it. 10-15: now owned by the sh4zam
  lane (knob SKIN_MOVCA); not a t2exact follow-up any more.

## B5: I-cache code size (HOT_COLD_SPLIT)

Knob HOT_COLD_SPLIT=1 (t2exact.mk; exact, code placement only): every C++ / C object gets -include cold_decls.h, which
declares re4dc_log and re4dc_missing cold; GCC then lays the blocks that only lead to a log line / MISSING report after
the hot path of each function. The image shrinks ~4 KB (text 2,694,004 -> 2,689,876).

Tried and rejected:
- -freorder-blocks-and-partition (cold blocks in a separate .text.unlikely section): does not assemble on SH ("pcrel too
  far": the hot part's constant pools end up out of reach).
- the same + -freorder-blocks-algorithm=stc for the -O1 objects: text +13 KB (block duplication), I-cache fills not
  lower (cross 108,194 vs 108,990), D fills +11%; MODELLED cross 59.6 (layout).

MODELLED fill counts (the model counts misses right; it cannot price them: console A/B only), frames 500..799:

| scene | control I fills / frame | HOT_COLD_SPLIT=1 | D fills | MODELLED ms |
|---|---|---|---|---|
| r101 cross | 108,990 | 104,362 (-4.2%) | 144,203 -> 145,055 | 57.3 -> 57.0 |
| r103 farm | 154,741 | 153,846 (-0.6%) | 213,931 -> 211,847 | 88.0 -> 83.7 (farm runs differ by 0.8M instructions of disc / KOS work: not comparable) |

Image b5drW (committed knob) = b5crW (measured) objcopy image 24960240. Knob-off identity: test 13 image c1ae83dd.
Not done yet: STRICT (it changes block order in logic code too: needs the trace pair), align / KOS gates, and the
console bench disc (bench/definitive 702d82ef via t14/bench aa7554d6 + this knob, Part 1 fixtures, same-tree control;
branch lane/t2exact-bench, worktree /root/probe/lanes-20261015/t2exact/bench, no commits yet).
LAYOUT WARNING (for every lane): layout alone moves the cross by up to +2.5 ms MODELLED (B4's code growth; the sh4zam
lane saw +2.2 ms from moving _end by ~700 B with IMAGE_PAD_BYTES=704, knob off), more than this lever and most exact
levers. A lever's MODELLED gain is only real when it beats a layout control, and the console prices D misses ~2.5x the
model. See "Layout sweep" below.

## Job 1: strip groups (.r4sg) for every released chapter 1-2 room (priced, NOT built; coordinator 10-15)

Today only r101 has a ps2-world.r4sg (bake13, 117,152 B). The runtime is generic: any room whose disc carries a matching
.r4sg (mesh crc) gets the group tests under the test 13 recipe's PS2_STRIP_GROUPS=1; no code change is needed.

Tool tools/d367/worldlean/sgprice.py (runtime model of MeshDraw: box_class + LOD at lod_px 5, box_mask / group_visible
per meshlet, cluster-inside skips, sg_select on the crossed planes, corner range lo..hi, strip outcodes against the
screen edges, near and the PROJECTION far 1e6, not the 25 m cull far). Checked against the game's own counters on the
logged cameras (frames 500..799):

| counter (per frame) | r101 cross: sim / game | r103 farm: sim / game |
|---|---|---|
| sg_select calls | 405 / 411 | (no records) |
| meshlets with a group cut | 282 / 282 | |
| groups cut | 683 / 685 | |
| corners skipped (sg_vskip) | 8,692 / 8,812 | |
| strips walked | 4,564 / 4,402 | 6,147 / 6,088 |
| strips culled after the transform | 1,009 / 988 | 2,172 / 2,024 |

Price per frame (MODELLED, unit costs from the t2exact k0 hw runs, frames 500..799): transform 0.22 us a corner
(cross 4.44 ms / 19.5k, farm 5.35 / 24.9k), a culled strip's walk 0.31 us (lane objs' r101 delta), sg_select 2.9 us a
call (1.18 ms / 405), sg_coef 2.9 us a part, box_mask 1.34 us vs group_visible 1.51 us a meshlet test. Check against the
one measured A/B: lane objs' r101 bench eye (-15300,1721,2377, yaw 90, pitch -8) prices at -0.81 ms MODELLED; measured
-0.82 world (oe23s vs hy23). Corrected = MODELLED x1.23 (WORLD). Cameras: logged (r101 cross 56, r103 farm 35);
elsewhere roomproj.py's samples (door arrivals + ESL enemy sets, Leon's over-the-shoulder rig, 16 yaws; "worst" = the
10% of views with the most transformed corners). Packages = the test 13 disc's (fixture fix-t2crT-cross.json).

| room | views | corners T today (typ / worst) | corners feeding only culled strips | walked strips culled after transform | G=4 corners skipped | saving MODELLED typ / worst | corrected typ / worst | + SG_SELECT_LEAN (job 2) MODELLED typ / worst | .r4sg KB (G=4 / sparse 10 B) |
|---|---|---|---|---|---|---|---|---|---|
| r100 | 416 | 12.2k / 21.2k | 49% | 50% | 34% | 0.66 / 0.84 | 0.81 / 1.03 | 0.94 / 1.26 | 123 / 76 |
| r101 (has it) | 816 | 17.3k / 29.7k | 51% | 52% | 37% | 1.03 / 1.44 | 1.27 / 1.78 | 1.44 / 2.10 | 114 / 69 |
| r101 LOGGED cross | 56 cams | 28.2k | 47% | 49% | 31% | 1.32 | 1.62 | 1.95 | |
| r102 | 48 | 5.3k / 13.1k | 43% | 46% | 30% | 0.19 / -0.04 | 0.24 / -0.05 | 0.31 / 0.19 | 33 / 19 |
| r103 | 320 | 13.1k / 23.1k | 40% | 41% | 29% | 0.53 / 0.76 | 0.65 / 0.93 | 0.81 / 1.25 | 91 / 56 |
| r103 LOGGED farm | 35 cams | 24.9k | 34% | 35% | 24% | 0.71 | 0.88 | 1.21 | |
| r104 | 752 | 12.5k / 23.8k | 42% | 44% | 28% | 0.43 / 0.41 | 0.53 / 0.50 | 0.69 / 0.84 | 57 / 35 |
| r105 | 352 | 8.2k / 18.6k | 49% | 51% | 35% | 0.39 / 0.56 | 0.48 / 0.69 | 0.60 / 0.97 | 68 / 40 |
| r106 | 272 | 14.7k / 25.5k | 44% | 45% | 31% | 0.75 / 0.96 | 0.92 / 1.18 | 1.07 / 1.49 | 81 / 50 |
| r107 | 432 | 12.7k / 34.6k | 40% | 40% | 29% | 0.49 / 0.64 | 0.61 / 0.78 | 0.77 / 1.22 | 75 / 47 |
| r108 | 512 | 8.6k / 17.4k | 49% | 50% | 34% | 0.42 / 0.71 | 0.52 / 0.88 | 0.63 / 1.08 | 75 / 46 |
| r109 | 288 | 17.5k / 27.5k | 29% | 29% | 18% | 0.36 / 0.41 | 0.44 / 0.50 | 0.66 / 0.84 | 74 / 45 |
| r10a | 496 | 8.2k / 19.6k | 43% | 44% | 30% | 0.28 / 0.31 | 0.34 / 0.38 | 0.45 / 0.65 | 65 / 39 |
| r10b | 32 | 8.1k / 15.5k | 57% | 58% | 41% | 0.50 / 0.38 | 0.61 / 0.46 | 0.70 / 0.72 | 61 / 36 |
| r117 | 80 | 11.7k / 31.4k | 40% | 43% | 29% | 0.35 / 0.22 | 0.43 / 0.27 | 0.62 / 0.78 | 76 / 45 |
| r118 | 256 | 11.4k / 19.2k | 44% | 45% | 31% | 0.51 / 0.79 | 0.62 / 0.97 | 0.76 / 1.19 | 76 / 47 |
| r119 | 80 | 17.7k / 39.9k | 32% | 32% | 21% | 0.53 / 0.82 | 0.65 / 1.01 | 0.84 / 1.47 | 83 / 52 |
| r11a | 208 | 6.1k / 17.1k | 47% | 47% | 32% | 0.21 / 0.25 | 0.26 / 0.30 | 0.35 / 0.56 | 66 / 40 |
| r11b | 352 | 7.6k / 14.0k | 55% | 56% | 38% | 0.43 / 0.51 | 0.53 / 0.63 | 0.62 / 0.82 | 68 / 40 |

- The farm: 35% of walked strips are culled after the transform (game: 2,024 culled of 6,088 walked; "51%" is culled /
  emitted), and 34% of the transformed corners feed only culled strips. Groups skip 24% of its corners: 0.71 ms
  MODELLED (0.88 corrected), 1.21 with job 2's leaner sg_select.
- 16 rooms without records: 0.19-0.75 ms MODELLED in the typical view (sum 7.0), 0.24-0.92 corrected. Above the
  ~0.4 ms bar: r100, r103, r104 (0.43), r106, r107, r108 (0.42), r10b, r118, r119, r11b (0.43); with job 2 every room
  but r102 / r11a / r10a. G=2 (half the bytes) keeps about half the saving (r103 farm 0.31; table in
  t2exact-20261015/sgprice), so G=4 is the better trade per KB.
- Heap 4 (no net growth rule): a dense G=4 file is 16 B x 4 x meshlets: 33-123 KB per room, 1,171 KB for the 16. Each
  needs an equal heap 4 saving or a smaller format. A sparse format (a u16 offset per meshlet, records only for
  meshlets with 2+ non-empty groups, 10-byte records with the group box in u8 fractions of the meshlet box, rounded
  outward) is 19-76 KB (714 KB for the 16; same culls, a box test on u8 data; needs a runtime reader change + gates).
  Known tight rooms: r100 (s30 movie skipped: largest block 40.7 KB < 48 KB), r119 (El Gigante end movie failed its
  heap 4 staging when the mesh grew 184 KB), r103 (516,896 B min in play, and MOTION_COLD_POOL keeps 256 KB free).
- Effort with the existing converter: tools/ps2_strip_groups.py runs in under a second a room; sgcheck.py on r100,
  r103, r119 here: 0 triangle-set differences, 0 record faults. Per room: one t11-fix.py data set (re4mesh + r4sg, after
  blackps2 / r100tr4 so the reordered mesh replaces the disc's), one sgcheck run, and the gates: heap 4 at the room's
  movies / enemy loads (s30-style), KOS squeeze, and the emitted-strip identity (PS2MESH strips= equal knob on / off,
  one 1-min pair per room, or batched rooms per warp disc). r100 also needs its interior cell
  (interior-r100.cell) re-stamped: PS2_R100_SMX / TR4 check the package crc, and the reorder changes it (meshlet ids
  do not change). About a day for the 16 rooms with gates, mostly the heap 4 proofs.
- Evidence: C:\Flycast-Evidence\re4-dreamcast\t2exact-20261015\sgprice (per-room result.json + views.json, table.json);
  drivers /root/probe/lanes-20261015/t2exact/s/sgrooms.py + sgtable.py.

## Job 2: SG_SELECT_LEAN (built; exact; below the bar on the layout-independent part; default 0, POC toggle)

What it is (t2exact.mk SG_SELECT_LEAN=1, needs PS2_STRIP_GROUPS=1; render only): lean::sg_select_lean, sg_coef_lean and
box_mask_lean in native_static.cpp. They give the same answers bit for bit as sg_select / sg_coef / box_mask:
- Each plane keeps one term per axis (P = max(n, 0) or Q = min(n, 0)). A +0 term leaves the knob-off value unchanged,
  so dropping it is exact anywhere.
- The kept terms run in the knob-off order (P axes 1, 0, 2, then Q axes 0, 1, 2) as a serial fmac chain. GCC fuses the
  first product on its own, so the chain is spelled with __builtin_fmaf (checked in the disassembly).
- The coefficient table is a packed 16-byte pattern table (kTerms[8]); the crossed planes come from the mask without a
  shift loop; the corner u16s are read straight from the group record; the meshlet's group records are prefetched as
  soon as box_mask_lean says it crosses a plane.
- Runtime switch re4dc_sg_lean_on: warp line "sglean 0|1", or re4dc_sg_select_lean_set(unsigned) for a POC disc row.
  0 runs the original functions in the same image.

Checks (FLYCAST):
- =2 compare build, sg5rW: both versions run and every output is compared. r101 cross for 60 s gave 356,093
  sg_select calls and 556,078 box tests, with sel_bad 0 and bm_bad 0. Evidence: t2exact-20261015\sgchk5-cross.
- Knob-off identity: sgoffrP image c1ae83dd (test 13), and the 6 overlays are identical to t14rckP.

Cost (MODELLED, same image, warp sglean 0 vs 1; r101 cross, frames 300..389 at stride 30, 3 traced frames; runs took
63-65 s):

| build | frame | sg_select | box_mask | sg_coef | I fills / frame |
|---|---|---|---|---|---|
| sg6rW (final, packed table) | 84.0 -> 83.3 | 1.32 -> 0.85 | 1.08 -> 0.61 | 0.30 -> 0.39 | 114,288 -> 102,985 |
| sg3rW (unpacked table) | 84.5 -> 83.9 | 1.33 -> 0.88 | 1.08 -> 0.66 | 0.30 -> 0.44 | |
| sg1rW (first version) | 84.5 -> 83.5 | | | | |

- Layout-independent part (the hw model's base column, the pipeline without cache misses): sg_select -0.19,
  box_mask -0.05, sg_coef +0.06. Net **-0.18 ms MODELLED**, under the ~0.4 ms bar.
- The rest of the -0.7 is I-cache. The lean functions are shorter, and I fills fall 10% in this image. It came out at
  -0.6 to -1.0 in all three builds, but it is a placement effect. See "Layout sweep": a code shift alone moves the cross
  by +-1-2 ms MODELLED.
- Estimate in the brief: -0.35..0.40 for sg_select plus 0.2-0.3 for box_mask. Measured: -0.19 and -0.05 in the pipe,
  -0.46 and -0.47 in total with I-cache.
- Verdict: kept as a default-off knob. The =1 build (sg6rW) carries the runtime toggle for the POC disc, where a console
  A/B on the same image prices the I-cache part. Do not put it in a recipe on the MODELLED number. Job 1's farm figure
  "1.21 with lean sg_select" used the brief's estimate. Use the measured pipe saving instead, which is about half of it.

Evidence: hwmodel-sgs0-cross / sgs1-cross (final), sgq0/sgq1, sgr0/sgr1 (earlier), sgchk-cross (v1 check),
sgchk5-cross (final check). Scripts: /root/probe/lanes-20261015/t2exact/s/bsg.sh, hwq.sh, cmpsg.sh, j2build.sh.

### Job 2 gates (2026-10-15 evening; trace arm sggrT = test 13 recipe + SG_SELECT_LEAN=1, lean on from boot)

- STRICT vs the t2crT control: fight (r101 cross, 802 ticks) STRICT; bell (trg at room frame 300, 547 ticks) STRICT;
  door103 (1,402 ticks, door frames masked as usual) STRICT; decisions MUST-IDENTICAL in all three. Runs c0-bell,
  sg2-fight, sg3-bell, sg3-door; strict/*. (sg-*, sg2-door: cut short by the runner's C: capacity guard, renamed
  _failed-capguard-*; their prefixes were STRICT too.)
- Knob-off identity: sgoffrP image c1ae83dd = test 13 (earlier, unchanged tree).
- Align logger (hwmodel Flycast, interpreter, 60 s, twin sgsq, segments/bell-warp.txt): 0 misaligned accesses.
- KOS squeeze (48 KiB, kos-sg): **FAIL**. fight / call / door pass (min headroom 6,120 / 38,152 / 18,736); leave100 and
  leave103 with 4 KiB pieces fail: "Out of memory ... diff 4096" then OSCreateThread failed at the room change (B5's twin
  passed all ten, headroom 640..2,080 B higher). Release _end: sggrP 8c41cbfc vs knob-off sgoffrP 8c41c53c = **+1,728 B**
  (the =1 image keeps the original functions beside the lean ones for the runtime toggle). Not recipe-ready as built;
  a recipe form would need a lean-only variant (no toggle, originals dropped) and a re-run of the squeeze.
- hw model (MODELLED, same image sg6rW, warp sglean 0 / 1, 3 traced frames): r101 cross 84.0 -> 83.3 (-0.7; pipe part
  -0.18, x1.23 world correction -0.22; the rest is I-cache placement). r100 house (frames 1300..1389): 45.8 -> 45.8,
  0.00: r100 has no strip groups, so sg_select never runs there (hwmodel-sgs0-house / sgs1-house).

### Job 3: .r4sg for every room (from the sgprice table above; NOT built)

Rooms gaining >= 0.4 ms (typical view): MODELLED: r100 0.66, r101 has it, r103 0.53 (farm 0.71), r104 0.43, r106 0.75,
r107 0.49, r108 0.42, r10b 0.50, r118 0.51, r119 0.53, r11b 0.43 (10 rooms). Corrected (x1.23) adds r105 0.48, r109
0.44, r117 0.43. Below the bar: r102, r10a, r11a. Work: see Job 1 "Effort" (about a day for the rooms with gates, the
heap 4 proofs dominate; sparse 10 B format 19-76 KB a room needs a runtime reader change, dense G=4 33-123 KB a room
needs equal heap 4 savings).

### SLAB_PIN (job 3 WIP from the 10-15 stop; layout lever, NOT built or measured)

Uncommitted native_ui.cpp + t2exact.mk change found in the tree after the stop: pins the 64 KiB native model slab head
to operand-cache index 0x3080 +- 0x200 with a temporary filler block. Layout lever, so console A/B only. Saved as
/root/probe/lanes-20261015/t2exact/slab-pin-wip-on-866edc60.patch and on local branch lane/t2exact-slabpin; not in the
lane stack.
