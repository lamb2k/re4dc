# SDO3 footprint repair (cf0 source control)

The standard542 ON full-H2 control completed its 340-frame movie and restore,
but its 93,920-byte game heap was 4,096 bytes below matched OFF (98,016).
Parent measured unchanged data/BSS and 3,072 bytes added text: OFF `_end`
`8c43c5b8`, ON `8c43d1b8`. This crossed the next 4 KiB arena boundary.
This source repair has no linked-programme or runtime acceptance yet.

## Changes

* In a mode3 reader build, outline the existing `fail` method at `Os`. It
  still clears the published data pointer and records exactly the same error.
  No validation or rejection condition changes. This first isolated control
  saved 206 aggregate bytes; it was insufficient by itself.
* Reuse the existing decoder context populated by `corners(l)` for the current
  repeat count, unique count, and source pointer. Boolean consumers use the
  existing `dd_base` predicate. No new field, allocation, reset, or retained
  lifetime is introduced. Modes1/2 retain their original table calculations.
* `dedup::fill` reads the reference from the current repeat vertex's x word.
  Admission already requires that word below the unique count (at most255)
  and verifies both repeat tags; its former byte-pointer read had the same
  value. Source coordinate selection, range priming, UV/color, and both SH4
  FMAC instructions are unchanged.
* In the mode3 alternate-file check, remove an unused zero-fill and cache the
  immutable baseline descriptor size. Header fields are inspected only after
  `read_package(...,80,0)` succeeds; that method succeeds only after all80 bytes
  are read. Only the first20 words are inspected; the uninitialized final four
  alignment words are never read. All identity checks remain.

## Actual SH4 unit measurement

Base source: `cf0d675acba08a8d0b61a9a3bb4eefa320107591`.
Exact compiler command came from retained standard542 ON/OFF build logs;
only the native_static output path changes. Compiler/scratch/output remain
in `/dev/shm`; compilation used the shared SDK slot and an owned-tree lease.
No full programme, staging, guest or media action ran in this lane.

| Unit | text plus read-only data | data | BSS |
|---|---:|---:|---:|
| Actual original542 ON and reproduced baseline |94342|2804|17212|
| Cold fail only |94136|2804|17212|
| Final candidate |93780|2804|17212|

Total aggregate reduction:562 bytes. Reproduced baseline and original542 ON
objects are byte-identical after debug stripping (SHA256
`55e29992e6ae1034e6a304eb48ee19d9c1c0b0ec1f982a6ec2af0dd343639de9`).
This projects the original standardW `_end` to `8c43cf86`,122 bytes below
`8c43d000`, before fresh linker alignment/relaxation. A fresh linked symbol
and matched full-H2 heap comparison are required; this projection is not a
passing memory gate. `size` includes read-only sections, not just symbols.

Measured symbol deltas: chunk_emit -172, draw -156, adopt -220, fill -12
(the compiler creates an internal clone), ps2_open -16, outlined fail +14.
Discarded outlining/annotation experiments increased size or gave inadequate
savings; no hot FP annotation or global optimization policy changes remain.

## Context caller audit

All new context getters are private MeshDraw members. Every consuming path
refreshes the current metadata in `corners(l)` before reading them:

* Ordinary `meshlet`: corners precedes the full transform, checksNone/Screen,
  strip-group span transform/priming/fill and clipping.
* Generic `draw`: corners precedes per-corner Emitter decode and near/far
  clipping. Those generic readers still use the original bounded
  `offline_position` decoder, including source XYZ and current UV/color.
* Chunk `emit_pick`: bind/borrow succeeds, then corners refreshes the current
  meshlet before SG or full transform/fill. Failed bind/borrow returns before
  metadata consumption. A later successful pick refreshes it again.
* `chunk_select` uses original bounds/LOD metadata and consumes no encoded
  coordinate. Empty selections consume no old decoder state. Zero groups
  refresh corners but exit before references. Plain/indexed corners clear
  dd_base and set unique==count. Every other LOD uses its own corners call.
* `chunk_restart` retains the existing fields, but subsequent geometry always
  refreshes them before consumption. Emitters are synchronous stack contexts;
  no emitter survives room retirement or the movie world-loan/reload. The
  existing package close/re-adopt contract is covered separately by readers.

The existing SCENERY_CHUNK compile guard requires MESH_VP_SCHED1 and disables
MESH_CLASSIFY. Mode0 keeps the original reader/failure helper and excludes the
entire dedup branch. Mode3 supports the existing default-off UV snapshot
boundary; this change does not assert UV snapshot ON composition.

## Validation

Final-candidate Python tests:14 pass. Actual C++ reader tests pass on retained
r100/r101/r103 original and alternate files:123664/103562/85192 ordered corners,
no reader operator-new, malformed marker/source/tag/count refusal; r101 SG
admission/refusal; close/reload and ordinary-room reset. Mode0 admits each base
and refuses each actual encoded alternate. These are host source semantics.

The source-extraction control is extended only to extract the two new actual
context getters (older snapshots without them remain supported). Final clean
source96 comparisons across8 configurations pass at runtime-source commit
`3467e45c6ea8c94a4a7cc26f4cc2623197330ee6`; the stale-cache mutation is detected.
See `composition-controls-footprint-3467-host.json`. The reader check additionally
replaces an earlier successful alternate bind with each malformed package,
requires the publication to become invalid, then rebinds an ordinary base.

The final frozen-source ON unit reproduces the562-byte reduction. OFF matches
the actual standard542 original object byte-for-byte after debug stripping:
`ee7f36bb77c14e5eec26f594f3f6136708a4ac3d0c15ea4a0e88d44f39e1b909`.
See `footprint-unit-cf-3467.json` for exact commands, generated-header pins,
source hashes, sizes and object hashes. SH4 FTRV/FSRRA, optimized target clipping, timings,
full image identity and memory gates remain root's qualification work.

Later actual5be qualification still measured ON93920 versus OFF98016. The
absolute-end projection above was insufficient: mem.cpp rounds available KOS
room minus its reserve, not absolute `_end`. See STRIP-SHARE.md for the current
exact-data repair and actual arena explanation; the562-byte unit result remains
valid, but it did not establish the required memory floor.
