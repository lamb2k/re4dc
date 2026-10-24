# Build 13 builder evidence — 2026-10-24

Public synthetic inputs only. Receipt: `layout-receipt.json`; generated files
and path manifest: `/tmp/b13-current-layout/fixtures.json`. Baseline exporter:
`9b248c5b40a49e4c954ea834fdf665fdbbc314f0`. The ordinary 64-vertex default is
unchanged. All numbers below describe the public fixture, not r101.

## Resident asset counts, all LODs

| Meshlet limit | Meshlets / setup calls if all LODs visited | Ordinary bytes | Split bytes | Strip headers | Submitted corners | Stored vertex records | Repeated stored records within parts | Sum of local transformed vertices |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 32 | 75 | 21,312 | 21,344 | 95 | 1,554 | 1,386 | 666 | 1,514 |
| 64 | 27 | 15,488 | 15,520 | 62 | 1,488 | 1,020 | 300 | 1,148 |
| 128 | 18 | 13,056 | 13,056 | 62 | 1,488 | 840 | 120 | 968 |
| 256 | 12 | 11,456 | 11,456 | 62 | 1,488 | 720 | 0 | 848 |

All LODs are resident; these all-LOD totals are not one rendered frame. Each
package has one mesh, three parts, three clusters, twelve cluster levels and
two placements. There are 1,364 triangles across resident levels, including
1,254 at LOD0. The record split adds only alignment padding in this fixture
(32, 32, 0, 0 bytes); it does not reduce the underlying 28-byte record payload.
R4PW is unchanged. Four-group R4SG sizes are 4,832 / 1,760 / 1,184 / 800 bytes.

## One unique mesh at LOD0, all visible

| Limit | Meshlet setup calls | Strip headers | Submitted corners | Local transformed vertices |
| ---: | ---: | ---: | ---: | ---: |
| 32 | 66 | 66 | 1,386 | 1,386 |
| 64 | 18 | 33 | 1,320 | 1,020 |
| 128 | 9 | 33 | 1,320 | 840 |
| 256 | 3 | 33 | 1,320 | 720 |

A synthetic frame that draws both placements, all parts, LOD0 and no clipping
has twice these work counts, two placement visits and six part visits. Six
polygon headers is an upper bound, not an observed header-cache result.
Fewer/larger meshlets can reduce setup and repeated transforms while changing
culling granularity; this table does not choose a size for the actual world.

## Geometry, ordering and restarts

- All twelve part/cluster/LOD oriented-triangle multisets match the 256-size
  reference exactly, including prelit colour and quantized UV corner words.
  Source mesh IDs, material/pass/cull policy, placements, cluster bounds and
  LOD errors remain identical.
- At 32/64/128, nine of twelve raw ordered streams match 256. The three LOD0
  streams change order, including the translucent part. These are order-changing
  candidates requiring acceptance; no identical TA/visual result is claimed.
- The 32-size result has 33 additional strip segments and 66 additional corners
  versus 256. At 64/128 the strip/corner totals match 256 while meshlet packing
  and order still differ. The split layout itself changes no strips at any size.
- A separate 401-corner strip control preserves exact ordered triangles and
  winding for every limit. It emits 14/8/4/2 segments with 427/415/407/403
  corners: exactly two repeated corners for each additional segment.

## Dense metadata 32-byte demand-line unions

| Limit | Ordinary emit-prefix union | Split Emit16 union | Ordinary complete-record union | Split emit plus bounds union |
| ---: | ---: | ---: | ---: | ---: |
| 32 | 66 | 38 | 66 | 67 |
| 64 | 24 | 14 | 24 | 25 |
| 128 | 16 | 9 | 16 | 16 |
| 256 | 11 | 6 | 11 | 11 |

The receipt also includes sparse-every-fourth and selected-LOD0 controls and
per-record sums. These are architectural address unions, not cache misses,
bus traffic or timings. Selection reading both tables can absorb emission's
smaller footprint. The root's actual SH4 target-cost lane prices its own
selector/setup/replay code; these counts do not substitute for that result.

## Completed gates

- Real production exporter CLI at 32/64/128/256, then actual ordinary C++
  `MeshPackage` adoption; generated full-wrapper-v5 source also passes actual
  `SpanPackage` admission.
- Absent flag, explicit split `0`, and explicit existing 64 limit give exact
  baseline `.re4mesh`, `.r4pw`, and `.json` bytes. Split-on retains the ordinary
  package alongside an explicit v4 alternate.
- Both landed Build12 flags retain exact normal/alternate/report bytes with
  split absent or `0`. Combining either with split `1` rejects before source
  access or any output; their formats and proof contracts remain separate.
- v2 plain and v3 indexed inputs produce strict canonical v4 with unchanged
  logical fields and all-LOD streams. Existing preserve-order R4SG output
  matches the established generator byte for byte.
- Actual spatial `ps2_strip_groups.py` output is accepted by the standalone
  converter with its authenticated group file; exact supplied record bytes
  survive the physical layout change.
- A nonsequential `first_strip` public control passes the ordinary reader and
  retains exact raw index-section bytes in v4, with unchanged per-meshlet
  ordered geometry. This does not inherit the Build11 canonical-index-order
  assumption; private r101/r103 admission still has not been run for Build13.
- Twenty-one invalid/stale/unsupported controls reject: CRC/extent, global u16
  ID capacity, overflowing aggregate Pick reservation, source owner, prelit
  encoding, part state, vertex/strip references, R4PW/R4SG binding and group
  enclosure, wrong lineage/adjacency, unknown trailing sections/sidecars,
  Build12 SDS1/SDO3 markers, appended runtime tables, and an indexed base that
  overlaps a prior part even though its actual offset references are unchanged.

On the recorded host, the four split-on exporter processes took approximately
0.178 / 0.179 / 0.170 / 0.170 seconds and peaked at 15,872 / 17,180 / 17,692 /
18,332 KiB RSS respectively. These are process-local host conversion figures,
including ordinary and alternate outputs. They make no target performance claim.

No private proof sidecar is rebound. Build12 composition requires a new
versioned lineage contract. No game asset, texture atlas, capture, disc,
Blender file or look acceptance is included in this evidence.
