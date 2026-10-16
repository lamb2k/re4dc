# Far scenery shell: source and asset review, 2026-10-16

The idea merits a bounded r101 prototype, but neither a 0.5–1 ms shell cost nor a net 7 ms saving is established. The user's Full-to-Short console saving of 7.9 ms is a useful anchor for that exact console comparison. A shell which restores Full fog, foliage, live props and actors has a different workload. Measure it against the accepted L2 geometry and current full Leon/g70/cap-6 stack before assigning any of that saving to it.

This review is offline and read-only for game code and private assets. It created only the census scripts, JSON and this report in `_codex_cpu_t15_20261016`. It did not launch an emulator, run a model capture, change another lane, create a disc, publish or copy to SD.

## Current ownership and inspected identities

The CPU baseline is `cxt16baserW`, measured runtime source `3e303c5e` on the local integration based on `ae3d2c8b`; the checked-out tree is now `1f001a1f` with subsequent diagnostics. Its ELF is `1f98fe56859c114ad09a818dd4b6f33658c42c73d11229186ec5ad9428cef8c6`. The baseline source/fixture paths are:

* `/root/probe/codex-cpu-t15-20261016/tree`.
* `/root/probe/codex-cpu-t15-20261016/logs/fix/cxt16base-cross.json`.
* R101 selected geometry: `/root/probe/codex-ch1-render-20261015/assets/r101/ps2-wv5.re4mesh`, the approved L2 triangles packed for locality/batching. This is not a new visual reduction level.
* R101 placement, ID and live-gate manifest: `re4-assets-private/crowd12-bake-20261015/r101-t13/{ps2-world.r4pw,ps2-world.ids,append.json}`. The census verifies that the manifest and both inspected r101 sidecars have the same CRC.
* R103 currently resolves to `re4-assets-private/t11-20261014/blackps2/r103/{ps2-world.re4mesh,ps2-world.r4pw,ps2-world.ids}`.

An existing Claude lane already implements a far-shell POC at `/root/probe/lanes-20261016/farshell`, based on `c3fedcaa78ae8ec821bfb04b040b2fac13bdbf86`, with uncommitted runtime edits. It is separate from this review. Its private converter and assets are in `C:/Game Dev/Emulators/farshell-20261016`, and its generated build is `fs16arW` / `routefs16arW`, ELF `b4ab85937472dcfdbb2c11bb120c8a0a980dc5c5353a9c44b9f93722faa57caf`, `_end=8c428198`. These files are active work, so the accompanying census records their inspected hashes rather than claiming this report describes all subsequent edits.

The POC resolved-knob file is `/root/probe/lanes/route/out-fs16arW/resolved-knobs.txt`. Relevant values: `FAR_SHELL=1 VIEW_DIST_OPTION=1 FOG_FAR=25000 FOG_FAR_CAP=0 PS2_WORLD_MESH=1 PS2_WORLD_DYNAMIC=1 PS2_WORLD_PARTS=1 PS2_WORLD_LEAN=23 PS2_PLACE_GATE=1 PS2_AREA_HIDE=1 PS2_PVS=0 PS2_STRIP_GROUPS=1 STATIC_OBJ_BAKE=1 R101_ALIVE_CAP=6 PS2_LEON=1 GANADO_LOD=1 GANADO_LOD_LEVEL=2 PACE_MODE=off MOVIE_WORLD_ARENA=0 TA_VERTBUF_KB=2048 TA_DOUBLEBUF=1 MESH_LOD_PX=3`.

That POC is not the CPU baseline. Its input world is the original source-detail package: 47,231 opaque triangle instances, versus 25,463 in the selected CPU L2 package. An apparent saving against its own Full arm cannot be added to the accepted L2 saving or transferred to `cxt16baserW` without a matched measurement.

## What the package actually contains

`farshell-source-census.json` is the reproducible structural census. These are whole-room level-zero instances, not camera-visible triangles, recurring CPU charges or savings. Vertex references count each selected meshlet's inputs and can repeat a stored vertex. Material keys overlap categories and must not be added as independent resident allocations.

