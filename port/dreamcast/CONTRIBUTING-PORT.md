# Contributing to the Dreamcast port

**From a fresh clone on Linux (or WSL) to your own build of the game, in Flycast or on a Dreamcast with GDEMU.**
You build only the program. The game data comes from a published test release, so you never need the original discs.

**Build your own program, in short:**

1. Install the host packages (below).
2. Clone with `--recurse-submodules`.
3. Run `bash port/dreamcast/contrib.sh`.
4. Open the printed `disc.gdi` in Flycast, or copy its four files to a GDEMU SD card folder.
5. Put your change behind a default-off knob and open a pull request (section 6).

## Quick start: one command

On Ubuntu 24.04 (or WSL) install the host packages once:

    sudo apt install build-essential bison flex texinfo libgmp-dev libmpfr-dev libmpc-dev \
        libelf-dev libjpeg-dev libpng-dev git curl python3 genisoimage

Clone with the submodules (SH4ZAM is one, see section 1):

    git clone --recurse-submodules https://github.com/lamb2k/re4dc.git

(in a clone made without it: `git submodule update --init`). Then, from the repository root:

    bash port/dreamcast/contrib.sh

What it does:

* **Toolchain:** builds it the first time (about 11 minutes, into `~/re4dc-toolchain`).
* **Downloads:** the newest test release and its Build-Assets zip, checked against the release's `SHA256SUMS.txt`.
* **Build and swap:** builds the program, puts it on the release disc and prints the path of `disc.gdi`
  (under `port/dreamcast/out-contrib/disc`).

Options:

* `--release <tag>` picks a release by its tag (`test-<source commit>-<date>`, as on the releases page).
  An older release needs the `build-public.sh` of its own source commit (see "Which recipe" below).
* `--toolchain <dir>` uses or builds the toolchain there; a toolchain already in the environment
  (`RE4DC_KOS_BASE`) is used as is.
* `KNOB=value` arguments go to the build, for example `bash port/dreamcast/contrib.sh MY_FEATURE=1`.

**The Build-Assets zip:**

* **Character data** the release program was built with: `ps2leon/`, `ps2ganado/`, and `glod/ganado_lod.re4gl`
  (the lighter villager meshes named by `GANADO_LOD_PACK`). Your program draws the same characters as the release.
* **Chapter 2 enemy rows:** `ps2enemych2/`, the PS2 enemy rows of chapters 2-2 and 2-3
  (`PS2_ENEMY_CH22_DIR` / `PS2_ENEMY_CH23_DIR`, compiled into the program), so your program places the same enemies.
  Also `ps2stump/`, the layout header of the PS2 lost-head stump and hand-pose package (`ACTOR_GANADO_PS2_STUMP_DIR`).
* **Leon after his head comes off:** `ps2leonhead/`, the PS2 neck header (`LEON_HEADLESS_DIR`).
  The head archives `em/pl00.drs` and `em/pl08.drs` are disc data (set `garr18h`).
* **Newer disc data files,** under `re4dc-assets/disc/<disc path>`: the knob file's disc sets (its `disc-sets` line),
  among them the chapter 2 rooms, the far shells, `dc/resident.bin` and `dc/tex.pak`. `dc/tex.pak`
  holds every texture, so the disc and the zip carry no loose `dc/tex/<c>/` textures. They are on the release disc
  already; you need them only for a disc of your own.
* **Byte for byte:** built from the release's source commit with its zip, the program is the release's program.
  The maintainers check this before every release.
