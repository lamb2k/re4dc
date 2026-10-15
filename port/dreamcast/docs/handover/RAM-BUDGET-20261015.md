# RAM budget for test 15: main RAM and KOS (lane ramreclaim, 2026-10-15)

Base: test 14 final (t14/rc b1518aa4, play image eb2bc4e4). Lane branch: lane/ramreclaim (local, 2 commits on b1518aa4).
Evidence: `C:\Flycast-Evidence\re4-dreamcast\rambudget-20261015` (cens2 = census runs, strict, sq = knob gates).
All runs are Flycast (JIT unless marked align). No timings in this document; every number is bytes.

## In plain words

- **Where the 16 MB goes.** About 4.2 MB is the program itself and 64 KB is the main stack. The game's own memory
  (sound, Leon, weapons, fixed system work and "heap 4", which holds rooms, enemies and movies) is about 12.1 MB.
  The system's general allocator (KOS) keeps a fixed 192 KB.
- **Code growth costs heap 4, not KOS.** When the program grows, the game's memory shrinks by the same amount (in
  4 KB steps). The 192 KB KOS share stays put, apart from up to 4 KB of rounding noise. Heap 4 has room in normal
  play: about 500 KB free at the tightest scenes sampled. The exception is the cliff cutscene in r100 (s30), which
  is already skipped as a known issue.
- **KOS is the tight one, and it is tight in the village (r101).** r101 keeps about 139 KB of KOS busy the whole
  time: a 64 KB model buffer, 355 small texture records (54 KB) and the records for 16 threads. The fight itself
  adds almost nothing. Most of the KOS use is the room's standing load, not a fight spike.
- **The real margin is tiny.** Test 14, with the 48 KB console allowance held back, leaves 2.8 to 5.3 KB of usable
  KOS in r101, depending on the rounding. Test 13 had only 0.4 to 0.8 KB. That is why "any growth" failed there:
  one new thread record (1.2 KB) or one file open was enough.
- **4 KB of KOS was never usable.** A one-character bug in KOS means the last 4 KB page before the main stack
  can never be handed out. Every "Out of memory. Requested sbrk_base 0x8cff0000" message (on the console and in
  the squeeze runs) was a request for that page. The fix is built behind KOS_SBRK_LAST_PAGE=1, default off. It
  gives +4,096 B exactly where the console runs out, and changes nothing else.
- **The console gap is not proven to be 33 KB.** No allocation happens only on the console. The 33 KB estimate
  compared Flycast's total free memory with one large request on the console; it ignored the unusable page and
  how scattered the free memory was. The real gap is probably a few KB of timing-dependent overlap. Keep the
  48 KB squeeze until one console disc measures it.
- **Budget for test 15.** Recommended: turn on KOS_SBRK_LAST_PAGE, move 16 KB from heap 4 to KOS
  (ARENA_FIT_KOS_BYTES 196,608 to 212,992), and give the lanes 8 KB of new KOS use plus 96 KB of code and static
  growth between them, with the rest held back as margin. Gate KOS on "consumption" (bytes the build uses), which
  does not wobble with the rounding, instead of on the free bytes that are left.

### Reclaim options, ranked (bytes x risk)

| # | Game area | Work it cuts | In plain words | Bytes | Lands in | Risk | Status |
|---|---|---|---|---|---|---|---|
| 1 | Every room | KOS refusing its last page | Lets KOS use the last 4 KB before the main stack | +4,096 | KOS | exact | BUILT, lane/ramreclaim 464aada4 |
| 2 | Every room | Fixed 192 KB KOS share | Moves memory from heap 4 to KOS, 4 KB at a time | +4 KB per step | KOS (from heap 4) | low (s30 heap 4 already short) | knob exists (ARENA_FIT_KOS_BYTES) |
| 3 | Every room | 4 KB rounding noise in the KOS share | Makes the KOS share exact, so code growth never moves it | 0 to 4 KB (noise removed) | KOS/heap 4 | low | proposed |
| 4 | r101 and later rooms | 355 texture records of 153 B, kept in KOS | Keeps the texture records in a compact table instead of KOS | +40..57 KB | KOS | medium (render bookkeeping, exact) | proposed |
| 5 | Every room with native models | 64 KB model buffer in KOS | Makes the model buffer a fixed program buffer | +64 KB KOS, -64 KB heap 4 | KOS (from heap 4) | low code risk; heap 4/s30 decision | proposed |
| 6 | Every room | Thread names and folders kept per thread (512 B each) | Shrinks each thread record from 1,152 B to about 700 B | +~7 KB | KOS/heap 4 | medium (KOS rebuild) | proposed |
| 7 | Look label | 32 KB picture buffer for the look label | Draws the label straight into video memory | +32 KB | heap 4 | low (render only) | proposed (VRAM rule) |
| 8 | Release discs | 64 KB message log in RAM | Keeps a 16 KB log on release discs | +48 KB | heap 4 | low-medium (tools read it) | proposed |
| 9 | Music and voices | Two audio thread stacks, 12 KB and 6 KB | Sizes them to what they use (1.4 KB, 1.1 KB) | +11..14 KB | heap 4 | low-medium (movie/save paths unmeasured) | proposed |
| 10 | Every room | Main stack 64 KB | Halves the main stack (it uses 18 KB) | +32 KB | KOS/heap 4 | medium-high (overflow is silent) | needs a full-play census first |
| 11 | Every room | 18 task stacks of 12 KB | Sizes each task's stack to its use (most use under 1.5 KB) | +~100 KB | heap 4 | medium (per-task census over full play) | proposed |
| 12 | Disc reads | 64 KB disc cache | Halves the file cache | +32 KB | heap 4 | medium (more disc reads) | needs a read-meter A/B |

