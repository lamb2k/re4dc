# Chapter 1 cliff movie: retained-world memory loan

> Current snapshot: [physical-test handover, 2026-10-16 UTC](ch1-physical-validation-20261016.md). The final combined image saves 1.268 ms in the model; earlier image measurements below remain historical evidence.

Local experimental branch: `codex/ch1-render-poc-20261015`.
The extension defaults off. This is emulator/component evidence, not physical
Dreamcast acceptance or permission to publish/copy a package to an SD card.

## Failure and scope

The full H2 fixture reaches r100s30 after r100s03 and r100s20. Both original
matched arms fail before the first cliff-movie picture: the second 55,296-byte
plane cannot fit. The allocator reports 275,552 bytes free but a largest cell of
40,736 bytes after its existing motion-cache eviction. The prior successful
skip fixtures did not cover this failure.

`MOVIE_WORLD_ARENA_S30=1` requires `MOVIE_WORLD_ARENA=1`. It extends the existing
D38 retained-world owner only to full, blocking movie `0x10030`: 288x192 YUV,
340 expected pictures, idle stream service, and the r100 SMX/TR4 package layout
(mesh 1,537,920 bytes; sidecar 19,612 bytes; retained cell 1,562,656 bytes).
The ordinary recipe and both switches' defaults remain unchanged.

The loan uses the existing 363,360-byte/13-slot ledger and existing player,
stream, teardown, generation and heap-transition hooks. There is no new heap,
heap expansion, general allocator fallback, resolution change or audio change.
The renderer relinquishes its world pointers after a completed presentation
fence. On return, the exact original mesh and sidecar are read into the same
cell and checked against their captured CRC and FNV before re-publication.
The LUT, gather pointer and pass masks are rebuilt. Source object identities,
serials, rest matrices, part witnesses and dynamic slot ordering are retained.

The r100 interior-cell loan/restoration stays in its existing route bridge.
Separate PVS and strip-group allocations are not borrowed; their Room4 owners
must still be valid. Unlike r11f, r100 restoration does not discard a PVS set.
The current tested recipe has PS2_PVS=0 and no r100 strip-group file.

The old arena guard now precedes the newer r11f renderer's early dispatch in
both mesh draw and source draw. The existing arena integration test caught that
ordering defect before this extension was enabled. Its helper extractor also
now selects the existing non-cabin UI-close signature correctly; the production
UI-close body was not changed.

## Evidence

Root: `C:\Flycast-Evidence\re4-dreamcast\codex-ch1-render-20261015`.

- `movie-arena-s30-host-final.json`: 1,179 assertions plus 25 source integration
  checks, actual extracted production lifecycle/restore/UI/service/heap helpers,
  guard pages and UBSan. Includes r100 round trip, exact-layout rejection,
  corrupted file and failed read cases, and owner invalidation during a read.
  Filesystem/device/package-validation adapters remain host substitutes.
- `movie-arena-h2-{0,1}`: `cxmv3rT` baseline and `cxmv4rT` render candidate,
  full H2 source fixture/pad, 360-second budget, stop after tick 2500. No skips.
  Both complete/present s03 1465/1465, s20 571/571 and s30 340/340.
- `movie-arena-h2-summary.json`: STRICT across 2,502 state records (493 masked),
  MUST-IDENTICAL decisions across 2,501 records, no trace gaps. TEXCHK and LEON-GC
  pass. TEXCHK reports three existing policy skips, zero failures.
- Both s30 loans use all 13 slots and return on the first reload attempt with
  `restored=1`. Source-heap free remains 135,040 bytes throughout the movie.
  The interior cell is restored afterward (fourth load, third loan). Late
  candidate framebuffers show the restored cliff scenery and Leon.
- The records count one initial audio underrun per movie in both arms. They do
  not establish uninterrupted analog audio or physical display cadence.
- `movie-arena-s30-source.patch`, SHA256
  `d62faad5c5e5364dbbde26e542642cd8d9faabf19193c905c5a04e43f4e86b41`,
  records the exact pre-commit source used by these H2 builds on `e4f5a2d2`.
- `cxoffv2rW`, all new switches off after the changes, retains loadable-image
  SHA256 `d9cad4f66d813eb2999b46b58390db0bd755504fbc7856c71c9cfec87ef99d5c`:
  byte-identical to the original explicit current-recipe baseline.

The later trace-only correction `a9533269` skips the player parts walk while
that already-masked backing belongs to the subscreen. It fixes an independently
reproduced operand-cache diagnostic fault; it does not add masked ticks or
change the scalar position feed. The rebuilt `cxfm0rT`/`cxfm1rT` pair includes
both corrections. Its full cache H2 and randomized GDEMU gates are separate
from the completed normal-emulator H2 result above.

## Reproduction

Authoritative checkout: `/root/probe/codex-ch1-render-20261015/tree`.
Builds, program registry and stage cache remain under the same isolated parent;
private inputs remain local. Existing coordinator checkouts/jobs are untouched.

- Full H2 builds: `C:\Game Dev\Emulators\_codex_ch1_20261015\build-movie-scope.sh`
  with `MOVIE_WORLD_ARENA=1 MOVIE_WORLD_ARENA_S30=1`, then `compat-run.py movie-arena`.
- Updated paired trace/cost builds: `build-movie-final.sh` in the same directory.
- Arena host test: `python3 port/dreamcast/tests/test_movie_world_arena.py`.
- Default-off identity: `build-offv2.sh`; only the private generated binary is
  inspected, not committed.

Each capture retains resolved build inputs, ELF/disc/configuration hashes,
reader logs, screenshots and a process-owned run report. Physical GDEMU
performance/stability, complete Chapter 1 acceptance and any broader room
extension remain separate gates.