# Known issues

The official list of known problems in the public test builds. Updated with each test release.
Report new problems with the [bug report form](https://github.com/lamb2k/re4dc/issues/new/choose);
please name the build, real console or emulator, and where in the game it happened.

**Last updated:** October 25, 2026.

**Current build: Test 23** ([download](https://github.com/lamb2k/re4dc/releases/tag/test-d5b678df-20261024)). **Test 24 is pulled**: the first area is missing a door, house windows, a house and the explosives in the tree. Test 24 was PS2 weapons, HUD,
inventory screens and fonts, PS2 animation for Leon, the Ganados and the weapons, PS2 sounds and music in chapter 1,
PS2 props in chapter 2, Leon's PS2 textures, the PS2 church candles, Mendez's PS2 model in the barn door animation
(#57) and the Blacktail can be equipped (#58). A QA build for testers is the second download.

**Earlier builds** (newest first):

- **Test 23:** PS2 river water, trap explosions, Mendez no longer freezes (#55), steady barn lights, no hang on slow
disc reads (#28), mipmaps on bushes and cut-outs, fewer see-through effects, faster inventory and a better El Gigante
up close.

- **Test 22:** smoother distant textures (mipmaps), no disc read when you shoot, no stutter at in-game events, faster
inventory opening, lake trees fixed, trail effects back, and fixes for the dam crash (#52), memory after a reset (#26),
Ganado death stalls and the Mendez pause (#48, #49).

- **Test 21:** lighter, smoother fights. Fights no longer stall reloading enemy animations, Ashley no longer stalls
the game before the El Gigante fight, the night road villagers (r111) use their PS2 model, the dam rooms use the PS2
lighting, and Options has a Steady frame pacing choice.

- **Test 20:** chapter 2-1's real path. The dam (r10c), r10d and r10e are playable, the Insignia Key comes from the
dam, and far scenery and far enemies cost less.

- **Test 19.1:** hotfix of Test 19. The r100 cliff cutscene plays all its frames again (#45), r117 keeps its effect
sprites (#46), and character drawing goes back to the earlier, faster path.

- **Test 19:** quick weapon select (hold X + D-pad), foliage boots Off and view distance boots Near, the Dreamcast
Player's Manual pages (#44), enemies hidden behind walls are not drawn, and faster scenery drawing.

- **Test 18:** chapter 2-1 can be finished again (the Insignia Key is given at the dam gate), a lighter El Gigante,
Leon on his PS2 model after a chainsaw kill and in the first El Gigante fight, the r102 pictures after loading a save,
no sound gap in cutscenes, and fewer disc reads in the r100 house fight and at the night lake shore.

- **Test 17.1:** the Coming Soon screen returns you to the room.

- **Test 17:** chapters 2-2 and 2-3
up to the castle gate (r200), PS2 Ashley, Mendez and El Gigante as lighter PS2 models, rain at the night lake, solid
see-through scenery drawn solid in every chapter 2 room too, and fewer disc reads in fights.
- **Test 16.5:** the night lake's torch flames, solid see-through scenery drawn solid in every chapter 1 and 2-1 room (the cabin, r109, included), and a smaller room-entry hitch.
- **Test 16.4:** Foliage Near shows its near brush and leaf cards again; the lake draws to 45 m.
- **Test 16.3:** the village and farm fights load their Ganado animations at room entry; the village keeps all its pictures in video memory (two Ganado texture sheets at half resolution).
- **Test 16.2:** no fifth Ganado for a moment in some village areas; the r108 Ganados with a weapon use their PS2 model.
- **Test 16.1:** at most 4 Ganados at once (was 6); no ambient farm animals.
- **Test 16:** a standard GD-ROM disc image (for the GDEMU freezes), plain disc reads when a fast read fails, radio call subtitles that keep up with the voice, PS2 water out on the lake, and the village (r101) back to its full-detail world.
- **Test 15.1:** hotfix of test 15: no haze or mist sprites around Leon; Foliage Off leaves out every see-through card.
- **Test 15:** follows test 14.
- **Test 13:** follows test 12.2.
- **Test 12.2:** test 12.1 with a memory fix for leaving the village.
- **Test 12.1:** test 12 with a room lighting fix.
- **Test 11:** not released; its changes are in test 12.
- **Test 8** (`d4bc5f45`): withdrawn.

## Status at a glance

| Status | Meaning | Count |
| --- | --- | --- |
| ✅ Confirmed fixed | Fixed and confirmed on a real Dreamcast | 1 |
| 🟢 Fixed, needs console check | Fixed and checked in our tests; waiting for a console report (see the checklist below) | 10 |
| 🟢 Fixed in test 8 / 9 / 9.1 / 10 / 12 / 12.1 / 13 / 15 / 15.1 / 16 / 16.1 / 16.2 / 16.3 / 16.5 / 17 / 17.1 / 18 / 19.1 / 22 / 23 / 24 | Fixed and checked in our tests; the problem was not console-only | 61 |
| 🛠️ In progress | Being fixed now | 0 |
| 🔍 Investigating | Being reproduced or traced | 4 |
| ⏸️ Open | Known, not yet worked on | 15 |
| ❔ Not reproduced | We could not make it happen; more details welcome | 1 |

## Game progress (ongoing work)

Not bugs: work that goes on from test to test.

- **Frame rate.** It varies by scene, and the busiest fights are slowest. Speed work goes on in every test
  (history: [#29](https://github.com/lamb2k/re4dc/issues/29)).
- **Pauses when entering rooms.** Rooms load their pictures and models at the door; this is getting shorter.
- **Rooms not built yet.** The castle beyond the gate (r200). Its door shows Coming Soon and returns you to the room.
- **Dark night rooms on some consoles.** Some players report them; our Flycast captures match the GameCube's
  brightness. We're checking.

## Stability

| Problem | Builds | Status | Report |
| --- | --- | --- | --- |
| Equipping the Blacktail handgun stops the game with "DLL link/unlink failed" | test 23 | 🟢 Fixed in test 24: its weapon code is in the build again | [#58](https://github.com/lamb2k/re4dc/issues/58) |
| Mendez freezes after grabbing Leon (chapter 2-3 barn, r11f) | test 22 and earlier | 🟢 Fixed in test 23: his state word was read in the wrong byte order; the bear hug holds and the fight goes on | [#55](https://github.com/lamb2k/re4dc/issues/55) |
| A Ganado with a chainsaw who catches Leon at low health can stall: Leon lies down but the death scene and Continue never come | test 21 and earlier | 🟢 Fixed in test 22: the death scene plays and Continue returns you to the room | |
| Opening the pause menu (Options / RETRY) changes the world behind it: GameCube scenery drawn over the room outdoors, and a big lighting change in the Mendez fight | test 21 | 🟢 Fixed in test 22: the paused world stays as it was and play resumes cleanly, in the Mendez fight too | [#48](https://github.com/lamb2k/re4dc/issues/48), [#49](https://github.com/lamb2k/re4dc/issues/49) |
| A crash on a real Dreamcast when the first villager at the dam appears (a disc read failed and the enemy was never made) | test 20, 21 | 🟢 Fixed in test 22, needs console check: a failed enemy read is retried, and the dam guards a missing enemy | [#52](https://github.com/lamb2k/re4dc/issues/52) |
| At the castle gate (r200), at the end of chapter 2-3, one texture fails its preparation check in our tests. Play goes on | test 22 | 🟢 Fixed in test 23: the picture loads and passes its check |  |
| Video memory is short by one 32 KB block for the look buffer when you enter the village (r101). Play goes on | test 22 | 🟢 Fixed in test 23, needs console check: the room texture memory arrangement is on, and every room fits with no failed block in our tests. An earlier test disc with it crashed once on a console; the cache fix that may explain it is in, and Flycast runs clean. Please report any crash in the village |  |
| Random crashes on a real console, often in the village or shortly after a room loads (memory corruption) | test 7, test 8 | 🟢 Fixed, needs console check | [#23](https://github.com/lamb2k/re4dc/issues/23), [#27](https://github.com/lamb2k/re4dc/issues/27), [#26](https://github.com/lamb2k/re4dc/issues/26) |
| Changing the Rendering level sometimes crashes a few seconds later | test 8 | 🟢 Fixed in test 9: the Rendering option was removed. Test 12 brings the row back with two choices, Standard and FSAA (both full 480-line pictures), checked in both and while switching | [#26](https://github.com/lamb2k/re4dc/issues/26) |
| Loading a save and then starting a New Game shows an error | test 7, test 8 | 🟢 Fixed in test 9 | [#26](https://github.com/lamb2k/re4dc/issues/26) |
| Opening the attaché case and pressing B twice stops the game | test 8 | ❔ Not reproduced in 8 tries | |
| Freeze in the cabin (an old build, r22i) | r22i | 🔍 Investigating: likely the same memory corruption as the random crashes | [#24](https://github.com/lamb2k/re4dc/issues/24) |
| After loading a save and resetting, the first room starts with less free memory (no crash seen) | test 9 to 21 | 🟢 Fixed in test 22: Leon's outfit data from the save was reloaded for the New Game; the reset now forgets it, so the first room starts with the same memory as after a fresh boot | [#26](https://github.com/lamb2k/re4dc/issues/26) |
| The intro stops on `MISSING motion key read` (one disc read came back incomplete) | test 7 | 🟢 Fixed, needs console check: since test 8 the read is retried up to 3 times | [#25](https://github.com/lamb2k/re4dc/issues/25) |
| Some memory is not freed when leaving a room (a side effect of the test 9 reset fix; no crash seen on the test 9 route) | test 9 | 🟢 Fixed in test 9.1 | |
| Black screen when started from DreamShell with an IDE mod | test 9, 10 | 🟢 Fixed in test 16, needs a DreamShell check: DreamShell's loader handles the game's fast "streaming" disc reads differently, so some reads came back wrong. Test 16 still reads with the fast mode first, but checks that every read really arrived; the first time one fails, times out or comes back empty, the game switches to plain sector reads (the way most discs are read, with a slower method as the last resort) for the rest of the session, and shows on screen what it is doing if a read misbehaves. From test 23 a read that never finishes times out and is read again (the DreamShell hang on the first music read) | [#28](https://github.com/lamb2k/re4dc/issues/28) |
| Freezes or crashes on some GDEMU units while other games work, often while a room loads; one freeze at the SEGA screen | test 7, 8 and later | 🟢 Fixed in test 16: the disc is now a standard GD-ROM image, laid out like a pressed GD-ROM (as the community tool mkdcdisc writes it): the table of contents real GD-ROMs carry, the full-size data track and the program as the last file. The disc of the earlier tests came from our own script and differed from that layout in several places. The test 14 game in the standard format ran fine on our GDEMU console on October 16, 2026 ("new gdi runs fine"), and it passes the GDEMU disc-timing checks in our console-like emulator. Test 14 also fixed the disc library underneath (a read waits until the drive's transfer has really finished; two drive hangs fixed). If a GDEMU still freezes with test 16, please report it with whether your GDEMU is an original or a clone, the firmware version shown in its menu, and your SD card's brand and size; leave "Shrink GDI" off. Details: [CONTRIBUTING-PORT.md section 8](../CONTRIBUTING-PORT.md#8-disc-image-and-compatibility). From test 16 the game also switches to plain sector reads by itself (for the rest of the session) as soon as a fast "streaming" read fails or times out, so a unit that cannot stream keeps playing instead of freezing; loading speed is unchanged when nothing fails. | [#17](https://github.com/lamb2k/re4dc/issues/17), [#24](https://github.com/lamb2k/re4dc/issues/24), [#25](https://github.com/lamb2k/re4dc/issues/25), [#27](https://github.com/lamb2k/re4dc/issues/27) |
| A texture is refused for about 2 seconds when video memory is too broken up, though enough is free (r105 key event, r10b, r119) | test 9, 9.1, 10, 11 | 🟢 Fixed in test 15: fixed in test 13 for the r105 key event; from test 15 every chapter 1 room and r119 loads its pictures once when you enter it (lists per room, and 39 large pictures in a smaller compressed format), so nothing is refused for lack of one free block | |
| On the r10b boat, and in r105 after the chapter 1-2 results screen, a few effect pictures can be skipped while video memory is full | test 12.2, 13 | 🟢 Fixed in test 15: the rooms' pictures load once at room entry and stay in video memory, and after the chapter results and save screens the room's pictures are loaded back in one go before play resumes | |
| A small menu texture does not fit in memory as the r100 cliff movie starts | test 9, 9.1, 10 | ⏸️ Open (found by the full-play check) | |
| The cutscene at the r100 cliff (after the first house) is skipped; the game goes on normally after it | test 12, 12.1, 12.2, 13, 14 | 🟢 Fixed in test 15: while the movie plays it borrows the memory of the room's scenery, which is read back from the disc and checked when the movie ends | |
| Possible out-of-memory crash on a real console when leaving the village (r101) after a long fight, at the next room's start | test 12, 12.1 | 🟢 Fixed in test 12.2, needs console check: found by our memory checks, not reported by anyone yet; the village's leftover texture records are freed when the room changes, and our console-memory test (Flycast with 48 KiB of the console's system memory held back) now leaves the village to r100 and r103 without running out | |
| Chapter 2-1 has two ways forward and the test carries one. Main path: the lake shore, r11a, r119, r118, r117. Doors that show Coming Soon: on the lake shore the second exit and the ladder (r11b to r10c / r10d); in the El Gigante area by day or night, the side path (r119 / r109 to r10e). Until 17.1 the game stayed on the Coming Soon screen | test 17 and earlier | 🟢 Fixed in test 17.1: the screen now returns you to the room, so you can take the other exit | |
| Chapter 2-1 can't be finished: the church door (r118) needs the Insignia Key, which is found in the dam (r10c), a room not on the disc yet | test 17, 17.1 | 🟢 Fixed in test 18: the key is given at the gate to the dam, where Coming Soon shows | [#40](https://github.com/lamb2k/re4dc/issues/40) |
| A crash screen (`MISSING sub screen pool freeze allocation`) when a radio call opens on a real console | test 11 (not released), test 12 preview | ✅ Confirmed fixed on a real Dreamcast (test 12 preview): the call screen now keeps its copies in memory set aside for it | |

## Picture

| Problem | Builds | Status | Report |
| --- | --- | --- | --- |
| After the Mendez fight (chapter 2-3 barn, r11f), the short door animation out of the barn draws Mendez with his GameCube model, and one of its pictures is missing. Play goes on | test 23 | 🟢 Fixed in test 24: the animation draws Mendez with his PS2 model | [#57](https://github.com/lamb2k/re4dc/issues/57) |
| River and waterfall water is missing or drawn with the wrong picture: the cave river, the dam river by the water wheel, the merchant cave pool | test 22 and earlier | 🟢 Fixed in test 23: they draw their PS2 water planes | [#55](https://github.com/lamb2k/re4dc/issues/55) |
| Tree and door traps do not explode | test 22 and earlier | 🟢 Fixed in test 23: the trap explosion sprites are drawn | [#55](https://github.com/lamb2k/re4dc/issues/55) |
| The light in Mendez's barn flickers | test 22 and earlier | 🟢 Fixed in test 23 | [#55](https://github.com/lamb2k/re4dc/issues/55) |
| The lever gears (r11c) disappear | test 22 | 🟢 Fixed in test 23: the gears stay drawn and turn | [#52](https://github.com/lamb2k/re4dc/issues/52) |
| El Gigante looks blocky up close: he is drawn with his low-detail model | test 17 and later | 🟢 Fixed in test 23: a better close-up model (checked by the maintainer) |  |
| Trees on the lake islands (r10b) look shredded | test 21 and earlier | 🟢 Fixed in test 22: the bark uses its own picture again | |
| The r100 cliff cutscene (after the first house) skips about 43 of its 340 frames, so it looks choppier. The game goes on normally | test 19 | 🟢 Fixed in test 19.1: the scenery shares repeated corner points, so the movie has its memory again (340 of 340 frames) | [#45](https://github.com/lamb2k/re4dc/issues/45) |
| In r117, after the Saddler scene starts, a few effect sprites are skipped for about 3 seconds while video memory is short. Play continues | test 19 | 🟢 Fixed in test 19.1: no sprites skipped in r117 (0 refusals) | [#46](https://github.com/lamb2k/re4dc/issues/46) |
| The Player's Manual pages 1-3 (aim, knife, action) and file 3 show the GameCube controller instead of the Dreamcast one. The Dreamcast pages are on the disc, but the game looks for them outside the texture pack | test 8 to 18 | ✅ Fixed in test 19 | [#44](https://github.com/lamb2k/re4dc/issues/44) |
| In the Mendez fight (chapter 2-3 barn, r11f) the room's effect pool fills (1,024 of 1,024 sprites) and a few fire / smoke effects are skipped; the same happens with the GameCube's own pool size | test 17 | 🔍 Investigating, not blocking: found by our effect-pool count (ESP_POOL_DIAG), no gameplay effect seen | |
| Leaves, fences and tree branch tips draw as solid shapes on a real console (fine in emulators) | test 8 | 🟢 Fixed, needs console check | [#26](https://github.com/lamb2k/re4dc/issues/26) |
| Blank screen on door transitions | test 7, test 8 | 🟢 Fixed in test 9 | |
| The item name disappears when its menu opens in the inventory | test 7, test 8 | 🟢 Fixed in test 9 | |
| The on-screen speed display is cut off by the border on a real console | test 8 | 🟢 Fixed, needs console check | [#26](https://github.com/lamb2k/re4dc/issues/26) |
| Leon switches back to the GameCube model after the boat | test 8, test 9, test 9.1 | 🟢 Fixed, needs console check (test 10) | [#26](https://github.com/lamb2k/re4dc/issues/26) |
| Lake ripples are not visible | test 8 | 🟢 Fixed in test 16, needs console check (test 15: the lake seen from the shore only): the lakes now draw the PS2 way, a dark water base with two slow moving water layers and a moving ripple layer, from the shore and out on the lake (the Del Lago boat fight), by day and at night | [#26](https://github.com/lamb2k/re4dc/issues/26) |
| Curtains in the first house have no texture | test 8 | 🟢 Fixed, needs console check (likely the same memory corruption) | |
| Some textures are missing or corrupted (same memory corruption as the crashes) | test 7, test 8 | 🟢 Fixed, needs console check | [#26](https://github.com/lamb2k/re4dc/issues/26) |
| Leon and most villagers are not lit by the scene's lights | test 8 | 🟢 Fixed in test 15: Leon is lit by the scene's lights from test 12, with a soft fill light that brings him close to the GameCube brightness. From test 15 the villagers take their colour from the lights around each of them (the same light probe as Leon), drawn flat: one colour per body part, no shading across the body | [#26](https://github.com/lamb2k/re4dc/issues/26) |
| Water and puddles are missing | test 7, test 8 | 🟢 Fixed, needs console check: the lake surface and the wet ground layers draw in test 9.1; mirror-like puddles are not drawn (the PS2 version has none either). From test 15 the pool, the river and the lake seen from the shore draw their water the PS2 way (needs console check); from test 16 the open lake (Del Lago, and the lake at night) does too | [#19](https://github.com/lamb2k/re4dc/issues/19) |
| Some rooms look almost pitch black: the r11b lake shore (dark dock and ground, near-black sky), r117, r108 | test 12 | 🟢 Fixed in test 12.1: the rooms use the PS2 room lighting, and the r11b / r119 mist is drawn as in test 10 | |
| Shadows draw incorrectly | test 7 | 🔍 Investigating: the soft shadows are fixed; some fence rails in the valley still draw black | [#20](https://github.com/lamb2k/re4dc/issues/20) |
| At the village bell the game looks for a 128x128 texture that is not on the disc | test 9, 9.1, 10 | 🟢 Fixed in test 12 | |
| The chapter 2-1 results screen is missing one texture | test 9, 9.1, 10 | 🟢 Fixed in test 12 | |
| A few effect pictures are the GameCube ones: two shared room effects seen in most chapter 1 rooms, one in r101 / r103 / r106 and one animated effect in r117; every other effect uses the PS2 pictures | test 12, 13 | ⏸️ Open: the PS2 version has no matching picture for these four; the full-play checks of test 12.2 and test 13 found no others. The 31 shared fire, smoke and spark pictures that test 12 took from the GameCube now use the PS2 pictures | |
| The merchant is not lit by the scene's lights: his robe reads brown-black instead of the PS2's blue-black | test 12 | 🟢 Fixed in test 15: lit by the room lights | |
| Broken boxes and barrels leave dark debris in the rooms after the village (r103, r104, r106, r107, r108, r10a, r10b, r117, r118, r11a, r11b) | test 8 to test 12.2 | 🟢 Fixed in test 13: breakable boxes and barrels use the GameCube models in every room, so they break into the GameCube splinters; the other room objects use their PS2 models | |
| Right after the door from the village into r103, some effect pictures can be missing for a moment and more textures load from the disc during play | test 12, 12.1, 12.2 | 🟢 Fixed in test 13: the village's leftover textures are cleared at the door, so r103 (and r100 when you go back) loads its textures when the room starts | |
| The night lake (start of chapter 2-1): the torches have no flames | test 10 to 16.4 | 🟢 Fixed in test 16.5 (LAKE_NIGHT_FX), needs console check | [#30](https://github.com/lamb2k/re4dc/issues/30) |
| The night lake (start of chapter 2-1): the rain is missing | test 10 to 16.5 | 🟢 Fixed in test 17 (RAIN_DC), needs console check: 320 falling streaks drawn the Dreamcast way, cheaper than the old faint lines | [#30](https://github.com/lamb2k/re4dc/issues/30) |
| Ashley shows a resting face: her facial expressions are not shown | test 13 | ⏸️ Open: Ashley uses her PS2 model (from test 17 in every room she follows Leon, r10f to r200 included); the expressions come later | |
| Foliage: Off removes walls and floor in r109 (the cabin); use Near or Full there | test 15 | 🟢 Fixed in test 15.1: Off now leaves out only the see-through brush, leaf and shadow cards; the cabin keeps its walls and floor | |
| In the village (r101) the burning stake has lost its crossbar and a plank of the pyre (the simplified village scenery of test 15) | test 15 | 🟢 Fixed in test 16 (r101 uses its unreduced world again) | |
| In the village (r101) the fence by the house on the right of the square shows only its posts, without its rails (the simplified village scenery of test 15) | test 15 | 🟢 Fixed in test 16 (r101 uses its unreduced world again) | |
| The item menu's confirm popup does not look as it did in test 13 | test 14, 15 | ⏸️ Open | |
| The dam (r10c), r10d and r10e use the GameCube room light, not a measured PS2 value, so their brightness may differ a little from the PS2 version | test 20 | ⏸️ Open, not blocking: a look check is planned | [#47](https://github.com/lamb2k/re4dc/issues/47) |
| In r102, right after loading a save, a few effect pictures are not drawn while video memory is full (test 16.5: 4 refused; test 16.3 and 16.4: 5; test 15: 4; test 14: 76) | test 14 to 17.1 | 🟢 Fixed in test 18: r102's pictures load with the room's resident list after a save is loaded | [#33](https://github.com/lamb2k/re4dc/issues/33) |
| A few pictures are read from the disc again during play in rooms that should keep all their pictures loaded: the r100 house fight (about 50) and the r11b lake shore (4 to 5) | test 16.3 to 17.1 | 🟢 Fixed in test 18: the rooms' resident picture lists now hold these pictures | |
| In r118 one small picture (64x64) is not on the disc, so it is not drawn | test 16.4, 16.5 | 🟢 Fixed in test 17: the picture is in the disc's texture package, and our texture check passes in r118 | [#37](https://github.com/lamb2k/re4dc/issues/37) |
| In r200, at the castle gate, some effect sprites are skipped for about a second: the per-frame list of see-through parts is full. Play continues | test 17 to 18 | 🟢 Fixed in test 23: effects in busy rooms get more room and the barn light keeps its slot | [#41](https://github.com/lamb2k/re4dc/issues/41) |
| After a chainsaw kill, Leon is drawn with his GameCube model for the death scene | test 17.1 and earlier | 🟢 Fixed in test 18: Leon keeps his PS2 model, his head included | |
| Arriving at the night lake shore (r11b) straight from the Del Lago fight, three large pictures wait about 2 seconds for a free block of video memory and one effect sprite is skipped. Play continues | test 17.1, 18 | ⏸️ Open, not blocking: found by our new chapter 2-1 checks; test 17.1 does the same (12 waits there, 8 in test 18) | [#43](https://github.com/lamb2k/re4dc/issues/43) |
| Our not-drawn check finds enemies in view that are not drawn for a while: four Ganados in r111 and seven of the enemies in r113 (model em2a). Play is not affected | test 17.1, 18 | 🔍 Investigating, not blocking: found by our in-view not-drawn check in the test 18 checks; test 17.1 does the same | [#42](https://github.com/lamb2k/re4dc/issues/42) |
| In r106 the four Ganados waiting behind the closed gate are not drawn until they come through it (they are out of view behind the gate) | test 17 | ⏸️ Open: by design for now; found by our new not-drawn check | |

## Sound

| Problem | Builds | Status | Report |
| --- | --- | --- | --- |
| The rifle sound is lower quality | all | ⏸️ Open (memory limit) | |
| Cutscenes have a short gap in the sound (about 0.15 s). The Mendez cutscene (r11f) ends as soon as you pass its button prompt, as in the original game | test 17.1 and earlier | 🟢 Fixed in test 18: the cutscene sound is fully loaded before it starts | [#38](https://github.com/lamb2k/re4dc/issues/38) |
| Radio call subtitles lag behind the voice: they fall further behind as the call goes on and end well after it (real console) | test 14 and earlier | 🟢 Fixed in test 16, needs console check: the subtitles counted one GameCube 30 Hz step per drawn frame of the call, while the voice plays in real time, so every call frame slower than 1/30 s put them further behind. They now follow the voice's own clock from the moment it starts sounding. With the call slowed to 15 frames a second on an emulator (a model, not a console measurement): 27 s behind at the end of the first call before, within 0.06 s of the voice through the whole call after (Flycast at full speed: 0.32 s before, 0.03 s after) | |
| The chapter results music is silent on the third results screen | test 7 and earlier | 🟢 Fixed in test 8: the music that plays after each chapter's results (chapters 1-1, 1-2 and 1-3, on the save screen) is on the disc. The results table itself has no music, as in the original game: the chapter end stops the room music and starts none | |
| Footsteps and room ambience are silent in r103 (the farm) | test 13, 14 | 🟢 Fixed in test 15: r103's footstep and ambience sounds are converted for the Dreamcast again (ambience 16 kHz, footsteps 11 kHz, the same rates as the other rooms). The later chapter 1 rooms already had theirs | |
| Some music and voices are silent: the r104 and r107 room music, the r106 battle music, the r102 room music and the merchant's voice, the "you died" screen music, and a few short event jingles (r100, r101, r104, r108, r10b) | all | 🟢 Fixed in test 15: these music and voice tracks are now on the disc. Only one of them plays at a time, so a voice that starts while another track plays can still be silent, as before | |

## Performance and loading

| Problem | Builds | Status | Report |
| --- | --- | --- | --- |
| For contributors: a kit build of the Test 21 source with its own knob file does not give the exact published Test 21 program bytes (26da4fe3, published bd0970c0). The Test 22 kit build does match the Test 22 program. Play is not affected | test 21 | ⏸️ Open, not blocking: older builds are not byte-reproducible across toolchain and tree state | |
| Opening the inventory still reads about 0.8 to 1.4 MB from the disc each time | test 22 and earlier | 🟢 Fixed in test 23: the inventory opens faster |  |
| At most 4 Ganados are active at once (6 from test 12 in the village and test 13 in every chapter 1 room; 4 from test 16.1); the others wait and arrive as you kill them | test 12, 13, 16.1 | ⏸️ Open: by design, for the frame rate. Every villager still appears, and the waves, the kills and the events are unchanged. Test 16.1 lowers the limit from 6 to 4 in every room |  |
| A fifth Ganado could appear for a moment in some village areas (r107), over the limit of 4 | test 16.1 | 🟢 Fixed in test 16.2: every Ganado a room sends waits for its turn under the limit |  |
| In r108, the Ganados holding a weapon use the GameCube model instead of the PS2 one | test 16, 16.1 | 🟢 Fixed in test 16.2 |  |
| The village (r101) and farm (r103) fights read Ganado animations from the disc in the middle of the fight, and the village loaded some pictures while playing (short pauses); r104, r108 and r118 too | test 16, 16.1, 16.2 | 🟢 Fixed in test 16.3: the animations these rooms' fights use, and their pictures, are loaded when you enter the room |  |
| In the village (r101), two Ganado texture sheets load at half resolution, so all of the room's pictures fit in video memory; the villagers have a little less texture detail up close there | test 16.3 | ⏸️ Open: by design, for the frame rate (the other rooms keep full detail) |  |
| Some scripted Ganado waves in r10a can start early: a Ganado still waiting for its turn under the Ganado limit is counted as dead, so the wave that waits for those kills begins too soon | test 16 | 🟢 Fixed in test 16.1: a waiting Ganado now counts as alive until it arrives and is killed |  |
| The ambient farm animals are removed for speed: cows, chickens and the farm dog in the village (r101) and the farm (r103); no eggs from chickens. The dog in the bear trap (r100) and the dog that helps against El Gigante stay | test 16.1 | ⏸️ Open: by design, for the frame rate (the farm ran about 20% slower with them in our emulator tests) |  |
| The farm after the village (r103) re-reads villager animations from the disc during play (about 38 reads a second on a console) and loads textures while playing; after a radio call in the village the on-screen display reloads its pictures | test 12, 13 | 🟢 Fixed in test 14, needs a console check: the animations stay in memory, and r103's and r101's textures are loaded when the room starts. From test 15 the on-screen display also keeps its pictures through the village radio call | |
| FSAA (Options, Rendering) is slower than Standard in busy scenes such as the village fight: it draws twice the pixels | test 12 | ⏸️ Open: by design; Standard is the default | |
| View distance Near or Short (Options) shows less of the distant outdoor scenery: it fades into the fog sooner (houses inside stay clear, the lake keeps its full horizon). From test 17, Short draws a simplified far view in the first area and the village (the distant houses, trees and hills kept beyond the cut) | test 15 | ⏸️ Open: by design; from Test 19 every boot starts at Near (Full is one press away in Options) | |
| Foliage Near and Off look the same: no near brush or leaf cards at Near | test 16 | 🟢 Fixed in test 16.4 (FOLIAGE_NEAR_FIX), needs console check | |
| The lake fades into the fog at 25 m, closer than on PS2 | test 16 | 🟢 Fixed in test 16.4 (LAKE_FAR / LAKE_FAR_SHORE), needs console check: 45 m on the boat (Del Lago) and from the shore by day and at night | |
| The contributor kit's knob file (`tools/d367/test16/release-knobs.txt`) at the test 16.4 tag described an earlier candidate (LAKE_FAR=30000), so a kit build did not match the 16.4 program | test 16.4 | 🟢 Fixed in test 16.5: the knob file is written from the release build and committed on the tagged commit itself | [#34](https://github.com/lamb2k/re4dc/issues/34) |
| Entering a room could hitch briefly while the room's draw plan was built | test 16.4 and earlier | 🟢 Fixed in test 16.5 (contributed by Bruceleeto): the plan copies only the parts it uses | |
| See-through scenery parts whose pictures are really solid, or whose edges are almost hard cut-outs, used the slower see-through drawing | test 16.4 and earlier | 🟢 Changed in test 16.5 (TRANS_POLICY, FLAT + CARD) in every chapter 1 and 2-1 room, including r109 (the cabin, where some window and wall pictures look slightly different; look approved) | |
| FSAA: busiest scenes have less geometry headroom (FSAA borrows 225 KB of the 1.95 MB per-frame geometry buffer; measured peak use 82% in the busiest test scene, El Gigante) | test 12 | ⏸️ Open: by design; Standard keeps the full buffer | |

## Console checklist for test 16

Test 16: the newest release on the [releases page](https://github.com/lamb2k/re4dc/releases/latest) (the checklist is the same as test 15, plus: do rooms load on your GDEMU without a freeze with the new standard disc format (#27), and do the radio call subtitles keep up with the voice?)

These fixes can only be confirmed on a real Dreamcast, because emulators draw the old and new versions the same.
If you play test 16 on a console, please report on any of these in a bug report:

1. **Long play in the village and the first house.** Play for 20 minutes or more, through room loads. Any crash screen?
2. **Trees and fences by the first house.** Do branch tips, leaves and fence gaps show the sky or wall behind them, or
   solid blocks?
3. **Curtains and walls in the first house.** Textured, or flat, striped or noisy?
4. **Speed display** (hold R, press START until it shows on screen). Is the counter fully visible?
5. **Leaving the village after the fight** (test 12.2 and later). After the village fight, walk on to the next room
   (back to r100, or on to r103). Any crash screen while it loads, or missing effect pictures right after the door?
6. **Room loads on GDEMU** (test 14 and later; test 16 is the first standard GD-ROM image). Do doors and room loads
   finish without a freeze? Please name your GDEMU (original or clone), its firmware and your SD card.
7. **The r100 cliff cutscene** (test 15). After the first house, does the cliff cutscene play, and does the game go on
   normally after it?
8. **Radio call subtitles** (test 16). In a radio call, do the subtitles keep up with the voice and end with it?

An item moves to ✅ Confirmed fixed after a console report.