* Downloads are kept, so a second run only rebuilds.

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
`tools/d367/test23/release-knobs.txt` (test 23: the previous release recipe plus `WATER_PS2_EXT=1` (PS2 river and pool water), `TRAP_FX=1` (trap explosions), `EM35_ROUTINE_BYTES=1` (the Mendez freeze), `LIGHT_CUT_HOLD=1 FX_ROOM_SPILL_KB=24` (steady barn light, effects in busy rooms), `DISC_DMA_WAIT_TIMEOUT=1` (#28: a disc read that never finishes times out), `FX_LEVEL=3 FX_TRIM=1` (Essential effects: mist, glows and dust cut), `PS2_WORLD_SOURCE_TEX_MIP=1 PS2_WORLD_ROOT_POSE=1` (r200 mips, the r11c gears), `SCENERY_SELECT_ONLY=1 SCENERY_REPLAY_LEAN=1 SCENERY_SUBMIT_BATCH=1` (scenery draw setup), `STAT_ROUTINE_BYTES=1`, the safety fixes `ESP_POOL_RECYCLE=1 R117_EFFECT_FAILURE_SAFE=1 KOS_CACHE_P2=1 R10C_SPAWN_LIVE_GUARD=1 EM_READ_RETRY=1`, `VRAM_ROOM_ARENA=1` and `FOLIAGE_MIP24=1` (mip chains for bushes and cut-outs, data set `fol24`). The release before added the texture pipeline below with `VRAM_ROOM_ARENA=0`, `GANADO_EVENT_KEEP_LOD=1` (Ganados keep their models through in-engine events), `SS_DATA_LZ=1` (packed inventory data, data set `sslz23`), `FX_STRIP21=1` (trail and ribbon effects), `MOTION_CAPACITY=1`, `PS2_WORLD_NONEMPTY_LOD=1`, the fixes `RESET_MEM_FIX=1` (#26), `GANADO_ROUTINE_BYTES=1` (death stall), `PAUSE_NATIVE_PRESENTATION=1` (#48/#49), `CLOTH_LIGHT_ABI_FIX=1`, `AICA_LAYOUT_RECOVER=1`, the load guards (`EVD_*`, `EFFECT_ADMISSION_GUARD`, `EFFECT_CONTROLLER_VALIDATE_FIRST`, `EM_ADMISSION_DISP_FIX`, `EVENT_MANAGER_STORAGE_FLAGS`, `MOTION_RETIRE_PREFLIGHT`, `PARTS_LINKED_FLAG`, `RESET_RETIRE_BEFORE_HEAPS`, `SS_*`, `TEX_PAYLOAD_RETRY`), and the data sets `lake22` (lake island tree bark) and `sslz23`; `CPU_BACKFACE=0 ACTOR_BACKFACE=0` (slower on a console). Earlier releases added `BODY_CORPSE=1 BODY_ROUTE=1` (dead bodies cost less), `RIGID_CHUNK=1 CHUNK_SUBMIT=1` (props drawn in chunks), `PACE_STEADY=1` (Options > Frame pacing > Steady; Fast stays the default) and `MOTION_PRESSURE_BACKING=1 MOTION_RESERVE_PACK=1` (fights stop reloading enemy animations), with the data sets `r111p` (r111 villagers on the PS2 model), `ch21l` (dam rooms with the PS2 lighting) and `ash21` (Ashley keeps her r11e pre-fight animations loaded). `QA_MENU` stays 0: the QA build for testers is `QA_MENU=1` on the warp build (game/qamenu.mk). Data set `nostd20` is release-disc only and not in the Build-Assets zip, since a kit build swaps only the program onto the release disc. The release before it added `ROUTE_CH21_FULL=1` (chapter 2-1's real path: the dam r10c, r10d and r10e, with the Insignia Key from the dam's own pickup; data set `ch21r`; it replaces `ROUTE_SOON_KEY`), the scenery speed knobs `SCENERY_UNIT_CONCAT=1 SCENERY_SCREEN_MEMO=1 SCENERY_FAR_LOD=4` and the enemy logic knobs `LOGIC_LOD_EM=2 LOGIC_APPROX_MASK=0x01 ESP_TYPE_CAP=16 ESP_CUT_EARLY=1`; `SCENERY_DEDUP` and `CHAR_CHUNK` are off (measured slower). The `T15_V` group of `tools/d367/test15/t15-build.sh` carries `VIEW_DIST_BOOT=1` and `FOLIAGE_TRIM=2` (every boot at view distance Near and foliage Off), `QUICK_WEAPON=1`, `ACTOR_PLAN=1`, `MANUAL_PACK_PROBE=1` (the Dreamcast manual pages), `SCENERY_CHUNK=1 SG_SELECT_LEAN=1` (scenery draw path) and `ENEMY_VIS_CULL=1` (the wall check, with the room files of data set `rc19`); see the knob notes below. Earlier releases added the chapter 2-2 / 2-3 knobs of `tools/d367/ch2/ch2-build.sh` and `ROUTE_SOON_RETURN=1`, `MOVIE_AUDIO_PRIME=1` (cutscene sound loaded before it starts), `ROOM_LEFTOVER_FIT=1 PS2_WORLD_SOURCE_TEX_VQ=1` (the r10f to r200 pictures), `LEON_SKIN_SLOTS=2` (r119), `LEON_HEADLESS=1` (Leon after his head comes off), `LEON_CLOTH_DRAWN=1` (jacket movement only when shown) and `FX_MIST_PS2=1 PS2_HDR_SETS=128` (the village and farm mist); the disc data sets are on its `disc-sets` line, with the lighter El Gigante `boss18g50` and the resident lists `res18f`; its header names the source commit). The maintainers write that file from
the release build itself, so it is the exact knob list of the published program. To build an older
release, check out that release's source commit: its `build-public.sh` points at its own knob file.

Without `ASSETS` the build uses `game/public-assets`, neutral stand ins that carry no game data, and
switches these release knobs off (`PRIVATE_OFF` in `build-public.sh`). The game plays the same (except the
chapter 2 enemies, below); it looks different from the release:

* `PS2_LEON=0 LEON_HAND_PACK=0`: Leon is the GameCube model (the release draws the PS2 Leon, also in
  every hand pose).
* `PS2_GANADO=0 PS2_GANADO_LIT=0`: the male villagers are the GameCube models (the release draws the
  PS2 models with the PS2 lighting).
* `GANADO_LOD=0`: no lighter villager meshes (they need the PS2 villagers and the zip's `glod/`).
* `ACTOR_PROBE_LIGHT=1 GANADO_LIT=0`: only Leon is lit by the room-light probe (the release lights the PS2 villagers
  with it too).
* `NATIVE_MODEL_REGISTRY_DYING=0`: a dying villager fades on the GameCube model (the release keeps the PS2 model
  through the fade, which needs the PS2 villagers).
* El Gigante, Del Lago, the female villagers, the animals, Ashley, the PS2 room objects and the PS2 room
  worlds (with the village's baked doors, windows and racks) come from the disc, so they draw as in the
  release.
* Leon and the villagers draw from the original GameCube models on the disc instead of the converted
  meshes. They cost more time to draw, so do not compare speed with the release.
* `PS2_CH2_ENEMY=0` (without the zip's `ps2enemych2/`): chapters 2-2 and 2-3 use the GameCube enemy
  lists and room code instead of the PS2 ones, so the enemies there differ from the release (this one changes
  gameplay in those chapters; chapter 1 is unchanged).
* `ACTOR_GANADO_PS2_STUMP=0` (without the zip's `ps2stump/`): a villager whose head is shot off, or
  who raises or points a hand, draws the GameCube model until the pose ends (looks only).
* `LEON_HEADLESS=0` (without the zip's `ps2leon/` or `ps2leonhead/`): after a chainsaw or claw kill Leon
  draws the GameCube model for the death scene (looks only).
* The memory card messages show the GameCube wording ("Memory Card in Slot A") instead of the VMU wording.

Either way, measure your change against your own build with the change switched off.

## 3. Put it on a release disc

    python3 port/dreamcast/tools/swap-program.py RE4DC-Console-Test-<commit>-<date>-GDEMU.zip \
        port/dreamcast/out-public mydisc

`mydisc` gets `disc.gdi` and its three tracks: the release disc with your program as the boot file and
your overlays in place. Everything else on the disc is unchanged. Use a release made from the same or a
close source revision; a program much newer than the release may need data files the release lacks.

The release disc is a standard GD-ROM image (section 8), and `swap-program.py` keeps it one
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

The release program starts with the speed display off. Hold R and press START to show it on screen: drawn
frames per second and game speed (the VMU shows the Leon, Ashley, Hunnigan and Luis pages instead of speed
numbers). Frame pacing is set in Options (Fast is the default). Hold X and press START to switch the look
preset. A build with `SPEED_VMU_OFF=0` puts the speed numbers back on the VMU.

The player options are the rows in Options (START), and the knobs behind them:

* **Frame pacing:** stored on the VMU.
* **Rendering:** Standard or FSAA, knob `RENDER_FSAA`. Not saved; every boot starts in Standard.
* **View distance:** Full, Near or Short, knob `VIEW_DIST_OPTION`. The world is drawn to 25, 18.75 or 12.5 m and the
  fog reaches full strength there. Drawing only; the game logic is unchanged. Not saved; every boot starts at the
  `VIEW_DIST_BOOT` level (0 Full, the knob default; the release recipe uses 1, Near).
  Two rules refine it (game/option_rows.cpp):
  * a per-room minimum far table, `kViewRoomMin`, keeps rooms that need their horizon at Full (the lakes r10b, r11a
    and r11b);
  * while the player stands in one of the room's indoor effect areas (the game's weather-off areas, `Status_flg[1]`
    0x02000000), the fog ramp starts behind that area. A house interior is not fogged, while the scenery seen through
    its doors and windows still fades out before the cut.
* **Foliage:** Full, Near or Off, knobs `FOLIAGE_TRIM` (the level word and the boot level, hwfog.mk) and
  `FOLIAGE_OPTION` (the row). The release recipe boots at Off (`FOLIAGE_TRIM=2`).
  * Near draws the translucent PS2 world parts whose texture is a near-binary cut-out (leaf / brush cards, fence gaps)
    in the punch-through list up to 12 m. The key table is platform/include/foliage_keys.inc, built from an alpha
    census of the chapter 1 packages.
  * Off leaves out every listed card key (classes 1-4, soft shadow / mist / grass cards included).
  * Surfaces without cut-out holes (walls, floors, water), unlisted keys and the vertex-alpha overlays always draw.
  * Not saved: every boot starts at the recipe's `FOLIAGE_TRIM` level (Off in the release).
  * `FOLIAGE_NEAR_FIX=1` (hwfog.mk, recipe group `T15_FN`; render only) makes Near's punch-through pass also visit
    placements that only have translucent parts, so their cut-out cards draw at Near (without it they were drawn in
    neither pass).

Control knob in the release recipe:

* **Quick weapon** (quickweapon.mk, recipe group `T15_V`): `QUICK_WEAPON=1`. Hold X and press the D-pad
  to equip a weapon by kind: up handguns, right shotguns, down grenades, left rifles, the TMP, then launchers. Pressing
  the same direction again picks the next weapon of that kind in the case.
  * The equip is the case's own: `cItemMgr::arm`, then the weapon reload of `SubScreenExit`. The game pauses for a few
    frames while the weapon's module reads from the disc.
  * A swap is ignored where the case could not open, and while shooting, reloading or carrying Ashley.
  * With X released the D-pad works as before (camera look, a tap down for the map). Nothing changes until the chord is
    pressed, so the logic trace stays STRICT.
  * `QUICK_WEAPON_POC_KIT=1` (a starting weapon kit) is for test discs only and never goes in a recipe.

Speed knobs in the release recipe (recipe group `T15_V`; each one exact or render only, so the logic trace stays
STRICT, except the approximations marked below):

* `ACTOR_PLAN=1` (actorplan.mk): character setup runs once per tick and is reused by every draw of that tick.
* `SCENERY_CHUNK=1 SG_SELECT_LEAN=1` (scenery19.mk): the PS2 world pass selects first, then emits; pixel identical.
* `CHAR_CHUNK` (chardraw19.mk) is off in the release: the new character draw path measured slower.
* `SCENERY_UNIT_CONCAT=1 SCENERY_SCREEN_MEMO=1` (scenery19.mk): the PS2 world pass skips repeated matrix products and
  reuses its last screen matrix when the inputs match (exact). `SCENERY_FAR_LOD=4` swaps far world pieces to their lower detail (an
  approximation; far detail only). `SCENERY_DEDUP` is off (measured slower).
* `LOGIC_LOD_EM=2 LOGIC_APPROX_MASK=0x01 ESP_TYPE_CAP=16 ESP_CUT_EARLY=1` (logiclod20.mk): cheaper logic for far
  enemies and effects (approximations, each its own switch; gated for the same kills, doors, waves and cutscenes).
* `ENEMY_VIS_CULL=1` (engine_preview.mk): the wall check. A villager fully hidden behind a wall is not drawn; logic,
  sound and collision are unchanged. It reads the room file `dc/native/<room>/room.r4rc` (R4RC grid + wall-check
  occluders, tools/enginebake/room_compile.py), staged by data set `rc19` (private store `rc19o2-20261019`, in the
  Build-Assets zip). A room without its file draws every villager, as before.
* `MANUAL_PACK_PROBE=1`: the Player's Manual finds the Dreamcast manual pages in `dc/tex.pak`.
* **Texture pipeline** (render only): `CAST_MIPMAP TEX_TWIDDLED_MIPMAP TEX_PAL4_ALPHA TEX_PAL4_MIPMAP TEX_PAL8_ALPHA
  TEX_PAL8_MIPMAP WORLD_RECT21` (mip chains, rectangle textures, scoped world texture keys; the key tables are in the
  source, `tools/d367/texture_rect21/`), `TEX_MIP_DADJ=3` (mip D adjust 0.75). `VRAM_ROOM_ARENA=1` (core textures
  from the top of texture memory, room textures from the bottom; on from Test 23) and `FOLIAGE_MIP24=1`
  (Test 23: coverage-preserving mip chains for 169 foliage and cut-out pictures, data set `fol24` after `mip22b`). They read
  disc data sets `mip22`, `mip22b` (r11c palette fix) and `res22c` (resident lists with the HUD digits and muzzle flash) (mip22 private store `mip22-20261022`: `dc/tex.pak` with the mip chains, the 27 rekeyed worlds'
  `ps2-world.r4pw`, `dc/resident.bin`). It is on the release disc; a program built with these knobs needs that disc data,
  and a knob-off program must not read it (mip22 is not in the knob-off disc sets).

Render knobs in the release recipe:

* **Lake far** (post30.mk, recipe group `T15_LF`; render only): `LAKE_FAR=<mm>` draws r10b (the Del Lago boat) and
  `LAKE_FAR_SHORE=<mm>` (default `LAKE_FAR`) draws r11a / r11b (the shore, day and night) to that far instead of the
  25 m cap, for the PS2 world, the coarse view and the fog. The fog ramp still takes the last 20 %. 0 keeps 25 m;
  values must be above 25000 and need `FOG_FAR_CAP=0`. The release uses 45000 / 45000.
* **Transparency policy** (hwfog.mk, recipe group `T15_TR`; render only): `TRANS_POLICY=<mask>` reads each room's class
  sidecar `dc/native/rXXX/ps2-world.r4tc` and the index `dc/native/trclass.idx` (disc data set trans17, written by
  `tools/d367/tr_classify.py`). 1 FLAT draws parts whose pictures are uniform 14/15 alpha or fully opaque as solid;
  2 CARD draws near-binary cut-out cards as punch-through. The release uses 3. A room missing from the index draws as before.
* **Night lake torches:** `LAKE_NIGHT_FX=1` (effects30.mk, group `T15_LN`) draws the night lake's torch flames. Their
  picture is in r11b's resident list (data set res17b, the resident file packed from every list).
* **Night lake rain:** `RAIN_DC=1 RAIN_DC_N=320` (effects30.mk, group `T15_RD`; render only, an approximation of the
  PS2's full-screen rain sheet) draws 320 short screen-space streaks with a view depth, one untextured strip each, from
  a private random generator (the game's own random numbers are untouched). It needs `RAIN_PS2=1`'s hook; with it on,
  the old faint `RAIN_PS2` lines stop. `RAIN_PS2_SHEET_REF` is a reference arm for comparisons, never in a recipe.
* **Haze cut:** `HAZE_SPRITE_CUT=1` (hwfog.mk, recipe group `T15_HZ`; render only) leaves out every haze / mist sprite
  at every Foliage setting: the camera haze around Leon (Esp15), the mist sheets (Esp48) and the r118 / r11c PS2 haze
  additions. The distant haze stays as the fog table (`HW_FOG_HAZE`, `EFFECT_HAZE_LEAN`), which is fed before the cut.
  Docs: docs/MIST_CUT.md.
* **Warp discs:** on a warp test disc (`DBG_WARP=1`) the warp line `viewdist 0|1|2` starts the run at Full, Near or Short.

In the release:

* **Far shell** (knob `FAR_SHELL`, needs `VIEW_DIST_OPTION`, recipe group `T15_FS`; game/platform/far_shell.inc).
  Built for r100 and r101 as `dc/native/rXXX/far-shell.fsh` (disc data set fsh). It is read at Short only (Full and
  Near never read it), lent to every route movie and read again after it, and freed when a heap-4 allocation fails.
  * In a room with a shell, Short cuts only the world's opaque pass. The fog, the cut-out and see-through world
    surfaces, characters and objects keep Full's distance.
  * The shell (a simplified copy of the far world, about 3,000 triangles textured with the world's own textures, so
    no extra graphics memory) is drawn beyond the cut, so landmarks stay visible.
  * Build a shell with tools/d367/farshell (README there; Windows Python and Blender 5.2) from the room's PS2 world
    package. Near, and rooms without a file, keep the plain cut.
  * Warp line `farshell 0|1|2` (0 = plain cut, 1 = shell, 2 = opaque cut without the shell, for pricing).

Radio call subtitles (knob `RADIO_SUB_RT`, game/subscreen.mk; src/Sscrn/ss_term.cpp):

* **The problem:** the GameCube steps a call's subtitle sequence once per 30 Hz sub screen frame, while the voice plays
  from the AICA in real time.
* **The fix:** each call frame runs the steps owed since the voice began to sound (KOS timer, platform/audio_aica.cpp
  `re4dc_aica_stream_started`), so the pages stay with the voice when a call frame takes longer than 1/30 s.
* **Logic unchanged:** the game is stopped under the sub screen.
* **Logging:** test builds can add `RADIO_SUB_LOG=1` for one log line per subtitle page (time since the voice started).

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

The maintainers then run these checks before a change goes into a test build. They use private
recordings and tools, so you do not need to run them, but your patch has to pass them:

* **Gameplay identity (STRICT).** Recorded sessions are replayed and the game logic is compared tick by
  tick. An exact change must leave the gameplay exactly as it was.
* **Approximations.** A change that is close but not exact (for example faster maths that rounds a little
  differently) is welcome. It stays behind its own default-off knob. A render-only
  approximation is judged by its look (a pair of stills). One that touches game logic must keep the same
  gameplay: the same kills, triggers, doors, waves, room clears and cutscenes, with no desync or stuck
  event. Each approximation is reported with its measured gain and its check results.
* **System memory (KOS squeeze).** The game is run in Flycast with 48 KiB of the console's system memory
  held back (`tools/d367/fullplay/kos_squeeze.sh`) through the village fight, a radio call and the door to
  r103; it must not run out. Real consoles have less free system memory than Flycast, so say how much your
  change adds to the program's static size.
* **Short runs.** Each emulator check is a scene of a minute or less, started right at the event (a warp,
  not a long walk). Long play happens once, on the final release candidate.

A change to collision, events, game state or AI that is not one of the approximations above will not be
accepted.

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
| same plus game run logs | texture package `dc/tex.pak`: every texture of the disc (no loose `dc/tex/` files), 16-bit pictures VQ by default | partly: `tools/d367/vram/disc_pack.py` packs a disc's loose textures (opaque 16-bit pictures of 16 KiB or more as VQ when PSNR >= 29 dB; UI, alpha and small pictures stay 16-bit), but the earlier VQ selections come from logs of test runs |
| none (the lists are in the repository, made from game run logs) | per-room resident texture lists `dc/resident.bin` (ROOM_RESIDENT) | yes (`tools/d367/vram/resident_keys.py pack` of `tools/d367/vram/resident/r*.tsv`) |
| PS2 Resident Evil 4, USA (SLUS 21134), `BIO4MOV.AFS` | cutscene movies `dc/movie/*.seq` | yes (`tools/convert_route_movies.py`, needs ffmpeg) |
| PS2 USA, `BIO4DAT.AFS` rooms (plus two JADERLINK unpack tools) | PS2 room worlds `dc/native/rXXX/ps2-world.*` | converters exist; the released set is a reviewed frozen output |
| PS2 USA characters | PS2 Leon and villager meshes (compiled into the program), registry packs, pl08 pack | no: needs Blender and review steps |
| none (made by hand or by tools) | title art, look presets, glyphs, character bakes, test scripts | no |

No PC version and no GameCube retail disc are used. The second GameCube debug disc is used only by
the decompilation build.

## 8. Disc image and compatibility

The release disc format since 2026-10-16 (decided that day; earlier tests shipped the old layout). Users had reported freezes and crashes on GDEMU
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

**How the game reads it.** The game keeps the drive's fast streaming reads (KallistiOS
`cdrom_stream_*`, as in tests 14 and 15) and checks that every read really arrived. The first time a stream or sector read
fails, times out or comes back without its data, the game switches to plain sector reads (one bounded "read N sectors"
command per request, the way most discs are read) for the rest of the session and never starts a stream again; the
read that failed is redone the plain way. Make knobs, all in the release recipe's disc set
(`tools/d367/test16/t16-build.sh`, group `T14_DISC`):

| Knob | What it does |
| --- | --- |
| `DISC_COMPAT=1` | the KallistiOS disc fixes (`KOS_DISC_FIX=1`), the Shrink-GDI mount, an on-screen disc log only when a read misbehaves |
| `DISC_READ_FALLBACK=3` | stream reads, each checked; the first failure switches the session to plain reads (`=2`: a bounded DMA command, then DMA after a bounded drive re-init, then PIO). `=0` is the earlier stream reads with no fallback, `=2` plain reads from the start |
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
   --image-sha256 <sha256 of sh-elf-objcopy -R .stack -O binary> --assets-zip <name> [--disc-sets <t11-fix.py sets>]`.
2. Point `RELEASE_KNOBS` in `build-public.sh` at it (one line), and update the release names in this page.
3. Make the Build-Assets zip from the recipe (`release-knobs.py zip <candidate.txt> <zip> --disc-sets <the knob
   file's disc-sets line>`, or the test's package script), not by hand.
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
