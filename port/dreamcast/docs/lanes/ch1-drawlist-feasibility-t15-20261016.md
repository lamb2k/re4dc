# Precomputed world draw decisions: bounded feasibility audit

Status: investigated; no runtime patch, claimed saving or acceptance. Source is the isolated Test15 CPU branch, with the current spatial32v3 approved-L2 geometry as the next-stack asset candidate. This investigates avoiding repeated decisions, separately from the older outdoor occlusion PVS experiment.

## What can be reused

The implementation can keep live vertex transforms, materials and submission while reusing proven visibility, cluster LOD and strip-group choices for immutable opaque scenery. `native_static.cpp` already selects one LOD per cluster, skips fully outside meshlets, and narrows transformed corners to surviving strip groups. Existing placement pass masks, inside tests and world pretests must remain part of the baseline.

A position-only list cannot reproduce these decisions. `ps2_pass` uses the view and projection, cull-far, quality LOD tolerance, placement affine and live area/object gates. `MeshDraw::draw_clusters` uses nearest **view depth**, not just eye-to-object distance. The subsequent meshlet and strip-group decisions depend on the frustum. Changing aim or projection at the same eye can change the list. Dynamic source objects, sky, non-opaque parts and r101 gate placements 209–222 stay on the live path.

Relevant source: `game/platform/native_static.cpp`, `lean::box_class`, `box_mask`, `sg_select`, `MeshDraw::draw`, `draw_clusters`, and `ps2_pass`. The existing `PS2_PVS` lookup stores conservative potentially visible sets; it does not replace all of these decisions.

## Current cost evidence

These are **self costs** from the console-fit SH-4 model, r101 cross, frames 500–799, stride 10, 30 samples, same executable. They do not include every inlined selection operation and are not all removable.

| Named decision function | Current stack, ms | With spatial32v3, ms |
|---|---:|---:|
| Placement world-plane test | 0.531546 | 0.317350 |
| Box classification | 0.818868 | 0.789195 |
| Meshlet plane mask | 0.488364 | 0.471381 |
| Strip-group selection | 0.874225 | 0.836718 |
| Disjoint subtotal | 2.713004 | 2.414643 |
| Whole sampled frame | 61.420635 | 60.692146 |

Use the **2.414643 ms** subtotal when pricing a follow-on on top of spatial32. It includes protected/live geometry as well as the immutable candidate pool, so applying its entire value to a static cache would overstate the benefit. The separate nominal current-baseline subtotal is 2.525184 ms; it belongs to a different model configuration and must not be added to this table. The supplied 133/234-cycle ratio was not reproduced as a current removable-cost measurement; vertex transformation, strip walking, binding and submission remain live work.

Evidence: `C:/Flycast-Evidence/re4-dreamcast/codex-cpu-t15-20261016/drawlist-cost-census.json`, derived from both `proj/console.pcs.tsv` files and the common `cg.syms.txt`.

## Offline census

`drawlist_census.py` uses the existing R4IM reader and the **current spatial32v3 package**, selecting only immutable opaque candidates. The camera input is the historical 2026-10-15 t2exact cross sample: 56 unique full camera poses from its frames 500–799. It is not a new Test15 camera capture. The census uses float64 geometric box tests and cannot establish SH-4 bit-exact decisions or performance.

- 301 candidate cluster instances across 9 placements; 637 meshlet instances across all LOD levels.
- The 56 poses produce 6 unique cluster visibility/LOD lists and 16 unique full cluster/meshlet/strip-group decision lists. This shows useful repeated decisions in this sample, despite all 56 camera keys differing.
- A synthetic 90-degree turn at the same eye changes 135 of the 301 complete cluster decisions; changing projection scale by 20% changes 32.
- All 32 probes displaced by 250 mm in X or Z change at least one decision; the mean is 8.375 clusters and the maximum is 14. Most decisions remain stable, but copying a whole cell's center list would be incorrect.
- A dense cluster-only list takes 76 bytes per pose; a simple representation adding masks for every candidate meshlet at every LOD takes 395 bytes. An illustrative 1,024 positions × 16 yaw × 4 pitch grid would take 4.98 MB / 25.89 MB before indices, guards and projection variants. This is an example uncompressed layout, not a required coverage estimate or lower bound. Deduplication could be substantial; these 56 poses need only 16 distinct full lists, but do not establish room coverage.

Evidence: `ch1-drawlist-census-t15-20261016.json`, with hashes of the input package, sidecars and camera file. The first local census attempt misread the R4ID header and was rejected; the retained script validates its magic/version/count/CRC and slices IDs after the 16-byte header.

## Concrete first implementation candidate

Use a **sparse cache of certified decisions**, first for the cross's immutable opaque clusters. Each entry must identify the exact package and generation, render pass, view/projection domain, cull-far and LOD tolerance. A certificate covers bounded camera position and orientation, and proves that a particular cluster remains outside, or that its LOD/meshlet/strip-group decisions remain constant throughout that domain. Merely sampling bucket corners is insufficient for nonlinear orientation ranges. Use analytic interval bounds or an exact runtime guard; values near float-comparison boundaries fall back to the current path.

Keep mixed/boundary clusters and all live gates on the normal path. Preserve original traversal and draw order. Do not cache transformed vertices, live matrices, allocator results or material side effects. First count certificate hits, fallbacks and bytes without changing output; then permit decision reuse only for certified hits. A small sparse table is preferable to allocating an all-room pose grid before its hit rate is known.

The diagnostic must compare the existing and reused cluster level, meshlet set, strip groups, corner range and order for every hit, with zero mismatches. Missing/stale package data, view changes beyond the domain, room transitions and resource pressure must take the normal path. Measure whole frames on top of the actual preceding accepted stack and keep lookup/guard cost in the result. Finish STRICT/decision comparisons, exact submitted-geometry comparison, the fight/bell/door route, memory/fragmentation gates, and matched console A/B before claiming a gain.

This remains distinct from the rejected prepared-descriptor experiment (`WORLD_DRAW_PLAN`, +0.651833 modeled ms and 68,904 borrowed arena bytes), and the rejected placement grid walk. Neither measured a cache of camera-dependent draw decisions, so those results do not settle this proposal. They do show why saved arithmetic alone is insufficient.

## Reproduction

Run the script with Python and NumPy, passing the repository's `tools/d367/ps2world/interior` directory, the private `assets/spatial32v3` directory, and the historical `cams-cross.txt`. The full paths and SHA-256 input identities are in the JSON. Output is analysis only; no source package is overwritten and no disc is staged.
