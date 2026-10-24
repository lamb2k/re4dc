# Triangle-shadow feasibility plan — for math review before implementation

Freeze: source 5f60ff133 and private I001-fb254-lod-surface-r6 remain unchanged.
Use its exact fb254 integration/profile/input pins and actual hut/turn/walk camera
cells. No closed-room assumption is needed. This phase emits a private offline
report only: no PVS table, certificate/data option, shared source, SDK or guest.

## Proposed sufficient geometric predicate

For oriented nondegenerate source triangle A,B,C, put n=(B-A) cross (C-A).
Choose one orientation for the entire cell. Require, strictly for every eye E
in the expanded camera-cell box and every target point T in the expanded
all-LOD target box:

- dE=n dot (E-A) > 0 and dT=n dot (T-A) < 0.
- hAB(E,T)=((E-A) cross (B-A)) dot (T-A) > 0, and the same
  predicate for the cyclic edges BC and CA.

Reason: the plane crossing X=E+t(T-E), t=dE/(dE-dT), has 0<t<1.
For edge AB, hAB(E,X)=t*hAB(E,T) and hAB(E,C)=dE. Thus X is
strictly on the interior side of every triangle edge. Every complete eye-target
segment crosses the actual triangle interior. A reversed orientation is allowed
only uniformly and only where actual two-sided/cull semantics are authenticated;
there is no per-corner sign switch or guessed one-sided winding.

For fixed source vertices, dE/dT are affine and each h is bi-affine in E and T
(separately affine in every independent eye/target coordinate). Recursive linear
interpolation therefore expresses every interior value as a convex combination
of the 8 eye corners times 8 target corners. The 64 strict edge tests plus strict
plane-side corner tests cover the continuous boxes, not sampled rays.

Uncertain source positions are separate operands. Use outward enclosing interval
arithmetic (or exact rational interval arithmetic) for the full determinants;
nominal corner values plus an arbitrary epsilon are insufficient. The equivalent
four-point determinant is multi-affine in its independent point coordinates,
but a naive expanded expression can repeat variables: interval dependence may
lose yield, never tighten the enclosure. Degeneracy, sign ambiguity, singular
view/affine, nonfinite values, touching a plane/edge or unbounded error fails open.
An exact-rational nominal oracle and adversarial interior-point controls will
check the interval implementation; finite samples are controls, never the proof.

## Source and renderer admission boundary

1. Reuse exact per-cluster all-selectable-LOD invariant facets, without the old
   heuristic that triangles must be large/vertical. Classify source IDs using
   the authenticated current unique-ID-below-250 rule; exclude all conditional,
   appended, animated, sky, unknown/mixed or unproved ownership/placement cases.
2. Require ordinary opaque pass, no vertex alpha, and actual immutable RGB565
   texture/flags/descriptor/key qualification. Preserve real top-drop/binary/
   alpha vetoes and exact WORLD_RECT21 adaptation. A label, file key or pass
   number is insufficient. Any unavailable/unproved material is excluded.
3. Target bounds enclose every source LOD and the proven transform uncertainty.
   Keep conditional/unproved targets out of the strict compatible cohort. Keep
   the existing source-placement prefix, at most 16 dependency panels, and
   retain every cell or target unsupported by the existing PVS namespace.
4. Plane clearance is not a near-plane proof. Near/far/viewport clipping, screen
   orientation/area, partial strip picks, texture/header state, source pose and
   successful opaque depth-writing emission still require the unchanged current
   numeric, panel_sent, opacity, generation and committed-prefix receipts.
   The single-triangle duplicate-index representation must be reviewed against
   panel_sent; do not assume its old research descriptor is already admitted.
5. The current numeric guard is explicitly a bounded private-QA engineering
   envelope, not universal SH-4 verification. Reuse its 32 mm allowance only
   after binding its exact gamma128/FSRRA/eye-selector/viewport assumptions and
   showing how source, target and eye intervals enclose that error. Keep the
   existing clearance/raster conditions; do not lower them to manufacture cuts.
   Unresolved FP, raster coverage or clip obligations yield no renderer-qualified
   hidden count. Nominal mathematical feasibility is labelled separately.
6. All-LOD stable geometry can be researched, but the current source receipt
   restricts panels to one-level clusters. Report that compatible subset
   separately; no multi-LOD receipt relaxation or new runtime API is proposed.

## Report and GO

Identify actual eligible source triangle IDs, material/owner/placement evidence,
cell-target proofs, all-LOD bounds and exact source/helper hashes. Show successive
nominal, uncertainty-safe and existing-guard-compatible counts. Use captured
cameras only to price selected work and potential receipt liveness; unsampled
cells, failed receipts and unsupported states draw all. Keep hut and arrival-turn
fixtures explicitly identified; historical e9bf7 camera weights are not current
runtime counters or current exact-55-second guest qualification.

Price proven compatible removed transformed corners/setup only with a frozen,
source-matched exclusive current SH-4 model and account for proof/guard cost.
Existing fb254 objects/disassembly may be read offline; no build is allocated.
If no suitable model or guard-cost bound exists, report MODELLED ms unavailable
rather than borrow old r10d timing. The >=1 ms MODELLED GO stays unestablished
until a conservative net estimate supports it. No runtime cuts or console gain
are claimed from a host report. Main reviews math and yield before any later
runtime/data option, target timing, pixel gate or private pair.
