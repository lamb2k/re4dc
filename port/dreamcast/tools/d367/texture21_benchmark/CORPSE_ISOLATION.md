# Future matched corpse render isolation

This is a preparation plan. No corpse render filter is implemented or enabled,
and no performance cause is established. Preserve the ten bodies and source
region semantics; the rejected CUT_GORE workaround does not belong in a recipe.

The report's image13 shows a body pile. The corresponding source candidate is
r103_setCorpse in src/st1/r103.cpp, called outside region0. It creates ten class2
cObj instances through SetObjSmd, each with a base plus three appended parts,
source motion and two-thirds material RGB. SetObjSmd uses ObjMgr.create(2),
front insertion, blk=-1 and no authored SMD scroll number. A static world BIN
or invented SMD ID is therefore not an adequate selector.

| Creation ordinal | Enemy archive0x12 base | First extra part | Shared extras | TPL | Room motion |
|---|---|---|---|---|---|
|0|0x1bc|0x1be|0x1c0,0x1c5|0x1bd|0x1f|
|1|0x1d8|0x1da|0x1c0,0x1c5|0x1d9|0x20|
|2|0x1e0|0x1e3|0x1c0,0x1c5|0x1e1|0x21|
|3|0x1bc|0x1be|0x1c0,0x1c5|0x1dd|0x22|
|4|0x1d8|0x1da|0x1c0,0x1c5|0x1bd|0x23|
|5|0x1e0|0x1e3|0x1c0,0x1c5|0x1d9|0x24|
|6|0x1bc|0x1be|0x1c0,0x1c5|0x1e1|0x25|
|7|0x1d8|0x1da|0x1c0,0x1c5|0x1dd|0x26|
|8|0x1e0|0x1e3|0x1c0,0x1c5|0x1bd|0x27|
|9|0x1bc|0x1be|0x1c0,0x1c5|0x1d9|0x28|

First establish exact runtime identity. In a separately claimed diagnostic build,
register each object once at its source constructor with its ordinal, owner
serial/generation, complete base/part/TPL/motion signature and room epoch. Do
not walk live logic lists from benchmark/render code. Validate all ten identities
and their current draw path. Object-address reuse, missing identities, changed
room/archive, or epoch retirement must disable the diagnostic filter safely.

Root must reserve any shared constructor/draw hook before implementation. A
proposed diagnostic-only switch defaults0 and requires the explicit QA benchmark
configuration. Ordinary builds remain unchanged. The diagnostic changes only
final render submission for the registered whole-body cohort. It never writes
be_flag, region, model links, motion, source object transforms, collision, enemy
state, event flags, audio, visibility state consumed by gameplay or cull policy.
Do not use SmdSetTrans or destroy/suspend bodies as a render-isolation shortcut.
Keep normal preparation/logic intact for this first test; it isolates final draw
cost and cannot measure potential skin/pose savings that still execute.

Use one exact diagnostic program/ELF and asset set for both arms. Reuse the
unchanged QA r103f cold-entry lineage and its scheduled id0x12 kill. Normal
navigation to the reporter-facing pile camera must first be established and
saved with source position, camera matrices, room/frame, neutral-input state,
health and exact same-program checkpoint hash. The current farm entry camera
has not established that view. Do not compare it directly with the reporter's
unbound screenshot or call it the pile hotspot.

Once that camera is authenticated, run two independent fresh continuations of
that exact same-program checkpoint. One emits all ten bodies; the other suppresses
only their final draws. Both use the same120 source ticks, neutral controller,
animals-off, cap4, same room state/geometry/assets/materials and source-scheduled
kill history. Controls: all-on should emit the registered cohort, all-off should
emit zero cohort submissions, while all noncohort geometry/logic counters agree.
Keep menu, pause and offscreen views out of this pair. A separate viewport-away
control may follow if the initial pair identifies a cost worth investigating.

Record exclusive final-submit CPU/TA work and whole-frame CPU/PVR, source ticks
per picture, displayed pictures, read requests/bytes, VRAM/KOS peaks and
pixel/still evidence. Require unchanged source decisions, event/door/kill counts
and visible noncohort work. Report Flycast or MODELLED results as such; console
acceptance remains separate. A large render-only delta would justify a scoped
follow-up such as source-faithful one-pose reuse; it would not itself prove why
the tester's hardware slowed down or authorize permanent body removal.