## The answers

### 1. The 16 MB map at the worst scenes

Release image eb2bc4e4 (sizes from the ELF); arena and heap numbers from the census twin (cens2) and the test 14
full-play twin logs. Every scene shares the same map; only the use inside heap 4 and the KOS reserve changes.

| Region | Addresses (release; twin in the appendix) | Bytes | Notes |
|---|---|---|---|
| System (BIOS, KOS vectors) | 8c000000-8c010000 | 65,536 | not usable |
| Program image | 8c010000-8c41ce98 (_end) | 4,247,192 | .text 2,475,600; .rodata 199,584; .data 186,468; .re4dc_char_data 461,088; .bss 908,664; other 1,572; alignment 14,216 |
| KOS allocations made before the arena | _end + 98,216 | 98,216 | fs_iso9660 caches 65,792; maple DMA 16,384; maple device records 3,720; boot thread records and the crash thread's 4 KB stack; pty and stdio buffers; ~3 KB free |
| Arena: sound | | 393,216 | 374,624 used |
| Arena: core / option / player / weapon | | 1,360,608 / 149,920 / 869,728 / 275,424 | fixed reservations |
| Arena: boot-phase allocations in front of heap 4 | | 1,399,584 | heaps 0-3 are created and destroyed in turn; what each keeps stays here (includes the 18 x 12 KB task stack pool, 221,184) |
| Arena: heap 4 | to the arena top (8cfbee40) | 7,651,104 release (7,544,608 in the census twin, 7,618,336 in the full-play twin) | rooms, enemies, models, movies; 4 KB steps |
| KOS reserve (after the arena) | 8cfbee40-8cff0000 | 201,152 physical; the boot log's "left to KOS" = 199,064 = 196,672 + slack 2,392 (it counts from sbrk; 2,088 B lower in both twin and release) | ARENA_FIT_KOS_BYTES 196,608 + 64; the r101 working set lives here (release value measured by a 30 s boot of eb2bc4e4). All slack and consumption figures here use the log's value |
| Kernel (main thread) stack | 8cff0000-8d000000 | 65,536 | high-water mark 18,112 measured |

Inside the KOS reserve at the r101 fight (census twin, unsqueezed, census peak at room frame 1050):

| Owner | Bytes | Notes |
|---|---|---|
| Native model slab (native_ui.cpp ensure_model_storage) | 65,536 | allocated at the first native model draw, kept for good |
| Streamed texture metadata (texture_package.cpp:300) | 54,315 in 355 blocks | ~153 B each; TEX_KEEP keeps them across rooms (RETIRE_KOS_FLOOR closes down to 64 KB) |
| Game task thread records (thd_create_ex) | 11,520 (10 x 1,152) | the stacks themselves come from the game's pool, not KOS |
| Load indicator, card, file handles, newlib | ~4,100 | 1,664 + 1,152 + 1,056 + small |
| Allocator headers (424 blocks x 8) | ~3,400 | |
| **Total in use** | **~139,000** | headroom left 58,440 at the peak (slack 792) |

How program growth turns into lost bytes (mem.cpp ARENA_FIT): the arena gets
`(room - ARENA_FIT_KOS_BYTES - 64) & ~0xFFF`, where room is everything between the KOS break and the kernel stack.
So:
- Heap 4 loses the growth, rounded to 4 KB steps.
- The KOS reserve is 196,672 B plus a slack of 0 to 4,095 B: `(room - 196,672) mod 4096`. Growth of g bytes takes g
  bytes of slack until the next 4 KB step, which then gives 4 KB back to KOS and takes 4 KB from heap 4. A single
  change can move KOS by up to 4 KB either way. That is the "+256 B fails the fight" effect: the build that crossed
  a step lost its slack.
- Measured: across 26 earlier squeeze runs, fight headroom = left_to_kos - consumption, with consumption fixed per
  build (test 14 final 199,160 - 11,520 = 187,640; census twin of the same source 197,464 - 9,824 = 187,640). Arms
  of one source (W, mW, T) differ by up to 3.2 KB of slack (t14final: 197,144 to 200,312), so the squeeze gate
  measures the twin's slack, not the release's.
