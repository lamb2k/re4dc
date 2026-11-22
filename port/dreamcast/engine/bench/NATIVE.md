# M1 native bench

Build in the KOS environment with the private pack directory containing cross.pak and hayfork.pak.

```sh
. port/dreamcast/kos-env.sh
make -j6 -C port/dreamcast/engine/bench native OUT="$PWD/out" PRIVATE_PACK_DIR="$PRIVATE_PACK_DIR"
```

The NAT3 pack contains immutable geometry, material descriptors and 300 ticks of logic inputs. Its NWR3 section retains the whole room's indexed R4IM and group table. Cells own contiguous placement spans. Bounds, UV encoding, inverse binds, texture storage and source blend state are static. The private logic stream carries camera matrices, joint transforms, lights, effects, caster feet, widget state and message records. The loader verifies CRC, references, patch bounds and model streams. It uploads the resident textures before picture one. Both TA vertex buffers are enabled.

The packer takes the private disc directory, capture directory, hexadecimal room ID, output path and static actor table dump. Build actor_static_dump.cpp on the host with the two private generated header directories on the include path. Redirect its standard output to the static table file. The capture directory contains the contiguous LOG3 picture files, Leon's simulation inverse binds and the room's optional model identity catalogue. For the additional model assets native_extra.py follows the source ModelData, TPL and joint tables in the private relocated asset archive. It reads full-detail source streams. Private assets and generated packs stay outside Git.

```sh
python3 port/dreamcast/engine/bake/native_pack.py "$DISC/dc" "$CAPTURE" 101 "$PRIVATE_PACK_DIR/cross.pak" "$STATIC_TABLES"
# lane eng-e1i: native_pack.py ends with the HUD fix (bake/hud_fix.py, SERVICES.md 45) and refuses to write a pack
# without it; it reads "$DISC/dc/tex.pak" and the capture's resource-ram-*.raw
```

The sample-store observer in model_profile.py takes the path to hwmodel/hwsim.c and an output directory. Set M1_TIMING to the SH-4 ELF address of timing. The optional M1_PHASE_MASK selects function counters for setup/world, characters/volumes, punch-through, translucent/hair, effects, HUD or scene finish in bits zero through six. The simulator still executes the full trace. Subtract the store in timing column six from the store in column seven to obtain the absolute drawing interval in cycles. Divide by 200,000 for milliseconds. timing's row index is zero-based. The retail image alternates rooms and repeats the 300 inputs twice at each load.

## E0 additions (lane eng-e0)

- Build: `Makefile` builds the engine image with fast math (`-mfsca -mfsrra`), `-DNDEBUG`, link-time optimisation,
  `-Os` by default and `-O2` for `render.c` and `native_world.c`. `render/stage_sh4.S` holds the world stage loop and the
  actor strip emitter; `game/platform/avk_sh4.S` supplies the skinned position kernel.
- Load-time conversion (outside the picture): per-part actor streams sorted by weight set with per-bone bounding spheres;
  per-meshlet staged vertex ranges per strip group, TA colours, signed coordinate words.
- Baked visibility: `cc -O2 -I../render bake_vis.c ../render/native_world.c -lm -o bake_vis`, then
  `bake_vis cross.pak CROSS.VIS` (and `FARM.VIS`); put the tables beside the packs on the disc. `bake_vis ... --wrong 1`
  writes the control table (one route-visible cluster instance per cell marked hidden).
- Boot options (empty files in the disc root): `NOVIS` draws the full set (pixel check), `ARMA` stages world vertices in
  operand-cache RAM (survey arm a), `ARMB` uses three short loops over 32-vertex blocks (survey arm b), `DELAY5` adds the
  5 ms busy-wait control, `STILLS` hands every picture of the first 300 to the host, `FARM1` starts in the farm.
- `host_world.c`: host replay of the world selection over a pack (per-picture meshlet, vertex and corner counts).
- `model_profile.py` treats operand-cache RAM (0x7C000000-0x7FFFFFFF) as one-cycle RAM for arm (a); run the observer with
  `--oc-kb 8` for that arm.

## E0b additions (lane eng-e0b)

- Pack format 4 (NAT3 version 4): fifteen root sections, nine logic streams. Stream 9 (`state[8]`) carries each
  player/enemy/prop model's light inputs (17 words: light volume shape, parts, EnableMask, SelectMask, offset, size,
  material colour, TEV scale group, AddAmb, the game's own last light pick for the test, room status). Lights
  (`state[2]`) are 18 words: + array index, xF / Attribute / Priority / kind-enabled, spot A0, fade A1, parent.
  Effects (`state[3]`) are 38 words: + the GX blend (type, src, dst, op). The HUD head's fourth word is the stance
  (`PlGetWeaponNo()`, 0x10 = knife in hand). The capture switch writes them (`r3_inputs.inc`, `src/game/esp.cpp`).
