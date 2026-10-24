![RE4 Dreamcast](docs/images/title.jpg)

# RE4 Dreamcast

**Resident Evil 4 runs on the Sega Dreamcast, from New Game to the end of chapter 2-3 at the castle gate.**

It is the GameCube game's own recovered code, not a remake, drawn by a native Dreamcast renderer.
This is an experimental fan test build, not the complete game.

**[Download Test 22](https://github.com/lamb2k/re4dc/releases/latest)** · [Known issues](port/dreamcast/docs/KNOWN_ISSUES.md) ·
[Port notes](port/dreamcast/README.md) · [Build the port](port/dreamcast/CONTRIBUTING-PORT.md) · [Decompilation](docs/DECOMPILATION.md)

## What's new in Test 22

Smoother distant textures, fewer pauses and crash and stall fixes, still up to the castle gate. Full details are
in the [release notes](https://github.com/lamb2k/re4dc/releases/latest).

- **Smoother distant textures (mipmaps).** Far ground and walls use smaller copies of their pictures, so they
  shimmer less.

  ![Mipmaps in the village: before left, Test 22 right](docs/images/releases/test-22/mipmaps-village.jpg)
  <br>The village. Left without mipmaps, right Test 22. Flycast capture.

  ![Mipmaps at the farm: before left, Test 22 right](docs/images/releases/test-22/mipmaps-farm.jpg)
  <br>The farm. Left without mipmaps, right Test 22. Flycast capture.
- **No disc read when you shoot.** The ammo digits and the muzzle flash load with the room.
- **No stutter at in-game events.** Ganados keep their models through scripted moments.
- **Faster inventory opening.** Its data is packed smaller on the disc.
- **Fixed: the crash at the dam's first villager** on a real Dreamcast ([#52](https://github.com/lamb2k/re4dc/issues/52)).
- **Fixed: less free memory after loading a save and resetting** ([#26](https://github.com/lamb2k/re4dc/issues/26)).
- **Fixed: Ganados stalling as they die**, and the death scene after a chainsaw catch.
- **Fixed: pausing in the Mendez fight**, and the world behind the pause menu ([#48](https://github.com/lamb2k/re4dc/issues/48), [#49](https://github.com/lamb2k/re4dc/issues/49)).
- **Lake trees** on the islands no longer look shredded.

  ![Lake island trees: Test 21 left, Test 22 right](docs/images/releases/test-22/lake-trees.jpg)
  <br>The lake from the boat. Left Test 21, right Test 22. Flycast capture.
- **Trail and ribbon effects** draw again.
- **Safety guards** stop a failed load from crashing the game.

## What's new in Test 21

Lighter, smoother fights and two places fixed, still up to the castle gate.

- **Fights no longer stall reloading enemy animations** (the r100 ambush, the village fights). In the forest ambush after the house, animation loads dropped from about 700 to about 20, with no disc reads in the last 16 seconds (Flycast measurement).
- **Ashley no longer stalls the game before the El Gigante fight (r11e).**
- **Lighter fights.** Dead bodies and props cost less to run and draw.
- **The night road villagers (r111) use their PS2 model** ([#42](https://github.com/lamb2k/re4dc/issues/42)).

  ![Villagers on the night road (r111)](docs/images/releases/test-21/r111-villagers.jpg)
  <br>The night road villagers. Flycast capture, test 21.
- **The dam rooms use the PS2 lighting** ([#47](https://github.com/lamb2k/re4dc/issues/47)).

  ![The dam with PS2 lighting](docs/images/releases/test-21/dam-light.jpg)
  <br>The dam. Flycast capture, test 21.
- **Steady frame pacing.** Options > Frame pacing > Steady shows every frame for the same time. Fast stays the default.

  ![Options: Frame pacing Steady](docs/images/releases/test-21/options-steady.jpg)
  <br>The Options screen. Flycast capture, test 21.
- **QA build for testers** is a second download: teleports, a weapon kit and a Diagnostics page with a QR code.

## What's new in Test 20

Chapter 2-1's real path: the dam is in. Full details are in the
[release notes](https://github.com/lamb2k/re4dc/releases/latest).

- **The dam (r10c) and the lake's side rooms (r10d, r10e) are playable.** Open the gate, drain the dam and fight
  the Ganados there, as in the original.

  ![The dam (r10c)](docs/images/releases/test-20/dam-r10c.jpg)
  <br>The dam. Flycast capture, test 20.
- **The Insignia Key is where the game leaves it**, at the dam. The key handover at the dam gate and the two Coming
  Soon doors are gone.

  ![The Insignia Key pickup (r10c)](docs/images/releases/test-20/insignia-key.jpg)
  <br>Taking the key at the dam. Flycast capture, test 20.
- **Faster scenery and enemy logic.** Far scenery uses its lower detail, and far enemies and effects do less work.
  Fights play the same.

## What's new in Test 19.1

A hotfix of Test 19. Full details are in the [release notes](https://github.com/lamb2k/re4dc/releases/latest).

- **The cliff cutscene after the first house plays smoothly again** ([#45](https://github.com/lamb2k/re4dc/issues/45)).
  The scenery now shares repeated corner points, which leaves the cutscene enough memory.
- **No skipped effect sprites in r117** after the Saddler scene starts ([#46](https://github.com/lamb2k/re4dc/issues/46)).
- **Back to the earlier character drawing.** Test 19's new path for Leon and the enemies measured slower, so 19.1
  goes back to the one before it. The picture is the same.

## What's new in Test 19

Quick weapon select, new Options defaults and faster drawing, still up to the castle gate. Full details are in the
[release notes](https://github.com/lamb2k/re4dc/releases/latest).

- **Quick weapon select.** Hold X and press the D-pad to swap weapons, like the RE4 remake: up handguns, right
  shotguns, down grenades, left rifles. Press the same direction again for the next one. The game pauses for a moment
  while the weapon loads.

  ![Quick weapon select](docs/images/releases/test-19/quick-weapon.jpg)
  <br>A quick swap in play. Flycast capture, test 19.
- **New Options defaults.** Foliage starts Off and view distance starts at Near. The lake keeps its long view. You can
  still change both in Options.

  ![The Options screen](docs/images/releases/test-19/options-defaults.jpg)
  <br>The Options screen at boot. Flycast capture, test 19.
- **The Player's Manual shows the Dreamcast pages** ([#44](https://github.com/lamb2k/re4dc/issues/44)), not the
  GameCube ones.

  ![The Player's Manual](docs/images/releases/test-19/manual-page.jpg)
  <br>A Dreamcast manual page. Flycast capture, test 19.
- **Enemies hidden behind walls are no longer drawn.** The game still runs them as before.
- **Faster drawing.** A new path for the scenery and for Leon and the enemies, with the same picture.

## What's new in Test 18

Fixes and a little more speed, still up to the castle gate. Full details are in the [release notes](https://github.com/lamb2k/re4dc/releases/latest).

- **Fix: chapter 2-1 can now be finished** ([#40](https://github.com/lamb2k/re4dc/issues/40)). The Insignia Key for
  the church is given at the gate to the dam, which isn't in the game yet.

  ![The Insignia Key at the dam gate (r11b)](docs/images/releases/test-18/key-at-dam-gate.jpg)
  <br>The key, given at the dam gate. Flycast capture, test 18.
- **A lighter El Gigante** in both fights.

  ![El Gigante (r11e)](docs/images/releases/test-18/el-gigante-g50.jpg)
  <br>The lighter El Gigante. Flycast capture, test 18.

- **Leon and El Gigante keep their PS2 models** for the whole first El Gigante fight (r119). Before, both switched to
  the GameCube models for a moment.

  ![Leon and El Gigante (r119)](docs/images/releases/test-18/r119-leon-gigante.jpg)
  <br>Leon and El Gigante, both PS2 models. Flycast capture, test 18.

- **Leon keeps his PS2 model after a chainsaw kill**, for the whole death scene.

  ![Leon after a chainsaw kill](docs/images/releases/test-18/leon-chainsaw.jpg)
  <br>Leon's death scene, PS2 head. Flycast capture of the test 18 program in a castle test room.

- **Effect pictures are there right after loading a save** in r102 ([#33](https://github.com/lamb2k/re4dc/issues/33)).

- **A little faster in play.** Leon's jacket movement is worked out only for pictures that are shown.
- **A little faster in the village and at the farm.** Mist sheets the PS2 version never shows are no longer moved, and more scenery stays ready in memory.
- **No more disc reads for pictures** during the first house fight (r100) and at the night lake shore (r11b).
- **No sound gap in cutscenes** ([#38](https://github.com/lamb2k/re4dc/issues/38)). The Mendez cutscene still ends as
  soon as you pass its button prompt, as in the original game.
- **The world picture and the effect pictures on the way to the castle gate are back** ([#39](https://github.com/lamb2k/re4dc/issues/39)).
  For about a second in r200, some effect sprites can still be skipped ([#41](https://github.com/lamb2k/re4dc/issues/41)).

## Coming soon: Test 23

Planned, with no date yet. Ticked items have passed our checks and will be in Test 23.

- [ ] **Chapter 3-1 playable:** the castle's first part, past the gate (Test 24).
- [ ] **Mipmaps in more places**, with the room texture memory arranged to fit them.
- [ ] **Less scenery drawn when it can't be seen** (Test 24).
- [x] **Faster inventory.**
- [x] **A better-looking El Gigante up close.**
- [x] **River water:** the cave river, the dam river by the water wheel and the merchant cave pool now draw their PS2 water ([#55](https://github.com/lamb2k/re4dc/issues/55)).
- [x] **Trap explosions:** tree and door traps now explode with fire ([#55](https://github.com/lamb2k/re4dc/issues/55)).
- [x] **Missing gears:** the lever gears stay drawn and turn ([#52](https://github.com/lamb2k/re4dc/issues/52)).
- [x] **Castle gate texture:** the one picture at the castle gate that failed its check now loads.
- [x] **Mendez keeps fighting:** he no longer freezes after grabbing Leon, and his bear hug holds ([#55](https://github.com/lamb2k/re4dc/issues/55)).
- [x] **Steady barn lights:** the light in Mendez's barn no longer flickers, and effects in busy rooms stop dropping out ([#55](https://github.com/lamb2k/re4dc/issues/55), [#41](https://github.com/lamb2k/re4dc/issues/41)).
- [x] **No hang on slow disc reads:** a disc read that never finishes now gives up and reads again, for DreamShell and similar loaders ([#28](https://github.com/lamb2k/re4dc/issues/28)).
- [x] **Fewer see-through effects:** mist, glows and dust are cut. Blood, fire, explosions, grenades and the laser sight stay.

- [x] **Boat weapon display:** boarding the boat shows the harpoon and hides handgun ammunition.

- [x] **Effect and puzzle safety:** full effect-pool reuse releases old effects correctly; the church light puzzle handles a missing beam.
- [x] **Dam encounter safety:** a villager that retires while loading is retried instead of being used by the scripted encounter.

## What's new in Test 17.1

A hotfix of Test 17.

- **Coming Soon no longer traps you.** Chapter 2-1 has two ways forward and this test carries one. A door off the
  test's path shows Coming Soon, then returns you to the room so you can take the other exit.

  ![Coming Soon (r11b to r10c)](docs/images/releases/test-17.1/flycast-coming-soon-r11b-r10c.png)
  <br>The Coming Soon screen. Flycast capture, test 17.1.

## What's new in Test 17

Chapters 2-2 and 2-3 are playable, up to the castle gate.

- **Chapters 2-2 and 2-3.** The cabin siege with Luis, Mendez, the second El Gigante and the truck ride to the
  castle gate (r200), with the PS2 enemy lists. At most 4 Ganados at once, as in chapter 1.

  ![Leon in the cabin (r11c)](docs/images/releases/test-17/chapter2-siege.jpg)
  <br>In the cabin, chapter 2-2. Flycast capture, test 17.

- **PS2 Ashley** in every room she follows Leon.

  ![Leon and Ashley (r11e)](docs/images/releases/test-17/ashley.jpg)
  <br>Leon and Ashley. Flycast capture, test 17.

- **Mendez and El Gigante as lighter PS2 models** in their fights.

  ![El Gigante (r11e)](docs/images/releases/test-17/el-gigante.jpg)
  <br>El Gigante. Flycast capture, test 17.

- **Rain at the night lake** ([#30](https://github.com/lamb2k/re4dc/issues/30)): 320 falling streaks, drawn the
  Dreamcast way. It is cheaper than the old faint lines.

  ![Rain at the night lake (r11b)](docs/images/releases/test-17/night-rain.jpg)
  <br>Rain at the night lake. Flycast capture, test 17.

- **The castle gate (r200)** is the end of this test.

  ![Outside the castle (r200)](docs/images/releases/test-17/castle-gate-r200.jpg)
  <br>Outside the castle, where this test ends. Flycast capture, test 17.

- **Solid scenery draws solid** in every chapter 2 room too (the 16.5 change). The new rooms look the same.
- **Fewer pauses in fights.** The Ganado animations the fights use load with the room, and Ganados that lose their
  head keep their PS2 model.
- **Short view distance** draws a simplified far view in the first area and the village.
- **The small picture missing in r118 is back** ([#37](https://github.com/lamb2k/re4dc/issues/37)).

## Play it

One download plays on a real Dreamcast with GDEMU, or in Flycast. No BIOS or VMU saves are included.

| File on the release page | What it is |
| --- | --- |
| `RE4DC-Console-Test-...-GDEMU.zip` | The game disc. This is the one to download. |
| `SHA256SUMS.txt` | Checksums for the zips. |
| `RE4DC-Test18-...-Build-Assets.zip` | Only for building the program from source. Not needed to play. |

**On a Dreamcast with GDEMU:**

1. Extract the zip.
2. Copy the four files inside `gdemu` into a new numbered folder on the SD card. Keep the file names.
3. Replace any older test folder. Do not mix track files from two tests.
4. If your card manager offers "Shrink GDI", leave it off.

**In Flycast:**

1. Extract the zip. Do not open the zip itself.
2. Open `gdemu/disc.gdi` from the extracted folder, with the track files beside it.

**Flycast tips** (from [#35](https://github.com/lamb2k/re4dc/issues/35), seen in Flycast 2.7):

- **Turn off Widescreen, Widescreen Game Cheats and Super Widescreen.** The game draws 4:3; widescreen shows undrawn side areas.
- **Broken menu or popup text?** Use Flycast's per-pixel renderer setting.

The disc is a standard GD-ROM image, laid out like a pressed disc
([section 8 of CONTRIBUTING-PORT.md](port/dreamcast/CONTRIBUTING-PORT.md#8-disc-image-and-compatibility)).

| Action | Dreamcast pad |
| --- | --- |
| Move | Analog stick |
| Aim / fire | Hold R, press A |
| Action / talk / pick up | A |
| Run / cancel | B |
| Knife | L |
| Inventory | Y |
| Quick weapon (from Test 19) | Hold X, press the D-pad: up handguns, right shotguns, down grenades, left rifles and others. Press again for the next one. |
| Pause / options | START |
| Speed display on / off | Hold R, press START |

**Options:**

- **Frame pacing:** Fast is the default. Saved on the VMU.
- **Rendering:** Standard (default) or FSAA, which smooths edges but is slower in busy scenes.
- **View distance:** Full (as on the PS2), Near or Short. Near and Short fade distant scenery sooner and run faster. From Test 19 every boot starts at Near; the lake always keeps its full view.
- **Foliage:** Full, Near or Off. Off is fastest; walls, floors and water always draw. From Test 19 every boot starts at Off (Near before).
- Rendering, View distance and Foliage reset at every boot.

The VMU in controller slot 1 shows Leon, Ashley, Hunnigan and Luis pages.

## Known issues

The full, current list is [KNOWN_ISSUES.md](port/dreamcast/docs/KNOWN_ISSUES.md). The top open items:

- **Some effect sprites skipped for about a second** in r200, at the castle gate ([#41](https://github.com/lamb2k/re4dc/issues/41)).
- **Pauses when entering rooms.**

## Help out

**Testers:** use the [Game bug form](https://github.com/lamb2k/re4dc/issues/new/choose).

- **Say** the build, the room or chapter, the steps, and Flycast or Dreamcast (with your loader).
- **Attach** a screenshot or video. For a console crash, a clear photo of the whole diagnostic screen.
- **One bug per issue.**

**Contributors:**

- **Clone with submodules:** `git clone --recurse-submodules https://github.com/lamb2k/re4dc.git` (SH4ZAM is a submodule).
- **Build and swap in one command:** `bash port/dreamcast/contrib.sh` builds your program and puts it on the latest test disc.
- **Read first:** [CONTRIBUTING-PORT.md](port/dreamcast/CONTRIBUTING-PORT.md), then [CLAUDE.md](CLAUDE.md) or
  [AGENTS.md](AGENTS.md) ("Outside contributors start here").
- **Branch from `dreamcast-port`:** one change per PR, behind a default-off knob, no game data.

## How it works

The original game logic, with a Dreamcast-native picture.

- **Recovered GameCube code** runs the gameplay, collision and enemy AI, built for the SH-4 with KallistiOS.
- **A native PowerVR renderer** replaces the GameCube graphics.
- **PS2 room and character assets,** converted offline, are lighter for the Dreamcast.
- **VMU saves** stand in for the memory card, and **cutscene movies stream** from the disc.

<p>
<img src="docs/images/04-village.jpg" width="32%"> <img src="docs/images/05-farm.jpg" width="32%"> <img src="docs/images/10-mendez.jpg" width="32%">
</p>

More in the [port notes](port/dreamcast/README.md), the [build recipes](port/dreamcast/tools/d367/README.md),
[engine overview](docs/overview.md).

## Credits and legal

Built on the [RE4 GameCube decompilation](docs/DECOMPILATION.md),
[KallistiOS](https://github.com/KallistiOS/KallistiOS) and [Flycast](https://github.com/flyinghead/flycast).
Third-party code in the program and its licences: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
An independent fan project for research and preservation, not affiliated with Capcom, Sega or Nintendo.
Resident Evil is a Capcom trademark; game code and data belong to their owners. Project tools and
documentation are [CC0](LICENSE).