- Heap 4 is not the binding side in play. Sampled minimums (test 14 full play, the UI upload samples): fight
  748,640; door103 506,784; r106 513,792; ch21 630,688; boat 866,112. Movies: r100 s03 heap_before 1,040,640 and
  s20 880,768 against a 363,328 B staged need. **r100 s30 already fails** (known issue): heap_before 152,192;
  after evicting motion keys 284,192 free, largest block 40,736 against a 55,296 B piece, so it is about 79 KB
  short in total plus fragmentation. The UI texture staging (55 KB in heap 4) is the blocker the log names.

### 2. KOS census at the fight peak, and fragmentation

The census (KOS_CENSUS=2, lane commit 523ba02c) tracks every malloc, calloc, realloc, memalign, aligned_alloc, free
and operator new by caller, and snapshots the caller table at each new peak in 150-frame windows. Coverage: 424
live blocks, 0 lost; it accounts for the whole KOS reserve use (above).

- **The r101 KOS level is set at room entry, not by the fight.** Fight windows from room frame 150 to 1050 move by
  less than 600 B (live 12,278,113 to 12,278,297 B). The peak that sets each window is a 16 B file handle
  (fs_hnd_open) or a 153 B texture record (open_streamed_impl). The door103 run bottoms out in r101 (61,544 B
  unsqueezed). leave100 and leave103 carry r101's level into the next room's entry (58,656 B).
