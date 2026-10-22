# CABIN_SOURCE carrier staging proposal

Design only, 2026-10-22. Base: origin/t15/int 64a28a7bdc44312924b14414501b7d4ff1d2d032, verified against the remote before this lane began. No runtime changes, asset creation, compiler, stage, image or guest was started. The user instruction in CODEX-UPDATE-20261022.md is explicit: "Write the design and ask before building."

## Current-base rebase review

Rebased the two owned design commits onto current origin/t15/int 64a28a7bdc44312924b14414501b7d4ff1d2d032 after preserving the exact original tip88532e6eb44d95f5cbf24f4946c7039879b5c172 at refs/backup/cabin23/pre-rebase-20261022-88532e6eb. The prior reviewed base was f047721fb138b9d7c1a4bf2edf217f76beda4d6c. The intervening backface22 merge adds backface.mk and guarded native_ui census hooks; the eleven cabin/event/audio/media/lifetime source contracts below are unchanged except the main Makefile include. Current source hashes include the new Makefile, native_ui and backface.mk. Keep the approved base's actual backface/census flags when later freezing qualification identities; this design does not enable or edit them.

The full October22 update, Addendum and Correction were reread. They withdraw pack pruning and hold the shared Ganado texture mip decisions: this overlay proposes no prune, mip generation or atlas work. Cabin remains design only. The pending approval question is unanswered; elapsed time is not approval. No assets, build or guest are authorized by this rebase.

## Proposed first deliverable

After user approval, assemble one private **cabin23 ordinary-costume overlay**, using the existing `replace`/`unremove` data-set convention and SHA256SUMS, on a separately pinned current Test 23 data set. Reuse twelve exact retained files below. Do not rebuild the complete old ch2data set, replace its audio/world/texture bundles wholesale, introduce a new archive or emulate a general ARAM heap. The source already implements three narrowly identified carriers, the certificate reader, original room event sequence and movie/audio/UI ownership.

A 64 MiB payload-and-mirror reservation is sufficient for this twelve-file overlay and small manifests (50,926,492 logical payload bytes for two copies). It does **not** allocate a compiler tree, objdir, image or guest. Main must allocate each later qualification job separately, using current disk/guest limits and release priority. No production recipe is changed by this proposal.

## Retained input inventory

All twelve files exist in `/root/re4data/private/ch2data-20261018/files` and in the Windows private mirror. Fresh streamed SHA256 checks match for every pair. Full paths, exact SHA256 values, source-file hashes and headers are in INPUT-INVENTORY.json. Data bytes were read but never copied/materialized by this lane.

| Event | Source carrier path and duplicate preflight/exec path | EVD bytes / payload CRC32 | EVQ CRC32 | Existing movie path, bytes, pictures |
|---|---|---:|---|---|
| s00 / 11c00 | evd/r11cs00.evd; event/evd/r11cs00.evd | 27,456 / 049c020d | 71ab9c4d | dc/movie/r11cs00.seq; 16,100,668; 2,296 |
| s10 / 11c10 | evd/r11cs10.evd; event/evd/r11cs10.evd | 7,296 / 5d7c586f | 8ede2d00 | dc/movie/r11cs10.seq; 5,584,817; 761 |
| s20 / 11c20 | evd/r11cs20.evd; event/evd/r11cs20.evd | 5,568 / 2d331534 | 55c322f1 | dc/movie/r11cs20.seq; 3,697,013; 526 |

Each `evd/*.evd` has its existing 36-byte `.evd.evq` companion: R4EVDREF/version 1, logical payload size, 65,536-byte chunk size, one chunk, canonical-name CRC and CRC-table CRC. These exact certificate CRCs are compiled into native_event_file.cpp. The movie files already match the compiled R4FMV003/full-frame contract: 288x192, 29.97 pictures/s, stereo PCM16 at 32 kHz. Input movies total 25,382,498 B; three unique EVD payloads total 40,320 B; certificates total 108 B. Both EVD directory spellings are needed by present source call paths/preflight and must resolve to identical bytes. Logical twelve-file size is 25,463,246 B. No armour-costume substitution: `game_costume==1` is explicitly rejected by the current preflight.

