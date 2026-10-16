# World reduction look test, in game (2026-10-16)

The user asked: "I don't know if I trust the world approach. run a test." The world16 offline sheets were an offline
raster (no fog, no alpha, grey keys, poor cameras). This test shows the same cuts **in game**: Flycast, fog on, View
distance Full, real gameplay cameras, the same frozen frame for every arm. Only the world files differ between arms.

## Answer

**Don't trust the automatic cut on its own.** In game, the world16 cut (B) is bad in 4 of 5 rooms. It deletes or bends
the thin and nearby geometry the player sees up close: chair legs, a doorway corner, a cabin wall, barn beams,
gravestones, grass tufts, fence rails, tree trunks next to the camera, and the stake's crossbar.

Protecting landmarks (C) fixes most of that. But it also removes most of the saving. **B's modelled savings come from
exactly the structures it damages.** Once those are kept, C saves 0.4 to 2.2 ms per room (MODELLED, p90 view), where B
saved 5.2 to 8.3 ms. Even C still deleted the near tree trunks in r106 and the grass tufts in r108.

**Recommendation: tool plus a Blender touch-up, not the tool alone and not a full hand-model.**

- Let the tool cut terrain, rock and cliff faces. In these views those cuts were invisible.
- Have a person check each room's structures and thin props, and simplify them by hand where the frame rate needs it.
- Fix the tool so it never deletes a whole connected piece (a plank, chair leg, crossbar, grass card or trunk). Its
  protection also has to work per vertex near the walk path, because protecting whole bins does not isolate a
  landmark: r101's bins and clusters span tens of metres.
- Don't cut r102 at all. The 10-15 rule says rooms with no Ganados are not cut.

## Sheets