- **Dynamic KOS requests in play are all small:** texture records 153 B, file handles 16 B plus iso9660 fd 352 B,
  thread records 1,152 B (one per OSCreateThread; the 12 KB stack in "OSCreateThread ... size 12288" comes from the
  game's task pool), newlib Balloc 24-132 B inside printf. The only large KOS request after boot is the 64 KB model
  slab at the first native model draw.
- **The unusable last page.** KOS mm_sbrk refuses `new_base >= _arch_mem_top - THD_KERNEL_STACK_SIZE`, and dlmalloc
  grows the heap in 4 KB steps, so the final page of break room is never handed out. The reported headroom (free
  chunks + break room) therefore overstates usable KOS by 4,096 B. Every OOM in the record is that page:
  "Requested sbrk_base 0x8cff0000, was 0x8cfef000, diff 4096" (uicoll kos-ub: a motion key file open, 5 lines;
  kos-un: "OSCreateThread: thd_create_ex failed"; test 12 at 64 KB; the console previews).
- **Why 4 KB pieces fail when one block passes.** The squeeze's pieces mode holds 12 x 4 KB and frees 12 x 4 KB gaps
  between them. On passing builds pieces cost only 24-88 B more consumption than one block, but they lower the
  largest free block by 700-860 B (test 14 final: top 10,304 block vs 9,440 pieces), because small requests land in
  different holes and the top shrinks. A request that does not fit a hole must come from the top, and the top
  includes the dead page. Test 13 base: top 4,352-4,864 B, so 256-768 B of usable contiguous space. uicoll kos-ub
  passed as a block (top 4,864) and failed as pieces (top 4,512, a 352 B fd or 1,152 B record needed the dead page).
- **Usable margin (largest free block minus the dead page), 48 KB squeeze, r101 fight:**

| Build | left_to_kos | consumption | min top (pieces) | usable now | usable at zero slack |
|---|---|---|---|---|---|
| test 12.2 (kos-122) | 200,136 | 192,296 | 5,696 | 1,600 | -1,864 |
| test 13 (kos-t13) | 199,880 | 192,816 | 4,864 | 768 | -2,440 |
| test 14 final (t14final/kos) | 199,160 | 187,640 | 9,440 | 5,344 | 2,856 |
| census twin, same source (cens2) | 197,464 | 187,640 | 7,744 | 3,648 | 2,856 |
| test 14 release image eb2bc4e4 (its own left_to_kos; top estimated from the twins' hole size) | 199,064 | 187,640 | ~9,340 | ~5,250 | 2,856 |
| knob-on twin rbkW (KOS_SBRK_LAST_PAGE=1: no dead page) | 199,032 | 187,640 | 9,312 | 9,312 | 6,952 |

  "Zero slack" means the KOS reserve at exactly 196,672 B, the worst a code change can leave it. Test 13's negative
  value explains why it passed on Flycast only by rounding luck.

### 3. The console vs Flycast gap

- **The evidence behind 33 KB.** Preview 1: the first radio call could not get 12,248 B on the console, where
  Flycast showed about 45 KB of headroom. Preview 2: 7-8.5 KB minimum headroom in the Flycast r101 fight, and it
  ran out on the console. The earlier lane found no console-only KOS consumer in the code.
- **What those numbers left out (measured here).** Headroom counts the dead page (4 KB) and the holes (1-5 KB in
  these scenes, 5.1 KB in squeezed door103). Preview 1's 12,248 B was a single request that needed one contiguous
  block, and 45 KB of total headroom says nothing about the largest block. Preview 2's 7-8.5 KB was 3-4.5 KB of
  usable space before holes. A console transient of 2-3 KB is then enough to fail.
- **Console-only allocations: none fixed.** The game's VMU code uses its own buffers, not KOS vmufs. Maple device
  records (1,240 B each) are allocated at boot, before the arena, so they cost heap 4, not KOS. Only a device
  reattaching mid-game (a loose VMU or rumble pack) would allocate in the KOS reserve. GD read retries reopen
  files (368 B each, freed on close). No KOS buffer depends on the console.
- **Timing-driven overlap (INFERRED, the likely cause).** Every KOS peak in the census sits at a room-entry
  preload, set by a texture package open. On the console the disc is slower and the game runs at about 71% speed
  in the fight, so thread creation, file opens and preloads overlap differently. That changes both the peak and the
  hole layout (fragmentation order). Expected size: a thread record plus a few handles and printf temporaries,
  about 2-4 KB, rather than 33 KB.
- **Is 48 KB right?** It is conservative and safe to keep, but no measurement supports 33 KB. Replace the guess
  with one console disc: the census twin with the minimum headroom and minimum usable top since boot shown on
  screen (or the VMU PACE page), played once through the r101 fight, call and door103. The squeeze is then set to
  the measured gap plus 8 KB.

### 4. Reclaim options ranked by bytes x risk

See the plain-words table above. Details:

1. **KOS_SBRK_LAST_PAGE=1 (built, exact).** +4,096 B of usable KOS. Only changes behaviour where the stock check would
   already have run out. Gates below.
2. **ARENA_FIT_KOS_BYTES +16,384.** Moves 16 KB from heap 4 to KOS. Heap 4 has about 500 KB free in play; it
   deepens the s30 gap (already failing). Cheapest real KOS headroom.
3. **Exact KOS share (ARENA_FIT step 32 B instead of 4 KB).** Removes the 0-4 KB sawtooth. KOS = reserve + 64 + <32,
   so code growth never moves KOS. Pair with +4 KB of reserve to keep today's average.
4. **Texture metadata out of KOS.** 355 x ~161 B = ~57 KB at r101. A compact per-entry record (key, format, size,
   file offset, ~40 B) in a fixed table, or a heap-4 pool, frees 40-57 KB of KOS. Render bookkeeping only (STRICT
   can gate it).
5. **Model slab to a static buffer.** +64 KB KOS, -64 KB heap 4 (via the arena fit). It is a CPU-written TA packet
   buffer, so it cannot live in VRAM. It also removes the only large KOS request in play, the one most exposed to
   fragmentation.
6. **kthread_t label/pwd 256+256 B.** Shrinking both to 32-64 B saves ~450 B per thread record (16 records at the
   fight: ~7 KB, of which ~4.5 KB is in the KOS reserve). Needs a libkallisti rebuild (shared by every lane).
7. **osd_texture 32 KB static buffer** (native_ui.cpp: the look label is drawn into a 512x32 RGB565 CPU buffer, then
   uploaded): draw in 4 KB slices or straight into its VRAM texture. +32 KB heap 4. Render only.
8. **re4dc_logbuf 64 KB** in release play builds: 16 KB is enough for the crash screen's tail. +48 KB heap 4. The
   twins keep 64 KB, so the gates need to read the release's own value.
9. **Audio stacks:** re4dc-audio 12,288 B static, high-water 1,388 B; re4dc-aica-str 6,144 B, high-water 1,072 B.
   4 KB and 3 KB keep about 3x margin: +11 KB heap 4. The stream thread does disc reads and logs (vfprintf), and
   movies and saves were not measured, so this needs a guard word and a census over those paths first.
10. **Kernel stack 64 KB to 32 KB:** high-water 18,112 B (door103), 18,036 B (leave103), 12,756 B (fight). Boot,
    movies, saves and the crash screen were not measured. A silent overflow would corrupt the KOS top. Only with a
    full-play stack census plus a guard word checked every frame.
11. **Task stack pool:** 18 x 12 KB in the persistent zone. High-water: one slot 10,860 B, two slots 8,612 B, the
    rest 224-1,468 B. Per-task sizing could free about 100 KB of heap 4, but slots map to tasks per scene, so it
    needs a per-task census over full play.
12. **fs_iso9660 cache** (2 x 16 x 2 KB = 64 KB, pre-arena): halving it gives +32 KB heap 4 but may add disc reads,
    which count as gaps under the VRAM rule. A disc read-meter A/B decides.

Not worth it or not applicable:
- KOS default THD_STACK_SIZE (32 KB): no thread in this build uses a KOS-allocated default stack. All game and
  audio threads pass their own stack; only re4crash owns one (4 KB, high-water 636 B).
- The 16 KB purge-all buffer: KOS arch_dcache_purge_all's static buffer is only linked when a purge of 39,936 B or
  more happens; dvd_read_safe.cpp and native_effect.cpp already purge line by line to avoid it. It is not in the
  image's large-symbol list.
- The maple DMA buffer (16 KB, KOS MAPLE_DMA_SIZE): pre-arena, a KOS rebuild, about 8 KB gain, console VMU risk.
- .data/.bss: besides items 7-9, the largest are Snd_seq_work 103,520, the native_ui entries table 100,352
  (initialised .data), re4dc_dvd_buff 131,072 (the source's DVD staging area), Global 34,432, g_entryPath 32,768
  (512 x 64 B paths; a string pool would save ~24 KB), and about 87 KB of coarse-actor palettes and skin streams
  (.data; worth checking whether the PS2 cast still reaches them).

### 5. The budget for test 15

**Currency.** KOS is budgeted as consumption, the bytes a build uses at the r101 fight, leave100 and door103 under
the 48 KB squeeze (4 KB pieces). Consumption = left_to_kos - minimum headroom. It is fixed per build and does not
depend on the slack. Program growth is budgeted as the _end delta of the release play image, which comes out of
heap 4.

**Test 14 baseline:** consumption 187,640 B; usable margin at zero slack 2,856 B (knob off).

**Recommended test 15 setting:** KOS_SBRK_LAST_PAGE=1 (+4,096) and ARENA_FIT_KOS_BYTES=212,992 (+16,384). Usable KOS
margin at zero slack: 2,856 + 4,096 + 16,384 = **23,336 B**. Of that:
- **8,192 B allocated to lanes** (table below);
- **8,192 B unallocated reserve** (later pull-ins, console timing);
- **~6,900 B kept as margin** for transients (thread record + file handles + printf temporaries ~2 KB) and
  fragmentation (pieces vs block ~0.9 KB), plus the unmeasured console gap.

**Program growth (heap 4):** 96 KB for test 15 in total, plus the 16 KB moved to KOS: heap 4 -112 KB. That leaves about
390 KB at the tightest sampled scene (door103) and keeps the r100 s03/s20 movies' staging comfortable. s30 stays a known
issue and gets 112 KB further away. Funding it from reclaims 7-9 (~90 KB) would keep s30 where it is.

**Per-lane split** (paste-ready block below).

**Gate rule (proposed for the release gates):**
1. Every lane reports its _end delta (release recipe arm) and its KOS consumption delta (squeeze twin, fight +
   leave100 + door103, pieces) against the test 14 base (consumption 187,640).
2. A lane over its KOS allowance moves its allocation to heap 4 or a static buffer, or trades with another lane
   through the coordinator.
3. Candidate gate: KOS squeeze 48 KB, 10/10, with the largest free block normalised to zero slack
   (`min_top - (left_to_kos - ARENA_FIT_KOS_BYTES - 64)`) at least 8,192 B with KOS_SBRK_LAST_PAGE=0, or at least
   4,096 B with =1. Read left_to_kos from the release image's own boot log, not only from the twin's.
4. Candidate census twin (KOS_CENSUS=2): report the "kos peak" at_peak_headroom, which catches transients between
   KOS_WATCH samples (uicoll kos-un ran out with 8,592 B at its watch minimum).
5. Heap 4: the sum of the lanes' _end deltas stays within the allowance; full play confirms the r100 s03 and s20
   movies play and reports s30 heap_before; the door103 and r106 sampled minimums stay above 256 KB.

## Paste-ready rows for TEST15-SCOPE.md

```
### RAM budget (lane ramreclaim, RAM-BUDGET-20261015.md)

Base: test 14 (KOS consumption at the r101 fight 187,640 B under the 48 KB squeeze; usable margin 2,856 B at zero slack).
Test 15 setting: KOS_SBRK_LAST_PAGE=1 (+4,096 B, exact; lane/ramreclaim 464aada4) + ARENA_FIT_KOS_BYTES=212,992 (+16,384 B
from heap 4). Gate: consumption delta per lane (squeeze twin: fight, leave100, door103, 4 KB pieces) and _end delta
(release recipe arm).

| Lane | Items | Game area | KOS allowance (consumption delta) | Program growth (_end delta, heap 4) | Notes |
|---|---|---|---|---|---|
| logicwaste | 10 LOGIC_WASTE_MASK | Rooms with enemies/effects | 0 B (credit: -1,152 B per task thread made a direct call) | <= 16 KB | memo tables static, not malloc |
| sh4zam | 11 SKIN_SH4ZAM, shz_mem | Every room | 0 B | <= 16 KB | no runtime allocations |
| t2exact | 2 GC_CENSUS_TRIM, SG_SELECT_LEAN, B5 HOT_COLD_SPLIT | Every room | 0 B | <= 8 KB (trims should be <= 0) | layout: watch I-fill, not RAM |
| ps2cast | 7 PS2_CAST_CH1/BOAT, ACTOR_PALETTE_BANK=40, NATIVE_MODEL_REGISTRY_POOL | ch1-1..2-1 | <= 4,096 B (about 25 resident texture records at r101) | <= 16 KB | packages in heap 4 per room |
| leonlod + worldlod | 4 GANADO_LOD=2, 3 far scenery (C1) packages | Every room / heavy rooms | <= 4,096 B (shared) | <= 16 KB (shared) | each extra resident package = ~161 B of KOS |
| uicoll | 9 HUD quad cache (B3) | Every room | 0 B (its cache goes in heap 4 or static: earlier arms ran out of KOS in the squeeze) | <= 8 KB | |
| poc101 | 8 proof disc | r101 | - | - | not shipped |
| unallocated | | | 8,192 B | 16 KB | coordinator pull-ins |
| margin | | | ~6,900 B | heap 4 keeps ~390 KB at door103 | transients, fragmentation, console gap |
```

## Gate results for KOS_SBRK_LAST_PAGE=1 (lane/ramreclaim 464aada4)

| Gate | Result |
|---|---|
| Knob-off identity | **PASS**: the test 14 release recipe on lane/ramreclaim (out-rrrP) builds image eb2bc4e4, the test 14 final |
| _end delta, knob on | **0 B** on the squeeze twins (rb0W vs rbkW, both 8c428eb8); +32 B on the trace arms (alignment). The patched mm.o replaces libkallisti's |
| KOS squeeze 48 KB, knob on (rbkW, 10 runs) | **PASS 10/10**. Min headroom block / pieces: fight 11,480 / 11,392; call 41,920 / 41,832; door103 18,080 / 17,992; leave100 11,680 / 11,592; leave103 11,680 / 11,592. Consumption 187,640 (= test 14) |
| The gain, A/B at deeper squeezes (fight, one block; same left_to_kos 199,032 in both arms) | knob off: **FAIL** at 56 KB and 57 KB ("Out of memory. Requested sbrk_base 0x8cff0000, was 0x8cfef000, diff 4096", scene end not reached). knob on: **PASS** at both (largest block down to 2,560 and 1,536 B, no OOM). The knob adds at least 4 KB of usable KOS |
| STRICT / decisions, knob off (rr0rT) vs on (rr1rT), stop tick 500, 60 s, trace_lock | **STRICT + MUST-IDENTICAL** in all three: fight 502 ticks (masked 0), r101 bell fight 502 (masked 0), door103 502 (masked 239, as in the test 14 RC). Raw trace lines: bell and door103 byte-identical; fight differs only in the `sq` sound-queue digest on 4 ticks, which STRICT does not compare (code layout timing) |
| Align (hwmodel interpreter, HWTRACE_ALIGN=1, knob-on twin, 150 s caps) | **PASS: 0 MISALIGN** in both runs (hwtrace.log align=1). The fight run reached the crowd alert at the cross; the door103 run reached r103 entry. 0 OOM / MISSING / HALT |

Disk: this lane's staged discs and objdirs are deleted after the gates (manifest in the evidence root).

## Technical appendix

### A. Builds and evidence

| Label | What | _end | Image (objcopy -R .stack) |
|---|---|---|---|
| out-rrrP | test 14 release recipe on lane/ramreclaim 464aada4, knobs off | 8c41ce98 | eb2bc4e4 (= test 14 final: knob-off identity PASS) |
| out-rbdW | census twin: release recipe + DBG_WARP/WARP_JUMP/TEX_CHECK/MCHECK_LEONGC + KOS_WATCH/KOS_SQUEEZE/W11_FIXTURE + KOS_CENSUS=2 | 8c4374d8 | (diagnostic) |
| out-rb0W / out-rbkW | squeeze twins without the census, knob off / KOS_SBRK_LAST_PAGE=1 | 8c428eb8 / 8c428eb8 | cda2440b / 459e14c7 |
| out-rr0rT / out-rr1rT | trace arms (t14-build.sh rT), knob off / on | 8c428938 / 8c428958 | e0b74ffb / e15e5138 |

Evidence root `C:\Flycast-Evidence\re4-dreamcast\rambudget-20261015`:
- `cens2\kos-<scene>-<bytes>-<frag>`: census runs (fight, call, door, leave100, leave103; 0 and 49152 pieces).
  Gate output: KOS SQUEEZE GATE PASS (fight 9,824 / call 40,264 / door 16,424 / leave100 10,024 / leave103 10,024
  squeezed).
- `relboot`: 30 s boot of the release program (eb2bc4e4): arena fit 12,099,584, 199,064 left to KOS.
- `strict\`, `sqk\`, `sqab\`, `align\`: knob gates (section I).
- `cens\`: the first attempt (rbcW). Its stack paint overwrote the source task stacks' 0xDEADBABE guard word and
  every run stopped in scheduler.cpp StackOverflowCheck right after the warp; superseded by cens2. The fixed paint
  starts 32 B above each stack base.

### B. Address map, census twin and release

| | census twin (rbdW) | release (eb2bc4e4) |
|---|---|---|
| _end | 8c4374d8 | 8c41ce98 |
| arena | 8c44f480-8cfbf480 (11,993,088) | 8c434e40-8cfbee40 (12,099,584) |
| pre-arena KOS (arena_lo - _end) | 98,216 | 98,216 |
| sound / core / option / player / weapon | 393,216 / 1,360,608 / 149,920 / 869,728 / 275,424 | same |
| game heap start | 8c737a40 | 8c71d400 |
| MemCreateHeap 0 / 1 / 2 / 3 / 4 | 8c737ae0 / 8c7d63a0 / 8c862f40 / 8c88d360 / 8c88d560 | +(-0x1a640) |
| persistent zone (heap start to heap 4) | 1,399,584 (phase 0 keeps 649,920, phase 1 576,416, phase 2 173,088, phase 3 512) | same |
| heap 4 | 7,544,608 | 7,651,104 |
| left_to_kos (reserve + 64 + slack) | 197,464 (slack 792) | 199,064 (slack 2,392) |
| kernel stack | 8cff0000-8d000000 | same |

Task stack pool: 18 stacks of 12,288 B at 8c737b80 + n x 0x3000 (twin addresses), in the phase-0 zone. Other stacks:
re4dc-audio 12,288 (.bss g_thread_stack), re4dc-aica-str 6,144 (.bss g_strStack), re4crash 4,096 (KOS-owned,
pre-arena), leon-hands 6,144 (heap 4), [idle]/[reaper] 512 each (KOS static).

### C. KOS census, r101 fight peak (cens2 kos-fight-0-0, window ending room frame 1050)

Window header: live 12,229,145 B in 424 blocks, 27 callers, at_peak_headroom 58,440 (free 1,096 + break 57,344), largest
block 57,904, the peak set by fs_hnd_open (16 B).

| Caller (resolved against out-rbdW) | Blocks | Bytes | Where |
|---|---|---|---|
| re4dc_mem_init (mem.cpp:103), the arena | 1 | 11,993,088 | arena |
| fs_iso9660_init (kosfix fs_iso9660.c:1276), data + inode caches | 1 | 65,536 | pre-arena |
| ensure_model_storage (native_ui.cpp:5644), native model slab | 1 | 65,536 | KOS reserve |
| Package::open_streamed_impl (texture_package.cpp:300), streamed texture metadata | 355 | 54,315 (max 153) | KOS reserve |
| thd_create_ex (thread.c:428), kthread_t records | 16 | 18,432 (1,152 each) | 6 pre-arena, 10 reserve |
| maple_hw_init (maple_init_shutdown.c:133), maple DMA buffer | 1 | 16,384 | pre-arena |
| thd_create_ex (thread.c:437), re4crash's own stack | 1 | 4,096 | pre-arena |
| maple_driver_attach (maple_driver.c:88), device records | 3 | 3,720 | pre-arena |
| re4dc_loadind_boot (load_indicator.cpp:104) | 1 | 1,664 | KOS reserve |
| card.cpp:484 join() | 1 | 1,152 | KOS reserve |
| fs_pty_create (fs_pty.c:132/138) | 2 | 2,160 | pre-arena |
| iso_open (kosfix fs_iso9660.c:643), open file records | 3 | 1,056 | KOS reserve |
| _smakebuf_r (newlib stdio buffer) | 1 | 1,024 | pre-arena |
| fs_iso9660_init:1277 (cache headers) | 1 | 256 | pre-arena |
| vblank_handler_add, snd_mem_malloc, newlib Balloc, fs_hnd_open, fs_ramdisk, tls, maple attach | 31 | ~700 | mixed |

Squeezed (49152 pieces) the same window adds the 12 squeeze pieces (49,152) and leaves at_peak_headroom 9,440, largest
block 7,744. Door103 squeezed: the deepest point is r101 frames 1-150 (359 texture records, 13 thread records):
at_peak_headroom 12,480, largest 11,136, 3.9 KB below the KOS_WATCH minimum (16,424) because the watch samples miss it.

Scene minimums (cens2; watch / census peak headroom):

| Scene | Unsqueezed | 48 KB pieces | Largest block (pieces) |
|---|---|---|---|
| fight | 58,824 / 58,440 | 9,824 / 9,440 | 7,744 |
| call (r100) | 89,280 / 99,152 | 40,264 / 50,040 | 38,976 |
| door103 | 65,504 / 61,544 | 16,424 / 12,480 | 14,240 (11,136 at the peak) |
| leave100 | 59,040 / 58,656 | 10,024 / 9,640 | 8,160 |
| leave103 | 59,040 / 58,656 | 10,024 / 9,640 | 8,160 |

### D. KOS consumption across builds (r101 fight, 48 KB squeeze)

Consumption = left_to_kos - minimum watch headroom. Block (frag 0) and pieces (frag 1):

| Evidence | left_to_kos | block | pieces | min top block / pieces | OOM lines (pieces) |
|---|---|---|---|---|---|
| t11crash kos-t12 (test 12) | 200,488 | 192,272 | 192,296 | 6,816 / 6,048 | 0 |
| t11crash kos-122 (12.2) | 200,136 | 192,272 | 192,296 | 6,464 / 5,696 | 0 |
| t13rc kos-t13 (test 13) | 199,880 | 192,792 | 192,816 | 5,632 / 4,864 | 0 |
| t13rc kos-t13m | 199,368 | 192,792 | 192,816 | 5,120 / 4,352 | 0 |
| uicoll kos-ub (t13 + arm) | 199,112 | 192,792 | 192,616 | 4,864 / 4,512 | 5 (motion key file open) |
| uicoll kos-un | 198,088 | 192,008 | 189,496 | 4,480 / 6,496 | 1 (OSCreateThread) |
| sh4zam kos-sz | 198,632 | 192,472 | 192,512 | 4,544 / 4,192 | 0 |
| t14rc kos-t14 (intermediate) | 198,392 | 190,592 | 190,680 | 6,496 / 5,632 | 0 |
| t14final kos (test 14 final) | 199,160 | 187,552 | 187,640 | 10,304 / 9,440 | 0 |
| rambudget cens2 (same source + census) | 197,464 | - | 187,640 | - / 7,744 | 0 |

The sh4zam lane's "fight headroom 6,160" next to the intermediate's 7,712 was slack, not SH4ZAM: its consumption
(192,512) was the test 13 level. The uicoll kos-un row ran out with 8,592 B of watch headroom: a thread-record
transient between samples.

### E. Thread stacks (KOS_CENSUS=2 high-water marks, all five scenes, unsqueezed)

| Thread | Stack | Size | High-water (max over scenes) | Ratio |
|---|---|---|---|---|
| [kernel] main thread | 8cff0000 | 65,536 | 18,112 (door103); 18,036 leave103; 12,756 fight | 3.6x |
| re4dc-audio | .bss | 12,288 | 1,388 | 8.9x |
| re4dc-aica-str | .bss | 6,144 | 1,072 | 5.7x |
| re4crash (KOS-owned) | pre-arena | 4,096 | 636 (no crash exercised) | 6.4x |
| re4-task slot 8c737b80 | pool | 12,288 | 10,860 | 1.1x |
| re4-task slots 8c740b80, 8c743b80 | pool | 12,288 | 8,612 | 1.4x |
| re4-task, other 8 slots seen | pool | 12,288 | 224-1,468 | 8-55x |
| [idle], [reaper] | static | 512 | not painted (stack pointer within 512 B of the base) | - |

High-water marks count only use after the first report (room frame 1 of the first room). Boot, title, movies, saves,
the sub screen and the crash screen were not measured. The call scene produced no report after the paint (the room
frame counter does not advance while the sub screen is open).

### F. KOS mm_sbrk and the last page

kernel/mm/mm.c (KOS 804b319, /root/work/kos-re4dc-d367): `if(new_base >= (_arch_mem_top - THD_KERNEL_STACK_SIZE))`
refuses. dlmalloc extends the top by page-multiple requests ("diff 4096"), the break sits at 8cfef000 when the
reserve is nearly used, and the only remaining request, to 8cff0000, equals the limit and is refused. re4dc_kos_heap_state
counts `limit - brk` as break room, so KOS_WATCH headroom and the squeeze gate's floor (min headroom >= 4,096) both
include the page. KOS_SBRK_LAST_PAGE=1 links patches/kos-804b319-mm-sbrk-last-page.patch's mm.c ahead of
libkallisti (objdump: stock `cmp/hi r4,r1`, patched `cmp/hs r4,r1`).

### G. The arena fit (mem.cpp, ARENA_FIT=1)

`room = (limit - sbrk(0)) + mallinfo().keepcost; fit = (room - (ARENA_FIT_KOS_BYTES + 64)) & ~0xFFF`, and the arena
is memalign(32, fit). KOS keeps `room - fit` = 196,672 + ((room - 196,672) mod 4096). The pre-arena KOS use (98,216 B)
does not depend on the image, so the slack is a function of _end mod 4096 only: release 2,392, census twin 792, the
t14final arms 472 to 3,640.

### H. s30 (r100 cliff movie), test 14 full play (fullplay-20261015\t14ffp-154950\h2)

- s03: heap_before 1,040,640, staged 363,328, plays. s20: heap_before 880,768, plays.
- s30: "route movie heap: preflight need=55296 ... evicted=13 motion keys (193056 B) short free=284192
  largest=40736"; "alloc[d800]:free[45400] native UI texture staging"; "terminal=3 id=10030 frames=0/340
  heap_before=152192"; kos_free 11,664 at the retire.
- Heap 4 free map at the failure: native UI texture staging blocks (55,360 and 65,600 B) split the free space into
  27,040 / 35,392 / 15,840 / 22,432 B holes.

### I. KOS_SBRK_LAST_PAGE=1 gates (evidence)

- Identity: out-rrrP (t14-build.sh rP, LP=rr) objcopy image eb2bc4e4e6c40b56..., = test14/release-knobs.txt image-sha256.
- Squeeze: `sqk\kos-<scene>-49152-<0|1>`, base `_discs\sqk` (rbkW), output `sqk-gate.txt`.
- A/B: `sqab0` (rb0W, knob off) and `sqab1` (rbkW, knob on), levels 57344:0 and 58368:0, fight; outputs `sqab0.txt`,
  `sqab1.txt`.
- STRICT: `strict\<fight|bell|door>-<t0|t1>` (bases `_discs\t0` = rr0rT, `_discs\t1` = rr1rT; fixtures kos-fight-warp,
  bell-trg-warp, door103-warp; RE4DC_LOG_STOP_TICK=500); verdicts in `strict\*-raw.txt`, `*-dcmp.txt`.
- Align: `align\<fight|door>` (hwtrace.log), `align-summary.txt`.
- Release boot: `relboot\run-output.txt` (eb2bc4e4: arena fit 12,099,584, 199,064 left to KOS).
