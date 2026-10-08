# Inventory visual candidates, 2026-10-08

These implemented candidates pass the supplied-save appearance, STRICT and
integrated lamp regression checks below. The measured inventory CPU cost is
recorded below. The exact clean GDI passes the supplied-save regression;
physical-console acceptance remains pending. They are not console acceptance or a release.
The inventory lifetime and lamp fixes at c2fd317a remain the accepted baseline.

## Missing source mask packages

The supplied-save inventory capture requested missing color/mask pairs for the
Yellow Herb case model, the shared Black Bass / Large Bass case texture, and
Yellow Herb Examine. `pieceTblInit` selects the source textures; the model part
headers identify the exact color and mask indices with alpha reference zero.
The separate Green and Red Herb Examine pairs were also absent from the pack.
Fish Examine already had its required pair.

Extended `prepare_inventory_pairs.py` to prepare eight reviewed source pairs
across `ss/eng/ss_pzzl.dat` and the five herb/fish Examine TPLs. The existing
converter, identities, texture format and runtime material path are retained.
Against the current 3,749-entry pack, five packages are added and all existing
entries remain byte-identical. The private candidate contains 3,754 entries,
114,409,472 bytes, SHA256
`8d2d807baddd8e9e82d9fd5c62f3f5a4470f15fd54d20f520ca1cd8b09bce565`.

Readback checks verify every prepared pair's identity, package CRC, dimensions,
layout, source color and mask texel after the established ARGB4444 quantization.
Transparent and partial-alpha texels remain present. Sixteen converter tests
pass. This establishes offline preparation; it does not establish target VRAM
residency, cost, appearance or full inventory coverage.

## Source selection tiles

`pieceFrameDisp` submits animated source color tiles through
`ss_Draw_tile3d_local`, whose GX FIFO writes are discarded on Dreamcast.
A Dreamcast-only adapter copies the same view-space corners, current projection
and viewport, RGBA, blend mode and depth comparison into the existing bounded
native translucent queue at the source OT callback. Both source depth modes
disable depth writes. The accepted model clipper is reused; no texture, new
backing allocator or gameplay change is introduced.

Compiled host checks with ASAN/UBSAN cover projection, near clipping, offscreen
and far rejection, blend/depth, copied packet ownership, spill capacity and
explicit rejection. Another check executes the actual source helper, checks all
copied inputs, and compares the PowerPC-path GX call sequence against the
unmodified baseline for all blend/depth combinations. It also checks the
RE4DC_GAME plus __PPC__ guard. This is not a full ProDG object comparison.

The integrated traced SH-4 build (including the source PowerPC guards and
inventory lines) passes with no unresolved symbols; ELF SHA256
`bfa234cd716135f774956d8d3bef3a7f147dc017ea00d2510bb64eb3a8c3ef57`.
Build intermediates were kept in RAM and archived with a verified per-file
manifest (1,089 files). Persistent output and binaries are on D:.

The source case grid, cursor and corner lines now use the same bounded
subscreen queue. Their source callback retains its endpoints, GX width,
RGBA, blend and depth-test state. Depth clipping and perpendicular strips
reuse the accepted laser approach; laser rendering itself is unchanged.
Host checks cover width, near/far/viewport rejection and callback input binding,
including the unchanged PowerPC-path GX calls. Final visual and CPU-cost qualification follows below.

## Bridge regression

The baseline and integrated candidate both pass a 240-second Flycast fixture:
synthetic placement in r108, normal controller action holds and the source
transition into r109, then continued simulation. ACT_CAP=0; full play payloads
retained, and the same prepared texture pack in both arms. All 3,804 compared
source-state records are STRICT and all 3,804 decisions MUST-IDENTICAL.
No fatal diagnostic, presentation failure or fence timeout occurs.

Both arms report fence_blocked=0. This is a normal-transition regression,
not a target execution of the timeout race or a reproduction of the reported
physical-console failure. The race remains supported by its actual-function
host negative control and pending/completed ownership checks.

The full ISO images were staged in RAM and verified in both namespaces plus
an independent raw reader. Lossless xdelta archives against a retained baseline
were decoded and SHA256-verified before running Flycast through the WSL UNC
path. This changes host storage transport, not disc payloads or emulation.

## Outstanding qualification

