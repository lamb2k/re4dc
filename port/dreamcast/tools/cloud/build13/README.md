# Build 13: scenery record split and meshlet-size controls

This is an opt-in physical layout experiment for the PS2 world. It separates
each existing 28-byte meshlet record into a 16-byte emission record and a
12-byte bounds record. Geometry, vertex/pool records, strips, winding,
materials, placements, source IDs and all LODs remain unchanged by this
conversion. The two records still occupy 28 bytes per meshlet before padding.

The ordinary builder's default remains 64 vertices per meshlet. Changing that
existing knob is a separate experiment: the existing greedy packer can change
strip/triangle order. The sweep reports that change explicitly.

The current base already includes Build12. Its local-indexed/direct-strips
flags and their output/report bytes are retained. Combining either with split
`1` fails before source access or output; split `0` preserves their behavior.

## Generate an alternate with the existing world builder

From the repository root:

```sh
python3 port/dreamcast/tools/ps2_world_r4im.py \
  PUBLIC.r4p PUBLIC.inc OUT/ps2-world --scenery-record-split 1
```

The ordinary `ps2-world.re4mesh`, `ps2-world.r4pw` and `ps2-world.json` outputs
are identical to the same invocation without the flag. Extra outputs are
`ps2-world-split.re4mesh`, `ps2-world-split.r4sg` and
`ps2-world-split.json`. The R4PW remains the ordinary policy/placement file.
`--record-split` is an alias, and either name without a value means `1`.
An absent flag or explicit `0` does not import the new converter or add a key
to the ordinary JSON report. No build recipe is changed by invoking this tool.

When an ordinary same-stem `.r4sg` already exists, it must validate against the
newly built ordinary mesh and policy; its exact records are retained. Otherwise
four consecutive, preserve-order groups are generated using the existing
visibility23 policy. This is not the spatial grouping/reordering pass.

For a pipeline that already ran the ordinary `ps2_strip_groups.py` spatial
grouping pass, convert the **actual final ordinary mesh** instead:

```sh
python3 port/dreamcast/tools/scenery_record_split.py \
  OUT/ps2-world.re4mesh OUT/ps2-world.r4pw OUT/ps2-world-split \
  --source-groups OUT/ps2-world.r4sg
```

The standalone command discovers a same-stem `.r4sg` when the argument is
omitted. Without an existing group file, `--groups 1..8` selects the generated
consecutive group count; default is 4. It refuses existing output files and
source/output aliases. Do not run the old v3-only grouping tool on the v4 file.
No alternate R4PW, texture, proof or source-ID file is synthesized.

## Exact binary contract

All integers are little endian. This is explicit **R4IM version 4**, not a
v3 reserved-bit reinterpretation. The header remains 80 bytes (`<4s19I`),
followed by the same 32-byte LOD header (`<8I`). The CRC is CRC32 of bytes
`[80:]`; the size is the complete file extent, including zero padding.

| Header field | v4 meaning |
| --- | --- |
| `version` | 4 |
| `meshlet_count` | Same logical IDs/count as the ordinary source |
| `meshlet_offset` | Emit16 table |
| `reserved[0]` | 2, prelit ARGB1555 |
| `reserved[1]` | Bounds12 table offset |
| `reserved[2]` | Actual ordinary source R4IM body CRC |
| `reserved[3]` | Actual ordinary source file size |

| Table | Serialized record |
| --- | --- |
| Emit16 | `<IIIHH`: first vertex, first strip, strip byte count, vertex count, strip count/flags |
| Bounds12 | `<6H`: min XYZ, max XYZ in the unchanged mesh quantization grid |

Both tables begin on 32-byte boundaries. Bounds must begin at exactly
`align32(emit_offset + 16 * meshlet_count)`. Canonical section order is meshes,
parts, emit, bounds, vertices, indices/strips, palette, part LODs, clusters,
levels, optional classes, optional class rules. All section padding is zero.

The source's indexed flag (`strip_count & 0x8000`), u16 pool-offset tables and
strip bytes are retained verbatim. A plain v2 input is explicitly accepted;
it is never relabeled as v3 to appease a reader. Optional existing classes and
class rules remain verbatim. The runtime uses a separate world-only reader;
the generic scenery `MeshPackage` format remains unchanged.

