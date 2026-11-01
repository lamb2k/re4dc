# Work-removal spikes: local-agent handback, 2026-11-01

## Activity checkpoint — source work in progress

User request: spike fixes for the six source-grounded opportunities from the blob-style
work-removal investigation, then share with the local agent. Source base is
`65fe3d1f96ab269c136053725850101be9d3e692` on `origin/t15/int`, fetched through GitHub.
Its only change after `4df01855356d2defcdce6fb3b6c59f3bf690a469` is build-output pruning;
the reviewed runtime source is unchanged.

Delivery branch: `codex/work-removal-spikes-20261101`. Root serializes bounded commits and owns
shared build wiring and tracking documents. This is a new isolated task; it does not
resolve or overwrite the three previously blocked owner merges. No integration,
recipe enablement, runtime acceptance or release is authorized by this checkpoint.

## Actual worker / task / next deliverable / dependency matrix

| Worker | Observed state | Exclusive source ownership and current task | Next deliverable | Dependency wait |
|---|---|---|---|---|
| root/deep_actor | Running; padding slice delivered to root, prop slice in progress | native_actor_fast.cpp, trans.cpp, new actor make fragment and fixtures | Default-OFF first-byte padding guard; conservative prop eligibility before pose | No private input; root review/publication, then local target/full OFF/cost |
| root/deep_effects | Running | esp_sub.cpp, espgen00.cpp, native_effect.cpp and relevant effect headers if needed, esp1b_grid03.inc, new effect make fragment and fixtures | Immediate decoded-record reuse and horizontal grid-corner reuse | Burst reuse depends on archive-current/constructor lifetime proof; no private-data implementation wait |
| root/deep_world | Running | native_static.cpp, new world make fragment and fixtures | Empty picks return after binding/mutation check but before geometry-only preparation | No private input; actual empty-pick incidence and target cost require local runs |
| root | Running | cloth.cpp, esp4e.cpp, cloth declarations if needed; main Makefile; queue/backlog/existing build handbacks | Deferred cloth normals at the real fallback consumer; publish reviewed slices and draft handoff | Selected target SDK and local runtime/console qualification unavailable here |

Assignments alone are not activity evidence. The three workers were contacted in this
session and are executing the stated isolated tasks. Prior review probes survived.
Older accessible worktrees were inspected; staged Blender-policy work and historical
patches/branch tips were left untouched. Old workers outside this accessible team
cannot be certified active. Command-line Git network access currently fails at the
configured proxy; the GitHub connector provides current read and publication access.

## Bounded implementation contracts

1. Actor padding: retain pointer/length/RAM checks and the complete proof when byte zero
   is zero; a nonzero first byte proves that the list is not padding.
2. Prop gate: reject only safely proven unsupported inputs before pose setup; preserve
   source rendering on refusal. Do not add pose/lighting caches.
3. Effect records: reuse the already decoded local record in the immediate selector
   chain. Burst sharing is separately held unless it preserves archive retirement and
   copying-consumer qualification; raw retaining consumers must remain unchanged.
4. Grid: reuse old quad corners 1 and 2 as the next cell's 0 and 3. Preserve repeated
   float addition, source diagonals, order and terminal failures; no row allocation.
5. Cloth: mark pending at the original normal-update call, calculate unchanged normals
   only before an actual GX fallback. Preserve initialized normals before the first
   update, pool reuse, physics/RNG and partial-publication no-replay.
6. World: retain bind/header/owner/camera and the post-bind mutation guard; skip only
   geometry preparation when nr is zero. Empty completion is not an occlusion witness.

All controls remain default 0, outside release recipes. Guard PowerPC behavior and
preserve disabled source/diagnostic identity. Host probes are source evidence only:
the local coordinator still owns actual target profiles, full program/allocated-section/
overlay OFF identity, STRICT/output/look, stack/heap/VRAM, complete frame cost and
physical-console acceptance. Existing private/release/console/look holds and stopped
emails remain in force.

## Validation and publication state

Initial actor-padding production-fragment fixture: 172,245 cases passed; a nonzero
first byte reduces inspected bytes from 32/64/128/256 to 1 in those synthetic inputs.
Whole-TU preprocessing with include bodies elided preserves undefined/explicit-zero/
PPC token and __LINE__ output. Target binary identity and game benefit are unmeasured.