## Disc staging and admission order

1. Pin the approved release data manifest, source/program/ELF and all fourteen overlay identities first. Layer these twelve path replacements onto that base only. Bind the expected existing hashes before writing anything. Reject a changed base or a collision with different cabin bytes.
2. Use the existing stager on ext4 and bulk mirror once; record final path, bytes, SHA and LBA/extents. Keep movies as their existing interleaved `.seq` files, with the 2,048-byte header prefix unchanged and all record order intact. No split video/audio file, recompression, partial-read container or inv23 change.
3. Keep each movie's extents contiguous where the current stager permits. Put its small EVD/EVQ entries adjacent to the corresponding movie before the long media extent if supported by existing ordering. Preserve two logical EVD paths; allow shared immutable extents only if the existing stager already supports that alias safely. Otherwise pay the extra 40,320 B rather than add a feature.
4. Validate certificates against the exact canonical `evd/...` names, table CRC, payload CRC and file length. At room entry the source's cabin preflight must find all three event copies and all three movie headers; missing/mismatched input must fail before source activation. Preparation is a metadata/file-size qualification; it is not a payload install or successful playback.
5. Preserve the existing source actor/module, room DAR/ARC, texture/model registry and `bgm/aica_str.dat` from the chosen current base. Close their event dependency inventory before the overlay is called build ready; never take the legacy ch2data bundle as proof that the current base has Luis or every effect.

## Source order and ownership

| Phase | Required existing source action | Owner and release boundary |
|---|---|---|
| Room admission | r11c_eventInit preflights all three events/movies; DC registers evd0/evd1; evd0 CMND_ARAM_LOAD prepares a certified logical reference; EmReadSearch retains module 13 capacity at least evd0 size | cDataUnit identity belongs to DC; carrier generation/name/size/logical range is checked before/after any yielding provider call. No payload is published at prepare. |
| s00 entry | Original SceEventStart, destroy partner as authored, close/lock cabin door, waitLoadOk, InitModule, forward MemorySwap into module13, cabin_begin(11c00), EvtMgr.SetEvt, source waits and packets | Native carrier binds the exact module allocation and heap, retains displaced bytes, and pairs each request with its generation. Cabin independently owns one movie/UI generation and source event pointer. |
| s00 exit | Original event finishes; reverse MemorySwap restores the original module bytes; evd0 DEL_DATA. Source creates Ashley and pre-reads module4 with the existing 0x120000 reserve, prepares evd1 and preloads s20 | Audio-owner close precedes media aftermath. Do not shrink the 0x120000 source reserve merely because s10 is only 7,296 B. Wait for source_done plus exact final picture shown/transport retired before complete handoff. |
| Siege | Original room logic controls waves, kills, ladders, Luis and event triggers; movie owner is idle after s00 aftermath | No generic replacement siege, no synthetic completion flags. Preserve current PS2 chapter-spawn and cap contract. |
| s10 completion | Existing evd1 wait, forward swap into current module13, cabin_begin(11c10), SetEvt (StatusFlag 0x400), source wait, reverse swap, evd1 DEL_DATA, event end, aftermath, r11c_initGate | Source remains progression authority. Byte restoration, event-count release and final UI presentation are separate receipts, all required. |
| s20 failure | Original failure branch, source event/stream stop, source enemy retirement, cabin_begin(11c20), EvtReadExec("event/evd/r11cs20.evd",0,2), source_done keep1 | Keep the authored death event alive. s20 has no generic s00/s10 park/swap path; death committed by source packets leads to original death demo/Continue. Do not force mode2, health or event counters. |
| Accepted cancel | Only source RunEvtCancel acceptance arms movie fast-final; no independent movie pad shortcut | Consume/check every record, require exact final upload serial actually shown, then complete media and reverse/retire through original source paths. |
| Teardown/reset | Preflight all carrier allocations, module identity, event/readers, DMA scopes/requests, audio callbacks, source/room heaps and UI presentation | Refuse retirement while any borrow exists; never clear a partial forward state or overwrite a newer generation. Only the validated source owner frees its current allocation. Preserve evidence on failure. |

