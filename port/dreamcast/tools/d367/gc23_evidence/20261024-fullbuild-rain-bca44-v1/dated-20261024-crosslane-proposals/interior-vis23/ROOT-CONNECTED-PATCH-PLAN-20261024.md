# Root next-proof brief: connected opaque patches

2026-10-24. Root integration/proof review, following the bounded exact-union zero result and full-scene discovery. This is an offline proposal, not runtime/data admission. Current integration remains fb254e82; frozen interior implementation16a6fe76 and discovery0f902577 are distinct inputs. No recipe, asset, loader format, allocation or culling enablement.

## Why this next step

The prior exact proof covered only six distinct physical two-triangle patches and found no cuts. Full-scene discovery reports larger actual connected opaque patches and some 27-point hidden-cluster hints. Samples can miss a hole: they are never a certificate. Prefer candidates whose source precedes the target under the existing accepted-source-prefix contract. A late source is not promoted just because its shadow looks promising.

## Proposed exact-real sufficient test

Use a complete connected patch of actual indexed triangles. Do not flatten, weld by equal coordinates, fill holes, infer a wall from an AABB, or insert diagonal faces. Refuse unless its oriented combinatorial complex is a triangulated disk: connected faces; opposite use of each interior edge; one simple boundary cycle; valid single-cycle/path vertex links; orientability and Euler characteristic1. A shared endpoint is the same source index with the same actual transform/cache/kernel/clip generation, not a separately rounded copy.

For every eye E in the closed camera box:

1. Every actual patch vertex lies in one common positive perspective chart. The chart and strict denominator bounds must be fixed and verified over the full eye box.
2. Every projected triangle has a strict nonzero orientation with the same sign. Exact determinant sign bounds are affine in E and may be checked at every eye-box corner.
3. The projected boundary is strictly convex in that orientation. Check each oriented boundary edge against every other boundary vertex, over every eye-box corner. Strictness excludes degenerate edges/faces and projected folds at the boundary.
4. Every target-box point projects strictly inside every outer boundary edge. The determinant is multi-affine in E and target point T; exact checks on all eye/target box corners suffice for this conservative inequality.
5. Every actual source-face plane separates the whole eye box from the whole target box with the correct signs. This conservative condition ensures the source intersection for a covered target ray is strictly between eye and target. It may reject useful folded patches; rejection is draw-all.

Justification to review independently: a continuous oriented triangulated disk with a simple convex degree-one projected boundary and uniformly positive nondegenerate face orientation covers the boundary interior. Degree counts triangle interiors positively; an interior point has degree1, and shared edges follow by continuity. Thus each target ray meets some actual triangle. Plane separation places that triangle before the target. The argument concerns real geometry only.

## Conditions that remain outside this math

Existing runtime source/target namespaces and admission stay unchanged. Discovery uses an authenticated selected-LOD full-authored envelope; that is not an emitted roster. An exact candidate must independently close all required source and target LOD cases, material/alpha/conditional rules, actual source-prefix acceptance, cache/generation ownership, near/clip coverage and renderer rounding. A selected-LOD sample cannot silently become an all-LOD certificate. Whole-cluster targets exclude all own-instance sources; counterfactual meshlet targets cannot enter a whole-cluster table.

No runtime bit may clear from the exact-real test alone. Requested/actual floating error bounds need their own reached proof stage and controls, including correlated shared endpoints and actual matrix/transform paths. A first exact-real positive is a reason to investigate those remaining guards, not a performance or appearance pass.

## Bounded prototype after independent plan review

Use the existing host-only 256MiB/one-numeric-thread bounds, actual pinned source/mesh/policy/camera hashes, and at most three ranked supported target/source patch candidates first. Keep original zero-result cohorts and refusal runs. Controls must include a real hole, missing triangle, pinched link, reversed face, duplicate/copied endpoint, nonpositive chart, concave boundary, chart crossing within the eye box, target-plane failure and a sample-complete-but-uncovered point. Prove a solid public synthetic patch accepts, and each intended-failure mutation rejects. Report exact-real outcomes, uncertainty-stage outcomes, runtime cuts and ms separately.