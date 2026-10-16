![RE4 Dreamcast](docs/images/title.jpg)

# RE4 Dreamcast

**An experimental Resident Evil 4 port for the Sega Dreamcast.**

The recovered GameCube code runs the gameplay, collision and enemy AI. A native PowerVR renderer,
lighter PS2 room assets, streamed movies and VMU saves adapt it to Dreamcast hardware.

**[Download the latest GDEMU test build](https://github.com/lamb2k/re4dc/releases/latest)** ·
[Known issues](port/dreamcast/docs/KNOWN_ISSUES.md) · [Roadmap](port/dreamcast/docs/D367_THIRTY_FPS_ROUTE.md) ·
[Port notes](port/dreamcast/README.md) · [Build the port](port/dreamcast/CONTRIBUTING-PORT.md) · [Decompilation](docs/DECOMPILATION.md)

## Contributing

Clone with `git clone --recurse-submodules https://github.com/lamb2k/re4dc.git` (the SH4ZAM maths library is a git
submodule). One command then builds your own program and puts it on the latest test disc: `bash port/dreamcast/contrib.sh`.
See [CONTRIBUTING-PORT.md](port/dreamcast/CONTRIBUTING-PORT.md); contributors and their coding agents should then read
[CLAUDE.md](CLAUDE.md) or [AGENTS.md](AGENTS.md) (section "Outside contributors start here").

## Playing

The latest build is console test 13 (test 12.2 plus the PS2 enemy rules in every chapter 1 room with at most 6 villagers active at once, PS2 room objects after the village with the dark box debris fixed, the PS2 Ashley, and less work per frame in the village). Desktop packages will return with a later test build;
until then, play the console test in Flycast. Extract the complete package:

| System | Download | Launch |
| --- | --- | --- |
| Dreamcast / GDEMU | Console test ZIP (`RE4DC-Console-Test-...-GDEMU.zip`) on the [latest release](https://github.com/lamb2k/re4dc/releases/latest) | Copy the four files inside `gdemu` into a new numbered SD card folder. |

The release page also has the test build checksums (`SHA256SUMS.txt`) and the test notes.

Already have Flycast? Open `gdemu/disc.gdi` from the console test ZIP, keeping all track files beside it.
For GDEMU, keep filenames unchanged and save any card-manager changes before ejecting the card.
Disc format: from test 16 the disc is a standard GD-ROM image (the layout of pressed GD-ROMs, as the mkdcdisc tool
writes it; `track03.bin` is about 1.2 GB), which fixes the GDEMU-only freezes of earlier tests; leave "Shrink GDI" off.
See [section 8 of CONTRIBUTING-PORT.md](port/dreamcast/CONTRIBUTING-PORT.md#8-disc-image-and-compatibility).
No BIOS or personal VMU saves are included; keep your existing saves separately.

| Action | Dreamcast pad |
| --- | --- |
| Move | Analog stick |
| Aim / fire | Hold R, press A |
| Action / talk / pick up | A |
| Run / cancel | B |
| Knife | L |
| Inventory | Y |
| Pause / options | START |
| Speed display: Off → On screen | Hold R, press START |

Options has the Frame pacing row (Fast is the default), the Rendering row, the View distance row and the Foliage row. Rendering is
Standard (the default, the full 640x480 picture) or FSAA, which smooths edges by drawing twice the pixels and is
slower in busy scenes. View distance is how far the scenery is drawn: Full (the default, as on the PS2), Near or
Short. Near and Short fade the distant scenery into the fog sooner, which makes busy outdoor scenes faster; the
game plays the same. Inside a house the room around you stays clear, and only what you see through the doors and
windows fades. In the first area and the village, Short draws a simplified copy of the distant scenery
instead, so houses, trees and the hills stay in view. The lake always shows its full horizon. Foliage is how the see-through brush and leaf cards outdoors
are drawn: Near (the default) draws the leaf and brush cards with sharp edges and only up to about 12 m, where the
fog hides them anyway, which makes the woods faster; Full draws all of them blended, as on the PS2; Off leaves them
out, with the soft shadow and grass cards (fastest; walls, floors and water are always drawn). FSAA, View distance
and Foliage last until the console is switched off; every boot starts in Standard, Full and Near.
The speed display shows the frame rate and game speed on screen; it is off unless you switch it on.
The VMU in controller slot 1 shows Leon, Ashley, Hunnigan and Luis pages.

## Status and limitations

**Console test 13, October 15, 2026:** the game plays to the end of chapter two, part one
(the lake and the boat ride, the wolves, the El Gigante fight, finding Ashley and the chapter results),
up to a **Coming Soon** screen. This is a prerelease, not the complete game.

Recent progress:

* Test 13: the PS2 enemy rules in every chapter 1 room, with at most 6 villagers active at once; PS2 room
  objects from r102 to r11b with the GameCube breakable boxes (no more dark debris); the PS2 Ashley; less work per
  frame in the village; fewer disc reads in r103 and r100 after the village.
* Test 12: PS2 models for the room objects in the first two villages, the items you pick up, the villagers' caps
  and the merchant; a brighter Leon; at most 6 villagers attack at once; the radio call crash is fixed
  (confirmed on a real console).
* Fixes for the random console crashes and broken textures of test 7 and test 8 (please confirm on a console).
* Doors hold the last picture and fade to black, with the PS2 Loading banner.
* The village fight follows the PS2 rules: fewer villagers at once, new waves when fewer than 5 are left.
* VMU pages for Leon, Ashley, Hunnigan and Luis; the speed display setting is saved.
* PS2 models for Leon in both outfits, the villagers, the animals, El Gigante and the lake monster.
* The bridge door freeze is fixed, confirmed on a real console.

Known issues (full list: [KNOWN_ISSUES.md](port/dreamcast/docs/KNOWN_ISSUES.md)):

* **Stability:** random crashes on a real console (fixed in test 9, needs a console check); a few menu actions can stop the game;
  the r100 cliff cutscene is skipped (test 12).
* **Picture:** some textures are missing; water, ripples and shadows are incomplete; characters are not lit by the scene.
* **Sound:** the rifle sound is lower quality.
* **Performance:** below the 30 fps / full speed target; pauses when entering rooms.

## Development

The GameCube C/C++ builds for SH-4 with KallistiOS. Dreamcast code replaces graphics, audio, disc and
memory-card services; offline tools convert room worlds, characters and textures from original data.
Game data is not committed. Rendering changes must preserve gameplay, checked with matching logic traces.

<p>
<img src="docs/images/dev/ganado-ps2-look.jpg" width="49%" alt="Ganado model from the PS2 version, prepared for the Dreamcast">
<img src="docs/images/dev/r104-world-sheet.jpg" width="49%" alt="r104 world rebuilt from PS2 room data, review sheet">
</p>
<p>
<img src="docs/images/dev/prompt-glyphs.jpg" width="49%" alt="The game's button-prompt glyphs, extracted for the native UI renderer">
<img src="docs/images/dev/manual-vq.jpg" width="49%" alt="Player's Manual page: original texture against PowerVR VQ">
</p>

Asset work: a PS2 Ganado, the r104 world, button glyphs and a Player's Manual texture before/after VQ compression.

Start with the [build recipes](port/dreamcast/tools/d367/README.md),
[room coverage](port/dreamcast/docs/R4_FIRST_STAGE_GAP_AUDIT.md) and [engine overview](docs/overview.md).
Contributions branch from `dreamcast-port`: one change per PR, relevant before/after checks, no game data.

## Pictures

Captured in Flycast from the play builds.

<p>
<img src="docs/images/01-intro.jpg" width="32%"> <img src="docs/images/02-radio.jpg" width="32%"> <img src="docs/images/03-forest.jpg" width="32%">
<img src="docs/images/04-village.jpg" width="32%"> <img src="docs/images/05-farm.jpg" width="32%"> <img src="docs/images/06-woods.jpg" width="32%">
<img src="docs/images/07-cutscene.jpg" width="32%"> <img src="docs/images/08-vmu-save.jpg" width="32%"> <img src="docs/images/09-r104.jpg" width="32%">
<img src="docs/images/10-mendez.jpg" width="32%"> <img src="docs/images/11-chapter-end.jpg" width="32%">
</p>

## Reporting bugs

[Open a Game bug issue](https://github.com/lamb2k/re4dc/issues/new/choose) with the build, room/chapter,
steps to reproduce, system (Flycast or Dreamcast), and a screenshot or video. On Windows, attach the
newest game log from `logs/`. For a console crash, include the Frame pacing setting and a clear photo
of the complete diagnostic screen. One bug per issue.

## Credits

Built on the [RE4 GameCube decompilation](docs/DECOMPILATION.md),
[KallistiOS](https://github.com/KallistiOS/KallistiOS) and [Flycast](https://github.com/flyinghead/flycast).
An independent fan project for research and preservation, not affiliated with Capcom, Sega or Nintendo.
Resident Evil is a Capcom trademark; game code and data belong to their owners. Project tools and
documentation are [CC0](LICENSE).
