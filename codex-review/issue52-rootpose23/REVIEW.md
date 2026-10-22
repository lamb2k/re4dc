# Independent rootpose23 source/data review — 2026-10-22

Initial review615e8b21a againstf047721fb is preserved. CURRENT independent review pins coordinator base 64a28a7bdc44312924b14414501b7d4ff1d2d032 and rebased mainfix 6b47094d7a9d716107b93a0547ba48ea834303ca. No correctness finding in the patch. No source/recipe/builder/guest changes or tests rerun by this lane. Main owns runtime tests/build/stage/actual gates; Claude protected areas untouched.

## Allocation and lifetime

The old ROOT1 count1 allocation was sizeof(PartPose)+96 while movie preflight requested sizeof(PartPose). Room4Cell32 validates exact payload size. SH4 PartPose40 gives target136, host64 PartPose48 gives144; host size is not target ABI. Slot already uses correct sizeof(Slot). New dyn::part_cell_bytes shares allocation/log/validation, preserves ROOT0 and multipart sizes, and keys on count1 even when root witness is refused/singular (~0 offset). Binding bounds1..255 prevent arithmetic overflow.

Room4 validation first rejects stale generation, inactive heap4, range and non-32-aligned base before header read, then checks W6H4 magic, generation and exact payload bytes. It does not validate MAD diagnostic tag strings. Tail needs float alignment, not an independent32-aligned allocation. IDs/Slots/parts live outside the borrowed world cell. Movie borrows only retained world package; reload preserves owner serial/rest/part witness/root tail/order. Reset/rebind frees once; patch changes no lifetime/layout.

Main host evidence inspected, not rerun: actual production types/helper; old ROOT1 validation failure preserved; fixed ROOT0 1224/ROOT1 1226 assertions plus27 integration contracts. Includes count1/2/255, short/long sizes, stale generation, refused witness and full-tail roundtrip. Source/host evidence only.

## Pinned current references

Evidence identities.json freshly hashes release/H2 programme/ELF/flags/fixtures/tools and12 selected current raw-image members, all byteexact retained manifest. Whole1.18GB track not rehashed. Both retained programmes are ROOT0 references, not new ROOT1 acceptance:
- source f047721fb release raw97beeb54a66f787bc5c4c40159f922bb204c94a2fcec5103ee92cb4df505e723; ELF b344ec85a4fd6d6738e44e79368d0fe97c746502732836238f1ff882446b0244.
- diagnostic H2 ELF e4b265a3416091a8475f41cbfeffc5713ecf215199610fe35bb0bdd9267c09f8.
- dc/movie/r100s30.seq2,402,304B SHAa7a73a704159997504e4cbcca8d3aa457c4505cf02da81f2363222077ddc7de3.

Image C:/Game Dev/Emulators/RE4DC-RR/cand-f047721f/gdemu/track03.bin. trigger-records.json retains fresh current .arc/.dar member/AEV/selected-record SHA and exact selected records; paired AEV records match. Read into memory only; no asset extraction/writes.

Main separately reports ROOT1 linked programme and WARP_JUMP1 diagnostic build. Its4GiB ext4 full extract+fp_master /root/probe/rootpose23-stage-20261022-01 is parent owned. No append design/stage/fixture allocated here. Retained RR rel/tree absent; manifest.json/IP.BIN present. All original QA images immutable.

## Source-qualified s30 fragment proposal — unexecuted

Fresh matching diagnostic ROOT1 programme, own ELF symbols/ABI, cold boot. Declare room0x100 jp1 pos(-110405,-733,2193) ang-1.5708 scenario0 0x10 invdefault. RSF14 initially clear, no old save-state. R100Init jump1 sets RSF3/10/13, initializes after-officer car/trap state, registers original area1→r100_GakeEvent and preloads event4. Explicit3/10/13 would be redundant and does not prove preceding gameplay traversal.

