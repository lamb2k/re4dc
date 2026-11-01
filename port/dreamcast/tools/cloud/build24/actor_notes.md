# Build 24: actor clipping audit and default-off reuse

`ACTOR_CLIP_REUSE=1` reuses the two shared corners of each near-clipped strip
triangle. Its default is zero. This is a concrete reduction in repeated drawing
work; it is not proof that actor clipping explains the farm's console slowdown.
The diagnostic must establish the number and length of clipped strips in the
near-barn/body view before assigning a scene benefit.

## Mechanism and preserved behavior

`Part::strips` already rejects common-outside strips and directly submits strips
with no near-plane corner. Only its existing near-plane fallback changes. The
old `Part::clip_strip` rebuilds all three corners for every triangle, including
`world_of`, projection, cached UV/RGB, and opacity reads. A strip of `n` vertices
therefore prepares `3*(n-2)` corners. The new helper prepares exactly `n`.

The same three `RenderVertex` slots and three opacity slots hold the live
triangle. After emitting triangle `t`, the helper copies slot 2 into slot
`t&1` and prepares the next corner in slot 2. The sequence is
`0,1,2` → `2,1,3` → `2,3,4`, preserving strip winding and order. The unchanged
shared clipper, UV packing, capacity check, output sink, output counts, and
first-failure behavior remain in the owner. No persistent geometry cache,
resource ownership, pose reuse across draws, or new allocation is introduced.
Preparation reads inputs that remain stable during this strip; emission
consumes its arguments synchronously.

For valid attempted strips, including a capacity refusal, the audit should show:

- OFF: `ClipRebuilds = 3 * ClipTriangles`.
- ON: `ClipRebuilds = ClipTriangles + 2 * ClipStrips`.

The separate actor draw audit classifies native part attempts and existing
input/output topology. Actor OUT/XLU includes CPU-emitted or packet-staged
triangles that may later be abandoned or belong to a discarded scene; it does
not prove successful TA consumption or presentation. Translucency comes from
native UI's actual selected or draining PVR list. View overlap uses common
screen outcodes; it does not measure
occlusion or depth visibility. Optional alternate sinks/backface accounting
that cannot supply matching topology are marked `Unsupported`.

Other inspected issues remain suspects, without a speculative fix: repeated
model/frame/light setup, matrix/palette traffic, and pointer alignment contracts.
The actor admission checks validate ranges and strides but do not provide an
explicit alignment proof for every `short*`/`float*` source read. No malformed
asset or observed alignment exception was available. The model OT walker is a
linked-list traversal; a per-frame sort was not found in `Render()`.

## Exact host verification

`actor_host.py` executes the actual production actor translation unit through
the existing Build 2 host AVK/SQ adapters. Production preparation/control code
and the shared `pvr_geometry.cpp` clipper remain live. Packet and direct modes
each compare the complete OFF/ON emitted TA, ownership, and state bytes.

Both ordinary O2 and AddressSanitizer + UndefinedBehaviorSanitizer O1 passed:

| Mode | Cases per OFF or ON arm | Added clip cases |
|---|---:|---:|
| Packet | 3,766 | 3,624 |
| Direct | 3,774 | 3,624 |

Each configuration also executes 8,130 helper controls for parity, sequential
preparation, and every bounded early-abort position. The clipping cases cover
rigid/skin/source6/wide-normal inputs, lengths through 128, all cull modes,
material/per-vertex alpha, packed/unpacked UV, repeated indices and EOL bits,
near/far/equality/zero-depth/outside-screen conditions, and capacity failures.
The test-only dump helper skips `fwrite` on empty vectors, fixing its null-pointer
libc contract without changing output bytes. Source/receipt hashes and exact
case/output hashes are retained in `actor_receipt.json`.

## Compiled SH4 reconstruction cost

`actor_target_build.py` compiles the full production actor TU using the selected
Make-derived Test 24 profile and the pinned KOS compiler. The explicit public
profile override `NMR_POOL_LOD=0` avoids an existing recipe prerequisite that
cannot be satisfied by the restricted public profile; neither arm changes the
recipe. `actor_target_run.py` executes the resulting scalar SH4 instructions
and compares every prepared vertex/opacity byte at the clipper edge.