Other production spikes and fixtures are WIP. Subsequent sections will record each
bounded result, exact pushed commit and next local action. No implemented/pushed/
integrated/enabled/accepted state is inferred from this activity checkpoint.


## Slice A — actor padding first byte (implemented; public host gates pass)

Control `ACTOR_PADDING_FIRST01=0`; main Makefile wiring included in this slice.
The original range guard remains first; a nonzero initial byte skips the remaining
32..256-byte OR scan. A zero prefix retains a complete all-zero proof. No new cache,
allocation, owner state, geometry or admission is introduced. Source lines are reset
for exact disabled diagnostic expansion, and the PPC profile remains inert.

Root reapplied the patch to exact GitHub blob-verified source and reran
`python3 port/dreamcast/tests/test_work_removal_actor01.py`: 172,245 production-fragment
cases pass with matching outcomes/side effects. Nonzero headers inspect 1 byte versus
32/64/128/256 in the control. Make 0/1/invalid/prerequisite and includes-elided full-TU
OFF/PPC token/__LINE__ checks pass. Whole Makefile default resolution reports 0 using
an explicitly empty SDK rules fixture (build-wiring check only, no target compilation).

Before publication, integration advanced to `44a073ca6d5a09145507aa1aa6dfa10649ec7961`;
its sole rr-qa.sh padding fix has no runtime overlap. It is preserved in topic merge
`e68bf9648698c45a074748d7f9ef869490e46946`, retaining already published history.
Target programme/allocated/overlay OFF identity, target cost, actual incidence and
runtime/console acceptance remain pending. No recipe enablement.


## Slice A corrective review — disabled parent features

The initially pushed A commit `d72663fa4998d1c8584c4cf2b06a900cb1ad6518` is
**superseded as a standalone deliverable**. Independent review found that its source
line restoration was inside ACTOR_REPLAY_SKIN: when that parent is disabled, later
logical source lines shifted by12. The first host gate covered the enabled parent
and therefore missed this configuration. No target judge was changed or waived.

The corrective slice restores the old line immediately outside the parent block and
extends the test to15 profiles (minimal, FAST0/1, REPLAY0/1, absent/zero, PPC explicit1).
Every active token's logical filename/line and a downstream __LINE__ sentinel match
the pre-spike source. Root reran these gates and172245 actual detector cases: PASS.
Target programme/allocated/overlay OFF identity remains pending. Take A together
with this correction, or use the final branch tip; do not cherry-pick the initial A
commit alone. A similar inactive-parent gap in the unpublished prop slice is being
repaired before its first publication.

Integration was re-fetched at66260173711929c63386b552323fd1e2d5447c6a before this correction: upstream Test25 release docs/kit changes have no runtime or owned tracking overlap and are preserved by a topic merge. This spike does not modify those release decisions or enable any new control.


## Slice C — immediate effect-record reuse

Control `EFFECT_RECORD_PASS01=0`, scoped to esp_sub.o. EspEstSetSelect keeps
the record it already decoded for Kind through its immediate EspSeqSet call.
Raw/retaining records keep their original address. The single-line conditional
change preserves source-line counts. No timer code, generator burst, ABI or
archive lifecycle change is included.

Root reapplied exact baseline source and reran the actual selector/adapter fixture:
29 cases per arm;12 packed selections24 ->12 decodes and48 ->24 timer calls.
Constructor entry is a boundary shim, not full constructor/RNG/STRICT execution.
The retired-tag case tests adapter read after unbind, not retirement interleaved
inside the selector. Enabled packed selections add a raw_reads increment for the
predecoded-pointer branch; diagnostic classifications are intentionally changed.
Tested record bytes, call arguments, return mapping and raw retaining addresses
match. Independent review found no explicit yield in the immediate reuse interval.

Includes-elided source OFF/PPC preprocessing and extracted host executable OFF
identity pass (SHA25643960ebc27d81d2a9633079b4a42a60ccf76322c762fb2d015bff0b748753160).
Make default/invalid controls pass; main Makefile wiring is included.
Command: `python3 port/dreamcast/tests/test_work_removal_effect01.py`
(the driver reads the pinned65fe baseline from Git).

