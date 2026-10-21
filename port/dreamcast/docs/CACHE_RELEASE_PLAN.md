# Shared loading audit and release integration plan

Codex main owns the remaining audit, repair prioritization, integration and evidence review. At the user's latest direction, the dedicated cache_fixes agent implements confirmed defects as main finds them. Claude owns production merges, release scope, packaging and publication. Castle is an independent progression workstream and does not wait for this audit. Earlier subagent results are inputs to the main thread, not a queue waiting for those agents to resume.

The next release can use qualified fixes without claiming that the holistic audit is finished. Test21 is already published as test-fe0efcdd-20261020. Its tagged recipe enables MOTION_PRESSURE_BACKING=1 and MOTION_RESERVE_PACK=1; the earlier core repair is already shipped. Retain its regression evidence, qualify later candidates as bounded additions and keep unqualified components disabled. This plan does not authorize a production merge or a release upload.

## Inbox authority and ownership

The applicable coordinator directive is boss18 INBOX I-018: the accounting/packing repair landed as 334416a3, and Claude needs the original post-s20 r100 result before enabling it for Test21. That result is already available at the top of CODEX-STATUS.md, and the published Test21 recipe now enables both switches. The later audit must not reinterpret that fulfilled handoff as an unresolved release hold.

I-016/I-017 require current origin/t15/int before new builds, current recipe/data, castle on disc2 and alive/in-view/not-drawn checks. COMMON.md and CLAUDE.md govern scope freeze, release gates and ownership. The remote integration ref checked for this plan is 54cef5d1560c41d074beee05ffa1ecd38f2ee642. Recheck it before integration; it is a reference point, not a request to freeze Claude's ongoing work.

There was no separate main-cache inbox. codex-lanes/cache21/INBOX.md now records the user's main-thread assignment and references I-018 without inventing a new coordinator directive. Main acknowledges and executes that queue. U004 assigns implementation to /root/cache_fixes in its isolated current-integration worktree; main remains accountable for every audit row, review and integration. Castle retains its separate queue and checkpoints.

## What Claude can use now

The already landed accounting/packing pair has a real original-ambush result on source 4aca1f8330941af1e4b20cb33577169f82c4342f, with the frozen receipt MOTION-PACK-R100-QUALIFICATION.json:

| Same encounter family, different normal-input runs | Motion loads | Evictions | Low-level drive calls |
| --- | --- | --- | --- |
| Baseline | 21 to 703 | 0 to 682 | 2810 to 3994, plus 1184 |
| Repaired pair | 21 to 24 | 0 to 0 | 2210 to 2311, plus 101 |

The repaired run has three ordinary kills and a 16.625-second read-quiet tail. These are bounded Flycast cache results, not a frame-identical timing pair or a console FPS claim. Claude's I-018 records existing identity, STRICT, KOS48KiB and s30 checks on the earlier integration. Use this evidence for the existing motion release decision; do not cherry-pick334416a3 again when it is already in the selected base.

Claude selects the upcoming hotfix or next release scope. Test21 is already published and its assets stay immutable. The tag resolves to documentation commit860281041f3a3560f2a5aef5d50625222e4dadf3 over game sourcefe0efcdd. The tagged release-knobs.txt was read directly: both motion switches are1, CAST_MIPMAP=1 and GANADO_LOD_LEVEL=2 (g70). Later additions require a new candidate and its own gates.

## Candidate register

All switches are default off. An evidence-only branch is not a runtime patch.

