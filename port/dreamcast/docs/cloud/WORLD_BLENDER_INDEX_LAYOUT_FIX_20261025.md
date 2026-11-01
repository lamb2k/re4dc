# World Blender index-layout adapter

Date: 2026-10-25. Branch: `codex/world-blender-index-layout-20261025`.
Validation/publication base: `9c2c83dba00ba219fbb135503aa508975fe4855c` (`origin/t15/int`).

**Status: PASS_PUBLIC_INDEX_LAYOUT_IDENTITY_ONLY.** The public append failure
is fixed and the complete public gate passes. This is an explicitly invoked,
default-off authoring-tool fix. It does not reduce geometry or change runtime
code. Private r101 admission remains an owner check.

## Problem and reproduced cause

The owner reported that Build11's Blender codec refuses the shipped r101 mesh
with `noncanonical index placement` before constructing a scene. The codec
assumed each meshlet's index span follows the preceding meshlet immediately,
apart from the one-byte alignment needed before an indexed pool table.

The existing [`ps2_world_append.py`](../../tools/ps2_world_append.py) writer
aligns concatenated index tables to **four bytes**. Its `append_tables()`
preserves all base offsets and rebases the added records by that aligned table
size. The actual runtime [`MeshPackage::adopt`](../../room/instanced_mesh.hpp)
validates each stored offset and does not impose the codec's sequential-order
assumption. The subsequent [`ps2_strip_groups.py`](../../tools/ps2_strip_groups.py)
pass rewrites commands in place, preserving those offsets and padding.

Using the real append parser, append function, serializer and policy writer on
public synthetic input reproduces the exact refusal:

| Field | Value |
|---|---:|
| Base index table | 66 bytes |
| Append alignment padding | 2 zero bytes |
| First appended plain meshlet index offset | 68 |
| Original codec / option absent / option zero | `noncanonical index placement` |

This establishes a concrete cause in the actual public writer chain. It does
not establish that the private room has no other unsupported feature or
companion issue. The separate remapped-policy/source-CRC problem remains
subject to the existing original-policy control or provenance workflow.

## Change and supported contract

`blender_bridge.py` gains **`--preserve-index-layout [0|1]`**, default **0**.
The enabled option is required on both import and export. It accepts existing
disjoint meshlet command spans at their original offsets, including a physical
order different from meshlet order, and preserves the exact declared index
table byte count.

The serializer reconstructs each span from the typed pool offsets and strip
commands. Pool bytes and strip bytes are one interval. It sorts intervals for
overlap checks and writes each reconstructed interval into a zero-filled table
of the original size. No original index blob is stored in the scene or copied
through as an opaque payload. Prefix, interstitial and suffix bytes must all be
zero where no interval owns them.

Full and partial overlaps, aliases, nonzero unclaimed bytes, odd indexed starts,
invalid references, malformed strip lengths/counts and out-of-bounds spans are
refused. Outer section layout, alignment and padding retain their existing
canonical checks. Unknown format extensions remain unsupported. The SDO3
sharing writer is outside this adapter's contract; ordinary runtime acceptance
of a broader layout is not permission to pass unknown data through the bridge.

Enabled scenes use `re4dc.blender.identity-index-layout/1`. The only additional
layout metadata is `index_layout.index_bytes`; offsets remain in their existing
meshlet records. The original source bundle is loaded independently at export,
and its schema, complete source-file hashes, layout metadata, records and
geometry are checked before any destination is written. Changing import/export
mode cannot reinterpret an existing blend. Default-mode blends retain the
original schema and can still be exported in default mode.

The existing companion registry and validators are unchanged. Accepted mesh,
policy and every registered companion must regenerate byte-identically.
Unknown companions, stale bindings and unsupported representations still stop
the whole operation. No visibility, lost-part or provenance certificate is
issued, rebound or relaxed.

## Validation

The final reproducible gate is documented in
[`world_blender_roundtrip/README.md`](../../tools/d367/world_blender_roundtrip/README.md).
The complete machine-readable evidence is
[`index-layout-receipt.json`](../../tools/d367/world_blender_roundtrip/index-layout-receipt.json).
The gate uses pinned Blender **4.4.3**, build **802179c51ccc**, with the original
official archive and executable SHA256 pins. It covers:

- the unchanged Build11 baseline, its three public bundles and all registered
  companion formats;
- real append boundaries for all four byte residues, with plain/indexed starts;
- actual append followed by the actual strip-group command;
- reordered disjoint spans and zero prefix/interstitial/suffix gaps;
- real Blender import, save, process exit, reopen and export;
- complete output identity, baseline-blend compatibility and source immutability;
- malformed binary inputs, incompatible modes and actual Blender scene edits;
- the current runtime reader on exported synthetic meshes, in a host executable.

