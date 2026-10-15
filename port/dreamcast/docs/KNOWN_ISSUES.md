# Known issues

The official list of known problems in the public test builds. Updated with each test release.
Report new problems with the [bug report form](https://github.com/lamb2k/re4dc/issues/new/choose);
please name the build, real console or emulator, and where in the game it happened.

Last updated: October 15, 2026. The current public build is console test 12 (the newest release on the
[releases page](https://github.com/lamb2k/re4dc/releases/latest)). Test 11 was not released; its changes are in test 12.
Test 8 (`d4bc5f45`) was withdrawn.

## Status at a glance

| Status | Meaning | Count |
| --- | --- | --- |
| ✅ Confirmed fixed | Fixed and confirmed on a real Dreamcast | 1 |
| 🟢 Fixed, needs console check | Fixed and checked in our tests; waiting for a console report (see the checklist below) | 8 |
| 🟢 Fixed in test 9 / 9.1 / 10 / 12 | Fixed and checked in our tests; the problem was not console-only | 7 |
| 🛠️ In progress | Being fixed now | 1 |
| 🔍 Investigating | Being reproduced or traced | 4 |
| ⏸️ Open | Known, not yet worked on | 16 |
| ❔ Not reproduced | We could not make it happen; more details welcome | 1 |

## Stability

| Problem | Builds | Status | Report |
| --- | --- | --- | --- |
| Random crashes on a real console, often in the village or shortly after a room loads (memory corruption) | test 7, test 8 | 🟢 Fixed, needs console check | [#23](https://github.com/lamb2k/re4dc/issues/23), [#27](https://github.com/lamb2k/re4dc/issues/27), [#26](https://github.com/lamb2k/re4dc/issues/26) |
| Changing the Rendering level sometimes crashes a few seconds later | test 8 | 🟢 Fixed in test 9: the Rendering option was removed. Test 12 brings the row back with two choices, Standard and FSAA (both full 480-line pictures), checked in both and while switching | [#26](https://github.com/lamb2k/re4dc/issues/26) |
| Loading a save and then starting a New Game shows an error | test 7, test 8 | 🟢 Fixed in test 9 | [#26](https://github.com/lamb2k/re4dc/issues/26) |
| Opening the attaché case and pressing B twice stops the game | test 8 | ❔ Not reproduced in 8 tries | |
| Freeze in the cabin (an old build, r22i) | r22i | 🔍 Investigating: likely the same memory corruption as the random crashes | [#24](https://github.com/lamb2k/re4dc/issues/24) |
| After loading a save and resetting, the first room starts with less free memory (no crash seen) | test 9 | ⏸️ Open, being traced | [#26](https://github.com/lamb2k/re4dc/issues/26) |
| The intro stops on `MISSING motion key read` (one disc read came back incomplete) | test 7 | 🟢 Fixed, needs console check: since test 8 the read is retried up to 3 times | [#25](https://github.com/lamb2k/re4dc/issues/25) |
| Some memory is not freed when leaving a room (a side effect of the test 9 reset fix; no crash seen on the test 9 route) | test 9 | 🟢 Fixed in test 9.1 | |
| Black screen when started from DreamShell with an IDE mod | test 9 | ⏸️ Open: not tested yet; we test GDEMU and Flycast only | [#28](https://github.com/lamb2k/re4dc/issues/28) |
| A texture is refused for about 2 seconds when video memory is too broken up, though enough is free (r105 key event, r10b, r119) | test 9, 9.1, 10 | ⏸️ Open (found by the full-play check) | |
| A small menu texture does not fit in memory as the r100 cliff movie starts | test 9, 9.1, 10 | ⏸️ Open (found by the full-play check) | |
| The cutscene at the r100 cliff (after the first house) is skipped; the game goes on normally after it | test 12 | ⏸️ Open: at that point there is not enough free memory in one piece for the movie. Planned for test 13 | |
| A crash screen (`MISSING sub screen pool freeze allocation`) when a radio call opens on a real console | test 11 (not released), test 12 preview | ✅ Confirmed fixed on a real Dreamcast (test 12 preview): the call screen now keeps its copies in memory set aside for it | |

## Picture

| Problem | Builds | Status | Report |
| --- | --- | --- | --- |
| Leaves, fences and tree branch tips draw as solid shapes on a real console (fine in emulators) | test 8 | 🟢 Fixed, needs console check | [#26](https://github.com/lamb2k/re4dc/issues/26) |
| Blank screen on door transitions | test 7, test 8 | 🟢 Fixed in test 9 | |
| The item name disappears when its menu opens in the inventory | test 7, test 8 | 🟢 Fixed in test 9 | |
| The on-screen speed display is cut off by the border on a real console | test 8 | 🟢 Fixed, needs console check | [#26](https://github.com/lamb2k/re4dc/issues/26) |
| Leon switches back to the GameCube model after the boat | test 8, test 9, test 9.1 | 🟢 Fixed, needs console check (test 10) | [#26](https://github.com/lamb2k/re4dc/issues/26) |
| Lake ripples are not visible | test 8 | 🔍 Investigating: they draw in emulators; faint by design in fog | [#26](https://github.com/lamb2k/re4dc/issues/26) |
| Curtains in the first house have no texture | test 8 | 🟢 Fixed, needs console check (likely the same memory corruption) | |
| Some textures are missing or corrupted (same memory corruption as the crashes) | test 7, test 8 | 🟢 Fixed, needs console check | [#26](https://github.com/lamb2k/re4dc/issues/26) |
| Leon and most villagers are not lit by the scene's lights | test 8 | 🛠️ In progress: from test 12, Leon is lit by the scene's lights, with a soft fill light that brings him close to the GameCube brightness. The villagers are not done yet | [#26](https://github.com/lamb2k/re4dc/issues/26) |
| Water and puddles are missing | test 7, test 8 | 🟢 Fixed, needs console check: the lake surface and the wet ground layers draw in test 9.1; mirror-like puddles are not drawn | [#19](https://github.com/lamb2k/re4dc/issues/19) |
| Shadows draw incorrectly | test 7 | 🔍 Investigating: the soft shadows are fixed; some fence rails in the valley still draw black | [#20](https://github.com/lamb2k/re4dc/issues/20) |
| At the village bell the game looks for a 128x128 texture that is not on the disc | test 9, 9.1, 10 | 🟢 Fixed in test 12 | |
| The chapter 2-1 results screen is missing one texture | test 9, 9.1, 10 | 🟢 Fixed in test 12 | |
| Some effects (31 shared fire, smoke and spark pictures) still use the GameCube pictures; the rest of the village effects use the PS2 ones | test 12 | ⏸️ Open: those pictures are stored in a PS2 format that is not converted yet | |
| The merchant is not lit by the scene's lights: his robe reads brown-black instead of the PS2's blue-black | test 12 | ⏸️ Open: a lit version is waiting for a look check | |
| Some rooms look almost pitch black, as if they had no light | test 12 | 🔍 Investigating: we are comparing every room on the disc with test 10. Please tell us which rooms | |
| Broken boxes and barrels leave dark debris in the rooms after the village (r103, r104, r106, r107, r108, r10a, r10b, r117, r118, r11a, r11b) | test 8 to test 12 | ⏸️ Open: those rooms use the PS2 boxes with the GameCube debris effect. Planned for test 13 | |

## Sound

| Problem | Builds | Status | Report |
| --- | --- | --- | --- |
| The rifle sound is lower quality | all | ⏸️ Open (memory limit) | |
| The chapter results music is silent on the third results screen | all | ⏸️ Open |
| Footsteps and room ambience are silent in r103 (the farm), and in later rooms not yet in the build | all | ⏸️ Open: their sound banks are not prebuilt yet | |

## Performance and loading

| Problem | Builds | Status | Report |
| --- | --- | --- | --- |
| Below the 30 fps / full speed target, slowest in the village fight | all | ⏸️ Open: PS2 enemy and effect reductions under way | |
| In the village fight at most 6 villagers attack at once; the others wait and join as villagers fall | test 12 | ⏸️ Open: by design, for the frame rate. Every villager still appears, and the waves, the kills and the bell are unchanged | |
| Pauses when entering rooms | all | ⏸️ Open | |
| FSAA (Options, Rendering) is slower than Standard in busy scenes such as the village fight: it draws twice the pixels | test 12 | ⏸️ Open: by design; Standard is the default | |
| FSAA: busiest scenes have less geometry headroom (FSAA borrows 225 KB of the 1.95 MB per-frame geometry buffer; measured peak use 82% in the busiest test scene, El Gigante) | test 12 | ⏸️ Open: by design; Standard keeps the full buffer | |

## Console checklist for test 12

Test 12: the newest release on the [releases page](https://github.com/lamb2k/re4dc/releases/latest) (the checklist is the same as test 10, plus: do the radio calls open and close without a crash screen, and are the controller and VMU found at start-up?)

These fixes can only be confirmed on a real Dreamcast, because emulators draw the old and new versions the same.
If you play test 12 on a console, please report on any of these in a bug report:

1. **Long play in the village and the first house.** Play for 20 minutes or more, through room loads. Any crash screen?
2. **Trees and fences by the first house.** Do branch tips, leaves and fence gaps show the sky or wall behind them, or
   solid blocks?
3. **Curtains and walls in the first house.** Textured, or flat, striped or noisy?
4. **Speed display** (hold R, press START until it shows on screen). Is the counter fully visible?

An item moves to ✅ Confirmed fixed after a console report.

The game currently ends at a **Coming Soon** screen after chapter 2-1. See the
[disc 1 route](DISC1_ROUTE.md) for the rooms still to come.
