# Exact perspective union of a full physical Panel

This generic host helper tests one fixed union of TWO authenticated actual triangles over one whole target triangle and one complete eye box. It returns an exact-real opportunity or `Unknown`, never a runtime visibility decision. It uses exact `int`/`Fraction` arithmetic; no interval front end, private input reader, assets, renderer, runtime hook, PVS/schema, converter, recipe, SDK or guest path is added. The canonical target partition tools and runner are independent and unchanged.

Noncoplanarity is permitted. The helper never substitutes a plane for the physical source triangles, welds their indices, flattens them, or fills a projected hull without proving the exact two-triangle union. All public fixtures are synthetic rational geometry.

## Predicate

Authenticate a full `PhysicalPanel`: exactly two nondegenerate actual oriented triangles; three distinct corner IDs each; exactly two shared IDs and four in their union; identical realized coordinates for every shared ID; one oppositely directed shared edge; and one directed outer four-cycle. Canonicalization cyclically rotates that boundary to its smallest actual ID; it does not reverse winding, change the diagonal or choose new faces. A source binding must refer to the unchanged complete actual physical source. An index alone does not authenticate the renderer's shared realized-position contract.

An `Assignment` chooses ONE fixed nonzero rational linear functional L and ONE sign tau (+1 or -1) for the whole eye/target domain. With all eight corners of the explicit `EyeBox`, all four source vertices and all three original target vertices, require:

    min L(E) > max L(S),   min L(S) > max L(T).

These strict gaps put a common mathematical projection plane L=c between all eyes and all source vertices, and every actual source point before every target point along a valid intersecting ray. The plane is a proof chart, never source geometry.

For D(e;a,b,c)=det(a-e,b-e,c-e), require tau*D positive at every eye corner for the four consecutive source triples. Also require tau*D(e;Si,S(i+1),t)>0 at every Cartesian eye-corner/target-vertex pair for all four outer edges. The code evaluates all 32+96=128 volumes per whole target triangle, without matched-pair, one-eye or source-switching shortcuts. Volumes are checked with exact rational operations and a bound on every intermediate. Non-strict contact/uncertainty refuses; an internal diagonal contact is included in the ideal closed union.

D is affine in e and separately affine in t, so the corner-product signs extend to the entire box times the entire triangle. The four consecutive signs make the projected four-cycle strictly convex: for every boundary edge both other vertices lie strictly on its inward side. Positive perspective depth denominators map each actual triangle bijectively onto its projected triangle by positive barycentric reweighting. Their exact common indexed diagonal partitions the projected quad into precisely those two closed triangles. The outer-cone signs place every target-ray projection inside this complete union. Inverting one projected triangle gives an intersection on an ACTUAL source triangle; the L gaps put it strictly between eye and target. No physical source coplanarity is assumed.

This is a sufficient test. A failure is `Unknown`, not evidence of visibility or exhaustive failure. Strong global L gaps can conservatively reject a genuinely occluding folded source.

## API and provenance boundary

`cover_triangle(eyes, parent, assignment, limits)` tests one complete original triangle. It cannot certify that the caller supplied every triangle of a let.

`cover_assigned(inventory, eyes, assignments, limits)` requires every original occurrence in order (ordinal 0..N-1, one unchanged physical target tuple), the exact prebound inventory digest and exactly one fixed whole-Panel assignment per occurrence. It returns only after ALL originals succeed. A later failure discards the whole result; no subset proof is returned. It checks global Panel-ID/record/geometry/source-binding bijections and unions at most 16 FULL physical Panel dependencies across the entire original inventory. Every dependency must be ANDed by any future admission code; both actual member faces are required.

The input shapes mirror the existing generic partition interface without importing or modifying it:

- `Parent.occurrence`: `(placement, field, part, cluster, effectiveLOD, let, original_ordinal)`; `indices` preserves the original oriented three local corner IDs; affine SHA and exact vertices remain unchanged.
- `PhysicalPanel.record`: the established 11 integers `(placement, field, part, cluster, let, a,b,c,d,e,f)`, with TWO actual ordered triangle index triples. Its source binding must externally authenticate actual source/effective LOD, affine operands, geometry, package and membership. This helper does not silently invent another source namespace.
- `EyeBox`: explicit finite rational `low` and `high` plus caller-bound domain identity. All eight corners are evaluated, including duplicates for zero-width axes. The box denotes its entire closed convex volume.
- `inventory_digest`: binds an EXTERNALLY authenticated complete original inventory. Recomputing a digest of a chosen subset does not authenticate assets. A future reader must independently reconstruct and match the frozen complete source inventory/indices/affine operands; these SHA strings are caller assertions, not game/runtime provenance evidence.

