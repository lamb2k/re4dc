# Independent connected implementation review — 2026-10-24

Reviewer: `/root/pvs23_assets_sol61`. **Source CLEAR for the bounded host/offline implementation at `581482ed4274ac30e1c9da8ec92760e9b3f93354`. No actionable defect found in the strict/kernel oracle, source/camera/all-LOD bindings, focused controls or stated result boundaries.** The new height-band work is outside this review. No runtime/table/domain-bit/FP admission, actual cut or speed acceptance follows.

Reviewed `exact_patch.py`, its tests/control runners, `connected_feasibility.py`, `connected_pair_feasibility.py`, `connected_diagnose.py` and `connected_pair_point_diagnose.py` under `/root/work/lanes/interior-vis23/port/dreamcast/tools/d367/interior_vis23/triangle_shadow_next/`. Their live bytes matched the frozen commit on inspection. Only this note and the adjacent `review-connected-controls-20261024/` receipts were persistently written. No author output, asset, source, SDK, guest, domain or search was changed.

## Oracle and topology

`indexed_disk()` enforces nonempty distinct-index faces, no duplicate unoriented face, edge incidence 1/2 and opposite interior use, connected FACE adjacency, Euler characteristic 1, one simple directed boundary cycle and connected vertex links with the correct boundary-path/interior-cycle degrees and endpoints. It does not infer adjacency from equal coordinates. These are the reviewed disk conditions rather than Euler characteristic alone.

`prove_patch()` retains one rational position/interval point per actual used index across all faces. It rejects nominal degeneracy and requires every uncertain actual face to have a uniform strict eye-side sign and the opposite target-side sign. The L1 normal upper bound conservatively supports requested clearance. This also supplies every projected face's nonzero consistent orientation. The chart is fixed from one nominal normal and one global sign; strict positive denominators cover all source interval points and eye/target corner combinations.

Strict mode completes the ENTIRE boundary-other-vertex convexity stage before target tests. Kernel mode removes only that stage and records winding `at_least_one`, correctly retaining all face/chart/topology/plane/target constraints. Target edge determinants enclose all 8-by-8 eye/target corner products. Exact interval arithmetic and separate affinity supply the complete-box proof reviewed earlier. Shared-variable interval dependency can reject useful geometry, not tighten the enclosure. Internal triangle edges remain covered by the finite CLOSED union. No nominal hull, seam weld, sampled-ray acceptance or float prefilter is present.

A refusal is failure of a sufficient criterion, not global non-occlusion. In particular, adding actual faces can shrink the boundary kernel even while enlarging actual coverage. The six-face kernel's failure and a correctly authenticated two-face subpatch's point-eye success are therefore consistent.

## Source, cameras and all-LOD bounds

The six-face runner redecodes the pinned physical package/policy/IDs and actual parity-correct ordinals 4–9, meshlet 951, source placement 165 / part 230 / cluster 234. It verifies whole source ownership, one declared source LOD, nonsingular affine, unconditional source field and membership of EVERY actual triangle in the current stable ordinary opaque descriptor cohort. No actual cache/kernel/clip construction is inferred merely from same source indices.

The target remains instance 299, placement 209 / part 268 / cluster 272 / field 209, ordinary/static and unconditioned, with the existing exact all-authored-LOD box from `collect()`. Frozen report/input hashes, material pack/header/RECT21 pins and current source/profile are rechecked. The discovery's selected-LOD component is bound to these redecoded triples; it does not replace the one-LOD/source or target-bound checks. Source 165 precedes target 209, but actual source emission acceptance is explicitly UNPROVEN.

Both full-domain runners authenticate R6 preparation/raw log hashes, exact rational inverse eyes from stored f32 view bits, the same 129 retained label/frame/view/eye records and serialized control cells. Local 500/250 windows preserve full old Y limits and their exact prior recorded boxes wherever those earlier sparse variants existed. Historical whole-cluster pricing rows are namespace-checked. Full 2 m and local boxes remain ideal representations: actual float selector preimage and true-eye error are not established. Repeated boxes may reuse a proof cache; the reported counts are per retained camera, not claims of distinct domains.

The pair runner preserves the six-face result hash and permits ONLY the already authorized actual ordinals 8/9 `(14,13,12),(13,14,15)`, verified as the same component subset. It rechecks the same source/material/camera/target identities. Point diagnostics additionally pin their exact input report and executed runner SHA, reconstruct the same eye and call the unchanged sufficient oracle over the WHOLE target box. Their separate closed-ray corner hits are explicitly not continuous-box proofs.

## Independent controls and replay

Serial host reruns used 268,435,456-byte address-space caps:

