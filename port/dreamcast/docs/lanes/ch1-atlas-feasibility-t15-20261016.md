# r101 scenery atlas feasibility — 2026-10-16

Area atlases can remove material boundaries, but the present r101 assets leave
little room for a broad lossless atlas. All 46 textures used by the 78 spatial
batches already use RGB565 VQ. Their combined codebooks exceed one atlas's
256-vector limit, and repeated UVs make direct uncompressed packing expensive.
The existing capture has 196,256 bytes free in texture VRAM, with a largest
free block of 12,288 bytes. The retail 8 MiB is total VRAM, not spare capacity.

This is a read-only investigation of the current CPU stack at `1f001a1f`, the
approved L2 geometry/WORLD_VERT=5, and `spatial32v3`. No runtime, game asset,
fixture, resident list or shipped package was changed, and no emulator was
launched. Claude's viewdist16/resident16/disc16 work is untouched.

## Material census and possible merges

The asset has 238 active mesh parts, including 197 opaque parts; these are
asset-table counts, not the number of parts submitted in a particular frame.
The 78 spatial parts occupy eight static cells and use 46 unique textures.
Their present unique payload is 374,528 bytes. All opaque world textures are
RGB565 VQ; the complete world uses 109 textures/709,120 payload bytes, including
25 ARGB4444 textures (13 VQ, 12 twiddled). No world texture in this census is
paletted or mipmapped. Actor/effect palettes and mipmaps still consume their
own resources and are outside these world-only totals.

The converter currently groups by every sidecar field and
`MeshPart.texture/alpha/flags/reserved`. For an atlas, texture identity and its
source indices change, but pass/cull/alpha flags remain compatible within each
of the eight cells. Runtime binding uses the sidecar key, dimensions, pass and
cull; the prelit PS2 world path does not use `MeshPart.texture` as a binding.
See [the spatial converter](../../tools/ps2_world_spatial_batch.py), lines 63–84,
and [native_static.cpp](../../game/platform/native_static.cpp), lines 4757–4810.

| Spatial mesh | Parts | Unique texture keys | Minimum header-state groups | Distinct existing VQ vectors |
| --- | ---: | ---: | ---: | ---: |
| 204 | 1 | 1 | 1 | 256 |
| 205 | 7 | 7 | 1 | 1,602 |
| 206 | 19 | 17 | 1 | 4,053 |
| 207 | 4 | 4 | 1 | 968 |
| 208 | 24 | 21 | 1 | 4,687 |
| 209 | 16 | 14 | 1 | 3,374 |
| 210 | 6 | 6 | 1 | 1,298 |
| 211 | 1 | 1 | 1 | 120 |

Thus 78→8 is a material-state ceiling, conditional on an atlas representation
that actually fits. It is not a measured reduction. The actual spatial32
frame-600 log reports 118 opaque parts, but retained evidence lacks the part
IDs and full camera matrix needed to map those exact 118 to candidates.
The earlier spatial32 capture did not retain raw RAM/trace samples for that
purpose. No exact claim such as 118→48 is justified.

As a separate historical-pose exercise, all 56 recorded `t2exact` cross poses
admit spatial meshes 206–209 on the current geometry: 66 spatial parts, with
a theoretical four-atlas ceiling of 62 fewer parts. This calculation uses
Python double arithmetic and assumes a zero viewport origin; it covers static
cell admission, not live dynamic/protected objects, meshlet/strip emission, or
the current frame-600 drawlist. The exact current IDs would require a bounded
diagnostic or a matched retained state, not another inferred count.

There is a smaller opportunity without an atlas. Seven boundaries separate
parts with the same texture and render state merely because their source
texture indices differ. Three pairs, 175/176, 195/196 and 219/220, also have
bit-identical UV bias/scale grids, all using `6d47e0e6-8454336c`. They are a
candidate for preserving the current vertex/UV bytes while concatenating
parts. The other four boundaries need a UV-grid audit. These are proposed
data changes, not implemented or timed savings; meshlet, LOD, strip-group and
part-pool remapping must still pass the converter's identity checks.

## Capacity, formats and texture repetition

The pinned KOS header defines retail PVR RAM as 8 MiB
(`/root/work/kos/kernel/arch/dreamcast/include/dc/pvr/pvr_regs.h`, lines 180–181).
The captured runtime allocates two 2,000,896-byte vertex banks, object-pointer
blocks and overflow pools, tile matrices and frame buffers before establishing
the texture allocator. [native_ui.cpp](../../game/platform/native_ui.cpp),
lines 4746–4862, records the layout and reserves glyph/overlay storage and a
65,536-byte budget margin.

