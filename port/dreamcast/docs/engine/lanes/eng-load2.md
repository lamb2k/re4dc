# eng-load2 hand-back (2026-11-22): room loading through a door

**Status: finished, unaudited.** Branch `lane/eng-load2` (from lane/eng-mem2 4c9ef7e87, merged with origin/engine
78cf37442). Head: last line. Lane document: `port/dreamcast/docs/engine/lanes/eng-load2.md` (this text).

Tiers:
- Load times are **MODELLED (console-build dynarec at 70 MHz, calibrated on the old port)**, slot fly2, with the GDEMU
  disc timing profile (`RE4DC_GD_PROFILE=gdemu`, `RE4DC_GD_JITTER=20000`). Each run's `slot.txt` / settings line
  shows `Dynarec.Enabled yes`, `Sh4Clock 70`. The standard build reads the engine 3 to 10% kinder.
- Function results are **Flycast**: plain slots std1 and std2, plus fly2 for d3.
- Nothing here is a console number. The model cannot see real disc timing (seeks, the GDEMU card's own speed), bus
  contention, or the graphics chip.

## Lead
1. **The door now takes about the old port's time.**
   - Village to farm: engine **4.80 s**, old port **4.68 s**, same door, slot and settings.
   - Before this lane: **7.13 s**.
   - Farm to village: 5.17 -> **3.28 s**.
   - The 55 to 68 s of the brief was plain Flycast only. That build reads single sectors very slowly. On plain Flycast
     the door is now 3.16 s and 2.16 s (d5).
2. **What is left of the difference is not disc work.** Of the farm's 4.80 s:
   - **3.12 s** is `native_actor_open` (render/native_actor.inc, not this lane's file). It re-indexes and sorts every
     catalogue model's vertices at load.
   - 0.35 s is `native_world_runtime`.
   - Reading the pack and putting its textures in video memory take 0.90 s.
   - Baking the actor layout into the pack would bring the farm to about 1.7 s (estimate). Request 1.
3. **DOOR is OK.** The 16 B was allocator slack, not a kept block.
   - A debug build logged every tracked block (dbg1). The second village visit holds the same 315 blocks, with the
     same sizes and callers, as the first.
   - mallinfo's uordblks still reads 16 B more. A 256,212 B calloc landed with 16 B of slack, and small blocks landed
     in reused chunks.
   - The round trip is now judged on **kos-net**: uordblks less the tracked blocks' slack. It reads 5,736,836 on both
     visits.
   - The check is no looser. It still counts every byte and header, KOS's own blocks included. CDOORLK still fails
     with "LEAK kos-net" (+4,100). A ledger that lost blocks fails the check.
   - **This changes what the check measures: it needs the integrator's ruling.**
4. **Stream-end hang.** The game images already make fs_iso9660's 32-byte request blocking, through core/disc_safe.c
   as eng-load1 lifted it. This lane proved it with a control:
   - DOORSE (the farm pack ending at 2,020 mod 2,048) loads.
   - Its control CDOORSE passes the request on non-blocking, as KOS does. It stops at the farm load: TIMEOUT after
     300 s, no load done (d4b, plain std2).

## Door times (MODELLED, fly2 70 MHz dynarec, GDEMU profile; matched pair d1b / d2 run back to back)

| Arm | Village > farm | Farm > village | Opens / reads / drive requests (farm load) |
|---|---:|---:|---|
| Old port, Test 27.2 recipe warp twin (run old-door-f70g) | **4.676 s** | not run | 807 reads, 6,779 KB |
| Engine before (375c9691b, d1 and its re-run d1b, identical) | 7.130 s | 5.166 s | 10 / 667 / 3,992 |
| Ring reader, version 4 packs (DOORV4, d2) | 5.526 s | 3.865 s | 12 / 408 / 376 |
| **Ring reader, version 5 packs (DOOR, d2)** | **4.800 s** | **3.276 s** | 9 / 202 / 210 |

Old port build:
- oldD: origin/t15/int a5aca9cf9, the release recipe (rr/recipe.conf CH2 and t15-build.sh T15REC), plus `DBG_WARP=1
  PC_SAMPLER=0 PACE_HOLD_LOG=2 GAME_TICK_LOG=1 PHASE_METER=1 DISC_READ_METER=1`.
- Fixture: door103 (all31's), the r101 post-bell door.
- Its figure is the meter's `DISCRD: room=103 load_ms`: from the room's entry to its first picture. It covers neither
  the door fade nor the leave. The engine's figure runs from the request to play resuming, the leave included (15 ms).
- Measured, never tuned.

The farm load's phases (DOOR, d2): leave 0.015 s; room set-up 0.15 s; pack open 4.48 s, made of:

| Phase | Time |
|---|---:|
| header | 0.4 ms |
| textures (2.77 MB, CRC and upload) | 0.411 s |
| resident (3.48 MB with CRC) | 0.493 s |
| world | 0.027 s |
| world runtime | 0.353 s |
| models | 0.029 s |
| frame 0 | 0.005 s |
| bind and actors | **3.122 s** |
| visibility | 0.039 s |

After the pack, the memory map sample takes 0.106 s.

Where the time went before (d1): the reads followed the pack's sections. Those are multiples of 4 bytes, so most reads
started off a 32-byte boundary and went through the ISO cache one sector at a time (3,992 drive requests). Textures
took 0.98 s and the resident part 2.25 s.

## Per item
1. **Baseline.** Done: above (runs old-door-f70g, d1-fly2g, d1b-fly2g).
2. **The 16 B.** Done (Lead 3).
   - Block log: debug branch dbg-load2, local only, not pushed (run dbg1-fly2). Snapshots 0 to 3 of every tracked
     block, kept in memory and printed after play: 744 lines, none lost.
   - The two blocks added during the first visit are KOS `vblank_handler_add` nodes (2 x 20 B). They are made once
     and are already in mark 0.
   - Results: DOOR OK on d2, d3, d4b and d5. CDOORLK FAILED "round trip LEAK kos-net" on d3 and d5.
3. **Stream end.** Done (Lead 4). Scenes DOORSE and CDOORSE; boot file DISCNB; `bake/engine_pack.py --stream-end`.
   CDISCF stays OK on the new read path: latched 1, read again (d4b).
4. **Shorter loads, exact first.** Done.
   - **Version 5 packs** (`bake/engine_pack.py`): after the unchanged texture section, the resident part exactly as the
     frame-0 load built it in memory. That is frame 0's rows, and the camera row's pad that keeps the models' offset
     mod 32.
   - The loader reads it straight, in one pass. A version 5 pack is sized from the load's own header, so one open.
   - **The check is the same**: CRC-32 over every byte after the 20-byte header, checked at the end of the read.
   - Byte equality with the frame-0 path, lab file RESCRC (d4b): village abe5e86b and abe5e86b, farm 7d602c15 and
     7d602c15, from the version 4 and version 5 packs.
   - **Ring reader** (render/native_scene.inc): every pack read is a 32 KiB request at a 32 KiB file offset into one
     aligned buffer, handed out by copies. fs_iso9660 streams the whole file by DMA.
   - The frame-0 path's skipped rows pass through it in place. The 16 KiB scratch is gone, so the image grows by
     16 KiB net.
   - Textures stay resident for the room. No disc access in play: CDOORRD still fails.
   - The bench keeps the whole packs (BENCH, BOSSB) and refuses a version 5 pack (code path; no control run).
5. **Clean disc d5** (head 5e3a80386, plain std1):
   - LEON, HILL, FIGHT, BOSS, DOOR and DOORV4 are OK.
   - CDOORLK FAILED (LEAK kos-net). CDOORRD FAILED (disc in play 0 / 1 / 1).
   - CDOORPK FAILED "missing /cd/st1/r103.arc" on d3.
   - Four images link (ev\link-head.txt): default 0, FIGHT=1 10, BOSS=1 0, SENDABLE=1 0 SERVICE functions.
     FIGHT's 10 is origin/engine's own count after eng-e2f (30 -> 10); this lane adds no original unit.
   - PC suites: see "Suites" below.

## Pack sizes (on disc; resident in memory is the same as before, the kept layout)
| Pack | Version 4 on disc | Version 5 on disc | Resident |
|---|---:|---:|---:|
| village CROSS.PAK | 8,988,784 | 4,914,096 | 2,584,232 |
| farm R103.PAK (eng-mem1's, weapon models) | 11,314,244 | 6,247,556 | 3,476,176 |
| hill hill2-wep.pak | 7,782,672 | 3,645,232 | 2,036,460 |
| fight fight-wep.pak | 4,914,076 | 4,914,108 | 2,584,244 |

- Each version 5 pack is converted by the disc script at staging. Its receipt line goes in MANIFEST.txt: input,
  script and output sha256.
- No new shared pack set is needed. If the integration lane wants one, `bake/engine_pack.py <pack> <out> --receipt
  <file>` writes it.
- Memory, d5 margins: KOS heap to the arena after play LEON 4,759,552, HILL 4,911,104, FIGHT 278,528 (was 290,816),
  BOSS 1,978,368. The image is 16 KiB larger (the stream buffer). MEMORY_MAP.md rows updated.

## Checks and their controls (all in the repository)
| Check | Where | Control and how it failed |
|---|---|---|
| DOOR round trip on kos-net, ledger complete | core/room_change.cpp, core/memmap.cpp e1_mm_ledger | CDOORLK: LEAK kos-net 5,736,836 / 5,740,936 (d5) |
| Stream end loads | DOORSE (build_console_disc.sh) | CDOORSE (DISCNB): TIMEOUT 300 s, loads 0 (d4b, std2) |
| Version 5 = frame-0 path, byte for byte | lab file RESCRC (native_scene.inc) | farm --stream-end pack: 3,477,040 B crc 5e89b6f4, against 7d602c15 (d4b) |
| engine_pack input checks | bake/engine_pack.py | version 5 input, one flipped bit, 299-row frame table: each refused, rc 1 (ev\engine_pack_controls.txt) |
| Pack CRC (unchanged) | native_open | eng-mem1's controls |
| No disc in play | unchanged | CDOORRD: opens 0 reads 1 sectors 1 (d5) |
| Read safety on the ring reader | unchanged disc_safe.c | CDISCF OK: not-landed 1, latched 1 (d4b) |

## Old port pieces considered (H-032, H-035, H-036)
| Piece | Verdict | Why |
|---|---|---|
| DISC_READ_FALLBACK=3's blocking 32-byte stream request (dvd_read_safe.cpp, release knob) | **Taken, already in** | eng-load1 lifted it in core/disc_safe.c. Kept as lifted (console-proven) and not rewritten: this lane added a comment, the DISCNB control and the DOORSE/CDOORSE scenes |
| DISC_READ_VERIFY's GD-DMA settle wait and held-off stale abort | Left | Not in the 27.2 release's knobs. A console-only question for the deferred run |
| DISC_READ_METER | Used to measure the old port only | Measuring stick |
| The GameCube read queue (dvd.cpp) and archive-at-a-time loading (read.cpp) | Left (H-035) | Would bend the engine's loader. The engine reads its own pack format, resident and read in place |
| Its read pattern: long sequential reads, one pass per file | **Taken as an idea** | Written the engine's way: the ring reader |
| Its overlap of reads with work (the game thread blocked only 167 ms of the 4,676 ms) | Idea, not taken | Would need a loader thread. The engine's remaining cost is CPU conversion (actors), not reads |

Convenient but costly things of the engine's own, removed:
- reading and checking the 299 unused frames (version 5);
- single-sector reads (the ring);
- two extra opens and their seeks per load (version 5 sizes from its own header).

## Files touched outside the owned list
- `engine/core/memmap.cpp`: `e1_mm_ledger` (15 lines). The round trip's ledger needs the tracked blocks.
- `engine/hostref/svc/svc_dump.cpp`: merge resolution only (eng-skel1's skent hooks and eng-e2f's e2f hooks both kept).

## Stubs and original units
None added. The DOOR scene's planted door request (eng-load1's logged stub, R1) stays.

## Requests
1. **Renderer owner:** move `native_actor_open`'s per-model work into the bake, into the version 5 pack. That work is
   the corner re-indexing, the sort by weight set, the spheres, and the per-part maps. It costs 3.12 s for the farm and
   1.59 s for the village (MODELLED). Move `native_world_runtime` too (0.35 s and 0.50 s). Then a door is about 1.7 s
   (estimate).
2. **Integrator ruling:** the round trip judges kos-net, not uordblks (Lead 3).
3. **Integration lane:** the disc script now stages version 5 packs for the engine images. The bench scenes keep
   version 4.

## Not done / not verified
- A second round trip.
- The old port's farm-to-village door.
- The bench's refusal of a version 5 pack: no control run.
- A faster CRC: it is part of the 0.90 s, not split out.
- The weak-GDEMU profile.
- No console.

## Suites
PC suites at the merged head 5e3a80386 (ev\suites-a\): every row ended as it must, none turned WRONG:
- svc_controls, camcheck, refctl;
- controls (18 rows), outcome_controls (35 rows);
- aim_check, e2check, e2bcheck, e2c_check, skent_check, colmap_check, speed_controls;
- door_check PASS, with its controls early20 and at0 FAILing; two reference runs identical.

The PC reference does not link the files this lane changed. The serial-log suites (shot_engine, hill_engine,
camengine) were not re-run: this lane changed no traced scene's play.

Evidence: `E:\RE4DC-Lanes\eng-load2\runs\` (old-door-f70g, d1-fly2g, d1b-fly2g, dbg1-fly2, d2-fly2g, d3-fly2,
d4b-std2, d5-std1), `ev\`, STATUS.md, DELETED.txt (every test disc deleted after its runs).
