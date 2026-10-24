# I-001 offline re-strip estimate

Base runtime/recipe source: fb254e82ee6f9a3d9e34d53d1d442348a46b9cf2.
Owned tools only; no runtime, shared converter, recipe or asset changes.

The initial strict-order control preserves the native clipper's exact ordered
triangle tuples (native_static.cpp:1360), including the final/provoking corner,
full decoded XYZ/UV/color attributes, winding and degenerate multiplicity.
It partitions only inside existing meshlet and R4SG group boundaries; nonopaque,
vertex-alpha or marked parts are left untouched. Strips remain <=255 corners,
local indices <=255, and candidate traffic must decrease or the old strips stay.

Nine host semantic tests cover packet joins, winding/provoking rotation refusal,
UV/color seams, exact aliases, group/transparency isolation, degenerates, index/
length limits and deterministic non-growth. This is not a target/pixel gate.

The real current compact r100/r101/r103 census admits 1,257/1,678/1,157 opaque
meshlets. It finds zero strict-order reduction and no physical/allocation growth.
That is a lower-bound control, NOT a final NO-GO. The user allows opaque triangle
reordering with the required rendering contracts; the separate opaque graph
estimate must audit actual Gouraud/flat state, canonical attributed winding
multisets, degenerates and consequential tie risks before any admission.

Current recipe inputs were resolved through the source's actual DATA precedence
and pinned on C:. Compact package source CRC/source extent remain bound to the
actual original package. The estimator writes only small JSON reports, no assets.

Pending: actual benchmark camera selection at effective LOD20 for r101 cross,
r103 farm and r100; separate walked versus actually submitted/clipped traffic;
general opaque candidate; exact compact strip-sharing allocation size; tie/
provenance/sidecar risks. GO requires >=15% cross corners and no r100 heap harm.
No SDK, guest, new media, timing, hardware or look acceptance is claimed.

