# Garrador material evidence (I009, 2026-10-19)

The reported black polygons are r201 room alpha geometry with a missing texture
pair. They are not a Garrador hood/mask error. Restoring the exact original room
pair removes them at the same source frame, with the full character package and
program unchanged. The core glow remains unresolved: two colour bakes and an
all-white texture control do not reproduce the lower GC orange/red highlight.
Neither bake is a user-look candidate. AUX_OBJ_NATIVE stays 0 in recipes.

## Concrete room-data fix

Apply the additive fixture fragment
tools/d367/boss18/r201-room-alpha-pair.json to a complete, program-retargeted
r201 fixture. The key is dc/tex/a/a7ed275f-c2425e1d.re4tex, 8336 bytes,
SHA256 1c2743e6dd88bf83ae490404b2f7ee803e431df8bef50df32ab65bc91de44b60.
The already-verified input is in the root textures/ directory of
/root/re4data/private/castle18-ch31-source-pairs-20261019 and its immediate C:
mirror. Do not confuse it with files/. This reuses Castle's conversion; no
duplicate conversion, source fallback character or new geometry is installed.

The source is original GC r201.das ARC9/TPL2+3, colour284d87de-1cc4a313 and
mask86ac6830-98755031, archive SHA256
57009ea20c309a9eac3de0eaf3333cd1a761011af7c689eba112242e771ff587.
The existing converter preserves alpha exactly; ARGB4444 colour quantization
has max14 RGB error. It is room data, not the dungeon key or Garrador body.

The reported old c0/c1 stills both logged this missing pair. The current missing
control reproduces the same black polygons. The restored control removes them:
TEXCHK last summary598 failures versus0. Both use identical AUX0 program and
original full r201 package e8b494ffa01b4f39fff55b13512f1a5e44b54a8a2903911191875840f03e4123.
All used PS2 body diffuse images0/1/3 are opaque (rawalpha128); image2 is unused.
All source UV corners are legal; original source/packed rest views agree.
No body triangles, alpha modes, source facts or accessories were removed.

## Current bounded runtime proof

Exact source is 283bc363 (be416f5a merged); helpers/specs do not change runtime.
Both arms include LEON_SKIN_SLOTS=2, LEON_HEADLESS=1 with the original garr18 neck
data, LEON_CLOTH_DRAWN=1, current Test18 diagnostic extras, and actual KOS49152
hold. AUX0 b18aerT ELF:
1d64bb023025af142634d9e77688632ed244d9c32367393f589cae72a6a665b7.
AUX1 b18afrT ELF:
941683dacbc81192c9281c4759e244fa4dd8de25828bb9d659961313d5c1c9e5.
Boot and all overlays are byte-bound to each staged candidate.

The retained garr18 core-view initial position, ordinary idle/no flags or
damage rig is used. Source hold500, last completed LT499 before and after each
read-only VRAM capture, is proven in each capture/held-source-500 directory.
Every restored-vs-missing/broad/local/white pair passes STRICT and
MUST-IDENTICAL for320 room ticks180:499: zero drift, gaps or masking.
Decision counts are49776 em-em,10549 linequeries,638 area,4466 damage.

All actual emulators run less than60 seconds (55-second budget), through
trace_lock with release priority, at most2 owned. The restored/native trials
have TEX0, HALT/FAULT/MISSING0. Leon and full Garrador each have450 native/0GC
census counts; AUX1 full core448/0, no native decline. NOT-DRAWN passes with
zero live boss rows in this idle rig: it is not proof of fight activation.
The overall firstpass is UNPROVEN because no traversal/short-walk gate is
attempted. Headless appearance is not triggered in this material rig.

At the f181 preload snapshot, all arms report pinned1245280,dynamic0,
other57344,free1264800,largest1232896,evicted0,retries0. This is not a steady
fight residency result. Heap4 water min/largest1731104; actual49152KOS held.
Observed minimum KOS headroom is38280 restored and37224 in native colour
trials. Late loads, complete fight/residency, death/grabs/movies, r218 current
bake runtime, fresh Disc1off identity and console performance are not accepted.