| Candidate and exact input | Activation and dependency | Current evidence | Remaining release work |
| --- | --- | --- | --- |
| Six-fix successor d4a3b31fac3362937a3f21eaa874e07be94fd061, branch codex/cache21-successor | MOTION_PRESSURE_BACKING, MOTION_RESERVE_PACK, WEAPON_ARCHIVE_REUSE, MOTION_RESUME, LEON_HAND_RETAIN, RESIDENT_LIST_CACHE. Preserve their existing prerequisites. | Full disabled identity on its c7 base; enabled full link; bounded Flycast qualification 3a38c146. | Reconcile current integration base/recipe; resolve memory/VRAM behavior against a matched control; final release gates. |
| Capacity1f7c34e4fc7a72222fd99c81afe66d08f890aa9e, branch codex/boss21-motion-capacity, parent d4 | MOTION_CAPACITY=1 with packed reserve/pressure backing. | Actual-SDK host K05 60loads/58evictions to3/0; five disabled SH4 objects match. | Root architecture review, reset/borrower contracts, native admission/preflight edges, full link and actual crowded-scene checks. |
| Audio83cb1ab0d739d95e8fb00d6346578c947e1aa142, branch codex/cache21-audio-recovery, parent c7 | AICA_LAYOUT_RECOVER=1, AICA_AUDIO=1. | 396 source sanitizer checks; disabled SH4 identity. | Reconcile source base, full callchain stack, native bank/ring recovery and playback/KOS checks. |
| Effectb3101919701173f23260edeff29433d6754d7e8f, branch codex/cache21-effect-admission | EFFECT_ADMISSION_GUARD=1. | Baseline/OFF/ON source tests; disabled actual SH4 object identity; enabled plus 47 text bytes/no data or BSS growth. | Final program identity and failure/retry plus successful FX gameplay checks. Partial downstream registration remains separate. |
| Display restorationa3727579d2f3a8c49cc6877e330f8a783780ce99, branch codex/cache21-fixes, base54cef5d1 | EM_ADMISSION_DISP_FIX=1. | Actual-source 216 checks per baseline/OFF/ON; disabled SH4 read.o identity for both weapon heap variants. Main reviewed the three-line failure-return repair. | Final program identity and admission/refusal gameplay gates. Failure cleanup, not an ordinary disc-read explanation. |
| Texture-window holdf3229facdc92e42b097753d9328f7889968bf060, branch codex/cache21-fixes, parenta372 | SS_WINDOW_HOLD_RESTORE=1 with existing SS_HOLD_RESTORE, MOVIE_WINDOW and TEX_RESIDENT. | Actual-helper/lease sanitizer arms26/26/26 plus25hold-off cases; disabled whole native_ui.o identity; enabled plus96text/no data or BSS growth. Main reviewed the hook. | Final program, inventory/movie restore and target-I/O comparison. Existing restore intersection/working-set pressure remain open; no read-elimination claim. |
| Optional HUD preparationf33c3189 | Existing resident-list format and explicitly selected private data. | Tool/source evidence only. | Separate asset admission and VRAM comparison. Excluded from the default bundle. |
| Lifetime findingsd396bd9e, branch codex/boss21-motion-lifetime-audit | Docs/tests only; no runtime switch. | Post-destroy frees, display flags on full slots and partial EVD false-complete retry reproduced. | Fix worker implements scoped repairs; main reviews and validates integration. Do not merge this evidence branch as if it repaired runtime behavior. |

Six-fix runtime identity: ELF 52a5d671203e22e9f20728a8fbc3b61e080f7ba44e06891df635248a374dd053; raw 8c26c048c3e7aec66f2ea6496b1c2ec03e0b2b6e2ce6ff1ae1308dac62958034; ISO a8bfd7e67d8de2c8d79f3b639f6243e30da40afbe8b523aec87d5bb47c3f110d. Qualification 3a38c146421ac953690bec20211c0c50979d370a is tools/docs, not another runtime component.

That candidate passes cold entry, warmed HG/TMP hands, resident metadata reuse, inventory returns, radio portraits, natural s20 completion, original ambush kills and Diagnostics return. Its resource snapshot still has heap54304B, KOSfree8384B plus brk69632B, VRAMfree103168B/largest12160B with fragmentation failures, and movie underruns. Inventory returns still read2.76 to3.06MB. Classify these with a matched control before release; this is functional qualification, not clean resource or whole-cache acceptance.

## Current normal-reload finding

The retained d4 sixfix-inventory07 run has four ordinary HG/TMP menu/equip cycles. Main separated their captured admissions; the log prefix overran, so this is a bounded window, not an all-room texture census.

| Cycle | Total low-level read bytes | Texture opens while menu active | Return preload opens | Later first-sight opens |
| --- | ---: | ---: | ---: | ---: |
| 0 | 3056032 | 36 | 32 | 2 |
| 1 | 2758496 | 32 | 15 | 0 |
| 2 | 3004704 | 36 | 11 | 1 |
| 3 | 2999936 | 35 | 17 | 0 |

