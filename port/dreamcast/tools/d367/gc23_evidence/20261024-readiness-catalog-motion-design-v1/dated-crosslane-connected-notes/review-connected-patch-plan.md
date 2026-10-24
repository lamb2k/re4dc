# Independent connected-patch plan review — 2026-10-24

Reviewer: `/root/pvs23_assets_sol61`. **Exact-real theorem CLEAR under the refined stated conditions. No counterexample found.** This is a plan/theorem assessment, not implementation review, asset qualification, table/runtime admission or speed acceptance. Scope was read-only mathematics plus bounded public synthetic controls; no SDK, guest, source/data changes or wider asset search.

Both root documents were read and their SHA256 identities verified:

| Document | SHA256 |
|---|---|
| ROOT-CONNECTED-PATCH-PLAN-20261024.md | e06087c1b0c877242ef2836f1e4bd937be93061aa0c6f0a91e96f7ffd6720f18 |
| ROOT-CONNECTED-PATCH-REFINEMENT-20261024.md | e4ec95ee427870baa3eef8b62435397201175bf4b5cac2cac9234eb13fb97042 |

The explicit target-positive-chart and exact face/edge-incidence refinements matter and are included in this verdict.

## Finite coverage proof

Fix any eye E in the admitted box. Let d be the SAME fixed nonzero chart direction for the complete candidate domain, with `q(X)=d·(X-E)>0` for every actual source vertex X and every target point T. The chart point is `p(X)=(X-E)/q(X)` on the affine plane `d·p=1`.

Each actual physical triangle projects exactly to the CLOSED chart triangle of its three vertices. Physical barycentric coefficients lambda_i become `mu_i=lambda_i*q_i/sum(lambda_j*q_j)`; conversely `lambda_i=(mu_i/q_i)/sum(mu_j/q_j)`. Positive denominators make both transformations nonnegative. Thus we may use the finite oriented affine chart triangles to prove their actual projection coverage, without fitting or inventing a physical surface.

Authenticate a finite oriented indexed triangulated disk with one boundary cycle. Every interior edge occurs twice with opposite directed use, so the sum of oriented projected triangle boundary chains is exactly the outer projected boundary chain. The physical shared endpoints project to the SAME endpoints; the same edge has the same chart segment. There is no seam weld or unmatched edge.

Choose the chart-plane orientation consistently. At any chart point P not lying on any projected triangle edge, winding-number additivity gives:

`sum_face winding(projected oriented triangle boundary, P) = winding(outer boundary, P)`.

The simple strictly convex outer boundary has winding one in its interior (or minus one after uniformly reversing the chosen orientation). Every projected face is strictly nondegenerate with that same orientation, so each contributes either zero or one after the uniform sign normalization. Consequently every such interior P lies in exactly one projected triangle interior. A positive-overlap region or uncovered open hole would contradict this integer identity. No assumption that the physical patch is planar is needed.

The finite union of CLOSED chart triangle images is closed. Every point inside the outer boundary that lies on a projected internal edge or vertex is a limit of nearby interior points avoiding the finitely many projected edges. Those nearby points are covered; closedness therefore covers the limiting point too. This includes a target ray on an internal seam. Strict outer-boundary target inequalities keep it away from an unqualified outer edge.

The target direction is therefore in some actual triangle's projection. For that triangle put `sE=N·(E-A)` and `sT=N·(T-A)`. Strict opposite plane sides give `t=sE/(sE-sT)` in (0,1). Its unique actual triangle-plane crossing is on the segment before T and in the actual physical triangle. Requiring separation for EVERY source face is sufficient even though conservative; it must not be replaced with a fitted common plane or selected face.

This finite-chain argument makes the proposed degree-one claim explicit. The disk conditions are stronger than the minimal chain identity, but appropriate safeguards for a bounded implementation. Interior vertices need not separately be assumed inside the outer projected polygon: the same nonnegative winding identity prevents an open positively oriented overhang outside it.

## Exact full-box checks and topology obligations

For fixed source geometry, face orientation/eye-plane signs are affine in E. Boundary-edge/other-boundary-vertex determinants are affine in E. The target-edge determinant `H_AB(E,T)=-det(A-E,B-E,T-E)` is separately affine in E and T. Its 8-by-8 eye/target corner values bound the complete box product by tensor interpolation. Fixed-d chart denominators are affine; source-face target-plane signs are affine in T. Uniform strict signs at the required corners suffice for the full boxes. Never select a different chart/sign for different corners or triangles.

