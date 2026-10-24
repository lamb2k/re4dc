# SDO3 and replay context composition control

Result: **PASS_HOST_COMPOSITION_ONLY** at consolidated source
04e1c8f2057c9d4169f23f931cbf8f7a00ac0fb2. This closes the bounded host-control item
in REVIEW-CURRENT.md; it does not accept the enabled combination on target.
Runtime/shared files, recipes, media and external STATUS headers were not edited.
No target build, staging or guest was launched.

The existing world_replay_lean source-extracted geometry harness is reused. New
[check_composition.py](/root/work/lanes/dedup-offline23/port/dreamcast/tools/d367/dedup_offline23/check_composition.py)
extracts the actual production Emitter, MeshDraw borrow/gather/corners, dd_word,
dd_source, emit_pick, strips_lean, chunk_restart and chunk_emit, plus the actual
chunk_flush lambda and direct begin/end functions. The actual portable clipper
and current package reader are included. The MeshDraw declaration contains only
the fields needed by these methods, using the existing geometry fixture's shim;
the tested method bodies are not rewritten implementations.

[fixture_composition.cpp.in](/root/work/lanes/dedup-offline23/port/dreamcast/tools/d367/dedup_offline23/fixture_composition.cpp.in)
adds synthetic, reader-validated v3 geometry and this eight-context sequence:

1. Encoded meshlet pair with position repeats and distinct UV/color seam words.
2. Empty context, with no picks and no coordinate access.
3. Unencoded plain meshlets.
4. Indexed fallback meshlets using the actual gather method and isolated pool.
5. Newly transformed/materialed encoded meshlets, selecting only SG group1.
6. A zero-group pick context, which refreshes corners but emits no geometry.
7. Another encoded SG context with different transform/material/alpha state.
8. A final plain context.

The encoded SG range is first-source span1..3; source0 is excluded while emitted
repeat corners4..7 reference sources1/2/3/1. This exercises partial priming without
reading an unselected first copy. SG source ranges are admitted through the
actual offline_groups validator. The decoded-position oracle uses ordinary
plain corners and its corresponding1..7 range. Both controls emit the same
selected strips; their transform work need not be equal. The encoded ref XYZ
contains the format tags, making accidental use as coordinates observable against
the decoded oracle.

Four shapes cover inside, near-plane crossing, far-plane crossing and screen
rejection. Three failure modes cover ordinary success, insufficient scratch at
the second texture acquisition, and binding/owner failure there. Every failure
follows an earlier successful context. Cases use new processes, so globals start
fresh between cases. Within a case the reused emitter spans the whole sequence,
while the reference constructs a fresh emitter per context through the actual
conditional chunk_flush branches.

## What is compared

SCENERY_DEDUP3 and SCENERY_SELECT_ONLY1 are fixed. Encoded versus decoded data,
SCENERY_REPLAY_LEAN0/1 and SCENERY_SUBMIT_BATCH0/1 produce eight configurations,
each running12 cases. The96 exact comparisons comprise48 fresh/reused comparisons
and48 encoded/decoded comparisons. Every submitted TA word, semantic accounting
word and selected cache record/outcode word is compared; unused scratch bytes
are intentionally excluded. Lock/unlock counts must balance. Near/far cases
assert that the actual portable clip path was entered. A separate mutation that
omits chunk_restart's cache/prime reset returns successfully but produces a
word/state difference, which the control detects. This demonstrates sensitivity
to stale borrowed constants/cache rather than relying only on noncrashing runs.

The compact receipt is
[composition-controls-04e1-host.json](/root/work/lanes/dedup-offline23/port/dreamcast/tools/d367/dedup_offline23/composition-controls-04e1-host.json).
It pins source files, extracted method bodies, helper/template bytes, compiler
and complete-output hashes. Detailed generated C++, binaries, compiler logs and
word traces remain only under /dev/shm/dedup-composition-control-final2. The
immutable RAM source snapshot was checked file by file against04e1 git objects
before main advanced its worktree; it contains no asset/media data.

## Scope limits and rerun

Two unconditional SH4 FMAC instructions in dedup::fill are adapted to host
multiply/add; dyadic fixture constants keep these chosen cases exact. The existing
geometry harness supplies a documented C adapter at the SH4-only SQ walk edge,
controlled texture/owner/stream edges and the portable transform. The portable
Emitter clipping branch executes; SH4-only optimized clip branches do not.
Consequently this is not FTRV/FSRRA/FMAC validation, target object/image identity,
real-room geometry coverage, PVR/console acceptance or performance evidence.
PVS/interior culling, package retirement/reload and cross-package emitter reuse
are outside this synchronous immutable-package chunk replay control. Enabled
SCENERY_DEDUP3 + SCENERY_REPLAY_LEAN1 still needs explicit target/look qualification.

Run in WSL with an existing pinned source tree or the preserved RAM snapshot:

```sh
PYTHONDONTWRITEBYTECODE=1 TMPDIR=/dev/shm \
python3 port/dreamcast/tools/d367/dedup_offline23/check_composition.py \
  --source-tree /dev/shm/dedup-composition-source-04e1c8f20 \
  --expected-source 04e1c8f2057c9d4169f23f931cbf8f7a00ac0fb2 \
  --output /dev/shm/a-new-composition-control
```

The output directory must be new and inside/dev/shm. Compiler scratch, generated
sources, binaries and traces stay there; child working directories are there and
core dumps are disabled. Python bytecode writes are disabled. Source snapshots
validate their complete source-pins.json before compilation; an ordinary source
tree must have the exact requested Git HEAD. No target or emulator tool is called.