Canonical **section** order does not require meshlets' `first_strip` offsets
to follow meshlet order. The complete raw index/strip section is copied, with
all original offsets and local remaps retained. A public control swaps two
physical strip spans and their offsets, preserving exact per-meshlet geometry;
the ordinary reader accepts it, and v4 retains its index section exactly.
This avoids assuming Build11's canonical per-meshlet index placement. It does
not claim admission of the owner's private r101/r103 packages; no private
Build13 package or extra-sidecar adapter has been validated here.

## Admission, lineage and sidecars

`scenery_record_split.Package` validates canonical section layout, CRC/size,
prelit encoding, PS2 source owner, source/part ownership, vertices, local and
pool references, strips, bounds enclosure, all LOD ranges/errors, and part
vertex-pool separation before conversion. It requires at most 65,536 logical
meshlets (`Pick.let` is u16). For each part, the sum of the maximum meshlet
count in each cluster's selectable levels must fit that part's meshlet count;
overlapping ranges cannot overrun the runtime's selected-Pick reservation.

The R4PW body CRC, counts, placement IDs and material/placement fields are
checked; its bytes are unchanged. R4SG validation checks the actual mesh and
policy bindings, its internal CRC/extent, every group/strip boundary, corner
range and geometric enclosure. Only the new physical mesh CRC/size bindings
change. The record bytes and their CRC remain identical when an existing
R4SG is supplied. The existing runtime's 262,144-byte R4SG cap applies.

The standalone sidecar registry permits only `.re4mesh`, `.r4pw`, `.r4sg` and
`.json` at the input/output stem. Unknown siblings, including physical proof
formats, fail closed. Source/output alias checks also cover existing hard
links in the builder. A fresh stem is recommended for each experiment.

**Build12/SDS1/SDO3 composition is unsupported.** Nonzero ordinary reserved
lineage/marker words, appended runtime tables and unknown trailing sections
are rejected. Their fields are not reused or overwritten. A combined format
requires a new explicit versioned lineage extension and separate validation.
PVS, room-cell, interior/occlusion and other physical certificates are not
rebound: identical logical geometry does not authorize a new physical proof.
The reader/loader's original-source guards and unsupported runtime feature
combinations are part of the separate runtime lane.

The in-memory APIs have no file/proof side effects:

```python
import scenery_record_split as split
candidate = split.split_package(ordinary_mesh_bytes)
candidate, candidate_groups, report = split.convert(
    ordinary_mesh_bytes, ordinary_r4pw_bytes, ordinary_r4sg_bytes)
```

`split_package` alone does not approve external sidecars. `Package(data,
allow_split=True)` exposes validated header/LOD tuples, logical meshlets,
raw sections and `refs(id)` / `strips(id)` for independent controls.

## Reproduce the public sweep and controls

```sh
python3 port/dreamcast/tools/cloud/build13/layout_controls.py \
  --out /tmp/b13-current-layout \
  --receipt /tmp/b13-current-layout/layout-controls.json
```

The generator constructs a public full-wrapper-v5 source and source INC, then
executes the **real production exporter** in separate processes with limits
32, 64, 128 and 256. The source has three wavy 20x12 grids with opaque,
punch-through and translucent policy, prelit colours, and two placements of
the same mesh. It includes 720 source positions and 2,508 placed triangles;
the unique mesh's LOD0 has 1,254 triangles. No game assets are required.

`fixtures.json` records paths and offsets for all four ordinary/split packages,
the unchanged R4PW and both matching R4SGs. R4SG records start at byte 32,
with four 16-byte records per logical meshlet. Actual C++ `SpanPackage` and
ordinary `MeshPackage` admission are compiled and exercised. The new runtime
reader/selector/target costs are tested by the independent runtime/cost lane.

The control also compares all three ordinary output files byte for byte
against exporter base `9b248c5b40a49e4c954ea834fdf665fdbbc314f0`, using identical
arguments and output paths. Absent split, explicit `0`, and explicit existing
64-vertex default all match, including the JSON arguments. Plain v2, actual
post-spatial-group CLI output, existing preserve-order R4SG generation,
nonsequential strip placement, 21 invalid/stale/unsupported inputs, and minimal
restart parity are covered. Both existing Build12 flags also preserve their
ordinary and alternate output/report bytes with split absent or `0`; the two
unsupported combined-flag cases fail before attempting nonexistent inputs.

