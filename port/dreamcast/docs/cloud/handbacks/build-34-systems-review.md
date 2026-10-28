# Build 34: six systems switches reviewed on 2026-10-28

Audit baseline: `36643bf8ab5a78c581274f28eca702ae8aa48330` on `codex/offknob-review-20261028`. Repository paths below are relative to its root. Commit dates are the recorded author dates, including their original UTC offset. Historical timing and emulator receipts are not physical-console results. A default-zero introduction is not described as an enable-then-disable event unless recipe history establishes one.

## Decisions

| Switch | Historical status and reason | Recommendation | Remaining owner gate |
| --- | --- | --- | --- |
| `FRONT_TEXOBJ` | Introduced off and explicitly not promoted. Historical render comparison passed and its touched-function model saved about 0.45 ms, inside frame noise. No recipe enable/removal found. Current cache key can return stale descriptor words; an actual-source host probe demonstrates this contract gap. | **Enable after fix and qualification.** The Build 34 implementation plan includes descriptor validation under the existing switch; implementation is the next step, not part of this audit receipt. | Exact GX words/wrap/tail/swap regressions, target OFF identity and ON link, then current-recipe STRICT/look/performance qualification including same-room texture reuse and menu/movie/weapon lifecycle. Do not enable automatically after host tests. |
| `GAME_HF_ASM` | Explicit historical measured rejection: G29.76 ms versus control29.17 ms. Now mutually exclusive with the enabled, later `GAME_HF_REG` optimization. | **Park.** | Only revisit if a current same-input target cost and route comparison beats the register sampler; check output, history, return and discrete decisions. |
| `GAME_TRIG_FSCA` | Introduced as a retained negative experiment. Global approximate `sincosf` changed line-query and enemy-collision decisions in the documented fight gate. | **Park.** | A revised caller boundary would need a fresh discrete-decision/STRICT gate. Numerical error bounds and a render-only FSCA success do not qualify this global switch. |
| `MOTION_PRESSURE_GROW` | Introduced off as one of three pressure alternatives; no accepted recipe enable/removal found. It relaxes the heap-key cap when an absolute free-byte margin survives. The release adopted a bounded cold-pool/reserve policy instead. | **Park.** | Demonstrate a remaining cap-induced miss problem on the current backing/packing/capacity policy, then qualify the selected byte margin against required allocations, fragmentation, movie/menu pressure and STRICT. |
| `MOTION_RESUME` | Held out in the explicitly documented Test22 item3 bundle after ch21/r117 thrash failures. Off and items5+6-only passed. This is a **bundle attribution**, not proof that resume alone caused the failure. | **Park pending isolated qualification.** | First isolate resume0/1 with the other three item3 switches off; then repeat the failing route and combinations. Existing loader/allocator host checks do not clear the bundle regression or full-program/console gates. |
| `STORAGE_BOUNCE_ALIGNED` | Briefly enabled in a plain-read recipe, then removed when user optionA selected stream-first reads with latched fallback. No standalone bounce correctness failure is documented. It explicitly requires `DISC_READ_FALLBACK=2`, while release uses3. | **Park for the current release profile.** | If plain mode is reconsidered, compare aligned0/1 with fallback2 and all data/window options fixed; qualify bytes, read commands, weak-drive and console behavior. Do not widen the fallback guard. |

## FRONT_TEXOBJ

### Behavior and current source evidence

`port/dreamcast/game/records30.mk` declares `FRONT_TEXOBJ ?= 0` and emits its value through the generated records header for `src/game/trans.o`. The implementation is inside the existing `RE4DC_FRONT_NATIVE`/SH-4 path, with its own `#if RE4DC_FRONT_TEXOBJ` block in `src/game/trans.cpp` (`FtRec`, `FtKey`, `ftLookup`, `frontTexInit`, `frontTexObj`, `frontTexFlush`).

