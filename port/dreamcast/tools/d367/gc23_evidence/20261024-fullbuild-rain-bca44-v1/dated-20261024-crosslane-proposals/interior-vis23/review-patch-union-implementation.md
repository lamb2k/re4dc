# Independent actual union implementation review — 2026-10-24

Reviewer: `/root/pvs23_assets_sol61`. **Source CLEAR within the bounded host/offline scope; no actionable defect found in the implemented sufficient geometry predicates, fixed-cohort binding, controls or reported limitations. Zero useful cuts in this cohort is not global impossibility. No runtime/data admission or speed acceptance follows.**

Reviewed clean source `16a6fe76cfae3dfa6d4e307d93e3f6040f52032a` under `/root/work/lanes/interior-vis23/port/dreamcast/tools/d367/interior_vis23/triangle_shadow_next/`. The actual run is frozen at `721dff3ec91941516d30898d5f60836a450d09f8`; its oracle and runner match the current reviewed bytes. The final checkpoint hardens control-failure qualification and documents results. This review performed only source/evidence inspection and small independent host controls, with 256 MiB address-space caps and one compiler/process at a time. No SDK, guest, further geometry search, source/data/runtime changes or author-output mutation occurred. This is the only persistent review file written.

## Predicate implementation

`exact_union.py` implements the prior `review-patch-union-plan.md` theorem rather than an inferred coplanar hull. `boundary()` authenticates two three-distinct-index triangles, exactly four used identities, one oppositely traversed shared edge and one four-edge boundary cycle. It rejects coordinate-equal copies with different IDs as a connecting edge. Physical coincident/degenerate or angularly invalid positions must additionally survive the strict geometric predicates.

`prove_union()` maps each actual used index to one nominal rational position and one uncertain interval point reused by both triangles. Exact rational interval operations may over-enclose repeated variables but never narrow their possible values. Both actual triangle planes must strictly separate all expanded eye and target corners with one common orientation, including the requested clearance times a conservative L1-normal upper bound. The chart direction is fixed from the first NOMINAL normal after selecting that uniform orientation; it is not independently varied at corners. Positive chart denominators are tested for every source interval vertex and every target corner against every eye corner.

The actual shared diagonal's third vertices must remain strictly on opposite angular sides over the entire eye box. Each boundary edge tests both other boundary vertices for convexity and all 8-by-8 eye/target pairs for strict outer coverage. Fixed-source determinants are separately affine in eye/target coordinates, so product-corner interpolation covers complete boxes. Interval predicates enclose each uncertain source choice before that argument applies. Ambiguity rejects. The two closed projected triangles include their true common diagonal; no strict internal-edge target test accidentally opens a seam. Noncoplanar fourth vertices retain their second real plane.

No division or float prefilter participates in these exact union decisions. The chosen chart is intentionally only one sufficient chart, and the normal/L1 interval tests are conservative; a refusal is not a necessary visibility result. The current generic oracle does not by itself prove source identities belong to a renderer package; that is the runner's separate responsibility.

## Source/camera/domain binding

`union_feasibility.py` pins the prior 512 report, exact closest-20 diagnostic and smaller-domain report, the independent theorem note, frozen R6 report/preparation, exact source inputs, material prerequisites and source/profile binding. It recollects the current stable unconditional descriptor cohort and requires each seed's placement/part/cluster/meshlet/parity triple/grid identity to exist in it. Its adjacent companion must use the same actual meshlet corner indices, source placement/part/cluster, one declared LOD, valid ownership and ordinary material classification. Exact physical positions use the authenticated affine/grid mapping. A same-index companion in this one-LOD cluster is an actual triangle of that selectable source, not an inferred extra LOD face.

The runner authenticates the old raw log hashes through `raw_cameras()`, reconstructs exact rational inverse eyes from the actual f32 view bits and compares all 129 retained label/frame/view/eye records with the frozen smaller-domain report. The original serialized control table is hash-bound by `cells()`. Local 500/250 mm windows retain the full old signed-decimetre Y band, f32 window origins and exact recorded boxes; containment of each authentic eye is checked. These remain IDEAL domains: the actual float selector preimage and true-eye error are explicitly unproved.

Only the same closest-20 source/target identities are used. The exact prior-40 authored per-LOD meshlet boxes are reached only after all whole-cluster nominal union counts stay zero, with target cluster/level/meshlet membership checked. They remain counterfactual bounds unsupported by the current PVS bit namespace. Historical whole-cluster selector weights are namespace-checked and labelled host replay; per-meshlet authored corners are not priced as selected work. The report's `correlated_cache_indices` means authenticated ideal source-index identity, not actual kernel/clip/raster qualification; the limitations state this explicitly.

