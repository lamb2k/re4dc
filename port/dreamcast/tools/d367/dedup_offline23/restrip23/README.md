# I-001 offline re-strip estimate

Runtime and recipe base fb254e82ee6f9a3d9e34d53d1d442348a46b9cf2.
Owned tools only. No runtime, shared converter, recipe, asset or media changes.

The strict-order control keeps the native clipper's exact ordered triangle tuples,
including final/provoking corner, full decoded XYZ/UV/final ARGB1555, winding and
degenerate multiplicity. It finds zero savings, a control rather than a final
NO-GO. The opaque graph estimate additionally permits triangle reorder and cyclic
rotation under ordinary Gouraud semantics. It preserves each meshlet and existing
SG group, material/part/placement/LOD boundaries, <=255 strip corners, <=255 local
indices and all attributed oriented triangles with multiplicity. Unchanged local
corner tables retain the existing <=256 limit. Whole vertex tables remain intact.
Nonopaque, alpha<255 or marked source parts are untouched. Full decoded attribute
keys prevent welding UV or color seams. Counter validation checks every candidate;
fixed-provoking mode also checks exact tuple multiplicities. Candidates that fail
to reduce corner count retain original strips.

Three graph variants are reported: fixed provoking; ordinary opaque Gouraud cyclic
potential with known tie risks; and cyclic with conservative whole-group exact-grid
tie guards. None is rendering admission. PVR-SOURCE-AUDIT.md explains Gouraud,
GEQUAL and cyclic near-clip fan/FP risks. Untested effective-pass overrides and
cross-group/meshlet interactions also remain outside admission. The deterministic
greedy stripifier is a heuristic, not a global optimum.

A separate optimistic topology control relaxes parity, ties, provoking and clip
constraints. Full attributed directed shared edges define triangle adjacency.
Each connected component requires at least one strip, each degree-one triangle
requires an endpoint, and a <=255-corner strip holds at most253 triangles. Summing
max(1,ceil(leaves/2),ceil(triangles/253)) per component gives a lower strip-count
floor, hence a maximum selected/walked-corner reduction. This is NOT a universal
post-cull/near-clipped TA bound: changing strips can change trivial rejection.

Actual cross/farm PS2CAM frames500..794 stride7 (43 views each) are priced at the
current effective LOD divisor20 (Standard5 times SCENERY_FAR_LOD4). The copied
camera/selection helper is source-hashed and attributed; no old LOD5 estimate is
used as current evidence. Existing original R4IM/R4PW/R4SG provide transforms,
LOD and box selection. Actual compact decoded coordinates/strips provide traffic.
Compact versus original SG bounds/end offsets are checked equal; word7 source
span intentionally differs after existing offline point dedup. Group membership
is remapped after re-striping, retaining exact group triangles. CPU point priming
is not estimated. Corner reports distinguish selected/walked and after trivial
strip rejection before near clipping; they are MODELLED, not actual TA capture.

Current cyclic heuristic cross savings are0.104620% after trivial rejection,
guarded0.082284%, fixed0. Farm cyclic0.068498%, guarded0. The optimistic ceiling
for selected/walked traffic is3.160883% cross and2.641016% farm. These do not
establish the required >=15% submitted-corner GO. No target work is warranted by
this candidate yet. Forest has no authenticated camera log available; the known
fixture player pose is not substituted for a camera. Root owns camera capture.

Loaded compact cyclic physical sizes model r1001487808 (-384), r1011243712 (-96),
r1031047712 (-256) bytes; guarded r1001488128 (-64), r1011243744 (-64), r1031047968
(unchanged). Exact full-block sharing, two-byte alignment and32-byte tail alignment
are priced; vertex/LOD bytes remain unchanged. This is an allocation estimate,
not a fresh s30 heap gate, and no packages are written. Original source CRC/extent
and every resolved input hash/size are checked against the current recipe and
frozen compact pins. Any future output needs fresh physical CRC/SG/provenance binds.

Run18 host controls with python -m unittest discover -v in this directory. Tests
cover joins, winding/provoking, rotations, UV/color seams, groups/transparency,
degenerate multiplicity, length limits, deterministic non-growth, topology floors,
and wrong hash/same-size content/wrong extent refusal. Windows Python312 with numpy
runs estimate_cameras.py; estimate_graph.py needs only standard Python. Both write
only a new small JSON report and refuse overwriting prior evidence. Inputs are the
private resolved-inputs.json and exact compact root, supplied explicitly. Preserve
all r1/r2 reports; final frozen rerun is r3. No SDK, guest, timing, hardware,
look acceptance, production change or I-001 GO is claimed.
