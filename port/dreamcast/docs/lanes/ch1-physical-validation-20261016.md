# Chapter 1 render POC: physical-test handover

This is the current handover for branch `codex/ch1-render-poc-20261015` and
supersedes the compatibility status and cost number in the earlier POC notes.
It covers the isolated tree `/root/probe/codex-ch1-render-20261015/tree` only.
The goal remains active. Physical appearance, performance and stability acceptance
is still required before converting another room or promoting this candidate.

## Current implementation

Runtime source is local commit `bce6fd98`, following trace-guard fix `a9533269`.
The candidate enables `ACTOR_PLAN=1 WORLD_VERT=1 WORLD_VERT_LEVEL=5`.
`ACTOR_ONEPASS=0` remains off because the fused experiment was slower.
The full PS2 Leon model remains (`LEON_LOD=0`); Ganado g70 level 2 and the six-alive
rule are inherited identically by both arms. SH4ZAM stays render-only:
`GAME_SH4ZAM=1 GAME_SH4ZAM_RENDER_ONLY=1`.

Both arms also enable `MOVIE_WORLD_ARENA=1 MOVIE_WORLD_ARENA_S30=1` to resolve
r100's pre-existing full s30 allocation failure. The fix borrows the retained
r100 world cell while full movie playback owns presentation, then rereads and
verifies the exact original mesh/sidecar before republishing it. It reuses the
existing 13-slot, 363,360-byte movie ledger, with no heap fallback. See
[ch1-movie-memory-20261015.md](ch1-movie-memory-20261015.md) for the contract.
The trace fix avoids dereferencing the already-masked player model while the
subscreen owns that backing. It does not introduce another masked field.

All newly introduced runtime knobs still default to zero. The new all-off image
`cxoffv2rW` remains byte-identical to the preserved loadable baseline:
`d9cad4f66d813eb2999b46b58390db0bd755504fbc7856c71c9cfec87ef99d5c`.

## Evidence established

`E` below is `C:\Flycast-Evidence\re4-dreamcast\codex-ch1-render-20261015`.
`Q` is `C:\Game Dev\Emulators\_codex_ch1_20261015`.

| Gate | Current evidence |
| --- | --- |
| GDEMU/DMA timing | `gdemu-final-s01..s10-{0,1}`: ten matched seeds, jitter 20,000 SH-4 cycles, original installed console emulator 41905914. All twenty runs reach r103 and tick 2000; each pair is STRICT for 2,002 records and MUST-IDENTICAL for decisions. No trace gaps, NULs, faults, OOM, texture failure or Leon GC fallback. |
| Actual SH-4 cache model, full H2 | `cache-final-h2-v2-{0,1}`: 2,502 STRICT records, 493 established subscreen-masked records, 2,501 MUST-IDENTICAL decisions. Zero NULs, gaps, faults, fatal exits and alignment warnings. TEXCHK and LEON-GC pass. |
| Full H2 movie playback | Each cache arm uploads and presents all s03 1,465/1,465, s20 571/571 and s30 340/340 frames, with no skip. s30 returns the world on its first attempt (`restored=1`, 13 slots, 363,360 bytes). Both arms retain one startup audio underrun per movie (18,556 silence bytes); continuous audible playback has not been reviewed. |
| Cache fight / call / door | Complete cache-aware traces pass for fight and call; the original door trace fault was fixed by `a9533269`, then `cache-fixed-door-{0,1}` pass STRICT/MUST through r103. See earlier iteration notes for exact images. |
| KOS pressure | `kosfm-<scene>-49152-{0,1}`: ten of ten pass with 48 KiB deliberately held, as one block and as fragmented blocks, across fight, call, door, return to r100 and return to r103. Minimum measured headroom is 7,456 bytes; smallest top chunk is 4,608 bytes. Diagnostic arm `cxfmsqrW`. |
| Movie ledger host checks | 1,179 assertions, 25 source contracts, UBSan and guard-page adapters pass. Includes r100 round-trip, all slots, failed/corrupt reload and stale generation. These adapters do not execute Dreamcast file I/O. |
| GDI payload / boot readback | All four local packages verified directly from raw 2,352-byte track 3 through ISO9660/Rock Ridge. Play: 2,619 files each. Benchmark: 2,621 files each. Raw boot binary matches ELF objcopy plus verified zero padding to 2,048-byte sectors. |
| Packaged play boot | Both exact GDI play images reach the fresh-VMU system-information prompt with the actual cache model and GDEMU timing profile. No fault, fatal error or alignment warning in the 120-second captures. This is a boot check, not a manual playthrough. |
| Packaged benchmark execution | Both exact-GDI cache/GDEMU runs finish both scenes with identical per-scene end-state hashes. Both result screens were visually checked. Candidate capture passes; baseline execution passes but whole-capture integrity remains FAIL because of one malformed boot-log line (see below). |
| Expanded cache warning attribution | `cache-audit-h2-{0,1}` repeat the full 2,502-record STRICT / 2,501-decision H2 pass. Each arm has 35 observed sites, all classified by source/disassembly, zero overflow, and a census sum exactly matching total garbage reads. Stale-read, lost-write, clobbered-writeback, dirty-DMA and SQ-over-valid counters remain zero. |