| Current capture observation | Bytes |
| --- | ---: |
| Initial texture allocator pool | 2,567,424 |
| Pool after glyph/overlay allocation | 2,510,080 |
| Texture-cache budget | 2,444,544 |
| Cross scene texture payload, pinned + dynamic | 2,313,784 |
| Cross scene free VRAM | 196,256 |
| Cross scene largest free block | 12,288 |
| Full-bell observed minimum free | 187,040 |
| Full-bell observed minimum largest block | 4,096 |

The full-bell capture requests a 196,608-byte movie window for the 288×192
movie and releases 41 texture entries/154,688 bytes to obtain it. This is
observed allocator pressure, not a reserve available for permanent atlases.
Movie allocation/retirement is in
[native_ui.cpp](../../game/platform/native_ui.cpp), lines 8250–8283. Reported
minima are sampled room-log minima; they are not a continuous all-route peak.
The scene's 2.31 MB texture payload includes actors, effects and UI, not just
the 374,528 bytes belonging to spatial scenery.

Thirty-six of the 78 spatial parts span more than one texture tile; 42 have
UVs outside the unit square. Maximum spans are 23.2773 U and 28.7539 V tiles.
The 46 unique source images alone occupy 2,242,560 bytes if decoded to 16-bit,
before repetition, gutters or power-of-two packing. That is 1,868,032 bytes
more than their VQ payload. Packing each part's entire finite UV rectangle
with a one-texel bilinear border would consume about 33.7 MB uncompressed.
This deliberately conservative rectangle total is not a minimum: separating
disconnected UV islands and shifting each by whole texture periods could
reduce it. It establishes why copying complete UV bounding rectangles is an
unworkable first design.

The current world header uses bilinear filtering and repeat in both axes
(`PVR_UVCLAMP_NONE`), including header-cache hits. See
[native_ui.cpp](../../game/platform/native_ui.cpp), lines 7704–7784 and
7814–7890. Applying `fract` to vertices changes interpolation across repeat
boundaries and is not an exact conversion. A packed island needs periodic
gutters and an affine remap over its full used UV interval; repeating geometry
needs finite tiling, island splitting, or triangle splitting at tile seams.
Splitting triangles also changes vertices, strip construction and setup work.
Pass/cull/fog/alpha/modifier-volume state, existing LODs and strip groups must
remain valid. Transparent and punch-through content stays separate.

Full VQ has one 256-entry codebook per texture. Combining codebooks without
changing decoded texels is possible only when the used vector union fits.
Of 479 distinct-texture pairs sharing a cell, 18 pass this initial test, and
every one contains the single-color `b0920af0-420b71c5` image. This pair test
uses complete original texture vector sets; it does not rule out more elaborate
cropped-island or reblocked encodings. Aligned even-texel periodic gutters can
reuse current 2×2 vectors; odd reblocking can introduce additional vectors.
See [texture_package.hpp](../../room/texture_package.hpp) and
[texture_package.cpp](../../room/texture_package.cpp), lines 413–437 and
574–593, for supported formats and allocation mapping.

## Bounded feasibility example

Cell 208 parts 205 and 208 provide a small exact-texel candidate:

| Part | Texture key | Source size | Used UV interval | Existing payload |
| --- | --- | --- | --- | ---: |
| 205 | `929e8902-683dbf1e` | 64×32 | U 0–1, V 0–0.996094 | 2,560 B |
| 208 | `b0920af0-420b71c5` | 32×32, one color | U 0–1, V 0–0.789063 | 2,304 B |

A 128×64 RGB565 VQ page contains both finite regions plus two-texel periodic
gutters at even coordinates. It needs 210 exact existing vectors and a
4,096-byte payload, compared with 4,864 bytes for the two current textures.
The analysis decodes every accepted 2×2 vector and validates reconstruction;
it does not invoke a lossy encoder or write a texture package.

The proposed patch rectangles are 68×36 at atlas (0,0) and 36×30 at (68,0),
both starting at source texel (-2,-2). Mapping these into a common 16-bit UV
grid adds an estimated maximum 0.000611 texel U error in the offline arithmetic.
Exact decoded texels therefore do not establish identical filtering, UV
interpolation, clipping or raster output. No candidate has been visually
accepted. Even this pair still needs frozen seam/near-wall/motion comparisons.

