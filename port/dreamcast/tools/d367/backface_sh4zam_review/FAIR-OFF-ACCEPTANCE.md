# Required fair OFF versus CPU_BACKFACE=2 gate

The user's new acceptance gate is faster than non-backface. Improvement over the C reference is not sufficient. Hold the current SDK candidate as a correctness baseline until a matched full-render comparison establishes that gate.

## What the current opcode evidence establishes

The exact SDK trace-off kernel object92adaa7e has been re-modelled after the generic SH4ZAM dependency scheduling changed. For64 input indices: world front2578 cycles, back3242 with0 emitted vertices, mixed3422 with35 emitted. The actual OFF world walk costs1141 including its outcode scan, decisions and all64 SQ copies. The ASM numbers exclude its caller scan, so current CPU-only modelling shows no win in these tested front, back or mixed cases. This comparison already accounts for dropped copy work; adding a separate12-cycle saving per dropped vertex would double count it.

It does not settle device performance. The issue model omits cache misses, SQ drain/TA backpressure and PVR work. Those omitted costs may make rejected traffic valuable. They need a matched measurement or an explicitly calibrated model, rather than attributing all saved vertices the same invented cost. CPU and PVR overlap, so adding independent total CPU and GPU durations also gives a false frame saving.

Within this issue model, even ignoring CPU2's caller scan, the64-index all-back strip needs over2101 saved stall/device cycles to recover the difference, or over32.83 per rejected vertex. The mixed strip needs over2281, or over78.66 per rejected vertex. All-front emits the same traffic and cannot recover its extra issue work through vertex rejection. These are illustrative lower requirements within the incomplete model, not hardware bounds or scene thresholds.

## Exact evidence required per fixture

Use matched OFF0 and SDK2 builds from the same final source, QA base, compiler/KOS/SDK pins, recipe knobs, CPU clock model, assets, camera, logic/animation tick, enemy poses, lights and resolution. Trace/census instrumentation must be disabled in the timing arms. Preserve programme, ELF, every overlay, all loaded model/texture package identities and exact frame window. Run separate diagnostic capture arms only to extract and bind that window.

For r101 calm/fight, r100 forest, r119 El Gigante and close Ganado, record a complete drawn iteration after fixed warmup. Do not combine loading frames with recurring draw cost. Name logic ticks per picture and isolate drawing self cost from animation/gameplay. Repeat matched windows and compare variation. Flycast wall time/FPS is not Dreamcast performance evidence; label any existing SH4 issue/PVR simulation MODELLED, and physical measurements separately.

A bounded private diagnostic capture needs, for EVERY submitted eligible or excluded part in that complete frame: model kind/id plus source package identity, world/Leon/Ganado/ElGigante class, owned/skinned path, cull/alpha/depth material flags, header identity, meshlet/strip boundaries, original index bytes, projected32-byte vertex cache and outcodes, active SQ/clip decision, source strip limit and input/output spans. Record clipping and rejected-before-backface work too. Count at least strips, input triangles/vertices, output vertices, emitted pieces, all-front/all-back/mixed classification, short versus long back runs and leading/trailing rejection. A byte cap or partial frame means capture incomplete, not extrapolation.

The capture should use the established qualified class bridge, rather than model offsets or guessing from class4. Positive actual Ganado bursts in the close fixture are mandatory. Leon, Ganados and El Gigante get independent rows even though the kernel is shared. Static world rows need material eligibility; alpha-mask, no-depth-write and cull-none remain excluded. Preserve all private records locally and charge their storage; root must allocate any new capture before execution.

## How to price the complete caller fairly

Feed identical captured projected inputs into the actual OFF and SDK2 target opcode paths. World OFF is the entire lean codes/decisions/copy function; SDK2 includes walk_lean_sq caller setup, codes/decision loop, every kernel call, split/EOL work and return/counters. Actors OFF include whole-meshlet AVK or strip emitter selection and setup; SDK2 includes the actual Part::whole/strip dispatch and whole-stream EOL handling. Price clipped, excluded and all-front parts too. Carry actual branch paths and caller/callee effects, not an average triangle area count. Keep common transform/skin/light work once and demonstrate it is unchanged before cancelling it.

For each material/class and scene, sum actual per-call path costs, including count-dependent setup and split counts. Separately state the uncached issue result and calibrated cache/SQ/TA model result. A useful threshold is the remaining added CPU cost divided by actual saved traffic or device work, with units and calibration clearly named. No threshold exists for rows with zero saved traffic. Device critical-path modelling must preserve CPU/PVR overlap; require the complete matched drawn-iteration result, not a sum of incompatible inclusive timers.

The standing BACKFACE_CENSUS input/output vertex percentages cannot supply these missing strip distributions or full caller costs. TA_HASH/census also changes the diagnostic emit cost. Current retained opcode tables are useful correctness/per-path baselines, not the scene acceptance table. The independent lean-address/outcode-fusion branch can be measured against the same frozen replay set once sealed; do not change the acceptance baseline while evaluating it.
