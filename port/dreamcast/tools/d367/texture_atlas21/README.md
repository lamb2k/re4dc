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
