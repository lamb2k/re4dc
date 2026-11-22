# Lane eng-crash1: the crash screen and the sampling profiler (2026-11-22)

Status: **finished, unaudited**. Brief: `E:\RE4DC-Lanes\eng-crash1\BRIEF.md` (plan 3.3 section 8, B4; SALVAGE_20261121.md
rows 44 and 45). Evidence: `E:\RE4DC-Lanes\eng-crash1\` (runs, ev, STATUS.md, HANDBACK.md). All numbers here are
**Flycast** (plain build, slots std1 / std2): function evidence, no speed claim.

## What was lifted, and from where
- `core/crash_screen.cpp` from the old port's `port/dreamcast/game/platform/crash_screen.cpp` (origin/t15/int, last
  changed in 503f38de1), release form (`CRASH_SCREEN=1 CRASH_TASK_DETAIL=1`): BIOS font copied into RAM at boot,
  put_text into the frame buffer on screen, the render wait, the KOS thread list, the saved-stack return-address scan,
  the newest log lines; the log ring is the old `fault.cpp` dbgio ring handler (every printed byte), put in front of
  the device in use (the console loop's tee, or the serial line).
- `core/pc_sampler.cpp` from the old port's `platform/pc_sampler.cpp` (c1a9f6dc4): TMU1, the refusal when TMU1 is in
  use, the underflow handler (ctx pc / pr), jittered period, late and latency counts, the record layout.
- Left out (old-port globals and hooks): the game task scheduler rows, re4dc_stage / ui frame, HALT and MISSING entry
  points, PVR latch, overlay / VRAM ring / heap event / issue-52 rows, RES_MODES, the 30 s hang watchdog thread (a
  wake every second inside the timed pictures; on the console disc a hang is the loader's deadline), crashtest.txt; in
  the sampler, the build knob, the fixed .bss ring, the render-profile stage, the per-frame marker and read_pcs.py's
  streaming header.

## What is new, and why
- Crash screen: the scene and tick row from the engine's record (image, scene, route room, `e1_tick`, loop stage, the
  console loop's arguments); the memory row (image end, sbrk, faulting sp, main stack used from memmap.cpp's paint;
  no allocator call); the faulting context's return-address row; the in-play log lines flushed before the log rows
  (`e1_log_flush`; they are held in RAM during the ticks); the serial copy of every row (`CRASHSCREEN ...`); the still
  request for the Flycast runner (`m1_state`, as STILLS does); after an 8 s hold the console loop's own crash handler
  is called (chained at install), so the selector marks the scene FAILED "CRASHED exc .. pc .." as before. Booted from
  its own disc the screen stays.
- Boot file `CRASHCTL` (control): "<addr|ill> <tick>"; a thread above the main thread's priority faults at that tick
  of play (a misaligned read of 8c0abcd1, or the illegal instruction fffd); the armed line names the planted pc.
- Sampler: a helper thread starts TMU1 at the first tick of play and stops it after the last (no main-loop code); the
  image ranks the kept samples after play (`E1 PCS top ...`) and prints the timer check line. Boot file `PCSAMPLE`
  (lab arm, never in a timing scene): "[hz N] [spin]"; the ring (32 KiB) is allocated at load only with the file.
  "spin" is the control: 10 ms of every 33 ms of play in `e1_pcs_spin`.
- `core/main.cpp`: four lines (two includes, `e1_crash_boot()` and `e1_pcs_boot()` once after `e1_lab_boot()`).
- `tools/engine/build_console_disc.sh`: CRASH_CONTROLS (CRASHLA, CRASHLI, CRASHFA, CRASHFI, CRASHBA, CRASHBI, PCSLEON,
  PCSSPIN), staged only when `--scenes` names them.
- `tools/engine/crashcheck.py` (the crash screen's check, with its controls `--control flipaddr|flippc|fliptick|noscreen`)
  and `tools/engine/pcs_table.py` (the sample table on the ELF's symbols; `--expect-top`).
- `loader/selector.c` not changed: a crashed scene was already FAILED with its event and pc (selector.c:517).

## Results (Flycast plain; disc A2 = lane head 635092c05 after merging origin/engine 78cf37442; BASE2 = 78cf37442)
- CRASHLI, CRASHFI, CRASHBI (illegal instruction at tick 200 in the default, FIGHT and BOSS images): the screen shows,
  its serial copy names event 180, the planted pc, the image, room and tick 200; the selector marks each FAILED
  "CRASHED exc 180 pc <planted>". crashcheck.py PASS; LEON, FIGHT, HILL, BOSS beside them OK.
  Stills: `runs\A2\pic-8c1149e4-s0-4999.png` (default), `pic-8c1c0d98-s0-4999.png` (FIGHT), `pic-8c16d2b8-s0-4999.png`
  (BOSS, headless image).
- Address fault (CRASHLA, CRASHFA, CRASHBA): **not verifiable on Flycast**. Flycast does not raise a data address
  error on a misaligned read (as the old file noted); the image prints "the planted fault did not stop the program",
  the scene runs on, and crashcheck.py FAILs it (as it must). The address-fault path (event 0e0, TEA as the address)
  is the deferred console run's question.
- Controls of crashcheck.py on run A2: flippc FAIL (pc 8c03a510 against 8c03a518), fliptick FAIL (tick 201 against
  200), noscreen FAIL (no crash screen); CRASHLA (no fault on Flycast) FAIL. flipaddr has nothing to change on an
  illegal-instruction screen (addr is not compared there): its control needs the console's address-fault screen.
- Cost with nothing faulting, LEON rows 41-640, same session, same slot kind: base mean / p99 / max tick 3087 / 3920 /
  5275 us, draw 12645 / 15022 / 15126 us; lane 3087 / 3922 / 5275, draw 12644 / 15020 / 15124 (Flycast, function
  evidence). Selector sums identical to the hundredth of a ms in LEON, FIGHT, HILL and BOSS. By reading: the handlers
  and the ring are installed once in `e1_crash_boot`; the only code after boot is the ring's copy of printed bytes
  (nothing is printed inside the timed pictures).
- Sampler (disc B, lane 56fd85980, before the merge; PCSLEON): 4293 samples at 200 Hz over play, 4096 kept, 0 late,
  latency mean 36 max 396 x 80 ns; top function `e1_pace_end` 47.5% (the pacer's field wait), then walk_strips 4.2%,
  light_normals_once 4.0%, m1_emit_actor_strip 3.1%, re4dc_avk_pos_skin_u16 2.4% (`ev\pcs-leon.txt`). PCSSPIN:
  e1_pcs_spin 30.0% on top (10/33 expected); pcs_table.py `--expect-top e1_pcs_spin` PASS there and FAIL on PCSLEON
  (its control). Timer check: TMU1 stopped after play, TMU2 reload 12468721 counts (engine clock 12468720: same); E1
  FIELDS in both PCS scenes 600 intervals, none over 2 fields: no collision with the engine clock or the pacer.
- Link: default, FIGHT=1, BOSS=1, SENDABLE=1 link at head. check_link: default 407 kept / 407 allowed PASS, BOSS 501 /
  501 PASS, SENDABLE 407 / 407 PASS; FIGHT FAILs with 10 em10 functions (4476 B) by the name guard **on origin/engine
  78cf37442 too** (unchanged by this lane). No disc access in play (E1 FILES 0 / 0 / 0 in every scene).

## Bytes (for lane eng-mem2, which owns the map)
- Sections after --gc-sections (each image): crash_screen text 4244, data 52, bss 8962 (glyphs 4608, log ring 2048,
  rows 1536); pc_sampler text 1912, data 8, bss 60; strings merged into .rodata (not attributed).
- Image end, SENDABLE default image: 8c2302c8 (base) to 8c234bf4: +18,732 B.
- After-play arena margin (selector): LEON 217088 to 200704, FIGHT 45056 to 24576, HILL 434176 to 413696, BOSS
  2007040 to 1986560 B. CRASHCTL and PCSAMPLE threads take 4 KiB stacks from the heap (control and lab scenes only);
  PCSAMPLE's ring 32 KiB at load.

## Not done
- The address-fault screen on hardware (deferred console run); HALT / assert screens (arch_abort is wrapped by the
  console loop's client in SENDABLE images; no engine HALT exists); a hang screen (left to the loader's deadline).
