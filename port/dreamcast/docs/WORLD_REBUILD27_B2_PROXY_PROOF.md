# B2 private structural proof, 2026-10-27

The bounded B2 experiment produces a real existing-format mesh package, but
boundary-preserving retessellation cannot close the world budget. Do not model
the 21-triangle complete-room saving. This is not a rejection of deliberate
architecture replacement or the whole world programme.

## Delivered semantic plane

Private root: `world-rebuild27-20261027/B2-semantic-facade-proof-r1`.
Tool: `port/dreamcast/tools/world_rebuild27_facade.py`, importing the stable
world worker helper read-only. Offline dependencies are Shapely 2.1.2 and NumPy
2.2.6. No renderer, build recipe, staging, disc or runtime file changes.

The source near-house stone wall is placement 123, mesh 104, part 160,
resident PS2 key `0c77c65b-a7d392ac`. That part spans several buildings, so the
proof first maps the 145-triangle connected component with source world bounds
`(-1064,862,7826)..(10666,5767,21110)`. It replaces only a 41-triangle vertical
wall surface inside that component with one 20-triangle plane. The source
projection has one window opening, preserved in the quantized output. The
separate changing door at placement 211 / part 326 remains untouched.

This removes source relief of up to 45.479 mm. The authored outer boundary is
within 0.946 mm of the source projection. The window expands conservatively by
2 mm to avoid filling the aperture after quantization. UVs and prelight use
nearest source corners with the existing PS2 material; appearance is unaccepted.

The room remains 11,033 L0 triangles versus B1's 11,054. Package bytes: 261,280.
CRC: `2d7542e8`. Mesh SHA256:
`1fb719c959bfb8146cc0bd2677b759cd08e741875ba5751cb09fb95bde23c8f9`.

## Verification

The standalone `world_rebuild27_facade_verify.py` reads the serialized package,
subtracts the retained source triangles, and independently projects the actual
remaining geometry using a fresh source-derived normal. It verifies:

- All 21 changing-owner meshes and their 62 levels are exact.
- Ground's 17 levels and 700 other source levels remain exact against B1.
- The actual authored triangles are 20, nondegenerate, nonoverlapping and have
  the source winding.
- One source aperture remains one output aperture. Filled source aperture
  area is zero.
- Material, placements, part/LOD identity tables and whole R4PW, R4ID, R4TC and
  room.r4rc companions remain unchanged.

Actual host MeshPackage reader: `RUNTIME_ADOPT_OK meshes=204 parts=342
meshlets=139 vertices=15350`. Receipt:
`host-adopt-B2-semantic-facade-proof-r1/RECEIPT.json`.
Package and host evidence were mirrored to the matching C: private directories
and every copied file was hash checked. No Flycast, SDK build, guest model,
console, route or look check ran. No timing or appearance PASS is claimed.

## Negative automatic patch results

The earlier `B2-planar-patches-r1` retained source UV boundaries and removed
only 10 triangles. Allowing interior UV appearance approximation saved 320
triangles at 5 mm / 5 degree grouping. Broad 50 mm / 30 degree grouping saved
404 triangles before independent verification caught a degenerate output
triangle. That artifact is explicitly unqualified and must not be admitted.
The source tool now refuses degenerate/reversed output, but no further sweep
was run. These results stay private as negative evidence.

Most remaining source patches already have only one or two triangles and no
interior vertices to remove. A useful sparse B2 now needs broader named
architectural faces and a visual review, rather than larger automatic
tolerances or additional object pruning. Main retains qualification; Claude
retains integration, recipes, releases and SD changes.
