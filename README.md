![RE4 Dreamcast](docs/images/title.jpg)

# RE4 Dreamcast

**An experimental Resident Evil 4 port for the Sega Dreamcast.**

The recovered GameCube code runs the gameplay, collision and enemy AI. A native PowerVR renderer,
lighter PS2 room assets, streamed movies and VMU saves adapt it to Dreamcast hardware.

**[Download the combined GDEMU test build](https://github.com/lamb2k/re4dc/releases/tag/test-combined-254eab36-20261008)** ·
[Roadmap](port/dreamcast/docs/D367_THIRTY_FPS_ROUTE.md) ·
[Port notes](port/dreamcast/README.md) · [Decompilation](docs/DECOMPILATION.md)

## Playing

The latest console test is build `254eab36`. The desktop packages below are the earlier r22j build.
Extract the complete package for your system:

| System | Download | Launch |
| --- | --- | --- |
| Windows (r22j) | [RE4DC-r22j.zip](https://github.com/lamb2k/re4dc/releases/download/play-r22j-audio-performance-20261007/RE4DC-r22j.zip) | Double-click `Play-r22j.cmd`. Includes Flycast and keyboard/DualSense support. |
| Steam Deck / SteamOS (r22j) | [SteamOS package](https://github.com/lamb2k/re4dc/releases/download/play-r22j-audio-performance-20261007/RE4DC-r22j-SteamOS.tar.gz) | In Desktop Mode, run `play.sh`; uses Flathub Flycast. |
| CachyOS / Arch (r22j) | [CachyOS package](https://github.com/lamb2k/re4dc/releases/download/play-r22j-audio-performance-20261007/RE4DC-r22j-CachyOS.tar.gz) | Run `./play.sh`; uses native or Flathub Flycast. |
| Dreamcast / GDEMU | [Combined test ZIP](https://github.com/lamb2k/re4dc/releases/download/test-combined-254eab36-20261008/RE4DC-Combined-Console-Test-254eab36-20261008-GDEMU.zip) | Copy the four files inside `gdemu` into a new numbered SD card folder. |

[Test build checksums](https://github.com/lamb2k/re4dc/releases/download/test-combined-254eab36-20261008/SHA256SUMS.txt) · [Test notes and verification](https://github.com/lamb2k/re4dc/releases/tag/test-combined-254eab36-20261008) · [r22j desktop checksums](https://github.com/lamb2k/re4dc/releases/download/play-r22j-audio-performance-20261007/SHA256SUMS.txt)

Already have Flycast? Open `gdemu/disc.gdi` from the combined test ZIP, keeping all track files beside it.
For an r22j emulator package, open `disc/disc.cue` and keep its `disc.bin` beside it.
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
| Frame pacing: Smooth → Fast → Off | Hold R, press START |

Fast pacing is the default. A VMU in controller slot 1 shows FPS, game speed, CPU percentage and pacing.

## Status and limitations

**Combined console test `254eab36`, October 8, 2026:** includes corrections to inventory memory
handling, selection glow and grid, Examine textures, herb/fish and other inventory textures,
lamp fire, and graphics presentation completion checks.

Flycast checks cover save loading, walking, repeated inventory and Examine, lamp effects and
bridge transitions. The published downloads are hash verified. These checks do not establish
a fix for the original console crashes; physical Dreamcast confirmation is still pending.
See the [test notes](https://github.com/lamb2k/re4dc/releases/tag/test-combined-254eab36-20261008)
and [build checklist](port/dreamcast/docs/D367_PLAY_BUILD_CHECKLIST.md).

The route extends through r10a; the unfinished r10b door shows **Coming Soon**. This is a prerelease,
not the complete game.

* **Stability:** the [bridge door presentation timeout](https://github.com/lamb2k/re4dc/issues/9)
  and [freeze after loading a save and walking](https://github.com/lamb2k/re4dc/issues/2) remain unresolved.
* **Performance:** below the 30 fps/full speed target. This candidate has no new physical console
  performance measurement.
* **Presentation and sound:** some models, effects and textures need work. Rifle sound is lower quality;
  the restored room music and grenade sounds still need listening checks on hardware.
* **Loading and saves:** room entry pauses remain. Normal chapter 1-2 key item pickups and reloading
  a save made inside r106 still need checking.

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
of the complete diagnostic screen. To check the save load freeze, cold boot, load your existing save
and walk before opening inventory. One bug per issue.

## Credits

Built on the [RE4 GameCube decompilation](docs/DECOMPILATION.md),
[KallistiOS](https://github.com/KallistiOS/KallistiOS) and [Flycast](https://github.com/flyinghead/flycast).
An independent fan project for research and preservation, not affiliated with Capcom, Sega or Nintendo.
Resident Evil is a Capcom trademark; game code and data belong to their owners. Project tools and
documentation are [CC0](LICENSE).