It stores the four meaningful GX texture-object words in 16-byte records, with 32 keys and 512 records. Texture swaps remain a per-model sequential index remap. It materializes eight-word GX objects only for source/other readers or when a smaller new set must preserve the preceding tail. A room change or capacity exhaustion flushes and resets the cache. Counts outside1..248 and out-of-set swaps use the source path. It adds approximately8.7 KiB of target static storage, not an archive allocation.

The existing hit key compares the primary and added TPL pointers, total descriptor count, negative-flags wrap mode, and **only descriptor0's data pointer**. It does not compare the remaining data pointers or any dimensions, format, wraps, or mip-flag relation. Source texture data is relocated/reassigned in `src/game/model.cpp` (`tpl_addr`, `pAddTpl` assignments and texture-header data adjustments around lines1353,1364,1538,1657,1679,1705,2030). Those paths establish why pointer identity is not an adequate lifetime certificate; this audit has not established which private route, if any, exercises a stale cache entry.

The exact-source host probe in `the temporary extracted-production probe (the permanent fixture follows in step 2)` extracts the production `FtRec` through `ftLookup` implementation. It demonstrates both stale cases without changing production:

1. Keeping all lookup-key fields fixed, changing descriptor1 data `0x2000 -> 0x3000` and width64->128 returns the old data and64x64 words as a hit.
2. Keeping descriptor0's data pointer fixed and changing its height likewise returns the old dimension word.

The source also writes `wrapS=wrapT=1` for wrap models, so a fix must preserve that mutation, including on cache hits; merely comparing effective forced-wrap words is insufficient. Shared `pAddTpl` headers must also be validated even when primary TPL pointers differ. The cache's current `ft_cur`, remap, tail, flush and reset semantics must remain intact.

### History

- Introduction: `58d405e9b4536544f259ca244230170ca5aa162d`, **2026-09-23T21:38:16-04:00**, “d367: FRONT_TEXOBJ per-room texture-object cache (records R1)”. Its commit body explicitly says default off and not yet in the canonical recipe. It reports `FRONT_NATIVE=2` zero mismatches over882,607 parts, zero framebuffer pixels different, logic STRICT, and about0.45 ms less modeled touched-function time, within frame noise.
- `port/dreamcast/docs/D367_HANDOVER.md` records R1 as landed/not in recipe; the historical canonical fixture did not reach gameplay because of VMU/title blockers, while listed gates used the bmk2 route. These are historical qualifications, not a current-release run.
- Later guarded call-site composition: `e5c69413cd9e73c4cdfbaf833e81883cdc7e52b5`, **2026-10-17T10:09:34-04:00**, PROP_GATE integration. This is not an off-toggle.
- No accepted release-recipe enable followed by disable was found in the searched tracked history. The correct classification is **off from introduction/not promoted**, followed by a newly demonstrated cache validation gap.

### Approved next work and gate

The Build 34 implementation plan includes a fix in `src/game/trans.cpp` only, inside the existing switch: validate all four packed descriptor words on hits, preserve source wrap writes, rebuild/refresh on mismatch without corrupting symbolic prior objects, and exercise shared added-TPL aliases, same pointer reuse, counts/tails, swaps and resets. New actual-source fixtures belong in `port/dreamcast/tools/cloud/build34/front_*`; bounded target cost should price validation rather than inherit the old0.45 ms claim. The final hand-back will contain whole-TU target checks and final handback commands. Promotion still requires current STRICT, image comparison and net target benefit.

## GAME_HF_ASM

### Behavior and prerequisites

`port/dreamcast/game/game30.mk` declares `GAME_HF_ASM ?= 0`, requires `GAME_HERMITE_FAST` for nonzero, compiles existing `platform/hf_sh4.S`, and defines `RE4DC_HF_ASM` for motion. `GAME_HF_REG` explicitly rejects a nonzero assembly setting. The release's register sampler therefore cannot remain enabled in an assembly comparison.