The maximum batch reduction is one part. The 768-byte net payload reduction
applies only if both original allocations retire; retaining them instead adds
4,096 bytes, plus normal package/allocator overhead. Neither key appears in
the current `dc/resident.bin`, and neither is referenced by a nonspatial world
part in this asset, but every preload/fallback/other-owner reference still needs
checking before retirement. The new page must load before its first use and
remain resident while queued polygons sample it; retirement requires the normal
render fence and handle/header-cache invalidation. Movie/subscreen entry and
room re-entry must retain their allocation guarantees. The resident source was
read only; no lifetime policy was changed.

Given a one-part upside, this report does not recommend building a runtime
spike solely to demonstrate this small pair. The three identical-grid,
same-texture pairs above offer a simpler candidate if further work is approved.

## Cost and a larger-atlas decision

The actual spatial32 capture's console-fit model assigns these self costs over
30 samples, frames 500–799 at stride 10: world direct-begin 0.6131 ms,
direct-end 0.1488 ms, stream-select 0.1133 ms, MeshDraw::run 1.2185 ms and
ps2_pass 0.8556 ms. They include other passes/callers or work that an atlas
does not remove. The header cache is already active. These are model costs,
not measured console milliseconds, removable per-part fees, or atlas savings.
They must not be multiplied by a part-count reduction or added to overlapping
parent-call costs. Vertex transformation, clipping and most geometry work
remain. Larger pages may also worsen texture locality or eviction behavior.

A broader design would first crop/normalize disconnected UV islands, then
price a small set of same-state pages per cell. Any page that requantizes more
than 256 source vectors is a lossy visual change; it needs a declared image-error
budget and side-by-side seam, detail, distance and motion review. A lossless
uncompressed alternative needs a measured residency budget covering actors,
effects, subscreen and movie peaks. Neither route is currently shown to fit.
Only after an offline pack fits and earns visual acceptance should a matched
capture measure actual submitted parts and hardware-model deltas, followed by
the existing STRICT/decision, full-Leon, texture, movie/door-route and physical
console gates. No performance benefit is promised by this investigation.

An incidental format finding is retained in the census: the 97 VQ world
packages use payload-only header CRCs, while the 12 twiddled packages match
the loader's descriptor-plus-payload CRC. The current resident fast path skips
that CRC pass (`texture_package.cpp`, lines 316–333); source package SHA-256s
are recorded instead. This report does not certify their CRCs against the
debug path or modify accepted packages. A new writer should emit the loader's
expected CRC and pass its normal validator.

## Evidence and reproduction

[Machine-readable result](ch1-atlas-t15-20261016.json) contains the material
counts, source hashes, same-key candidates, bounded atlas price and exact log
line references. Full per-part/texture metadata is preserved privately in
`C:/Game Dev/Emulators/_codex_atlas_t15_20261016/final/`.
The scripts are [census.py](../../tools/d367/ps2world/atlas/census.py),
[price.py](../../tools/d367/ps2world/atlas/price.py) and
[evidence.py](../../tools/d367/ps2world/atlas/evidence.py). The census intentionally
pins spatial32v3's mesh hash so future part-index changes cannot silently reuse
this report's candidate identities.

From the repository root under WSL, with the existing private evidence present:

```sh
python3 port/dreamcast/tools/d367/ps2world/atlas/price.py \
  --asset-dir /root/probe/codex-ch1-render-20261015/assets/spatial32v3 \
  --fixture /mnt/c/Flycast-Evidence/re4-dreamcast/codex-cpu-t15-20261016/hwmodel-cxt16sp32-cross/fixture.json \
  --historical-cameras /mnt/c/Users/lambd/AppData/Local/Temp/t2x/pvs/cams-cross.txt \
  --out /root/probe/codex-atlas-t15-20261016/reproduced
python3 port/dreamcast/tools/d367/ps2world/atlas/evidence.py \
  --model-capture /mnt/c/Flycast-Evidence/re4-dreamcast/codex-cpu-t15-20261016/hwmodel-cxt16sp32-cross \
  --movie-capture /mnt/c/Flycast-Evidence/re4-dreamcast/codex-cpu-t15-20261016/spatial-bell-full-spatial32v3 \
  --out /root/probe/codex-atlas-t15-20261016/reproduced/evidence.json
```

Validation: asset and sidecar parsers/CRCs passed; source package hashes and
format records were read back; the proposed pair's VQ blocks reconstruct exactly;
historical pose admission and UV-grid arithmetic were rerun; Python syntax and
Git whitespace checks passed. This validates the investigation, not a runtime
atlas or a console improvement.
