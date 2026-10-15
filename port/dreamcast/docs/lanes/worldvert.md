# Lane worldvert: wholesale world vertex levels (r101 first)

Status 2026-10-15 19:25: HANDED OVER (the user moved CPU/rendering optimization to another team). Branch
`lane/worldvert` (local, not pushed), worktree `/root/probe/lanes-20261015/worldvert`, work dir
`/root/probe/lanes-20261015/worldvert-work`. Base: `wip/lanes-20261015-worldlod-20261015-1740` (b933f62a, the
worldlod WIP snapshot on top of lane/worldlod 6f3defad, itself on the test 13 merge 1c79d543).

## What it is

A render-only, default-off world reduction. It is not a far LOD. Every PS2 world cluster's level 0 is REPLACED by an
error-bounded simplification. The data ships as extra level files beside the source package, and the runtime picks one.

### Converter: `port/dreamcast/tools/ps2_world_vert_ladder.py`

- Simplification is `mesh_lod.py`'s half-edge collapse: every surviving vertex is an original PS2 vertex.
- UVs and textures are unchanged; the UV guard and vertex-colour guard are on.
- Cluster borders and material seams (positions shared between parts of a mesh) are locked, so neighbouring clusters
  never crack.
- Collision is untouched (a separate file).
- The output keeps the mesh / part / placement / cluster records, so the source R4PW sidecar and ids file still match.
  Run `ps2_strip_groups.py` on each level afterwards.

Error bound (screen space from the gameplay camera region):
- Cluster mode (default): `P px x max(cluster's distance to the nearest walkable point, --min-eye-mm 1500) / focal 514.7`.
  The walkable points come from `tools/d367/worldlod/walk.py` (PS2 SAT floors).
- `--per-vertex`: the same bound per vertex, using a 0.5 m chamfer distance field of the walkable points plus a camera
  height band (0..3.5 m). This is needed because 491 of r101's 535 clusters touch walkable ground (cluster distance 0).
- `--thin-frac F --thin-mm M` (per-vertex mode): a connected piece within M of the camera region never takes more error
  than F x its middle bbox extent. This is the sliver fix: posts and planks next to Leon can no longer collapse.
- Guards loosen with distance: `--colour-guard C --colour-per-m c` and `--uv-guard U --uv-per-m u`.
- `--max-error-mm` caps the error at any distance.

Other knobs:
- `--protect-bins` keeps landmarks by mesh bin (r101: 0x2d, the well). `--protect-last N` keeps the N baked
  STATIC_OBJ_BAKE objects (r101: 14); their bins repeat 0x0.., so `--baked 14` excludes them from `--protect-bins`.
- `--target-share` bisects P so the TA corners of the clusters within `--view-mm 25000` of `--eye` (the bench camera)
  reach that share of level 0.
- `--repack --let-verts N`: re-emit every cluster's level 0 in N-vertex meshlets (`--px 0` = the same triangles). This
  was the first, crude form of plan step 4.
- Also present, but found too costly: `--lock-borders`, `--border-px` (mesh_lod `BORDER_EPS`), and `--near-px` / `--near-mm`
  (cluster tier). On r101 they cost 15 to 25 points of reduction.
- `mesh_lod.py` gains `BORDER_EPS` and `VERTEX_EPS`. Both default to None, which keeps the historical behaviour.

### Runtime: `WORLD_VERT=1` (`game30.mk`; `native_static.cpp`; default 0, so the image is unchanged)

- `WORLD_VERT_LEVEL=n` makes the package open load `/cd/dc/native/rXXX/ps2-wvN.re4mesh` (and `ps2-wvN.r4sg`) instead of
  `ps2-world.re4mesh`. The file names use one dot because ISO9660 rejects two.
- Memory neutral: the heap-4 blocks are always sized by the level-0 file, and the sidecar sits at the same offset. A
  missing or larger level file falls back to level 0. The `WORLDVERT room= want= loaded=` log line reports which level
  is resident. The heap after open was identical at every level (3,343,328).
- `re4dc_world_vert_level_set(n)` swaps a resident package IN PLACE (mesh plus strip groups into the same blocks; the
  sidecar, ids, baked-object gate and area hides are unchanged). It is meant for bench rows and is NOT EXERCISED YET.

## Data (private, never committed): `C:\Game Dev\Emulators\re4-assets-private\worldvert-20261015\`