The existing native state machine is `Absent -> Preparing -> Reference -> (Swap -> Ready/module role) or installed MRAM -> event-bound -> unbound -> reverse/park/retire`. It has exactly three carrier slots, sixteen request leases, monotonic generations and at most 1,024 bytes of fixed carrier metadata. DC has 32 cDataUnit slots. Three slots are a capacity requirement, not proof that the other 29 are free in the actual room. Module identity, heap tags, exact allocation and logical non-overlap checks remain mandatory.

Original source sound requests remain authoritative. Current cabin audio ownership maps s00/s10/s20 to request numbers 0x21/0x44/0x28, tags exact source event/voice identities and suppresses only the owned duplicate disc stream while the movie PCM presents. Preserve unrelated sound slots. Stream START/DMA acknowledgement and final drain must be observed; submitting DMA is not playback/drain proof.

## Memory accounting before an approved build

These are source-derived payload components, not measured peak acceptance:

| Component | Bytes / constraint |
|---|---:|
| Three EVD payload identities | 40,320 total |
| Conservative simultaneous EVD transfer/retained copies | Up to 80,640 payload B (two copies per identity), excluding original module allocation already in the base; verify actual overlap/allocator tags |
| Carrier fixed metadata | <=1,024 B by existing static_assert; 3 carriers / 16 requests |
| Movie video input + two luma + four chroma planes | 65,536 + 110,592 + 55,296 = 231,424 B |
| PCM/callback/read staging | 49,152 + 32,768 + 16,416 = 98,336 B |
| Source-heap stereo separation buffer | 32,800 B when this movie owns the stream service |
| Pinned codec control objects | 52 + 716 = 768 B |
| Known movie CPU payload subtotal | 363,328 B; software row conversion adds 4,608 B if selected |
| Conservative carrier+movie component sum | 443,968 B; 448,576 B with software rows, before allocator tags/alignment/fixed owners/other room work |
| Movie texture | Budget 262,144 VRAM B conservatively; existing MOVIE_WINDOW=1 uses 196,608 B at height192. Resolve actual approved flags rather than assume the smaller arm. |
| AICA movie ring | 32,768 B per channel, 65,536 B total, within current audio layout; do not double count source separation as AICA storage |
| Largest known individual CPU staging request | 65,536 B; allocator/tag/alignment may require a larger actual free block |

Keep the existing DVD swap scratch buffers and original module13/room/actor allocations in the live base budget; they are not free just because the incremental table excludes them. MemorySwap uses the existing 64 KiB scratch pieces; these events are each below one piece. Cabin IDs do not satisfy `movie_world_id()` (currently r11f10/r11f11 and optionally r100s30), so **do not claim the cabin decoder borrows the world cell**. Keep the cabin world allocation live in the budget. No new arena, pool or fallback allocator is proposed.

Before admission, require fresh per-heap live/peak/free/largest-block accounting at room entry, forward swap, movie open, source terminal, transport retirement and aftermath; report KOS free/stack high-water, VRAM pinned/dynamic/free/largest, AICA reservations and all requests still owned. The sums above are not an upper bound for the whole room. Source-task 12 KiB floor and earlier static-frame notes are not a whole-call-chain stack pass.

## Qualification plan after user approval and separate root allocation

