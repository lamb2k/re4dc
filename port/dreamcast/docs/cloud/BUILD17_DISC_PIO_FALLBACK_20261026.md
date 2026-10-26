# Build 17: bounded disc retirement and PIO recovery

Date: 2026-10-26. Branch: `codex/disc-pio-fallback-20261026`.
Base: [`ab31de24`](https://github.com/lamb2k/re4dc/commit/ab31de24c84034b5356ca42ab105856cb6824ed1),
the newest `origin/t15/int` at final qualification. Work began on `714589f6`;
the base was refreshed after unrelated castle31 updates. Issue:
[#28](https://github.com/lamb2k/re4dc/issues/28).

## Result and scope

`DISC_PIO_FALLBACK=1` adds a separately selectable recovery path. A failed DMA
command is retired while the caller still owns G1 and its destination, then
the **same buffer, first sector and sector count** are submitted by PIO. Two
consecutive failed DMA attempts permanently select PIO for the session.
Successful PIO does not erase that failure count. Successful DMA erases it
only after any outstanding stream-table validation accepts its contents.

The make default is **0**, with no recipe change. The option requires
`KOS_DISC_FIX=1` and `DISC_READ_FALLBACK=2` or `3`. It rejects composition with
the older destructive disc-fault hooks; its fault proof uses synthetic
devices. No new assembly, link layout, worker, callback or allocation is
introduced. Claude decides whether and when to merge and enable it.

This is a loading-reliability change. It does not make world drawing cheaper
or establish an FPS gain. When enabled, it refuses CD streams from startup so
the ISO reader uses the bounded sector path even on a healthy drive. That is
an intentional behavior and throughput difference requiring the owner runs
below. The complete game image and real-loader behavior remain owner gates.

## What actually waits

The queue's description of `[reaper]` as a disc worker is not supported by the
pinned source. KOS's reaper cleans up terminated threads; waiting on
`thd_reap_sem` is its normal idle state. The port already excludes that thread
from its stuck-thread report. `DVDReadAsyncPrio` in
[`platform/dvd.cpp`](../../game/platform/dvd.cpp) performs a synchronous
`fs_read` before delivering the SDK callback. No new disc reaper is needed.

The audit used KOS
[`804b3195`](https://github.com/KallistiOS/KallistiOS/tree/804b3195ebd1a06a27cc2b3a5eacf7a2429040a3),
especially `hardware/cdrom.c`, `hardware/g1ata.c`, `fs/fs_iso9660.c` and
`kernel/thread/thread.c`, together with the repository's KOS patches.

| Path | Finding and enabled behavior |
| --- | --- |
| Game DVD, room, texture, motion, movie and sound file reads | Go through ISO filesystem reads and the wrapped sector/stream entry points. |
| KOS sector DMA | The existing DMA-wait patch bounds `dma_done`; ready and final-command polls can still be untimed. The new data path uses direct BIOS sector commands with its own bounded polls. |
| KOS stream start/request/stop and ISO's short stream poll | These have further completion/abort waits. Enabled wrappers refuse start/request and report no active stream on stop, so the ISO fallback never installs this stream ownership. |
| Direct v2 sector reader | Previously released G1 before the engine/landing check. The enabled controller retains G1 through completion, landing, retirement and retry. |
| First sound stream table | A completed transfer can still contain invalid offsets. The actual `SndInit` retry now holds PIO policy through the entire logical-file reread and validates bounded offsets before dereferencing them. |
| Mount/PVD probe | Its `cdrom_read_sectors_ex` call is covered by the wrapper. |
| TOC, status, initialization and BIOS internals | These remain distinct firmware operations. A BIOS syscall that never returns cannot be interrupted by a deadline in its caller. |

There is no in-tree caller of a raw `g1_ata_read_*` data path to redirect.
DreamShell implements the GD BIOS interface; the new code calls its PIO
command, not an assumed direct ATA programmed-I/O loop. KOS's CD and ATA IRQ
handlers signal their waiters only when their own DMA state is installed.
The new sector path installs none of those waiters or stream callbacks.

## Ownership and retirement

The production controller is
[`disc_pio_fallback.h`](../../game/platform/disc_pio_fallback.h); the actual
KOS/BIOS adapter is
[`disc_pio_native.inc`](../../game/platform/disc_pio_native.inc).

1. Validate the request and acquire `_g1_ata_sem` with a 30-second bound.
   Keep the request immutable. DMA requires 32-byte alignment; the ordinary
   PIO alignment requirement remains two bytes.
2. Bound command submission at 200 ms and command completion at
   `5000 + 8 × sector_count` ms. Completion is not sufficient by itself:
   require GDST idle, then the existing destination landing-marker check.
   The idle bound is `1000 + 8 × sector_count` ms; landing has a 250 ms bound.
   Command waits retain `DISC_POLL_SPIN_MS`; engine/landing waits retain
   `DISC_LAND_SPIN_MS`, so the recipe's 20 ms landing-yield window still applies.
3. On failure, disable GD DMA, abort the owned command, and wait up to 1 s.
   If abort or engine-idle proof fails, reset/init the BIOS driver, prove the
   engine idle and restore 2048-byte data-sector mode before retrying.
   Initialization completion has a 6-second bound.
4. Clear only the GD DMA completion/overrun/illegal-address event bits,
   re-enable the engine and issue the exact same request as PIO. The lock is
   released once after recovery or a terminal error. No-disc/disc-changed
   results are not counted as failed DMA attempts.
5. If retirement cannot prove safety, poison the reader and fail-stop without
   returning the possibly owned destination to its caller. A failed PIO retry
   is retired too; it does not recurse indefinitely.

The failure counter saturates at two. An accepted DMA outside a semantic
validation window resets it immediately; inside the window that reset waits
for acceptance. A transport fault followed by a bad semantic check counts as
one DMA failure, not two. Once latched, session PIO is never cleared by a
successful read, validation end, or room transition.

Each actual fallback policy transition emits one
`DISC: DMA->PIO after <reason> (...)` line. Reads already in permanent PIO do
not emit new switch lines. Existing optional diagnostic logging remains
separately selectable.

### A corrupt final sector must not come back from the ISO cache

The first file is a logical read, potentially several sector calls plus a
cached partial final sector. Setting a one-call PIO flag would allow an
intervening read to consume it; retrying without cache invalidation could
return the same corrupt final bytes without touching the disc.

The enabled Snd path therefore brackets the complete initial read/check and
reread/check. On rejection it sets PIO policy for the whole reread and calls
the small
[`kos-804b319-iso-pio-retry.patch`](../../patches/kos-804b319-iso-pio-retry.patch)
helper. Under the existing ISO/cache locks, that helper invalidates the 16
file-data cache tags. It preserves open handles, directory-cache state and
file identities; it does not call `iso_reset`. G1 is released before taking
the ISO lock, preserving the normal ISO → G1 order.

[`disc_stream_table_check.h`](../../game/platform/disc_stream_table_check.h)
checks length before reading either header and uses subtraction bounds to
avoid offset-addition overflow. Read lengths start at zero so failed reads
cannot leave an indeterminate length. A second invalid result retains the
existing safe no-streamed-sound behavior. The check preserves the existing
two-block structural contract; it is **not authentication of arbitrary
payload corruption** or a replacement for a known-good data hash.
Other assets' CRC/admission failures do not automatically trigger this
sound-table-specific semantic retry.

## Synthetic proof

Run from the repository root:

```sh
python3 port/dreamcast/tests/test_disc_pio_fallback.py --report /tmp/build17-host.json
```

The gate runs the same production controller used on target. It also imports
and executes the actual native adapter, sector/stream wrappers, first-file
Snd retry region and added ISO helper, with fake BIOS/semaphore/time/MMIO and
mapped SH4 address aliases. It does not substitute a separate implementation
of the recovery policy.

The recorded gate has **73 passing named cases**: 21 controller, 4 semantic
state, 29 validator and 19 native/integration cases. The 54 portable cases
also pass AddressSanitizer and UndefinedBehaviorSanitizer. LeakSanitizer is
disabled because this sandbox cannot provide its process-inspection support;
the native fixed-address mapping run is separate from sanitizer shadow RAM.

Recorded evidence:
[`BUILD17_DISC_PIO_FALLBACK_20261026.host.json`](BUILD17_DISC_PIO_FALLBACK_20261026.host.json).

Cases include dropped completion, command failure, missing landing bytes,
corrupt completed data, late completion after timeout, done-but-engine-busy,
bounded reset/reinitialization, no-disc/disc change, lock refusal, unsafe
retirement, exact sector geometry, balanced lock ownership, accepted DMA
breaking a failure streak, two semantic failures latching PIO, an intervening
read during whole-file retry, cached-final-sector invalidation, and a bad
second sound read. The receipt includes source hashes, commands and case
names. Fake clocks and mapped RAM do not prove actual SH4 coherence or
firmware behavior.
The native spin-budget case also proves that command, engine-idle and
byte-landing waits choose the intended polling versus landing setting.

## SH4 build, identity, code and stack

The [target gate tools](../../tools/cloud/build17/README.md) derive flags from
the actual Makefile and ordered public recipe. The toolchain is the pinned
KOS build of GCC 15.2.0, binutils 2.45.1 and newlib 4.6.0.20260123, with KOS
`804b3195` and SH4ZAM `33fa485`. Source/archive/compiler hashes are in the
[toolchain receipt](BUILD17_DISC_PIO_FALLBACK_20261026.toolchain.json).

The [target receipt](BUILD17_DISC_PIO_FALLBACK_20261026.target.json) records:

- **24 byte-equality checks PASS:** fallback 2 and recipe-style fallback 3
  with the meter; absent and explicit zero; DVD, Snd and patched ISO; complete
  preprocessed source and complete ELF object bytes. No debug records were
  emitted in any arm. Source input uses stdin with the real include directory;
  objects are neither stripped nor byte-normalized after compilation. Make
  flags, object lists and linker flags also retain off identity.
- Both enabled profiles compile. Relocatable links resolve every new
  validation/cache-invalidation hook exactly once. Ordinary game/KOS callees
  remain unresolved; this is not a full game link or full-image proof.
- Five invalid knob/fault-hook configurations are rejected. The receipt
  lists the exact cases, recipe inputs and documented public missing-data
  substitutions. DVD uses its actual `-O1` profile and Snd its final `-O2`
  profile with the recovered-source safety flags.

Combined **object-section** deltas across those three translation units:

| Enabled profile versus its baseline | Executable bytes | Allocated bytes | Zero-fill bytes |
| --- | ---: | ---: | ---: |
| Fallback 2 | +2,844 | +3,080 | −16 |
| Recipe-style fallback 3 + meter | +1,456 | −1,096 | −2,078 |

These are complete compiled-TU totals, not the final garbage-collected ELF or
a heap saving. The enabled early path makes some legacy internal data/code
unused; that explains why an allocated-section delta can be negative.
The new policy state itself is **8 bytes**. There is **no new heap-4 or KOS
heap allocation** and no added per-read destination copy owned by this code.

Compiler-reported native helper frames are: `pio_read` 32 B, controller
`read` 36 B, `transfer` 40 B, `retire` 36 B, `wait_command` 56 B, and
`wait_idle` 36 B. The validation wrappers/helpers and ISO invalidation helper
have 4 B frames. Enabled `SndInit` has a 92 B frame. Individual static frames
are not the complete nested stack peak; BIOS, scheduler and interrupt stack
use is outside this measurement.

## Cycles and traffic: the priced portion

The [cost receipt](BUILD17_DISC_PIO_FALLBACK_20261026.cost.json) executes the
compiled production controller/state/validator instructions in the existing
SH4 trace interpreter and prices them with the repository hardware model.
All **19 cases pass**, including state outcomes and exact request geometry.
The controller fixture includes deterministic fake-driver bookkeeping and
transfers no payload. Its synthetic pause advances time by 1,000 ms to reach
deadline branches quickly; that is not a real polling interval.

Warm cycles use perfect caches. Cold-I cycles start an isolated 8 KiB
instruction cache cold, with perfect data cache and the synthetic fixture's
layout. Loads/stores include stack and literals. Distinct demanded 32-byte
lines describe the footprint, not measured cache misses or bus transfers.

| Compiled case | Warm cycles | Cold-I cycles | Loads / stores | Load / store bytes | Distinct data lines | Fixture stack B |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Accepted DMA request | 204 | 427 | 57 / 27 | 214 / 105 | 9 | 60 |
| Accepted session-PIO request | 191 | 424 | 51 / 25 | 196 / 100 | 9 | 60 |
| Dropped DMA completion → PIO | 604 | 930 | 165 / 73 | 621 / 289 | 11 | 60 |
| Missing landing marker → PIO | 452 | 752 | 126 / 51 | 471 / 201 | 10 | 60 |
| Abort timeout → reset → PIO | 724 | 1,060 | 193 / 82 | 726 / 325 | 12 | 60 |
| First semantic rejection, state only | 41 | 84 | 8 / 4 | 8 / 4 | 1 | 0 |
| Second semantic rejection, state only | 44 | 87 | 8 / 5 | 8 / 5 | 1 | 0 |
| Valid 44,384-byte stream-table check | 343 | 465 | 59 / 44 | 140 / 80 | 7 | 48 |

The validator uses the actual `SND_RIT` alignment of two bytes and actual
compiler/libc instructions. The table's size is its accepted input length;
the validator inspects the two headers, not all 44,384 bytes. The fixture
code totals 1,468 executable and 1,632 allocated bytes; those are test-fixture
sizes, separate from the native-TU deltas above.

Unpriced native work includes BIOS execution, G1 semaphore/timer calls,
IRQ/event-register access, scheduler transitions, cache maintenance, actual
poll counts and device transfer. A 21-sector command requests **43,008 bytes**;
one same-sector retry requests another 43,008. Successful aligned reads also
use the existing 32-byte destination marker; the cache operations and the
loader's implementation of PIO must be measured on the device. ISO retry
invalidation performs 16 data-cache-tag stores plus its pointer reads/locks,
without copying the cached sector payloads.

**MODELLED whole-frame scenario:** with no disc requests, this change adds
0 ms of executed recovery-path work. Assuming ten accepted synthetic DMA
requests per drawn frame at 200 MHz, their controller fixture costs total
0.01020 ms warm or 0.02135 ms with each request's I-cache cold. Ten session-PIO
controller fixtures total 0.00955 / 0.02120 ms. These are explicitly just the
priced component, not a before/after frame delta or complete frame time;
all real I/O and the other native work listed above must be added. A true
whole-frame improvement cannot be inferred from those small numbers.

## PIO read-rate cost

**No actual DreamShell PIO rate is available in this environment.** A fake
driver's elapsed time would not measure it. The BIOS may implement PIO using
different IDE/SD/loader paths, so an ATA headline bandwidth is not a valid
substitute either.

These are explicit **MODELLED payload-only scenarios**, before command
latency, cache work, scheduler delays or the failed DMA attempt:

| Assumed sustained rate | 44,384-byte table | 1 MiB | 8 MiB |
| --- | ---: | ---: | ---: |
| 2 MiB/s | 21.164 ms | 0.5 s | 4 s |
| 1 MiB/s | 42.328 ms | 1 s | 8 s |
| 0.5 MiB/s | 84.656 ms | 2 s | 16 s |

For payload `B`, the additional transfer time is
`B × (1 / PIO_rate − 1 / DMA_rate)`. If healthy DMA is 2 MiB/s, PIO at
1 MiB/s adds **0.5 s per MiB**; PIO at 0.5 MiB/s adds **1.5 s per MiB**.
Those are assumptions, not measured losses. The 44,384-byte logical file can
require 22 physical 2048-byte sectors, or 45,056 bytes, when its partial tail
is uncached; account for that distinction in the owner receipt.

A missing completion on a 21-sector request first costs approximately its
**5.168-second command timeout**, plus retirement and PIO. This is recovery
from a failed read, not steady-state PIO throughput. Permanent PIO avoids
repeating that DMA timeout after the second failure. Continuous movies must
also meet their actual sustained byte rate while sharing CPU time with
audio/decode/rendering; a door-load bandwidth result alone cannot qualify
movie playback.

## What the local owner must run

Use separate clean object directories for every arm. The existing make
system does not generally rebuild all objects when command-line knobs change.
Start from the same current recipe and data, then add
`DISC_PIO_FALLBACK=1`; keep `DISC_COMPAT=1`, `DISC_READ_FALLBACK=3`,
`DISC_DMA_WAIT_TIMEOUT=1`, `DVD_READ_SAFE=1` and the existing spin settings.
Use `DISC_READ_METER=1` and, for door timing, `DOOR_PROBE=1` in **both**
diagnostic arms, with the meter's existing prerequisites `PHASE_METER=1`,
`GAME_TICK_LOG=1` and `PACE_VMU_GPU=1`. Do not combine its wrappers with
`IO_PROBE`. Keep the old fault-injection knobs at zero.

1. On the affected DreamShell/IDE unit, record exact loader/firmware, media,
   sector format and DMA/Async settings. Run the relevant DMA/Async combinations
   with matched program/data hashes. Capture first-table acceptance, switch
   reason/count and whether later reads stay in PIO without repeating timeouts.
   Compare the loaded table bytes/hash with the owner's known-good source.
2. Repeat on GDEMU and the owner's Flycast setup. Confirm healthy DMA keeps
   working, no new switch log appears, and the enabled no-stream route does
   not introduce unacceptable load/streaming regressions. Off/absent must
   also pass the owner's complete image/overlay identity gate.
3. Measure the same cold and warm door transitions, a fixed-size file/read
   interval, a sustained movie and streamed music/speech. Retain requested
   bytes, wall duration, game-blocked time and CPU time. Separate initial
   timeout/retirement from settled PIO. Existing `DISCRD`/door meters count
   logical wrapper bytes; an internal retry is extra physical traffic, not
   a second successful logical request. Report the rates in bytes/s with
   the denominator and window stated.
4. Test room changes, save/load and the s30 route with audio active. Confirm
   no deadlock, stale destination, duplicate callback or unexpected heap
   loss; retain the project's logic and memory gates. A nonreturning BIOS
   syscall or hardware engine that will not retire remains a failure to
   escalate with the captured state, not a claim of successful recovery.

No private game data, console result, measured PIO rate or full-game
performance result is claimed by this branch.