| Package / category | Part instances | Triangle instances | Vertex references |
| --- | ---: | ---: | ---: |
| R101 L2, conservative immutable opaque candidates | 182 | 12,679 | 24,405 |
| R101 L2, protected opaque IDs below 250 | 102 | 9,004 | 15,773 |
| R101 L2, protected appended live-gate objects | 15 | 3,583 | 5,068 |
| R101 L2, sky | 1 | 136 | 97 |
| R101 L2, nonuniform transform, conservatively protected | 1 | 61 | 107 |
| R101 L2, punch-through | 33 | 2,438 | 4,191 |
| R101 L2, translucent | 27 | 3,260 | 3,676 |
| R103, conservative immutable opaque candidates | 30 | 2,230 | 3,898 |
| R103, protected opaque IDs below 250 | 189 | 31,616 | 53,091 |
| R103, punch-through | 32 | 7,004 | 12,838 |
| R103, translucent | 16 | 1,708 | 2,404 |

R101 has 223 placements, 204 meshes, 342 stored parts, 1,113 meshlets and 60,606 stored vertices. R103 has 134 placements, 134 meshes, 267 parts, 1,448 meshlets and 73,605 stored vertices. The conservative r101 candidate pool is about half its opaque triangle instances; the r103 pool is about 6.6%. These percentages do not imply proportional frame-time savings.

The protection rule is deliberately the same conservative ID/live-manifest boundary used by the existing static batching experiment. An ID below 250 does not prove that its placement moves: only unique IDs get runtime dynamic slots, and actual binding/state decides whether they move or hide. Broader coverage is possible after a room-specific lifecycle audit. It is not established by a still picture or by the object being stationary at spawn.

## The current POC is unqualified

The inspected r101 output contains 2,602 triangles, 6,071 packed vertices, 369 groups, 45 source materials and 107,169 bytes. Its mode is `material`: geometry is simplified, then triangle UVs/colours are reconstructed from nearby source surfaces. It reuses the original textures. It is not yet the proposed one-atlas baked shell, and 369 groups / 45 materials are not one draw. The converter also has an atlas-baking branch, but the inspected packed FSH1 uses material mode.

Concrete open issues in the inspected POC:

