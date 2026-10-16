# Contributing to the Dreamcast port

This page gets you from a fresh clone on Linux (or WSL) to your own build of the game running in
Flycast or on a Dreamcast with GDEMU. You build only the program. The game data comes from a
published test release, so you never need the original discs.

## Quick start: one command

On Ubuntu 24.04 (or WSL) install the host packages once:

    sudo apt install build-essential bison flex texinfo libgmp-dev libmpfr-dev libmpc-dev \
        libelf-dev libjpeg-dev libpng-dev git curl python3 genisoimage

Clone with the submodules (SH4ZAM is one, see section 1):

    git clone --recurse-submodules https://github.com/lamb2k/re4dc.git

(in a clone made without it: `git submodule update --init`). Then, from the repository root:

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
`patches/`, and the KOS "stable" SH4 compiler (GCC 15.2.0, binutils 2.45.1, newlib 4.6.0.20260123).

**SH4ZAM.** SH4ZAM, the SH4 maths library by Falco Girgis and contributors (MIT,
https://github.com/gyrovorbis/sh4zam), is a git submodule at `port/dreamcast/game/third_party/sh4zam`. Its pin
is the submodule commit this repository records, and nothing else (`git submodule status` shows it). The build
reads its headers from there (every SH4ZAM call the port makes is inline, so no `libsh4zam.a` is linked; `make
sh4zam-lib` in `game/` builds one from the submodule with cmake if a change needs it). An empty submodule stops
the build with "run git submodule update --init"; `contrib.sh` runs that for you.

**Bumping SH4ZAM** (to a newer upstream commit):

    cd port/dreamcast/game/third_party/sh4zam            # from the repository root
    git fetch origin && git checkout <new commit>
    cd - && git add port/dreamcast/game/third_party/sh4zam
    git commit -m "SH4ZAM: bump to <new commit>"

Then rebuild and gate it like any other change: the program with every SH4ZAM knob off must stay byte for
byte the same (knob-off identity); the SH4ZAM knobs' users take the release recipe through STRICT (logic is
tick for tick the same; render-only users also get a still pair) and, for the logic users (`SH4_APPROX_LOGIC`,
global `GAME_SH4ZAM`), the decisions check. Others who pull the bump run `git submodule update` once.

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

From test 16 on the release disc is a standard GD-ROM image (section 8), and `swap-program.py` keeps it one
(on an older release disc it appends a longer file after the end of track 3 instead): your
`1ST_READ.BIN` stays the last file and ends where the release's did; if it is longer, the files it would
cover move into the free space in front of the first file, and a file that no longer fits its old place
moves there too. Only the directory records of the changed files are rewritten (IP.BIN with its table of
contents, the volume descriptors and the path tables stay as they are), every changed sector gets its
error-correction codes again, and the tool reads the new disc back before it finishes. Then check it:

    python3 port/dreamcast/tools/d367/disc_lint.py mydisc/disc.gdi

It must end with `DISC_LINT PASS ... profile=standard violations=0` (`contrib.sh` runs this for you).

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

The player options are the rows in Options (START): Frame pacing (stored on the VMU), Rendering (Standard or FSAA,
knob `RENDER_FSAA`) and View distance (Full, Near or Short, knob `VIEW_DIST_OPTION`: the world is drawn to 25, 18.75
or 12.5 m and the fog reaches full strength there; drawing only, the game logic is unchanged). Two rules refine it
(game/option_rows.cpp): a per-room minimum far table, `kViewRoomMin`, keeps rooms that need their horizon at Full (the
lakes r10b, r11a and r11b); and while the player stands in one of the room's indoor effect areas (the game's
weather-off areas, `Status_flg[1]` 0x02000000) the fog ramp starts behind that area, so a house interior is not
fogged while the scenery seen through its doors and windows still fades out before the cut. Rendering and View
distance are not saved: every boot starts in Standard and Full. Foliage (Full, Near or Off, knobs `FOLIAGE_TRIM`
(the level word and the boot level, hwfog.mk) and `FOLIAGE_OPTION` (the row)): the translucent PS2 world parts whose
texture is a near-binary cut-out (leaf / brush cards, fence gaps; key table platform/include/foliage_keys.inc, built
from an alpha census of the chapter 1 packages) are drawn in the punch-through list up to 12 m at Near, and every listed
card key (classes 1-4, soft shadow / mist / grass cards included) is left out at Off; surfaces without cut-out holes
(walls, floors, water), unlisted keys and the vertex-alpha overlays always draw. It is not
saved either: every boot starts at the recipe's `FOLIAGE_TRIM` level (test 15: Near). Docs: docs/MIST_CUT.md. On a warp test disc (`DBG_WARP=1`) the warp line
`viewdist 0|1|2` starts the run at Full, Near or Short.
Far shell (knob `FAR_SHELL`, needs `VIEW_DIST_OPTION`; game/platform/far_shell.inc): in a room that has a
`dc/native/rXXX/far-shell.fsh` (r100 and r101 in test 15), Short cuts only the world's opaque pass; the fog,
the cut-out and see-through world surfaces, characters and objects keep Full's distance, and the room's far shell (a
simplified copy of the far world, about 3,000 triangles textured with the world's own textures, so no extra graphics
memory) is drawn beyond the cut, so landmarks stay visible. Build a shell with tools/d367/farshell (README there;
Windows Python and Blender 5.2) from the room's PS2 world package. Near, and rooms without a file, keep the plain cut. Warp line
`farshell 0|1|2` (0 = plain cut, 1 = shell, 2 = opaque cut without the shell, for pricing).
Radio call subtitles (knob `RADIO_SUB_RT`, game/subscreen.mk; src/Sscrn/ss_term.cpp): the GameCube steps a call's
subtitle sequence once per 30 Hz sub screen frame, while the voice plays from the AICA in real time. With the knob
each call frame runs the steps owed since the voice began to sound (KOS timer, platform/audio_aica.cpp
`re4dc_aica_stream_started`), so the pages stay with the voice when a call frame takes longer than 1/30 s. The game
is stopped under the sub screen, so logic is unchanged. Test builds can add `RADIO_SUB_LOG=1` for one log line per
subtitle page (time since the voice started).

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

