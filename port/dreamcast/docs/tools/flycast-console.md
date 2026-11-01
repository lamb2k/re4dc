# flycast-console: console-like Flycast for crash repro (never timing)

`flycast-console.exe` is a separate Flycast build that makes disc reads behave more like a real console with GDEMU or
a GD-ROM drive, so read-timing bugs that only show on hardware (the LinkOrder room-load stops, KNOWN issue #27) can be
reproduced on the PC. It never replaces the harness binaries (`d367-harness-par\flycast.exe`, `hwmodel-bin`). Its
frame times mean nothing: use it for crash and corruption repro only.

- Source: `C:\Game Dev\Emulators\flycast-console`, branch `console-like` (base = the flycast-strict-t11c snapshot,
  hwmodel fork + t11 cache observer). Build: `tools\console\build-console.cmd` (MSVC 2022 + Ninja, USE_DX9=OFF).
- Installed binary: `C:\Flycast-Evidence\re4-dreamcast\flycast-console-bin\flycast-console.exe` (KEEP).
- Everything is off unless an environment variable turns it on, so with no RE4DC_GD_* set it runs like the
  t11c strict snapshot (HLE BIOS reads land at once).

## GD-ROM timing profiles (RE4DC_GD_*)

Applies to the HLE BIOS DMA sector read (GDCC_DMAREAD, what KOS `cdrom_read_sectors_dma_irq` / fs_iso9660 use).
The harness has no BIOS in `data\`, so the HLE BIOS is always the one in use.

| Variable | Meaning | gdemu default | weak default | drive default |
|---|---|---|---|---|
| RE4DC_GD_PROFILE | `gdemu`, `weak` or `drive` (unset = off) | | | |
| RE4DC_GD_CPB32 | SH-4 cycles per 32-byte chunk | 533 (~12 MB/s) | 10417 (~600 KiB/s) | 4571 (~1.4 MB/s) |
| RE4DC_GD_SEEK | cycles from command to first byte | 20000 (100 us) | 1000000 (5 ms) | 2000000 (10 ms) |
| RE4DC_GD_STAT | gdemu/weak: cycles from command to BIOS status COMPLETED | 2000 | = SEEK | n/a |
| RE4DC_GD_IRQ | cycles from the last byte to the GD-DMA end IRQ | 4000 | 4000 | 4000 |
| RE4DC_GD_JITTER | max random extra cycles on SEEK, STAT and IRQ each | 0 | 400000 (2 ms) | 0 |
| RE4DC_GD_SEED | PRNG seed; a given seed is deterministic | 1 | 1 | 1 |
| RE4DC_GD_EARLY | gdemu/weak: per mille of commands whose status goes COMPLETED early | 1000 | 1000 | n/a |
| RE4DC_GD_CHUNK | bytes landed per scheduler event | 32 | 32 | 32 |
| RE4DC_GD_STREAM_CPB | weak: cycles per byte of a KOS stream DMA (REQ_DMA_TRANS) | n/a | 326 (~600 KiB/s) | n/a |
| RE4DC_GD_STREAM_LAT | weak: extra cycles (+ jitter) before a stream DMA lands | n/a | = SEEK | n/a |

- **gdemu:** the BIOS status reads COMPLETED almost at once (STAT cycles), independent of the data. The G1 DMA then
  lands the data progressively, 32 B at a time, written straight to RAM (bypassing the modelled operand cache, as a
  real DMA does). SB_GDST reads 1 while bytes are in flight. The DMA-end IRQ comes IRQ cycles after the last byte.
- **drive:** status stays PROCESSING until the last byte landed; seek latency, then ~1.4 MB/s.
- **weak** (2026-10-16, fork d17dc82d): a weak or clone GDEMU, as with `read_limit = 600` in GDEMU.ini plus slow
  command handling (clone status polling is far slower than a real drive, KallistiOS PR #957). gdemu semantics
  (status before the data), but data at ~600 KiB/s, 5 ms + 0..2 ms per command, and the KOS stream DMA
  (REQ_DMA_TRANS, which the gdemu profile leaves instant) slowed the same way unless HWTRACE_GDLAT is set. PIO
  reads still land at once. A test 14 run needs ~42 s of game time to reach r101 under it (7 s under gdemu).
- One G1 engine: a second DMAREAD waits for the first; a stream request (REQ_DMA_TRANS) or a PIO read lands any
  in-flight sector DMA at once (simplification).
- stderr (`serial.err.txt`) carries `GDCONSOLE` lines: the profile, the first 20 reads, then every 500th with counts.

## SH-4 cache model (STRICT_MODE)

`core/build.h` has `#define STRICT_MODE` on this branch: with the dynarec OFF (`Dynarec.Enabled = no`), memory reads
and writes go through the operand and instruction cache model (ReadCachedMem in sh4_mem.cpp), and `movca.l`
allocates a line without reading memory (copy-back), as on hardware. The interpreter is slow (a 150 s run reaches far
less game time); use it only when stale cache lines are a suspect. With the dynarec on (default), the cache model is
not used and the binary behaves like the fast build plus the GD profile.

**HLE BIOS coherency (fix-cachefly27, 2026-10-27, fork 8fb534cc, exe sha256 7e0b26ca...b1b1).** The HLE BIOS used to
write the GD TOC, subcode and SYSINFO results to host RAM with memcpy, past the modelled operand cache. A real BIOS
stores them with the CPU, through the cache, so under the cache model the game read stale TOC lines: endless disc
change / drive re-init before the title (Test 24b, 175 disc changes in 90 s; CACHE_COHERENT_DMA=1 in the game had
hidden it). Now any valid cached copy is refreshed after those stores (Sh4OCache::SyncFromRam). DMA (sector DMA,
gdemu landings, stream DMA) is unchanged: it bypasses the cache and the game invalidates, as on hardware. With the
dynarec on nothing changes. The previous exe is kept as `flycast-console-8e6c4987-prev.exe`.

## Savestates for cache-model comparisons (<= 1 min runs)

The interpreter runs about 5x slower than real time (a cold boot needs ~60 s to reach early boot, ~5 min to the
title menu). Comparison runs start from a saved scene instead:

- `RE4DC_CONSOLE_LOAD_STATE=<file>`: load this state at boot (before the first frame).
- `RE4DC_CONSOLE_SAVE_STATE=<file>`: quick saves go to this file; with `RE4DC_CONSOLE_SAVE_AT_S=<host s>` the
  emulator saves once that many wall seconds after start, with no input.
- Make a state from the same exe and the same disc, and save it with the cache model on (dynarec off):
  1. fast: dynarec on, RE4DC_GD_PROFILE=gdemu, reach the scene (QA disc: teleporter keys, for example
     `presets in | 2 | down`, then `a`, `a`, `down`, `down`, `a` = CHAPTER 1-1 / R101 BY THE CROSS), SAVE_AT_S ~50;
  2. cache: dynarec off (RE4DC_CONSOLE_DYNAREC=no), LOAD_STATE = step 1, SAVE_STATE = the final file, SAVE_AT_S 40.
  A dynarec-made state carries an empty (all-invalid) cache, so step 2 only warms it; the step-2 file is the one to
  use. A state belongs to one exe + disc image; never load it into another build.
- Run: dynarec off, gdemu, LOAD_STATE = the step-2 file, `--seconds 60`. fp_run.py passes the environment through
  and records RE4DC_CONSOLE_* in run-result.json `emu_env`.

| Gate (2026-10-27, cache model, gdemu seed 1) | Result |
|---|---|
| Test 24b release disc (52cb8198, track03 0aceb947), cold boot, old exe 8e6c4987, 90 s | FAIL: 175 disc changes, no title |
| same disc, new exe, cold boot, newgame keys (named exception: 500 s wall) | title, New Game, r100 entered (~480 s wall, guest frame ~13000); 1 disc change (boot), 0 bad reads |
| Test 24b QA disc, state at r101 by the cross, 60 s | r101 runs ~30 s game time, 0 bad reads, 0 disc changes |
| Test 22 QA disc (a2477bd2), state at r101 by the cross, 60 s | same, 0 bad reads, 0 disc changes |
| Test 24b release disc, dynarec on, profile unset, old vs new exe, 60 s | same title/state sequence (1 disc change each) |

Evidence: `C:/Flycast-Evidence/re4-dreamcast/fix-cachefly27-20261027` (runs/, states/).

## Harness use (opt-in RE4DC_EMU=console)

- Full-play / gate runs: `RE4DC_EMU=console` makes `tools/d367/fullplay/fp_run.py` copy flycast-console.exe instead
  of the template exe (RE4DC_CONSOLE_EXE overrides the path). RE4DC_GD_* pass through the environment;
  `RE4DC_CONSOLE_DYNAREC=no` writes `Dynarec.Enabled = no` into the run's emu.cfg. run-result.json records `emu` and
  `emu_env`. From Git Bash add the names to MSYS2_ENV_CONV_EXCL if a value looks like a path.
- One-off runs: `tools\console\fc-run.sh <run> <disc.gdi> <syms.txt> <seconds> [dynarec=no] RE4DC_GD_PROFILE=gdemu
  RE4DC_GD_SEED=3 RE4DC_GD_JITTER=20000` (Git Bash; hard-links the disc into the run dir, boot2.ps1 log reader).

## GDEMU race gate

`[RE4DC_GD_PROFILE=gdemu|weak] [SECS=60] tools/d367/fullplay/gdemu_gate.sh <tag> <evidence dir> <disc> "<twin syms>" <door103 fixture|-> 1 2 ... 10`
(Git Bash). `<disc>` is an fp_master.sh twin base (fixture into track 1) or a plain disc dir whose `dc/warp.txt`
already holds the fixture (pass `-`), such as a mkdcdisc twin. 10 seeds, r101 entry plus the r103 door load, at most
MAXP (6) at once. SECS defaults to 60 (lean rule); the weak profile needs SECS=150 (named exception: ~42 s to
r101 and a slow door at 600 KiB/s). Pass = every seed reaches r103 with no stop and no bad read; the table gives per
seed bad reads, stop, the guest-time r101 placement and door time (emulator model, not console timing).

## Results (2026-10-15, gdemu, jitter 20000, dynarec on; crash repro, not rates)

| Disc | Seeds stopped | What stopped |
|---|---|---|
| LINKORD-D2 (585327c5) | 1/5 | MISSING motion identity/header mismatch (as LINKORD2 on the console) |
| LINKORD-D3 (7a801afc, CRC check) | 3/5 | DISCCRC BAD-READ aica_str.dat / tex.pak, all `gd 1 sem 0` (engine still writing, no stale count) |
| LINKORD-D3-CTL (12.2 order) | 0/5 | |
| LINKORD-D3-FIX (KOS_DMA_DONE_FIX) | 0/15 | |
| test 13 (c1ae83dd twin, door103) | 3/10 | MISSING enemy texture identities (2), HALT model.cpp(1907) (1) |
| test 14 candidate (e2048df6 / 12dddcac twin, door103) | 0/10 | |

## Results (2026-10-16, fork d17dc82d, dynarec on; crash repro, not rates)

| Disc | Profile | Seeds failed | r101 placed (game time) |
|---|---|---|---|
| test 14 candidate twin (fp_master base, our layout, 3e24dedc) | weak | 0/10 (0 bad reads, 0 stops) | ~41.9 s |
| test 14 mkdcdisc standard twin (same files, 3e24dedc) | gdemu | 0/10 | ~7.0 s |
| test 14 mkdcdisc standard twin | weak | 0/10 | ~42.2 s |

Under the weak profile almost every read is a one-sector command, so the 5 ms per command costs more than the
600 KiB/s rate. The door to r103 itself showed no clear change (its reads in this fixture are few); r101 entry did.
Evidence: `C:/Flycast-Evidence/re4-dreamcast/disc-20261016` (gate-*.log, gate/).
e4-dreamcast\disc-20261016 (gate-*.log, gate\).

The model makes every read report COMPLETED early (worst-case GDEMU). Interpreter + cache model (dynarec off) runs
of D3/CTL/FIX seed 3 reached no disc-check reads within 240 s: too slow for this gate; keep them for cache suspects.

## Results (2026-10-16, lane discstd16 76f4af8c: the release-format gate; crash repro, not rates)

The test 14 standard image (mkdcdisc, console-tested in GDEMU slot 167) with the kit warp twin (built from a clean
checkout by kit-check.sh, 3,363,892 B, longer than the release program) swapped in by the rewritten swap-program.py
plus the door103 fixture (kit-check RACE_FIXTURE disc-race; disc_lint standard + loader PASS, 1ST_READ.BIN still last).

| Disc | Profile | Seeds failed | Bad reads | r101 placed (game time) |
|---|---|---|---|---|
| disc-race (standard, swapped) | gdemu | 0/10 | 0 | ~7.0 s |
| disc-race (standard, swapped) | weak (SECS=150) | 0/10 | 0 | ~42.2 s |

Evidence: `C:/Flycast-Evidence/re4-dreamcast/discstd-20261016` (gate-gdemu.log, gate-weak.log, gate/, kit-boot.log).