`src/game/motion.cpp` (`hermiteSelected`, around1907–2016) admits only Hermite types0,5,6 with even key alignment. Unsupported layouts call `hermiteFast`. The assembly restores the original output/history on cold exits before the C fallback, preserving invalid-history and exhausted-search behavior. `GAME_HF_ASM=2` runs boundary self-tests and compares output words, histories and return values on live calls, trapping on mismatch. The existing assembly is not a proposed new implementation.

### History and evidence

- First public-tree appearance found: `4fb68a886eed27058d3284c8baa7ab21b8f956d5`, **2026-09-28T18:43:47-04:00**, bulk r10–r19 playability integration. This establishes a repository introduction date; it does not establish the earlier local authoring date of the imported assembly.
- `7def9b3846fd271bb4920c00c80f224f2d15d574`, **2026-09-28T18:52:01-04:00**, subsequent r21 recipe explicitly selects `GAME_HF_ASM=0` in `port/dreamcast/tools/d367/build-r21.sh`.
- `port/dreamcast/docs/D367_PLAY_BUILD_CHECKLIST.md`, evening2026-09-29 sweep around line876, records measured-and-dropped `MOTION_LEASE_LEAN / GAME_HF_ASM` with G29.18/29.76 versus control29.17 ms. The latter is the assembly result; it is not a0.01 ms win. This review uses the recorded comparison, not a newly rerun target or physical-console receipt.
- Replacement register implementation: `a5013baf887843772747873181464f485eb72506`, **2026-10-05T08:36:00-04:00**. It adds `GAME_HF_REG`, keeps common layouts in compiler-visible constant-stride/register code, preserves fallbacks, and documents modeled Hermite savings plus correctness gates. `port/dreamcast/docs/cloud/BUILD8_ANIM_SAMPLE_LEAN_20261024.md` also classifies assembly among earlier measured/dropped work.

### Recommendation and owner gate

**Park.** There is an explicit negative performance result and a later enabled alternative. A future comparison must use current production source and compare `GAME_HF_REG=1 GAME_HF_ASM=0` against `GAME_HF_REG=0 GAME_HF_ASM=1`, with a separate assembly check2 run. Preserve the other animation settings and test supported/misaligned/unsupported/cold cases, current motion routes and STRICT. Any claimed gain must include replacing the enabled sampler, not just comparing against an older unoptimized C path.

## GAME_TRIG_FSCA

### Behavior and prerequisites

`port/dreamcast/game/game30.mk` defaults it to0 and requires `GAME_TRIG_LEAN=1` plus `GAME_SINCOS=1`. The global switch replaces `re4dc_sincosf` in `port/dreamcast/game/game30_trig.c`; standalone `sinf` and `cosf` remain exact. `platform/include/re4dc_fsca.h` supplies FSCA with residual correction. Small arguments retain exact tiny behavior, the direct interval extends through2pi, the supported larger interval uses exact reduction, and large/non-finite values retain the exact path.

`GAME_TRIG_FSCA=2` runs the exact implementation beside each call and reports difference bins, **but returns the approximate result**. It is an observation build, not a safe reference mode. The global callers include rotation-matrix paths used by collision. Make also rejects composition with `SH4_APPROX_LOGIC` and with a non-render-only global `GAME_SH4ZAM` override; the release's render-only SH4ZAM setting is a separate matter.

### History and documented failure