## Interpret the evidence

The checked-in `layout-receipt.json` records complete controls and source
hashes. `builder-evidence.md` provides compact tables for the aggregate report.
Counts cover resident all-LOD data and a separately labeled synthetic
all-visible LOD0 frame. Two repeated placements multiply actual per-placement
work; they are not used to inflate unique physical data-line counts.

For each part/cluster/LOD stream the sweep distinguishes raw ordered corner
equality, oriented ordered triangle equality, and an exact oriented triangle
multiset. Cyclic triangle rotations preserve winding; reversal does not.
At limits 32/64/128, LOD0 order differs from 256 in all three parts, including
the translucent part. Those order-changing sizes are explicitly unqualified
for translucent visual equivalence; the existing default remains 64.
Splitting the records **within any one size** preserves every stream exactly.

The strip primitive repeats exactly two corners at a restart and preserves
parity. The sweep's 32-vertex case introduces 33 additional strips and 66
additional corners relative to 256; other sizes introduce no extra strip
segments in this fixture. Meshlet setup counts still differ substantially.

Architectural 32-byte demand-line unions are distinct from the sum of lines
each record independently touches. They are neither cache misses nor measured
cycles. Dense emission sees fewer record lines; selection can read bounds as
well and absorb that difference. Host process wall time and peak RSS describe
conversion only. No console/Flycast/r101 speedup, frame time, world budget or
hardware cache-miss reduction follows from these tools-only measurements.

## Runtime switch and access paths

`SCENERY_RECORD_SPLIT=0` is the default. An absent switch or explicit `0`
adds no compiler flag, object or dependency. The production recipe remains
unchanged. In an explicitly paired experiment, append these overrides to the
same complete game recipe in both arms, then vary only the split switch:

```text
PS2_INTERIOR_CULL=0 WORLD_RECT21=0 FOLIAGE_MIP24=0
SCENERY_RECORD_SPLIT=0  # control
SCENERY_RECORD_SPLIT=1  # candidate
```

Those matched overrides remove consumers of existing physical certificates;
they are not credited to record splitting. Keep `PS2_INTERIOR_ACTORS` at the
recipe value required by `ENEMY_VIS_CULL`. The source policy and textures
must be the matching ordinary, unremapped inputs. An old rect21 remap is not
approved by substituting its original fingerprint.

The switch requires the existing native mesh/LOD/world draw/direct TA/direct
mesh/aligned IO paths, room packages, and scenery chunks. Make rejects the
unqualified WORLD_VERT, SCENERY21_AB, dedup, cone/piece-state, PVS, interior
world culling and WORLD_RECT21 combinations. It also rejects either enabled
Build12 payload switch. The corresponding source guards reject these mixed
modes if someone supplies compiler definitions without Make.

The PS2 world alone owns a `record_split::WorldPackage`. It selects a normal
`room::MeshPackage` or the explicit v4 `SplitPackage`; the generic package's
definition and ABI do not change across translation units. A small
`RecordView` exposes the active representation. Streaming emission reads the
16-byte emit record directly; selection reads the 12-byte bounds record and
fetches emit fields only when vertex-skip accounting or census classification
needs them. Fully inside picks without group tests do not eagerly copy emit
metadata. The existing eager path uses a transient view containing the
16-byte prefix, bounds pointers and logical ID; it never reconstructs or
stores a full AoS table.

Ordinary-record prefix/suffix views use explicitly declared GCC `may_alias`
types, including target compilation with the pinned GCC15.2 toolchain.
They do not depend on an unrelated-type cast being valid under ordinary C++
alias rules. The unchanged vertex gather/transform/clipping/submission
kernels are reused. The 3,072-byte shared gather allocation remains present;
no resident saving is attributed to removing it. The v4 loader allocates no
temporary 28-byte-per-meshlet AoS validation table.

The primary experiment is independent of `SCENERY_EMIT_PREFETCH`. With that
switch enabled, existing hints address the actual emit or bounds table.
The target controls also compile selection-lean2/UV/prefetch composition,
the eager selection/replay/submission configuration, and active Build10
census. Census scopes and input/output counters retain their existing
meaning: Build13 changes metadata access and does not fuse transform and
submission or add duplicate output counts.

