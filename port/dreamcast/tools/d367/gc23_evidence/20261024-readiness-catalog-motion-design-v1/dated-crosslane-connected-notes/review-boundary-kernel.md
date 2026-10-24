# Independent boundary-kernel refinement review — 2026-10-24

Reviewer: `/root/pvs23_assets_sol61`. **Exact-real refinement CLEAR.** Under the retained oriented disk/incidence/shared-endpoint, common positive source-and-target chart, uniformly oriented nondegenerate faces and source-plane separation conditions, strict target-left-of-EVERY-directed-boundary-edge is a sufficient coverage condition. Strict boundary convexity is unnecessary. This is a mathematical plan review only; the existing strict criterion remains unchanged until root authorizes its replacement. No author source, asset, table, SDK, guest or runtime change occurred.

This supplements the root connected-patch plan SHA256 `e06087c1b0c877242ef2836f1e4bd937be93061aa0c6f0a91e96f7ffd6720f18`, refinement SHA256 `e4ec95ee427870baa3eef8b62435397201175bf4b5cac2cac9234eb13fb97042`, and `review-connected-patch-plan.md`. It evaluates root's subsequent proposed boundary-kernel criterion, not an existing implementation.

## Why positive winding is enough

Fix any admitted eye E and target T. Use the same fixed positive chart as in the earlier proof. Let P be the target chart point and let `r_i=p(V_i)-P` for consecutive actual boundary vertices. Normalize ONE global orientation sign consistently with every face and directed boundary edge.

The strict boundary predicate is equivalent, up to a positive denominator factor and that fixed orientation convention, to `cross2(r_i,r_(i+1))>0`. It implies neither endpoint equals P and no boundary segment passes through P. The unique principal counterclockwise angular increment from r_i to r_(i+1) is strictly between zero and pi. The boundary is a closed finite cycle, so the sum of these increments is `2*pi*w` for an integer winding number w. Every increment is positive; hence **w>=1**. It need not be one. This argument does not require a convex boundary or a geometrically injective projection.

Actual interior directed edges cancel exactly in the sum of projected triangle boundary chains. Therefore, for a chart point away from projected triangle edges, the sum of face winding numbers equals the boundary winding w. Every face has the same strict orientation and is nondegenerate, so after the fixed sign normalization each face contributes zero or one. Their sum is at least one: some actual projected triangle contains P.

At points on internal projected edges or vertices, use the finite union of CLOSED projected triangles. Strict boundary-left inequalities define an open neighborhood of P which avoids the boundary. Every nearby point avoiding the finitely many triangle edges still has all strict boundary signs and therefore positive winding/coverage. Closedness supplies coverage of P itself. This is the same actual-seam argument as before, not a fabricated fill.

Positive common chart denominators ensure that each physical source triangle projects exactly onto its closed chart triangle via positive barycentric reweighting. Opposite eye/target sides of EVERY actual face plane then place the intersection in the physical triangle strictly before T, as in the prior theorem. Noncoplanar faces remain separate real faces.

No counterexample was found under these conditions. A projected self-overlap or multiply covered region is not excluded by this weaker theorem; coverage only needs winding at least one. Do not retain the earlier degree-ONE/injectivity claim after removing convexity. The boundary's simple indexed cycle and valid disk topology still remain authenticated source safeguards.

## Full-domain and source conditions remain

For fixed actual source vertices, each edge shadow determinant `H_AB(E,T)=-det(A-E,B-E,T-E)` is separately affine in E and T. A single uniform strict sign at every eye-box corner times target-box corner bounds the complete Cartesian product. No per-edge, per-face or per-corner sign flip is allowed. The proof is pointwise for every E,T; no angular sampling or numerical angle evaluation is required in a certifier.

Keep explicit positive source AND target chart tests, all-face orientation, both source-plane signs for each face, exact directed incidences and one actual shared physical variable per source endpoint. Exact intervals must enclose every predicate for requested/established geometry uncertainty; shared indices cannot become independent displaced seams. Removing convexity removes only the boundary-other-vertex tests, not these obligations or topology validation.

A collinear subdivision of a boundary edge is permitted: relative to a target strictly on its interior side, each nonzero subedge still has a positive angular increment. A zero projected subedge, target on a boundary line or zero/ambiguous interval sign still rejects. The intersection of all directed target halfspaces is a conservative kernel; it may be much smaller than the actual patch coverage or empty. Failure is unknown, not proof that no target ray is occluded.

## Independent exact controls

Ran public Fraction arithmetic controls in one host process with a 268,435,456-byte address-space cap. Eye box `[-.1,.1] x [-.1,.1] x [10,11]`, target box `[-1,1] x [-1,1] x [-11,-10]`, source z=0 and fixed d=(0,0,-1). Each polygon is an actual center-fan triangulated disk with uniformly positive faces, not an inferred hull.

- A square with all four edge midpoints retained has eight real fan triangles. All face-plane signs and complete eye/target boundary predicates are strict: eye-plane minimum160, target-plane maximum−160, kernel minimum276. The old strict boundary-other-vertex minimum is exactly0 because adjacent subedges are collinear. The weaker condition correctly admits its continuous actual coverage.
- A genuinely concave boundary `(-4,-4),(4,-4),(4,4),(0,2),(-4,4)` has five real fan triangles. Eye-plane minimum80, target-plane maximum−80 and kernel minimum94 are strict over all required corners. The old convexity minimum is−176, so convexity rejects a sound kernel-covered target box.
- For the same concave patch, eye `(0,0,10)` and target `(6,5,-10)` have an actual hit `(3,5/2,0)` strictly inside the source fan face `(0,0),(4,-4),(4,4)`, with exact barycentric weights `1/4,1/16,11/16`. A directed boundary condition rejects this target because it lies outside the conservative kernel. This is an intended false negative, demonstrating that the weaker sufficient test still does not characterize all coverage.

The earlier annulus control still explains why topology cannot simply be replaced with covered samples. These controls corroborate the new inequalities; the winding/chain argument supplies the continuous proof. No private source geometry was copied or qualified.

## Admission boundary

Retain all source/target LOD cases, immutable opaque material/alpha/conditional/pose rules, target own-instance exclusions, exact source order and actual accepted-prefix receipts for EVERY required face. Positive discovery samples or selected-LOD source envelopes remain NO_CERTIFICATE. More than one source face/patch is not successfully emitted merely because it is geometrically present or ordered early.

Actual transform/true-eye/selector error, common projected endpoint/cache/kernel/clip generation, correct emitted cull side, near/far/clipping, raster seam/sample/depth and successful frame/scene/material commits remain separate. The refinement approves no table representation, runtime bit, search expansion or ms/appearance claim. A prototype should preserve both old and new predicate outcomes and include the collinear, concave, outside-kernel, boundary-contact, topology, uncertainty and actual-receipt controls before any later admission review.
