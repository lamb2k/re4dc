# Static-prop bake coverage on the current T15 fixture, 2026-10-16

The current source configures 14 baked object records, all in r101. The
runtime ownership, visibility, rest-pose fallback and room-retirement machinery
already works by room. Extending that table and generating matching assets is
possible, but this audit does not establish an incremental saving in any other
room. The suggested 0.5–1 ms per room remains an estimate, not a measured result.
No runtime code, assets, flags, arena or capture was added by this audit.

The census reads source at `4aa1dbe912baaf36d8f2afc492229af1006d713b` and the
17 world packages and room archives from the exact actor-lane T15 fixture.
Every package and archive SHA256 matches that fixture's captured payload
manifest. The source registry supports additional rooms; this is an inventory
of the 17 staged packages, not a claim of whole-game coverage. The route's
chapter 1 rooms are r100–r10b; r117/r118/r119/r11a/r11b are included because
they are also in the fixture and belong to the later chapter-2-1 route. In
`fullplay/segments.conf`, the lake segment ends chapter 1-3 and enters r11b at
the start of chapter 2-1. A stage-1 room ID does not by itself mean chapter 1.

## Existing coverage and room inventory

`port/dreamcast/game/model_bridge.cpp:620` contains the current `sobake` table:
placements 209–222 in r101, four doors (kind 0/id 0x41), three boxes (0x43),
three racks (0x45), three windows (0x46), and one kind-1/id-0x21 object.
Their source table comments total 3,786 triangles. That count is table metadata,
not a new decoded-geometry or current-visibility measurement.

The following ETS columns are **source declarations**, classified through
`EtcModel.cpp` and `et00.cpp` into the same door/box/rack/window classes the
existing bake supports. They are not visible object counts, immutable-object
counts, or the number of objects that can safely be appended. Conditional
creation, already-broken state and room-code spawns still require live evidence.

| Room | World placements / maximum ID | Bake records | ETS declarations | Door/box/rack/window declarations | Existing world mesh + R4PW bytes |
|---|---:|---:|---:|---:|---:|
| r100 | 283 / 282 | 0 | 11 | 11 | 1,557,532 |
| r101 | 223 / 222 | 14 | 28 | 25 | 1,300,620 |
| r102 | 43 / 42 | 0 | 8 | 6 | 400,380 |
| r103 | 134 / 133 | 0 | 21 | 12 | 1,085,960 |
| r104 | 291 / 290 | 0 | 22 | 18 | 666,764 |
| r105 | 243 / 242 | 0 | 10 | 10 | 770,476 |
| r106 | 156 / 155 | 0 | 8 | 8 | 1,002,480 |
| r107 | 71 / 70 | 0 | 17 | 17 | 905,820 |
| r108 | 148 / 147 | 0 | 15 | 7 | 923,872 |
| r109 | 95 / 94 | 0 | 6 | 3 | 940,476 |
| r10a | 228 / 227 | 0 | 6 | 6 | 751,664 |
| r10b | 126 / 125 | 0 | 4 | 4 | 706,216 |
| r117 | 238 / 237 | 0 | 14 | 14 | 867,304 |
| r118 | 159 / 158 | 0 | 21 | 7 | 935,628 |
| r119 | 95 / 94 | 0 | 6 | 3 | 1,065,692 |
| r11a | 242 / 241 | 0 | 14 | 6 | 760,552 |
| r11b | 137 / 136 | 0 | 14 | 5 | 780,660 |

These are the base `ps2-world.re4mesh` plus sidecar sizes, not heap use or
increased bake sizes. r101 currently selects the separately recorded wv5
variant: the approved L2-fixed geometry with contiguous data and 4 m batches.
The JSON records that variant's identity separately. All observed maximum
placement IDs are below 512; the narrowest room still has 221 additional IDs
available before the current gate limit. This does not establish a RAM budget.

## What is eligible for further study

| Source class/state | Treatment supported by this audit |
|---|---|
| Existing fixed world scenery | Already in the PS2 world path; prove an object is absent there before appending it. |
| Closed doors, unbroken boxes/windows, stationary racks | Candidates only at a reviewed rest state with current source visibility and exact model/part matrices; preserve source simulation and the live draw for every changed state. |
| Room-code set pieces and kind-1 objects | Require per-instance identity and state review; the current whitelist only includes kind-1/id-0x21. The ETS counts omit these spawns. |
| Transparent or alpha-tested surfaces | Preserve pass, cull, depth, alpha, texture and submission-order semantics; a stable matrix alone is insufficient. Window panes in particular are not certified immutable by their class. |
| Torches, fire/effects, scrolling or animated materials, moving parts, pickup/debris states | No new bake eligibility established. Continue their existing live paths until their changing state and ordering are separately accounted for. |