- Room load streams the texture section into VRAM through the start of the resident buffer, one texture at a time;
  the buffer holds only the rest of the pack (CRC still over the whole file). No texture copy stays in main RAM.
- Actor lighting follows the source rule (`render/source_light.inc`): setModel2's selection, LightSetModel's
  per-type brightness, GX per-vertex diffuse, material colour x TEV scale. Hair (role 7) is drawn alpha-tested in
  the punch-through list; Leon's knife part only in the knife stance; HUD widgets with a mask use a texture baked
  from widget texture x mask alpha (`bake/dctex.py`), masked backdrops first, deepest level first.
- Baked visibility VIS2 (`bench/bake_vis.c`): whole reachable room, 2 m camera cells with a camera height band,
  actor columns (2 m) over every floor column, masks stored once (raw or run-length) and merged by intersection
  into a 256 KiB budget. Anything the table does not cover draws everything. `--control <vis> N` writes the
  wrong-entry control for a pack's route; `--survey` prints the domain and route coverage.
- `main.c` runs a schedule of 600-picture windows in one boot (`/cd/SCHEDULE.TXT`, default
  `c0 f0 ca c0 cb c0 fa f0 fb f0 c0dh`): rooms c/f, arms 0/a/b, `n` no visibility, `d` 5 ms delay, `h` hold
  picture 300 for 40 ms. Raw rows per picture in `m1_rows` (draw us, PVR wait us, presented fields, two counters,
  visibility state), summaries in `m1_windows`, printed as `WINDOW` / `ROW` lines on serial and on screen.
  Counter calibration at boot in `m1_calib` (`CALIB` lines). Memory map per room in `m1_mem` (`MEM`, `VRAM`,
  `MEMBLK` lines; `memmap.h`: malloc wrappers, stack paint and guard).
- Tests: `bench/test_part_clip.c` (near-plane part class; `-DM1_PART_LOOP_E0` is the failing control).

## Room bake, one command per room (lane eng-bake1)

- `python3 bake/room_bake.py <room>` (for example `10b`) bakes one room into `E:\RE4DC-Lanes\eng-bake1\packs` (`--out`),
  then its visibility (`bench/bake_vis.c`), its checks and its census (`bake/census_world.c`); `--chapter1` does every
  chapter 1 room and writes `census.json` and `census.md`; `--inputs` lists each room's inputs, present or missing.
- A room with a recording of the old game (`RECORDINGS` in `room_bake.py`: village, farm, hill) gets a **game pack**
  (`<room>.pak`) through `native_pack.build` / `hill_pack.build`, HUD fix included. The village's recording has no
  RAM snapshot of its own: `native_pack.py --ram` names the one the HUD fix reads.
- A room without one gets a **world pack** (`<room>.world.pak`), same NAT3 format: world, materials, textures, sky,
  the actor catalogue and its distance variants, all from offline data; its logic streams hold only the room's entry
  points as cameras (door destinations from the room archives, `tools/d367/stage_route.py`), which seed
  `bake_vis`. No lights, environment, HUD, props or effects: `hud_fix.py --verify` fails on it by design, so no pack
  writer or disc script accepts it. It is for the census and the visibility table, not for an image.
- A room the PS2 gives no sky (r102) gets an empty one (`native_world.sky_bytes`).
- Checks per room: the HUD verify (game packs pass, world packs fail); the reachable floor is seeded (control:
  `room_bake.py --control-seeds <room>`, every seed moved off the floor, must fail); for rooms with a recording, the
  world pack's table grown from the entry points alone must hold at least 95% of the recorded cameras in baked cells
  inside their bands; `census_world` opens the pack, the world and the table against each other (exit 2, 3, 4 when not).
  The seeds are the entry points plus the centre of every AEV area and ITA item of the room archive.
- `room_bake.py --controls` runs each check's failing input after `--chapter1` (seeds off the floor, the village pack
  against the farm's table, the village cameras against the lake's table, a world pack through the HUD verify, a
  tampered receipt) and writes `controls.json`; every row must read "failed as it must". The seed coverage check tests
  that cameras sit in baked cells, not which room baked them: the farm's and the hill's tables pass the village's
  cameras because those rooms share its world coordinates.
- Receipt: `BAKE_COMMIT=<commit> room_bake.py --receipt` writes `receipt.json` (per room the hashes of the room's
  converted data, its recording, the common inputs, the bake scripts as committed at the bake's commit, and the pack and
  table it wrote); `--check-receipt` re-hashes and exits 1 on any mismatch.
- Host tools are built into `/dev/shm/eng-bake1/bin`.
