# Contributing to the Dreamcast port

This page gets you from a fresh clone on Linux (or WSL) to your own build of the game running in
Flycast or on a Dreamcast with GDEMU. You build only the program. The game data comes from a
published test release, so you never need the original discs.

## Quick start: one command

On Ubuntu 24.04 (or WSL) install the host packages once:

    sudo apt install build-essential bison flex texinfo libgmp-dev libmpfr-dev libmpc-dev \
        libelf-dev libjpeg-dev libpng-dev git curl python3 genisoimage

Then, from the repository root:

    bash port/dreamcast/contrib.sh

It builds the toolchain the first time (about 11 minutes, into `~/re4dc-toolchain`), downloads the
newest test release and its Build-Assets zip from GitHub and checks them against the release's
`SHA256SUMS.txt`, builds the program, puts it on the release disc and prints the path of
`disc.gdi` (under `port/dreamcast/out-contrib/disc`). Options:

* `--release <tag>` picks a release by its tag (`test-<source commit>-<date>`, as on the releases page).
  An older release needs the `build-public.sh` of its own source commit (see "Which recipe" below).
* `--toolchain <dir>` uses or builds the toolchain there; a toolchain already in the environment
  (`RE4DC_KOS_BASE`) is used as is.
* `KNOB=value` arguments go to the build, for example `bash port/dreamcast/contrib.sh MY_FEATURE=1`.

The Build-Assets zip holds the generated character data the release program was built with, so your
program draws the same characters as the release: built from the release's source commit with its
Build-Assets zip, the program is byte for byte the release's program (the maintainers check this before
every release). Downloads are kept, so a second run only rebuilds.

## Where to read next

These are the documents to give yourself (or your coding agent) before changing code:

* `CLAUDE.md` and `AGENTS.md` at the repository root: the working rules, with a short section for
  outside contributors at the top.
* `port/dreamcast/docs/D367_THIRTY_FPS_ROUTE.md`: goals, decisions and the current state.
* `port/dreamcast/tools/d367/README.md`: the build recipe and what each knob does.
* `port/dreamcast/docs/D367_PLAY_BUILD_CHECKLIST.md`: what goes into a test build.
* `port/dreamcast/tests`: unit tests for the tools (`python3 -m unittest` in that folder).

The steps below are what `contrib.sh` does, for when you want to run them by hand.

## 1. Toolchain

You need the exact toolchain the maintainers use: KallistiOS commit 804b3195 with the three patches in
`patches/`, the KOS "stable" SH4 compiler (GCC 15.2.0, binutils 2.45.1, newlib 4.6.0.20260123), and
kos-ports with its sh4zam port installed (SH4ZAM, the SH4 maths library by Falco Girgis and contributors, MIT).

**SH4ZAM.** The game uses SH4ZAM from kos-ports, not a copy in this repository, so upstream fixes and
new features reach us. `toolchain.lock` pins the kos-ports commit (`KOS_PORTS_SHA`) and the SH4ZAM
upstream commit (`SH4ZAM_SHA`); `tools/install-sh4zam.sh` checks kos-ports out at its pin and runs
`make install GIT_CHANGESET=$SH4ZAM_SHA` in `kos-ports/sh4zam`, which installs the headers into
`kos-ports/include/sh4zam` and `libsh4zam.a` into `kos-ports/lib` (the build reads them through
`KOS_PORTS`, i.e. `RE4DC_KOS_PORTS`). The setup script and `contrib.sh` run it for you. To update
SH4ZAM, bump `SH4ZAM_SHA` (and `KOS_PORTS_SHA` if the port itself changed) in `toolchain.lock`, rerun
`tools/install-sh4zam.sh`, rebuild, and gate the change like any other (render-only users: stills and
logic STRICT; logic users: decisions-identical).

**Script.**

    bash port/dreamcast/tools/setup-toolchain.sh ~/re4dc-toolchain
    . ~/re4dc-toolchain/env.sh