## Runtime admission and fallback

The loader tries `ps2-world-split.re4mesh` only when enabled and when the
current owner/movie rules permit it. It reads the actual standard file's
v2/v3 prelit header and extent, verifies the alternate's actual body CRC,
requires explicit v4, then validates its canonical sections and stored
source CRC/extent. A v4 file at the standard filename is refused. A split
format never masquerades as a cached v3 package.

Rooms r11f, r100 and r200 retain the ordinary file when their existing
movie-arena/transition/source-owner exclusions apply. A missing alternate
also retains the ordinary file. A **present invalid alternate rejects the
native PS2 package through the existing fallback path**; it does not silently
reopen and price the base package as a candidate. `SCNSPLIT` logs which
representation was admitted, its physical CRC/extent and emit/bounds offsets,
and the retained gather bytes. Ordinary fallback and candidate measurements
must be distinguished using that admission log.

Only an admitted v4 package requests `ps2-world-split.r4sg`. The existing
mesh CRC/bytes, policy CRC, group counts, size cap and body CRC checks retain
their physical meanings. An additional split-only validation walks the
actual strip data before publishing the borrowed group records. It proves
monotonic complete strip boundaries, local corner ranges, and geometric
enclosure for every referenced corner. A stale or malformed R4SG is freed;
the admitted package continues through the existing whole-meshlet path.
No PVS, hidden-room, texture or owner proof is rebound to a different file.

## Actual-reader and complete target controls

After generating the public `fixtures.json` above, reproduce the bounded
reader controls with:

```sh
python3 port/dreamcast/tools/cloud/build13/check_reader.py \
  --fixtures /tmp/b13-current-layout/fixtures.json \
  --output /tmp/b13-reader
python3 port/dreamcast/tools/cloud/build13/check_reader.py \
  --fixtures /tmp/b13-current-layout/fixtures.json \
  --output /tmp/b13-reader-asan --sanitize
```

Both runs pass 23 cases: ordinary/v4 admission at all four limits, malformed
section/count/colour/extension/emit records, actual body CRC and source
lineage, conservative part-pool ownership, selected-Pick capacity, and
malformed R4SG strip ends, extents, corner ranges, enclosure and physical
binding. Malformed bodies have recomputed CRCs unless the checksum itself
is being tested. These controls execute the actual C++ reader, the actual
source-header predicate, and source-extracted production CRC and R4SG
admission blocks. File IO is a host adapter; disc opening, transition-owner
lifecycles and private packages are outside that fixture. The ASan/UBSan run
disables leak detection because process inspection is unavailable here.

Complete target validation uses real KOS headers, the repository's existing
PVR declaration overlay, generated game headers and the pinned SH4 compiler:

```sh
python3 port/dreamcast/tools/cloud/build13/build_controls.py \
  --output /tmp/b13-target \
  --sh4-cxx /tmp/re4dc-sdk-20261024/rootfs/opt/toolchains/dc/sh-elf/bin/sh-elf-g++ \
  --kos-root /tmp/re4dc-sdk-20261024/kos \
  --sdk-root /tmp/re4dc-sdk-20261024/sh4zam
```

The final gate against base `9b248c5b40a49e4c954ea834fdf665fdbbc314f0` passes
32 complete raw `.ii`/object byte comparisons for absent/explicit-zero split,
covering original production, the matched pair, and both already-landed
Build12 enabled profiles. It passes four enabled profiles, two unaffected
`native_ui` comparisons, and 21 Make rejections. The active-census objects
partially link against the real core with every census hook resolved; the
compiled core has zero FPU instructions. This is complete-TU compilation
and a partial link, not a final game link.

| Primary matched `native_static.o` metric | Split 0 | Split 1 |
| --- | ---: | ---: |
| Executable section bytes | 62,510 | 66,860 |
| Allocated section bytes | 91,358 | 97,026 |
| Zero-fill bytes | 17,067 | 17,067 |
| Largest individual function stack | 8,880 | 8,896 |
| `ps2_open` stack | 592 | 684 |
| Selector stack | 260 | 236 |
| `chunk_emit` stack | 128 | 132 |