`C:\Game Dev\Emulators\worldtest-20261016\`

- `WORLDTEST-r101.png`
- `WORLDTEST-r102.png`
- `WORLDTEST-r106.png`, plus `WORLDTEST-r106-control.png`
- `WORLDTEST-r108.png`
- `WORLDTEST-r10a.png`

Columns are A | B | C. Each column is labelled with its arm, kept vertex share and MODELLED world ms against A.

## Verdict per room

| Room | B: world16 as built (kept, MODELLED ms vs A at p90 / worst view) | C: landmarks + gentler (kept, MODELLED ms) | What is visibly lost |
|---|---|---|---|
| r101 | world32 as landed, 0.62, -5.9 / -7.2: **visible but acceptable** | 0.63, -5.2 / -5.8: **visible but acceptable** | B (landed): the stake's crossbar, a long pyre plank, and the rails of the fence by the house (only posts remain). C3 brings back the crossbar and the plank (+0.7 ms); the fence rails are still lost. The road view is unchanged in both. |
| r102 | 0.37, -6.2 / -11.5: **bad** | 0.93, -0.4 / -2.0: **indistinguishable** | B: the dining chairs break apart (legs gone, backs bent) and the cave rock flattens. C: no visible loss, but almost no saving, and the room should not be cut (no Ganados). |
| r106 | 0.60, -8.3 / -10.8: **bad** | 0.87, -2.2 / -3.1: **bad** (at camera 3) | B and C: on the bridge (camera 3), the tree trunks and planks next to the camera disappear. Control N (same packaging, kept 0.97) keeps them, so the cut causes it, not the packaging. Cameras 1 and 2: B thins the branches slightly, C matches A. |
| r108 | 0.53, -6.6 / -8.0: **bad** | 0.84, -2.1 / -2.3: **visible but acceptable** | B: the r102 doorway corner leans, the ornate gravestone melts, the leaning gravestone and the iron gate are lost, the fence rails go and the grass tufts go. C: the grass tufts are gone; everything else matches A. |
| r10a | 0.63, -5.2 / -9.2: **bad** | 0.86, -1.5 / -2.9: **indistinguishable** | B: the cabin wall by the r109 door skews (window and corner) and the ruined barn loses beams. C: matches A (0.9% of pixels differ). |

The world16 cut does not make the targets either. The unbuffered 20 fps worst-view budgets (WORLD-BUDGET-BY-ROOM) are:

| Room | Budget | B worst view | C worst view |
|---|---|---|---|
| r106 | 6.9k | 12.6k | 19.7k |
| r108 | 8.0k | 8.3k | 13.4k |
| r10a | 6.9k | 12.3k | 18.1k |

Values are MODELLED world TA vertices in thousands.

## How it was done

**Build.** One ELF for every arm: `wtrT` is the t15/int 6153f987 trace arm (t15-build.sh rT, `WORLD_VERT=1
WORLD_VERT_LEVEL=5`, `PACE_MODE=off`). The arms differ only in the world files staged by each fixture (`mkfix.sh`):

- **A** is the current world. For r101 that is bake13, the pre-world32 data, with no variant 5, so the loader loads 0.
- **B** is world16 as built (`re4-assets-private/world16-ch1-20261016`). For r101 it is world32 as landed (wv32r101).
- **C** keeps landmark bins at level 0. A landmark bin is any single placement 0.3 to 25 m wide and at least 1.5 m tall
  (`landmark-bins.txt` per room). The gentler ladder is `--px 96 --max-error-mm 2500 --colour-guard 2 --colour-per-m 4
  --uv-guard 0.02 --uv-per-m 0.02`; B used `--max-error-mm 4000`.
  - px 48 and 96 and max error 1.5 to 4 m all gave nearly the same kept share once structures were protected
    (`price-1.json`: Cp48, Cp96, Cm25 and CB). The landmarks set the cost, not the level.
  - r101 C3 is the world32 recipe plus bins 0x10, 0x65 and 0xa4, plus a vertex box around the stake and pyre
    (`ladder_region.py`, `WT_PROTECT_VBOX`). A first try that protected those bins alone (`r101-binsonly`) did not
    bring back the crossbar: its clusters span tens of metres.

**Cameras.** Each run is a warp with `pos` and `ang`, View Full, `god` and freeze at tick 400. The r101 cameras are
world32's own (the cross, and the road at tick 270).

- Camera 1 is the door arrival position from the previous room (Leon's view on the main path).
- Camera 2 is the room's worst-projected view (roomproj's highest-TA sample).
- r102 camera 2 was recaptured at the merchant spot (em18). The first view (the r108 door) put the camera against a
  rock face.
- r106 has a third camera. Its worst view mostly faces a hillside, so the 2nd-worst view (the bridge) was added.
- I checked every sheet image. None is black, blank or inside geometry. Every B and C run logs
  `WORLDVERT ... loaded=5`; every A run logs `loaded=0`.

**Timing labels.**

- All ms values are **MODELLED**: the console-fit room model, 1.1 ms per 1k on-screen world TA vertices
  (room-budget-20261015 `roomproj.py` / `budget.py`), over 16 yaws at every door and enemy sample (`price2.py`). They
  are not console measurements.
- The fixed per-placement cost is not included. The spatial 32 m batching applied only in r101 and r10a.
- "kept" is the share of level-0 corners that remain after the cut.

**Caveats.**

- These are Flycast JIT stills. Flycast draws some console-only problems correctly.
- One run (r106-c1-B) logged a log overrun. It does not affect the still.
- Two or three cameras per room cannot show every loss.

## Evidence

- Runs: `C:\Flycast-Evidence\re4-dreamcast\worldtest-20261016\<room>-<cam>-<arm>`. Each holds run-output.txt, shots
  and disc.sha256; the discs were deleted.
- Tools: `_tools` (t-run.sh, q.sh, sheet.py, warps in `w\`).
- Code: branch lane/worldtest16 (port/dreamcast/tools/d367/worldtest16). Nothing lands.
- Private meshes: `re4-assets-private\worldtest-20261016`: r101 (C3), r101-binsonly, r102, r106, r106-N, r108 and
  r10a, with SHA256SUMS.
- Pricing: `price-1.json`.

## B: terrain/rock-only reduction (2026-10-16 evening, not landed; the user judges the sheets)

**Tool.** Branch lane/worldtest16 (commit 3978474f, plus the thin-edge guard).

- `ps2_world_vert_ladder.py --mode terrain` classifies each part, then reduces only the terrain parts.
  - A part counts as terrain if it is opaque, has planarity < 0.55 (the area share within 3° of its 6 main normal
    directions), and has at least 70% of its area in ground, cliff or rock-shaped pieces.
  - Every structure part keeps level 0. Structure covers walls, roofs, beams, planks, posts, furniture, trunks and
    cards.
- `--keep-pieces` (mesh_lod.KEEP_PIECES) never deletes or folds away a connected piece.
- `--keep-walk-mm 1500` stops vertices near the walk path from moving.
- Settings are otherwise the world32 L2 error settings.

**What was measured.**

- Sheets: `TERRAIN-<room>.png`, columns A (current, t15/int) | T (terrain-only), two cameras per room. All are in-game
  Flycast JIT stills: trace ELF w16mrT, WORLD_VERT=1 LEVEL=5, the same frozen tick in each row. Every T run logged
  `WORLDVERT loaded=5`.
- Cost figures are MODELLED (room-budget console fit, 1.1 ms per 1k on-screen world vertices, p90 / worst over the
  door and enemy samples). They are not console measurements.
- Pricing: `price-terrain.json`.

| Room | Kept | MODELLED world p90 A -> T | Worst view | Pixels changed (cam 1 / 2) | Verdict |
| --- | --- | --- | --- | --- | --- |
| r102 | 0.756 | 10.18 -> 5.96 (-4.22) | 18.54 -> 16.86 | 0.0% / 17.3% | Worth it. Only the cave rock is simplified: slightly flatter shading, no holes. The house is untouched. |
| r108 | 0.956 | 12.91 -> 11.90 (-1.01) | 17.07 -> 14.66 | 0.0% / 0.2% | Worth it. Small gain, no visible change. |
| r10a | 0.959 | 14.58 -> 14.02 (-0.56) | 22.83 -> 21.52 | 3.1% / 5.1% | OK. Distant ground is slightly smoother; small gain. |
| r100 | 0.960 | 15.81 -> 15.56 (-0.25) | 21.91 -> 21.26 | 3.8% / 0.0% | Marginal. The hillside is slightly smoother. The movie-layout caveat applies (the look test used plain wv5). |
| r106 | 0.985 | 19.69 -> 19.49 (-0.20) | 24.69 -> 24.35 | 0.2% / 0.3% | Not worth it: no visible change, but almost no gain. |
| r104 | 0.963 | 19.14 -> 18.99 (-0.15) | 25.69 -> 25.35 | 0.0% / 0.0% | Not worth it: almost no gain. |
| r103 | 0.980 | 17.96 -> 17.80 (-0.16) | 23.06 -> 23.04 | 0.0% / 0.0% | Not worth it: almost no gain. |
| r105 | 0.996 | 9.70 -> 9.67 (-0.03) | 31.44 -> 31.31 | 0.1% / 0.2% | No gain. |
| r107 | 0.996 | 29.69 -> 29.60 (-0.09) | 38.95 -> 38.91 | 1.1% / 0.0% | No. Camera 1 shows a sky sliver at the top of the cliff for a 0.09 ms gain. |
| r109 | 1.000 | unchanged | | | No runs: nothing is classified terrain. The output is larger, so the loader would fall back to level 0. |

**Conclusion.** Terrain-only reduction is safe, but it is cheap in effect too. Terrain parts hold only about 3-15% of
each room's corners. Only the r102 cave (-4.2 ms p90 MODELLED) and r108 (-1.0) gain enough to matter. The rooms over
budget (r107, r109, r104, r106) spend their cost on structure. That needs the manual (Blender) pass.

**Lesson from the r101 fence rails (added to B).**

- The rails sat in mesh 0x17, a house-front piece that is fused with the rest of the house.
- The ladder's piece-thinness guard measures whole connected pieces, and only within --thin-mm of the walk path. So it
  missed the rails.
- New option `--thin-edge-frac F`: a vertex moves at most F times its shortest edge, at any distance. Default off.
  Measured on r101:

| `--thin-edge-frac` | Kept | 0x17 rail-texture triangles in view (source 255) |
| --- | --- | --- |
| 0.5 | 0.923 | 239 |
| 1.5 | 0.725 | 155 |
| 3 | 0.657 | 137 |

- Hand protection of 0x17 alone (C16) keeps 0.652 and restores the rails in game. The guard is therefore not a cheap
  replacement.
- `--thin-mm 0` (the piece guard everywhere) changed nothing, because the pieces are fused.
- Terrain mode is immune: it classifies 0x17, 0x19, 0x63, 0x73, 0x75, 0x7c, 0x93 and 0xbd as structure and keeps them
  at level 0 (r101 terrain mode keeps 0.975).
- A sub-piece guard (splitting fused pieces by texture or plane before the thinness test) is the better next step.

Private data: `re4-assets-private\worldtest-20261016\terrain-<room>` (the wv5 mesh, class.json, L2.json, job.log,
SHA256SUMS). Runs: `C:\Flycast-Evidence\re4-dreamcast\worldtest-20261016\t-<room>-<cam>-<A|T>`.

## Next: the Blender pass, top 3 rooms by structure cost (10-16)

All figures are MODELLED (not measured): 1.1 ms per 1k on-screen world TA vertices, over the price2 view samples (door
arrivals and enemy set positions with 16 yaws each, plus the sheet cameras) on the shipping level 0. A part counts as
"structure" when terrain mode classes it so. Script: `scripts/price_struct.py`; data: `price-struct.json`. r101 is
left out because it already ships the reduced world32/C16 set.

| Rank | Room | World p90 / structure p90 | Worst view / structure in it | Structure share | Note |
| --- | --- | --- | --- | --- | --- |
| 1 | r107 | 29.82 / 29.05 ms | 38.95 / 37.80 ms | 0.96 | Canyon sight lines; worst world of chapter 1 |
| 2 | r109 | 24.88 / 24.40 ms | 34.97 / 33.73 ms | 0.97 | The cabin: almost everything is structure |
| 3 | r104 | 19.19 / 17.74 ms | 25.68 / 23.32 ms | 0.90 | Next are r106 (17.21 p90) and r103 (17.17); r105 has one 28.74 ms worst view |

Terrain mode cannot help these rooms. Structure is 90-97% of their world cost.

## Lost-part check (required gate for any reduced world; coordinator 10-16)

The tool is `scripts/lostpart.py`. It runs offline in about 20-90 s per room. There is one verdict per set:
`lostpart/<set>.txt` (PASS/FAIL list), `<set>.json` (every piece's numbers) and `<set>-flags.png` (thumbnails).

**How it works.**
- Every original (placement, part) is split into connected pieces. A part is one texture of one mesh, so fused meshes
  split by texture first.
- Each piece is compared with the reduced world's triangles of the same texture, so batched outputs need no part
  identity.
- **Silhouette test:** X, Y and Z silhouettes at 128 px on the piece's longest side. With no back-face culling, the +/-
  views of an axis are identical, so the 6 axes reduce to 3.
- **Walk-path cameras:** the room's sheet cameras, door arrivals and enemy set positions, at 8 yaws each, 320x240,
  clipped at the near plane. Each piece is checked against reduced triangles of its own texture, so a changed occluder
  is not counted as a lost part.
- A piece is flagged FAIL when any of these holds:
  - its coverage drops below 0.90 and the loss is at least 4 px² on screen at its walk-path distance;
  - its thin pixels (what a 3x3 opening removes) keep less than 0.75;
  - a camera loses at least 20 px of it and keeps less than 50%.

**Validation.** Original = crowd12 bake13 level 0; reduced = each set's ps2-wv5.

| Set | Flagged of 4494 | Stake crossbar 0xb9 | Pyre planks 0x75 (6) | Fence rails 0x17 | Gone completely |
| --- | --- | --- | --- | --- | --- |
| self (original vs original) | 0 (PASS) | pass | pass | pass | 0 |
| test 15 wv32r101 | 1657 | **FLAG** (cov 0) | **FLAG** (cov 0) | **FLAG** (87) | 382 |
| test 16 C (C4) | 1598 | pass | pass | **FLAG** (87) | 358 |
| test 17 C16 | 1511 | pass | pass | pass | 349 |

- The check finds all three known losses and clears them where the sets fixed them.
- **C16 does not pass.** 464 pieces are flagged by both the silhouette test and the cameras, mainly beams, planks,
  posts and boards (bins 0x7c, 0x75, 0x19, 0x1f, 0x73, 0x1a, 0xf, 0xe).
- An in-game pair confirms it (`lostpart/r101-C16-ingame.png`; same ELF, original world vs C16):
  - at the em15 position, the slanted roof/fence beam is gone;
  - at the r102 door, the fence boards and a post change.
- So the shipped test 15/16 worlds, and C16, lose structure away from the cross.

**Terrain sets (test 17 candidates, held):**
- **r102:** FAIL, 5 rock pieces, all terrain. They keep 0.85-0.89 of their silhouette (the "slightly flatter" cave).
- **r108:** FAIL, 31 pieces, all classed terrain:
  - the dead trees (0x72) lose thin branch tips;
  - nine 0x4e strips (12 triangles, about 2 m) vanish completely, and the em17 cameras show them (up to 1003 px).
- **r10a:** FAIL, 24 pieces. Its trees (0xa9, 0xab, 0xac) are classed terrain and lose their branch tips.
- **Root cause:** the terrain classifier counts trees as terrain (irregular and large), so a structure test needs
  "thin branches" as well.
- **r102 seam:** the merchant-cave streak stays with `--lock-borders` (`TERRAIN-r102-c2-locked.png`). It is not an
  open-border crack; most likely it is a sliver triangle stretched across a UV seam on the fold. Coverage cannot see
  it.

**Other gates on the held terrain data** (land17 = t15/int d7c4c0a3 + wt17terr; ELFs w17trT and w17tmW):
- STRICT + decisions r102/r108/r10a: MUST-IDENTICAL, drift 0.
- TEXCHK/LEON-GC: PASS on all 6 runs.
- KOS/GDEMU: not run. fp_twin refuses a twin of a build made from a dirty tree.