The source for every level is `crowd12-bake-20261015\r101-t13` (bake13, the test 13 r101 package).

- `r101-v1\`: the checkpoint ladder L1 / L2 / L3 as ps2-wv1..3 (plus the reports L1..3.json/.log). The settings are
  inside each .log summary:
  - L1: px 56, colour 2+4/m, uv 0.02+0.02/m, maxerr 3000.
  - L2: px 96, colour 3+8/m, uv 0.03+0.05/m, maxerr 4000.
  - L3: px 200, colour 4+16/m, uv 0.05+0.1/m, maxerr 6000.
  - All three: cluster mode, `--protect-bins 0x2d --protect-last 14`.
- `r101-v2\` (what `t11-fix.py` data set `wv101` stages now):
  - wv1 = L2-fixed: L2 settings + `--per-vertex --thin-frac 0.5 --thin-mm 2000`.
  - wv2 = L2-fixed + `--repack --let-verts 256`.
- `r101-scan\`: the sliver-fix candidates q96 / m35_2 / m50_2 (look scans only; data set `wvscan`).

Regenerate L2-fixed (WSL, from `port/dreamcast/tools`):

```
B=".../re4-assets-private/crowd12-bake-20261015/r101-t13"; W=/root/probe/lanes-20261015/worldlod-work/walk/r101.json
python3 ps2_world_vert_ladder.py $B/ps2-world.re4mesh L2F.re4mesh --sidecar $B/ps2-world.r4pw --walk $W \
  --protect-bins 0x2d --protect-last 14 --colour-guard 3 --colour-per-m 8 --uv-guard 0.03 --uv-per-m 0.05 \
  --per-vertex --thin-frac 0.5 --thin-mm 2000 --max-error-mm 4000 --px 96 --report L2F.json