1. **Protected input is not excluded.** `fs_common.py:world_tris` includes all source placements. `fs_blender.py:build` filters opaque passes and applies `exclude_placements` only when the parameter exists. R101 `params.json` has no such parameter. Of its 47,231 opaque input triangles, 23,859 belong to the conservative protected set (dynamic IDs, live-gated props, sky, nonuniform placement). The packed file has no source-placement lineage, so this audit cannot determine how many survive simplification. It does establish that they were admitted to the source BVH and candidate surface. Runtime cutting all opaque placements can therefore suppress a live far object while the static replacement retains its rest appearance. Exclusion from the shell must be paired with leaving that object's live opaque rendering at Full distance.
2. **The source occlusion witnesses can change.** Even if moving/gated faces are excluded from output, using their closed/rest shapes as occluders when discarding unseen static faces can remove surfaces exposed by an open door, ladder/prop change or broken window. Only immutable occluders are safe for a first offline visibility reduction. A finite set of ray hits is also not proof that every unhit surface is invisible.
3. **Camera coverage is sampled, not bounded.** `fs_eyes.py` uses enemy route nodes plus 1.6 m and manually supplied extras. R101 has 106 eye samples, spanning x -51.165..39.372 m, y 1.6..11.1 m, z -29.526..32.749 m. These are neither all player locations nor the camera's swept volume. Aim/binocular views, camera collision, shoulder offset, upper floors, tower, windows and door approaches need explicit coverage. A shell at true surface depth provides parallax where those surfaces survive; it does not recover unseen back surfaces or disoccluded gaps by itself.
4. **The current seam is not hidden by Short fog.** Ordinary Short ramps over approximately 7.5..12.5 m. The POC deliberately retains Full's fog, whose extra far ramp is 20..25 m. The source fog/haze may still veil the seam, but it is not guaranteed to conceal a replacement at 12.5 m. Keeping Short's 100% fog at 12.5 m would hide the desired distant scenery too.
5. **Depth bias and coarse group admission need visible checks.** `far_shell.inc` selects a whole group if its box reaches beyond the cut; it does not clip each shell triangle to that cut. It scales reciprocal depth by 0.97 so source geometry wins overlap. That corresponds to about 0.39 m extra depth at 12.5 m and 0.77 m at 25 m. Foreground intersections, gaps, ground contact, alpha/effect overlap and fog lookup can change. Strips with any vertex behind the near plane are dropped rather than clipped. This is particularly relevant when walking close to a large group which still extends into the far band.
6. **Visibility and geometry tolerances are substantial.** Current parameters use `min_part=1500` mm, `max_dev` default 300 mm, 20,000 sampled directions per eye and no visibility dilation. Dropping a component below a 1.5 m bounding diagonal is not generally a few-pixel change at 12.5 m. The usual 50-degree vertical-FOV illustrative focal length is about 515 pixels at 480 lines, so 0.3 m transverse displacement at 12.5 m is about 12 pixels; this is an explanatory calculation, not a measured image error.
7. **Failure behavior needs an explicit Full fallback.** With shell mode enabled but a missing/invalid/unallocatable room file, the inspected runtime still keeps Full fog/PT/TR while cutting opaque geometry, and no shell appears. Unsupported rooms and failed shell loads should retain the complete qualified source path until they have a candidate, rather than silently giving a different partial-world look. The copied file's CRC also does not bind it to the specific source mesh/sidecar revision; include those identities in candidate admission.

The offline `work/r101/sheet4.png` was visually inspected. The Short+shell preview restores major far-building and fence structure that Short hides. It also shows visible geometric/texture differences from the Full preview. These Blender stills do not establish in-game equivalence, moving-camera coverage, effect compositing or timing. They are useful early look evidence only.

## Dynamic content and camera bounds

The blanket statement that chapter 1 has no moving far objects is not supported. `native_static.cpp:3797–3806` documents r100 gate swaps, r101 ladder/doors/dials and r105 puzzle/door motion. R101 source changes ladder state (`src/st1/r101.cpp:234–241`, `886–893`), enables/disables window damage, and changes the house door from open-lock to closed-lock (`920–943`). R103 source moves/turns the cesspit lid and hides its cover (`src/st1/r103.cpp:450–486`); item glow is also a live effect. Their distance depends on where the player/camera is, so none become static merely by being beyond the current cut.

The benchmark at the burning cross explicitly contains pyre fire, torches and moving haze/mist. Preserve all their live paths. Punch-through fences, foliage and translucent layers must retain their depth/alpha semantics; a colour bake of their current appearance cannot replace their holes, independent depth layers or animation. Sky/backdrop rows already have separate treatment and are not ordinary far opaque building geometry.

The existing SAT-floor sampler gives additional bounds, not a reachability proof:

| Room | Upward floor triangles | Approx. 1 m samples | XYZ bounds in metres |
| --- | ---: | ---: | --- |
| R101 | 180 | 23,926 | (-53.514, -0.100, -40.051) to (42.448, 9.000, 40.051) |
| R103 | 396 | 9,797 | (-51.457, -0.206, -38.347) to (13.575, 6.548, 10.223) |

The sampler includes every upward collision polygon, including any unreachable or broad proxy floor. Its finite samples cannot by themselves certify far-only geometry. Keep a conservative camera volume and treat uncertain faces as retained. Room transitions should retire the shell with its owning package; the destination starts with its own verified mesh identity, textures and camera policy. Full and unsupported rooms must remain valid without a shell.

## Lowest-risk bounded pilot

