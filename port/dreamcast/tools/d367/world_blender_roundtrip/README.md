# Build 11: strict world ↔ Blender identity foundation

This is an explicitly invoked authoring tool. It does not change the game,
builder defaults, geometry, draw distance, textures, or any runtime option.
The accepted result is the same package bytes after a real Blender save, exit,
reopen, scene validation, and record serialization.

The public gate is **PASS**: three synthetic packages roundtrip through Blender
4.4.3, 43 real `bpy` mutations are refused, 11 host test methods exercise binary
and dependency rejection cases, and the current runtime `MeshPackage::adopt`
accepts all three exported meshes in a host executable. See [receipt.json](receipt.json).
This is not a lost-part, appearance, visibility-proof, Dreamcast timing, or
30-fps acceptance result. No private game asset was used.

The default-off index-placement follow-up is documented below and in
[WORLD_BLENDER_INDEX_LAYOUT_FIX_20261025.md](../../../docs/cloud/WORLD_BLENDER_INDEX_LAYOUT_FIX_20261025.md).
Its [index-layout-receipt.json](index-layout-receipt.json) records a passing
public gate: five noncanonical real-Blender round trips, nine canonical mode
round trips, six old-blend compatibility exports, 21 host methods / 61 subcases,
27 CLI refusals and 57 enabled-mode Blender mutation controls. The original
Build11 receipt above remains the historical baseline.

## Reproduce

