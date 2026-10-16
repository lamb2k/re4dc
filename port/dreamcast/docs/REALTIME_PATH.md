# RE4 Dreamcast performance and measurement contract

Current execution belongs to [PLAYABLE_PATH.md](PLAYABLE_PATH.md) and the
[active r100 native cutover](R100_NATIVE_CUTOVER_GOAL.md). This file supplies
measurement/acceptance rules, not a competing sequence of optimizations.

## Current measured baseline

D361 retained preparation improved matched recovered render p50 from about
1,563 to 1,368 ms. D362 (`62414dc`) then recovered 34,016 source-heap bytes with
exact UV sharing and no material runtime-work reduction. D362 ends the lossless
scavenging phase. Keep both controls and their exact source overlays/assets.

D362 render p50/p95: **1,368.093 / 1,370.801 ms**; page-flip p50/p95:
**1,389.602 / 1,406.282 ms**; late source free/largest: **116,704 bytes**.
These are matched settled Flycast observations, not responsive encounter or
physical-hardware acceptance. Audit counters disabled in the ordinary build are
unmeasured, not zero. See [the checkpoint](R4_NATIVE_PREPARATION_CHECKPOINT.md).

D349's approximately 49-58 ms CPU reference demonstrates the converted-room
architecture on its own supported workload; it does not promise that cost for
the recovered game. D353's bake result likewise belongs to its historical room
target. Preserve [D349](R4_R100_REFERENCE_RECOVERY_CHECKPOINT.md) and the isolated
D353 checkpoint as reuse/evidence references.