- Ten patch math groups passed; all six mutations failed intended assertions. Coverage includes solid/warped disks, exact strip-style topology, real annulus holes and 27-sample false assurance, broken/copied/reversed/pinched topology, chart and plane failures, boundary/internal seam cases, requested uncertainty and kernel collinear/concave/outside-kernel cases. Peak child RSS 17,664 KiB.
- The chart mutation changes the refusal ROUTE from `chart_unknown` to a later convexity refusal. It tests that the chart guard executes; this fixture does NOT demonstrate unsafe acceptance when the chart check is removed. The other five mutations produce the intended failed refusal assertions. No incidental exception is counted as qualification. `-B` avoids stale bytecode between variants.
- Thirty-nine unchanged production three-Panel/six-triangle synthetic receipt assertions passed under host UBSan; missing-triangle, material and epoch mutants failed intended assertions. The actual host frame guard is checked false before the fixture explicitly arms isolated validity. Peak child RSS 60,804 KiB. Stub material/pose/scene/cache values are not actual target rendering qualifications.
- The sealed diagnostic's exact closed-ray positive/reversed/contact and miss/parallel/before-source group passed independently.
- Independently replayed ONLY the fixed hut 647 point and preserved 250 mm full-height box. The pair's point-eye/whole-target-box nominal proof is positive and matches its sealed exact result. The preserved full-height250mm pair proof still refuses. The six-face point kernel still refuses edge 10→8. Verified pair positions, target box, inputs and material pins equal the six-face report, and the pair is exactly its last two triangles. No new eye/domain/target or requested-error experiment was introduced. Replay peak RSS 21,824 KiB.

My first replay equality check compared Python tuple-valued index fields against JSON lists; a JSON-normalized comparison resolved that representation difference. The successful receipt journals it. No author result or geometry changed.

## Four sealed outcomes and their limits

Verified every byte count/SHA256 in all four manifests: 42 listed entries, no mismatch (46 files including the four manifests).

| Evidence root under `C:/Flycast-Evidence/re4-dreamcast/interior-vis23-20261023/` | Manifest SHA256 |
|---|---|
| I001-fb254-connected-first-r1 | b6b5333160fbed2fa735ad9a206a3d14d3d8ae931498241364570a060451c4f7 |
| I001-fb254-connected-point-diagnostic-r1 | e5afcb02de8dc22cc377779bb8710c01364e94110b3514b31607a8ae784cde15 |
| I001-fb254-connected-pair-r1 | dc42dea6ae6d27e53eabac7e27235d47f81e6b9f1209a3dca162bb1e5457516f |
| I001-fb254-connected-pair-point-r1 | 1dcc1e883d4be1bda21009d9581f4092722f4300c6d95ed94b9785bcd73d2aa6 |

At EACH full 2 m / local 500 mm / local 250 mm size, all 129 six-face strict cases refuse boundary convexity and all 129 kernel cases refuse a target edge. All129 actual pair cases likewise refuse at EACH full-height size. Selected host cut corners and nominal acceptances remain 0; requested-error stages are not reached. Recorded full-run peaks are 105,840 KiB (six-face) and105,552 KiB (pair), with 256 MiB cap / jobs 1. Diagnostic scripts enforce the same cap but their sealed reports do not record peak RSS; no diagnostic peak claim is made.

At the fixed exact point eye, the full six-face kernel fails edge 10→8 for all eight target corners. Corner-ray hits on the last two faces merely motivate a subpatch analysis. The separate pair point-eye proof DOES certify the continuous IDEAL whole target box via the reviewed union theorem. The same point proof appears beside all three domain diagnostics; these are not three accepted camera cells. Its preserved 250 mm box fails edge 12→14 at 16/64 eye/target corner pairs, showing why the point result cannot be promoted to that box.

The point positive uses nominal ideal coordinates and a zero-volume eye domain, with no requested 32 mm/actual transform envelope, emitted cull, near/far, selector, raster or receipt qualification. Runtime admitted cuts remain 0, MODELLED ms is unavailable and the 1 ms GO remains unestablished. The outcomes establish neither global impossibility nor current rendering gain.

Failed early binding attempts and intermediate bytecode/control hazards are preserved and explicitly separated from final successful reports. No incomplete attempt is relied on for the final proof/result claims.

## Key identities and own receipts

| File | SHA256 |
|---|---|
| exact_patch.py | 2f4f2017013a7d8ffca3d6563a79f699b3277f066e1a6fdc0fe558d4fb019f41 |
| connected_feasibility.py | 9b81928484efff845536ce75862b2bb78a9370a8de01158b2756cfe8c585518d |
| connected_pair_feasibility.py | 0f44bbc9a1bd24917ea18c890d56228377b3579e1cf334b496e39253d59cb2dd |
| six-face report.json | 7715fe03a89fd5d7e03b716065a57583bc061b66e549ca0b9059d2ae8906c181 |
| pair report.json | dbda668aa4cd20f4bea43b742f742de2c8ef59f49c28e1f86836e0a741bb92d6 |
| pair-point diagnostic.json | 57c4f139531348b1a70224908eb51fa304ece85a41f81666a1df8dc0d31333c0 |
| own math.json | 867715b497a1098ca95a19927ab1758de9e41a6c893765924ecd2be07c77d036 |
| own receipts.json | b51c0d0cdf1441660cb6f83dc7d18d23de33fd038d2a93ff641255a983579a64 |
| own fixed-point-replay.json | 03681b4f71504f46c2cee68a5bb2c0df8856204e5a2294446ee7300abba43e6d |

Own receipts are in `C:/Game Dev/Emulators/codex-lanes/interior-vis23/triangle-shadow-next/review-connected-controls-20261024/`. Actual target/all-LOD, source-prefix, pose/material, true-eye/selector and matrix/FP/raster/near/clip/generation admission obligations stay intact. No mutable future height-band or table proposal was reviewed or approved.