- Introduction: `90e6341c15dc08c6b4a26e75665f78112a24847e`, **2026-10-05T15:46:07-04:00**, the GAME_ROT_FSCA lane commit. The global experiment remains off as a recorded negative result; the accepted render narrower path must not be conflated with it.
- `port/dreamcast/docs/lanes/fm-20261005.md` records fm-cT3 modeled function savings of about0.325 ms draw/0.293 ms skip. More importantly, fm-pfA/fm-pfT3 failed the discrete gate: line-query differences over245 ticks beginning2003, enemy-collision differences at tick3009, and enemy drift up to5.8 units (player0.047). Its explanation traces last-bit differences through collision-fed matrix operations. The negative result remains meaningful even though numerical error is small.
- Conflict guards added by `875ae9824cc7940fc072be2b1fb55a0ff35dbcc1` (**2026-10-15T09:09:55-04:00**, SH4 approximation) and `3db050b060b18cf5b2cddfb8bdfb1b0a7605bb96` (**2026-10-15T12:56:07-04:00**, SH4ZAM).
- No accepted release enable/removal found. The documented reason is **failed decision qualification**, not missing hardware support.

### Recommendation and owner gate

**Park.** Keep the narrower qualified render option distinct. Numerical testing is available through:

```sh
bash port/dreamcast/tools/game30/trig_fsca_check.sh "$PWD" /absolute/path/to/fsca-table.h -O2
```

