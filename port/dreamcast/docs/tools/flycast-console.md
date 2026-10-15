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

| Variable | Meaning | gdemu default | drive default |
|---|---|---|---|
| RE4DC_GD_PROFILE | `gdemu` or `drive` (unset = off) | | |
| RE4DC_GD_CPB32 | SH-4 cycles per 32-byte chunk | 533 (~12 MB/s) | 4571 (~1.4 MB/s) |
| RE4DC_GD_SEEK | cycles from command to first byte | 20000 (100 us) | 2000000 (10 ms) |
| RE4DC_GD_STAT | gdemu: cycles from command to BIOS status COMPLETED | 2000 | n/a |
| RE4DC_GD_IRQ | cycles from the last byte to the GD-DMA end IRQ | 4000 | 4000 |
| RE4DC_GD_JITTER | max random extra cycles on SEEK, STAT and IRQ each | 0 | 0 |
| RE4DC_GD_SEED | PRNG seed; a given seed is deterministic | 1 | 1 |
| RE4DC_GD_EARLY | gdemu: per mille of commands whose status goes COMPLETED early | 1000 | n/a |
| RE4DC_GD_CHUNK | bytes landed per scheduler event | 32 | 32 |

- **gdemu:** the BIOS status reads COMPLETED almost at once (STAT cycles), independent of the data. The G1 DMA then
  lands the data progressively, 32 B at a time, written straight to RAM (bypassing the modelled operand cache, as a
  real DMA does). SB_GDST reads 1 while bytes are in flight. The DMA-end IRQ comes IRQ cycles after the last byte.
- **drive:** status stays PROCESSING until the last byte landed; seek latency, then ~1.4 MB/s.
- One G1 engine: a second DMAREAD waits for the first; a stream request (REQ_DMA_TRANS) or a PIO read lands any
  in-flight sector DMA at once (simplification).
- stderr (`serial.err.txt`) carries `GDCONSOLE` lines: the profile, the first 20 reads, then every 500th with counts.

## SH-4 cache model (STRICT_MODE)

`core/build.h` has `#define STRICT_MODE` on this branch: with the dynarec OFF (`Dynarec.Enabled = no`), memory reads
and writes go through the operand and instruction cache model (ReadCachedMem in sh4_mem.cpp), and `movca.l`
allocates a line without reading memory (copy-back), as on hardware. The interpreter is slow (a 150 s run reaches far
less game time); use it only when stale cache lines are a suspect. With the dynarec on (default), the cache model is
not used and the binary behaves like the fast build plus the GD profile.

## Harness use (opt-in RE4DC_EMU=console)

- Full-play / gate runs: `RE4DC_EMU=console` makes `tools/d367/fullplay/fp_run.py` copy flycast-console.exe instead
  of the template exe (RE4DC_CONSOLE_EXE overrides the path). RE4DC_GD_* pass through the environment;
  `RE4DC_CONSOLE_DYNAREC=no` writes `Dynarec.Enabled = no` into the run's emu.cfg. run-result.json records `emu` and
  `emu_env`. From Git Bash add the names to MSYS2_ENV_CONV_EXCL if a value looks like a path.
- One-off runs: `tools\console\fc-run.sh <run> <disc.gdi> <syms.txt> <seconds> [dynarec=no] RE4DC_GD_PROFILE=gdemu
  RE4DC_GD_SEED=3 RE4DC_GD_JITTER=20000` (Git Bash; hard-links the disc into the run dir, boot2.ps1 log reader).

## GDEMU race gate

`tools/d367/fullplay/gdemu_gate.sh <tag> <evidence dir> <fp_master twin base> "<twin syms>" <door103 fixture> 1 2 ... 10`
(Git Bash). 10 seeds, r101 entry plus the r103 door load, 150 s each, at most 6 at once. Pass = 0 of 10 stopped.

## Results (2026-10-15, gdemu, jitter 20000, dynarec on; crash repro, not rates)

| Disc | Seeds stopped | What stopped |
|---|---|---|
| LINKORD-D2 (585327c5) | 1/5 | MISSING motion identity/header mismatch (as LINKORD2 on the console) |
| LINKORD-D3 (7a801afc, CRC check) | 3/5 | DISCCRC BAD-READ aica_str.dat / tex.pak, all `gd 1 sem 0` (engine still writing, no stale count) |
| LINKORD-D3-CTL (12.2 order) | 0/5 | |
| LINKORD-D3-FIX (KOS_DMA_DONE_FIX) | 0/15 | |
| test 13 (c1ae83dd twin, door103) | 3/10 | MISSING enemy texture identities (2), HALT model.cpp(1907) (1) |
| test 14 candidate (e2048df6 / 12dddcac twin, door103) | 0/10 | |

The model makes every read report COMPLETED early (worst-case GDEMU). Interpreter + cache model (dynarec off) runs
of D3/CTL/FIX seed 3 reached no disc-check reads within 240 s: too slow for this gate; keep them for cache suspects.
