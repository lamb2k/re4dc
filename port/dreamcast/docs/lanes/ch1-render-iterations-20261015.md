# Chapter 1 render POC: persistent iteration

> Current snapshot: [physical-test handover, 2026-10-16 UTC](ch1-physical-validation-20261016.md). The final combined image saves 1.268 ms in the model; earlier image measurements below remain historical evidence.

The user requested a persistent goal on 2026-10-15 after the bounded POC in
`ch1-render-poc-20261015.md` (local commit `168042a3`). The goal is active.

Work remains isolated in `/root/probe/codex-ch1-render-20261015/tree`, branch
`codex/ch1-render-poc-20261015`. Private inputs and evidence remain local.
This does not authorize publication, SD copying, or changes to other worktrees.

## Order and acceptance

1. Matched baseline/candidate Flycast console checks: GDEMU/DMA timing and the
   interpreter's SH-4 cache model, distinguishing emulator defects from game
   defects. These runs are never performance measurements.
2. Full H2 and bell playback, including the r100 cliff movie. Qualified skips
   from the first POC do not establish complete playback.
3. Resolve blockers, then prepare matched GDEMU builds for physical Dreamcast
   performance and stability checks. Emulator/model evidence cannot satisfy
   physical-console acceptance.
4. Extend scenery conversion room by room with asset/strip identities, visual
   checks, memory gates, matched cost, and source-state proofs. Keep SH4ZAM in
   its current render-only configuration and the slower one-pass experiment off.

## Iteration 1: compatibility checks

Evidence root `E` is
`C:\Flycast-Evidence\re4-dreamcast\codex-ch1-render-20261015`.
Local orchestration lives in `C:\Game Dev\Emulators\_codex_ch1_20261015`:
`make-compat-gates.py`, `compat_gates.py`, `compat-run.py`,
`compat-review.py`, and `movie-review.py`. The runner records emulator hash,
configuration hash, environment, exact ELF/disc hashes, fixture and process
ownership in each run. It uses the existing trace semaphore and isolated ext4
stager. All comparisons use baseline `cxtp0rT` and candidate `cxfinalrT`, with
identical T15 data and fixture inputs. These are diagnostic twins, not release
or hardware-timing images.

### GDEMU timing: first matched seed passes

Installed flycast-console is source `41905914`, binary SHA256
`29f4c7f7c5bdd81d506528e0f77588acdf31cc8d300b2aa6231c1b471259b801`.
Settings: dynarec on, `RE4DC_GD_PROFILE=gdemu`, seed 3, jitter 20000,
early-completion default 1000/1000. Each run is bounded to 60 seconds.

| Scene | Common trace frames | Inventory-masked frames | Result |
|---|---:|---:|---|
| r101 fight | 1403 | 0 | STRICT and MUST-IDENTICAL |
| r100 radio/subscreen | 1653 | 873 | STRICT and MUST-IDENTICAL |
| r101 to r103 | 1542 | 473 | STRICT and MUST-IDENTICAL |

Both arms reach each scene, including r103 entry. Six logs pass TEX_CHECK and
LEON-GC; no MISSING/HALT/OOM, trace gaps or overruns. The radio fixture covers
opening the call; its scripted A presses do not reach that subscreen's loop.
Evidence: `compat-gdemu-<scene>-<arm>-s3`, `compat-gdemu-summary.json`.
This is one seed; the wider multi-seed race gate is still outstanding.

### Full H2 reproduces the known cliff-movie failure

The existing full-play H2 warp and pad script run without movie skips to trace
tick 2200 (300-second timeout). Both arms fully play s03 (1465/1465) and s20
(571/571), then fail s30: terminal 3, zero of 340 frames. At its reservation
failure, a 55296-byte piece cannot fit: total free 275552, largest block 40736.
The entry `heap_before` is 143232. This agrees with the consolidated handover's
known r100 s30 heap-4 shortage; it is not a new POC regression or a gate pass.