The larger espgen00 burst reuse is **deferred**. Mutable factory, virtual-constructor
and pool-cleanup paths have no proven archive-current interval across children.
No persistent cache or new generation mechanism was added to hide that gap.

Integration re-fetched before this slice: `cff417dde421e4919825c740eac7f3e3be8a7270`. All new controls remain default0; target/full-image OFF identity, runtime/STRICT/output/look, net cost and console gates remain pending.


## Slice B — conservative prop eligibility before pose

Control `PROP_GATE_EARLY01=0`, scoped to trans.o. Only the head info is examined
early, after existing model/projection checks and before pose setup. New dereferences
require full aligned cached-RAM spans. Empty list, existing reason4 metadata failures
or an already materialized position buffer can refuse the gate; ordinary rendering
continues. Unknown spans, hidden head infos and invalid buffer selectors retain the
original path. No list walk, display-list/header read, weight memo, skin registry or
lighting/palette operation is moved.

This is narrower than the non-FE TinyKeep hypothesis: **non-FE-only header refusal
still occurs late**. That larger change needs a stream-owner proof.

Root reran actual complete propGate/propGateWeights extraction:665 cases in each
PROP_GATE1 and checker2 pass, with matching return/continuation/postlude/checker/
weight-memo effects. Definite early refusals for B=1..64 bones skip one inverse and
2B concatenations. Positive inputs pay added metadata checks; net target cost is
unknown. Simultaneous pose and early-metadata failures can report reason2 ->4/5/8;
this diagnostic precedence change is explicit and tested.

Independent review repaired inactive PROP_GATE and FRONT_NATIVE parent line exits
before first publication.33 includes-elided token/location/__LINE__ profiles pass,
including PROP0/1/2, FRONT0/1/2, scenery/lean combinations and PPC. Reconstructed
pre-spike controls were verified byte-identical to frozen source. The final combined
actor driver also passes the15 padding profiles and172245 cases.
Run `python3 port/dreamcast/tests/test_work_removal_actor01.py`.
Target programme/overlay/allocated-section OFF identity remains required.

Integration re-fetched before this slice: `cff417dde421e4919825c740eac7f3e3be8a7270`. All new controls remain default0; target/full-image OFF identity, runtime/STRICT/output/look, net cost and console gates remain pending.


## Slice D — Esp1b adjacent-corner reuse

Control `ESP1B_EDGE_REUSE01=0`; requires ESP1B_GRID03=1, EFFECT_UV12=1 and
NATIVE_DRAW_OUTCOMES=1 individually. Root strengthened the new make guard to reject
ambiguous concatenated dependency values. Flag scope is esp_sub.o only.

At j>0, old corner1 ->0 and2 ->3 are copied before either source slot is overwritten.
Only corners1 and2 are evaluated; j=0 recomputes all four. The existing quad holds
the values: no row buffer, persistent pointer, allocation or material batching.
Repeated float addition, diagonals, cell order and terminal failures remain intact.

Root and an independent reviewer ran the actual producer/interpolation/UV fixture:
1082 cases,5728648 quad vertex records per arm, zero byte differences. Refusal,
partial abort, overflow and live-input mutation after the initial capture are
included. Complete d16 grids use1024 ->544 corner evaluations; d64 use16384 ->8320.
These counts do not establish real-grid frequency, target instruction cost or FPS.

Includes-elided source OFF/PPC checks and host ELF identity pass (grid
SHA2569709a30eb835dcce0620624cd50d741eb69c0d9f8e736243fbef3b5e5f3d3e9c).
ASan/UBSan pass; leak detection is disabled because sandbox /proc inspection is
unavailable, and no production allocation is added. Matrix/emission boundaries are
host shims: real FIFO/admission and stable SH-4 numeric/FPSCR behavior across emitter
callbacks remain target gates. Run the combined effect test driver from Slice C.

Integration re-fetched before this slice: `cff417dde421e4919825c740eac7f3e3be8a7270`. All new controls remain default0; target/full-image OFF identity, runtime/STRICT/output/look, net cost and console gates remain pending.
