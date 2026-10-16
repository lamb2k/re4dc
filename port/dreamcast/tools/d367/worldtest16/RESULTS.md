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

## Test 16 landing: r101 version C (2026-10-16)

The user accepted the plan: no structural world cuts for now; the tool may cut terrain and rock only; structure is
simplified by hand later. Version C of r101 lands in t15/int for test 16 (test 15 stays frozen at 6b5bc9b0).

**Data (T15_DATA wv32r101 -> wt16r101).** The world32 recipe, plus these at level 0:

- bins 0x2d, 0x10, 0x65, 0xa4, 0x7f, 0x80, 0x95 and 0xd;
- a vertex box over the stake and pyre (x -7000..1500, y -500..6500, z -7000..-1500 to 7000).

The data is in `re4-assets-private/world-r101-wt16-20261016`, with SHA256SUMS and RECIPE.txt. Its wv5 mesh hash
starts 32b9d913. The set keeps 0.642 of the corners (world32 kept 0.619).

The cost is MODELLED, not measured: world p90 15.11 ms and worst view 20.41 ms. world32 was 14.06 / 18.90; the
pre-world32 world was 19.95 / 26.06.

**Gates.** The build was lane/worldtest16 5197fa04, which is t15/int 189ac886 plus the data swap. ELFs: w16mrP, w16mrT
and w16mmW. Each "o" run used the t15/int data; each "n" run used wt16r101 on the same ELF.

| Gate | Result |
| --- | --- |
| Knob-off identity | PASS. The w16mrP program image is identical to the w16brP image (189ac886): fed16888, 3368208 bytes. The 6 overlays and syms are identical too. No game or Makefile source changed. |
| STRICT + decisions, h2 (r100) | STRICT, MUST-IDENTICAL, 2002 ticks, drift 0 |
| STRICT + decisions, bell (r101) | STRICT, MUST-IDENTICAL, 2002 ticks, drift 0 |
| STRICT + decisions, door103 (r101 to r103) | STRICT, MUST-IDENTICAL, 2002 ticks, drift 0 |
| KOS squeeze, twin fpw16sq2W | 10/10 PASS. Minimum headroom 11416 B; minimum top block 4576 B. |
| TEXCHK / LEON-GC at the cross (mW) | PASS / PASS for o and n: fails 0, 0 fallback frames |
| VRAM, r101 | o equals n. At the bell: used 2191832, free 342784, 448 textures, missing 0, rejects 0. No thrash or "no contiguous" lines. The world mesh is in main RAM, and the level-5 block is sized by level 0. |
| GDEMU race (console Flycast, gdemu profile, door103) | 10/10 seeds reach r103. No MISSING, HALT, FAULT or bad-read lines. WORLDVERT 101 loaded=5. |
| Still pair at the cross | `C:\Game Dev\Emulators\worldtest-20261016\TEST16-r101-cross.png`. The crossbar is back and the pyre plank is kept. |

**Fence rails.** The rails of the house fence (right of the pyre) are still missing.

- Version C5 added a second vertex box over the fence (bins 0x7e and 0x94: x 17500..24500, y -500..3600,
  z -7000..-1000).
- diffverts confirmed that every fence vertex survives the ladder. Even so, the rails still did not draw in game
  (run m-still-c5d).
- So the rails are lost after the vertex reduction, in the batching, spatial or strip-group steps. That needs a
  separate look or a hand fix.
- C5 was not landed. Its cost is +0.15 ms p90 MODELLED.
- KNOWN_ISSUES now has two rows: the stake and pyre are fixed in test 16; the fence rails stay open.

**Landing.** lane/worldtest16-land: 5197fa04, then the KNOWN_ISSUES split, merged with origin t15/int 39d815d7.

- The water16b, radiosub16 and foliage changes landed in between. The data swap does not touch them.
- The T15_DATA line keeps their vq16w and water16i.
- Evidence: `C:\Flycast-Evidence\re4-dreamcast\wt16land-20261016` (m-*, strict\, kos\, gdemu\, _tools\).

## Test 16 follow-up: r101 set C16 restores the house-front fence rails (2026-10-16 evening)

**Root cause.** The ladder's per-vertex reduction collapsed the fence rails. They are thin pieces of mesh 0x17, which
is fused with the house front (x 2.7..11.7 m, z 5.0..13.9 m).

- The piece-thinness guard measures whole connected pieces, and only within --thin-mm of the walk path, so it missed
  them.
- Bisect: feeding the ladder's output in directly as variant 5 (no 4 m batch, no strip groups, no 32 m spatial batch)
  already lost the rails. The bake13 level 0 on the same build draws them.
- Keeping 0x17 at level 0 alone restores them. The earlier tries (C5..C15) protected meshes on the wrong side of the
  view.
- Tools: worldtest16/fence (lane/worldtest16).

**Data.** C16 = C4 + `--protect-bins 0x17`, stored in re4-assets-private/world-r101-wt16c16-20261016 (SHA256SUMS,
RECIPE.txt; wv5 hash starts d4368ff3). WT16D now points there. The C4 set stays in world-r101-wt16-20261016.

- Kept 0.652 of corners (C4 kept 0.642).
- MODELLED, not measured: world p90 15.50 ms (+0.39) and worst view 20.49 ms (+0.08).

**Gates.** Build: t15/int e22bf562 + C16 = landA 37bcf721. ELFs: w16crT, w16cmW and w16crP. Each "o" run used the C4
data and each "n" run used C16, on the same ELF.

| Gate | Result |
| --- | --- |
| STRICT + decisions, h2 / bell / door103 | STRICT, MUST-IDENTICAL, 2002 ticks each, drift 0 |
| TEXCHK / LEON-GC | PASS for o and n |
| VRAM, r101 | o equals n. At the bell: used 2191832, free 342784, missing 0, rejects 0, no thrash. |
| KOS squeeze, twin fpw16sq3W | 10/10 PASS. Minimum headroom 14360 B; minimum top block 7520 B. |
| GDEMU race | 10/10 seeds reach r103, 0 bad reads, WORLDVERT 101 loaded=5 |
| Code identity | No game, Makefile or source change. The program image of the twin is identical to the release build (IDENTITY OK, beb15f71). |
| Still pair | `C:\Game Dev\Emulators\worldtest-20261016\TEST16-r101-cross-C16.png` and TEST16-r101-fence-C16.png. The rails, crossbar and plank are all drawn. |

KNOWN_ISSUES: the fence-rail row is now "Fixed in test 16". This change is not part of the 15.1 hotfix.

**fp_twin.sh tool fix.** A new twin worktree now runs `git submodule update --init` (SH4ZAM became a submodule at
e22bf562 and the twin build stopped). It also prunes stale worktree registrations before the add.

Evidence: `C:\Flycast-Evidence\re4-dreamcast\wt16land-20261016`: c-*, strict-c16\, kosc\ and gdemuc\.
