# Arena23 defensive console experiment

Base: `64a28a7bdc44312924b14414501b7d4ff1d2d032` (`origin/t15/int`, fetched 2026-10-22).
Worktree: `/root/probe/codex-arena23`, branch `codex/arena23`.

## Implemented experiment

`VRAM_ROOM_ARENA_NO_TOP=1` requires `VRAM_ROOM_ARENA=1 VRAM_PAGES=1 UI_VRAM=1`.
It replaces only class 2 top placement with best-fit placement ending at or below
`0xa47f2000`. Glyph atlas, overlay slab and core-key allocations therefore cannot
occupy `[0xa47f2000,0xa4800000)`, the final 57,344 bytes of VRAM. There is no high
fallback. The real extent remains intact, so class 0 dynamic and class 1 room
allocations can still use the tail. Room first-fit placement and room retirement
are unchanged. Texture assets, package formats, uploads and gameplay are unchanged.
The knob defaults to 0, and no recipe enables it.

This changes runtime texture placement and can change fragmentation/lifetimes.
It does not preserve the failing layout when enabled. It is an experiment, not a
proven repair of the console fault or proof that residency gains survive.

## Evidence completed

- `tools/d367/test_arena23_allocator.py` compiles the real allocator with stubbed
  platform/interrupt declarations and simulated VRAM addresses. Four combinations
  (NO_TOP 0/1 x VQ_ONLY 0/1) pass placement, hard-cutoff exhaustion, preserved tail
  access for dynamic/room users, and twenty room-turnover/coalescence cycles.
  It never dereferences simulated texture RAM. This is host evidence only.
- Sequential SH-4 object compile, GCC 15.2, pinned KOS
  `/root/work/kos-re4dc-d336`, `-O2 -g0`, page allocator, VQ-only and arena enabled.
  Base and explicit NO_TOP=0 raw objects are identical: 7,088 bytes,
  SHA256 `9eb1370595a539dc9d5692d98452aa3383e1465e65bcdaa058598609928547b6`.
  NO_TOP=1: 6,968 bytes,
  SHA256 `2c592534194c5acd7c29b25128c80618f643857c1fb8e47783c94bd2bf4dbcec`.
  Allocatable text 2,115 -> 2,043 bytes; BSS unchanged at 6,181 bytes.
  Exact commands/results are private in `arena23-object-check-02/` and the lane
  `check-objects.py`. Debug-bearing objects first differed because line/path
  tables changed; their instruction/relocation disassembly matched. The `-g0`
  comparison above is the decisive raw-object identity check, not linked identity.
- No full build, link, guest or disc was run in this source allocation.

## Cache investigation

`modules.cpp` writes/relocates the image, writes back D cache, then calls
`icache_flush_range` at load and release. `subscreen_backing.cpp` also writes back
D cache before that call. In the pinned KOS, `icache_flush_range` is a deprecated
inline alias for `icache_sync_range`, which calls `arch_icache_sync_range`, not
`arch_icache_inval_range`. Its P2 routine writes back each D line with `ocbwb`
and writes `(address & 0xfffffc00)` to the I-cache array at
`0xf0000000 | (address & 0x1fe0)`, while interrupts are disabled. Neither this
store value nor its target is the observed `0x0c8a8001`: its low valid bit is clear,
and the destination is P4, not overlay RAM. That does not rule out a hardware
interaction, stale data or corruption elsewhere. It does mean the cache-tag-shaped
word is a clue, not proof that this correct-looking routine wrote it into RAM.

No cache code was changed. Replacing instruction sync with a D-cache purge alone
would omit the stale-I-line invalidation contract and is not an accepted fix.
A later separate, default-off diagnostic may hash overlay code through cached and
uncached aliases immediately before/after code sync and compare the known literal
at each step. Such an experiment changes layout and cannot itself prove repair.
Any module/cache mutation requires coordinated ownership; KOS remains untouched.

## Later controlled gate and package plan (not allocated or executed)

1. Freeze exact current QA programme, recipe/data mip22b, source, KOS/toolchain,
   ELF/raw/overlay hashes and overlay load addresses. Gate 48 KiB KOS and r100 s30
   heap 4. Run TEXCHK 26/26 against the final assets.
