# Canonical four-child exact-real proof wrapper

New tools only, based on production integrationfb254e82ee6f9a3d9e34d53d1d442348a46b9cf2. No runtime, rendered microgeometry, schema, source asset, recipe, SDK, guest, ray or ledger change. Private shadow predicates are HELD until independent review and a separate root grant.

Design source: independent review `C:/Game Dev/Emulators/codex-lanes/interior-discovery24/review-partition-design-v1/REVIEW.md`, SHAedc710989a5f6fd0cff7485cecb7f2ddfbd2e3d9704221fd2a2b8ff962aae4a0. It approves the sufficient exact-real theorem only. The fixed-face backend is unchanged generic28c739468ae7d2d2d3c09f81330015e7769dc824, exact_shadow.py SHA9c0f85d588be2020a1506325da078e27a99c23b81f783ff3db268f6082a64f41.

`partition.py` authenticates supplied original occurrences against a CALLER-AUTHENTICATED immutable inventory digest. This digest does not itself prove game-data provenance: a private importer must independently derive all original occurrences, oriented strip ordinals/indices, physical placement/field/part/cluster/effectiveLOD/let, exact affine/dequantization operand pins, and package/policy/ownership identities. The helper cannot turn a self-signed subset into an actual complete asset certificate. The original manifest remains external/private. Every parent occurrence has a separate ordered ordinal even when two parents have identical coordinates.

For each original(A,B,C), exact rational midpoints ab,bc,ac give ONLY these four ordered children:

1. (A,ab,ac)
2. (ab,B,bc)
3. (ac,bc,C)
4. (ab,bc,ac)

One correlated construction uses the same original endpoints. Child IDs, parent IDs, canonical barycentric vectors, exact coordinates and order must all match. Nothing is sorted, welded, pruned, rounded or emitted as new geometry. The wrapper conservatively REFUSES a degenerate parent in this unit, as explicitly directed; it never omits it or silently deduplicates its children. The design review's broader affine-image statement for degenerate parents is not implemented here.

`cover_partition` first validates the complete inventory and partition, then takes exactly one fixed actual face for EACH complete child over the SAME whole eye cell. It makes one global call to generic cover_assigned across all children of all parents. Every child and parent must succeed. Missing assignments, last-child failure or incomplete backend output leaves the whole let UNKNOWN. Sources cannot switch per vertex, point or eye.

Each FixedFace binds a FULL PhysicalPanel: production placement/field/part/cluster/let/corners[6], both distinct actual adjacent oriented faces, and external source provenance. Shared corner indices must have identical exact positions. ID-to-full-record and full-record-to-ID bijections are checked, with no coordinate-based alias merge. The union is at most16 FULL physical Panel dependencies across the ENTIRE let, ANDed together, never a per-parent or per-child limit. Source membership, original semantics, material/LOD/effective0 capability, frame/generation, successful prefix emission, near/clip/cull/raster and current receipt liveness remain EXTERNAL and unqualified. A PhysicalPanel structure is not an actual submission receipt.

Bounds are strict int/Fraction only, deep immutable tuples, <=256 input scalar bits, <=256 parents, <=1024 children, and <=73728 generic edge tests per fixed assignment. Caller limits may reduce these bounds. Midpoint bit growth refuses instead of rounding. The serialized input/accounting envelope is at most4MiB; it is NOT a measurement or upper bound on Python RSS. Public controls run under an external256MiB address cap. Memory allocation/budget refusal yields UNKNOWN. Actual process/memory/wall budgets are a separate runner obligation.

`conditional_radius` is algebra only: with an explicitly caller-VALID endpoint enclosure, nonnegative barycentric weights summing to1 lift endpoint component radii by the weighted sum. Equal endpoint errors retain the full radius; correlated seams remain identical. This cannot establish actual SH4 endpoint bounds, chosen32mm errors, source/eye uncertainty, clipping/raster or a numeric certificate. Without valid endpoint hypotheses it returns ENDPOINT_BOUND_UNQUALIFIED. There are no runtime midpoint operations or claimed numeric acceptance.

Sixteen public host groups pass. The reviewed strict example uses full eye box[-1/100,1/100]^3 and four different source planes q=(9/10,1,11/10,19/20). Every old single-source whole-parent choice fails, while all four assigned children pass. Instrumented generic backend counts exactly288 edge signs and44 source-plane evaluations for that positive. Other controls cover quarter normals, canonical barycentrics, internal edge cancellation/exterior subdivision, missing/duplicate/reversed/wrong-parent/wrong-midpoint children, omitted/duplicate/wrong-index/wrong-affine parents, repeated original coordinate occurrences, last-child failure,16 versus17 global Panels, coordinate aliases, complete actual Panel corners, incomplete backend result, fixed-source typing, floats/mutability, work/record/bits/serialized-memory/allocation refusals and conditional perturbation/seam identity. Controls corroborate the reviewed algebra; they are not scene or runtime evidence.

Run public controls from WSL:

```sh
TREE=/root/work/lanes/triangle-partition24
D=$TREE/port/dreamcast/tools/d367/triangle_partition24
(ulimit -v 262144; timeout 120s env PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s "$D" -v)
```

Private preparation, if provided by a successor, must first rederive the complete original inventory from frozen actual bytes, keep every canonical child and full provenance private, preserve the same finite source roster and authentic eye domains, and publish fourfold candidate/final reservations before any private predicates. No discovery, new tiny domains or source-pool widening is implied.