The earlier direct-to-disk bridge stage hit the reserved floor before boot.
The RAM/archive workflow above now permits emulator checks without removing
prior images or captures. No physical-console acceptance is claimed.

- Obtain physical bridge and cold-load/walking acceptance before claiming those
  reported console faults resolved. The normal r108/r109 transition fixture
  does not reproduce the reported timeout.
- Verify inventory and lamp behavior on physical Dreamcast hardware.
- Extract the verified full archive to a destination with sufficient space for
  its 1,158,320,103 raw disc bytes. No SD write or binary release is included.

## Reused Examine texture buffer

The first full supplied-save visual run (900.92 seconds) shows the new grid,
cursor lines, changing selection highlight, Yellow Herb foliage and Large
Bass case model. Yellow Herb and Large Bass Examine render. Both inventory
closes restore all 3,145,728 bytes exactly; ordinary movement follows. No UI
drops, missing uploads, VRAM rejects or fatal presentation diagnostics occur.

That same run exposes an additional source-lifetime defect: examining Green
Herb after Yellow uses the yellow texture. Closing/reopening the case and
examining Green first restores its green texture. Both model BIN files have
54,022 bytes, placing their different raw TPL contents at the same addresses.
SsItemExamine bypasses TexRegist, so the renderer's descriptor-to-identity
cache and direct handles retain the earlier item's upload.

The Dreamcast-only publication boundary now calls the existing
re4dc_ui_invalidate_sources API after the new model/TPL reads complete and
before modelInit. It clears source identities/handles and resets draw plans;
source item state, file reads and the PowerPC call path are unchanged.
The compiled actual-key/publication regression fails on the old function and
passes under ASAN/UBSAN with the hook. Repeated same-address overwrites and
the PowerPC guards are checked. All three subscreen host tests pass.

The integrated target rebuild has no unresolved symbols; ELF SHA256
`ad7998c7449e6afc90ce8c6930067afa624c941b7157f1c67ac32ead70791bf0`.
All 1,089 RAM build files are preserved in a decoded/hash-verified archive.
The initial run remains a defect reproduction; the corrected qualification
below supersedes its appearance result.

## Corrected supplied-save and source-state checks

The corrected full-payload Flycast run lasts 901.11 seconds from a cold title
Load of the original, unchanged isolated VMU. It uses no warp or forced case.
The case grid, cursor, changing selection tile, Yellow Herb foliage and Large
Bass appear. Yellow Herb followed by Green Herb Examine within the same case
session now loads each distinct texture; rotating Green keeps its green foliage.
Three closes restore all 3,145,728 bytes exactly. Movement begins after the last
close, with source position changes, before the bounded run ends during the hold.
There is no final after-movement screenshot in this visual run. Large Bass
Examine was reviewed in the preceding run; Red Herb is absent from this save.
No UI drops, missing uploads, VRAM rejects or fatal presentation diagnostics occur.

A separate matched source-clock run compares the accepted c2fd317a baseline
against the corrected integrated build, with the same full payload and prepared
texture pack. The 29 ordinary controller entries load the save, examine Yellow
then Green, close/walk, reopen/close and walk again. ACT_CAP=0 and fast pacing
are identical. All 5,474 unique source frames are STRICT and all 5,474 decisions
MUST-IDENTICAL. All 19,659 raw LT/LU/LX/LP lines are also exactly equal, including
17 duplicate frame records during save loading. The frame-counter jump from
1,207 to 140,131 is the saved counter; it is present identically in both arms.
Both complete room restores pass per arm. The final 101-frame walking window
has 80 distinct positions in each arm, followed by continued r102 simulation.

The integrated lamp fixture lasts 121.25 seconds and retains the flame/smoke
at impact, followed by its fade. All 2,781 common source frames are STRICT and
all decisions MUST-IDENTICAL against the previously accepted lamp fix. Its
existing source-damage placement, god-mode fixture, resident-only sprites and
sprite cap remain; this is not manual shooting or full particle fidelity.

