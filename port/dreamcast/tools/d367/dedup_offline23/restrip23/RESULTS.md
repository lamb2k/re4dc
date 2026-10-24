# I-001 estimate checkpoint

Runtime/recipe fb254e82ee6f9a3d9e34d53d1d442348a46b9cf2; final helper freeze
955ebf73d46f7d75c49d35e7a824c0c2677144bd. The final r3 reports record every
helper/input hash. They reproduce the provisional r1/r2 counts, preserved on C:.
Twenty-one host semantic/input controls passed. No assets were written.

The >=15% cross submitted-corner GO is not established. Strict-order and fixed-
provoking graph candidates save zero. Allowing opaque Gouraud cyclic reorder
finds very little. Counts below aggregate the43 actual cameras500..794 stride7,
LOD20; corners/strips are after trivial rejection but BEFORE near clipping.

| View / mode | Strips | Corners | Average length | Corner reduction |
| --- | ---: | ---: | ---: | ---: |
| Cross baseline |129924|608869|4.686347|0%|
| Cross cyclic potential |129522|608232|4.695974|0.104620%|
| Cross guarded cyclic |129666|608368|4.691808|0.082284%|
| Farm baseline |146200|627757|4.293824|0%|
| Farm cyclic potential |145899|627327|4.299735|0.068498%|
| Farm guarded cyclic |146200|627757|4.293824|0%|

This is MODELLED traffic, not captured TA words, target timing or pixel equality.
Cross near-straddling strips remain301 across all modes; farm cyclic changes258
into301, directly demonstrating why clipping cannot be silently ignored.

The full XYZ/UV/ARGB1555 adjacency graph provides a distinct optimistic bound for
selected/walked traffic. It permits cyclic reorder and relaxes parity and tie
constraints. Cross797119 selected corners has an optimistic floor771923: ceiling
3.160883% (per-frame range3.10..3.22%). Farm1019229 has floor992311: ceiling2.641016%.
This does NOT bound all possible post-cull/near-clipped TA traffic, because strip
repartition can change rejection. It does show most existing short packet strips
cannot freely join while retaining all source attributes and SG boundaries.

| Room | Compact bytes | Cyclic estimate | Guarded estimate |
| --- | ---: | ---: | ---: |
| r100 |1488192|1487808 (-384)|1488128 (-64)|
| r101 |1243808|1243712 (-96)|1243744 (-64)|
| r103 |1047968|1047712 (-256)|1047968 (0)|

These include exact immutable full-strip-block sharing, alignment and unchanged
vertex/LOD tails. No r100 allocation growth is modeled, but no fresh s30 gate ran.
Source CRC/extent and all four compact pins remain authenticated separately.

Legacy camera logs truncate viewport depth tails in43cross/42farm requested rows.
No nibble was supplied or inferred. New validation authenticates the first four
viewport words actually used by side planes: complete finite words, zero offsets,
positive extents. Native LOD uses screen resolution and projection; neither this
model nor those runtime side-plane calculations use vp4/vp5. See source audit and
negative controls. This narrowly supports these counts, not a full25-float camera.

Forest remains pending root's authenticated camera capture. Fixture player pose
is not a camera. Missing forest data does not block reporting the existing cross
candidate's failure to establish GO. No runtime/shared-builder claim, SDK, guest,
new media, recipe or production change follows from this estimate checkpoint.

Physical report byte pins refer to preserved C evidence. Git normalizes Windows
camera JSON CRLF to LF; r3-seal.json records the separate Git canonical byte pins.
Parsed report values are identical. No earlier physical evidence is overwritten.