The arms remain STRICT over 2202 records and MUST-IDENTICAL over 2201 decisions;
493 records are inventory masked, no gaps. TEX_CHECK and LEON-GC pass. Those
results do not excuse the movie failure. Evidence: `compat-full-h2-{0,1}` and
`compat-full-movie-summary.json`.

The full bell run completes movie 10130 (1331/1331 decoded frames; 1300 and
1301 presented in the two arms), with no skip. Both runs are STRICT and
MUST-IDENTICAL through 2201 records, 473 inventory masked, no gaps; TEX_CHECK
and LEON-GC pass. Movie heap-before is 2173120 and staging 363328 in both.
Evidence: `compat-full-bell-{0,1}`. Completion does not mean every decoded
picture was presented, and the trace comparison does not compare movie pixels.

### Cache interpreter: not yet qualified

The installed console fork with dynarec off, `HWTRACE_ALIGN=1` and
`HWTRACE_CACHE=1` exits during boot in both arms, before room entry. Its Flycast
log reports `Fatal: SH4 exception when blocked`; the game log reports missing
disc files and `cDatTbl::end : memory failed`. Both also emit cache-observer
warnings at KOS `thd_block_now` / `save_regs_finish`, not in the POC renderer.
Evidence: `compat-cache-fight-{0,1}`. Treat these as failed coverage.

Two tool limitations need separation from a game fault:

- HLE TOC, PIO sectors, and subcode have raw-RAM fast paths, even while the
  STRICT_MODE interpreter uses its operand cache. An opt-in experiment routes
  these CPU-mediated writes through the existing WriteMem APIs, retaining raw
  DMA writes. It is isolated in `C:\Game Dev\Emulators\flycast-console-codex-ch1`,
  branch `codex/ch1-console-cache-20261015`, starting at `41905914`.
- The host log reader reads the emulator's raw RAM directly through process
  memory, whereas the game's log ring is written through cached addresses.
  GDB also returns raw RAM. The null holes in the captured log are not
  independently proof of game corruption. Do not flush caches merely to make
  the log readable: that could conceal the behavior under test.

The same rebuilt emulator was tested with `RE4DC_HLE_CACHE_CPU=0` and `=1`
against the identical baseline disc. Switch 0 repeats the startup exit; switch
1 reaches r101 gameplay through tick 325 in 60 seconds. This confirms the
startup effect of the HLE path correction. The new emulator hash is
`1b3c29fc53782c59bbcd9be847d4f6e976c5f8fc5efb59f1d78ae11df5912f7d`;
evidence is `compat-cache-hle-{0,1}`. Its framebuffer was inspected.

The observer still flags KOS context saves and several render-header copies;
these require an audit, not a blanket clean-memory verdict. Extended matched
baseline/candidate runs use the correction with the real cache model active,
alignment checks on, and the optional observer off. Both extended runs finish
normally at the reader's tick-2000 stop (300-second timeout); both enter r101,
with no emulator Fatal or MISALIGN lines. The candidate's final framebuffer was
inspected. The raw captures contain 2971/2875 null bytes and malformed records,
so the trace comparison is rejected: its first reported difference is the
corrupted value `es=811native` at tick 60, not a valid state hash. Evidence:
`compat-cache-hle-ext-{0,1}` and `compat-cache-summary.json`. This is evidence of
sustained operation under the corrected cache model, not a clean-memory or
STRICT acceptance.

No game/runtime change or installed Flycast replacement has been made in this
iteration. See the isolated emulator's `tools/console/CACHE-HLE-CH1.md` for the
limited scope and dependency-source build caveat.

## Next iteration

Fix log observability without changing guest cache state, then repeat the
matched cache comparison and audit observer warnings. Continue the multi-seed
GDEMU gate. For r100 s30, use the existing ownership and allocation mechanisms:
largest-first movie reservation and model-cache lending are already enabled;
the existing MOVIE_WORLD_ARENA mechanism is currently restricted to r11f movies,
so it is not an immediate switch-only remedy. Keep the reproduced baseline
failure explicit until a scoped fix passes its movie and lifetime checks.
