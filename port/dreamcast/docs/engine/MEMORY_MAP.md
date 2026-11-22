# Main memory map (lane eng-mem1, 2026-11-22; H-031)

One owner for main RAM (16 MiB, 0x8c000000-0x8d000000): `engine/host/e1_engine.h` (the fixed blocks),
`render/native_scene.inc` (the renderer's resident pack buffer, its sizing), `core/loader*` (the loader's allocations).
Every figure below is **Flycast** (plain build, slot std1/std2: a function run, no timing claim), read from the scene's
own serial lines (`E1 MEM image`, `E1 MEM after play`, `E1 ARENA heap 4`, `E1 SVCMEM region`, `E1 MEMBLK`) on the test
discs d4 and d6 (head 8d0fe36e0 / fa2b14aba; images built with SENDABLE=1 as every disc's are). Memory figures do not
depend on the tier; a console run must still confirm them (the console's KOS and disc driver allocate the same, but
nothing here was measured on one).

## The blocks, per image

| Block | Range (E1 / SENDABLE image) | FIGHT image | BOSS image | Sized by |
|---|---|---|---|---|
| KOS vectors, system area | 0x8c000000-0x8c010000 (64 KiB) | same | same | KOS |
| Image (code, data, bss) | 0x8c010000-0x8c275e30 (2,514,480 B; bss 1.79 MB) | -0x8c32e750 (3,270,480 B) | -0x8c2d2c70 (2,895,984 B) | the link |
| KOS heap (renderer pack, sound data, archives, loader) | _end-0x8cc80000 (10,526,152 B) | _end-0x8ce40000 (11,606,184 B) | _end-0x8cc80000 (10,146,696 B) | what is left |
| Behaviour arena (13-heap API; heap 4 the room heap with the room archive) | 0x8cc80000-0x8cf40000 (2,883,584 B) | 0x8ce40000-0x8cf40000 (1,048,576 B) | as E1 | `E1_ARENA_LO/HI` |
| Native services region (skeleton pool 256 KiB, boot carve, room carve) | 0x8cf40000-0x8cfc0000 (524,288 B) | same | same | `E1_SVC_LO/HI` |
| Unused, below the main stack | 0x8cfc0000-0x8cfd0000 (65,536 B) | same | same | - |
| Main thread stack | 0x8cfd0000-0x8cfe0000 (65,536 B) | same | same | `arch_stack_16m` |
| Console loop hand-off | 0x8cfe0000-0x8d000000 (131,072 B) | same | same | `loader/cl_handoff.h` |

Largest image bss objects (E1): the projected pool 262,144, the draw lists `selected` and `ordered` 196,608 each, the
trace buffer 196,608, the sound driver's `Snd_seq_work` 103,520, `e1_timing` 81,920; FIGHT adds `smd_obj` 251,904 and
`fx_sprites` 84,484.

## Measured peaks and margins after play (Flycast plain, d4; DOOR from d6)

| Scene (image, room) | KOS heap in use, peak | KOS margin to the arena ("free to arena") | Arena heap 4 peak | Arena margin | Services pool tables / carve | Stack high water | VRAM free |
|---|---:|---:|---:|---:|---|---:|---:|
| LEON (E1, r101) | 5,744,224 | **4,780,032** | 692,704 | 2,186,624 | 52,064 / 34,816 | 9,548 | 2,639,720 |
| HILL (E1, r11d) | 5,578,813 | **4,931,584** | 604,992 | 2,274,336 | 108,800 / 34,816 | 9,548 | 3,338,792 |
| FIGHT (FIGHT, r101) | 11,303,336 | **290,816** | 844,384 | 199,936 | 115,680 / 0 | 9,544 | 2,639,720 |
| BOSS (BOSS, r119, headless) | 8,142,942 | **1,986,560** | 464,576 | 2,414,752 | 111,200 / 34,816 | 9,396 | (no renderer) |
| DOOR (E1, r101 > r103 > r101) | see "DOOR" below | | 1,077,984 (the farm) | 1,801,344 | | | |

The arena margin is heap 4's span (arena size less heap 0's 4,256 B) less its peak. The services region's margin is
its size less the pool and the carve: 227,328 B (FIGHT 262,144 B). The worst margins are the fight's: 290,816 B of KOS
heap and 199,936 B of arena.

## What changed in this lane and why

1. **The renderer's resident pack keeps frame 0 of the old game's recording, not its 300 frames.** A game pack
   (NAT3) holds, besides the room content, the recording the bench plays: sections 4-12, nine delta tables with a row
   for each of 300 frames. The engine images apply frame 0 once at open and draw from their services afterwards, so the
   other 299 rows were 4.1 to 6.3 MB of main RAM read and never used. Resident part of each pack, whole -> kept
   (`tools/engine/pack_keep_check.py`, on the shared pack sets):

   | Pack | Whole | Kept |
   |---|---:|---:|
   | village CROSS.PAK (lkg-wep) | 6,658,951 | 2,584,263 |
   | farm FARM.PAK (lkg-wep) | 8,526,603 | 3,459,915 |
   | farm R103.PAK (eng-bake1 r103 + weapon models) | 8,542,895 | 3,476,207 |
   | hill hill2-wep.pak | 6,173,931 | 2,036,491 |
   | fight fight-wep.pak | 2,584,243 | 2,584,275 |
   | El Gigante boss3-full.pak (bench) | 7,814,907 | 1,523,227 |

   This answers the integration lane's question: **both farm figures were right.** 8,526,624 B (the reopen's request) is
   the farm pack's non-texture part with the recording; eng-bake1's 4,011 KiB is its census's "room content only", which
   leaves the recording out. The bench (engine/bench, not linking core/loader.cpp) keeps the whole recording.
2. **FIGHT's arena 1.25 MB -> 1 MB** (peak 844,384 B): the KOS heap ended play 28,672 B from the arena before (d2) and
   20,480 B into it with a 48 KiB larger image (d3).
3. **The services region stays 512 KiB** (eng-skel2: the collision baked into the room archive, on the room heap with
   it) and the E1 arena stays 2.75 MB above it; eng-snd1's request R1 (arena 512 / 256 KiB smaller for the sound
   driver's image and heap) is met by (1): the KOS heap has megabytes over in E1, HILL and BOSS.

## DOOR (village > farm > village)

Filled from d6: see `docs/engine/lanes/eng-mem1.md`.

## Checks

- `tools/engine/pack_keep_check.py <pack>...`: the kept layout against the whole pack (sections 1-3, 13, 14 identical
  at their offsets modulo 32; each kept table valid; frame 0's state of all nine tables word for word the whole
  pack's). Controls `--control pad`, `nopad`, `drop` FAIL on every pack.
- The scenes' own memory lines and the selector's after-play rule (`CDISC SUM <scene> after play: ... arena margin`:
  a negative margin fails the scene, as FIGHT did on d3).
- DOOR's round-trip rule (`E1 ROUNDTRIP ... : equal`) and its control CDOORLK (4 KiB kept across the leave: LEAK).

## What the figures do not cover

The console (its KOS build is the same; its disc driver's buffers are not measured); scenes other than the five; rooms
other than r101, r103, r11d, r119; enemies above the fight's four; the sound's disc streams (none requested by any
scene today); the boss image with a renderer (it is headless).