Start with a cross-local pilot, not an immediate whole-room guarantee. Use the exact accepted L2 package, its matching sidecar/IDs and append manifest. Select a small set of immutable opaque building/background clusters that stay beyond the replacement band throughout a declared camera volume around the cross. Keep the original source path outside that volume, during scripted camera states and for every protected or uncertain cluster. This first step avoids a moving near/far handoff until the surface approximation and cost are known.

The prototype recipe is:

1. Define the pilot from the benchmark cross (`pos -7914 0 2000`, facing 1.5708) plus measured camera matrices, lateral/forward/back movement and pitch/yaw extremes. The player's position is not the camera position. Use continuous-volume bounds or conservative geometry retention between samples. Begin with building walls/roofs and distant ground, keeping silhouette edges, door/window openings, thin fences and all gameplay objects unchanged.
2. Export only allowed placement/part/cluster IDs from the selected L2 data. Write a manifest containing source mesh/sidecar/IDs hashes, exact included and excluded ownership, material semantics, world-space bounds and source-to-shell lineage. Restrict occlusion pruning to immutable opaque blockers. Do not merge across portal apertures or disconnected depth layers.
3. Retain a real three-dimensional coarse surface per selected building/ground region; merge submission by atlas/cell afterward. A single enclosing backdrop or one camera projection will not preserve walk parallax. Keep all surfaces needed at the volume boundary. Preserve silhouette and aperture vertices before simplification; let the remaining interiors carry the large reduction.
4. Bake source texel colour multiplied by the selected prelit vertex colour into one initial 512x512 RGB565 VQ atlas, with adequate island padding. Runtime colour should not multiply that baked lighting again. The existing `tools/blender/bl_house_shell.py` and `tools/house_shells.py` already demonstrate shell baking, RGB565 full-codebook VQ packaging and decoded-texture previews; extend their source extraction to this PS2 prelit input or reuse the peer's bake branch. Do not introduce another renderer or asset format merely for convenience. If the single atlas cannot represent the allowed surfaces cleanly, reduce pilot coverage or price a second atlas; do not assume one room atlas preserves detail.
5. Reuse the existing direct opaque submission path or the qualified peer hook after it carries immutable ownership and source identities. Only the selected source geometry receives replacement; protected live opaque, PT/TR, effects, sky and actors retain their existing Full coverage. Keep the default off. Missing, mismatched or failed resources fall back to Full. Preserve existing room ownership, retirement, radio/subscreen and movie behavior, including the CPU baseline's movie-arena variant.
6. For whole-room expansion, qualify the moving near/far boundary separately: actual source/shell clipping, overlap, hysteresis and silhouette continuity. Do not rely on a 3% depth push and “fog hides it” as the acceptance criterion. The bounded first pilot can switch back to the source path before approaching any uncertain boundary.

This is intentionally a smaller opportunity than replacing every far opaque object. Its measurement answers whether a baked surface can provide a worthwhile gain without first depending on an unproved whole-room visibility set or live-object freeze.

## Memory budget and cost gates

The current CPU baseline log already contradicts treating the entire 8 MiB as free texture space. `hwmodel-cxt16base-cross/boot.log` reports:

* Texture pool 2,567,424 B; usable texture budget 2,444,544 B after UI/reserves.
* R101 frame 185 after preload: pinned 2,313,784 B, other 57,384 B, free 196,256 B, largest free block 12,288 B.
* Tick frame 767 retains free 196,256 B / largest 12,288 B, with 355 loads, zero evictions and zero retries in that log. This is evidence of this captured residency state, not a chapter-wide free-space guarantee.

For full-codebook VQ without mipmaps, a 512 square atlas costs 2,048 + 512*512/4 = **67,584 B** of payload; two cost 135,168 B. A 1024 square costs **264,192 B**, exceeding this captured free space. Mips, allocation alignment and reserves add to these figures. Original textures remain necessary near the player, so the atlas is generally additive, not a credit for deleting all originals. The 12 KiB largest block also means a 66 KiB atlas cannot be assumed to load late; coordinate early ordered preload/resident manifest packing with resident16, then verify actual allocation and lifecycle overlap. The material-mode peer shell adds no texture payload but retains its source textures and adds about 105 KiB of heap plus allocator cost.