The observer's metadata-eviction counter stays zero throughout. Motion stays20loads/0evictions, and the last three hand switches need no hand-disc reads. Each menu still logically loads531040B of common data,912704B of puzzle/item data and a126720B overlay. These logical sizes are not added to texture VRAM bytes as if they were disjoint low-level drive counters.

The 3MiB world backing compresses to about1.721MB inside the2MiB bank, with pool0 and ui_released0. Later menu-image uploads trigger texture-window evictions of26,6and2entries. Actual movie_window_release closes entries without RE4DC_HOLD_EVICTED, unlike ordinary LRU/slot eviction. This omission is present in publishedfe0efcdd and current54cef5d1 as well as d4. The fix worker implemented and source/object-qualified the narrow repairf3229fac; selected-window, fence and lease behavior stay unchanged. Target restoration/I/O remains open.

Remembering the keys repairs restoration coverage; it does not establish fewer total reads. Existing hold restoration intersects remembered keys with budgeted preload candidates, and real menu/world working-set pressure remains. Exact evicted key ownership, complete package coverage and target before/after validation remain open. Local attribution: codex-lanes/cache21/menu-reload-attribution.json and its replayable analyzer.

## Main thread execution order

1. **Maintain the fulfilled I-018 handoff.** Keep the original result and receipt at the top of CODEX-STATUS as regression evidence. Test21 already enables the pair. Reproduce the new Test21 reports on that immutable release before attributing them to later candidates.
2. **Trace normal reloads and implement confirmed findings concurrently.** Main follows ordinary enemy, shot, weapon, inventory, player and boss demand into actual read/admission paths. The fix worker implements narrow handed-over defects immediately behind default-off guards; main reviews source tests and integration. Its current small H064 display-flags repair does not replace the normal-path audit. Inventory texture-window bookkeeping is the next handed-over normal-path repair.
3. **Finish source repair contracts and repeated image/effect/audio admission.** Review capacity and H064 together: retire native metadata, reserves and overflow before heap destruction after draining/canceling actual readers; preserve handle generations and shared-owner refcount deltas during rollback. Trace persistent packed payload failure separately from index backoff, loose missing-key overflow, successful owner reuse and emitter destruction. Reuse the existing audio/effect candidates. Resolve actual working-set and fragmentation constraints before adding residency.
4. **Reconcile the qualified subset onto current integration.** In one isolated landing branch, import selected runtime deltas and required tests/docs. Do not merge every historical branch or old recipe wholesale. The d4 runtime imports are1bb1ddec weapon, b753db30 movie,75802750 joined reserve,fc99c487 hands and3e5ede65 resident metadata; accounting/packing already exists upstream. Resolve shared-file claims first. Preserve all frozen controls and private data.
5. **Qualify the combined chosen scope.** Record all modified switches, including changes under existing MOTION_RESERVE_PACK; not just new knob names. Build a matching control and merged-disabled arm with identical labels, recipe and asset inputs. Then build the combined enabled candidate once and run the required gates on those exact bytes. Use component arms only when a failure needs attribution.
6. **Hand Claude a release integration kit.** Include the one landing revision, prerequisites, switch/data manifest, program/overlay/asset hashes, gate receipts, memory maps, screenshot index and issue classification. Claude selects the open release scope, merges, packages and publishes under the standing release rules.

A new candidate is not enabled merely because a host test passes. Conversely, five remaining lifetime cases do not silently block the independent earlier motion handoff. A newly introduced crash, hang, stuck route, save loss or required asset failure blocks its affected release scope. Existing non-regression issues follow Claude's documented known-issue policy.

## Remaining holistic audit ledger

Main owns every audit row below. Prior Boss/QA assignments identify evidence sources; the active fix worker implements confirmed scoped defects under main review. Each row records selected code/data identity, demand group, owner/generation/lifetime, failure/retry behavior and the target case needed for closure.

