![RE4 Dreamcast](docs/images/title.jpg)

# RE4 Dreamcast

**Resident Evil 4 runs on the Sega Dreamcast, from New Game to the end of chapter 2-3 at the castle gate.**

It is the GameCube game's own recovered code, not a remake, drawn by a native Dreamcast renderer.
This is an experimental fan test build, not the complete game.

**[Download Test 18](https://github.com/lamb2k/re4dc/releases/latest)** · [Known issues](port/dreamcast/docs/KNOWN_ISSUES.md) ·
[Port notes](port/dreamcast/README.md) · [Build the port](port/dreamcast/CONTRIBUTING-PORT.md) · [Decompilation](docs/DECOMPILATION.md)

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

## Coming soon: Test 19

Planned, with no date yet. Ticked items have passed our checks and will be in Test 19.

- [ ] **Chapter 3-1 playable:** the castle's first part, past the gate.
- [x] **Faster character drawing:** a new path for Leon and the enemies.
- [x] **New Options defaults:** foliage starts Off and view distance starts at Near. The lake keeps its long view. You can still change both.
- [ ] **Enemies hidden behind walls are no longer drawn.**
- [ ] **Quick weapon select:** hold X and press the D-pad to swap weapons, like the RE4 remake.
- [ ] **Work continues** on cheaper enemies and cheaper scenery.

Screenshots come with the release.

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