1. **Offline data gate:** exact base/overlay manifests; all twelve hashes/EVQ headers/chunk CRCs; movie record totals/end markers and header contracts; path/extents map; mirror readback. Resolve Luis/model/effect/audio dependency closure. No asset generation if retained inputs suffice.
2. **Source/object gate:** exercise existing carrier/EVD forward/refusal/retry/rollback/retirement suites on the selected current source, including EVD_ARAM_ALLOC_RETRY and EVD_FORWARD_RECEIPT prerequisites, repeated/role2 paths, pointer/epoch changes and admission failure. Retain all integrated safety guards; do not independently change production recipes/defaults. Selected CABIN_SOURCE arm needs ROUTE_CH22/ROUTE_MOVIES/AICA_AUDIO/AICA_STREAMS/NATIVE_STATIC. Resolve MOVIE_HEAP_EVICT/MOVIE_STAGE_ORDER explicitly: the cabin has twelve live CPU allocation records (thirteen with software rows), so the current MaxAllocs16 branch is required; MaxAllocs10 without MOVIE_HEAP_EVICT is insufficient. Largest-first reserve has at most twelve entries, excluding the two separately admitted codec controls. Prefer existing CABIN_COMPLETE_HANDOFF for the reviewed final-display handshake, once current source/data prerequisites are pinned.
3. **Full identity gate:** one separately allocated disabled control and enabled candidate; exact OFF program plus all fourteen overlays against the frozen base, unrelated files/bytes/extents unchanged. Pin SDK/KOS, resolved flags, source/program/ELF, each overlay and complete data manifest. This is not a new shipping recipe.
4. **Console-mode Flycast component gates:** normal s00 2296/2296, s10 761/761 and s20 526/526, with zero HALT/FAULT/MISSING, no TEXCHK/registry gaps, source packet/cancel/death receipts, owned audio/DMA drain, module reverse CRC and source terminal. Capture active display through movie/aftermath as well as fb0; a final still cannot establish continuous presentation. Test accepted skip at multiple valid points and held input across return; no forced source flags/health.
5. **Route gate:** authentic chapter/cabin entry, complete original siege/waves/ladders/Luis exit, s10 next-gate playability, original s20 death/Continue, post-Continue repeat and clean room/reset retirement. Each owned guest remains <=50s (or current stricter root cap), console mode, global capacity/release priority. s00 itself is ~76.61s of media: an uninterrupted full playback requires an explicit future guest-limit allocation/approved capture strategy; do not silently exceed the bound or call a checkpoint-fragmented run continuous acceptance.
6. **Release/hardware gates:** final selected release tier, KOS squeeze and current global gates remain Claude's ownership. Physical Dreamcast/GDEMU verifies DMA/read timing, uninterrupted display/audio and lifetime/route behavior. Source/host/object or Flycast success does not accept physical behavior or claim performance.

## Missing inputs and decision for review

The twelve cabin carrier/movie inputs are present and exact; the missing deliverable is a reviewed, named overlay tied to the current release base, not missing EVD/movie conversion. Before a build:

- Main/Claude must choose the frozen Test23 base manifest and inclusion order relative to codex22/mipfault22/inv23. Historical ch2data is only the input donor. No edits in those lanes or root-owned native_static.cpp are needed for this design.
- Close current event dependency provenance: original module13/4/3 sizes and allocation overlap, Luis gameplay model/texture pairs, cabin effect keys, source audio block/request layout versus current aica_str.dat. Historical CODEX_INTEGRATED names D55 TEX fail441a0cca, missing Luis paira333b301-0ad86c86 and AICA block10; these remain historical unresolved warnings until mapped on the chosen current data set. No matching files were found by bounded filename checks in ch2data, mip22b, rc19 and sc21; packed-index membership has not been inspected, so absence from the final current disc is not established.
- Decide qualification capture/resource policy for the ~76.61s s00 movie against the existing <=50s guest bound. Partial component sessions cannot substitute for continuous-display proof.
- **User decision requested before any building:** approve the ordinary-costume twelve-file carrier overlay and the staged qualification plan, leaving armour event support out of this first data set. Approval does not authorize publication, recipe promotion, SD copying or contacting anyone.
