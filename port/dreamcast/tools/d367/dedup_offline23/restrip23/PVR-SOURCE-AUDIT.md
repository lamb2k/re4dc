# Rendering contracts for the estimate

Runtime/recipe base fb254e82ee6f9a3d9e34d53d1d442348a46b9cf2.
Independent read-only audit by i001_pvr_audit; no source edits. Paths below are
relative to port/dreamcast unless qualified. These establish source semantics,
not actual target headers, pixel equality or converter provenance.

Ordinary PS2-world direct headers use native_ui.cpp game/platform:8816-8831
pvr_poly_cxt_txr, with no shading override. Local KOS source
804b3195ebd1a06a27cc2b3a5eacf7a2429040a3 pvr_prim.c:155 initializes Gouraud;
dc/pvr.h:174 defines it, pvr_prim.c:40 writes the shade bit. Opaque headers use
GEQUAL with depth writing and ONE/ZERO blending. Pass0 is opaque, pass1 punch
through, pass2 translucent. Only pass0, alpha255 and unmarked source parts enter
the estimate. Foliage/transpolicy can alter effective pass; sky, UI, diagnostic
interior and modifier paths still require separate exclusion before admission.

Gouraud removes the flat provoking-color objection to cyclic rotation for that
ordinary cohort. It does not prove pixel equality: room/pvr_geometry.cpp:112-153
traverses from source[2], clips then fans from clipped[0]; a cyclic rotation can
change a clipped quad diagonal, FP operation order and coverage. The area test
in pvr_geometry.hpp:69 is also FP/order dependent. Existing canonical odd strip
triangles use (previous,last-before-previous,new), native_static.cpp:1360. The
geometry-only r4im_pkg.let_tris odd cyclic convention is not a provoking oracle.

GEQUAL makes coincident/overlapping surfaces and depth ties consequential.
Guarded estimates retain the original entire group on exact-grid degenerates,
attribute seams at the same XYZ, duplicate position faces, nonmanifold position
edges, positive-area coplanar overlap or transverse segment/surface crossings.
Those guards are deliberately conservative and do not prove absence of near-equal
FP depth ties, cross-group/meshlet/part interactions, singular transforms or clip
changes. No output asset is admitted or written. Existing source provenance,
source CRC/extent and new physical payload/sidecar identities would require fresh
binding on any later output; the converter does not establish PS2 authority.