Stack values are compiler per-function usage, not whole-call-chain peaks.
Code and static-data growth are real costs of this candidate. The separate
target-cost lane reports setup cycles and architectural memory traffic;
fewer dense emit-table lines do not establish a renderer or frame-time win.
In particular, the dynamic ordinary/split view can increase selection/setup
work. Console cache stalls, full target geometry, TA service time and private
r101/r103 scenes remain unmeasured by these controls.

The committed reader receipts are `receipts/reader-controls.json` and
`receipts/reader-asan-controls.json`. `receipts/target-controls.json` uses
`RE4DC_COMPACT_RECEIPT1`; the existing
`tools/cloud/build12/compact_receipts.py::expand_receipt` losslessly restores
every original metric, command and source hash. Compaction checks exact
parsed-JSON equality and records the full source receipt's SHA256 and bytes.

## Actual-emitter packet controls

```sh
python3 port/dreamcast/tools/cloud/build13/check_emitter.py \
  --fixtures /tmp/b13-current-layout/fixtures.json \
  --output /tmp/b13-emitter
python3 port/dreamcast/tools/cloud/build13/check_emitter.py \
  --fixtures /tmp/b13-current-layout/fixtures.json \
  --output /tmp/b13-emitter-census-asan --sanitize --census
```

The fixture reuses Build5's controlled texture/TA/SQ sink and extracts the
current production gather, transform-call, clipping, replay and submission
bodies. The record-member guard and R4SG admission block are also extracted
from production source. Every comparison uses `TA_HASH=0` and compares all
packet/accounting words, work counts, and balanced SQ ownership within the
same meshlet limit: split-off ordinary versus enabled ordinary fallback and
enabled v4. No packet identity comparison is made between different limits.

The primary matrix covers all four limits, all three passes, all four LODs,
and thirteen scenarios: inside, near/far clipping, offscreen rejection,
single and multiple retained group ranges, no retained groups, low packet
tail, mirrored/nonuniform transforms, absent groups, and sparse picks.
Fully inside cases must emit actual corners at every size/pass/LOD. The
low-tail case proves a reserve refusal **after header submission**, with
one abort and complete SQ release. It is not claimed as oversized-strip
coverage: these authored strips are at most 40 corners, below the existing
borrow path's 64-slot minimum. A further checksum-correct invalid R4SG case
must match whole-meshlet fallback packets and accounting exactly.

| Gate | Layout/fallback comparisons | Original Build5 case comparisons |
| --- | ---: | ---: |
| Normal, five bounded profiles | 1,993 | 390 |
| Primary, active census + ASan/UBSan | 1,249 | 78 |

The normal gate includes the full primary matrix and bounded composed,
select-only-off/UV-off, batch-off and replay-off profiles. The composed and
select-only-off profiles use limits32/256 and LOD0/3; the independent batch
and replay checks use limit64, LOD0/3 and five representative scenarios.
Every profile also runs the original 78 cases. The primary census gate
links the real Build10 core and verifies actual packet/header counts,
the error on the refused draw, and the exclusive phase partition.

Selection and queued camera/placement snapshots are controlled inputs in
this host sink. The separate SH4 cost lane executes the actual selector.
Portable host floating point does not prove target FTRV/FSRRA, game visuals,
owner transitions or console frame time; the synthetic census clock is
accounting evidence only. No additional runtime or geometry change was
needed to pass these controls.

The complete compact receipts are `receipts/host-emitter.json` and
`receipts/host-emitter-census-asan.json`; both use the lossless receipt
encoding described above and bind the final runtime and fixture hashes.

## Target traffic and cycle evidence

[Target-cost evidence](target-cost-evidence.md) contains reproduction commands,
the complete 25-case warm table, representative cold-I and demand-traffic
figures, code/stack costs and the explicitly MODELLED six-part setup scenario.
The full lossless receipts are `receipts/cost-build.json` and
`receipts/target-costs.json`; scenario arithmetic is also recorded in
`receipts/modelled-scenario.json`. The emit-field consumption probe is reported
separately from production selection/replay and is excluded from the frame
scenario. Geometry, D-cache stalls, memory-bus/SQ service and console event
qualification remain outside that target fixture.