The clean build disables source/decision tracing, debug warp and PC sampling;
ACT_CAP=0 and the accepted play settings remain. ELF SHA256 is
`847ad967fc53d8cd785072ddfc6faf1b120155e2d5b56204f16eefb610f840a1`.
Its 1,085 RAM build files are archived with verified hashes. The new raw GDI
retains all 1,195 payload files, replacing only the program, Sscrn overlay and
texture pack. Both ISO namespaces pass manifest readback. The persistent delta decodes to the exact raw GDI SHA256
`3cc22877afa5682da86289a1a0dc565daf8da510141e8320c5b82da45a40212b`.
A byte-verified RAM copy of the retained baseline avoids slow host-filesystem
random reads during this independent delta decode check. A separate complete
xz archive, split across two drives, is also independently decoded and
SHA256-verified. It needs no older disc. A Windows verification helper checks
all archive parts and all decoded bytes without extracting them.

These are host/Flycast and archive checks, not physical-console acceptance.

## Presentation completion race

The async PVR timed waiter can become runnable with its timeout return before
the render/vblank interrupt completes. By the time the waiting thread resumes,
the frame may already be complete. The fence now rechecks pvr_present_pending
after a negative wait result, mirroring the existing frame-resolution policy.
A truly pending frame still sets the failure and follows the existing fatal
path before another upload. There is no timeout extension or global KOS change.
The actual-function compiled negative control reproduces the false failure;
the fix passes completed, late-completed and genuinely pending ownership cases
under ASAN/UBSAN. The r108/r109 fixture above does not trigger the timed wait,
so this remains a candidate for the reported physical bridge fault.

## Full-change inventory CPU cost

The nominal SH-4 model at 200 MHz compares the accepted baseline runtime and
old texture pack against the integrated runtime and new herb/fish pack. It
cold-loads the same supplied save and uses the same source-clock controller
sequence, ACT_CAP=0, fast pacing and enabled source/decision diagnostics.
Source frames 140810 through 140813 show the open case with Yellow Herb selected.

| Measurement | Baseline | Integrated |
| --- | ---: | ---: |
| Mean modeled CPU milliseconds, four paired drawn frames | 174.988070 | 182.813644 |
| Drawn frames in the 32-tick census | 32 | 32 |
| Skipped frames in that census | 0 | 0 |
| Model-part entries per drawn frame | 109 | 109 |

The full sampled CPU delta is **+7.825574 ms**. All 1,919 common source records
are STRICT and all decisions MUST-IDENTICAL, including the measured window.
Drawn/skip classification comes from actual native UI begin/skip entries.
The new native geometry and submission subtrees account for 1.554883 ms per
drawn frame, excluding IRQ descendants, source-overlay transformation/callback
work, shared deferred drain and additional textured-model work. Submission
alone accounts for 0.773819 ms; it is not the complete cost of the adapters.

This is the cost of restoring visuals, not a speed improvement. The four-frame
sample is diagnostic-build CPU timing, not physical Dreamcast timing, PVR fill
cost, clean-build FPS or a broader inventory/route performance claim.
Clean text grows by 3,072 bytes; data remains 625,076 and BSS 818,140 bytes.
Alignment moves the linked end from 0x8c3dff3c to 0x8c3e1f3c (+8,192 bytes).
No new persistent backing allocation is added by the quad/line adapter.

## Exact clean GDI regression and preservation

The final 301.19-second Flycast run cold-loads the unchanged isolated original
VMU, using ordinary controller inputs through the existing input fixture and
no test files on disc. Leon and the case visuals appear. Yellow Herb followed
by Green Herb Examine within the same case uses the correct foliage, including
rotation. Three closes restore all 3,145,728 bytes exactly (hashes a4b7127e,
dc072798 and ced691d2). Leon then walks, with before/after world captures,
and simulation continues until the bounded run ends. There are no fatal,
presentation, missing-upload, UI-drop or VRAM-reject diagnostics.

The clean GDI retains all 1,195 payloads and contains no warp, automatic
controller, debug-save or forced-crash files. Source/decision trace, debug
warp and PC sampling are disabled. The final run reads both this disc and
its identical emulator/capture files from RAM. Its original VMU is unchanged.
Three earlier capture runs hit the host storage-margin guard and remain
incomplete evidence; the final RAM-capture run completes without errors.
Every capture file is preserved in a compressed archive with per-file hash
readback. The full disc archive also passes an independent Windows decode.

This qualifies the combined image in Flycast. It does not establish that the
reported physical-console bridge timeout or cold-load walking freeze is fixed.
No binary publication, SD write or issue closure is performed by this change.
