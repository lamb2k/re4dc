# Build 31 portal-cell builder

`barn_portals29.py --barn-portals29=1` builds a package-bound candidate from
the actual converted PS2 world mesh. The flag defaults to 0; absent or zero
reads no input and writes no output. `graft_portals29.py` has the same gate.
The tool changes no existing package, recipe, source state or collision.

## Geometry contract

The caller supplies one or more axis-aligned building hull boxes and safe
camera-eye boxes. These are authoring inputs from the private geometry, not
the player's approximate console coordinate. Every hull face begins open.
Only exactly coplanar triangles in opaque, static parts can close it.
Cutout/translucent/vertex-alpha parts, unique mutable R4ID placements,
unsupported cull modes, off-plane/slanted walls and every other uncertainty
remain open. The initial codec accepts canonical or preserved-index R4IM v3
plus R4PW. Other physical layouts refuse and need an owning adapter; do not
relabel their headers to force admission.

Static-ID classification follows `native_static.cpp`'s `dyn::slot_of` build
at package open: only IDs below `dyn::kIds` (250) occurring exactly once
receive slots. `re4dc_ps2_dyn_bind` rejects IDs without a slot, and `ps2_pass`
queries through `ids[pl.placement]`, not the R4PW array ordinal. Repeated IDs
remain baked by this explicit runtime contract. The tool applies the same
lookup; an out-of-range source placement is unknown and cannot occlude.

For each cluster, the tool intersects its opaque triangle coverage across
**every stored LOD level**, including empty levels. It then unions the
qualified clusters and takes each face's complement. Polygon clipping and
subtraction use exact rational arithmetic on the package's stored values.
There are no sampled rays, sample-spacing assumptions or missed positive-area
cracks. Each uncovered polygon becomes a conservative aperture rectangle,
expanded by at least 64 mm and rounded outward to float32. Complicated faces
may become entirely open to keep the runtime at no more than 24 portals.
This can reduce savings, but cannot justify hiding more geometry.

The eye boxes must be inset at least `near_max + 64` mm from every hull
face. Runtime view/projection checks must also verify that every near-plane
corner lies within `near_max` of the camera eye. Leaving a safe eye box
disables the cell; doorway crossings never retain a previous eye's proof.

The 64 mm guard covers ordinary float32 world transforms only within the
tool's admitted magnitude bound: the sum of absolute affine terms is below
2^20 mm. The arithmetic complement proves the decoded geometric surface.
It does not certify rasterization, package admission, source draw availability
or console pictures. The magenta hidden-geometry walk and current-frame
witness gate remain necessary. The PCL2 extension deliberately fails the old
loader's exact file-size check; it cannot silently activate through it.

## WP29 extension to PCL2

Houses, cells and portals retain the existing PCL2 structs and lifetime.
The reserved header words and trailing witness array add the following:

| Header byte | Meaning |
|---|---|
| 40 | `WP29` marker, little-endian `0x39325057` |
| 44 | Proof offset, immediately after the last portal |
| 48 | 1–256 witness records |
| 52 | Proof version 1 |
| 56 | CRC32 of the witness array |
| 60 | CRC32 of the entire file with this word zero |

A witness is two little-endian u32 values: placement ordinal and absolute
part ordinal. Records are sorted and unique. The physical R4IM CRC/bytes
and **physical** R4PW CRC remain in the ordinary header. R4ID is hash checked
and bound to the physical policy or an exact approved provenance remap.

The runtime must require every witness part to have completed its opaque
draw successfully in the same current view, with unchanged source state and
affine, before any portal reject. A missing texture, partial/failed meshlet
submission, skipped part, hidden/moved source placement, stale view, movie
loan or missing package invalidates that permission. The tools do not treat
the presence of an opaque wall in a file as evidence that it drew.

## Author a private configuration

This is the schema. Coordinates and hashes below are explanatory placeholders,
not r103 data or a usable candidate. Choose hull planes from the actual
opaque static wall planes; use all openings, not a door-only rectangle.

```json
{
  "schema": "re4dc.world-portal29/1",
  "room": "0x103",
  "package": {
    "mesh": "ps2-world.re4mesh",
    "mesh_sha256": "SHA256_OF_THIS_FILE",
    "policy": "ps2-world.r4pw",
    "policy_sha256": "SHA256_OF_THIS_FILE",
    "ids": "ps2-world.ids",
    "ids_sha256": "SHA256_OF_THIS_FILE"
  },
  "near_max": 256,
  "aperture_margin": 64,
  "houses": [
    {
      "name": "barn from PS2 package",
      "hull": [[0, 0, 0], [4000, 4000, 4000]],
      "eye_boxes": [[[512, 512, 512], [3488, 3488, 3488]]]
    }
  ]
}
```

An optional `placements` integer list restricts which source placements may
contribute walls. It never changes which openings are required. Omitting it
considers every package placement. Repeat the house object for village or
castle buildings. Several houses can share witness parts; the runtime still
requires the complete witness set before culling.

## Exact private-data commands for Claude

Run from the repository root. Set the variables to the real private paths;
the cloud does not have or infer them. `PKG` is the directory containing the
three files above, `CFG` is the authored configuration, `BASE_FIXTURE` is an
existing fixture that explicitly stages this room's mesh and policy, and
`OUT` is a **fresh** private result directory. Use forward-slash WSL paths.

```sh
sha256sum "$PKG/ps2-world.re4mesh" "$PKG/ps2-world.r4pw" "$PKG/ps2-world.ids"

python3 port/dreamcast/tools/d367/ps2world/interior/barn_portals29.py \
  --barn-portals29=1 --config "$CFG" --package "$PKG" \
  --out "$OUT/interior.cell" --report "$OUT/portal-proof.json"

python3 port/dreamcast/tools/d367/ps2world/interior/graft_portals29.py \
  --barn-portals29=1 --fixture "$BASE_FIXTURE" \
  --cell "$OUT/interior.cell" --out "$OUT/fixture-portals29.json"
```

The graft verifies the cell CRCs and compares both staged package identities
before adding `dc/native/rXXX/interior.cell`. It preserves every other fixture
field, resolves existing replacement paths against the original fixture and
removes this destination from the removal list. Use the existing fixture/disc
packing procedure on the resulting file. Do not overwrite the accepted cell
or release asset directory. The hand-back supplies the runtime build knobs
and owner gates after the runtime portion is qualified.

Retain `portal-proof.json`, exact config/package/image hashes, the six face
areas/openings, witness count and all loader/runtime refusals. An all-open
face or unsupported package is a useful answer: return it for a source-backed
adapter instead of decreasing margins or declaring an unobserved wall closed.

## Synthetic qualification

```sh
python3 port/dreamcast/tools/d367/ps2world/interior/test_barn_portals29.py -v
```

Fixtures are authored cuboids with doors, windows, a 0.125 mm slit, alternate
LODs, wrong-facing/cutout/dynamic walls and malformed cells. They check actual
package serialization/strict decoding, exact complements, checksum and near
refusals, legacy-loader exclusion and absent/zero no-output behavior.
No recovered game assets are included.

Tool-only cost: no runtime code, stack, loads/stores, cache lines or cycles
are added by running the converter offline. **MODELLED whole-frame delta:
0 ms for the tool-only step.** Candidate cell bytes are reported exactly;
runtime selection/witness costs and actual rejected geometry belong to the
runtime receipt and private console pair, not to converter wall-clock time.