## Core texture trials and boundary

| Source/model | Bones / parts / infos | Full geometry | Special systems | Current exclusive draw / logic MODELLED |
|---|---|---|---|---|
| Garrador body typeA (r201), typeA/D (r218) | 38 /38 /1 | 1993 or1989 triangles, unmodified PS2 source | Original grab/head loss, hearing/AI, back weak collider37, death/event handoff | Unpriced on these exact builds; no aggregate actor split |
| Independent core cObj16 type4 | 14 /14 /1 | 491 PS2 triangles,701 native strip vertices | Attach original body36; original motions229/22A; source weakpoint/effects | Unpriced; no performance gain claimed |

Original GC core has929 triangles; original PS2 full core491 is source geometry,
not a new reduction. Bone IDs/parents/rest are exact; original static
PS2-to-GC surface max3.429mm, reverse13.827mm (not animated look acceptance).
Original GC material flags3 include bump1+specular, power0x46/0x32. The native
path has no equivalent specular stage. No runtime lighting or material gate
was changed here.

Both rooms have rebuilt, target-host-checked full packages. Broad texture key
af47a27e-0a4966f0 warmed the wrong upper surfaces; withdrawn. Localized key
5aa31dca-5029ba64 uses the original core UV chart and central bone1 surface,
preserving shared chart uses and sampler gutters. It still fails to match
the lower source glow; withdrawn. The generators are retained only for
reproduction. Both formats remain256x128 VQ RGB565/10240VRAM bytes.

All non-texture binary sections (including descriptors, refs, geometry, blobs,
source model/part/TPL facts, roles, parents and binds) are byte-exact with the
original full packages. Arenas remain241952(r201)/239408(r218), below425984.
Each bake passes16 actual target positive/corruption/owner controls across
both rooms. No capacity, source contract or allowlist was relaxed.

The c3ca2c60-6afd9488 white control fills every atlas texel including padding.
Only the texture record/content identity and package checksums change; the
actual target checker passes. In the same-source capture, upper native lobes
become white but the lower source-glow region remains black. This bounds the
texture-only approach under unchanged geometry/material/lighting. It does not
uniquely distinguish a zero diffuse/specular-only surface from occlusion.
The smallest next ownership question belongs to coordinator/garr18: inspect
native core source-part coverage and lighting for that lower region. Boss18
does not implement an engine solution under I006/I008. The original AUX0
source core remains the current path; no new user look choice is ready.

## Retained evidence and data

C:/Flycast-Evidence/re4-dreamcast/boss18-20261018/:
- garrador-black-polygons-roompair-proof-20261019.png (corrected causal still);
- garrador-core-source-native-bake-20261019.png (full views/details);
- garrador-core-white-texture-limit-20261019.png (source/local/white details);
- garrador-core-texture-limit-proof-20261019.json and per-arm STRICT/decision
  reports, source-hold proofs, exact staged manifests and actual capture logs;
- h-b18garrador/scenarios/cx-r201-i009-{missing,restored,corebake,corelocal,corewhite}-c.

New private set /root/re4data/private/boss18-garrador-material-20261019 and
C:/Game Dev/Emulators/re4-assets-private/boss18-garrador-material-20261019:
457 files23624547 bytes, SHA256SUMS
a4d37c58d95d37d00ad2cd322cc0b12ec2814d6cd889ad65bd1429ed504234ef
before final report-only additions. The original Garrador541-file set and
Castle room pair are unchanged. Every verified addition is immediately
mirrored. No game bytes or stills are committed to source.

No recipe, runtime code, gate or default changed. No integration, release,
tag, PR or public media. H020 twins user choice remains separate and ready;
this material milestone does not complete the boss track.