There are 25 cases: rigid/skin near-crossing, rigid/skin far-depth, and stride-6
source near-crossing, each at 3, 4, 16, 64, and 128 vertices. Far-depth cases
deliberately invoke `clip_strip` as controls; the normal renderer takes its
existing fast strip path for these inputs. All prepared bytes match exactly.

The external clipper observation edge returns zero. Timings include full Part
construction and the actual preparation/parity loop, but exclude unchanged
clipping arithmetic, nonempty TA emission, and device waits. The repository's
pipeline model supplies warm/perfect-I and initially cold 8 KiB I-cache costs;
both assume perfect D-cache and a synthetic code layout. These are model cycles,
not measured console time.

| Input | Vertices | Prepared corners OFF → ON | Warm cycles OFF → ON | Cold-I cycles OFF → ON |
|---|---:|---:|---:|---:|
| Rigid near | 3 | 3 → 3 | 1,377 → 1,400 | 2,003 → 1,999 |
| Rigid near | 4 | 6 → 4 | 2,635 → 1,918 | 3,261 → 2,548 |
| Rigid near | 16 | 42 → 16 | 17,713 → 8,134 | 18,339 → 8,764 |
| Rigid near | 64 | 186 → 64 | 78,025 → 32,998 | 78,651 → 33,628 |
| Rigid near | 128 | 378 → 128 | 158,441 → 66,150 | 159,067 → 66,780 |
| Skin near | 3 | 3 → 3 | 1,716 → 1,730 | 2,416 → 2,418 |
| Skin near | 4 | 6 → 4 | 3,313 → 2,358 | 4,013 → 3,077 |
| Skin near | 16 | 42 → 16 | 22,459 → 9,894 | 23,159 → 10,613 |
| Skin near | 64 | 186 → 64 | 99,043 → 40,038 | 99,743 → 40,757 |
| Skin near | 128 | 378 → 128 | 201,155 → 80,230 | 201,855 → 80,949 |

The minimum three-vertex strip regresses by 23 warm model cycles for rigid and
14 for skin. Longer tested strips improve. For 64 vertices, the actual scalar
data trace shows:

| Input | Loads OFF → ON | Stores OFF → ON | Load bytes OFF → ON | Store bytes OFF → ON | 32-byte line visits OFF → ON |
|---|---:|---:|---:|---:|---:|
| Rigid near | 21,356 → 9,355 | 9,849 → 4,985 | 76,614 → 34,480 | 39,393 → 19,937 | 31,205 → 14,340 |
| Skin near | 26,937 → 11,148 | 10,221 → 5,113 | 96,892 → 40,948 | 40,881 → 20,449 | 37,158 → 16,261 |

Unique touched data lines increase by one in this fixture (rigid 146 → 147,
skin 158 → 159); peak stack rises 716 → 736 bytes. Fixture executable bytes
rise 3,192 → 3,288. Thus the supported claim is less repeated computation and
traffic, not a smaller total data footprint or measured cache misses. These
fixture sizes do not replace the separate full-TU composition/identity gate.

## Reproduction and acceptance boundary

From the repository root:

```sh
python3 port/dreamcast/tools/cloud/build24/actor_host.py --output /tmp/actor-host
python3 port/dreamcast/tools/cloud/build24/actor_host.py --sanitizer --output /tmp/actor-host-san
python3 port/dreamcast/tools/cloud/build24/actor_target_build.py \
  --output /tmp/actor-target --sh4-cxx /path/to/sh-elf-g++ \
  --kos-root /path/to/kos --sdk-root /path/to/sh4zam
python3 port/dreamcast/tools/cloud/build24/actor_target_run.py \
  --build /tmp/actor-target/actor-target-build.json --output /tmp/actor-price
```

Generated output directories must be new. Only synthetic fixtures are used.
`actor_receipt.json` is the compact final evidence; each script writes fuller
receipts and commands into its output directory. The complete modified-TU
OFF/absent identity and enabled compositions are handled by `build_controls.py`.
Console near/far attribution, enabled visual checks, gameplay STRICT, heap/KOS
headroom and scene milliseconds remain owner acceptance gates. Neither this
candidate nor its diagnostic is enabled by default.
