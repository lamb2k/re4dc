# t15 OTHER accounting audit, 2026-10-16

Reusable host profiling is complete. No runtime optimization is proposed or
accepted. **The requested 15.8 ms console OTHER residual is not yet mapped to
functions.** These tables account for the whole model interval and reconstruct
physical draw/skip means; neither is the benchmark's phase 4.

Source base: `3e303c5ecdcd993b14b22d540994708ecdd6a306`. Scene: r101-t12 burning
cross, approved L2 geometry; WORLD_VERT_LEVEL=5 is the contiguous 4 m package
variant, not another visual detail level. Costs below use the nominal 200 MHz
model unless explicitly called a calibrated projection.

| Run | Pacing | Samples/window | Nominal ms per trace | Calibrated projection ms per trace |
| --- | --- | --- | ---: | ---: |
| cxt16baserW | off | 30, 500:799 stride 10 | 57.702094 | 61.420635 |
| cxt16skiprW drawn-image group | fast, FORCE=2 | 21, 500:799 stride 7 | 70.302141 | 74.033660 |
| cxt16skiprW dropped-image group | fast, FORCE=2 | 22, same window | 21.326136 | 22.364405 |

## Physical iteration reconstruction

Each raw trace starts at Frame_cnt's increment. Its prefix runs logic and
preparation N, then Render_done/swap N-1. Its suffix starts at the actual
re4dc_pace_begin entry and renders N. In this forced alternating fixture, draw
combines drawn-image suffix with dropped-image prefix; skip combines
dropped-image suffix with drawn-image prefix. These combine independently
sampled means, not adjacent captured tick pairs or measured console pictures.

| Reconstructed physical mean | Total nominal ms | Identified pace polling | After that polling |
| --- | ---: | ---: | ---: |
| Draw | 56.986047 | 5.026795 | 51.959252 |
| Skip | 34.642230 | 14.509957 | 20.132273 |

The skipped physical iteration prepares the next visible image. Its remaining
20.132273 ms includes logic, preparation, service work and unidentified waits;
it is not a saving or the console's 6.4 ms residual. FORCE=2 runs iTaskScheduler
every iteration, unlike production catchup. Its measured flat self is only
0.000465 ms here; the watched complete reconstructed span is 0.000685 ms.

Polling was isolated from audited ELF PCs: the pace_end loop
`8c23e71c..8c23e724` and vi_retrace_count instructions `8c21e5b8..8c21e5be`
reached from that loop's call site. Other retrace callers and pace bookkeeping
remain. The final successful loop check is included. The entire pace_end or
retrace function was not subtracted. The configuration is locked to ELF SHA256
`897440d52a335b44f0dd0e6d7ead8f18609f2608bb44b9955e9c76bb9842f35c`.

Largest non-overlapping physical-skip self costs after the identified polling:

| Function | Nominal self ms | Observed caller context / interpretation |
| --- | ---: | --- |
| re4dc_pwc_ftrv_run | 0.977233 | Primarily partsWorldCalc; simulation/model state |
| re4dc_line_leaf2 | 0.893951 | blkPolyLineCkCore; collision |
| cEsp::CommonMove | 0.548034 | Mostly cEsp48::move; stateful effect update |
| re4dc_line_walk2 | 0.442431 | Collision |
| cSatMgr::hitCheck2 | 0.406324 | Collision |
| penClothAtCkParallel | 0.404523 | Cloth collision/update |
| EspTrans | 0.401878 | Trans; prepares the next visible image |
| Ps2fxClass | 0.384818 | Sprite visibility/classification; existing recipe memoization |

The numerical rows are flat PC self costs. Caller context comes from the partial
call tree and source; its timings are not relabeled as physical phase costs.
Tail calls and KOS thread switches can misassign or lose reconstructed returns.
For example, TaskScheduler has actual entry execution in every sample but no
completed watched returns. Return absence is not absence of execution.

## Audited opportunity and limits

No untried exact repeat-work target is demonstrated by this audit. This is a
bounded finding about the inspected helpers, not a claim that no optimization
exists. Physical-skip category totals give upper bounds before any correctness
constraint: UI/bridge 0.008172 ms, PVR helpers 0.009142 ms, fog/haze 0.049321 ms,
OT/primitive allocation 0.284318 ms, and shared copies/clears 0.402561 ms. These
are disjoint self totals, not removable savings. clearOtWork alone is 0.112576 ms
and Trans self is 0.252190 ms; much of the latter prepares the next image.