| Gate | Observed result |
|---|---|
| Original Build11 suite in default mode | 3 real round trips, 43 rejected scene mutations, 11 host test methods; all pass |
| Canonical bundles with option absent / 0 / 1 | 3 fixtures × 3 modes = 9 complete byte-identical round trips |
| Old baseline blends exported by the new bridge | 3 fixtures × absent / 0 = 6 byte-identical exports |
| New noncanonical layouts through Blender | 5 complete byte-identical import/save/exit/reopen/export bundles |
| New host structural controls | 21 test methods and 61 dynamically counted subcases; no failures/errors |
| CLI refusal controls | 27 pass, including off-mode refusal, invalid values, mixed modes and no overwrite |
| Enabled-mode actual Blender mutations | 57 rejected: all 43 original controls plus 14 layout/source controls; restored scene passes |
| Actual runtime reader on current exports | 14 meshes accepted by host `MeshPackage::adopt(..., true, true)`; the original gate separately admits its 3 |
| Source/input/executable immutability | Pre/post hashes agree |
| Existing converter/writer/runtime dependencies | 10 dependency files byte-identical to the pinned baseline; no runtime/build changes |

The five new bundles each contain mesh, policy, R4ID, R4TC, R4SG, an all-visible
PVS, a cell with no portals, empty occluders and a synthetic builder report.
Every file is generated for public synthetic geometry and remains identical
after export. No production proof is rebound. The existing rich fixtures
separately retain coverage of the room container and far-shell versions.

The enabled Blender mutation controls run on a canonical rich input using the
new schema; the five noncanonical inputs separately prove real save/reopen
identity. They are distinct claims, not an assertion that every negative was
rerun on every fixture. The host runtime reader uses only the filesystem type
declarations needed to compile; it calls no KOS filesystem function and is not
a Dreamcast execution result.

Measured host process costs, including Blender startup and file I/O:

| Public fixture | Input/output bytes | Saved blend bytes | Import wall seconds | Export wall seconds | Import/export peak RSS, KiB |
|---|---:|---:|---:|---:|---:|
| Append, plain first meshlet | 4,118 / 4,118 | 652,137 | 0.469015 | 0.371871 | 292,484 / 279,236 |
| Append, indexed first meshlet | 4,118 / 4,118 | 652,459 | 0.399362 | 0.353828 | 291,796 / 283,264 |
| Append followed by strip groups | 5,510 / 5,510 | 793,120 | 0.417348 | 0.359373 | 293,320 / 279,968 |
| Reordered disjoint spans | 2,726 / 2,726 | 511,175 | 0.416898 | 0.322922 | 275,912 / 267,960 |
| Zero prefix/interstitial/suffix gaps | 2,726 / 2,726 | 511,175 | 0.422073 | 0.337139 | 284,020 / 270,052 |

The largest new fixture has 6 meshes, 9 parts, 18 meshlets, 45 stored vertices
and 9 placements. These small controls do not establish full-room memory or
conversion time. No generated binary asset, executable, capture or blend is
included in the commit. The receipt records complete file and source hashes,
commands, process results, timing, RSS and explicit limitations.

## Traffic, cycles and frame impact

This is a host authoring adapter. The game sources, target headers, Makefiles,
linker inputs, runtime defaults and recipe are unchanged. Every accepted world
file is byte-identical before and after the round trip.

| Target delta | Value | Basis |
|---|---:|---|
| Warm-I / cold-I SH4 cycles per piece | 0 / 0 | No target code or accepted data changes |
| Loads / stores | 0 / 0 | Same runtime and package bytes |
| Demanded 32-byte data lines | 0 | Same addresses and data layout |
| Executable / stack bytes | 0 / 0 | No target build integration |
| Main RAM / VRAM | 0 / 0 | Same runtime and accepted data |
| **MODELLED whole-frame delta** | **0 ms** | Architectural identity deduction, not a hardware run |

These zeros are a scope/identity conclusion, not a new target benchmark. Host
conversion times and peak RSS are measured separately and include Blender
startup and file I/O. Small public fixtures do not predict full-room authoring
time or memory. No console, emulator, gameplay-STRICT or performance acceptance
is claimed for this tool-only change.

## Owner hand-back

Run the commands in the README against the complete qualified original-policy
r101 bundle, with the new option enabled on both import and export. Keep all
companions and the original source bundle. Record every input/output hash,
successful runtime admission, Blender import/export time and peak memory.
The full bundle must remain byte-identical.

If another unsupported layout or dependency is found, retain the refusal and
report its exact field and public structural description. Do not canonicalize
the production room, drop a companion, or rebind a proof to bypass the identity
gate. Intentional reconstruction is a later step with its own source-feature
mapping, lost-part, visual and hardware acceptance under the World 2 ms plan.
