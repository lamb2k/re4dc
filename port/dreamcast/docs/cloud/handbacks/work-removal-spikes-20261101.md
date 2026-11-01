# Work-removal spikes: local-agent handback, 2026-11-01

## Latest local handoff — six source spikes pushed; qualification held

Source bundle: `7b29e56d57203b8b521dae9c768f779bd8c72f47`; branch `codex/work-removal-spikes-20261101`.
Shared with local through draft [PR #62](https://github.com/lamb2k/re4dc/pull/62)
and existing Build29/31/32 handbacks. Local pickup/execution has not been observed.
All six controls default0 and no recipe is changed. **Implemented and pushed** are
complete for these bounded slices. **Integrated, enabled and accepted** are not
claimed. The larger burst-decode and non-FE-header opportunities remain deferred.

### Delivery commits

| Slice | Exact pushed commit | Local scope |
|---|---|---|
| A actor padding | `d72663fa4998d1c8584c4cf2b06a900cb1ad6518` **plus** `27337b4284f505596755219b28578c6d1673185f` | Initial A alone is superseded; take the inactive-parent line correction |
| B early prop refusal | `87f81a28016bb11faf2866aec8ef960c16ef1978` | Head metadata/materialized buffer only; normal rendering continues |
| C immediate effect decode | `1632d433b51bb638c46da6418ceaa7056ca1e7ab` | Immediate selector call only; no burst reuse |
| D grid edge reuse | `3c7608c06f9312cf8af2e48ef077758d5c6604cf` | Existing quad only; no row buffer |
| E empty world preparation | `0415f16cb8cfc07ad36d66b9dcf2d677caa6440c` | Bind/header/owner/camera retained |
| F deferred cloth normals | `7b29e56d57203b8b521dae9c768f779bd8c72f47` | Existing normal producer/fallback boundary;64-byte revision/pending state |

These are serialized commits, with shared make fragments/test drivers and tracking
updates. D extends C's make/test files; B extends A's actor driver. Use the final
corrected branch tip for the combined source review. Cherry-picking individual
runtime experiments requires their prerequisite make/test changes and all noted
corrections; it does not authorize hand-resolving the three older blocked merges.

### Truthful worker / task / next deliverable / dependency matrix

| Worker | Observed execution state | Completed task | Next deliverable | Dependency wait |
|---|---|---|---|---|
| root/deep_actor | Completed; files frozen | A/B initial implementation; F cloth implementation and fixtures | None outstanding for the delivered bounded spikes | Local target/runtime gates |
| root/deep_effects | Completed; files released | C/D implementation; independent actor/world/cloth review; actor line repairs | None outstanding | Burst sharing needs source lifetime proof; no private-data excuse for that deferred proof |
| root/deep_world | Completed; files frozen | E implementation; independent effects review | None outstanding | Actual empty-pick incidence and target economics |
| root | Source publication complete; final handoff verification | Main Makefile, exact-source application, repeated host checks, tracking, serialized pushes/readback, PR | Handback to local | Selected target SDK/runtime/console not accessible here |
| Local coordinator | Pickup/activity not observed | No local execution claimed by cloud | Target OFF/ON qualification, one-switch cost arms, serialized integration decision | Local SDK, runtime/private scenes and console access |

Assignment is not evidence of active execution. Cloud workers above delivered files
and test results in this session and are no longer represented as running jobs.

### Reproduce the public host gates

From a complete checkout containing the pinned65fe3d1f baseline:

```sh
python3 port/dreamcast/tests/test_work_removal_actor01.py
python3 port/dreamcast/tests/test_work_removal_effect01.py
python3 port/dreamcast/tools/tests/test_world_empty_prep01.py
python3 port/dreamcast/tests/test_cloth_normals_defer01.py
```

Root reapplied and reran all four suites in the assembled publication snapshot.
Effects/world use immutable baseline source; cloth also supports
`--baseline-root <frozen-source-root>`. Actor reconstruction was independently
verified against exact frozen source. Includes-elided source location checks and
host object/executable hashes are **not** target programme/allocated/overlay identity.

New controls are registered through four make fragments included by the real game
Makefile. Full Makefile knob resolution with an explicitly empty SDK-rules fixture
reported all six0; object-specific isolated make gates also pass. This proves
wiring/default resolution only. No selected SH-4 compiler was accessible. The owner
off-switch scanner is not in the accessible public tree; it was not run. All51
pre-existing `landed` Status rows are byte-for-byte preserved, and the new row does
not mark these controls landed or enabled.

### Local experiment order and stop conditions

Qualify target OFF identity before any runtime comparison: absent and explicit0
must preserve the complete program, allocated sections and overlays under the
existing judge. Then compile each ON profile with its required parents and invalid
guard controls. Grid/cloth require actual-target numeric/FPSCR checks. Host stubs
do not qualify the real FIFO, material lifetime, native texture publication or task
interactions.

| Control | First useful positive arm | Required negative/cost arm | Added cost to include |
|---|---|---|---|
| ACTOR_PADDING_FIRST01 | A current actor workload with nonzero display-list headers | All-zero or zero-prefix padding lists | One branch; no persistent state |
| EFFECT_RECORD_PASS01 | Natural packed EspEstSetSelect calls | Raw/retaining records and constructor failure paths | No added persistent state; raw-read diagnostics reclassified |
| ESP1B_EDGE_REUSE01 | Admitted multi-cell grids at several divisions | Small grids, early budget refusal, partial publication and FPSCR variants | Two existing vertex copies per subsequent cell; no row buffer |
| WORLD_EMPTY_PREP01 | Empty-first and all-empty selected parts | All-visible/nonempty worlds and mutation/resource failures | Early nr check; binding stays |
| CLOTH_NORMALS_DEFER01 | Native-only cloth updates then fallback | 2x2 sheets, frequent fallback, reuse/retirement and degenerate diagnostics | 64-byte state; per-update and per-draw revision work |
| PROP_GATE_EARLY01 | Definite head-info metadata/materialized-buffer refusals | Mostly eligible props and non-FE-only rejection (unchanged) | Additional head/span checks; diagnostic reason precedence changes |

Use matched source/assets, same camera/enemy state and identical measurement/
observer settings. Alternate control/candidate order, include cold and warm cases,
and report whole-frame milliseconds and distribution plus CPU/PVR/wait components.
Count natural qualifying operations and fallback/refusal rates; do not extrapolate
the synthetic work savings to every object or frame. Report code/stack/data and
heap/VRAM/arena thresholds, since tiny code/data growth can change real costs.

Start with A and C, then D; qualify E where empty-first/all-empty incidence is real.
F must include small grids and frequent fallback. B's larger non-FE opportunity is
still unimplemented and its positive-path checks can lose time. Keep any candidate
parked if net frame cost regresses or output/STRICT/lifetime evidence fails. Combine
only individually worthwhile candidates and rerun combined memory/cost/identity
gates. No speed claim, recipe promotion or hardware acceptance follows from this
handoff.

### Publication and recovery provenance

Current integration was re-fetched between slices; last preserved upstream is
`cff417dde421e4919825c740eac7f3e3be8a7270`. Its three follow-ups after65fe changed rr-qa and
release documentation/kit, with no runtime overlap. Topic-only merges preserve
those updates and published history; no force push or integration-branch write
occurred. Older staged Blender-policy work and historical worktrees/branch tips
remain untouched. Git CLI network access was unavailable at the configured proxy;
GitHub Git-database APIs performed the authorized topic publication.

Every entry below was followed by branch-ref readback. The final documentation
commit will be identified by PR head and the cloud response.

| Publication | SHA |
|---|---|
| Initial activity checkpoint | `03670a1d0da272e9c6dc07b225f6ced2b539cc71` |
| Preserve current upstream rr-qa change | `e68bf9648698c45a074748d7f9ef869490e46946` |
| A ACTOR_PADDING_FIRST01 | `d72663fa4998d1c8584c4cf2b06a900cb1ad6518` |
| Preserve upstream Test25 docs and kit | `90b5be6127b59bb8b93013c918c8676624d3fe97` |
| A correction: inactive-parent OFF line identity | `27337b4284f505596755219b28578c6d1673185f` |
| Preserve upstream cff417dd | `fa55a2fa5592e2cc0305e2f4936fddd227aae868` |
| C EFFECT_RECORD_PASS01 | `1632d433b51bb638c46da6418ceaa7056ca1e7ab` |
| B PROP_GATE_EARLY01 | `87f81a28016bb11faf2866aec8ef960c16ef1978` |
| D ESP1B_EDGE_REUSE01 | `3c7608c06f9312cf8af2e48ef077758d5c6604cf` |
| E WORLD_EMPTY_PREP01 | `0415f16cb8cfc07ad36d66b9dcf2d677caa6440c` |
| F CLOTH_NORMALS_DEFER01 | `7b29e56d57203b8b521dae9c768f779bd8c72f47` |

Emails remain stopped. Existing private/release/look/console holds and the three
older blocked merges remain; upstream's separately authorized release-document
changes were preserved, not reclassified as acceptance of these spikes.


---

## Historical activity and bounded slice records

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


## Slice E — empty world picks skip geometry-only preparation

Control `WORLD_EMPTY_PREP01=0`, main Makefile wired to native_static.o.
The nr==0 return follows bind(), its header/owner/camera effects, the post-bind
mutation check and existing accounting. Only gather/scratch/package geometry/
constant/cache preparation is skipped. Empty replay records remain selected.

Seven test methods pass in root and independent review, using complete production
emit_pick/chunk_emit/chunk_restart, actual borrow members and real portal helpers:
22 scenarios per compiled arm, mutation/stream combinations, bind/owner refusal,
pre/post-bind/end mutation, scratch/gather failure, mixed empty/live order, partial
output and restart. Empty completion stays Culled with no whole-source witness.
The SCN_CENSUS empty increment is preserved.

Intentional behavior change: unused geometry-resource refusal no longer aborts an
empty pick. Nonempty resource failure and bind/owner/mutation failures retain their
abort/refusal behavior. In the fresh64-corner indexed-empty fixture, one gather,
one geometry borrow, one constant preparation, five package accesses and64 cache
primes disappear while bind/header/owner/camera/end traces match. Do not multiply
this saving by every empty pick; later records can share already prepared state.

Four includes-elided whole-source token/logical-location profiles and extracted
host object OFF identity pass (SHA256e96c964a17d837af836b7860dba3f6f5652023abd9f1069f56dda818356fc6bc).
Run `python3 port/dreamcast/tools/tests/test_world_empty_prep01.py`.
SH-4 object/link identity, target cost and real empty-first/all-empty incidence
remain open. Binding elision and selector plane/gap changes are outside this spike.

Integration re-fetched before this slice: `cff417dde421e4919825c740eac7f3e3be8a7270`. All new controls remain default0; target/full-image OFF identity, runtime/STRICT/output/look, net cost and console gates remain pending.


## Slice F — deferred cloth normals

Control `CLOTH_NORMALS_DEFER01=0`, requires CLOTH_NATIVE=1 and
NATIVE_DRAW_OUTCOMES=1; only cloth.o and esp4e.o receive the flag. Main Makefile
wiring is included. No Cloth ABI, normal allocation or geometry cache changes.

Only Esp4e's original calcNormal site marks pending. The unchanged normal routine
runs before an actual GX fallback consumes normals. Set's initialized{0,0,1}
normals and120 warmup moves remain untouched until the original update site occurs.
Native submitted/queued/partial-abort results never permit new GX replay.

Eight revision/pending records occupy exactly64 bytes. Init/Set/Destroy reset and
advance the slot. The draw snapshots revision around the native attempt; a changed
slot refuses stale fallback and preserves newer pending work. Revision is checked
again after calculation, before clearing pending or replay. Off-pool objects stay
eager; exhaustion permanently restores eager calculation for that slot.

Root applied the six-file patch to blob-verified baseline and reran:
`python3 port/dreamcast/tests/test_cloth_normals_defer01.py`.
The driver extracts actual spring/move/normal routines, both Esp4e move arms,
Cloth lifecycle and full clothTrans, with host engine/math/GX/native boundaries.
46752 assertions in each spring mode0/1/2 pass; these include per-normal checks,
not46752 independent scenes. Eight grid/pin stress profiles,28 real result/
publication combinations, first fallback, native-only updates then fallback,
repeated fallback, all8 slots, reuse/retirement/update callbacks, off-pool and
revision exhaustion pass. Host positions/speeds/phase/material/matrix/RNG traces
and consumed fallback normal bytes match the eager control.

Independent review fixed a native1/outcomes0 disabled line gap before publication.
24 includes-elided token/diagnostic/every-active-line profiles per source pass
against the frozen baseline.19 make/control/isolation profiles pass. ASan/UBSan
pass all spring modes; LSan is disabled for restricted /proc inspection, with
separate fixture allocation accounting. Whole Makefile resolution with empty
SDK rules reports all six new controls0; this is wiring evidence, not a target build.

**Enabled differences and limits:** zero-normal diagnostics are delayed until
fallback and can be omitted on native-only frames. The actual VECNormalize macro
and same-allocation diagnostic update are tested. The revision recheck preserves
newer pending work and refuses stale replay; it does not prove safety if a grid
were freed inside the unchanged normal loop. No such ordinary path was demonstrated
by the source scheduler/logger audit, and no logger/lifetime architecture change
is claimed. Host native outcomes do not qualify actual native admission or texture
publication, especially for oversized stress grids.

Measure tiny2x2 sheets and frequent-fallback scenes separately:64 bytes and update/
draw bookkeeping can cost more than the saved normalization. Actual SH-4 numeric/
FPSCR/exception behavior and complete memory/stack/net frame cost remain local gates.

Integration re-fetched before this slice: `cff417dde421e4919825c740eac7f3e3be8a7270`. All new controls remain default0; target/full-image OFF identity, runtime/STRICT/output/look, net cost and console gates remain pending.