Record shell mesh/metadata RAM, image/text/BSS growth and arena rounding, texture payload/resident/free/largest bytes, peak TA vertices/OPB, room entry/door/radio/movie overlap and reload counts. Keep zero refused required textures and zero in-game disc rereads. Any change to the 8 MiB partition is a separate measured decision; this pilot does not authorize shrinking TA banks.

Use four matched states on the same accepted stack, executable where runtime switches permit, assets, camera/input, cap and effect settings:

| State | Purpose |
| --- | --- |
| Full | Complete baseline with the accepted L2 geometry |
| Ordinary Short | Reproduce the user's exact distance policy; separate anchor, not the shell-cost subtraction |
| Full fog/live objects + eligible source cut only | Incomplete-picture diagnostic to isolate the candidate's removable source work |
| Same eligible cut + shell | Candidate appearance and total cost |

Shell cost is the last state minus the eligible-cut-only state. Net benefit is Full minus the candidate. Do not subtract the shell from the historical 7.9 ms or add independent per-piece/vertex estimates. Report complete drawn and skipped CPU, GPU/TA and paced gameplay/frame-rate behavior; all model numbers remain MODEL. Cache/layout/GPU acceptance needs the existing physical CONSOLE A/B requirement. This review requests no new model slot while the current pressure matrix runs.

Visual/gameplay gates must include matched frozen Full/candidate stills at the cross, approach road, left/right side steps, four viewing directions, building corners, house inside/outside, upstairs/tower, window/door apertures, an aiming/binocular view and the near/far boundary. Use both pre-bell and post-bell states, ladder and door/window changes, then bell completion and r101→r103→r101 travel. Add lateral walk video to reveal parallax/disocclusion and switching that stills miss. Near-world and protected-layer differences should be zero by ownership; far appearance is an explicitly judged approximation. Run the current gameplay-equivalence/decision gates and STRICT where retained logic permits, without treating masked unavailable records as unmasked identity. Include texture validation, full-Leon checks, H2/s30 and room/movie memory gates on the final candidate.

No far-shell performance or visual acceptance is claimed by this review.

## Evidence and reproduction

Own outputs:

* `C:/Game Dev/Emulators/_codex_cpu_t15_20261016/farshell-source-census.json`: input hashes, per-placement census, conservative protected rows, current peer runtime/asset hashes and flags, floor/camera sample bounds.
* `farshell-audit.py`: WSL stdlib parser using the repository's existing R4IM/R4PW readers; validates header/CRC correspondence. Run with WSL Python.
* `farshell-array-audit.py`: Windows NumPy supplement for the peer's NPZ/NPY source and eye samples. Run after the WSL census.
* `farshell-r103-floor-samples.json`: new read-only SAT sample output. Generated by the existing `tools/d367/worldlod/walk.py` from `/root/probe/lanes/ps2rooms/extract/work/r103/r103/r103_001.SAT`.

Source references: CPU `platform/native_static.cpp` around 3797 (dynamic ownership), 4146 (unique-ID slots), 4462 (world pass/cull), 4645 (live gates), 4655 (dynamic/source-hierarchy fallback), 4380 (sky); `platform/native_ps2_world.cpp` for source fog latch and final submission; `tools/ps2_world_spatial_batch.py` for conservative protected rows; `tools/ps2_world_far_lod.py` and `tools/d367/worldlod/walk.py` for existing offline geometry tools. Claude `platform/far_shell.inc`, its native-static/native-world hooks and the private `fs_common.py`, `fs_eyes.py`, `fs_blender.py`, `fs_pack.py` were inspected without edits. SHA-256 snapshots are in the census.