The table is an external FSCA table (the script names Flycast's `core/hw/sh4/fsca-table.h`); it is not provided by this repository. The test sweeps all2^32 float words and is not a short gate. Passing it cannot overturn the recorded source-decision failure. A revised caller restriction would need current LOGIC_TRACE/GAME_DECISION_TRACE comparison across the known failure ticks plus full STRICT routes and visual checks. No new assembly is proposed.

## MOTION_PRESSURE_GROW

### Exact policy

`port/dreamcast/game/game30.mk` declares a default0 **byte-margin parameter**, not a boolean. It requires the existing `MOTION_PRESSURE_BYTES` policy. `port/dreamcast/game/platform/native_motion.cpp::pressure_room_for` normally evicts unpinned LRU keys until the global payload cap can admit the requested clip. With nonzero growth, it stops that cap eviction early if `re4dc_static_heap_free() >= bytes + MOTION_PRESSURE_GROW`.

This changes cache residency and memory-pressure policy; it does not change FCV decoding. The decision uses current total heap-free bytes, not a largest-contiguous-region certificate or a reservation for future required allocations. Normal allocation/OOM/movie paths still have their own behavior. With `MOTION_PRESSURE_BACKING=1`, the cap counts heap-backed keys and excludes already allocated reserved slabs. The release has subsequently gained backing, reserve packing, cold-pool/spill and capacity policies, so a2026-10-15 workload cannot be assumed to represent today's cap pressure.

### History

- Introduction: `c7d07c065449627bf0e12ca409bd3aac9ab08fbe`, **2026-10-15T10:19:25-04:00**. The commit describes option1 of3 for coordinator evaluation; it cites farm em12 churn near80 key loads/sec under the256 KiB cap. Make comments also mention an associated console wait report, but there is no isolated accepted GROW benefit receipt here.
- Chosen recipe alternative: `c9dc83eda265658e106e5a0c0296cb9a31a1bbbc`, **2026-10-15T11:17:36-04:00**, explicitly adds `MOTION_COLD_POOL=262144` with the res14r3 data set in the Test14 recipe.
- `port/dreamcast/tools/d367/boss21/MOTION_PRESSURE_REPAIR.md` retains the global262,144-byte reclaimable heap-key cap in the backing repair. `port/dreamcast/docs/CASTLE_SHARED_CACHE_ACCEPTANCE_20261020.md` explains the bounded memory contract. Current recipe values retain GROW0 with cold pool262144/spill524288 and capacity support.
- No tracked accepted GROW enable/removal was found. **Off from introduction/unselected alternative** is the supported history; “disabled after an OOM” would be invented.

### Recommendation and owner gate

**Park.** First collect `MOTION_STATS_LOG=1 MOTION_MISS_LOG=1 DISC_READ_METER=1` on the current release and establish that the strict cap still causes avoidable demand reads after its newer storage policy. If so, specify the intended byte margin explicitly; do not treat GROW1 as a meaningful boolean enable. Compare GROW0 against that exact margin with all other knobs/data fixed. Require multi-enemy/co-bound archive and castle pressure, movie staging, menu suspension, room retirement, required allocation success, free/largest-region evidence, no live-pin violation, and STRICT. Host motion-pressure tests can check implementation invariants, but do not measure the owner’s real workload benefit.

## MOTION_RESUME

### Behavior and existing validation

`port/dreamcast/game/game30.mk` permits only0/1 and requires `MOTION_PRESSURE_BACKING=1`, `MOVIE_HEAP_EVICT=1`, and `ROUTE_MOVIES=1`. It affects `platform/native_motion.cpp`, `platform/native_movie.cpp`, `route_movie_bridge.cpp`, and the existing `platform/motion_resume_journal.hpp`.

The journal records successful source acquires in the current/previous frame, intersects them with actual movie-owned heap-key evictions, and carries binding generations. Native movie finish only queues metadata. Restoration occurs after movie/model/weapon/world cleanup and source end callbacks, immediately after the final route `SceEventEnd`. It does not indiscriminately preload all keys, restore ordinary pressure victims, or cover Cabin's separate lifecycle.

Under the loader lock, it checks source age, current generation/heap, menu hold, nested ownership and individual key retirement. The entire missing set must fit the payload cap and a conservative contiguous region while retaining cold margins. It accounts for aligned payload plus96 bytes/key (motion owner, MAD tag, SDK heap cell). Refusal performs no I/O or eviction; an allocation race can leave a logged partial set without eviction retry. FCV transport/CRC/relocation remains the existing path.

`port/dreamcast/tools/d367/boss21/MOTION_MOVIE_RESUME.md` records actual native-motion ASan/UBSan fixture variants, current source APIs, generation/hold/cap/fragmentation/fault cases, target object compilation and OFF object identity. The reported metadata addition is569 bytes target BSS. It explicitly leaves full-program/overlay identity, enabled link, real post-movie behavior and source decisions open, and makes no physical-console claim.

### Introduction and actual hold reason

- Introduction: `b753db3061f75b8026b3bbccdb06209cafaf4f9e`, **2026-10-20T19:19:10-04:00**, “Add bounded movie motion restoration with complete allocation preflight”. Default off.
- Capacity integration: `91aa0cb1862e729e876211cdbdb43b52be217deb`, **2026-10-20T21:35:55-04:00**.
- Explicit hold: `42c82e0ff568b81a6787a3c73ad745ce136ea74a`, **2026-10-22T09:30:20-04:00**, Test22 items5+6 promotion. Its commit body records full item3+5+6 and item3-only ch21/r117 thrash failures, while items5+6-only and off passed. The held item3 bundle is `WEAPON_ARCHIVE_REUSE + RESIDENT_LIST_CACHE + LEON_HAND_RETAIN + MOTION_RESUME`.
- `port/dreamcast/tools/d367/rr/recipe.conf` around104–107 retains the item3 hold and r11721–24 refusals. The all-on diagnostic configuration in `CASTLE_SHARED_CACHE_ACCEPTANCE_20261020.md` is not release acceptance.

The available evidence isolates the bundle, **not resume as the culprit**. Calling it a proven resume-only regression would overstate the record; calling it merely untested would omit the observed bundle refusal.

### Recommendation and owner gate

**Park pending an isolated current-recipe test.** Start with `MOTION_RESUME=0/1` while forcing the other three item3 switches0, keep backing/pool/capacity unchanged, and repeat the documented ch21/r117 window. If isolated resume passes, test the relevant bundle combinations and explain the former refusal before promotion. Cover fresh title/card load, normal movie finish, skip/cancel chains, immediate first gameplay I/O, menu hold, retirement/rebind and heap/KOS pressure. Require STRICT and the ordinary visual/owner gates.

Existing host command (not rerun as part of this audit):

```sh
python3 port/dreamcast/tools/d367/boss21/test_motion_pressure.py
```

It compiles actual `native_motion.cpp` into sanitized variants; its script explicitly requests leak checking. `test_motion_resume_journal.cpp` is an additional component fixture. `test_motion_resume_build_guards.py` accepts the regular baseline make arguments **after the KOS environment is loaded** and performs Make dry runs only. Those scripts cannot substitute for target link or route evidence.

## STORAGE_BOUNCE_ALIGNED

### Current behavior and composition

`port/dreamcast/room/room_storage.cpp` owns one shared `alignas(32)` bounce buffer with32 bytes of slack and a guarded reader lifetime. The knob changes the returned small-file bounce pointer from base+16 to the aligned base. Byte counts, destination copies, chunk consumers and reader locking remain the same; it adds no new buffer allocation. Whole bounded chunks in plain mode can then use a single multi-sector GD command instead of the unaligned sector-cache sequence.

`port/dreamcast/game/game30.mk` declares0 by default and rejects nonzero unless `DISC_READ_FALLBACK=2`; its error explains that alignment otherwise starts KOS streams. The release uses fallback3, which deliberately starts in streaming mode and latches to plain reads after the first failure. This knob is therefore not independently enableable in the accepted release profile.

### Timeline and reason off

- Introduction: `34be409d78075b491d66a3d519ae615c61569f6d`, **2026-10-16T12:49:01-04:00**, aligned plain-read bounce.
- Recipe enable: `52868e97b0441e1100287f9d96d89a429c9c5d85`, **2026-10-16T13:58:25-04:00**. The candidate combined `DISC_COMPAT=1 DISC_LAND_SPIN_MS=20 STORAGE_BOUNCE_ALIGNED=1 TEX_PACK_WINDOW=128` with texord16 data ordering. Its weak-drive command/read figures are a bundle/window result, not an isolated bounce-buffer speedup.
- Recipe removal/profile change: merge `359b2125bcec184b659f29a8eb3d4dab41f1ca78`, **2026-10-16T16:13:09-04:00**, selected **user optionA**: keep fast streams, then latch bounded DMA/reinit/PIO plain fallback on the first failure and redo that request. The recipe becomes `DISC_COMPAT=1 DISC_READ_FALLBACK=3 DISC_LAND_SPIN_MS=20`; aligned bounce and texord16 are no longer selected.
- `port/dreamcast/tools/d367/test15/t15-build.sh` and `port/dreamcast/CONTRIBUTING-PORT.md` retain this policy: plain-read alignment/window are optional, not the selected release path. The merge requires `git log -m`/first-parent inspection to see the recipe removal; a simple pickaxe that suppresses merge diffs misses it.

This is a documented strategy choice and dependency conflict, **not evidence that aligned bounce corrupted bytes or independently failed a console test**.

### Recommendation and owner gate

**Park for the release's fallback3 profile.** If the owner deliberately reopens the plain-mode decision, compare `DISC_READ_FALLBACK=2 STORAGE_BOUNCE_ALIGNED=0` against the same recipe with alignment1, holding `TEX_PACK_WINDOW` and data order fixed. Check full read/destination hashes, read-command and wait logs, partial/error handling, mutex ownership, weak-drive/GDEMU repeat seeds, room/door/movie load timings, and physical console behavior. Source/discrete timing gates must explicitly cover the profile change. Do not remove the guard or advertise old bundle figures as an aligned-bounce result.

## Reproduction and attribution limits

This report is source/history review plus the new FRONT_TEXOBJ host counterexample. It has not run game data, a physical Dreamcast, new STRICT routes, or full target builds for the five parked switches. Older logged costs and host/object receipts are labeled historical. Every acceptance recommendation still has the concrete owner gate above; no default or release recipe has been changed by this audit.

See [the Build 34 hand-back](build-34.md) for current progress, final qualification receipts and canonical owner commands.