It took 11 minutes on 12 threads in a clean directory and needs about 6 GB free while it builds.
The finished toolchain is 402 MB.

**Docker.** From the repository root (this image runs the same script; the maintainers have tested
the script, not yet the image):

    docker build -t re4dc-toolchain -f port/dreamcast/docker/Dockerfile .
    docker run --rm -it -v "$PWD":/src re4dc-toolchain bash port/dreamcast/contrib.sh

## 2. Build the program

    ASSETS=<unpacked Build-Assets zip>/re4dc-assets bash port/dreamcast/build-public.sh

This builds the current test recipe into `port/dreamcast/out-public`: `re4dc-game.elf`, the room
overlays (`*.ovl`) that belong to it, and `resolved-knobs.txt` with every build knob as make saw it.
Add your own knobs at the end, for example `bash port/dreamcast/build-public.sh MY_FEATURE=1`.

**Which recipe.** `build-public.sh` reads the release's knob file, today
`tools/d367/test14/release-knobs.txt` (test 14; its header names the source commit). The maintainers write that file from
the release build itself, so it is the exact knob list of the published program. To build an older
release, check out that release's source commit: its `build-public.sh` points at its own knob file.

Without `ASSETS` the build uses `game/public-assets`, neutral stand ins that carry no game data, and
switches these release knobs off (`PRIVATE_OFF` in `build-public.sh`). The game plays the same; it looks
different from the release:

* `PS2_LEON=0 LEON_HAND_PACK=0`: Leon is the GameCube model (the release draws the PS2 Leon, also in
  every hand pose).
* `PS2_GANADO=0 PS2_GANADO_LIT=0`: the male villagers are the GameCube models (the release draws the
  PS2 models with the PS2 lighting).
