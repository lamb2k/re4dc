![RE4 Dreamcast](docs/images/title.jpg)

# RE4 Dreamcast

**An experimental Resident Evil 4 port for the Sega Dreamcast.**

The recovered GameCube code runs the gameplay, collision and enemy AI. A native PowerVR renderer,
lighter PS2 room assets, streamed movies and VMU saves adapt it to Dreamcast hardware.

**[Download the latest GDEMU test build](https://github.com/lamb2k/re4dc/releases/tag/test-c29c4bf5-20261011)** ·
[Known issues](port/dreamcast/docs/KNOWN_ISSUES.md) · [Roadmap](port/dreamcast/docs/D367_THIRTY_FPS_ROUTE.md) ·
[Port notes](port/dreamcast/README.md) · [Build the port](port/dreamcast/CONTRIBUTING-PORT.md) · [Decompilation](docs/DECOMPILATION.md)

## Contributing

One command builds your own program and puts it on the latest test disc: `bash port/dreamcast/contrib.sh`.
See [CONTRIBUTING-PORT.md](port/dreamcast/CONTRIBUTING-PORT.md); contributors and their coding agents should then read
[CLAUDE.md](CLAUDE.md) or [AGENTS.md](AGENTS.md) (section "Outside contributors start here").

For original-disc asset work, [the PS2 asset build guide](port/dreamcast/docs/PS2_ASSET_BUILD.md)
identifies the supported USA `SLUS_211.34` source and the new `make assets` world workflow
(56 room recipes, default r102/r106), including the remaining GameCube dependencies and full-disc build gaps.

## Playing

The latest build is console test `c29c4bf5` (r22j test 7). Desktop packages will return with a later test build;
until then, play the console test in Flycast. Extract the complete package:

| System | Download | Launch |
| --- | --- | --- |
| Dreamcast / GDEMU | [Console test ZIP](https://github.com/lamb2k/re4dc/releases/download/test-c29c4bf5-20261011/RE4DC-Console-Test-c29c4bf5-20261011-GDEMU.zip) | Copy the four files inside `gdemu` into a new numbered SD card folder. |

[Test build checksums](https://github.com/lamb2k/re4dc/releases/download/test-c29c4bf5-20261011/SHA256SUMS.txt) · [Test notes](https://github.com/lamb2k/re4dc/releases/tag/test-c29c4bf5-20261011)

Already have Flycast? Open `gdemu/disc.gdi` from the console test ZIP, keeping all track files beside it.
For GDEMU, keep filenames unchanged and save any card-manager changes before ejecting the card.
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
| Speed display: Off → VMU → Screen → Both | Hold R, press START |

Options has the Frame pacing and Rendering (Quality, Standard, Fast) rows; Fast pacing and Quality are the defaults.
The speed display shows the frame rate and game speed on a VMU in controller slot 1, on screen, or both.

## Status and limitations

**Console test `c29c4bf5` (r22j test 7), October 11, 2026:** the game plays to the end of chapter two, part one
(the lake and the boat ride, the wolves, the El Gigante fight, finding Ashley and the chapter results),
up to a **Coming Soon** screen. This is a prerelease, not the complete game.

Recent progress:

* PS2 models for Leon in both outfits, the villagers, El Gigante and the lake monster.
* Look test: two options, Current and GameCube (hold X, press START). Please vote in the
  [look test issue](https://github.com/lamb2k/re4dc/issues/22).
* Soft shadows and blended ground layers instead of solid black shapes.
* The bridge door freeze is fixed, confirmed on a real console.
* Music and voices rebuilt to remove crackling and clipping; the chapter results music is back.
* Error screens show more detail for bug reports.

Known issues (full list: [KNOWN_ISSUES.md](port/dreamcast/docs/KNOWN_ISSUES.md)):

* **Stability:** random crashes on a real console (fixed for test 9); a few menu and save actions can stop the game.
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
documentation are [CC0](LICENSE), except attributed third-party helpers with their own
[notices](port/dreamcast/tools/ps2_assets/README.md).
