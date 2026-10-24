# Dedup qualification and continuation, 2026-10-23

Done: Frozen af09 programme passes target link, OFF image identity, three exact look comparisons, KOS48 fight, three-room texture/character census, GDEMU seed1 and full H2 movie playback with identical OFF/ON heap.
Doing now: Correcting the memory gate profile and preserving the current-integration unit. Large builds and staging wait for C: to recover above its floor and working reserve.
Next: Build standard release-derived Off/On gate twins, verify the recipe heap floor, package the private QA pair, then start INBOX I-001 offline re-stripification without waiting for the coordinator.
Blocked / Needs the user: C: is below the20GiB floor; physical-console timing remains pending. Automatic cleanup review rejected both deletion attempts; no files were removed.

## Pushed source unit

- Current consolidated branch: wip/dedup-offline23-next-20261023 at3911ebb40262fb7a572aa80488a1f5734023f731. It contains origin/t15/int eb1fe9533, reviewed runtime e66ec61e4, authored tools/auditor/tests/memory review dffc315b3, and main helpers75f3df38c. Only origin was pushed. Production recipe changes are inherited integration changes, not local edits.
- Frozen tested integration: af09f0a2bfd32f2ecc29bda6a71a1de42bcf2b34, basee17af64a. Source review CLEAR.
- Intermediate current merge daabb0dba96e55a047fda9135e5fb9aad91d1c4f built as dd23daabnowrW: ELF879a1a9916926f9a..., missing0, all14overlays linked, end8c44e698. All14overlays exactly match af09 ON; raw main programme differs by21bytes, exclusively three QA source labels. This does not establish the newly enabled eb1 recipe's gates.
- SCENERY_REPLAY_LEAN0 source review CLEAR. Combination=1 is not qualified; require a reused/fresh emitter transition test before enabling it. No confirmed incompatibility or permanent guard is needed.

## Actual af09 gates

- OFF image af09 vs e17 after objcopy-R.stack:3655e448838402af86097f8cf848e5f35b0f81312b1805dd003348edb31fc050.
- ON reproduction identity:f23774e1ae98c9b30c107ed34d3ec5a3e5cf78c03d38c4622fd158d9e72323c7.
- Crossr101, farmr103, forestr100 tick330:0of307200 pixels differ, no masking. PNGs inspected and hashed.
- KOS48fight contiguous:held49152,minheadroom6056,largest3904; fragmented:held49152,minheadroom6120,largest3136. Both pass the existing total-headroom>=4096 criterion, no OOM/HALT/FAULT/MISSING, alert reached.
- TEXCHK5/5logs pass; CAST-GC125censuslines/7room-modelrows,0unallowedGC/MIXED; NOT-DRAWN59alivelistlines,0alive-neverdrawn; LEON-GC3/3pass.
- GDEMUgdemu profile, jitter20000, seed1:r101->r103 reached,0badreads/stops, alternatepackages admitted in both rooms.
- Instrumented post-ambush s30 fragment:340/340 uploaded/presented, restored1, heap119136. Ordinary fragment matched Off/On140448.
- Full canonical H2 Off/On: all s03(1465),s20(571),s30(340) frames uploaded/presented, restored1; s30heap40352 both. Same warp/pad wire hashes and programme/data profile. User approved one pair with240s limits; actual host runs ended59.7/56.6s. This is fixture route coverage, not a full release/no-warp check or console performance.

## Confirmed test-profile issue, not floor acceptance

The ordinary QA rW programme includes PC_SAMPLER1, QA_MENU1, WORLD_METER1 and other diagnostics. Existing e17 standard release-gate twin reports s30heap98016. QA OFF's image end is72384B higher, arena fit73728B lower, initial heap73824B lower; therefore40352 is not evidence that the recipe's~94KB floor is maintained. Both QA arms matching proves no added dedup heap in that profile only. MEMORY-FLOOR-REVIEW.md pins the retained baseline receipts and source; no invented full ELF hash for the pruned twin.

Next memory qualification must use actual current recipe rP inputs with standard fp_twin reproduction identity enabled, Off/On differing only SCENERY_DEDUP0/3. Keep QA_MENU0/WORLD_METER0/PC_SAMPLER0, existing DBG_WARP1/WARP_JUMP1/TEX_CHECK1/MCHECK_LEONGC1 overrides and exact recipe/data. Do not just remove QA_MENU and keep the other QA diagnostics. C: floor20GiB, reserve before each build/stage; one tree lease, two shared build slots, JOBS1, release priority.

## Media, disk and queued work

Private Off/On standard-layout QA media and NTFS logical bases remain preserved under /root/work/lanes/dedup-offline23-main and C:\Flycast-Evidence\re4-dreamcast\dedup-offline23-20261023. Loader/standard layout lint passed. Final RE4DC-QA23-Dedup pair has not been delivered; memory-profile qualification and current recipe gates remain open.

No files were deleted. Automatic review rejected removal of the shared-cache diagnostic ISO and then two narrower owned raw-track intermediates, returning only blocked by policy. Lossless NTFS compression of the three owned logical ISOs saved623872000B; their byte hashes still match every original track03.sha256. Owned capture executable copies were also compressed. All logs, screenshots, assets, programmes and failed attempts remain. Floor remains a constraint as other jobs use disk.

INBOX I-001 is queued, not started: after dedup completion, estimate offline re-stripification atop dedup at r101/r103/r100 cameras; >=15% fewer submitted corners at the cross, exact triangles/winding, no s30 heap harm. Read fix-r10d-speed23/CLAUDE-STATUS.md first. Its world-builder work is Claude-owned; no shared world-tool edit is claimed by this queued work yet. Keep SELECT_ONLY/SUBMIT_BATCH/REPLAY_LEAN composition and use a default-off option if GO. Final expected pair: RE4DC-QA23-Restrip-{Off,On}-<sha8>.

No production merge, publication, SD copy or third-party message. Physical performance and acceptance remain pending. Backface speed, WORLD_SCRATCH, PVS/actor-wide/castle/cabin/PR56 queues stay closed or parked as the latest handover specifies.
