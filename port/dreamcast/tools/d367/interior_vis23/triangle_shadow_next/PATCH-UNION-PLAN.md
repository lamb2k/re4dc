# Next bounded plan: actual shared-edge triangle unions

This is a proposal for main and independent math review before implementation.
The frozen 512-face unit and the same 20 closest pairs remain unchanged. No
runtime, data option, converter, SDK or guest work is requested by this plan.

The authentic smaller-domain result is zero: 129 retained matrix cameras,
178 applicable fixed-pair cases at 500 mm, then the same 178 at local 250 mm.
Every exact nominal test refuses edge coverage. No selected host corners are
cut in hut, arrival-turn or walk. Full old Y bands remain. Requested-error and
renderer admission are zero; MODELLED ms is unavailable and the 1 ms GO is open.

## Why an exact coplanar-only patch cannot be assumed

Read-only inspection of the two best-ranked seed faces (17 and 18 in the frozen
512 list) shows that each has only its own same-winding exact coplanar triangle
inside its source cluster. Each nevertheless has one exact edge-adjacent,
same-winding triangle in its own meshlet 491. That companion is NOT coplanar
under the exact serialized grid determinant. The two seeds are different
opposite surfaces: they share no grid positions with each other. Joining the
seeds, flattening their companions or applying a tolerance would invent a
surface. No such operation is proposed.

The frozen fcf49c1d helper already contains `quad_hides`: it authenticates an
actual shared-edge pair, keeps both real triangle planes, and tests its convex
projected boundary. It does not require a planar quad. The next bounded unit
should review and reuse that geometric idea with the new exact rational oracle,
not repeat a broader individual-face search. It must preserve the two actual
source triangles and their shared coordinates, winding, material and LOD.

## Proposed sufficient test

1. For each of the same closest 20 seeds, inspect only exact edge-adjacent
   triangles in its own unconditional ordinary opaque source cluster. Start
   with a companion in the same whole meshlet and current one-LOD cohort. Both
   triangles must be in the exact all-selectable-LOD stable set. Bind each
   actual parity-correct source index triple; reject duplicate or ambiguous
   membership. No seam weld or position epsilon is allowed.
2. Authenticate exactly four position identities and exactly one shared edge
   traversed in opposite directions. The four remaining directed edges must
   form one simple cycle. Any missing edge, overlap ambiguity, extra vertex or
   ownership/material/pose mismatch fails open. Coplanar pairs can use the same
   test; noncoplanar pairs retain both separate physical planes.
3. Prove both complete source triangles strictly separate the full eye box
   from the full all-LOD target box with one consistent orientation. Retain the
   requested clearance and perturbation experiments separately from nominal
   geometry. A source triangle that fails this plane test cannot be patched
   over by its neighbor.
4. Require a common open projection hemisphere. Choose an exact fixed chart
   direction from a source plane (and reject it if unsupported); prove
   `d dot (V-E) > 0` for all four real source vertices and every eye, and
   `d dot (T-E) > 0` for every target and eye. This ensures finite projective
   coordinates and prevents a wrapping angular polygon from masquerading as
   an ordinary convex quad.
5. For every directed outer edge AB, use the reviewed determinant H_AB(E,T).
   All full eye x target corner pairs must have the common strict interior
   sign. For each other boundary vertex V, H_AB(E,V) must have that same strict
   sign for all eye corners. Authenticate that the two third vertices are on
   opposite sides of the shared-edge ray plane throughout the eye box.
6. In the common projective chart the authenticated boundary is a strict
   convex quadrilateral, and the actual two triangles partition it along the
   real shared diagonal. Thus a target ray inside the boundary belongs to one
   actual triangle; both-plane separation places that real intersection
   strictly before the target. The internal diagonal is covered by the actual
   shared edge, not by a fabricated fill. General multi-triangle hulls, holes,
   disconnected components and arbitrary convex-hull filling are out of scope.

For fixed source points each outer determinant is separately affine in eye and
target, so the reviewed full product-corner interpolation remains sufficient.
Plane/chart predicates are affine in the relevant box points. Uncertain source
vertices need exact outward interval bounds over each predicate. Shared source
position identities remain the SAME variables in both triangles; independent
uncertainty must not silently disconnect the common edge. This is an IDEAL
coverage theorem, not a raster seam, depth quantization or SH4 guarantee.

## Controls, scope and result to return

Use a synthetic square split across its diagonal: neither individual triangle
covers the whole target-box projection, while their actual union does. Repeat
with an actual nonplanar fourth vertex. Negative controls include missing or
reversed shared edge, mismatched owner/material/LOD, concave/folded boundary,
chart contact, plane crossing, target-edge contact, false convex hull across a
hole, independent displaced seam vertices, uncertainty-induced ambiguity and
missing/clipped/stale real receipts. Keep actual source matcher/table controls;
the existing Panel already stores two actual oriented source triples and its
one-LOD and whole-meshlet restrictions stay unchanged.

Evaluate only the same closest source/target pair identities and authenticated
camera cohort at the existing full cell and represented local 500/250 mm
boxes. Adding each seed's exact adjacent companion is the sole proposed new
source coverage; no wider source sampling or target partition is implied.
Return nominal and requested-uncertainty proofs, one-source-prefix compatible
host corner weights per camera, failure categories and exact local data extent.
Prefer a small local window with draw-all outside; the full-room 500 mm grid's
70 KB is not an approved heap4 allocation.

Do not emit or admit a table until actual numeric, source, cull, near/far,
material/header, raster edge/sample/depth and committed source-prefix receipts
close. No renderer cut or >=1 ms claim follows from the geometric union. If the
bounded actual pair union remains zero, report it and re-plan; do not turn this
unit into repeated source-cap expansion or a watertight-room requirement.

Independent refinement: the first source cohort must use the SAME actual shared meshlet corner indices and projected cache slots in both triangles, with identical kernel, transform and unchanged clipping construction. Coordinate-equal copies do not prove a renderer seam. The host interval dictionary uses one physical endpoint variable for each such index, reused across both triangles. The exact-real theorem is independently CLEAR in review-patch-union-plan.md (f26ed9355bae23be24f0445580191b06a73106e26810a5587f2903c5cb06565d); renderer/raster admission remains separate.