## 8. Disc image and compatibility

The release disc format from test 16 on (decided 2026-10-16; test 15 still ships the old layout). Users had reported freezes and crashes on GDEMU
with this game only ([#27](https://github.com/lamb2k/re4dc/issues/27), "LinkOrder"); the image then was laid out by
our own script and differed from a pressed GD-ROM in several ways (no table of contents in IP.BIN, a data track
that ended with its last file, the program first instead of last, a non-standard low-density track). The same game
mastered in the standard layout below ran fine on the maintainers' GDEMU console on 2026-10-16.

**One image.** Each test release ships one disc image: a standard three-track GD-ROM GDI with raw 2,352-byte
sectors, laid out the way the community tool [mkdcdisc](https://gitlab.com/simulant/mkdcdisc) writes `-F gdi`
(the release packaging runs mkdcdisc v0.0.4 itself, through `tools/d367/mkgdi.sh`):

| Track | Start (LBA) | What it holds |
| --- | --- | --- |
| `track01.bin` | 0 | data, low-density area: 450 sectors, a small ISO9660 volume (COPYRIGH.TXT, ABSTRACT.TXT, BIBLIOGR.TXT) with the IP.BIN header in all 16 system sectors (IP0000.BIN) |
| `track02.raw` | 600 | audio: 526 sectors of silence (the "warning" track) |
| `track03.bin` | 45000 | data, high-density area: IP.BIN (header, TOC1, SEGA licence code, bootstrap), then the game's ISO9660 tree (Rock Ridge names); padded to LBA 549150, the end of a real GD-ROM; the files sit at the outer end of the disc and `1ST_READ.BIN` is the last file, 150 sectors before the end |

`disc.gdi` is four CRLF lines (`3`, then `number LBA type 2352 file 0` per track). GDEMU, MODE, USB-GDROM,
DreamShell and Flycast all read this form. Put the four files in their own numbered folder on the SD card; don't
rename them, and don't mix track files of two tests in one folder. `track03.bin` is about 1.2 GB (the padding is
zeros, so the zip is not much bigger than before). If your card manager offers **Shrink GDI**, leave it off: an
unshrunk image is what we test.

**How the game reads it (test 16 and later).** The game keeps the drive's fast streaming reads (KallistiOS
`cdrom_stream_*`, as in tests 14 and 15) and checks that every read really arrived. The first time a stream or sector read
fails, times out or comes back without its data, the game switches to plain sector reads (one bounded "read N sectors"
command per request, the way most discs are read) for the rest of the session and never starts a stream again; the
read that failed is redone the plain way. Make knobs, all in the release recipe's disc set
(`tools/d367/test15/t15-build.sh`, `T14_DISC`):

| Knob | What it does |
| --- | --- |
| `DISC_COMPAT=1` | the KallistiOS disc fixes (`KOS_DISC_FIX=1`), the Shrink-GDI mount, an on-screen disc log only when a read misbehaves |
| `DISC_READ_FALLBACK=3` | stream reads, each checked; the first failure switches the session to plain reads (`=2`: a bounded DMA command, then DMA after a bounded drive re-init, then PIO). `=0` is test 14's stream reads, `=2` plain reads from the start |
| `DISC_LAND_SPIN_MS=20` | plain reads only: wait for a read's DMA by yielding instead of sleeping a whole 10 ms scheduler tick, with a bound that grows with the read's size |

Test only: `DISC_FAIL_TEST=2 DISC_FAIL_AFTER_S=20` makes stream reads fail after 20 s of play, to see the switch.
Plain reads from the start can also use `STORAGE_BOUNCE_ALIGNED=1` and `TEX_PACK_WINDOW=128` (with `tex.pak` reordered
by `tools/d367/texpak_order.py`, data set `texord16`); they are not in the recipe.

**How it is checked.** Every release image goes through these checks before it is published (the release packaging
script, `tools/d367/test16/t16-package.sh`, refuses to package an image that fails the first one):

1. `python3 port/dreamcast/tools/d367/disc_lint.py <gdemu>/disc.gdi`, both profiles, 0 violations: `standard`
   (the default) checks the track count, types and LBAs; whole sectors; sync, MSF header, EDC and ECC of a sector
   sample; every IP.BIN field (hardware and maker ID, GD-ROM device info, area symbols and the matching region text,
   peripherals, version, date, boot file, the unmodified SEGA licence code, the TOC1 table); the ISO9660 volume
   (absolute extents, path table, names KOS can look up, no overlapping files, the boot file present and last);
   padding to LBA 549150; the low-density headers. `--profile loader` keeps only the rules a loader needs.
   `--compare a.gdi b.gdi` prints two images side by side. It exits non-zero on any violation.
2. The program and the game files on the disc are the release build's, byte for byte (`tools/d367/fullplay/fp_iso.py
   manifest` of track 3; the packaging compares `1ST_READ.BIN` with the build's program image).
3. The GDEMU disc-timing gate in the console-like Flycast (`tools/d367/fullplay/gdemu_gate.sh`, see
   `docs/tools/flycast-console.md`) on the release disc with the warp twin swapped in, under both disc profiles,
   10 seeds each, r101 plus the r103 door load: `RE4DC_GD_PROFILE=gdemu` (a GDEMU that answers before its data has
   landed) and `RE4DC_GD_PROFILE=weak` (a weak or clone unit: about 600 KiB/s, like `read_limit = 600` in
   GDEMU.ini, and several milliseconds per command). Pass = no stop and no bad read in any run.
4. The contributor kit (`tools/d367/kit-check.sh`): a clean checkout builds the release program byte for byte,
   `swap-program.py` puts it and the warp twin on the release disc, both swapped discs pass `disc_lint.py` (both
   profiles) and boot in Flycast (`tools/d367/kit-boot.sh`).

Two images of the same files can differ in the Rock Ridge inode numbers of their directory records (mkdcdisc numbers
them in the order the build machine created the files); the file placement does not (`mkgdi.sh` gives mkdcdisc a sort
file in path order). Compare images by their files, not by track hashes. Internal benchmark and harness discs may
still use the old layout with `LAYOUT=legacy mkgdi.sh ...`; a test release never does. `swap-program.py` still
accepts an old-layout disc from an earlier release (it appends a longer file after the end of track 3, as before).

To build mkdcdisc for the packaging: `tools/d367/setup-mkdcdisc.sh` (the pinned commit; needs `meson`,
`ninja-build`, `pkg-config`, `libisofs-dev`). Contributors don't need it.

**Compatibility reports.** Please add a row when you play a test build on a loader we have not listed:

| Loader | Firmware / version | Menu (openMenu, GDMenu, none) | Image (test, folder name) | Console (region, model) | SD card | Result | Report |
| --- | --- | --- | --- | --- | --- | --- | --- |
| GDEMU (genuine or clone) | e.g. 5.20.3, `read_limit` | | | | | boots / plays to ... / stops at ... | #issue |
| MODE | | | | | | | |
| USB-GDROM | | | | | | | |
| DreamShell (IDE / SD) | | | | | | | |
| Flycast | version | n/a | | n/a | n/a | | |

## Release checklist (maintainers)

On every test release, in the same landing as the release recipe, before the release publishes:

1. Refresh the knob file from the release's play build:
   `python3 port/dreamcast/tools/d367/release-knobs.py write <out-<label>>/candidate.txt
   port/dreamcast/tools/d367/<test>/release-knobs.txt --test N --tag <tag> --source <sha> --recipe <t-build.sh>
   --image-sha256 <sha256 of sh-elf-objcopy -R .stack -O binary> --assets-zip <name>`.
2. Point `RELEASE_KNOBS` in `build-public.sh` at it (one line), and update the release names in this page.
3. Make the Build-Assets zip from the recipe (`release-knobs.py zip <candidate.txt> <zip>`), not by hand.
   The package script (`tools/d367/<test>/t<N>-package.sh`) masters the standard GD-ROM image (section 8) and
   runs `disc_lint.py` on it, loader and standard profiles.
4. Run `RACE_FIXTURE=<door103 fixture> tools/d367/kit-check.sh <knob file> <out-<label>> <package dir>` (knob
   file = recipe, zip = recipe, these docs name no older release, a clean checkout of the release commit rebuilds
   the release program byte for byte, builds without assets, swaps onto the release disc, every swapped disc passes
   `disc_lint.py`), then `tools/d367/kit-boot.sh <WORK>` (the swapped discs boot to New Game and r101 in Flycast)
   and the GDEMU race gate on `<WORK>/disc-race` (section 8, check 3). A release does not publish until all pass.

## Questions

Open an issue. The build notes for maintainers are in `tools/d367/README.md`, and the port notes are
in `README.md` in this folder.
