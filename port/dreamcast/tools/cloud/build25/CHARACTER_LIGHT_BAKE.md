# Build 25: PS2 character light and AO dataset

`character_light_bake.py` bakes a static light field and bind-pose ambient
occlusion into RGB vertex colours. It reads the **existing**
`re4dc-approved-render-mesh-1` exchange produced by `tools/ps2_cast.py` and
`tools/d367/ps2leon/build_arm_a.py`, including the PS2 geometry and its mapped
rig. The output is a source-bound colour dataset for the local owner's
character packer. There is no new runtime file format or geometry converter.

The explicit `--bake-static-light [0|1]` flag defaults to **0**. Absent and zero
copy the input mesh bytes exactly, without parsing or normalizing them, and
emit no colour data. With the flag enabled, `mesh.json` and `source.json`
still remain byte-identical; the new colours live in a sidecar. Neither arm
rewrites bones, weights, positions, normals, UVs, materials, source-info
identities, triangle order, alpha or source hashes.

This tool uses Python 3.10+ and its standard library. It does not require
Blender or a game disc for the synthetic examples. Actual character inputs
and all derived character assets stay in the owner's private asset store.

## Existing mechanisms used

- `ps2_bin.py` already decodes PS2 BIN positions, normals, strips and weights.
  `ps2_cast.py` verifies the PS2 and game skeleton mapping and produces this
  approved exchange; the bake does not invent another BIN/rig reader.
- `ps2leon/build_arm_a.py --rig` uses the PS2 Leon geometry, weights and rests
  with its documented hair/cloth simulation mapping. That rig is copied
  unchanged, including the differences from the original source rig.
- `d367/charbake/charbake.py` already bakes bind-pose AO into **texture atlases**
  through Blender and private texture jobs. It does not provide vertex-colour
  output and averages shared atlas texels. This tool instead keeps a colour
  per source corner, retaining normal and material seams; it does not alter
  that atlas pipeline or bake an already shaded atlas a second time.
- The native actor already supports `p.colors` and record colour indices.
  Build 25's `ACTOR_LIGHT_FAST_ONLY` path multiplies those colours by its
  precomputed per-part Q16 channel gains, then clamps the final channel to
  255. Gains above 1 survive until this multiply, so a room tint of 1 plus a
  flash of 0.5 can brighten baked RGB 64 to 96 without Leon's texture-headroom
  option. No runtime normal/light evaluation or rebake is needed for these
  colours.

## Deterministic public examples: Leon and em12

Run from the repository root, choosing a new output directory:

```sh
python3 -B port/dreamcast/tools/cloud/build25/test_character_light_bake.py -v
python3 -B port/dreamcast/tools/cloud/build25/bake_examples.py /tmp/build25-light-examples
python3 -B port/dreamcast/tools/cloud/build25/character_light_bake.py verify /tmp/build25-light-examples/leon/baked
python3 -B port/dreamcast/tools/cloud/build25/character_light_bake.py verify /tmp/build25-light-examples/em12/baked
```

Each example is **hand-authored synthetic geometry**, seven positions, two
bones and three triangles; neither is an extracted character or an appearance
proof. Both exercise a receiver under a roof and multiple skin weights.
The synthetic Leon example excludes roof source-info 7, demonstrating how
the real Leon's alpha hair cards can be excluded as solid AO occluders. The
em12 example keeps the roof as an occluder. An authored vertex alpha of 93
must survive packing independently of the changed RGB. Outputs explicitly
carry `synthetic_fixture: true`.

Each generated example contains input `mesh.json`, `source.json`,
`settings.json` and a `baked/` dataset. A separate off-arm demonstration is:

```sh
python3 -B port/dreamcast/tools/cloud/build25/character_light_bake.py bake \
  /tmp/build25-light-examples/leon/mesh.json /tmp/build25-light-off
cmp /tmp/build25-light-examples/leon/mesh.json /tmp/build25-light-off/mesh.json
```

## Real owner examples