## Independently executed controls

Eight geometry test groups passed. They include a planar diagonal union and a real noncoplanar union where neither triangle individually covers the target box, reversed overall orientation, broken/reversed/copied topology, chart/plane contact, concavity, outer-edge contact, both-real-plane necessity, requested-error positive, error-ambiguous negative and correlated endpoint controls. Outer-edge removal, ignored uncertainty and omitted second-plane mutations each failed the intended assertion. The hardened runner rejects incidental exceptions as mutant qualification. Peak math child RSS was 17,664 KiB.

The actual unchanged production Panel/table/observe/commit/cut source passed 38 assertions on a synthetic two-triple shared-cache transcript under host UBSan. Both real triples are needed; omitted triangle, material-gate bypass and stale-epoch bypass mutants failed their intended assertions. Peak receipt child RSS was 60,364 KiB. All processes had a 268,435,456-byte address-space cap; compilation was serial.

These are controlled package/cache/material/scene transcripts and explicitly armed internal validity, not target frame-guard acceptance or actual source rendering. The earlier duplicate-panel controls separately checked actual host frame-guard refusal. Neither suite qualifies SH-4 arithmetic, material residency, source pose, projected cache/kernel/clip identity, near/far or raster edge/sample/depth coverage. The preserved preliminary KeyError mutant receipt is journaled and not used as final qualification; fresh independent controls reached the intended assertions.

## Sealed result and limits

Independently verified all 24 manifest-listed files with no byte-count or SHA256 mismatch (25 files including manifest). The eight seed-oriented descriptors represent six distinct physical pairs: source placements 69/165, actual meshlets 491/953/946. No claim of eight independent physical surfaces is made.

At EACH full 2 m, local 500 mm and local 250 mm domain size, 184 whole-cluster cases have zero nominal proofs and zero selected host cut corners. Only after those zeros, 278 cases from the prior-40 per-LOD boxes at EACH size likewise have zero proofs. All recorded refusals are `edge_unknown`. This establishes that these particular sufficient tests did not accept the bounded cohort. Early outer-edge refusal can leave later edges/convexity predicates unexamined; it does not imply their complete proof passed. The author result note says so.

Requested uncertainty is not reached after nominal refusal; reported zero positives is not an executed real-asset interval qualification. Renderer-admitted cuts remain zero. MODELLED ms is unavailable and the 1 ms GO remains unestablished. The exact pair search is bounded; it does not rule out other triangles, larger authenticated patches, alternative sufficient charts or less conservative represented bounds. No global impossibility or actual gain is established.

Actual numeric/true-eye/selector bounds, correct emitted cull side, near/far and clipping, identical actual shared endpoint construction, raster seam/depth coverage, live immutable material, target pose and successful committed source-prefix receipts remain admission requirements. This review authorizes no table, finer grid allocation, new target partition or broader source search.

## Identities

Private sealed root: `C:/Flycast-Evidence/re4-dreamcast/interior-vis23-20261023/I001-fb254-union-r1`.

| Item | SHA256 |
|---|---|
| SHA256-MANIFEST.json | 9f6474675ec9ffdd80800b68346b85aaa33d6ef999415af3dbb2132207afc1a8 |
| report.json | 1fc7ea63666f64c501d621b0f08f3437ff57473c1459683b756c5d3656db1da4 |
| exact_union.py | b891139899814a5dc840d17982cbbc5147318d70e27ac91dfadd4928789880f8 |
| union_feasibility.py | a1f57cbb3895c28e2790809d2b8c9001e2cd410fc31cc7e8299fae303f7c5c53 |
| final test_exact_union.py | 986ae77236a7f1b3ed8a02d446bd2fb54d8a479f90385c7c8e567ce307aa59ae |
| final union_math_checks.py | aa2c74016d4255b04b26798423c5b5a2b7695a0cfbb8dfbead55bde98f3c5eb4 |
| final union_receipt_checks.py | c1fed2af5fffb002f7829003265ca5b87acce4c0d40e66a38e16628cc4b2c13b |
| unchanged pvs23_proof.hpp | 1881d1d814fdc7bb787991a2cd6f67ebab293d5c2a7efa42cdd515fb07821ba4 |
| unchanged pvs23_runtime.inc | 09a05d430e31216570bcce9e7ef6a8c5fde929bd32f4c2b6979a25df967609a0 |
