# Salazar complete source requirements — 2026-10-19 (H-037)

The retained full source data has four separate admission dependencies: complete texture facts, authored position scale, original alpha/material behavior and backing size. Its attached weak point also needs typed object ownership. No converter, renderer, guard, recipe or game program was changed. No new model level or Flycast run was made.

## Complete roles and source identities

Both original archives are pinned: PS2 em38.dat `f356533a4f7fe3df7ed2a98d37a3ae5323aaf1358adc532e8b6ea4a9d0026b14`; GC em38.drs `4c43af7d0c7fb65eb56c321d9d7a6d7a4828210ed5ecd234ea6cf6647efb005d`. Six source BINs, three TPLs and every original material record remain complete.

| Full source role | BIN / TPL | Owner parts / infos | GC source shift / retained native shift | Complete TPL images | Current generator result |
|---|---|---|---|---:|---|
| Queen body | 4 / 8 | 59 / info 0 | 0 / 1 | 34 | Original mask/source pass needs material contract |
| Queen added eye | 9 / A | Same 59-part owner / info 1 | 1 / 1 | 2 | Included in Queen refusal; PS2 eye alpha remains required |
| Tentacle types 1 and 2 | 5 / 8 | 19 / 1 | 0 / 0 | 34 | Position shift 0 outside 1..4 |
| Upper Salazar type 3 | 6 / 8 | 21 / 1 | 3 / 3 | 34 | Original mask/source pass needs material contract |
| Roots type 4 | 7 / 8 | 21 / 1 | 0 / 0 | 34 | Position shift 0 outside 1..4 |
| Attached weak object 00 | 51 / 52 | 1 / 1 | 0 / 4 | 1 | Full data emits; typed ObjMgr owner is absent |

The original source TPLs contain **37 unique texture facts: 34 + 2 + 1**. A separate big-endian header/payload/key parser reproduces all 37 existing 68-byte fact records. Six incomplete fact lists fail the exact-count comparison; a changed final key differs from the original. These are source-comparison controls, not generator admission tests. Original source material facts total 156. The boss-only counts are below the existing total fact capacities of 64 textures and 224 parts under ROLES5; other room cast is excluded here. The separate per-role maximum is still 23.

TPL8 cannot be replaced by its first 23 images: Queen materials reference diffuse 32 and bump 33; upper materials reference diffuse 30 and bump 31. Original GC upper materials also reference diffuse 28/opacity 29, even though the PS2 replacement mesh does not sample that pair. Source identity facts and replacement atlas usage are different contracts. Preserve all source entries and indices.

## Material and source-scale requirements

Queen body uses PS2 partial diffuse image 16 with separate opacity image 17; upper uses diffuse 26 and opacity 27. The eye uses partial diffuse 0 and separate opacity 1. PS2 eye material flag is 4, while its GC counterpart is 3. The H-029 authored footprint proof preserves these identities and all original corners. It establishes sampled diffuse-alpha coverage, not the original GS ALPHA/TEST equation or final rendered equivalence.

No opacity image is silently substituted for diffuse alpha. GC mask/source-pass facts, source bump/specular indices and PS2 replacement material records remain explicit. The probes use the existing documented source-only bump drop, with no new material approximation or alpha substitute. Queen and upper therefore stop at the real material contract before reaching the later 34-image package check. Their current refusal must not be reported as a fresh fully emitted 34-image package rejection.

The retained tentacle and roots native streams use authored shift 0 and are rejected before package emission. Descriptor low bits 0 currently mean legacy shift 4. The P2 scale contract from H-036 therefore applies here too; changing only the 1..4 guard would draw the wrong scale. All six unchanged native source infos pass preflight. No re-quantization or source geometry change was attempted.

## Full backing does not fit the unchanged layout

Using the current v1 aligned array layout, exact complete-geometry deduplication and unchanged skin streams:

| Full source info | Aligned geometry bytes | Skin bytes |
|---|---:|---:|
| Queen body | 259296 | 6264 |
| Queen eye | 2464 | 40 |
| Tentacle shared by types 1/2 | 28544 | 1856 |
| Upper | 79104 | 3840 |
| Roots | 58144 | 2104 |
| Weak object | 1888 | 40 |

Geometry plus skin totals **443584 bytes**, already 17600 above the unchanged **425984-byte** package-plus-skin ceiling. This is a lower bound for retaining these complete source forms in one v1 package. It excludes metadata and final alpha-run storage. It is not an emitted complete package, an actual heap failure or a claim that all forms draw concurrently.

Do not raise the arena, remove source forms, introduce phase streaming or invent a lighter level from this inventory. The existing P2 owner must qualify the complete source/data-layout contract. I-013 still requires a qualified whole-fight projection before a new g50; whole-fight remainder U remains missing.

## Weak object: prepared data is not ownership

Original em38.cpp creates BIN51/TPL52 through SetObj00, scales it by 1.3, sets LightInfo.EnableMask to 0x80 and attaches it to original part 0x3a. Shell-open status 0x04000000 and body health control visibility. SetObj00 uses ObjMgr.create(0); obj00 follows its parent and is destroyed with it. This object is distinct from player id 0 and must not borrow that ownership.

The existing source_actor_owner_hooks kinds cover Garrador core 0x16 and flying head 0x01, not this object. The P2 owner needs original ObjMgr lifetime, parent transform, lighting/visibility, texture preparation, skin lease and source pass ownership. The weak point and its hit/attachment systems remain full.

Current source 269a23fe emits the weak-only preparation package, 2720 bytes, SHA256 `b5e1df28ab0983d9ac7116a0a65e020620d85fbd5e3c1f46663b1df202d6058c`. Eight checks pass against the actual target package validator under ASan/UBSan: valid data plus malformed room, magic, reference geometry, texture size, owner root, owner bind and role texture count. No sanitizer stderr. This is not a full r228 cast package, native drawing, arena qualification for the fight or a shipping selection.

## Handoff

Coordinator routes the existing character renderer/registry owner in P2 for complete 34-image roles, compatible source shift 0, original material/eye-alpha support, complete backing and typed weak-object ownership. Preserve source parts, collision, animation, attachments, visibility, lighting and live event selection. No enemy-id substitution, source subset or new room format is needed.

Original animated retarget poses, actual GS/look, all-live/all-drawn proof, whole-fight cost, resident textures, VRAM, 48 KiB KOS, STRICT/decisions, route and knob-off image gates remain open. Settled Gigante/twins/Del Lago selections are untouched.

## Private receipt

`boss18-salazar-role-contract-20261019`: 106 files / 9097852 bytes. SHA256SUMS `1e3c63d9694d6ff457f79b212e911d438f2da15b3c6977a6892dfc0a270d6809`. Immediate C mirror byte-verified. Original full source and H-029 sets are unchanged; owned host executable was pruned with a deletion manifest.

Evidence: `C:/Flycast-Evidence/re4-dreamcast/boss18-20261018/salazar-role-contract-20261019/`. Public hash-only reference: `tools/d367/boss18/salazar-role-contract-20261019.json`. No original BIN/TPL, generated header, texture or media enters Git.
