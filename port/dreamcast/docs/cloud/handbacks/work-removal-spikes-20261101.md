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