| Area | Evidence already available | Main closure requirement |
| --- | --- | --- |
| A01 evaluator callers | Seven scoped lease hooks and source pins | Cover wrappers/direct consumers; every cached table has a valid lease through final use. |
| A02 transitions/blends | Hokan matrix interpolation distinguished from retained FCVs | Resolve true body/blend demand, phase changes and saved donor pointers. |
| A03 shapes/attachments | Shape/face/Work inventory | Close OBJ12 child/destructor and OBJ16 installed callback lifetime; include independently animated attachments. |
| A04 Work/event selectors | Event ARC and Work source tracing | Resolve all selected dynamic owners and exceptional exits. |
| A05 selected variants | 66-archive inventory | Validate actual selected flags/records/groups; inventory count is not reviewed behavior count. |
| A06 capacity/pressure | K05 proven72224B demand in64832B backing; candidate1f7 | Prove reclamation, allocation feasibility, fragmentation, pins and bounded cap in actual scenes. |
| A07 borrowed player motion | H064 leases plus normal teardown controls | Close fatal/forced interrupt, child/callback donor and generation contracts. |
| A08 admission/retirement | Three H064 faults reproduced | Repair reset, full-slot flags and EVD transaction; close intra-room quiescence/event-shape plus DVD/resize/model partial-admission cases. |
| A09 model/detail packages | First-spawn/native family evidence | Attribute repeated package opens across LOD/detail changes, re-entry and movie restoration. |
| A10 texture/HUD/FX residency | Resident-list fix and six-fix target checks | Close payload retry/missing overflow, menu/world texture readmission and VRAM fragmentation. |
| A11 effect-record lifetimes | Actual registration fault and source delete ordering | Prove every live emitter/controller stops before its source is freed; partial registration remains open. |
| A12 one-shot banks | Resident bank source map; audio recovery83cb | Verify reuse, rejected fresh/replacement admission, headloss/death/weapon variants and reset ownership. |
| A13 music/voice streams | Dedicated stream attribution and natural s20 result | Separate expected refills from game-thread stalls; close interrupted/chained stream recovery and audible output. |
| A14 Leon/Ashley transitions | HG/TMP and inventory gates | Complete quick-select, knife, reload, damage/grab, costume/role, partner/playable and Continue cases. |
| A15 menu/held heaps | Six-fix inventory/Diagnostics return | Prove hold/unhold, dead-generation invalidation, no stale pointers and explicit eviction/refill cases. |
| A16 movies/re-entry | Natural s20, skip callbacks, radio portraits | Add cancel/failure/chained clips and changed actor/shape ownership; preserve source resource restoration order. |

## Gameplay and resource acceptance

Use source-defined representative families and add variants when their owner or loader contract differs. Reuse existing evidence when source, program, asset and path identities match. Required coverage includes village r100 post-s20 shots/first appearance/body/headloss/death, village r101 cap4, farm r103 working/alert/hit, pre-fight r11e Ashley movement, Leon quick-select/inventory/knife/reload, and a crowded castle capacity case. Mendez and each distinct boss/parasite/attachment/borrowed-motion policy need explicit coverage, including phase/grab/QTE/death/exit. A movie does not qualify live boss state.

Record source frames, action, motion/hand/texture/model/metadata/bank/stream caller, bytes/reads/blocked time, cache hits/evictions, heap free/largest, KOS minimum and VRAM pinned/dynamic/free/largest/retry/reject map. Warm resident metadata and qualified HG/TMP hand groups must stop rereading. A working set that fits the qualified motion budget must stop cyclic reloads. Attribute residual first-use and streaming separately. No arbitrary enemy/geometry/update reduction is part of this fix bundle.

On the final selected candidate, require full boot/14-overlay/runtime-segment disabled identity, resolved-knob proof, STRICT/decisions or the documented gameplay-equivalence gate, KOS48KiB/s30, memory pressure and recovery, TEXCHK/CAST-GC/NOT-DRAWN, menu/movie/radio/room/Continue/save behavior and the ten-seed GDEMU race through r101 plus a door. Source-only repairs also need their meaningful injected failure/retry controls.

Castle's original chapter-end save remains its own release gate. Its Garrador kill/door and wave evidence are retained, but the latest original Continue restored the earlier checkpoint; do not call the current chapter completed. A future disc2 shared candidate must include the existing qualified castle source/data prerequisites in CASTLE_SHARED_CACHE_ACCEPTANCE_20261020.md; merely swapping d4 bytes into J assets is invalid. Never retarget an old program's save state.

Build/stage on WSL ext4 with existing resource guards, one owned build slot per tree and release priority. Capture actual checkpoint/failure PNGs with program/ELF, room, source-frame interval, action and authoritative post-capture health. Do not launch screenshots-only fixtures. Physical Dreamcast checks must cover the user's actual village/farm/r11e cases before claiming console performance; Flycast results are labeled as such.

