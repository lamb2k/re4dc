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
