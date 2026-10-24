# Bounded triangle-shadow feasibility

The frozen exact-math plan is `PLAN.md` at 1c8dd9c55. The earlier all-LOD surface
lemma at 5f60ff133 is unchanged. This folder adds host tools only; it emits no
PVS, package, data option or runtime change.

`exact_shadow.py` evaluates full eye-box x all-LOD target-box predicates with
exact rational arithmetic. Its exact rational intervals enclose caller-specified
source/eye/target perturbations. The fixed-triangle determinant is separately
affine in E and T, so all 64 corner pairs bound the complete product. One uniform
plane/edge sign is mandatory. Strict contact, parallel/ambiguous and degenerate
cases fail open. The requested 32 mm boxes and 2000 mm source clearance are IDEAL
research conditions, not a derived SH4/raster error theorem.

`feasibility.py` binds source fb254, its real divisor20 profile, frozen R6 assets,
original/current physical affines and IDs, actual texture flags and full RECT21
descriptors, and the preserved 19 serialized old-camera domains. It intersects
oriented triangles over each source cluster's independently selectable LODs.
Unique dynamic IDs, singular poses, unsupported material/path and vertex alpha
are excluded. All-LOD target bounds include every actual authored source vertex.
No guessed closure, seam welding, filled portal or sampled-ray proof is used.

The floating-point prefilter and area ranking can lose candidates. A rejection
is NOT an exact negative certificate. `test_exact_shadow.py` includes an exact
dyadic nominal positive that the float filter rejects after cancellation, so
this boundary is explicit. Only surviving pairs enter the exact oracle. Test
controls include continuous tensor interpolation/barycentrics, interval endpoint
containment, both orientations, requested-error positives, strict plane/edge
contacts, degeneracy, invalid boxes and uncertainty-induced ambiguity.

`duplicate_panel_checks.py` executes the unchanged production Panel matcher,
table guard, observer, commit and cut function against synthetic host state. The
one actual oriented triple may satisfy `{a,b,c,a,b,c}`. All 49 assertions pass;
matcher, material-commit and stale-epoch mutants fail. One-LOD, material, owner,
clip, truncation, degeneracy, partial/missing observations and stale receipts
remain guarded. The actual host frame guard still refuses. Controlled validity
isolates receipt tests; these controls do not admit real geometry or raster
coverage and do not change the runtime.

## Frozen run and refusal analysis

The source 2f5cd21cf run examined only the 256 largest area-ranked eligible faces
in each one-LOD and multi-LOD stratum: 512 of 24,874 descriptor-qualified stable
unconditional faces. Across 19 full serialized domains and 220 static ordinary
cluster targets, 2,130,432 pairs yielded zero float-filter survivors and therefore
zero accepted exact candidates. This is partial coverage, not exact exclusion
of every rejected pair or a global NO-GO for triangle occlusion. Peak RSS 84,240
KiB, hard address-space cap 256 MiB, one job.

`diagnose.py` preserves that same 512 cohort. Heuristic float refusals divide into
1,463,849 target-plane cases, 201,699 eye-plane cases and 464,884 triangle-edge
coverage cases. The 20 closest opposite-plane pairs all fail the exact sufficient
edge test. The 40 existing per-LOD meshlet boxes in those same closest pairs also
fail it; this narrow counterfactual does not exclude all smaller geometry.
The 220 target boxes have diagonal 54 mm to 11.90 m, median1.257 m. Cells are 2 m in
XZ and 600..1400 mm high. These facts explain the tested geometry; they do not
establish camera/raster admission.

Current PVS target bits address placement-owned cluster instances shared across
LOD choices. Existing authored per-LOD meshlets have no individual target bits.
They cannot become a supported smaller target group simply by changing this
offline search. No smaller partition or new runtime/data contract is approved.

Current renderer admission and cuts remain zero. Actual selector-rounding/true
eye enclosure, source cull and near/far clipping, SH4 arithmetic, raster edge and
depth coverage, resident material/header state, complete 16-panel committed
source-prefix receipts and source-matched net exclusive cost remain unclosed.
MODELLED ms is unavailable; the >=1 ms GO is not established. No target build,
Flycast, console run, gain or look claim is made. All unproved and unsampled
cases keep drawing.

Private evidence: `C:/Flycast-Evidence/re4-dreamcast/interior-vis23-20261023/I001-fb254-triangle-shadow-r1`.
It retains the source2f run, preliminary receipts, exact run-source snapshots,
synthetic controls, the unchanged control PVS, independent math note and seal.
Historical cameras are e9bf7: 54 s requested, 55.4..55.8 s total wall; they are not
current exact 55-child qualification. Private geometry/report coordinates stay
out of Git. No continuation beyond this bounded source sample is implied.