The earlier original-build GDEMU seed-2 STRICT failure is retained in
`gdemu-race-summary.json` and the A/A and repeated A/B evidence. It is not
relabelled a pass. The rebuilt matched pair passes all ten seeds, including 2;
no ablation establishes which layout/timing change removed that divergence.

## Cache and capture interpretation

The isolated emulator is now at local commit `def67d76` (after `1a428003` for
non-mutating cache-aware logging). The expanded census binary is SHA256
`d10cdde02cc11fc0d232262984d5a25b39256684361b5c67db39668f2cca3e21`.
It records read PC, allocation PC, byte offset and width separately, so a shared
memcpy site cannot hide a later allocation origin behind its first samples.

The 35 sites in each arm are 14 packed-polygon header padding reads (bytes
16..31), two sprite-header padding reads (24..31), 12 modifier-header padding
reads (8..31), and seven KOS voluntary-thread-return reads of caller-clobbered
R0..R6. R7 is written by MOVCA itself. `pvr_prim.c` and `entry.s` / `thdswitch.s`,
plus the linked ELF disassembly, establish those classifications. The earlier
read-PC-only logger hid the sprite origin behind memcpy. These events remain
visible and their nonzero totals remain in the report; they were not suppressed.
Dirty OCBI callers resolve to the disc-stream destination invalidation before
DMA, and no subsequent lost-write read is observed. This is source-based
classification of observed accesses, not an exhaustive clean-memory or hardware
certification. See `cache-audit-h2-site-classification.json`.

`gdi-cache-retry-bench-baseline` has exactly one NUL in its initial
`OSCreateThread` log line. The complete raw capture is retained and its original
whole-capture gate stays failed. Both benchmark execution/result screens and
end-state hashes are verified separately. `LOGIC_TRACE=0` intentionally uses
the inherited non-atomic logger (`platform/mem.cpp`), so concurrent writer
interleaving is a plausible source; that cause was not isolated. No release
logging change was introduced to hide or repair this sample. The atomic traced
H2 captures have zero NULs/gaps and pass STRICT. `physical-gdi-qa-summary.json`
records `EXECUTION_PASS_CAPTURE_LIMITED` for this baseline capture.

The first benchmark-baseline launch also failed before emulator launch while
copying the emulator executable. Its partial staging and error remain. The
candidate and replacement baseline ran the same hash-verified `d10cdde0`
executable; an immutable versioned copy is now pinned for future runs. This setup failure is
not counted as an execution pass or as a game fault.

## Current cost result

**MODEL, not physical hardware:** `cxfmc0rW` versus `cxfmc1rW`, the same T15 data,
`benchmark-r101-t12`, burning cross, frames 500..799 sampled every tenth frame
(30 measured frames), pacing off. Console-fit SH-4 model:

- Baseline: 375,027,378 cycles / 30 = **62.504563 ms per frame**.
- Candidate: 367,419,838 cycles / 30 = **61.236640 ms per frame**.
- Saving: **1.267923 ms (2.03%)**. This supersedes the earlier 4.501 ms result for
  the older image. It is not a fresh console FPS measurement or a 30 FPS result.