2. Separately retain original failing B/B3 source/programme/layout and its existing
   artifacts. Pair original arena-on failing control and NO_TOP experiment, with
   equal diagnostics. Record main/overlay sizes, addresses, hashes and every padding
   or layout difference. A new QA-layout pass is not a B-layout pass. Enabled
   allocator size changes (-72 text bytes in the focused object) are already known.
3. Check r101/r100/r117 re-entry with arena on and NO_TOP 0/1, requiring zero VRAM
   FAILS and zero no-contiguous events; report pinned/dynamic/free/largest extents,
   reloads, and whether glyph/slab/core addresses stay below the cutoff.
4. User runs both controlled B-layout and QA discs on physical Dreamcast. Flycast
   console mode checks route/regression behavior only; it cannot accept this
   hardware-only, layout-sensitive crash repair.
5. Only after root programme/gate allocation, prepare the private folder
   `C:\Game Dev\Emulators\RE4DC-QA23-Arena-<sha>` with gdemu, README, exact source,
   knobs, data, pending physical gates and SHA256SUMS using gdemu/ prefixes.

Resource proposal: current sparse source is about 50.3 MB. Source/host/target-object
allocation stays below 256 MiB. A future full build should request up to 2 GiB for
objects/ELF/overlays and one standard GDEMU package at 1,188,056,400 bytes (prior
layout: track01 1,058,400 + track02 1,237,152 + track03 1,185,760,800); final sizes
must be measured. Keep one staging tree cap of 1.2 GB and at most two retained discs
(about 2.38 GB); this is a later peak proposal, not current allocation. Admission
requires fresh C free >= 19,394,461,696 + 1,073,741,824 peer bytes + the approved
actual peak, one nonblocking shared build slot/per-tree lease, jobs <=4, and
release priority. Do not overwrite original controls, peer data or existing discs.

## Reused diagnostics and narrow repairs

The following missing diagnostics were applied from `origin/wip/mipfault22`,
without importing any old recipe or private data:

- `f0cacf59e81f903b2f719a53cf52aa0ff04e68fd`: OVL_GUARD modes 1/2.
- `1ad4de95c674b3819dcfd3f9552958592f923809`: ARENA_RING, OVL_GUARD=3,
  LOG_TRIM, associated crash/module/memory/native-ui/VRAM diagnostics.
- `f0188ffb0e9b241ba35f2c0856cd1ff2f3ee2a51`: HDR_ALIGN_PROBE.
- Only `native_ui.cpp` from `8459e76b634e237d7db528298b2ce345849a577e`:
  corrected probe newline/caller. The unrelated `tools/link.sh` debug-ELF copy
  was deliberately excluded. There is no new linker/artifact behavior.

Two confirmed diagnostic guard defects were repaired: the crash-screen ring
function declaration now depends on ARENA_RING itself, and a ring allocation
records class 0 when the arena is disabled. Thus independent ARENA_RING=1 with
CRASH_OVL_LINE=0 and with VRAM_ROOM_ARENA=0 can compile for a controlled arena-off
comparison. All imported diagnostics still default to 0.

SH-4 objects compiled sequentially under nonblocking shared/per-tree leases:
base vs diagnostics-off raw objects are identical for `vram_pages`, `modules`,
`mem`, `crash_screen`, and `native_ui` in their stated focused configurations.
`vram_pages` ring-on with arena off and with arena+NO_TOP on, crash-screen ring-on
without CRASH_OVL_LINE, modules OVL_GUARD=3 with route/stage overlays, and native UI
HDR_ALIGN_PROBE with TEX_MIP_DADJ=3 all compile. These are focused object checks,
not an integrated programme, linked off-identity, full recipe or guest gate.
Initial direct compiles omitted normal build-provided native-UI screen/stream
macros and the crash GD format header; the retained logs show those setup errors
and the final commands include them. No production file was changed for setup.

The cache experiment must remain independent of WORLD_SCRATCH or any changed
cache/renderer mode: preserve original relevant settings in the B comparison.
Combining them could mask the hardware fault. Root cause is still open; the
next coordinated code step is a cached/uncached pre/post-sync hash diagnostic
only if the placement experiment and physical B-layout evidence require it.