Actual AEV1: flag3/type2/trigger0x08/player1/checkFlag3 (front+angle), XZ prism floor-733.040527 height1764.099854 center(-110405.107422,2193.113373). Angle-90deg, range80deg. Old H2 goto matches center to integer rounding. Ordinary A required. After ready placement, release neutral then one ordinary A pulse. SceAtDataSet_exec a=0 preserves authored trigger. Callback with RSF14 clear sets it and original readEvent(4,1) routes to0x10030, then restores gameplay. Do not use atfunc/DebugTrg/direct movie/kill. Area0x18 is a separate authored bridge action callback, not area1.

Full H2 traversal is not a source prerequisite for this exact allocation mismatch: bindings exist on room load before original area1 action. Cold fragment has different memory/gameplay history; it cannot certify continuous H2, its original420s named exception, or timing. Historical current H2 elapsed168.1s/harnessROOT0 is reference only.

Future main allocation: RE4DC_EMU=console, <=50s actual hard bound, exact programme/ELF/14overlay/asset receipts, before/movie/after screenshots, MOVIEARENA borrow+return, s30 total340 played340 drop0 late00 and normal resumed world/dynamic state. Timeout/untriggered/partial is not pass. Source does not assure completion within50s. No old-state ABI mixing.

## Source-qualified r11c original lever proposal — unexecuted

Cold matching programme, room0x11c. Item_find_flg must include0x00020000 (siege complete); retain Ashley-found0x00100000 if desired =>0x00120000. r11c_initGate only registers area4 with siege-complete. Existing census find0x00100000 DOES NOT register lever. Route must be unset (saveflag0x40000000 clear) or opposite known selection; same selected choice deliberately sets noGear1.

Actual AEV4: flag3/type2/trigger0x08/player1/checkFlag1 (front point, no angle requirement), floor-13.8908997 height1000, centerXZ(112701.199219,-28326.738770). Candidate position(112701,-13.89,-28327), ang0: its front point550 ahead stays inside recorded convex prism. Actual floor/wall snapping still untested. Optional area4 helper uses world center but preserves existing Y; matching Y needed. Lever0x35 model position is not substituted for interaction-area center.

Ordinary A opens message0 attr0x220. Message::init sets m_cur0; code08 A confirms choice1, Down then A choice2. Separate press/release edges required. Warp dialogue confirmation must append ev to act lines because SceEventStart holds event status1 and normal acts are suppressed. Example syntax act FRAME a 3 ev; no exact frame schedule qualified. Warp parser does NOT recognize literal down; source supports fwd/back stick or raw masks, which need mapping proof. Default choice1 avoids that issue; fp_run host keys supports down+A. Do not invent blind frame timings.

Unset choice1 or2 calls r11c_moveLever(noGear0) and ordinary source gear/chain/gate tasks. Same-selected calls noGear1 intentionally. Observe lever0x35; gear0x10/0x11/0x32 part z/y/z rotations after15 sleeps; chain0x02/0x03 Y; gates0x33/0x34 move3600 over80 ticks and signal Room_flg[2]bit31. Capture before/changing gears/end gates+lever, source route flags and restored control. Census entry or two stills without original animation/end-state does not pass. Church PT/emptyLOD work remains independent.

## Scope and preserved evidence

Source/host, linked programme, Flycast console, release checks and physical Dreamcast acceptance distinct. No new target result or performance claim. No release/publication/SD/contact. Coordinator update supersedes historical advice. Main owns fixtures/allocations/staging/runs. Preserved all existing evidence, castle checkpoint127, texture/atlas/castle and prior units.

Evidence folder C:/Flycast-Evidence/re4-dreamcast/issue52-rootpose23-review-20261022. First read-only inspection shape error preserved as first-inspection-error.json; corrected tuple-reader completed. Final metadata write attempt had JavaScript parse error before any file call; no partial new output. Neither was a target run.


## Current coordinator-base review

Across f047→64a, native_static adds43 lines for backface headers/emission/census scopes outside dyn/movie regions. dbgwarp adds18 lines of read-only atlog diagnostics. R100/R11c/AEV/area/message/input contracts are byteunchanged. Rebased6b470 carries the same helper/allocation/log/validation repair. No new correctness issue. Old f047 programme/master is pre-rebase evidence only; new target qualification must bind current main programme/assets and fresh ELF ABI. No new tests/build/guest performed by this review.