Candidate L5 loads 1,113 meshlets / 60,606 vertices versus L0's 1,830 / 86,592.
World allocation is 1,305,760 bytes in both arms. The final candidate image crosses
an arena page boundary and starts r101 with 4,096 bytes less heap 4. Do not call
the whole image heap-neutral. The hardware-model reports are
`E/hwmodel-cxfmc{0,1}-cross`, with console sums, frame traces and call attribution.

## Physical packages

Prepared locally at `C:\Game Dev\Emulators\RE4DC-CH1-POC-Physical-20261016`.
The date in this folder is UTC. No publication or SD copy has been performed.
Each role has its own four-file `gdemu` directory, checksums, full resolved knobs,
fixture, payload manifest, GDI readback report and source/ELF provenance.

| Role | Arm | ELF SHA256 prefix | Distinction |
| --- | --- | --- | --- |
| play-baseline | cxfmp0rW | 6bd2da57b337b2cd | POC actor/world knobs off |
| play-candidate | cxfmp1rW | dd2cba4d778bb314 | Actor plan + world L5 |
| bench-baseline | cxfmb0rW | 1e488d38223230de | Results ID CH1-B0 |
| bench-candidate | cxfmb1nrW | 789c5da4784c4b41 | Results ID CH1-B1 |

Play variants have `DBG_WARP=0 PC_SAMPLER=0 LOGIC_TRACE=0` and the normal 196,608-byte
KOS reserve. Benchmark variants use the existing `BENCHMARK=1` two-scene program,
with its established 262,144-byte KOS reserve for scene resets. Both have normal
fast pacing. Benchmark and play memory layouts therefore differ. Within each
pair, all payloads match except ELF-linked overlays; boot programs differ as
expected. Both discs carry the same L0 and prepared L5 files.

The benchmark automatically runs the cross (room frames 300..1199) and the r100
house (1100..1599), then shows a results code. This window differs from the
30-frame sampled model window. Use the real console results, not emulator
benchmark numbers, for adoption. Run baseline, candidate, candidate, baseline
on the same console/display/settings and record all four results screens/codes.
For stability, use the normal-play pair for New Game through s03/s20/s30, radio
and inventory close, r101 fight/bell, farm entry, backtracking and death/retry.
Review Leon's jacket/hands, scenery, shadows, HUD and movie audio while doing so.
Record the exact build role and scene for any failure.

## Reproduction and preservation

Runtime builds use the isolated actorplan wrapper and the existing T15 recipe.
`Q/build-movie-final.sh` produces the traced and model pair;
`Q/build-movie-squeeze.sh` produces its KOS pressure twin;
`Q/build-physical.sh` records the four physical-build commands.
`Q/rebuild-physical.sh <fresh-prefix>` refuses existing outputs and runtime
changes from the tested source; `Q/repackage-physical.py <prefix> <new-C-folder>`
rejects private-data drift against the original package manifests.
`Q/package-physical.py` masters on ext4 through the existing `mkgdi.sh`, hashes
all payloads, reads them back from raw GDI and verifies the Windows copy.
`Q/verify-physical-gdi.py` is the readback adapter. `Q/gdi-qa.py` runs exact packaged
tracks in isolated captures. Build recipes and tooling are local, not uploads.
Use new output labels for rebuilds; preserve the existing images and evidence.

Review scripts: `race-final-review.py`, `cache-peek-review.py h2-v2 cache-final`,
`cache-final-h2-movies-review.py`, `movie-squeeze-review.py`. Each reads the
preserved logs; the full summaries live in E. The emulator fix lives only in
`C:\Game Dev\Emulators\flycast-console-codex-ch1`; the installed console emulator
is unchanged. Cache-aware logging reads P1 cache bytes without cache fills,
evictions, writebacks, guest writes or guest-cycle changes.

## Remaining acceptance

1. Obtain physical-console appearance, performance and route-stability results.
   The remaining capture limitation is explicitly retained above; do not claim
   the untraced baseline boot log is wholly intact.
2. Only after those gates, extend the compatible conversion to the next room,
   with that room's original-data reference, identities, memory, STRICT behavior,
   visuals and matched cost evidence. Do not extrapolate r101's gain to Chapter 1.