python3 ps2_strip_groups.py L2F.re4mesh $B/ps2-world.r4pw ps2-wv1.re4mesh ps2-wv1.r4sg
```

The walk file `r101.json` comes from `python3 tools/d367/worldlod/walk.py <r101_001.SAT> r101.json`.

## Results

All counts below are FLYCAST: PS2MESH TA world vertices per frame, from frozen frames (global tick 700) with the
village emptied. Nothing has been priced: there are no MODELLED or CONSOLE numbers yet.

| Camera | L0 | L1 | L2 | L3 | L2-fixed |
|---|---|---|---|---|---|
| Cross (bench) | 17.70k | 13.73k | 12.12k | 10.33k | 12.60k |
| Facing away | 11.31k | 9.57k | 7.71k | 6.12k | 7.94k |
| Side | 14.17k | 11.08k | 8.95k | 7.85k | 9.72k |
| Worst (em28) | 24.63k | 20.12k | 16.69k | 15.97k | 18.47k |
| Typical (door from r100) | 11.89k | 11.03k | 8.07k | 7.41k | 8.29k |
| Approach 16 m | 21.68k | 17.86k | 14.78k | 12.69k | 15.63k |
| Approach 10 m | 25.37k | 20.50k | 17.06k | 14.93k | 18.56k |
| Approach 5 m | 21.86k | 17.51k | 15.48k | 13.11k | 16.55k |
| **Mean** | **18.6k** | **15.2k (-18%)** | **12.6k (-32%)** | **11.1k (-41%)** | **13.5k (-28%)** |

- Package sizes (B): L0 1,283,520; L1 1,036,192; L2 840,704; L3 810,784; L2-fixed 907,520.
- The -55% level is not reachable without unlocking cluster and material borders (design question). Even with every
  guard off the floor is about -50%.
- Defects seen at the checkpoint:
  - L2 / L3 at approach 10 m: a wooden post next to Leon collapsed, and a light sliver showed through the dark wall.
  - L3 at approach 5 m: a hole in the ground near Leon.
  - L3: a displaced window shutter at the worst view, and a wall section opened at approach 16 m.
  - L1: clean.
- **User verdict:** "Village L2 salvaged". L2 is the r101 target and L3 is dropped.
- **L2-fixed:** the approach-10 m post and sliver are back to the L0 look (a2-S3 / a2-F). The other 7 L2-fixed cameras
  are captured but NOT yet reviewed crop by crop.
- **Bigger meshlets (wv2):**
  - 804 meshlets instead of 1,335. The a2 frame is pixel-identical to L2-fixed (the cross frame differs only where the
    fire animates).
  - BUT the TA vertices submitted rose: cross 12.6k to 15.5k, approach 10 m 18.6k to 21.3k. Longer meshlets stripify
    worse.
  - So the net effect needs pricing (setup saved vs extra TA corners). That is exactly the measurement plan step 4 asks
    for.
  - Plan step 4's real design (merge compatible pieces within spatial cells, same material/state, in the same converter
    pass) was NOT started.
  - Repacking L0 itself grows the package (+67 KB), which would break memory neutrality.

## Sheets

- `C:\Game Dev\Emulators\worldvert-20261015\WORLDVERT-R101-CHECKPOINT.png` (+ .html): L0 / L1 / L2 / L3, 8 cameras,
  risk crops.
- `C:\Game Dev\Emulators\worldvert-20261015\WORLDVERT-R101-L2FIX.png` (+ .html): L0 / L2 / L2-fixed / L2-fixed with
  big meshlets (the big-meshlet column covers cross and approach 10 m only). Not yet shown to the user.

## Gates

No gates have run. These are still open:
- knob-off identity: WORLD_VERT=0 must give the wlirP image ba9f5f9f / test 13 c1ae83dd;
- TEX check;
- KOS squeeze, 5 segments. `_end` is 8c4240bc with WORLD_VERT=1 against 8c423f3c knob-off on the cost recipe:
  +0x180 B of code, no data;
- STRICT fight / bell / door103 (render only, so it should be identical);
- align 0;
- the `re4dc_world_vert_level_set` runtime swap.

## Exact next experiment

1. Review the L2-fixed crops on `WORLDVERT-R101-L2FIX.png` and send the sheet to the user.
2. Price L2-fixed: `bash worldvert-work/hw.sh wv1 wvF-cross cross` and `... wv1 wvF-house house` against
   `wv0 wv0-cross cross` / `wv0-house house` (MODELLED, then world x1.23).
3. Calibrate against CONSOLE: the 12.5 m cut saved -7.9 ms at the cross; the slope is about 1.0-1.6 ms per 1k world
   vertices.
4. Price wv2 (big meshlets) the same way, on top of wv1.
5. Then run the gates above, then POC102 on lane/poc101 (a row per level + ALL ON), then the worst-first rooms with the
   L2-fixed settings.

## Commands

All helper scripts are copied in `port/dreamcast/tools/d367/worldvert/`; the warps are in `.../worldvert/warps/`.

- Build: `bash /root/probe/lanes-20261015/worldvert-work/build.sh <label> WORLD_VERT=1 WORLD_VERT_LEVEL=<n>`. This is
  the worldlod wlcrW cost recipe; `BASE=play` gives the wlirP play recipe.
  - Built arms: wv0 33dcf2d0, wv1 3436e8ac, wv2 25f2caf4, wv3 5e5bfe75 (`_end` 8c4240bc).
  - With r101-v2 data, wv1 = L2-fixed and wv2 = big meshlets. wv3 has no level file now, so it falls back to level 0.
- Fixtures: `python3 tools/d367/test11/t11-fix.py wv<n> <out.json> --data <T13 list>,wv101 --warp <abs warp path>`. The
  warp path must be absolute.
- Look runs (Git Bash): `MINGB=18 bash C:/Flycast-Evidence/re4-dreamcast/worldvert-20261015/_tools/qlook.sh <jobs file>`
  (lines `<run> <label>`; 2 at a time, 60 s each). `wv-run.sh` deletes each staged disc and keeps `disc.sha256`.
- Sheets: `python checkpoint.py` / `checkpoint_l2fix.py` / `sheet.py` in that `_tools` folder.
- hw model: `bash worldvert-work/hw.sh <label> <name> <cross|house>` (`bench-hw.sh`, window 500:799, stride 30).

## Evidence

`C:\Flycast-Evidence\re4-dreamcast\worldvert-20261015\`:
- runs `<cam>-L0..L3` (checkpoint), `<cam>-F` (L2-fixed), `vc-FB` / `a2-FB` (big meshlets), `a2-S1..3` (sliver
  scans);
- the `_tools` scripts, `jobs*.txt` and `qdone.txt`.

No discs are left. No jobs are running.
