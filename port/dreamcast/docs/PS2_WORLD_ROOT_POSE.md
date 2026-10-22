# One-root scenery pose candidate

`PS2_WORLD_ROOT_POSE=1` keeps a one-bone scenery object on its existing PS2
geometry while the original room script animates that bone. It defaults to 0
and requires `PS2_WORLD_PARTS=1`. No recipe enables it.

## Confirmed source and data defect

Issue 52's gate machinery is in r11c, the cabin route selector. The original
`r11c_moveGear` changes child angles of scroll IDs 0x10, 0x11 and 0x32;
`r11c_moveLever` changes ID 0x35. Their source SMD rows bind BINs 15, 16, 64 and
67 to unique PS2 placements 15, 16, 64 and 67. All four models have one bone.

In the retained QA fixture, their source BINs have two placeholder vertices and
zero primitive-stream bytes in every display list. The disc has no source
`MAINSCENARIO.re4mesh` package. Previously, `PS2_WORLD_PARTS` latched the first
changed child pose as source-owned and suppressed the PS2 placement permanently.
`PS2_WORLD_ROOMS=2` also skips binding a source native package. Consequently the
selected geometry disappeared as soon as the gear/lever animated.

The fixture's r11c.arc SHA256 is
`fd940ae7fe9137dda96ee5c3520e069875f099e896ce80f3d3469a53d2a62aed`.
This source/data result does not bind the reporter's exact executable.

## Implementation contract

Scroll setup calls `matUpdate` after applying placement and SMX parameters,
before publishing the part witness. For exactly one bone, retain its bind world
matrix and inverse in the existing witness allocation. At draw time use
`current_root_world * inverse(bind_root_world) * baked_PS2_placement`.
The selected retained BIN roots are part 0, parent 0xFF (the object), with zero
local centre and unit object scale. `modelInit -> initJoint -> setPartsParent ->
setPartsOffset` initializes the parts; the latter builds both local and world
matrices. `SmdSetParam` applies authored placement and calls `matUpdate`.
`setObj` applies SMX and calls `matUpdate` again before both native binds.
`cModel::matUpdate` rebuilds the object matrix, local part matrices and then
world part matrices, including the object's parent transform. Room SMD setup
also precedes scenario initialization and the gear tasks. The captured matrix
is initialized world space. Applying an extra object delta would apply it twice.
Source hashes and exact call-order lines are in `source-bind-order.json`.

The current root is source-owned; no animation, event, collision or AI code is
changed. The existing PS2 material, camera, clipping and ordering paths remain.

The object serial and active/visible/ready bits are checked before borrowed part
memory is read. A refused witness, stale owner, non-finite matrix, singular bind
matrix or exhausted delta array rejects the placement. A rejected root never
silently displays stale baked geometry. An intact occluder also requires the
same live owner and exact captured root matrix. The frame delta is a copied
matrix; the draw does not retain a borrowed root matrix.

Rebind and room/package retirement free witnesses through the existing owner
boundary. One-root witnesses add 96 bytes (rest plus inverse), and slots add
four bytes when enabled. The inverse is computed once at bind. The existing
16-moved-owner limit is preserved and remains a target coverage requirement.
Multi-bone objects retain the original source-hierarchy fallback; missing source
geometry for those objects remains an open gap.

## Evidence and remaining gates

`test_ps2_root_pose.py` compiles the actual adapter, affine helpers and occluder
query with address/undefined sanitizers. It covers root movement with pivot,
translation, nonuniform and negative scale, simultaneous object/root motion,
return to rest, visibility/readiness,
serial/address reuse, wrong-room lookup, allocation failure, singular/NaN input,
delta exhaustion, unchanged multi-bone fallback and reset retirement.
`test_ps2_dynamic_parts.py` retains the disabled-path lifetime checks.

Actual SH4 compilation using retained QA flags/generated headers passes for
native_static.cpp and scroll.cpp. Each stripped OFF object is byte-identical
to its original 892c10dde control. ON stripped-object size changes are +736 and
+4 bytes respectively. This is object evidence, not full program identity.

Private receipts, source-object ledger, extracted-asset hashes and the five
original issue screenshots are under
`C:/Flycast-Evidence/re4-dreamcast/issue52-objects-20261021/`.

Full matched OFF/ON program and overlay identity, normal-input lever activation,
animation/end-state screenshots, memory/refusal checks, broader room regressions
and console acceptance remain open. The church candle and unidentified save-room
lamp disappearance have not been attributed to this defect. The existing
OPTIONS pause candidate changes a separate presentation-context boundary.