All nested geometry must be immutable tuples of exact `int`/`Fraction` coordinates. Boolean, floating, mutable, malformed, missing, nonfinite/unbounded or degenerate input refuses. A degenerate original target is never pruned. `bool()` on `Unknown` or either opportunity result raises `TypeError`. Every returned opportunity explicitly has `runtime_admitted=False`.

## Public example

```python
from fractions import Fraction as Q
import source_quad as q
s = ((-1,-1,1), (1,-1,1), (1,1,1), (-1,1,Q(3,2)))
panel = q.PhysicalPanel(1, (1,2,3,4,5,0,1,2,0,2,3), 'b'*64,
                        ((s[0],s[1],s[2]), (s[0],s[2],s[3])))
parent = q.Parent((99,2,3,4,0,5,0), (0,1,2), 'c'*64,
                  ((Q(-1,2),Q(1,2),3), (Q(1,2),Q(-1,2),3),
                   (Q(1,2),Q(1,2),3)))
eyes = q.EyeBox((Q(-1,100),)*3, (Q(1,100),)*3, 'a'*64)
a = q.Assignment(panel, (0,0,-1), 1)
answer = q.cover_triangle(eyes, parent, a)
assert type(answer) is q.TriangleOpportunity
```

This is a strict noncoplanar volume-eye positive. Both old fixed triangle-face choices fail for different target vertices; the source's actual shared diagonal is included. The synthetic binding strings above are placeholders, not source authentication.

## Limits and public controls

Defaults and hard maxima: 256 original target occurrences, 256 numerator/denominator bits for every input AND arithmetic intermediate, 32,768 volume tests, 1 MiB serialized-input accounting, 16 complete Panel dependencies. Callers can lower the first four limits, never raise them. A whole-inventory call reserves `128*N` volume capacity BEFORE the first coverage volume. Failed early coverage may consume less, but no partial positive or unbounded retry/search exists. The helper has no candidate search. Its maximum successful volume count is deterministic.

The byte envelope bounds the validated serialized inputs, not Python RSS. Exact rational operations may transiently allocate a bounded intermediate before its bit check. Public entries catch `MemoryError` and `OverflowError` as `Unknown('MEMORY_ALLOCATION')`; unsupported/invalid/bit/work/accounting failures also return `Unknown`. Process-level failure with no complete result is not a positive. An external actual-data caller must separately enforce memory/wall/output caps; no generic result grants itself resources or execution authority.

Run only the finite public controls under the declared process cap:

```sh
set -euo pipefail
D=/root/work/lanes/source-quad24/port/dreamcast/tools/d367/source_quad24
ulimit -v 262144
exec timeout 120s env PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s "$D" -v
```

Controls include the noncoplanar and coplanar positives, all 48 signed axis permutations/mirrors, rational scale/translation, concavity, bow tie, source/target depth failure despite all cone signs passing, strict depth/outer-edge equality, internal diagonal inclusion, one omitted edge, matched-pair/one-eye false positives, broken actual seam, physical/index/coordinate aliases, invalid/degenerate/missing inputs, full original inventory/last-original failure, global 16/17 Panel composition, independent work/bit/byte caps and injected allocation/overflow at public entries including the final original. No private scene is read.

## Held obligations and next adapter

Exact nominal math does NOT authenticate source opacity, actual selected geometry/effective0 capability, source cull, successful current opaque commits for BOTH faces, prefix order, near/clip/depth/raster seam coverage, room/generation/lifetime or numeric error bounds. No measured gain follows. An actual renderer may produce different realized positions for nominally shared indices; that contract must be proven, not welded by this helper. Sound endpoint boxes and exact multi-affine/interval extensions are a possible later sufficient method; this implementation does not provide or assume them. Actual endpoint bounds remain CALLER_UNQUALIFIED.

After independent source/public review, root may request a SEPARATE finite actual-data adapter. A minimal proposal is to reuse the frozen existing target/source/domain reader, freshly reauthenticate every original occurrence/index/affine operand and full Panel, convert without changing the original roster/domains, predeclare whole-case candidate/final/bit/memory/wall caps, require a separately pinned root grant, and report opportunities/UNKNOWN with all numeric/raster/runtime obligations unqualified. Such an adapter must not scan new geometry, infer source receipts, widen a source pool, relabel LOD, emit visibility data or execute automatically. No adapter/private predicate is implemented or authorized by this unit.