Use PS2 geometry from the existing converters. Their disc extraction and
native packing dependencies are private and were not run for this hand-back.
These are the existing converter entry points, not promises that the private
inputs are present in a public clone:

```sh
python3 port/dreamcast/tools/d367/ps2leon/build_arm_a.py "$RE4_PRIVATE/build25-leon-input" --rig
python3 port/dreamcast/tools/ps2_cast.py convert ganado-em12-01 "$RE4_PRIVATE/build25-em12-input" \
  --ps2-iso "$RE4_PS2_ISO" --gc-iso "$RE4_GC_ISO"
```

Leon retains the source binding to
`character-prototype-20260925/source/leon-source.json`; em12's converter writes
`source.json` beside its mesh. The bake refuses a mismatching source hash.
The committed settings are conservative examples in model-space millimetres,
not a calibration to a particular room or appearance:

```sh
python3 -B port/dreamcast/tools/cloud/build25/character_light_bake.py bake \
  "$RE4_PRIVATE/build25-leon-input/mesh.json" "$RE4_PRIVATE/build25-leon-light" \
  --source "$RE4_PRIVATE/character-prototype-20260925/source/leon-source.json" \
  --settings port/dreamcast/tools/cloud/build25/examples/leon-light.json --bake-static-light=1

python3 -B port/dreamcast/tools/cloud/build25/character_light_bake.py bake \
  "$RE4_PRIVATE/build25-em12-input/mesh.json" "$RE4_PRIVATE/build25-em12-light" \
  --source "$RE4_PRIVATE/build25-em12-input/source.json" \
  --settings port/dreamcast/tools/cloud/build25/examples/em12-light.json --bake-static-light=1
```

Existing output directories are refused. Settings are explicit, with no
environment-dependent defaults. Do not bake the previous AO/GCB texture
variant as well as these colours: use its unshaded PS2 albedo or deliberately
record and judge the combined look.

## Dataset format and pack adapter contract

| File | Meaning |
|---|---|
| `mesh.json`, `source.json` | Exact original bytes, including topology, rig, weights, source-info/material/UV seams and any authored alpha |
| `settings.json` | Canonical settings used by this bake |
| `light-colours.json` | `re4dc-character-light-bake-1`; exact mesh/source/settings hashes; geometry-and-rig hash; RGB palette; one row per original triangle and one record per original corner |
| `palette.rgb8` | Palette in first-use order; 3 bytes R,G,B per entry, values 0–255; no alpha |
| `corner-indices.u16le` | One little-endian u16 palette index per source corner, original triangle/corner order |
| `manifest.json` | File sizes/hashes, sample/palette/triangle counts, AO range and offline ray/BVH work counts |

Each mapping row is `{triangle, source_info, corners:[{vertex, colour_index}, ...]}`.
It is intentionally per corner, not only per position or skin palette: a
position shared by two normal/material/UV seams must retain both mappings.
Palette equality permits RGB deduplication but never authorizes topology,
skin-weight or material merging. The tool refuses more than 65,536 RGB
entries; split by existing source parts if that limit is reached. These are
offline dataset bytes; they are not final resident memory figures.

The local adapter must do the following before producing a candidate asset:

1. Run `verify` on the dataset. Bind it to the exact mesh, source and rig;
   never transfer by nearest position or by a guessed vertex order. Carry the
   mapping through the existing strip/reindex pass and include colour index
   in record identity. Preserve all normal, material, UV and part seams.
2. Build the existing `p.colors` RGBA table from the RGB palette, pairing
   each mapped RGB with its **original source alpha**. A shared RGB may need
   separate RGBA entries for different alpha. A missing authored alpha means
   retain the source runtime colour/part-alpha rule, not force alpha to 255.
   The optional exchange `colour_rgba8` property is multiplied into baked
   RGB; its alpha is preserved in `mesh.json` without modification.
