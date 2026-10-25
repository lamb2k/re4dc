# Build 11 — world Blender identity foundation

Date: 2026-10-24. Branch: `codex/world-blender-roundtrip-20261024`.
Base: `057e00a248c9ed473d0b3377a0ce14b0b2f5186d` (`origin/t15/int`).

**Status: PASS for the tools-only identity foundation.** Three public fixture
bundles completed an actual Blender import, save, process exit, reopen,
scene-validation and export with byte-identical output. Every supported
companion was regenerated and checked. No game asset, render-world geometry,
texture, collision, gameplay, or runtime code changed.

Implementation and reproducibility instructions are in
[`world_blender_roundtrip/README.md`](../../tools/d367/world_blender_roundtrip/README.md).
The machine-readable evidence is
[`receipt.json`](../../tools/d367/world_blender_roundtrip/receipt.json).

## What this establishes

The existing R4IM v3/prelit and R4PW v1 record definitions now have a strict
identity bridge into a real Blender scene. It preserves source mesh/part and
placement identities, all LODs, triangle strip order/winding/degenerates,
indexed shared vertex pools, texture keys, pass/cull state, UVs and prelit
colors. Scene vertices, loop attributes, materials, affine basis points, and
identity records are validated against the independent input package. The
serializer reconstructs records and checksum-bound tables; it does not just
extract a saved copy of the original binary.

This makes the no-change foundation reviewable before any manual shell edit or
simplification. Identity mode intentionally rejects an edited scene. A later
geometry change still requires protected-feature checks, all dependent data
regeneration, lost-part and visual acceptance, and hardware measurement.

## Pins and controls

| Control | Observed result |
|---|---|
| Blender | **4.4.3**, build **802179c51ccc**, official Linux archive. |
| Archive SHA256 | `8d3be07d2bc412b502c6bfe3cfe3e22195a4164076867da987ce148d73c27946` |
| Executable SHA256 | `2de8d1e2d358e52f88ecb18a31439a4f12da5858c82218e91fa8b4e6cdb365f6`, unchanged before/after validation. |
| Real save/reopen | **3/3 byte-identical bundles**, separate Blender import/export processes. |
| Actual scene mutations | **43/43 rejected**, including position, UV, prelit color, quantized fields, winding, LOD, identity, affine basis, material keys/nodes/settings, added/deleted geometry and modifiers. Restored scene still passes. |
| Host binary controls | **11 test methods pass**, including corrupt/stale dependencies and unknown/unsupported schemas. |
| Runtime layout acceptance | Current `MeshPackage::adopt(..., true, true)` accepts all 3 exported meshes in a compiled host fixture. No SH4/KOS timing is claimed. |
| Default/absent-tool path | No Makefile or pipeline integration. Existing converter and dependencies match upstream **057e00a248c9ed473d0b3377a0ce14b0b2f5186d**; its public converter fixture is byte-identical. |

The final publication-tree gate was executed on upstream
`057e00a248c9ed473d0b3377a0ce14b0b2f5186d`, including the unchanged-builder
comparison at that same commit. Only new tool, fixture, documentation and
receipt files belong to this build.

## Host conversion measurements

These are actual measurements on the host in the receipt, including Blender
startup and file I/O. Peak RSS is the child process's observed maximum. They are
not Dreamcast frame times and do not project full-room authoring memory use.

| Public fixture | Package input/output | Saved blend | Import wall | Export wall | Import/export peak RSS |
|---|---:|---:|---:|---:|---:|
| Rich current companion versions | 4,501 B / 4,501 B | 511,290 B | 0.680 s | 0.477 s | 282,536 / 268,424 KiB |
| Rich legacy VIS/OCCL/FSH versions | 4,469 B / 4,469 B | 511,290 B | 0.635 s | 0.548 s | 268,816 / 264,280 KiB |
| Existing converter fixture | 996 B / 996 B | 413,431 B | 0.511 s | 0.438 s | 273,548 / 258,116 KiB |

The rich geometry has 2 meshes, 3 parts, 6 meshlets, 15 stored vertices, 3
placements, 3 clusters and 6 LOD records. The existing-converter fixture has
1 mesh, 1 part, 2 meshlets, 25 stored vertices, 1 placement, 1 cluster and 3 LOD
records, including an empty coarsest level. These are deliberately small public
controls, with no private r101 source data or images.

## CRC dependencies and proof boundary

The explicit companion registry supports R4ID, R4TC, R4SG, R4PV, PCL1, R4OC,
R4RC, FSH1 and the existing PS2 world builder JSON report. R4RC has explicit
adapters for SRCB, GRID v1, VIS v1/v2, OCCL v1/v2, SCNK v1, SCDD v1, SCCN v1 and
SCPS v1. Bindings, section extents, internal checksums and record structure are
checked before output. Strip-group bounds are rebuilt from unchanged geometry;
SCDD uses the existing generator; SCPS initial slots and container CRCs are
regenerated. Every accepted result must still match its input bytes exactly.

Existing visibility and occlusion proof payloads are inherited unchanged. The
tool does not certify geometric coverage, issue PVS23 certificates, manufacture
source provenance, or generate a lost-part PASS. Original external source/SAT
hashes and compiled guards remain inherited dependencies. Uncertified input
does not become certified. This identity-only rule cannot be used by a
geometry-changing converter to update bindings around an old proof payload.

An unknown file/room section/version, stale binding, malformed field,
noncanonical padding or unsupported R4IM extension rejects the whole bundle.
Known alternate SDO3/SDS1 representations and appended runtime impostor/texture
tables are explicit unsupported cases. The independent far-shell companion is
validated and reproduced, not converted into new editable R4IM scene geometry.

## Target cost and next acceptance boundary

The build adds **0 SH4 cycles, loads, stores, demanded 32-byte lines, executable
bytes, stack bytes, main RAM bytes or VRAM bytes**. There is no target code or
runtime integration, and accepted world files are byte-identical. Warm- and
cold-I target cycle deltas are both zero. The **MODELLED whole-frame delta is
0 ms**; Build11 claims no r101 speedup.

The bridge uses `(x,-z,y)/1000` metres, `(u,1-v)` UVs, original strip parity and
float32-validated scene attributes with exact raw quantization metadata. It
represents full source affine placement through explicit basis points and
placed geometry, preserving shear/reflection that ordinary Blender TRS
decomposition could lose. Displayed geometry is duplicated across placements;
large-room authoring residency remains unmeasured. The preview uses prelit
vertex color and preserves texture keys without loading private images, so
this build is not a visual-look approval.

All generated binary packages, `.blend` files, host executables and logs stayed
outside the repository. Only public source, synthetic fixture generators,
documentation and the compact evidence receipt are intended for publication.
