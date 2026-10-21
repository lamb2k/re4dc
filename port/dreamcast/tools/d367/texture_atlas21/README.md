# Leon atlas tile isolation

Opt-in offline implementation for the square128 coat/body tile
SourceTex_878b23c0-e7038833. The standard jacket has17 and pl08 body23 conservative
corner-footprint crossings at the original atlas128 mip. This narrow candidate
adds one square128 clamped VQ resource per costume; all other atlas tiles remain
explicitly held. No padding or stretching is used.

The source512 atlas packages remain exact. New bases are Morton sub-plane crops
with the entire original2048-byte codebook unchanged. The u16 UV transform is an
exact integer power-of-two affine map. Positions, normals, weights, source role,
triangle rotation/winding/duplicates and draw order remain exact. Contiguous
material runs preserve order; the tool never groups distant triangles by tile.
Each output run is a bounded FE/v3 stream in the existing actor format. The new
opaque tile material is appended after existing atlas/hair slots by a future
guarded integration. Existing material slots and hair/alpha contracts remain.

The sealed square128-v2 candidate limits contiguous segments to the existing 22
plan runs, reserving every other body role and up to two source hair runs.
Standard Leon isolates all 43 selected-tile triangles in 9 role runs (17 total
plan runs at that conservative bound). Pl08 isolates 278 of its 326 tile
triangles in 13 role runs (22 total at the bound); seven other segments keep the
original atlas. The earlier v1's 27 pl08 role runs are an unadmitted offline
comparison. No runtime capacity is raised.

New private keys are 3662c0aa-c9e71c00 (standard) and fefdf580-f15c1f47 (pl08).
Each adds 7510 raw or 7520 rounded payload bytes while the original atlas stays
used. Independent KOS pvrtex checks cover 16 candidate levels and 38 decodes
including original/baseline levels. A separate scalar bilinear/box comparison
agrees with the vector comparison and finds zero base sampling error.
Conservative footprint crossings at atlas128 do not change sampled RGB in this
tile. Numerical error improves at coarser levels; a conservative crossing is
not itself proof of a visible artifact. Private before/after charts show actual
sampling outputs against the isolated box reference, not generated gameplay.

The first v2 seal has 68 file entries and SHA256SUMS hash
9b524ee573753dcb640cb561ba7966e56c5d57e53200c5dcbd8683f0796ad2a2.
Its Windows mirror is texture-atlas21-20261021/square128-v2. V1 remains preserved.

The consumers-v2 recovery binds the exact original 17-blob hand archive, the
37-triangle neck and the 1045-triangle flying face to their actual UV owners.
The four neck arrays are checked in the actual loaded unchanged QA program,
not debug sections. None uses the first isolated tile. The separate flying hair
retains its repeat colour/mask material. These preencoded streams have no pending
dynamic LOD; the optional LEON_LOD package path is resolved off in the selected
recipe. The recovery retains original manifest, archive, program and source
hashes and does not modify any gameplay state or texture input.

The resumed adapter is now source-qualified against the unchanged actual plan
and preflight types under ASan/UBSan. Standard, pl08 and headless pl08 produce
17, 22 and 19 conservative runs respectively, appending only the selected tile
material. All 17 original hand blobs are preserved in each appearance's correct
current role (51 dynamic plan variants). The headless fixture also retains and
preflights the actual 37-triangle neck. Flying-head appearance 0x10A declines
without changing the original plan because it does not sample this tile.

Cold qualification walks every source and emitted triangle in order and checks
exact position/normal references and original or affine UV values. It refuses
pending/alternate LOD streams. Bind refuses stale epochs, insufficient/overlapping
local immutable-ID ranges, changed source descriptors and run/material overflow.
Both failed and default-off edits leave the destination unchanged, including an
aliased source/destination. retire() revokes a prepared binding before its package
owner can free or reuse backing. No backing is allocated or freed by the adapter.

binding-v1 seals six actual OFF/ON source-format executables and logs. Enabled
standard/pl08/headless cases pass 65/65/66 checks, including 51 original dynamic
hand plans. The candidate/source seals remain unchanged. Foreign owner-info and
unrelated role descriptors are explicit host sentinels; these results do not
certify a full live owner, original material, runtime lease or game frame.

No runtime includes the adapter yet. RE4DC_LEON_ATLAS_SPLIT defaults to zero.
Global immutable IDs, package generation/reset wiring, material-capability hooks,
pinned resources and target gates remain open. The next shared-hook proposal
must preserve the complete existing material certificate and transaction leases.

Run with Windows Python/NumPy/Pillow:

```
python atlas_split.py --source-root PRIVATE/texture-actors21-20261021 \
  --out PRIVATE/texture-atlas21-20261021/square128-v1 --enable-atlas-split
```

Without the switch it emits exact original package identities. Existing output
directories refuse. No runtime/shared helper, recipe, asset input, release or SD
is changed. New runtime adoption stays default0 and needs separate coordination,
material/run admission, allocation, actual projected sampling/look and hardware
checks. Historical actor source policies and exact source hashes accompany the
candidate. Sampling charts are mathematical texture comparisons, not gameplay
screenshots or target performance.
