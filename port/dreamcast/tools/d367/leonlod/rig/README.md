# LEON_LOD on the PS2 rig (lane leonlod, 2026-11-16)

Leon's reduced-detail rungs, made from the PS2 rig arm (`LEON_PS2_RIG=1`, `PS2_LEON_DIR=ps2leon-rig-20261026`), not from the
old pl08-era arm of 2026-10-15. Draw only: skeleton, animation, hit tests, game state and the hands are untouched. Default off.

Build: `python build_rig_package.py <rig arm dir> <work dir>` (host Python; the same private character-prototype tools as
`tools/d367/ps2leon/pack_arm.py`). Output `leon_lod.re4lp` goes into the disc data set `leonlod`
(`dc/native/pl00/leon_lod.re4lp`, tools/d367/test11/t11-fix.py) and is named by `LEON_LOD_PACK=` for the image header.

## Rungs (package order)

| level | name | what changes | triangles (all roles, hands included) | positions |
|---:|---|---|---:|---:|
| 0 | A | nothing (the PS2 rig Leon) | 5,155 | 3,115 |
| 1 | lg65 | legs 924 to 603 triangles, head attachment's never-seen triangles removed | 4,686 | 2,862 |
| 2 | bd70 | lg65 plus sleeves / body, jacket and knife to about 63 % | 4,004 | 2,494 |
| 3 | u70 | every role to about 65 %, face and hair too (not for close-ups) | 3,459 | 2,184 |

Face (role 3), hair (role 7) and the hands (roles 5 / 6) are the full PS2 meshes at levels 1 and 2. Level 3 is the 2026-10-15
pick and reduces them.

## Selection rule

- `LEON_LOD=<n>`: gameplay draws level n (boot level; `LEON_LOD_LEVEL` overrides). `LEON_LOD=0` is off and the image is identical.
- While an in-engine event or cutscene holds the game (`Status_flg[1] & 0x10000000`) the full level 0 is drawn; the switch is a
  ~0.1 MB read at the next actor retirement.
- A level change (warp `leonlod <n>`, `lodat`, the QA menu row LEON LEVEL) applies at the next room enter.
- Leon is 2 to 3 m from the camera in nearly all gameplay (over-the-shoulder), so there is no distance rule: a rung is a whole-model
  choice, loaded into one buffer (the size of level 0), not switched per frame.

## Reduction

`lod_mesh.py` collapses half-edges: a surviving vertex keeps its own PS2 position, weights, normal and UV, so no new bone
combination or UV drift appears. Seams, hard normals and role junctions (neck, wrists, jacket edge) are locked.
`vis-a.json` (per-triangle seen counts from the 2026-10-15 look study; same triangle order as the rig arm) marks triangles never seen.

## Memory

The role 0-4 / 7 arrays leave the image (`lod_pack.py derive`) and live in one `leon_lod::buf` of 97,056 B (level 0's size), in the
character data block. Under `LEON_LOD` the FTRV palette stream (`kSkinStream`) is 7,168 B instead of 24,576 B (the rig's level 0
needs 6,328 B; `lod_pack.py pack` asserts every rung fits), which brings the block back under its 16 KiB step.