For uncertain geometry, exact outward interval evaluation must enclose EVERY predicate over shared correlated vertex variables, followed by the same fixed-source corner argument. The actual common endpoint remains one physical variable for all incident triangles. Fixed nominal chart directions are acceptable if their strict inequalities enclose the uncertainty; an independently varying chart is not covered by this proof. Nonfinite/degenerate/contact/ambiguous bounds reject. Requested error boxes alone do not establish renderer error.

A validator must enforce, rather than infer from Euler characteristic alone: three distinct valid indices per face; no duplicate unoriented faces; connected face adjacency; exactly one incident face on boundary edges and two on interior edges; opposite interior directed incidences; one simple boundary cycle; each interior vertex link a connected simple cycle and each boundary link a connected simple path; orientability and Euler characteristic one. These establish a disk and reject pinches, nonmanifold edges and holes. Coordinate equality of separate indices is not a shared-source identity.

A missing boundary triangle may leave a smaller legitimate disk that still occludes a different target. Therefore construct negative controls with an actual uncovered target/hole or violated invariant; do not require arbitrary face deletion to reject irrespective of the remaining valid geometry. A genuinely warped physical patch can remain valid; reject angular orientation reversals/folds, not noncoplanarity itself.

## Independent bounded controls

Ran exact Fraction controls in one host process with a 268,435,456-byte address-space cap, using public synthetic geometry only. The positive patch has six boundary vertices `(−3,−2),(0,−4),(3,−2),(3,2),(0,4),(−3,2)` with alternating z=0/1, center `(0,0,1/3)` and six actual center-fan triangles. Eye box is `[-.1,.1] x [-.1,.1] x [20,21]`; target box is `[-.1,.1] x [-.1,.1] x [-21,-20]`; d=(0,0,−1).

Its topology has Euler characteristic1, one boundary component and maximum edge incidence2. Across all prescribed corners, source-plane eye minimum is 3533/15, target-plane maximum −3653/15, boundary-convexity minimum 2151/10, outer target-edge minimum 460 and chart denominator minimum19. All signs are strict. This is a real warped six-face positive, not a flattened polygon.

The negative control is a planar six-sector annulus made from twelve actual positive-oriented triangles, between the same outer polygon and its quarter-scale inner polygon. All outer target inequalities accept the central target direction, and a sample at each of its twelve actual face centroids is covered. Nevertheless the center has zero actual triangle winding/coverage while the outer cycle has winding one. Its Euler characteristic is0 and it has TWO boundary components, correctly failing the disk requirements. This demonstrates the danger of dropping the topology check or treating finite blocked samples as a coverage certificate. It is a counterexample to that weaker test, not to the refined plan.

These controls corroborate predicates and exhibit a failure mode; the continuous proof above supplies soundness. They are not private geometry or runtime validation.

## Asset/runtime boundaries

Discovery target299/placement209/cluster272 versus source165/part230/cluster234/selected-LOD0/meshlet951 remains **NO_CERTIFICATE**. Its sampled27/27 and selected-LOD connected-six-face roster do not establish this theorem's complete predicates or any actual accepted source roster. No original private coordinates were copied or qualified by this review.

For an eventual exact candidate, authenticate all target LOD bounds and every required source LOD configuration. Source clusters select LOD independently: equal global LOD numbers are not a proof. Either preserve authenticated invariant faces or prove/admit each permitted actual configuration; missing faces in another selectable LOD cannot be filled. Preserve exact source material, alpha/conditional/pose ownership, whole-cluster own-instance exclusions, source namespace and original parity/cull semantics.

Every required face must actually be submitted as live immutable ordinary opaque depth-writing geometry before cutting the target. Preserve the accepted-source-prefix contract, pin dependencies visible, include ALL required source placements/parts/clusters and require target order after the last accepted dependency. A selected-LOD envelope or prefix index alone is not successful emission. Respect current receipt and panel-cap limitations; this theorem adds no runtime representation.

Positive mathematical chart depth is not camera near/far clipping. Actual source/target/eye transform error, selector preimage, common cache/kernel/transform/clip generation, source cull side, raster seam/sample/depth coverage and frame/scene/material commit receipts remain separate requirements. All shared indices must denote identical actual projected endpoints, not independently rounded coordinate copies. No exact-real positive may directly clear a runtime bit.

Keep nominal proofs, requested/established uncertainty-stage proofs, actual renderer cuts and ms separate. Existing zero-result cohorts stay zero; a future positive would justify investigating remaining guards, not claim performance or appearance acceptance. This review does not authorize source expansion beyond root's at-most-three candidate plan, tables, assets or runtime changes.