Earlier bridge-cache/admission instructions, prelighting postponements and
per-component priorities are superseded. Their measurements and rejected
experiments remain in the checkpoints and
[the D362 plan snapshot](https://github.com/stevedamnvan/re4dc/blob/62414dc39feccc949af4b3ed29053be9fde4d5fc/port/dreamcast/docs/REALTIME_PATH.md).

## Measurement contract

Record commit, executable/disc and private asset hashes, converter options,
compiler/KOS versions, output resolution, emulator configuration, room/state,
input source, camera, requested and actual simulation ticks, and capture window.
Keep generated outputs and evidence directories isolated. Concurrent emulator
runs or drifting assets invalidate a paired timing comparison.

Time production-like builds. Keep digest, full tracing, fault-injection and
snapshot instrumentation separate. Collect the smallest diagnostic needed to
answer the question, then time without its overhead. Do not redesign telemetry
or repeat all historic captures as a prerequisite for each implementation step.

**A requested tick is not an observed state.** For comparison builds, stop the
simulation exactly on the requested tick and record actual player, animation,
camera, input/RNG/event state. Do not freeze after a catch-up batch and label it
with an earlier target tick. Use the `b7d29e3` mechanism and validate its identity.

Separate these costs instead of summing overlapping aggregates:

| Measurement | Required distinction |
|---|---|
| Source simulation | Input consumption, task/event ordering, collision, actors, camera; no silently discarded time. |
| CPU rendering | Visibility, deformation, lighting, clipping, packet preparation, and actual transfer costs. |
| PVR / presentation | Registration/render duration, waits and distinct presented updates; zero wait alone is not proof that GPU cost is zero. |
| Packet workload | Native static room, dynamic actors, effects, HUD and generic fallback calls/bytes separately; fewer emitted vertices/passes, not compressed packets. |
| Loading | Read, validation, installation, texture/audio transfers, and retirement measured separately. |
| Memory | Code/data/reservations, persistent resources, temporary install scratch, heap/stack, VRAM/AICA, and safety margin at simultaneous peak. |

Report p50/p95/p99/max frame and presentation intervals where available, sample
counts, missed deadlines, input queues/gaps, simulation debt/drops, and route
coverage. A reciprocal CPU-frame median is not sustained FPS. Do not add stage
medians from different populations and call the result a frame budget.

Compare unchanged baseline and candidate in the same sitting/configuration.
An old baseline also becoming faster in a new session is not a new-code gain.
Load-time savings are not resident-frame savings. Emulator memory arithmetic and
functional evidence do not establish physical SH-4 timing or real media rates.

## Current implementation and deferred tuning

The acceptance unit is the complete r100 native-package cutover in
[R100_NATIVE_CUTOVER_GOAL.md](R100_NATIVE_CUTOVER_GOAL.md), measured against
D361/D362. Profiling explains remaining cost and regression; it does not start
another series of independently promoted bridge/cache optimizations. Use focused
host checks internally, then the integrated target comparison. Bisect a failing
whole candidate when needed.

Preserve dynamic source dependencies and safe fallback for unconverted content.
Converted static work is prepared offline. Reuse existing D349 topology, local
slots, pass organization, lighting/prelighting, clipping and packet mechanisms;
do not recreate them or spend the source heap on a second complete visual copy.

Instruction-level math/transfer experiments are deferred until the cutover's
residual cost warrants them. `tools/sh4_loop_cost.py` is a proxy, not hardware
acceptance. Historical R3/R4 negative results remain in their checkpoints; use
those findings before repeating a rejected approach. The DCA3/KOS/community
references supply mechanisms, not this project's task order or FPS promises.

## Correctness and test scope

Maintain three distinct statuses: execution-safe diagnostic; source-correct
integration; performance-qualified gameplay. Unsafe resources or memory block
execution. An identified visual mismatch blocks promotion to fidelity acceptance,
not every diagnostic or independent integration task.

Use focused host/boundary tests for layouts, counts, overflow, partial preparation,
and indices above 65,535. In fault tests, distinguish requests from reached
failures and assert ownership while the failure stands before cleanup/retry.

For a rendering mismatch, reproduce one complete state and locate the first
divergent batch, packet, primitive grouping, or effective state. Do not repeat
multi-minute pixel runs before isolating that state. A common helper name is not
proof of emitted equality; an aggregate counter is not proof of identical pixels.

Pure optimizations compare against the accepted matching target state. Source
behavior corrections may intentionally change it and must use the source game
as authority. Alternative assets receive explicit fidelity/performance review,
not a false claim of losslessness. Never preserve a known prototype bug solely
to retain an old digest.

## Performance qualification, not permission to integrate

For the completed representative sequence, target one new game update per two
refreshes in the selected 60-Hz mode; use measured cadence and report 50-Hz or
other modes separately. Include stressful gameplay and transitions, repeated
runs, native-resolution moving images, audio alignment, and responsive human
control. Report missed deadlines and stalls rather than hiding them in averages.

No hidden simulation/input loss, allocation failure, TA overflow, or memory
corruption is acceptable. Preserve source pause/loading semantics so transition
waits neither accumulate catch-up debt nor replay queued gameplay inputs.

Physical Dreamcast validation is required for final performance, controller,
audio, storage, and memory conclusions. Prepare runnable hardware candidates
without blocking useful software integration solely because hardware is absent.
If intact source workload cannot meet the target, present measured options for
review under the asset policy instead of quietly altering camera or gameplay.

The next task remains the dependency needed for the boot-forward playable slice,
not the next letter in a graphics experiment series.

## D364 decision and historical stretch references (2026-09-23)

AoS20 is the leading layout unless integrated evidence disproves it. Its four
packages total 1,299,298 B versus Split24 1,478,690 B and v3 1,992,824 B. The
Flycast preparation/packet fixture p50 was 47.486 ms for AoS/D349, 47.935 ms for
Split/D349 and 35.293 ms for v3 prelit. This is a storage/CPU trade, not a game
speedup. SH4ZAM transform/reciprocal did not win; keep D349 math as default.
Initial qualification is complete; layout/math micro-tuning is not current work.
Keep its pinned implementation and PVR DMA example review in
R4_ROOM_PACKAGE_V4_CHECKPOINT.md (the pin itself: the submodule game/third_party/sh4zam since 2026-10-16).

After the generic visual bridge has largely disappeared and remaining costs are
measured, evaluate useful XMTRX/SH4ZAM transforms, actor skinning, positive-depth
reciprocal, dynamic-light math, direct/DMA transfer and compiler choices. Preserve
the pinned GCC15.2/KOS; any toolchain-wide change is a separate measured decision.

The roadmap's historical references are D349 whole-trace CPU p50 ~57.6 ms, mean
presentation interval ~55.2 ms (~18.1 presented FPS), PVR traffic ~0.97 MB/frame,
and D353 settled prelit room pass ~17.6 ms. These are different workloads, not
equivalence promises. The stretch objective is to make the complete source-driven
game cost no more than D349, then pursue 33.3 ms/30 FPS if hardware permits.
Measure equivalent candidate/control states and actual presented cadence before
claiming either threshold. Source gameplay quality is not reduced to hit them.
