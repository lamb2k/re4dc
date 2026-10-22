# Fused candidates10 and12: independent full caller model

Root increased the total review source/Git/C-mirror ceiling to2MiB before these files were sealed. Target output remains32MiB. Candidate12 was first evaluated in-memory with Python bytecode writes disabled while that allocation was pending; the same immutable inputs were then recorded. No implementation edit, compiler, guest or image was used.

Candidate10 ELF2c30a252f4c523928a2db79a8789ba4af5f9007671b2a4d92f910dee1efd4128 carries the next raw seed moves into the FCMP/carry/branch-delay slots. Source lifetimes are sound: the old FR2 determinant is consumed by FCMP before its seed overwrite; seed moves preserve T; raw coordinates are consumed before their dead A register pair is reused; the final seed in the BRA delay is available before the next FSUB. Initial warmup seeds the first phase, and scalar terminal cases retain the full exact DAG. The representative phase models at18cycles instead of09's22.

Candidate12 ELFa2b396e208c7f8bd785ffcf8c6508ee427ece4d6477836e4962cbcb3d17f3ad1 adds six-triangle full blocks with fall-through, preserving scalar short tails and per-index actor EOL checks. The representative complete-block phase is15 MODELLED cycles with no exposed dependency wait under this model. That is not a four-cycle incremental or hardware claim.

|64-index first-code0 pattern|10 single-strip cycles|12 single-strip cycles|10 batch32 per strip|12 batch32 per strip|Fair OFF batch32|
|---|---:|---:|---:|---:|---:|
|All front|2242|2126|2130.594|2014.594|1109.031|
|All back|1432|1316|1320.594|1204.594|1109.031|
|Mixed retained fixture|2458|2342|2346.594|2230.594|1109.031|

These are entire SDK world submission paths, including lease, scan, mask, run emission, counters and return, excluding the thin RE4 adapter. Exact words, counts and stop pointers agree with the target-lowered C oracle in all retained cases. Both models omit caches, SQ/TA drain/backpressure, memory stalls and FPU exceptions. Transform/skinning/projection/light work is unchanged and not credited as a saving. None of these accepted submission rows passes faster than OFF; no scene gain follows from them.

Accepted first outcode4 with every other outcode0 adds447cycles/strip in10 and451 in12. Candidate12's batch32 per-strip front/back/mixed rows are2465.594/1655.594/2681.594. Keep these as separate eligible cases, rather than treating them as screen-all rejects.

Candidate12's first-code0 interior depth crossing at positions1/31/32/63 costs1244cycles in each case (10:1360). First-depth1 crossing costs606; all-depth629; all-screen641. Oversize first-depth0 clips in140, while first1/all1 rejects depth-all before the limit in628 and first1/rest0 clips in605. These cases preserve original decision order and expose the remaining interior-cross cost.

Actual trace-off text sizes:09=7072bytes,10=6976bytes,12=8160bytes. Candidate12 grows1184bytes over10. The full function text is not its executed hot set: world, actor, cull-direction, tail and legacy fallback bodies are selected differently. The current issue model charges no I-cache fill, set conflict, branch-layout or interaction with transform/draw caller code, so the size growth cannot be assumed free. Full scene and actor integration must retain those caveats or measure them.

Evidence is in DYNAMIC-SDK-CALLER-FUSED10-MODEL.json, DYNAMIC-SDK-CALLER-FUSED12-MODEL.json and corresponding HOT-PHASE-SCHEDULE files, with source/materialized-object identities. Repository patches were not yet the identities of these immutable dev objects. Existing exact controls, pixel/memory acceptance, release checks and physical acceptance remain separate gates.
