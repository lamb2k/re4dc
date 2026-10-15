# Known issues

The official list of known problems in the public test builds. Updated with each test release.
Report new problems with the [bug report form](https://github.com/lamb2k/re4dc/issues/new/choose);
please name the build, real console or emulator, and where in the game it happened.

Last updated: October 15, 2026. The current public build is console test 13 (the newest release on the
[releases page](https://github.com/lamb2k/re4dc/releases/latest)). Test 11 was not released; its changes are in test 12. Test 12.1 is test 12 with a room lighting fix; test 12.2 is test 12.1 with a memory fix for leaving the village; test 13 follows test 12.2.
Test 8 (`d4bc5f45`) was withdrawn.

## Status at a glance

| Status | Meaning | Count |
| --- | --- | --- |
| ✅ Confirmed fixed | Fixed and confirmed on a real Dreamcast | 1 |
| 🟢 Fixed, needs console check | Fixed and checked in our tests; waiting for a console report (see the checklist below) | 9 |
| 🟢 Fixed in test 9 / 9.1 / 10 / 12 / 12.1 / 13 | Fixed and checked in our tests; the problem was not console-only | 10 |
| 🛠️ In progress | Being fixed now | 2 |
| 🔍 Investigating | Being reproduced or traced | 5 |
| ⏸️ Open | Known, not yet worked on | 14 |
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
| Black screen when started from DreamShell with an IDE mod | test 9, 10 | 🔍 Investigating: DreamShell's loader handles the game's fast "streaming" disc reads differently, so some reads come back wrong. A second test disc that uses plain disc reads and shows on screen what it is doing is being prepared | [#28](https://github.com/lamb2k/re4dc/issues/28) |
| Freezes or crashes on some GDEMU units while other games work, often while a room loads; one freeze at the SEGA screen | test 7, 8 and later | 🔍 Investigating: the game reads the disc with a fast "streaming" mode that some drive emulators and older firmware handle differently. We are testing plain disc reads instead. Test 14 fixes the disc library underneath: a read now waits until the drive's transfer has really finished (before, a read could be handed over early on a real console), and two drive hangs are fixed; this needs a console check. Meanwhile: start the game from openMenu or GDMenu, and if your SD card tool has a "Shrink GDI" option, leave it off (a tester fixed a freeze at the SEGA screen this way). When you report, please tell us whether your GDEMU is an original or a clone, the firmware version shown in its menu, and your SD card's brand and size | [#17](https://github.com/lamb2k/re4dc/issues/17), [#24](https://github.com/lamb2k/re4dc/issues/24), [#25](https://github.com/lamb2k/re4dc/issues/25), [#27](https://github.com/lamb2k/re4dc/issues/27) |
| A texture is refused for about 2 seconds when video memory is too broken up, though enough is free (r105 key event, r10b, r119) | test 9, 9.1, 10, 11 | 🛠️ In progress: fixed in test 13 for the r105 key event (the chapter 1-2 results screen: a large picture now gets one free block of its size); r10b and r119 are still open | |
| On the r10b boat, and in r105 after the chapter 1-2 results screen, a few effect pictures can be skipped while video memory is full | test 12.2, 13 | ⏸️ Open (found by the full-play check; fewer in r105 since test 13) | |
| A small menu texture does not fit in memory as the r100 cliff movie starts | test 9, 9.1, 10 | ⏸️ Open (found by the full-play check) | |
| The cutscene at the r100 cliff (after the first house) is skipped; the game goes on normally after it | test 12, 12.1, 12.2, 13 | ⏸️ Open: at that point there is not enough free memory in one piece for the movie | |
| Possible out-of-memory crash on a real console when leaving the village (r101) after a long fight, at the next room's start | test 12, 12.1 | 🟢 Fixed in test 12.2, needs console check: found by our memory checks, not reported by anyone yet; the village's leftover texture records are freed when the room changes, and our console-memory test (Flycast with 48 KiB of the console's system memory held back) now leaves the village to r100 and r103 without running out | |
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
| Some rooms look almost pitch black: the r11b lake shore (dark dock and ground, near-black sky), r117, r108 | test 12 | 🟢 Fixed in test 12.1: the rooms use the PS2 room lighting, and the r11b / r119 mist is drawn as in test 10 | |
| Shadows draw incorrectly | test 7 | 🔍 Investigating: the soft shadows are fixed; some fence rails in the valley still draw black | [#20](https://github.com/lamb2k/re4dc/issues/20) |
| At the village bell the game looks for a 128x128 texture that is not on the disc | test 9, 9.1, 10 | 🟢 Fixed in test 12 | |
| The chapter 2-1 results screen is missing one texture | test 9, 9.1, 10 | 🟢 Fixed in test 12 | |
| A few effect pictures are the GameCube ones: two shared room effects seen in most chapter 1 rooms, one in r101 / r103 / r106 and one animated effect in r117; every other effect uses the PS2 pictures | test 12, 13 | ⏸️ Open: the PS2 version has no matching picture for these four; the full-play checks of test 12.2 and test 13 found no others. The 31 shared fire, smoke and spark pictures that test 12 took from the GameCube now use the PS2 pictures | |
| The merchant is not lit by the scene's lights: his robe reads brown-black instead of the PS2's blue-black | test 12 | ⏸️ Open: a lit version is waiting for a look check | |
| Broken boxes and barrels leave dark debris in the rooms after the village (r103, r104, r106, r107, r108, r10a, r10b, r117, r118, r11a, r11b) | test 8 to test 12.2 | 🟢 Fixed in test 13: breakable boxes and barrels use the GameCube models in every room, so they break into the GameCube splinters; the other room objects use their PS2 models | |
| Right after the door from the village into r103, some effect pictures can be missing for a moment and more textures load from the disc during play | test 12, 12.1, 12.2 | 🟢 Fixed in test 13: the village's leftover textures are cleared at the door, so r103 (and r100 when you go back) loads its textures when the room starts | |
| Ashley shows a resting face: her facial expressions are not shown | test 13 | ⏸️ Open: Ashley now uses her PS2 model; the expressions come later | |

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
| At most 6 villagers are active at once (the village fight from test 12, every chapter 1 room from test 13); the others wait and join as villagers fall | test 12, 13 | ⏸️ Open: by design, for the frame rate. Every villager still appears, and the waves, the kills and the events are unchanged; the enemy rules otherwise follow the PS2 version. Exception: the ambush at the first house (r100) can have more than 6 villagers, as in the original | |
| Pauses when entering rooms | all | ⏸️ Open | |
| The farm after the village (r103) re-reads villager animations from the disc during play (about 38 reads a second on a console) and loads textures while playing; after a radio call in the village the on-screen display reloads its pictures | test 12, 13 | 🟢 Fixed in test 14, needs a console check: the animations stay in memory, and r103's and r101's textures (and the on-screen display's) are loaded when the room starts | |
| FSAA (Options, Rendering) is slower than Standard in busy scenes such as the village fight: it draws twice the pixels | test 12 | ⏸️ Open: by design; Standard is the default | |
| FSAA: busiest scenes have less geometry headroom (FSAA borrows 225 KB of the 1.95 MB per-frame geometry buffer; measured peak use 82% in the busiest test scene, El Gigante) | test 12 | ⏸️ Open: by design; Standard keeps the full buffer | |

## Console checklist for test 13

Test 13: the newest release on the [releases page](https://github.com/lamb2k/re4dc/releases/latest) (the checklist is the same as test 10, plus: do the radio calls open and close without a crash screen, and are the controller and VMU found at start-up?)

These fixes can only be confirmed on a real Dreamcast, because emulators draw the old and new versions the same.
If you play test 13 on a console, please report on any of these in a bug report:

1. **Long play in the village and the first house.** Play for 20 minutes or more, through room loads. Any crash screen?
2. **Trees and fences by the first house.** Do branch tips, leaves and fence gaps show the sky or wall behind them, or
   solid blocks?
3. **Curtains and walls in the first house.** Textured, or flat, striped or noisy?
4. **Speed display** (hold R, press START until it shows on screen). Is the counter fully visible?
5. **Leaving the village after the fight** (test 12.2, 13). After the village fight, walk on to the next room (back to
   r100, or on to r103). Any crash screen while it loads, or missing effect pictures right after the door?

An item moves to ✅ Confirmed fixed after a console report.

The game currently ends at a **Coming Soon** screen after chapter 2-1. See the
[disc 1 route](DISC1_ROUTE.md) for the rooms still to come.