The existing gate (`model_bridge.cpp:701–785`, `native_static.cpp:3678–3747`)
does the following:

- Allocates from the existing room heap and keys state to the live room-heap
  generation. Room exit frees the saved matrices and state; a retired generation
  is never reused as a live source owner.
- Runs its preparation callback at the first world pass after object movement
  and OT registration, then latches the same gate decision for all passes.
- Finds actual OT `ModelRender` callbacks, skips objects whose
  `invisible_factor * invisible_factor2` is zero, binds an
  allowed class and rest-matrix hash, waits for the package placement and all
  texture keys, and compares every model/part matrix word and count each frame.
- Gates the world copy off if the original object drew earlier in the frame;
  otherwise the source model skips only when that frame's world decision draws
  it. Absent/hidden/moved objects fall back or disappear through source state.

This is not a general proof of immutable material state. The table/gate does
not freshly compare a material revision, texture animation, partial opacity,
lighting parameters or every source shader mode. Those must be established for
each new rest-state candidate. An extension must also keep per-room entries
contiguous: current lookup stores the first match and a count, then indexes a
contiguous subarray.

## Reuse the current converter and caches

`STATIC_OBJ_BATCH=2`, its word comparison, `MODEL_DRAW_PLANS=1`, preparation,
position and room-strip caches are already enabled in the current stack.
Batching copies eligible runs of identical display-list/part/light records to
existing room-heap cells and keeps poses and lights live; it is not offline
world baking. Its existing level-2 lighting behavior is already part of the
baseline, not a new gain available from this proposal.

Other rooms already ship PS2 geometry converted into source model assets.
`ps2_objects.py` preserves the generic model path, joint and material identities,
source culling and lifecycle. The current fixture uses the objs13 archives in
15 rooms and the existing r100/r101 archives. The objs13 recipe deliberately
keeps breakable geometry on its reviewed GC path because the broken/debris
model depends on it. That geometry conversion coverage is separate from the
14 r101 world-bake records and supplies no measured world-bake benefit.

The existing `SOB_DUMP` capture and private `sob_bake.py`/`p_bake5.py` pipeline
already produce the exact pose, lit geometry, material and placement mapping.
The checked-in `ps2_world_append.py` appends the resulting prelit groups to
R4IM and R4PW while retaining base tables, and can share an affine-identical
mesh when materials, UVs and colors match. It uses existing texture keys;
R4SG and other CRC-bound sidecars must be regenerated for the resulting package.
The diagnostic's 384 KiB buffer is a capture resource, not a proposed resident
arena. No converter has been rerun here.

An appended placement costs 52 R4PW bytes, each new sidecar part 16 bytes,
plus the actual R4IM mesh/part/vertex/index/LOD tables and any derived sidecars.
The source object assets and simulation are still needed for live fallback, so
this does not release their backing. Runtime saved rest matrices cost
`48 * (1 + linked part count)` bytes per bound object, plus the existing state.
That state currently embeds `Obj[kN]` for the **entire** global table, not just
the active room. Simply adding every room's records would therefore increase
each active room's state allocation. Any extension should account for this
before generating assets; this audit adds no allocator or arena.

## Cost evidence and next admissible step

The current r101 burning-cross capture attributes 1.559094 ms/frame nominally
to all remaining per-part setup (about 30.2 calls), with current PLAN1 enabled,
frames 500–799 sampled every ten frames. That includes non-prop callers,
lighting, packet/SQ work and meshlet bookkeeping; it is not the immutable-prop
subset or a removable budget. Call-tree reconstruction is imperfect under
interrupts/tail calls. The existing actor audit provides the exact source,
payload and full-frame model comparison.

There is no matched current-base per-room immutable-prop cost or new bake A/B
for any of the other 16 rooms. Their cost and savings fields are explicitly
null in the machine-readable report. No 0.5–1 ms/room saving is claimed, and
no arena is justified by these counts. If this lane continues, first measure
the visible candidate subset in one representative room, then reuse the
existing capture/conversion path for only that subset and compare against the
complete current stack with source-state, texture, image/order, event/fallback
and memory gates. Further captures are outside this completed read-only audit.

Evidence: `/root/probe/codex-static-props-t15-20261016/audit/room-package-census.json`.
The reproducible reader is
`C:\Game Dev\Emulators\_codex_static_props_t15_20261016\census.py`.
