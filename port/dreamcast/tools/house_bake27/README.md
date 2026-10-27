# PS2 house bake experiment

This offline pipeline bakes verified PS2 texture texels and stored PS2 prelight
onto a small C9 wall/roof shell. It adds no renderer, material format, texture
format, runtime knob, stager, release or SD operation. Main owns the separate
default-off runtime material override.

The final private candidate is `C10-house-bake-r3` plus
`C10-native-house-r3`, inside `world-rebuild27-20261027`. Its original-A context
changes only the named 407-triangle house core into 112 triangles: 63 wall and
49 roof. The geometry retains windows, doors, wall thickness, raised roof ridge
and actual source-boundary dormer notches. The other original roof/dormer
materials, changing objects and all other room geometry remain original A.

## Inputs and source chain

`world_rebuild27_house_bake.py prepare` accepts the reviewed
`re4dc.world-rebuild27.house-exchange/1` and a pinned texture-provenance manifest.
Every new output directory freezes the Blender producer scripts and their
hashes. Run the frozen `producer/blender_bake.py` in a separate offline Blender
factory session with private user resources and autoexec disabled.

Wall key `0c77c65b-a7d392ac` comes from original PS2 TPL ordinal 84; roof key
`5f6ca8e9-290510a7` comes from ordinal 37. Independent GS and Jaderlink decoders
agree with those source PNGs, and the original TPL is byte-identical to its
embedded PS2 ISO member. The existing gain-derived PNGs were independently
recomputed from the original PS2 pixels. Stored R4IM prelight already contains
inverse gain; use it verbatim once. This pipeline does not infer PS2 provenance
from a filename or a staged tex.pak key.

Blender uses the proper axis rotation `(x,-z,y)` and millimetres divided by 1000.
Source images and bake images use Non-Color values, with a Raw review view, so
the bake is the numeric source texel times stored prelight. There is no new
lighting, fixed-view world impostor or generated image content.

## Outputs and native boundary

Cycles EMIT selected-to-active writes two 512x512 maps. No mip chain is added.
Existing KOS pvrtex produces full 256-entry RGB565/VQ, and
`convert_tpl.package_existing_vq` wraps the encoded data unchanged. Each compact
payload is 67,584 bytes, including its 2,048-byte codebook; 32-byte alignment adds
nothing. Both maps cost **135,168 incremental VRAM bytes**. Original textures
stay resident. Each `.dt` is 67,616 bytes and each native package is 67,728 bytes.
No upload, contiguous-VRAM or target lifetime acceptance is inferred from this
arithmetic. Far shimmer and mip qualification remain open.

`ATLAS-EXCHANGE.json` records every target corner and its atlas UV encoded back
through the unchanged sourcepart bias/scale. It refuses out-of-range values and
reports quantization. Baked vertex prelight is white ARGB1555 `0xffff` because
source prelight is already in the pixels. The source parts are shared with other
buildings, so a global material or UV-basis replacement would be incorrect.

`world_rebuild27_bake_pack.py` verifies all five original-A hashes, all C9
companions, the exchange/preparation/verified-pixel chain, and clean-A noncore
geometry before creating an output. It creates dedicated L0 core meshlets with
distinct vertex records. Higher LODs, parts, materials, placements, R4PW, R4ID,
R4TC and whole room.r4rc remain unchanged. Existing strip grouping preserves the
meshlet indices; final ranges are independently checked after grouping.

The private include `world_rebuild27_bake_certificates.inc` emits only the
constants for main's existing namespace/type boundary: mesh CRC/bytes,
`Range ranges[]` and `textures[2][4]`. Keys are CRC32/FNV1a of actual compact VQ
payloads, followed by width and height. There are two sorted ranges:
part160/meshlet368 and part288/meshlet659, one meshlet each. Main independently
checks body CRC through its private geometry-admission path before overriding a
draw's texture key.

## Verification and limits

- Final source407 to target112 coverage, source winding, openings and actual
  physical source-edge roof notches are independently checked.
- All 21 changing-owner meshes/62 levels and 705 other levels are exact.
- The final 122 baked vertex records share no index with retained/higher LODs.
- Missing/tampered R4TC and altered baked positions reject before output.
- Independent native VQ decoding agrees with pvrtex to one channel LSB, the
  documented RGB expansion-rounding difference.
- The final Blender decoded-VQ preview recreates the baked core from **actual
  final R4IM strips and their quantized UVs**, then explicitly converts runtime
  top-left V to Blender V. It does not simply reuse unquantized authoring UVs.
- The independent actual runtime block/MeshPackage host check covers 707 levels,
  306,954 checks, 3,539 streams, 2,385 pick visits and eight atlas visits, plus six
  rejected compile configurations.

`BLENDER-VQ-COMPARISON.png` and `BLENDER-VQ-ORBIT.gif` are labelled authoring
previews of the selected core only. Unchanged dormer and other materials are
omitted in every column. They are not Flycast, target-pixel, gameplay, timing or
physical-console acceptance. No performance improvement is claimed.

Earlier r1/r2 outputs are negative prototypes. Their roof planes crossed
different source-material dormer notches; those results remain preserved.
`roof_continuation.py` implements the explicitly authorized bounded same-source
UV continuation alternative, but **it was never applied**: the identified gaps
were genuine source-component notches and were corrected in geometry instead.