Use Blender **4.4.3**, build **802179c51ccc**. The official Linux archive is
[blender-4.4.3-linux-x64.tar.xz](https://download.blender.org/release/Blender4.4/blender-4.4.3-linux-x64.tar.xz);
the release checksum list is
[blender-4.4.3.sha256](https://download.blender.org/release/Blender4.4/blender-4.4.3.sha256).
The required archive SHA256 is:

```
8d3be07d2bc412b502c6bfe3cfe3e22195a4164076867da987ce148d73c27946
```

From the repository root, with a newly named work directory:

```sh
python3 port/dreamcast/tools/d367/world_blender_roundtrip/validate.py \
  --blender /tmp/blender-4.4.3-linux-x64/blender \
  --archive /path/to/blender-4.4.3-linux-x64.tar.xz \
  --work /tmp/build11-validation \
  --receipt /tmp/build11-receipt.json \
  --baseline origin/t15/int
```

The host needs Python 3.11 or later, Git, and a C++17 host compiler (`g++`).
Blender's own Python runs the scene bridge. No external Python package is added
to Blender. The host runtime-admission fixture supplies only the `file_t` and
`FILEHND_INVALID` declarations needed by a header; it calls no KOS filesystem
function. This is not a KOS SDK or SH4 compile claim.

`validate.py` checks the archive hash and Blender version/build, records the
executable SHA256 before and after runs, hashes the scripts and existing
converter/runtime dependencies, and checks that neither input bundles nor source
files changed during the suite. A changed or incomplete executable fails the
gate. Generated fixtures, `.blend` files, child logs, and the host executable
belong in the selected temporary work directory, not Git.

To use the bridge separately:

```sh
/path/to/blender --background --factory-startup --disable-autoexec \
  --python-exit-code 1 \
  --python port/dreamcast/tools/d367/world_blender_roundtrip/blender_bridge.py \
  -- import --source /path/to/identity-bundle --blend /tmp/world-identity.blend

/path/to/blender --background --factory-startup --disable-autoexec \
  --python-exit-code 1 \
  --python port/dreamcast/tools/d367/world_blender_roundtrip/blender_bridge.py \
  -- export --source /path/to/identity-bundle --blend /tmp/world-identity.blend \
  --out /tmp/world-identity-export
```

The blend and output directory must not already exist. Export validates before
creating a destination, writes a sibling staging directory, and then renames it.
The original input bundle is required at export: it is the independent source of
identity and quantization expectations. A self-edited text block cannot redefine
what an unchanged scene means. Embedded Python in a blend is disabled.

## Preserve existing index placement (explicit option, default 0)

The public `ps2_world_append.append_tables()` writer aligns each appended index
table to four bytes. Its valid zero padding can be larger than the canonical
bridge's one-byte indexed-pool alignment. A synthetic use of that actual writer
reproduces the owner's `noncanonical index placement` refusal: a 66-byte base
index table gains two zero bytes before the first appended plain meshlet at
offset 68. The runtime reads each meshlet's stored offset independently.

Use `--preserve-index-layout=1` on **both** import and export to preserve that
layout, including disjoint spans stored in a different physical order:

```sh
/path/to/blender --background --factory-startup --disable-autoexec \
  --python-exit-code 1 \
  --python port/dreamcast/tools/d367/world_blender_roundtrip/blender_bridge.py \
  -- import --preserve-index-layout=1 \
  --source /path/to/complete-original-policy-bundle \
  --blend /tmp/world-layout-identity.blend

/path/to/blender --background --factory-startup --disable-autoexec \
  --python-exit-code 1 \
  --python port/dreamcast/tools/d367/world_blender_roundtrip/blender_bridge.py \
  -- export --preserve-index-layout=1 \
  --source /path/to/complete-original-policy-bundle \
  --blend /tmp/world-layout-identity.blend --out /tmp/world-layout-export
```

The option accepts only 0 or 1 (a bare option means 1). Absent and zero retain
the original document/schema, canonical-placement checks and output bytes.
An enabled scene uses `re4dc.blender.identity-index-layout/1`, so changing the
mode at export is refused even for canonical input. Existing default-mode
blends continue to export with the default mode.

This adapter stores only the index-table byte count as additional layout
metadata. Existing meshlet records retain their original offsets. Pool offsets
and strip commands are regenerated from typed, source-validated scene records;
the serializer does not save or return an opaque copy of the index table.
It permits zero prefix, interstitial and suffix padding. All unclaimed bytes
must be zero. Full/partial overlaps and aliases, odd indexed-pool offsets,
out-of-bounds spans, malformed commands, unknown extensions and noncanonical
outer section layout remain errors. Pool bytes and strip bytes together form
one indivisible span. This is a supported subset of standard prelit R4IM v3,
not permission to copy unknown payloads or SDO3 sharing layouts.

The independent input bundle is required on export. Every layout field,
meshlet offset, command, vertex and source hash is checked against it before
writing output. All supported companion files still pass the unchanged
binding checks and must regenerate byte-identically. This option does not
resolve the separate shipped `WORLD_RECT21` source-policy lineage: use the
owner's complete, qualified original-policy control bundle, or a separately
qualified provenance workflow. Never drop a companion or stamp a new CRC
around an unverified proof to make the bundle pass.

The reproducible follow-up gate is:

```sh
python3 port/dreamcast/tools/d367/world_blender_roundtrip/validate_index_layout.py \
  --blender /path/to/blender-4.4.3-linux-x64/blender \
  --archive /path/to/blender-4.4.3-linux-x64.tar.xz \
  --work /tmp/build11-index-layout-validation \
  --receipt /tmp/build11-index-layout-receipt.json \
  --baseline 9c2c83dba00ba219fbb135503aa508975fe4855c
```

Use a new work directory. This gate includes real Blender save/reopen cycles,
the original Build11 suite, baseline-blend compatibility, enabled/disabled CLI
controls, malformed-layout and actual-scene mutation controls, registered
companion identity, and the existing runtime reader on the exported public
fixtures. Its measurements describe the host authoring tool only. Private r101
admission, full-room memory/time and subsequent reconstruction remain owner
checks. Accepted data is unchanged, so this adapter claims no game speedup.

## Format and scene contract

The codec imports the existing structures and strip walker from
[`convert_room_bins.py`](../../convert_room_bins.py). Its default scope is the
canonical standard **R4IM v3**, prelit **ARGB1555** encoding, plus **R4PW v1**
produced by the current PS2 world pipeline. The explicit index-placement option
above broadens only the index-table layout. Sections, offsets, 32-byte alignment, zero padding,
every record, strip command, pool remap, class/rule table, and both checksums are
regenerated. The original binary is not stored in a text block or returned as
the exported mesh. Unsupported layout, unrepresented vertices, unknown header
fields, nonfinite values, and unsupported extensions fail closed.

The imported scene uses this schema:

| Scene data | Meaning and validation |
|---|---|
| `mesh.NNNNNN` empty | Source mesh/bin/common/owner/count/flags identity; origin, step, and bounds as original float32 values. |
| `part.NNNNNN` empty | Source part offset/size/texture/alpha/flags, meshlet range, and UV quantization parameters. |
| `cluster.NNNNNN`, `level.NNNNNN` empties | Every cluster and every LOD, including empty coarsest levels, with bounds, ranges, and original error values. |
| `placement.NNNNNN` mesh | Four explicit affine basis points plus the original source mesh/placement identity and 3×4 matrix fields. |
| `draw.PPPPPP.MMMMMM` mesh | One actual triangle mesh per placement/meshlet, including every LOD and every local pool vertex. An unplaced source mesh is represented once in model space. |
| Point integer attributes | `r4_qx/qy/qz/qu/qv/argb1555` and `r4_vertex_id` retain the exact stored grid, UV, prelit value, and shared-pool identity. |
| Loop attributes | `uv` and `prelit` are actual Blender UV and float-color layers, independently checked against the stored corner identity. |
| `material.NNNNNN` | Original CRC/FNV key, dimensions, pass, cull mode, texture index and vertex-alpha byte; actual assignments and shader settings are validated. |
| Scene identity properties | Schema version, the SHA256 of every bundle member, palette, class/rule tables and part-to-cluster mapping. |

Source millimetres map to Blender metres as **`(x, -z, y) / 1000`**. This is an
orientation-preserving rotation, so it does not reverse winding. UVs become
**`(u, 1-v)`**. ARGB1555 color channels become their exact 5-bit value divided by
31, with alpha 0 or 1, in a `FLOAT_COLOR` corner attribute. No new lighting or
normal encoding is introduced. The preview shader emits these vertex colors;
it does not load private texture images or claim textured visual equivalence.
Texture identity remains explicit and unchanged in the material fields.

Blender object transforms use translation/rotation/scale decomposition, which
does not represent every affine shear exactly. Placements therefore use four
actual basis points and retain validated raw matrix fields; draw vertices have
the full source affine baked into their displayed positions. This covers shear,
reflection and nonuniform scaling without silently changing the source matrix.
All object transforms themselves must remain identity. The authoring cost is
duplicate displayed geometry for repeated placements; no production-room memory
or editing-speed claim has been made.

Every source strip is expanded in its original order. For triangle `k`, even
parity is `(s[k], s[k+1], s[k+2])` and odd parity is
`(s[k+1], s[k], s[k+2])`. Degenerate restart/parity triangles stay represented.
The original strip commands and pool mapping are checked as well as every
triangle's loop order. No Blender triangulation modifier, weld, remesh,
decimation, normal repair, or automatic geometry validation is allowed.
Higher LOD objects are hidden in the initial preview, but all remain present and
are validated and serialized. Their visibility flags cannot be used to remove
them from the export.

The exporter checks actual coordinates, UVs and color values against the exact
float32 values the importer wrote. There is no tolerance that could absorb an
edit. Raw quantization fields are also checked against the independent original
package. They are needed because different 16-bit grid/UV values or affine
values can become the same displayed float32 value; reconstructing solely by
rounding Blender coordinates would lose source bits. Reassembled vertices come
from these validated scene attributes, and record fields come from validated
scene identity properties. Every shared copy must agree. The complete serialized
mesh and policy must finally equal the original bytes.

Geometry, topology, winding, source identity, UV, color, object transforms,
placement basis, materials, nodes, modifiers, shape keys, animation, added or
missing data, extra attributes and LOD changes are refused. UI selection and
node-editor positions are not geometry or material parameters. **Identity mode
has no accepted-edit path.** A future authoring/change mode needs its own
quantization, feature protection, dependency regeneration and acceptance gates.

## Companion registry and proof boundary

The directory inventory is strict. Every member must be a required world file
or an explicitly registered companion, with a supported version and layout.
Unrecognized files, symlinks, directories, unknown room sections and stale
bindings stop the whole operation. Do not remove a dependent file merely to get
past this gate; add and qualify its adapter first.

| Companion | Identity-only work performed |
|---|---|
| `ps2-world.r4pw` | Rebuild part policy and placement records, counts and body CRC. |
| `ps2-world.ids` / R4ID | Validate count, source field range and original policy CRC; preserve source ID bytes; regenerate header and zero padding. |
| `ps2-world.r4tc` / R4TC | Validate classifier version, part count, classes, original policy CRC and class CRC; regenerate both checksum fields. Classification labels are inherited. |
| `ps2-world.r4sg` / R4SG | Validate original geometry/policy binding, groups and payload CRC; regenerate each existing consecutive group's exact bounds, local index range and strip-end offset from unchanged geometry, then regenerate checksums. No reordering pass is run. |
| `ps2-world.pvs` / R4PV | Validate world binding, placement→part→cluster instance count, grid/cell/set structure, bit extents and padding; reserialize records and current bindings. Existing visibility bits remain identical. |
| `interior.cell` / PCL1 | Validate world binding and cell/portal ranges; reserialize fields. Compiled room/near/outer constants are unchanged, not newly generated or certified. |
| `ps2-world.occl` / R4OC | Validate world binding and finite occluder records; reserialize records and bindings. |
| `room.r4rc` / R4RC | Validate header/directory/section extents, canonical layout and payload CRC. Rebuild each registered section and the container CRC. Details below. |
| `far-shell.fsh` / FSH1 v1/v2 | Validate its independent CRC, materials, groups, vertex/strip ranges and payload; reserialize and regenerate its CRC. This separate representation is an unchanged companion, not newly editable R4IM scene geometry. |
| `ps2-world.json` | Parse the existing builder report schema; verify actual world counts, lengths and SHA256; regenerate its canonical JSON. External source/INC hashes remain inherited provenance. |

The R4RC section registry covers **SRCB, GRID v1, VIS v1/v2, OCCL v1/v2, SCNK v1,
SCDD v1, SCCN v1 and SCPS v1**. SRCB world entries must match the actual input
file lengths and SHA256; external SAT identities are retained without claiming
that absent private source data was checked. GRID collision data is parsed,
range checked and reproduced identically. VIS/OCCL structures and policy
bindings are checked; no new hidden-area assertion is made. SCNK point mappings
must reconstruct the source meshlet positions. SCDD is regenerated by the
existing `scdd_compile.scdd` generator, including its indexed-pool overlap guard.
SCCN requires its actual strip-group dependency and matching world/group
identity. SCPS is regenerated with zero initial runtime slots. The room's render
sections require exact R4IM and R4PW SRCB dependencies.

**A matching CRC is not a visibility proof.** Build11 preserves all accepted
input/output bytes, so existing PVS23 certificates, runtime fingerprints,
occlusion assumptions, SAT/source provenance and compiled portal constants are
neither invalidated nor newly endorsed by this tool. It issues no certificate,
lost-part result, or geometry PASS. An originally uncertified PVS remains
uncertified. Geometry-changing builds cannot reuse this identity-only permission
to update bindings or retain a stale proof payload.

Known unsupported representations are explicit: SDO3 offline-dedup alternates,
SDS1 direct-strip variants, normal-lit color modes, other R4IM versions, and
appended runtime impostor/texture tables. They require separate adapters and
fixtures. New versions and unknown fields are never copied through silently.

## Evidence and limits

`fixtures.py` constructs two rich public bundles and a third bundle from the
unchanged actual `convert_lod` function. They cover indexed/plain meshlets,
shared pools, all passes/culls, source identifiers, several placements, every
LOD, empty coarsest LOD, strip parity and degenerates, UV/color seams, ARGB alpha,
signed zero, quantization rounding and affine shear/reflection. Rich bundles
exercise every supported companion and both legacy/current VIS/OCCL/FSH
versions. Their visibility sets allow everything and their occluder lists and
cones make no hiding assertions.

`test_identity.py` rejects corrupt CRCs, stale binding fields, unsupported
markers/extensions, bad versions/ranges/quantization, nonzero padding, unknown
inventory and stale room source metadata. `blender_controls.py` performs 43
actual scene mutations, reopens the pristine blend between cases, and proves
that a final restored scene still exports identically. `validate.py` also
compares a public fixture produced by the existing converter at upstream
`057e00a2` with the current converter and checks the tracked dependencies are
unchanged.

The committed receipt records fixture and output hashes, source hashes, actual
Blender process wall/CPU time, peak host RSS, and blend/package bytes. These
small fixtures measure the conversion tool and process startup; they do not
predict a complete r101 Blender scene's memory footprint or conversion time.

Runtime delta is **0 cycles, 0 loads/stores, 0 demanded 32-byte lines, 0 executable
bytes, 0 stack bytes, 0 main RAM and 0 VRAM**: the tools add no target code and
accepted output files are identical. The modelled world-frame delta is **0 ms**.
No console or emulator performance improvement is attributed to Build11.