3. Keep the existing colour-index metadata, record stride, alpha-state,
   depth/cull/blend state, source-info visibility, rig and lifetime contracts.
   Set the draw lighting record's **`material_vertex=1`, `ambient_vertex=0`**
   for these baked assets, under the candidate asset switch. Keep
   `ACTOR_LIGHT_FAST_ONLY=1`. Static baked RGB then multiplies the per-part
   Q16 lighting gain with rounding and a final 255 clamp; do not replace that
   gain with the separately clamped eight-bit constant-part colour. The
   multiply does not select the old exact evaluator.
4. Supply **room tint plus live flash/fire only** in that draw's light record.
   Exclude the static lamps already represented in the bake. Do not clear
   Leon's live probe or dynamic light mask. This source-light selection is
   part of the local asset integration; the sidecar cannot distinguish a
   game's dynamic lamp from a static one by itself.
5. Verify the final packed colour mapping, geometry/rig identities and
   source alpha, then run the owner's stills, animation/deformation, muzzle
   flash/fire, source gameplay-equivalence and memory gates. The public
   checkout lacks `pack_coarse_actor.py`/the final private packer, so this
   hand-back does **not** claim a ready-to-ship repacked Leon or em12 bundle.

This contract adds no overloaded normal-matrix marker or new actor blob flag.
Normals may remain in the packed source for compatibility; the fast-only
colour pass does not evaluate lights against them.

## Shading and approximations

All directions and distances are in the input's model bind space, using
millimetres and +Y up as the existing PS2 exchange does. A directional light's
`toward_light` vector points from the surface toward the light. For each
unique `(vertex, normal)` sample:

```text
visibility = unblocked cosine-hemisphere samples / ao_samples
ao = max(ao_floor, 1 - ao_strength * (1 - visibility))
shade = ao * (ambient_rgb + sum(rgb * max(0, dot(normal, toward_light))))
baked_rgb8 = round(clamp(authored_rgb8 * shade, 0, 255))
```

Normals and lamp directions are normalized for the offline calculation only.
The fixed cosine-weighted Fibonacci sequence has no random seed. Rays start
`ray_bias_mm` above the surface, stop at `ao_distance_mm`, and test both sides
of nondegenerate occluder triangles. A deterministic median BVH with at most
eight triangles per leaf avoids scanning the entire character per ray. AO
samples are bounded to 1–1,024; offline lights to 32. Excluded info IDs must
exist, so a typo cannot silently change the occlusion set. Degenerate input
triangles are retained in the source mapping but do not block AO rays.

RGB values are PVR-style multiplicative colour values, with no gamma
conversion and no HDR storage. The tool rounds to the nearest 8-bit channel
and clamps at 255. Static directional shading and AO remain attached to the
bind pose as the actor animates/turns; AO is sampled per vertex rather than
per texel; direct-light shadowing is approximated by the same AO multiplier.
Those are intentional appearance changes. Runtime light attenuation and
flash/fire variation are evaluated once per part by Build 25, so they do not
recover original per-vertex shadow or position variation. Alpha, animation,
collision, events and AI are not baked or changed.

## Verification and cost scope

The public gate covers absent/zero byte identity, enabled source/rig identity,
deterministic rebuilds, analytic static-light colours, an opaque roof AO
control and its exclusion, normal seams, preservation of source alpha,
250 BVH-versus-full-scan ray controls, stale-source and tampered-palette/mapping
refusals, nonfinite geometry, invalid/cyclic rigs, invalid weights, topology
and setting limits. Synthetic examples do not establish private character
appearance or console acceptance.

The **tool itself** adds 0 game warm/cold-I cycles, loads/stores, 32-byte lines,
code, stack, RAM or VRAM: it is not in the game build. Its **MODELLED
whole-frame delta is 0 ms before assets are repacked**. Once packed, the
colours cost the existing colour-index stream and RGBA table; the local
owner must report the actual final sizes. A dataset with K RGB palette
entries and C corners contains `3*K + 2*C` binary bytes; an RGBA table starts
at `4*K` bytes and may grow for alpha splits. It is not honest to equate this
interchange count to an already deduplicated meshlet's resident footprint or
claim a new console speedup from the bake alone.