## Claude handoff and release checklist

The handoff contains:

- Pinned upstream and landing commit, ordered runtime imports, switch prerequisites and explicit deferred components.
- Resolved public recipe and per-disc data manifest; checksums for boot, overlays and staged files; program-only versus asset changes identified.
- Source/SH4/full-program/runtime receipts, remaining A01-A16 rows, blocker versus known-issue decisions and evidence paths.
- At least one useful gameplay screenshot per visible change, actual failure screenshots and an index; source-only fixes carry source evidence rather than invented gameplay pictures.
- Main and QA disc outputs built from the same selected release recipe. Village remains disc1, castle disc2, island disc3; report actual sectors under504000 and verify save-swap-load. Do not change packaging from this plan alone.
- Updated contributor kit, clean-checkout build proof, README/port README/KNOWN_ISSUES, live release notes, release images and the standing QA asset. Claude handles publication and SD work only under its release authorization.

Do not replace published tag assets or copy this experimental candidate to SD. No release, merge, issue posting or user notification to another service has occurred merely by saving this plan.

## Evidence locations and status reporting

Local shared files: CODEX-STATUS.md, codex-lanes/cache21/INBOX.md, codex-lanes/cache21/STATUS.md and HANDOVER-CODEX-20261020.md. The current execution queue and this release plan supersede stale next-step paragraphs in older component docs; their measured receipts remain valid in their stated scope.

Primary receipts: C:/Flycast-Evidence/re4-dreamcast/qa21-r11e-20261020/MOTION-PACK-R100-QUALIFICATION.json and SIXFIX-FUNCTIONAL-QUALIFICATION.json; boss21-20261020/capacity-handback-1f7c34e4; boss21-20261020/motion-lifetime-h064-d396bd9e; cache21-20261020/effect-admission-b3101919.

Main updates the status header and reports a meaningful completion, failure, blocking condition or material change of direction while working. A finished checkpoint advances to the next queue item; it is not an instruction to wait for a user nudge. Claims of active work reflect actual tool/guest activity, not a completed agent's stale WORKING header.
## New tester feedback

The user confirms Release21. Source-only triage of all five photos is complete in codex-lanes/feedback21/TRIAGE.md, HANDBACK.md and provenance.json. Device, exact QA/main asset, non-boss rooms and freeze persistence after resume remain open. Codex main created and read back four tracking issues at the user's request:

| Issue | Classification and next action |
| --- | --- |
| [48 Pause and RETRY geometry and lighting](https://github.com/lamb2k/re4dc/issues/48) | Priority renderer reproduction. Trace the pause native-world/static-submit/generic-source ownership boundary; photos do not prove a second world was loaded. |
| [49 Reported Mendez freeze](https://github.com/lamb2k/re4dc/issues/49) | Potential progression blocker only if it persists after normal resume. Verify original r11f/em35 fight/phase and source actor progression. |
| [50 QA selector reopening](https://github.com/lamb2k/re4dc/issues/50) | Existing control is full L+R and Down on portA after30 safe gameplay ticks. Verify Test21, improve discoverability and retain event/transition guards. |
| [51 Reduced Ganado quality](https://github.com/lamb2k/re4dc/issues/51) | Named same-pose full/reduced comparison and compatible artist contribution path; no new reduction/default without look review. |

Published fe0efcdd and d4 retain the relevant pause/menu paths; current54cef retains the source-supported ownership lead. No gameplay reproduction or fix for these reports is claimed. Source-only pause triage is not a failed renderer acceptance gate by itself. Main includes the confirmed blocker/known-issue classification before choosing the next release scope.

Test21 already enables CAST_MIPMAP for supported textures. At the user's U005 direction, the mipmap worker now implements compatibility incrementally, beginning with an opt-in existing-VQ world path and15-key farm candidate; remaining formats/consumers follow. Main's MipsFit source review uses existing SH-4 trace/placement tools and has not changed a linker layout. Neither effort has a new performance claim or joins a frozen release scope automatically. PS2 facial/cloth/bone simplification remains separate research. Private chat screenshots are retained as provenance; GitHub issues contain focused summaries rather than the private conversations.
