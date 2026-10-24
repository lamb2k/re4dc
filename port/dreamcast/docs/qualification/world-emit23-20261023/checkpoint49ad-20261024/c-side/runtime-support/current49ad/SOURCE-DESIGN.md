# Current49ad freeze330: implementation and source verdict

Source49ad20f9932d638ddb7becf5db6f86b92e0a76a2; exact R-gW ELF9f41e9b398984b1c3cdbed6d6910b032746aa6badc76dcfeda0a1fa739250e5d. All work here is source/read-only ELF research and host controls. No SDK, guest, runtime patch, staging, image comparison, gate or recipe change occurred. Existing7a receipt9fd3ff6d...40dee and modeled timings are unchanged.

## What the helper implements

`freeze330-observer.py` requires the exact source/ELF/layout hash, cap path, PID, executable/decoder hashes and original guest monotonic deadline in an owner-supplied binding. It opens only the exact OwnedRam cap/PID/image and uses that same already-validated process handle for both main RAM and each exact8MiB VRAM read. No unchecked PID reopen, input, suspension, write, process launch, SDK or endless retry. Completed seqlock reads try at most3 times; actor lists are bounded to512 nodes, checked against actual manager pool boundaries/stride, reject cycles and pushed storage. Reads cease at the original guest deadline. The launcher must still hold worker serialization, shared3-slot then global16 lock, and exact-child55s guard.

The helper reads actual compiled completed render/source/frame snapshots; live GlobalWork/camera, actor/object rosters, viewport/projection; PVR current view/frame offsets/extent, pending/flip/render; steady queue/watch and presentation failure; retained package pool upload states. Source/presentation/upload fields bracket VRAM, and a second bounded read checks both framebuffers. It keeps both decoded images and their hashes. Current framebuffer offsets come from actual KOS state, not a latest boot-log fb pair. Backend limits are640×480, non-FSAA RGB565 mapping; unsupported extents refuse. Format mapping remains tied to the existing backend/source contract, not a new MMIO probe.

`readonly_snapshot_consistent` is only a diagnostic observation. `strict_pixel_qualified` is always false for this source. The helper never interprets freeze330, matching images or matching current rosters as a strict pixel gate. It observes current package state, not an absent completed-frame upload-owner table. It uses KOS pending/flip/render and steady queue/watch; native present_submitted/resolved alone is insufficient in PIPELINE2, where resolved is updated at a later fence.

No current guest binding has been supplied and no observer run is claimed. The provided manifest is R-gW ONLY. It refuses another arm/twin ELF until its actual symbols/DWARF/source receipt is extracted; R-mW addresses must not be substituted.

## Proven source phase

`src/game/main.cpp`: Render_before -> Render -> Frame_cnt++ -> TaskScheduler -> Render_done -> Render_swap. `gameMainLoop` is inside TaskScheduler and calls re4dc_room_cycle_poll before gameplay movement; ui_bridge calls warp_poll there. The fixture freeze logs/sleeps inside that poll. Thus global330 can stop after a new native frame was begun using source329 and before that frame is completed/presented. In an unskipped normal path the last completed snapshot is source328. The helper requires that exact observed relationship, equal completed profile/UI frame IDs, and next UI frame=completed+1; other relationships are refused rather than guessed.

This corrects the earlier generic “top of tick” shorthand: it is the top of the gameplay task, not before Render_before in the outer loop. Freeze330 is not a completed image for tick330. Source snapshots are112B, profile snapshot428B, completed frame192B, KOS pvr_state520B. Actual DWARF cUnit vptr0/be_flag4/pNext8 and manager pArray4/nArray8/stride12/pAlive20 differ from legacy source comments. All decoder fields come from actual modern ELF layouts.

## Restricted actor-free qualification is unavailable

The completed frame records aggregate model work, not source actor count/identity/pose. Current recipe is NATIVE_ACTOR_FAST1, ACTOR_STATS_LEAN1, NATIVE_ACTOR_LOG0. The actual fast actor implementation makes parts/handled/etc NopStat and returns stats_live with only triangles live; zero actor counters are synthesized and cannot establish actor-count0 except Leon. Neither f1 nor f2 can receive an actor-free exception from these counters. No scene or actor appearance was inferred without a guest.

The completed Source retains player/camera only. Live camera/actors may be ahead of the displayed picture, and next Render_before has already overwritten live viewport/projection/jitter. Existing source/actor ledgers and cumulative/lean statistics do not publish a completed, same-frame actor-pose/viewport population. A live roster read or a completed player position cannot fill that historical gap.

## Minimum missing diagnostic contract (proposal only, default0)

If root later needs a strict pixel gate despite the nil/slower modelled result, a separately owned/reviewed diagnostic would need all of:

1. A completed UI frame/source-tick record containing the actual submitted viewport/projection/jitter and source camera/player state, published before the next frame can overwrite them.
2. A same-frame authoritative actor draw population: distinguish scenery/Leon/other actors and source/native/deferred paths, including count0 support. Preserve source logical identity/creation identity and the actual submitted pose/motion/visibility inputs, or a fully specified digest of those exact immutable inputs with coverage proven on every path. Current NopStat/aggregate counters cannot substitute. This requires actor/model owner coordination; no current GC actor claims are edited here.
3. Texture identity/upload generation coverage for the same submitted frame, including deferred parts; couple its frame/source identity to the actual completed presentation/selected framebuffer generation. Current package flags plus KOS idle prove current observations only, not historical ownership.

Use a separate diagnostic knob default0; absent/explicit0 must preprocess/object/raw-image identically. Publish a bounded fixed record with odd/even sequence outside SQ/SubmitScope and no allocation/logging under render locks; do not attach a fresh-state assumption or persistent production epoch to fix observation. No concrete buffer/hash size, runtime field, hook or implementation is admitted by this proposal. Prove complete hook coverage, mutation controls and OFF identity before any target build; then qualify exact new diagnostic programme/profile separately. Root may simply keep both world switches off and these pixel gates pending. There is no need to manufacture this instrumentation to preserve the honest current result.

## Host evidence

`test-observer.py` reads the actual pinned source and resolved profile, checks source call order/lean-stat counter limitation and actual nm/DWARF offsets, and runs one coherent diagnostic positive while strict pixels remain refused. Seventeen negative state/phase/present/upload controls, freeze-only admission mutant, bounded odd/torn sequence rejection, manager/cUnit roster/cycle checks, exact same-handle8MiB read and short-read rejection pass. Synthetic data stays in RAM; no guest is opened. `HOST-CONTROLS.log` and `RECEIPT.json` pin all source/layout/helper inputs. The Windows ABI/backend call path is source-checked and modeled with a fake ReadProcessMemory callback; an actual Windows observer capture is still untested.