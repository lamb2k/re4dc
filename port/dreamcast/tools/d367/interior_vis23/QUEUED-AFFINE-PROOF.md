# Captured affine provenance for PVS source receipts

Runtime fix: `5576aea29`, on `wip/interior-vis23-runtime-20261023`, based on
`831a2115e78e762f5a14886e3b1a4b17dbf9fab1`. This is a correctness fix inside the
existing default-off PS2_PVS feature. No knobs, queue fields, allocation, source
state, actor wall cut, target visibility indexes, base offsets or geometry are
changed.

## Invariant

At the actual affine selection, a source receipt gets placement `i` only if
`RE4DC_PS2_AFFINE == pl.affine`. A moved selection points at local
`moved_affine`, gets `~0U`, and carries that sentinel in the existing queued
placement member. Both SELECT_ONLY and legacy ChunkPart paths and direct
MeshDraw use that captured identity. Queue replay already transfers the
identity to its emitter and resets pending observations for each context.

This authenticates the immutable baked geometry actually captured. It does
not attempt to infer that geometry from fresh dynamic-slot state during
emission. A later bind/cache reset cannot turn a queued moved matrix into a
valid baked panel. A baked matrix captured before a later rebind remains baked.
The existing fresh source predicate remains independently conservative.

## Reproducible host controls

From the repository root in WSL:

```text
python3 port/dreamcast/tools/d367/interior_vis23/check_queued_affine.py \
  --evidence /mnt/c/Flycast-Evidence/re4-dreamcast/interior-vis23-20261023
```

Compiler inputs, copied header and executables exist only in a temporary
`/dev/shm/queued-affine-*` directory and are removed on exit. Evidence contains
only small JSON source excerpts/results, no private game coordinates/assets.

The runner extracts these current production bodies without editing their
logic: the whole dyn namespace including query; placements_intact; selected
affine/provenance block; all three identity assignments; replay identity;
MeshDraw pvs_observed, pvs_finish and chunk_restart; proof sources/sync,
observe/commit/can_cut. The full current pvs23_proof.hpp supplies Panel,
Receipts and panel_sent. It compiles each extracted assignment independently
and fails if the expected three paths are absent.

Synthetic boundaries are object/root backing storage, translation-compatible
concat/inverse, scene/material APIs, package/meshlet accessor storage and
rebinding/reset of the real query inputs. Material API refusal is exercised,
but the actual texture-residency implementation is not executed. Admission
table/frame guards are not executed: the fixture seeds a single synthetic
certificate and a qualified proof state to isolate this confirmed discrepancy.
Host FPSCR cannot qualify target arithmetic. These controls are not renderer,
target ABI, SDK, target arithmetic or hardware acceptance.

## Results, 2026-10-23

G++ 13.3, C++17, O2, Wall/Wextra/Werror. Four lean/root-pose combinations pass:

| WORLD_LEAN | ROOT_POSE | Assertions |
| --- | --- | --- |
| 0 | 0 | 75 |
| 0 | 1 | 127 |
| 1 | 0 | 75 |
| 1 | 1 | 127 |

For every identity assignment, normal and enabled single-root controls query
while moved, restore fresh rest in the same frame, and establish that the
actual placements_intact and healthy panel_sent both pass while actual query
still supplies its cached moved delta. An explicit old-index control observes,
commits and permits actual can_cut. The patched moved capture does none of
those, including after same-ID rebind/cache state zero. Stable-rest,
unbound-baked, normal serial-reuse baked, and baked-capture/later-rebind
controls still qualify.

Emitter reuse covers moved sentinel, baked index, empty context and aborted
submission. Other exercised refusals include cached hidden/source hierarchy,
changed part pose, root refusal/absence/nonfinite matrix/serial reuse,
hidden/area/gate sources, missing package, material refusal, closed scene,
next frame, scene transition, package generation, key change, clipping,
missing/reversed triangles and oversized strips. Source failure clears actual
committed receipts. Key/scene/generation controls exercise Receipts and sync,
not a simulated target frame_guard or real movie transition.

Each of three separate mutation controls restores only its own assignment to
old `i`, compiles successfully and fails the moved-queue no-cut assertion.

The runner also preprocesses the full native_static.cpp text for PS2_PVS=0,
across dynamic on/off, lean on/off and select-only on/off. Each of eight
outputs matches the base byte for byte. SDK includes are removed identically
and all other RE4DC conditions are explicitly defaulted off for this host
source comparison. This establishes bounded source-preprocessing identity;
it does not establish a target object, ELF or knob-off program-image identity.

Evidence: `queued-affine-host.json` and `queued-affine-excerpts.json` under
`C:\Flycast-Evidence\re4-dreamcast\interior-vis23-20261023`.
Runtime native_static.cpp SHA256:
`7b1f1f471a3c11022850689e1ba216e372f8475a07765f43fa950a58f1d44cf7`.

## Remaining integration acceptance

Independent code/control review and target knob-off program-image identity
remain required. No full target build, SDK initialization, staging, guest run,
performance measurement, console test, recipe change or release was performed
for this bounded host proof. Conditional certificates remain research and
unadmitted until the integrating owner completes its acceptance gates.