* El Gigante, Del Lago, the female villagers, the animals, Ashley, the PS2 room objects and the PS2 room
  worlds (with the village's baked doors, windows and racks) come from the disc, so they draw as in the
  release.
* Leon and the villagers draw from the original GameCube models on the disc instead of the converted
  meshes. They cost more time to draw, so do not compare speed with the release.
* The memory card messages show the GameCube wording ("Memory Card in Slot A") instead of the VMU wording.

Either way, measure your change against your own build with the change switched off.

## 3. Put it on a release disc

    python3 port/dreamcast/tools/swap-program.py RE4DC-Console-Test-<commit>-<date>-GDEMU.zip \
        port/dreamcast/out-public mydisc

`mydisc` gets `disc.gdi` and its three tracks: the release disc with your program as the boot file and
your overlays in place. Everything else on the disc is unchanged. Use a release made from the same or a
close source revision; a program much newer than the release may need data files the release lacks.

To start a new game by itself (useful for repeatable tests), add the scripted pad file:

    ... mydisc --add dc/padscript.txt=port/dreamcast/tools/padscript-newgame.txt

Do not use that disc for normal play: the script presses buttons at fixed times.

## 4. Run it

**Flycast:** open `mydisc/disc.gdi`. Keep the track files beside it.

**GDEMU:** copy the four files into a new numbered folder on the SD card.

## 5. Speed display

Test builds show their speed on the VMU in controller slot 1: drawn frames per second, game speed,
CPU percentage and the frame pacing mode. Hold R and press START to cycle the frame pacing
(Smooth, Fast, Off). Builds that also have the on screen display use R and START to cycle the display
instead: Off, VMU, Screen, Both. Hold X and press START to switch the look preset.

## 6. Send a patch

* Put every change behind a build knob whose default is 0, so the default program does not change.
  The knob goes in the makefiles under `game/` with a comment saying what it does.
* Check the knob off identity yourself: with the knob at 0, `build-public.sh` must produce the same
  program bytes as before your patch. Compare `sh-elf-objcopy -R .stack -O binary re4dc-game.elf p.bin`
  of both builds with `sha256sum`.
* Describe the gain in milliseconds per frame, and say where you measured it: the room, the camera
  view and how many enemies were on screen. Numbers from a fight with villagers in view matter most.
* Say what the change looks like, with a screenshot pair (knob off, knob on) if it changes the picture.
* Open a pull request against the `dreamcast-port` branch.

The maintainers then run the gameplay identity gates before a change goes into a test build. They
replay recorded sessions and compare the game logic tick by tick, so a render change must leave the
gameplay exactly as it was (STRICT). That harness uses private recordings, so you do not need to
run it; a change that touches collision, events, game state or AI will not be accepted.

## 7. A full disc from your own discs

You do not need this to work on the code. A whole disc (not only the program) can only be built from
your own copies of the games; the repository holds the tools and recipes, never game data. Today that
path is not one command: several outputs are frozen results of conversion and review work that the
maintainers keep outside the repository.

| Source you need | What the port makes from it | Rebuilt by a script from the disc? |
| --- | --- | --- |
| GameCube Resident Evil 4 debug disc 1 (G4BE08, extracted file tree) | base disc tree: rooms, enemies, sound banks, menus | mostly (`tools/le_mirror.py`, `tools/d367/stage.sh`, `tools/aica_banks.py disc`) |
| same | Dreamcast room meshes (`dc/native/rXXX/MAINSCENARIO.re4mesh`) | yes, per room (`tools/convert_room_bins.py`) |
| same | room archives with Dreamcast audio (`st1/rXXX.dar`) | per room steps, not one command |
| same plus game run logs | texture package `dc/tex.pak` (VQ textures) | no: the VQ selection comes from logs of test runs |
| none (the lists are in the repository, made from game run logs) | per-room resident texture lists `dc/resident.bin` (ROOM_RESIDENT) | yes (`tools/d367/vram/resident_keys.py pack` of `tools/d367/vram/resident/r*.tsv`) |
| PS2 Resident Evil 4, USA (SLUS 21134), `BIO4MOV.AFS` | cutscene movies `dc/movie/*.seq` | yes (`tools/convert_route_movies.py`, needs ffmpeg) |
| PS2 USA, `BIO4DAT.AFS` rooms (plus two JADERLINK unpack tools) | PS2 room worlds `dc/native/rXXX/ps2-world.*` | converters exist; the released set is a reviewed frozen output |
| PS2 USA characters | PS2 Leon and villager meshes (compiled into the program), registry packs, pl08 pack | no: needs Blender and review steps |
| none (made by hand or by tools) | title art, look presets, glyphs, character bakes, test scripts | no |

No PC version and no GameCube retail disc are used. The second GameCube debug disc is used only by
the decompilation build.

## Release checklist (maintainers)

On every test release, in the same landing as the release recipe, before the release publishes:

1. Refresh the knob file from the release's play build:
   `python3 port/dreamcast/tools/d367/release-knobs.py write <out-<label>>/candidate.txt
   port/dreamcast/tools/d367/<test>/release-knobs.txt --test N --tag <tag> --source <sha> --recipe <t-build.sh>
   --image-sha256 <sha256 of sh-elf-objcopy -R .stack -O binary> --assets-zip <name>`.
2. Point `RELEASE_KNOBS` in `build-public.sh` at it (one line), and update the release names in this page.
3. Make the Build-Assets zip from the recipe (`release-knobs.py zip <candidate.txt> <zip>`), not by hand.
4. Run `tools/d367/kit-check.sh <knob file> <out-<label>> <package dir>` (knob file = recipe, zip = recipe,
   these docs name no older release, a clean checkout of the release commit rebuilds the release program
   byte for byte, builds without assets, swaps onto the release disc), then `tools/d367/kit-boot.sh <WORK>`
   (the swapped discs boot to New Game and r101 in Flycast). A release does not publish until both pass.

## Questions

Open an issue. The build notes for maintainers are in `tools/d367/README.md`, and the port notes are
in `README.md` in this folder.