Esp09_Trans, Esp0e_Trans, Esp45_Trans and Esp47_Trans have zero observed self cost
in both the base and forced samples, so they provide no measured opportunity in
this fixture. They retain stateful semantics and are not skipped by this work.
Fog tables already use dirty-key checks. native_ui::load is shared world/actor
binding work, not a HUD-only cost; world direct begin already caches headers.
The apparent repeated EspSpriteEligible source check compiles to one call in
the examined EspCommonTrans path. UI_OT_CACHE and the rejected world/actor draw
plans, MOVCA/SQ/PREF/layout approaches were not repeated.

## Why exact benchmark OTHER remains unresolved

The phase definition was read from `76f40d95`:
`bench.cpp:19-24,1027-1048`, `main.cpp:295,302,375`,
`trans.cpp:1199-1210,1307-1386,2658-2660,2759-2781`, and
`coarse.cpp:908,1006-1008`. Phase 4 excludes TaskScheduler, two actor-preparation
regions, dynamic EmMgr ModelRender callbacks, world drawing, and the wait/swap
tail. Interrupts and other KOS threads belong to the phase they interrupt.

The current model ELF has no re4dc_bench_phase/re4dc_bench_iter,
benchAliveSnapshot, re4dc_bench_actor_slot or BenchActorDraw code. Recoverable
anchors in the forced ELF are:

| Boundary | Current ELF anchor | Remaining qualification |
| --- | --- | --- |
| Logic | TaskScheduler call `8c023aee`, entry `8c033ff4`, explicit return site `8c023af2` | Frame_cnt write is in the call delay slot `8c023af0`; erased marker has no exact counter barrier |
| Wait tail | `8c023c08`, after DRAW REMAIN's ProcessTickGet return | Includes swap and pacing, not only busy polling |
| Next OTHER | `8c023a9e`, return from pace_begin | Benchmark begins OTHER after this call, not at pace_begin entry |
| Coarse world start | `8c0502ce`, after readiness and null guards | Internal world-to-actor and actor-to-OTHER transitions are inlined |
| PS2 world call | `8c050582`, return `8c050586` | Only part of the benchmark's world region |
| ModelRender | entry `8c03dc30` | Requires per-call EmMgr snapshot membership and nested phase restoration |

The decisive missing information is **ModelRender's actor membership at OT
construction**. Both objTrans and emTrans call ModelTrans; it registers the same
ModelRender callback into several shared OTs. Function entry or return PCs alone
cannot distinguish those models. The benchmark snapshots EmMgr membership and
uses it to push phase 2 for actors, then restore the interrupted phase. This
snapshot is absent; the retained trace records PCs and memory addresses, not
register values or loaded/stored values. Actor transaction eligibility is a
narrower predicate and cannot substitute for benchmark membership. A validated
reconstruction of object identities and the relevant EmMgr snapshot, or explicit
phase events from a matching benchmark diagnostic, is still needed.

Additionally sourceActorPlan/sourceActorPrepare and coarse draw_actors are
inlined with no symbol entry/return pair. Their two preparation regions,
early exits, and world/actor/OTHER transitions need a complete audited control-
flow map; subtracting whole Trans, Render, coarse_draw or ModelRender functions
would be wrong. Current evidence therefore does not establish an exact model
phase-4 partition, and no number is labeled as one. Even a future exact model
partition would not turn model milliseconds into the console's 15.8 ms residual.

## Validation and artifacts

All input traces were replayed in their original order with continuous model
cache/timing state. Every frame's function charges and call-node deltas reconcile
with its total. Every trace crosses exactly one pace_begin boundary; prefix plus
suffix equals its function costs exactly. All retrace caller shares reconcile
exactly; loop cost is a subset of pace_end self.

The instrumented simulator preserves the original frame totals, per-PC table and
aggregate call tree byte-for-byte. The raw-entry scanner passed instruction vs
memory-event and truncated-record fixtures. The final rebuilt simulator is
byte-identical to the qualified executable, SHA256
`0c79a92f2c56437ecba5292a985c799da2ad1b916abb13560ac75c85ad2c29e9`.
These are host-tool checks. No runtime source changed, no game build or console
test ran in this lane, and there is no runtime STRICT or console acceptance claim.

- Machine-readable result: `ch1-other-accounting-t15-20261016.json` beside this file.
- Reusable tools: `port/dreamcast/tools/d367/other/README.md`.
- Evidence root: `/root/probe/codex-other-t15-20261016/audit/`.
- Final full-model tables: `base-account-final`, `base-partition-final`,
  `skip-account-final`, `skip-partition-final`.
- Physical reconstruction: `skip-phases/{phases.json,physical_functions.tsv,physical_categories.tsv,wait_pcs.tsv}`.
- Full ordered replay: `skip-segments-v2`; disassembly: `bench-boundaries` and `pace-end-disasm.txt`.
- Validation: `exporter-validation.json`, `phase-exporter-validation.json`.

Raw source traces remain untouched under the parent CPU lane's evidence folders.
